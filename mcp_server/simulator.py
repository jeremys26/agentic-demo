"""
Live "Simulate Next Day" event generator (PLANNING.md §9).

Posts a new day's payloads to each sim service's own webhook — OneSource360
(warehouse rollup), SmartSpot360 (spots), Captivator360 (creative metrics),
Maestro360 (call events) — rather than writing into their databases from
here. Continues the seeded §9 pattern: campaign 1 stays in the spiked-CPL /
declining-CTR / Pool-B-overflow regime; other warehouse campaigns stay
steady. Idempotent: each receiver skips a date it already has.
"""

from __future__ import annotations

import os
import random
from datetime import date, datetime, timedelta, timezone

from http_client import service_client

ONESOURCE360_URL = os.environ.get("ONESOURCE360_URL", "http://onesource360:8000")
SMARTSPOT360_URL = os.environ.get("SMARTSPOT360_URL", "http://smartspot360:8000")
CAPTIVATOR360_URL = os.environ.get("CAPTIVATOR360_URL", "http://captivator360:8000")
MAESTRO360_URL = os.environ.get("MAESTRO360_URL", "http://maestro360:8000")

FLAGGED_CAMPAIGN_ID = 1
DEFAULT_NEXT_DATE = date(2026, 8, 29)  # day after the 28-day seed window


def latest_rollup_date(rollups: list[dict]) -> date | None:
    if not rollups:
        return None
    return max(date.fromisoformat(row["date"]) for row in rollups)


def next_sim_date(rollups: list[dict]) -> date:
    latest = latest_rollup_date(rollups)
    if latest is None:
        return DEFAULT_NEXT_DATE
    return latest + timedelta(days=1)


def build_onesource_rollups(campaigns: list[dict], sim_date: date, rng: random.Random) -> list[dict]:
    rows = []
    for campaign in campaigns:
        target = float(campaign["target_cpl"])
        if campaign["id"] == FLAGGED_CAMPAIGN_ID:
            spend = round(rng.uniform(7100, 7250), 2)
            leads = rng.randint(100, 112)
            cpl = round(spend / leads, 2)
            calls = round(leads * rng.uniform(1.4, 1.6))
            conversions = round(leads * rng.uniform(0.55, 0.65))
        else:
            daily_budget = target * rng.uniform(140, 170)
            spend = round(daily_budget * rng.uniform(0.94, 1.06), 2)
            cpl = round(target * rng.uniform(0.92, 1.08), 2)
            leads = max(1, round(spend / cpl))
            calls = round(leads * rng.uniform(1.3, 1.6))
            conversions = round(leads * rng.uniform(0.45, 0.60))
        rows.append(
            {
                "campaign_id": campaign["id"],
                "date": sim_date.isoformat(),
                "spend": spend,
                "leads": leads,
                "calls": calls,
                "conversions": conversions,
                "cpl": cpl,
            }
        )
    return rows


def build_smartspot_spots(template_spots: list[dict], sim_date: date, rng: random.Random) -> list[dict]:
    seen: set[tuple[int, int]] = set()
    rows = []
    for spot in reversed(template_spots):
        key = (spot["station"], spot["daypart"])
        if key in seen:
            continue
        seen.add(key)
        cost = round(float(spot["cost"]) * rng.uniform(0.95, 1.05), 2)
        conversions = rng.randint(3, 6)
        rows.append(
            {
                "campaign_id": spot["campaign_id"],
                "station_id": spot["station"],
                "daypart_id": spot["daypart"],
                "cost": cost,
                "creative_label": spot.get("creative_label") or "CR-114",
                "calls": rng.randint(8, 14),
                "conversions": conversions,
                "cpl": round(cost / max(conversions, 1), 2),
            }
        )
    return list(reversed(rows))


def build_creative_metrics(latest_by_creative: dict[int, dict], sim_date: date, rng: random.Random) -> list[dict]:
    rows = []
    for creative_id, latest in latest_by_creative.items():
        ctr = max(0.008, float(latest["ctr"]) + rng.uniform(-0.001, 0.0))
        conversion_rate = max(0.02, float(latest["conversion_rate"]) + rng.uniform(-0.003, 0.0))
        rows.append(
            {
                "creative_id": creative_id,
                "impressions": rng.randint(22000, 28000),
                "ctr": round(ctr, 4),
                "conversion_rate": round(conversion_rate, 4),
            }
        )
    return rows


def build_call_events(
    campaign_id: int, pools: list[dict], sim_date: date, rng: random.Random, daily_calls: int = 200
) -> list[dict]:
    pool_a = next((p for p in pools if p.get("is_certified_medicare")), pools[0] if pools else None)
    pool_b = next((p for p in pools if not p.get("is_certified_medicare")), pool_a)
    if pool_a is None:
        return []
    events = []
    for _ in range(daily_calls):
        pool = pool_b if rng.random() < 0.35 else pool_a
        hour = rng.randint(8, 19)
        minute = rng.randint(0, 59)
        ts = datetime.combine(sim_date, datetime.min.time(), tzinfo=timezone.utc).replace(
            hour=hour, minute=minute
        )
        conversion_rate = float(pool.get("historical_conversion_rate") or (0.31 if pool is pool_a else 0.18))
        roll = rng.random()
        if roll < conversion_rate:
            outcome, duration = "conversion", rng.randint(180, 600)
        elif roll < conversion_rate + 0.15:
            outcome, duration = "voicemail", rng.randint(15, 60)
        elif roll < conversion_rate + 0.25:
            outcome, duration = "dropped", rng.randint(5, 30)
        else:
            outcome, duration = "no_answer", 0
        events.append(
            {
                "campaign_id": campaign_id,
                "timestamp": ts.isoformat(),
                "routed_pool_id": pool["id"],
                "wait_time_seconds": rng.randint(5, 120),
                "duration_seconds": duration,
                "outcome": outcome,
            }
        )
    return events


async def _get_json(client, url: str, **kwargs) -> dict | list:
    response = await client.get(url, **kwargs)
    response.raise_for_status()
    return response.json()


async def run_simulate_next_day() -> dict:
    rng = random.Random(360)
    async with service_client() as client:
        campaigns = await _get_json(client, f"{ONESOURCE360_URL}/api/campaigns/")
        flagged_perf = await _get_json(
            client, f"{ONESOURCE360_URL}/api/performance/", params={"campaign_id": FLAGGED_CAMPAIGN_ID}
        )
        sim_date = next_sim_date(flagged_perf.get("daily_rollups") or [])
        rng.seed(360 + sim_date.toordinal())

        onesource_payload = {"rollups": build_onesource_rollups(campaigns, sim_date, rng)}
        onesource = await client.post(
            f"{ONESOURCE360_URL}/api/webhooks/daily-performance/", json=onesource_payload
        )
        onesource.raise_for_status()

        spots = await _get_json(
            client, f"{SMARTSPOT360_URL}/api/spots/", params={"campaign_id": FLAGGED_CAMPAIGN_ID}
        )
        smartspot_body = {"date": sim_date.isoformat(), "spots": build_smartspot_spots(spots, sim_date, rng)}
        smartspot = await client.post(f"{SMARTSPOT360_URL}/api/webhooks/spot-performance/", json=smartspot_body)
        smartspot.raise_for_status()

        creatives = await _get_json(
            client, f"{CAPTIVATOR360_URL}/api/creatives/", params={"campaign_id": FLAGGED_CAMPAIGN_ID}
        )
        latest_by_creative: dict[int, dict] = {}
        for creative in creatives:
            detail = await _get_json(client, f"{CAPTIVATOR360_URL}/api/creatives/{creative['id']}/performance/")
            daily = detail.get("daily_performance") or []
            if daily:
                latest_by_creative[creative["id"]] = daily[-1]
        captivator_body = {
            "date": sim_date.isoformat(),
            "metrics": build_creative_metrics(latest_by_creative, sim_date, rng),
        }
        captivator = await client.post(
            f"{CAPTIVATOR360_URL}/api/webhooks/creative-metrics/", json=captivator_body
        )
        captivator.raise_for_status()

        rules = await _get_json(client, f"{MAESTRO360_URL}/api/routing-rules/")
        pools = []
        for rule in rules:
            pool = rule.get("pool")
            if isinstance(pool, dict):
                pools.append(pool)
            elif isinstance(pool, int):
                # RoutingRuleSerializer may expose pool as an id; fetch via the rule fields.
                pools.append(
                    {
                        "id": pool,
                        "is_certified_medicare": "certified" in (rule.get("description") or "").lower()
                        and "not" not in (rule.get("description") or "").lower()[:40],
                        "historical_conversion_rate": 0.31 if rule.get("priority") == 1 else 0.18,
                    }
                )
        # Prefer explicit pool records from call summary when serializer only has ids.
        summary = await _get_json(
            client, f"{MAESTRO360_URL}/api/calls/summary/", params={"campaign_id": FLAGGED_CAMPAIGN_ID}
        )
        summary_pools = []
        for row in summary.get("pool_distribution") or []:
            summary_pools.append(
                {
                    "id": row["pool_id"],
                    "is_certified_medicare": row["is_certified_medicare"],
                    "historical_conversion_rate": 0.31 if row["is_certified_medicare"] else 0.18,
                }
            )
        if summary_pools:
            pools = summary_pools

        maestro_body = {
            "date": sim_date.isoformat(),
            "events": build_call_events(FLAGGED_CAMPAIGN_ID, pools, sim_date, rng),
        }
        maestro = await client.post(f"{MAESTRO360_URL}/api/webhooks/call-events/", json=maestro_body)
        maestro.raise_for_status()

    from guardrails.engine import run_anomaly_sweep

    sweep = await run_anomaly_sweep()
    return {
        "date": sim_date.isoformat(),
        "onesource": onesource.json(),
        "smartspot": smartspot.json(),
        "captivator": captivator.json(),
        "maestro": maestro.json(),
        "sweep": sweep,
    }
