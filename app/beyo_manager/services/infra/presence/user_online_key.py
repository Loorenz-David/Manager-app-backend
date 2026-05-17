from beyo_manager.services.infra.redis.async_client import get_async_redis
from beyo_manager.services.infra.redis.keys import make_key

_USER_ONLINE_TTL_SECONDS = 86400


def _key(user_id: str) -> str:
    return make_key("user_online", user_id)


async def set_user_online(user_id: str) -> None:
    r = get_async_redis()
    await r.set(_key(user_id), "1", ex=_USER_ONLINE_TTL_SECONDS)


async def delete_user_online(user_id: str) -> None:
    r = get_async_redis()
    await r.delete(_key(user_id))
