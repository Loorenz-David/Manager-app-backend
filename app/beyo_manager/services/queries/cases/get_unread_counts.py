from sqlalchemy import select

from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.services.context import ServiceContext


async def get_unread_counts(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    user_id = data.get("user_id") or ctx.user_id
    stmt = select(CaseConversation.client_id, CaseConversation.last_message_seq, CaseParticipant.last_read_message_seq).join(
        CaseParticipant, CaseParticipant.case_id == CaseConversation.case_id
    ).where(CaseParticipant.user_id == user_id)
    if data.get("conversation_client_ids"):
        stmt = stmt.where(CaseConversation.client_id.in_(data["conversation_client_ids"]))
    rows = (await ctx.session.execute(stmt)).all()
    counts = {conversation_id: max(last_seq - read_seq, 0) for conversation_id, last_seq, read_seq in rows}
    if not data.get("conversation_client_ids"):
        counts = {key: value for key, value in counts.items() if value > 0}
    return {"unread_counts": counts}
