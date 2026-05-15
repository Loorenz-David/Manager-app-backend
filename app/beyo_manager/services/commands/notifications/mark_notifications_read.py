from datetime import datetime, timezone

from sqlalchemy import select, update

from beyo_manager.models.tables.notifications.notification import Notification
from beyo_manager.services.context import ServiceContext


async def mark_notifications_read(ctx: ServiceContext) -> dict:
    """Set read_at = now() on unread notifications. Idempotent (already-read rows skipped).

    incoming_data keys:
      notification_client_ids (list[str]) — explicit list, OR
      mark_all_read           (bool)      — mark every unread notification for the user.
    """
    data        = ctx.incoming_data
    mark_all    = data.get("mark_all_read", False)
    target_ids  = data.get("notification_client_ids", [])
    now         = datetime.now(timezone.utc)

    stmt = (
        update(Notification)
        .where(
            Notification.user_id == ctx.user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )

    if not mark_all:
        if not target_ids:
            return {"marked_read": 0}
        stmt = stmt.where(Notification.client_id.in_(target_ids))

    async with ctx.session.begin():
        result = await ctx.session.execute(stmt)
    return {"marked_read": result.rowcount}
