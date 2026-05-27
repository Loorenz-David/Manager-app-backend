from datetime import datetime, timezone

from sqlalchemy import update as sa_update

from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.services.commands.upholstery.requests import parse_mark_upholsteries_favorite_request
from beyo_manager.services.context import ServiceContext


async def mark_upholsteries_favorite(ctx: ServiceContext) -> dict:
    request = parse_mark_upholsteries_favorite_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            sa_update(Upholstery)
            .where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.is_deleted.is_(False),
                Upholstery.client_id.in_(request.upholstery_ids),
            )
            .values(
                favorite=request.favorite,
                updated_by_id=ctx.user_id,
                updated_at=datetime.now(timezone.utc),
            )
            .execution_options(synchronize_session=False)
        )

    return {"updated_count": int(result.rowcount or 0)}
