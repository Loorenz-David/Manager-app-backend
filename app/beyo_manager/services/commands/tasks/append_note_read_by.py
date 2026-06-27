from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task_note import TaskNote
from beyo_manager.services.commands.tasks.requests import parse_mark_note_read_by_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def append_note_read_by(ctx: ServiceContext) -> dict:
    request = parse_mark_note_read_by_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(TaskNote).where(
                TaskNote.workspace_id == ctx.workspace_id,
                TaskNote.client_id == request.client_id,
                TaskNote.is_deleted.is_(False),
            )
        )
        note = result.scalar_one_or_none()
        if note is None or note.task_id != request.task_id:
            raise NotFound("Task note not found.")

        existing_list = list(note.users_read_list or [])
        existing_set = set(existing_list)
        for entry in request.user_ids:
            if entry in existing_set:
                continue
            existing_list.append(entry)
            existing_set.add(entry)
        note.users_read_list = existing_list

    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="task:note-updated",
            client_id=note.task_id,
            workspace_id=ctx.workspace_id,
            extra={"note_id": note.client_id},
        ),
    ])
    return {"client_id": note.client_id}
