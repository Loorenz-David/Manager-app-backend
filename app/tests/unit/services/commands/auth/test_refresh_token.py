from datetime import datetime, timedelta, timezone

import jwt
import pytest

import beyo_manager.services.commands.auth.refresh_token as refresh_module
from beyo_manager.config import settings
from beyo_manager.errors.permissions import RefreshTokenRejected
from beyo_manager.services.commands.auth.refresh_token import refresh_token
from beyo_manager.services.context import ServiceContext


@pytest.fixture(autouse=True)
def _unrevoked_refresh_token(monkeypatch) -> None:
    async def _is_blocklisted(_jti: str) -> bool:
        return False

    monkeypatch.setattr(
        refresh_module,
        "is_token_blocklisted",
        _is_blocklisted,
    )


@pytest.mark.unit
async def test_refresh_token_rejected_when_cookie_missing() -> None:
    ctx = ServiceContext(identity={}, incoming_data={"scope": "manager"}, session=None)  # type: ignore[arg-type]

    with pytest.raises(RefreshTokenRejected) as exc_info:
        await refresh_token(ctx)

    assert exc_info.value.code == "auth_refresh_rejected"
    assert exc_info.value.reason == "refresh_cookie_missing"


@pytest.mark.unit
async def test_refresh_token_rejected_when_cookie_invalid() -> None:
    ctx = ServiceContext(identity={}, incoming_data={"scope": "manager", "refresh_token": "bad-token"}, session=None)  # type: ignore[arg-type]

    with pytest.raises(RefreshTokenRejected) as exc_info:
        await refresh_token(ctx)

    assert exc_info.value.code == "auth_refresh_rejected"
    assert exc_info.value.reason == "refresh_token_invalid"


@pytest.mark.unit
async def test_refresh_token_returns_access_token_when_cookie_valid() -> None:
    now = datetime.now(timezone.utc)
    refresh = jwt.encode(
        {
            "user_id": "usr_test",
            "workspace_id": "ws_test",
            "app_scope": "manager",
            "jti": "refresh-jti",
            "exp": now + timedelta(days=1),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    ctx = ServiceContext(identity={}, incoming_data={"scope": "manager", "refresh_token": refresh}, session=None)  # type: ignore[arg-type]

    result = await refresh_token(ctx)
    access_claims = jwt.decode(
        result["access_token"],
        settings.jwt_secret_key,
        algorithms=["HS256"],
    )

    assert isinstance(result.get("access_token"), str)
    assert result["access_token"]
    assert access_claims["token_type"] == "access"


@pytest.mark.unit
async def test_refresh_token_rejected_when_scope_missing() -> None:
    ctx = ServiceContext(identity={}, incoming_data={"refresh_token": "bad-token"}, session=None)  # type: ignore[arg-type]

    with pytest.raises(RefreshTokenRejected) as exc_info:
        await refresh_token(ctx)

    assert exc_info.value.code == "auth_refresh_rejected"
    assert exc_info.value.reason == "refresh_scope_missing"


@pytest.mark.unit
async def test_refresh_token_rejected_when_scope_mismatches_claim() -> None:
    now = datetime.now(timezone.utc)
    refresh = jwt.encode(
        {
            "user_id": "usr_test",
            "workspace_id": "ws_test",
            "app_scope": "worker",
            "jti": "refresh-jti",
            "exp": now + timedelta(days=1),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    ctx = ServiceContext(identity={}, incoming_data={"scope": "manager", "refresh_token": refresh}, session=None)  # type: ignore[arg-type]

    with pytest.raises(RefreshTokenRejected) as exc_info:
        await refresh_token(ctx)

    assert exc_info.value.code == "auth_refresh_rejected"
    assert exc_info.value.reason == "scope_mismatch"


@pytest.mark.unit
async def test_floor_scope_guard_rejects_floor_access_token_before_reading_the_blocklist(
    monkeypatch,
) -> None:
    """Named for what it proves: the floor-scope guard rejects first.

    The blocklist stub below never gets called — the scope guard raises before any
    revocation lookup (phase 5 review finding R3-1). Renamed in phase 6; assertions
    unchanged. Actual revocation enforcement is covered by the integration probes in
    `tests/integration/services/commands/auth/`.
    """
    async def _is_blocklisted(jti: str) -> bool:
        assert jti == "device-jti"
        return True

    monkeypatch.setattr(
        refresh_module,
        "is_token_blocklisted",
        _is_blocklisted,
    )
    floor_access_token = jwt.encode(
        {
            "user_id": "usr_manager",
            "workspace_id": "ws_test",
            "role_name": "manager",
            "app_scope": "floor",
            "jti": "device-jti",
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    ctx = ServiceContext(
        identity={},
        incoming_data={
            "scope": "floor",
            "refresh_token": floor_access_token,
        },
        session=None,  # type: ignore[arg-type]
    )

    with pytest.raises(RefreshTokenRejected):
        await refresh_token(ctx)


@pytest.mark.unit
async def test_floor_scope_refresh_rejected_even_with_valid_refresh_token() -> None:
    now = datetime.now(timezone.utc)
    refresh = jwt.encode(
        {
            "user_id": "usr_manager",
            "workspace_id": "ws_test",
            "app_scope": "floor",
            "jti": "floor-refresh-jti",
            "token_type": "refresh",
            "exp": now + timedelta(days=1),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    ctx = ServiceContext(
        identity={},
        incoming_data={"scope": "floor", "refresh_token": refresh},
        session=None,  # type: ignore[arg-type]
    )

    with pytest.raises(RefreshTokenRejected) as exc_info:
        await refresh_token(ctx)

    assert exc_info.value.reason == "floor_scope_not_refreshable"


@pytest.mark.unit
async def test_revoked_non_floor_refresh_token_is_rejected(monkeypatch) -> None:
    async def _is_blocklisted(jti: str) -> bool:
        assert jti == "revoked-refresh-jti"
        return True

    monkeypatch.setattr(
        refresh_module,
        "is_token_blocklisted",
        _is_blocklisted,
    )
    now = datetime.now(timezone.utc)
    refresh = jwt.encode(
        {
            "user_id": "usr_manager",
            "workspace_id": "ws_test",
            "app_scope": "manager",
            "jti": "revoked-refresh-jti",
            "token_type": "refresh",
            "exp": now + timedelta(days=1),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    ctx = ServiceContext(
        identity={},
        incoming_data={"scope": "manager", "refresh_token": refresh},
        session=None,  # type: ignore[arg-type]
    )

    with pytest.raises(RefreshTokenRejected) as exc_info:
        await refresh_token(ctx)

    assert exc_info.value.reason == "refresh_token_revoked"


@pytest.mark.unit
async def test_regular_access_token_cannot_be_used_as_refresh_cookie() -> None:
    now = datetime.now(timezone.utc)
    access_token = jwt.encode(
        {
            "user_id": "usr_manager",
            "workspace_id": "ws_test",
            "app_scope": "manager",
            "jti": "access-jti",
            "token_type": "access",
            "exp": now + timedelta(minutes=30),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    ctx = ServiceContext(
        identity={},
        incoming_data={"scope": "manager", "refresh_token": access_token},
        session=None,  # type: ignore[arg-type]
    )

    with pytest.raises(RefreshTokenRejected) as exc_info:
        await refresh_token(ctx)

    assert exc_info.value.reason == "refresh_token_invalid"


@pytest.mark.unit
async def test_exp_less_token_cannot_be_used_as_non_floor_refresh_cookie() -> None:
    access_token = jwt.encode(
        {
            "user_id": "usr_manager",
            "workspace_id": "ws_test",
            "app_scope": "manager",
            "jti": "exp-less-access-jti",
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    ctx = ServiceContext(
        identity={},
        incoming_data={"scope": "manager", "refresh_token": access_token},
        session=None,  # type: ignore[arg-type]
    )

    with pytest.raises(RefreshTokenRejected) as exc_info:
        await refresh_token(ctx)

    assert exc_info.value.reason == "refresh_token_invalid"


@pytest.mark.unit
async def test_legacy_expiring_typeless_refresh_token_still_works() -> None:
    now = datetime.now(timezone.utc)
    legacy_refresh = jwt.encode(
        {
            "user_id": "usr_manager",
            "workspace_id": "ws_test",
            "app_scope": "manager",
            "jti": "legacy-refresh-jti",
            "exp": now + timedelta(days=1),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    ctx = ServiceContext(
        identity={},
        incoming_data={"scope": "manager", "refresh_token": legacy_refresh},
        session=None,  # type: ignore[arg-type]
    )

    result = await refresh_token(ctx)

    assert result["access_token"]


@pytest.mark.unit
async def test_refresh_fails_closed_when_blocklist_is_unavailable(monkeypatch) -> None:
    async def _blocklist_unavailable(_jti: str) -> bool:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(
        refresh_module,
        "is_token_blocklisted",
        _blocklist_unavailable,
    )
    now = datetime.now(timezone.utc)
    refresh = jwt.encode(
        {
            "user_id": "usr_manager",
            "workspace_id": "ws_test",
            "app_scope": "manager",
            "jti": "refresh-jti",
            "token_type": "refresh",
            "exp": now + timedelta(days=1),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    ctx = ServiceContext(
        identity={},
        incoming_data={"scope": "manager", "refresh_token": refresh},
        session=None,  # type: ignore[arg-type]
    )

    with pytest.raises(RefreshTokenRejected) as exc_info:
        await refresh_token(ctx)

    assert exc_info.value.reason == "refresh_blocklist_unavailable"
