from __future__ import annotations

import redis
from rq import Queue

from beyo_manager.config import settings
from beyo_manager.queues.registry import QUEUE_NAMES


def queue_for(name: str) -> Queue:
    if name not in QUEUE_NAMES:
        raise RuntimeError(f"Unknown queue '{name}'. Known queues: {', '.join(QUEUE_NAMES)}")
    conn = redis.from_url(settings.redis_url)
    return Queue(name, connection=conn)
