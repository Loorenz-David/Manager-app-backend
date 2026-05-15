from dataclasses import dataclass


@dataclass
class NotificationResult:
    client_id:         str
    notification_type: str
    title:             str
    body:              str
    entity_type:       str | None
    entity_client_id:  str | None
    read_at:           str | None
    created_at:        str
