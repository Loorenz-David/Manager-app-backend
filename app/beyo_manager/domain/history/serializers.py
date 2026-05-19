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
