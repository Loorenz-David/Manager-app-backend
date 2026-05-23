# PLAN_merge_set_update_quantity_20260523

## Metadata

- Plan ID: `PLAN_merge_set_update_quantity_20260523`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-23T00:00:00Z`
- Last updated at (UTC): `2026-05-23T19:47:25Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- **Goal:** Merge the `set-quantity` and `update-quantity` endpoints into a single `POST /{client_id}/update-quantity` that dispatches internally based on the requirement's current state. Remove the now-redundant `set-quantity` endpoint and its backing command.
- **Business/user intent:** Callers should not need to inspect a requirement's state before deciding which URL to call. One endpoint, one payload — the backend resolves the correct path.
- **Non-goals:** No change to inventory mutation logic (`check_and_inject_need`, `adjust_need`). No change to request shape (`item_upholstery_id`, `amount_meters`). No migration.

## Scope

- **In scope:**
  1. Extend `update_requirement_quantity.py` to handle `MISSING_QUANTITY` via the original `check_and_inject_need` path in addition to the existing `AVAILABLE` / `NEEDS_ORDERING` delta-adjust path.
  2. Remove `set_requirement_quantity.py` (deleted).
  3. Remove `SetQuantityRequest` and `parse_set_quantity_request` from `requests/__init__.py`.
  4. Remove the `set-quantity` route, its import, and its `_SetQuantityBody` class from `item_upholsteries.py`.

- **Out of scope:** Any change to `_inventory_mutations.py`, `adjust_need`, or `check_and_inject_need`. No changes to `ORDERED`, `IN_USE`, `COMPLETED`, `FAILED` handling.

- **Assumptions:**
  - No other file in the codebase imports `set_requirement_quantity` or `SetQuantityRequest` / `parse_set_quantity_request` outside of the files being modified. Codex must verify this with a grep before deleting.

## Clarifications required

*(none)*

## Acceptance criteria

1. `POST /{client_id}/update-quantity` with a `MISSING_QUANTITY` requirement behaves identically to the old `set-quantity`: injects the full need via `check_and_inject_need`, sets `upholstery_inventory_id`, transitions state to `AVAILABLE` or `NEEDS_ORDERING`.
2. `POST /{client_id}/update-quantity` with an `AVAILABLE` or `NEEDS_ORDERING` requirement applies the delta via `adjust_need` and re-evaluates state — unchanged from the existing `update-quantity` behaviour.
3. `POST /{client_id}/update-quantity` on `ORDERED`, `IN_USE`, `COMPLETED`, or `FAILED` returns `400 {"ok": false, "error": "Quantity can only be set on requirements in MISSING_QUANTITY, AVAILABLE, or NEEDS_ORDERING state."}`.
4. `POST /{client_id}/set-quantity` returns `404` (route no longer exists).
5. `amount_meters <= 0` returns `400` from the request parser before any DB access.
6. A call on `AVAILABLE` or `NEEDS_ORDERING` with `amount_meters` equal to the current value is a no-op: returns `200`, no DB writes.

## Contracts and skills

### Contracts loaded

- `../architecture/06_commands.md` + `../architecture/06_commands_local.md`: `maybe_begin`, `session.flush`, error-raising shape
- `../architecture/05_errors.md`: `ValidationError`, `NotFound` import paths
- `../architecture/09_routers.md`: handler wiring, `run_service`, `build_ok` / `build_err`

### File read intent — pattern vs. relational

Permitted (relational reads — understanding what exists):
- `update_requirement_quantity.py` — current implementation being extended
- `set_requirement_quantity.py` — source of the `MISSING_QUANTITY` branch logic to inline
- `item_upholsteries.py` — to locate and remove `set-quantity` route, import, and body class
- `requests/__init__.py` — to remove `SetQuantityRequest` and its parser

Prohibited (pattern reads):
- Reading any other command or router to understand structure → use contracts

## Implementation plan

---

### Step 1 — Verify no other consumers before deleting

Before making any change, run the following greps and confirm no results outside the files listed in scope:

```
grep -r "set_requirement_quantity" backend/app --include="*.py"
grep -r "SetQuantityRequest\|parse_set_quantity_request" backend/app --include="*.py"
```

Expected results: only `set_requirement_quantity.py`, `requests/__init__.py`, and `item_upholsteries.py`. If any other file appears, stop and report before proceeding.

---

### Step 2 — Extend `update_requirement_quantity.py` to handle `MISSING_QUANTITY`

**File:** `backend/app/beyo_manager/services/commands/items/update_requirement_quantity.py`

Replace the entire file with the merged version below. The only new addition is the `MISSING_QUANTITY` branch inside `maybe_begin`. The `AVAILABLE` / `NEEDS_ORDERING` branch is unchanged.

```python
"""CMD: Set or update quantity on a mutable requirement."""

from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests import parse_update_requirement_quantity_request
from beyo_manager.services.commands.upholstery._inventory_mutations import adjust_need, check_and_inject_need
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

_MUTABLE_STATES = {
    ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
    ItemUpholsteryRequirementStateEnum.AVAILABLE,
    ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING,
}


async def update_requirement_quantity(ctx: ServiceContext) -> dict:
    request = parse_update_requirement_quantity_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
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
        active_req = req_result.scalar_one_or_none()
        if active_req is None:
            raise NotFound("Active requirement not found.")

        if active_req.state not in _MUTABLE_STATES:
            raise ValidationError(
                "Quantity can only be set on requirements in MISSING_QUANTITY, AVAILABLE, or NEEDS_ORDERING state."
            )

        if active_req.state == ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY:
            inv_result = await check_and_inject_need(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_id=iup.upholstery_id,
                quantity=request.amount_meters,
                inject=True,
            )
            active_req.amount_meters = request.amount_meters
            active_req.upholstery_inventory_id = inv_result["inventory_id"]
            active_req.state = (
                ItemUpholsteryRequirementStateEnum.AVAILABLE
                if inv_result["sufficient"]
                else ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
            )
            active_req.updated_by_id = ctx.user_id

        else:
            if active_req.upholstery_inventory_id is None:
                raise ValidationError(
                    "Requirement has no linked inventory record — quantity cannot be adjusted."
                )

            old_amount = active_req.amount_meters or Decimal("0")
            delta = request.amount_meters - old_amount

            if delta == Decimal("0"):
                return {}

            inv_result = await adjust_need(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                upholstery_inventory_id=active_req.upholstery_inventory_id,
                delta=delta,
            )
            active_req.amount_meters = request.amount_meters
            active_req.state = (
                ItemUpholsteryRequirementStateEnum.AVAILABLE
                if inv_result["sufficient"]
                else ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
            )
            active_req.updated_by_id = ctx.user_id

    return {}
```

---

### Step 3 — Remove `SetQuantityRequest` and `parse_set_quantity_request` from `requests/__init__.py`

**File:** `backend/app/beyo_manager/services/commands/items/requests/__init__.py`

Delete the `SetQuantityRequest` class and the `parse_set_quantity_request` function. No other change to this file.

---

### Step 4 — Delete `set_requirement_quantity.py`

**File:** `backend/app/beyo_manager/services/commands/items/set_requirement_quantity.py`

Delete the file entirely. It is fully superseded by the merged command.

---

### Step 5 — Remove `set-quantity` from the router

**File:** `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`

Remove these three things:

1. The import line:
   ```python
   from beyo_manager.services.commands.items.set_requirement_quantity import set_requirement_quantity
   ```

2. The `_SetQuantityBody` inline class.

3. The `route_set_quantity` handler (`@router.post("/{client_id}/set-quantity")` and its body).

The `update-quantity` route and `_UpdateQuantityBody` class are **unchanged**.

---

## Risks and mitigations

- **Risk:** Another file imports `set_requirement_quantity` or `SetQuantityRequest` and breaks at import time after deletion.
  **Mitigation:** Step 1 requires a grep confirmation before any deletion. Stop if unexpected references are found.

- **Risk:** A caller (e.g., integration test, script, worker) still calls `POST /set-quantity` after the route is removed.
  **Mitigation:** The route returns `404` immediately — no silent data corruption. Callers will need to update to `update-quantity`.

## Validation plan

- `MISSING_QUANTITY` requirement → `POST /update-quantity` → 200, `upholstery_inventory_id` set, state transitions to `AVAILABLE` or `NEEDS_ORDERING`.
- `AVAILABLE` requirement → `POST /update-quantity` with different `amount_meters` → 200, delta applied.
- `AVAILABLE` requirement → `POST /update-quantity` with same `amount_meters` → 200, no DB writes.
- `NEEDS_ORDERING` requirement → same as `AVAILABLE` checks above.
- `ORDERED` requirement → `POST /update-quantity` → 400 guard message.
- `POST /set-quantity` → 404.
- `amount_meters <= 0` → 400 from parser.
- Server starts cleanly with no import errors.

## Review log

*(none yet)*

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `copilot`
