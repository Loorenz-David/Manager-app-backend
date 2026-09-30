"""An in-memory stand-in for the shared async Redis client (hash + string commands).

Loop-agnostic, unlike the real shared client, so it works both under pytest-asyncio
and inside TestClient's own event loop. ``fail`` makes every command raise, as
redis-py does when the server is down; ``delay`` makes every command hang that long.
"""

from __future__ import annotations

import asyncio


class FakeAsyncRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int | None] = {}
        self.hset_calls: list[tuple[str, dict[str, str]]] = []
        self.set_calls: list[tuple[str, str, int | None]] = []
        self.fail: Exception | None = None
        self.delay: float = 0.0

    async def _io(self) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail is not None:
            raise self.fail

    async def hset(self, key: str, *, mapping: dict) -> int:
        await self._io()
        clean = {str(k): str(v) for k, v in mapping.items()}
        self.hset_calls.append((key, clean))
        self.hashes.setdefault(key, {}).update(clean)
        return len(clean)

    async def hgetall(self, key: str) -> dict[str, str]:
        await self._io()
        return dict(self.hashes.get(key, {}))

    async def set(self, key: str, value: str, *, ex: int | None = None) -> bool:
        await self._io()
        self.set_calls.append((key, value, ex))
        self.values[key] = value
        self.expirations[key] = ex
        return True

    async def get(self, key: str) -> str | None:
        await self._io()
        return self.values.get(key)

    async def ttl(self, key: str) -> int:
        if key not in self.values and key not in self.hashes:
            return -2
        expiration = self.expirations.get(key)
        return -1 if expiration is None else expiration
