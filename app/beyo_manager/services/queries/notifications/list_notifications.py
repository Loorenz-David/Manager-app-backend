from sqlalchemy import func, select

from beyo_manager.domain.notifications.results import NotificationResult
from beyo_manager.models.tables.notifications.notification import Notification
from beyo_manager.services.context import ServiceContext


async def list_notifications(ctx: ServiceContext) -> dict:
    """Paginated notification list for the authenticated user.

    incoming_data keys:
      unread_only      (bool, default False)
      limit            (int,  default 30)
      before_client_id (str | None) — keyset cursor
    """
    params       = ctx.incoming_data
    unread_only  = params.get("unread_only", False)
    limit        = min(int(params.get("limit", 30)), 100)
    cursor_id    = params.get("before_client_id")

    stmt = select(Notification).where(Notification.user_id == ctx.user_id)

    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))

    if cursor_id:
        cursor_result = await ctx.session.execute(
            select(Notification.created_at).where(Notification.client_id == cursor_id)
        )
        cursor_at = cursor_result.scalar_one_or_none()
        if cursor_at:
            stmt = stmt.where(Notification.created_at < cursor_at)

    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows   = result.scalars().all()
    has_more = len(rows) > limit

    # Total unread count (always included for badge)
    count_result = await ctx.session.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == ctx.user_id,
            Notification.read_at.is_(None),
        )
    )
    unread_count = count_result.scalar_one()

    return {
        "notifications": [_serialize(n) for n in rows[:limit]],
        "has_more":      has_more,
        "unread_count":  unread_count,
    }


def _serialize(n: Notification) -> dict:
    return {
        "client_id":         n.client_id,
        "notification_type": n.notification_type,
        "title":             n.title,
        "body":              n.body,
        "entity_type":       n.entity_type,
        "entity_client_id":  n.entity_client_id,
        "read_at":           n.read_at.isoformat() if n.read_at else None,
        "created_at":        n.created_at.isoformat(),
    }
