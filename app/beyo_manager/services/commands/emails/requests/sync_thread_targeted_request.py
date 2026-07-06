from pydantic import BaseModel, Field


class SyncThreadsBatchTargetedRequest(BaseModel):
    connection_client_id: str | None = None
    thread_client_ids: list[str] = Field(default_factory=list)
    entity_type: str | None = None
    entity_client_ids: list[str] = Field(default_factory=list)
    major_entity_type: str | None = None
    major_entity_client_id: str | None = None
    max_threads: int = Field(default=50, ge=1, le=50)
