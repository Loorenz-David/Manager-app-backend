from __future__ import annotations

from .interfaces import EventStore


class InMemoryEventStore(EventStore):
    async def list_failed_events(self, limit: int = 100) -> list[dict]:
        return []

    async def list_failed_jobs(self, limit: int = 100) -> list[dict]:
        return []

    async def list_failed_webhooks(self, limit: int = 100) -> list[dict]:
        return []
