"""
Celery task wrappers around the MCP server's async helpers.

`sweep_for_anomalies` is the only scheduled task (celery_app.py beat_schedule).
`simulate_next_day` is registered so it can be enqueued by hand; the demo
itself uses the HTTP `POST /simulate-next-day` path from Overview.
"""

import asyncio

from celery_app import celery_app
from guardrails.engine import run_anomaly_sweep
from simulator import run_simulate_next_day


@celery_app.task(name="tasks.sweep_for_anomalies")
def sweep_for_anomalies():
    return asyncio.run(run_anomaly_sweep())


@celery_app.task(name="tasks.simulate_next_day")
def simulate_next_day():
    return asyncio.run(run_simulate_next_day())
