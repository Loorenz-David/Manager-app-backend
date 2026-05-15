# PLAN_bootstrap_and_roles_20260515

## Metadata

- Plan ID: `PLAN_bootstrap_and_roles_20260515`
- Status: `archived`
- Owner agent: `GitHub Copilot`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T00:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_bootstrap_and_roles_20260515.md`

## Goal and intent

- Goal: Implement an idempotent bootstrap endpoint that seeds roles, workspace, admin user, item categories, issue types, issue severities, working sections, and issue category configs so the app is fully usable immediately after `alembic upgrade head`.
- Business/user intent: A fresh deployment must be sign-in-ready without manual DB intervention. The phase-per-file structure makes it trivially safe to extend as the app grows.
- Non-goals: Permission atoms, user management endpoints, multi-workspace provisioning, CI automation.

## Scope

- In scope: 13 new files + 1 new Alembic migration + 5 edits to existing files.
- Out of scope: Any JWT or auth flow changes.
- Assumptions:
  - `alembic upgrade head` has already been run before the bootstrap endpoint is called.
  - `bcrypt` is already installed (used in `sign_in_user.py`).
  - The `Workspace` model has `name` (String) and `time_zone` (String) fields. `created_by_id` is nullable.
  - `WorkspaceRole.is_system` (Boolean) distinguishes seeded system roles from user-created roles.
  - `WorkspaceMembership.is_active` defaults to `True`.
  - `run_service` in `services/run_service.py` does not require JWT claims — it only calls `fn(ctx)`.
  - `ServiceContext` with `identity={}` is valid for the bootstrap (no JWT present; `ctx.user_id` and `ctx.workspace_id` return `""`, which is intentional for a setup command).

## Clarifications required

All items below are **resolved decisions**. Copilot must follow them exactly — do not reinterpret or find alternatives.

- [x] **Bootstrap trigger**: `POST /api/v1/bootstrap` — one route only. No `GET`, `PATCH`, or other methods on this router.

- [x] **Bootstrap security**: The route checks the `X-Bootstrap-Secret` HTTP header against `settings.bootstrap_secret`. If the header is missing, empty, or does not match the setting value, return HTTP `403` immediately with no DB interaction. Use `raise HTTPException(status_code=403, detail="Invalid or missing bootstrap secret.")` — do NOT use `build_err` or `run_service` for this check; it must fire before the command runs.

- [x] **No `require_roles` on the bootstrap route**: This endpoint has no JWT. Do not import or call `require_roles`. The only auth mechanism is the `X-Bootstrap-Secret` header check.

- [x] **`ServiceContext` with empty identity**: The bootstrap router builds `ServiceContext(incoming_data={}, identity={}, session=session)`. The command reads credentials from `settings` directly, not from `ctx.incoming_data` or `ctx.identity`.

- [x] **Settings fields to add to `config.py`**: Six new fields on the `Settings` class:
  - `bootstrap_secret: str | None = Field(default=None, alias="BOOTSTRAP_SECRET")`
  - `bootstrap_admin_email: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_EMAIL")`
  - `bootstrap_admin_username: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_USERNAME")`
  - `bootstrap_admin_password: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_PASSWORD")`
  - `bootstrap_workspace_name: str = Field(default="My Workspace", alias="BOOTSTRAP_WORKSPACE_NAME")`
  - `bootstrap_workspace_timezone: str = Field(default="UTC", alias="BOOTSTRAP_WORKSPACE_TIMEZONE")`
  These fields must NOT be added to `_require_critical_settings` — they are optional at startup; only the bootstrap command validates them at call time.

- [x] **Env var names in `.env.example`**: Add six lines to `.env.example`:
  `BOOTSTRAP_SECRET`, `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_USERNAME`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_WORKSPACE_NAME`, `BOOTSTRAP_WORKSPACE_TIMEZONE`. All six should be present with placeholder values. `BOOTSTRAP_SECRET` must have a prominent `# Required to call POST /api/v1/bootstrap` comment.

- [x] **New `RoleNameEnum` values**: `{ADMIN, WORKER, MANAGER, SELLER}` only. Remove `MEMBER` and `FIELD`. Update `domain/roles/enums.py` as the first code change. All other changes flow from this file.

- [x] **`routers/utils/roles.py` update**: Replace with `ADMIN = "admin"`, `WORKER = "worker"`, `MANAGER = "manager"`, `SELLER = "seller"`. Delete `MEMBER` and `FIELD` lines. No other changes to this file.

- [x] **Alembic migration for `role_name_enum`**: Postgres cannot remove enum values without recreating the type. The migration must run in strict child→parent order to avoid FK violations:
  1. Delete `workspace_memberships` rows that reference workspace_roles linked to the removed role values — **run first** (it is the deepest child).
  2. Delete `workspace_roles` rows linked to roles where `name IN ('member', 'field')` — run second.
  3. Delete `roles` rows where `name IN ('member', 'field')` — run third.
  4. Create new enum: `CREATE TYPE role_name_enum_new AS ENUM ('admin', 'worker', 'manager', 'seller')`.
  5. Alter column: `ALTER TABLE roles ALTER COLUMN name TYPE role_name_enum_new USING name::text::role_name_enum_new`.
  6. Drop old type and rename: `DROP TYPE role_name_enum; ALTER TYPE role_name_enum_new RENAME TO role_name_enum`.
  The `downgrade()` function must reverse the enum change (same child→parent DELETE order, but for 'worker'/'manager'/'seller'). It does NOT restore deleted data rows.
  **Note**: After autogenerating the migration, Copilot must manually replace or augment the auto-generated body with the SQL in Step 5 — Alembic autogenerate cannot detect enum value removal. The Step 5 code block is authoritative.

- [x] **Idempotency contract per phase**: Each phase function checks for existence before inserting. If the data already exists, return its `client_id` without modifying it. An empty `try/except` or `ON CONFLICT DO NOTHING` pattern is NOT used — always SELECT first, INSERT only if not found. Raise no error if the row exists.

- [x] **Phase execution order and data passing**: All nine phases run inside a **single** `async with ctx.session.begin()` block in `bootstrap_app.py`. Do not open per-phase transactions.
  1. `seed_roles(session)` → returns `dict[str, str]` of `{role_name_value: role_client_id}`, e.g. `{"admin": "role_...", "worker": "role_...", ...}`.
  2. `seed_workspace(session, settings, role_ids)` → creates the workspace AND four `WorkspaceRole` rows (one per role, `is_system=True`). Returns `dict` with `workspace_id` and workspace_role ids keyed by role name, e.g. `{"workspace_id": "ws_...", "admin": "wsr_...", "worker": "wsr_...", ...}`.
  3. `seed_item_categories(session, workspace_id)` → returns `dict[str, str]` mapping category name → `client_id` (34 rows).
  4. `seed_issue_types(session, workspace_id)` → returns `dict[str, str]` mapping issue type name → `client_id` (9 rows).
  5. `seed_issue_severities(session, workspace_id)` → returns `dict[str, str]` (3 rows; orchestrator discards the return — no downstream phase needs severity IDs).
  6. `seed_working_sections(session, workspace_id)` → returns `dict[str, str]` mapping section name → `client_id` (13 sections + 15 dependency edges).
  7. `seed_issue_category_configs(session, workspace_id, issue_type_ids, item_category_ids, section_ids)` → returns `None` (27 `WorkingSectionSupportedIssueType` + 279 `IssueCategoryConfig` rows: 63 seating + 216 wood).
  8. `seed_working_section_item_categories(session, workspace_id, section_ids, item_category_ids)` → returns `None` (178 rows: cleaning → all 34; wood fix / ground oil / hardwax oil → 27 wood each; 9 other sections → 7 seating each).
  9. `seed_admin_user(session, settings, workspace_result)` → creates the admin `User` (bcrypt-hashed password) and a `WorkspaceMembership` linking the user to the ADMIN `WorkspaceRole`. Returns `{"admin_user_id": "usr_..."}`.
  The Step 10 code block is authoritative for exact call order and argument passing.

- [x] **`seed_workspace` idempotency**: Check for any existing `Workspace` row (`.limit(1)`). If one exists, re-query its associated `WorkspaceRole` rows to rebuild `workspace_role_ids` and return without inserting. The bootstrap targets a single-workspace app — do not create a second workspace.

- [x] **`seed_admin_user` idempotency**: Check for a `User` where `email == settings.bootstrap_admin_email`. If found, re-query their `WorkspaceMembership` to confirm linkage (do not modify it). If the user exists with no active membership, create the membership.

- [x] **WorkspaceRole display names**: Hardcoded system defaults: `"admin"` → `"Admin"`, `"worker"` → `"Worker"`, `"manager"` → `"Manager"`, `"seller"` → `"Seller"`. Do not read from env vars.

- [x] **Password hashing in `seed_admin_user`**: Use `bcrypt.hashpw(settings.bootstrap_admin_password.encode(), bcrypt.gensalt()).decode()`. Import `bcrypt` at the top of `seed_admin_user.py`. Do not import or use any other hashing library.

- [x] **Bootstrap command return shape**:
  ```python
  return {
      "workspace_id": workspace_result["workspace_id"],
      "admin_user_id": user_result["admin_user_id"],
      "roles_seeded": list(role_ids.keys()),
  }
  ```
  Wrapped by `build_ok` in the router: `{"data": {...}, "warnings": []}`.

- [x] **`bootstrap_app.py` env var validation**: Before opening the transaction, check that `settings.bootstrap_admin_email`, `settings.bootstrap_admin_username`, and `settings.bootstrap_admin_password` are all non-None and non-empty. If any is missing, raise `ValidationError("Bootstrap admin credentials are not configured in environment variables.")`. Import: `from beyo_manager.errors.validation import ValidationError`. **Do NOT use `ValidationFailed`** — that class does not exist in the codebase. The correct class is `ValidationError` (http_status=422, defined in `beyo_manager/errors/validation.py`).

- [x] **No events dispatched from bootstrap**: The bootstrap command does not call `dispatch`. Seeding is a setup operation, not a domain command — workspace events do not apply here.

- [x] **Router URL**: Register at `/api/v1/bootstrap` (kebab-case). Tag: `"bootstrap"`.

- [x] **`__init__.py` stubs**: Two empty stubs — `services/commands/bootstrap/__init__.py` (content: `# bootstrap package`) and `services/commands/bootstrap/phases/__init__.py` (content: `# bootstrap phases`).

## Acceptance criteria

1. `POST /api/v1/bootstrap` with correct `X-Bootstrap-Secret` on an empty DB returns `200` with `{data: {workspace_id, admin_user_id, roles_seeded: [...]}, warnings: []}`.
2. Re-running the same call returns `200` with identical `workspace_id` and `admin_user_id` — no duplicates in DB.
3. `POST /api/v1/auth/sign-in` with `BOOTSTRAP_ADMIN_EMAIL` + `BOOTSTRAP_ADMIN_PASSWORD` returns a valid JWT after bootstrap.
4. `POST /api/v1/bootstrap` with wrong or missing `X-Bootstrap-Secret` returns `403`.
5. `POST /api/v1/bootstrap` when `BOOTSTRAP_ADMIN_EMAIL` is unset in env returns `422 ValidationError`.
6. After migration, `SELECT unnest(enum_range(NULL::role_name_enum))` returns `{admin, worker, manager, seller}` only.
7. `domain/roles/enums.py` contains only `ADMIN`, `WORKER`, `MANAGER`, `SELLER`. No reference to `MEMBER` or `FIELD` anywhere in application code.
8. `routers/utils/roles.py` contains only `ADMIN`, `WORKER`, `MANAGER`, `SELLER` constants.
9. After bootstrap, `item_categories` table contains exactly 34 rows in the workspace: 7 with `major_category = 'seat'` and 27 with `major_category = 'wood'`.
10. After bootstrap, `issue_types` table has 9 rows (all `source = 'internal_inspection'`), `issue_severities` has 3 rows (low/medium/high), `working_sections` has 13 rows with `image = NULL`, and `working_section_dependencies` has 15 rows matching the dependency graph. `"wood fix"` has zero dependency rows; `"ground oil"` and `"hardwax oil"` each have one (→ wood fix).
11. After bootstrap, `working_section_supported_issue_types` has 27 rows and `issue_category_configs` has 279 rows (63 seating: 9 types × 7 categories; 216 wood: 8 types × 27 categories; all `base_time_seconds = 600`, `effective_from = NULL`). `"ground oil"` and `"hardwax oil"` have zero rows in `working_section_supported_issue_types`. Re-running bootstrap leaves all row counts unchanged.
12. After bootstrap, `working_section_item_categories` has 178 rows: `cleaning` → 34 categories; `wood fix`, `ground oil`, `hardwax oil` → 27 wood categories each; every other section → 7 seating categories.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: Layer boundaries — business logic in commands, not routers.
- `backend/architecture/04_context.md`: `ServiceContext` — `ctx.session` is the only field used by bootstrap; `identity={}` is intentional.
- `backend/architecture/05_errors.md`: `ValidationFailed` for missing env vars; `HTTPException(403)` (FastAPI, not domain error) for missing secret header.
- `backend/architecture/06_commands.md`: Command structure — `async with ctx.session.begin()` wraps all phase calls; return type is `dict`.
- `backend/architecture/09_routers.md`: Router skeleton — `run_service`, `build_ok`, `build_err`. Exception: the `X-Bootstrap-Secret` guard uses `HTTPException` directly before `run_service` is called.
- `backend/architecture/30_migrations.md`: Enum migration pattern — autogenerate then manually fix the body for enum value removal; downgrade logs steps only.
- `backend/architecture/21_naming_conventions.md`: File and function naming.
- `backend/architecture/40_identity.md`: `IdentityMixin` — all models use `client_id` as PK, auto-assigned on flush.

### Local extensions loaded

- `backend/architecture/40_identity_local.md`: Prefix registry. No new prefixes needed — `Role` = `role`, `Workspace` = `ws`, `WorkspaceRole` = `wsr`, `WorkspaceMembership` = `wsm`, `User` = `usr`.
- No local extensions found for 01, 04, 05, 06, 09, 21, 30.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read contracts (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (field names, import paths, model columns)

Permitted relational reads for this plan:
- `beyo_manager/models/tables/roles/role.py` — column names
- `beyo_manager/models/tables/roles/workspace_role.py` — column names, especially `is_system`
- `beyo_manager/models/tables/workspaces/workspace.py` — column names
- `beyo_manager/models/tables/workspaces/workspace_membership.py` — column names, `is_active`
- `beyo_manager/models/tables/users/user.py` — column names (`email`, `username`, `password`)
- `beyo_manager/models/tables/items/item_category.py` — column names, `major_category` type
- `beyo_manager/models/tables/issue_types/issue_type.py` — column names, `source` type
- `beyo_manager/models/tables/issue_types/issue_severity.py` — column names, `time_multiplier` type (Numeric/Decimal)
- `beyo_manager/models/tables/issue_types/issue_category_config.py` — column names, `effective_from` nullable, no `working_section_id`
- `beyo_manager/models/tables/working_sections/working_section.py` — column names, `image` nullable
- `beyo_manager/models/tables/working_sections/working_section_dependency.py` — column names (`dependent_section_id`, `prerequisite_section_id`)
- `beyo_manager/models/tables/working_sections/working_section_supported_issue_type.py` — column names
- `beyo_manager/models/tables/working_sections/working_section_item_category.py` — column names (`working_section_id`, `item_category_id`); no `major_category` column — section/category link is direct
- `beyo_manager/domain/items/enums.py` — `ItemMajorCategoryEnum.SEAT = "seat"`, `ItemMajorCategoryEnum.WOOD = "wood"` (not "seating")
- `beyo_manager/domain/issue_types/enums.py` — `IssueSourceEnum.INTERNAL_INSPECTION` for admin-seeded issue types
- `beyo_manager/config.py` — to know where to add the new settings fields
- `beyo_manager/routers/api_v1/__init__.py` — to know where to add the router

### Skill selection

- Primary skill: `backend/task_system/backend_contract_goal_mapping_guide.md` (CRUD + document-only protocol).
- Goal bundle used: Core contracts only (no CRUD bundle — this is a setup/infra command, not a domain CRUD endpoint).
- Excluded: infra events (42), sockets (13), background jobs (16), testing (15) — not in scope.

---

## Implementation plan

All paths are relative to `backend/app/beyo_manager/` unless noted otherwise.

---

### Step 1 — Update `RoleNameEnum`

**File: `domain/roles/enums.py`** (EDIT)

Replace the entire file content:

```python
from enum import StrEnum


class RoleNameEnum(StrEnum):
    ADMIN = "admin"
    WORKER = "worker"
    MANAGER = "manager"
    SELLER = "seller"
```

---

### Step 2 — Update router role constants

**File: `routers/utils/roles.py`** (EDIT)

Replace the entire file content:

```python
ADMIN   = "admin"
WORKER  = "worker"
MANAGER = "manager"
SELLER  = "seller"
```

---

### Step 3 — Add bootstrap settings to `config.py`

**File: `config.py`** (EDIT)

Add these six fields to the `Settings` class body, after the `sleep_mode_enabled` block and before `model_config`:

```python
    # Bootstrap
    bootstrap_secret: str | None = Field(default=None, alias="BOOTSTRAP_SECRET")
    bootstrap_admin_email: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_username: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_password: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_PASSWORD")
    bootstrap_workspace_name: str = Field(default="My Workspace", alias="BOOTSTRAP_WORKSPACE_NAME")
    bootstrap_workspace_timezone: str = Field(default="UTC", alias="BOOTSTRAP_WORKSPACE_TIMEZONE")
```

Do NOT add these to `_require_critical_settings`. They are optional at startup — the bootstrap command validates them at call time.

---

### Step 4 — Update `.env.example`

**File: `backend/app/.env.example`** (EDIT)

Append a new block at the end of the file:

```
# Bootstrap — POST /api/v1/bootstrap
# Required to call POST /api/v1/bootstrap. Keep this secret and rotate after first use.
BOOTSTRAP_SECRET=replace-me
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=replace-me
BOOTSTRAP_WORKSPACE_NAME=My Workspace
BOOTSTRAP_WORKSPACE_TIMEZONE=UTC
```

---

### Step 5 — Write Alembic migration for `role_name_enum`

**Action: Generate then manually fix.**

1. First, make the model change in Step 1 so autogenerate sees the delta.
2. Run: `alembic revision --autogenerate -m "update_role_name_enum_worker_manager_seller"`
3. Open the generated file in `migrations/versions/` and **replace the auto-generated `upgrade()` and `downgrade()` bodies** with the following (keep the file header, revision ID, down_revision unchanged):

```python
def upgrade() -> None:
    # Step 1: Cascade-clean rows that reference the removed enum values.
    # Order: memberships → workspace_roles → roles (child → parent).
    op.execute("""
        DELETE FROM workspace_memberships
        WHERE workspace_role_id IN (
            SELECT wsr.client_id
            FROM workspace_roles wsr
            JOIN roles r ON wsr.role_id = r.client_id
            WHERE r.name IN ('member', 'field')
        )
    """)
    op.execute("""
        DELETE FROM workspace_roles
        WHERE role_id IN (
            SELECT client_id FROM roles WHERE name IN ('member', 'field')
        )
    """)
    op.execute("DELETE FROM roles WHERE name IN ('member', 'field')")

    # Step 2: Recreate the enum type with the new value set.
    op.execute("CREATE TYPE role_name_enum_new AS ENUM ('admin', 'worker', 'manager', 'seller')")
    op.execute("""
        ALTER TABLE roles
        ALTER COLUMN name TYPE role_name_enum_new
        USING name::text::role_name_enum_new
    """)
    op.execute("DROP TYPE role_name_enum")
    op.execute("ALTER TYPE role_name_enum_new RENAME TO role_name_enum")


def downgrade() -> None:
    # Step 1: Cascade-clean rows that reference the new enum values before reverting.
    # Same child→parent order as upgrade() but for worker/manager/seller.
    op.execute("""
        DELETE FROM workspace_memberships
        WHERE workspace_role_id IN (
            SELECT wsr.client_id
            FROM workspace_roles wsr
            JOIN roles r ON wsr.role_id = r.client_id
            WHERE r.name IN ('worker', 'manager', 'seller')
        )
    """)
    op.execute("""
        DELETE FROM workspace_roles
        WHERE role_id IN (
            SELECT client_id FROM roles WHERE name IN ('worker', 'manager', 'seller')
        )
    """)
    op.execute("DELETE FROM roles WHERE name IN ('worker', 'manager', 'seller')")

    # Step 2: Recreate the original enum type.
    # Note: admin rows survive; member/field rows are not restored.
    op.execute("CREATE TYPE role_name_enum_old AS ENUM ('admin', 'member', 'field')")
    op.execute("""
        ALTER TABLE roles
        ALTER COLUMN name TYPE role_name_enum_old
        USING name::text::role_name_enum_old
    """)
    op.execute("DROP TYPE role_name_enum")
    op.execute("ALTER TYPE role_name_enum_old RENAME TO role_name_enum")
```

**Important**: The `USING name::text::role_name_enum_new` cast will fail if any existing row has a value not present in the new enum (e.g., `'worker'` in the old enum). The DELETE statements in Step 1 eliminate all such rows before the cast runs. Order is critical.

---

### Step 6 — Create bootstrap package `__init__.py` stubs

**Files** (CREATE — two new files):

- `services/commands/bootstrap/__init__.py` — content: `# bootstrap package`
- `services/commands/bootstrap/phases/__init__.py` — content: `# bootstrap phases`

---

### Step 7 — Create phase: `seed_roles.py`

**File: `services/commands/bootstrap/phases/seed_roles.py`** (CREATE)

Returns a `dict[str, str]` mapping role name values to `client_id`s. Idempotent: selects before inserting.

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.roles.role import Role


async def seed_roles(session: AsyncSession) -> dict[str, str]:
    role_ids: dict[str, str] = {}
    for role_name in [
        RoleNameEnum.ADMIN,
        RoleNameEnum.WORKER,
        RoleNameEnum.MANAGER,
        RoleNameEnum.SELLER,
    ]:
        existing = await session.scalar(
            select(Role).where(Role.name == role_name)
        )
        if existing is None:
            role = Role(name=role_name)
            session.add(role)
            await session.flush()
            role_ids[role_name.value] = role.client_id
        else:
            role_ids[role_name.value] = existing.client_id
    return role_ids
```

---

### Step 8 — Create phase: `seed_workspace.py`

**File: `services/commands/bootstrap/phases/seed_workspace.py`** (CREATE)

Creates the workspace and all four `WorkspaceRole` rows (one per role). Idempotent: if a workspace exists, re-reads its roles and returns without inserting.

`WorkspaceRole` display names: `"Admin"`, `"Worker"`, `"Manager"`, `"Seller"`.

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace import Workspace

_DISPLAY_NAMES: dict[str, str] = {
    "admin": "Admin",
    "worker": "Worker",
    "manager": "Manager",
    "seller": "Seller",
}


async def seed_workspace(
    session: AsyncSession,
    settings: Settings,
    role_ids: dict[str, str],
) -> dict[str, str]:
    # Check for existing workspace
    existing_workspace = await session.scalar(select(Workspace).limit(1))

    if existing_workspace is not None:
        workspace_id = existing_workspace.client_id
        # Re-read existing workspace roles to rebuild the return map
        workspace_role_rows = (
            await session.execute(
                select(WorkspaceRole).where(WorkspaceRole.workspace_id == workspace_id)
            )
        ).scalars().all()
        result: dict[str, str] = {"workspace_id": workspace_id}
        for wsr in workspace_role_rows:
            for role_name_value, role_client_id in role_ids.items():
                if wsr.role_id == role_client_id:
                    result[role_name_value] = wsr.client_id
        # Create any missing workspace roles (handles partial-seed recovery).
        # Without this, seed_admin_user crashes with KeyError if a prior run was interrupted.
        for role_name_value, role_client_id in role_ids.items():
            if role_name_value not in result:
                wsr = WorkspaceRole(
                    workspace_id=workspace_id,
                    role_id=role_client_id,
                    name=_DISPLAY_NAMES[role_name_value],
                    is_system=True,
                )
                session.add(wsr)
                await session.flush()
                result[role_name_value] = wsr.client_id
        return result

    # Create workspace
    workspace = Workspace(
        name=settings.bootstrap_workspace_name,
        time_zone=settings.bootstrap_workspace_timezone,
    )
    session.add(workspace)
    await session.flush()

    result = {"workspace_id": workspace.client_id}

    # Create one WorkspaceRole per role
    for role_name_value, role_client_id in role_ids.items():
        wsr = WorkspaceRole(
            workspace_id=workspace.client_id,
            role_id=role_client_id,
            name=_DISPLAY_NAMES[role_name_value],
            is_system=True,
        )
        session.add(wsr)
        await session.flush()
        result[role_name_value] = wsr.client_id

    return result
```

---

### Step 9 — Create phase: `seed_admin_user.py`

**File: `services/commands/bootstrap/phases/seed_admin_user.py`** (CREATE)

Creates the admin `User` and a `WorkspaceMembership` linking them to the ADMIN `WorkspaceRole`. Idempotent: if the user already exists and has an active membership, returns without inserting.

```python
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def seed_admin_user(
    session: AsyncSession,
    settings: Settings,
    workspace_result: dict[str, str],
) -> dict[str, str]:
    workspace_id = workspace_result["workspace_id"]
    admin_workspace_role_id = workspace_result["admin"]

    # Check for existing admin user
    existing_user = await session.scalar(
        select(User).where(User.email == settings.bootstrap_admin_email)
    )

    if existing_user is None:
        hashed = bcrypt.hashpw(
            settings.bootstrap_admin_password.encode(), bcrypt.gensalt()
        ).decode()
        user = User(
            email=settings.bootstrap_admin_email,
            username=settings.bootstrap_admin_username,
            password=hashed,
        )
        session.add(user)
        await session.flush()
        user_client_id = user.client_id
    else:
        user_client_id = existing_user.client_id

    # Ensure workspace membership exists
    existing_membership = await session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user_client_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    if existing_membership is None:
        membership = WorkspaceMembership(
            user_id=user_client_id,
            workspace_id=workspace_id,
            workspace_role_id=admin_workspace_role_id,
        )
        session.add(membership)
        await session.flush()

    return {"admin_user_id": user_client_id}
```

---

### Step 10 — Create bootstrap orchestrator command

**File: `services/commands/bootstrap/bootstrap_app.py`** (CREATE)

Validates env vars, opens a single transaction, runs all nine phases in order.

Phase execution order:
1. `seed_roles` — no dependencies
2. `seed_workspace` — needs `role_ids`
3. `seed_item_categories` — needs `workspace_id`
4. `seed_issue_types` — needs `workspace_id`
5. `seed_issue_severities` — needs `workspace_id`
6. `seed_working_sections` — needs `workspace_id`
7. `seed_issue_category_configs` — needs `workspace_id`, `issue_type_ids`, `item_category_ids`, `section_ids`
8. `seed_working_section_item_categories` — needs `workspace_id`, `section_ids`, `item_category_ids`
9. `seed_admin_user` — needs `workspace_result`

```python
from beyo_manager.config import settings
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.bootstrap.phases.seed_admin_user import seed_admin_user
from beyo_manager.services.commands.bootstrap.phases.seed_issue_category_configs import seed_issue_category_configs
from beyo_manager.services.commands.bootstrap.phases.seed_issue_severities import seed_issue_severities
from beyo_manager.services.commands.bootstrap.phases.seed_issue_types import seed_issue_types
from beyo_manager.services.commands.bootstrap.phases.seed_item_categories import seed_item_categories
from beyo_manager.services.commands.bootstrap.phases.seed_roles import seed_roles
from beyo_manager.services.commands.bootstrap.phases.seed_working_section_item_categories import seed_working_section_item_categories
from beyo_manager.services.commands.bootstrap.phases.seed_working_sections import seed_working_sections
from beyo_manager.services.commands.bootstrap.phases.seed_workspace import seed_workspace
from beyo_manager.services.context import ServiceContext


async def bootstrap_app(ctx: ServiceContext) -> dict:
    if not (settings.bootstrap_admin_email and settings.bootstrap_admin_username and settings.bootstrap_admin_password):
        raise ValidationError(
            "Bootstrap admin credentials are not configured in environment variables."
        )

    async with ctx.session.begin():
        role_ids = await seed_roles(ctx.session)
        workspace_result = await seed_workspace(ctx.session, settings, role_ids)
        workspace_id = workspace_result["workspace_id"]
        item_category_ids = await seed_item_categories(ctx.session, workspace_id)
        issue_type_ids = await seed_issue_types(ctx.session, workspace_id)
        await seed_issue_severities(ctx.session, workspace_id)
        section_ids = await seed_working_sections(ctx.session, workspace_id)
        await seed_issue_category_configs(
            ctx.session, workspace_id, issue_type_ids, item_category_ids, section_ids
        )
        await seed_working_section_item_categories(
            ctx.session, workspace_id, section_ids, item_category_ids
        )
        user_result = await seed_admin_user(ctx.session, settings, workspace_result)

    return {
        "workspace_id": workspace_result["workspace_id"],
        "admin_user_id": user_result["admin_user_id"],
        "roles_seeded": list(role_ids.keys()),
    }
```

---

### Step 11 — Create bootstrap router

**File: `routers/api_v1/bootstrap.py`** (CREATE)

Single route: `POST ""`. The `X-Bootstrap-Secret` guard fires before `run_service`.

```python
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.services.commands.bootstrap.bootstrap_app import bootstrap_app
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.post("")
async def bootstrap_route(
    x_bootstrap_secret: str | None = Header(default=None, alias="X-Bootstrap-Secret"),
    session: AsyncSession = Depends(get_db),
):
    if not settings.bootstrap_secret or x_bootstrap_secret != settings.bootstrap_secret:
        raise HTTPException(status_code=403, detail="Invalid or missing bootstrap secret.")

    ctx = ServiceContext(
        incoming_data={},
        identity={},
        session=session,
    )
    outcome = await run_service(bootstrap_app, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

---

### Step 12 — Register bootstrap router in `__init__.py`

**File: `routers/api_v1/__init__.py`** (EDIT — add two lines)

Add to the imports at the top:
```python
from beyo_manager.routers.api_v1 import bootstrap
```

Add to `register_v1_routers`:
```python
app.include_router(bootstrap.router, prefix="/api/v1/bootstrap", tags=["bootstrap"])
```

---

### Step 13 — Create phase: `seed_item_categories.py`

**File: `services/commands/bootstrap/phases/seed_item_categories.py`** (CREATE)

Seeds 34 item categories: 7 seating (`ItemMajorCategoryEnum.SEAT`) and 27 wood (`ItemMajorCategoryEnum.WOOD`). Idempotent: SELECT by `(workspace_id, name)` before INSERT. Returns `dict[str, str]` mapping category name → `client_id`.

**Important**: `ItemMajorCategoryEnum.SEAT = "seat"` (not `"seating"` — the enum value in the database is `"seat"`).

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.models.tables.items.item_category import ItemCategory

_SEATING_CATEGORIES = [
    "armchair", "bench", "chair", "chairs", "dining chair", "sofa", "stool",
]

_WOOD_CATEGORIES = [
    "bar cabinet", "bedside table", "bookshelf", "cabinet", "chest of drawer",
    "chest of drawers", "coffee table", "conference table", "corner cabinet",
    "dining table", "hall table", "highboard", "lamp", "mirror", "nest of tables",
    "plant stand", "poster", "round table", "secretary", "serving trolley",
    "side table", "sideboard", "small table", "shelving", "sewing table",
    "trolley", "writing desk",
]


async def seed_item_categories(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    category_ids: dict[str, str] = {}
    pairs = [
        (name, ItemMajorCategoryEnum.SEAT) for name in _SEATING_CATEGORIES
    ] + [
        (name, ItemMajorCategoryEnum.WOOD) for name in _WOOD_CATEGORIES
    ]
    for name, major_category in pairs:
        existing = await session.scalar(
            select(ItemCategory).where(
                ItemCategory.workspace_id == workspace_id,
                ItemCategory.name == name,
            )
        )
        if existing is None:
            cat = ItemCategory(
                workspace_id=workspace_id,
                name=name,
                major_category=major_category,
            )
            session.add(cat)
            await session.flush()
            category_ids[name] = cat.client_id
        else:
            category_ids[name] = existing.client_id
    return category_ids
```

---

### Step 14 — Create phase: `seed_issue_types.py`

**File: `services/commands/bootstrap/phases/seed_issue_types.py`** (CREATE)

Seeds 9 issue types. All use `IssueSourceEnum.INTERNAL_INSPECTION` — this value represents issue types created by admin (as opposed to issue instances reported by workers or customers). Idempotent: SELECT by `(workspace_id, name)` before INSERT. Returns `dict[str, str]` mapping issue type name → `client_id`.

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.issue_types.enums import IssueSourceEnum
from beyo_manager.models.tables.issue_types.issue_type import IssueType

_ISSUE_TYPES = [
    "scratches",
    "dents",
    "broken parts",
    "stains",
    "structural damage",
    "finish damage",
    "assembly issues",
    "loose joints",
    "upholstery damage",
]


async def seed_issue_types(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    issue_type_ids: dict[str, str] = {}
    for name in _ISSUE_TYPES:
        existing = await session.scalar(
            select(IssueType).where(
                IssueType.workspace_id == workspace_id,
                IssueType.name == name,
            )
        )
        if existing is None:
            issue_type = IssueType(
                workspace_id=workspace_id,
                name=name,
                source=IssueSourceEnum.INTERNAL_INSPECTION,
            )
            session.add(issue_type)
            await session.flush()
            issue_type_ids[name] = issue_type.client_id
        else:
            issue_type_ids[name] = existing.client_id
    return issue_type_ids
```

---

### Step 15 — Create phase: `seed_issue_severities.py`

**File: `services/commands/bootstrap/phases/seed_issue_severities.py`** (CREATE)

Seeds 3 issue severities. `time_multiplier` is `Mapped[Decimal]` / `Numeric(8,4)` — use `Decimal` literals, not floats. Idempotent: SELECT by `(workspace_id, name)` before INSERT. Returns `dict[str, str]` mapping severity name → `client_id`.

```python
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.issue_types.issue_severity import IssueSeverity

_SEVERITIES: list[tuple[str, Decimal]] = [
    ("low", Decimal("1.1")),
    ("medium", Decimal("1.5")),
    ("high", Decimal("2.0")),
]


async def seed_issue_severities(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    severity_ids: dict[str, str] = {}
    for name, multiplier in _SEVERITIES:
        existing = await session.scalar(
            select(IssueSeverity).where(
                IssueSeverity.workspace_id == workspace_id,
                IssueSeverity.name == name,
            )
        )
        if existing is None:
            severity = IssueSeverity(
                workspace_id=workspace_id,
                name=name,
                time_multiplier=multiplier,
            )
            session.add(severity)
            await session.flush()
            severity_ids[name] = severity.client_id
        else:
            severity_ids[name] = existing.client_id
    return severity_ids
```

---

### Step 16 — Create phase: `seed_working_sections.py`

**File: `services/commands/bootstrap/phases/seed_working_sections.py`** (CREATE)

Seeds 13 working sections (`image=None`) and 15 dependency edges. Idempotent: SELECT by `(workspace_id, name)` for sections; SELECT by `(workspace_id, dependent_section_id, prerequisite_section_id)` for edges. Returns `dict[str, str]` mapping section name → `client_id`.

`"wood fix"` has no dependencies. `"ground oil"` and `"hardwax oil"` each depend on `"wood fix"`.

**Dependency graph** (dependent → prerequisite):
- cleaning → disassembly
- structural repair → disassembly
- sanding → structural repair
- upholstery removal → disassembly
- padding → upholstery removal
- upholstery installation → padding
- upholstery installation → upholstery removal
- assembly → upholstery installation
- assembly → structural repair
- assembly → sanding
- sewing → disassembly
- sewing → upholstery removal
- weaving → sewing
- ground oil → wood fix
- hardwax oil → wood fix

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency

_SECTIONS = [
    "disassembly",
    "cleaning",
    "structural repair",
    "sanding",
    "upholstery removal",
    "padding",
    "upholstery installation",
    "assembly",
    "sewing",
    "weaving",
    "wood fix",
    "ground oil",
    "hardwax oil",
]

# Each tuple: (dependent_section_name, prerequisite_section_name)
_DEPENDENCIES: list[tuple[str, str]] = [
    ("cleaning", "disassembly"),
    ("structural repair", "disassembly"),
    ("sanding", "structural repair"),
    ("upholstery removal", "disassembly"),
    ("padding", "upholstery removal"),
    ("upholstery installation", "padding"),
    ("upholstery installation", "upholstery removal"),
    ("assembly", "upholstery installation"),
    ("assembly", "structural repair"),
    ("assembly", "sanding"),
    ("sewing", "disassembly"),
    ("sewing", "upholstery removal"),
    ("weaving", "sewing"),
    ("ground oil", "wood fix"),
    ("hardwax oil", "wood fix"),
]


async def seed_working_sections(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    section_ids: dict[str, str] = {}

    for name in _SECTIONS:
        existing = await session.scalar(
            select(WorkingSection).where(
                WorkingSection.workspace_id == workspace_id,
                WorkingSection.name == name,
            )
        )
        if existing is None:
            section = WorkingSection(
                workspace_id=workspace_id,
                name=name,
                image=None,
            )
            session.add(section)
            await session.flush()
            section_ids[name] = section.client_id
        else:
            section_ids[name] = existing.client_id

    for dependent_name, prerequisite_name in _DEPENDENCIES:
        dependent_id = section_ids[dependent_name]
        prerequisite_id = section_ids[prerequisite_name]
        existing_dep = await session.scalar(
            select(WorkingSectionDependency).where(
                WorkingSectionDependency.workspace_id == workspace_id,
                WorkingSectionDependency.dependent_section_id == dependent_id,
                WorkingSectionDependency.prerequisite_section_id == prerequisite_id,
            )
        )
        if existing_dep is None:
            dep = WorkingSectionDependency(
                workspace_id=workspace_id,
                dependent_section_id=dependent_id,
                prerequisite_section_id=prerequisite_id,
            )
            session.add(dep)
            await session.flush()

    return section_ids
```

---

### Step 17 — Create phase: `seed_issue_category_configs.py`

**File: `services/commands/bootstrap/phases/seed_issue_category_configs.py`** (CREATE)

Seeds two bridge tables:

**`WorkingSectionSupportedIssueType`** — links each working section to the issue types it can encounter (27 rows total):
- structural repair, sanding → scratches, dents, broken parts, stains, structural damage, finish damage, loose joints (2 × 7 = 14)
- upholstery installation, sewing, weaving → upholstery damage (3 × 1 = 3)
- assembly → assembly issues, loose joints (1 × 2 = 2)
- wood fix → scratches, dents, broken parts, stains, structural damage, finish damage, assembly issues, loose joints (1 × 8 = 8)
- ground oil, hardwax oil → no supported issue types (not in `_SECTION_ISSUE_TYPE_MAP`)

**`IssueCategoryConfig`** — links issue types to item categories with `base_time_seconds=600` (10 minutes). Two groups:
- **Seating**: all 9 issue types × 7 seating categories = 63 rows
- **Wood**: 8 wood-applicable issue types (all except `upholstery damage`) × 27 wood categories = 216 rows
- **Total**: 279 rows

`effective_from` is `None`. `IssueCategoryConfig` has no `working_section_id` column — section specificity comes from `WorkingSectionSupportedIssueType` only.

**Idempotency note for `IssueCategoryConfig`**: The unique constraint includes `effective_from`, which is nullable. In Postgres, `NULL != NULL` for unique constraint purposes — two rows with the same other columns and `effective_from = NULL` would both pass the constraint. Therefore idempotency MUST use `SELECT ... WHERE effective_from IS NULL` before INSERT, not the DB constraint.

Returns `None` — the orchestrator does not need downstream data from this phase.

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.issue_types.issue_category_config import IssueCategoryConfig
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import WorkingSectionSupportedIssueType

# Maps working section name → list of issue type names it supports
_SECTION_ISSUE_TYPE_MAP: dict[str, list[str]] = {
    "structural repair": [
        "scratches", "dents", "broken parts", "stains",
        "structural damage", "finish damage", "loose joints",
    ],
    "sanding": [
        "scratches", "dents", "broken parts", "stains",
        "structural damage", "finish damage", "loose joints",
    ],
    "upholstery installation": ["upholstery damage"],
    "sewing": ["upholstery damage"],
    "weaving": ["upholstery damage"],
    "assembly": ["assembly issues", "loose joints"],
    "wood fix": [
        "scratches", "dents", "broken parts", "stains",
        "structural damage", "finish damage", "assembly issues", "loose joints",
    ],
}
# Note: "ground oil" and "hardwax oil" have no supported issue types — they are not in this map.

_SEATING_CATEGORIES = [
    "armchair", "bench", "chair", "chairs", "dining chair", "sofa", "stool",
]

_WOOD_CATEGORIES = [
    "bar cabinet", "bedside table", "bookshelf", "cabinet", "chest of drawer",
    "chest of drawers", "coffee table", "conference table", "corner cabinet",
    "dining table", "hall table", "highboard", "lamp", "mirror", "nest of tables",
    "plant stand", "poster", "round table", "secretary", "serving trolley",
    "side table", "sideboard", "small table", "shelving", "sewing table",
    "trolley", "writing desk",
]

# Issue types that apply to wood item categories.
# "upholstery damage" is seating-only and is intentionally excluded.
_WOOD_APPLICABLE_ISSUE_TYPES: frozenset[str] = frozenset({
    "scratches", "dents", "broken parts", "stains",
    "structural damage", "finish damage", "assembly issues", "loose joints",
})


async def seed_issue_category_configs(
    session: AsyncSession,
    workspace_id: str,
    issue_type_ids: dict[str, str],
    item_category_ids: dict[str, str],
    section_ids: dict[str, str],
) -> None:
    # 1. WorkingSectionSupportedIssueType links
    for section_name, issue_type_names in _SECTION_ISSUE_TYPE_MAP.items():
        section_id = section_ids[section_name]
        for issue_type_name in issue_type_names:
            issue_type_id = issue_type_ids[issue_type_name]
            existing = await session.scalar(
                select(WorkingSectionSupportedIssueType).where(
                    WorkingSectionSupportedIssueType.workspace_id == workspace_id,
                    WorkingSectionSupportedIssueType.working_section_id == section_id,
                    WorkingSectionSupportedIssueType.issue_type_id == issue_type_id,
                )
            )
            if existing is None:
                link = WorkingSectionSupportedIssueType(
                    workspace_id=workspace_id,
                    working_section_id=section_id,
                    issue_type_id=issue_type_id,
                )
                session.add(link)
                await session.flush()

    # 2. IssueCategoryConfig — seating: all 9 issue types × 7 seating categories = 63 rows
    # effective_from is None; must use IS NULL in WHERE for idempotency (NULL != NULL in Postgres unique constraints)
    for issue_type_name, issue_type_id in issue_type_ids.items():
        for cat_name in _SEATING_CATEGORIES:
            item_category_id = item_category_ids[cat_name]
            existing = await session.scalar(
                select(IssueCategoryConfig).where(
                    IssueCategoryConfig.workspace_id == workspace_id,
                    IssueCategoryConfig.issue_type_id == issue_type_id,
                    IssueCategoryConfig.item_category_id == item_category_id,
                    IssueCategoryConfig.effective_from.is_(None),
                )
            )
            if existing is None:
                config = IssueCategoryConfig(
                    workspace_id=workspace_id,
                    issue_type_id=issue_type_id,
                    item_category_id=item_category_id,
                    base_time_seconds=600,
                )
                session.add(config)
                await session.flush()

    # 3. IssueCategoryConfig — wood: 8 wood-applicable issue types × 27 wood categories = 216 rows
    # "upholstery damage" is excluded — it does not apply to wood item categories.
    for issue_type_name, issue_type_id in issue_type_ids.items():
        if issue_type_name not in _WOOD_APPLICABLE_ISSUE_TYPES:
            continue
        for cat_name in _WOOD_CATEGORIES:
            item_category_id = item_category_ids[cat_name]
            existing = await session.scalar(
                select(IssueCategoryConfig).where(
                    IssueCategoryConfig.workspace_id == workspace_id,
                    IssueCategoryConfig.issue_type_id == issue_type_id,
                    IssueCategoryConfig.item_category_id == item_category_id,
                    IssueCategoryConfig.effective_from.is_(None),
                )
            )
            if existing is None:
                config = IssueCategoryConfig(
                    workspace_id=workspace_id,
                    issue_type_id=issue_type_id,
                    item_category_id=item_category_id,
                    base_time_seconds=600,
                )
                session.add(config)
                await session.flush()
```

---

### Step 18 — Create phase: `seed_working_section_item_categories.py`

**File: `services/commands/bootstrap/phases/seed_working_section_item_categories.py`** (CREATE)

Links each working section to the item categories it can process (178 rows total):
- `cleaning` → all 34 item categories (7 seating + 27 wood)
- `wood fix`, `ground oil`, `hardwax oil` → 27 wood item categories only (3 × 27 = 81)
- all other 9 sections → 7 seating item categories only (9 × 7 = 63)

Idempotent: SELECT by `(workspace_id, working_section_id, item_category_id)` before INSERT. Returns `None` — no downstream phase needs this data.

**Mapping rule** (hardcoded): `_BOTH_CATEGORY_SECTIONS` sections get all 34 categories; `_WOOD_ONLY_SECTIONS` sections get wood only; every other section gets seating only. Adding a new section with a non-default scope requires only adding it to the appropriate frozenset.

`"wood fix"`, `"ground oil"`, and `"hardwax oil"` are all in `_WOOD_ONLY_SECTIONS`.

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section_item_category import WorkingSectionItemCategory

_SEATING_CATEGORIES = [
    "armchair", "bench", "chair", "chairs", "dining chair", "sofa", "stool",
]

_WOOD_CATEGORIES = [
    "bar cabinet", "bedside table", "bookshelf", "cabinet", "chest of drawer",
    "chest of drawers", "coffee table", "conference table", "corner cabinet",
    "dining table", "hall table", "highboard", "lamp", "mirror", "nest of tables",
    "plant stand", "poster", "round table", "secretary", "serving trolley",
    "side table", "sideboard", "small table", "shelving", "sewing table",
    "trolley", "writing desk",
]

# Sections that accept both seating and wood item categories.
_BOTH_CATEGORY_SECTIONS: frozenset[str] = frozenset({"cleaning"})
# Sections that accept wood item categories only.
_WOOD_ONLY_SECTIONS: frozenset[str] = frozenset({"wood fix", "ground oil", "hardwax oil"})
# All other sections accept seating categories only.


async def seed_working_section_item_categories(
    session: AsyncSession,
    workspace_id: str,
    section_ids: dict[str, str],
    item_category_ids: dict[str, str],
) -> None:
    for section_name, section_id in section_ids.items():
        if section_name in _BOTH_CATEGORY_SECTIONS:
            cat_names = _SEATING_CATEGORIES + _WOOD_CATEGORIES
        elif section_name in _WOOD_ONLY_SECTIONS:
            cat_names = _WOOD_CATEGORIES
        else:
            cat_names = _SEATING_CATEGORIES
        for cat_name in cat_names:
            item_category_id = item_category_ids[cat_name]
            existing = await session.scalar(
                select(WorkingSectionItemCategory).where(
                    WorkingSectionItemCategory.workspace_id == workspace_id,
                    WorkingSectionItemCategory.working_section_id == section_id,
                    WorkingSectionItemCategory.item_category_id == item_category_id,
                )
            )
            if existing is None:
                link = WorkingSectionItemCategory(
                    workspace_id=workspace_id,
                    working_section_id=section_id,
                    item_category_id=item_category_id,
                )
                session.add(link)
                await session.flush()
```

---

## Risks and mitigations

- **Risk**: `USING name::text::role_name_enum_new` cast fails if any role row still has `'member'` or `'field'` when the ALTER runs.
  Mitigation: The three DELETE statements in `upgrade()` run before the enum recreation. Order is strict: workspace_memberships → workspace_roles → roles. If a FK violation occurs, it means the migration's DELETE order is wrong — recheck the child-first ordering.

- **Risk**: `seed_workspace` idempotent re-read may encounter a partially-seeded state (workspace exists, some WorkspaceRole rows do not) if a prior bootstrap run was interrupted mid-transaction.
  Mitigation: After re-reading existing workspace roles, the idempotent branch iterates `role_ids` and creates any missing `WorkspaceRole` row before returning. The result dict is always complete when `seed_admin_user` receives it.

- **Risk**: `bcrypt.gensalt()` uses the default work factor (12). On slow hardware this adds ~300ms to the bootstrap call. This is intentional and acceptable for a one-time setup operation.

- **Risk**: The bootstrap endpoint is unauthenticated (no JWT). A leaked `BOOTSTRAP_SECRET` allows an attacker to reset the admin user's workspace role by re-running bootstrap.
  Mitigation: The idempotency guard does NOT update existing data — it only inserts missing rows. Rotate `BOOTSTRAP_SECRET` after the first successful bootstrap call in production.

- **Risk**: Alembic autogenerate may produce unexpected additional changes beyond the enum column if there is schema drift on other tables.
  Mitigation: Review the autogenerated migration file carefully before applying. If unrelated tables appear in the diff, remove those changes and handle them separately.

---

## Validation plan

Run after `alembic upgrade head` against a dev DB with bootstrap env vars set:

- `POST /api/v1/bootstrap` with correct `X-Bootstrap-Secret` → `200`, body: `{"data": {"workspace_id": "ws_...", "admin_user_id": "usr_...", "roles_seeded": ["admin","worker","manager","seller"]}, "warnings": []}`.
- Re-run `POST /api/v1/bootstrap` → `200`, same `workspace_id` and `admin_user_id` — verify DB row count unchanged.
- `POST /api/v1/auth/sign-in` with `BOOTSTRAP_ADMIN_EMAIL` + `BOOTSTRAP_ADMIN_PASSWORD` → valid JWT with `role_name: "admin"`.
- `POST /api/v1/bootstrap` with wrong secret → `403`.
- `POST /api/v1/bootstrap` with correct secret but `BOOTSTRAP_ADMIN_EMAIL` unset → `422 ValidationError`.
- `SELECT unnest(enum_range(NULL::role_name_enum))` in psql → `{admin, worker, manager, seller}`.
- Verify no `member` or `field` rows in `roles` table.
- `SELECT count(*) FROM item_categories WHERE workspace_id = '<ws_id>'` → 34.
- `SELECT count(*) FROM issue_types WHERE workspace_id = '<ws_id>'` → 9; all rows have `source = 'internal_inspection'`.
- `SELECT count(*) FROM issue_severities WHERE workspace_id = '<ws_id>'` → 3; verify `time_multiplier` values: 1.1, 1.5, 2.0.
- `SELECT count(*) FROM working_sections WHERE workspace_id = '<ws_id>'` → 13; all have `image = NULL`.
- `SELECT count(*) FROM working_section_dependencies WHERE workspace_id = '<ws_id>'` → 15; verify `wood fix` has zero dependency rows; `ground oil` and `hardwax oil` each have one.
- `SELECT count(*) FROM working_section_supported_issue_types WHERE workspace_id = '<ws_id>'` → 27; verify `ground oil` and `hardwax oil` have zero rows each.
- `SELECT count(*) FROM issue_category_configs WHERE workspace_id = '<ws_id>' AND effective_from IS NULL` → 279; all have `base_time_seconds = 600`.
- `SELECT count(*) FROM working_section_item_categories WHERE workspace_id = '<ws_id>'` → 178.
- Spot-check: `SELECT count(*) FROM working_section_item_categories wsic JOIN working_sections ws ON wsic.working_section_id = ws.client_id WHERE ws.name = 'cleaning'` → 34.
- Spot-check: same query for `wood fix` → 27; for `ground oil` → 27; for `hardwax oil` → 27.
- Spot-check: same query for any seating-only section name → 7.
- Re-run `POST /api/v1/bootstrap` → all row counts remain identical (idempotency verified).

---

## Review log

- `2026-05-15` `claude-sonnet-4-6`: Plan created. Decisions resolved: HTTP + secret header trigger, workspace in bootstrap, `BOOTSTRAP_ADMIN_*` env var names, migration in scope, one-file-per-phase structure. Migration SQL manually written (autogenerate cannot handle enum value removal). Phase passing contract fully specified.
- `2026-05-15` `claude-sonnet-4-6`: Gap review applied. Fixed two bugs: (1) `downgrade()` now cascade-deletes worker/manager/seller rows before the enum cast — without this the cast fails on a seeded database. (2) `seed_workspace` idempotent branch now creates missing WorkspaceRole rows — without this a partially-seeded re-run crashes with `KeyError` in `seed_admin_user`.
- `2026-05-15` `claude-sonnet-4-6`: Extended with 5 new seed phases (Steps 13–17) covering item categories (34), issue types (9), issue severities (3), working sections (10 + 13 dependency edges), and issue category configs (19 `WorkingSectionSupportedIssueType` + 63 `IssueCategoryConfig` rows). Updated scope to 12 new files. Key decisions: `IssueSourceEnum.INTERNAL_INSPECTION` for all admin-seeded issue types; `IssueCategoryConfig` idempotency uses `IS NULL` filter on `effective_from` because Postgres unique constraints treat NULL as not-equal; `ItemMajorCategoryEnum.SEAT = "seat"` (not "seating"). `seed_issue_severities` uses `Decimal` literals not floats.
- `2026-05-15` `claude-sonnet-4-6`: Gap review (second pass). Fixed 5 gaps: (1) `ValidationFailed` renamed to `ValidationError` everywhere — `ValidationFailed` does not exist; correct class is `ValidationError` (http_status=422) from `beyo_manager.errors.validation`. (2) Clarification item 6 updated from "all three phases" to all eight phases — old text would mislead Copilot to wrap only 3 phases in the transaction. (3) Migration clarification prose rewritten to show correct child→parent DELETE order (was showing the inverse). (4) `__init__.py` stub contents clarified — each stub now listed individually with its correct content string. (5) Goal description updated to reflect all 8 seed domains.
- `2026-05-15` `claude-sonnet-4-6`: Added Step 18 `seed_working_section_item_categories.py` — `working_section_item_categories` table was missing from bootstrap entirely. Mapping: `cleaning` → all 34 categories (seating + wood); all other 9 sections → 7 seating categories only (97 rows total). Updated scope to 13 new files, phase count to 9, clarification item 6, acceptance criterion 12, and validation plan.
- `2026-05-15` `claude-sonnet-4-6`: Added "wood worker" working section (Step 16). No dependencies. Item category scope: wood only (27 categories) via `_WOOD_ONLY_SECTIONS` in Step 18. Supported issue types: 8 (all except upholstery damage) via Step 17 `_SECTION_ISSUE_TYPE_MAP`. Added `_WOOD_APPLICABLE_ISSUE_TYPES` and a third loop in `seed_issue_category_configs` to seed `IssueCategoryConfig` for 8 issue types × 27 wood categories = 216 additional rows. Updated totals: 11 sections, 27 `WorkingSectionSupportedIssueType` rows, 279 `IssueCategoryConfig` rows, 124 `working_section_item_categories` rows.
- `2026-05-15` `claude-sonnet-4-6`: Renamed "wood worker" → "wood fix" everywhere (Steps 16, 17, 18). Added "ground oil" and "hardwax oil" sections — both depend on "wood fix", both wood-only item categories, no supported issue types. Updated totals: 13 sections, 15 dependency edges, 178 `working_section_item_categories` rows. `WorkingSectionSupportedIssueType` and `IssueCategoryConfig` counts unchanged (27 and 279).

## Lifecycle transition

- Current state: `archived`
- Previous states: `under_construction` → `approved` → `implemented` → `summarized` → `archived`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_bootstrap_and_roles_20260515.md`
- Archive: `backend/docs/architecture/archives/ARCHIVE_bootstrap_and_roles_20260515_1200.md`
