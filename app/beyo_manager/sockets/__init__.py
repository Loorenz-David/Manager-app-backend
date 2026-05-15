import socketio

from beyo_manager.config import settings

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.frontend_origins,
)
socket_app = None
