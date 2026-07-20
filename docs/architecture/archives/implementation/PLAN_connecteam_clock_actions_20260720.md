# PLAN_connecteam_clock_actions_20260720

## Metadata

- Plan ID: `PLAN_connecteam_clock_actions_20260720`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-20T13:00:00Z`
- Last updated at (UTC): `2026-07-20T01:23:33Z`
- Related issue/ticket: `n/a` (predecessor: `PLAN_connecteam_time_activity_webhook_foundation_20260720.md`)
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_connecteam_clock_actions_20260720.md`

## Goal and intent

- Goal: Replace the three placeholder Connecteam handlers with real domain actions — a resolved worker's `clock_in` event clocks the worker in, and `clock_out` / `auto_clock_out` events clock the worker out — using the **same shift machinery the `toggle_worker_shift` endpoint executes**, driven by the webhook's explicit intent.
- Business/user intent: Workers clock in/out on Connecteam; ManagerBeyo's internal shift state (and everything derived from it: step pausing, presence, worker stats) must follow automatically, exactly as if the worker had pressed the internal clock button.
- Non-goals: changing intake/dedup/queueing (phase 1, live); syncing users from Connecteam; handling `manual_break`; modifying `toggle_worker_shift`, `_clock_worker_shift.py`, or any shared architecture; emitting new realtime events (the manual clock path emits none — parity is the requirement).

## Scope

- In scope:
  - Rewrite the bodies of `handlers/handle_clock_in.py`, `handle_clock_out.py`, `handle_auto_clock_out.py` to perform shift mutations via the existing internal primitives.
  - Session/transaction plumbing in `handle_connecteam_process_time_activity.py` so resolve + clock action are atomic per event.
  - Idempotency semantics: `ConflictError` from the primitives is a terminal no-op outcome, never a retry.
  - Structured logging for applied/no-op outcomes; tests; live ngrok validation.
- Out of scope: everything in intention "Out of scope"; new settings; migrations; new queues/workers; changes to retry policy.
- Assumptions:
  - Phase 1 is live and archived-or-approved; `resolve_connecteam_worker` returns `(work_profile_id, user_id, workspace_id)`.
  - At least one work profile has `connecteam_user_id` set for live validation.
  - Connecteam sends `eventTimestamp` (epoch seconds) on every time-activity event (observed in phase-1 discovery).

## Clarifications required

- [x] **RESOLVED 2026-07-20 (owner): intent-aware primitives.** Original question: Literal `toggle_worker_shift` vs the toggle endpoint's internal primitives with explicit intent (recommended)? — Blocks safe implementation because the two behave differently under duplicate or out-of-order deliveries. `toggle_worker_shift` is a state-flip: it reads the current open shift and does the opposite (`toggle_worker_shift.py:37-55`). If a `clock_in` webhook arrives while the worker is already clocked in internally (redelivery past the dedup TTL, a manually-requeued dead-letter, a missed prior `clock_out`), toggling would **clock the worker out** — inverting intent. The toggle endpoint's actual work is done by shared primitives in `_clock_worker_shift.py` — `clock_in_shift_for_user` / `clock_out_shift_for_user` — which take explicit intent, an explicit timestamp, and guard with `ConflictError` ("already clocked in" / "not clocked in"). The system-triggered precedent already exists: `services/tasks/users/auto_clock_out_open_shifts.py` calls `clock_out_shift_for_user` directly from a worker. **Recommendation (plan written against it): handlers call the primitives directly — `clock_in` event → `clock_in_shift_for_user`; `clock_out`/`auto_clock_out` events → `clock_out_shift_for_user`; `ConflictError` → logged no-op.** This *is* "using the toggle endpoint" in every behavioral sense (identical records, identical step transitions) while honoring the webhook's intention, and it satisfies the owner rule of not modifying shared code.
- [x] **RESOLVED 2026-07-20 (owner): Connecteam event time (`occurred_at`, fallback `received_at`).** Original question: Shift timestamps: Connecteam event time (recommended) or backend processing time? — Changes what `entered_at`/`exited_at` mean. The primitives accept the timestamp as a parameter, so using the webhook's `occurred_at` (from `eventTimestamp`) records when the worker actually clocked, immune to queue/retry delay (a clock-out retried for 30 minutes should not inflate the shift by 30 minutes). Recommendation: use `occurred_at`; fall back to `received_at` if absent. Processing time (`datetime.now`) is the simpler-but-lossier alternative.

## Acceptance criteria

1. A real Connecteam `clock_in` (shift) for a mapped worker creates exactly the records the toggle endpoint creates: a `STARTED_SHIFT` marker and an open `IDLE` `user_shift_state_record`, with `manually_recorded=False`.
2. A real Connecteam `clock_out` (shift) closes the open shift record, writes the `ENDED_SHIFT` marker, and transitions all open `WORKING` step records to `ENDED_SHIFT` with reason `PAUSE_ENDED_SHIFT` — identical to the manual path; the transitioned-step count is logged.
3. `auto_clock_out` performs the same close as `clock_out` and is distinguishable in logs.
4. A `clock_in` event for an already-clocked-in worker is a logged no-op (`already_clocked_in`) — the shift is **not** toggled closed; a `clock_out`/`auto_clock_out` with no open shift is a logged no-op (`no_open_shift`). Both complete the task without retry.
5. Shift record timestamps come from the Connecteam event's `occurred_at`, not from processing time (per Clarification 2's resolution).
6. `changed_by_id` on webhook-created records is the resolved worker's own `user_id` (the worker performed the action, via Connecteam).
7. Unmapped workers still produce `connecteam_worker_not_mapped` and perform zero writes; `manual_break` still never reaches handlers.
8. Resolve + clock action commit atomically per event; an unexpected failure (DB down) raises, and the platform retries the task (max 5) with the whole unit re-executed idempotently (a retry after a successful commit lands on the `ConflictError` no-op path).
9. Concurrent processing of two events for the same worker cannot corrupt state (`load_open_worker_shift_for_update` row-locks per worker inside the primitives).
10. No changes to `toggle_worker_shift.py`, `_clock_worker_shift.py`, `_worker_shift_access.py`, worker runtime, or any non-Connecteam file (the phase-1 files listed in scope are the only edits).
11. Tests cover: applied clock-in, applied clock-out with step transitions, both no-op paths, auto variant, timestamp sourcing, changed_by attribution, retry-then-noop idempotency, and record parity with the toggle endpoint.
12. Live ngrok validation: Connecteam clock-in/out by a mapped worker visibly drives internal shift state end-to-end.

## Contracts and skills

### Contracts loaded

Selected contracts (core, always included):
- `backend/architecture/01_architecture.md`: layering — handlers stay in the integration boundary, domain writes go through existing command-layer primitives.
- `backend/architecture/04_context.md`: `ServiceContext` construction rules (the clock-out primitive builds one internally for step transitions).
- `backend/architecture/05_errors.md`: `ConflictError` semantics and classification.
- `backend/architecture/06_commands.md`: command/primitive structure and transaction ownership.
- `backend/architecture/07_queries.md`: resolver query usage.
- `backend/architecture/09_routers.md`: core-mandated (no router changes this phase — confirms none needed).
- `backend/architecture/21_naming_conventions.md`: naming for new log events/outcomes.
- `backend/architecture/40_identity.md`: `client_id` handling on state records.
- `backend/architecture/41_user.md`: user/work-profile/shift-state domain rules.
- `backend/architecture/42_event.md`: event vocabulary (confirms no domain-event emission exists on the manual clock path — parity means none here).
- `backend/architecture/48_presence.md`: shift/presence state semantics this phase now writes into.

Added from guide (goal bundle: **Worker-driven backend** + triggers):
- `backend/architecture/16_background_jobs.md`: trigger "worker/retry" — task handler behavior, retry-by-raise contract.
- `backend/architecture/12_infra_redis.md`: bundle member — dedup interplay with redelivery.
- `backend/architecture/51_worker_runtime.md`: trigger "worker" — session usage inside workers.
- `backend/architecture/49_observability_runtime.md`: trigger "structured logs" — lifecycle log fields.
- `backend/architecture/17_logging.md`: trigger "structured logs" — no payload/PII leakage in new logs.
- `backend/architecture/32_concurrency.md`: `FOR UPDATE` row-locking guarantees relied on for criterion 9 (justification: correctness of concurrent clock events; not in trigger map, added deliberately).
- `backend/architecture/15_testing.md`: test layout and DB fixtures.
- `backend/architecture/19_integrations.md`: integration boundary discipline.
- `backend/architecture/57_shopify_integration.md`: precedent for extending an integration from intake to real processing.

Excluded contracts:
- `30_migrations.md` / `03_models.md`: no schema change this phase.
- `13_sockets.md` / `56_realtime_layer.md`: manual clock path emits nothing; parity requires nothing.
- `52_replayability.md`, `54_ci_cd_runtime.md`, `34_file_storage.md`: not touched by this phase.

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: `maybe_begin` + session call safety — governs the handler's transaction plumbing.
- `backend/architecture/07_queries_local.md`: query conventions for the resolver call.
- `backend/architecture/40_identity_local.md`, `41_user_local.md`, `42_event_local.md`, `48_presence_local.md`: app deltas for the domains being written.

Applied precedence: canonical first, local second; local wins for this app.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted (relational reads — performed while authoring this plan; may be repeated):
- `services/commands/users/toggle_worker_shift.py`, `_clock_worker_shift.py` — exact primitive signatures, ConflictError guards, record shapes, step-transition behavior.
- `services/tasks/users/auto_clock_out_open_shifts.py` — the existing worker-invoked clock mutation precedent (session pattern, `changed_by_id=None` usage).
- `services/tasks/connecteam/*` and `services/queries/users/resolve_connecteam_worker.py` — phase-1 files being modified.
- `models/tables/users/user_shift_state_record.py` — field names/nullability if needed for tests.
- `services/commands/users/clock_in_worker_shift.py` / `clock_out_worker_shift.py` — confirmed thin wrappers; no event emission anywhere in the manual path.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md` (lifecycle processing, as phase 1); contract set assembled via `backend/skills/cross_cutting/planning_contract_selection/SKILL.md`.
- Router trigger terms: `worker, retry, concurrency, integration, shift`
- Excluded alternatives: `backend/skills/domains/presence/SKILL.md` — closest domain skill, but this phase only *calls* existing shift primitives; it defines no new presence behavior. Re-load it if implementation reveals a need to alter shift semantics (it must not — that would violate scope).

## Implementation plan

Design constants:
- Timestamp: `occurred_at` from the normalized envelope (fallback `received_at`), parsed to aware UTC `datetime`.
- Actor: `changed_by_id = worker.user_id` (the worker's own action via Connecteam; also satisfies `clock_in_shift_for_user`'s non-optional `changed_by_id: str`).
- New processing outcomes (extend `ConnecteamProcessingOutcomeEnum`): `clock_in_applied`, `clock_out_applied`, `already_clocked_in`, `no_open_shift`.
- New log events: `connecteam_clock_in_applied`, `connecteam_clock_out_applied`, `connecteam_clock_event_noop` (with `noop_reason`), keeping phase-1 field conventions (`connecteam_event_type=`, never `event_type=` — see phase-1 Review log defect).

Steps:

1. **Handler signature evolution** — in `services/tasks/connecteam/`: the dispatcher (`handle_connecteam_process_time_activity.py`) already owns a session for resolution; restructure so **one transaction spans resolve + clock action** (per `06_commands_local.md` `maybe_begin` rules, mirroring `auto_clock_out_open_shifts`'s `async with session.begin()` shape): open session → begin → `resolve_connecteam_worker` → dispatch `HANDLER_MAP[event_type](session=session, worker=worker, event=event)` → commit. Handlers change from `execute(*, worker, event)` to `execute(*, session, worker, event) -> ConnecteamHandlerResult`. Unmapped/manual-break early-exits keep their phase-1 behavior.

2. **`handlers/handle_clock_in.py`** — replace the no-op body:
   - Parse `occurred_at` per design constants.
   - `try: await clock_in_shift_for_user(session, worker.workspace_id, worker.user_id, occurred_at, changed_by_id=worker.user_id)`
   - Success → log `connecteam_clock_in_applied` (fields: event_key, request_id, connecteam_event_type, workspace_id, internal_user_id, occurred_at) → outcome `clock_in_applied`.
   - `except ConflictError` → log `connecteam_clock_event_noop` with `noop_reason="already_clocked_in"` → outcome `already_clocked_in` (return normally; task completes; **no retry, no toggle**).
   - Any other exception propagates (platform retry).

3. **`handlers/handle_clock_out.py`** — same shape with `clock_out_shift_for_user(...)`; capture the returned transitioned-step count into the `connecteam_clock_out_applied` log; `ConflictError` → `noop_reason="no_open_shift"` → outcome `no_open_shift`.

4. **`handlers/handle_auto_clock_out.py`** — delegate to the same clock-out logic (shared private helper `_apply_clock_out(session, worker, event, *, auto: bool)` inside the handlers package is acceptable) with `auto=True` reflected in the log fields (`auto_clock_out=true`), so Connecteam-initiated auto-closures are distinguishable from worker-tapped ones and from the internal midnight safeguard.

5. **Outcome enum + completion log** — extend `domain/connecteam/enums.py` with the four new outcomes; the dispatcher's `connecteam_webhook_completed` log carries the handler's outcome as `processing_status`.

6. **Interplay note (document in code where the decision lives, not as narration):** the internal midnight safeguard (`AUTO_CLOCK_OUT_OPEN_SHIFTS`) may close a shift before Connecteam's own `auto_clock_out` arrives; the later webhook then lands on the `no_open_shift` no-op path — correct and expected. No coordination logic is needed or wanted.

7. **Tests** — extend `backend/tests/connecteam/` (DB-backed, following existing fixtures):
   - `test_clock_in_handler.py`: mapped clock_in creates `STARTED_SHIFT` + open `IDLE` records with `manually_recorded=False`, `changed_by_id == worker.user_id`, `entered_at == occurred_at`; duplicate clock_in → no new records, outcome `already_clocked_in`, task completes.
   - `test_clock_out_handler.py`: closes open shift, writes `ENDED_SHIFT`, transitions an open `WORKING` step record to `ENDED_SHIFT`/`PAUSE_ENDED_SHIFT`, logs the count; clock_out with no shift → no-op outcome; `exited_at == occurred_at`.
   - `test_auto_clock_out_handler.py`: same close semantics; log distinguishes auto; after internal midnight safeguard already closed → no-op.
   - `test_handler_idempotency.py`: simulate retry-after-commit (run handler twice with same event) → second run is the ConflictError no-op; unexpected exception propagates out of the handler (assert raise, not swallow).
   - `test_toggle_parity.py`: records produced by the webhook clock_in/clock_out match the shape produced by `toggle_worker_shift` for the same user (field-by-field on the state records) — the "same mechanism as the endpoint" guarantee, pinned by test.
   - Update phase-1 `test_dispatcher.py` no-write assertion: it must now assert no writes **only for unmapped and manual_break paths**.

8. **Live ngrok validation** — extend `VALIDATION_connecteam_webhook_ngrok.md`: with a mapped profile, clock in on Connecteam → verify open `IDLE` record and UI state; start a working step, clock out on Connecteam → verify shift closed and step paused with `PAUSE_ENDED_SHIFT`; verify the duplicate-delivery no-op by requeueing a completed event via the phase-1 CLI.

## Risks and mitigations

- Risk: Out-of-order delivery (clock_out processed before its clock_in, or a late clock_out after the next day's clock_in) mis-attributes shift boundaries.
  Mitigation: Single shared `tasks-worker` serializes processing in arrival order; `ConflictError` guards absorb inverted sequences as no-ops rather than corrupting state; the residual case (late clock_out closing a *newer* shift) is bounded by Connecteam's 3-retry delivery window vs. the shift cadence, and its blast radius is one mis-closed shift, repairable manually — accepted for this phase and noted for a future sequencing guard (compare `occurred_at` with the open shift's `entered_at`).
- Risk: Event `occurred_at` clock skew vs. backend time produces shifts that appear to start "in the past/future".
  Mitigation: Connecteam epoch timestamps are server-side, not device-side (observed in discovery); no clamping this phase; parity tests pin the timestamp source so the decision is explicit.
- Risk: Retry after successful commit double-applies the action.
  Mitigation: The primitives' ConflictError guards make re-application a no-op; test `test_handler_idempotency.py` pins this.
- Risk: Toggle-literal interpretation regresses into the flip hazard if Clarification 1 is resolved against the recommendation.
  Mitigation: The clarification documents the failure mode concretely; if the owner still chooses literal toggle, handlers must at minimum verify desired end-state before invoking it (making it equivalent to the recommendation anyway).
- Risk: A second `tasks-worker` instance processes two events for the same worker concurrently.
  Mitigation: `load_open_worker_shift_for_update` takes a row lock per worker inside both primitives; the transaction spanning resolve+action keeps the lock for the whole unit.

## Validation plan

- `cd backend/app && .venv/bin/python -m pytest ../tests/connecteam -q`: all phase-1 and phase-2 suites pass.
- `.venv/bin/ruff check beyo_manager`: no new violations.
- Grep guard: `grep -rn "toggle_worker_shift\|_clock_worker_shift" beyo_manager/services/tasks/connecteam` shows imports of the two primitives only — no copies of their logic.
- Diff guard: `toggle_worker_shift.py`, `_clock_worker_shift.py`, `_worker_shift_access.py`, `worker_base.py` are byte-identical to before the phase.
- Live flow per updated `VALIDATION_connecteam_webhook_ngrok.md`: Connecteam clock-in → open shift visible; Connecteam clock-out → shift closed, working step paused; duplicate → no-op logged; `SELECT` on `user_shift_state_records` confirms `manually_recorded=false`, `changed_by_id = <worker>`, timestamps = Connecteam event times.

## Review log

- `2026-07-20` `claude (plan author)`: Initial draft. Clarification 1 (toggle-literal vs intent-aware primitives) and Clarification 2 (timestamp source) await owner sign-off; plan is written against the recommendations.
- `2026-07-20` `owner (David)`: Both clarifications resolved per recommendation — intent-aware primitives (`clock_in_shift_for_user`/`clock_out_shift_for_user`); shift timestamps from Connecteam `occurred_at` with `received_at` fallback. Status moved to `approved`.
- `2026-07-20` `codex`: Implemented the phase-2 handlers, atomic resolve-plus-action transaction, terminal ConflictError no-op outcomes, structured logs, timestamp fallback, and focused unit/DB parity coverage. Protected shared files remained byte-identical.
- `2026-07-20` `codex`: Automated validation passed: 18 Connecteam tests, scoped Ruff, and compilation. Repository-wide Ruff still reports pre-existing violations outside this phase's files; no new phase-2 violations were found.
- `2026-07-20` `codex`: Live ngrok validation requires a human Connecteam clock-in/out and remains pending; archival proceeds with that follow-up explicitly recorded.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_connecteam_clock_actions_20260720.md`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_connecteam_clock_actions_20260720.md`
