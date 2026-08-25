---
plan: plan_2
role: implement
round: 1
date: 2026-08-24
---

# Implement Plan 2 — Task budget-signal service and serializer

Implement Plan 2 in
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

Invoke the `implementation-executor` skill and follow its doctrine. The phase plan is your
task list and authority; where this prompt differs, `plans/plan_2.md` wins.

## Content gates

Before editing, confirm at source:

- `planning/intention.md` has `status: **RATIFIED**`.
- The master-plan tracker shows Plan 1 `APPROVED` and Plan 2 `PROMPT_READY`.
- The Phase 2 projection r0 ledger has been folded and its owner waiver is recorded in the
  Plan 2 Review log.

If any content gate fails, stop and write a blocked handoff; do not implement.

## Read order

1. `master_plan.md` in full — especially §§5, 6.1, 6.3, 6.4, 6.6, 6.8, 8–10.
2. `planning/intention.md` sections listed in Plan 2 §2, including M2/M4/M5/M6 and all cited
   mechanism contracts.
3. `plans/plan_2.md` in full, including its Review log and all 18 mutations.
4. `plans/plan_1.md` §6 and Review log; the named inventory-handoff rows; then the Plan 2
   Read-first source/test anchors.
5. The resolved architecture contracts named in master plan §5. Re-emit the contract resolution
   in your handoff before coding.
6. Architecture graph: run `archgraph_status`, search `budget`, and inspect Plan 2 §8 anchors.
   Never call `archgraph_build_context`; do not modify or adjudicate graph reviews.

## Scope and inherited non-optional constraints

Final implementation perimeter is exactly Plan 2 §4:

- new `get_task_budget_signals.py`;
- additive-only `division_serializers.py` changes (the two named functions and two `__all__`
  entries; no existing serializer behavior changes);
- new `test_budget_signals_query.py`.

No route, router README, route-mirror test, endpoint test, frontend handoff, migration, sibling
service edit, or shared-helper extraction belongs here. `get_task_budget_allocations.py` and its
tests are read/copy sources only. Temporary mutation probes may touch the precisely declared
phase-1 `budget_signal.py` site and are reverted; list them separately in the handoff.

The plan's projection fixes are binding: fresh criterion-local tasks with exactly their named
steps; parameterised committed evaluations; historical timestamps relative to fixed `ctx.now`;
StepStateRecord teardown before TaskStep; refresh the C8(c) ORM evaluation; top-level service
envelope exactly `{"budget_signals"}`; every mutation has its named site. The only delegated
choices are the non-colliding fresh IDs and MUT-06's arbitrary `Decimal("3.7500")` rate.

## Execution and evidence

Complete executor Task 0 before production edits: forward and reverse trace map, one line per
criterion row and every phase test. Implement tests from the criteria, then the service and
serializer. Run all 18 named mutations one at a time at the listed site, record observed reds,
and revert/md5-verify each. Include the two exception-shape probes as declared ledger rows.

This session's L4 budget is exactly **1** run: the closing `PYTHONPATH=. pytest -m 'not e2e'`
stamp on the tree you hand over, compared by failing-ID set with the master-plan baseline. Use
L1/L2 for all other evidence. C7's clock mutation runs under `TZ=UTC` and the host zone.

On success: update only Plan 2's tracker row to `IMPLEMENTED`; append the Plan 2 Review log;
record the one phase-2 projection graph delta in one batch only if the closing tree proves it;
make the required checkpoint commit with subject prefix `CHECKPOINT (not approved):`; and write
the report to `handoffs/implementer/20260824_plan_2_implementation_round_1.md` with the charter
schema, full write perimeter, coverage map, mutation ledger, evidence identity, graph result,
and owner layer.
