---
plan: phase 4B (category-driven group selection)
role: fix
state: IMPLEMENTED
date: 2026-08-13
actor: Codex
---

# Phase 4B fix-r1 implementer handoff

Implemented and checkpointed at `8285cf1`:
`CHECKPOINT (not approved): item-cost phase 4B fix r1`.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required from this session. The N5 Architecture Graph
source-link correction was performed by the coordinator at revision
`5c60534d`, commit `5d8b6a6`; this session skips the graph step as instructed.

## Delivered

- **B1:** `app/migrations/env.py` now commits the cleanup transaction as the
  last statement of `_do_run_migrations()`'s `finally`. This makes a genuinely
  cold Alembic build persist its migration head while persisting no synthetic
  migration workspace or anchor-owned pause reasons.
- **S1:**
  `test_phase4b_model_index_predicate_is_soft_delete_partial_unique` directly
  inspects `ProductionCostGroup.__table__.indexes` and asserts the named index's
  PostgreSQL predicate text is exactly `is_deleted = false`.
- **S2:**
  `test_status_shared_model_failure_is_repeated_in_each_category_block` now
  asserts the complete status payload by exact dictionary equality, including
  `has_open_basis_version: true` for the configured wood group even though the
  shared cost-model failure makes that category non-evaluable.
- The phase plan Review log and master-plan tracker were updated to
  `IMPLEMENTED`; master-plan §10 contains the timed C9 state evidence.

## Focused selector and verification

The focused selector used for both runs was this exact command from
`backend/app/`:

```text
PYTHONPATH=. pytest -q \
  tests/unit/domain/item_economics/test_phase4b_category_classifier.py \
  tests/integration/models/item_economics/test_phase4b_category_schema.py \
  tests/integration/services/commands/item_economics/test_phase4b_category_selection.py \
  tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py \
  tests/integration/services/commands/item_economics/test_configuration_commands.py \
  tests/integration/models/item_economics/test_item_economics_schema.py \
  tests/unit/services/commands/item_economics/test_item_economics_requests.py
```

This is a 200-test selector, and it passed **200/200 twice**. It is not the
reviewer r1's broader 256-test selection; the difference is intentional and is
named here so the reviewer can reconcile the counts. The full non-e2e run was
`PYTHONPATH=. pytest -q -m 'not e2e'`: **1927 passed, 23 known baseline
failures, 1 deselected, 2 warnings**. The 23 failures were the established
pre-existing set. Ruff passed on the changed Python files and `git diff --check`
passed.

## C9 disposable end-state evidence

On disposable database `beyo_manager_4b_fix_r1_verified`, the from-scratch
recipe completed in **1.70s**. A state query returned:

```text
alembic_version | workspaces(mig_cold_build_workspace) | pause_reasons(owner) | mig_cold_build_workspace rows
5caae620088c   | 0                                     | 0                    | 0
```

The database was dropped after the query. The configured `beyo_manager`
database remained at `5caae620088c (head)`. Its scoped residue query returned
zero rows for `production_cost_groups`, `production_cost_group_sections`,
`production_cost_basis_versions`, `item_cost_evaluations`,
`cost_model_versions`, `cost_model_terms`, and matching `audit_logs` events
(`production_cost%`, `cost_model%`, `item_cost%`).

## Full mutation ledger

Every mutation was applied at the named site, run, observed, and reverted. The
observed red set below is the complete set from that run; B1 is a state-query
mutation rather than a pytest mutation and therefore records its complete
observed state set.

| Finding | Real mutation file | Mutation | Main SHA-256 → mutant SHA-256 | Full observed red/state set | Restored SHA-256 |
|---|---|---|---|---|---|
| B1 / C9 | `app/migrations/env.py` | Reverted the authorized `connection.commit()` edit in the `finally` block; disposable cold build `beyo_manager_4b_fix_r1_b1` | `09261d91c7813483193fc93dd62e422719a956bb0694fda2af6eb586af4b4e13` → `db98e1ee8c215861f346bbc69a4b29643f997dbc6721a7a028108a44280beae5` | State set: `alembic_version` reached `5caae620088c`; `workspaces` row for `mig_cold_build_workspace` = **1**; owned `pause_reasons` = **7**; `mig_cold_build_workspace` rows = **1** | `09261d91c7813483193fc93dd62e422719a956bb0694fda2af6eb586af4b4e13` |
| S1(i) | `app/beyo_manager/models/tables/item_economics/production_cost_group.py` | Deleted `postgresql_where=text("is_deleted = false")` from `uix_production_cost_groups_major_category_active` | `27d99ecb8b3a0e5ea5a84b4f214d60a94029308e4b2cb48d33875dea99e17b5f` → `4f2076e1a7405a94f88c3515fad8370d706a53c95a6febe2c5597755eb439afa` | `tests/integration/models/item_economics/test_phase4b_category_schema.py::test_phase4b_model_index_predicate_is_soft_delete_partial_unique` | `27d99ecb8b3a0e5a84b4f214d60a94029308e4b2cb48d33875dea99e17b5f` |
| S1(ii) | `app/beyo_manager/models/tables/item_economics/production_cost_group.py` | Flipped that model predicate to `is_deleted = true` | `27d99ecb8b3a0e5a84b4f214d60a94029308e4b2cb48d33875dea99e17b5f` → `ceb5248a80d8fa6f9a9c9a1457ce7a93cdf7854e3938e97c04e007fc47d99b52` | `tests/integration/models/item_economics/test_phase4b_category_schema.py::test_phase4b_model_index_predicate_is_soft_delete_partial_unique` | `27d99ecb8b3a0e5a84b4f214d60a94029308e4b2cb48d33875dea99e17b5f` |
| S2 | `app/beyo_manager/services/queries/item_economics/get_economics_configuration_status.py` | Collapsed `has_open_basis_version` to `has_open_basis and evaluable` | `ce43ca5f132667b3bba598d8b97aa3bd4f51bc60f6ae7a5e9c38e1cd65144a62` → `a09aa514df16d8536a1f5545bf526d31e560eaecd9f4b7ab96de6bfa16e68bc0` | `tests/integration/services/commands/item_economics/test_phase4b_category_selection.py::test_status_shared_model_failure_is_repeated_in_each_category_block` | `ce43ca5f132667b3bba598d8b97aa3bd4f51bc60f6ae7a5e9c38e1cd65144a62` |

The two S1 and one S2 probe files were production files touched only for
apply/run/revert mutation probes; they are byte-identical to their restored
hashes and are not part of the shipped fix. `app/migrations/env.py` is both a
fix file and the B1 probe file; its final hash is the restored/main hash above.

## Disposable resources

Created and dropped during this cycle:

- `beyo_manager_4b_fix_r1_b1` — B1 reverted-edit ghost-state probe.
- `beyo_manager_4b_fix_r1_c9` — initial corrected C9 state verification.
- `beyo_manager_4b_fix_r1_verified` — timed corrected C9 verification.

No `beyo_manager_4b_fix_r1%` disposable database remains.

## Full write perimeter

Checkpoint `8285cf1` contains exactly:

- `app/migrations/env.py`
- `app/tests/integration/models/item_economics/test_phase4b_category_schema.py`
- `app/tests/integration/services/commands/item_economics/test_phase4b_category_selection.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_4b_category_selection.md`

This handoff is deposited after that checkpoint. Probe-only production files
are listed separately in the mutation ledger. No other production file was
changed. No Architecture Graph mutation was performed by this session; the
coordinator-owned N5 correction is recorded above.

## Judgment calls and carry-forward

- `connection.commit()` is deliberately the final statement of the migration
  `finally` block so cleanup DELETEs persist after Alembic's per-migration
  transactions commit. N6 (partial-target cold-build cleanup crashing before
  `pause_reasons` exists) remains routed to the migration-infrastructure owner
  and was not changed here.
- C6(b) is explicitly collapsed per the coordinator's fix-r1 amendment; C6(a)'s
  exact seat block plus the shared-model exact payload row discharges it.
- No semantic or production-code deviation remains. The only post-checkpoint
  artifact from this session is this handoff.
