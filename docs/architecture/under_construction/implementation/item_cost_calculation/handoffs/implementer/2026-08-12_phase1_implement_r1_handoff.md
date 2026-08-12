---
plan: phase 1
role: implementer
round: 1
date: 2026-08-12
state: IMPLEMENTED
verdict: READY_FOR_REVIEW
actor: Codex
---

# Phase 1 implementer handoff

Implemented fail-closed, role-derived redaction of `task_steps.total_cost_minor` for WORKER and SELLER payloads across the complete eight-endpoint census. ADMIN/MANAGER retention is explicit and equality-tested against the seeded value `4321`. Checkpoint: `4416570` (`CHECKPOINT (not approved): item-cost phase 1 — redact worker step money`).

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Implementation and judgment calls

- Added `include_monetary_step_fields` beside `serialize_step` as the single allow-list derivation helper; unknown and absent roles fail closed.
- Changed `serialize_step` to `serialize_step(step, *, include_monetary: bool)` with no default; the monetary key is absent, not `null`, when false.
- Derived the flag at the five planned call sites. The two shared builders carry the behavior to reassigned-steps, pending-acknowledgments, and last-interacted endpoints; their query services were not edited.
- Kept serialization in the existing query layer per the master-plan contract-gap-2 divergence. `serialize_item` and item money fields were untouched.
- Reused the existing working-section seed helper for the new task/list integration tests; all fixtures use `flush()` on the rolled-back `db_session` and do not commit.
- Re-parameterized the working-section characterization test by role and recorded the changed worker key set. Added the required keyword to the existing ended-shift characterization call without changing its assertion.

## Verification

- Initial required baseline before implementation: 1602 collected, 1601 selected; 1092 passed, 473 failed, 38 errors, 1 deselected. The sandbox denied PostgreSQL/Redis connections; unrelated unit failures were also present.
- Focused phase suite after implementation: 57 passed.
- Final full `PYTHONPATH=. pytest -m 'not e2e'` with healthy local containers: 1624 collected, 1623 selected; 1601 passed, 22 failed, 1 deselected. All 57 phase-focused tests passed in that run. The 22 failures are outside this phase and are recorded in the phase Review log.

## Mutation probes

M1, M2, M3, M4, M5, M6, the site-5 blanket-`False` probe, and the shared step-record-builder blanket-`False` probe were each applied at the named definition/call site, caused the named test rows to fail, and were reverted. Probe file list:

- `app/beyo_manager/domain/tasks/serializers.py`
- `app/beyo_manager/services/queries/tasks/tasks.py`
- `app/beyo_manager/services/queries/tasks/list_task_steps.py`
- `app/beyo_manager/services/queries/working_sections/steps_list_payload.py`
- `app/beyo_manager/services/queries/working_sections/step_record_payload.py`
- `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py`

All probes were reverted before the checkpoint commit; the committed tree contains none of them.

## Architecture Graph

Close status was valid at 116 nodes / 157 edges, revision `b0702c3c…`, zero stale nodes, with 244 pending reviews left untouched. The required batched closeout call used the existing `table-task-step` anchor; it was skipped as an exact duplicate (`applied=[]`), so the architectural delta is explicitly zero.

## Full write perimeter

Code and test files:

- `app/beyo_manager/domain/tasks/serializers.py`
- `app/beyo_manager/services/queries/tasks/list_task_steps.py`
- `app/beyo_manager/services/queries/tasks/tasks.py`
- `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py`
- `app/beyo_manager/services/queries/working_sections/step_record_payload.py`
- `app/beyo_manager/services/queries/working_sections/steps_list_payload.py`
- `app/tests/integration/services/queries/analytics/test_ended_shift_bucket_collapse.py`
- `app/tests/integration/services/queries/task_step_acknowledgments/test_reassigned_steps_integration.py`
- `app/tests/integration/services/queries/tasks/test_worker_money_redaction.py`
- `app/tests/integration/services/queries/worker_stats/test_get_worker_daily_step_breakdown.py`
- `app/tests/integration/services/queries/worker_stats/test_worker_stats_endpoint_split_integration.py`
- `app/tests/integration/services/queries/working_sections/test_get_user_last_active_step_record_integration.py`
- `app/tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py`
- `app/tests/unit/test_task_serializers.py`

Pipeline artifacts:

- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_1_worker_money_redaction.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-12_phase1_implement_r1_handoff.md` (this handoff, deposited after the checkpoint)

Tool-recorded state changes:

- Architecture Graph status/orientation reads only.
- One batched `archgraph_apply_changes` closeout attempt; it applied zero changes because the existing `table-task-step` node was an exact duplicate. Graph revision remained unchanged.
- Git checkpoint commit `4416570`.
