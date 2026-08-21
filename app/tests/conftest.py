from __future__ import annotations

import asyncio
import os
import warnings
from collections.abc import Generator
from uuid import uuid4

import pytest
import pytest_asyncio
import redis
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.models.database import close_db, get_db, init_db
from tests.database_isolation import DatabaseIsolation, start_database_isolation


pytest_plugins = ("tests.fixtures.phase1_reference_data",)


@pytest.fixture(scope="session")
def isolated_database() -> Generator[DatabaseIsolation, None, None]:
    """Provision one fresh marked database for this pytest process."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required before test database isolation starts")
    original_database_url = settings.database_url
    isolation = start_database_isolation(original_database_url)
    settings.database_url = isolation.worker_database_url
    try:
        yield isolation
    finally:
        try:
            asyncio.run(isolation.assert_configured_database_unchanged())
        finally:
            settings.database_url = original_database_url
            asyncio.run(isolation.stop())


@pytest.fixture(scope="session", autouse=True)
def configure_isolated_database(isolated_database: DatabaseIsolation) -> None:
    """Make the process-wide application seam resolve to the worker database."""
    return None


@pytest_asyncio.fixture(autouse=True)
async def initialize_database() -> None:
    """Ensure get_db has an initialized session factory during tests."""
    await init_db()
    yield
    await close_db()


@pytest.fixture(scope="session", autouse=True)
def isolated_redis_prefix() -> Generator[str, None, None]:
    prefix = f"{settings.redis_key_prefix}:test:{uuid4().hex[:8]}"
    old = settings.redis_key_prefix
    settings.redis_key_prefix = prefix
    client = None
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.set(f"{prefix}:teardown-probe", "1")
    except redis.exceptions.ConnectionError:
        warnings.warn(
            "Redis unavailable while setting the isolation teardown probe; continuing without it",
            RuntimeWarning,
            stacklevel=2,
        )
        if client is not None:
            client.close()
            client = None
    try:
        yield prefix
    finally:
        try:
            if client is None:
                client = redis.from_url(settings.redis_url, decode_responses=True)
            for key in client.scan_iter(f"{prefix}:*"):
                client.delete(key)
            remaining = list(client.scan_iter(f"{prefix}:*"))
            assert not remaining, f"Redis isolation prefix left residue: {remaining!r}"
        except redis.exceptions.ConnectionError:
            warnings.warn(
                "Redis unavailable while cleaning the isolation prefix; continuing",
                RuntimeWarning,
                stacklevel=2,
            )
        finally:
            if client is not None:
                client.close()
            settings.redis_key_prefix = old


def pytest_collection_modifyitems(config, items) -> None:
    order = os.getenv("BEYO_TEST_COLLECTION_ORDER")
    if order is None:
        return
    if order == "reverse":
        items.reverse()
        return
    raise pytest.UsageError(
        "BEYO_TEST_COLLECTION_ORDER must be unset or set to 'reverse'"
    )


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
