from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, update

from beyo_manager.domain.item_economics.budget_signal import (
    BUDGET_STATES,
    CURRENCY_VOCABULARY,
)
from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.task_steps.enums import (
    TaskStepReadinessStatusEnum,
    TaskStepStateEnum,
)
from beyo_manager.domain.tasks.enums import (
    TaskItemRoleEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.cost_model_version import (
    CostModelVersion,
)
from beyo_manager.models.tables.item_economics.item_cost_evaluation import (
    ItemCostEvaluation,
)
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import (
    ProductionCostBasisVersion,
)
from beyo_manager.models.tables.item_economics.production_cost_group import (
    ProductionCostGroup,
)
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext


UTC = timezone.utc
T = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
NUMERIC_KEYS = (
    "over_seconds",
    "over_cost_minor",
    "projected_over_seconds",
    "projected_over_cost_minor",
    "allowed_seconds",
    "actual_worked_seconds",
    "cost_per_worker_minute_ten_thousandths",
)
ROW_KEYS = {
    "task_id",
    "budget_state",
    "over_seconds",
    "over_cost_minor",
    "projected_over_seconds",
    "projected_over_cost_minor",
    "currency",
    "allowed_seconds",
    "actual_worked_seconds",
    "cost_per_worker_minute_ten_thousandths",
}


def _ctx(db_session, workspace_id: str, task_ids: list[str], *, now: datetime = T):
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": "usr_budget_signals",
            "role_name": "manager",
        },
        incoming_data={},
        query_params={"task_ids": task_ids},
        session=db_session,
        now=now,
    )


async def _get(ctx: ServiceContext) -> dict:
    from beyo_manager.services.queries.item_economics.get_task_budget_signals import (
        get_task_budget_signals,
    )

    return await get_task_budget_signals(ctx)


class CaseData:
    def __init__(self, db_session):
        token = uuid4().hex[:10]
        self.db_session = db_session
        self.token = token
        self.workspace = Workspace(
            client_id=f"ws_sig_{token}", name=f"Budget signals {token}"
        )
        self.foreign_workspace = Workspace(
            client_id=f"ws_sig_foreign_{token}", name=f"Foreign signals {token}"
        )
        self.user = User(
            client_id=f"usr_sig_{token}",
            username=f"budget_signals_{token}",
            email=f"budget_signals_{token}@example.test",
            password="secret",
        )
        self.section_a = WorkingSection(
            client_id=f"wsec_sig_a_{token}",
            workspace_id=self.workspace.client_id,
            name="A",
            order_list=1,
        )
        self.section_b = WorkingSection(
            client_id=f"wsec_sig_b_{token}",
            workspace_id=self.workspace.client_id,
            name="B",
            order_list=2,
        )
        self.group = ProductionCostGroup(
            client_id=f"pcg_sig_{token}",
            workspace_id=self.workspace.client_id,
            name=f"signal group {token}",
            major_category="wood",
            created_by_id=self.user.client_id,
        )
        self.basis = ProductionCostBasisVersion(
            client_id=f"pcbv_sig_{token}",
            workspace_id=self.workspace.client_id,
            production_cost_group_id=self.group.client_id,
            fixed_monthly_cost_minor=1,
            currency=ItemCurrencyEnum.SWEDISH_KRONA,
            monthly_paid_hours=Decimal("1.00"),
            planning_utilization_percent=Decimal("1.00"),
            cost_per_worker_minute_minor=Decimal("9.9999"),
            created_by_id=self.user.client_id,
        )
        self.model = CostModelVersion(
            client_id=f"cmv_sig_{token}",
            workspace_id=self.workspace.client_id,
            currency=ItemCurrencyEnum.SWEDISH_KRONA,
            created_by_id=self.user.client_id,
        )
        self.scalar = 1000

    async def seed_base(self) -> None:
        self.db_session.add(self.workspace)
        await self.db_session.flush()
        self.db_session.add(self.user)
        await self.db_session.flush()
        self.db_session.add(self.foreign_workspace)
        await self.db_session.flush()
        self.db_session.add_all(
            [self.section_a, self.section_b, self.group, self.model]
        )
        await self.db_session.flush()
        self.db_session.add(self.basis)
        await self.db_session.flush()

    async def task(
        self,
        label: str,
        *,
        workspace: Workspace | None = None,
        deleted: bool = False,
        with_item: bool = True,
    ) -> Task:
        target_workspace = workspace or self.workspace
        self.scalar += 1
        task = Task(
            client_id=f"tsk_sig_{label}_{self.token}",
            workspace_id=target_workspace.client_id,
            task_scalar_id=self.scalar,
            task_type=TaskTypeEnum.INTERNAL,
            state=TaskStateEnum.ASSIGNED,
            is_deleted=deleted,
            created_by_id=self.user.client_id,
        )
        self.db_session.add(task)
        await self.db_session.flush()
        if with_item and target_workspace is self.workspace:
            item = Item(
                client_id=f"itm_sig_{label}_{self.token}",
                workspace_id=self.workspace.client_id,
                item_major_category_snapshot="wood",
                created_by_id=self.user.client_id,
            )
            self.db_session.add(item)
            await self.db_session.flush()
            self.db_session.add(
                TaskItem(
                    client_id=f"tim_sig_{label}_{self.token}",
                    workspace_id=self.workspace.client_id,
                    task_id=task.client_id,
                    item_id=item.client_id,
                    role=TaskItemRoleEnum.PRIMARY,
                    created_by_id=self.user.client_id,
                )
            )
            await self.db_session.flush()
        return task

    async def item_for(self, task: Task) -> Item:
        item_id = await self.db_session.scalar(
            TaskItem.__table__.select()
            .with_only_columns(TaskItem.item_id)
            .where(TaskItem.task_id == task.client_id)
        )
        assert item_id is not None
        item = await self.db_session.get(Item, item_id)
        assert item is not None
        return item

    async def evaluation(
        self,
        task: Task,
        *,
        allowed: Decimal = Decimal("60.00"),
        rate: Decimal = Decimal("3.7500"),
        currency: ItemCurrencyEnum = ItemCurrencyEnum.SWEDISH_KRONA,
        superseded: bool = False,
        deleted: bool = False,
    ) -> ItemCostEvaluation:
        item = await self.item_for(task)
        evaluation = ItemCostEvaluation(
            client_id=f"ice_sig_{task.client_id}",
            workspace_id=self.workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            kind=ItemCostEvaluationKindEnum.COMMITTED,
            task_type_snapshot=TaskTypeEnum.INTERNAL,
            expected_sale_price_minor=0,
            currency=currency,
            cost_model_version_id=self.model.client_id,
            production_cost_group_id=self.group.client_id,
            production_cost_basis_version_id=self.basis.client_id,
            monthly_paid_hours_snapshot=Decimal("1.00"),
            planning_utilization_percent_snapshot=Decimal("1.00"),
            fixed_monthly_cost_minor_snapshot=1,
            cost_per_worker_minute_minor_snapshot=rate,
            production_budget_minor=0,
            allowed_worker_minutes=allowed,
            calculation_version=1,
            committed_at=T - timedelta(days=2),
            superseded_at=T - timedelta(days=1) if superseded else None,
            is_deleted=deleted,
            created_by_id=self.user.client_id,
        )
        self.db_session.add(evaluation)
        await self.db_session.flush()
        return evaluation

    async def valuation(
        self,
        task: Task,
        *,
        currency: ItemCurrencyEnum = ItemCurrencyEnum.SWEDISH_KRONA,
    ) -> ItemValuation:
        item = await self.item_for(task)
        valuation = ItemValuation(
            client_id=f"ival_sig_{task.client_id}",
            workspace_id=self.workspace.client_id,
            item_id=item.client_id,
            expected_sale_price_minor=100,
            currency=currency,
            created_by_id=self.user.client_id,
        )
        self.db_session.add(valuation)
        await self.db_session.flush()
        return valuation

    async def step(
        self,
        task: Task,
        label: str,
        *,
        section: WorkingSection | None = None,
        state: TaskStepStateEnum = TaskStepStateEnum.PENDING,
        worked: int = 0,
        order: int = 1,
        closed_at: datetime | None = None,
    ) -> TaskStep:
        target_section = section or self.section_a
        step = TaskStep(
            client_id=f"tsp_sig_{label}_{self.token}",
            workspace_id=self.workspace.client_id,
            task_id=task.client_id,
            working_section_id=target_section.client_id,
            state=state,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            sequence_order=order,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=worked,
            closed_at=closed_at,
            created_by_id=self.user.client_id,
        )
        self.db_session.add(step)
        await self.db_session.flush()
        return step

    async def open_record(self, step: TaskStep, *, entered_at: datetime) -> None:
        record = StepStateRecord(
            client_id=f"ssr_sig_{step.client_id}",
            workspace_id=self.workspace.client_id,
            step_id=step.client_id,
            state=TaskStepStateEnum.WORKING,
            entered_at=entered_at,
            created_by_id=self.user.client_id,
            credited_user_id=self.user.client_id,
        )
        self.db_session.add(record)
        await self.db_session.flush()
        step.latest_state_record_id = record.client_id
        await self.db_session.flush()

    async def typicals(self, section: WorkingSection, seconds: int, label: str) -> None:
        for index in range(5):
            task = await self.task(f"hist_{label}_{index}", with_item=False)
            await self.step(
                task,
                f"hist_{label}_{index}",
                section=section,
                state=TaskStepStateEnum.COMPLETED,
                worked=seconds,
                closed_at=T - timedelta(days=1),
            )

    async def cleanup(self) -> None:
        session = self.db_session
        await session.execute(
            update(TaskStep)
            .where(TaskStep.workspace_id == self.workspace.client_id)
            .values(latest_state_record_id=None)
        )
        await session.execute(
            delete(StepStateRecord).where(
                StepStateRecord.workspace_id == self.workspace.client_id
            )
        )
        await session.execute(
            delete(ItemCostEvaluation).where(
                ItemCostEvaluation.workspace_id == self.workspace.client_id
            )
        )
        await session.execute(
            delete(TaskItem).where(TaskItem.workspace_id == self.workspace.client_id)
        )
        await session.execute(
            delete(ItemValuation).where(
                ItemValuation.workspace_id == self.workspace.client_id
            )
        )
        await session.execute(
            delete(TaskStep).where(TaskStep.workspace_id == self.workspace.client_id)
        )
        await session.execute(
            delete(Task).where(Task.workspace_id == self.workspace.client_id)
        )
        await session.execute(
            delete(Task).where(Task.workspace_id == self.foreign_workspace.client_id)
        )
        await session.execute(
            delete(Item).where(Item.workspace_id == self.workspace.client_id)
        )
        await session.execute(
            delete(ProductionCostBasisVersion).where(
                ProductionCostBasisVersion.workspace_id == self.workspace.client_id
            )
        )
        await session.execute(
            delete(CostModelVersion).where(
                CostModelVersion.workspace_id == self.workspace.client_id
            )
        )
        await session.execute(
            delete(ProductionCostGroup).where(
                ProductionCostGroup.workspace_id == self.workspace.client_id
            )
        )
        await session.execute(
            delete(WorkingSection).where(
                WorkingSection.workspace_id == self.workspace.client_id
            )
        )
        await session.execute(delete(User).where(User.client_id == self.user.client_id))
        await session.execute(
            delete(Workspace).where(Workspace.client_id == self.workspace.client_id)
        )
        await session.execute(
            delete(Workspace).where(
                Workspace.client_id == self.foreign_workspace.client_id
            )
        )


@asynccontextmanager
async def _case(db_session):
    data = CaseData(db_session)
    await data.seed_base()
    try:
        yield data
    finally:
        await data.cleanup()


async def _evaluated_task(
    data: CaseData,
    label: str,
    *,
    allowed: Decimal = Decimal("60.00"),
    rate: Decimal = Decimal("3.7500"),
    currency: ItemCurrencyEnum = ItemCurrencyEnum.SWEDISH_KRONA,
    state: TaskStepStateEnum = TaskStepStateEnum.PENDING,
    worked: int = 0,
) -> tuple[Task, ItemCostEvaluation]:
    task = await data.task(label)
    evaluation = await data.evaluation(
        task, allowed=allowed, rate=rate, currency=currency
    )
    await data.step(task, label, state=state, worked=worked)
    return task, evaluation


@pytest.mark.integration
async def test_c1_a_allocator_uses_reconciled_unequal_typicals(db_session):
    async with _case(db_session) as data:
        await data.typicals(data.section_a, 3600, "c1a_a")
        await data.typicals(data.section_b, 1800, "c1a_b")
        task = await data.task("c1a")
        await data.evaluation(task)
        await data.step(
            task,
            "c1a_a",
            section=data.section_a,
            state=TaskStepStateEnum.COMPLETED,
            worked=2400,
        )
        await data.step(task, "c1a_b", section=data.section_b, order=2)
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert (row["projected_over_seconds"], row["budget_state"]) == (
            0,
            "within_budget",
        )


@pytest.mark.integration
async def test_c1_b_query_count_is_constant_for_one_and_three_tasks(db_session):
    async with _case(db_session) as data:
        tasks = []
        for index in range(3):
            task, _ = await _evaluated_task(data, f"c1b_{index}")
            tasks.append(task)
        from beyo_manager.models import database

        engine = database._engine
        assert engine is not None
        statements: list[str] = []

        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine.sync_engine, "before_cursor_execute", record)
        try:
            await _get(_ctx(db_session, data.workspace.client_id, [tasks[0].client_id]))
            one_count = len(statements)
            statements.clear()
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [task.client_id for task in tasks],
                )
            )
            assert len(statements) == one_count
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", record)


@pytest.mark.integration
async def test_c2_a_current_committed_evaluation_is_budget_bearing(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(data, "c2a")
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert row["budget_state"] == "within_budget"
        assert row["budget_state"] != "no_budget"
        assert row["currency"] == "swedish_krona"


@pytest.mark.integration
async def test_c2_b_negative_allowance_is_a_forecast_on_the_service_path(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(data, "c2b", allowed=Decimal("-12.50"))
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert (
            row["budget_state"],
            row["projected_over_seconds"],
            row["over_seconds"],
            row["allowed_seconds"],
            row["cost_per_worker_minute_ten_thousandths"],
        ) == ("projected_over", 750, 0, 0, 37500)


@pytest.mark.integration
async def test_c2_c_missing_evaluation_is_no_budget(db_session):
    async with _case(db_session) as data:
        task = await data.task("c2c")
        await data.valuation(task)
        await data.step(task, "c2c")
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert row["budget_state"] == "no_budget"


@pytest.mark.integration
async def test_c2_d_superseded_evaluation_is_no_budget(db_session):
    async with _case(db_session) as data:
        task = await data.task("c2d")
        await data.evaluation(task, superseded=True)
        await data.step(task, "c2d")
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert row["budget_state"] == "no_budget"


@pytest.mark.integration
async def test_c2_e_deleted_evaluation_is_no_budget(db_session):
    async with _case(db_session) as data:
        task = await data.task("c2e")
        await data.evaluation(task, deleted=True)
        await data.step(task, "c2e")
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert row["budget_state"] == "no_budget"


@pytest.mark.integration
async def test_c3_a_no_budget_row_is_constructed_with_all_zeroes(db_session):
    async with _case(db_session) as data:
        task = await data.task("c3a")
        await data.step(task, "c3a", state=TaskStepStateEnum.WORKING, worked=1200)
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert row == {
            "task_id": task.client_id,
            "budget_state": "no_budget",
            "over_seconds": 0,
            "over_cost_minor": 0,
            "projected_over_seconds": 0,
            "projected_over_cost_minor": 0,
            "currency": "no_currency",
            "allowed_seconds": 0,
            "actual_worked_seconds": 0,
            "cost_per_worker_minute_ten_thousandths": 0,
        }


@pytest.mark.integration
async def test_c3_b_no_budget_currency_ignores_item_valuation(db_session):
    async with _case(db_session) as data:
        task = await data.task("c3b")
        await data.valuation(task)
        await data.step(task, "c3b", state=TaskStepStateEnum.WORKING, worked=1200)
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert row["currency"] == "no_currency"


@pytest.mark.integration
async def test_c3_c_evaluated_currency_is_the_enum_value_string(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(data, "c3c", currency=ItemCurrencyEnum.EURO)
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert row["currency"] == "euro"
        assert type(row["currency"]) is str


@pytest.mark.integration
async def test_c4_a_every_row_has_exactly_the_ten_contract_keys(db_session):
    async with _case(db_session) as data:
        evaluated, _ = await _evaluated_task(data, "c4a_eval")
        unevaluated = await data.task("c4a_none")
        await data.step(unevaluated, "c4a_none")
        rows = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [evaluated.client_id, unevaluated.client_id],
                )
            )
        )["budget_signals"]
        assert len(rows) == 2
        assert all(set(row) == ROW_KEYS for row in rows)


@pytest.mark.integration
async def test_c4_b_row_values_have_closed_types_and_vocabularies(db_session):
    async with _case(db_session) as data:
        evaluated, _ = await _evaluated_task(data, "c4b_eval")
        unevaluated = await data.task("c4b_none")
        await data.step(unevaluated, "c4b_none")
        rows = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [evaluated.client_id, unevaluated.client_id],
                )
            )
        )["budget_signals"]
        assert len(rows) == 2
        for row in rows:
            assert all(type(row[key]) is int and row[key] >= 0 for key in NUMERIC_KEYS)
            assert all(
                type(row[key]) is str for key in ("task_id", "budget_state", "currency")
            )
            assert row["budget_state"] in BUDGET_STATES
            assert row["currency"] in CURRENCY_VOCABULARY


@pytest.mark.integration
async def test_c4_c_envelope_is_exact_and_rows_are_flat(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(data, "c4c")
        result = await _get(
            _ctx(db_session, data.workspace.client_id, [task.client_id])
        )
        assert set(result) == {"budget_signals"}
        assert result["budget_signals"]
        assert not any(
            isinstance(value, (list, dict))
            for row in result["budget_signals"]
            for value in row.values()
        )


@pytest.mark.integration
async def test_c5_a_visibility_omits_deleted_foreign_and_unknown_tasks(db_session):
    async with _case(db_session) as data:
        visible, _ = await _evaluated_task(data, "c5a_visible")
        deleted_task = await data.task("c5a_deleted", deleted=True)
        foreign = await data.task(
            "c5a_foreign", workspace=data.foreign_workspace, with_item=False
        )
        rows = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [
                        visible.client_id,
                        deleted_task.client_id,
                        foreign.client_id,
                        "tsk_invented",
                    ],
                )
            )
        )["budget_signals"]
        assert len(rows) == 1
        assert rows[0]["task_id"] == visible.client_id


@pytest.mark.integration
async def test_c5_b_duplicate_ids_collapse_to_one_row(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(data, "c5b")
        rows = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id] * 3))
        )["budget_signals"]
        assert len(rows) == 1


@pytest.mark.integration
async def test_c5_c_fifty_raw_ids_are_accepted(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(data, "c5c")
        rows = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [f"tsk_invented_{index}" for index in range(49)] + [task.client_id],
                )
            )
        )["budget_signals"]
        assert len(rows) == 1


@pytest.mark.integration
async def test_c5_d_fifty_one_ids_raise_before_any_statement(db_session):
    async with _case(db_session) as data:
        from beyo_manager.models import database

        engine = database._engine
        assert engine is not None
        statements: list[str] = []

        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine.sync_engine, "before_cursor_execute", record)
        try:
            with pytest.raises(ValidationError) as caught:
                await _get(
                    _ctx(
                        db_session,
                        data.workspace.client_id,
                        [f"tsk_invented_{index}" for index in range(51)],
                    )
                )
            assert str(caught.value).startswith("BUDGET_SIGNALS_TOO_MANY_TASK_IDS:")
            assert statements == []
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", record)


@pytest.mark.integration
async def test_c5_e_cap_is_applied_before_deduplication(db_session):
    async with _case(db_session) as data:
        with pytest.raises(ValidationError) as caught:
            await _get(
                _ctx(db_session, data.workspace.client_id, ["tsk_repeated"] * 51)
            )
        assert str(caught.value).startswith("BUDGET_SIGNALS_TOO_MANY_TASK_IDS:")


@pytest.mark.integration
async def test_c5_f_unevaluated_visible_task_is_present(db_session):
    async with _case(db_session) as data:
        evaluated, _ = await _evaluated_task(data, "c5f_eval")
        unevaluated = await data.task("c5f_none")
        await data.step(unevaluated, "c5f_none")
        rows = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [evaluated.client_id, unevaluated.client_id],
                )
            )
        )["budget_signals"]
        assert len(rows) == 2
        assert (
            next(row for row in rows if row["task_id"] == unevaluated.client_id)[
                "budget_state"
            ]
            == "no_budget"
        )


@pytest.mark.integration
async def test_c6_a_rows_are_sorted_independently_of_request_order(db_session):
    async with _case(db_session) as data:
        tasks = []
        for label in ("c", "b", "a"):
            task, _ = await _evaluated_task(data, f"c6a_{label}")
            tasks.append(task)
        by_label = {task.client_id.split("_")[-2]: task for task in tasks}
        requested = [by_label["c"], by_label["a"], by_label["b"]]
        ids = [
            row["task_id"]
            for row in (
                await _get(
                    _ctx(
                        db_session,
                        data.workspace.client_id,
                        [task.client_id for task in requested],
                    )
                )
            )["budget_signals"]
        ]
        assert ids == sorted(task.client_id for task in tasks)


@pytest.mark.integration
async def test_c6_b_second_request_order_returns_the_same_sorted_rows(db_session):
    async with _case(db_session) as data:
        tasks = []
        for label in ("c", "b", "a"):
            task, _ = await _evaluated_task(data, f"c6b_{label}")
            tasks.append(task)
        first = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [tasks[1].client_id, tasks[0].client_id, tasks[2].client_id],
                )
            )
        )["budget_signals"]
        second = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [tasks[2].client_id, tasks[1].client_id, tasks[0].client_id],
                )
            )
        )["budget_signals"]
        assert [row["task_id"] for row in first] == [row["task_id"] for row in second]
        assert [row["task_id"] for row in first] == sorted(
            task.client_id for task in tasks
        )


@pytest.mark.integration
async def test_c7_a_fixed_rows_are_equal_across_clock_advance(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(data, "c7a")
        first = (
            await _get(
                _ctx(db_session, data.workspace.client_id, [task.client_id], now=T)
            )
        )["budget_signals"][0]
        second = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [task.client_id],
                    now=T + timedelta(seconds=60),
                )
            )
        )["budget_signals"][0]
        assert first == second


@pytest.mark.integration
async def test_c7_b_open_record_moves_only_live_time_fields(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(data, "c7b", state=TaskStepStateEnum.WORKING)
        step_id = f"tsp_sig_c7b_{data.token}"
        step = await db_session.get(TaskStep, step_id)
        assert step is not None
        await data.open_record(step, entered_at=T - timedelta(seconds=600))
        first = (
            await _get(
                _ctx(db_session, data.workspace.client_id, [task.client_id], now=T)
            )
        )["budget_signals"][0]
        second = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [task.client_id],
                    now=T + timedelta(seconds=60),
                )
            )
        )["budget_signals"][0]
        assert second["actual_worked_seconds"] - first["actual_worked_seconds"] == 60
        for key in (
            "task_id",
            "allowed_seconds",
            "currency",
            "cost_per_worker_minute_ten_thousandths",
        ):
            assert second[key] == first[key]
        assert [first["task_id"]] == [second["task_id"]]


@pytest.mark.integration
async def test_c7_c_over_is_absorbing_and_non_decreasing(db_session):
    async with _case(db_session) as data:
        settled, _ = await _evaluated_task(
            data, "c7c_settled", state=TaskStepStateEnum.COMPLETED, worked=3700
        )
        live, _ = await _evaluated_task(
            data, "c7c_live", state=TaskStepStateEnum.WORKING, worked=3600
        )
        live_step = await db_session.get(TaskStep, f"tsp_sig_c7c_live_{data.token}")
        assert live_step is not None
        await data.open_record(live_step, entered_at=T - timedelta(seconds=600))
        first = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [settled.client_id, live.client_id],
                    now=T,
                )
            )
        )["budget_signals"]
        second = (
            await _get(
                _ctx(
                    db_session,
                    data.workspace.client_id,
                    [settled.client_id, live.client_id],
                    now=T + timedelta(seconds=60),
                )
            )
        )["budget_signals"]
        fixed_first = next(row for row in first if row["task_id"] == settled.client_id)
        fixed_second = next(
            row for row in second if row["task_id"] == settled.client_id
        )
        live_first = next(row for row in first if row["task_id"] == live.client_id)
        live_second = next(row for row in second if row["task_id"] == live.client_id)
        assert (fixed_first["budget_state"], fixed_second["budget_state"]) == (
            "over",
            "over",
        )
        assert (fixed_first["over_seconds"], fixed_second["over_seconds"]) == (100, 100)
        assert live_second["over_seconds"] >= live_first["over_seconds"]


@pytest.mark.integration
async def test_c8_a_half_tie_money_uses_the_shipped_calculator(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(
            data, "c8a", state=TaskStepStateEnum.COMPLETED, worked=3736
        )
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert (
            row["over_seconds"],
            row["over_cost_minor"],
            row["projected_over_seconds"],
            row["projected_over_cost_minor"],
            row["budget_state"],
        ) == (136, 9, 136, 9, "over")


@pytest.mark.integration
async def test_c8_b_second_domain_operand_does_not_round_through_minutes(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(
            data, "c8b", state=TaskStepStateEnum.COMPLETED, worked=3602
        )
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert row["over_seconds"] == 2


@pytest.mark.integration
async def test_c8_c_orm_snapshot_rate_wins_over_live_basis_rate(db_session):
    async with _case(db_session) as data:
        task, evaluation = await _evaluated_task(data, "c8c")
        await db_session.refresh(evaluation)
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert row["cost_per_worker_minute_ten_thousandths"] == 37500
        assert row["cost_per_worker_minute_ten_thousandths"] == int(
            evaluation.cost_per_worker_minute_minor_snapshot.scaleb(4)
        )
        assert Decimal(row["cost_per_worker_minute_ten_thousandths"]) == (
            evaluation.cost_per_worker_minute_minor_snapshot * 10_000
        )


@pytest.mark.integration
async def test_c8_d_nonzero_overrun_can_legitimately_cost_zero(db_session):
    async with _case(db_session) as data:
        task, _ = await _evaluated_task(
            data, "c8d", state=TaskStepStateEnum.COMPLETED, worked=3608
        )
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert (row["over_seconds"], row["over_cost_minor"], row["budget_state"]) == (
            8,
            0,
            "over",
        )


@pytest.mark.integration
async def test_c8_e_money_fields_map_to_distinct_nonzero_operands(db_session):
    async with _case(db_session) as data:
        task = await data.task("c8e")
        await data.evaluation(task, allowed=Decimal("-12.50"))
        await data.step(
            task,
            "c8e_a",
            section=data.section_a,
            state=TaskStepStateEnum.WORKING,
            worked=60,
        )
        await data.step(
            task,
            "c8e_b",
            section=data.section_b,
            state=TaskStepStateEnum.PENDING,
            worked=0,
            order=2,
        )
        row = (
            await _get(_ctx(db_session, data.workspace.client_id, [task.client_id]))
        )["budget_signals"][0]
        assert (
            row["over_seconds"],
            row["over_cost_minor"],
            row["projected_over_seconds"],
            row["projected_over_cost_minor"],
            row["budget_state"],
        ) == (60, 4, 810, 51, "over")
