from beyo_manager.domain.users.serializers import serialize_user_working_section_member
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.users.user import User


def serialize_pin_full(pin: NotificationPin, user: User) -> dict:
    return {
        "client_id": pin.client_id,
        "entity_type": pin.entity_type,
        "entity_client_id": pin.entity_client_id,
        "major_entity_type": pin.major_entity_type,
        "major_client_entity_id": pin.major_client_entity_id,
        "conditions": pin.conditions,
        "fire_once": pin.fire_once,
        "pinned_at": pin.pinned_at.isoformat(),
        "user": serialize_user_working_section_member(user),
    }
