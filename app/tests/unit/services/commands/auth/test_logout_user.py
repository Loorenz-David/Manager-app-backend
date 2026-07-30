import logging
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from beyo_manager.config import settings
from beyo_manager.routers.utils import jwt_dep
from beyo_manager.services.commands.auth import logout_user as logout_module
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.redis import async_client


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int | None] = {}

    async def set(self, key: str, value: str, *, ex: int | None = None) -> None:
        self.values[key] = value
        self.expirations[key] = ex

    async def ttl(self, key: str) -> int:
        if key not in self.values:
            return -2
        expiration = self.expirations[key]
        return -1 if expiration is None else expiration

    async def exists(self, key: str) -> int:
        return int(key in self.values)


@pytest.fixture
def fake_redis(monkeypatch) -> _FakeRedis:
    redis = _FakeRedis()
    monkeypatch.setattr(async_client, "get_async_redis", lambda: redis)
    return redis


@pytest.mark.unit
async def test_blocklist_token_without_exp_has_no_ttl(fake_redis: _FakeRedis) -> None:
    await logout_module._blocklist_token({"jti": "floor-jti"})

    key = f"{settings.redis_key_prefix}:auth:blocklist:floor-jti"
    assert await fake_redis.ttl(key) == -1


@pytest.mark.unit
async def test_expiring_token_keeps_existing_blocklist_ttl(
    fake_redis: _FakeRedis,
    monkeypatch,
) -> None:
    monkeypatch.setattr(logout_module.time, "time", lambda: 1_000.0)

    await logout_module._blocklist_token({"jti": "manager-jti", "exp": 1_100.0})

    key = f"{settings.redis_key_prefix}:auth:blocklist:manager-jti"
    assert await fake_redis.ttl(key) == 160


@pytest.mark.unit
async def test_floor_logout_permanently_revokes_subsequent_request(
    fake_redis: _FakeRedis,
) -> None:
    token = jwt.encode(
        {
            "user_id": "usr_floor",
            "workspace_id": "ws_floor",
            "app_scope": "floor",
            "jti": "lost-device-jti",
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    claims = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
    )
    ctx = ServiceContext(
        identity=claims,
        incoming_data={"refresh_token": None},
        session=None,  # type: ignore[arg-type]
    )

    result = await logout_module.logout_user(ctx)

    key = f"{settings.redis_key_prefix}:auth:blocklist:lost-device-jti"
    assert result == {"logged_out": True}
    assert await fake_redis.ttl(key) == -1

    jwt_dep._claim_cache.clear()
    with pytest.raises(HTTPException) as exc_info:
        await jwt_dep.get_jwt_claims(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )

    assert exc_info.value.status_code == 401


@pytest.mark.unit
async def test_refresh_token_logout_ttl_remains_expiring(
    fake_redis: _FakeRedis,
    monkeypatch,
) -> None:
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(logout_module.time, "time", lambda: now.timestamp())
    refresh = jwt.encode(
        {
            "jti": "refresh-jti",
            "exp": now + timedelta(seconds=300),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    decoded_refresh = jwt.decode(
        refresh,
        settings.jwt_secret_key,
        algorithms=["HS256"],
    )
    expected_refresh_ttl = max(
        int(decoded_refresh["exp"] - now.timestamp()) + 60,
        1,
    )
    ctx = ServiceContext(
        identity={"jti": "access-jti", "exp": now.timestamp() + 100},
        incoming_data={"refresh_token": refresh},
        session=None,  # type: ignore[arg-type]
    )

    await logout_module.logout_user(ctx)

    prefix = settings.redis_key_prefix
    assert await fake_redis.ttl(f"{prefix}:auth:blocklist:access-jti") == 160
    assert (
        await fake_redis.ttl(f"{prefix}:auth:blocklist:refresh-jti")
        == expected_refresh_ttl
    )


@pytest.mark.unit
async def test_floor_logout_log_contains_revoked_jti(
    fake_redis: _FakeRedis,
    caplog,
) -> None:
    ctx = ServiceContext(
        identity={
            "user_id": "usr_floor",
            "workspace_id": "ws_floor",
            "app_scope": "floor",
            "jti": "retired-device-jti",
        },
        incoming_data={"refresh_token": None},
        session=None,  # type: ignore[arg-type]
    )

    with caplog.at_level(
        logging.INFO,
        logger="beyo_manager.services.commands.auth.logout_user",
    ):
        await logout_module.logout_user(ctx)

    record = next(
        record
        for record in caplog.records
        if record.getMessage().startswith("auth.floor_device_logout")
    )
    assert record.user_id == "usr_floor"
    assert record.workspace_id == "ws_floor"
    assert record.jti == "retired-device-jti"
