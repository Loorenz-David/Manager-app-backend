# PLAN_user_admin_management_20260515

## Metadata

- Plan ID: `PLAN_user_admin_management_20260515`
- Status: `under_construction`
- Owner agent: `Copilot`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T00:00:00Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_user_profile_management_20260515.md`

## Goal and intent

- Goal: Add admin/manager user management endpoints (GET, PATCH, PATCH/deactivate) and a paginated active-users list with string search and FK filters (role, working section), all scoped to the current workspace.
- Business/user intent: Admins and managers need a dashboard-ready user list with role and section context, the ability to update any user's profile and salary fields, and a safe workspace-scoped deactivation action.
- Non-goals: Self-service profile endpoints (covered by `PLAN_user_self_service_profile_20260515`); user re-activation; hard deletion; cross-workspace operations.

## Scope

- In scope:
  - `GET /api/v1/users` — paginated list of **active** workspace members with role, profile_picture, working sections; supports `q`, `string_filters`, `role`, `working_sections` query params
  - `GET /api/v1/users/{user_client_id}` — admin/manager view of any workspace member including salary fields
  - `PATCH /api/v1/users/{user_client_id}` — update identity fields and/or salary fields for any workspace member
  - `PATCH /api/v1/users/{user_client_id}/deactivate` — set `WorkspaceMembership.is_active = False` (admin only)
  - New `serialize_user_list_item` in `domain/users/serializers.py`
  - New `serialize_working_section_compact` in `domain/working_sections/serializers.py`

- Out of scope:
  - Self-service `/me` routes — `PLAN_user_self_service_profile_20260515`
  - User re-activation
  - Hard deletion of User row or WorkspaceMembership row
  - Password reset (already exists in `auth.py`)

- Assumptions:
  - `PLAN_user_self_service_profile_20260515` has been implemented first — `routers/api_v1/users.py` already exists and is registered
  - `services/queries/utils/string_filter.py` (`apply_string_filter`) is implemented (done by `PLAN_query_filter_system_20260515`)
  - `serialize_user_profile(user, work_profile)` already exists in `domain/users/serializers.py`
  - Active working section membership = `WorkingSectionMembership.removed_at IS NULL`
  - No migration needed — only existing columns are touched

## Clarifications required

None — all decisions resolved in alignment.

## Acceptance criteria

1. `GET /api/v1/users` returns only workspace members where `WorkspaceMembership.is_active = True`.
2. `GET /api/v1/users` supports `q` string search against `username`, `email`, `phone_number` via `apply_string_filter`.
3. `GET /api/v1/users` supports `role` filter (comma-separated role names) — exact match against `WorkspaceRole.name`.
4. `GET /api/v1/users` supports `working_sections` filter (comma-separated section names) — users who are active members of any of the named sections.
5. `GET /api/v1/users` response includes `users_pagination` with `has_more`, `limit`, `offset`.
6. Each item in the users list includes: `client_id`, `username`, `email`, `phone_number`, `profile_picture`, `role` (`{client_id, name}`), `working_sections` (`[{client_id, name, image}]`).
7. `GET /api/v1/users/{user_client_id}` returns the full profile including work profile salary fields; raises `NotFound` if user is not an active member of the workspace.
8. `PATCH /api/v1/users/{user_client_id}` updates any subset of `email`, `phone_number`, `profile_picture`, `salary_per_hour_before_tax`, `salary_per_hour_after_tax`; raises `ConflictError` on duplicate email.
9. `PATCH /api/v1/users/{user_client_id}/deactivate` sets `WorkspaceMembership.is_active = False`; raises `ValidationError` if the caller attempts to deactivate their own account.
10. Admin routes use `require_roles([ADMIN, MANAGER])`; deactivate route uses `require_roles([ADMIN])`.
11. Admin routes in `users.py` are appended **after** the `/me` static routes and **before** no wildcards precede them (list `GET /` then `GET /{id}` then `PATCH /{id}` then `PATCH /{id}/deactivate`).

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: command skeleton, transaction boundary, read-before-write pattern
- `backend/architecture/07_queries.md`: query skeleton, session.execute, result extraction methods
- `backend/architecture/07_queries_local.md`: offset pagination — `limit + 1` for `has_more`, `_MAX_LIMIT = 200`, `_DEFAULT_LIMIT = 50`
- `backend/architecture/09_routers.md`: router skeleton, static-before-wildcard order, path param merging into `incoming_data`
- `backend/architecture/05_errors.md`: `ValidationError`, `ConflictError`, `NotFound`
- `backend/architecture/55_query_filters_local.md`: `apply_string_filter` utility, `q` + `string_filters` params, joined table pattern, conditional join pattern

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: overrides cursor pagination → offset. All list queries use `limit`/`offset` pattern from this file.

### File read intent — pattern vs. relational

Prohibited (pattern reads — contracts cover these):
- Reading another query for the pagination shape → `07_queries_local.md`
- Reading another command for `session.begin()` shape → `06_commands.md`
- Reading `list_working_sections.py` for filter builder pattern → `55_query_filters_local.md`

Permitted (relational reads — understanding what exists):
- Reading `domain/users/serializers.py` for exact `serialize_user_profile` signature
- Reading `domain/working_sections/serializers.py` to see existing functions before adding the new one
- Reading `models/tables/working_sections/working_section_membership.py` for exact field names (`removed_at`, `workspace_id`)
- Reading `models/tables/workspaces/workspace_membership.py` for `is_active`, `workspace_role_id` fields
- Reading `models/tables/roles/workspace_role.py` for `name`, `client_id` fields
- Reading `routers/api_v1/users.py` to confirm `/me` routes are declared and to append admin routes correctly

### Skill selection

- Primary skill: not applicable — governed entirely by contracts above
- Excluded alternatives: none

## Implementation plan

### File manifest

| Action | File |
|--------|------|
| CREATE | `backend/app/beyo_manager/services/queries/users/get_user_admin.py` |
| CREATE | `backend/app/beyo_manager/services/queries/users/list_users.py` |
| CREATE | `backend/app/beyo_manager/services/commands/users/requests/update_user_admin_request.py` |
| CREATE | `backend/app/beyo_manager/services/commands/users/update_user_admin.py` |
| CREATE | `backend/app/beyo_manager/services/commands/users/requests/deactivate_user_request.py` |
| CREATE | `backend/app/beyo_manager/services/commands/users/deactivate_user.py` |
| EDIT   | `backend/app/beyo_manager/routers/api_v1/users.py` |
| EDIT   | `backend/app/beyo_manager/domain/users/serializers.py` |
| EDIT   | `backend/app/beyo_manager/domain/working_sections/serializers.py` |

**Prerequisite**: `PLAN_user_self_service_profile_20260515` must be implemented before this plan. `routers/api_v1/users.py` and `services/queries/users/__init__.py` must already exist.

---

### Step 1 — EDIT `domain/working_sections/serializers.py`

Add `serialize_working_section_compact` for use in the users list. Append at the bottom — do not modify existing functions.

```python
def serialize_working_section_compact(section_id: str, section_name: str, section_image: str | None) -> dict:
    return {
        "client_id": section_id,
        "name": section_name,
        "image": section_image,
    }
```

---

### Step 2 — EDIT `domain/users/serializers.py`

Add `serialize_user_list_item` for the users list endpoint. Append at the bottom — do not modify existing functions.

```python
def serialize_user_list_item(
    user: User,
    role_client_id: str,
    role_name: str,
    working_sections: list[dict],
) -> dict:
    return {
        "client_id": user.client_id,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "profile_picture": user.profile_picture,
        "role": {"client_id": role_client_id, "name": role_name},
        "working_sections": working_sections,
    }
```

---

### Step 3 — `services/queries/users/get_user_admin.py`

Returns full profile including work profile. User must be an active member of `ctx.workspace_id`.

```python
from sqlalchemy import select

from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext


async def get_user_admin(ctx: ServiceContext) -> dict:
    user_client_id = ctx.incoming_data.get("user_client_id")

    membership = await ctx.session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.user_id == user_client_id,
            WorkspaceMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise NotFound("User not found in workspace.")

    user = await ctx.session.scalar(
        select(User).where(User.client_id == user_client_id)
    )

    work_profile = await ctx.session.scalar(
        select(UserWorkProfile).where(
            UserWorkProfile.user_id == user_client_id,
            UserWorkProfile.workspace_id == ctx.workspace_id,
        )
    )

    return {"user": serialize_user_profile(user, work_profile)}
```

---

### Step 4 — `services/queries/users/list_users.py`

Pagination: offset-based (`07_queries_local.md`).
String search: `apply_string_filter` on `username`, `email`, `phone_number` (all on `User` — no join needed for string search).
Role filter: exact match on `WorkspaceRole.name` — join is always present for role data.
Working sections filter: `EXISTS` subquery — conditional, avoids row duplication.
Sections data for serialization: second query after pagination, keyed by `user_id`.

```python
from sqlalchemy import exists, select
from sqlalchemy.orm import aliased

from beyo_manager.domain.users.serializers import serialize_user_list_item
from beyo_manager.domain.working_sections.serializers import serialize_working_section_compact
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.string_filter import apply_string_filter

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50

_ALLOWED_STRING_COLUMNS = {
    "username": User.username,
    "email": User.email,
    "phone_number": User.phone_number,
}


async def list_users(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    string_filters = ctx.query_params.get("string_filters")
    role_filter = ctx.query_params.get("role")
    sections_filter = ctx.query_params.get("working_sections")

    stmt = (
        select(
            User,
            WorkspaceRole.client_id.label("role_client_id"),
            WorkspaceRole.name.label("role_name"),
        )
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.client_id)
        .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
        .where(
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.is_active.is_(True),
        )
    )

    stmt = apply_string_filter(stmt, q, string_filters, _ALLOWED_STRING_COLUMNS)

    if role_filter:
        role_names = [r.strip() for r in role_filter.split(",") if r.strip()]
        stmt = stmt.where(WorkspaceRole.name.in_(role_names))

    if sections_filter:
        section_names = [s.strip() for s in sections_filter.split(",") if s.strip()]
        stmt = stmt.where(
            exists(
                select(WorkingSectionMembership.client_id)
                .join(
                    WorkingSection,
                    WorkingSection.client_id == WorkingSectionMembership.working_section_id,
                )
                .where(
                    WorkingSectionMembership.user_id == User.client_id,
                    WorkingSectionMembership.workspace_id == ctx.workspace_id,
                    WorkingSectionMembership.removed_at.is_(None),
                    WorkingSection.workspace_id == ctx.workspace_id,
                    WorkingSection.is_deleted.is_(False),
                    WorkingSection.name.in_(section_names),
                )
            )
        )

    stmt = stmt.order_by(User.username.asc()).offset(offset).limit(limit + 1)
    result = await ctx.session.execute(stmt)
    rows = result.all()
    has_more = len(rows) > limit
    page = rows[:limit]

    if not page:
        return {
            "users": [],
            "users_pagination": {"has_more": False, "limit": limit, "offset": offset},
        }

    user_ids = [row.User.client_id for row in page]

    sections_result = await ctx.session.execute(
        select(
            WorkingSectionMembership.user_id,
            WorkingSection.client_id,
            WorkingSection.name,
            WorkingSection.image,
        )
        .join(
            WorkingSection,
            WorkingSection.client_id == WorkingSectionMembership.working_section_id,
        )
        .where(
            WorkingSectionMembership.user_id.in_(user_ids),
            WorkingSectionMembership.workspace_id == ctx.workspace_id,
            WorkingSectionMembership.removed_at.is_(None),
            WorkingSection.is_deleted.is_(False),
        )
    )
    sections_by_user: dict[str, list[dict]] = {uid: [] for uid in user_ids}
    for sec_row in sections_result.all():
        sections_by_user[sec_row.user_id].append(
            serialize_working_section_compact(sec_row.client_id, sec_row.name, sec_row.image)
        )

    return {
        "users": [
            serialize_user_list_item(
                row.User,
                row.role_client_id,
                row.role_name,
                sections_by_user[row.User.client_id],
            )
            for row in page
        ],
        "users_pagination": {"has_more": has_more, "limit": limit, "offset": offset},
    }
```

---

### Step 5 — `services/commands/users/requests/update_user_admin_request.py`

All fields optional. Salary accepts `None` to clear.

```python
from decimal import Decimal

from pydantic import BaseModel, EmailStr, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError


class UpdateUserAdminRequest(BaseModel):
    user_client_id: str
    email: EmailStr | None = None
    phone_number: str | None = None
    profile_picture: str | None = None
    salary_per_hour_before_tax: Decimal | None = None
    salary_per_hour_after_tax: Decimal | None = None


def parse_update_user_admin_request(data: dict) -> UpdateUserAdminRequest:
    try:
        return UpdateUserAdminRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
```

---

### Step 6 — `services/commands/users/update_user_admin.py`

```python
from sqlalchemy import select

from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.errors.conflict import ConflictError
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.requests.update_user_admin_request import (
    parse_update_user_admin_request,
)
from beyo_manager.services.context import ServiceContext


async def update_user_admin(ctx: ServiceContext) -> dict:
    request = parse_update_user_admin_request(ctx.incoming_data)

    async with ctx.session.begin():
        membership = await ctx.session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == ctx.workspace_id,
                WorkspaceMembership.user_id == request.user_client_id,
                WorkspaceMembership.is_active.is_(True),
            )
        )
        if membership is None:
            raise NotFound("User not found in workspace.")

        user = await ctx.session.scalar(
            select(User).where(User.client_id == request.user_client_id)
        )

        if request.email is not None and request.email != user.email:
            conflict = await ctx.session.scalar(
                select(User).where(
                    User.email == request.email,
                    User.client_id != request.user_client_id,
                )
            )
            if conflict is not None:
                raise ConflictError("Email is already in use.")
            user.email = request.email

        if "phone_number" in ctx.incoming_data:
            user.phone_number = request.phone_number

        if "profile_picture" in ctx.incoming_data:
            user.profile_picture = request.profile_picture

        work_profile = await ctx.session.scalar(
            select(UserWorkProfile).where(
                UserWorkProfile.user_id == request.user_client_id,
                UserWorkProfile.workspace_id == ctx.workspace_id,
            )
        )
        if work_profile is not None:
            if "salary_per_hour_before_tax" in ctx.incoming_data:
                work_profile.salary_per_hour_before_tax = request.salary_per_hour_before_tax
            if "salary_per_hour_after_tax" in ctx.incoming_data:
                work_profile.salary_per_hour_after_tax = request.salary_per_hour_after_tax

    return {"user": serialize_user_profile(user, work_profile)}
```

---

### Step 7 — `services/commands/users/requests/deactivate_user_request.py`

```python
from pydantic import BaseModel, ValidationError as PydanticValidationError

from beyo_manager.errors.validation import ValidationError


class DeactivateUserRequest(BaseModel):
    user_client_id: str


def parse_deactivate_user_request(data: dict) -> DeactivateUserRequest:
    try:
        return DeactivateUserRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
```

---

### Step 8 — `services/commands/users/deactivate_user.py`

```python
from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.requests.deactivate_user_request import (
    parse_deactivate_user_request,
)
from beyo_manager.services.context import ServiceContext


async def deactivate_user(ctx: ServiceContext) -> dict:
    request = parse_deactivate_user_request(ctx.incoming_data)

    if request.user_client_id == ctx.user_id:
        raise ValidationError("user_client_id: cannot deactivate your own account.")

    async with ctx.session.begin():
        membership = await ctx.session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == ctx.workspace_id,
                WorkspaceMembership.user_id == request.user_client_id,
                WorkspaceMembership.is_active.is_(True),
            )
        )
        if membership is None:
            raise NotFound("User not found or already inactive in workspace.")

        membership.is_active = False

    return {}
```

---

### Step 9 — EDIT `routers/api_v1/users.py`

Append admin routes **after** the existing `/me` routes. Follow static-before-wildcard order: `GET /` list first, then `GET /{id}`, then `PATCH /{id}`, then `PATCH /{id}/deactivate`.

**Add to imports:**
```python
from fastapi import Query
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.services.commands.users.update_user_admin import update_user_admin
from beyo_manager.services.commands.users.deactivate_user import deactivate_user
from beyo_manager.services.queries.users.get_user_admin import get_user_admin
from beyo_manager.services.queries.users.list_users import list_users
```

**New Pydantic body model (add in router file):**
```python
class UpdateUserAdminBody(BaseModel):
    email: str | None = None
    phone_number: str | None = None
    profile_picture: str | None = None
    salary_per_hour_before_tax: str | None = None
    salary_per_hour_after_tax: str | None = None
```

**Append routes (in this exact order after /me routes):**
```python
@router.get("")
async def list_users_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    string_filters: str | None = Query(None),
    role: str | None = Query(None),
    working_sections: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "string_filters": string_filters,
            "role": role,
            "working_sections": working_sections,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_users, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{user_client_id}")
async def get_user_admin_route(
    user_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_client_id": user_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_user_admin, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{user_client_id}")
async def update_user_admin_route(
    user_client_id: str,
    body: UpdateUserAdminBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_client_id": user_client_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_user_admin, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{user_client_id}/deactivate")
async def deactivate_user_route(
    user_client_id: str,
    claims: dict = Depends(require_roles([ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_client_id": user_client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(deactivate_user, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

## Risks and mitigations

- Risk: `list_users` query joins `WorkspaceMembership` and `WorkspaceRole` in a compound `select()` returning multiple columns — `result.all()` returns `Row` objects, not ORM instances. Access the user via `row.User`, role via `row.role_client_id` / `row.role_name`.
  Mitigation: Target code uses `row.User`, `row.role_client_id`, `row.role_name` throughout — exact access pattern specified.

- Risk: `working_sections` filter uses EXISTS subquery. If SQLAlchemy version does not support the correlated `exists()` form, it will raise at query-build time.
  Mitigation: `exists(select(...).where(...))` is standard SQLAlchemy 2.x and already used elsewhere in the codebase.

- Risk: `update_user_admin` reads `work_profile` inside the `begin()` block but references it outside (in the return). After the block commits, lazy-loading is disabled — `work_profile` may be expired.
  Mitigation: Access only already-loaded attributes after the block. Both `user` and `work_profile` are loaded inside the block and their Python-side state is available after commit.

- Risk: `PATCH /api/v1/users/{user_client_id}` uses `body.model_dump()` without `exclude_none`. This is intentional — the command uses `"field" in ctx.incoming_data` to distinguish explicit-null from absent.
  Mitigation: Documented in Step 9 — do not add `exclude_none=True`.

- Risk: `deactivate_user` guard checks `user_client_id == ctx.user_id` **before** the transaction. This is intentional — no DB round-trip needed for a self-deactivation guard.
  Mitigation: The guard is in the command body before `session.begin()`, consistent with contract 06's domain guard pattern.

## Validation plan

- `GET /api/v1/users` with admin JWT → HTTP 200, `data.users` is a list, `data.users_pagination` present
- `GET /api/v1/users?q=john` → returns only users with "john" in username/email/phone_number
- `GET /api/v1/users?role=admin` → returns only users with admin workspace role
- `GET /api/v1/users?working_sections=paint` → returns only users who are active members of a "paint" section
- `GET /api/v1/users/{user_client_id}` with valid admin JWT → HTTP 200, `data.user.work_profile` present
- `GET /api/v1/users/{user_client_id}` for user not in workspace → HTTP 404
- `PATCH /api/v1/users/{user_client_id}` with `{"email": "new@example.com"}` → HTTP 200, email updated
- `PATCH /api/v1/users/{user_client_id}/deactivate` → HTTP 200, `{}`
- `PATCH /api/v1/users/{ctx.user_id}/deactivate` (self-deactivation) → HTTP 400

## Review log

*(none yet)*

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
