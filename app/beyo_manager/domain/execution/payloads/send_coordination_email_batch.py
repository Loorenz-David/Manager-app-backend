from dataclasses import dataclass


@dataclass(frozen=True)
class SendCoordinationEmailBatchPayload:
    """Payload for SEND_COORDINATION_EMAIL_BATCH tasks."""

    workspace_id: str
    connection_client_id: str
    thread_ids: list[str]
