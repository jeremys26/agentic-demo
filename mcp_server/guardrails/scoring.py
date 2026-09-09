"""
The risk-scoring guardrail (PLANNING.md §7) — the most safety-critical code
in the repo, split in two on purpose:

- compute_score() is pure math, no I/O — this is what gets the heaviest test
  coverage (every threshold boundary, the hard cap, each tool's per-input
  definitions), since it's trivial to hit every edge case without mocking
  HTTP calls or a database.
- the gather_*_inputs() functions do the I/O (calling the sim services'
  REST APIs and querying the MCP server's own DB) to turn a proposed action
  into the four inputs compute_score() needs. Bugs there are ordinary
  integration bugs; bugs in compute_score() are safety bugs.
"""

import datetime
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from http_client import service_client

from guardrails import policy
from guardrails.models import ExecutedAction, ProposedAction


@dataclass
class RiskResult:
    magnitude_pct: float
    magnitude_score: float
    confidence: float
    confidence_score: float
    recency_flag: bool
    recency_score: float
    vertical: str
    regulatory_multiplier: float
    base_score: float
    final_score: float
    hard_cap_exceeded: bool
    decision: str = field(init=False)

    def __post_init__(self):
        self.decision = policy.route(self.final_score, self.hard_cap_exceeded)

    def as_dict(self) -> dict:
        return {
            "magnitude_pct": self.magnitude_pct,
            "magnitude_score": self.magnitude_score,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "recency_flag": self.recency_flag,
            "recency_score": self.recency_score,
            "vertical": self.vertical,
            "regulatory_multiplier": self.regulatory_multiplier,
            "base_score": self.base_score,
            "final_score": self.final_score,
            "hard_cap_exceeded": self.hard_cap_exceeded,
            "decision": self.decision,
        }


def compute_score(
    magnitude_pct: float,
    confidence: float,
    recency_flag: bool,
    vertical: str,
    hard_cap_exceeded: bool = False,
) -> RiskResult:
    """
    Pure function, no I/O. Combines the four PLANNING.md §7 inputs into a
    single 0-100 score:
      - magnitude_score: the magnitude input, clamped to [0, 100]
      - confidence_score: inverted confidence (low confidence -> high risk)
      - recency_score: a flat 100 if the campaign was modified recently, else 0
      - weighted 50/35/15 (magnitude/confidence/recency), then multiplied by
        a regulatory sensitivity multiplier for regulated verticals
    hard_cap_exceeded is carried through unchanged into routing (policy.route)
    but does not affect the numeric score itself — it's a separate,
    score-independent gate.
    """
    magnitude_score = min(100.0, max(0.0, magnitude_pct))
    confidence_clamped = min(1.0, max(0.0, confidence))
    confidence_score = (1 - confidence_clamped) * 100.0
    recency_score = 100.0 if recency_flag else 0.0

    base_score = 0.5 * magnitude_score + 0.35 * confidence_score + 0.15 * recency_score
    regulatory_multiplier = (
        policy.REGULATORY_MULTIPLIER if vertical in policy.REGULATED_VERTICALS else 1.0
    )
    final_score = min(100.0, base_score * regulatory_multiplier)

    return RiskResult(
        magnitude_pct=round(magnitude_pct, 2),
        magnitude_score=round(magnitude_score, 2),
        confidence=round(confidence_clamped, 3),
        confidence_score=round(confidence_score, 2),
        recency_flag=recency_flag,
        recency_score=recency_score,
        vertical=vertical,
        regulatory_multiplier=regulatory_multiplier,
        base_score=round(base_score, 2),
        final_score=round(final_score, 2),
        hard_cap_exceeded=hard_cap_exceeded,
    )


async def was_recently_modified(session: AsyncSession, campaign_id: int) -> bool:
    """Same definition for every tool: was this campaign touched by an
    executed action, or an approved-but-not-yet-executed one, within the
    last policy.RECENCY_WINDOW_HOURS?"""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=policy.RECENCY_WINDOW_HOURS
    )

    executed = await session.scalar(
        select(ExecutedAction).where(
            ExecutedAction.campaign_id == campaign_id, ExecutedAction.executed_at >= cutoff
        )
    )
    if executed is not None:
        return True

    approved = await session.scalar(
        select(ProposedAction).where(
            ProposedAction.campaign_id == campaign_id,
            ProposedAction.status == "approved",
            ProposedAction.resolved_at >= cutoff,
        )
    )
    return approved is not None


async def get_campaign(client: httpx.AsyncClient, onesource360_url: str, campaign_id: int) -> dict:
    response = await client.get(f"{onesource360_url}/api/campaigns/{campaign_id}/", timeout=10.0)
    response.raise_for_status()
    return response.json()


async def get_baseline_weekly_spend(
    client: httpx.AsyncClient, onesource360_url: str, campaign_id: int, window_days: int = 7
) -> float:
    response = await client.get(
        f"{onesource360_url}/api/performance/", params={"campaign_id": campaign_id}, timeout=10.0
    )
    response.raise_for_status()
    rollups = response.json()["daily_rollups"][-window_days:]
    total_spend = sum(float(r["spend"]) for r in rollups)
    if not rollups:
        return 0.0
    # Scale to a full week regardless of how many days of history exist.
    return total_spend / len(rollups) * 7


async def gather_reallocate_budget_inputs(
    session: AsyncSession,
    onesource360_url: str,
    campaign_id: int,
    recommendation: dict,
) -> RiskResult:
    """
    magnitude: recommendation's total budget_amount relative to the
    campaign's baseline weekly spend (PLANNING.md §7 — "% of campaign
    budget moved" for reallocate_budget).
    confidence: SmartSpot360-sim's own confidence score on the recommendation
    (sample size behind the scoring, per §7).
    """
    async with service_client() as client:
        campaign = await get_campaign(client, onesource360_url, campaign_id)
        baseline_weekly_spend = await get_baseline_weekly_spend(client, onesource360_url, campaign_id)

    budget_amount = float(recommendation["budget_amount"])
    magnitude_pct = (budget_amount / baseline_weekly_spend * 100) if baseline_weekly_spend else 100.0
    hard_cap_exceeded = magnitude_pct > policy.REALLOCATE_BUDGET_HARD_CAP_PCT

    confidence = float(recommendation["confidence"])
    recency_flag = await was_recently_modified(session, campaign_id)

    return compute_score(
        magnitude_pct=magnitude_pct,
        confidence=confidence,
        recency_flag=recency_flag,
        vertical=campaign["vertical"],
        hard_cap_exceeded=hard_cap_exceeded,
    )


async def gather_creative_refresh_inputs(
    session: AsyncSession,
    onesource360_url: str,
    captivator360_url: str,
    campaign_id: int,
    creative: dict,
) -> RiskResult:
    """
    magnitude: how disruptive the refresh is — 100 / count of the campaign's
    active creatives (PLANNING.md §7 — sole active creative = 100%, one of
    four = 25%).
    confidence: days of CreativePerformanceDaily backing the CTR reading,
    scaled against a 14-day full-confidence baseline.
    Hard cap equivalent for this tool: never auto-execute if this would leave
    the campaign with zero active creatives (the sole-active-creative case).
    """
    async with service_client() as client:
        campaign = await get_campaign(client, onesource360_url, campaign_id)

        creatives_response = await client.get(
            f"{captivator360_url}/api/creatives/", params={"campaign_id": campaign_id}, timeout=10.0
        )
        creatives_response.raise_for_status()
        active_count = sum(1 for c in creatives_response.json() if c["is_active"])
        active_count = max(active_count, 1)

        perf_response = await client.get(
            f"{captivator360_url}/api/creatives/{creative['id']}/performance/", timeout=10.0
        )
        perf_response.raise_for_status()
        days_of_data = perf_response.json()["summary"]["days_of_data"]

    magnitude_pct = 100.0 / active_count
    hard_cap_exceeded = active_count == 1

    confidence = min(1.0, days_of_data / 14.0)
    recency_flag = await was_recently_modified(session, campaign_id)

    return compute_score(
        magnitude_pct=magnitude_pct,
        confidence=confidence,
        recency_flag=recency_flag,
        vertical=campaign["vertical"],
        hard_cap_exceeded=hard_cap_exceeded,
    )
