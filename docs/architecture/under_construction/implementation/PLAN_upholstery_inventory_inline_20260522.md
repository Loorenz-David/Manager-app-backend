# PLAN_upholstery_inventory_inline_20260522

## Metadata

- Plan ID: `PLAN_upholstery_inventory_inline_20260522`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-22T00:00:00Z`
- Last updated at (UTC): `2026-05-22T15:50:50Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- **Goal:** Extend `serialize_upholstery` and its callers to inline two inventory fields — `current_stored_amount_meters` and `inventory_condition` — so the list and get endpoints return stock context without extra round-trips from the client.
- **Business/user intent:** Frontend form fields showing upholstery options need to display stock status alongside name and image without making a second API call per record.
- **Non-goals:** Changing any router path or adding new endpoints. The `GET /api/v1/upholsteries/{client_id}` endpoint already exists and requires no router changes.

## Scope

- **In scope:**
  - Extend `serialize_upholstery` in `domain/upholstery/serializers.py` to accept an optional `UpholsteryInventory` and emit two new fields.
  - Extend `list_upholsteries` in `services/queries/upholstery/upholsteries.py` to batch-load inventory records for the current page in a single additional query (no N+1).
  - Extend `get_upholstery` in the same file to load the single inventory record alongside the upholstery.
  - No router file changes.

- **Out of scope:**
  - Adding new router files or new route handlers.
  - Surfacing any other `UpholsteryInventory` fields beyond the two specified.
  - Changing `serialize_upholstery_inventory` or any other existing serializer.

- **Assumptions:**
  - The partial unique index `uix_upholstery_inventory_workspace_upholstery_active` — `UNIQUE (workspace_id, upholstery_id) WHERE is_deleted = false` — guarantees **at most one** active inventory row per upholstery. The batch map will therefore have at most one entry per `upholstery_id`; `scalar_one_or_none()` is safe for the single get.
  - An upholstery with no inventory row is valid; the fields must be returned as `null`.
  - `current_stored_amount_meters` is a `Decimal` column and must be serialized as a `str` (consistent with the existing `serialize_upholstery_inventory` pattern). Never return a raw `Decimal` — it is not JSON-serializable.

## Clarifications required

*(none — requirements fully specified)*

## Acceptance criteria

1. `GET /api/v1/upholsteries` response includes `current_stored_amount_meters` (string or `null`) and `inventory_condition` (string or `null`) on every upholstery record.
2. `GET /api/v1/upholsteries/{client_id}` response includes the same two fields on the single record.
3. The list endpoint issues exactly **one** inventory batch query per page, not one per row.
4. An upholstery with no inventory row returns `null` for both fields.
5. An upholstery with `current_stored_amount_meters = NULL` in the DB returns `null` for that field (not an error).
6. Existing callers of `serialize_upholstery` that do not pass an inventory continue to receive `null` for both new fields (the parameter is optional with default `None`).

## Contracts and skills

### Contracts loaded

- `backend/architecture/07_queries.md`: query signature, workspace scope, result extraction
- `backend/architecture/07_queries_local.md`: offset pagination pattern (no changes to pagination shape required)
- `backend/architecture/46_serialization.md`: serializers are pure functions, no DB access, accept pre-fetched data as arguments

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset override (no change needed here — pagination shape unchanged)

### File read intent — pattern vs. relational

Permitted relational reads (explicitly allowed):
- `models/tables/upholstery/upholstery_inventory.py` — exact field names, types, and the partial unique index confirming 1:1 active relationship
- `services/queries/upholstery/upholsteries.py` — current implementation to extend it correctly
- `domain/upholstery/serializers.py` — current `serialize_upholstery` signature to extend it

Prohibited:
- Reading another query for pagination or workspace scope shape → `07_queries_local.md` already covers this
- Reading another serializer to understand output structure → `46_serialization.md`

### Skill selection

- Primary skill: `backend/architecture/46_serialization.md` (serializer extension), `backend/architecture/07_queries.md` (batch load pattern)
- Excluded alternatives: command skill — no writes in scope

## Implementation plan

Execute steps in order. Step 2 depends on Step 1.

---

### Step 1 — Extend `serialize_upholstery` in `domain/upholstery/serializers.py`

**File:** `backend/app/beyo_manager/domain/upholstery/serializers.py`

Add the `UpholsteryInventory` import and extend the function signature and body. Do **not** alter `serialize_upholstery_inventory`.

Replace the current `serialize_upholstery` function:

```python
# BEFORE
def serialize_upholstery(row: Upholstery, primary_image: Image | None = None) -> dict:
    return {
        "client_id": row.client_id,
        "name": row.name,
        "code": row.code,
        "image_url": serialize_image_light(primary_image)["image_url"] if primary_image else None,
    }
```

With:

```python
# AFTER
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory


def serialize_upholstery(
    row: Upholstery,
    primary_image: Image | None = None,
    inventory: UpholsteryInventory | None = None,
) -> dict:
    return {
        "client_id": row.client_id,
        "name": row.name,
        "code": row.code,
        "image_url": serialize_image_light(primary_image)["image_url"] if primary_image else None,
        "current_stored_amount_meters": (
            str(inventory.current_stored_amount_meters)
            if inventory is not None and inventory.current_stored_amount_meters is not None
            else None
        ),
        "inventory_condition": inventory.inventory_condition.value if inventory is not None else None,
    }
```

**Rules:**
- The `inventory` parameter is the raw `UpholsteryInventory` ORM object, not a dict.
- `current_stored_amount_meters` is a `Decimal` — always convert to `str`. Never return a raw `Decimal`.
- Both new fields must be `null` when `inventory is None`. Do not raise.
- The `UpholsteryInventory` import must be added at the top of the file with the other imports — not inline inside the function.

---

### Step 2 — Extend `list_upholsteries` and `get_upholstery` in `services/queries/upholstery/upholsteries.py`

**File:** `backend/app/beyo_manager/services/queries/upholstery/upholsteries.py`

Add the `UpholsteryInventory` import at the top of the file with the existing imports:

```python
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
```

#### 2a — `list_upholsteries`

After the existing image batch load block and before the `return` statement, add an inventory batch load block using the same page-scoped pattern:

```python
    # Batch-load active inventory per upholstery — single query, no N+1.
    # The partial unique index guarantees at most one active row per upholstery_id.
    inventory_map: dict[str, UpholsteryInventory] = {}
    if page:
        inv_result = await ctx.session.execute(
            select(UpholsteryInventory).where(
                UpholsteryInventory.workspace_id == ctx.workspace_id,
                UpholsteryInventory.upholstery_id.in_(upholstery_ids),
                UpholsteryInventory.is_deleted.is_(False),
            )
        )
        inventory_map = {inv.upholstery_id: inv for inv in inv_result.scalars().all()}
```

Then update the `return` statement to pass the inventory to the serializer:

```python
    return {
        "upholsteries": [
            serialize_upholstery(u, images_map.get(u.client_id), inventory_map.get(u.client_id))
            for u in page
        ],
        "upholsteries_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
```

**Important notes for `list_upholsteries`:**
- `upholstery_ids` is already defined in the existing image batch block — do not redefine it. Place the inventory batch block immediately after the image batch block so it reuses the same variable.
- The inventory block must be guarded by `if page:` to avoid querying when the page is empty — consistent with the image batch block.
- Use `{inv.upholstery_id: inv for inv in ...}` as the map key, not `client_id`. The lookup in the serializer call is `inventory_map.get(u.client_id)` where `u.client_id` is the upholstery's `client_id`, which matches `UpholsteryInventory.upholstery_id`.

#### 2b — `get_upholstery`

After fetching the upholstery record and before the image query, add:

```python
    inv_result = await ctx.session.execute(
        select(UpholsteryInventory).where(
            UpholsteryInventory.workspace_id == ctx.workspace_id,
            UpholsteryInventory.upholstery_id == upholstery.client_id,
            UpholsteryInventory.is_deleted.is_(False),
        )
    )
    inventory = inv_result.scalar_one_or_none()
```

Then update the `return` statement to pass the inventory:

```python
    return {"upholstery": serialize_upholstery(upholstery, primary_image, inventory)}
```

**`scalar_one_or_none()` is safe here** because the partial unique index guarantees at most one active row per upholstery.

---

## Risks and mitigations

- **Risk:** `upholstery_ids` variable is referenced by both the image batch block and the new inventory batch block. If a future refactor moves or renames that variable, the inventory block breaks silently.
  **Mitigation:** Place the inventory batch block immediately after the image batch block and use the same `upholstery_ids` variable. No separate definition.

- **Risk:** `current_stored_amount_meters` is `Decimal` — accidentally removing the `str()` cast would cause a JSON serialization error at runtime.
  **Mitigation:** The cast is explicit in the serializer. The pattern matches `serialize_upholstery_inventory` in the same file.

- **Risk:** An upholstery row exists but its inventory row has `current_stored_amount_meters = NULL`.
  **Mitigation:** The double-guard `if inventory is not None and inventory.current_stored_amount_meters is not None` in the serializer handles this correctly, returning `null` without raising.

## Validation plan

- `GET /api/v1/upholsteries` response shape includes `current_stored_amount_meters` and `inventory_condition` on each record.
- `GET /api/v1/upholsteries/{client_id}` response shape includes both fields.
- For an upholstery with no inventory row: both fields are `null`.
- Query count on list page: 3 queries total (upholsteries, images, inventories) — not `2 + N`.

## Review log

- `2026-05-22T15:50:50Z` — Implemented Step 1 and Step 2 strictly: serializer and upholstery query layer updates only (no router changes).
- `2026-05-22T15:50:50Z` — Validation: backend app venv import smoke passed; no upholstery-specific tests exist in `tests/`.
- `2026-05-22T15:50:50Z` — Lifecycle progressed implemented -> summarized -> archived with linked summary and archive record.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `copilot`
