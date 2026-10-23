"""Tests for the worker skeleton: database helpers and the ``python -m worker`` entry."""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

import worker.__main__ as worker_main
from worker import db

REPO_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_COLUMNS = [
    "id",
    "text",
    "analysis",
    "status",
    "result",
    "error",
    "created_at",
    "updated_at",
]


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "jobs.db"


@pytest.fixture
def conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = db.get_connection(db_path)
    try:
        yield connection
    finally:
        connection.close()


def _columns(conn: sqlite3.Connection) -> list[str]:
    return [row["name"] for row in conn.execute("PRAGMA table_info(jobs)")]


def _run_worker(*args: str, env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **env_extra}
    return subprocess.run(
        [sys.executable, "-m", "worker", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_init_schema_creates_contract_table(conn: sqlite3.Connection) -> None:
    db.init_schema(conn)

    assert _columns(conn) == CONTRACT_COLUMNS


def test_init_schema_is_idempotent_and_keeps_rows(conn: sqlite3.Connection) -> None:
    db.init_schema(conn)
    conn.execute(
        "INSERT INTO jobs (text, analysis) VALUES (?, ?)",
        ("hello world", "word_count"),
    )

    db.init_schema(conn)
    db.init_schema(conn)

    assert _columns(conn) == CONTRACT_COLUMNS
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1


def test_schema_defaults_match_contract(conn: sqlite3.Connection) -> None:
    db.init_schema(conn)
    conn.execute(
        "INSERT INTO jobs (text, analysis) VALUES (?, ?)",
        ("some text", "top_words"),
    )

    row = conn.execute("SELECT * FROM jobs").fetchone()

    assert row["status"] == "pending"
    assert row["result"] is None
    assert row["error"] is None
    iso_utc = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    assert iso_utc.match(row["created_at"])
    assert iso_utc.match(row["updated_at"])


def test_schema_rejects_unknown_status(conn: sqlite3.Connection) -> None:
    db.init_schema(conn)

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO jobs (text, analysis, status) VALUES (?, ?, ?)",
            ("x", "word_count", "lost"),
        )


def test_schema_created_by_one_connection_is_seen_by_another(db_path: Path) -> None:
    first = db.get_connection(db_path)
    second = db.get_connection(db_path)
    try:
        db.init_schema(first)
        first.execute("INSERT INTO jobs (text, analysis) VALUES (?, ?)", ("a b", "word_count"))

        db.init_schema(second)

        assert second.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    finally:
        first.close()
        second.close()


def test_connection_enables_wal(conn: sqlite3.Connection) -> None:
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert mode.lower() == "wal"


def test_connection_sets_busy_timeout(conn: sqlite3.Connection) -> None:
    timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]

    assert timeout_ms >= 5000


def test_get_connection_creates_missing_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "data" / "jobs.db"

    connection = db.get_connection(path)
    try:
        db.init_schema(connection)
    finally:
        connection.close()

    assert path.is_file()


def test_writer_waits_for_a_short_lock_instead_of_failing(db_path: Path) -> None:
    setup = db.get_connection(db_path)
    db.init_schema(setup)
    setup.close()
    # Stands in for the other process holding the write lock for a moment.
    holder = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    writer = db.get_connection(db_path)
    try:
        holder.execute("BEGIN IMMEDIATE")
        holder.execute("INSERT INTO jobs (text, analysis) VALUES (?, ?)", ("held", "word_count"))

        # WAL: a reader is not blocked by the open write transaction.
        assert writer.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0

        releaser = threading.Timer(0.3, lambda: holder.execute("COMMIT"))
        releaser.start()
        started = time.monotonic()
        writer.execute("INSERT INTO jobs (text, analysis) VALUES (?, ?)", ("waited", "word_count"))
        waited = time.monotonic() - started
        releaser.join(timeout=10)

        assert writer.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 2
        assert waited < 5.0
    finally:
        writer.close()
        holder.close()


def test_resolve_db_path_defaults_to_data_jobs_db() -> None:
    assert db.resolve_db_path({}) == "data/jobs.db"
    assert db.resolve_db_path({"JOBS_DB_PATH": "   "}) == "data/jobs.db"


def test_resolve_db_path_reads_jobs_db_path() -> None:
    assert db.resolve_db_path({"JOBS_DB_PATH": "/srv/shared/jobs.db"}) == "/srv/shared/jobs.db"


def test_read_poll_interval_defaults_to_two_seconds() -> None:
    assert worker_main.read_poll_interval({}) == pytest.approx(2.0)


def test_read_poll_interval_reads_the_variable() -> None:
    env = {"WORKER_POLL_INTERVAL_SECONDS": "0.5"}

    assert worker_main.read_poll_interval(env) == pytest.approx(0.5)


@pytest.mark.parametrize("raw", ["abc", "0", "-1", "nan", "inf"])
def test_read_poll_interval_rejects_unusable_values(raw: str) -> None:
    with pytest.raises(worker_main.ConfigError, match="WORKER_POLL_INTERVAL_SECONDS"):
        worker_main.read_poll_interval({"WORKER_POLL_INTERVAL_SECONDS": raw})


def test_open_database_retries_while_locked_then_creates_schema(
    db_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    real_get_connection = db.get_connection
    calls = {"n": 0}

    def flaky_get_connection(path: db.PathLike) -> sqlite3.Connection:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise sqlite3.OperationalError("database is locked")
        return real_get_connection(path)

    monkeypatch.setattr(worker_main, "get_connection", flaky_get_connection)
    waits: list[float] = []

    with caplog.at_level("WARNING", logger="worker"):
        connection = worker_main.open_database(db_path, base_delay=0.5, sleep=waits.append)
    try:
        assert _columns(connection) == CONTRACT_COLUMNS
    finally:
        connection.close()

    assert calls["n"] == 3
    assert len(waits) == 2
    assert waits[1] > waits[0]
    warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 2
    assert all("OperationalError" in message for message in warnings)


def test_open_database_gives_up_after_bounded_attempts(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def always_locked(path: db.PathLike) -> sqlite3.Connection:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(worker_main, "get_connection", always_locked)
    waits: list[float] = []

    with pytest.raises(sqlite3.OperationalError):
        worker_main.open_database(
            db_path, attempts=4, base_delay=1.0, max_delay=2.0, sleep=waits.append
        )

    assert len(waits) == 3
    assert max(waits) <= 2.0


def test_help_exits_zero(tmp_path: Path) -> None:
    result = _run_worker("--help", env_extra={"JOBS_DB_PATH": str(tmp_path / "jobs.db")})

    assert result.returncode == 0, result.stderr
    assert "--once" in result.stdout


def test_once_creates_schema_at_jobs_db_path_and_exits_zero(tmp_path: Path) -> None:
    path = tmp_path / "shared" / "jobs.db"

    result = _run_worker("--once", env_extra={"JOBS_DB_PATH": str(path)})

    assert result.returncode == 0, result.stderr
    assert path.is_file()
    connection = sqlite3.connect(path)
    try:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(jobs)")]
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        connection.close()
    assert columns == CONTRACT_COLUMNS
    assert mode.lower() == "wal"


def test_invalid_poll_interval_refuses_to_start_and_names_the_variable(tmp_path: Path) -> None:
    result = _run_worker(
        env_extra={
            "JOBS_DB_PATH": str(tmp_path / "jobs.db"),
            "WORKER_POLL_INTERVAL_SECONDS": "soon",
        },
    )

    assert result.returncode != 0
    assert "WORKER_POLL_INTERVAL_SECONDS" in result.stderr
