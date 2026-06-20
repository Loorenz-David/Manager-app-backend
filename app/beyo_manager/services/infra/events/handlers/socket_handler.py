import logging

from beyo_manager.services.infra.events.domain_event import (
    BatchWorkspaceEvent,
    ConversationRoomEvent,
    UserEvent,
    WorkspaceEvent,
)
from beyo_manager.services.infra.events.realtime_push import (
    push_to_conversation,
    push_to_user,
    push_workspace_batch,
    push_workspace_event_items,
    push_workspace_refresh,
)

logger = logging.getLogger(__name__)


async def handle(event) -> None:
    """Route domain events to the correct socket room.
    ConversationRoomEvent is checked first (most specific).
    """
    if isinstance(event, ConversationRoomEvent):
        logger.info(
            "[socket_handler] ConversationRoomEvent | event=%s room=conversation:%s client_id=%s",
            event.event_name,
            event.conversation_id,
            event.client_id,
        )
        await push_to_conversation(
            event.conversation_id,
            event.event_name,
            {"client_id": event.client_id, **event.extra},
        )
    elif isinstance(event, BatchWorkspaceEvent):
        logger.info(
            "[socket_handler] BatchWorkspaceEvent | event=%s room=workspace:%s count=%d",
            event.event_name,
            event.workspace_id,
            len(event.items),
        )
        await push_workspace_event_items(event.workspace_id, event.event_name, event.items)
    elif isinstance(event, WorkspaceEvent):
        if "ids" in event.extra:
            logger.info(
                "[socket_handler] WorkspaceEvent(batch) | event=%s room=workspace:%s",
                event.event_name,
                event.workspace_id,
            )
            await push_workspace_batch(event.workspace_id, event.event_name, event.extra["ids"])
        else:
            logger.info(
                "[socket_handler] WorkspaceEvent | event=%s room=workspace:%s client_id=%s",
                event.event_name,
                event.workspace_id,
                event.client_id,
            )
            await push_workspace_refresh(
                event.workspace_id,
                event.event_name,
                {"client_id": event.client_id, **event.extra},
            )
    elif isinstance(event, UserEvent):
        logger.info(
            "[socket_handler] UserEvent | event=%s room=user:%s client_id=%s",
            event.event_name,
            event.user_id,
            event.client_id,
        )
        await push_to_user(
            event.user_id,
            event.event_name,
            {"client_id": event.client_id, **event.extra},
        )
