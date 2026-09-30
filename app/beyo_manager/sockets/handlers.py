import logging

import jwt
from socketio import exceptions as socketio_exceptions

from beyo_manager.config import settings
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.errors.availability import (
    AUTH_UNAVAILABLE_CODE,
    AUTH_UNAVAILABLE_RETRY_AFTER_SECONDS,
)
from beyo_manager.models.database import get_db_session
from beyo_manager.services.infra.activity.human_activity import (
    SOURCE_SOCKET,
    record_human_activity,
)
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.auth import is_token_blocklisted
from beyo_manager.services.infra.presence import mark_left, mark_viewing
from beyo_manager.services.infra.presence.user_online_key import delete_user_online, set_user_online
from beyo_manager.sockets.connection_meta import ConnectionMeta
from beyo_manager.sockets.manager import manager


logger = logging.getLogger(__name__)


async def _handle_connect(sid: str, environ: dict, auth: dict | None = None):
    token = (auth or {}).get("token") or _query_token(environ)
    if not token:
        return False
    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return False
    jti = claims.get("jti")
    if jti:
        try:
            revoked = await is_token_blocklisted(jti)
        except Exception as exc:
            # Still refused, but say why: the token may be valid, so the client
            # should retry, not sign out. python-socketio sends this to the client's
            # connect_error as {"message": "auth_unavailable", "data": {...}}.
            logger.warning(
                "auth.blocklist_unavailable | where=socket_connect exc_type=%s",
                type(exc).__name__,
                extra={"event_type": "auth.blocklist_unavailable", "service": "auth"},
            )
            raise socketio_exceptions.ConnectionRefusedError(
                AUTH_UNAVAILABLE_CODE,
                {
                    "code": AUTH_UNAVAILABLE_CODE,
                    "retry_after_seconds": AUTH_UNAVAILABLE_RETRY_AFTER_SECONDS,
                },
            ) from exc
        if revoked:
            return False
    user_id = claims.get("user_id", "")
    if not user_id:
        return False
    await manager.connect(
        sid,
        ConnectionMeta(
            user_id=user_id,
            workspace_id=claims.get("workspace_id", ""),
            username=claims.get("username", ""),
            app_scope=claims.get("app_scope", "") or "",
        ),
    )
    try:
        await set_user_online(user_id)
    except Exception:
        logger.warning("set_user_online failed for user_id=%s — connection allowed, user appears offline", user_id)
    return True


async def _handle_disconnect(sid: str, reason: str | None = None):
    meta = await manager.disconnect(sid)
    if meta:
        await _cleanup_presence(meta)
        if not manager.is_user_connected(meta.user_id):
            try:
                await delete_user_online(meta.user_id)
            except Exception:
                logger.warning("delete_user_online failed for user_id=%s", meta.user_id)


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
    await _record_socket_activity(meta)
    mark_viewing(entity_type.value, entity_client_id, meta.user_id)
    meta.entity_views.add((entity_type.value, entity_client_id))
    if entity_type == EntityType.CONVERSATION:
        await manager.join_conversation(sid, entity_client_id)
    async for session in get_db_session():
        await create_instant_task(
            session=session,
            task_type=TaskType.RECORD_VIEW_START,
            payload={"user_id": meta.user_id, "entity_type": entity_type.value, "entity_client_id": entity_client_id},
        )
        await session.commit()


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
    await _record_socket_activity(meta)
    mark_left(entity_type.value, entity_client_id, meta.user_id)
    meta.entity_views.discard((entity_type.value, entity_client_id))
    if entity_type == EntityType.CONVERSATION:
        await manager.leave_conversation(sid, entity_client_id)
    async for session in get_db_session():
        await create_instant_task(
            session=session,
            task_type=TaskType.RECORD_VIEW_END,
            payload={"user_id": meta.user_id, "entity_type": entity_type.value, "entity_client_id": entity_client_id},
        )
        await session.commit()


async def _record_socket_activity(meta: ConnectionMeta) -> None:
    # Opening or leaving an entity is a person navigating — a human event. Connect,
    # disconnect and transport pings are not. Throttled, bounded and never raising
    # (see human_activity); the guard is belt and braces so presence always proceeds.
    try:
        await record_human_activity(
            app_scope=meta.app_scope, source=SOURCE_SOCKET, user_id=meta.user_id
        )
    except Exception:
        logger.debug("socket human-activity recording raised", exc_info=True)


async def _cleanup_presence(meta: ConnectionMeta) -> None:
    async for session in get_db_session():
        for entity_type, entity_client_id in list(meta.entity_views):
            mark_left(entity_type, entity_client_id, meta.user_id)
            await create_instant_task(
                session=session,
                task_type=TaskType.RECORD_VIEW_END,
                payload={"user_id": meta.user_id, "entity_type": entity_type, "entity_client_id": entity_client_id},
            )
        await session.commit()


def _query_token(environ: dict) -> str | None:
    query = environ.get("QUERY_STRING", "")
    for part in query.split("&"):
        if part.startswith("token="):
            return part.removeprefix("token=")
    return None
