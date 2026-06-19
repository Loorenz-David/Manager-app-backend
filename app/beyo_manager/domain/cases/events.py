from enum import StrEnum

from beyo_manager.domain.cases.enums import CaseStateEnum


class CaseEvent(StrEnum):
    CREATED = "case:created"
    UPDATED = "case:updated"
    DELETED = "case:deleted"
    STATE_CHANGED = "case:state-changed"
    PARTICIPANT_ADDED = "case:participant-added"
    PARTICIPANT_REMOVED = "case:participant-removed"
    CONVERSATION_CREATED = "case:conversation-created"
    UNREAD_UPDATED = "case:unread-updated"


class ConversationMessageEvent(StrEnum):
    CREATED = "conversation:message-created"
    EDITED = "conversation:message-edited"
    DELETED = "conversation:message-deleted"


def case_state_extra(new_state: CaseStateEnum) -> dict:
    return {"new_state": new_state.value}


def conversation_message_extra(message_seq: int) -> dict:
    return {"message_seq": message_seq}
