from __future__ import annotations


class EventStore:
    async def list_failed_events(self, limit: int = 100) -> list[dict]:
        raise NotImplementedError

    async def list_failed_jobs(self, limit: int = 100) -> list[dict]:
        raise NotImplementedError

    async def list_failed_webhooks(self, limit: int = 100) -> list[dict]:
        raise NotImplementedError
