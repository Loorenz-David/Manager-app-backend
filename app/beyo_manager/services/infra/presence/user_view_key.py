import json

from beyo_manager.services.infra.redis import make_key
from beyo_manager.services.infra.redis.async_client import get_async_redis

_USER_VIEW_TTL_SECONDS = 86400  # 24 hours


def _key(user_id: str) -> str:
    return make_key("user_view", user_id)


async def set_user_view(user_id: str, entity_type: str, entity_client_id: str) -> None:
    r = get_async_redis()
    await r.set(
        _key(user_id),
        json.dumps({"entity_type": entity_type, "entity_client_id": entity_client_id}),
        ex=_USER_VIEW_TTL_SECONDS,
    )


async def clear_user_view_if_matches(user_id: str, entity_type: str, entity_client_id: str) -> None:
    r = get_async_redis()
    key = _key(user_id)
    raw = await r.get(key)
    if raw is not None:
        current = json.loads(raw)
        if current.get("entity_type") == entity_type and current.get("entity_client_id") == entity_client_id:
            await r.delete(key)


async def get_user_view(user_id: str) -> dict | None:
    r = get_async_redis()
    raw = await r.get(_key(user_id))
    if raw is None:
        return None
    return json.loads(raw)
