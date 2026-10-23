"""The job worker: claims pending jobs from the shared SQLite database, runs the
requested text analysis and writes result and status back.

Start it with ``python -m worker`` (``--once`` drains the pending jobs and exits).
"""
