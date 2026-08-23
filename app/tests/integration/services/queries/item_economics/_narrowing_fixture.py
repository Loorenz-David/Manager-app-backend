"""Seed helpers for the phase-4 task-economics contract tests."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from tests.integration.services.queries.item_economics.test_budget_allocations_query import _seed
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum, ItemStateEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from tests.integration.services.queries.item_economics.test_budget_allocations_query import _cleanup


async def seed_narrowing_history(db_session):
    """Reuse the approved economics seed and expose its objects to narrowing cases."""

    values = await _seed(db_session)
    workspace, user, section, _task, *_ = values
    now = datetime.now(timezone.utc)
    for index, seconds in enumerate((600, 900, 1200, 1500, 1800)):
        history_task = Task(
            client_id=f"tsk_narrowing_history_{workspace.client_id}_{index}",
            workspace_id=workspace.client_id,
            task_scalar_id=1000 + index,
            task_type=TaskTypeEnum.INTERNAL,
            state=TaskStateEnum.ASSIGNED,
            created_by_id=user.client_id,
        )
        history_step = TaskStep(
            client_id=f"tsp_narrowing_history_{workspace.client_id}_{index}",
            workspace_id=workspace.client_id,
            task_id=history_task.client_id,
            working_section_id=section.client_id,
            state=TaskStepStateEnum.COMPLETED,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=seconds,
            closed_at=now - timedelta(days=1),
            created_by_id=user.client_id,
        )
        db_session.add_all([history_task, history_step])
    await db_session.flush()
    return values


async def seed_categorized_two_section_task(db_session, *, budgeted: bool):
    """Seed two narrowed sections for C8/C11 with deterministic literals."""

    values = await _seed(db_session)
    workspace, user, section, task, unevaluated_task, item, *_ = values
    target = task if budgeted else unevaluated_task
    target_item = item
    if not budgeted:
        unevaluated_item_id = await db_session.scalar(
            select(TaskItem.item_id).where(TaskItem.task_id == unevaluated_task.client_id)
        )
        target_item = await db_session.scalar(select(Item).where(Item.client_id == unevaluated_item_id))
    token = uuid4().hex[:10]
    second_section = WorkingSection(
        client_id=f"wsec_narrowing_second_{token}", workspace_id=workspace.client_id, name="Finishing"
    )
    category = ItemCategory(
        client_id=f"itc_narrowing_chair_{token}", workspace_id=workspace.client_id,
        name=f"Chair {token}", major_category=ItemMajorCategoryEnum.SEAT, created_by_id=user.client_id,
    )
    db_session.add_all([second_section, category])
    await db_session.flush()
    target_item.item_category_id = category.client_id
    await db_session.flush()

    target_steps = [
        TaskStep(
            client_id=f"tsp_narrowing_target_{token}_{index}", workspace_id=workspace.client_id,
            task_id=target.client_id, working_section_id=section_id,
            state=TaskStepStateEnum.PENDING, readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0, completed_dependencies=0, total_working_seconds=0,
            created_by_id=user.client_id,
        )
        for index, section_id in enumerate((section.client_id, second_section.client_id))
    ]
    db_session.add_all(target_steps)
    await db_session.flush()

    for section_index, section_id in enumerate((section.client_id, second_section.client_id)):
        typical = 540 if section_index == 0 else 600
        for history_index in range(7):
            history_task = Task(
                client_id=f"tsk_narrowing_categorized_{token}_{section_index}_{history_index}",
                workspace_id=workspace.client_id, task_scalar_id=3000 + section_index * 100 + history_index,
                task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id,
            )
            history_item = Item(
                client_id=f"itm_narrowing_categorized_{token}_{section_index}_{history_index}",
                workspace_id=workspace.client_id, item_category_id=category.client_id,
                state=ItemStateEnum.READY, created_by_id=user.client_id,
            )
            history_task_item = TaskItem(
                client_id=f"tim_narrowing_categorized_{token}_{section_index}_{history_index}",
                workspace_id=workspace.client_id, task_id=history_task.client_id,
                item_id=history_item.client_id, role=TaskItemRoleEnum.PRIMARY, created_by_id=user.client_id,
            )
            history_step = TaskStep(
                client_id=f"tsp_narrowing_categorized_{token}_{section_index}_{history_index}",
                workspace_id=workspace.client_id, task_id=history_task.client_id,
                working_section_id=section_id, state=TaskStepStateEnum.COMPLETED,
                readiness_status=TaskStepReadinessStatusEnum.READY, total_dependencies=0,
                completed_dependencies=0, total_working_seconds=typical,
                closed_at=datetime.now(timezone.utc) - timedelta(days=1), created_by_id=user.client_id,
            )
            db_session.add_all([history_task, history_item, history_task_item, history_step])
    await db_session.flush()
    return values, (section.client_id, second_section.client_id), category.client_id


async def seed_batch_dedupe_fixture(db_session):
    """Seed the 50-task C10 discriminator with three distinct populations."""

    token = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_narrowing_batch_{token}", name=f"Batch {token}")
    user = User(
        client_id=f"usr_narrowing_batch_{token}", username=f"batch_{token}",
        email=f"batch_{token}@example.com", password="secret",
    )
    section = WorkingSection(
        client_id=f"wsec_narrowing_batch_{token}", workspace_id=workspace.client_id, name="Batch section"
    )
    db_session.add(workspace)
    await db_session.flush()
    db_session.add(user)
    await db_session.flush()
    db_session.add(section)
    await db_session.flush()

    category_specs = (("chair", 7, 600), ("table", 9, 900), ("stool", 11, 1200))
    categories = {}
    for name, _count, _typical in category_specs:
        category = ItemCategory(
            client_id=f"itc_narrowing_batch_{token}_{name}", workspace_id=workspace.client_id,
            name=f"{name} {token}", major_category=ItemMajorCategoryEnum.SEAT, created_by_id=user.client_id,
        )
        categories[name] = category
        db_session.add(category)
    await db_session.flush()

    for category_index, (name, count, typical) in enumerate(category_specs):
        category = categories[name]
        for history_index in range(count):
            history_task = Task(
                client_id=f"tsk_narrowing_batch_history_{token}_{name}_{history_index}",
                workspace_id=workspace.client_id, task_scalar_id=5000 + category_index * 100 + history_index,
                task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id,
            )
            history_item = Item(
                client_id=f"itm_narrowing_batch_history_{token}_{name}_{history_index}",
                workspace_id=workspace.client_id, item_category_id=category.client_id,
                state=ItemStateEnum.READY, created_by_id=user.client_id,
            )
            history_task_item = TaskItem(
                client_id=f"tim_narrowing_batch_history_{token}_{name}_{history_index}",
                workspace_id=workspace.client_id, task_id=history_task.client_id,
                item_id=history_item.client_id, role=TaskItemRoleEnum.PRIMARY, created_by_id=user.client_id,
            )
            history_step = TaskStep(
                client_id=f"tsp_narrowing_batch_history_{token}_{name}_{history_index}",
                workspace_id=workspace.client_id, task_id=history_task.client_id,
                working_section_id=section.client_id, state=TaskStepStateEnum.COMPLETED,
                readiness_status=TaskStepReadinessStatusEnum.READY, total_dependencies=0,
                completed_dependencies=0, total_working_seconds=typical,
                closed_at=datetime.now(timezone.utc) - timedelta(days=1), created_by_id=user.client_id,
            )
            db_session.add_all([history_task, history_item, history_task_item, history_step])

    tasks = []
    for task_index in range(50):
        category_name = (
            "chair" if task_index < 20 else "table" if task_index < 35 else "stool" if task_index < 45 else None
        )
        task = Task(
            client_id=f"tsk_narrowing_batch_{token}_{task_index}", workspace_id=workspace.client_id,
            task_scalar_id=7000 + task_index, task_type=TaskTypeEnum.INTERNAL,
            state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id,
        )
        item = Item(
            client_id=f"itm_narrowing_batch_{token}_{task_index}", workspace_id=workspace.client_id,
            item_category_id=categories[category_name].client_id if category_name else None,
            state=ItemStateEnum.READY, created_by_id=user.client_id,
        )
        task_item = TaskItem(
            client_id=f"tim_narrowing_batch_{token}_{task_index}", workspace_id=workspace.client_id,
            task_id=task.client_id, item_id=item.client_id, role=TaskItemRoleEnum.PRIMARY,
            created_by_id=user.client_id,
        )
        step = TaskStep(
            client_id=f"tsp_narrowing_batch_{token}_{task_index}", workspace_id=workspace.client_id,
            task_id=task.client_id, working_section_id=section.client_id,
            state=TaskStepStateEnum.PENDING, readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0, completed_dependencies=0, total_working_seconds=0,
            created_by_id=user.client_id,
        )
        tasks.append(task)
        db_session.add_all([task, item, task_item, step])
    await db_session.flush()
    return {
        "workspace": workspace,
        "user": user,
        "section": section,
        "tasks": tasks,
        "category_ids": {name: category.client_id for name, category in categories.items()},
    }


async def cleanup_batch_dedupe_fixture(db_session, fixture):
    workspace_id = fixture["workspace"].client_id
    await db_session.execute(delete(TaskStep).where(TaskStep.workspace_id == workspace_id))
    await db_session.execute(delete(TaskItem).where(TaskItem.workspace_id == workspace_id))
    await db_session.execute(delete(Task).where(Task.workspace_id == workspace_id))
    await db_session.execute(delete(Item).where(Item.workspace_id == workspace_id))
    await db_session.execute(delete(ItemCategory).where(ItemCategory.workspace_id == workspace_id))
    await db_session.execute(delete(WorkingSection).where(WorkingSection.workspace_id == workspace_id))
    await db_session.execute(delete(User).where(User.client_id == fixture["user"].client_id))
    await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace_id))


async def cleanup_categorized_fixture(db_session, values):
    base_values, _section_ids, category_id = values
    workspace_id = base_values[0].client_id
    await db_session.execute(delete(TaskStep).where(TaskStep.workspace_id == workspace_id))
    await db_session.execute(delete(ItemCostEvaluation).where(ItemCostEvaluation.workspace_id == workspace_id))
    await db_session.execute(delete(TaskItem).where(TaskItem.workspace_id == workspace_id))
    await db_session.execute(delete(ItemValuation).where(ItemValuation.workspace_id == workspace_id))
    await db_session.execute(delete(Item).where(Item.workspace_id == workspace_id))
    await db_session.execute(delete(ItemCategory).where(ItemCategory.client_id == category_id))
    await _cleanup(db_session, base_values)
