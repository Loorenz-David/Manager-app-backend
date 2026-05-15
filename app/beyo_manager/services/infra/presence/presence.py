from beyo_manager.config import settings
from beyo_manager.services.infra.redis import get_redis_client, make_key

PRESENCE_TTL_SECONDS = 90


def _key(entity_type: str, entity_client_id: str) -> str:
    return make_key("presence", entity_type, entity_client_id)


def mark_viewing(entity_type: str, entity_client_id: str, user_id: str) -> None:
    r = get_redis_client(settings.redis_url)
    key = _key(entity_type, entity_client_id)
    r.sadd(key, user_id)
    r.expire(key, PRESENCE_TTL_SECONDS)


def mark_left(entity_type: str, entity_client_id: str, user_id: str) -> None:
    r = get_redis_client(settings.redis_url)
    r.srem(_key(entity_type, entity_client_id), user_id)


def get_viewers(entity_type: str, entity_client_id: str) -> set[str]:
    r = get_redis_client(settings.redis_url)
    return set(r.smembers(_key(entity_type, entity_client_id)))
