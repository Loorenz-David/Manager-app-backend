from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplayEnvelope:
    source_id: str
    payload: dict
    replay_key: str


class ReplayHandlerProtocol:
    async def run(self, envelope: ReplayEnvelope, *, dry_run: bool) -> None:
        raise NotImplementedError
