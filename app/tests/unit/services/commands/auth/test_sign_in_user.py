import logging
from types import SimpleNamespace

import bcrypt
import jwt
import pytest

from beyo_manager.config import settings
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.services.commands.auth.sign_in_user import sign_in_user
from beyo_manager.services.context import ServiceContext

_DEFAULT_WORKSPACE_SPECIALIZATION = object()


def _hashed_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, user, membership, workspace):
        self._execute_calls = 0
        self._user = user
        self._membership = membership
        self._workspace = workspace

    async def execute(self, _query):
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _ScalarResult(self._user)
        return _ScalarResult(self._membership)

    async def get(self, _model, _workspace_id):
        return self._workspace


def _ctx(
    *,
    role_name: RoleNameEnum,
    app_scope: str,
    workspace_specialization: str | None | object = _DEFAULT_WORKSPACE_SPECIALIZATION,
):
    user = SimpleNamespace(
        client_id="usr_1",
        email="user@test.local",
        username="user",
        password=_hashed_password("Test1234!"),
    )
    role = SimpleNamespace(name=role_name)
    workspace_role = SimpleNamespace(
        client_id="wsr_1",
        role=role,
        specialization=(
            None
            if workspace_specialization is _DEFAULT_WORKSPACE_SPECIALIZATION
            else workspace_specialization
        ),
    )
    membership = SimpleNamespace(workspace_id="ws_1", workspace_role=workspace_role)
    workspace = SimpleNamespace(client_id="ws_1", time_zone="UTC")
    session = _Session(user, membership, workspace)
    return ServiceContext(
        identity={},
        incoming_data={"email": user.email, "password": "Test1234!", "app_scope": app_scope},
        session=session,  # type: ignore[arg-type]
    )


@pytest.mark.unit
async def test_sign_in_user_allows_admin_role_for_manager_scope() -> None:
    result = await sign_in_user(_ctx(role_name=RoleNameEnum.ADMIN, app_scope="manager"))

    assert result["access_token"]
    assert result["_refresh_token"]


@pytest.mark.unit
async def test_sign_in_user_allows_manager_role_for_worker_scope() -> None:
    result = await sign_in_user(_ctx(role_name=RoleNameEnum.MANAGER, app_scope="worker"))

    assert result["access_token"]
    assert result["_refresh_token"]


@pytest.mark.unit
async def test_sign_in_user_rejects_unknown_scope() -> None:
    with pytest.raises(PermissionDenied, match="Invalid credentials."):
        await sign_in_user(_ctx(role_name=RoleNameEnum.MANAGER, app_scope="unknown_scope"))


@pytest.mark.unit
async def test_sign_in_user_rejects_seller_role_for_manager_scope() -> None:
    with pytest.raises(PermissionDenied, match="Invalid credentials."):
        await sign_in_user(_ctx(role_name=RoleNameEnum.SELLER, app_scope="manager"))


@pytest.mark.unit
async def test_sign_in_user_allows_seller_role_for_seller_scope() -> None:
    result = await sign_in_user(_ctx(role_name=RoleNameEnum.SELLER, app_scope="seller"))

    assert result["access_token"]
    assert result["_refresh_token"]


@pytest.mark.unit
async def test_sign_in_user_falls_back_to_permission_role_name_for_system_workspace_roles() -> None:
    result = await sign_in_user(
        _ctx(role_name=RoleNameEnum.MANAGER, app_scope="manager", workspace_specialization=None)
    )

    assert result["user"]["workspace_role_name"] == "manager"
    assert result["user"]["workspace_specialization"] is None


@pytest.mark.unit
async def test_sign_in_user_preserves_custom_workspace_role_name() -> None:
    result = await sign_in_user(
        _ctx(role_name=RoleNameEnum.WORKER, app_scope="worker", workspace_specialization="wood_worker")
    )

    assert result["user"]["workspace_role_name"] == "wood_worker"
    assert result["user"]["workspace_specialization"] == "wood_worker"


@pytest.mark.unit
@pytest.mark.parametrize("role_name", [RoleNameEnum.ADMIN, RoleNameEnum.MANAGER])
async def test_sign_in_user_allows_floor_scope_for_device_roles(
    role_name: RoleNameEnum,
) -> None:
    result = await sign_in_user(_ctx(role_name=role_name, app_scope="floor"))
    claims = jwt.decode(
        result["access_token"],
        settings.jwt_secret_key,
        algorithms=["HS256"],
    )

    assert set(result) == {"access_token", "user", "workspace_id"}
    assert result["workspace_id"] == "ws_1"
    assert result["user"]["user_id"] == "usr_1"
    assert result["user"]["workspace_id"] == "ws_1"
    assert result["user"]["role_name"] == role_name.value
    assert result["user"]["app_scope"] == "floor"
    assert claims["app_scope"] == "floor"
    assert claims["jti"]
    assert "exp" not in claims


@pytest.mark.unit
@pytest.mark.parametrize("role_name", [RoleNameEnum.WORKER, RoleNameEnum.SELLER])
async def test_sign_in_user_rejects_floor_scope_for_non_device_roles_opaquely(
    role_name: RoleNameEnum,
) -> None:
    with pytest.raises(PermissionDenied, match=r"^Invalid credentials\.$"):
        await sign_in_user(_ctx(role_name=role_name, app_scope="floor"))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("app_scope", "role_name"),
    [
        ("manager", RoleNameEnum.MANAGER),
        ("worker", RoleNameEnum.WORKER),
        ("seller", RoleNameEnum.SELLER),
        ("admin", RoleNameEnum.ADMIN),
    ],
)
async def test_existing_scopes_keep_expiring_access_and_refresh_tokens(
    app_scope: str,
    role_name: RoleNameEnum,
) -> None:
    result = await sign_in_user(_ctx(role_name=role_name, app_scope=app_scope))

    access_claims = jwt.decode(
        result["access_token"],
        settings.jwt_secret_key,
        algorithms=["HS256"],
    )
    refresh_claims = jwt.decode(
        result["_refresh_token"],
        settings.jwt_secret_key,
        algorithms=["HS256"],
    )

    assert access_claims["exp"]
    assert refresh_claims["exp"]
    assert access_claims["app_scope"] == app_scope
    assert refresh_claims["app_scope"] == app_scope


@pytest.mark.unit
async def test_floor_sign_in_emits_structured_device_log(caplog) -> None:
    with caplog.at_level(
        logging.INFO,
        logger="beyo_manager.services.commands.auth.sign_in_user",
    ):
        await sign_in_user(_ctx(role_name=RoleNameEnum.MANAGER, app_scope="floor"))

    record = next(
        record
        for record in caplog.records
        if record.getMessage().startswith("auth.floor_device_sign_in")
    )
    assert record.event_type == "auth.floor_device_sign_in"
    assert record.service == "auth"
    assert record.user_id == "usr_1"
    assert record.workspace_id == "ws_1"
