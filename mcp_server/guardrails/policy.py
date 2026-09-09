"""
Configurable policy values for the risk-scoring guardrail (PLANNING.md §7).
These are business-set dials, not constants baked into the agent — the
business sets the thresholds, the deterministic scoring layer enforces them,
the agent never gets to decide its own leash. Overridable via environment
variables so they can be tuned per deployment without a code change.
"""

import os


def _float_env(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


AUTO_EXECUTE_THRESHOLD = _float_env("RISK_AUTO_EXECUTE_THRESHOLD", 30.0)
BLOCK_THRESHOLD = _float_env("RISK_BLOCK_THRESHOLD", 70.0)

# Fixed, score-independent hard cap: never auto-execute a budget reallocation
# above this % of the campaign's baseline weekly spend, regardless of what
# the computed score says. Defense in depth against a bug in the scoring
# function itself (PLANNING.md §7).
REALLOCATE_BUDGET_HARD_CAP_PCT = _float_env("RISK_REALLOCATE_BUDGET_HARD_CAP_PCT", 5.0)

# Regulatory sensitivity multiplier applied to regulated verticals — same
# definition for every tool (PLANNING.md §7).
REGULATED_VERTICALS = {"medicare_advantage"}
REGULATORY_MULTIPLIER = _float_env("RISK_REGULATORY_MULTIPLIER", 1.4)

# A campaign counts as "recently modified" if it had an executed or approved
# action within this many hours — same definition for every tool.
RECENCY_WINDOW_HOURS = _float_env("RISK_RECENCY_WINDOW_HOURS", 24.0)


def route(score: float, hard_cap_exceeded: bool) -> str:
    """auto_execute / pending_approval / blocked — PLANNING.md §7's routing table."""
    if score >= BLOCK_THRESHOLD:
        return "blocked"
    if score < AUTO_EXECUTE_THRESHOLD and not hard_cap_exceeded:
        return "auto_execute"
    return "pending_approval"
