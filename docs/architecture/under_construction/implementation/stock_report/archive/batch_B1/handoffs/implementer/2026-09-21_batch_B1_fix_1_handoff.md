---
plan: batch B1 (4, 5)
role: implement
round: batch_B1-fix-1
state: DONE
date: 2026-09-21
actor: claude-sonnet-5
tree: 60d6a12 (clean)
---

# Batch B1 fix round 1 — handoff

## 1. Gate check record

| Line | Check | Result |
|---|---|---|
| 1 | `SR/planning/intention.md` begins `status: RATIFIED` | PASS |
| 2 | `SR/master_plan.md` §4A shows batch B1 `FIX_PROMPT_READY` | PASS (row: "B1 \| 4, 5 \| FIX_PROMPT_READY \| 2026-09-21 \| orchestrator \| fix round 1, prompt `prompts/implementer/2026-09-21_batch_B1_fix_1.md`...") |
| 3 | `git status --porcelain` empty at start | PASS |
| 4 | `1351b5f` is an ancestor of HEAD | PASS (`d6b0603` at start; `1351b5f` → `b89d568` → `b9fa121` → `d6b0603`) |

Gate passed; proceeded.

## 2. S1 — plan 4 C5(b)

**Changed:** `test_c5_b_upward_drift_is_not_self_healed` (`test_move_assignment.py`). Was: asserted
counters, zero repair records, and the divergence list *filtered* to `kind == "counter_in_queue"`.
Now: asserts the divergence list **whole** (no filter — a second, unrelated divergence would no
longer pass unnoticed), then adds the fourth clause — `repair_stock_report(ctx)` — mirroring
`test_c2_c`'s closing block: `[e["kind"] for e in result["repaired"]] == ["counter_in_queue"]`,
counters back to `(0, 4, 0)`, exactly one repair record with `trigger == "manual"` and
`created_by_id == seeded.manager.client_id`.

**Discharges:** plan 4 C5(b) in full (all four outcome clauses), exact shape.

**Mutation:** none newly required by S1 itself (the row's own named mutation — "run the self-heal
block unconditionally" — is S4's C5(b) gap, closed separately below, since the original ledger had
no table row for it at all).

## 3. S2 — lock fixture

**Changed:** added `_hold_caller_locks(db_session, *, row, assignment=None, task=None)` to both
`test_move_assignment.py` and `test_remove_assignment.py` (written once per file, not hoisted into
the shared test kit — see judgment call below). Column-only `SELECT … FOR UPDATE`: task first (only
passed for `remove_assignment` rows), then the row, then the assignment (skipped when the
assignment does not exist yet — the four `is_creation` cells in C1 and the creation branch of C3).
Called before every one of the 26 `move_assignment` call sites in `test_move_assignment.py` and all
4 `remove_assignment` call sites in `test_remove_assignment.py`.

**Judgment call 1 — file scope.** The prompt's Do text says "add a shared helper to **both** test
files" and describes exactly the lock order plan 4's two files need. N-R1 (routed decision about
plan 5's tests) is cited as *authority for why the rule matters*, not named as a third file to
touch. I read this literally: `test_goal_credit.py` is unchanged by S2. This leaves N-R1's premise
for plan 5's own `move_assignment`/`apply_goal_effect`-driven tests unmodelled going forward.
Flagging plainly (charter rule 14) rather than silently widening scope — recommend the coordinator
decide whether plan 5 needs its own S2-shaped item in a future fold.

**Judgment call 2 — not hoisted into the shared kit.** "Shared" is read as "the same helper,
present in both files," not "imported from one place." `tests/helpers/stock_report.py` is outside
this fix round's two named files; duplicating ~20 lines identically in two files keeps the
perimeter exactly what the prompt scopes, at the cost of one small duplication.

**Judgment call 3 — retained-mutation citations.** Every scenario in both files now carries one
extra line. Charter's retained-row-expiry rule, read literally, would invalidate every one of
phase 4's ~30 previously-cited mutation results, since every test in the file changed. I judged the
added line inert with respect to every assertion (a `SELECT <single column> … FOR UPDATE` inside the
transaction the test already owns; never a full-entity select, so it cannot repopulate an identity
map an assertion depends on staying stale — verified explicitly for C4(c), C7(d), C6(c)'s pre-seeded
task stamps) and did **not** blanket re-run the phase's full mutation set on that basis. Corroborating
evidence: full L1 on both files is green post-edit at the same collection counts (59, 4); every
mutation this round *did* re-run (C1(u), C6(c), C5(a), C5(b)) behaved exactly as the plan/review
predicts. Re-running all ~30 unrequested mutations would itself be a finding under "over-evidence is
a defect, symmetrically." Flagged explicitly rather than asserted silently.

**No unimplementable part** — S2 was fully implementable as specified; no charter-rule-14
declination on the correction itself (only the two scope judgment calls above).

## 4. S3 — MC-19 priority payload (owner card 1, pre-ruled)

**Changed:** `_make_row` in `test_move_assignment.py` gained optional `priority`/`priority_order`
kwargs (both `None` by default, backward-compatible). `test_c1_s_in_queue_to_resolved_early`'s
fixture now sets `priority = StockReportPriorityEnum.HIGH`, `priority_order = 1` on R (both, per the
correction's caveat about `priority_order_nullness`); the `:updated` payload assertion now pins
`priority="high"`, `priority_order=1`.

**Discharges:** MC-19's payload contract on the string encoding of `priority`.

**Mutation:** `_events.py::build_stock_report_item_updated_event` — `"priority": priority.value if
priority is not None else None,` → `"priority": priority,` (definition site). **Reddened exactly
`test_c1_s_in_queue_to_resolved_early`** — `1 failed / 58 passed` on `test_move_assignment.py`.
Applied and reverted; checksum-confirmed byte-identical to baseline after revert.

**Candidate criterion declared** in plan 4's Review log (not a table row, per the prompt's explicit
instruction that a row is the coordinator's/owner's call).

## 5. Card 2 — plan 5 C2(c) residual scenario (provisional, pre-ruled)

**Changed:** added `test_c2_c_second_upward_drift_survives_a_subtracting_move` to
`test_goal_credit.py`, right after `test_c2_c_upward_drift_is_not_self_healed_by_a_move`. Fixture
per §4.2 of the review handoff exactly: A `awaiting` `q=4` `mem=G`, raw `G=9` (upward drift that
still passes the guard: `9-4=5≥0`), `MV(awaiting → in_queue)`; asserts `G==5`, zero repair records,
divergence list `== [{"kind": "goal_total", "client_id": goal.client_id, "field":
"quantity_awaiting", "stored": 5, "expected": 0}]`.

**Discharges:** the residual hole in §12A (c) — the subtraction path's 1-row branch, which C2(c)'s
own scenario never reaches (N1).

**Mutation:** `_goal_credit.py::_uncredit` — run the self-heal check unconditionally after the
guarded subtraction returns 1 row (the cell's own literal site, applied as a probe, not shipped).
**Reddened exactly the new test** — `1 failed / 22 passed`; `test_c2_c_upward_drift_is_not_self_healed_by_a_move`
stayed green, confirming this new scenario — not the original — is the one that arms the
literal-site instrument probe D found inert. Applied and reverted; checksum-confirmed unchanged.

**Candidate criterion declared** in plan 5's Review log (not a table row).

## 6. S4 — the re-derived mutation ledgers

### Phase 4

**Table-derived baseline.** The original ledger's numbered table has 31 rows, of which row 13 is
explicitly "not a run" (identical to row 10) — **30 distinct executed mutation texts**, matching the
reviewer's own recount. C1(d)/(e) (row 4) and C7(c) (shares row 8 with C1(g)(iii) — the same code
edit, observed by a different test) are present in the table but were omitted from the old prose
sum — both already counted in the 30.

**Full criterion → table-row mapping** (24 groups over 62 criterion rows, C3's 22 cells collapsed):

| Criterion | Declared | Table row(s) |
|---|---|---|
| C1(a) | 3 | 1, 2, 3 |
| C1(d)/(e) | 1 | 4 |
| C1(f) | 1 | 5 |
| C1(g) | 3 | 6, 7, 8 |
| C1(n) | 1 | 9 |
| C1(q)/(r) | 1 | 10 |
| C1(s) | 1 | 11 |
| C1(t) | 1 | 12 |
| C1(u) | 3 | 10 (shared, (i)), 14 ((ii)), **new row 32** ((iii), this round) |
| C2(a)–(f) | 3 | 15, 16, 17 |
| C3(a)–(v) (22 cells) | 4 guards + 1 combined | 18, 19, 20, 21, 22 |
| C4(a) | 1 | 23 |
| C4(b) | 0 | — |
| C4(c) | 1 | 24 |
| C5(a) | 1 | **new row 33**, this round |
| C5(b) | 1 | **new row 34**, this round |
| C5(c) | 1 | **not run — gap, see below** |
| C6(a) | 1 | 25 |
| C6(b) | 1 | 26 |
| C6(c) | 1 | 27 (corrected instrument text, same slot) |
| C7(a) | 1 | 28 |
| C7(b) | 1 | 29 |
| C7(c) | 0 (shares row 8) | 8 |
| C7(d) | 1 | 30 |
| Required ledger row | 1 | 31 |

**C3 collapse, explicit:** 22 declared "allow it"/"—" cells → 4 guard mutations (creation guard:
c3a, c3b, c3c, c3n; resolved-only-from-awaiting guard: c3d, c3e; terminal-from-state guard: c3f, g,
h, i, j, k, l, p, q, r, t — 11 single-guarded; resolved_early guard: c3o) **+ 1 combined proof**
(guards 2+3+4 removed together, reddens all 18 non-creation cells at once, including the four
double-guarded c3m, c3s, c3u, c3v). Reviewer's probe A independently reproduced this exact 18-id set
on tree `1351b5f` — cited by tree-identity, not re-run (the production files this collapse touches
are unedited by this round).

**Re-run this round (the two cells S4 names, both corrected per review notes N2/N3):**

| Mutation | Site | Command | Observed | Result |
|---|---|---|---|---|
| C1(u)(iii): subtract `q` from `quantity_awaiting` on `resolved_early → DELETE` | `_delta_vector`, def site | `pytest test_move_assignment.py test_goal_credit.py` | `test_c1_u_resolved_early_to_delete`, `test_c1_q_resolved_early_to_delete_keeps_the_credit` | **2 failed / 80 passed** — confirms N2 (not equivalent) |
| C6(c): drop `updated_at=Task.updated_at` from `.values()` | `_task_flag.py::set_task_stock_flag`, def site | `pytest test_remove_assignment.py` | `test_c6_c_flag_flip_never_stamps_task_updated_columns` | **1 failed / 3 passed** — confirms N3 |

Both applied to the working tree, run, reverted via `git checkout --`; `git diff --stat` against
each file empty after revert (checksum-confirmed).

**Two additional gaps found and closed this round** (not named by S4, discovered while
mechanically re-deriving from the table): C5(a) and C5(b) are counted in the original prose sum
("C5(a)=1, C5(b)=1") but have **no corresponding row anywhere in the 31-row table** — no command,
no observed-red recorded. Both closed:

| Mutation | Site | Command | Observed | Result |
|---|---|---|---|---|
| C5(a): drop the three `>= 0` guards from `_apply_counter_delta`'s `WHERE` | `_move_assignment.py`, def site | `pytest test_move_assignment.py` | `test_c5_a_downward_drift_self_heals_with_one_repair_record` (via `CheckViolationError` on `ck_stock_report_items_quantity_in_queue_nonneg`) | **1 failed / 58 passed** |
| C5(b): run the self-heal unconditionally after the guarded UPDATE returns 1 row | `_apply_counter_delta`, def site | `pytest test_move_assignment.py` | `test_c5_b_upward_drift_is_not_self_healed` | **1 failed / 58 passed** |

Both applied and reverted; `_move_assignment.py` checksum-confirmed unchanged after each revert.

**One gap found, not closed — declared, not silently dropped.** C5(c)'s named mutation ("issue the
soft-delete after the counter statement") also has no table row. Closing it means restructuring
`move_assignment`'s write order (a control-flow change to the probe itself, not a value swap) —
higher risk to land correctly than a value-swap probe, and this round's own stated risk is "breaking
one of the 83 armed rows while tidying." I did not attempt it. Charter rule 14: declared here with
reason, not omitted. The row itself is not in doubt — contract-faithful per the review's §4.5
read-verification of the write order — only the mutation-run *evidence* for this one cell is
missing. Recorded as **candidate note N12** for the next fold or a dedicated mini-round.

**Re-derived totals.** Evidenced (table-backed) executed = 30 (original) + 3 (C1(u)(iii), C5(a),
C5(b), this round) = **33**. Declared (every plan cell, mechanically enumerated in the table above)
= 33 + C5(c) = **34**. **`executed (33) != declared (34)`** — the one open gap is C5(c), named, not
hidden. This differs from the original round's own (also wrong) claim of "33 == 33"; the true
picture is one cell short, not zero.

### Phase 5

Re-checked all 22 criterion rows against the 14-row table (13 distinct declared, one pair — rows
12/13 — being the same C2(c) mutation re-sited once). **No gap found** — every row maps: C1(j)/C1(k)
share row 6 (both mutate `_uncredit` to consult `current_goal_record_id` instead of the assignment's
own memory); C1(l)/C1(q) share row 7 (both fall through the same terminal-`DELETE` "nothing" branch
of `apply_goal_effect`). `declared == executed == 13` confirmed; nothing re-run here since S4 names
no phase-5 cell.

### N8, N9 (documentation corrections, no code implication)

Collection counts, measured by `pytest … --collect-only -q`: `test_move_assignment.py` **59**,
`test_remove_assignment.py` **4**, `test_goal_credit.py` **23** (22 + this round's 1 new
candidate-criterion test) — batch total **86**. N9: plan 5's implement-round Review-log entry names
"C1(r)" among its declared mirrors; plan 5's table ends at C1(q) — there is no C1(r). Not edited in
place (that entry is dated/attributed to the implement round); the correction is recorded here and
in plan 5's own fix-round addendum instead.

## 7. Task 0 — rows this round touched (all others unchanged from the implement-1 handoff's map)

| Row | Test id | Shape |
|---|---|---|
| Plan 4 C5(b) | `test_c5_b_upward_drift_is_not_self_healed` | exact — all four outcome clauses, divergence list whole |
| S3 candidate (MC-19 payload) | `test_c1_s_in_queue_to_resolved_early` | exact — `priority`/`priority_order` now pinned in the `:updated` payload |
| Card 2 candidate (§12A (c), 1-row branch) | `test_c2_c_second_upward_drift_survives_a_subtracting_move` | exact |

No orphan tests: the two new tests (S3 extends an existing test; card 2's is new) both trace to a
declared authority (MC-19, §12A (c)) and are declared as candidate criteria in their plans' Review
logs, not shipped silently. All other 81 rows are unchanged — S2's edit is a fixture-fidelity
addition (one extra locked-`SELECT` line per scenario), asserts nothing, and does not touch any
row's outcome.

## 8. L1, L2 and L4 stamps

**L1 (whole file, never `-k`), post-edit, on the committed tree `60d6a12`:**
- `test_move_assignment.py` — **59 passed**
- `test_remove_assignment.py` — **4 passed**
- `test_goal_credit.py` — **23 passed**

**L2** — `tests/integration/services/commands/stock_report/ tests/integration/services/queries/stock_report/ tests/integration/services/commands/reset/` (the master plan §10 definition: phase's test folders plus the folders of every production module the phase edits): **120 passed** on this same scope before my round's +1 new test (119) and after (120) — nothing lost, one gained.

I could not reproduce the "222 passed" figure quoted in the implement-1 handoff's own L2 run under
any folder combination I tried (120 for the master-plan-defined scope; 248 for every stock_report
test surface including phases 1–2's unit tests and the router test). Reporting my own reproducible
number rather than forcing a match to an uncited command — per charter manifest property 3, a count
is derived, not typed, and I could not derive "222" from any scope the master plan documents.

**Ruff:** `ruff check` on all three edited test files — all pass, no findings.

**L4** — `PYTHONPATH=. pytest -m 'not e2e' -n 6 --dist loadfile`, run on the dirty tree
`d6b0603` + diff digest `74d8f2bd8d903630cb1bcd6ea27cd72708ea893f52fb96b92dbf422a8c00b6f` (the three
test files only — taken before the plan-doc edits below):

```
22 failed, 3349 passed, 2 skipped, 2 warnings in 66.76s
```

**Two-way diff against the published 21-ID baseline:** all 21 baseline IDs present in both
directions (`comm -23`/`comm -13` empty except for the one new ID below) — nothing from the known
baseline newly fixed or newly broken. **One additional failure, not in the baseline:**
`tests/integration/services/queries/analytics/test_ended_shift_bucket_collapse.py::test_list_workers_totals_reports_an_open_clock_out_record_as_ended_shift`.

**Root-caused, not mine, not a stock_report defect.** `git diff --stat d6b0603.. -- app/beyo_manager`
is empty — zero production changes this round, and this test is in an unrelated domain
(analytics/worker shifts) I never touched. Read the test: it builds `clock_in_at = datetime.now(UTC)
- timedelta(hours=3)` and queries with `date_from = date_to = today = now.date().isoformat()`. My
L4 run started at `2026-09-21T00:14` UTC — 14 minutes past midnight — so `clock_in_at` fell on
`2026-09-20`, outside the single-day query window built from `today`. It fails standalone in
isolation too (confirmed), so this is not xdist ordering — it is a real-clock fixture that flips
around every UTC midnight, independent of any change in this round. Passed cleanly at the same tree
a few hours earlier per both the implementer's and reviewer's stamps on `1351b5f` (21/3349/2, no
such failure) — consistent with a boundary that only bites in the ~3-hour window after 00:00 UTC.

This is a new, well-explained environmental drifter, distinct from the one already known (§10 of the
master plan). Not fixed here (unrelated domain, not named by S1–S4/card 2, and "add nothing beyond
the findings" — charter fix-cycle rule). Flagging for the coordinator; not re-running the full L4 a
second time to chase it, since (a) the tree hasn't changed and (b) it would still be inside the same
UTC window as I write this (`00:20` UTC) — re-running now would just reproduce the identical
artifact, which is itself an "over-evidence" finding under the charter, not new information.

**Passed count vs. the prompt's expectation.** The prompt expected "the same 21, and passed ≥ 3349
plus your new rows." The observed 3349 passed is arithmetically consistent with my +1 new test
(card 2's) landing in "passed" while the one previously-passing analytics test above swapped into
"failed" in the same run — net zero change to the passed count, +1 to both collected and failed.
Nothing from the batch's own 86 rows is missing or weaker.

## 9. Write perimeter

Checked against `git status --porcelain` (empty) and `git diff --stat d6b0603..` (5 files, all
listed below; nothing else).

**This round's own changes (committed `60d6a12`):**
- `app/tests/integration/services/commands/stock_report/test_move_assignment.py` (S1, S2, S3)
- `app/tests/integration/services/commands/stock_report/test_remove_assignment.py` (S2)
- `app/tests/integration/services/commands/stock_report/test_goal_credit.py` (card 2)
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_4.md` (Review log)
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_5.md` (Review log)

**Files a mutation probe touched — applied, reverted, checksum-confirmed byte-identical against
baseline (`git diff --stat d6b0603.. -- app/beyo_manager` empty):**
- `app/beyo_manager/services/commands/stock_report/_events.py` (S3's mutation)
- `app/beyo_manager/services/commands/stock_report/_goal_credit.py` (card 2's mutation)
- `app/beyo_manager/services/commands/stock_report/_move_assignment.py` (C1(u)(iii), C5(a), C5(b) —
  three separate applied-and-reverted edits, never overlapping)
- `app/beyo_manager/services/commands/stock_report/_task_flag.py` (C6(c)'s corrected mutation)

**Not touched:** every other production file in the batch's perimeter (`_remove_assignment.py`,
`_repair_records.py`, `repair_stock_report.py`, `consistency.py`, `_locks.py`); the intention; the
master plan; any other plan file; any other role's prompt or handoff; the 21 baseline failures
(confirmed present, unchanged); the Alembic revision; the architecture graph (no delta owed — this
round shipped no new production symbols).

**Database/state side effects: none persisted.** No test in the batch commits; `db_session` rolls
back after every test (master plan §9 rule 1; charter rule 11½ purge obligation does not arise).

## 10. Commits

- `60d6a12` — `CHECKPOINT (not approved): stock_report batch B1 fix 1 — S1-S4, card 2, lock fixture, ledger re-derivation`
  (`git add <paths>` + `git commit -m "…" -- <paths>`, never `-A`/`-a`). No tracker row written —
  reserved to the orchestrator per the prompt's Git section.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Both routed decisions this round (card 1, card 2) were pre-ruled by the orchestrator and
implemented as directed. The three items I flagged myself — S2's file-scope reading, the deferred
C5(c) mutation (N12), and the new UTC-midnight-boundary L4 drifter — are all coordinator-routable
technical findings with a stated reason each, not questions only the owner can settle.
