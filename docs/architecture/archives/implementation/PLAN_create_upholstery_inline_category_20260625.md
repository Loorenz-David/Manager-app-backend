# PLAN_create_upholstery_inline_category_20260625

## Metadata

- Plan ID: `PLAN_create_upholstery_inline_category_20260625`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-06-25T00:00:00Z`
- Last updated at (UTC): `2026-06-25T09:50:50Z`
- Related issue/ticket: —
- Intention plan: —

---

## Goal and intent

- **Goal:** Extend `PUT /api/v1/upholsteries` (`create_upholstery`) to accept an optional `create_category` inline payload. When present, the command creates the `UpholsteryCategory` and links it to the new `Upholstery` in a single atomic transaction. When absent, existing behavior is preserved.
- **Business/user intent:** Users creating an upholstery sometimes need a new category at the same time. Forcing them to make two separate API calls (create category, then create upholstery with the returned ID) is wasteful. A single call with the category payload embedded should do both in one round-trip.
- **Non-goals:** Changes to `create_upholstery_category` standalone command, inline category update, inline category deletion, updating an existing category via this endpoint.

---

## Scope

- **In scope:**
  - New nested request model `CreateUpholsteryCategoryInlineRequest` in `services/commands/upholstery/requests/__init__.py`
  - `model_validator` on `CreateUpholsteryRequest` to enforce mutual exclusion of `create_category` and `upholstery_category_id`
  - `create_category` field added to `CreateUpholsteryRequest`
  - Inline category creation logic added to `create_upholstery` command within its existing `async with ctx.session.begin()` transaction
  - `_InlineCategoryBody` Pydantic model added to `routers/api_v1/upholsteries.py`
  - `create_category` field added to router `_CreateBody`

- **Out of scope:**
  - Changes to `create_upholstery_category.py` standalone command
  - `maybe_begin` migration — not needed because no two commands are being composed; all work stays in one command's own transaction
  - Updating `upholstery_category_id` to point at a new inline-created category on `update_upholstery`

- **Assumptions:**
  - `body.model_dump()` on the extended `_CreateBody` will produce a flat dict with `create_category` as a nested dict key. `CreateUpholsteryRequest.model_validate(data)` correctly parses this nested structure because `create_category: CreateUpholsteryCategoryInlineRequest | None = None` accepts a dict.
  - Both `create_category` and `upholstery_category_id` being `None` is valid (no category linked) — existing behavior.
  - The response shape is unchanged: `serialize_upholstery(upholstery, inventory, category)` already embeds the category object, so the newly created inline category appears naturally in `upholstery_category`.

---

## Clarifications required

- [x] **Mutual exclusion rule** — sending both `create_category` and `upholstery_category_id` is a client error. The model validator raises `ValidationError`. Codex must not silently prefer one over the other.
- [x] **Transaction ownership** — no `maybe_begin` migration is required. The inline category creation is not a separate command composition. It is additional ORM work inside `create_upholstery`'s own `async with ctx.session.begin()` block. The whole thing (category + upholstery + inventory) commits atomically in one transaction.
- [x] **Conflict handling for inline category** — if `create_category.name` conflicts with an existing workspace category name, raise `ConflictError`. The upholstery is NOT created. The whole transaction rolls back.
- [x] **`client_id` for inline category** — optional, same validation prefix rule as standalone category creation (`"upc"` prefix via `validate_provided_client_id`). If not provided, the DB generates it.
- [x] **`favorite` default for inline category** — defaults to `False`, same as standalone `_CreateBody` in `upholstery_categories.py`.

---

## Acceptance criteria

1. `PUT /api/v1/upholsteries` with `create_category: {"name": "Möbeltyger"}` and no `upholstery_category_id` creates both a new `UpholsteryCategory` and a new `Upholstery` in one transaction; returns `{"upholstery": {..., "upholstery_category": {"id": "upc_...", "name": "Möbeltyger", "image_url": null}}}`.
2. `PUT /api/v1/upholsteries` with `upholstery_category_id: "upc_..."` and no `create_category` continues to link to an existing category (existing behavior unchanged).
3. `PUT /api/v1/upholsteries` with neither `create_category` nor `upholstery_category_id` creates an upholstery without a category (existing behavior unchanged).
4. `PUT /api/v1/upholsteries` with both `create_category` and `upholstery_category_id` returns `422` with a descriptive message.
5. `PUT /api/v1/upholsteries` with `create_category.name` that conflicts with an existing workspace category name returns `409` and does NOT create the upholstery.
6. `PUT /api/v1/upholsteries` with `create_category.client_id` that is already in use returns `409` and does NOT create the upholstery.
7. `PUT /api/v1/upholsteries` with `create_category: {"name": ""}` (blank name) returns `422` (caught by field validator on the request model).
8. The `create_upholstery_category` standalone command and its route `PUT /api/v1/upholstery-categories` are completely unaffected by this change.

---

## Contracts and skills

### Read order

| Contract | Applied rule |
|---|---|
| `architecture/06_commands.md` | Command signature, transaction ownership, request parsing, no cross-command calls |
| `architecture/06_commands_local.md` | `maybe_begin` — **explicitly excluded** (no cross-command composition; single transaction) |
| `architecture/09_routers.md` | Handler skeleton, `_CreateBody` as router-local Pydantic model, `build_ok`/`build_err` |
| `architecture/05_errors.md` | `ValidationError` for mutual exclusion, `ConflictError` for name/id conflicts |
| `architecture/21_naming_conventions.md` | Naming of new model and field |

### Applied contract deltas

- **06_commands_local.md `maybe_begin`**: Explicitly NOT applied. This plan adds inline DB work to one command's own transaction block. There is no parent/child command hierarchy. Using `ctx.session.begin()` (the existing pattern in `create_upholstery`) is correct and sufficient.
- **Router `_CreateBody`**: Router Pydantic models are declared in the router file. The new `_InlineCategoryBody` is also declared in `upholsteries.py` — not shared, not moved to a `schemas/` file, because it is only used by this one router.

### File read intent

Permitted relational reads (what exists):
- `routers/api_v1/upholsteries.py` — to know the current `_CreateBody` shape and route list
- `routers/api_v1/upholstery_categories.py` — to verify exact fields of the standalone category create body
- `services/commands/upholstery/create_upholstery.py` — to understand current transaction structure before extending it
- `services/commands/upholstery/create_upholstery_category.py` — to understand what inline category creation must replicate
- `services/commands/upholstery/requests/__init__.py` — to understand existing request model patterns and where to add new models

Prohibited (pattern reads — contracts cover these):
- Reading another command to understand `session.add` / `flush` shape → `06_commands.md`
- Reading another router to understand handler skeleton → `09_routers.md`

---

## Implementation plan

### Step 1 — Add `CreateUpholsteryCategoryInlineRequest` to the requests module

**File:** `app/beyo_manager/services/commands/upholstery/requests/__init__.py`

Add a new model class after the existing `CreateUpholsteryCategoryRequest` class (around line 269). This model represents the inline category payload embedded in the upholstery create request. It mirrors `CreateUpholsteryCategoryRequest` exactly — same fields, same validators — but is a separate class so it is semantically distinct:

```python
class CreateUpholsteryCategoryInlineRequest(BaseModel):
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
```

No standalone parse function is needed for this model — it is only ever parsed as part of `CreateUpholsteryRequest.model_validate()`.

---

### Step 2 — Extend `CreateUpholsteryRequest` with `create_category` field and mutual exclusion validator

**File:** `app/beyo_manager/services/commands/upholstery/requests/__init__.py`

Modify the existing `CreateUpholsteryRequest` class:

1. Add the import for `model_validator` at the top of the file alongside the existing pydantic imports:
   ```python
   from pydantic import BaseModel, field_validator, model_validator
   ```

2. Add the `create_category` field to `CreateUpholsteryRequest` after `upholstery_category_id`:
   ```python
   create_category: CreateUpholsteryCategoryInlineRequest | None = None
   ```

3. Add a `@model_validator(mode="after")` to enforce mutual exclusion after all fields are validated:
   ```python
   @model_validator(mode="after")
   def validate_category_fields(self) -> "CreateUpholsteryRequest":
       if self.create_category is not None and self.upholstery_category_id is not None:
           raise ValueError(
               "create_category and upholstery_category_id are mutually exclusive. "
               "Provide one or the other, not both."
           )
       return self
   ```

The complete updated `CreateUpholsteryRequest` body (showing only the changed/added lines):

```python
class CreateUpholsteryRequest(BaseModel):
    client_id: str | None = None
    name: str
    code: str | None = None
    image_url: str | None = None
    favorite: bool = False
    current_stored_amount_meters: Decimal | None = None
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None
    upholstery_category_id: str | None = None
    create_category: CreateUpholsteryCategoryInlineRequest | None = None  # NEW

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("name must not be blank.")
        return value

    @field_validator("low_stock_threshold_meters")
    @classmethod
    def create_threshold_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= Decimal("0"):
            raise ValueError("low_stock_threshold_meters must be greater than 0.")
        return v

    @field_validator("current_stored_amount_meters")
    @classmethod
    def create_current_stock_must_be_non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < Decimal("0"):
            raise ValueError("current_stored_amount_meters must be >= 0.")
        return v

    @field_validator("minimum_to_have", "maximum_to_have", "projected_inventory_value_minor")
    @classmethod
    def create_must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0.")
        return v

    @model_validator(mode="after")                                        # NEW
    def validate_category_fields(self) -> "CreateUpholsteryRequest":      # NEW
        if self.create_category is not None and self.upholstery_category_id is not None:
            raise ValueError(
                "create_category and upholstery_category_id are mutually exclusive. "
                "Provide one or the other, not both."
            )
        return self
```

---

### Step 3 — Extend `create_upholstery` command with inline category creation logic

**File:** `app/beyo_manager/services/commands/upholstery/create_upholstery.py`

Add `validate_provided_client_id` is already imported. No new imports are needed beyond what exists.

Replace the current `async with ctx.session.begin():` block to handle the three cases:

```python
async def create_upholstery(ctx: ServiceContext) -> dict:
    request = parse_create_upholstery_request(ctx.incoming_data)

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "uph")

    if request.create_category is not None and request.create_category.client_id is not None:
        validate_provided_client_id(request.create_category.client_id, "upc")

    category = None
    async with ctx.session.begin():
        uph_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(Upholstery, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            uph_kwargs["client_id"] = request.client_id

        name_conflict = await ctx.session.execute(
            select(Upholstery).where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.name == request.name,
                Upholstery.is_deleted.is_(False),
            )
        )
        if name_conflict.scalar_one_or_none() is not None:
            raise ConflictError("An upholstery with this name already exists in the workspace.")

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

        # --- resolve category (three mutually exclusive paths) ---

        resolved_category_id: str | None = None

        if request.create_category is not None:
            # Inline category creation — create the category within this same transaction.
            cat_req = request.create_category

            if cat_req.client_id is not None:
                dup_cat = await ctx.session.get(UpholsteryCategory, cat_req.client_id)
                if dup_cat is not None:
                    raise ConflictError("Provided category client_id is already in use.")

            cat_name_conflict = await ctx.session.execute(
                select(UpholsteryCategory).where(
                    UpholsteryCategory.workspace_id == ctx.workspace_id,
                    UpholsteryCategory.name == cat_req.name,
                    UpholsteryCategory.is_deleted.is_(False),
                )
            )
            if cat_name_conflict.scalar_one_or_none() is not None:
                raise ConflictError(
                    "An upholstery category with this name already exists in the workspace."
                )

            cat_kwargs: dict[str, str] = {}
            if cat_req.client_id is not None:
                cat_kwargs["client_id"] = cat_req.client_id

            category = UpholsteryCategory(
                **cat_kwargs,
                workspace_id=ctx.workspace_id,
                name=cat_req.name,
                image_url=cat_req.image_url,
                favorite=cat_req.favorite,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(category)
            await ctx.session.flush()  # needed to get category.client_id before upholstery is created
            resolved_category_id = category.client_id

        elif request.upholstery_category_id is not None:
            # Link to an existing category — existing behavior.
            category_result = await ctx.session.execute(
                select(UpholsteryCategory).where(
                    UpholsteryCategory.workspace_id == ctx.workspace_id,
                    UpholsteryCategory.client_id == request.upholstery_category_id,
                    UpholsteryCategory.is_deleted.is_(False),
                )
            )
            category = category_result.scalar_one_or_none()
            if category is None:
                raise NotFound("Upholstery category not found.")
            resolved_category_id = request.upholstery_category_id

        # else: no category — resolved_category_id stays None

        upholstery = Upholstery(
            **uph_kwargs,
            workspace_id=ctx.workspace_id,
            name=request.name,
            code=request.code,
            image_url=request.image_url,
            favorite=request.favorite,
            upholstery_category_id=resolved_category_id,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(upholstery)
        await ctx.session.flush()

        initial_stock = request.current_stored_amount_meters or Decimal("0")
        inventory_condition = evaluate_inventory_condition(
            stored=initial_stock,
            in_need=Decimal("0"),
            threshold=request.low_stock_threshold_meters,
        )

        inventory = UpholsteryInventory(
            workspace_id=ctx.workspace_id,
            upholstery_id=upholstery.client_id,
            inventory_condition=inventory_condition,
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

    return {"upholstery": serialize_upholstery(upholstery, inventory, category)}
```

**Key differences from the current implementation:**
- `upholstery_category_id=request.upholstery_category_id` is replaced by `upholstery_category_id=resolved_category_id`
- The category resolution is now a three-branch conditional: create inline → link existing → no category
- The inline category creation path does a `flush()` immediately after adding the category so `category.client_id` is available before the upholstery is constructed
- The `validate_provided_client_id` call for the inline category's `client_id` is done before the transaction opens (same pattern as the existing upholstery `client_id` validation)

---

### Step 4 — Extend the router body model

**File:** `app/beyo_manager/routers/api_v1/upholsteries.py`

Add `_InlineCategoryBody` as a new Pydantic model (before `_CreateBody`) and extend `_CreateBody` with a `create_category` field:

```python
class _InlineCategoryBody(BaseModel):
    client_id: str | None = None
    name: str
    image_url: str | None = None
    favorite: bool = False


class _CreateBody(BaseModel):
    client_id: str | None = None
    name: str
    code: str | None = None
    image_url: str | None = None
    favorite: bool = False
    current_stored_amount_meters: Decimal | None = None
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None
    upholstery_category_id: str | None = None
    create_category: _InlineCategoryBody | None = None  # NEW
```

No changes to `route_create_upholstery` itself — `body.model_dump()` automatically serializes the nested `_InlineCategoryBody` as a dict under the `create_category` key, which `CreateUpholsteryRequest.model_validate(data)` then parses correctly.

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| `model_validator` ordering: mutual exclusion fires before field validators complete | `mode="after"` means all field validators (including `normalize_name` on both `name` fields) run first. By the time `validate_category_fields` runs, `create_category` is already a fully validated `CreateUpholsteryCategoryInlineRequest` or `None`. |
| `flush()` for inline category inside the same `begin()` block causes partial commit | `flush()` is NOT a commit — it sends SQL to the DB within the open transaction. If the upholstery creation subsequently fails (e.g. name conflict), the whole transaction rolls back including the category row. This is the correct atomic behavior. |
| `category.client_id` not available before second `flush()` on upholstery | The inline category path calls `await ctx.session.flush()` immediately after `ctx.session.add(category)`. This causes the DB to assign and return `client_id`. Then `resolved_category_id = category.client_id` is set. The upholstery is then constructed with this ID. |
| Sending `create_category` with an existing category `name` creates orphan upholstery | The name conflict check raises `ConflictError` before the upholstery is added. The transaction rolls back. No partial state. |
| `validate_provided_client_id("upc")` called outside the transaction | This is a format/prefix check only — it raises `ValidationError` if the format is wrong but does NOT check the DB. The DB-level duplicate check happens inside the `begin()` block. Same pattern as the existing upholstery `client_id` validation. |
| `body.model_dump()` serializes `_InlineCategoryBody` as a nested dict | Pydantic v2 `model_dump()` on a model with a nested BaseModel field serializes the nested model as a `dict` by default. `CreateUpholsteryRequest.model_validate(data)` accepts this dict and constructs `CreateUpholsteryCategoryInlineRequest` from it. This is standard pydantic v2 behavior. |

---

## Validation plan

```bash
# 1. Inline category creation — happy path
curl -X PUT 'http://localhost:8000/api/v1/upholsteries' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Tyg Afrodite 2 Midnight",
    "code": "1000402",
    "create_category": {"name": "Tyg Afrodite", "image_url": null, "favorite": false}
  }' | jq
# Expected: upholstery_category.name == "Tyg Afrodite", upholstery.name == "Tyg Afrodite 2 Midnight"

# 2. Existing behavior — link to existing category
curl -X PUT 'http://localhost:8000/api/v1/upholsteries' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "Tyg B", "upholstery_category_id": "upc_existing_id"}' | jq
# Expected: upholstery_category.id == "upc_existing_id"

# 3. Existing behavior — no category
curl -X PUT 'http://localhost:8000/api/v1/upholsteries' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "Tyg C"}' | jq
# Expected: upholstery_category == null

# 4. Both fields set — must reject
curl -X PUT 'http://localhost:8000/api/v1/upholsteries' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Tyg D",
    "upholstery_category_id": "upc_existing_id",
    "create_category": {"name": "Another Category"}
  }' | jq
# Expected: HTTP 422 with error mentioning mutual exclusion

# 5. Inline category name conflict
curl -X PUT 'http://localhost:8000/api/v1/upholsteries' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "Tyg E", "create_category": {"name": "<existing_category_name>"}}' | jq
# Expected: HTTP 409, upholstery NOT created

# 6. Blank inline category name
curl -X PUT 'http://localhost:8000/api/v1/upholsteries' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "Tyg F", "create_category": {"name": ""}}' | jq
# Expected: HTTP 422

# 7. Standalone category route unchanged
curl -X PUT 'http://localhost:8000/api/v1/upholstery-categories' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "Test Category"}' | jq
# Expected: same response shape as before this change
```

---

## Review log

- `2026-06-25`: Implemented inline category creation in `create_upholstery`, added mutual-exclusion validation for category inputs, and verified the behavior with targeted unit tests plus `py_compile`.

---

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`

## Implementation summary

- Added `create_category` as an optional nested payload on `PUT /api/v1/upholsteries` and enforced that it cannot be sent together with `upholstery_category_id`.
- Extended `create_upholstery` so an inline category is created, flushed, and linked to the new upholstery inside the command’s existing transaction.
- Preserved existing behavior for requests that use `upholstery_category_id` or no category at all.
- Validation completed with focused request-model and command unit tests plus a static compile check; no live API smoke call was run in this task.
