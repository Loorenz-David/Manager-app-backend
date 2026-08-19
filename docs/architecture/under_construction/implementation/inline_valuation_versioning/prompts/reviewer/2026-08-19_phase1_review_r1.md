---
plan: 1
role: reviewer
round: 1
date: 2026-08-19
pipeline: inline_valuation_versioning
---

# Review round 1 — plan 1 (inline valuation versioning)

You are the reviewer (plan-reviewer doctrine,
`/Users/davidloorenz/agent-skills/pipeline-charter.md`). You fix nothing. You verify that
what was built is what the contract specifies, and that every guard can actually fail.
Write perimeter: exactly one handoff file:

`…/inline_valuation_versioning/handoffs/reviewer/2026-08-19_phase1_review_r1_handoff.md`

**Scope is light** per the MVP calibration rule: fifteen lines of behaviour, no
arithmetic, no rounding, no ordering key. The coordinator has already done the checks
listed below — **do not repeat them, extend them.**

## Already verified by the coordinator — do NOT redo

- **Suite, re-run twice independently: 2320 passed / 26 failed / 1 deselected**, 26 unique
  IDs byte-identical to baseline, no duplicates. The implementer's arithmetic (2 removed,
  8 added) reconciles.
- **Perimeter exact.** Checkpoint `6f82579` contains six files — the four HC-1 files plus
  `master_plan.md` and `plans/plan_1.md` — all declared, nothing undeclared.
- **The identity is retired from live surfaces.** `grep` over `app/` and `docs/handoff/`
  returns nothing; it survives in **9** `item_cost_calculation` planning/archive files,
  which are provenance and correctly untouched.
- **C2's named mutation re-applied on the POST-RUFF FINAL FILE** (the implementer probed a
  slightly earlier revision): forcing `should_write_valuation = True` reddens
  `test_c2_…_zero_write_noop` **and** `test_c4_…_zero_write_noop`. C4 biting independently
  is exactly what that row was added for.
- **Revert integrity:** `create_task.py` hashes to the handoff's declared
  `10c5f350bf6d8e624a0bf9f2612510785c77435c1c3f8f69b2acee33f1772986`.
- **The architecture graph is already corrected — do not re-flag it.** The stale claim the
  implementer surfaced has been fixed under owner authorization:
  `node:command-task-create`'s description edited, the `writes_to → table-item-valuation`
  anchor moved 317-353 → 316-367, and the `reads_from → table-item` edge deleted,
  re-recorded with an accurate summary and promoted back to `human_confirmed`. Final
  revision `0f36b07a…`; 183 nodes / 275 edges, pending still 4, 0 diagnostics.

## What to review

1. **The four unprobed criteria.** The coordinator probed C2 only. Apply the remaining
   named mutations at their definition sites — **C3** (pass the request value through
   instead of inheriting) and **C5** (drop currency from the comparison) — plus construct
   your own for **C1** (omit the writer call, or pass a creator other than `ctx.user_id`)
   and **C8** (broaden the trigger). Mutate → observe red → revert → `sha256`. A probe you
   cannot reproduce is a finding.
2. **The precedence-disagreement audit** (master plan §5). For every new fixture, does it
   make each level of what it pins disagree with the others? C2 and C3 each hold for a
   second independent reason — that is precisely why C4 exists. Confirm C4's fixture really
   is *partial input whose inherited field makes the triple identical*, and that C1's
   fixture cannot pass if the creator were wrong.
3. **Nothing loosened, and the deletion accounted for.** `git diff aa95d5e 6f82579 --
   app/tests/` is the whole evidence base. The rejection test was **removed**; per the
   **deleted-assertion rule**, verify the handoff's mapping is honest — each behaviour it
   pinned is either covered by a named new row or **deliberately retired**, and say which.
   A removed assertion is reviewed exactly like a weakened one.
4. **The rewritten §9.1 (C10).** Read it as a frontend developer would. Does it state the
   new behaviour — re-prices, inherits an omitted field, no-ops on identical values, first
   write for an unvalued item, and the deliberate divergence from
   `PUT /items/{id}/valuation` — without asserting the retired refusal anywhere in the
   document? The implementer also changed a generic validation phrase from
   "inline-pricing refusal" to "inline-pricing versioning"; rule on whether that was
   required by C10 or was scope creep.
5. **HC-2 and HC-4, mechanically.** Confirm `write_item_valuation_chain_in_session` is
   still the only code that supersedes or inserts a valuation, and that the no-op path
   writes **nothing at all** — no row, no supersede, no `item_valuation.created` audit.
   "Writes an identical row" would be a different behaviour and is wrong.
6. **Anything built that no criterion covers**, and anything the artifacts left open that
   the implementer settled silently. Their DECISIONS section says "None" — test that claim.

## Environment

From `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`. Start point **2320 / 26 / 1**.

**A single run is not evidence.** On unchanged code this suite has been observed at **25,
26 and 27** failures across separate runs — it drifts in both directions. If your count
disagrees, repeat the run and diff the **ID set**; only an ID added or removed across
repeated runs is a finding. A count alone is noise. The drifting test is inherited and
unidentified. The DB also accrues ~24 `task_steps` per full run from tests outside this
pipeline, so row counts drift too.

## Output

Verdict `APPROVED` or `CHANGES_REQUIRED`, then a numbered ledger (`S<n>` should-fix,
`N<n>` note) with file:line and, for each finding, the mutation that demonstrates it. Add a
criterion → test → mutation table (C1–C10) recording **which test bites on which
mutation**, per the criterion-kind rule.

If everything closes, say so plainly and do not manufacture findings to justify the round.
A clean review is a legitimate outcome. If something does not close, do not soften it
because the fix looks small.
