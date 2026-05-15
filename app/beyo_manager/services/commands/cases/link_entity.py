from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum, CaseLinkRoleEnum
from beyo_manager.domain.cases.serializers import serialize_case_link
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.services.context import ServiceContext


async def link_entity(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    async with ctx.session.begin():
        case = await ctx.session.get(Case, data.get("case_client_id"))
        if case is None:
            raise NotFound("Case not found")
        link = CaseLink(
            case_id=case.client_id,
            entity_type=CaseLinkEntityTypeEnum(data.get("entity_type")),
            entity_client_id=data.get("entity_client_id"),
            role=CaseLinkRoleEnum(data.get("role")),
        )
        ctx.session.add(link)
    return {"link": serialize_case_link(link)}
