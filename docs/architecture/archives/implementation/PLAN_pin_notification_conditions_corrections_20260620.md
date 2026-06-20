# PLAN_pin_notification_conditions_corrections_20260620

## Metadata

- Plan ID: `PLAN_pin_notification_conditions_corrections_20260620`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-20T00:00:00Z`
- Last updated at (UTC): `2026-06-20T12:42:01Z`
- Related issue/ticket: `review of SUMMARY_PLAN_pin_notification_conditions_20260619`

## Goal and intent

- Goal: Apply the six corrections and improvements identified in the post-implementation review of the pin notification conditions feature.
- Business/user intent: Harden the pin conditions system before the frontend consumes it. The critical missing piece is `cleanup_task_pins`, which prevents pin accumulation for deleted tasks. The remaining items fix a transaction pattern inconsistency, an evaluation path that can raise instead of returning False, a DRY violation across two domain modules, a missing warning log, and a documentation gap.
- Non-goals: No schema changes. No new features beyond what the review identified. No changes to the `time` condition evaluation (intentionally deferred).

## Scope

- In scope:
  - Fix `pin_notification.py`: swap `ctx.session.begin()` → `maybe_begin(ctx.session)`.
  - Fix `_evaluate_state_condition`: make it never raise; inline the op-switch instead of calling `_state_condition_values`.
  - Add a structured warning log to `pin_conditions_match` when a condition type is missing from the registry.
  - Extract shared `_get_managers` to `domain/roles/queries.py` and update both callers.
  - Document in `47_notifications_local.md` that state conditions are only supported for TASK, TASK_STEP, ITEM_UPHOLSTERY.
  - Implement `domain/notifications/pin_cleanup.py` with `cleanup_task_pins(session, task_client_id)`.
  - Wire `cleanup_task_pins` into `delete_task.py` inside the existing `maybe_begin` block.
- Out of scope:
  - `time` condition evaluation.
  - Frontend UI for composing conditions.
  - An explicit `unpin_notification` service command.
  - Any migration or schema change.
- Assumptions:
  - `ItemUpholstery.item_id` is the correct FK to join from `TaskItem.item_id`.
  - `CaseLink.entity_type == CaseLinkEntityTypeEnum.TASK` and `CaseLink.entity_client_id == task_client_id` is the correct path to find cases linked to a task.
  - Cleanup runs unconditionally on task deletion regardless of cross-entity sharing (task is root authority).

## Clarifications required

_None — all decisions confirmed during the review conversation._

## Acceptance criteria

1. `pin_notification.py` uses `maybe_begin(ctx.session)` and does not call `ctx.session.begin()` directly.
2. `_evaluate_state_condition` returns `False` (never raises) for any unrecognized or malformed op value.
3. `pin_conditions_match` emits a `logging.warning` and returns `False` when a condition type is absent from the registry.
4. `domain/roles/queries.py` exports `get_manager_user_ids(session, workspace_id) -> set[str]`; the `_get_managers` private function is removed from both `domain/tasks/notification_targets.py` and `domain/items/notification_targets.py`.
5. `47_notifications_local.md` documents that state conditions are only supported for TASK, TASK_STEP, and ITEM_UPHOLSTERY entity types.
6. `domain/notifications/pin_cleanup.py` exists with `cleanup_task_pins(session, task_client_id)` that deletes all `NotificationPin` rows for: (a) the task itself, (b) all its task steps, (c) all item upholsteries for items linked to the task, (d) all cases linked to the task via `CaseLink`.
7. `delete_task.py` calls `cleanup_task_pins` inside its `maybe_begin` block after the soft-delete mutation.
8. `py_compile` passes on all changed modules.
9. Existing tests in `test_pin_conditions.py` and `test_transition_step_state.py` continue to pass.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: all commands must use `maybe_begin` for transaction boundaries — fixes Step 1.
- `backend/architecture/08_domain.md`: domain modules are pure or DB-isolated; shared domain utilities are acceptable in peer domain packages — supports Step 4.
- `backend/architecture/47_notifications.md`: pin resolution semantics and pin identity — informs Steps 6–7.

### Local extensions loaded

- `backend/architecture/47_notifications_local.md`: conditions JSONB, fire_once bool, last-write-wins re-pin — updated in Step 5.

### Skill selection

- Primary skill: _no specialized skill required_
- Router trigger terms: `pin_notification`, `cleanup`, `notification_targets`
- Excluded alternatives: _none_

## Implementation plan

### Step 1 — Fix `pin_notification.py` transaction pattern

**File:** `backend/app/beyo_manager/services/commands/notifications/pin_notification.py`

Replace:
```python
async with ctx.session.begin():
```
With:
```python
async with maybe_begin(ctx.session):
```

Add the import:
```python
from beyo_manager.services.commands.utils.transaction import maybe_begin
```

---

### Step 2 — Fix `_evaluate_state_condition` to never raise

**File:** `backend/app/beyo_manager/domain/notifications/pin_conditions.py`

Replace the entire `_evaluate_state_condition` function body so it inlines the op dispatch without calling `_state_condition_values`. The new implementation must return `False` for any op it does not recognize:

```python
def _evaluate_state_condition(condition: PinCondition, event_facts: EventFacts) -> bool:
    state = event_facts.get("state")
    if not isinstance(state, str):
        return False
    op = condition.get("op")
    raw_value = condition.get("value")
    if op == "eq":
        return isinstance(raw_value, str) and state == raw_value
    if op == "in":
        return isinstance(raw_value, list) and state in raw_value
    if op == "not_in":
        return isinstance(raw_value, list) and state not in raw_value
    return False
```

`_state_condition_values` is retained as-is because it is still used by `_validate_state_condition` at write time (where raising is correct behavior).

---

### Step 3 — Add warning log to `pin_conditions_match`

**File:** `backend/app/beyo_manager/domain/notifications/pin_conditions.py`

Add at module top:
```python
import logging

_logger = logging.getLogger(__name__)
```

In `pin_conditions_match`, replace the silent `return False` branch when `handler is None`:
```python
handler = PIN_CONDITION_REGISTRY.get(str(condition_type))
if handler is None:
    _logger.warning("Unknown pin condition type %r — pin will not match.", condition_type)
    return False
```

---

### Step 4 — Extract shared `_get_managers` to `domain/roles/queries.py`

**New file:** `backend/app/beyo_manager/domain/roles/queries.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def get_manager_user_ids(session: AsyncSession, workspace_id: str) -> set[str]:
    rows = await session.execute(
        select(WorkspaceMembership.user_id)
        .join(WorkspaceRole, WorkspaceMembership.workspace_role_id == WorkspaceRole.client_id)
        .join(Role, WorkspaceRole.role_id == Role.client_id)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.is_active.is_(True),
            Role.name == RoleNameEnum.MANAGER,
        )
        .distinct()
    )
    return set(rows.scalars().all())
```

**Update `domain/tasks/notification_targets.py`:**
- Remove the `_get_managers` private function and its imports (`Role`, `WorkspaceRole`, `WorkspaceMembership`, `RoleNameEnum`).
- Add import: `from beyo_manager.domain.roles.queries import get_manager_user_ids`
- In `resolve_task_notification_targets`, replace `_get_managers(session, workspace_id)` with `get_manager_user_ids(session, workspace_id)`.

**Update `domain/items/notification_targets.py`:**
- Remove the `_get_managers` private function and its imports (`Role`, `WorkspaceRole`, `WorkspaceMembership`, `RoleNameEnum`).
- Add import: `from beyo_manager.domain.roles.queries import get_manager_user_ids`
- In `resolve_upholstery_notification_targets`, replace `_get_managers(session, workspace_id)` with `get_manager_user_ids(session, workspace_id)`.

---

### Step 5 — Document entity type state condition scope in `47_notifications_local.md`

**File:** `backend/architecture/47_notifications_local.md`

In the **Local Decisions** section, add after the existing `fire_once` bullet:

```
- State conditions are validated against a per-entity-type enum registry. They are
  currently supported for TASK, TASK_STEP, and ITEM_UPHOLSTERY only. Attempting to
  set a state condition on CASE, CONVERSATION, or other entity types raises a
  ValidationError at pin creation time.
```

---

### Step 6 — Implement `domain/notifications/pin_cleanup.py`

**New file:** `backend/app/beyo_manager/domain/notifications/pin_cleanup.py`

The function collects all entity client_ids reachable from the task, then issues targeted deletes against `NotificationPin`. All collection queries run concurrently via `asyncio.gather`. Deletes are skipped when the collected id list is empty.

Entity graph covered:
| Pin entity_type   | Source path                                                    |
|-------------------|----------------------------------------------------------------|
| `task`            | `task_client_id` directly                                      |
| `task_step`       | `TaskStep.client_id WHERE task_id = task_client_id`            |
| `item_upholstery` | `ItemUpholstery.client_id` via `TaskItem.item_id` join         |
| `case`            | `CaseLink.case_id WHERE entity_type=task AND entity_client_id=task_client_id` |

```python
import asyncio

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep


async def cleanup_task_pins(session: AsyncSession, task_client_id: str) -> None:
    step_ids, upholstery_ids, case_ids = await asyncio.gather(
        _get_step_ids(session, task_client_id),
        _get_upholstery_ids(session, task_client_id),
        _get_case_ids(session, task_client_id),
    )

    await session.execute(
        delete(NotificationPin).where(
            NotificationPin.entity_type == EntityType.TASK.value,
            NotificationPin.entity_client_id == task_client_id,
        )
    )

    if step_ids:
        await session.execute(
            delete(NotificationPin).where(
                NotificationPin.entity_type == EntityType.TASK_STEP.value,
                NotificationPin.entity_client_id.in_(step_ids),
            )
        )

    if upholstery_ids:
        await session.execute(
            delete(NotificationPin).where(
                NotificationPin.entity_type == EntityType.ITEM_UPHOLSTERY.value,
                NotificationPin.entity_client_id.in_(upholstery_ids),
            )
        )

    if case_ids:
        await session.execute(
            delete(NotificationPin).where(
                NotificationPin.entity_type == EntityType.CASE.value,
                NotificationPin.entity_client_id.in_(case_ids),
            )
        )


async def _get_step_ids(session: AsyncSession, task_client_id: str) -> list[str]:
    rows = await session.execute(
        select(TaskStep.client_id).where(TaskStep.task_id == task_client_id)
    )
    return list(rows.scalars().all())


async def _get_upholstery_ids(session: AsyncSession, task_client_id: str) -> list[str]:
    rows = await session.execute(
        select(ItemUpholstery.client_id).where(
            ItemUpholstery.item_id.in_(
                select(TaskItem.item_id).where(TaskItem.task_id == task_client_id)
            )
        )
    )
    return list(rows.scalars().all())


async def _get_case_ids(session: AsyncSession, task_client_id: str) -> list[str]:
    rows = await session.execute(
        select(CaseLink.case_id).where(
            CaseLink.entity_type == CaseLinkEntityTypeEnum.TASK,
            CaseLink.entity_client_id == task_client_id,
        )
    )
    return list(rows.scalars().all())
```

---

### Step 7 — Wire `cleanup_task_pins` into `delete_task.py`

**File:** `backend/app/beyo_manager/services/commands/tasks/delete_task.py`

Add import:
```python
from beyo_manager.domain.notifications.pin_cleanup import cleanup_task_pins
```

Inside the `maybe_begin` block, after the history record write and before the block closes, add:
```python
await cleanup_task_pins(ctx.session, task.client_id)
```

The call must be inside `maybe_begin` so the pin deletes commit atomically with the soft-delete mutation.

---

## Risks and mitigations

- Risk: `_get_upholstery_ids` returns upholsteries for items that were removed from the task (removed_at IS NOT NULL). This causes cleanup of pins the user set on items that were previously removed from the task.
  Mitigation: Acceptable — the task is being deleted and is the root authority. Cleaning up all reachable pins (including removed items) is the desired behavior per the task-driven design.

- Risk: `cleanup_task_pins` could delete case pins for cases shared across multiple tasks.
  Mitigation: Accepted trade-off. The user explicitly confirmed task is the termination authority. Document in the function docstring that cleanup is unconditional.

- Risk: `maybe_begin` wraps an existing transaction in `delete_task.py` — the pin deletes and soft-delete are now a single atomic unit. If pin cleanup fails, the task deletion rolls back.
  Mitigation: Desired behavior — partial deletion is worse than a clean rollback.

## Validation plan

- `py_compile` on all changed and new modules:
  - `backend/app/beyo_manager/services/commands/notifications/pin_notification.py`
  - `backend/app/beyo_manager/domain/notifications/pin_conditions.py`
  - `backend/app/beyo_manager/domain/roles/queries.py`
  - `backend/app/beyo_manager/domain/tasks/notification_targets.py`
  - `backend/app/beyo_manager/domain/items/notification_targets.py`
  - `backend/app/beyo_manager/domain/notifications/pin_cleanup.py`
  - `backend/app/beyo_manager/services/commands/tasks/delete_task.py`

- `pytest tests/unit/domain/notifications/test_pin_conditions.py`: all 7 tests pass.
- `pytest tests/unit/services/commands/task_steps/test_transition_step_state.py`: passes.
- `rg -n "_get_managers" backend/app/beyo_manager`: zero results (function fully removed from notification_targets modules).
- `rg -n "ctx.session.begin\(\)" backend/app/beyo_manager/services/commands`: zero results.

## Review log

- `2026-06-20` `claude-sonnet-4-6`: Post-implementation review of PLAN_pin_notification_conditions_20260619. Identified 6 items: transaction pattern drift, evaluate-path raise risk, _get_managers duplication, missing warning log, undocumented CASE state condition gap, missing cleanup_task_pins helper.

## Lifecycle transition

- Current state: `archived`
- Next state: _none_
- Transition owner: `codex`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_pin_notification_conditions_corrections_20260620.md`
- Archive record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_pin_notification_conditions_corrections_20260620.md`
