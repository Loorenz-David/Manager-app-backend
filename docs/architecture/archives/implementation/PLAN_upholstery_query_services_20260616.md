# PLAN_upholstery_query_services_20260616

## Metadata

- Plan ID: `PLAN_upholstery_query_services_20260616`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-16T16:00:00Z`
- Last updated at (UTC): `2026-06-16T15:11:56Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Implement 4 read-only query services and their router handlers for the upholstery ordering domain.
- Business/user intent: Give the frontend a complete picture of what upholsteries need ordering (with aggregated counts, amounts, and due dates), the tasks driving each need, the list of created upholstery orders with their statuses, and the tasks affected by specific upholsteries.
- Non-goals: Mutations, allocation, push notifications, events. No model/enum/migration changes beyond the 3 indexes added in Step 1.

## Scope

- In scope:
  - 1 Alembic migration adding 3 missing indexes.
  - `services/queries/upholstery/upholstery_order_needs.py` — 2 new query functions.
  - `services/queries/upholstery/upholstery_orders_query.py` — 2 new query functions.
  - `routers/api_v1/upholstery_order_needs.py` — new router file, 2 GET handlers.
  - `routers/api_v1/upholstery_orders.py` — append 2 GET handlers + import `Query`.
  - `routers/api_v1/__init__.py` — register new router.
- Out of scope: Command mutations, model changes, existing router modifications beyond appending handlers.
- Assumptions:
  - `ItemUpholsteryRequirement.upholstery_inventory_id` points to `UpholsteryInventory.client_id` (no FK constraint declared, join done manually).
  - Tasks connect to items via `TaskItem`; the primary item has `TaskItem.role.value == "primary"`.
  - `UpholsteryOrder.upholstery_inventory_id` → `UpholsteryInventory.client_id` → `UpholsteryInventory.upholstery_id` → `Upholstery.client_id`.

## Clarifications required

(None — all ambiguities resolved in design session.)

## Acceptance criteria

1. `GET /api/v1/upholstery-order-needs` returns `upholstery_needs_pagination` with per-upholstery item_count, total_amount_meters, earliest_due_date; only upholsteries that have ≥1 NEEDS_ORDERING requirement appear.
2. `GET /api/v1/upholstery-order-needs/{upholstery_id}/items` returns `tasks_pagination` (same shape as list_tasks) extended with an `item_upholstery` object per task.
3. `GET /api/v1/upholstery-orders` returns `orders_pagination` with joined upholstery metadata and supports `states` CSV filter.
4. `GET /api/v1/upholstery-orders/items` returns `tasks_pagination` extended with `item_upholstery`, filtered by `upholstery_ids` (required CSV) and optional `requirement_states` CSV.
5. `q` applies correctly across all 4 endpoints as specified per-service below.
6. `GET /api/v1/upholstery-order-needs/count` returns `{ "needs_ordering_count": int, "upholstery_count": int }` in a single query with no joins — fast enough for badge rendering on page load.
7. `GET /api/v1/upholstery-orders/count` returns `{ "total": int, "by_state": { state_value: int, ... } }` for all orders (or only the requested states when `states` CSV param is provided). Single GROUP BY query, no joins.
8. `python3 -m py_compile` passes on all new and modified files.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: overall principles
- `backend/architecture/04_context.md`: `ServiceContext` shape — `ctx.query_params`, `ctx.incoming_data`, `ctx.workspace_id`, `ctx.user_id`
- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: query service structure, offset pagination with `limit + 1` trick
- `backend/architecture/09_routers.md`: thin handler wiring via `run_service`
- `backend/architecture/21_naming_conventions.md`: naming
- `backend/architecture/40_identity.md`: PK prefix conventions

### File read intent — pattern vs. relational

Before writing, Codex must read (relational reads — what already exists):

- `backend/app/beyo_manager/services/queries/tasks/tasks.py` — exact q columns list, `_split_csv`, `_build_order_by`, pagination pattern, image batch-load pattern. **Copy these helpers directly; do not re-derive from contracts.**
- `backend/app/beyo_manager/domain/tasks/serializers.py` — `serialize_task`, `serialize_item`, `serialize_image`, `serialize_image_light` signatures.
- A recent Alembic migration file (any under `backend/alembic/versions/`) — to match the migration file format exactly. Also read `backend/architecture/30_migrations.md` for CONCURRENTLY DDL rules.

Prohibited pattern reads (already covered by contracts):
- Reading another command file to understand session/flush structure.
- Reading another router to understand handler skeleton.

## Implementation plan

---

### Step 1 — Migration: 3 new indexes

**File**: new Alembic migration under `backend/alembic/versions/`.

Read an existing migration file first to match `revision`, `down_revision`, `branch_labels`, `depends_on` header format exactly.
Read `backend/architecture/30_migrations.md` to confirm CONCURRENTLY DDL rules.

CONCURRENTLY `CREATE INDEX` cannot run inside a transaction. The migration must use AUTOCOMMIT mode or the established app pattern for non-transactional DDL.

**Indexes to create**:

| Index name | Table | Columns | Reason |
|---|---|---|---|
| `ix_item_upholstery_requirements_workspace_state` | `item_upholstery_requirements` | `(workspace_id, state)` | Service 1 aggregates ALL NEEDS_ORDERING requirements per workspace |
| `ix_item_upholstery_requirements_workspace_inventory_id` | `item_upholstery_requirements` | `(workspace_id, upholstery_inventory_id)` | Services 1 and 3 join IUR → UpholsteryInventory; no FK constraint means no auto-index |
| `ix_item_upholsteries_workspace_upholstery_id` | `item_upholsteries` | `(workspace_id, upholstery_id)` | Services 2 and 4 filter item_upholsteries by workspace + upholstery_id |

```python
def upgrade() -> None:
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_item_upholstery_requirements_workspace_state "
        "ON item_upholstery_requirements (workspace_id, state)"
    )
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_item_upholstery_requirements_workspace_inventory_id "
        "ON item_upholstery_requirements (workspace_id, upholstery_inventory_id)"
    )
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_item_upholsteries_workspace_upholstery_id "
        "ON item_upholsteries (workspace_id, upholstery_id)"
    )

def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_item_upholstery_requirements_workspace_state")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_item_upholstery_requirements_workspace_inventory_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_item_upholsteries_workspace_upholstery_id")
```

---

### Step 2 — New file: `services/queries/upholstery/upholstery_order_needs.py`

#### Imports

```python
from datetime import datetime, timezone
from sqlalchemy import String, and_, case, cast, distinct, func, or_, select
from sqlalchemy.orm import ...  # as needed

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.tasks.serializers import serialize_item, serialize_task
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory
from beyo_manager.services.context import ServiceContext
```

#### Module-level

```python
_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_NEEDS_ORDERING = ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
```

Copy `_split_csv` verbatim from `services/queries/tasks/tasks.py`.

---

#### `get_upholstery_order_needs_count(ctx: ServiceContext) -> dict`

No params. Single aggregate query — no joins, no pagination.

```python
result = await ctx.session.execute(
    select(
        func.count().label("needs_ordering_count"),
        func.count(distinct(ItemUpholsteryRequirement.upholstery_inventory_id)).label("upholstery_count"),
    ).where(
        ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
        ItemUpholsteryRequirement.is_deleted.is_(False),
        ItemUpholsteryRequirement.state == _NEEDS_ORDERING,
    )
)
row = result.one()
return {
    "needs_ordering_count": row.needs_ordering_count,
    "upholstery_count": row.upholstery_count,
}
```

- `needs_ordering_count`: total NEEDS_ORDERING requirement records in the workspace.
- `upholstery_count`: count of distinct `upholstery_inventory_id` values among those records (proxy for distinct upholsteries needing ordering; rows with NULL `upholstery_inventory_id` are excluded from the distinct count by SQL semantics).

This query is served entirely by the new `ix_item_upholstery_requirements_workspace_state` index added in Step 1 — no table heap access, no joins.

---

#### `list_upholstery_order_needs(ctx: ServiceContext) -> dict`

**Params from `ctx.query_params`**: `limit` (int, default 50, max 200), `offset` (int, default 0), `q` (str | None).

**Phase 1 — Aggregation + pagination**

Build an aggregate `select` over upholsteries that have ≥1 NEEDS_ORDERING requirement:

```
SELECT
  Upholstery.client_id,
  Upholstery.name,
  Upholstery.code,
  Upholstery.image_url,
  COUNT(DISTINCT ItemUpholsteryRequirement.client_id)  AS item_count,
  COALESCE(SUM(ItemUpholsteryRequirement.amount_meters), 0) AS total_amount_meters
FROM upholsteries
INNER JOIN upholstery_inventory
  ON upholstery_inventory.upholstery_id = upholsteries.client_id
  AND upholstery_inventory.workspace_id = :ws
  AND upholstery_inventory.is_deleted IS FALSE
INNER JOIN item_upholstery_requirements
  ON item_upholstery_requirements.upholstery_inventory_id = upholstery_inventory.client_id
  AND item_upholstery_requirements.workspace_id = :ws
  AND item_upholstery_requirements.is_deleted IS FALSE
  AND item_upholstery_requirements.state = 'needs_ordering'
LEFT JOIN item_upholsteries
  ON item_upholsteries.client_id = item_upholstery_requirements.item_upholstery_id
  AND item_upholsteries.workspace_id = :ws
  AND item_upholsteries.is_deleted IS FALSE
LEFT JOIN items
  ON items.client_id = item_upholsteries.item_id
  AND items.workspace_id = :ws
  AND items.is_deleted IS FALSE
LEFT JOIN task_items
  ON task_items.item_id = items.client_id
  AND task_items.workspace_id = :ws
  AND task_items.removed_at IS NULL
LEFT JOIN tasks
  ON tasks.client_id = task_items.task_id
  AND tasks.workspace_id = :ws
  AND tasks.is_deleted IS FALSE
WHERE upholsteries.workspace_id = :ws
  AND upholsteries.is_deleted IS FALSE
  [AND upholsteries.client_id IN (q_subq)  -- only when q is set]
GROUP BY upholsteries.client_id, upholsteries.name, upholsteries.code, upholsteries.image_url
ORDER BY MIN(tasks.ready_by_at) ASC NULLS LAST, upholsteries.name ASC
OFFSET :offset LIMIT :limit+1
```

The outer joins to the task chain exist solely to allow `MIN(tasks.ready_by_at)` as an ORDER BY aggregate. The COUNT/SUM aggregate only counts NEEDS_ORDERING requirements (guaranteed by the inner join on IUR).

**If `q` is set** — build a `q_subq` that selects `Upholstery.client_id` through the same join chain (with outer joins on the task side) and filters by:

```python
or_(
    Upholstery.name.ilike(q_like),
    Upholstery.code.ilike(q_like),
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
)
```

Apply `.distinct()` to `q_subq`. Then: `agg_stmt = agg_stmt.where(Upholstery.client_id.in_(q_subq))`.

After execution: extract `page = rows[:limit]`, `has_more = len(rows) > limit`, `page_upholstery_ids = [r.client_id for r in page]`.

**Phase 2 — Batch due-date query (closest to now per upholstery)**

If `page_upholstery_ids` is non-empty, run a CTE with `ROW_NUMBER()`:

```python
ranked_cte = (
    select(
        Upholstery.client_id.label("upholstery_id"),
        Task.ready_by_at.label("ready_by_at"),
        func.row_number().over(
            partition_by=Upholstery.client_id,
            order_by=[
                # NULL ready_by_at sorts last
                case((Task.ready_by_at.is_(None), 1), else_=0).asc(),
                func.abs(
                    func.extract("epoch", Task.ready_by_at)
                    - func.extract("epoch", func.now())
                ).asc(),
                Task.created_at.asc(),
            ],
        ).label("rn"),
    )
    .select_from(Upholstery)
    .join(UpholsteryInventory, and_(...))
    .join(ItemUpholsteryRequirement, and_(..., IUR.state == _NEEDS_ORDERING))
    .join(ItemUpholstery, and_(...))
    .join(Item, and_(...))
    .join(TaskItem, and_(...))
    .join(Task, and_(...))
    .where(Upholstery.client_id.in_(page_upholstery_ids))
    .cte("ranked")
)

due_date_rows = await ctx.session.execute(
    select(ranked_cte.c.upholstery_id, ranked_cte.c.ready_by_at)
    .where(ranked_cte.c.rn == 1)
)
due_date_map: dict[str, datetime | None] = {
    row.upholstery_id: row.ready_by_at for row in due_date_rows
}
```

All joins in the CTE are **inner joins** (not outer) — only upholsteries with tasks can have a due date; those without tasks get `None` from the map default.

**Response**:

```python
return {
    "upholstery_needs_pagination": {
        "items": [
            {
                "upholstery_id": row.client_id,
                "upholstery_name": row.name,
                "upholstery_code": row.code,
                "upholstery_image_url": row.image_url,
                "item_count": row.item_count,
                "total_amount_meters": float(row.total_amount_meters),
                "earliest_due_date": (
                    due_date_map[row.client_id].date().isoformat()
                    if due_date_map.get(row.client_id) is not None
                    else None
                ),
            }
            for row in page
        ],
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
    }
}
```

---

#### `get_upholstery_order_need_items(ctx: ServiceContext) -> dict`

**Params**: `upholstery_id` from `ctx.incoming_data["upholstery_id"]`; `limit`, `offset`, `q` from `ctx.query_params`.

**Phase 1 — Task ID query**

```python
stmt = select(Task.client_id).where(
    Task.workspace_id == ctx.workspace_id,
    Task.is_deleted.is_(False),
)
```

Apply upholstery filter subquery:

```python
uph_subq = (
    select(TaskItem.task_id)
    .join(Item, and_(
        Item.client_id == TaskItem.item_id,
        Item.workspace_id == ctx.workspace_id,
        Item.is_deleted.is_(False),
    ))
    .join(ItemUpholstery, and_(
        ItemUpholstery.item_id == Item.client_id,
        ItemUpholstery.workspace_id == ctx.workspace_id,
        ItemUpholstery.is_deleted.is_(False),
        ItemUpholstery.upholstery_id == upholstery_id,
    ))
    .join(ItemUpholsteryRequirement, and_(
        ItemUpholsteryRequirement.item_upholstery_id == ItemUpholstery.client_id,
        ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
        ItemUpholsteryRequirement.is_deleted.is_(False),
        ItemUpholsteryRequirement.state == _NEEDS_ORDERING,
    ))
    .where(
        TaskItem.workspace_id == ctx.workspace_id,
        TaskItem.removed_at.is_(None),
    )
    .distinct()
)
stmt = stmt.where(Task.client_id.in_(uph_subq))
```

**If `q` is set** — apply a q subquery matching the same column list as `list_tasks` (copy the `q_subq` block from `tasks.py` verbatim, including `ItemUpholstery.name.ilike` and `ItemUpholstery.code.ilike`). Note: do NOT include `Upholstery.name/code` here — the upholstery is fixed by path param, and the q is searching task + item fields only.

ORDER BY: use `_build_order_by` from `tasks.py` with the default (no `order_by` param). Copy `_build_order_by` into this file or import it from a shared location.

Apply `.offset(offset).limit(limit + 1)`.

**Phase 2 — Load tasks, items, images** — copy the three-batch pattern from `list_tasks` (task_map, task_items_result, primary_item_ids, items_map, item_images_map).

**Phase 3 — Load ItemUpholstery extras for the page**

```python
iup_map: dict[str, ItemUpholstery] = {}
if primary_item_ids:
    iup_result = await ctx.session.execute(
        select(ItemUpholstery).where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.item_id.in_(primary_item_ids),
            ItemUpholstery.upholstery_id == upholstery_id,
            ItemUpholstery.is_deleted.is_(False),
        )
    )
    iup_map = {iup.item_id: iup for iup in iup_result.scalars().all()}
```

**Response**:

```python
items_payload = []
for task_id in page_ids:
    task = task_map.get(task_id)
    if task is None:
        continue
    primary_item_id = task_to_primary_item_id.get(task_id)
    primary_item = items_map.get(primary_item_id)
    iup = iup_map.get(primary_item_id) if primary_item_id else None
    items_payload.append({
        "task": serialize_task(task),
        "primary_item": serialize_item(primary_item),
        "item_images": item_images_map.get(primary_item_id, []),
        "item_upholstery": {
            "client_id": iup.client_id,
            "amount_meters": float(iup.amount_meters) if iup.amount_meters is not None else None,
        } if iup is not None else None,
    })

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

### Step 3 — New file: `services/queries/upholstery/upholstery_orders_query.py`

Named `upholstery_orders_query.py` (not `upholstery_orders.py`) to avoid shadowing the router module in imports.

#### Imports

Same as Step 2, plus:
- `UpholsteryOrder` from `beyo_manager.models.tables.upholstery.upholstery_order`
- Remove `Upholstery`-specific serializers (inline serialization below).

Copy `_split_csv` from `tasks.py`.

---

#### `get_upholstery_orders_count(ctx: ServiceContext) -> dict`

**Param from `ctx.query_params`**: `states` (str | None) — optional CSV of `UpholsteryOrderStateEnum` string values.

Single GROUP BY query — no joins, no pagination:

```python
states_list = _split_csv(ctx.query_params.get("states"))

stmt = (
    select(UpholsteryOrder.state, func.count().label("count"))
    .where(
        UpholsteryOrder.workspace_id == ctx.workspace_id,
        UpholsteryOrder.is_deleted.is_(False),
    )
    .group_by(UpholsteryOrder.state)
)
if states_list:
    stmt = stmt.where(UpholsteryOrder.state.in_(states_list))

rows = (await ctx.session.execute(stmt)).all()
by_state = {row.state.value: row.count for row in rows}
return {
    "total": sum(by_state.values()),
    "by_state": by_state,
}
```

Served entirely by the existing index `ix_upholstery_orders_workspace_state_created` on `(workspace_id, state, created_at)` — no new index needed.

**Response shape**:
```json
{
  "total": 18,
  "by_state": {
    "draft": 3,
    "ordered": 10,
    "partially_received": 2,
    "received": 3
  }
}
```

Only states that have ≥1 order appear in `by_state`. When the `states` param is provided, only the requested states are counted.

---

#### `list_upholstery_orders(ctx: ServiceContext) -> dict`

**Params from `ctx.query_params`**: `limit`, `offset`, `q`, `states` (CSV of `UpholsteryOrderStateEnum` string values).

**Main query** — selects `(UpholsteryOrder, Upholstery)` tuples with outer joins:

```python
stmt = (
    select(UpholsteryOrder, Upholstery)
    .outerjoin(UpholsteryInventory, and_(
        UpholsteryInventory.client_id == UpholsteryOrder.upholstery_inventory_id,
        UpholsteryInventory.workspace_id == ctx.workspace_id,
        UpholsteryInventory.is_deleted.is_(False),
    ))
    .outerjoin(Upholstery, and_(
        Upholstery.client_id == UpholsteryInventory.upholstery_id,
        Upholstery.workspace_id == ctx.workspace_id,
        Upholstery.is_deleted.is_(False),
    ))
    .where(
        UpholsteryOrder.workspace_id == ctx.workspace_id,
        UpholsteryOrder.is_deleted.is_(False),
    )
    .order_by(UpholsteryOrder.created_at.desc())
    .offset(offset)
    .limit(limit + 1)
)
```

**If `states` is set**: `.where(UpholsteryOrder.state.in_(states_list))`

**If `q` is set**: apply a q subquery that selects `UpholsteryOrder.client_id`. The subquery outer-joins the full chain:

```
UpholsteryOrder
  → (outer) UpholsteryInventory  ON inventory.client_id = order.upholstery_inventory_id
  → (outer) Upholstery           ON upholstery.client_id = inventory.upholstery_id
  → (outer) ItemUpholsteryRequirement  ON iur.upholstery_inventory_id = order.upholstery_inventory_id
                                        AND iur.workspace_id = :ws AND iur.is_deleted IS FALSE
  → (outer) ItemUpholstery       ON iu.client_id = iur.item_upholstery_id
                                  AND iu.workspace_id = :ws AND iu.is_deleted IS FALSE
  → (outer) Item                 ON item.client_id = iu.item_id
                                  AND item.workspace_id = :ws AND item.is_deleted IS FALSE
  → (outer) TaskItem             ON ti.item_id = item.client_id
                                  AND ti.workspace_id = :ws AND ti.removed_at IS NULL
  → (outer) Task                 ON task.client_id = ti.task_id
                                  AND task.workspace_id = :ws AND task.is_deleted IS FALSE
```

WHERE: same `or_()` as Service 1's q filter (Upholstery.name, Upholstery.code, all task/item string columns). Apply `.distinct()`.

**Response** — iterate `(order, upholstery)` tuples (upholstery may be None):

```python
return {
    "orders_pagination": {
        "items": [
            {
                "client_id": order.client_id,
                "upholstery_id": upholstery.client_id if upholstery else None,
                "upholstery_name": upholstery.name if upholstery else None,
                "upholstery_code": upholstery.code if upholstery else None,
                "upholstery_image_url": upholstery.image_url if upholstery else None,
                "order_amount_meters": float(order.order_amount_meters),
                "expected_receive_at": order.expected_receive_at.isoformat() if order.expected_receive_at else None,
                "received_at": order.received_at.isoformat() if order.received_at else None,
                "state": order.state.value,
                "supplier_id": order.supplier_id,
            }
            for order, upholstery in page
        ],
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
    }
}
```

---

#### `list_upholstery_order_items(ctx: ServiceContext) -> dict`

**Params from `ctx.query_params`**: `limit`, `offset`, `q`, `upholstery_ids` (CSV, required), `requirement_states` (CSV, optional).

If `upholstery_ids_list` is empty, return early:
```python
return {"tasks_pagination": {"items": [], "limit": limit, "offset": offset, "has_more": False}}
```

**Phase 1 — Task ID query**

```python
stmt = select(Task.client_id).where(
    Task.workspace_id == ctx.workspace_id,
    Task.is_deleted.is_(False),
)
```

**Filter by `upholstery_ids`** (always applied):

```python
uph_subq = (
    select(TaskItem.task_id)
    .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id, Item.is_deleted.is_(False)))
    .join(ItemUpholstery, and_(
        ItemUpholstery.item_id == Item.client_id,
        ItemUpholstery.workspace_id == ctx.workspace_id,
        ItemUpholstery.is_deleted.is_(False),
        ItemUpholstery.upholstery_id.in_(upholstery_ids_list),
    ))
    .where(TaskItem.workspace_id == ctx.workspace_id, TaskItem.removed_at.is_(None))
    .distinct()
)
stmt = stmt.where(Task.client_id.in_(uph_subq))
```

**Filter by `requirement_states`** (optional, when non-empty):

```python
req_subq = (
    select(TaskItem.task_id)
    .join(Item, ...)
    .join(ItemUpholstery, and_(..., ItemUpholstery.upholstery_id.in_(upholstery_ids_list)))
    .join(ItemUpholsteryRequirement, and_(
        ItemUpholsteryRequirement.item_upholstery_id == ItemUpholstery.client_id,
        ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
        ItemUpholsteryRequirement.is_deleted.is_(False),
        ItemUpholsteryRequirement.state.in_(requirement_states_list),
    ))
    .where(TaskItem.workspace_id == ctx.workspace_id, TaskItem.removed_at.is_(None))
    .distinct()
)
stmt = stmt.where(Task.client_id.in_(req_subq))
```

**If `q` is set** — same q subquery as `get_upholstery_order_need_items` **plus** include `Upholstery.name.ilike(q_like)` and `Upholstery.code.ilike(q_like)` (outer-join `Upholstery` on `Upholstery.client_id == ItemUpholstery.upholstery_id`).

ORDER BY: same default as `list_tasks`. Apply `.offset(offset).limit(limit + 1)`.

**Phase 2 — Load tasks, items, images** — identical batch pattern to Phase 2 of `get_upholstery_order_need_items`.

**Phase 3 — Load ItemUpholstery extras**

```python
iup_map: dict[str, ItemUpholstery] = {}
if primary_item_ids:
    iup_result = await ctx.session.execute(
        select(ItemUpholstery).where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.item_id.in_(primary_item_ids),
            ItemUpholstery.upholstery_id.in_(upholstery_ids_list),
            ItemUpholstery.is_deleted.is_(False),
        )
    )
    for iup in iup_result.scalars().all():
        iup_map.setdefault(iup.item_id, iup)  # first match wins if multiple upholsteries per item
```

**Response**: same `tasks_pagination` shape as `get_upholstery_order_need_items`.

---

### Step 4 — New router: `routers/api_v1/upholstery_order_needs.py`

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.upholstery_order_needs import (
    get_upholstery_order_need_items,
    get_upholstery_order_needs_count,
    list_upholstery_order_needs,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/upholstery-order-needs", tags=["upholstery-order-needs"])


@router.get("/count")
async def route_get_upholstery_order_needs_count(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_upholstery_order_needs_count, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_upholstery_order_needs(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
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
    outcome = await run_service(list_upholstery_order_needs, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{upholstery_id}/items")
async def route_get_upholstery_order_need_items(
    upholstery_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
):
    ctx = ServiceContext(
        incoming_data={"upholstery_id": upholstery_id},
        query_params={"limit": limit, "offset": offset, "q": q},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_upholstery_order_need_items, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

### Step 5 — Extend: `routers/api_v1/upholstery_orders.py`

**Read the file before editing.**

Add to imports:
```python
from fastapi import APIRouter, Depends, Query  # add Query
from beyo_manager.services.queries.upholstery.upholstery_orders_query import (
    get_upholstery_orders_count,
    list_upholstery_order_items,
    list_upholstery_orders,
)
```

Append three GET handlers after the existing `route_receive_upholstery_order` handler:

```python
@router.get("/count")
async def route_get_upholstery_orders_count(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    states: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"states": states},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_upholstery_orders_count, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_upholstery_orders(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    states: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q, "states": states},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholstery_orders, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/items")
async def route_list_upholstery_order_items(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    upholstery_ids: str | None = Query(None),
    requirement_states: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "upholstery_ids": upholstery_ids,
            "requirement_states": requirement_states,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholstery_order_items, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Registration note**: `GET /items` must be declared before any future `GET /{order_id}` handler in this router. FastAPI resolves literal path segments before path parameters in registration order.

---

### Step 6 — Register router: `routers/api_v1/__init__.py`

**Read the file before editing.**

Add import alongside existing upholstery imports:
```python
from beyo_manager.routers.api_v1 import (
    ...
    upholstery_order_needs,   # add this line
    upholstery_orders,
    ...
)
```

Add registration after `upholstery_orders`:
```python
app.include_router(upholstery_order_needs.router)
```

---

## Risks and mitigations

- Risk: Aggregate query in `list_upholstery_order_needs` joins 6 tables and can be slow.
  Mitigation: 3 new indexes in Step 1 cover all critical join columns. All joins are workspace-scoped.

- Risk: q subquery in `list_upholstery_orders` traverses 7 hops (order → inventory → upholstery + IUR → IU → item → task_item → task).
  Mitigation: All outer joins; `.distinct()` on subquery prevents fanout. Existing indexes on task/item chain handle the inner sides.

- Risk: `GET /items` literal route conflicting with a future `GET /{order_id}` path-param route.
  Mitigation: Register `GET /items` first (Step 5 appends it before any `/{order_id}` handler); FastAPI literal-before-param ordering applies.

- Risk: `upholstery_orders_query.py` name may seem unconventional.
  Mitigation: Keeps the module name distinct from the router module `upholstery_orders.py`. Consistent naming within the queries directory.

## Validation plan

- `python3 -m py_compile backend/app/beyo_manager/services/queries/upholstery/upholstery_order_needs.py`: passes
- `python3 -m py_compile backend/app/beyo_manager/services/queries/upholstery/upholstery_orders_query.py`: passes
- `python3 -m py_compile backend/app/beyo_manager/routers/api_v1/upholstery_order_needs.py`: passes
- `python3 -m py_compile backend/app/beyo_manager/routers/api_v1/upholstery_orders.py`: passes
- `python3 -m py_compile backend/app/beyo_manager/routers/api_v1/__init__.py`: passes
- `rg -n "route_get_upholstery_order_needs_count\|route_list_upholstery_order_needs\|route_get_upholstery_order_need_items" backend/app/beyo_manager/routers/api_v1/upholstery_order_needs.py`: returns all three handlers
- `rg -n "route_get_upholstery_orders_count\|route_list_upholstery_orders\|route_list_upholstery_order_items" backend/app/beyo_manager/routers/api_v1/upholstery_orders.py`: returns all three handlers
- `rg -n "upholstery_order_needs" backend/app/beyo_manager/routers/api_v1/__init__.py`: returns import + include_router

## Review log

(none)

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`

## Implementation summary

- Added the planned read-only upholstery ordering query services, router handlers, and the supporting Alembic index migration.
- Static compile validation passed, route registration was confirmed with `rg`, and import-level app bootstrap remains blocked in this shell by missing required local settings.
