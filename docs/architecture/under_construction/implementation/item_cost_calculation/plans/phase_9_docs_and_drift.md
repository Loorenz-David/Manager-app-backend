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
- **Phase-1 review r1 additions to the drift batch (2026-08-12):**
  (N1) `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`
  publishes `total_cost_minor` as always-present on a worker-app endpoint — false
  since phase 1; correct it here and note it for the frontend team alongside the
  `LastActiveStepCard.tsx` smoke note.
  (N2) the ADMIN/MANAGER-only step-money audience is a real architectural policy no
  archgraph node carries — candidate node/description in this phase's graph delta.
- **Phase-2/3 additions to the drift batch (2026-08-12):** phase-2 review N4
  (`checkfirst=True` on the five new enum types), N5 (prefix-map row ordering),
  re-review N8 (downgrade proxy misses raw-SQL `DROP TYPE`), r3 N14 (order-dependent
  Shopify assertion — flaky under load, threatens byte-identical baseline gates);
  phase-3 projection S7 (**eleven `Mapped[float]` annotations on `Numeric` columns**
  in the item_economics models → `Mapped[Decimal]`/`| None` per
  `user_work_profile.py:33` precedent — annotation-only, no runtime change).

- **Forward note (phase-6 projection r0, D22):** the frontend doc mirrors
  carrying the legacy money keys
  (`frontend/docs/architecture/backend/routers_endpoints/README.md:1918-1920,
  1976-1978, 2078-2080, 2475-2477`;
  `frontend/docs/architecture/backend/tables/README.md:437,467,469` — :469
  also mirrors the `create_type=True` flag phase 6 flips) are OUTSIDE phase
  6's perimeter by decision, not oversight — this drift batch owns them.

- **Forward notes (phase-6 reviews):** (r1 N9) deploy ordering for the column
  drop is unstated — an old ORM selecting the dropped columns during a rolling
  deploy errors; document the required order (deploy code first, migrate
  second) in the living-docs page. (r2 N1) the drop migration's docstring
  still reads `Revises: 5caae620088c` while `down_revision = "5420acc6a7b3"`
  — one-line correction + the fix-r1 record correction is already in the r2
  Review log entry.

- **Forward note (phase-8 projection r0, L17 — deferred 4B N3):**
  `get_economics_configuration_status.py:38,:47` carry a redundant
  `and not version.is_deleted` (the loader already filters deleted rows) —
  two sufficient causes, verified not-a-gap; simplify or keep KNOWINGLY with
  a comment. Phase 8 took only N4 (the `status is EconomicsStatusEnum.OK`
  swap) with a declared one-file extension; the N3 clause is this phase's.

- **Forward notes (phase-8 re-review r3, routed at approval):**
  (N1) the three C1 filter-deletion mutations' bite is order-CONTINGENT
  (62/62 empirically, but the alternate heap order was observed on clean
  trees in r2) — this phase, as the first to touch the status queries, adds
  the STRUCTURAL arbiter: assert each of the three services' compiled
  evaluation `SELECT` carries the three literal filter clauses
  (`kind='committed'`, `superseded_at IS NULL`, `is_deleted = false`),
  which no heap order affects (§9 structural-filter rule). (N2) the C5
  supersession row never closes its task, so "after close" is untested and
  2 of 10 compared columns are vacuous — resolve the task before the
  second handler run, or rename the row (§9 scenario-fixture rule). (N4)
  `test_phase8_serializers.py` carries a stray re-indented `)` and a
  dropped blank line from the fix-r2 row deletion — cosmetic, ruff-silent,
  fold into this phase's formatting sweep.

## Review log

(append-only)
