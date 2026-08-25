"""Partial unique index behaviour for `user_work_profiles.clock_in_code`.

Phase 6 acceptance 1: the DB is the real arbiter of code uniqueness — per workspace,
only while the code is set.
"""

from uuid import uuid4

import pytest
from sqlalchemy import delete, select
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


async def _seed_two_workspaces(db_session) -> tuple[Workspace, Workspace]:
    suffix = uuid4().hex
    workspaces = (
        Workspace(client_id=f"ws-clock-code-a-{suffix}", name=f"Clock code A {suffix}"),
        Workspace(client_id=f"ws-clock-code-b-{suffix}", name=f"Clock code B {suffix}"),
    )
    db_session.add_all(workspaces)
    await db_session.flush()
    return workspaces


async def _cleanup_owned_rows(
    db_session,
    workspaces: tuple[Workspace, Workspace],
    users: list[User],
) -> None:
    workspace_ids = [workspace.client_id for workspace in workspaces]
    await db_session.execute(
        delete(UserWorkProfile).where(UserWorkProfile.workspace_id.in_(workspace_ids))
    )
    if users:
        await db_session.execute(
            delete(User).where(User.client_id.in_([user.client_id for user in users]))
        )
    await db_session.execute(
        delete(Workspace).where(Workspace.client_id.in_(workspace_ids))
    )


def _profile(workspace: Workspace, user: User, code: str | None) -> UserWorkProfile:
    return UserWorkProfile(
        user_id=user.client_id,
        workspace_id=workspace.client_id,
        clock_in_code=code,
        created_by_id=user.client_id,
    )


async def test_duplicate_clock_in_code_in_one_workspace_is_rejected(db_session) -> None:
    workspaces = await _seed_two_workspaces(db_session)
    users: list[User] = []
    try:
        code = uuid4().hex[:10]
        users.extend([await _seed_user(db_session), await _seed_user(db_session)])
        db_session.add(_profile(workspaces[0], users[0], code))
        await db_session.flush()

        with pytest.raises(IntegrityError) as exc_info:
            async with db_session.begin_nested():
                db_session.add(_profile(workspaces[0], users[1], code))
                await db_session.flush()

        assert "uix_user_work_profiles_workspace_clock_code" in str(exc_info.value)
    finally:
        await _cleanup_owned_rows(db_session, workspaces, users)


async def test_same_clock_in_code_in_two_workspaces_is_allowed(db_session) -> None:
    workspaces = await _seed_two_workspaces(db_session)
    users: list[User] = []
    try:
        code = uuid4().hex[:10]
        users.extend([await _seed_user(db_session), await _seed_user(db_session)])

        db_session.add_all(
            [
                _profile(workspaces[0], users[0], code),
                _profile(workspaces[1], users[1], code),
            ]
        )
        await db_session.flush()

        stored = (
            (
                await db_session.execute(
                    select(UserWorkProfile.workspace_id).where(
                        UserWorkProfile.clock_in_code == code
                    )
                )
            )
            .scalars()
            .all()
        )
        assert sorted(stored) == sorted(workspace.client_id for workspace in workspaces)
    finally:
        await _cleanup_owned_rows(db_session, workspaces, users)


async def test_index_is_partial_so_unassigned_codes_never_collide(db_session) -> None:
    workspaces = await _seed_two_workspaces(db_session)
    users: list[User] = []
    try:
        users.extend([await _seed_user(db_session), await _seed_user(db_session)])

        db_session.add_all(
            [
                _profile(workspaces[0], users[0], None),
                _profile(workspaces[0], users[1], None),
            ]
        )
        await db_session.flush()

        unassigned = (
            (
                await db_session.execute(
                    select(UserWorkProfile.client_id).where(
                        UserWorkProfile.workspace_id == workspaces[0].client_id,
                        UserWorkProfile.user_id.in_([user.client_id for user in users]),
                        UserWorkProfile.clock_in_code.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(unassigned) == 2
    finally:
        await _cleanup_owned_rows(db_session, workspaces, users)
