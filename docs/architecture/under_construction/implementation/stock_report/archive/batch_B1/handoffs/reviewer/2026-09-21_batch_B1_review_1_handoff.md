---
plan: batch B1 (4, 5)
role: review
round: batch_B1-review-1
state: CHANGES_REQUESTED
date: 2026-09-21
actor: claude-opus-5 (plan-reviewer)
tree: 1351b5f
---

# Batch B1 review 1 — phases 4 and 5 (`stock_report`)

## 1. Verdict and counts

**CHANGES_REQUESTED.** No blocking finding; no production defect found. Four should-fix items,
three of which are test-coverage or ledger-integrity gaps rather than code defects, and one of
which (S2) is an explicit prompt directive that was not implemented and not declared.

The production code is contract-faithful on every point I checked, including the four the prompt
named as most likely wrong. Every criterion row has a test; every row I probed can fail.

| | PASS | FAIL | NOT_VERIFIED | total |
|---|---|---|---|---|
| Phase 4 (plan_4.md) | 61 | 1 | 0 | 62 |
| Phase 5 (plan_5.md) | 22 | 0 | 0 | 22 |
| **Batch B1** | **83** | **1** | **0** | **84** |

The one FAIL is plan 4 **C5(b)**, whose test asserts three of the outcome cell's four clauses
(finding S1). It is a partial row, not a wrong one.

## ⚠ OWNER DECISIONS REQUIRED (2)

### Card 1 — Should the priority-payload row be folded into plan 4 now, or inherited by phase 12?

**Question.** Add one criterion row now that pins the board event's priority field to a text
value, or let the priority phase pick it up later?

**Story.** A board row is marked "high". Somebody unassigns a task from it. Manager tries to tell
every open browser that the row changed, and the message it builds carries the priority as an
internal Python object instead of the word "high". The audit writer tries to store that message
and throws; the socket broadcast never goes out. Nobody's board updates, and the only trace is a
stack trace in the logs. Today the code does the right thing — but nothing in the test suite would
notice if a later edit undid it, and the next edit to that file is two phases away.

**Branches.**
- *Fold now:* one existing test gains two fixture lines and one assertion; the guard is locked in tonight.
- *Wait for phase 12:* the one-line safeguard sits unwatched across phases 6–11.

**Recommendation.** Fold now — the ratified contract already states the payload is text, so the
row is discharging an existing obligation, not adding one.

**On silence.** The gate holds; the batch stays CHANGES_REQUESTED either way for S1/S2/S4.

**Kind.** *The intention settles it* — §9D MC-19's payload spec names `"high"|"medium"|"low"|null`,
so the orchestrator is authorized to rule and fold the row.

*Trace:* intention §9D MC-19 payload block; plan 4 C1 group; projection H9; implementer handoff §12.

---

### Card 2 — Close plan 5 C2(c)'s residual hole in this fix round, or carry it to batch C?

**Question.** Give the goal self-heal row a second scenario now, or defer it?

**Story.** The rule is that Manager repairs a goal total only when it would go *below* zero, and
leaves a total that drifted *upward* for the manual repair tool, so a human sees it. The test that
guards that rule only ever exercises the paths where no subtraction happens at all. If someone
later made the subtraction path repair upward drift too, a stock manager would find the number
quietly corrected overnight with a repair record they never asked for, and the consistency report
that should have flagged it would come back clean.

**Branches.**
- *Close now:* one extra scenario in the same test file, same fix round.
- *Defer:* the rule stays unguarded on the path that actually subtracts, through batches C and D.

**Recommendation.** Close now — the fix round is already open and the scenario is four lines.

**On silence.** The gate holds; the hole is recorded as carry-forward N1 and does not block approval
of a future round on its own.

**Kind.** *Judgment, not settled by the intention* — §12A (c) settles the semantics (inline fires
only downward); whether to spend a criterion row on it is a planning call. Proceed provisionally on
the recommendation.

*Trace:* plan 5 C2(c); intention §12A (c), §6A MC-5 floor block; fold `a306298`.

---

## 2. Per-phase verdict tables

### Phase 4 — `plans/plan_4.md` (62 rows)

Shape column: **exact** = the assertion has the literal shape the row specifies. Test file is
`test_move_assignment.py` unless noted.

| Row | Test id | Shape | Verdict |
|---|---|---|---|
| C1(a) | `test_c1_a_to_c_creation[c1a]` | exact — counters, both events, clean | PASS |
| C1(b) | `…[c1b]` | exact | PASS |
| C1(c) | `…[c1c]` | exact | PASS |
| C1(d) | `test_c1_d_in_queue_to_in_progress` | exact; `:updated` asserted by list length, not payload (row says "+ `:updated`", no payload pinned) | PASS |
| C1(e) | `test_c1_e_in_queue_to_awaiting` | exact | PASS |
| C1(f) | `test_c1_f_in_queue_to_failed` | exact | PASS |
| C1(g) | `test_c1_g_in_queue_to_delete` | exact — counters, `is_deleted`/`deleted_at`/`deleted_by_id`, event kind+state, clean | PASS |
| C1(h)–(j) | `test_c1_h_to_j_in_progress_moves[c1h/c1i/c1j]` | exact | PASS ×3 |
| C1(k) | `test_c1_k_in_progress_to_delete` | exact | PASS |
| C1(l),(m),(o) | `test_c1_l_m_o_awaiting_moves[c1l/c1m/c1o]` | exact | PASS ×3 |
| C1(n) | `test_c1_n_awaiting_to_resolved_scanner` | exact — incl. `updated_by_id IS NULL`, `updated_at == now` | PASS |
| C1(p) | `test_c1_p_awaiting_to_delete` | exact | PASS |
| C1(q),(r) | `test_c1_q_r_terminal_delete_moves_no_counter[c1q/c1r]` | exact — `len(events) == 1` is the literal "no `:updated`" | PASS ×2 |
| C1(s) | `test_c1_s_in_queue_to_resolved_early` | exact — incl. the `:updated` payload | PASS |
| C1(t) | `test_c1_t_in_progress_to_resolved_early` | exact | PASS |
| C1(u) | `test_c1_u_resolved_early_to_delete` | exact — `len(events) == 1`, `deleted_by_id == U` | PASS |
| C2(a)–(f) | `test_c2_same_state_is_noop[c2a…c2f]` | exact — `events == []`, `count_writes == 0` over the four MC-9 tables, stamps unchanged | PASS ×6 |
| C3(a)–(v) | `test_c3_forbidden_moves_raise[c3a…c3v]` | exact — raises, counters unchanged, zero repair records, state and `is_deleted` unchanged | PASS ×22 |
| C4(a) | `test_c4_a_units_not_one` | exact | PASS |
| C4(b) | `test_c4_b_two_assignments_second_item_and_task` | exact | PASS |
| C4(c) | `test_c4_c_updated_event_uses_returning_not_stale_orm` | exact; **I re-ran this mutation myself** (probe E) — reddens this test and only this test | PASS |
| C5(a) | `test_c5_a_downward_drift_self_heals_with_one_repair_record` | exact — all six record fields, the `delta=-4` warning, check `[]` | PASS |
| C5(b) | `test_c5_b_upward_drift_is_not_self_healed` | **partial** — asserts success, counters, zero repair records, the one `counter_in_queue` divergence; does **not** assert the row's final clause "`repair_stock_report` then clears it", and filters the divergence list by kind instead of asserting it whole | **FAIL (S1)** |
| C5(c) | `test_c5_c_delete_write_order_self_heals…` (`test_remove_assignment.py`) | exact | PASS |
| C6(a) | `test_c6_a_removing_the_only_assignment_clears_the_flag` | exact; fold armed it (flag seeded `true`) | PASS |
| C6(b) | `test_c6_b_flag_stays_true_while_a_second_assignment_remains` | exact | PASS |
| C6(c) | `test_c6_c_flag_flip_never_stamps_task_updated_columns` | exact; **the row's own named mutation does not reach this sub-check** — I armed it with a different mutation and it bit (probe B, note N3) | PASS |
| C7(a) | `test_c7_a_stamps_actor_and_now` | exact | PASS |
| C7(b) | `test_c7_b_null_actor_means_scanner` | exact | PASS |
| C7(c) | `test_c7_c_delete_stamps_deleted_only` | exact — `updated_by_id` still X | PASS |
| C7(d) | `test_c7_d_counter_move_does_not_stamp_the_row` | exact; fold armed it (seeded non-null `t_seed`/X) | PASS |
| Required ledger row | `test_required_ledger_row_double_decrement_self_heals` + the `−2q` run | correctness case present; the `−2q` run is ledger row 31, reddening only the repair-record half as predicted | PASS |

### Phase 5 — `plans/plan_5.md` (22 rows), `test_goal_credit.py`

| Row | Test id | Shape | Verdict |
|---|---|---|---|
| C1(a) | `test_c1_a_creation_into_awaiting_credits_the_goal` | exact | PASS |
| C1(b),(c) | `test_c1_b_c_active_to_awaiting_credits_the_goal[c1b/c1c]` | exact | PASS ×2 |
| C1(d) | `test_c1_d_no_goal_record_credits_nothing` | exact — `count_writes` on `stock_report_history_records == 0`, `mem IS NULL` | PASS |
| C1(e) | `test_c1_e_scanner_resolve_keeps_the_credit` | exact | PASS |
| C1(f)–(i) | `test_c1_f_to_i_leaving_awaiting_uncredits[c1f…c1i]` | exact; the flag fixture switches on `ends_deleted`, exactly as the fold's rule reads | PASS ×4 |
| C1(j) | `test_c1_j_subtraction_lands_on_the_credited_record_not_the_current_one` | exact — explicit `T0`/`T1`, both records asserted | PASS |
| C1(k) | `test_c1_k_no_memory_before_any_goal_leaves_it_untouched` | exact | PASS |
| C1(l) | `test_c1_l_resolved_to_delete_keeps_the_credit` | exact | PASS |
| C1(m) | `test_c1_m_active_to_terminal_credits_nothing` | exact | PASS |
| C1(n) | `test_c1_n_entering_resolved_early_from_in_queue_credits_the_goal` | exact | PASS |
| C1(o) | `test_c1_o_entering_resolved_early_from_in_progress_credits_the_goal` | exact | PASS |
| C1(p) | `test_c1_p_resolved_early_no_goal_record_credits_nothing` | exact | PASS |
| C1(q) | `test_c1_q_resolved_early_to_delete_keeps_the_credit` | exact | PASS |
| C2(a) | `test_c2_a_downward_drift_self_heals_with_one_repair_record` | exact — all record fields, the `delta=-4` warning, check `[]` | PASS |
| C2(b) | `test_c2_b_recomputation_includes_deleted_resolved_credit` | exact; fixture starts G at 0 instead of crediting to 5 then forcing 0 — observationally identical (stored `"0"`, recomputed `"2"`) | PASS |
| C2(c) | `test_c2_c_upward_drift_is_not_self_healed_by_a_move` | exact — incl. the `repair_stock_report` manual leg and the single `manual` record. **Its named mutation is inert at the named site** (note N1, card 2) | PASS |
| C2(d) | `test_c2_d_recomputation_includes_resolved_early_credit` | exact; drives A1 and A2 through `move_assignment` as the row's `MV(...)` notation requires | PASS |
| C3(a) | `test_c3_a_worked_sequence` | exact — all six steps asserted at their stated checkpoints, both `recompute_goal_total` values, clean, zero repair records | PASS |

## 3. Mutation audit — declared vs executed

**`executed == declared` is asserted in both phases and derivable in neither.** This is the
review's most charter-central finding (manifest properties 3 and 4: counts are derived, never
typed; the declared mutation set is closed). See S4.

**Phase 4.** The handoff claims `declared = executed = 33`.
- Its own per-criterion summand string `3+1+3+1+1+1+2+3+4+1+…+1` has 21 terms summing to **31**, not 33 (recomputed).
- Its ledger table has 31 numbered rows, of which **row 13 is explicitly not a run** ("equivalent-run, see row 10"), giving **30 distinct executed mutation texts**.
- Two plan-named mutations are executed but absent from the summands: plan C1(d)/(e) ("apply `+q` without `−q`", table row 4) and plan C7(c) ("stamp `updated_*` on delete", executed under the name C1(g)(iii), table row 8).
- The plan's 22 C3 "allow it" cells were collapsed to 4 guard mutations + 1 combined proof. The collapse is legitimate (see §4.1) but makes "33" un-reconcilable against the plan cells.

**Phase 5.** The handoff claims `declared = executed = 15`. Its own prose enumerates **13** named
groupings; its table has 14 rows, two of which (12, 13) are the same named mutation re-sited. So
**13 distinct declared, 14 runs**. 15 is derivable from neither.

**Substantively**, I believe every plan-named mutation was in fact executed: the table's
observed-red sets are internally consistent with the code, and the four I re-ran myself all
behaved as an independent derivation predicts. The defect is the arithmetic, not the work.

### What I re-ran myself (variation, not reproduction)

Tree for every probe: `1351b5f`, `git status --porcelain` empty before and after each, checksums
verified byte-identical (§9).

| # | Probe | Site | Scope | Observed | Verdict |
|---|---|---|---|---|---|
| A | C3 combined removal: terminal guard → `pass`, resolved guard → `return`, resolved_early guard → `return` | `_move_assignment.py::_assert_allowed_move` (definition) | L1 `test_move_assignment.py` | **18 failed / 41 passed**, exactly `c3d,e,f,g,h,i,j,k,l,m,o,p,q,r,s,t,u,v` — **including c3m, c3s, c3u, c3v** | confirms the implementer's row 22 exactly |
| B | drop `updated_at=Task.updated_at` from the flag UPDATE | `_task_flag.py::set_task_stock_flag` (definition) | L1 `test_remove_assignment.py` | **1 failed** — `test_c6_c` only, on the timestamp assertion | **new evidence**: C6(c)'s sub-check *is* armed, by a different mutation than the plan names |
| C | C1(u)'s **declared-equivalent** mutant: `−q` on `quantity_awaiting` when `from_state == RESOLVED_EARLY` | `_move_assignment.py::_delta_vector` (definition) | L1 move + goal_credit | **2 failed** — `test_c1_u` and phase 5 `test_c1_q` | **refutes** the fold's equivalence call (N2) |
| D | C2(c)'s named mutation at its **literal** site: unconditional divergence check + repair after the guarded subtraction returns 1 row | `_goal_credit.py::_uncredit` (definition) | L2 `commands/stock_report/` + `queries/stock_report/` — **118 passed** | **completely inert at batch scope** | confirms and widens the implementer's finding (N1) |
| E | C4(c)'s named mutation: build the `:updated` payload from the identity-mapped ORM instance | `_move_assignment.py::_apply_counter_delta` (definition) | L2 `commands/stock_report/` | **1 failed** — `test_c4_c` only | confirms; the row is armed and specific |

No L4 run was taken: my tree is byte-identical to the orchestrator's stamped `1351b5f`, so the
21/3349/2 stamp is consumed by citation (charter test-evidence reuse; re-running it would itself be
a finding).

## 4. The five risk areas

### 4.1 Risk 1a — phase 4 C3's four double-guarded rows

**Confirmed, and the rows are genuinely armed.** Probe A reproduces the implementer's combined
removal independently and reddens all 18 non-creation C3 rows, `c3m`/`c3s`/`c3u`/`c3v` among them.

The structural fact the implementer reported is real: `_assert_allowed_move` has four `raise`
sites, and those four cells are covered by two of them, so no single-guard removal reddens them.
That is **not** a row that cannot fail — it is a row whose absence proof requires a two-guard
mutant, which the implementer ran and I reproduced. Charter rule 15 asks for "the planted defect
and the observed red"; a defect that requires two edits is still a planted defect.

It is also not lesson L-12's shape inverted into a problem: L-12 warns that one mutation may not
*reach* every sub-check. Here one mutation does not reach *any* of the four rows, which the
implementer detected and corrected by escalating the mutant, rather than declaring the rows
covered. That is the behaviour the rule wants.

**Do the four collapse into fewer real checks?** In code, yes — they are redundant against any
single-branch defect. In specification, no: the table is deliberately total over six states
(plan 4 note, round 9), and the redundancy is a property of a *correct* implementation, not of the
criteria. A future implementation that expressed the table as one lookup would make all 22 cells
single-guarded. Keep the rows. **No finding.**

### 4.2 Risk 1b — phase 5 C2(c)'s inert mutation

**The re-siting was legitimate; the inertia is real and leaves a residual hole.**

Probe D plants the named mutation at the literal site the fold gave it and runs it over the whole
stock-report tree: **118 passed, nothing red.** So the inertia is not an artefact of the
implementer's scope — no test in the batch, and none in batch A, would catch an unconditional
inline self-heal inside `_uncredit`'s 1-row branch.

The cause is the fixture, not the implementation. C2(c)'s scenario is `awaiting → resolved` then
`resolved → DELETE`; per MC-5 the first move issues **no statement at all** on the goal record
(§6A MC-5 row 3: "none: the record keeps the units") and the second falls through to the terminal
default. `_uncredit` is never called. Reading MC-5 literally, the implementation is right and the
cell's site description is wrong.

Re-siting the mutation to the `RESOLVED` early-return branch tests the same *defect class* (an
inline self-heal on a move that should leave the record alone) against the code that actually runs
in this scenario, and it reddened exactly `c2c`. That is a faithful realisation of the cell's
intent. **The row is armed; it is armed against a different site than the cell names.**

Residual: the subtraction path's 1-row branch has no guard. Closing it costs one scenario — A
`awaiting` `q = 4` `mem = G`, raw `G = 9` (upward drift large enough that `9 − 4 ≥ 0` passes the
guard), `MV(awaiting → in_queue)`; correct outcome `G == 5`, zero repair records, check reports
`goal_total` stored 5 expected 0. Under the mutation a record appears and `G` becomes 0. Routed as
note N1 and owner card 2.

### 4.3 Risk 2 — H9, the enum serialization

**The fix is correct, load-bearing, and exercised by nothing. A row is needed now, and the
intention says so.**

Verified structurally:
- `StockReportItem.priority` is `Mapped[StockReportPriorityEnum | None]` on a native PG enum
  (`stock_report_item.py:52-57`), so `RETURNING … priority` yields an enum member.
- `event_bus.dispatch` does no serialization; it hands the event to three registered handlers
  (`bootstrap.py:42-44`). `audit_handler` writes `detail=event.extra` onto an audit record, and
  `socket_handler` → `push_workspace_refresh` → socket emit both encode the payload. An enum
  member in `extra` breaks both.
- **Intention §9D MC-19 pins the payload**: `"priority": "high"|"medium"|"low"|null`. The value is
  contractually a string. `_events.py:23` emits `priority.value`, which is correct.
- **No fixture in phases 4 or 5 sets a non-null `priority`** (`_make_row` never passes it;
  `_assert_row_event` defaults `priority=None`). Read-verified across all three test files.

So the safeguard ships with no criterion naming the mutation that would redden it — exactly the
construction charter rule 11 forbids, and the shape of this project's own measured Sonnet finding
(an inert safety switch that a review affirmed).

**Decision: a row now, not phase 12.** Reasons: (a) MC-19 already obliges it, so the row discharges
an existing contract rather than inventing one; (b) `_events.py` is next edited in phase 8
(`coalesce_stock_report_events`), four phases before priority triage; (c) the fixture cost is two
lines. One caveat for whoever writes it: the consistency check reports `priority_order_nullness`
when exactly one of `priority`/`priority_order` is set (`consistency.py:166-183`), so the fixture
must set **both** or the row's `assert_stock_report_clean` will fail for an unrelated reason.
Owner card 1.

### 4.4 Risk 3 — the task-flag fixture rule (folds F4-1 / F5-1)

**Present where required, absent where required, and it does not do the rows' work. The fold
worked.**

(a) *Present.* `_seed_flag(…, True)` is called in every phase-4 scenario that ends with A
non-deleted, and in the phase-5 equivalents. Phase 5's C1(f)–(i) does it conditionally
(`not ends_deleted`), which is the rule expressed as code rather than copied per row.

(b) *Absent.* Verified row by row for the eight plan-4 rows and the five plan-5 rows the fold
names: plan 4 C1(g), C1(k), C1(p), C1(q), C1(r), C1(u), C5(c), C7(c) — none calls `_seed_flag`;
plan 5 C1(i) (via the conditional), C1(l), C1(q), C2(c) — seeded `False`; C3(a) step 6 seeds
`True` at the start and lets `remove_assignment`'s recompute drive it to `False` before the final
clean assertion, which is correct and stronger than leaving it false.

(c) *Not doing the row's work.* The two rows the prompt singles out:
- **C6(a)** — flag seeded `true`, outcome asserts `false`. Without the seed, `set_task_stock_flag`
  no-ops through `is_distinct_from` and "skip the recompute" cannot fail. With it, the mutation
  reddens on both the direct flag assertion and `assert_stock_report_clean`. **The fold armed it.**
- **C6(c)** — flag seeded `true` plus `tasks.updated_at`/`updated_by_id` seeded to known non-null
  values. Probe B confirms the timestamp sub-check is live. **The fold armed it.**

(d) One qualification, recorded as note N3: C6(c)'s *named* mutation ("write the flag via the ORM
attribute") does not reach the row's own sub-check. The implementer reported why — a
`session.get(Task, …)` returns the stale identity-mapped object whose `is_stock_assignment`
SQLAlchemy already believes is `True`, so the unit of work emits no UPDATE at all and the flag
simply stays wrong; `assert_stock_report_clean` reddens, the timestamp assertions never do. That
is charter rule 12's shape. The sub-check is nonetheless armed, by the mutation I ran instead.

### 4.5 Risk 4 — the guarded counter statement and the inline self-heal (MC-1)

All verified against intention §5A MC-1 (round-7 re-check block) by reading and, where noted, by
probe:

- **Write order.** Own columns → `flush()` → guarded UPDATE → goal step → events
  (`_move_assignment.py:203-268`). Creation inserts with `state` set and flushes; DELETE writes the
  soft-delete trio and nothing else. ✔
- **`WHERE` carries no predicate beyond the guard.** `client_id == row_id` plus the three
  `col + delta >= 0` guards; no `workspace_id`, no `is_deleted` (`_move_assignment.py:105-112`).
  Exactly MC-1's "0 rows means exactly a counter would go negative". ✔
- **`stored_before` read fresh** by a dedicated `SELECT` after the 0-row result, never from the ORM
  instance (`:130-142`). ✔
- **One repair record per diverging column**, gated on `stored_value + delta != recomputed_value`
  (`:160-176`) — which is why C5(a) gets exactly one record and not three. ✔
- **The delta reaches the warning.** `write_repair_record(… delta=delta)` → the `logger.warning`
  format string carries `delta=%s` (`_repair_records.py:43-51`). C5(a) and phase 5 C2(a) both
  assert `"delta=-4"` in the captured message. This is what the B2 amendment exists for and it is
  discharged. ✔
- **Events built from `RETURNING`, never the ORM instance.** `_apply_counter_delta` returns
  `dict(row)` from the guarded statement, or `dict(repaired)` from the absolute UPDATE; the event
  builder consumes only that. Probe E plants the ORM-instance payload and reddens exactly
  `test_c4_c`, so C4(c)'s premise — the identity-mapped instance stays stale at 10 — holds and is
  the thing being measured. Nothing in `move_assignment` expires or refreshes R. ✔
- **`:updated` suppression.** Emitted iff `any(delta != 0)` (`:260`). That satisfies plan 4
  C1(q)/(r)/(u) and MC-19's "deleting a terminal assignment moves no counter, so no `:updated`".
  Carry-forward N6 for phase 8: it is *not* the same as MC-19's net-change rule — C5(c) is a live
  case where the deltas are non-zero, the self-heal restores the counters to their pre-move values,
  and a `:updated` is emitted whose payload equals the snapshot. `coalesce_stock_report_events`
  must compare values against `initial_row_values`, not merely dedupe by entity.

### 4.6 Risk 5 — lock order and the H6 premise

**Split verdict: the production side is right; the test side was not done and the divergence was
not declared.**

- **`apply_goal_effect` takes no lock on `R`.** Confirmed: `current_goal_record_id` is a plain
  `SELECT … ORDER BY (created_at, client_id) DESC LIMIT 1` with no `with_for_update`
  (`_goal_credit.py:19-36`); neither credit nor uncredit adds one. This is exactly intention §6A
  MC-5's round-7 re-check ("no lock is taken on `R` itself") and the prompt's N-R1 ruling. ✔
- **`remove_assignment` writes `tasks` after the row and assignment locks**, inverting MC-1's order,
  as H6 predicted. The resolution — the caller already holds the task lock — is a *premise*, and
  N-R1 made proving it the implementer's obligation.
- **No test in the batch takes any lock.** `grep -rn "with_for_update\|FOR UPDATE"` over
  `tests/integration/services/commands/stock_report/` returns nothing; the only match in the
  stock-report tree is `_locks.py:34` itself. Plan 4 §5 task 4 ("Test files hold the locks the way
  callers will — row `FOR UPDATE`, then assignment `FOR UPDATE`, inside one transaction"), the
  implementer prompt's H6 ("In phase 4's tests, take the task `FOR UPDATE` before the row lock, so
  the test models the caller. Record the premise in the handoff") and N-R1 ("plan 5's tests hold
  row + assignment `FOR UPDATE` before calling") are all unimplemented, and the handoff does not
  mention locks anywhere. Finding S2.

## 5. Judgment on the fold (`a306298`, 22 cells)

**No over-reach. No fold weakened a row, changed what a row asserts, or shaped a fixture to the
implementation.** Twenty of the twenty-two cells did exactly what the fold note claims. Two carry
analytical errors, both discovered by measurement, both in the safe direction.

**What the fold got right, specifically.**
- *The task-flag rule (F4-1/F5-1).* The single highest-value cell in the set. Without it ~50 rows
  whose outcome is "clean" fail against the shipped check, and C6(a)/C6(c)'s mutations are inert by
  construction. It arms rather than assists: it sets the flag to the value a *correct* system would
  hold before the operation, so the operation still has to change it.
- *C2(a)–(f).* The pre-fold cell read "write equal values", which the implementation short-circuits
  before writing anything — a genuinely inert mutation on a six-row group. The three enumerated
  replacements each bite a distinct sub-check (writes / stamps / return value). This is the fold's
  clearest win.
- *C1(a), C1(g), C1(u).* Enumeration per sub-check, charter rule 12's other half. Each enumerated
  mutation reddened a different assertion, as the plan predicted and the ledger records.
- *C1(g)'s equivalence call is correct.* "Soft-delete after the counter statement" cannot be
  observed on C1(g) (consistent counters, the guard never trips) and is genuinely carried by C5(c),
  where drift makes it observable — and C5(c) names it. Verified by reading both paths.
- *C4(c), C6(a), C6(c), C7(d).* Each adds the precondition without which the named mutation cannot
  be observed. C4(c)'s "do not expire, refresh or re-select R" is arming in the strict sense: a
  test that re-selected R would report 99 under both the correct code and the mutant, making the
  row decoration with a correct name.
- *Plan 5's explicit `created_at`.* C1(j) and C3(a) both turn on which goal record is "current";
  ULID `client_id`s do not order reliably inside a millisecond, so without the explicit timestamps
  those two rows are coin flips that pass most of the time. Real disarming, correctly closed.
- *The mirror declarations (C1(c)/(g)/(h)/(i)).* Purely bookkeeping — they change no arming and make
  the `declared` count honest. Ironically the count still did not close (S4), but not because of
  these cells.

**Where the fold erred.**

**F-1 (the one that cost something) — plan 5 C2(c)'s site narrowing.** The pre-fold cell read
"fire inline on any mismatch", which is implementation-agnostic and satisfiable wherever the code
actually runs. The fold replaced it with "in `_goal_credit.py` (definition site), after the guarded
subtraction returns **1** row … a record appears on the **first** move". That site does not execute
in this row's own scenario, because MC-5 requires `awaiting → resolved` to issue no statement at
all. The fold narrowed a correct-but-vague cell into a precise-but-unreachable one.

The authority is the charter's own rule 17 attribution: plan authorship owns the fixture/mutation
seam, and *"the coordinator at every fold, since amending a row is authoring one"*. The check that
was skipped is small — read the adjacent fixture cell and ask whether the named site executes in
it. Cost: one inert mutation run, one judgment call pushed onto the implementer (which it handled
correctly and reported), and a residual coverage hole (N1, card 2). The row's **outcome** cell was
untouched and the test asserts it in full, so nothing shipped weaker than specified.

**F-2 (harmless, but worth knowing) — plan 4 C1(u)'s equivalence call is wrong.** The fold declared
"subtract `q` from `quantity_awaiting`" an equivalent mutant on C1(u), reasoning that the guard
trips and the self-heal restores 0. Probe C measures it: it reddens `test_c1_u` **and** phase 5's
`test_c1_q`. Two causes the reasoning missed — the `:updated` event is gated on the delta vector,
not on whether the counters actually changed, so a non-zero delta produces a second event and
`len(events) == 1` fails; and the self-heal writes a repair record, so `assert_stock_report_clean`
fails too. The call was made against code that did not yet exist, which is the structural
difficulty with declaring equivalence at fold time rather than at review time. Effect: one mutation
the implementer was correctly told not to run. The row was armed by its other two mutations, so
nothing was lost.

**Judgment.** If the question is "did I over-reach", the answer is no — the authority boundary
(mutation and fixture cells only, no outcome cell) was respected in all 22, and I checked each
against its outcome cell. The lesson is narrower and worth carrying into batch C: **a fold that
replaces a vague mutation with a precise site must verify that the site executes under the row's
own fixture.** Vagueness and unreachability fail differently — a vague cell makes the implementer
choose, an unreachable one makes it choose *and* look wrong for doing so.

## 6. Batch-level findings, grouped by cause, blocking first

**Blocking: none.**

### S1 (should-fix) — plan 4 C5(b) asserts three of its four clauses

*What is wrong.* The outcome cell is "succeeds; counters `(1, 4, 0)`; **zero** repair records;
check reports one `counter_in_queue` (stored 1, expected 0); **`repair_stock_report` then clears
it**". `test_c5_b_upward_drift_is_not_self_healed` stops at the divergence assertion. Its sibling
row, plan 5 C2(c), does ship the equivalent manual-repair leg, so the two halves of the same
`§12A (c)` contract are covered asymmetrically. Secondarily, the divergence assertion filters the
check output to `kind == "counter_in_queue"` before comparing, so a second, unrelated divergence
would pass unnoticed; the row says "check reports one".

*Violated authority.* plan 4 §6 C5(b) outcome cell; charter rule 2 (each row asserts its one exact
expected outcome).

*Correction.* Add the `repair_stock_report(ctx)` leg — assert `[e["kind"] for e in
result["repaired"]] == ["counter_in_queue"]`, the counters back to `(0, 4, 0)`, and one `manual`
repair record — mirroring `test_c2_c`'s closing block. Assert the divergence list whole instead of
filtering.

### S2 (should-fix) — the tests model no locks, and the divergence is undeclared

*What is wrong.* Plan 4 §5 task 4, projection hazard H6 and routed decision N-R1 all require the
phase-4 and phase-5 tests to hold the caller's locks (task `FOR UPDATE` first for
`remove_assignment`; row then assignment `FOR UPDATE` before `apply_goal_effect`). No test in
either file takes any lock. N-R1 framed this as the implementer's positive obligation — "prove the
premise, not add a lock" — so the premise that makes `remove_assignment`'s inverted write order
safe is currently unproven and unmodelled. The handoff's §13 asserts contract compliance against
§5 but never mentions locks, and §5/§9's judgment-call sections do not record the divergence.

*Violated authority.* plan 4 §5 task 4; master plan §9 rule 4; implementer prompt §1 H6 and N-R1;
charter rule 14 (an unimplemented quoted correction is declared, with its reason, in its own
section).

*Correction.* Add a shared helper to both test files that, before each call, issues
`SELECT … FOR UPDATE` on the task (for the `remove_assignment` rows), then the
`stock_report_items` row, then the `stock_task_assignment`, inside the same `db_session`
transaction, and use it in every scenario. If the implementer judges any part unimplementable,
charter rule 14 requires it to say which and why rather than omit it silently. This is fixture
fidelity, not an implementation-coupled assertion: it adds no assertion about internals, it runs
the production path under production's locking conditions (charter rule 3's spirit) and it is the
only place phases 8–13 will find the caller contract written down.

### S3 (should-fix, routed to a plan fold) — MC-19's priority payload has no criterion

*What is wrong.* Intention §9D MC-19 specifies the `stock_report_item:updated` payload's
`priority` as `"high"|"medium"|"low"|null`. `_events.py:23` implements it correctly
(`priority.value if priority is not None else None`), and nothing exercises it: no phase-4 or
phase-5 fixture sets a non-null `priority`, and `dispatch` is never reached in these tests. A
one-line safeguard against a ratified contract is shipping unwatched.

*Violated authority.* intention §9D MC-19 (payload block); charter rule 11 (a safeguard's criterion
names the mutation that must turn its test red); charter rule 16 (coverage is purchased against the
ledger — this contract is served by no row in the batch).

*Correction.* Coordinator folds one row into plan 4 (natural home: alongside C1(d) or C1(s), whose
tests already assert the full `:updated` payload). Fixture sets `priority = HIGH` **and**
`priority_order = 1` on R — both, or `consistency.py`'s `priority_order_nullness` check makes the
row's clean assertion fail for an unrelated reason. Outcome: the payload's `priority` is the string
`"high"`. Named mutation: emit `values["priority"]` unchanged → the payload carries the enum member
→ red. See owner card 1.

### S4 (should-fix) — the mutation ledger's arithmetic does not close in either phase

*What is wrong.* Both phases assert `executed == declared` on numbers that cannot be derived from
their own artifacts: phase 4's summand string sums to 31 against a claimed 33, its table supports
30 distinct runs, and two executed plan mutations (C1(d)/(e), C7(c)) are missing from the summands;
phase 5's prose enumerates 13 groupings against a claimed 15, and its table holds 13 distinct
mutations across 14 runs. The identity the charter cares about is very probably true in substance —
I re-ran four mutations and all four behaved as predicted — but as written the claim is a typed
number, not a computed one.

*Violated authority.* charter phase manifest properties 3 (every count is derived, never typed) and
4 (the declared mutation set is closed); master plan §9 rule 8.

*Correction.* Re-derive both counts mechanically from the plan cells and the ledger table, publish
the derivation (which plan cell → which table row), and state the C3 collapse explicitly as "22
declared cells → 4 guard mutations + 1 combined proof, with the mapping". If a number disagrees with
the table, the table wins.

## 7. Backlog notes (no fix round required)

- **N1 — `_uncredit`'s 1-row branch has no guard.** Measured inert at batch scope (probe D). One
  extra scenario closes it; see §4.2 for the exact fixture. Owner card 2.
- **N2 — plan 4 C1(u)'s "equivalent mutant" is not equivalent.** Measured (probe C): reddens
  `test_c1_u` and `test_c1_q`. Correct the cell at the next fold; do not re-run anything.
- **N3 — plan 4 C6(c)'s named mutation does not reach its own sub-check** (charter rule 12).
  The better instrument, measured: drop `updated_at=Task.updated_at` from `set_task_stock_flag`'s
  `.values()` → reddens exactly `test_c6_c`. Worth replacing the cell text, because phase 13
  re-uses this mutation. The implementer's own note about the stale-identity-map mechanism is a
  genuinely useful finding and should survive into the plan.
- **N4 — MC-1 literal write order, credit memory.** §5A MC-1 places the assignment's *credit memory
  change* in the own-columns write, before the counter statement. The implementation writes it
  inside `apply_goal_effect`, after the counter statement (`_goal_credit.py:56-57`). No observable
  difference: `recompute_row_counters` reads `state`/`is_deleted`/`quantity` only, and the un-credit
  direction does clear-and-flush before its own statement, which is the ordering MC-5 actually
  depends on. Recorded because it is an undeclared deviation from a cited contract sentence.
- **N5 — dead condition.** `apply_goal_effect`'s `if from_state != AWAITING` (`:123`) can never be
  false: `move_assignment` short-circuits `state == target` before calling, and MC-1 forbids
  `awaiting → resolved_early`. Harmless, and it is load-bearing under one of the ledger's own
  mutations, so leaving it is defensible — but it reads as a guard and is not one.
- **N6 — carry to phase 8.** `move_assignment` can emit a `stock_report_item:updated` whose payload
  equals the pre-move snapshot: C5(c) is exactly that case (deltas non-zero, self-heal restores the
  counters to their prior values). MC-19's net-change rule is enforced by
  `coalesce_stock_report_events`, which must therefore compare values against `initial_row_values`
  rather than dedupe by entity. Phase 8 should carry a row for it.
- **N7 — N-S3's tenancy guard has no test.** `set_task_stock_flag` now carries
  `Task.workspace_id == workspace_id`; nothing exercises the cross-workspace case. The implementer
  declared it as a candidate criterion (handoff §12) and verified it ad hoc. Recommend folding it
  as a standing row wherever the next tenancy-shaped phase lands, not into this fix round.
- **N8 — handoff counts.** §3 says `test_move_assignment.py` has "63 cases" and "58 passed";
  §7 says `test_remove_assignment.py` has "7 cases" and "5 passed". Measured by collection: **59**,
  **4**, and `test_goal_credit.py` **22** — total 85, which is the number the L4 delta relies on.
  Same family as S4.
- **N9 — plan 5's Review log names "C1(r)" as a declared mirror.** Plan 5's rows end at C1(q).
- **N10 — `_credit_current_goal(session, assignment, now)` never uses `now`.**
- **N11 — no phase-4 row pins MC-17's "creation: `updated_*` NULL".** The implementation is correct
  (the creation branch writes only `state`); the plan simply does not ask. Phase 8 owns assignment
  creation and should carry it.

### Carry-forward dispositions

| Item | Destination | Why there |
|---|---|---|
| N1 | plan 5 C2(c), this fix round (card 2) or batch C fold | the row exists; only its fixture needs a second scenario |
| N2, N3 | next plan fold (before batch C) | mutation-cell corrections; N3 also feeds plan 13's copy of the same mutation |
| N4, N5, N10 | plan 5 Review log, no action | recorded deviations with no observable effect |
| N6, N11 | plan 8 | `coalesce_stock_report_events` and assignment creation are phase 8's |
| N7 | next tenancy-shaped phase (10 or 13) | needs a cross-workspace fixture the stock-report kit does not yet build |
| N8, N9 | batch B1 fix handoff | documentation corrections, folded with S4 |

## 8. The three §6.5 amendments (final signatures, for the master plan)

Transcribed from the shipped code at `1351b5f`; the orchestrator writes these into §6.5.

**1. `_repair_records.py` — B2, `write_repair_record` gains `delta`.** Replace the registry row's
signature with:

```
write_repair_record(session, *, workspace_id, target_kind, target_client_id, field,
                    stored_value, recomputed_value, trigger, created_by_id, now,
                    delta=None) -> StockReportRepairRecord
```

`delta` is keyword-only, defaults to `None`, and is passed into the existing `logger.warning`'s
`delta=%s` slot (the warning's field list in the current row is already correct; it was
unreachable before this amendment). Phase 3's three call sites omit it and are behaviourally
unchanged.

**2. `_task_flag.py` — N-S3, `set_task_stock_flag` gains the tenancy predicate.** Replace the
registry row's signature **and delete its standing note.** New text:

```
set_task_stock_flag(session, workspace_id, task_id, value, *, require_update=False) -> None
```

— the MC-15 Core UPDATE with `updated_at = tasks.updated_at`, `Task.is_stock_assignment
.is_distinct_from(value)`, **and `Task.workspace_id == workspace_id`** in the `WHERE`.
`recompute_task_stock_flag(session, workspace_id, task_id) -> bool` is unchanged.
**The sentence "Note `set_task_stock_flag`'s UPDATE still has no workspace predicate … phase 4
decides it (re-review 2 N-S3)" is now spent and must be removed** — phase 4 decided it by adding
the predicate, which closes the write half of the boundary card 1 closed on the read half. Two call
sites were updated, not the one the routing note named: `_task_flag.py::recompute_task_stock_flag`
and `repair_stock_report.py`'s direct call (`ctx.workspace_id` threaded in). The guard itself is
untested — note N7.

**3. `_events.py` — H12, the builders construct `WorkspaceEvent` directly.** Signatures are
unchanged from the registry; append to the row:

> Both builders construct `WorkspaceEvent(event_name=…, client_id=…, workspace_id=…, extra=…)`
> directly rather than calling `build_workspace_event`, which requires an object carrying
> `.client_id` while these builders are registered with a bare `client_id: str` (the moving
> row's / assignment's id, not an entity). No shim object was introduced.
> `build_stock_report_item_updated_event` emits `priority.value` (or `None`), never the enum
> member, per MC-19's payload spec — see finding S3.

## 9. What I ran, and the mutation-probe declaration

**Consumed by citation, not re-run** (tree identity matches mine exactly): the orchestrator's L4 on
`1351b5f` — 21 failed / 3349 passed / 2 skipped, failure IDs identical to the published 21-ID
baseline in both directions, 3349 = 3264 + 85. Re-running it would itself be a finding against this
round (charter: over-evidence is a defect, symmetrically).

**Runs taken (all on `1351b5f`, `git status --porcelain` empty at start):**

| Hypothesis | Scope | Command | Result |
|---|---|---|---|
| The batch is green on my tree before any probe | L1 ×3 files | `PYTHONPATH=. pytest tests/integration/services/commands/stock_report/{test_move_assignment,test_remove_assignment,test_goal_credit}.py` | 85 passed |
| Collection counts as claimed | collect-only | same files, `--collect-only -q` | 59 / 4 / 22 = 85 (handoff says 63 / 7 / 22 — note N8) |
| Probe A — C3's four double-guarded rows can fail | L1 | `pytest test_move_assignment.py` | 18 failed / 41 passed; ids as in §3 |
| Probe B — C6(c)'s timestamp sub-check can fail | L1 | `pytest test_remove_assignment.py` | 1 failed (`test_c6_c`) / 3 passed |
| Probe C — is C1(u)'s declared-equivalent mutant equivalent? | L1 ×2 | `pytest test_move_assignment.py test_goal_credit.py` | 2 failed (`test_c1_u`, `test_c1_q`) / 79 passed — **not equivalent** |
| Probe D — is C2(c)'s named mutation inert at its named site, at batch scope? | L2 | `pytest tests/integration/services/commands/stock_report/ tests/integration/services/queries/stock_report/` | 118 passed — **inert** |
| Probe E — is C4(c) armed and specific? | L2 | `pytest tests/integration/services/commands/stock_report/` | 1 failed (`test_c4_c`) / 101 passed |

No L3 or L4 run. No test file was executed with `-k`.

### Mutation-probe declaration

Every probe was applied to the working tree, run, and reverted with
`git checkout -- <path>`. **Files touched by my probes (all reverted, all verified
byte-identical against a SHA-256 baseline taken before the first probe):**

- `app/beyo_manager/services/commands/stock_report/_move_assignment.py` (probes A, C, E)
  — `50ef15cc9c7ad0c8688d3d949bb23291ef827412d4b9a8f3bf177a7189285b58`
- `app/beyo_manager/services/commands/stock_report/_task_flag.py` (probe B)
  — `fc9c5131e0866a3ea2937aa7ef54fd649369550a15c0625eecc9dc556e71bfe9`
- `app/beyo_manager/services/commands/stock_report/_goal_credit.py` (probe D)
  — `ed86fc35934372d75964ca2ee610b04a8bc0027df485c99631686a2b250c0ede`

Untouched by any probe and checksum-confirmed unchanged: `_events.py`, `_remove_assignment.py`,
`consistency.py`, every test file, every document except the two Review logs and this handoff.

**Database and state side effects: none persisted.** The `db_session` fixture (`tests/conftest.py:107`)
rolls back after every test, and no test in either phase commits, so charter rule 11½'s purge
obligation does not arise and no workspace survives a run. Each test seeds its own workspace through
`seed_stock_report_workspace` with a fresh `uuid4` suffix, and every assertion is scoped to it — no
global count, no cross-workspace total (master plan §9 rule 1 satisfied).

`git status --porcelain` is empty at the time of writing except for this handoff and the two
Review-log appends. No commit was made, no graph write, no master-plan edit, no source or test file
modified.

## 10. Other batch-level checks (verified correct)

- **Perimeter.** `git diff aa849cc..1351b5f -- app/` is exactly the ten files the prompt lists,
  +2426/−4. No escape. `consistency.py` — probed by both the implementer and me — is absent from
  the diff, so both sets of probes were reverted.
- **Cross-phase integration.** `apply_goal_effect` is called at `_move_assignment.py:231`, after
  `_apply_counter_delta` and before the event build — exactly plan 5 §4's placement and MC-1's
  write order. Every phase-4 row still holds with it present (the 85-test run is on the tree that
  includes it). `test_c3_a_worked_sequence` drives creation → sync → Scanner resolve →
  `remove_assignment` in one transaction and is the batch's integration proof.
- **N-R3 discharge — all three helpers genuinely reached, not merely referenced.**
  `recompute_row_counters` is called from `_apply_counter_delta`'s self-heal and executed by
  C5(a), C5(c) and the required-ledger row's `−2q` run; `recompute_task_stock_flag` from
  `remove_assignment` and executed by C6(a)–(c), C5(c) and plan 5 C3(a) step 6;
  `recompute_goal_total` from `_uncredit`'s self-heal and executed by C2(a), C2(b), C2(d). Probe D
  incidentally re-confirmed the third: planting code in that branch changed nothing, which is only
  possible because the *other* branch is the one under test — and C2(a)/(b)/(d) still passed.
- **Workspace isolation (§9 rule 1).** Every test seeds its own workspace; every query and
  assertion is scoped by `workspace_id` or by an explicit `client_id`; no global count anywhere.
  `_repair_records`, `assert_stock_report_clean` and `compute_stock_report_divergences` are all
  workspace-scoped. No test commits, so no purge is owed.
- **Orphan tests: none.** All 85 collected tests map 1:1 (or via a declared parametrized group) to a
  criterion row or to plan 4's required ledger row. `test_required_ledger_row_double_decrement_self_heals`
  duplicates C1(d)'s scenario, which is deliberate — it is the correctness case the `−2q` mutation
  is measured against, and the plan names it.
- **Implementation-coupled tests: none.** The three uses of `record_statements`/`count_writes` are
  MC-9 zero-write bounds (C2) and "no history write" bounds (plan 5 C1(d), C1(k), C1(m), C1(p)),
  which master plan §9 rule 7 reserves for exactly this. No test asserts query text, call counts,
  private helpers or a mocked internal collaborator.
- **The three authorized phase-3 edits** are minimal and correct by reading, and phase 3's suite is
  green on this tree (included in probe D's and E's 118/102 runs).
- **Ruff** on the perimeter: the implementer reports clean; not re-run (no tree difference).

## 11. Tracker

Not written — the prompt reserves the master plan to the orchestrator. The transition this review
supports is **batch B1: REVIEWING → CHANGES_REQUESTED**, 2026-09-21, reviewer (claude-opus-5):
*83/84 rows PASS, no production defect; four should-fix items — one partial row (plan 4 C5(b)), the
unimplemented and undeclared lock modelling (plan 4 §5 task 4 / H6 / N-R1), an uncovered MC-19
payload contract, and a mutation ledger whose arithmetic does not close.*
