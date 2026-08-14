"""REVIEWER PROBE — phase 8 review r1.

Builds the criterion rows r1b declared unbuilt and deferred to review
(C6/C6b/C10 boundary emissions with EXACT counts, C8 item_binding, C9/A11
disjointness, A10 loader equality, C7's hazard + priority rows through the
REAL producer, and a C1 fixture whose projection is the discriminating one).

Disposable: preserved under the pipeline folder's `probes/` table for the fix
cycle to adopt; not part of the shipped suite.
"""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum
from beyo_manager.models.tables.execution.execution_payload import ExecutionPayload
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.item_economics._common import _load_preview_inputs
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import (
    commit_item_cost_evaluation,
)
from beyo_manager.services.commands.item_economics.create_item_cost_projection import (
    create_item_cost_projection,
)
from beyo_manager.services.commands.task_steps.add_task_steps import add_task_steps
from beyo_manager.services.commands.tasks._task_state_transitions import maybe_evaluate_task_ready
from beyo_manager.services.commands.tasks.cancel_task import cancel_task
from beyo_manager.services.commands.tasks.fail_task import fail_task
from beyo_manager.services.commands.tasks.resolve_task import resolve_task
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_task_budget_status import get_task_budget_status
from beyo_manager.services.tasks.analytics.process_item_cost_result import (
    handle_process_item_cost_result,
)

from tests.integration.services.commands.item_economics.test_phase7_evaluations import (
    _cleanup_committed_fixture,
    _ctx,
    _fixture,
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


_NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)


def _read_ctx(session, workspace_id: str, user_id: str, data: dict) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": "manager"},
        incoming_data=data,
        session=session,
    )


async def _emit_count(session, task_client_id: str) -> int:
    """Count PROCESS_ITEM_COST_RESULT execution tasks emitted for one task."""
    return await session.scalar(
        select(func.count())
        .select_from(ExecutionTask)
        .join(ExecutionPayload, ExecutionPayload.execution_task_id == ExecutionTask.client_id)
        .where(
            ExecutionTask.task_type == TaskType.PROCESS_ITEM_COST_RESULT,
            ExecutionPayload.payload["task_id"].as_string() == task_client_id,
        )
    )


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
    from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
    from beyo_manager.models.tables.tasks.task_post_handling import TaskPostHandling
    from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
    from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord

    await db_session.execute(
        delete(TaskCustomerCoordination).where(TaskCustomerCoordination.workspace_id == workspace_id)
    )
    await db_session.execute(
        delete(TaskPostHandling).where(TaskPostHandling.workspace_id == workspace_id)
    )
    await db_session.execute(
        delete(TaskStepAcknowledgment).where(TaskStepAcknowledgment.workspace_id == workspace_id)
    )
    from sqlalchemy import update

    await db_session.execute(
        update(TaskStep)
        .where(TaskStep.workspace_id == workspace_id)
        .values(latest_state_record_id=None)
    )
    await db_session.execute(
        delete(StepStateRecord).where(StepStateRecord.workspace_id == workspace_id)
    )
    await db_session.execute(delete(ItemCostResult).where(ItemCostResult.workspace_id == workspace_id))
    await db_session.execute(delete(TaskStep).where(TaskStep.workspace_id == workspace_id))
    from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
    from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
    from beyo_manager.models.tables.analytics.user_section_daily_work_stats import (
        UserSectionDailyWorkStats,
    )
    from beyo_manager.models.tables.analytics.working_section_daily_work_stats import (
        WorkingSectionDailyWorkStats,
    )

    for model in (
        UserSectionDailyWorkStats,
        WorkingSectionDailyWorkStats,
        UserDailyWorkStats,
        UserLifetimeStats,
    ):
        await db_session.execute(delete(model).where(model.workspace_id == workspace_id))
    await db_session.execute(delete(WorkingSection).where(WorkingSection.workspace_id == workspace_id))
    await db_session.commit()
    await _cleanup_committed_fixture(db_session, workspace_id, user_id)


async def _committed_fixture(db_session, *, task_state=TaskStateEnum.WORKING, seconds=120):
    """phase-7 fixture + a committed evaluation + one time-bearing step."""
    workspace, user, item, task, _basis = await _fixture(db_session)
    committed = await commit_item_cost_evaluation(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"task_client_id": task.client_id, "label": "probe"},
        )
    )
    section = WorkingSection(
        client_id=f"wsec_probe_{task.client_id}",
        workspace_id=workspace.client_id,
        name=f"probe {task.client_id}",
    )
    step = TaskStep(
        client_id=f"tsp_probe_{task.client_id}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.COMPLETED,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=seconds,
        created_by_id=user.client_id,
    )
    task.state = task_state
    db_session.add_all([section, step])
    await db_session.commit()
    return workspace, user, item, task, committed["evaluation"], section


# --------------------------------------------------------------------------
# C10 / A4 — the three terminal commands, ZERO notification targets
# --------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    ("command", "expected_state"),
    [
        (resolve_task, TaskStateEnum.RESOLVED),
        (fail_task, TaskStateEnum.FAILED),
        (cancel_task, TaskStateEnum.CANCELLED),
    ],
    ids=["C10-terminal-resolve", "C10-terminal-fail", "C10-terminal-cancel"],
)
async def test_probe_c10_terminal_command_emits_exactly_one_result_task(
    db_session, command, expected_state
):
    """A4: the emit sits OUTSIDE `if target_user_ids:` — fixture has zero targets."""
    workspace, user, _item, task, _ev, _sec = await _committed_fixture(db_session)
    try:
        assert await _emit_count(db_session, task.client_id) == 0

        await command(
            _ctx(db_session, workspace.client_id, user.client_id, {"client_id": task.client_id})
        )
        await db_session.commit()

        # zero-notification-target fixture: no notification task was created
        notifications = await db_session.scalar(
            select(func.count())
            .select_from(ExecutionTask)
            .join(
                ExecutionPayload,
                ExecutionPayload.execution_task_id == ExecutionTask.client_id,
            )
            .where(
                ExecutionTask.task_type == TaskType.CREATE_NOTIFICATIONS,
                ExecutionPayload.payload["entity_client_id"].as_string() == task.client_id,
            )
        )
        assert notifications == 0, "fixture must have zero notification targets"

        assert await _emit_count(db_session, task.client_id) == 1

        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        row = await db_session.scalar(
            select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)
        )
        assert row.task_state_snapshot == expected_state
        assert row.task_closed_at is not None
    finally:
        await _cleanup(db_session, workspace.client_id, user.client_id, task.client_id)


# --------------------------------------------------------------------------
# C6b — the boundary lifecycle
# --------------------------------------------------------------------------


@pytest.mark.integration
async def test_probe_c6b_ready_entry_writes_ready_snapshot_with_null_closed_at(db_session):
    workspace, user, _item, task, _ev, _sec = await _committed_fixture(db_session)
    try:
        changed = await maybe_evaluate_task_ready(
            db_session,
            task,
            workspace_id=workspace.client_id,
            now=_NOW,
            updated_by_id=user.client_id,
        )
        await db_session.commit()

        assert changed is True
        assert task.state == TaskStateEnum.READY
        assert await _emit_count(db_session, task.client_id) == 1

        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        row = await db_session.scalar(
            select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)
        )
        assert row.task_state_snapshot == TaskStateEnum.READY
        assert row.task_closed_at is None
        assert row.actual_worker_seconds == 120
    finally:
        await _cleanup(db_session, workspace.client_id, user.client_id, task.client_id)


@pytest.mark.integration
async def test_probe_c6b_reopen_through_add_task_steps_flips_snapshot_to_working(db_session):
    """A3/§8B.1 row 2: the reopen emit must fire through the add_task_steps path."""
    workspace, user, _item, task, _ev, section = await _committed_fixture(
        db_session, task_state=TaskStateEnum.READY
    )
    try:
        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        before = await db_session.scalar(
            select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)
        )
        assert before.task_state_snapshot == TaskStateEnum.READY
        baseline_emits = await _emit_count(db_session, task.client_id)

        await add_task_steps(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {
                    "task_id": task.client_id,
                    "steps": [{"working_section_id": section.client_id}],
                },
            )
        )
        await db_session.commit()

        await db_session.refresh(task)
        assert task.state == TaskStateEnum.WORKING
        assert await _emit_count(db_session, task.client_id) == baseline_emits + 1

        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        after = await db_session.scalar(
            select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)
        )
        await db_session.refresh(after)
        assert after.task_state_snapshot == TaskStateEnum.WORKING
    finally:
        await _cleanup(db_session, workspace.client_id, user.client_id, task.client_id)


# --------------------------------------------------------------------------
# C8 — item_binding, three exact rows
# --------------------------------------------------------------------------


@pytest.mark.integration
async def test_probe_c8_item_binding_bound_mismatched_detached(db_session):
    workspace, user, item, task, _ev, _sec = await _committed_fixture(db_session)
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        status = await get_task_budget_status(
            _read_ctx(
                db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id}
            )
        )
        assert status.item_binding == "bound"
        assert status.item_id == item.client_id

        # mismatched: PRIMARY swapped to a different item after the commit
        other = Item(
            client_id=f"itm_other_{uuid4().hex}",
            workspace_id=workspace.client_id,
            article_number=f"ART-OTHER-{uuid4().hex}",
            item_major_category_snapshot="wood",
            created_by_id=user.client_id,
        )
        db_session.add(other)
        await db_session.flush()
        primary = await db_session.scalar(
            select(TaskItem).where(
                TaskItem.task_id == task.client_id,
                TaskItem.role == TaskItemRoleEnum.PRIMARY,
            )
        )
        primary.item_id = other.client_id
        await db_session.commit()

        status = await get_task_budget_status(
            _read_ctx(
                db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id}
            )
        )
        assert status.item_binding == "mismatched"
        assert status.item_id == item.client_id, "result/status must keep the evaluation's item"

        # detached: no PRIMARY row at all
        primary.removed_at = _NOW
        await db_session.commit()
        status = await get_task_budget_status(
            _read_ctx(
                db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id}
            )
        )
        assert status.item_binding == "detached"
    finally:
        await db_session.rollback()
        await db_session.execute(
            delete(TaskItem).where(TaskItem.task_id == tsk_id)
        )
        await db_session.execute(
            delete(Item).where(Item.workspace_id == ws_id, Item.client_id.like("itm_other_%"))
        )
        await db_session.commit()
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


# --------------------------------------------------------------------------
# C7 — the hazard row and the priority row, through the REAL producer
# --------------------------------------------------------------------------


@pytest.mark.integration
async def test_probe_c7_hazard_selection_ok_without_committed_evaluation_reads_not_evaluated(
    db_session,
):
    """A1: the resolver's OK must never leak into the payload as `ok`."""
    workspace, user, item, task, _basis = await _fixture(db_session)
    await db_session.commit()
    try:
        selection, _terms = await _load_preview_inputs(
            _read_ctx(db_session, workspace.client_id, user.client_id, {}), item
        )
        assert selection.status is EconomicsStatusEnum.OK, "non-vacuity: config resolves OK"

        status = await get_task_budget_status(
            _read_ctx(
                db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id}
            )
        )
        assert status.status is EconomicsStatusEnum.NOT_EVALUATED
        assert status.allowed_worker_minutes is None
        assert status.percent_consumed is None
        assert status.consumed_cost_minor is None
    finally:
        await _cleanup(db_session, workspace.client_id, user.client_id, task.client_id)


@pytest.mark.integration
async def test_probe_c7_priority_committed_evaluation_survives_unconfiguring_the_workspace(
    db_session,
):
    """§11A.4 rule 1: the snapshot is self-sufficient."""
    from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion

    workspace, user, _item, task, _ev, _sec = await _committed_fixture(db_session)
    try:
        from sqlalchemy import update

        await db_session.execute(
            update(CostModelVersion)
            .where(CostModelVersion.workspace_id == workspace.client_id)
            .values(is_deleted=True)
        )
        await db_session.commit()

        status = await get_task_budget_status(
            _read_ctx(
                db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id}
            )
        )
        assert status.status is EconomicsStatusEnum.OK
    finally:
        await _cleanup(db_session, workspace.client_id, user.client_id, task.client_id)


# --------------------------------------------------------------------------
# C1 — a DISCRIMINATING projection-isolation fixture
# --------------------------------------------------------------------------


@pytest.mark.integration
async def test_probe_c1_projection_isolation_with_a_discriminating_fixture(db_session):
    """The projection is created so that dropping the filter selects IT, not the
    committed row — which is what makes the named C1 mutation bite."""
    workspace, user, _item, task, _basis = await _fixture(db_session)
    await db_session.commit()
    try:
        # the PROJECTION is inserted FIRST, so an unfiltered read (the C1 mutation)
        # reaches it before the committed row — this is what makes the row bite.
        projection = await create_item_cost_projection(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {
                    "task_client_id": task.client_id,
                    "expected_sale_price_minor": 999999,
                },
            )
        )
        await db_session.commit()
        committed = (
            await commit_item_cost_evaluation(
                _ctx(
                    db_session,
                    workspace.client_id,
                    user.client_id,
                    {"task_client_id": task.client_id, "label": "probe"},
                )
            )
        )["evaluation"]
        section = WorkingSection(
            client_id=f"wsec_probe_{task.client_id}",
            workspace_id=workspace.client_id,
            name=f"probe {task.client_id}",
        )
        db_session.add(section)
        await db_session.flush()
        db_session.add(TaskStep(
            client_id=f"tsp_probe_{task.client_id}",
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            working_section_id=section.client_id,
            state=TaskStepStateEnum.COMPLETED,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=120,
            created_by_id=user.client_id,
        ))
        task.state = TaskStateEnum.WORKING
        await db_session.commit()

        # non-vacuity: the unfiltered query really does see two rows for this task
        from beyo_manager.models.tables.item_economics.item_cost_evaluation import (
            ItemCostEvaluation,
        )

        unfiltered = (
            await db_session.scalars(
                select(ItemCostEvaluation).where(ItemCostEvaluation.task_id == task.client_id)
            )
        ).all()
        assert len(unfiltered) == 2
        assert unfiltered[0].client_id == projection["evaluation"]["client_id"], (
            "fixture must place the PROJECTION first so an UNFILTERED read picks it"
        )

        status = await get_task_budget_status(
            _read_ctx(
                db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id}
            )
        )
        assert status.evaluation_id == committed["client_id"]
        assert status.production_budget_minor == committed["production_budget_minor"]

        await handle_process_item_cost_result(
            {"workspace_id": workspace.client_id, "task_id": task.client_id}, "execution-task"
        )
        row = await db_session.scalar(
            select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)
        )
        assert row.evaluation_id == committed["client_id"]
    finally:
        await _cleanup(db_session, workspace.client_id, user.client_id, task.client_id)


# --------------------------------------------------------------------------
# C6 / A17-L23 — the §8A.5 straggler re-emit guard (READY ∪ terminal)
# --------------------------------------------------------------------------


async def _straggler_transition(db_session, workspace, user, task, section):
    """Commit a closed time-bearing StepStateRecord and run the analytics handler."""
    from beyo_manager.domain.task_steps.enums import TaskStepStateEnum as _S
    from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
    from beyo_manager.services.tasks.analytics.process_step_transition import (
        handle_process_step_transition,
    )

    step = await db_session.scalar(
        select(TaskStep).where(TaskStep.task_id == task.client_id)
    )
    entered = datetime(2026, 8, 14, 8, 0, tzinfo=timezone.utc)
    exited = datetime(2026, 8, 14, 9, 0, tzinfo=timezone.utc)
    record = StepStateRecord(
        client_id=f"ssr_probe_{uuid4().hex}",
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=_S.WORKING,
        entered_at=entered,
        exited_at=exited,
        credited_user_id=user.client_id,
        created_by_id=user.client_id,
    )
    db_session.add(record)
    await db_session.commit()

    await handle_process_step_transition(
        {
            "step_id": step.client_id,
            "task_id": task.client_id,
            "workspace_id": workspace.client_id,
            "closing_record_id": record.client_id,
            "closing_state": _S.WORKING.value,
            "new_state": _S.COMPLETED.value,
            "performed_by_user_id": user.client_id,
            "credited_user_id": user.client_id,
            "assigned_worker_id": None,
            "working_section_id": section.client_id,
            "working_section_name_snapshot": section.name,
            "entered_at": entered.isoformat(),
            "exited_at": exited.isoformat(),
            "step_task_id": task.client_id,
        },
        "execution-task",
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("task_state", "expected_emits"),
    [
        (TaskStateEnum.RESOLVED, 1),
        (TaskStateEnum.READY, 1),
        (TaskStateEnum.WORKING, 0),
    ],
    ids=["C6-straggler-RESOLVED", "C6-straggler-READY-half", "C6-straggler-WORKING-none"],
)
async def test_probe_c6_straggler_guard_emits_exactly_on_ready_and_terminal(
    db_session, task_state, expected_emits
):
    workspace, user, _item, task, _ev, section = await _committed_fixture(
        db_session, task_state=task_state
    )
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        assert await _emit_count(db_session, tsk_id) == 0
        await _straggler_transition(db_session, workspace, user, task, section)
        await db_session.rollback()
        assert await _emit_count(db_session, tsk_id) == expected_emits
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


# --------------------------------------------------------------------------
# A10 — the loader equality property (+ its non-vacuity arbiter)
# --------------------------------------------------------------------------


@pytest.mark.integration
async def test_probe_a10_preview_and_live_loaders_agree_field_for_field(db_session):
    from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import (
        _load_live_inputs,
    )

    workspace, user, item, task, _basis = await _fixture(db_session)
    await db_session.commit()
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        ctx = _read_ctx(db_session, ws_id, usr_id, {})
        preview_selection, preview_terms = await _load_preview_inputs(ctx, item)
        _groups, live_selection, live_terms = await _load_live_inputs(
            db_session, ws_id, item
        )

        # non-vacuity (P-J 3rd ext): the compared pair is non-empty and fully resolved
        assert preview_selection.status is EconomicsStatusEnum.OK
        assert preview_selection.selected_group is not None
        assert preview_selection.basis_version is not None
        assert preview_selection.cost_model_version is not None
        assert len(list(preview_terms)) >= 1

        assert live_selection.status is preview_selection.status
        assert live_selection.selected_group.client_id == preview_selection.selected_group.client_id
        assert live_selection.basis_version.client_id == preview_selection.basis_version.client_id
        assert (
            live_selection.cost_model_version.client_id
            == preview_selection.cost_model_version.client_id
        )
        assert [t.client_id for t in live_terms] == [t.client_id for t in preview_terms]
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


# --------------------------------------------------------------------------
# C9 / A11 — the two-cost boundary, QUANTIFIED over both enumerated surfaces
# --------------------------------------------------------------------------


_MONEY_KEY_MARKERS = ("_minor", "cost", "price", "budget", "salary", "amount")


def _money_keys(payload: dict) -> set[str]:
    return {
        key
        for key in payload
        if any(marker in key for marker in _MONEY_KEY_MARKERS)
    }


def test_probe_c9_step_and_economics_money_key_sets_are_disjoint():
    """A11: quantify over the economics serializer surface, not one sample."""
    import inspect

    from beyo_manager.domain.tasks import serializers as step_serializers
    from beyo_manager.domain.item_economics import serializers as econ_serializers
    from beyo_manager.domain.item_economics.serializers import serialize_task_budget_status

    step = SimpleNamespace(
        client_id="tsp_1", task_id="tsk_1",
        state=SimpleNamespace(value="completed"),
        readiness_status=SimpleNamespace(value="ready"),
        sequence_order=1, working_section_id="wsec_1",
        assigned_worker_id=None, total_dependencies=0, completed_dependencies=0,
        working_section_name_snapshot="s",
        assigned_worker_display_name_snapshot=None,
        created_at=None, closed_at=None, ready_by_at=None,
        total_working_seconds=60, total_pause_seconds=0,
        total_ended_shift_seconds=0, total_working_count=0,
        total_pause_count=0, total_ended_shift_count=0,
        total_issues_count=0, total_issues_resolved_count=0,
        recorded_time_marked_wrong=False, total_cost_minor=999,
    )
    step_payload = step_serializers.serialize_step(step, include_monetary=True)

    step_money = _money_keys(step_payload)
    assert "total_cost_minor" in step_money, "non-vacuity: the step family carries salary money"

    status = SimpleNamespace(
        status=EconomicsStatusEnum.OK, item_binding="bound",
        actual_worker_seconds=1, actual_worker_minutes="1.00",
        remaining_worker_minutes="1.00", percent_consumed="1.00",
        variance_worker_minutes="1.00", production_budget_minor=1,
        allowed_worker_minutes="1.00", consumed_cost_minor=1,
        variance_cost_minor=1, evaluation_id="e", item_id="i", result=None,
    )
    econ_money = _money_keys(serialize_task_budget_status(status, include_monetary=True))
    assert "consumed_cost_minor" in econ_money, "non-vacuity: the economics family carries money"

    # enumerate the whole economics public surface, not a sample
    econ_public = sorted(
        name
        for name, obj in vars(econ_serializers).items()
        if not name.startswith("_") and inspect.isfunction(obj)
        and obj.__module__ == econ_serializers.__name__
    )
    assert len(econ_public) >= 12, econ_public

    assert step_money & econ_money == set(), step_money & econ_money


# --------------------------------------------------------------------------
# C1 (A7) — the WORKER service carries its own literal filter
# --------------------------------------------------------------------------


@pytest.mark.integration
async def test_probe_c1_worker_service_filter_is_independent_and_projection_blind(db_session):
    from beyo_manager.services.queries.item_economics.get_task_budget_status_worker import (
        get_task_budget_status_worker,
    )

    workspace, user, _item, task, _basis = await _fixture(db_session)
    await db_session.commit()
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        projection = await create_item_cost_projection(
            _ctx(db_session, ws_id, usr_id, {
                "task_client_id": tsk_id, "expected_sale_price_minor": 999999,
            })
        )
        await db_session.commit()
        committed = (
            await commit_item_cost_evaluation(
                _ctx(db_session, ws_id, usr_id, {"task_client_id": tsk_id, "label": "probe"})
            )
        )["evaluation"]
        await db_session.commit()

        from beyo_manager.models.tables.item_economics.item_cost_evaluation import (
            ItemCostEvaluation,
        )

        unfiltered = (
            await db_session.scalars(
                select(ItemCostEvaluation).where(ItemCostEvaluation.task_id == tsk_id)
            )
        ).all()
        assert unfiltered[0].client_id == projection["evaluation"]["client_id"]

        status = await get_task_budget_status_worker(
            _read_ctx(db_session, ws_id, usr_id, {"task_client_id": tsk_id})
        )
        assert status.evaluation_id == committed["client_id"]
        assert status.allowed_worker_minutes == Decimal(committed["allowed_worker_minutes"])
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


# --------------------------------------------------------------------------
# A15 / R17-2 — the DELETE status is RE-RESOLVED, not hardcoded
# --------------------------------------------------------------------------


@pytest.mark.integration
async def test_probe_a15_delete_valuation_reresolves_the_status(db_session):
    from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
    from beyo_manager.services.commands.item_economics.delete_item_valuation import (
        delete_item_valuation,
    )
    from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
    from sqlalchemy import update

    workspace, user, item, task, _basis = await _fixture(db_session)
    await db_session.commit()
    ws_id, usr_id, tsk_id = workspace.client_id, user.client_id, task.client_id
    try:
        valuation = await db_session.scalar(
            select(ItemValuation).where(ItemValuation.item_id == item.client_id)
        )
        # row 1 — CONFIGURED workspace: unchanged for normal use
        out = await delete_item_valuation(
            _ctx(db_session, ws_id, usr_id, {"client_id": valuation.client_id})
        )
        await db_session.commit()
        assert out["preview"]["status"] == EconomicsStatusEnum.ITEM_UNVALUED.value

        # row 2 — UNCONFIGURED workspace: the missing-setup reason, and it must
        # equal what a never-priced item in the same workspace reads (R17-2).
        second = ItemValuation(
            workspace_id=ws_id,
            item_id=item.client_id,
            expected_sale_price_minor=1000,
            currency=valuation.currency,
            created_by_id=usr_id,
        )
        db_session.add(second)
        await db_session.commit()
        await db_session.execute(
            update(CostModelVersion)
            .where(CostModelVersion.workspace_id == ws_id)
            .values(is_deleted=True)
        )
        await db_session.commit()

        out2 = await delete_item_valuation(
            _ctx(db_session, ws_id, usr_id, {"client_id": second.client_id})
        )
        await db_session.commit()

        never_priced = await get_task_budget_status(
            _read_ctx(db_session, ws_id, usr_id, {"task_client_id": tsk_id})
        )
        assert out2["preview"]["status"] != EconomicsStatusEnum.ITEM_UNVALUED.value
        assert out2["preview"]["status"] == never_priced.status.value
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


# --------------------------------------------------------------------------
# C11 (A2.5) — the lifetime read uses EVALUATION snapshots, never live fields
# --------------------------------------------------------------------------


@pytest.mark.integration
async def test_probe_c11_lifetime_uses_evaluation_snapshot_not_the_live_task_field(db_session):
    from beyo_manager.domain.tasks.enums import TaskTypeEnum
    from beyo_manager.services.queries.item_economics.get_item_lifetime_economics import (
        get_item_lifetime_economics,
    )

    workspace, user, item, task, _ev, _sec = await _committed_fixture(db_session)
    ws_id, usr_id, tsk_id, itm_id = (
        workspace.client_id, user.client_id, task.client_id, item.client_id,
    )
    try:
        # the live task's type is changed AFTER the commit — the snapshot must win
        task.task_type = TaskTypeEnum.INTERNAL
        await db_session.commit()

        read = await get_item_lifetime_economics(
            _read_ctx(db_session, ws_id, usr_id, {"item_client_id": itm_id})
        )
        assert read["episodes"][0]["task_type_snapshot"] == TaskTypeEnum.RETURN.value
    finally:
        await _cleanup(db_session, ws_id, usr_id, tsk_id)


# --------------------------------------------------------------------------
# C9 / HC-1 — the ROUTE's money boundary (the serializer row is not enough)
# --------------------------------------------------------------------------


_MANAGER_ONLY_PAYLOAD_KEYS = frozenset({
    "production_budget_minor",
    "consumed_cost_minor",
    "variance_cost_minor",
    "evaluation_id",
    "item_id",
})


@pytest.mark.parametrize("role_name", ["worker", "seller"], ids=["route-worker", "route-seller"])
def test_probe_c9_budget_status_endpoint_returns_no_money_for_worker_roles(role_name, monkeypatch):
    """The endpoint's own response body — not the serializer in isolation."""
    from tests.unit.routers.api_v1.test_item_economics_router import _client

    client, calls = _client(monkeypatch, role_name)

    response = client.get("/api/v1/item-economics/tasks/tsk_1/budget-status")

    assert response.status_code == 200
    body = response.json()["data"]
    assert _MANAGER_ONLY_PAYLOAD_KEYS.isdisjoint(body), sorted(
        _MANAGER_ONLY_PAYLOAD_KEYS.intersection(body)
    )
    assert not any(key.endswith("_minor") for key in body), sorted(body)
    # non-vacuity: the manager view really does carry those keys
    manager_client, _ = _client(monkeypatch, "manager")
    manager_body = manager_client.get(
        "/api/v1/item-economics/tasks/tsk_1/budget-status"
    ).json()["data"]
    assert _MANAGER_ONLY_PAYLOAD_KEYS.issubset(manager_body)
