from sqlalchemy import select

from beyo_manager.domain.cases.serializers import serialize_participant
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.services.context import ServiceContext


async def list_participants(ctx: ServiceContext) -> dict:
    participants = (await ctx.session.execute(select(CaseParticipant).where(CaseParticipant.case_id == (ctx.incoming_data or {}).get("case_client_id")))).scalars().all()
    return {"participants": [serialize_participant(participant) for participant in participants]}
