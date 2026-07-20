"""One-time manual Connecteam CSV user-ID mapping; dry-run is the default.

The script reads only the owner-provided CSV. It never calls Connecteam, reads an
API key, schedules itself, or creates users, profiles, shifts, or time records.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy.exc import SQLAlchemyError

from beyo_manager.core.logging.config import log_event
from beyo_manager.domain.connecteam.user_csv_rows import (
    ConnecteamCsvError,
    read_connecteam_users_csv,
)
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.services.commands.connecteam.map_connecteam_user_ids import (
    map_connecteam_user_ids,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)
DEFAULT_CSV_PATH = Path("scripts/connecteam/connecteam_users.csv")


def _validate_flags(*, dry_run: bool, execute: bool, apply: bool) -> bool:
    if execute and apply:
        raise ValueError("--execute and --apply are aliases; pass only one.")
    if dry_run and (execute or apply):
        raise ValueError("--dry-run is mutually exclusive with --execute/--apply.")
    return execute or apply


def _format_report(report) -> None:
    typer.echo(
        "connecteam_user_mapping | "
        f"rows={len(report.rows)} | applied={report.applied} | "
        f"identity_conflicts={report.identity_conflicts_present}"
    )
    for status, count in report.status_counts.items():
        if count:
            typer.echo(f"  {status}: {count}")
    typer.echo("user_id | external_name | internal_username | status | detail")
    typer.echo("-" * 92)
    for row in report.rows:
        typer.echo(
            f"{row.user_id} | {row.external_full_name or '<invalid>'} | "
            f"{row.internal_username or '<none>'} | {row.status.value} | {row.detail or ''}"
        )


def _write_json(report, output: str | None) -> None:
    if output is None:
        return
    Path(output).write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def _run(*, path: Path, apply: bool, workspace_id: str | None, output: str | None) -> int:
    # Parse before init_db so file errors open no database session.
    csv_users = read_connecteam_users_csv(path)
    log_event("connecteam_users_csv_loaded", provider="connecteam", row_count=len(csv_users))
    await init_db()
    try:
        async for session in get_db_session():
            report = await map_connecteam_user_ids(
                session,
                csv_users=csv_users,
                apply=apply,
                workspace_id=workspace_id,
            )
            report = replace(report, source_file=str(path))
            _write_json(report, output)
            _format_report(report)
            if apply and report.identity_conflicts_present:
                return 2
            return 0
    finally:
        await close_db()


@app.command("map-connecteam-user-ids")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Review without writing; this is the default.")] = False,
    execute: Annotated[bool, typer.Option("--execute", help="Apply conflict-free mappings.")] = False,
    apply: Annotated[bool, typer.Option("--apply", help="Alias for --execute.")] = False,
    file: Annotated[Path, typer.Option("--file", help="CSV path; defaults to scripts/connecteam/connecteam_users.csv.")] = DEFAULT_CSV_PATH,
    workspace_id: Annotated[str | None, typer.Option("--workspace-id", help="Limit eligible profiles to one workspace.")] = None,
    output: Annotated[str | None, typer.Option("--output", help="Write the complete report as JSON.")] = None,
) -> None:
    """Map existing users from the owner-provided CSV, once and manually."""
    try:
        write_requested = _validate_flags(dry_run=dry_run, execute=execute, apply=apply)
        exit_code = asyncio.run(
            _run(path=file, apply=write_requested, workspace_id=workspace_id, output=output)
        )
    except SQLAlchemyError as exc:
        log_event("connecteam_user_mapping_failed", provider="connecteam")
        typer.echo("ERROR: Connecteam user mapping database operation failed.", err=True)
        raise typer.Exit(1) from exc
    except (ConnecteamCsvError, ValueError, OSError, RuntimeError) as exc:
        log_event("connecteam_user_mapping_failed", provider="connecteam")
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(1) from exc
    if exit_code:
        raise typer.Exit(exit_code)


if __name__ == "__main__":
    app()
