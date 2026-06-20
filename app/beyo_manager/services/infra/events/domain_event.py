from dataclasses import dataclass, field


@dataclass(kw_only=True)
class Event:
    """Base event. All domain events inherit from this."""
    event_name: str
    client_id:  str
    extra:      dict = field(default_factory=dict)


@dataclass(kw_only=True)
class BatchWorkspaceEvent:
    """Broadcast a list payload to all users in a workspace room."""
    event_name: str
    workspace_id: str
    items: list[dict]


@dataclass(kw_only=True)
class WorkspaceEvent(Event):
    """Broadcast to all users connected to a workspace room."""
    workspace_id: str


@dataclass(kw_only=True)
class UserEvent(Event):
    """Push to a specific user's room only."""
    user_id: str


@dataclass(kw_only=True)
class ConversationRoomEvent(Event):
    """Broadcast to all users currently viewing a specific conversation."""
    conversation_id: str
    workspace_id:    str
