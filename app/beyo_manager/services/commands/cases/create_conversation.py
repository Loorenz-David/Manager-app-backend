from sqlalchemy import update

from beyo_manager.domain.cases.enums import CaseStateEnum
from beyo_manager.domain.cases.events import CaseEvent
from beyo_manager.domain.cases.serializers import serialize_conversation
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def create_conversation(ctx: ServiceContext) -> dict:
    async with ctx.session.begin():
        case = await ctx.session.get(Case, (ctx.incoming_data or {}).get("case_client_id"))
        if case is None:
            raise NotFound("Case not found")
        conversation = CaseConversation(case_id=case.client_id, created_by_id=ctx.user_id, state=CaseStateEnum.OPEN)
        ctx.session.add(conversation)
        await ctx.session.execute(update(Case).where(Case.client_id == case.client_id).values(conversations_count=Case.conversations_count + 1))
    event = build_workspace_event(case, CaseEvent.CONVERSATION_CREATED, workspace_id=ctx.workspace_id)
    await dispatch([event])
    return {"conversation": serialize_conversation(conversation)}
