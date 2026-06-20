"""Worker handler for deferred step completion finalization."""

import logging
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES, TERMINAL_TASK_STATES
from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.task_steps.notification_targets import resolve_task_step_notification_targets
from beyo_manager.domain.task_steps.readiness import recalculate_readiness
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task

logger = logging.getLogger(__name__)

async def handle_finalize_pending_step_completion(payload: dict, task_client_id: str) -> None:
    step_id = payload["step_id"]
    task_id = payload["task_id"]
    workspace_id = payload["workspace_id"]
    performed_by = payload["performed_by_user_id"]
    credited_user_id = payload["credited_user_id"]
    reason_raw = payload.get("reason")
    description = payload.get("description")
    reason = StepEventReasonEnum(reason_raw) if reason_raw else None

    try:
        completion_requested_at = datetime.fromisoformat(payload["completion_requested_at"])
    except ValueError:
        logger.warning(
            "finalize_pending_step_completion | invalid_completion_requested_at | task_id=%s",
            task_client_id,
        )
        return

    now = datetime.now(timezone.utc)

    readiness_changes: list[tuple[TaskStep, object]] = []
    old_task_state: TaskStateEnum | None = None
    pending_events: list = []

    async for session in get_db_session():
        async with session.begin():
            step_result = await session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == workspace_id,
                    TaskStep.client_id == step_id,
                    TaskStep.task_id == task_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
            step = step_result.scalar_one_or_none()
            if step is None:
                logger.warning(
                    "finalize_pending_step_completion | step_not_found | step_id=%s",
                    step_id,
                )
                return
            if step.state != TaskStepStateEnum.WORKING:
                logger.info(
                    "finalize_pending_step_completion | skipped | step_id=%s current_state=%s",
                    step_id,
                    step.state.value,
                )
                return

            task_result = await session.execute(
                select(Task).where(
                    Task.workspace_id == workspace_id,
                    Task.client_id == task_id,
                    Task.is_deleted.is_(False),
                )
            )
            task = task_result.scalar_one_or_none()
            if task is None:
                logger.warning(
                    "finalize_pending_step_completion | task_not_found | task_id=%s",
                    task_id,
                )
                return
            old_task_state = task.state

            open_record_result = await session.execute(
                select(StepStateRecord).where(
                    StepStateRecord.workspace_id == workspace_id,
                    StepStateRecord.step_id == step.client_id,
                    StepStateRecord.exited_at.is_(None),
                )
            )
            closing_record = open_record_result.scalar_one_or_none()
            if closing_record is None:
                logger.warning(
                    "finalize_pending_step_completion | no_open_record | step_id=%s",
                    step_id,
                )
                return
            closing_state = closing_record.state
            closing_entered_at = closing_record.entered_at
            closing_record.exited_at = completion_requested_at

            new_record = StepStateRecord(
                workspace_id=workspace_id,
                step_id=step.client_id,
                state=TaskStepStateEnum.COMPLETED,
                reason=reason,
                description=description,
                entered_at=completion_requested_at,
                exited_at=None,
                created_by_id=performed_by,
            )
            session.add(new_record)
            await session.flush()

            step.state = TaskStepStateEnum.COMPLETED
            step.latest_state_record_id = new_record.client_id
            step.closed_at = completion_requested_at
            step.updated_at = now
            step.updated_by_id = performed_by

            dependent_edges_result = await session.execute(
                select(TaskStepDependency).where(
                    TaskStepDependency.workspace_id == workspace_id,
                    TaskStepDependency.prerequisite_step_id == step.client_id,
                    TaskStepDependency.removed_at.is_(None),
                )
            )
            for edge in dependent_edges_result.scalars().all():
                dep_step_result = await session.execute(
                    select(TaskStep).where(
                        TaskStep.workspace_id == workspace_id,
                        TaskStep.client_id == edge.dependent_step_id,
                        TaskStep.is_deleted.is_(False),
                    )
                )
                dep_step = dep_step_result.scalar_one_or_none()
                if dep_step is not None:
                    old_dep_readiness = dep_step.readiness_status
                    dep_step.completed_dependencies += 1
                    recalculate_readiness(dep_step)
                    readiness_changes.append((dep_step, old_dep_readiness))

            all_steps_result = await session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == workspace_id,
                    TaskStep.task_id == task.client_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
            all_steps = all_steps_result.scalars().all()
            if all_steps and all(s.state in TERMINAL_STEP_STATES for s in all_steps):
                if task.state not in TERMINAL_TASK_STATES:
                    task.state = TaskStateEnum.READY
                    task.updated_at = now
                    task.updated_by_id = performed_by

            analytics_payload = StepTransitionPayload(
                step_id=step.client_id,
                task_id=task.client_id,
                workspace_id=workspace_id,
                closing_record_id=closing_record.client_id,
                closing_state=closing_state.value,
                new_state=TaskStepStateEnum.COMPLETED.value,
                performed_by_user_id=performed_by,
                credited_user_id=credited_user_id,
                assigned_worker_id=step.assigned_worker_id,
                working_section_id=step.working_section_id,
                working_section_name_snapshot=step.working_section_name_snapshot,
                entered_at=closing_entered_at.isoformat(),
                exited_at=completion_requested_at.isoformat(),
                step_task_id=task.client_id,
            )
            await create_instant_task(
                session=session,
                task_type=TaskType.PROCESS_STEP_TRANSITION,
                payload=asdict(analytics_payload),
            )

            step_pin_user_ids = list(
                await resolve_task_step_notification_targets(
                    session,
                    step.client_id,
                    performed_by,
                    {"state": TaskStepStateEnum.COMPLETED.value},
                )
            )
            if step_pin_user_ids:
                await create_instant_task(
                    session=session,
                    task_type=TaskType.CREATE_NOTIFICATIONS,
                    payload=asdict(
                        NotificationPayload(
                            notification_type="task_step_state_changed",
                            user_ids=step_pin_user_ids,
                            title="Step state changed",
                            body="A step you are following has changed state.",
                            entity_type="task_step",
                            entity_client_id=step.client_id,
                            exclude_viewing=[
                                {"entity_type": "task_step", "entity_client_id": step.client_id}
                            ],
                        )
                    ),
                )

            # TODO: call _dispatch_section_side_effects(step, COMPLETED, session) here when
            # that extension point is implemented. Mirror transition_step_state.py step 8 —
            # section side effects must fire for deferred completions too.

            pending_events.append(
                build_workspace_event(
                    step,
                    "task:step-state-changed",
                    extra={"new_state": TaskStepStateEnum.COMPLETED.value},
                )
            )
            for dep_step, old_dep_readiness in readiness_changes:
                if dep_step.readiness_status != old_dep_readiness:
                    pending_events.append(
                        WorkspaceEvent(
                            event_name="task:step-readiness-changed",
                            client_id=dep_step.client_id,
                            workspace_id=workspace_id,
                            extra={"new_readiness": dep_step.readiness_status.value},
                        )
                    )
            if old_task_state is not None and task.state != old_task_state:
                pending_events.append(
                    build_workspace_event(
                        task,
                        "task:state-changed",
                        extra={"new_state": task.state.value},
                    )
                )

        if pending_events:
            await event_bus.dispatch(pending_events)
        return
