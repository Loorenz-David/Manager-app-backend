from datetime import datetime, timezone

from sqlalchemy.orm import selectinload

from beyo_manager.domain.cases.events import CaseEvent
from beyo_manager.domain.cases.serializers import serialize_case
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_type import CaseType
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def update_case(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    if "case_type_id" not in data and "type_label" not in data:
        raise ValidationError("case_type_id or type_label is required")
    case_type = None
    async with ctx.session.begin():
        case = await ctx.session.get(
            Case,
            data.get("case_client_id"),
            options=[selectinload(Case.conversations), selectinload(Case.case_type)],
        )
        if case is None:
            raise NotFound("Case not found")
        case_type = case.__dict__.get("case_type")
        if "case_type_id" in data:
            case.case_type_id = data.get("case_type_id")
            if case.case_type_id and "type_label" not in data:
                case_type = await ctx.session.get(CaseType, case.case_type_id)
                case.type_label = case_type.name if case_type else case.type_label
            elif not case.case_type_id:
                case_type = None
        if "type_label" in data:
            case.type_label = data.get("type_label")
        case.updated_by_id = ctx.user_id
        case.updated_at = datetime.now(timezone.utc)
    event = build_workspace_event(case, CaseEvent.UPDATED, workspace_id=ctx.workspace_id)
    await dispatch([event])
    return {"case": serialize_case(case, case_type=case_type)}
