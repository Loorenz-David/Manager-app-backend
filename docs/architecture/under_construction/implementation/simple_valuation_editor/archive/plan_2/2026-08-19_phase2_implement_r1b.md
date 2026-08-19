---
plan: 2
role: implementer
round: 1b
date: 2026-08-19
project: simple_valuation_editor
supersedes: 2026-08-19_phase2_implement_r1.md
---

# Session prompt — implement r1b, phase 2 (`simple_valuation_editor`)

## 0. Why there is a round 1b

You stopped at the scope gate on two contradictions in `plan_2.md`. **You were right on
both, and stopping was the correct call** — the constraint did its job, for the second time
in this project's history. Nothing was changed; the worktree was clean; the baseline you
verified (2373 / 26 / 1) matches.

**Both contradictions were the coordinator's, and both are now fixed at the source.** Re-read
`plans/plan_2.md`; do not work from the r1 prompt or from memory of it.

1. **`price_scenario.py` was forbidden outright while an exception required a comment in
   it.** §2's blanket line now reads *"No change to any **executable line** of
   `price_scenario.py`"*, and **exception 3** authorizes exactly one comment beside
   `_shape_error` at `:53-57`, naming `calculator.py:124-128`. That is the entire
   authorization for that file — one comment, no executable line, and phase 1's arithmetic
   remains APPROVED and out of scope.
2. **C16 still required the retired call-to-call equality** after §2 had been corrected to
   the exact literal. **C16 now requires the literal**:
   `slider_domain(8_919, 0, 0) == SliderDomain(step_minor=110, min_minor=3_080, max_minor=12_100)`,
   red under `max(1, quantity) → max(6, quantity)` at `slider_domain`'s definition (the
   mutation returns `114 / 3_078 / 12_084`). **Never a call-to-call equality** — `f(0) == f(1)`
   is invariant under that mutation at every `B`, which is the whole reason the row exists.

Neither correction required an owner decision: authorizing the comment writes down a sanction
master plan §4 had already granted, on the same entailment as HC-2's fourth artifact.

**The perimeter is now nine files: the seven in §2's table plus three enumerated exceptions**
(`test_price_scenario.py` — one assertion; `calculator.py` — one comment;
`price_scenario.py` — one comment). Count them off before you finish.

## 1. Everything else is unchanged

The r1 prompt's remaining sections stand in full and are not restated here. Read
**`prompts/implementer/2026-08-19_phase2_implement_r1.md` §§1–11** for role, workspace, gate
check, read order, the five settled projection findings, the three delegations, standing
rules, environment and the closing protocol — **with the two corrections above applied where
they conflict.**

Two of those sections matter enough to repeat:

- **D-7 carries a STOP.** If you serialize router-side, an existing test feeds
  `fake_run_service`'s `{"ok": "test"}` into your serializer and
  `test_item_economics_router.py` needs more than the one authorized row. **Stop and report
  rather than widen the perimeter.** Service-side keeps §2 accurate and has a live precedent
  at `get_task_production_time.py:82`.
- **The assertion-form rule.** A named mutation's check is on the **assertion form**, not the
  fixture. Prefer an exact literal over an equality between two calls. Compute both sides;
  run the **whole file**, never `-k`; record every test that reddens.

## 2. Gate check — re-run it, it has changed

- `plans/plan_2.md` §2 reads *"No change to any executable line of `price_scenario.py`"* and
  enumerates **three** exceptions.
- `plan_2.md`'s C16 requires the **exact `SliderDomain` literal**, not an equality.
- `planning/intention.md` carries **§9.2A**, **§4.4B** and §9A.1's `†` qualification.
- `git status` clean; baseline **2373 / 26 / 1**.

**If any of these is still false, stop again and report.** A second blocker on the same
artifact is a signal about the artifact, not about you.

## 3. Handoff

As r1 §§10–11, at `handoffs/implementer/2026-08-19_phase2_implement_r1b_handoff.md`. Add one
line confirming which files the three enumerated exceptions touched and that no executable
line changed in `price_scenario.py` or `calculator.py`.
