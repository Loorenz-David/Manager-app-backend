import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, update

from beyo_manager.domain.item_economics.budget_division import (
    ALLOCATION_METHOD,
    DivisionStep,
    _section_sort_key,
    divide_production_budget,
)
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_task_budget_allocations import get_task_budget_allocations
from beyo_manager.services.queries.item_economics.get_task_production_time import get_task_production_time

from tests.integration.services.queries.item_economics.test_budget_allocations_query import _cleanup, _seed


def _ctx(db_session, workspace_id, task_id, role_name="manager"):
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr", "role_name": role_name},
        incoming_data={"task_client_id": task_id},
        query_params={},
        session=db_session,
    )


def _step(token, workspace_id, task_id, section_id, user_id, *, state=TaskStepStateEnum.PENDING, worked=0, sequence_order=None, snapshot=None):
    return TaskStep(
        client_id=f"tsp_extra_{token}_{section_id}_{sequence_order or 'x'}",
        workspace_id=workspace_id,
        task_id=task_id,
        working_section_id=section_id,
        state=state,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        sequence_order=sequence_order,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=worked,
        working_section_name_snapshot=snapshot,
        created_by_id=user_id,
    )


@pytest.mark.integration
async def test_c1a_c2_section_order_is_total_and_nulls_last(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, *_ = values
    token = task.client_id.rsplit("_", 1)[-1]
    first = WorkingSection(client_id=f"wsec_tie_a_{token}", workspace_id=workspace.client_id, name="Alpha", order_list=2)
    second = WorkingSection(client_id=f"wsec_tie_b_{token}", workspace_id=workspace.client_id, name="Beta", order_list=2)
    null_section = WorkingSection(client_id=f"wsec_null_{token}", workspace_id=workspace.client_id, name="Zulu", order_list=None)
    db_session.add_all([first, second, null_section])
    await db_session.flush()
    db_session.add_all([
        _step(token, workspace.client_id, task.client_id, first.client_id, user.client_id, sequence_order=1),
        _step(token, workspace.client_id, task.client_id, second.client_id, user.client_id, sequence_order=2),
        _step(token, workspace.client_id, task.client_id, null_section.client_id, user.client_id, sequence_order=3),
    ])
    await db_session.flush()
    try:
        result = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        ids = [row["working_section_id"] for row in result["sections"]]
        assert ids == [first.client_id, second.client_id, section.client_id, null_section.client_id]
        again = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        assert result == again
    finally:
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_c1b_reversed_insertion_order_keeps_name_tie_break(db_session):
    values = await _seed(db_session)
    workspace, user, _section, task, *_ = values
    token = task.client_id.rsplit("_", 1)[-1]
    for base_step in values[11]:
        base_step.is_deleted = True
    alpha = WorkingSection(
        client_id=f"wsec_tie_b_{token}", workspace_id=workspace.client_id, name="Alpha", order_list=2
    )
    beta = WorkingSection(
        client_id=f"wsec_tie_a_{token}", workspace_id=workspace.client_id, name="Beta", order_list=2
    )
    # C1b: sections and their steps are inserted in the reverse order.
    db_session.add_all([beta, alpha])
    await db_session.flush()
    db_session.add_all([
        _step(token, workspace.client_id, task.client_id, beta.client_id, user.client_id, sequence_order=2),
        _step(token, workspace.client_id, task.client_id, alpha.client_id, user.client_id, sequence_order=1),
    ])
    await db_session.flush()
    try:
        result = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        assert [row["working_section_id"] for row in result["sections"]] == [alpha.client_id, beta.client_id]
    finally:
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_c4_c6a_c6b_c25a_c25b_grouped_row_preserves_state_and_snapshot(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, *_ = values
    token = task.client_id.rsplit("_", 1)[-1]
    for base_step in values[11]:
        base_step.is_deleted = True
    pending_entered_at = datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc)
    completed_entered_at = datetime(2026, 8, 17, 11, 0, tzinfo=timezone.utc)
    pending = _step(
        token, workspace.client_id, task.client_id, section.client_id, user.client_id,
        state=TaskStepStateEnum.PENDING, sequence_order=2, snapshot="Upholstery installation",
    )
    completed = _step(
        token, workspace.client_id, task.client_id, section.client_id, user.client_id,
        state=TaskStepStateEnum.COMPLETED, worked=600, sequence_order=1, snapshot="Upholstery",
    )
    pending.created_at = pending_entered_at - timedelta(minutes=1)
    completed.created_at = pending_entered_at
    db_session.add_all([pending, completed])
    await db_session.flush()
    pending_record = StepStateRecord(
        client_id=f"ssr_pending_{token}", workspace_id=workspace.client_id, step_id=pending.client_id,
        state=TaskStepStateEnum.PENDING, entered_at=pending_entered_at, created_by_id=user.client_id,
    )
    completed_record = StepStateRecord(
        client_id=f"ssr_completed_{token}", workspace_id=workspace.client_id, step_id=completed.client_id,
        state=TaskStepStateEnum.COMPLETED, entered_at=completed_entered_at, created_by_id=user.client_id,
    )
    db_session.add_all([pending_record, completed_record])
    await db_session.flush()
    pending.latest_state_record_id = pending_record.client_id
    completed.latest_state_record_id = completed_record.client_id
    section.name = "Renamed"
    await db_session.flush()
    try:
        result = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        row = next(row for row in result["sections"] if row["working_section_id"] == section.client_id)
        assert row["step_count"] == 2
        assert row["worked_seconds"] == 600
        assert row["state"] == "pending"
        assert row["state_entered_at"] == pending_entered_at.isoformat()
        assert row["section_name"] == "Renamed"
        assert row["section_name_snapshot"] == "Upholstery installation"
        assert row["allowance_seconds"] == 6000
    finally:
        await db_session.execute(
            update(TaskStep)
            .where(TaskStep.workspace_id == workspace.client_id)
            .values(latest_state_record_id=None)
        )
        await db_session.execute(delete(StepStateRecord).where(StepStateRecord.workspace_id == workspace.client_id))
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_c8_c9_excluded_and_mixed_sections_keep_task_charge(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, *_ = values
    token = task.client_id.rsplit("_", 1)[-1]
    excluded_section = WorkingSection(client_id=f"wsec_excluded_{token}", workspace_id=workspace.client_id, name="Excluded", order_list=4)
    db_session.add(excluded_section)
    values[10].allowed_worker_minutes = Decimal("20.00")
    await db_session.flush()
    db_session.add_all([
        _step(token, workspace.client_id, task.client_id, excluded_section.client_id, user.client_id, state=TaskStepStateEnum.SKIPPED, worked=30),
        _step(token, workspace.client_id, task.client_id, excluded_section.client_id, user.client_id, state=TaskStepStateEnum.SKIPPED, worked=40, sequence_order=2),
    ])
    await db_session.flush()
    try:
        result = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        row = next(row for row in result["sections"] if row["working_section_id"] == excluded_section.client_id)
        assert row["share_state"] == "excluded"
        assert row["allowance_seconds"] is None
        assert row["worked_seconds"] == 70
        mixed = next(row for row in result["sections"] if row["working_section_id"] == section.client_id)
        assert mixed["worked_seconds"] == 1200
        assert mixed["share_state"] == "over_share"
        assert result["budget"]["actual_worker_seconds"] == 1270
    finally:
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_c11_c12_c20_c24_e2_and_e3_agree_and_keep_e2_shape(db_session):
    values = await _seed(db_session)
    workspace, _user, section, task, *_ = values
    try:
        e2 = await get_task_budget_allocations(
            ServiceContext(
                identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "worker"},
                incoming_data={}, query_params={"task_ids": [task.client_id]}, session=db_session,
            )
        )
        e3 = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        e2_row = e2["budget_allocations"][0]
        e3_row = next(row for row in e3["sections"] if row["working_section_id"] == section.client_id)
        assert all(row["allocation_method"] == "static_proportional_section_v2" for row in e2["budget_allocations"])
        assert e3["allocation_method"] == "static_proportional_section_v2"
        assert sum(step["allowance_seconds"] for step in e2_row["steps"] if step["allowance_seconds"] is not None) == e3_row["allowance_seconds"]
        assert e2_row["allocation_method"] == ALLOCATION_METHOD == "static_proportional_section_v2"
        assert set(e2_row) == {"task_id", "status", "allowed_worker_minutes", "actual_worker_seconds", "remaining_worker_minutes", "allocation_method", "typical_resolution", "steps"}
        assert result_keys(e2_row["steps"][0]) == {"step_id", "working_section_id", "section_name_snapshot", "typical_worker_seconds", "typical_basis", "sample_count", "allowance_seconds", "worked_seconds", "left_seconds", "share_state"}
        assert sum(row["worked_seconds"] for row in e3["sections"]) == e3["budget"]["actual_worker_seconds"]
    finally:
        await _cleanup(db_session, values)


def result_keys(row):
    return set(row)


@pytest.mark.integration
async def test_c13_negative_open_residual_is_not_clamped(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, *_ = values
    values[10].allowed_worker_minutes = Decimal("1.00")
    for base_step in values[11]:
        base_step.is_deleted = True
    token = task.client_id.rsplit("_", 1)[-1]
    completed = _step(token, workspace.client_id, task.client_id, section.client_id, user.client_id, state=TaskStepStateEnum.COMPLETED, worked=100)
    pending = _step(token, workspace.client_id, task.client_id, section.client_id, user.client_id, state=TaskStepStateEnum.PENDING, sequence_order=2)
    db_session.add_all([completed, pending])
    await db_session.flush()
    try:
        result = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        row = next(row for row in result["sections"] if row["working_section_id"] == section.client_id)
        assert row["allowance_seconds"] == 60
        assert row["left_seconds"] == -40
    finally:
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_c14_c16_flat_time_only_degradation_and_tenant_boundary(db_session):
    values = await _seed(db_session)
    workspace, _user, _section, task, unevaluated_task, item, _task_item, _group, _basis, _model, evaluation, _steps, foreign_task, foreign_workspace = values
    frozen = ItemCostResult(
        client_id=f"icr_flat_{task.client_id}", workspace_id=workspace.client_id, task_id=task.client_id,
        item_id=item.client_id, evaluation_id=evaluation.client_id, actual_worker_seconds=1200,
        actual_worker_minutes=Decimal("20.00"), consumed_cost_minor=3, variance_worker_minutes=Decimal("80.00"),
        variance_cost_minor=4, task_closed_at=None, task_state_snapshot=TaskStateEnum.RESOLVED,
        calculation_version=1, computed_at=datetime.now(timezone.utc),
    )
    db_session.add(frozen)
    await db_session.flush()
    try:
        bodies = []
        for role in ("admin", "manager", "worker", "seller"):
            body = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id, role))
            bodies.append(json.dumps(body, sort_keys=True, separators=(",", ":")))
            keys = set()
            def walk(value):
                if isinstance(value, dict):
                    keys.update(value)
                    for item in value.values():
                        walk(item)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)
            walk(body)
            assert not any(token in key.lower() for key in keys for token in ("_minor", "cost", "price", "currency", "money", "valuation"))
        assert len({hashlib.sha256(body.encode()).hexdigest() for body in bodies}) == 1
        degraded = await get_task_production_time(_ctx(db_session, workspace.client_id, unevaluated_task.client_id))
        assert degraded["budget"] == {"allowed_worker_minutes": None, "actual_worker_seconds": None, "actual_worker_minutes": None, "remaining_worker_minutes": None, "percent_consumed": None}
        assert all(section["share_state"] == "no_budget" for section in degraded["sections"])
        with pytest.raises(Exception, match="Task not found"):
            await get_task_production_time(_ctx(db_session, workspace.client_id, foreign_task.client_id))
    finally:
        await db_session.execute(delete(ItemCostResult).where(ItemCostResult.client_id == frozen.client_id))
        await _cleanup(db_session, values)


@pytest.mark.integration
# The asserted equality is fixture coincidence after D9: frozen 20.00 / 80.00 reconstructs 100.00, matching live 20.00 / 100.00.
async def test_c17_frozen_final_uses_live_percent_without_money(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, *_ = values
    evaluation = values[10]
    result = ItemCostResult(
        client_id=f"icr_{task.client_id}", workspace_id=workspace.client_id, task_id=task.client_id,
        item_id=values[5].client_id, evaluation_id=evaluation.client_id, actual_worker_seconds=1200,
        actual_worker_minutes=Decimal("20.00"), consumed_cost_minor=3, variance_worker_minutes=Decimal("80.00"),
        variance_cost_minor=4, task_closed_at=None, task_state_snapshot=TaskStateEnum.RESOLVED,
        calculation_version=1, computed_at=datetime.now(timezone.utc),
    )
    db_session.add(result)
    await db_session.flush()
    try:
        body = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        assert body["final"]["percent_consumed"] == body["budget"]["percent_consumed"]
        assert "consumed_cost_minor" not in body["final"]
    finally:
        await db_session.execute(delete(ItemCostResult).where(ItemCostResult.client_id == result.client_id))
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_c15_c21_c22_task_scope_and_soft_deleted_section_outer_join(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, *_ = values
    values[11][1].working_section_name_snapshot = section.name
    section.is_deleted = True
    section_name = section.name
    await db_session.flush()
    try:
        body = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        assert len(body["sections"]) == 1
        row = body["sections"][0]
        assert row["working_section_id"] == section.client_id
        assert row["section_name"] is None
        assert row["order_list"] is None
        assert row["typical"]["typical_worker_seconds"] is None
        assert row["typical"]["typical_basis"] == "insufficient_sample"
        assert row["typical"]["sample_count"] == 0
        assert row["section_name_snapshot"] == "Upholstery"
        assert section_name == "Upholstery"
    finally:
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_c23_leftover_section_tie_uses_section_id_for_both_surfaces(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, *_ = values
    evaluation = values[10]
    evaluation.allowed_worker_minutes = Decimal("21.01")
    token = task.client_id.rsplit("_", 1)[-1]
    others = [
        WorkingSection(client_id=f"wsec_left_{token}_{i}", workspace_id=workspace.client_id, name=f"Left {i}", order_list=i)
        for i in range(2)
    ]
    db_session.add_all(others)
    await db_session.flush()
    db_session.add_all([
        _step(token, workspace.client_id, task.client_id, section.client_id, user.client_id, sequence_order=1),
        _step(token, workspace.client_id, task.client_id, others[0].client_id, user.client_id, sequence_order=2),
        _step(token, workspace.client_id, task.client_id, others[1].client_id, user.client_id, sequence_order=3),
    ])
    await db_session.flush()
    try:
        e2 = await get_task_budget_allocations(ServiceContext(identity={"workspace_id": workspace.client_id}, incoming_data={}, query_params={"task_ids": [task.client_id]}, session=db_session))
        e3 = await get_task_production_time(_ctx(db_session, workspace.client_id, task.client_id))
        e2_allowances = {}
        for step in e2["budget_allocations"][0]["steps"]:
            e2_allowances[step["working_section_id"]] = e2_allowances.get(step["working_section_id"], 0) + (step["allowance_seconds"] or 0)
        e3_allowances = {row["working_section_id"]: row["allowance_seconds"] for row in e3["sections"]}
        assert e2_allowances == e3_allowances
        min_allocated = min(key for key, value in e2_allowances.items() if value is not None)
        assert e2_allowances[min_allocated] == 21
    finally:
        await _cleanup(db_session, values)
