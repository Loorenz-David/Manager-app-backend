# PLAN_reset_bootstrap_20260515

## Metadata

- Plan ID: `PLAN_reset_bootstrap_20260515`
- Status: `implemented_and_validated`
- Owner agent: `GitHub Copilot`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T00:00:00Z`
- Related issue/ticket: `cleanup bootstrap data`
- Intention plan: (none)

## Goal and intent

- Goal: Implement a reset/clear endpoint that deletes all bootstrap-created data in a single atomic transaction, restoring the workspace to pre-bootstrap state.
- Business/user intent: Enable developers to easily reset the database during development/testing without manual cleanup.
- Non-goals: Selective deletion, data archival, audit trail preservation for deleted bootstrap data.

## Scope

- In scope: 1 reverse-orchestrator + 27 reverse-phase files + 1 optional orphan-bootstrap-user cleanup phase + 1 default orphan-bootstrap-role cleanup phase + 1 router + 1 config field + event dispatch.
- Out of scope: Multi-workspace deletion, soft-delete reversal.
- Assumptions:
  - Workspace exists in DB before reset is called.
  - Only deletes workspace-scoped data; global entities remain (notably `users` and global `roles`).
  - DELETE operations use hard-delete (not soft-delete reversal).
  - Idempotent: `DELETE WHERE workspace_id = ...` — if data doesn't exist, query succeeds with 0 rows affected.
  - Same secret-header pattern as bootstrap, via `RESET_SECRET` env var (optional; if empty/missing, endpoint returns 501 Not Implemented).

## Implementation plan

### 1. Config & Environment

- Add `reset_secret: str = Field(default="")` to `config.py` `Settings` class.
- Add `RESET_SECRET=` to `.env.example` (empty by default, must be set to enable).
- If `reset_secret` is empty string, the reset router returns `501 Not Implemented`.

### 2. Reset Router (`routers/api_v1/reset.py`)

- Single endpoint: `DELETE /api/v1/reset`.
- Required query param: `workspace_id`.
- Optional query param: `delete_orphan_bootstrap_users` (default `true`). Use `false` to preserve orphan bootstrap users.
- Accepts `X-Reset-Secret` header.
- If header missing or secret doesn't match `settings.reset_secret`, return `403 Forbidden`.
- If `settings.reset_secret` is empty, return `501 Not Implemented` before checking header.
- Call `reset_app(ctx)` command.
- Return `{"data": {"workspace_id": "<id>", "delete_orphan_bootstrap_users": <bool>, "deleted_orphan_bootstrap_roles": <int>}, "ok": true, "warnings": []}` on success.

### 3. Reset Orchestrator (`services/commands/reset/reset_app.py`)

- Single async function `async def reset_app(ctx: ServiceContext) -> dict`.
- Validates `ctx.workspace_id` is set (if empty, raise `ValidationError`).
- Single `async with ctx.session.begin()` block.
- Calls 27 reset phases in dependency-aware deletion order (bootstrap + operational data).
- By default, performs orphan bootstrap admin cleanup. Set `delete_orphan_bootstrap_users=false` to skip.
- Dispatches events after transaction commit using `WorkspaceEvent(event_name="workspace:reset", client_id=workspace_id, workspace_id=workspace_id)`.
- Also deletes orphan bootstrap global roles (`admin`, `worker`, `manager`, `seller`) after `workspace_roles` cleanup.
- Returns `{"workspace_id": <id>, "delete_orphan_bootstrap_users": <bool>, "deleted_orphan_bootstrap_roles": <int>}`.

### 4. Reset Phases (27 files, implemented)

Each phase:
- Accepts `(session: AsyncSession, workspace_id: str)`.
- Uses `DELETE FROM <table> WHERE workspace_id = <id>` (or similar scope filter).
- Silent success if no rows exist (idempotent).
- No ORM relationship access (`lazy="raise"` enforced).

Deletion order (reverse dependency):
1. `delete_issue_category_configs.py`: Hard-delete all `IssueCategoryConfig` rows.
2. `delete_working_section_item_categories.py`: Hard-delete all `WorkingSectionItemCategory` rows.
3. `delete_working_section_supported_issue_types.py`: Hard-delete all `WorkingSectionSupportedIssueType` rows.
4. `delete_working_section_dependencies.py`: Hard-delete all `WorkingSectionDependency` rows.
5. `delete_working_sections.py`: Hard-delete all `WorkingSection` rows.
6. `delete_issue_severities.py`: Hard-delete all `IssueSeverity` rows.
7. `delete_issue_types.py`: Hard-delete all `IssueType` rows.
8. `delete_item_categories.py`: Hard-delete all `ItemCategory` rows.
9. `delete_task_history_records.py`: Hard-delete all `TaskHistoryRecord` rows.
10. `delete_task_events.py`: Hard-delete all `TaskEvent` rows.
11. `delete_step_state_records.py`: Hard-delete all `StepStateRecord` rows.
12. `delete_task_step_assignment_records.py`: Hard-delete all `TaskStepAssignmentRecord` rows.
13. `delete_task_step_dependencies.py`: Hard-delete all `TaskStepDependency` rows.
14. `delete_task_steps.py`: Hard-delete all `TaskStep` rows.
15. `delete_task_items.py`: Hard-delete all `TaskItem` rows.
16. `delete_tasks.py`: Hard-delete all `Task` rows.
17. `delete_upholstery_inventories.py`: Hard-delete all `UpholsteryInventory` rows.
18. `delete_upholstery_inventory_threshold_policies.py`: Hard-delete all `UpholsteryInventoryThresholdPolicy` rows.
19. `delete_upholsteries.py`: Hard-delete all `Upholstery` rows.
20. `delete_static_costs.py`: Hard-delete all `StaticCost` rows.
21. `delete_working_section_memberships.py`: Hard-delete all `WorkingSectionMembership` rows.
22. `delete_user_shift_state_records.py`: Hard-delete all `UserShiftStateRecord` rows.
23. `delete_workspace_memberships.py`: Hard-delete all `WorkspaceMembership` rows.
24. `delete_audit_logs.py`: Hard-delete all `AuditLog` rows.
25. `delete_pending_uploads.py`: Hard-delete all `PendingUpload` rows.
26. `delete_workspace_roles.py`: Hard-delete all `WorkspaceRole` rows.
27. `delete_workspace.py`: Hard-delete the `Workspace` row itself.

Important correction:
- `delete_users.py` is now a safe optional cleanup phase that only deletes configured bootstrap admin user(s)
  when they have zero remaining workspace memberships.

### 5. Router Registration

- Import reset router in `routers/api_v1/__init__.py`.
- Register: `include_router(reset.router, prefix="/api/v1/reset", tags=["reset"])`.

### 6. Event Dispatch

- Event name: `"workspace:reset"`.
- Event object: `WorkspaceEvent`.
- Dispatch after transaction completes (same pattern as bootstrap).

## Implementation summary

- Endpoint implemented at `DELETE /api/v1/reset?workspace_id=<id>` with `X-Reset-Secret`.
- Default behavior deletes orphan bootstrap users. Override mode to preserve users:
  `DELETE /api/v1/reset?workspace_id=<id>&delete_orphan_bootstrap_users=false`.
- Router is registered in API v1 router setup.
- `RESET_SECRET` support added to settings and env templates.
- Reset now clears both bootstrap tables and workspace operational tables that hold FKs to `workspaces`.
- FK blockers resolved during implementation by adding explicit phases for:
  - `audit_logs`
  - `pending_uploads`
- Event dispatch bug fixed by sending a typed domain event (`WorkspaceEvent`) instead of a plain dict.
- Optional orphan bootstrap user deletion implemented with strict safety guards:
  - candidate must match configured bootstrap email and/or username
  - candidate must have zero remaining rows in `workspace_memberships`
- Orphan bootstrap role deletion implemented by default with strict safety guard:
  - role name in `{admin, worker, manager, seller}`
  - role has zero remaining rows in `workspace_roles`

## Acceptance criteria

1. `DELETE /api/v1/reset` with correct `X-Reset-Secret` returns `200 OK`, `{"data": {"workspace_id": "<id>", "delete_orphan_bootstrap_users": <bool>, "deleted_orphan_bootstrap_roles": <int>}, "ok": true, "warnings": []}`.
2. Calling delete removes bootstrap and operational workspace-scoped rows for the target workspace.
3. Idempotent: second call also returns `200 OK` (no error on DELETE of already-deleted data).
4. Missing/wrong secret returns `403 Forbidden`.
5. Empty `RESET_SECRET` env var returns `501 Not Implemented`.
6. By default, global entities (`users`, global `roles`) are preserved.
7. Optional mode can delete only orphaned bootstrap admin user(s): `delete_orphan_bootstrap_users=true`.
8. Event `workspace:reset` dispatched after deletion.

## Validation evidence (live)

- API health check: `200 OK`.
- Wrong-secret call: `403 Forbidden` with `{"detail":"Invalid or missing reset secret."}`.
- Successful call: `200 OK` with `{"data":{"workspace_id":"ws_01KRNY6KW77BRK9949Q4PB38YD"},"ok":true,"warnings":[]}`.
- Successful optional-mode call (after server restart):
  `{"data":{"workspace_id":"ws_01KRNZ5SBKBV8MRSM42G3QCXRG","delete_orphan_bootstrap_users":true},"ok":true,"warnings":[]}`.
- Verified before/after counts for target workspace (`ws_01KRNY6KW77BRK9949Q4PB38YD`):
  - `workspaces`: `1 -> 0`
  - `workspace_roles`: `4 -> 0`
  - `workspace_memberships`: `1 -> 0`
  - `issue_types`: `9 -> 0`
  - `issue_severities`: `3 -> 0`
  - `item_categories`: `34 -> 0`
  - `working_sections`: `13 -> 0`
  - `issue_category_configs`: `279 -> 0`
  - `working_section_supported_issue_types`: `27 -> 0`
  - `working_section_item_categories`: `178 -> 0`
  - `working_section_dependencies`: `15 -> 0`
  - `audit_logs`: `0 -> 0`
  - `pending_uploads`: `0 -> 0`
- Verified optional user cleanup result (bootstrap admin `admin@beyo.dev`):
  - `user_count`: `1 -> 0`
  - `membership_count`: `1 -> 0`
- Verified role cleanup result:
  - `roles(admin,worker,manager,seller)`: `4 -> 0`
  - reset response included `"deleted_orphan_bootstrap_roles": 4`

## Contracts and skills

- `04_context.md`: `ServiceContext` — `ctx.workspace_id` must be set (identity from request path or default from bootstrap-context).
- `05_errors.md`: `ValidationError` for missing/invalid workspace_id.
- `06_commands.md`: Orchestrator pattern — single transaction, phases, event dispatch.
- `09_routers.md`: Router skeleton — secret header guard, `run_service`, `build_ok`/`build_err`.
- `21_naming_conventions.md`: Phase files named `delete_<domain>.py`; orchestrator named `reset_app.py`.
