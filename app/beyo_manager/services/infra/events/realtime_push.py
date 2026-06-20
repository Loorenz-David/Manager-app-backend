from beyo_manager.sockets.manager import manager


async def push_workspace_refresh(workspace_id: str, event_name: str, payload: dict) -> None:
    await manager.broadcast_to_room(manager.workspace_room(workspace_id), event_name, payload)


async def push_workspace_batch(workspace_id: str, event_name: str, ids: list) -> None:
    await manager.broadcast_to_room(
        manager.workspace_room(workspace_id), event_name, {"ids": ids}
    )


async def push_workspace_event_items(workspace_id: str, event_name: str, items: list[dict]) -> None:
    await manager.broadcast_items_to_room(manager.workspace_room(workspace_id), event_name, items)


async def push_to_conversation(conversation_id: str, event_name: str, payload: dict) -> None:
    await manager.broadcast_to_room(
        manager.conversation_room(conversation_id), event_name, payload
    )


async def push_to_user(user_id: str, event_name: str, payload: dict) -> None:
    await manager.send_to_user(user_id, event_name, payload)
