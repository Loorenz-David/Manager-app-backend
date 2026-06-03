from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.task_steps.readiness import recalculate_readiness


async def _sync_step_dependencies_for_section_in_session(
    session: AsyncSession,
    workspace_id: str,
    dependent_section_id: str,
    added_section_ids: set[str],
    removed_section_ids: set[str],
    user_id: str,
) -> None:
    now = datetime.now(timezone.utc)

    if removed_section_ids:
        await _remove_edges_for_sections(
            session=session,
            workspace_id=workspace_id,
            dependent_section_id=dependent_section_id,
            removed_section_ids=removed_section_ids,
            now=now,
            user_id=user_id,
        )

    if added_section_ids:
        await _add_edges_for_sections(
            session=session,
            workspace_id=workspace_id,
            dependent_section_id=dependent_section_id,
            added_section_ids=added_section_ids,
            user_id=user_id,
        )


async def _remove_edges_for_sections(
    session: AsyncSession,
    workspace_id: str,
    dependent_section_id: str,
    removed_section_ids: set[str],
    now: datetime,
    user_id: str,
) -> None:
    dep_step = aliased(TaskStep)
    prereq_step = aliased(TaskStep)

    rows = (
        await session.execute(
            select(TaskStepDependency, dep_step)
            .join(
                dep_step,
                and_(
                    dep_step.client_id == TaskStepDependency.dependent_step_id,
                    dep_step.workspace_id == workspace_id,
                    dep_step.working_section_id == dependent_section_id,
                    dep_step.is_deleted.is_(False),
                    dep_step.state.notin_(TERMINAL_STEP_STATES),
                ),
            )
            .join(
                prereq_step,
                and_(
                    prereq_step.client_id == TaskStepDependency.prerequisite_step_id,
                    prereq_step.workspace_id == workspace_id,
                    prereq_step.working_section_id.in_(removed_section_ids),
                    prereq_step.is_deleted.is_(False),
                ),
            )
            .where(
                TaskStepDependency.workspace_id == workspace_id,
                TaskStepDependency.removed_at.is_(None),
            )
        )
    ).all()

    for edge, step in rows:
        edge.removed_at = now
        edge.removed_by_id = user_id
        step.total_dependencies = max(step.total_dependencies - 1, 0)
        if step.completed_dependencies > step.total_dependencies:
            step.completed_dependencies = step.total_dependencies
        recalculate_readiness(step)

    await session.flush()


async def _add_edges_for_sections(
    session: AsyncSession,
    workspace_id: str,
    dependent_section_id: str,
    added_section_ids: set[str],
    user_id: str,
) -> None:
    dep_step = aliased(TaskStep)
    prereq_step = aliased(TaskStep)

    pairs = (
        await session.execute(
            select(dep_step, prereq_step)
            .join(
                prereq_step,
                and_(
                    prereq_step.task_id == dep_step.task_id,
                    prereq_step.workspace_id == workspace_id,
                    prereq_step.working_section_id.in_(added_section_ids),
                    prereq_step.is_deleted.is_(False),
                ),
            )
            .where(
                dep_step.workspace_id == workspace_id,
                dep_step.working_section_id == dependent_section_id,
                dep_step.is_deleted.is_(False),
                dep_step.state.notin_(TERMINAL_STEP_STATES),
            )
        )
    ).all()

    if not pairs:
        return

    dep_step_ids = [step.client_id for step, _ in pairs]
    existing_rows = (
        await session.execute(
            select(
                TaskStepDependency.dependent_step_id,
                TaskStepDependency.prerequisite_step_id,
            ).where(
                TaskStepDependency.workspace_id == workspace_id,
                TaskStepDependency.dependent_step_id.in_(dep_step_ids),
                TaskStepDependency.removed_at.is_(None),
            )
        )
    ).all()
    existing_active: set[tuple[str, str]] = {(row[0], row[1]) for row in existing_rows}

    for step, prereq in pairs:
        key = (step.client_id, prereq.client_id)
        if key in existing_active:
            continue

        session.add(
            TaskStepDependency(
                workspace_id=workspace_id,
                dependent_step_id=step.client_id,
                prerequisite_step_id=prereq.client_id,
                created_by_id=user_id,
            )
        )
        existing_active.add(key)

        step.total_dependencies += 1
        if prereq.state == TaskStepStateEnum.COMPLETED:
            step.completed_dependencies += 1
        recalculate_readiness(step)

    await session.flush()