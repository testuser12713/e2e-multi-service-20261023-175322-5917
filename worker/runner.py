"""The worker's processing loop.

``run_once`` drains the pending jobs, ``run_forever`` polls for new ones every
``interval`` seconds until the process is stopped. Log lines carry only the job id,
its status and an error class — never the job text.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any

from .analyses import ANALYSES
from .db import claim_next_job, fail_job, finish_job

logger = logging.getLogger(__name__)


def process_job(conn: sqlite3.Connection, job: dict[str, Any]) -> None:
    """Run the job's analysis and store its result ('done') or its error ('failed').

    Never raises for an analysis failure: the job is marked failed with a short
    message (error class plus a fixed description — no traceback, path or job text).
    """
    job_id = job["id"]
    fn = ANALYSES.get(job.get("analysis", ""))
    if fn is None:
        fail_job(conn, job_id, "UnknownAnalysis: analysis is not supported")
        logger.warning("job %s failed (UnknownAnalysis)", job_id)
        return
    try:
        result = fn(job["text"])
    except Exception as exc:
        name = type(exc).__name__
        fail_job(conn, job_id, f"{name}: analysis raised an error")
        logger.warning("job %s failed (%s)", job_id, name)
        return
    finish_job(conn, job_id, result)
    logger.info("job %s done", job_id)


def run_once(conn: sqlite3.Connection) -> int:
    """Process every pending job and return how many were processed."""
    count = 0
    while (job := claim_next_job(conn)) is not None:
        logger.info("job %s running", job["id"])
        process_job(conn, job)
        count += 1
    return count


def run_forever(conn: sqlite3.Connection, interval: float) -> None:
    """Poll for pending jobs every ``interval`` seconds until the process is stopped."""
    logger.info("worker idle, polling every %.1f s", interval)
    while True:
        run_once(conn)
        time.sleep(interval)
