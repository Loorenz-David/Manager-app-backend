from sqlalchemy import select

from beyo_manager.domain.cases.serializers import serialize_message
from beyo_manager.models.tables.cases.case_conversation_message import CaseConversationMessage
from beyo_manager.services.context import ServiceContext


async def list_messages(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    stmt = select(CaseConversationMessage).where(CaseConversationMessage.case_conversation_id == data.get("conversation_client_id"))
    if data.get("before_seq") is not None:
        stmt = stmt.where(CaseConversationMessage.message_seq < int(data["before_seq"]))
    stmt = stmt.order_by(CaseConversationMessage.message_seq.desc()).limit(int(data.get("limit", 50)))
    messages = (await ctx.session.execute(stmt)).scalars().all()
    return {"messages": [serialize_message(message) for message in messages]}
