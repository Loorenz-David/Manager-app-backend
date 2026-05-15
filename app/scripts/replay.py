from __future__ import annotations

import typer

from beyo_manager.core.logging.config import configure_logging, log_event

cli = typer.Typer(help="Operational replay hooks")


@cli.command("events")
def replay_events(limit: int = 50, dry_run: bool = True) -> None:
    configure_logging()
    log_event("replay.events.start", limit=limit, dry_run=dry_run)


@cli.command("jobs")
def replay_jobs(limit: int = 50, dry_run: bool = True) -> None:
    configure_logging()
    log_event("replay.jobs.start", limit=limit, dry_run=dry_run)


@cli.command("webhooks")
def replay_webhooks(limit: int = 50, dry_run: bool = True) -> None:
    configure_logging()
    log_event("replay.webhooks.start", limit=limit, dry_run=dry_run)


if __name__ == "__main__":
    cli()
