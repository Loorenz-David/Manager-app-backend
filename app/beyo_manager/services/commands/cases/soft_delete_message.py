from sqlalchemy import func, select, update

from beyo_manager.domain.cases.events import ConversationMessageEvent
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_conversation_message import CaseConversationMessage
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_conversation_event


async def soft_delete_message(ctx: ServiceContext) -> dict:
    async with ctx.session.begin():
        message = await ctx.session.get(CaseConversationMessage, (ctx.incoming_data or {}).get("message_client_id"))
        if message is None:
            raise NotFound("Message not found")
        conversation_id = message.case_conversation_id
        if not message.has_been_deleted:
            message.has_been_deleted = True
            conversation = await ctx.session.get(CaseConversation, conversation_id)
            await ctx.session.execute(update(CaseConversation).where(CaseConversation.client_id == conversation_id).values(messages_count=func.greatest(CaseConversation.messages_count - 1, 0)))
            if conversation:
                await ctx.session.execute(update(Case).where(Case.client_id == conversation.case_id).values(messages_count=func.greatest(Case.messages_count - 1, 0)))
    event = build_conversation_event(
        message,
        ConversationMessageEvent.DELETED,
        conversation_id=conversation_id,
        workspace_id=ctx.workspace_id,
    )
    await dispatch([event])
    return {"deleted": True}
