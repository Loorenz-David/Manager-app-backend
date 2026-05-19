from sqlalchemy import update

from beyo_manager.domain.cases.enums import CaseStateEnum
from beyo_manager.domain.cases.events import CaseEvent
from beyo_manager.domain.cases.serializers import serialize_conversation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.services.commands.cases.requests import parse_create_conversation_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def create_conversation(ctx: ServiceContext) -> dict:
    request = parse_create_conversation_request(ctx.incoming_data or {})

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "ccv")

    async with ctx.session.begin():
        conversation_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(CaseConversation, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            conversation_kwargs["client_id"] = request.client_id

        case = await ctx.session.get(Case, request.case_client_id)
        if case is None:
            raise NotFound("Case not found")
        conversation = CaseConversation(**conversation_kwargs, case_id=case.client_id, created_by_id=ctx.user_id, state=CaseStateEnum.OPEN)
        ctx.session.add(conversation)
        await ctx.session.execute(update(Case).where(Case.client_id == case.client_id).values(conversations_count=Case.conversations_count + 1))
    event = build_workspace_event(case, CaseEvent.CONVERSATION_CREATED, workspace_id=ctx.workspace_id)
    await dispatch([event])
    return {"conversation": serialize_conversation(conversation)}
