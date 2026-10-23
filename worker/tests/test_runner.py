"""Tests for claiming, failure handling and the run loop."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from worker import analyses, db, runner

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "jobs.db"


@pytest.fixture
def conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    c = db.get_connection(db_path)
    db.init_schema(c)
    try:
        yield c
    finally:
        c.close()


def _add(conn: sqlite3.Connection, text: str, analysis: str) -> int:
    cur = conn.execute("INSERT INTO jobs (text, analysis) VALUES (?, ?)", (text, analysis))
    return int(cur.lastrowid)


def _job(conn: sqlite3.Connection, job_id: int) -> dict:
    return dict(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())


def test_claim_never_returns_same_job_twice(conn: sqlite3.Connection, db_path: Path) -> None:
    ids = {_add(conn, "a b", "word_count") for _ in range(4)}
    other = db.get_connection(db_path)
    try:
        claimed = []
        for c in [conn, other] * 3:
            job = db.claim_next_job(c)
            if job:
                assert job["status"] == "running"
                claimed.append(job["id"])
    finally:
        other.close()
    assert sorted(claimed) == sorted(ids)
    assert db.claim_next_job(conn) is None


def test_run_once_processes_all(conn: sqlite3.Connection) -> None:
    a = _add(conn, "Hi there hi", "top_words")
    b = _add(conn, "one two", "word_count")
    assert runner.run_once(conn) == 2
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0] == 0
    ja = _job(conn, a)
    assert ja["status"] == "done"
    assert json.loads(ja["result"])["top_words"][0] == {"word": "hi", "count": 2}
    assert json.loads(_job(conn, b)["result"]) == {"words": 2}


def test_unknown_analysis_fails_and_continues(conn: sqlite3.Connection) -> None:
    bad = _add(conn, "secret text", "nope")
    good = _add(conn, "x", "word_count")
    assert runner.run_once(conn) == 2
    j = _job(conn, bad)
    assert j["status"] == "failed"
    assert j["error"] and "secret" not in j["error"]
    assert _job(conn, good)["status"] == "done"


def test_raising_analysis_fails(conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(text: str) -> dict:
        raise ValueError(f"bad {text} at /etc/passwd")

    monkeypatch.setitem(analyses.ANALYSES, "word_count", boom)
    jid = _add(conn, "private words", "word_count")
    runner.run_once(conn)
    j = _job(conn, jid)
    assert j["status"] == "failed"
    assert j["error"].startswith("ValueError")
    assert "private" not in j["error"] and "/" not in j["error"]
    assert "Traceback" not in j["error"]


def test_cli_once_exits_zero(db_path: Path) -> None:
    c = db.get_connection(db_path)
    db.init_schema(c)
    jid = _add(c, "a b c", "reading_time")
    c.close()
    proc = subprocess.run(
        [sys.executable, "-m", "worker", "--once"],
        cwd=REPO_ROOT,
        env={**os.environ, "JOBS_DB_PATH": str(db_path)},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0
    assert "a b c" not in proc.stderr
    c = db.get_connection(db_path)
    try:
        assert _job(c, jid)["status"] == "done"
    finally:
        c.close()
