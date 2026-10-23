"""Entry point of the worker: ``python -m worker [--once]``.

Opens the shared jobs database (``JOBS_DB_PATH``, default ``data/jobs.db``), creates
the schema if the API has not done so yet — retrying with a bounded backoff while the
file is busy — and then either drains the pending jobs once (``--once``) or polls for
new jobs every ``WORKER_POLL_INTERVAL_SECONDS`` seconds (default 2).

Log lines carry only job id, status and error class — never job text.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import signal
import sqlite3
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from types import FrameType

from . import runner
from .db import DB_PATH_ENV, PathLike, get_connection, init_schema, resolve_db_path

logger = logging.getLogger("worker")

POLL_INTERVAL_ENV = "WORKER_POLL_INTERVAL_SECONDS"
DEFAULT_POLL_INTERVAL = 2.0

OPEN_ATTEMPTS = 6
OPEN_BASE_DELAY = 0.5
OPEN_MAX_DELAY = 8.0


class ConfigError(ValueError):
    """A configuration variable holds a value the worker cannot use."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m worker",
        description=(
            "Claims pending text-analysis jobs from the shared SQLite database "
            f"({DB_PATH_ENV}), runs the analysis and stores result and status. "
            f"Polls every {POLL_INTERVAL_ENV} seconds (default 2)."
        ),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="process all pending jobs, then exit with code 0",
    )
    return parser


def read_poll_interval(environ: Mapping[str, str] | None = None) -> float:
    """Return the poll interval in seconds from ``WORKER_POLL_INTERVAL_SECONDS``.

    Unset or empty means the default of 2 seconds; anything that is not a positive,
    finite number raises :class:`ConfigError` naming the variable.
    """
    env = os.environ if environ is None else environ
    raw = (env.get(POLL_INTERVAL_ENV) or "").strip()
    if not raw:
        return DEFAULT_POLL_INTERVAL
    try:
        value = float(raw)
    except ValueError:
        raise ConfigError(
            f"{POLL_INTERVAL_ENV} must be a positive number of seconds, got {raw!r}"
        ) from None
    if not math.isfinite(value) or value <= 0:
        raise ConfigError(f"{POLL_INTERVAL_ENV} must be a positive number of seconds, got {raw!r}")
    return value


def open_database(
    path: PathLike,
    *,
    attempts: int = OPEN_ATTEMPTS,
    base_delay: float = OPEN_BASE_DELAY,
    max_delay: float = OPEN_MAX_DELAY,
    sleep: Callable[[float], None] = time.sleep,
) -> sqlite3.Connection:
    """Open the database and create the schema, retrying while SQLite is busy.

    The API may be creating the same file at the same moment, so a
    ``sqlite3.OperationalError`` (e.g. "database is locked") is retried up to
    ``attempts`` times with an exponential backoff capped at ``max_delay`` seconds.
    Each wait is logged with the error class only. The last error is re-raised.
    """
    attempts = max(1, attempts)
    delay = base_delay
    for attempt in range(1, attempts + 1):
        conn: sqlite3.Connection | None = None
        try:
            conn = get_connection(path)
            init_schema(conn)
            return conn
        except sqlite3.OperationalError as exc:
            if conn is not None:
                conn.close()
            if attempt == attempts:
                raise
            logger.warning(
                "database not ready (%s), retry %d/%d in %.1f s",
                type(exc).__name__,
                attempt,
                attempts - 1,
                delay,
            )
            sleep(delay)
            delay = min(delay * 2, max_delay)
    raise RuntimeError("unreachable: the retry loop either returns or raises")


def _stop_on_sigterm() -> None:
    """Turn SIGTERM into a normal exit so the connection is closed cleanly."""

    def handle(signum: int, frame: FrameType | None) -> None:
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        interval = read_poll_interval()
    except ConfigError as exc:
        logger.error("invalid configuration: %s", exc)
        return 2

    try:
        conn = open_database(resolve_db_path())
    except (sqlite3.Error, OSError) as exc:
        logger.error(
            "could not open the jobs database (%s); check %s",
            type(exc).__name__,
            DB_PATH_ENV,
        )
        return 1
    logger.info("jobs schema ready")

    try:
        if args.once:
            processed = runner.run_once(conn)
            logger.info("processed %d job(s), exiting", processed or 0)
        else:
            _stop_on_sigterm()
            runner.run_forever(conn, interval)
    except KeyboardInterrupt:
        logger.info("worker stopped")
    except sqlite3.Error as exc:
        logger.error("worker stopped on a database error (%s)", type(exc).__name__)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
