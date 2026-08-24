---
plan: plan_1
role: implement
round: 1
date: 2026-08-24
---

# Session prompt — implement phase 1 of Task Budget Overrun Signal

Implement phase 1: the pure `budget_signal.py` domain rule. Run as Claude Opus in a fresh
session. The phase plan is your task list; where this prompt differs, the plan wins.

Repository: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

## Doctrine — read first

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## Gate check — stop and report if any fails

1. `master_plan.md` §4 records phase 1 as `PROMPT_READY`; phase 1 has no predecessor.
2. `planning/intention.md` header says `RATIFIED`, round 10, with no owner decision open.
3. `plans/plan_1.md` is present, has exactly the two new files in §4, and its Review log
   records the owner waiver after projection rounds 0–2.
4. `app/beyo_manager/domain/item_economics/budget_signal.py` and
   `app/tests/unit/domain/item_economics/test_budget_signal.py` are absent before this work.

## Read order

1. `master_plan.md` §§5, 6.2, 6.8, 8–10.
2. The ratified intention and source evidence specified by plan 1 §2, in that exact order.
3. `plans/plan_1.md` in full.
4. The selected contracts named by master plan §5; re-emit the contract resolution before
   coding and stop if repository reality contradicts it.

## Scope and non-optional constraints

- Touch only the two new code/test files from plan §4, the phase-1 tracker row in `master_plan.md`,
  the plan-1 Review log, the implementer handoff below, and the phase-1 architecture-graph delta
  if the completed tree warrants it. No other pre-existing file.
- No service, serializer, route, database, migration, frontend handoff, or edits to allocator,
  calculator, existing tests, or existing docs. Those belong to later phases.
- The three projection ledgers were fully folded. Do not reopen product semantics; no decision is
  delegated to you. In particular, implement C5(g)'s two production call sites, C7's sentinel
  contract, and C8's complete public surface exactly as the current plan states.
- Do not write the substrings `digest` or `fingerprint` anywhere in `budget_signal.py`.

## Architecture graph

At session start, call `archgraph_status`, search the existing budget/allocation anchors, and
inspect the prior allocation projection as required by master plan §8. Do **not** read or
overwrite `.archgraph/contexts/current-task.md`; do not promote/reject/edit review items.
At close, assess the plan-1 delta exactly as master §8 requires: none or one `source_file` node,
recording only what the implemented tree proves in one batch.

## Evidence budget and closing work

- Build the executor Task-0 forward and reverse coverage map before production edits. Include
  every criterion sub-row and every test; no orphan tests.
- Run L1 evidence and every **35** named mutations in plan §6.1, one at a time, reverted and
  recorded with observed failing id/assertion. Report the per-criterion mutation summands and
  prove `executed == declared == 35`.
- Run the master-plan L2 item-economics command after L1/mutations.
- L4 budget: exactly **one** run, the final `PYTHONPATH=. pytest -m 'not e2e'` stamp on the tree
  handed over, with failing-ID comparison to the documented 21-ID baseline. Any additional L4
  requires the charter's pre-run authorization line.
- Make the required checkpoint commit at `IMPLEMENTED` with subject prefix
  `CHECKPOINT (not approved):`.

## Closing protocol

1. Update only the phase-1 tracker row to `IMPLEMENTED` after all phase criteria and the one L4
   stamp are complete.
2. Append the plan Review-log entry: what you built, coverage map, all judgment calls,
   evidence/mutation summary, and graph assessment.
3. Write the session report at:
   `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/implementer/20260824_plan_1_implementation_round_1.md`

Use frontmatter `plan: plan_1`, `role: implement`, `round: 1`, `state: IMPLEMENTED`, `date`,
and `actor`. Include owner-readable opening; `⚠ OWNER DECISIONS REQUIRED (n)`; all changed files;
the separate mutation-probe file list; complete coverage and mutation ledgers; L1/L2/L4 records
with tree identity and failure-ID deltas; graph delta; commit SHA; and any upstream item.

The plan is your task list. If this prompt differs from it, the plan wins.
