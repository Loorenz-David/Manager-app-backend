import pytest

from beyo_manager.config import settings
from beyo_manager.services.commands.auth.logout_user import logout_user
from beyo_manager.services.context import ServiceContext


@pytest.mark.integration
async def test_floor_logout_blocklist_has_no_ttl_in_real_redis(
    redis_client,
    isolated_redis_prefix: str,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "redis_key_prefix", isolated_redis_prefix)
    jti = "real-redis-floor-jti"
    key = f"{isolated_redis_prefix}:auth:blocklist:{jti}"
    redis_client.set(key, "stale", ex=60)
    ctx = ServiceContext(
        identity={
            "user_id": "usr_floor",
            "workspace_id": "ws_floor",
            "app_scope": "floor",
            "jti": jti,
        },
        incoming_data={"refresh_token": None},
        session=None,  # type: ignore[arg-type]
    )

    await logout_user(ctx)

    assert redis_client.get(key) == "1"
    assert redis_client.ttl(key) == -1
