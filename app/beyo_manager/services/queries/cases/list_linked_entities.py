from sqlalchemy import select

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum, CaseLinkRoleEnum
from beyo_manager.domain.cases.serializers import serialize_case_link
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.services.context import ServiceContext


async def list_linked_entities(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    stmt = select(CaseLink).where(CaseLink.case_id == data.get("case_client_id"))
    if data.get("entity_type"):
        stmt = stmt.where(CaseLink.entity_type == CaseLinkEntityTypeEnum(data["entity_type"]))
    if data.get("role"):
        stmt = stmt.where(CaseLink.role == CaseLinkRoleEnum(data["role"]))
    links = (await ctx.session.execute(stmt)).scalars().all()
    return {"links": [serialize_case_link(link) for link in links]}
