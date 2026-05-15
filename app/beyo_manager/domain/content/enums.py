from enum import StrEnum


class InputContentTypeEnum(StrEnum):
    TEXT = "text"
    MENTION = "mention"
    LABEL = "label"
    LINK = "link"


class ContentMentionLinkEntityTypeEnum(StrEnum):
    CASE_CONVERSATION_MESSAGE = "case_conversation_message"
    TASK_DETAILS_MENTION = "task_details_mention"
    TASK_NOTE_MENTION = "task_note_mention"
