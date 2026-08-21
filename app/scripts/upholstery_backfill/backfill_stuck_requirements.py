"""Backfill upholstery requirement transitions for steps that predate the
"upholstery installation" section auto-transition logic
(`beyo_manager.services.commands.task_steps._upholstery_installation_side_effect`).

Before that logic existed, transitioning a task step to WORKING or COMPLETED
in the "upholstery installation" working section never advanced the task's
fabric requirement past AVAILABLE — see the conversation record dated
2026-08-21. This leaves every step that already reached one of those states
(or PAUSED / SKIPPED, which map to the same outcomes) with fabric that is
still shown as reserved-but-untouched, even though the physical work already
happened.

This script re-derives, from each affected step's OWN current persisted
state, what its fabric requirement should be, and applies it through the
exact same `apply_upholstery_installation_side_effect` helper the live code
now uses — so a backfilled item ends up in the identical state it would be
in had the new logic existed from day one. No mutation logic is duplicated
here; this only decides *which* steps to feed it and *what* `new_state` to
simulate for each:

    step COMPLETED or SKIPPED              -> simulate COMPLETED
        (requirement: IN_USE/AVAILABLE -> COMPLETED, fabric consumed)
    step WORKING or PAUSED                 -> simulate WORKING
        (requirement: AVAILABLE -> IN_USE, fabric reserved-in-progress)
    step PENDING/FAILED/CANCELLED/BLOCKED  -> no change
        (the live logic never would have fired for these either)

Dry-run by default (`--dry-run`, the default, vs. `--execute`). Every
candidate step is applied inside its own SAVEPOINT: in dry-run mode the
savepoint is always rolled back after computing what it would have done; in
execute mode, one step's failure (e.g. insufficient stock to honor a WORKING
step) rolls back only that step and is reported as an error — it does not
block every other fix in the batch.

Known limitations, accepted for a one-time fix rather than engineered around:
  * Timestamps (`in_use_at` / `completed_at`) are backdated to the step's own
    `updated_at` (when it actually reached that persisted state), not "now"
    — so the record reflects when the work happened, not when this script
    ran. Falls back to `created_at` if `updated_at` is unset.
  * `updated_by_id` on every touched requirement is the actor resolved from
    --username, NOT the worker who actually did the installation — there is
    no reliable source data linking the two.
  * A step currently PAUSED only has `updated_at` from whenever it was last
    paused, not from when it first went WORKING — close enough for a
    one-time fix, not an attempt at full historical precision.

Usage:
    python -m scripts.upholstery_backfill.backfill_stuck_requirements \
        --username Norbi
    python -m scripts.upholstery_backfill.backfill_stuck_requirements \
        --username Norbi --execute
    python -m scripts.upholstery_backfill.backfill_stuck_requirements \
        --username Norbi --execute --task-id tsk_01ABCDEF  # one task, for testing
"""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Annotated

import typer
from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import (
    ItemUpholsteryRequirement,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import (
    WorkspaceMembership,
)
from beyo_manager.services.commands.task_steps._upholstery_installation_side_effect import (
    apply_upholstery_installation_side_effect,
)


app = typer.Typer(add_completion=False, no_args_is_help=True)

_SECTION_NAME = "upholstery installation"

# Which step state maps to which `apply_upholstery_installation_side_effect`
# `new_state` to simulate. Absent keys (PENDING/FAILED/CANCELLED/BLOCKED) mean
# "no change" — the live logic never fires for those either.
_STATE_TO_SIMULATED_TRANSITION: dict[TaskStepStateEnum, TaskStepStateEnum] = {
    TaskStepStateEnum.COMPLETED: TaskStepStateEnum.COMPLETED,
    TaskStepStateEnum.SKIPPED: TaskStepStateEnum.COMPLETED,
    TaskStepStateEnum.WORKING: TaskStepStateEnum.WORKING,
    TaskStepStateEnum.PAUSED: TaskStepStateEnum.WORKING,
}

# Mirrors the source-state gate inside apply_upholstery_installation_side_effect,
# used here only to preview what a step WOULD touch before running it for real.
_SOURCE_STATES_FOR_TRANSITION: dict[TaskStepStateEnum, tuple] = {
    TaskStepStateEnum.WORKING: (ItemUpholsteryRequirementStateEnum.AVAILABLE,),
    TaskStepStateEnum.COMPLETED: (
        ItemUpholsteryRequirementStateEnum.IN_USE,
        ItemUpholsteryRequirementStateEnum.AVAILABLE,
    ),
}

_TARGET_REQUIREMENT_STATE = {
    TaskStepStateEnum.WORKING: ItemUpholsteryRequirementStateEnum.IN_USE,
    TaskStepStateEnum.COMPLETED: ItemUpholsteryRequirementStateEnum.COMPLETED,
}


class _DryRunRollback(Exception):
    """Raised inside a SAVEPOINT to force its rollback in dry-run mode."""


@dataclass
class CandidateStep:
    step: TaskStep
    task_scalar_id: int
    item_id: str
    item_label: str


@dataclass(frozen=True)
class PreviewRow:
    item_upholstery_id: str
    fabric_label: str
    requirement_id: str
    from_state: ItemUpholsteryRequirementStateEnum
    amount_meters: Decimal


@dataclass
class StepOutcome:
    step_id: str
    task_scalar_id: int
    item_label: str
    simulated_step_state: TaskStepStateEnum
    target_requirement_state: ItemUpholsteryRequirementStateEnum
    rows: list[PreviewRow] = field(default_factory=list)
    applied: bool = False
    error: str | None = None


async def resolve_actor(
    session, *, username: str, workspace_id: str | None
) -> tuple[str, str]:
    """Resolve (user_id, workspace_id) from a username.

    Requires exactly one active workspace membership unless --workspace-id is
    given explicitly to disambiguate a user in more than one workspace.
    """
    user = (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None:
        raise typer.BadParameter(f"No user found with username {username!r}.")

    statement = select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == user.client_id,
        WorkspaceMembership.is_active.is_(True),
    )
    if workspace_id is not None:
        statement = statement.where(WorkspaceMembership.workspace_id == workspace_id)
    memberships = (await session.execute(statement)).scalars().all()

    if not memberships:
        raise typer.BadParameter(
            f"User {username!r} has no active membership"
            + (f" in workspace {workspace_id!r}." if workspace_id else ".")
        )
    if len(memberships) > 1:
        ws_ids = ", ".join(sorted(m.workspace_id for m in memberships))
        raise typer.BadParameter(
            f"User {username!r} belongs to multiple workspaces ({ws_ids}) — "
            "pass --workspace-id to disambiguate."
        )
    return user.client_id, memberships[0].workspace_id


async def collect_candidate_steps(
    session, *, workspace_id: str, task_id: str | None
) -> list[CandidateStep]:
    """Every non-deleted "upholstery installation" step whose task has a primary item."""
    statement = (
        select(TaskStep, Task.task_scalar_id, TaskItem.item_id, Item.article_number, Item.sku)
        .join(
            Task,
            (Task.client_id == TaskStep.task_id) & (Task.workspace_id == TaskStep.workspace_id),
        )
        .join(
            TaskItem,
            (TaskItem.task_id == TaskStep.task_id)
            & (TaskItem.workspace_id == TaskStep.workspace_id)
            & (TaskItem.role == TaskItemRoleEnum.PRIMARY)
            & (TaskItem.removed_at.is_(None)),
        )
        .join(
            Item,
            (Item.client_id == TaskItem.item_id) & (Item.workspace_id == TaskStep.workspace_id),
        )
        .where(
            TaskStep.workspace_id == workspace_id,
            TaskStep.is_deleted.is_(False),
            Task.is_deleted.is_(False),
            Item.is_deleted.is_(False),
        )
        .order_by(TaskStep.updated_at.asc().nulls_first(), TaskStep.created_at.asc())
    )
    if task_id is not None:
        statement = statement.where(TaskStep.task_id == task_id)

    rows = (await session.execute(statement)).all()
    candidates: list[CandidateStep] = []
    for step, task_scalar_id, item_id, article_number, sku in rows:
        section_name = (step.working_section_name_snapshot or "").strip().lower()
        if section_name != _SECTION_NAME:
            continue
        candidates.append(
            CandidateStep(
                step=step,
                task_scalar_id=task_scalar_id,
                item_id=item_id,
                item_label=article_number or sku or item_id,
            )
        )
    return candidates


async def preview_requirements_for_item(
    session,
    *,
    workspace_id: str,
    item_id: str,
    source_states: tuple,
) -> list[PreviewRow]:
    """What a transition to `source_states`' target would touch — read-only."""
    statement = (
        select(ItemUpholsteryRequirement, ItemUpholstery.name, ItemUpholstery.code)
        .join(
            ItemUpholstery,
            ItemUpholstery.client_id == ItemUpholsteryRequirement.item_upholstery_id,
        )
        .where(
            ItemUpholstery.workspace_id == workspace_id,
            ItemUpholstery.item_id == item_id,
            ItemUpholstery.is_deleted.is_(False),
            ItemUpholsteryRequirement.workspace_id == workspace_id,
            ItemUpholsteryRequirement.state.in_(source_states),
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
    )
    rows = (await session.execute(statement)).all()
    return [
        PreviewRow(
            item_upholstery_id=req.item_upholstery_id,
            fabric_label=name or code or req.item_upholstery_id,
            requirement_id=req.client_id,
            from_state=req.state,
            amount_meters=req.amount_meters or Decimal("0"),
        )
        for req, name, code in rows
    ]


async def run_backfill(
    session,
    *,
    workspace_id: str,
    actor_id: str,
    dry_run: bool,
    task_id: str | None = None,
) -> list[StepOutcome]:
    candidates = await collect_candidate_steps(
        session, workspace_id=workspace_id, task_id=task_id
    )
    outcomes: list[StepOutcome] = []

    for candidate in candidates:
        step = candidate.step
        simulated_state = _STATE_TO_SIMULATED_TRANSITION.get(step.state)
        if simulated_state is None:
            continue  # PENDING/FAILED/CANCELLED/BLOCKED — the live logic never fires either.

        rows = await preview_requirements_for_item(
            session,
            workspace_id=workspace_id,
            item_id=candidate.item_id,
            source_states=_SOURCE_STATES_FOR_TRANSITION[simulated_state],
        )
        if not rows:
            continue  # Already consistent — nothing this step would change.

        as_of: datetime = step.updated_at or step.created_at
        error: str | None = None
        try:
            async with session.begin_nested():
                await apply_upholstery_installation_side_effect(
                    session,
                    workspace_id=workspace_id,
                    task_id=step.task_id,
                    step=step,
                    new_state=simulated_state,
                    actor_id=actor_id,
                    now=as_of,
                )
                if dry_run:
                    raise _DryRunRollback()
        except _DryRunRollback:
            pass
        except Exception as exc:  # noqa: BLE001 — reported per-step, batch must continue.
            error = str(exc)

        outcomes.append(
            StepOutcome(
                step_id=step.client_id,
                task_scalar_id=candidate.task_scalar_id,
                item_label=candidate.item_label,
                simulated_step_state=simulated_state,
                target_requirement_state=_TARGET_REQUIREMENT_STATE[simulated_state],
                rows=rows,
                applied=(error is None and not dry_run),
                error=error,
            )
        )
    return outcomes


def _print_outcome(outcome: StepOutcome, *, dry_run: bool) -> None:
    result = "would_apply" if dry_run else ("applied" if outcome.applied else "error")
    meters = sum((row.amount_meters for row in outcome.rows), Decimal("0"))
    fabrics = ", ".join(sorted({row.fabric_label for row in outcome.rows}))
    line = (
        "upholstery_backfill_step | "
        f"task=#{outcome.task_scalar_id} step={outcome.step_id} item={outcome.item_label} "
        f"target_state={outcome.target_requirement_state.value} "
        f"requirements={len(outcome.rows)} meters={meters} fabrics=[{fabrics}] "
        f"result={result}"
    )
    if outcome.error:
        line += f" error={outcome.error}"
    typer.echo(line)


def _print_summary(outcomes: list[StepOutcome], *, dry_run: bool) -> None:
    errored = [o for o in outcomes if o.error]
    succeeded = [o for o in outcomes if o.error is None]
    state_counts = Counter(o.target_requirement_state.value for o in succeeded)
    total_meters = sum(
        (sum((row.amount_meters for row in o.rows), Decimal("0")) for o in succeeded),
        Decimal("0"),
    )
    typer.echo(
        "upholstery_backfill_summary | "
        f"mode={'dry_run' if dry_run else 'execute'} "
        f"steps_examined={len(outcomes)} "
        f"steps_ok={len(succeeded)} steps_errored={len(errored)} "
        f"requirements={sum(len(o.rows) for o in succeeded)} "
        f"meters={total_meters}"
    )
    for state in sorted(state_counts):
        typer.echo(
            f"upholstery_backfill_summary_state | state={state} steps={state_counts[state]}"
        )
    if errored:
        typer.echo(f"upholstery_backfill_errors | count={len(errored)}")
        for outcome in errored:
            typer.echo(
                "  "
                f"task=#{outcome.task_scalar_id} step={outcome.step_id} "
                f"item={outcome.item_label} error={outcome.error}"
            )


async def _run(
    *,
    username: str,
    workspace_id: str | None,
    task_id: str | None,
    dry_run: bool,
) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            actor_id, resolved_workspace_id = await resolve_actor(
                session, username=username, workspace_id=workspace_id
            )
            typer.echo(
                "upholstery_backfill_target | "
                f"username={username} actor_id={actor_id} workspace_id={resolved_workspace_id}"
            )
            outcomes = await run_backfill(
                session,
                workspace_id=resolved_workspace_id,
                actor_id=actor_id,
                dry_run=dry_run,
                task_id=task_id,
            )
            for outcome in outcomes:
                _print_outcome(outcome, dry_run=dry_run)
            _print_summary(outcomes, dry_run=dry_run)

            if dry_run:
                typer.echo("[dry-run] no changes committed")
                return
            await session.commit()
            typer.echo("upholstery_backfill | committed")
    finally:
        await close_db()


@app.command("backfill-stuck-upholstery-requirements")
def main(
    username: Annotated[
        str,
        typer.Option(
            "--username",
            help="Username of the actor to credit and whose workspace is targeted.",
        ),
    ],
    workspace_id: Annotated[
        str | None,
        typer.Option(
            "--workspace-id",
            help="Disambiguate when --username belongs to more than one workspace.",
        ),
    ] = None,
    task_id: Annotated[
        str | None,
        typer.Option("--task-id", help="Limit to a single task — useful for testing first."),
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
) -> None:
    """Backfill fabric requirement transitions for "upholstery installation" steps
    that were already WORKING/COMPLETED/PAUSED/SKIPPED before the auto-transition
    logic existed. Dry-run by default."""
    asyncio.run(
        _run(
            username=username,
            workspace_id=workspace_id,
            task_id=task_id,
            dry_run=dry_run,
        )
    )


if __name__ == "__main__":
    app()
