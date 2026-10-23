"""SQLite access for the worker.

The worker shares one SQLite file with the API (``JOBS_DB_PATH``). Every connection
switches the database to WAL mode and sets a busy timeout, so a reader never blocks
the writer and a short write lock held by the other process is waited for instead of
failing with "database is locked". The schema is created idempotently with the same
``CREATE TABLE IF NOT EXISTS`` statement the API uses, so whichever process starts
first creates it and the other finds it in place.

All statements are parameterized; no job value is ever formatted into SQL.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Mapping
from typing import Any

DB_PATH_ENV = "JOBS_DB_PATH"
DEFAULT_DB_PATH = "data/jobs.db"
BUSY_TIMEOUT_MS = 5000

JOB_STATUSES = ("pending", "running", "done", "failed")

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    analysis TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'done', 'failed')),
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
)
"""

PathLike = str | os.PathLike[str]


def resolve_db_path(environ: Mapping[str, str] | None = None) -> str:
    """Return the database path from ``JOBS_DB_PATH``, else ``data/jobs.db``.

    A relative path is resolved against the current working directory, exactly as
    SQLite itself resolves it.
    """
    env = os.environ if environ is None else environ
    value = (env.get(DB_PATH_ENV) or "").strip()
    return value or DEFAULT_DB_PATH


def _ensure_parent_dir(path: PathLike) -> None:
    raw = os.fspath(path)
    if raw == ":memory:":
        return
    parent = os.path.dirname(raw)
    if parent:
        os.makedirs(parent, exist_ok=True)


def get_connection(path: PathLike | None = None) -> sqlite3.Connection:
    """Open the jobs database with WAL journaling and a busy timeout.

    ``path`` defaults to :func:`resolve_db_path`. The parent directory is created
    when missing. The connection runs in autocommit mode (``isolation_level=None``):
    a single statement commits on its own, and a multi-statement unit opens its
    transaction explicitly (``BEGIN IMMEDIATE`` ... ``COMMIT``). Rows come back as
    :class:`sqlite3.Row`, so ``dict(row)`` yields a job mapping.
    """
    db_path = resolve_db_path() if path is None else path
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(
        db_path,
        timeout=BUSY_TIMEOUT_MS / 1000,
        isolation_level=None,
    )
    try:
        conn.row_factory = sqlite3.Row
        # PRAGMAs take no bound parameters; the literal must equal BUSY_TIMEOUT_MS.
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.Error:
        conn.close()
        raise
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the ``jobs`` table when it does not exist yet. Safe to call repeatedly."""
    conn.execute(SCHEMA_DDL)


def claim_next_job(conn: sqlite3.Connection) -> dict[str, Any] | None:
    """Atomically move the oldest pending job to 'running' and return it.

    Returns the claimed job as a dict, or ``None`` when no job is pending.
    """
    return None


def finish_job(conn: sqlite3.Connection, job_id: int, result: Any) -> None:
    """Store ``result`` (a JSON value) for the job and set its status to 'done'."""
    return None


def fail_job(conn: sqlite3.Connection, job_id: int, error: str) -> None:
    """Store the short ``error`` message for the job and set its status to 'failed'."""
    return None
