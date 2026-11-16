"""Release fabric still requested by tasks that already finished.

One-off cleanup for requirements stranded before ``settle_finished_task_upholstery``
existed (incident 2026-11-16: PRE-ORDER 29 / task #1014, plus #204 and #1066 on prod).
Finds every non-deleted READY / RESOLVED / CANCELLED / FAILED task whose items still
hold a ``needs_ordering`` or ``ordered`` requirement, and cancels those requirements
through the same service the live commands use (need released, ledger row with trigger
``maintenance_script``). Items still on another unfinished task are left alone.

Dry-run by default: it performs the real settlement inside a transaction, prints what
changed, then rolls back. ``--execute`` commits.

    python -m scripts.backfill.settle_finished_task_upholstery settle-finished-task-upholstery
    python -m scripts.backfill.settle_finished_task_upholstery settle-finished-task-upholstery --execute
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

import typer
from sqlalchemy import select

from beyo_manager.domain.upholstery.enums import InventoryMovementTriggerEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import (
    ItemUpholsteryRequirement,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.items.cancel_upholstery_requirements import (
    CancelledRequirement,
)
from beyo_manager.services.commands.items.settle_finished_task_upholstery import (
    FINISHED_TASK_STATES,
    SETTLEABLE_REQUIREMENT_STATES,
    settle_upholstery_for_task_ids,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)
_NOTE = "settle_finished_task_upholstery backfill (incident 2026-11-16)"


async def collect_finished_task_ids(
    session, *, workspace_id: str | None, task_id: str | None
) -> dict[str, list[str]]:
    """workspace_id -> finished task ids that still link a settleable requirement."""
    statement = (
        select(Task.workspace_id, Task.client_id)
        .join(
            TaskItem,
            (TaskItem.task_id == Task.client_id)
            & (TaskItem.workspace_id == Task.workspace_id),
        )
        .join(
            ItemUpholstery,
            (ItemUpholstery.item_id == TaskItem.item_id)
            & (ItemUpholstery.workspace_id == Task.workspace_id),
        )
        .join(
            ItemUpholsteryRequirement,
            ItemUpholsteryRequirement.item_upholstery_id == ItemUpholstery.client_id,
        )
        .where(
            Task.is_deleted.is_(False),
            Task.state.in_(FINISHED_TASK_STATES),
            TaskItem.removed_at.is_(None),
            ItemUpholstery.is_deleted.is_(False),
            ItemUpholsteryRequirement.is_deleted.is_(False),
            ItemUpholsteryRequirement.state.in_(SETTLEABLE_REQUIREMENT_STATES),
        )
        .distinct()
        .order_by(Task.workspace_id.asc(), Task.client_id.asc())
    )
    if workspace_id is not None:
        statement = statement.where(Task.workspace_id == workspace_id)
    if task_id is not None:
        statement = statement.where(Task.client_id == task_id)

    by_workspace: dict[str, list[str]] = defaultdict(list)
    for row in (await session.execute(statement)).all():
        by_workspace[row.workspace_id].append(row.client_id)
    return dict(by_workspace)


async def settle_finished_tasks(
    session, *, workspace_id: str | None, task_id: str | None
) -> list[CancelledRequirement]:
    now = datetime.now(timezone.utc)
    cancelled: list[CancelledRequirement] = []
    candidates = await collect_finished_task_ids(
        session, workspace_id=workspace_id, task_id=task_id
    )
    for ws_id in sorted(candidates):
        cancelled.extend(
            await settle_upholstery_for_task_ids(
                session,
                candidates[ws_id],
                workspace_id=ws_id,
                actor_user_id=None,
                now=now,
                trigger=InventoryMovementTriggerEnum.MAINTENANCE_SCRIPT,
                note=_NOTE,
            )
        )
    typer.echo(
        "settle_finished_task_upholstery | "
        f"workspaces={len(candidates)} "
        f"candidate_tasks={sum(len(ids) for ids in candidates.values())} "
        f"requirements={len(cancelled)} "
        f"meters={sum((row.amount_meters for row in cancelled), Decimal('0'))}"
    )
    for row in cancelled:
        typer.echo(
            "settle_finished_task_upholstery_row | "
            f"requirement={row.requirement_id} previous_state={row.previous_state.value} "
            f"meters={row.amount_meters} inventory={row.upholstery_inventory_id}"
        )
    return cancelled


async def _run(*, dry_run: bool, workspace_id: str | None, task_id: str | None) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            await settle_finished_tasks(session, workspace_id=workspace_id, task_id=task_id)
            if dry_run:
                await session.rollback()
                typer.echo("[dry-run] rolled back, nothing committed")
                return
            await session.commit()
            typer.echo("settle_finished_task_upholstery | committed")
    finally:
        await close_db()


@app.command("settle-finished-task-upholstery")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
    task_id: Annotated[str | None, typer.Option("--task-id")] = None,
) -> None:
    """Cancel needs_ordering/ordered requirements on already-finished tasks."""
    asyncio.run(_run(dry_run=dry_run, workspace_id=workspace_id, task_id=task_id))


if __name__ == "__main__":
    app()
