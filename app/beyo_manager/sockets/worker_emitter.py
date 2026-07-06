from __future__ import annotations

import socketio

from beyo_manager.config import settings
from beyo_manager.sockets.rooms import user_room

_worker_socket_manager: socketio.AsyncRedisManager | None = None


def _get_worker_socket_manager() -> socketio.AsyncRedisManager:
    global _worker_socket_manager
    if _worker_socket_manager is None:
        _worker_socket_manager = socketio.AsyncRedisManager(
            settings.redis_url,
            write_only=True,
        )
    return _worker_socket_manager


async def emit_to_user_room(*, user_id: str, event: str, payload: dict) -> None:
    await _get_worker_socket_manager().emit(
        event,
        payload,
        room=user_room(user_id),
    )
