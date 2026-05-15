from sqlalchemy import select

from beyo_manager.domain.cases.enums import CaseStateEnum
from beyo_manager.domain.cases.events import CaseEvent
from beyo_manager.domain.cases.serializers import serialize_case
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_type import CaseType
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def create_case(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    case_type_id = data.get("case_type_id")
    type_label = data.get("type_label")
    async with ctx.session.begin():
        if case_type_id:
            case_type = await ctx.session.get(CaseType, case_type_id)
            if case_type and type_label is None:
                type_label = case_type.name
        case = Case(created_by_id=ctx.user_id, updated_by_id=ctx.user_id, state=CaseStateEnum.OPEN, case_type_id=case_type_id, type_label=type_label)
        ctx.session.add(case)
    event = build_workspace_event(case, CaseEvent.CREATED, workspace_id=ctx.workspace_id)
    await dispatch([event])
    return {"case": serialize_case(case)}
