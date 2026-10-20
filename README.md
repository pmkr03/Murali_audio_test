# Audio Transcription API

A small FastAPI project that accepts audio files, transcribes speech with a pretrained `faster-whisper` model, and returns segment-level timestamps.

## Features

- `POST /transcriptions`: upload WAV, MP3, M4A, FLAC, OGG, WEBM, or MP4 audio.
- `GET /transcriptions/{job_id}`: poll job status and retrieve transcript/timestamped segments.
- `GET /health`: health check.
- File-size limit and extension validation.
- Background transcription, a configurable concurrency limit, and bounded retries.
- Segment output includes `start`, `end`, and `text`.
- Audio is deleted after processing by default. Set `KEEP_AUDIO=true` to retain it.

## Requirements

- Python 3.10+
- FFmpeg installed and available on `PATH` (required by many audio formats).
- Internet access on first run if the model must be downloaded.
- Enough RAM/CPU for the selected Whisper model. `base` is the default.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API docs.

## Example request

```bash
curl -X POST "http://127.0.0.1:8000/transcriptions" \
  -F "file=@sample.wav"
```

The API returns HTTP 202 with a `job_id`. Poll the returned status URL:

```bash
curl "http://127.0.0.1:8000/transcriptions/YOUR_JOB_ID"
```

A completed response contains fields similar to:

```json
{
  "job_id": "example-id",
  "status": "completed",
  "language": "en",
  "transcript": "Hello there.",
  "segments": [
    {"start": 0.0, "end": 1.2, "text": "Hello there."}
  ]
}
```

Exact timestamps and text depend on the audio and model output.

## Configuration

Environment variables:

- `WHISPER_MODEL`: `tiny`, `base`, `small`, etc. Default: `base`.
- `WHISPER_DEVICE`: `cpu` or `cuda`. Default: `cpu`.
- `WHISPER_COMPUTE_TYPE`: e.g. `int8` on CPU. Default: `int8`.
- `MAX_FILE_MB`: upload limit in MB. Default: `100`.
- `MAX_CONCURRENT_TRANSCRIPTIONS`: concurrent transcription slots. Default: `2`.
- `UPLOAD_DIR`: upload directory. Default: `uploads`.
- `KEEP_AUDIO`: set to `true` to keep audio after processing. Default: `false`.

## Docker

```bash
docker build -t audio-transcription-api .
docker run --rm -p 8000:8000 audio-transcription-api
```

## Git repository setup

```bash
git init
git add .
git commit -m "Build audio transcription API with segment timestamps"
```

Create an empty repository on GitHub, then connect and push:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/audio-transcription-api.git
git push -u origin main
```

Replace the URL with your actual repository URL. Do not submit the placeholder.

## Design decisions and limitations

- The API returns quickly with a job ID; clients poll for completion.
- The example keeps job state in process memory. Restarting the service loses job status. For a production multi-instance service, use a durable queue (e.g. Celery/RQ with Redis), persistent job metadata (e.g. PostgreSQL), and object storage (e.g. S3/Azure Blob).
- The in-memory state is for a take-home demonstration, not a durable production queue.
- Retries are bounded. Permanent failures still end in `failed` status.
- Extension validation is not a complete security inspection. Production deployments should inspect actual file content, scan uploads, authenticate clients, apply rate limits, and enforce retention policies.
- Do not commit real customer audio, credentials, API keys, or sensitive transcripts.
