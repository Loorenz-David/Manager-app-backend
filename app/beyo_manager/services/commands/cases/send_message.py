from sqlalchemy import select, update

from beyo_manager.domain.cases.events import ConversationMessageEvent, conversation_message_extra
from beyo_manager.domain.cases.serializers import serialize_message
from beyo_manager.domain.content.enums import ContentMentionLinkEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_conversation_message import CaseConversationMessage
from beyo_manager.services.commands.cases.requests import parse_send_message_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.content import process_content_mentions, validate_content
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_conversation_event


async def _next_message_seq(ctx: ServiceContext, conversation_id: str) -> int:
    result = await ctx.session.execute(
        update(CaseConversation)
        .where(CaseConversation.client_id == conversation_id)
        .values(last_message_seq=CaseConversation.last_message_seq + 1)
        .returning(CaseConversation.last_message_seq)
    )
    return result.scalar_one()


async def send_message(ctx: ServiceContext) -> dict:
    request = parse_send_message_request(ctx.incoming_data or {})

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "ccm")

    blocks = validate_content(request.content)
    content = [block.__dict__ for block in blocks]
    async with ctx.session.begin():
        message_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(CaseConversationMessage, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            message_kwargs["client_id"] = request.client_id

        conversation = await ctx.session.get(CaseConversation, request.conversation_client_id)
        if conversation is None:
            raise NotFound("Conversation not found")
        seq = await _next_message_seq(ctx, conversation.client_id)
        message = CaseConversationMessage(
            **message_kwargs,
            case_conversation_id=conversation.client_id,
            message_seq=seq,
            created_by_id=ctx.user_id,
            content=content,
            plain_text=request.plain_text,
        )
        ctx.session.add(message)
        await ctx.session.flush()
        await process_content_mentions(ctx.session, content, ContentMentionLinkEntityTypeEnum.CASE_CONVERSATION_MESSAGE, message.client_id, ctx.user_id)
        await ctx.session.execute(update(CaseConversation).where(CaseConversation.client_id == conversation.client_id).values(messages_count=CaseConversation.messages_count + 1))
        await ctx.session.execute(update(Case).where(Case.client_id == conversation.case_id).values(messages_count=Case.messages_count + 1))
    event = build_conversation_event(
        message,
        ConversationMessageEvent.CREATED,
        conversation_id=conversation.client_id,
        workspace_id=ctx.workspace_id,
        extra=conversation_message_extra(seq),
    )
    await dispatch([event])
    return {"message": serialize_message(message)}
