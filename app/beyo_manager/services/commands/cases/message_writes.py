from sqlalchemy import update

from beyo_manager.domain.cases.events import ConversationMessageEvent, conversation_message_extra
from beyo_manager.domain.content.enums import ContentMentionLinkEntityTypeEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_conversation_message import CaseConversationMessage
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.content import process_content_mentions, validate_content


async def _next_message_seq(ctx: ServiceContext, conversation_id: str) -> int:
    result = await ctx.session.execute(
        update(CaseConversation)
        .where(CaseConversation.client_id == conversation_id)
        .values(last_message_seq=CaseConversation.last_message_seq + 1)
        .returning(CaseConversation.last_message_seq)
    )
    return result.scalar_one()


async def write_case_message(
    ctx: ServiceContext,
    *,
    conversation: CaseConversation,
    client_id: str | None,
    content: list,
    plain_text: str,
    increment_case_messages: bool = True,
) -> tuple[CaseConversationMessage, int]:
    if client_id is not None:
        validate_provided_client_id(client_id, "ccm")

    blocks = validate_content(content)
    normalized_content = [block.__dict__ for block in blocks]

    message_kwargs: dict[str, str] = {}
    if client_id is not None:
        duplicate = await ctx.session.get(CaseConversationMessage, client_id)
        if duplicate is not None:
            raise ConflictError("Provided client_id is already in use.")
        message_kwargs["client_id"] = client_id

    seq = await _next_message_seq(ctx, conversation.client_id)
    message = CaseConversationMessage(
        **message_kwargs,
        case_conversation_id=conversation.client_id,
        message_seq=seq,
        created_by_id=ctx.user_id,
        content=normalized_content,
        plain_text=plain_text,
    )
    ctx.session.add(message)
    await ctx.session.flush()
    await process_content_mentions(
        ctx.session,
        normalized_content,
        ContentMentionLinkEntityTypeEnum.CASE_CONVERSATION_MESSAGE,
        message.client_id,
        ctx.user_id,
    )
    await ctx.session.execute(
        update(CaseConversation)
        .where(CaseConversation.client_id == conversation.client_id)
        .values(messages_count=CaseConversation.messages_count + 1)
    )
    if increment_case_messages:
        await ctx.session.execute(
            update(Case)
            .where(Case.client_id == conversation.case_id)
            .values(messages_count=Case.messages_count + 1)
        )
    return message, seq