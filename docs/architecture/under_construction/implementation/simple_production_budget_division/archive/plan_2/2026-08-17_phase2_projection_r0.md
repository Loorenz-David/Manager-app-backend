---
plan: 2
role: reviewer
round: 0 (projection — gate, mandatory)
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Projection round 0 — plan 2 (task-scoped section-keyed production-time view)

You are the projectionist (plan-projection doctrine,
`/Users/davidloorenz/agent-skills/pipeline-charter.md` + your role doctrine). You
implement nothing and fix nothing: you walk the planned mechanisms against the real code
and the real database BEFORE implementation, and deposit a ledger of everything that
would go wrong. Read-only session — your write perimeter is exactly one handoff file:

`docs/architecture/under_construction/implementation/simple_production_budget_division/handoffs/reviewer/2026-08-17_phase2_projection_r0_handoff.md`

**This phase changes a shipped, approved mechanism.** Phase 1 closed on 2026-08-17 with
zero production defects, and D11 now changes the unit `divide_production_budget`
allocates to. Your ledger is the only thing standing between that decision and a silent
regression in E2, which real frontend code is about to consume.

## Read first (in this order)

1. `…/simple_production_budget_division/planning/intention.md` — **§12 entire**. §3–§6
   remain in force for everything phase 2 does not change; where §12 and §4 appear to
   conflict, that conflict is a finding, not something for you to reconcile silently.
2. `…/planning/owner_decisions.md` — D9, **D11 (incl. the recorded coordinator
   correction), D11a, D12**.
3. `…/master_plan.md` — §4 naming registry (phase-2 block), §6 standing rules + nine
   earned rules + **MVP calibration rule**, §7 environment, §9 phase-2 gates.
4. `…/plans/plan_2.md` — T1–T7b, C1–C21.
5. Code — read every one, verify independently, do not trust a citation:
   - `domain/item_economics/budget_division.py` (whole file)
   - `services/queries/item_economics/get_task_budget_allocations.py`
   - `services/queries/item_economics/get_task_budget_status.py`
   - `services/queries/working_sections/get_working_section_typical_times.py`
   - `domain/item_economics/calculator.py` (`:302`, `:328`, `:340`)
   - `domain/item_economics/division_serializers.py`
   - `models/tables/working_sections/working_section.py`,
     `models/tables/tasks/task_step.py`
   - `routers/api_v1/item_economics.py:330-370`
   - the phase-1 test files under `app/tests/` for `budget_division` and
     `budget_allocations`

## What to project (walk each with concrete numbers; pin expected values)

1. **Re-measure §12.4 on the database as it stands right now.** The coordinator measured
   it 2026-08-17, but the local copy was refreshed from RDS mid-pipeline and figures
   already moved once (skipped steps went 253 → 0 between phase 1's projection and now).
   Re-run and report as counts: `order_list` populated / total / distinct, every tie
   group, the steps-per-(task,section) distribution, groups with 2+ non-closed steps, and
   the step-state distribution. **Any figure that disagrees with §12.4 is a finding that
   routes back to the intention.**

2. **D11's arithmetic at the new unit.** Walk the §12.5 example by hand: 180 min,
   typicals 60/30/60, two Upholstery steps. Confirm 72/36/72 in integer seconds through
   `_budget_seconds` half-even quantization, `Fraction` weights, and largest-remainder
   with the tie key. Then walk a case where the section count makes
   `distributable_seconds` indivisible, and confirm P-SUM3 exactly. State whether
   `_sort_key` (`:72`, step-shaped) can serve grouped units unchanged or whether
   `_section_sort_key` must differ — the grouped unit has no `sequence_order`.

3. **What D11 does to phase 1's existing tests.** Enumerate — do not sample — every
   phase-1 test whose expected value changes, and every one that does **not** change
   because its steps are each in a distinct section (there the weights are identical and
   the values must be byte-identical). A phase-1 test that silently keeps passing when it
   should have changed is the failure mode here.

4. **D11a's per-step split, adversarially.** The rule is "the open step is allowed the
   section's slice minus the worked seconds of the section's closed steps." Walk: closed
   pass burned *more* than the whole slice (negative left — is that `over_share` or a
   clamp? which does the frontend contract in §6.2 already promise?); closed pass burned
   exactly the slice; section with no open step at all; section with one step only (the
   98.2% case — confirm the rule degenerates to today's behaviour **exactly**, since any
   drift there changes almost every card in production).

5. **`allocation_method` under HC-5.** E2's per-step values change while its shape does
   not, and HC-5 makes that label the consumer's cache key. Rule on whether
   `static_proportional_v1` must become `_v2` or a new value. Argue both sides and
   recommend — this is a contract decision the coordinator deliberately left to you.

6. **The status/`item_binding` third copy.** `get_task_budget_status` resolves them, and
   E2 already re-derives them inline (`get_task_budget_allocations.py:179-201`). E3 would
   be the third site. Say what the single home should be and whether extracting it is in
   phase-2 scope or a finding to record for later — the **one-copy rule** is at stake,
   but so is HC-1's blast radius.

7. **M3.4's governing step against the real state machine.** `closed_at` is the rule's
   pivot. Verify against `task_step.py` and the transition service which states actually
   set `closed_at`, and whether any state can be non-closed yet terminal (or closed yet
   re-openable — check `force_task_ready` and the remove/re-add path). If "non-closed"
   is not a faithful proxy for "live", say what is.

8. **Route declaration order.** `/tasks/{task_client_id}/production-time` is a
   three-segment parameterized path; `/tasks/budget-allocations` is two-segment fixed.
   Verify no shadowing in either direction, and whether the P7-style hazard that bit E1
   applies here. Check both hand-written mirrors' current counts so T6 increments the
   right numbers.

9. **P-FLAT's monetary check.** C14 requires a **recursive** no-monetary-key walk. Name
   every key in the planned payload that could carry money if someone later extended a
   nested object, and state what the assertion must traverse to be meaningful rather than
   decorative.

10. **HC-10 end to end.** Take the two mockups' element lists (frontend handoff §4 and
    §8) and confirm every single element is renderable from E3's §12.7 payload with **no
    client-side join**. Anything missing is a gap in the contract, found now rather than
    by the frontend.

11. **Anything the plan assumes without contracting it.** The mechanism-inventory gate
    was waived a second time on the condition that **any mechanism you find operating
    without a contract is a GATE FAILURE routed to the intention, never downgraded to a
    note.** That condition is yours to enforce.

## Output

One handoff at the path above. Verdict `READY` or `AMENDMENTS_REQUIRED`. A numbered
ledger: each item `B<n>` (blocking) / `P<n>` (contract amendment) / `N<n>` (note), with
the exact file:line or measured count it rests on, and — for blocking items — the
concrete wrong number or wrong behaviour that would ship. Where you recommend contract
wording, give the wording.

Do not soften a blocking finding into a note because the fix looks small. Phase 1's
seven should-fix findings were all guards that did not guard, and every one was found by
deleting a construction and watching the suite stay green.
