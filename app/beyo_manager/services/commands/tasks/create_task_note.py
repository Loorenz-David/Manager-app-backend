from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskNoteTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_note import TaskNote
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_create_message
from beyo_manager.services.commands.tasks.requests import parse_create_task_note_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def _create_task_note_in_session(
    session: AsyncSession,
    workspace_id: str,
    task_id: str,
    note_type: TaskNoteTypeEnum,
    content: dict,
    user_id: str,
    client_id: str | None = None,
) -> TaskNote:
    note_kwargs: dict[str, str] = {}
    if client_id is not None:
        validate_provided_client_id(client_id, "tno")
        existing = await session.get(TaskNote, client_id)
        if existing is not None:
            raise ConflictError("Provided client_id is already in use.")
        note_kwargs["client_id"] = client_id

    note = TaskNote(
        **note_kwargs,
        workspace_id=workspace_id,
        task_id=task_id,
        note_type=note_type,
        content=content,
        created_by_id=user_id,
    )
    session.add(note)
    await session.flush()
    return note


async def create_task_note(ctx: ServiceContext) -> dict:
    request = parse_create_task_note_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
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

        note = await _create_task_note_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            task_id=request.task_id,
            note_type=request.note_type,
            content=request.content,
            user_id=ctx.user_id,
            client_id=request.client_id,
        )

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=build_create_message(username, "note", "task"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    await event_bus.dispatch([
        build_workspace_event(task, "task:updated"),
    ])
    return {"client_id": note.client_id}
