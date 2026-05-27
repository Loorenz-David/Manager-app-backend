from datetime import datetime, timezone

from sqlalchemy.orm import selectinload

from beyo_manager.domain.cases.enums import CaseStateEnum
from beyo_manager.domain.cases.events import CaseEvent, case_state_extra
from beyo_manager.domain.cases.serializers import serialize_case
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def update_case_state(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    new_state = CaseStateEnum(data.get("new_state"))
    async with ctx.session.begin():
        case = await ctx.session.get(
            Case,
            data.get("case_client_id"),
            options=[selectinload(Case.conversations), selectinload(Case.case_type)],
        )
        if case is None:
            raise NotFound("Case not found")
        case.state = new_state
        case.updated_by_id = ctx.user_id
        case.updated_at = datetime.now(timezone.utc)
    event = build_workspace_event(case, CaseEvent.STATE_CHANGED, workspace_id=ctx.workspace_id, extra=case_state_extra(new_state))
    await dispatch([event])
    return {"case": serialize_case(case, case_type=case.__dict__.get("case_type"))}
