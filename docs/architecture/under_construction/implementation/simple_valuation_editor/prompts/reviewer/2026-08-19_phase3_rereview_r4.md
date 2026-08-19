---
plan: 3
role: reviewer
round: 4
date: 2026-08-19
project: simple_valuation_editor
kind: re-review — delta-scoped, narrow
---

# Session prompt — re-review r4, phase 3 (`simple_valuation_editor`)

## 1. History, and what is closed

**r1**: `CHANGES_REQUESTED`, 0 blocking / 3 should-fix / 6 notes. **All seven criteria MET.**
**r2** (fix): the three should-fixes applied verbatim, both coordinator amendments included.
**r3** (fix): two coordinator findings on r2's own newly-landed comment text.

**Closed and not re-opened**, each verified independently by the coordinator on the shipped
tree rather than read off a ledger:

- **F-2's central claim.** With both `SET LOCAL` statements deleted, dropping
  `superseded_at.is_(None)` still reddens exactly `test_phase3_c1_…` across the whole suite —
  one ID added, none removed. **Five independent measurements now agree the planner GUCs did
  nothing**; F-2's STOP condition did not fire.
- **E1, across both fix rounds combined.** `git diff -U0 ef55f6d -- get_task_price_scenario.py`
  filtered of comment lines is **empty**. Twenty-odd comment lines changed; **zero executable
  lines in production code across the entire fix history.**
- **G-2's mutation, re-measured whole-suite by the coordinator**: dropping
  `ItemValuation.is_deleted.is_(False)` reddens exactly
  `test_phase3_g2_soft_deleted_valuation_is_hidden_from_the_price_screen`, one ID added, none
  removed.
- **G-2's load-bearing consequence, isolated.** The coordinator neutralised the row's first
  two assertions and re-ran the mutant: `assert result["can_commit"] is False` fails with
  `assert True is False`. **The deleted valuation really does readmit commit** — the failure
  the finding predicted, observed directly rather than inferred from a red test.
- **E2's deviation is correct and better than the criterion asked for.**
  `serialize_task_price_scenario` (`serializers.py:294-315`) builds `saved_payload` wholesale
  and sets it to `None` in the `else`, so `assert result["saved"] is None` strictly dominates
  three sub-field null checks — which would have been assertions that cannot fail.
- Ruff check and format clean; suite **26 / 2431 / 1** with failure IDs byte-identical;
  focused file 50/50.

## 2. The delta you are reviewing

Small, and deliberately so.

| # | Change | File |
|---|---|---|
| **G-1** | One clause in the F-3 accepted-duplication comment: `TaskBudgetStatus` "carries item_id and no objects" → "carries item_id and the evaluation result but none of the objects re-read here — not the Task, the Item, the selection, the terms or the valuation" | `get_task_price_scenario.py` |
| **G-2** | One new integration row, `test_phase3_g2_soft_deleted_valuation_is_hidden_from_the_price_screen`, ~135 lines, self-contained (no shared fixture — E4 answered "not shared", so C1's mutation was correctly **not** re-measured) | `test_price_scenario_query.py` |
| **coordinator** | A one-line reflow of G-1's paragraph — the verbatim splice left a ragged short line. **The implementer flagged it and correctly declined to fix it**, since reflowing prose issued verbatim is the error this project has ruled worse. Comment-only; E1 re-verified after it. | `get_task_price_scenario.py` |

## 3. Probes

### P1 — attack the new prose. This is the round's central instruction.

**Phase 3's last two rounds were both opened by defects in the previous round's replacement
text**, not by defects in code:

- r2 fixed a comment nobody could *resolve* (`(C10)`) and shipped a comment nobody had
  *verified* (`is_deleted` called load-bearing with no test behind it).
- r2's F-3 text asserted "no objects" about a dataclass carrying `result: ItemCostResult | None`
  — the review's own C6 row had the qualification and the replacement lost it.

Both were caught by the coordinator, who also wrote or amended the text in question. **So the
prose now in the tree has had one reader, and that reader is not independent.** You are the
second.

Read every comment in the delta as a **claim under rule 2**, and check the claims that are
checkable:

- G-1's replacement now enumerates five things `TaskBudgetStatus` does *not* carry. **Open the
  dataclass and count.** Is the enumeration complete and correct, or has a fix for a
  false-by-omission sentence produced a false-by-enumeration one? This is the exact defect
  shape the phase has now produced twice.
- The new row's three inline comments make three assertions about mechanism: that
  `delete_item_valuation` leaves `superseded_at` null; that
  `uix_item_valuations_current`'s partial predicate makes the fixture legal; and that
  "task ASSIGNED, selection OK, currencies agreeing and no purchase term leave
  valuation-presence as the only false conjunct". **The third is the interesting one** — verify
  it against `_scenario_objects()`'s actual defaults rather than against the sentence.
- F-1's surviving clause still says *"The three predicates below this one are load-bearing."*
  G-2 closed the third. **Are all three now genuinely asserted?** `item_id` is the one nobody
  has probed. If dropping it reddens nothing, the sentence is still one-third unverified and
  that is a finding — the same finding, a third time.

### P2 — the new row against the standard C1 was held to

C1 went through the review that produced this phase's sharpest finding. Hold G-2's row to it:

- Rule 11½: teardown in `try/finally` naming its tables, residue outside. Confirm both halves.
- **Rule 2's companion**: is the row's own predicate the only reason its outcome holds? The
  coordinator isolated `can_commit`; **`result["currency"] is None` has not been isolated.**
  Does it discriminate on its own, or is it carried by the other two?
- The fixture sets `deleted_at` and `deleted_by_id` "as the command sets them". Check that
  against `delete_item_valuation.py`. If the command sets a field the fixture omits, the
  fixture is not the post-delete state it claims to be — which would not change the verdict,
  but would make the comment false.
- Does the row leave residue? Four tables are asserted zero. Are four the complete set,
  given `_scenario_objects()` builds five more objects that are never added to the session?
  (Review r1 verified exactly this for C1 and found it sound; confirm the new row copied the
  property and not just the shape.)

### P3 — the phase as a whole, one pass

You approved all seven criteria at r1 and nothing since has touched behaviour. **Do not
re-derive them.** But read `plans/plan_3.md` §6 (the Review log, written at the r1 fold) once
against the tree, because it now carries three corrections to the plan's own text — the F5
premise, C1's unrecorded second clause, and F4's under-specified fixture guidance. **Are those
three statements true of the code as it now stands?** A Review log that is wrong is worse than
one that is empty, because it is what survives closeout.

## 4. What a finding looks like

Blocking = the endpoint or the evidence is wrong. Should-fix = true but a reader is misled, or
a claim overstates what was measured. Notes = everything else.

**A comment that asserts a property is a claim.** That rule was earned in this phase, one round
ago, on this file. Apply it to the text the fix rounds added.

If the verdict is `APPROVED`, say so plainly and state what phase 3 now guarantees that it did
not before. Three fix rounds is enough; the bar is correct and usable, not perfect.

## 5. Closing protocol

Deposit at `handoffs/reviewer/2026-08-19_phase3_rereview_r4_handoff.md`, charter frontmatter.

State explicitly whether **G-1 and G-2 are each closed**, and whether **E1–E6** hold. Findings
by severity with verbatim replacement text — and if you supply prose, **say so and mark it as
unreviewed**, because §3's P1 exists precisely because reviewer prose has entered this file
twice with no second reader.

Carry-forward table if approving with notes. **Full write perimeter — you write no code and no
handoff but your own.** Do not update the master plan tracker or plan 3's Review log.

## 6. Environment

- Working directory `backend/app/`; `PYTHONPATH=. pytest -m 'not e2e'` (the bare `make test`
  form fails collection with `ModuleNotFoundError: beyo_manager` under some shells; collection
  is otherwise identical).
- Expect **26 / 2431 / 1**. A different count is repeated and **ID-diffed** before any
  conclusion.
- **The drifting test**: ten observations stand — implementer r1b 27, 27; coordinator 26;
  reviewer r1 26; fix r2 26, 26; coordinator 26, 26; fix r3 26, 26 — plus the coordinator's two
  runs this round, both 26. Report whether
  `test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
  appears in yours, and do **not** touch it.
- **The working tree carries an uncommitted owner change** to `purchase_api.py`, its unit test
  and `.archgraph/architecture.yml`, unrelated to this pipeline. **Do not review, revert, stage
  or count it.** It is why the suite reads 2431 rather than 2428.
- **Architecture graph**: the new row inserts ~135 lines after the C1 span, so anchors pointing
  at `test_c14_…` / `test_c16_…` have shifted. Pending `ai_inferred`, coordinator-owned —
  **report drift, repair nothing.** The review path is the only door and it is not yours.
