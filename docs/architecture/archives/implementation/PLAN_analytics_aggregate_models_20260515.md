# PLAN_analytics_aggregate_models_20260515

## Metadata

- Plan ID: `PLAN_analytics_aggregate_models_20260515`
- Status: `under_construction`
- Owner agent: `Claude`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T00:00:00Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/planning_tables/working_sections/analytics/analytics_models.md`

## Goal and intent

- Goal: Create the 4 missing analytics aggregate model files in a new `models/tables/analytics/` domain, register them in `models/__init__.py`, register their client_id prefixes in `40_identity_local.md`, and generate an alembic migration.
- Business/user intent: Every registered workspace needs foundational aggregate tables in place so that future command flows (shifts, task execution) can update projection state without lazy-creating rows or encountering missing aggregates.
- Non-goals: Inserting `user_lifetime_stats` during user registration (separate follow-up plan). No analytics pipelines, workers, or query endpoints. No domain enums needed for these tables.

## Scope

- In scope:
  - 5 new files: `models/tables/analytics/__init__.py` + 4 model files
  - `models/__init__.py`: add 4 import registrations in correct dependency order
  - `backend/architecture/40_identity_local.md`: register 4 new prefixes
  - Alembic migration: run `alembic revision --autogenerate -m "add_analytics_aggregate_tables"` and verify output
- Out of scope: Eager creation during user registration, queries, routers, serializers, workers.
- Assumptions:
  - All 4 aggregate metrics mixins already exist in `models/base/aggregate_metrics.py` and do not need changes.
  - The `working_sections` table exists (imported before analytics in `__init__.py`).
  - `updated_at` is **non-nullable** on all analytics aggregate tables — set by command layer on every mutation; deviates intentionally from the nullable `updated_at` pattern on core entity tables.

## File manifest

List every file touched by this plan. Implementing agents use this table to know what
to open (EDIT) versus what to create from scratch (CREATE). Never search for CREATE files
— they do not exist yet.

### Existing files to edit

| Path (relative to `backend/app/`) | Change summary |
|---|---|
| `beyo_manager/models/__init__.py` | Append 4 analytics module import lines under a new `# --- Analytics aggregates ---` comment block |
| `backend/architecture/40_identity_local.md` | Append 4 new prefix entries under "Local Decisions" |

> Note: `backend/architecture/` is relative to the repo root, not `backend/app/`.

### New files to create

| Path (relative to `backend/app/`) |
|---|
| `beyo_manager/models/tables/analytics/__init__.py` |
| `beyo_manager/models/tables/analytics/user_lifetime_stats.py` |
| `beyo_manager/models/tables/analytics/user_daily_work_stats.py` |
| `beyo_manager/models/tables/analytics/user_section_daily_work_stats.py` |
| `beyo_manager/models/tables/analytics/working_section_daily_work_stats.py` |

## Clarifications required

None — all decisions resolved in the intention plan and alignment session.

## Acceptance criteria

1. `python -c "from beyo_manager.models import Base; print('OK')"` runs without error (all 4 new models imported through `__init__.py`).
2. `.venv/bin/python -m compileall -q beyo_manager && echo OK` exits clean.
3. `alembic revision --autogenerate` produces a non-empty migration that creates 4 new tables: `user_lifetime_stats`, `user_daily_work_stats`, `user_section_daily_work_stats`, `working_section_daily_work_stats`.
4. `alembic upgrade head` applies the migration without error.
5. A subsequent `alembic revision --autogenerate -m "drift_check"` detects no schema drift.
6. `40_identity_local.md` lists all 4 new prefixes.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: layer boundaries — models live in models/tables/, no business logic in model files
- `backend/architecture/03_models.md`: SQLAlchemy 2.x `Mapped`/`mapped_column`, UTC DateTime, FK indexing, named constraints
- `backend/architecture/08_domain.md`: enums in `domain/<domain>/enums.py` — not applicable here (no enums)
- `backend/architecture/21_naming_conventions.md`: table name, index name, constraint name patterns
- `backend/architecture/30_migrations.md`: alembic autogenerate, `use_alter` for circular FKs (not needed here), verify no drift after upgrade
- `backend/architecture/40_identity.md` + `backend/architecture/40_identity_local.md`: client_id prefix rule, prefix registration requirement

### Local extensions loaded

- `backend/architecture/40_identity_local.md`: existing prefix registry — new entries must be appended, no existing entries changed

### File read intent — pattern vs. relational

Before reading any file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`03_models.md`, `21_naming_conventions.md`)
- **What exists** → reading is legitimate (field names, existing import order in `__init__.py`, existing prefix list)

Permitted reads for this plan:
- `beyo_manager/models/__init__.py` — to find the correct insertion point
- `beyo_manager/models/base/aggregate_metrics.py` — to verify mixin names before importing
- `backend/architecture/40_identity_local.md` — to find the correct insertion point for new prefixes

Prohibited reads (pattern reads — contract already covers these):
- Reading another model file to understand `Mapped`/`mapped_column` syntax → `03_models.md`
- Reading `identity.py` to understand `IdentityMixin` → already known from `03_models.md` and `40_identity.md`

### Skill selection

- Primary skill: CRUD + realtime goal bundle (models + migrations)
- Excluded: worker-driven, replayable async, CI-validated — not triggered

## Implementation plan

### Step 1 — Create `models/tables/analytics/__init__.py`

**File**: `beyo_manager/models/tables/analytics/__init__.py`

Content: empty file (package marker only).

---

### Step 2 — Create `user_lifetime_stats.py`

**File**: `beyo_manager/models/tables/analytics/user_lifetime_stats.py`

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.aggregate_metrics import (
    AggregateMetricsCostMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsTotalsMixin,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UserLifetimeStats(
    IdentityMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTotalsMixin,
    AggregateMetricsCostMixin,
    Base,
):
    CLIENT_ID_PREFIX = "usr_stat"
    __tablename__ = "user_lifetime_stats"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_display_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_user_lifetime_stats_workspace_user"),
        Index("ix_user_lifetime_stats_workspace_user", "workspace_id", "user_id"),
    )
```

> `updated_at` is **non-nullable** and has no `onupdate`. The command layer sets it explicitly on every aggregate mutation. This is intentional per the aggregate design contract.

---

### Step 3 — Create `user_daily_work_stats.py`

**File**: `beyo_manager/models/tables/analytics/user_daily_work_stats.py`

```python
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.aggregate_metrics import (
    AggregateMetricsCostMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsTotalsMixin,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UserDailyWorkStats(
    IdentityMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTotalsMixin,
    AggregateMetricsCostMixin,
    Base,
):
    CLIENT_ID_PREFIX = "udwr"
    __tablename__ = "user_daily_work_stats"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_display_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "user_id", "work_date",
            name="uq_user_daily_work_stats_workspace_user_date",
        ),
        Index("ix_user_daily_work_stats_user_date", "user_id", "work_date"),
    )
```

> `work_date` is a `Date` column. The value must be computed by the caller using the workspace's operational timezone before passing it to the command layer — not derived from UTC at the DB level.

---

### Step 4 — Create `user_section_daily_work_stats.py`

**File**: `beyo_manager/models/tables/analytics/user_section_daily_work_stats.py`

```python
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.aggregate_metrics import (
    AggregateMetricsCostMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsTotalsMixin,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UserSectionDailyWorkStats(
    IdentityMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTotalsMixin,
    AggregateMetricsCostMixin,
    Base,
):
    CLIENT_ID_PREFIX = "usdwr"
    __tablename__ = "user_section_daily_work_stats"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    working_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    section_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    user_display_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "user_id", "working_section_id", "work_date",
            name="uq_user_section_daily_work_stats_workspace_user_section_date",
        ),
        Index("ix_user_section_daily_work_stats_section_date", "working_section_id", "work_date"),
    )
```

---

### Step 5 — Create `working_section_daily_work_stats.py`

**File**: `beyo_manager/models/tables/analytics/working_section_daily_work_stats.py`

```python
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.aggregate_metrics import (
    AggregateMetricsCostMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsTotalsMixin,
)
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class WorkingSectionDailyWorkStats(
    IdentityMixin,
    AggregateMetricsTimeMixin,
    AggregateMetricsCountsMixin,
    AggregateMetricsTotalsMixin,
    AggregateMetricsCostMixin,
    Base,
):
    CLIENT_ID_PREFIX = "wsdws"
    __tablename__ = "working_section_daily_work_stats"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    working_section_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("working_sections.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    section_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "working_section_id", "work_date",
            name="uq_working_section_daily_work_stats_workspace_section_date",
        ),
        Index("ix_working_section_daily_work_stats_section_date", "working_section_id", "work_date"),
    )
```

---

### Step 6 — Register in `models/__init__.py`

**File**: `beyo_manager/models/__init__.py`

Append the following block at the **end of the file**, after the existing `# --- Task step assignment records ---` line:

```python
# --- Analytics aggregates (depends on users and working_sections) ---
from beyo_manager.models.tables.analytics import user_lifetime_stats  # noqa: F401
from beyo_manager.models.tables.analytics import user_daily_work_stats  # noqa: F401
from beyo_manager.models.tables.analytics import user_section_daily_work_stats  # noqa: F401
from beyo_manager.models.tables.analytics import working_section_daily_work_stats  # noqa: F401
```

> These must be imported **after** `working_sections` and `users` since they hold FKs into both.

---

### Step 7 — Register prefixes in `40_identity_local.md`

**File**: `backend/architecture/40_identity_local.md`

Under the existing "Local Decisions" bullet list, append the following entries:

```
- Added table prefix reservations for analytics aggregate models (PLAN_analytics_aggregate_models_20260515):
    - `usr_stat`: `UserLifetimeStats`
    - `udwr`: `UserDailyWorkStats`
    - `usdwr`: `UserSectionDailyWorkStats`
    - `wsdws`: `WorkingSectionDailyWorkStats`
```

> Compressed prefixes are intentional per the prefix strategy rules in `analytics_models.md`.

---

### Step 8 — Generate and verify the alembic migration

Run from `backend/app/`:

```bash
APP_ENV=development ./.venv/bin/alembic revision --autogenerate -m "add_analytics_aggregate_tables"
```

Verify the generated migration file:
- Creates 4 new tables: `user_lifetime_stats`, `user_daily_work_stats`, `user_section_daily_work_stats`, `working_section_daily_work_stats`
- Each table includes all aggregate mixin columns (`total_working_seconds`, `total_pause_seconds`, `total_ended_shift_seconds`, `total_working_count`, `total_pause_count`, `total_ended_shift_count`, `total_issues_count`, `total_issues_resolved_count`, `total_cost_minor`)
- Each table includes its `UniqueConstraint` and `Index`

Then apply:

```bash
APP_ENV=development ./.venv/bin/alembic upgrade head
```

Then verify no drift:

```bash
APP_ENV=development ./.venv/bin/alembic revision --autogenerate -m "analytics_drift_check"
```

The drift-check migration must be empty (no `op.create_table`, `op.add_column`, or `op.create_index` calls). Delete the drift-check file after confirming.

## Risks and mitigations

- Risk: Import order in `__init__.py` — analytics tables FK into `working_sections` and `users`, which must be imported first.
  Mitigation: Step 6 appends to the end of the file, after all existing imports, which already include `working_sections` and `users`.

- Risk: `CLIENT_ID_PREFIX = "usr_stat"` contains an underscore — unusual for identity prefixes.
  Mitigation: The prefix is defined in `analytics_models.md` and explicitly documented as intentional. Prefix strategy rules state: "compressed prefixes are intentional and must remain documented centrally." Register it as-is.

- Risk: `updated_at` non-nullable diverges from the nullable `onupdate` pattern used in core entity tables — Copilot may revert to the nullable pattern.
  Mitigation: Step notes explicitly state the deviation is intentional. The column has `default=lambda: datetime.now(timezone.utc)` but no `onupdate`. Do not add `onupdate`.

## Validation plan

- `APP_ENV=development python -c "from beyo_manager.models import Base; print('OK_BASE_IMPORT')"` (run from `backend/app`): prints `OK_BASE_IMPORT`.
- `./.venv/bin/python -m compileall -q beyo_manager && echo COMPILE_OK` (run from `backend/app`): prints `COMPILE_OK`.
- `alembic revision --autogenerate` output: 4 new tables detected, no drift on existing tables.
- `alembic upgrade head`: applies without error.
- Subsequent `alembic revision --autogenerate -m "drift_check"`: empty migration (delete after confirming).

## Review log

_Empty — awaiting implementation._

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: David
