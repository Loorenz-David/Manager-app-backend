---
plan: plan_2
role: projection
round: 1
date: 2026-08-24
---

# Re-projection — Plan 2: Task budget-signal service and serializer

You are the independent pre-implementation projection reviewer for Plan 2 in
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

Read and follow `/Users/davidloorenz/agent-skills/plan-projection.md`, then
`/Users/davidloorenz/agent-skills/pipeline-charter.md`. The phase plan is your
authority; if this prompt differs from it, the plan wins.

## Gate check

Confirm from source before analysis:

- `planning/intention.md` has `status: **RATIFIED**`.
- The master-plan tracker records Plan 1 as `APPROVED` and Plan 2 as
  pre-implementation.
- Plan 2 declares its projection gate mandatory.

If any content gate fails, do not project; write a short blocked handoff explaining it.

## Read order

1. `master_plan.md` §§1–10, especially §§5, 6.1, 6.3, 6.4, 6.6, 6.8, 8–10.
2. `planning/intention.md`: header; §1 HC-2, HC-4, HC-5, HC-7; §1A M2/M4/M5/M6;
   §§2.5–2.6; §§3A.1 and 3A.5; §§4.1 and 4A.1–4A.3; §§5 and 5A.1–5A.3;
   §§6A.1 and 6A.4; §§7.3 and 7A.1–7A.2, 7A.6–7A.7.
3. `plans/plan_2.md` in full, then `plans/plan_1.md` §6 and Review log.
4. The Plan 2 Read-first code/test anchors and the inventory-handoff rows named by Plan 2 §2.
5. Architecture-graph orientation: `archgraph_status`, search `budget`, and inspect the
   three Plan 2 §8 anchors. Do not call `archgraph_build_context`; do not write graph content
   or adjudicate reviews.

## Projection task

Perform the plan-projection procedure against the artifacts and code as they stand today.
Independently derive the service/serializer skeleton only to expose unresolved decisions;
discard it or retain it only as a clearly non-authoritative handoff appendix. Do not edit
code, tests, plans, intention, master plan, or graph records.

Give deep attention to the phase's silent-failure mechanisms: allocator inputs and
typicals, batch-query shape/cap/visibility/order, constructed no-budget rows and the
ten-key serializer, `ctx.now` live time and absorbing `over`, and snapshot-rate integer
money conversion. For every criterion, verify decidability and both-direction trace
coverage; for every named mutation, verify a concrete site and observable red path.
Classify every unresolved point as a plan gap, intention gap, or explicit delegation.

## Evidence budget and closeout

This session's L4 budget is exactly **0** runs. Projection is an artifact/source-analysis
gate; do not run the full suite. Use narrow inspection or probes only when they establish a
concrete projection finding.

Write the report to:
`handoffs/reviewer/20260824_plan_2_projection_round_1.md`

Use the charter handoff schema and plan-projection closing protocol. Use verdict
`PROJECTED_CLEAN` or `AMENDMENTS_REQUIRED`; include the owner-readable opening, required
`⚠ OWNER DECISIONS REQUIRED (n)` section, routed decision ledger, reality/decidability/trace
findings, exact write perimeter, and owner-layer final response. Do not update the master-plan
tracker or Plan 2 Review log; the coordinator does that after consuming the handoff.
