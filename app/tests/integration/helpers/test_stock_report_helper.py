import pytest
from sqlalchemy import select

from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from tests.helpers.stock_report import (
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_purge_stock_report_workspace_removes_seed_graph_and_users(db_session):
    seeded = await seed_stock_report_workspace(db_session, suffix="purge-kit")
    workspace_id = seeded.workspace.client_id
    user_ids = (seeded.manager.client_id, seeded.worker.client_id)
    await purge_stock_report_workspace(db_session, workspace_id)
    assert (
        await db_session.scalar(
            select(Workspace.client_id).where(Workspace.client_id == workspace_id)
        )
        is None
    )
    assert (
        await db_session.scalars(
            select(User.client_id).where(User.client_id.in_(user_ids))
        )
    ).all() == []
