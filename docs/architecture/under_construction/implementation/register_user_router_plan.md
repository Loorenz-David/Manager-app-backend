# PLAN_register_user_router_20260515

## Metadata

- Plan ID: `PLAN_register_user_router_20260515`
- Status: `under_construction`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T00:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_register_user_router_20260515.md`

## Goal and intent

- Goal:
  Implement an authenticated `POST /api/v1/auth/register` endpoint that allows an admin in a workspace to create a new user in that same workspace, with membership and optional working section assignment created atomically.
- Business/user intent:
  Enable admin-managed user onboarding (not public self-registration) while enforcing tenant boundaries and existing RBAC rules. When registering a WORKER, the admin can immediately assign them to one or more working sections in the same request.
- Non-goals:
  Email verification, invite links, password reset, auto-login on register, multi-workspace assignment at creation, RBAC graph redesign, background event fanout.

## Scope

- In scope:
  Router handler in `auth` router, `register_user` command, request parser, domain validator for password policy, role resolution with workspace constraint, uniqueness checks, password hashing, atomic user + membership + optional section memberships write, `serialize_user_profile` serializer.
- Out of scope:
  Any auth flow changes outside register path (`sign-in`, refresh, logout), migration changes (all tables already exist), frontend flows, `user_guards.py` (no state-based authorization guard needed — role guard is handled by `require_roles([ADMIN])` at the router).
- Assumptions:
  - `require_roles` and `ADMIN` remain authoritative for role guard decisions.
  - `username` uniqueness is **global** — the `User` model has a DB-level `unique=True` on `username`. There is no per-workspace username uniqueness to implement.
  - `WorkingSectionMembership` table already exists (created by CRUD plan).
  - `assign_user_to_working_sections` command already exists and is fully implemented. Its section-assignment DB logic is reproduced inline in the register command to keep user creation, membership, and section assignments in a single atomic transaction. This is intentional — calling another command from within a transaction violates contract 06.

## File manifest

List every file touched by this plan. Implementing agents use this table to know what
to open (EDIT) versus what to create from scratch (CREATE). Never search for CREATE files
— they do not exist yet.

### Existing files to edit

| Path (relative to `backend/app/`) | Change summary |
|---|---|
| `beyo_manager/routers/api_v1/auth.py` | Add `RegisterUserBody` Pydantic model and `@router.post("/register")` handler |

### New files to create

| Path (relative to `backend/app/`) |
|---|
| `beyo_manager/services/commands/users/__init__.py` |
| `beyo_manager/services/commands/users/requests/__init__.py` |
| `beyo_manager/services/commands/users/requests/register_user_request.py` |
| `beyo_manager/domain/users/validators.py` |
| `beyo_manager/domain/users/serializers.py` |
| `beyo_manager/services/commands/users/register_user.py` |

## Clarifications required

All items below are **resolved decisions**. Copilot must follow them exactly — do not reinterpret or find alternatives.

- [x] **Username uniqueness**: Global. The `User` model has `unique=True` on `username` at the DB level. Duplicate username returns `ConflictError("Username already taken.")`. No per-workspace check needed.
- [x] **HTTP status**: `200 OK`. Consistent with all other existing routes — no `201 Created`.
- [x] **Route ownership**: `POST /api/v1/auth/register` lives in `auth.py`. Contract 09 notes this should ideally be in `users.py`, but this plan scopes to `auth.py` to match the stated acceptance criteria. A future refactor can move it.
- [x] **Working section assignment atomicity**: If `working_section_ids` is provided, section memberships are created inside the same `async with ctx.session.begin()` block as the user and workspace membership. This guarantees no partial commits. A separate call to `assign_user_to_working_sections` is NOT used because: (a) that command opens its own transaction and cannot be nested, and (b) contract 06 forbids calling commands from commands.
- [x] **Working section ids validation**: `working_section_ids` is only valid when the resolved role is a WORKER role. If provided for any other role, raise `ValidationError("working_section_ids can only be provided when registering a WORKER.")`. Check BEFORE the transaction.
- [x] **Serializer location**: `beyo_manager/domain/users/serializers.py`. Per contract 46 and the project pattern, serializers are plain functions in `domain/<domain>/serializers.py`. Do NOT create a serializer inside `services/queries/`.
- [x] **`ValidationError` class**: Import from `beyo_manager.errors.validation`. The class is `ValidationError`. `ValidationFailed` does NOT exist in this codebase.

## Acceptance criteria

1. `POST /api/v1/auth/register` exists in `beyo_manager/routers/api_v1/auth.py` and is protected by `require_roles([ADMIN])`.
2. Request body accepts `username`, `email`, `password`, `phone_number` (optional), `role_id`, `working_section_ids` (optional, default `[]`). `workspace_id` is never accepted from body.
3. Command resolves `WorkspaceRole` scoped to `ctx.workspace_id`; cross-workspace role lookup returns `NotFound("Workspace role not found.")`.
4. Duplicate email returns `ConflictError("A user with this email already exists.")`.
5. Duplicate username returns `ConflictError("Username already taken.")`.
6. Password is hashed before any `session.add(...)` call; plaintext password is never persisted, serialized, or logged.
7. `User`, `WorkspaceMembership`, and (if provided) `WorkingSectionMembership` rows are all inserted inside one `async with ctx.session.begin()` transaction; no partial commit is possible.
8. If `working_section_ids` is non-empty and the resolved role is not WORKER, raises `ValidationError("working_section_ids can only be provided when registering a WORKER.")` before the transaction starts.
9. If any `working_section_id` in the list is not found in the workspace, raises `NotFound(f"Working section '{section_id}' not found.")` inside the transaction (rolls back all prior inserts).
10. Route returns `{"user": serialize_user_profile(user)}` and the serializer output excludes `password` and all internal sensitive fields.
11. Unauthorized request returns `401`; authenticated non-admin returns `403`.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: Layer map, dependency boundaries, domain grouping by vertical slice.
- `backend/architecture/04_context.md`: `ServiceContext` ownership of identity/session/incoming_data and `ctx.workspace_id` source-of-truth.
- `backend/architecture/05_errors.md`: `DomainError` hierarchy — `ValidationError`, `ConflictError`, `NotFound`. Note: `ValidationFailed` does NOT exist in this codebase.
- `backend/architecture/06_commands.md`: Write-path command structure, request parsing, transaction boundaries, private helpers. Commands must not call other commands.
- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: Serialization patterns. Local extension takes precedence.
- `backend/architecture/08_domain.md`: Pure domain functions for validators without I/O.
- `backend/architecture/09_routers.md`: Router handler skeleton and service invocation pattern.
- `backend/architecture/21_naming_conventions.md`: Naming for files/functions/fields.
- `backend/architecture/24_multi_tenancy.md`: Workspace-scoping rules and membership role model.
- `backend/architecture/40_identity.md`: `client_id` strategy and identity generation.
- `backend/architecture/41_user.md`: User model conventions.
- `backend/architecture/46_serialization.md`: Serializers are plain functions in `domain/<domain>/serializers.py`.

### Local extensions loaded

- `backend/architecture/40_identity_local.md`: App-specific identity constraints/delta.
- `backend/architecture/41_user_local.md`: App-specific user model/behavior deltas.
- `backend/architecture/07_queries_local.md`: Offset-based pagination and list-query completion gate. (No list query in this plan — loaded for serialization guidance only.)
- No local extension files found for 01, 04, 05, 06, 08, 09, 21, 24, 46 at plan-writing time.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read contracts (`06_commands.md`, `09_routers.md`, etc.).
- **What exists** → implementation reads are valid (field names, import paths, existing patterns).

Permitted relational reads for this plan:
- `beyo_manager/routers/api_v1/auth.py` — to know what already exists before adding the new route
- `beyo_manager/models/tables/users/user.py` — exact field names for `User`
- `beyo_manager/models/tables/workspaces/workspace_membership.py` — field names for `WorkspaceMembership`
- `beyo_manager/models/tables/working_sections/working_section.py` — `client_id`, `is_deleted`, `workspace_id`
- `beyo_manager/models/tables/working_sections/working_section_membership.py` — field names for insert
- `beyo_manager/models/tables/roles/workspace_role.py` — field names for role resolution
- `beyo_manager/models/tables/roles/role.py` — `name`, `client_id`
- `beyo_manager/domain/roles/enums.py` — `RoleNameEnum` for WORKER check

### Skill selection

- Primary skill: `backend/task_system/backend_contract_goal_mapping_guide.md` (document-only protocol and contract resolution discipline).
- Excluded alternatives: Runtime/worker skills excluded — no queue/replay/worker scope.

---

## Implementation plan

All paths are relative to `backend/app/beyo_manager/`.

---

### Step 1 — Create `domain/users/validators.py`

**File: `domain/users/validators.py`** (CREATE)

Pure function with no I/O. Called from the command after parsing.

```python
from beyo_manager.errors.validation import ValidationError

_MIN_PASSWORD_LENGTH = 8


def validate_password_policy(password: str) -> None:
    if len(password) < _MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long.")
```

---

### Step 2 — Create `domain/users/serializers.py`

**File: `domain/users/serializers.py`** (CREATE)

Plain serializer function. Excludes `password` and all internal fields.

```python
from beyo_manager.models.tables.users.user import User


def serialize_user_profile(user: User) -> dict:
    return {
        "client_id": user.client_id,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "profile_picture": user.profile_picture,
        "created_at": user.created_at.isoformat(),
    }
```

---

### Step 3 — Create request parser

**File: `services/commands/users/requests/register_user_request.py`** (CREATE)

```python
from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class RegisterUserRequest(BaseModel):
    username: str
    email: str
    password: str
    phone_number: str | None = None
    role_id: str
    working_section_ids: list[str] = []

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("username must not be blank.")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("email must not be blank.")
        return v

    @field_validator("password", mode="before")
    @classmethod
    def password_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("password must not be blank.")
        return v

    @field_validator("role_id", mode="before")
    @classmethod
    def role_id_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("role_id must not be blank.")
        return v


def parse_register_user_request(data: dict) -> RegisterUserRequest:
    try:
        return RegisterUserRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

### Step 4 — Create command `register_user.py`

**File: `services/commands/users/register_user.py`** (CREATE)

Logic order:
1. Parse request.
2. Validate password policy (pure domain function).
3. If `working_section_ids` is non-empty, validate that the role resolves to a WORKER role — raise `ValidationError` if not. This check happens BEFORE the transaction.
4. Open `async with ctx.session.begin()`:
   a. Resolve `WorkspaceRole` by `role_id` in `ctx.workspace_id` — raise `NotFound` if not found.
   b. Check email uniqueness (global) — raise `ConflictError` if taken.
   c. Check username uniqueness (global) — raise `ConflictError` if taken.
   d. Hash password.
   e. Insert `User`, flush to get `client_id`.
   f. Insert `WorkspaceMembership` (workspace_id=ctx.workspace_id, workspace_role_id=resolved_role.client_id, is_active=True), flush.
   g. If `working_section_ids` is non-empty:
      - Bulk-validate all section IDs exist in workspace (single `IN` query) — raise `NotFound` for any missing.
      - Insert one `WorkingSectionMembership` per section ID, flush after all inserts.
5. Return `{"user": serialize_user_profile(user)}`.

```python
import bcrypt
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.domain.users.validators import validate_password_policy
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.requests.register_user_request import (
    RegisterUserRequest,
    parse_register_user_request,
)
from beyo_manager.services.context import ServiceContext


async def register_user(ctx: ServiceContext) -> dict:
    request: RegisterUserRequest = parse_register_user_request(ctx.incoming_data)
    validate_password_policy(request.password)

    # Pre-transaction: if sections requested, verify role is WORKER before opening DB
    if request.working_section_ids:
        if len(request.working_section_ids) != len(set(request.working_section_ids)):
            raise ValidationError("Duplicate IDs in working_section_ids are not allowed.")

    async with ctx.session.begin():
        # Resolve workspace role
        workspace_role = await ctx.session.scalar(
            select(WorkspaceRole)
            .join(Role, Role.client_id == WorkspaceRole.role_id)
            .where(
                WorkspaceRole.workspace_id == ctx.workspace_id,
                WorkspaceRole.client_id == request.role_id,
            )
        )
        if workspace_role is None:
            raise NotFound("Workspace role not found.")

        # Validate working_section_ids only allowed for WORKER role
        if request.working_section_ids:
            role_name = await ctx.session.scalar(
                select(Role.name).where(Role.client_id == workspace_role.role_id)
            )
            if role_name != RoleNameEnum.WORKER.value:
                raise ValidationError("working_section_ids can only be provided when registering a WORKER.")

        # Email uniqueness (global)
        email_taken = await ctx.session.scalar(
            select(User.client_id).where(User.email == request.email)
        )
        if email_taken is not None:
            raise ConflictError("A user with this email already exists.")

        # Username uniqueness (global)
        username_taken = await ctx.session.scalar(
            select(User.client_id).where(User.username == request.username)
        )
        if username_taken is not None:
            raise ConflictError("Username already taken.")

        hashed_password = bcrypt.hashpw(
            request.password.encode(), bcrypt.gensalt()
        ).decode()

        user = User(
            username=request.username,
            email=request.email,
            password=hashed_password,
            phone_number=request.phone_number,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(user)
        await ctx.session.flush()

        ctx.session.add(
            WorkspaceMembership(
                user_id=user.client_id,
                workspace_id=ctx.workspace_id,
                workspace_role_id=workspace_role.client_id,
                is_active=True,
            )
        )
        await ctx.session.flush()

        if request.working_section_ids:
            section_ids_found = set(
                (
                    await ctx.session.execute(
                        select(WorkingSection.client_id).where(
                            WorkingSection.workspace_id == ctx.workspace_id,
                            WorkingSection.client_id.in_(request.working_section_ids),
                            WorkingSection.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for section_id in request.working_section_ids:
                if section_id not in section_ids_found:
                    raise NotFound(f"Working section '{section_id}' not found.")

            for section_id in request.working_section_ids:
                ctx.session.add(
                    WorkingSectionMembership(
                        workspace_id=ctx.workspace_id,
                        working_section_id=section_id,
                        user_id=user.client_id,
                        assigned_at=datetime.now(timezone.utc),
                        assigned_by_id=ctx.user_id,
                    )
                )
            await ctx.session.flush()

    return {"user": serialize_user_profile(user)}
```

---

### Step 5 — Add route to `auth.py`

**File: `routers/api_v1/auth.py`** (EDIT — append after existing routes)

Add import and body model at the top of the file alongside existing imports:

```python
from beyo_manager.routers.utils.jwt_dep import require_roles   # already imported — verify, do not duplicate
from beyo_manager.routers.utils.roles import ADMIN              # add if not already present
from beyo_manager.services.commands.users.register_user import register_user
```

Add body model (alongside existing `SignInBody`):

```python
class RegisterUserBody(BaseModel):
    username: str
    email: str
    password: str
    phone_number: str | None = None
    role_id: str
    working_section_ids: list[str] = []
```

Add route handler (after existing routes, before any EOF):

```python
@router.post("/register")
async def register_user_route(
    body: RegisterUserBody,
    claims: dict = Depends(require_roles([ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(register_user, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

### Step 6 — Create package `__init__.py` stubs

**Files: `services/commands/users/__init__.py` and `services/commands/users/requests/__init__.py`** (CREATE)

Both files are empty. Required for Python package resolution.

---

## Risks and mitigations

- **Risk**: Duplicate `working_section_ids` entries create multiple rows for the same user+section pair, violating the DB unique constraint.
  **Mitigation**: Duplicate check raises `ValidationError` before the transaction.

- **Risk**: Sections valid at validation time but deleted by another concurrent request before the insert.
  **Mitigation**: Acceptable race — section is soft-deleted after the bulk validation query but the `WorkingSectionMembership` row pointing to it is still valid. The next list query will exclude it naturally.

- **Risk**: `working_section_ids` provided for a non-WORKER role silently succeeds if the role check is skipped.
  **Mitigation**: Role name is resolved inside the transaction (not assumed from the role_id prefix) before any section rows are inserted.

- **Risk**: Hidden plaintext password leakage through logs or debug artifacts.
  **Mitigation**: Hash before persistence; never log request payload fields containing `password`.

- **Risk**: Cross-workspace role probing leaks tenant information.
  **Mitigation**: `WorkspaceRole` is always filtered by `ctx.workspace_id`; mismatch raises generic `NotFound("Workspace role not found.")`.

- **Risk**: `WorkspaceMembership` has a unique constraint `(user_id, workspace_id)`. Re-registering an existing user to the same workspace would hit a DB-level constraint error rather than a clean domain error.
  **Mitigation**: The email uniqueness check on `User` fires first — a duplicate email raises `ConflictError` before the `WorkspaceMembership` insert is ever reached.

---

## Validation plan

- `POST /api/v1/auth/sign-in` with bootstrap admin credentials → obtain bearer token with admin role claims.
- `POST /api/v1/auth/register` (admin token, valid WORKER role_id, no sections) → `200`, returns `{"data": {"user": {...}}}`.
- `POST /api/v1/auth/sign-in` as newly registered user → login succeeds with expected workspace/role claims.
- `POST /api/v1/auth/register` (admin token, valid WORKER role_id, valid `working_section_ids`) → `200`, section memberships exist in DB.
- `POST /api/v1/auth/register` (admin token, non-WORKER role_id, `working_section_ids` non-empty) → `422 ValidationError`.
- `POST /api/v1/auth/register` (admin token, valid WORKER role_id, one invalid section ID) → `404 NotFound`; user does NOT exist in DB (rolled back).
- `POST /api/v1/auth/register` (admin token) with duplicate email → `409 ConflictError`.
- `POST /api/v1/auth/register` (admin token) with duplicate username → `409 ConflictError`.
- `POST /api/v1/auth/register` (admin token) with password shorter than 8 chars → `422 ValidationError`.
- `POST /api/v1/auth/register` (admin token) with role_id from a different workspace → `404 NotFound`.
- `POST /api/v1/auth/register` without token → `401 Unauthorized`.
- `POST /api/v1/auth/register` with non-admin token → `403 Forbidden`.

---

## Review log

- `2026-05-15` `GitHub Copilot`: Initial plan draft. Restructured to match `TEMPLATE_PLAN.md`, aligned paths to real app package layout.
- `2026-05-15` `claude-sonnet-4-6`: Aligned plan with updated `TEMPLATE_PLAN.md` (added File manifest). Resolved all open clarifications. Fixed `ValidationFailed` → `ValidationError` throughout. Moved serializer to `domain/users/serializers.py`. Removed `user_guards.py` (no state-based guard needed). Integrated `working_section_ids` as optional field with atomic single-transaction section assignment, following the same bulk-query pattern used in `assign_user_to_working_sections`. Loaded `07_queries_local.md` in contracts.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `GitHub Copilot (GPT-5.3-Codex)`
