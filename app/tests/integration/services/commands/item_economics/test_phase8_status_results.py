import pytest
from sqlalchemy import delete, select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import commit_item_cost_evaluation
from beyo_manager.services.commands.item_economics.create_item_cost_projection import create_item_cost_projection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_item_lifetime_economics import get_item_lifetime_economics
from beyo_manager.services.queries.item_economics.get_task_budget_status import get_task_budget_status
from beyo_manager.services.tasks.analytics.process_item_cost_result import handle_process_item_cost_result

from tests.integration.services.commands.item_economics.test_phase7_evaluations import (
    _cleanup_committed_fixture,
    _ctx,
    _fixture,
)


def _read_ctx(session, workspace_id: str, user_id: str, data: dict) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": "manager"},
        incoming_data=data,
        session=session,
    )


async def _cleanup_phase8(db_session, workspace_id: str, user_id: str) -> None:
    await db_session.rollback()
    await db_session.execute(delete(ItemCostResult).where(ItemCostResult.workspace_id == workspace_id))
    await db_session.execute(delete(TaskStep).where(TaskStep.workspace_id == workspace_id))
    await db_session.execute(delete(WorkingSection).where(WorkingSection.workspace_id == workspace_id))
    await db_session.commit()
    await _cleanup_committed_fixture(db_session, workspace_id, user_id)


async def _prepared(db_session):
    workspace, user, item, task, _basis = await _fixture(db_session)
    committed = await commit_item_cost_evaluation(
        _ctx(db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id, "label": "phase8"})
    )
    section = WorkingSection(
        client_id=f"wsec_phase8_{task.client_id}",
        workspace_id=workspace.client_id,
        name=f"phase8 {task.client_id}",
    )
    step = TaskStep(
        client_id=f"tsp_phase8_{task.client_id}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.SKIPPED,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=120,
        created_by_id=user.client_id,
    )
    task.state = TaskStateEnum.WORKING
    db_session.add_all([section, step])
    await db_session.commit()
    return workspace, user, item, task, committed["evaluation"]


@pytest.mark.integration
async def test_c1_projection_is_invisible_to_status_and_result_handler(db_session):
    workspace, user, item, task, committed = await _prepared(db_session)
    try:
        projection = await create_item_cost_projection(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {"task_client_id": task.client_id, "source": "committed", "expected_sale_price_minor": 2000},
            )
        )
        await db_session.commit()
        status = await get_task_budget_status(
            _read_ctx(db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id})
        )
        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        result = await db_session.scalar(select(ItemCostResult).where(ItemCostResult.task_id == task.client_id))
        assert status.evaluation_id == committed["client_id"]
        assert projection["evaluation"]["client_id"] != status.evaluation_id
        assert result.evaluation_id == committed["client_id"]
        assert result.item_id == item.client_id
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
async def test_c4_consumption_excludes_deleted_steps_but_counts_skipped_steps(db_session):
    workspace, user, _item, task, _committed = await _prepared(db_session)
    try:
        step = await db_session.scalar(select(TaskStep).where(TaskStep.task_id == task.client_id))
        deleted = TaskStep(
            client_id=f"tsp_deleted_{task.client_id}",
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            working_section_id=step.working_section_id,
            state=TaskStepStateEnum.PENDING,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=999,
            is_deleted=True,
            created_by_id=user.client_id,
        )
        db_session.add(deleted)
        await db_session.commit()
        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        result = await db_session.scalar(select(ItemCostResult).where(ItemCostResult.task_id == task.client_id))
        assert result.actual_worker_seconds == 120
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
async def test_c5_replay_updates_only_computed_at_and_converges(db_session):
    workspace, user, _item, task, _committed = await _prepared(db_session)
    try:
        payload = {"workspace_id": workspace.client_id, "task_id": task.client_id}
        await handle_process_item_cost_result(payload, "execution-task")
        first = await db_session.scalar(select(ItemCostResult).where(ItemCostResult.task_id == task.client_id))
        first_snapshot = {
            key: getattr(first, key)
            for key in (
                "evaluation_id", "item_id", "actual_worker_seconds", "actual_worker_minutes",
                "consumed_cost_minor", "variance_worker_minutes", "variance_cost_minor",
                "task_closed_at", "task_state_snapshot", "calculation_version",
            )
        }
        first_computed_at = first.computed_at
        await handle_process_item_cost_result(payload, "execution-task")
        second = await db_session.scalar(select(ItemCostResult).where(ItemCostResult.task_id == task.client_id))
        await db_session.refresh(second)
        assert {key: getattr(second, key) for key in first_snapshot} == first_snapshot
        assert second.computed_at > first_computed_at
        assert second.client_id == first.client_id
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
async def test_c11_lifetime_read_uses_snapshot_episode_and_result_only_totals(db_session):
    workspace, user, item, task, committed = await _prepared(db_session)
    try:
        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        read = await get_item_lifetime_economics(
            _read_ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {"item_client_id": item.client_id},
            )
        )
        assert len(read["episodes"]) == 1
        episode = read["episodes"][0]
        assert episode["task_id"] == task.client_id
        assert episode["evaluation"]["client_id"] == committed["client_id"]
        assert episode["task_type_snapshot"] == committed["task_type_snapshot"]
        assert episode["result"] is not None
        assert read["totals"]["actual_worker_seconds"] == 120
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
async def test_c5_without_current_evaluation_writes_nothing(db_session):
    workspace, user, _item, task, _basis = await _fixture(db_session)
    try:
        await db_session.commit()
        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        assert await db_session.scalar(select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)) is None
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
@pytest.mark.parametrize(
    "state",
    [TaskStateEnum.PENDING, TaskStateEnum.ASSIGNED, TaskStateEnum.STALLED],
    ids=["PENDING", "ASSIGNED", "STALLED"],
)
async def test_c6b_non_admitted_states_write_nothing(db_session, state):
    workspace, user, _item, task, _committed = await _prepared(db_session)
    try:
        task.state = state
        await db_session.commit()
        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        assert await db_session.scalar(select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)) is None
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)
