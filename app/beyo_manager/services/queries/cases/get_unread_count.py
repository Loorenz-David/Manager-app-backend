from sqlalchemy import func, select

from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.services.context import ServiceContext


async def get_unread_count(ctx: ServiceContext) -> dict:
    user_id = (ctx.incoming_data or {}).get("user_id") or ctx.user_id

    result = await ctx.session.execute(
        select(
            func.coalesce(
                func.sum(
                    func.greatest(
                        CaseConversation.last_message_seq - CaseParticipant.last_read_message_seq,
                        0,
                    )
                ),
                0,
            )
        )
        .select_from(CaseConversation)
        .join(CaseParticipant, CaseParticipant.case_id == CaseConversation.case_id)
        .where(CaseParticipant.user_id == user_id)
    )

    return {"unread_count": int(result.scalar_one() or 0)}
