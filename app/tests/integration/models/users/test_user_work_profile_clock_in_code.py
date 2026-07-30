"""Partial unique index behaviour for `user_work_profiles.clock_in_code`.

Phase 6 acceptance 1: the DB is the real arbiter of code uniqueness — per workspace,
only while the code is set.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace import Workspace


pytestmark = pytest.mark.asyncio


async def _seed_user(db_session) -> User:
    suffix = uuid4().hex
    user = User(
        username=f"clock-code-{suffix}",
        email=f"clock-code-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _two_workspaces(db_session) -> tuple[Workspace, Workspace]:
    workspaces = (
        await db_session.execute(select(Workspace).order_by(Workspace.client_id).limit(2))
    ).scalars().all()
    assert len(workspaces) == 2, "this test needs two workspaces in the test database"
    return workspaces[0], workspaces[1]


def _profile(workspace: Workspace, user: User, code: str | None) -> UserWorkProfile:
    return UserWorkProfile(
        user_id=user.client_id,
        workspace_id=workspace.client_id,
        clock_in_code=code,
        created_by_id=user.client_id,
    )


async def test_duplicate_clock_in_code_in_one_workspace_is_rejected(db_session) -> None:
    workspace, _ = await _two_workspaces(db_session)
    code = uuid4().hex[:10]
    first = await _seed_user(db_session)
    second = await _seed_user(db_session)
    db_session.add(_profile(workspace, first, code))
    await db_session.flush()

    db_session.add(_profile(workspace, second, code))
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.flush()

    assert "uix_user_work_profiles_workspace_clock_code" in str(exc_info.value)


async def test_same_clock_in_code_in_two_workspaces_is_allowed(db_session) -> None:
    first_workspace, second_workspace = await _two_workspaces(db_session)
    code = uuid4().hex[:10]
    first = await _seed_user(db_session)
    second = await _seed_user(db_session)

    db_session.add_all(
        [
            _profile(first_workspace, first, code),
            _profile(second_workspace, second, code),
        ]
    )
    await db_session.flush()

    stored = (
        await db_session.execute(
            select(UserWorkProfile.workspace_id).where(UserWorkProfile.clock_in_code == code)
        )
    ).scalars().all()
    assert sorted(stored) == sorted([first_workspace.client_id, second_workspace.client_id])


async def test_index_is_partial_so_unassigned_codes_never_collide(db_session) -> None:
    workspace, _ = await _two_workspaces(db_session)
    first = await _seed_user(db_session)
    second = await _seed_user(db_session)

    db_session.add_all([_profile(workspace, first, None), _profile(workspace, second, None)])
    await db_session.flush()

    unassigned = (
        await db_session.execute(
            select(UserWorkProfile.client_id).where(
                UserWorkProfile.workspace_id == workspace.client_id,
                UserWorkProfile.user_id.in_([first.client_id, second.client_id]),
                UserWorkProfile.clock_in_code.is_(None),
            )
        )
    ).scalars().all()
    assert len(unassigned) == 2
