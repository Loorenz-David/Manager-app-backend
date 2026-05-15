from beyo_manager.domain.cases.serializers import serialize_case
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.services.context import ServiceContext


async def get_case(ctx: ServiceContext) -> dict:
    case = await ctx.session.get(Case, (ctx.incoming_data or {}).get("case_client_id"))
    if case is None:
        raise NotFound("Case not found")
    return {"case": serialize_case(case)}
