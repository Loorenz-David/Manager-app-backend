---
plan: phase 1
role: fix
round: 2
date: 2026-08-12
state: IMPLEMENTED
verdict: READY_FOR_RE_REVIEW
actor: Codex
---

# Phase 1 fix-r2 handoff

S1 is resolved with ADMIN assertions for all five previously untested retention
rows. S2 is resolved with the verified baseline pair and complete 23-item failure
list recorded in the phase plan. No production code changed.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Finding-by-finding resolution

### S1 — ADMIN acceptance rows

- Added `admin` to the role enumeration in
  `test_list_working_section_steps_payload_characterization.py` and
  `test_get_user_last_active_step_record_integration.py`.
- Parameterized the reassigned/pending payload test over `manager` and `admin`,
  so both retained-money assertions execute for ADMIN.
- Added `role_name` to the worker-stats `_ctx` helper and parameterized
  `test_last_interacted_steps_keep_money_for_manager` over `manager` and `admin`.
- Every added retained-money row asserts `payload["total_cost_minor"] == 4321`.

### S2 — suite baseline record

- Added an append-only S2 correction under the implementer r1 entry in the phase
  plan. It records `545e504` as 1578 passed / 23 failed / 1 deselected and
  `4416570` as 1600 passed / 23 failed / 1 deselected, plus the complete 23-item
  failure list.
- Re-ran the full suite at this working HEAD with healthy PostgreSQL and Redis:
  1605 passed / 23 failed / 1 deselected (`1629` collected). The failures match
  the recorded 23-item set; no new failures appeared.

## Verification

- Connectivity: `pg_isready -h 127.0.0.1 -p 5433` accepted connections; Redis
  returned `PONG` on `127.0.0.1:6380`.
- Focused suite: **39 passed** across the four changed integration modules.
- Full suite: **1605 passed, 23 failed, 1 deselected** in 67.53s via
  `PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`.
- The initial focused attempt had one collection error because the new
  parametrized reassigned/pending function omitted its `role_name` argument; that
  wiring error was corrected, and the rerun passed 39/39.
- Optional notes N3, N4, and N6 were not taken because they are not required by
  S1/S2 and would expand the minimal fix delta.

## Full write perimeter

Fix changes in checkpoint `ed99e7e`:

- `app/tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py`
- `app/tests/integration/services/queries/working_sections/test_get_user_last_active_step_record_integration.py`
- `app/tests/integration/services/queries/task_step_acknowledgments/test_reassigned_steps_integration.py`
- `app/tests/integration/services/queries/worker_stats/test_worker_stats_endpoint_split_integration.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_1_worker_money_redaction.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`

Handoff artifact written after the checkpoint:

- `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-12_phase1_fix_r2_handoff.md`

Production code changes: none.

Mutation-probe files: none; this finding-scoped fix cycle ran no mutation probes.
The unrelated pre-existing edit in
`docs/architecture/under_construction/implementation/item_cost_calculation/planning/intention.md`
was preserved and was not staged or changed by this session.

Architecture Graph: zero delta. Status remained valid at 116 nodes / 157 edges,
zero stale nodes, revision `b0702c3c…`; no graph write was made.

