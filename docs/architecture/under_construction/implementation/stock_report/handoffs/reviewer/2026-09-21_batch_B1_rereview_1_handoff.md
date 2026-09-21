---
plan: batch B1 (4, 5)
role: review
round: batch_B1-rereview-1
state: APPROVED
date: 2026-09-21
actor: claude-opus-5 (plan-reviewer)
tree: 60d6a12 (code identical at HEAD `a894675`; the intervening commits touch documents only)
---

# Batch B1 re-review 1 — after fix round 1

## 1. Verdict and row totals

**APPROVED.** No blocking finding. No should-fix finding. The one FAIL review 1 recorded is closed,
and the round's one declared gap is closed too — by me, in six seconds, rather than by a third round.

| | PASS | FAIL | NOT_VERIFIED | total |
|---|---|---|---|---|
| Phase 4 (plan_4.md) | 62 | 0 | 0 | 62 |
| Phase 5 (plan_5.md) | 22 | 0 | 0 | 22 |
| **Batch B1** | **84** | **0** | **0** | **84** |

**Delta against review 1 (83/1/0):** plan 4 C5(b) FAIL → PASS (finding S1 closed, all four outcome
clauses asserted, divergence list asserted whole). No other row's verdict moved. Two tests were
added or extended beyond the 84 rows — S3's MC-19 payload guard (folded into `test_c1_s`) and card
2's goal scenario (a new test in `test_goal_credit.py`) — both declared as **candidate criteria** in
their plans' Review logs, neither authored as a criterion row. Row count therefore stays 84; the
collection is 86 (59 / 4 / 23).

The fix round shipped **zero production-code change** (`git diff 1351b5f..60d6a12 -- app/beyo_manager/`
is empty; the three production checksums in review 1 §9 still match byte-for-byte on my tree). Its
commit `60d6a12` touches exactly the five files it declares: the three test files and the two plans.
No perimeter escape.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Do the two new guards become criterion rows, or stay candidates?

**Question.** Promote the two tests this round added to real criterion rows in plans 4 and 5, or
leave them recorded as candidates in the Review logs?

**Story.** Two safeguards now exist and both are proven to bite: one keeps a board row's priority
travelling to the browser as the word "high" instead of an internal Python object (without it, the
board simply never refreshes and only the logs know why), and one keeps Manager from quietly
"correcting" a stock goal that drifted upward, which is the number a human is supposed to see and
investigate. They are tests today, but nothing in the plan says they must exist. The next time
someone tidies a test file, a guard with no row behind it is the one that gets deleted.

**Branches.**
- *Promote both:* the plan set goes 615 → 617 rows; each guard is owed for the life of the project.
- *Leave as candidates:* both guards work today and are recorded, but no plan requires them.

**Recommendation.** Promote both — each discharges a contract you already ratified (the payload
spelling, and "repair only downward"), so the rows record obligations rather than create them.

**On silence.** The gate holds on the promotion only; batch B1 is APPROVED either way and phase 6
is not blocked.

**Kind.** *The intention settles the semantics, not the bookkeeping* — §9D MC-19 and §12A (c) both
already bind; only whether a criterion row is authored is open, and this project reserves that to
the owner.

*Trace:* plan 4 Review log (S3 candidate), plan 5 Review log (card 2 candidate); intention §9D
MC-19, §12A (c); master plan §4A batch B1 row.

---

## 2. The five items

### S1 — plan 4 C5(b) — **CONFIRMED**

The outcome cell is "succeeds; counters `(1, 4, 0)`; **zero** repair records; check reports one
`counter_in_queue` (stored 1, expected 0); `repair_stock_report` then clears it".
`test_c5_b_upward_drift_is_not_self_healed` now asserts all four, read line by line
(`test_move_assignment.py:907-956`): the move returns without raising; counters `(1, 4, 0)`; repair
records `== []`; `compute_stock_report_divergences(...) == [ … ]` **unfiltered** — the filter review
1 objected to is gone, so a second divergence of any kind now fails the row; then the manual leg —
`repair_stock_report(ctx)` with `result["repaired"]` kinds `== ["counter_in_queue"]`, counters back
to `(0, 4, 0)`, exactly one record with `trigger == "manual"` and `created_by_id == manager`. That is
`test_c2_c`'s closing block mirrored, which is what the correction asked for, and it makes the two
halves of §12A (c) symmetric across the two phases.

The row is armed: its own named mutation had never been run by anyone (see §4); I ran it myself and
it reddens exactly this test.

### S2 — the lock modelling — **PARTIAL** (delivered for phase 4, declined for phase 5, and weaker as
an instrument than the finding assumed)

**(a) What landed, verified.** `_hold_caller_locks(db_session, *, row, assignment=None, task=None)`
is present in both phase-4 test files and called at **26 of 26** `move_assignment` call sites in
`test_move_assignment.py` and **4 of 4** `remove_assignment` call sites in
`test_remove_assignment.py` — counted, and each call verified to sit immediately before its
operation. Lock order is task → `stock_report_items` → `stock_task_assignment`, which is master plan
§9 rule 4's order (`… → tasks → stock_report_items → stock_task_assignments → …`) with the classes
this batch does not touch omitted, and it matches the repo's only existing exemplar,
`repair_stock_report.py:173-194`. The task leg is passed only for the `remove_assignment` rows,
which is right: `move_assignment` writes no `tasks` row, and the inverted write order S2 exists for
is `remove_assignment`'s alone.

**(b) What did not land.** `test_goal_credit.py` is untouched by S2: **0 of 26** call sites (25
`move_assignment`, 1 `remove_assignment`) take any lock. The finding's own text named plan 5 ("the
phase-4 **and phase-5** tests"; N-R1: "plan 5's tests hold row + assignment `FOR UPDATE` before
calling"), while its correction sentence said "both test files", which the implementer read as plan
4's two. The divergence is declared plainly in the fix handoff §3 and plan 4's Review log — charter
rule 14 is satisfied. Routed as note **N13**, to a fold, not to a round; the reason is (c).

**(c) The judgment the prompt asked for: it runs, and as a *guard* it proves nothing — measured.**
I violated the modelled contract inside the fixture itself (dropped the task lock, locked the
assignment before the row, i.e. exactly the MC-1 order violation the helper exists to express) and
ran both files: **63 passed**. It cannot fail, and it cannot fail for a structural reason no
repair will change: the test owns one transaction, so there is no second holder to contend with,
and the helper asserts nothing. Re-locking a row your own transaction already holds is a Postgres
no-op.

That is not a reason to remove it, and it is not charter rule 15's defect — a fixture is not a
guard. What it *is* worth, precisely: the caller contract written down in executable form at the
call sites phases 8–13 will copy, plus one weak real property (the command is exercised while the
rows are genuinely locked, which would expose a command that reached for a second connection). It
must never be described, in a plan or a handoff, as proof of H6/N-R1's premise. **The premise is
today unprovable by test in this batch**, because `move_assignment`/`remove_assignment` have no
production caller at all — `grep` over `beyo_manager/` returns none outside their own module. The
premise becomes checkable in **phase 8**, where the first caller is written; that is where the
obligation belongs, and it should be stated there as a criterion on the caller, not re-litigated
as a fixture in this batch.

**(d) New and load-bearing for phases 8–13: the helper models the caller's lock *order*, not the
caller's lock *call*, and the difference disarms C4(c).** Production callers will lock through
`_locks.py`, whose `_lock` is a **full-entity** `SELECT … FOR UPDATE … execution_options(populate_existing=True)`.
I substituted those real helpers into the fixture (`lock_tasks` / `lock_stock_report_items` /
`lock_stock_task_assignments`) and measured:

| Fixture | Batch result | C4(c)'s named mutation (payload built from the identity-mapped ORM) |
|---|---|---|
| shipped, column-only | 63 passed | **1 failed / 58 passed — exactly `test_c4_c`** |
| production `_locks.py` helpers | 63 passed | **59 passed — inert** |

`populate_existing` refreshes R in the identity map, which destroys the staleness C4(c) is built to
observe. So "model the caller faithfully" and "keep C4(c) armed" are in genuine tension, and the
implementer resolved it in the direction that keeps the row armed and documented why in the
docstring. **That is the right call** — but phase 8 must carry it: a C4(c)-shaped staleness row
written under a caller that locks with `populate_existing` is decoration. Note **N14**.

### S3 / card 1 — the priority payload guard — **CONFIRMED**, all three checks

1. *Fixture sets both fields.* `_make_row` gained `priority`/`priority_order` (both defaulting to
   `None`, so the other 58 cases are untouched); `test_c1_s` passes `StockReportPriorityEnum.HIGH`
   and `priority_order=1`. Both, as the correction's caveat required — `consistency.py:166-183`'s
   `priority_order_nullness` would otherwise fail the row's `assert_stock_report_clean` for an
   unrelated reason. The row still ends clean, so the check is satisfied, which is the proof the
   caveat was honoured.
2. *The payload asserts the string.* `_assert_row_event` compares `event.extra` as a **whole dict**
   and now carries `priority`/`priority_order` keys, so `priority="high"` is a real assertion, not
   an ignored kwarg.
3. *The mutation reddens it.* I ran it (`_events.py`, definition site: `"priority": priority.value
   if priority is not None else None` → `"priority": priority`): **1 failed / 58 passed, exactly
   `test_c1_s_in_queue_to_resolved_early`.** The mutant is observable because
   `StockReportPriorityEnum` is a plain `enum.Enum`, not a `str` mixin — had it been a `str` enum,
   `HIGH == "high"` would have made this an equivalent mutant and the guard decoration. It is not.

The row's clean assertion still holds for the right reason: the fixture supplies a *consistent*
priority pair, so nothing about the drift semantics changed.

### Card 2 — the goal self-heal scenario — **CONFIRMED**, and it closes N1

`test_c2_c_second_upward_drift_survives_a_subtracting_move` implements review 1 §4.2's fixture
exactly: A `awaiting` `q=4` with `mem = G`, raw `G = 9` (upward drift that still clears the guard,
`9 − 4 ≥ 0`), `MV(awaiting → in_queue)`; asserts `G == 5`, zero repair records, one `goal_total`
divergence (stored 5, expected 0). This is the first scenario in the project that reaches
`_uncredit`'s guarded-subtraction **1-row** branch.

I ran the mutation at the cell's literal site — the one review 1's probe D measured **inert** —
writing my own mutant text rather than reusing the implementer's: unconditional self-heal after the
subtraction returns 1 row. **1 failed / 22 passed, exactly the new test**, and
`test_c2_c_upward_drift_is_not_self_healed_by_a_move` stayed green. So the new scenario, and only
the new scenario, arms the literal site. N1 is discharged, and C2(c)'s existing clauses are
undisturbed — the new test is additive, shares no fixture, and the old test still passes in the same
run.

One presentational point, not a defect: the new test filters the divergence list to `kind ==
"goal_total"` — the same shape S1 just removed from C5(b). I measured whether the filter hides
anything: asserting the list **whole** in that scenario also passes (23 passed). So when the
candidate criterion is folded, the row can and should say "the check reports exactly one
divergence" and the assertion can drop the filter at zero cost. Note **N15**.

### S4 — the ledger — **CONFIRMED, and now closed**

The re-derivation is honest, mechanical, and finds more than review 1 did. See §4 for the audit,
§3 for the gap ruling.

## 3. Ruling on the C5(c) gap

**It does not block — and it is no longer a gap: I ran it.**

`_move_assignment.py`, definition site, C5(c)'s named mutation ("issue the soft-delete after the
counter statement"): I deferred the DELETE branch's own-columns write until after
`_apply_counter_delta`, and ran all three batch files. **1 failed / 85 passed — exactly
`test_c5_c_delete_write_order_self_heals_with_one_repair_record`.** Reverted; `_move_assignment.py`
checksum-confirmed byte-identical.

**Why it would not have blocked even unrun.** The declaration met every condition the charter asks
of a divergence: named cell, named site, a stated reason (the probe is a control-flow edit, not a
value swap, in a round whose own stated risk was breaking one of 83 armed rows while tidying),
declared in the handoff's own section and in the plan's Review log, and routed as note N12. The
production code is unchanged and read-verified (review 1 §4.5), and the row's fixture is
discriminating by construction — it plants drift that only a correctly-ordered write can resolve to
zero. One named, reasoned, declared, single-cell gap against that background is a carry-forward, not
a blocker.

**But "does not block" is not "acceptable", and the right answer was not a fold.** A declared gap
still has to be closed by somebody, and the cheapest somebody was me: mutation-probing tests is the
reviewer's own instrument, the edit took three minutes and the run six seconds — against a fold that
would have carried the gap across four more phases, or a third round costing a full session.
**Lesson L-1 (below): a mutation an implementer declines on caution grounds should be routed to the
reviewer in the same round, explicitly, rather than deferred to a fold.** The caution was sound; the
routing was the missed move.

## 4. The ledger re-derivation audit

**The mapping holds.** I checked every row of the new criterion → table-row map against the
implement-1 handoff's 31-row ledger table, and re-derived the declared set independently from plan
4's own mutation cells (`plan_4.md:120-176`) rather than from the fix handoff's prose. Both
derivations land on the same place:

- Table rows 1–31 with row 13 explicitly "not a run" → **30 distinct executed texts**, as claimed.
- Row 4 = C1(d)/(e); row 8 = C1(g)(iii), whose observed-red set includes `test_c7_c`; row 10 =
  C1(q)/(r), whose observed-red set includes `c1u(i)`. Both sharings the map asserts are visible in
  the original table's own observed-red columns. ✔
- **C3 collapse — confirmed against the table.** Rows 18, 19, 20, 21 are the four guard removals and
  row 22 is the combined proof: "22 declared cells → 4 guard mutations + 1 combined proof" is exactly
  what the table shows. The cell attribution also closes: 4 (`c3a,b,c,n`) + 2 (`c3d,e`) + 11
  (`c3f,g,h,i,j,k,l,p,q,r,t`) + 1 (`c3o`) = 18 single-guarded, plus the four double-guarded
  (`c3m,s,u,v`) that only the combined mutant reaches = **22**. ✔
- **The declared column sums to 35 cells, not 34.** The difference is exactly C1(u)(i), which the map
  itself flags as sharing row 10's text. So: 35 declared *cells*, 34 declared *distinct texts*, 33
  executed before my probes. The stated "declared 34" is correct as distinct texts; the column header
  reads "Declared mutations", which invites the wrong sum. Cosmetic — note **N16** — but it is the
  same family the round exists to fix, so the fold should say "distinct mutation texts".

**One substantive correction to the derivation, measured.** The map records **C7(c) = 0 additional,
shares row 8 (same code edit)**. It is not the same edit. Row 8 *replaces* the delete stamps with
`updated_*`; plan 4 C7(c)'s cell says *"stamp `updated_*` on delete"*, which read literally is
**additive** — keep `deleted_*`, also write `updated_*`. That matters under charter rule 12:
`test_c7_c` asserts `deleted_by_id`, then `deleted_at`, then `updated_by_id still X`, so row 8's
replace-form mutant trips the **first** assertion and the row's distinguishing third sub-check never
executes. I ran the additive mutant, which nobody had: **1 failed / 62 passed, exactly
`test_c7_c`**, and the assertion that bites is the third one. So C7(c) is genuinely armed — the
conclusion survives, the reasoning did not. Counting C7(c)'s text as distinct: declared 35 texts,
executed 35 (33 by the round, C5(c) and C7(c)-additive by me). **The phase-4 ledger closes under
either reading.** Note **N17** for the cell-text correction.

**Spot-checks of the four mutations re-run this round.** Two of the four (C1(u)(iii), C6(c)) were
already measured by review 1's probes C and B on a tree whose production files are byte-identical to
mine, so re-running them would be reproduction and a finding against this round; I consumed them by
citation and spent the budget on the two that **no one had ever run** — the newly-discovered C5(a)
and C5(b) gaps — writing my own mutant text in both cases:

| Spot-check | Site | Observed | Implementer's claim | Match |
|---|---|---|---|---|
| **C5(a)** — drop all three `>= 0` guards from `_apply_counter_delta`'s `WHERE` | `_move_assignment.py`, def site | **1 failed / 58 passed**, exactly `test_c5_a_…`, via `CheckViolationError` on `ck_stock_report_items_quantity_in_queue_nonneg` | 1 failed / 58 passed, same id, same mechanism | ✔ exact |
| **C5(b)** — unconditional self-heal after the guarded UPDATE returns 1 row | `_apply_counter_delta`, def site | **1 failed / 58 passed**, exactly `test_c5_b_…`, on the "zero repair records" clause | 1 failed / 58 passed, same id | ✔ exact |

One qualification on C5(a), for the record rather than as a finding: its mutant reddens the row by
raising a database error, not by failing an assertion, so it proves the guard exists without proving
which of the row's six record-field assertions are live. The plan's own cell predicts exactly that
("→ DB check aborts"), so it is the declared instrument, not a substitution.

**Phase 5.** Re-checked: 22 rows against a 14-run table holding 13 distinct texts (rows 12/13 the
same mutation re-sited), the two sharings (C1(j)/C1(k) → row 6, C1(l)/C1(q) → row 7) verified
against the table's own observed-red sets. `declared == executed == 13` holds. With card 2's new
mutation — run by the implementer and independently by me — it becomes 14/14 if the candidate
criterion is folded.

## 5. Rows pulled in under the widening

The lock fixture now runs in every scenario of two files, so I pulled in the rows whose instruments
an extra `SELECT … FOR UPDATE` could plausibly disturb. **None was perturbed.**

| Row | Why pulled in | Result |
|---|---|---|
| **C4(c)** (stale ORM payload) | the fixture could repopulate the identity map the row needs stale | **still armed** — its mutation reddens exactly `test_c4_c` (1 failed / 58) under the shipped fixture. Column-only `select(Model.client_id)` returns a scalar, never an entity, so nothing enters the identity map. Measured, not reasoned |
| **C7(d)** (R's stamps unchanged) | raw-SQL-seeded stamps, asserted byte-identical after | **still armed** — ledger row 30's mutation (`updated_at=now` on the counter UPDATE) reddens exactly `test_c7_d` (1 failed / 58) with the fixture in place |
| **C6(c)** (task stamps unchanged) | the fixture adds a task `FOR UPDATE` right after the raw-SQL stamps | **still armed** — the round's own corrected-instrument run on this tree (1 failed / 3, exactly `test_c6_c`) is tree-matched to mine and consumed by citation |
| **C2(a)–(f)** (`count_writes == 0`) | an extra statement could enter the counted window | **structurally clear** — the helper is called at line 691, the `async with record_statements(...)` window opens at 692, so the SELECTs are outside it; and they are reads, which `count_writes` does not count. No run needed |
| **C1(q)/(r)/(u)** (`len(events) == 1`) | event-list bounds | **structurally clear** — the helper emits no events and touches no delta |

Corroborating: across my eight probe runs, every run that was not targeting a specific row reported
the full complement green (63 / 59 / 23 / 85+1), so no silent drift hid behind a red.

## 6. Findings

**Blocking: none. Should-fix: none.**

All four of review 1's should-fix findings are discharged: S1 completed, S2 delivered for phase 4
and declared for phase 5 (see N13), S3 implemented and armed, S4 re-derived and — with my two
probes — closed.

### Backlog notes

- **N12 (review 1's round) — CLOSED.** C5(c)'s named mutation ran: 1 failed / 85 passed, exactly
  `test_c5_c_…`. Record the run in plan 4's ledger; no further work.
- **N13 — plan 5's tests model no caller locks.** 26 call sites in `test_goal_credit.py`, zero locks;
  declared under charter rule 14. Destination: a fold before batch C, *or* a recorded refusal — see
  N14 before deciding, because the value of adding it is documentary, not evidential.
- **N14 — the fixture models the lock order, not the lock call, and the difference disarms C4(c)**
  (measured, §2 S2(d)). Destination: **plan 8**. Phase 8 writes the first real caller; its plan must
  (a) carry the criterion that proves H6/N-R1's premise on the caller (the task lock precedes the
  row lock), which is the only place that premise can be proven, and (b) not write a C4(c)-shaped
  staleness row under a caller that locks with `populate_existing`, because the mutant is inert
  there.
- **N15 — card 2's divergence assertion filters by kind.** Measured: the whole-list assertion also
  passes. Destination: the fold that authors the candidate criterion (card 1) — state "exactly one
  divergence" and drop the filter.
- **N16 — the re-derivation's "Declared" column sums to 35 cells against a stated 34.** The gap is
  exactly C1(u)(i)'s shared text. Destination: the same fold; relabel the column "distinct mutation
  texts".
- **N17 — plan 4 C7(c)'s mutation cell.** "Stamp `updated_*` on delete" is an *additive* edit, not
  row 8's replace-form; the replace-form short-circuits on the row's first assertion (charter rule
  12). My additive run reddens exactly `test_c7_c` on the third assertion. Destination: next plan
  fold — record the additive text and its observed red as C7(c)'s own ledger row.
- **N18 — the fix handoff could not reproduce the implement round's "222 passed" L2 figure** and
  reported its own derivable 120 instead (master-plan §10 scope). Correct behaviour; the stale number
  lives in the implement-1 handoff and should not be cited again. Destination: no action.
- Review 1's **N2–N11** are unchanged by this round except N2 and N3, whose cell corrections the
  coordinator has already folded into plan 4 (verified in the cell text at `plan_4.md:143,172`), and
  N8/N9, which the fix round corrected with measured counts.

### Carry-forward dispositions

| Item | Destination | Why there |
|---|---|---|
| N13 | fold before batch C, or recorded refusal | scope question, no evidential loss either way |
| N14 | **plan 8** | the caller that makes the premise provable is written there |
| N15, N16 | the fold that authors the two candidate criteria (card 1) | both are edits to text that fold will touch anyway |
| N17 | next plan fold | mutation-cell correction; phase 13 reuses delete-stamp semantics |
| N4, N5, N6, N7, N10, N11 (review 1) | unchanged from review 1's table | nothing this round touched them |

## 7. What I ran, and the mutation-probe declaration

**Consumed by citation, not re-run** (tree identity matches mine — production and test files are
byte-identical between `60d6a12` and my working tree at `a894675`, which differs only in documents):
the round's L1 stamps (59 / 4 / 23), its C1(u)(iii) and C6(c) re-runs, review 1's probes A–E, and the
orchestrator's L4 (22 failed / 3349 passed / 2 skipped, the 22nd root-caused as the UTC-midnight
analytics drifter). **No L4 run was taken; the clean post-03:00 stamp is the orchestrator's
obligation, as its prompt states.** Re-running any of the above would itself be a finding against
this round.

**Runs taken — all variation, all on the tree above, `git status --porcelain` empty before and
after each:**

| # | Hypothesis | Site | Scope | Observed |
|---|---|---|---|---|
| P1 | S3's guard is armed | `_events.py::build_stock_report_item_updated_event` (def) | L1 move | **1 failed / 58** — exactly `test_c1_s` |
| P2 | C5(a)'s never-run mutation bites (spot-check 1) | `_move_assignment.py::_apply_counter_delta` WHERE (def) | L1 move | **1 failed / 58** — exactly `test_c5_a` |
| P3 | C5(b)'s never-run mutation bites (spot-check 2) | `_apply_counter_delta`, 1-row branch (def) | L1 move | **1 failed / 58** — exactly `test_c5_b` |
| P4 | C7(c)'s *literal, additive* mutation reaches its third sub-check | `move_assignment`, DELETE branch (def) | L1 move + remove | **1 failed / 62** — exactly `test_c7_c` |
| P5 | card 2's new test is armed at the literal site | `_goal_credit.py::_uncredit`, 1-row branch (def) | L1 goal_credit | **1 failed / 22** — exactly the new test; old `c2c` green |
| P6 | **C5(c)'s declared-unrun mutation bites** | `move_assignment`, soft-delete deferred past the counter statement (def) | L1 ×3 files | **1 failed / 85** — exactly `test_c5_c` |
| P7 | can the lock fixture observe a lock-order defect? | the fixture itself, both phase-4 files | L1 move + remove | **63 passed** — contract violated, nothing red |
| P8 | does the *production* lock call model the caller as well? | fixture → `_locks.py` helpers, both files | L1 move + remove | **63 passed** |
| P9 | …and does C4(c) survive it? | P8 + C4(c)'s mutation | L1 move | **59 passed — inert** |
| P10 | control for P9 under the shipped fixture | C4(c)'s mutation alone | L1 move | **1 failed / 58** — exactly `test_c4_c` |
| P11 | C7(d) still armed with the fixture in place (widening) | `_apply_counter_delta` `.values()` (def) | L1 move | **1 failed / 58** — exactly `test_c7_d` |
| P12 | would card 2's divergence assertion hold unfiltered? | the test itself | L1 goal_credit | **23 passed** — the filter hides nothing today |

No L2, L3 or L4 run. No file executed with `-k`. Every mutant text was written by me, not copied
from the round's handoff, so each is an independent shape for the same hypothesis.

### Mutation-probe declaration

Every probe was applied to the working tree, run, and reverted with `git checkout -- <path>`.
**Files touched by my probes, all reverted, all verified byte-identical against a SHA-256 baseline
taken before the first probe:**

- `app/beyo_manager/services/commands/stock_report/_move_assignment.py` (P2, P3, P4, P6, P9, P10, P11)
  — `50ef15cc9c7ad0c8688d3d949bb23291ef827412d4b9a8f3bf177a7189285b58`
- `app/beyo_manager/services/commands/stock_report/_events.py` (P1)
  — `732f6e9ffe8e9e36540479bc830b9f4a51809a768967acd8309c9a02ab05a89b`
- `app/beyo_manager/services/commands/stock_report/_goal_credit.py` (P5)
  — `ed86fc35934372d75964ca2ee610b04a8bc0027df485c99631686a2b250c0ede`
- `app/tests/integration/services/commands/stock_report/test_move_assignment.py` (P7, P8)
  — `04254f9a7a3d6505b4affe2ce75665721043013290edfe65d860b66d1b3665c9`
- `app/tests/integration/services/commands/stock_report/test_remove_assignment.py` (P7, P8)
  — `62075116104458f9429e7a19e50d379fd41ba14ef9d05af2b93bcd67e1d5e1bc`
- `app/tests/integration/services/commands/stock_report/test_goal_credit.py` (P12)
  — `fabe2ffe627b8861c59691adf943899dfbe227fe6f2fa9b025699ffc1c1014b4`

`_task_flag.py`, `_remove_assignment.py`, `_repair_records.py`, `repair_stock_report.py`,
`consistency.py` and `_locks.py` were **not** touched by any probe. The first three production
checksums match review 1's declaration exactly, which independently confirms that round's probes
were fully reverted too.

**Database and state side effects: none persisted.** No test in the batch commits; `db_session`
rolls back after each, every scenario seeds its own `uuid4`-suffixed workspace, and no assertion is
a global count (master plan §9 rule 1, charter rule 11½ not engaged).

**Write perimeter of this session:** this handoff file, and one appended Review-log entry in each of
`plans/plan_4.md` and `plans/plan_5.md`. No commit, no graph write, no master-plan edit, no source or
test file left modified, no tracker row.

## 8. Tracker

Not written — reserved to the orchestrator. The transition this review supports is
**batch B1: REVIEWING → APPROVED**, 2026-09-21, reviewer (claude-opus-5): *84/84 rows PASS, zero
blocking and zero should-fix findings; S1 completed, S3 and card 2 armed and independently measured,
the phase-4 mutation ledger closed by the reviewer running C5(c) and the isolating C7(c) mutant; S2
delivered for phase 4 and declared for phase 5, with the measured caveat that the lock fixture is
executable documentation, not a guard, and that the premise it stands for becomes provable only in
phase 8.*

## 9. Lessons for the plans

- **L-1 — route a declined mutation to the reviewer in the same round, not to a fold.** A caution
  -first fix round was right to refuse a control-flow probe; it was wrong to let the gap travel. The
  reviewer already owns mutation probing, runs on the same tree, and cannot break production because
  it ships nothing. "Declared and deferred" cost four phases of exposure here; "declared and routed"
  would have cost six seconds. Worth a line in the coordinator's fix-prompt template.
- **L-2 — "same code edit" is a claim to be measured, not asserted.** Two ledger rows shared a slot
  on a similarity that did not survive reading (C7(c) vs C1(g)(iii)), and the sharing hid a
  short-circuited sub-check. When a re-derivation collapses two cells into one run, the collapse
  needs the rule-12 check — does the shared mutant reach the *second* row's distinguishing assertion?
- **L-3 — a fixture that models an environment cannot fail, and plans should say so.** Naming the
  lock order in a test buys documentation and one weak property, not proof. Plan 8 should write the
  premise as a criterion on the caller instead of inheriting the fixture as if it were evidence.
- **L-4 — the strongest evidence this round produced was a *pair*.** C4(c) armed under one plausible
  fixture and inert under another equally plausible one; neither run alone says anything. Where a
  plan has a choice of fixture, the criterion should name which choice keeps the row armed.
