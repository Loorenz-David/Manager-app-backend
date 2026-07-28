"""Reconcile unfinished upholstery demand left by already-deleted tasks.

The command is dry-run by default. Use ``--execute`` to fail unfinished
requirements and update their inventory projections through the same service
used by live task deletion.
"""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated

import typer
from sqlalchemy import select

from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.items.cancel_upholstery_requirements import (
    CancelledRequirement,
    cancel_unfinished_item_requirements_in_session,
    load_unfinished_item_requirements,
    lock_and_filter_items_without_active_tasks,
)


app = typer.Typer(add_completion=False, no_args_is_help=True)


@dataclass(frozen=True)
class ReconciliationCandidate:
    workspace_id: str
    item_id: str
    task_id: str
    actor_id: str | None


async def collect_reconciliation_candidates(
    session,
    *,
    workspace_id: str | None,
    task_id: str | None,
) -> list[ReconciliationCandidate]:
    statement = (
        select(
            Task.workspace_id,
            TaskItem.item_id,
            Task.client_id.label("task_id"),
            Task.deleted_by_id,
            Task.deleted_at,
        )
        .join(
            TaskItem,
            (TaskItem.task_id == Task.client_id)
            & (TaskItem.workspace_id == Task.workspace_id),
        )
        .where(
            Task.is_deleted.is_(True),
            TaskItem.removed_at.is_(None),
        )
        .order_by(
            Task.workspace_id.asc(),
            TaskItem.item_id.asc(),
            Task.deleted_at.desc().nulls_last(),
            Task.client_id.asc(),
        )
    )
    if workspace_id is not None:
        statement = statement.where(Task.workspace_id == workspace_id)
    if task_id is not None:
        statement = statement.where(Task.client_id == task_id)

    rows = (await session.execute(statement)).all()
    candidates_by_item: dict[
        tuple[str, str], ReconciliationCandidate
    ] = {}
    for row in rows:
        key = (row.workspace_id, row.item_id)
        candidates_by_item.setdefault(
            key,
            ReconciliationCandidate(
                workspace_id=row.workspace_id,
                item_id=row.item_id,
                task_id=row.task_id,
                actor_id=row.deleted_by_id,
            ),
        )
    return list(candidates_by_item.values())


def _print_summary(
    *,
    mode: str,
    candidates: list[ReconciliationCandidate],
    cancelled: list[CancelledRequirement],
) -> None:
    state_counts = Counter(row.previous_state.value for row in cancelled)
    state_meters: defaultdict[str, Decimal] = defaultdict(
        lambda: Decimal("0")
    )
    for row in cancelled:
        state_meters[row.previous_state.value] += row.amount_meters

    typer.echo(
        "deleted_task_upholstery_reconciliation | "
        f"mode={mode} "
        f"workspaces={len({row.workspace_id for row in candidates})} "
        f"tasks={len({row.task_id for row in candidates})} "
        f"items={len({row.item_id for row in candidates})} "
        f"requirements={len(cancelled)} "
        f"inventories={len({row.upholstery_inventory_id for row in cancelled if row.upholstery_inventory_id})} "
        f"meters={sum((row.amount_meters for row in cancelled), Decimal('0'))}"
    )
    for state in sorted(state_counts):
        typer.echo(
            "deleted_task_upholstery_reconciliation_state | "
            f"state={state} count={state_counts[state]} "
            f"meters={state_meters[state]}"
        )


async def reconcile_deleted_task_upholstery_requirements(
    session,
    *,
    dry_run: bool,
    workspace_id: str | None,
    task_id: str | None,
) -> list[CancelledRequirement]:
    candidates = await collect_reconciliation_candidates(
        session,
        workspace_id=workspace_id,
        task_id=task_id,
    )
    candidates_by_workspace: defaultdict[
        str, list[ReconciliationCandidate]
    ] = defaultdict(list)
    for candidate in candidates:
        candidates_by_workspace[candidate.workspace_id].append(candidate)

    effective_candidates: list[ReconciliationCandidate] = []
    preview: list[CancelledRequirement] = []
    for candidate_workspace_id in sorted(candidates_by_workspace):
        workspace_candidates = candidates_by_workspace[
            candidate_workspace_id
        ]
        candidates_by_item = {
            candidate.item_id: candidate
            for candidate in workspace_candidates
        }
        orphaned_item_ids = await lock_and_filter_items_without_active_tasks(
            session=session,
            workspace_id=candidate_workspace_id,
            item_ids=candidates_by_item,
            lock_rows=not dry_run,
        )
        for item_id in orphaned_item_ids:
            candidate = candidates_by_item[item_id]
            requirements = await load_unfinished_item_requirements(
                session=session,
                workspace_id=candidate_workspace_id,
                item_ids=[item_id],
                lock_rows=not dry_run,
            )
            if not requirements:
                continue
            effective_candidates.append(candidate)
            if dry_run:
                preview.extend(
                    CancelledRequirement(
                        requirement_id=requirement.client_id,
                        item_upholstery_id=requirement.item_upholstery_id,
                        upholstery_inventory_id=requirement.upholstery_inventory_id,
                        previous_state=requirement.state,
                        amount_meters=requirement.amount_meters
                        or Decimal("0"),
                    )
                    for requirement in requirements
                )
            else:
                preview.extend(
                    await cancel_unfinished_item_requirements_in_session(
                        session=session,
                        workspace_id=candidate_workspace_id,
                        item_ids=[item_id],
                        actor_id=candidate.actor_id,
                    )
                )

    _print_summary(
        mode="dry_run" if dry_run else "execute",
        candidates=effective_candidates,
        cancelled=preview,
    )
    return preview


async def _run(
    *,
    dry_run: bool,
    workspace_id: str | None,
    task_id: str | None,
) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            await reconcile_deleted_task_upholstery_requirements(
                session,
                dry_run=dry_run,
                workspace_id=workspace_id,
                task_id=task_id,
            )
            if dry_run:
                typer.echo("[dry-run] no changes committed")
                return
            await session.commit()
            typer.echo(
                "deleted_task_upholstery_reconciliation | committed"
            )
    finally:
        await close_db()


@app.command("reconcile-deleted-task-upholstery-requirements")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    workspace_id: Annotated[
        str | None, typer.Option("--workspace-id")
    ] = None,
    task_id: Annotated[str | None, typer.Option("--task-id")] = None,
) -> None:
    """Cancel orphaned unfinished upholstery requirements."""

    asyncio.run(
        _run(
            dry_run=dry_run,
            workspace_id=workspace_id,
            task_id=task_id,
        )
    )


if __name__ == "__main__":
    app()
