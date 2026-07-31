"""Floor-scope-only worker identification fields in the roster query.

Phase 6 acceptance 3 and 4 (D13 rev 3): a `floor` session's `GET /users` items gain
`clock_in_code` and `email`; every other app scope gets a response that is
byte-identical to the pre-phase one — the fields are ABSENT, not null. Codes are
fetched in one batched query for the page.

There were no pre-existing `list_users` tests to leave unmodified, so the shape pins
below stand in for that regression proof: they assert the exact key sets of both
serialized modes.
"""

from uuid import uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, event as sa_event, select

from beyo_manager import create_app
from beyo_manager.config import settings
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.database import get_db
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.domain.workspaces.enums import WorkspaceSpecializationEnum
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.users.list_users import list_users


pytestmark = pytest.mark.asyncio

# The serialized shapes as they exist WITHOUT this phase's additions.
_COMPACT_KEYS = {"client_id", "username", "profile_picture", "role", "workspace_role"}
_FULL_KEYS = {
    "client_id",
    "username",
    "email",
    "phone_number",
    "profile_picture",
    "role",
    "workspace_role",
    "working_sections",
}
_IDENTIFICATION_KEYS = {"clock_in_code", "email"}
_FLOOR_COMPACT_KEYS = _COMPACT_KEYS | _IDENTIFICATION_KEYS | {"working_sections"}

_NON_FLOOR_SCOPES = ["manager", "worker", "admin", "seller", None]


class _Roster:
    def __init__(self, db_session, workspace_id: str, label: str) -> None:
        self._db_session = db_session
        self.workspace_id = workspace_id
        self.label = label
        self.user_ids: list[str] = []
        self.codes: dict[str, str | None] = {}
        self.emails: dict[str, str] = {}

    async def seed_worker(
        self,
        *,
        clock_in_code: str | None,
        with_work_profile: bool = True,
        specialization: WorkspaceSpecializationEnum | None = None,
    ) -> str:
        suffix = uuid4().hex
        user = User(
            username=f"{self.label}-{suffix}",
            email=f"{self.label}-{suffix}@example.com",
            password="test-password-hash",
        )
        self._db_session.add(user)
        await self._db_session.flush()
        role = (
            await self._db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))
        ).scalar_one()
        specialization_clause = (
            WorkspaceRole.specialization.is_(None)
            if specialization is None
            else WorkspaceRole.specialization == specialization
        )
        workspace_role = await self._db_session.scalar(
            select(WorkspaceRole)
            .where(
                WorkspaceRole.workspace_id == self.workspace_id,
                WorkspaceRole.role_id == role.client_id,
                specialization_clause,
            )
            .limit(1)
        )
        if workspace_role is None:
            workspace_role = WorkspaceRole(
                workspace_id=self.workspace_id,
                role_id=role.client_id,
                specialization=specialization,
                is_system=True,
            )
            self._db_session.add(workspace_role)
            await self._db_session.flush()
        self._db_session.add(
            WorkspaceMembership(
                user_id=user.client_id,
                workspace_id=self.workspace_id,
                workspace_role_id=workspace_role.client_id,
                is_active=True,
            )
        )
        if with_work_profile:
            self._db_session.add(
                UserWorkProfile(
                    user_id=user.client_id,
                    workspace_id=self.workspace_id,
                    clock_in_code=clock_in_code,
                    created_by_id=user.client_id,
                )
            )
        await self._db_session.flush()
        self.user_ids.append(user.client_id)
        self.codes[user.client_id] = clock_in_code
        self.emails[user.client_id] = user.email
        return user.client_id

    def ctx(
        self,
        *,
        app_scope: str | None,
        compact: bool,
        role: str | None = RoleNameEnum.WORKER.value,
        limit: int = 50,
    ) -> ServiceContext:
        identity = {
            "workspace_id": self.workspace_id,
            "user_id": self.user_ids[0],
            "role_name": RoleNameEnum.MANAGER.value,
        }
        if app_scope is not None:
            identity["app_scope"] = app_scope
        return ServiceContext(
            identity=identity,
            incoming_data={},
            session=self._db_session,
            query_params={
                "q": self.label,
                "string_filters": "username",
                "role": role,
                "working_sections": None,
                "limit": str(limit),
                "offset": "0",
                "compact": str(compact),
            },
        )

    async def items(
        self,
        *,
        app_scope: str | None,
        compact: bool,
        role: str | None = RoleNameEnum.WORKER.value,
        limit: int = 50,
    ) -> dict[str, dict]:
        result = await list_users(
            self.ctx(app_scope=app_scope, compact=compact, role=role, limit=limit)
        )
        return {item["client_id"]: item for item in result["users"]}


@pytest.fixture
def executed_statements():
    """Every SQL statement this test issues, for the no-N+1 proof.

    Local on purpose: the shared `count_queries` fixture binds the engine through a
    session-scoped fixture that resolves before `init_db()` creates it, so it raises
    on first use (it has no other consumers in the suite).
    """
    from beyo_manager.models import database

    engine = database._engine
    assert engine is not None, "init_db() must have run before this fixture"
    statements: list[str] = []

    @sa_event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    yield statements

    sa_event.remove(engine.sync_engine, "before_cursor_execute", _record)


@pytest_asyncio.fixture
async def roster(db_session):
    workspace_id = await db_session.scalar(
        select(Workspace.client_id).order_by(Workspace.client_id).limit(1)
    )
    # A label unique to this test run keeps the `q` filter scoped to our own rows.
    fixture = _Roster(db_session, workspace_id, f"rosteruser{uuid4().hex}")
    try:
        yield fixture
    finally:
        await db_session.rollback()
        await db_session.execute(
            delete(UserWorkProfile).where(UserWorkProfile.user_id.in_(fixture.user_ids))
        )
        await db_session.execute(
            delete(WorkspaceMembership).where(WorkspaceMembership.user_id.in_(fixture.user_ids))
        )
        await db_session.execute(delete(User).where(User.client_id.in_(fixture.user_ids)))
        await db_session.commit()


@pytest.mark.parametrize("compact", [True, False])
async def test_floor_session_receives_clock_in_code_and_email(roster, compact: bool) -> None:
    code = uuid4().hex[:8]
    with_code = await roster.seed_worker(clock_in_code=code)
    without_code = await roster.seed_worker(clock_in_code=None)
    # A worker with no work-profile row at all must still serialize cleanly.
    without_profile = await roster.seed_worker(clock_in_code=None, with_work_profile=False)

    items = await roster.items(app_scope="floor", compact=compact)

    expected_keys = _FLOOR_COMPACT_KEYS if compact else _FULL_KEYS | _IDENTIFICATION_KEYS
    for user_id in (with_code, without_code, without_profile):
        assert set(items[user_id]) == expected_keys
        assert items[user_id]["email"] == roster.emails[user_id]
    assert items[with_code]["clock_in_code"] == code
    assert items[without_code]["clock_in_code"] is None
    assert items[without_profile]["clock_in_code"] is None
    if compact:
        assert all(items[user_id]["working_sections"] == [] for user_id in items)


@pytest.mark.parametrize("app_scope", _NON_FLOOR_SCOPES)
@pytest.mark.parametrize("compact", [True, False])
async def test_non_floor_scopes_never_receive_identification_fields(
    roster,
    app_scope: str | None,
    compact: bool,
) -> None:
    user_id = await roster.seed_worker(clock_in_code=uuid4().hex[:8])

    items = await roster.items(app_scope=app_scope, compact=compact)

    item = items[user_id]
    assert set(item) == (_COMPACT_KEYS if compact else _FULL_KEYS)
    # Absent, not null: a `null` here would still leak that the field exists.
    assert "clock_in_code" not in item
    if compact:
        assert "email" not in item
        assert "working_sections" not in item


@pytest.mark.parametrize("compact", [True, False])
async def test_floor_response_adds_only_floor_compact_fields(
    roster,
    compact: bool,
) -> None:
    code = uuid4().hex[:8]
    user_id = await roster.seed_worker(clock_in_code=code)

    floor_item = (await roster.items(app_scope="floor", compact=compact))[user_id]
    manager_item = (await roster.items(app_scope="manager", compact=compact))[user_id]

    floor_only_keys = _IDENTIFICATION_KEYS | ({"working_sections"} if compact else set())
    stripped = {key: value for key, value in floor_item.items() if key not in floor_only_keys}
    if not compact:
        # `email` is part of the pre-phase full shape; put it back before comparing.
        stripped["email"] = floor_item["email"]
    assert stripped == manager_item


async def test_floor_code_fetch_is_one_batched_query_for_the_page(
    roster,
    executed_statements,
) -> None:
    for _ in range(4):
        await roster.seed_worker(clock_in_code=uuid4().hex[:8])
    del executed_statements[:]

    await roster.items(app_scope="floor", compact=True)

    profile_queries = [q for q in executed_statements if "user_work_profiles" in q]
    assert len(profile_queries) == 1, profile_queries


async def test_non_floor_page_never_queries_work_profiles(roster, executed_statements) -> None:
    for _ in range(4):
        await roster.seed_worker(clock_in_code=uuid4().hex[:8])
    del executed_statements[:]

    await roster.items(app_scope="manager", compact=True)

    assert [q for q in executed_statements if "user_work_profiles" in q] == []


async def test_pagination_envelope_is_unchanged_under_floor_scope(roster) -> None:
    await roster.seed_worker(clock_in_code=uuid4().hex[:8])

    result = await list_users(roster.ctx(app_scope="floor", compact=True))

    assert set(result) == {"users", "users_pagination"}
    assert set(result["users_pagination"]) == {"has_more", "limit", "offset", "total"}


async def test_floor_roster_reaches_more_than_200_workers_in_one_page(roster) -> None:
    for _ in range(201):
        await roster.seed_worker(clock_in_code=None)

    items = await roster.items(app_scope="floor", compact=True, limit=1000)

    assert set(items) == set(roster.user_ids)


async def test_floor_roster_accepts_the_1000_row_ceiling(roster) -> None:
    await roster.seed_worker(clock_in_code=None)

    result = await list_users(roster.ctx(app_scope="floor", compact=True, limit=1000))

    assert result["users_pagination"]["limit"] == 1000


async def test_users_route_allows_floor_1000_but_rejects_non_floor_201(roster, db_session) -> None:
    for _ in range(200):
        await roster.seed_worker(clock_in_code=None)

    async def _db_override():
        yield db_session

    def _token(app_scope: str) -> str:
        return jwt.encode(
            {
                "workspace_id": roster.workspace_id,
                "user_id": roster.user_ids[0],
                "role_name": RoleNameEnum.MANAGER.value,
                "app_scope": app_scope,
                "nonce": uuid4().hex,
            },
            settings.jwt_secret_key,
            algorithm="HS256",
        )

    app = create_app()
    app.dependency_overrides[get_db] = _db_override
    transport = ASGITransport(app=app)
    common_params = {
        "q": roster.label,
        "string_filters": "username",
        "role": RoleNameEnum.WORKER.value,
        "compact": "true",
    }
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            floor_response = await client.get(
                "/api/v1/users",
                params={**common_params, "limit": 1000},
                headers={"Authorization": f"Bearer {_token('floor')}"},
            )
            manager_response = await client.get(
                "/api/v1/users",
                params={**common_params, "limit": 201},
                headers={"Authorization": f"Bearer {_token('manager')}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert floor_response.status_code == 200
    floor_users = floor_response.json()["data"]["users"]
    assert len(floor_users) == 200
    assert "working_sections" in floor_users[0]
    assert manager_response.status_code == 422
    assert manager_response.json()["detail"] == "limit must be less than or equal to 200"


# ── `?role=` filter repair ───────────────────────────────────────────────────
# `Role.name` and `WorkspaceRole.specialization` are disjoint Postgres enums, and the
# filter used to compare BOTH against every supplied name — so any `?role=<value>` hit
# `InvalidTextRepresentationError` and surfaced as a 500. That made the kiosk roster
# call the handoff documents (`?role=worker&compact=true`) unusable, so acceptance 3
# and 6 could not be met without repairing it. See the plan's Review log (P1).


@pytest.mark.parametrize("app_scope", ["floor", "manager"])
async def test_role_name_filter_returns_workers_instead_of_erroring(
    roster,
    app_scope: str,
) -> None:
    user_id = await roster.seed_worker(clock_in_code=uuid4().hex[:8])

    items = await roster.items(app_scope=app_scope, compact=True, role="worker")

    assert user_id in items


async def test_specialization_filter_still_matches_on_the_other_enum_leg(roster) -> None:
    specialized = await roster.seed_worker(
        clock_in_code=uuid4().hex[:8],
        specialization=WorkspaceSpecializationEnum.WOOD_WORKER,
    )
    plain = await roster.seed_worker(clock_in_code=uuid4().hex[:8])

    items = await roster.items(
        app_scope="floor",
        compact=True,
        role=WorkspaceSpecializationEnum.WOOD_WORKER.value,
    )

    assert specialized in items
    assert plain not in items


async def test_both_enum_legs_can_be_requested_together(roster) -> None:
    specialized = await roster.seed_worker(
        clock_in_code=uuid4().hex[:8],
        specialization=WorkspaceSpecializationEnum.WOOD_WORKER,
    )
    plain = await roster.seed_worker(clock_in_code=uuid4().hex[:8])

    items = await roster.items(
        app_scope="floor",
        compact=True,
        role=f"worker,{WorkspaceSpecializationEnum.WOOD_WORKER.value}",
    )

    assert {specialized, plain} <= set(items)


async def test_unknown_role_name_matches_nothing_rather_than_everything(roster) -> None:
    await roster.seed_worker(clock_in_code=uuid4().hex[:8])

    items = await roster.items(app_scope="floor", compact=True, role="not-a-role")

    assert items == {}
