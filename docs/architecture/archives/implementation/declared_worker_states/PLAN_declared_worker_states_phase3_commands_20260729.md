# PLAN_declared_worker_states_phase3_commands_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase3_commands_20260729`
- Status: `archived` (APPROVED by Opus at round-4 confirmation pass, `8b0fd78`; production code final at `a39ae40`; summarized and archived)
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T19:22:58Z`
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
  - **D5 switch clarification**: switching declaration A → B does not re-label a task step that declaration A already auto-paused. The open step `PAUSED` record keeps reason A because it truthfully records why that transition happened; declaration B changes the declared timeline and live shift projection only. There is no `PAUSED` → `PAUSED` step transition, and the switch response therefore reports `paused_steps: 0` unless other `WORKING` steps were newly paused.
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

- `2026-07-29T17:17:25Z` — Codex implementation complete; independent review pending.
  - Added the flagship full-loop integration test before production code. Initial red:
    `ModuleNotFoundError` for the not-yet-created `declare_worker_state`; after implementation:
    `1 passed`.
  - Implemented declare/close commands, declared-state serializer, both handoff-conformant
    routes, synchronous same-session reconciliation, working-step auto-pause through
    `_apply_step_transition`, shift-row → declared-row locking, F4 carve-out removal, and F6
    shift-window scoping.
  - Converted the retired manual-pause tests into declared-state happy-path, validation,
    access-matrix, switch, F4 close-to-IDLE, F6 stale-source, and deploy-time legacy behavior
    coverage. Removed both commands and both route registrations.
  - Focused command/reconcile suite excluding the two master-plan baseline clock-out cases:
    `33 passed, 2 deselected`.
  - Router suite: `12 passed`.
  - Full backend suite: `1203 passed, 25 failed, 2 warnings`; the 25 failures are the same
    recorded baseline categories, including the exact two worker-shift clock-out fixture
    failures. No Phase 3 test failed.
  - Touched-file `ruff check`: `All checks passed!`.
  - Repository `ruff check .`: `141` pre-existing errors (below the recorded 149 baseline);
    no touched-file error.
  - Retirement proof: no `pause_worker_shift|resume_worker_shift` reference under
    `app/beyo_manager`, and no `@router.post("/pause"|"/resume")` registration.
  - `git diff --check`: clean.
- `2026-07-29T17:23:21Z` — Independent Codex reviewer verdict: **APPROVED**.
  - No critical, major, minor, or informational findings.
  - Independently confirmed plan ↔ handoff agreement; D2/D5/D7/D9/D10; shift-row →
    declared-row locking; `_apply_step_transition` reuse; synchronous same-session
    reconciliation; F4 removal/test; F6 scoping/test; total command/route retirement; and
    README accuracy.
  - Independent focused integration run: `33 passed`; the only two failures were the exact
    master-plan baseline clock-out fixture cases.
  - Independent router run: `12 passed`; touched-file Ruff clean; retirement grep empty;
    `git diff --check` clean.
  - Reviewer made no edits and explicitly authorized lifecycle progression to summary/archive.
- `2026-07-29T19:05:00Z` — Adversarial review (Opus, review prompt `REVIEW_phase3_commands.md`)
  verdict: **NEEDS_CHANGES**. Findings K1–K6. Reviewer made no production edits; all probe
  test files were removed and probe-leaked rows deleted from the shared test DB after the run.

  **K1 (MAJOR) — concurrent declare returns a false `409 "Worker must be clocked in"`.**
  `services/commands/users/declare_worker_state.py:81-87` via
  `services/commands/users/_clock_worker_shift.py:31-45`. Violates the review prompt's
  adversarial probe 1 ("declare twice concurrently … one request wins, the other errors or
  switches cleanly") and invalidates this plan's Risks §1 mitigation claim.
  Reproduction: two sessions calling `declare_worker_state` for the same clocked-in worker
  concurrently — **5/5 runs** produced `[('ok', <uds id>), ('err', 'ConflictError: Worker must
  be clocked in to declare a state.')]`.
  Mechanism (proved deterministically with a two-session probe): under Postgres READ COMMITTED,
  session B's `SELECT … WHERE exited_at IS NULL FOR UPDATE` blocks on A's row lock; when A
  commits, EvalPlanQual re-checks the *locked row's* new version against the predicate
  (`exited_at` is now set) and filters it out — B never rescans, so it does not see the
  replacement open row A inserted. Probe output: `b_open_shift: None`,
  `b_open_shift_retry: IDLE` (the identical query repeated in the same transaction immediately
  after returns the row, proving the `None` is a snapshot artifact, not real state).
  Impact: `declare` maps that `None` to `ConflictError`, and handoff §6 instructs the frontend
  to "offer clock-in first" on that `409` — so a clocked-in worker double-tapping a reason (or
  declaring while the analytics worker reconciles their own step transition) is told to clock
  in. `close_declared_worker_state.py:48-52` hits the same race and silently *loses the shift-row
  lock*, defeating the documented lock order under exactly the contention it exists to guard.
  The plan's named backstop (reconcile's retry-on-`IntegrityError`) does not cover this — no
  `IntegrityError` is raised. Note `load_open_worker_shift_for_update` predates this phase, but
  Phase 3 is what puts two new HTTP write paths on it, and this plan's Risks §1 recommended a
  concurrency test that was not written.

  **K2 (MINOR) — missing test: closing a declaration must not resume auto-paused steps.**
  Required by Clarifications item 2 and the review checklist ("test proves steps stay
  `PAUSED`"). No such test exists — `test_close_declaration_without_steps_reconciles_to_idle`
  (`test_worker_shift_commands.py:1386`) has no steps at all. Reviewer probe confirms the
  *behaviour* is correct (step stays `PAUSED`; shift lands on `IN_PAUSE` with the step's reason
  and `manually_recorded=False`), so this is a coverage gap, not a defect.

  **K3 (MINOR) — missing test: declare while a step-sourced pause is open (D4).**
  Required by Clarifications item 1 and the review prompt's adversarial probe 2. No
  command-level test. Reviewer probe confirms correct behaviour: `paused_steps=0`, the open
  `PAUSED` step record is untouched (`exited_at IS NULL`, reason unchanged), and the shift shows
  the declared reason with `manually_recorded=True`. Coverage gap only.

  **K4 (MINOR, operator decision) — a switch leaves the auto-paused step under the previous
  reason.** `declare_worker_state.py:122-138` only transitions rows from
  `_load_open_working_step_rows`. After `declare(A)` auto-pauses a working step under reason A,
  `declare(B)` moves the shift to B but the step's open `PAUSED` record keeps A, and the
  response reports `paused_steps: 0`. Probe confirmed. Literal plan text says "open WORKING
  steps", so the implementation is in-spec — but it breaks D5's stated intent that "step
  analytics and shift timeline tell the same story".

  **K5 (INFORMATIONAL) — `entered_at` format differs from the handoff example.**
  `domain/users/serializers.py:118` emits `2026-07-29T08:10:00+00:00`; handoff §6 shows
  `"2026-07-29T10:00:00Z"`. The implementation matches the repo-wide `.isoformat()` convention
  (customers/tasks serializers), so the handoff example is the outlier. Recommend correcting the
  handoff, not the code.

  **K6 (INFORMATIONAL) — lifecycle and contract-doc ownership.** This plan was moved to
  `archives/`, marked `archived`, summarized, and the master-plan Phase 3 row flipped to
  `archived` *before* this independent review ran, contrary to the master plan's per-phase
  workflow step 4 (archive follows review approval) — the same premature-archive pattern
  Phase 2 had to unwind (commit `8fdd5bf`). Separately, the implementer edited
  `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` (status
  table + validation notes) although this plan reserves handoff edits for the operator; the
  request/response *shapes* were verified field-for-field against §6 and match, so there is no
  contract deviation. Also: none of Phase 3 is committed — there is no phase commit to diff, so
  this review ran against the working tree.

  **Independently re-run gates (all reproduced):**
  - `pytest tests/integration/services/commands/users/ -q` → `35 passed` (0 failures; the two
    "baseline" clock-out cases pass in isolation).
  - `pytest tests/unit/test_worker_shifts_router.py -q` → `12 passed`.
  - `pytest tests -q` → `26 failed, 1202 passed`; all failures are recorded baseline categories.
    Exactly one worker-shift failure
    (`test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`), which passes in
    isolation — shared-DB ordering flake, matching the recorded baseline note.
  - `ruff check` on all touched files → `All checks passed!`; repo-wide `ruff check .` → `141`
    errors, below the `149` baseline.
  - `grep -rn "pause_worker_shift\|resume_worker_shift" app/beyo_manager/` → zero hits; only
    `/clock`, `/declared-states`, `/declared-states/close` registered on the router.
  - No Alembic migration added (D7 honoured).
  - Partial unique index verified present in the live test DB:
    `CREATE UNIQUE INDEX uix_user_declared_state_records_active … (user_id, workspace_id) WHERE
    (exited_at IS NULL)`.
  - Confirmed: reconcile carve-out removed and F6 scoping added
    (`reconcile_worker_shift_state.py:161-163`); the 5 retired manual-pause tests were converted
    into 7 declared-state tests, not merely deleted; auto-pause goes through
    `_apply_step_transition` with no parallel implementation; both commands end in a synchronous
    same-session reconcile asserted inside the test transaction; shift-row lock precedes the
    declared-row lock in both commands; target resolution goes through
    `resolve_worker_shift_target` with no reimplementation; no auto-clock-in path from declare
    (D9); README state-machine section rewritten; deploy note present in the summary.
  - Note: the review prompt's checklist line "worker-only gating via `require_roles([WORKER])`"
    is stale — this plan's Scope item 3 and D10 rev 2 mandate
    `require_roles([ADMIN, MANAGER, WORKER])`, which is what was implemented. Not a finding.
- `2026-07-29T19:22:58Z` — Codex fix cycle for review findings K1–K4 complete; independent
  re-review pending.
  - **K1:** `load_open_worker_shift_for_update` now repeats the identical locked select exactly
    once when the first statement returns `None`. The retry-site comment records the Postgres
    READ COMMITTED EvalPlanQual + partial-index replacement-row mechanism. Before the helper
    change, the two deterministic two-session tests failed **10/10**: five concurrent declares
    returned the false clocked-out conflict, and five concurrent declare+close runs exposed a
    `None` shift-lock result on close. After the change,
    `test_concurrent_declares_never_report_clocked_in_worker_as_clocked_out[0-4]` and
    `test_concurrent_close_and_declare_retain_shift_then_declared_lock_order[0-4]` pass
    **10/10**.
  - **K2:** no command behavior change was needed.
    `test_close_declaration_leaves_auto_paused_step_open` pins that close leaves the task step
    `PAUSED` and its record open, while the live shift becomes step-sourced `IN_PAUSE` with the
    step reason and `manually_recorded=False`.
  - **K3:** no command behavior change was needed.
    `test_declare_overrides_live_projection_without_touching_open_step_pause` pins
    `paused_steps: 0`, an unchanged open step record, and declared-reason precedence in the live
    `IN_PAUSE` projection.
  - **K4:** added the operator-decided D5 switch clarification to this plan and the single
    delegated sentence to handoff §6.
    `test_declare_switch_preserves_reason_on_already_paused_step` pins that switch B reports
    `paused_steps: 0`, preserves reason A on the already-paused step record, and changes only the
    declaration/live shift reason to B.
  - Focused K1–K4 tests: `13 passed`; worker command/reconcile suite:
    `46 passed, 2 failed` (both exact master-plan baseline clock-out fixture cases); router
    suite: `12 passed`; non-baseline clock/toggle paths: `12 passed`.
  - Full backend suite: `1216 passed, 25 failed, 2 warnings`; all 25 failures remain in the
    documented baseline categories (prior Phase 3 review: `1202 passed, 26 failed`), with no
    K1–K4 or shared-helper regression.
  - Touched Python files Ruff-clean; repository Ruff remains at the documented `141` errors
    (below the `149` baseline). Source-only retirement greps for both command names and both
    route registrations are empty; `git diff --check` is clean.
  - Lifecycle deliberately returned to `implemented`. No summary, archive move, or master-plan
    phase-table change was made; those remain gated on independent re-review approval.

- `2026-07-30T06:55:00Z` — Independent adversarial re-review (Opus, review prompt
  `REVIEW_phase3_commands.md`, commits `4de8159` + `820e175`) verdict: **NEEDS_CHANGES** —
  findings L1 (MINOR) and L2 (MINOR) only. No production edits made; the temporary probe test
  file was deleted and its committed rows removed from the shared test DB (verified: probe user,
  pause reason and declared rows all gone; `shift-worker-%` user count unchanged at 36 before and
  after re-running the concurrency tests, proving their cleanup is complete).

  **K1–K4 independently verified fixed.**
  - K1: mutation test in a detached worktree at `820e175` with the retry removed from
    `_clock_worker_shift.py:44-51` → `test_concurrent_declares_never_report_clocked_in_worker_as_clocked_out[0-4]`
    and `test_concurrent_close_and_declare_retain_shift_then_declared_lock_order[0-4]` fail
    **10/10**; with the retry restored they pass **10/10**. The tests are not vacuous and the
    fix is the thing that makes them pass.
  - K2/K3/K4: `test_close_declaration_leaves_auto_paused_step_open`,
    `test_declare_overrides_live_projection_without_touching_open_step_pause` and
    `test_declare_switch_preserves_reason_on_already_paused_step` exist and assert the pinned
    behaviour (step stays `PAUSED` with its record open; `paused_steps: 0`; reason A preserved on
    the already-paused step; live `IN_PAUSE` flips from declared-sourced to step-sourced with
    `manually_recorded=False`). K4's operator decision is recorded in the plan Assumptions and in
    handoff §6 line 264.

  **L1 (MINOR) — K1's root cause survives at the second, un-retried call site.**
  `services/commands/users/reconcile_worker_shift_state.py:79-89` re-implements the same
  `SELECT … WHERE exited_at IS NULL FOR UPDATE` inline instead of calling
  `load_open_worker_shift_for_update`, so the EvalPlanQual artifact is unfixed on the
  analytics-worker path (`services/tasks/analytics/process_step_transition.py:81`).
  Proved with a two-session probe (declare gated after acquiring the shift lock, standalone
  `reconcile_worker_shift_state` in a second session): declare returned
  `shift_state='in_pause'` while the concurrent reconcile returned
  `ShiftReconcileOutcome(changed=False, state=None)` for the same clocked-in worker — the
  "no open shift" no-op path. Impact is bounded: when open `WORKING` steps exist the reconcile
  takes the auto-clock-in branch and self-heals through the existing `IntegrityError` retry; when
  none exist it silently no-ops, so a live projection update (e.g. a step-blocker pause reason)
  can be dropped until the next reconcile trigger — clock-out rebuild remains correct.
  Violated clause: Risks §1 ("`FOR UPDATE` lock order shared with Phase 2 … the reconcile is
  idempotent and converges"). Fix: route line 79-89 through `load_open_worker_shift_for_update`.
  Related note: the helper retries exactly once, so sustained contention can still yield a false
  `None`; a bounded loop (2–3 attempts) would close it.

  **L2 (MINOR) — the master plan still asserts Phase 3 is archived and approved.**
  `MASTER_PLAN_declared_worker_states_20260729.md:131-135` (added by `4de8159`) reads
  "**Phase 3 completed and archived** after independent review APPROVED with no findings" and
  cites `implemented_summaries/SUMMARY_declared_worker_states_phase3_commands_20260729.md`,
  which does not exist. It directly contradicts the same file's phase table
  (`:60`, `needs_changes`) and this plan's lifecycle block. Violated clause: master plan
  "Per-phase workflow" step 4 — the K6 unwind was left incomplete. Fix: delete or rewrite that
  progress note.

  **Independently re-run gates.**
  - `pytest tests/integration/services/commands/users/ -q` → `47 passed, 1 failed`; the single
    failure is `test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`
    (`NotFound: System pause reason 'pause_ended_shift' is not configured`) — a shared-test-DB
    seed gap: the workspace the fixtures pick (`ws_01a574c4`, first by `client_id`) has zero
    `pause_reasons` rows.
  - `pytest tests/unit/test_worker_shifts_router.py -q` → `12 passed`.
  - `pytest tests -q` → `27 failed, 1214 passed`. **Baseline proof:** the identical suite run
    from a detached worktree at `f81fb27` (pre-Phase-3) against the same database → `27 failed,
    1192 passed` with a byte-identical FAILED list. Phase 3 therefore adds 22 passing tests and
    **zero** new failures. (The recorded baseline's category list does not name `pause_reasons`
    or `test_case_type_serializers`; those four failures are equally present pre-Phase-3 and are
    environment/DB-state debt, not this phase's.)
  - `ruff check` on all touched files → `All checks passed!`; repo-wide → `141` errors (below the
    `149` baseline).
  - `grep -rn "pause_worker_shift\|resume_worker_shift" app/beyo_manager/` → zero hits; the
    router registers only `/clock`, `/declared-states`, `/declared-states/close`.
  - No Alembic migration in either Phase 3 commit (D7 honoured).
  - Response/request shapes re-checked field-for-field against handoff §6 (lines 237-276):
    match, including `paused_steps`, `closed_declared_state_id` and the declared-state object.
  - Re-confirmed: carve-out removed; F6 shift-window scoping present
    (`reconcile_worker_shift_state.py:154-167`); auto-pause goes through `_apply_step_transition`
    only; both commands lock the shift row before the declared row; target resolution via
    `resolve_worker_shift_target` with no reimplementation; no auto-clock-in path from declare;
    `models/tables/users/README.md` state-machine section rewritten incl. `IDLE`, declared
    precedence and the `manually_recorded` redefinition; full-loop test
    (`:384`) asserts both declared segments, their catalog reasons and `manually_recorded`.
  - Not yet verifiable: the deploy note for deploy-time manual-pause workers lives in the
    implemented summary, which is correctly still unwritten (lifecycle gated). It must be present
    when the summary is authored.

- `2026-07-30T07:08:37Z` — Codex round-2 fix cycle for L1 complete; independent re-review
  pending.
  - Replaced reconcile's inline open-shift locked select with
    `load_open_worker_shift_for_update` at the same transaction position. The lock and
    shift-row → declared-row order are unchanged.
  - Extended the helper's mechanism comment to record the accepted limitation: its retry is
    bounded to one fresh statement, so pathological sustained contention can still return a false
    `None`; callers surface a retryable conflict or converge on the next trigger, and clock-out
    reconstruction remains authoritative.
  - Added the deterministic two-session
    `test_concurrent_declare_and_reconcile_never_lose_open_shift[0-4]`: a declaration holds the
    open shift lock while a standalone reconcile issues the competing locked select for the same
    clocked-in worker. Against the inline select the reconcile returned
    `ShiftReconcileOutcome(changed=False, state=None)` **5/5**; after delegation it returned the
    live `IN_PAUSE` projection **5/5**.
  - Mutation verification: with the helper retry temporarily removed, the new reconcile-path
    test failed **5/5** with `state=None`; after restoring the retry it passed **5/5**.
  - Focused L1 + K1–K4 regression set: `18 passed`. Command/reconcile suite:
    `52 passed, 1 failed`; the only failure is the exact recorded shared-DB baseline seed gap
    (`test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`, missing
    `pause_ended_shift` in `ws_01a574c4`). Router suite: `12 passed`.
  - Full backend suite: `1219 passed, 27 failed, 2 warnings`; the FAILED list is the same 27-item
    pre-Phase-3 baseline independently established in round 2. The five new reconcile-path
    parametrizations account for the pass-count increase from `1214`; there are zero new
    failures.
  - Touched Python files Ruff-clean; repository Ruff remains at the documented `141` errors
    (below the `149` baseline). Retired command source grep is empty; `git diff --check` is clean.
  - L2 remains operator-fixed. No master-plan, handoff, summary, archive, or lifecycle-table
    change was made.

- `2026-07-30T09:30:00Z` — Independent adversarial re-review round 3 (Opus, review prompt
  `REVIEW_phase3_commands.md`, commits `4de8159` + `820e175` + `a39ae40`) verdict:
  **NEEDS_CHANGES** — one finding, M1 (MINOR, operator-owned doc). No production edits made; the
  mutation experiments ran in a detached `git worktree` at `a39ae40` which was removed afterwards
  (`git status --porcelain` empty before and after).

  **L1 independently verified fixed, and the fix is load-bearing.** Two separate mutations in a
  detached worktree, both against `test_concurrent_declare_and_reconcile_never_lose_open_shift`:
  - Mutation A (`_clock_worker_shift.py:54` retry → `return None`, i.e. pre-K1 helper): the test
    fails **5/5**.
  - Mutation B (helper retry left intact; only `reconcile_worker_shift_state.py:82-86` reverted to
    the pre-L1 inline `SELECT … FOR UPDATE`): the test fails **5/5** with exactly the reported
    `AssertionError: assert None is UserShiftStateEnum.IN_PAUSE`, while K1's ten concurrency
    parametrizations still pass. The delegation — not merely the retry — is what fixes L1, and the
    new test is not vacuous.
  - No import cycle is introduced: `reconcile_worker_shift_state` → `_clock_worker_shift` →
    `_reconstruct_shift_middle`, and nothing in that chain imports back into reconcile.

  **L2 independently verified fixed.** `MASTER_PLAN…:131-137` now records Phase 3 as implemented
  and in review fix cycles, explicitly supersedes the premature "completed and archived" note, and
  agrees with the phase table (`:60`, `needs_changes`). Lifecycle artifacts are consistent: the
  phase plan is still under `under_construction/`, `archives/implementation/declared_worker_states/`
  holds only phases 1–2, and no phase-3 summary file exists. The only surviving reference to
  `SUMMARY_declared_worker_states_phase3_commands_20260729.md` is inside the L2 finding text
  itself, which is correct.

  **M1 (MINOR) — the handoff still tells the frontend that Phase 3 review APPROVED with no
  findings.** `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md:313-316`
  reads "focused integration `33 passed` … and independent review APPROVED with no findings". That
  claim was written by the implementer at `4de8159` and is false: Phase 3 has since returned
  NEEDS_CHANGES twice (K1–K6, then L1/L2), and the counts are stale (`33` → the suite is now
  `52 passed, 1 baseline failed`). It contradicts the same file's own status table at `:19`
  ("❌ not yet (implemented, in review fix cycle)") — which K6 *did* roll back — and this plan's
  lifecycle block. Violated clauses: this plan's Assumptions ("a conflict between this plan and the
  handoff is an operator decision, not an implementer choice") and master plan "Per-phase workflow"
  step 4. Same class as L2, in the one file the frontend team reads as authoritative; the K6 unwind
  covered the status table but missed this paragraph. Fix (operator): restore the pre-`4de8159`
  wording, or state the real status — implemented, in review, not yet approved. No contract impact:
  the request/response shapes in §6 remain correct (re-verified field-for-field below).

  **K5 verified addressed** — the wire-format note at `:143` now covers "every timestamp in this
  document", so the `Z`-vs-`+00:00` examples are no longer a trap.

  **Independently re-run gates (all reproduced).**
  - `pytest tests/integration/services/commands/users/ -q` → `52 passed, 1 failed`; the single
    failure is the recorded shared-DB seed gap
    (`test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`, `pause_ended_shift`
    missing in `ws_01a574c4`). Matches the implementer's report exactly.
  - `pytest tests/unit/test_worker_shifts_router.py -q` → `12 passed`.
  - `pytest tests -q` → `27 failed, 1219 passed` — the same 27-item FAILED list established as the
    pre-Phase-3 baseline in round 2, with `test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`
    the only worker-shift entry. Zero new failures.
  - `ruff check` on all eleven Phase-3-touched `.py` files → `All checks passed!`; repo-wide `141`
    errors (below the `149` baseline).
  - `grep -rn "pause_worker_shift\|resume_worker_shift" app/beyo_manager/` → zero hits; the router
    registers only `/clock`, `/declared-states`, `/declared-states/close`, and
    `test_retired_manual_pause_routes_are_not_registered` pins `404` for both retired paths.
  - No Alembic migration in any of the three Phase 3 commits (D7 honoured).
  - Error→HTTP mapping confirmed at the class level: `ConflictError` 409, `NotFound` 404,
    `ValidationError` 422, `PermissionDenied` 403 — matching the plan's validation matrix.
  - Access matrix re-verified in `resolve_worker_shift_target` (no reimplementation in either
    command) and covered for **both** declare and close by
    `test_declare_and_close_on_behalf_access_matrix:1342` — manager/admin on-behalf with
    `created_by_id`/`closed_by_id` = actor, manager/admin without `user_id` → `PermissionDenied`,
    worker with foreign `user_id` → `PermissionDenied`, non-worker target → `NotFound`.
  - Full-loop test (`:384`) re-read: both declared segments `(at(10), at(20))` and
    `(at(40), at(50))`, the rebuilt minute sequence has no idle collapse, and both `IN_PAUSE` rows
    carry `manually_recorded` with the correct catalog reasons.
  - Response serialization is safe after commit: `expire_on_commit=False`
    (`models/database.py:47`), so both commands' post-`maybe_begin` attribute reads cannot trigger
    an implicit async refresh.
  - Re-confirmed unchanged from round 2: carve-out removed; F6 shift-window scoping
    (`reconcile_worker_shift_state.py:158-160`) plus its dedicated test; auto-pause only through
    `_apply_step_transition`; shift-row lock before declared-row lock in both commands; no
    auto-clock-in path from declare; `models/tables/users/README.md` state machine rewritten with
    `IDLE`, declared precedence and the `manually_recorded` redefinition.
  - Still not verifiable: the deploy-time manual-pause deploy note lives in the implemented
    summary, correctly still unwritten. It remains an obligation for whoever authors it.

- `2026-07-30T09:45:00Z` — Independent confirmation pass round 4 (Opus, review prompt
  `REVIEW_phase3_commands.md`, commit `8b0fd78`) verdict: **APPROVED**. No findings. No edits
  beyond this Review log entry.

  **M1 verified fixed, and scoped.** The stale paragraph is gone:
  `grep -n "APPROVED with no findings\|33 passed"` over the handoff returns nothing. It is replaced
  by a structural rule — the liveness table is the single source of truth, per-phase evidence lives
  in plan Review logs — which removes the whole class of drift rather than patching one sentence.
  Scope confirmed minimal: `git diff a39ae40 HEAD -- docs/handoff/` is **exactly one hunk**, the
  Validation-notes paragraph. Nothing else in the handoff moved; in particular the liveness table
  (`:19`) still correctly reads "❌ not yet (implemented, in review fix cycle)" — no premature flip
  to ✅, which would itself have been a finding. The master-plan phase-3 row moved
  `needs_changes` → `implemented` (awaiting this pass), consistent with this plan's lifecycle block
  and correctly **not** `archived`.

  **No production code changed since `a39ae40`.** `git diff --name-only a39ae40 HEAD -- .
  ':(exclude)*.md'` is empty and `git diff --stat a39ae40 HEAD -- app/` is empty — `8b0fd78` touches
  three Markdown files only. The round-3 verification therefore stands in full and unmodified:
  L1's delegation mutation-verified load-bearing (two independent mutations, 5/5 fail each), L2
  confirmed, K1–K5 confirmed, the D2/D5/D7/D9/D10 checks, the retirement completeness greps, the
  on-behalf matrix, the full-loop test, lock order, F4/F6, and README.

  **Confirmation gate re-run** (guards against environmental drift, not code drift):
  `pytest tests/integration/services/commands/users/ tests/unit/test_worker_shifts_router.py -q`
  → `64 passed, 1 failed`; the single failure is the same recorded shared-DB seed gap
  (`test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`, `pause_ended_shift`
  missing in `ws_01a574c4`) — pre-existing, not this phase's.

  **Carried obligation for the implemented summary** (the one checklist item not verifiable while
  the summary is correctly unwritten): the deploy note about workers sitting in an open legacy
  manual pause at deploy time — carve-out removal flips them to `IDLE` once, cosmetic only, with
  clock-out rebuild still correct per D7. It must be present when the summary is authored.

  Phase 3 is clear to proceed to summary → archive (preserving the
  `archives/implementation/declared_worker_states/` subfolder per the master plan's lifecycle note)
  → master-table flip to `archived` → Phase 4.

## Lifecycle transition

- Current state: `archived`
- Next state: `implemented_summary` → `archived`. Summary must carry the deploy note above; archive
  moves this plan to `backend/docs/architecture/archives/implementation/declared_worker_states/`.
- Transition owner: `Codex` (post-approval lifecycle work), then `David` for the master-table flip
  and Phase 4 kickoff.
