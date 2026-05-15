from sqlalchemy import select, update

from beyo_manager.domain.cases.events import CaseEvent
from beyo_manager.domain.cases.serializers import serialize_participant
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def add_participant(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    user_ids = set(data.get("user_ids") or [])
    async with ctx.session.begin():
        case = await ctx.session.get(Case, data.get("case_client_id"))
        if case is None:
            raise NotFound("Case not found")
        existing = set((await ctx.session.execute(select(CaseParticipant.user_id).where(CaseParticipant.case_id == case.client_id, CaseParticipant.user_id.in_(user_ids)))).scalars().all())
        added = [CaseParticipant(case_id=case.client_id, user_id=user_id) for user_id in user_ids - existing]
        ctx.session.add_all(added)
        if added:
            await ctx.session.execute(update(Case).where(Case.client_id == case.client_id).values(participants_count=Case.participants_count + len(added)))
    if added:
        event = build_workspace_event(case, CaseEvent.PARTICIPANT_ADDED, workspace_id=ctx.workspace_id)
        await dispatch([event])
    return {"added": [serialize_participant(participant) for participant in added]}
