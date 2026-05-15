from beyo_manager.core.logging.config import log_event


def run_worker_control(action: str) -> None:
    log_event("ops.worker_control", action=action)
