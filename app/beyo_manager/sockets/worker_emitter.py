from __future__ import annotations

import asyncio

import socketio

from beyo_manager.config import settings
from beyo_manager.sockets.rooms import conversation_room, user_room, workspace_room

_worker_socket_manager: socketio.AsyncRedisManager | None = None
_manager_loop: asyncio.AbstractEventLoop | None = None


def _get_worker_socket_manager() -> socketio.AsyncRedisManager:
    """One manager per event loop, not one per process.

    The manager owns an asyncio Redis connection, and an asyncio connection belongs to the
    loop that opened it — reusing it under a different loop raises `Event loop is closed` at
    the first publish. A long-running process has exactly one loop for its lifetime, so this
    hands back the same manager every time and behaves as a plain singleton. Loops only churn
    under test, which is the one place the process-wide cache was wrong.
    """
    global _worker_socket_manager, _manager_loop
    loop = asyncio.get_running_loop()
    if _worker_socket_manager is None or _manager_loop is not loop:
        # The previous manager's connection is dropped rather than closed: its loop is gone,
        # so there is nothing left to close it from.
        _worker_socket_manager = socketio.AsyncRedisManager(
            settings.redis_url,
            write_only=True,
        )
        _manager_loop = loop
    return _worker_socket_manager


# `payload` is a list for the batch events that carry one entry per changed entity —
# the same shape `push_workspace_event_items` emits from the API process.
async def emit_to_room(*, room: str, event: str, payload: dict | list) -> None:
    """Publish to a named room. Room names come from `rooms.py`, shared with the manager."""
    await _get_worker_socket_manager().emit(event, payload, room=room)


async def emit_to_user_room(*, user_id: str, event: str, payload: dict | list) -> None:
    await emit_to_room(room=user_room(user_id), event=event, payload=payload)


async def emit_to_workspace_room(*, workspace_id: str, event: str, payload: dict | list) -> None:
    await emit_to_room(room=workspace_room(workspace_id), event=event, payload=payload)


async def emit_to_conversation_room(
    *, conversation_client_id: str, event: str, payload: dict | list
) -> None:
    await emit_to_room(
        room=conversation_room(conversation_client_id), event=event, payload=payload
    )
