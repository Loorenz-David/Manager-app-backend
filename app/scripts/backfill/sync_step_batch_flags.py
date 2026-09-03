"""Audit and repair `task_steps.allows_batch_working` drift against the owning section.

The per-step flag is a snapshot taken at step creation, and it — not the section
column — is what the backend enforces (the one-active-step auto-pause guard, the
batch endpoint's admission check, the resume card's batch mode). A writer that
flips `working_sections.allows_batch_working` without re-stamping the existing
steps leaves those steps enforcing the old rule forever, while the workers app
renders the batch UI from the section. `_sync_step_batch_flag` now closes that gap
at both writers (`edit_working_section` and the bootstrap re-seed), so the re-seed
is self-healing; this script exists for environments where running a full bootstrap
to correct a handful of rows is not wanted, and as a standing drift audit.

Dry-run by default — it prints the per-section drift table and commits nothing.
Use ``--execute`` to apply.

TERMINAL STEPS ARE NEVER TOUCHED, by this script or by the helper. On a closed step
the flag is the historical record of the rule it was worked under, and the analytics
concurrency sweep reads it as such: a batchable interval's time is divided across its
overlaps, a non-batch interval's is not. Re-stamping closed steps would rewrite past
worked-time attribution.

    python -m scripts.backfill.sync_step_batch_flags                # audit
    python -m scripts.backfill.sync_step_batch_flags --execute      # repair
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Annotated

import typer
from sqlalchemy import func, select

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.working_sections._sync_step_batch_flag import (
    sync_step_batch_flag_for_section_in_session,
)


app = typer.Typer(add_completion=False, no_args_is_help=True)


@dataclass(frozen=True)
class SectionDrift:
    workspace_id: str
    section_id: str
    name: str
    section_flag: bool
    open_drifted: int
    closed_drifted: int


async def collect_drift(
    session,
    *,
    workspace_id: str | None,
    section_id: str | None,
) -> list[SectionDrift]:
    """Sections whose steps disagree with the section's own flag.

    `open_drifted` is what the repair touches; `closed_drifted` is reported for
    visibility only and is deliberately left alone.
    """
    is_open = TaskStep.state.not_in(TERMINAL_STEP_STATES)

    statement = (
        select(
            WorkingSection.workspace_id,
            WorkingSection.client_id,
            WorkingSection.name,
            WorkingSection.allows_batch_working,
            func.count()
            .filter(
                is_open,
                TaskStep.allows_batch_working != WorkingSection.allows_batch_working,
            )
            .label("open_drifted"),
            func.count()
            .filter(
                TaskStep.state.in_(TERMINAL_STEP_STATES),
                TaskStep.allows_batch_working != WorkingSection.allows_batch_working,
            )
            .label("closed_drifted"),
        )
        .join(
            TaskStep,
            (TaskStep.working_section_id == WorkingSection.client_id)
            & (TaskStep.workspace_id == WorkingSection.workspace_id)
            & (TaskStep.is_deleted.is_(False)),
        )
        .where(WorkingSection.is_deleted.is_(False))
        .group_by(
            WorkingSection.workspace_id,
            WorkingSection.client_id,
            WorkingSection.name,
            WorkingSection.allows_batch_working,
        )
        .order_by(WorkingSection.name)
    )

    if workspace_id is not None:
        statement = statement.where(WorkingSection.workspace_id == workspace_id)
    if section_id is not None:
        statement = statement.where(WorkingSection.client_id == section_id)

    rows = (await session.execute(statement)).all()
    return [
        SectionDrift(
            workspace_id=row[0],
            section_id=row[1],
            name=row[2],
            section_flag=row[3],
            open_drifted=row[4],
            closed_drifted=row[5],
        )
        for row in rows
        if row[4] or row[5]
    ]


async def sync_step_batch_flags(
    session,
    *,
    dry_run: bool,
    workspace_id: str | None,
    section_id: str | None,
) -> list[SectionDrift]:
    drifted = await collect_drift(
        session, workspace_id=workspace_id, section_id=section_id
    )

    if not drifted:
        typer.echo("step_batch_flag_sync | no drift found")
        return []

    for entry in drifted:
        typer.echo(
            f"{entry.name:<30} section={str(entry.section_flag):<5} "
            f"open_drifted={entry.open_drifted:<5} "
            f"closed_drifted={entry.closed_drifted} (left as historical record)"
        )

    if dry_run:
        return drifted

    for entry in drifted:
        if not entry.open_drifted:
            continue
        corrected = await sync_step_batch_flag_for_section_in_session(
            session=session,
            workspace_id=entry.workspace_id,
            section_id=entry.section_id,
            allows_batch_working=entry.section_flag,
        )
        typer.echo(f"{entry.name:<30} corrected={corrected}")

    return drifted


async def _run(
    *,
    dry_run: bool,
    workspace_id: str | None,
    section_id: str | None,
) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            await sync_step_batch_flags(
                session,
                dry_run=dry_run,
                workspace_id=workspace_id,
                section_id=section_id,
            )
            if dry_run:
                typer.echo("[dry-run] no changes committed")
                return
            await session.commit()
            typer.echo("step_batch_flag_sync | committed")
    finally:
        await close_db()


@app.command("sync-step-batch-flags")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
    section_id: Annotated[str | None, typer.Option("--section-id")] = None,
) -> None:
    """Re-stamp open steps whose batch flag disagrees with their working section."""

    asyncio.run(
        _run(
            dry_run=dry_run,
            workspace_id=workspace_id,
            section_id=section_id,
        )
    )


if __name__ == "__main__":
    app()
