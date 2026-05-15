# PLAN_working_section_membership_20260515

## Metadata

- Plan ID: `PLAN_working_section_membership_20260515`
- Status: `under_construction`
- Owner agent: `GitHub Copilot`
- Created at (UTC): `2026-05-15T12:00:00Z`
- Last updated at (UTC): `2026-05-15T13:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/user_assign_to_working_section.md`

## Goal and intent

- Goal: Implement 3 working section membership endpoints (assign, unassign, list members) with commands, a query, serializer additions, and two routers.
- Business/user intent: Enable admins and managers to assign workers to working sections and track who is in each section. Commands are reusable by other services (e.g. user registration).
- Non-goals: Bulk multi-user operations, historical membership queries, notifications/push fanout.

## Scope

- In scope: 7 new files + 2 edits to existing files.
- Out of scope: Any auth flow changes, migration changes (table already exists), working section CRUD, user management commands.
- Assumptions:
  - `WorkingSectionMembership` table is stable and matches the model at `models/tables/working_sections/working_section_membership.py`.
  - `PLAN_working_section_crud_20260515` is fully implemented (summary at `implemented_summaries/SUMMARY_working_section_crud_20260515.md`). Therefore: `domain/working_sections/serializers.py` EXISTS with `serialize_working_section_id_only` and `serialize_working_section_full` — Step 1 is EDIT only. Package stubs `services/commands/working_sections/__init__.py`, `services/commands/working_sections/requests/__init__.py`, and `services/queries/working_sections/__init__.py` already exist. `routers/api_v1/__init__.py` already registers the working_sections CRUD router at `/api/v1/working-sections` — Step 9 adds the two new routers alongside without touching that line.
  - `UserEvent` and `build_user_event` are available from `services.infra.events.domain_event` and `services.infra.events.build_event` — confirmed by inspection.
  - `WorkspaceMembership` links a user to their `WorkspaceRole`, which links to a `Role` with `name = "worker"`.
  - `DELETE /api/v1/users/{user_id}/working-sections` carries a JSON body — FastAPI supports this via `Body(...)`. The HTTP spec allows bodies on DELETE.

## Clarifications required

All items below are **resolved decisions**. Copilot must follow them exactly — do not reinterpret or find alternatives.

- [x] **Route shape**: User-centric batch routes. `POST /api/v1/users/{user_id}/working-sections` to assign. `DELETE /api/v1/users/{user_id}/working-sections` with body to unassign. `GET /api/v1/working-sections/{working_section_id}/members` for section member list.

- [x] **HTTP methods**: `POST ""` for assign, `DELETE ""` for unassign (both defined in `user_working_sections.py` router registered at `/api/v1/users`). `GET "/{working_section_id}/members"` defined in `working_section_memberships.py` router registered at `/api/v1/working-sections`.

- [x] **Route declaration order in `user_working_sections.py`**: `POST ""` → `DELETE ""`. Route declaration order in `working_section_memberships.py`: `GET "/{working_section_id}/members"` only.

- [x] **Role permissions**: `require_roles([ADMIN, MANAGER])` on all three routes (assign, unassign, list).

- [x] **Assignable roles**: WORKER only. Assigning a user with any other role raises `ValidationError` (422).

- [x] **Assign is transactional for the full list**: All sections in a single `POST` run inside one `async with ctx.session.begin()` block. If any section fails validation (section not found, already assigned), the entire operation rolls back. No partial assignment.

- [x] **Unassign is transactional for the full list**: Same — all unassigns in one transaction. If any section has no active membership, the entire operation rolls back.

- [x] **Duplicate section IDs in the request**: Raise `ValidationError` if `working_section_ids` contains duplicate values.

- [x] **Worker role check**: Use a two-step query. First, check `WorkspaceMembership` joined to `WorkspaceRole` joined to `Role` where `role.name == RoleNameEnum.WORKER.value` and `is_active=True`. If no row found, run a second query checking any active membership. If active membership exists → raise `ValidationError("Only workers can be assigned to working sections.")`. If no membership at all → raise `NotFound("User not found in workspace.")`.

- [x] **Soft-remove semantics**: Unassign sets `removed_at = datetime.now(timezone.utc)` and `removed_by_id = ctx.user_id`. Does not hard-delete the row.

- [x] **Event**: Dispatch a `UserEvent` (not a `WorkspaceEvent`) targeting the affected user's socket room. Use `build_user_event(user_id=request.user_id, event_name="user:working_sections_updated", client_id=request.user_id, extra={"working_section_ids": list_of_changed_ids})`. Call `await dispatch([event])` AFTER the `async with ctx.session.begin()` block.

- [x] **Assign return value**: `{"assigned_section_ids": [list of section IDs that were newly assigned]}`.

- [x] **Unassign return value**: `{"unassigned_section_ids": [list of section IDs that were removed]}`.

- [x] **List members return value**: `{"members": [{membership_id, user_id, username, assigned_at}]}`. `assigned_at` is ISO-8601 string (`isoformat()`). Ordered by `assigned_at ASC`.

- [x] **No ORM relationship attribute access**: `WorkspaceMembership` has a `workspace_role` relationship but `lazy="raise"` is set on working section models. Use explicit JOINs for the role chain. Do not access `.workspace_role` or `.role` attributes.

- [x] **`workspace_id` is always first filter**: Every `WHERE` clause starts with the workspace boundary.

- [x] **Commands use `ServiceContext` standard signature**: `async def assign_user_to_working_sections(ctx: ServiceContext) -> dict`. Reusable by other commands via `ServiceContext` construction. No special callable protocol needed.

- [x] **No `__init__.py` content**: All `__init__.py` files in new or existing packages should be empty or contain a single comment. Do not add re-exports.

## Acceptance criteria

1. `POST /api/v1/users/{user_id}/working-sections` with `{"working_section_ids": ["wsec_..."]}` returns `{"data": {"assigned_section_ids": ["wsec_..."]}, "warnings": []}`.
2. `DELETE /api/v1/users/{user_id}/working-sections` with `{"working_section_ids": ["wsec_..."]}` returns `{"data": {"unassigned_section_ids": ["wsec_..."]}, "warnings": []}` and sets `removed_at`.
3. `GET /api/v1/working-sections/{id}/members` returns `{"data": {"members": [{membership_id, user_id, username, assigned_at}]}, "warnings": []}` with only active (non-removed) members.
4. Assigning a user with a non-WORKER role returns `422`.
5. Assigning a user not in the workspace returns `404`.
6. Assigning the same user to an already-active section returns `409 Conflict`.
7. Unassigning a user with no active membership for a given section returns `404`.
8. Assigning with an empty `working_section_ids` list returns `422`.
9. Assigning with duplicate section IDs in the list returns `422`.
10. Non-ADMIN/MANAGER request returns `403`.
11. `UserEvent("user:working_sections_updated")` is dispatched after successful assign and after successful unassign.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: Layer boundaries — business logic in commands/queries, never in routers.
- `backend/architecture/04_context.md`: `ServiceContext` — `ctx.workspace_id`, `ctx.user_id`, `ctx.session`, `ctx.incoming_data`.
- `backend/architecture/05_errors.md`: `NotFound`, `ValidationError` (http_status=422), `Conflict` error hierarchy. Note: the correct class is `ValidationError` from `beyo_manager.errors.validation`, NOT `ValidationFailed` (which does not exist in the codebase). This also applies to `PLAN_working_section_crud_20260515` which incorrectly uses `ValidationFailed` in its request parsers — that plan has a bug that must be fixed on implementation.
- `backend/architecture/06_commands.md`: Command structure — parse → `async with ctx.session.begin()` → dispatch events after.
- `backend/architecture/07_queries.md`: Query structure — read-only, `ctx.workspace_id` first filter.
- `backend/architecture/09_routers.md`: Router skeleton — `require_roles`, `run_service`, `build_ok`/`build_err`, no business logic.
- `backend/architecture/21_naming_conventions.md`: File naming patterns.
- `backend/architecture/40_identity.md`: `client_id` as primary key, `IdentityMixin`.
- `backend/architecture/42_event.md`: Event dispatch — `UserEvent` for user-specific rooms, `WorkspaceEvent` for workspace broadcast. Use `build_user_event` for this domain.
- `backend/architecture/46_serialization.md`: Serializers are plain functions in `domain/<domain>/serializers.py`.

### Local extensions loaded

- `backend/architecture/40_identity_local.md`: Prefix `wsme` = `WorkingSectionMembership`.
- No local extensions found for 01, 04, 05, 06, 07, 09, 21, 42, 46.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read contracts (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (field names, import paths, model columns)

Permitted relational reads for this plan:
- `beyo_manager/models/tables/working_sections/working_section_membership.py` — exact field names
- `beyo_manager/models/tables/working_sections/working_section.py` — `client_id`, `is_deleted`, `workspace_id`
- `beyo_manager/models/tables/workspaces/workspace_membership.py` — `user_id`, `workspace_role_id`, `is_active`
- `beyo_manager/models/tables/roles/workspace_role.py` — `role_id`, `client_id`
- `beyo_manager/models/tables/roles/role.py` — `name`, `client_id`
- `beyo_manager/models/tables/users/user.py` — `client_id`, `username`
- `beyo_manager/services/infra/events/domain_event.py` — `UserEvent` fields
- `beyo_manager/services/infra/events/build_event.py` — `build_user_event` signature
- `beyo_manager/routers/api_v1/__init__.py` — to know where to add the routers
- `beyo_manager/domain/working_sections/serializers.py` — to know what already exists (if created by CRUD plan)

### Skill selection

- Primary skill: `backend/task_system/backend_contract_goal_mapping_guide.md` (CRUD + document-only protocol).
- Goal bundle used: CRUD (contracts 01, 04, 05, 06, 07, 09, 21, 40, 46) + event dispatch (42).
- Excluded: sockets direct (13), background jobs (16), testing (15) — not in scope for this plan.

---

## Implementation plan

All paths are relative to `backend/app/beyo_manager/`.

---

### Step 1 — Add membership serializer to domain serializers

**File: `domain/working_sections/serializers.py`** (EDIT — file already exists)

The CRUD plan created this file with `serialize_working_section_id_only` and `serialize_working_section_full`. Append `serialize_working_section_member` after the existing functions. Do not modify or remove the existing functions.

```python
def serialize_working_section_member(row) -> dict:
    return {
        "membership_id": row.membership_id,
        "user_id": row.user_id,
        "username": row.username,
        "assigned_at": row.assigned_at.isoformat(),
    }
```

`row` is a SQLAlchemy `Row` result from a JOIN query (not an ORM instance). The fields `membership_id`, `user_id`, `username`, and `assigned_at` are labelled columns from the query in Step 6.

---

### Step 2 — Create request parser: assign

**File: `services/commands/working_sections/requests/assign_user_request.py`**

```python
from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class AssignUserRequest(BaseModel):
    user_id: str
    working_section_ids: list[str]

    @field_validator("user_id", mode="before")
    @classmethod
    def user_id_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("user_id must not be blank.")
        return v

    @field_validator("working_section_ids", mode="before")
    @classmethod
    def section_ids_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("working_section_ids must contain at least one section ID.")
        return v


def parse_assign_user_request(data: dict) -> AssignUserRequest:
    try:
        return AssignUserRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

### Step 3 — Create request parser: unassign

**File: `services/commands/working_sections/requests/unassign_user_request.py`**

```python
from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class UnassignUserRequest(BaseModel):
    user_id: str
    working_section_ids: list[str]

    @field_validator("user_id", mode="before")
    @classmethod
    def user_id_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("user_id must not be blank.")
        return v

    @field_validator("working_section_ids", mode="before")
    @classmethod
    def section_ids_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("working_section_ids must contain at least one section ID.")
        return v


def parse_unassign_user_request(data: dict) -> UnassignUserRequest:
    try:
        return UnassignUserRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

### Step 4 — Create command: `assign_user_to_working_sections.py`

**File: `services/commands/working_sections/assign_user_to_working_sections.py`**

Logic order inside `async with ctx.session.begin()`:
1. Parse request.
2. Validate no duplicate section IDs in the input list.
3. Verify the user is an active WORKER in the workspace (two-step query — see clarification).
4. For each section ID in order: verify section exists and is not deleted, then verify no active membership already exists.
5. After all validations pass, create `WorkingSectionMembership` rows (one per section ID), flushing after each `add()`.
6. After `begin()` block: dispatch `UserEvent`.

```python
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.working_sections.requests.assign_user_request import (
    AssignUserRequest,
    parse_assign_user_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_user_event


async def assign_user_to_working_sections(ctx: ServiceContext) -> dict:
    request: AssignUserRequest = parse_assign_user_request(ctx.incoming_data)

    # Duplicate section ID check
    if len(request.working_section_ids) != len(set(request.working_section_ids)):
        raise ValidationError("Duplicate IDs in working_section_ids are not allowed.")

    async with ctx.session.begin():
        # Worker role check (two-step for good error messages)
        worker_membership_id = await ctx.session.scalar(
            select(WorkspaceMembership.client_id)
            .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
            .join(Role, Role.client_id == WorkspaceRole.role_id)
            .where(
                WorkspaceMembership.workspace_id == ctx.workspace_id,
                WorkspaceMembership.user_id == request.user_id,
                WorkspaceMembership.is_active.is_(True),
                Role.name == RoleNameEnum.WORKER.value,
            )
        )
        if worker_membership_id is None:
            any_membership = await ctx.session.scalar(
                select(WorkspaceMembership.client_id).where(
                    WorkspaceMembership.workspace_id == ctx.workspace_id,
                    WorkspaceMembership.user_id == request.user_id,
                    WorkspaceMembership.is_active.is_(True),
                )
            )
            if any_membership is None:
                raise NotFound("User not found in workspace.")
            raise ValidationError("Only workers can be assigned to working sections.")

        # Validate all sections and check for existing active memberships
        for section_id in request.working_section_ids:
            section = await ctx.session.scalar(
                select(WorkingSection).where(
                    WorkingSection.workspace_id == ctx.workspace_id,
                    WorkingSection.client_id == section_id,
                    WorkingSection.is_deleted.is_(False),
                )
            )
            if section is None:
                raise NotFound(f"Working section '{section_id}' not found.")

            existing = await ctx.session.scalar(
                select(WorkingSectionMembership.client_id).where(
                    WorkingSectionMembership.workspace_id == ctx.workspace_id,
                    WorkingSectionMembership.working_section_id == section_id,
                    WorkingSectionMembership.user_id == request.user_id,
                    WorkingSectionMembership.removed_at.is_(None),
                )
            )
            if existing is not None:
                raise ConflictError(
                    f"User is already assigned to working section '{section_id}'."
                )

        # Create membership rows
        for section_id in request.working_section_ids:
            membership = WorkingSectionMembership(
                workspace_id=ctx.workspace_id,
                working_section_id=section_id,
                user_id=request.user_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=ctx.user_id,
            )
            ctx.session.add(membership)
            await ctx.session.flush()

    await dispatch([
        build_user_event(
            user_id=request.user_id,
            event_name="user:working_sections_updated",
            client_id=request.user_id,
            extra={"working_section_ids": request.working_section_ids},
        )
    ])
    return {"assigned_section_ids": request.working_section_ids}
```

---

### Step 5 — Create command: `unassign_user_from_working_sections.py`

**File: `services/commands/working_sections/unassign_user_from_working_sections.py`**

Logic order inside `async with ctx.session.begin()`:
1. Parse request.
2. Validate no duplicate section IDs.
3. For each section ID: find the active `WorkingSectionMembership` row. If not found, raise `NotFound`.
4. After all memberships are confirmed to exist, set `removed_at` and `removed_by_id` on each.
5. After `begin()` block: dispatch `UserEvent`.

```python
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.services.commands.working_sections.requests.unassign_user_request import (
    UnassignUserRequest,
    parse_unassign_user_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_user_event


async def unassign_user_from_working_sections(ctx: ServiceContext) -> dict:
    request: UnassignUserRequest = parse_unassign_user_request(ctx.incoming_data)

    # Duplicate section ID check
    if len(request.working_section_ids) != len(set(request.working_section_ids)):
        raise ValidationError("Duplicate IDs in working_section_ids are not allowed.")

    async with ctx.session.begin():
        # Load all active memberships first to validate before mutating
        memberships: list[WorkingSectionMembership] = []
        for section_id in request.working_section_ids:
            result = await ctx.session.execute(
                select(WorkingSectionMembership).where(
                    WorkingSectionMembership.workspace_id == ctx.workspace_id,
                    WorkingSectionMembership.working_section_id == section_id,
                    WorkingSectionMembership.user_id == request.user_id,
                    WorkingSectionMembership.removed_at.is_(None),
                )
            )
            membership = result.scalar_one_or_none()
            if membership is None:
                raise NotFound(
                    f"No active membership found for user in section '{section_id}'."
                )
            memberships.append(membership)

        # All found — now soft-remove
        now = datetime.now(timezone.utc)
        for membership in memberships:
            membership.removed_at = now
            membership.removed_by_id = ctx.user_id

    await dispatch([
        build_user_event(
            user_id=request.user_id,
            event_name="user:working_sections_updated",
            client_id=request.user_id,
            extra={"working_section_ids": request.working_section_ids},
        )
    ])
    return {"unassigned_section_ids": request.working_section_ids}
```

---

### Step 6 — Create query: `list_working_section_members.py`

**File: `services/queries/working_sections/list_working_section_members.py`**

Runs 2 DB reads: one to verify the section exists, one to load active members via JOIN to `users`.

```python
from sqlalchemy import select

from beyo_manager.domain.working_sections.serializers import serialize_working_section_member
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.services.context import ServiceContext


async def list_working_section_members(ctx: ServiceContext) -> dict:
    working_section_id: str = ctx.incoming_data.get("working_section_id", "")

    # 1. Verify section exists
    section = await ctx.session.scalar(
        select(WorkingSection).where(
            WorkingSection.workspace_id == ctx.workspace_id,
            WorkingSection.client_id == working_section_id,
            WorkingSection.is_deleted.is_(False),
        )
    )
    if section is None:
        raise NotFound("Working section not found.")

    # 2. Load active members with username
    result = await ctx.session.execute(
        select(
            WorkingSectionMembership.client_id.label("membership_id"),
            WorkingSectionMembership.user_id,
            User.username,
            WorkingSectionMembership.assigned_at,
        )
        .join(User, User.client_id == WorkingSectionMembership.user_id)
        .where(
            WorkingSectionMembership.workspace_id == ctx.workspace_id,
            WorkingSectionMembership.working_section_id == working_section_id,
            WorkingSectionMembership.removed_at.is_(None),
        )
        .order_by(WorkingSectionMembership.assigned_at.asc())
    )
    members = [serialize_working_section_member(row) for row in result.all()]
    return {"members": members}
```

---

### Step 7 — Create router: `user_working_sections.py`

**File: `routers/api_v1/user_working_sections.py`**

Handles the assign and unassign routes at `/api/v1/users`. Route declaration order: `POST ""` → `DELETE ""`.

The `DELETE` route uses `Body(...)` to accept a JSON body, which is valid per HTTP spec and supported by FastAPI.

```python
from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.commands.working_sections.assign_user_to_working_sections import (
    assign_user_to_working_sections,
)
from beyo_manager.services.commands.working_sections.unassign_user_from_working_sections import (
    unassign_user_from_working_sections,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()


class AssignSectionsBody(BaseModel):
    working_section_ids: list[str]


class UnassignSectionsBody(BaseModel):
    working_section_ids: list[str]


@router.post("/{user_id}/working-sections")
async def assign_working_sections_route(
    user_id: str,
    body: AssignSectionsBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_id": user_id, "working_section_ids": body.working_section_ids},
        identity=claims,
        session=session,
    )
    outcome = await run_service(assign_user_to_working_sections, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{user_id}/working-sections")
async def unassign_working_sections_route(
    user_id: str,
    body: UnassignSectionsBody = Body(...),
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_id": user_id, "working_section_ids": body.working_section_ids},
        identity=claims,
        session=session,
    )
    outcome = await run_service(unassign_user_from_working_sections, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

### Step 8 — Create router: `working_section_memberships.py`

**File: `routers/api_v1/working_section_memberships.py`**

Handles the list-members route. Registered at `/api/v1/working-sections` alongside the CRUD router.

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.list_working_section_members import (
    list_working_section_members,
)
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.get("/{working_section_id}/members")
async def list_working_section_members_route(
    working_section_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"working_section_id": working_section_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_working_section_members, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

### Step 9 — Register routers in `__init__.py`

**File: `routers/api_v1/__init__.py`** (EDIT — add four lines, do not modify existing lines)

The CRUD plan already added `working_sections` to the imports and registered its router at `/api/v1/working-sections`. Do not touch those existing lines. Only add the two new routers.

Add to the existing import line (expand it):
```python
from beyo_manager.routers.api_v1 import ..., user_working_sections, working_section_memberships
```

Or add as a separate import line after the existing one — either form is acceptable.

Add to `register_v1_routers` (after the existing `working_sections` include_router call):
```python
app.include_router(user_working_sections.router, prefix="/api/v1/users", tags=["user-working-sections"])
app.include_router(working_section_memberships.router, prefix="/api/v1/working-sections", tags=["working-section-memberships"])
```

The `working_section_memberships` router is registered at the same prefix as the CRUD router. FastAPI merges routes from both routers under `/api/v1/working-sections` without conflict — the membership router adds `/{id}/members` which does not overlap with any CRUD path (`""`, `"/{id}"`).

---

## Risks and mitigations

- **Risk**: `DELETE` with a JSON body. Some HTTP clients and proxies strip the body from DELETE requests per older HTTP/1.1 interpretations.
  Mitigation: FastAPI supports it via `Body(...)`. Document in API notes that clients must send `Content-Type: application/json` with the DELETE body. If this causes client issues in future, add `POST "/{user_id}/working-sections/unassign"` as an alias.

- **Risk**: Both `working_section_memberships.py` and the CRUD router registered at `/api/v1/working-sections`. If route paths collide, FastAPI returns the first match.
  Mitigation: No collision exists — CRUD routes are `""`, `"/{id}"`, and `"/{id}"` for different methods. Membership route is `"/{id}/members"` (longer path, literal `/members` segment prevents ambiguity).

- **Risk**: The two-step worker validation (WORKER query + fallback any-membership query) issues two DB round-trips on failure.
  Mitigation: The failure path is an error path — performance is not a concern. The two queries give accurate, user-friendly error messages.

- **Risk**: Assign validation loop issues one SELECT per section ID for existence and one for active membership. With a large batch, this is O(2n) queries inside the transaction.
  Mitigation: Batch size is bounded by realistic operational use (assign a user to 1–10 sections at a time). Can be optimised to two bulk SELECT IN queries if needed.

- **Risk**: `domain/working_sections/serializers.py` may not exist yet if the CRUD plan runs after this one.
  Mitigation: Step 1 explicitly covers create-or-edit. Copilot checks whether the file exists before deciding to create or edit.

---

## Validation plan

Run these checks after implementation against a running dev server (bootstrap admin token required):

- `POST /api/v1/users/{worker_user_id}/working-sections` with `{"working_section_ids": ["wsec_..."]}` → `200`, body contains `{"data": {"assigned_section_ids": ["wsec_..."]}}`.
- `POST /api/v1/users/{worker_user_id}/working-sections` same payload again → `409 Conflict` (already assigned).
- `POST /api/v1/users/{admin_user_id}/working-sections` → `422` (not a WORKER).
- `POST /api/v1/users/usr_nonexistent/working-sections` → `404 NotFound`.
- `POST /api/v1/users/{worker_user_id}/working-sections` with `{"working_section_ids": []}` → `422`.
- `POST /api/v1/users/{worker_user_id}/working-sections` with duplicate IDs `["wsec_1", "wsec_1"]` → `422`.
- `GET /api/v1/working-sections/{wsec_id}/members` → `200`, contains the assigned worker with `membership_id`, `user_id`, `username`, `assigned_at`.
- `DELETE /api/v1/users/{worker_user_id}/working-sections` with `{"working_section_ids": ["wsec_..."]}` → `200`, body contains `{"data": {"unassigned_section_ids": ["wsec_..."]}}`.
- `GET /api/v1/working-sections/{wsec_id}/members` after delete → `200`, empty `members` list.
- `DELETE /api/v1/users/{worker_user_id}/working-sections` same payload again → `404 NotFound` (no active membership).
- Worker `POST /api/v1/users/{id}/working-sections` → `403`. Worker `DELETE` → `403`. Worker `GET /members` → `403`.

---

## Review log

- `2026-05-15` `claude-sonnet-4-6`: Plan created. Route shape re-aligned after reading intention file — user-centric batch routes (`/users/{id}/working-sections`) chosen over single-nested section routes. `UserEvent` confirmed via inspection of `domain_event.py` and `build_event.py`. `ConflictError` confirmed at `beyo_manager.errors.validation` (same module as `ValidationError`) — `from beyo_manager.errors.validation import ConflictError, ValidationError`.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `GitHub Copilot`
