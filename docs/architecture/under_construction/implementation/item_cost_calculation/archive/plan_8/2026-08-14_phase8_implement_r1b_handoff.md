---
plan: phase 8 — status & results
role: fix
state: IMPLEMENTED
date: 2026-08-14
actor: Codex
checkpoint: 6c1da6b
---

# Phase 8 r1b implementation handoff

## Outcome

The r1b production defect is fixed by adding the native PostgreSQL enum
migration:

`c1d2e3f4a5b6_add_process_item_cost_result_task_type.py`

The configured development database was upgraded from `be9dfe42a035` to
`c1d2e3f4a5b6`. The state query
`SELECT enumlabel FROM pg_enum ... task_type_enum ...` returned exactly
`process_item_cost_result`; Alembic reports `c1d2e3f4a5b6 (head)`.

## Cycle-scoped write perimeter

- `app/migrations/versions/c1d2e3f4a5b6_add_process_item_cost_result_task_type.py`
- `app/tests/integration/migrations/test_phase8_task_type_migration.py`
- `app/tests/integration/services/commands/item_economics/test_phase8_status_results.py`
- `app/tests/integration/services/commands/item_economics/test_phase7_evaluations.py`
- `app/tests/unit/services/queries/item_economics/test_phase8_serializers.py`
- `app/tests/unit/services/tasks/analytics/test_process_item_cost_result.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_8_status_results.md`
- this handoff file

No r1 production files were changed in r1b. The Architecture Graph was
read-only as required; the new migration architecture note is recorded here
for the coordinator instead of mutating the held 21-item graph delta.

## Verification

- Final foreground non-E2E suite: **2111 passed / 23 failed / 1 deselected**.
  The 23 failure IDs displayed by pytest are the established phase-1 failure
  set; a saved-output byte diff was not produced in this session, so this is
  reported as an observed ID-set match, not as a byte-identical claim.
- Combined phase-7 regression, phase-8 migration/lifecycle integration, and
  phase-8 serializer/handler/router/state coverage: **33 passed**.
- `ruff check` on the cycle perimeter: passed.
- `python3 -m compileall -q beyo_manager tests/unit`: passed before the final
  test run; the cycle adds no runtime-only syntax.
- Configured DB: `c1d2e3f4a5b6 (head)` and the enum state assertion passed.
- `alembic check`: reports three pre-existing unrelated metadata drifts
  (`email_sync_states_connection_id_key` and two `step_state_records` indexes);
  the enum migration itself has no reported new metadata operation.
- No disposable database migration round-trip was run. The configured DB was
  left at head and no destructive database operation was issued.

## Coverage added

The cycle adds automated rows for the migration state, projection isolation,
current committed evaluation selection, deleted-step exclusion and
state-unfiltered SKIPPED consumption, replay/upsert identity with advancing
`computed_at`, no-evaluation no-write, lifetime snapshot/result totals,
PENDING/ASSIGNED/STALLED total admission, all twelve shipped status enum
members, worker monetary-key exclusion, and worker/router registration. The
phase-7 hardening assertion now checks exactly one evaluation-committed event.

The full amended C1–C11 matrix is not fully automated in this cycle: the
bucket/dilution rows, all boundary emission exact-count rows, loader equality
property, A6 mutation rows, and several lifetime/status sole-predicate rows
remain reviewer follow-up. No production change beyond the migration was made
to compensate for that proof gap.

## Per-row mutation ledger

No mutation files were touched. Each named mutation below is explicitly
deferred to review because this session did not have a disposable worktree in
which to apply-and-revert the mutation without contaminating the checkpoint:

1. **C1 manager filter deletion** in `get_task_budget_status.py` — deferred;
   no byte hash or pytest node produced.
2. **C1 worker filter deletion** in `get_task_budget_status_worker.py` —
   deferred; no byte hash or pytest node produced.
3. **C1 handler filter deletion** in `process_item_cost_result.py` — deferred;
   no byte hash or pytest node produced.
4. **A15 DELETE re-resolution removal** in `delete_item_valuation.py` —
   deferred; no byte hash or pytest node produced.
5. **READY-entry emit deletion** at the definition site in
   `_task_state_transitions.py` — deferred; no byte hash or pytest node
   produced.
6. **Reopen emit deletion** at the helper definition site, exercised through
   `add_task_steps` — deferred; no byte hash or pytest node produced.
7. **Resolve terminal emit deletion** — deferred; no byte hash or pytest node
   produced.
8. **Fail terminal emit deletion** — deferred; no byte hash or pytest node
   produced.
9. **Cancel terminal emit deletion** — deferred; no byte hash or pytest node
   produced.
10. **Straggler re-emit deletion** in `process_step_transition.py` — deferred;
    no byte hash or pytest node produced.
11. **Straggler READY-half guard narrowing** — deferred; no byte hash or pytest
    node produced.
12. **C7 selection-OK producer swap** — deferred; no byte hash or pytest node
    produced.
13. **C9 `total_cost_minor` serializer addition** at the definition site —
    deferred; no byte hash or pytest node produced.
14. **C11 live-task-field substitution for evaluation snapshots** — deferred;
    no byte hash or pytest node produced.
15. **A6 removal of WORKER from the budget-status allow-list** — deferred; no
    byte hash or pytest node produced.
16. **A6 moving budget-status into the manager-only route table** — deferred;
    no byte hash or pytest node produced.
17. **A13 `computed_at` freeze** — deferred; no byte hash or pytest node
    produced.

## Final SHA-256 — all phase production files

```text
07641d45213a038a3287925b3dc47b4afef814aa4203db75eaeb536dae264d0a  app/beyo_manager/domain/execution/enums.py
b533790c3f5d424131527d3115af8ef39834cd7688f58bf63dce6f9f793d44ce  app/beyo_manager/domain/execution/payloads/item_cost_result.py
12d6e36a7a04074c03c277704d66744d8da7adade3469edd0c9de27ce2a53f88  app/beyo_manager/domain/item_economics/serializers.py
50efab2962319e95359c250a0b665349124d5430ae7a0e2ef2b032597d7aefe0  app/beyo_manager/routers/api_v1/item_economics.py
0bb4d312b00e0c137b6a839e192f4557e580eea78d3251cddd3b2fc8830ab007  app/beyo_manager/services/commands/item_economics/delete_item_valuation.py
22366088c403de1cb9057be67797239aedc47306724a3242710fc1a6440229f3  app/beyo_manager/services/commands/task_steps/add_task_steps.py
728e7770ca669ec914c6a53190b956713bf06639e84a6ee27e46f890b45073c2  app/beyo_manager/services/commands/tasks/_task_state_transitions.py
97de30b2fdb435f0cb5e0e42f04d0f2ee2498c496226452b403e0d54a16ea438  app/beyo_manager/services/commands/tasks/cancel_task.py
bceb07689f923a640d3b7977b135ecfddc9c844ef8b72f41f3abe0a4eccede9c  app/beyo_manager/services/commands/tasks/fail_task.py
f5d9e23fb1090fa81a44b924b28a32792a13d6ffbf385cf745ddae6a79944cb4  app/beyo_manager/services/commands/tasks/resolve_task.py
8f94d36ed8be2756727f4d31f689d034e735c8c3f88fd46abb969231f8eafe46  app/beyo_manager/services/infra/execution/task_router.py
ce9fc62dbe372af5e74385530f4ec1306bc3da5dc56314b312d0517fb6c442b2  app/beyo_manager/services/queries/item_economics/get_economics_configuration_status.py
c10d6bc64c98177fcb4720c660515da823828f8bbe8e59a99c7045f5d2df2e06  app/beyo_manager/services/queries/item_economics/get_item_lifetime_economics.py
9abf05b547ec8d47bcbaaa1307bde851e7f69f64ceb2a526354aa4f7fd8e0941  app/beyo_manager/services/queries/item_economics/get_task_budget_status.py
011cf2ae76dde81fe837a1f7b5f8a869230621001c64af06feb7718951970f00  app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py
d57ca890d0ad9b14eb09bdda339e07cfe94e3a20475621ca640e61a11e2e5172  app/beyo_manager/services/tasks/analytics/process_item_cost_result.py
fe1091c68a5fdb72bad8eb7c2f225d2d44f81b85842dfafdf7a8b4cb21267e80  app/beyo_manager/services/tasks/analytics/process_step_transition.py
4729a0ab598542e4dec37d370047dd67abb8fb36b4e2db44d917589ba47ab6d3  app/beyo_manager/workers/analytics_worker.py
877f71a849f954032774c5b814a0e7a1af264f92ddf7cb611be17a9a62e9049a  app/migrations/versions/c1d2e3f4a5b6_add_process_item_cost_result_task_type.py
```

## Decisions and delegations

No owner decision card is required. The graph migration mapping is delegated
to the coordinator's post-approval graph pass because r1b is read-only for
Architecture Graph. The mutation ledger and disposable migration round-trip
are delegated to review, explicitly per row above.

## Checkpoint

The r1b checkpoint is:

`CHECKPOINT (not approved): item-cost phase 8 implement r1b — enum migration and evidence`
