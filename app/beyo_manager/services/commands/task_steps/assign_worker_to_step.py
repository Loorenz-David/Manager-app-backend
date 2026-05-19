from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_assignment_record import TaskStepAssignmentRecord
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.services.commands.task_steps.requests import parse_assign_worker_to_step_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def _resolve_worker_for_section(
    session: AsyncSession,
    workspace_id: str,
    working_section_id: str,
    explicit_worker_id: str | None,
) -> str | None:
    """Return the worker_id to assign, or None if the step should remain unassigned.

    If explicit_worker_id is provided it is returned as-is. Otherwise the section's
    active memberships are queried: exactly one member → auto-assign; any other count
    → leave unassigned so the frontend can prompt.
    """
    if explicit_worker_id is not None:
        return explicit_worker_id

    members_result = await session.execute(
        select(WorkingSectionMembership.user_id).where(
            WorkingSectionMembership.workspace_id == workspace_id,
            WorkingSectionMembership.working_section_id == working_section_id,
            WorkingSectionMembership.removed_at.is_(None),
        )
    )
    member_ids = members_result.scalars().all()
    return member_ids[0] if len(member_ids) == 1 else None


async def _assign_worker_to_step_in_session(
    session: AsyncSession,
    workspace_id: str,
    step: TaskStep,
    worker_id: str,
    user_id: str,
    now: datetime,
) -> TaskStepAssignmentRecord:
    """Close any active assignment and open a new one. Updates step snapshot fields.

    No transaction management — must be called inside an active maybe_begin block.
    """
    worker_result = await session.execute(
        select(User).where(User.client_id == worker_id)
    )
    worker = worker_result.scalar_one_or_none()
    if worker is None:
        raise NotFound("Worker not found.")

    active_result = await session.execute(
        select(TaskStepAssignmentRecord).where(
            TaskStepAssignmentRecord.workspace_id == workspace_id,
            TaskStepAssignmentRecord.step_id == step.client_id,
            TaskStepAssignmentRecord.removed_at.is_(None),
        )
    )
    active_assignment = active_result.scalar_one_or_none()
    if active_assignment is not None:
        active_assignment.removed_at = now
        active_assignment.removed_by_id = user_id

    new_assignment = TaskStepAssignmentRecord(
        workspace_id=workspace_id,
        step_id=step.client_id,
        assigned_worker_id=worker_id,
        assigned_at=now,
        assigned_by_id=user_id,
    )
    session.add(new_assignment)
    await session.flush()

    step.assigned_worker_id = worker_id
    step.assigned_worker_display_name_snapshot = worker.username
    step.updated_at = now
    step.updated_by_id = user_id

    return new_assignment


async def assign_worker_to_step(ctx: ServiceContext) -> dict:
    request = parse_assign_worker_to_step_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == request.step_id,
                TaskStep.task_id == request.task_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            raise NotFound("Task step not found.")

        now = datetime.now(timezone.utc)
        new_assignment = await _assign_worker_to_step_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            step=step,
            worker_id=request.worker_id,
            user_id=ctx.user_id,
            now=now,
        )

        if request.worker_id != ctx.user_id:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_step_assigned",
                    user_ids=[request.worker_id],
                    title="Step assigned to you",
                    body="You have been assigned to a step on a task.",
                    entity_type="task_step",
                    entity_client_id=step.client_id,
                    exclude_viewing=[],
                )),
            )

    await event_bus.dispatch([
        build_workspace_event(step, "task:step-assigned", extra={"user_id": step.assigned_worker_id}),
    ])
    return {"assignment_id": new_assignment.client_id, "worker_id": step.assigned_worker_id}
