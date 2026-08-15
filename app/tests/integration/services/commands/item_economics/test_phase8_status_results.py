from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from beyo_manager.domain.item_economics.calculator import calculate_consumed_cost_minor
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import commit_item_cost_evaluation
from beyo_manager.services.commands.item_economics.create_item_cost_projection import create_item_cost_projection
from beyo_manager.services.commands.item_economics.create_production_cost_basis_version import (
    create_production_cost_basis_version,
)
from beyo_manager.services.commands.item_economics._common import today_utc
from beyo_manager.services.commands.item_economics.delete_item_valuation import delete_item_valuation
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_item_lifetime_economics import get_item_lifetime_economics
from beyo_manager.services.queries.item_economics.get_task_budget_status import get_task_budget_status
from beyo_manager.services.tasks.analytics.process_item_cost_result import handle_process_item_cost_result
from beyo_manager.services.tasks.analytics.process_step_transition import handle_process_step_transition

from tests.integration.services.commands.item_economics.test_phase7_evaluations import (
    _cleanup_committed_fixture,
    _ctx,
    _fixture,
)
from tests.integration.services.commands.item_economics.test_phase8_reviewer_r1_probe import (
    _cleanup as _cleanup_probe,
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
@pytest.mark.parametrize(
    ("allowed_worker_minutes", "expected_status"),
    [
        (Decimal("0.00"), "infeasible"),
        (Decimal("10.00"), "ok"),
    ],
    ids=["P-V-infeasible", "P-V-ok"],
)
async def test_c7_committed_evaluation_branch_drives_evaluated_status(
    db_session, allowed_worker_minutes, expected_status
):
    workspace, user, _item, task, committed = await _prepared(db_session)
    try:
        evaluation = await db_session.get(ItemCostEvaluation, committed["client_id"])
        evaluation.allowed_worker_minutes = allowed_worker_minutes
        await db_session.commit()

        status = await get_task_budget_status(
            _read_ctx(db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id})
        )

        assert status.status.value == expected_status
        if expected_status == "infeasible":
            assert status.percent_consumed is None
        else:
            assert status.percent_consumed is not None
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)


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
        step.total_pause_seconds = 30
        step.total_ended_shift_seconds = 40
        step.inaccurate_working_seconds = 50
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


async def _run_analytics_transition(db_session, workspace, user, task, step, record):
    await handle_process_step_transition(
        {
            "step_id": step.client_id,
            "task_id": task.client_id,
            "workspace_id": workspace.client_id,
            "closing_record_id": record.client_id,
            "closing_state": TaskStepStateEnum.WORKING.value,
            "new_state": TaskStepStateEnum.COMPLETED.value,
            "performed_by_user_id": user.client_id,
            "credited_user_id": user.client_id,
            "assigned_worker_id": None,
            "working_section_id": step.working_section_id,
            "working_section_name_snapshot": "phase8 analytics",
            "entered_at": record.entered_at.isoformat(),
            "exited_at": record.exited_at.isoformat(),
            "step_task_id": task.client_id,
        },
        "phase8-g3",
    )


@pytest.mark.integration
async def test_c2_rollup_separates_working_paused_ended_shift_and_marked_wrong(db_session):
    """Each real ORM record drives exactly one production rollup bucket."""
    workspace, user, _item, task, _basis = await _fixture(db_session)
    from beyo_manager.models.tables.working_sections.working_section import WorkingSection

    section = WorkingSection(
        client_id=f"wsec_g3_{uuid4().hex}",
        workspace_id=workspace.client_id,
        name="phase8 analytics",
    )
    step = TaskStep(
        client_id=f"tsp_g3_{uuid4().hex}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.COMPLETED,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        allows_batch_working=False,
        created_by_id=user.client_id,
    )
    base = datetime(2026, 8, 14, 8, 0, tzinfo=timezone.utc)
    records = [
        StepStateRecord(
            client_id=f"ssr_g3_{uuid4().hex}", workspace_id=workspace.client_id,
            step_id=step.client_id, state=TaskStepStateEnum.WORKING,
            entered_at=base, exited_at=base.replace(hour=9),
            credited_user_id=user.client_id, created_by_id=user.client_id,
        ),
        StepStateRecord(
            client_id=f"ssr_g3_{uuid4().hex}", workspace_id=workspace.client_id,
            step_id=step.client_id, state=TaskStepStateEnum.PAUSED,
            entered_at=base.replace(hour=9), exited_at=base.replace(hour=10),
            credited_user_id=user.client_id, created_by_id=user.client_id,
        ),
        StepStateRecord(
            client_id=f"ssr_g3_{uuid4().hex}", workspace_id=workspace.client_id,
            step_id=step.client_id, state=TaskStepStateEnum.PAUSED,
            transition_reason=TransitionReasonEnum.SHIFT_ENDED.value,
            entered_at=base.replace(hour=10), exited_at=base.replace(hour=11),
            credited_user_id=user.client_id, created_by_id=user.client_id,
        ),
        StepStateRecord(
            client_id=f"ssr_g3_{uuid4().hex}", workspace_id=workspace.client_id,
            step_id=step.client_id, state=TaskStepStateEnum.WORKING,
            recorded_time_marked_wrong=True,
            entered_at=base.replace(hour=11), exited_at=base.replace(hour=12),
            credited_user_id=user.client_id, created_by_id=user.client_id,
        ),
    ]
    db_session.add(section)
    await db_session.flush()
    db_session.add(step)
    await db_session.flush()
    db_session.add_all(records)
    task.state = TaskStateEnum.WORKING
    await db_session.commit()
    try:
        await _run_analytics_transition(db_session, workspace, user, task, step, records[0])
        await db_session.refresh(step)
        assert step.total_working_seconds == 3600
        assert step.total_pause_seconds == 3600
        assert step.total_ended_shift_seconds == 3600
        assert step.inaccurate_working_seconds == 3600
        assert step.total_working_count == 1
        assert step.total_pause_count == 1
        assert step.total_ended_shift_count == 1
    finally:
        await _cleanup_probe(db_session, workspace.client_id, user.client_id, task.client_id)


@pytest.mark.integration
async def test_c3_batch_rollup_dilutes_two_overlapping_steps_to_wall_clock(db_session):
    workspace, user, _item, task, _basis = await _fixture(db_session)
    from beyo_manager.models.tables.working_sections.working_section import WorkingSection

    second_task = Task(
        client_id=f"tsk_g3_{uuid4().hex}",
        workspace_id=workspace.client_id,
        task_scalar_id=2,
        task_type=task.task_type,
        state=TaskStateEnum.PENDING,
        created_by_id=user.client_id,
    )
    db_session.add(second_task)
    await db_session.flush()
    db_session.add(
        TaskItem(
            workspace_id=workspace.client_id,
            task_id=second_task.client_id,
            item_id=_item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=user.client_id,
        )
    )
    await db_session.flush()
    await commit_item_cost_evaluation(
        _ctx(db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id})
    )
    await commit_item_cost_evaluation(
        _ctx(db_session, workspace.client_id, user.client_id, {"task_client_id": second_task.client_id})
    )

    section = WorkingSection(
        client_id=f"wsec_g3_{uuid4().hex}", workspace_id=workspace.client_id, name="batch"
    )
    steps = [
        TaskStep(
            client_id=f"tsp_g3_{uuid4().hex}", workspace_id=workspace.client_id,
            task_id=(task.client_id if index == 0 else second_task.client_id),
            working_section_id=section.client_id,
            state=TaskStepStateEnum.COMPLETED, readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0, completed_dependencies=0, allows_batch_working=True,
            created_by_id=user.client_id,
        )
        for index in range(2)
    ]
    base = datetime(2026, 8, 14, 8, 0, tzinfo=timezone.utc)
    records = [
        StepStateRecord(
            client_id=f"ssr_g3_{uuid4().hex}", workspace_id=workspace.client_id,
            step_id=step.client_id, state=TaskStepStateEnum.WORKING,
            entered_at=base, exited_at=base.replace(hour=9),
            credited_user_id=user.client_id, created_by_id=user.client_id,
        )
        for step in steps
    ]
    db_session.add(section)
    await db_session.flush()
    db_session.add_all(steps)
    await db_session.flush()
    db_session.add_all(records)
    task.state = TaskStateEnum.WORKING
    second_task.state = TaskStateEnum.WORKING
    await db_session.commit()
    try:
        await _run_analytics_transition(db_session, workspace, user, task, steps[0], records[0])
        await _run_analytics_transition(db_session, workspace, user, second_task, steps[1], records[1])
        for step in steps:
            await db_session.refresh(step)
        assert [step.total_working_seconds for step in steps] == [1800, 1800]
        assert sum(step.total_working_seconds for step in steps) == 3600
        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": second_task.client_id}, "execution-task"
        )
        results = (
            await db_session.scalars(
                select(ItemCostResult).where(ItemCostResult.task_id.in_([task.client_id, second_task.client_id]))
            )
        ).all()
        assert {result.actual_worker_seconds for result in results} == {1800}
        assert sum(result.actual_worker_seconds for result in results) == 3600
    finally:
        await _cleanup_probe(db_session, workspace.client_id, user.client_id, task.client_id)


@pytest.mark.integration
async def test_c4_no_steps_coalesces_consumption_to_zero(db_session):
    workspace, user, _item, task, _basis = await _fixture(db_session)
    await commit_item_cost_evaluation(
        _ctx(db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id})
    )
    task.state = TaskStateEnum.WORKING
    await db_session.commit()
    try:
        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        result = await db_session.scalar(select(ItemCostResult).where(ItemCostResult.task_id == task.client_id))
        assert result is not None
        assert result.actual_worker_seconds == 0
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
async def test_c6b_reentry_recomputes_one_result_row_from_new_totals(db_session):
    workspace, user, _item, task, _committed = await _prepared(db_session)
    try:
        task.state = TaskStateEnum.READY
        await db_session.commit()
        payload = {"workspace_id": workspace.client_id, "task_id": task.client_id}
        await handle_process_item_cost_result(payload, "execution-task")
        result = await db_session.scalar(select(ItemCostResult).where(ItemCostResult.task_id == task.client_id))
        assert result is not None
        task.state = TaskStateEnum.WORKING
        step = await db_session.scalar(select(TaskStep).where(TaskStep.task_id == task.client_id))
        step.total_working_seconds = 240
        await db_session.commit()
        await handle_process_item_cost_result(payload, "execution-task")
        await db_session.refresh(result)
        assert result.task_state_snapshot is TaskStateEnum.WORKING
        assert result.actual_worker_seconds == 240
        assert await db_session.scalar(
            select(func.count())
            .select_from(ItemCostResult)
            .where(ItemCostResult.task_id == task.client_id)
        ) == 1
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
async def test_c5_config_supersession_after_close_preserves_snapshot_recompute(db_session):
    workspace, user, _item, task, committed = await _prepared(db_session)
    try:
        # Close BEFORE the first run, not between the runs: both lifecycle columns
        # then carry real closed values, so "after close" is genuinely reached and
        # the ten-column equality below still holds. Resolving between the runs
        # would flip task_state_snapshot and task_closed_at and redden it.
        # RESOLVED is an admitted state, so the first run still writes.
        task.state = TaskStateEnum.RESOLVED
        task.closed_at = datetime.now(timezone.utc)
        await db_session.commit()

        payload = {"workspace_id": workspace.client_id, "task_id": task.client_id}
        await handle_process_item_cost_result(payload, "execution-task")
        first = await db_session.scalar(select(ItemCostResult).where(ItemCostResult.task_id == task.client_id))
        # Ten columns: §8A.4's replay-identity set plus task_state_snapshot.
        # That extra column is deliberate and stricter, not an oversight.
        first_values = {
            field: getattr(first, field)
            for field in (
                "evaluation_id",
                "item_id",
                "actual_worker_seconds",
                "actual_worker_minutes",
                "consumed_cost_minor",
                "variance_worker_minutes",
                "variance_cost_minor",
                "task_closed_at",
                "task_state_snapshot",
                "calculation_version",
            )
        }
        basis = await db_session.scalar(
            select(ProductionCostBasisVersion).where(
                ProductionCostBasisVersion.workspace_id == workspace.client_id,
                ProductionCostBasisVersion.effective_to.is_(None),
            )
        )
        new_basis = await create_production_cost_basis_version(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {
                    "production_cost_group_id": basis.production_cost_group_id,
                    "effective_from": today_utc(),
                    "fixed_monthly_cost_minor": 200000,
                    "currency": basis.currency,
                    "monthly_paid_hours": basis.monthly_paid_hours,
                    "planning_utilization_percent": basis.planning_utilization_percent,
                },
            )
        )
        await db_session.commit()
        new_rate = Decimal(new_basis["production_cost_basis_version"]["cost_per_worker_minute_minor"])
        assert new_rate != Decimal(str(committed["cost_per_worker_minute_minor_snapshot"]))
        assert calculate_consumed_cost_minor(first.actual_worker_seconds, new_rate) != first.consumed_cost_minor

        await handle_process_item_cost_result(payload, "execution-task")
        await db_session.refresh(first)
        assert {field: getattr(first, field) for field in first_values} == first_values
    finally:
        await _cleanup_phase8(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
async def test_g8_delete_valuation_on_soft_deleted_item_returns_item_unvalued(db_session):
    workspace, user, item, _task, _basis = await _fixture(db_session)
    item.is_deleted = True
    await db_session.flush()
    try:
        result = await delete_item_valuation(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {"item_client_id": item.client_id},
            )
        )
        assert result["preview"]["status"] == "item_unvalued"
    finally:
        await _cleanup_committed_fixture(db_session, workspace.client_id, user.client_id)
