---
plan: plan_2
role: implement
round: 2
date: 2026-08-25
---

# Bounded continuation — Plan 2 C19 contract update and checkpoint

Continue Plan 2 in
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.
Invoke the `implementation-executor` skill. `plans/plan_2.md` remains authoritative.

## Gates and read order

Confirm the intention header is `RATIFIED`; Plan 1 is `APPROVED`; Plan 2 is
`PROMPT_READY`; and the 2026-08-25 owner decision in Plan 2's Review log authorizes the C19
perimeter amendment. Read the master plan §§4, 6.1, 8–10; Plan 2 in full; and
`handoffs/implementer/20260824_plan_2_implementation_round_1.md` before editing.

## Allowed continuation perimeter — no other changes

1. `app/tests/unit/services/queries/item_economics/test_production_time_contract.py`:
   amend only C19's expected set to include `get_task_budget_signals` alongside the two existing
   consumers. Do not weaken its other assertions.
2. `app/beyo_manager/domain/item_economics/division_serializers.py`:
   restore every formatting-only change to pre-round-1 form, retaining only the two new
   budget-signal serializer functions and their two `__all__` entries.
3. Plan 2 tracker row and Review log, the implementation handoff, and the required checkpoint
   commit / graph record are closing artifacts, not product scope.

The three implemented phase files must otherwise stay byte-identical to the round-1 handover.
Do not change the Plan 2 integration tests or rerun its mutation ledger: the prior 18 mutation
records remain valid because their test file and production sites are unchanged.

## Evidence and closeout

Run C19 at L1, the Plan 2 integration test file at L1, and the master-plan L2 radius. This
continuation's L4 budget is exactly **1** run: `PYTHONPATH=. pytest -m 'not e2e'` on the final
handed-over tree, with failing-ID delta against the 21-ID baseline. Record all tree identities.

At phase close, perform the master-plan §8 graph delta: status, required searches/node reads,
duplicate preflight, then one additive `archgraph_apply_changes` batch for the phase-2
projection only if the tree proves it. Do not use `archgraph_build_context` and do not
promote/reject/edit review items.

If all evidence is acceptable, update only Plan 2's tracker row to `IMPLEMENTED`, append the
Review log, make the checkpoint commit with subject prefix `CHECKPOINT (not approved):`, and
write `handoffs/implementer/20260825_plan_2_implementation_round_2.md` with full perimeter,
evidence, graph result, and owner layer. If blocked, preserve the implementation and report the
precise blocker without a checkpoint.
