from sqlalchemy import select

from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.services.context import ServiceContext


async def get_unread_counts(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    user_id = data.get("user_id") or ctx.user_id
    stmt = select(
        CaseConversation.case_id,
        CaseConversation.last_message_seq,
        CaseParticipant.last_read_message_seq,
    ).join(
        CaseParticipant, CaseParticipant.case_id == CaseConversation.case_id
    ).where(CaseParticipant.user_id == user_id)

    if data.get("case_client_ids"):
        stmt = stmt.where(CaseConversation.case_id.in_(data["case_client_ids"]))

    rows = (await ctx.session.execute(stmt)).all()

    case_counts: dict[str, int] = {}
    for case_id, last_seq, read_seq in rows:
        case_counts[case_id] = case_counts.get(case_id, 0) + max(last_seq - read_seq, 0)

    if not data.get("case_client_ids"):
        case_counts = {key: value for key, value in case_counts.items() if value > 0}

    return {"case_unread_counts": case_counts}
