from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.bootstrap.phases.seed_pause_reasons import seed_pause_reasons
from beyo_manager.services.commands.pause_reasons.create_pause_reason import create_pause_reason
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.pause_reasons.list_pause_reasons import list_pause_reasons


async def _seed_workspace(db_session, name_prefix: str):
    suffix = uuid4().hex[:8]
    workspace = (
        await db_session.scalar(select(Workspace).order_by(Workspace.client_id))
        if name_prefix == "Query workspace"
        else Workspace(client_id=f"ws_{suffix}", name=f"{name_prefix} {suffix}")
    )
    user = User(
        client_id=f"usr_{suffix}",
        username=f"query_user_{suffix}",
        email=f"query_{suffix}@example.com",
        password="secret",
    )
    db_session.add(user)
    if workspace.client_id == f"ws_{suffix}":
        db_session.add(workspace)
    await db_session.flush()
    return workspace, user


@pytest.mark.integration
async def test_list_pause_reasons_returns_offset_pagination_and_workspace_scope(db_session):
    workspace, user = await _seed_workspace(db_session, "Query workspace")
    other_workspace, other_user = await _seed_workspace(db_session, "Other workspace")
    await seed_pause_reasons(db_session, workspace.client_id)

    ctx = ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": user.client_id},
        # Offset 2, not 1: the seed now holds four PERSONAL rows (lunch, coffee, meeting, other),
        # and this case is about the tail page — the one that exhausts the set and reports
        # has_more False.
        query_params={"limit": 2, "offset": 2, "pause_type": PauseTypeEnum.PERSONAL.value},
        incoming_data={},
        session=db_session,
    )
    result = await list_pause_reasons(ctx)

    assert len(result["pause_reasons"]) == 2
    assert result["pause_reasons_pagination"] == {"has_more": False, "limit": 2, "offset": 2}
    assert all(row["pause_type"] == "personal" for row in result["pause_reasons"])
    other_ctx = ServiceContext(
        identity={"workspace_id": other_workspace.client_id, "user_id": other_user.client_id},
        query_params={"limit": 50, "offset": 0},
        incoming_data={},
        session=db_session,
    )
    assert (await list_pause_reasons(other_ctx))["pause_reasons"] == []
