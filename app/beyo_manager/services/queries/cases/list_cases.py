from sqlalchemy import select

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum, CaseStateEnum
from beyo_manager.domain.cases.serializers import serialize_case
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.services.context import ServiceContext


async def list_cases(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}
    stmt = select(Case)
    if data.get("state"):
        stmt = stmt.where(Case.state == CaseStateEnum(data["state"]))
    if data.get("created_by_id"):
        stmt = stmt.where(Case.created_by_id == data["created_by_id"])
    if data.get("entity_type") and data.get("entity_client_id"):
        stmt = stmt.join(CaseLink, CaseLink.case_id == Case.client_id).where(
            CaseLink.entity_type == CaseLinkEntityTypeEnum(data["entity_type"]),
            CaseLink.entity_client_id == data["entity_client_id"],
        )
    stmt = stmt.offset(int(data.get("offset", 0))).limit(int(data.get("limit", 50)))
    cases = (await ctx.session.execute(stmt)).scalars().all()
    return {"cases": [serialize_case(case) for case in cases]}
