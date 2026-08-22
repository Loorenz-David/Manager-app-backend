---
plan: 2
role: reviewer
round: 1
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Review round 1 — plan 2 (task-scoped section-keyed production-time view)

You are the reviewer (plan-reviewer doctrine,
`/Users/davidloorenz/agent-skills/pipeline-charter.md`). You fix nothing. You verify that
what was built is what the contract specifies, and that every guard actually guards.
Read-only session; your write perimeter is exactly one handoff file:

`…/simple_production_budget_division/handoffs/reviewer/2026-08-17_phase2_review_r1_handoff.md`

**Scope is deliberately light** per the MVP calibration rule (master plan §6): a full
mutation ledger is required only for rule-6 mechanisms and the tenant boundary. The
coordinator has already done the consumption checks recorded below — **do not repeat
them, extend them.**

## What the coordinator already verified (independently, do not redo)

- **Suite re-run from scratch: 2311 passed / 26 failed / 1 deselected**, failure IDs
  **byte-identical** to the approved 26-ID baseline (full-set diff, zero added, zero
  removed). The handoff's numbers are accurate.
- **C5 re-derived through the real allocator**: 180 min, typicals 60/30/60, two Upholstery
  steps → **4320 / 2160 / 4320**, sum 10800. D11 is correctly implemented.
- **E3 against live production data** (a 9-section task): sections returned in true
  `order_list` order `[1,2,3,5,6,7,8,9,1000]`; all four roles **byte-identical**; **zero**
  monetary keys at any depth; degradation correct (`item_unvalued` → `budget.*` null,
  `share_state: "no_budget"`, `worked_seconds` and typicals still populated);
  `allocation_method` = `static_proportional_section_v1`.
- **Write perimeter diffed against git.** Checkpoint `98aa31b` (+ `aa95d5e`, a one-line
  hash correction). It contains **`.archgraph/architecture.yml`, which the handoff does
  not declare** — inspected: exactly 2 phase-2 nodes, **zero** foreign/bootstrap records,
  so the content is clean but the declaration is incomplete (F2 below).
- **Tenant probe already run and adjudicated (F3): do not re-open.** Deleting
  `TaskStep.workspace_id` from E3's step query leaves all 26 phase-2 tests green. This is a
  **genuine equivalence**, not a hole: `task_id` is globally unique and
  `get_task_budget_status(ctx)` 404s on the tenant boundary before the step query runs.
  Same class as phase 1's recorded r3 probe-4. Reverted, `sha256` verified byte-identical.

## Findings the coordinator is routing to you (adjudicate these first)

### F1 — mixed-section `share_state` contradicts `left_seconds` (SHOULD-FIX, reproduced)

`budget_division.py:357-361` computes `worked_for_share` **excluding** excluded steps'
seconds; `:367` computes `left_seconds = allowance - worked` where `worked` is the group
total **including** them. Two different bases on the same row.

Reproduced by the coordinator: a section holding one `SKIPPED` step (100 s worked) and one
`COMPLETED` step (10 s), slice 10 s →

    worked=110  allowance=10  left_seconds=-100  share_state="on_track"

A card that says "on track" beside "−100s left". Also note the step rows inherit
`section_state` (`:383`), so they say on-track too.

**The contract is genuinely ambiguous and you must rule.** D13 says a step reports
`over_share` when *"the section's **total** worked exceeds its slice"*, and M3.3 defines
section `worked_seconds` as including excluded steps — that reading makes `share_state`
wrong. But M3.5b says the residual must never subtract an excluded step's seconds because
they are *"already charged against `B`, which would charge them twice"* — that reading
makes `left_seconds` wrong. Both cannot stand. Rule which field moves, state the wording
the intention needs, and say whether C9 must be strengthened (it passes today and did not
catch this).

**Reachability:** zero `skipped`/`cancelled`/`failed` steps exist in the database, so this
is fixture-only. That is an argument about urgency, not about correctness.

### F2 — declared perimeter is incomplete (SHOULD-FIX, process)

`.archgraph/architecture.yml` is in the checkpoint but absent from the handoff's file
list; `master_plan.md`'s phase-2 tracker row was rewritten by the implementer (a
coordinator artifact). Content of both is fine. Rule 11's point is that a perimeter which
does not match `git show --stat` cannot be audited — say so.

### F4 — correct the projection's risk framing on B8 (NOTE)

Projection B8 warned that P-COVER would fail on *"5 production tasks"* holding steps on the
soft-deleted `sanding` section. The coordinator checked those five: **all five tasks are
themselves soft-deleted**, so E3 correctly 404s and the branch has **zero reachable
production instances**. B8's outer-join contract stays (C22 is right to exist); only the
urgency was overstated. Confirm and record so it is not re-escalated later.

## What to review (light scope)

1. **The five unverified mutation probes.** The handoff paraphrases its red output
   (*"expected X, got Y"*) rather than reproducing it. The coordinator independently
   confirmed C5 and adjudicated the tenant one. **Re-apply the remaining five yourself** —
   C6 (governing step), C14 (`final` via `serialize_item_cost_result`), C22 (inner-join the
   section attributes), C23 (tie key), C25 (live name twice) — mutate → observe red →
   revert → `sha256`. A probe you cannot reproduce is a finding.
2. **P-AGREE end to end (C12).** The property this phase exists to establish. Verify E2 and
   E3 agree on section allowance *in every M3.5b branch*: no-open-step (45 of 50 real
   multi-step groups), `{completed, pending}`, negative residual, and the excluded/mixed
   cases. This is where F1 lives, so treat it as the same investigation.
3. **T7b closure.** The handoff claims exactly two phase-1 value rows changed. Verify no
   other phase-1 assertion moved **and none was loosened** — `git diff 8a1f815 98aa31b --
   app/tests/` is the whole evidence base. A weakened assertion is a failed round
   regardless of suite colour (r2 lesson).
4. **HC-6 / C19.** Confirm mechanically that no second allocator exists and that the
   per-step split lives in `budget_division.py`, not in E2.
5. **B10's dispatch branch.** Confirm the third branch asserts the E3 service identity
   rather than loosening the existing budget-status assertion.
6. **Anything built that no criterion covers.** `test_production_time_contract.py` is a
   file the plan did not name — read it and say whether it earns its place or duplicates.

## Output

Verdict `APPROVED` or `CHANGES_REQUIRED`, then a numbered ledger (`S<n>` should-fix,
`N<n>` note), each with file:line and — for should-fix — the concrete wrong behaviour and
the mutation that demonstrates it. For F1, give the contract wording you recommend.

Do not soften a finding because the fix looks small, and do not raise one you could not
demonstrate. Phase 1's seven should-fix findings were every one a guard that did not
guard, each found by deleting a construction and watching the suite stay green.
