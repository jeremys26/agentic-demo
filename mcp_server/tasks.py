"""
Celery task wrappers around the MCP server's async helpers.

`sweep_for_anomalies` is the scheduled task (celery_app.py beat_schedule).
Simulate Next Day is HTTP-only (`POST /simulate-next-day` from Overview).
"""

import asyncio

from celery_app import celery_app
from guardrails.engine import run_anomaly_sweep


@celery_app.task(name="tasks.sweep_for_anomalies")
def sweep_for_anomalies():
    return asyncio.run(run_anomaly_sweep())
