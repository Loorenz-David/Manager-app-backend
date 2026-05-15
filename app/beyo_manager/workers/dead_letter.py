from __future__ import annotations

from beyo_manager.core.logging.config import log_event


def send_to_dead_letter(task_type: str, payload: dict, reason: str) -> None:
    log_event(
        "worker.dead_letter",
        task_type=task_type,
        reason=reason,
        payload_size=len(str(payload)),
    )
