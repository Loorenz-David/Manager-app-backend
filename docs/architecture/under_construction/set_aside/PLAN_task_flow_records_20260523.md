# PLAN_task_flow_records_20260523

## Metadata

- Plan ID: `PLAN_task_flow_records_20260523`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-23T00:00:00Z`
- Last updated at (UTC): `2026-05-23T13:00:57Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- **Goal:** Add a `GET /api/v1/tasks/{task_id}/flow-records` endpoint that returns a merged, time-ordered, paginated feed of history records (task, item upholstery, item upholstery requirement, case) and task step state records for a single task — serialized as a normalized `FlowRecord` shape the frontend can render reliably.
- **Business/user intent:** The frontend needs a unified activity timeline per task without multiple parallel fetches or knowledge of the internal entity graph. The normalized shape allows the frontend to ask for more detail on any record independently.
- **Non-goals:** Creating new tables or migrations. Modifying the history write path. Returning raw `HistoryRecord` or `StepStateRecord` shapes. Adding filter/search query params (this is v1 — no filter params, only `offset` for pagination).

## Scope

- **In scope:**
  - New query service: `services/queries/tasks/task_flow_records.py`
  - New serializer helpers (two functions) added to `domain/tasks/serializers.py`
  - New route `GET /{task_id}/flow-records` added to `routers/api_v1/tasks.py`
  - Pagination: fixed `limit = 10`, `offset` query param (int, default 0, ≥ 0), `has_more` boolean

- **Out of scope:**
  - New migrations
  - Changing any existing serializer or query service
  - Filter/search query params
  - Event records (the `type: event` variant in the shape is reserved for future use)

- **Assumptions:**
  - `HistoryRecord` has no `workspace_id`. Workspace isolation is enforced by deriving entity IDs from workspace-scoped queries on Task, TaskItem, ItemUpholstery, ItemUpholsteryRequirement, and CaseLink. We verify the task exists in `ctx.workspace_id` before proceeding.
  - `CaseLink` has no `workspace_id`. Scoping is implicit via `entity_client_id = task_id` (already workspace-verified).
  - History record volume per task is bounded (task lifecycle). Full in-memory merge then paginate is acceptable for v1.
  - `HistoryRecord.username_snapshot` is the fallback username for history records when the user row is not found.
  - `StepStateRecord` has no `username_snapshot`. If the user row is not found, `created_by.username` is `null`.

## Clarifications required

*(none — requirements fully specified)*

## Acceptance criteria

1. `GET /api/v1/tasks/{task_id}/flow-records` returns `200` with `flow_records` array and `flow_records_pagination` object.
2. Every item in `flow_records` has exactly the keys: `type`, `entity_type`, `entity_client_id`, `description`, `created_at`, `created_by`.
3. Records are ordered by `created_at` descending (most recent first).
4. History records for all four entity types (task, item_upholstery, item_upholstery_requirement, case) appear when they exist.
5. Task step state records appear as `type: "task_step"` with description `"{username} marked {state} on working section {working_section_name}"`.
6. `created_by` is `null` when `created_by_id` is `null`. When populated, it contains `client_id`, `username`, and `profile_picture`.
7. `has_more` is `true` when more records exist beyond the current `offset + limit`.
8. `GET /api/v1/tasks/{task_id}/flow-records` returns `404` when the task does not exist in the workspace.
9. No N+1 queries: all users are batch-loaded in a single query.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: layer isolation, no DB in domain
- `backend/architecture/04_context.md`: `ServiceContext` usage, `ctx.workspace_id`, `ctx.user_id`, `ctx.query_params`
- `backend/architecture/05_errors.md`: `NotFound` for missing task
- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: query signature, workspace scope first, offset pagination (local overrides cursor)
- `backend/architecture/09_routers.md`: handler skeleton, `build_ok` / `build_err`
- `backend/architecture/21_naming_conventions.md`: file naming, function naming
- `backend/architecture/46_serialization.md`: pure serializer functions, no DB access

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination — `limit + 1` trick, `<entity>_pagination` top-level key

### Skill selection

- Primary skill: `backend/architecture/07_queries.md` (read-only multi-source query), `backend/architecture/46_serialization.md` (normalized serializer shape)
- Excluded alternatives: command skill — no writes in scope

## Implementation plan

Execute steps in order. Step 2 depends on Step 1.

---

### Step 1 — Add two serializer helpers to `domain/tasks/serializers.py`

**File:** `backend/app/beyo_manager/domain/tasks/serializers.py`

Add these imports at the top of the file (with the existing imports):

```python
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
```

Add the following three functions at the end of the file. Do **not** modify any existing function.

```python
def _serialize_flow_record_user(user: User | None, created_by_id: str | None, username_snapshot: str | None = None) -> dict | None:
    if created_by_id is None:
        return None
    if user is not None:
        return {
            "client_id": user.client_id,
            "username": user.username,
            "profile_picture": user.profile_picture,
        }
    return {
        "client_id": created_by_id,
        "username": username_snapshot,
        "profile_picture": None,
    }


def serialize_history_flow_record(record: HistoryRecord, link: HistoryRecordLink, users_map: dict) -> dict:
    user = users_map.get(record.created_by_id) if record.created_by_id else None
    return {
        "type": "history_record",
        "entity_type": link.entity_type.value,
        "entity_client_id": link.entity_client_id,
        "description": record.description,
        "created_at": record.created_at.isoformat(),
        "created_by": _serialize_flow_record_user(user, record.created_by_id, record.username_snapshot),
    }


def serialize_step_flow_record(ssr: StepStateRecord, step: TaskStep, users_map: dict) -> dict:
    user = users_map.get(ssr.created_by_id) if ssr.created_by_id else None
    username = user.username if user else (ssr.created_by_id or "Unknown")
    working_section_name = step.working_section_name_snapshot or ""
    description = f"{username} marked {ssr.state.value} on working section {working_section_name}"
    return {
        "type": "task_step",
        "entity_type": "task_step",
        "entity_client_id": ssr.step_id,
        "description": description,
        "created_at": ssr.created_at.isoformat(),
        "created_by": _serialize_flow_record_user(user, ssr.created_by_id),
    }
```

**Rules:**
- `_serialize_flow_record_user` is a private helper (leading underscore) — do not export or reference it outside this file.
- `serialize_history_flow_record` and `serialize_step_flow_record` are the two public serializers.
- The `users_map` parameter is `dict[str, User]` keyed by `user.client_id`.
- `entity_type` for history records is the `.value` of `HistoryRecordLink.entity_type` enum — never hard-code the string.
- `entity_type` for step flow records is the literal string `"task_step"` — this is intentional (not from an enum).

---

### Step 2 — Create `services/queries/tasks/task_flow_records.py`

**File:** `backend/app/beyo_manager/services/queries/tasks/task_flow_records.py`

Create this file from scratch. The full implementation is specified below.

```python
"""Query: paginated task flow records (history + step state records, merged and time-ordered)."""

from sqlalchemy import and_, or_, select

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.domain.history.enums import HistoryRecordEntityTypeEnum
from beyo_manager.domain.tasks.serializers import serialize_history_flow_record, serialize_step_flow_record
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.cases.case_link import CaseLink
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext

FLOW_RECORDS_LIMIT = 10


async def get_task_flow_records(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data["task_id"]
    offset = int(ctx.query_params.get("offset", 0))

    # 1. Verify task exists in this workspace.
    task_check = await ctx.session.execute(
        select(Task.client_id).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
        )
    )
    if task_check.scalar_one_or_none() is None:
        raise NotFound("Task not found.")

    # 2a. Collect item_ids from task_items (active only — removed_at IS NULL).
    item_result = await ctx.session.execute(
        select(TaskItem.item_id).where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id == task_id,
            TaskItem.removed_at.is_(None),
        )
    )
    item_ids = [row[0] for row in item_result.all()]

    # 2b. Collect upholstery_ids from item_upholsteries.
    upholstery_ids: list[str] = []
    if item_ids:
        up_result = await ctx.session.execute(
            select(ItemUpholstery.client_id).where(
                ItemUpholstery.workspace_id == ctx.workspace_id,
                ItemUpholstery.item_id.in_(item_ids),
                ItemUpholstery.is_deleted.is_(False),
            )
        )
        upholstery_ids = [row[0] for row in up_result.all()]

    # 2c. Collect requirement_ids from item_upholstery_requirements.
    requirement_ids: list[str] = []
    if upholstery_ids:
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement.client_id).where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id.in_(upholstery_ids),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
        requirement_ids = [row[0] for row in req_result.all()]

    # 2d. Collect case_ids via CaseLink (CaseLink has no workspace_id — scoped implicitly via task_id).
    case_result = await ctx.session.execute(
        select(CaseLink.case_id).where(
            CaseLink.entity_type == CaseLinkEntityTypeEnum.TASK,
            CaseLink.entity_client_id == task_id,
        )
    )
    case_ids = [row[0] for row in case_result.all()]

    # 2e. Collect step_ids from task_steps.
    step_id_result = await ctx.session.execute(
        select(TaskStep.client_id).where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.task_id == task_id,
            TaskStep.is_deleted.is_(False),
        )
    )
    step_ids = [row[0] for row in step_id_result.all()]

    # 3. Fetch history records for all entity types in one join query.
    #    Always include the task entity type. Add other types only when their ID
    #    lists are non-empty to avoid empty IN() clauses.
    history_conditions = [
        and_(
            HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.TASK,
            HistoryRecordLink.entity_client_id == task_id,
        )
    ]
    if upholstery_ids:
        history_conditions.append(
            and_(
                HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
                HistoryRecordLink.entity_client_id.in_(upholstery_ids),
            )
        )
    if requirement_ids:
        history_conditions.append(
            and_(
                HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY_REQUIREMENT,
                HistoryRecordLink.entity_client_id.in_(requirement_ids),
            )
        )
    if case_ids:
        history_conditions.append(
            and_(
                HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.CASE,
                HistoryRecordLink.entity_client_id.in_(case_ids),
            )
        )

    hist_result = await ctx.session.execute(
        select(HistoryRecord, HistoryRecordLink)
        .join(HistoryRecordLink, HistoryRecordLink.history_record_id == HistoryRecord.client_id)
        .where(or_(*history_conditions))
    )
    history_rows = hist_result.all()  # list[tuple[HistoryRecord, HistoryRecordLink]]

    # 4. Fetch step state records joined with task_steps for working_section_name_snapshot.
    step_state_rows: list = []
    if step_ids:
        ssr_result = await ctx.session.execute(
            select(StepStateRecord, TaskStep)
            .join(TaskStep, TaskStep.client_id == StepStateRecord.step_id)
            .where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.step_id.in_(step_ids),
                StepStateRecord.is_deleted.is_(False),
            )
        )
        step_state_rows = ssr_result.all()  # list[tuple[StepStateRecord, TaskStep]]

    # 5. Batch-load users for all created_by_ids in a single query.
    all_user_ids: set[str] = set()
    for record, _ in history_rows:
        if record.created_by_id:
            all_user_ids.add(record.created_by_id)
    for ssr, _ in step_state_rows:
        if ssr.created_by_id:
            all_user_ids.add(ssr.created_by_id)

    users_map: dict[str, User] = {}
    if all_user_ids:
        users_result = await ctx.session.execute(
            select(User).where(User.client_id.in_(all_user_ids))
        )
        users_map = {u.client_id: u for u in users_result.scalars().all()}

    # 6. Build a sortable raw list: (created_at_datetime, source_type, row_a, row_b).
    #    Sort before serializing to avoid string comparison on ISO timestamps.
    raw: list[tuple] = []
    for record, link in history_rows:
        raw.append((record.created_at, "history", record, link))
    for ssr, step in step_state_rows:
        raw.append((ssr.created_at, "step", ssr, step))

    raw.sort(key=lambda x: x[0], reverse=True)

    # 7. Python-level offset pagination (limit + 1 trick for has_more).
    paged = raw[offset: offset + FLOW_RECORDS_LIMIT + 1]
    has_more = len(paged) > FLOW_RECORDS_LIMIT
    paged = paged[:FLOW_RECORDS_LIMIT]

    # 8. Serialize the page.
    flow_records = []
    for _, source_type, a, b in paged:
        if source_type == "history":
            flow_records.append(serialize_history_flow_record(a, b, users_map))
        else:
            flow_records.append(serialize_step_flow_record(a, b, users_map))

    return {
        "flow_records": flow_records,
        "flow_records_pagination": {
            "has_more": has_more,
            "limit": FLOW_RECORDS_LIMIT,
            "offset": offset,
        },
    }
```

**Rules:**
- `workspace_id` must be the **first** condition in every `.where()` call that touches a workspace-scoped table (`TaskItem`, `ItemUpholstery`, `ItemUpholsteryRequirement`, `TaskStep`, `StepStateRecord`, `Task`).
- `CaseLink` has no `workspace_id` — do not add one.
- `HistoryRecord` and `HistoryRecordLink` have no `workspace_id` — workspace isolation comes from the verified `task_id` and derived entity IDs.
- The `history_conditions` list always contains at least the `TASK` condition before calling `or_()`, so `or_()` is never called with an empty list.
- `hist_result.all()` returns `list[tuple[HistoryRecord, HistoryRecordLink]]` — do **not** call `.scalars()`.
- `ssr_result.all()` returns `list[tuple[StepStateRecord, TaskStep]]` — do **not** call `.scalars()`.
- The `users_result` uses `.scalars().all()` because it selects only `User` columns.
- The `FLOW_RECORDS_LIMIT` constant is module-level (value `10`) — never hard-code `10` inside the function body.
- Sorting is done on `created_at` datetime objects (not ISO strings) before serialization.
- Python-level pagination is intentional: history sources cannot be merged in SQL without `UNION ALL`. For v1, in-memory merge is acceptable given bounded task history volume.

---

### Step 3 — Add route to `routers/api_v1/tasks.py`

**File:** `backend/app/beyo_manager/routers/api_v1/tasks.py`

Add this import with the existing service query imports (near the existing `from beyo_manager.services.queries.tasks.tasks import get_task, list_tasks` line):

```python
from beyo_manager.services.queries.tasks.task_flow_records import get_task_flow_records
```

Add this route handler. Place it immediately after `route_get_task` (after the `GET /{task_id}` handler, before `PATCH /{task_id}`):

```python
@router.get("/{task_id}/flow-records")
async def route_get_task_flow_records(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id},
        query_params={"offset": offset},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_task_flow_records, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Rules:**
- Roles: `[ADMIN, MANAGER, WORKER, SELLER]` — same as `route_get_task`.
- `task_id` is passed via `incoming_data`, `offset` via `query_params`.
- No `limit` query param — limit is fixed at `FLOW_RECORDS_LIMIT = 10` inside the service.
- Route path `/{task_id}/flow-records` does not conflict with existing paths because the literal segment `flow-records` is more specific than the single wildcard routes like `/{task_id}/resolve`.

---

## Risks and mitigations

- **Risk:** `or_()` called with a single condition (when upholstery_ids, requirement_ids, and case_ids are all empty) is valid SQLAlchemy but produces `WHERE (... TASK ...)` without the `OR` wrapper — this is correct behavior.
  **Mitigation:** Confirmed valid. SQLAlchemy handles single-element `or_()` correctly.

- **Risk:** Empty `IN()` clause if step_ids, upholstery_ids, etc. are empty — invalid SQL in some drivers.
  **Mitigation:** All list-dependent queries are guarded by `if step_ids:`, `if upholstery_ids:`, `if requirement_ids:`, `if case_ids:`. Never call `.in_([])`.

- **Risk:** Sorting datetime objects from two different sources (HistoryRecord.created_at and StepStateRecord.created_at) — both must be timezone-aware to avoid comparison errors.
  **Mitigation:** Both model columns are declared `DateTime(timezone=True)`. SQLAlchemy returns timezone-aware datetimes for these columns.

- **Risk:** `hist_result.all()` silently drops `HistoryRecordLink` data if `.scalars()` is accidentally called.
  **Mitigation:** The implementation spec explicitly calls `.all()` on the join result. The plan forbids `.scalars()` on this query.

- **Risk:** Python-level pagination means the DB loads all history records per page request.
  **Mitigation:** Accepted for v1. Add a DB-level `UNION ALL` approach in a future plan when task history volume becomes a concern.

- **Risk:** `route_get_task_flow_records` placed after `route_get_task` in the router file. FastAPI matches routes in declaration order. The path `/{task_id}/flow-records` must be declared before any catch-all-style single-segment routes. Check: it is more specific than `/{task_id}` because it has a second literal segment.
  **Mitigation:** Place the handler immediately after `route_get_task`. The two-segment path `/{task_id}/flow-records` never conflicts with `/{task_id}` for the same HTTP method.

## Validation plan

- `GET /api/v1/tasks/{task_id}/flow-records` with valid task_id → `200`, `flow_records` array, `flow_records_pagination.limit = 10`.
- `GET /api/v1/tasks/nonexistent-id/flow-records` → `404`.
- Task with only task history (no items, no upholstery, no cases) → only `type: "history_record"` records with `entity_type: "task"`.
- Task with steps → `type: "task_step"` records appear with formatted description.
- `offset=10` when fewer than 10 records remain → `has_more: false`, `flow_records` has remaining count.
- All records ordered by `created_at` descending.
- No N+1: user data loaded in one query regardless of record count.

## Review log

*(none yet)*

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `copilot`
