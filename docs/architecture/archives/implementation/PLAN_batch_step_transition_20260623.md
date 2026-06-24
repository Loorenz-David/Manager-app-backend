# PLAN_batch_step_transition_20260623

## Metadata

- Plan ID: `PLAN_batch_step_transition_20260623`
- Status: `archived`
- Owner agent: `claude-opus-4-8`
- Created at (UTC): `2026-06-23T00:00:00Z`
- Last updated at (UTC): `2026-06-23T12:15:00Z`
- Related issue/ticket: `<none>`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_batch_step_transition_20260623.md` (optional, not yet authored)

## Goal and intent

- Goal: Add a workspace-scoped endpoint that transitions **1..N** batch-capable task steps to a single target state in one atomic, efficient operation, reusing the existing single-step transition logic so all sub-processes (state machine, record close/open, metrics, task side-effects, outbox, notifications, realtime events) stay identical and correct.
- Business/user intent: Working sections marked `allows_batch_working` are worked in batches. The frontend exposes one button per transition (`pending→working`, `working→paused`, `paused→working`, `working→completed`) that must move the worker's whole active batch group at once. Issuing N single calls works but is chatty and non-atomic; this gives one reliable call.
- Non-goals:
  - No change to the one-active-step guard for non-batch steps. The batch path only accepts batch-capable steps and never runs auto-pause.
  - No per-step heterogeneous target states in one request (the button applies one `new_state`; each step's *current* state is validated individually).
  - No schema/model/migration changes.
  - No changes to worker/consumer logic for `PROCESS_STEP_TRANSITION` / `CREATE_NOTIFICATIONS` tasks (we only emit them, coalesced).
  - No removal/breaking of the existing single-step transition endpoint.

## Scope

- In scope:
  - New request schema + parser for the batch transition.
  - New router handler `POST /api/v1/tasks/steps/transition-batch` in `routers/api_v1/tasks.py`.
  - Add a reusable, transaction-free, dispatch-free **core** (`_apply_step_transition`) for the batch command. The existing `transition_step_state` is left unchanged except for a drift-warning comment.
  - New top-level command `transition_step_state_batch` (atomic two-phase, batched I/O, coalesced events/notifications).
  - Coalesced realtime event + deduped notifications for the batch.
  - Integration tests for the four transitions, atomic rejection, coalescing, cross-task batch, and non-batch rejection.
  - Frontend handoff doc for the new endpoint.
- Out of scope:
  - Single-endpoint changes (Option B): `transition_step_state` keeps its current request/response **and inline implementation**; the only edit is a drift-warning comment pointing at the batch core.
  - `mark_closing_record_inaccurate` support in the batch path (v1 omits it; see Clarifications).
  - Heterogeneous per-step `new_state`, partial-success semantics (we chose atomic all-or-nothing).
- Assumptions:
  - The batch group is homogeneous at press time (all share the same current state), but the command still validates each step's transition independently and rejects the whole batch on any invalid item.
  - Batch steps never auto-pause anything; the extracted core's existing guard condition (`and not step.allows_batch_working`) already no-ops for batch steps, so reusing the core is safe with no auto-pause in the batch path.
  - Steps in one batch may belong to different tasks (cross-task), so the endpoint is workspace-scoped and items carry their own `task_id`.

## Clarifications required

- [x] Failure model — resolved: **atomic all-or-nothing** (pre-validate all; any invalid item rejects the whole batch with per-item errors; nothing changes).
- [x] Notifications/events granularity — resolved: **coalesced** (one realtime event with N items; notifications deduped per recipient).
- [x] Endpoint shape — resolved: **new endpoint + shared core**; existing single endpoint preserved.
- [x] Single-endpoint internals — resolved: **leave `transition_step_state` untouched** (Option B, lower blast radius). The batch command gets its own `_apply_step_transition` core that mirrors the single endpoint's sub-processes; the single command keeps its current inline body. To manage the accepted duplication, add a **cross-reference drift-warning comment in both files** (the single command and the core) stating that any change to the transition sub-processes in one must be evaluated for the other. Trade-off accepted: zero risk to the battle-tested single path, at the cost of two implementations kept in sync by convention + tests.
- [x] Max batch size — resolved: **soft cap of 100** `items`; reject larger with a `ValidationError`. Bounds the single transaction.

## Acceptance criteria

1. `POST /api/v1/tasks/steps/transition-batch` with N batch-capable steps in a valid current state transitions all N to `new_state` atomically and returns a per-step result.
2. Each of the four button transitions works for N>1: `pending→working`, `working→paused`, `paused→working`, `working→completed`.
3. If **any** item is invalid (missing, terminal, disallowed transition from its current state, no open record, or `allows_batch_working = false`), the entire request is rejected, **no** step/record/metric/event is mutated, and the response lists the offending item(s).
4. Steps in the batch may belong to different tasks; all are handled in one transaction.
5. Side-effects match the single endpoint per step: closing record closed, new record opened, `latest_state_record_id`/`state` updated, metrics accrued, terminal `closed_at` set, task `ASSIGNED→WORKING` / all-terminal→`READY` applied, one `PROCESS_STEP_TRANSITION` outbox task per step.
6. Realtime: exactly **one** `task:step-state-changed` `BatchWorkspaceEvent` carrying all N step items, plus one `task:state-changed` per *distinct* task whose state changed.
7. Notifications are coalesced (no N-fold duplicate pings to the same recipient).
8. Query count is bounded/near-constant in N (batched `IN` loads + bulk inserts), not O(N) per-step round-trips.
9. The existing single-step endpoint is unchanged (Option B) — its tests pass without modification, and it carries a drift-warning comment referencing the batch core (with the reciprocal comment on the core).
10. New integration tests pass; existing transition tests still pass.

## Contracts and skills

Read order (apply local-overrides-baseline precedence; load canonical first, `_local` second):

### Contracts loaded

Core (always):
- `../architecture/01_architecture.md`: command/router layering.
- `../architecture/04_context.md`: `ServiceContext` (`session`, `workspace_id`, `user_id`, `identity`, `incoming_data`).
- `../architecture/05_errors.md`: `ValidationError` / `ConflictError` / `NotFound` raising; used for the atomic per-item rejection.
- `../architecture/06_commands.md` + `../architecture/06_commands_local.md`: command structure; **local is central here** — `maybe_begin` transaction utility (one tx for the whole batch), session-call safety, and the **subordinate-command event rule** (only the top-level command dispatches events, after commit). The extracted core must be transaction-free and dispatch-free; the batch command owns the single `maybe_begin` and the single dispatch.
- `../architecture/07_queries.md` + `../architecture/07_queries_local.md`: read-shape baseline for the in-command pre-validation loads (informational).
- `../architecture/09_routers.md`: handler wiring for the new route.
- `../architecture/21_naming_conventions.md`: command/request/endpoint naming.
- `../architecture/40_identity.md`, `../architecture/41_user.md` (+ `_local` if present), `../architecture/42_event.md`, `../architecture/48_presence.md`: identity + event baseline.

Goal bundle — **CRUD + realtime** (subset; no model/migration):
- `../architecture/08_domain.md`: where serialization/domain helpers live (result payload, reuse of `serialize_step_state_record_light`).
- `../architecture/11_infra_events.md`: `event_bus.dispatch`, building/accumulating events, the outbox `create_instant_task` pattern.
- `../architecture/13_sockets.md`: `BatchWorkspaceEvent` socket fan-out — confirm the single coalesced event with `items=[…]` is the right shape (the single endpoint already uses it).
- `../architecture/15_testing.md`: integration test placement/fixtures (mirror `app/tests/integration/services/commands/task_steps/`).
- `../architecture/46_serialization.md`: explicit-allowlist result payload for the batch response.

Trigger expansion:
- `../architecture/22_*` ("bulk insert", "batch write"): **included** — the batch command bulk-inserts the new `StepStateRecord`s and the outbox rows; follow the contract's bulk-write guidance (single `add_all`/`flush`, avoid per-row round-trips). NOTE: unlike the earlier batch-section plan, here "batch" genuinely means bulk DB writes, so `22` applies.
- `../architecture/16_background_jobs.md`: **included (reference only)** — to emit `PROCESS_STEP_TRANSITION` and coalesced `CREATE_NOTIFICATIONS` instant tasks via the existing outbox contract; no consumer changes.

### Local extensions loaded

- `../architecture/06_commands_local.md`: `maybe_begin`, session-safety, subordinate-command event rule (drives the core/orchestrator split).
- `../architecture/07_queries_local.md`: offset-pagination override (informational; not exercised).
- Any `*_local.md` companions present for the core contracts above (load canonical-first).

### Excluded contracts

- `../architecture/03_models.md`, `../architecture/30_migrations.md`: **excluded** — no schema/model/migration change.
- `../architecture/55_*` (search/filter), `../architecture/18_*` (rate limit), `../architecture/34_*` (multipart): excluded — not relevant.
- Replayability/CI bundles (`52`, `53`, `54`, `33`, `31`): excluded — no replay/pipeline surface; the outbox tasks are emitted exactly as the single endpoint already does.

### File read intent — pattern vs. relational

All implementation-file reads are **relational** (what exists: exact sub-process order, kwargs, event/notification shapes, request-parser pattern, router registration). Do **not** open sibling commands to re-learn command structure — `06_commands.md` defines it.

Permitted relational reads:
- `services/commands/task_steps/transition_step_state.py` — the full sub-process sequence being extracted (the source of truth for the core).
- `services/commands/task_steps/requests/__init__.py` — request-schema + parser pattern to mirror (`TransitionStepStateRequest`).
- `services/commands/task_steps/_user_working_record.py` — confirm the guard is naturally skipped for batch steps (no change needed).
- `routers/api_v1/tasks.py` — the existing `route_transition_step_state` and `_TransitionStepBody`; where/how to register the new route and body.
- `routers/api_v1/__init__.py` — confirms `tasks.router` is mounted at `/api/v1/tasks`.
- `services/infra/events/domain_event.py` + `services/infra/events/build_event.py` — `BatchWorkspaceEvent` / `build_workspace_event` shapes for coalescing.
- `domain/tasks/serializers.py` — `serialize_step_state_record_light` for the result payload.
- `domain/execution/enums.py` + `domain/execution/payloads/*` — `TaskType.PROCESS_STEP_TRANSITION`, `StepTransitionPayload`, `NotificationPayload` shapes (already used by the single endpoint).

### Skill selection

- Primary skill: standard backend command + router implementation (no specialized skill file required).
- Router trigger terms: `task step`, `transition`, `batch`, `command`, `router`, `events`.
- Excluded alternatives: migration/model skills — `no schema change`; search/query skills — `not a read-filter change`.

## Implementation plan

1. **Request schema + parser** (`services/commands/task_steps/requests/__init__.py`): add
   ```python
   class BatchTransitionItem(BaseModel):
       task_id: str
       step_id: str

   class BatchTransitionStepStateRequest(BaseModel):
       items: list[BatchTransitionItem]   # non-empty; max 100
       new_state: TaskStepStateEnum
       reason: StepEventReasonEnum | None = None
       description: str | None = None
   ```
   Validate `items` non-empty, enforce the size cap, and reject duplicate `step_id`s. Add `parse_batch_transition_step_state_request`.

2. **Add the per-step core for the batch command** (Option B — do **not** modify `transition_step_state`'s logic). Create
   `async def _apply_step_transition(ctx, step, task, *, new_state, reason, description, credited_user_id, now) -> StepTransitionApplied` (in the new batch module, or a dedicated `_step_transition_core.py` under `services/commands/task_steps/`):
   - Mirrors the single endpoint's sub-processes **faithfully** (validate transition, auto-pause guard [naturally skipped for batch], close open record, open new record, update step/state/latest pointer, metrics, terminal `closed_at`, task state side-effects, build the per-step `PROCESS_STEP_TRANSITION` outbox task).
   - **Does not** open a transaction and **does not** call `event_bus.dispatch`. Returns a small result object carrying: the step-changed item `{client_id, new_state}`, the new `StepStateRecord` (or its light serialization), whether the task state changed (+ the task), and the resolved notification intents (step-pin targets, optional task-pin targets).
   - The transaction (`maybe_begin`) and final `event_bus.dispatch` are owned by the batch command (caller).

3. **Leave `transition_step_state` unchanged**, with one addition: a **drift-warning comment** at the top of the function, e.g.
   `# NOTE: the per-step transition sub-processes here are mirrored by _apply_step_transition (used by transition_step_state_batch). Any change to the state machine, record handling, metrics, task side-effects, or outbox here MUST be evaluated for that core, and vice versa — they are intentionally kept in sync by convention.`
   Add the **reciprocal comment** at the top of `_apply_step_transition` pointing back at `transition_step_state`. No behavioral edits to the single command.

4. **New batch command** `services/commands/task_steps/transition_step_state_batch.py`:
   - Parse request; resolve `credited_user_id` default (`ctx.user_id`).
   - `async with maybe_begin(ctx.session):`
     - **Batch-load** all steps (`WHERE client_id IN (:step_ids)`, scoped workspace, not deleted), all distinct tasks (`IN`), and all open `StepStateRecord`s (`IN`, `exited_at IS NULL`) in three queries. Optionally `with_for_update` the steps to avoid races.
     - **Phase 1 — validate all, mutate nothing:** for each item check step exists + `task_id` matches, not terminal, `new_state ∈ _ALLOWED_TRANSITIONS[current]`, an open record exists, and `allows_batch_working is True`. Accumulate `{step_id, error}` failures. If any → raise a `ValidationError`/`ConflictError` carrying the per-item list (atomic reject; nothing written).
     - **Phase 2 — apply:** call `_apply_step_transition` per step; accumulate step-changed items, the set of distinct tasks whose state changed, and notification intents. Prefer **bulk inserts** (`add_all` for the new records and outbox rows, single `flush`) per `22_*`.
     - **Coalesce notifications:** union recipients across steps; emit a minimal set of `CREATE_NOTIFICATIONS` instant tasks (e.g. one per notification type with the deduped recipient list and an "N steps changed" body) rather than N per-step notifications.
   - **After commit:** dispatch **one** `BatchWorkspaceEvent("task:step-state-changed", items=[…all…])` plus one `task:state-changed` per distinct changed task.
   - Return `{"items": [{"step_id", "new_state", "last_state_record"}, …]}` (reuse `serialize_step_state_record_light`).

5. **Router** (`routers/api_v1/tasks.py`): add `_BatchTransitionStepBody` (mirrors the request schema) and
   `@router.post("/steps/transition-batch")` → `route_transition_step_state_batch` (roles `ADMIN, MANAGER, WORKER`), building `ServiceContext(incoming_data=body.model_dump(), …)` and `run_service(transition_step_state_batch, ctx)`. Register so the literal `/steps/transition-batch` is not captured by `/{task_id}/...` (it is not — different segment count — but place it deliberately).

6. **Scope/guard guarantees:** the batch command rejects any non-batch step in Phase 1, so the auto-pause guard never runs in the batch path and the non-batch "one active step" invariant is untouched.

7. **Tests** (`app/tests/integration/services/commands/task_steps/`): mirror existing batch test style. Cover: (a) each of the four transitions for N=2..3; (b) cross-task batch; (c) atomic rejection — one invalid item leaves **all** steps and records unchanged; (d) coalescing — one workspace event with N items; (e) non-batch item rejected; (f) parity — for a representative transition, the per-step effects produced by the batch core match what the single endpoint produces for the same step (guards against drift between the two implementations). Existing single-endpoint tests must continue to pass unchanged. Add a unit test for the request validator (empty/duplicate/oversize >100).

8. **Frontend handoff** (`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_batch_step_transition_20260623.md`, from the template): document `POST /api/v1/tasks/steps/transition-batch` — request body, the four supported transitions, the atomic all-or-nothing behavior + per-item error shape, the coalesced single realtime event, and the response shape. Note it complements the new `active_batch_steps` resume-card field.

## Risks and mitigations

- Risk: Logic drift between `transition_step_state` and the `_apply_step_transition` core (Option B keeps two implementations).
  Mitigation: reciprocal drift-warning comments in both files; a parity test (step 7f) asserting the core reproduces the single endpoint's per-step effects; the single endpoint itself is untouched so it cannot regress from this change.
- Risk: Long transaction / lock contention for large batches.
  Mitigation: soft-cap `items`; batched loads + bulk inserts; optional `with_for_update` on the step rows.
- Risk: Partial mutation if validation is interleaved with writes.
  Mitigation: strict two-phase — validate everything before any write; single transaction so a late failure rolls back fully.
- Risk: Notification semantics change (coalesced copy differs from per-step).
  Mitigation: document in the handoff; keep entity links intact so deep-links still resolve.
- Risk: Event ordering/dup if both core and batch command dispatch.
  Mitigation: core never dispatches; only the top-level batch command dispatches once (subordinate-command event rule).

## Validation plan

- `cd app && PYTHONPATH=. .venv/bin/python -m compileall beyo_manager` : clean.
- `cd app && PYTHONPATH=. .venv/bin/pytest tests/integration/services/commands/task_steps tests/unit/services/commands/task_steps` : all green (new + existing).
- Manual: issue a batch `pending→working` for steps across two tasks → all `working`, one socket event with N items, one outbox task per step; then a batch with one already-completed step → 4xx, nothing changed.
- Regression: existing single-transition tests pass unchanged.

## Review log

- `2026-06-23` `claude-opus-4-8`: Initial plan from confirmed design — new endpoint + shared core, atomic two-phase, coalesced events/notifications, batched I/O.
- `2026-06-23` `David`: Confirmed 100 batch-size cap; clarified the single-endpoint-delegation decision.
- `2026-06-23` `claude-opus-4-8`: Resolved both open clarifications — Option A (single delegates to shared core) and `items` max 100.
- `2026-06-23` `David`: Prefer **Option B** — leave the single endpoint untouched; add reciprocal drift-warning comments in both services.
- `2026-06-23` `claude-opus-4-8`: Switched plan to Option B — single command left as-is + drift comment, batch core is a faithful mirror; updated scope, steps 2–3, tests (parity test 7f), risks, and acceptance criterion 9.
- `2026-06-23` `claude-opus-4-8`: Implemented (Option B), validated (26 task_steps tests green), summarized, archived.
- `2026-06-23` `David`: `mark_closing_record_inaccurate` should be supported on batch transitions (esp. completion).
- `2026-06-23` `claude-opus-4-8`: Post-implementation follow-up — added **per-item** `mark_closing_record_inaccurate` (originally deferred): request item field + router body + passthrough to the core (already supported it); added a completion test; updated handoff + summary.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `claude-opus-4-8`
- Implemented + summarized on 2026-06-23; summary: `backend/docs/architecture/implemented_summaries/SUMMARY_batch_step_transition_20260623.md`
