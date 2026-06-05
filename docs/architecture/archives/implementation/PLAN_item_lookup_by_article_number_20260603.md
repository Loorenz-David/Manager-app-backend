# PLAN_item_lookup_by_article_number_20260603

## Metadata

- Plan ID: `PLAN_item_lookup_by_article_number_20260603`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-03T00:00:00Z`
- Last updated at (UTC): `2026-06-03T17:37:59Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Add a `GET /api/v1/items/lookup?article_number=<value>` endpoint that fans out to multiple item sources in parallel using the strategy pattern and returns a unified list of matching items to the frontend.
- Business/user intent: Allow managers, admins, and sellers to resolve an article number against both the internal database and the external Beyo Vintage purchase API simultaneously, so the frontend can display all matches (internal and external) in a single fast response and let the user act on them (e.g., import, link, or review).
- Non-goals: Writing items to the database (this is read-only). Caching external API responses. Pagination across sources. Adding other identity types (SKU, EAN) as query parameters now — the architecture is designed to support them later but the first iteration uses article_number only. Moving the API key to a vault (deferred).

## Scope

- In scope:
  - `backend/app/beyo_manager/services/queries/items/lookup/` package (4 files: `__init__.py`, `base.py`, `internal_db.py`, `purchase_api.py`)
  - `backend/app/beyo_manager/services/queries/items/lookup_item_by_article_number.py` — orchestrator service function
  - `backend/app/beyo_manager/routers/api_v1/items.py` — add one `GET /lookup` handler, placed before `/{client_id}`
  - `backend/app/beyo_manager/config.py` — add `beyo_vintage_api_key: str | None` setting
  - `backend/app/.env.example` — add `BEYO_VINTAGE_API_KEY=` stub entry

- Out of scope:
  - Database migrations (no new tables or columns)
  - Realtime events or socket broadcasts
  - Adding the result items to the local database
  - Any changes to existing item queries or commands

- Assumptions:
  - `httpx==0.28.1` is already pinned in requirements.txt — confirmed present.
  - `item_category_id` in the unified response shape is `str | None` (a `client_id` ULID string from the `item_categories` table), not `int`. The initial specification said `int` but the codebase uses string client IDs throughout; this is the correct type.
  - Category matching against the external API's `subcategory` field uses a case-insensitive exact match against `ItemCategory.name`. If no match is found, `item_category_id` is `None`.
  - If `BEYO_VINTAGE_API_KEY` is not set, `PurchaseApiLookupHandler.lookup` returns `None` and logs a warning rather than raising an error. The endpoint still returns internal DB results.
  - A handler that raises an exception during `asyncio.gather` is logged as a warning and excluded from results — it does not fail the whole request.
  - The photo URL prefix is `https://api.beyovintage.se` (no trailing slash). Path segments from the API already start with `/`.
  - Route order: `/lookup` must appear before `/{client_id}` in `items.py` to prevent FastAPI matching the literal string "lookup" as a `client_id`.

## Clarifications required

_None — scope is fully defined._

## Acceptance criteria

1. `GET /api/v1/items/lookup?article_number=0000420` with a valid JWT (admin / manager / seller) returns HTTP 200 with `{ "success": true, "data": { "items": [...] } }`.
2. When the article number exists in the internal DB, the items list contains one entry with `external_source: null`.
3. When the external purchase API returns a match, the items list contains one entry with `external_source: "purchase_api"`, `images` with fully-qualified URLs, and `item_category_id` resolved to a local category client_id (or `null` if no match).
4. Both sources run concurrently — a single network call latency does not block the DB read.
5. If `BEYO_VINTAGE_API_KEY` is missing, the endpoint returns only the internal DB result (no 500 error).
6. `GET /api/v1/items/lookup` with no `article_number` returns HTTP 422.
7. A worker JWT (`role: worker`) receives HTTP 403.
8. No existing item endpoints are broken (no route ordering conflict with `/{client_id}`).

## Contracts and skills

### Contracts loaded

- `../../../architecture/01_architecture.md`: baseline layered architecture rules — queries live in services/queries, not in routers
- `../../../architecture/04_context.md`: ServiceContext shape — `ctx.query_params`, `ctx.session`, `ctx.workspace_id`
- `../../../architecture/05_errors.md`: error imports — `ValidationError` for missing article_number
- `../../../architecture/07_queries.md`: query function conventions — async def, takes ServiceContext, returns dict
- `../../../architecture/07_queries_local.md`: local query delta — offset pagination override (not applicable here but load both per policy)
- `../../../architecture/09_routers.md`: router handler wiring — `Query(...)`, `Depends(require_roles(...))`, `run_service`, `build_ok/build_err`
- `../../../architecture/21_naming_conventions.md`: snake_case, file naming, module layout
- `../../../architecture/40_identity.md`: client_id ULID format — confirms `item_category_id` is `str`

### Local extensions loaded

- `../../../architecture/07_queries_local.md`: app-specific query delta

### File read intent — pattern vs. relational

Prohibited (pattern reads — contract covers these):
- Reading another query file to understand ServiceContext usage → `07_queries.md`
- Reading another router to understand handler wiring → `09_routers.md`

Permitted (relational reads — understanding what exists):
- `routers/api_v1/items.py` — to confirm route order and existing import block (add import without breaking what is there)
- `services/queries/item_categories/item_categories.py` — to understand `ItemCategory` query shape before writing the category-name lookup helper
- `models/tables/items/item.py` — to know exact field names for the internal DB handler mapping
- `models/tables/items/item_category.py` — to know exact column names used in the category lookup query
- `config.py` — to understand the Settings class pattern before adding the new field

### Skill selection

- Primary skill: `../../../architecture/07_queries.md` (new query service)
- Router trigger terms: `article_number`, `lookup`
- Excluded alternatives: `06_commands.md` — no writes; `13_sockets.md` — no realtime; `11_infra_events.md` — no domain events; `30_migrations.md` — no schema changes

## Implementation plan

### Step 1 — Add `beyo_vintage_api_key` to Settings

File: `backend/app/beyo_manager/config.py`

Add this field inside the `Settings` class, after the existing VAPID block and before the `environment` field:

```python
# External partner APIs
beyo_vintage_api_key: str | None = Field(default=None, alias="BEYO_VINTAGE_API_KEY")
```

No validator needed. The field is optional; absence is handled gracefully in the handler.

---

### Step 2 — Add `BEYO_VINTAGE_API_KEY` stub to `.env.example`

File: `backend/app/.env.example`

Add the following line in the appropriate section (after the VAPID block or as a new `# External APIs` section):

```
# External partner APIs
BEYO_VINTAGE_API_KEY=
```

---

### Step 3 — Create the `lookup/` package

Create the directory `backend/app/beyo_manager/services/queries/items/lookup/` with the following four files.

#### 3a — `__init__.py`

Empty file. Its presence makes the directory a package.

```python
```

#### 3b — `base.py`

Defines `ItemLookupResult` (the unified output shape) and `ItemLookupHandler` (the abstract base class all handlers implement).

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ItemLookupResult:
    article_number: str
    sku: str | None
    item_category_id: str | None
    quantity: int
    external_id: str | None
    external_source: str | None
    images: list[str] = field(default_factory=list)


class ItemLookupHandler(ABC):
    """Strategy interface for item lookup sources.

    Each concrete handler targets one source (internal DB, external API, etc.).
    Implement lookup() to query the source and map the result to ItemLookupResult.
    Return None when the article number is not found in this source.
    Raise only unexpected exceptions; caught in the orchestrator via asyncio.gather.
    """

    @abstractmethod
    async def lookup(
        self,
        article_number: str,
        session: AsyncSession,
        workspace_id: str,
    ) -> ItemLookupResult | None: ...
```

#### 3c — `internal_db.py`

Queries the local `items` table. Returns the first active item matching the article number, or `None`.

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.queries.items.lookup.base import ItemLookupHandler, ItemLookupResult


class InternalDbLookupHandler(ItemLookupHandler):
    async def lookup(
        self,
        article_number: str,
        session: AsyncSession,
        workspace_id: str,
    ) -> ItemLookupResult | None:
        result = await session.execute(
            select(Item).where(
                Item.workspace_id == workspace_id,
                Item.article_number == article_number,
                Item.is_deleted.is_(False),
            ).limit(1)
        )
        item = result.scalar_one_or_none()
        if item is None:
            return None

        return ItemLookupResult(
            article_number=item.article_number,
            sku=item.sku,
            item_category_id=item.item_category_id,
            quantity=item.quantity,
            external_id=item.external_id,
            external_source=None,
            images=[],
        )
```

Note: `images=[]` because the `Item` model has no photo-URL column. Future sources may populate this.

#### 3d — `purchase_api.py`

Calls the Beyo Vintage partner API. Resolves `subcategory` → local `item_category_id` via a direct DB query. Returns `None` when the API key is missing, the article is not found, or the response is not `success: true`.

```python
from __future__ import annotations

import logging

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.queries.items.lookup.base import ItemLookupHandler, ItemLookupResult

logger = logging.getLogger(__name__)

_PURCHASE_API_BASE = "https://api.beyovintage.se"
_EXTERNAL_SOURCE_NAME = "purchase_api"


async def _find_category_id_by_name(
    session: AsyncSession,
    workspace_id: str,
    name: str,
) -> str | None:
    """Case-insensitive exact match on ItemCategory.name within the workspace."""
    result = await session.execute(
        select(ItemCategory.client_id).where(
            ItemCategory.workspace_id == workspace_id,
            func.lower(ItemCategory.name) == name.lower(),
            ItemCategory.is_deleted.is_(False),
        ).limit(1)
    )
    return result.scalar_one_or_none()


class PurchaseApiLookupHandler(ItemLookupHandler):
    async def lookup(
        self,
        article_number: str,
        session: AsyncSession,
        workspace_id: str,
    ) -> ItemLookupResult | None:
        api_key = settings.beyo_vintage_api_key
        if not api_key:
            logger.warning("BEYO_VINTAGE_API_KEY is not set; skipping purchase API lookup")
            return None

        url = f"{_PURCHASE_API_BASE}/api/partner/items/{article_number}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={"X-Partner-Key": api_key})

        if response.status_code == 404:
            return None
        response.raise_for_status()

        body = response.json()
        if not body.get("success"):
            return None

        data = body.get("data", {})

        subcategory = data.get("subcategory")
        item_category_id: str | None = None
        if subcategory:
            item_category_id = await _find_category_id_by_name(session, workspace_id, subcategory)

        raw_photo_urls: list[str] = data.get("photo_urls") or []
        images = [
            f"{_PURCHASE_API_BASE}{path}" if path.startswith("/") else path
            for path in raw_photo_urls
        ]

        return ItemLookupResult(
            article_number=data.get("article_number", article_number),
            sku=None,
            item_category_id=item_category_id,
            quantity=int(data.get("quantity") or 1),
            external_id=None,
            external_source=_EXTERNAL_SOURCE_NAME,
            images=images,
        )
```

---

### Step 4 — Create the orchestrator service function

File: `backend/app/beyo_manager/services/queries/items/lookup_item_by_article_number.py`

```python
"""QUERY: Lookup item by article_number across all registered sources in parallel."""
from __future__ import annotations

import asyncio
import logging

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.items.lookup.base import ItemLookupResult
from beyo_manager.services.queries.items.lookup.internal_db import InternalDbLookupHandler
from beyo_manager.services.queries.items.lookup.purchase_api import PurchaseApiLookupHandler

logger = logging.getLogger(__name__)

_HANDLERS = [
    InternalDbLookupHandler(),
    PurchaseApiLookupHandler(),
]


def _serialize_result(r: ItemLookupResult) -> dict:
    return {
        "article_number": r.article_number,
        "sku": r.sku,
        "item_category_id": r.item_category_id,
        "quantity": r.quantity,
        "external_id": r.external_id,
        "external_source": r.external_source,
        "images": r.images,
    }


async def lookup_item_by_article_number(ctx: ServiceContext) -> dict:
    article_number = (ctx.query_params.get("article_number") or "").strip()
    if not article_number:
        raise ValidationError("article_number query parameter is required.")

    tasks = [
        h.lookup(article_number, ctx.session, ctx.workspace_id)
        for h in _HANDLERS
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    items: list[dict] = []
    for result in raw_results:
        if isinstance(result, Exception):
            logger.warning("Item lookup handler raised an exception: %s", result, exc_info=result)
            continue
        if result is not None:
            items.append(_serialize_result(result))

    return {"items": items}
```

Note on `_HANDLERS`: the list is module-level so handler instances are shared across requests. Both `InternalDbLookupHandler` and `PurchaseApiLookupHandler` are stateless (no instance state) — this is safe. If a future handler needs per-request state, move instantiation inside `lookup_item_by_article_number`.

---

### Step 5 — Add the route handler to `items.py`

File: `backend/app/beyo_manager/routers/api_v1/items.py`

**5a — Add the import.** At the end of the existing imports block, add:

```python
from beyo_manager.services.queries.items.lookup_item_by_article_number import lookup_item_by_article_number
```

Also add `SELLER` to the roles import line (if not already present):

```python
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
```

**5b — Add the route handler.** Insert this handler **immediately before** the existing `@router.get("/{client_id}")` handler (line 265 in the current file). This ordering is critical: FastAPI resolves routes in declaration order, and `/lookup` must not be shadowed by `/{client_id}`.

```python
@router.get("/lookup")
async def route_lookup_item_by_article_number(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
    article_number: str = Query(..., min_length=1, max_length=128),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"article_number": article_number},
        identity=claims,
        session=session,
    )
    outcome = await run_service(lookup_item_by_article_number, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

`Query(..., min_length=1, max_length=128)` means FastAPI returns 422 automatically if `article_number` is missing or empty — the `ValidationError` guard in the service is a secondary safety net for callers that bypass the router (e.g., direct service calls from other services).

---

## Risks and mitigations

- Risk: `GET /api/v1/items/lookup` is accidentally matched by the existing `GET /{client_id}` handler because `/lookup` is a valid string for a `client_id` path parameter.
  Mitigation: Step 5b explicitly places the `/lookup` route **before** `/{client_id}`. FastAPI uses first-match ordering.

- Risk: `httpx` request to the external API times out, blocking the response for the full timeout duration.
  Mitigation: `httpx.AsyncClient(timeout=10.0)` caps the call at 10 seconds. The `asyncio.gather` runs both handlers in parallel so the DB result is not delayed by the HTTP call. If the HTTP call times out, `raise_for_status` or the timeout itself raises an exception, which `asyncio.gather` captures as a result entry; the handler loop logs it as a warning and continues.

- Risk: The external API returns a non-JSON body on error (e.g., HTML 502 gateway error).
  Mitigation: `response.raise_for_status()` is called before `response.json()`. If the status is 5xx, the exception is captured by `asyncio.gather` and logged as a warning; the endpoint still returns internal DB results.

- Risk: `PurchaseApiLookupHandler` and `InternalDbLookupHandler` are instantiated at module level. If either gains instance state in the future, this will cause subtle concurrency bugs.
  Mitigation: Both are documented as stateless in Step 4. The comment in the orchestrator notes the requirement explicitly. Any future handler needing per-request state must be instantiated inside `lookup_item_by_article_number`.

- Risk: `_HANDLERS` is a module-level singleton list. Adding or removing sources requires a code change and a deploy.
  Mitigation: This is intentional — sources are not runtime-configurable in this iteration. The strategy pattern makes adding a new source a single new file + one-line append to `_HANDLERS`.

- Risk: The `_find_category_id_by_name` helper uses `func.lower()` which may not use an index if `ItemCategory.name` has no functional index.
  Mitigation: Category lookups are expected to be infrequent (at most one per request through the purchase API handler). The `item_categories` table is small. No index change is required at this scale.

## Validation plan

- `GET /api/v1/items/lookup` (no `article_number`): returns HTTP 422 from FastAPI's `Query(...)` validation
- `GET /api/v1/items/lookup?article_number=` (empty string): returns HTTP 422 (`min_length=1`)
- `GET /api/v1/items/lookup?article_number=NONEXISTENT` with valid admin JWT: returns `{ "success": true, "data": { "items": [] } }`
- `GET /api/v1/items/lookup?article_number=<existing-internal-article>` with valid admin JWT: returns one item with `external_source: null`, `images: []`
- `GET /api/v1/items/lookup?article_number=0000420` with valid admin JWT and `BEYO_VINTAGE_API_KEY` set: returns at most two items (one from DB if it exists, one from purchase API with `external_source: "purchase_api"` and fully-qualified image URLs)
- `GET /api/v1/items/lookup?article_number=0000420` with `BEYO_VINTAGE_API_KEY` unset: returns only internal DB result, no 500 error
- `GET /api/v1/items/lookup?article_number=0000420` with a worker JWT: returns HTTP 403
- `GET /api/v1/items/{known-client-id}` still returns the existing item detail (no route shadowing regression)
- Import smoke test: `python -c "from beyo_manager.services.queries.items.lookup_item_by_article_number import lookup_item_by_article_number"` exits 0

## Review log

_None yet._

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
