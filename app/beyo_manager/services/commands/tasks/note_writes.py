from beyo_manager.domain.content.enums import ContentMentionLinkEntityTypeEnum
from beyo_manager.domain.tasks.enums import TaskNoteTypeEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.task_note import TaskNote
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.content import process_content_mentions, validate_content


async def write_task_note(
    ctx: ServiceContext,
    *,
    task_id: str,
    note_type: TaskNoteTypeEnum,
    content: list,
    plain_text: str,
    users_read_list: list[str] | None = None,
    client_id: str | None = None,
) -> TaskNote:
    if client_id is not None:
        validate_provided_client_id(client_id, "tno")
        existing = await ctx.session.get(TaskNote, client_id)
        if existing is not None:
            raise ConflictError("Provided client_id is already in use.")

    blocks = validate_content(content)
    normalized_content = [block.__dict__ for block in blocks]

    note_kwargs: dict[str, str] = {}
    if client_id is not None:
        note_kwargs["client_id"] = client_id

    note = TaskNote(
        **note_kwargs,
        workspace_id=ctx.workspace_id,
        task_id=task_id,
        note_type=note_type,
        content=normalized_content,
        plain_text=plain_text,
        users_read_list=users_read_list or [],
        created_by_id=ctx.user_id,
    )
    ctx.session.add(note)
    await ctx.session.flush()

    await process_content_mentions(
        ctx.session,
        normalized_content,
        ContentMentionLinkEntityTypeEnum.TASK_NOTE_MENTION,
        note.client_id,
        ctx.user_id,
    )
    return note
