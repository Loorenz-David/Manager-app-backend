# PLAN_workspace_role_wood_worker_20260623

## Metadata

- Plan ID: `PLAN_workspace_role_wood_worker_20260623`
- Status: `under_construction`
- Owner agent: `codex`
- Created at (UTC): `2026-06-23T00:00:00Z`
- Last updated at (UTC): `2026-06-23T00:00:00Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Introduce a `wood_worker` custom workspace role as a sub-specialisation of the `worker` system role. Add a `WorkspaceRoleNameEnum` domain enum that becomes the column type for `workspace_roles.name`. Make that column nullable so system roles (admin, manager, seller, worker) carry `NULL`, while custom roles carry the enum value. Assign Mykola to `wood_worker` in the worker seed. Add `workspace_role_name` to the JWT claims so the frontend can read the custom role by decoding the token.
- Business/user intent: Allow workspaces to define specialised sub-roles that share the permissions of a base system role but carry a distinct label (e.g., a wood-working specialist who is still a `worker` for access-control purposes). The frontend derives all user/session data solely from the decoded access token — same shape on sign-in and refresh — so `workspace_role_name` must be a token claim.
- Non-goals: New API endpoints, permission changes, or any frontend change.

## Scope

- In scope:
  - New `domain/workspaces/__init__.py` and `domain/workspaces/enums.py` — `WorkspaceRoleNameEnum`
  - `models/tables/roles/workspace_role.py` — change `name` column to `SAEnum(WorkspaceRoleNameEnum) nullable=True`
  - Alembic migration — create `workspace_role_name_enum` PG enum, migrate existing rows to `NULL`, alter column type
  - `services/commands/bootstrap/phases/seed_workspace.py` — look up existing rows by `role_id`; seed `wood_worker` custom role; return its `client_id` under key `"wood_worker"`
  - `services/commands/bootstrap/phases/seed_workers.py` — assign Mykola to `"wood_worker"` workspace role
  - `services/commands/auth/sign_in_user.py` — add `workspace_role_name` claim to JWT; fix `"role"` field fallback in `user` response body
- Out of scope:
  - `refresh_token.py` — no change needed; it re-encodes the existing claims dict, so `workspace_role_name` is automatically carried forward once it exists in the original token
  - Any router, query service, or serializer outside `sign_in_user`
  - Adding more custom workspace roles beyond `wood_worker`
  - Permission-level changes (wood_worker inherits full `worker` permissions unchanged)

## Clarifications required

_(none — all decisions are resolved below)_

## Acceptance criteria

1. `domain/workspaces/enums.py` exists and defines `WorkspaceRoleNameEnum` with member `WOOD_WORKER = "wood_worker"`.
2. `WorkspaceRole.name` is typed `Mapped[WorkspaceRoleNameEnum | None]` with `nullable=True`.
3. Alembic migration upgrades cleanly: existing `name` values become `NULL`; enum type `workspace_role_name_enum` is created in Postgres.
4. After bootstrap: four system `WorkspaceRole` rows have `name=NULL`; one `WorkspaceRole` row has `name='wood_worker'`.
5. After bootstrap: Mykola's `WorkspaceMembership.workspace_role_id` points to the `wood_worker` workspace role.
6. Decoded access token for Mykola contains `role_name: "worker"` and `workspace_role_name: "wood_worker"`.
7. Decoded access token for Norby (manager) contains `role_name: "manager"` and `workspace_role_name: null`.
8. `refresh_token` response produces a new access token that also contains `workspace_role_name` (no code change needed — claims are forwarded automatically).
9. All other seeded workers are unaffected.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: session.add / flush / error-raising shape in seed phases
- `backend/architecture/08_domain.md`: enum placement in `domain/<subdomain>/enums.py` using `StrEnum`
- Alembic migration pattern: see `migrations/versions/ec9017a0245c_update_role_name_enum_worker_manager_.py` for the PG-enum alter pattern used in this project

### File read intent — pattern vs. relational

Permitted reads:
- `models/tables/roles/workspace_role.py` — exact current field names and type declarations
- `services/commands/bootstrap/phases/seed_workspace.py` — existing seeding logic to identify the exact lines to change
- `services/commands/bootstrap/phases/seed_workers.py` — `_WORKER_WORKSPACE_ROLES` dict and `_resolve_worker_workspace_role_id` function
- `services/commands/auth/sign_in_user.py` — exact `claims` dict and `"role"` key construction
- `migrations/versions/ec9017a0245c_*.py` — migration pattern reference

Prohibited (pattern reads — covered by contracts):
- Reading another domain enum file to understand `StrEnum` usage → `08_domain.md`
- Reading another migration to understand `op.execute` shape → reference migration above

## Implementation plan

### Step 1 — Create `domain/workspaces/` package with `WorkspaceRoleNameEnum`

Create two files:

**`app/beyo_manager/domain/workspaces/__init__.py`** — empty.

**`app/beyo_manager/domain/workspaces/enums.py`**:
```python
from enum import StrEnum


class WorkspaceRoleNameEnum(StrEnum):
    WOOD_WORKER = "wood_worker"
```

---

### Step 2 — Update `WorkspaceRole` model

File: `app/beyo_manager/models/tables/roles/workspace_role.py`

Add imports at the top:
```python
from sqlalchemy import Enum as SAEnum
from beyo_manager.domain.workspaces.enums import WorkspaceRoleNameEnum
from beyo_manager.models.base.sa_enum import configure_sa_enum_values

SAEnum = configure_sa_enum_values(SAEnum)
```

Change the `name` field:

Find:
```python
    name: Mapped[str] = mapped_column(String(64), nullable=False)
```

Replace with:
```python
    name: Mapped[WorkspaceRoleNameEnum | None] = mapped_column(
        SAEnum(WorkspaceRoleNameEnum, name="workspace_role_name_enum", create_type=False),
        nullable=True,
    )
```

`String` stays imported — it is still used by `workspace_id` and `description`.

The `UniqueConstraint` on `(workspace_id, name)` is intentionally kept: PostgreSQL treats NULLs as distinct so multiple system roles with `name=NULL` in the same workspace do not conflict; uniqueness is only enforced for non-NULL values (no two `wood_worker` rows per workspace).

---

### Step 3 — Alembic migration

Create a new migration file following the existing naming convention.

Migration description: `add_workspace_role_name_enum_column`

**`upgrade()`**:
```python
def upgrade() -> None:
    # 1. Create the new enum type.
    op.execute("CREATE TYPE workspace_role_name_enum AS ENUM ('wood_worker')")

    # 2. Wipe existing string name values — system roles carry NULL.
    op.execute("UPDATE workspace_roles SET name = NULL")

    # 3. Alter the column: drop NOT NULL, change type from VARCHAR to the new enum.
    op.execute(
        """
        ALTER TABLE workspace_roles
        ALTER COLUMN name DROP NOT NULL,
        ALTER COLUMN name TYPE workspace_role_name_enum
            USING name::workspace_role_name_enum
        """
    )
```

**`downgrade()`**:
```python
def downgrade() -> None:
    # 1. Cast back to VARCHAR (NULL values stay NULL, enum values cast to text).
    op.execute(
        """
        ALTER TABLE workspace_roles
        ALTER COLUMN name TYPE VARCHAR(64)
            USING name::text,
        ALTER COLUMN name SET NOT NULL
        """
    )
    # Note: SET NOT NULL will fail if any row has NULL — only safe after a full
    # re-seed with the old code. Acceptable for dev environments.

    # 2. Drop the enum type.
    op.execute("DROP TYPE workspace_role_name_enum")
```

---

### Step 4 — Update `seed_workspace.py`

File: `app/beyo_manager/services/commands/bootstrap/phases/seed_workspace.py`

**4a.** Add import:
```python
from beyo_manager.domain.workspaces.enums import WorkspaceRoleNameEnum
```

**4b.** Change the existing-row lookup from keying by `name` to keying by `role_id`, because system roles now have `name=NULL`:

Find:
```python
    existing_roles = await session.execute(
        select(WorkspaceRole).where(WorkspaceRole.workspace_id == workspace_id)
    )
    workspace_roles = {row.name: row for row in existing_roles.scalars().all()}

    for role_name_value, role_client_id in role_ids.items():
        workspace_role = workspace_roles.get(role_name_value)
        if workspace_role is None:
            workspace_role = WorkspaceRole(
                workspace_id=workspace_id,
                role_id=role_client_id,
                name=role_name_value,
                description=_DISPLAY_NAMES[role_name_value],
                is_system=True,
            )
            session.add(workspace_role)
            await session.flush()
        result[role_name_value] = workspace_role.client_id
```

Replace with:
```python
    existing_roles_result = await session.execute(
        select(WorkspaceRole).where(WorkspaceRole.workspace_id == workspace_id)
    )
    all_existing = existing_roles_result.scalars().all()
    workspace_roles_by_role_id = {row.role_id: row for row in all_existing}

    for role_name_value, role_client_id in role_ids.items():
        workspace_role = workspace_roles_by_role_id.get(role_client_id)
        if workspace_role is None:
            workspace_role = WorkspaceRole(
                workspace_id=workspace_id,
                role_id=role_client_id,
                name=None,
                description=_DISPLAY_NAMES[role_name_value],
                is_system=True,
            )
            session.add(workspace_role)
            await session.flush()
        result[role_name_value] = workspace_role.client_id
```

**4c.** After the `for` loop, seed the `wood_worker` custom workspace role. It shares `role_id` with the system `worker` row so it cannot be looked up by `role_id` — use a name scan instead:

```python
    existing_wood_worker = next(
        (row for row in all_existing if row.name == WorkspaceRoleNameEnum.WOOD_WORKER),
        None,
    )
    if existing_wood_worker is None:
        wood_worker_role = WorkspaceRole(
            workspace_id=workspace_id,
            role_id=role_ids["worker"],
            name=WorkspaceRoleNameEnum.WOOD_WORKER,
            description="Wood Worker",
            is_system=True,
        )
        session.add(wood_worker_role)
        await session.flush()
        result["wood_worker"] = wood_worker_role.client_id
    else:
        result["wood_worker"] = existing_wood_worker.client_id
```

---

### Step 5 — Update `seed_workers.py`

File: `app/beyo_manager/services/commands/bootstrap/phases/seed_workers.py`

Find:
```python
_WORKER_WORKSPACE_ROLES["Fayoz"] = "admin"
```

Replace with:
```python
_WORKER_WORKSPACE_ROLES["Fayoz"] = "admin"
_WORKER_WORKSPACE_ROLES["Mykola"] = "wood_worker"
```

No other changes. `_resolve_worker_workspace_role_id` already looks up by key from `workspace_result`, which now includes `"wood_worker"`.

---

### Step 6 — Update `sign_in_user.py`

File: `app/beyo_manager/services/commands/auth/sign_in_user.py`

Two changes in `build_auth_response`:

**6a.** Add `workspace_role_name` to the JWT claims dict.

Find:
```python
    claims = {
        "user_id": user.client_id,
        "username": user.username,
        "workspace_id": workspace.client_id,
        "workspace_role_id": workspace_role.client_id,
        "role_name": permission_role.name.value,
        "app_scope": app_scope,
        "time_zone": workspace.time_zone or "UTC",
        "backend_permissions": permissions["backend"],
        "ui": permissions["ui"],
    }
```

Replace with:
```python
    claims = {
        "user_id": user.client_id,
        "username": user.username,
        "workspace_id": workspace.client_id,
        "workspace_role_id": workspace_role.client_id,
        "role_name": permission_role.name.value,
        "workspace_role_name": workspace_role.name,
        "app_scope": app_scope,
        "time_zone": workspace.time_zone or "UTC",
        "backend_permissions": permissions["backend"],
        "ui": permissions["ui"],
    }
```

`workspace_role.name` is `WorkspaceRoleNameEnum | None`. `None` serialises to `null` in the JWT payload automatically — no extra handling needed.

**6b.** Fix the `"role"` field in the response body so it falls back to the base role name for system roles where `workspace_role.name` is `None`:

Find:
```python
            "role": workspace_role.name,
```

Replace with:
```python
            "role": workspace_role.name if workspace_role.name is not None else permission_role.name.value,
```

---

## Risks and mitigations

- Risk: `UPDATE workspace_roles SET name = NULL` then `ALTER COLUMN ... USING name::workspace_role_name_enum` — any non-null value would fail the cast.
  Mitigation: The `UPDATE` runs first, so all rows are already `NULL` before the type change. No cast ever touches a non-null string.

- Risk: `refresh_token.py` re-encodes from the claims dict decoded from the existing refresh token. If a user authenticated before the `workspace_role_name` claim was introduced, their stored refresh token won't have it.
  Mitigation: Acceptable — users will pick it up on their next sign-in. No code change to `refresh_token.py` is needed.

- Risk: The downgrade `SET NOT NULL` fails if rows have `NULL` names.
  Mitigation: Downgrade is dev-only. The project pattern (see `ec9017a0245c`) does not guarantee safe production downgrades.

- Risk: `workspace_roles_by_role_id` is keyed by `role_id`. Both the system `worker` and the `wood_worker` custom role share the same `role_id` (the `worker` Role). The dict would only hold one of them.
  Mitigation: Already handled — system roles are seeded in the `for` loop (keyed by `role_id`); `wood_worker` is seeded separately via a name scan over `all_existing`. The two lookups are independent.

## Validation plan

- `alembic upgrade head`: no errors.
- `POST /bootstrap` (or equivalent): completes without exception.
- `SELECT name, description FROM workspace_roles;` — system rows show `NULL` for name; one row shows `wood_worker`.
- Sign in as Mykola → decode access token → assert `role_name = "worker"`, `workspace_role_name = "wood_worker"`.
- Sign in as Norby → decode access token → assert `role_name = "manager"`, `workspace_role_name = null`.
- Use Mykola's refresh token → new access token also contains `workspace_role_name = "wood_worker"`.
- `python3 -m compileall` on all changed files: no errors.

## Review log

_(none yet)_

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `codex`
