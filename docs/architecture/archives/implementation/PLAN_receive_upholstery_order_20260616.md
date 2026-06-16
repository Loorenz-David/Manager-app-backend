# PLAN_receive_upholstery_order_20260616

## Metadata

- Plan ID: `PLAN_receive_upholstery_order_20260616`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-16T00:00:00Z`
- Last updated at (UTC): `2026-06-16T14:28:29Z`
- Related issue/ticket: `n/a`
- Intention plan: `n/a`

## Goal and intent

- Goal: Create the `receive_upholstery_order` command and its router endpoint. The service marks an upholstery order as received (or partially received), updates the inventory by moving the received quantity from ordered → stored, and allocates that quantity across pending requirements (ORDERED first, then NEEDS_ORDERING), marking resolved ones as AVAILABLE.
- Business/user intent: When a fabric order arrives at the workshop, staff records how much arrived. The system tracks cumulative received meters, determines whether the order is fully or partially received, and fulfills pending upholstery requirements from the newly stocked material.
- Non-goals: No changes to existing model files, enum files, or the `_inventory_mutations.py` helper. No migration work. No changes to the create command or its router. No `available_at` timestamp field is added (the model does not have one; `updated_at` auto-stamps via `onupdate`).

## Scope

- In scope:
  - `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py` — append `ReceiveUpholsteryOrderRequest` and `parse_receive_upholstery_order_request`
  - `backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py` — new file: command + private allocation helper
  - `backend/app/beyo_manager/routers/api_v1/upholstery_orders.py` — append new endpoint to the existing router

- Out of scope:
  - `routers/api_v1/__init__.py` — the router file already exists and is registered; no new registration needed
  - Model changes, enum changes, migration files
  - Snapshot of received amount in `UpholsteryOrderHistoryRecord` (model has no `snapshot_received_amount_meters` column; the order's `received_amount_meters` captures cumulative state)

- Assumptions:
  - `received_amount_meters` on `UpholsteryOrder` tracks **cumulative** received meters across all receive calls. Each call adds to it. The guard `(existing + incoming) > order_amount_meters` rejects over-delivery.
  - Only orders in state `ORDERED` or `PARTIALLY_RECEIVED` may be received. All other states raise `ValidationError`.
  - `order.upholstery_inventory_id` is always set when an order was created via the create command (enforced there). A guard is still included for safety.
  - There is no `available_at` column on `ItemUpholsteryRequirement`; `timestamp_field=None` is passed to `run_skip_and_continue_allocation` for the AVAILABLE target state.
  - The `_resolve_upholstery_audience` and `create_instant_task` helpers are used with the same pattern as `create_upholstery_order`. Codex must read `create_upholstery_order.py` to confirm the exact call signatures before writing them.

## Clarifications required

_(none — requirements are fully specified)_

## Acceptance criteria

1. A POST to `/api/v1/upholstery-orders/receive` with a valid `client_id`, `received_amount_meters`, and optional `priority_item_upholstery_ids` / `received_at` succeeds when the order is in `ORDERED` or `PARTIALLY_RECEIVED` state.
2. `received_amount_meters` on the order accumulates across calls: first call at 5m on a 10m order sets it to 5; second call at 3m sets it to 8.
3. When cumulative total equals `order_amount_meters`, state transitions to `RECEIVED`. Otherwise it transitions to `PARTIALLY_RECEIVED`.
4. A request where `(existing + incoming) > order_amount_meters` raises `ValidationError` and makes no writes.
5. A request against an order not in `ORDERED` or `PARTIALLY_RECEIVED` raises `ValidationError`.
6. `confirm_ordered_to_stock` is called with `quantity=request.received_amount_meters` (the incremental amount, not the cumulative total) — this correctly decrements `current_amount_ordered_meters` and increments `current_stored_amount_meters`.
7. Allocation runs skip-and-continue across Tier 1 (priority ids in caller order), Tier 2 (ORDERED requirements not in priority set, `created_at ASC`), Tier 3 (NEEDS_ORDERING requirements not in priority set, `created_at ASC`). A candidate that doesn't fit is skipped — smaller later candidates still get allocated.
8. Resolved requirements are stamped with `updated_by_id = ctx.user_id` and transition to `AVAILABLE`.
9. When at least one requirement is resolved, a `CREATE_NOTIFICATIONS` instant task is persisted in the same transaction.
10. Post-commit events `upholstery:order-received` and (if any allocated) `item:upholstery-requirement-state-changed` are dispatched.
11. An `UpholsteryOrderHistoryRecord` is appended for every state transition.
12. `py_compile` passes on all three changed files.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: transaction ownership, flush discipline, post-commit event dispatch, subordinate-command call rules.
- `backend/architecture/09_routers.md`: thin handler, `_Body` model, `ServiceContext`, `run_service`, `build_ok`/`build_err`.
- `backend/architecture/05_errors.md`: `ValidationError`, `NotFound` import paths and usage rules.
- `backend/architecture/42_event.md`: event bus dispatch shape, `WorkspaceEvent`.

### File read intent — pattern vs. relational

Permitted relational reads (understanding what exists):
- `create_upholstery_order.py` — to copy exact `_resolve_upholstery_audience` / `create_instant_task` / `NotificationPayload` call shapes and import paths
- `_inventory_mutations.py` — to confirm `confirm_ordered_to_stock` signature (already provided in this plan)
- `upholstery_orders.py` (router) — to see exactly where to append the new endpoint without breaking the existing one

Prohibited pattern reads:
- Reading other commands to understand `session.add / flush / error-raising` shape → `06_commands.md` covers this
- Reading other routers for handler skeleton → `09_routers.md` covers this

### Skill selection

- Primary skill: command + router addition; no new model or migration

## Implementation plan

---

### Step 1 — Request model

**File**: `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`

Append after the last existing class and parser (`UpdateUpholsteryListOrderRequest` / `parse_update_upholstery_list_order_request`).

```python
class ReceiveUpholsteryOrderRequest(BaseModel):
    client_id: str
    received_amount_meters: Decimal
    priority_item_upholstery_ids: list[str] = []
    received_at: datetime | None = None

    @field_validator("received_amount_meters")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("received_amount_meters must be > 0.")
        return v


def parse_receive_upholstery_order_request(data: dict) -> ReceiveUpholsteryOrderRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return ReceiveUpholsteryOrderRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

No new imports are needed in this file — `Decimal` and `datetime` are already present.

---

### Step 2 — Command

**File**: `backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py` (new file)

```python
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.upholstery.enums import UpholsteryOrderStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.models.tables.upholstery.upholstery_order_history_record import UpholsteryOrderHistoryRecord
from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation
from beyo_manager.services.commands.items._notification_helpers import _resolve_upholstery_audience
from beyo_manager.services.commands.upholstery._inventory_mutations import confirm_ordered_to_stock
from beyo_manager.services.commands.upholstery.requests import parse_receive_upholstery_order_request
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task

_RECEIVABLE_STATES = {
    UpholsteryOrderStateEnum.ORDERED,
    UpholsteryOrderStateEnum.PARTIALLY_RECEIVED,
}


async def receive_upholstery_order(ctx: ServiceContext) -> dict:
    request = parse_receive_upholstery_order_request(ctx.incoming_data)

    async with ctx.session.begin():
        order = await ctx.session.get(UpholsteryOrder, request.client_id)
        if order is None or order.workspace_id != ctx.workspace_id or order.is_deleted:
            raise NotFound("Upholstery order not found.")

        if order.state not in _RECEIVABLE_STATES:
            raise ValidationError(
                "Order must be in ORDERED or PARTIALLY_RECEIVED state to record a receipt."
            )

        if order.upholstery_inventory_id is None:
            raise ValidationError(
                "Order has no linked inventory — cannot confirm stock."
            )

        cumulative = (order.received_amount_meters or Decimal("0")) + request.received_amount_meters
        if cumulative > order.order_amount_meters:
            raise ValidationError(
                "Received amount exceeds the ordered amount. "
                f"Maximum receivable: {order.order_amount_meters - (order.received_amount_meters or Decimal('0'))} m."
            )

        new_state = (
            UpholsteryOrderStateEnum.RECEIVED
            if cumulative == order.order_amount_meters
            else UpholsteryOrderStateEnum.PARTIALLY_RECEIVED
        )

        received_at = request.received_at or datetime.now(timezone.utc)

        order.state = new_state
        order.received_amount_meters = cumulative
        order.received_at = received_at
        order.updated_by_id = ctx.user_id
        await ctx.session.flush()

        history = UpholsteryOrderHistoryRecord(
            workspace_id=ctx.workspace_id,
            upholstery_order_id=order.client_id,
            state=new_state,
            changed_at=received_at,
            snapshot_price_minor=order.price_minor,
            snapshot_currency=order.currency,
            snapshot_order_amount_meters=order.order_amount_meters,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(history)

        await confirm_ordered_to_stock(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=order.upholstery_inventory_id,
            quantity=request.received_amount_meters,
        )

        allocated_item_upholstery_ids = await _allocate_received_requirements(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            inventory_id=order.upholstery_inventory_id,
            received_amount_meters=request.received_amount_meters,
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
                        notification_type="upholstery_requirement_available",
                        user_ids=target_user_ids,
                        title="Upholstery available",
                        body="Upholstery requirements are now available for production.",
                        entity_type=None,
                        entity_client_id=None,
                        exclude_viewing=[],
                    )),
                )

    await event_bus.dispatch(
        [
            WorkspaceEvent(
                event_name="upholstery:order-received",
                client_id=order.client_id,
                workspace_id=ctx.workspace_id,
                extra={"state": order.state.value},
            ),
        ]
    )
    if allocated_item_upholstery_ids:
        await event_bus.dispatch(
            [
                WorkspaceEvent(
                    event_name="item:upholstery-requirement-state-changed",
                    client_id="",
                    workspace_id=ctx.workspace_id,
                    extra={
                        "ids": allocated_item_upholstery_ids,
                        "new_state": ItemUpholsteryRequirementStateEnum.AVAILABLE.value,
                    },
                ),
            ]
        )

    return {"client_id": order.client_id}


async def _allocate_received_requirements(
    session: AsyncSession,
    workspace_id: str,
    inventory_id: str,
    received_amount_meters: Decimal,
    priority_item_upholstery_ids: list[str],
    actor_id: str,
) -> list[str]:
    req_result = await session.execute(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.workspace_id == workspace_id,
            ItemUpholsteryRequirement.upholstery_inventory_id == inventory_id,
            ItemUpholsteryRequirement.state.in_([
                ItemUpholsteryRequirementStateEnum.ORDERED,
                ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
            ]),
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
    )
    candidates = req_result.scalars().all()
    if not candidates:
        return []

    priority_set = set(priority_item_upholstery_ids)
    priority_order = {
        item_upholstery_id: index
        for index, item_upholstery_id in enumerate(priority_item_upholstery_ids)
    }

    tier1 = sorted(
        [req for req in candidates if req.item_upholstery_id in priority_set],
        key=lambda req: priority_order.get(
            req.item_upholstery_id, len(priority_item_upholstery_ids)
        ),
    )
    tier2 = sorted(
        [
            req for req in candidates
            if req.item_upholstery_id not in priority_set
            and req.state == ItemUpholsteryRequirementStateEnum.ORDERED
        ],
        key=lambda req: req.created_at,
    )
    tier3 = sorted(
        [
            req for req in candidates
            if req.item_upholstery_id not in priority_set
            and req.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
        ],
        key=lambda req: req.created_at,
    )
    ordered_candidates = tier1 + tier2 + tier3

    result = run_skip_and_continue_allocation(
        candidates=ordered_candidates,
        running_pool=received_amount_meters,
        target_state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        timestamp_field=None,
    )

    resolved_set = set(result["resolved"])
    for req in ordered_candidates:
        if req.item_upholstery_id in resolved_set:
            req.updated_by_id = actor_id

    return result["resolved"]
```

**Key design decisions documented:**

- `timestamp_field=None`: `ItemUpholsteryRequirement` has no `available_at` column. The `onupdate` lambda on `updated_at` stamps the row automatically on flush.
- Tier 1 includes requirements of any target state (ORDERED or NEEDS_ORDERING) that appear in `priority_item_upholstery_ids`. The caller decides which items are priority — the system doesn't filter by state for the priority tier.
- `confirm_ordered_to_stock` is called with `request.received_amount_meters` (incremental), not `cumulative`. This correctly moves only the newly received meters from ordered→stored. Calling it with the cumulative total would double-count previous partial receipts.
- The `_RECEIVABLE_STATES` module-level set avoids repeating the literal set in the guard.

---

### Step 3 — Router endpoint

**File**: `backend/app/beyo_manager/routers/api_v1/upholstery_orders.py`

Add the following import and body model and handler to the existing file. Do not modify the existing `router` declaration or the `route_create_upholstery_order` handler.

New import to add to the existing import block:
```python
from beyo_manager.services.commands.upholstery.receive_upholstery_order import receive_upholstery_order
```

New body model and handler to append after the existing handler:

```python
class _ReceiveBody(BaseModel):
    client_id: str
    received_amount_meters: Decimal
    priority_item_upholstery_ids: list[str] = []
    received_at: datetime | None = None


@router.post("/receive")
async def route_receive_upholstery_order(
    body: _ReceiveBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(receive_upholstery_order, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Note on `datetime` import**: `datetime` is already imported in the file for the existing `_CreateBody`. No new import needed for the body model.

---

## Risks and mitigations

- Risk: `confirm_ordered_to_stock` raises `ValidationError` ("Confirmed quantity exceeds the recorded ordered amount") if `current_amount_ordered_meters` on the inventory is less than `request.received_amount_meters`. This can happen if the order's inventory counter was not incremented at creation (e.g., order was created in DRAFT state and never transitioned).
  Mitigation: This is a legitimate guard — the error is intentional and surfaces a real data inconsistency. No special handling needed.

- Risk: `Tier 1` items may include requirements in `NEEDS_ORDERING` state. This is intentional — the caller explicitly prioritized them. But mixing ORDERED and NEEDS_ORDERING requirements in Tier 1 means a NEEDS_ORDERING item could jump ahead of an ORDERED item.
  Mitigation: This is by design — the priority list is caller-driven. Document in the plan so it is clear this is not a bug.

- Risk: `result["resolved"]` from `run_skip_and_continue_allocation` contains `item_upholstery_id` values. Verifying this against the algorithm source: the function appends `req.item_upholstery_id` to `resolved`. This matches `_allocate_requirements` in `create_upholstery_order.py`.
  Mitigation: Codex should verify by reading `_allocation_algorithm.py` before writing the return handling.

- Risk: `order.received_at` gets overwritten on every call. An order that was partially received at time T1 and then fully received at time T2 will have `received_at = T2`.
  Mitigation: This is intentional — `received_at` records the last receipt event. The history records capture each event with its own `changed_at` timestamp. This is consistent with how `failed_at`, `cancelled_at` work on the order model.

## Validation plan

- `python3 -m py_compile backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py backend/app/beyo_manager/routers/api_v1/upholstery_orders.py`: must pass with no output.
- `rg -n "receive_upholstery_order" backend/app/beyo_manager/routers/api_v1/upholstery_orders.py`: must return the import line and the handler decorator line.
- `rg -n "ReceiveUpholsteryOrderRequest" backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`: must return the class definition and parser return type.
- `rg -n "confirm_ordered_to_stock" backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py`: must return one import and one call site.

## Review log

- `2026-06-16`: Plan authored from audit session. Three-tier sort differs from `create_upholstery_order` by replacing the deadline (ready_by_at) secondary sort with a state-based split (ORDERED before NEEDS_ORDERING) — both resolve to oldest-first within tier, consistent with the "oldest record wins" tie-breaker rule.
- `2026-06-16`: Implemented the receive-order command and router endpoint, wrote `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_receive_upholstery_order_20260616.md`, and prepared this plan for archival.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
