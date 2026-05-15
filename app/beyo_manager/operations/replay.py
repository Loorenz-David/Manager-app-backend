from beyo_manager.core.logging.config import log_event


def run_replay(source: str, dry_run: bool = True) -> None:
    log_event("ops.replay", source=source, dry_run=dry_run)
