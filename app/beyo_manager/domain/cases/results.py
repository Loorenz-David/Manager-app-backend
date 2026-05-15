from dataclasses import dataclass, field
from typing import Any


@dataclass
class CaseResult:
    client_id: str
    state: str
    type_label: str | None
    participants_count: int
    conversations_count: int
    messages_count: int
    created_at: str
    created_by_id: str


@dataclass
class CaseLinkResult:
    client_id: str
    entity_type: str
    entity_client_id: str
    role: str
    created_at: str


@dataclass
class CaseParticipantResult:
    client_id: str
    user_id: str
    last_read_message_seq: int
    joined_at: str


@dataclass
class CaseConversationResult:
    client_id: str
    state: str
    messages_count: int
    last_message_seq: int
    created_at: str
    last_messages: list = field(default_factory=list)


@dataclass
class CaseConversationMessageResult:
    client_id: str
    message_seq: int
    content: list[Any] | dict[str, Any] | None
    plain_text: str
    has_been_edited: bool
    has_been_deleted: bool
    created_at: str
    created_by: dict | None = None
