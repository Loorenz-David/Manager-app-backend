from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.task_steps.assign_worker_to_step import (
    _assign_worker_to_step_in_session,
    _resolve_worker_for_section,
)
from beyo_manager.services.commands.task_steps.requests import parse_add_task_step_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event

_TERMINAL_STATES = frozenset({
    TaskStateEnum.RESOLVED,
    TaskStateEnum.FAILED,
    TaskStateEnum.CANCELLED,
})


async def add_task_step(ctx: ServiceContext) -> dict:
    request = parse_add_task_step_request(ctx.incoming_data)

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "tsp")

    async with maybe_begin(ctx.session):
        step_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(TaskStep, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            step_kwargs["client_id"] = request.client_id

        # 1. Fetch task
        task_result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.task_id,
                Task.is_deleted.is_(False),
            )
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")

        # 2. Guard: terminal task cannot receive new steps
        if task.state in _TERMINAL_STATES:
            raise ConflictError("Cannot add a step to a terminal task.")

        # 3. Fetch working section
        section_result = await ctx.session.execute(
            select(WorkingSection).where(
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.client_id == request.working_section_id,
                WorkingSection.is_deleted.is_(False),
            )
        )
        section = section_result.scalar_one_or_none()
        if section is None:
            raise NotFound("Working section not found.")

        now = datetime.now(timezone.utc)

        # 4. Create TaskStep
        step = TaskStep(
            **step_kwargs,
            workspace_id=ctx.workspace_id,
            task_id=request.task_id,
            working_section_id=request.working_section_id,
            working_section_name_snapshot=section.name,
            state=TaskStepStateEnum.PENDING,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            sequence_order=request.sequence_order,
            created_at=now,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(step)
        await ctx.session.flush()  # assigns step.client_id

        # 5. Create initial StepStateRecord (PENDING, open — exited_at=None)
        record = StepStateRecord(
            workspace_id=ctx.workspace_id,
            step_id=step.client_id,
            state=TaskStepStateEnum.PENDING,
            entered_at=now,
            exited_at=None,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(record)
        await ctx.session.flush()  # assigns record.client_id

        # 6. Update circular FK: latest_state_record_id (same transaction)
        step.latest_state_record_id = record.client_id

        # 7. Task state side effect: PENDING → ASSIGNED on first step
        if task.state == TaskStateEnum.PENDING:
            task.state = TaskStateEnum.ASSIGNED
            task.updated_at = now
            task.updated_by_id = ctx.user_id

        # 8. Worker assignment: explicit worker_id takes priority; if omitted and the
        #    section has exactly one active member, auto-assign to them. Multiple members
        #    → leave unassigned so the frontend can prompt.
        resolved_worker_id = await _resolve_worker_for_section(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            working_section_id=request.working_section_id,
            explicit_worker_id=request.worker_id,
        )
        if resolved_worker_id is not None:
            await _assign_worker_to_step_in_session(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                step=step,
                worker_id=resolved_worker_id,
                user_id=ctx.user_id,
                now=now,
            )

    await event_bus.dispatch([
        build_workspace_event(task, "task:updated"),
    ])
    return {"step_id": step.client_id}
