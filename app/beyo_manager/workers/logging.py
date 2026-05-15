from __future__ import annotations

from beyo_manager.core.logging.config import log_event
from beyo_manager.core.logging.context import bind_execution_context


def bind_worker_context(worker_name: str) -> tuple[str, str]:
    execution_id, worker_id = bind_execution_context(worker_id=worker_name)
    log_event("worker.context.bound", execution_id=execution_id, worker_id=worker_id)
    return execution_id, worker_id
