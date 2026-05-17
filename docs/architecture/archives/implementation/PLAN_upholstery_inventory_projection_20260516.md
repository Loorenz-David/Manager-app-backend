# PLAN_upholstery_inventory_projection_20260516

## Metadata

- Plan ID: `PLAN_upholstery_inventory_projection_20260516`
- Status: `under_construction`
- Owner agent: `GitHub Copilot`
- Created at (UTC): `2026-05-16T14:00:00Z`
- Last updated at (UTC): `2026-05-16T14:00:00Z`
- Related issue/ticket: `—`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_upholstery_inventory_projection_20260516.md`

## Goal and intent

- **Goal:** Implement the complete upholstery inventory projection layer: prerequisite DB migrations, a deterministic `evaluate_condition` pure function, 7 composable private mutation helpers callable by any service, 3 public CRUD commands, read queries, and a router — so every inventory field write flows through one controlled command set and `inventory_condition` is always accurate.
- **Business/user intent:** Workspace managers need a reliable view of how much of each upholstery material is stored, in use, on order, or needed. This plan locks down the mutation surface so no service can diverge the aggregate.
- **Non-goals:** `upholstery_inventory_history_records`, warehouse location tracking, notification/event emission on condition change, replay from history.

## Scope

- **In scope:**
  - 4 Alembic migrations (drop threshold policy table + enums, add `low_stock_threshold_meters`, add `missing_quantity` enum value, make `amount_meters` nullable on requirements)
  - Delete `upholstery_inventory_threshold_policy.py` model file
  - Update `item_upholstery_requirement.py` model (`amount_meters` nullable, updated constraint)
  - Domain pure function `evaluate_inventory_condition` in `domain/upholstery/condition_evaluation.py`
  - Domain serializer `domain/upholstery/serializers.py`
  - 7 private mutation helpers in `services/commands/upholstery/_inventory_mutations.py`
  - 3 public CRUD commands: `create_upholstery_inventory.py`, `update_upholstery_inventory.py`, `delete_upholstery_inventory.py`
  - 2 public action commands: `confirm_ordered_to_stock.py`, `add_ordered.py`
  - 2 queries: `list_upholstery_inventories.py`, `get_upholstery_inventory.py`
  - 1 new router file `routers/api_v1/upholstery_inventories.py`
  - Registration in `routers/api_v1/__init__.py`
- **Out of scope:** Intention 1 (requirement lifecycle), item_upholstery commands, external order placement system.
- **Assumptions:**
  - `low_stock_threshold_meters` is already in the `UpholsteryInventory` model (confirmed — `upholstery_inventory.py` line 64).
  - `MISSING_QUANTITY` is already in `ItemUpholsteryRequirementStateEnum` Python enum (confirmed — `domain/items/enums.py`).
  - `upholstery_inventory_threshold_policy.py` model exists and will be deleted (confirmed — file found).
  - `alembic` CLI is available in the app environment.

## Clarifications required

*(none — all design decisions resolved in the intention plan)*

## Acceptance criteria

1. `alembic upgrade head` applies all 4 migrations without error.
2. `upholstery_inventory_threshold_policies` table and its DB enums are dropped.
3. `upholstery_inventory.low_stock_threshold_meters` column exists as `NUMERIC(14,3) NULL`.
4. `item_upholstery_requirement_state_enum` DB type includes the value `missing_quantity`.
5. `item_upholstery_requirements.amount_meters` is nullable in the DB.
6. `evaluate_inventory_condition(stored, in_need, threshold)` returns the correct `UpholsteryInventoryConditionEnum` value for all input combinations (see condition logic).
7. All 7 mutation helpers in `_inventory_mutations.py` are importable and callable with `(session, ...)` parameters; they flush but never commit.
8. `PUT /api/v1/upholstery-inventories` creates a new inventory row and returns `{"data": {"client_id": "<uin_...>"}, "warnings": []}`.
9. `PATCH /api/v1/upholstery-inventories/{id}` updates allowed fields and returns `{"data": {}, "warnings": []}`.
10. `DELETE /api/v1/upholstery-inventories/{id}` soft-deletes and returns `{"data": {}, "warnings": []}`.
11. `GET /api/v1/upholstery-inventories` returns a paginated list with `upholstery_inventories_pagination`.
12. `GET /api/v1/upholstery-inventories/{id}` returns the full inventory row.
13. `POST /api/v1/upholstery-inventories/{id}/add-ordered` increments `current_amount_ordered_meters`.
14. `POST /api/v1/upholstery-inventories/{id}/confirm-ordered` moves quantity from ordered → stored and re-evaluates condition.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: layer separation — models, domain, services, routers
- `backend/architecture/05_errors.md`: `ValidationError`, `ConflictError` from `beyo_manager.errors.validation`; `NotFound` from `beyo_manager.errors.not_found`
- `backend/architecture/06_commands.md`: command skeleton, `async with ctx.session.begin()`, flush pattern, returning `dict`
- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: offset-based pagination, `_MAX_LIMIT = 200`, `_DEFAULT_LIMIT = 50`, `<entity>_pagination` key required
- `backend/architecture/09_routers.md`: `build_ok`/`build_err`, `ServiceContext`, `run_service`, route declaration order (statics before wildcards)
- `backend/architecture/21_naming_conventions.md`: file naming (`<verb>_<noun>.py`), function naming (`<verb>_<noun>(ctx) -> dict`), private prefix `_`
- `backend/architecture/30_migrations.md`: Alembic auto-generate pattern, enum add-value pattern, nullable-first for new columns

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination overrides cursor pagination

### File read intent — pattern vs. relational

Before reading any file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

Prohibited (contract already covers these):
- Reading another command for `session.add` / flush shape → `06_commands.md`
- Reading another query for pagination shape → `07_queries_local.md`
- Reading another router for handler wiring → `09_routers.md`

Permitted relational reads:
- `models/tables/upholstery/upholstery_inventory.py` — exact field names and types
- `models/tables/items/item_upholstery_requirement.py` — confirm `amount_meters` column to make nullable
- `models/tables/upholstery/upholstery_inventory_threshold_policy.py` — confirm what to delete
- `routers/api_v1/__init__.py` — confirm registration pattern before editing
- `services/commands/working_sections/create_working_section.py` — confirm import paths for ServiceContext and event dispatch (relational: what the existing code does)

### Skill selection

- Primary skill: `—` *(direct implementation — no task-system skill required)*

---

## Implementation plan

### PHASE 0 — Prerequisite migrations and model cleanup

---

#### Step 0.1 — READ models/tables/upholstery/upholstery_inventory_threshold_policy.py

Read the file to identify what foreign keys, enums, and constraints exist before deleting it.

---

#### Step 0.2 — UPDATE models/tables/items/item_upholstery_requirement.py

Make `amount_meters` nullable and update its check constraint.

**File:** `backend/app/beyo_manager/models/tables/items/item_upholstery_requirement.py`

Change line 41:
```python
# BEFORE
amount_meters: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)

# AFTER
amount_meters: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
```

Change the check constraint in `__table_args__` (line 94):
```python
# BEFORE
CheckConstraint("amount_meters >= 0", name="ck_item_upholstery_requirements_amount_positive"),

# AFTER
CheckConstraint(
    "amount_meters IS NULL OR amount_meters >= 0",
    name="ck_item_upholstery_requirements_amount_positive",
),
```

---

#### Step 0.3 — DELETE models/tables/upholstery/upholstery_inventory_threshold_policy.py

Delete the file:
```
backend/app/beyo_manager/models/tables/upholstery/upholstery_inventory_threshold_policy.py
```

---

#### Step 0.4 — CHECK models/tables/__init__.py and models/tables/upholstery/__init__.py

Read both `__init__.py` files and remove any imports of `UpholsteryInventoryThresholdPolicy`. If the upholstery `__init__.py` imports it, remove that line.

---

#### Step 0.5 — GENERATE Migration 1: drop threshold policy table

Run from inside `backend/app/`:
```bash
alembic revision --autogenerate -m "drop_upholstery_inventory_threshold_policies"
```

**Review the generated migration.** It should include:
- `op.drop_table("upholstery_inventory_threshold_policies")`
- Drop statements for DB enums: `threshold_policy_scope_enum`, `sourcing_escalation_policy_enum`, `inventory_warning_tier_enum`

If auto-generate does not detect the enum drops (common), add them manually to the `upgrade()` function:
```python
def upgrade():
    op.drop_table("upholstery_inventory_threshold_policies")
    op.execute("DROP TYPE IF EXISTS threshold_policy_scope_enum")
    op.execute("DROP TYPE IF EXISTS sourcing_escalation_policy_enum")
    op.execute("DROP TYPE IF EXISTS inventory_warning_tier_enum")

def downgrade():
    # Recreating the dropped enums and table is intentionally omitted —
    # this is a permanent removal. Add manual steps here if ever needed.
    pass
```

Apply: `alembic upgrade head`

---

#### Step 0.6 — GENERATE Migration 2: add low_stock_threshold_meters column

The column is already in the model (`upholstery_inventory.py` line 64). Run:
```bash
alembic revision --autogenerate -m "add_low_stock_threshold_meters_to_upholstery_inventory"
```

Review: the generated migration should add:
```python
op.add_column(
    "upholstery_inventory",
    sa.Column("low_stock_threshold_meters", sa.Numeric(precision=14, scale=3), nullable=True),
)
op.create_check_constraint(
    "ck_upholstery_inventory_low_stock_threshold_positive",
    "upholstery_inventory",
    "low_stock_threshold_meters IS NULL OR low_stock_threshold_meters > 0",
)
```

Apply: `alembic upgrade head`

---

#### Step 0.7 — GENERATE Migration 3: add missing_quantity to state enum

Run:
```bash
alembic revision --autogenerate -m "add_missing_quantity_to_item_upholstery_requirement_state_enum"
```

Auto-generate will NOT detect enum value additions automatically. Add manually to the generated file:
```python
def upgrade():
    op.execute("ALTER TYPE item_upholstery_requirement_state_enum ADD VALUE IF NOT EXISTS 'missing_quantity'")

def downgrade():
    # Postgres cannot remove enum values — log manual steps only
    pass
```

Apply: `alembic upgrade head`

---

#### Step 0.8 — GENERATE Migration 4: make amount_meters nullable on requirements

The model was updated in Step 0.2. Run:
```bash
alembic revision --autogenerate -m "make_item_upholstery_requirement_amount_meters_nullable"
```

Review: the generated migration should:
1. Alter column nullable → True:
```python
op.alter_column("item_upholstery_requirements", "amount_meters", existing_type=sa.Numeric(precision=12, scale=3), nullable=True)
```
2. Drop old constraint and add updated one:
```python
op.drop_constraint("ck_item_upholstery_requirements_amount_positive", "item_upholstery_requirements", type_="check")
op.create_check_constraint(
    "ck_item_upholstery_requirements_amount_positive",
    "item_upholstery_requirements",
    "amount_meters IS NULL OR amount_meters >= 0",
)
```

Apply: `alembic upgrade head`

---

### PHASE 1 — Domain layer

---

#### Step 1.1 — CREATE domain/upholstery/condition_evaluation.py

**File:** `backend/app/beyo_manager/domain/upholstery/condition_evaluation.py`

```python
from decimal import Decimal

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum


def evaluate_inventory_condition(
    stored: Decimal | None,
    in_need: Decimal | None,
    threshold: Decimal | None,
) -> UpholsteryInventoryConditionEnum:
    safe_stored = stored or Decimal("0")
    safe_need = in_need or Decimal("0")
    net = safe_stored - safe_need

    if net <= Decimal("0"):
        return UpholsteryInventoryConditionEnum.OUT_OF_STOCK

    if threshold is not None and net < threshold:
        return UpholsteryInventoryConditionEnum.LOW_STOCK

    return UpholsteryInventoryConditionEnum.AVAILABLE
```

**Invariants:**
- `net = stored − in_need`. If `net <= 0` → `OUT_OF_STOCK`.
- If `threshold` is not null and `net < threshold` → `LOW_STOCK`.
- Otherwise → `AVAILABLE`.
- Null fields are treated as zero (empty inventory, no need).
- No hysteresis — the same threshold applies for downward and upward transitions.

---

#### Step 1.2 — CREATE domain/upholstery/serializers.py

**File:** `backend/app/beyo_manager/domain/upholstery/serializers.py`

```python
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory


def serialize_upholstery_inventory(inv: UpholsteryInventory) -> dict:
    return {
        "client_id": inv.client_id,
        "workspace_id": inv.workspace_id,
        "upholstery_id": inv.upholstery_id,
        "inventory_condition": inv.inventory_condition.value,
        "current_stored_amount_meters": str(inv.current_stored_amount_meters) if inv.current_stored_amount_meters is not None else None,
        "current_amount_in_use_meters": str(inv.current_amount_in_use_meters) if inv.current_amount_in_use_meters is not None else None,
        "current_amount_in_need_meters": str(inv.current_amount_in_need_meters) if inv.current_amount_in_need_meters is not None else None,
        "current_amount_ordered_meters": str(inv.current_amount_ordered_meters) if inv.current_amount_ordered_meters is not None else None,
        "total_upholstery_used_meters": str(inv.total_upholstery_used_meters) if inv.total_upholstery_used_meters is not None else None,
        "total_upholstery_used_inventory_meters": str(inv.total_upholstery_used_inventory_meters) if inv.total_upholstery_used_inventory_meters is not None else None,
        "total_upholstery_used_surplus_meters": str(inv.total_upholstery_used_surplus_meters) if inv.total_upholstery_used_surplus_meters is not None else None,
        "total_upholstery_surplus_meters": str(inv.total_upholstery_surplus_meters) if inv.total_upholstery_surplus_meters is not None else None,
        "low_stock_threshold_meters": str(inv.low_stock_threshold_meters) if inv.low_stock_threshold_meters is not None else None,
        "minimum_to_have": inv.minimum_to_have,
        "maximum_to_have": inv.maximum_to_have,
        "projected_inventory_value_minor": inv.projected_inventory_value_minor,
        "currency": inv.currency.value if inv.currency else None,
        "planning_position": inv.planning_position,
        "latest_projection_history_id": inv.latest_projection_history_id,
        "created_at": inv.created_at.isoformat(),
        "created_by_id": inv.created_by_id,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        "updated_by_id": inv.updated_by_id,
        "is_deleted": inv.is_deleted,
    }
```

---

### PHASE 2 — Private inventory mutation helpers

All 7 mutation helpers live in one module. They are `async` functions that take `session: AsyncSession` and explicit parameters — NOT `ctx: ServiceContext`. They call `await session.flush()` when they write. They never call `session.begin()` or `session.commit()` — the calling command owns the transaction.

**File:** `backend/app/beyo_manager/services/commands/upholstery/_inventory_mutations.py`

```python
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementSourceEnum
from beyo_manager.domain.upholstery.condition_evaluation import evaluate_inventory_condition
from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.infra.identity import generate_client_id


# ---------------------------------------------------------------------------
# CMD-1 — check_and_inject_need
# ---------------------------------------------------------------------------

async def check_and_inject_need(
    session: AsyncSession,
    workspace_id: str,
    upholstery_id: str,
    quantity: Decimal,
    inject: bool = True,
) -> dict:
    """
    Load or create the UpholsteryInventory row for (workspace_id, upholstery_id).
    When inject=True: add quantity to current_amount_in_need_meters and flush.
    Always returns: {inventory_id, sufficient, condition}.
    When inject=False: pure read — no writes, no flush.
    """
    result = await session.execute(
        select(UpholsteryInventory).where(
            UpholsteryInventory.workspace_id == workspace_id,
            UpholsteryInventory.upholstery_id == upholstery_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
    )
    inv = result.scalar_one_or_none()

    if inv is None:
        inv = UpholsteryInventory(
            client_id=generate_client_id(UpholsteryInventory.CLIENT_ID_PREFIX),
            workspace_id=workspace_id,
            upholstery_id=upholstery_id,
            current_stored_amount_meters=Decimal("0"),
            current_amount_in_need_meters=Decimal("0"),
            current_amount_in_use_meters=Decimal("0"),
            current_amount_ordered_meters=Decimal("0"),
            total_upholstery_used_meters=Decimal("0"),
            total_upholstery_used_inventory_meters=Decimal("0"),
            total_upholstery_used_surplus_meters=Decimal("0"),
            total_upholstery_surplus_meters=Decimal("0"),
            inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
            low_stock_threshold_meters=None,
        )
        session.add(inv)
        if inject:
            await session.flush()

    if inject:
        inv.current_amount_in_need_meters = (inv.current_amount_in_need_meters or Decimal("0")) + quantity
        inv.inventory_condition = evaluate_inventory_condition(
            inv.current_stored_amount_meters,
            inv.current_amount_in_need_meters,
            inv.low_stock_threshold_meters,
        )
        await session.flush()

    net = (inv.current_stored_amount_meters or Decimal("0")) - (inv.current_amount_in_need_meters or Decimal("0"))
    return {
        "inventory_id": inv.client_id,
        "sufficient": net >= Decimal("0"),
        "condition": inv.inventory_condition,
    }


# ---------------------------------------------------------------------------
# CMD-2 — consume_to_in_use
# ---------------------------------------------------------------------------

async def consume_to_in_use(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
) -> None:
    """
    Move quantity from stored → in_use. Decrements in_need (requirement is now active).
    Guard: raises ValidationError if stored would go negative.
    No condition re-evaluation — net (stored − in_need) is unchanged.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    new_stored = (inv.current_stored_amount_meters or Decimal("0")) - quantity
    if new_stored < Decimal("0"):
        raise ValidationError(
            "Not enough upholstery in stored inventory to start production — "
            "please add more stock before marking in-use."
        )
    inv.current_stored_amount_meters = new_stored
    inv.current_amount_in_use_meters = (inv.current_amount_in_use_meters or Decimal("0")) + quantity
    inv.current_amount_in_need_meters = max(
        Decimal("0"),
        (inv.current_amount_in_need_meters or Decimal("0")) - quantity,
    )
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-3 — finish_in_use
# ---------------------------------------------------------------------------

async def finish_in_use(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    source: ItemUpholsteryRequirementSourceEnum,
) -> None:
    """
    Decrement in_use by quantity; route to used_inventory or used_surplus totals by source.
    Guard: raises ValidationError if in_use would go negative.
    No condition re-evaluation — net (stored − in_need) is unchanged.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    new_in_use = (inv.current_amount_in_use_meters or Decimal("0")) - quantity
    if new_in_use < Decimal("0"):
        raise ValidationError(
            "Inventory inconsistency: completion quantity exceeds recorded in-use amount."
        )
    inv.current_amount_in_use_meters = new_in_use
    inv.total_upholstery_used_meters = (inv.total_upholstery_used_meters or Decimal("0")) + quantity
    if source == ItemUpholsteryRequirementSourceEnum.INVENTORY:
        inv.total_upholstery_used_inventory_meters = (
            inv.total_upholstery_used_inventory_meters or Decimal("0")
        ) + quantity
    elif source == ItemUpholsteryRequirementSourceEnum.SURPLUS:
        inv.total_upholstery_used_surplus_meters = (
            inv.total_upholstery_used_surplus_meters or Decimal("0")
        ) + quantity
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-4 — add_ordered (internal helper — also wrapped by public command)
# ---------------------------------------------------------------------------

async def add_ordered(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
) -> None:
    """
    Increment current_amount_ordered_meters. No condition re-evaluation.
    Called by the external order system via the public command wrapper.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    inv.current_amount_ordered_meters = (inv.current_amount_ordered_meters or Decimal("0")) + quantity
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-5 — confirm_ordered_to_stock (internal helper — also wrapped by public command)
# ---------------------------------------------------------------------------

async def confirm_ordered_to_stock(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
) -> None:
    """
    Move quantity from ordered → stored. Re-evaluates condition.
    Guard: raises ValidationError if ordered would go negative.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    new_ordered = (inv.current_amount_ordered_meters or Decimal("0")) - quantity
    if new_ordered < Decimal("0"):
        raise ValidationError(
            "Confirmed quantity exceeds the recorded ordered amount — "
            "verify the stock quantity before confirming."
        )
    inv.current_amount_ordered_meters = new_ordered
    inv.current_stored_amount_meters = (inv.current_stored_amount_meters or Decimal("0")) + quantity
    inv.inventory_condition = evaluate_inventory_condition(
        inv.current_stored_amount_meters,
        inv.current_amount_in_need_meters,
        inv.low_stock_threshold_meters,
    )
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-6 — add_stored_surplus
# ---------------------------------------------------------------------------

async def add_stored_surplus(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
) -> None:
    """
    Add offcut/surplus material to stored inventory. Re-evaluates condition.
    Does NOT modify in_need — need decrements only when material moves to in_use (CMD-2).
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    inv.current_stored_amount_meters = (inv.current_stored_amount_meters or Decimal("0")) + quantity
    inv.total_upholstery_surplus_meters = (inv.total_upholstery_surplus_meters or Decimal("0")) + quantity
    inv.inventory_condition = evaluate_inventory_condition(
        inv.current_stored_amount_meters,
        inv.current_amount_in_need_meters,
        inv.low_stock_threshold_meters,
    )
    await session.flush()


# ---------------------------------------------------------------------------
# CMD-7 — complete_available_direct
# ---------------------------------------------------------------------------

async def complete_available_direct(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
    quantity: Decimal,
    source: ItemUpholsteryRequirementSourceEnum,
) -> None:
    """
    Atomic combine of consume + finish for AVAILABLE → COMPLETED (skips IN_USE).
    Decrements stored and in_need by same quantity — net unchanged, no condition re-eval.
    Guard: raises ValidationError if stored would go negative.
    """
    inv = await _load_inventory(session, workspace_id, upholstery_inventory_id)
    new_stored = (inv.current_stored_amount_meters or Decimal("0")) - quantity
    if new_stored < Decimal("0"):
        raise ValidationError(
            "Not enough upholstery in stored inventory to complete directly — "
            "stock may have changed since availability was confirmed."
        )
    inv.current_stored_amount_meters = new_stored
    inv.current_amount_in_need_meters = max(
        Decimal("0"),
        (inv.current_amount_in_need_meters or Decimal("0")) - quantity,
    )
    inv.total_upholstery_used_meters = (inv.total_upholstery_used_meters or Decimal("0")) + quantity
    if source == ItemUpholsteryRequirementSourceEnum.INVENTORY:
        inv.total_upholstery_used_inventory_meters = (
            inv.total_upholstery_used_inventory_meters or Decimal("0")
        ) + quantity
    elif source == ItemUpholsteryRequirementSourceEnum.SURPLUS:
        inv.total_upholstery_used_surplus_meters = (
            inv.total_upholstery_used_surplus_meters or Decimal("0")
        ) + quantity
    await session.flush()


# ---------------------------------------------------------------------------
# Private loader — shared by all mutation helpers
# ---------------------------------------------------------------------------

async def _load_inventory(
    session: AsyncSession,
    workspace_id: str,
    upholstery_inventory_id: str,
) -> UpholsteryInventory:
    result = await session.execute(
        select(UpholsteryInventory).where(
            UpholsteryInventory.workspace_id == workspace_id,
            UpholsteryInventory.client_id == upholstery_inventory_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise NotFound("UpholsteryInventory not found.")
    return inv
```

---

### PHASE 3 — Public CRUD commands

---

#### Step 3.1 — CREATE services/commands/upholstery/ package

Create the directory and an empty `__init__.py`:
```
backend/app/beyo_manager/services/commands/upholstery/__init__.py
```

---

#### Step 3.2 — CREATE services/commands/upholstery/requests/ package and request models

Create `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py` (empty).

**File:** `backend/app/beyo_manager/services/commands/upholstery/requests/create_upholstery_inventory_request.py`

```python
from decimal import Decimal

from pydantic import BaseModel, field_validator

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.errors.validation import ValidationError


class CreateUpholsteryInventoryRequest(BaseModel):
    upholstery_id: str
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None

    @field_validator("low_stock_threshold_meters")
    @classmethod
    def threshold_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= Decimal("0"):
            raise ValueError("low_stock_threshold_meters must be greater than 0.")
        return v

    @field_validator("minimum_to_have", "maximum_to_have", "projected_inventory_value_minor")
    @classmethod
    def must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0.")
        return v


def parse_create_upholstery_inventory_request(data: dict) -> CreateUpholsteryInventoryRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return CreateUpholsteryInventoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

**File:** `backend/app/beyo_manager/services/commands/upholstery/requests/update_upholstery_inventory_request.py`

```python
from decimal import Decimal

from pydantic import BaseModel, field_validator

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.errors.validation import ValidationError


class UpdateUpholsteryInventoryRequest(BaseModel):
    client_id: str
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None

    @field_validator("low_stock_threshold_meters")
    @classmethod
    def threshold_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= Decimal("0"):
            raise ValueError("low_stock_threshold_meters must be greater than 0.")
        return v


def parse_update_upholstery_inventory_request(data: dict) -> UpdateUpholsteryInventoryRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return UpdateUpholsteryInventoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

**File:** `backend/app/beyo_manager/services/commands/upholstery/requests/delete_upholstery_inventory_request.py`

```python
from pydantic import BaseModel
from beyo_manager.errors.validation import ValidationError


class DeleteUpholsteryInventoryRequest(BaseModel):
    client_id: str


def parse_delete_upholstery_inventory_request(data: dict) -> DeleteUpholsteryInventoryRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return DeleteUpholsteryInventoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

**File:** `backend/app/beyo_manager/services/commands/upholstery/requests/add_ordered_request.py`

```python
from decimal import Decimal
from pydantic import BaseModel, field_validator
from beyo_manager.errors.validation import ValidationError


class AddOrderedRequest(BaseModel):
    client_id: str
    quantity: Decimal

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("quantity must be > 0.")
        return v


def parse_add_ordered_request(data: dict) -> AddOrderedRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return AddOrderedRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

**File:** `backend/app/beyo_manager/services/commands/upholstery/requests/confirm_ordered_request.py`

```python
from decimal import Decimal
from pydantic import BaseModel, field_validator
from beyo_manager.errors.validation import ValidationError


class ConfirmOrderedRequest(BaseModel):
    client_id: str
    quantity: Decimal

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("quantity must be > 0.")
        return v


def parse_confirm_ordered_request(data: dict) -> ConfirmOrderedRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return ConfirmOrderedRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

#### Step 3.3 — CREATE services/commands/upholstery/create_upholstery_inventory.py

**File:** `backend/app/beyo_manager/services/commands/upholstery/create_upholstery_inventory.py`

```python
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.domain.upholstery.serializers import serialize_upholstery_inventory
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests.create_upholstery_inventory_request import (
    parse_create_upholstery_inventory_request,
)
from beyo_manager.services.context import ServiceContext


async def create_upholstery_inventory(ctx: ServiceContext) -> dict:
    request = parse_create_upholstery_inventory_request(ctx.incoming_data)

    async with ctx.session.begin():
        existing = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == request.upholstery_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(
                "An inventory record already exists for this upholstery in this workspace."
            )

        inv = UpholsteryInventory(
            workspace_id=ctx.workspace_id,
            upholstery_id=request.upholstery_id,
            inventory_condition=UpholsteryInventoryConditionEnum.AVAILABLE,
            current_stored_amount_meters=Decimal("0"),
            current_amount_in_need_meters=Decimal("0"),
            current_amount_in_use_meters=Decimal("0"),
            current_amount_ordered_meters=Decimal("0"),
            total_upholstery_used_meters=Decimal("0"),
            total_upholstery_used_inventory_meters=Decimal("0"),
            total_upholstery_used_surplus_meters=Decimal("0"),
            total_upholstery_surplus_meters=Decimal("0"),
            low_stock_threshold_meters=request.low_stock_threshold_meters,
            minimum_to_have=request.minimum_to_have,
            maximum_to_have=request.maximum_to_have,
            projected_inventory_value_minor=request.projected_inventory_value_minor,
            currency=request.currency,
            planning_position=request.planning_position,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(inv)

    return {"client_id": inv.client_id}
```

---

#### Step 3.4 — CREATE services/commands/upholstery/update_upholstery_inventory.py

**File:** `backend/app/beyo_manager/services/commands/upholstery/update_upholstery_inventory.py`

```python
from datetime import datetime, timezone
from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests.update_upholstery_inventory_request import (
    parse_update_upholstery_inventory_request,
)
from beyo_manager.services.context import ServiceContext


async def update_upholstery_inventory(ctx: ServiceContext) -> dict:
    request = parse_update_upholstery_inventory_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.client_id == request.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inv = result.scalar_one_or_none()
        if inv is None:
            raise NotFound("UpholsteryInventory not found.")

        if request.low_stock_threshold_meters is not None:
            inv.low_stock_threshold_meters = request.low_stock_threshold_meters
        if request.minimum_to_have is not None:
            inv.minimum_to_have = request.minimum_to_have
        if request.maximum_to_have is not None:
            inv.maximum_to_have = request.maximum_to_have
        if request.projected_inventory_value_minor is not None:
            inv.projected_inventory_value_minor = request.projected_inventory_value_minor
        if request.currency is not None:
            inv.currency = request.currency
        if request.planning_position is not None:
            inv.planning_position = request.planning_position
        inv.updated_by_id = ctx.user_id
        inv.updated_at = datetime.now(timezone.utc)

    return {}
```

---

#### Step 3.5 — CREATE services/commands/upholstery/delete_upholstery_inventory.py

**File:** `backend/app/beyo_manager/services/commands/upholstery/delete_upholstery_inventory.py`

```python
from datetime import datetime, timezone
from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests.delete_upholstery_inventory_request import (
    parse_delete_upholstery_inventory_request,
)
from beyo_manager.services.context import ServiceContext


async def delete_upholstery_inventory(ctx: ServiceContext) -> dict:
    request = parse_delete_upholstery_inventory_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.client_id == request.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inv = result.scalar_one_or_none()
        if inv is None:
            raise NotFound("UpholsteryInventory not found.")

        inv.is_deleted = True
        inv.deleted_at = datetime.now(timezone.utc)
        inv.deleted_by_id = ctx.user_id

    return {}
```

---

#### Step 3.6 — CREATE services/commands/upholstery/add_ordered.py

Public command wrapping the `add_ordered` mutation helper. Called by the external order system API.

**File:** `backend/app/beyo_manager/services/commands/upholstery/add_ordered.py`

```python
from beyo_manager.services.commands.upholstery._inventory_mutations import add_ordered as _add_ordered
from beyo_manager.services.commands.upholstery.requests.add_ordered_request import (
    parse_add_ordered_request,
)
from beyo_manager.services.context import ServiceContext


async def add_ordered(ctx: ServiceContext) -> dict:
    request = parse_add_ordered_request(ctx.incoming_data)

    async with ctx.session.begin():
        await _add_ordered(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=request.client_id,
            quantity=request.quantity,
        )

    return {}
```

---

#### Step 3.7 — CREATE services/commands/upholstery/confirm_ordered_to_stock.py

Public command for marking stock as received.

**File:** `backend/app/beyo_manager/services/commands/upholstery/confirm_ordered_to_stock.py`

```python
from beyo_manager.services.commands.upholstery._inventory_mutations import confirm_ordered_to_stock as _confirm
from beyo_manager.services.commands.upholstery.requests.confirm_ordered_request import (
    parse_confirm_ordered_request,
)
from beyo_manager.services.context import ServiceContext


async def confirm_ordered_to_stock(ctx: ServiceContext) -> dict:
    """
    Moves quantity from ordered → stored and re-evaluates inventory_condition.
    Must be called BEFORE Intention 1 CMD-5 (resolve_requirements_after_stock).
    The task command layer is responsible for sequencing these two operations.
    """
    request = parse_confirm_ordered_request(ctx.incoming_data)

    async with ctx.session.begin():
        await _confirm(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            upholstery_inventory_id=request.client_id,
            quantity=request.quantity,
        )

    return {}
```

---

### PHASE 4 — Queries

---

#### Step 4.1 — CREATE services/queries/upholstery/ package

Create `backend/app/beyo_manager/services/queries/upholstery/__init__.py` (empty).

---

#### Step 4.2 — CREATE services/queries/upholstery/list_upholstery_inventories.py

**File:** `backend/app/beyo_manager/services/queries/upholstery/list_upholstery_inventories.py`

```python
from sqlalchemy import select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_inventory
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_upholstery_inventories(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    stmt = (
        select(UpholsteryInventory)
        .where(
            UpholsteryInventory.workspace_id == ctx.workspace_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
        .order_by(UpholsteryInventory.created_at.asc())
        .offset(offset)
        .limit(limit + 1)
    )

    # Optional filter: upholstery_id
    if upholstery_id := ctx.query_params.get("upholstery_id"):
        stmt = stmt.where(UpholsteryInventory.upholstery_id == upholstery_id)

    # Optional filter: inventory_condition
    if condition := ctx.query_params.get("inventory_condition"):
        from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
        stmt = stmt.where(UpholsteryInventory.inventory_condition == UpholsteryInventoryConditionEnum(condition))

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "upholstery_inventories": [serialize_upholstery_inventory(r) for r in page],
        "upholstery_inventories_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
```

---

#### Step 4.3 — CREATE services/queries/upholstery/get_upholstery_inventory.py

**File:** `backend/app/beyo_manager/services/queries/upholstery/get_upholstery_inventory.py`

```python
from sqlalchemy import select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_inventory
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.context import ServiceContext


async def get_upholstery_inventory(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(UpholsteryInventory).where(
            UpholsteryInventory.workspace_id == ctx.workspace_id,
            UpholsteryInventory.client_id == client_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise NotFound("UpholsteryInventory not found.")

    return {"upholstery_inventory": serialize_upholstery_inventory(inv)}
```

---

### PHASE 5 — Router and registration

---

#### Step 5.1 — CREATE routers/api_v1/upholstery_inventories.py

**File:** `backend/app/beyo_manager/routers/api_v1/upholstery_inventories.py`

```python
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.commands.upholstery.add_ordered import add_ordered
from beyo_manager.services.commands.upholstery.confirm_ordered_to_stock import confirm_ordered_to_stock
from beyo_manager.services.commands.upholstery.create_upholstery_inventory import create_upholstery_inventory
from beyo_manager.services.commands.upholstery.delete_upholstery_inventory import delete_upholstery_inventory
from beyo_manager.services.commands.upholstery.update_upholstery_inventory import update_upholstery_inventory
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.get_upholstery_inventory import get_upholstery_inventory
from beyo_manager.services.queries.upholstery.list_upholstery_inventories import list_upholstery_inventories
from beyo_manager.services.run_service import run_service

router = APIRouter()


class CreateInventoryBody(BaseModel):
    upholstery_id: str
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None


class UpdateInventoryBody(BaseModel):
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None


class OrderQuantityBody(BaseModel):
    quantity: Decimal


# --- Collection routes (must come before /{id}) ---

@router.put("")
async def create_upholstery_inventory_route(
    body: CreateInventoryBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_upholstery_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def list_upholstery_inventories_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    upholstery_id: str | None = Query(None),
    inventory_condition: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "upholstery_id": upholstery_id,
            "inventory_condition": inventory_condition,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholstery_inventories, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# --- Single-resource routes ---

@router.get("/{inventory_client_id}")
async def get_upholstery_inventory_route(
    inventory_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": inventory_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_upholstery_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{inventory_client_id}")
async def update_upholstery_inventory_route(
    inventory_client_id: str,
    body: UpdateInventoryBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": inventory_client_id, **body.model_dump(exclude_none=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_upholstery_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{inventory_client_id}")
async def delete_upholstery_inventory_route(
    inventory_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": inventory_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(delete_upholstery_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{inventory_client_id}/add-ordered")
async def add_ordered_route(
    inventory_client_id: str,
    body: OrderQuantityBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": inventory_client_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(add_ordered, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{inventory_client_id}/confirm-ordered")
async def confirm_ordered_to_stock_route(
    inventory_client_id: str,
    body: OrderQuantityBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": inventory_client_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(confirm_ordered_to_stock, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

#### Step 5.2 — EDIT routers/api_v1/__init__.py — register the router

Add import and registration to `backend/app/beyo_manager/routers/api_v1/__init__.py`:

```python
# Add import
from beyo_manager.routers.api_v1 import upholstery_inventories

# Add inside register_v1_routers(app):
app.include_router(
    upholstery_inventories.router,
    prefix="/api/v1/upholstery-inventories",
    tags=["upholstery-inventories"],
)
```

---

### PHASE 6 — Update intention plan linked table

Edit `INTENTION_upholstery_inventory_projection_20260516.md` — update the "Linked implementation plans" table:

```markdown
| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| PLAN_upholstery_inventory_projection_20260516 | backend/docs/architecture/under_construction/implementation/PLAN_upholstery_inventory_projection_20260516.md | under_construction | All migrations, mutation helpers, CRUD commands, queries, router |
```

---

## Risks and mitigations

- **Risk:** Alembic does not auto-detect enum drops from the removed model file.
  **Mitigation:** Step 0.5 explicitly instructs adding `DROP TYPE` statements manually to the generated migration.

- **Risk:** `generate_client_id` import path may differ from `services/infra/identity.py`.
  **Mitigation:** Permitted relational read — confirm exact import before implementing the helpers.

- **Risk:** `check_and_inject_need` creates a new `UpholsteryInventory` row inside a calling command's transaction. If flush fails (e.g. FK violation), it rolls back the entire outer transaction.
  **Mitigation:** Caller must ensure `upholstery_id` is valid before calling. Guard in CMD-1 of Intention 1 checks for null `upholstery_id`.

- **Risk:** `confirm_ordered_to_stock` must always be called before Intention 1 CMD-5. Sequencing is enforced at the task command layer (not here).
  **Mitigation:** Documented in the command's docstring and open questions in the intention plan.

---

## Validation plan

Run these checks after each phase:

- **Phase 0:** `alembic current` shows head revision. `alembic history` is linear. `psql`: verify `upholstery_inventory_threshold_policies` table is gone, `low_stock_threshold_meters` column exists, `missing_quantity` value in the enum, `amount_meters` is nullable.
- **Phase 1:** Import `evaluate_inventory_condition` from Python shell and run manual assertions:
  - `evaluate_inventory_condition(Decimal("10"), Decimal("15"), None)` → `OUT_OF_STOCK`
  - `evaluate_inventory_condition(Decimal("10"), Decimal("2"), Decimal("5"))` → `LOW_STOCK`
  - `evaluate_inventory_condition(Decimal("10"), Decimal("2"), Decimal("3"))` → `AVAILABLE`
  - `evaluate_inventory_condition(Decimal("10"), Decimal("2"), None)` → `AVAILABLE`
- **Phase 2:** Import `_inventory_mutations` from Python shell — no import error.
- **Phase 3–5:** `curl` the endpoints with a valid JWT token and verify HTTP 200 responses match acceptance criteria.

---

## Review log

- `2026-05-16` Claude Sonnet 4.6: Plan created from intention plan + contract review.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David Loorenz`
