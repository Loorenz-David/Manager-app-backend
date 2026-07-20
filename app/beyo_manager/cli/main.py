from __future__ import annotations

import typer

from beyo_manager.operations.backfill import run_backfill
from beyo_manager.operations.cleanup import run_cleanup
from beyo_manager.operations.db import run_reset_db
from beyo_manager.operations.diagnostics import run_diagnostics
from beyo_manager.operations.inspect import run_inspect
from beyo_manager.operations.replay import run_replay
from beyo_manager.operations.seed import run_seed
from beyo_manager.operations.worker_control import run_worker_control
from beyo_manager.operations.connecteam_dead_letter import (
    list_dead_letters,
    purge_dead_letter,
    requeue_dead_letter,
)

cli = typer.Typer(help="Operational CLI")


@cli.command("seed")
def seed(dry_run: bool = False) -> None:
    run_seed(dry_run=dry_run)


@cli.command("inspect")
def inspect_runtime() -> None:
    run_inspect()


@cli.command("backfill")
def backfill(target: str, dry_run: bool = True) -> None:
    run_backfill(target=target, dry_run=dry_run)


@cli.command("cleanup")
def cleanup(target: str, dry_run: bool = True) -> None:
    run_cleanup(target=target, dry_run=dry_run)


@cli.command("replay")
def replay(source: str = "events", dry_run: bool = True) -> None:
    run_replay(source=source, dry_run=dry_run)


@cli.command("worker")
def worker_control(action: str) -> None:
    run_worker_control(action=action)


@cli.command("reset-db")
def reset_db(confirm: bool = False, dry_run: bool = True) -> None:
    run_reset_db(confirm=confirm, dry_run=dry_run)


@cli.command("diagnostics")
def diagnostics() -> None:
    run_diagnostics()


@cli.command("connecteam-dead-letter-list")
def connecteam_dead_letter_list(raw: bool = False) -> None:
    list_dead_letters(raw=raw)


@cli.command("connecteam-dead-letter-requeue")
def connecteam_dead_letter_requeue(task_client_id: str) -> None:
    requeue_dead_letter(task_client_id)


@cli.command("connecteam-dead-letter-purge")
def connecteam_dead_letter_purge(task_client_id: str, confirm: bool = False) -> None:
    purge_dead_letter(task_client_id, confirm=confirm)


if __name__ == "__main__":
    cli()
