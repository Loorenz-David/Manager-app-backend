from beyo_manager.config import settings


def make_key(namespace: str, *parts: object) -> str:
    clean = [str(p).strip(":") for p in parts if p is not None and str(p) != ""]
    return ":".join([settings.redis_key_prefix, namespace, *clean])
