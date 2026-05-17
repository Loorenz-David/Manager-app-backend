# PLAN_item_upholstery_requirement_lifecycle_20260516

## Metadata

- Plan ID: `PLAN_item_upholstery_requirement_lifecycle_20260516`
- Status: `under_construction`
- Owner agent: `GitHub Copilot`
- Created at (UTC): `2026-05-16T14:00:00Z`
- Last updated at (UTC): `2026-05-16T14:00:00Z`
- Related issue/ticket: `—`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_item_upholstery_requirement_lifecycle_20260516.md`

## Goal and intent

- **Goal:** Implement all 9 leaf commands that manage the full lifecycle of `ItemUpholstery` and `ItemUpholsteryRequirement` — from creation with inventory need injection, through priority-based stock allocation, surplus application, and completion — plus read queries and a router. These commands call Intention 2 mutation helpers for all inventory changes.
- **Business/user intent:** Production managers need accurate per-item upholstery tracking. Each item knows its material state (available, needs ordering, in use, completed) and the system automatically reflects that in inventory projections via a deterministic, non-duplicated command set.
- **Non-goals:** Item state transitions (`ItemStateEnum`), external procurement/order placement, multi-upholstery batch creation, notification emission, customer-source expansion.

## Scope

- **In scope:**
  - Domain serializers: `domain/items/serializers.py`
  - 1 private helper: `services/commands/items/_allocation_algorithm.py` (skip-and-continue pool logic shared by CMD-4, CMD-5, CMD-9)
  - 9 lifecycle commands (CMD-1 through CMD-9)
  - 2 additional CRUD commands: `update_item_upholstery.py`, `delete_item_upholstery.py`
  - 4 queries: `list_item_upholsteries.py`, `get_item_upholstery.py`, `list_upholstery_requirements.py`, `get_upholstery_requirement.py`
  - 1 new router file: `routers/api_v1/item_upholsteries.py`
  - Registration in `routers/api_v1/__init__.py`

- **Out of scope:** All migrations (done in `PLAN_upholstery_inventory_projection_20260516`). Direct writes to `upholstery_inventory` fields — all delegated to `_inventory_mutations.py`.

- **Assumptions:**
  - `PLAN_upholstery_inventory_projection_20260516` is fully applied — all migrations run, `_inventory_mutations.py` exists and is importable.
  - `ItemUpholstery.active_requirement_id` is nullable (confirmed in model — `nullable=True`).
  - `ItemUpholsteryRequirement.amount_meters` is nullable (applied by Plan 1 Migration 4).
  - `ItemUpholsteryRequirement.upholstery_inventory_id` is a plain `String(64)` with no FK constraint (confirmed — `nullable=True`, no FK).
  - `ADMIN`, `MANAGER` role constants exist in `routers/utils/roles.py` (read existing file to confirm actual constants).

## Clarifications required

*(none — all design decisions resolved in the intention plan)*

## Acceptance criteria

1. `PUT /api/v1/item-upholsteries` with a valid quantity creates `ItemUpholstery` + `ItemUpholsteryRequirement` atomically; requirement state is `AVAILABLE` or `NEEDS_ORDERING`; `active_requirement_id` is set.
2. `PUT /api/v1/item-upholsteries` with null/0 quantity creates requirement with state `MISSING_QUANTITY` and `amount_meters = null`; no inventory command is called.
3. `POST /api/v1/item-upholsteries/{id}/mark-in-use` transitions all `AVAILABLE` requirements to `IN_USE` and calls `consume_to_in_use` for each non-customer requirement.
4. `POST /api/v1/item-upholsteries/{id}/complete` closes all `IN_USE` (via `finish_in_use`) and `AVAILABLE` (via `complete_available_direct`) requirements.
5. `POST /api/v1/item-upholsteries/mark-ordered` allocates an `ordered_quantity` across `NEEDS_ORDERING` requirements using skip-and-continue (priority list → oldest first); returns `{ordered: [...], unordered: [...]}`.
6. `POST /api/v1/item-upholsteries/resolve-after-stock` recalculates ORDERED/NEEDS_ORDERING requirements for a given upholstery using three-tier priority; returns `{resolved: [...], unresolved: [...]}`.
7. `POST /api/v1/item-upholsteries/{id}/apply-surplus` applies workspace offcut material; Case A converts to SURPLUS AVAILABLE, Case B splits into a new SURPLUS requirement. Both call `add_stored_surplus`.
8. `POST /api/v1/item-upholsteries/{id}/set-quantity` transitions a `MISSING_QUANTITY` requirement to `AVAILABLE` or `NEEDS_ORDERING`.
9. `POST /api/v1/upholstery-requirements/{id}/complete` completes a single `IN_USE` requirement independently.
10. `POST /api/v1/item-upholsteries/reallocate-stock` moves donors from `AVAILABLE` to `NEEDS_ORDERING` and runs skip-and-continue allocation. No inventory field changes.
11. `GET /api/v1/item-upholsteries` returns paginated list with `item_upholsteries_pagination`.
12. `GET /api/v1/item-upholsteries/{id}` returns full `ItemUpholstery` with its requirements.
13. `GET /api/v1/item-upholsteries/{id}/requirements` returns paginated list of all requirements for the item upholstery.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: layer separation
- `backend/architecture/05_errors.md`: `ValidationError`, `ConflictError`, `NotFound`
- `backend/architecture/06_commands.md`: command skeleton, `async with ctx.session.begin()`, batch iteration, private helpers, flush pattern, returning `dict`
- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: offset pagination, `_MAX_LIMIT`, `_DEFAULT_LIMIT`, required `<entity>_pagination` key
- `backend/architecture/09_routers.md`: handler wiring, static routes before wildcards, `build_ok`/`build_err`
- `backend/architecture/21_naming_conventions.md`: file and function naming, private prefix `_`
- `backend/architecture/30_migrations.md`: no new migrations in this plan (all done in Plan 1)

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination overrides cursor pagination

### File read intent — pattern vs. relational

Prohibited (contract already covers these):
- Reading another command for session/flush shape → `06_commands.md`
- Reading another query for pagination → `07_queries_local.md`

Permitted relational reads for this plan:
- `models/tables/items/item_upholstery.py` — exact field names and types
- `models/tables/items/item_upholstery_requirement.py` — confirm post-migration nullable `amount_meters`, timestamp fields (`ordered_at`, `in_use_at`, `completed_at`)
- `models/tables/items/item.py` — confirm `workspace_id` FK exists for guard in CMD-1
- `services/commands/upholstery/_inventory_mutations.py` — confirm function signatures (what each helper accepts)
- `routers/api_v1/__init__.py` — confirm registration pattern
- `routers/utils/roles.py` — confirm role constants (ADMIN, MANAGER, WORKER, etc.)

### Skill selection

- Primary skill: `—` *(direct implementation)*

---

## Implementation plan

### PHASE 1 — Domain serializers

---

#### Step 1.1 — CREATE domain/items/serializers.py

**File:** `backend/app/beyo_manager/domain/items/serializers.py`

```python
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement


def serialize_item_upholstery(iup: ItemUpholstery) -> dict:
    return {
        "client_id": iup.client_id,
        "workspace_id": iup.workspace_id,
        "item_id": iup.item_id,
        "upholstery_id": iup.upholstery_id,
        "name": iup.name,
        "code": iup.code,
        "amount_meters": str(iup.amount_meters) if iup.amount_meters is not None else None,
        "source": iup.source.value,
        "time_to_fix_in_seconds": iup.time_to_fix_in_seconds,
        "active_requirement_id": iup.active_requirement_id,
        "created_at": iup.created_at.isoformat(),
        "created_by_id": iup.created_by_id,
        "updated_at": iup.updated_at.isoformat() if iup.updated_at else None,
        "updated_by_id": iup.updated_by_id,
        "is_deleted": iup.is_deleted,
    }


def serialize_upholstery_requirement(req: ItemUpholsteryRequirement) -> dict:
    return {
        "client_id": req.client_id,
        "workspace_id": req.workspace_id,
        "item_upholstery_id": req.item_upholstery_id,
        "upholstery_inventory_id": req.upholstery_inventory_id,
        "amount_meters": str(req.amount_meters) if req.amount_meters is not None else None,
        "source": req.source.value,
        "state": req.state.value,
        "value_minor": req.value_minor,
        "currency": req.currency.value if req.currency else None,
        "created_at": req.created_at.isoformat(),
        "created_by_id": req.created_by_id,
        "ordered_at": req.ordered_at.isoformat() if req.ordered_at else None,
        "in_use_at": req.in_use_at.isoformat() if req.in_use_at else None,
        "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        "failed_at": req.failed_at.isoformat() if req.failed_at else None,
        "updated_at": req.updated_at.isoformat() if req.updated_at else None,
        "updated_by_id": req.updated_by_id,
        "is_deleted": req.is_deleted,
    }
```

---

### PHASE 2 — Private allocation helper

The skip-and-continue pool algorithm is shared by CMD-4, CMD-5, and CMD-9. Extract it into one private helper so the logic is never duplicated.

---

#### Step 2.1 — CREATE services/commands/items/_allocation_algorithm.py

**File:** `backend/app/beyo_manager/services/commands/items/_allocation_algorithm.py`

```python
from decimal import Decimal
from datetime import datetime, timezone
from typing import TypedDict

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement


class AllocationResult(TypedDict):
    resolved: list[str]      # item_upholstery_ids marked AVAILABLE (or ORDERED)
    unresolved: list[str]    # item_upholstery_ids left unchanged


def run_skip_and_continue_allocation(
    candidates: list[ItemUpholsteryRequirement],
    running_pool: Decimal,
    target_state: ItemUpholsteryRequirementStateEnum,
    timestamp_field: str,
) -> AllocationResult:
    """
    Iterate candidates in priority order (already sorted by caller).
    For each candidate: if pool >= candidate.amount_meters → assign target_state.
    Skip candidates that don't fit — do NOT stop early.
    Returns resolved and unresolved item_upholstery_ids.

    target_state: the state to assign when a candidate fits (AVAILABLE or ORDERED).
    timestamp_field: the attribute to stamp on the model ('ordered_at', etc.). Pass None to skip.
    """
    resolved: list[str] = []
    unresolved: list[str] = []
    now = datetime.now(timezone.utc)

    for req in candidates:
        amount = req.amount_meters or Decimal("0")
        if running_pool - amount >= Decimal("0"):
            req.state = target_state
            if timestamp_field:
                setattr(req, timestamp_field, now)
            running_pool -= amount
            resolved.append(req.item_upholstery_id)
        else:
            unresolved.append(req.item_upholstery_id)

    return AllocationResult(resolved=resolved, unresolved=unresolved)
```

---

### PHASE 3 — Create commands package

Create `backend/app/beyo_manager/services/commands/items/__init__.py` (empty) and `backend/app/beyo_manager/services/commands/items/requests/__init__.py` (empty).

---

### PHASE 4 — CMD-1: Create ItemUpholstery

---

#### Step 4.1 — CREATE requests/create_item_upholstery_request.py

**File:** `backend/app/beyo_manager/services/commands/items/requests/create_item_upholstery_request.py`

```python
from decimal import Decimal
from pydantic import BaseModel, field_validator
from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.errors.validation import ValidationError


class CreateItemUpholsteryRequest(BaseModel):
    item_id: str
    upholstery_id: str | None = None
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    source: ItemUpholsterySourceEnum
    time_to_fix_in_seconds: int | None = None

    @field_validator("amount_meters", mode="before")
    @classmethod
    def coerce_zero_to_null(cls, v) -> Decimal | None:
        if v is None:
            return None
        v = Decimal(str(v))
        return None if v <= Decimal("0") else v

    @field_validator("time_to_fix_in_seconds")
    @classmethod
    def time_must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("time_to_fix_in_seconds must be >= 0.")
        return v


def parse_create_item_upholstery_request(data: dict) -> CreateItemUpholsteryRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return CreateItemUpholsteryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

#### Step 4.2 — CREATE services/commands/items/create_item_upholstery.py

**File:** `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py`

```python
from sqlalchemy import select

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests.create_item_upholstery_request import (
    parse_create_item_upholstery_request,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import check_and_inject_need
from beyo_manager.services.context import ServiceContext


async def create_item_upholstery(ctx: ServiceContext) -> dict:
    request = parse_create_item_upholstery_request(ctx.incoming_data)

    # Guard: non-CUSTOMER source must provide upholstery_id
    if request.upholstery_id is None and request.source != ItemUpholsterySourceEnum.CUSTOMER:
        raise ValidationError(
            "upholstery_id is required when source is not CUSTOMER."
        )

    async with ctx.session.begin():
        # Guard: item must belong to this workspace
        item_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.item_id,
                Item.is_deleted.is_(False),
            )
        )
        if item_result.scalar_one_or_none() is None:
            raise NotFound("Item not found.")

        iup = ItemUpholstery(
            workspace_id=ctx.workspace_id,
            item_id=request.item_id,
            upholstery_id=request.upholstery_id,
            name=request.name,
            code=request.code,
            amount_meters=request.amount_meters,
            source=request.source,
            time_to_fix_in_seconds=request.time_to_fix_in_seconds,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(iup)
        await ctx.session.flush()  # get iup.client_id

        if request.amount_meters is not None and request.source != ItemUpholsterySourceEnum.CUSTOMER:
            # Branch A: quantity provided, non-customer — check inventory and inject need
            inv_result = await check_and_inject_need(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_id=request.upholstery_id,
                quantity=request.amount_meters,
                inject=True,
            )
            state = (
                ItemUpholsteryRequirementStateEnum.AVAILABLE
                if inv_result["sufficient"]
                else ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
            )
            req = ItemUpholsteryRequirement(
                workspace_id=ctx.workspace_id,
                item_upholstery_id=iup.client_id,
                upholstery_inventory_id=inv_result["inventory_id"],
                amount_meters=request.amount_meters,
                source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
                state=state,
                created_by_id=ctx.user_id,
            )
        elif request.amount_meters is None:
            # Branch B: no quantity — MISSING_QUANTITY state, no inventory touch
            req = ItemUpholsteryRequirement(
                workspace_id=ctx.workspace_id,
                item_upholstery_id=iup.client_id,
                upholstery_inventory_id=None,
                amount_meters=None,
                source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
                state=ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
                created_by_id=ctx.user_id,
            )
        else:
            # Branch A for CUSTOMER source: create requirement but no inventory touch
            req = ItemUpholsteryRequirement(
                workspace_id=ctx.workspace_id,
                item_upholstery_id=iup.client_id,
                upholstery_inventory_id=None,
                amount_meters=request.amount_meters,
                source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
                state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
                created_by_id=ctx.user_id,
            )

        ctx.session.add(req)
        await ctx.session.flush()  # get req.client_id

        iup.active_requirement_id = req.client_id

    return {"client_id": iup.client_id}
```

---

### PHASE 5 — CMD-2: Mark Requirements In-Use

---

#### Step 5.1 — CREATE services/commands/items/mark_requirements_in_use.py

**File:** `backend/app/beyo_manager/services/commands/items/mark_requirements_in_use.py`

```python
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.upholstery._inventory_mutations import consume_to_in_use
from beyo_manager.services.context import ServiceContext


async def mark_requirements_in_use(ctx: ServiceContext) -> dict:
    item_upholstery_id = ctx.incoming_data.get("item_upholstery_id")

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id == item_upholstery_id,
                ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum.AVAILABLE,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        requirements = result.scalars().all()

        if not requirements:
            raise ValidationError(
                "No AVAILABLE requirements found for this item upholstery."
            )

        now = datetime.now(timezone.utc)
        for req in requirements:
            if req.upholstery_inventory_id is not None:
                await consume_to_in_use(
                    session=ctx.session,
                    workspace_id=ctx.workspace_id,
                    upholstery_inventory_id=req.upholstery_inventory_id,
                    quantity=req.amount_meters,
                )
            req.state = ItemUpholsteryRequirementStateEnum.IN_USE
            req.in_use_at = now
            req.updated_by_id = ctx.user_id

    return {}
```

---

### PHASE 6 — CMD-3: Mark Requirements Completed (natural complete-all)

---

#### Step 6.1 — CREATE services/commands/items/mark_requirements_completed.py

**File:** `backend/app/beyo_manager/services/commands/items/mark_requirements_completed.py`

```python
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.upholstery._inventory_mutations import (
    complete_available_direct,
    finish_in_use,
)
from beyo_manager.services.context import ServiceContext


async def mark_requirements_completed(ctx: ServiceContext) -> dict:
    item_upholstery_id = ctx.incoming_data.get("item_upholstery_id")

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id == item_upholstery_id,
                ItemUpholsteryRequirement.state.in_([
                    ItemUpholsteryRequirementStateEnum.IN_USE,
                    ItemUpholsteryRequirementStateEnum.AVAILABLE,
                ]),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        requirements = result.scalars().all()

        if not requirements:
            raise ValidationError(
                "No IN_USE or AVAILABLE requirements found for this item upholstery."
            )

        now = datetime.now(timezone.utc)
        for req in requirements:
            if req.state == ItemUpholsteryRequirementStateEnum.IN_USE:
                if req.upholstery_inventory_id is not None:
                    await finish_in_use(
                        session=ctx.session,
                        workspace_id=ctx.workspace_id,
                        upholstery_inventory_id=req.upholstery_inventory_id,
                        quantity=req.amount_meters,
                        source=req.source,
                    )
            elif req.state == ItemUpholsteryRequirementStateEnum.AVAILABLE:
                if req.upholstery_inventory_id is not None:
                    await complete_available_direct(
                        session=ctx.session,
                        workspace_id=ctx.workspace_id,
                        upholstery_inventory_id=req.upholstery_inventory_id,
                        quantity=req.amount_meters,
                        source=req.source,
                    )
            req.state = ItemUpholsteryRequirementStateEnum.COMPLETED
            req.completed_at = now
            req.updated_by_id = ctx.user_id

    return {}
```

---

### PHASE 7 — CMD-4: Mark Requirements Ordered (pool-based)

---

#### Step 7.1 — CREATE requests/mark_requirements_ordered_request.py

**File:** `backend/app/beyo_manager/services/commands/items/requests/mark_requirements_ordered_request.py`

```python
from decimal import Decimal
from pydantic import BaseModel, field_validator
from beyo_manager.errors.validation import ValidationError


class MarkRequirementsOrderedRequest(BaseModel):
    upholstery_id: str
    ordered_quantity: Decimal
    priority_item_upholstery_ids: list[str] = []

    @field_validator("ordered_quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("ordered_quantity must be > 0.")
        return v


def parse_mark_requirements_ordered_request(data: dict) -> MarkRequirementsOrderedRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return MarkRequirementsOrderedRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

#### Step 7.2 — CREATE services/commands/items/mark_requirements_ordered.py

**File:** `backend/app/beyo_manager/services/commands/items/mark_requirements_ordered.py`

```python
from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation
from beyo_manager.services.commands.items.requests.mark_requirements_ordered_request import (
    parse_mark_requirements_ordered_request,
)
from beyo_manager.services.context import ServiceContext


async def mark_requirements_ordered(ctx: ServiceContext) -> dict:
    """
    CMD-4: Pool-based, priority-aware allocation of ordered_quantity to NEEDS_ORDERING requirements.
    Does NOT modify any upholstery_inventory fields — purely updates requirement states.
    Called AFTER the external order system has called add_ordered on the inventory.
    """
    request = parse_mark_requirements_ordered_request(ctx.incoming_data)

    async with ctx.session.begin():
        # Load all NEEDS_ORDERING requirements for this upholstery
        result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.upholstery_inventory_id.isnot(None),
                ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        all_needs_ordering = result.scalars().all()

        # Filter to upholstery_id by checking via the inventory — join approach:
        # Since upholstery_inventory_id is stored on the requirement but not upholstery_id,
        # we need to filter by the upholstery through the inventory. Two options:
        # (A) load inventory ids for the upholstery first; (B) add upholstery_id column to requirement.
        # The model has upholstery_inventory_id (not upholstery_id). Load inventory row to get the match.
        # Load all upholstery_inventory rows for this upholstery_id in the workspace:
        from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory.client_id).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == request.upholstery_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        valid_inventory_ids = set(inv_result.scalars().all())

        candidates = [r for r in all_needs_ordering if r.upholstery_inventory_id in valid_inventory_ids]

        # Build priority-ordered candidate list
        priority_set = set(request.priority_item_upholstery_ids)
        priority_order = {iid: idx for idx, iid in enumerate(request.priority_item_upholstery_ids)}

        tier1 = sorted(
            [r for r in candidates if r.item_upholstery_id in priority_set],
            key=lambda r: priority_order.get(r.item_upholstery_id, 9999),
        )
        tier2 = sorted(
            [r for r in candidates if r.item_upholstery_id not in priority_set],
            key=lambda r: r.created_at,
        )
        ordered_candidates = tier1 + tier2

        result_dict = run_skip_and_continue_allocation(
            candidates=ordered_candidates,
            running_pool=request.ordered_quantity,
            target_state=ItemUpholsteryRequirementStateEnum.ORDERED,
            timestamp_field="ordered_at",
        )

        # Set updated_by_id on modified requirements
        modified_ids = set(result_dict["resolved"])
        for req in ordered_candidates:
            if req.item_upholstery_id in modified_ids:
                req.updated_by_id = ctx.user_id

    return {
        "ordered": result_dict["resolved"],
        "unordered": result_dict["unresolved"],
    }
```

---

### PHASE 8 — CMD-5: Resolve Requirements After Stock Arrival

---

#### Step 8.1 — CREATE requests/resolve_requirements_after_stock_request.py

**File:** `backend/app/beyo_manager/services/commands/items/requests/resolve_requirements_after_stock_request.py`

```python
from pydantic import BaseModel
from beyo_manager.errors.validation import ValidationError


class ResolveRequirementsAfterStockRequest(BaseModel):
    upholstery_id: str
    priority_item_upholstery_ids: list[str] = []


def parse_resolve_requirements_after_stock_request(data: dict) -> ResolveRequirementsAfterStockRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return ResolveRequirementsAfterStockRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

#### Step 8.2 — CREATE services/commands/items/resolve_requirements_after_stock.py

**File:** `backend/app/beyo_manager/services/commands/items/resolve_requirements_after_stock.py`

```python
from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation
from beyo_manager.services.commands.items.requests.resolve_requirements_after_stock_request import (
    parse_resolve_requirements_after_stock_request,
)
from beyo_manager.services.context import ServiceContext


async def resolve_requirements_after_stock(ctx: ServiceContext) -> dict:
    """
    CMD-5: Recalculate which ORDERED/NEEDS_ORDERING requirements can now be AVAILABLE
    after new stock arrives. Assumes confirm_ordered_to_stock (Intention 2 CMD-5) was
    already called by the task command before this runs.
    No inventory field mutations — only requirement state changes.
    """
    request = parse_resolve_requirements_after_stock_request(ctx.incoming_data)

    async with ctx.session.begin():
        # Load inventory row for pool calculation
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == request.upholstery_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inv = inv_result.scalar_one_or_none()
        if inv is None:
            raise NotFound("UpholsteryInventory not found for this upholstery.")

        # Load all ORDERED and NEEDS_ORDERING candidates
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.upholstery_inventory_id == inv.client_id,
                ItemUpholsteryRequirement.state.in_([
                    ItemUpholsteryRequirementStateEnum.ORDERED,
                    ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
                ]),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        candidates = req_result.scalars().all()

        if not candidates:
            return {"resolved": [], "unresolved": []}

        # Calculate running pool:
        # total_need_of_all_candidates = SUM(candidate.amount_meters)
        # running_pool = stored - (in_need - total_candidate_need)
        # This removes candidates' in_need contribution so we can re-allocate cleanly.
        total_candidate_need = sum(
            (r.amount_meters or Decimal("0")) for r in candidates
        )
        stored = inv.current_stored_amount_meters or Decimal("0")
        in_need = inv.current_amount_in_need_meters or Decimal("0")
        running_pool = stored - (in_need - total_candidate_need)

        # Sort into three tiers
        priority_set = set(request.priority_item_upholstery_ids)
        priority_order = {iid: idx for idx, iid in enumerate(request.priority_item_upholstery_ids)}

        tier1 = sorted(
            [r for r in candidates if r.item_upholstery_id in priority_set],
            key=lambda r: priority_order.get(r.item_upholstery_id, 9999),
        )
        tier2 = sorted(
            [r for r in candidates if r.item_upholstery_id not in priority_set
             and r.state == ItemUpholsteryRequirementStateEnum.ORDERED],
            key=lambda r: r.ordered_at or r.created_at,
        )
        tier3 = sorted(
            [r for r in candidates if r.item_upholstery_id not in priority_set
             and r.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING],
            key=lambda r: r.created_at,
        )
        ordered_candidates = tier1 + tier2 + tier3

        result_dict = run_skip_and_continue_allocation(
            candidates=ordered_candidates,
            running_pool=running_pool,
            target_state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
            timestamp_field=None,
        )

        modified_ids = set(result_dict["resolved"])
        for req in ordered_candidates:
            if req.item_upholstery_id in modified_ids:
                req.updated_by_id = ctx.user_id

    return {
        "resolved": result_dict["resolved"],
        "unresolved": result_dict["unresolved"],
    }
```

---

### PHASE 9 — CMD-6: Apply Surplus to Requirement

---

#### Step 9.1 — CREATE requests/apply_surplus_request.py

**File:** `backend/app/beyo_manager/services/commands/items/requests/apply_surplus_request.py`

```python
from decimal import Decimal
from pydantic import BaseModel, field_validator
from beyo_manager.errors.validation import ValidationError


class ApplySurplusRequest(BaseModel):
    item_upholstery_id: str
    surplus_amount_meters: Decimal

    @field_validator("surplus_amount_meters")
    @classmethod
    def surplus_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("surplus_amount_meters must be > 0.")
        return v


def parse_apply_surplus_request(data: dict) -> ApplySurplusRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return ApplySurplusRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

#### Step 9.2 — CREATE services/commands/items/apply_surplus_to_requirement.py

**File:** `backend/app/beyo_manager/services/commands/items/apply_surplus_to_requirement.py`

```python
from sqlalchemy import select

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests.apply_surplus_request import (
    parse_apply_surplus_request,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import add_stored_surplus
from beyo_manager.services.context import ServiceContext

_ALLOWED_STATES = {
    ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
    ItemUpholsteryRequirementStateEnum.ORDERED,
}


async def apply_surplus_to_requirement(ctx: ServiceContext) -> dict:
    """
    CMD-6: Apply workspace offcut material to a NEEDS_ORDERING or ORDERED requirement.
    Case A (full cover): convert existing requirement to SURPLUS AVAILABLE.
    Case B (partial): create new SURPLUS requirement + reduce INVENTORY requirement amount.
    Both cases call add_stored_surplus to track the offcut in inventory.
    """
    request = parse_apply_surplus_request(ctx.incoming_data)

    async with ctx.session.begin():
        iup_result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.client_id == request.item_upholstery_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        iup = iup_result.scalar_one_or_none()
        if iup is None:
            raise NotFound("ItemUpholstery not found.")

        # Load the active requirement
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.client_id == iup.active_requirement_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        active_req = req_result.scalar_one_or_none()
        if active_req is None:
            raise NotFound("Active requirement not found.")

        if active_req.state not in _ALLOWED_STATES:
            raise ValidationError(
                "Surplus can only be applied to requirements in NEEDS_ORDERING or ORDERED state."
            )

        if request.surplus_amount_meters > (active_req.amount_meters or 0):
            raise ValidationError(
                "surplus_amount_meters cannot exceed the requirement's amount_meters."
            )

        # Call add_stored_surplus (same inventory row for both cases)
        await add_stored_surplus(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=active_req.upholstery_inventory_id,
            quantity=request.surplus_amount_meters,
        )

        if request.surplus_amount_meters == active_req.amount_meters:
            # Case A: full cover — convert existing to SURPLUS AVAILABLE
            active_req.source = ItemUpholsteryRequirementSourceEnum.SURPLUS
            active_req.state = ItemUpholsteryRequirementStateEnum.AVAILABLE
            active_req.updated_by_id = ctx.user_id
        else:
            # Case B: partial cover — create SURPLUS requirement + reduce INVENTORY requirement
            surplus_req = ItemUpholsteryRequirement(
                workspace_id=ctx.workspace_id,
                item_upholstery_id=iup.client_id,
                upholstery_inventory_id=active_req.upholstery_inventory_id,
                amount_meters=request.surplus_amount_meters,
                source=ItemUpholsteryRequirementSourceEnum.SURPLUS,
                state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(surplus_req)

            from decimal import Decimal
            active_req.amount_meters = (active_req.amount_meters or Decimal("0")) - request.surplus_amount_meters
            active_req.updated_by_id = ctx.user_id
            # active_requirement_id stays on the INVENTORY requirement

    return {}
```

---

### PHASE 10 — CMD-7: Set Quantity on Missing-Quantity Requirement

---

#### Step 10.1 — CREATE requests/set_quantity_request.py

**File:** `backend/app/beyo_manager/services/commands/items/requests/set_quantity_request.py`

```python
from decimal import Decimal
from pydantic import BaseModel, field_validator
from beyo_manager.errors.validation import ValidationError


class SetQuantityRequest(BaseModel):
    item_upholstery_id: str
    amount_meters: Decimal

    @field_validator("amount_meters")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("amount_meters must be > 0.")
        return v


def parse_set_quantity_request(data: dict) -> SetQuantityRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return SetQuantityRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

#### Step 10.2 — CREATE services/commands/items/set_requirement_quantity.py

**File:** `backend/app/beyo_manager/services/commands/items/set_requirement_quantity.py`

```python
from sqlalchemy import select

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementStateEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests.set_quantity_request import (
    parse_set_quantity_request,
)
from beyo_manager.services.commands.upholstery._inventory_mutations import check_and_inject_need
from beyo_manager.services.context import ServiceContext


async def set_requirement_quantity(ctx: ServiceContext) -> dict:
    """
    CMD-7: Resolve a MISSING_QUANTITY requirement by providing a quantity.
    Calls check_and_inject_need to add to in_need and determine state.
    The only valid transition out of MISSING_QUANTITY.
    """
    request = parse_set_quantity_request(ctx.incoming_data)

    async with ctx.session.begin():
        iup_result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.client_id == request.item_upholstery_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        iup = iup_result.scalar_one_or_none()
        if iup is None:
            raise NotFound("ItemUpholstery not found.")

        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.client_id == iup.active_requirement_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        req = req_result.scalar_one_or_none()
        if req is None:
            raise NotFound("Active requirement not found.")

        if req.state != ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY:
            raise ValidationError(
                "set_quantity can only be called on requirements in MISSING_QUANTITY state."
            )

        inv_result = await check_and_inject_need(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_id=iup.upholstery_id,
            quantity=request.amount_meters,
            inject=True,
        )

        req.amount_meters = request.amount_meters
        req.upholstery_inventory_id = inv_result["inventory_id"]
        req.state = (
            ItemUpholsteryRequirementStateEnum.AVAILABLE
            if inv_result["sufficient"]
            else ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
        )
        req.updated_by_id = ctx.user_id

        iup.amount_meters = request.amount_meters
        iup.updated_by_id = ctx.user_id

    return {}
```

---

### PHASE 11 — CMD-8: Complete a Specific Requirement Instance

---

#### Step 11.1 — CREATE services/commands/items/complete_requirement_instance.py

**File:** `backend/app/beyo_manager/services/commands/items/complete_requirement_instance.py`

```python
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.upholstery._inventory_mutations import finish_in_use
from beyo_manager.services.context import ServiceContext


async def complete_requirement_instance(ctx: ServiceContext) -> dict:
    """
    CMD-8: Complete a single identified IN_USE requirement by its own client_id.
    Does not affect other requirements on the same ItemUpholstery.
    """
    requirement_id = ctx.incoming_data.get("requirement_id")

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.client_id == requirement_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        req = result.scalar_one_or_none()
        if req is None:
            raise NotFound("ItemUpholsteryRequirement not found.")

        if req.state != ItemUpholsteryRequirementStateEnum.IN_USE:
            raise ValidationError(
                "Only IN_USE requirements can be completed via this command."
            )

        if req.upholstery_inventory_id is not None:
            await finish_in_use(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_inventory_id=req.upholstery_inventory_id,
                quantity=req.amount_meters,
                source=req.source,
            )

        req.state = ItemUpholsteryRequirementStateEnum.COMPLETED
        req.completed_at = datetime.now(timezone.utc)
        req.updated_by_id = ctx.user_id

    return {}
```

---

### PHASE 12 — CMD-9: Reallocate Available Stock

---

#### Step 12.1 — CREATE requests/reallocate_stock_request.py

**File:** `backend/app/beyo_manager/services/commands/items/requests/reallocate_stock_request.py`

```python
from pydantic import BaseModel, model_validator
from beyo_manager.errors.validation import ValidationError


class ReallocateStockRequest(BaseModel):
    upholstery_id: str
    priority_item_upholstery_ids: list[str]
    donor_item_upholstery_ids: list[str]

    @model_validator(mode="after")
    def no_overlap(self) -> "ReallocateStockRequest":
        priority_set = set(self.priority_item_upholstery_ids)
        donor_set = set(self.donor_item_upholstery_ids)
        if priority_set & donor_set:
            raise ValueError(
                "priority_item_upholstery_ids and donor_item_upholstery_ids must not overlap."
            )
        return self


def parse_reallocate_stock_request(data: dict) -> ReallocateStockRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return ReallocateStockRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

#### Step 12.2 — CREATE services/commands/items/reallocate_available_stock.py

**File:** `backend/app/beyo_manager/services/commands/items/reallocate_available_stock.py`

```python
from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.items._allocation_algorithm import run_skip_and_continue_allocation
from beyo_manager.services.commands.items.requests.reallocate_stock_request import (
    parse_reallocate_stock_request,
)
from beyo_manager.services.context import ServiceContext


async def reallocate_available_stock(ctx: ServiceContext) -> dict:
    """
    CMD-9: Move donor AVAILABLE requirements back to NEEDS_ORDERING, then run
    skip-and-continue allocation to give priority items first access to the pool.
    No inventory field mutations — stored and in_need are unchanged.
    """
    request = parse_reallocate_stock_request(ctx.incoming_data)

    async with ctx.session.begin():
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == request.upholstery_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inv = inv_result.scalar_one_or_none()
        if inv is None:
            raise NotFound("UpholsteryInventory not found for this upholstery.")

        donor_set = set(request.donor_item_upholstery_ids)
        priority_set = set(request.priority_item_upholstery_ids)

        # Load donor requirements — must all be AVAILABLE
        donor_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.upholstery_inventory_id == inv.client_id,
                ItemUpholsteryRequirement.item_upholstery_id.in_(donor_set),
                ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum.AVAILABLE,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        donor_reqs = donor_result.scalars().all()

        if len(donor_reqs) != len(donor_set):
            raise ValidationError(
                "All donor requirements must be in AVAILABLE state."
            )

        # Move donors to NEEDS_ORDERING (no inventory change — in_need is unchanged)
        for req in donor_reqs:
            req.state = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
            req.updated_by_id = ctx.user_id

        # Load all ORDERED and NEEDS_ORDERING requirements (including donors now back at NEEDS_ORDERING)
        all_candidates_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.upholstery_inventory_id == inv.client_id,
                ItemUpholsteryRequirement.state.in_([
                    ItemUpholsteryRequirementStateEnum.ORDERED,
                    ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
                ]),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        all_candidates = all_candidates_result.scalars().all()

        # Pool calculation (same formula as CMD-5)
        total_candidate_need = sum((r.amount_meters or Decimal("0")) for r in all_candidates)
        stored = inv.current_stored_amount_meters or Decimal("0")
        in_need = inv.current_amount_in_need_meters or Decimal("0")
        running_pool = stored - (in_need - total_candidate_need)

        # Sort into tiers
        priority_order = {iid: idx for idx, iid in enumerate(request.priority_item_upholstery_ids)}
        tier1 = sorted(
            [r for r in all_candidates if r.item_upholstery_id in priority_set],
            key=lambda r: priority_order.get(r.item_upholstery_id, 9999),
        )
        tier2 = sorted(
            [r for r in all_candidates if r.item_upholstery_id not in priority_set
             and r.state == ItemUpholsteryRequirementStateEnum.ORDERED],
            key=lambda r: r.ordered_at or r.created_at,
        )
        tier3 = sorted(
            [r for r in all_candidates if r.item_upholstery_id not in priority_set
             and r.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING],
            key=lambda r: r.created_at,
        )
        ordered_candidates = tier1 + tier2 + tier3

        result_dict = run_skip_and_continue_allocation(
            candidates=ordered_candidates,
            running_pool=running_pool,
            target_state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
            timestamp_field=None,
        )

        modified_ids = set(result_dict["resolved"])
        for req in ordered_candidates:
            if req.item_upholstery_id in modified_ids:
                req.updated_by_id = ctx.user_id

    donor_ids = request.donor_item_upholstery_ids
    return {
        "reallocated_to": result_dict["resolved"],
        "returned_to_needs_ordering": [d for d in donor_ids if d not in set(result_dict["resolved"])],
    }
```

---

### PHASE 13 — Queries

---

#### Step 13.1 — CREATE services/queries/items/ package

Create `backend/app/beyo_manager/services/queries/items/__init__.py` (empty).

---

#### Step 13.2 — CREATE services/queries/items/list_item_upholsteries.py

**File:** `backend/app/beyo_manager/services/queries/items/list_item_upholsteries.py`

```python
from sqlalchemy import select

from beyo_manager.domain.items.serializers import serialize_item_upholstery
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_item_upholsteries(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    stmt = (
        select(ItemUpholstery)
        .where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.is_deleted.is_(False),
        )
        .order_by(ItemUpholstery.created_at.asc())
        .offset(offset)
        .limit(limit + 1)
    )

    if item_id := ctx.query_params.get("item_id"):
        stmt = stmt.where(ItemUpholstery.item_id == item_id)

    if upholstery_id := ctx.query_params.get("upholstery_id"):
        stmt = stmt.where(ItemUpholstery.upholstery_id == upholstery_id)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "item_upholsteries": [serialize_item_upholstery(r) for r in page],
        "item_upholsteries_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
```

---

#### Step 13.3 — CREATE services/queries/items/get_item_upholstery.py

**File:** `backend/app/beyo_manager/services/queries/items/get_item_upholstery.py`

```python
from sqlalchemy import select

from beyo_manager.domain.items.serializers import serialize_item_upholstery, serialize_upholstery_requirement
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.context import ServiceContext


async def get_item_upholstery(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(ItemUpholstery).where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.client_id == client_id,
            ItemUpholstery.is_deleted.is_(False),
        )
    )
    iup = result.scalar_one_or_none()
    if iup is None:
        raise NotFound("ItemUpholstery not found.")

    req_result = await ctx.session.execute(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
            ItemUpholsteryRequirement.item_upholstery_id == client_id,
            ItemUpholsteryRequirement.is_deleted.is_(False),
        ).order_by(ItemUpholsteryRequirement.created_at.asc())
    )
    requirements = req_result.scalars().all()

    data = serialize_item_upholstery(iup)
    data["requirements"] = [serialize_upholstery_requirement(r) for r in requirements]
    return {"item_upholstery": data}
```

---

#### Step 13.4 — CREATE services/queries/items/list_upholstery_requirements.py

**File:** `backend/app/beyo_manager/services/queries/items/list_upholstery_requirements.py`

```python
from sqlalchemy import select

from beyo_manager.domain.items.serializers import serialize_upholstery_requirement
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_upholstery_requirements(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    stmt = (
        select(ItemUpholsteryRequirement)
        .where(
            ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
        .order_by(ItemUpholsteryRequirement.created_at.asc())
        .offset(offset)
        .limit(limit + 1)
    )

    if item_upholstery_id := ctx.query_params.get("item_upholstery_id"):
        stmt = stmt.where(ItemUpholsteryRequirement.item_upholstery_id == item_upholstery_id)

    if state := ctx.query_params.get("state"):
        from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
        stmt = stmt.where(ItemUpholsteryRequirement.state == ItemUpholsteryRequirementStateEnum(state))

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "upholstery_requirements": [serialize_upholstery_requirement(r) for r in page],
        "upholstery_requirements_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
```

---

### PHASE 14 — Router and registration

---

#### Step 14.1 — CREATE routers/api_v1/item_upholsteries.py

**Route order:** Static action routes (`/mark-ordered`, `/resolve-after-stock`, `/reallocate-stock`) MUST be declared BEFORE wildcard `/{id}` routes.

**File:** `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`

```python
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.commands.items.apply_surplus_to_requirement import apply_surplus_to_requirement
from beyo_manager.services.commands.items.complete_requirement_instance import complete_requirement_instance
from beyo_manager.services.commands.items.create_item_upholstery import create_item_upholstery
from beyo_manager.services.commands.items.mark_requirements_completed import mark_requirements_completed
from beyo_manager.services.commands.items.mark_requirements_in_use import mark_requirements_in_use
from beyo_manager.services.commands.items.mark_requirements_ordered import mark_requirements_ordered
from beyo_manager.services.commands.items.reallocate_available_stock import reallocate_available_stock
from beyo_manager.services.commands.items.resolve_requirements_after_stock import resolve_requirements_after_stock
from beyo_manager.services.commands.items.set_requirement_quantity import set_requirement_quantity
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.items.get_item_upholstery import get_item_upholstery
from beyo_manager.services.queries.items.list_item_upholsteries import list_item_upholsteries
from beyo_manager.services.queries.items.list_upholstery_requirements import list_upholstery_requirements
from beyo_manager.services.run_service import run_service

router = APIRouter()


# ---- Request body models ----

class CreateItemUpholsteryBody(BaseModel):
    item_id: str
    upholstery_id: str | None = None
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    source: ItemUpholsterySourceEnum
    time_to_fix_in_seconds: int | None = None


class MarkOrderedBody(BaseModel):
    upholstery_id: str
    ordered_quantity: Decimal
    priority_item_upholstery_ids: list[str] = []


class ResolveAfterStockBody(BaseModel):
    upholstery_id: str
    priority_item_upholstery_ids: list[str] = []


class ReallocateStockBody(BaseModel):
    upholstery_id: str
    priority_item_upholstery_ids: list[str]
    donor_item_upholstery_ids: list[str]


class ApplySurplusBody(BaseModel):
    surplus_amount_meters: Decimal


class SetQuantityBody(BaseModel):
    amount_meters: Decimal


class CompleteRequirementBody(BaseModel):
    requirement_id: str


# ---- Collection-level routes ----

@router.put("")
async def create_item_upholstery_route(
    body: CreateItemUpholsteryBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_item_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def list_item_upholsteries_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    item_id: str | None = Query(None),
    upholstery_id: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "item_id": item_id, "upholstery_id": upholstery_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_item_upholsteries, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# ---- Static action routes (must be before /{id} wildcard) ----

@router.post("/mark-ordered")
async def mark_requirements_ordered_route(
    body: MarkOrderedBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(mark_requirements_ordered, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/resolve-after-stock")
async def resolve_requirements_after_stock_route(
    body: ResolveAfterStockBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(resolve_requirements_after_stock, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/reallocate-stock")
async def reallocate_available_stock_route(
    body: ReallocateStockBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(reallocate_available_stock, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# ---- Single-resource routes (wildcard /{id} after statics) ----

@router.get("/{item_upholstery_client_id}")
async def get_item_upholstery_route(
    item_upholstery_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": item_upholstery_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_item_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{item_upholstery_client_id}/requirements")
async def list_requirements_route(
    item_upholstery_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    state: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "item_upholstery_id": item_upholstery_client_id,
            "limit": limit,
            "offset": offset,
            "state": state,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholstery_requirements, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{item_upholstery_client_id}/mark-in-use")
async def mark_in_use_route(
    item_upholstery_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"item_upholstery_id": item_upholstery_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(mark_requirements_in_use, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{item_upholstery_client_id}/complete")
async def complete_all_route(
    item_upholstery_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"item_upholstery_id": item_upholstery_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(mark_requirements_completed, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{item_upholstery_client_id}/apply-surplus")
async def apply_surplus_route(
    item_upholstery_client_id: str,
    body: ApplySurplusBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"item_upholstery_id": item_upholstery_client_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(apply_surplus_to_requirement, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{item_upholstery_client_id}/set-quantity")
async def set_quantity_route(
    item_upholstery_client_id: str,
    body: SetQuantityBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"item_upholstery_id": item_upholstery_client_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(set_requirement_quantity, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# ---- Upholstery requirement direct routes ----

@router.post("/requirements/{requirement_client_id}/complete")
async def complete_requirement_instance_route(
    requirement_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"requirement_id": requirement_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(complete_requirement_instance, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Important:** The `/requirements/{id}/complete` route uses a multi-segment path with the `requirements` static prefix — it will not conflict with `/{item_upholstery_client_id}` because FastAPI matches the full path. However, to be safe, declare it BEFORE the `/{item_upholstery_client_id}` wildcard routes.

---

#### Step 14.2 — EDIT routers/api_v1/__init__.py — register the router

Add import and registration:

```python
# Add import
from beyo_manager.routers.api_v1 import item_upholsteries

# Add inside register_v1_routers(app):
app.include_router(
    item_upholsteries.router,
    prefix="/api/v1/item-upholsteries",
    tags=["item-upholsteries"],
)
```

---

### PHASE 15 — Update intention plan linked table

Edit `INTENTION_item_upholstery_requirement_lifecycle_20260516.md` — update the linked plans table:

```markdown
| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| PLAN_item_upholstery_requirement_lifecycle_20260516 | backend/docs/architecture/under_construction/implementation/PLAN_item_upholstery_requirement_lifecycle_20260516.md | under_construction | All 9 lifecycle commands, CRUD, queries, router |
```

---

## Risks and mitigations

- **Risk:** `run_skip_and_continue_allocation` mutates ORM instances in-place. If the session is not flushed after, changes may not persist.
  **Mitigation:** All callers use `async with ctx.session.begin()` — changes are committed when the block exits. The helper does not need to flush; the command owns the transaction boundary.

- **Risk:** CMD-5 and CMD-9 use the pool formula `stored - (in_need - total_candidate_need)`. If `in_need < total_candidate_need` (can happen if some candidates were already partially resolved), `running_pool` could exceed `stored`.
  **Mitigation:** This is correct — `running_pool` can exceed `stored` if more than the actual stored amount is "spoken for" in need. The allocation will still correctly mark candidates as AVAILABLE only up to the actual available net. The formula is a logical subtraction, not a constraint — the guard is at consume time (CMD-2 / CMD-7), not at allocation time.

- **Risk:** `requirements/{id}/complete` route prefix `requirements` may conflict with `/{item_upholstery_client_id}` wildcard if FastAPI processes them in wrong order.
  **Mitigation:** Declare the `/requirements/{id}/complete` route BEFORE `/{item_upholstery_client_id}` in the router file. FastAPI matches routes in declaration order.

- **Risk:** `generate_client_id` function path may differ from what is imported.
  **Mitigation:** Read `services/infra/identity.py` (permitted relational read) before implementing to confirm the exact function name and import path.

- **Risk:** `roles.py` constants (`ADMIN`, `MANAGER`) may use different names.
  **Mitigation:** Read `routers/utils/roles.py` (permitted relational read) before implementing the router.

---

## Validation plan

- **CMD-1 happy path:** `PUT /api/v1/item-upholsteries` with quantity → requirement state = AVAILABLE. DB: `upholstery_inventory.current_amount_in_need_meters` incremented.
- **CMD-1 MISSING_QUANTITY:** `PUT /api/v1/item-upholsteries` with `amount_meters=null` → requirement state = MISSING_QUANTITY, `amount_meters=null`. Inventory unchanged.
- **CMD-1 guard:** `PUT` with `source=INTERNAL` and no `upholstery_id` → 422.
- **CMD-2:** `POST /mark-in-use` → all AVAILABLE requirements transition to IN_USE. Inventory: `current_stored` decremented, `current_amount_in_use` incremented, `current_amount_in_need` decremented.
- **CMD-3:** `POST /complete` → IN_USE requirements call `finish_in_use`; AVAILABLE ones call `complete_available_direct`. Both end at COMPLETED.
- **CMD-4 skip-and-continue:** Call `/mark-ordered` with `ordered_quantity` smaller than one large requirement but larger than two smaller ones. Verify the large one is skipped, the two smaller ones are marked ORDERED.
- **CMD-5 three-tier ordering:** Verify priority list items get AVAILABLE first, then ORDERED by `ordered_at`, then NEEDS_ORDERING by `created_at`.
- **CMD-6 Case A:** `POST /apply-surplus` with `surplus_amount_meters == requirement.amount_meters` → requirement source=SURPLUS, state=AVAILABLE. One requirement total.
- **CMD-6 Case B:** `POST /apply-surplus` with `surplus_amount_meters < requirement.amount_meters` → two requirements; SURPLUS one is AVAILABLE, INVENTORY one has reduced amount.
- **CMD-7:** `POST /set-quantity` on MISSING_QUANTITY requirement → requirement has new amount, state is AVAILABLE or NEEDS_ORDERING, inventory has updated in_need.
- **CMD-8:** `POST /requirements/{id}/complete` on single IN_USE requirement → only that requirement transitions to COMPLETED.
- **CMD-9:** `POST /reallocate-stock` → donors go to NEEDS_ORDERING, priority items get AVAILABLE first from pool.

---

## Review log

- `2026-05-16` Claude Sonnet 4.6: Plan created from intention plan + contract review.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David Loorenz`
