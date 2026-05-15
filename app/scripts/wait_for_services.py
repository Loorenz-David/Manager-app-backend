import asyncio
import time

import redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from beyo_manager.config import settings


async def _check_db() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is missing.")
    engine = create_async_engine(
        settings.database_url,
        connect_args={"timeout": 5},
        pool_pre_ping=True,
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


def _check_redis() -> None:
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is missing.")
    redis.from_url(settings.redis_url, decode_responses=True).ping()


async def wait_for_services(timeout_seconds: int = 60, interval_seconds: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            await _check_db()
            _check_redis()
            return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(interval_seconds)

    raise RuntimeError(f"Timed out waiting for database and Redis: {last_error}")


if __name__ == "__main__":
    asyncio.run(wait_for_services())
