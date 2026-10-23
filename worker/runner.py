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

logger = logging.getLogger(__name__)


def process_job(conn: sqlite3.Connection, job: dict[str, Any]) -> None:
    """Run the job's analysis and store its result ('done') or its error ('failed')."""
    return None


def run_once(conn: sqlite3.Connection) -> int:
    """Process every pending job and return how many were processed."""
    return 0


def run_forever(conn: sqlite3.Connection, interval: float) -> None:
    """Poll for pending jobs every ``interval`` seconds until the process is stopped."""
    logger.info("worker idle, polling every %.1f s", interval)
    while True:
        run_once(conn)
        time.sleep(interval)
