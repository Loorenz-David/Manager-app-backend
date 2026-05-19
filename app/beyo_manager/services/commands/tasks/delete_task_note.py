from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.task_note import TaskNote
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_delete_message
from beyo_manager.services.commands.tasks.requests import parse_delete_task_note_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def delete_task_note(ctx: ServiceContext) -> dict:
    request = parse_delete_task_note_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(TaskNote).where(
                TaskNote.workspace_id == ctx.workspace_id,
                TaskNote.client_id == request.client_id,
            )
        )
        note = result.scalar_one_or_none()
        if note is None:
            raise NotFound("Task note not found.")
        if note.is_deleted:
            raise ConflictError("Task note is already deleted.")

        note.is_deleted = True
        note.deleted_at = datetime.now(timezone.utc)
        note.deleted_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=note.task_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_delete_message(username, "note", "task"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="task:updated",
            client_id=note.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"client_id": note.client_id}
