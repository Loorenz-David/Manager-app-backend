# PLAN_upholstery_model_audit_corrections_20260616

## Metadata

- Plan ID: `PLAN_upholstery_model_audit_corrections_20260616`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-06-16T13:00:00Z`
- Last updated at (UTC): `2026-06-16T12:43:25Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/planning_tables/upholstery/upholstery_order_models.md`, `backend/docs/architecture/under_construction/intention/planning_tables/upholstery/upholstery_supplier_relationship_models.md`

## Goal and intent

- Goal: Apply six targeted corrections to three model files identified during a post-implementation audit of `PLAN_upholstery_supplier_models_20260616` and `PLAN_upholstery_order_models_20260616`. All changes are pre-migration — no Alembic migration has been generated yet, so schema corrections are safe to apply now.
- Business/user intent: Two of the issues would cause silent runtime failures (missing `state` default causes NOT NULL violations on order creation; the redundant standalone index on `state` adds unnecessary write overhead to every order mutation). The remaining four are correctness gaps or missing guards that are cheapest to fix before the migration is generated.
- Non-goals: Commands, queries, routers, serializers, migrations. No logic changes — only model/column/constraint/index definitions.

## Scope

- In scope:
  - `models/tables/upholstery/upholstery_order.py`: remove `index=True` from `state`; add `default=UpholsteryOrderStateEnum.DRAFT` to `state`
  - `models/tables/upholstery/upholstery_order_history_record.py`: remove `index=True` from `state`; add `CheckConstraint` on `snapshot_order_amount_meters`
  - `models/tables/upholstery/upholstery_supplier_link.py`: add `Index` import; add composite index on `(workspace_id, upholstery_id, preferred)` to `__table_args__`

- Out of scope:
  - Alembic migration generation — run separately after all corrections are applied
  - Command-layer validation for nullable `upholstery_inventory_id` / `upholstery_supplier_link_id` — flagged in this plan's risks section; must be addressed in the create-order command plan

- Assumptions:
  - No Alembic migration referencing these tables has been generated or applied yet. All changes are at the Python model layer only.
  - `UpholsteryOrderStateEnum` is already imported in `upholstery_order.py`; adding `default=` does not require a new import.
  - The `Index` symbol is not currently imported in `upholstery_supplier_link.py` — it must be added to the import block.

## Clarifications required

_None — all changes are unambiguous corrections with no design decisions outstanding._

## Acceptance criteria

1. `upholstery_order.py`: `state` column has `default=UpholsteryOrderStateEnum.DRAFT` and no `index=True`.
2. `upholstery_order.py`: `__table_args__` composite index `ix_upholstery_orders_workspace_state_created` is unchanged.
3. `upholstery_order_history_record.py`: `state` column has no `index=True`.
4. `upholstery_order_history_record.py`: `__table_args__` contains a `CheckConstraint` named `ck_upholstery_order_history_records_snapshot_amount_positive`.
5. `upholstery_supplier_link.py`: `__table_args__` contains an `Index` named `ix_upholstery_supplier_links_workspace_upholstery_preferred` on `(workspace_id, upholstery_id, preferred)`.
6. `python -c "import beyo_manager.models"` loads without error.
7. `python3 -m py_compile` passes on all three modified files.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_model_base.md` (or equivalent): `mapped_column` `default=` pattern, `__table_args__`, `CheckConstraint`, `Index`

### Local extensions loaded

- None

### File read intent — pattern vs. relational

Permitted relational reads:
- `models/tables/upholstery/upholstery_inventory.py` — confirm `default=` pattern on enum column (`inventory_condition` defaults to `AVAILABLE`)
- `models/tables/upholstery/upholstery_order.py` — read current content before editing (required)
- `models/tables/upholstery/upholstery_order_history_record.py` — read current content before editing (required)
- `models/tables/upholstery/upholstery_supplier_link.py` — read current content before editing (required)

Prohibited (pattern reads):
- Reading other model files to understand CheckConstraint or Index syntax → contract covers this

### Skill selection

- Primary skill: model editing
- Router trigger terms: none
- Excluded alternatives: none

## Implementation plan

All steps are independent edits to three separate files. Apply all three steps, then run the validation commands.

---

### Step 1 — Fix `upholstery_order.py`: remove redundant index; add default state

**File:** `backend/app/beyo_manager/models/tables/upholstery/upholstery_order.py`

**Change A — `state` column:** remove `index=True`; add `default=UpholsteryOrderStateEnum.DRAFT`.

Replace:
```python
    state: Mapped[UpholsteryOrderStateEnum] = mapped_column(
        SAEnum(UpholsteryOrderStateEnum, name="upholstery_order_state_enum", create_type=True),
        nullable=False,
        index=True,
    )
```

With:
```python
    state: Mapped[UpholsteryOrderStateEnum] = mapped_column(
        SAEnum(UpholsteryOrderStateEnum, name="upholstery_order_state_enum", create_type=True),
        nullable=False,
        default=UpholsteryOrderStateEnum.DRAFT,
    )
```

No other changes to this file. The composite `Index("ix_upholstery_orders_workspace_state_created", ...)` in `__table_args__` is correct and must remain untouched.

Why `index=True` is removed: the composite index `(workspace_id, state, created_at)` covers all realistic query patterns in this workspace-scoped application. The standalone `state` index generated by `index=True` is never chosen by the query planner for workspace-filtered queries and adds overhead to every INSERT/UPDATE on `upholstery_orders`.

Why `default=DRAFT` is added: `state` is `NOT NULL`. Without a default, any command that does not explicitly set `state` will receive a database NOT NULL violation. `DRAFT` is the correct initial lifecycle state per the intention document.

---

### Step 2 — Fix `upholstery_order_history_record.py`: remove redundant index; add snapshot constraint

**File:** `backend/app/beyo_manager/models/tables/upholstery/upholstery_order_history_record.py`

**Change A — `state` column:** remove `index=True`.

Replace:
```python
    state: Mapped[UpholsteryOrderStateEnum] = mapped_column(
        SAEnum(UpholsteryOrderStateEnum, name="upholstery_order_state_enum", create_type=False),
        nullable=False,
        index=True,
    )
```

With:
```python
    state: Mapped[UpholsteryOrderStateEnum] = mapped_column(
        SAEnum(UpholsteryOrderStateEnum, name="upholstery_order_state_enum", create_type=False),
        nullable=False,
    )
```

**Change B — `__table_args__`:** add `CheckConstraint` on `snapshot_order_amount_meters`. The current `__table_args__` is a tuple with a single `Index`; a trailing comma is required inside a single-element tuple — verify it is present, then expand it to two elements.

Replace:
```python
    __table_args__ = (
        Index(
            "ix_upholstery_order_history_records_workspace_order_changed",
            "workspace_id",
            "upholstery_order_id",
            "changed_at",
        ),
    )
```

With:
```python
    __table_args__ = (
        Index(
            "ix_upholstery_order_history_records_workspace_order_changed",
            "workspace_id",
            "upholstery_order_id",
            "changed_at",
        ),
        CheckConstraint(
            "snapshot_order_amount_meters IS NULL OR snapshot_order_amount_meters >= 0",
            name="ck_upholstery_order_history_records_snapshot_amount_positive",
        ),
    )
```

`CheckConstraint` is already imported in this file (verify — it was used in the original plan's template). If it is not present in the import block, add it alongside the other SQLAlchemy symbols.

Why the constraint is added: `snapshot_order_amount_meters` captures the value of `order_amount_meters` at the moment of a state transition. The parent column has a `>= 0` guard. The snapshot should carry the same guard for defense-in-depth — a negative snapshot value indicates a data integrity bug upstream that should surface at the DB layer rather than silently persist.

---

### Step 3 — Fix `upholstery_supplier_link.py`: add composite index on `preferred`

**File:** `backend/app/beyo_manager/models/tables/upholstery/upholstery_supplier_link.py`

**Change A — import block:** add `Index` to the SQLAlchemy import list (it is not currently imported).

Replace:
```python
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
```

With:
```python
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
```

**Change B — `__table_args__`:** append the new `Index` as a fourth element.

Replace:
```python
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "upholstery_id",
            "supplier_id",
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

With:
```python
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "upholstery_id",
            "supplier_id",
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
        Index(
            "ix_upholstery_supplier_links_workspace_upholstery_preferred",
            "workspace_id",
            "upholstery_id",
            "preferred",
        ),
    )
```

Why this index: the intention document identifies `preferred` as the explicit operational override for sourcing selection. Sourcing queries that select the preferred supplier for a given upholstery (`WHERE workspace_id = ? AND upholstery_id = ? AND preferred = true`) will use this index. Without it, those queries fall back to the full unique constraint scan.

---

## Risks and mitigations

- Risk: `CheckConstraint` is not yet in the import block of `upholstery_order_history_record.py`.
  Mitigation: Step 2 instructs Codex to verify the import before adding the constraint. The file was generated from the plan template which included `CheckConstraint` in the import block — it should already be present.

- Risk: Removing `index=True` from `state` on `upholstery_order.py` after a migration has already been applied would require a migration to drop the index.
  Mitigation: This plan's assumptions confirm no migration has been applied yet. If a migration was already applied, do NOT remove `index=True` from the Python file; instead create a new migration to drop the index. Codex must verify this assumption before proceeding.

- Risk: Command layer for future create-order operations does not explicitly pass `state` and relies on the Python-level default not propagating through SQLAlchemy bulk INSERT paths.
  Mitigation: The `default=` on `mapped_column` applies at the Python ORM layer (not at the DB column level via `server_default`). For ORM `session.add()` patterns this is sufficient. For bulk `INSERT` via `session.execute(insert(...))` the default does not apply — future commands using bulk insert must pass `state` explicitly. Flag this in the create-order command plan.

- Risk: `nullable FK` gap — both `upholstery_inventory_id` and `upholstery_supplier_link_id` on `UpholsteryOrder` are nullable, so a row can be created with no traceability to any upholstery.
  Mitigation: Cannot be enforced at the model layer (CheckConstraint cannot cross tables). The create-order command must validate that at least one of these two FKs is non-null before inserting. Document this requirement in the create-order command plan as a mandatory guard.

## Validation plan

- `python3 -m py_compile backend/app/beyo_manager/models/tables/upholstery/upholstery_order.py` → passes
- `python3 -m py_compile backend/app/beyo_manager/models/tables/upholstery/upholstery_order_history_record.py` → passes
- `python3 -m py_compile backend/app/beyo_manager/models/tables/upholstery/upholstery_supplier_link.py` → passes
- `PYTHONPATH=backend/app python3 -c "import beyo_manager.models"` → no import error
- `PYTHONPATH=backend/app python3 -c "from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder; from beyo_manager.domain.upholstery.enums import UpholsteryOrderStateEnum; col = UpholsteryOrder.__table__.c['state']; print(col.default.arg)"` → prints `UpholsteryOrderStateEnum.DRAFT`
- `PYTHONPATH=backend/app python3 -c "from beyo_manager.models.tables.upholstery.upholstery_order import UpholsteryOrder; indexes = [i.name for i in UpholsteryOrder.__table__.indexes]; print(indexes)"` → list contains `ix_upholstery_orders_workspace_state_created` and does NOT contain any standalone `ix_upholstery_orders_state`
- `PYTHONPATH=backend/app python3 -c "from beyo_manager.models.tables.upholstery.upholstery_order_history_record import UpholsteryOrderHistoryRecord; constraints = [c.name for c in UpholsteryOrderHistoryRecord.__table__.constraints]; print(constraints)"` → list contains `ck_upholstery_order_history_records_snapshot_amount_positive`
- `PYTHONPATH=backend/app python3 -c "from beyo_manager.models.tables.upholstery.upholstery_supplier_link import UpholsterySupplierLink; indexes = [i.name for i in UpholsterySupplierLink.__table__.indexes]; print(indexes)"` → list contains `ix_upholstery_supplier_links_workspace_upholstery_preferred`

## Review log

- `2026-06-16`: Applied all six audit corrections across `upholstery_order.py`, `upholstery_order_history_record.py`, and `upholstery_supplier_link.py`, then wrote `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_upholstery_model_audit_corrections_20260616.md`.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `claude-sonnet-4-6`
