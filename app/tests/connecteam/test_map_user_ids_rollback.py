from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.connecteam.user_csv_rows import ConnecteamCsvUser
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.connecteam.map_connecteam_user_ids import map_connecteam_user_ids


@pytest.mark.asyncio
async def test_apply_rolls_back_when_flush_fails(db_session, monkeypatch):
    suffix = uuid4().hex
    workspace = Workspace(name=f"mapping-rollback-{suffix}")
    worker = User(
        username=f"Rollback{suffix} Worker",
        email=f"rollback-{suffix}@example.com",
        password="hash",
    )
    db_session.add_all([workspace, worker])
    await db_session.flush()
    profile = UserWorkProfile(
        user_id=worker.client_id,
        workspace_id=workspace.client_id,
        created_by_id=worker.client_id,
    )
    db_session.add(profile)
    workspace_id = workspace.client_id
    profile_id = profile.client_id
    await db_session.commit()

    async def fail_flush(*args, **kwargs):
        raise IntegrityError("forced mapping failure", {}, RuntimeError("forced"))

    monkeypatch.setattr(db_session, "flush", fail_flush)
    with pytest.raises(IntegrityError):
        await map_connecteam_user_ids(
            db_session,
            csv_users=[ConnecteamCsvUser(555, f"Rollback{suffix}", "Worker", 2)],
            apply=True,
            workspace_id=workspace_id,
        )

    monkeypatch.undo()
    persisted = await db_session.scalar(
        select(UserWorkProfile.connecteam_user_id).where(UserWorkProfile.client_id == profile_id)
    )
    assert persisted is None
