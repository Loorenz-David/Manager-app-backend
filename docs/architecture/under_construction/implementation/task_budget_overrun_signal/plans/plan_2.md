# Plan 2 — The batched service and its serializer: `get_task_budget_signals.py`

```
plan: plan_2
project: task_budget_overrun_signal
projection_gate: MANDATORY (rule-6 mechanisms: the allocator call's typicals, ordering, the no_budget construction, money on the production path)
```

## 1. Goal

Create `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py`
(master plan §6.3) — the sibling `get_task_budget_allocations`'s loading shape with a
different tail: per visible task, the four-argument allocator call, then either
`compute_budget_signal(...)` (phase 1) or `NO_BUDGET_SIGNAL`, attached to `task_id` and
`currency`, sorted by `task_id`, serialized by the new `serialize_budget_signals` in
`division_serializers.py` (§6.4). Integration tests on the disposable database.

**Explicitly NOT in this phase:** no route, no README row, no mirror-test change, no
frontend handoff. **Nothing in `get_task_budget_allocations.py` changes** — its loading
code is copied into the new service, never extracted into a shared helper (HC-2; M6).
`test_budget_allocations_query.py` is not edited; its `_seed` is copied.

## 2. Read first

- Master plan §§5 (esp. `46_serialization_local.md`, `25_soft_delete.md`, `22_performance.md`),
  6.1, 6.3, 6.4, 6.6, 6.8, 8 (phase-2 graph delta), 9, 10 (**database safety, the slot rule,
  Redis**).
- Intention header (confirm `RATIFIED`), §1 HC-2, HC-4, HC-5, HC-7, §1A (M2, M4, M5, M6),
  §2.5, §2.6, **§3A.1 in full** (the four arguments), §3A.5, **§4.1**, **§4A.1–4A.3**,
  **§5, §5A.1, §5A.2, §5A.3**, **§6A.1**, **§6A.4 in full**, §7.3, **§7A.1, §7A.2**, §7A.6
  (the corrected query-count statement), §7A.7 (superseded by F3 — the local contract).
- `plans/plan_1.md` §6 (the API you consume) and its Review log.
- Inventory handoff §1 rows 2, 6, 7, 8, 11, 13, 15, 16, 21 and §6.
- Code, at source: `get_task_budget_allocations.py` **whole file** (`:51-56` cap; `:58-67`
  visibility; `:69-200` loads; `:203-229` status; `:231-249` `DivisionStep` rows; `:284-291`
  reconciliation; `:292` actual seconds; `:314` inline serialization);
  `live_worked_seconds.py:18-30` (signature, `now`); `services/context.py:24` (`now` default);
  `division_serializers.py:22-23` (`_decimal` — **do not use it**), `:57-71` (the sibling
  serializer pair to mirror), `:210-220` (`__all__`);
  `models/tables/item_economics/item_cost_evaluation.py:30-39, :56` (currency, snapshot,
  allowed, the unique partial index); `tests/integration/services/queries/item_economics/
  test_budget_allocations_query.py:31-131, :229-244` (the fixture kit to copy: `_seed`, `_ctx`,
  `_seed_two_section_allocation`, `_cleanup`) and `:178-208` (the statement-counting
  technique); `test_live_worked_seconds.py` (how an open `StepStateRecord` is seeded and what
  share a single user's open interval contributes).

## 3. Dependencies

Phase 1 **APPROVED**. Gate: intention header `RATIFIED`; projection routed or waiver recorded.

## 4. Files expected to change

| File | Kind |
|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py` | NEW |
| `app/beyo_manager/domain/item_economics/division_serializers.py` | MOD, additive only (two functions, two `__all__` entries) |
| `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py` | NEW |
| `app/tests/unit/services/queries/item_economics/test_production_time_contract.py` | MOD, inherited C19 consumer-set update only: add `get_task_budget_signals` |

## 5. Ordered tasks

0. **Task 0.** Re-run plan 1 §7's probe (the P-* figures below reuse it) and additionally
   derive C1(a)'s figures with typicals `A: 3600, B: 1800` through the pure allocator. Read
   `live_worked_seconds.py` and `test_live_worked_seconds.py` and record, in the Review log,
   the exact share one user's single open `WORKING` record contributes after 60 s of
   `ctx.now` advance (the plan asserts **60**; if the loader's divisor makes it otherwise,
   that is a finding against C7(b) — do not adjust the test). Write the trace map.
1. Write `test_budget_signals_query.py` from §6. Copy the sibling fixture *components*, but
   use a fresh task per criterion row and attach **only** the steps named by that row; do not
   call `_seed` as an opaque ready-made task. Parameterise each committed evaluation's allowed
   minutes, snapshot rate, currency, and basis rate; every divergent evaluation uses its own
   task, item, and current evaluation. Historical `closed_at` values are derived from the
   fixed test `ctx.now`; `_cleanup` deletes `StepStateRecord` rows before `TaskStep` rows.
   Every test that commits rows owns a `try/finally` delete (charter rule 11½). Role in the
   context: `"manager"` (the service is not role-aware, but the fixture should not lie).
2. Add `serialize_budget_signal` / `serialize_budget_signals` (§6.4) — ten keys copied through,
   no `_decimal`, no `str()`, no `.get()` defaults.
3. Implement the service exactly as §6.3 fixes it. Copy the sibling's blocks; **do not import
   the sibling except for `_BUDGET_STATUSES`**. Ordering on the visibility query only.
4. L1 green → every §6.1 mutation, one at a time, reverted and md5-verified → L2 → one L4 stamp
   on the handed-over tree, ID-diffed against the 21-ID baseline. Run C7's mutation under
   `TZ=UTC` and the host zone.
5. Handoff + graph delta (§8: one `projection` node with the edges the tree proves) + owner layer.

## 6. Tests / acceptance criteria

Conventions: evaluation `cost_per_worker_minute_minor_snapshot = Decimal("3.7500")`,
`currency = SWEDISH_KRONA`, `allowed_worker_minutes = Decimal("60.00")` unless stated; each
criterion row uses a fresh task whose step set is **exactly** the steps named in that row;
steps carry their worked seconds in `total_working_seconds` and **no open `StepStateRecord`**
unless stated (so live seconds == settled seconds); a single working section unless stated.
Set a fixed aware `T`; every historical `closed_at` is derived from `T` and stays within the
90-day typical window. Construct contexts as
`ServiceContext(identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": "manager"}, incoming_data={}, query_params={"task_ids": [...]}, session=db_session, now=T)`.
Rows are read from `result["budget_signals"]`.

### C1 — the allocator call and the query shape · trace **§3.1, §3A.1, §7A.6 (HC-7) → M1, M6**

| Row | Fixture | Assertion | Expected |
|---|---|---|---|
| C1(a) | two sections `A`, `B` with seeded completed history (five samples each: `A` median **3600**, `B` median **1800** — copy `_seed_two_section_allocation`'s loop with `closed_at = T - 1 day`); the task has **only** `A` `completed` worked 2400 with `closed_at is None`, and `B` `pending` worked 0 | `projected_over_seconds, budget_state` | `0, within_budget` — allowances split 2400/1200, `B` left 1200, pot 1200. **Under an equal split** (typicals `None`) the same state gives `600, projected_over` |
| C1(b) | the C1(a) task requested alone, then together with two further evaluated tasks (no open records) — count statements with a `before_cursor_execute` listener as `test_budget_allocations_query.py:178-208` does | `count(three) == count(one)` | True (rule 13: **not** the literal twelve) |

### C2 — budget-bearing ⟺ a current committed evaluation · trace **§6A.1, §6 (D2) → M4**

| Row | Fixture | Assertion | Expected |
|---|---|---|---|
| C2(a) | committed evaluation, `60.00`, one `pending` step 0 | `budget_state != "no_budget"`; `currency` | `within_budget`; `"swedish_krona"` |
| C2(b) | committed evaluation, **`Decimal("-12.50")`**, one `pending` step, no work (P-C on the production path) | `budget_state, projected_over_seconds, over_seconds, allowed_seconds, cost_per_worker_minute_ten_thousandths` | `projected_over, 750, 0, 0, 37500` |
| C2(c) | **no** evaluation; its fresh task's primary item has an `ItemValuation` (`SWEDISH_KRONA`) | `budget_state` | `no_budget` |
| C2(d) | a committed evaluation with `superseded_at` set and **no** current one | `budget_state` | `no_budget` |
| C2(e) | a committed evaluation with `is_deleted = True` and no current one | `budget_state` | `no_budget` |

### C3 — the `no_budget` row is constructed · trace **§5A.2, §5A.3, §5.1 (D3) → M4**

| Row | Fixture | Assertion | Expected |
|---|---|---|---|
| C3(a) | unevaluated task whose one `working` step carries `total_working_seconds = 1200` | the whole row | `task_id`, `budget_state "no_budget"`, `currency "no_currency"`, and **all seven numerics `== 0`** — `actual_worked_seconds` included |
| C3(b) | the same task; its item carries an `ItemValuation` with `currency = SWEDISH_KRONA` | `currency` | `"no_currency"` — the valuation is never consulted |
| C3(c) | evaluated task with `evaluation.currency = EURO` | `currency` | `"euro"` and `type(...) is str` |

### C4 — the row shape and JSON forms · trace **§5, §5A.1, HC-4 → M4**

| Row | Fixture | Assertion | Expected |
|---|---|---|---|
| C4(a) | one evaluated task + one unevaluated task | `set(row.keys())` on **both** rows | exactly `{task_id, budget_state, over_seconds, over_cost_minor, projected_over_seconds, projected_over_cost_minor, currency, allowed_seconds, actual_worked_seconds, cost_per_worker_minute_ten_thousandths}` (derived: 10) |
| C4(b) | both rows | first `len(rows) == 2`; then per key: the seven numerics `type(v) is int and v >= 0`; `task_id`, `budget_state`, `currency` `type(v) is str`; `budget_state in BUDGET_STATES`; `currency in CURRENCY_VOCABULARY` | True |
| C4(c) | the whole `result` dict | `set(result.keys())`; then a recursive walk finds **no `list` or `dict` inside any row** (the only list is `budget_signals` itself) | exactly `{budget_signals}`; True |

### C5 — cardinality, duplicates, visibility, cap · trace **§7A.1, §7.3 (D7) → M4**

| Row | Fixture | Assertion | Expected |
|---|---|---|---|
| C5(a) | request `[visible, deleted (Task.is_deleted=True), foreign-workspace, "tsk_invented"]` | `len(rows)` and `rows[0]["task_id"]` | `1`, the visible id — no marker, no warning |
| C5(b) | request `[visible, visible, visible]` | `len(rows)` | `1` |
| C5(c) | `50` ids (49 invented + the visible one) | returns; `len(rows) == 1` | True |
| C5(d) | `51` ids | `pytest.raises(ValidationError)`; `str(exc).startswith("BUDGET_SIGNALS_TOO_MANY_TASK_IDS:")`; **statement count `0`** (raised before any query) | True |
| C5(e) | `51` copies of **one** id | raises the same | True — the cap is on the raw list (§7A.1) |
| C5(f) | request `[evaluated, unevaluated]` | `len(rows) == 2` and the unevaluated row is present with `no_budget` | True (M4 presence) |

### C6 — deterministic ordering · trace **§7A.2 → M5**

| Row | Fixture | Assertion | Expected |
|---|---|---|---|
| C6(a) | three evaluated tasks inserted in **descending** `client_id` order (`tsk_c_<t>` first, then `tsk_b_<t>`, then `tsk_a_<t>`); request order `[c, a, b]` | `[r["task_id"] for r in rows]` | `[a, b, c]` (ascending by the string's own ordering) |
| C6(b) | the same, request order `[b, c, a]` | same | `[a, b, c]` — identical to (a) |

### C7 — what M5 promises, and the absorbing `over` · trace **§6A.4 → M5**

| Row | Fixture | Assertion | Expected |
|---|---|---|---|
| C7(a) | evaluated task, no open record; two calls with `ctx.now = T` and `T + 60 s` | the two rows | **equal** (dict equality) |
| C7(b) | one `working` step with an **open `StepStateRecord`** started at `T − 600 s` by one user (seed as `test_live_worked_seconds.py` does); calls at `T` and `T + 60 s` | `actual_worked_seconds` delta; the keys `task_id, allowed_seconds, currency, cost_per_worker_minute_ten_thousandths`, row membership and order | delta **`== 60`**; the listed keys and the order **unchanged** |
| C7(c) | evaluated task already over (settled 3700, no open record); calls at `T` and `T + 60 s` | `budget_state` at both; `over_seconds` | `over`, `over`; `100` both times — and on the C7(b) fixture with settled 3600, `over_seconds` at `T + 60` `>=` at `T` |

### C8 — money and the second-domain operand on the production path · trace **§4A.1, §4A.2, §4.1, §3A.5 → M2**

| Row | Fixture | Assertion | Expected |
|---|---|---|---|
| C8(a) | evaluated task, one `completed` step settled **3736** | `over_seconds, over_cost_minor, projected_over_seconds, projected_over_cost_minor, budget_state` | `136, 9, 136, 9, over` |
| C8(b) | settled **3602** | `over_seconds` | `2` (the minute-domain derivation gives `1`) |
| C8(c) | the evaluation's `cost_per_worker_minute_minor_snapshot = Decimal("3.7500")` while its `ProductionCostBasisVersion.cost_per_worker_minute_minor = Decimal("9.9999")`; explicitly `await db_session.refresh(evaluation)` before reading the rate | `cost_per_worker_minute_ten_thousandths`; and `== int(evaluation.cost_per_worker_minute_minor_snapshot.scaleb(4))` on the **ORM-read** value, `== evaluation.cost_per_worker_minute_minor_snapshot * 10_000` exactly | `37500` — the snapshot, never the live basis |
| C8(d) | settled **3608** | `over_seconds, over_cost_minor, budget_state` | `8, 0, over` |
| C8(e) | evaluated task, `allowed = Decimal("-12.50")`, rate `Decimal("3.7500")`, two steps: `a` working in section A with `total_working_seconds = 60`, `b` pending in section B with `0`; no open record | `over_seconds, over_cost_minor, projected_over_seconds, projected_over_cost_minor, budget_state` | `60, 4, 810, 51, over` — re-derived through `calculate_consumed_cost_minor`; Task 0 re-derives it |

### 6.1 Named mutations — the closed set (19)

| # | Mutation (site) | Must redden |
|---|---|---|
| MUT-01 | call site: `divide_production_budget(allowed, division_steps, None)` | C1(a) (`600, projected_over`) |
| MUT-02 | move the evaluation `select` inside the per-task loop | C1(b) |
| MUT-03 | `_BUDGET_STATUSES = frozenset({EconomicsStatusEnum.OK})` local respelling | C2(b) (`no_budget`) |
| MUT-04 | drop `ItemCostEvaluation.superseded_at.is_(None)` | C2(d) |
| MUT-05 | drop `ItemCostEvaluation.is_deleted.is_(False)` | C2(e) |
| MUT-06 | delete the `no_budget` short-circuit: run the general path with `allowed_seconds_raw = 0` and the live actual | C3(a) (`actual_worked_seconds 1200`) |
| MUT-07 | `currency = valuation.currency.value if valuation else NO_CURRENCY` on the no-budget branch | C3(b) |
| MUT-08 | serializer: `"allowed_seconds": _decimal(row["allowed_seconds"])` | C4(b) |
| MUT-09 | serializer: add `"steps": []` to the row | C4(a), C4(c) |
| MUT-10 | drop `Task.is_deleted.is_(False)` from the visibility query | C5(a) (`2` rows) |
| MUT-11 | cap on `len(set(task_ids))` | C5(e) |
| MUT-12 | `_MAX_TASK_IDS = 51` | C5(d) |
| MUT-13 | `continue` when `evaluation is None` | C5(f), C2(c) |
| MUT-14 | delete `.order_by(Task.client_id.asc())` | C6(a) or C6(b) — **if neither reddens** (the heap happened to return ascending order) record a miss and grow the fixture to five ids; do not declare the mutation covered |
| MUT-15 | `load_live_worked_seconds(..., datetime.now(timezone.utc))` instead of `ctx.now` | C7(b) (delta ≠ 60) — run under `TZ=UTC` and the host zone |
| MUT-16 | `app/beyo_manager/domain/item_economics/budget_signal.py`, definition site `compute_budget_signal`: derive `over_seconds` as `max(0, int(-calculate_remaining_worker_minutes(Decimal(allowed), calculate_actual_worker_minutes(actual)) * 60))` | C8(b) |
| MUT-17 | `get_task_budget_signals.py`, call site: use the matching entry from the loaded `basis_versions` list's `cost_per_worker_minute_minor` instead of `evaluation.cost_per_worker_minute_minor_snapshot` | C8(c) |
| MUT-18 | `get_task_budget_signals.py`, definition site: move the raw-list cap check until after the visibility query | C5(d) (statement count becomes non-zero) |
| MUT-19 | `get_task_budget_signals.py`, call site: transpose `over_cost_minor` and `projected_over_cost_minor` in the per-task row dict | C8(e) |

Plus two **exception-shape probes** recorded as ledger rows (not criteria): in
`app/beyo_manager/domain/item_economics/budget_signal.py`, definition site
`compute_budget_signal`, pass `Decimal(over_seconds)` into the money call (expect `TypeError`
to surface from the service in C8(a) — the production consequence is a 500 with no identity,
§4A.1); use
`live_seconds.get(step.client_id, 0)` instead of strict indexing and confirm **no** test in
this file observes it — record it as the known blind spot the strict index exists for. The
two probes that touch `budget_signal.py` are reverted, declared phase-1-file probes, not
perimeter changes. For MUT-06's hypothetical general-path call, use `Decimal("3.7500")` as
the deliberately arbitrary rate; C3(a)'s red is `actual_worked_seconds`, not money.

## 7. Notes

- **Statement counting** is the sibling's technique (`test_budget_allocations_query.py:178-208`);
  reuse it for C1(b) and C5(d).
- **`ctx.now`** is the only clock; the service never calls `datetime.now`.
- The status-resolution branch for tasks without an evaluation (`get_task_budget_allocations.py:207-227`)
  is copied verbatim although **no wire field observes it** — its result can only ever be a
  non-member of `_BUDGET_STATUSES`. Recorded as structurally held: keep the copy so the
  equivalence in §6A.1 holds by the same code, and let the reviewer confirm it by source
  inspection. (Planner finding F6 in the handoff.)
- Graph delta (master plan §8): one `projection` node; edges only as the tree shows them.

## 8. Review log

*(append-only)*

- **Projection r0 consumed (2026-08-24).** `20260824_plan_2_projection_round_0.md` returned
  `AMENDMENTS_REQUIRED`. The owner approved the M6/§9 perimeter clarification; the coordinator
  then folded PROJ-01–10 and PROJ-12–15 without changing product semantics: criterion-local
  fresh task fixtures, parameterised evaluations, fixed-clock historical evidence, teardown,
  ORM refresh, sited mutations/probes plus MUT-18, the service envelope assertion, a constructible
  context, and the corrected cleanup citation. Explicit delegations: fresh task IDs must not
  collide with sibling helpers' scalar IDs `1`, `2`, or historical `100+`; MUT-06 may use
  `Decimal("3.7500")`. The owner then explicitly waived re-projection r1: one projection round
  is sufficient for this bounded phase, so the folded plan proceeds to implementation.
- **Implementation round 1 blocked at close (2026-08-24, Codex).** Added the batched service,
  additive ten-key serializer pair, and one criterion-local integration test for each of
  C1(a)–C8(d). Task 0 reproduced the plan-1 probe and the unequal-typical allocation, and
  confirmed that a single user's single open record contributes exactly 60 seconds after a
  60-second `ctx.now` advance. The honest red baseline was 28 import failures before the
  service existed. Final focused evidence: L1 **28 passed** and L2 **639 passed**. The one
  closing L4 stamp was **22 failed / 2785 passed / 1 skipped**: the durable 21 IDs remained,
  but `test_production_time_contract.py::test_c19_division_has_one_allocator_and_services_only_consume_it`
  was added because that inherited source scan hard-codes the two pre-phase-2 consumers. All
  18 named mutations reddened and were md5-restored; the
  Decimal money-operand probe surfaced `TypeError`, while the declared strict-index blind-spot
  probe stayed green at 28 passed and was restored. No new product judgment was taken. The
  complete trace, mutation, contract, perimeter, blocker, and graph records are in
  `handoffs/implementer/20260824_plan_2_implementation_round_1.md`.
- **Owner decision consumed (2026-08-25).** The owner approved the inherited C19 contract-test
  perimeter amendment. The allowed file is added to §4 and the master-plan §6.1 registry solely
  to add `get_task_budget_signals` to C19's allocator-consumer set. A bounded continuation must
  also restore unrelated formatting-only changes in `division_serializers.py`, re-stamp the
  resulting tree, checkpoint it, and then enter review.
- **Maintenance r1 consumed (2026-08-25).** `20260825_full_suite_fixture_order_stabilization_round_1.md`
  repaired the unrelated order-dependent clock-code fixtures and C10's nondeterministic SQL-order
  assertion. Both serial file orders passed, and its one L4 stamp returned exactly the durable
  baseline: **21 failed / 2786 passed / 1 skipped**, with an empty failing-ID delta. Its executable
  tree retains the Plan-2 service, serializer, integration-test, and C19 hashes from implementation
  round 2, so the evidence unblocks the Plan-2 checkpoint without a redundant full-suite run.
- **Review r1 findings folded (2026-08-25).** Owner-approved intention/master-plan field-count
  clarification now names seven numeric fields and updates the intention header to round 12.
  Before the bounded B1 fix, C4(b) gains its two-row non-vacuity assertion, C4(c)'s test must
  assert a non-empty `budget_signals` list, and C8(e)/MUT-19 add the unequal, non-zero money-pair
  witness: `60, 4, 810, 51, over`. The phase remains `CHANGES_REQUESTED` pending that fix.
- **Implementation round 2 blocked at close (2026-08-25, Codex).** The bounded continuation changed
  only C19's closed consumer set and restored the serializer's pre-round-1 formatting outside
  the two additive budget-signal functions and two `__all__` entries. The service and Plan-2
  integration test retained their round-1 SHA-256 identities, so the 18/18 named mutation
  ledger and two exception-probe records remain valid without re-execution. Honest continuation
  red: C19 failed with `get_task_budget_signals` as the sole extra member; after the authorized
  amendment C19 was **1 passed**, the Plan-2 integration file **28 passed**, L2 **639 passed**,
  but the closing stamp could not establish the required empty failing-ID delta. Run 1 was
  **22 failed / 2785 passed / 1 skipped** with one unrelated C10 ordering addition; C10 passed
  immediately at L1. The charter-authorized anomaly recovery was **24 failed / 2783 passed /
  1 skipped** with three different `clock_in_code` fixture additions; those three fail alone
  because they require two workspaces seeded by other files. One additive graph batch recorded
  the task-budget-signals projection plus its six proven containment/read/implementation edges;
  no endpoint or review item was changed. No checkpoint was made. Complete cycle evidence,
  perimeter, and owner card: `handoffs/implementer/20260825_plan_2_implementation_round_2.md`.
- **Checkpoint closeout (2026-08-25, Codex).** No executable or test file changed in this
  closeout. The Plan-2 service, serializer, integration test, and C19 hashes still match
  implementation round 2; the two maintenance test hashes still match maintenance round 1.
  The maintenance L4 stamp is therefore the handed-over executable-tree stamp: **21 failed /
  2786 passed / 1 skipped**, with additions `∅` and removals `∅` against the durable baseline.
  L4 budget was 0 and no test was rerun. The tracker moved to `IMPLEMENTED`; the checkpoint
  stages the authorized Plan-2 and maintenance artifacts plus only the already-recorded
  task-budget-signals graph projection and its six relationships. The unrelated bootstrap
  graph node/edges and the waived re-projection queue prompt remain unstaged. Checkpoint subject:
  `CHECKPOINT (not approved): task budget signal phase 2`.
- **Review round 1 — `CHANGES_REQUESTED` (2026-08-25, Claude Opus 5).** Full first-review
  checklist on `8a63402`. Gates passed; all seven declared SHA-256 hashes reproduce; trace chain
  bijective 28↔28 with no orphan test; all six §9 rule 7 traps escaped by named fixtures. The
  loading half is proven **structurally**: an AST-normalized comparison against
  `get_task_budget_allocations` yields exactly four deltas (function name, error identity,
  the added `.order_by(Task.client_id.asc())`, the tail), which discharges §3A.1's
  element-for-element invariant and HC-2's copy rule by construction and makes the never-exercised
  item-narrowing branch a non-issue. Reviewer L4 (1 of 1, authorized pre-run): **21 failed / 2786
  passed / 1 skipped**, durable-baseline additions `∅`, removals `∅`.
  **B1 (should-fix)** — no criterion can observe a transposition of `over_cost_minor` and
  `projected_over_cost_minor` in the row dict (`get_task_budget_signals.py:406-421`): measured
  **28 passed** under probe PR-A, while the control probe PR-B (`allowed_seconds` ⇄
  `actual_worked_seconds`) reddened C7(b). Cause: C8(a) `9/9`, C8(d) `0/0` and C3(a) `0/0` make
  the pair numerically equal, and C2(b) — the one fixture where they differ (`0`/`47`) — asserts
  neither. Violates intention §4.3, §5.1, §5A.1 → **M2**, and charter rule 2's companion.
  Correction: add **C8(e)** — trace §4.3, §5.1, §4A.1 → M2; fixture `allowed = Decimal("-12.50")`,
  rate `3.7500`, steps `a` (`working`, section A, 60 s) and `b` (`pending`, section B, 0), no open
  record; assert `over_seconds, over_cost_minor, projected_over_seconds,
  projected_over_cost_minor, budget_state` = `60, 4, 810, 51, over` (re-derived through the
  shipped `calculate_consumed_cost_minor`; re-derive again in Task 0 per §9 rule 3) — and
  **MUT-19**, `get_task_budget_signals.py` call site, transpose the two cost keys; C8(e) must
  redden. Closed set becomes 19. Extending C2(b) alone is insufficient: a zero operand cannot
  separate a mapping from a constant. C8(e) also lands §6A.2's "60 s logged, work still ahead"
  row on the service path.
  **N1 (note)** — "the eight numerics" is wrong; the row has seven (`task_id` is a string).
  Sites: intention §5A.2 and §6A.2 row 1, master plan §6.6, and this plan's C3(a) and C4(b) cells
  (C4(b) lists three strings *and* eight numerics — eleven fields in a ten-field row). Code and
  tests use seven and are correct. Owner card 1 gates the intention amendment.
  **N2 (note)** — C4(b) and C4(c)'s flatness half pass vacuously on an empty `budget_signals`
  list; add `assert len(rows) == 2` and `assert result["budget_signals"]`. Fold into the B1 fix
  cycle. C4(c)'s "recursive walk" wording vs the test's single-level scan is equivalent in effect;
  no action.
  **N3 / N4 (notes, routed to the coordinator, not to the fix cycle)** — the intention header
  still reads `round 10` after the round-11 amendment; and every plan file's `state:` header says
  `NOT_STARTED`, including approved Plan 1.
  Full findings, verified-correct items V1–V14, mutation-probe declaration, carry-forward table,
  four lessons and owner card 1: `handoffs/reviewer/20260825_plan_2_review_round_1.md`.
- **Fix round 1 implemented (2026-08-25, Codex).** Added the owner-authorized C8(e) fixture
  with the independently re-derived tuple `60, 4, 810, 51, over`, added the C4(b)/C4(c)
  non-vacuity assertions, and freshly executed the closed 19-mutation set after the test-file
  edit. Every mutation reddened, including MUT-19's money-key transposition. Final evidence:
  L1 **29 passed**, L2 **640 passed**, and the one L4 stamp **21 failed / 2787 passed /
  1 skipped**, with additions `∅` and removals `∅` against the durable 21-ID baseline. Ruff
  and diff checks passed. No production or architecture-graph meaning changed; the existing
  pending task-budget-signals projection and its six relationships remain sufficient. Full
  trace, mutation ledger, perimeter, evidence, and graph assessment:
  `handoffs/implementer/20260825_plan_2_fix_round_1.md`.
