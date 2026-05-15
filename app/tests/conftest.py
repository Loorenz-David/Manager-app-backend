from __future__ import annotations

import os
from collections.abc import Generator
from uuid import uuid4

import pytest
import pytest_asyncio
import redis
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from beyo_manager.config import settings
from beyo_manager.models.database import get_db


@pytest.fixture(scope="session")
def isolated_redis_prefix() -> Generator[str, None, None]:
    prefix = f"{settings.redis_key_prefix}:test:{uuid4().hex[:8]}"
    old = os.environ.get("REDIS_KEY_PREFIX")
    os.environ["REDIS_KEY_PREFIX"] = prefix
    try:
        yield prefix
    finally:
        if old is None:
            os.environ.pop("REDIS_KEY_PREFIX", None)
        else:
            os.environ["REDIS_KEY_PREFIX"] = old


@pytest.fixture(scope="session")
def async_engine():
    # Lazy import: _engine is None at module load time; init_db() must run first.
    from beyo_manager.models.database import _engine
    return _engine


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async for session in get_db():
        yield session
        await session.rollback()


@pytest.fixture
def redis_client(isolated_redis_prefix: str):
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        for key in client.scan_iter(f"{isolated_redis_prefix}:*"):
            client.delete(key)


@pytest.fixture
def count_queries(async_engine):
    """Collect SQL statements executed during a test to detect N+1 regressions.
    Expected maximum: 1 + len(selectinloads) per list fetch.
    """
    queries: list[str] = []

    @sa_event.listens_for(async_engine.sync_engine, "before_cursor_execute")
    def _count(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    yield queries

    sa_event.remove(async_engine.sync_engine, "before_cursor_execute", _count)
