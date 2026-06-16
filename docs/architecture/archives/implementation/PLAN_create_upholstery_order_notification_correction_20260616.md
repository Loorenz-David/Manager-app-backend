# PLAN_create_upholstery_order_notification_correction_20260616

## Metadata

- Plan ID: `PLAN_create_upholstery_order_notification_correction_20260616`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-16T00:00:00Z`
- Last updated at (UTC): `2026-06-16T13:56:05Z`
- Related issue/ticket: `n/a`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_create_upholstery_order_20260616.md`
- Source review: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_create_upholstery_order_20260616.md`

## Goal and intent

- Goal: Add the missing in-app push notification dispatch to `create_upholstery_order` when requirements are allocated into `ORDERED` state. No new functionality is added; this brings the command into parity with `mark_requirements_ordered`.
- Business/user intent: When an order is created in `ORDERED` state and covers pending requirements, the task owners whose requirements are resolved must receive an in-app notification — identical in shape to the one sent by `mark_requirements_ordered`. Without this correction, order creation silently updates requirement state with no notification to affected users.
- Non-goals: No changes to allocation logic, sorting, inventory mutation, event dispatch, router, or any other file.

## Scope

- In scope:
  - `backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py` — two edits: add imports, add notification block inside the transaction
- Out of scope:
  - All other files in the codebase
  - Allocation algorithm, priority sort, `add_ordered`, event dispatch, router

- Assumptions:
  - `_resolve_upholstery_audience` accepts `item_upholstery_ids: list[str]` where values are `item_upholstery_id` strings — the same values returned by `_allocate_requirements`.
  - `create_instant_task` must be called inside the open transaction so the notification task and the requirement state changes commit atomically.
  - The `NotificationPayload` shape matches the one used in `mark_requirements_ordered` exactly. Codex must read `mark_requirements_ordered.py` to copy the payload verbatim.

## Clarifications required

_(none — the gap and fix are unambiguous)_

## Acceptance criteria

1. When `create_upholstery_order` allocates at least one requirement into `ORDERED` state, a `CREATE_NOTIFICATIONS` instant task is persisted in the same transaction, targeting the resolved audience.
2. When allocation resolves zero requirements, no notification task is created.
3. The notification payload shape (`notification_type`, `title`, `body`, `entity_type`, `entity_client_id`, `exclude_viewing`) matches the one in `mark_requirements_ordered` exactly.
4. The notification block sits inside the `async with ctx.session.begin():` block — before the transaction closes.
5. `py_compile` passes on the changed file after the edit.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: confirms that side-effect tasks (notifications) must be created inside the owning transaction.

### File read intent — pattern vs. relational

All reads in this plan are **relational**:
- Reading `mark_requirements_ordered.py` to copy the exact `NotificationPayload` arguments and import paths — this is understanding what the existing code does, not how to write new code structure.

### Skill selection

- Primary skill: targeted file edits only
- Excluded alternatives: no new service functions, no router changes

## Implementation plan

### File — `backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py`

#### Edit A — Add missing imports

Read `mark_requirements_ordered.py` to confirm the exact import paths, then add the following four imports to the existing import block:

```python
from dataclasses import asdict

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.commands.items._notification_helpers import _resolve_upholstery_audience
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

Place them grouped with the other stdlib/domain/service imports following the existing import ordering convention in the file.

#### Edit B — Add notification block inside the transaction

Current code (inside `async with ctx.session.begin():`, after the `if request.state == UpholsteryOrderStateEnum.ORDERED:` block):

```python
        allocated_item_upholstery_ids: list[str] = []
        if request.state == UpholsteryOrderStateEnum.ORDERED:
            await add_ordered(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_inventory_id=inventory.client_id,
                quantity=request.order_amount_meters,
            )
            allocated_item_upholstery_ids = await _allocate_requirements(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                inventory_id=inventory.client_id,
                order_amount_meters=request.order_amount_meters,
                priority_item_upholstery_ids=request.priority_item_upholstery_ids,
                actor_id=ctx.user_id,
            )
```

Replace with:

```python
        allocated_item_upholstery_ids: list[str] = []
        if request.state == UpholsteryOrderStateEnum.ORDERED:
            await add_ordered(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_inventory_id=inventory.client_id,
                quantity=request.order_amount_meters,
            )
            allocated_item_upholstery_ids = await _allocate_requirements(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                inventory_id=inventory.client_id,
                order_amount_meters=request.order_amount_meters,
                priority_item_upholstery_ids=request.priority_item_upholstery_ids,
                actor_id=ctx.user_id,
            )
            if allocated_item_upholstery_ids:
                target_user_ids = await _resolve_upholstery_audience(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    item_upholstery_ids=allocated_item_upholstery_ids,
                    actor_id=ctx.user_id,
                )
                if target_user_ids:
                    await create_instant_task(
                        session=ctx.session,
                        task_type=TaskType.CREATE_NOTIFICATIONS,
                        payload=asdict(NotificationPayload(
                            notification_type="upholstery_requirement_ordered",
                            user_ids=target_user_ids,
                            title="Requirements ordered",
                            body="Upholstery requirements have been ordered.",
                            entity_type=None,
                            entity_client_id=None,
                            exclude_viewing=[],
                        )),
                    )
```

> **Why inside the `if allocated_item_upholstery_ids:` guard**: The notification is only relevant when at least one requirement was resolved. `_allocate_requirements` returns an empty list when nothing was allocated, so the guard is both correct and avoids an unnecessary DB call.
>
> **Why inside the transaction**: `create_instant_task` writes a row to the execution task table. It must commit atomically with the requirement state changes. If the notification task were created outside the transaction and the transaction failed, a spurious notification would be sent for a state change that never persisted.

## Risks and mitigations

- Risk: `_resolve_upholstery_audience` signature differs from what is assumed here.
  Mitigation: Codex must read `mark_requirements_ordered.py` before writing the call. The import path and call signature must be copied verbatim from that file.

- Risk: `NotificationPayload` field names or defaults differ from what is written in this plan.
  Mitigation: Same — read `mark_requirements_ordered.py` and copy the payload construction verbatim.

## Validation plan

- `python3 -m py_compile backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py`: must pass with no output.
- Grep for `_resolve_upholstery_audience` in the file: must return one match inside `create_upholstery_order.py`.
- Grep for `create_instant_task` in the file: must return one match inside `create_upholstery_order.py`.
- Grep for `asdict` in the file: must return one match in the import and one match at the call site.

## Review log

- `2026-06-16`: Correction plan created from audit of `PLAN_create_upholstery_order_20260616` implementation. Gap identified: `create_upholstery_order` dispatches `item:upholstery-requirement-state-changed` event but does not create an in-app notification task for resolved requirement owners, unlike `mark_requirements_ordered`.
- `2026-06-16`: Added the missing in-transaction notification task creation to `create_upholstery_order`, wrote `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_create_upholstery_order_notification_correction_20260616.md`, and created `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_create_upholstery_order_notification_correction_20260616.md`.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
