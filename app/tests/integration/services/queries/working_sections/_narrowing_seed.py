"""Reproducible seed and EXPLAIN helpers for the phase-2 cost matrix."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from beyo_manager.domain.item_economics.typical_filters import TypicalFilterSpec
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum, ItemStateEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.queries.working_sections.get_working_section_typical_times import (
    typical_times_statement,
)


MEASUREMENT_NOW = datetime(2026, 8, 22, tzinfo=timezone.utc)
TYPICAL_PAGE_SIZE = 20
API_CEILING = 50
DISTINCT_CATEGORY_COUNT = 20
STEPS_PER_TASK = 1
HISTORY_SPAN_DAYS = 90


async def seed_narrowing_workspace(
    db_session,
    *,
    task_count: int,
    category_count: int = DISTINCT_CATEGORY_COUNT,
) -> tuple[str, tuple[str, ...]]:
    """Seed one section, one step per task, and one primary category per task."""
    token = uuid4().hex[:12]
    workspace_id = f"ws_measure_{token}"
    user_id = f"usr_measure_{token}"
    section_id = f"wsec_measure_{token}"
    workspace = Workspace(client_id=workspace_id, name=f"Measure {token}")
    user = User(
        client_id=user_id,
        username=f"measure_{token}",
        email=f"measure_{token}@example.com",
        password="secret",
    )
    section = WorkingSection(client_id=section_id, workspace_id=workspace_id, name=f"Measure {token}")
    db_session.add(workspace)
    await db_session.flush()
    db_session.add(user)
    await db_session.flush()
    db_session.add(section)
    await db_session.flush()

    categories: list[ItemCategory] = []
    items: list[Item] = []
    for category_index in range(category_count):
        category = ItemCategory(
            client_id=f"itc_measure_{token}_{category_index}",
            workspace_id=workspace_id,
            name=f"Measure category {token} {category_index}",
            major_category=ItemMajorCategoryEnum.SEAT,
            created_by_id=user_id,
        )
        item = Item(
            client_id=f"itm_measure_{token}_{category_index}",
            workspace_id=workspace_id,
            item_category_id=category.client_id,
            state=ItemStateEnum.READY,
            created_by_id=user_id,
        )
        categories.append(category)
        items.append(item)
    db_session.add_all(categories)
    await db_session.flush()
    db_session.add_all(items)
    await db_session.flush()

    for task_index in range(task_count):
        task_id = f"tsk_measure_{token}_{task_index}"
        task = Task(
            client_id=task_id,
            workspace_id=workspace_id,
            task_scalar_id=task_index + 1,
            task_type=TaskTypeEnum.INTERNAL,
            state=TaskStateEnum.ASSIGNED,
            created_by_id=user_id,
        )
        item = items[task_index % category_count]
        task_item = TaskItem(
            client_id=f"tim_measure_{token}_{task_index}",
            workspace_id=workspace_id,
            task_id=task_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=user_id,
        )
        step = TaskStep(
            client_id=f"tsp_measure_{token}_{task_index}",
            workspace_id=workspace_id,
            task_id=task_id,
            working_section_id=section_id,
            working_section_name_snapshot=section.name,
            state=TaskStepStateEnum.COMPLETED,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0,
            completed_dependencies=0,
            total_working_seconds=100 + task_index,
            closed_at=MEASUREMENT_NOW - timedelta(days=1),
            created_by_id=user_id,
        )
        db_session.add_all([task, task_item, step])
    await db_session.flush()
    return workspace_id, tuple(category.client_id for category in categories)


def specs_for_categories(category_ids: tuple[str, ...], count: int) -> tuple[TypicalFilterSpec, ...]:
    return tuple(
        TypicalFilterSpec(item_category_ids=frozenset({category_ids[index]}))
        for index in range(count)
    )


async def explain_typical_times(db_session, statement) -> dict[str, object]:
    """Run PostgreSQL's measured plan with literals for reproducibility."""
    compiled = statement.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    explain = text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {compiled}")
    payload = (await db_session.execute(explain)).scalar_one()[0]
    plan = payload["Plan"]
    return {
        "planning_ms": payload["Planning Time"],
        "execution_ms": payload["Execution Time"],
        "node_type": plan["Node Type"],
        "startup_cost": plan["Startup Cost"],
        "total_cost": plan["Total Cost"],
    }


async def collect_measurement_matrix(db_session) -> list[dict[str, object]]:
    """Collect the ten matrix cells plus the labelled 50×20 ceiling row."""
    rows: list[dict[str, object]] = []
    cases = [
        ("single task", 1, 0, "current"),
        ("20 tasks × 5 categories", TYPICAL_PAGE_SIZE, 5, "current"),
        ("20 tasks × 10 categories", TYPICAL_PAGE_SIZE, 10, "current"),
        ("20 tasks × 20 categories", TYPICAL_PAGE_SIZE, 20, "current"),
        ("no-spec", TYPICAL_PAGE_SIZE, 0, "current"),
        ("single task", 1, 0, "new"),
        ("20 tasks × 5 categories", TYPICAL_PAGE_SIZE, 5, "new"),
        ("20 tasks × 10 categories", TYPICAL_PAGE_SIZE, 10, "new"),
        ("20 tasks × 20 categories", TYPICAL_PAGE_SIZE, 20, "new"),
        ("no-spec", TYPICAL_PAGE_SIZE, 0, "new"),
        ("50 tasks × 20 categories (API ceiling, not a realistic page)", API_CEILING, 20, "new"),
    ]
    for shape, task_count, spec_count, statement_kind in cases:
        workspace_id, category_ids = await seed_narrowing_workspace(
            db_session,
            task_count=task_count,
            category_count=DISTINCT_CATEGORY_COUNT,
        )
        specs = specs_for_categories(category_ids, spec_count)
        statement = typical_times_statement(
            workspace_id,
            now=MEASUREMENT_NOW,
            specs=specs if statement_kind == "new" else (),
        )
        measured = await explain_typical_times(db_session, statement)
        rows.append(
            {
                "shape": shape,
                "statement": statement_kind,
                "tasks": task_count,
                "steps_per_task": STEPS_PER_TASK,
                "distinct_categories": DISTINCT_CATEGORY_COUNT,
                "history_span_days": HISTORY_SPAN_DAYS,
                "spec_count": spec_count,
                "strategy": "outer spec-index attachment; primary item joins",
                **measured,
            }
        )
    return rows


__all__ = [
    "API_CEILING",
    "DISTINCT_CATEGORY_COUNT",
    "HISTORY_SPAN_DAYS",
    "MEASUREMENT_NOW",
    "STEPS_PER_TASK",
    "TYPICAL_PAGE_SIZE",
    "collect_measurement_matrix",
    "explain_typical_times",
    "seed_narrowing_workspace",
    "specs_for_categories",
]
