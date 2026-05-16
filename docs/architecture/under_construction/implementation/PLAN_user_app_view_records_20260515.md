# PLAN_user_app_view_records_20260515

## Metadata

- Plan ID: `PLAN_user_app_view_records_20260515`
- Status: `under_construction`
- Owner agent: `GitHub Copilot`
- Created at (UTC): `2026-05-15T02:00:00Z`
- Last updated at (UTC): `2026-05-15T02:00:00Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_user_app_view_records_20260515.md`

## Goal and intent

- Goal: Add the HTTP transport layer for user app view record events — batch POST, self-service reads, admin reads, and an admin live workspace presence snapshot.
- Business/user intent: The frontend sends batches of view events over HTTP (for offline recovery). Admins and managers see who is currently viewing what across the workspace in real time. All users can browse their own view history.
- Non-goals: WebSocket socket handler wiring, EntityType enum extension, background flush jobs, retention policy.

## Scope

- In scope:
  - CREATE `services/infra/presence/user_view_key.py` — async Redis helpers for the user→entity reverse-mapping key
  - CREATE `domain/presence/serializers.py` — view record serializer + live presence serializer
  - CREATE `services/commands/users/requests/record_view_events_request.py` — batch request parser
  - CREATE `services/commands/users/record_view_events.py` — batch POST command
  - CREATE `services/queries/users/list_self_view_records.py` — self-service paginated history
  - CREATE `services/queries/users/get_current_view.py` — current active view from Redis
  - CREATE `services/queries/users/list_user_view_records.py` — admin/manager paginated history per user
  - CREATE `services/queries/users/get_live_workspace_presence.py` — admin/manager live workspace snapshot
  - UPDATE `services/tasks/presence/record_view_start.py` — global auto-close + honour payload `started_at`
  - UPDATE `services/tasks/presence/record_view_end.py` — honour payload `ended_at`
  - UPDATE `routers/api_v1/users.py` — register 5 new routes
  - UPDATE `architecture/48_presence_local.md` — document local overrides

- Out of scope: socket handlers, user_online key ownership, EntityType additions, admin routes beyond this plan.

- Assumptions:
  - `settings.redis_url` and `settings.redis_key_prefix` exist (confirmed from reading `presence.py` and `keys.py`).
  - `settings.presence_debounce_seconds` exists (confirmed from reading `record_view_start.py`).
  - `UserAppViewRecord` has no `workspace_id` column; admin endpoint enforces workspace scope via `WorkspaceMembership` check only.
  - `RECORD_VIEW_START` and `RECORD_VIEW_END` `TaskType` values already exist in `domain/execution/enums.py`.
  - `create_instant_task(session, task_type, payload)` is the correct call signature.

## Clarifications required

- None — all decisions resolved during alignment.

## Acceptance criteria

1. `POST /api/v1/users/me/view-records` with a valid batch returns `200 {}`.
2. START items (no `ended_at`) call `mark_viewing` + write `user_view` Redis key + enqueue one `RECORD_VIEW_START` task each.
3. Completed items (has `ended_at`) call `mark_left` + clear `user_view` key if matching + enqueue `RECORD_VIEW_START` then `RECORD_VIEW_END` tasks each.
4. `entity_type` not in `EntityType` enum → `422`.
5. `records` list exceeds `_MAX_BATCH_SIZE` (50) → `422`.
6. `GET /api/v1/users/me/view-records/current` returns `{"current_view": {entity_type, entity_client_id}}` or `{"current_view": null}` when key absent.
7. `GET /api/v1/users/me/view-records?limit=&offset=` returns paginated view records with `view_records_pagination` key.
8. `GET /api/v1/users/{user_client_id}/view-records` returns `404` if user is not an active workspace member; else returns same paginated shape.
9. `GET /api/v1/users/live` returns `{"presence": [...]}` — one entry per active workspace member with `current_view` (null if absent) and `is_online` (false if key absent). Reads all Redis keys in a single pipeline.
10. `record_view_start.py` closes all `ended_at IS NULL` records for the user before inserting a new one (global auto-close).
11. `record_view_start.py` uses `payload["started_at"]` (ISO string, parsed to datetime) if present; otherwise falls back to `datetime.now(timezone.utc)`.
12. `record_view_end.py` uses `payload["ended_at"]` (ISO string, parsed to datetime) if present; otherwise falls back to `datetime.now(timezone.utc)`.
13. `/me/view-records` routes declared before `/{user_client_id}` wildcard; `/live` declared before `GET /{user_client_id}`.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: service layer structure
- `backend/architecture/04_context.md`: ServiceContext, query_params
- `backend/architecture/05_errors.md`: NotFound, ValidationError
- `backend/architecture/06_commands.md`: single transaction, request parser pattern
- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: offset pagination, `limit + 1` has_more pattern
- `backend/architecture/09_routers.md`: route handler shape, run_service, build_ok/build_err
- `backend/architecture/12_infra_redis.md`: key naming, TTL rules, async client usage
- `backend/architecture/48_presence.md`: two-layer architecture, mark_viewing/mark_left, task enqueue pattern

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: offset pagination replaces cursor-based; `_MAX_LIMIT = 200`, `_DEFAULT_LIMIT = 50`
- `backend/architecture/48_presence_local.md`: will be updated by this plan

### File read intent — pattern vs. relational

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand `session.begin()` shape → use `06_commands.md`
- Reading another router to understand handler skeleton → use `09_routers.md`
- Reading another query to understand pagination shape → use `07_queries_local.md`

Permitted (relational reads — understanding what exists):
- `services/infra/presence/presence.py` — to confirm `mark_viewing`/`mark_left` signatures
- `services/infra/redis/keys.py` and `async_client.py` — to confirm `make_key` and `get_async_redis` import paths
- `services/infra/execution/task_factory.py` — to confirm `create_instant_task` signature
- `domain/execution/enums.py` — to confirm `TaskType.RECORD_VIEW_START` / `RECORD_VIEW_END` values
- `models/tables/users/user_app_view_record.py` — to confirm field names
- `models/tables/workspaces/workspace_membership.py` — to confirm field names for workspace scope check
- `routers/api_v1/users.py` — to know the current route order before inserting new routes

## Implementation plan

### Step 1 — CREATE `services/infra/presence/user_view_key.py`

Async Redis helpers for the `{prefix}:user_view:{user_id}` reverse-mapping key. Owned by this module. TTL is a module-level constant (move to settings in a future pass if needed).

```python
import json

from beyo_manager.services.infra.redis import make_key
from beyo_manager.services.infra.redis.async_client import get_async_redis

_USER_VIEW_TTL_SECONDS = 86400  # 24 hours


def _key(user_id: str) -> str:
    return make_key("user_view", user_id)


async def set_user_view(user_id: str, entity_type: str, entity_client_id: str) -> None:
    r = get_async_redis()
    await r.set(
        _key(user_id),
        json.dumps({"entity_type": entity_type, "entity_client_id": entity_client_id}),
        ex=_USER_VIEW_TTL_SECONDS,
    )


async def clear_user_view_if_matches(user_id: str, entity_type: str, entity_client_id: str) -> None:
    r = get_async_redis()
    key = _key(user_id)
    raw = await r.get(key)
    if raw is not None:
        current = json.loads(raw)
        if current.get("entity_type") == entity_type and current.get("entity_client_id") == entity_client_id:
            await r.delete(key)


async def get_user_view(user_id: str) -> dict | None:
    r = get_async_redis()
    raw = await r.get(_key(user_id))
    if raw is None:
        return None
    return json.loads(raw)
```

---

### Step 2 — CREATE `domain/presence/serializers.py`

Two serializers: one for `UserAppViewRecord` rows (used by both self-service and admin history), one for the live presence snapshot entries.

```python
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord


def serialize_view_record(record: UserAppViewRecord) -> dict:
    return {
        "client_id": record.client_id,
        "entity_type": record.entity_type,
        "entity_client_id": record.entity_client_id,
        "started_at": record.started_at.isoformat(),
        "ended_at": record.ended_at.isoformat() if record.ended_at else None,
    }


def serialize_live_user_presence(
    user: User,
    role_name: str,
    current_view: dict | None,
    is_online: bool,
) -> dict:
    return {
        "client_id": user.client_id,
        "username": user.username,
        "profile_picture": user.profile_picture,
        "role_name": role_name,
        "current_view": current_view,
        "is_online": is_online,
    }
```

---

### Step 3 — CREATE `services/commands/users/requests/record_view_events_request.py`

Validates the batch. `entity_type` must be a valid `EntityType` enum value — Pydantic coerces automatically via `StrEnum`. Batch size capped at `_MAX_BATCH_SIZE`.

```python
from datetime import datetime

from pydantic import BaseModel, ValidationError as PydanticValidationError, model_validator

from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.errors.validation import ValidationError

_MAX_BATCH_SIZE = 50


class ViewRecordItem(BaseModel):
    entity_type: EntityType
    entity_client_id: str
    started_at: datetime
    ended_at: datetime | None = None


class RecordViewEventsRequest(BaseModel):
    records: list[ViewRecordItem]

    @model_validator(mode="after")
    def validate_batch_size(self) -> "RecordViewEventsRequest":
        if len(self.records) > _MAX_BATCH_SIZE:
            raise ValueError(f"records: batch exceeds maximum of {_MAX_BATCH_SIZE} items.")
        return self


def parse_record_view_events_request(data: dict) -> RecordViewEventsRequest:
    try:
        return RecordViewEventsRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
```

---

### Step 4 — CREATE `services/commands/users/record_view_events.py`

Redis writes happen inline (before the transaction). DB task enqueue happens inside a single transaction. Completed items (with `ended_at`) enqueue both START and END tasks so the worker creates the record and immediately closes it with the correct timestamp. START items only enqueue START.

```python
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.services.commands.users.requests.record_view_events_request import (
    parse_record_view_events_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.presence.presence import mark_left, mark_viewing
from beyo_manager.services.infra.presence.user_view_key import (
    clear_user_view_if_matches,
    set_user_view,
)


async def record_view_events(ctx: ServiceContext) -> dict:
    request = parse_record_view_events_request(ctx.incoming_data)

    for item in request.records:
        if item.ended_at is None:
            mark_viewing(item.entity_type.value, item.entity_client_id, ctx.user_id)
            await set_user_view(ctx.user_id, item.entity_type.value, item.entity_client_id)
        else:
            mark_left(item.entity_type.value, item.entity_client_id, ctx.user_id)
            await clear_user_view_if_matches(ctx.user_id, item.entity_type.value, item.entity_client_id)

    async with ctx.session.begin():
        for item in request.records:
            await create_instant_task(
                ctx.session,
                TaskType.RECORD_VIEW_START,
                {
                    "user_id": ctx.user_id,
                    "entity_type": item.entity_type.value,
                    "entity_client_id": item.entity_client_id,
                    "started_at": item.started_at.isoformat(),
                },
            )
            if item.ended_at is not None:
                await create_instant_task(
                    ctx.session,
                    TaskType.RECORD_VIEW_END,
                    {
                        "user_id": ctx.user_id,
                        "entity_type": item.entity_type.value,
                        "entity_client_id": item.entity_client_id,
                        "ended_at": item.ended_at.isoformat(),
                    },
                )

    return {}
```

---

### Step 5 — CREATE `services/queries/users/list_self_view_records.py`

Self-service paginated view record history. No workspace filter — `UserAppViewRecord` has no `workspace_id`; scoped by `user_id` only. Ordered `started_at DESC`.

```python
from sqlalchemy import desc, select

from beyo_manager.domain.presence.serializers import serialize_view_record
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_self_view_records(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    result = await ctx.session.execute(
        select(UserAppViewRecord)
        .where(UserAppViewRecord.user_id == ctx.user_id)
        .order_by(desc(UserAppViewRecord.started_at))
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "view_records": [serialize_view_record(r) for r in page],
        "view_records_pagination": {"has_more": has_more, "limit": limit, "offset": offset},
    }
```

---

### Step 6 — CREATE `services/queries/users/get_current_view.py`

Reads the `user_view` Redis key for the authenticated user. Returns `null` if absent.

```python
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.presence.user_view_key import get_user_view


async def get_current_view(ctx: ServiceContext) -> dict:
    current = await get_user_view(ctx.user_id)
    return {"current_view": current}
```

---

### Step 7 — CREATE `services/queries/users/list_user_view_records.py`

Admin/manager paginated view record history for any workspace member. Verifies active membership before querying. Same pagination shape as `list_self_view_records`.

```python
from sqlalchemy import desc, select

from beyo_manager.domain.presence.serializers import serialize_view_record
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_user_view_records(ctx: ServiceContext) -> dict:
    user_client_id = ctx.incoming_data.get("user_client_id")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

    membership = await ctx.session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.user_id == user_client_id,
            WorkspaceMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise NotFound("User not found in workspace.")

    result = await ctx.session.execute(
        select(UserAppViewRecord)
        .where(UserAppViewRecord.user_id == user_client_id)
        .order_by(desc(UserAppViewRecord.started_at))
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "view_records": [serialize_view_record(r) for r in page],
        "view_records_pagination": {"has_more": has_more, "limit": limit, "offset": offset},
    }
```

---

### Step 8 — CREATE `services/queries/users/get_live_workspace_presence.py`

Fetches all active workspace members from DB, then batch-reads their `user_view` and `user_online` Redis keys in a single pipeline. `user_online` key is written by a separate future plan; if absent, `is_online = False`.

```python
import json

from sqlalchemy import select

from beyo_manager.domain.presence.serializers import serialize_live_user_presence
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.redis import make_key
from beyo_manager.services.infra.redis.async_client import get_async_redis


async def get_live_workspace_presence(ctx: ServiceContext) -> dict:
    result = await ctx.session.execute(
        select(User, WorkspaceRole.name.label("role_name"))
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.client_id)
        .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
        .where(
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.is_active.is_(True),
        )
        .order_by(User.username.asc())
    )
    members = result.all()

    if not members:
        return {"presence": []}

    redis = get_async_redis()
    view_keys = [make_key("user_view", row.User.client_id) for row in members]
    online_keys = [make_key("user_online", row.User.client_id) for row in members]

    pipe = redis.pipeline(transaction=False)
    for key in view_keys + online_keys:
        pipe.get(key)
    values = await pipe.execute()

    n = len(members)
    view_values = values[:n]
    online_values = values[n:]

    presence = []
    for i, row in enumerate(members):
        raw_view = view_values[i]
        current_view = json.loads(raw_view) if raw_view is not None else None
        is_online = online_values[i] is not None
        presence.append(
            serialize_live_user_presence(row.User, row.role_name, current_view, is_online)
        )

    return {"presence": presence}
```

---

### Step 9 — UPDATE `services/tasks/presence/record_view_start.py`

Two changes:
1. Before inserting a new record, close ALL open records for this user globally (`ended_at IS NULL` regardless of entity) — the app-specific one-active-per-user rule.
2. Use `payload["started_at"]` (ISO string) if present, so offline batch records land with the correct timestamp.

Full replacement of the existing file:

```python
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from beyo_manager.config import settings
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord
from beyo_manager.services.infra.execution.db import task_db_session


async def handle_record_view_start(payload: dict, task_id: str) -> None:
    user_client_id = payload.get("user_id")
    entity_type = payload.get("entity_type")
    entity_client_id = payload.get("entity_client_id")
    if not user_client_id or not entity_type:
        return

    started_at_raw = payload.get("started_at")
    started_at = (
        datetime.fromisoformat(started_at_raw) if started_at_raw else datetime.now(timezone.utc)
    )

    async with task_db_session() as session:
        user = (
            await session.execute(select(User).where(User.client_id == user_client_id))
        ).scalar_one_or_none()
        if user is None:
            return

        debounce_cutoff = started_at - timedelta(seconds=settings.presence_debounce_seconds)
        existing = (
            await session.execute(
                select(UserAppViewRecord)
                .where(
                    UserAppViewRecord.user_id == user.client_id,
                    UserAppViewRecord.entity_type == entity_type,
                    UserAppViewRecord.entity_client_id == entity_client_id,
                    UserAppViewRecord.ended_at.is_(None),
                    UserAppViewRecord.started_at >= debounce_cutoff,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return

        # App override: close all globally open records before creating a new one.
        await session.execute(
            update(UserAppViewRecord)
            .where(
                UserAppViewRecord.user_id == user.client_id,
                UserAppViewRecord.ended_at.is_(None),
            )
            .values(ended_at=started_at)
        )

        record = UserAppViewRecord(
            user_id=user.client_id,
            entity_type=entity_type,
            entity_client_id=entity_client_id,
            started_at=started_at,
        )
        session.add(record)
        await session.flush()
        user.last_app_view_record_id = record.client_id
        await session.commit()
```

---

### Step 10 — UPDATE `services/tasks/presence/record_view_end.py`

Use `payload["ended_at"]` (ISO string) if present, so offline batch records land with the correct end timestamp.

Full replacement of the existing file:

```python
from datetime import datetime, timezone

from sqlalchemy import desc, select

from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_app_view_record import UserAppViewRecord
from beyo_manager.services.infra.execution.db import task_db_session


async def handle_record_view_end(payload: dict, task_id: str) -> None:
    user_client_id = payload.get("user_id")
    entity_type = payload.get("entity_type")
    entity_client_id = payload.get("entity_client_id")
    if not user_client_id or not entity_type:
        return

    ended_at_raw = payload.get("ended_at")
    ended_at = (
        datetime.fromisoformat(ended_at_raw) if ended_at_raw else datetime.now(timezone.utc)
    )

    async with task_db_session() as session:
        user = (
            await session.execute(select(User).where(User.client_id == user_client_id))
        ).scalar_one_or_none()
        if user is None:
            return

        result = await session.execute(
            select(UserAppViewRecord)
            .where(
                UserAppViewRecord.user_id == user.client_id,
                UserAppViewRecord.entity_type == entity_type,
                UserAppViewRecord.entity_client_id == entity_client_id,
                UserAppViewRecord.ended_at.is_(None),
            )
            .order_by(desc(UserAppViewRecord.started_at))
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return

        record.ended_at = ended_at
        await session.commit()
```

---

### Step 11 — UPDATE `routers/api_v1/users.py`

Add 5 imports, 1 body class, and 5 route handlers. Route order must be:

```
GET  /me                         (existing)
GET  /me/view-records            (NEW)
GET  /me/view-records/current    (NEW)
PATCH /me                        (existing)
PATCH /me/password               (existing)
POST /me/view-records            (NEW)
GET  /live                       (NEW — static, before /{user_client_id})
GET  ""                          (existing — list users)
GET  /{user_client_id}           (existing)
PATCH /{user_client_id}          (existing)
PATCH /{user_client_id}/deactivate (existing)
GET  /{user_client_id}/view-records (NEW — two-segment, no wildcard conflict)
```

**Add to the existing import block** (after the existing service imports, before `router = APIRouter()`):

```python
from beyo_manager.services.commands.users.record_view_events import record_view_events
from beyo_manager.services.queries.users.get_current_view import get_current_view
from beyo_manager.services.queries.users.get_live_workspace_presence import get_live_workspace_presence
from beyo_manager.services.queries.users.list_self_view_records import list_self_view_records
from beyo_manager.services.queries.users.list_user_view_records import list_user_view_records
```

**Add body class** after the existing `UpdateUserAdminBody` class:

```python
class RecordViewEventsBody(BaseModel):
    records: list[dict]
```

**Add after the existing `GET /me` route** (before `PATCH /me`):

```python
@router.get("/me/view-records")
async def list_self_view_records_route(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        identity=claims,
        session=session,
        query_params={"limit": str(limit), "offset": str(offset)},
    )
    outcome = await run_service(list_self_view_records, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/me/view-records/current")
async def get_current_view_route(
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_current_view, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Add after the existing `PATCH /me/password` route** (before `GET ""`):

```python
@router.post("/me/view-records")
async def record_view_events_route(
    body: RecordViewEventsBody,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(record_view_events, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/live")
async def get_live_workspace_presence_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_live_workspace_presence, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Add after the existing `PATCH /{user_client_id}/deactivate` route** (at the end of the file):

```python
@router.get("/{user_client_id}/view-records")
async def list_user_view_records_route(
    user_client_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_client_id": user_client_id},
        identity=claims,
        session=session,
        query_params={"limit": str(limit), "offset": str(offset)},
    )
    outcome = await run_service(list_user_view_records, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

### Step 12 — UPDATE `architecture/48_presence_local.md`

Replace the placeholder sections with the app-specific overrides documented here:

```markdown
# Presence - Local Extensions
> Extends: 48_presence.md

## Added Fields

- None

## Overridden Behaviour

### One active `UserAppViewRecord` per user globally (replaces multi-tab rule)

The canonical contract (`48_presence.md`) allows multiple open `UserAppViewRecord` rows per user — one per entity viewed concurrently (multi-tab). This app enforces a stricter rule:

**Only one open record per user at any time, globally across all entity types.**

When `RECORD_VIEW_START` is processed:
1. All existing `UserAppViewRecord` rows for this user with `ended_at IS NULL` are bulk-closed with `ended_at = started_at` of the new record.
2. The new record is then inserted.

This is implemented in `services/tasks/presence/record_view_start.py`.

### Payload timestamps honoured (`started_at`, `ended_at`)

The canonical handlers use `datetime.now(timezone.utc)` for all timestamps. This app extends both handlers to accept ISO timestamps from the task payload:

- `RECORD_VIEW_START`: uses `payload["started_at"]` if present (supports offline batch records with correct start times).
- `RECORD_VIEW_END`: uses `payload["ended_at"]` if present (supports offline batch records with correct end times).

## Local Decisions

### `user_view` reverse-mapping Redis key

Key pattern: `{prefix}:user_view:{user_id}`
Value: JSON `{"entity_type": "...", "entity_client_id": "..."}`
TTL: `_USER_VIEW_TTL_SECONDS` (module constant, 86400 s — 24 h)
Owner: `services/infra/presence/user_view_key.py`

Written inline by `POST /api/v1/users/me/view-records` on START events.
Cleared on END events if the stored entity matches.
Read by `GET /api/v1/users/me/view-records/current` and `GET /api/v1/users/live`.

### `user_online` key (read-only from this plan)

Key pattern: `{prefix}:user_online:{user_id}`
Owner: a future online-status plan.
Read by: `GET /api/v1/users/live` (pipeline). If absent, user is treated as offline (`is_online = false`).
```

---

## Risks and mitigations

- Risk: `mark_viewing` / `mark_left` are synchronous Redis calls invoked from an async context, blocking the event loop momentarily.
  Mitigation: Both are sub-millisecond SADD/SREM operations. Acceptable for now. Migrate to async client if benchmarks show contention.

- Risk: The global auto-close in `RECORD_VIEW_START` issues a bulk `UPDATE` before the debounce check returns — if debounce short-circuits, the bulk update still ran.
  Mitigation: The debounce check is done BEFORE the bulk update in Step 9. If debounce matches, the function returns early and the bulk update never executes.

- Risk: Pipeline order inversion in `get_live_workspace_presence` if view_keys and online_keys lengths differ.
  Mitigation: Both lists are derived from the same `members` list in the same order. `values[:n]` and `values[n:]` are safe because `len(view_keys) == len(online_keys) == n`.

- Risk: Stale `user_view` key if server restarts before the TTL expires — a user who has closed their session may still appear as "viewing" until TTL lapses.
  Mitigation: Best-effort accepted per alignment. TTL of 24 h is a reasonable trade-off for workspace activity dashboards.

## Validation plan

- Static: `python -c "from beyo_manager.services.commands.users.record_view_events import record_view_events; from beyo_manager.services.queries.users.get_live_workspace_presence import get_live_workspace_presence; print('OK_VIEW_RECORDS')"` → `OK_VIEW_RECORDS`
- Static: `python -c "from beyo_manager.routers.api_v1.users import router; print('OK_ROUTER')"` → `OK_ROUTER`
- Live HTTP (server must be running at `http://localhost:8000`):
  - `POST /api/v1/users/me/view-records` with `{"records": [{"entity_type": "case", "entity_client_id": "cas_test", "started_at": "<now_iso>"}]}` → `200 {}`
  - `GET /api/v1/users/me/view-records/current` → `{"current_view": {"entity_type": "case", "entity_client_id": "cas_test"}}`
  - `POST /api/v1/users/me/view-records` with `{"records": [{"entity_type": "case", "entity_client_id": "cas_test", "started_at": "<now_iso>", "ended_at": "<later_iso>"}]}` → `200 {}`
  - `GET /api/v1/users/me/view-records/current` → `{"current_view": null}`
  - `GET /api/v1/users/me/view-records?limit=5&offset=0` → `{"view_records": [...], "view_records_pagination": {...}}`
  - `GET /api/v1/users/live` (admin token) → `{"presence": [...]}`
  - `GET /api/v1/users/{valid_user_client_id}/view-records` (admin token) → `{"view_records": [...], "view_records_pagination": {...}}`
  - `POST /api/v1/users/me/view-records` with `entity_type: "invalid_type"` → `422`
  - `POST /api/v1/users/me/view-records` with 51 records → `422`

## Review log

- `2026-05-15` Claude: Plan written. 8 new files, 4 updated files. All contract references resolved. Ready for Copilot implementation.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
