# PLAN_history_record_system_20260518

## Metadata

- Plan ID: `PLAN_history_record_system_20260518`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-19T05:58:19Z`
- Related issue/ticket: `history-record-system`
- Intention plan: _none — new cross-cutting infrastructure_

---

## Goal and intent

- **Goal:** Implement a polymorphic history record system: a central `HistoryRecord` table that captures field-level changes (`created_at`, `created_by_id`, `change_type`, `description`, `field_name`, `from_value: JSONB`, `to_value: JSONB`) and a `HistoryRecordLink` table that connects each record to any addressable entity (item, item_upholstery, item_upholstery_requirement, task) via an `entity_type` enum + `entity_client_id` FK-less column — exactly mirroring the `image_links` and `case_links` patterns already in place.
- **Business/user intent:** Every meaningful mutation to an entity (field edits, state changes, creation, soft-deletion) should be auditable. The frontend can display a change timeline for any entity. The link table is designed for future extensibility: new entity types can be added without altering the core record table.
- **Non-goals:** Real-time event propagation of history records (that is a future analytics concern). Automatic diffing/trigger-based recording — all recording is explicit, called by commands. No permission system on history records (any authenticated workspace member can read). Modifying or deleting history records (they are append-only / immutable after creation).

---

## Prerequisite

Pre-existing schema and code must be cleaned up before new tables are created. The cleanup is part of this plan (Step 0). No prior plan must be applied first.

---

## Scope

- **In scope (pre-cleanup — Step 0):**
  - RENAME `models/base/history_record.py` class `HistoryRecord` → `HistoryRecordMixin` and update all its consumers
  - DELETE model files: `models/tables/customers/customer_history_record.py`, `models/tables/tasks/task_history_record.py`
  - DELETE enum: `CustomerHistoryChangeTypeEnum` from `domain/customers/enums.py`
  - MODIFY `models/tables/customers/customer.py` — remove `latest_history_record_id` column + FK
  - MODIFY `models/tables/tasks/task.py` — remove `latest_history_record_id` column + FK
  - MODIFY `models/__init__.py` — remove dead imports
  - DELETE `services/commands/reset/phases/delete_task_history_records.py`
  - MODIFY `services/commands/reset/reset_app.py` — remove that phase call and import
  - NEW migration — drop the old tables, FKs, indexes, and enum type in the correct order
- **In scope (new system — Steps 1–8):**
  - NEW `models/tables/history/` — `HistoryRecord`, `HistoryRecordLink` models + `__init__.py`
  - NEW `domain/history/` — `enums.py` (two enums), `serializers.py` (two serializers), `__init__.py`
  - NEW `services/commands/history/_create_history_record_in_session.py` — session helper (the primary interface for other commands)
  - NEW `services/commands/history/create_history_record.py` — public command wrapper using `maybe_begin`
  - NEW `services/commands/history/__init__.py`
  - NEW `services/queries/history/list_history_records.py` — paginated, filterable query
  - NEW `services/queries/history/__init__.py`
  - NEW `routers/api_v1/history.py` — GET-only router (no create/delete endpoints)
  - MODIFY `routers/api_v1/__init__.py` (or equivalent app registration file) — register the new router
  - NEW migration — `history_records` + `history_record_links` tables + `history_record_entity_type_enum` + `history_record_change_type_enum` Postgres types
- **Out of scope:** Hooking existing commands to record history (that is a follow-up task once this infrastructure is in place). No router endpoint for creating history records — creation is command-internal only. `user_history_records` table and `UserHistoryRecord` model — NOT deprecated, left as-is. The `HistoryRecord` mixin columns embedded directly on `cases` (`from_value`, `to_value`, `reason`) — NOT removed, left as-is (they track the case's own state, not audit records).
- **Assumptions:**
  - `customer_history_records` and `task_history_records` have zero active application writes or reads (confirmed by grep — only the `reset_app` teardown command touches `task_history_records`). Dropping them is safe.
  - `HistoryRecord` has no `workspace_id` — consistent with `Image` (workspace scoping goes through the entity side via `entity_client_id`). Any query for history by `entity_client_id` is implicitly workspace-scoped because entity IDs are globally unique.
  - `HistoryRecordLink.entity_client_id` is a plain `String(64)` with no FK constraint — same as `ImageLink.entity_client_id` and `CaseLink.entity_client_id`. This is the polymorphic FK-less design that allows pointing to any entity type.
  - The session helper always creates both `HistoryRecord` + `HistoryRecordLink` atomically in one call. The caller owns the transaction.
  - Records are append-only. There are no update or delete commands.

---

## Clarifications required

_None._

---

## Acceptance criteria

1. `HistoryRecord` and `HistoryRecordLink` tables exist in the DB after migration.
2. `_create_history_record_in_session` can be called inside any parent transaction with `entity_type`, `entity_client_id`, `change_type`, optional `description`, optional `field_name`, `from_value`, `to_value`, and `created_by_id`. It creates one `HistoryRecord` row and one `HistoryRecordLink` row, returns the `HistoryRecord`.
3. `GET /api/v1/history?entity_type=task&entity_client_id=tsk_xxx` returns a paginated list of history records linked to that entity, ordered newest first.
4. Filtering by `change_type` and `field_name` is supported as optional query parameters.
5. The router has no POST/PATCH/DELETE endpoints — the system is internally written by commands only.
6. Adding a new `entity_type` value in the future requires only: adding a value to `HistoryRecordEntityTypeEnum` and adding a migration for the Postgres enum type. No other files change.
7. `from_value` is `null` for `CREATED` records. `to_value` is `null` for `DELETED` records.
8. `field_name` is `null` for `CREATED` and `DELETED` change types; it names the changed field (e.g. `"state"`, `"amount_meters"`) for `UPDATED` records.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/03_models.md`: SQLAlchemy model conventions, `IdentityMixin`, `Base`, `SAEnum`, `configure_sa_enum_values`, JSONB usage
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: session-helper naming (`_verb_noun_in_session`), `maybe_begin` usage, `session.add` / `session.flush` sequence
- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: offset pagination pattern, query return shape
- `backend/architecture/09_routers.md`: handler wiring, body model, `_run` helper
- `backend/architecture/08_domain.md`: enum (`StrEnum`), serializer conventions
- `backend/architecture/30_migrations.md`: Alembic migration conventions — enum type creation order, `create_type=False` usage
- `backend/architecture/21_naming_conventions.md`: prefix registry, module naming
- `backend/architecture/40_identity.md` + `backend/architecture/40_identity_local.md`: `CLIENT_ID_PREFIX` registration, `generate_id`

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: session helpers must not open transactions; `maybe_begin` is for public commands
- `backend/architecture/07_queries_local.md`: offset pagination with `has_more` sentinel

### File read intent — pattern vs. relational

Permitted relational reads (understanding what exists):

| File | What to extract |
|---|---|
| `models/tables/images/image_link.py` | `ImageLink` field shapes — `entity_type` SAEnum, `entity_client_id` FK-less String(64), `UniqueConstraint` pattern |
| `models/tables/images/image.py` | How `Image` references its links via relationship, no `workspace_id` |
| `models/tables/cases/case_link.py` | `CaseLinkEntityTypeEnum` usage, `CaseLinkRoleEnum`, confirm FK-less pattern |
| `domain/images/enums.py` | `ImageLinkEntityTypeEnum` as `StrEnum` pattern — confirm values are lowercase strings |
| `domain/images/serializers.py` | Serializer function shape — confirm `_value()` helper usage for enum coercion |
| `domain/cases/enums.py` | `CaseLinkEntityTypeEnum` + `CaseLinkRoleEnum` — confirm StrEnum pattern |
| `services/commands/cases/link_entity.py` | How a "link" command creates both the lookup and the link row; confirms `session.begin()` ownership pattern for a public command |
| `services/queries/cases/list_linked_entities.py` | Query pattern for polymorphic link filtering |
| `routers/api_v1/cases.py` | `_run` helper pattern, body model wiring — confirm GET-only route structure we'll mirror |
| `models/base/identity.py` | `generate_id` and `IdentityMixin.client_id` declared_attr pattern |

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand `session.add` / `flush` / error-raising → `06_commands.md`
- Reading another router to understand handler skeleton → `09_routers.md`
- Reading another serializer to understand output shape → `08_domain.md`

---

## Implementation plan

### Step 0 — Pre-cleanup: deprecate dead history tables

This step must be completed **before Step 1**. It removes the dead `customer_history_records` and `task_history_records` schema, resolves the naming collision on the `HistoryRecord` base mixin, and eliminates all code that references the deprecated tables.

#### Step 0a — Rename base mixin

**`beyo_manager/models/base/history_record.py`**

Rename the class declaration:
```python
# Before:
class HistoryRecord:
# After:
class HistoryRecordMixin:
```

**`beyo_manager/models/tables/users/user_history_record.py`**

Update the import and the class declaration:
```python
from beyo_manager.models.base.history_record import HistoryRecordMixin
# ...
class UserHistoryRecord(IdentityMixin, HistoryRecordMixin, Base):
```

**`beyo_manager/models/tables/cases/case.py`**

Update the import and the class declaration:
```python
from beyo_manager.models.base.history_record import HistoryRecordMixin
# ...
class Case(IdentityMixin, HistoryRecordMixin, Base):
```

#### Step 0b — Delete dead model files and enum

1. **Delete** `beyo_manager/models/tables/customers/customer_history_record.py`
2. **Delete** `beyo_manager/models/tables/tasks/task_history_record.py`
3. In `beyo_manager/domain/customers/enums.py`: **remove** the `CustomerHistoryChangeTypeEnum` class entirely.

#### Step 0c — Remove dead columns from existing models

**`beyo_manager/models/tables/customers/customer.py`**

Remove the `latest_history_record_id` column and its FK declaration (the exact field uses `use_alter=True` and `deferrable=True` — remove the entire `mapped_column` entry).

**`beyo_manager/models/tables/tasks/task.py`**

Remove the `latest_history_record_id` column and its FK declaration (same pattern as customer — `use_alter=True`, `deferrable=True`).

#### Step 0d — Update models registry

**`beyo_manager/models/__init__.py`**

Remove the two dead import lines (find by module name):
```python
# Remove these two lines:
from beyo_manager.models.tables.customers import customer_history_record  # noqa: F401
from beyo_manager.models.tables.tasks import task_history_record  # noqa: F401
```

#### Step 0e — Delete reset phase and update reset command

1. **Delete** `beyo_manager/services/commands/reset/phases/delete_task_history_records.py`
2. In `beyo_manager/services/commands/reset/reset_app.py`: remove the import of `delete_task_history_records` and its corresponding `await` call.

#### Step 0f — Migration: drop dead tables

Create a new Alembic migration for the cleanup. This migration must be given a **lower revision number** than the new-table migration created in Step 3 — it must run first.

Operations must execute in this exact order (FK constraints must be dropped before columns, columns before tables, tables before enum type):

```python
# In upgrade():

# 1. Drop FK constraints referencing the dead tables
op.drop_constraint("fk_customers_latest_history_record_id", "customers", type_="foreignkey")
op.drop_constraint("fk_tasks_latest_history_record_id", "tasks", type_="foreignkey")

# 2. Drop the columns that held those FKs
op.drop_column("customers", "latest_history_record_id")
op.drop_column("tasks", "latest_history_record_id")

# 3. Drop all indexes on the dead tables before dropping the tables
#    (find exact index names via \d customer_history_records and \d task_history_records in psql,
#    or read the original migration that created them)
#    Example pattern:
#    op.drop_index("ix_customer_history_records_<col>", table_name="customer_history_records")

# 4. Drop the dead tables
op.drop_table("customer_history_records")
op.drop_table("task_history_records")

# 5. Drop the enum type (no table references it any more)
op.execute("DROP TYPE IF EXISTS customer_history_change_type_enum")
```

```python
# In downgrade():
# Reverse: re-create enum type, tables, columns, FK constraints in reverse order.
# (Copilot: write the exact downgrade inverse of the above — use op.create_table,
#  op.add_column, op.create_foreign_key, op.execute("CREATE TYPE ...") in the
#  correct reverse order.)
```

**Note on exact constraint and index names:** Read the migration file that originally created `customer_history_records` and `task_history_records` to confirm the exact FK constraint names and index names before writing this migration. Do not guess.

---

### Step 1 — Domain: `domain/history/`

Create `beyo_manager/domain/history/__init__.py` (empty).

**`beyo_manager/domain/history/enums.py`**

```python
from enum import StrEnum


class HistoryRecordEntityTypeEnum(StrEnum):
    ITEM = "item"
    ITEM_UPHOLSTERY = "item_upholstery"
    ITEM_UPHOLSTERY_REQUIREMENT = "item_upholstery_requirement"
    TASK = "task"
    CASE = "case"
    USER = "user"


class HistoryRecordChangeTypeEnum(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
```

**`beyo_manager/domain/history/serializers.py`**

```python
def _value(v):
    return v.value if hasattr(v, "value") else v


def serialize_history_record(record) -> dict:
    return {
        "client_id": record.client_id,
        "change_type": _value(record.change_type),
        "description": record.description,
        "field_name": record.field_name,
        "from_value": record.from_value,
        "to_value": record.to_value,
        "created_at": record.created_at.isoformat(),
        "created_by_id": record.created_by_id,
    }


def serialize_history_record_with_link(record, link) -> dict:
    return {
        **serialize_history_record(record),
        "entity_type": _value(link.entity_type),
        "entity_client_id": link.entity_client_id,
    }
```

---

### Step 2 — Models: `models/tables/history/`

Create `beyo_manager/models/tables/history/__init__.py` (empty).

**`beyo_manager/models/tables/history/history_record.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class HistoryRecord(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "hrec"
    __tablename__ = "history_records"

    change_type: Mapped[HistoryRecordChangeTypeEnum] = mapped_column(
        SAEnum(HistoryRecordChangeTypeEnum, name="history_record_change_type_enum", create_type=False),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    from_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    to_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id", deferrable=True), nullable=True, index=True
    )

    link: Mapped["HistoryRecordLink | None"] = relationship(
        "HistoryRecordLink", back_populates="history_record", uselist=False
    )
```

**`beyo_manager/models/tables/history/history_record_link.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.domain.history.enums import HistoryRecordEntityTypeEnum
from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin
from beyo_manager.models.base.sa_enum import configure_sa_enum_values


SAEnum = configure_sa_enum_values(SAEnum)


class HistoryRecordLink(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "hrlk"
    __tablename__ = "history_record_links"

    history_record_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("history_records.client_id", deferrable=True), nullable=False, index=True
    )
    entity_type: Mapped[HistoryRecordEntityTypeEnum] = mapped_column(
        SAEnum(HistoryRecordEntityTypeEnum, name="history_record_entity_type_enum", create_type=False),
        nullable=False,
        index=True,
    )
    entity_client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    history_record: Mapped["HistoryRecord"] = relationship(
        "HistoryRecord", back_populates="link"
    )

    __table_args__ = (
        Index(
            "ix_history_record_links_entity_type_client_id",
            "entity_type",
            "entity_client_id",
        ),
    )
```

**Why no `UniqueConstraint` on `history_record_id`?**
Future extensibility — a single HistoryRecord may one day be linked to multiple entities (e.g. a bulk operation touching multiple items). The session helper always creates exactly one link per call in its current form, but the schema imposes no such constraint.

**Register in `models/__init__.py`**

After creating both model files, add them to `beyo_manager/models/__init__.py` so Alembic detects the new tables. Follow the same pattern as the rest of the file — one import per module, with a comment grouping:

```python
# --- History records ---
from beyo_manager.models.tables.history import history_record  # noqa: F401
from beyo_manager.models.tables.history import history_record_link  # noqa: F401
```

Place this block after the existing image/case imports (the exact insertion point is not critical, but it must come after `Base` is imported at the top). Without this step, Alembic will not detect the new tables and the auto-generated migration will be empty.

---

### Step 3 — Migration

Create a new Alembic migration file. The migration must:

1. Create the two Postgres enum types BEFORE the tables that use them. Enum creation order:
   ```python
   # In upgrade():
   op.execute("CREATE TYPE history_record_change_type_enum AS ENUM ('created', 'updated', 'deleted')")
   op.execute("CREATE TYPE history_record_entity_type_enum AS ENUM ('item', 'item_upholstery', 'item_upholstery_requirement', 'task', 'case', 'user')")
   ```

2. Create `history_records` table:
   - `client_id VARCHAR(64) PRIMARY KEY`
   - `change_type history_record_change_type_enum NOT NULL`
   - `description VARCHAR(512) NULLABLE`
   - `field_name VARCHAR(128) NULLABLE`
   - `from_value JSONB NULLABLE`
   - `to_value JSONB NULLABLE`
   - `created_at TIMESTAMPTZ NOT NULL`
   - `created_by_id VARCHAR(64) NULLABLE REFERENCES users(client_id) DEFERRABLE`
   - Indexes: `change_type`, `field_name`, `created_at`, `created_by_id`

3. Create `history_record_links` table:
   - `client_id VARCHAR(64) PRIMARY KEY`
   - `history_record_id VARCHAR(64) NOT NULL REFERENCES history_records(client_id) DEFERRABLE`
   - `entity_type history_record_entity_type_enum NOT NULL`
   - `entity_client_id VARCHAR(64) NOT NULL`
   - `created_at TIMESTAMPTZ NOT NULL`
   - Indexes: `history_record_id`, `entity_type`, composite `(entity_type, entity_client_id)`

4. In `downgrade()`: drop tables first (child before parent), then drop enum types:
   ```python
   op.drop_table("history_record_links")
   op.drop_table("history_records")
   op.execute("DROP TYPE history_record_entity_type_enum")
   op.execute("DROP TYPE history_record_change_type_enum")
   ```

**`create_type=False` on both `SAEnum` usages** — the types are created by the migration, NOT by SQLAlchemy's `create_all`. This is the established pattern in this codebase (see `CaseLink`, `TaskStep` models).

---

### Step 4 — Session helper: `services/commands/history/_create_history_record_in_session.py`

Create `beyo_manager/services/commands/history/__init__.py` (empty) before creating the files below.

This is the **primary interface** for all other commands. It does not own a transaction.

```python
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink


async def _create_history_record_in_session(
    session: AsyncSession,
    entity_type: HistoryRecordEntityTypeEnum,
    entity_client_id: str,
    change_type: HistoryRecordChangeTypeEnum,
    from_value: dict | None,
    to_value: dict | None,
    created_by_id: str | None,
    description: str | None = None,
    field_name: str | None = None,
) -> HistoryRecord:
    now = datetime.now(timezone.utc)
    record = HistoryRecord(
        change_type=change_type,
        description=description,
        field_name=field_name,
        from_value=from_value,
        to_value=to_value,
        created_at=now,
        created_by_id=created_by_id,
    )
    session.add(record)
    await session.flush()  # assign record.client_id before linking

    link = HistoryRecordLink(
        history_record_id=record.client_id,
        entity_type=entity_type,
        entity_client_id=entity_client_id,
        created_at=now,
    )
    session.add(link)
    await session.flush()

    return record
```

**Import path for all callers:**
```python
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
```

**Usage pattern inside any command:**
```python
# Example: inside update_task.py, after mutating task.title
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task.client_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description="Task title updated.",
    field_name="title",
    from_value={"title": old_title},
    to_value={"title": task.title},
    created_by_id=ctx.user_id,
)
```

---

### Step 5 — Public command: `services/commands/history/create_history_record.py`

A thin `maybe_begin` wrapper for callers that do not already own a transaction. Standalone use only — the session helper is preferred when inside a parent transaction.

```python
from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_history_record(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}

    entity_type_raw = data.get("entity_type")
    entity_client_id = data.get("entity_client_id")
    change_type_raw = data.get("change_type")

    if not entity_type_raw or not entity_client_id or not change_type_raw:
        raise ValidationError("entity_type, entity_client_id, and change_type are required.")

    try:
        entity_type = HistoryRecordEntityTypeEnum(entity_type_raw)
    except ValueError:
        raise ValidationError(f"Unknown entity_type: {entity_type_raw!r}")

    try:
        change_type = HistoryRecordChangeTypeEnum(change_type_raw)
    except ValueError:
        raise ValidationError(f"Unknown change_type: {change_type_raw!r}")

    async with maybe_begin(ctx.session):
        record = await _create_history_record_in_session(
            session=ctx.session,
            entity_type=entity_type,
            entity_client_id=entity_client_id,
            change_type=change_type,
            description=data.get("description"),
            field_name=data.get("field_name"),
            from_value=data.get("from_value"),
            to_value=data.get("to_value"),
            created_by_id=ctx.user_id,
        )

    # record.link is flush-loaded — re-fetch if needed; for simplicity return flat dict
    return {
        "client_id": record.client_id,
        "entity_type": entity_type.value,
        "entity_client_id": entity_client_id,
        "change_type": change_type.value,
        "description": record.description,
        "field_name": record.field_name,
        "from_value": record.from_value,
        "to_value": record.to_value,
        "created_at": record.created_at.isoformat(),
        "created_by_id": record.created_by_id,
    }
```

---

### Step 6 — Query: `services/queries/history/list_history_records.py`

Create `beyo_manager/services/queries/history/__init__.py` (empty) before creating the file below.

Paginated, ordered newest-first. Filters by `entity_type` + `entity_client_id` (required — always scope to one entity), with optional `change_type` and `field_name` filters.

```python
from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.history.serializers import serialize_history_record_with_link
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.services.context import ServiceContext

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


async def list_history_records(ctx: ServiceContext) -> dict:
    params = ctx.incoming_data or {}
    entity_type_raw = params.get("entity_type")
    entity_client_id = params.get("entity_client_id")

    if not entity_type_raw or not entity_client_id:
        raise ValidationError("entity_type and entity_client_id are required query parameters.")

    try:
        entity_type = HistoryRecordEntityTypeEnum(entity_type_raw)
    except ValueError:
        raise ValidationError(f"Unknown entity_type: {entity_type_raw!r}")

    limit = min(int(params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(params.get("offset", 0))

    stmt = (
        select(HistoryRecord, HistoryRecordLink)
        .join(HistoryRecordLink, HistoryRecordLink.history_record_id == HistoryRecord.client_id)
        .where(
            HistoryRecordLink.entity_type == entity_type,
            HistoryRecordLink.entity_client_id == entity_client_id,
        )
    )

    if params.get("change_type"):
        try:
            stmt = stmt.where(
                HistoryRecord.change_type == HistoryRecordChangeTypeEnum(params["change_type"])
            )
        except ValueError:
            raise ValidationError(f"Unknown change_type: {params['change_type']!r}")

    if params.get("field_name"):
        stmt = stmt.where(HistoryRecord.field_name == params["field_name"])

    stmt = stmt.order_by(HistoryRecord.created_at.desc())
    stmt = stmt.offset(offset).limit(limit + 1)

    rows = (await ctx.session.execute(stmt)).all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "history_pagination": {
            "items": [
                serialize_history_record_with_link(record, link)
                for record, link in page
            ],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
```

---

### Step 7 — Router: `routers/api_v1/history.py`

GET-only. No create/update/delete endpoints — history is written by commands exclusively.

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.history.list_history_records import list_history_records
from beyo_manager.services.run_service import run_service

router = APIRouter()


async def _run(query, data: dict, claims: dict, session: AsyncSession):
    outcome = await run_service(query, ServiceContext(identity=claims, incoming_data=data, session=session))
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.get("")
async def list_history_records_route(
    entity_type: str,
    entity_client_id: str,
    change_type: str | None = None,
    field_name: str | None = None,
    offset: int = 0,
    limit: int = 50,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_history_records,
        {
            "entity_type": entity_type,
            "entity_client_id": entity_client_id,
            "change_type": change_type,
            "field_name": field_name,
            "offset": offset,
            "limit": limit,
        },
        claims,
        session,
    )
```

**Note:** The router passes all params via `incoming_data=data` in the `ServiceContext` constructor (matching the `list_cases` pattern). The query reads from `ctx.incoming_data`, not `ctx.query_params`.

---

### Step 8 — Register the router

Locate the file that registers all `api_v1` routers (typically `routers/api_v1/__init__.py` or `app.py`). Add:

```python
from beyo_manager.routers.api_v1.history import router as history_router

app.include_router(history_router, prefix="/api/v1/history", tags=["history"])
# or however other routers are registered — match the exact pattern
```

Read the existing router registration file to confirm the exact `include_router` call style before writing.

---

## Critical implementation notes

### `create_type=False` on both SAEnum usages

Both `history_record_change_type_enum` and `history_record_entity_type_enum` must use `create_type=False` in the SQLAlchemy SAEnum declaration. These Postgres types are created by the migration, not by `create_all`. If `create_type=True` is used instead, running the migration on a database that already has tables would attempt to create the type twice and fail.

### Flush before linking

`HistoryRecord` must be flushed before creating `HistoryRecordLink` so that `record.client_id` is assigned (the `IdentityMixin` default fires on flush, not on `session.add`). See Step 4 — two sequential `session.flush()` calls.

### No `workspace_id` on `HistoryRecord`

Intentional — matching the `Image` model. Workspace scoping is enforced at the query level by requiring `entity_client_id`, which is globally unique per entity (ULID). No cross-workspace data leakage is possible through entity_client_id filtering.

### Extending entity types in the future

To add a new entity type (e.g. `CUSTOMER = "customer"`):
1. Add the value to `HistoryRecordEntityTypeEnum`
2. Write a migration: `op.execute("ALTER TYPE history_record_entity_type_enum ADD VALUE 'customer'")`
No other files change.

### `field_name` semantics by `change_type`

| `change_type` | `field_name` | `from_value` | `to_value` |
|---|---|---|---|
| `created` | `null` | `null` | snapshot of new entity fields |
| `updated` | `"field_name"` (e.g. `"state"`) | `{"state": "old"}` | `{"state": "new"}` |
| `deleted` | `null` | snapshot of entity before deletion | `null` |

Callers are responsible for following these conventions. The model does not enforce them.

---

## Risks and mitigations

- **Risk:** `create_type=False` is forgotten on one of the SAEnum fields — migration fails on `CREATE TYPE` conflict.
  **Mitigation:** The plan specifies both SAEnum declarations explicitly with `create_type=False`. Copilot must verify this on both model files after writing them.

- **Risk:** The relationship `HistoryRecord.link` is `uselist=False` but the DB has no unique constraint on `history_record_links.history_record_id`. If two links are ever created for the same record, ORM loads will be non-deterministic.
  **Mitigation:** The session helper always creates exactly one link per record. This is a convention enforced by code, not schema. If the future requires multi-entity links, `uselist=False` should be changed to `uselist=True`.

- **Risk:** The query in Step 5 uses an INNER JOIN — records without a link row are silently dropped.
  **Mitigation:** The session helper always creates link + record atomically. A record without a link cannot exist in normal operation. This is correct behavior and consistent with how `ImageLink` is joined in image queries.

- **Risk:** `entity_type` and `entity_client_id` are required query params. Omitting them returns a `ValidationError`, not an empty list.
  **Mitigation:** Intentional design — history records are only meaningful scoped to a specific entity. Workspace-wide history queries are not in scope.

---

## Validation plan

```
# 1. Run migration → both tables created, both enum types created.

# 2. Call _create_history_record_in_session inside a test transaction:
#    entity_type=TASK, entity_client_id="tsk_xxx", change_type=CREATED,
#    field_name=None, from_value=None, to_value={"title": "New task"}
#    → one row in history_records, one row in history_record_links.
#    record.client_id starts with "hrec_", link.client_id starts with "hrlk_".

# 3. GET /api/v1/history?entity_type=task&entity_client_id=tsk_xxx
#    → returns {"history_pagination": {"items": [<record>], "has_more": false, ...}}

# 4. GET with change_type=updated filter → only UPDATED records returned.
# 5. GET with field_name=state filter → only "state" field records returned.
# 6. GET with entity_type missing → 400 ValidationError.
# 7. GET with invalid entity_type → 400 ValidationError.
# 8. No POST endpoint exists on /api/v1/history → 405 Method Not Allowed.

# 9. Create 201 records for same entity → GET with limit=50 returns 50 items, has_more=true.
#    GET with offset=50 → next page.

# 10. Verify created_at ordering: newest first (DESC).

# 11. Create history records for two different entity_client_ids.
#     GET scoped to entity A → does NOT return entity B records.
```

---

## Review log

- `2026-05-19T05:12:00Z` — completed Step 0 cleanup: renamed the shared base to `HistoryRecordMixin`, removed dead customer/task history models and reset teardown references, and removed `latest_history_record_id` from customer/task model surfaces.
- `2026-05-19T05:40:00Z` — implemented the new history domain, models, session helper, public command wrapper, paginated query, router, and router registration following the plan contracts.
- `2026-05-19T05:52:00Z` — created and populated cleanup migration `f9de7bfdb842` and new-system migration `868a18698f33`; fixed enum creation handling with `create_type=False` after the first upgrade attempt exposed duplicate enum DDL.
- `2026-05-19T05:58:19Z` — validated with `py_compile`, import checks, `alembic upgrade head`, editor problems check, direct service smoke test, and in-process FastAPI route smoke test (`sign-in 200`, `GET /api/v1/history 200`, created record returned, cleanup successful).

---

## Lifecycle transition

- Current state: `archived`
- Next state: _none_
- Transition owner: `copilot`
