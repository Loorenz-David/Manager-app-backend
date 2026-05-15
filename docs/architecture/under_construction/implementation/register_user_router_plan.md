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
  Implement an authenticated `POST /api/v1/auth/register` endpoint that allows an admin in a workspace to create a new user in that same workspace, with membership and role assignment created atomically.
- Business/user intent:
  Enable admin-managed user onboarding (not public self-registration) while enforcing tenant boundaries and existing RBAC rules.
- Non-goals:
  Email verification, invite links, password reset, auto-login on register, multi-workspace assignment at creation, RBAC graph redesign, background event fanout.

## Scope

- In scope:
  Router handler wiring in `auth` router, register-user command, request parser, domain validators/guards, role resolution with workspace constraint, uniqueness checks, password hashing, atomic user + membership write, shared user profile serializer reuse/creation.
- Out of scope:
  Any auth flow changes outside register path (`sign-in`, refresh, logout), migration strategy changes, frontend flows, infra queues/workers.
- Assumptions:
  `require_roles` and `ADMIN` remain authoritative for role guard decisions; user creation can proceed once role resolution and uniqueness checks pass.

## Clarifications required

- [ ] Should username uniqueness be enforced strictly per workspace (recommended by this plan) or globally? — This affects conflict checks and must be finalized before implementation to avoid behavioral drift.
- [ ] Should the register endpoint return `200 OK` (current router style) or `201 Created` for new resource semantics? — This affects API contract/testing expectations.

## Acceptance criteria

1. `POST /api/v1/auth/register` exists in `beyo_manager/routers/api_v1/auth.py` and is protected by `require_roles([ADMIN])`.
2. Request body accepts only `username`, `email`, `password`, `phone_number`, `role_id`; `workspace_id` is never accepted from body.
3. Command resolves `WorkspaceRole` scoped to `ctx.workspace_id`; cross-workspace role lookup returns `NotFound("Workspace role not found.")`.
4. Duplicate email returns `Conflict("A user with this email already exists.")`.
5. Duplicate workspace username returns `Conflict("Username already taken in this workspace.")` (subject to clarification above).
6. Password is hashed before any `session.add(...)` call; plaintext password is never persisted/serialized/logged.
7. `User` and `WorkspaceMembership` are inserted inside one `async with ctx.session.begin()` transaction; no partial commit is possible.
8. Route returns `{"user": serialize_user_profile(user)}` and serializer output excludes password/hash/internal sensitive fields.
9. Unauthorized request to `/auth/register` returns `401`; authenticated non-admin returns `403`.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: Layer map, dependency boundaries, domain grouping by vertical slice.
- `backend/architecture/03_models.md`: ORM conventions used by `User`, `WorkspaceMembership`, and `WorkspaceRole` writes/reads.
- `backend/architecture/04_context.md`: `ServiceContext` ownership of identity/session/incoming_data and `ctx.workspace_id` source-of-truth.
- `backend/architecture/05_errors.md`: `DomainError` hierarchy and required conversion from validation/runtime errors.
- `backend/architecture/06_commands.md`: Write-path command structure, request parsing discipline, transaction boundaries.
- `backend/architecture/07_queries.md`: Read-path/serialization patterns to keep response assembly outside router.
- `backend/architecture/08_domain.md`: Pure domain functions for guards/validators without I/O.
- `backend/architecture/09_routers.md`: Router handler skeleton and service invocation pattern.
- `backend/architecture/10_auth.md`: JWT claims and role-based access policy for protected routes.
- `backend/architecture/21_naming_conventions.md`: Naming for files/functions/fields.
- `backend/architecture/24_multi_tenancy.md`: Workspace-scoping rules and membership role model.
- `backend/architecture/25_soft_delete.md`: Soft-delete consistency invariants.
- `backend/architecture/40_identity.md`: `client_id` strategy and identity generation expectations.
- `backend/architecture/41_user.md`: User model and user-history conventions.

### Local extensions loaded

- `backend/architecture/40_identity_local.md`: App-specific identity constraints/delta for this codebase.
- `backend/architecture/41_user_local.md`: App-specific user model/behavior deltas for this codebase.
- No local extension files were found for 01, 03, 04, 05, 06, 07, 08, 09, 10, 21, 24, or 25 at plan-writing time.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** -> read contracts (`06_commands.md`, `09_routers.md`, etc.).
- **What exists** -> implementation reads are valid (current endpoint naming, package paths, serializer availability, model field names).

Read order:
- `backend/architecture/<canonical>.md` (baseline)
- `backend/architecture/<canonical>_local.md` (app delta, if present)

Applied precedence:
- Local extension overrides canonical baseline only for this app.

### Skill selection

- Primary skill: `backend/task_system/backend_contract_goal_mapping_guide.md` (document-only protocol and contract resolution discipline).
- Router trigger terms: `auth`, `register`, `admin`, `workspace`, `role_id`, `multi-tenancy`.
- Excluded alternatives: Runtime/worker skills were excluded because this plan has no queue/replay/worker scope.

## Implementation plan

1. Add `RegisterUserBody` to `beyo_manager/routers/api_v1/auth.py` and wire `@router.post("/register")` with:
   - `claims: dict = Depends(require_roles([ADMIN]))`
   - `session: AsyncSession = Depends(get_db)`
   - `ctx = ServiceContext(identity=claims, incoming_data=body.model_dump(), session=session)`
   - `outcome = await run_service(register_user, ctx)`
   - `return build_ok(outcome.data) if outcome.success else build_err(outcome.error)`
2. Create request parser module:
   - `beyo_manager/services/commands/users/requests/register_user_request.py`
   - `RegisterUserRequest` Pydantic model:
     - `username`: strip and non-blank
     - `email`: lowercase + strip
     - `password`: min length 8 (and domain validator call)
     - `phone_number`: optional
     - `role_id`: non-blank
   - `parse_register_user_request(data)` converts Pydantic `ValidationError` to `ValidationFailed`.
3. Create domain validation/guard modules:
   - `beyo_manager/domain/users/user_validators.py`
   - `beyo_manager/domain/users/user_guards.py`
   - Keep pure functions only (no DB, no service/model imports).
4. Create command module `beyo_manager/services/commands/users/register_user.py`:
   - Parse request.
   - Validate email/password format via domain validators.
   - Resolve role by `role_id` in `ctx.workspace_id` only; raise `NotFound` on mismatch/miss.
   - Check email uniqueness globally.
   - Check username uniqueness in workspace.
   - Hash password using existing auth hashing infra.
   - Execute one `async with ctx.session.begin()` block for:
     - user insert
     - membership insert (`workspace_id=ctx.workspace_id`, `workspace_role_id=resolved_role.id`, `invited_by_id=ctx.user_id`)
     - flush as needed
   - Return `{"user": serialize_user_profile(user)}`.
5. Ensure shared profile serializer exists:
   - If missing, create `beyo_manager/services/queries/users/serialize_user_profile.py`.
   - Reuse in register command return path and user profile query path for one canonical user payload shape.
6. Update package `__init__.py` exports where needed so imports remain stable and lint/type checks pass.

## Risks and mitigations

- Risk: Inconsistent response shape if register returns inline dict while profile query uses another serializer.
  Mitigation: Enforce single `serialize_user_profile` module and reuse it in both paths.
- Risk: Cross-workspace role probing leaks tenant information.
  Mitigation: Always raise generic `NotFound("Workspace role not found.")` when role not in caller workspace.
- Risk: Partial writes create orphan users without memberships.
  Mitigation: Single transaction block for both inserts.
- Risk: Hidden plaintext password leakage through logs/debug artifacts.
  Mitigation: Hash before persistence, avoid logging request payload fields containing password.
- Risk: Contract drift from generic namespace examples (`my_app.errors`) to real app package.
  Mitigation: Use concrete package paths under `beyo_manager/*` in implementation.

## Validation plan

- `POST /api/v1/auth/sign-in` with bootstrap admin credentials: obtain bearer token with admin role claims.
- `POST /api/v1/auth/register` (admin token): returns success and user payload from shared serializer.
- `POST /api/v1/auth/sign-in` as newly created user: login succeeds with expected workspace/role claims.
- `POST /api/v1/auth/register` using new user token:
  - If role is admin -> success.
  - If role is non-admin -> `403 Forbidden`.
- `POST /api/v1/auth/register` without token -> `401 Unauthorized`.
- Negative validation checks:
  - short password -> `400 ValidationFailed`
  - invalid email format -> `400 ValidationFailed`
  - duplicate email -> `409 Conflict`
  - duplicate username in workspace -> `409 Conflict`
  - role not in workspace -> `404 NotFound`

## Review log

- `2026-05-15` `GitHub Copilot`: Restructured plan to match `TEMPLATE_PLAN.md`, aligned paths to real app package layout (`backend/app/beyo_manager/...`), and tightened contract-driven implementation checklist.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `GitHub Copilot (GPT-5.3-Codex)`
