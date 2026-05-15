import logging
import time

from beyo_manager.config import settings
from beyo_manager.services.infra.redis import get_redis_client

logger = logging.getLogger(__name__)

_SLEEP_KEY    = "{prefix}:system:sleeping"
_ACTIVITY_KEY = "{prefix}:system:last_activity"
_ACTIVITY_TTL = 86400  # 24h — prevents stale key if app never restarts


def _key(k: str) -> str:
    return k.replace("{prefix}", settings.redis_key_prefix)


class ActivityTracker:
    """Redis-backed sleep/wake state shared across all processes."""

    @classmethod
    def touch(cls) -> None:
        r = get_redis_client(settings.redis_url)
        was_sleeping = r.exists(_key(_SLEEP_KEY))
        r.delete(_key(_SLEEP_KEY))
        r.set(_key(_ACTIVITY_KEY), str(time.time()), ex=_ACTIVITY_TTL)
        if was_sleeping:
            logger.info("app_wake | activity detected")

    @classmethod
    def is_sleeping(cls) -> bool:
        return bool(get_redis_client(settings.redis_url).exists(_key(_SLEEP_KEY)))

    @classmethod
    def enter_sleep(cls) -> None:
        get_redis_client(settings.redis_url).set(_key(_SLEEP_KEY), "1")
        logger.info("app_sleep | entering sleep mode after idle")

    @classmethod
    def idle_seconds(cls) -> float:
        val = get_redis_client(settings.redis_url).get(_key(_ACTIVITY_KEY))
        return 0.0 if val is None else time.time() - float(val)
