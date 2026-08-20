from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, event

from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.item_economics.budget_division import ALLOCATION_METHOD
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_task_budget_allocations import get_task_budget_allocations
from beyo_manager.services.queries.item_economics.get_task_budget_status import get_task_budget_status
from beyo_manager.services.commands.task_steps.remove_task_step import remove_task_step


async def _seed(db_session):
    token = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_{token}", name=f"Allocations {token}")
    foreign_workspace = Workspace(client_id=f"ws_foreign_{token}", name=f"Foreign allocations {token}")
    user = User(client_id=f"usr_{token}", username=f"alloc_{token}", email=f"alloc_{token}@example.com", password="secret")
    section = WorkingSection(client_id=f"wsec_{token}", workspace_id=workspace.client_id, name="Upholstery")
    task = Task(client_id=f"tsk_{token}", workspace_id=workspace.client_id, task_scalar_id=1, task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id)
    unevaluated_task = Task(client_id=f"tsk_unevaluated_{token}", workspace_id=workspace.client_id, task_scalar_id=2, task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id)
    foreign_task = Task(client_id=f"tsk_foreign_{token}", workspace_id=foreign_workspace.client_id, task_scalar_id=1, task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id)
    item = Item(client_id=f"itm_{token}", workspace_id=workspace.client_id, item_major_category_snapshot="wood", created_by_id=user.client_id)
    unevaluated_item = Item(client_id=f"itm_unevaluated_{token}", workspace_id=workspace.client_id, item_major_category_snapshot="wood", created_by_id=user.client_id)
    task_item = TaskItem(client_id=f"tim_{token}", workspace_id=workspace.client_id, task_id=task.client_id, item_id=item.client_id, role=TaskItemRoleEnum.PRIMARY, created_by_id=user.client_id)
    unevaluated_task_item = TaskItem(client_id=f"tim_unevaluated_{token}", workspace_id=workspace.client_id, task_id=unevaluated_task.client_id, item_id=unevaluated_item.client_id, role=TaskItemRoleEnum.PRIMARY, created_by_id=user.client_id)
    unevaluated_valuation = ItemValuation(
        client_id=f"ival_unevaluated_{token}", workspace_id=workspace.client_id, item_id=unevaluated_item.client_id,
        expected_sale_price_minor=0, currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id,
    )
    group = ProductionCostGroup(client_id=f"pcg_{token}", workspace_id=workspace.client_id, name=f"group {token}", major_category="wood", created_by_id=user.client_id)
    basis = ProductionCostBasisVersion(client_id=f"pcbv_{token}", workspace_id=workspace.client_id, production_cost_group_id=group.client_id, fixed_monthly_cost_minor=1, currency=ItemCurrencyEnum.SWEDISH_KRONA, monthly_paid_hours=Decimal("1.00"), planning_utilization_percent=Decimal("1.00"), cost_per_worker_minute_minor=Decimal("0.0001"), created_by_id=user.client_id)
    model = CostModelVersion(client_id=f"cmv_{token}", workspace_id=workspace.client_id, currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id)
    evaluation = ItemCostEvaluation(
        client_id=f"ice_{token}", workspace_id=workspace.client_id, task_id=task.client_id, item_id=item.client_id,
        kind=ItemCostEvaluationKindEnum.COMMITTED, task_type_snapshot=TaskTypeEnum.INTERNAL,
        expected_sale_price_minor=0, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        cost_model_version_id=model.client_id, production_cost_group_id=group.client_id,
        production_cost_basis_version_id=basis.client_id, monthly_paid_hours_snapshot=Decimal("1.00"),
        planning_utilization_percent_snapshot=Decimal("1.00"), fixed_monthly_cost_minor_snapshot=1,
        cost_per_worker_minute_minor_snapshot=Decimal("0.0001"), production_budget_minor=0,
        allowed_worker_minutes=Decimal("100.00"), calculation_version=1, created_by_id=user.client_id,
    )
    failed = TaskStep(client_id=f"tsp_failed_{token}", workspace_id=workspace.client_id, task_id=task.client_id, working_section_id=section.client_id, state=TaskStepStateEnum.FAILED, readiness_status=TaskStepReadinessStatusEnum.READY, total_dependencies=0, completed_dependencies=0, total_working_seconds=1200, created_by_id=user.client_id)
    live = TaskStep(client_id=f"tsp_live_{token}", workspace_id=workspace.client_id, task_id=task.client_id, working_section_id=section.client_id, state=TaskStepStateEnum.PENDING, readiness_status=TaskStepReadinessStatusEnum.READY, total_dependencies=0, completed_dependencies=0, total_working_seconds=0, created_by_id=user.client_id)
    deleted = TaskStep(client_id=f"tsp_deleted_{token}", workspace_id=workspace.client_id, task_id=task.client_id, working_section_id=section.client_id, state=TaskStepStateEnum.SKIPPED, readiness_status=TaskStepReadinessStatusEnum.READY, total_dependencies=0, completed_dependencies=0, total_working_seconds=1200, is_deleted=True, created_by_id=user.client_id)
    db_session.add(workspace)
    await db_session.flush()
    db_session.add(user)
    await db_session.flush()
    db_session.add(foreign_workspace)
    await db_session.flush()
    db_session.add_all([section, task, unevaluated_task, foreign_task, item, unevaluated_item, group, model])
    await db_session.flush()
    db_session.add_all([task_item, unevaluated_task_item, unevaluated_valuation, basis])
    await db_session.flush()
    db_session.add(evaluation)
    db_session.add_all([failed, live, deleted])
    await db_session.flush()
    return workspace, user, section, task, unevaluated_task, item, task_item, group, basis, model, evaluation, [failed, live, deleted], foreign_task, foreign_workspace


def _ctx(db_session, workspace_id, task_ids):
    return ServiceContext(identity={"workspace_id": workspace_id, "user_id": "usr", "role_name": "worker"}, incoming_data={}, query_params={"task_ids": task_ids}, session=db_session)


async def _seed_two_section_allocation(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, *_ = values
    token = uuid4().hex[:10]
    second_section = WorkingSection(
        client_id=f"wsec_second_{token}", workspace_id=workspace.client_id, name="Finishing"
    )
    db_session.add(second_section)
    await db_session.flush()
    for section_index, (section_for_groups, group_values) in enumerate((
        (section, [1000, 2000, 3600, 5000, 6000]),
        (second_section, [600, 1200, 1800, 2400, 3000]),
    )):
        for index, seconds in enumerate(group_values):
            historical_task = Task(
                client_id=f"tsk_typical_{token}_{section_for_groups.client_id}_{index}",
                workspace_id=workspace.client_id,
                task_scalar_id=100 + section_index * 10 + index,
                task_type=TaskTypeEnum.INTERNAL,
                state=TaskStateEnum.ASSIGNED,
                created_by_id=user.client_id,
            )
            historical_step = TaskStep(
                client_id=f"tsp_typical_{token}_{section_for_groups.client_id}_{index}",
                workspace_id=workspace.client_id,
                task_id=historical_task.client_id,
                working_section_id=section_for_groups.client_id,
                state=TaskStepStateEnum.COMPLETED,
                readiness_status=TaskStepReadinessStatusEnum.READY,
                total_dependencies=0,
                completed_dependencies=0,
                total_working_seconds=seconds,
                closed_at=datetime.now(timezone.utc) - timedelta(days=1),
                created_by_id=user.client_id,
            )
            db_session.add_all([historical_task, historical_step])
    db_session.add(
        TaskStep(
            client_id=f"tsp_second_live_{token}", workspace_id=workspace.client_id,
            task_id=task.client_id, working_section_id=second_section.client_id,
            state=TaskStepStateEnum.PENDING, readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0, completed_dependencies=0, total_working_seconds=0,
            created_by_id=user.client_id,
        )
    )
    await db_session.flush()
    return values


@pytest.mark.integration
async def test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, unevaluated_task, item, task_item, group, basis, model, evaluation, steps, _foreign_task, _foreign_workspace = values
    try:
        result = await get_task_budget_allocations(_ctx(db_session, workspace.client_id, [task.client_id]))
        row = result["budget_allocations"][0]
        assert row["allocation_method"] == ALLOCATION_METHOD
        assert row["actual_worker_seconds"] == 1200
        assert {step["step_id"] for step in row["steps"]} == {steps[0].client_id, steps[1].client_id}
        failed = next(step for step in row["steps"] if step["step_id"] == steps[0].client_id)
        live = next(step for step in row["steps"] if step["step_id"] == steps[1].client_id)
        assert failed["share_state"] == "excluded"
        assert failed["allowance_seconds"] is None
        assert live["allowance_seconds"] == 4800
        status = await get_task_budget_status(
            ServiceContext(
                identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "worker"},
                incoming_data={"task_client_id": task.client_id}, query_params={}, session=db_session,
            )
        )
        assert row["actual_worker_seconds"] == status.actual_worker_seconds
    finally:
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_budget_allocation_uses_shared_typicals_for_section_proportional_split(db_session):
    values = await _seed_two_section_allocation(db_session)
    workspace, _user, section, task, *_ = values
    try:
        result = await get_task_budget_allocations(_ctx(db_session, workspace.client_id, [task.client_id]))
        row = result["budget_allocations"][0]
        steps = [step for step in row["steps"] if step["share_state"] != "excluded"]
        assert next(step for step in steps if step["working_section_id"] == section.client_id)["typical_worker_seconds"] == 3600
        second_section_id = next(step["working_section_id"] for step in steps if step["working_section_id"] != section.client_id)
        allowances_by_section = {}
        for step in steps:
            allowances_by_section[step["working_section_id"]] = allowances_by_section.get(step["working_section_id"], 0) + step["allowance_seconds"]
        # §12.6 P1: the proportional invariant is defined at the section unit.
        assert allowances_by_section[section.client_id] == 2 * allowances_by_section[second_section_id]
    finally:
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_budget_allocation_constant_query_count_for_one_and_three_tasks(db_session):
    values = await _seed(db_session)
    workspace, _user, _section, task, unevaluated_task, *_rest, foreign_task, _foreign_workspace = values
    statements = []
    from beyo_manager.models import database
    async_engine = database._engine
    assert async_engine is not None

    @event.listens_for(async_engine.sync_engine, "before_cursor_execute")
    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    try:
        one = await get_task_budget_allocations(_ctx(db_session, workspace.client_id, [values[4].client_id]))
        first_count = len(statements)
        statements.clear()
        three = await get_task_budget_allocations(_ctx(db_session, workspace.client_id, [task.client_id, unevaluated_task.client_id, "tsk_unknown", foreign_task.client_id]))
        assert len(three["budget_allocations"]) == 2
        assert foreign_task.client_id not in {row["task_id"] for row in three["budget_allocations"]}
        # A populated batch now performs the single shared live-worked-seconds
        # probe; the empty-step request legitimately returns before that probe.
        assert len(statements) == first_count + 1
        assert first_count == 11
        assert one["budget_allocations"][0]["status"] == "not_configured_no_cost_group"
        assert next(row for row in three["budget_allocations"] if row["task_id"] == values[3].client_id)["status"] == "ok"
        assert next(row for row in three["budget_allocations"] if row["task_id"] == values[4].client_id)["status"] == "not_configured_no_cost_group"
    finally:
        event.remove(async_engine.sync_engine, "before_cursor_execute", record)
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_remove_service_maps_a_removed_step_to_deleted_skipped(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, unevaluated_task, item, task_item, group, basis, model, evaluation, steps, _foreign_task, _foreign_workspace = values
    try:
        await remove_task_step(
            ServiceContext(
                identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "manager"},
                incoming_data={"task_id": task.client_id, "step_id": steps[1].client_id},
                query_params={}, session=db_session,
            )
        )
        await db_session.refresh(steps[1])
        assert steps[1].state is TaskStepStateEnum.SKIPPED
        assert steps[1].is_deleted is True
    finally:
        await _cleanup(db_session, values)


async def _cleanup(db_session, values):
    workspace, user, section, task, unevaluated_task, item, task_item, group, basis, model, evaluation, steps, foreign_task, foreign_workspace = values
    await db_session.execute(delete(TaskStep).where(TaskStep.workspace_id == workspace.client_id))
    await db_session.execute(delete(ItemCostEvaluation).where(ItemCostEvaluation.client_id == evaluation.client_id))
    await db_session.execute(delete(TaskItem).where(TaskItem.workspace_id == workspace.client_id))
    await db_session.execute(delete(ItemValuation).where(ItemValuation.workspace_id == workspace.client_id))
    await db_session.execute(delete(Task).where(Task.workspace_id == workspace.client_id))
    await db_session.execute(delete(Task).where(Task.client_id == foreign_task.client_id))
    await db_session.execute(delete(Item).where(Item.workspace_id == workspace.client_id))
    await db_session.execute(delete(ProductionCostBasisVersion).where(ProductionCostBasisVersion.client_id == basis.client_id))
    await db_session.execute(delete(CostModelVersion).where(CostModelVersion.client_id == model.client_id))
    await db_session.execute(delete(ProductionCostGroup).where(ProductionCostGroup.client_id == group.client_id))
    await db_session.execute(delete(WorkingSection).where(WorkingSection.workspace_id == workspace.client_id))
    await db_session.execute(delete(User).where(User.client_id == user.client_id))
    await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace.client_id))
    await db_session.execute(delete(Workspace).where(Workspace.client_id == foreign_workspace.client_id))
