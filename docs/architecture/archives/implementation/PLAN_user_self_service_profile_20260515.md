# PLAN_user_self_service_profile_20260515

## Metadata

- Plan ID: `PLAN_user_self_service_profile_20260515`
- Status: `under_construction`
- Owner agent: `Copilot`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T00:00:00Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_user_profile_management_20260515.md`

## Goal and intent

- Goal: Add self-service profile endpoints (`GET /me`, `PATCH /me`, `PATCH /me/password`) so any authenticated user can read and update their own profile without admin intervention.
- Business/user intent: Workers, sellers, and managers need to maintain their own contact info, profile picture, and password independently. Password change is security-sensitive and uses a dedicated endpoint that requires current-password verification.
- Non-goals: Admin modification of other users' profiles (covered by `PLAN_user_admin_management_20260515`); user deactivation; users list; salary fields (work profile is admin-only).

## Scope

- In scope:
  - `GET /api/v1/users/me` — return own profile (username, email, phone_number, profile_picture)
  - `PATCH /api/v1/users/me` — update own profile fields (email, phone_number, profile_picture)
  - `PATCH /api/v1/users/me/password` — change own password (requires current_password)
  - Create `routers/api_v1/users.py` (self-service routes only; admin routes added by `PLAN_user_admin_management_20260515`)
  - Register `users.router` in `routers/api_v1/__init__.py`

- Out of scope:
  - Admin GET/UPDATE/deactivate of other users — handled in `PLAN_user_admin_management_20260515`
  - Users list endpoint
  - Profile picture file upload (client sends URL string only)
  - Work profile (salary) fields

- Assumptions:
  - `serialize_user_profile(user)` already exists at `domain/users/serializers.py` — use it directly, no new serializer needed
  - `User.profile_picture` is the image field (String 512, nullable)
  - Password hashing uses `bcrypt` (same as `register_user.py`)
  - No migration needed — only existing columns are touched

## Clarifications required

None — all decisions resolved in alignment.

## Acceptance criteria

1. `GET /api/v1/users/me` returns the authenticated user's own profile using `serialize_user_profile(user)` (without work_profile).
2. `PATCH /api/v1/users/me` updates any combination of `email`, `phone_number`, `profile_picture`; omitted fields are unchanged.
3. `PATCH /api/v1/users/me` raises `ConflictError` if the new email is already taken by another user.
4. `PATCH /api/v1/users/me/password` verifies `current_password` against the stored bcrypt hash and raises `ValidationError` if it does not match.
5. `PATCH /api/v1/users/me/password` updates `User.password` to a bcrypt hash of `new_password`.
6. All three routes are declared in `users.py` using `get_jwt_claims` (any authenticated role, no role restriction).
7. `users.router` is registered at `/api/v1/users` in `routers/api_v1/__init__.py`.
8. Self-service routes (`/me`, `/me/password`) are declared **before** any wildcard `/{id}` routes in `users.py`.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: command skeleton, request parsing, transaction boundary, bcrypt pattern
- `backend/architecture/07_queries.md`: query skeleton, session.execute pattern
- `backend/architecture/07_queries_local.md`: offset pagination (not used here — no list query in this plan)
- `backend/architecture/09_routers.md`: router skeleton, static-before-wildcard rule, `get_jwt_claims` usage, path param merging
- `backend/architecture/05_errors.md`: `ValidationError`, `ConflictError`, `NotFound` error classes

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: confirms offset-based pagination — not applicable to this plan's GET /me query

### File read intent — pattern vs. relational

Prohibited (pattern reads — contracts cover these):
- Reading another command for the `async with ctx.session.begin()` shape → `06_commands.md`
- Reading another router for handler wiring → `09_routers.md`
- Reading `register_user.py` for bcrypt usage → `06_commands.md` defines the pattern

Permitted (relational reads — understanding what exists):
- Reading `domain/users/serializers.py` to confirm `serialize_user_profile` signature
- Reading `models/tables/users/user.py` for exact field names
- Reading `routers/api_v1/__init__.py` to verify registration syntax
- Reading `routers/utils/roles.py` for role constant names
- Reading `routers/api_v1/auth.py` top-level imports only (to verify `get_jwt_claims` import path)

### Skill selection

- Primary skill: not applicable — standard command + query + router scaffolding governed entirely by contracts above
- Excluded alternatives: none

## Implementation plan

### File manifest

| Action | File |
|--------|------|
| CREATE | `backend/app/beyo_manager/services/queries/users/__init__.py` |
| CREATE | `backend/app/beyo_manager/services/queries/users/get_self_profile.py` |
| CREATE | `backend/app/beyo_manager/services/commands/users/requests/update_self_profile_request.py` |
| CREATE | `backend/app/beyo_manager/services/commands/users/update_self_profile.py` |
| CREATE | `backend/app/beyo_manager/services/commands/users/requests/update_self_password_request.py` |
| CREATE | `backend/app/beyo_manager/services/commands/users/update_self_password.py` |
| CREATE | `backend/app/beyo_manager/routers/api_v1/users.py` |
| EDIT   | `backend/app/beyo_manager/routers/api_v1/__init__.py` |

---

### Step 1 — `services/queries/users/__init__.py`

Empty file. Package marker only.

---

### Step 2 — `services/queries/users/get_self_profile.py`

```python
from sqlalchemy import select

from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext


async def get_self_profile(ctx: ServiceContext) -> dict:
    user = await ctx.session.scalar(
        select(User).where(User.client_id == ctx.user_id)
    )
    if user is None:
        raise NotFound("User not found.")
    return {"user": serialize_user_profile(user)}
```

---

### Step 3 — `services/commands/users/requests/update_self_profile_request.py`

All fields optional (PATCH semantics — omitted fields leave the current value unchanged).

```python
from pydantic import BaseModel, EmailStr, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class UpdateSelfProfileRequest(BaseModel):
    email: EmailStr | None = None
    phone_number: str | None = None
    profile_picture: str | None = None


def parse_update_self_profile_request(data: dict) -> UpdateSelfProfileRequest:
    try:
        return UpdateSelfProfileRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
```

---

### Step 4 — `services/commands/users/update_self_profile.py`

```python
from sqlalchemy import select

from beyo_manager.errors.conflict import ConflictError
from beyo_manager.errors.not_found import NotFound
from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.commands.users.requests.update_self_profile_request import (
    parse_update_self_profile_request,
)
from beyo_manager.services.context import ServiceContext


async def update_self_profile(ctx: ServiceContext) -> dict:
    request = parse_update_self_profile_request(ctx.incoming_data)

    async with ctx.session.begin():
        user = await ctx.session.scalar(
            select(User).where(User.client_id == ctx.user_id)
        )
        if user is None:
            raise NotFound("User not found.")

        if request.email is not None and request.email != user.email:
            conflict = await ctx.session.scalar(
                select(User).where(
                    User.email == request.email,
                    User.client_id != ctx.user_id,
                )
            )
            if conflict is not None:
                raise ConflictError("Email is already in use.")
            user.email = request.email

        if "phone_number" in ctx.incoming_data:
            user.phone_number = request.phone_number

        if "profile_picture" in ctx.incoming_data:
            user.profile_picture = request.profile_picture

    return {"user": serialize_user_profile(user)}
```

---

### Step 5 — `services/commands/users/requests/update_self_password_request.py`

```python
from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class UpdateSelfPasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password", mode="before")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("new_password must be at least 8 characters.")
        return v


def parse_update_self_password_request(data: dict) -> UpdateSelfPasswordRequest:
    try:
        return UpdateSelfPasswordRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
```

---

### Step 6 — `services/commands/users/update_self_password.py`

```python
import bcrypt
from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.commands.users.requests.update_self_password_request import (
    parse_update_self_password_request,
)
from beyo_manager.services.context import ServiceContext


async def update_self_password(ctx: ServiceContext) -> dict:
    request = parse_update_self_password_request(ctx.incoming_data)

    async with ctx.session.begin():
        user = await ctx.session.scalar(
            select(User).where(User.client_id == ctx.user_id)
        )
        if user is None:
            raise NotFound("User not found.")

        if not bcrypt.checkpw(request.current_password.encode(), user.password.encode()):
            raise ValidationError("current_password: incorrect password.")

        user.password = bcrypt.hashpw(
            request.new_password.encode(), bcrypt.gensalt()
        ).decode()

    return {}
```

---

### Step 7 — `routers/api_v1/users.py`

Declare `/me` static routes **before** any future `/{user_client_id}` wildcard routes (per contract 09 route order rule). Admin routes from `PLAN_user_admin_management_20260515` will be appended after these.

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims
from beyo_manager.services.commands.users.update_self_profile import update_self_profile
from beyo_manager.services.commands.users.update_self_password import update_self_password
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.users.get_self_profile import get_self_profile
from beyo_manager.services.run_service import run_service

router = APIRouter()


class UpdateSelfProfileBody(BaseModel):
    email: str | None = None
    phone_number: str | None = None
    profile_picture: str | None = None


class UpdateSelfPasswordBody(BaseModel):
    current_password: str
    new_password: str


@router.get("/me")
async def get_self_profile_route(
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={}, identity=claims, session=session)
    outcome = await run_service(get_self_profile, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/me")
async def update_self_profile_route(
    body: UpdateSelfProfileBody,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_self_profile, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/me/password")
async def update_self_password_route(
    body: UpdateSelfPasswordBody,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_self_password, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

### Step 8 — EDIT `routers/api_v1/__init__.py`

Add import and uncomment the users router registration.

**Add to imports block:**
```python
from beyo_manager.routers.api_v1 import users
```

**Replace the commented line:**
```python
# app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
```
**With:**
```python
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
```

## Risks and mitigations

- Risk: `PATCH /me` with `phone_number=null` in the body should clear the field, but `exclude_none=True` in `model_dump()` would silently drop it.
  Mitigation: Use plain `body.model_dump()` (without `exclude_none`) in the router. The command checks `"phone_number" in ctx.incoming_data` to distinguish explicit-null from absent.

- Risk: Future admin routes in `users.py` are declared after `/{user_client_id}` wildcard, and `/me` is incorrectly captured as a path param value.
  Mitigation: `/me` routes are declared first in the file. `PLAN_user_admin_management_20260515` must append its routes after the `/me` group and list route, following the static-before-wildcard order in contract 09.

- Risk: `update_self_profile` command does not have `updated_at` field on `User`.
  Mitigation: `User` model has no `updated_at` column (confirmed from model read) — do not add one.

## Validation plan

- `GET /api/v1/users/me` with valid JWT → HTTP 200, `data.user` has `client_id`, `username`, `email`, `phone_number`, `profile_picture`
- `PATCH /api/v1/users/me` with `{"email": "new@example.com"}` → HTTP 200, returned email updated
- `PATCH /api/v1/users/me` with duplicate email → HTTP 409
- `PATCH /api/v1/users/me/password` with wrong `current_password` → HTTP 400
- `PATCH /api/v1/users/me/password` with correct `current_password` and `new_password` ≥ 8 chars → HTTP 200, `{}`
- `PATCH /api/v1/users/me/password` with `new_password` < 8 chars → HTTP 400

## Review log

*(none yet)*

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
