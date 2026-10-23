from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

SECRET = "confidential-marker-text"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("JOBS_DB_PATH", str(tmp_path / "jobs.db"))
    with TestClient(create_app()) as c:
        yield c


def _count(c: TestClient) -> int:
    return len(c.get("/api/jobs").json())


def test_create_returns_pending_job_with_all_fields(client: TestClient) -> None:
    r = client.post("/api/jobs", json={"text": "hello world", "analysis": "word_count"})
    assert r.status_code == 201
    job = r.json()
    assert set(job) == {
        "id",
        "text",
        "analysis",
        "status",
        "result",
        "error",
        "created_at",
        "updated_at",
    }
    assert job["status"] == "pending"
    assert job["text"] == "hello world"
    assert job["analysis"] == "word_count"
    assert job["result"] is None and job["error"] is None
    assert job["created_at"].endswith("Z")
    assert client.get(f"/api/jobs/{job['id']}").json() == job


@pytest.mark.parametrize(
    "body",
    [
        {"text": "", "analysis": "word_count"},
        {"text": "   \n\t ", "analysis": "word_count"},
        {"text": "x" * 20001, "analysis": "word_count"},
        {"text": "fine", "analysis": "sentiment"},
        {"analysis": "word_count"},
    ],
)
def test_invalid_input_422_and_nothing_stored(client: TestClient, body: dict) -> None:
    r = client.post("/api/jobs", json=body)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert _count(client) == 0


def test_max_length_accepted(client: TestClient) -> None:
    r = client.post("/api/jobs", json={"text": "x" * 20000, "analysis": "top_words"})
    assert r.status_code == 201


def test_422_body_has_no_job_text(client: TestClient) -> None:
    r = client.post("/api/jobs", json={"text": SECRET, "analysis": "bogus"})
    assert r.status_code == 422
    assert SECRET not in r.text
    r = client.post("/api/jobs", json={"text": SECRET * 2000, "analysis": "word_count"})
    assert r.status_code == 422
    assert SECRET not in r.text


def test_oversized_body_rejected(client: TestClient) -> None:
    big = '{"text": "' + "a" * (2 * 1024 * 1024) + '", "analysis": "word_count"}'
    r = client.post("/api/jobs", content=big, headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "payload_too_large"
    assert _count(client) == 0


def test_oversized_streamed_body_rejected(client: TestClient) -> None:
    def gen() -> Iterator[bytes]:
        for _ in range(40):
            yield b"a" * 65536

    r = client.post("/api/jobs", content=gen(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    assert _count(client) == 0


def test_list_newest_first(client: TestClient) -> None:
    ids = [
        client.post("/api/jobs", json={"text": f"t{i}", "analysis": "reading_time"}).json()["id"]
        for i in range(3)
    ]
    listed = [j["id"] for j in client.get("/api/jobs").json()]
    assert listed == list(reversed(ids))


def test_unknown_id_404(client: TestClient) -> None:
    r = client.get("/api/jobs/9999")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "not_found", "message": "Job not found"}}
