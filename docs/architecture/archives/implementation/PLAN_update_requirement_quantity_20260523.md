# PLAN_update_requirement_quantity_20260523

## Metadata

- Plan ID: `PLAN_update_requirement_quantity_20260523`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-23T00:00:00Z`
- Last updated at (UTC): `2026-05-23T19:30:19Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- **Goal:** Add a new command and route that allows updating `amount_meters` on an `ItemUpholsteryRequirement` that is in `AVAILABLE` or `NEEDS_ORDERING` state — states where a quantity has already been set but material has not yet been ordered or consumed.
- **Business/user intent:** Users occasionally need to correct a quantity estimate after the initial value has been set. The existing `set-quantity` endpoint only accepts `MISSING_QUANTITY` requirements. This command closes the gap for the two pre-order mutable states without touching any terminal or order-in-flight state.
- **Non-goals:** No changes allowed to `ORDERED`, `IN_USE`, `COMPLETED`, or `FAILED` requirements. No automatic downstream reallocation of freed inventory (the caller can trigger `resolve-after-stock` manually if needed). No migration. No new model. No history record.

## Scope

- **In scope:**
  1. New private helper `adjust_need` in `_inventory_mutations.py`
  2. New request model `UpdateRequirementQuantityRequest` + parser in `requests/__init__.py`
  3. New command file `update_requirement_quantity.py`
  4. New route `POST /{client_id}/update-quantity` in the `item_upholsteries` router

- **Out of scope:** Reallocation of freed inventory to other requirements (manual via `resolve-after-stock`), history recording, notifications, domain events.

- **Assumptions:**
  - A requirement in `AVAILABLE` or `NEEDS_ORDERING` always has `upholstery_inventory_id` set (injected by `set_requirement_quantity`).
  - The `amount_meters` on the requirement precisely matches its contribution to `current_amount_in_need_meters` that was registered during `set_requirement_quantity`. The delta `new - old` is therefore safe to apply.

## Clarifications required

*(none)*

## Acceptance criteria

1. `POST /{client_id}/update-quantity` on an `AVAILABLE` requirement returns `200 {"ok": true}` and `current_amount_in_need_meters` reflects the delta.
2. `POST /{client_id}/update-quantity` on a `NEEDS_ORDERING` requirement returns `200 {"ok": true}` and `current_amount_in_need_meters` reflects the delta.
3. `POST /{client_id}/update-quantity` on a `MISSING_QUANTITY`, `ORDERED`, `IN_USE`, `COMPLETED`, or `FAILED` requirement returns `400 {"ok": false, "error": "Quantity can only be updated on AVAILABLE or NEEDS_ORDERING requirements."}`.
4. After a successful call the requirement `state` is re-evaluated: `AVAILABLE` when `stored - in_need >= 0`, otherwise `NEEDS_ORDERING`.
5. A call with `amount_meters` equal to the existing value is a no-op: returns `200`, no DB writes.
6. `amount_meters <= 0` returns `400` from the request parser before any DB access.

## Contracts and skills

### Contracts loaded

- `../architecture/06_commands.md` + `../architecture/06_commands_local.md`: `maybe_begin` transaction utility, `session.flush` discipline, error-raising shape
- `../architecture/05_errors.md`: `ValidationError` and `NotFound` import paths
- `../architecture/09_routers.md`: handler wiring, `run_service`, `build_ok` / `build_err`
- `../architecture/21_naming_conventions.md`: file naming, CMD docstring convention

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand `maybe_begin` / `session.flush` / error-raising → `06_commands.md`
- Reading another router to understand handler skeleton → `09_routers.md`

Permitted (relational reads — understanding what exists):
- `set_requirement_quantity.py` — exact load pattern (workspace_id first, `active_requirement_id` lookup, state guard)
- `_inventory_mutations.py` — `_load_inventory`, `evaluate_inventory_condition`, flush/return pattern used by existing helpers
- `requests/__init__.py` — where to place the new model and how to write the validator/parser pair
- `item_upholsteries.py` — where to place the new route and how to write the `_Body` inline class

## Implementation plan

---

### Step 1 — Add `adjust_need` helper to `_inventory_mutations.py`

**File:** `backend/app/beyo_manager/services/commands/upholstery/_inventory_mutations.py`

Place the new helper after `add_stored_surplus` (CMD-6) and before `complete_available_direct` (CMD-7). Follow the same structure as the other helpers in this file: load via `_load_inventory`, mutate, flush, return a result dict.

```python
async def adjust_need(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    delta: Decimal,
) -> dict:
    """
    Adjust current_amount_in_need_meters by a signed delta and re-evaluate condition.
    delta > 0: need increases (requirement quantity grew).
    delta < 0: need decreases (requirement quantity shrank).
    Returns {sufficient, condition}.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    new_in_need = max(
        Decimal("0"),
        (inv.current_amount_in_need_meters or Decimal("0")) + delta,
    )
    inv.current_amount_in_need_meters = new_in_need
    inv.inventory_condition = evaluate_inventory_condition(
        inv.current_stored_amount_meters,
        inv.current_amount_in_need_meters,
        inv.low_stock_threshold_meters,
    )
    await session.flush()
    net = (inv.current_stored_amount_meters or Decimal("0")) - new_in_need
    return {
        "sufficient": net >= Decimal("0"),
        "condition": inv.inventory_condition,
    }
```

The `max(Decimal("0"), ...)` guard prevents `current_amount_in_need_meters` from going negative due to any latent inconsistency. The net result is allowed to go negative — that is the `NEEDS_ORDERING` signal.

---

### Step 2 — Add request model and parser to `requests/__init__.py`

**File:** `backend/app/beyo_manager/services/commands/items/requests/__init__.py`

Add `UpdateRequirementQuantityRequest` immediately after `SetQuantityRequest` and add `parse_update_requirement_quantity_request` immediately after `parse_set_quantity_request`. Follow the exact validator and PydanticValidationError-wrapping pattern used by every other class/parser pair in this file.

```python
class UpdateRequirementQuantityRequest(BaseModel):
    """Request to update quantity on AVAILABLE or NEEDS_ORDERING requirement."""
    item_upholstery_id: str
    amount_meters: Decimal

    @field_validator("amount_meters")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("amount_meters must be > 0.")
        return v


def parse_update_requirement_quantity_request(data: dict) -> UpdateRequirementQuantityRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return UpdateRequirementQuantityRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

### Step 3 — Create `update_requirement_quantity.py`

**File:** `backend/app/beyo_manager/services/commands/items/update_requirement_quantity.py`

New file. Follow the structure of `set_requirement_quantity.py` for the `ItemUpholstery` + active requirement load pattern. The command performs four actions inside `maybe_begin`: guards, computes the delta, calls `adjust_need`, updates the requirement.

```python
"""CMD: Update quantity on AVAILABLE or NEEDS_ORDERING requirement."""

from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests import parse_update_requirement_quantity_request
from beyo_manager.services.commands.upholstery._inventory_mutations import adjust_need
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

_MUTABLE_STATES = {
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
                "Quantity can only be updated on AVAILABLE or NEEDS_ORDERING requirements."
            )

        if active_req.upholstery_inventory_id is None:
            raise ValidationError(
                "Requirement has no linked inventory record — quantity cannot be adjusted."
            )

        old_amount = active_req.amount_meters or Decimal("0")
        new_amount = request.amount_meters
        delta = new_amount - old_amount

        if delta == Decimal("0"):
            return {}

        inv_result = await adjust_need(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=active_req.upholstery_inventory_id,
            delta=delta,
        )

        active_req.amount_meters = new_amount
        active_req.state = (
            ItemUpholsteryRequirementStateEnum.AVAILABLE
            if inv_result["sufficient"]
            else ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
        )
        active_req.updated_by_id = ctx.user_id

    return {}
```

---

### Step 4 — Add route to `item_upholsteries.py`

**File:** `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`

**4a.** Add the import at the top of the file alongside the other command imports:

```python
from beyo_manager.services.commands.items.update_requirement_quantity import update_requirement_quantity
```

**4b.** Add the inline body class immediately after `_SetQuantityBody`:

```python
class _UpdateQuantityBody(BaseModel):
    amount_meters: Decimal
```

**4c.** Add the route immediately after `route_set_quantity` and before `route_list_requirements`:

```python
@router.post("/{client_id}/update-quantity")
async def route_update_quantity(
    client_id: str,
    body: _UpdateQuantityBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={
            "item_upholstery_id": client_id,
            "amount_meters": body.amount_meters,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_requirement_quantity, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

## Risks and mitigations

- **Risk:** The `amount_meters` stored on the requirement diverges from its actual contribution to `current_amount_in_need_meters` (e.g., a prior bug left the aggregate inconsistent), making the delta inaccurate.
  **Mitigation:** The `max(Decimal("0"), ...)` guard in `adjust_need` prevents the aggregate from going negative. The operation completes and leaves `current_amount_in_need_meters` at `0` in the degenerate case rather than crashing.

- **Risk:** After a quantity decrease, other `NEEDS_ORDERING` requirements remain blocked even though freed inventory could now cover them.
  **Mitigation:** Documented non-goal. The existing `POST /upholstery/resolve-after-stock` endpoint is the correct mechanism for downstream reallocation and can be called by the caller after a successful quantity decrease.

## Validation plan

- `AVAILABLE` requirement, higher `amount_meters`: requirement stays `AVAILABLE` or flips to `NEEDS_ORDERING`; `current_amount_in_need_meters` increases by delta.
- `AVAILABLE` requirement, lower `amount_meters`: `current_amount_in_need_meters` decreases by delta; state stays `AVAILABLE`.
- `NEEDS_ORDERING` requirement: same checks as `AVAILABLE` above.
- `MISSING_QUANTITY` requirement: `update-quantity` → 400 with guard message.
- `ORDERED` requirement: same 400 guard.
- `amount_meters` equal to current value: 200, no DB writes (`delta == 0` short-circuit).
- `amount_meters <= 0`: 400 from request parser before any DB access.

## Review log

*(none yet)*

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `copilot`
