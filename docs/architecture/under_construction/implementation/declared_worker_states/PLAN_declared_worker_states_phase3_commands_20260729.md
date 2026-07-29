# PLAN_declared_worker_states_phase3_commands_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase3_commands_20260729`
- Status: `under_construction`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T12:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (decisions D2, D5, D7, D9, D10 govern this phase)
- Prerequisite: Phase 2 archived (the whole derived pipeline already understands declared rows).

## Goal and intent

- Goal: Ship the write path — workers declare and close states via new commands + routes; declaring auto-pauses open working steps under the declared reason; `/pause` + `/resume` (and their commands, and the reconcile's legacy stickiness carve-out) are retired.
- Business/user intent: This is the phase where a worker can finally say "I'm cleaning / in a meeting / loading the truck" and have both the live timeline and step analytics tell that story from the manager-editable catalog.
- Non-goals: Clock routes / current-state endpoint (Phase 4). Device auth / kiosk identification (Phases 5–6). Data migration of legacy manual rows (D7 — never).

## Scope

- In scope:
  1. Command `services/commands/users/declare_worker_state.py`.
  2. Command `services/commands/users/close_declared_worker_state.py`.
  3. Routes on `routers/api_v1/worker_shifts.py`: `POST /declared-states` (declare) and `POST /declared-states/close` — `require_roles([ADMIN, MANAGER, WORKER])` with the **same on-behalf matrix as clock actions** (D10 rev 2): both bodies accept optional `user_id`; target resolution via `resolve_worker_shift_target(ctx, request.user_id)` (worker = self only; admin/manager must name a worker).
  4. Retirement: delete `pause_worker_shift.py`, `resume_worker_shift.py`, the `/pause` and `/resume` routes, and the reconcile's legacy manual-pause stickiness carve-out (declared precedence from Phase 2 replaces it). Update/replace their tests.
  5. Serializer for the declared-state response payload (domain serializer per `46_serialization.md` conventions).
  6. Docs: `models/tables/users/README.md` — replace the stale state-machine section (it predates `IDLE`) with the real machine incl. declared states; document `manually_recorded`'s redefined meaning (D3) and the retirement of manual pause.
- Out of scope: reasons-listing changes (Phase 4 checks whether `list_pause_reasons` needs a `pause_type` filter).
- Assumptions:
  - **Declare command flow** (all inside `maybe_begin(ctx.session)`, lock order from Phase 2: shift row → declared row):
    1. Parse `{user_id: str | None, pause_reason_id: str, description: str | None}` (pydantic; strip/length-bound description at 512).
    2. Resolve target via `resolve_worker_shift_target(ctx, request.user_id)` (worker self-only; admin/manager on-behalf; target must be an active workspace WORKER — all existing semantics, D10 rev 2).
    3. `load_open_worker_shift_for_update(...)` — `None` → `ConflictError("Worker must be clocked in to declare a state.")` (D9).
    4. Load the reason: same workspace, `is_deleted IS FALSE` → else `NotFound`. `pause_type != PERSONAL` → `ValidationError` (D2 — BLOCKER reasons are step-blockers, not declarable). `requires_description` and no description → `ValidationError`.
    5. Load open declared row `with_for_update()`; if present → close it (`exited_at = now`, `closed_by_id = ctx.user_id`) — the "switch" behavior (D5). (`ctx.user_id` is the acting account — the device's manager identity when on-behalf; `user_id`/`created_by_id` capture the worker vs. actor split.)
    6. Auto-pause open working steps: reuse `_load_open_working_step_rows(session, workspace_id, user_id)` + `_apply_step_transition(...)` per row with `new_state=TaskStepStateEnum.PAUSED`, `pause_reason_id = <declared reason>`, `description=None`, `credited_user_id = user_id`, `now=now` — exactly the clock-out pattern in `_clock_worker_shift.py`, different target state and reason (D5). These transitions emit their normal analytics events; the async reconcile they trigger is idempotent against step 8.
    7. Insert `UserDeclaredStateRecord(entered_at=now, exited_at=None, created_by_id=ctx.user_id, ...)`.
    8. Call `reconcile_worker_shift_state(session, workspace_id, user_id, now)` synchronously (subordinate, same session) so the live derived state flips to declared-`IN_PAUSE` immediately — worker UX must not depend on analytics-worker latency.
    9. Return `{declared_state: <serialized row + reason name>, shift_state: <outcome.state.value>, paused_steps: <count from step 6>}`.
  - **Close command flow**: parse `{user_id: str | None}` → resolve target via `resolve_worker_shift_target(ctx, request.user_id)` → load open declared row `with_for_update()` → `None` → `ConflictError("No declared state is open.")` → close (`exited_at = now`, `closed_by_id = ctx.user_id`) → synchronous reconcile (lands on `IDLE`, or `WORKING` if a step is somehow open) → return `{shift_state, closed_declared_state_id}`.
  - **Carve-out removal is safe**: after this phase nothing writes `manually_recorded=True` directly to `user_shift_state_records` (only the reconcile/reconstruction emit it, sourced from declared rows). A worker mid-manual-pause **at deploy time** keeps their open manual `IN_PAUSE` row; without the carve-out the next reconcile would flip it to `IDLE`. Accepted: one-time, cosmetic-only (clock-out rebuild still folds the manual row correctly per D7). Note it in the deploy notes of the implemented summary.
  - Route naming `POST /declared-states` / `POST /declared-states/close` — default, veto in review.
  - Request/response shapes must match `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` (the frontend is built against it in parallel); a conflict between this plan and the handoff is an operator decision, not an implementer choice.

## Clarifications required

- [x] Can a worker declare while a *step-sourced* pause is live (blocker open, no working steps)? — resolved: yes; nothing to auto-pause; declared outranks step pause in derivation (D4).
- [x] Does closing a declaration resume the auto-paused steps? — resolved: **no**. Steps stay paused (paused-step resumption is an explicit worker action on the task, existing flow); the shift lands back on `IN_PAUSE` (step-sourced) or `IDLE` per derivation. The declare response's `paused_steps` count lets the frontend prompt the worker.
- [x] Free-text-only declaration (no catalog reason)? — resolved: not supported; catalog + `description` covers it (D2).
- [x] On-behalf declare/close? — resolved 2026-07-29 (rev 2): yes, same matrix as clock actions (D10 rev 2) — required by the shop-floor device (D13).
- [x] **Pinned from the Phase 2 review (Opus, findings F4/F6 — MUST be addressed in this phase, not assumed away):**
  - **F4 (carve-out trap):** Phase 2's retained legacy carve-out no-ops when the current open record is `IN_PAUSE` + `manually_recorded` and target is `IDLE` — but the reconcile itself now *authors* such records from declared states. Once this phase's close command exists, a worker whose declaration is closed while no steps are open would be stuck in a phantom `IN_PAUSE`. Removing the carve-out (already in this phase's scope) dissolves the trap — but it MUST be pinned by a dedicated test: declare → close declaration (no open steps) → reconcile lands on `IDLE`, not a stale declared `IN_PAUSE`.
  - **F6 (unscoped declared lookup):** the reconcile's open-declared lookup is not shift-window scoped (unlike `_load_open_steps`). Today unreachable only because clock-out and the safeguard clamp every open declared row. This phase must either (a) add shift-window scoping to the lookup, or (b) prove the clamp invariant holds on every path this phase adds (declare requires an open shift per D9, so no declared row can outlive its shift) and document that invariant where the lookup lives. Either way: an explicit test or assertion, not silence.

## Acceptance criteria

1. Declare happy path: clocked-in worker, valid PERSONAL reason → declared row open; open working steps transitioned to `PAUSED` with the declared `pause_reason_id`; live shift record is `IN_PAUSE` + `reason = pause_reason_id` + `manually_recorded = true` **within the same request/transaction**; response shape as specified.
2. Declare validation matrix: not clocked in → `409`; reason from another workspace or deleted → `404`; `BLOCKER` reason → validation error; `requires_description` without description → validation error. Access matrix (mirrors clock actions): worker without `user_id` → self; worker with foreign `user_id` → `403`; admin/manager with `user_id` → on-behalf works (`created_by_id` = actor); admin/manager without `user_id` → `403`; target not an active workspace worker → `404`. Same matrix tested for close.
3. Switch: declaring with a declaration already open closes the old row (`closed_by_id = actor`) and opens the new one atomically; at no point do two open declared rows exist (DB partial index is the backstop; test both the behavior and that no `IntegrityError` surfaces).
4. Close: open declaration → closed with `closed_by_id = actor`, live state reconciles to `IDLE`; no open declaration → `409`.
5. Full loop: declare → work a step (reconcile auto-closes declaration, Phase 2) → step completes → declare again → clock out → rebuilt timeline shows both declared segments with catalog reasons and zero unexplained idle inside them.
6. Retirement: `/pause` + `/resume` routes and both commands removed; router tests updated; reconcile carve-out removed and its dedicated test replaced by declared-precedence coverage; no dangling imports (`grep pause_worker_shift|resume_worker_shift` returns nothing outside archives/migrations).
7. `models/tables/users/README.md` state-machine section rewritten to match reality (incl. `IDLE`, declared states, `manually_recorded` redefinition).
8. Full suite green; `ruff check` clean.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md` + `06_commands_local.md`: command structure; `maybe_begin`; subordinate-command rule (both commands call the reconcile as subordinate; step transitions emit their own events via the existing core — commands add none).
- `backend/architecture/09_routers.md`: thin routes, `run_service`, `build_ok`/`build_err`.
- `backend/architecture/04_context.md`: `ServiceContext` usage.
- `backend/architecture/05_errors.md`: `ConflictError`/`NotFound`/`ValidationError` → HTTP mapping.
- `backend/architecture/28_roles_permissions.md`: `require_roles([WORKER])` + `resolve_worker_shift_target` self-path.
- `backend/architecture/32_concurrency.md`: honor the Phase 2 lock order (shift row → declared row).
- `backend/architecture/46_serialization.md` (+ local): response serializer conventions.
- `backend/architecture/21_naming_conventions.md`: command/route/serializer naming.
- `backend/architecture/15_testing.md`: integration placement; extend `test_worker_shift_commands.py` and `test_worker_shifts_router.py`.
- `backend/architecture/23_documentation.md`: README rewrite discipline.

### Local extensions loaded

- `06_commands_local.md`: `maybe_begin` + session-call safety + subordinate-command event rule.
- `46_serialization_local.md`: output-shape deltas.

### File read intent — pattern vs. relational

Permitted relational reads:
- `services/commands/users/pause_worker_shift.py`, `resume_worker_shift.py` — the exact behavior being retired (parity check for error messages/status codes).
- `services/commands/users/_clock_worker_shift.py` — `_load_open_working_step_rows` + `_apply_step_transition` invocation shape being reused.
- `services/commands/task_steps/_step_transition_core.py` — `_apply_step_transition` signature/semantics (what it emits, invariants).
- `services/commands/users/_worker_shift_access.py`, `reconcile_worker_shift_state.py` — call contracts.
- `models/tables/pause_reasons/pause_reason.py`, `models/tables/users/user_declared_state_record.py` — field names.
- `routers/api_v1/worker_shifts.py` — the router being modified.
- Existing tests for pause/resume — to convert, not fork.

Prohibited pattern reads: other commands for write-path skeleton → `06`; other routers for wiring → `09`; other serializers for shape → `46`.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
- Router trigger terms: `worker`, `command`, `router`.
- Excluded alternatives: none.

## Implementation plan

1. Serializer for the declared-state payload (id, pause_reason {id, name, image_url}, description, entered_at).
2. `declare_worker_state.py` per the Assumptions flow (steps 1–9), structured logs on declare/switch.
3. `close_declared_worker_state.py` per flow, structured log.
4. Router: add the two routes; delete `/pause` + `/resume` handlers and request models.
5. Delete both retired commands; remove the reconcile carve-out (and its `manually_recorded` current-row check); fix all imports.
6. Tests: acceptance 1–6 (extend `test_worker_shift_commands.py`, `test_worker_shifts_router.py`, reconcile suite); the full-loop test (acceptance 5) is the flagship — write it first.
7. README rewrite (acceptance 7).
8. Run validation plan.

## Risks and mitigations

- Risk: declare races the analytics worker's reconcile (step events from auto-pause) → double transition or unique-index violation.
  Mitigation: same-session synchronous reconcile is idempotent; the async one converges to no-op; `FOR UPDATE` lock order shared with Phase 2; existing retry-on-`IntegrityError` in the reconcile is the backstop. Concurrency test optional but recommended.
- Risk: deploy-time worker stuck in manual pause gets flipped to `IDLE` by carve-out removal.
  Mitigation: accepted one-time cosmetic effect (assumption block); deploy note in summary; clock-out rebuild remains correct.
- Risk: `_apply_step_transition` has clock-out-specific side effects we mis-reuse for pause.
  Mitigation: relational read of `_step_transition_core.py` before use; the existing manual step-pause flow through the same core is the reference behavior; acceptance 1 asserts the paused records' state + reason directly.
- Risk: retiring `/pause`/`/resume` breaks a frontend still calling them.
  Mitigation: coordinated by the operator (frontend is being rebuilt for in-app clock in this same effort); Phase 4 handoff doc states the removal explicitly.

## Validation plan

- `pytest app/tests/integration/services/commands/users/ -q`: declare/close/switch/validation matrix + full loop — green.
- `pytest app/tests/unit/test_worker_shifts_router.py -q`: route wiring + role gates — green.
- `pytest app/tests -q`: full suite green (no dangling references).
- `grep -rn "pause_worker_shift\|resume_worker_shift" app/beyo_manager/`: no hits.
- `ruff check`: clean.

## Review log

- (empty — filled by implementer and reviewer)

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
