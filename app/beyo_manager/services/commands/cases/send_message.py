from beyo_manager.domain.cases.events import ConversationMessageEvent, conversation_message_extra
from beyo_manager.domain.cases.serializers import serialize_message
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.services.commands.cases.requests import parse_send_message_request
from beyo_manager.services.commands.cases.message_writes import write_case_message
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_conversation_event

async def send_message(ctx: ServiceContext) -> dict:
    request = parse_send_message_request(ctx.incoming_data or {})

    async with ctx.session.begin():
        conversation = await ctx.session.get(CaseConversation, request.conversation_client_id)
        if conversation is None:
            raise NotFound("Conversation not found")
        message, seq = await write_case_message(
            ctx,
            conversation=conversation,
            client_id=request.client_id,
            content=request.content,
            plain_text=request.plain_text,
        )
    event = build_conversation_event(
        message,
        ConversationMessageEvent.CREATED,
        conversation_id=conversation.client_id,
        workspace_id=ctx.workspace_id,
        extra=conversation_message_extra(seq),
    )
    await dispatch([event])
    return {"message": serialize_message(message)}
