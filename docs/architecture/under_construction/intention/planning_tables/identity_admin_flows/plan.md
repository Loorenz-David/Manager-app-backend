# Plan — Bootstrap Identity Initialization Flow

**Lifecycle state:** `REVIEW`
**Skill loadout:** plan_lifecycle_orchestrator · planning_contract_selection · ask_clarification_first · goal_intent_alignment
**Contracts referenced:** 01, 02, 04, 05, 06, 07, 08, 09, 10, 17, 18, 28, 36, 40, 41
**Date:** 2026-05-12
**Clarifications resolved:** 2026-05-12
**App-specific details locked:** 2026-05-12
**Target app:** Beyo Admin

---

## Resolved Decisions

| # | Question | Decision |
|---|---|---|
| Q1 | Identity system PK/FK | `client_id` String(64) is the PK and FK target across all tables. Generated app is being aligned to contracts. |
| Q2 | Bootstrap secret delivery | Both: `BOOTSTRAP_TOKEN` env var required to authorize the request + DB state tracks completion. Raw token is never stored in DB. |
| Q3 | Role seeding | Bootstrap creates default roles/permissions idempotently if absent. Never assumes pre-seeded roles. |
| Q4 | Response shape | Resource IDs only — no JWT returned. Admin must sign in via normal auth flow after bootstrap. |
| Q5 | Multi-tenant scope | One workspace per bootstrap. Model is extensible but platform workspace pattern is deferred. |
| Q6 | Audit log | Write bootstrap audit event if `audit_logs` table exists. If not, emit a minimal structured log entry and leave an explicit `# TODO: phase-audit-log` comment. |
| Q7 | Initial workspace name | Fixed: `"Beyo Vintage"` — hardcoded in bootstrap, not user-supplied. |
| Q8 | Role model | Name-based only: `ADMIN`, `MANAGER`, `SELLER`, `WORKER`. No permissions matrix. No RBAC tables. Role checks compare role name string only via `require_role("ADMIN")`. |
| Q9 | First bootstrap role | `ADMIN` only. All four base roles provisioned idempotently; admin user gets `ADMIN`. |
| Q10 | Permissions | Deferred entirely. Architecture must remain extensible but no permission atoms, groups, or tables in this phase. |
| Q11 | Membership model | `User ↔ WorkspaceMembership ↔ Workspace` with one Role per membership. Role is membership-scoped, not user-global. One membership per bootstrap. No many-to-many role assignment. Future multi-workspace support is possible without schema changes. |
| Q12 | Email uniqueness | `User.email` is globally unique (not workspace-scoped). Duplicate email must fail with 409. This invariant is required to keep auth architecture global-identity-first. |
| Q13 | Setup router lifecycle | Keep setup router mounted permanently. `/setup/status` remains available always. `/setup/init` remains mounted but returns 409 once bootstrap is completed. |
| Q14 | Bootstrap side effects | Bootstrap is strictly synchronous and transaction-bound. No background jobs, queue dispatch, websocket broadcasts, or external side effects are allowed during `bootstrap_init`. |
| Q15 | Workspace timezone source | Fixed timezone for initial workspace: `Europe/Stockholm`. Not request-driven. No timezone parameter in bootstrap API. |
| Q16 | Bootstrap enum semantics | `BootstrapStateEnum` persists only `PENDING` and `COMPLETED`. `DISABLED` in lifecycle diagrams is a derived runtime guard state (env/config), not a DB enum value. Runtime `DISABLED` means BOOTSTRAP_TOKEN missing OR bootstrap guard disabled. |

---

## 1. Goal Restatement

Enable a fresh installation of the **Beyo Admin** application to create the first administrator user securely, without any developer manually touching the database. The bootstrap automatically provisions a fixed initial workspace (`"Beyo Vintage"`), the base roles (`ADMIN`, `WORKER`, `MANAGER`), and the admin user + membership in one atomic transaction. Once initialization completes, the bootstrap mechanism permanently disables itself. The flow must be auditable, race-safe, and compatible with the async FastAPI + SQLAlchemy architecture.

---

## 2. High-Level Architecture Plan

The bootstrap flow is a **one-time-use, gated initialization subsystem** composed of four layers:

```
Environment / Config Layer
        │
        ▼
Bootstrap State Guard  ──── bootstrap_state table (or config row)
        │  (PENDING | COMPLETED)
        ▼
Bootstrap Router  (POST /setup/init)
        │
        ▼
bootstrap_init command  (CQRS command)
        │
        ├─ idempotent_create_roles  (ADMIN, MANAGER, SELLER, WORKER — name-based only)
        ├─ create_workspace          (name = "Beyo Vintage", fixed)
        ├─ create_workspace_role     (ADMIN role in workspace)
        ├─ create_user               (admin credentials from request)
        ├─ create_workspace_membership  (user ↔ "Beyo Vintage" ↔ ADMIN role)
        └─ mark_bootstrap_complete   (atomic flag transition)
                │
                ▼
        audit_log entry  (event: "bootstrap:admin_created")
```

**Activation strategy:** Bootstrap mode is gated by TWO independent guards (both must be satisfied):
1. `BOOTSTRAP_TOKEN` environment variable is set and non-empty
2. `bootstrap_state.status == PENDING` in the database AND no admin user exists yet

**Secret handling:** The raw `BOOTSTRAP_TOKEN` value is never stored in the database. Authorization is checked via `hmac.compare_digest` at request time against the env var only.

**Deactivation:** After successful initialization, `bootstrap_state.status` is flipped to `COMPLETED` atomically. Even if `BOOTSTRAP_TOKEN` remains set in the environment, the DB state check prevents re-use.

---

## 3. Domain Boundaries

```
┌────────────────────────────────────────────────────────────────┐
│  domain/bootstrap/                                              │
│  ├── enums.py       BootstrapStateEnum (PENDING | COMPLETED)   │
│  └── results.py     BootstrapInitResult                        │
│                                                                 │
│  models/tables/bootstrap/                                       │
│  └── bootstrap_state.py   BootstrapState (singleton row)       │
│                                                                 │
│  services/commands/bootstrap/                                   │
│  └── bootstrap_init.py    full orchestration command           │
│                                                                 │
│  routers/setup/                                                 │
│  └── setup.py        POST /setup/init  (no JWT required)       │
│                                                                 │
│  services/infra/bootstrap/                                      │
│  └── guard.py        is_bootstrap_available() async check      │
└────────────────────────────────────────────────────────────────┘
```

**Out of scope for this domain:**
- User management (contract 41)
- Role/permission management (contract 28)
- Workspace management (contract 24)
- All post-bootstrap auth flows (contract 10)

The bootstrap command **orchestrates** these domains — it does not own their logic. It calls the same model/session patterns those domains use.

### Role hierarchy and membership model (this phase)

```
Role
   -> global canonical role identity
       ADMIN / MANAGER / SELLER / WORKER

WorkspaceRole
   -> workspace-local representation of a Role
       (has workspace-local display_name, points to one Role)

WorkspaceMembership
   -> binds User to one WorkspaceRole in one Workspace
```

- `Role.name` is the canonical authorization identity used in claims (`claims["role_name"]`) and role checks.
- `WorkspaceRole.display_name` is workspace-local labeling, not the authorization claim identity.
- A membership holds exactly one `WorkspaceRole` (and therefore one underlying `Role`).
- Role assignment is membership-scoped, not user-global.
- One User can belong to multiple Workspaces via separate membership rows (future).
- Bootstrap provisions exactly one membership: admin user -> "Beyo Vintage" -> WorkspaceRole mapped to `Role.name = ADMIN`.
- Do not implement many-to-many role assignment in this phase.

### Identity invariant — global email uniqueness

- `User.email` is globally unique across the entire application.
- Email uniqueness is not scoped by workspace.
- Authentication identity lookup remains global (`email` / `username`), then membership constrains workspace access.
- Do not introduce per-workspace email uniqueness in this phase.

---

## 4. Required Tables / Models

### `BootstrapState` — `models/tables/bootstrap/bootstrap_state.py`

Singleton table — exactly one row, inserted by migration with `status = PENDING`.

```
bootstrap_state
├── client_id         String(64) PK  (IdentityMixin — CLIENT_ID_PREFIX = "bst")
├── status            Enum(BootstrapStateEnum)  PENDING | COMPLETED
├── completed_at      DateTime(tz) nullable
├── completed_by_id   String(64) FK → users.client_id  nullable
└── detail            JSON nullable  (metadata snapshot: app version, env, timestamp)
```

**Design decisions:**
- Single row — never INSERT from application code. Only UPDATE status.
- `client_id` PK aligns with contract 40 identity system (`client_id` is primary key).
- `completed_by_id` FK → `users.client_id` (string FK, consistent with contract 40/41 style).
- `completed_by_id` is nullable because user creation happens inside the same transaction — set after flush.
- `detail` captures: app version, timestamp, env name — never includes the raw `BOOTSTRAP_TOKEN`.
- Row is inserted by Alembic seed data in the migration, not by application startup.
- `BOOTSTRAP_TOKEN` env var value is **never written to this table**.

### No new tables required beyond `BootstrapState`

All other entities (User, Role, Workspace, WorkspaceRole, WorkspaceMembership) already exist from the bootstrap scaffold (phases 2 and 4). This flow just creates rows in them.

### Required uniqueness constraints (schema-level)

These constraints are mandatory at the database level (not just in service logic):

- `users.email` UNIQUE
- `roles.name` UNIQUE
- `workspaces.name` UNIQUE (current phase)
- `workspace_roles(workspace_id, display_name)` UNIQUE
- `workspace_memberships(user_id, workspace_id)` UNIQUE

Implementation notes:

- Constraints must be created in Alembic migrations, not left as implied behavior.
- Keep indexed access paths on uniqueness lookup columns used by bootstrap checks (`users.email`, `roles.name`, `workspaces.name`).
- Conflict handling in commands must map DB uniqueness violations to deterministic 409 responses.
- Service-level fetch-or-create logic is required, but it does not replace DB constraints.

---

## 5. Required Commands / Queries

### Command: `bootstrap_init` — `services/commands/bootstrap/bootstrap_init.py`

**Transaction boundary (explicit):** `bootstrap_init` runs inside one database transaction (`async with session.begin():`).
- No partial commit is allowed.
- All writes succeed together or fail together:
   - role provisioning
   - workspace + workspace role creation
   - user + membership creation
   - bootstrap state transition (`PENDING → COMPLETED`)
   - audit write / structured log fallback marker
- On any error, the transaction is rolled back and `BootstrapState` remains unchanged.

**Synchronous-only execution rule (explicit):**
- `bootstrap_init` must not enqueue background jobs.
- `bootstrap_init` must not publish websocket events.
- `bootstrap_init` must not dispatch queue messages.
- `bootstrap_init` must not invoke external side effects (webhooks, third-party APIs, email delivery, async workers).
- Allowed effects are limited to in-transaction database writes and local structured logging.
- Determinism requirement: command outcome is fully determined by request + DB state at execution time.

```
incoming_data keys:
  bootstrap_token    (str)   — must match BOOTSTRAP_TOKEN env var exactly
  email              (str)   — admin user email (validated format)
  username           (str)   — admin username
   password           (str)   — baseline policy enforced (minimum 8 characters); bcrypt-hashed inside command

Execution sequence (all inside one async transaction):
  1. Verify BOOTSTRAP_TOKEN env var is set — raise BootstrapDisabled (403) if absent
  2. Verify bootstrap_token matches env var (hmac.compare_digest — constant-time)
  3. Lock BootstrapState row FOR UPDATE (prevents race condition)
  4. Assert status == PENDING — raise BootstrapAlreadyCompleted (409) if COMPLETED
  5. Assert no User with ADMIN role exists — raise BootstrapAlreadyCompleted (409) if found
  6. Validate password against baseline policy (minimum 8 characters)
  7. Hash password with bcrypt
  8. Idempotent role provisioning (fetch-or-create by name — no permissions, name-based only):
     - Fetch or create Role(name="ADMIN")
     - Fetch or create Role(name="MANAGER")
     - Fetch or create Role(name="SELLER")
     - Fetch or create Role(name="WORKER")
  9. Fetch or create Workspace(name="Beyo Vintage", time_zone="Europe/Stockholm")
     — fetch-or-create by name (idempotent — safe on retry)
     — existing workspace while `BootstrapState=PENDING` is treated as a valid retry artifact, not corruption
     — workspace_name is NOT user-supplied; it is fixed in the command
     — timezone is fixed and NOT user-supplied in this phase
  10. Fetch or create WorkspaceRole(display_name="Admin", workspace_id=workspace.client_id, role=ADMIN)
     — fetch-or-create by (workspace_id, display_name) — idempotent
  11. Create User if no User with email already exists — raise BootstrapConflict(409) if email taken
     — email uniqueness is global across all workspaces (not workspace-scoped)
      — password hashed with bcrypt before insert
  12. Fetch or create WorkspaceMembership(user_id=user.client_id, workspace_id=workspace.client_id)
      — if membership already exists: verify role matches ADMIN, continue (idempotent)
      — if absent: create with workspace_role_id = WorkspaceRole(ADMIN).client_id
  13. Flip BootstrapState.status = COMPLETED, completed_at = now(), completed_by_id = user.client_id
  14. Write audit event:
      - If audit_logs table exists: write AuditLog(event="bootstrap:admin_created", ...)
      - If not: logger.info(structured bootstrap event)  # TODO: phase-audit-log
  15. Commit

Returns: BootstrapInitResult
  - user_client_id      str
  - workspace_client_id str
  - message             str  ("Bootstrap complete. Sign in via POST /api/v1/auth/sign-in")
  (No JWT returned — explicit sign-in required)
```

**CQRS boundary:** This is a pure command — no read path. The router reads nothing before calling it.
**Token security:** `bootstrap_token` from `incoming_data` is compared but never logged, never stored, and stripped from any error context before raising exceptions.

### Query: `get_bootstrap_status` — `services/queries/bootstrap/get_bootstrap_status.py`

```
incoming_data: none

Returns: {"status": "PENDING" | "COMPLETED", "initialized_at": str | null}
```

Used by health checks and setup-wizard front-ends. Returns state only — no sensitive detail.

---

## 6. Router / API Design

### `routers/setup/setup.py`

```
POST /setup/init
  — No JWT required
  — No role guard
   — Body: {bootstrap_token, email, username, password}
  — Note: workspace_name is NOT in the request body — it is fixed as "Beyo Vintage" in the command
   — Note: workspace timezone is fixed as "Europe/Stockholm" in the command
  — Returns 200: {user_client_id, workspace_client_id, message}
   — Returns 409: if bootstrap already completed, admin already exists, or email is already registered
  — Returns 403: if BOOTSTRAP_TOKEN env var is not set OR token mismatch
   — Returns 422: Pydantic validation failure (including password policy violations)
  (No JWT in response — admin must sign in via POST /api/v1/auth/sign-in)

GET /setup/status
  — No JWT required
  — Returns: {status: "PENDING" | "COMPLETED"}
  — Safe to call at any time — used by frontend setup wizard and health probes

POST /api/v1/auth/register
   — Not implemented
   — Must return 404 (or 405 if route exists but is disabled)
   — Public self-registration/open signup is explicitly prohibited
```

**Router registration rule:** `register_setup_router()` stays mounted permanently (no conditional unmount).
- `/setup/status` is permanently available for frontend and operational diagnostics.
- `/setup/init` is permanently mounted; behavior is state-gated and returns 409 after bootstrap completion.
- Routing lifecycle stays stable across environments; behavior changes by state, not by route presence.

**Rate limiting note:** `/setup/init` must be rate-limited (1 req/min per IP). Implementation via middleware or a simple in-memory TTL guard in the guard layer (full rate-limiting is infra-level, outside this contract).

**Post-bootstrap user creation rule:** After bootstrap is completed, user creation is an authenticated administrative operation only. No public registration endpoint exists. Only callers authorized by `require_role("ADMIN")` may create users through the admin user-management flow.

---

## 7. Bootstrap Lifecycle State Machine

**Enum semantics note:** `BootstrapStateEnum` is intentionally `PENDING | COMPLETED` only.
- `DISABLED` is not persisted in `bootstrap_state.status`.
- `DISABLED` is a derived runtime guard condition when either:
   - `BOOTSTRAP_TOKEN` is missing, or
   - bootstrap guard is disabled by configuration.
- Do not add `DISABLED` as a third persisted enum value.
- This keeps persisted state minimal while still modeling operational behavior in the lifecycle diagram.

```
              ┌─────────────────────────────────┐
              │         BOOTSTRAP DISABLED       │
              │  BOOTSTRAP_TOKEN env not set     │
              │  → 403 on all /setup/* routes    │
              └─────────────────────────────────┘
                            │
                   env var set at startup
                            │
                            ▼
              ┌─────────────────────────────────┐
              │             PENDING              │ ◄── initial migration seed
              │  POST /setup/init available      │
              │  GET /setup/status → PENDING     │
              └─────────────────────────────────┘
                            │
              POST /setup/init (valid secret + valid data)
                            │
              ┌─── atomic row lock ─────────────┐
              │    status = PENDING confirmed    │
              │    all entities created          │
              │    status flipped → COMPLETED    │
              └─────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────────┐
              │           COMPLETED              │
              │  POST /setup/init → 409          │
              │  GET /setup/status → COMPLETED   │
              │  BOOTSTRAP_TOKEN ignored         │
              └─────────────────────────────────┘
```

**Transitions:**
- `DISABLED → PENDING`: env var present + DB row is PENDING (both required)
- `PENDING → COMPLETED`: successful `bootstrap_init` command execution only
- `COMPLETED → *`: **irreversible at application layer** — no HTTP endpoint may reset bootstrap state

### Bootstrap reset — operator-only recovery contract

Bootstrap state reset is a privileged operator procedure. Three permitted methods only:

| Method | When to use | Command |
|---|---|---|
| **Direct DB** | Emergency recovery, DB access already available | `UPDATE bootstrap_state SET status='PENDING', completed_at=NULL, completed_by_id=NULL;` |
| **Alembic migration** | Controlled environment reset (staging, CI) | Write a downgrade step that resets the row |
| **Privileged CLI** | Operator tooling on the server | `make bootstrap-reset` → Typer command `reset_bootstrap_state` (requires `BOOTSTRAP_RESET_SECRET` env var distinct from `BOOTSTRAP_TOKEN`) |

**Explicit prohibitions:**
- No HTTP endpoint (even admin-gated) may reset bootstrap state
- No application-layer code path triggers a `PENDING` reset
- `reset_bootstrap_state` CLI must require a separate env var (`BOOTSTRAP_RESET_SECRET`) to prevent accidental invocation
- Any reset must be logged as a structured warning event before execution: `logger.warning("bootstrap_state reset by operator")`

---

## 8. Security Considerations

### Password Policy (baseline)

To keep this phase deterministic and avoid inconsistent agent behavior, bootstrap password validation is explicitly defined as:

- Minimum length: 8 characters
- No complexity requirements in this phase (no required uppercase/number/symbol rules)
- Validation happens before hashing and before any user insert
- Validation failure returns 422 with a stable message: `password must be at least 8 characters`

This baseline applies to both `POST /setup/init` and `bootstrap-admin` CLI.

| Threat | Mitigation |
|---|---|
| Secret brute force | `hmac.compare_digest` (constant-time); rate limit 1 req/min per IP |
| Race condition — two concurrent `/setup/init` calls | `SELECT FOR UPDATE` row lock on `BootstrapState` |
| Secret leaked in logs | Never log `bootstrap_token`; command strips it before any structured logging |
| Secret leaked in error responses | All error responses use generic messages — never echo input |
| Token stored in DB | Raw `BOOTSTRAP_TOKEN` value is never written to any table — only compared at runtime |
| Replay after completion | DB row status `COMPLETED` is checked under lock — 409 returned immediately |
| BOOTSTRAP_TOKEN committed to source control | Delivery via env var only; `.env.example` shows `BOOTSTRAP_TOKEN=` with no value |
| Password stored in plain text | bcrypt hash inside command before any DB write |
| Weak bootstrap password | Baseline policy enforced: minimum 8 characters before hashing |
| Auth model drift via workspace-scoped identity | Enforce global unique `User.email`; duplicate email fails with 409 |
| Internal integer IDs exposed | Serializer returns only `client_id` — never `id` (contract 18) |
| Bootstrap endpoint left enabled in production | Guard checks env var — removing it from production env permanently disables it |
| Public signup abuse | No self-registration endpoint is exposed; only bootstrap init (pre-completion) and ADMIN-only authenticated user creation (post-completion) are allowed |
| Non-deterministic bootstrap via async side effects | Explicitly forbid queue/websocket/worker/external dispatch during bootstrap; keep command synchronous and transaction-bound |

---

## 9. Failure / Recovery Considerations

| Scenario | Behavior |
|---|---|
| Transaction fails mid-way (e.g. DB connection drop) | Full rollback — `BootstrapState` stays `PENDING`; retry is safe because all creation steps are fetch-or-create |
| Partial failure: roles created, workspace created, user not yet created | Retry hits fetch-or-create for roles and workspace — no duplicates; continues to user creation |
| Workspace already exists while `BootstrapState=PENDING` | Expected in retry-safe flow; bootstrap reuses workspace via fetch-or-create and continues |
| Partial failure: workspace + user created, membership not yet created | Retry fetches existing workspace + user, fetch-or-creates membership — completes cleanly |
| `bootstrap_init` called twice simultaneously | Second call hits row lock, sees `COMPLETED`, returns 409 |
| Bootstrap attempted with an email that already exists globally | Return 409 `email already registered`; no user overwrite or workspace-scoped duplicate allowed |
| Bootstrap command dispatches async side effects | Contract violation — bootstrap must fail review/CI checks; no async dispatch allowed in this phase |
| Env var set but DB has no `BootstrapState` row | Guard raises `BootstrapNotConfigured` (500) — deployment error, operator must run migration |
| Env var removed after initialization | No impact — `COMPLETED` state prevents re-use regardless |
| Admin password forgotten post-bootstrap | CLI fallback: `make reset-admin` → new Typer command `reset_admin_password` (operational CLI, contract 27) |
| Workspace creation succeeds but user creation fails | Transaction rollback — entire graph is atomic |

---

## 10. Suggested Implementation Phases

### Phase A — Foundation (no UI dependency)
1. Add `BootstrapStateEnum` to `domain/bootstrap/enums.py`
2. Add `BootstrapState` model to `models/tables/bootstrap/` (`client_id` PK, FK → `users.client_id`)
3. Register model in `models/__init__.py`
4. Generate and apply migration — includes Alembic seed data: one `PENDING` row with generated `client_id`
5. Add `is_bootstrap_available()` guard to `services/infra/bootstrap/guard.py`
   — checks: `BOOTSTRAP_TOKEN` env var set AND `bootstrap_state.status == PENDING` AND no admin user exists

### Phase B — Command
6. Implement `bootstrap_init` command with full orchestration sequence
   — idempotent role provisioning: ADMIN, MANAGER, SELLER, WORKER (name-based only, no permissions tables)
   — workspace fixed as `"Beyo Vintage"` — not user-supplied
   — one workspace + workspace_role + user + membership
   — atomic state flip
   — conditional audit log (exists → write; absent → structured log + TODO)
7. Implement `get_bootstrap_status` query
8. Unit test command in isolation (mock session + env var)

### Phase C — Router
9. Implement `POST /setup/init` and `GET /setup/status` in `routers/setup/setup.py`
   — response: resource IDs only, no JWT
10. Register setup router in `app/__init__.py` (separate from `register_v1_routers`) and keep it mounted permanently
11. Integration test: full flow HTTP → command → DB → state flip → structured log
12. Integration test router lifecycle invariants:
   — `/setup/status` returns 200 before and after completion
   — `/setup/init` returns 200 when `PENDING`, then 409 when `COMPLETED`

### Phase D — CLI Fallback
12. Add `bootstrap-admin` Typer CLI command (same `bootstrap_init` command, bypasses HTTP)
13. Add `reset-admin-password` Typer CLI command
14. Add `reset-bootstrap-state` Typer CLI command — requires `BOOTSTRAP_RESET_SECRET` env var; logs warning before executing; operator-only
15. Add `make bootstrap-admin`, `make reset-admin-password`, `make bootstrap-reset` targets to Makefile

### Phase E — Documentation & Ops
15. Update `README.md` with bootstrap instructions
16. Add `BOOTSTRAP_TOKEN=` (empty placeholder) to `.env.example`
17. Add setup status to `/health` endpoint: `"bootstrap": "pending" | "completed"`

### Phase F — Deferred (explicit TODOs left in code)
- Full `AuditLog` table integration (`# TODO: phase-audit-log`)
- Granular permissions matrix / RBAC tables (`# TODO: phase-permissions`)
- Additional workspace roles beyond ADMIN (`# TODO: phase-roles-expand`)
- Multi-workspace provisioning API
- Platform workspace / multi-tenant pattern
- Rate limiting at infrastructure level

---

## 11. Pre-Implementation Checklist

- [x] Q1 identity system — `client_id` String(64) is PK and FK target
- [x] Q2 secret delivery — `BOOTSTRAP_TOKEN` env var + DB state; raw token never stored
- [x] Q3 role seeding — idempotent creation inside bootstrap transaction
- [x] Q4 response shape — resource IDs only, no JWT
- [x] Q5 multi-tenant scope — one workspace per bootstrap, extensible later
- [x] Q6 audit log — conditional write; structured log fallback with TODO marker
- [x] Q7 initial workspace — fixed as `"Beyo Vintage"`, not user-supplied
- [x] Q8 role model — name-based only: ADMIN, MANAGER, SELLER, WORKER; no permissions tables
- [x] Q9 first admin role — ADMIN
- [x] Q10 permissions — deferred; architecture extensible but nothing implemented now
- [ ] Contract 24 FK inconsistency updated (`client_id` FK examples already match — confirmed consistent)
- [ ] Plan approved — ready for Phase A implementation

---

**Next state transition:** `REVIEW → APPROVED` — confirm plan is ready to implement.

---

## 12. Contract Reference Map (for implementation agent)

### Always loaded (foundation — all phases)
- [01_architecture.md](../backend/architecture/01_architecture.md) — layer boundaries and dependency rules
- [04_context.md](../backend/architecture/04_context.md) — ServiceContext and service seam
- [05_errors.md](../backend/architecture/05_errors.md) — domain error types and raising conventions
- [21_naming_conventions.md](../backend/architecture/21_naming_conventions.md) — naming rules for files, columns, functions
- [40_identity.md](../backend/architecture/40_identity.md) — `client_id` PK, `IdentityMixin`, FK conventions

### Phase A — Model + migration
- [03_models.md](../backend/architecture/03_models.md) — model structure, mixins, column patterns
- [08_domain.md](../backend/architecture/08_domain.md) — folder structure for domain enums and results
- [30_migrations.md](../backend/architecture/30_migrations.md) — Alembic revision, seed data in migration
- [41_user.md](../backend/architecture/41_user.md) — User model, HistoryRecord mixin
- [28_roles_permissions.md](../backend/architecture/28_roles_permissions.md) — Role model structure (name-based only for this phase)

### Phase B — Command
- [06_commands.md](../backend/architecture/06_commands.md) — command structure, incoming_data, transaction patterns
- [18_security.md](../backend/architecture/18_security.md) — input validation, constant-time compare, secret handling
- [10_auth.md](../backend/architecture/10_auth.md) — password hashing, workspace membership structure
- [17_logging.md](../backend/architecture/17_logging.md) — structured log event format (used for audit fallback)
- [36_audit_log.md](../backend/architecture/36_audit_log.md) — audit entry shape (conditional write if table exists)

### Phase C — Router
- [09_routers.md](../backend/architecture/09_routers.md) — router registration, Depends, error handling
- [20_api_versioning.md](../backend/architecture/20_api_versioning.md) — versioning strategy (setup router is unversioned)
- [46_serialization.md](../backend/architecture/46_serialization.md) — response schema patterns
- [02_app_factory.md](../backend/architecture/02_app_factory.md) — where to register the setup router

### Phase D — CLI fallback
- [27_cli_scripts.md](../backend/architecture/27_cli_scripts.md) — Typer command patterns, make targets

### Phase E — Docs + health
- [31_health_observability.md](../backend/architecture/31_health_observability.md) — adding bootstrap status to /health response

### Phase F — Deferred (do not load yet)
- [28_roles_permissions.md](../backend/architecture/28_roles_permissions.md) — full RBAC section (`# TODO: phase-permissions`)
- [36_audit_log.md](../backend/architecture/36_audit_log.md) — full audit integration (`# TODO: phase-audit-log`)

**Handoff note for implementation agent:**
- All FK declarations must be `String(64), ForeignKey("table.client_id")` throughout.
- The generated bootstrap app uses integer PKs — those models will be aligned as each domain is touched.
- Workspace name `"Beyo Vintage"` is a constant in the command, not an API input.
- Role model is name-based only (`role.name` string comparison). Four base roles: `ADMIN`, `MANAGER`, `SELLER`, `WORKER`. Do not add permissions columns, atoms, groups, or resolution logic in this phase. Leave `# TODO: phase-permissions` where the hook would go.
- `require_roles(["ADMIN"])` decorator in `jwt_dep.py` compares `claims["role_name"]` string — this is the only auth enforcement needed now.
