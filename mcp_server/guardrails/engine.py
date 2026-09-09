"""
Ties the risk-scoring guardrail together (PLANNING.md §7): scores a
proposed write action, decides auto-execute / human approval / hard block,
performs the real execution call when appropriate, and logs everything.
Also wraps read tools so every tool call — read or write — lands in
AgentToolCall identically, per §7.

Approval/rejection of a queued ProposedAction (resolve_proposed_action) is
deliberately exposed only as plain REST (main.py's /agent-actions/{id}/...
endpoints), never as an MCP tool — an agent must never be able to approve
its own proposed action, only a human via React-Admin can (§7: "A human
approves/rejects in React-Admin").
"""

import functools
import os
from decimal import Decimal

from sqlalchemy import select

import registry
from guardrails import scoring
from guardrails.db import SessionLocal
from guardrails.models import AgentToolCall, ExecutedAction, FlaggedCampaign, ProposedAction, utcnow
from http_client import service_client

ONESOURCE360_URL = os.environ.get("ONESOURCE360_URL", "http://onesource360:8000")
SMARTSPOT360_URL = os.environ.get("SMARTSPOT360_URL", "http://smartspot360:8000")
CAPTIVATOR360_URL = os.environ.get("CAPTIVATOR360_URL", "http://captivator360:8000")

_TIER_RATIONALE = {
    "auto_execute": (
        "This change is small relative to the campaign's usual activity and well-supported "
        "by historical data, so it's being applied automatically."
    ),
    "pending_approval": (
        "This change is either large relative to the campaign's usual activity or not yet "
        "backed by much historical data, so it's queued for your approval before anything changes."
    ),
    "blocked": (
        "This change is too large and/or too thinly supported by data to apply automatically "
        "or queue for approval as-is — a smaller or different change would need to be proposed instead."
    ),
}


def summarize_result_for_log(result, max_list_preview: int = 3) -> dict:
    """Compact a tool result for AgentToolCall.result_summary.

    Read tools like get_call_quality can return thousands of rows; storing
    the full payload on every log line would bloat the MCP server's DB and
    make the Tool Calls show page unreadable. Lists become a count + short
    preview; everything else is kept as-is.
    """
    if not isinstance(result, dict):
        return {"value": str(result)[:500]}
    summary = {}
    for key, value in result.items():
        if isinstance(value, list):
            summary[key] = {"count": len(value), "preview": value[:max_list_preview]}
        else:
            summary[key] = value
    return summary


def wrap_read_tool(func):
    """Every read tool call gets logged to AgentToolCall identically to
    write tools (PLANNING.md §7) — same table, just always outcome=read_ok
    (or error) and no risk score."""

    @functools.wraps(func)
    async def wrapper(**kwargs):
        async with SessionLocal() as session:
            try:
                result = await func(**kwargs)
                session.add(
                    AgentToolCall(
                        tool_name=func.__name__,
                        kind="read",
                        arguments=kwargs,
                        outcome="read_ok",
                        result_summary=summarize_result_for_log(result),
                    )
                )
                await session.commit()
                return result
            except Exception as exc:
                session.add(
                    AgentToolCall(
                        tool_name=func.__name__,
                        kind="read",
                        arguments=kwargs,
                        outcome="error",
                        result_summary={"error": str(exc)},
                    )
                )
                await session.commit()
                raise

    return wrapper


# --- Execution steps, shared between the auto-execute path and the
# approve-a-pending-action path (resolve_proposed_action) below, so the two
# can never diverge in how they actually call the backing service. ---


async def _execute_reallocate_budget(arguments: dict) -> tuple[dict, dict]:
    """Returns (pre_action_state, result)."""
    recommendation_id = arguments["recommendation_id"]
    async with service_client() as client:
        rec_response = await client.get(
            f"{SMARTSPOT360_URL}/api/recommendations/{recommendation_id}/", timeout=10.0
        )
        rec_response.raise_for_status()
        recommendation = rec_response.json()
        if recommendation["applied"]:
            raise ValueError("recommendation already applied")

        pre_action_state = {"recommendation_applied_before": False, "recommendation": recommendation}
        apply_response = await client.post(
            f"{SMARTSPOT360_URL}/api/recommendations/{recommendation_id}/apply/", timeout=10.0
        )
        apply_response.raise_for_status()
        return pre_action_state, apply_response.json()


async def _execute_request_creative_refresh(arguments: dict) -> tuple[dict, dict]:
    """Returns (pre_action_state, result). Creates the refresh request, then
    immediately approves it — the guardrail already decided this can go
    through, whether that decision was auto-execute or a human's approval."""
    creative_id = arguments["creative_id"]
    reason = arguments["reason"]
    async with service_client() as client:
        creative_response = await client.get(
            f"{CAPTIVATOR360_URL}/api/creatives/{creative_id}/performance/", timeout=10.0
        )
        creative_response.raise_for_status()
        creative = creative_response.json()["creative"]

        pre_action_state = {"creative": creative}
        create_response = await client.post(
            f"{CAPTIVATOR360_URL}/api/creatives/{creative_id}/refresh-request/",
            json={"reason": reason},
            timeout=10.0,
        )
        create_response.raise_for_status()
        refresh_request = create_response.json()

        resolve_response = await client.post(
            f"{CAPTIVATOR360_URL}/api/creatives/refresh-requests/{refresh_request['id']}/resolve/",
            json={"status": "approved"},
            timeout=10.0,
        )
        resolve_response.raise_for_status()
        return pre_action_state, resolve_response.json()


_EXECUTORS = {
    "reallocate_budget": _execute_reallocate_budget,
    "request_creative_refresh": _execute_request_creative_refresh,
}


async def _existing_pending_action(session, tool_name: str, arguments: dict) -> ProposedAction | None:
    """Return a still-queued ProposedAction with the same tool + arguments, if any.

    An agent that retries a write (network blip, user re-asks) would otherwise
    create a second pending row — two Approve buttons for one change.
    """
    result = await session.execute(
        select(ProposedAction).where(
            ProposedAction.tool_name == tool_name,
            ProposedAction.status == "pending_approval",
        )
    )
    for proposed in result.scalars():
        if proposed.arguments == arguments:
            return proposed
    return None


def _pending_response(proposed: ProposedAction) -> dict:
    return {
        "status": "pending_approval",
        "proposed_action_id": proposed.id,
        "risk": proposed.risk_breakdown,
        "rationale": proposed.rationale,
        "already_queued": True,
    }


def normalize_variance_pct(variance_pct: float) -> Decimal:
    """Same 2-decimal Numeric scale as FlaggedCampaign.variance_pct.

    Comparing a Python float to a Numeric column can miss an existing row
    and insert a duplicate every sweep tick.
    """
    return Decimal(str(variance_pct)).quantize(Decimal("0.01"))


async def guard_reallocate_budget(campaign_id: int, recommendation_id: int) -> dict:
    """
    Executes a previously-computed SmartSpot360-sim budget recommendation
    (from get_budget_recommendation) — but only after the risk-scoring
    guardrail clears it. Never applies the recommendation directly.
    """
    arguments = {"campaign_id": campaign_id, "recommendation_id": recommendation_id}
    async with SessionLocal() as session:
        try:
            async with service_client() as client:
                rec_response = await client.get(
                    f"{SMARTSPOT360_URL}/api/recommendations/{recommendation_id}/", timeout=10.0
                )
                if rec_response.status_code == 404:
                    session.add(
                        AgentToolCall(
                            tool_name="reallocate_budget",
                            kind="write",
                            arguments=arguments,
                            outcome="error",
                            result_summary={"error": f"no recommendation with id {recommendation_id}"},
                        )
                    )
                    await session.commit()
                    return {"status": "error", "detail": f"no recommendation with id {recommendation_id}"}
                rec_response.raise_for_status()
                recommendation = rec_response.json()

            if recommendation["campaign_id"] != campaign_id:
                session.add(
                    AgentToolCall(
                        tool_name="reallocate_budget",
                        kind="write",
                        arguments=arguments,
                        outcome="error",
                        result_summary={"error": "recommendation does not belong to this campaign"},
                    )
                )
                await session.commit()
                return {"status": "error", "detail": "recommendation does not belong to this campaign"}

            if recommendation["applied"]:
                session.add(
                    AgentToolCall(
                        tool_name="reallocate_budget",
                        kind="write",
                        arguments=arguments,
                        outcome="error",
                        result_summary={"error": "recommendation already applied"},
                    )
                )
                await session.commit()
                return {"status": "error", "detail": "recommendation already applied"}

            existing = await _existing_pending_action(session, "reallocate_budget", arguments)
            if existing is not None:
                return _pending_response(existing)

            risk = await scoring.gather_reallocate_budget_inputs(
                session, ONESOURCE360_URL, campaign_id, recommendation
            )
        except Exception as exc:
            # Backing service unreachable/timed out, or an unexpected response
            # shape — log it like every other outcome instead of letting it
            # propagate silently (PLANNING.md §7: every outcome logged to
            # AgentToolCall).
            session.add(
                AgentToolCall(
                    tool_name="reallocate_budget",
                    kind="write",
                    arguments=arguments,
                    outcome="error",
                    result_summary={"error": str(exc)},
                )
            )
            await session.commit()
            return {"status": "error", "detail": str(exc)}

        rationale = f"{recommendation['rationale']} {_TIER_RATIONALE[risk.decision]}"

        call = AgentToolCall(
            tool_name="reallocate_budget",
            kind="write",
            arguments=arguments,
            outcome=risk.decision,
            risk_score=risk.final_score,
            rationale=rationale,
        )
        session.add(call)
        await session.flush()

        if risk.decision == "blocked":
            call.result_summary = {"risk": risk.as_dict()}
            await session.commit()
            return {"status": "blocked", "risk": risk.as_dict(), "rationale": rationale}

        if risk.decision == "pending_approval":
            proposed = ProposedAction(
                tool_call_id=call.id,
                tool_name="reallocate_budget",
                campaign_id=campaign_id,
                arguments=arguments,
                risk_score=risk.final_score,
                risk_breakdown=risk.as_dict(),
                rationale=rationale,
                status="pending_approval",
            )
            session.add(proposed)
            await session.commit()
            return {
                "status": "pending_approval",
                "proposed_action_id": proposed.id,
                "risk": risk.as_dict(),
                "rationale": rationale,
            }

        # auto_execute
        try:
            pre_action_state, result = await _execute_reallocate_budget(arguments)
        except Exception as exc:
            call.outcome = "error"
            call.result_summary = {"error": str(exc)}
            await session.commit()
            return {"status": "error", "detail": str(exc), "risk": risk.as_dict()}
        session.add(
            ExecutedAction(
                tool_call_id=call.id,
                tool_name="reallocate_budget",
                campaign_id=campaign_id,
                arguments=arguments,
                risk_score=risk.final_score,
                rationale=rationale,
                pre_action_state=pre_action_state,
                source="auto",
                result=result,
            )
        )
        call.result_summary = {"result": result, "risk": risk.as_dict()}
        await session.commit()
        return {"status": "auto_executed", "risk": risk.as_dict(), "rationale": rationale, "result": result}


async def guard_request_creative_refresh(creative_id: int, reason: str) -> dict:
    """
    Creates a Captivator360-sim creative refresh request — but only after the
    risk-scoring guardrail clears it. Never creates it directly.
    """
    # campaign_id isn't known until the creative fetch below resolves, so the
    # 404 case is logged with a partial argument set (no campaign_id yet).
    partial_arguments = {"creative_id": creative_id, "reason": reason}
    async with SessionLocal() as session:
        try:
            async with service_client() as client:
                creative_response = await client.get(
                    f"{CAPTIVATOR360_URL}/api/creatives/{creative_id}/performance/", timeout=10.0
                )
                if creative_response.status_code == 404:
                    session.add(
                        AgentToolCall(
                            tool_name="request_creative_refresh",
                            kind="write",
                            arguments=partial_arguments,
                            outcome="error",
                            result_summary={"error": f"no creative with id {creative_id}"},
                        )
                    )
                    await session.commit()
                    return {"status": "error", "detail": f"no creative with id {creative_id}"}
                creative_response.raise_for_status()
                creative = creative_response.json()["creative"]

                campaign_id = creative["campaign_id"]

            # campaign_id is not an input to this tool, but the frontend (and
            # the audit log) need it to attribute the action to a campaign —
            # arguments otherwise only carry creative_id + reason.
            arguments = {"creative_id": creative_id, "reason": reason, "campaign_id": campaign_id}

            existing = await _existing_pending_action(session, "request_creative_refresh", arguments)
            if existing is not None:
                return _pending_response(existing)

            risk = await scoring.gather_creative_refresh_inputs(
                session, ONESOURCE360_URL, CAPTIVATOR360_URL, campaign_id, creative
            )
        except Exception as exc:
            session.add(
                AgentToolCall(
                    tool_name="request_creative_refresh",
                    kind="write",
                    arguments=partial_arguments,
                    outcome="error",
                    result_summary={"error": str(exc)},
                )
            )
            await session.commit()
            return {"status": "error", "detail": str(exc)}

        rationale = (
            f"Requesting a creative refresh for '{creative['variant_label']}' — {reason} "
            f"{_TIER_RATIONALE[risk.decision]}"
        )

        call = AgentToolCall(
            tool_name="request_creative_refresh",
            kind="write",
            arguments=arguments,
            outcome=risk.decision,
            risk_score=risk.final_score,
            rationale=rationale,
        )
        session.add(call)
        await session.flush()

        if risk.decision == "blocked":
            call.result_summary = {"risk": risk.as_dict()}
            await session.commit()
            return {"status": "blocked", "risk": risk.as_dict(), "rationale": rationale}

        if risk.decision == "pending_approval":
            proposed = ProposedAction(
                tool_call_id=call.id,
                tool_name="request_creative_refresh",
                campaign_id=campaign_id,
                arguments=arguments,
                risk_score=risk.final_score,
                risk_breakdown=risk.as_dict(),
                rationale=rationale,
                status="pending_approval",
            )
            session.add(proposed)
            await session.commit()
            return {
                "status": "pending_approval",
                "proposed_action_id": proposed.id,
                "risk": risk.as_dict(),
                "rationale": rationale,
            }

        # auto_execute
        try:
            pre_action_state, result = await _execute_request_creative_refresh(arguments)
        except Exception as exc:
            call.outcome = "error"
            call.result_summary = {"error": str(exc)}
            await session.commit()
            return {"status": "error", "detail": str(exc), "risk": risk.as_dict()}
        session.add(
            ExecutedAction(
                tool_call_id=call.id,
                tool_name="request_creative_refresh",
                campaign_id=campaign_id,
                arguments=arguments,
                risk_score=risk.final_score,
                rationale=rationale,
                pre_action_state=pre_action_state,
                source="auto",
                result=result,
            )
        )
        call.result_summary = {"result": result, "risk": risk.as_dict()}
        await session.commit()
        return {"status": "auto_executed", "risk": risk.as_dict(), "rationale": rationale, "result": result}


async def get_pending_actions() -> list[dict]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(ProposedAction).where(ProposedAction.status == "pending_approval")
        )
        return [_proposed_action_dict(p) for p in result.scalars()]


async def get_all_agent_actions() -> list[dict]:
    """
    Every write-tool call ever logged, across all three risk tiers — the
    single source React-Admin's Agent Actions view (PLANNING.md §10) reads
    from. AgentToolCall (kind="write") already captures every tier uniformly
    (auto_execute / pending_approval / blocked / approved_executed / error),
    including blocked calls, which never get a ProposedAction or
    ExecutedAction row of their own.
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(AgentToolCall).where(AgentToolCall.kind == "write").order_by(AgentToolCall.id.desc())
        )
        calls = list(result.scalars())

        proposed_result = await session.execute(select(ProposedAction))
        proposed_by_call_id = {p.tool_call_id: p for p in proposed_result.scalars()}

        executed_result = await session.execute(select(ExecutedAction))
        executed_by_call_id = {e.tool_call_id: e for e in executed_result.scalars()}

        rows = []
        for c in calls:
            proposed = proposed_by_call_id.get(c.id)
            executed = executed_by_call_id.get(c.id)
            campaign_id = (
                (c.arguments or {}).get("campaign_id")
                or (proposed.campaign_id if proposed else None)
                or (executed.campaign_id if executed else None)
            )
            risk_breakdown = None
            if proposed is not None:
                risk_breakdown = proposed.risk_breakdown
            elif isinstance(c.result_summary, dict):
                risk_breakdown = c.result_summary.get("risk")
            rows.append(
                {
                    "id": c.id,
                    "tool_name": c.tool_name,
                    "arguments": c.arguments,
                    "outcome": c.outcome,
                    "risk_score": float(c.risk_score) if c.risk_score is not None else None,
                    "risk_breakdown": risk_breakdown,
                    "rationale": c.rationale,
                    "result_summary": c.result_summary,
                    "pre_action_state": executed.pre_action_state if executed else None,
                    "executed_source": executed.source if executed else None,
                    "created_at": c.created_at.isoformat(),
                    "campaign_id": campaign_id,
                    "proposed_action_id": proposed.id if proposed else None,
                }
            )
        return rows


async def get_all_tool_calls() -> list[dict]:
    """
    Every tool call ever logged, reads and writes alike — the full MCP
    trace, distinct from get_all_agent_actions() above which only surfaces
    the write tier's risk-scored decisions. Lets the frontend show the
    agent's actual MCP traffic (including which backing sim service each
    call reached) rather than just the subset that resulted in a change.
    """
    service_by_tool = {spec.name: spec.service for spec in registry.all_tools()}
    async with SessionLocal() as session:
        result = await session.execute(select(AgentToolCall).order_by(AgentToolCall.id.desc()))
        return [
            {
                "id": c.id,
                "tool_name": c.tool_name,
                "service": service_by_tool.get(c.tool_name, "unknown"),
                "kind": c.kind,
                "arguments": c.arguments,
                "outcome": c.outcome,
                "risk_score": float(c.risk_score) if c.risk_score is not None else None,
                "risk_breakdown": (c.result_summary or {}).get("risk") if isinstance(c.result_summary, dict) else None,
                "rationale": c.rationale,
                "result_summary": c.result_summary,
                "created_at": c.created_at.isoformat(),
            }
            for c in result.scalars()
        ]


def _proposed_action_dict(p: ProposedAction) -> dict:
    return {
        "id": p.id,
        "tool_name": p.tool_name,
        "campaign_id": p.campaign_id,
        "arguments": p.arguments,
        "risk_score": float(p.risk_score),
        "risk_breakdown": p.risk_breakdown,
        "rationale": p.rationale,
        "status": p.status,
        "created_at": p.created_at.isoformat(),
        "resolved_at": p.resolved_at.isoformat() if p.resolved_at else None,
    }


async def run_anomaly_sweep(threshold_pct: float = 15.0, window_days: int = 7) -> dict:
    """
    The Tier 2 anomaly sweep (PLANNING.md §8): reuses get_performance_anomalies'
    own code path directly — no LLM, no MCP protocol round-trip, no cost —
    triggered by Celery beat on a timer instead of a conversation. Called
    with the module-level function directly (not the wrap_read_tool-wrapped
    handler main.py registers with the MCP server) since a scheduled sweep
    isn't an agent tool call and shouldn't be logged to AgentToolCall as one;
    FlaggedCampaign is this process's own audit trail instead.

    Idempotent per (campaign_id, variance_pct): re-running against unchanged
    seed data — the common case in this demo, since there's no live data feed
    — doesn't pile up duplicate rows every tick.
    """
    from tools.onesource360 import get_performance_anomalies

    result = await get_performance_anomalies(threshold_pct=threshold_pct, window_days=window_days)

    newly_flagged = []
    async with SessionLocal() as session:
        for anomaly in result["anomalies"]:
            variance = normalize_variance_pct(anomaly["variance_pct"])
            existing = await session.scalar(
                select(FlaggedCampaign).where(
                    FlaggedCampaign.campaign_id == anomaly["campaign_id"],
                    FlaggedCampaign.variance_pct == variance,
                )
            )
            if existing is not None:
                continue
            session.add(
                FlaggedCampaign(
                    campaign_id=anomaly["campaign_id"],
                    campaign_name=anomaly["campaign_name"],
                    variance_pct=variance,
                )
            )
            newly_flagged.append(anomaly)
        await session.commit()

    return {
        "threshold_pct": threshold_pct,
        "window_days": window_days,
        "anomalies_found": len(result["anomalies"]),
        "newly_flagged": newly_flagged,
        "swept_at": utcnow().isoformat(),
    }


async def get_all_flagged_campaigns() -> list[dict]:
    """Every anomaly the automated sweep has ever persisted, most recent
    first — the sweep's own audit log, distinct from the frontend's live
    client-side variance recompute on every page load."""
    async with SessionLocal() as session:
        result = await session.execute(select(FlaggedCampaign).order_by(FlaggedCampaign.id.desc()))
        return [
            {
                "id": f.id,
                "campaign_id": f.campaign_id,
                "campaign_name": f.campaign_name,
                "variance_pct": float(f.variance_pct),
                "flagged_at": f.flagged_at.isoformat(),
            }
            for f in result.scalars()
        ]


async def resolve_proposed_action(proposed_action_id: int, approve: bool) -> dict:
    """
    The human-approval step React-Admin's Agent Actions view will call
    (PLANNING.md §10) — a human approving or rejecting a queued
    ProposedAction. Only reachable via plain REST (main.py), never as an MCP
    tool: an agent must never approve its own proposed action.
    """
    async with SessionLocal() as session:
        proposed = await session.get(ProposedAction, proposed_action_id)
        if proposed is None:
            return {"status": "error", "detail": f"no proposed action with id {proposed_action_id}"}
        if proposed.status != "pending_approval":
            return {"status": "error", "detail": f"proposed action already {proposed.status}"}

        original_call = await session.get(AgentToolCall, proposed.tool_call_id)

        if not approve:
            proposed.status = "rejected"
            proposed.resolved_at = utcnow()
            # Flip the original log row too — otherwise Agent Actions keeps
            # showing this as pending_approval with live Approve/Reject buttons.
            if original_call is not None:
                original_call.outcome = "rejected"
            await session.commit()
            return {"status": "rejected", "proposed_action": _proposed_action_dict(proposed)}

        executor = _EXECUTORS[proposed.tool_name]
        try:
            pre_action_state, result = await executor(proposed.arguments)
        except Exception as exc:
            await session.rollback()
            return {"status": "error", "detail": str(exc)}

        proposed.status = "approved"
        proposed.resolved_at = utcnow()

        # Update the original pending row rather than inserting a second
        # AgentToolCall — a new row left the pending one in the list with
        # working Approve/Reject buttons after the action had already run.
        if original_call is not None:
            original_call.outcome = "approved_executed"
            original_call.result_summary = {"result": result, "risk": proposed.risk_breakdown}
            tool_call_id = original_call.id
        else:
            call = AgentToolCall(
                tool_name=proposed.tool_name,
                kind="write",
                arguments=proposed.arguments,
                outcome="approved_executed",
                risk_score=proposed.risk_score,
                rationale=proposed.rationale,
                result_summary={"result": result, "risk": proposed.risk_breakdown},
            )
            session.add(call)
            await session.flush()
            tool_call_id = call.id

        session.add(
            ExecutedAction(
                tool_call_id=tool_call_id,
                tool_name=proposed.tool_name,
                campaign_id=proposed.campaign_id,
                arguments=proposed.arguments,
                risk_score=proposed.risk_score,
                rationale=proposed.rationale,
                pre_action_state=pre_action_state,
                source="approved",
                result=result,
            )
        )
        await session.commit()
        return {
            "status": "approved_executed",
            "proposed_action": _proposed_action_dict(proposed),
            "result": result,
        }
