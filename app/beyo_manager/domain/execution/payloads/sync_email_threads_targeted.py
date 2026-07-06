from dataclasses import dataclass, field


@dataclass(frozen=True)
class SyncEmailThreadsTargetedPayload:
    workspace_id: str
    requested_by_user_id: str
    role_name: str
    connection_client_id: str | None = None
    thread_client_ids: list[str] = field(default_factory=list)
    entity_type: str | None = None
    entity_client_ids: list[str] = field(default_factory=list)
    major_entity_type: str | None = None
    major_entity_client_id: str | None = None
    max_threads: int = 50
