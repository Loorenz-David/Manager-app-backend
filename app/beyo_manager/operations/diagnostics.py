from beyo_manager.core.logging.config import log_event


def run_diagnostics() -> None:
    log_event("ops.diagnostics")
