# PLAN_find_or_create_item_20260518

## Metadata

- Plan ID: `PLAN_find_or_create_item_20260518`
- Status: `under_construction`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-18T00:00:00Z`
- Related issue/ticket: `task-system-prerequisite`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`

---

## Goal and intent

- **Goal:** Add `find_or_create_item` command to the items domain — a command that looks up an item by `article_number OR sku` and either updates its fields if found or creates it if not found, returning `{client_id, was_created}`.
- **Business/user intent:** CMD-1 (`create_task`) must atomically link or create the primary item in the same transaction. Item identity is controlled by `article_number` or `sku`; the task system should never blindly create duplicate items.
- **Non-goals:**
  - No item issues or item upholstery in this command. Issues and upholstery are created by separate session-level helpers AFTER `find_or_create_item` returns, still within the same CMD-1 transaction.
  - No task creation logic of any kind.
  - No changes to existing item commands (`create_item`, `update_item`).

---

## Scope

- **In scope:**
  - New Pydantic request model: `FindOrCreateItemRequest`
  - New parse function: `parse_find_or_create_item_request`
  - New command: `find_or_create_item(ctx: ServiceContext) -> dict`
  - New route: `POST /api/v1/items/find-or-create` (ADMIN, MANAGER only)
- **Out of scope:**
  - No migration — all columns exist on `items`
  - No item issues, item upholstery, or requirement logic
  - No realtime events or outbox publishing
  - No changes to existing item commands or queries
- **Assumptions:**
  - `Item.article_number` and `Item.sku` each have partial unique indexes scoped to `(workspace_id, article_number)` and `(workspace_id, sku)` where `is_deleted = false`. These already exist on the model.
  - The `maybe_begin` utility already exists at `beyo_manager/services/commands/utils/transaction.py`.
  - The `ItemCategory` table and its FK already exist.

---

## Clarifications required

_None. All design decisions are locked in the intention plan._

---

## Acceptance criteria

1. `POST /api/v1/items/find-or-create` with a new `article_number` (not yet in the workspace) creates the item and returns `{"client_id": "<new_id>", "was_created": true}`.
2. `POST /api/v1/items/find-or-create` with an existing `article_number` returns the existing item's `client_id` with `"was_created": false`, and updates any other fields present in the payload on the existing item.
3. `POST /api/v1/items/find-or-create` with an existing `sku` (and no `article_number`) behaves identically to criterion 2 via the `sku` match path.
4. `POST /api/v1/items/find-or-create` with neither `article_number` nor `sku` returns a `ValidationError` (HTTP 422).
5. When an existing item is found and `item_category_id` is present in the payload, both `item_category_snapshot` and `item_major_category_snapshot` are updated to reflect the new category. If `item_category_id` is explicitly null in the payload, both snapshot columns are cleared.
6. When an existing item is found, only fields explicitly sent in the request body are updated (`model_fields_set` semantics) — absent fields leave the existing item columns unchanged.
7. When creating a new item, `quantity` defaults to `1` if not provided.
8. `article_number` and `sku` are stripped of leading/trailing whitespace and coerced to `None` if the resulting string is empty, in both the lookup and create paths.
9. The route `POST /api/v1/items/find-or-create` is registered **before** `GET /api/v1/items/{client_id}` in the router to prevent FastAPI routing ambiguity.
10. The command works correctly as a subordinate (called from within CMD-1's `maybe_begin` block) — it uses the existing session without opening a nested transaction.

---

## Contracts and skills

### Contracts loaded

Read these contracts **in full** before writing any code. They are the authoritative pattern source — do not substitute them with readings of other implementation files.

- `backend/architecture/01_architecture.md`: overall structure, module layout
- `backend/architecture/04_context.md`: `ServiceContext` — how `incoming_data`, `workspace_id`, `user_id`, `session` are accessed
- `backend/architecture/05_errors.md`: `ValidationError`, `NotFound` — where they live, how they are raised
- `backend/architecture/06_commands.md`: command skeleton, `maybe_begin` owner/subordinate mode, session call safety rules
- `backend/architecture/06_commands_local.md`: app-specific additions — `maybe_begin` transaction utility, subordinate-command event rule (subordinate commands must not fire their own events)
- `backend/architecture/09_routers.md`: router handler skeleton, how `build_ok` / `build_err` are used, `body.model_dump(exclude_unset=True)` for PATCH-style handlers
- `backend/architecture/21_naming_conventions.md`: file names, function names, class names

### Local extensions loaded

- `backend/architecture/06_commands_local.md` extends `06_commands.md`: adds `maybe_begin` import path and subordinate-command event rule. **Local wins on conflict.**

### File read intent — pattern vs. relational

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

**Permitted relational reads (understand what exists):**

| File | What to extract |
|---|---|
| `beyo_manager/services/commands/items/requests/__init__.py` | Exact existing class names, parse function names, `@field_validator` patterns, `ValidationError` import path — to add alongside without breaking existing code |
| `beyo_manager/services/commands/customers/find_or_create_customer.py` | Exact `maybe_begin` usage, `or_` lookup pattern, early-return shape inside `maybe_begin` block, return dict shape `{client_id, was_created}` |
| `beyo_manager/services/commands/items/update_item.py` | Exact `_DIRECT_FIELDS` set, `model_fields_set` loop, `item_category_id` snapshot-update block, `updated_at` / `updated_by_id` assignment |
| `beyo_manager/models/tables/items/item.py` | Exact column names, nullable flags, `is_deleted` column name |
| `beyo_manager/routers/api_v1/items.py` | Route order to know where to insert `find-or-create` (must be before `GET /{client_id}`) |

**Prohibited pattern reads (contract already covers these):**

- Do NOT read any other command to learn `maybe_begin` / `session.add` / `flush` / error-raising shape — `06_commands.md` defines this.
- Do NOT read the customer router to learn handler wiring — `09_routers.md` defines this.
- Do NOT read `create_item.py` to learn command structure — `06_commands.md` defines this. Reading it only to check what fields Item accepts is permitted.

### Skill selection

- Primary skill: `backend/task_system/backend_contract_goal_mapping_guide.md`
- Goal bundle: **CRUD + realtime** (minus sockets/events — not needed here; selected for model + command contracts)
- Excluded alternatives: `16_background_jobs.md` — no async worker; `13_sockets.md` — no realtime; `30_migrations.md` — no schema change

---

## Implementation plan

Execute steps in order. Do not skip ahead.

### Step 1 — Add `FindOrCreateItemRequest` and parse function to `requests/__init__.py`

**File:** `backend/app/beyo_manager/services/commands/items/requests/__init__.py`

**Action:** Append to the end of the file (after all existing classes and parse functions). Do NOT modify existing classes or parse functions.

Add the following class and parse function:

```python
class FindOrCreateItemRequest(BaseModel):
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


def parse_find_or_create_item_request(data: dict) -> FindOrCreateItemRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return FindOrCreateItemRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

**Notes:**
- `ItemCurrencyEnum` is already imported in the file — do not re-import.
- `field_validator` is already imported — do not re-import.
- `ValidationError` (from `beyo_manager.errors.validation`) is already imported — do not re-import.
- The `strip_or_none` validator is identical to the one in `CreateItemRequest` — this is intentional. Both classes are independent; do not introduce a shared base class.

---

### Step 2 — Create `find_or_create_item.py` command

**File:** `backend/app/beyo_manager/services/commands/items/find_or_create_item.py` _(new file)_

**Full implementation:**

```python
"""Find existing Item by article_number or sku, update its fields if found, create if not found."""

from datetime import datetime, timezone

from sqlalchemy import or_, select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.commands.items.requests import (
    FindOrCreateItemRequest,
    parse_find_or_create_item_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


_DIRECT_FIELDS = {
    "article_number",
    "sku",
    "quantity",
    "designer",
    "height_in_cm",
    "width_in_cm",
    "depth_in_cm",
    "item_value_minor",
    "item_cost_minor",
    "item_currency",
    "item_position",
    "external_id",
    "external_url",
    "external_source",
    "external_order_id",
}


async def find_or_create_item(ctx: ServiceContext) -> dict:
    """Return an existing active item matched by article_number or sku, updating its fields; create if not found."""
    request = parse_find_or_create_item_request(ctx.incoming_data)

    if request.article_number is None and request.sku is None:
        raise ValidationError("At least one of article_number or sku must be provided.")

    async with maybe_begin(ctx.session):
        lookup_conditions = []
        if request.article_number is not None:
            lookup_conditions.append(Item.article_number == request.article_number)
        if request.sku is not None:
            lookup_conditions.append(Item.sku == request.sku)

        existing_result = await ctx.session.execute(
            select(Item)
            .where(
                Item.workspace_id == ctx.workspace_id,
                Item.is_deleted.is_(False),
                or_(*lookup_conditions),
            )
            .limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            # Update fields present in the payload (model_fields_set semantics)
            for field_name in _DIRECT_FIELDS:
                if field_name in request.model_fields_set:
                    setattr(existing, field_name, getattr(request, field_name))

            if "item_category_id" in request.model_fields_set:
                existing.item_category_id = request.item_category_id
                if request.item_category_id is None:
                    existing.item_category_snapshot = None
                    existing.item_major_category_snapshot = None
                else:
                    category_result = await ctx.session.execute(
                        select(ItemCategory).where(
                            ItemCategory.workspace_id == ctx.workspace_id,
                            ItemCategory.client_id == request.item_category_id,
                            ItemCategory.is_deleted.is_(False),
                        )
                    )
                    category = category_result.scalar_one_or_none()
                    if category is None:
                        raise NotFound("ItemCategory not found.")
                    existing.item_category_snapshot = category.name
                    existing.item_major_category_snapshot = category.major_category.value

            existing.updated_at = datetime.now(timezone.utc)
            existing.updated_by_id = ctx.user_id

            return {"client_id": existing.client_id, "was_created": False}

        # Item not found — create it
        item_category_snapshot: str | None = None
        item_major_category_snapshot: str | None = None
        if request.item_category_id is not None:
            category_result = await ctx.session.execute(
                select(ItemCategory).where(
                    ItemCategory.workspace_id == ctx.workspace_id,
                    ItemCategory.client_id == request.item_category_id,
                    ItemCategory.is_deleted.is_(False),
                )
            )
            category = category_result.scalar_one_or_none()
            if category is None:
                raise NotFound("ItemCategory not found.")
            item_category_snapshot = category.name
            item_major_category_snapshot = category.major_category.value

        from beyo_manager.domain.items.enums import ItemStateEnum

        item = Item(
            workspace_id=ctx.workspace_id,
            article_number=request.article_number,
            sku=request.sku,
            state=ItemStateEnum.PENDING,
            item_category_id=request.item_category_id,
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
            item_category_snapshot=item_category_snapshot,
            item_major_category_snapshot=item_major_category_snapshot,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(item)
        await ctx.session.flush()

    return {"client_id": item.client_id, "was_created": True}
```

**Critical implementation notes:**

1. **`ItemStateEnum` import placement**: Import `ItemStateEnum` at the top of the file from `beyo_manager.domain.items.enums`, not inside the function body. The inline import shown above is for illustration only — move it to the top-level imports.

2. **Early return inside `maybe_begin` block**: Returning `{"client_id": existing.client_id, "was_created": False}` from inside the `async with maybe_begin(ctx.session):` block is valid Python — the `__aexit__` of `maybe_begin` will still run (commit if owner mode, no-op if subordinate). This is the same pattern used in `find_or_create_customer`.

3. **`updated_at` / `updated_by_id` always set on update path**: Even if no scalar field changed (e.g., the payload only contained the lookup key), these two columns are always set when the item is found. This matches the `update_item` pattern.

4. **No events, no outbox**: This command is a prerequisite for CMD-1. CMD-1 (the owner) is responsible for any events. This command fires nothing.

5. **`maybe_begin` subordinate mode**: When called from CMD-1's `async with maybe_begin(ctx.session):` block, this command's `maybe_begin` call detects the active transaction and yields the bare session. No nested transaction is opened.

6. **`item` variable scope for create path**: `item` is assigned inside the `async with maybe_begin` block. The `return {"client_id": item.client_id, "was_created": True}` at the end of the function is **outside** the `async with` block — identical to `find_or_create_customer`. This is correct: `item.client_id` is populated after `flush()`, and the variable remains in scope after the `async with` exits.

---

### Step 3 — Add route to `items.py` router

**File:** `backend/app/beyo_manager/routers/api_v1/items.py`

**Action:** Add the following import and route handler.

**Import to add** (alongside existing command imports):
```python
from beyo_manager.services.commands.items.find_or_create_item import find_or_create_item
```

**Route body model to add** (alongside existing body models, before the route handlers):
```python
class _FindOrCreateItemBody(BaseModel):
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
```

**Route handler to add** — insert this handler **before** `@router.get("/{client_id}")`. It must appear before any `/{client_id}` route to avoid FastAPI treating `find-or-create` as a path parameter:

```python
@router.post("/find-or-create")
async def route_find_or_create_item(
    body: _FindOrCreateItemBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(exclude_unset=True),
        identity=claims,
        session=session,
    )
    outcome = await run_service(find_or_create_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Critical router note:** `body.model_dump(exclude_unset=True)` is used here (not `body.model_dump()`). This propagates `model_fields_set` correctly into `incoming_data` so the command can distinguish "caller omitted this field" from "caller explicitly sent null". If `model_dump()` (without `exclude_unset=True`) were used, every optional field would appear in `incoming_data` even if the caller never sent it, making `model_fields_set` useless for the update path.

**Route order verification:** After the edit, the order in `items.py` must be:
```
PUT    ""                → route_create_item
GET    ""                → route_list_items
POST   "/{client_id}/issues" → route_create_item_issue
POST   "/find-or-create" → route_find_or_create_item   ← NEW (must be here)
GET    "/{client_id}"    → route_get_item
PATCH  "/{client_id}"   → route_update_item
DELETE "/{client_id}"   → route_delete_item
```

---

## Risks and mitigations

- **Risk:** `item` variable used after `async with` block on the create path — could cause `UnboundLocalError` if control flow is wrong.
  **Mitigation:** The create path returns ONLY after `flush()` populates `item.client_id`. The return statement is outside `async with` but `item` is still in scope (same function). This is the identical pattern to `find_or_create_customer`. Do not move the return inside the `async with` block.

- **Risk:** `model_dump(exclude_unset=True)` not used in the router → all optional fields appear as `None` in `incoming_data` → `model_fields_set` on the request object inside the command contains ALL fields → every field on an existing item is overwritten with `None`.
  **Mitigation:** Acceptance criterion 9 requires `model_dump(exclude_unset=True)`. The validation plan bash test verifies partial-update semantics.

- **Risk:** FastAPI routing ambiguity — `POST /find-or-create` registered after `GET /{client_id}` causes FastAPI to match `find-or-create` as a `client_id` value.
  **Mitigation:** Acceptance criterion 9 requires the route order. Step 3 specifies exact insertion point. The validation plan verifies the route resolves correctly.

- **Risk:** Duplicate `@field_validator` names in `requests/__init__.py` if Copilot re-declares `strip_or_none` or `quantity_must_be_positive` in the new class with a name that conflicts at module level.
  **Mitigation:** Pydantic validators are class-scoped, not module-scoped. Two classes can each have a `strip_or_none` validator independently — this is not a conflict.

---

## Validation plan

Run from `backend/` directory. Requires a running server and a valid admin credential.

### Manual bash test

```bash
# ── Configuration ──────────────────────────────────────────────────────────────
BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="$1"      # e.g. admin@beyo.dev
PASSWORD="$2"   # e.g. Admin1234!
TIMESTAMP=$(date +%s)

# Sign in
TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/sign-in" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"app_scope\":\"admin\"}" \
  | jq -r '.data.access_token')
echo "Token: ${#TOKEN} chars"

ART="ART_FIND_${TIMESTAMP}"
SKU="SKU_FIND_${TIMESTAMP}"

# ── Test 1: ValidationError — no lookup key ────────────────────────────────────
echo "--- Test 1: no article_number or sku → ValidationError"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"designer":"NoKey"}')
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
[ "$STATUS" == "422" ] && echo "✅ PASS (422)" || echo "❌ FAIL (got $STATUS)"

# ── Test 2: Create new item by article_number ──────────────────────────────────
echo "--- Test 2: create new item by article_number"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"article_number\":\"$ART\",\"designer\":\"DesignerA\",\"quantity\":3}")
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
BODY=$(echo "$R" | sed '/_STATUS_:/d')
ITEM_ID=$(echo "$BODY" | jq -r '.data.client_id')
WAS_CREATED=$(echo "$BODY" | jq -r '.data.was_created')
[ "$STATUS" == "200" ] && [ "$WAS_CREATED" == "true" ] && [ "$ITEM_ID" != "null" ] \
  && echo "✅ PASS (created, id=$ITEM_ID)" || echo "❌ FAIL (status=$STATUS was_created=$WAS_CREATED)"

# ── Test 3: Find existing item by article_number, update designer ──────────────
echo "--- Test 3: find existing by article_number, update designer"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"article_number\":\"$ART\",\"designer\":\"DesignerB\"}")
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
BODY=$(echo "$R" | sed '/_STATUS_:/d')
ITEM_ID2=$(echo "$BODY" | jq -r '.data.client_id')
WAS_CREATED2=$(echo "$BODY" | jq -r '.data.was_created')
[ "$STATUS" == "200" ] && [ "$WAS_CREATED2" == "false" ] && [ "$ITEM_ID2" == "$ITEM_ID" ] \
  && echo "✅ PASS (found same id, was_created=false)" || echo "❌ FAIL (status=$STATUS was_created=$WAS_CREATED2 id=$ITEM_ID2)"

# ── Test 4: Partial-update semantics — quantity not sent, must be preserved ────
echo "--- Test 4: partial-update — quantity omitted, must stay 3"
GET_R=$(curl -s "$BASE_URL/api/v1/items/$ITEM_ID" -H "Authorization: Bearer $TOKEN")
QTY=$(echo "$GET_R" | jq -r '.data.item.quantity // empty')
[ "$QTY" == "3" ] && echo "✅ PASS (quantity=3 preserved)" || echo "❌ FAIL (quantity=$QTY)"

# ── Test 5: Create new item by sku only ───────────────────────────────────────
echo "--- Test 5: create by sku only"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"sku\":\"$SKU\"}")
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
BODY=$(echo "$R" | sed '/_STATUS_:/d')
ITEM_ID3=$(echo "$BODY" | jq -r '.data.client_id')
WAS_CREATED3=$(echo "$BODY" | jq -r '.data.was_created')
[ "$STATUS" == "200" ] && [ "$WAS_CREATED3" == "true" ] \
  && echo "✅ PASS (sku create, id=$ITEM_ID3)" || echo "❌ FAIL (status=$STATUS was_created=$WAS_CREATED3)"

# ── Test 6: Find existing by sku ──────────────────────────────────────────────
echo "--- Test 6: find existing by sku"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"sku\":\"$SKU\"}")
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
BODY=$(echo "$R" | sed '/_STATUS_:/d')
ITEM_ID4=$(echo "$BODY" | jq -r '.data.client_id')
WAS_CREATED4=$(echo "$BODY" | jq -r '.data.was_created')
[ "$STATUS" == "200" ] && [ "$WAS_CREATED4" == "false" ] && [ "$ITEM_ID4" == "$ITEM_ID3" ] \
  && echo "✅ PASS (found same sku item, was_created=false)" || echo "❌ FAIL (status=$STATUS was_created=$WAS_CREATED4)"

echo ""
echo "All find_or_create_item tests done."
```

Save to: `backend/tests/items/test_find_or_create_item.sh`

### Checklist

- [ ] `POST /api/v1/items/find-or-create` route resolves (no 404, no routing to `GET /{client_id}`)
- [ ] Test 1 passes (no lookup key → 422)
- [ ] Test 2 passes (create new, `was_created=true`)
- [ ] Test 3 passes (find existing by `article_number`, `was_created=false`, same `client_id`)
- [ ] Test 4 passes (`quantity` preserved when not in payload — partial semantics)
- [ ] Test 5 passes (create new by `sku`, `was_created=true`)
- [ ] Test 6 passes (find existing by `sku`, `was_created=false`)

---

## Review log

_Empty — awaiting implementation._

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
