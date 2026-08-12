# Phase 9 — Living docs & drift routing

```
plan: phase 9
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Write the domain's living-docs page and land the documentation-drift fixes routed by
the intention (§2.6) and the gate handoff (D-1…D-4). **NOT in this phase:** any code
or schema change; the dead-code cleanup candidates (§2.6 item 5 — recorded
out-of-scope); the archgraph D-3 anchor repair (human-authorized maintenance
channel, master plan §8). This phase is deliberately thin — **refine at prompt
time** (planner doctrine): the coordinator finalizes the exact wording tasks from
what phases 1–8 actually shipped.

## Read first

1. `master_plan.md` §§2, 6.5, 7, 9 (P-A…P-D), 11.
2. Intention §2.6 (drift list), §8.1/§8A.2 (two-cost divergence statement — rule 5),
   §6A.4 + R4-2 (presentation rule + 25→20 guidance), §11A.4 (vocabulary), §13,
   §10.2 breakage list (docs entries); gate handoff D-1…D-4.
3. Contracts: `23_documentation`, `29_feature_workflow` (+ core).

## Dependencies

Phase 8 APPROVED.

## Files expected to change

- `docs/domains/item_economics.md` (new — the living-docs page; if `docs/domains/`
  does not exist yet, create it per `23_documentation`'s placement rules and record
  the decision in the Review log)
- `app/beyo_manager/models/tables/items/README.md` (§2.6-1 `STALL`→`STALLED`;
  §2.6-2 remove the dropped `item_issues` columns section; plus the phase-6 column
  removal reflected)
- `app/beyo_manager/models/tables/tasks/README.md` (§2.6-3 stale
  `task_history_record.py` / `latest_history_record_id` references; plus a D-4 line:
  step transitions are not guarded on task terminality and terminal commands leave
  open step records open — with the §8A.5 re-emit as the consequence-handler)
- `routers/README.md` (verify every phase's OpenAPI mirror rows landed; fix gaps)
- `/Users/davidloorenz/Desktop/Developer/Application_contracts/planning/task/task_step_models.md`
  (§2.6-4: the step time/cost aggregates gap) and
  `/planning/item/item_models.md` §"Value and cost semantics" (§10.2 breakage list)
  — **separate working directory**; the coordinator confirms it is in the session's
  scope before compiling the prompt, or reroutes these two as an explicit
  maintenance item.

## Implementation tasks (ordered)

1. Living-docs page with pinned content: the §1 economic contract chain; the
   **two-cost-numbers side-by-side definitions with the divergence and its reason**
   (§8A.2 rule 5 — `total_cost_minor` = salary-priced working+paused;
   `consumed_cost_minor` = allowance-priced working-only); the **R4-2 presentation
   rule** (percentage terms are planning allocations; never presented as legally
   payable tax; VMB out of scope; the 25→20 gross-base example) — master plan P-D;
   the §11A.4 status vocabulary; snapshot/replay semantics (HC-1/HC-7, §8A.4);
   unvalued-is-never-zero (R-9); worker-minutes vocabulary (P-C); the §10A.3 bridge
   and its planned one-release lifetime (master plan §7 note).
2. README drift fixes per the file list above.
3. Application_contracts gap entries (or the rerouted maintenance item — coordinator
   decision recorded here).
4. Confirm the master plan's follow-up ledger still records: bridge-validator
   removal (release after frontend stops sending keys); D-3 anchor repair
   (maintenance channel); §2.6-5 dead-code list (out of scope).

## Acceptance criteria

Documentation deliverables; where a criterion is not automatable it is
reviewer-verified content (recorded — this is a deliberate, justified exception to
charter rule 1's test-backed norm, which targets code behavior).

**C1 (automated proxy):** a test asserting `docs/domains/item_economics.md` exists
and contains the pinned phrases: "planning allocation", the never-legally-payable-tax
sentence, "worker-minutes", and both cost-number definitions (string containment —
cheap drift alarm, not a substitute for review).

**C2 (reviewer-verified):** the living-docs page states both cost definitions side
by side with the R-5 reason; the presentation rule appears verbatim in spirit; no
sentence presents a percentage term as computing tax; "minutes per worker" appears
nowhere (P-C).

**C3 (reviewer-verified):** the three README fixes match the code as shipped
(STALLED; no dropped-column docs; no `task_history_record` references; D-4 line
present and accurate against `transition_step_state`'s actual guard).

**C4 (reviewer-verified):** `routers/README.md` mirrors every route the registry
§6.5 shipped; Application_contracts entries landed or the reroute decision is
recorded in the Review log.

## Notes

- Evidence documents (`research_context.md`, `raw_intention.md`) are records — never
  edited (charter artifact map); drift found in them was routed, not patched.
- Projection gate: **waived by plan** (no S1/S2 mechanism; documentation only) —
  the waiver justification the charter requires is this line; the coordinator may
  still order a projection if phase-8 lessons suggest it.
- Archgraph: expected delta ≈ zero (docs); state it explicitly at close.

## Review log

(append-only)
