# Plan — Authenticated ADMIN User Creation Flow

**Lifecycle state:** DRAFT — PENDING CLARIFICATION
**Skill loadout:** plan_lifecycle_orchestrator · planning_contract_selection · ask_clarification_first · goal_intent_alignment
**Primary contracts:** 41, 10, 28, 40
**Supporting contracts:** 01, 02, 03, 04, 05, 06, 07, 08, 09, 17, 18, 21, 27, 31, 36, 46
**Date:** 2026-05-12
**Scope:** Post-bootstrap user creation by authenticated ADMIN only

---

## 1. High-Level Architecture Plan

Goal: after bootstrap completes, user creation is an authenticated administrative operation only.

Core flow:
1. Router endpoint receives request and enforces auth guard via role-name check.
2. Router builds ServiceContext and delegates to a command.
3. Command performs validation, uniqueness checks, role/workspace resolution, and atomic writes.
4. Command writes audit event (or structured fallback if audit table unavailable).
5. Command returns a deterministic result payload (no token issuance in this flow).

Design constraints:
- CQRS-compliant: writes in command, reads in query.
- Synchronous and transaction-bound.
- No websocket dispatch, no queue jobs, no background workers.
- No invitations, no email verification, no password reset in this phase.

---

## 2. Domain Boundaries

Write path:
- services/commands/users/create_user_admin.py
- orchestrates User + WorkspaceMembership + WorkspaceRole assignment

Read path:
- services/queries/users/get_user.py
- services/queries/users/list_users.py (if needed for admin panel)

API boundary:
- routers/api_v1/users.py (or equivalent user-management router)

Infra boundary:
- password hashing through auth/security infra
- audit write through shared audit infra

Out of scope:
- granular RBAC permission graph
- invitation tokens
- password reset lifecycle
- async side-effect orchestration

---

## 3. Required Models/Tables

No new core identity tables required for this phase. Uses existing:
- users
- roles
- workspace_roles
- workspace_memberships
- workspaces
- audit_logs (if present)

Required schema invariants (must exist at DB level):
- users.email UNIQUE (global)
- roles.name UNIQUE
- workspace_roles(workspace_id, display_name) UNIQUE
- workspace_memberships(user_id, workspace_id) UNIQUE

Identity model:
- client_id is the persisted PK/FK identity style used by contracts in this plan.

---

## 4. Required Commands/Queries

### Command: create_user_admin

Input contract:
- email (required, globally unique)
- username (required)
- password (required, minimum 8 characters)
- workspace_client_id (required unless fixed by current admin context policy)
- workspace_role_client_id OR role_name (one required; see clarification)

Execution responsibilities:
1. Verify caller claims include role_name=ADMIN.
2. Validate payload and password baseline policy.
3. Resolve workspace and target WorkspaceRole.
4. Enforce global email uniqueness.
5. Hash password before persistence.
6. Create User.
7. Create WorkspaceMembership linking user to selected WorkspaceRole in workspace.
8. Write audit event.
9. Return created user and membership identifiers.

Transaction boundary:
- Entire command runs in one DB transaction.
- No partial commits allowed.
- User + membership + audit write succeed/fail together.

Synchronous-only rule:
- No background jobs, queue dispatch, websocket broadcast, external webhook/email side effects.

### Queries

Minimum:
- get_user (admin read for created user)

Optional for immediate admin UX:
- list_workspace_roles_for_workspace (read role options)
- list_users_for_workspace

---

## 5. Router/API Design

Proposed endpoints:
- POST /api/v1/users
- GET /api/v1/users/{user_client_id}
- GET /api/v1/users (optional list)

Auth requirements:
- Require JWT claims.
- Require ADMIN role via existing role-name guard strategy.

Request/response behavior:
- POST returns 201 with user + membership ids and display fields.
- Duplicate email returns 409.
- Invalid role/workspace references return 404 or 422 per error taxonomy.
- Validation errors return 422.

Explicit prohibitions:
- No public registration endpoint.
- No open signup route.

---

## 6. Validation and Security Rules

Validation boundaries:
- Router validates request schema shape.
- Command validates business rules and cross-entity consistency.

Password policy (baseline for this phase):
- Minimum length 8 characters.
- No extra complexity requirements in this phase.
- Hash before persistence, never store plaintext.

Identity/security rules:
- User.email globally unique.
- Role assignment is workspace-scoped through WorkspaceMembership -> WorkspaceRole.
- One role per membership.
- Role checks operate via claims.role_name string comparison.

Operational safety:
- Structured logs redact sensitive payload fields.
- Token/credential values never logged.

---

## 7. Failure/Recovery Considerations

Failure cases:
- Duplicate email: deterministic 409, no writes.
- Workspace not found: 404, no writes.
- WorkspaceRole not found or mismatched to workspace: 422/404, no writes.
- Transaction error mid-write: rollback entire operation.
- Audit table unavailable: fallback structured log (if this fallback policy is approved).

Replay/idempotency notes:
- Identical retries with same email should return 409 after first success.
- No partial membership-only or user-only persistence allowed.

---

## 8. Suggested Implementation Phases

Phase A — Command + domain contracts
1. Define request/result dataclasses or schemas.
2. Implement create_user_admin command with atomic transaction.
3. Add uniqueness and membership validations.

Phase B — Router
4. Add POST /api/v1/users with ADMIN guard.
5. Add minimal read endpoint(s) for admin verification.

Phase C — Audit + observability
6. Add audit event write integration.
7. Add structured logging around create attempts and outcomes.

Phase D — Tests
8. Unit tests for command branches (success, duplicate email, invalid role/workspace).
9. Integration tests for router auth guard and transaction behavior.

Phase E — Ops/docs
10. Update operational docs: no public signup, ADMIN-only creation path.
11. Add CLI parity only if explicitly required later.

---

## 9. Clarification Questions Before Implementation Begins

1. Input contract: should admin provide workspace_role_client_id directly, or role_name + workspace_client_id and command resolves role mapping?
2. Workspace scope: can ADMIN create users in any workspace, or only in the admin caller's active workspace claim?
3. Username uniqueness: should username be globally unique, workspace-unique, or non-unique for now?
4. Audit strictness: if audit_logs table is unavailable, should command fail hard or use structured log fallback and still succeed?
5. API surface: do you want user creation endpoint under users router only, or under an admin router namespace?
6. Initial activation: should this flow be available immediately after bootstrap completion without extra feature flag?
7. Serializer shape: return only client_id references, or include compact role/workspace projections in create response?

---

**Next transition:** DRAFT -> REVIEW after clarification answers are confirmed.
