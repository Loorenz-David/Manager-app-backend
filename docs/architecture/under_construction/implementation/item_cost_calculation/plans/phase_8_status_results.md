# Phase 8 — Status & results

```
plan: phase 8
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Ship the operational reads and the episode-boundary result lifecycle (intention §8B,
round 6): live budget status (manager and worker variants), the result event +
idempotent handler, **all four emission touch points** (READY-entry hook, reopen
hook, terminal commands, §8A.5 straggler re-emit with the widened READY ∪ terminal
guard), and the lifetime read model.
**NOT in this phase:** branch B of §8A.5 (rejected by the owner — R4-1; never
built); the operational CLI re-emit (only-if-cheap ledger); any change to the time
pipeline beyond the P-E touch-point list (master plan rule P-E as amended round 6).

## Read first

1. `master_plan.md` §§5, 6 (registry: TaskType, payload, handler, routes), 9
   (P-A/P-B/P-E/P-F), 10 (analytics-worker launch caveat — needed to run this
   phase's integration tests).
2. Intention **§8, §8A entire, §8B entire** (consumption read, two-cost boundary,
   handler contract, replay identity, §8A.5 branch A with the round-6 guard, the
   §8B emission points and total admission), §11A.1–§11A.4 (exposure predicate,
   status vocabulary), §7B.3 (item_binding read side), §6A.8, HC-2/HC-3/HC-7.
3. In-tree: `services/tasks/analytics/process_step_transition.py`
   (`handle_process_step_transition`, `_recompute_step_time_totals` — verified at
   `:161` on 2026-08-12), `services/infra/execution/task_router.py`,
   `services/infra/execution/task_factory.py` (`create_instant_task`, `:46`),
   `services/infra/execution/db.py` (`task_db_session`, `:10`),
   `domain/execution/payloads/step_transition.py` (payload shape precedent),
   `workers/analytics_worker.py` (handler map), terminal commands
   `resolve_task.py` / `fail_task.py` / `cancel_task.py` (side-effect block).
4. Contracts: `16_background_jobs`, `51_worker_runtime`, `52_replayability`,
   `11_infra_events`, `12_infra_redis`, `07_queries`+local, `46_serialization`+local
   (+ core).

## Dependencies

Phase 7 APPROVED.

## Files expected to change

- `app/beyo_manager/domain/execution/enums.py` (`PROCESS_ITEM_COST_RESULT`)
- `app/beyo_manager/services/infra/execution/task_router.py` (→ `queue:analytics`)
- `app/beyo_manager/domain/execution/payloads/item_cost_result.py` (new — frozen
  dataclass, `{workspace_id, task_id}` and nothing else)
- `app/beyo_manager/services/tasks/analytics/process_item_cost_result.py` (new
  handler) + `workers/analytics_worker.py` (registration)
- `app/beyo_manager/services/commands/tasks/resolve_task.py`, `fail_task.py`,
  `cancel_task.py` (one `create_instant_task` line each, inside the existing
  side-effect block / same transaction)
- `app/beyo_manager/services/commands/tasks/_task_state_transitions.py` (round 6,
  §8B.1: one emit hook in `maybe_evaluate_task_ready`, one in
  `maybe_reopen_task_to_working` — both inside the helpers so every caller inherits)
- `app/beyo_manager/services/tasks/analytics/process_step_transition.py`
  (§8A.5 branch-A guarded re-emit, guard READY ∪ terminal — the ONLY change to an
  existing analytics handler)
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`,
  `get_task_budget_status_worker.py`, `get_item_lifetime_economics.py`
- `app/beyo_manager/domain/item_economics/serializers.py` (status serializers — the
  worker one has NO monetary keys at all)
- `routers/api_v1/item_economics.py` (budget-status + lifetime routes);
  `routers/README.md`; tests

## Implementation tasks (ordered)

1. **Consumption read** exactly §8A.1's expression (COALESCE to 0; `is_deleted` the
   only filter; step state deliberately unfiltered; rollup columns only — never
   `step_state_records`; never `inaccurate_*` / pause / ended-shift columns).
2. **Status query** (§8A.6): every operational read carries the literal filter
   `kind = 'committed' AND superseded_at IS NULL AND is_deleted = false`; returns
   `EconomicsStatusEnum` per §11A.4's ordered vocabulary, snapshot values, live
   §6A.8 consumption, `item_binding` (§7B.3: bound/mismatched/detached), and the
   result block when closed + present. Null-numerics rule for every non-`ok`/
   `infeasible` status (P-B). Worker variant: separate service + serializer with
   zero monetary keys (minutes/percent only — §11A.3's declared-field discipline).
   Router selects worker service for WORKER and SELLER identities (§11A.1).
3. **Result pipeline** (§8A.3 + §8B): TaskType + routing + payload; **emissions at
   all four §8B.1 touch points** — READY-entry hook in `maybe_evaluate_task_ready`,
   reopen hook in `maybe_reopen_task_to_working`, the three terminal commands (same
   transaction, outbox semantics), and task 4's straggler re-emit; handler —
   `task_db_session()`; **§8B.2 total admission**: non-deleted and state ∈
   {WORKING, READY, RESOLVED, FAILED, CANCELLED} → compute; {PENDING, ASSIGNED,
   STALLED} → log-and-return writing nothing; current committed evaluation **at
   handler time** else log-and-return writing nothing (R-9); compute §8A.1 + §6A.8
   at the evaluation's snapshot rate; stamp `task_state_snapshot` (state at handler
   time) and `task_closed_at` (copied, NULL when not terminal); upsert
   `INSERT … ON CONFLICT (task_id) DO UPDATE SET <derived columns>`; `evaluation_id`
   NOT NULL; `calculation_version` copied (A7); no delete path exists.
4. **§8A.5 straggler re-emit** (R4-1, guard widened round 6): in
   `handle_process_step_transition`, inside the existing time-bearing branch after
   `_recompute_step_time_totals`, enqueue one `PROCESS_ITEM_COST_RESULT` for the
   step's task **iff** the task's state ∈ {READY} ∪ terminal.
   Nothing else in the file changes (P-E).
5. **Lifetime read model:** per item, committed evaluations + result rows across its
   tasks, typed by `task_type_snapshot`/`return_source_snapshot` (never live task
   fields).

## Acceptance criteria

**C1 — projection isolation (intention test 4; HC-2):** projections invisible to the
status query, the worker variant, and the result handler; promotion leaves them
invisible. **Named mutations:** deleting the committed-current filter at its call
site in `get_task_budget_status.py` → a specific test red; same for the filter in
`process_item_cost_result.py` (two named call sites, one row each).

**C2 — bucket policy (test 5; R-5):** one record per bucket
(working / paused / ended-shift / marked-wrong), each the sole discriminator, summed
through the production rollup pipeline on real ORM instances → only the working row
counts.

**C3 — batch dilution flow-through (test 6):** one worker, two batchable steps on
two tasks, full overlap → each episode consumes exactly half the wall clock;
Σ = wall clock.

**C4 — consumption read rows (§8A.1):** task with no steps → 0 (COALESCE row);
soft-deleted step's time excluded; a SKIPPED step carrying nonzero
`total_working_seconds` **counts** (state-unfiltered proof row).

**C5 — result idempotency & replay (tests 7/21; §8A.4):** handler run twice →
byte-identical over the named §8A.4 column set while `computed_at` advances; the
whole-row identity assertion variant **fails** (proving the exclusion is real, not
convenience); no committed evaluation → nothing written, log only; late-arriving
step analytics + replay converges; config supersession after close → recompute
byte-identical (§8.4); ON CONFLICT update path exercised (row exists → updated).

**C6 — post-boundary straggler (test 18; §8A.5 with the round-6 guard):** transition
a step of a RESOLVED task → a `PROCESS_ITEM_COST_RESULT` task is enqueued and the
result row converges onto the new total; same for a READY task (guard's round-6
half); same transition on a WORKING task (mid-episode) → **no** result event
enqueued from the straggler path. The branch-B freeze row is NOT built.

**C6b — boundary lifecycle (test 22; §8B, round 6), enumerated:** entry into READY
(via a real step-transition reaching `maybe_evaluate_task_ready`) writes the row
with `task_state_snapshot = ready`, `task_closed_at` NULL; reopen (add steps to a
READY task) refreshes it to `snapshot = working`; re-entry into READY converges onto
the new totals (8B.3); RESOLVED finalizes (`snapshot = resolved`, `task_closed_at`
set — one row per terminal command, three rows); a replayed event for a PENDING task
carrying a committed evaluation writes nothing (8B.2 admission row). **Named
mutation:** removing the READY-entry emit hook in `maybe_evaluate_task_ready`
(call-site-of-hook, `_task_state_transitions.py`) must turn the READY-entry row red.
`task_state_snapshot` and `task_closed_at` join C5's §8A.4 replay-identity column
set.

**C7 — status vocabulary (§11A.4), all eleven values enumerated** (each fixture
sole-predicate, exact enum value): `ok` (exact numbers), `infeasible`
(allowed ≤ 0; `percent_consumed` null), the four `not_configured_*`,
`item_unvalued`, `item_missing_expected_price`, `item_missing_purchase_cost` (only
when the model carries a purchase term), `currency_mismatch`, `not_evaluated`.
Group-2 rows assert every numeric field is `null` — never 0, never omitted.
Priority row: a task with a current committed evaluation in a now-unconfigured
workspace → still `ok` (the snapshot is self-sufficient — §11A.4 rule 1).

**C8 — item_binding (§7B.3):** bound / mismatched (PRIMARY swapped after commit) /
detached — three exact rows; the result row records `evaluation.item_id`, never the
live PRIMARY (swap fixture).

**C9 — two-cost boundary (§8A.2; P-A):** the money-key sets of the step-payload
family and the item-economics payload family are disjoint (test over both serializer
outputs); the worker budget-status payload has zero monetary keys (key-set
assertion). **Named mutation:** adding `total_cost_minor` to the economics status
payload in `domain/item_economics/serializers.py` (definition site) → red.

**C10 — wiring:** handler map includes `PROCESS_ITEM_COST_RESULT` → handler
(worker-registration test per existing pattern); task_router routes it to
`queue:analytics`; the three terminal commands each enqueue exactly one result task
inside their transaction (three rows).

## Notes

- The payload never carries derived values — the handler re-resolves everything;
  that is what makes replays of old events produce today's correct answer (§8A.3).
- "Result exists but its evaluation is gone" is unreachable (INV-E2); build no
  handling for it.
- Redundant §8A.5 emissions are free by recompute-and-SET; do not add dedupe.
- Integration tests that exercise the queue path need the analytics worker running —
  master plan §10's Makefile-only caveat applies (and `make task-router` for outbox
  dispatch); in-process handler invocation is the default test seam.
- Archgraph: delta = event/handler/projection nodes + edges into the analytics
  branch; orient on `intention-step-transition-analytics`,
  `analytics-recompute-step-time-totals`, `domain-work-analytics`. Do NOT repair the
  D-3 anchor drift here (maintenance channel owns it — master plan §8).

## Review log

(append-only)
