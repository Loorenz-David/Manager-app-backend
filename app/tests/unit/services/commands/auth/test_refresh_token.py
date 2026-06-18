from datetime import datetime, timedelta, timezone

import jwt
import pytest

from beyo_manager.config import settings
from beyo_manager.errors.permissions import RefreshTokenRejected
from beyo_manager.services.commands.auth.refresh_token import refresh_token
from beyo_manager.services.context import ServiceContext


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

    assert isinstance(result.get("access_token"), str)
    assert result["access_token"]


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
