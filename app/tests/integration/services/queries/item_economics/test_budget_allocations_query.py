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
from beyo_manager.services.commands.task_steps.remove_task_step import remove_task_step


async def _seed(db_session):
    token = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_{token}", name=f"Allocations {token}")
    user = User(client_id=f"usr_{token}", username=f"alloc_{token}", email=f"alloc_{token}@example.com", password="secret")
    section = WorkingSection(client_id=f"wsec_{token}", workspace_id=workspace.client_id, name="Upholstery")
    task = Task(client_id=f"tsk_{token}", workspace_id=workspace.client_id, task_scalar_id=1, task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id)
    no_item_task = Task(client_id=f"tsk_no_item_{token}", workspace_id=workspace.client_id, task_scalar_id=2, task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id)
    item = Item(client_id=f"itm_{token}", workspace_id=workspace.client_id, item_major_category_snapshot="wood", created_by_id=user.client_id)
    task_item = TaskItem(client_id=f"tim_{token}", workspace_id=workspace.client_id, task_id=task.client_id, item_id=item.client_id, role=TaskItemRoleEnum.PRIMARY, created_by_id=user.client_id)
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
    db_session.add_all([section, task, no_item_task, item, group, model])
    await db_session.flush()
    db_session.add_all([task_item, basis])
    await db_session.flush()
    db_session.add(evaluation)
    db_session.add_all([failed, live, deleted])
    await db_session.flush()
    return workspace, user, section, task, no_item_task, item, task_item, group, basis, model, evaluation, [failed, live, deleted]


def _ctx(db_session, workspace_id, task_ids):
    return ServiceContext(identity={"workspace_id": workspace_id, "user_id": "usr", "role_name": "worker"}, incoming_data={}, query_params={"task_ids": task_ids}, session=db_session)


@pytest.mark.integration
async def test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, no_item_task, item, task_item, group, basis, model, evaluation, steps = values
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
    finally:
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_budget_allocation_constant_query_count_for_one_and_three_tasks(db_session):
    values = await _seed(db_session)
    workspace, *_ = values
    statements = []
    from beyo_manager.models import database
    async_engine = database._engine
    assert async_engine is not None

    @event.listens_for(async_engine.sync_engine, "before_cursor_execute")
    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    try:
        one = await get_task_budget_allocations(_ctx(db_session, workspace.client_id, [values[3].client_id]))
        first_count = len(statements)
        statements.clear()
        three = await get_task_budget_allocations(_ctx(db_session, workspace.client_id, [values[3].client_id, values[4].client_id, "tsk_unknown"]))
        assert len(three["budget_allocations"]) == 2
        assert first_count == len(statements)
        assert one["budget_allocations"][0]["status"] == "ok"
        assert next(row for row in three["budget_allocations"] if row["task_id"] == values[4].client_id)["status"] == "not_evaluated"
    finally:
        event.remove(async_engine.sync_engine, "before_cursor_execute", record)
        await _cleanup(db_session, values)


@pytest.mark.integration
async def test_remove_service_maps_a_removed_step_to_deleted_skipped(db_session):
    values = await _seed(db_session)
    workspace, user, section, task, no_item_task, item, task_item, group, basis, model, evaluation, steps = values
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
    workspace, user, section, task, no_item_task, item, task_item, group, basis, model, evaluation, steps = values
    await db_session.execute(delete(TaskStep).where(TaskStep.task_id.in_([task.client_id, no_item_task.client_id])))
    await db_session.execute(delete(ItemCostEvaluation).where(ItemCostEvaluation.client_id == evaluation.client_id))
    await db_session.execute(delete(TaskItem).where(TaskItem.client_id == task_item.client_id))
    await db_session.execute(delete(Task).where(Task.client_id.in_([task.client_id, no_item_task.client_id])))
    await db_session.execute(delete(Item).where(Item.client_id == item.client_id))
    await db_session.execute(delete(ProductionCostBasisVersion).where(ProductionCostBasisVersion.client_id == basis.client_id))
    await db_session.execute(delete(CostModelVersion).where(CostModelVersion.client_id == model.client_id))
    await db_session.execute(delete(ProductionCostGroup).where(ProductionCostGroup.client_id == group.client_id))
    await db_session.execute(delete(WorkingSection).where(WorkingSection.client_id == section.client_id))
    await db_session.execute(delete(User).where(User.client_id == user.client_id))
    await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace.client_id))
