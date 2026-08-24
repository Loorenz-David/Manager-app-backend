---
plan: plan_1
role: review
round: 1
date: 2026-08-24
---

# Session prompt — full review of phase 1, Task Budget Overrun Signal

Independently review implemented phase 1, the pure `budget_signal.py` domain rule. Run as Claude
Opus in a fresh session. You review and report; never fix code, tests, plans, or intention.

Repository: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

## Doctrine — read first

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Gate check — stop and report if any fails

1. `master_plan.md` §4 records phase 1 as `REVIEWING` and phases 2–3 remain `NOT_STARTED`.
2. `planning/intention.md` header says `RATIFIED`, round 10, and no owner decision is open.
3. `plans/plan_1.md` is current; its Review log contains the three projection folds, owner waiver,
   and the implementer's completion entry.
4. The implementation handoff exists at
   `handoffs/implementer/20260824_plan_1_implementation_round_1.md` and records checkpoint
   `6b84ef0f19f545b54fbd24157eea3964582ba1bf`.
5. `git diff --name-status f376928 6b84ef0` contains only the two new phase code/test files plus
   the phase plan, tracker, and implementer handoff; the subsequent commit `248f8f0` changes only
   that handoff. Any wider implementation perimeter is a finding.

## Read order

1. Master plan §§5, 6.2, 6.8, 8–10.
2. The intention and code/contract sources listed by plan 1 §2.
3. `plans/plan_1.md` in full.
4. The implementer handoff above — consume its evidence; do not trust it blindly.
5. The completed production module and its test file.

## Review scope

This is the first, full review: evaluate every phase-1 criterion, the ratified semantic
authorities, and all 35 declared mutations. Re-derive the rule and use variation rather than
redundantly replaying the implementer's evidence. Inspect the code structurally for purity,
exact types, terminal-state representation, D9/D10, the two production money call sites,
sentinel derivation, and the closed public API.

Specific judgment-call probes from the implementation report:

- C4(e) was added after the first criterion pass; prove its allocator-originated excluded-row
  fixture is non-vacuous.
- MUT-07 first landed at the wrong textual site and was re-sited; independently verify the final
  mutation actually changes the task-pot operand rather than merely producing a convenient red.
- C5(g)'s wrapper must observe both production money calls in incurred-then-projected order;
  verify its type assertions cannot be bypassed.
- Confirm the 35-mutation ledger is closed and each reported bite reaches the named assertion.

## Evidence budget

- Reuse the implementer L1/L2 evidence only where its recorded tree identity matches.
- Run variation probes at L1/L2 as needed; every probe must be applied and reverted, with files
  recorded in your handoff.
- L4 budget: exactly **one** `PYTHONPATH=. .venv/bin/pytest -m 'not e2e'` review-entry stamp,
  because the review tree differs from the implementation stamp due to the closeout handoff.
  Compare the full failing-ID set against the documented 21-ID baseline. Any extra L4 needs the
  charter's pre-run authorization line.

## Architecture graph

Call `archgraph_status`, search the existing allocation/budget anchors, and inspect the phase-1
delta assessment. Do not read or overwrite `.archgraph/contexts/current-task.md`, make no graph
mutation, and never adjudicate pending review items.

## Write perimeter

Only write:

- the phase-1 tracker row in `master_plan.md` (`APPROVED` or `CHANGES_REQUESTED`);
- an append-only technical Review-log entry in `plans/plan_1.md`;
- `handoffs/reviewer/20260824_plan_1_review_round_1.md`.

Mutation probes may temporarily touch only the two phase code/test files and must be reverted.
No other write is authorized.

## Closing protocol

Write the handoff with frontmatter `plan: plan_1`, `role: review`, `round: 1`, `verdict`,
`date`, and `actor`. Include: owner-readable opening; `⚠ OWNER DECISIONS REQUIRED (n)`;
findings by severity with authority and correction; verified-correct ground; mutation-probe
declaration; evidence records/tree identity/failing-ID delta; perimeter result; architecture
assessment; lessons for plans; and carry-forward dispositions if approving with notes.

Update the tracker and plan Review log exactly once, after completing the review. The plan is
your task list; if this prompt differs from it, the plan wins.
