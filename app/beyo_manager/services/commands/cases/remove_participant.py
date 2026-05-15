from sqlalchemy import func, update

from beyo_manager.domain.cases.events import CaseEvent
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def remove_participant(ctx: ServiceContext) -> dict:
    async with ctx.session.begin():
        participant = await ctx.session.get(CaseParticipant, (ctx.incoming_data or {}).get("case_participant_client_id"))
        if participant is None:
            raise NotFound("CaseParticipant not found")
        case_id = participant.case_id
        case = await ctx.session.get(Case, case_id)
        await ctx.session.delete(participant)
        await ctx.session.execute(update(Case).where(Case.client_id == case_id).values(participants_count=func.greatest(Case.participants_count - 1, 0)))
    if case:
        event = build_workspace_event(case, CaseEvent.PARTICIPANT_REMOVED, workspace_id=ctx.workspace_id)
        await dispatch([event])
    return {"deleted": True}
