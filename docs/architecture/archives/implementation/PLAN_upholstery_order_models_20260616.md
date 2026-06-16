# PLAN_upholstery_order_models_20260616

## Metadata

- Plan ID: `PLAN_upholstery_order_models_20260616`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-06-16T00:00:00Z`
- Last updated at (UTC): `2026-06-16T12:31:35Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/planning_tables/upholstery/upholstery_order_models.md`

## Goal and intent

- Goal: Add `UpholsteryOrderStateEnum` to the upholstery enums file, create two new SQLAlchemy ORM model files — `upholstery_order.py` (the `UpholsteryOrder` procurement lifecycle table) and `upholstery_order_history_record.py` (the `UpholsteryOrderHistoryRecord` append-only snapshot table) — and register them with Alembic in `beyo_manager/models/__init__.py`.
- Business/user intent: Upholstery procurement is tracked as a lifecycle of state transitions (DRAFT → ORDERED → RECEIVED, etc.) with an append-only history table for replay-safe reconstruction. These models are the domain-owned source of truth for sourcing intent and progression; they deliberately exclude accounting, payment, and warehouse runtime authority.
- Non-goals: Commands, queries, routers, serializers. Any payment/accounting models. Alembic migration authoring. Any changes to inventory counters triggered by order transitions (future integration scope).

## Scope

- In scope:
  - Extend `beyo_manager/domain/upholstery/enums.py` — append `UpholsteryOrderStateEnum`
  - New file `models/tables/upholstery/upholstery_order.py` — `UpholsteryOrder` model
  - New file `models/tables/upholstery/upholstery_order_history_record.py` — `UpholsteryOrderHistoryRecord` model
  - Update `beyo_manager/models/__init__.py` — register both new modules for Alembic detection

- Out of scope:
  - Commands or routers for order creation/state transitions
  - Changes to `upholstery_inventory.py`, `supplier.py`, or `upholstery_supplier_link.py`
  - Alembic migration authoring — generate separately after models are registered

- Assumptions:
  - `PLAN_upholstery_supplier_models_20260616` has already been applied: `suppliers` table and `upholstery_supplier_links` table exist in the codebase and in the database. `UpholsteryOrder` holds FKs to both.
  - `upholstery_currency_enum` Postgres enum type already exists in the DB. Both new models reference it with `create_type=False`.
  - `upholstery_inventory` table exists and `upholstery_inventory_id` on `UpholsteryOrder` can reference it with `ondelete="RESTRICT"`. The FK is nullable — a NULL value means the order is not yet linked to a specific inventory record.
  - `IdentityMixin`, `Base`, `configure_sa_enum_values`, and `ondelete="RESTRICT"` FK convention are used exactly as in `upholstery_inventory.py`.

## Clarifications required

- [ ] Should `APPROVED` be optional or mandatory before `ORDERED`? — does not block model creation (the enum contains all states; transition guards are a command-layer concern), but should be resolved before writing order commands.
- [ ] Can `FAILED` transition back to `PENDING`/`APPROVED`, or must recovery always create a new order row? — does not block model creation; affects future command logic only.
- [ ] Is `supplier_id` on `UpholsteryOrder` required in phase one, or can it remain nullable while `upholstery_supplier_link_id` snapshots the relationship? — the intention document marks it nullable; this plan implements it as nullable and does not change that decision.
- [ ] Should `upholstery_order_state_enum` be a shared PG type or a new type? — this plan creates it as a new PG type via `create_type=True` on the first column that uses it (`UpholsteryOrder.state`). `UpholsteryOrderHistoryRecord.state` and `UpholsteryOrderHistoryRecord.snapshot_state` both reference the same type with `create_type=False`.

## Acceptance criteria

1. `UpholsteryOrderStateEnum` is importable from `beyo_manager.domain.upholstery.enums` with values: `DRAFT`, `PENDING`, `APPROVED`, `ORDERED`, `FAILED`, `CANCELLED`, `PARTIALLY_RECEIVED`, `RECEIVED`.
2. Running `alembic revision --autogenerate` produces a migration that creates `upholstery_orders` and `upholstery_order_history_records` with all columns, constraints, and indexes below, plus a new PG enum type `upholstery_order_state_enum`.
3. `from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder` resolves without error; `UpholsteryOrder.CLIENT_ID_PREFIX == "uor"`.
4. `from beyo_manager.models.tables.upholstery.upholstery_order_history_record import UpholsteryOrderHistoryRecord` resolves without error; `UpholsteryOrderHistoryRecord.CLIENT_ID_PREFIX == "uoh"`.
5. `python -c "import beyo_manager.models"` loads without error.
6. `alembic check` passes after migration is applied.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_model_base.md` (or equivalent): `IdentityMixin`, `Base`, `mapped_column`, `Mapped` usage
- `backend/architecture/03_enums.md` (or equivalent): enum class pattern, `create_type=True` for new PG type vs `create_type=False` for existing type

### Local extensions loaded

- None

### File read intent — pattern vs. relational

Permitted relational reads:
- `models/tables/upholstery/upholstery_inventory.py` — SAEnum with `configure_sa_enum_values`, `create_type=False`, Numeric, CheckConstraint naming pattern
- `models/tables/upholstery/upholstery.py` — FK pattern with `ondelete="RESTRICT"`, Index naming convention
- `models/tables/items/item_upholstery_requirement.py` — state enum with `create_type=True` on a lifecycle model, index with state column
- `domain/upholstery/enums.py` — existing enum members to append after; verify `UpholsteryCurrencyEnum` and `UpholsteryInventoryConditionEnum` are already present
- `models/__init__.py` — registration block location and comment style

Prohibited (pattern reads — contract already covers these):
- Reading other model files to understand `IdentityMixin` or `mapped_column` usage → contract covers this

### Skill selection

- Primary skill: model authoring
- Router trigger terms: none
- Excluded alternatives: none

## Implementation plan

### Step 1 — Extend `enums.py` with `UpholsteryOrderStateEnum`

**File:** `backend/app/beyo_manager/domain/upholstery/enums.py`

Append after the existing `UpholsteryInventoryConditionEnum` class:

```python
class UpholsteryOrderStateEnum(enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    ORDERED = "ordered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
```

No other changes to this file.

---

### Step 2 — Create `upholstery_order.py`

**File:** `backend/app/beyo_manager/models/tables/upholstery/upholstery_order.py` (new file)

```python
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.upholstery.enums import (
    UpholsteryCurrencyEnum,
    UpholsteryOrderStateEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class UpholsteryOrder(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "uor"
    __tablename__ = "upholstery_orders"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_inventory_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("upholstery_inventory.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    upholstery_supplier_link_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("upholstery_supplier_links.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    supplier_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("suppliers.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    order_amount_meters: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    price_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[UpholsteryCurrencyEnum | None] = mapped_column(
        SAEnum(UpholsteryCurrencyEnum, name="upholstery_currency_enum", create_type=False), nullable=True
    )
    order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state: Mapped[UpholsteryOrderStateEnum] = mapped_column(
        SAEnum(UpholsteryOrderStateEnum, name="upholstery_order_state_enum", create_type=True),
        nullable=False,
        index=True,
    )
    ordered_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    expected_receive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_amount_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index("ix_upholstery_orders_workspace_state_created", "workspace_id", "state", "created_at"),
        CheckConstraint(
            "order_amount_meters >= 0",
            name="ck_upholstery_orders_amount_positive",
        ),
        CheckConstraint(
            "price_minor IS NULL OR price_minor >= 0",
            name="ck_upholstery_orders_price_positive",
        ),
    )
```

Key decisions:
- `state` uses `create_type=True` — this is the first model to reference `upholstery_order_state_enum`; Alembic will emit `CREATE TYPE` in the migration.
- `currency` uses `create_type=False` — `upholstery_currency_enum` was already created by `UpholsteryInventory`.
- `upholstery_inventory_id` references `upholstery_inventory.client_id` (the table name is `upholstery_inventory`; column name is `client_id` from `IdentityMixin`).
- `order_amount_meters` is non-nullable — procurement intent must always have a quantity.
- `received_amount_meters` is nullable — receiving is a later lifecycle event; it is intentionally independent from `order_amount_meters` to support partial receiving.
- `ordered_by_id` is a separate FK from `created_by_id` — the actor who placed the order may differ from the actor who created the record in the system.
- The composite index on `(workspace_id, state, created_at)` is the primary listing index for procurement views filtered by state within a workspace.

---

### Step 3 — Create `upholstery_order_history_record.py`

**File:** `backend/app/beyo_manager/models/tables/upholstery/upholstery_order_history_record.py` (new file)

```python
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.upholstery.enums import (
    UpholsteryCurrencyEnum,
    UpholsteryOrderStateEnum,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class UpholsteryOrderHistoryRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "uoh"
    __tablename__ = "upholstery_order_history_records"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("upholstery_orders.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state: Mapped[UpholsteryOrderStateEnum] = mapped_column(
        SAEnum(UpholsteryOrderStateEnum, name="upholstery_order_state_enum", create_type=False),
        nullable=False,
        index=True,
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    snapshot_price_minor: Mapped[int | None] = mapped_column(nullable=True)
    snapshot_currency: Mapped[UpholsteryCurrencyEnum | None] = mapped_column(
        SAEnum(UpholsteryCurrencyEnum, name="upholstery_currency_enum", create_type=False), nullable=True
    )
    snapshot_order_amount_meters: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_upholstery_order_history_records_workspace_order_changed",
            "workspace_id",
            "upholstery_order_id",
            "changed_at",
        ),
    )
```

Key decisions:
- `state` uses `create_type=False` — `upholstery_order_state_enum` was already created by `UpholsteryOrder` (registered first in `__init__.py`). Using `create_type=True` here would cause a `DuplicateObject` error.
- `snapshot_currency` uses `create_type=False` for the same reason as all other currency columns.
- `changed_at` is a separate field from `created_at` — it records the business timestamp of the state transition, while `created_at` records when this history row was inserted. These may differ in import or correction scenarios.
- No `updated_at` / `updated_by_id` — history records are append-only. Soft-deletion fields are present for privileged data governance workflows (matching the intention document's replay-safe semantics), but no update fields.
- `snapshot_price_minor` is typed as `Mapped[int | None]` without an explicit `Integer` column type argument — SQLAlchemy infers `Integer` from the Python type annotation. This is consistent; explicitly passing `Integer` is also fine if Codex prefers it for clarity.

---

### Step 4 — Register in `beyo_manager/models/__init__.py`

**File:** `backend/app/beyo_manager/models/__init__.py`

Insert the following block **after** the supplier block added by `PLAN_upholstery_supplier_models_20260616` (i.e., after `upholstery_supplier_link`) and **before** `# --- Customers ---`:

```python
# --- Upholstery order lifecycle (depends on upholstery_inventory, suppliers, upholstery_supplier_links) ---
from beyo_manager.models.tables.upholstery import upholstery_order  # noqa: F401
from beyo_manager.models.tables.upholstery import upholstery_order_history_record  # noqa: F401
```

`upholstery_order` must appear before `upholstery_order_history_record` because the history record FK references `upholstery_orders.client_id`.

## Risks and mitigations

- Risk: `create_type=True` on `upholstery_order_state_enum` used in both model files — would cause `DuplicateObject` on migration.
  Mitigation: Only `UpholsteryOrder.state` uses `create_type=True`; `UpholsteryOrderHistoryRecord.state` explicitly uses `create_type=False`.

- Risk: `upholstery_order_history_record` registered before `upholstery_order` in `__init__.py` — FK from history to order would require the order table to exist first in Alembic's dependency graph.
  Mitigation: Plan specifies `upholstery_order` before `upholstery_order_history_record`.

- Risk: `PLAN_upholstery_supplier_models_20260616` not applied before this plan — `UpholsteryOrder` FKs to `suppliers` and `upholstery_supplier_links` would fail.
  Mitigation: This plan's assumptions section explicitly calls out the prerequisite. Codex must apply the supplier plan's migration first, then apply this plan's migration.

- Risk: `order_amount_meters` check `>= 0` is a non-null column with a `>= 0` constraint — a zero-meter order is technically valid at the model layer. Business validation (e.g., rejecting zero) is a command-layer responsibility.
  Mitigation: Explicitly documented; command implementation must add a `> 0` validator in the request parser if the business rule requires it.

- Risk: `received_amount_meters` can diverge from `order_amount_meters` in practice, which future analytics queries must handle correctly.
  Mitigation: The intention document explicitly states these are independent fields; this plan preserves that independence. Analytics queries must not assume equality.

## Validation plan

- `python -c "from beyo_manager.domain.upholstery.enums import UpholsteryOrderStateEnum; print([e.value for e in UpholsteryOrderStateEnum])"` → prints all 8 state values
- `python -c "from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder; print(UpholsteryOrder.CLIENT_ID_PREFIX)"` → `uor`
- `python -c "from beyo_manager.models.tables.upholstery.upholstery_order_history_record import UpholsteryOrderHistoryRecord; print(UpholsteryOrderHistoryRecord.CLIENT_ID_PREFIX)"` → `uoh`
- `python -c "import beyo_manager.models"` → no import error
- `alembic revision --autogenerate -m "add_upholstery_order_models"` → generates migration with `CREATE TYPE upholstery_order_state_enum`, `CREATE TABLE upholstery_orders`, `CREATE TABLE upholstery_order_history_records`, and all indexes/constraints; no spurious changes to existing tables
- `alembic upgrade head` → applies without error
- `alembic check` → no pending changes

## Review log

- `2026-06-16`: Added `UpholsteryOrderStateEnum`, implemented `UpholsteryOrder` and `UpholsteryOrderHistoryRecord`, registered both modules in `beyo_manager.models`, and wrote `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_upholstery_order_models_20260616.md`.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `claude-sonnet-4-6`
