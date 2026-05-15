import jwt

from beyo_manager.config import settings
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.presence import mark_left, mark_viewing
from beyo_manager.sockets.connection_meta import ConnectionMeta
from beyo_manager.sockets.manager import manager


async def _handle_connect(sid: str, environ: dict, auth: dict | None = None):
    token = (auth or {}).get("token") or _query_token(environ)
    if not token:
        return False
    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return False
    await manager.connect(
        sid,
        ConnectionMeta(
            user_id=claims.get("user_id", ""),
            workspace_id=claims.get("workspace_id", ""),
            username=claims.get("username", ""),
        ),
    )
    return True


async def _handle_disconnect(sid: str):
    meta = await manager.disconnect(sid)
    if meta:
        _cleanup_presence(meta)


async def _handle_view_entity(sid: str, data: dict):
    meta = manager.get(sid)
    if not meta:
        return
    try:
        entity_type = EntityType(str(data.get("entity_type", "")))
    except ValueError:
        return
    entity_client_id = str(data.get("entity_client_id", ""))
    if not entity_client_id:
        return
    mark_viewing(entity_type.value, entity_client_id, meta.user_id)
    meta.entity_views.add((entity_type.value, entity_client_id))
    create_instant_task(TaskType.RECORD_VIEW_START, {"user_id": meta.user_id, "entity_type": entity_type.value, "entity_client_id": entity_client_id})
    if entity_type == EntityType.CONVERSATION:
        await manager.join_conversation(sid, entity_client_id)


async def _handle_leave_entity(sid: str, data: dict):
    meta = manager.get(sid)
    if not meta:
        return
    try:
        entity_type = EntityType(str(data.get("entity_type", "")))
    except ValueError:
        return
    entity_client_id = str(data.get("entity_client_id", ""))
    if not entity_client_id:
        return
    mark_left(entity_type.value, entity_client_id, meta.user_id)
    meta.entity_views.discard((entity_type.value, entity_client_id))
    create_instant_task(TaskType.RECORD_VIEW_END, {"user_id": meta.user_id, "entity_type": entity_type.value, "entity_client_id": entity_client_id})
    if entity_type == EntityType.CONVERSATION:
        await manager.leave_conversation(sid, entity_client_id)


def _cleanup_presence(meta: ConnectionMeta) -> None:
    for entity_type, entity_client_id in list(meta.entity_views):
        mark_left(entity_type, entity_client_id, meta.user_id)
        create_instant_task(TaskType.RECORD_VIEW_END, {"user_id": meta.user_id, "entity_type": entity_type, "entity_client_id": entity_client_id})


def _query_token(environ: dict) -> str | None:
    query = environ.get("QUERY_STRING", "")
    for part in query.split("&"):
        if part.startswith("token="):
            return part.removeprefix("token=")
    return None
