# Suggested 2–3 minute video walkthrough

## 1. Introduction (15–20 seconds)

"Hi, I'm presenting my audio transcription pipeline. I built a Python FastAPI service that accepts an audio file, transcribes it using a pretrained faster-whisper model, and returns timestamped text segments."

## 2. Explain the architecture (30–40 seconds)

"The client uploads a file to POST /transcriptions. The service validates the extension, checks the size, saves it with a unique job ID, and schedules transcription in the background. It returns HTTP 202 so the client does not need to wait for the full transcription. The client polls GET /transcriptions/{job_id} for status and the final result."

## 3. Show the implementation (45–60 seconds)

"In main.py, create_transcription handles the upload and size limit. transcribe_job loads the model, uses a concurrency semaphore to limit simultaneous transcriptions, and collects each segment's start time, end time, and text. The status endpoint returns queued, processing, completed, or failed. The worker retries failures up to three times with exponential backoff and removes temporary audio by default."

## 4. Demonstrate the API (30–45 seconds)

"Here is the Swagger UI at /docs. I upload a small audio file using POST /transcriptions, copy the job ID, and poll the GET endpoint. When it completes, the response contains the full transcript and a list of timestamped segments. I would also test an unsupported extension and an empty file to verify error handling."

## 5. Discuss trade-offs (20–30 seconds)

"This is a small take-home implementation. Job state is held in memory, so for production I would replace it with a durable queue and database, store audio in object storage, add authentication and rate limiting, and add automated tests and monitoring. This makes the service more reliable across restarts and multiple instances."

## Before recording

- Run the project locally and confirm `/docs` opens.
- Test with a short audio file you are allowed to use.
- Show the actual code while explaining it.
- Do not claim a test passed unless you ran it.
- Speak in your own words and keep the video concise.
