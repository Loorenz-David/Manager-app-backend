"""Executable phase-4 contract cases for both task-economics consumers."""

from __future__ import annotations

import json
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select

from beyo_manager.domain.item_economics.budget_division import DivisionStep, divide_production_budget
from beyo_manager.domain.item_economics import budget_division
from beyo_manager.domain.item_economics.division_serializers import (
    serialize_budget_allocation,
    serialize_budget_step,
    serialize_production_time_section,
    serialize_task_production_time,
)
from beyo_manager.domain.item_economics.typical_filters import (
    SectionTypicalEvidence,
    SelectedTypical,
    TaskTypicalSelection,
    TypicalFilterSpec,
    reconcile_task_typicals,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_task_budget_allocations import get_task_budget_allocations
from beyo_manager.services.queries.item_economics.get_task_production_time import get_task_production_time
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep

from tests.integration.services.queries.item_economics._narrowing_fixture import seed_narrowing_history
from tests.integration.services.queries.item_economics.test_budget_allocations_query import _cleanup, _seed_two_section_allocation


SNAPSHOT = Path(__file__).with_name("snapshots") / "no_category_task_prerefactor.json"


def selected(section: str, value: int | None, basis: str = "section_wide", count: int = 0) -> SelectedTypical:
    evidence = SectionTypicalEvidence(section, None, 0, value, count)
    return SelectedTypical(section, value, basis, evidence, True, count)


def step(client_id: str, section: str = "section", *, state: str = "pending") -> DivisionStep:
    return DivisionStep(client_id=client_id, state=state, working_section_id=section)


def test_c3_missing_selection_is_an_honest_terminal_and_not_a_key_error():
    result = divide_production_budget(Decimal("1.00"), [step("missing")], {})
    row = result["steps"][0]
    assert row["typical_worker_seconds"] is None
    assert row["typical_basis"] == "insufficient_sample"
    assert row["sample_count"] == 0
    assert row["allowance_seconds"] == 60
    assert "typical_worker_seconds" not in {field.name for field in fields(DivisionStep)}


def test_c4_no_usable_typicals_use_equal_business_allocation_without_publishing_terminal():
    result = divide_production_budget(
        Decimal("1.00"), [step("a", "a"), step("b", "b")],
        {"a": selected("a", None), "b": selected("b", None)},
    )
    assert [row["allowance_seconds"] for row in result["steps"]] == [30, 30]
    assert all(row["typical_worker_seconds"] is None for row in result["steps"])


def test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections():
    row = {
        "step_id": "step", "working_section_id": "section", "section_name_snapshot": None,
        "typical_worker_seconds": None, "typical_basis": "insufficient_sample", "sample_count": 3,
        "allowance_seconds": 60, "worked_seconds": 0, "left_seconds": 60, "share_state": "on_track",
    }
    assert set(serialize_budget_step(row)) == {
        "step_id", "working_section_id", "section_name_snapshot", "typical_worker_seconds",
        "typical_basis", "sample_count", "allowance_seconds", "worked_seconds", "left_seconds", "share_state",
    }
    selection = TaskTypicalSelection(
        "section_wide_uniform", "uniform_basis_v1", "primary_item_category_v1", None,
        frozenset({"a", "b", "c"}),
        {
            "a": selected("a", 100, "item_narrowed", 7),
            "b": selected("b", 200, "section_wide", 8),
            "c": selected("c", None, "insufficient_sample", 2),
            "excluded": selected("excluded", 300, "item_narrowed", 9),
        },
    )
    from beyo_manager.domain.item_economics.division_serializers import serialize_typical_resolution

    resolution = serialize_typical_resolution(selection)
    assert resolution["sections_by_basis"] == {"item_narrowed": 1, "section_wide": 1, "insufficient_sample": 1}
    assert resolution["participating_section_count"] == 3
    assert serialize_budget_step({**row, "typical_worker_seconds": 0, "typical_basis": "section_wide"})["typical_worker_seconds"] == 0


def test_c12_defaults_are_always_present_on_the_production_section():
    payload = serialize_production_time_section(
        {"working_section_id": "section", "worked_seconds": 0, "step_count": 1, "share_state": "on_track"}
    )
    assert payload["typical"] == {
        "typical_worker_seconds": None, "sample_count": 0, "typical_basis": "insufficient_sample",
        "narrowed_sample_count": 0, "section_sample_count": 0,
        "method": "median_completed_section_totals", "window_days": 90, "min_sample_size": 5,
    }


def test_c7_excluded_sections_resolve_independently_in_both_directions():
    spec = TypicalFilterSpec(item_category_ids=frozenset({"chair"}))
    narrowed = lambda section: SectionTypicalEvidence(section, 540, 7, 600, 61)
    broad = lambda section: SectionTypicalEvidence(section, None, 0, 600, 61)
    selection = reconcile_task_typicals(
        {"a": narrowed("a"), "b": narrowed("b"), "excluded": broad("excluded")},
        spec, frozenset({"a", "b"}), frozenset({"a", "b", "excluded"}),
    )
    assert selection.task_typical_basis == "item_narrowed_uniform"
    assert selection.selected["excluded"].typical_basis == "section_wide"
    mirrored = reconcile_task_typicals(
        {"a": broad("a"), "excluded": narrowed("excluded")},
        spec, frozenset({"a"}), frozenset({"a", "excluded"}),
    )
    assert mirrored.task_typical_basis == "section_wide_uniform"
    assert mirrored.selected["excluded"].typical_basis == "item_narrowed"


@pytest.mark.integration
async def test_c9_no_category_snapshot_and_empty_spec_converge(db_session):
    values = await seed_narrowing_history(db_session)
    workspace, _user, _section, task, _unevaluated, item, *_ = values
    item.item_category_id = None
    await db_session.flush()
    context = ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "manager"},
        incoming_data={"task_client_id": task.client_id}, query_params={}, session=db_session,
    )
    allocations_context = ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "worker"},
        incoming_data={}, query_params={"task_ids": [task.client_id]}, session=db_session,
    )
    try:
        production = await get_task_production_time(context)
        allocations = await get_task_budget_allocations(allocations_context)
        current = {"production_time": production, "budget_allocations": allocations}
        if not SNAPSHOT.exists():
            SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
            SNAPSHOT.write_text(json.dumps(current, sort_keys=True, indent=2) + "\n")
        expected = json.loads(SNAPSHOT.read_text())
        def assert_preexisting_numeric(before, after):
            if isinstance(before, dict):
                for key, value in before.items():
                    if key in {"allocation_method", "typical_resolution"}:
                        continue
                    assert key in after
                    assert_preexisting_numeric(value, after[key])
            elif isinstance(before, list):
                assert len(before) == len(after)
                for old, new in zip(before, after):
                    assert_preexisting_numeric(old, new)
            elif isinstance(before, (int, float)) or before is None:
                assert after == before

        for surface in current:
            assert_preexisting_numeric(expected[surface], current[surface])
        assert production["typical_resolution"]["applied_filter"] is None
        assert production["typical_resolution"]["task_typical_basis"] == "section_wide_uniform"
        assert all(section["typical"]["typical_basis"] == "section_wide" for section in production["sections"]), production["sections"]
        assert allocations["budget_allocations"][0]["typical_resolution"]["applied_filter"] is None
    finally:
        await db_session.execute(delete(StepStateRecord).where(StepStateRecord.workspace_id == workspace.client_id))
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_c13_one_participating_sections_patch_moves_both_consumers(monkeypatch, db_session):
    values = await seed_narrowing_history(db_session)
    workspace, _user, _section, task, _unevaluated, _item, *_ = values
    monkeypatch.setattr(budget_division, "participating_sections", lambda _steps: frozenset())
    production_context = ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "manager"},
        incoming_data={"task_client_id": task.client_id}, query_params={}, session=db_session,
    )
    allocations_context = ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "worker"},
        incoming_data={}, query_params={"task_ids": [task.client_id]}, session=db_session,
    )
    try:
        production = await get_task_production_time(production_context)
        allocations = await get_task_budget_allocations(allocations_context)
        assert production["sections"]
        assert all(section["share_state"] == "excluded" for section in production["sections"])
        assert allocations["budget_allocations"][0]["steps"]
        assert all(step["share_state"] == "excluded" for step in allocations["budget_allocations"][0]["steps"])
    finally:
        await db_session.execute(delete(StepStateRecord).where(StepStateRecord.workspace_id == workspace.client_id))
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_c1_both_consumers_keep_settled_typicals_when_live_clock_moves(db_session):
    values = await _seed_two_section_allocation(db_session)
    workspace, user, _section, task, *_ = values
    open_steps = (
        await db_session.execute(
            select(TaskStep).where(
                TaskStep.task_id == task.client_id,
                TaskStep.state == TaskStepStateEnum.PENDING,
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    entered_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.add_all(
        [
            StepStateRecord(
                client_id=f"ssr_c1_{step.client_id}", workspace_id=workspace.client_id,
                step_id=step.client_id, state=TaskStepStateEnum.WORKING,
                entered_at=entered_at, created_by_id=user.client_id,
            )
            for step in open_steps
        ]
    )
    await db_session.flush()
    base = datetime.now(timezone.utc)
    contexts = [
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "manager"},
            incoming_data={"task_client_id": task.client_id}, query_params={}, session=db_session, now=base,
        ),
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "manager"},
            incoming_data={"task_client_id": task.client_id}, query_params={}, session=db_session, now=base + timedelta(days=1),
        ),
    ]
    allocations_contexts = [
        ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "worker"},
            incoming_data={}, query_params={"task_ids": [task.client_id]}, session=db_session, now=context.now,
        )
        for context in contexts
    ]
    try:
        production_rows = [await get_task_production_time(context) for context in contexts]
        allocation_rows = [await get_task_budget_allocations(context) for context in allocations_contexts]
        production_allowances = [
            (section["working_section_id"], section["allowance_seconds"])
            for section in production_rows[0]["sections"]
        ]
        assert production_allowances == [
            (section["working_section_id"], section["allowance_seconds"])
            for section in production_rows[1]["sections"]
        ]
        assert [
            (step["working_section_id"], step["allowance_seconds"])
            for step in allocation_rows[0]["budget_allocations"][0]["steps"]
        ] == [
            (step["working_section_id"], step["allowance_seconds"])
            for step in allocation_rows[1]["budget_allocations"][0]["steps"]
        ]
    finally:
        await db_session.execute(delete(StepStateRecord).where(StepStateRecord.workspace_id == workspace.client_id))
        await _cleanup(db_session, values)
