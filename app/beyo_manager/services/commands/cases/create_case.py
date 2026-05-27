from beyo_manager.domain.cases.enums import CaseStateEnum
from beyo_manager.domain.cases.events import CaseEvent
from beyo_manager.domain.cases.serializers import serialize_case
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.models.tables.cases.case_type import CaseType
from beyo_manager.services.commands.cases.requests import parse_create_case_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def create_case(ctx: ServiceContext) -> dict:
    request = parse_create_case_request(ctx.incoming_data or {})
    case_type_id = request.case_type_id
    type_label = request.type_label
    case_type = None

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "ca")

    async with ctx.session.begin():
        case_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(Case, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            case_kwargs["client_id"] = request.client_id

        if case_type_id:
            case_type = await ctx.session.get(CaseType, case_type_id)
            if case_type and type_label is None:
                type_label = case_type.name
        case = Case(
            **case_kwargs,
            created_by_id=ctx.user_id,
            updated_by_id=ctx.user_id,
            state=CaseStateEnum.OPEN,
            case_type_id=case_type_id,
            type_label=type_label,
        )
        ctx.session.add(case)
        await ctx.session.flush()

        conversation = CaseConversation(
            case=case,
            created_by_id=ctx.user_id,
            state=CaseStateEnum.OPEN,
        )
        ctx.session.add(conversation)
        case.conversations_count = 1
    event = build_workspace_event(case, CaseEvent.CREATED, workspace_id=ctx.workspace_id)
    await dispatch([event])
    return {"case": serialize_case(case, case_type=case_type)}
