---
plan: plan_2
role: projection
round: 0
date: 2026-08-24
---

# Projection — Plan 2: Task budget-signal service and serializer

You are the independent pre-implementation projection reviewer for Plan 2 in
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

Read and follow the doctrine at
`/Users/davidloorenz/agent-skills/plan-projection.md`, then
`/Users/davidloorenz/agent-skills/pipeline-charter.md`. The phase plan is your
authority; if this prompt differs from it, the plan wins.

## Gate check

Before analysis, confirm all of the following from source:

- `planning/intention.md` has the header `status: **RATIFIED**`.
- Master-plan tracker: Plan 1 is `APPROVED` and Plan 2 remains pre-implementation.
- Plan 2 declares its projection gate mandatory.

If a gate fails, do not project; write a short blocked handoff explaining the
failed content gate.

## Read order

1. `master_plan.md` §§1–10, especially §§5, 6.1, 6.3, 6.4, 6.6, 6.8, 8–10.
2. `planning/intention.md`: header; §1 HC-2, HC-4, HC-5, HC-7; §1A M2/M4/M5/M6;
   §§2.5–2.6; §§3A.1 and 3A.5; §§4.1 and 4A.1–4A.3; §§5 and 5A.1–5A.3;
   §§6A.1 and 6A.4; §§7.3 and 7A.1–7A.2, 7A.6–7A.7.
3. `plans/plan_2.md` in full, then `plans/plan_1.md` §6 and Review log.
4. The Plan 2 Read-first code/test anchors and the inventory handoff rows named
   in Plan 2 §2.
5. Architecture graph orientation: run `archgraph_status`, search `budget`, and
   inspect the three Plan 2 §8 nodes. Do not call `archgraph_build_context`; do
   not modify graph content or adjudicate reviews.

## Projection task

Perform the plan-projection procedure. Derive the service/serializer skeleton
only to expose unresolved decisions; discard the sketch or place it only as a
clearly non-authoritative appendix to the handoff. Do not edit code, tests,
plans, intention, master plan, or graph records.

Allocate depth to these silent-failure mechanisms named by the phase itself:

- the allocator's four-argument call and its typical-time inputs;
- batch query shape, raw-list cap, visibility filtering, and deterministic order;
- constructed `no_budget` rows and the ten-key serializer contract;
- `ctx.now`-based live seconds and the absorbing `over` state;
- integer-second money conversion from the evaluation snapshot.

For every criterion, test whether an implementer can write its assertion now
from the authorities alone, whether its trace resolves in both directions, and
whether every named mutation has a concrete site and an observable red path.
Classify every unresolved point as a plan gap, intention gap, or explicitly
delegable free choice; do not silently choose.

## Evidence budget and closeout

This session's L4 budget is exactly **0** runs. Projection is an artifact and
source-analysis gate; do not run the full suite. Use narrow inspection/probes
only where they establish a concrete projection finding.

Write your report to:
`handoffs/reviewer/20260824_plan_2_projection_round_0.md`

Use the charter handoff schema and plan-projection closing protocol. State the
verdict as `PROJECTED_CLEAN` or `AMENDMENTS_REQUIRED`; include the owner-readable
opening, the required `⚠ OWNER DECISIONS REQUIRED (n)` section, a fully routed
decision ledger, reality/decidability/trace findings, exact write perimeter, and
your owner-layer final response. Do not update the master-plan tracker or Plan 2
Review log; the coordinator does that after consuming this handoff.
