from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.models.tables.notifications.push_subscription import PushSubscription
from beyo_manager.services.context import ServiceContext


async def register_push_subscription(ctx: ServiceContext) -> dict:
    """Upsert PushSubscription for (user_id, endpoint). Idempotent."""
    data     = ctx.incoming_data
    endpoint = data["endpoint"]

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == ctx.user_id,
                PushSubscription.endpoint == endpoint,
            )
        )
        sub = result.scalar_one_or_none()

        if sub is None:
            sub = PushSubscription(
                user_id=ctx.user_id,
                endpoint=endpoint,
                p256dh=data["p256dh"],
                auth=data["auth"],
            )
            ctx.session.add(sub)
        else:
            sub.p256dh = data["p256dh"]
            sub.auth   = data["auth"]

        sub.device_label = data.get("device_label")
        sub.last_used_at = datetime.now(timezone.utc)
    return {"subscription": {"client_id": sub.client_id}}
