import pytest

from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.tasks.list_task_steps import list_task_steps
from beyo_manager.services.queries.tasks.tasks import get_task
from tests.integration.services.queries.working_sections.test_list_working_section_steps_payload_characterization import (
    _seed_step,
)


def _ctx(db_session, *, workspace_id, user_id, task_id, role_name):
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": role_name},
        incoming_data={"client_id": task_id, "task_id": task_id},
        query_params={},
        session=db_session,
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "role_name, expected_money",
    [("admin", True), ("manager", True), ("worker", False), ("seller", False)],
)
async def test_get_task_redacts_step_money_by_identity(db_session, role_name, expected_money):
    workspace, user, _, _ = await _seed_step(db_session)
    result = await get_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            task_id=f"tsk_{workspace.client_id.removeprefix('ws_')}",
            role_name=role_name,
        )
    )
    step_payload = result["task_steps"][0]
    if expected_money:
        assert step_payload["total_cost_minor"] == 4321
    else:
        assert "total_cost_minor" not in step_payload


@pytest.mark.integration
@pytest.mark.parametrize(
    "role_name, expected_money",
    [("admin", True), ("manager", True), ("worker", False), ("seller", False)],
)
async def test_list_task_steps_redacts_step_money_by_identity(db_session, role_name, expected_money):
    workspace, user, _, _ = await _seed_step(db_session)
    task_id = f"tsk_{workspace.client_id.removeprefix('ws_')}"
    result = await list_task_steps(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            task_id=task_id,
            role_name=role_name,
        )
    )
    step_payload = result["steps_pagination"]["items"][0]
    if expected_money:
        assert step_payload["total_cost_minor"] == 4321
    else:
        assert "total_cost_minor" not in step_payload
