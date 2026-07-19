# PLAN_worker_shift_state_recording_20260720

## Metadata

- Plan ID: `PLAN_worker_shift_state_recording_20260720`
- Status: `archived`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-20T00:00:00Z`
- Last updated at (UTC): `2026-07-20T00:00:30Z` (implementation completed, summarized, and archived)
- Related issue/ticket: `n/a` (originates from linear-timeline live-DB validation: cross-day pause bleed)
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_worker_shift_state_recording_20260720.md` (optional — design intent captured in this plan's Goal section)
- **Supersedes:** `PLAN_linear_pause_semantics_and_stale_close_20260719.md` (classification-filter + stale-close scheduler). That plan patched the *symptoms* of a missing shift signal; this plan records the signal itself.

## Goal and intent

- **Goal:** Populate the existing (currently empty) `UserShiftStateRecord` table as the worker's **recorded linear timeline** — one open state per worker at all times between clock-in and clock-out (`WORKING` / `IN_PAUSE` / `IDLE`, bounded by `STARTED_SHIFT` / `ENDED_SHIFT`) — with **full clock-in/clock-out machinery from day one** (commands + routers + safeguards), state derived at **write time** from step transitions via an idempotent, transport-agnostic reconcile service; then read the linear worker-stats endpoints straight off these records instead of inferring the timeline from step-record sweeps.
- **Business/user intent:** A manager must see where a worker's shift actually went: worked, on a recorded pause (with the reason from the paused step), or idle (present, nothing active). Today this is *inferred* from step records, which is fragile: open pauses bleed across days (a 3-week-old lunch shows as 6–20 h of pause/idle on unrelated days), post-shift hours read as idle, and no-activity days show phantom time. Recording the worker's state directly makes the timeline gapless by construction and immune to all of these, and unlocks accurate labor-cost reporting (`UserWorkProfile.salary_per_hour_*`) later.
- **Non-goals:**
  - The user-defined **pause-reasons table** and pause-category classification. Fully deferred — the state machine needs neither (any recorded step pause → `IN_PAUSE`; the reason value is copied onto the shift record's `reason` column, the table will later back that same slot).
  - Realtime/socket emission of worker shift-state changes (presence UX). Can be layered on later; the reconcile service is the natural emission point.
  - Auto-closing stale **step** records (`/totals` aggregate hygiene). Superseded plan's Part B is dropped; open step pauses after clock-out are *off-shift* on the read side and therefore harmless to this feature.
  - Changing `/totals`, `/{user_id}/daily-steps`, or `UserDailyWorkStats` semantics.
  - Night-shift support across midnight (see Risks — accepted limitation for this workshop's day-shift operation).

## Scope

- **In scope:**
  1. **Migrations:** add `IDLE` to `user_shift_state_enum`; add a nullable free-string `reason` column and a `manually_recorded` boolean (default false) to `user_shift_state_records`; add the safeguard scheduler/task enum values (`RecurringSchedulerTypeEnum` + execution `TaskType`) for the midnight auto-clock-out.
  2. **Pure domain state machine** for worker shift state: target-state derivation from open-step counts, allowed transitions, boundary semantics.
  3. **Transport-agnostic reconcile service** `reconcile_worker_shift_state(session, workspace_id, user_id, now)` — idempotent, per-worker-serialized, callable from *any* worker handler, command, or backfill (owner may change the executing worker later; this function is the stable seam). Includes the **auto-clock-in safeguard**.
  4. **Clock-in / clock-out commands + routers** — full user-facing machinery from day one — plus **worker self-service shift pause/resume**: a worker can mark their own shift `IN_PAUSE` with a free-text `reason` (curing idle time) and resume back to `IDLE`.
  5. **Midnight auto-clock-out safeguard** — recurring-scheduler task that clock-outs any shift left open from a previous day, stamped at 00:00.
  6. **Write hook:** one call from the current analytics handler (`handle_process_step_transition`) after its existing reconcile, same session/transaction.
  7. **Read swap:** re-implement the two linear endpoints (`GET /worker-stats/linear-timeline`, `GET /worker-stats/{user_id}/linear-timeline`) to read `UserShiftStateRecord` intervals + join overlapping `StepStateRecord`s, **keeping the delivered response contracts backward-compatible with additive-only extensions** (marker segments, `manually_recorded`) per `HANDOFF_TO_FRONTEND_worker_stats_linear_timeline_20260719.md`. Swap ships with the machinery (hard cutover — records flow from day one via auto-clock-in); backfill fills history at rollout.
  8. **Backfill:** operational script reusing the existing sweep (`compute_linear_segments`) to reconstruct historical `UserShiftStateRecord`s so past dates aren't blank after the swap.
- **Out of scope:** pause table, realtime presence events, step-record hygiene jobs, non-UTC day boundaries, night shifts spanning midnight.
- **Assumptions:**
  - `UserShiftStateRecord` schema is final enough: `user_id, workspace_id, state, entered_at, exited_at, changed_by_id` + unique partial index on the open record (`exited_at IS NULL`). Verified in model; table is empty in live DB (0 rows).
  - `PROCESS_STEP_TRANSITION` outbox events fire per step (batch of N steps ⇒ N events) and the existing handler is recompute-idempotent — verified in `process_step_transition.py`.
  - Shift-state records carry a nullable free-string **`reason`** (decision revised 2026-07-20, rev 3): a **derived** `IN_PAUSE` stores the earliest open paused step's reason value; a **manual** worker pause stores the worker's free text; other states leave it NULL. Roster `pause_by_reason` reads straight off shift records (no join needed for totals); the step-record join remains for drill-down `steps[]` detail. Free-text reasons flow into `pause_by_reason` keys — the delivered handoff already declares that key set open, so no frontend contract change. This column is the forward-compatible slot the future user-defined pause-reasons table will back.
  - **Manual-pause stickiness:** manual records are distinguished by a dedicated boolean **`manually_recorded`** (default false). `changed_by_id` records *who* acted (and is also set on manager-on-behalf clock actions), while the flag records *origin* — unambiguous, and it serializes straight into the timeline so manual pauses render distinctly with no extra query. The reconcile never displaces a manual `IN_PAUSE` with `IDLE`; only `WORKING` (worker starts a task), an explicit resume, clock-out, or the midnight safeguard ends it.
  - Boundary markers: `STARTED_SHIFT` and `ENDED_SHIFT` are **instantaneous marker records, written closed** (`exited_at = entered_at`, zero duration); `WORKING`/`IN_PAUSE`/`IDLE` are the durationful states between them. They must not stay open: the unique partial index tolerates one open row per worker, and the system-wide invariant is *open record ⟺ worker currently on shift* — an eternally-open marker would break both. Markers **are returned in the drill-down as zero-duration marker segments** so the frontend renders clock-in/clock-out ticks on the timeline. Manual clock-in writes `STARTED_SHIFT` then opens `IDLE`; auto-clock-in writes `STARTED_SHIFT` and lets the reconcile open the correct state (typically `WORKING`, since it was triggered by a task start).
  - **Clock permissions (proposed default, veto in review):** workers clock themselves; `ADMIN`/`MANAGER` may clock on behalf of a worker, recorded via `changed_by_id`. Safeguard-written records carry `changed_by_id = NULL`.

## Clarifications required

All resolved with product owner (2026-07-20):

- [x] **No-open-shift behavior** — RESOLVED: **auto-clock-in**. When a worker starts working a task with no open shift, the shift is opened automatically with `STARTED_SHIFT` stamped at the moment the task work began (the working record's `entered_at`, not event-processing time). Supersedes the earlier skip+log proposal — self-healing from day one.
- [x] **Rollout / read-swap gating** — RESOLVED: **no gated dual-read period**. Clock-in/out services + routers are built in this plan ("full functional machinery from day one"); the read swap ships with it as a hard cutover, with the backfill run at rollout to fill history. Auto-clock-in guarantees records flow forward from deploy even before workers adopt the clock habit.
- [x] **Forgotten clock-out** — RESOLVED: **recurring-scheduler safeguard**. A daily recurring task clock-outs any shift still open from a previous day, stamping the clock-out at **00:00** (the midnight boundary ending the shift's start day). It reuses the same clock-out command as the manual path (so open WORKING steps → `ended_shift`, paused steps left open — identical semantics).

## Acceptance criteria

1. Migrations add `IDLE` to `user_shift_state_enum`, the `reason` + `manually_recorded` columns on `user_shift_state_records`, and the safeguard scheduler/task enum values; `alembic upgrade head` applies cleanly; downgrade paths documented (PG enum values are not removable — enum downgrade is a documented no-op; column downgrades drop them).
2. The pure state machine is exhaustively unit-tested: every `(open_working_count, open_paused_count)` combination maps to exactly one target state (the on-shift gate and shift-scoping of the counts live in the reconcile, not the pure function); boundary markers never returned as targets.
3. `reconcile_worker_shift_state` is **idempotent** (calling it N times with unchanged inputs writes at most one transition) and **per-worker serialized** (concurrent invocations for one worker cannot violate the unique open-record index) — proven by an integration test with two concurrent reconciles.
4. A step transition for an on-shift worker produces the correct shift-state record: last working step paused → `IN_PAUSE` **carrying the earliest open paused step's reason**; last working step completed → `IDLE`; any step started → `WORKING`; a batch of N simultaneous transitions converges to a **single** state change.
5. **Auto-clock-in:** a step transition to working for a worker with **no** open shift creates `STARTED_SHIFT` at the working record's `entered_at` and converges to `WORKING` — verified by test. Non-working events with no open shift remain a no-op + structured log.
6. Derivation is **shift-scoped**: an open paused step from a *previous* shift does not pull a freshly clocked-in worker out of `IDLE` (test reproduces the "clocked out during late lunch, clocked in next day" case).
7. **Clock toggle route (`POST /clock`):** with no open shift → clock-in (`STARTED_SHIFT` marker, closed instantly, + opens `IDLE`); with an open shift → clock-out (every open WORKING step → `ended_shift` via the existing transition command, paused steps left open, durationful record closed, `ENDED_SHIFT` marker written closed); response reports which action ran. **Pause route:** from `IDLE` only, records `IN_PAUSE` with required free-text `reason`, `manually_recorded = true`, `changed_by_id`; **sticky** — a subsequent reconcile never reverts it to `IDLE`, but starting a task (`WORKING`) ends it. **Resume route:** manual `IN_PAUSE` → `IDLE`; `409` otherwise. All covered by integration tests including the permission matrix.
8. **Midnight safeguard:** a shift left open from a previous day is clock-outed at 00:00 by the recurring task (same semantics as manual clock-out); next day starts clean; verified by test. Records written by the safeguard have `changed_by_id = NULL`.
9. After the read swap, both linear endpoints are **backward-compatible with the delivered handoff contract**: every existing key/shape unchanged (contract tests assert key-sets and reconciliation invariants: buckets partition the shift, `pause_by_reason` sums to `pause_seconds`, durationful `segments` sum to `timeline`), with only additive extensions — `started_shift`/`ended_shift` zero-duration marker segments and `manually_recorded` on segments. The live bleed cases (3-week lunch, post-shift idle, 20 h ended-shift) show zero bleed.
10. Backfill reconstructs a known historical day such that read-from-records equals the sweep's output for that day (equivalence test), and is idempotent (re-run ⇒ no duplicates).
11. Full worker-stats + analytics suites green; ruff clean.

## Contracts and skills

### Contracts loaded

Selected per `task_system/backend_contract_goal_mapping_guide.md` — core + **Worker-driven backend** bundle + explicit triggers ("worker", "stale task") + model/migration/router needs.

Selected contracts:
- `../architecture/01_architecture.md`: layering — pure machine in domain, reconcile + clock commands in services, hook in worker handler, routes in routers.
- `../architecture/03_models.md`: reading/extending the `UserShiftStateRecord` model and enum column conventions.
- `../architecture/04_context.md`: `ServiceContext` for the clock commands/routes; explicit-session signature for the worker-called reconcile.
- `../architecture/05_errors.md`: `409` on double clock-in; conflict/retry shape in the reconcile.
- `../architecture/06_commands.md` + `06_commands_local.md`: write-path structure, `maybe_begin`, session-call safety, subordinate-command event rule (reconcile emits no events of its own; clock-out delegates step closures to the existing transition command).
- `../architecture/07_queries.md` + `07_queries_local.md`: the read-swap query services; offset pagination (local override) already in use by the roster endpoint.
- `../architecture/08_domain.md`: the state machine is pure domain logic (no I/O), same discipline as `domain/analytics/linear_timeline.py`.
- `../architecture/09_routers.md`: the new clock-in/clock-out routes; existing linear routes unchanged in wiring.
- `../architecture/11_infra_events.md` + `../architecture/42_event.md`: consuming `PROCESS_STEP_TRANSITION` outbox events; atomicity of the hook with the handler's transaction.
- `../architecture/16_background_jobs.md`, `../architecture/12_infra_redis.md`, `../architecture/51_worker_runtime.md`: worker runtime semantics — delivery/ordering guarantees motivating the row-lock serialization; registering the midnight-safeguard task; how a future worker swap re-homes the hook.
- `../architecture/30_migrations.md`: PG enum `ADD VALUE` migrations and irreversibility handling.
- `../architecture/21_naming_conventions.md`: naming the domain module, services, routes, task type, backfill script.
- `../architecture/15_testing.md`: unit vs. integration placement; concurrency test pattern.
- `../architecture/40_identity.md`, `41_user.md`, `48_presence.md` (core): user identity fields; role checks for clock-on-behalf; shift ≠ connection presence (explicitly not merged).
- `../architecture/49_observability_runtime.md`: structured logs for auto-clock-in, safeguard clock-outs, and reconcile transitions.
- `../architecture/53_operational_cli.md`: the backfill as an operational script.

Added from guide:
- `16`, `12`, `51`: trigger "worker" — hook runs inside the outbox worker; midnight safeguard registers as a scheduler-fired task; serialization guarantees stated from `51`, not assumed.
- `53`: backfill is operator-run tooling.

Local extensions loaded:
- `06_commands_local.md`: `maybe_begin` + session-call safety + subordinate-command event rule (reconcile is subordinate — the owning handler/command controls commit and events).
- `07_queries_local.md`: offset pagination override (roster endpoint unchanged).

Excluded contracts:
- `13_sockets.md`: no realtime emission in this plan (non-goal; future layer).
- `52_replayability.md`: reconcile is derivation-based and idempotent — replay-safe by construction, no replay machinery added.
- `55` (search): no filter/search surface.
- `18` (rate limit), `34` (uploads), `22` (bulk insert): not applicable.

### File read intent — pattern vs. relational

Relational reads already performed (what exists — legitimate):
- `models/tables/users/user_shift_state_record.py`, `domain/users/enums.py` — exact schema, states, unique open index.
- `services/tasks/analytics/process_step_transition.py` — handler is recompute-idempotent; loads user/step; where the hook lands.
- `services/commands/task_steps/_step_transition_core.py`, `transition_step_state.py`, `transition_step_state_batch.py` — per-step outbox emission; batch ⇒ N events; "no open record ⇒ ConflictError" invariant (why clock-out must delegate to the transition command).
- `services/infra/schedulers/recurring_scheduler_runner.py`, `domain/schedulers/enums.py` — scheduler type → task type dispatch for the midnight safeguard.
- `domain/analytics/linear_timeline.py`, `services/queries/worker_stats/*` — current read path to be swapped; sweep to be reused as backfill.
- Live DB — `user_shift_state_records` is empty (0 rows); bleed cases (Mykola/Andrii) verified against raw records.

Prohibited pattern reads (contract already covers): another command for write-path skeleton → `06`; another router for handler wiring → `09`; another worker handler for handler shape → `16`/`51`.

### Skill selection

- Primary skill: none dedicated — document-only protocol from `task_system/backend_contract_goal_mapping_guide.md`.
- Router trigger terms: `worker`, `stale task`, `background job`.
- Excluded alternatives: CRUD+realtime bundle as primary — clock routes are a thin command surface, not a realtime CRUD domain; realtime explicitly deferred.

## Implementation plan

### Part A — Migrations + pure domain state machine

1. **Alembic migration(s):** `ALTER TYPE user_shift_state_enum ADD VALUE 'idle'` (+ `IDLE = "idle"` on `UserShiftStateEnum`); add nullable `reason` `String(512)` and `manually_recorded` `Boolean` (server default false) columns to `user_shift_state_records` (+ model fields); add the safeguard values to `RecurringSchedulerTypeEnum` (e.g. `AUTO_CLOCK_OUT_OPEN_SHIFTS`) and execution `TaskType`, wired into `RECURRING_TYPE_TO_TASK_TYPE`. Enum downgrades documented as no-ops per `30_migrations.md`; the column downgrades drop them.
2. **New pure module** `beyo_manager/domain/users/shift_state_machine.py`:
   - `DURATIONFUL_STATES = {WORKING, IN_PAUSE, IDLE}`; `BOUNDARY_MARKERS = {STARTED_SHIFT, ENDED_SHIFT}`.
   - `derive_target_state(open_working_count: int, open_paused_count: int) -> UserShiftStateEnum`:
     `≥1 working → WORKING`; `0 working, ≥1 paused → IN_PAUSE`; `else → IDLE`. Pure, exhaustive, no I/O. **The counts are shift-scoped by the caller** — only open steps entered during the *current* shift (Part B step d); a previous shift's lingering open pause is invisible to the derivation.
   - Transition-validity helper (durationful ↔ durationful; markers only at boundaries) for defensive assertions in the reconcile.
3. **Unit tests** (`tests/unit/domain/users/test_shift_state_machine.py`): exhaustive derivation table; markers never derivable; validity matrix.

### Part B — Transport-agnostic reconcile service (the stable seam)

4. **New service** `beyo_manager/services/commands/users/reconcile_worker_shift_state.py`:
   - Signature: `async def reconcile_worker_shift_state(session, workspace_id: str, user_id: str, now: datetime) -> ShiftReconcileOutcome` — plain session, no `ServiceContext`, no event dispatch (subordinate per `06_local`). **This is the seam:** whichever worker/command calls it, behavior is identical; swapping the executing worker later is a one-line re-home.
   - Algorithm:
     a. `SELECT … FOR UPDATE` the worker's open shift record (unique partial index guarantees ≤1).
     b. **No open shift:** if the worker has ≥1 open WORKING step → **auto-clock-in**: write `STARTED_SHIFT` marker stamped at the earliest open working record's `entered_at`, **clamped to `max(entered_at, latest ENDED_SHIFT marker for this worker)`** so a late-arriving event can never open a shift overlapping the previous shift's close; then continue to (c). Otherwise → no-op + structured log (non-working events never invent a shift).
     c. Resolve the current shift's start (latest `STARTED_SHIFT` marker ≤ now for this worker).
     d. Count the worker's open `StepStateRecord`s **entered at/after shift start** (shift-scoped — a previous shift's lingering open pause is invisible): `open_working`, `open_paused` (credited via `COALESCE(credited_user_id, created_by_id)`, live steps only).
     e. `target = derive_target_state(...)`. **Stickiness guard:** if the current open record is a *manual* `IN_PAUSE` (`manually_recorded = true`) and `target == IDLE` → no-op (the derivation never cures a worker's own pause; only `WORKING`, explicit resume, clock-out, or the safeguard ends it). If `target == current.state` → no-op (idempotent). Else close current (`exited_at = now`) and open the target record (`entered_at = now`, `manually_recorded = false`); when `target == IN_PAUSE`, set `reason` from the earliest open paused step's reason value.
   - **Concurrency:** the `FOR UPDATE` row-lock serializes per worker; an `IntegrityError` on the unique open index (race on first open, incl. auto-clock-in races) → retry once (reconcile is idempotent, retry converges).
5. **Integration tests:** idempotency (double call, one transition); concurrency (two parallel reconciles, index never violated); shift-scoping (previous-shift open pause ignored → `IDLE` after clock-in — acceptance 6); auto-clock-in (acceptance 5).

### Part C — Clock-in / clock-out commands + routers + midnight safeguard

6. **Commands** (`beyo_manager/services/commands/users/`):
   - `clock_in_worker_shift.py`: validates no open shift (`409` ConflictError otherwise); writes `STARTED_SHIFT` marker (closed instantly) + opens `IDLE`. `changed_by_id` = acting user when acting on behalf.
   - `clock_out_worker_shift.py`: for every open WORKING step of the worker → delegate to the existing `transition_step_state` machinery targeting `ended_shift` (respects the one-open-record-per-step invariant and emits the analytics events); **leave paused steps open** (a late lunch across clock-out remains truthful; off-shift time is unbounded on the read side); close the open durationful shift record (manual pauses included); write `ENDED_SHIFT` marker. Accepts an explicit `clock_out_at` (used by the midnight safeguard); defaults to now.
   - `pause_worker_shift.py`: worker marks their own shift `IN_PAUSE` with a required free-text `reason` (curing idle). Valid only from an open `IDLE` (or `WORKING`? — no: pausing while steps are working is done by pausing the steps; command rejects with `409` unless current state is `IDLE`). Writes the manual `IN_PAUSE` record with `reason`, `manually_recorded = true`, and `changed_by_id = acting user`.
   - `resume_worker_shift.py`: ends a manual `IN_PAUSE` → opens `IDLE`. Rejects (`409`) if the current open state is not a manual `IN_PAUSE`. (Starting a task also ends it naturally — `WORKING` wins via the reconcile.)
7. **Routes** (new router module, e.g. `routers/api_v1/worker_shifts.py`): **`POST /clock` — a single toggle endpoint** that dispatches on current state (no open shift → clock-in; open shift → clock-out; response reports which action was taken) — plus `POST /pause` (body: `reason`) and `POST /resume`. The two clock *commands* stay separate internally (thin router dispatch per `09`). Self-service for workers; `ADMIN`/`MANAGER` may pass a target `user_id` to act on behalf (recorded via `changed_by_id`). Wired in `routers/api_v1/__init__.py`.
8. **Midnight safeguard:** task handler under `services/tasks/users/` fired by the recurring scheduler (daily, shortly after 00:00): find shifts still open whose `STARTED_SHIFT` day < today; invoke `clock_out_worker_shift` with `clock_out_at = 00:00` of the current day (end of the shift's start day); `changed_by_id = NULL`. **Registering the scheduler entry:** investigate how `RecurringScheduler` rows are created in this app (`origin_source` COMMAND vs WORKER, see `services/infra/schedulers/recurring_scheduler_runner.py` and the scheduler model) and use the established path; if no precedent exists for a system-owned recurring scheduler, seed the row in the migration (interval = 1 DAY) and document that choice in the implementation summary.
9. **Integration tests:** route permission matrix; `/clock` toggle dispatch (clock-in with no shift, clock-out with one; the `clock_in` *command*'s `409` guard when invoked directly with an open shift); clock-out closes WORKING steps + leaves paused; manual pause records `reason` + `manually_recorded` + `changed_by_id`; **stickiness** (a reconcile firing during a manual pause does not revert it to `IDLE`; starting a task does end it); resume `409` outside manual pause; safeguard caps a forgotten shift at 00:00 (manual pause included) and next day starts clean (acceptance 7–8).

### Part D — Write hook (current worker; swappable)

10. **One call** in `handle_process_step_transition` after the existing time-reconcile, same session/transaction: `await reconcile_worker_shift_state(session, payload.workspace_id, payload.credited_user_id, now)` (guarded on `credited_user_id`). Batch fan-out (N events) converges by idempotency — no coalescing needed for correctness.
11. **Integration tests:** working→last-pause ⇒ `IN_PAUSE`; last-complete ⇒ `IDLE`; start ⇒ `WORKING` (incl. auto-clock-in path end-to-end through the handler); batch of N ⇒ exactly one shift transition.

### Part E — Backfill + read swap (ships with the machinery)

12. **Backfill script** (operational CLI per `53`): per worker × historical day, run the existing sweep (`compute_linear_segments` over step records) and write the equivalent `UserShiftStateRecord` rows (activity-envelope-bounded, since no real clock data exists historically). **Explicit segment→record mapping:** synthesize a closed `STARTED_SHIFT` marker at the day's first sweep segment's start; sweep `working` → `WORKING`, `paused` → `IN_PAUSE` (copy the segment's reason), `idle` → `IDLE`; a sweep `ended_shift` segment **terminates the day's shift** — write the `ENDED_SHIFT` marker at that segment's start and ignore the remainder of the day; otherwise write `ENDED_SHIFT` at the last segment's end. All rows `manually_recorded = false`, `changed_by_id = NULL` (marks *reconstructed* data). Idempotent: delete-and-rewrite per (worker, day) or skip-if-present. Run at rollout before the swap goes live.
13. **Read swap:** new query implementations behind the existing two endpoints:
    - Roster totals: sum durationful `UserShiftStateRecord` intervals per state over the range; `pause_by_reason` now reads **directly off the shift records' `reason`** (derived and manual pauses alike — free-text keys allowed, contract already open); `completed_count` via the (already-built) step-record join.
    - Drill-down: shift records **are** the segments — the durationful states (`working`/`in_pause`/`idle`, incl. manual pauses with their free-text reason) **plus the `started_shift`/`ended_shift` markers as zero-duration marker segments**, so the timeline granularity shows clock-in/clock-out ticks. Each segment serializes `manually_recorded` (and `reason`) directly from the record — manual pauses render distinctly with no extra query. Join overlapping `StepStateRecord`s per durationful interval for `steps[]` (record times, `ended_by`, item labels — logic reused from the current implementation; marker/idle segments carry `steps: []`).
    - **Response contracts additive-only:** contract tests assert every existing key/shape from the delivered handoff is unchanged; the swap adds (a) marker segments with the two new `state` values and `seconds: 0`, and (b) the `manually_recorded` field on segments. No existing field changes meaning or shape.
14. **Handoff addendum:** short update to `HANDOFF_TO_FRONTEND_worker_stats_linear_timeline_20260719.md` documenting the tightened semantics (off-shift time excluded; idle = recorded on-shift gap; live `is_open` behavior unchanged) and the **additive** shape extensions: `started_shift`/`ended_shift` marker segments, `manually_recorded` on segments, and free-text `pause_by_reason` keys (key set already declared open).

## Risks and mitigations

- Risk: PG enum `ADD VALUE` is irreversible; a bad rollout can't drop the new values.
  Mitigation: additive-only values; downgrade documented no-op; nothing writes `IDLE` until Part B ships.
- Risk: concurrent per-worker events double-open a shift state (incl. auto-clock-in races on the very first event).
  Mitigation: `FOR UPDATE` serialization + unique partial index as backstop + single idempotent retry; dedicated concurrency test (acceptance 3).
- Risk: derived shift records drift from step-record truth (missed event, handler bug).
  Mitigation: reconcile derives from *current* open-step state (not event deltas) so any later event self-heals; backfill doubles as a repair tool for a (worker, day).
- Risk: owner changes the executing worker; hook orphaned.
  Mitigation: all logic in the transport-agnostic service (Part B); the hook is one line — re-homing is trivial and stated as a supported operation.
- Risk: hard cutover changes numbers the frontend already renders (semantics tighten: off-shift excluded).
  Mitigation: existing shape frozen (additive-only extensions) + contract tests; semantic change documented in the handoff addendum; backfill runs before the swap so history isn't blank; the first shipped numbers are already the correct ones.
- Risk: **night shift spanning midnight** — the safeguard clock-outs at 00:00, splitting a genuine overnight shift; the span between 00:00 and the worker's next step action is lost until auto-clock-in reopens.
  Mitigation: accepted limitation (workshop runs day shifts); documented; the safeguard only targets shifts opened on a *previous* day, and auto-clock-in reopens on the next action. Revisit if night shifts become real.
- Risk: auto-clock-in stamps `STARTED_SHIFT` in the past (working record's `entered_at`) — could overlap a prior `ENDED_SHIFT` if events arrive very late.
  Mitigation: clamp the auto stamp to `max(entered_at, last ENDED_SHIFT marker)`; covered by a test.
- Risk: the derivation **stomps a manual pause** — any reconcile firing while a worker is manually `IN_PAUSE` computes `IDLE` (0 working, 0 paused steps) and would revert their pause.
  Mitigation: stickiness guard in the reconcile (manual `IN_PAUSE`, identified by `manually_recorded = true`, is never displaced by `IDLE`; `WORKING` still wins); dedicated test (acceptance 7).
- Risk: free-text manual reasons fragment `pause_by_reason` keys (typos, variants) and weaken aggregation.
  Mitigation: accepted for now — the delivered contract declares the key set open; the planned user-defined pause-reasons table is the real fix (this column is its forward-compatible slot).
- Risk: safeguard reuses the clock-out command, which transitions steps → emits analytics events at 00:05 for a 00:00 boundary.
  Mitigation: explicit `clock_out_at` parameter keeps stamps at 00:00 regardless of run time; analytics reconcile is date-scoped by record times, not processing time.

## Validation plan

- `pytest tests/unit/domain/users/test_shift_state_machine.py -q`: exhaustive derivation + validity — all pass.
- `pytest tests/integration/services/commands/users/ -q`: reconcile (idempotency, concurrency, shift-scoping, auto-clock-in), clock-in/out commands, permission matrix — all pass.
- `pytest tests/integration/services/tasks/ -q`: write hook through the handler; batch convergence; midnight safeguard — all pass.
- `pytest tests/integration/services/queries/worker_stats -q`: contract tests — backward-compatible with the delivered handoff (existing keys unchanged; only the additive marker segments + `manually_recorded`); reconciliation invariants hold.
- Backfill equivalence: run backfill for a seeded day → read-from-records equals sweep output for that day; re-run → no duplicates.
- `alembic upgrade head` (and documented no-op downgrades): applies cleanly.
- Manual: re-run the two live validation queries (2026-07-16 and 2026-07-19 roster) post-swap — Mykola shows no pre-shift lunch bleed, no post-shift idle; Andrii/Tetiana show no 20 h ended-shift.
- `ruff check`: clean.

## Review log

- `2026-07-20` implementer: `Codex` — all 11 acceptance criteria verified; Parts A–E committed independently; final worker-shift, worker-stats, and analytics suite passed (149 tests); touched Python files Ruff-clean; Alembic head `b4074f2e26c4` applied successfully; plan summarized and archived.
- `2026-07-20` implementer: `Codex` — implementation started against approved rev 4; contracts loaded canonical-first with app-local companions taking precedence.
- `2026-07-20` owner: clarifications 1–3 resolved — auto-clock-in on first task start; full clock machinery in scope, hard cutover with backfill at rollout; midnight recurring-scheduler safeguard reusing the clock-out command. Plan revised accordingly (rev 2).
- `2026-07-20` owner: added free-string `reason` on `UserShiftStateRecord` (derived pauses carry the paused step's reason; manual pauses carry worker free text) + worker self-service pause/resume routes to cure idle time. Rev 3 adds the manual-pause stickiness rule so the reconcile never reverts a worker's own pause to `IDLE`.
- `2026-07-20` owner (rev 4): markers confirmed **written closed** (`exited_at = entered_at`; the unique open index + "open record ⟺ on shift" invariant forbid open markers) and returned as zero-duration marker segments in the drill-down; clock-in/out collapsed into a single `POST /clock` toggle route (commands stay separate); `manually_recorded` boolean added (origin flag — `changed_by_id` alone is ambiguous under manager-on-behalf) and used for stickiness + serialized on segments; state-machine doc clarified that derivation counts are shift-scoped; response contract restated as additive-only.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `Codex`
