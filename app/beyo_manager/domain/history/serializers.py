def _value(value):
    return value.value if hasattr(value, "value") else value


def serialize_history_record(record) -> dict:
    return {
        "client_id": record.client_id,
        "change_type": _value(record.change_type),
        "description": record.description,
        "field_name": record.field_name,
        "from_value": record.from_value,
        "to_value": record.to_value,
        "created_at": record.created_at.isoformat(),
        "created_by_id": record.created_by_id,
        "username_snapshot": record.username_snapshot,
    }


def serialize_history_record_with_link(record, link) -> dict:
    return {
        **serialize_history_record(record),
        "entity_type": _value(link.entity_type),
        "entity_client_id": link.entity_client_id,
    }


def serialize_record_actor(user, created_by_id: str | None, username_snapshot: str | None = None) -> dict | None:
    """Actor shape shared by timeline-style endpoints (task flow records, inventory history):
    ``{client_id, username, profile_picture}``; falls back to the username snapshot when the
    user row is gone, and is ``None`` for system-written records."""
    if created_by_id is None:
        return None
    if user is not None:
        return {
            "client_id": user.client_id,
            "username": user.username,
            "profile_picture": user.profile_picture,
        }
    return {
        "client_id": created_by_id,
        "username": username_snapshot,
        "profile_picture": None,
    }
