"""Clock-code management through the established work-profile update path.

Phase 6 acceptance 2: an admin sets/clears a worker's `clock_in_code` via
`update_user_admin`; duplicates inside the workspace come back as a friendly 409,
`updated_by_id` is stamped, and length/trim validation is enforced.

`update_user_admin` owns its own transaction (`ctx.session.begin()`), so — as in
`test_worker_shift_commands.py` — the fixtures below commit their seeds and delete
the committed rows again on teardown.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import (
    CLOCK_IN_CODE_INDEX_NAME,
    UserWorkProfile,
)
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.update_user_admin import update_user_admin
from beyo_manager.services.context import ServiceContext


pytestmark = pytest.mark.asyncio


class _Fixture:
    """Committed workspace + acting admin, plus a worker factory.

    Only plain ids cross a commit boundary: the session expires ORM instances on
    commit, and touching an expired attribute afterwards is unexpected IO.
    """

    def __init__(self, db_session, workspace_id: str, admin_id: str) -> None:
        self._db_session = db_session
        self.workspace_id = workspace_id
        self.admin_id = admin_id
        self.user_ids = [admin_id]

    async def seed_worker(self, *, with_work_profile: bool = False) -> str:
        suffix = uuid4().hex
        user = User(
            username=f"code-worker-{suffix}",
            email=f"code-worker-{suffix}@example.com",
            password="test-password-hash",
        )
        self._db_session.add(user)
        await self._db_session.flush()
        user_id = user.client_id
        role = (
            await self._db_session.execute(select(Role).where(Role.name == RoleNameEnum.WORKER))
        ).scalar_one()
        workspace_role = await self._db_session.scalar(
            select(WorkspaceRole)
            .where(
                WorkspaceRole.workspace_id == self.workspace_id,
                WorkspaceRole.role_id == role.client_id,
                WorkspaceRole.specialization.is_(None),
            )
            .limit(1)
        )
        if workspace_role is None:
            workspace_role = WorkspaceRole(
                workspace_id=self.workspace_id,
                role_id=role.client_id,
                is_system=True,
            )
            self._db_session.add(workspace_role)
            await self._db_session.flush()
        self._db_session.add(
            WorkspaceMembership(
                user_id=user_id,
                workspace_id=self.workspace_id,
                workspace_role_id=workspace_role.client_id,
                is_active=True,
            )
        )
        if with_work_profile:
            self._db_session.add(
                UserWorkProfile(
                    user_id=user_id,
                    workspace_id=self.workspace_id,
                    created_by_id=self.admin_id,
                )
            )
        await self._db_session.commit()
        self.user_ids.append(user_id)
        return user_id

    def ctx(self, incoming_data: dict) -> ServiceContext:
        return ServiceContext(
            identity={
                "workspace_id": self.workspace_id,
                "user_id": self.admin_id,
                "role_name": RoleNameEnum.ADMIN.value,
            },
            incoming_data=incoming_data,
            session=self._db_session,
        )

    async def work_profile(self, user_id: str):
        """Committed column values — no ORM instance survives the commit boundary.

        Leaves the session with no open transaction so the next command under test
        can own one (`update_user_admin` calls `session.begin()`).
        """
        await self._db_session.rollback()
        row = (
            await self._db_session.execute(
                select(
                    UserWorkProfile.clock_in_code,
                    UserWorkProfile.created_by_id,
                    UserWorkProfile.updated_by_id,
                    UserWorkProfile.salary_per_hour_before_tax,
                ).where(
                    UserWorkProfile.user_id == user_id,
                    UserWorkProfile.workspace_id == self.workspace_id,
                )
            )
        ).one_or_none()
        await self._db_session.rollback()
        return row


@pytest_asyncio.fixture
async def admin_fixture(db_session):
    workspace_id = await db_session.scalar(
        select(Workspace.client_id).order_by(Workspace.client_id).limit(1)
    )
    suffix = uuid4().hex
    admin = User(
        username=f"code-admin-{suffix}",
        email=f"code-admin-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add(admin)
    await db_session.flush()
    admin_id = admin.client_id
    await db_session.commit()
    fixture = _Fixture(db_session, workspace_id, admin_id)
    try:
        yield fixture
    finally:
        await db_session.rollback()
        await db_session.execute(
            delete(UserWorkProfile).where(UserWorkProfile.user_id.in_(fixture.user_ids))
        )
        await db_session.execute(
            delete(WorkspaceMembership).where(
                WorkspaceMembership.user_id.in_(fixture.user_ids)
            )
        )
        await db_session.execute(delete(User).where(User.client_id.in_(fixture.user_ids)))
        await db_session.commit()


async def test_admin_sets_then_clears_a_workers_clock_in_code(admin_fixture) -> None:
    worker_id = await admin_fixture.seed_worker(with_work_profile=True)
    code = uuid4().hex[:8]

    await update_user_admin(
        admin_fixture.ctx({"user_client_id": worker_id, "clock_in_code": code})
    )

    profile = await admin_fixture.work_profile(worker_id)
    assert profile.clock_in_code == code
    assert profile.updated_by_id == admin_fixture.admin_id

    await update_user_admin(
        admin_fixture.ctx({"user_client_id": worker_id, "clock_in_code": None})
    )

    profile = await admin_fixture.work_profile(worker_id)
    assert profile.clock_in_code is None
    assert profile.updated_by_id == admin_fixture.admin_id


async def test_clock_in_code_is_trimmed_before_storage(admin_fixture) -> None:
    worker_id = await admin_fixture.seed_worker(with_work_profile=True)
    code = uuid4().hex[:6]

    await update_user_admin(
        admin_fixture.ctx(
            {"user_client_id": worker_id, "clock_in_code": f"  {code}\t"}
        )
    )

    profile = await admin_fixture.work_profile(worker_id)
    assert profile.clock_in_code == code


async def test_setting_clock_in_code_creates_a_missing_work_profile(admin_fixture) -> None:
    worker_id = await admin_fixture.seed_worker()
    assert await admin_fixture.work_profile(worker_id) is None
    code = uuid4().hex[:8]

    await update_user_admin(
        admin_fixture.ctx({"user_client_id": worker_id, "clock_in_code": code})
    )

    profile = await admin_fixture.work_profile(worker_id)
    assert profile is not None
    assert profile.clock_in_code == code
    assert profile.created_by_id == admin_fixture.admin_id
    # users README: updated_by_id is nullable only at creation time.
    assert profile.updated_by_id is None


async def test_duplicate_clock_in_code_in_workspace_is_a_friendly_conflict(
    admin_fixture,
) -> None:
    holder_id = await admin_fixture.seed_worker(with_work_profile=True)
    other_id = await admin_fixture.seed_worker(with_work_profile=True)
    code = uuid4().hex[:8]
    await update_user_admin(
        admin_fixture.ctx({"user_client_id": holder_id, "clock_in_code": code})
    )

    with pytest.raises(ConflictError) as exc_info:
        await update_user_admin(
            admin_fixture.ctx({"user_client_id": other_id, "clock_in_code": code})
        )

    assert exc_info.value.http_status == 409
    assert exc_info.value.message == (
        "Clock-in code is already in use in this workspace and may belong to an inactive worker."
    )
    # The losing worker keeps no code at all — the conflict rolled back.
    assert (await admin_fixture.work_profile(other_id)).clock_in_code is None


async def test_reassigning_a_workers_own_code_is_not_a_conflict(admin_fixture) -> None:
    worker_id = await admin_fixture.seed_worker(with_work_profile=True)
    code = uuid4().hex[:8]
    payload = {"user_client_id": worker_id, "clock_in_code": code}
    await update_user_admin(admin_fixture.ctx(payload))

    await update_user_admin(admin_fixture.ctx(dict(payload)))

    profile = await admin_fixture.work_profile(worker_id)
    assert profile.clock_in_code == code


async def test_clock_in_code_index_constant_matches_the_model_index() -> None:
    assert CLOCK_IN_CODE_INDEX_NAME in {
        index.name for index in UserWorkProfile.__table__.indexes
    }


async def test_clock_in_code_assignment_translates_the_post_precheck_race(
    admin_fixture,
    monkeypatch,
) -> None:
    worker_id = await admin_fixture.seed_worker(with_work_profile=True)
    code = uuid4().hex[:8]

    async def _lose_race_at_flush(*_args, **_kwargs) -> None:
        raise IntegrityError(
            "UPDATE user_work_profiles",
            {},
            Exception(f'duplicate key violates index "{CLOCK_IN_CODE_INDEX_NAME}"'),
        )

    monkeypatch.setattr(admin_fixture._db_session, "flush", _lose_race_at_flush)

    with pytest.raises(ConflictError) as exc_info:
        await update_user_admin(
            admin_fixture.ctx({"user_client_id": worker_id, "clock_in_code": code})
        )

    assert exc_info.value.http_status == 409
    assert exc_info.value.message == (
        "Clock-in code is already in use in this workspace and may belong to an inactive worker."
    )


@pytest.mark.parametrize("code", ["abc", "   x   ", "", "x" * 17])
async def test_clock_in_code_length_matrix_is_rejected(admin_fixture, code: str) -> None:
    worker_id = await admin_fixture.seed_worker(with_work_profile=True)

    with pytest.raises(ValidationError) as exc_info:
        await update_user_admin(
            admin_fixture.ctx({"user_client_id": worker_id, "clock_in_code": code})
        )

    assert exc_info.value.http_status == 422
    assert "clock_in_code" in exc_info.value.message
    assert (await admin_fixture.work_profile(worker_id)).clock_in_code is None


async def test_salary_only_update_leaves_clock_in_code_untouched(admin_fixture) -> None:
    worker_id = await admin_fixture.seed_worker(with_work_profile=True)
    code = uuid4().hex[:8]
    await update_user_admin(
        admin_fixture.ctx({"user_client_id": worker_id, "clock_in_code": code})
    )

    await update_user_admin(
        admin_fixture.ctx(
            {"user_client_id": worker_id, "salary_per_hour_before_tax": "42.5"}
        )
    )

    profile = await admin_fixture.work_profile(worker_id)
    assert profile.clock_in_code == code
    assert profile.salary_per_hour_before_tax == Decimal("42.5000")
