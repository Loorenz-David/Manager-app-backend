# PLAN_workspace_role_wood_worker_20260623

## Metadata

- Plan ID: `PLAN_workspace_role_wood_worker_20260623`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-23T00:00:00Z`
- Last updated at (UTC): `2026-06-23T07:02:59Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Introduce a `wood_worker` custom workspace role as a sub-specialisation of the `worker` system role. Add a `WorkspaceRoleNameEnum` domain enum that becomes the column type for `workspace_roles.name`. Make that column nullable so system roles (admin, manager, seller, worker) carry `NULL`, while custom roles carry the enum value. Assign Mykola to `wood_worker` in the worker seed.
- Business/user intent: Allow workspaces to define specialised sub-roles that share the permissions of a base system role but carry a distinct label (e.g., a wood-working specialist who is still a `worker` for access-control purposes).
- Non-goals: New API endpoints, permission changes, or frontend serializer changes beyond the fallback fix in `sign_in_user`.

## Scope

- In scope:
  - New `domain/workspaces/__init__.py` and `domain/workspaces/enums.py` — `WorkspaceRoleNameEnum`
  - `models/tables/roles/workspace_role.py` — change `name` column to `SAEnum(WorkspaceRoleNameEnum) nullable=True`
  - Alembic migration — create `workspace_role_name_enum` PG enum, migrate existing rows to `NULL`, alter column type
  - `services/commands/bootstrap/phases/seed_workspace.py` — look up existing rows by `role_id`; seed `wood_worker` custom role; return its `client_id` under key `"wood_worker"`
  - `services/commands/bootstrap/phases/seed_workers.py` — assign `Mykola` to `"wood_worker"` workspace role
  - `services/commands/auth/sign_in_user.py` — fall back to `permission_role.name.value` when `workspace_role.name` is `None`
- Out of scope:
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
6. `sign_in_user` response field `"role"` is `"wood_worker"` for Mykola and remains `"admin"` / `"worker"` / etc. for standard users.
7. All other seeded workers are unaffected.

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
- `services/commands/auth/sign_in_user.py` — exact `"role"` key construction to write the fallback
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

Remove the `String` import if it becomes unused after this change (verify — `String` is also used by `workspace_id` and `description` fields, so it stays).

The `UniqueConstraint` on `(workspace_id, name)` is intentionally kept: PostgreSQL treats NULLs as distinct so multiple system roles with `name=NULL` in the same workspace do not conflict; uniqueness is only enforced across non-NULL values (i.e., no two `wood_worker` rows per workspace).

---

### Step 3 — Alembic migration

Create a new migration file. Follow the naming convention of existing migrations.

Migration description: `add_workspace_role_name_enum_column`

**`upgrade()`**:
```python
def upgrade() -> None:
    # 1. Create the new enum type.
    op.execute("CREATE TYPE workspace_role_name_enum AS ENUM ('wood_worker')")

    # 2. Wipe existing name values — system roles will carry NULL.
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
    # Note: downgrade sets NOT NULL but existing rows may have NULL — only safe
    # if workspace_roles has been fully re-seeded beforehand. Acceptable for dev.

    # 2. Drop the enum type.
    op.execute("DROP TYPE workspace_role_name_enum")
```

---

### Step 4 — Update `seed_workspace.py`

File: `app/beyo_manager/services/commands/bootstrap/phases/seed_workspace.py`

**Changes:**

1. Import `WorkspaceRoleNameEnum`:
```python
from beyo_manager.domain.workspaces.enums import WorkspaceRoleNameEnum
```

2. Change the existing-row lookup from keying by `name` to keying by `role_id`, because system roles now have `name=NULL`:

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
    existing_roles = await session.execute(
        select(WorkspaceRole).where(WorkspaceRole.workspace_id == workspace_id)
    )
    workspace_roles_by_role_id = {row.role_id: row for row in existing_roles.scalars().all()}

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

3. After the `for` loop, add the `wood_worker` custom workspace role. `wood_worker` also references the `worker` Role (`role_ids["worker"]`), but it is looked up separately because the system `worker` workspace role has already been inserted above.

```python
    # Custom workspace roles — keyed by name since they may share role_id with a system role.
    existing_wood_worker = next(
        (row for row in workspace_roles_by_role_id.values() if row.name == WorkspaceRoleNameEnum.WOOD_WORKER),
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
_WORKER_WORKSPACE_ROLES: dict[str, str] = {
    worker_name: "worker"
    for worker_name in _WORKER_NAMES
}
_WORKER_WORKSPACE_ROLES["Norby"] = "manager"
_WORKER_WORKSPACE_ROLES["Stina"] = "manager"
_WORKER_WORKSPACE_ROLES["Betty"] = "manager"
_WORKER_WORKSPACE_ROLES["Fayoz"] = "admin"
```

Replace with:
```python
_WORKER_WORKSPACE_ROLES: dict[str, str] = {
    worker_name: "worker"
    for worker_name in _WORKER_NAMES
}
_WORKER_WORKSPACE_ROLES["Norby"] = "manager"
_WORKER_WORKSPACE_ROLES["Stina"] = "manager"
_WORKER_WORKSPACE_ROLES["Betty"] = "manager"
_WORKER_WORKSPACE_ROLES["Fayoz"] = "admin"
_WORKER_WORKSPACE_ROLES["Mykola"] = "wood_worker"
```

No other changes in this file. `_resolve_worker_workspace_role_id` already looks up by key from `workspace_result`, which now includes `"wood_worker"`.

---

### Step 6 — Fix `sign_in_user.py` role fallback

File: `app/beyo_manager/services/commands/auth/sign_in_user.py`

`workspace_role.name` is now `WorkspaceRoleNameEnum | None`. For system roles it is `None`; for custom roles it is the enum value (e.g., `"wood_worker"`). The `"role"` field in the auth response must fall back to the base role name when `name` is `None`.

Find:
```python
        "user": {
            "client_id": user.client_id,
            "email": user.email,
            "username": user.username,
            "role": workspace_role.name,
            "backend_permissions": permissions["backend"],
            "ui": permissions["ui"],
        },
```

Replace with:
```python
        "user": {
            "client_id": user.client_id,
            "email": user.email,
            "username": user.username,
            "role": workspace_role.name if workspace_role.name is not None else permission_role.name.value,
            "backend_permissions": permissions["backend"],
            "ui": permissions["ui"],
        },
```

---

## Risks and mitigations

- Risk: Existing rows in `workspace_roles.name` are non-null strings. The `USING name::workspace_role_name_enum` cast will fail if any current value is not in the new enum.
  Mitigation: The migration first runs `UPDATE workspace_roles SET name = NULL` before the `ALTER COLUMN`, so no existing string value is ever cast — all rows are already `NULL` when the type change happens.

- Risk: The downgrade sets `NOT NULL` on a column where rows may be `NULL` after a reset/re-seed cycle.
  Mitigation: Downgrade is only safe in a development environment after a fresh bootstrap. This is acceptable — the project pattern (see `ec9017a0245c`) does not guarantee safe downgrades in production.

- Risk: `workspace_roles_by_role_id` is keyed by `role_id`. The `wood_worker` custom role shares `role_id` with the system `worker` workspace role. The seed lookup for the `wood_worker` row uses a separate `next(...)` scan by name, which correctly avoids collision.
  Mitigation: Already accounted for in Step 4's implementation. The standard system roles (including `worker`) are looked up by `role_id`; the custom `wood_worker` is looked up by its enum name.

- Risk: The unique constraint `uq_workspace_roles_workspace_name` on `(workspace_id, name)` — if `name` is `NULL` for multiple system rows in the same workspace, PostgreSQL treats each `NULL` as distinct, so no violation occurs.
  Mitigation: This is standard PostgreSQL NULL behaviour. No constraint change needed.

## Validation plan

- `alembic upgrade head` on a clean DB: passes with no errors.
- `POST /bootstrap` (or equivalent bootstrap command): completes without exception.
- Query `SELECT name, description FROM workspace_roles;` — system rows return `NULL` for name; one row returns `wood_worker`.
- Query `SELECT wm.workspace_role_id, wr.name FROM workspace_memberships wm JOIN workspace_roles wr ON wr.client_id = wm.workspace_role_id JOIN users u ON u.client_id = wm.user_id WHERE u.username = 'Mykola';` — returns `wood_worker`.
- `POST /auth/sign-in` with Mykola's credentials — response `user.role` is `"wood_worker"`.
- `POST /auth/sign-in` with Norby's credentials — response `user.role` is `"manager"` (fallback path).
- `python3 -m compileall` on all changed files: no errors.

## Review log

_(none yet)_

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
