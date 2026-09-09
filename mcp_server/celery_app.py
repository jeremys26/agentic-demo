"""
Celery + Redis, hosted alongside the MCP server itself rather than as a
separate, unowned component (PLANNING.md §8/§14 phase 7) — only the MCP
server has a clean, already-built reason to read across all four sim
services, so the anomaly sweep belongs here. Two extra containers run this
(docker-compose.yml's celery_worker and celery_beat), both built from this
same mcp_server image, so the task code (tasks.py) always matches whatever
version of guardrails/engine.py the API server is running.
"""

import os
import sys
from pathlib import Path

# Prefork children do not always keep cwd on sys.path, so sibling packages
# (tools, guardrails) fail inside tasks unless the app root is explicit.
_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("agent360", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.timezone = "UTC"
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.beat_schedule = {
    "sweep-for-anomalies": {
        "task": "tasks.sweep_for_anomalies",
        "schedule": float(os.environ.get("ANOMALY_SWEEP_INTERVAL_SECONDS", 300)),
    },
}

import tasks  # noqa: E402, F401 — registers sweep_for_anomalies + simulate_next_day
