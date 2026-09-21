---
plan: 13
batch: D1
role: test-fix
round: 2
state: OWNER_DECISIONS_PENDING
date: 2026-09-22
actor: tester (Opus, slot `dt2`)
---

# Batch D1 — verification fix round 1. S-1 and N-4, and nothing else.

Both findings routed `verification` are resolved. **S-1's ordering row is now armed on the term
that mattered** — the `created_at` half, whose loss was the shipping risk the reviewer named — and
**N-4's assertion is added and bites**. One half of S-1's prescribed proof did not come out as the
prompt predicted, and it is not a weak fixture: it is a **measured equivalent mutant**, with the
query plan that makes it one. That is the single item needing a ruling, and it is a `plan`/owner
question, not a production defect.

Prompt: `prompts/tester/2026-09-22_batch_D1_fix_verification_1.md`.
Tester checkpoint: **`0b7a32f`** (see §8 — SHA recorded by the commit that carries this file).
Implementer checkpoint consumed: **`b6cbbb9`**. Review round 1 tree: **`4b90bad`**.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card D-11 — the assignment list's tiebreaker cannot be proven by any test we can write

**Question** — Accept that the `client_id` tiebreaker on the assignment list is held by a
structural check (a reviewer reading the query) rather than by a test, or spend a round trying to
force it?

**Story** — A worker opens an item's task history and sees three assignments. Two were created in
the same instant, so the list has to pick an order for them, and the rule we wrote says "then by
id" so the board never reshuffles between two refreshes of the same screen. Today Postgres happens
to hand those two rows back in id order anyway, because of how it reaches them — so if someone
deleted the "then by id" words tomorrow, every test we own would still pass, and the reshuffling
would only start appearing much later, on a bigger table, as an intermittent complaint nobody can
reproduce.

**Branches** — *Accept:* the clause stays in the code and in the review checklist, unproven by a
test, and we carry a known blind spot on one list. *Spend a round:* a test could force it only by
manipulating how Postgres physically stores rows, which is brittle and would mislead the next
reader. *Drop the clause:* the list becomes non-deterministic on ties, which is the defect.

**Recommendation** — **Accept**, because the alternative test would prove our knowledge of
Postgres storage, not our contract, and the clause is one line a reviewer can read.

**On silence** — the gate holds: C4(a) ships `ARMED` on its `created_at` term with the tiebreaker
recorded `EQUIVALENT`, and no criterion cell is changed by me.

**Trace** — plan 13 C4(a); §9 rule 14; doctrine "green where you expected red".

---

## 1. What changed — the whole diff

Two test files. **No production file, no plan cell, no criterion row, no tracker row.**

### (a) `app/tests/integration/services/queries/stock_report/test_list_stock_task_assignments.py` — S-1

In `test_every_non_deleted_state_is_listed_in_created_at_client_id_order`:

1. **The fixture now orders the data against its key** (plan 13 §6 preamble, L-14, master plan
   §10). The three listed ids are bound by sorting the real ids at runtime — `LO < MID < HI` —
   and `created_at` is then written against that sort by raw SQL: `HI` (the **largest**
   `client_id`) gets `EARLY`, `LO` and `MID` share `LATE`. So `created_at` ascending disagrees
   with `client_id` ascending, and the pair that remains is separated only by `client_id`.
2. **The expectation is constructed, not re-derived.** The old test computed `expected_order` by
   re-running production's own `ORDER BY created_at, client_id` in a second query — a mirror, not
   a pin. It is replaced by `assert ids == [HI, LO, MID]`.
3. Two module constants added (`EARLY`, `LATE`) and a comment block recording the measurement in
   §3 so the next reader does not re-derive it.

Nothing else in the test changed: `set(ids) == {a1, a2, a4}` and the three `state` assertions are
untouched, which is why C4(a)'s state-filter half needed no new instrument.

### (b) `app/tests/integration/services/commands/stock_report/test_delete_stock_report_item.py` — N-4

One assertion and one import in `test_a_counter_left_non_zero_is_repaired_to_zero_and_recorded`:

```python
assert record.target_kind == StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM
```

placed **first** among the record's field assertions, so a wrong mapping is reported as a wrong
mapping rather than surfacing later as a confusing mismatch on another field.

---

## 2. Verification ledger

### Table 1 — mutations (all applied at the definition site, all reverted)

| M-id | Site (`file:symbol`, def / call-site) | Plan-named? (row) | Landed | Command (scope) | Observed red: test id → assertion / row letter | Reverted |
|---|---|---|---|---|---|---|
| RP-1 | `services/queries/stock_report/list_stock_task_assignments.py:list_stock_task_assignments` (def.) — drop `created_at` from `.order_by`, leaving `client_id` alone | no (reviewer's S-1 proof; **proposed backfill** for C4(a)) | yes, verified in the `.order_by` inside the function | L1 `BEYO_TEST_SLOT=dt2 PYTHONPATH=. pytest tests/integration/services/queries/stock_report/test_list_stock_task_assignments.py` | **RED** `…::test_every_non_deleted_state_is_listed_in_created_at_client_id_order` → `assert ids == [HI, LO, MID]`, "At index 0 diff" (1 failed / 4 passed). **Green on the pre-fix fixture, 5 runs (reviewer).** | yes, `git diff --quiet` exit 0 |
| RP-1b | same `.order_by` (def.) — drop `client_id`, keep `created_at` | no (reviewer's S-1 proof) | yes | L1 same file | **GREEN — 5 passed.** `EQUIVALENT`, measured; mechanism in §3 | yes, exit 0 |
| RP-2 | same `.order_by` (def.) — both terms `.desc()` | no (reviewer's S-1 proof) | yes | L1 same file | **RED** same test → `assert ids == [HI, LO, MID]` (1 failed / 4 passed). Re-run at the new surface (L-23) | yes, exit 0 |
| M-71 | same function (def.) — add `state.in_(ACTIVE_ASSIGNMENT_STATES)` to the `where` | **yes — C4(a)(i)** | yes | L1 same file | **RED** same test → `assert set(ids) == {a1, a2, a4}`, A2 **and** A4 missing | yes, exit 0 |
| M-72 | same function (def.) — add a hand-typed `state IN ('in_queue','in_progress','awaiting','resolved','failed')` | **yes — C4(a)(ii)** | yes | L1 same file | **RED** same test → same assertion, **A4 alone** missing — the §9 rule 16 defect the row exists for | yes, exit 0 |
| M-67 | `services/commands/stock_report/_delete_stock_report_item_cascade.py` (def.) — raise instead of repairing when a counter is non-zero after the loop | **yes — C2(a)** | yes, inside the `_COUNTER_COLUMNS` loop | L1 `…/test_delete_stock_report_item.py` | **RED** `…::test_a_counter_left_non_zero_is_repaired_to_zero_and_recorded` → `RuntimeError: sri_… has a non-zero quantity_in_queue` (1 failed / 5 passed) | yes, exit 0 |
| RP-11 | `_delete_stock_report_item_cascade.py` (def.) — `target_kind=STOCK_REPORT_ITEM` → `HISTORY_RECORD` at the cascade's `write_repair_record` call | no (**proposed backfill** for C2(a)) | yes, the one occurrence in the file | L1 same file | **RED** same test → **the new assertion**: `assert <…HISTORY_RECORD: 'history_record'> == <…STOCK_REPORT_ITEM: 'stock_report_item'>` (1 failed / 5 passed — **no other test in the file moves**, which is N-4's claim measured) | yes, exit 0 |

**M-71, M-72 and M-67 were re-run, not cited**, because I edited both test functions and L-23
expires a retained row's mutation when its file changes. Nothing else in the batch was re-armed.

### Table 2 — rows (forward coverage map; only the two rows in scope)

| Row | Observable (boundary → exact outcome) | Test id | Source | What it detects that nothing else did | M-id(s) | Disposition |
|---|---|---|---|---|---|---|
| 13 C4(a) | `GET …/items/{R}/assignments` → A1, A2, A4 listed (A3 absent), **in `created_at, client_id` order**, A4 `resolved_early` | `test_every_non_deleted_state_is_listed_in_created_at_client_id_order` | **strengthened** (fixture + expectation) | A production order key that **drops `created_at`** — three order keys satisfied the previous fixture, so a date-less list would have shipped | RP-1, RP-2, M-71, M-72 · RP-1b `EQUIVALENT` | **ARMED** on the `created_at` term and on the state filter; the `client_id` tiebreaker is `EQUIVALENT` at this boundary (§3, card D-11) |
| 13 C2(a) | `DR(R)` with `quantity_in_queue` drifted to 4 → counters `(0,0,0)` and **one** repair record `{stock_report_item, R, quantity_in_queue, "3", "0", inline:delete_stock_report_item}`, deletion proceeds | `test_a_counter_left_non_zero_is_repaired_to_zero_and_recorded` | **strengthened** (one assertion) | A wrong `target_kind` on the cascade's own repair record — the §6.5 `counter_*` → `STOCK_REPORT_ITEM` mapping, which no other test in the batch reads | M-67, RP-11 | **ARMED** |

### Table 3 — removed or consolidated tests

None. No test was added, deleted, merged or moved.

### Arithmetic (derived, printed, not typed)

- **Rows in scope = 2** = 2 `ARMED` + 0 other dispositions. (The `EQUIVALENT` is a *sub-check* of
  C4(a), recorded inside that row, not a row disposition.)
- **Plan-named mutations in scope, re-run under L-23**: C4(a) declares **2** (M-71, M-72) + C2(a)
  declares **1** (M-67) = **3 declared**. Executed: M-71, M-72, M-67 = **3**. `3 == 3`.
- **Mutation runs total this session**: 7 (3 declared + 4 proofs: RP-1, RP-1b, RP-2, RP-11).
- **Reverse map**: the two test functions I touched are both credited in table 2; no test added,
  so no orphan is possible from this session.
- **Pass-count delta = new − removed = 0 − 0 = 0.** Observed 3739 before and after, which is the
  check.

---

## 3. The one correction I did not implement as quoted (§9 rule 14) — RP-1b

**The prompt says:** "order by `created_at` alone → **must now be red** (green today) … If any of
the first two stays green, the fixture still does not discriminate and you are not done."

**RP-1b stays green, and I am reporting it rather than tuning the fixture until it reddens.** The
cause is not a second sufficient cause in the fixture; it is that **the mutant produces
byte-identical output at the public boundary**. Measured, not reasoned — a diagnostic probe
inside the real test (applied, then removed; see §6) printed, identically on three consecutive
runs and again after I added `EXPLAIN`:

```
sorted   = [LO, MID, HI]                      # ascending client_id
ctid     = [HI, MID, LO]                      # physical order = my UPDATE order
scan     = [LO, MID, HI]                      # what the Sort actually receives
bycreated= [HI, LO, MID]                      # ORDER BY created_at alone
plan     = Sort (Sort Key: created_at)
             -> Index Scan using ix_stock_task_assignments_stock_report_item_id
```

Read together those four lines are the whole explanation:

1. The query reaches the rows through `ix_stock_task_assignments_stock_report_item_id`, not a seq
   scan, so the **sort input is index order**, not physical order.
2. My `created_at` back-dating is a **HOT update** — `created_at` is in no index — so the index
   entries still address the original tuples. Index order is therefore **insertion order**
   (`scan = [LO, MID, HI]`), even though the heap order is now `[HI, MID, LO]`.
3. Insertion order **equals `client_id` ascending order** here, because `_CR` performs several
   round trips per assignment, so the ULIDs are minted in distinct milliseconds and are monotonic
   (master plan §10's coin flip applies within one millisecond, which this fixture never hits).
4. Postgres's sort is stable at this size, so the tied pair leaves the sort in the order it
   arrived — **`client_id` ascending** — with or without the `client_id` term.

So `ORDER BY created_at` and `ORDER BY created_at, client_id` return the same list for every
fixture I can build from `CR` at this boundary. That is the doctrine definition of an
**equivalent mutant**, and doctrine's instruction is explicit: record it with the reason and move
on, **never write a test to kill it**.

**The one thing that would have forced a red, and why I refused it.** I could make the back-dating
UPDATE non-HOT by also touching an indexed column; the new index entries would then be ordered by
the new heap TIDs, the sort input would become my chosen order, and RP-1b would go red. That test
would be discriminating with respect to **Postgres's storage behaviour**, not with respect to our
contract; it would break on a plan change that is not a defect, and it would teach the next reader
that the tiebreaker is observable when it is not. I judged that gaming the instrument and did not
do it. Card **D-11** puts the choice where it belongs.

**What is *not* affected:** the defect S-1 was actually about — "a change that dropped the date
entirely would ship unnoticed" — **is closed.** RP-1 is red.

---

## 4. Closing stamp (L4)

| | |
|---|---|
| Command | `BEYO_TEST_SLOT=dt2 PYTHONPATH=. pytest -m 'not e2e'` from `app/` |
| Tree | HEAD `19bbb62` + the two test files and `plans/plan_13.md` (the tree this handoff hands over; committed at §8) |
| Result | **24 failed / 3739 passed / 1 skipped**, 75.1 s |
| Failure IDs **observed but not in the baseline** | exactly **1**: `tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py::test_the_priority_record_snapshots_the_live_awaiting_counter` — **the declared card D-5 witness**, expected red, not touched by me |
| Failure IDs **in the baseline but not observed** | **0** (empty) |
| Baseline comparator | `handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`, 23 IDs (21 published + the 2 slot-sensitive isolation IDs) |
| Pass reconciliation | 3739 before, 3739 after; delta 0 = 0 new tests − 0 removed |

`24 = 23 baseline + 1 declared witness`, `0` unexplained reds. **The stamp was taken twice** —
see §7 item 3.

---

## 5. Production diff is empty

```
git status --porcelain -- app/ | grep -v "app/tests/"      # → no output
git diff --name-only b6cbbb9..HEAD -- app/beyo_manager app/migrations app/scripts | wc -l   # → 0
```

Both run on the handed-over tree, after every probe was reverted.

---

## 6. Write perimeter

**Files I changed (my perimeter — committed):**

```
app/tests/integration/services/queries/stock_report/test_list_stock_task_assignments.py
app/tests/integration/services/commands/stock_report/test_delete_stock_report_item.py
docs/architecture/under_construction/implementation/stock_report/plans/plan_13.md            (Review log, verification half only)
docs/architecture/under_construction/implementation/stock_report/handoffs/tester/2026-09-22_batch_D1_fix_verification_1_handoff.md
```

**Files a probe touched and that are byte-identical again (listed separately, none committed):**

```
app/beyo_manager/services/queries/stock_report/list_stock_task_assignments.py      (RP-1, RP-1b, RP-2, M-71, M-72)
app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py (M-67, RP-11)
app/tests/integration/services/queries/stock_report/test_list_stock_task_assignments.py (the §3 diagnostic probe — 5 runs)
```

Each production probe was reverted with `git checkout --` and confirmed by `git diff --quiet`
(exit 0), printed at the time of each revert. The **diagnostic probe lived inside a file I was
also legitimately editing**, so `git checkout --` could not separate it from my intended change:
before applying it I copied the edited file to the session scratchpad
(`…/scratchpad/c4a_test_backup.py`) and restored from that copy, then verified `grep -c PROBE` → 0
and re-read the full diff. Flagging the mechanism because it is the one revert in this session
that git did not witness.

**Not touched:** any plan criterion cell, the master plan, the tracker, any other role's prompt or
handoff, and `test_stock_report_priority_and_ordering.py` (the witness test's file).

---

## 7. What I could have hidden, and am reporting

1. **RP-1b stayed green** and the prompt told me that means I am not done. I could have made it red
   by forcing a non-HOT update and said nothing about why it worked. §3 is the whole measurement
   instead, including the trick I refused. If the owner or reviewer disagrees with the judgment,
   the fixture change to force it is three lines and I will make it.
2. **My first version of the fixture comment asserted something my own measurement disproved** —
   it claimed "ordering by `created_at` alone yields [HI, MID, LO] and fails too", written from
   the design I *expected* before I probed. It survived into the file for one edit cycle and I
   caught it only because I re-read my own diff before committing. A comment is not a test, but a
   false claim beside a fixture is exactly how the next session inherits a wrong premise. It is
   corrected in the shipped file and the correction is why the L4 was taken twice.
3. **I took the L4 stamp twice** (75.4 s + 75.1 s). The first was valid; then I changed that
   comment, which changed the tree the stamp describes, so I re-took it (charter: a session that
   invalidates its own stamp re-takes it, and the re-take is not over-budget). Both runs returned
   the identical count and the identical ID diff.
4. **I ran two L1 commands twice for no new evidence.** In the RP-1 run and again in the M-71 run I
   issued the same pytest command a second time to read the assertion text after reading the
   summary line, instead of capturing both in one pass. Two duplicate runs, ~4 s, no variation,
   no pre-run authorization line — by the charter's own symmetry rule that is over-evidence and a
   finding against this session. It is small; it is still the rule.
5. **The diagnostic probe cost 5 test runs** (3 identical repeats to confirm the tie order was not
   a flake, then 2 more as I added `EXPLAIN` and the scan-order query). The 3 repeats were the
   deliberate part — the reviewer's own S-1 finding rested on repeating a run whose result could
   have been a coin flip, and I was measuring exactly that class of non-determinism. I would
   defend the 3; the 2 extra iterations are just me not designing the probe in one go.
6. **I did not re-run anything else in the batch** — no other row's mutations, no second mutant
   shape at the ordering site (a reversal of one term only), no L2/L3. The reviewer's variation
   budget is unspent everywhere outside these two rows; §9 says where it buys the most.

---

## 8. Proposed plan-cell backfills (the coordinator folds these; I did not)

| Cell | Proposed addition | Evidence |
|---|---|---|
| plan 13 **C4(a)** | a third named mutant beside the two state-filter ones: *`list_stock_task_assignments.py` (def.): drop `created_at` from the `.order_by`, leaving `client_id` alone → the list comes back in id order and the constructed expectation fails* | RP-1, red on this tree |
| plan 13 **C4(a)** — note, not a mutant | *the `client_id` tiebreaker is not observable at this boundary (equivalent mutant, measured 2026-09-22); the reviewer's structural check is that the `.order_by` carries both terms* | RP-1b, §3 |
| plan 13 **C2(a)** | a second named mutant: *`_delete_stock_report_item_cascade.py` (def.): `target_kind=STOCK_REPORT_ITEM` → `HISTORY_RECORD` → the record's kind assertion fails, and nothing else in the file moves* | RP-11, red on this tree |

## 9. Variation I did NOT spend — where the reviewer's budget buys something new

- **A one-term reversal at the ordering site** (`created_at.desc(), client_id.asc()`). I ran the
  full reversal (RP-2) and the two drops; a single-term reversal is a different mutant shape at
  the same site and I deliberately left it — doctrine forbids me a second mutant of the same sign,
  and it is the reviewer's to spend if it wants one more shape there.
- **The ordering row at the HTTP boundary.** Every run of mine is at the service boundary the cell
  names. Whether the router preserves list order is untested by me.
- **`target_kind` at the *other* two cascade repair sites** (`_goal_credit.py`,
  `repair_stock_report.py`). Those have their own tests and are out of my two-item scope; I did
  not check whether their mappings are pinned as well as this one now is.
- **Anything in plan 12**, and every other plan 13 row. Untouched, and their round-1 ledger rows
  stand on a matching tree.

## 10. Candidate criteria

None. The `target_kind` gap was already a declared finding, and the tiebreaker question is card
D-11 rather than a new row, because writing the row would oblige someone to write the test §3
shows cannot exist.
