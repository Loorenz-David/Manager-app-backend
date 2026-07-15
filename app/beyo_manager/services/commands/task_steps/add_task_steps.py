from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import load_only

from beyo_manager.domain.task_steps.constants import TERMINAL_TASK_STATES
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.task_steps._wire_new_step_dependencies import (
    wire_batch_steps_into_dependency_graph,
)
from beyo_manager.services.commands.task_steps._notify_section_workers_of_new_steps import (
    enqueue_section_workers_new_steps_notification,
)
from beyo_manager.services.commands.task_steps.assign_worker_to_step import (
    _assign_worker_to_step_in_session,
    _resolve_worker_for_section,
)
from beyo_manager.services.commands.task_steps.requests import parse_add_task_steps_request
from beyo_manager.services.commands.tasks._task_state_transitions import maybe_reopen_task_to_working
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent


async def add_task_steps(ctx: ServiceContext) -> dict:
    request = parse_add_task_steps_request(ctx.incoming_data)
    seen_client_ids: set[str] = set()
    provided_client_ids: list[str] = []
    section_ids = {step_input.working_section_id for step_input in request.steps}

    for step_input in request.steps:
        if step_input.client_id is None:
            continue
        validate_provided_client_id(step_input.client_id, "tsp")
        if step_input.client_id in seen_client_ids:
            raise ConflictError("Duplicate client_id provided in step batch.")
        seen_client_ids.add(step_input.client_id)
        provided_client_ids.append(step_input.client_id)

    readiness_changed: list[TaskStep] = []
    created_steps: list[TaskStep] = []
    task: Task | None = None
    old_task_state: TaskStateEnum | None = None
    task_reopened = False

    async with maybe_begin(ctx.session):
        if provided_client_ids:
            existing_client_ids = (
                await ctx.session.execute(
                    select(TaskStep.client_id).where(
                        TaskStep.workspace_id == ctx.workspace_id,
                        TaskStep.client_id.in_(provided_client_ids),
                    )
                )
            ).scalars().all()
            if existing_client_ids:
                raise ConflictError("Provided client_id is already in use.")

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
        old_task_state = task.state

        if task.state in TERMINAL_TASK_STATES:
            raise ConflictError("Cannot add a step to a terminal task.")

        section_map: dict[str, WorkingSection] = {}
        if section_ids:
            sections = (
                await ctx.session.execute(
                    select(WorkingSection)
                    .options(
                        load_only(
                            WorkingSection.client_id,
                            WorkingSection.name,
                            WorkingSection.allows_batch_working,
                        )
                    )
                    .where(
                        WorkingSection.workspace_id == ctx.workspace_id,
                        WorkingSection.client_id.in_(section_ids),
                        WorkingSection.is_deleted.is_(False),
                    )
                )
            ).scalars().all()
            section_map = {section.client_id: section for section in sections}
            missing_sections = sorted(section_ids - set(section_map))
            if missing_sections:
                raise NotFound(f"Working section {missing_sections[0]!r} not found.")

        now = datetime.now(timezone.utc)

        for step_input in request.steps:
            section = section_map[step_input.working_section_id]

            step = TaskStep(
                **({"client_id": step_input.client_id} if step_input.client_id is not None else {}),
                workspace_id=ctx.workspace_id,
                task_id=request.task_id,
                working_section_id=step_input.working_section_id,
                working_section_name_snapshot=section.name,
                allows_batch_working=section.allows_batch_working,
                state=TaskStepStateEnum.PENDING,
                readiness_status=TaskStepReadinessStatusEnum.READY,
                total_dependencies=0,
                completed_dependencies=0,
                sequence_order=step_input.sequence_order,
                ready_by_at=step_input.ready_by_at if step_input.ready_by_at is not None else task.ready_by_at,
                created_at=now,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(step)
            await ctx.session.flush()

            record = StepStateRecord(
                workspace_id=ctx.workspace_id,
                step_id=step.client_id,
                state=TaskStepStateEnum.PENDING,
                entered_at=now,
                exited_at=None,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(record)
            await ctx.session.flush()

            step.latest_state_record_id = record.client_id

            if task.state == TaskStateEnum.PENDING:
                task.state = TaskStateEnum.ASSIGNED
                task.updated_at = now
                task.updated_by_id = ctx.user_id

            resolved_worker_id = await _resolve_worker_for_section(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                working_section_id=step_input.working_section_id,
                explicit_worker_id=step_input.worker_id,
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

            created_steps.append(step)

        if created_steps:
            task_reopened = maybe_reopen_task_to_working(
                task,
                now=now,
                updated_by_id=ctx.user_id,
            )

        readiness_changed = await wire_batch_steps_into_dependency_graph(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            new_steps=created_steps,
            task_id=request.task_id,
            user_id=ctx.user_id,
        )

        if task_reopened:
            await enqueue_section_workers_new_steps_notification(
                ctx.session,
                workspace_id=ctx.workspace_id,
                task=task,
                working_section_ids={step.working_section_id for step in created_steps},
                working_section_names={
                    section_id: section.name
                    for section_id, section in section_map.items()
                },
                actor_id=ctx.user_id,
            )

    if not created_steps:
        return {"step_ids": []}

    pending_events: list = [
        build_workspace_event(task, "task:updated"),
        BatchWorkspaceEvent(
            event_name="task:step-created",
            workspace_id=ctx.workspace_id,
            items=[
                {
                    "client_id": step.client_id,
                    "working_section_id": step.working_section_id,
                }
                for step in created_steps
            ],
        ),
    ]
    if old_task_state != task.state:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    readiness_items = [
        {
            "client_id": step.client_id,
            "new_readiness": step.readiness_status.value,
        }
        for step in readiness_changed
    ]
    if readiness_items:
        pending_events.append(
            BatchWorkspaceEvent(
                event_name="task:step-readiness-changed",
                workspace_id=ctx.workspace_id,
                items=readiness_items,
            )
        )
    await event_bus.dispatch(pending_events)
    return {"step_ids": [step.client_id for step in created_steps]}
