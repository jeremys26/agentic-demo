"""
RankPulse-sim — a small, standalone stand-in for a newly-acquired SEO
analytics platform (PLANNING.md §14 phase 10, the "live fifth-platform
onboarding demo"). Deliberately built as a single-file FastAPI service, not
a fifth full Django project like the four core sim platforms in services/ —
the point of this demo is that an acquisition brings its own pre-existing
stack, not another copy of BMG360's own tooling.

This service runs continuously alongside the other four (docker-compose.yml)
the whole time — a newly-acquired company's system doesn't wait for anyone.
What's deliberately NOT done yet is wiring it into the agent's tool
registry: see mcp_server/tools/rankpulse.py and the commented-out import in
mcp_server/main.py. Onboarding it live is one import line plus a container
restart — no other code changes — which is the thing being demonstrated.
"""

import datetime
import random

from fastapi import FastAPI, Query

app = FastAPI(title="RankPulse-sim")

DEMO_START = datetime.date(2026, 8, 1)
WEEKS = 4
CAMPAIGN_IDS = range(1, 7)  # matches OneSource360-sim's 6 seeded campaign ids


def _generate_weekly(campaign_id: int) -> list[dict]:
    """Deterministic per campaign (same random.seed(360) convention the real
    seed_data commands use elsewhere in this repo) — no anomaly baked in
    here, since organic search isn't part of PLANNING.md §9's root-cause
    story; this platform exists to demonstrate onboarding, not to add a
    second scenario."""
    rng = random.Random(360 + campaign_id)
    sessions = rng.randint(900, 2200)
    rank = round(rng.uniform(3.0, 9.0), 1)
    weekly = []
    for week in range(WEEKS):
        sessions = max(200, round(sessions * rng.uniform(0.92, 1.08)))
        rank = round(max(1.0, rank + rng.uniform(-0.4, 0.3)), 1)
        conversions = max(0, round(sessions * rng.uniform(0.01, 0.025)))
        weekly.append(
            {
                "week_start": (DEMO_START + datetime.timedelta(weeks=week)).isoformat(),
                "organic_sessions": sessions,
                "organic_conversions": conversions,
                "avg_keyword_rank": rank,
            }
        )
    return weekly


_DATA = {cid: _generate_weekly(cid) for cid in CAMPAIGN_IDS}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/inspect/")
def inspect_tables():
    """In-memory snapshot for the Systems inspector — RankPulse-sim has no Postgres."""
    columns = [
        {"name": "campaign_id", "type": "Integer", "nullable": False, "primary_key": False},
        {"name": "week_start", "type": "Date", "nullable": False, "primary_key": False},
        {"name": "organic_sessions", "type": "Integer", "nullable": False, "primary_key": False},
        {"name": "organic_conversions", "type": "Integer", "nullable": False, "primary_key": False},
        {"name": "avg_keyword_rank", "type": "Float", "nullable": False, "primary_key": False},
    ]
    rows = []
    for campaign_id, weekly in _DATA.items():
        for week in weekly:
            rows.append({"campaign_id": campaign_id, **week})
    return {
        "database": None,
        "tables": [
            {
                "model": "OrganicPerformanceWeekly",
                "db_table": "(in-memory — RankPulse-sim has no Postgres)",
                "app_label": "rankpulse",
                "columns": columns,
                "total": len(rows),
                "offset": 0,
                "limit": len(rows),
                "rows": rows,
            }
        ],
    }


@app.get("/api/organic-performance/")
def organic_performance(campaign_id: int = Query(...)):
    weekly = _DATA.get(campaign_id)
    if weekly is None:
        return {"campaign_id": campaign_id, "weekly": [], "summary": None}

    total_conversions = sum(w["organic_conversions"] for w in weekly)
    avg_rank = round(sum(w["avg_keyword_rank"] for w in weekly) / len(weekly), 1)
    trend = "improving" if weekly[-1]["avg_keyword_rank"] < weekly[0]["avg_keyword_rank"] else "steady"

    return {
        "campaign_id": campaign_id,
        "weekly": weekly,
        "summary": {
            "avg_keyword_rank": avg_rank,
            "total_organic_conversions": total_conversions,
            "trend": trend,
        },
    }
