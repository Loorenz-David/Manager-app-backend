import enum


class NotificationType(str, enum.Enum):
    """str enum — values stored directly in String column, no migration on extension."""
    # Case domain
    CASE_MESSAGE           = "case:message"
    CASE_STATE_CHANGED     = "case:state-changed"
    CASE_PARTICIPANT_ADDED = "case:participant-added"
    # Add more notification types here as domains expand.
