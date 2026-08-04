from uuid import uuid4

import pytest

from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.sku_templates.create_sku_template import create_sku_template
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.sku_templates.get_sku_template_by_task_type import get_sku_template_by_task_type
from beyo_manager.services.queries.sku_templates.list_sku_templates import list_sku_templates


async def _seed_identity(db_session, label: str):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"{label} {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"sku_query_{suffix}",
        email=f"sku_query_{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


def _ctx(session, workspace, user, incoming_data=None, query_params=None):
    return ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": user.client_id},
        incoming_data=incoming_data or {},
        query_params=query_params or {},
        session=session,
    )


@pytest.mark.integration
async def test_by_task_type_preview_math_and_404(db_session):
    workspace, user = await _seed_identity(db_session, "Query workspace")
    await create_sku_template(
        _ctx(
            db_session,
            workspace,
            user,
            {"task_type": TaskTypeEnum.PRE_ORDER, "prefix": "PRE", "initial_scalar": 6},
        )
    )

    result = await get_sku_template_by_task_type(
        _ctx(db_session, workspace, user, {"task_type": "pre_order"})
    )
    assert result["next_scalar"] == result["last_scalar"] + 1 == 7
    assert result["next_sku_preview"] == "PRE-7"

    other_workspace, other_user = await _seed_identity(db_session, "Other workspace")
    with pytest.raises(NotFound):
        await get_sku_template_by_task_type(
            _ctx(db_session, other_workspace, other_user, {"task_type": "pre_order"})
        )


@pytest.mark.integration
async def test_list_sku_templates_uses_offset_pagination_and_workspace_scope(db_session):
    workspace, user = await _seed_identity(db_session, "List workspace")
    other_workspace, other_user = await _seed_identity(db_session, "Other list workspace")
    await create_sku_template(
        _ctx(db_session, workspace, user, {"task_type": "pre_order", "prefix": "PRE"})
    )

    result = await list_sku_templates(_ctx(db_session, workspace, user, query_params={"limit": 1, "offset": 0}))
    assert len(result["sku_templates"]) == 1
    assert result["sku_templates_pagination"] == {"has_more": False, "limit": 1, "offset": 0}

    other_result = await list_sku_templates(_ctx(db_session, other_workspace, other_user))
    assert other_result["sku_templates"] == []
