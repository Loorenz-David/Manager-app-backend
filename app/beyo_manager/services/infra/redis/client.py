import redis


def get_redis_client(redis_uri: str | None):
    if not redis_uri:
        raise RuntimeError("Redis URI is not configured.")
    return redis.from_url(redis_uri, decode_responses=True)


def assert_redis_available(redis_uri: str | None) -> None:
    get_redis_client(redis_uri).ping()
