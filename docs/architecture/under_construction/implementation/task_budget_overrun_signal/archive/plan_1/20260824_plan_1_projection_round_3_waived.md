---
plan: plan_1
role: projection
round: 3
date: 2026-08-24
---

# Session prompt — re-projection, phase 1 of Task Budget Overrun Signal

You are the plan-projection gate for phase 1, the pure `budget_signal.py` domain rule.
Run as Claude Opus in a fresh session. Do the implementer's first hour on paper,
adversarially and without permission to improvise. This is a fresh assessment of the current
plan, not a response to any earlier projection.

Repository: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.
Do not push, commit, edit plans or intention, or edit code/tests.

## Doctrine — read first

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

## Gate check — stop and report if any fails

1. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/master_plan.md`
   §4 says phase 1 is `NOT_STARTED` and projection is mandatory.
2. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_1.md`
   exists and its Review log contains only the coordinator's three 2026-08-24 projection-fold
   entries.
3. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md`
   header says `RATIFIED`, round 10, mechanism-inventory complete, and no owner decision open.

## Inputs discipline

Read only what the implementer will receive:

- `docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_1.md`.
- Its §2 Read-first list, in full, including the listed master-plan sections, intention
  sections, inventory-handoff rows, code, and tests.
- The actual codebase as needed to derive the work.

Do not read prior reviewer handoffs, implementation-planner handoffs, coordinator prompts,
chat history, or other planning-session context. What you cannot derive from the plan's inputs
is a finding, not a reason to fill in the gap yourself.

## Depth targets

Spend the deep passes on the phase's silent-failure mechanisms: the `str` versus enum terminal
predicate; allocator-originated section rows and the per-section clamp; the D9/D10 negative-pot
and no-work-ahead boundary; both exact `int`/`Decimal` money-call seams and their two forbidden
derivations; four-state precedence with both populated pairs; the wire-only currency sentinel;
and the full public API surface. Configuration/plumbing receives only the depth needed to
establish it has no hidden decision.

For every phase task and criterion, derive a non-authoritative skeleton, identify each decision
point, verify paths/sections/fixtures against source, test criterion decidability, and check
traces both directions. Do not preserve the skeleton as implementer guidance.

## Evidence budget

L4 budget: exactly **0** runs. Test-execution budget: **0** at every scope. This is a paper
gate; use static reading only.

## Write perimeter

Only write:

- `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/reviewer/20260824_plan_1_projection_round_3.md`

Everything else is out of perimeter. The coordinator, not you, writes any plan Review-log line
after consuming your handoff.

## Closing protocol

Write the handoff at the exact path above with frontmatter `plan: plan_1`,
`role: projection`, `round: 3`, `date`, `verdict` (`PROJECTED_CLEAN` or
`AMENDMENTS_REQUIRED`), and `actor`. Its body must contain:

1. a 3–5 sentence owner-readable opening;
2. `⚠ OWNER DECISIONS REQUIRED (n)` with decision cards where needed, or a one-line
   zero-card declaration;
3. a fully routed decision ledger (plan gap / intention gap / free choice);
4. reality-check and decidability findings with exact artifact locations;
5. trace-verification results; and
6. the full write perimeter from `git status`, plus `L4 runs: 0; tests executed: 0`.

The plan is your task list. If this prompt differs from it, the plan wins.
