from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord


def serialize_view_record(record: UserAppViewRecord) -> dict:
    return {
        "client_id": record.client_id,
        "entity_type": record.entity_type,
        "entity_client_id": record.entity_client_id,
        "started_at": record.started_at.isoformat(),
        "ended_at": record.ended_at.isoformat() if record.ended_at else None,
    }


def serialize_live_user_presence(
    user: User,
    role_name: str,
    current_view: dict | None,
    is_online: bool,
) -> dict:
    return {
        "client_id": user.client_id,
        "username": user.username,
        "email": user.email,
        "profile_picture": user.profile_picture,
        "role_name": role_name,
        "current_view": current_view,
        "is_online": is_online,
    }
