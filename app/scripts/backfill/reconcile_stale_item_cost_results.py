"""Reconcile `item_cost_results` rows left pinned to a superseded evaluation.

Before the commit boundary existed (states.md emission point 5), re-committing an
evaluation moved the live allowance and left the stored result frozen against the
superseded one — permanently, for a task that never reached another transition. The
symptom is a served `final` whose variance is measured against a different allowance
than the live `budget` block's.

This finds every row whose `evaluation_id` is not its task's current committed
evaluation and recomputes it through the production handler itself
(`handle_process_item_cost_result`), so the backfill can never drift from the
write path. Idempotent (the handler is a recompute-and-SET), and rows whose task is
in a state the handler refuses are reported and skipped, not forced.

Dry-run by default; ``--execute`` writes.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from sqlalchemy import select

from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.tasks.analytics.process_item_cost_result import (
    _ADMITTED_STATES,
    handle_process_item_cost_result,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)


async def _stale_rows(session) -> list[tuple[str, str, str, str, object, object]]:
    """(workspace_id, task_id, pinned_evaluation_id, task_state, frozen, current)."""
    current = (
        select(
            ItemCostEvaluation.task_id.label("task_id"),
            ItemCostEvaluation.client_id.label("client_id"),
            ItemCostEvaluation.allowed_worker_minutes.label("allowed_worker_minutes"),
        )
        .where(
            ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
            ItemCostEvaluation.superseded_at.is_(None),
            ItemCostEvaluation.is_deleted.is_(False),
        )
        .subquery()
    )
    rows = await session.execute(
        select(
            ItemCostResult.workspace_id,
            ItemCostResult.task_id,
            ItemCostResult.evaluation_id,
            Task.state,
            ItemCostResult.actual_worker_minutes + ItemCostResult.variance_worker_minutes,
            current.c.allowed_worker_minutes,
        )
        .join(Task, Task.client_id == ItemCostResult.task_id)
        .join(current, current.c.task_id == ItemCostResult.task_id)
        .where(ItemCostResult.evaluation_id != current.c.client_id)
        .order_by(ItemCostResult.task_id.asc())
    )
    return list(rows)


async def _run(*, dry_run: bool) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            stale = await _stale_rows(session)
            if not stale:
                typer.echo("item_cost_results | no row is pinned to a superseded evaluation")
                return
            skipped = 0
            reconcilable: list[tuple[str, str]] = []
            for workspace_id, task_id, evaluation_id, state, frozen, live in stale:
                admitted = state in _ADMITTED_STATES
                typer.echo(
                    f"{task_id} | state={state.value} pinned={evaluation_id} "
                    f"frozen_allowance={frozen} live_allowance={live} "
                    f"{'recompute' if admitted else 'SKIP (handler refuses this state)'}"
                )
                if admitted:
                    reconcilable.append((workspace_id, task_id))
                else:
                    skipped += 1
            typer.echo(
                f"item_cost_results | stale={len(stale)} recomputable={len(reconcilable)} skipped={skipped}"
            )
            if dry_run:
                typer.echo("[dry-run] no changes committed")
                return
            break

        for workspace_id, task_id in reconcilable:
            # The handler opens and commits its own session, exactly as the worker does.
            await handle_process_item_cost_result(
                {"workspace_id": workspace_id, "task_id": task_id}, "backfill"
            )
        typer.echo(f"item_cost_results | recomputed {len(reconcilable)} row(s)")
    finally:
        await close_db()


@app.command("reconcile-stale-item-cost-results")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
) -> None:
    """Recompute result rows frozen against a superseded evaluation."""
    asyncio.run(_run(dry_run=dry_run))


if __name__ == "__main__":
    app()
