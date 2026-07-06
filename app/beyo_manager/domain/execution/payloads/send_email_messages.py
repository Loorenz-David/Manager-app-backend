from dataclasses import dataclass


@dataclass(frozen=True)
class SendEmailMessagesPayload:
    workspace_id: str
    connection_client_id: str
    message_ids: list[str]
    request_kind: str
    requested_by_user_id: str | None = None
