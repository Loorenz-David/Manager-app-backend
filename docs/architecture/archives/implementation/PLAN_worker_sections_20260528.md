# PLAN_worker_sections_20260528

## Metadata

- Plan ID: `PLAN_worker_sections_20260528`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-28T00:00:00Z`
- Last updated at (UTC): `2026-05-28T12:00:00Z`
- Related issue/ticket: N/A
- Intention plan: N/A

## Goal and intent

- Goal: Add two new read-only endpoints to the working sections router — `GET /me` (worker's assigned sections + per-section step state counts) and `GET /{working_section_id}/steps` (paginated task steps for a section with full worker-view payload).
- Business/user intent: Power the worker app home screen that shows per-section work status and lets workers drill into individual task steps.
- Non-goals: No writes, no state transitions, no working section management changes.

## Scope

- In scope:
  - 3 new serializer functions in `domain/tasks/serializers.py`
  - 1 new query file: `services/queries/working_sections/get_worker_working_sections.py`
  - 1 new query file: `services/queries/working_sections/list_working_section_steps.py`
  - 2 new route handlers added to `routers/api_v1/working_sections.py`
- Out of scope: New migrations, model changes, command changes, socket events.
- Assumptions:
  - `WorkingSectionMembership.removed_at IS NULL` means the user is currently assigned to a section.
  - `TaskStep.latest_state_record_id` (already on TaskStep, indexed) is used to determine the entered_at of the latest state for terminal state today-filtering — no extra lookup needed beyond joining StepStateRecord on `client_id == latest_state_record_id`.
  - The primary item of a task is identified by `TaskItem.role == "primary"`.
  - `today_start` is a UTC ISO 8601 timestamp sent by the frontend (e.g., `2026-05-28T06:00:00Z`) representing the start of the user's local day. If absent, the backend falls back to `datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)`.

## Clarifications required

(All resolved before writing this plan.)

## Acceptance criteria

1. `GET /working-sections/me?today_start=<iso>` returns a list of working sections the authenticated user is assigned to, each with a `task_steps_counts` dict containing keys: `pending`, `working`, `paused`, `ended_shift`, `blocked`, `completed`, `skipped`, `failed`. Active-state counts are total; terminal-state counts are limited to steps whose latest state record `entered_at >= today_start`.
2. `GET /working-sections/{working_section_id}/steps` returns a paginated response (`has_more`, `limit`, `offset`) of task steps for that section with the worker-view payload (step, task light, item light + upholstery requirements, item images, created_by user, last_state_record light).
3. The `q` param filters steps by `item.article_number ILIKE` and `item.sku ILIKE` always; adds `ItemUpholstery.name ILIKE` and `ItemUpholstery.code ILIKE` only when `upholstery_search=true`.
4. The `GET /me` route is declared in the router **before** `GET /{working_section_id}` to prevent FastAPI from swallowing it as a path param.
5. Both routes are accessible to ADMIN, MANAGER, and WORKER roles.

## Contracts and skills

### Contracts loaded

- `../architecture/01_architecture.md`: layered structure (model → query → router)
- `../architecture/04_context.md`: ServiceContext usage, user_id / workspace_id extraction
- `../architecture/05_errors.md`: NotFound raise pattern
- `../architecture/07_queries.md` + `../architecture/07_queries_local.md`: query function signature, offset pagination with `limit + 1` / `has_more`, no business logic in queries
- `../architecture/09_routers.md`: handler wiring, `run_service`, `build_ok` / `build_err`, Pydantic-free GET handlers using `Query()`
- `../architecture/21_naming_conventions.md`: file names, function names, variable names
- `../architecture/40_identity.md`: workspace scoping on every query
- `../architecture/41_user.md`: user model fields

### Local extensions loaded

- `../architecture/07_queries_local.md`: offset pagination overrides cursor — `limit + 1` sentinel, `has_more` bool.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead.
- **What exists** → reading is legitimate.

Permitted reads for this plan:
- `models/tables/working_sections/working_section.py` — field names (client_id, name, image)
- `models/tables/working_sections/working_section_membership.py` — field names (user_id, removed_at)
- `models/tables/tasks/task_step.py` — field names (working_section_id, latest_state_record_id, created_by_id, state)
- `models/tables/tasks/step_state_record.py` — field names (entered_at, state)
- `models/tables/tasks/task.py` — field names for light serializer
- `models/tables/items/item.py` — field names for light serializer
- `models/tables/items/item_upholstery.py` — field names
- `models/tables/items/item_upholstery_requirement.py` — field names (client_id, item_upholstery_id, state, source, amount_meters)
- `domain/users/serializers.py` — import `serialize_user_working_section_member`
- `domain/tasks/serializers.py` — import existing helpers, add new ones

Prohibited (pattern reads — contracts cover these):
- Reading another query to understand limit+1 / has_more shape → `07_queries_local.md`
- Reading another router handler to understand wiring → `09_routers.md`

### Skill selection

- Primary skill: query service pattern (`07_queries_local.md`)
- Router trigger terms: `working_sections`, `steps`, `worker`, `me`
- Excluded alternatives: command pattern (`06_commands.md`) — no writes here

## Implementation plan

### Step 1 — Add three light serializer functions to `domain/tasks/serializers.py`

Add at the bottom of the file (after `serialize_step_flow_record`). No existing functions are modified.

**1a. `serialize_task_light`** — subset of `serialize_task` for worker view:

```python
def serialize_task_light(task: Task) -> dict:
    return {
        "client_id": task.client_id,
        "task_type": task.task_type.value,
        "priority": task.priority.value,
        "state": task.state.value,
        "return_source": task.return_source.value if task.return_source else None,
        "item_location": task.item_location.value if task.item_location else None,
        "ready_by_at": task.ready_by_at.isoformat() if task.ready_by_at else None,
        "return_method": task.return_method.value if task.return_method else None,
    }
```

**1b. `serialize_step_state_record_light`** — stripped state record for last_state_record field:

```python
def serialize_step_state_record_light(record: StepStateRecord | None) -> dict | None:
    if record is None:
        return None
    return {
        "state": record.state.value,
        "entered_at": record.entered_at.isoformat() if record.entered_at else None,
        "exited_at": record.exited_at.isoformat() if record.exited_at else None,
    }
```

**1c. `serialize_item_worker_light`** — light item with upholstery requirements inline:

```python
def serialize_item_worker_light(
    item: Item | None,
    upholstery_requirements: list[ItemUpholsteryRequirement] | None = None,
) -> dict | None:
    if item is None:
        return None
    return {
        "client_id": item.client_id,
        "article_number": item.article_number,
        "sku": item.sku,
        "state": item.state.value,
        "item_category_id": item.item_category_id,
        "quantity": item.quantity,
        "item_position": item.item_position,
        "upholstery_requirement": [
            {
                "client_id": req.client_id,
                "item_upholstery_id": req.item_upholstery_id,
                "state": req.state.value,
                "source": req.source.value,
                "amount_meters": float(req.amount_meters) if req.amount_meters is not None else None,
            }
            for req in (upholstery_requirements or [])
        ],
    }
```

The `upholstery_requirements` argument will be all `ItemUpholsteryRequirement` rows whose `item_upholstery_id` belongs to an `ItemUpholstery` whose `item_id` is this item's `client_id`. Pass `None` or `[]` when the item has no upholstery.

Add `ItemUpholsteryRequirement` to the imports at the top of the file if not already present.

---

### Step 2 — Create `services/queries/working_sections/get_worker_working_sections.py`

This query returns the sections the current user is assigned to, each with per-state step counts.

```
File: backend/app/beyo_manager/services/queries/working_sections/get_worker_working_sections.py
```

**Full implementation**:

```python
from datetime import datetime, timezone

from sqlalchemy import and_, case, func, select

from beyo_manager.domain.working_sections.serializers import serialize_working_section_compact
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.services.context import ServiceContext

_ACTIVE_STATES = ("pending", "working", "paused", "ended_shift", "blocked")
_TERMINAL_STATES = ("completed", "skipped", "failed")


async def get_worker_working_sections(ctx: ServiceContext) -> dict:
    today_start_raw = ctx.query_params.get("today_start")
    if today_start_raw:
        today_start = datetime.fromisoformat(today_start_raw)
    else:
        now = datetime.now(tz=timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Load active memberships for the current user.
    membership_result = await ctx.session.execute(
        select(WorkingSectionMembership.working_section_id)
        .where(
            WorkingSectionMembership.workspace_id == ctx.workspace_id,
            WorkingSectionMembership.user_id == ctx.user_id,
            WorkingSectionMembership.removed_at.is_(None),
        )
    )
    section_ids = [row[0] for row in membership_result.all()]

    if not section_ids:
        return {"working_sections": []}

    # 2. Load WorkingSection objects.
    sections_result = await ctx.session.execute(
        select(WorkingSection)
        .where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.client_id.in_(section_ids),
            WorkingSection.is_deleted.is_(False),
        )
        .order_by(WorkingSection.name.asc())
    )
    sections = sections_result.scalars().all()

    # 3a. Count active (non-terminal) step states — no date filter needed.
    active_counts_result = await ctx.session.execute(
        select(
            TaskStep.working_section_id,
            TaskStep.state,
            func.count().label("cnt"),
        )
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id.in_(section_ids),
            TaskStep.is_deleted.is_(False),
            TaskStep.state.in_(_ACTIVE_STATES),
        )
        .group_by(TaskStep.working_section_id, TaskStep.state)
    )

    # 3b. Count terminal step states — only those whose latest state record
    #     entered_at is on or after today_start (i.e. marked today).
    terminal_counts_result = await ctx.session.execute(
        select(
            TaskStep.working_section_id,
            TaskStep.state,
            func.count().label("cnt"),
        )
        .join(
            StepStateRecord,
            and_(
                StepStateRecord.client_id == TaskStep.latest_state_record_id,
                StepStateRecord.entered_at >= today_start,
            ),
        )
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id.in_(section_ids),
            TaskStep.is_deleted.is_(False),
            TaskStep.state.in_(_TERMINAL_STATES),
        )
        .group_by(TaskStep.working_section_id, TaskStep.state)
    )

    # 4. Build counts map keyed by section_id.
    counts_map: dict[str, dict[str, int]] = {sid: {} for sid in section_ids}
    for row in active_counts_result.all():
        counts_map[row.working_section_id][row.state.value] = row.cnt
    for row in terminal_counts_result.all():
        counts_map[row.working_section_id][row.state.value] = row.cnt

    all_states = list(_ACTIVE_STATES) + list(_TERMINAL_STATES)

    # 5. Assemble response.
    return {
        "working_sections": [
            {
                **serialize_working_section_compact(
                    section.client_id, section.name, section.image
                ),
                "task_steps_counts": {
                    state: counts_map[section.client_id].get(state, 0)
                    for state in all_states
                },
            }
            for section in sections
        ]
    }
```

---

### Step 3 — Create `services/queries/working_sections/list_working_section_steps.py`

This query returns paginated task steps for a specific working section with the full worker-view payload.

```
File: backend/app/beyo_manager/services/queries/working_sections/list_working_section_steps.py
```

**Full implementation**:

```python
from sqlalchemy import String, and_, cast, distinct, or_, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.tasks.serializers import (
    serialize_item_worker_light,
    serialize_step,
    serialize_step_state_record_light,
    serialize_task_light,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.domain.users.serializers import serialize_user_working_section_member
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_working_section_steps(ctx: ServiceContext) -> dict:
    working_section_id = ctx.incoming_data.get("working_section_id")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    upholstery_search = ctx.query_params.get("upholstery_search", "false").lower() == "true"

    # Verify the working section exists and belongs to this workspace.
    ws_result = await ctx.session.execute(
        select(WorkingSection).where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.client_id == working_section_id,
            WorkingSection.is_deleted.is_(False),
        )
    )
    if ws_result.scalar_one_or_none() is None:
        raise NotFound("Working section not found.")

    # 1. Build base step ID query.
    stmt = (
        select(TaskStep.client_id)
        .where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id == working_section_id,
            TaskStep.is_deleted.is_(False),
        )
        .order_by(TaskStep.created_at.desc())
    )

    # 2. Apply q filter as a subquery on TaskStep.client_id.
    if q:
        q_like = f"%{q}%"

        # Always join Item for article_number / sku.
        q_stmt = (
            select(distinct(TaskStep.client_id))
            .select_from(TaskStep)
            .join(Task, Task.client_id == TaskStep.task_id)
            .join(
                TaskItem,
                and_(
                    TaskItem.task_id == Task.client_id,
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.removed_at.is_(None),
                    TaskItem.role == TaskItemRoleEnum.PRIMARY,
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
        )

        or_clauses = [
            Item.article_number.ilike(q_like),
            Item.sku.ilike(q_like),
        ]

        if upholstery_search:
            q_stmt = q_stmt.join(
                ItemUpholstery,
                and_(
                    ItemUpholstery.item_id == Item.client_id,
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.is_deleted.is_(False),
                ),
                isouter=True,
            )
            or_clauses += [
                ItemUpholstery.name.ilike(q_like),
                ItemUpholstery.code.ilike(q_like),
            ]

        q_stmt = q_stmt.where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.working_section_id == working_section_id,
            TaskStep.is_deleted.is_(False),
            or_(*or_clauses),
        )

        stmt = stmt.where(TaskStep.client_id.in_(q_stmt))

    stmt = stmt.offset(offset).limit(limit + 1)

    ids_result = await ctx.session.execute(stmt)
    step_ids = [row[0] for row in ids_result.all()]

    has_more = len(step_ids) > limit
    page_ids = step_ids[:limit]

    if not page_ids:
        return {
            "steps_pagination": {
                "items": [],
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            }
        }

    # 3. Load full TaskStep objects with latest_state_record eagerly loaded.
    steps_result = await ctx.session.execute(
        select(TaskStep)
        .options(selectinload(TaskStep.latest_state_record))
        .where(TaskStep.client_id.in_(page_ids))
        .order_by(TaskStep.created_at.desc())
    )
    steps = steps_result.scalars().all()
    step_map = {s.client_id: s for s in steps}

    # 4. Batch-load Tasks.
    task_ids = list({s.task_id for s in steps})
    tasks_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id.in_(task_ids),
        )
    )
    task_map = {t.client_id: t for t in tasks_result.scalars().all()}

    # 5. Batch-load primary TaskItem → Item.
    task_items_result = await ctx.session.execute(
        select(TaskItem).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id.in_(task_ids),
            TaskItem.removed_at.is_(None),
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
        )
    )
    task_items = task_items_result.scalars().all()
    task_to_primary_item_id = {ti.task_id: ti.item_id for ti in task_items}

    primary_item_ids = list(task_to_primary_item_id.values())
    items_map: dict[str, Item] = {}
    if primary_item_ids:
        items_result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id.in_(primary_item_ids),
                Item.is_deleted.is_(False),
            )
        )
        items_map = {item.client_id: item for item in items_result.scalars().all()}

    # 6. Batch-load ItemUpholstery → ItemUpholsteryRequirement.
    upholstery_map: dict[str, list[ItemUpholstery]] = {}  # item_id → upholsteries
    requirements_map: dict[str, list[ItemUpholsteryRequirement]] = {}  # item_id → requirements
    if primary_item_ids:
        uph_result = await ctx.session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.item_id.in_(primary_item_ids),
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        upholsteries = uph_result.scalars().all()
        for u in upholsteries:
            upholstery_map.setdefault(u.item_id, []).append(u)

        upholstery_ids = [u.client_id for u in upholsteries]
        if upholstery_ids:
            req_result = await ctx.session.execute(
                select(ItemUpholsteryRequirement).where(
                    ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                    ItemUpholsteryRequirement.item_upholstery_id.in_(upholstery_ids),
                    ItemUpholsteryRequirement.is_deleted.is_(False),
                )
            )
            for req in req_result.scalars().all():
                # Find the item_id this requirement belongs to via upholstery.
                for u in upholsteries:
                    if u.client_id == req.item_upholstery_id:
                        requirements_map.setdefault(u.item_id, []).append(req)
                        break

    # 7. Batch-load item images (first full, rest light — same strategy as tasks.py).
    item_images_map: dict[str, list] = {}
    if primary_item_ids:
        img_result = await ctx.session.execute(
            select(Image, ImageLink.entity_client_id)
            .join(
                ImageLink,
                and_(
                    ImageLink.image_id == Image.client_id,
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                    ImageLink.entity_client_id.in_(primary_item_ids),
                ),
            )
            .options(selectinload(Image.last_event))
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
        )
        for image, item_id in img_result.all():
            image_list = item_images_map.setdefault(item_id, [])
            image_list.append(
                serialize_image(image) if not image_list else serialize_image_light(image)
            )

    # 8. Batch-load creator Users for serialize_user_working_section_member.
    creator_ids = list({s.created_by_id for s in steps if s.created_by_id})
    users_map: dict[str, User] = {}
    if creator_ids:
        users_result = await ctx.session.execute(
            select(User).where(User.client_id.in_(creator_ids))
        )
        users_map = {u.client_id: u for u in users_result.scalars().all()}

    # 9. Assemble response preserving page order.
    items_payload = []
    for step_id in page_ids:
        step = step_map.get(step_id)
        if step is None:
            continue
        task = task_map.get(step.task_id)
        primary_item_id = task_to_primary_item_id.get(step.task_id) if task else None
        item = items_map.get(primary_item_id) if primary_item_id else None
        creator = users_map.get(step.created_by_id) if step.created_by_id else None
        item_reqs = requirements_map.get(primary_item_id, []) if primary_item_id else []

        items_payload.append(
            {
                **serialize_step(step),
                "created_by": serialize_user_working_section_member(creator) if creator else None,
                "last_state_record": serialize_step_state_record_light(step.latest_state_record),
                "task": serialize_task_light(task) if task else None,
                "item": serialize_item_worker_light(item, item_reqs),
                "item_images": item_images_map.get(primary_item_id, []) if primary_item_id else [],
            }
        )

    return {
        "steps_pagination": {
            "items": items_payload,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
```

**Note on requirements_map build**: The inner loop matching `req.item_upholstery_id` against `upholsteries` is O(upholsteries_per_page). For pages with many upholsteries, replace with a dict lookup: build `upholstery_id_to_item_id: dict[str, str] = {u.client_id: u.item_id for u in upholsteries}` before the loop and use `requirements_map.setdefault(upholstery_id_to_item_id[req.item_upholstery_id], []).append(req)`.

---

### Step 4 — Add two routes to `routers/api_v1/working_sections.py`

**Imports to add** at the top of the file:

```python
from beyo_manager.services.queries.working_sections.get_worker_working_sections import (
    get_worker_working_sections,
)
from beyo_manager.services.queries.working_sections.list_working_section_steps import (
    list_working_section_steps,
)
```

**Route 1 — `GET /me`** (add BEFORE the `GET /{working_section_id}` handler to avoid FastAPI treating "me" as a path param):

```python
@router.get("/me")
async def get_worker_working_sections_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    today_start: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"today_start": today_start} if today_start else {},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_worker_working_sections, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Route 2 — `GET /{working_section_id}/steps`** (can go after `GET /{working_section_id}`):

```python
@router.get("/{working_section_id}/steps")
async def list_working_section_steps_route(
    working_section_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    q: str | None = Query(None),
    upholstery_search: bool = Query(False),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={"working_section_id": working_section_id},
        query_params={
            "q": q,
            "upholstery_search": str(upholstery_search).lower(),
            "limit": limit,
            "offset": offset,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_working_section_steps, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Critical ordering rule**: In `working_sections.py`, the final route order must be:
1. `PUT ""` — create
2. `GET ""` — list
3. `GET "/me"` ← new, must be here before the path-param route
4. `GET "/{working_section_id}"` — get by id
5. `GET "/{working_section_id}/steps"` ← new
6. `PATCH "/{working_section_id}"` — edit
7. `DELETE "/{working_section_id}"` — delete

---

### Step 5 — Verify `TaskItemRoleEnum.PRIMARY` import path

Before implementing, confirm the enum in `domain/tasks/enums.py` has `PRIMARY = "primary"`. The query files that already compare `ti.role.value == "primary"` confirm this value exists. Import as:

```python
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
```

And use `TaskItem.role == TaskItemRoleEnum.PRIMARY` in SQLAlchemy `.where()` / join conditions.

---

### Step 6 — Verify `ItemUpholsteryRequirement.workspace_id` exists

Before adding `.where(ItemUpholsteryRequirement.workspace_id == ctx.workspace_id, ...)`, check that the model has this column. If it does not, remove the workspace_id filter and rely solely on the `item_upholstery_id.in_(upholstery_ids)` filter (the IDs are already workspace-scoped from the prior query). Read `models/tables/items/item_upholstery_requirement.py` to confirm.

## Risks and mitigations

- Risk: `GET /me` conflicts with `GET /{working_section_id}` if order is wrong.
  Mitigation: Plan step 4 explicitly specifies route ordering. Copilot must declare `/me` before `/{working_section_id}` in the router file.

- Risk: The `requirements_map` inner loop is O(upholsteries × requirements) per page.
  Mitigation: Replace with `upholstery_id_to_item_id` dict lookup (noted in Step 3). The dict approach is O(1) per requirement.

- Risk: `today_start` parsing fails on malformed ISO string from frontend.
  Mitigation: `datetime.fromisoformat()` raises `ValueError` which bubbles up as a 500. Add a try/except in the query and raise `ValidationError("today_start must be a valid ISO 8601 timestamp.")` if parsing fails.

- Risk: `TaskItemRoleEnum.PRIMARY` import path is wrong.
  Mitigation: Step 5 instructs copilot to read `domain/tasks/enums.py` to confirm before using.

- Risk: `ItemUpholsteryRequirement` may not have `workspace_id`.
  Mitigation: Step 6 instructs copilot to read the model before adding the workspace filter.

## Validation plan

- `GET /api/v1/working-sections/me` with a WORKER token → returns `{"working_sections": [...]}` with `task_steps_counts` keys for all 8 states.
- `GET /api/v1/working-sections/me` with `today_start=<iso>` → terminal state counts reflect only steps entered today.
- `GET /api/v1/working-sections/me` with a user assigned to 0 sections → returns `{"working_sections": []}`.
- `GET /api/v1/working-sections/{id}/steps` → returns `steps_pagination` with `items`, `has_more`, `limit`, `offset`.
- `GET /api/v1/working-sections/{id}/steps?q=SKU123` → filters by article_number/sku, does NOT filter by upholstery name.
- `GET /api/v1/working-sections/{id}/steps?q=velvet&upholstery_search=true` → filters by article_number, sku, upholstery name, and upholstery code.
- `GET /api/v1/working-sections/me` → FastAPI must NOT match "me" as a `working_section_id` path param (verify 200, not 404).
- Upholstery requirements in step item payload include `item_upholstery_id` field on each requirement object.

## Review log

- `2026-05-28` plan author: initial draft

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `david`
