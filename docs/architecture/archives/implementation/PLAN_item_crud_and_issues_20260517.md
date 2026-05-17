# PLAN_item_crud_and_issues_20260517

## Metadata

- Plan ID: `PLAN_item_crud_and_issues_20260517`
- Status: `archived`
- Owner agent: `Claude Sonnet 4.6`
- Created at (UTC): `2026-05-17T14:00:00Z`
- Last updated at (UTC): `2026-05-17T18:20:00Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_item_crud_and_issues_20260517.md`

---

## Goal and intent

- **Goal:** Deliver CMD-1 through CMD-4 (item CRUD + issue creation), QUERY-1 (list items) and QUERY-2 (get item by ID), all serializers for `Item`, `ItemIssue`, and the extended `ItemUpholstery`, plus the items router and the Alembic migration that adds snapshot columns and fixes partial unique indexes on the `items` table.
- **Business/user intent:** Items are the primary production unit. Without atomic item creation, update, delete, and retrieval with full composition (issues + upholstery), no production workflow can be initiated or tracked.
- **Non-goals:** `ItemIssue` state transitions; `ItemUpholstery` standalone CRUD (already done); item state transitions; batch import; backfilling snapshot columns on existing rows; `maybe_begin` utility (pre-condition, already implemented).

---

## Scope

- **In scope:**
  - Migration: snapshot columns on `items`, fixed partial unique indexes
  - Model update: `item.py` — new columns and updated `__table_args__`
  - Request models: `CreateItemRequest`, `CreateItemIssueRequest`, `UpdateItemRequest`, `DeleteItemRequest` added to `requests/__init__.py`
  - New command: `create_item.py` (CMD-1) — atomic item + optional issues + optional upholstery
  - New command: `create_item_issue.py` (CMD-2) — standalone create issue; contains `_create_item_issue_in_session` helper
  - Refactor: `create_item_upholstery.py` — extract `_create_item_upholstery_in_session` helper; standalone command calls the helper
  - New command: `update_item.py` (CMD-3) — partial update using `model_fields_set`
  - New command: `delete_item.py` (CMD-4) — soft delete
  - Serializer update: `domain/items/serializers.py` — extend `serialize_item_upholstery` to accept requirements; add `serialize_item_list`, `serialize_item_detail`, `serialize_item_issue`
  - Query update: `services/queries/items/item_upholsteries.py` — update both callers of `serialize_item_upholstery` to batch-load requirements
  - New query file: `services/queries/items/items.py` — `list_items` (QUERY-1) and `get_item` (QUERY-2)
  - New router: `routers/api_v1/items.py`
  - Router registration: `routers/api_v1/__init__.py`

- **Out of scope:** `maybe_begin` utility (already at `services/commands/utils/transaction.py`); upholstery lifecycle commands (already implemented); `ItemCategory` CRUD; item state machine.

- **Assumptions:**
  - `maybe_begin` exists at `beyo_manager.services.commands.utils.transaction`.
  - `apply_string_filter` exists at `beyo_manager.services.queries.utils.string_filter`.
  - The Alembic chain is linear and at `f3c8a1d209e5` head before this migration is applied.
  - `ItemCategory` model exists at `beyo_manager.models.tables.items.item_category` with `name: str` and `major_category: ItemMajorCategoryEnum` columns.

---

## Clarifications required

None — all design questions resolved in the intention plan.

---

## Acceptance criteria

1. `alembic upgrade head` applies without error; `items` table has `item_category_snapshot`, `item_major_category_snapshot` columns and updated unique indexes that include `AND is_deleted = false`.
2. `PUT /api/v1/items` creates Item, Issues, and ItemUpholstery atomically in one transaction; returns `{"data": {"client_id": "itm_..."}}`.
3. `POST /api/v1/items/{client_id}/issues` creates a standalone issue; returns `{"data": {"client_id": "iti_..."}}`.
4. `PATCH /api/v1/items/{client_id}` updates only fields present in the payload; absent fields are unchanged; null in payload clears the column; returns `{"data": {"client_id": "itm_..."}}`.
5. `DELETE /api/v1/items/{client_id}` soft-deletes the item; returns `{"data": {}}`.
6. `GET /api/v1/items` returns `{"data": {"items_pagination": {"items": [...], "limit": int, "offset": int, "has_more": bool}}}` where each item has `issue_count` and snapshot-based `item_category`; `q` filters across 7 columns spanning 3 tables.
7. `GET /api/v1/items/{client_id}` returns `{"data": {"item": {..., "item_issues": [...], "item_upholstery": {...} | null}}}` where `item_upholstery` includes `item_upholstery_requirements`.
8. `GET /api/v1/item-upholsteries` and `GET /api/v1/item-upholsteries/{client_id}` still work correctly after the `serialize_item_upholstery` breaking change; both include `item_upholstery_requirements` in the response.
9. Import smoke test passes: `.venv/bin/python -c "from beyo_manager import create_app; create_app()"`.
10. `grep -rn "ctx.session.begin" backend/app/beyo_manager/services/commands/items/` returns zero matches.

---

## Contracts and skills

### Contracts loaded

**Read order (canonical first, local second):**

- `backend/architecture/01_architecture.md` (baseline): layer rules, folder structure.
- `backend/architecture/04_context.md` (baseline): `ServiceContext` shape — `incoming_data`, `query_params`, `identity`, `session`.
- `backend/architecture/05_errors.md` (baseline): `NotFound`, `ValidationError`, `ConflictError` error classes and import paths.
- `backend/architecture/06_commands.md` (baseline): command skeleton, transaction pattern, request parser pattern.
- `backend/architecture/06_commands_local.md` (local delta): **ALL commands in this plan use `maybe_begin` instead of `ctx.session.begin()`**; session call safety table; event emission rule for subordinates; invariant: one `maybe_begin` per function, no manual commit/rollback.
- `backend/architecture/07_queries.md` (baseline): query signature, `select()` pattern, result extraction methods.
- `backend/architecture/07_queries_local.md` (local delta): **offset-based pagination only** — no cursor pagination; exact implementation pattern including `limit + 1` trick; completion gate checklist.
- `backend/architecture/09_routers.md` (baseline): handler skeleton, `run_service` call, `build_ok`/`build_err`, route declaration order (static before wildcard), path parameter injection into `incoming_data`, `body.model_dump(exclude_unset=True)` for PATCH.
- `backend/architecture/21_naming_conventions.md` (baseline): file naming, constant naming, prefix conventions.
- `backend/architecture/03_models.md` (baseline): `Mapped` + `mapped_column` style, `lazy="raise"` on relationships, index naming, `__table_args__` pattern.
- `backend/architecture/08_domain.md` (baseline): serializers in `domain/<domain>/serializers.py`, pure functions.
- `backend/architecture/30_migrations.md` (baseline): autogenerate workflow, nullable-first for new columns, review checklist.
- `backend/architecture/46_serialization.md` (baseline): serializers are pure functions in `domain/`; services return `dict` for commands; serializer naming convention.
- `backend/architecture/55_query_filters_local.md` (local-only): `apply_string_filter` utility; `q` + `string_filters` query params; router `max_length=200` validation; **QUERY-1 exception documented in this plan**.

### Local extensions loaded

- `06_commands_local.md`: replaces `ctx.session.begin()` with `maybe_begin(ctx.session)` in all item commands; defines session call safety rules and subordinate event rule.
- `07_queries_local.md`: offset pagination overrides cursor pagination — use this pattern exclusively.
- `55_query_filters_local.md`: `apply_string_filter` utility for single-table ILIKE; QUERY-1 exempt (see implementation note below).

### File read intent — pattern vs. relational

**Prohibited (pattern reads — contract covers these):**
- Reading another command file to understand `session.add` / `flush` / error-raising shape → read `06_commands.md` instead.
- Reading another router to understand handler shape → read `09_routers.md` instead.
- Reading another serializer to understand output shape → read `46_serialization.md` instead.

**Permitted (relational reads — understanding existing state):**
- `backend/app/beyo_manager/models/tables/items/item.py` — exact column names, types, `__table_args__` to modify.
- `backend/app/beyo_manager/models/tables/items/item_issue.py` — exact column names and types for `ItemIssue`.
- `backend/app/beyo_manager/models/tables/items/item_upholstery.py` — exact column names for helper extraction.
- `backend/app/beyo_manager/models/tables/items/item_upholstery_requirement.py` — column names for batch query.
- `backend/app/beyo_manager/models/tables/items/item_category.py` — `name` and `major_category` fields.
- `backend/app/beyo_manager/domain/items/serializers.py` — current `serialize_item_upholstery` signature to extend.
- `backend/app/beyo_manager/domain/items/enums.py` — `ItemStateEnum`, `ItemIssueStateEnum`, `ItemMajorCategoryEnum`, etc.
- `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py` — existing logic to extract into helper.
- `backend/app/beyo_manager/services/commands/items/requests/__init__.py` — existing request models to append to.
- `backend/app/beyo_manager/services/queries/items/item_upholsteries.py` — existing callers of `serialize_item_upholstery` to update.
- `backend/app/beyo_manager/routers/api_v1/__init__.py` — existing registration block to extend.
- `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py` — existing router for structural reference (prefix pattern, role constants).
- `backend/app/beyo_manager/services/queries/utils/string_filter.py` — confirm signature before calling.

### Skill selection

- Primary skill: Backend CRUD + domain commands
- Excluded: worker, background jobs, redis, websockets — none required here.

---

## Implementation plan

### Step 0 — Pre-condition verification

Run:
```bash
grep -r "def maybe_begin" backend/app/beyo_manager/services/commands/utils/
```
Expected: one match in `transaction.py`. If absent, stop and implement `PLAN_maybe_begin_transaction_utility` first.

---

### Step 1 — Update `item.py` model (required before migration autogenerate)

**File:** `backend/app/beyo_manager/models/tables/items/item.py`

**Changes:**

1. **Add two nullable `String` columns** after `external_order_id`:
   ```python
   item_category_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
   item_major_category_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
   ```

2. **Update `__table_args__`** — replace the two partial unique indexes with versions that add `AND is_deleted = false` to the WHERE condition:

   **Before:**
   ```python
   Index(
       "uix_items_workspace_article_number",
       "workspace_id",
       "article_number",
       unique=True,
       postgresql_where=text("article_number IS NOT NULL"),
   ),
   Index(
       "uix_items_workspace_sku",
       "workspace_id",
       "sku",
       unique=True,
       postgresql_where=text("sku IS NOT NULL"),
   ),
   ```

   **After:**
   ```python
   Index(
       "uix_items_workspace_article_number",
       "workspace_id",
       "article_number",
       unique=True,
       postgresql_where=text("article_number IS NOT NULL AND is_deleted = false"),
   ),
   Index(
       "uix_items_workspace_sku",
       "workspace_id",
       "sku",
       unique=True,
       postgresql_where=text("sku IS NOT NULL AND is_deleted = false"),
   ),
   ```

   Keep `ix_items_workspace_state` unchanged.

3. Add `from sqlalchemy import ... text` to imports if not already present (it already is — verify).

**Result:** Model now declares snapshot columns and corrected partial indexes. Do NOT run migrations yet.

---

### Step 2 — Generate and apply the Alembic migration

From `backend/app/`:
```bash
alembic revision --autogenerate -m "item_snapshot_columns_and_fix_unique_indexes"
```

**Review the generated file before applying.** Verify the following are present:
- `op.add_column("items", sa.Column("item_category_snapshot", sa.String(255), nullable=True))`
- `op.add_column("items", sa.Column("item_major_category_snapshot", sa.String(64), nullable=True))`
- `op.drop_index("uix_items_workspace_article_number", table_name="items")` (or equivalent)
- `op.create_index("uix_items_workspace_article_number", "items", ["workspace_id", "article_number"], unique=True, postgresql_where=sa.text("article_number IS NOT NULL AND is_deleted = false"))`
- `op.drop_index("uix_items_workspace_sku", table_name="items")` (or equivalent)
- `op.create_index("uix_items_workspace_sku", "items", ["workspace_id", "sku"], unique=True, postgresql_where=sa.text("sku IS NOT NULL AND is_deleted = false"))`

**If Alembic does not detect the partial WHERE condition change** (it sometimes misses this), manually add the drop and create statements. The correct `downgrade()` must reverse every `upgrade()` operation.

After review:
```bash
alembic upgrade head
```

Verify: `alembic current` shows the new revision at head.

---

### Step 3 — Add request models to `services/commands/items/requests/__init__.py`

Append the following to the end of the existing file. Do not remove or modify any existing class or function.

#### 3a — Nested sub-models (for CMD-1 embedded inputs)

```python
class ItemIssueCreateInput(BaseModel):
    """Nested input for one issue to create atomically with an item."""
    issue_type_id: str | None = None
    issue_severity_id: str | None = None
    base_time_seconds: int | None = None
    time_multiplier: Decimal | None = None
    issue_name_snapshot: str | None = None
    severity_name_snapshot: str | None = None


class ItemUpholsteryCreateInput(BaseModel):
    """Nested input for the upholstery to create atomically with an item."""
    upholstery_id: str | None = None
    source: ItemUpholsterySourceEnum
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    time_to_fix_in_seconds: int | None = None

    @field_validator("amount_meters", mode="before")
    @classmethod
    def coerce_zero_to_null(cls, v) -> Decimal | None:
        if v is None:
            return None
        v = Decimal(str(v))
        return None if v <= Decimal("0") else v

    @field_validator("time_to_fix_in_seconds")
    @classmethod
    def time_must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("time_to_fix_in_seconds must be >= 0.")
        return v
```

#### 3b — `CreateItemRequest`

```python
class CreateItemRequest(BaseModel):
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    quantity: int = 1
    designer: str | None = None
    height_in_cm: int | None = None
    width_in_cm: int | None = None
    depth_in_cm: int | None = None
    item_value_minor: int | None = None
    item_cost_minor: int | None = None
    item_currency: ItemCurrencyEnum | None = None
    item_position: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None
    item_issues: list[ItemIssueCreateInput] | None = None
    item_upholstery: ItemUpholsteryCreateInput | None = None

    @field_validator("article_number", "sku", mode="before")
    @classmethod
    def strip_or_none(cls, v) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be >= 1.")
        return v
```

Add the required enum imports at the top of the file — `ItemCurrencyEnum` is imported from `beyo_manager.domain.items.enums`. Add it to the existing import line if not present.

#### 3c — `CreateItemIssueRequest`

```python
class CreateItemIssueRequest(BaseModel):
    item_id: str  # injected from path param
    issue_type_id: str | None = None
    issue_severity_id: str | None = None
    base_time_seconds: int | None = None
    time_multiplier: Decimal | None = None
    issue_name_snapshot: str | None = None
    severity_name_snapshot: str | None = None
```

#### 3d — `UpdateItemRequest`

```python
class UpdateItemRequest(BaseModel):
    client_id: str  # injected from path param
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    quantity: int | None = None
    designer: str | None = None
    height_in_cm: int | None = None
    width_in_cm: int | None = None
    depth_in_cm: int | None = None
    item_value_minor: int | None = None
    item_cost_minor: int | None = None
    item_currency: ItemCurrencyEnum | None = None
    item_position: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("quantity must be >= 1.")
        return v
```

#### 3e — `DeleteItemRequest`

```python
class DeleteItemRequest(BaseModel):
    client_id: str
```

#### 3f — Parse functions (append after the class definitions)

```python
def parse_create_item_request(data: dict) -> CreateItemRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return CreateItemRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_create_item_issue_request(data: dict) -> CreateItemIssueRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return CreateItemIssueRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_update_item_request(data: dict) -> UpdateItemRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return UpdateItemRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_delete_item_request(data: dict) -> DeleteItemRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return DeleteItemRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

**Additional import needed at the top of `requests/__init__.py`:**
```python
from beyo_manager.domain.items.enums import ItemCurrencyEnum  # add to existing import line
```

---

### Step 4 — Refactor `create_item_upholstery.py` — extract session-level helper

**File:** `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py`

Extract the logic inside the `maybe_begin` block (excluding the item existence check) into a private session-level helper. The standalone command calls the helper after checking item existence.

**New file structure:**

```python
"""CMD-1: Create ItemUpholstery with initial requirement."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.commands.items.requests import parse_create_item_upholstery_request
from beyo_manager.services.commands.upholstery._inventory_mutations import check_and_inject_need
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def _create_item_upholstery_in_session(
    session: AsyncSession,
    workspace_id: str,
    item_id: str,
    upholstery_id: str | None,
    name: str | None,
    code: str | None,
    amount_meters: Decimal | None,
    source: ItemUpholsterySourceEnum,
    time_to_fix_in_seconds: int | None,
    user_id: str | None,
) -> str:
    """Create ItemUpholstery and initial requirement inside an open transaction.

    Caller is responsible for verifying item existence and resolving
    name/code from the Upholstery registry before calling this helper.
    Does NOT open or commit a transaction — must be called inside maybe_begin.
    Returns the new ItemUpholstery client_id.
    """
    iup = ItemUpholstery(
        workspace_id=workspace_id,
        item_id=item_id,
        upholstery_id=upholstery_id,
        name=name,
        code=code,
        amount_meters=amount_meters,
        source=source,
        time_to_fix_in_seconds=time_to_fix_in_seconds,
        created_by_id=user_id,
    )
    session.add(iup)
    await session.flush()  # get iup.client_id

    if amount_meters is not None and source != ItemUpholsterySourceEnum.CUSTOMER:
        inv_result = await check_and_inject_need(
            session=session,
            workspace_id=workspace_id,
            upholstery_id=upholstery_id,
            quantity=amount_meters,
            inject=True,
        )
        state = (
            ItemUpholsteryRequirementStateEnum.AVAILABLE
            if inv_result["sufficient"]
            else ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
        )
        req = ItemUpholsteryRequirement(
            workspace_id=workspace_id,
            item_upholstery_id=iup.client_id,
            upholstery_inventory_id=inv_result["inventory_id"],
            amount_meters=amount_meters,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=state,
            created_by_id=user_id,
        )
    elif amount_meters is None:
        req = ItemUpholsteryRequirement(
            workspace_id=workspace_id,
            item_upholstery_id=iup.client_id,
            upholstery_inventory_id=None,
            amount_meters=None,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=ItemUpholsteryRequirementStateEnum.MISSING_QUANTITY,
            created_by_id=user_id,
        )
    else:
        # CUSTOMER source with quantity — AVAILABLE, no inventory touch
        req = ItemUpholsteryRequirement(
            workspace_id=workspace_id,
            item_upholstery_id=iup.client_id,
            upholstery_inventory_id=None,
            amount_meters=amount_meters,
            source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
            state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
            created_by_id=user_id,
        )

    session.add(req)
    await session.flush()  # get req.client_id
    iup.active_requirement_id = req.client_id
    return iup.client_id


async def create_item_upholstery(ctx: ServiceContext) -> dict:
    """Create ItemUpholstery and initial ItemUpholsteryRequirement (standalone command)."""
    request = parse_create_item_upholstery_request(ctx.incoming_data)

    if request.upholstery_id is None and request.source != ItemUpholsterySourceEnum.CUSTOMER:
        raise ValidationError("upholstery_id is required when source is not CUSTOMER.")

    async with maybe_begin(ctx.session):
        item_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.item_id,
                Item.is_deleted.is_(False),
            )
        )
        if item_result.scalar_one_or_none() is None:
            raise NotFound("Item not found.")

        iup_client_id = await _create_item_upholstery_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_id=request.item_id,
            upholstery_id=request.upholstery_id,
            name=request.name,
            code=request.code,
            amount_meters=request.amount_meters,
            source=request.source,
            time_to_fix_in_seconds=request.time_to_fix_in_seconds,
            user_id=ctx.user_id,
        )

    return {"client_id": iup_client_id}
```

**Important:** The `_create_item_upholstery_in_session` helper does NOT verify item existence — the standalone command does that check before calling the helper; CMD-1 does not re-check because it just created the item.

---

### Step 5 — Create `create_item_issue.py` (CMD-2 + session-level helper)

**File:** `backend/app/beyo_manager/services/commands/items/create_item_issue.py`

```python
"""CMD-2: Create ItemIssue — standalone command and session-level helper."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemIssueStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.services.commands.items.requests import (
    CreateItemIssueRequest,
    parse_create_item_issue_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def _create_item_issue_in_session(
    session: AsyncSession,
    workspace_id: str,
    item_id: str,
    issue_data: CreateItemIssueRequest,
    user_id: str | None,
) -> str:
    """Create one ItemIssue inside an open transaction.

    Does NOT open or commit a transaction — must be called inside maybe_begin.
    Returns the new ItemIssue client_id.
    """
    issue = ItemIssue(
        workspace_id=workspace_id,
        item_id=item_id,
        issue_type_id=issue_data.issue_type_id,
        issue_severity_id=issue_data.issue_severity_id,
        state=ItemIssueStateEnum.PENDING,
        base_time_seconds=issue_data.base_time_seconds,
        time_multiplier=issue_data.time_multiplier,
        issue_name_snapshot=issue_data.issue_name_snapshot,
        severity_name_snapshot=issue_data.severity_name_snapshot,
        created_by_id=user_id,
    )
    session.add(issue)
    await session.flush()
    return issue.client_id


async def create_item_issue(ctx: ServiceContext) -> dict:
    """Create a standalone ItemIssue linked to an existing active item."""
    request = parse_create_item_issue_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        item_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.item_id,
                Item.is_deleted.is_(False),
            )
        )
        if item_result.scalar_one_or_none() is None:
            raise NotFound("Item not found.")

        issue_client_id = await _create_item_issue_in_session(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_id=request.item_id,
            issue_data=request,
            user_id=ctx.user_id,
        )

    return {"client_id": issue_client_id}
```

---

### Step 6 — Create `create_item.py` (CMD-1)

**File:** `backend/app/beyo_manager/services/commands/items/create_item.py`

```python
"""CMD-1: Create Item atomically with optional issues and optional upholstery."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemStateEnum, ItemUpholsterySourceEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.services.commands.items.create_item_upholstery import _create_item_upholstery_in_session
from beyo_manager.services.commands.items.create_item_issue import _create_item_issue_in_session
from beyo_manager.services.commands.items.requests import (
    CreateItemIssueRequest,
    parse_create_item_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_item(ctx: ServiceContext) -> dict:
    """Create Item with optional embedded issues and optional item upholstery."""
    request = parse_create_item_request(ctx.incoming_data)

    # Guard: at least one identifier must be non-null
    if request.article_number is None and request.sku is None:
        raise ValidationError("At least one of article_number or sku must be provided.")

    # Guard: upholstery source validation (pre-transaction, no DB needed)
    if request.item_upholstery is not None:
        iup_input = request.item_upholstery
        if iup_input.source == ItemUpholsterySourceEnum.INTERNAL and iup_input.upholstery_id is None:
            raise ValidationError("upholstery_id is required when source is INTERNAL.")
        if iup_input.source == ItemUpholsterySourceEnum.CUSTOMER and iup_input.upholstery_id is not None:
            raise ValidationError("upholstery_id must be null when source is CUSTOMER.")

    async with maybe_begin(ctx.session):
        # Load category and populate snapshots
        category_snapshot: str | None = None
        major_category_snapshot: str | None = None
        if request.item_category_id is not None:
            cat_result = await ctx.session.execute(
                select(ItemCategory).where(
                    ItemCategory.workspace_id == ctx.workspace_id,
                    ItemCategory.client_id == request.item_category_id,
                    ItemCategory.is_deleted.is_(False),
                )
            )
            category = cat_result.scalar_one_or_none()
            if category is None:
                raise NotFound("ItemCategory not found.")
            category_snapshot = category.name
            major_category_snapshot = category.major_category.value

        item = Item(
            workspace_id=ctx.workspace_id,
            article_number=request.article_number,
            sku=request.sku,
            state=ItemStateEnum.PENDING,
            item_category_id=request.item_category_id,
            item_category_snapshot=category_snapshot,
            item_major_category_snapshot=major_category_snapshot,
            quantity=request.quantity,
            designer=request.designer,
            height_in_cm=request.height_in_cm,
            width_in_cm=request.width_in_cm,
            depth_in_cm=request.depth_in_cm,
            item_value_minor=request.item_value_minor,
            item_cost_minor=request.item_cost_minor,
            item_currency=request.item_currency,
            item_position=request.item_position,
            external_id=request.external_id,
            external_url=request.external_url,
            external_source=request.external_source,
            external_order_id=request.external_order_id,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(item)
        await ctx.session.flush()  # obtain item.client_id

        # Create embedded issues
        for issue_input in (request.item_issues or []):
            issue_req = CreateItemIssueRequest(
                item_id=item.client_id,
                issue_type_id=issue_input.issue_type_id,
                issue_severity_id=issue_input.issue_severity_id,
                base_time_seconds=issue_input.base_time_seconds,
                time_multiplier=issue_input.time_multiplier,
                issue_name_snapshot=issue_input.issue_name_snapshot,
                severity_name_snapshot=issue_input.severity_name_snapshot,
            )
            await _create_item_issue_in_session(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_id=item.client_id,
                issue_data=issue_req,
                user_id=ctx.user_id,
            )

        # Create embedded upholstery
        if request.item_upholstery is not None:
            iup_input = request.item_upholstery
            resolved_name = iup_input.name
            resolved_code = iup_input.code

            # Resolve name/code from Upholstery registry when source is INTERNAL
            if iup_input.source == ItemUpholsterySourceEnum.INTERNAL:
                uph_result = await ctx.session.execute(
                    select(Upholstery).where(
                        Upholstery.workspace_id == ctx.workspace_id,
                        Upholstery.client_id == iup_input.upholstery_id,
                        Upholstery.is_deleted.is_(False),
                    )
                )
                upholstery = uph_result.scalar_one_or_none()
                if upholstery is None:
                    raise NotFound("Upholstery not found.")
                if resolved_name is None:
                    resolved_name = upholstery.name
                if resolved_code is None:
                    resolved_code = upholstery.code  # may remain null — Upholstery.code is nullable

            await _create_item_upholstery_in_session(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_id=item.client_id,
                upholstery_id=iup_input.upholstery_id,
                name=resolved_name,
                code=resolved_code,
                amount_meters=iup_input.amount_meters,
                source=iup_input.source,
                time_to_fix_in_seconds=iup_input.time_to_fix_in_seconds,
                user_id=ctx.user_id,
            )

    return {"client_id": item.client_id}
```

**Imports note:** `ItemCategory` is at `beyo_manager.models.tables.items.item_category`. `Upholstery` is at `beyo_manager.models.tables.upholstery.upholstery`. Verify exact paths by reading those model files.

---

### Step 7 — Create `update_item.py` (CMD-3)

**File:** `backend/app/beyo_manager/services/commands/items/update_item.py`

```python
"""CMD-3: Update Item fields — null vs omit via model_fields_set."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.commands.items.requests import parse_update_item_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


_DIRECT_FIELDS = {
    "article_number", "sku", "quantity", "designer",
    "height_in_cm", "width_in_cm", "depth_in_cm",
    "item_value_minor", "item_cost_minor", "item_currency",
    "item_position", "external_id", "external_url",
    "external_source", "external_order_id",
}


async def update_item(ctx: ServiceContext) -> dict:
    """Update Item — only fields present in the request payload are written."""
    request = parse_update_item_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.client_id,
                Item.is_deleted.is_(False),
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFound("Item not found.")

        # Apply only fields the caller explicitly included in the payload
        for field in _DIRECT_FIELDS & request.model_fields_set:
            setattr(item, field, getattr(request, field))

        # Handle snapshot re-population when item_category_id changes
        if "item_category_id" in request.model_fields_set:
            if request.item_category_id is not None:
                cat_result = await ctx.session.execute(
                    select(ItemCategory).where(
                        ItemCategory.workspace_id == ctx.workspace_id,
                        ItemCategory.client_id == request.item_category_id,
                        ItemCategory.is_deleted.is_(False),
                    )
                )
                category = cat_result.scalar_one_or_none()
                if category is None:
                    raise NotFound("ItemCategory not found.")
                item.item_category_id = request.item_category_id
                item.item_category_snapshot = category.name
                item.item_major_category_snapshot = category.major_category.value
            else:
                item.item_category_id = None
                item.item_category_snapshot = None
                item.item_major_category_snapshot = None

        item.updated_at = datetime.now(timezone.utc)
        item.updated_by_id = ctx.user_id

    return {"client_id": item.client_id}
```

**`model_fields_set` rule:** The router passes `body.model_dump(exclude_unset=True)` (see Step 11). The parser calls `model_validate(data)`. Fields absent from the original payload are NOT in the dict, so they are NOT in `model_fields_set` on the validated model. Fields explicitly set to null ARE in the dict and thus in `model_fields_set`. This is what enables null-means-clear and absence-means-preserve semantics.

---

### Step 8 — Create `delete_item.py` (CMD-4)

**File:** `backend/app/beyo_manager/services/commands/items/delete_item.py`

```python
"""CMD-4: Soft-delete an Item."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.items.requests import parse_delete_item_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_item(ctx: ServiceContext) -> dict:
    """Soft-delete an Item. Does not cascade to issues or upholstery rows."""
    request = parse_delete_item_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.client_id,
                Item.is_deleted.is_(False),
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFound("Item not found.")

        item.is_deleted = True
        item.deleted_at = datetime.now(timezone.utc)
        item.deleted_by_id = ctx.user_id

    return {}
```

---

### Step 9 — Update serializers in `domain/items/serializers.py`

**File:** `backend/app/beyo_manager/domain/items/serializers.py`

**Change 1: Update `serialize_item_upholstery` signature (breaking change).**

Current:
```python
def serialize_item_upholstery(iup: ItemUpholstery) -> dict:
```

New:
```python
def serialize_item_upholstery(
    iup: ItemUpholstery,
    requirements: list,  # list[ItemUpholsteryRequirement]
) -> dict:
```

Add `"item_upholstery_requirements": [serialize_upholstery_requirement(r) for r in requirements]` to the returned dict (at the end).

**Change 2: Add three new serializer functions** (append to the file):

```python
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue


def serialize_item_issue(issue: ItemIssue) -> dict:
    return {
        "client_id": issue.client_id,
        "item_id": issue.item_id,
        "issue_type_id": issue.issue_type_id,
        "issue_severity_id": issue.issue_severity_id,
        "state": issue.state.value,
        "base_time_seconds": issue.base_time_seconds,
        "time_multiplier": str(issue.time_multiplier) if issue.time_multiplier is not None else None,
        "issue_name_snapshot": issue.issue_name_snapshot,
        "severity_name_snapshot": issue.severity_name_snapshot,
        "created_at": issue.created_at.isoformat(),
        "created_by_id": issue.created_by_id,
        "started_at": issue.started_at.isoformat() if issue.started_at else None,
        "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
        "updated_by_id": issue.updated_by_id,
    }


def _build_item_category_object(item: Item) -> dict | None:
    if item.item_category_id is None:
        return None
    return {
        "client_id": item.item_category_id,
        "name": item.item_category_snapshot,
        "major_category": item.item_major_category_snapshot,
    }


def _serialize_item_base(item: Item) -> dict:
    return {
        "client_id": item.client_id,
        "article_number": item.article_number,
        "sku": item.sku,
        "state": item.state.value,
        "item_category": _build_item_category_object(item),
        "quantity": item.quantity,
        "designer": item.designer,
        "height_in_cm": item.height_in_cm,
        "width_in_cm": item.width_in_cm,
        "depth_in_cm": item.depth_in_cm,
        "item_value_minor": item.item_value_minor,
        "item_cost_minor": item.item_cost_minor,
        "item_currency": item.item_currency.value if item.item_currency else None,
        "item_position": item.item_position,
        "external_id": item.external_id,
        "external_url": item.external_url,
        "external_source": item.external_source,
        "external_order_id": item.external_order_id,
        "created_at": item.created_at.isoformat(),
        "created_by_id": item.created_by_id,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def serialize_item_list(item: Item, issue_count: int) -> dict:
    return {**_serialize_item_base(item), "issue_count": issue_count}


def serialize_item_detail(
    item: Item,
    issues: list,         # list[ItemIssue]
    upholstery,           # ItemUpholstery | None
    requirements: list,   # list[ItemUpholsteryRequirement] — empty if upholstery is None
) -> dict:
    return {
        **_serialize_item_base(item),
        "item_issues": [serialize_item_issue(iss) for iss in issues],
        "item_upholstery": serialize_item_upholstery(upholstery, requirements) if upholstery is not None else None,
    }
```

**Import additions needed at the top of `serializers.py`:**
```python
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
```

---

### Step 10 — Update `services/queries/items/item_upholsteries.py` (breaking change callers)

**File:** `backend/app/beyo_manager/services/queries/items/item_upholsteries.py`

Both `list_item_upholsteries` and `get_item_upholstery` must batch-load requirements before calling the updated `serialize_item_upholstery`.

**Updated `list_item_upholsteries`:**

After `items = rows[:limit]`, add:
```python
    # Batch-load requirements for all items on this page
    iup_ids = [iup.client_id for iup in items]
    reqs_by_iup: dict = {}
    if iup_ids:
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.item_upholstery_id.in_(iup_ids),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            ).order_by(ItemUpholsteryRequirement.created_at.asc())
        )
        for req in req_result.scalars().all():
            reqs_by_iup.setdefault(req.item_upholstery_id, []).append(req)
```

Then update the return statement:
```python
    return {
        "item_upholsteries_pagination": {
            "items": [serialize_item_upholstery(iup, reqs_by_iup.get(iup.client_id, [])) for iup in items],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
```

**Updated `get_item_upholstery`:**

After `iup = result.scalar_one_or_none()` check, add:
```python
    req_result = await ctx.session.execute(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.item_upholstery_id == iup.client_id,
            ItemUpholsteryRequirement.is_deleted.is_(False),
        ).order_by(ItemUpholsteryRequirement.created_at.asc())
    )
    requirements = req_result.scalars().all()
    return {"item_upholstery": serialize_item_upholstery(iup, requirements)}
```

Add `from sqlalchemy import desc, select` is already present. Add import for `ItemUpholsteryRequirement` if not already in the file.

---

### Step 11 — Create `services/queries/items/items.py` (QUERY-1 + QUERY-2)

**File:** `backend/app/beyo_manager/services/queries/items/items.py`

```python
"""QUERY-1: List Items | QUERY-2: Get Item by ID."""

from sqlalchemy import exists, func, or_, select

from beyo_manager.domain.items.serializers import (
    serialize_item_detail,
    serialize_item_list,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_items(ctx: ServiceContext) -> dict:
    """QUERY-1: List items with optional q filter and issue_count per item."""
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

    stmt = (
        select(Item)
        .where(
            Item.workspace_id == ctx.workspace_id,
            Item.is_deleted.is_(False),
        )
    )

    # q filter — 7 columns across 3 tables
    # NOTE: apply_string_filter is NOT used here because 3 of the 7 conditions
    # require EXISTS subqueries on related tables. Using JOINs on item_issues
    # (1:N) would produce duplicate parent rows. All 7 conditions are combined
    # in a single or_() to maintain correct OR semantics.
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(
            Item.article_number.ilike(pattern),
            Item.sku.ilike(pattern),
            Item.item_position.ilike(pattern),
            Item.designer.ilike(pattern),
            exists(
                select(ItemIssue.client_id).where(
                    ItemIssue.item_id == Item.client_id,
                    ItemIssue.workspace_id == ctx.workspace_id,
                    ItemIssue.is_deleted.is_(False),
                    ItemIssue.issue_name_snapshot.ilike(pattern),
                )
            ),
            exists(
                select(ItemUpholstery.client_id).where(
                    ItemUpholstery.item_id == Item.client_id,
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                    ItemUpholstery.name.ilike(pattern),
                )
            ),
            exists(
                select(ItemUpholstery.client_id).where(
                    ItemUpholstery.item_id == Item.client_id,
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                    ItemUpholstery.code.ilike(pattern),
                )
            ),
        ))

    stmt = stmt.order_by(Item.created_at.desc()).offset(offset).limit(limit + 1)
    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    # Batch-fetch issue_count for items on this page
    issue_counts: dict = {}
    if page:
        item_ids = [item.client_id for item in page]
        count_result = await ctx.session.execute(
            select(ItemIssue.item_id, func.count().label("cnt"))
            .where(
                ItemIssue.item_id.in_(item_ids),
                ItemIssue.is_deleted.is_(False),
            )
            .group_by(ItemIssue.item_id)
        )
        issue_counts = {row.item_id: row.cnt for row in count_result}

    return {
        "items_pagination": {
            "items": [
                serialize_item_list(item, issue_counts.get(item.client_id, 0))
                for item in page
            ],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }


async def get_item(ctx: ServiceContext) -> dict:
    """QUERY-2: Get Item by ID with full composition (issues + upholstery + requirements)."""
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(Item).where(
            Item.workspace_id == ctx.workspace_id,
            Item.client_id == client_id,
            Item.is_deleted.is_(False),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFound("Item not found.")

    # Load all non-deleted issues for this item
    issues_result = await ctx.session.execute(
        select(ItemIssue).where(
            ItemIssue.workspace_id == ctx.workspace_id,
            ItemIssue.item_id == item.client_id,
            ItemIssue.is_deleted.is_(False),
        ).order_by(ItemIssue.created_at.asc())
    )
    issues = issues_result.scalars().all()

    # Load upholstery (at most one per item)
    iup_result = await ctx.session.execute(
        select(ItemUpholstery).where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.item_id == item.client_id,
            ItemUpholstery.is_deleted.is_(False),
        )
    )
    upholstery = iup_result.scalar_one_or_none()

    # Load requirements only if upholstery exists
    requirements = []
    if upholstery is not None:
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id == upholstery.client_id,
                ItemUpholsteryRequirement.is_deleted.is_(False),
            ).order_by(ItemUpholsteryRequirement.created_at.asc())
        )
        requirements = req_result.scalars().all()

    return {"item": serialize_item_detail(item, issues, upholstery, requirements)}
```

---

### Step 12 — Create `routers/api_v1/items.py`

**File:** `backend/app/beyo_manager/routers/api_v1/items.py`

**Route declaration order (FastAPI matches top-to-bottom; static before wildcard):**
1. `PUT ""` — create item (collection level)
2. `GET ""` — list items (collection level)
3. `POST "/{client_id}/issues"` — create issue (multi-segment — safe after single-segment wildcard but declared first for clarity)
4. `GET "/{client_id}"` — get item
5. `PATCH "/{client_id}"` — update item
6. `DELETE "/{client_id}"` — delete item

```python
"""Router: /api/v1/items"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemUpholsterySourceEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.items.create_item import create_item
from beyo_manager.services.commands.items.create_item_issue import create_item_issue
from beyo_manager.services.commands.items.delete_item import delete_item
from beyo_manager.services.commands.items.update_item import update_item
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.items.items import get_item, list_items
from beyo_manager.services.run_service import run_service

router = APIRouter()


# ── Request body models ────────────────────────────────────────────────────────

class _ItemIssueBody(BaseModel):
    issue_type_id: str | None = None
    issue_severity_id: str | None = None
    base_time_seconds: int | None = None
    time_multiplier: Decimal | None = None
    issue_name_snapshot: str | None = None
    severity_name_snapshot: str | None = None


class _ItemUpholsteryBody(BaseModel):
    upholstery_id: str | None = None
    source: ItemUpholsterySourceEnum
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    time_to_fix_in_seconds: int | None = None


class _CreateItemBody(BaseModel):
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    quantity: int = 1
    designer: str | None = None
    height_in_cm: int | None = None
    width_in_cm: int | None = None
    depth_in_cm: int | None = None
    item_value_minor: int | None = None
    item_cost_minor: int | None = None
    item_currency: ItemCurrencyEnum | None = None
    item_position: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None
    item_issues: list[_ItemIssueBody] | None = None
    item_upholstery: _ItemUpholsteryBody | None = None


class _UpdateItemBody(BaseModel):
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    quantity: int | None = None
    designer: str | None = None
    height_in_cm: int | None = None
    width_in_cm: int | None = None
    depth_in_cm: int | None = None
    item_value_minor: int | None = None
    item_cost_minor: int | None = None
    item_currency: ItemCurrencyEnum | None = None
    item_position: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None


class _CreateIssueBody(BaseModel):
    issue_type_id: str | None = None
    issue_severity_id: str | None = None
    base_time_seconds: int | None = None
    time_multiplier: Decimal | None = None
    issue_name_snapshot: str | None = None
    severity_name_snapshot: str | None = None


# ── Collection-level routes (before wildcard /{client_id}) ────────────────────

@router.put("")
async def route_create_item(
    body: _CreateItemBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(create_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_items(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_items, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# ── Wildcard /{client_id} routes ───────────────────────────────────────────────

@router.post("/{client_id}/issues")
async def route_create_item_issue(
    client_id: str,
    body: _CreateIssueBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"item_id": client_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(create_item_issue, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_item(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_item(
    client_id: str,
    body: _UpdateItemBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_item(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(delete_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**PATCH body note:** `body.model_dump(exclude_unset=True)` is used — NOT `model_dump()` and NOT `model_dump(exclude_none=True)`. This passes only explicitly-provided fields (including explicit nulls) to `incoming_data`, enabling `model_fields_set` in CMD-3 to correctly distinguish "absent" from "explicit null."

---

### Step 13 — Register items router in `routers/api_v1/__init__.py`

**File:** `backend/app/beyo_manager/routers/api_v1/__init__.py`

Add the import at the top of the import block:
```python
from beyo_manager.routers.api_v1 import items
```

Add the registration inside `register_v1_routers` before the comment line `# Add domain routers here as you build them:`:
```python
    app.include_router(items.router, prefix="/api/v1/items", tags=["items"])
```

---

## Risks and mitigations

- **Risk:** Alembic doesn't detect the `postgresql_where` condition change on partial indexes.
  **Mitigation:** Review the generated migration file before applying. If the drop/create statements for the two partial indexes are missing, add them manually using `op.drop_index` + `op.create_index` with the correct `postgresql_where=sa.text(...)`.

- **Risk:** `serialize_item_upholstery` signature change breaks existing callers silently (Python doesn't enforce function signatures at import time).
  **Mitigation:** Search for all call sites after Step 9: `grep -rn "serialize_item_upholstery" backend/app/`. Fix every call site before running the smoke test.

- **Risk:** `model_fields_set` in CMD-3 is empty if the router uses `body.model_dump()` instead of `body.model_dump(exclude_unset=True)`.
  **Mitigation:** The router PATCH handler must use `exclude_unset=True`. If the model_dump includes all keys (even absent ones), `model_fields_set` on the re-validated `UpdateItemRequest` will include all keys and the selective-update logic will fail.

- **Risk:** QUERY-2 raises `MissingGreenlet` if `ItemIssue`, `ItemUpholstery`, or `ItemUpholsteryRequirement` relationships are lazily loaded.
  **Mitigation:** QUERY-2 explicitly loads each related collection with separate `select()` statements. No relationship attributes on ORM instances are accessed directly. This is correct — relationships are `lazy="raise"` per `03_models.md`.

- **Risk:** CMD-1 creates the item and then raises `NotFound` for a missing Upholstery — leaving the item committed.
  **Mitigation:** All writes (item, issues, upholstery) are inside the single `maybe_begin` block. If the Upholstery lookup raises `NotFound`, the exception propagates before the block exits cleanly, triggering rollback. The item is never committed.

---

## Validation plan

Run all steps in order after implementation is complete.

```bash
# 1. Alembic head check
cd backend/app && alembic current
# Expected: shows new revision at head

# 2. Import smoke test
cd backend/app && .venv/bin/python -c "from beyo_manager import create_app; create_app(); print('OK')"
# Expected: OK

# 3. No ctx.session.begin() in items commands
grep -rn "ctx.session.begin" backend/app/beyo_manager/services/commands/items/
# Expected: zero matches

# 4. All serialize_item_upholstery call sites have requirements argument
grep -rn "serialize_item_upholstery(" backend/app/beyo_manager/
# Expected: every call site passes two arguments

# 5. All new command files exist
ls backend/app/beyo_manager/services/commands/items/create_item.py
ls backend/app/beyo_manager/services/commands/items/create_item_issue.py
ls backend/app/beyo_manager/services/commands/items/update_item.py
ls backend/app/beyo_manager/services/commands/items/delete_item.py
ls backend/app/beyo_manager/services/queries/items/items.py
ls backend/app/beyo_manager/routers/api_v1/items.py
# Expected: all exist

# 6. Router registered — items prefix present
grep "items" backend/app/beyo_manager/routers/api_v1/__init__.py
# Expected: includes_router line with /api/v1/items prefix
```

---

## Review log

- `2026-05-17` Claude Sonnet 4.6: Plan created from intention plan + full contract + implementation file review.
- `2026-05-17` GitHub Copilot (GPT-5.3-Codex): Implemented all scoped code changes, generated migration `3a5532f8f0a7`, manually added missing partial-index drop/create operations, applied `alembic upgrade head`, ran `alembic current`, import smoke test, and grep validation checks.

---

## Lifecycle transition

- Current state: `archived`
- Next state: `debugging` (only if defects are reported)
- Transition owner: GitHub Copilot (implementation and archive completion)
