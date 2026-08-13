---
plan: phase 4 (configuration services)
role: fix
state: IMPLEMENTED
date: 2026-08-13
actor: Codex
---

# Phase 4 fix-r3 implementer handoff

The phase-4 fix-r3 work is implemented and checkpointed at `74b280b`:
`CHECKPOINT (not approved): item-cost phase 4 fix r3 — test coverage closure`.

⚠ OWNER DECISIONS REQUIRED (0)

## Delivered

This cycle was test-side only. No production file remains changed. The shipped
coverage now:

- maps all 10 §7A.4 admission-table rows across both basis and model chains,
  including live `effective_from IS NULL` open rows and the predecessor
  `effective_to` assertion;
- asserts the exact registered identity token on C3's genuine two-session
  race and bounds both audit gates with `asyncio.wait_for(..., timeout=0.3)`;
- gives each of C10's six list filters a sole-cause fixture whose filtered row
  competes inside the `limit=1` slice, and covers both rename paths: 422
  pre-check and translated DB conflict;
- pins float-to-decimal text parsing with `2.675`; and
- adds adjacent accepted/rejected request-boundary cases for fixed cost,
  hours, utilization, percent, and fixed amount.

## Verification

- Focused phase/router suite: **139 passed**.
- C3/C6 concurrency subset: **5 passed**, run twice.
- Full non-e2e suite (`PYTHONPATH=. pytest -q -m 'not e2e'`): **1892 passed,
  23 failed, 1 deselected, 2 warnings**. The 23 failures are exactly the
  recorded phase-1 baseline set; no new failure was introduced.
- Ruff on both changed test files: **passed**.
- `git diff --check`: **passed**.
- Architecture Graph status was read before and after implementation: valid,
  revision unchanged at
  `bf6dad5b9264937b5950366affe9910dcaacf7abd68a42114bb52fa327e68262`, 148
  nodes / 186 edges, 47 pending review items, zero delta. No graph mutation was
  performed.

## Mutation ledger

Each mutant was applied with `apply_patch`, run against the targeted test, and
reverted. The final production files were byte-identical to their pre-probe
hashes. The observed red nodes are the actual pytest node ids.

| Finding | Mutation | Main SHA-256 → mutant SHA-256 | Observed red node |
|---|---|---|---|
| B1 | Remove `open_from is not None` guard | `3b594c367b535a0b74766f9435b390b85d928a561bc9bc14316cdaa94b018b0d` → `d8c41d1ad38725787d18085e1378eea499b6fd298c6eb01b52dace48fef70ba0` | `test_c1_admission_matrix_has_one_exact_outcome_per_chain[table-row-5-null-open-at-or-before-today-basis]`; same model node |
| B2 | Drop group `workspace_id` filter | `75d81316163fc545764f63421d576775817095c518c668b636bb7711bfae7d4e` → `b04eab86683afefc954f38a782b6b7fd60639bf6d48b4ad61d7501d75c390c29` | `test_c10_each_list_filter_has_a_sole_cause_fixture[groups-workspace]` |
| B2 | Drop group `is_deleted` filter | `75d81316163fc545764f63421d576775817095c518c668b636bb7711bfae7d4e` → `6c28c4173b394b37923e63562a4ee56f25f5db8f1d7149058b00f386bc870ec4` | `test_c10_each_list_filter_has_a_sole_cause_fixture[groups-is-deleted]` |
| B2 | Drop model `is_deleted` filter | `1841fae0987ff2b2daa316592ce4ab073a5e019e7f782041520902919312fa50` → `96daa161bd592512e12be620f0f29a7f3ef7f64d23c2a15eb46db5d7ea550552` | `test_c10_each_list_filter_has_a_sole_cause_fixture[models-is-deleted]` |
| B2 | Drop basis `workspace_id` filter | `e4b752498d303f91fc21a8332c2809775ab5f3e111edbebe95b9ccb08d356883` → `084e287d94de28dd338737c73fb3851506224bc93b36b358b513bce2d943efc5` | `test_c10_each_list_filter_has_a_sole_cause_fixture[basis-workspace]` |
| B2 | Delete rename pre-check | `9f4241643ba5db8a35478f82c795c3603a60cc09ddae00730beebb59c589f7ee` → `3e397be547b3c8947f1567ace90ee56e3173306ce913899ade723be4df485e8b` | `test_c10_group_rename_collision_precheck_is_a_validation_error` |
| S1 | Translate basis race by model identity | `3b594c367b535a0b74766f9435b390b85d928a561bc9bc14316cdaa94b018b0d` → `71249f1a9c7c25351f24dc59a6c43ed758a7c28130e7c6948d76d9cd52a91d22` | `test_c3_real_concurrent_open_insert_translates_the_loser[basis]` |
| S2 | Parse float with `Decimal(v)` | `904b635fcca7670729d2d3d470ea6b2f32cc82223bacdca852a653cbf5424860` → `66626dee8d48b1d2af6e8a3734d19df1a7fe28babed63b5fb739ca51d78794a8` | `test_basis_request_parses_float_as_decimal_text_before_quantization` |
| S3 | Change fixed-cost `gt=0` to `ge=0` | `904b635fcca7670729d2d3d470ea6b2f32cc82223bacdca852a653cbf5424860` → `3de51c176775798c09fc58f5cee61c413c0e1a6497b226c80c947780050e9b8d` | `test_basis_request_rejects_each_out_of_range_numeric_field[fixed-zero]` |

The model-workspace and basis-`is_deleted` cases remain protected by the existing
combined C10 ordering/limit+1 arbiter. Optional N4/N5/N6 were not taken; they
remain documented as non-blocking notes.

## Write perimeter

Checkpoint files:

- `app/tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py`
- `app/tests/unit/services/commands/item_economics/test_item_economics_requests.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_4_configuration_services.md`

The following production files were used only for apply/run/revert mutation
probes and are clean and byte-identical to their pre-probe values:

- `app/beyo_manager/services/commands/item_economics/_common.py`
- `app/beyo_manager/services/commands/item_economics/queries/list_groups.py`
- `app/beyo_manager/services/commands/item_economics/queries/list_basis.py`
- `app/beyo_manager/services/commands/item_economics/queries/list_models.py`
- `app/beyo_manager/services/commands/item_economics/update_group.py`
- `app/beyo_manager/services/commands/item_economics/requests/__init__.py`

This handoff is the only artifact deposited after the checkpoint. No coordinator
fold-in or owner decision is required; the phase is ready for re-review.
