from __future__ import annotations

from beyo_manager.core.logging.config import log_event


async def execute_replay(handler, envelope, *, dry_run: bool) -> bool:
    try:
        await handler.run(envelope, dry_run=dry_run)
        log_event("replay.item.success", replay_key=envelope.replay_key, dry_run=dry_run)
        return True
    except Exception as exc:
        log_event("replay.item.failed", replay_key=envelope.replay_key, error=str(exc), dry_run=dry_run)
        return False
