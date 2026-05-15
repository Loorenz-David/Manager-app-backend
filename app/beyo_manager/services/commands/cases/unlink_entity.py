from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.services.context import ServiceContext


async def unlink_entity(ctx: ServiceContext) -> dict:
    async with ctx.session.begin():
        link = await ctx.session.get(CaseLink, (ctx.incoming_data or {}).get("case_link_client_id"))
        if link is None:
            raise NotFound("CaseLink not found")
        await ctx.session.delete(link)
    return {"deleted": True}
