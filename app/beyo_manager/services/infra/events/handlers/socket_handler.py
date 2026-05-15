from beyo_manager.services.infra.events.domain_event import (
    ConversationRoomEvent,
    UserEvent,
    WorkspaceEvent,
)
from beyo_manager.services.infra.events.realtime_push import (
    push_to_conversation,
    push_to_user,
    push_workspace_batch,
    push_workspace_refresh,
)


async def handle(event) -> None:
    """Route domain events to the correct socket room.
    ConversationRoomEvent is checked first (most specific).
    """
    if isinstance(event, ConversationRoomEvent):
        await push_to_conversation(
            event.conversation_id,
            event.event_name,
            {"client_id": event.client_id, **event.extra},
        )
    elif isinstance(event, WorkspaceEvent):
        if "ids" in event.extra:
            await push_workspace_batch(event.workspace_id, event.event_name, event.extra["ids"])
        else:
            await push_workspace_refresh(
                event.workspace_id,
                event.event_name,
                {"client_id": event.client_id, **event.extra},
            )
    elif isinstance(event, UserEvent):
        await push_to_user(
            event.user_id,
            event.event_name,
            {"client_id": event.client_id, **event.extra},
        )
