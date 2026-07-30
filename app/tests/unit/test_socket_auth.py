import jwt
import pytest

from beyo_manager.config import settings
from beyo_manager.sockets import handlers


def _access_token(*, jti: str) -> str:
    return jwt.encode(
        {
            "user_id": "usr_floor",
            "workspace_id": "ws_floor",
            "username": "floor manager",
            "app_scope": "floor",
            "jti": jti,
            "token_type": "access",
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )


@pytest.mark.unit
async def test_revoked_token_is_rejected_by_socket_auth(monkeypatch) -> None:
    async def _is_blocklisted(jti: str) -> bool:
        assert jti == "revoked-socket-jti"
        return True

    async def _unexpected_connect(*_args, **_kwargs) -> None:
        raise AssertionError("revoked socket token must not connect")

    monkeypatch.setattr(handlers, "is_token_blocklisted", _is_blocklisted)
    monkeypatch.setattr(handlers.manager, "connect", _unexpected_connect)

    accepted = await handlers._handle_connect(
        "sid-revoked",
        {},
        {"token": _access_token(jti="revoked-socket-jti")},
    )

    assert accepted is False


@pytest.mark.unit
async def test_socket_auth_fails_closed_when_blocklist_is_unavailable(
    monkeypatch,
) -> None:
    async def _blocklist_unavailable(_jti: str) -> bool:
        raise RuntimeError("redis unavailable")

    async def _unexpected_connect(*_args, **_kwargs) -> None:
        raise AssertionError("socket must not connect without blocklist verification")

    monkeypatch.setattr(
        handlers,
        "is_token_blocklisted",
        _blocklist_unavailable,
    )
    monkeypatch.setattr(handlers.manager, "connect", _unexpected_connect)

    accepted = await handlers._handle_connect(
        "sid-no-redis",
        {},
        {"token": _access_token(jti="socket-jti")},
    )

    assert accepted is False
