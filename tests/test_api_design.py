"""Lightweight tests for the API contract. Install pytest and httpx to run."""
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_rejects_unsupported_extension():
    response = client.post(
        "/transcriptions",
        files={"file": ("notes.txt", b"not audio", "text/plain")},
    )
    assert response.status_code == 415


def test_unknown_job_returns_404():
    response = client.get("/transcriptions/not-a-real-job")
    assert response.status_code == 404
