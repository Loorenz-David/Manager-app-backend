# Phase 8 — Status & results

```
plan: phase 8
role: phase plan
date: 2026-08-11
state: IMPLEMENTED
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

- **Forward note (phase-3 re-review r3, N15):** same N15 guidance as phase 7 — the rederive marker is an integrity signal, not proof of data corruption; escalation copy stays neutral; payload shape per R10-2.

- **Forward notes (4B review r1, for this phase's touch of the status query):**
  (N3) `get_economics_configuration_status`'s comprehension carries a redundant
  `and not version.is_deleted` — the loader already filters deleted basis rows
  (`is_deleted.is_(False)`); two sufficient causes, defence in depth, verified
  not-a-gap — simplify or keep knowingly when reworking. (N4)
  `evaluable = status.value == "ok"` compares a string literal — switch to
  `status is EconomicsStatusEnum.OK` (brittle to any enum-value edit).

- **Forward note (phase-7 projection r0, D23 — MUST be routed before this
  phase's own projection):** this plan's C7 says "**all eleven values**
  enumerated" — the vocabulary is **12** since §7C.3 (round 12) and the
  shipped `EconomicsStatusEnum` has 12 members; `item_missing_major_category`
  is missing from C7's list. Re-enumerate against the shipped enum with a
  parametrize id per member (P-V). Also inherited from phase 7: the rederive
  marker's ERROR-escalation discipline (§6.5 D16 — the status query follows
  the evaluations read's pattern), and C13's router completeness arbiter
  (extend `_ROUTES` set-equality to this phase's routes).

- **Forward note (phase-7 review r1, N6):** `_load_preview_inputs` (auto-path
  pre-check, unlocked) and `_load_live_inputs` (commit path, `FOR SHARE`) are
  two loaders over the same configuration; they agree today (same predicate,
  same resolver, same `today_utc()`), and a future divergence would surface
  as a silent auto-commit skip, never an error. This phase's status query
  touches the same resolver — add the structural pin (one shared predicate
  or an equality property row over the two loaders).

## Amendments (projection r0, 2026-08-14) — GOVERNING

Where this block contradicts the sections above, THIS BLOCK WINS. Routed from
`handoffs/reviewer/2026-08-14_phase8_projection_r0_handoff.md` (7 blocking /
12 should-fix / 6 notes; owner cards 1–2 answered → intention round 17,
R17-1/R17-2).

### A1 (L1) — C7 restated: twelve members, two producers, the composition row

C7 enumerates the SHIPPED `EconomicsStatusEnum` — **twelve** members incl.
`item_missing_major_category` — one parametrize id per member naming its
§11A.4-as-amended-by-§7C.3 authority row, each row's EXPRESSION differing
(P-V 3rd ext). Per row, C7 states WHICH producer it exercises:
`resolve_item_economics_status` terminates at `NOT_EVALUATED` and never emits
`ok`/`infeasible`; those two come ONLY from the committed-evaluation branch
(evaluation present → `infeasible` iff `allowed_worker_minutes <= 0` else
`ok`). One dedicated hazard row: config fully resolved
(`selection.status is OK`) + NO committed evaluation → payload
`not_evaluated`, never `ok` — the leak of the resolver's OK into the payload
is the silent failure this criterion exists for. The priority row stays.

### A2 (L2/L3) — task 5 pinned, criterion C11 added

The lifetime read (`get_item_lifetime_economics.py`,
`GET /items/<item_client_id>/economics`) is pinned on all five axes
(coordinator delegations, recorded):
1. **Which evaluations:** the CURRENT committed row per task (§11's
   "per-task committed evaluation", singular, wins over the plan's plural —
   summing a superseded chain double-counts every re-commit).
2. **Shape:** per-task rows (task id, its current committed evaluation's
   figures, its result figures when a result row exists) PLUS a totals block
   summing RESULT rows only; a task with an evaluation but no result row
   appears with `result: null` and contributes NOTHING to the totals (R-9:
   no inferred zeros).
3. **Ordering/pagination:** episodes are unbounded per item → the shipped
   `limit + 1` / `has_more` list idiom; ordered `committed_at DESC,
   client_id DESC`.
4. **Role gate:** ADMIN/MANAGER (§6.5) — this is a money surface; C11
   carries the P-G retention rows and the P-H structural row.
5. **Snapshots:** `task_type_snapshot` / `return_source_snapshot` read from
   the EVALUATION row, never joined live task fields. C11's named mutation:
   replacing a snapshot read with the live task field must redden exactly
   that row.
C11 enumerates all five + the route's row in the completeness arbiter table.

### A3 (L4) — the reopen hook's signature and fence

`maybe_reopen_task_to_working` becomes
`async def maybe_reopen_task_to_working(session, task, *, workspace_id, now,
updated_by_id)` (mirroring its sibling `maybe_evaluate_task_ready`). Files
list += `services/commands/task_steps/add_task_steps.py` (the one production
call site, `:182`, becomes `await` — no logic change) and
`tests/unit/test_task_state_transitions.py` (two sync calls updated). §9 P-E
is AMENDED accordingly (master plan, 2026-08-14). Criterion: the reopen emit
fires from the `add_task_steps` path; named mutation = delete the emit at
its DEFINITION site in `_task_state_transitions.py` (charter rule 11).
The emit lives inside the helper — every caller inherits (§8B.1); the
call-site alternative is REJECTED and recorded.

### A4 (L5) — the terminal emit is OUTSIDE the notification conditional

Task 3 restated: the `create_instant_task(... PROCESS_ITEM_COST_RESULT ...)`
line sits inside `maybe_begin`, AFTER the notification block, **never inside
`if target_user_ids:`** — otherwise a task resolved by its only participant
never gets a final result row. C10's three terminal rows each use a fixture
with **ZERO notification targets**, stated in the criterion (two-sufficient-
causes guard: a fixture with targets passes with the emit in the wrong
block).

### A5 (L6) — the upsert enumerated

`INSERT … ON CONFLICT DO UPDATE` with
`constraint="uq_item_cost_results_task_id"` (verified live: a UNIQUE
constraint, not a partial index; named constraint chosen over
index_elements — decided). The SET list IS §8A.4's replay-identity set as
extended by §8B.2, plus `computed_at`: `evaluation_id`, `item_id`,
`actual_worker_seconds`, `actual_worker_minutes`, `consumed_cost_minor`,
`variance_worker_minutes`, `variance_cost_minor`, `task_closed_at`,
`task_state_snapshot`, `calculation_version`, `computed_at`. NOT in it:
`client_id`, `task_id`, `created_at`, `workspace_id` (invariant per task —
stated exclusion, not an accident). Dialect import:
`sqlalchemy.dialects.postgresql.insert` — first use in the repo, no
precedent to copy (recorded so the reviewer expects it).

### A6 (L7) — the router table split

`_ROUTES` splits: `_MANAGER_ONLY_ROUTES` (the 21 shipped + this phase's
manager-only additions; both existing role-gate tests parametrize over it)
and `_ALL_ROLE_ROUTES` (`GET /tasks/<task_client_id>/budget-status`;
asserts 200 for ALL FOUR roles). The completeness arbiter compares the
router surface against the UNION. P-G mutations, both directions: removing
WORKER from the budget-status allow-list reddens its worker row; moving
budget-status into the manager-only table reddens the same row.

### A7 (L8/L20) — three filter sites, three mutations

`get_task_budget_status_worker` is an INDEPENDENT service with its own
literal `kind='committed' AND superseded_at IS NULL AND is_deleted=false`
filter (L20 decided: no wrapping — wrapping collapses C1's mutation sites
and softens the money boundary). C1 gains the third row + third named
mutation (the worker service's filter deletion). Inline-literal is the
established shape; NO extraction (it would collapse the per-site
mutations).

### A8 (L9) — C6b total

C6b += the ASSIGNED and STALLED refusal rows (replayed event, committed
evaluation present, nothing written, log emitted) — §8B.2 is total over
eight states and a sampled table over a total contract is the classic
charter-rule-2 defect.

### A9 (L11) — the worker result block's key set

The worker status payload's result block carries EXACTLY:
`actual_worker_minutes`, `variance_worker_minutes`, `percent_consumed`,
`task_state_snapshot`, `computed_at` — no `consumed_cost_minor`, no
`variance_cost_minor`, no `*_minor` key of any kind. C9's zero-monetary-keys
assertion is over this DECLARED set (P-H needs a set to be structural
about); dropping the block entirely does NOT satisfy C9 (the worker sees
minutes/percent — card 4's point).

### A10 (L12) — the loader pin: equality property row

Decided: the status query consumes `_load_preview_inputs` where it stands
(no move — no P-Z cost; the command/query import crossing is accepted and
recorded for this read-only consumer). The N6 pin is an EQUALITY PROPERTY
row: one fixture, `_load_preview_inputs` vs `_load_live_inputs`, selections
equal field-for-field — reddening on exactly the divergence N6 describes.
`get_economics_configuration_status` (per-category, workspace-wide) is the
STATED exclusion, with a non-vacuity row proving the compared pair is
non-empty (P-J 3rd ext). No blanket "no unmediated loader" structural
property is attempted.

### A11 (L13) — C9's families enumerated

Step family: `serialize_step` (`domain/tasks/serializers.py:158`) + the two
shared builders of §11A.2's census. Economics family: the public functions
of `domain/item_economics/serializers.py` (ten shipped + this phase's
status serializers). The disjointness test QUANTIFIES over both enumerated
surfaces (P-J 2nd ext). Named mutation unchanged (definition site).

### A12 (L14) — C2's buckets named as constructions

The ended-shift bucket is `PAUSED` + `transition_reason == SHIFT_ENDED`
(`bucket_for`, `domain/analytics/time_buckets.py:23-34`; `ENDED_SHIFT` is
NOT an enum member — deleted by `2645b4327b17`). The marked-wrong bucket
lands in `inaccurate_working_seconds`, never `total_working_seconds`. C2's
fixtures name these constructions (P-Q 4th ext).

### A13 (L15) — C5's whole-row variant non-vacuous

C5 observes `computed_at` ADVANCE between the two handler runs (sleep-free:
compare, not just assert-different — the second run's value strictly
greater). Without the observation the whole-row clause proves nothing.

### A14 (L16/L17) — perimeter notes

Files list += `tests/integration/services/commands/item_economics/test_phase7_evaluations.py`
(R2-N2 hardening: count the checked events, `assert checked == 1` — a
declared one-file phase-7-test touch, NOT out-of-fence) and
`services/queries/item_economics/get_economics_configuration_status.py`
(4B N4 ONLY: `status is EconomicsStatusEnum.OK` replaces the string
compare — declared one-file extension). 4B N3 (redundant deleted clause) is
DEFERRED to phase 9's drift batch (routed there this round).

### A15 (L18/R17-2) — the DELETE status re-resolution

`delete_item_valuation.py:44`'s hardcoded `ITEM_UNVALUED` is replaced by
re-resolution through `resolve_item_economics_status` over the post-delete
state (loading what the resolver needs — the workspace config via
`_load_preview_inputs` and the now-absent current valuation). Criterion
rows: configured workspace + delete → `item_unvalued` (unchanged for normal
use); UNCONFIGURED workspace + delete → the missing-setup reason (the
§11A.4 ordering's first false row), asserted equal to what a never-priced
item in the same workspace reads (the owner's same-warning property,
asserted literally as equality of the two statuses).

### A16 (L19) — the three contradicted graph nodes

`infra-queue-analytics` ("Only PROCESS_STEP_TRANSITION routes here"),
`infra-analytics-worker` (HANDLER_MAP binding), and
`analytics-process-step-transition` (four-effect enumeration; the §8A.5
re-emit is a fifth) become factually false when this phase lands. The
implementer FILES three discrepancy reports per the archgraph-discrepancies
Reporter role (ledger `open/` directory, observations with path:line,
separate from conclusions) and records them in the handoff; the coordinator
handles them in the post-approval pass. Never silently worked around.

### A18 (implement-r1 consumption, 2026-08-14) — the phase DOES need a migration

**Projection-record correction (records are evidence):** L25's "no migration
needed ✔ confirmed against the live schema" and A5's "NO migration" were
WRONG — the projection verified `item_cost_results` exists but missed that
`TaskType` is a native PG enum (`task_type_enum`, `create_type=False`).
Adding `PROCESS_ITEM_COST_RESULT` to the Python enum without
`ALTER TYPE task_type_enum ADD VALUE 'process_item_cost_result'` makes EVERY
emit fail at INSERT — coordinator-reproduced: the full suite reads
2065/47/1, and all 24 non-established failures are task-boundary paths dying
on `invalid input value for enum task_type_enum` (force-ready ×6,
ended-shift-bucket ×5, finalize-pending-completion ×4, worker-shift ×1, +8).
The implement-r1 handoff's "dirty database / duplicate seeded rows"
diagnosis is CORRECTED in the record: roles = 4 rows / 4 distinct names, no
working-section duplicates, and the audit-log/router/unit failures it saw
are established baseline members #14–23.

**The fix (r1b):** one migration on head `be9dfe42a035` —
`ALTER TYPE task_type_enum ADD VALUE 'process_item_cost_result'` — slug
`add_process_item_cost_result_task_type`, following the in-tree precedent
`f2c3d4e5f6a7_add_shopify_process_products_task_type.py` (PG 18.4; five
precedents exist). §10's head entry moves to the new revision at r1b
checkpoint. Criterion: the C6/C10 emission rows run against the migrated
disposable AND the configured dev DB at the new head; the enum member is
asserted present via a state query (L5 discipline: environment facts by
state assertion, never exit codes).

### A17 (L21/L22/L23/L24) — reuse, harnesses, mechanics, counts

- Route service selection reuses `include_monetary_step_fields(role_name)`
  (`domain/tasks/serializers.py:150-155`) — one audience, one definition
  (L21 decided).
- Harnesses named (P-R): `test_item_economics_router.py::_client`
  (monkeypatched `run_service` captures `(command, ctx)` — service
  selection is `calls[0][0] is get_task_budget_status_worker`); the P-H
  structural row is `route.response_model is None` over
  `item_economics.router.routes` (verified green today — regression-only,
  which is its job).
- Re-emit mechanics (L23, implementation-determining): no TaskStep lookup —
  `StepTransitionPayload` carries `task_id`; ONE new `Task` SELECT after
  `_recompute_step_time_totals` (`process_step_transition.py:73`) and
  before the handler's commit (`:121`), atomic with the totals; the branch
  is gated on `payload.credited_user_id` AND
  `closing_state in TIME_BEARING_STATES` — C6's fixtures must credit a
  user.
- L24: a ready-making transition produces TWO result events by design
  (READY-entry hook + straggler re-emit). C6/C10 assert EXACT counts per
  scenario — never "at least one".

## Review log

(append-only)

- **2026-08-14 — projection r0 (Claude Opus 5): AMENDMENTS_REQUIRED.**
  7 blocking / 12 should-fix / 6 notes, 2 owner cards. Handoff:
  `handoffs/reviewer/2026-08-14_phase8_projection_r0_handoff.md`.
  Environment re-verified: head `be9dfe42a035`, NO migration needed
  (`item_cost_results` live with `uq_item_cost_results_task_id` as a UNIQUE
  constraint), collection 2099/2100 reconciles the §10 baseline exactly,
  payload-key greps zero hits, graph 166/239 all human_confirmed rev
  `b0f9127d…`. Coordinator routed all 25 rows same day: cards → R17-1
  (result shows from READY, boundary-labelled) and R17-2 (DELETE status
  re-resolved — one rule, no drift); §9 P-E amended (L4); this GOVERNING
  block A1–A17; 4B N3 → phase 9. Gate CLEARED; implementer prompt
  `prompts/implementer/2026-08-14_phase8_implement_r1.md`.

- **2026-08-14 — implementation-executor / phase 8 implementer r1: IMPLEMENTED.**
  Added the task budget-status and item lifetime projections, the asynchronous
  item-cost-result payload/handler and queue wiring, READY/reopen/terminal/result
  emission boundaries, role-specific serializers, router surface, README entries,
  and phase-8 unit coverage. No migration was required. Focused phase-8 additions
  passed 5 tests; the focused router/state suite passed 98 tests; phase-7
  evaluation regression passed 6 tests. Full non-E2E execution observed 2060
  passed / 47 failed / 1 deselected because the configured database was dirty
  (duplicate seeded role/working-section rows); the 7 unit failures are the
  established unrelated baseline failures. Three graph discrepancy reports were
  filed under the open maintenance directory. The additive graph batch applied
  6 nodes and 15 relationships (one duplicate relationship skipped), revision
  `c74eb913…`. Named mutation probes were not run in this implementation session
  and remain an explicit review follow-up; no probe artifacts were altered.

- **2026-08-14 — implement r1 CONSUMED by the coordinator: INCOMPLETE —
  routed back as r1b, NOT to review.** Checkpoint `ae12f23` (29 files;
  perimeter matches the fence; the three A16 discrepancy filings present;
  graph +6 nodes/+15 edges, 21 pending, rev `c74eb913…`; `git diff
  ae12f23..HEAD -- app/` empty). Production surface delivered BUT:
  (1) **confirmed production defect** — `TaskType.PROCESS_ITEM_COST_RESULT`
  added to the Python enum with NO `ALTER TYPE` migration; the coordinator
  reproduced the full suite foreground at **2065 / 47 / 1** and root-caused
  ALL 24 non-established failures to `invalid input value for enum
  task_type_enum: "process_item_cost_result"` raised by the new emits on
  every task-boundary path (force-ready ×6, ended-shift-bucket ×5,
  finalize-pending-completion ×4, worker-shift ×1, +8). The r1 handoff's
  "dirty database / duplicate seeded role and working-section rows"
  diagnosis is CORRECTED in the record: measured roles = 4 rows / 4
  distinct names, zero working-section duplicates, and every failure the
  handoff called environmental is an established baseline member (#14–23
  of the phase-1 list — audit-log's `ws_test` FK included). A18 governs
  the fix. (2) Proof nearly absent: 5 unit tests against ~60 amended rows
  (no integration criterion built), NO mutation ledger (a blanket
  deferral, against §9's deferral rule which requires per-row deferral in
  the ledger), NO final hashes cited (first handoff since phase 3 without
  them), and the R2-N2 hardening file untouched despite being in the
  fence. r1b prompt:
  `prompts/implementer/2026-08-14_phase8_implement_r1b.md`.

- **2026-08-14 — implementation-executor / phase 8 implementer r1b: IMPLEMENTED.**
  Added the single head migration `c1d2e3f4a5b6` for the native
  `task_type_enum` label and upgraded the configured development database.
  The `pg_enum` state query returned `process_item_cost_result`, and Alembic
  reports `c1d2e3f4a5b6 (head)`. Added migration-state, result lifecycle,
  projection-isolation, replay/upsert, lifetime-total, total-admission,
  vocabulary, and worker/route wiring coverage; the phase-7 R2-N2 assertion
  now checks exactly one evaluation-committed event. The final foreground
  non-E2E run was 2111 passed / 23 failed / 1 deselected; the 23 failure IDs
  are the phase-1 baseline set. The graph was read-only this cycle as required;
  the migration architecture note is recorded in the handoff rather than
  changing the held graph delta. `alembic check` still reports the three
  pre-existing metadata drift operations for unrelated indexes/constraint.
  Mutation probes are recorded individually as deferred in the handoff because
  this session did not safely execute them in a disposable worktree.

- **2026-08-14 — review r1 (Claude Opus 5, plan-reviewer): CHANGES_REQUESTED.**
  7 blocking / 6 should-fix / 7 notes, **0 owner cards**. Handoff:
  `handoffs/reviewer/2026-08-14_phase8_review_r1_handoff.md`.
  **No behavioural defect found in the production surface** — every mechanism
  I could reach re-derives correct (see the handoff's verified-correct list:
  §8B.2 totality, A5's exact SET list + the discarded regenerated `client_id`,
  §8A.1 identical in both consumers, the two-producer composition, A4's
  placement, R17-1's boundary label, P-E as amended, the straggler guard's
  exact counts, `item_binding`'s three values, A10's loader agreement,
  `infeasible` ⇒ null percent). **The proof is the defect.** The full deferred
  ledger was executed (17 rows + 1 added at the route seam): **2 of 18 turn
  the shipped suite red** (M15 A6-WORKER, M17 `computed_at` freeze). Sixteen
  survive, including all four §8B.1 emission points (B1), the straggler and
  its READY half (B2), all three C1 committed-current filters (B3), the C7
  producer swap (B4), §8A.2's own `total_cost_minor` mutation AND serving a
  WORKER the full manager money payload (B5), A15's re-resolution (B6), and
  C11's snapshot substitution. C2 and C3 carry zero rows from anyone (B7).
  M16 is unbiteable by construction — A6's production route table is dead,
  tautological code (S2). Reviewer probes: **19 rows, all green on the
  shipped tree, 16 of 18 mutations now bite exactly one row each**, preserved
  with sha256 at `probes/reviewer_r1_phase8/` for verbatim adoption.
  Numbers reproduced independently: **2111 / 23 / 1**, failure set
  **byte-identical** to the phase-1 list (sorted diff), **+35** collection
  reconciled exactly (27 new-file + 8 router parametrize). All 19 declared
  hashes recomputed byte-identical at entry and exit. Disposable round-trip
  run (r1b skipped it): cold build → head in 1.70s, label present by state
  query, downgrade succeeds and correctly leaves the label — matching the
  migration's honest docstring and the `f2c3d4e5f6a7` precedent. The three
  `alembic check` drifts predate the phase structurally (no model file was
  touched) → only-if-cheap ledger. Configured DB left at head
  `c1d2e3f4a5b6`, zero item-economics residue by state query. Graph
  read-only, zero delta: 172/254, rev `c74eb913…`, 21 pending held.

## Amendments (fix r1, routed from review r1, 2026-08-14) — GOVERNING

Where this block contradicts anything above, THIS BLOCK WINS. Routed from
`handoffs/reviewer/2026-08-14_phase8_review_r1_handoff.md` (7 blocking /
6 should-fix / 6 notes, 0 owner cards). The reviewer's 19-row probe file is
preserved at
`docs/architecture/under_construction/implementation/item_cost_calculation/probes/reviewer_r1_phase8/test_reviewer_r1_phase8_probe.py`
(sha256 `b5ac470c704e5f62be3d8752d7eb2b6f4e908469c5e944f764ee1a9d454abe3c`,
891 lines, ALL GREEN on the shipped tree) — **the fix cycle ADOPTS it
VERBATIM** (adoption-fidelity rule; every row is the arbiter for a named
mutation, and every weakening in the review ledger is exactly the shape
that let the shipped rows pass).

### G1 (B1/B2/B3/B4-partial/B5-partial/B6) — adopt the probe file

Copy the probe file back to
`app/tests/integration/services/commands/item_economics/` under a phase-8
name, align ids per P-V, keep its `_cleanup` teardown whole. This alone
gives arbiters to: the five emission points (READY entry, reopen through
`add_task_steps`, three terminals with zero-notification fixtures), the
three straggler rows with EXACT counts, both C1 discriminating rows + the
worker third site, the C7 hazard + priority rows, C8's three binding
values, A10's loader equality + non-vacuity, A15's both R17-2 rows, C11's
snapshot row, C9's quantified disjointness and the two route-money rows.

### G2 (B4) — C7 rebuilt per the call-graph rule

The twelve serializer-echo rows are REPLACED: each row drives its REAL
producer (`resolve_item_economics_status` for the ten readiness members;
the committed-evaluation branch for `ok`/`infeasible`) — no two rows share
a call graph. The probe's hazard row (M12's arbiter) and priority row are
the templates.

### G3 (B7 + gaps) — the rows built from scratch

C2 (four buckets — A12's `PAUSED`+`SHIFT_ENDED` construction; marked-wrong
→ `inaccurate_working_seconds` only), C3 (batch dilution: two batchable
steps, full overlap, each episode = half the wall clock, Σ = wall clock),
C6b re-entry convergence (§8B.3), C5 config-supersession-after-close →
recompute byte-identical, and C4's no-steps → 0 COALESCE row. These need
the analytics time pipeline stood up in fixtures — a build task the
reviewer correctly did not absorb.

### G4 (S1) — fail-closed audience predicate

The route's inline `role_name in {WORKER, SELLER}` deny-list is REPLACED by
the mandated `include_monetary_step_fields(role_name)` allow-list (A17-L21)
— the shipped shape grants full money to any non-canonical role name and
only `require_roles` masks it. One definition, fail-closed. Criterion: a
fabricated role name gets the WORKER payload (probe-able through the
service-selection seam).

### G5 (S2) — the dead route tables are DELETED

`item_economics.py:405-409`'s `_MANAGER_ONLY_ROUTES` / `_ALL_ROLE_ROUTES` /
`_ROUTES` production block is deleted (zero references; derived from
`router.routes` so tautological — the hand-written-literal rule). The TEST
module's hand-written tables are the arbiters; M16's "move" mutation
re-targets the test table and must redden the all-roles row.

### G6 (S3/S4) — one definition each

`get_item_lifetime_economics` CALLS `serialize_item_lifetime_economics`
(deleting its inline duplicate dict — charter 4's zero-caller finding);
`get_task_budget_status.py`'s verbatim copy of `_build_evaluated_status`
is deleted and both services call the ONE helper — A7's three mutation
sites are the FILTERS (which stay per-service literals); the money
computation was never meant to be duplicated (charter 5).

### G7 (S5) — the structural row

`route.response_model is None` asserted over `item_economics.router.routes`
in the router test (P-H; regression-only is its job).

### G8 (S6) — soft-deleted item on DELETE valuation

The A15 re-resolution's item load raises `NotFound` for a soft-deleted
item, aborting a delete that succeeded before this phase (unsanctioned
regression). Corrected per the review's recommendation: when the item is
soft-deleted (or absent), resolve the preview to `ITEM_UNVALUED` rather
than refusing — restoring pre-phase behaviour. New criterion row +
mutation (revert to the raising load → row reds).

### G9 — the mutation pass, NO deferrals

All 18 review-ledger mutations re-run against the adopted+built rows, plus
G8's. **The deferral cap binds: zero deferrals this cycle** — every
mutation now has an in-tree arbiter. Per row: site → expected red node id
(L2's template), sha256 pairs copy-pasted, observed reds, reversion
proven. M15/M17's already-biting rows are regression re-runs.

### G10 — notes recorded

N1: the reopen touch point's only prior integration coverage is baseline
failure #5 — the adopted reopen probe row is the mandatory green (L6).
N2: the worker key-set arbiter sits on `serialize_item_cost_result_worker`
whose production path is `_serialize_result` — after G6's dedupe, verify
the arbiter guards the production path. N6/N7 recorded as intended
behaviour (unreachable today; premise noted). alembic-check drifts →
only-if-cheap ledger (routed).

- **2026-08-14 — review r1 CONSUMED by the coordinator.** Perimeter exact
  (probe artifact + 3 docs; app/ byte-identical to `6c1da6b`; probe hash
  re-verified `b5ac470c…`). Lessons L1–L6 folded into §9 (deferral cap,
  expected-red rule, call-graph rule, endpoint-boundary rule,
  hand-written-literal rule, red-coverage flag). This GOVERNING fix block
  G1–G10; fix prompt
  `prompts/implementer/2026-08-14_phase8_fix_r1.md`.

- **2026-08-15 — fix r1 IMPLEMENTED (Codex).** The preserved reviewer probe was
  adopted verbatim at
  `app/tests/integration/services/commands/item_economics/test_phase8_reviewer_r1_probe.py`:
  891 lines, 19 rows, SHA256
  `b5ac470c704e5f62be3d8752d7eb2b6f4e908469c5e944f764ee1a9d454abe3c`.
  G2 replaced serializer echoes with producer-driven C7 rows; G3 added real
  C2/C3/C4/C5/C6b coverage; G4–G8 delivered the five production corrections
  and the soft-deleted-item regression; G7 added the structural
  `response_model is None` guard. No migration or emission/handler/transition
  production files were changed.

  G9 mutation ledger — every row was applied, the named arbiter reddened, and
  the mutation was reverted; zero deferrals:

  | mutation | site | expected red arbiter |
  | --- | --- | --- |
  | M1 | manager committed-evaluation filter | `test_probe_c1_projection_isolation_with_a_discriminating_fixture` |
  | M2 | worker committed-evaluation filter | `test_probe_c1_worker_service_filter_is_independent_and_projection_blind` |
  | M3 | result-handler committed-evaluation filter | `test_probe_c1_projection_isolation_with_a_discriminating_fixture` |
  | M4 | DELETE valuation re-resolution | `test_probe_a15_delete_valuation_reresolves_the_status` |
  | M5 | READY-entry result emit | `test_probe_c6b_ready_entry_writes_ready_snapshot_with_null_closed_at` |
  | M6 | READY reopen result emit | `test_probe_c6b_reopen_through_add_task_steps_flips_snapshot_to_working` |
  | M7 | resolve terminal emit | `test_probe_c10_terminal_command_emits_exactly_one_result_task[C10-terminal-resolve]` |
  | M8 | fail terminal emit | `test_probe_c10_terminal_command_emits_exactly_one_result_task[C10-terminal-fail]` |
  | M9 | cancel terminal emit | `test_probe_c10_terminal_command_emits_exactly_one_result_task[C10-terminal-cancel]` |
  | M10 | straggler terminal guard | `test_probe_c6_straggler_guard_emits_exactly_on_ready_and_terminal[C6-straggler-RESOLVED]` |
  | M11 | straggler READY guard | `test_probe_c6_straggler_guard_emits_exactly_on_ready_and_terminal[C6-straggler-READY-half]` |
  | M12 | C7 selection-status producer swap | `test_probe_c7_hazard_selection_ok_without_committed_evaluation_reads_not_evaluated` |
  | M13 | economics `total_cost_minor` injection | `test_probe_c9_step_and_economics_money_key_sets_are_disjoint` |
  | M14 | lifetime snapshot substitution | `test_probe_c11_lifetime_uses_evaluation_snapshot_not_the_live_task_field` |
  | M15 | WORKER route authorization removal | `test_budget_status_route_is_available_to_all_roles[get-budget-status-worker]` |
  | M16 | hand-written route-table budget row removal | `test_router_route_pairs_match_the_authoritative_route_table` |
  | M17 | `computed_at` update removal | `test_c5_replay_updates_only_computed_at_and_converges` |
  | M18 | worker route manager-payload substitution | `test_probe_c9_budget_status_endpoint_returns_no_money_for_worker_roles[route-worker]`, `[route-seller]` |
  | G8 | soft-deleted item restored to `NotFound` | `test_g8_delete_valuation_on_soft_deleted_item_returns_item_unvalued` |

  Restoration hashes (entry = exit) were re-verified for the mutation-only
  files: `_task_state_transitions.py`
  `728e7770ca669ec914c6a53190b956713bf06639e84a6ee27e46f890b45073c2`,
  `process_step_transition.py`
  `fe1091c68a5fdb72bad8eb7c2f225d2d44f81b85842dfafdf7a8b4cb21267e80`,
  `resolve_task.py`
  `f5d9e23fb1090fa81a44b924b28a32792a13d6ffbf385cf745ddae6a79944cb4`,
  `fail_task.py`
  `bceb07689f923a640d3b7977b135ecfddc9c844ef8b72f41f3abe0a4eccede9c`,
  `cancel_task.py`
  `97de30b2fdb435f0cb5e0e42f04d0f2ee2498c496226452b403e0d54a16ea438`,
  and `process_item_cost_result.py`
  `d57ca890d0ad9b14eb09bdda339e07cfe94e3a20475621ca640e61a11e2e5172`.
  The adopted probe hash was also rechecked after the ledger and remains
  identical to its preserved source.

  Verification: focused phase-8 suite **146 passed**; full non-E2E suite
  **2138 passed / 23 established baseline failures / 1 deselected**, with the
  failure set unchanged; targeted `ruff check` passed; development database
  reports Alembic head `c1d2e3f4a5b6`. A repository-wide ruff run still reports
  123 pre-existing findings outside this fix perimeter (including the
  verbatim probe's pre-existing unused import). Architecture Graph was read
  only: no architectural delta was identified or applied.

- **2026-08-15 — re-review r2 (Claude Opus 5, plan-reviewer): CHANGES_REQUESTED.**
  **2 blocking / 3 should-fix / 6 notes, 0 owner cards.** Handoff:
  `handoffs/reviewer/2026-08-15_phase8_rereview_r2_handoff.md`.
  **Twelve of thirteen r1 findings CLOSED, each by the arbiter that was
  absent-or-green in r1**: all 19 declared mutations bite their named row (M5–M9
  emissions; M10 both straggler rows / M11 the READY half only; M1/M2/M3 the
  three filters; M4 A15; M13 the disjointness row PLUS both route rows; M18 both
  route rows; M16 now reddens the hand-written route-table arbiter; M17; G8;
  and G7's `response_model` row verified to bite under `response_model=dict`).
  Fifteen unchanged production files' mutant hashes REPRODUCE r1's byte-for-byte;
  the four changed files' necessarily differ. Perimeter exact (4 production + 4
  test + 2 docs; `git diff 0c85707..HEAD -- app/` empty; 15 files byte-identical
  to my r1 entry record); adopted probe hash-identical to the preserved source,
  19 collected, 19 green, all parametrize ids intact. Numbers reproduced:
  **2138/23/1**, failure set BYTE-identical to the phase-1 list, **+27**
  reconciled exactly (19 probe + 6 integration + 2 router + 0 serializer net).
  Graph zero-delta claim independently checked and CORRECT (G5 deleted dead code
  that was never a node; G6 is an intra-node refactor). DB at head, zero
  item-economics residue.
  **Two blockers remain, both found by mutations the reviewer added (neither is
  a shipped defect; both are one-fixture fixes):**
  **B1** C7's `ok`/`infeasible` rows are STILL hand-built serializer echoes —
  the r1 B4 shape preserved for exactly the two members A1 names as coming only
  from the committed-evaluation branch; MX2 (replace
  `INFEASIBLE if allowed <= 0 else OK` with a constant `OK`) SURVIVES, and the
  "`infeasible` ⇒ `percent_consumed` null" clause rides the same unarbitrated
  object. **B2** §8A.1's "`total_pause_seconds` / `total_ended_shift_seconds` /
  `inaccurate_*` are never read" (R-5) has NO discriminating fixture — every
  phase-8 consumption fixture carries zero in all three columns; MX1 (sum
  `total_working_seconds + total_pause_seconds` in the handler) SURVIVES, which
  would bill paused time against the production budget silently. C2 AS WORDED is
  satisfied — the new bucket row proves each ORM record lands in its own rollup
  column (A12's `PAUSED`+`SHIFT_ENDED` and the marked-wrong split both asserted);
  what is missing is the step from those columns into the phase-8 read.
  **Should-fix:** **S1** the adopted C1 probe row is INTERMITTENTLY RED on a
  clean tree (3 reds in ~25 wide-scope runs; reproduced: the committed row came
  back first from an unordered heap scan, firing the reviewer's own non-vacuity
  guard) — a defect in the r1 probe the fix adopted verbatim exactly as G1
  instructed; it fails SAFE (M1/M3 redden the row in both heap orders) but a
  flaky row corrodes the byte-identical baseline discipline (phase-2 N14 class);
  fix = assert over the candidate SET, not an unordered `scalar()` pick (same
  guard in the worker sibling row). **S2** the C5 config-supersession row CANNOT
  FAIL — it soft-deletes a `CostModelVersion` while the handler's call graph
  reads Task/ItemCostEvaluation/TaskStep and NO configuration table (grep-verified);
  it also does not exercise supersession (a soft delete is the delete path).
  **S3** C3 puts both batchable steps on ONE task, not the criterion's two — the
  dilution arithmetic is proven, the per-episode flow-through is not.
  **Notes:** N1 C6b re-entry's single-row claim uses `scalar()` (can't see a
  second row; UNIQUE makes it true anyway); N2 G7's row covers the budget-status
  route only, not all router routes as A17 worded it; N3 the fix ledger cites no
  per-row mutant hashes (P-I 9th) — behaviourally re-confirmed by the reviewer;
  N4 r1's N2 arbiter-placement question resolved by the route-money rows;
  N5 probe ids intact; N6 the 881 `user_section_daily_work_stats` rows are the
  known wider-suite class, zero orphaned, phase-8 rows clean their own.
  Lessons: (1) "rebuild every row on real producers" needs a per-row tick-list
  in the fix prompt — the two hardest rows stayed decorative; (2) criteria about
  a pipeline need a row at EACH end (C2 stopped one step short of the money);
  (3) non-vacuity applies to "nothing changed" rows too; (4) a fixture that
  depends on physical row order is not a fixture (earned against the reviewer's
  own probe); (5) per-row mutant hashes are what make a ledger re-derivable.

## Amendments (fix r2, routed from re-review r2, 2026-08-15) — GOVERNING

Where this block contradicts anything above, THIS BLOCK WINS. Routed from
`handoffs/reviewer/2026-08-15_phase8_rereview_r2_handoff.md` (2 blocking /
3 should-fix / 6 notes, 0 owner cards — ALL test-side; no production file
changes this cycle). The row list below is EXHAUSTIVE and each item is
ticked in the fix handoff (row-list tick rule).

### H1 (r2 B1) — C7's `ok`/`infeasible` rows drive the real producer

Two integration rows through `get_task_budget_status` against a COMMITTED
evaluation: `allowed_worker_minutes <= 0` → `status is INFEASIBLE` AND
`percent_consumed is None`; the `> 0` counterpart → `OK`. The
SimpleNamespace echo rows are deleted. The reviewer's MX2 mutation
(producer collapsed to constant `OK`,
`5f89e29b…bde8` → `57c4591f8d21fbdb5940cc9262012d0d41f33465e47a05c96ffd98ec23d2c140`)
must redden the INFEASIBLE row. The probe's `_committed_fixture` is the
scaffolding.

### H2 (r2 B2) — §8A.1's excluded-columns clause gets its discriminating fixture

Extend one consumption row's step with NONZERO `total_pause_seconds`,
`total_ended_shift_seconds` and `inaccurate_working_seconds`; assert
`result.actual_worker_seconds` equals the WORKING seconds alone. The
reviewer's MX1 mutation (pause seconds summed in,
`d57ca890…5172` → `fdae3c4106686398559c4c50574b9653d4b0a5d26f80e430f42dfa9f87b490b7`)
must redden it. One fixture edit — this is the row that stops paused time
being billed as consumption.

### H3 (r2 S1) — the two C1 probe rows made order-independent

AUTHORIZED verbatim-adoption deviation (the defect is the r1 reviewer's
own, specified by them): in
`test_probe_c1_projection_isolation_with_a_discriminating_fixture` and
`test_probe_c1_worker_service_filter_is_independent_and_projection_blind`,
replace the order-dependent `scalar()` pick + guard with a CANDIDATE-SET
assertion (the unfiltered predicate admits both rows; the literal
committed-current predicate admits exactly the committed row), keeping the
behavioural assertion on `status.evaluation_id`. M1/M2/M3 must still bite.
This closes the observed clean-tree flake (3 reds in ~25 runs — the
set-assertion rule).

### H4 (r2 S2) — the C5 supersession row rebuilt non-vacuously

Replace the soft-delete scenario: COMMIT a superseding basis/model version
with a DIFFERENT rate after the close; re-run the handler; assert the
§8A.4 column set byte-identical; PLUS the non-vacuity assertion that the
new live configuration would have produced a different number (P-J 5th
ext). The soft-delete row is deleted (it exercised the phase-4/5 delete
path, not §8.4 supersession, and the handler's call graph reads no config
table).

### H5 (r2 S3) — C3's second step moves to a second task

Second step on a SECOND task with its own committed evaluation; assert
EACH episode's `actual_worker_seconds` == 1800 and Σ == wall clock — the
flow-through into two episodes is the criterion's point.

### H6 (notes taken) — cheap ride-alongs

- N1: C6b re-entry's single-row claim uses a COUNT, not `scalar()`.
- N2: widen G7's structural row to quantify over
  `item_economics.router.routes` (A17's wording) — it bites today on the
  one route; the widening is one comprehension.
- N3/L5: the fix handoff's mutation ledger carries the PER-ROW MUTANT HASH
  as a required column (P-I 9th restated) — for the re-run rows, state
  reproduces/differs vs the r2 ledger's hashes.

### H7 — scope

TEST-SIDE ONLY. Zero production edits (the re-review proved all fifteen
untouched production files byte-identical and the four changed ones
correct; MX1/MX2 are proof gaps, not defects). Any production edit is
stop-and-report.

- **2026-08-15 — re-review r2 CONSUMED by the coordinator.**
  CHANGES_REQUESTED — 2/3/6, 0 cards. Twelve of thirteen r1 findings
  CLOSED (19/19 declared mutations bite; 11 mutant hashes reproduce r1's
  byte-for-byte, the rest differ only where the pre-image changed); the
  two new blockers are reviewer-ADDED mutations surviving (MX1 pause-bill,
  MX2 producer-constant) — the same echo/pipeline shapes as r1, caught one
  layer deeper; S1 is the reviewer's own probe flake, honestly attributed
  and specified. Reviewer perimeter exact (3 docs; app/ clean). §9 += five
  r2 rules (row-list tick, pipeline-ends, P-J 5th ext stability
  non-vacuity, set-assertion, P-I 9th as hard ledger field). This
  GOVERNING block H1–H7; fix r2 prompt
  `prompts/implementer/2026-08-15_phase8_fix_r2.md`.

- **2026-08-15 — fix r2 IMPLEMENTED (Codex / implementation-executor).** H1–H6
  are complete and H7 is satisfied: test-side only, with zero production edits,
  migrations, or Architecture Graph writes. H1 now drives both status rows
  through the real `get_task_budget_status` producer; H2 makes pause, ended-shift,
  and inaccurate seconds nonzero while asserting WORKING-only consumption; H3
  uses candidate-set assertions in both C1 probes and passed 10/10 consecutive
  runs; H4 commits a real superseding basis version with a different rate and
  proves the closed-task result snapshot is byte-identical and non-vacuous; H5
  uses two tasks with one committed evaluation each and proves 1800 seconds per
  episode and 3600 seconds in aggregate; H6 changes the re-entry check to a
  count and quantifies `response_model is None` over every
  `item_economics.router.routes`. The three SimpleNamespace C7 echo rows were
  removed. Focused phase scope: 146 passed; the H3 pair was 2 passed on each of
  10 runs (20 passes). Full `not e2e`: 2138 passed / 23 established failures /
  1 deselected; the sorted failure set is byte-identical to the phase-1
  baseline. Ruff passes on the three non-adopted changed test files; the adopted
  probe retains its pre-existing unused `ItemMajorCategoryEnum` import. Database
  head is `c1d2e3f4a5b6`; direct state checks report zero
  `item_cost_evaluations`, zero `item_cost_results`, and zero
  `execution_tasks` of `process_item_cost_result`. Mutation ledger: MX1 and
  MX2 reddened their exact H2/H1 rows; M1, M2, M3, and M17 reddened their exact
  probe/replay rows; every temporary production mutation was reverted and all
  three touched production hashes restored. Final test hashes are recorded in
  the fix handoff. Tracker moved to IMPLEMENTED; checkpoint and handoff follow
  the closing protocol.

- **2026-08-15 — re-review r3 (Claude Opus 5, plan-reviewer): APPROVED.**
  **0 blocking / 0 should-fix / 4 notes, 0 owner cards.** Handoff:
  `handoffs/reviewer/2026-08-15_phase8_rereview_r3_handoff.md`. Delta-scoped per
  the r3 prompt; the 15 ledger rows proven biting in r2 against byte-identical
  production files were NOT re-run (declared out of scope).
  **Perimeter exact:** `git diff 6988364..HEAD -- app/` empty; all seven declared
  hashes recomputed identical (3 production pre-images `d57ca890…`, `5f89e29b…`,
  `011cf2ae…`; 4 test files incl. adopted probe `7df683f7…`).
  **Both r2 blockers CLOSED, each by a mutation re-applied from the reviewer's own
  r2 bytes:** MX1 (`fdae3c41…b490b7`, hash reproduces) reddens
  `test_c4_consumption_excludes_deleted_steps_but_counts_skipped_steps` with
  `assert 150 == 120`; MX2 (`57c4591f…d2c140`, reproduces) reddens
  `test_c7_committed_evaluation_branch_drives_evaluated_status[P-V-infeasible]`
  with `assert 'ok' == 'infeasible'`. H1's rows drive the REAL
  `get_task_budget_status` against a committed evaluation (no hand-built object);
  the three SimpleNamespace echo rows are gone. **Three reviewer-added mutations
  this round also bite** (strengthening, not findings): MX1b ended-shift summed
  → `assert 160 == 120`; MX1c inaccurate summed → `assert 170 == 120` (so each of
  H2's three nonzero excluded columns discriminates INDEPENDENTLY, beyond the one
  named mutation); MX3 `calculate_percent_consumed` returning `0.00` instead of
  `None` for a non-positive allowance → `assert Decimal('0.00') is None`, closing
  the second half of r2 B1 (the `infeasible` ⇒ null-percent clause) on the
  production path. **C7 now enumerates all TWELVE shipped `EconomicsStatusEnum`
  members with BOTH producers real** — ten `resolve_item_economics_status` ids +
  `P-V-infeasible`/`P-V-ok` through the committed-evaluation branch (A1 satisfied
  for the first time). **S1 CLOSED structurally:** zero order-dependent picks
  remain in the probe (both rows assert candidate SETS); the pair ran 10x2 green;
  M1 (`3a659e93…`) and M2 (`783698f8…`) reproduce and redden their named rows in
  62/62 row-executions across focused (25 runs) and wide (6 runs, 35-test) scope.
  **S2 CLOSED:** the rebuilt C5 row commits a REAL superseding basis version
  (`create_production_cost_basis_version` closes the open version,
  `effective_to = effective_from` — verified in the command, not assumed) at a
  different rate, with two non-vacuity assertions (new rate != snapshot rate;
  recomputing at the new rate WOULD change `consumed_cost_minor`). **S3 CLOSED:**
  C3's second step sits on a second task with its own committed evaluation; each
  episode's `actual_worker_seconds` is 1800 and the sum is 3600. **H6 CLOSED:**
  re-entry asserts `func.count() == 1`; `response_model is None` quantifies over
  all `item_economics.router.routes` and BITES on a non-budget-status route
  (probed on `/configuration-status`), which is what N2's widening was for.
  **Numbers re-derived independently:** full non-E2E foreground **2138 / 23 / 1**
  (123.18s); failure set sorted-diffed **BYTE-IDENTICAL** to the phase-1 23-item
  list, zero drift; collection **net 0** reconciled exactly (serializers 15→13,
  status_results 14→16, probe 19 and router 98 unchanged; 2161 selected / 2162
  collected). Ruff clean on the perimeter except the declared pre-existing F401 in
  the adopted probe (correctly untouched — H3 authorized only two rows). DB left
  at head `c1d2e3f4a5b6`; zero item-economics residue (evaluations 0, results 0,
  `process_item_cost_result` execution-tasks 0); the 2 configuration rows present
  are pre-existing non-orphaned dev data from 2026-08-14. Graph read-only, zero
  delta: 172/254, rev `c74eb913…`, stale 1, 21 pending held.
  **Notes (all carried forward, none blocking):** **N1** C1's mutation bite is now
  order-CONTINGENT — the repair removed the fixture guard, so M1/M2/M3 redden only
  via `status.evaluation_id`, which depends on which row the mutated (unfiltered)
  `scalar()` returns; empirically 62/62 today, but r2 recorded the alternate heap
  order occurring on a clean tree, under which the mutation would silently
  survive. This is a limitation of the r2 reviewer's own H3 specification, not of
  the fix (H3's stated acceptance condition — M1/M2/M3 still bite — is verified);
  the order-free repair is a STRUCTURAL arbiter asserting the three services'
  compiled evaluation SELECT carries the three literal filter clauses. **N2** the
  C5 row's "after close" premise is not exercised — `_prepared` leaves the task
  WORKING, so `task_closed_at` (None) and `task_state_snapshot` (WORKING) are
  trivially equal on both sides of the ten-column comparison; the money invariant
  proven is closure-independent and C6b separately arbitrates both columns for
  terminal states (probe `:232-233`, `:266-267`), so no defect hides here — close
  the task before the second handler run, or rename the row. **N3** record
  quality: the fix handoff says "three SimpleNamespace C7 echo rows were removed";
  it was TWO (one parametrized function, ids `P-V-infeasible`/`P-V-ok`) — the
  collection reconciles at -2/+2. **N4** cosmetic: the serializer test's import
  block closing paren was re-indented to a stray `        )` and one of the two
  blank lines before `_result()` was dropped — an edit artifact in a file whose
  only intended change was row deletion; passes ruff (default rules exclude
  E1/E3), inconsistent with the rest of the perimeter.
  Lessons: (1) a filter-deletion mutation whose correct row REMAINS in the
  candidate set cannot be arbitrated order-independently by a behavioural
  assertion alone — such criteria want a structural arbiter over the compiled
  statement; (2) "prove the excluded columns are excluded" is stronger with
  DISTINCT nonzero values per column (30/40/50 → 150/160/170 identifies WHICH
  column leaked, where one shared value would only say "something leaked");
  (3) a stability row's fixture must also satisfy the SCENARIO the criterion
  names, not just its mechanism — "after close" needs a closed task.
