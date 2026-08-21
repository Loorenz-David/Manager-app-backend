from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from decimal import Decimal
import json

import pytest
from sqlalchemy import event, select

from beyo_manager.domain.item_economics.budget_division import EXCLUDED_STEP_STATES
from beyo_manager.domain.item_economics.serializers import serialize_task_budget_status
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.commands.task_steps._step_transition_core import _apply_step_transition
from beyo_manager.services.queries.item_economics import get_task_budget_allocations as allocations_module
from beyo_manager.services.queries.item_economics import live_worked_seconds as live_module
from beyo_manager.services.queries.item_economics import get_task_budget_status as status_module
from beyo_manager.services.queries.item_economics import get_task_production_time as production_module
from beyo_manager.services.queries.item_economics.get_task_budget_allocations import get_task_budget_allocations
from beyo_manager.services.queries.item_economics.get_task_budget_status import get_task_budget_status
from beyo_manager.services.queries.item_economics.get_task_budget_status_worker import (
    get_task_budget_status_worker,
)
from beyo_manager.services.queries.item_economics.get_task_production_time import get_task_production_time
from beyo_manager.services.commands.item_economics import _common as common_module
from beyo_manager.services.queries.working_sections.get_working_section_typical_times import (
    typical_times_statement,
)
from beyo_manager.services.queries.working_sections import (
    get_working_section_typical_times as typicals_module,
)
from beyo_manager.services.tasks.analytics.process_step_transition import _recompute_step_time_totals

from tests.integration.services.queries.item_economics.test_budget_allocations_query import _seed


UTC = timezone.utc


def _ctx(
    db_session,
    workspace_id: str,
    task_id: str,
    now: datetime,
    *,
    role: str = "manager",
    user_id: str = "usr_phase2",
):
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": role},
        incoming_data={"task_client_id": task_id},
        query_params={},
        session=db_session,
        now=now,
    )


async def _make_live_fixture(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, _unevaluated_task, _item, _task_item, _group, _basis, _model, evaluation, steps, _foreign_task, _foreign_workspace = values
    now = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)
    evaluation.allowed_worker_minutes = Decimal("20.00")
    live = steps[1]
    live.state = TaskStepStateEnum.WORKING
    live.created_at = now - timedelta(minutes=10)
    record = StepStateRecord(
        client_id=f"ssr_phase2_{workspace.client_id}",
        workspace_id=workspace.client_id,
        step_id=live.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=now - timedelta(minutes=10),
        exited_at=None,
        created_by_id=user.client_id,
        credited_user_id=user.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    live.latest_state_record_id = record.client_id
    skipped = TaskStep(
        client_id=f"tsp_phase2_skipped_{workspace.client_id}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.SKIPPED,
        readiness_status=live.readiness_status,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=240,
        created_by_id=user.client_id,
    )
    db_session.add(skipped)
    db_session.add(
        ItemCostResult(
            client_id=f"icr_phase2_{workspace.client_id}",
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            item_id=values[5].client_id,
            evaluation_id=evaluation.client_id,
            actual_worker_seconds=1200,
            actual_worker_minutes=Decimal("20.00"),
            consumed_cost_minor=1,
            variance_worker_minutes=Decimal("0.00"),
            variance_cost_minor=0,
            task_closed_at=None,
            task_state_snapshot=TaskStateEnum.ASSIGNED,
            calculation_version=1,
            computed_at=now - timedelta(days=1),
            created_at=now - timedelta(days=1),
        )
    )
    await db_session.flush()
    return values, now


async def _recommit_with_allowed_minutes(db_session, values, now: datetime, allowed: str):
    """Create the current evaluation that changes only the live denominator."""
    old = values[10]
    replacement = ItemCostEvaluation(
        client_id=f"ice_phase3_recommit_{values[0].client_id}",
        workspace_id=old.workspace_id,
        task_id=old.task_id,
        item_id=old.item_id,
        # Insert as a projection first so the self-FK and current-evaluation
        # uniqueness constraints can be crossed in two valid database steps.
        kind=ItemCostEvaluationKindEnum.PROJECTION,
        label=old.label,
        task_type_snapshot=old.task_type_snapshot,
        return_source_snapshot=old.return_source_snapshot,
        expected_sale_price_minor=old.expected_sale_price_minor,
        purchase_cost_minor=old.purchase_cost_minor,
        currency=old.currency,
        cost_model_version_id=old.cost_model_version_id,
        production_cost_group_id=old.production_cost_group_id,
        production_cost_basis_version_id=old.production_cost_basis_version_id,
        monthly_paid_hours_snapshot=old.monthly_paid_hours_snapshot,
        planning_utilization_percent_snapshot=old.planning_utilization_percent_snapshot,
        fixed_monthly_cost_minor_snapshot=old.fixed_monthly_cost_minor_snapshot,
        cost_per_worker_minute_minor_snapshot=old.cost_per_worker_minute_minor_snapshot,
        production_budget_minor=old.production_budget_minor,
        allowed_worker_minutes=Decimal(allowed),
        calculation_version=old.calculation_version,
        committed_at=now,
        promoted_from_id=old.client_id,
        created_by_id=old.created_by_id,
    )
    db_session.add(replacement)
    await db_session.flush([replacement])
    old.superseded_at = now
    old.superseded_by_id = replacement.client_id
    await db_session.flush()
    replacement.kind = ItemCostEvaluationKindEnum.COMMITTED
    await db_session.flush()
    return replacement


async def _make_share_state_fixture(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    evaluation = values[10]
    settled_steps = (
        await db_session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == workspace.client_id,
                TaskStep.task_id == task.client_id,
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    for step in settled_steps:
        step.total_working_seconds = 0
        if step.state in EXCLUDED_STEP_STATES:
            step.state = TaskStepStateEnum.PENDING

    live = values[11][1]
    live.state = TaskStepStateEnum.WORKING
    live.created_at = now - timedelta(minutes=25)
    record = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.workspace_id == workspace.client_id,
            StepStateRecord.step_id == live.client_id,
            StepStateRecord.exited_at.is_(None),
        )
    )
    assert record is not None
    record.entered_at = now - timedelta(minutes=25)
    evaluation.allowed_worker_minutes = Decimal("3.10")
    await db_session.flush()
    return values, now


async def _make_two_section_typicals_fixture(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, user, section, task, *_ = values
    evaluation = values[10]
    evaluation.allowed_worker_minutes = Decimal("100.00")
    token = workspace.client_id
    second_section = WorkingSection(
        client_id=f"wsec_phase2_second_{token}",
        workspace_id=workspace.client_id,
        name="Finishing",
    )
    db_session.add(second_section)
    await db_session.flush()
    for section_index, (section_for_groups, group_values) in enumerate(
        (
            (section, [1000, 2000, 3600, 5000, 6000]),
            (second_section, [600, 1200, 1800, 2400, 3000]),
        )
    ):
        for index, seconds in enumerate(group_values):
            historical_task = Task(
                client_id=f"tsk_phase2_typical_{token}_{section_index}_{index}",
                workspace_id=workspace.client_id,
                task_scalar_id=200 + section_index * 10 + index,
                task_type=task.task_type,
                state=TaskStateEnum.ASSIGNED,
                created_by_id=user.client_id,
            )
            historical_step = TaskStep(
                client_id=f"tsp_phase2_typical_{token}_{section_index}_{index}",
                workspace_id=workspace.client_id,
                task_id=historical_task.client_id,
                working_section_id=section_for_groups.client_id,
                state=TaskStepStateEnum.COMPLETED,
                readiness_status=TaskStepReadinessStatusEnum.READY,
                total_dependencies=0,
                completed_dependencies=0,
                total_working_seconds=seconds,
                closed_at=datetime.now(UTC) - timedelta(days=1),
                created_by_id=user.client_id,
            )
            db_session.add_all([historical_task, historical_step])
    second_step = TaskStep(
        client_id=f"tsp_phase2_second_live_{token}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=second_section.client_id,
        state=TaskStepStateEnum.PENDING,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=0,
        created_by_id=user.client_id,
    )
    db_session.add(second_step)
    await db_session.flush()
    return values, now, second_section


async def _make_ordering_fixture(db_session, *, row: int):
    values, now = await _make_live_fixture(db_session)
    workspace, user, section, task, *_ = values
    existing_steps = (
        await db_session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == workspace.client_id,
                TaskStep.task_id == task.client_id,
            )
        )
    ).scalars().all()
    for base_step in existing_steps:
        base_step.is_deleted = True

    entered_a = now - timedelta(hours=3)
    entered_b = now - timedelta(hours=2)
    created_a = now - timedelta(hours=1)
    created_b = now - timedelta(minutes=30)
    if row == 3:
        created_a, created_b = created_b, created_a

    step_a = TaskStep(
        client_id=f"stp_a_{workspace.client_id}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.WORKING,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=0,
        working_section_name_snapshot="Snapshot A",
        created_at=created_a,
        created_by_id=user.client_id,
    )
    step_b = TaskStep(
        client_id=f"stp_b_{workspace.client_id}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.PENDING,
        readiness_status=values[11][1].readiness_status,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=0,
        working_section_name_snapshot="Snapshot B",
        created_at=created_b,
        created_by_id=user.client_id,
    )
    db_session.add_all([step_a, step_b])
    await db_session.flush()
    record_a = StepStateRecord(
        client_id=f"ssr_a_{workspace.client_id}",
        workspace_id=workspace.client_id,
        step_id=step_a.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=entered_a,
        exited_at=None,
        created_by_id=user.client_id,
        credited_user_id=user.client_id,
    )
    record_b = StepStateRecord(
        client_id=f"ssr_b_{workspace.client_id}",
        workspace_id=workspace.client_id,
        step_id=step_b.client_id,
        state=TaskStepStateEnum.PENDING,
        entered_at=entered_a if row == 2 else entered_b,
        exited_at=entered_a if row == 2 else entered_b,
        created_by_id=user.client_id,
        credited_user_id=user.client_id,
    )
    db_session.add_all([record_a, record_b])
    await db_session.flush()
    step_a.latest_state_record_id = record_a.client_id
    step_b.latest_state_record_id = record_b.client_id
    await db_session.flush()
    return (values, step_a, step_b), now


async def _make_all_completed_fixture(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, user, section, task, *_ = values
    existing_steps = (
        await db_session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == workspace.client_id,
                TaskStep.task_id == task.client_id,
            )
        )
    ).scalars().all()
    for base_step in existing_steps:
        base_step.is_deleted = True
    step_a = TaskStep(
        client_id=f"stp_completed_a_{workspace.client_id}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.COMPLETED,
        readiness_status=values[11][1].readiness_status,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=100,
        created_at=now - timedelta(hours=1),
        created_by_id=user.client_id,
    )
    step_b = TaskStep(
        client_id=f"stp_completed_b_{workspace.client_id}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.COMPLETED,
        readiness_status=values[11][1].readiness_status,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=200,
        created_at=now,
        created_by_id=user.client_id,
    )
    db_session.add_all([step_a, step_b])
    await db_session.flush()
    record_a = StepStateRecord(
        client_id=f"ssr_completed_a_{workspace.client_id}",
        workspace_id=workspace.client_id,
        step_id=step_a.client_id,
        state=TaskStepStateEnum.COMPLETED,
        entered_at=now,
        exited_at=now,
        created_by_id=user.client_id,
    )
    record_b = StepStateRecord(
        client_id=f"ssr_completed_b_{workspace.client_id}",
        workspace_id=workspace.client_id,
        step_id=step_b.client_id,
        state=TaskStepStateEnum.COMPLETED,
        entered_at=now - timedelta(hours=1),
        exited_at=now - timedelta(hours=1),
        created_by_id=user.client_id,
    )
    db_session.add_all([record_a, record_b])
    await db_session.flush()
    step_a.latest_state_record_id = record_a.client_id
    step_b.latest_state_record_id = record_b.client_id
    await db_session.flush()
    db_session.expire(step_a, ["latest_state_record"])
    db_session.expire(step_b, ["latest_state_record"])
    return values, step_a, step_b, now


async def _make_three_task_batch(db_session, *, two_workers: bool):
    values, now = await _make_live_fixture(db_session)
    workspace, user, section, task, *_ = values
    live = values[11][1]
    live.state = TaskStepStateEnum.WORKING
    live.created_at = now - timedelta(minutes=10)
    live_record = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.workspace_id == workspace.client_id,
            StepStateRecord.step_id == live.client_id,
            StepStateRecord.exited_at.is_(None),
        )
    )
    assert live_record is not None
    live_record.credited_user_id = user.client_id

    second_user = User(
        client_id=f"usr_batch_two_{workspace.client_id}",
        username=f"batch_two_{workspace.client_id}",
        email=f"batch_two_{workspace.client_id}@example.test",
        password="secret",
    )
    db_session.add(second_user)
    await db_session.flush()
    extra_tasks = []
    extra_steps = []
    for index in (2, 3):
        extra_task = Task(
            client_id=f"tsk_batch_{index}_{workspace.client_id}",
            workspace_id=workspace.client_id,
            task_scalar_id=10 + index,
            task_type=task.task_type,
            state=TaskStateEnum.ASSIGNED,
            created_by_id=user.client_id,
        )
        extra_step = TaskStep(
            client_id=f"tsp_batch_{index}_{workspace.client_id}",
            workspace_id=workspace.client_id,
            task_id=extra_task.client_id,
            working_section_id=section.client_id,
            state=TaskStepStateEnum.WORKING,
            readiness_status=live.readiness_status,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=0,
            created_at=now - timedelta(minutes=10),
            created_by_id=user.client_id,
        )
        extra_tasks.append(extra_task)
        extra_steps.append(extra_step)
    db_session.add_all([*extra_tasks, *extra_steps])
    await db_session.flush()
    for index, step in zip((2, 3), extra_steps):
        credited = second_user.client_id if two_workers and index == 3 else user.client_id
        record = StepStateRecord(
            client_id=f"ssr_batch_{index}_{workspace.client_id}",
            workspace_id=workspace.client_id,
            step_id=step.client_id,
            state=TaskStepStateEnum.WORKING,
            entered_at=now - timedelta(minutes=10),
            exited_at=None,
            created_by_id=user.client_id,
            credited_user_id=credited,
        )
        db_session.add(record)
        await db_session.flush()
        step.latest_state_record_id = record.client_id
    await db_session.flush()
    return values, [task, *extra_tasks], now


@pytest.mark.integration
async def test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values

    production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now)
    )
    manager = await get_task_budget_status(
        _ctx(db_session, workspace.client_id, task.client_id, now)
    )
    worker = await get_task_budget_status_worker(
        _ctx(db_session, workspace.client_id, task.client_id, now, role="worker")
    )
    allocation = await get_task_budget_allocations(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": "usr_phase2", "role_name": "worker"},
            incoming_data={},
            query_params={"task_ids": [task.client_id]},
            session=db_session,
            now=now,
        )
    )

    section = production["sections"][0]
    assert production["budget"]["actual_worker_seconds"] == 2040
    assert section["worked_seconds"] == production["budget"]["actual_worker_seconds"]
    assert section["share_state"] == "over_share"
    assert section["left_seconds"] == section["allowance_seconds"] - section["worked_seconds"]
    assert allocation["budget_allocations"][0]["actual_worker_seconds"] == 2040
    assert {row["worked_seconds"] for row in allocation["budget_allocations"][0]["steps"]} >= {240, 600, 1200}

    manager_payload = serialize_task_budget_status(manager, include_monetary=True)
    worker_payload = serialize_task_budget_status(worker, include_monetary=False)
    for field in (
        "actual_worker_seconds",
        "actual_worker_minutes",
        "remaining_worker_minutes",
        "percent_consumed",
        "variance_worker_minutes",
    ):
        assert worker_payload[field] == manager_payload[field]

    settled_steps = (
        await db_session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == workspace.client_id,
                TaskStep.task_id == task.client_id,
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    assert worker_payload["actual_worker_seconds"] > sum(
        step.total_working_seconds for step in settled_steps
    )

    def walk_keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from walk_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk_keys(child)

    assert all(
        not any(token in key.lower() for token in ("_minor", "cost", "price", "currency", "money", "valuation"))
        for key in walk_keys(worker_payload)
    )


@pytest.mark.integration
async def test_c1_ep_final_freezes_while_budget_percent_ticks(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    entered_at = now - timedelta(minutes=10)

    pre_open = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, entered_at)
    )
    open_now = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now)
    )

    # P3-D3 C1/C4b: settled 20.00 + zero open share gives frozen 100.00 and
    # live 120.00 before opening; ten minutes of open share gives live 170.00.
    assert pre_open["final"]["percent_consumed"] == "100.00"
    assert open_now["final"] == pre_open["final"]
    assert pre_open["budget"]["percent_consumed"] == "120.00"
    assert open_now["budget"]["percent_consumed"] == "170.00"


@pytest.mark.integration
async def test_c2_worker_result_percent_uses_frozen_result_figures(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    worker = await get_task_budget_status_worker(
        _ctx(
            db_session,
            workspace.client_id,
            task.client_id,
            now - timedelta(minutes=10),
            role="worker",
        )
    )
    payload = serialize_task_budget_status(worker, include_monetary=False)

    # P3-D3 C2: actual 20.00 / (actual 20.00 + variance 0.00) = 100.00 exactly.
    assert payload["result"]["percent_consumed"] == "100.00"


@pytest.mark.integration
async def test_c3_recommit_changes_live_denominator_not_frozen_percent(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    result = await db_session.scalar(
        select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)
    )
    assert result is not None
    # P3-D3 C3: frozen actual 20.00 + variance 5.00 = allowance 25.00,
    # so the frozen percent is 80.00; the replacement evaluation uses 30.00
    # while the live pre-open basis remains 24.00 minutes.
    result.variance_worker_minutes = Decimal("5.00")
    await db_session.flush()

    before = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now - timedelta(minutes=10))
    )
    replacement = await _recommit_with_allowed_minutes(db_session, values, now, "30.00")
    assert replacement.allowed_worker_minutes == Decimal("30.00")
    after = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now - timedelta(minutes=10))
    )
    worker = await get_task_budget_status_worker(
        _ctx(
            db_session,
            workspace.client_id,
            task.client_id,
            now - timedelta(minutes=10),
            role="worker",
        )
    )
    worker_payload = serialize_task_budget_status(worker, include_monetary=False)

    assert before["final"]["percent_consumed"] == "80.00"
    assert before["budget"]["percent_consumed"] == "120.00"
    assert after["final"]["percent_consumed"] == "80.00"
    assert after["budget"]["percent_consumed"] == "80.00"
    assert worker_payload["result"]["percent_consumed"] == "80.00"


@pytest.mark.integration
async def test_c4a_manager_result_block_has_no_percent_consumed_key(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    manager = await get_task_budget_status(
        _ctx(db_session, workspace.client_id, task.client_id, now)
    )
    payload = serialize_task_budget_status(manager, include_monetary=True)

    def walk_keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from walk_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk_keys(child)

    assert "percent_consumed" not in set(walk_keys(payload["result"]))


@pytest.mark.integration
async def test_c4c_worker_top_level_percent_still_ticks(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    entered_at = now - timedelta(minutes=10)

    pre_open = await get_task_budget_status_worker(
        _ctx(db_session, workspace.client_id, task.client_id, entered_at, role="worker")
    )
    open_now = await get_task_budget_status_worker(
        _ctx(db_session, workspace.client_id, task.client_id, now, role="worker")
    )
    pre_payload = serialize_task_budget_status(pre_open, include_monetary=False)
    open_payload = serialize_task_budget_status(open_now, include_monetary=False)

    # P3-D3 C4c: the worker's live top-level percent is 120.00 before the
    # open share and 170.00 after it; its nested result remains 100.00.
    assert pre_payload["percent_consumed"] == "120.00"
    assert open_payload["percent_consumed"] == "170.00"
    assert open_payload["result"]["percent_consumed"] == "100.00"


@pytest.mark.integration
async def test_c6a_frozen_percent_survives_infeasible_current_evaluation(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    result = await db_session.scalar(
        select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)
    )
    assert result is not None
    # P3-D3 C6a: frozen 15.00 / (15.00 + 85.00) = 15.00 even when current
    # allowance is 0.00 and status is infeasible.
    result.actual_worker_minutes = Decimal("15.00")
    result.variance_worker_minutes = Decimal("85.00")
    values[10].allowed_worker_minutes = Decimal("0.00")
    await db_session.flush()

    production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now)
    )
    worker = await get_task_budget_status_worker(
        _ctx(db_session, workspace.client_id, task.client_id, now, role="worker")
    )
    worker_payload = serialize_task_budget_status(worker, include_monetary=False)

    assert production["status"] == "infeasible"
    assert production["final"]["percent_consumed"] == "15.00"
    assert worker_payload["status"] == "infeasible"
    assert worker_payload["result"]["percent_consumed"] == "15.00"


@pytest.mark.integration
async def test_c6b_frozen_non_positive_allowance_returns_null_percent(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    result = await db_session.scalar(
        select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)
    )
    assert result is not None
    # P3-D3 C6b: frozen 15.00 + (-15.00) = 0.00, so the percentage is
    # undefined solely because the frozen basis is non-positive; the current
    # evaluation remains positive and therefore has status "ok".
    result.actual_worker_minutes = Decimal("15.00")
    result.variance_worker_minutes = Decimal("-15.00")
    values[10].allowed_worker_minutes = Decimal("20.00")
    await db_session.flush()

    production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now)
    )
    worker = await get_task_budget_status_worker(
        _ctx(db_session, workspace.client_id, task.client_id, now, role="worker")
    )
    worker_payload = serialize_task_budget_status(worker, include_monetary=False)

    assert production["status"] == "ok"
    assert worker_payload["status"] == "ok"
    assert production["final"]["percent_consumed"] is None
    assert worker_payload["result"]["percent_consumed"] is None


@pytest.mark.integration
async def test_c6c_frozen_percent_preserves_over_budget_region(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    result = await db_session.scalar(
        select(ItemCostResult).where(ItemCostResult.task_id == task.client_id)
    )
    assert result is not None
    # P3-D3 C6c: frozen 15.00 / (15.00 - 5.00) = 150.00; the current
    # positive allowance keeps both payload statuses at "ok".
    result.actual_worker_minutes = Decimal("15.00")
    result.variance_worker_minutes = Decimal("-5.00")
    values[10].allowed_worker_minutes = Decimal("20.00")
    await db_session.flush()

    production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now)
    )
    worker = await get_task_budget_status_worker(
        _ctx(db_session, workspace.client_id, task.client_id, now, role="worker")
    )
    worker_payload = serialize_task_budget_status(worker, include_monetary=False)

    assert production["status"] == "ok"
    assert production["final"]["percent_consumed"] == "150.00"
    assert worker_payload["status"] == "ok"
    assert worker_payload["result"]["percent_consumed"] == "150.00"


@pytest.mark.integration
async def test_c2_positive_allowance_moves_share_state_under_live_basis(db_session):
    values, now = await _make_share_state_fixture(db_session)
    workspace, user, _section, task, *_ = values
    production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now, user_id=user.client_id)
    )
    section = production["sections"][0]
    assert section["allowance_seconds"] == 186
    assert section["worked_seconds"] == 1500
    assert section["left_seconds"] == -1314
    assert section["share_state"] == "over_share"


@pytest.mark.integration
async def test_b1_live_work_does_not_change_typical_section_weights(db_session):
    values, now, second_section = await _make_two_section_typicals_fixture(db_session)
    workspace, user, section, task, *_ = values
    production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now, user_id=user.client_id)
    )
    production_by_section = {
        row["working_section_id"]: row for row in production["sections"]
    }
    assert {
        section_id: production_by_section[section_id]["allowance_seconds"]
        for section_id in (section.client_id, second_section.client_id)
    } == {
        section.client_id: 3040,
        second_section.client_id: 1520,
    }

    allocation = await get_task_budget_allocations(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "worker"},
            incoming_data={},
            query_params={"task_ids": [task.client_id]},
            session=db_session,
            now=now,
        )
    )
    allocation_steps = allocation["budget_allocations"][0]["steps"]
    allowances_by_section = {}
    for row in allocation_steps:
        if row["allowance_seconds"] is not None:
            allowances_by_section[row["working_section_id"]] = (
                allowances_by_section.get(row["working_section_id"], 0)
                + row["allowance_seconds"]
            )
    assert allowances_by_section == {
        section.client_id: 3040,
        second_section.client_id: 1520,
    }


@pytest.mark.integration
async def test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds(
    db_session,
    monkeypatch,
):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    original = production_module.load_live_worked_seconds

    async def counted(*args, **kwargs):
        counted.calls += 1
        return await original(*args, **kwargs)

    counted.calls = 0
    monkeypatch.setattr(production_module, "load_live_worked_seconds", counted)
    monkeypatch.setattr(status_module, "load_live_worked_seconds", counted)
    monkeypatch.setattr(allocations_module, "load_live_worked_seconds", counted)
    await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id, now))
    assert counted.calls == 1

    counted.calls = 0
    await get_task_budget_status(_ctx(db_session, workspace.client_id, task.client_id, now))
    assert counted.calls == 1

    counted.calls = 0
    await get_task_budget_status_worker(
        _ctx(db_session, workspace.client_id, task.client_id, now, role="worker")
    )
    assert counted.calls == 1

    counted.calls = 0
    await get_task_budget_allocations(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": "usr_phase2", "role_name": "worker"},
            incoming_data={},
            query_params={"task_ids": [task.client_id]},
            session=db_session,
            now=now,
        )
    )
    assert counted.calls == 1

    assert not any(isinstance(obj, TaskStep) for obj in db_session.dirty)
    workspace_id = workspace.client_id
    task_id = task.client_id
    live_id = values[11][1].client_id
    db_session.expire_all()
    stored = (
        await db_session.execute(
            select(TaskStep.client_id, TaskStep.total_working_seconds).where(
                TaskStep.workspace_id == workspace_id,
                TaskStep.task_id == task_id,
                TaskStep.is_deleted.is_(False),
            )
        )
    ).all()
    assert {client_id: seconds for client_id, seconds in stored}[live_id] == 0


@pytest.mark.integration
async def test_c4_frozen_open_record_payloads_are_byte_identical(db_session, monkeypatch):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    original = production_module.load_live_worked_seconds

    async def counted(*args, **kwargs):
        counted.calls += 1
        return await original(*args, **kwargs)

    counted.calls = 0
    monkeypatch.setattr(production_module, "load_live_worked_seconds", counted)
    monkeypatch.setattr(status_module, "load_live_worked_seconds", counted)
    monkeypatch.setattr(allocations_module, "load_live_worked_seconds", counted)

    def payload_bytes(payload):
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()

    production_payloads = [
        await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id, now))
        for _ in range(2)
    ]
    assert payload_bytes(production_payloads[0]) == payload_bytes(production_payloads[1])
    assert counted.calls == 2

    counted.calls = 0
    manager_payloads = [
        serialize_task_budget_status(
            await get_task_budget_status(_ctx(db_session, workspace.client_id, task.client_id, now)),
            include_monetary=True,
        )
        for _ in range(2)
    ]
    assert payload_bytes(manager_payloads[0]) == payload_bytes(manager_payloads[1])
    assert counted.calls == 2

    counted.calls = 0
    worker_payloads = [
        serialize_task_budget_status(
            await get_task_budget_status_worker(
                _ctx(db_session, workspace.client_id, task.client_id, now, role="worker")
            ),
            include_monetary=False,
        )
        for _ in range(2)
    ]
    assert payload_bytes(worker_payloads[0]) == payload_bytes(worker_payloads[1])
    assert counted.calls == 2

    counted.calls = 0
    allocation_payloads = [
        await get_task_budget_allocations(
            ServiceContext(
                identity={"workspace_id": workspace.client_id, "user_id": "usr_phase2", "role_name": "worker"},
                incoming_data={},
                query_params={"task_ids": [task.client_id]},
                session=db_session,
                now=now,
            )
        )
        for _ in range(2)
    ]
    assert payload_bytes(allocation_payloads[0]) == payload_bytes(allocation_payloads[1])
    assert counted.calls == 2


@pytest.mark.integration
async def test_c8_allocations_batch_has_one_open_record_probe(db_session, monkeypatch):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    original = allocations_module.load_live_worked_seconds

    async def counted(*args, **kwargs):
        counted.calls += 1
        return await original(*args, **kwargs)

    counted.calls = 0
    monkeypatch.setattr(allocations_module, "load_live_worked_seconds", counted)
    from beyo_manager.models import database

    statements: list[str] = []
    engine = database._engine
    assert engine is not None

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        await get_task_budget_allocations(
            ServiceContext(
                identity={"workspace_id": workspace.client_id, "user_id": "usr_phase2", "role_name": "worker"},
                incoming_data={},
                query_params={"task_ids": [task.client_id]},
                session=db_session,
                now=now,
            )
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)

    assert counted.calls == 1
    assert sum(
        "FROM step_state_records" in statement and "JOIN task_steps" not in statement
        for statement in statements
    ) == 1


@pytest.mark.unit
def test_c11_typicals_statement_uses_the_request_clock_when_supplied():
    frozen = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    statement = typical_times_statement("ws_phase2", now=frozen)
    # C11's clock stub is installed at this module's bound ``datetime`` name;
    # passing ctx.now makes the statement construction perform zero reads there.
    assert frozen - timedelta(days=90) in statement.compile().params.values()


@pytest.mark.integration
async def test_c12_preview_inputs_uses_ctx_clock_and_keeps_command_shim(monkeypatch):
    captured: list[date] = []

    def fake_selection(*args):
        captured.append(args[-1])
        return SimpleNamespace(cost_model_version=None)

    class EmptyResult:
        def scalars(self):
            return self

        def all(self):
            return []

    class EmptySession:
        async def execute(self, statement):
            return EmptyResult()

    monkeypatch.setattr(common_module, "resolve_economics_selection", fake_selection)
    frozen = datetime(2020, 1, 1, 0, 0, tzinfo=UTC)
    ctx = ServiceContext(
        identity={"workspace_id": "ws_phase2", "user_id": "usr_phase2"},
        incoming_data={},
        query_params={},
        session=EmptySession(),
        now=frozen,
    )
    item = SimpleNamespace(item_major_category_snapshot="wood")

    await common_module._load_preview_inputs(ctx, item, now=ctx.now)
    assert captured == [frozen.date()]

    monkeypatch.setattr(common_module, "today_utc", lambda: date(2099, 1, 1))
    await common_module._load_preview_inputs(ctx, item)
    assert captured[-1] == date(2099, 1, 1)


@pytest.mark.integration
async def test_c3_population_fold_counts_nonzero_skipped_consumption_on_manager_face(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, *_ = values
    values[11][0].is_deleted = True
    status = await get_task_budget_status(_ctx(db_session, workspace.client_id, task.client_id, now))
    assert status.actual_worker_seconds == 840


@pytest.mark.integration
async def test_c6_allowances_are_byte_identical_after_settlement_recompute(db_session, monkeypatch):
    values, now, _second_section = await _make_two_section_typicals_fixture(db_session)
    workspace, user, _section, task, *_ = values
    division_inputs: list[list] = []
    production_divide = production_module.divide_production_budget
    allocations_divide = allocations_module.divide_production_budget

    def capture_production_division(*args, **kwargs):
        division_inputs.append(list(args[1]))
        return production_divide(*args, **kwargs)

    def capture_allocations_division(*args, **kwargs):
        division_inputs.append(list(args[1]))
        return allocations_divide(*args, **kwargs)

    monkeypatch.setattr(production_module, "divide_production_budget", capture_production_division)
    monkeypatch.setattr(allocations_module, "divide_production_budget", capture_allocations_division)
    before_production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now, user_id=user.client_id)
    )
    before_allocations = await get_task_budget_allocations(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "worker"},
            incoming_data={},
            query_params={"task_ids": [task.client_id]},
            session=db_session,
            now=now,
        )
    )
    all_steps = (
        await db_session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == workspace.client_id,
                TaskStep.task_id == task.client_id,
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    excluded_ids = {step.client_id for step in all_steps if step.state in EXCLUDED_STEP_STATES}
    open_excluded = (
        await db_session.execute(
            select(StepStateRecord.step_id).where(
                StepStateRecord.workspace_id == workspace.client_id,
                StepStateRecord.step_id.in_(excluded_ids),
                StepStateRecord.exited_at.is_(None),
            )
        )
    ).scalars().all()
    assert open_excluded == []
    settled_charged_seconds = sum(
        step.total_working_seconds for step in all_steps if step.client_id in excluded_ids
    )
    assert settled_charged_seconds == 1440
    assert all(
        sum(step.total_working_seconds for step in division if step.state in EXCLUDED_STEP_STATES)
        == settled_charged_seconds
        for division in division_inputs
    )
    live = values[11][1]
    record = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.workspace_id == workspace.client_id,
            StepStateRecord.step_id == live.client_id,
            StepStateRecord.exited_at.is_(None),
        )
    )
    assert record is not None
    close_at = now
    await _apply_step_transition(
        _ctx(db_session, workspace.client_id, task.client_id, close_at, user_id=user.client_id),
        live,
        task,
        record,
        new_state=TaskStepStateEnum.PAUSED,
        pause_reason_id=None,
        description=None,
        credited_user_id=user.client_id,
        now=close_at,
    )
    await _recompute_step_time_totals(db_session, workspace.client_id, live.client_id, close_at)
    await db_session.flush()
    after_production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, close_at, user_id=user.client_id)
    )
    after_allocations = await get_task_budget_allocations(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "worker"},
            incoming_data={},
            query_params={"task_ids": [task.client_id]},
            session=db_session,
            now=close_at,
        )
    )
    assert [
        (row["allowance_seconds"], row["left_seconds"])
        for row in before_production["sections"]
    ] == [
        (row["allowance_seconds"], row["left_seconds"])
        for row in after_production["sections"]
    ]
    before_steps = before_allocations["budget_allocations"][0]["steps"]
    after_steps = after_allocations["budget_allocations"][0]["steps"]
    assert [
        (row["step_id"], row["allowance_seconds"], row["left_seconds"])
        for row in before_steps
    ] == [
        (row["step_id"], row["allowance_seconds"], row["left_seconds"])
        for row in after_steps
    ]
    assert len(division_inputs) == 4
    assert all(
        sum(step.total_working_seconds for step in division if step.state in EXCLUDED_STEP_STATES)
        == settled_charged_seconds
        for division in division_inputs
    )


@pytest.mark.integration
async def test_c6_created_at_is_carried_into_the_production_division_row(db_session):
    (values, step_a, step_b), now = await _make_ordering_fixture(db_session, row=2)
    workspace, user, _section, task, *_ = values
    production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now, user_id=user.client_id)
    )
    section = production["sections"][0]
    assert section["state"] == TaskStepStateEnum.PENDING.value
    assert section["state_entered_at"] == (now - timedelta(hours=3)).isoformat()
    assert section["section_name_snapshot"] == "Snapshot B"
    allocations = await get_task_budget_allocations(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "worker"},
            incoming_data={},
            query_params={"task_ids": [task.client_id]},
            session=db_session,
            now=now,
        )
    )
    step_rows = {row["step_id"]: row for row in allocations["budget_allocations"][0]["steps"]}
    assert {step_a.client_id, step_b.client_id} == set(step_rows)
    assert {
        step_id: (row["allowance_seconds"], row["worked_seconds"], row["section_name_snapshot"])
        for step_id, row in step_rows.items()
    } == {
        step_a.client_id: (600, 10800, "Snapshot A"),
        step_b.client_id: (600, 0, "Snapshot B"),
    }


@pytest.mark.integration
async def test_c6_latest_state_record_is_carried_into_the_production_division_row(db_session):
    (values, _step_a, _step_b), now = await _make_ordering_fixture(db_session, row=3)
    workspace, user, _section, task, *_ = values
    production = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now, user_id=user.client_id)
    )
    section = production["sections"][0]
    assert section["state"] == TaskStepStateEnum.PENDING.value
    assert section["state_entered_at"] == (now - timedelta(hours=2)).isoformat()
    assert section["section_name_snapshot"] == "Snapshot B"


@pytest.mark.integration
async def test_c6_all_completed_e_a_section_keeps_allowances_without_eager_state_load(db_session):
    values, step_a, step_b, now = await _make_all_completed_fixture(db_session)
    workspace, user, _section, task, *_ = values
    allocations = await get_task_budget_allocations(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "worker"},
            incoming_data={},
            query_params={"task_ids": [task.client_id]},
            session=db_session,
            now=now,
        )
    )
    step_rows = {row["step_id"]: row for row in allocations["budget_allocations"][0]["steps"]}
    assert {
        step_a.client_id: (step_rows[step_a.client_id]["allowance_seconds"], step_rows[step_a.client_id]["left_seconds"]),
        step_b.client_id: (step_rows[step_b.client_id]["allowance_seconds"], step_rows[step_b.client_id]["left_seconds"]),
    } == {
        step_a.client_id: (100, 0),
        step_b.client_id: (1100, 900),
    }


@pytest.mark.integration
async def test_c8_three_task_batch_shares_one_probe_and_one_worker_sweep(db_session, monkeypatch):
    values, tasks, now = await _make_three_task_batch(db_session, two_workers=False)
    workspace, user, _section, _task, *_ = values
    original = live_module.compute_record_contributions

    async def counted(*args, **kwargs):
        counted.calls += 1
        return await original(*args, **kwargs)

    counted.calls = 0
    # D6: SQL text counts the loader's open-record probe; this wrapper counts the
    # per-worker averaging sweep, the two halves of C8's batch contract.
    monkeypatch.setattr(live_module, "compute_record_contributions", counted)
    statements: list[str] = []
    from beyo_manager.models import database

    engine = database._engine
    assert engine is not None

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        await get_task_budget_allocations(
            ServiceContext(
                identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "worker"},
                incoming_data={},
                query_params={"task_ids": [task.client_id for task in tasks]},
                session=db_session,
                now=now,
            )
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)
    assert sum(
        "FROM step_state_records" in statement and "JOIN task_steps" not in statement
        for statement in statements
    ) == 1
    assert counted.calls == 1


@pytest.mark.integration
async def test_c8_three_task_batch_runs_one_sweep_per_active_worker(db_session, monkeypatch):
    values, tasks, now = await _make_three_task_batch(db_session, two_workers=True)
    workspace, user, _section, _task, *_ = values
    original = live_module.compute_record_contributions

    async def counted(*args, **kwargs):
        counted.calls += 1
        return await original(*args, **kwargs)

    counted.calls = 0
    monkeypatch.setattr(live_module, "compute_record_contributions", counted)
    statements: list[str] = []
    from beyo_manager.models import database

    engine = database._engine
    assert engine is not None

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        await get_task_budget_allocations(
            ServiceContext(
                identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "worker"},
                incoming_data={},
                query_params={"task_ids": [task.client_id for task in tasks]},
                session=db_session,
                now=now,
            )
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)
    assert sum(
        "FROM step_state_records" in statement and "JOIN task_steps" not in statement
        for statement in statements
    ) == 1
    assert counted.calls == 2


@pytest.mark.integration
async def test_c9_settlement_window_drop_is_visible_until_recompute(db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, user, _section, task, *_ = values
    before = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, now, user_id=user.client_id)
    )
    live = values[11][1]
    record = await db_session.scalar(
        select(StepStateRecord).where(
            StepStateRecord.workspace_id == workspace.client_id,
            StepStateRecord.step_id == live.client_id,
            StepStateRecord.exited_at.is_(None),
        )
    )
    assert record is not None
    close_at = now
    await _apply_step_transition(
        _ctx(db_session, workspace.client_id, task.client_id, close_at, user_id=user.client_id),
        live,
        task,
        record,
        new_state=TaskStepStateEnum.PAUSED,
        pause_reason_id=None,
        description=None,
        credited_user_id=user.client_id,
        now=close_at,
    )
    after_close = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, close_at, user_id=user.client_id)
    )
    assert after_close["sections"][0]["worked_seconds"] == 1440
    assert before["sections"][0]["worked_seconds"] == 2040
    await _recompute_step_time_totals(db_session, workspace.client_id, live.client_id, close_at)
    await db_session.flush()
    after_recompute = await get_task_production_time(
        _ctx(db_session, workspace.client_id, task.client_id, close_at, user_id=user.client_id)
    )
    assert after_recompute["sections"][0]["worked_seconds"] == 2040


@pytest.mark.integration
async def test_c11_typicals_compatibility_shim_keeps_five_sample_median(db_session):
    values, _now = await _make_live_fixture(db_session)
    workspace, user, section, task, *_ = values
    for index, seconds in enumerate((1000, 2000, 3600, 5000, 6000)):
        historical_task = Task(
            client_id=f"tsk_typical_phase2_{workspace.client_id}_{index}",
            workspace_id=workspace.client_id,
            task_scalar_id=100 + index,
            task_type=task.task_type,
            state=TaskStateEnum.ASSIGNED,
            created_by_id=user.client_id,
        )
        historical_step = TaskStep(
            client_id=f"tsp_typical_phase2_{workspace.client_id}_{index}",
            workspace_id=workspace.client_id,
            task_id=historical_task.client_id,
            working_section_id=section.client_id,
            state=TaskStepStateEnum.COMPLETED,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=seconds,
            closed_at=datetime.now(UTC) - timedelta(days=1),
            created_by_id=user.client_id,
        )
        db_session.add_all([historical_task, historical_step])
    await db_session.flush()
    result = await db_session.execute(typical_times_statement(workspace.client_id))
    row = next(row for row in result if row.client_id == section.client_id)
    assert row.sample_count == 5
    assert row.typical_worker_seconds == 3600


@pytest.mark.integration
async def test_c11_c12_surface_call_sites_do_not_fall_back_to_module_clocks(monkeypatch, db_session):
    values, now = await _make_live_fixture(db_session)
    workspace, _user, _section, task, unevaluated_task, *_ = values
    typical_reads: list[datetime] = []
    config_reads: list[date] = []

    class NoClock:
        @classmethod
        def now(cls, tz=None):
            typical_reads.append(now)
            raise AssertionError("surface should pass ctx.now to typical_times_statement")

    def unexpected_today():
        config_reads.append(now.date())
        raise AssertionError("surface should pass ctx.now to _load_preview_inputs")

    monkeypatch.setattr(typicals_module, "datetime", NoClock)
    monkeypatch.setattr(common_module, "today_utc", unexpected_today)
    await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id, now))
    await get_task_budget_allocations(
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": "usr_phase2", "role_name": "worker"},
            incoming_data={},
            query_params={"task_ids": [task.client_id]},
            session=db_session,
            now=now,
        )
    )
    await get_task_budget_status(
        _ctx(db_session, workspace.client_id, unevaluated_task.client_id, now)
    )
    await get_task_budget_status_worker(
        _ctx(db_session, workspace.client_id, unevaluated_task.client_id, now, role="worker")
    )
    assert typical_reads == []
    assert config_reads == []
