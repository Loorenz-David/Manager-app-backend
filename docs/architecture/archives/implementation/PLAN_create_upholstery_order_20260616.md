# PLAN_create_upholstery_order_20260616

## Metadata

- Plan ID: `PLAN_create_upholstery_order_20260616`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-06-16T14:00:00Z`
- Last updated at (UTC): `2026-06-16T13:34:05Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/planning_tables/upholstery/upholstery_order_models.md`

## Goal and intent

- Goal: Implement a `create_upholstery_order` command and a `PUT /api/v1/upholstery-orders` route that creates an `UpholsteryOrder` row, appends an initial `UpholsteryOrderHistoryRecord`, and — only when `state == ORDERED` — increments `current_amount_ordered_meters` on the linked `UpholsteryInventory` and allocates the ordered quantity to eligible `ItemUpholsteryRequirement` rows (state `NEEDS_ORDERING`) in priority order.
- Business/user intent: Users need to record that upholstery material has been ordered from a supplier. When the order is placed (`ORDERED`), inventory tracking is immediately updated and as many waiting requirements as possible are advanced to `ORDERED` state, prioritising explicitly named item-upholstery links, then those with the earliest task deadline, then oldest by creation time. The frontend controls the order record's `client_id` via optimistic updates.
- Non-goals: Order state transitions after creation (DRAFT → ORDERED etc.), order listing/get queries, supplier or supplier-link CRUD, Alembic migration.

## Scope

- In scope:
  - Append `CreateUpholsteryOrderRequest` + `parse_create_upholstery_order_request` to `services/commands/upholstery/requests/__init__.py`
  - New file `services/commands/upholstery/create_upholstery_order.py`
  - New file `routers/api_v1/upholstery_orders.py`
  - Update `routers/api_v1/__init__.py` — import and register the new router

- Out of scope:
  - Changes to `mark_requirements_ordered.py` (used as reference only; not called by this command)
  - Commands for order state transitions, order deletion, or listing
  - Commands for `Supplier` or `UpholsterySupplierLink` CRUD

- Assumptions:
  - `UpholsteryOrder`, `UpholsteryOrderHistoryRecord`, `UpholsteryOrderStateEnum` are already defined and registered (from `PLAN_upholstery_order_models_20260616`).
  - `add_ordered` from `_inventory_mutations.py` increments `current_amount_ordered_meters`; it flushes but does not commit, so it is safe to call inside `ctx.session.begin()`.
  - `run_skip_and_continue_allocation` from `services/commands/items/_allocation_algorithm.py` is the allocation engine; it mutates ORM objects in-place and returns `AllocationResult` with `resolved` and `unresolved` lists of `item_upholstery_id` values.
  - `validate_provided_client_id` from `services/commands/utils/client_id.py` validates prefix and format of a caller-supplied `client_id`.
  - The join path from `ItemUpholsteryRequirement` to `Task.ready_by_at` is: `ItemUpholsteryRequirement.item_upholstery_id` → `ItemUpholstery.client_id` → `ItemUpholstery.item_id` → `TaskItem.item_id` → `TaskItem.task_id` → `Task.client_id` → `Task.ready_by_at`. Both `TaskItem` and `Task` must be outer-joined (not all items belong to tasks with deadlines).
  - `ItemUpholsteryRequirement.upholstery_inventory_id` is the correct field to filter requirements by inventory — requirements link to inventory, not to upholstery directly.
  - The `task_items` bridge is the only path from `Item` to `Task`; `Item` has no direct `task_id` FK.

## Clarifications required

- [x] Are `priority_item_upholstery_ids` in the request `ItemUpholsteryRequirement.client_id` values or `item_upholstery_id` values (FK to `item_upholsteries`)? — **Resolved: `item_upholstery_id` values.** The field is named `priority_item_upholstery_ids` and the tier1 sort key uses `r.item_upholstery_id`. This matches the shape of `mark_requirements_ordered`.
- [x] Should requirement allocation (NEEDS_ORDERING → ORDERED) execute for all creation states, or only when state == `ORDERED`? — **Resolved: only when `state == ORDERED`.**
- [x] Should `current_amount_ordered_meters` on inventory be incremented for all creation states, or only for `ORDERED`? — **Resolved: only when `state == ORDERED`.** Both the `add_ordered` call and the allocation are gated on the same condition. Future state-transition commands (DRAFT/PENDING/APPROVED → ORDERED) must handle the inventory increment and allocation at that point.

## Acceptance criteria

1. `PUT /api/v1/upholstery-orders` with `{"upholstery_id": "uph_...", "order_amount_meters": "10.000"}` returns `{"client_id": "uor_..."}`.
2. A caller-supplied `client_id` (prefix `uor`) is used if provided; a 409 is returned if it is already in use.
3. An `UpholsteryOrder` row is persisted with `state = ORDERED` (default) and `upholstery_inventory_id` set to the active inventory record for the given upholstery.
4. An `UpholsteryOrderHistoryRecord` row is appended in the same transaction, snapshotting the initial state, price, currency, and amount.
5. When `state == ORDERED`: `UpholsteryInventory.current_amount_ordered_meters` is incremented by `order_amount_meters` in the same transaction.
6. When `state == ORDERED`: `NEEDS_ORDERING` requirements linked to the inventory are advanced to `ORDERED` state (skip-and-continue) in order: `priority_item_upholstery_ids` first (in list order by `item_upholstery_id`), then by earliest `task.ready_by_at` ASC (nulls last), then by oldest `created_at` ASC.
7. Passing `state = "draft"` creates the order row and history record only — no inventory increment, no requirement allocation.
8. Passing `state = "failed"` or `"cancelled"` returns a 422 validation error.
9. Passing an unknown `upholstery_id` (no active inventory) returns a 404.
10. Post-commit realtime events are dispatched for the new order and for any requirements whose state changed.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: transaction pattern via `ctx.session.begin()`, request parser in `requests/__init__.py`, no cross-command calls, flush-not-commit for helpers, event dispatch after commit
- `backend/architecture/09_routers.md`: router skeleton, `build_ok`/`build_err`, `ServiceContext` construction, `run_service`, role guards

### Local extensions loaded

- None

### File read intent — pattern vs. relational

Permitted relational reads:
- `services/commands/upholstery/requests/__init__.py` — existing parser pattern to append after (required before editing)
- `services/commands/upholstery/_inventory_mutations.py` — `add_ordered` exact signature: `(session, workspace_id, upholstery_inventory_id, quantity)` → `None`; flushes internally
- `services/commands/items/_allocation_algorithm.py` — `run_skip_and_continue_allocation` signature and `AllocationResult` shape
- `services/commands/items/mark_requirements_ordered.py` — event dispatch shape to match
- `routers/api_v1/upholstery_inventories.py` — router skeleton and `ServiceContext` construction pattern
- `routers/api_v1/__init__.py` — registration block location to append after (required before editing)
- `models/tables/items/item_upholstery.py` — `item_id` field name for join
- `models/tables/tasks/task_item.py` — `item_id` and `task_id` field names; verify `is_deleted` presence
- `models/tables/tasks/task.py` — confirm `ready_by_at` field name and type

Prohibited (pattern reads — contract already covers these):
- Reading another command file to understand `session.add` / flush shape → `06_commands.md`
- Reading another router file to understand handler skeleton → `09_routers.md`

### Skill selection

- Primary skill: command + router authoring
- Router trigger terms: none (standard CRUD)
- Excluded alternatives: none

## Implementation plan

### Step 1 — Request parser

**File:** `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`

Append after the last existing class and parser in the file:

```python
class CreateUpholsteryOrderRequest(BaseModel):
    client_id: str | None = None
    upholstery_id: str
    order_amount_meters: Decimal
    priority_item_upholstery_ids: list[str] = []
    state: UpholsteryOrderStateEnum = UpholsteryOrderStateEnum.ORDERED
    supplier_id: str | None = None
    upholstery_supplier_link_id: str | None = None
    price_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    order_at: datetime | None = None
    expected_receive_at: datetime | None = None

    @field_validator("state")
    @classmethod
    def validate_creation_state(cls, v: UpholsteryOrderStateEnum) -> UpholsteryOrderStateEnum:
        allowed = {
            UpholsteryOrderStateEnum.DRAFT,
            UpholsteryOrderStateEnum.PENDING,
            UpholsteryOrderStateEnum.APPROVED,
            UpholsteryOrderStateEnum.ORDERED,
        }
        if v not in allowed:
            raise ValueError("state on creation must be one of: draft, pending, approved, ordered.")
        return v

    @field_validator("order_amount_meters")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("order_amount_meters must be > 0.")
        return v

    @field_validator("price_minor")
    @classmethod
    def price_must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("price_minor must be >= 0.")
        return v


def parse_create_upholstery_order_request(data: dict) -> CreateUpholsteryOrderRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return CreateUpholsteryOrderRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

Add the following imports to the top of the file (only those not already present):

```python
from datetime import datetime
from beyo_manager.domain.upholstery.enums import UpholsteryOrderStateEnum  # add alongside UpholsteryCurrencyEnum
```

`UpholsteryCurrencyEnum` is already imported. `datetime` may already be imported — verify before adding.

---

### Step 2 — Command: `create_upholstery_order.py`

**File:** `backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py` (new file)

```python
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.upholstery.enums import UpholsteryOrderStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.supplier import Supplier
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder
from beyo_manager.models.tables.upholstery.upholstery_order_history_record import UpholsteryOrderHistoryRecord
from beyo_manager.models.tables.upholstery.upholstery_supplier_link import UpholsterySupplierLink
from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation
from beyo_manager.services.commands.upholstery._inventory_mutations import add_ordered
from beyo_manager.services.commands.upholstery.requests import parse_create_upholstery_order_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def create_upholstery_order(ctx: ServiceContext) -> dict:
    request = parse_create_upholstery_order_request(ctx.incoming_data)

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "uor")

    async with ctx.session.begin():
        # 1. Validate caller-supplied client_id uniqueness
        if request.client_id is not None:
            if await ctx.session.get(UpholsteryOrder, request.client_id) is not None:
                raise ConflictError("Provided client_id is already in use.")

        # 2. Resolve upholstery → active inventory
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == request.upholstery_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inventory = inv_result.scalar_one_or_none()
        if inventory is None:
            raise NotFound("No active inventory record found for the given upholstery_id.")

        # 3. Validate optional supplier_id
        if request.supplier_id is not None:
            supplier = await ctx.session.get(Supplier, request.supplier_id)
            if supplier is None or supplier.workspace_id != ctx.workspace_id or supplier.is_deleted:
                raise NotFound("Supplier not found.")

        # 4. Validate optional upholstery_supplier_link_id
        if request.upholstery_supplier_link_id is not None:
            link = await ctx.session.get(UpholsterySupplierLink, request.upholstery_supplier_link_id)
            if link is None or link.workspace_id != ctx.workspace_id or link.is_deleted:
                raise NotFound("UpholsterySupplierLink not found.")

        # 5. Create UpholsteryOrder
        order_kwargs = {}
        if request.client_id is not None:
            order_kwargs["client_id"] = request.client_id

        order = UpholsteryOrder(
            **order_kwargs,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=inventory.client_id,
            upholstery_supplier_link_id=request.upholstery_supplier_link_id,
            supplier_id=request.supplier_id,
            order_amount_meters=request.order_amount_meters,
            price_minor=request.price_minor,
            currency=request.currency,
            order_at=request.order_at,
            state=request.state,
            ordered_by_id=ctx.user_id,
            expected_receive_at=request.expected_receive_at,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(order)
        await ctx.session.flush()  # assigns client_id before history record FK

        # 6. Append initial history record (always, regardless of state)
        history = UpholsteryOrderHistoryRecord(
            workspace_id=ctx.workspace_id,
            upholstery_order_id=order.client_id,
            state=order.state,
            changed_at=datetime.now(timezone.utc),
            snapshot_price_minor=order.price_minor,
            snapshot_currency=order.currency,
            snapshot_order_amount_meters=order.order_amount_meters,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(history)

        # 7 & 8. When state is ORDERED: increment inventory counter and allocate requirements
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

    # 9. Post-commit event dispatch
    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="upholstery:order-created",
            client_id=order.client_id,
            workspace_id=ctx.workspace_id,
            extra={"state": order.state.value},
        ),
    ])
    if allocated_item_upholstery_ids:
        await event_bus.dispatch([
            WorkspaceEvent(
                event_name="item:upholstery-requirement-state-changed",
                client_id="",
                workspace_id=ctx.workspace_id,
                extra={
                    "ids": allocated_item_upholstery_ids,
                    "new_state": ItemUpholsteryRequirementStateEnum.ORDERED.value,
                },
            ),
        ])

    return {"client_id": order.client_id}


async def _allocate_requirements(
    session: AsyncSession,
    workspace_id: str,
    inventory_id: str,
    order_amount_meters: Decimal,
    priority_item_upholstery_ids: list[str],
    actor_id: str,
) -> list[str]:
    """
    Load all NEEDS_ORDERING requirements for the given inventory, sort by priority,
    run skip-and-continue allocation, return resolved item_upholstery_ids.
    """
    # Load candidates
    req_result = await session.execute(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.workspace_id == workspace_id,
            ItemUpholsteryRequirement.upholstery_inventory_id == inventory_id,
            ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
    )
    candidates = req_result.scalars().all()
    if not candidates:
        return []

    # Load earliest task.ready_by_at per item_upholstery_id in one query
    # Join path: ItemUpholstery → TaskItem → Task
    item_upholstery_ids = [r.item_upholstery_id for r in candidates]
    ready_result = await session.execute(
        select(
            ItemUpholstery.client_id,
            func.min(Task.ready_by_at).label("earliest_ready_by_at"),
        )
        .join(TaskItem, TaskItem.item_id == ItemUpholstery.item_id)
        .join(Task, Task.client_id == TaskItem.task_id)
        .where(
            ItemUpholstery.client_id.in_(item_upholstery_ids),
            ItemUpholstery.is_deleted.is_(False),
            TaskItem.is_deleted.is_(False),
            Task.is_deleted.is_(False),
            Task.ready_by_at.is_not(None),
        )
        .group_by(ItemUpholstery.client_id)
    )
    ready_by_at_map: dict[str, datetime | None] = {
        row.client_id: row.earliest_ready_by_at for row in ready_result
    }

    # Sort into three tiers:
    # Tier 1 — explicitly listed item_upholstery_ids, in caller-specified order
    # Tier 2 — remaining, by earliest task.ready_by_at ASC (requirements with no deadline last)
    # Tier 3 — within the same ready_by_at bucket (or no deadline), by oldest created_at ASC
    # Tiers 2 and 3 are combined into a single sort key.
    priority_set = set(priority_item_upholstery_ids)
    priority_order = {iid: idx for idx, iid in enumerate(priority_item_upholstery_ids)}

    tier1 = sorted(
        [r for r in candidates if r.item_upholstery_id in priority_set],
        key=lambda r: priority_order.get(r.item_upholstery_id, len(priority_item_upholstery_ids)),
    )
    tier2_and_3 = sorted(
        [r for r in candidates if r.item_upholstery_id not in priority_set],
        key=lambda r: (
            ready_by_at_map.get(r.item_upholstery_id) is None,  # False (has deadline) sorts before True (no deadline)
            ready_by_at_map.get(r.item_upholstery_id),          # earlier deadlines first
            r.created_at,                                        # tiebreaker: oldest first
        ),
    )
    ordered_candidates = tier1 + tier2_and_3

    # Run skip-and-continue allocation
    result = run_skip_and_continue_allocation(
        candidates=ordered_candidates,
        running_pool=order_amount_meters,
        target_state=ItemUpholsteryRequirementStateEnum.ORDERED,
        timestamp_field="ordered_at",
    )

    # Stamp updated_by_id on resolved requirements
    resolved_set = set(result["resolved"])
    for req in ordered_candidates:
        if req.item_upholstery_id in resolved_set:
            req.updated_by_id = actor_id

    return result["resolved"]
```

Key decisions:
- The command owns its own `session.begin()` — it does NOT use `maybe_begin`. `mark_requirements_ordered` is NOT called; its logic is reproduced here with the extended sorting.
- `add_ordered` and `_allocate_requirements` are both gated on `state == ORDERED`. DRAFT/PENDING/APPROVED orders create the row and history record only. Future state-transition commands own the inventory increment and allocation for those paths.
- `flush()` after `ctx.session.add(order)` is required before appending the history record, which FKs to `order.client_id`.
- The allocation sort key `(deadline_is_None, deadline, created_at)` is sortable by Python: the boolean first element prevents Python from ever comparing `None` against a `datetime` in the second position.
- Event dispatch happens after the `session.begin()` block exits (after commit). The order object remains accessible because it was flushed within the transaction.

---

### Step 3 — Router: `upholstery_orders.py`

**File:** `backend/app/beyo_manager/routers/api_v1/upholstery_orders.py` (new file)

```python
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum, UpholsteryOrderStateEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.commands.upholstery.create_upholstery_order import create_upholstery_order
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/upholstery-orders", tags=["upholstery-orders"])


class _CreateBody(BaseModel):
    client_id: str | None = None
    upholstery_id: str
    order_amount_meters: Decimal
    priority_item_upholstery_ids: list[str] = []
    state: UpholsteryOrderStateEnum = UpholsteryOrderStateEnum.ORDERED
    supplier_id: str | None = None
    upholstery_supplier_link_id: str | None = None
    price_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    order_at: datetime | None = None
    expected_receive_at: datetime | None = None


@router.put("")
async def route_create_upholstery_order(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_upholstery_order, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

Note: The `state` field on `_CreateBody` accepts the full `UpholsteryOrderStateEnum` at the FastAPI layer. The creation-state restriction (only DRAFT/PENDING/APPROVED/ORDERED) is enforced in the command's request parser, keeping the domain guard out of the router.

---

### Step 4 — Register router in `routers/api_v1/__init__.py`

**File:** `backend/app/beyo_manager/routers/api_v1/__init__.py`

**Change A — import block:** add `upholstery_orders` to the existing import tuple.

Replace:
```python
from beyo_manager.routers.api_v1 import (
    audit,
    auth,
    bootstrap,
    case_types,
    cases,
    customers,
    files,
    health,
    history,
    images,
    issue_types,
    items,
    item_categories,
    item_upholsteries,
    notifications,
    reset,
    tasks,
    upholsteries,
    upholstery_inventories,
    users,
    user_working_sections,
    working_section_memberships,
    working_sections,
)
```

With:
```python
from beyo_manager.routers.api_v1 import (
    audit,
    auth,
    bootstrap,
    case_types,
    cases,
    customers,
    files,
    health,
    history,
    images,
    issue_types,
    items,
    item_categories,
    item_upholsteries,
    notifications,
    reset,
    tasks,
    upholsteries,
    upholstery_inventories,
    upholstery_orders,
    users,
    user_working_sections,
    working_section_memberships,
    working_sections,
)
```

**Change B — registration block:** add the new router after `upholsteries.router`.

Replace:
```python
    app.include_router(upholstery_inventories.router)
    app.include_router(upholsteries.router)
```

With:
```python
    app.include_router(upholstery_inventories.router)
    app.include_router(upholsteries.router)
    app.include_router(upholstery_orders.router)
```

## Risks and mitigations

- Risk: `_allocate_requirements` sort key `(deadline_is_None, deadline, created_at)` — comparing `None` with a `datetime` in the second tuple position would raise a `TypeError`.
  Mitigation: The boolean first element (`deadline_is_None`) short-circuits tuple comparison before reaching the second element. All no-deadline items carry `True` as their first key and sort after all deadline-bearing items (`False`). Python never compares `None` against a `datetime`.

- Risk: `task_items.is_deleted` — if `TaskItem` does not have an `is_deleted` column, the filter `TaskItem.is_deleted.is_(False)` raises an `AttributeError`.
  Mitigation: Codex must verify `is_deleted` exists on `TaskItem` (via permitted relational read) before adding that filter. If absent, omit it.

- Risk: `ItemUpholsteryRequirement.upholstery_inventory_id` may be `None` for requirements not yet linked to inventory; such rows are excluded by the `== inventory_id` filter.
  Mitigation: Correct behavior — unlinked requirements are not eligible for allocation.

- Risk: Future state-transition commands (DRAFT/PENDING/APPROVED → ORDERED) must call `add_ordered` and run the allocation at transition time, since this command skips both for non-ORDERED states.
  Mitigation: Document this coupling in the state-transition command plan. The transition command is responsible for the inventory and allocation side effects.

- Risk: `model_dump()` on `_CreateBody` serializes `state` as a `UpholsteryOrderStateEnum` object. The request parser's `model_validate` handles enum instances without coercion issues.
  Mitigation: Verify via smoke test. If the parser rejects enum instances, use `body.model_dump(mode="json")` in the router instead.

- Risk: A `flush()` failure (e.g. constraint violation on `UpholsteryOrder`) rolls back the entire `session.begin()` block, leaving inventory and requirements unchanged.
  Mitigation: Intended behavior — atomicity is the goal.

## Validation plan

- `PYTHONPATH=backend/app python3 -c "from beyo_manager.routers.api_v1 import upholstery_orders"` → no import error
- `PYTHONPATH=backend/app python3 -c "from beyo_manager.services.commands.upholstery.create_upholstery_order import create_upholstery_order"` → no import error
- `PUT /api/v1/upholstery-orders` with `{"upholstery_id": "<valid_uph_id>", "order_amount_meters": "10.000"}`:
  - Response: `{"client_id": "uor_..."}` (200)
  - DB: `upholstery_orders` row with `state = ordered`, `upholstery_inventory_id` set
  - DB: `upholstery_order_history_records` row with matching `upholstery_order_id`
  - DB: `upholstery_inventory.current_amount_ordered_meters` increased by 10.000
- `PUT /api/v1/upholstery-orders` with `{"upholstery_id": "<valid_uph_id>", "order_amount_meters": "10.000", "client_id": "uor_CUSTOM"}`:
  - Response: `{"client_id": "uor_CUSTOM"}` (200); second identical call → 409
- `PUT /api/v1/upholstery-orders` with `{"upholstery_id": "<valid_uph_id>", "order_amount_meters": "10.000", "state": "draft"}`:
  - Response: 200; `state = draft` in DB; `current_amount_ordered_meters` unchanged; NEEDS_ORDERING requirements unchanged
- `PUT /api/v1/upholstery-orders` with `state = "cancelled"` → 422
- `PUT /api/v1/upholstery-orders` with unknown `upholstery_id` → 404
- `PUT /api/v1/upholstery-orders` with `order_amount_meters = 0` → 422
- With NEEDS_ORDERING requirements present: `priority_item_upholstery_ids` are resolved first regardless of `created_at`; remaining sort by `task.ready_by_at` ASC before falling back to `created_at` ASC

## Review log

- `2026-06-16` owner: resolved all three clarifications — field renamed to `priority_item_upholstery_ids`, tier1 key uses `r.item_upholstery_id`; inventory increment and allocation both gated on `state == ORDERED`
- `2026-06-16` owner: implemented `create_upholstery_order`, added the `PUT /api/v1/upholstery-orders` router, wrote `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_create_upholstery_order_20260616.md`, and created `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_create_upholstery_order_20260616.md`.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `claude-sonnet-4-6`
