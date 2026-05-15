from datetime import datetime, timezone

from beyo_manager.domain.cases.events import ConversationMessageEvent
from beyo_manager.domain.cases.serializers import serialize_message
from beyo_manager.domain.content.enums import ContentMentionLinkEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.cases.case_conversation_message import CaseConversationMessage
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.content import process_content_mentions, validate_content
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_conversation_event


async def edit_message(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    blocks = validate_content(data.get("content"))
    content = [block.__dict__ for block in blocks]
    async with ctx.session.begin():
        message = await ctx.session.get(CaseConversationMessage, data.get("message_client_id"))
        if message is None:
            raise NotFound("Message not found")
        if message.has_been_deleted:
            raise ValidationError("deleted messages cannot be edited")
        message.content = content
        message.plain_text = data.get("plain_text", "")
        message.has_been_edited = True
        message.updated_at = datetime.now(timezone.utc)
        await process_content_mentions(ctx.session, content, ContentMentionLinkEntityTypeEnum.CASE_CONVERSATION_MESSAGE, message.client_id, ctx.user_id, replace=True)
    event = build_conversation_event(
        message,
        ConversationMessageEvent.EDITED,
        conversation_id=message.case_conversation_id,
        workspace_id=ctx.workspace_id,
    )
    await dispatch([event])
    return {"message": serialize_message(message)}
