"""Job endpoints: create a job, list all jobs, read one job."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas import JobCreate, JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_PENDING = "ticket #6 implements this endpoint"


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate) -> JobOut:
    """Store a new job in status 'pending' and return it."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_PENDING)


@router.get("", response_model=list[JobOut])
def list_jobs() -> list[JobOut]:
    """Return all jobs, newest first (created_at desc, id desc)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_PENDING)


@router.get("/{id}", response_model=JobOut)
def get_job(id: int) -> JobOut:
    """Return one job; an unknown id answers 404."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_PENDING)
