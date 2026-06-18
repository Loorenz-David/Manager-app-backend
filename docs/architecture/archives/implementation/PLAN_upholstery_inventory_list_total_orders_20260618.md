# PLAN_upholstery_inventory_list_total_orders_20260618

## Metadata

- Plan ID: `PLAN_upholstery_inventory_list_total_orders_20260618`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-18T00:00:00Z`
- Last updated at (UTC): `2026-06-18T13:07:31Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Add `total_orders` (count of active orders) to each item returned by `list_upholstery_inventories`.
- Business/user intent: The inventory list screen needs to surface how many in-flight orders exist for each inventory entry, so the user can see ordering activity at a glance without navigating into each inventory.
- Non-goals: Changing the full inventory serializer (`serialize_upholstery_inventory`), modifying order state transitions, or adding meters/amount aggregations (only count of orders is in scope).

## Scope

- In scope:
  - Define which `UpholsteryOrderStateEnum` values are considered "active".
  - Add a second aggregation query in `list_upholstery_inventories` to count active orders per inventory ID.
  - Update `serialize_upholstery_inventory_partial` to accept and emit `total_orders`.
- Out of scope:
  - `get_upholstery_inventory` (single-item endpoint) — not touched.
  - Any migration — no schema change required.
  - Filtering/sorting by `total_orders`.
- Assumptions:
  - "Active" means the order is still in-progress: `DRAFT`, `PENDING`, `APPROVED`, `ORDERED`, `PARTIALLY_RECEIVED`. Terminal states (`FAILED`, `CANCELLED`, `RECEIVED`) are excluded.
  - `total_orders = null` when the count is 0 (as requested by user).
  - `is_deleted = false` guard on `UpholsteryOrder` applies.

## Clarifications required

- [ ] Confirm which states are considered "active" — the plan assumes `DRAFT, PENDING, APPROVED, ORDERED, PARTIALLY_RECEIVED`. If `DRAFT` should be excluded (e.g. drafts are not real orders yet), the active set changes.
- [ ] Confirm `total_orders = null` for zero vs. `total_orders = 0`. Current plan emits `null` for zero as stated.

## Acceptance criteria

1. Each item in `upholstery_inventories_pagination.items` includes a `total_orders` key.
2. `total_orders` equals the count of non-deleted orders for that inventory whose `state` is in the active set.
3. `total_orders` is `null` when the count is 0.
4. No N+1 queries — the count is resolved in a single extra query scoped to the page's inventory IDs.
5. Inventories with no orders (or only terminal-state orders) return `total_orders: null`.

## Contracts and skills

### Contracts loaded

- No formal contract file exists for query patterns; pattern is inferred from existing queries in `services/queries/upholstery/`.

### Local extensions loaded

- None.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Permitted (relational reads — understanding what exists):
- Reading `upholstery_orders_query.py` to confirm how `func.count` + `GROUP BY` is used — ✅ done during planning.
- Reading `upholstery_order.py` model for exact field names (`upholstery_inventory_id`, `state`, `is_deleted`) — ✅ done during planning.
- Reading `domain/upholstery/enums.py` for `UpholsteryOrderStateEnum` values — ✅ done during planning.
- Reading `domain/upholstery/serializers.py` for current signature of `serialize_upholstery_inventory_partial` — ✅ done during planning.

### Skill selection

- Primary skill: built-in query + serializer pattern (no dedicated skill file).
- Router trigger terms: —
- Excluded alternatives: N+1 (one COUNT query per inventory row) — excluded, unacceptable at page sizes up to 200.

## Implementation plan

1. **Define active states constant** in `list_upholstery_inventories.py`:

   ```python
   _ACTIVE_ORDER_STATES = {
       UpholsteryOrderStateEnum.DRAFT,
       UpholsteryOrderStateEnum.PENDING,
       UpholsteryOrderStateEnum.APPROVED,
       UpholsteryOrderStateEnum.ORDERED,
       UpholsteryOrderStateEnum.PARTIALLY_RECEIVED,
   }
   ```

2. **Add count query** after the inventory page is sliced in `list_upholstery_inventories`:

   ```python
   inventory_ids = [inv.client_id for inv in items]
   order_counts: dict[str, int] = {}
   if inventory_ids:
       count_rows = (
           await ctx.session.execute(
               select(
                   UpholsteryOrder.upholstery_inventory_id,
                   func.count().label("total"),
               )
               .where(
                   UpholsteryOrder.workspace_id == ctx.workspace_id,
                   UpholsteryOrder.is_deleted.is_(False),
                   UpholsteryOrder.upholstery_inventory_id.in_(inventory_ids),
                   UpholsteryOrder.state.in_(_ACTIVE_ORDER_STATES),
               )
               .group_by(UpholsteryOrder.upholstery_inventory_id)
           )
       ).all()
       order_counts = {row.upholstery_inventory_id: row.total for row in count_rows}
   ```

3. **Update `serialize_upholstery_inventory_partial`** in `domain/upholstery/serializers.py` to accept an optional `total_orders` parameter:

   ```python
   def serialize_upholstery_inventory_partial(
       inv: UpholsteryInventory,
       total_orders: int | None = None,
   ) -> dict:
       return {
           ...,
           "total_orders": total_orders if total_orders else None,
       }
   ```

4. **Pass count at the call site** in `list_upholstery_inventories.py`:

   ```python
   "items": [
       serialize_upholstery_inventory_partial(
           inv,
           total_orders=order_counts.get(inv.client_id) or None,
       )
       for inv in items
   ],
   ```

   `order_counts.get(inv.client_id)` returns `None` if the key is absent (0 active orders → key not in dict because GROUP BY only returns rows with count > 0), so `or None` normalises both the missing-key and zero cases.

## Risks and mitigations

- Risk: `_ACTIVE_ORDER_STATES` set is wrong (wrong business definition of "active").
  Mitigation: Clarification question above; easy to adjust — only one constant to change.

- Risk: Large `inventory_ids` list (up to 200) causes slow `IN` clause.
  Mitigation: `upholstery_inventory_id` is already indexed (`index=True` in model); 200 IDs in an `IN` is well within Postgres limits.

- Risk: Caller passes `total_orders=0` and expects `0` not `null`.
  Mitigation: Clarification question above; the `or None` coercion in step 4 is the single change point if requirements flip.

## Validation plan

- Manual curl / httpie against `GET /upholstery-inventories?limit=10`: response items include `total_orders`.
- Inventory with active orders: `total_orders` equals expected count.
- Inventory with no orders or only `RECEIVED`/`CANCELLED`/`FAILED` orders: `total_orders` is `null`.
- No regression on existing fields (`client_id`, `inventory_condition`, `current_stored_amount_meters`, `updated_at`).

## Review log

- `2026-06-18` claude-sonnet-4-6: initial plan created from code read during planning session.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
