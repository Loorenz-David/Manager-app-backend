from beyo_manager.services.infra.events.domain_event import (
    ConversationRoomEvent,
    UserEvent,
    WorkspaceEvent,
)


def build_workspace_event(
    entity,
    event_name: str,
    *,
    workspace_id: str | None = None,
    extra: dict | None = None,
) -> WorkspaceEvent:
    return WorkspaceEvent(
        event_name=event_name,
        client_id=entity.client_id,
        workspace_id=workspace_id or getattr(entity, "workspace_id", None),
        extra=extra or {},
    )


def build_user_event(
    user_id:    str,
    event_name: str,
    client_id:  str,
    extra: dict | None = None,
) -> UserEvent:
    return UserEvent(
        event_name=event_name,
        client_id=client_id,
        user_id=user_id,
        extra=extra or {},
    )


def build_conversation_event(
    entity,
    event_name:      str,
    *,
    conversation_id: str,
    workspace_id:    str,
    extra: dict | None = None,
) -> ConversationRoomEvent:
    return ConversationRoomEvent(
        event_name=event_name,
        client_id=entity.client_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        extra=extra or {},
    )
