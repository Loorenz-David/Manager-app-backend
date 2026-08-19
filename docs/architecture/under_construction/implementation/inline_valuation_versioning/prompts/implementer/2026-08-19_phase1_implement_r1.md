---
plan: 1
role: implementer
round: 1
date: 2026-08-19
pipeline: inline_valuation_versioning
---

# Implement round 1 — plan 1 (inline valuation versioning)

You are the implementer (implementation-executor doctrine,
`/Users/davidloorenz/agent-skills/pipeline-charter.md`). Implement plan 1 exactly. Every
decision has been made; where you find one that has not, **STOP and report** rather than
settling it in code.

This is a **small, deliberate change to closed item-cost v1 behaviour** that retires a
registered error identity. Precision about the perimeter matters more than volume here.

## Read first

1. `docs/architecture/under_construction/implementation/inline_valuation_versioning/planning/intention.md` — all; §3 is the contract.
2. `…/planning/owner_decisions.md` — D-AUTH, D17, D18.
3. `…/master_plan.md` — §4 naming, §5 rules, §6 baseline, §7 gates.
4. `…/plans/plan_1.md` — T1–T3, C1–C9.
5. The five code sites listed in plan 1's "Read first".

## Hard constraints (violating any one is a failed round)

- **HC-1 — exactly THREE files may change**, and no others:
  `services/commands/tasks/create_task.py`,
  `tests/unit/docs/test_item_economics_handoff_accuracy.py`,
  `tests/integration/services/commands/item_economics/test_phase8b_inline_task_prices.py`.
  If a fix appears to need a fourth: **STOP and report.**
- **HC-2 — no second valuation writer.** `write_item_valuation_chain_in_session` stays the
  only code that supersedes or inserts a valuation. You add a decision in front of it.
- **HC-3 — no migration, no schema change, no `CALCULATION_VERSION` bump.**
- **HC-4 — the no-op must write nothing.** Not a row, not a supersede, not an audit event.
  "Writes an identical row" is a different behaviour and is wrong.
- **D17 — inherit.** A field absent from the request takes the current valuation's value.
  Passing `None` through to the writer stores `None` and unprices the item; that is the
  bug this decision exists to prevent.
- **D18 — currency is part of the comparison**, alongside both amounts.

## Discipline

- Each named mutation in C2, C3 and C5 must be applied **at its definition site**,
  observed red, reverted, and the file confirmed `sha256` byte-identical. Record the
  **observed output**, not a paraphrase.
- **C4 is the row that catches a fixture confound** — C2 and C3 each hold for a second
  independent reason, so build C4 as specified (partial request whose inherited field
  makes the triple identical). Precedence-disagreement rule, master plan §5.
- You are **removing** a test. Per the deleted-assertion rule, the handoff must state
  which new row covers each behaviour the rejection test used to pin.
- No weaker assertions. Row counts are exact integers, not "unchanged" in prose.

## Suite

From `backend/app/`, containers healthy: `PYTHONPATH=. pytest -m 'not e2e'`.

Start baseline: **2313 passed / 26 failed / 1 deselected**. Reproduce it before editing.
**Diff failure IDs, never totals** — one run in three has been seen at 25 failed and the
drifting test is unidentified; a lower number is not "better than baseline".

This phase **removes** one test and adds several, so state the arithmetic explicitly:
selected before, tests removed, tests added, selected after. The DB also accrues ~24
`task_steps` per full run from tests outside this pipeline — never read a changed row
count as evidence of a code change.

## Checkpoint and handoff

Commit with subject `CHECKPOINT (not approved): inline valuation versioning`.
Handoff → `…/handoffs/implementer/2026-08-19_phase1_implement_r1_handoff.md`: frontmatter,
checkpoint hash, **full write perimeter declared by path and generated from `git`**, suite
totals with the arithmetic above plus the failure-ID diff, observed-red output per named
mutation, a C1–C9 table naming which test bites on which mutation, the deleted-assertion
mapping, and a **DECISIONS I HAD TO MAKE** section for anything the artifacts left open.
