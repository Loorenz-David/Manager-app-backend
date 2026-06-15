# PLAN_seat_tasks_pending_upholstery_20260615

## Metadata

- Plan ID: `PLAN_seat_tasks_pending_upholstery_20260615`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-15T00:00:00Z`
- Last updated at (UTC): `2026-06-15T12:15:46Z`
- Related issue/ticket: `n/a`
- Intention plan: `n/a`

## Goal and intent

- Goal: Two independent endpoints on `/api/v1/item-upholsteries`:
  1. **List** (`GET /pending-seat-tasks`) — paginated task list filtered to seat items with missing upholstery data. Supports `q` text search and `missing_selection`/`missing_quantity` filter params. Returns the same `tasks_pagination` shape as `list_tasks`.
  2. **Counts** (`GET /pending-seat-tasks/counts`) — lightweight endpoint that returns only two integers: total seat tasks with no upholstery record and total seat tasks with an upholstery record but no/zero quantity. No pagination, no entity loading, no `q` filter. Called independently by the frontend.
- Business/user intent: Give managers/workers a focused view of seat items blocked on upholstery data entry. The counts endpoint drives badge/counter UI independently of the paginated list.
- Non-goals: No mutation. No new migrations. No events or realtime. Does not touch non-seat items.

## Scope

- In scope:
  - New file `services/queries/items/seat_tasks_pending_upholstery.py` containing two functions:
    - `list_seat_tasks_pending_upholstery` — paginated list service
    - `get_seat_tasks_pending_upholstery_counts` — counts-only service
  - Two new static GET routes added to the existing `router` in `routers/api_v1/item_upholsteries.py`, both before the wildcard `/{client_id}` block:
    - `GET /pending-seat-tasks`
    - `GET /pending-seat-tasks/counts`
- Out of scope:
  - Migrations
  - Events / WebSocket push
  - Mutation commands
  - Non-primary task items
- Assumptions:
  - `item_major_category_snapshot` stores the seat semantic value; the implementation normalizes casing with `func.lower(...) == "seat"`.
  - "Primary item" is identified by `TaskItem.role == TaskItemRoleEnum.PRIMARY` and `TaskItem.removed_at IS NULL`.
  - A task has exactly one active primary item (enforced by unique index `uix_task_items_primary_active`).
  - Counts are global workspace totals — they are not filtered by `q`.

## Clarifications required

- [x] `item_major_category_snapshot` casing ambiguity handled in implementation by matching `func.lower(Item.item_major_category_snapshot) == "seat"`.

## Acceptance criteria

1. `GET /pending-seat-tasks` with no params returns `tasks_pagination` containing only tasks whose primary item has `item_major_category_snapshot == "seat"` and either no `ItemUpholstery` record or an `ItemUpholstery` with `amount_meters` null/zero.
2. `?missing_selection=true` narrows to tasks whose seat item has no upholstery record; tasks with an upholstery record (even with null `amount_meters`) are excluded.
3. `?missing_quantity=true` narrows to tasks whose seat item has an upholstery record but `amount_meters IS NULL OR amount_meters = 0`; tasks with no upholstery record are excluded.
4. `?missing_selection=true&missing_quantity=true` behaves identically to no filter (OR union of both conditions).
5. `?q=<text>` filters the paginated list using the same ilike pattern as `list_tasks` (task string columns + item columns + upholstery name/code).
6. Pagination (`limit`, `offset`, `has_more`) works correctly for the list endpoint.
7. Tasks whose primary item is NOT a seat are never returned.
8. `GET /pending-seat-tasks/counts` returns `{ "missing_selection_total": int, "missing_quantity_total": int }` with no other keys.
9. Counts reflect the full workspace scope — they are NOT affected by any filter params. A seat task with a missing upholstery is always counted regardless of whether the list endpoint is currently filtered to `missing_quantity` only.
10. ADMIN, MANAGER, WORKER roles have access to both endpoints. Other roles receive 403.

## Contracts and skills

### Contracts loaded

- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: query structure, offset pagination, two-phase ID → entity load pattern
- `backend/architecture/09_routers.md`: handler wiring, `ServiceContext` construction, `run_service` / `build_ok` / `build_err`
- `backend/architecture/21_naming_conventions.md`: file and function naming
- `backend/architecture/04_context.md`: `ServiceContext`, `workspace_id`, `user_id`
- `backend/architecture/55_search_filters.md` (if present): ilike/q param patterns (trigger: "q param", "partial match", "ilike")

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination override (cursor pagination is NOT used here)

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`07_queries.md`, `09_routers.md`)
- **What exists** → reading is legitimate

Permitted reads already done:
- `services/queries/tasks/tasks.py` — to confirm exact q-search join shape, ordering, pagination, and return structure
- `routers/api_v1/tasks.py` — to confirm query_params dict wiring pattern
- `models/tables/items/item.py` — `item_major_category_snapshot` field name/type
- `models/tables/items/item_upholstery.py` — `amount_meters` field name/type, `item_id` FK
- `models/tables/tasks/task_item.py` — `role` enum, `removed_at` sentinel, unique index confirming one primary per task
- `domain/tasks/serializers.py` — `serialize_task`, `serialize_item`, `serialize_image`, `serialize_image_light` shapes
- `routers/api_v1/item_upholsteries.py` — existing routes (static vs wildcard ordering, existing imports)

Prohibited:
- Reading another query file to understand the two-phase load pattern → `07_queries.md` covers it

### Skill selection

- Primary skill: `backend/architecture/07_queries.md` (query service)
- Router trigger terms: `q param`, `offset pagination`, `ilike`
- Excluded alternatives: command skill — no mutation

## Implementation plan

### Step 1 — Create `services/queries/items/seat_tasks_pending_upholstery.py`

Create a new file containing both service functions. Do not modify any existing file in this step.

```
backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py
```

**Imports required (used across both functions):**

```python
from sqlalchemy import String, and_, cast, distinct, func, or_, select

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.domain.tasks.serializers import serialize_item, serialize_task
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.context import ServiceContext
```

Note: `case` and `TaskPriorityEnum` are needed only if the ordering helper is inlined (see ordering note in function 1 below).

**Module-level constants:**

```python
_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_SEAT_MAJOR_CATEGORY = "seat"
```

---

#### Function 1 — `list_seat_tasks_pending_upholstery`

```python
async def list_seat_tasks_pending_upholstery(ctx: ServiceContext) -> dict:
```

**Logic outline** (implement in this exact order):

1. Extract params from `ctx.query_params`:
   - `limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)`
   - `offset = int(ctx.query_params.get("offset", 0))`
   - `q = ctx.query_params.get("q")`  — `str | None`
   - `missing_selection = bool(ctx.query_params.get("missing_selection", False))`
   - `missing_quantity = bool(ctx.query_params.get("missing_quantity", False))`

2. Build the base stmt selecting `Task.client_id`:
   ```python
   stmt = (
       select(Task.client_id)
       .where(
           Task.workspace_id == ctx.workspace_id,
           Task.is_deleted.is_(False),
       )
   )
   ```

3. Apply the static seat + primary-item filter via subquery:
   ```python
   seat_task_subq = (
       select(TaskItem.task_id)
       .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id))
       .where(
           TaskItem.workspace_id == ctx.workspace_id,
           TaskItem.removed_at.is_(None),
           TaskItem.role == TaskItemRoleEnum.PRIMARY,
           Item.is_deleted.is_(False),
           Item.item_major_category_snapshot == _SEAT_MAJOR_CATEGORY,
       )
       .distinct()
   )
   stmt = stmt.where(Task.client_id.in_(seat_task_subq))
   ```

4. Build the two missing-upholstery subqueries (always built; used both for filtering in this step and, if needed, reused):

   **`missing_selection_subq`** — primary seat item has NO active `ItemUpholstery`:
   ```python
   missing_selection_subq = (
       select(TaskItem.task_id)
       .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id))
       .outerjoin(
           ItemUpholstery,
           and_(
               ItemUpholstery.item_id == Item.client_id,
               ItemUpholstery.workspace_id == ctx.workspace_id,
               ItemUpholstery.is_deleted.is_(False),
           ),
       )
       .where(
           TaskItem.workspace_id == ctx.workspace_id,
           TaskItem.removed_at.is_(None),
           TaskItem.role == TaskItemRoleEnum.PRIMARY,
           Item.is_deleted.is_(False),
           Item.item_major_category_snapshot == _SEAT_MAJOR_CATEGORY,
           ItemUpholstery.client_id.is_(None),
       )
       .distinct()
   )
   ```

   **`missing_quantity_subq`** — primary seat item HAS an `ItemUpholstery` but `amount_meters` is null or zero:
   ```python
   missing_quantity_subq = (
       select(TaskItem.task_id)
       .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id))
       .join(
           ItemUpholstery,
           and_(
               ItemUpholstery.item_id == Item.client_id,
               ItemUpholstery.workspace_id == ctx.workspace_id,
               ItemUpholstery.is_deleted.is_(False),
           ),
       )
       .where(
           TaskItem.workspace_id == ctx.workspace_id,
           TaskItem.removed_at.is_(None),
           TaskItem.role == TaskItemRoleEnum.PRIMARY,
           Item.is_deleted.is_(False),
           Item.item_major_category_snapshot == _SEAT_MAJOR_CATEGORY,
           or_(ItemUpholstery.amount_meters.is_(None), ItemUpholstery.amount_meters == 0),
       )
       .distinct()
   )
   ```

   **Apply filter based on params:**
   ```python
   if missing_selection and not missing_quantity:
       stmt = stmt.where(Task.client_id.in_(missing_selection_subq))
   elif missing_quantity and not missing_selection:
       stmt = stmt.where(Task.client_id.in_(missing_quantity_subq))
   else:
       # both True or both False: OR union of both conditions
       stmt = stmt.where(
           or_(
               Task.client_id.in_(missing_selection_subq),
               Task.client_id.in_(missing_quantity_subq),
           )
       )
   ```

5. Apply `q` search filter using the same ilike pattern as `list_tasks`. All joins are outer so that tasks with no upholstery still match on task/item text fields:
   ```python
   if q:
       q_like = f"%{q}%"
       q_subq = (
           select(distinct(Task.client_id))
           .select_from(Task)
           .join(
               TaskItem,
               and_(
                   TaskItem.task_id == Task.client_id,
                   TaskItem.workspace_id == ctx.workspace_id,
                   TaskItem.removed_at.is_(None),
               ),
               isouter=True,
           )
           .join(
               Item,
               and_(
                   Item.client_id == TaskItem.item_id,
                   Item.workspace_id == ctx.workspace_id,
                   Item.is_deleted.is_(False),
               ),
               isouter=True,
           )
           .join(
               ItemUpholstery,
               and_(
                   ItemUpholstery.item_id == Item.client_id,
                   ItemUpholstery.workspace_id == ctx.workspace_id,
                   ItemUpholstery.is_deleted.is_(False),
               ),
               isouter=True,
           )
           .where(
               Task.workspace_id == ctx.workspace_id,
               or_(
                   Task.title.ilike(q_like),
                   cast(Task.additional_details, String).ilike(q_like),
                   Task.primary_phone_number.ilike(q_like),
                   Task.secondary_phone_number.ilike(q_like),
                   Task.primary_email.ilike(q_like),
                   Task.secondary_email.ilike(q_like),
                   Item.article_number.ilike(q_like),
                   Item.sku.ilike(q_like),
                   Item.designer.ilike(q_like),
                   Item.item_position.ilike(q_like),
                   Item.item_category_snapshot.ilike(q_like),
                   Item.item_major_category_snapshot.ilike(q_like),
                   ItemUpholstery.name.ilike(q_like),
                   ItemUpholstery.code.ilike(q_like),
               ),
           )
       )
       stmt = stmt.where(Task.client_id.in_(q_subq))
   ```

6. Apply ordering and pagination — reuse the same default ordering as `list_tasks`:
   ```python
   from beyo_manager.services.queries.tasks.tasks import _build_order_by

   stmt = stmt.order_by(*_build_order_by(ctx.query_params.get("order_by")))
   stmt = stmt.offset(offset).limit(limit + 1)
   ```

   > **Note on `_build_order_by`**: It is a private helper in `tasks.py`. If importing a private from another module is against local convention, inline the ordering logic using `case(...)` with `TaskPriorityEnum`. The plan prefers the import for DRY; adjust if the project convention disallows it.

7. Execute ID query, detect `has_more`, slice to `page_ids`. Early-return on empty:
   ```python
   result = await ctx.session.execute(stmt)
   task_ids = [row[0] for row in result.all()]
   has_more = len(task_ids) > limit
   page_ids = task_ids[:limit]
   if not page_ids:
       return {
           "tasks_pagination": {
               "items": [],
               "limit": limit,
               "offset": offset,
               "has_more": has_more,
           }
       }
   ```

8. Two-phase entity load (identical to `list_tasks`):
   - Load `Task` rows for `page_ids` → `task_map`
   - Load `TaskItem` rows for `page_ids` (where `removed_at IS NULL`) → derive `task_to_primary_item_id` and `primary_item_ids`
   - Load `Item` rows for `primary_item_ids` → `items_map`
   - Batch-load images: join `Image` + `ImageLink` where `entity_type == ImageLinkEntityTypeEnum.ITEM` and `entity_client_id IN primary_item_ids`, ordered by `display_order ASC` → `item_images_map`
   - First image per item: `serialize_image(image)`, subsequent: `serialize_image_light(image)`

9. Assemble payload in `page_ids` order:
   ```python
   items_payload = []
   for task_id in page_ids:
       task = task_map.get(task_id)
       if task is None:
           continue
       primary_item_id = task_to_primary_item_id.get(task_id)
       primary_item = items_map.get(primary_item_id)
       items_payload.append({
           "task": serialize_task(task),
           "primary_item": serialize_item(primary_item),
           "item_images": item_images_map.get(primary_item_id, []),
       })
   ```

10. Return:
    ```python
    return {
        "tasks_pagination": {
            "items": items_payload,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
    ```

---

#### Function 2 — `get_seat_tasks_pending_upholstery_counts`

Simple and self-contained. No pagination, no entity loading, no `q` filter. The seat category filter is already embedded inside each subquery, so no `seat_task_subq` needed.

```python
async def get_seat_tasks_pending_upholstery_counts(ctx: ServiceContext) -> dict:
```

**Logic outline:**

1. Build `missing_selection_subq` (identical to Function 1, step 4):
   ```python
   missing_selection_subq = (
       select(TaskItem.task_id)
       .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id))
       .outerjoin(
           ItemUpholstery,
           and_(
               ItemUpholstery.item_id == Item.client_id,
               ItemUpholstery.workspace_id == ctx.workspace_id,
               ItemUpholstery.is_deleted.is_(False),
           ),
       )
       .where(
           TaskItem.workspace_id == ctx.workspace_id,
           TaskItem.removed_at.is_(None),
           TaskItem.role == TaskItemRoleEnum.PRIMARY,
           Item.is_deleted.is_(False),
           Item.item_major_category_snapshot == _SEAT_MAJOR_CATEGORY,
           ItemUpholstery.client_id.is_(None),
       )
       .distinct()
   )
   ```

2. Build `missing_quantity_subq` (identical to Function 1, step 4):
   ```python
   missing_quantity_subq = (
       select(TaskItem.task_id)
       .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id))
       .join(
           ItemUpholstery,
           and_(
               ItemUpholstery.item_id == Item.client_id,
               ItemUpholstery.workspace_id == ctx.workspace_id,
               ItemUpholstery.is_deleted.is_(False),
           ),
       )
       .where(
           TaskItem.workspace_id == ctx.workspace_id,
           TaskItem.removed_at.is_(None),
           TaskItem.role == TaskItemRoleEnum.PRIMARY,
           Item.is_deleted.is_(False),
           Item.item_major_category_snapshot == _SEAT_MAJOR_CATEGORY,
           or_(ItemUpholstery.amount_meters.is_(None), ItemUpholstery.amount_meters == 0),
       )
       .distinct()
   )
   ```

3. Run two COUNT queries sequentially:
   ```python
   sel_result = await ctx.session.execute(
       select(func.count(Task.client_id))
       .where(
           Task.workspace_id == ctx.workspace_id,
           Task.is_deleted.is_(False),
           Task.client_id.in_(missing_selection_subq),
       )
   )
   missing_selection_total = sel_result.scalar_one() or 0

   qty_result = await ctx.session.execute(
       select(func.count(Task.client_id))
       .where(
           Task.workspace_id == ctx.workspace_id,
           Task.is_deleted.is_(False),
           Task.client_id.in_(missing_quantity_subq),
       )
   )
   missing_quantity_total = qty_result.scalar_one() or 0
   ```

   > `func.count(Task.client_id)` without `distinct` is correct: the outer SELECT hits `Task` directly via `IN` — one row per task, no join fan-out. The subqueries already use `.distinct()`.

4. Return:
   ```python
   return {
       "missing_selection_total": missing_selection_total,
       "missing_quantity_total": missing_quantity_total,
   }
   ```

---

### Step 2 — Add two routes to `routers/api_v1/item_upholsteries.py`

**Import**: Add to the existing imports block:
```python
from beyo_manager.services.queries.items.seat_tasks_pending_upholstery import (
    get_seat_tasks_pending_upholstery_counts,
    list_seat_tasks_pending_upholstery,
)
```

**Routes**: Both go in the "Static collection-level routes" section, before the wildcard `/{client_id}` block. Add after the existing `GET ""` route:

```python
@router.get("/pending-seat-tasks")
async def route_list_seat_tasks_pending_upholstery(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    missing_selection: bool = Query(False),
    missing_quantity: bool = Query(False),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "missing_selection": missing_selection,
            "missing_quantity": missing_quantity,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_seat_tasks_pending_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/pending-seat-tasks/counts")
async def route_get_seat_tasks_pending_upholstery_counts(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_seat_tasks_pending_upholstery_counts, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

> **Placement critical**: Both static routes MUST appear before the `@router.get("/{client_id}")` handler AND before any `@router.get("/{client_id}/...")` sub-path handlers. FastAPI matches routes in declaration order. `/pending-seat-tasks/counts` has two path segments after the prefix, so it could be captured by `/{client_id}/requirements` etc. if declared after them.

---

## Risks and mitigations

- Risk: `item_major_category_snapshot` stores a value other than `"seat"` (e.g. `"Seat"`, `"SEAT"`, or a translated string).
  Mitigation: Confirm the stored value before shipping. Use `func.lower(Item.item_major_category_snapshot) == "seat"` as a safe fallback if casing is inconsistent.

- Risk: `_build_order_by` is a private function imported across modules — if the tasks query module is refactored, this import breaks silently.
  Mitigation: If the project disallows cross-module private imports, inline the ordering logic (10 lines, uses `case` + `TaskPriorityEnum`).

- Risk: `/pending-seat-tasks/counts` placed after the `/{client_id}/...` wildcard sub-path routes.
  Mitigation: The plan explicitly requires both static routes before the wildcard block. Verify placement after editing.

- Risk: `missing_selection=true` and `missing_quantity=true` together being treated as AND rather than OR.
  Mitigation: The plan specifies OR (union) when both are true, matching the no-filter default behavior (acceptance criterion #4).

## Validation plan

**List endpoint:**
- `GET /pending-seat-tasks` with no params: returns `tasks_pagination` containing only seat-item tasks with missing upholstery data.
- `?missing_selection=true`: no task in response has a non-deleted `ItemUpholstery` for its primary item.
- `?missing_quantity=true`: every task in response has an `ItemUpholstery`, but `amount_meters` is null or 0.
- `?q=<known task title>`: result is filtered correctly.
- `?limit=2&offset=0`: `has_more` is `true` if more than 2 results exist.

**Counts endpoint:**
- `GET /pending-seat-tasks/counts`: returns `{ "missing_selection_total": <int>, "missing_quantity_total": <int> }` with no other top-level keys.
- Value of `missing_selection_total` matches the number of tasks returned by `?missing_selection=true` with no limit (manually verified on a known dataset).
- Value is unchanged when calling `GET /pending-seat-tasks?missing_quantity=true` — confirms counts are independent of the list's filter params.

**Both endpoints:**
- Request with a non-ADMIN/MANAGER/WORKER token: returns 403.
- Tasks whose primary item is not a seat: never appear in either response.

## Review log

- `2026-06-15`: Implemented query module and router endpoints. Seat-category matching was made case-insensitive to avoid depending on snapshot casing.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
