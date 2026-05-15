# PLAN_models_tables_20260515

## Metadata

- Plan ID: `PLAN_models_tables_20260515`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T10:00:01Z`
- Related issue/ticket: N/A
- Intention plan: `backend/docs/architecture/under_construction/intention/planning_tables/`

---

## Goal and intent

- Goal: Implement all new domain model tables and their enums for the beyo_manager app.
- Business/user intent: Provide the full data model foundation so workers, sellers, and managers can track second-hand furniture restoration work, task progress, and operational efficiency metrics.
- Non-goals: Commands, queries, routers, serializers, Alembic migration generation, analytics aggregates, upholstery order/supplier lifecycle, upholstery inventory history records.

---

## Scope

- In scope: New base mixins, new `domain/<domain>/enums.py` files, new `models/tables/<domain>/<table>.py` files, registration in `models/__init__.py`, empty `__init__.py` stubs for new domain folders.
- Out of scope: Domain logic (guards, states, validators, calculations), services, routers, Alembic migrations.
- Assumptions:
  - `workspaces` table exists: `models/tables/workspaces/workspace.py`, PK `client_id`.
  - `users` table exists: `models/tables/users/user.py`, PK `client_id`.
  - `IdentityMixin` exists at `beyo_manager/models/base/identity.py`. Uses `declared_attr` for `client_id`. Concrete classes set `CLIENT_ID_PREFIX: ClassVar[str]`.
  - `Base` is at `beyo_manager/models/base/base.py`.
  - App package root is `beyo_manager/`.
  - `upholstery_inventory_history_records` table is out of scope. The `latest_projection_history_id` column on `upholstery_inventory` is a plain `String(64) nullable` with **no FK constraint** (FK added in a future migration when that table is introduced).

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: Layer map and hard dependency rules.
- `backend/architecture/03_models.md`: Model contract — `Mapped`/`mapped_column`, `IdentityMixin`, enum pattern, index rules, `lazy="raise"`, `updated_at`.
- `backend/architecture/08_domain.md`: Domain layer — enums live in `domain/<domain>/enums.py`.
- `backend/architecture/21_naming_conventions.md`: Naming rules for tables, columns, constraints, indexes.
- `backend/architecture/30_migrations.md`: Migration rules — autogenerate only, `use_alter` for circular FKs.
- `backend/architecture/40_identity.md`: `IdentityMixin`, `CLIENT_ID_PREFIX`, prefix registry rules.

### Local extensions loaded

- `backend/architecture/40_identity_local.md`: Check for app-specific prefix additions before writing models.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`03_models.md`, `08_domain.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Permitted (relational reads — understanding what exists):
- Reading `models/base/identity.py` for `IdentityMixin` usage pattern
- Reading `models/base/base.py` for `Base` import path
- Reading `models/__init__.py` to see current imports and append new ones
- Reading existing table files to verify FK target column names and types

Prohibited (pattern reads — contracts already cover these):
- Reading another model table file to understand `Mapped`/`mapped_column` syntax
- Reading another domain `enums.py` to understand `class X(enum.Enum)` structure

---

## Critical architectural rules before coding

### Rule 1 — Enum placement

All enums are defined in `domain/<domain>/enums.py`. Models import from there. Never define enums inside model files.

```python
# domain/items/enums.py
import enum

class ItemStateEnum(enum.Enum):
    PENDING = "pending"
    STALL   = "stall"
    FIXING  = "fixing"
    READY   = "ready"
```

```python
# models/tables/items/item.py
from beyo_manager.domain.items.enums import ItemStateEnum
from sqlalchemy import Enum as SAEnum
...
state: Mapped[ItemStateEnum] = mapped_column(
    SAEnum(ItemStateEnum, name="item_state_enum", create_type=True),
    nullable=False,
    default=ItemStateEnum.PENDING,
    index=True,
)
```

### Rule 2 — Import isolation (no circular Python imports)

Circular FK references in SQLAlchemy are broken with `use_alter=True` on the FK that creates the back-reference. This tells SQLAlchemy/Alembic to emit the FK as a separate `ALTER TABLE` after both tables are created.

```python
# customers.py — FK to customer_history_records creates a cycle
latest_history_record_id: Mapped[str | None] = mapped_column(
    String(64),
    ForeignKey(
        "customer_history_records.client_id",
        use_alter=True,
        name="fk_customers_latest_history_record_id",
    ),
    nullable=True,
    index=True,
)
```

The `customer_history_records` table must still be **imported after** `customers` in `models/__init__.py`. The `use_alter=True` flag controls DDL ordering only.

### Rule 3 — Relationship loading

All relationships use `lazy="raise"`. Never use `lazy="select"`.

```python
history_records: Mapped[list["CustomerHistoryRecord"]] = relationship(
    "CustomerHistoryRecord", back_populates="customer", lazy="raise"
)
```

### Rule 4 — FK column type

All FK columns are `String(64)` and reference `<table>.client_id`. Keep semantic column names.

### Rule 5 — Timestamps

All `DateTime` columns use `DateTime(timezone=True)`. Never store naive datetimes. Use `default=lambda: datetime.now(timezone.utc)` and `onupdate=lambda: datetime.now(timezone.utc)` for `updated_at`.

### Rule 6 — RESTRICT delete behavior

All FK constraints on lineage/history/bridge tables use `ondelete="RESTRICT"` to prevent cascade deletes.

```python
task_id: Mapped[str] = mapped_column(
    String(64),
    ForeignKey("tasks.client_id", ondelete="RESTRICT"),
    nullable=False,
    index=True,
)
```

### Rule 7 — Soft-delete consistency

Tables with soft-delete carry: `is_deleted: bool (not null, default false)`, `deleted_at: DateTime nullable`, `deleted_by_id: String(64) FK nullable`.

### Rule 8 — Index naming

`ix_{table}_{columns}` — e.g. `ix_items_workspace_id_state`. Declare composite indexes in `__table_args__`.

### Rule 9 — Unique constraint naming

`uq_{table}_{columns}` — e.g. `uq_user_work_profiles_user_workspace`.

### Rule 10 — Partial unique indexes

Partial unique indexes (e.g. `WHERE removed_at IS NULL`) are PostgreSQL-specific and **cannot be expressed via `UniqueConstraint`**. They must use `Index(..., postgresql_where=...)`.

```python
from sqlalchemy import Index
__table_args__ = (
    Index(
        "ix_user_shift_state_records_active",
        "user_id", "workspace_id",
        unique=True,
        postgresql_where=text("exited_at IS NULL"),
    ),
)
```

Import `text` from `sqlalchemy`.

---

## Circular FK pairs — resolution table

| Table A | Column | References | Resolution |
|---|---|---|---|
| `customers` | `latest_history_record_id` | `customer_history_records.client_id` | `use_alter=True, name="fk_customers_latest_history_record_id"` |
| `tasks` | `latest_history_record_id` | `task_history_records.client_id` | `use_alter=True, name="fk_tasks_latest_history_record_id"` |
| `tasks` | `latest_event_id` | `task_events.client_id` | `use_alter=True, name="fk_tasks_latest_event_id"` |
| `task_steps` | `latest_state_record_id` | `step_state_records.client_id` | `use_alter=True, name="fk_task_steps_latest_state_record_id"` |
| `item_upholsteries` | `active_requirement_id` | `item_upholstery_requirements.client_id` | `use_alter=True, name="fk_item_upholsteries_active_requirement_id"` |
| `upholstery_inventory` | `latest_projection_history_id` | *(deferred table)* | Plain `String(64) nullable`, **no FK constraint** |

---

## New prefix registry entries

Register these prefixes. Verify no collision with existing prefixes in `40_identity_local.md` before writing.

| Class | Table | Prefix |
|---|---|---|
| `UserWorkProfile` | `user_work_profiles` | `uwp` |
| `UserShiftStateRecord` | `user_shift_state_records` | `uss` |
| `WorkingSection` | `working_sections` | `wsec` |
| `WorkingSectionMembership` | `working_section_memberships` | `wsme` |
| `WorkingSectionDependency` | `working_section_dependencies` | `wsd` |
| `WorkingSectionItemCategory` | `working_section_item_categories` | `wsic` |
| `WorkingSectionSupportedIssueType` | `working_section_supported_issue_types` | `wsit` |
| `Customer` | `customers` | `cus` |
| `CustomerHistoryRecord` | `customer_history_records` | `chr` |
| `IssueType` | `issue_types` | `ist` |
| `IssueSeverity` | `issue_severities` | `iss` |
| `IssueCategoryConfig` | `issue_category_configs` | `icc` |
| `ItemCategory` | `item_categories` | `itc` |
| `Item` | `items` | `itm` |
| `ItemIssue` | `item_issues` | `iti` |
| `ItemUpholstery` | `item_upholsteries` | `iup` |
| `ItemUpholsteryRequirement` | `item_upholstery_requirements` | `iur` |
| `Upholstery` | `upholsteries` | `uph` |
| `UpholsteryInventory` | `upholstery_inventory` | `uin` |
| `UpholsteryInventoryThresholdPolicy` | `upholstery_inventory_threshold_policies` | `utp` |
| `StaticCost` | `static_costs` | `scst` |
| `Task` | `tasks` | `tsk` |
| `TaskHistoryRecord` | `task_history_records` | `thr` |
| `TaskEvent` | `task_events` | `tev` |
| `TaskNote` | `task_notes` | `tno` |
| `TaskItem` | `task_items` | `tim` |
| `TaskStep` | `task_steps` | `tsp` |
| `TaskStepDependency` | `task_step_dependencies` | `tsd` |
| `StepStateRecord` | `step_state_records` | `ssr` |
| `TaskStepAssignmentRecord` | `task_step_assignment_records` | `tsar` |

> Note: The intention file uses prefix `ws_sec` for `working_sections`. This violates the naming rule (no underscores in prefixes). Use `wsec` instead.
> Note: The intention file uses prefix `wsica` for `working_section_supported_issue_types`. Changed to `wsit` to avoid confusion with `wsic`.
> Note: The intention file uses prefix `wsm` for `working_section_memberships`. This collides with the bootstrap app's `workspace_membership` table which already owns `wsm`. Changed to `wsme`.

---

## Implementation plan

### Step 1 — Create domain enum files (no models yet)

Create these files with their enum classes. Models in later steps import from here.

---

#### `beyo_manager/domain/users/enums.py`

```python
import enum

class UserShiftStateEnum(enum.Enum):
    STARTED_SHIFT = "started_shift"
    WORKING       = "working"
    IN_PAUSE      = "in_pause"
    ENDED_SHIFT   = "ended_shift"
```

---

#### `beyo_manager/domain/working_sections/enums.py`

```python
# No enums needed for base working section tables in this phase.
# File must exist as an empty module placeholder.
```

---

#### `beyo_manager/domain/customers/enums.py`

```python
import enum

class CustomerTypeEnum(enum.Enum):
    PERSON  = "person"
    COMPANY = "company"
    UNKNOWN = "unknown"

class CustomerStatusEnum(enum.Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"

class CustomerHistoryChangeTypeEnum(enum.Enum):
    CREATED         = "created"
    PROFILE_UPDATED = "profile_updated"
    CONTACT_UPDATED = "contact_updated"
    ADDRESS_UPDATED = "address_updated"
    STATUS_UPDATED  = "status_updated"
    SOFT_DELETED    = "soft_deleted"
    RESTORED        = "restored"
    MERGED          = "merged"
    REDACTED        = "redacted"
    ANONYMIZED      = "anonymized"
    CORRECTION      = "correction"
    RETRACTION      = "retraction"
```

---

#### `beyo_manager/domain/issue_types/enums.py`

```python
import enum

class IssueSourceEnum(enum.Enum):
    INTERNAL_INSPECTION = "internal_inspection"
    CUSTOMER            = "customer"
    SUPPLIER            = "supplier"
    IMPORTED            = "imported"
```

---

#### `beyo_manager/domain/items/enums.py`

```python
import enum

class ItemStateEnum(enum.Enum):
    PENDING = "pending"
    STALL   = "stall"
    FIXING  = "fixing"
    READY   = "ready"

class ItemCurrencyEnum(enum.Enum):
    SWEDISH_KRONA = "swedish_krona"
    DANISH_KRONA  = "danish_krona"
    EURO          = "euro"

class ItemMajorCategoryEnum(enum.Enum):
    WOOD = "wood"
    SEAT = "seat"

class ItemIssueStateEnum(enum.Enum):
    PENDING  = "pending"
    FIXING   = "fixing"
    BLOCKED  = "blocked"
    DEFERRED = "deferred"
    SKIPPED  = "skipped"
    RESOLVED = "resolved"

class ItemUpholsterySourceEnum(enum.Enum):
    INTERNAL = "internal"
    CUSTOMER = "customer"

class ItemUpholsteryRequirementSourceEnum(enum.Enum):
    INVENTORY = "inventory"
    SURPLUS   = "surplus"

class ItemUpholsteryRequirementStateEnum(enum.Enum):
    AVAILABLE      = "available"
    NEEDS_ORDERING = "needs_ordering"
    ORDERED        = "ordered"
    IN_USE         = "in_use"
    COMPLETED      = "completed"
    FAILED         = "failed"
```

---

#### `beyo_manager/domain/upholstery/enums.py`

```python
import enum

class UpholsteryCurrencyEnum(enum.Enum):
    SWEDISH_KRONA = "swedish_krona"
    DANISH_KRONA  = "danish_krona"
    EURO          = "euro"

class UpholsteryInventoryConditionEnum(enum.Enum):
    AVAILABLE   = "available"
    LOW_STOCK   = "low_stock"
    OUT_OF_STOCK = "out_of_stock"

class ThresholdPolicyScopeEnum(enum.Enum):
    WORKSPACE_DEFAULT = "workspace_default"
    UPHOLSTERY        = "upholstery"

class SourcingEscalationPolicyEnum(enum.Enum):
    NONE                    = "none"
    RECOMMEND_REORDER       = "recommend_reorder"
    ESCALATE_TO_PROCUREMENT = "escalate_to_procurement"

class InventoryWarningTierEnum(enum.Enum):
    NORMAL              = "normal"
    LOW_STOCK_WARNING   = "low_stock_warning"
    URGENT_REORDER      = "urgent_reorder"
```

---

#### `beyo_manager/domain/static_costs/enums.py`

```python
import enum

class StaticCostCurrencyEnum(enum.Enum):
    SWEDISH_KRONA = "swedish_krona"
    DANISH_KRONA  = "danish_krona"
    EURO          = "euro"
```

---

#### `beyo_manager/domain/tasks/enums.py`

```python
import enum

class TaskTypeEnum(enum.Enum):
    RETURN     = "return"
    PRE_ORDER  = "pre_order"
    INTERNAL   = "internal"

class TaskPriorityEnum(enum.Enum):
    LOW    = "low"
    NORMAL = "normal"
    HIGH   = "high"
    URGENT = "urgent"

class TaskStateEnum(enum.Enum):
    PENDING   = "pending"
    ASSIGNED  = "assigned"
    WORKING   = "working"
    STALLED   = "stalled"
    READY     = "ready"
    RESOLVED  = "resolved"
    FAILED    = "failed"
    CANCELLED = "cancelled"

class TaskReturnSourceEnum(enum.Enum):
    AFTER_PURCHASE  = "after_purchase"
    BEFORE_PURCHASE = "before_purchase"
    STORE_RETURN    = "store_return"

class TaskItemLocationEnum(enum.Enum):
    STORE    = "store"
    CUSTOMER = "customer"

class TaskReturnMethodEnum(enum.Enum):
    DROP_OFF_BY_CUSTOMER = "drop_off_by_customer"
    PICKUP               = "pickup"

class TaskFulfillmentMethodEnum(enum.Enum):
    PICKUP_AT_STORE = "pickup_at_store"
    DELIVERY        = "delivery"

class TaskNoteTypeEnum(enum.Enum):
    USER_NOTE       = "user_note"
    SYSTEM_NOTE     = "system_note"
    CORRECTION_NOTE = "correction_note"
    RETRACTION_NOTE = "retraction_note"

class TaskItemRoleEnum(enum.Enum):
    PRIMARY = "primary"
    RELATED = "related"

class TaskEventTypeEnum(enum.Enum):
    TASK_CREATED            = "task_created"
    TASK_STATE_CHANGED      = "task_state_changed"
    TASK_STEP_STATE_CHANGED = "task_step_state_changed"
    TASK_ASSIGNMENT_CHANGED = "task_assignment_changed"
    TASK_RESOLVED           = "task_resolved"

class TaskDomainEventLifecycleStateEnum(enum.Enum):
    RECORDED    = "recorded"
    SUPERSEDED  = "superseded"
    COMPENSATED = "compensated"
    IGNORED     = "ignored"

class TaskEventErrorCodeEnum(enum.Enum):
    VALIDATION_FAILED      = "validation_failed"
    ORCHESTRATION_CONFLICT = "orchestration_conflict"
    DEPENDENCY_BLOCKED     = "dependency_blocked"
    UNKNOWN                = "unknown"
```

---

#### `beyo_manager/domain/task_steps/enums.py`

```python
import enum

class TaskStepStateEnum(enum.Enum):
    PENDING     = "pending"
    WORKING     = "working"
    PAUSED      = "paused"
    ENDED_SHIFT = "ended_shift"
    BLOCKED     = "blocked"
    COMPLETED   = "completed"
    SKIPPED     = "skipped"
    FAILED      = "failed"
    CANCELLED   = "cancelled"

class TaskStepReadinessStatusEnum(enum.Enum):
    BLOCKED = "blocked"
    PARTIAL = "partial"
    READY   = "ready"

class StepEventReasonEnum(enum.Enum):
    WAITING_FOR_UPHOLSTERY  = "waiting_for_upholstery"
    PAUSE_LUNCH_BREAK       = "pause_lunch_break"
    PAUSE_COFFEE_BREAK      = "pause_coffee_break"
    PAUSE_ENDED_SHIFT       = "pause_ended_shift"
    PAUSE_MEETING           = "pause_meeting"
    PAUSE_OTHER_TASK_PRIORITY = "pause_other_task_priority"

class StepStateRecordAccuracyMeasuredByEnum(enum.Enum):
    USER = "user"
    AI   = "ai"
```

---

### Step 2 — Create aggregate metrics base mixins

**File:** `beyo_manager/models/base/aggregate_metrics.py`

These are column-only mixins (no `declared_attr`, no FK). They may be used by `task_steps`. Columns are defined here so they can be composed via multiple inheritance.

```python
from datetime import datetime, timezone
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column


class AggregateMetricsTimeMixin:
    total_working_seconds:      Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pause_seconds:        Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_ended_shift_seconds:  Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AggregateMetricsCountsMixin:
    total_working_count:     Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pause_count:       Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_ended_shift_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AggregateMetricsTotalsMixin:
    total_issues_count:          Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_issues_resolved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AggregateMetricsCostMixin:
    total_cost_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

> `task_steps` uses `AggregateMetricsTimeMixin`, `AggregateMetricsCountsMixin`, `AggregateMetricsTotalsMixin`, and `AggregateMetricsCostMixin`.
> `tasks` does **not** use these mixins — its projection columns (`recorded_time_marked_wrong`, etc.) are inline per the intention file column list.

---

### Step 3 — Create model table files (follow this exact order)

#### 3.1 User domain extensions

**`beyo_manager/models/tables/users/user_work_profile.py`**

```
Class:       UserWorkProfile
Table:       user_work_profiles
Prefix:      uwp
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `user_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `salary_per_hour_before_tax`: `Numeric(12, 4)`, nullable
- `salary_per_hour_after_tax`: `Numeric(12, 4)`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

> Use `Numeric` from `sqlalchemy`. **Never `Float` for money fields.**

`__table_args__`:
```python
(
    UniqueConstraint("user_id", "workspace_id", name="uq_user_work_profiles_user_workspace"),
    CheckConstraint("salary_per_hour_before_tax IS NULL OR salary_per_hour_before_tax >= 0", name="ck_user_work_profiles_salary_before_tax"),
    CheckConstraint("salary_per_hour_after_tax IS NULL OR salary_per_hour_after_tax >= 0", name="ck_user_work_profiles_salary_after_tax"),
    Index("ix_user_work_profiles_workspace_user", "workspace_id", "user_id"),
)
```

Relationships:
- None required in this phase.

---

**`beyo_manager/models/tables/users/user_shift_state_record.py`**

```
Class:       UserShiftStateRecord
Table:       user_shift_state_records
Prefix:      uss
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.users.enums import UserShiftStateEnum
```

Columns:
- `user_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `state`: `SAEnum(UserShiftStateEnum, name="user_shift_state_enum", create_type=True)`, not null
- `entered_at`: `DateTime(timezone=True)`, not null
- `exited_at`: `DateTime(timezone=True)`, nullable
- `changed_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    CheckConstraint("exited_at IS NULL OR exited_at >= entered_at", name="ck_user_shift_state_records_exited_after_entered"),
    Index("ix_user_shift_state_records_user_workspace_entered", "user_id", "workspace_id", "entered_at"),
    Index("ix_user_shift_state_records_user_workspace_exited", "user_id", "workspace_id", "exited_at"),
    Index(
        "uix_user_shift_state_records_active",
        "user_id", "workspace_id",
        unique=True,
        postgresql_where=text("exited_at IS NULL"),
    ),
)
```

> Import `text` from `sqlalchemy` for the partial index `postgresql_where`.

---

#### 3.2 Working sections domain

Create folder: `models/tables/working_sections/` with `__init__.py`.
Create folder: `domain/working_sections/` with `__init__.py` and `enums.py` (already defined in Step 1).

**`beyo_manager/models/tables/working_sections/working_section.py`**

```
Class:       WorkingSection
Table:       working_sections
Prefix:      wsec
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `name`: `String(255)`, not null
- `image`: `String(512)`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "name", name="uq_working_sections_workspace_name"),
)
```

Relationships: none in this phase.

---

**`beyo_manager/models/tables/working_sections/working_section_membership.py`**

```
Class:       WorkingSectionMembership
Table:       working_section_memberships
Prefix:      wsme
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `working_section_id`: `String(64)`, `FK("working_sections.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `user_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `assigned_at`: `DateTime(timezone=True)`, not null
- `assigned_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, not null
- `removed_at`: `DateTime(timezone=True)`, nullable
- `removed_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_working_section_memberships_user_removed", "user_id", "removed_at"),
    Index("ix_working_section_memberships_section_removed", "working_section_id", "removed_at"),
    Index(
        "uix_working_section_memberships_active",
        "workspace_id", "working_section_id", "user_id",
        unique=True,
        postgresql_where=text("removed_at IS NULL"),
    ),
)
```

---

**`beyo_manager/models/tables/working_sections/working_section_dependency.py`**

```
Class:       WorkingSectionDependency
Table:       working_section_dependencies
Prefix:      wsd
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `dependent_section_id`: `String(64)`, `FK("working_sections.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `prerequisite_section_id`: `String(64)`, `FK("working_sections.client_id", ondelete="RESTRICT")`, not null, `index=True`

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "dependent_section_id", "prerequisite_section_id", name="uq_working_section_dependencies_unique_edge"),
    CheckConstraint("dependent_section_id != prerequisite_section_id", name="ck_working_section_dependencies_no_self_ref"),
)
```

---

#### 3.3 Issue type registry domain

Create folder: `models/tables/issue_types/` with `__init__.py`.
Create folder: `domain/issue_types/` with `__init__.py` and `enums.py` (already defined).

**`beyo_manager/models/tables/issue_types/issue_type.py`**

```
Class:       IssueType
Table:       issue_types
Prefix:      ist
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.issue_types.enums import IssueSourceEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `name`: `String(255)`, not null
- `source`: `SAEnum(IssueSourceEnum, name="issue_source_enum", create_type=True)`, not null, `index=True`
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "name", name="uq_issue_types_workspace_name"),
)
```

---

**`beyo_manager/models/tables/issue_types/issue_severity.py`**

```
Class:       IssueSeverity
Table:       issue_severities
Prefix:      iss
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `name`: `String(128)`, not null
- `time_multiplier`: `Numeric(8, 4)`, not null
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "name", name="uq_issue_severities_workspace_name"),
    CheckConstraint("time_multiplier >= 0", name="ck_issue_severities_time_multiplier_positive"),
)
```

---

#### 3.4 Item category (must precede item, working section bridges, and issue_category_config)

Create folder: `models/tables/items/` with `__init__.py`.
Create folder: `domain/items/` with `__init__.py` and `enums.py` (already defined).

**`beyo_manager/models/tables/items/item_category.py`**

```
Class:       ItemCategory
Table:       item_categories
Prefix:      itc
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `name`: `String(255)`, not null
- `major_category`: `SAEnum(ItemMajorCategoryEnum, name="item_major_category_enum", create_type=True)`, not null, `index=True`
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "name", name="uq_item_categories_workspace_name"),
    Index("ix_item_categories_workspace_major_category", "workspace_id", "major_category"),
)
```

---

#### 3.5 Working section bridge tables (depend on item_categories and issue_types)

**`beyo_manager/models/tables/working_sections/working_section_item_category.py`**

```
Class:       WorkingSectionItemCategory
Table:       working_section_item_categories
Prefix:      wsic
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `working_section_id`: `String(64)`, `FK("working_sections.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `item_category_id`: `String(64)`, `FK("item_categories.client_id", ondelete="RESTRICT")`, not null, `index=True`

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "working_section_id", "item_category_id", name="uq_ws_item_categories_unique"),
)
```

---

**`beyo_manager/models/tables/working_sections/working_section_supported_issue_type.py`**

```
Class:       WorkingSectionSupportedIssueType
Table:       working_section_supported_issue_types
Prefix:      wsit
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `working_section_id`: `String(64)`, `FK("working_sections.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `issue_type_id`: `String(64)`, `FK("issue_types.client_id", ondelete="RESTRICT")`, not null, `index=True`

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "working_section_id", "issue_type_id", name="uq_ws_supported_issue_types_unique"),
)
```

---

#### 3.6 Issue category config (depends on issue_types and item_categories)

**`beyo_manager/models/tables/issue_types/issue_category_config.py`**

```
Class:       IssueCategoryConfig
Table:       issue_category_configs
Prefix:      icc
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `issue_type_id`: `String(64)`, `FK("issue_types.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `item_category_id`: `String(64)`, `FK("item_categories.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `base_time_seconds`: `Integer`, not null
- `effective_from`: `DateTime(timezone=True)`, nullable
- `effective_to`: `DateTime(timezone=True)`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "issue_type_id", "item_category_id", "effective_from", name="uq_issue_category_configs_unique"),
    CheckConstraint("base_time_seconds >= 0", name="ck_issue_category_configs_base_time_positive"),
    CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from", name="ck_issue_category_configs_effective_window"),
)
```

---

#### 3.7 Upholstery registry (no dependency on new tables)

Create folder: `models/tables/upholstery/` with `__init__.py`.
Create folder: `domain/upholstery/` with `__init__.py` and `enums.py` (already defined).

**`beyo_manager/models/tables/upholstery/upholstery.py`**

```
Class:       Upholstery
Table:       upholsteries
Prefix:      uph
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `name`: `String(255)`, not null
- `code`: `String(128)`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "name", name="uq_upholsteries_workspace_name"),
    Index(
        "uix_upholsteries_workspace_code",
        "workspace_id", "code",
        unique=True,
        postgresql_where=text("code IS NOT NULL"),
    ),
)
```

---

#### 3.8 Item (depends on item_categories)

**`beyo_manager/models/tables/items/item.py`**

```
Class:       Item
Table:       items
Prefix:      itm
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.items.enums import ItemStateEnum, ItemCurrencyEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `article_number`: `String(128)`, nullable, `index=True`
- `sku`: `String(128)`, nullable, `index=True`
- `state`: `SAEnum(ItemStateEnum, name="item_state_enum", create_type=True)`, not null, `index=True`, `default=ItemStateEnum.PENDING`
- `item_category_id`: `String(64)`, `FK("item_categories.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `quantity`: `Integer`, not null, `default=1`
- `designer`: `String(255)`, nullable
- `height_in_cm`: `Integer`, nullable
- `width_in_cm`: `Integer`, nullable
- `depth_in_cm`: `Integer`, nullable
- `item_value_minor`: `Integer`, nullable
- `item_cost_minor`: `Integer`, nullable
- `item_currency`: `SAEnum(ItemCurrencyEnum, name="item_currency_enum", create_type=True)`, nullable
- `item_position`: `String(255)`, nullable
- `external_id`: `String(255)`, nullable
- `external_url`: `String(1024)`, nullable
- `external_source`: `String(128)`, nullable
- `external_order_id`: `String(255)`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_items_workspace_state", "workspace_id", "state"),
    Index(
        "uix_items_workspace_article_number",
        "workspace_id", "article_number",
        unique=True,
        postgresql_where=text("article_number IS NOT NULL"),
    ),
    Index(
        "uix_items_workspace_sku",
        "workspace_id", "sku",
        unique=True,
        postgresql_where=text("sku IS NOT NULL"),
    ),
)
```

---

#### 3.9 Item issues (depends on items, issue_types, issue_severities)

**`beyo_manager/models/tables/items/item_issue.py`**

```
Class:       ItemIssue
Table:       item_issues
Prefix:      iti
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.items.enums import ItemIssueStateEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `item_id`: `String(64)`, `FK("items.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `issue_type_id`: `String(64)`, `FK("issue_types.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `issue_severity_id`: `String(64)`, `FK("issue_severities.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `state`: `SAEnum(ItemIssueStateEnum, name="item_issue_state_enum", create_type=True)`, not null, `index=True`, `default=ItemIssueStateEnum.PENDING`
- `base_time_seconds`: `Integer`, nullable
- `time_multiplier`: `Numeric(8, 4)`, nullable
- `issue_name_snapshot`: `String(255)`, nullable
- `severity_name_snapshot`: `String(255)`, nullable
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `started_at`: `DateTime(timezone=True)`, nullable
- `resolved_at`: `DateTime(timezone=True)`, nullable
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_item_issues_workspace_state", "workspace_id", "state"),
    Index("ix_item_issues_workspace_item_state", "workspace_id", "item_id", "state"),
    CheckConstraint("base_time_seconds IS NULL OR base_time_seconds >= 0", name="ck_item_issues_base_time_positive"),
    CheckConstraint("time_multiplier IS NULL OR time_multiplier >= 0", name="ck_item_issues_time_multiplier_positive"),
)
```

---

#### 3.10 Item upholstery (depends on items, upholsteries; circular FK to item_upholstery_requirements)

**`beyo_manager/models/tables/items/item_upholstery.py`**

```
Class:       ItemUpholstery
Table:       item_upholsteries
Prefix:      iup
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `item_id`: `String(64)`, `FK("items.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `upholstery_id`: `String(64)`, `FK("upholsteries.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `name`: `String(255)`, nullable
- `code`: `String(128)`, nullable
- `amount_meters`: `Numeric(12, 3)`, nullable
- `source`: `SAEnum(ItemUpholsterySourceEnum, name="item_upholstery_source_enum", create_type=True)`, not null, `index=True`
- `time_to_fix_in_seconds`: `Integer`, nullable
- `active_requirement_id`: `String(64)`, `FK("item_upholstery_requirements.client_id", use_alter=True, name="fk_item_upholsteries_active_requirement_id", ondelete="RESTRICT")`, nullable, `index=True`
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_item_upholsteries_workspace_item", "workspace_id", "item_id"),
    CheckConstraint("amount_meters IS NULL OR amount_meters >= 0", name="ck_item_upholsteries_amount_positive"),
    CheckConstraint("time_to_fix_in_seconds IS NULL OR time_to_fix_in_seconds >= 0", name="ck_item_upholsteries_time_positive"),
)
```

---

#### 3.11 Item upholstery requirements (depends on item_upholsteries)

**`beyo_manager/models/tables/items/item_upholstery_requirement.py`**

```
Class:       ItemUpholsteryRequirement
Table:       item_upholstery_requirements
Prefix:      iur
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.items.enums import ItemUpholsteryRequirementSourceEnum, ItemUpholsteryRequirementStateEnum, ItemCurrencyEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `item_upholstery_id`: `String(64)`, `FK("item_upholsteries.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `upholstery_inventory_id`: `String(64)`, nullable  *(plain String, no FK — inventory table deferred)*
- `amount_meters`: `Numeric(12, 3)`, not null
- `value_minor`: `Integer`, nullable
- `currency`: `SAEnum(ItemCurrencyEnum, name="item_currency_enum", create_type=False)`, nullable  *(create_type=False — enum type already created by items.item)*
- `source`: `SAEnum(ItemUpholsteryRequirementSourceEnum, name="item_upholstery_requirement_source_enum", create_type=True)`, not null, `index=True`
- `state`: `SAEnum(ItemUpholsteryRequirementStateEnum, name="item_upholstery_requirement_state_enum", create_type=True)`, not null, `index=True`, `default=ItemUpholsteryRequirementStateEnum.AVAILABLE`
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `ordered_at`: `DateTime(timezone=True)`, nullable
- `in_use_at`: `DateTime(timezone=True)`, nullable
- `completed_at`: `DateTime(timezone=True)`, nullable
- `failed_at`: `DateTime(timezone=True)`, nullable
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_item_upholstery_requirements_workspace_upholstery_state", "workspace_id", "item_upholstery_id", "state"),
    CheckConstraint("amount_meters >= 0", name="ck_item_upholstery_requirements_amount_positive"),
    CheckConstraint("value_minor IS NULL OR value_minor >= 0", name="ck_item_upholstery_requirements_value_positive"),
)
```

> **Important:** `item_currency_enum` Postgres type is created by `item.py` (create_type=True there). In `item_upholstery_requirement.py` use `create_type=False` to reuse the existing type. This applies to every other file that reuses an enum type already created elsewhere.

---

#### 3.12 Upholstery inventory (depends on upholsteries; latest_projection_history_id is plain String)

**`beyo_manager/models/tables/upholstery/upholstery_inventory.py`**

```
Class:       UpholsteryInventory
Table:       upholstery_inventory
Prefix:      uin
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum, UpholsteryCurrencyEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `upholstery_id`: `String(64)`, `FK("upholsteries.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `minimum_to_have`: `Integer`, nullable
- `maximum_to_have`: `Integer`, nullable
- `projected_inventory_value_minor`: `Integer`, nullable
- `currency`: `SAEnum(UpholsteryCurrencyEnum, name="upholstery_currency_enum", create_type=True)`, nullable
- `planning_position`: `String(255)`, nullable
- `inventory_condition`: `SAEnum(UpholsteryInventoryConditionEnum, name="upholstery_inventory_condition_enum", create_type=True)`, not null, `index=True`, `default=UpholsteryInventoryConditionEnum.AVAILABLE`
- `current_stored_amount_meters`: `Numeric(14, 3)`, nullable
- `current_amount_in_use_meters`: `Numeric(14, 3)`, nullable
- `current_amount_in_need_meters`: `Numeric(14, 3)`, nullable
- `current_amount_ordered_meters`: `Numeric(14, 3)`, nullable
- `total_upholstery_used_meters`: `Numeric(14, 3)`, nullable
- `total_upholstery_used_inventory_meters`: `Numeric(14, 3)`, nullable
- `total_upholstery_used_surplus_meters`: `Numeric(14, 3)`, nullable
- `total_upholstery_surplus_meters`: `Numeric(14, 3)`, nullable
- `latest_projection_history_id`: `String(64)`, nullable  *(no FK — table deferred)*
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "upholstery_id", name="uq_upholstery_inventory_workspace_upholstery"),
    CheckConstraint("minimum_to_have IS NULL OR minimum_to_have >= 0", name="ck_upholstery_inventory_min_positive"),
    CheckConstraint("maximum_to_have IS NULL OR maximum_to_have >= 0", name="ck_upholstery_inventory_max_positive"),
    CheckConstraint("maximum_to_have IS NULL OR minimum_to_have IS NULL OR maximum_to_have >= minimum_to_have", name="ck_upholstery_inventory_max_gte_min"),
    CheckConstraint("projected_inventory_value_minor IS NULL OR projected_inventory_value_minor >= 0", name="ck_upholstery_inventory_value_positive"),
)
```

---

**`beyo_manager/models/tables/upholstery/upholstery_inventory_threshold_policy.py`**

```
Class:       UpholsteryInventoryThresholdPolicy
Table:       upholstery_inventory_threshold_policies
Prefix:      utp
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.upholstery.enums import ThresholdPolicyScopeEnum, SourcingEscalationPolicyEnum, InventoryWarningTierEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `scope`: `SAEnum(ThresholdPolicyScopeEnum, name="threshold_policy_scope_enum", create_type=True)`, not null, `index=True`
- `upholstery_id`: `String(64)`, `FK("upholsteries.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `low_stock_minimum_meters`: `Numeric(14, 3)`, nullable
- `low_stock_ratio`: `Numeric(8, 4)`, nullable
- `out_of_stock_epsilon_meters`: `Numeric(14, 3)`, nullable
- `escalation_policy`: `SAEnum(SourcingEscalationPolicyEnum, name="sourcing_escalation_policy_enum", create_type=True)`, nullable
- `warning_tier`: `SAEnum(InventoryWarningTierEnum, name="inventory_warning_tier_enum", create_type=True)`, nullable
- `effective_from`: `DateTime(timezone=True)`, nullable
- `effective_to`: `DateTime(timezone=True)`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "scope", "upholstery_id", "effective_from", name="uq_upholstery_inv_threshold_policies_unique"),
    CheckConstraint("low_stock_minimum_meters IS NULL OR low_stock_minimum_meters >= 0", name="ck_utp_low_stock_min_positive"),
    CheckConstraint("low_stock_ratio IS NULL OR (low_stock_ratio >= 0 AND low_stock_ratio <= 1)", name="ck_utp_low_stock_ratio_range"),
    CheckConstraint("out_of_stock_epsilon_meters IS NULL OR out_of_stock_epsilon_meters >= 0", name="ck_utp_epsilon_positive"),
    CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from", name="ck_utp_effective_window"),
    CheckConstraint("scope != 'upholstery' OR upholstery_id IS NOT NULL", name="ck_utp_upholstery_scope_requires_id"),
)
```

---

#### 3.13 Customers (circular FK to customer_history_records → use_alter)

Create folder: `models/tables/customers/` with `__init__.py`.
Create folder: `domain/customers/` with `__init__.py` and `enums.py` (already defined).

**`beyo_manager/models/tables/customers/customer.py`**

```
Class:       Customer
Table:       customers
Prefix:      cus
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.customers.enums import CustomerTypeEnum, CustomerStatusEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `display_name`: `String(255)`, not null
- `customer_type`: `SAEnum(CustomerTypeEnum, name="customer_type_enum", create_type=True)`, not null, `index=True`, `default=CustomerTypeEnum.UNKNOWN`
- `status`: `SAEnum(CustomerStatusEnum, name="customer_status_enum", create_type=True)`, not null, `index=True`, `default=CustomerStatusEnum.ACTIVE`
- `primary_phone_number`: `String(64)`, nullable
- `primary_email`: `String(255)`, nullable
- `primary_phone_number_normalized`: `String(64)`, nullable, `index=True`
- `primary_email_normalized`: `String(255)`, nullable, `index=True`
- `address`: `JSON`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `latest_history_record_id`: `String(64)`, `FK("customer_history_records.client_id", use_alter=True, name="fk_customers_latest_history_record_id", ondelete="RESTRICT")`, nullable, `index=True`
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_customers_workspace_display_name", "workspace_id", "display_name"),
    Index("ix_customers_workspace_phone", "workspace_id", "primary_phone_number"),
    Index("ix_customers_workspace_email", "workspace_id", "primary_email"),
    Index("ix_customers_workspace_phone_normalized", "workspace_id", "primary_phone_number_normalized"),
    Index("ix_customers_workspace_email_normalized", "workspace_id", "primary_email_normalized"),
)
```

---

**`beyo_manager/models/tables/customers/customer_history_record.py`**

```
Class:       CustomerHistoryRecord
Table:       customer_history_records
Prefix:      chr
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.customers.enums import CustomerHistoryChangeTypeEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `customer_id`: `String(64)`, `FK("customers.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `change_type`: `SAEnum(CustomerHistoryChangeTypeEnum, name="customer_history_change_type_enum", create_type=True)`, not null, `index=True`
- `occurred_at`: `DateTime(timezone=True)`, not null, `index=True`
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `payload`: `JSON`, nullable
- `change_summary`: `String(512)`, nullable
- `correlation_id`: `String(64)`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_customer_history_records_workspace_customer_occurred", "workspace_id", "customer_id", "occurred_at"),
    Index("ix_customer_history_records_workspace_customer_created", "workspace_id", "customer_id", "created_at"),
)
```

---

#### 3.14 Static costs

Create folder: `models/tables/static_costs/` with `__init__.py`.
Create folder: `domain/static_costs/` with `__init__.py` and `enums.py` (already defined).

**`beyo_manager/models/tables/static_costs/static_cost.py`**

```
Class:       StaticCost
Table:       static_costs
Prefix:      scst
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.static_costs.enums import StaticCostCurrencyEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `name`: `String(255)`, not null
- `description`: `String(1024)`, nullable
- `cost_minor`: `Integer`, not null
- `currency`: `SAEnum(StaticCostCurrencyEnum, name="static_cost_currency_enum", create_type=True)`, not null
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`: none required beyond what's implicit.

---

#### 3.15 Tasks (depends on customers; circular FKs to task_history_records and task_events)

Create folder: `models/tables/tasks/` with `__init__.py`.
Create folders: `domain/tasks/` and `domain/task_steps/` with `__init__.py` and `enums.py` (already defined).

**`beyo_manager/models/tables/tasks/task.py`**

```
Class:       Task
Table:       tasks
Prefix:      tsk
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.tasks.enums import (
    TaskTypeEnum, TaskPriorityEnum, TaskStateEnum,
    TaskReturnSourceEnum, TaskItemLocationEnum,
    TaskReturnMethodEnum, TaskFulfillmentMethodEnum,
)
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `task_scalar_id`: `Integer`, not null
- `task_type`: `SAEnum(TaskTypeEnum, name="task_type_enum", create_type=True)`, not null, `index=True`
- `priority`: `SAEnum(TaskPriorityEnum, name="task_priority_enum", create_type=True)`, not null, `default=TaskPriorityEnum.NORMAL`, `index=True`
- `state`: `SAEnum(TaskStateEnum, name="task_state_enum", create_type=True)`, not null, `index=True`, `default=TaskStateEnum.PENDING`
- `title`: `String(255)`, nullable
- `summary`: `String(1024)`, nullable
- `return_source`: `SAEnum(TaskReturnSourceEnum, name="task_return_source_enum", create_type=True)`, nullable
- `item_location`: `SAEnum(TaskItemLocationEnum, name="task_item_location_enum", create_type=True)`, nullable
- `additional_details`: `JSON`, nullable
- `ready_by_at`: `DateTime(timezone=True)`, nullable
- `scheduled_start_at`: `DateTime(timezone=True)`, nullable
- `scheduled_end_at`: `DateTime(timezone=True)`, nullable
- `return_method`: `SAEnum(TaskReturnMethodEnum, name="task_return_method_enum", create_type=True)`, nullable
- `fulfillment_method`: `SAEnum(TaskFulfillmentMethodEnum, name="task_fulfillment_method_enum", create_type=True)`, nullable
- `customer_id`: `String(64)`, `FK("customers.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `primary_phone_number`: `String(64)`, nullable
- `secondary_phone_number`: `String(64)`, nullable
- `primary_email`: `String(255)`, nullable
- `secondary_email`: `String(255)`, nullable
- `address`: `JSON`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `closed_at`: `DateTime(timezone=True)`, nullable
- `latest_history_record_id`: `String(64)`, `FK("task_history_records.client_id", use_alter=True, name="fk_tasks_latest_history_record_id", ondelete="RESTRICT")`, nullable, `index=True`
- `latest_event_id`: `String(64)`, `FK("task_events.client_id", use_alter=True, name="fk_tasks_latest_event_id", ondelete="RESTRICT")`, nullable, `index=True`
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

*Projection columns (inline — not from mixin):*
- `recorded_time_marked_wrong`: `Boolean`, not null, `default=False`
- `taken_from_average`: `Boolean`, not null, `default=False`

`__table_args__`:
```python
(
    UniqueConstraint("workspace_id", "task_scalar_id", name="uq_tasks_workspace_scalar_id"),
    Index("ix_tasks_workspace_state_scheduled_start", "workspace_id", "state", "scheduled_start_at"),
    CheckConstraint(
        "scheduled_end_at IS NULL OR scheduled_start_at IS NULL OR scheduled_end_at >= scheduled_start_at",
        name="ck_tasks_scheduled_end_after_start",
    ),
)
```

---

#### 3.16 Task history records (depends on tasks)

**`beyo_manager/models/tables/tasks/task_history_record.py`**

```
Class:       TaskHistoryRecord
Table:       task_history_records
Prefix:      thr
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `task_id`: `String(64)`, `FK("tasks.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `occurred_at`: `DateTime(timezone=True)`, not null, `index=True`
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `state_from`: `String(64)`, nullable
- `state_to`: `String(64)`, nullable
- `reason_code`: `String(128)`, nullable
- `reason_text`: `String(512)`, nullable
- `snapshot_payload`: `JSON`, nullable
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_task_history_records_workspace_task_occurred", "workspace_id", "task_id", "occurred_at"),
    Index("ix_task_history_records_workspace_task_created", "workspace_id", "task_id", "created_at"),
)
```

---

#### 3.17 Task events (depends on tasks)

**`beyo_manager/models/tables/tasks/task_event.py`**

```
Class:       TaskEvent
Table:       task_events
Prefix:      tev
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.tasks.enums import (
    TaskEventTypeEnum, TaskDomainEventLifecycleStateEnum, TaskEventErrorCodeEnum
)
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `task_id`: `String(64)`, `FK("tasks.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `event_type`: `SAEnum(TaskEventTypeEnum, name="task_event_type_enum", create_type=True)`, not null, `index=True`
- `event_lifecycle_state`: `SAEnum(TaskDomainEventLifecycleStateEnum, name="task_domain_event_lifecycle_state_enum", create_type=True)`, not null, `index=True`, `default=TaskDomainEventLifecycleStateEnum.RECORDED`
- `error_code`: `SAEnum(TaskEventErrorCodeEnum, name="task_event_error_code_enum", create_type=True)`, nullable, `index=True`
- `payload`: `JSON`, nullable
- `occurred_at`: `DateTime(timezone=True)`, not null, `index=True`
- `correlation_id`: `String(64)`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_task_events_workspace_task_occurred", "workspace_id", "task_id", "occurred_at"),
)
```

---

#### 3.18 Task notes (depends on tasks)

**`beyo_manager/models/tables/tasks/task_note.py`**

```
Class:       TaskNote
Table:       task_notes
Prefix:      tno
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.tasks.enums import TaskNoteTypeEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `task_id`: `String(64)`, `FK("tasks.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `note_type`: `SAEnum(TaskNoteTypeEnum, name="task_note_type_enum", create_type=True)`, not null
- `content`: `JSON`, not null
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_task_notes_workspace_task_created", "workspace_id", "task_id", "created_at"),
)
```

---

#### 3.19 Task items / bridge (depends on tasks and items)

**`beyo_manager/models/tables/tasks/task_item.py`**

```
Class:       TaskItem
Table:       task_items
Prefix:      tim
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `task_id`: `String(64)`, `FK("tasks.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `item_id`: `String(64)`, `FK("items.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `role`: `SAEnum(TaskItemRoleEnum, name="task_item_role_enum", create_type=True)`, not null
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `removed_at`: `DateTime(timezone=True)`, nullable
- `removed_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_task_items_workspace_item", "workspace_id", "item_id"),
    Index(
        "uix_task_items_active",
        "workspace_id", "task_id", "item_id",
        unique=True,
        postgresql_where=text("removed_at IS NULL"),
    ),
    Index(
        "uix_task_items_primary_active",
        "workspace_id", "task_id",
        unique=True,
        postgresql_where=text("role = 'primary' AND removed_at IS NULL"),
    ),
)
```

---

#### 3.20 Task steps (depends on tasks, working_sections; circular FK to step_state_records)

**`beyo_manager/models/tables/tasks/task_step.py`**

```
Class:       TaskStep
Table:       task_steps
Prefix:      tsp
Inherits:    IdentityMixin, AggregateMetricsTimeMixin, AggregateMetricsCountsMixin, AggregateMetricsTotalsMixin, AggregateMetricsCostMixin, Base
Imports enums: from beyo_manager.domain.task_steps.enums import TaskStepStateEnum, TaskStepReadinessStatusEnum
Imports mixins: from beyo_manager.models.base.aggregate_metrics import (
    AggregateMetricsTimeMixin, AggregateMetricsCountsMixin,
    AggregateMetricsTotalsMixin, AggregateMetricsCostMixin,
)
```

> Mixin inheritance order: `class TaskStep(IdentityMixin, AggregateMetricsTimeMixin, AggregateMetricsCountsMixin, AggregateMetricsTotalsMixin, AggregateMetricsCostMixin, Base):`

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `task_id`: `String(64)`, `FK("tasks.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `state`: `SAEnum(TaskStepStateEnum, name="task_step_state_enum", create_type=True)`, not null, `index=True`, `default=TaskStepStateEnum.PENDING`
- `readiness_status`: `SAEnum(TaskStepReadinessStatusEnum, name="task_step_readiness_status_enum", create_type=True)`, not null, `index=True`, `default=TaskStepReadinessStatusEnum.READY`
- `sequence_order`: `Integer`, nullable
- `working_section_id`: `String(64)`, `FK("working_sections.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `assigned_worker_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `total_dependencies`: `Integer`, not null, `default=0`
- `completed_dependencies`: `Integer`, not null, `default=0`
- `recorded_time_marked_wrong`: `Boolean`, not null, `default=False`
- `taken_from_average`: `Boolean`, not null, `default=False`
- `working_section_name_snapshot`: `String(255)`, nullable
- `assigned_worker_display_name_snapshot`: `String(255)`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `closed_at`: `DateTime(timezone=True)`, nullable
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `updated_at`: `DateTime(timezone=True)`, nullable, `onupdate=lambda: datetime.now(timezone.utc)`
- `updated_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `latest_state_record_id`: `String(64)`, `FK("step_state_records.client_id", use_alter=True, name="fk_task_steps_latest_state_record_id", ondelete="RESTRICT")`, nullable, `index=True`
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_task_steps_workspace_task_state", "workspace_id", "task_id", "state"),
    CheckConstraint("completed_dependencies >= 0", name="ck_task_steps_completed_deps_positive"),
    CheckConstraint("total_dependencies >= 0", name="ck_task_steps_total_deps_positive"),
    CheckConstraint("completed_dependencies <= total_dependencies", name="ck_task_steps_completed_lte_total"),
    CheckConstraint("total_pause_count >= 0", name="ck_task_steps_pause_count_positive"),
    CheckConstraint("total_ended_shift_count >= 0", name="ck_task_steps_ended_shift_count_positive"),
    CheckConstraint("total_pause_seconds >= 0", name="ck_task_steps_pause_seconds_positive"),
    CheckConstraint("total_ended_shift_seconds >= 0", name="ck_task_steps_ended_shift_seconds_positive"),
)
```

---

#### 3.21 Step state records (depends on task_steps)

**`beyo_manager/models/tables/tasks/step_state_record.py`**

```
Class:       StepStateRecord
Table:       step_state_records
Prefix:      ssr
Inherits:    IdentityMixin, Base
Imports enums: from beyo_manager.domain.task_steps.enums import (
    TaskStepStateEnum, StepEventReasonEnum, StepStateRecordAccuracyMeasuredByEnum
)
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `step_id`: `String(64)`, `FK("task_steps.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `state`: `SAEnum(TaskStepStateEnum, name="task_step_state_enum", create_type=False)`, not null, `index=True`  *(create_type=False — type already created by task_steps)*
- `reason`: `SAEnum(StepEventReasonEnum, name="step_event_reason_enum", create_type=True)`, nullable, `index=True`
- `description`: `String(1024)`, nullable
- `accuracy`: `Integer`, nullable
- `accuracy_measured_by`: `SAEnum(StepStateRecordAccuracyMeasuredByEnum, name="step_state_record_accuracy_measured_by_enum", create_type=True)`, nullable
- `taken_from_average`: `Boolean`, not null, `default=False`
- `entered_at`: `DateTime(timezone=True)`, not null
- `exited_at`: `DateTime(timezone=True)`, nullable
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `is_deleted`: `Boolean`, not null, `default=False`
- `deleted_at`: `DateTime(timezone=True)`, nullable
- `deleted_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index("ix_step_state_records_workspace_step_entered", "workspace_id", "step_id", "entered_at"),
    Index(
        "uix_step_state_records_active",
        "workspace_id", "step_id",
        unique=True,
        postgresql_where=text("exited_at IS NULL"),
    ),
    CheckConstraint("accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 100)", name="ck_step_state_records_accuracy_range"),
    CheckConstraint("exited_at IS NULL OR exited_at >= entered_at", name="ck_step_state_records_exited_after_entered"),
)
```

---

#### 3.22 Task step dependencies (depends on task_steps)

**`beyo_manager/models/tables/tasks/task_step_dependency.py`**

```
Class:       TaskStepDependency
Table:       task_step_dependencies
Prefix:      tsd
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `dependent_step_id`: `String(64)`, `FK("task_steps.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `prerequisite_step_id`: `String(64)`, `FK("task_steps.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `created_at`: `DateTime(timezone=True)`, not null, `default=lambda: datetime.now(timezone.utc)`
- `created_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `removed_at`: `DateTime(timezone=True)`, nullable
- `removed_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable

`__table_args__`:
```python
(
    Index(
        "uix_task_step_dependencies_active",
        "workspace_id", "dependent_step_id", "prerequisite_step_id",
        unique=True,
        postgresql_where=text("removed_at IS NULL"),
    ),
    CheckConstraint("dependent_step_id != prerequisite_step_id", name="ck_task_step_dependencies_no_self_ref"),
)
```

---

#### 3.23 Task step assignment records (depends on task_steps)

**`beyo_manager/models/tables/tasks/task_step_assignment_record.py`**

```
Class:       TaskStepAssignmentRecord
Table:       task_step_assignment_records
Prefix:      tsar
Inherits:    IdentityMixin, Base
Imports enums: none
```

Columns:
- `workspace_id`: `String(64)`, `FK("workspaces.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `step_id`: `String(64)`, `FK("task_steps.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `assigned_worker_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, not null, `index=True`
- `assigned_at`: `DateTime(timezone=True)`, not null
- `assigned_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable, `index=True`
- `removed_at`: `DateTime(timezone=True)`, nullable
- `removed_by_id`: `String(64)`, `FK("users.client_id", ondelete="RESTRICT")`, nullable
- `reason_code`: `String(128)`, nullable
- `reason_text`: `String(512)`, nullable

`__table_args__`:
```python
(
    Index("ix_task_step_assignment_records_workspace_step_assigned", "workspace_id", "step_id", "assigned_at"),
    Index(
        "uix_task_step_assignment_records_active",
        "workspace_id", "step_id",
        unique=True,
        postgresql_where=text("removed_at IS NULL"),
    ),
)
```

---

### Step 4 — Update `models/__init__.py`

Append imports in exactly this order after the existing lines. Do not reorder existing imports.

```python
# --- User domain extensions ---
from beyo_manager.models.tables.users import user_work_profile          # noqa: F401
from beyo_manager.models.tables.users import user_shift_state_record    # noqa: F401

# --- Working sections ---
from beyo_manager.models.tables.working_sections import working_section                          # noqa: F401
from beyo_manager.models.tables.working_sections import working_section_membership               # noqa: F401
from beyo_manager.models.tables.working_sections import working_section_dependency               # noqa: F401

# --- Issue type registry ---
from beyo_manager.models.tables.issue_types import issue_type      # noqa: F401
from beyo_manager.models.tables.issue_types import issue_severity  # noqa: F401

# --- Item categories (before working section bridges and items) ---
from beyo_manager.models.tables.items import item_category  # noqa: F401

# --- Working section bridge tables (depend on item_category and issue_type) ---
from beyo_manager.models.tables.working_sections import working_section_item_category         # noqa: F401
from beyo_manager.models.tables.working_sections import working_section_supported_issue_type  # noqa: F401

# --- Issue category config (depends on issue_type and item_category) ---
from beyo_manager.models.tables.issue_types import issue_category_config  # noqa: F401

# --- Upholstery registry ---
from beyo_manager.models.tables.upholstery import upholstery  # noqa: F401

# --- Items (depends on item_category) ---
from beyo_manager.models.tables.items import item  # noqa: F401

# --- Item issues (depends on item, issue_type, issue_severity) ---
from beyo_manager.models.tables.items import item_issue  # noqa: F401

# --- Item upholstery (depends on item, upholstery; use_alter FK to item_upholstery_requirement) ---
from beyo_manager.models.tables.items import item_upholstery  # noqa: F401

# --- Item upholstery requirements (depends on item_upholstery) ---
from beyo_manager.models.tables.items import item_upholstery_requirement  # noqa: F401

# --- Upholstery inventory (depends on upholstery) ---
from beyo_manager.models.tables.upholstery import upholstery_inventory                      # noqa: F401
from beyo_manager.models.tables.upholstery import upholstery_inventory_threshold_policy     # noqa: F401

# --- Customers (use_alter FK to customer_history_record) ---
from beyo_manager.models.tables.customers import customer  # noqa: F401

# --- Customer history records (depends on customer) ---
from beyo_manager.models.tables.customers import customer_history_record  # noqa: F401

# --- Static costs ---
from beyo_manager.models.tables.static_costs import static_cost  # noqa: F401

# --- Tasks (depends on customer; use_alter FKs to task_history_record and task_event) ---
from beyo_manager.models.tables.tasks import task  # noqa: F401

# --- Task history records (depends on task) ---
from beyo_manager.models.tables.tasks import task_history_record  # noqa: F401

# --- Task events (depends on task) ---
from beyo_manager.models.tables.tasks import task_event  # noqa: F401

# --- Task notes (depends on task) ---
from beyo_manager.models.tables.tasks import task_note  # noqa: F401

# --- Task items / bridge (depends on task and item) ---
from beyo_manager.models.tables.tasks import task_item  # noqa: F401

# --- Task steps (depends on task, working_section; use_alter FK to step_state_record) ---
from beyo_manager.models.tables.tasks import task_step  # noqa: F401

# --- Step state records (depends on task_step) ---
from beyo_manager.models.tables.tasks import step_state_record  # noqa: F401

# --- Task step dependencies (depends on task_step) ---
from beyo_manager.models.tables.tasks import task_step_dependency  # noqa: F401

# --- Task step assignment records (depends on task_step) ---
from beyo_manager.models.tables.tasks import task_step_assignment_record  # noqa: F401
```

---

### Step 5 — Create `__init__.py` stubs for all new folders

Each new folder under `models/tables/` and `domain/` needs an empty `__init__.py`.

New `models/tables/` folders requiring `__init__.py`:
- `models/tables/working_sections/__init__.py`
- `models/tables/issue_types/__init__.py`
- `models/tables/items/__init__.py`
- `models/tables/upholstery/__init__.py`
- `models/tables/customers/__init__.py`
- `models/tables/static_costs/__init__.py`
- `models/tables/tasks/__init__.py`

New `domain/` folders requiring `__init__.py` and `enums.py`:
- `domain/users/__init__.py` *(check if already exists — do not overwrite)*
- `domain/working_sections/__init__.py`
- `domain/customers/__init__.py`
- `domain/issue_types/__init__.py`
- `domain/items/__init__.py`
- `domain/upholstery/__init__.py`
- `domain/static_costs/__init__.py`
- `domain/tasks/__init__.py`
- `domain/task_steps/__init__.py`

---

### Step 6 — Verify create_type usage (avoid duplicate Postgres enum types)

Each `SAEnum(..., name="...", create_type=True)` creates a Postgres ENUM type. The same type name must not be emitted twice. Rule:

- The **first** model file (in `models/__init__.py` import order) that uses an enum type sets `create_type=True`.
- Every **subsequent** file that reuses the **same Postgres type name** sets `create_type=False`.

Shared enum type reuse map:

| Postgres type name | First file (create_type=True) | Reuse files (create_type=False) |
|---|---|---|
| `item_currency_enum` | `items/item.py` | `items/item_upholstery_requirement.py` |
| `task_step_state_enum` | `tasks/task_step.py` | `tasks/step_state_record.py` |

All other enum types appear in exactly one file — use `create_type=True` there.

---

## Risks and mitigations

- Risk: Circular FK at DDL time causes migration to fail.
  Mitigation: Use `use_alter=True` on all back-reference FKs identified in the circular FK table. Alembic will emit these as separate `ALTER TABLE ADD CONSTRAINT` statements after both tables are created.

- Risk: Duplicate Postgres enum type names cause `CREATE TYPE` to fail.
  Mitigation: Follow the create_type reuse map in Step 6. Only the first imported file uses `create_type=True`.

- Risk: Missing `__init__.py` in new domain or model folders causes `ModuleNotFoundError`.
  Mitigation: Step 5 explicitly lists every folder that needs an `__init__.py`.

- Risk: Wrong `models/__init__.py` import order breaks Alembic FK detection.
  Mitigation: Follow the exact order in Step 4. Do not reorder.

- Risk: `ws_sec` prefix (with underscore) was used in the intention file. Violates naming rule.
  Mitigation: Use `wsec` (4 lowercase letters) as specified in the prefix registry above.

- Risk: `Numeric` type accidentally replaced with `Float` for money/salary fields.
  Mitigation: Plan explicitly states `Numeric(precision, scale)` for all financial fields. `Float` is forbidden.

- Risk: `text(...)` not imported for partial index `postgresql_where` expressions.
  Mitigation: Import `text` from `sqlalchemy` in every file that declares a partial index.

---

## Validation plan

After all files are written:

- `cd backend/app && python -c "from beyo_manager.models import Base; print('OK')"`: Import chain is clean — no circular Python import errors.
- `alembic revision --autogenerate -m "add_domain_models" --dry-run` (or without `--dry-run` in dev): Migration detects all new tables, columns, indexes, and constraints without detecting unintended changes.
- Inspect the generated migration: verify `use_alter=True` FKs appear as separate `AddForeignKeyConstraint` ops after both referenced tables are created.
- Verify no duplicate `create type` statements for the shared enum types (`item_currency_enum`, `task_step_state_enum`).

---

## Review log

- `2026-05-15T10:00:01Z`: Implementation completed, summary generated, archive record created.

---

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: GitHub Copilot (archived after summary generation)
