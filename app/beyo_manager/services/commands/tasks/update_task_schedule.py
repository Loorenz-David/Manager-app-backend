"""CMD: Update Task schedule fields and emit task:updated event."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_update_message
from beyo_manager.services.commands.task_post_handling._sync_post_handling_state_in_session import (
    _sync_post_handling_state_in_session,
)
from beyo_manager.services.commands.tasks.requests import parse_update_task_schedule_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


_TERMINAL_STATES = frozenset(
    {
        TaskStateEnum.RESOLVED,
        TaskStateEnum.FAILED,
        TaskStateEnum.CANCELLED,
    }
)


async def update_task_schedule(ctx: ServiceContext) -> dict:
    request = parse_update_task_schedule_request(ctx.incoming_data)

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
            raise ValidationError("Terminal tasks cannot be updated.")

        task.scheduled_start_at = request.scheduled_start_at
        task.scheduled_end_at = request.scheduled_end_at

        if (
            task.scheduled_start_at is not None
            and task.scheduled_end_at is not None
            and task.scheduled_end_at < task.scheduled_start_at
        ):
            raise ValidationError("scheduled_end_at must be >= scheduled_start_at.")

        task.updated_at = datetime.now(timezone.utc)
        task.updated_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_update_message(
                username,
                ["scheduled_start_at", "scheduled_end_at"],
                f"task #{task.task_scalar_id}",
            ),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    async with maybe_begin(ctx.session):
        await _sync_post_handling_state_in_session(
            ctx.session,
            task.client_id,
            workspace_id=ctx.workspace_id,
            now=datetime.now(timezone.utc),
            user_id=ctx.user_id,
            username_snapshot=ctx.identity.get("username"),
        )

    await event_bus.dispatch([build_workspace_event(task, "task:updated")])
    return {"client_id": task.client_id}
