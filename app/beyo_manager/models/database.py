import logging
import time
from typing import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from beyo_manager.config import settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None

_perf_logger = logging.getLogger("sqlalchemy.perf")


async def init_db() -> None:
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.database_url,
        connect_args={"server_settings": {"timezone": "UTC"}, "timeout": 5},
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_timeout=30,
        pool_pre_ping=True,
        echo=settings.environment == "development",
    )

    @event.listens_for(_engine.sync_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("_query_start", time.monotonic())

    @event.listens_for(_engine.sync_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        elapsed_ms = (time.monotonic() - conn.info.pop("_query_start", time.monotonic())) * 1000
        if elapsed_ms >= settings.slow_query_threshold_ms:
            _perf_logger.warning("slow_query | elapsed_ms=%.1f | %s", elapsed_ms, statement[:200])

    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — one session per request."""
    if _session_factory is None:
        raise RuntimeError("DB not initialised — init_db() must run first.")
    async with _session_factory() as session:
        yield session


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Background task helper — same pool, usable outside request context."""
    if _session_factory is None:
        raise RuntimeError("DB not initialised — init_db() must run first.")
    async with _session_factory() as session:
        yield session
