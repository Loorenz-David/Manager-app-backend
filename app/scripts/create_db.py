import asyncio
import re
import time

import asyncpg

from beyo_manager.config import settings


def _admin_dsn(database_url: str) -> tuple[str, str]:
    """Return (admin_dsn, db_name) derived from DATABASE_URL."""
    dsn = re.sub(r"^postgresql\+asyncpg://", "postgresql://", database_url)
    match = re.match(r"(.*)/([^/?]+)(\?.*)?$", dsn)
    if not match:
        raise RuntimeError(f"Cannot parse DATABASE_URL: {database_url!r}")
    return match.group(1) + "/postgres", match.group(2)


async def create_db_if_missing(timeout_seconds: int = 60, interval: float = 1.0) -> None:
    admin_dsn, db_name = _admin_dsn(settings.database_url)
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            conn = await asyncpg.connect(admin_dsn, timeout=5)
            try:
                exists = await conn.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = $1", db_name
                )
                if not exists:
                    await conn.execute(f'CREATE DATABASE "{db_name}"')
                    print(f"[create-db] Created database: {db_name}")
                else:
                    print(f"[create-db] Database already exists: {db_name}")
                return
            finally:
                await conn.close()
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(interval)

    raise RuntimeError(
        f"Could not create database '{db_name}' after {timeout_seconds}s: {last_error}"
    )


if __name__ == "__main__":
    asyncio.run(create_db_if_missing())
