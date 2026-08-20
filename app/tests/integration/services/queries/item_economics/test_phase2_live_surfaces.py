from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import event, select

from beyo_manager.domain.item_economics.serializers import serialize_task_budget_status
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics import get_task_budget_allocations as allocations_module
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

from tests.integration.services.queries.item_economics.test_budget_allocations_query import _seed


UTC = timezone.utc


def _ctx(db_session, workspace_id: str, task_id: str, now: datetime, *, role: str = "manager"):
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr_phase2", "role_name": role},
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
    assert all(
        not any(token in key.lower() for token in ("_minor", "cost", "price", "currency", "money", "valuation"))
        for key in worker_payload["result"]
    )


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
