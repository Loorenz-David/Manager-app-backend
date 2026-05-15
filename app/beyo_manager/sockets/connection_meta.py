from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ConnectionMeta:
    user_id: str
    workspace_id: str
    username: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    entity_views: set[tuple[str, str]] = field(default_factory=set)
