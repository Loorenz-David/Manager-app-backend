---
plan: phase 4 (configuration services)
role: fix
state: IMPLEMENTED
date: 2026-08-12
actor: Codex
---

# Phase 4 fix-r2 implementer handoff

Review-r1 corrections are implemented and checkpointed at
`4e19506b2c17ec2999659642a8a708a79e33b72e1`:
`CHECKPOINT (not approved): item-cost phase 4 fix r2 — coverage and request bounds`.

⚠ OWNER DECISIONS REQUIRED (0)

## Delivered

- Added command-backed C1–C11 coverage: all 20 admission outcomes, both chain
  adjacency boundaries, genuine two-session races, rate underflow and
  canonicalize-then-derive persistence, all 12 term-shape cells, duplicate
  prechecks, guarded-delete serial/interleaving behavior, all six status-query
  fixtures, all three list-query behaviors, all nine registered audit events,
  and the complete 13-route role/router surface.
- Added request bounds for fixed cost, paid hours, utilization, percentage
  terms, and fixed term amounts.
- Removed the router's derived rate input, dead `_common` scaffolding, and the
  vestigial model-delete assignment. Cost-model branching now compares enum
  members directly. Router percent documentation remains on the router body
  model, and no term mutation routes were added.

## Verification

- Focused phase suite: **126 passed**.
- Changed-file Ruff: **passed**.
- Full non-e2e suite: **1,875 passed / 23 known failures / 1 deselected / 2
  warnings**. The 23 failures are the established baseline set; no new failure
  appeared. Full-tree Ruff reports the pre-existing repository-wide result of
  **131 findings**; all changed phase files are clean.
- `git diff --check`: passed before checkpoint.

## Mutation ledger

Each mutation was applied in a disposable local clone because the managed
workspace's `.git` directory cannot create worktrees. The clones were not part
of the main worktree or checkpoint. Main and mutated file SHA-256 values are
recorded for reproducibility.

| Criterion | Mutation result | Main SHA-256 | Mutated SHA-256 | Observed node |
|---|---|---|---|---|
| C1/S2 | Dropping the open-row `is_deleted = false` filter fails the soft-deleted-open admission row. | `acd64c36b8de89530d9aee50e5a1f0c737bd538bb0b6c2b816c0bb6edad4b5cb` | `d613591f8374ea70537fd32ff7891622f514225a49fe39a79c42df4525c4522f` | `test_c1_admission_matrix_has_one_exact_outcome_per_chain[soft-deleted-open-treated-as-none-soft-deleted-none-None-basis]` |
| C2 | Dropping predecessor closure fails the v1-at-d boundary. | `acd64c36b8de89530d9aee50e5a1f0c737bd538bb0b6c2b816c0bb6edad4b5cb` | `cd2bf7464a6d692d1c2217125827c35aed852b2f62b7d5f4d83ce813f2a40124` | `test_c2_adjacency_uses_command_built_orm_versions_and_is_applicable[v1-at-basis]` |
| C3 | Mapping the basis index to the model identity fails the registered translator assertion; clean real races pass for both chains. | `3b594c367b535a0b74766f9435b390b85d928a561bc9bc14316cdaa94b018b0d` | `71249f1a9c7c25351f24dc59a6c43ed758a7c28130e7c6948d76d9cd52a91d22` | `test_integrity_translation_preserves_each_registered_index_identity[uix_production_cost_basis_versions_open-ITEM_COST_CONCURRENT_BASIS_VERSION]` |
| C4 | Changing hour canonicalization from 2 dp to 4 dp fails the persisted canonical hours/rate assertion. | `904b635fcca7670729d2d3d470ea6b2f32cc82223bacdca852a653cbf5424860` | `1008720dd6f60a6b3c48b5dbb8d43d17abbdf29a86b53fa874eba713dfb8b368` | `test_configuration_commands_canonicalize_chain_and_status` |
| C5 | Collapsing all integrity identities to the basis-concurrency marker fails the purchase-term identity assertion. | `3b594c367b535a0b74766f9435b390b85d928a561bc9bc14316cdaa94b018b0d` | `6d425e12055c7f317633f0786feb30ed630a3f065c025240d62e3f863b078e05` | `test_integrity_translation_preserves_each_registered_index_identity[uix_cost_model_terms_purchase_cost-ITEM_COST_PURCHASE_TERM_DUPLICATE]` |
| C6(a) | Dropping the locked reference re-check makes the serial in-use row stop raising. | `196fa87033064c79886f66899c4ff6f0b2b0faf6fde1fa301203e55e50d4104c` | `28a6abca6b7d8facbfd19b0957ae66533a54b280cc4d84c5224403da8ecabe72` | `test_c6_serial_delete_guard_rechecks_all_evaluation_references[basis]` |
| C6(b) | Dropping `FOR UPDATE` lets the interleaved FK insert complete before release. | `196fa87033064c79886f66899c4ff6f0b2b0faf6fde1fa301203e55e50d4104c` | `80646d9dd7c6fcb3b0256f079d9bfae29325145b1eb21a88b92f2cadc4eb2373` | `test_c6_interleaved_fk_insert_is_blocked_by_the_delete_row_lock_then_proceeds` |
| C8 | Swapping the first two explicit precedence entries returns the wrong no-group status. | `3e4412f01c4925e90b855b81a05303823948d86b4d39cb70c7e2f6e63d08b195` | `a5de2350b4ee03deddf0300684937682884c96067adbf83e225dd0c4f6a023f3` | `test_c8_status_query_enumerates_each_first_failure_and_success` |
| C9 | Removing the router percent-field description fails the documentation assertion. | `891f9a18f4a72d4bc619c62fd8ea24c3a8f34702eeae5f8b0c8bddba5474b792` | `acfa6b6fff2d4765c9b279c92ff4a98da08dd28bf4149742806c3213ef279df0` | `test_router_body_percent_field_carries_planning_allocation_documentation` |
| C11 | Removing MANAGER from the first route allow-list returns 403 for the manager retention row. | `891f9a18f4a72d4bc619c62fd8ea24c3a8f34702eeae5f8b0c8bddba5474b792` | `e6c3a5fceb26166d00d5f9cbaaf8f07251f9ef3db125dc24ba0099a4e8cce663` | `test_every_configuration_route_retains_admin_and_manager_access[post-cost-groups-manager]` |
| B2 | Removing `gt=0` from fixed monthly cost lets the negative bound case pass. | `904b635fcca7670729d2d3d470ea6b2f32cc82223bacdca852a653cbf5424860` | `22ea01255e468b1d681adbbb370fd79ba2270f0020390d6b1775d9e6d05f9ea2` | `test_basis_request_rejects_each_out_of_range_numeric_field[fixed-negative]` |
| S1 | Re-adding the derived rate field fails the router absence assertion. | `891f9a18f4a72d4bc619c62fd8ea24c3a8f34702eeae5f8b0c8bddba5474b792` | `abcc8c31943313e19fd8422a87b002f155772dfcc2a1c84e0bae2ccc3aac547b` | `test_router_surface_has_no_term_mutation_and_no_derived_rate_input` |

## Architecture Graph

Graph status/orientation was read only. The initialized graph remained valid at
revision `bf6dad5b9264937b5950366affe9910dcaacf7abd68a42114bb52fa327e68262`.
Graph delta: **zero**; no graph mutation was performed.

## Write perimeter

Checkpoint production files:

- `app/beyo_manager/routers/api_v1/item_economics.py`
- `app/beyo_manager/services/commands/item_economics/_common.py`
- `app/beyo_manager/services/commands/item_economics/create_cost_model_version.py`
- `app/beyo_manager/services/commands/item_economics/delete_cost_model_version.py`
- `app/beyo_manager/services/commands/item_economics/requests/__init__.py`

Checkpoint test files:

- `app/tests/unit/services/commands/item_economics/test_item_economics_requests.py`
- `app/tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py`
- `app/tests/unit/routers/api_v1/test_item_economics_router.py`

Checkpoint planning records:

- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_4_configuration_services.md` (Review log append)
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md` (phase-4 tracker row only)

The disposable mutation clones and their mutations are not part of the main
worktree. The handoff is the only artifact deposited after the checkpoint.

## Coordinator fold-ins

- Consume this handoff after the checkpoint; the phase-4 tracker is already
  `IMPLEMENTED` and the Review log contains the append-only evidence.
- A reviewer can re-run the focused node set and the mutation ledger above.
- No owner decision or Architecture Graph promotion is pending from this fix
  cycle.
