# INTENTION_bootstrap_and_roles_20260515

## Metadata

- Intention ID: `INTENTION_bootstrap_and_roles_20260515`
- Status: `achieved`
- Owner: `claude-sonnet-4-6`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T12:00:00Z`

## Goal

Establish an idempotent app-level bootstrap so the system is immediately usable after a fresh deployment: correct roles exist in the database, a default workspace is provisioned, and a default admin user can sign in with credentials drawn from environment variables.

## Why this matters

After `alembic upgrade head` there is no data in the system — no roles, no workspace, no user. The sign-in flow requires a complete chain: User → WorkspaceMembership → WorkspaceRole → Role → Workspace. Without the bootstrap, a freshly deployed instance cannot accept any sign-in or API call. The bootstrap fills this gap in a single idempotent HTTP call, and its phase-per-file design makes it safe to extend as new domain data needs seeding in future iterations.

## Success criteria

1. `POST /api/v1/bootstrap` protected by `X-Bootstrap-Secret` header creates all seed data on a fresh database and returns a summary payload with `workspace_id` and `admin_user_id`.
2. Re-running `POST /api/v1/bootstrap` on an already-seeded database returns the same summary without creating duplicates, raising errors, or modifying existing data.
3. After bootstrap, an admin user can sign in via `POST /api/v1/auth/sign-in` using the credentials from `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` and receive a valid JWT.
4. `RoleNameEnum` is updated to `{ADMIN, WORKER, MANAGER, SELLER}`. `MEMBER` and `FIELD` are removed. The Alembic migration runs before the bootstrap and handles the enum type change cleanly.
5. `routers/utils/roles.py` reflects the new role set: `ADMIN`, `WORKER`, `MANAGER`, `SELLER`. No reference to `MEMBER` or `FIELD` remains in the application code.
6. The bootstrap command is structured as one phase file per concern (`seed_roles`, `seed_workspace`, `seed_admin_user`). Adding a new seed phase requires only: creating a new phase file and adding one `await` call in the orchestrator.
7. A missing or incorrect `BOOTSTRAP_SECRET` returns `403 Forbidden` with no data written to the database.
8. Missing required bootstrap env vars (`BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_USERNAME`, `BOOTSTRAP_ADMIN_PASSWORD`) cause the command to raise `ValidationFailed` before any DB writes.

## Scope boundary

- In scope:
  - Alembic migration: drop `member` and `field` enum values, add `worker`, `manager`, `seller` to `role_name_enum`
  - Python enum update: `domain/roles/enums.py` — `RoleNameEnum`
  - Router utils update: `routers/utils/roles.py` — role string constants
  - Settings update: `config.py` — six new bootstrap fields; `.env.example` — corresponding vars
  - Bootstrap command orchestrator: `services/commands/bootstrap/bootstrap_app.py`
  - Phase files: `seed_roles.py`, `seed_workspace.py`, `seed_admin_user.py`
  - Bootstrap router: `routers/api_v1/bootstrap.py` — one route, `POST ""`

- Out of scope:
  - Role-based permission atoms (the `Permission` enum in `domain/roles/permissions.py`) — a separate future plan
  - Workspace name or timezone management endpoints — not this plan
  - User management endpoints (invite, update, deactivate) — separate domain
  - CI pipeline integration or deploy-script automation for the bootstrap call
  - Multiple workspaces or multi-tenant provisioning

- Non-goals:
  - Changing the JWT claims structure or auth flow
  - Replacing the bootstrap endpoint with a startup hook or CLI-only path (decision already made: HTTP + secret header)

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_bootstrap_and_roles_20260515` | `backend/docs/architecture/under_construction/implementation/PLAN_bootstrap_and_roles_20260515.md` | `archived` | Migration, role enum, config, phase files, command, router |

## Progress notes

- `2026-05-15`: Intention created. All blocking decisions resolved: HTTP + secret header trigger, workspace created in bootstrap, `BOOTSTRAP_ADMIN_*` env var naming, migration in scope, one-file-per-phase scalability pattern.
- `2026-05-15`: Implementation complete. All 18 steps delivered. Migration `ec9017a0245c` applied — DB `role_name_enum` confirmed as `['admin', 'worker', 'manager', 'seller']`. Compile + import checks pass. Summary and archive written. Live HTTP end-to-end test deferred to next dev session.
- `2026-05-15`: Intention transitioned to `achieved`. All success criteria 1–8 met by code and DB evidence. Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_bootstrap_and_roles_20260515.md`. Archive: `backend/docs/architecture/archives/ARCHIVE_bootstrap_and_roles_20260515_1200.md`.

## Open questions

- None blocking at this time.

## Lifecycle transition

- Current status: `achieved`
- Next status: n/a
- Transition trigger: All 8 success criteria met — migration applied, code compiles, DB enum labels verified.
