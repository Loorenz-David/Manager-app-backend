# PLAN_seat_tasks_pending_upholstery_corrections_20260615

## Metadata

- Plan ID: `PLAN_seat_tasks_pending_upholstery_corrections_20260615`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-15T00:00:00Z`
- Last updated at (UTC): `2026-06-15T12:26:29Z`
- Related issue/ticket: `n/a`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_seat_tasks_pending_upholstery_20260615.md`
- Source review: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_seat_tasks_pending_upholstery_20260615.md`

## Goal and intent

- Goal: Apply three targeted corrections to the implementation produced by `PLAN_seat_tasks_pending_upholstery_20260615`. No new functionality is added.
- Business/user intent: Ensure the seat-tasks query is clean, consistent with the rest of the codebase, and does not execute unnecessary DB work.
- Non-goals: No logic changes to filters, pagination, or serialization. No changes to the counts function. No changes to the router endpoints, roles, or response shapes.

## Scope

- In scope:
  - `backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py` — three edits
  - `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py` — one edit
- Out of scope:
  - Counts function (`get_seat_tasks_pending_upholstery_counts`) — already correct, do not touch
  - All other files in the codebase
- Assumptions:
  - SQLAlchemy maps the `TaskItem.role` column to `TaskItemRoleEnum` instances on load. The Python-level comparison `ti.role.value == "primary"` is therefore valid at runtime (same assumption the existing `list_tasks` service relies on).

## Clarifications required

_(none — all three fixes are unambiguous)_

## Acceptance criteria

1. `_seat_task_subquery` helper function is deleted from the module. No reference to it remains in any function.
2. `list_seat_tasks_pending_upholstery` builds the base `stmt` with only workspace and `is_deleted` conditions, then applies the missing-upholstery `or_` filter directly — no `seat_task_subq` `IN` clause.
3. The in-memory primary-item dict comprehension uses `ti.role.value == "primary"` (string comparison), matching the convention in `list_tasks`.
4. The list route handler declares `order_by: str | None = Query(None)` and passes it as `"order_by": order_by` in the `query_params` dict.
5. `py_compile` passes on both changed files after all edits.

## Contracts and skills

### Contracts loaded

- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: confirms two-phase query pattern and that the ID filtering stage should be as minimal as provably correct.
- `backend/architecture/09_routers.md`: confirms query param wiring pattern through `ServiceContext`.

### File read intent — pattern vs. relational

All reads in this plan are **relational** (understanding what the existing implementation does so edits are applied precisely). No pattern reads needed — no new code structures are introduced.

### Skill selection

- Primary skill: targeted file edits only — no query contracts need re-reading
- Excluded alternatives: no new service functions, no new routes

## Implementation plan

All edits are in two files. Apply them in the order listed.

---

### File 1 — `backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py`

#### Edit 1-A — Delete the unused `_seat_task_subquery` helper

Remove the entire function (lines 26–38 in the current file):

```python
# DELETE this entire function — it is now unreferenced
def _seat_task_subquery(ctx: ServiceContext):
    return (
        select(TaskItem.task_id)
        .join(Item, and_(Item.client_id == TaskItem.item_id, Item.workspace_id == ctx.workspace_id))
        .where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.removed_at.is_(None),
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
            Item.is_deleted.is_(False),
            _seat_category_match(),
        )
        .distinct()
    )
```

After deletion, the module-level block reads: `_seat_category_match`, then `_missing_selection_subquery`, then `_missing_quantity_subquery`, then `list_seat_tasks_pending_upholstery`, then `get_seat_tasks_pending_upholstery_counts`.

#### Edit 1-B — Remove the redundant `seat_task_subq` filter from `list_seat_tasks_pending_upholstery`

Current code (inside the function, approximately lines 96–103):

```python
stmt = (
    select(Task.client_id)
    .where(
        Task.workspace_id == ctx.workspace_id,
        Task.is_deleted.is_(False),
    )
    .where(Task.client_id.in_(_seat_task_subquery(ctx)))
)
```

Replace with:

```python
stmt = (
    select(Task.client_id)
    .where(
        Task.workspace_id == ctx.workspace_id,
        Task.is_deleted.is_(False),
    )
)
```

> **Why this is safe**: `_missing_selection_subquery` and `_missing_quantity_subquery` both already filter by `TaskItem.role == PRIMARY`, `TaskItem.removed_at IS NULL`, `Item.is_deleted IS FALSE`, and `_seat_category_match()`. Any `task_id` returned by either subquery is guaranteed to belong to an active seat task. The removed line added a third subquery to the outer WHERE that could not narrow the result further.

#### Edit 1-C — Fix in-memory role comparison to match codebase convention

Current code (inside `list_seat_tasks_pending_upholstery`, approximately line 210):

```python
task_to_primary_item_id = {ti.task_id: ti.item_id for ti in task_items if ti.role == TaskItemRoleEnum.PRIMARY}
```

Replace with:

```python
task_to_primary_item_id = {ti.task_id: ti.item_id for ti in task_items if ti.role.value == "primary"}
```

> **Note**: `TaskItemRoleEnum` remains in scope and is still used inside `_missing_selection_subquery` and `_missing_quantity_subquery` for the SQLAlchemy WHERE clauses. Do not remove the import.

---

### File 2 — `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`

#### Edit 2-A — Expose `order_by` param in the list route

Current handler signature (approximately lines 128–136):

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
```

Replace with:

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
    order_by: str | None = Query(None),
):
```

Current `query_params` dict (approximately lines 139–145):

```python
query_params={
    "limit": limit,
    "offset": offset,
    "q": q,
    "missing_selection": missing_selection,
    "missing_quantity": missing_quantity,
},
```

Replace with:

```python
query_params={
    "limit": limit,
    "offset": offset,
    "q": q,
    "missing_selection": missing_selection,
    "missing_quantity": missing_quantity,
    "order_by": order_by,
},
```

---

## Risks and mitigations

- Risk: Edit 1-B accidentally removes more than the `.where(Task.client_id.in_(_seat_task_subquery(ctx)))` line, altering the base stmt.
  Mitigation: Only the chained `.where(...)` line that references `_seat_task_subquery` is removed. The two preceding `.where(...)` conditions (`workspace_id` and `is_deleted`) stay exactly as-is.

- Risk: Edit 1-C breaks role filtering if SQLAlchemy returns a plain string instead of an enum instance.
  Mitigation: This is the same pattern used by `list_tasks` throughout the codebase. If it works there, it works here. If either fails, they would have been caught long before this correction.

- Risk: After Edit 1-A, an import of `TaskItemRoleEnum` appears unused to a linter (if the linter cannot see the SQLAlchemy expression uses).
  Mitigation: `TaskItemRoleEnum` is used inside `_missing_selection_subquery` and `_missing_quantity_subquery`. It is not unused. No import change required.

## Validation plan

- `python3 -m py_compile backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`: must pass with no output.
- Grep for `_seat_task_subquery` in the file: must return zero matches.
- Grep for `ti.role ==` in the file: must return zero matches (only `ti.role.value ==` remains).
- `GET /api/v1/item-upholsteries/pending-seat-tasks?order_by=created_at:desc`: returns tasks ordered by `created_at` descending, confirming the param is now wired end-to-end.

## Review log

- `2026-06-15`: Removed the redundant seat-task subquery, aligned the primary-item role comparison with the existing `list_tasks` convention, and wired `order_by` through the router.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
