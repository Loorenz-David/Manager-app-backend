from beyo_manager.sockets import sio
from beyo_manager.sockets.connection_meta import ConnectionMeta


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, ConnectionMeta] = {}

    async def connect(self, sid: str, meta: ConnectionMeta) -> None:
        self._connections[sid] = meta
        await sio.enter_room(sid, self.user_room(meta.user_id))
        await sio.enter_room(sid, self.workspace_room(meta.workspace_id))

    async def disconnect(self, sid: str) -> ConnectionMeta | None:
        meta = self._connections.pop(sid, None)
        if meta:
            await sio.leave_room(sid, self.user_room(meta.user_id))
            await sio.leave_room(sid, self.workspace_room(meta.workspace_id))
        return meta

    async def join_conversation(self, sid: str, conversation_client_id: str) -> None:
        await sio.enter_room(sid, self.conversation_room(conversation_client_id))

    async def leave_conversation(self, sid: str, conversation_client_id: str) -> None:
        await sio.leave_room(sid, self.conversation_room(conversation_client_id))

    async def send_to_user(self, user_id: str, event: str, payload: dict) -> None:
        await sio.emit(event, payload, room=self.user_room(user_id))

    async def broadcast_to_room(self, room: str, event: str, payload: dict) -> None:
        await sio.emit(event, payload, room=room)

    def get(self, sid: str) -> ConnectionMeta | None:
        return self._connections.get(sid)

    @staticmethod
    def user_room(user_id: str) -> str:
        return f"user:{user_id}"

    @staticmethod
    def workspace_room(workspace_id: str) -> str:
        return f"workspace:{workspace_id}"

    @staticmethod
    def conversation_room(conversation_client_id: str) -> str:
        return f"conversation:{conversation_client_id}"


manager = ConnectionManager()
