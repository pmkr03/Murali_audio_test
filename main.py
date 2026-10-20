import os
import time
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from faster_whisper import WhisperModel

APP_NAME = "Audio Transcription API"
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_BYTES = int(os.getenv("MAX_FILE_MB", "100")) * 1024 * 1024
MAX_CONCURRENT_TRANSCRIPTIONS = int(os.getenv("MAX_CONCURRENT_TRANSCRIPTIONS", "2"))
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}

app = FastAPI(title=APP_NAME, version="1.0.0")
jobs: dict[str, dict[str, Any]] = {}
jobs_lock = threading.Lock()
transcription_slots = threading.Semaphore(MAX_CONCURRENT_TRANSCRIPTIONS)
_model = None
_model_lock = threading.Lock()


def get_model():
    """Load the model once, only when the first job needs it."""
    global _model
    with _model_lock:
        if _model is None:
            _model = WhisperModel(
                MODEL_SIZE,
                device=DEVICE,
                compute_type=COMPUTE_TYPE,
            )
    return _model


def update_job(job_id: str, **updates):
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(updates)


def transcribe_job(job_id: str, audio_path: Path, language: str | None):
    """Background worker. Retries a small number of times and records final status."""
    update_job(job_id, status="processing", started_at=time.time())
    try:
        with transcription_slots:
            last_error = None
            for attempt in range(1, 4):
                try:
                    model = get_model()
                    segments, info = model.transcribe(
                        str(audio_path),
                        language=language or None,
                        vad_filter=True,
                        beam_size=5,
                    )
                    output_segments = []
                    # faster-whisper returns a generator; consume it inside the try block.
                    for segment in segments:
                        output_segments.append({
                            "start": round(float(segment.start), 3),
                            "end": round(float(segment.end), 3),
                            "text": segment.text.strip(),
                        })

                    transcript = " ".join(s["text"] for s in output_segments).strip()
                    update_job(
                        job_id,
                        status="completed",
                        language=getattr(info, "language", language),
                        language_probability=round(float(getattr(info, "language_probability", 0.0)), 4),
                        transcript=transcript,
                        segments=output_segments,
                        completed_at=time.time(),
                        attempts=attempt,
                    )
                    return
                except Exception as exc:
                    last_error = exc
                    if attempt < 3:
                        time.sleep(2 ** (attempt - 1))
            update_job(
                job_id,
                status="failed",
                error=f"Transcription failed after 3 attempts: {last_error}",
                completed_at=time.time(),
            )
    finally:
        # Keep source audio for debugging only when configured; otherwise remove it.
        if os.getenv("KEEP_AUDIO", "false").lower() != "true":
            try:
                audio_path.unlink(missing_ok=True)
            except OSError:
                pass


@app.get("/health")
def health():
    return {"status": "ok", "service": APP_NAME}


@app.post("/transcriptions", status_code=202)
async def create_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str | None = None,
):
    """Accept an audio upload and return a job ID for polling."""
    filename = file.filename or "audio"
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio extension. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    job_id = str(uuid.uuid4())
    audio_path = UPLOAD_DIR / f"{job_id}{extension}"
    size = 0

    try:
        with audio_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    destination.close()
                    audio_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Audio file exceeds the configured size limit.")
                destination.write(chunk)
    finally:
        await file.close()

    if size == 0:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    with jobs_lock:
        jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "filename": Path(filename).name,
            "size_bytes": size,
            "created_at": time.time(),
        }

    background_tasks.add_task(transcribe_job, job_id, audio_path, language)
    return {
        "job_id": job_id,
        "status": "queued",
        "status_url": f"/transcriptions/{job_id}",
        "result_url": f"/transcriptions/{job_id}",
    }


@app.get("/transcriptions/{job_id}")
def get_transcription(job_id: str):
    """Return job status; completed jobs include transcript and segment timestamps."""
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Transcription job not found.")
        return dict(job)


@app.get("/")
def root():
    return {
        "service": APP_NAME,
        "docs": "/docs",
        "health": "/health",
        "submit_audio": "POST /transcriptions",
        "poll_result": "GET /transcriptions/{job_id}",
    }
