"""The commit boundary: a re-commit must not strand the frozen result row.

Reproduces the two-baseline drift observed on a READY task: the live budget block
reads the CURRENT committed evaluation while ``item_cost_results`` stayed pinned
to the superseded one, because committing an evaluation emitted no result
boundary and a READY task need never reach another transition.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.execution.execution_payload import ExecutionPayload
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import (
    commit_item_cost_evaluation,
)
from beyo_manager.services.commands.item_economics.create_item_cost_projection import (
    create_item_cost_projection,
)
from beyo_manager.services.commands.item_economics.promote_item_cost_projection import (
    promote_item_cost_projection,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_task_production_time import (
    get_task_production_time,
)
from beyo_manager.services.tasks.analytics.process_item_cost_result import (
    handle_process_item_cost_result,
)

from tests.integration.services.commands.item_economics.test_phase7_evaluations import (
    _cleanup_committed_fixture,
    _ctx,
    _fixture,
)


WORKED_SECONDS = 1800


def _read_ctx(session, workspace_id: str, task_id: str) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr", "role_name": "manager"},
        incoming_data={"task_client_id": task_id},
        query_params={},
        session=session,
    )


async def _emitted(session, task_client_id: str) -> list[dict]:
    """The PROCESS_ITEM_COST_RESULT payloads queued for one task, oldest first."""
    rows = await session.execute(
        select(ExecutionPayload.payload)
        .join(ExecutionTask, ExecutionTask.client_id == ExecutionPayload.execution_task_id)
        .where(
            ExecutionTask.task_type == TaskType.PROCESS_ITEM_COST_RESULT,
            ExecutionPayload.payload["task_id"].as_string() == task_client_id,
        )
        .order_by(ExecutionPayload.created_at.asc(), ExecutionPayload.client_id.asc())
    )
    return [row[0] for row in rows]


async def _current_allowance(session, task_client_id: str) -> Decimal:
    return await session.scalar(
        select(ItemCostEvaluation.allowed_worker_minutes).where(
            ItemCostEvaluation.task_id == task_client_id,
            ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
            ItemCostEvaluation.superseded_at.is_(None),
            ItemCostEvaluation.is_deleted.is_(False),
        )
    )


async def _worked_fixture(db_session, *, task_state=TaskStateEnum.READY):
    """phase-7 fixture + one committed evaluation + one section carrying worked time."""
    workspace, user, item, task, _basis = await _fixture(db_session)
    await commit_item_cost_evaluation(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"task_client_id": task.client_id, "label": "first"},
        )
    )
    section = WorkingSection(
        client_id=f"wsec_boundary_{task.client_id}",
        workspace_id=workspace.client_id,
        name=f"boundary {task.client_id}",
    )
    step = TaskStep(
        client_id=f"tsp_boundary_{task.client_id}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.COMPLETED,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=WORKED_SECONDS,
        created_by_id=user.client_id,
    )
    task.state = task_state
    db_session.add_all([section, step])
    await db_session.commit()
    return workspace, user, item, task, section


async def _cleanup(db_session, workspace_id: str, user_id: str, task_client_id: str) -> None:
    await db_session.rollback()
    ids = (
        await db_session.scalars(
            select(ExecutionPayload.execution_task_id).where(
                ExecutionPayload.payload["task_id"].as_string() == task_client_id
            )
        )
    ).all()
    if ids:
        await db_session.execute(
            delete(ExecutionPayload).where(ExecutionPayload.execution_task_id.in_(ids))
        )
        await db_session.execute(delete(ExecutionTask).where(ExecutionTask.client_id.in_(ids)))
    await db_session.execute(delete(ItemCostResult).where(ItemCostResult.workspace_id == workspace_id))
    await db_session.execute(delete(TaskStep).where(TaskStep.workspace_id == workspace_id))
    await db_session.execute(delete(WorkingSection).where(WorkingSection.workspace_id == workspace_id))
    await db_session.commit()
    await _cleanup_committed_fixture(db_session, workspace_id, user_id)


@pytest.mark.integration
@pytest.mark.parametrize(
    "task_state",
    [TaskStateEnum.READY, TaskStateEnum.WORKING],
    ids=["recommit-READY", "recommit-WORKING"],
)
async def test_recommit_emits_exactly_one_result_boundary(db_session, task_state):
    workspace, user, _item, task, _section = await _worked_fixture(
        db_session, task_state=task_state
    )
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        # The first commit ran while the fixture task was still PENDING.
        assert await _emitted(db_session, tsk_id) == []

        await commit_item_cost_evaluation(
            _ctx(db_session, ws_id, usr_id, {"task_client_id": tsk_id, "expected_sale_price_minor": 4000})
        )
        await db_session.commit()

        assert await _emitted(db_session, tsk_id) == [
            {"workspace_id": ws_id, "task_id": tsk_id}
        ]
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


@pytest.mark.integration
@pytest.mark.parametrize(
    "task_state",
    [TaskStateEnum.PENDING, TaskStateEnum.ASSIGNED, TaskStateEnum.STALLED],
    ids=["commit-PENDING", "commit-ASSIGNED", "commit-STALLED"],
)
async def test_commit_in_a_state_the_handler_refuses_emits_nothing(db_session, task_state):
    """The three commit-admitted states the result handler writes nothing in."""
    workspace, user, _item, task, _section = await _worked_fixture(
        db_session, task_state=task_state
    )
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        await commit_item_cost_evaluation(
            _ctx(db_session, ws_id, usr_id, {"task_client_id": tsk_id, "expected_sale_price_minor": 4000})
        )
        await db_session.commit()

        assert await _emitted(db_session, tsk_id) == []
        # and the handler would indeed have written nothing
        await handle_process_item_cost_result(
            {"workspace_id": ws_id, "task_id": tsk_id}, "execution-task"
        )
        assert await db_session.scalar(
            select(func.count()).select_from(ItemCostResult).where(ItemCostResult.task_id == tsk_id)
        ) == 0
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


@pytest.mark.integration
async def test_projection_creation_emits_no_result_boundary(db_session):
    """A projection supersedes nothing and no operational surface reads it."""
    workspace, user, _item, task, _section = await _worked_fixture(db_session)
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        await create_item_cost_projection(
            _ctx(
                db_session,
                ws_id,
                usr_id,
                {
                    "task_client_id": tsk_id,
                    "source": "committed",
                    "expected_sale_price_minor": 4000,
                    "label": "what-if",
                },
            )
        )
        await db_session.commit()

        assert await _emitted(db_session, tsk_id) == []
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


@pytest.mark.integration
async def test_promotion_emits_a_result_boundary(db_session):
    """Promotion runs the same commit procedure, so it moves the allowance too."""
    workspace, user, _item, task, _section = await _worked_fixture(db_session)
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        projection = await create_item_cost_projection(
            _ctx(
                db_session,
                ws_id,
                usr_id,
                {
                    "task_client_id": tsk_id,
                    "source": "committed",
                    "expected_sale_price_minor": 4000,
                    "label": "what-if",
                },
            )
        )
        await db_session.commit()
        assert await _emitted(db_session, tsk_id) == []

        await promote_item_cost_projection(
            _ctx(db_session, ws_id, usr_id, {"client_id": projection["evaluation"]["client_id"]})
        )
        await db_session.commit()

        assert await _emitted(db_session, tsk_id) == [
            {"workspace_id": ws_id, "task_id": tsk_id}
        ]
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


@pytest.mark.integration
async def test_recommit_boundary_reconciles_the_frozen_result_with_the_new_allowance(db_session):
    """End to end: the drift that produced -206.82 against a 403.20 allowance."""
    workspace, user, _item, task, _section = await _worked_fixture(db_session)
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        # Boundary 1 — entry into READY. The row freezes against the first allowance.
        await handle_process_item_cost_result(
            {"workspace_id": ws_id, "task_id": tsk_id}, "execution-task"
        )
        first_allowance = await _current_allowance(db_session, tsk_id)
        frozen = await db_session.scalar(
            select(ItemCostResult).where(ItemCostResult.task_id == tsk_id)
        )
        assert frozen.actual_worker_minutes + frozen.variance_worker_minutes == first_allowance

        # The manager re-prices the item. The live allowance moves.
        await commit_item_cost_evaluation(
            _ctx(db_session, ws_id, usr_id, {"task_client_id": tsk_id, "expected_sale_price_minor": 4000})
        )
        await db_session.commit()
        second_allowance = await _current_allowance(db_session, tsk_id)
        assert second_allowance != first_allowance

        # The boundary the commit emitted is what reconciles the stored row.
        assert await _emitted(db_session, tsk_id) == [{"workspace_id": ws_id, "task_id": tsk_id}]
        await handle_process_item_cost_result(
            {"workspace_id": ws_id, "task_id": tsk_id}, "execution-task"
        )
        await db_session.rollback()
        reconciled = await db_session.scalar(
            select(ItemCostResult).where(ItemCostResult.task_id == tsk_id)
        )
        assert (
            reconciled.actual_worker_minutes + reconciled.variance_worker_minutes
            == second_allowance
        )

        body = await get_task_production_time(_read_ctx(db_session, ws_id, tsk_id))
        assert body["final"]["allowed_worker_minutes_snapshot"] == str(second_allowance)
        assert body["budget"]["allowed_worker_minutes"] == str(second_allowance)
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


@pytest.mark.integration
async def test_final_serves_the_frozen_allowance_it_was_computed_against(db_session):
    """Before the boundary is handled, `final` must label its own baseline.

    The stored row is deliberately left pinned to the superseded evaluation here:
    the served snapshot has to follow the frozen variance, not the live block.
    """
    workspace, user, _item, task, _section = await _worked_fixture(db_session)
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        await handle_process_item_cost_result(
            {"workspace_id": ws_id, "task_id": tsk_id}, "execution-task"
        )
        first_allowance = await _current_allowance(db_session, tsk_id)

        await commit_item_cost_evaluation(
            _ctx(db_session, ws_id, usr_id, {"task_client_id": tsk_id, "expected_sale_price_minor": 4000})
        )
        await db_session.commit()
        second_allowance = await _current_allowance(db_session, tsk_id)
        assert second_allowance != first_allowance

        body = await get_task_production_time(_read_ctx(db_session, ws_id, tsk_id))
        final = body["final"]
        assert final["allowed_worker_minutes_snapshot"] == str(first_allowance)
        assert body["budget"]["allowed_worker_minutes"] == str(second_allowance)
        # the served baseline is the one the served variance and percentage used
        assert (
            Decimal(final["allowed_worker_minutes_snapshot"])
            - Decimal(final["actual_worker_minutes"])
            == Decimal(final["variance_worker_minutes"])
        )
        assert Decimal(final["percent_consumed"]) == (
            Decimal(final["actual_worker_minutes"])
            / Decimal(final["allowed_worker_minutes_snapshot"])
            * 100
        ).quantize(Decimal("0.01"))
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


@pytest.mark.integration
async def test_frozen_snapshot_survives_a_negative_variance(db_session):
    """An over-budget row's baseline is still the allowance, not the shortfall."""
    workspace, user, item, task, _section = await _worked_fixture(db_session)
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        evaluation_id = await db_session.scalar(
            select(ItemCostEvaluation.client_id).where(
                ItemCostEvaluation.task_id == tsk_id,
                ItemCostEvaluation.superseded_at.is_(None),
            )
        )
        db_session.add(
            ItemCostResult(
                client_id=f"icr_neg_{tsk_id}",
                workspace_id=ws_id,
                task_id=tsk_id,
                item_id=item.client_id,
                evaluation_id=evaluation_id,
                actual_worker_seconds=26987,
                actual_worker_minutes=Decimal("449.78"),
                consumed_cost_minor=585655,
                variance_worker_minutes=Decimal("-206.82"),
                variance_cost_minor=-269305,
                task_closed_at=None,
                task_state_snapshot=TaskStateEnum.READY,
                calculation_version=2,
                computed_at=datetime.now(timezone.utc),
            )
        )
        await db_session.flush()

        final = (await get_task_production_time(_read_ctx(db_session, ws_id, tsk_id)))["final"]
        assert final["allowed_worker_minutes_snapshot"] == "242.96"
        assert final["percent_consumed"] == "185.13"
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)
