# SUMMARY_batch_step_transition_20260623

## Metadata

- Summary ID: `SUMMARY_batch_step_transition_20260623`
- Status: `summarized`
- Owner agent: `claude-opus-4-8`
- Created at (UTC): `2026-06-23T12:15:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_batch_step_transition_20260623.md`
- Related debug plan (optional): `—`

## What was implemented

- Added `POST /api/v1/tasks/steps/transition-batch`, a workspace-scoped endpoint that transitions 1..N batch-capable task steps to one target state atomically (all-or-nothing), with batched I/O and coalesced realtime events/notifications.
- Implemented Option B: the existing single-step `transition_step_state` command and endpoint were left functionally untouched (only a drift-warning docstring added). The batch path uses a separate, faithfully-mirrored core `_apply_step_transition`.
- The transition-rules map `_ALLOWED_TRANSITIONS` is single-sourced from `transition_step_state` (imported by the batch command), so the legal-transition table cannot drift between the two paths.
- Only batch-capable steps (`allows_batch_working = true`) are accepted; the one-active-step auto-pause guard never fires in the batch path.
- Per-item `mark_closing_record_inaccurate` is supported (follow-up after initial implementation): each item may flag its closing record (and, for `completed`, the new record) as inaccurate, mirroring the single endpoint's flag.

## Files changed

- `backend/app/beyo_manager/services/commands/task_steps/requests/__init__.py`: added `BatchTransitionItem`, `BatchTransitionStepStateRequest` (non-empty, max 100, no duplicate `step_id`), and `parse_batch_transition_step_state_request`.
- `backend/app/beyo_manager/services/commands/task_steps/_step_transition_core.py` (new): transaction-free, dispatch-free `_apply_step_transition` + `StepTransitionApplied` result; mirrors the single endpoint's per-step sub-processes (state machine, record close/open, metrics, terminal handling, task side-effects, per-step `PROCESS_STEP_TRANSITION` outbox); returns resolved step-pin recipients for the caller to coalesce. Carries the reciprocal drift-warning comment.
- `backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py`: added a drift-warning docstring note only (no behavioral change).
- `backend/app/beyo_manager/services/commands/task_steps/transition_step_state_batch.py` (new): top-level command — single `maybe_begin`, batched loads (steps/tasks/open-records via `IN`), two-phase validate-then-apply (atomic), coalesced notifications, and a single post-commit dispatch of one `task:step-state-changed` BatchWorkspaceEvent plus one `task:state-changed` per distinct changed task.
- `backend/app/beyo_manager/routers/api_v1/tasks.py`: added `_BatchTransitionItemBody` / `_BatchTransitionStepBody` and `POST /steps/transition-batch` → `transition_step_state_batch` (roles admin/manager/worker). No conflict with `/{task_id}/...` routes.
- `backend/app/tests/integration/services/commands/task_steps/test_batch_step_transition_command_integration.py` (new): DB-backed coverage for the four transitions, cross-task batch, atomic rejection, non-batch rejection, single coalesced event, and task→ready.
- `backend/app/tests/unit/services/commands/task_steps/test_batch_transition_request.py` (new): request-validator coverage (valid, empty, duplicate, >100).
- `backend/app/tests/integration/services/commands/task_steps/test_batch_working_step_transition_integration.py`: fixed pre-existing broken seeding (FK ordering for user→task, and missing `WorkingSection` rows) so the prior plan's integration tests run green. No production code involved.
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_batch_step_transition_20260623.md` (new): frontend contract for the endpoint.

## Contract adherence

- `backend/architecture/06_commands.md` + `06_commands_local.md`: business logic in commands; one `maybe_begin` transaction owns the whole batch; the core is dispatch-free and only the top-level batch command dispatches events after commit (subordinate-command event rule).
- `backend/architecture/05_errors.md`: typed `ValidationError` for the atomic per-item rejection.
- `backend/architecture/09_routers.md`: router only wires the request body and delegates to `run_service`.
- `backend/architecture/11_infra_events.md` / `13_sockets.md` / `42_event.md`: reused `create_instant_task` outbox + a single coalesced `BatchWorkspaceEvent`.
- `backend/architecture/22_*` (bulk/batch write): batched `IN` loads keep validation query count independent of N. Per-step `PROCESS_STEP_TRANSITION` outbox rows are inherently one-per-step and are emitted via the established `create_instant_task` API (not a single bulk insert) for fidelity with the single endpoint — see Known gaps.
- `backend/architecture/15_testing.md`: integration tests mirror the existing task_steps integration style; unit test for the validator.

## Validation evidence

- `cd app && PYTHONPATH=. .venv/bin/python -m compileall beyo_manager`: clean.
- `cd app && PYTHONPATH=. .venv/bin/pytest tests/integration/services/commands/task_steps tests/unit/services/commands/task_steps`: `26 passed` (includes a per-step `mark_closing_record_inaccurate` completion test).
- Route registration verified: `/api/v1/tasks/steps/transition-batch` present on the tasks router; batch command imports cleanly.

## Known gaps or deferred items

- Per-step outbox/notification-target resolution still runs per step in Phase 2 (one `create_instant_task` and one `resolve_task_step_notification_targets` per step, plus the per-step all-steps-terminal check for terminal transitions). This is O(N) writes/reads, which is inherent (one analytics row per step) and kept this way for faithful parity with the single endpoint. The validation loads (steps/tasks/open-records) are batched. If very large batches become common, these per-step calls are the place to optimize.
- Coalesced step notification uses generic copy ("N steps changed to <state>") without a per-step deep-link entity, by design. Task-state notifications keep their entity link. Documented in the handoff.
- Per-item `mark_closing_record_inaccurate` IS supported (follow-up to the original plan, which had deferred it): each item may flag its closing record (and, for `completed`, the new record) as inaccurate. v1 still does not support per-item `credited_user_id` or heterogeneous per-item `new_state`.
- Option B keeps two implementations of the per-step sub-processes (`transition_step_state` and `_apply_step_transition`) in sync by convention: reciprocal drift-warning comments + the shared `_ALLOWED_TRANSITIONS` map. There is no automated cross-implementation parity assertion; behavioral coverage is via both suites.

## Handoff notes (if needed)

- To frontend: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_batch_step_transition_20260623.md`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_batch_step_transition_20260623.md`
```
