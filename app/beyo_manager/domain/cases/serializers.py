def _value(value):
    return value.value if hasattr(value, "value") else value


def serialize_case(case) -> dict:
    return {
        "client_id": case.client_id,
        "state": _value(case.state),
        "type_label": case.type_label,
        "participants_count": case.participants_count,
        "conversations_count": case.conversations_count,
        "messages_count": case.messages_count,
        "created_at": case.created_at.isoformat(),
        "created_by_id": case.created_by_id,
    }


def serialize_case_link(link) -> dict:
    return {
        "client_id": link.client_id,
        "entity_type": _value(link.entity_type),
        "entity_client_id": link.entity_client_id,
        "role": _value(link.role),
        "created_at": link.created_at.isoformat(),
    }


def serialize_participant(participant) -> dict:
    return {
        "client_id": participant.client_id,
        "user_id": participant.user_id,
        "last_read_message_seq": participant.last_read_message_seq,
        "joined_at": participant.joined_at.isoformat(),
    }


def serialize_conversation(conversation, *, last_messages: list | None = None) -> dict:
    return {
        "client_id": conversation.client_id,
        "state": _value(conversation.state),
        "messages_count": conversation.messages_count,
        "last_message_seq": conversation.last_message_seq,
        "created_at": conversation.created_at.isoformat(),
        "last_messages": last_messages or [],
    }


def serialize_message(message) -> dict:
    return {
        "client_id": message.client_id,
        "message_seq": message.message_seq,
        "content": None if message.has_been_deleted else message.content,
        "plain_text": "" if message.has_been_deleted else message.plain_text,
        "has_been_edited": message.has_been_edited,
        "has_been_deleted": message.has_been_deleted,
        "created_at": message.created_at.isoformat(),
    }
