from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.domain.tasks.notification_targets import resolve_task_notification_targets
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_state_change_message
from beyo_manager.services.commands.tasks.requests import parse_terminal_task_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.execution.task_factory import create_instant_task


_TERMINAL_STATES = frozenset(
    {
        TaskStateEnum.RESOLVED,
        TaskStateEnum.FAILED,
        TaskStateEnum.CANCELLED,
    }
)


async def resolve_task(ctx: ServiceContext) -> dict:
    request = parse_terminal_task_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.client_id,
                Task.is_deleted.is_(False),
            )
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")
        if task.state in _TERMINAL_STATES:
            raise ConflictError("Task is already in a terminal state.")

        original_state = task.state.value
        now = datetime.now(timezone.utc)
        task.state = TaskStateEnum.RESOLVED
        task.closed_at = now
        task.updated_at = now
        task.updated_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_state_change_message(username, "task", TaskStateEnum.RESOLVED.value),
            field_name="state",
            from_value={"state": original_state},
            to_value={"state": TaskStateEnum.RESOLVED.value},
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

        target_user_ids = list(
            await resolve_task_notification_targets(
                ctx.session,
                ctx.workspace_id,
                task.client_id,
                task.created_by_id,
                ctx.user_id,
                {"state": task.state.value},
            )
        )
        if target_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_state_changed",
                    user_ids=target_user_ids,
                    title="Task resolved",
                    body="A task has been resolved.",
                    entity_type="task",
                    entity_client_id=task.client_id,
                    exclude_viewing=[{"entity_type": "task", "entity_client_id": task.client_id}],
                )),
            )

    await event_bus.dispatch([
        build_workspace_event(task, "task:state-changed", extra={"new_state": TaskStateEnum.RESOLVED.value}),
    ])
    return {"client_id": task.client_id}
