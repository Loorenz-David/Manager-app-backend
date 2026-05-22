# PLAN_config_list_get_endpoints_20260522

## Metadata

- Plan ID: `PLAN_config_list_get_endpoints_20260522`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-22T00:00:00Z`
- Last updated at (UTC): `2026-05-22T15:39:27Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- **Goal:** Add list + get read endpoints for three configuration entities — `ItemCategory`, `IssueType` + `IssueCategoryConfig`, and `Upholstery` — that frontend form fields call independently to populate option sets.
- **Business/user intent:** Each form field (e.g. "select item category", "select issue type", "select upholstery") fetches its own data independently via a lightweight paginated list with an optional `q` text search and, where applicable, an `image_url` for display.
- **Non-goals:** Create, update, or delete endpoints are out of scope for this plan. `IssueSeverity` is out of scope.

## Scope

- **In scope:**
  - `GET /api/v1/item-categories` and `GET /api/v1/item-categories/{client_id}`
  - `GET /api/v1/issue-types` and `GET /api/v1/issue-types/{client_id}`
  - `GET /api/v1/issue-category-configs` and `GET /api/v1/issue-category-configs/{client_id}`
  - `GET /api/v1/upholsteries` and `GET /api/v1/upholsteries/{client_id}`
  - New `ImageLinkEntityTypeEnum` values: `ITEM_CATEGORY` and `UPHOLSTERY`
  - Alembic migration to extend the `image_link_entity_type_enum` Postgres enum
  - Serializers for each entity in their respective domain modules
  - Service query functions with batch image loading (no N+1)

- **Out of scope:**
  - Any command (write) endpoints
  - `IssueSeverity` endpoints
  - Adding image upload/link logic for item categories or upholsteries
  - `IssueCategoryConfig` create/update/link management

- **Assumptions:**
  - Images for `ItemCategory` and `Upholstery` may already be linked via `ImageLink` rows (e.g. imported externally). The endpoints must serve them correctly once the enum values and migration are in place.
  - `IssueCategoryConfig` has no image.
  - The `q` search param on `IssueCategoryConfig` list filters on `IssueType.name` via SQL join.
  - For `IssueCategoryConfig` list, an optional `item_category_id` query param is supported to allow the frontend to retrieve only configs relevant to a specific category.

## Clarifications required

*(none — requirements are fully specified)*

## Acceptance criteria

1. `GET /api/v1/item-categories?q=wood&limit=20&offset=0` returns a paginated list with `item_categories` and `item_categories_pagination` keys; `image_url` is a presigned URL string or `null`; workspace isolation is enforced.
2. `GET /api/v1/item-categories/{client_id}` returns `{"item_category": {...}}` or 404; `image_url` is resolved.
3. `GET /api/v1/issue-types?q=scratch` returns paginated `issue_types` + `issue_types_pagination`.
4. `GET /api/v1/issue-category-configs?q=scratch&item_category_id=itc_xxx` returns paginated configs with `issue_type_name` embedded; `issue_category_configs_pagination` present.
5. `GET /api/v1/upholsteries?q=linen` returns paginated `upholsteries` + `upholsteries_pagination`; `image_url` resolved.
6. No N+1 queries on list endpoints: images are loaded in a single batch query per list page.
7. All list endpoints enforce `workspace_id` as the first `where()` condition and exclude soft-deleted records.
8. Router `__init__.py` registers all new routers. Application starts without error.

## Contracts and skills

### Contracts loaded

- `backend/architecture/07_queries.md`: query signature, workspace scope, eager loading rules
- `backend/architecture/07_queries_local.md`: **offset-based pagination replaces cursor-based** — use this pattern exclusively
- `backend/architecture/09_routers.md`: router skeleton, handler shape, route declaration order, path param injection
- `backend/architecture/46_serialization.md`: serializer placement in `domain/<domain>/serializers.py`, pure functions, no DB access

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination, completion gate checklist

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

Prohibited (use contracts instead):
- Reading another query to understand `select()` / pagination shape → `07_queries_local.md`
- Reading another router to understand handler wiring → `09_routers.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted relational reads (explicitly allowed):
- `models/tables/items/item_category.py` — exact field names and types
- `models/tables/issue_types/issue_type.py` — exact field names and types
- `models/tables/issue_types/issue_category_config.py` — exact field names and types
- `models/tables/upholstery/upholstery.py` — exact field names and types
- `models/tables/images/image_link.py` — entity_type column, ImageLink structure
- `domain/images/enums.py` — current `ImageLinkEntityTypeEnum` values (to add new ones)
- `domain/images/serializers.py` — `serialize_image_light` signature (to call it correctly)
- `routers/api_v1/__init__.py` — to know where to register new routers
- `routers/api_v1/item_upholsteries.py` — to know where to add `upholstery_router`
- `services/queries/upholstery/` — to know existing file names so the new file does not conflict

### Skill selection

- Primary skill: `backend/architecture/07_queries_local.md` (list query pattern)
- Router trigger terms: `list`, `get`, `configuration`, `item_categories`, `issue_types`, `upholsteries`
- Excluded alternatives: command skill — no writes in scope

## Implementation plan

Execute steps in order. Each step is atomic and independently reviewable. Do not proceed to the next step until the current one is complete.

---

### Step 1 — Extend `ImageLinkEntityTypeEnum` and generate Alembic migration

**File:** `backend/app/beyo_manager/domain/images/enums.py`

Add two new values to `ImageLinkEntityTypeEnum`:

```python
class ImageLinkEntityTypeEnum(StrEnum):
    ITEM = "item"
    CASE = "case"
    CASE_CONVERSATION_MESSAGE = "case_conversation_message"
    ITEM_CATEGORY = "item_category"   # NEW
    UPHOLSTERY = "upholstery"         # NEW
```

**Migration:** Generate an Alembic migration (auto or manual) that issues:

```sql
ALTER TYPE image_link_entity_type_enum ADD VALUE IF NOT EXISTS 'item_category';
ALTER TYPE image_link_entity_type_enum ADD VALUE IF NOT EXISTS 'upholstery';
```

> `ADD VALUE IF NOT EXISTS` is safe for re-runs. Postgres requires these statements to run outside a transaction block — use `op.execute()` with a `connection.execute(text(...))` pattern and set `transaction_per_migration = False` on the migration if required by your alembic config.

---

### Step 2 — Add `serialize_item_category` to `domain/items/serializers.py`

**File:** `backend/app/beyo_manager/domain/items/serializers.py`

Append the following function. Do **not** alter existing functions.

```python
from beyo_manager.domain.images.serializers import serialize_image_light
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.images.image import Image   # import only if not already present


def serialize_item_category(category: ItemCategory, primary_image: "Image | None" = None) -> dict:
    return {
        "client_id": category.client_id,
        "name": category.name,
        "major_category": category.major_category.value,
        "created_at": category.created_at.isoformat(),
        "created_by_id": category.created_by_id,
        "image_url": serialize_image_light(primary_image)["image_url"] if primary_image else None,
    }
```

**Rules:**
- `primary_image` is the raw `Image` ORM object (first by `display_order`), not a dict.
- `serialize_image_light` from `domain/images/serializers.py` handles presigned URL resolution — do not re-implement URL logic here.
- The serializer is a pure function — no DB access.

---

### Step 3 — Create `domain/issue_types/serializers.py`

**File:** `backend/app/beyo_manager/domain/issue_types/serializers.py` *(new file)*

```python
"""Serialization helpers for issue type domain objects."""

from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.models.tables.issue_types.issue_category_config import IssueCategoryConfig


def serialize_issue_type(row: IssueType) -> dict:
    return {
        "client_id": row.client_id,
        "name": row.name,
        "source": row.source.value,
        "created_at": row.created_at.isoformat(),
        "created_by_id": row.created_by_id,
    }


def serialize_issue_category_config(row: IssueCategoryConfig, issue_type_name: str) -> dict:
    return {
        "client_id": row.client_id,
        "item_category_id": row.item_category_id,
        "issue_type_id": row.issue_type_id,
        "base_time_seconds": row.base_time_seconds,
        "issue_type_name": issue_type_name,
    }
```

**Rules:**
- `serialize_issue_category_config` accepts `issue_type_name` as a plain `str` pre-fetched by the query layer — the serializer does not touch the DB.
- No datetime fields are needed in the `IssueCategoryConfig` serialization per spec — do not add them.

---

### Step 4 — Add `serialize_upholstery` to `domain/upholstery/serializers.py`

**File:** `backend/app/beyo_manager/domain/upholstery/serializers.py`

Append the following function after `serialize_upholstery_inventory`. Do **not** rename or alter the existing function.

```python
from beyo_manager.domain.images.serializers import serialize_image_light
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.images.image import Image   # import only if not already present


def serialize_upholstery(row: Upholstery, primary_image: "Image | None" = None) -> dict:
    return {
        "client_id": row.client_id,
        "name": row.name,
        "code": row.code,
        "image_url": serialize_image_light(primary_image)["image_url"] if primary_image else None,
    }
```

---

### Step 5 — Create `services/queries/item_categories/item_categories.py`

**New folder:** `backend/app/beyo_manager/services/queries/item_categories/`
**New files:** `__init__.py` (empty) and `item_categories.py`

```python
"""QUERY-1: List ItemCategories | QUERY-2: Get ItemCategory by ID."""

from sqlalchemy import and_, or_, select

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image_light
from beyo_manager.domain.items.serializers import serialize_item_category
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_item_categories(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

    stmt = select(ItemCategory).where(
        ItemCategory.workspace_id == ctx.workspace_id,
        ItemCategory.is_deleted.is_(False),
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(ItemCategory.name.ilike(pattern))

    stmt = stmt.order_by(ItemCategory.created_at.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    # Batch-load first image per item category — single query, no N+1.
    images_map: dict[str, Image] = {}
    if page:
        category_ids = [cat.client_id for cat in page]
        img_result = await ctx.session.execute(
            select(Image, ImageLink.entity_client_id)
            .join(
                ImageLink,
                and_(
                    ImageLink.image_id == Image.client_id,
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM_CATEGORY,
                    ImageLink.entity_client_id.in_(category_ids),
                ),
            )
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
        )
        for image, entity_id in img_result.all():
            if entity_id not in images_map:          # keep only the first (lowest display_order)
                images_map[entity_id] = image

    return {
        "item_categories": [
            serialize_item_category(cat, images_map.get(cat.client_id)) for cat in page
        ],
        "item_categories_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_item_category(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(ItemCategory).where(
            ItemCategory.workspace_id == ctx.workspace_id,
            ItemCategory.client_id == client_id,
            ItemCategory.is_deleted.is_(False),
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise NotFound("Item category not found.")

    img_result = await ctx.session.execute(
        select(Image)
        .join(
            ImageLink,
            and_(
                ImageLink.image_id == Image.client_id,
                ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM_CATEGORY,
                ImageLink.entity_client_id == category.client_id,
            ),
        )
        .where(Image.deleted_at.is_(None))
        .order_by(ImageLink.display_order.asc())
        .limit(1)
    )
    primary_image = img_result.scalar_one_or_none()

    return {"item_category": serialize_item_category(category, primary_image)}
```

**Checklist against `07_queries_local.md` completion gate:**
- [x] `item_categories_pagination` present as top-level key in list response
- [x] `has_more` derived from `limit + 1` fetch
- [x] Empty path and non-empty path both return the pagination key
- [x] `_MAX_LIMIT = 200` and `_DEFAULT_LIMIT = 50` defined
- [x] `workspace_id` is the first `where()` condition

---

### Step 6 — Create `services/queries/issue_types/issue_types.py`

**New folder:** `backend/app/beyo_manager/services/queries/issue_types/`
**New files:** `__init__.py` (empty) and `issue_types.py`

```python
"""QUERY-1: List IssueTypes | QUERY-2: Get IssueType by ID."""

from sqlalchemy import select

from beyo_manager.domain.issue_types.serializers import serialize_issue_type
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_issue_types(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

    stmt = select(IssueType).where(
        IssueType.workspace_id == ctx.workspace_id,
        IssueType.is_deleted.is_(False),
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(IssueType.name.ilike(pattern))

    stmt = stmt.order_by(IssueType.created_at.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "issue_types": [serialize_issue_type(r) for r in page],
        "issue_types_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_issue_type(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(IssueType).where(
            IssueType.workspace_id == ctx.workspace_id,
            IssueType.client_id == client_id,
            IssueType.is_deleted.is_(False),
        )
    )
    issue_type = result.scalar_one_or_none()
    if issue_type is None:
        raise NotFound("Issue type not found.")

    return {"issue_type": serialize_issue_type(issue_type)}
```

---

### Step 7 — Create `services/queries/issue_types/issue_category_configs.py`

**File:** `backend/app/beyo_manager/services/queries/issue_types/issue_category_configs.py` *(new)*

This query lists and fetches `IssueCategoryConfig` records. Because `issue_type_name` must be embedded in the response, the query joins `IssueType` and passes the name into the serializer — no extra per-row query.

```python
"""QUERY-1: List IssueCategoryConfigs | QUERY-2: Get IssueCategoryConfig by ID."""

from sqlalchemy import and_, select

from beyo_manager.domain.issue_types.serializers import serialize_issue_category_config
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.issue_types.issue_category_config import IssueCategoryConfig
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_issue_category_configs(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    item_category_id = ctx.query_params.get("item_category_id")

    # Join IssueType so we can filter by name (q) and include it in the serialized output.
    stmt = (
        select(IssueCategoryConfig, IssueType.name.label("issue_type_name"))
        .join(
            IssueType,
            and_(
                IssueType.client_id == IssueCategoryConfig.issue_type_id,
                IssueType.workspace_id == ctx.workspace_id,
                IssueType.is_deleted.is_(False),
            ),
        )
        .where(
            IssueCategoryConfig.workspace_id == ctx.workspace_id,
            IssueCategoryConfig.is_deleted.is_(False),
        )
    )

    if q:
        stmt = stmt.where(IssueType.name.ilike(f"%{q}%"))

    if item_category_id:
        stmt = stmt.where(IssueCategoryConfig.item_category_id == item_category_id)

    stmt = stmt.order_by(IssueCategoryConfig.created_at.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.all()   # list of (IssueCategoryConfig, issue_type_name) tuples

    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "issue_category_configs": [
            serialize_issue_category_config(config, name) for config, name in page
        ],
        "issue_category_configs_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_issue_category_config(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(IssueCategoryConfig, IssueType.name.label("issue_type_name"))
        .join(
            IssueType,
            and_(
                IssueType.client_id == IssueCategoryConfig.issue_type_id,
                IssueType.workspace_id == ctx.workspace_id,
                IssueType.is_deleted.is_(False),
            ),
        )
        .where(
            IssueCategoryConfig.workspace_id == ctx.workspace_id,
            IssueCategoryConfig.client_id == client_id,
            IssueCategoryConfig.is_deleted.is_(False),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise NotFound("Issue category config not found.")

    config, issue_type_name = row
    return {"issue_category_config": serialize_issue_category_config(config, issue_type_name)}
```

**Important:** `result.all()` returns `Row` tuples `(IssueCategoryConfig, str)` — not scalar ORM instances. Use `result.all()`, not `result.scalars().all()`.

---

### Step 8 — Create `services/queries/upholstery/upholsteries.py`

**File:** `backend/app/beyo_manager/services/queries/upholstery/upholsteries.py` *(new — the folder already exists)*

```python
"""QUERY-1: List Upholsteries | QUERY-2: Get Upholstery by ID."""

from sqlalchemy import and_, or_, select

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_upholsteries(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

    stmt = select(Upholstery).where(
        Upholstery.workspace_id == ctx.workspace_id,
        Upholstery.is_deleted.is_(False),
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Upholstery.name.ilike(pattern),
                Upholstery.code.ilike(pattern),
            )
        )

    stmt = stmt.order_by(Upholstery.created_at.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    # Batch-load first image per upholstery — single query, no N+1.
    images_map: dict[str, Image] = {}
    if page:
        upholstery_ids = [u.client_id for u in page]
        img_result = await ctx.session.execute(
            select(Image, ImageLink.entity_client_id)
            .join(
                ImageLink,
                and_(
                    ImageLink.image_id == Image.client_id,
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.UPHOLSTERY,
                    ImageLink.entity_client_id.in_(upholstery_ids),
                ),
            )
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
        )
        for image, entity_id in img_result.all():
            if entity_id not in images_map:
                images_map[entity_id] = image

    return {
        "upholsteries": [
            serialize_upholstery(u, images_map.get(u.client_id)) for u in page
        ],
        "upholsteries_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_upholstery(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(Upholstery).where(
            Upholstery.workspace_id == ctx.workspace_id,
            Upholstery.client_id == client_id,
            Upholstery.is_deleted.is_(False),
        )
    )
    upholstery = result.scalar_one_or_none()
    if upholstery is None:
        raise NotFound("Upholstery not found.")

    img_result = await ctx.session.execute(
        select(Image)
        .join(
            ImageLink,
            and_(
                ImageLink.image_id == Image.client_id,
                ImageLink.entity_type == ImageLinkEntityTypeEnum.UPHOLSTERY,
                ImageLink.entity_client_id == upholstery.client_id,
            ),
        )
        .where(Image.deleted_at.is_(None))
        .order_by(ImageLink.display_order.asc())
        .limit(1)
    )
    primary_image = img_result.scalar_one_or_none()

    return {"upholstery": serialize_upholstery(upholstery, primary_image)}
```

---

### Step 9 — Create `routers/api_v1/item_categories.py`

**File:** `backend/app/beyo_manager/routers/api_v1/item_categories.py` *(new)*

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_categories.item_categories import (
    get_item_category,
    list_item_categories,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/item-categories", tags=["item-categories"])


@router.get("")
async def route_list_item_categories(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_item_categories, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_item_category(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_item_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Rules:**
- No business logic in the handler. Path param `client_id` is merged into `incoming_data`.
- `q=None` is passed through to the service; the service ignores it when `None`.

---

### Step 10 — Create `routers/api_v1/issue_types.py`

**File:** `backend/app/beyo_manager/routers/api_v1/issue_types.py` *(new)*

This file owns two routers: one for `IssueType` and one for `IssueCategoryConfig`. Both live in the same file because they are part of the same domain and will be extended together later.

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.issue_types.issue_types import (
    get_issue_type,
    list_issue_types,
)
from beyo_manager.services.queries.issue_types.issue_category_configs import (
    get_issue_category_config,
    list_issue_category_configs,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/issue-types", tags=["issue-types"])
category_configs_router = APIRouter(
    prefix="/api/v1/issue-category-configs", tags=["issue-category-configs"]
)


# ── Issue Types ────────────────────────────────────────────────────────────────

@router.get("")
async def route_list_issue_types(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_issue_types, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_issue_type(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_issue_type, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# ── Issue Category Configs ─────────────────────────────────────────────────────

@category_configs_router.get("")
async def route_list_issue_category_configs(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    item_category_id: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "item_category_id": item_category_id,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_issue_category_configs, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@category_configs_router.get("/{client_id}")
async def route_get_issue_category_config(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_issue_category_config, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Route declaration order:** Collection-level `GET ""` is declared before wildcard `GET "/{client_id}"` in both routers — this satisfies the FastAPI route ordering rule from `09_routers.md`.

---

### Step 11 — Add `upholstery_router` to `routers/api_v1/item_upholsteries.py`

**File:** `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py` *(existing — append only)*

Add the following at the **end** of the file. Do **not** modify any existing route or router.

```python
# ── Upholstery configuration router (/api/v1/upholsteries) ────────────────────
from beyo_manager.services.queries.upholstery.upholsteries import (
    get_upholstery,
    list_upholsteries,
)

upholstery_router = APIRouter(prefix="/api/v1/upholsteries", tags=["upholsteries"])


@upholstery_router.get("")
async def route_list_upholsteries(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholsteries, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@upholstery_router.get("/{client_id}")
async def route_get_upholstery(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Important:** Move the import block for the new query functions to the top of the file with the other imports — Python requires all imports at module level. The inline imports shown above are for readability in this plan only.

---

### Step 12 — Register new routers in `routers/api_v1/__init__.py`

**File:** `backend/app/beyo_manager/routers/api_v1/__init__.py` *(existing — extend imports and `register_v1_routers`)*

Add imports:

```python
from beyo_manager.routers.api_v1 import item_categories, issue_types
```

Add registration calls inside `register_v1_routers(app)` after the existing entries (before the `# Add domain routers here` comment):

```python
app.include_router(item_categories.router)
app.include_router(issue_types.router)
app.include_router(issue_types.category_configs_router)
app.include_router(item_upholsteries.upholstery_router)
```

`item_upholsteries` is already imported — only add the `upholstery_router` include line, not a second import.

---

## Risks and mitigations

- **Risk:** `ALTER TYPE ... ADD VALUE` requires running outside a transaction in Postgres 12 and earlier (Postgres 14+ allows it inside a transaction).
  **Mitigation:** Use `op.execute()` with `postgresql_execute_string` and set `transaction_per_migration = False` on the migration, or use `IF NOT EXISTS` to make it idempotent. Check the project's Alembic config for the correct pattern used by existing enum migrations.

- **Risk:** `serialize_upholstery` name collides with the existing `serialize_upholstery` in `domain/tasks/serializers.py`.
  **Mitigation:** The new function lives in `domain/upholstery/serializers.py`, a completely different module. No name collision at runtime. Import explicitly by module path everywhere — never use `from ... import *`.

- **Risk:** `image_url` may be `None` for all item categories and upholsteries if no `ImageLink` rows with the new `entity_type` values exist yet.
  **Mitigation:** The serializer returns `None` for `image_url` when no image is linked. This is correct and expected behavior — the frontend must handle `null`.

- **Risk:** `IssueCategoryConfig` list uses `result.all()` (returning tuples) rather than `result.scalars().all()` (returning ORM instances). Using `scalars()` would silently discard the joined `issue_type_name` column.
  **Mitigation:** Explicitly documented in Step 7. Copilot must not change this to `result.scalars().all()`.

## Validation plan

- `uvicorn` / `fastapi` app startup completes without `ImportError` or `OperationalError` (checks registration)
- `GET /api/v1/item-categories?limit=5` returns `{"data": {"item_categories": [...], "item_categories_pagination": {...}}, "warnings": []}`
- `GET /api/v1/item-categories/nonexistent_id` returns HTTP 404
- `GET /api/v1/issue-types?q=scratch` returns `{"data": {"issue_types": [...], "issue_types_pagination": {...}}, "warnings": []}`
- `GET /api/v1/issue-category-configs?item_category_id=itc_xxx` returns correctly filtered results with `issue_type_name` in each record
- `GET /api/v1/upholsteries?q=linen` returns `{"data": {"upholsteries": [...], "upholsteries_pagination": {...}}, "warnings": []}`
- Alembic migration applies cleanly with `alembic upgrade head`
- Alembic migration is idempotent on re-run

## Review log

- `2026-05-22T15:39:27Z` — Implemented all scoped query/serializer/router/migration changes.
- `2026-05-22T15:39:27Z` — Validation evidence captured: module import smoke check passed, targeted unit regression tests passed, and `alembic upgrade head` succeeded.
- `2026-05-22T15:39:27Z` — Plan lifecycle progressed through implemented -> summarized -> archived with linked summary and archive record.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `copilot`
