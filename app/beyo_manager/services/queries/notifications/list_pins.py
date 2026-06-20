from sqlalchemy import select

from beyo_manager.domain.notifications.serializers import serialize_pin_full
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext


async def list_pins(ctx: ServiceContext) -> dict:
    entity_client_ids = ctx.incoming_data.get("entity_client_ids")
    major_client_entity_ids = ctx.incoming_data.get("major_client_entity_ids")

    stmt = (
        select(NotificationPin, User)
        .join(User, NotificationPin.user_id == User.client_id)
        .where(NotificationPin.user_id == ctx.user_id)
    )

    if entity_client_ids:
        stmt = stmt.where(NotificationPin.entity_client_id.in_(entity_client_ids))
    elif major_client_entity_ids:
        stmt = stmt.where(NotificationPin.major_client_entity_id.in_(major_client_entity_ids))
    else:
        return {"pins": []}

    rows = (await ctx.session.execute(stmt)).all()
    return {"pins": [serialize_pin_full(pin, user) for pin, user in rows]}
