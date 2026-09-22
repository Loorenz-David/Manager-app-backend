---
batch: D1
plan: [12, 13, 3 (owner-authorized amendment)]
role: review
round: 2 (re-review 1, delta-scoped)
verdict: APPROVED
state: OWNER_DECISIONS_PENDING
date: 2026-09-22
actor: Opus reviewer (orchestrated subagent, slot `dr2`)
tree: HEAD `74c7a6e`, `git status --porcelain` empty at entry and at exit
---

# Batch D1 re-review 1 — delta-scoped

**Verdict: `APPROVED`.** The production fix is correct, load-bearing, and correctly *not* mirrored
into the repair — I tested that judgement by execution and it holds. All three in-scope rows now
PASS. I open **three should-fix findings and three notes**, none blocking, none requiring a return
to the implementer: the production code is right everywhere I looked.

**Rows in scope: 3 PASS / 0 FAIL / 0 NOT_VERIFIED.** The other 58 rows of the batch are carried
unchanged from round 1 (`2026-09-21_batch_D1_review_1_handoff.md`, 58 PASS / 2 FAIL / 4
NOT_VERIFIED); I did not re-open them and I found nothing in passing that disturbs them.

**L4 gate stamp: 23 failed / 3740 passed / 1 skipped**, both ID diffs ∅. The prompt's 3740 is
right and the earlier 3739 was the arithmetic slip the implementer already corrected.

**The single most important thing in this round is R2-1.** A claim the owner was asked to rule on,
and which has since been written into plan 13's C4(a) cell as settled fact — *"the `client_id`
tiebreaker itself is an EQUIVALENT mutant at this boundary"* — is **false, measured**. Reversing
that term (rather than deleting it) reddens the row. The owner's *decision* on card D-11 does not
change and needs no re-ruling; the sentence recording it does.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

Cards D-1 … D-11 are already ruled and are **not** re-raised. This one is new.

### Card D-12 — the new goal-record filter is proven for one record type out of the two it excludes

**Question.** Do you want a criterion row that plants a *priority-order* record with a live
awaiting count and asserts the health check stays clean — yes or no?

**Story.** The bug you approved a fix for this morning was this: when someone changed a board row's
priority, the system wrote a little history note that copied the row's live "waiting" number, and
the health check then screamed that the note was wrong — forever, on every board where anyone had
ever set a priority. The fix tells the check to look only at goal notes. But the board writes a
*second* kind of note, when someone drags a row up or down inside its priority group, and that note
copies the same live number in exactly the same way. It is covered by the fix. Nothing anywhere
checks that it stays covered: I re-admitted it to the check and all 632 stock-report tests passed.

**Branches.**
- *Yes, add a row:* one scenario — drag a row that has waiting work, then read the health check —
  and the fix is guarded for both note kinds instead of one.
- *No:* correct today; the next person to widen that one line gets the old bug back on a second
  path, and the suite says nothing.

**Recommendation.** Yes. The whole fix is one line, and half of what that line excludes is watched
by nothing; this is the cheapest possible guard for the most recently broken thing in the project.

**On silence.** The gate holds: I record it as a measured coverage gap and credit no coverage for it.

**Trace.** `consistency.py` histories predicate; `set_stock_report_item_priority_order.py:159`;
plan 12 C3(d); intention MC-20, §9 rule 15; my probe P3.

---

## 1. Gate check

| Check | Command / source | Result |
|---|---|---|
| Intention status | `head -40 SR/planning/intention.md` | `RATIFIED` (round 9, 2026-09-19; round 10 additive by owner ruling) — gate passes |
| Tree at entry | `git status --porcelain` | empty; HEAD `74c7a6e` |
| Fix checkpoint in HEAD | `git log --oneline 06ad124..HEAD` | `2fb7acb` (production fix) and `82d96e4` (verification fix) both ancestors |
| Production diff, implementer stamp → my tree | `git diff --name-only 2fb7acb..HEAD -- app/ \| wc -l` | **0** — my `app/` tree is byte-identical to the stamped tree |
| Tree at exit | `git status --porcelain` | empty (all probes reverted, §7) |

## 2. Perimeter — verified against the tree, not reconstructed

`git diff --name-only 06ad124..HEAD` (round-1 review tree → HEAD), **app/ paths**:

```
app/beyo_manager/services/queries/stock_report/consistency.py           ← production fix (the only production file)
app/tests/integration/services/commands/stock_report/test_delete_stock_report_item.py      ← verification fix (N-4)
app/tests/integration/services/queries/stock_report/test_list_stock_task_assignments.py    ← verification fix (S-1)
```

Nothing else under `app/`. The production diff is **+8 / −1 in one function**, exactly as declared:

```diff
-from beyo_manager.domain.stock_report.enums import ACTIVE_ASSIGNMENT_STATES
+from beyo_manager.domain.stock_report.enums import (
+    ACTIVE_ASSIGNMENT_STATES,
+    StockReportHistoryRecordTypeEnum,
+)
                 select(StockReportHistoryRecord)
-                .where(StockReportHistoryRecord.workspace_id == workspace_id)
+                .where(
+                    StockReportHistoryRecord.workspace_id == workspace_id,
+                    StockReportHistoryRecord.type
+                    == StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
+                )
```

**Docs in the window** (all accounted for, none an automatic finding): `plans/plan_3.md`,
`plans/plan_12.md`, `plans/plan_13.md`, `master_plan.md`, `OWNER_CARDS_batch_D.md`,
`REMAINING_WORK.md`, `MORNING_BRIEF_2026-09-22.md`, the three handoffs and three prompts.
The implementer's §9.5 warning is confirmed: `b9d2d03` and `79ad5aa` are the coordinator's own
docs-only commits inside the window, not the implementer's.

**Criterion-cell audit.** `git diff 06ad124..HEAD -- plans/` removes **zero** lines from
`plan_3.md` and `plan_12.md` (append-only) and exactly **two** from `plan_13.md` — the C2(a) and
C4(a) cells, replaced by the coordinator's authorized fold of the tester's proposed backfills
(`cbecd2b`). No implementer or tester edited a criterion cell. No test function was added or
removed in the window (`git diff 06ad124..HEAD -- app/tests/ | grep -E "^[-+](async )?def test_"`
→ empty), so this window contributes **zero orphan-test risk** and the pass-count arithmetic
closes: 24 + 3739 = 23 + 3740 = 3764, the identical collection.

## 3. Evidence policy for this round

`app/` is byte-identical from `2fb7acb` to my tree, so the implementer's ledger is **citable**
and I did not re-buy it: I consumed its M1 (revert the predicate → witness red), M2 (predicate
flipped to `PRIORITY_CHANGE` → the goal side goes unchecked, 2 red), its L2 (638 passed) and its
lint. The tester's rows are a different case: its tree carried the **un-fixed** `consistency.py`,
and `test_delete_stock_report_item.py` reaches that module through `assert_stock_report_clean`
(`tests/helpers/stock_report.py:143`), so its mutation evidence for C2(a) is **not** tree-matched
and I re-ran it. The C4(a) cell's mutants were **authored into the plan after** the tester's run
(fold `cbecd2b`), so executing them is manifest property 4, not repetition.

**Correction to the prompt's L-45 premise, stated plainly.** "Every mutation observed in round 1
and in the verification fix round ran against an already-red suite" is true of the *suite* and
false of the *runs that matter*: every tester mutation was an **L1 run of a single file**, and the
one red test lives in a third file that was in none of those runs. A second red could not have
hidden inside the first. What *did* justify re-running is the tree change above, plus two cells
that were amended after their measurement. Both C3(d) mutations, however, genuinely were run
against a red witness — those I re-confirmed, and one of them changed answer (R2-3).

**L4 authorization line, written before the run:** L4 at charter scope (c), the approval gate;
narrower evidence is insufficient because this round's verdict *is* the gate.

## 4. The eleven probes

All at slot `BEYO_TEST_SLOT=dr2`, `PYTHONPATH=. .venv/bin/pytest` from `app/`, all applied at the
**definition site**, all reverted and checksum-verified (§7).

| # | Hypothesis | Site (def./call) | Scope | Result |
|---|---|---|---|---|
| **P0** | the three in-scope files are green on my tree | — | L1 ×3 files | **27 passed** |
| **P1** | *(my error, reported)* C3(d)'s mutant expressed as a value-source swap `mover[…]` → `row.…` | `set_stock_report_item_priority.py` (def.) | L1 | **GREEN — 16 passed.** Not a faithful mutant: SQLAlchemy's ORM-enabled `update()` with `RETURNING` synchronises the identity map, so `row.*` already holds the post-move values. Discarded and re-applied as P1b |
| **P1b** | C3(d)'s **named** mutant — the record is inserted *before* the gap-close, the append and the mover `UPDATE` | same file (def.), block relocated | L1 | **RED — 2 failed / 14 passed.** Witness at `:627` `assert 2 == 3` (`priority_order`), plus `test_priority_change_closes_the_source_gap_and_appends` at `:556`. **The `quantity_awaiting` sub-check at `:628` is never reached** → R2-3 |
| **P2** | is C3(d)'s `quantity_awaiting == 4` sub-check discriminating at all? | same file (def.), `mover["quantity_awaiting"]` → `mover["quantity_in_queue"]` | L1 | **RED — 1 failed / 15 passed**, `:628 assert 0 == 4`, witness alone. The sub-check *is* armable; no named mutation reaches it |
| **P3** | **variation on the fix**: does anything observe the *other* excluded record type? predicate widened to `.in_((QUANTITY_REQUESTED_CHANGE, PRIORITY_ORDER_CHANGE))` | `consistency.py` (def.) | L2 (every stock_report tree + routers) | **GREEN — 632 passed.** → R2-2 / card D-12 |
| **P4** | the repair mirror is inert | `repair_stock_report.py` (def.), `type == QRC` added to the `goal_total` `UPDATE` | L2 goal side | **GREEN — 443 passed** |
| **P5** | …and inert because the branch *runs* and always targets a goal record, not because it never runs | same site, guard inverted to `type != QRC` | L2 goal side | **RED — 3 failed / 440 passed**, all three `RuntimeError: goal-total repair affected an unexpected number of rows` at `:263` |
| **P6** | consequence 1 — does the repair ever write a history record outside its lock set? | `repair_stock_report.py` (def.), instrumented `raise` if the written id is not in the locked list | L2 goal side | **GREEN — 443 passed**: write set ⊆ lock set everywhere the repair is exercised |
| **P7** | consequence 3 — is a **soft-deleted** goal record still reconciled clean after the cascade? | `test_delete_stock_report_item.py`, one added `assert_stock_report_clean` in the goal-record cascade test | L1 | **GREEN — 6 passed.** Goal at 8, A1's credit subtracted, A2/A4's kept, every history record soft-deleted, check clean |
| **P8** | consequence 3 — would CC-2 (`is_deleted.is_(False)` on the histories selection) be observable? | `consistency.py` (def.), with P7 still in place | L2 goal side | **GREEN — 443 passed.** CC-2 is an equivalent mutant → R2-5 |
| **RP-1** | C4(a) — drop `created_at`, leave `client_id` | `list_stock_task_assignments.py` (def.) | L1 | **RED — 1 failed / 4 passed**, `:265 assert ids == [HI, LO, MID]`, "At index 0 diff" |
| **RP-1b** | C4(a) — drop `client_id`, keep `created_at` (tester says EQUIVALENT) | same site (def.) | L1 | **GREEN — 5 passed.** Tester's measurement confirmed |
| **RP-1b-var** | **new mutant shape** — keep `client_id` but **reverse** it to `.desc()` | same site (def.) | L1 | **RED — 1 failed / 4 passed**, `:265` "At index **1** diff" — the tied pair. → **R2-1** |
| **RP-11** | C2(a) — `target_kind` `STOCK_REPORT_ITEM` → `HISTORY_RECORD` | `_delete_stock_report_item_cascade.py` (def.) | L1 | **RED — 1 failed / 5 passed**, `:427`, the new assertion, nothing else in the file moves |

**Consumed by citation, not re-bought:** the implementer's M1, M2, L2 and lint (tree-matched);
the tester's M-71, M-72 (state-filter mutants at a site the production fix does not reach) and
M-67 (the cascade's raise-instead-of-repair, which aborts before `assert_stock_report_clean` is
ever evaluated, so the tree change cannot affect it); round 1's RP-2.

## 5. The four questions the prompt asked

### 5.1 The repair mirror — **the implementer is confirmed, by execution. Do not add it.**

P4 + P5 together are the proof, and neither alone would be: P4 shows the mirror guard changes no
observable outcome (443 passed), and P5 shows that is *not* because the branch is dead — inverting
the same guard reddens three tests with `goal-total repair affected an unexpected number of rows`,
i.e. the branch executes and **every record it writes is a `quantity_requested_change`**. That is
the doctrinal definition of an equivalent mutant, and an equivalent mutant is by construction
unarmable: no test could ever distinguish the mirrored repair from the unmirrored one. Structural
reading agrees — `grep -rn "compute_stock_report_divergences" app/` gives exactly three production
consumers (`get_stock_report_consistency.py:10`, `repair_stock_report.py:170,217,294`) plus the
test helper, and `repair_stock_report` constructs no divergence of its own. **L-37 shape, correctly
identified. Adding the mirror would have been the finding, not omitting it.**

### 5.2 Consequence 1 — the narrowed lock set. **No sibling lock was lost.**

P6 asserts, inside the repair itself and across every test that exercises it, that each history
record the `goal_total` branch writes was in the list handed to `lock_stock_report_history_records`
— 443 passed, no violation. Structurally the two sets are the *same comprehension* over the
divergence list (`entry["kind"] == "goal_total"`), so narrowing the list cannot make them diverge;
and the branch needs no sibling record, because the recomputation it is checked against
(`_recompute_goal_totals_for_workspace`) reads **assignments**, not other history records, and
assignments are locked separately. The one path that remains unlocked-by-design is unchanged by
this fix and recorded as note R2-6.

### 5.3 Consequence 2 — the read endpoint. **No ratified or published text is contradicted; the opposite.**

Intention **MC-20**'s divergence table states the `goal_total` row as *"`quantity_awaiting` of each
**goal record**"*, and §6.2 / MC-5 define a goal record as a `quantity_requested_change`. The check
was therefore **out of conformance before the fix and is in conformance after it**; the payload did
not get narrower than its contract, it stopped emitting rows the contract never authorised.
The published `HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` §4.1 enumerates the eight `kind`
values, the five-key element shape and the sort order, and says nothing about which record types
`goal_total` covers — no key, kind, type or sort changed. **No frontend addendum is owed.** The only
client-visible difference is that an empty `divergences` array — the documented healthy state — is
now reachable on a workspace where anyone has ever changed a row's priority; before the fix it was
not.

### 5.4 Consequence 3 — `is_deleted`. **Correct as shipped. CC-2 should be closed "do not implement".**

Both sides of the `goal_total` comparison survive the cascade symmetrically, and P7 measures it:
in the cascade test the goal record ends at 8 with A1's credit subtracted and A2's/A4's kept
(MC-5's "`resolved → DELETE` … resolved work stays counted"), every history record of the row is
soft-deleted, and the check reports **nothing**. Adding CC-2's predicate (P8) leaves all 443
stock-report tests green, so it is an equivalent mutant *and* it would silently narrow MC-20 below
its ratified wording, which says "each **goal record**" with no non-deleted qualifier — MC-5's
"non-deleted" belongs to the definition of the **current** goal record (the credit *target*), not
to the reconciliation *set*, and MC-5's own last table row requires the arithmetic to run on a
soft-deleted `R`. Implementing CC-2 would stop the check watching every goal record of every
deleted row. See R2-5.

## 6. Findings

Legend — route: `production` → implementer · `verification` → tester · `plan` → coordinator/owner.

### Round-1 findings: all three closed

| Round 1 | Severity | Status |
|---|---|---|
| **B-1** (blocking, `production`) — the `goal_total` rule has no type filter | blocking | **RESOLVED.** Predicate in place; witness green **unedited**; fix load-bearing (implementer's M1, cited) and not over-narrowed (M2, cited; my P3, P4/P5) |
| **S-1** (should-fix, `verification`) — C4(a)'s ordering clause cannot fail | should-fix | **RESOLVED.** RP-1 red on the green tree at the constructed expectation. The shipping risk S-1 named — "a change that dropped the date entirely would ship unnoticed" — is closed |
| **N-4** (note, `verification`) — C2(a) does not assert `target_kind` | note | **RESOLVED.** RP-11 red on that assertion alone, 1 failed / 5 passed |

### R2-1 · should-fix · route `plan` · plan 13 C4(a)'s amended cell states a measurably false claim

The cell, as folded at `cbecd2b`, reads: *"**The `client_id` tiebreaker itself is an EQUIVALENT
mutant at this boundary, measured not assumed** (owner card D-11): dropping it leaves the output
identical…"*. The first clause does not follow from the second and is **false**:

```
RP-1b     .order_by(created_at.asc())                          → GREEN, 5 passed
RP-1b-var .order_by(created_at.asc(), client_id.desc())        → RED, 1 failed / 4 passed
          tests/…/test_list_stock_task_assignments.py:265: assert ids == [HI, LO, MID]
          AssertionError … At index 1 diff   ← the tied LO/MID pair
```

What is equivalent is the **deletion** of the term, not the term. When the clause is present it
genuinely decides the tie (reverse it and the output reverses); when it is absent, today's plan
happens to supply the same order for free. So C4(a) is armed on **two** of its three ordering
sub-terms — `created_at` (RP-1) and the tiebreaker's **direction** (RP-1b-var) — and unarmed only
against the clause's *removal*.

**Correction (coordinator's lane, cell wording only):** replace the quoted sentence with
*"deleting the `client_id` term is unobservable under today's query plan (RP-1b, green — the
conditions are recorded below); **reversing** it is observable and is the row's arming proof for
the tiebreaker (RP-1b-var, red at the tied pair, 2026-09-22)."*

**Owner card D-11 needs no re-ruling.** Its decision — accept a structural check rather than spend
a round — stands and is *better* supported than when it was taken: the blind spot is narrower than
the card's Story described ("unproven by a test" → "unproven only against deletion"). The card's
own coordinator note already insists both labels say "unobservable, not unnecessary"; this
measurement is exactly the *condition* that note asks to be recorded. **Card D-11 is not re-opened.**

### R2-2 · should-fix · route `verification` · the fix's predicate is armed for one of the two types it excludes

`set_stock_report_item_priority_order.py:155-166` writes a `priority_order_change` record carrying
`quantity_awaiting=mover["quantity_awaiting"]` — the row's **live** counter, byte-for-byte the
same construction as the `priority_change` record at
`set_stock_report_item_priority.py:157-169` that caused B-1. It is therefore exactly as unable to
satisfy the `goal_total` rule, and the fix correctly excludes it. **Nothing observes that it stays
excluded:** P3 re-admitted `PRIORITY_ORDER_CHANGE` to the predicate and the entire stock-report L2
surface stayed green — 632 passed.

*Absence bounded without an L4* (the instrument round 1 used for RP-10):
`grep -rln "compute_stock_report_divergences\|assert_stock_report_clean\|get_stock_report_consistency" app/tests`
filtered to paths outside the L2 set returns **nothing**, so every caller of the check anywhere in
the suite was inside P3's run.

Charter rule 15 — *a guard ships with proof it can fail* — is satisfied for one of the guard's two
exclusions and not the other. **Suggested correction:** one criterion row whose scenario applies
`SO(…)` to a row carrying an awaiting assignment and asserts the check returns `[]`, with the named
mutant *"widen the `histories` predicate to admit `priority_order_change` → the check reports a
spurious `goal_total` divergence"*. **See owner card D-12** — I author no row.

### R2-3 · should-fix · route `verification` · plan 12 C3(d): one named mutation, two sub-checks, and it reaches only one

The row's outcome is *"the record's `quantity_awaiting == 4` **and** `priority_order == 3`"*. Its
one named mutant ("insert the record before the append and before the counter read") reddens the
test at `:627`, the `priority_order` clause, and **returns before `:628` ever executes** (P1b:
2 failed / 14 passed, both failures on `priority_order`). The `quantity_awaiting` clause is
nonetheless genuinely discriminating — P2 reddens it alone (`:628 assert 0 == 4`, 1 failed /
15 passed). This is charter rule 12 verbatim: *"Sequential assertions short-circuit … enumerate the
mutations too, one per sub-check, and record which bites on which."* Round 1 could not see it —
L-D: the mutant was run against a witness that was already red for a third reason.

**Suggested correction, and the measurement is already in hand:** add to C3(d)'s mutation cell
*"`set_stock_report_item_priority.py` (def.): the record's `quantity_awaiting` sources
`mover["quantity_in_queue"]` instead of `mover["quantity_awaiting"]` → red at the snapshot clause
alone (1 failed / 15 passed, 2026-09-22)"*. No new test is needed; the assertion already exists.

### R2-4 · note · route `verification` · the witness test's docstring still says it is red

`test_stock_report_priority_and_ordering.py:591` reads **"This test is currently RED on the
unmutated tree, and that is the finding"**, followed by a five-line `input / expected / observed`
block describing the defect as live and a "The fix is in APPROVED phase 3's files" sentence. The
test has been green since `2fb7acb`. The implementer was right not to touch a test file in a
production-fix round, and the tester's perimeter excluded this file — so nobody owned it. It is
precisely the hazard the tester flagged against itself (its §7 item 2: *"a false claim beside a
fixture is exactly how the next session inherits a wrong premise"*). One docstring edit: keep the
`input/expected/observed` history, re-tense it, and name `2fb7acb` as where it went green.

### R2-5 · note · route `plan` · candidate CC-2 should be closed as "do not implement", not carried as a gap

Evidence and reasoning in §5.4. Plan 3's Review log currently records CC-2 as *"a soft-deleted goal
record is out of the reconciliation … Unreached today"*, which reads as a gap awaiting closure. It
is the opposite: implementing it would narrow MC-20 below its ratified wording and stop the check
watching the goal records of every deleted row, for no observable gain (P8 green). **Suggested
disposition:** close CC-2 with the measurement, not with a fix.

### R2-6 · note · route `plan` (passing glance, pre-existing, unchanged by this fix)

`repair_stock_report` locks **non-deleted** assignments only, while
`_recompute_goal_totals_for_workspace` sums **all** credited assignments *including soft-deleted
ones* (MC-5, deliberate). So a soft-deleted-but-still-credited assignment contributes to every
`goal_total` `expected` without being locked. Inert today — MC-5 §14F F4 keeps a resolved
assignment's credit and nothing mutates a soft-deleted assignment's `quantity` or
`credited_history_record_id` — and it predates this batch. Backlog note, not a defect.

## 7. Mutation-probe declaration

Every probe applied at a definition site, reverted, and verified byte-identical against a
`shasum -a 256` taken **before** the first probe on each file. `git status --porcelain` is empty
at exit and `git diff --quiet` exits 0.

| File touched by a probe | Probes | Revert method | Verification |
|---|---|---|---|
| `app/beyo_manager/services/commands/stock_report/set_stock_report_item_priority.py` | P1, P1b, P2 | `git checkout --` | `shasum -c` **OK** after each; `git diff --quiet` exit 0 |
| `app/beyo_manager/services/queries/stock_report/consistency.py` | P3, P8 | `git checkout --` | `shasum -c` **OK** after each |
| `app/beyo_manager/services/commands/stock_report/repair_stock_report.py` | P4, P5, P6 | `git checkout --` | `shasum -c` **OK** after each |
| `app/beyo_manager/services/queries/stock_report/list_stock_task_assignments.py` | RP-1, RP-1b, RP-1b-var | `git checkout --` | `shasum -c` **OK** after each |
| `app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py` | RP-11 | `git checkout --` | `shasum -c` **OK** |
| `app/tests/integration/services/commands/stock_report/test_delete_stock_report_item.py` | **P7** — one added `assert_stock_report_clean` line | **copy restored from `/tmp/del_backup.py`**, because the file is also a legitimate part of the fix perimeter and `git checkout --` would have been indistinguishable from reverting the tester's work | `shasum -c` **OK**; `grep -c "PROBE P7"` → **0** |

**Database / state side effects: none beyond ordinary test teardown.** Every probe ran through the
suite's own committing tests, each of which owns its `purge_stock_report_workspace` teardown
(§9 rule 11½); no probe wrote to the configured database outside a test, and no fixture, migration
or seed was modified. Slot `dr2` throughout, so no other slot's schema was touched.

**Tool-recorded state: NONE.** I made no archgraph write. I did verify the implementer's graph
observation rather than take it on trust: the
`query-stock-report-consistency → table-stock-report-history-record` `reads_from` edge
(`.archgraph/architecture.yml:14585-14592`) carries the evidence summary *"Sums workspace-scoped
**goal records** to recompute the goal total"* with `inferenceReason` *"The goal_total divergence
kind is derived entirely from these rows."* — which was false of the code on 2026-09-20 and is
**true as of `2fb7acb`**. The fix closes a graph/code discrepancy; no node or edge needs amending,
and nothing here is for an agent to adjudicate.

## 8. L4 — the one gate stamp

| | |
|---|---|
| Scope | L4, charter scope (c) — the approval gate. Authorization line written before the run (§3) |
| Command | `BEYO_TEST_SLOT=dr2 PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q --tb=no` from `app/` |
| Tree | HEAD **`74c7a6e`**, `git status --porcelain` **empty** before and after |
| Result | **23 failed / 3740 passed / 1 skipped**, 85.1 s |
| Baseline comparator | `handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt` — 23 IDs (21 published + the 2 slot-sensitive `test_database_isolation` IDs, master plan §10) |
| Observed **not** in baseline | **∅** (`comm -23`, empty) |
| Baseline **not** observed | **∅** (`comm -13`, empty) |
| Pass reconciliation | 24 + 3739 + 1 = 23 + 3740 + 1 = **3764**; no test added or removed in the window (§2) |

The prompt's **3740** is correct; the implementer's §5 arithmetic is confirmed independently here.

## 9. Per-row verdicts — the three rows in scope

| Row | Round 1 | Now | Evidence |
|---|---|---|---|
| plan 12 **C3(d)** | FAIL (`BLOCKED-PRODUCTION`, B-1 / card D-5) | **PASS** | Witness green **unedited** (P0, 16 passed in file). `priority_order` clause armed by the named mutant (P1b, red at `:627`); `quantity_awaiting` clause armed (P2, red at `:628` alone) though by no *named* mutation → R2-3. `assert_stock_report_clean` now passes for the right reason: the rule no longer applies to the record phase 12 writes |
| plan 13 **C4(a)** | FAIL (S-1) | **PASS** | State-filter half cited (M-71, M-72). `created_at` term armed (RP-1, red at `:265` index 0). Tiebreaker **direction** armed (RP-1b-var, red at `:265` index 1); tiebreaker **deletion** unobservable under today's plan (RP-1b, green — confirmed, and correctly recorded as a structural check per owner card D-11). Cell wording wrong → R2-1 |
| plan 13 **C2(a)** | PASS with note N-4 | **PASS** | `target_kind` asserted and armed (RP-11, red on that assertion alone, 1 failed / 5 passed, nothing else in the file moves). M-67 cited |

**The other 58 rows are carried unchanged from round 1** (58 PASS / 2 FAIL / 4 NOT_VERIFIED, of
which the 2 FAILs are the two rows above). Net batch position: **61 PASS / 0 FAIL / 4
NOT_VERIFIED** (the four NOT_VERIFIED — plan 12 C2(a), C2(b) and plan 13 C2(b), C1-side — are
unchanged and out of this round's scope).

## 10. Carry-forward dispositions

| Item | Route | Destination |
|---|---|---|
| **R2-1** — C4(a) cell wording (tiebreaker is not an equivalent mutant; deletion of it is) | `plan` | coordinator, next fold, **before the approval-gate commit** — the sentence is in a shipped criterion cell |
| **R2-2 / card D-12** — no row guards the `priority_order_change` exclusion | `verification` | owner rules the card → coordinator authors the row → tester arms it, alongside the three rows already queued (D-8, D-1, D-7) |
| **R2-3** — C3(d)'s second sub-check has no named mutation | `verification` | coordinator folds the measured mutant into C3(d)'s cell; no test work |
| **R2-4** — the witness docstring still says the test is red | `verification` | tester, next touch of `test_stock_report_priority_and_ordering.py`, or the D1 closeout |
| **R2-5** — CC-2 closed "do not implement" | `plan` | coordinator, plan 3 Review log, at the D1 closeout |
| **R2-6** — the repair's assignment lock vs MC-5's deleted-included sum | `plan` | project backlog (post-D), with the MC-5 F4 reasoning attached |

## 11. Lessons for the plans

- **L-46. A "cannot be proven" verdict is a claim about the mutant shapes tried, not about the
  clause.** RP-1 and RP-1b are both *deletions*; three runs of deletions produced the conclusion
  "unobservable", which one *reversal* refuted in two seconds. When a round is about to record
  `EQUIVALENT` or `UNFORCEABLE` on an ordering, precedence or comparison clause, the ledger must
  show at least one **non-deletion** shape at the site before the label is allowed to stand.
- **L-47. Re-confirm a mutant by re-applying it, not by re-expressing it.** My P1 expressed C3(d)'s
  "inserted too early" mutant as a value-source swap and it came back green — because SQLAlchemy's
  ORM-enabled `UPDATE … RETURNING` synchronises the identity map, so the "pre-move" ORM attribute is
  not pre-move at all. A round that had recorded P1 as the named mutation would have reported
  C3(d) as unarmable and been wrong. Relocating the statement (P1b) reddened it immediately.
- **L-48. "The suite was red" is not the same as "the run was red."** L-45 was written as a
  blanket re-confirmation duty; in fact every tester L1 run excluded the red test entirely, and
  the runs that genuinely needed re-confirmation were the two C3(d) mutations in the witness's own
  file. Future L-45 invocations should name the *runs whose scope contained the red test*, which
  is a cheap grep, rather than the whole campaign.
- **L-49. A fix scoped by an enum member owes a case table over the enum, not over the trigger.**
  The owner's ruling said "only … goal records"; the fix's predicate therefore excludes **two**
  types, and the round's evidence covered the one the bug report happened to name. Charter rule 2's
  "enumerate, never sample" applies to the *excluded* set of a new predicate exactly as it applies
  to a precedence order.
- **L-50 (process, small).** A production-fix round is forbidden to touch test files, and a
  verification round is scoped to the findings it was given — so a test **docstring** that a
  production fix falsifies (R2-4) belongs to nobody. Worth one line in the coordinator's fix-prompt
  template: *"name any test docstring or comment your change makes false; the tester re-tenses it."*

## 12. What I could have hidden and am reporting

1. **My first C3(d) mutant (P1) was wrong and came back green.** I could have reported only P1b
   and looked like I re-confirmed the mutation first time. P1 is in the ledger with the reason it
   was invalid, because a green mutant that is actually mis-applied is the exact failure mode this
   project has recorded three times.
2. **I ran a probe inside a test file** (P7) and reverted it from a scratch copy rather than with
   git, because that file is legitimately part of the fix perimeter. Git did not witness that
   revert; `shasum -c` and `grep -c "PROBE P7" → 0` did. Same mechanism the tester declared, same
   disclosure.
3. **RP-1b-var was not asked for and is not in any plan.** It is a mutant shape nobody named, at a
   site an owner card had already closed, and the prompt told me not to try to force that clause.
   I did not force it by manipulating storage — I applied an ordinary mutation and it bit. Reporting
   it costs the round a should-fix against a cell the coordinator wrote yesterday, and I am aware
   that staying quiet would have left a tidier handoff.
4. **The prompt's L-45 premise is partly wrong and I said so** (§3) rather than performing the
   full re-confirmation it asked for and billing the round for it. Two of the runs it asked for
   (C4(a)'s state-filter mutants) I consumed by citation instead, with the reason stated.
5. **Thirteen probe runs plus one L2 for P0 is more than a delta re-review strictly needs.** P4/P5
   and P7/P8 are pairs where one run would have produced an answer and two produced a *sound* one;
   I would defend both pairs, but the budget was not free and the charter's symmetry rule applies
   to me too.
6. **I did not re-verify the 58 carried rows in any way**, including the four `NOT_VERIFIED` ones.
   The batch's net tally in §9 is arithmetic on round 1's numbers, not a fresh measurement.
7. **I did not write any tracker row** (master plan §4/§4A: orchestrator-only), so the batch
   tracker still reads `CHANGES_REQUESTED` until the orchestrator moves it. My verdict lives here
   and in the two Review logs, nowhere else.
