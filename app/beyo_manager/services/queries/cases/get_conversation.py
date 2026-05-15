from beyo_manager.domain.cases.serializers import serialize_conversation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.services.context import ServiceContext


async def get_conversation(ctx: ServiceContext) -> dict:
    conversation = await ctx.session.get(CaseConversation, (ctx.incoming_data or {}).get("conversation_client_id"))
    if conversation is None:
        raise NotFound("Conversation not found")
    return {"conversation": serialize_conversation(conversation)}
