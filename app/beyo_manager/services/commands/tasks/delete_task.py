from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.notifications.pin_cleanup import cleanup_task_pins
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_delete_message
from beyo_manager.services.commands.tasks.requests import parse_terminal_task_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def delete_task(ctx: ServiceContext) -> dict:
    request = parse_terminal_task_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.client_id,
            )
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")
        if task.is_deleted:
            raise ConflictError("Task is already deleted.")

        task.is_deleted = True
        task.deleted_at = datetime.now(timezone.utc)
        task.deleted_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.DELETED,
            description=build_delete_message(username, "task", "workspace"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )
        await cleanup_task_pins(ctx.session, task.client_id)

    await event_bus.dispatch([
        build_workspace_event(task, "task:deleted"),
    ])
    return {"client_id": task.client_id}
