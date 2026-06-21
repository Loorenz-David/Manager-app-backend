from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationPayload:
    """Payload for CREATE_NOTIFICATIONS and NOTIFICATION tasks."""
    notification_type: str
    user_ids:          list[str]
    title:             str
    body:              str
    entity_type:       str | None = None
    entity_client_id:  str | None = None
    task_client_id:    str | None = None
    exclude_viewing:   list[dict] | None = None
