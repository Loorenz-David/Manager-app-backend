from beyo_manager.sockets import get_sio
from beyo_manager.sockets.handlers import (
    _handle_connect,
    _handle_disconnect,
    _handle_leave_entity,
    _handle_view_entity,
)


def register_socket_handlers() -> None:
    sio = get_sio()
    sio.on("connect", handler=_handle_connect)
    sio.on("disconnect", handler=_handle_disconnect)
    sio.on("view_entity", handler=_handle_view_entity)
    sio.on("leave_entity", handler=_handle_leave_entity)
