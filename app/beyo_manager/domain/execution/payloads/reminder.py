from dataclasses import dataclass


@dataclass(frozen=True)
class ReminderPayload:
    """Payload for DELAYED_REMINDER and RECURRING_REMINDER tasks."""
    workspace_id:     str
    user_id:          str
    entity_client_id: str
    message:          str = "You have a reminder."
