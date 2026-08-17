---
plan: 1
role: implementer
round: 1
date: 2026-08-16
pipeline: simple_production_budget_division
---

# Implement round 1 — plan 1 (typical section times + per-step budget allocations)

You are the implementer (implementation-executor doctrine,
`/Users/davidloorenz/agent-skills/pipeline-charter.md`). You implement plan 1
exactly as amended after projection round 0 — every decision you might be tempted to
make in code has already been made; where you find one that has not, STOP and report
rather than settling it silently.

## Read first (in this order; all paths repo-root-relative to `backend/`)

1. `docs/architecture/under_construction/implementation/simple_production_budget_division/planning/intention.md`
   — ALL. §3 (M1) and §4 (M2) as amended round 5 are the mechanism contracts you
   implement literally; §5 the payload shapes; §2.5 the mutation-surface grounding.
2. `…/simple_production_budget_division/master_plan.md` — §4 naming registry (names
   are final), §6 standing rules, §7 environment (test command, baseline).
3. `…/simple_production_budget_division/plans/plan_1.md` — tasks T1–T7, criteria
   C1–C21 (with C9b–C9e, C13b). The criteria are your test list; every named RED
   mutation must actually turn its test red — you verify each one before handoff
   (mutate → observe red → revert; record the observed-red output per mutation,
   byte-reproducibly, in the handoff — this is a HARD handoff field).
4. Code precedents:
   - `app/beyo_manager/domain/item_economics/calculator.py` — entry-guard style
   - `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py:111-125`
     — the status branch T3 mirrors IN FULL (item-less → NOT_EVALUATED without the resolver)
   - `app/beyo_manager/services/commands/item_economics/_common.py:172-216` — the
     loader whose QUERY SHAPES you copy but whose function you must NOT call per task
   - `app/tests/integration/services/commands/item_economics/test_phase8_status_results.py:51-84`
     — fixture + teardown precedent (`_prepared` / `_cleanup_phase8`) done right
   - `app/tests/integration/services/queries/users/test_list_users_floor_identification.py:173-193`
     — the LOCAL `executed_statements` statement-counting pattern (the shared
     `count_queries` fixture in `tests/conftest.py:63-76` is broken; never use it)
   - `app/tests/unit/routers/api_v1/test_item_economics_router.py:55-95` — DB-free
     route-test pattern (TestClient + `dependency_overrides` + monkeypatched `run_service`)
   - `app/tests/integration/services/queries/task_step_acknowledgments/test_reassigned_steps_integration.py:86-115`
     — second statement-counting precedent + step/section fixture shapes

## Hard constraints (violating any one is a failed round)

- **HC-2:** zero migrations, zero new indexes (measured unnecessary), zero
  persisted state. If you believe you need one: STOP, report.
- **HC-1/HC-1a:** the ONLY pre-existing files you may modify are, by addition only:
  1. `app/beyo_manager/routers/api_v1/item_economics.py` — the E2 route, declared
     above the `/tasks/{task_client_id}/…` block with a one-line ordering comment
  2. `app/beyo_manager/routers/api_v1/working_sections.py` — the E1 route, declared
     ABOVE the `/{working_section_id}` route at `:128` (declared after it, E1 is
     shadowed and 404s). This file is tab-indented — match it.
  3. `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` — ONE row
     added to `_EXPECTED_ROUTES`, count assertions 23 → 24
  4. `app/beyo_manager/routers/README.md` — one Quick Index row + one detail
     section for EACH of E1 and E2
  Everything else you touch must be a NEW file per the master plan §4 registry.
- **HC-3:** no monetary field anywhere in the new payloads. There is no role
  branching in the new serializers — nothing exists to gate.
- **M2 arithmetic:** `fractions.Fraction` for weights/shares/fractional parts — no
  float anywhere in the division; the NULL-safe sort key
  `(seq is None, seq if seq is not None else 0, client_id)`.
- **M1 rounding locus:** round `percentile_cont`'s double with SQL `round()` or
  Python `round()`; NEVER via a `::numeric` cast (it flips half-even to half-away).

## Deliverables (master plan §4 names, verbatim)

New: `app/beyo_manager/domain/item_economics/budget_division.py`,
`app/beyo_manager/domain/item_economics/division_serializers.py`,
`app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`,
`app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`,
`app/tests/unit/domain/item_economics/test_budget_division.py`,
`app/tests/integration/services/queries/working_sections/test_typical_times_query.py`,
`app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`,
`app/tests/unit/routers/api_v1/test_budget_division_routes.py`.
Modified (HC-1a only): the four files enumerated above.
Error identity: `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS` (422, DomainError with
identity per `architecture/05_errors_local.md`).
Query params: repeatable (`list[str] = Query(...)`) — deliberate first-of-kind
(master plan §4); `?task_ids=` degenerates to `[""]` = one unknown id, omitted.

## Non-negotiable test discipline

- Tests that commit rows own their teardown in `try/finally` or fixtures (charter
  11½), following `_cleanup_phase8`; name the tables your residue check scanned.
- M1 fixtures pad to ≥5 qualifying groups with the filler helper placing the target
  group AT the median (plan P1 rule; C9b worked example is in the plan).
- Key-set assertions are exact set equality; fixture values pairwise distinct.
- Full suite at the end: `PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`,
  foreground, healthy containers (`make dev-up`). Expected: the 23 pre-existing
  failures byte-identical to the v1 phase-1 list (v1 master plan §10), zero new
  failures, selected count = 2272 + your added tests + 1 (the mirror-test row does
  not change its test count). Record exact totals AND the failure-id list diff in
  the handoff. A run with DB connection noise is not a baseline — verify
  connectivity first.

## Checkpoint commit (standing owner authorization)

When the suite is green-per-baseline, commit everything with subject prefix
`CHECKPOINT (not approved): plan1 implement r1 — budget division surfaces`. Do not
push. The commit is part of the round; the handoff cites its hash.

## Handoff

Write `…/simple_production_budget_division/handoffs/implementer/2026-08-16_phase1_implement_r1_handoff.md`:
frontmatter (`plan: 1, role: implementer, round: 1, state: IMPLEMENTED, actor: <model>`),
the checkpoint hash, your FULL write perimeter (every file created/modified —
documents, code, tool state; the perimeter will be diffed against git), suite
totals + failure-list comparison, per-criterion status C1–C21 with the observed-red
record for every named mutation (mutation applied → exact red output line →
reverted), any STOP items, and archgraph delta summary (T7: one batched
`apply_changes`; orient with `archgraph_status` first; never promote/reject/edit
review items). Known pre-existing dirt in the working tree (NOT yours, do not touch,
do not commit): modified `.archgraph/architecture.yml` + `bootstrap_app.py`,
untracked bootstrap seeding files and `to_implement_the_accurate_costs_and_projections/`
— keep your checkpoint commit scoped to YOUR perimeter only.
