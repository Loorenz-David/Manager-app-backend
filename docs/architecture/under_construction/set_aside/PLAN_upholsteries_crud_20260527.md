# PLAN_upholsteries_crud_20260527

## Metadata

- Plan ID: `PLAN_upholsteries_crud_20260527`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-05-27T00:00:00Z`
- Last updated at (UTC): `2026-05-27T06:10:19Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Build a dedicated `/api/v1/upholsteries` router with commands for create, update, soft-delete, mark-favorite, and list-order-update; migrate the existing get/list routes from `item_upholsteries.py` to this new router; extend `list_upholsteries` with `in_stock` and `favorite` filters and corrected ordering.
- Business/user intent: Upholsteries are catalog items with linked inventory records. Users need a proper management API: create an upholstery (auto-creating its inventory record), update metadata, toggle favorite status, control display order, soft-delete, and filter lists by stock status or favorite flag. The current upholstery routes live incorrectly inside the item-upholsteries router and must be extracted.
- Non-goals: Inventory mutation operations (add ordered stock, confirm received, update thresholds) — covered by existing upholstery inventory commands. Item-upholstery link management — belongs in `item_upholsteries.py`.

## Scope

- In scope:
  - New router file `routers/api_v1/upholsteries.py` with 8 routes
  - Six new command files in `services/commands/upholstery/`
  - Six new request parsers added to `services/commands/upholstery/requests/__init__.py`
  - Updated `list_upholsteries` query: `in_stock` filter, `favorite` filter, corrected ordering
  - Removal of `upholstery_router`, `route_list_upholsteries`, and `route_get_upholstery` from `item_upholsteries.py`
  - Router registration update in `routers/api_v1/__init__.py`

- Out of scope:
  - Changes to existing upholstery inventory commands (`add_ordered_to_inventory`, `confirm_ordered_to_stock_inventory`, `update_upholstery_inventory`, `delete_upholstery_inventory`)
  - Item-upholstery creation, deletion, or requirement management
  - Changes to `get_upholstery` query (no changes needed)
  - Alembic migration for `list_order` and `favorite` columns (user confirmed columns are already added to the model — if a migration does not yet exist, one must be created separately before running commands)

- Assumptions:
  - The `list_order` and `favorite` columns exist in the DB (or a migration will be applied before first use).
  - Every upholstery created via `create_upholstery` will have a corresponding active inventory record; no upholstery should ever exist without one after this plan is implemented.
  - The unique partial index `uix_upholsteries_workspace_list_order` on `(workspace_id, list_order) WHERE list_order IS NOT NULL` applies to ALL rows regardless of `is_deleted`. This requires clearing `list_order` to `null` on soft-delete so the slot can be reused.

## Clarifications required

- [x] Should `favorite` be updatable via the general `PATCH /{id}` endpoint in addition to the dedicated `PATCH /{id}/favorite` route? **Resolved:** Keep both. `PATCH /{id}` general update includes `favorite`; the dedicated route also handles it. Additionally, the dedicated route gains a batch variant: a new collection-level `PATCH /favorite` route (no path param) that accepts `upholstery_ids: list[str]` and `favorite: bool` for bulk toggling.
- [x] When creating an upholstery, should `current_stored_amount_meters` be accepted as an optional field and trigger inventory condition evaluation? **Resolved:** Yes. `inventory_condition` at creation is derived from initial stock: `current_stored_amount_meters == 0` (or not provided) → `OUT_OF_STOCK`; `> 0` and `<= low_stock_threshold_meters` (if threshold provided) → `LOW_STOCK`; `> 0` otherwise → `AVAILABLE`.

## Acceptance criteria

1. `PUT /api/v1/upholsteries` creates an `Upholstery` and a linked `UpholsteryInventory` in a single atomic transaction; `inventory_condition` is derived from initial stock (`OUT_OF_STOCK` when `current_stored_amount_meters == 0`, `LOW_STOCK` when `> 0` and `<= low_stock_threshold_meters`, `AVAILABLE` otherwise); returns `{"upholstery": serialize_upholstery(upholstery, inventory)}`.
2. `GET /api/v1/upholsteries` supports `limit`, `offset`, `q`, `in_stock` (`true`/`false`), and `favorite` (`true`/`false`) query params; response includes `upholsteries_pagination` key; ordering puts list_order items first (asc by value), then remaining items by `favorite DESC`, `created_at ASC`.
3. `GET /api/v1/upholsteries/{client_id}` returns a single upholstery with inventory; 404 if not found or soft-deleted.
4. `PATCH /api/v1/upholsteries/{client_id}` updates `name`, `code`, `image_url`, and optionally `favorite`; returns updated upholstery; raises 409 on name/code workspace conflict.
5. `DELETE /api/v1/upholsteries/{client_id}` soft-deletes the upholstery (sets `is_deleted`, `deleted_at`, `deleted_by_id`, clears `list_order`); returns `{}`.
6. `PATCH /api/v1/upholsteries/{client_id}/favorite` sets `favorite` on a single upholstery; returns updated upholstery.
7. `PATCH /api/v1/upholsteries/favorite` (collection-level, static route declared before `/{client_id}`) accepts `{"upholstery_ids": list[str], "favorite": bool}`; updates all listed upholsteries in one transaction; returns `{"updated_count": int}`.
8. `PATCH /api/v1/upholsteries/{client_id}/list-order` sets `list_order` on target; if the new value is not null, a single bulk UPDATE increments `list_order + 1` for all other non-deleted workspace upholsteries with `list_order >= new_value`; `list_order=0` is rejected with `ValidationError`; null clears the value without cascading; returns updated upholstery.
9. The `upholstery_router` and its two route handlers are removed from `item_upholsteries.py`; `upholstery_router` is removed from `__init__.py` registration; the new `upholsteries.router` serves the same URL prefix `/api/v1/upholsteries` — no URL path changes.
10. All new commands follow `06_commands.md`: transaction via `ctx.session.begin()`, request parser in `requests/__init__.py`, no cross-command calls, event dispatch only after commit.
11. All list query responses follow `07_queries_local.md`: offset pagination, `upholsteries_pagination` top-level key, `_MAX_LIMIT = 200` and `_DEFAULT_LIMIT = 50`.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: command skeleton, transaction pattern, `session.begin()`, request parser shape, no cross-command calls
- `backend/architecture/06_commands_local.md`: `maybe_begin` noted but NOT used here — all new upholstery commands own their transactions directly and no higher-level command composes them; if future composition requires it, they will be migrated per local extension rules
- `backend/architecture/07_queries.md`: query signature, `select()` pattern, serialization, EXISTS subquery pattern
- `backend/architecture/07_queries_local.md`: offset-based pagination overrides cursor-based; `_MAX_LIMIT`/`_DEFAULT_LIMIT` constants required; completion gate checklist must be satisfied
- `backend/architecture/09_routers.md`: router skeleton, route declaration order (static before wildcard), path param injection, HTTP method conventions, `build_ok`/`build_err`

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination replaces cursor; pagination key shape is `{"has_more": bool, "limit": int, "offset": int}`

### File read intent — pattern vs. relational

Permitted relational reads completed:
- `models/tables/upholstery/upholstery.py` — exact field names, constraints, and index definitions
- `models/tables/upholstery/upholstery_inventory.py` — field names, enum types, check constraints
- `services/commands/upholstery/create_upholstery_inventory.py` — existing logic to replicate inline (not call)
- `services/commands/upholstery/requests/__init__.py` — existing parser patterns and field validators
- `services/queries/upholstery/upholsteries.py` — existing list/get query to extend
- `routers/api_v1/item_upholsteries.py` — upholstery_router to be removed
- `routers/api_v1/__init__.py` — registration to update
- `domain/upholstery/serializers.py` — `serialize_upholstery` signature to reuse
- `domain/upholstery/enums.py` — `UpholsteryInventoryConditionEnum`, `UpholsteryCurrencyEnum`
- `errors/validation.py` — `ValidationError`, `ConflictError` from `beyo_manager.errors.validation`

Prohibited (contract covers these — do not open):
- Any other command file to understand `session.add` / flush pattern → `06_commands.md`
- Any other router to understand handler skeleton → `09_routers.md`

### Skill selection

- Primary skill: CRUD + realtime goal bundle from `backend_contract_goal_mapping_guide.md`
- Trigger terms: `"search"`, `"filter query"`, `"ilike"`, `"partial match"` → contract `55` not loaded (filter logic is simple, no full-text search)
- Excluded alternatives: worker-driven, replayable async, CI-validated runtime (no background jobs, no replay, no CI changes)

## Implementation plan

### Step 1 — Request parsers

**File:** `services/commands/upholstery/requests/__init__.py` (append to existing file)

Add five new request models and their `parse_*` functions:

**`CreateUpholsteryRequest`**
```
client_id: str | None = None
name: str                                          # stripped, non-blank validator
code: str | None = None
image_url: str | None = None
favorite: bool = False
current_stored_amount_meters: Decimal | None = None  # optional initial stock, defaults to Decimal("0")
low_stock_threshold_meters: Decimal | None = None    # > 0 validator
minimum_to_have: int | None = None                   # >= 0 validator
maximum_to_have: int | None = None                   # >= 0 validator
projected_inventory_value_minor: int | None = None   # >= 0 validator
currency: UpholsteryCurrencyEnum | None = None
planning_position: str | None = None
```
Parser: `parse_create_upholstery_request(data: dict) -> CreateUpholsteryRequest`

**`UpdateUpholsteryRequest`**
```
client_id: str
name: str | None = None       # stripped, non-blank validator if provided
code: str | None = None
image_url: str | None = None
favorite: bool | None = None
```
Parser: `parse_update_upholstery_request(data: dict) -> UpdateUpholsteryRequest`

**`DeleteUpholsteryRequest`**
```
client_id: str
```
Parser: `parse_delete_upholstery_request(data: dict) -> DeleteUpholsteryRequest`

**`MarkUpholsteryFavoriteRequest`** (single)
```
client_id: str
favorite: bool
```
Parser: `parse_mark_upholstery_favorite_request(data: dict) -> MarkUpholsteryFavoriteRequest`

**`MarkUpholsteriesFavoriteRequest`** (batch)
```
upholstery_ids: list[str]   # non-empty validator
favorite: bool
```
Validator: `upholstery_ids` must not be empty.
Parser: `parse_mark_upholsteries_favorite_request(data: dict) -> MarkUpholsteriesFavoriteRequest`

**`UpdateUpholsteryListOrderRequest`**
```
client_id: str
list_order: int | None = None   # >= 1 validator when not None (0 rejected)
```
Parser: `parse_update_upholstery_list_order_request(data: dict) -> UpdateUpholsteryListOrderRequest`

All parsers use the same pattern as existing parsers in this file: `model_validate(data)` wrapped in `PydanticValidationError` catch → `ValidationError(f"{field}: {msg}")`.

---

### Step 2 — Command: `create_upholstery.py`

**File:** `services/commands/upholstery/create_upholstery.py`

```python
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_create_upholstery_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext


async def create_upholstery(ctx: ServiceContext) -> dict:
    request = parse_create_upholstery_request(ctx.incoming_data)

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "uph")

    async with ctx.session.begin():
        # 1. Optional client_id duplicate check
        if request.client_id is not None:
            if await ctx.session.get(Upholstery, request.client_id) is not None:
                raise ConflictError("Provided client_id is already in use.")

        # 2. Name uniqueness within workspace
        name_conflict = await ctx.session.execute(
            select(Upholstery).where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.name == request.name,
                Upholstery.is_deleted.is_(False),
            )
        )
        if name_conflict.scalar_one_or_none() is not None:
            raise ConflictError("An upholstery with this name already exists in the workspace.")

        # 3. Code uniqueness within workspace (only if code provided)
        if request.code is not None:
            code_conflict = await ctx.session.execute(
                select(Upholstery).where(
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.code == request.code,
                    Upholstery.is_deleted.is_(False),
                )
            )
            if code_conflict.scalar_one_or_none() is not None:
                raise ConflictError("An upholstery with this code already exists in the workspace.")

        # 4. Create Upholstery
        uph_kwargs = {}
        if request.client_id is not None:
            uph_kwargs["client_id"] = request.client_id

        upholstery = Upholstery(
            **uph_kwargs,
            workspace_id=ctx.workspace_id,
            name=request.name,
            code=request.code,
            image_url=request.image_url,
            favorite=request.favorite,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(upholstery)
        await ctx.session.flush()  # assigns client_id for FK reference below

        # 5. Derive inventory_condition from initial stock
        initial_stock = request.current_stored_amount_meters or Decimal("0")
        if initial_stock <= Decimal("0"):
            condition = UpholsteryInventoryConditionEnum.OUT_OF_STOCK
        elif (
            request.low_stock_threshold_meters is not None
            and initial_stock <= request.low_stock_threshold_meters
        ):
            condition = UpholsteryInventoryConditionEnum.LOW_STOCK
        else:
            condition = UpholsteryInventoryConditionEnum.AVAILABLE

        # 6. Create linked UpholsteryInventory
        inventory = UpholsteryInventory(
            workspace_id=ctx.workspace_id,
            upholstery_id=upholstery.client_id,
            inventory_condition=condition,
            current_stored_amount_meters=initial_stock,
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
        ctx.session.add(inventory)

    return {"upholstery": serialize_upholstery(upholstery, inventory)}
```

Key decisions:
- `inventory_condition` at creation is derived from `initial_stock` vs `low_stock_threshold_meters`; defaults to `OUT_OF_STOCK` when stock is 0 (not provided or explicit 0).
- No event emission (upholsteries are not realtime-broadcast entities in current scope).
- Does NOT accept `list_order` at creation — use `PATCH /{id}/list-order` after creation to avoid cascade complexity at create time.

---

### Step 3 — Command: `update_upholstery.py`

**File:** `services/commands/upholstery/update_upholstery.py`

Logic:
1. Parse request.
2. `async with ctx.session.begin():`
3. Load upholstery `(workspace_id, client_id, is_deleted=False)` → `NotFound` if missing.
4. Load linked active inventory (for return value).
5. If `name` provided and differs: check uniqueness → `ConflictError`.
6. If `code` provided and differs: check uniqueness → `ConflictError`.
7. Apply changed fields to ORM object; set `updated_by_id = ctx.user_id` (SQLAlchemy `onupdate` sets `updated_at` automatically on flush).

Import: `NotFound` from `beyo_manager.errors.not_found`.

Return: `{"upholstery": serialize_upholstery(upholstery, inventory)}`

Note on partial update: only apply fields that are explicitly provided (`is not None`). For `code` and `image_url`, `None` in the request means "not provided" — do not overwrite with null. If the caller wants to clear `code`, a separate null-clearing variant would be needed (out of scope — not requested).

---

### Step 4 — Command: `delete_upholstery.py`

**File:** `services/commands/upholstery/delete_upholstery.py`

Logic:
1. Parse request (`DeleteUpholsteryRequest` — just `client_id`).
2. `async with ctx.session.begin():`
3. Load upholstery → `NotFound` if missing or already deleted.
4. Set `is_deleted = True`, `deleted_at = datetime.now(timezone.utc)`, `deleted_by_id = ctx.user_id`.
5. **Set `list_order = None`** to free the slot in the partial unique index (which covers all rows regardless of `is_deleted`).

Return: `{}`

---

### Step 5a — Command: `mark_upholstery_favorite.py` (single)

**File:** `services/commands/upholstery/mark_upholstery_favorite.py`

Logic:
1. Parse `MarkUpholsteryFavoriteRequest`.
2. `async with ctx.session.begin():`
3. Load upholstery `(workspace_id, client_id, is_deleted=False)` → `NotFound` if missing.
4. Load linked inventory for return.
5. Set `upholstery.favorite = request.favorite`, `upholstery.updated_by_id = ctx.user_id`.

Return: `{"upholstery": serialize_upholstery(upholstery, inventory)}`

---

### Step 5b — Command: `mark_upholsteries_favorite.py` (batch)

**File:** `services/commands/upholstery/mark_upholsteries_favorite.py`

Logic:
1. Parse `MarkUpholsteriesFavoriteRequest`.
2. `async with ctx.session.begin():`
3. Single bulk UPDATE using SQLAlchemy ORM update statement:
   ```python
   await ctx.session.execute(
       sa_update(Upholstery)
       .where(
           Upholstery.workspace_id == ctx.workspace_id,
           Upholstery.is_deleted.is_(False),
           Upholstery.client_id.in_(request.upholstery_ids),
       )
       .values(favorite=request.favorite, updated_by_id=ctx.user_id)
       .execution_options(synchronize_session=False)
   )
   ```
4. Count affected rows via `result.rowcount` for the return payload.

Return: `{"updated_count": result.rowcount}`

Note: IDs in `request.upholstery_ids` that do not exist or belong to a different workspace are silently skipped by the WHERE clause — no per-ID error raised. This is intentional for batch operations (partial success is acceptable).

---

### Step 6 — Command: `update_upholstery_list_order.py`

**File:** `services/commands/upholstery/update_upholstery_list_order.py`

```python
from sqlalchemy import select, update as sa_update

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.domain.upholstery.serializers import serialize_upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.commands.upholstery.requests import parse_update_upholstery_list_order_request
from beyo_manager.services.context import ServiceContext


async def update_upholstery_list_order(ctx: ServiceContext) -> dict:
    request = parse_update_upholstery_list_order_request(ctx.incoming_data)

    async with ctx.session.begin():
        # 1. Load target upholstery
        result = await ctx.session.execute(
            select(Upholstery).where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.client_id == request.client_id,
                Upholstery.is_deleted.is_(False),
            )
        )
        upholstery = result.scalar_one_or_none()
        if upholstery is None:
            raise NotFound("Upholstery not found.")

        if request.list_order is not None:
            # 2. Cascade: shift all workspace upholsteries with list_order >= new value
            #    (excluding the target itself) up by 1 in a single bulk UPDATE
            await ctx.session.execute(
                sa_update(Upholstery)
                .where(
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.is_deleted.is_(False),
                    Upholstery.client_id != upholstery.client_id,
                    Upholstery.list_order >= request.list_order,
                    Upholstery.list_order.is_not(None),
                )
                .values(list_order=Upholstery.list_order + 1)
                .execution_options(synchronize_session=False)
            )

        # 3. Assign new list_order (or null) to target
        upholstery.list_order = request.list_order
        upholstery.updated_by_id = ctx.user_id

        # 4. Load inventory for return
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id == upholstery.client_id,
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inventory = inv_result.scalar_one_or_none()

    return {"upholstery": serialize_upholstery(upholstery, inventory)}
```

Key decisions:
- `synchronize_session=False` is correct here because we do not need the session's identity map updated for the shifted rows — we only return the target row, which is updated via direct ORM attribute assignment.
- The bulk UPDATE is a single SQL statement (one DB round trip), not a Python loop.
- When `list_order=None`: no cascade, only clear the target's value.
- The validator in `UpdateUpholsteryListOrderRequest` rejects `list_order=0`; minimum valid value is 1.
- No "consecutive gap filling" when setting null — the ordering system tolerates gaps.

---

### Step 7 — Update `list_upholsteries` query

**File:** `services/queries/upholstery/upholsteries.py`

Three changes to `list_upholsteries`:

**7a — New query params extracted from `ctx.query_params`:**
```python
in_stock_raw = ctx.query_params.get("in_stock")   # None | "true" | "false" | bool
favorite_raw = ctx.query_params.get("favorite")   # None | "true" | "false" | bool
```
Convert to bool via `_to_bool(v)` helper (handles both string and bool types, returns `None` if `v` is `None`).

**7b — `in_stock` filter via EXISTS subquery:**
```python
from sqlalchemy import exists

if in_stock is not None:
    conditions = (
        [UpholsteryInventoryConditionEnum.AVAILABLE, UpholsteryInventoryConditionEnum.LOW_STOCK]
        if in_stock
        else [UpholsteryInventoryConditionEnum.OUT_OF_STOCK]
    )
    stmt = stmt.where(
        exists(
            select(UpholsteryInventory.upholstery_id).where(
                UpholsteryInventory.upholstery_id == Upholstery.client_id,
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.is_deleted.is_(False),
                UpholsteryInventory.inventory_condition.in_(conditions),
            )
        )
    )
```
EXISTS subquery chosen over JOIN to avoid any possibility of duplicate rows (safe even if the unique index assumption ever changes).

**7c — `favorite` filter:**
```python
if favorite is not None:
    stmt = stmt.where(Upholstery.favorite.is_(favorite))
```

**7d — Corrected ordering** (replaces existing `order_by`):
```python
from sqlalchemy import case as sa_case

stmt = stmt.order_by(
    sa_case((Upholstery.list_order.is_(None), 1), else_=0),  # 0=has list_order (first), 1=null (after)
    Upholstery.list_order.asc().nulls_last(),
    Upholstery.favorite.desc(),
    Upholstery.created_at.asc(),
)
```
This guarantees: all upholsteries with a `list_order` appear first sorted by that value; remaining upholsteries (no list_order) appear after, sorted by `favorite DESC` then `created_at ASC`.

Also pass the new filters through to the router query params (see Step 9).

---

### Step 8 — New router file

**File:** `routers/api_v1/upholsteries.py`

```python
from fastapi import APIRouter, Depends, Query
from decimal import Decimal
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.upholstery.create_upholstery import create_upholstery
from beyo_manager.services.commands.upholstery.update_upholstery import update_upholstery
from beyo_manager.services.commands.upholstery.delete_upholstery import delete_upholstery
from beyo_manager.services.commands.upholstery.mark_upholstery_favorite import mark_upholstery_favorite
from beyo_manager.services.commands.upholstery.mark_upholsteries_favorite import mark_upholsteries_favorite
from beyo_manager.services.commands.upholstery.update_upholstery_list_order import update_upholstery_list_order
from beyo_manager.services.queries.upholstery.upholsteries import get_upholstery, list_upholsteries
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()
```

Route declaration order (static + collection before wildcard `/{client_id}`):

```
GET   ""                         → list_upholsteries              roles: ADMIN, MANAGER, WORKER
PUT   ""                         → create_upholstery              roles: ADMIN, MANAGER
PATCH "/favorite"                → mark_upholsteries_favorite     roles: ADMIN, MANAGER  ← static, must be BEFORE /{client_id}
GET   "/{client_id}"             → get_upholstery                 roles: ADMIN, MANAGER, WORKER
PATCH "/{client_id}"             → update_upholstery              roles: ADMIN, MANAGER
DELETE "/{client_id}"            → delete_upholstery              roles: ADMIN, MANAGER
PATCH "/{client_id}/favorite"    → mark_upholstery_favorite       roles: ADMIN, MANAGER
PATCH "/{client_id}/list-order"  → update_upholstery_list_order   roles: ADMIN, MANAGER
```

Request body models in the router file:

- `_CreateBody`: mirrors `CreateUpholsteryRequest` fields; expose `client_id: str | None` (consistent with `create_upholstery_inventory` router convention)
- `_UpdateBody`: `name: str | None`, `code: str | None`, `image_url: str | None`, `favorite: bool | None`
- `_BatchFavoriteBody`: `upholstery_ids: list[str]`, `favorite: bool`
- `_FavoriteBody`: `favorite: bool`
- `_ListOrderBody`: `list_order: int | None`

Router query params for `GET ""`:
```python
limit: int = Query(50, ge=1, le=200)
offset: int = Query(0, ge=0)
q: str | None = Query(None)
in_stock: bool | None = Query(None)
favorite: bool | None = Query(None)
```

`ServiceContext` for list route:
```python
ctx = ServiceContext(
    incoming_data={},
    query_params={"limit": limit, "offset": offset, "q": q, "in_stock": in_stock, "favorite": favorite},
    identity=claims,
    session=session,
)
```

Path param injection for all `/{client_id}` routes: merge `client_id` into `incoming_data`:
```python
ctx = ServiceContext(
    incoming_data={"client_id": client_id, **body.model_dump(exclude_none=True)},
    ...
)
```

---

### Step 9 — Remove `upholstery_router` from `item_upholsteries.py`

**File:** `routers/api_v1/item_upholsteries.py`

Remove:
- `upholstery_router = APIRouter(...)` variable declaration
- `route_list_upholsteries` function
- `route_get_upholstery` function
- The `list_upholsteries` and `get_upholstery` imports from `services.queries.upholstery.upholsteries`

---

### Step 10 — Update router registration

**File:** `routers/api_v1/__init__.py`

Changes:
1. Add import: `from beyo_manager.routers.api_v1 import upholsteries`
2. Add registration:
   ```python
   app.include_router(upholsteries.router, prefix="/api/v1/upholsteries", tags=["upholsteries"])
   ```
3. Remove line: `app.include_router(item_upholsteries.upholstery_router)`

## Risks and mitigations

- Risk: `synchronize_session=False` in the bulk list_order UPDATE means ORM instances for shifted upholsteries already in the session identity map hold stale `list_order` values for the rest of the request.
  Mitigation: The command only reads and returns the target upholstery (set via ORM attribute), not any of the shifted ones. Stale cached values are never read within this command's lifetime. Safe.

- Risk: The partial unique index `uix_upholsteries_workspace_list_order` covers all rows including soft-deleted ones. A soft-deleted upholstery retaining its `list_order` would permanently block that slot.
  Mitigation: `delete_upholstery` explicitly sets `list_order = None` before committing.

- Risk: Concurrent requests setting the same `list_order` value could produce a race condition before the bulk shift runs.
  Mitigation: The bulk shift + target assignment is inside a single `session.begin()` transaction. Postgres row-level locking within the transaction prevents duplicates from being committed simultaneously. At very high concurrency, serialization failures may occur; these surface as DB errors and are caught by `run_service` → generic error response. Acceptable for the current scale.

- Risk: The correlated EXISTS subquery for `in_stock` filter scans `upholstery_inventory` for each matching upholstery. At large dataset sizes this may be slow.
  Mitigation: `UpholsteryInventory` has an index on `upholstery_id`. For current workspace-scoped data sizes this is acceptable. Replace with an explicit JOIN if profiling shows cost.

- Risk: Removing `upholstery_router` from `item_upholsteries.py` while the import still exists in `__init__.py` would break startup.
  Mitigation: Steps 9 and 10 must be done atomically (same commit). The plan makes this explicit.

## Validation plan

- `python -c "from beyo_manager.routers.api_v1 import upholsteries"` — import succeeds without error
- `alembic check` — no pending migration if columns already exist; or `alembic upgrade head` if migration is pending
- `PUT /api/v1/upholsteries` with `{"name": "Velvet Red"}` (no stock) → inventory `inventory_condition = out_of_stock`; inventory `client_id` starts with `uin`
- `PUT /api/v1/upholsteries` with `{"name": "Velvet Blue", "current_stored_amount_meters": "5.000", "low_stock_threshold_meters": "3.000"}` → `inventory_condition = available`
- `PUT /api/v1/upholsteries` with `{"name": "Velvet Green", "current_stored_amount_meters": "2.000", "low_stock_threshold_meters": "3.000"}` → `inventory_condition = low_stock`
- `PUT /api/v1/upholsteries` with same name → returns 409
- `PATCH /api/v1/upholsteries/favorite` with `{"upholstery_ids": [...], "favorite": true}` → returns `{"updated_count": N}`; IDs not in workspace silently excluded
- `GET /api/v1/upholsteries?in_stock=true` → only upholsteries with inventory condition `available` or `low_stock`
- `GET /api/v1/upholsteries?in_stock=false` → only upholsteries with inventory condition `out_of_stock`
- `GET /api/v1/upholsteries?favorite=true` → only favorited upholsteries
- `PATCH /api/v1/upholsteries/{id}/list-order` with `{"list_order": 1}` → target gets `list_order=1`, all others with previous `list_order >= 1` are incremented
- `PATCH /api/v1/upholsteries/{id}/list-order` with `{"list_order": null}` → target `list_order` cleared, no other rows changed
- `PATCH /api/v1/upholsteries/{id}/list-order` with `{"list_order": 0}` → 422 validation error
- `DELETE /api/v1/upholsteries/{id}` on an upholstery with `list_order=2` → item disappears from list; slot `list_order=2` is freed (another upholstery can be assigned list_order=2 without conflict)
- `GET /api/v1/upholsteries` ordering: upholsteries with list_order appear before those without; within list_order group sorted ascending; within no-list_order group favorites appear before non-favorites

## Review log

_empty_

## Lifecycle transition

- Current state: `approved`
- Next state: `archived` (after successful implementation and validation)
- Transition owner: `claude-sonnet-4-6`
