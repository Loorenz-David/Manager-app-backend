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

DIVERGENT_BOUNDARY_CLOSED_AT = datetime(2026, 8, 1, tzinfo=timezone.utc)


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
    return values, (section.client_id, second_section.client_id), category.client_id, category.name


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


async def seed_divergent_category_task(db_session):
    """Seed the non-uniform narrowed/section-wide populations required by C5/C8."""

    values = await _seed(db_session)
    workspace, user, section, narrowed_task, plain_task, item, *_ = values
    token = uuid4().hex[:10]
    category = ItemCategory(
        client_id=f"itc_divergent_chair_{token}",
        workspace_id=workspace.client_id,
        name=f"Divergent chair {token}",
        major_category=ItemMajorCategoryEnum.SEAT,
        created_by_id=user.client_id,
    )
    for base_step in values[11]:
        base_step.is_deleted = True
    db_session.add(category)
    await db_session.flush()
    item.item_category_id = category.client_id
    await db_session.flush()
    excluded_section = WorkingSection(
        client_id=f"wsec_divergent_excluded_{token}",
        workspace_id=workspace.client_id,
        name=f"Excluded divergent {token}",
    )
    db_session.add(excluded_section)
    await db_session.flush()

    for task, suffix in ((narrowed_task, "narrowed"), (plain_task, "plain")):
        db_session.add(
            TaskStep(
                client_id=f"tsp_divergent_target_{suffix}_{token}",
                workspace_id=workspace.client_id,
                task_id=task.client_id,
                working_section_id=section.client_id,
                state=TaskStepStateEnum.PENDING,
                readiness_status=TaskStepReadinessStatusEnum.READY,
                total_dependencies=0,
                completed_dependencies=0,
                total_working_seconds=0,
                created_by_id=user.client_id,
            )
        )

    db_session.add(
        TaskStep(
            client_id=f"tsp_divergent_target_excluded_{token}",
            workspace_id=workspace.client_id,
            task_id=narrowed_task.client_id,
            working_section_id=excluded_section.client_id,
            state=TaskStepStateEnum.SKIPPED,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=0,
            created_by_id=user.client_id,
        )
    )

    populations = (
        ("chair", (500, 550, 600, 650, 700)),
        ("other", (100, 150, 200, 250, 300, 350, 400)),
    )
    for population, values_for_population in populations:
        for history_index, seconds in enumerate(values_for_population):
            history_task = Task(
                client_id=f"tsk_divergent_history_{population}_{token}_{history_index}",
                workspace_id=workspace.client_id,
                task_scalar_id=9000 + (0 if population == "chair" else 100) + history_index,
                task_type=TaskTypeEnum.INTERNAL,
                state=TaskStateEnum.ASSIGNED,
                created_by_id=user.client_id,
            )
            history_item = Item(
                client_id=f"itm_divergent_history_{population}_{token}_{history_index}",
                workspace_id=workspace.client_id,
                item_category_id=(category.client_id if population == "chair" else None),
                state=ItemStateEnum.READY,
                created_by_id=user.client_id,
            )
            history_task_item = TaskItem(
                client_id=f"tim_divergent_history_{population}_{token}_{history_index}",
                workspace_id=workspace.client_id,
                task_id=history_task.client_id,
                item_id=history_item.client_id,
                role=TaskItemRoleEnum.PRIMARY,
                created_by_id=user.client_id,
            )
            history_step = TaskStep(
                client_id=f"tsp_divergent_history_{population}_{token}_{history_index}",
                workspace_id=workspace.client_id,
                task_id=history_task.client_id,
                working_section_id=section.client_id,
                state=TaskStepStateEnum.COMPLETED,
                readiness_status=TaskStepReadinessStatusEnum.READY,
                total_dependencies=0,
                completed_dependencies=0,
                total_working_seconds=seconds,
                closed_at=DIVERGENT_BOUNDARY_CLOSED_AT,
                created_by_id=user.client_id,
            )
            db_session.add_all([history_task, history_item, history_task_item, history_step])

    await db_session.flush()
    return {
        "base_values": values,
        "workspace": workspace,
        "user": user,
        "section": section,
        "narrowed_task": narrowed_task,
        "plain_task": plain_task,
        "category_id": category.client_id,
        "category": category,
        "excluded_section": excluded_section,
    }


async def cleanup_divergent_category_fixture(db_session, fixture):
    values = fixture["base_values"]
    workspace_id = fixture["workspace"].client_id
    await db_session.execute(delete(TaskStep).where(TaskStep.workspace_id == workspace_id))
    await db_session.execute(delete(ItemCostEvaluation).where(ItemCostEvaluation.workspace_id == workspace_id))
    await db_session.execute(delete(ItemValuation).where(ItemValuation.workspace_id == workspace_id))
    await db_session.execute(delete(TaskItem).where(TaskItem.workspace_id == workspace_id))
    await db_session.execute(delete(Item).where(Item.workspace_id == workspace_id))
    await db_session.execute(delete(Task).where(Task.workspace_id == workspace_id))
    await db_session.execute(delete(ItemCategory).where(ItemCategory.workspace_id == workspace_id))
    await _cleanup(db_session, values)


async def seed_layer2_visibility_fixture(db_session, *, zero_section: bool):
    """Seed real task surfaces for below-floor and reachable-zero disclosure rows."""

    values = await _seed(db_session)
    workspace, user, section, task, *_ = values
    token = uuid4().hex[:10]
    second_section = WorkingSection(
        client_id=f"wsec_layer2_{token}", workspace_id=workspace.client_id, name="Layer 2 second"
    )
    db_session.add(second_section)
    for base_step in values[11]:
        base_step.is_deleted = True
    await db_session.flush()

    db_session.add_all([
        TaskStep(
            client_id=f"tsp_layer2_target_{token}_{index}", workspace_id=workspace.client_id,
            task_id=task.client_id, working_section_id=section_id,
            state=TaskStepStateEnum.PENDING, readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0, completed_dependencies=0, total_working_seconds=0,
            created_by_id=user.client_id,
        )
        for index, section_id in enumerate((section.client_id, second_section.client_id))
    ])
    history_counts = (5, 5) if zero_section else (3, 0)
    for section_index, (section_id, history_count) in enumerate(
        zip((section.client_id, second_section.client_id), history_counts)
    ):
        for history_index in range(history_count):
            history_task = Task(
                client_id=f"tsk_layer2_history_{token}_{section_index}_{history_index}",
                workspace_id=workspace.client_id, task_scalar_id=8000 + section_index * 100 + history_index,
                task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=user.client_id,
            )
            history_step = TaskStep(
                client_id=f"tsp_layer2_history_{token}_{section_index}_{history_index}",
                workspace_id=workspace.client_id, task_id=history_task.client_id,
                working_section_id=section_id, state=TaskStepStateEnum.COMPLETED,
                readiness_status=TaskStepReadinessStatusEnum.READY, total_dependencies=0,
                completed_dependencies=0,
                total_working_seconds=0 if zero_section else 600 + history_index * 60,
                closed_at=datetime.now(timezone.utc) - timedelta(days=1), created_by_id=user.client_id,
            )
            db_session.add_all([history_task, history_step])
    await db_session.flush()
    return values, (section.client_id, second_section.client_id)


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
    base_values, _section_ids, category_id, _category_name = values
    workspace_id = base_values[0].client_id
    await db_session.execute(delete(TaskStep).where(TaskStep.workspace_id == workspace_id))
    await db_session.execute(delete(ItemCostEvaluation).where(ItemCostEvaluation.workspace_id == workspace_id))
    await db_session.execute(delete(TaskItem).where(TaskItem.workspace_id == workspace_id))
    await db_session.execute(delete(ItemValuation).where(ItemValuation.workspace_id == workspace_id))
    await db_session.execute(delete(Item).where(Item.workspace_id == workspace_id))
    await db_session.execute(delete(ItemCategory).where(ItemCategory.client_id == category_id))
    await _cleanup(db_session, base_values)
