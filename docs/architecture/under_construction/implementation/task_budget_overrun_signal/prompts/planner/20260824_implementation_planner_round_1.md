---
plan: planning (project-level — belongs to no phase)
role: planner
round: 1
date: 2026-08-24
---

# Implementation-planning session — Task Budget Overrun Signal

You are the implementation-planner agent (Claude Opus) for this repository:
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

Produce the executable plan set for the ratified Task Budget Overrun Signal intention:
one `master_plan.md` and self-contained `plans/plan_<n>.md` files. Do not implement
code or tests; this is the contract-to-plan gate.

## Gate check — before all other work

Open `docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md`.
Proceed only when its source header reads `status: **RATIFIED**`, round 9, and says
mechanism-inventory is complete. It currently does. If the header no longer satisfies
that condition, stop without edits and write a failed-gate handoff.

The mechanism-inventory exit gate has passed: all silent-failure mechanisms are
contract grade; D9 and D10 were resolved and then re-ratified. The phase plan set may
now be authored.

## Read first — in this exact order

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-planner.md`
3. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md` — read the header first, then §§1, 1A, 2.4A, 3–7A, 8–10.6, 11 rounds 6–9, and 12–12A.
4. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/planner/20260824_mechanism_inventory_round_1.md` — all sections; its §6 gives the planner routing hazards.
5. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/shaper/20260824_shaping_context_handoff.md` — especially §§3–7.
6. `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823.md`.
7. `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md` only to confirm D5/HC-2 excludes it from this project.

Use Architecture Graph read-only for planning context: `archgraph_status`, searches for
the task-budget-signal concept and Item Economics, `archgraph_get_node` on the exact
reused anchors, and bounded `archgraph_compute_impact`. Do not call
`archgraph_build_context`: `.archgraph/contexts/current-task.md` belongs to a different
active task and must not be overwritten. Do not write or review-maintain graph state.

## Planning obligations

Follow the implementation-planner doctrine and charter in full. In particular:

- Create `master_plan.md` with all ten required sections: goal; source-of-truth map;
  roles/workflow; tracker; contract resolution; shared naming registry; sequencing;
  tool protocols; standing rules; verified environment topology.
- Create the smallest phase set that keeps every phase independently green and at no
  more than eight addressable criteria. Do not preserve the intention's tentative
  two-phase guess if the 22 mechanism registrations make it unsound; explain the chosen
  seam and make every ledger entry reachable from at least one criterion trace cell.
- Every phase criterion must have an ID, one exact expected outcome, a resolved
  measurement/contract trace, a test home, and named mutation(s). Enumerate state and
  adjacent-boundary rules rather than sampling them.
- Verify every named file, symbol, fixture/seed, observable payload key, count, and
  planned deletion against the current tree. Report exact commands and derived
  summands in the plan artifacts; do not type counts from the handoffs.
- Resolve the contract-system status from source. The inventory reports no published
  Application_contracts endpoint row, but independently verify that fact and state the
  selected/added/local/excluded result with reasons.
- Record environment topology from current evidence, not the shaper's baseline. The
  planner owns the exact test levels/commands, database safety rules, and known baseline
  caveats for future sessions.
- Plan the dated `to_frontend` handoff required by intention §8, including its three
  inventory corrections: a non-zero overrun may cost zero; N response rows is per
  distinct visible requested id; and the route has two 422 envelope shapes.
- Preserve HC-2: the worker-time-pressure request is a different project. The four
  HC-2a artifacts are the sole explicitly permitted pre-existing route/mirror changes.
- Each implementation phase closes with an Architecture Graph delta assessment. The
  intended likely delta is one endpoint and one projection plus reuse relationships,
  but record only what the implementation proves.

## Standing coordinator finding

The preceding mechanism-inventory session made an extra write outside its stated
perimeter: `docs/archgraph-anchor-observations.md`. It declared the write honestly; do
not alter or rely on that document in this session. Record this as a process lesson in
the master plan's standing rules: session write perimeters are closed, and an external
standing brief never silently expands a prompt's explicit allowed files. This is not a
product requirement and must not create a phase criterion.

## Permitted write perimeter

Only these project planning artifacts may be created or edited:

- `docs/architecture/under_construction/implementation/task_budget_overrun_signal/master_plan.md`
- `docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_<n>.md`
- `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/planner/20260824_implementation_planner_round_1.md`

Do not edit the intention, source code, tests, frontend handoffs, Architecture Graph,
or any file outside this project. Do not run an L4/full suite; planning uses source
inspection and narrowly scoped environment discovery only.

## Closing protocol

1. Lint the plan set against the charter's five manifest properties before handoff.
2. Leave every tracker row `NOT_STARTED`.
3. Write the handoff at the exact path above with frontmatter `plan`, `role`, `round`,
   `date`, `state`/`verdict`, and `actor`; include the full write perimeter, plan-file
   inventory, manifest-lint evidence, contract resolution, environment evidence,
   Graph reads/writes, unresolved decision cards (if any), and the explicit next gate.
4. Do not author an implementation prompt. The coordinator consumes your handoff,
   lints the selected first phase, and decides whether projection is mandatory before
   compiling it.

The intention is your task list. If this prompt differs from the intention, the
intention wins.
