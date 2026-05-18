# PLAN_analytics_worker_time_accuracy_20260518

## Metadata

- Plan ID: `PLAN_analytics_worker_time_accuracy_20260518`
- Status: `under_construction`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-18T00:00:00Z`
- Related issue/ticket: `task-system-plan-6`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`

---

## Goal and intent

- **Goal:** Implement WORKER-1 (`process_step_transition`) — the analytics background worker that consumes outbox events from CMD-12 and updates all four stats tables. Also implement CMD-13 (`mark_step_time_inaccurate`) which allows workers/managers to flag a time record as wrong.
- **Business/user intent:** Every completed or interrupted work session is aggregated into daily and lifetime stats per user, per user+section, and per section. These metrics power manager dashboards and capacity planning. Inaccurate time records are flagged and excluded from metrics; the system substitutes section averages.
- **Non-goals:** Analytics materialized views, reporting dashboards, average-time computation engine (the substitution from average is flagged but the actual substitution of specific numbers is deferred to a follow-up plan — the `taken_from_average` flag is set but no average lookup is performed in this plan).

---

## Prerequisite

**Plan 5 must be completed.** WORKER-1 consumes `StepTransitionPayload` events published by CMD-12. `TaskType.PROCESS_STEP_TRANSITION` must exist in `domain/execution/enums.py` (added in Plan 5).

---

## Scope

- **In scope:**
  - New handler: `services/tasks/analytics/process_step_transition.py` — WORKER-1 handler
  - New worker entry point: `workers/analytics_worker.py`
  - New command: `services/commands/task_steps/mark_step_time_inaccurate.py` — CMD-13
  - Request model appended to `services/commands/task_steps/requests/__init__.py`
  - Route addition to `routers/api_v1/tasks.py`
  - New directory: `services/tasks/analytics/` + `__init__.py`
- **Out of scope:** Average-time substitution computation (flagging is implemented, computation is deferred). No new migrations — all four stats tables exist.
- **Assumptions:** `UserDailyWorkStats`, `UserLifetimeStats`, `UserSectionDailyWorkStats`, `WorkingSectionDailyWorkStats` all exist with the aggregate metrics mixin columns. `UserWorkProfile` exists with `salary_per_hour_before_tax`. All four tables have the fields from `AggregateMetricsTimeMixin`, `AggregateMetricsCountsMixin`, `AggregateMetricsTotalsMixin`, `AggregateMetricsCostMixin`.

---

## Clarifications required

_None._

---

## Acceptance criteria

1. After a `WORKING` record is closed (CMD-12 transitions from WORKING to any other state), WORKER-1 increments `total_working_seconds`, `total_working_count`, and `total_cost_minor` on all four stats tables for the assigned worker.
2. After a `PAUSED` record is closed, WORKER-1 increments `total_pause_seconds`, `total_pause_count`, and `total_cost_minor` on all four stats tables.
3. After an `ENDED_SHIFT` record is closed, WORKER-1 increments `total_ended_shift_seconds` and `total_ended_shift_count` on all four stats tables. **No cost increment for ENDED_SHIFT.**
4. When a step transitions to `COMPLETED` AND the linked item has issues (non-deleted), WORKER-1 increments `total_issues_count` on all four tables. If any of those issues are resolved (however the item domain defines "resolved"), also increments `total_issues_resolved_count`.
5. **Exclusion rule:** If `StepStateRecord.recorded_time_marked_wrong = True`, all time and count increments for that record are skipped. The handler checks this flag on the closing record before any updates.
6. Cost calculation: `cost_minor = round((interval_seconds / 3600) * salary_per_hour_before_tax * 100)` where `salary_per_hour_before_tax` is from `UserWorkProfile` for the assigned worker. If the worker has no `UserWorkProfile` or `salary_per_hour_before_tax` is null, `cost_minor` increment is `0` (no cost, no error).
7. Stats rows are upserted — `get or create` per (workspace_id, user_id, work_date) for user-scoped tables and (workspace_id, section_id, work_date) for section table. The `work_date` is the date part of `entered_at` (the work session start date, not the exit date).
8. The handler is idempotent: if called twice with the same closing record, the increments are applied twice. This is acknowledged as acceptable — analytics workers may duplicate-process in exceptional cases. The outbox pattern with `max_try=3` makes duplicates rare, and the stats are approximate by design.
9. `POST /api/v1/tasks/{task_id}/steps/{step_id}/state-records/{record_id}/mark-inaccurate` sets `StepStateRecord.recorded_time_marked_wrong = True` and `TaskStep.taken_from_average = True`. Returns `{record_id}`.
10. Each aggregation rule is a **separate function** in the handler module. Adding a new stat requires adding a new function, not modifying existing ones.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: structure
- `backend/architecture/04_context.md`: `ServiceContext` (for CMD-13 only)
- `backend/architecture/05_errors.md`: `NotFound`
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin` (for CMD-13)
- `backend/architecture/09_routers.md`: router wiring (for CMD-13 route)
- `backend/architecture/16_background_jobs.md`: worker pattern, `task_db_session`, handler contract, payload deserialisation, idempotency, DB access in handlers
- `backend/architecture/21_naming_conventions.md`: naming

### Permitted relational reads

| File | What to extract |
|---|---|
| `models/tables/analytics/user_daily_work_stats.py` | All columns, UniqueConstraint key `(workspace_id, user_id, work_date)`, mixin column names |
| `models/tables/analytics/user_lifetime_stats.py` | All columns, UniqueConstraint key `(workspace_id, user_id)` |
| `models/tables/analytics/user_section_daily_work_stats.py` | All columns, UniqueConstraint key `(workspace_id, user_id, working_section_id, work_date)` |
| `models/tables/analytics/working_section_daily_work_stats.py` | All columns, UniqueConstraint key `(workspace_id, working_section_id, work_date)` |
| `models/tables/users/user_work_profile.py` | `user_id`, `salary_per_hour_before_tax` column name, UniqueConstraint |
| `models/tables/tasks/step_state_record.py` | `recorded_time_marked_wrong`, `taken_from_average`, `entered_at`, `exited_at`, `state` |
| `models/tables/tasks/task_step.py` | `taken_from_average`, `assigned_worker_id`, `working_section_id`, `task_id` |
| `models/tables/tasks/task_item.py` | JOIN path to item: `task_id, removed_at IS NULL` |
| `models/tables/items/item_issue.py` | `item_id`, `is_deleted` — to count issues |
| `services/infra/execution/task_factory.py` | `task_db_session` import path (if it exists), or confirm it's in `services/infra/execution/db.py` |
| `workers/notification_worker.py` | Exact pattern for worker entry point: `init_db`, `run_worker`, `HANDLER_MAP` |
| `domain/execution/payloads/step_transition.py` | `StepTransitionPayload` — the payload this handler receives |

---

## Implementation plan

### Step 1 — Create directory and `__init__.py`

Create `services/tasks/analytics/__init__.py` (empty).

### Step 2 — WORKER-1 handler: `services/tasks/analytics/process_step_transition.py`

**Full implementation structure:**

```python
"""WORKER-1: Process step state transition events — update analytics stats tables."""

import logging
from dataclasses import asdict
from datetime import date, datetime, timezone

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.analytics.working_section_daily_work_stats import WorkingSectionDailyWorkStats
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.services.infra.execution.db import task_db_session

logger = logging.getLogger(__name__)


async def handle_process_step_transition(raw: dict, task_id: str) -> None:
    """WORKER-1: Dispatch step transition payload to all applicable aggregation rules."""
    payload = StepTransitionPayload(**raw)  # validates at entry; raises TypeError on mismatch

    async with task_db_session() as session:
        closing_record = await _fetch_closing_record(session, payload)
        if closing_record is None:
            logger.warning("record_not_found | closing_record_id=%s task_id=%s", payload.closing_record_id, task_id)
            return

        # Exclusion rule: skip all time/count increments for inaccurate records
        if closing_record.recorded_time_marked_wrong:
            logger.info("record_marked_wrong_skipped | closing_record_id=%s", payload.closing_record_id)
            # Still check for issues if new_state is COMPLETED
        else:
            interval_seconds = _compute_interval_seconds(payload)
            closing_state = TaskStepStateEnum(payload.closing_state)

            if closing_state == TaskStepStateEnum.WORKING:
                await _apply_working_close(session, payload, interval_seconds)
            elif closing_state == TaskStepStateEnum.PAUSED:
                await _apply_paused_close(session, payload, interval_seconds)
            elif closing_state == TaskStepStateEnum.ENDED_SHIFT:
                await _apply_ended_shift_close(session, payload, interval_seconds)

        # Issues rule: applies regardless of recorded_time_marked_wrong
        new_state = TaskStepStateEnum(payload.new_state)
        if new_state == TaskStepStateEnum.COMPLETED:
            await _apply_issues_at_completion(session, payload)

        await session.commit()
```

**`_fetch_closing_record`:**
```python
async def _fetch_closing_record(session, payload) -> StepStateRecord | None:
    result = await session.execute(
        select(StepStateRecord).where(
            StepStateRecord.client_id == payload.closing_record_id,
            StepStateRecord.workspace_id == payload.workspace_id,
        )
    )
    return result.scalar_one_or_none()
```

**`_compute_interval_seconds`:**
```python
def _compute_interval_seconds(payload: StepTransitionPayload) -> int:
    entered = datetime.fromisoformat(payload.entered_at)
    exited = datetime.fromisoformat(payload.exited_at)
    delta = exited - entered
    return max(0, int(delta.total_seconds()))
```

**`_apply_working_close`:**
```python
async def _apply_working_close(session, payload, interval_seconds: int) -> None:
    cost_minor = await _compute_cost_minor(session, payload.assigned_worker_id, payload.workspace_id, interval_seconds)
    work_date = datetime.fromisoformat(payload.entered_at).date()
    
    await _increment_user_daily(session, payload, work_date,
        working_seconds=interval_seconds, working_count=1, cost_minor=cost_minor)
    await _increment_user_lifetime(session, payload,
        working_seconds=interval_seconds, working_count=1, cost_minor=cost_minor)
    await _increment_user_section_daily(session, payload, work_date,
        working_seconds=interval_seconds, working_count=1, cost_minor=cost_minor)
    await _increment_section_daily(session, payload, work_date,
        working_seconds=interval_seconds, working_count=1, cost_minor=cost_minor)
```

**`_apply_paused_close`:**
```python
async def _apply_paused_close(session, payload, interval_seconds: int) -> None:
    cost_minor = await _compute_cost_minor(session, payload.assigned_worker_id, payload.workspace_id, interval_seconds)
    work_date = datetime.fromisoformat(payload.entered_at).date()

    await _increment_user_daily(session, payload, work_date,
        pause_seconds=interval_seconds, pause_count=1, cost_minor=cost_minor)
    await _increment_user_lifetime(session, payload,
        pause_seconds=interval_seconds, pause_count=1, cost_minor=cost_minor)
    await _increment_user_section_daily(session, payload, work_date,
        pause_seconds=interval_seconds, pause_count=1, cost_minor=cost_minor)
    await _increment_section_daily(session, payload, work_date,
        pause_seconds=interval_seconds, pause_count=1, cost_minor=cost_minor)
```

**`_apply_ended_shift_close`:**
```python
async def _apply_ended_shift_close(session, payload, interval_seconds: int) -> None:
    # ENDED_SHIFT is NOT costed
    work_date = datetime.fromisoformat(payload.entered_at).date()

    await _increment_user_daily(session, payload, work_date,
        ended_shift_seconds=interval_seconds, ended_shift_count=1)
    await _increment_user_lifetime(session, payload,
        ended_shift_seconds=interval_seconds, ended_shift_count=1)
    await _increment_user_section_daily(session, payload, work_date,
        ended_shift_seconds=interval_seconds, ended_shift_count=1)
    await _increment_section_daily(session, payload, work_date,
        ended_shift_seconds=interval_seconds, ended_shift_count=1)
```

**`_apply_issues_at_completion`:**
```python
async def _apply_issues_at_completion(session, payload) -> None:
    # Count issues on the item linked to this task
    # Path: task_id → task_items (PRIMARY, removed_at IS NULL) → item_id → item_issues
    task_item_result = await session.execute(
        select(TaskItem).where(
            TaskItem.workspace_id == payload.workspace_id,
            TaskItem.task_id == payload.task_id,
            TaskItem.removed_at.is_(None),
        )
    )
    task_items = task_item_result.scalars().all()
    if not task_items:
        return

    item_ids = [ti.item_id for ti in task_items]
    issues_result = await session.execute(
        select(ItemIssue).where(
            ItemIssue.workspace_id == payload.workspace_id,
            ItemIssue.item_id.in_(item_ids),
            ItemIssue.is_deleted.is_(False),
        )
    )
    issues = issues_result.scalars().all()
    if not issues:
        return

    total_count = len(issues)
    # "resolved" issues: check ItemIssue.state or similar — verify the column/value against model
    # For now: resolved_count = total_count (same behavior, as noted in intention plan)
    resolved_count = total_count

    work_date = datetime.fromisoformat(payload.entered_at).date()
    await _increment_user_daily(session, payload, work_date,
        issues_count=total_count, issues_resolved_count=resolved_count)
    await _increment_user_lifetime(session, payload,
        issues_count=total_count, issues_resolved_count=resolved_count)
    await _increment_user_section_daily(session, payload, work_date,
        issues_count=total_count, issues_resolved_count=resolved_count)
    await _increment_section_daily(session, payload, work_date,
        issues_count=total_count, issues_resolved_count=resolved_count)
```

**`_compute_cost_minor`:**
```python
async def _compute_cost_minor(session, worker_id: str | None, workspace_id: str, interval_seconds: int) -> int:
    if not worker_id:
        return 0
    profile_result = await session.execute(
        select(UserWorkProfile).where(
            UserWorkProfile.user_id == worker_id,
            UserWorkProfile.workspace_id == workspace_id,
        )
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None or profile.salary_per_hour_before_tax is None:
        return 0
    cost = (Decimal(str(interval_seconds)) / Decimal("3600")) * profile.salary_per_hour_before_tax * Decimal("100")
    return int(cost.to_integral_value())
```

**Get-or-create helpers for each table** — one per table. Pattern:

```python
async def _get_or_create_user_daily(session, workspace_id, user_id, work_date, display_name_snapshot) -> UserDailyWorkStats:
    result = await session.execute(
        select(UserDailyWorkStats).where(
            UserDailyWorkStats.workspace_id == workspace_id,
            UserDailyWorkStats.user_id == user_id,
            UserDailyWorkStats.work_date == work_date,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserDailyWorkStats(
            workspace_id=workspace_id,
            user_id=user_id,
            user_display_name_snapshot=display_name_snapshot,
            work_date=work_date,
        )
        session.add(row)
        await session.flush()
    return row
```

Implement equivalent functions for `UserLifetimeStats`, `UserSectionDailyWorkStats`, `WorkingSectionDailyWorkStats`.

**`_increment_*` helper parameters:** All parameters are keyword-only with defaults of `0`:

```python
async def _increment_user_daily(
    session, payload, work_date,
    *, working_seconds=0, working_count=0,
    pause_seconds=0, pause_count=0,
    ended_shift_seconds=0, ended_shift_count=0,
    issues_count=0, issues_resolved_count=0,
    cost_minor=0,
) -> None:
    row = await _get_or_create_user_daily(
        session, payload.workspace_id, payload.assigned_worker_id, work_date,
        display_name_snapshot=payload.assigned_worker_id or ""  # fallback
    )
    row.total_working_seconds += working_seconds
    row.total_working_count += working_count
    row.total_pause_seconds += pause_seconds
    row.total_pause_count += pause_count
    row.total_ended_shift_seconds += ended_shift_seconds
    row.total_ended_shift_count += ended_shift_count
    row.total_issues_count += issues_count
    row.total_issues_resolved_count += issues_resolved_count
    if cost_minor:
        row.total_cost_minor = (row.total_cost_minor or 0) + cost_minor
    row.updated_at = datetime.now(timezone.utc)
```

**User display name snapshot:** The payload does not include the worker's display name. Fetch it from the `User` table in the handler if needed, or use a fallback. Recommended: fetch `User` by `assigned_worker_id` at the top of the handler for the display name. Cache in a local variable.

**Important:** `assigned_worker_id` may be `None` if no worker was assigned to the step. In this case, skip all user-scoped increments (user_daily, user_lifetime, user_section_daily) — only section_daily can be updated without a worker. Guard: `if payload.assigned_worker_id is None: skip user-scoped updates`.

**`_increment_section_daily`:** Uses `working_section_id` and `section_name_snapshot`. The section name is not in the payload — look it up from `WorkingSection.name` or use a fallback. Or: add `working_section_name_snapshot` to the `StepTransitionPayload`. Given the step has `working_section_name_snapshot`, include it in the payload. **Amendment to Plan 5:** add `working_section_name_snapshot: str | None` to `StepTransitionPayload`. Copilot should update the payload dataclass before implementing the handler.

### Step 3 — Worker entry point: `workers/analytics_worker.py`

```python
import asyncio

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.models.database import init_db
from beyo_manager.services.infra.execution.worker_base import run_worker
from beyo_manager.services.tasks.analytics.process_step_transition import handle_process_step_transition

HANDLER_MAP = {
    TaskType.PROCESS_STEP_TRANSITION: handle_process_step_transition,
}

async def main() -> None:
    await init_db()
    await run_worker("queue:analytics", HANDLER_MAP)

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4 — CMD-13: `services/commands/task_steps/mark_step_time_inaccurate.py`

```python
async def mark_step_time_inaccurate(ctx: ServiceContext) -> dict:
    request = parse_mark_step_time_inaccurate_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        # Fetch the StepStateRecord (scope: step_id + workspace_id)
        record_result = await ctx.session.execute(
            select(StepStateRecord).where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.client_id == request.record_id,
                StepStateRecord.is_deleted.is_(False),
            )
        )
        record = record_result.scalar_one_or_none()
        if record is None:
            raise NotFound("State record not found.")

        # Fetch the step to set taken_from_average
        step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == record.step_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            raise NotFound("Task step not found.")

        record.recorded_time_marked_wrong = True
        step.taken_from_average = True

    return {"record_id": record.client_id}
```

**Request model to append to `services/commands/task_steps/requests/__init__.py`:**
```
MarkStepTimeInaccurateRequest:
  record_id: str
  step_id: str   (for route scoping)
  task_id: str   (for route scoping)
```

### Step 5 — Route in `routers/api_v1/tasks.py`

```
POST "/{task_id}/steps/{step_id}/state-records/{record_id}/mark-inaccurate"
    → route_mark_step_time_inaccurate (ADMIN, MANAGER, WORKER)
```

Handler:
```python
ctx = ServiceContext(
    incoming_data={"record_id": record_id, "step_id": step_id, "task_id": task_id},
    ...
)
```

---

## Risks and mitigations

- **Risk:** `working_section_name_snapshot` missing from `StepTransitionPayload` — the analytics worker needs it for `WorkingSectionDailyWorkStats` and `UserSectionDailyWorkStats`. The payload must be amended in Plan 5's Step 2 (or the handler fetches it from the DB).
  **Mitigation:** Amend `StepTransitionPayload` in Plan 5 to include `working_section_name_snapshot: str | None`. Handler uses it directly.

- **Risk:** `assigned_worker_id` is `None` — the step had no assigned worker. User-scoped increments would fail.
  **Mitigation:** Guard at top of dispatch: `if payload.assigned_worker_id is None: skip user-scoped tables`. Section-daily still receives increments (only `working_section_id` required).

- **Risk:** `total_cost_minor` is `Mapped[int | None]` (nullable). Incrementing with `+= cost_minor` when the column is `None` raises `TypeError`.
  **Mitigation:** Use `row.total_cost_minor = (row.total_cost_minor or 0) + cost_minor`. Applied in every `_increment_*` helper.

- **Risk:** Duplicate execution (idempotency). The outbox `max_try=3` makes duplicates rare but possible. Stats are approximate projections — duplicate execution doubles the increment. This is documented as acceptable behavior (criterion 8).
  **Mitigation:** For future improvement, the closing record could be checked for a "processed" flag. Not in scope for this plan.

- **Risk:** Decimal cost computation overflow — `salary_per_hour_before_tax` is `Numeric(12,4)`. Multiplied by a large `interval_seconds` could produce a large number. `int()` truncation is fine.
  **Mitigation:** Use `Decimal` arithmetic, convert to `int` at the end.

---

## Validation plan

Save to `backend/tests/tasks/test_analytics_worker.sh`.

**Note:** Worker tests require running the analytics worker process. The test can verify DB state after the worker processes the outbox event.

```bash
# 1. Run full state transition flow (PENDING → WORKING → COMPLETED)
# 2. Verify ExecutionTask row with type=process_step_transition exists (state=OPEN initially)
# 3. Start analytics worker: `python -m beyo_manager.workers.analytics_worker`
# 4. Wait for task to be claimed and processed
# 5. Verify UserDailyWorkStats row created with total_working_seconds > 0
# 6. Verify UserLifetimeStats updated
# 7. Verify UserSectionDailyWorkStats updated
# 8. Verify WorkingSectionDailyWorkStats updated
# 9. Mark a state record as inaccurate: POST .../mark-inaccurate
# 10. Verify record.recorded_time_marked_wrong=True, step.taken_from_average=True
# 11. Trigger another transition; worker processes it; stats updated (inaccurate records excluded)
```

---

## Review log

_Empty — awaiting implementation._

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
