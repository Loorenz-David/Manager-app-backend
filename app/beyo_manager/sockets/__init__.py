import socketio

from beyo_manager.config import settings

sio: socketio.AsyncServer | None = None
socket_manager: socketio.AsyncRedisManager | None = None
socket_app = None

# Does THIS process hold the websocket connections?
#
# Only the API process does — it is the one clients dial. Workers run the same code but
# have no connections of their own, so they cannot deliver to a client directly and must
# publish to Redis for the API process to forward. `realtime_push` reads this to pick the
# right transport. Set explicitly by `create_app()` rather than inferred from whether `sio`
# happens to exist, so a worker that touches the socket module for some unrelated reason
# cannot accidentally look like a server.
_owns_socket_server = False


def mark_socket_server_process() -> None:
    global _owns_socket_server
    _owns_socket_server = True


def owns_socket_server() -> bool:
    return _owns_socket_server


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
