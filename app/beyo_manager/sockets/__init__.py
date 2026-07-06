import socketio

from beyo_manager.config import settings

sio: socketio.AsyncServer | None = None
socket_manager: socketio.AsyncRedisManager | None = None
socket_app = None


def get_socket_manager() -> socketio.AsyncRedisManager:
    global socket_manager
    if socket_manager is None:
        socket_manager = socketio.AsyncRedisManager(settings.redis_url)
    return socket_manager


def get_sio() -> socketio.AsyncServer:
    global sio
    if sio is None:
        sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=settings.frontend_origins,
            client_manager=get_socket_manager(),
        )
    return sio
