---
plan: phase 8 (status & results — status query, result handler, §8B emissions)
role: implementer
round: 1
date: 2026-08-14
---

# Session prompt — implement phase 8 (the last mechanism phase)

You are the **implementing agent** for phase 8: the live budget-status query
(manager + worker faces), the item lifetime economics read, the
`process_item_cost_result` handler, and the §8B boundary emissions. The
projection did your first hour on paper; its 25 rows are routed and the
plan's amendment block is GOVERNING.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## The plan — read BOTH layers as one document

`docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_8_status_results.md`:
the base plan + all forward notes + the **"Amendments (projection r0)" block
A1–A17 — GOVERNING wherever the two conflict** (C7 twelve members/two
producers, task-5 pins + C11, the reopen signature, the emit OUTSIDE the
notification conditional, the enumerated upsert, the router table split,
three filter sites, C6b total, the worker result-block key set, the loader
equality row, enumerated serializer families, bucket constructions,
computed_at observation, perimeter notes, the DELETE re-resolution, the
three graph discrepancy filings, reuse/harness/mechanics/counts).

Also read AS AMENDED (intention round 17): **§8A.6 (the result block renders
whenever a result row exists, boundary-labelled — R17-1)**, **§11A.5(d) (the
DELETE status is re-resolved, never hand-written — R17-2)**, §8A entire,
§8B entire, §11A entire (twelve-value §11A.4), §4A, §7B.3 (item_binding).
Master plan §6.4 (the status→identity mapping), §6.5 (worker handler, task
type + `"queue:analytics"` routing, `ItemCostResultPayload`, the two
separate budget-status services, the lifetime route), §9 P-A…P-AB + ALL
extensions — **P-E as amended today** (the reopen call-site adaptation is
inside the fence), P-T 3rd (lock modes), P-Q 4th (fixtures vs engine),
P-R 2nd (committing harness named), P-AB + companion (effect enumerations
read off the code), P-I 9th (mutations phrased for byte-reproducibility),
the deferral rule (if you defer, the ledger says so per row).

## Environment facts (verified at projection time, 2026-08-14)

- Head `be9dfe42a035` — **NO migration in this phase** (`item_cost_results`
  is live; conflict target `uq_item_cost_results_task_id` is a UNIQUE
  constraint). Suite baseline **2076 / 23 / 1 = 2099 selected**.
- Payload-key greps for every key this phase introduces: zero hits.
- `on_conflict_do_update`: ZERO repo precedent — yours is the first; the
  A5 enumeration is the spec (named constraint, 11 SET columns, 4 stated
  exclusions).
- Integration on the queue path needs the analytics worker (§10 Makefile
  caveat); in-process handler invocation is the default seam.
- Graph: 166/239, ALL human_confirmed, 0 pending, rev `b0f9127d…`. Your
  delta is one additive batch (status/lifetime read nodes — expect
  `projection` type per the list_task_evaluations convention — handler
  node, edges) PLUS three discrepancy FILINGS per A16 (the
  archgraph-discrepancies Reporter role: `open/` ledger files with
  path:line observations; never edit the contradicted nodes yourself).

## Discipline highlights

- **The emit placement is the phase's trap** (A4): terminal-command emits
  sit AFTER the notification block, never inside `if target_user_ids:`;
  C10's fixtures have ZERO notification targets. The reopen hook forces the
  async/session signature change (A3) — the fence admits exactly the two
  named adaptations, nothing else in the execution path.
- **Two producers, one vocabulary** (A1): the payload's `ok`/`infeasible`
  come only from the committed-evaluation branch; `selection.status is OK`
  never leaks into the payload (the dedicated hazard row proves it).
- **The money boundary is structural** (A9/A11/L22): the worker result
  block carries EXACTLY the five declared keys; the disjointness test
  quantifies over both ENUMERATED serializer families; the router rows use
  the `_client` harness and the `response_model is None` structural row;
  the budget-status route is ALL-ROLES via the split table (A6) with both
  P-G mutations.
- **R17-2**: `delete_item_valuation.py:44` re-resolves; the criterion
  asserts the owner's same-warning property LITERALLY (deleted-price status
  == never-priced status, same workspace, both configured and unconfigured
  rows).
- **Counts are exact** (L24): a ready-making transition yields TWO result
  events by design; no "at least one" anywhere.
- **N named mutations = N ledger rows**; per-row sha256 pairs COPY-PASTED;
  observed pytest node ids; mutations phrased so a second agent reproduces
  the mutant byte-for-byte (P-I 9th — the phase-7 fix ledger is the bar);
  suite numbers READ off the run; the four `create_task` integration files
  and the transition/analytics suites re-run (your hooks touch every task
  creation and every step transition in the suite).
- Any committing subset twice, residue scope named (rule 11½); bounded
  waits on anything concurrent (P-T).

## Scope fence

Production: `services/queries/item_economics/get_task_budget_status.py`,
`get_task_budget_status_worker.py`, `get_item_lifetime_economics.py` (all
new), `get_economics_configuration_status.py` (A14: the N4 enum-compare
swap ONLY), `services/commands/item_economics/delete_item_valuation.py`
(A15 re-resolution), `services/tasks/analytics/process_item_cost_result.py`
(new) + `workers/analytics_worker.py` (handler map),
`domain/execution/enums.py` (task type) +
`services/infra/execution/task_router.py` (routing),
`domain/execution/payloads/item_cost_result.py` (new),
`domain/item_economics/serializers.py` (status + lifetime serializers,
incl. the worker one with NO monetary keys),
`services/commands/tasks/_task_state_transitions.py` (both hooks; reopen
signature per A3), `services/commands/task_steps/add_task_steps.py` (the
awaited call site ONLY), `resolve_task.py`/`fail_task.py`/`cancel_task.py`
(one emit line each, placed per A4),
`services/tasks/analytics/process_step_transition.py` (the §8A.5 guarded
re-emit per A17), `routers/api_v1/item_economics.py` (two routes) +
`routers/README.md`. Tests: new phase-8 files +
`test_item_economics_router.py` (table split + rows) +
`tests/unit/test_task_state_transitions.py` (the two sync-call updates) +
`test_phase7_evaluations.py` (R2-N2 hardening ONLY). Docs: master plan
tracker + plan Review log + your handoff + the three A16 discrepancy
filings. **No migration.** If anything else seems needed, stop and report.

## Closing protocol

1. All criterion rows green (C1–C11 as amended + the split-table rows);
   the full mutation ledger.
2. Suite: expect 2076+N / 23 byte-identical to the phase-1 list / 1
   deselected (numbers READ off the run); ruff on changed files; DB at
   head `be9dfe42a035` (no migration — say so); disposables dropped and
   listed.
3. Tracker → `IMPLEMENTED`; Review log per P-L; state every delegation you
   exercised.
4. Checkpoint `CHECKPOINT (not approved): item-cost phase 8 implement r1 —
   <summary>`; handoff AFTER, citing FINAL hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-14_phase8_implement_r1_handoff.md`
   (full path). `⚠ OWNER DECISIONS REQUIRED (n)` if any arise; full write
   perimeter + probe declaration.
