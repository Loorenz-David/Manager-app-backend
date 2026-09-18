"""Load settled plus currently accruing worked seconds for task steps.

Two entry points over one query:

  - `load_live_worked_time` is the full surface — settled+live seconds, and the forward
    accrual rate each step is currently earning at.
  - `load_live_worked_seconds` returns just the seconds map, for the callers that never
    needed the rest.

They share one implementation and one sweep. The rate is read off the *same* contribution
objects that produce the seconds, so the two can never disagree about what a step is
accruing — which is the whole point of publishing it.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fractions import Fraction

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions


@dataclass(frozen=True)
class LiveWorkedTime:
    """Settled+live seconds per step, plus what each step is accruing at right now.

    `seconds` has an entry for every input step. `accrual_rate` and `concurrency` have
    entries only for steps that are actually accruing — absence means "not accruing", which
    the serializers publish as null. There is deliberately no zero sentinel: a concurrency
    of 0 is not a real divisor. This loader knows nothing about budgets; whether a surface
    publishes the rate for a given step or task is that surface's rule, not this one's.

    A step holds at most one open record (unique partial index
    `uix_step_state_records_active`), so `concurrency` is single-valued and the invariant
    `accrual_rate == Fraction(1, concurrency)` holds for every present entry.
    """

    seconds: dict[str, int]
    accrual_rate: dict[str, Fraction] = field(default_factory=dict)
    concurrency: dict[str, int] = field(default_factory=dict)

    def task_rate(self, step_ids: Iterable[str]) -> Fraction | None:
        """Total seconds per wall-clock second accruing across `step_ids`, or None.

        Summed as exact fractions before any rounding, so a task whose three batched steps
        each earn 1/3 reports exactly 1 rather than 0.9999. Two workers on one task can push
        this above 1 legitimately, as can a non-batch step running beside batched ones.

        Returns None — never 0 — when nothing is accruing, so "idle" is one value across
        both payloads rather than a zero the client has to distinguish from a real rate.
        """
        rates = [self.accrual_rate[step_id] for step_id in step_ids if step_id in self.accrual_rate]
        if not rates:
            return None
        return sum(rates, Fraction(0))


async def load_live_worked_time(
    session: AsyncSession,
    workspace_id: str,
    steps: Sequence[TaskStep],
    now: datetime,
) -> LiveWorkedTime:
    """Settled seconds plus the current open working share, and the live accrual rate.

    The open-record probe is intentionally task-step scoped, while each averaging sweep is
    user scoped so batch work on another task remains part of the divisor. That asymmetry is
    also why the rate cannot be derived by a client: a step running in a section the caller
    never asked for still divides the rate of one it did.

    The returned live share is carried in these separate mappings; no ORM step is mutated.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise TypeError("load_live_worked_seconds requires an aware UTC now")

    settled = {
        step.client_id: int(step.total_working_seconds or 0)
        for step in steps
    }
    if not settled:
        return LiveWorkedTime(seconds={})

    probe_rows = (
        await session.execute(
            select(StepStateRecord).where(
                StepStateRecord.workspace_id == workspace_id,
                StepStateRecord.step_id.in_(settled),
                StepStateRecord.exited_at.is_(None),
                StepStateRecord.state == TaskStepStateEnum.WORKING,
                StepStateRecord.is_deleted.is_(False),
            )
        )
    ).scalars().all()

    records_by_user: dict[str, list[StepStateRecord]] = defaultdict(list)
    for record in probe_rows:
        user_id = record.credited_user_id or record.created_by_id
        if user_id is not None:
            records_by_user[user_id].append(record)

    live_by_step: dict[str, int] = defaultdict(int)
    rate_by_step: dict[str, Fraction] = {}
    concurrency_by_step: dict[str, int] = {}
    for user_id, user_records in records_by_user.items():
        window_start = min(record.entered_at for record in user_records) - timedelta(days=1)
        probe_record_ids = {record.client_id for record in user_records}
        contributions = await compute_record_contributions(
            session,
            workspace_id,
            user_id,
            window_start,
            now,
            now,
        )
        for contribution in contributions:
            if (
                contribution.is_open
                and contribution.state == TaskStepStateEnum.WORKING.value
                and contribution.record_id in probe_record_ids
            ):
                live_by_step[contribution.step_id] += int(round(contribution.seconds))
                # Same contribution object as the seconds above, so the published rate is
                # by construction the rate those seconds are growing at.
                if contribution.accrual_rate is not None:
                    rate_by_step[contribution.step_id] = contribution.accrual_rate
                    concurrency_by_step[contribution.step_id] = contribution.concurrency

    return LiveWorkedTime(
        seconds={
            step_id: settled_seconds + live_by_step.get(step_id, 0)
            for step_id, settled_seconds in settled.items()
        },
        accrual_rate=rate_by_step,
        concurrency=concurrency_by_step,
    )


async def load_live_worked_seconds(
    session: AsyncSession,
    workspace_id: str,
    steps: Sequence[TaskStep],
    now: datetime,
) -> dict[str, int]:
    """Settled seconds plus the current open working share per input step.

    The narrow face of `load_live_worked_time`, for callers that need only the totals.
    """
    return (await load_live_worked_time(session, workspace_id, steps, now)).seconds


__all__ = ["LiveWorkedTime", "load_live_worked_seconds", "load_live_worked_time"]
