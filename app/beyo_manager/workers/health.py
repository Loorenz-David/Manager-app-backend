from __future__ import annotations

import redis

from beyo_manager.config import settings


def worker_healthcheck() -> dict[str, str]:
    client = redis.from_url(settings.redis_url, decode_responses=True)
    pong = client.ping()
    return {"redis": "ok" if pong else "error"}
