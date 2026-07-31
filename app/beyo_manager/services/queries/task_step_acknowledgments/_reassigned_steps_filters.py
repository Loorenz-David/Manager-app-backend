from sqlalchemy import and_

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.services.context import ServiceContext


def reassigned_steps_where_clauses(
    ctx: ServiceContext,
    *,
    unacknowledged_only: bool = False,
) -> list:
    """The single definition of a reassigned step this caller should see."""
    clauses = [
        TaskStepAcknowledgment.workspace_id == ctx.workspace_id,
        TaskStepAcknowledgment.worker_id == ctx.user_id,
        TaskStepAcknowledgment.is_deleted.is_(False),
        TaskStep.state.notin_(TERMINAL_STEP_STATES),
    ]
    if unacknowledged_only:
        clauses.append(TaskStepAcknowledgment.acknowledged_at.is_(None))
    return clauses


def reassigned_steps_select_from(stmt, ctx: ServiceContext):
    """Join ack to its live step, task, caller membership, and working section."""
    return (
        stmt.join(
            TaskStep,
            and_(
                TaskStep.client_id == TaskStepAcknowledgment.step_id,
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .join(
            Task,
            and_(
                Task.client_id == TaskStep.task_id,
                Task.workspace_id == ctx.workspace_id,
                Task.is_deleted.is_(False),
            ),
        )
        .join(
            WorkingSectionMembership,
            and_(
                WorkingSectionMembership.working_section_id == TaskStep.working_section_id,
                WorkingSectionMembership.user_id == ctx.user_id,
                WorkingSectionMembership.workspace_id == ctx.workspace_id,
                WorkingSectionMembership.removed_at.is_(None),
            ),
        )
        .join(
            WorkingSection,
            and_(
                WorkingSection.client_id == TaskStep.working_section_id,
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.is_deleted.is_(False),
            ),
        )
    )
