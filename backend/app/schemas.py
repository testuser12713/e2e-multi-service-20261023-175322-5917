"""Request and response models of the job API."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TEXT_MAX_LENGTH = 20000

Analysis = Literal["word_count", "top_words", "reading_time"]
JobStatus = Literal["pending", "running", "done", "failed"]


class JobCreate(BaseModel):
    """Body of ``POST /api/jobs``."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(min_length=1, max_length=TEXT_MAX_LENGTH)
    analysis: Analysis

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        # The message never repeats the submitted text.
        if not value.strip():
            raise ValueError("text must not be empty or whitespace only")
        return value


class JobOut(BaseModel):
    """A job as the API returns it (one row of the ``jobs`` table)."""

    id: int
    text: str
    # Plain string on output: a row with an analysis the worker does not know ends as
    # 'failed' and must still be listable instead of breaking the whole response.
    analysis: str
    status: JobStatus
    result: Any | None = None
    error: str | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any] | sqlite3.Row) -> JobOut:
        """Build a job from a ``jobs`` row; ``result`` is stored there as JSON text."""
        raw_result = row["result"]
        result: Any | None = None
        if raw_result is not None:
            try:
                result = json.loads(raw_result)
            except (TypeError, ValueError):
                result = None
        return cls(
            id=row["id"],
            text=row["text"],
            analysis=row["analysis"],
            status=row["status"],
            result=result,
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
