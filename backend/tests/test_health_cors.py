"""API skeleton: health route, schema bootstrap, CORS, error bodies, route table."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import db
from app.main import create_app, parse_cors_origins
from app.schemas import JobOut

ALLOWED_ORIGIN = "http://allowed.example:5173"
OTHER_ORIGIN = "http://evil.example:6666"

EXPECTED_COLUMNS = {
    "id",
    "text",
    "analysis",
    "status",
    "result",
    "error",
    "created_at",
    "updated_at",
}


@pytest.fixture()
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "nested" / "dir" / "jobs.db"
    monkeypatch.setenv("JOBS_DB_PATH", str(path))
    return path


@pytest.fixture()
def app(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("CORS_ORIGINS", f" {ALLOWED_ORIGIN} , http://second.example:3000 ")
    return create_app()


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    # The context-manager form runs the lifespan, i.e. the real startup path.
    with TestClient(app) as c:
        yield c


def _preflight(client: TestClient, origin: str, path: str = "/api/jobs") -> dict[str, str]:
    response = client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    return {k.lower(): v for k, v in response.headers.items()}


# --- health -----------------------------------------------------------------------


def test_health_answers_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_unusable_database_as_503_error_body(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("JOBS_DB_PATH", str(blocker / "jobs.db"))
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "service_unavailable"
    assert str(tmp_path) not in response.text


# --- schema -----------------------------------------------------------------------


def test_startup_creates_schema_in_jobs_db_path(client: TestClient, db_path: Path) -> None:
    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    assert columns == EXPECTED_COLUMNS
    assert mode.lower() == "wal"


def test_init_schema_is_idempotent_and_keeps_rows(db_path: Path) -> None:
    db.init_schema()
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO jobs (text, analysis, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("hello", "word_count", "pending", "2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z"),
            )
        db.init_schema(conn)
        db.init_schema()
        count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_get_connection_sets_wal_busy_timeout_and_creates_parent(db_path: Path) -> None:
    assert not db_path.parent.exists()
    conn = db.get_connection()
    try:
        assert db_path.parent.is_dir()
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 5000
        assert isinstance(conn.execute("SELECT 1 AS one").fetchone(), sqlite3.Row)
    finally:
        conn.close()


def test_db_path_defaults_to_data_jobs_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JOBS_DB_PATH", raising=False)
    assert db.get_db_path() == Path("data/jobs.db")


# --- CORS -------------------------------------------------------------------------


def test_preflight_from_allowed_origin_gets_allow_origin(client: TestClient) -> None:
    headers = _preflight(client, ALLOWED_ORIGIN)
    assert headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert headers.get("access-control-allow-credentials") is None


def test_preflight_from_other_origin_gets_no_allow_origin(client: TestClient) -> None:
    headers = _preflight(client, OTHER_ORIGIN)
    assert "access-control-allow-origin" not in headers


def test_simple_request_from_other_origin_gets_no_allow_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": OTHER_ORIGIN})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_wildcard_in_cors_origins_is_never_honoured(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with TestClient(create_app()) as c:
        headers = _preflight(c, OTHER_ORIGIN)
        plain = c.get("/health", headers={"Origin": OTHER_ORIGIN})
    assert "access-control-allow-origin" not in headers
    assert "access-control-allow-origin" not in {k.lower() for k in plain.headers}


def test_unset_cors_origins_allows_no_origin(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    with TestClient(create_app()) as c:
        headers = _preflight(c, ALLOWED_ORIGIN)
    assert "access-control-allow-origin" not in headers


def test_parse_cors_origins() -> None:
    assert parse_cors_origins(None) == []
    assert parse_cors_origins("") == []
    assert parse_cors_origins(" * , ") == []
    assert parse_cors_origins("http://a.example:1/, http://b.example:2,http://a.example:1") == [
        "http://a.example:1",
        "http://b.example:2",
    ]


# --- error bodies -----------------------------------------------------------------


def test_unknown_route_answers_error_body(client: TestClient) -> None:
    response = client.get("/no/such/route")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_validation_error_body_does_not_echo_text(client: TestClient) -> None:
    secret = "   \t   "
    response = client.post("/api/jobs", json={"text": secret, "analysis": "word_count"})
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]

    marker = "CONFIDENTIAL-MARKER-TEXT"
    response = client.post("/api/jobs", json={"text": marker, "analysis": "no_such_analysis"})
    assert response.status_code == 422
    assert marker not in response.text
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "", "analysis": "word_count"},
        {"text": "x" * 20001, "analysis": "top_words"},
        {"text": "fine", "analysis": "unknown"},
        {"analysis": "reading_time"},
    ],
)
def test_invalid_job_bodies_answer_422(client: TestClient, payload: dict[str, object]) -> None:
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "x" * 100 not in response.text


def test_unhandled_error_is_generic_500_with_cors_header(app: FastAPI) -> None:
    def explode() -> None:
        raise RuntimeError("leaked detail /home/someone/secret.py")

    app.add_api_route("/boom", explode, methods=["GET"])
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.get("/boom", headers={"Origin": ALLOWED_ORIGIN})
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error"}
    }
    assert "leaked" not in response.text
    assert "Traceback" not in response.text
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


# --- route table ------------------------------------------------------------------


def test_job_routes_are_registered(app: FastAPI) -> None:
    paths = app.openapi()["paths"]
    assert set(paths["/health"]) == {"get"}
    assert set(paths["/api/jobs"]) == {"get", "post"}
    assert set(paths["/api/jobs/{id}"]) == {"get"}
    assert "201" in paths["/api/jobs"]["post"]["responses"]
    assert "/api/jobs/" not in paths


# --- JobOut -----------------------------------------------------------------------


def test_job_out_from_row_decodes_json_result(db_path: Path) -> None:
    db.init_schema()
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO jobs (text, analysis, status, result, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "one two",
                    "word_count",
                    "done",
                    '{"words": 2}',
                    "2026-01-01T12:00:00Z",
                    "2026-01-01T12:00:05Z",
                ),
            )
        row = conn.execute("SELECT * FROM jobs").fetchone()
    finally:
        conn.close()
    job = JobOut.from_row(row)
    assert job.result == {"words": 2}
    assert job.status == "done"
    assert job.error is None
    assert set(job.model_dump()) == EXPECTED_COLUMNS
