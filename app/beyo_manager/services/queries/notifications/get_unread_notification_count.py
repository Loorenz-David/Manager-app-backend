from sqlalchemy import func, select

from beyo_manager.models.tables.notifications.notification import Notification
from beyo_manager.services.context import ServiceContext


async def get_unread_notification_count(ctx: ServiceContext) -> dict:
    """Lightweight unread-count query for badge polling and post-login hydration."""
    result = await ctx.session.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == ctx.user_id,
            Notification.read_at.is_(None),
        )
    )
    return {"unread_count": result.scalar_one()}
