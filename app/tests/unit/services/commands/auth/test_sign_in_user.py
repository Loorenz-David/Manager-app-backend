from types import SimpleNamespace

import bcrypt
import pytest

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.services.commands.auth.sign_in_user import sign_in_user
from beyo_manager.services.context import ServiceContext

_DEFAULT_WORKSPACE_ROLE_NAME = object()


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
    workspace_role_name: str | None | object = _DEFAULT_WORKSPACE_ROLE_NAME,
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
        name=role_name.value if workspace_role_name is _DEFAULT_WORKSPACE_ROLE_NAME else workspace_role_name,
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
async def test_sign_in_user_falls_back_to_permission_role_name_for_system_workspace_roles() -> None:
    result = await sign_in_user(
        _ctx(role_name=RoleNameEnum.MANAGER, app_scope="manager", workspace_role_name=None)
    )

    assert result["user"]["role"] == "manager"


@pytest.mark.unit
async def test_sign_in_user_preserves_custom_workspace_role_name() -> None:
    result = await sign_in_user(
        _ctx(role_name=RoleNameEnum.WORKER, app_scope="worker", workspace_role_name="wood_worker")
    )

    assert result["user"]["role"] == "wood_worker"
