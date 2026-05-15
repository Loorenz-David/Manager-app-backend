from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.services.context import ServiceContext


async def mark_read(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    async with ctx.session.begin():
        participant = await ctx.session.get(CaseParticipant, data.get("case_participant_client_id"))
        if participant is None:
            raise NotFound("CaseParticipant not found")
        participant.last_read_message_seq = max(participant.last_read_message_seq, int(data.get("up_to_message_seq", 0)))
    return {"last_read_message_seq": participant.last_read_message_seq}
