from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

import beyo_manager.models.database as _db


@asynccontextmanager
async def task_db_session() -> AsyncIterator[AsyncSession]:
    """Async context manager for background task handlers."""
    if _db._session_factory is None:
        raise RuntimeError("DB not initialised. Call init_db() before running workers.")
    async with _db._session_factory() as session:
        yield session
