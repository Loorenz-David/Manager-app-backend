from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ReplayMetadata:
    replay_id: str
    source: str
    started_at: str
    dry_run: bool


@dataclass(frozen=True)
class ReplayResult:
    replay_id: str
    processed: int
    skipped: int
    failed: int


def new_replay_metadata(replay_id: str, source: str, dry_run: bool) -> ReplayMetadata:
    return ReplayMetadata(
        replay_id=replay_id,
        source=source,
        started_at=datetime.now(timezone.utc).isoformat(),
        dry_run=dry_run,
    )
