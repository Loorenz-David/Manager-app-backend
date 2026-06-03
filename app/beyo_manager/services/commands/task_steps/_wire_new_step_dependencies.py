from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.task_steps.readiness import recalculate_readiness
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.models.tables.working_sections.working_section_dependency import (
    WorkingSectionDependency,
)


def _compute_dependency_edges(
    new_steps: list[TaskStep],
    existing_steps: list[TaskStep],
    section_prereqs: dict[str, set[str]],
) -> tuple[list[tuple[TaskStep, TaskStep]], list[TaskStep]]:
    new_by_section: dict[str, list[TaskStep]] = {}
    for step in new_steps:
        new_by_section.setdefault(step.working_section_id, []).append(step)

    existing_by_section: dict[str, list[TaskStep]] = {}
    for step in existing_steps:
        existing_by_section.setdefault(step.working_section_id, []).append(step)

    edges: list[tuple[TaskStep, TaskStep]] = []

    for step in new_steps:
        for prereq_section_id in section_prereqs.get(step.working_section_id, set()):
            for prereq_step in (
                existing_by_section.get(prereq_section_id, [])
                + new_by_section.get(prereq_section_id, [])
            ):
                edges.append((step, prereq_step))
                step.total_dependencies += 1
                if prereq_step.state == TaskStepStateEnum.COMPLETED:
                    step.completed_dependencies += 1
        recalculate_readiness(step)

    dependent_sections = set(section_prereqs)
    readiness_changed: list[TaskStep] = []
    for step in existing_steps:
        if step.state in TERMINAL_STEP_STATES or step.working_section_id not in dependent_sections:
            continue
        old_readiness = step.readiness_status
        for prereq_section_id in section_prereqs.get(step.working_section_id, set()):
            for new_prereq_step in new_by_section.get(prereq_section_id, []):
                edges.append((step, new_prereq_step))
                step.total_dependencies += 1
        recalculate_readiness(step)
        if step.readiness_status != old_readiness:
            readiness_changed.append(step)

    return edges, readiness_changed


async def wire_batch_steps_into_dependency_graph(
    session: AsyncSession,
    workspace_id: str,
    new_steps: list[TaskStep],
    task_id: str,
    user_id: str,
) -> list[TaskStep]:
    if not new_steps:
        return []

    section_ids = {step.working_section_id for step in new_steps}
    dep_rows = (
        await session.execute(
            select(WorkingSectionDependency).where(
                WorkingSectionDependency.workspace_id == workspace_id,
                or_(
                    WorkingSectionDependency.dependent_section_id.in_(section_ids),
                    WorkingSectionDependency.prerequisite_section_id.in_(section_ids),
                ),
            )
        )
    ).scalars().all()

    if not dep_rows:
        return []

    section_prereqs: dict[str, set[str]] = {}
    section_dependents: dict[str, set[str]] = {}
    for row in dep_rows:
        section_prereqs.setdefault(row.dependent_section_id, set()).add(
            row.prerequisite_section_id
        )
        section_dependents.setdefault(row.prerequisite_section_id, set()).add(
            row.dependent_section_id
        )

    relevant_sections = set(section_prereqs) | set(section_dependents)
    new_step_ids = {step.client_id for step in new_steps}
    existing_steps = (
        await session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == workspace_id,
                TaskStep.task_id == task_id,
                TaskStep.working_section_id.in_(relevant_sections),
                TaskStep.client_id.notin_(new_step_ids),
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()

    edges, readiness_changed = _compute_dependency_edges(
        new_steps=new_steps,
        existing_steps=list(existing_steps),
        section_prereqs=section_prereqs,
    )

    for dependent_step, prerequisite_step in edges:
        session.add(
            TaskStepDependency(
                workspace_id=workspace_id,
                dependent_step_id=dependent_step.client_id,
                prerequisite_step_id=prerequisite_step.client_id,
                created_by_id=user_id,
            )
        )

    await session.flush()
    return readiness_changed
