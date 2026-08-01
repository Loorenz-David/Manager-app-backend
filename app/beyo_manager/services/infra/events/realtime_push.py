"""Deliver an event to a socket room, from whichever process is asking.

Two transports, one address space — `rooms.py` names the rooms for both, so the paths cannot
drift on who receives what.

- **API process** — holds the websocket connections. `manager` hands the message straight to
  its own clients and publishes to Redis for any other API instance. No round trip.
- **Everything else** — a worker holds no connections and cannot reach a client at all. It
  publishes to the same Redis channel the API's socket server subscribes to, and the API
  forwards. This is why a worker cannot simply "emit": there is nothing there to emit *to*.

Callers never choose. `owns_socket_server()` is set once by `create_app()`, so a service used
by both a request and a background job emits identically from either.
"""

from beyo_manager.sockets import owns_socket_server
from beyo_manager.sockets.manager import manager
from beyo_manager.sockets.worker_emitter import (
    emit_to_conversation_room,
    emit_to_user_room,
    emit_to_workspace_room,
)


async def push_workspace_refresh(workspace_id: str, event_name: str, payload: dict) -> None:
    if owns_socket_server():
        await manager.broadcast_to_room(manager.workspace_room(workspace_id), event_name, payload)
        return
    await emit_to_workspace_room(workspace_id=workspace_id, event=event_name, payload=payload)


async def push_workspace_batch(workspace_id: str, event_name: str, ids: list) -> None:
    await push_workspace_refresh(workspace_id, event_name, {"ids": ids})


async def push_workspace_event_items(workspace_id: str, event_name: str, items: list[dict]) -> None:
    if owns_socket_server():
        await manager.broadcast_items_to_room(
            manager.workspace_room(workspace_id), event_name, items
        )
        return
    await emit_to_workspace_room(workspace_id=workspace_id, event=event_name, payload=items)


async def push_to_conversation(conversation_id: str, event_name: str, payload: dict) -> None:
    if owns_socket_server():
        await manager.broadcast_to_room(
            manager.conversation_room(conversation_id), event_name, payload
        )
        return
    await emit_to_conversation_room(
        conversation_client_id=conversation_id, event=event_name, payload=payload
    )


async def push_to_user(user_id: str, event_name: str, payload: dict) -> None:
    if owns_socket_server():
        await manager.send_to_user(user_id, event_name, payload)
        return
    await emit_to_user_room(user_id=user_id, event=event_name, payload=payload)
