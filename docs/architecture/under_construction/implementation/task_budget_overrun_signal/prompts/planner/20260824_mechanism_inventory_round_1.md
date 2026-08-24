---
plan: planning (project-level — belongs to no phase)
role: planner
round: 1
date: 2026-08-24
---

# Mechanism-inventory session — Task Budget Overrun Signal

You are the mechanism-inventory agent (Claude Opus) for this repository:
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

Your task is to take the ratified intention through the mechanism-inventory gate. Do
not plan phases, implement code, or create tests. The intention is the semantic
authority; where a handoff disagrees with it, the intention wins.

## Gate check — perform this before all other work

Open `docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md`.
Proceed only if its source header says `status: **RATIFIED**` and records the owner's
2026-08-24 ratification. It currently does. If that is no longer true, stop without
editing anything and report the failed gate in your handoff.

D5 is resolved: HC-2 stands and the worker-time-pressure request is a separate
project. Do not broaden this project to alter `budget-allocations`.

## Read first — in this exact order

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/mechanism-inventory.md`
3. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md` — especially §§1, 1A, 3, 4, 5, 6, 7.1–7.4, 8–10.3, 11 round 5, and 12.
4. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/shaper/20260824_shaping_context_handoff.md` — especially §§3–7. Use its anchors and probes for orientation; it is not semantic authority.
5. `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823.md`.
6. `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md`, only to confirm its scope is excluded by D5/HC-2; do not incorporate its requested fields.

For architecture orientation, use the Architecture Graph read-only workflow first:

1. call `archgraph_status`;
2. inspect `domain-item-economics` and `endpoint-item-economics-task-budget-allocations`;
3. use `archgraph_compute_impact` only if a source finding indicates a boundary not
   settled by the intention.

Do not overwrite the existing `.archgraph/contexts/current-task.md`: it belongs to a
different active task. Do not make any graph writes in this session.

## Work to perform

Adversarially inventory every load-bearing mechanism, rank by silent-failure risk,
and make every risky mechanism contract-grade in the intention. At minimum, deepen:

- §3.4's two-operand accounting divergence: task pot versus allocator section rows,
  excluded steps, infeasible/negative budget behavior, and the exact production-path
  invariant that prevents quiet cancellation.
- §3.1–§3.3's allocator reuse, terminal-state predicate, clamp, and 60-second floor.
- §4.1–§4.2's evaluation-snapshot rate and mandatory
  `calculate_consumed_cost_minor` call identity, including types/precision and the
  prohibited alternate derivations.
- §5–§6's complete non-null row/default contract and total precedence order,
  particularly the `INFEASIBLE` zero-work boundary and both populated overrun pairs.
- §7.3's batch cardinality, omitted-id identity, hard cap/error identity, request
  ordering, and two-call determinism behind M4/M5.
- Any further mechanism the intention relies upon, including ORM/serializer input
  types, enum/wire-only sentinel handling, live-worked-time basis, route precedence,
  and authorization/field-absence boundaries where they carry silent-failure risk.

For each contract-grade addition, state inputs and production types, canonicalization
or precision rules, total order/overlap behavior where relevant, the invariant that a
test must prove on the production path, and the measurement-ledger entry or existing
contract it registers against. Preserve citation stability: add lettered sections
rather than renumbering any cited section. Append a truthful changelog entry.

If a necessary contract would materially change semantics, do not choose it yourself:
put the intention back to `COLLABORATING` only when the materiality is clear, and
surface the question as a charter-format decision card. If it can be resolved without
changing semantics, record the rationale for owner ratification in the handoff.

## Scope and write perimeter

Permitted writes are exactly:

- `docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md`
- `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/planner/20260824_mechanism_inventory_round_1.md`

Do not modify source code, tests, the master plan, phase plans, prompts, frontend
handoffs, existing shaper artifacts, or Architecture Graph state. Do not run the full
test suite; this is a contract-definition session, not an implementation cycle.

## Closing protocol

1. Re-read the amended intention and verify the status remains `RATIFIED` unless a
   genuinely material semantic decision card requires reopening it.
2. Write the handoff at the exact path above, with frontmatter:
   `plan`, `role`, `round`, `date`, `state`/`verdict`, and `actor`.
3. The handoff must include: the complete ranked inventory table; every intention
   delta and its ledger registration; all decision cards verbatim; the full write
   perimeter (documents, code, and tool-recorded state); source evidence inspected;
   graph reads and the fact that graph writes were zero; and the explicit next gate.
4. Report back with the handoff path and whether the next actor may be
   implementation-planner. The coordinator will consume the file rather than a chat
   summary.

The intention is your task list. If this prompt and the intention differ, the
intention wins.
