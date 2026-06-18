# PLAN_fix_upholstery_alloc_sort_priority_20260618

## Metadata

- Plan ID: `PLAN_fix_upholstery_alloc_sort_priority_20260618`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-18T00:00:00Z`
- Last updated at (UTC): `2026-06-18T10:27:53Z`
- Related issue/ticket: `n/a`
- Intention plan: `n/a`

## Goal and intent

- Goal: Fix the allocation sort order in `_allocate_received_requirements` so that Tier 2 and Tier 3 candidates are sorted by the earliest `Task.ready_by_at` linked to their item before falling back to `created_at`.
- Business/user intent: When stock is insufficient to fulfill all pending requirements at once, requirements tied to items with an imminent deadline must be allocated before older requirements that have no deadline.
- Non-goals: Do not change Tier 1 (explicit pinning), `allocate_pooled_requirements`, any other command, or any model schema.

## Scope

- In scope: `backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py` — specifically `_allocate_received_requirements` and a new private helper `_fetch_earliest_ready_by_at`.
- Out of scope: Database migrations, model changes, `_pooled_requirement_allocation.py`, any query service, any router.
- Assumptions: An `ItemUpholsteryRequirement` is linked to a `Task` through the chain `ItemUpholsteryRequirement.item_upholstery_id → ItemUpholstery.client_id → ItemUpholstery.item_id → Item.client_id → TaskItem.item_id → TaskItem.task_id → Task.client_id`. A requirement may be linked to zero tasks (orphan item) — in that case `ready_by_at` is treated as `None` (lowest priority within its tier).

## Clarifications required

_None — the sort rule is fully specified._

## Acceptance criteria

1. When partial stock is received and multiple non-pinned ORDERED requirements compete, a requirement whose linked task has an earlier `ready_by_at` is allocated before one whose task has a later `ready_by_at` or no `ready_by_at`.
2. When two non-pinned requirements share the same earliest `ready_by_at` (or both have `None`), the one with the older `created_at` is allocated first.
3. Requirements with no linked task (no `ready_by_at`) always sort after requirements that do have one, within the same tier.
4. Tier 1 (explicitly pinned) requirements are unaffected.
5. Tier 3 (NEEDS_ORDERING) follows the same `ready_by_at → created_at` ordering as Tier 2.

## Contracts and skills

### Contracts loaded

- `n/a`: Implementation is a targeted patch to an existing function; no architectural contract needed beyond what is already established in the file.

### Local extensions loaded

- `n/a`

### File read intent — pattern vs. relational

Permitted reads for this plan:
- `receive_upholstery_order.py` — the file being changed (relational: understand existing structure)
- `item_upholstery_requirement.py` — confirm `item_upholstery_id` field name and type
- `item_upholstery.py` — confirm FK chain `client_id → item_id`
- `task_item.py` — confirm `item_id`, `task_id`, `removed_at` field names
- `task.py` — confirm `ready_by_at` field name, type, and nullability

Prohibited:
- Reading other command files to understand session/flush/error patterns (already established in the file being changed)

### Skill selection

- Primary skill: `n/a` — single-file patch, no routing skill required.

## Implementation plan

### Step 1 — Add missing imports

In `receive_upholstery_order.py`, extend the existing `sqlalchemy` import line:

**Before:**
```python
from sqlalchemy import select
```

**After:**
```python
from sqlalchemy import and_, func, select
```

Add four model imports after the existing model imports block:

```python
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
```

### Step 2 — Add `_fetch_earliest_ready_by_at` helper

Add a new private async function **below** `_allocate_received_requirements`:

```python
async def _fetch_earliest_ready_by_at(
    session: AsyncSession,
    workspace_id: str,
    item_upholstery_ids: list[str],
) -> dict[str, datetime | None]:
    if not item_upholstery_ids:
        return {}
    stmt = (
        select(
            ItemUpholstery.client_id.label("item_upholstery_id"),
            func.min(Task.ready_by_at).label("earliest_ready_by_at"),
        )
        .select_from(ItemUpholstery)
        .join(
            Item,
            and_(
                Item.client_id == ItemUpholstery.item_id,
                Item.workspace_id == workspace_id,
                Item.is_deleted.is_(False),
            ),
        )
        .join(
            TaskItem,
            and_(
                TaskItem.item_id == Item.client_id,
                TaskItem.workspace_id == workspace_id,
                TaskItem.removed_at.is_(None),
            ),
        )
        .join(
            Task,
            and_(
                Task.client_id == TaskItem.task_id,
                Task.workspace_id == workspace_id,
                Task.is_deleted.is_(False),
                Task.ready_by_at.is_not(None),
            ),
        )
        .where(
            ItemUpholstery.client_id.in_(item_upholstery_ids),
            ItemUpholstery.workspace_id == workspace_id,
            ItemUpholstery.is_deleted.is_(False),
        )
        .group_by(ItemUpholstery.client_id)
    )
    rows = (await session.execute(stmt)).all()
    return {row.item_upholstery_id: row.earliest_ready_by_at for row in rows}
```

**Why MIN?** An item can belong to multiple tasks. Using `MIN(Task.ready_by_at)` ensures the most urgent deadline wins when picking a sort key for a single requirement.

**Why filter `Task.ready_by_at.is_not(None)` in the join?** Rows with a null `ready_by_at` are excluded at the database level, so the resulting map contains only real deadline values. Items not in the map are treated as having no deadline by the `.get()` call returning `None` — no sentinel constant required.

### Step 3 — Update `_allocate_received_requirements` to call the helper and fix sort keys

Inside `_allocate_received_requirements`, after `ordered_candidates` are identified and before `tier2`/`tier3` are sorted, add a call to the helper. Then update the sort keys for both tiers.

**Target function signature (unchanged):**
```python
async def _allocate_received_requirements(
    session: AsyncSession,
    workspace_id: str,
    inventory_id: str,
    priority_item_upholstery_ids: list[str],
    actor_id: str,
) -> list[str]:
```

**Insert after `priority_order` is built (after line 187) and before the `tier1` sort:**

```python
    non_pinned_iup_ids = [
        req.item_upholstery_id
        for req in candidates
        if req.item_upholstery_id not in priority_set
    ]
    ready_by_at_map = await _fetch_earliest_ready_by_at(session, workspace_id, non_pinned_iup_ids)
```

**Replace the `tier2` sort key (currently `key=lambda req: req.created_at`):**

```python
    tier2 = sorted(
        [
            req
            for req in candidates
            if req.item_upholstery_id not in priority_set
            and req.state == ItemUpholsteryRequirementStateEnum.ORDERED
        ],
        key=lambda req: (
            ready_by_at_map.get(req.item_upholstery_id) is None,
            ready_by_at_map.get(req.item_upholstery_id),
            req.created_at,
        ),
    )
```

**Replace the `tier3` sort key (currently `key=lambda req: req.created_at`):**

```python
    tier3 = sorted(
        [
            req
            for req in candidates
            if req.item_upholstery_id not in priority_set
            and req.state == ItemUpholsteryRequirementStateEnum.NEEDS_ORDERING
        ],
        key=lambda req: (
            ready_by_at_map.get(req.item_upholstery_id) is None,
            ready_by_at_map.get(req.item_upholstery_id),
            req.created_at,
        ),
    )
```

**Sort key semantics:**
- Tuple element 0: `True` (1) if no entry in the map (no deadline), `False` (0) if there is one → dated requirements sort first.
- Tuple element 1: the actual `ready_by_at` datetime ascending, or `None` for undated → Python only compares element 1 when element 0 ties, so `None` is never compared against a `datetime` and no `TypeError` can occur.
- Tuple element 2: `created_at` ascending → oldest creation date wins on ties.

## Risks and mitigations

- Risk: A requirement's item belongs to multiple tasks with different `ready_by_at` values.
  Mitigation: `MIN(Task.ready_by_at)` ensures the most urgent (earliest) deadline is used, which is the correct conservative choice.

- Risk: A requirement's item is not linked to any task, or all its linked tasks have `ready_by_at = None` — the join returns no rows, so the `item_upholstery_id` is absent from `ready_by_at_map`.
  Mitigation: `ready_by_at_map.get(...)` returns `None` for missing keys. Element 0 of the sort tuple (`is None → True`) pushes these to the back of their tier. Element 1 is never compared against a real datetime for the same reason (element 0 already separates the two groups), so no `TypeError` is raised.

## Validation plan

- Manual test: Create two requirements sharing the same inventory — one older with no task `ready_by_at`, one newer with `ready_by_at = tomorrow`. Receive partial stock that only covers one requirement. Confirm the newer requirement with the deadline is allocated, not the older one.
- Manual test: Two requirements both have `ready_by_at`, same date — confirm the one with the older `created_at` wins.
- Manual test: No requirements have `ready_by_at` — confirm existing `created_at`-ascending behaviour is preserved.
- Manual test: A Tier 1 pinned requirement — confirm it still takes priority over any Tier 2 requirement regardless of `ready_by_at`.

## Review log

- `2026-06-18` `codex`: Implemented the allocation sort change in `receive_upholstery_order.py`, added a helper that resolves the earliest linked `Task.ready_by_at` per `item_upholstery_id`, and verified the module with `python3 -m py_compile`.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
