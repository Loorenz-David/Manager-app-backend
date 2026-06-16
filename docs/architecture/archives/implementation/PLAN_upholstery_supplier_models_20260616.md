# PLAN_upholstery_supplier_models_20260616

## Metadata

- Plan ID: `PLAN_upholstery_supplier_models_20260616`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-06-16T00:00:00Z`
- Last updated at (UTC): `2026-06-16T12:31:35Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/planning_tables/upholstery/upholstery_supplier_models.md`, `backend/docs/architecture/under_construction/intention/planning_tables/upholstery/upholstery_supplier_relationship_models.md`

## Goal and intent

- Goal: Create two new SQLAlchemy ORM model files — `supplier.py` (the `Supplier` registry table) and `upholstery_supplier_link.py` (the `UpholsterySupplierLink` relationship table) — and register them with Alembic in `beyo_manager/models/__init__.py`.
- Business/user intent: The upholstery ordering system requires a supplier registry to identify who supplies materials, and a relationship table that records which suppliers can provide a given upholstery at what price and preference. Both models are prerequisite for the upholstery order lifecycle (covered by a separate plan).
- Non-goals: Commands, queries, routers, serializers, enums (currency enum already exists). Any procurement runtime state, payment state, or order lifecycle logic.

## Scope

- In scope:
  - New file `models/tables/upholstery/supplier.py` — `Supplier` model
  - New file `models/tables/upholstery/upholstery_supplier_link.py` — `UpholsterySupplierLink` model
  - Update `beyo_manager/models/__init__.py` — register both new modules for Alembic detection

- Out of scope:
  - Any changes to existing upholstery models (`upholstery.py`, `upholstery_inventory.py`)
  - Enum creation (UpholsteryCurrencyEnum already exists in `domain/upholstery/enums.py`; the `upholstery_currency_enum` PG type is already created by `upholstery_inventory.py`)
  - Alembic migration authoring — the migration must be generated separately after these models are registered

- Assumptions:
  - `upholstery_currency_enum` Postgres enum type is already present in the database (created by `UpholsteryInventory`). The `upholstery_supplier_link.py` model must therefore use `create_type=False` for the currency SAEnum column.
  - `IdentityMixin` from `beyo_manager.models.base.identity` provides `client_id` as a prefixed ULID primary key.
  - `configure_sa_enum_values` from `beyo_manager.models.base.sa_enum` must wrap `SAEnum` imports when used (as done in `upholstery_inventory.py`).
  - `workspaces`, `users`, `upholsteries` tables are already defined and available for FK references with `ondelete="RESTRICT"`.

## Clarifications required

- [ ] Should `base_url` on `Supplier` be validated as a URL format at the model layer, or is that deferred to command-layer request parsers? — this does not block model creation but affects whether a CheckConstraint is needed.
- [ ] Are soft-deleted suppliers allowed to remain as FK targets on `upholstery_supplier_links` rows without enforcement? — FK uses `ondelete="RESTRICT"` which would block hard deletion of suppliers with links; soft deletion is unaffected, so this is consistent with the intention document's replay-safe semantics.
- [ ] Should the unique constraint on `upholstery_supplier_links(workspace_id, upholstery_id, supplier_id)` cover soft-deleted rows or only active ones? — the intention document does not specify a partial index, so the constraint covers all rows (including soft-deleted) in this plan.

## Acceptance criteria

1. Running `alembic revision --autogenerate -m "add_supplier_and_upholstery_supplier_link"` produces a migration that creates the `suppliers` table and `upholstery_supplier_links` table with all columns, constraints, and indexes specified below.
2. `from beyo_manager.models.tables.upholstery.supplier import Supplier` resolves without import error.
3. `from beyo_manager.models.tables.upholstery.upholstery_supplier_link import UpholsterySupplierLink` resolves without import error.
4. `Supplier.CLIENT_ID_PREFIX == "sup"` and `UpholsterySupplierLink.CLIENT_ID_PREFIX == "usl"`.
5. `alembic check` passes (no undetected model changes) after the migration is applied.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_model_base.md` (or equivalent): `IdentityMixin`, `Base`, `mapped_column`, `Mapped` usage pattern
- `backend/architecture/03_enums.md` (or equivalent): `configure_sa_enum_values`, `create_type=False` for pre-existing PG enum types

### Local extensions loaded

- None

### File read intent — pattern vs. relational

Permitted relational reads:
- `models/tables/upholstery/upholstery_inventory.py` — exact SAEnum import pattern with `configure_sa_enum_values` and `create_type=False` (currency enum already exists)
- `models/tables/upholstery/upholstery.py` — FK pattern, UniqueConstraint naming, `ondelete="RESTRICT"` convention
- `models/__init__.py` — registration block location and comment style
- `domain/upholstery/enums.py` — verify `UpholsteryCurrencyEnum` is already defined there

Prohibited (pattern reads — contract already covers these):
- Reading other model files to understand `IdentityMixin` or `mapped_column` usage → contract covers this

### Skill selection

- Primary skill: model authoring
- Router trigger terms: none (this plan has no router, command, or query work)
- Excluded alternatives: none

## Implementation plan

### Step 1 — Create `supplier.py`

**File:** `backend/app/beyo_manager/models/tables/upholstery/supplier.py` (new file)

```python
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class Supplier(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "sup"
    __tablename__ = "suppliers"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    street_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
        UniqueConstraint("workspace_id", "name", name="uq_suppliers_workspace_name"),
    )
```

Key decisions:
- No CheckConstraint on `base_url` — URL validation is a command-layer concern.
- `updated_at` uses `onupdate` lambda — matches the pattern in `upholstery.py` and `upholstery_inventory.py`.
- No index on `name` alone — the unique constraint covers workspace-scoped name lookups.

---

### Step 2 — Create `upholstery_supplier_link.py`

**File:** `backend/app/beyo_manager/models/tables/upholstery/upholstery_supplier_link.py` (new file)

```python
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class UpholsterySupplierLink(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "usl"
    __tablename__ = "upholstery_supplier_links"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    upholstery_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("upholsteries.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    supplier_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("suppliers.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    priority_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[UpholsteryCurrencyEnum | None] = mapped_column(
        SAEnum(UpholsteryCurrencyEnum, name="upholstery_currency_enum", create_type=False), nullable=True
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        UniqueConstraint(
            "workspace_id", "upholstery_id", "supplier_id",
            name="uq_upholstery_supplier_links_workspace_upholstery_supplier",
        ),
        CheckConstraint(
            "price_minor IS NULL OR price_minor >= 0",
            name="ck_upholstery_supplier_links_price_positive",
        ),
        CheckConstraint(
            "priority_order IS NULL OR priority_order >= 0",
            name="ck_upholstery_supplier_links_priority_positive",
        ),
    )
```

Key decisions:
- `create_type=False` for `upholstery_currency_enum` — the PG type was already created by `UpholsteryInventory`. Using `create_type=True` here would cause a `DuplicateObject` error on migration.
- The unique constraint includes soft-deleted rows (no partial index) — consistent with how `uq_suppliers_workspace_name` on `Supplier` is defined, and with the intention document's omission of a partial-index note.
- `last_checked_at` is operational metadata only; it is not a lifecycle timestamp and has no `onupdate` handler.

---

### Step 3 — Register in `beyo_manager/models/__init__.py`

**File:** `backend/app/beyo_manager/models/__init__.py`

Insert the following two lines **after** the existing `# --- Upholstery inventory (depends on upholstery) ---` block (line 76 area), and **before** `# --- Customers ---`:

```python
# --- Supplier registry and upholstery-supplier relationships (depend on upholstery) ---
from beyo_manager.models.tables.upholstery import supplier  # noqa: F401
from beyo_manager.models.tables.upholstery import upholstery_supplier_link  # noqa: F401
```

`supplier` must be listed before `upholstery_supplier_link` because the link table FK references `suppliers.client_id`.

## Risks and mitigations

- Risk: `create_type=True` accidentally used for `upholstery_currency_enum` in `upholstery_supplier_link.py` — would cause a Postgres `DuplicateObject` error on `alembic upgrade head`.
  Mitigation: The plan explicitly specifies `create_type=False`; Codex must match the pattern from `upholstery_inventory.py` exactly.

- Risk: Registering `upholstery_supplier_link` before `supplier` in `__init__.py` — Alembic processes metadata in import order; the FK from link → supplier requires supplier to be in metadata first.
  Mitigation: The plan specifies `supplier` must appear before `upholstery_supplier_link`.

- Risk: The unique constraint on `upholstery_supplier_links` covers soft-deleted rows; reactivating a soft-deleted link for the same `(workspace_id, upholstery_id, supplier_id)` triple will conflict.
  Mitigation: Future commands must handle reactivation by restoring the existing soft-deleted row rather than inserting a new one. This is a command-layer concern outside this plan's scope — document it in the intention file if needed.

## Validation plan

- `python -c "from beyo_manager.models.tables.upholstery.supplier import Supplier; print(Supplier.CLIENT_ID_PREFIX)"` → prints `sup`
- `python -c "from beyo_manager.models.tables.upholstery.upholstery_supplier_link import UpholsterySupplierLink; print(UpholsterySupplierLink.CLIENT_ID_PREFIX)"` → prints `usl`
- `python -c "import beyo_manager.models"` → no import error (full model registry loads cleanly)
- `alembic revision --autogenerate -m "add_supplier_and_upholstery_supplier_link"` → generates migration with CREATE TABLE for `suppliers` and `upholstery_supplier_links`, no spurious changes to existing tables
- `alembic upgrade head` → applies without error
- `alembic check` → no pending changes

## Review log

- `2026-06-16`: Implemented `Supplier` and `UpholsterySupplierLink`, registered both modules in `beyo_manager.models`, and wrote `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_upholstery_supplier_models_20260616.md`.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `claude-sonnet-4-6`
