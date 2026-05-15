from beyo_manager.core.logging.config import log_event


def run_seed(dry_run: bool = False) -> None:
    log_event("ops.seed", dry_run=dry_run)
