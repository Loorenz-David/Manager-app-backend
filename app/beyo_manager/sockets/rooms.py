def user_room(user_id: str) -> str:
    return f"user:{user_id}"


def workspace_room(workspace_id: str) -> str:
    return f"workspace:{workspace_id}"


def conversation_room(conversation_client_id: str) -> str:
    return f"conversation:{conversation_client_id}"
