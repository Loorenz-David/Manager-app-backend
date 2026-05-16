# PLAN_register_user_work_profile_20260515

## Metadata

- Plan ID: `PLAN_register_user_work_profile_20260515`
- Status: `under_construction`
- Owner agent: `Claude`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T00:00:00Z`
- Related issue/ticket: —

## Goal and intent

- Goal: On user registration, always create a `UserWorkProfile` row. The incoming request can optionally carry salary fields to populate it; if omitted, the row is still created with all salary fields as `null`.
- Business/user intent: Every registered user must have a work profile record from the moment of creation so the update-profile flow can assume the row exists.
- Non-goals: Updating or listing work profiles (separate future plan). No migration — `user_work_profiles` table exists via migration `7d92a90e6282`.

## Scope

- In scope:
  - Add `salary_per_hour_before_tax` and `salary_per_hour_after_tax` optional fields to the register request and router body.
  - Insert a `UserWorkProfile` row inside the existing `register_user` transaction (always).
  - Include `work_profile` data nested in the `serialize_user_profile` response when a work profile is provided.
- Out of scope: Dedicated work-profile update endpoint, listing work profiles, any migration.
- Assumptions:
  - `user_work_profiles` table is already in the DB (migration `7d92a90e6282` was applied).
  - `UserWorkProfile.created_at` has a server-side default; it is set explicitly in code as per the existing pattern in `register_user.py`.
  - `updated_at` and `updated_by_id` are `null` on creation — no action needed.

## File manifest

List every file touched by this plan. Implementing agents use this table to know what
to open (EDIT) versus what to create from scratch (CREATE). Never search for CREATE files
— they do not exist yet.

### Existing files to edit

| Path (relative to `backend/app/`) | Change summary |
|---|---|
| `beyo_manager/services/commands/users/requests/register_user_request.py` | Add `salary_per_hour_before_tax` and `salary_per_hour_after_tax` optional `Decimal` fields with non-negative validators |
| `beyo_manager/services/commands/users/register_user.py` | Import `UserWorkProfile`; insert work profile row after workspace membership; pass it to serializer |
| `beyo_manager/routers/api_v1/auth.py` | Add `salary_per_hour_before_tax` and `salary_per_hour_after_tax` to `RegisterUserBody` |
| `beyo_manager/domain/users/serializers.py` | Add `serialize_user_work_profile`; extend `serialize_user_profile` to accept optional `work_profile` param |
| `beyo_manager/services/commands/bootstrap/phases/seed_admin_user.py` | Import `UserWorkProfile` and `UserLifetimeStats`; create both rows for the admin user; assign `admin_user` variable in both branches so `username` is available for the snapshot |

### New files to create

None.

## Clarifications required

None — all decisions are resolved below.

## Acceptance criteria

1. `POST /api/v1/auth/register` with no salary fields creates a `UserWorkProfile` row with both salary columns `null`.
2. `POST /api/v1/auth/register` with `salary_per_hour_before_tax: 25.5` creates the row with that value and returns it in `user.work_profile`.
3. Passing a negative salary value returns a `ValidationError` before any DB write.
4. Response shape is `{"user": {..., "work_profile": {"salary_per_hour_before_tax": ..., "salary_per_hour_after_tax": ...}}}`.
5. All existing register scenarios (no salary, with working sections, conflict errors) continue to pass.
6. No `UserWorkProfile` row is left orphaned if the transaction rolls back (atomicity guaranteed by single `async with ctx.session.begin()` block).
7. `POST /api/v1/auth/register` also creates a `UserLifetimeStats` row with `user_display_name_snapshot = user.username`, all aggregate columns at their default `0` values.
8. `seed_admin_user.py` creates `UserWorkProfile` and `UserLifetimeStats` for the bootstrap admin user (idempotent — guards with `select` before inserting).

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: service layer pattern
- `backend/architecture/06_commands.md`: transaction scope, flush rules
- `backend/architecture/09_routers.md`: router body mirrors incoming_data, no business logic
- `backend/architecture/21_naming_conventions.md`: serializer naming
- `backend/architecture/46_serialization.md`: serializer in `domain/<domain>/serializers.py`

### Local extensions loaded

- None applicable.

### Skill selection

- Primary skill: CRUD + realtime goal bundle
- Excluded: worker-driven, replayable async, CI-validated — none triggered

## Implementation plan

### Step 1 — `register_user_request.py`: add salary fields

**File**: `beyo_manager/services/commands/users/requests/register_user_request.py`

Replace the full file content with:

```python
from decimal import Decimal

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.errors.validation import ValidationError


class RegisterUserRequest(BaseModel):
    username: str
    email: str
    password: str
    phone_number: str | None = None
    role_id: str
    working_section_ids: list[str] = []
    salary_per_hour_before_tax: Decimal | None = None
    salary_per_hour_after_tax: Decimal | None = None

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

    @field_validator("salary_per_hour_before_tax", "salary_per_hour_after_tax", mode="before")
    @classmethod
    def salary_must_be_non_negative(cls, v):
        if v is not None and Decimal(str(v)) < 0:
            raise ValueError("Salary values must be non-negative.")
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

### Step 2 — `register_user.py`: insert `UserWorkProfile` and `UserLifetimeStats`

**File**: `beyo_manager/services/commands/users/register_user.py`

Replace the full file content with:

```python
import bcrypt
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.domain.users.validators import validate_password_policy
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
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

    if request.working_section_ids:
        if len(request.working_section_ids) != len(set(request.working_section_ids)):
            raise ValidationError("Duplicate IDs in working_section_ids are not allowed.")

    async with ctx.session.begin():
        workspace_role = await ctx.session.scalar(
            select(WorkspaceRole).where(
                WorkspaceRole.client_id == request.role_id,
                WorkspaceRole.workspace_id == ctx.workspace_id,
            )
        )
        if workspace_role is None:
            raise NotFound("Workspace role not found.")

        if request.working_section_ids:
            role = await ctx.session.scalar(
                select(Role).where(Role.client_id == workspace_role.role_id)
            )
            if role is None or role.name != RoleNameEnum.WORKER.value:
                raise ValidationError("working_section_ids can only be provided when registering a WORKER.")

        existing_email = await ctx.session.scalar(
            select(User.client_id).where(User.email == request.email)
        )
        if existing_email is not None:
            raise ConflictError("A user with this email already exists.")

        existing_username = await ctx.session.scalar(
            select(User.client_id).where(User.username == request.username)
        )
        if existing_username is not None:
            raise ConflictError("Username already taken.")

        hashed_password = bcrypt.hashpw(
            request.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user = User(
            username=request.username,
            email=request.email,
            password=hashed_password,
            phone_number=request.phone_number,
            created_by_id=ctx.user_id,
            online=False,
            created_at=datetime.now(timezone.utc),
        )
        ctx.session.add(user)
        await ctx.session.flush()  # get user.client_id

        now = datetime.now(timezone.utc)

        ctx.session.add(WorkspaceMembership(
            user_id=user.client_id,
            workspace_id=ctx.workspace_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
            joined_at=now,
        ))

        work_profile = UserWorkProfile(
            user_id=user.client_id,
            workspace_id=ctx.workspace_id,
            salary_per_hour_before_tax=request.salary_per_hour_before_tax,
            salary_per_hour_after_tax=request.salary_per_hour_after_tax,
            created_by_id=ctx.user_id,
            created_at=now,
        )
        ctx.session.add(work_profile)

        ctx.session.add(UserLifetimeStats(
            workspace_id=ctx.workspace_id,
            user_id=user.client_id,
            user_display_name_snapshot=user.username,
            created_at=now,
            updated_at=now,
        ))
        await ctx.session.flush()  # persist membership + work_profile + lifetime_stats together

        if request.working_section_ids:
            result = await ctx.session.execute(
                select(WorkingSection.client_id).where(
                    WorkingSection.workspace_id == ctx.workspace_id,
                    WorkingSection.client_id.in_(request.working_section_ids),
                    WorkingSection.is_deleted.is_(False),
                )
            )
            found_ids = {row[0] for row in result.all()}
            for section_id in request.working_section_ids:
                if section_id not in found_ids:
                    raise NotFound(f"Working section '{section_id}' not found.")

            for section_id in request.working_section_ids:
                ctx.session.add(WorkingSectionMembership(
                    workspace_id=ctx.workspace_id,
                    working_section_id=section_id,
                    user_id=user.client_id,
                    assigned_at=now,
                    assigned_by_id=ctx.user_id,
                ))
            await ctx.session.flush()

    return {"user": serialize_user_profile(user, work_profile=work_profile)}
```

> `now` is captured once after the first flush and reused for all subsequent rows — avoids microsecond drift between related timestamps and removes repeated `datetime.now()` calls.

---

### Step 3 — `auth.py`: add salary fields to `RegisterUserBody`

**File**: `beyo_manager/routers/api_v1/auth.py`

Add `from decimal import Decimal` to the imports block (after the stdlib imports).

Replace the `RegisterUserBody` class with:

```python
class RegisterUserBody(BaseModel):
    username: str
    email: str
    password: str
    phone_number: str | None = None
    role_id: str
    working_section_ids: list[str] = []
    salary_per_hour_before_tax: Decimal | None = None
    salary_per_hour_after_tax: Decimal | None = None
```

No other changes to `auth.py`.

---

### Step 4 — `serializers.py`: add work profile serializer, extend `serialize_user_profile`

**File**: `beyo_manager/domain/users/serializers.py`

Replace the full file content with:

```python
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile


def serialize_user_work_profile(uwp: UserWorkProfile) -> dict:
    return {
        "salary_per_hour_before_tax": str(uwp.salary_per_hour_before_tax) if uwp.salary_per_hour_before_tax is not None else None,
        "salary_per_hour_after_tax": str(uwp.salary_per_hour_after_tax) if uwp.salary_per_hour_after_tax is not None else None,
    }


def serialize_user_profile(user: User, work_profile: UserWorkProfile | None = None) -> dict:
    data = {
        "client_id": user.client_id,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "profile_picture": user.profile_picture,
        "languages": user.languages,
        "language_preference": user.language_preference,
        "online": user.online,
        "created_at": user.created_at.isoformat(),
    }
    if work_profile is not None:
        data["work_profile"] = serialize_user_work_profile(work_profile)
    return data
```

> **Note**: The `work_profile` parameter defaults to `None`, so all existing call sites that pass only `user` continue to work without modification.

---

### Step 5 — `seed_admin_user.py`: create `UserWorkProfile` and `UserLifetimeStats` for the bootstrap admin

**File**: `beyo_manager/services/commands/bootstrap/phases/seed_admin_user.py`

Replace the full file content with:

```python
import bcrypt
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def seed_admin_user(
    session: AsyncSession,
    settings: Settings,
    workspace_result: dict[str, str],
) -> dict[str, str]:
    workspace_id = workspace_result["workspace_id"]
    admin_workspace_role_id = workspace_result["admin"]

    existing_user = await session.scalar(
        select(User).where(User.email == settings.bootstrap_admin_email)
    )
    if existing_user is None:
        hashed_password = bcrypt.hashpw(
            settings.bootstrap_admin_password.encode(),
            bcrypt.gensalt(),
        ).decode()
        user = User(
            email=settings.bootstrap_admin_email,
            username=settings.bootstrap_admin_username,
            password=hashed_password,
        )
        session.add(user)
        await session.flush()
        admin_user = user
    else:
        admin_user = existing_user

    user_client_id = admin_user.client_id

    existing_membership = await session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user_client_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    if existing_membership is None:
        session.add(WorkspaceMembership(
            user_id=user_client_id,
            workspace_id=workspace_id,
            workspace_role_id=admin_workspace_role_id,
            is_active=True,
        ))
        await session.flush()

    existing_work_profile = await session.scalar(
        select(UserWorkProfile).where(
            UserWorkProfile.user_id == user_client_id,
            UserWorkProfile.workspace_id == workspace_id,
        )
    )
    if existing_work_profile is None:
        now = datetime.now(timezone.utc)
        session.add(UserWorkProfile(
            user_id=user_client_id,
            workspace_id=workspace_id,
            created_by_id=user_client_id,
            created_at=now,
        ))
        session.add(UserLifetimeStats(
            workspace_id=workspace_id,
            user_id=user_client_id,
            user_display_name_snapshot=admin_user.username,
            created_at=now,
            updated_at=now,
        ))
        await session.flush()

    return {"admin_user_id": user_client_id}
```

Key changes from original:
- `admin_user` is assigned in both branches of the `existing_user` check so `admin_user.username` is available for the snapshot.
- `existing_work_profile` guards both `UserWorkProfile` and `UserLifetimeStats` — they are always created together, so a single guard is sufficient and avoids an extra query.
- Both rows share the same `now` timestamp.

---

## Risks and mitigations

- Risk: `UserWorkProfile` `UniqueConstraint("user_id", "workspace_id")` would raise an `IntegrityError` if called twice for the same user/workspace.
  Mitigation: This is a registration flow; the user does not exist before the call, so this cannot happen in practice. The existing email/username uniqueness checks provide the outer guard.

- Risk: `salary_per_hour_before_tax`/`salary_per_hour_after_tax` serialized as strings could surprise callers expecting numbers.
  Mitigation: `Decimal` values must be serialized as strings to preserve precision (JSON has no decimal type). This is the correct approach for financial data.

## Validation plan

- `alembic upgrade head` — confirms `user_work_profiles` and `user_lifetime_stats` tables are present.
- `POST /api/v1/auth/register` with no salary fields → `user.work_profile.salary_per_hour_before_tax` is `null`, both `user_work_profiles` and `user_lifetime_stats` rows exist in DB.
- `POST /api/v1/auth/register` with `salary_per_hour_before_tax: 25.5` → response contains `"salary_per_hour_before_tax": "25.5000"`.
- `POST /api/v1/auth/register` with `salary_per_hour_before_tax: -1` → `ValidationError` before DB write, no rows created.
- `user_lifetime_stats` row has `user_display_name_snapshot` equal to the registered `username` and all aggregate columns at `0`.
- Bootstrap seed run → `user_work_profiles` and `user_lifetime_stats` rows exist for the admin user; re-running seed is idempotent (no duplicate rows, no error).
- All 10 scenarios from `SUMMARY_register_user_router_20260515.md` still pass.

## Review log

_Empty — awaiting implementation._

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: David
