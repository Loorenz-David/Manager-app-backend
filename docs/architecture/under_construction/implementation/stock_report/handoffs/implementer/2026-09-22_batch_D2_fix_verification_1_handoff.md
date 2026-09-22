---
batch: D2
phases: [13A, 14]
plan: plan_13A.md, plan_14.md
role: fix (verification)
round: 1
state: IMPLEMENTED
date: 2026-09-22
actor: implementer (Opus, slot `d2f`)
checkpoint: 2303203
tree: 2303203, `git status --porcelain` clean at the stamp
---

# Batch D2 — verification fix round 1. B1, S1, S2 + notes N2/N3/N5/N6.

**All three review-1 verification findings are fixed and measured. No production code changed:
`git diff --name-only -- app/beyo_manager/` is EMPTY at close.** L4 **23 failed / 3798 passed /
1 skipped** at `2303203`, both ID diffs against the checked-in 23-ID baseline empty, pass count
unchanged because this round adds **zero** new test functions.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. **This is a claim, so here is its basis:** the three findings routed to me
were `verification`, all were fixable inside the two test files, and none needed an authority I do
not have. Everything I found that I could not settle myself is a **criteria-cell edit**, which the
prompt reserves for the orchestrator — those are in §6 as proposed text, not as owner questions.
Owner card 1 (finding S3, the lock-order window) was ruled **"file it"** by the owner in `cc5277b`
before I started; I did not touch it, work around it, or mention it in any test.

## 1. Gate check

| Gate | Result |
|---|---|
| Intention `status: RATIFIED` | **PASS** — `planning/intention.md` header, round 9 ratified 2026-09-19; rounds 10/11 additive-and-corrective by owner ruling, status unchanged |
| Predecessor APPROVED | **PASS** — phase 13 **VERIFIED** (D1 approved at re-review 1) |
| My phase at the expected state | **PASS** — 13A `CHANGES_REQUESTED`, review 1 handoff present with three `verification` routes |
| Scope authority | prompt + review §5; no criteria table edited, no other phase's tracker row touched |

**Foreign commit stream during my session, recorded because it moves tree identity.** HEAD was
`fd289f8` when I started and `84c4ff9` when I finished reading: the orchestrator committed
`cc5277b` (the S3 ruling, tracker, this round's prompt) and `84c4ff9` (the frontend wiring guide).
`git diff --name-only fd289f8..84c4ff9 -- app/` is **empty**, and neither document is a root of
plan 14's docs guard (`_CURRENT_HANDOFF` is `handoffs/to_frontend/HANDOFF_TO_FRONTEND_stock_report_api_20260922.md`,
not the wiring guide), so no test's inputs moved under me.

## 2. Write perimeter — cycle-scoped, not phase-scoped

**Changed by this fix (3 files):**

| File | What |
|---|---|
| `app/tests/integration/services/commands/stock_report/test_process_stock_demand_deleted.py` | B1, S1, S2, N2, N3 + the `Space` fixture handle |
| `app/tests/unit/docs/test_stock_report_docs.py` | N5 (`rglob`), N6 (three non-emptiness guards) |
| `docs/.../plans/plan_13A.md` | Review log entry (appended; no criterion cell touched) |

**Changed after the stamp (1 file, not a test root):**
`docs/.../master_plan.md` — my own 13A tracker row only, verified as a **one-line** diff
(`git diff --numstat` → `1 1`). Plus this handoff, which is a new file.

**Production: nothing.** `git diff --name-only -- app/beyo_manager/` → empty.

**Files a mutation probe touched (applied and reverted, listed separately so "no production
changes" stays falsifiable).** `git diff --quiet -- app/beyo_manager/` exit 0 verified after each:

- `app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py`
- `app/beyo_manager/services/commands/stock_report/process_stock_demand_deleted.py` (3 probes)
- `app/beyo_manager/services/commands/stock_report/_remove_assignment.py`
- `app/beyo_manager/services/commands/stock_report/_ordering.py` (2 sitings)
- `app/beyo_manager/services/commands/reset/phases/delete_stock_report_items.py`
- `app/beyo_manager/services/commands/stock_report/requests/__init__.py`
- the two test files above, probed as fixture permutations and restored byte-for-byte

**No other state:** no DB migration or manual DML (every probe ran through pytest on slot `d2f`,
tests own their teardown), no schema change, no archgraph write — **and no archgraph delta is owed,
because no production symbol, boundary or orchestration changed.** No run overlapped another, on
this slot or any other (L-50).

## 3. The three findings

### B1 (blocking) — C5(b) can no longer go red on a healthy build

**New assertion.** Both candidates are minted first into `candidates = {client_id: (properties,
wood_type)}`; then `row_r, row_c = sorted(candidates)` decides which identity plays R (position 2,
reached first by the ascending-`client_id` cascade loop) and which plays C (position 3), the way
`test_c5c` already does for `row_x, row_y`. The premise is stated before the act:

```python
row_r, row_c = sorted(candidates)
assert row_r < row_c, "the cascade loop must reach R before C"
```

The row's outcome clauses are unchanged — `orders[A] == 1`, `orders[D] == 2`, R's deleted row keeps
`priority_order 2` and C's keeps `priority_order 2` — and C is still a candidate *after* another
candidate in the same group, so the "shifted before its own deletion" clause survives.

**The re-ordering probe, as the prompt required.** Reversing the mint order (so the other identity
is minted first), positions and request order unchanged: **green, 1 passed**. A decidability
assertion inside the probe confirmed the swap really flipped which identity plays R
(`candidates[row_r][0] == {"wood_group": ["light"]}` — under the shipped order it is `teak`). The
flake is gone: the test no longer depends on which millisecond two ULIDs land in.

**And the pin is load-bearing, not decorative.** Inverting it (`row_c, row_r = sorted(candidates)`)
reproduces the reviewer's exact failure:

```
.../test_process_stock_demand_deleted.py:1319: assert 3 == 2
FAILED ...::test_c5b_two_rows_of_one_group_each_close_their_own_gap
```

**Reported because I could have hidden it: the probe found a second unpinned coupling — in my own
repair.** The two candidates' *items* still carried wood types bound to the old positional roles
(`Teak` for the position-2 row, `Oak` for the position-3 row). Once R is chosen by id, that binding
is wrong half the time, and under the swapped-mint probe the fixture died with
`StockAssignmentPropertyMismatch` (MC-12) at `create_stock_task_assignments.py:141` before reaching
a single assertion. Each candidate now carries its own MC-12-matching wood type beside its
properties. **Running the probe is what caught it; re-reading my own diff would not have** — the
repair looked complete and the suite was green.

### S1 — C3(a) now reads every history record, and counts them

**New assertion.** Before the act the row snapshots **all** of R's history records by `client_id`
(new helper `_history_records`, replacing the single-type `_goal_record` read), asserts which kinds
are present, that the count is what the fixture produces, and that every one is live. After the act:

```python
history_after = await _history_records(env.session, row_id)
assert set(history_after) == set(history_before)
assert len(history_after) == len(history_before)
for record in history_after.values():
    assert record.is_deleted is True, record.type
    assert record.deleted_at == NOW, record.type
    assert record.deleted_by_id is None, record.type
```

**Mutation observed red** — the reviewer's own mutant, `StockReportHistoryRecord.type ==
"quantity_requested_change"` added to the cascade's history soft-delete
(`_delete_stock_report_item_cascade.py:205-212`, definition site):

```
.../test_process_stock_demand_deleted.py:974: AssertionError: <StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE: 'priority_change'>
FAILED ...::test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited
1 failed, 32 passed in 14.62s
```

Review 1 measured this same mutant leaving **33 phase tests, 6 neighbouring tests and 495
stock-report tests all green**. It now reddens exactly one row — C3(a), the row that promises it.

**Correction to the finding's premise, measured, not assumed: R carries TWO history kinds, not
three.** The fixture yields `quantity_requested_change` and `priority_change` — there is **no**
`priority_order_change` record. Cause: `_seed_group` appends the rows with
`set_stock_report_item_priority` **in the wanted order**, so every row is already at its wanted
position by the time `set_stock_report_item_priority_order` runs, and each of those calls is a
no-op that writes no history record. §6's stated seeding procedure ("then moved into place with
`set_stock_report_item_priority_order`") is therefore **inert in every row that uses it**. This does
not weaken the fix — two kinds is "more than one X", and the mutant reddens on the second kind —
but the cell, and review 1's lesson 3, both say "three". Cell text proposed in §6.

### S2 — C5(e)'s foreign workspace holds the cell's shape, and it discriminates

**What was built.** The fixture kit gained a `Space` handle (identity, workspace, category,
manager); `_AD`, `_make_row`, `_make_pair`, `_CR`, `_move`, `_assignment_on`, `_seed_group` and
`_seed_six_assignment_row` each take `space=`, defaulting to W — **so no other row's behaviour
changed**. C5(e) now seeds W′ with the cell's shape through the shipped commands: the same row
through `AD`, the same `A1 R2 C3` group through the phase-12 priority commands, the same **six**
assignments through `CR` plus the state moves. The row then asserts W′'s counters, goal total,
group orders, six live assignments, six task flags and live history records as unchanged — not just
its divergence list.

**One necessary deviation, declared (charter rule 14).** W′'s row carries `wood_group: ["light"]`,
not `["teak"]`. The `env` fixture's cross-workspace reference row (C2(f)) already occupies the
default identity in W′, and `apply_stock_demand` mints no second live row for an existing identity
— `_make_row` would assert on the empty event list. The cell asks for the same **shape**, which is
what the control exists to hold; the identity *tuple* could never be identical across workspaces
anyway, which is precisely why the cell's second mutant was retired as inert (implementer F-3).

**Mutation observed red** — a gap close that loses its workspace term (`_ordering.py:close_priority_gap`,
definition site; APPROVED phase-12 code, probed and reverted, never edited):

```
.../test_process_stock_demand_deleted.py:1499: AssertionError: assert [{'client_id'...ensity', ...}] == []
FAILED ...::test_c5e_the_consistency_check_stays_empty_in_both_workspaces
1 failed, 32 passed in 14.08s
```

Line 1499 is the **W′** divergence assertion, and the divergence kind is `order_density` — W′'s
group renumbered by W's delete. Nothing else in the phase notices.

**And the counterfactual, which is the whole point of the finding.** The same mutant, run against
C5(e) as it stood before this round (W′ = one bare row):

```
1 passed in 2.05s
```

**Invisible.** The control was decoration; it is now an instrument.

## 4. Notes N1–N7 — disposition

| Note | Route | Disposition |
|---|---|---|
| **N1** C1(d) | plan | **Declined — none needed.** The reviewer's own text says "no action needed beyond the record"; the class is covered by C1(j)/C1(k). |
| **N2** C6(a), C6(b) | verification | **Applied.** C6(a) gains `assert_stock_report_clean` **and** `_assert_foreign_untouched`; C6(b) gains the clean check. Not separately mutation-probed: these are §6's standing close, not guards I authored, and M36 (§5, row 5) shows the clean check reddening across five other rows. |
| **N3** C5(f) | verification | **Applied**, as a before/after snapshot of all four MC-9 tables for W′ (`_foreign_table_counts`). **Stated plainly rather than dressed up:** three of the four are `0` in that fixture, so only the `stock_report_items` count (1 → 1) is load-bearing there. Probed anyway — dropping the workspace filter from `reset/phases/delete_stock_report_items.py` reddens the new clause at line 1591. |
| **N4** C1(i) | plan | **Declined — cell edit, the orchestrator's.** Proposed text in §6. |
| **N5** 14 C1(b) | verification | **Applied**: `_STOCK_COMMANDS.glob` → `rglob`. **Measured both ways**: with an `event_name=` site planted in the `requests/` subpackage, `rglob` reddens C1(b) (`missing from the handoff: stock_report_item:probe`) and `glob` stays green (13 passed). The gap was real and latent, not hypothetical. |
| **N6** 14 C1(b), C1(c) | verification | **Applied** as non-emptiness guards on the three scans. Asserted as *contracts, not counts* (charter rule 13 — C1(a)'s `== 13` and C1(d)'s `== 6` are the time-bomb shape I did not copy). Each proven able to fire, and **separately** (charter rule 12): emptying all three reddens C1(b) + both C1(c) parametrizations; emptying only `_message_identities` still reddens C1(c) on its second sub-check. |
| **N7** handoff arithmetic | plan | **Declined — the orchestrator's record.** Confirmed the reviewer's reading: the "C5 10" parenthetical sums to 11 because it counts runs while the total counts declarations, and the ledger's ID gaps are numbering only. |

## 5. Mutation ledger — 13 runs, all reverted

Scope **L1** throughout (the phase's own test file, or the docs test file): every hypothesis here is
"does this named test redden under this named mutation", which is what L1 is the default for. Tree
for every row: `84c4ff9` + this round's two test-file edits, i.e. the content that became
`2303203`; `git diff --quiet -- app/beyo_manager/` exit 0 after each revert.

| # | Row | Site (file, def. vs call site) | Mutation | Observed | Reverted |
|---|---|---|---|---|---|
| 1 | **C3(a)** / S1 | `_delete_stock_report_item_cascade.py:205-212` (def.) | history soft-delete narrowed to `quantity_requested_change` | `test_c3a` **red** at `:974`, `AssertionError: PRIORITY_CHANGE` — 1F/32P | `git checkout --`, `--quiet` exit 0 |
| 2 | **C5(b)** plan mutant (i-r) | `process_stock_demand_deleted.py:237` (def.) | cascade the **first** candidate only | `test_c5b` **red** at `:1318` `assert 3 == 2` (`orders[D]`), `test_c5c` red — 2F/31P (matches round 1's M31) | `--quiet` exit 0 |
| 3 | **C5(b)** / B1 | `process_stock_demand_deleted.py:237` (def.) | cascade loop **descending** `client_id` | `test_c5b` **red** at `:1320` `assert 3 == 2` — **C's own `priority_order` clause**, the one B1 is about — 1F/32P | `--quiet` exit 0 |
| 4 | **C5(b)** plan mutant (iii) | `process_stock_demand_deleted.py:210-219` (def.) | class-4 and class-5 locks moved **inside** the per-row loop | `test_c5b` **red** at `:1349` `assert 2 == 1` — the `stock_report_items` `FOR UPDATE` count clause — 1F/32P | `--quiet` exit 0 |
| 5 | **C5(e)** plan mutant 1 (M36) | `_remove_assignment.py:21` (def.) | `recompute_task_stock_flag` skipped | 6F/27P incl. `test_c5e` **red** at `:1498` (`task_flag`, the **W** half) — matches round 1 | `--quiet` exit 0 |
| 6 | **C5(e)** / S2 — **mis-sited, declared** | `_ordering.py:_group_where` (def.) | `workspace_id` term dropped | `test_c5e` red at `:1498` — **the W half, not W′**. `_group_where` also serves `append_to_priority_group` and the phase-12 order commands, so the probe broke W's own seeding. **Re-sited** → row 7. | `--quiet` exit 0 |
| 7 | **C5(e)** / S2 | `_ordering.py:close_priority_gap` (def.) | the **gap close alone** loses its `workspace_id` term | `test_c5e` **red** at `:1499` — the **W′** divergence assertion, kind `order_density` — 1F/32P | `--quiet` exit 0 |
| 8 | **C5(e)** / S2 counterfactual | row 7 + C5(e) reverted to the bare-row W′ | — | **1 passed** — the mutant is invisible to the old control | production + test both restored |
| 9 | **C5(f)** / N3 | `reset/phases/delete_stock_report_items.py` (def.) | workspace filter dropped | `test_c5f` **red** at `:1591` on the new four-table clause | `--quiet` exit 0 |
| 10 | **14 C1(b)** / N5 | `stock_report/requests/__init__.py` (new `event_name=` site) | plant an event name in the subpackage | C1(b) **red**: `missing from the handoff: stock_report_item:probe` — 1F/12P | `--quiet` exit 0 |
| 11 | **14 C1(b)** / N5 counterfactual | row 10 + `rglob` reverted to `glob` | — | **13 passed** — the subpackage site is invisible under `glob` | both restored |
| 12 | **14 C1(b), C1(c)** / N6 | `test_stock_report_docs.py` (the three scan helpers) | each returns `set()` | C1(b) **red** `the \`event_name=\` scan found nothing`; C1(c)×2 **red** `the error-class scan found nothing` — 3F/10P | restored |
| 13 | **14 C1(c)** / N6, second sub-check | `test_stock_report_docs.py:_message_identities` | returns `set()` alone | C1(c)×2 **red** at `:374` `the message-identity scan found nothing` — 2F/11P (rule 12: the second sub-check bites on its own mutation) | restored |

**Plus two test-side fixture permutations for B1** (§3): the mint-order swap (**green**, with an
in-probe assertion confirming the flip landed) and the inverted pin (**red**, `assert 3 == 2`).

**Retained rows whose citation I did not re-run, and why.** I edited `test_c3a`, `test_c5b`,
`test_c5e`, `test_c5f`, `test_c6a` and `test_c6b`. Rows 1–9 above re-run every round-1 mutation
whose observed red was inside one of those six tests (M31, M33, M36) plus the new ones. The
remaining round-1 mutations (M2, M7, M8-r, M17, M26, M30, M34, M35, M38, M39/M40 …) were observed
red in tests I did **not** touch; the only change reaching them is additive helper plumbing with
W-defaulting arguments, which alters no assertion in those rows. **M38 is the one edge case** — it
reddens `test_c5f`, whose assertions I did change — and row 9 above is a mutation at the same site
class on that same test, so its bite is re-demonstrated on the edited tree.

## 6. Proposed cell text — for the orchestrator to apply (I edited no criteria table)

1. **C5(b) — B2's cell edit.** Replace *"C's deleted row keeps `priority_order` 2 (it was shifted
   3 → 2 by R's cascade before its own deletion)"* with: *"the fixture mints both candidates and
   assigns the roles from the minted ids (`sorted()`): **R is the lower `client_id`** and takes
   position 2, C the higher and takes position 3, so the ascending cascade loop reaches R first.
   R's deleted row keeps `priority_order` 2; C's deleted row keeps `priority_order` 2 (shifted
   3 → 2 by R's cascade before its own deletion). Each candidate's item carries a wood type
   matching its own row's criteria (MC-12), since which identity plays R is not fixed in advance."*

2. **C3(a) — the history clause.** Replace *"every history record of R soft-deleted with NULL
   author"* with: *"**every** history record of R — the fixture produces **two**
   (`quantity_requested_change`, `priority_change`); it produces no `priority_order_change`, because
   `_seed_group` appends in the wanted order and the order command is then a no-op — each
   `is_deleted`, `deleted_at == ctx.now`, `deleted_by_id IS NULL`, with the id set and count
   asserted unchanged across the act."* Named mutation: *"narrow the cascade's history soft-delete
   to `type == QUANTITY_REQUESTED_CHANGE` → the `priority_change` record survives on a deleted row
   → red."*

3. **C5(e) — the W′ fixture and its second mutant.** Fixture cell: *"…and the same for W′, seeded
   with the same shape — the same row through `AD`, the same `A1 R2 C3` group through the phase-12
   commands, the same **six** assignments through `CR` plus the state moves — untouched. W′'s
   `wood_group` differs (`light`), because the C2(f) reference row already holds the default
   identity in W′ and `AD` mints no second live row for an existing identity; the cell asks for the
   shape, and the identity tuple cannot be identical across workspaces in any case."* Replace the
   retired second mutant with: *"`_ordering.py:close_priority_gap` (def.) — drop the `workspace_id`
   term from the gap close → W′'s group is renumbered by W's delete → C5(e) reddens on W′'s
   `order_density` divergence. **Measured 2026-09-22: invisible to the previous bare-row W′.**"*

4. **§6 preamble — the inert half of the seeding procedure.** *"…then moved into place with
   `set_stock_report_item_priority_order`"* is a **no-op as written**, because the append loop
   already runs in `ordered_ids` order. Either drop the clause, or change `_seed_group` to append in
   a different order than it places — which would also give every seeded row a
   `priority_order_change` history record. **Not made here: it is a fixture change touching C3(a)
   through C3(d) and C5(e), and it belongs to plan authorship.**

5. **N4 — C1(i)'s cell** still reads `"seven"` while the integration test sends `5`; one line in the
   cell saying the unit half is what arms the row.

## 7. Tests I wrote → the row each aimed at

**No test function was added or deleted this round** (pass count 3798 → 3798 confirms it). Every
change is a widened assertion or a helper serving one:

| Change | Row |
|---|---|
| `candidates` / `sorted()` role assignment + `assert row_r < row_c` in `test_c5b` | 13A C5(b) |
| per-candidate wood type in `test_c5b` | 13A C5(b) (MC-12 precondition of the same fixture) |
| `_history_records` + the before/after history block in `test_c3a` | 13A C3(a) |
| `Space`, the `space=` arguments, the W′ control and its assertions in `test_c5e` | 13A C5(e) |
| `_foreign_table_counts` + the four-table clause in `test_c5f` | 13A C5(f) (N3) |
| `assert_stock_report_clean` / `_assert_foreign_untouched` in `test_c6a`, `test_c6b` | 13A C6(a), C6(b) (N2) |
| `rglob` + three non-emptiness guards in `test_stock_report_docs.py` | 14 C1(b), C1(c) (N5, N6) |

No orphan test, no candidate criterion proposed, none owed. Every helper added has a caller in the
same round (charter rule 4).

## 8. L4 — one stamp, both ID diffs

**Authorization, written before the run:** L4 scope **(a)**, the one authoritative clean stamp
closing this fix cycle. Narrower evidence is insufficient because the hypothesis — "nothing in the
repository regressed" — is repository-wide by construction.

```
$ cd app && BEYO_TEST_SLOT=d2f PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q
23 failed, 3798 passed, 1 skipped, 2 warnings in 80.50s (0:01:20)
```

Tree identity: **`2303203`**, `git status --porcelain` **empty** at the stamp,
`git diff --name-only -- app/beyo_manager/` empty.

```
$ comm -23 observed.txt baseline.txt     # observed-not-in-baseline
(empty)
$ comm -13 observed.txt baseline.txt     # baseline-not-observed
(empty)
baseline: 23   observed: 23
```

against `handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`. **Both diffs empty.**

**Pass-count reconciliation:** 3798 → 3798, unchanged, because this round adds **zero** test
functions — exactly what the prompt asked me to say if the number moved, said here because it did
not.

**Lint:** `ruff check` clean on both changed files.

**Reported because I could have hidden it — one avoidable L4.** I piped the stamp run through
`tail -5`, which discarded the failing IDs I needed for the diffs, so I ran the suite a **second**
time on the byte-identical tree purely to capture them. That is over-evidence by the charter's own
definition (~80 s), and it was avoidable with one `tee`. Both runs reported
`23 failed / 3798 passed / 1 skipped`; the stamp above is the first, and the ID set is the second's
— identical tree, so the citation is valid, but the run should not have been needed.

## 9. For the coordinator

- **Apply the five cell edits in §6** before compiling the re-review prompt; three of them
  (C5(b), C3(a), C5(e)) are where review 1's corrections and the measured fixture disagree.
- **§6's seeding procedure is half inert** (§6 item 4). It is not a defect in any shipped row, but
  it is the reason S1's "three kinds" was two, and the same shape could mislead a future row that
  wants a `priority_order_change` record to exist.
- **Phase 14's tracker row** is not mine to move, but N5 and N6 — its only two open notes — are
  applied and armed in this round's commit.
- Master plan §9 could earn a rule from B1's second half: **a fixture that assigns roles from
  minted ids must move every role-dependent value with the role.** Pinning the order is half the
  job; the `wood_type` left behind made the repaired fixture crash, not fail, and only under a
  permutation nobody would have run without the prompt demanding it.
