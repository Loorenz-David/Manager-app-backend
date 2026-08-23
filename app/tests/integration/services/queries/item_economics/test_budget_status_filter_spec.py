"""Phase-3 contract tests for the additive TaskBudgetStatus filter carrier."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import fields
from decimal import Decimal
from importlib import import_module

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.item_economics.enums import (
    EconomicsStatusEnum,
    ItemCostEvaluationKindEnum,
)
from beyo_manager.domain.item_economics.serializers import serialize_task_budget_status
from beyo_manager.domain.item_economics.typical_filters import TypicalFilterSpec
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.tasks.add_item_to_task import add_item_to_task
from beyo_manager.services.context import ServiceContext


manager_module = import_module(
    "beyo_manager.services.queries.item_economics.get_task_budget_status"
)
worker_module = import_module(
    "beyo_manager.services.queries.item_economics.get_task_budget_status_worker"
)


class _ScalarSession:
    def __init__(self, scalar_values: list[object | None], rows: list[object] | None = None):
        self.scalar_values = iter(scalar_values)
        self.rows = rows or []

    async def scalar(self, _statement):
        return next(self.scalar_values)

    async def execute(self, _statement):
        return _ExecuteResult(self.rows)


class _ExecuteResult:
    def __init__(self, rows: list[object]):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self.rows)


def _ctx(session, task_id: str = "tsk_filter_spec") -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": "ws_filter_spec",
            "user_id": "usr_filter_spec",
            "role_name": "manager",
        },
        incoming_data={"task_client_id": task_id},
        query_params={},
        session=session,
    )


def _task(task_id: str = "tsk_filter_spec") -> Task:
    return Task(
        client_id=task_id,
        workspace_id="ws_filter_spec",
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
    )


def _item(item_id: str, category_id: str | None) -> Item:
    return Item(
        client_id=item_id,
        workspace_id="ws_filter_spec",
        item_category_id=category_id,
    )


def _evaluation(item_id: str) -> ItemCostEvaluation:
    return ItemCostEvaluation(
        client_id="ice_filter_spec",
        workspace_id="ws_filter_spec",
        task_id="tsk_filter_spec",
        item_id=item_id,
        kind=ItemCostEvaluationKindEnum.COMMITTED,
        task_type_snapshot=TaskTypeEnum.INTERNAL,
        expected_sale_price_minor=100,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        production_budget_minor=100,
        allowed_worker_minutes=Decimal("10.00"),
        cost_per_worker_minute_minor_snapshot=Decimal("1.00"),
    )


def _status(**overrides):
    values = {
        "status": EconomicsStatusEnum.NOT_EVALUATED,
        "item_binding": "detached",
        "actual_worker_seconds": None,
        "actual_worker_minutes": None,
        "remaining_worker_minutes": None,
        "percent_consumed": None,
        "variance_worker_minutes": None,
        "production_budget_minor": None,
        "allowed_worker_minutes": None,
        "consumed_cost_minor": None,
        "variance_cost_minor": None,
        "evaluation_id": None,
        "item_id": None,
        "result": None,
    }
    values.update(overrides)
    return manager_module.TaskBudgetStatus(**values)


def test_C1_task_budget_status_appends_defaulted_spec_after_result():
    assert [field.name for field in fields(manager_module.TaskBudgetStatus)] == [
        "status",
        "item_binding",
        "actual_worker_seconds",
        "actual_worker_minutes",
        "remaining_worker_minutes",
        "percent_consumed",
        "variance_worker_minutes",
        "production_budget_minor",
        "allowed_worker_minutes",
        "consumed_cost_minor",
        "variance_cost_minor",
        "evaluation_id",
        "item_id",
        "result",
        "typical_filter_spec",
    ]
    task_budget_fields = fields(manager_module.TaskBudgetStatus)
    assert task_budget_fields[13].name == "result"  # zero-based index
    assert task_budget_fields[14].name == "typical_filter_spec"  # zero-based index
    assert task_budget_fields[14].default is None
    assert _status().typical_filter_spec is None


def test_C2_manager_budget_status_payload_has_the_existing_exact_key_set():
    expected_keys = frozenset(
        {
            "status",
            "item_binding",
            "actual_worker_seconds",
            "actual_worker_minutes",
            "remaining_worker_minutes",
            "percent_consumed",
            "variance_worker_minutes",
            "result",
            "production_budget_minor",
            "allowed_worker_minutes",
            "consumed_cost_minor",
            "variance_cost_minor",
            "evaluation_id",
            "item_id",
        }
    )
    assert frozenset(serialize_task_budget_status(_status(), include_monetary=True)) == expected_keys


@pytest.mark.asyncio
async def test_C2_and_C3a_worker_service_serialization_is_not_a_payload_change(monkeypatch):
    task = _task()
    chair = _item("itm_chair", "cat_chair")

    async def load_task_and_item(_ctx):
        return task, chair

    async def load_preview_inputs(*_args, **_kwargs):
        return None, None

    monkeypatch.setattr(worker_module, "_load_task_and_item", load_task_and_item)
    monkeypatch.setattr(worker_module, "_load_preview_inputs", load_preview_inputs)
    monkeypatch.setattr(
        worker_module,
        "resolve_item_economics_status",
        lambda *_args: EconomicsStatusEnum.NOT_EVALUATED,
    )

    status = await worker_module.get_task_budget_status_worker(_ctx(_ScalarSession([None, None])))
    assert status.typical_filter_spec == TypicalFilterSpec(
        item_category_ids=frozenset({"cat_chair"})
    )

    expected_keys = frozenset(
        {
            "status",
            "item_binding",
            "actual_worker_seconds",
            "actual_worker_minutes",
            "remaining_worker_minutes",
            "percent_consumed",
            "variance_worker_minutes",
            "result",
            "allowed_worker_minutes",
        }
    )
    assert frozenset(serialize_task_budget_status(status, include_monetary=False)) == expected_keys


@pytest.mark.asyncio
async def test_C4_manager_uses_loaded_primary_item_not_evaluation_item(monkeypatch):
    task = _task()
    evaluated_item = _item("itm_table", "cat_table")
    primary_item = _item("itm_chair", "cat_chair")
    evaluation = _evaluation(evaluated_item.client_id)

    async def load_task_and_item(_ctx):
        return task, primary_item

    async def load_live_seconds(*_args):
        return {}

    monkeypatch.setattr(manager_module, "_load_task_and_item", load_task_and_item)
    monkeypatch.setattr(manager_module, "load_live_worked_seconds", load_live_seconds)

    status = await manager_module.get_task_budget_status(
        _ctx(_ScalarSession([evaluation, None]))
    )
    assert status.item_binding == "mismatched"
    assert status.item_id == evaluated_item.client_id
    assert status.typical_filter_spec == TypicalFilterSpec(
        item_category_ids=frozenset({primary_item.item_category_id})
    )


@pytest.mark.asyncio
async def test_C4_worker_uses_loaded_primary_item_not_evaluation_item(monkeypatch):
    task = _task()
    evaluated_item = _item("itm_table_worker", "cat_table")
    primary_item = _item("itm_chair_worker", "cat_chair")
    evaluation = _evaluation(evaluated_item.client_id)

    async def load_task_and_item(_ctx):
        return task, primary_item

    async def load_live_seconds(*_args):
        return {}

    monkeypatch.setattr(worker_module, "_load_task_and_item", load_task_and_item)
    monkeypatch.setattr(manager_module, "load_live_worked_seconds", load_live_seconds)

    status = await worker_module.get_task_budget_status_worker(
        _ctx(_ScalarSession([evaluation, None]))
    )
    assert status.item_binding == "mismatched"
    assert status.item_id == evaluated_item.client_id
    assert status.typical_filter_spec == TypicalFilterSpec(
        item_category_ids=frozenset({primary_item.item_category_id})
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "service_module", "item", "expected"),
    [
        ("C5-a-manager-no-primary", manager_module, None, None),
        ("C5-b-manager-categoryless-primary", manager_module, _item("itm_null", None), TypicalFilterSpec()),
        (
            "C5-e-manager-categorized-primary",
            manager_module,
            _item("itm_category", "cat_chair"),
            TypicalFilterSpec(item_category_ids=frozenset({"cat_chair"})),
        ),
        ("C5-c-worker-no-primary", worker_module, None, None),
        ("C5-d-worker-categoryless-primary", worker_module, _item("itm_null_worker", None), TypicalFilterSpec()),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
async def test_C5_empty_status_preserves_no_item_vs_categoryless_item(
    case_id, service_module, item, expected, monkeypatch
):
    task = _task()

    async def load_task_and_item(_ctx):
        return task, item

    async def load_preview_inputs(*_args, **_kwargs):
        return None, None

    monkeypatch.setattr(service_module, "_load_task_and_item", load_task_and_item)
    monkeypatch.setattr(service_module, "_load_preview_inputs", load_preview_inputs)
    monkeypatch.setattr(
        service_module,
        "resolve_item_economics_status",
        lambda *_args: EconomicsStatusEnum.NOT_EVALUATED,
    )
    session_values = [None] if item is None else [None, None]

    if service_module is manager_module:
        status = await manager_module.get_task_budget_status(_ctx(_ScalarSession(session_values)))
    else:
        status = await worker_module.get_task_budget_status_worker(_ctx(_ScalarSession(session_values)))

    assert status.typical_filter_spec is expected if expected is None else status.typical_filter_spec == expected


@pytest.mark.integration
async def test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical(db_session):
    from tests.integration.services.queries.item_economics.test_live_clock_goldens import (
        GOLDEN_DIR,
        _payloads,
        _seed_golden_fixture,
    )

    fixture = await _seed_golden_fixture(db_session)
    payloads = await _payloads(db_session, fixture)
    for name, payload in payloads.items():
        actual = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        assert actual == (GOLDEN_DIR / f"golden_{name}.json").read_text().strip()


@pytest.mark.integration
async def test_CN1a_primary_index_is_partial_and_two_legal_shapes_are_valid(db_session):
    workspace = Workspace(client_id="ws_primary_guard", name="Primary guard")
    task = Task(
        client_id="tsk_primary_guard",
        workspace_id=workspace.client_id,
        task_scalar_id=501,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
    )
    items = [
        Item(client_id=f"itm_primary_guard_{index}", workspace_id=workspace.client_id)
        for index in range(1, 6)
    ]
    db_session.add(workspace)
    await db_session.flush()
    db_session.add(task)
    db_session.add_all(items)
    await db_session.flush()

    db_session.add(
        TaskItem(
            client_id="tim_primary_guard_first",
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            item_id=items[0].client_id,
            role=TaskItemRoleEnum.PRIMARY,
        )
    )
    await db_session.flush()
    # Legal shape 1: a distinct active RELATED item.
    db_session.add(
        TaskItem(
            client_id="tim_primary_guard_related",
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            item_id=items[1].client_id,
            role=TaskItemRoleEnum.RELATED,
        )
    )
    # Legal shape 2: distinct removed PRIMARY items remain exempt from both indexes.
    db_session.add_all(
        [
            TaskItem(
                client_id="tim_primary_guard_removed_a",
                workspace_id=workspace.client_id,
                task_id=task.client_id,
                item_id=items[2].client_id,
                role=TaskItemRoleEnum.PRIMARY,
                removed_at=datetime.now(timezone.utc),
            ),
            TaskItem(
                client_id="tim_primary_guard_removed_b",
                workspace_id=workspace.client_id,
                task_id=task.client_id,
                item_id=items[3].client_id,
                role=TaskItemRoleEnum.PRIMARY,
                removed_at=datetime.now(timezone.utc),
            ),
        ]
    )
    await db_session.flush()

    indexdef = await db_session.scalar(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = current_schema() "
            "AND indexname = 'uix_task_items_primary_active'"
        )
    )
    assert "WHERE" in indexdef
    assert "role = 'primary'" in indexdef
    assert "removed_at IS NULL" in indexdef

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                TaskItem(
                    client_id="tim_primary_guard_second",
                    workspace_id=workspace.client_id,
                    task_id=task.client_id,
                    item_id=items[4].client_id,
                    role=TaskItemRoleEnum.PRIMARY,
                )
            )
            await db_session.flush()


@pytest.mark.integration
async def test_CN1b_add_item_to_task_has_the_explicit_primary_conflict_guard(db_session):
    workspace = Workspace(client_id="ws_primary_command_guard", name="Primary command guard")
    task = Task(
        client_id="tsk_primary_command_guard",
        workspace_id=workspace.client_id,
        task_scalar_id=502,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
    )
    first = Item(client_id="itm_primary_command_first", workspace_id=workspace.client_id)
    second = Item(client_id="itm_primary_command_second", workspace_id=workspace.client_id)
    db_session.add(workspace)
    await db_session.flush()
    db_session.add_all([task, first, second])
    await db_session.flush()
    db_session.add(
        TaskItem(
            client_id="tim_primary_command_first",
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            item_id=first.client_id,
            role=TaskItemRoleEnum.PRIMARY,
        )
    )
    await db_session.flush()

    with pytest.raises(ConflictError, match="^Task already has an active primary item\\.$") as caught:
        await add_item_to_task(
            ServiceContext(
                identity={"workspace_id": workspace.client_id, "user_id": "usr_primary_guard"},
                incoming_data={
                    "task_id": task.client_id,
                    "item_id": second.client_id,
                    "role": TaskItemRoleEnum.PRIMARY,
                },
                query_params={},
                session=db_session,
            )
        )
    assert caught.value.message == "Task already has an active primary item."
