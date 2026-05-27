def _value(value):
    return value.value if hasattr(value, "value") else value


def _first_conversation(case):
    conversations = getattr(case, "conversations", None) or []
    return conversations[0] if conversations else None


def _loaded_case_type(case):
    return case.__dict__.get("case_type")


def serialize_case_type(case_type) -> dict | None:
    if case_type is None:
        return None
    return {
        "name": case_type.name,
        "image": case_type.image_url,
    }


def serialize_case(case, *, case_type=None) -> dict:
    conversation = _first_conversation(case)
    resolved_case_type = case_type if case_type is not None else _loaded_case_type(case)
    payload = {
        "client_id": case.client_id,
        "state": _value(case.state),
        "case_type": serialize_case_type(resolved_case_type),
        "participants_count": case.participants_count,
        "conversations_count": case.conversations_count,
        "messages_count": case.messages_count,
        "created_at": case.created_at.isoformat(),
        "created_by_id": case.created_by_id,
    }
    if conversation is not None:
        payload.update(
            {
                "conversation_client_id": conversation.client_id,
                "conversation_messages_count": conversation.messages_count,
                "conversation_last_message_seq": conversation.last_message_seq,
                "conversation_created_at": conversation.created_at.isoformat(),
            }
        )
    return payload


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


def serialize_user_light(user) -> dict | None:
    if user is None:
        return None
    return {
        "client_id": user.client_id,
        "username": user.username,
        "profile_picture": user.profile_picture,
    }


def serialize_case_list_item(
    case,
    *,
    case_type=None,
    created_by,
    entity_type: str | None,
    last_message_seq: int,
    task=None,
    item=None,
    item_image=None,
) -> dict:
    resolved_case_type = case_type if case_type is not None else _loaded_case_type(case)
    payload = {
        "client_id": case.client_id,
        "created_at": case.created_at.isoformat(),
        "state": _value(case.state),
        "case_type_id": case.case_type_id,
        "case_type": serialize_case_type(resolved_case_type),
        "participant_count": case.participants_count,
        "messages_count": case.messages_count,
        "created_by": serialize_user_light(created_by),
        "entity_type": entity_type,
        "last_message_seq": last_message_seq,
    }
    if entity_type == "task" and task is not None:
        payload["task"] = {
            "client_id": task.client_id,
            "state": _value(task.state),
            "return_source": _value(task.return_source),
            "task_type": _value(task.task_type),
            "ready_by_at": task.ready_by_at.isoformat() if task.ready_by_at else None,
            "item": {
                "client_id": item.client_id if item else None,
                "article_number": item.article_number if item else None,
                "sku": item.sku if item else None,
                "item_image": item_image,
            },
        }
    return payload


def serialize_case_conversation_message(
    message,
    *,
    case_id: str,
    created_by,
    images: list,
    mentions: list,
) -> dict:
    return {
        "case_id": case_id,
        "client_id": message.client_id,
        "message_seq": message.message_seq,
        "created_at": message.created_at.isoformat(),
        "created_by": serialize_user_light(created_by),
        "content": None if message.has_been_deleted else message.content,
        "plain_text": "" if message.has_been_deleted else message.plain_text,
        "has_been_edited": message.has_been_edited,
        "has_been_deleted": message.has_been_deleted,
        "updated_at": message.updated_at.isoformat() if message.updated_at else None,
        "images": images,
        "mentions": mentions,
    }
