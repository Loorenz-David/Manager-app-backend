"""Load settled plus currently accruing worked seconds for task steps."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions


async def load_live_worked_seconds(
    session: AsyncSession,
    workspace_id: str,
    steps: Sequence[TaskStep],
    now: datetime,
) -> dict[str, int]:
    """Return settled seconds plus the current open working share per input step.

    The open-record probe is intentionally task-step scoped, while each averaging
    sweep is user scoped so batch work on another task remains part of the divisor.
    The returned live share is carried in this separate mapping; no ORM step is
    mutated.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise TypeError("load_live_worked_seconds requires an aware UTC now")

    settled = {
        step.client_id: int(step.total_working_seconds or 0)
        for step in steps
    }
    if not settled:
        return {}

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

    return {
        step_id: settled_seconds + live_by_step.get(step_id, 0)
        for step_id, settled_seconds in settled.items()
    }


__all__ = ["load_live_worked_seconds"]
