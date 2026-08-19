---
plan: 3
role: implementer
round: 1b
date: 2026-08-19
project: simple_valuation_editor
supersedes: 2026-08-19_phase3_implement_r1.md
---

# Session prompt — implement r1b, phase 3 (`simple_valuation_editor`)

## 0. You were right to stop, and the cause was outside your perimeter

Your baseline read **2424 / 27 / 1** where the prompt promised 2425 / 26 / 1, with
`test_retired_inline_refusal_identity_is_absent_from_live_sources` failing. You diagnosed the
cause exactly — a concurrent phase-4 document — and stopped rather than reaching for a third
file. **That was the correct call and the fourth time this project's scope gate has held.**

**The cause was the coordinator's, and it is fixed.** The phase-4 handoff named a retired error
identity in prose. That guard's roots cover all of `docs/handoff/` — roots this coordinator
widened in an earlier pipeline for exactly this reason — so a document in *another phase's*
perimeter broke *your* baseline. The handoff now describes the retired behaviour without
spelling the token, which is what the guard exists to enforce.

**Re-verified at `HEAD` after the fix:** `tests/unit/docs/` → **59 passed**; full non-`e2e`
suite → **2425 passed / 26 failed / 1 deselected**. Your expected baseline is restored and
correct.

**Nothing about your perimeter, your tasks or your criteria has changed.**

## 1. The lesson this earned, which applies to you too

**Parallel phases share a baseline even when their file perimeters are disjoint.** Plan 3
touches only `app/`, plan 4 only `docs/handoff/`, and they still collided — because a test's
roots are not a perimeter. Phase 4's documents are still being reviewed and may change again.

**Consequently:** if your baseline disagrees with 2425 / 26 / 1 again, **first check whether
the failing test is one of the docs guards** (`tests/unit/docs/`). If it is, that is phase 4's
and you stop and report, exactly as you did. If it is anything else, apply the standing rule —
repeat the run and **diff the ID sets** before concluding, since the count has been observed at
25, 26 and 27 on unchanged code.

## 2. Everything else is unchanged

Read **`prompts/implementer/2026-08-19_phase3_implement_r1.md` §§1–10** and follow it in full:
role, workspace, the two-file perimeter, read order, F4-first ordering, the mutation
discipline, the environment, the closing protocol and the handoff contents.

The three points worth repeating because they are the expensive ones:

- **F4 first.** It is the only repair guarding a silent failure with a live trigger: the
  previous pipeline made re-pricing write a **new chain row** rather than refuse, so
  supersession chains are a common state, and nothing pins that the endpoint reads the
  *current* row. Deleting `superseded_at.is_(None)` currently leaves the whole phase file
  green.
- **F6, F8 and F9 are decisions you may resolve either way.** The unacceptable outcome is an
  unrecorded one.
- **Mutations: both sides computed, whole suite, never `-k`.** Your F2 deletion is what makes
  the `max(6, quantity)` red set one test again — prove that across the suite, not the file.

## 3. Gate check

- `plans/plan_3.md` reads `state: PROMPT_READY`, `gate: projection WAIVED`.
- Perimeter is the two files in `plan_3.md` §2. **A third file is still a STOP.**
- Baseline **2425 / 26 / 1** — re-verified by the coordinator at `HEAD` after the fix.
- Expect to see phase 4's documents and the untracked
  `live_clock_for_working_time_economics/` folder in `git status`. **Neither is yours**;
  declare them as not written by you.

## 4. Handoff

As r1 §§9–10, at `handoffs/implementer/2026-08-19_phase3_implement_r1b_handoff.md`. Add one
line stating the baseline you measured at the start of this round.
