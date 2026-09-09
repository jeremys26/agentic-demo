import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from guardrails.models import Base

DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "mcp_server")
DB_USER = os.environ.get("DB_USER", "agent360")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "agent360")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Same tables the demo used to TRUNCATE by hand. CASCADE + RESTART IDENTITY
# keeps ids starting at 1 for a clean demo slate.
_AUDIT_TABLES = (
    "agent_tool_calls",
    "proposed_actions",
    "executed_actions",
    "flagged_campaigns",
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def reset_audit_tables() -> None:
    """Wipe the gateway's audit/approval log so a restart matches the four
    sims' reseed-on-start behavior. Call before the startup anomaly sweep."""
    tables = ", ".join(_AUDIT_TABLES)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
