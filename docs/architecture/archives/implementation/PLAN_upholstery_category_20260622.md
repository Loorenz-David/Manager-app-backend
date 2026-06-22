# PLAN_upholstery_category_20260622

## Metadata

- Plan ID: `PLAN_upholstery_category_20260622`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-22T00:00:00Z`
- Last updated at (UTC): `2026-06-22T09:14:43Z`
- Related issue/ticket: —
- Intention plan: n/a — implementation intent supplied directly by the product owner

---

## Goal and intent

- **Goal:** Introduce `UpholsteryCategory` as a new workspace-scoped entity that groups upholsteries via a one-to-many FK (one category → many upholsteries). Deliver full CRUD + favorite-toggle + listing endpoints for the category. Extend upholstery create/update to accept a category link. Extend `list_upholsteries` with an `upholstery_category_ids` comma-separated filter. Enrich `serialize_upholstery` with a nested `upholstery_category` key. Finally, produce a frontend handoff document covering all new and changed endpoints.
- **Business/user intent:** The frontend renders upholsteries in folder-style groupings. A category is a lightweight label with an image; each upholstery optionally belongs to one category. Managing categories is decoupled from managing upholsteries; the link is set at upholstery create/update time.
- **Non-goals:**
  - Many-to-many category assignment.
  - Ordering or nesting of categories.
  - Batch-moving upholsteries between categories.
  - A dedicated clear-category operation (setting `upholstery_category_id` back to null without a full update).
  - Any change to upholstery inventory, orders, or supplier logic.
  - Realtime/socket broadcast for category events.

---

## Scope

### In scope

| # | Artifact | Action |
|---|---|---|
| 1 | `models/tables/upholstery/upholstery_category.py` | **create** |
| 2 | `models/tables/upholstery/upholstery.py` | **modify** — add `upholstery_category_id` FK column |
| 3 | `app/migrations/versions/<rev>_add_upholstery_category.py` | **generate via alembic autogenerate** |
| 4 | `domain/upholstery/serializers.py` | **modify** — add `serialize_upholstery_category`; update `serialize_upholstery` signature |
| 5 | `services/commands/upholstery/requests/__init__.py` | **modify** — add 3 new request models; extend 2 existing models |
| 6 | `services/commands/upholstery/create_upholstery_category.py` | **create** |
| 7 | `services/commands/upholstery/update_upholstery_category.py` | **create** |
| 8 | `services/commands/upholstery/delete_upholstery_category.py` | **create** |
| 9 | `services/commands/upholstery/mark_upholstery_category_favorite.py` | **create** |
| 10 | `services/commands/upholstery/create_upholstery.py` | **modify** — accept + persist `upholstery_category_id` |
| 11 | `services/commands/upholstery/update_upholstery.py` | **modify** — accept + persist `upholstery_category_id` |
| 12 | `services/queries/upholstery/upholstery_categories.py` | **create** — `get_upholstery_category`, `list_upholstery_categories` |
| 13 | `services/queries/upholstery/upholsteries.py` | **modify** — `list_upholsteries` gains category filter + batch category load; `get_upholstery` loads and passes category |
| 14 | `routers/api_v1/upholstery_categories.py` | **create** |
| 15 | `routers/api_v1/upholsteries.py` | **modify** — create/update bodies gain `upholstery_category_id`; list route gains `upholstery_category_ids` param |
| 16 | `routers/api_v1/__init__.py` | **modify** — import + register `upholstery_categories` router |
| 17 | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_upholstery_category_20260622.md` | **create** |

### Out of scope

- Hard-delete of categories (soft-delete only, consistent with codebase).
- Cascade-null `upholstery_category_id` on linked upholsteries when a category is soft-deleted — Postgres FK `ondelete="RESTRICT"` constraint is a safety net only; application only soft-deletes. The serializer silently returns `upholstery_category: null` for deleted categories since the batch load filters `is_deleted.is_(False)`.
- Any change to `upholstery_inventory`, `upholstery_order`, or supplier tables/commands.

### Assumptions

1. **`workspace_id` is required on `UpholsteryCategory`** even though not listed in the intent spec — all workspace-scoped entities carry it (see `Upholstery`, `UpholsteryInventory`). Do not omit it.
2. **Category names are unique within a workspace** (same uniqueness convention as `Upholstery.name`).
3. **`upholstery_category_id` on `Upholstery` is nullable.** Existing upholsteries have no category after migration. No backfill needed.
4. **`serialize_upholstery` change applies to both `get_upholstery` and `list_upholsteries`.** The `list_upholsteries` query will batch-load categories (one extra query, no N+1), so all list items also carry the `upholstery_category` key.
5. **`list_upholstery_categories` `q` filter searches `UpholsteryCategory.name` only** — category has no `code` field; the "same string columns as `list_upholsteries`" means the same ilike approach applied to the string columns that exist on this entity.
6. **`in_stock` filter is NOT carried over to `list_upholstery_categories`** — it is upholstery-inventory-specific and has no meaning on the category entity.
7. The migration must be generated with `alembic revision --autogenerate`, not hand-written.

---

## Clarifications required

- None — all decisions are unambiguous from the intent specification and the existing codebase patterns.

---

## Acceptance criteria

1. `PUT /api/v1/upholstery-categories` creates an `UpholsteryCategory` in a single transaction; returns `{"upholstery_category": serialize_upholstery_category(cat)}`.
2. `GET /api/v1/upholstery-categories` supports `limit`, `offset`, `q` (ilike on `name`), `favorite`; response includes `upholstery_categories_pagination`; each item includes `upholstery_count` (count of non-deleted upholsteries linked to that category).
3. `GET /api/v1/upholstery-categories/{client_id}` returns a single category; 404 if not found or soft-deleted.
4. `PATCH /api/v1/upholstery-categories/{client_id}` updates `name` and/or `image_url`; raises 409 on duplicate name; returns `{}`.
5. `DELETE /api/v1/upholstery-categories/{client_id}` soft-deletes the category; returns `{}`.
6. `PATCH /api/v1/upholstery-categories/{client_id}/favorite` sets `favorite` on a single category; returns `{"upholstery_category": serialize_upholstery_category(cat)}`.
7. `PUT /api/v1/upholsteries` now accepts optional `upholstery_category_id`; if provided, validates category exists and is not deleted in the workspace; persists the FK.
8. `PATCH /api/v1/upholsteries/{client_id}` now accepts optional `upholstery_category_id`; same validation and persistence.
9. `GET /api/v1/upholsteries` now accepts `upholstery_category_ids: str` (comma-separated); when provided, filters to upholsteries whose `upholstery_category_id` is in the parsed list.
10. `GET /api/v1/upholsteries/{client_id}` and `GET /api/v1/upholsteries` both return a `upholstery_category` key: `{"id": ..., "name": ..., "image_url": ...}` or `null`.
11. Alembic migration applies cleanly with `alembic upgrade head`; `alembic check` reports no pending migration after apply.
12. `python -c "from beyo_manager.routers.api_v1 import upholstery_categories"` passes without error.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: command skeleton, `async with ctx.session.begin()`, request parser shape, no cross-command calls, event dispatch only after commit
- `backend/architecture/06_commands_local.md`: `maybe_begin` noted but NOT used here — all new commands own their transactions directly
- `backend/architecture/07_queries.md`: query signature, `select()` pattern, serialization, batch-load pattern
- `backend/architecture/07_queries_local.md`: offset-based pagination overrides cursor; `_MAX_LIMIT = 200`, `_DEFAULT_LIMIT = 50`; pagination key shape is `{"has_more": bool, "limit": int, "offset": int}`
- `backend/architecture/09_routers.md`: router skeleton, static routes before wildcard `/{client_id}`, path param injection, HTTP method conventions, `build_ok`/`build_err`
- `backend/architecture/03_models.md`: SQLAlchemy mapped_column patterns, `IdentityMixin`, `Base`
- `backend/architecture/30_migrations.md`: Alembic autogenerate flow

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination replaces cursor; pagination key shape `{"has_more": bool, "limit": int, "offset": int}`

### File read intent — pattern vs. relational

Permitted relational reads (Codex may read these to understand what already exists):
- `models/tables/upholstery/upholstery.py` — exact field names, FK conventions, index patterns
- `models/base/identity.py` — `IdentityMixin` signature
- `domain/upholstery/serializers.py` — existing `serialize_upholstery` signature to extend
- `services/commands/upholstery/requests/__init__.py` — existing request models to append to
- `services/commands/upholstery/create_upholstery.py` — current logic to extend (not to copy the command pattern; pattern comes from `06_commands.md`)
- `services/commands/upholstery/update_upholstery.py` — current logic to extend
- `services/queries/upholstery/upholsteries.py` — current query to extend
- `routers/api_v1/upholsteries.py` — current router to extend; reference for body model shape
- `routers/api_v1/__init__.py` — to identify where to insert the new import and `include_router` line

Prohibited (pattern reads — use the contract instead):
- Any other command file to understand `session.add` / flush pattern → `06_commands.md`
- Any other router file to understand handler skeleton → `09_routers.md`
- Any other serializer to understand output shape → `46_serialization.md`

### Skill selection

- Primary skill: CRUD goal bundle from `backend_contract_goal_mapping_guide.md`
- Trigger terms matched: `"search"`, `"ilike"`, `"partial match"` → contract `55` not loaded; the filter is a simple ilike on `name` (single column, no FTS), covered entirely by `07_queries.md`
- Excluded: worker-driven, replayable async, CI-validated runtime

---

## Implementation plan

> **Execute the steps in order.** Each step names the exact file to create or modify and gives the complete expected shape. Do not skip steps or reorder them — later steps depend on earlier ones.

---

### Step 1 — Create `UpholsteryCategory` model

**File:** `app/beyo_manager/models/tables/upholstery/upholstery_category.py` *(new file)*

```python
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class UpholsteryCategory(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "upc"
    __tablename__ = "upholstery_categories"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
        UniqueConstraint("workspace_id", "name", name="uq_upholstery_categories_workspace_name"),
        Index("ix_upholstery_categories_workspace_favorite", "workspace_id", "favorite"),
    )
```

---

### Step 2 — Add `upholstery_category_id` FK to `Upholstery` model

**File:** `app/beyo_manager/models/tables/upholstery/upholstery.py` *(modify)*

Add one column after `favorite`:

```python
upholstery_category_id: Mapped[str | None] = mapped_column(
    String(64),
    ForeignKey("upholstery_categories.client_id", ondelete="RESTRICT"),
    nullable=True,
    index=True,
)
```

No other changes to this file.

---

### Step 3 — Generate Alembic migration

Run from the `app/` directory (where `alembic.ini` lives):

```bash
alembic revision --autogenerate -m "add_upholstery_category"
```

**Verify** the generated file in `migrations/versions/` contains:
- `op.create_table("upholstery_categories", ...)` with all columns from Step 1
- `op.add_column("upholsteries", sa.Column("upholstery_category_id", sa.String(64), nullable=True))`
- `op.create_foreign_key(...)` from `upholsteries.upholstery_category_id` to `upholstery_categories.client_id`
- `op.create_index(...)` for `upholstery_category_id` on `upholsteries`

Then apply:

```bash
alembic upgrade head
```

If autogenerate produces extra noise (e.g., detects unrelated changes), keep only the two operations above and remove the noise.

---

### Step 4 — Add `serialize_upholstery_category` and update `serialize_upholstery`

**File:** `app/beyo_manager/domain/upholstery/serializers.py` *(modify)*

**4a — New import at the top of the file:**

```python
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
```

**4b — New function `serialize_upholstery_category` — append after existing functions:**

```python
def serialize_upholstery_category(
    cat: UpholsteryCategory,
    upholstery_count: int | None = None,
) -> dict:
    result = {
        "client_id": cat.client_id,
        "workspace_id": cat.workspace_id,
        "name": cat.name,
        "image_url": cat.image_url,
        "favorite": cat.favorite,
        "created_at": cat.created_at.isoformat(),
        "created_by_id": cat.created_by_id,
        "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
        "updated_by_id": cat.updated_by_id,
        "is_deleted": cat.is_deleted,
    }
    if upholstery_count is not None:
        result["upholstery_count"] = upholstery_count
    return result
```

**4c — Update `serialize_upholstery` signature and body:**

Change the function signature from:
```python
def serialize_upholstery(
    row: Upholstery,
    inventory: UpholsteryInventory | None = None,
) -> dict:
```
to:
```python
def serialize_upholstery(
    row: Upholstery,
    inventory: UpholsteryInventory | None = None,
    category: UpholsteryCategory | None = None,
) -> dict:
```

Add a `upholstery_category` key to the returned dict. The final `return` statement must produce:

```python
return {
    "client_id": row.client_id,
    "name": row.name,
    "code": row.code,
    "image_url": row.image_url,
    "favorite": row.favorite,
    "list_order": row.list_order,
    "current_stored_amount_meters": available_stored_amount,
    "inventory_condition": inventory.inventory_condition.value if inventory is not None else None,
    "upholstery_category": {
        "id": category.client_id,
        "name": category.name,
        "image_url": category.image_url,
    } if category is not None else None,
}
```

Do not change the `available_stored_amount` computation logic above the return statement.

---

### Step 5 — Add category request models and extend upholstery request models

**File:** `app/beyo_manager/services/commands/upholstery/requests/__init__.py` *(modify)*

**5a — Append three new request models at the end of the file:**

```python
class CreateUpholsteryCategoryRequest(BaseModel):
    client_id: str | None = None
    name: str
    image_url: str | None = None
    favorite: bool = False

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("name must not be blank.")
        return value


def parse_create_upholstery_category_request(data: dict) -> CreateUpholsteryCategoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return CreateUpholsteryCategoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class UpdateUpholsteryCategoryRequest(BaseModel):
    client_id: str
    name: str | None = None
    image_url: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        value = v.strip()
        if not value:
            raise ValueError("name must not be blank.")
        return value


def parse_update_upholstery_category_request(data: dict) -> UpdateUpholsteryCategoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return UpdateUpholsteryCategoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class DeleteUpholsteryCategoryRequest(BaseModel):
    client_id: str


def parse_delete_upholstery_category_request(data: dict) -> DeleteUpholsteryCategoryRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return DeleteUpholsteryCategoryRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


class MarkUpholsteryCategoryFavoriteRequest(BaseModel):
    client_id: str
    favorite: bool


def parse_mark_upholstery_category_favorite_request(data: dict) -> MarkUpholsteryCategoryFavoriteRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return MarkUpholsteryCategoryFavoriteRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

**5b — Extend existing `CreateUpholsteryRequest` with `upholstery_category_id`:**

Add one field to `CreateUpholsteryRequest` (after `planning_position`):
```python
upholstery_category_id: str | None = None
```
No validator needed. The command will validate existence at runtime.

**5c — Extend existing `UpdateUpholsteryRequest` with `upholstery_category_id`:**

Add one field to `UpdateUpholsteryRequest` (after `favorite`):
```python
upholstery_category_id: str | None = None
```
No validator needed.

---

### Step 6 — Command: `create_upholstery_category.py`

**File:** `app/beyo_manager/services/commands/upholstery/create_upholstery_category.py` *(new file)*

```python
from sqlalchemy import select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_category
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.commands.upholstery.requests import (
    parse_create_upholstery_category_request,
)
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext


async def create_upholstery_category(ctx: ServiceContext) -> dict:
    request = parse_create_upholstery_category_request(ctx.incoming_data)

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "upc")

    async with ctx.session.begin():
        if request.client_id is not None:
            dup = await ctx.session.get(UpholsteryCategory, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")

        name_conflict = await ctx.session.execute(
            select(UpholsteryCategory).where(
                UpholsteryCategory.workspace_id == ctx.workspace_id,
                UpholsteryCategory.name == request.name,
                UpholsteryCategory.is_deleted.is_(False),
            )
        )
        if name_conflict.scalar_one_or_none() is not None:
            raise ConflictError("An upholstery category with this name already exists in the workspace.")

        cat_kwargs: dict = {}
        if request.client_id is not None:
            cat_kwargs["client_id"] = request.client_id

        category = UpholsteryCategory(
            **cat_kwargs,
            workspace_id=ctx.workspace_id,
            name=request.name,
            image_url=request.image_url,
            favorite=request.favorite,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(category)

    return {"upholstery_category": serialize_upholstery_category(category)}
```

---

### Step 7 — Command: `update_upholstery_category.py`

**File:** `app/beyo_manager/services/commands/upholstery/update_upholstery_category.py` *(new file)*

```python
from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.commands.upholstery.requests import (
    parse_update_upholstery_category_request,
)
from beyo_manager.services.context import ServiceContext


async def update_upholstery_category(ctx: ServiceContext) -> dict:
    request = parse_update_upholstery_category_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(UpholsteryCategory).where(
                UpholsteryCategory.workspace_id == ctx.workspace_id,
                UpholsteryCategory.client_id == request.client_id,
                UpholsteryCategory.is_deleted.is_(False),
            )
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise NotFound("Upholstery category not found.")

        if request.name is not None and request.name != category.name:
            name_conflict = await ctx.session.execute(
                select(UpholsteryCategory).where(
                    UpholsteryCategory.workspace_id == ctx.workspace_id,
                    UpholsteryCategory.name == request.name,
                    UpholsteryCategory.is_deleted.is_(False),
                    UpholsteryCategory.client_id != category.client_id,
                )
            )
            if name_conflict.scalar_one_or_none() is not None:
                raise ConflictError("An upholstery category with this name already exists in the workspace.")

        if request.name is not None:
            category.name = request.name
        if request.image_url is not None:
            category.image_url = request.image_url

        category.updated_by_id = ctx.user_id

    return {}
```

---

### Step 8 — Command: `delete_upholstery_category.py`

**File:** `app/beyo_manager/services/commands/upholstery/delete_upholstery_category.py` *(new file)*

```python
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.commands.upholstery.requests import (
    parse_delete_upholstery_category_request,
)
from beyo_manager.services.context import ServiceContext


async def delete_upholstery_category(ctx: ServiceContext) -> dict:
    request = parse_delete_upholstery_category_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(UpholsteryCategory).where(
                UpholsteryCategory.workspace_id == ctx.workspace_id,
                UpholsteryCategory.client_id == request.client_id,
                UpholsteryCategory.is_deleted.is_(False),
            )
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise NotFound("Upholstery category not found.")

        category.is_deleted = True
        category.deleted_at = datetime.now(timezone.utc)
        category.deleted_by_id = ctx.user_id

    return {}
```

Note: Linked upholsteries retain their `upholstery_category_id` FK after soft-delete. The serializer returns `upholstery_category: null` for those upholsteries because the batch-load query filters `is_deleted.is_(False)`. No application-layer cascade is needed.

---

### Step 9 — Command: `mark_upholstery_category_favorite.py`

**File:** `app/beyo_manager/services/commands/upholstery/mark_upholstery_category_favorite.py` *(new file)*

```python
from sqlalchemy import select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_category
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.commands.upholstery.requests import (
    parse_mark_upholstery_category_favorite_request,
)
from beyo_manager.services.context import ServiceContext


async def mark_upholstery_category_favorite(ctx: ServiceContext) -> dict:
    request = parse_mark_upholstery_category_favorite_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(UpholsteryCategory).where(
                UpholsteryCategory.workspace_id == ctx.workspace_id,
                UpholsteryCategory.client_id == request.client_id,
                UpholsteryCategory.is_deleted.is_(False),
            )
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise NotFound("Upholstery category not found.")

        category.favorite = request.favorite
        category.updated_by_id = ctx.user_id

    return {"upholstery_category": serialize_upholstery_category(category)}
```

---

### Step 10 — Query: `upholstery_categories.py`

**File:** `app/beyo_manager/services/queries/upholstery/upholstery_categories.py` *(new file)*

```python
"""QUERY-1: List Upholstery Categories | QUERY-2: Get Upholstery Category by ID."""

from sqlalchemy import func, or_, select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_category
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_upholstery_categories(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    favorite_raw = ctx.query_params.get("favorite")

    # Left outer join to count non-deleted linked upholsteries per category.
    stmt = (
        select(
            UpholsteryCategory,
            func.count(Upholstery.client_id).label("upholstery_count"),
        )
        .outerjoin(
            Upholstery,
            (Upholstery.upholstery_category_id == UpholsteryCategory.client_id)
            & (Upholstery.workspace_id == ctx.workspace_id)
            & (Upholstery.is_deleted.is_(False)),
        )
        .where(
            UpholsteryCategory.workspace_id == ctx.workspace_id,
            UpholsteryCategory.is_deleted.is_(False),
        )
        .group_by(UpholsteryCategory.client_id)
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                UpholsteryCategory.name.ilike(pattern),
            )
        )

    if favorite_raw is not None:
        favorite = str(favorite_raw).strip().lower() == "true"
        stmt = stmt.where(UpholsteryCategory.favorite.is_(favorite))

    stmt = (
        stmt.order_by(
            UpholsteryCategory.favorite.desc(),
            UpholsteryCategory.created_at.asc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )

    result = await ctx.session.execute(stmt)
    rows = result.all()  # list of (UpholsteryCategory, int) tuples

    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "upholstery_categories": [
            serialize_upholstery_category(cat, upholstery_count=count)
            for cat, count in page
        ],
        "upholstery_categories_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_upholstery_category(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(UpholsteryCategory).where(
            UpholsteryCategory.workspace_id == ctx.workspace_id,
            UpholsteryCategory.client_id == client_id,
            UpholsteryCategory.is_deleted.is_(False),
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise NotFound("Upholstery category not found.")

    return {"upholstery_category": serialize_upholstery_category(category)}
```

Note on `q` filter: The `or_()` wraps a single condition intentionally. When a `code` or other string column is added to `UpholsteryCategory` in the future, add it inside the `or_()` without changing the surrounding structure.

---

### Step 11 — Router: `upholstery_categories.py`

**File:** `app/beyo_manager/routers/api_v1/upholstery_categories.py` *(new file)*

Route declaration order — static routes before wildcard `/{client_id}`:

```
PUT    ""                              → create_upholstery_category          roles: ADMIN, MANAGER
GET    ""                              → list_upholstery_categories           roles: ADMIN, MANAGER, WORKER
GET    "/{client_id}"                  → get_upholstery_category             roles: ADMIN, MANAGER, WORKER
PATCH  "/{client_id}"                  → update_upholstery_category          roles: ADMIN, MANAGER
DELETE "/{client_id}"                  → delete_upholstery_category          roles: ADMIN, MANAGER
PATCH  "/{client_id}/favorite"         → mark_upholstery_category_favorite   roles: ADMIN, MANAGER
```

```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.upholstery.create_upholstery_category import (
    create_upholstery_category,
)
from beyo_manager.services.commands.upholstery.delete_upholstery_category import (
    delete_upholstery_category,
)
from beyo_manager.services.commands.upholstery.mark_upholstery_category_favorite import (
    mark_upholstery_category_favorite,
)
from beyo_manager.services.commands.upholstery.update_upholstery_category import (
    update_upholstery_category,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.upholstery_categories import (
    get_upholstery_category,
    list_upholstery_categories,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/upholstery-categories", tags=["upholstery-categories"])


class _CreateBody(BaseModel):
    client_id: str | None = None
    name: str
    image_url: str | None = None
    favorite: bool = False


class _UpdateBody(BaseModel):
    name: str | None = None
    image_url: str | None = None


class _FavoriteBody(BaseModel):
    favorite: bool


@router.put("")
async def route_create_upholstery_category(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_upholstery_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_upholstery_categories(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    favorite: bool | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "favorite": favorite,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholstery_categories, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_upholstery_category(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(get_upholstery_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_upholstery_category(
    client_id: str,
    body: _UpdateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    data = body.model_dump()
    data["client_id"] = client_id
    ctx = ServiceContext(incoming_data=data, identity=claims, session=session)
    outcome = await run_service(update_upholstery_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_upholstery_category(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(delete_upholstery_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}/favorite")
async def route_mark_upholstery_category_favorite(
    client_id: str,
    body: _FavoriteBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, "favorite": body.favorite},
        identity=claims,
        session=session,
    )
    outcome = await run_service(mark_upholstery_category_favorite, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

### Step 12 — Register `upholstery_categories` router in `__init__.py`

**File:** `app/beyo_manager/routers/api_v1/__init__.py` *(modify)*

**12a — Add import** alongside the other upholstery imports (alphabetical order):
```python
from beyo_manager.routers.api_v1 import upholstery_categories
```

**12b — Add `include_router` call** inside `register_v1_routers`, immediately before the existing `upholsteries.router` line:
```python
app.include_router(upholstery_categories.router)
```

The prefix `"/api/v1/upholstery-categories"` is defined on the router itself; do not pass a `prefix` argument here.

---

### Step 13 — Update `create_upholstery.py` to accept and persist `upholstery_category_id`

**File:** `app/beyo_manager/services/commands/upholstery/create_upholstery.py` *(modify)*

**13a — New import** (add to existing imports):
```python
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
```

**13b — Category validation block** — insert inside `async with ctx.session.begin():`, after the `code` uniqueness check and before creating the `Upholstery` instance:

```python
if request.upholstery_category_id is not None:
    cat_result = await ctx.session.execute(
        select(UpholsteryCategory).where(
            UpholsteryCategory.workspace_id == ctx.workspace_id,
            UpholsteryCategory.client_id == request.upholstery_category_id,
            UpholsteryCategory.is_deleted.is_(False),
        )
    )
    if cat_result.scalar_one_or_none() is None:
        raise NotFound("Upholstery category not found.")
```

Import `NotFound` from `beyo_manager.errors.not_found` — it is already imported in some upholstery commands; add it here if not present.

**13c — Pass `upholstery_category_id` to the `Upholstery` constructor:**

In the `Upholstery(...)` instantiation, add:
```python
upholstery_category_id=request.upholstery_category_id,
```

**13d — Pass `category` to `serialize_upholstery` in the return statement.**

After the `async with` block ends, load the category if one was set:

```python
category = None
if request.upholstery_category_id is not None:
    cat_res = await ctx.session.execute(
        select(UpholsteryCategory).where(
            UpholsteryCategory.client_id == request.upholstery_category_id,
        )
    )
    category = cat_res.scalar_one_or_none()

return {"upholstery": serialize_upholstery(upholstery, inventory, category)}
```

Note: the transaction is already committed at this point (exited `async with`). The category select runs outside the transaction, which is correct for a read-only fetch.

---

### Step 14 — Update `update_upholstery.py` to accept and persist `upholstery_category_id`

**File:** `app/beyo_manager/services/commands/upholstery/update_upholstery.py` *(modify)*

**14a — New imports:**
```python
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.errors.not_found import NotFound  # already present; ensure it is imported
```

**14b — Category validation block** — insert inside `async with ctx.session.begin():`, after the `code` conflict check and before the field-assignment block:

```python
if request.upholstery_category_id is not None:
    cat_result = await ctx.session.execute(
        select(UpholsteryCategory).where(
            UpholsteryCategory.workspace_id == ctx.workspace_id,
            UpholsteryCategory.client_id == request.upholstery_category_id,
            UpholsteryCategory.is_deleted.is_(False),
        )
    )
    if cat_result.scalar_one_or_none() is None:
        raise NotFound("Upholstery category not found.")
```

**14c — Add field assignment** in the existing `if request.X is not None: upholstery.X = ...` block:

```python
if request.upholstery_category_id is not None:
    upholstery.upholstery_category_id = request.upholstery_category_id
```

**No change to the return value.** `update_upholstery` returns `{}`. This is correct and must not be changed.

---

### Step 15 — Update `upholsteries.py` (queries) — category filter + batch load

**File:** `app/beyo_manager/services/queries/upholstery/upholsteries.py` *(modify)*

**15a — New imports at the top:**
```python
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
```

**15b — `list_upholsteries` changes:**

Add extraction of the new query param after the existing `favorite_raw` line:
```python
upholstery_category_ids_raw = ctx.query_params.get("upholstery_category_ids")
```

Add filter block after the `favorite` filter block and before the `stmt.order_by` call:
```python
if upholstery_category_ids_raw:
    ids = [i.strip() for i in str(upholstery_category_ids_raw).split(",") if i.strip()]
    if ids:
        stmt = stmt.where(Upholstery.upholstery_category_id.in_(ids))
```

Add category batch-load after the existing `inventory_map` batch-load block (after the `if page:` / `inv_result` block):

```python
category_ids = {u.upholstery_category_id for u in page if u.upholstery_category_id is not None}
category_map: dict[str, UpholsteryCategory] = {}
if category_ids:
    cat_result = await ctx.session.execute(
        select(UpholsteryCategory).where(
            UpholsteryCategory.client_id.in_(category_ids),
            UpholsteryCategory.is_deleted.is_(False),
        )
    )
    category_map = {cat.client_id: cat for cat in cat_result.scalars().all()}
```

Update the final `return` statement to pass `category` to `serialize_upholstery`:

```python
return {
    "upholsteries": [
        serialize_upholstery(u, inventory_map.get(u.client_id), category_map.get(u.upholstery_category_id))
        for u in page
    ],
    "upholsteries_pagination": {
        "has_more": has_more,
        "limit": limit,
        "offset": offset,
    },
}
```

**15c — `get_upholstery` changes:**

After loading `inventory`, add a category fetch:

```python
category = None
if upholstery.upholstery_category_id is not None:
    cat_result = await ctx.session.execute(
        select(UpholsteryCategory).where(
            UpholsteryCategory.client_id == upholstery.upholstery_category_id,
            UpholsteryCategory.is_deleted.is_(False),
        )
    )
    category = cat_result.scalar_one_or_none()
```

Update the return statement:
```python
return {"upholstery": serialize_upholstery(upholstery, inventory, category)}
```

---

### Step 16 — Update `upholsteries.py` (router) — bodies + query param

**File:** `app/beyo_manager/routers/api_v1/upholsteries.py` *(modify)*

**16a — Add `upholstery_category_id` to `_CreateBody`:**
```python
upholstery_category_id: str | None = None
```
(append after `planning_position`)

**16b — Add `upholstery_category_id` to `_UpdateBody`:**
```python
upholstery_category_id: str | None = None
```
(append after `favorite`)

**16c — Add `upholstery_category_ids` query param to `route_list_upholsteries`:**

In the `route_list_upholsteries` function signature, add after `favorite`:
```python
upholstery_category_ids: str | None = Query(None),
```

Add `"upholstery_category_ids": upholstery_category_ids` to the `query_params` dict passed to `ServiceContext`.

No other changes to this file.

---

### Step 17 — Write frontend handoff document

**File:** `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_upholstery_category_20260622.md` *(new file)*

Use the template at `docs/handoff/to_frontend/TEMPLATE_HANDOFF_TO_FRONTEND.md` and the style of `HANDOFF_TO_FRONTEND_upholstery_update_endpoints_20260618.md` as reference.

The document must cover all endpoints below. For each endpoint provide: HTTP method + path, auth roles, full request shape (JSON), complete response shape (JSON with all keys), and all error cases.

**Endpoints to document:**

**Upholstery Category — new endpoints:**
1. `PUT /api/v1/upholstery-categories`
2. `GET /api/v1/upholstery-categories` (with pagination and filters)
3. `GET /api/v1/upholstery-categories/{client_id}`
4. `PATCH /api/v1/upholstery-categories/{client_id}`
5. `DELETE /api/v1/upholstery-categories/{client_id}`
6. `PATCH /api/v1/upholstery-categories/{client_id}/favorite`

**Upholstery — changed endpoints:**
7. `PUT /api/v1/upholsteries` — new optional `upholstery_category_id` field; `upholstery_category` key in response
8. `PATCH /api/v1/upholsteries/{client_id}` — new optional `upholstery_category_id` field
9. `GET /api/v1/upholsteries` — new `upholstery_category_ids` query param; `upholstery_category` key in each list item
10. `GET /api/v1/upholsteries/{client_id}` — `upholstery_category` key in response

For the `serialize_upholstery_category` response shape (used in `PUT`, `GET /{id}`, `PATCH /{id}/favorite`):
```json
{
  "client_id": "upc_01...",
  "workspace_id": "wsp_01...",
  "name": "Velvet",
  "image_url": "https://cdn.example.com/velvet.jpg",
  "favorite": false,
  "created_at": "2026-06-22T10:00:00+00:00",
  "created_by_id": "usr_01...",
  "updated_at": null,
  "updated_by_id": null,
  "is_deleted": false
}
```

For the `list_upholstery_categories` item shape (includes `upholstery_count`):
```json
{
  "client_id": "upc_01...",
  "workspace_id": "wsp_01...",
  "name": "Velvet",
  "image_url": "https://cdn.example.com/velvet.jpg",
  "favorite": false,
  "created_at": "2026-06-22T10:00:00+00:00",
  "created_by_id": "usr_01...",
  "updated_at": null,
  "updated_by_id": null,
  "is_deleted": false,
  "upholstery_count": 3
}
```

For the `upholstery_category` nested key in `serialize_upholstery`:
```json
"upholstery_category": {
  "id": "upc_01...",
  "name": "Velvet",
  "image_url": "https://cdn.example.com/velvet.jpg"
}
```
or `"upholstery_category": null` when no category is linked.

---

## Risks and mitigations

- **Risk:** `alembic autogenerate` detects unrelated schema drift from other pending model changes.
  **Mitigation:** Inspect the generated migration before applying. Keep only the two operations for `upholstery_categories` table creation and `upholstery_category_id` FK column on `upholsteries`. Remove any unrelated ops.

- **Risk:** After category soft-delete, linked upholsteries retain a stale `upholstery_category_id`. The serializer returns `upholstery_category: null`, which may confuse the frontend if it tries to display a category for those upholsteries.
  **Mitigation:** Document in the handoff that `upholstery_category: null` means either "no category" or "category was deleted". The frontend should treat both as "no category" for display purposes.

- **Risk:** The `list_upholstery_categories` GROUP BY query returns `(UpholsteryCategory, int)` tuples, not plain ORM instances. Using `result.scalars()` instead of `result.all()` would silently drop the count.
  **Mitigation:** In the query, use `result.all()` (not `result.scalars()`). Each row is a `Row` named tuple; access it as `cat, count = row` or `cat, count in page`.

- **Risk:** SQLAlchemy `select(UpholsteryCategory, func.count(...))` requires `group_by(UpholsteryCategory.client_id)` — omitting it will raise a DB error on Postgres.
  **Mitigation:** The plan includes the `.group_by(UpholsteryCategory.client_id)` call explicitly.

- **Risk:** `serialize_upholstery` is called from multiple places (commands, queries). Changing its signature with a new optional parameter is backward-compatible; existing callers that do not pass `category` continue to work and receive `upholstery_category: null`.
  **Mitigation:** New parameter is `category: UpholsteryCategory | None = None` — default `None`. No existing callsite needs updating except the ones explicitly listed in Steps 13, 15.

---

## Validation plan

Run all of these in order after implementation:

```bash
# Import checks
python -c "from beyo_manager.routers.api_v1 import upholstery_categories"
python -c "from beyo_manager.services.queries.upholstery import upholstery_categories"
python -c "from beyo_manager.domain.upholstery.serializers import serialize_upholstery_category"

# Migration
alembic check  # should report no pending migrations
```

Manual API checks (requires running server and valid JWT):

- `PUT /api/v1/upholstery-categories` `{"name": "Velvet"}` → returns `upholstery_category.client_id` starting with `upc_`
- `PUT /api/v1/upholstery-categories` same name → `409`
- `GET /api/v1/upholstery-categories` → list with `upholstery_categories_pagination` key; each item has `upholstery_count`
- `GET /api/v1/upholstery-categories?q=vel` → only categories matching `name` ilike `%vel%`
- `GET /api/v1/upholstery-categories?favorite=true` → only favorited categories
- `PATCH /api/v1/upholstery-categories/{id}/favorite` `{"favorite": true}` → returns `upholstery_category.favorite = true`
- `GET /api/v1/upholstery-categories/{id}` → returns single category; `404` for unknown id
- `PATCH /api/v1/upholstery-categories/{id}` `{"name": "Leather"}` → returns `{}`; subsequent GET shows updated name
- `DELETE /api/v1/upholstery-categories/{id}` → returns `{}`; subsequent GET returns `404`
- `PUT /api/v1/upholsteries` with `upholstery_category_id: "<valid_upc_id>"` → response `upholstery.upholstery_category.id` matches
- `PUT /api/v1/upholsteries` with `upholstery_category_id: "upc_nonexistent"` → `404`
- `GET /api/v1/upholsteries/{id}` for upholstery with category → `upholstery_category` key is `{"id": ..., "name": ..., "image_url": ...}`
- `GET /api/v1/upholsteries/{id}` for upholstery without category → `upholstery_category: null`
- `GET /api/v1/upholsteries?upholstery_category_ids=<id1>,<id2>` → only upholsteries linked to those categories
- `PATCH /api/v1/upholsteries/{id}` with `upholstery_category_id: "<valid_upc_id>"` → updates link; subsequent GET shows category

---

## Review log

- `2026-06-22` `codex`: Implemented the new upholstery category model, migration, commands, queries, routers, frontend handoff, and summary. Applied the migration and resolved unrelated ORM metadata drift for existing upholstery-query indexes so `alembic check` passes cleanly.

---

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`

## Implementation summary

- Added the new `UpholsteryCategory` workspace entity and linked it to `Upholstery` through nullable `upholstery_category_id`.
- Added category CRUD, favorite-toggle, list, and get services plus the `/api/v1/upholstery-categories` router family.
- Extended upholstery create/update/list/get flows with category validation, category filtering, and nested category serialization.
- Generated and applied Alembic migration `183fb6115bd3_add_upholstery_category`, then aligned existing item-upholstery query index metadata so `alembic check` reports no pending upgrade operations.
- Wrote the frontend handoff at `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_upholstery_category_20260622.md` and the implementation summary at `docs/architecture/implemented_summaries/SUMMARY_PLAN_upholstery_category_20260622.md`.
