"""SQLite access for the API.

The API and the worker share one SQLite file whose path comes from ``JOBS_DB_PATH``.
Both services carry the same ``CREATE TABLE IF NOT EXISTS`` statement, so whichever
process starts first creates the schema and the other one finds it in place.

Every connection switches the database to WAL mode and sets a busy timeout, so a
reader never blocks the writer and a short write lock held by the other process is
waited for instead of failing with ``database is locked``.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = "data/jobs.db"
BUSY_TIMEOUT_MS = 5000

JOBS_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    analysis TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def get_db_path() -> Path:
    """Return the database path from ``JOBS_DB_PATH`` (default ``data/jobs.db``, from cwd)."""
    raw = os.environ.get("JOBS_DB_PATH", "").strip()
    return Path(raw or DEFAULT_DB_PATH)


def get_connection() -> sqlite3.Connection:
    """Open a connection to the shared jobs database.

    The parent directory is created when it does not exist yet. Rows come back as
    :class:`sqlite3.Row`, so columns can be read by name. The connection may be used
    from another thread than the one that opened it (FastAPI runs sync dependencies
    and endpoints in a thread pool), but it must not be shared between requests.
    """
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        path,
        timeout=BUSY_TIMEOUT_MS / 1000,
        check_same_thread=False,
    )
    try:
        conn.row_factory = sqlite3.Row
        # busy_timeout (= BUSY_TIMEOUT_MS) first: switching to WAL needs a lock the
        # other process may hold. PRAGMAs take no bound parameters, hence the literal.
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.Error:
        conn.close()
        raise
    return conn


def init_schema(conn: sqlite3.Connection | None = None) -> None:
    """Create the ``jobs`` table if it does not exist. Safe to call any number of times.

    Uses the given connection, or opens (and closes) its own one when none is passed.
    """
    own = conn is None
    target = get_connection() if conn is None else conn
    try:
        with target:
            target.execute(JOBS_DDL)
    finally:
        if own:
            target.close()
