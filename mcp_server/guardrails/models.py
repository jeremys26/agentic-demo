"""
The MCP server's own database (PLANNING.md §5/§7) — separate from all four
sim services, which know nothing about agents, approvals, or logging. Uses
SQLAlchemy rather than Django since the MCP server is a FastAPI process, not
a Django one; tables are created via metadata.create_all() at startup
(db.py) rather than a full Alembic migration setup, proportionate to this
being a Tier 1 demo rather than a production schema under active change.
"""

import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class AgentToolCall(Base):
    """Every tool call, read or write, logged identically regardless of
    outcome (PLANNING.md §7) — the full audit trail."""

    __tablename__ = "agent_tool_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    tool_name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(10))  # "read" or "write"
    arguments: Mapped[dict] = mapped_column(JSON)
    outcome: Mapped[str] = mapped_column(String(30))  # read_ok / auto_execute / pending_approval / approved_executed / rejected / blocked / error
    risk_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    # Plain-language reasoning (PLANNING.md §7/§10) — the canonical copy for
    # every write-tool outcome, including "blocked", which never gets a
    # ProposedAction or ExecutedAction row of its own to hold it.
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProposedAction(Base):
    """A write action scored into the human-approval tier — created with
    status=pending_approval; a human approves/rejects it in React-Admin,
    which triggers (or skips) the real write call."""

    __tablename__ = "proposed_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tool_call_id: Mapped[int] = mapped_column()
    tool_name: Mapped[str] = mapped_column(String(100))
    campaign_id: Mapped[int] = mapped_column()
    arguments: Mapped[dict] = mapped_column(JSON)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    risk_breakdown: Mapped[dict] = mapped_column(JSON)
    rationale: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending_approval")  # pending_approval / approved / rejected
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutedAction(Base):
    """A write action that actually ran — either auto-executed immediately,
    or executed after a human approved a ProposedAction. pre_action_state is
    an audit snapshot of enough prior state to reconstruct what changed
    (PLANNING.md §7)."""

    __tablename__ = "executed_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tool_call_id: Mapped[int] = mapped_column()
    tool_name: Mapped[str] = mapped_column(String(100))
    campaign_id: Mapped[int] = mapped_column()
    arguments: Mapped[dict] = mapped_column(JSON)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    rationale: Mapped[str] = mapped_column(Text)
    pre_action_state: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(10))  # "auto" or "approved"
    result: Mapped[dict] = mapped_column(JSON)
    executed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FlaggedCampaign(Base):
    """Persisted log of the Tier 2 Celery anomaly sweep (PLANNING.md §8).
    `run_anomaly_sweep()` writes a row when `get_performance_anomalies`
    flags a campaign; duplicates are skipped on (campaign_id, variance_pct)."""

    __tablename__ = "flagged_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column()
    campaign_name: Mapped[str] = mapped_column(String(200))
    variance_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    flagged_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
