import logging

from beyo_manager.sockets import get_sio
from beyo_manager.sockets.connection_meta import ConnectionMeta
from beyo_manager.sockets.rooms import conversation_room, user_room, workspace_room

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, ConnectionMeta] = {}

    async def connect(self, sid: str, meta: ConnectionMeta) -> None:
        self._connections[sid] = meta
        sio = get_sio()
        await sio.enter_room(sid, self.user_room(meta.user_id))
        await sio.enter_room(sid, self.workspace_room(meta.workspace_id))
        logger.info(
            "[manager] connect | sid=%s user=%s joined rooms: %s %s",
            sid,
            meta.user_id,
            self.user_room(meta.user_id),
            self.workspace_room(meta.workspace_id),
        )

    async def disconnect(self, sid: str) -> ConnectionMeta | None:
        meta = self._connections.pop(sid, None)
        if meta:
            sio = get_sio()
            await sio.leave_room(sid, self.user_room(meta.user_id))
            await sio.leave_room(sid, self.workspace_room(meta.workspace_id))
        return meta

    async def join_conversation(self, sid: str, conversation_client_id: str) -> None:
        room = self.conversation_room(conversation_client_id)
        logger.info("[manager] join_conversation | sid=%s room=%s", sid, room)
        await get_sio().enter_room(sid, room)

    async def leave_conversation(self, sid: str, conversation_client_id: str) -> None:
        room = self.conversation_room(conversation_client_id)
        logger.info("[manager] leave_conversation | sid=%s room=%s", sid, room)
        await get_sio().leave_room(sid, room)

    async def send_to_user(self, user_id: str, event: str, payload: dict) -> None:
        room = self.user_room(user_id)
        logger.info("[manager] send_to_user | event=%s room=%s payload=%s", event, room, payload)
        await get_sio().emit(event, payload, room=room)

    async def broadcast_to_room(self, room: str, event: str, payload: dict) -> None:
        logger.info("[manager] broadcast_to_room | event=%s room=%s payload=%s", event, room, payload)
        await get_sio().emit(event, payload, room=room)

    async def broadcast_items_to_room(self, room: str, event: str, items: list[dict]) -> None:
        logger.info("[manager] broadcast_items_to_room | event=%s room=%s count=%d", event, room, len(items))
        await get_sio().emit(event, items, room=room)

    def get(self, sid: str) -> ConnectionMeta | None:
        return self._connections.get(sid)

    def is_user_connected(self, user_id: str) -> bool:
        return any(meta.user_id == user_id for meta in self._connections.values())

    @staticmethod
    def user_room(user_id: str) -> str:
        return user_room(user_id)

    @staticmethod
    def workspace_room(workspace_id: str) -> str:
        return workspace_room(workspace_id)

    @staticmethod
    def conversation_room(conversation_client_id: str) -> str:
        return conversation_room(conversation_client_id)


manager = ConnectionManager()
