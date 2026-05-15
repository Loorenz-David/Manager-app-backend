from beyo_manager.core.logging.config import log_event


def run_backfill(target: str, dry_run: bool = True) -> None:
    log_event("ops.backfill", target=target, dry_run=dry_run)
