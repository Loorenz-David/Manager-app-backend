from beyo_manager.core.logging.config import log_event


def run_reset_db(confirm: bool, dry_run: bool = True) -> None:
    if not confirm and not dry_run:
        raise RuntimeError("Refusing destructive reset without confirm=True")
    log_event("ops.reset_db", confirm=confirm, dry_run=dry_run)
