# Shaping handoff — remaining_production_pressure, round 1 (2026-08-24)

**Artifact:** `planning/intention.md`, status READY_FOR_RATIFICATION (round 1).
**Source:** `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md`
plus owner decisions O1–O5 given in conversation before writing.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. The five material decisions were the owner's (intention §10). What remains is the
ratification act itself on §10.6.

## What the session established (verified against the tree, not the handoff)

- Step allowances are static only in single-step sections; `_section_step_allowances`
  (`budget_division.py:222`) gives an open step the section residual. The intention preserves
  this (O3) and uses it as the share basis.
- Both operands of the pressure formula come from the step-level split, which never sees
  excluded steps — so sibling §3.4 cause 1 cannot manufacture pressure. Cause 2 (pot floored at
  0) enters by design and agrees with sibling D9.
- The frontend's acceptance criteria 3/4/6 were mutually inconsistent once a step has worked;
  the intention restates 3 (sum = pot after settled work) and 4 (settled steps contribute
  actual, never a negative) so that 6 (I-1) holds live without persistence.
- Shape-asserting artifacts that this project must touch and the sibling's M6 protects:
  `test_budget_division_routes.py` exact key sets, `golden_budget_allocations.json`,
  `golden_budget_status.json`, `division_serializers.py`. Hence HC-5.

## Sequencing gate (HC-5) — for every downstream role

Blocked until `task_budget_overrun_signal/master_plan.md` tracker shows phases 1–3 `APPROVED`.
At writing: 1 APPROVED, 2 PROMPT_READY, 3 NOT_STARTED. Ratification does not lift this gate.

## Next actor

Owner: ratify or amend §10.6. Then mechanism-inventory — **after** HC-5 clears, since its
probes would sit on the same files the sibling is editing.

## What this session did NOT do

No production code, no tests, no plan, no `to_frontend` handoff, no graph delta. The frontend
has not been answered; the answer is a new dated handoff authored at implementation time.

---

## Round 2 addendum (2026-08-25)

Owner decision **O6** folded into `planning/intention.md` (round 2, READY_FOR_RATIFICATION):
an open step with `left_seconds < 0` is *consuming* — its live worked seconds are charged to
the numerator every poll, it leaves the denominator, its own share is `0`. I-1 gains the one
named exception I-1x (crossing the allowance → `0`, once). M2 restated to guard the blind
window as well as the countdown. O1–O5 unchanged. Decision cards: still **0**.

## Round 3 — RATIFIED (2026-08-25)

Owner David ratified on §10.6 after confirming D1 (crossing = allowance), D2 (negative ratio
served), D3 (names). Status header RATIFIED round 3. **HC-5 still blocks every downstream
act** until `task_budget_overrun_signal` phases 1–3 are APPROVED. Next actor: coordinator →
HC-5 check → mechanism-inventory.
