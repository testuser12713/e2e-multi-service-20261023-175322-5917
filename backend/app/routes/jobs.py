"""Job endpoints: create a job, list all jobs, read one job."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app import db
from app.schemas import JobCreate, JobOut

logger = logging.getLogger("app.jobs")

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# 20000 characters of 4-byte UTF-8 plus JSON overhead stay well below this bound.
MAX_BODY_BYTES = 1024 * 1024

_TOO_LARGE = {"code": "payload_too_large", "message": "Request body too large"}


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _read_bounded_body(request: Request) -> bytes:
    """Read the body, refusing anything above MAX_BODY_BYTES before buffering it."""
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > MAX_BODY_BYTES:
                raise HTTPException(status_code=413, detail=_TOO_LARGE)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"code": "bad_request", "message": "Invalid Content-Length"},
            ) from None
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail=_TOO_LARGE)
        chunks.append(chunk)
    return b"".join(chunks)


def _insert_job(payload: JobCreate) -> JobOut:
    now = _now_iso()
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO jobs (text, analysis, status, result, error, created_at, updated_at)"
                " VALUES (?, ?, 'pending', NULL, NULL, ?, ?)",
                (payload.text, payload.analysis, now, now),
            )
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()
    return JobOut.from_row(row)


@router.post(
    "",
    response_model=JobOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": JobCreate.model_json_schema()}},
        }
    },
)
async def create_job(request: Request) -> JobOut:
    """Store a new job in status 'pending' and return it."""
    body = await _read_bounded_body(request)
    try:
        payload = JobCreate.model_validate_json(body)
    except ValidationError as exc:
        # The handler formats only location and message, never the rejected input.
        raise RequestValidationError(exc.errors(include_input=False)) from None
    job = await run_in_threadpool(_insert_job, payload)
    logger.info("job %s created status=%s", job.id, job.status)
    return job


@router.get("", response_model=list[JobOut])
def list_jobs() -> list[JobOut]:
    """Return all jobs, newest first (created_at desc, id desc)."""
    conn = db.get_connection()
    try:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC, id DESC").fetchall()
    finally:
        conn.close()
    return [JobOut.from_row(r) for r in rows]


@router.get("/{id}", response_model=JobOut)
def get_job(id: int) -> JobOut:
    """Return one job; an unknown id answers 404."""
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Job not found"}
        )
    return JobOut.from_row(row)
