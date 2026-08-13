---
plan: phase 4B (category-driven group selection)
role: implementer
state: IMPLEMENTED
date: 2026-08-13
actor: Codex
checkpoint: cfec9df4934f4b7328243b0f55474c8793b7b9d6
---

# Phase 4B implementer handoff — r1

Phase 4B is implemented and checkpointed. `production_cost_groups` now has a
required category owned by the existing `item_major_category_enum`; active
groups are unique per workspace/category; create and update commands enforce
the category identity and basis-version immutability contract; the classifier
and configuration-status query are category-aware; and the HTTP/serializer
surfaces expose the category.

## ⚠ OWNER DECISIONS REQUIRED (1)

1. **OD-1 — migration-environment scope exception.** `app/migrations/env.py`
   gained a four-line comment plus `connection.rollback()` immediately after
   `_cold_build_workspace_callbacks(connection)`. That callback performs a
   read-only preflight query, which opens SQLAlchemy's implicit transaction
   before Alembic establishes its per-migration transaction. Without clearing
   that transaction, `alembic upgrade` appeared successful but did not persist
   the revision or DDL. The change was required for the requested migration to
   commit and for upgrade/downgrade verification to be meaningful, but
   `env.py` was outside the phase prompt's production-file fence. Retain it or
   route the transaction-boundary repair to the migration-infrastructure owner.

## Checkpoint and perimeter

- Checkpoint: `cfec9df4934f4b7328243b0f55474c8793b7b9d6`
- Commit subject: `CHECKPOINT (not approved): item-cost phase 4B implement r1 — category-driven groups and status`
- The checkpoint includes the six-link Architecture Graph delta in
  `.archgraph/architecture.yml`, the implementation, tests, tracker, and
  phase Review log. This handoff is deposited after the checkpoint.
- Expected scope was respected except for the explicit `app/migrations/env.py`
  exception above. No item-domain code, new route, list category filter, or
  role-gate change was introduced.

## Implementation record

- Migration: `5caae620088c_add_major_category_to_production_cost_groups.py`
  preflights every group row (deleted rows included), reports ids and counts
  from sections, basis versions, and evaluations, raises before DDL, reuses
  the enum with `create_type=False`, adds no default/backfill, and creates the
  partial unique `(workspace_id, major_category)` index.
- Model and documentation: `ProductionCostGroup.major_category` uses the
  existing enum and the same partial unique index; the economics README records
  enum ownership and the inert `create_type=False` model flag.
- Requests and commands: create requires a known category; update accepts an
  optional category, with `None` as a no-op; name checks precede category checks;
  category conflicts translate to `ITEM_COST_GROUP_CATEGORY_TAKEN`; any basis
  row, including deleted, blocks a category flip with
  `ITEM_COST_GROUP_CATEGORY_IMMUTABLE` and both group/current-category values.
- Domain/query/API: `resolve_major_category` never guesses; the classifier
  explicitly orders missing category, no group, ambiguity, no basis, no model;
  group and basis selection are category-scoped; status returns exactly
  `categories.{wood,seat}` plus `has_open_cost_model_version`; serializer and
  HTTP body models carry `major_category`.
- Tests: added the category classifier, schema/migration, and command-selection
  suites; amended named phase-2/phase-4 fixtures and request/router tests,
  including T8-7 through T8-10.

## Verification

- Focused suite, run twice: **256 passed** each run.
- Ruff on all changed production, migration, and test files: **passed**.
- Full non-e2e suite, run twice: **1926 passed, 23 failed, 1 deselected**;
  the failure set was identical on both runs and identical to the established
  phase-1 baseline.
- Scoped residue after verification: zero rows in
  `production_cost_groups`, `production_cost_group_sections`,
  `production_cost_basis_versions`, `item_cost_evaluations`,
  `cost_model_versions`, and `cost_model_terms`; zero matching economics audit
  rows. Development Alembic reports `5caae620088c (head)`.
- C1 live/disposable checks: empty upgrade; seeded-row preflight refusal with
  group ids and dependent counts and no DDL; downgrade; upgrade again; one
  reused enum type; exact active partial index; filtered metadata comparison
  clean for the production-cost-group table.

## Mutation ledger

All mutations below were made against the named file, executed, observed, and
then reverted. `Original SHA` is the restored implementation hash. “Green by
design” means the mutation was specifically checking independence from enum
declaration order; it was not left applied.

| File | Mutation | Observed result | Original SHA | Mutant SHA |
|---|---|---|---|---|
| `app/migrations/versions/5caae620088c_add_major_category_to_production_cost_groups.py` | Preflight `RuntimeError` changed to `ValueError` | Failed `tests/integration/models/item_economics/test_phase4b_category_schema.py::test_phase4b_migration_has_report_first_preflight_and_enum_reuse` | `312db2741d06afd6efb281deb389c7f9efae1fbd89dc71a8947d46ba5ea2f18e` | `30f4ac155a4fb8e178c6fed78225f923d7c40fd7d326f8fc8ca8e1b594869a5d` |
| same migration | Added `server_default='wood'` | Failed the same preflight/static node | `312db2741d06afd6efb281deb389c7f9efae1fbd89dc71a8947d46ba5ea2f18e` | `573f149d2889d2d27584a3bd6d16b6f1ac2b6822cbb7c5858eb6cee5f2790537` |
| same migration | Downgrade dropped the reused enum | Failed `...::test_phase4b_migration_downgrade_drops_only_owned_column_and_index` | `312db2741d06afd6efb281deb389c7f9efae1fbd89dc71a8947d46ba5ea2f18e` | `1ba8fd3d03fab2e62e29953fcb0152eb3fd30d61b430ec90f4fe6a201a484415` |
| same migration | Widened unique key with `name` | Failed live `...::test_phase4b_index_conflict_row_shares_only_workspace_and_category` | `312db2741d06afd6efb281deb389c7f9efae1fbd89dc71a8947d46ba5ea2f18e` | `0bb4461c590e7f996b384674c636809e198911dce09061e2d9d234a4c7d0049a` |
| same migration | Removed `is_deleted = false` predicate | Failed live `...::test_phase4b_index_predicate_allows_deleted_row` | `312db2741d06afd6efb281deb389c7f9efae1fbd89dc71a8947d46ba5ea2f18e` | `10857fee2d5e8ddc83151849acbcc818c59a47a77cffa7b1a8b86c068c2397e0` |
| `app/beyo_manager/services/commands/item_economics/_common.py` | Removed category index identity | Failed `tests/unit/services/commands/item_economics/test_item_economics_requests.py::test_integrity_translation_preserves_each_registered_index_identity[uix_production_cost_groups_major_category_active-ITEM_COST_GROUP_CATEGORY_TAKEN]` | `64bb3b3970f56d9d7c41c43846b681bcb919f5f043de277ec6b0dd6ee9467263` | `3b594c367b535a0b74766f9435b390b85d928a561bc9bc14316cdaa94b018b0d` |
| `app/beyo_manager/services/commands/item_economics/update_production_cost_group.py` | Basis query filtered deleted rows | Failed `...::test_category_flip_remains_immutable_when_the_only_basis_is_deleted` | `8763888f77ea8af1f2c0ddce3f31773bf805aae6c50db7dbabf227b4ce1a02e0` | `15c9640c64eb3596d49f5ad5e80188478bfc562af81ae9091a1cdea10be877f1` |
| same update command | Removed `request.major_category != group.major_category` | Failed `...::test_equal_category_is_an_accepted_noop_for_a_versioned_group` | `8763888f77ea8af1f2c0ddce3f31773bf805aae6c50db7dbabf227b4ce1a02e0` | `dccb142c2d54a7e360489028c2d9c161598d10a0a39627df0c4e04b3283e1b9f` |
| same update command | Removed immutability guard | Failed both live-basis and deleted-basis immutability nodes | `8763888f77ea8af1f2c0ddce3f31773bf805aae6c50db7dbabf227b4ce1a02e0` | `78fec94e0068d844ded01155b714a0a8b59e9287cb0011a2f2befdec4044952c` |
| `app/beyo_manager/domain/item_economics/configuration.py` | Removed category filter | Failed V2 wrong-category-group and V4 wrong-basis-group parametrized nodes in `test_phase4b_category_classifier.py` | `e41ab910a3935d58ebadd8531a4bdefe5764d1e80d3cea77fe0659de8d57239e` | `c193c89f46af8c552dde0e19111beffdf42717ea8d12ac0d680282f96558d4ec` |
| same classifier | Removed active-group deleted-row filter | Failed V2b soft-deleted matching-group node | `e41ab910a3935d58ebadd8531a4bdefe5764d1e80d3cea77fe0659de8d57239e` | `581ad077780017ff34654149449b51f4c70885334d8bfdd837adfa4e02974c8b` |
| same classifier | Demoted missing-category precedence below no-group | Failed P1 adjacent-pair node | `e41ab910a3935d58ebadd8531a4bdefe5764d1e80d3cea77fe0659de8d57239e` | `22cc4294a3caca6d84263f0cb782943aba73333e9336c59fb51ca061a096b2cf` |
| `app/beyo_manager/domain/item_economics/enums.py` | Moved missing-category enum member to the end | **13 passed by design**: classifier uses the explicit precedence tuple, not enum iteration | `9490d6195acb0fe58a39c985c7ce175c1e02c19ba0ac1d4897884b08f50376bd` | `6a32b727087541fd1e4710cf4504ecfd79a824187a3950a3bfe9e9323528ccde` |
| `app/beyo_manager/services/queries/item_economics/get_economics_configuration_status.py` | Removed per-category basis-group scope | Failed `tests/integration/services/commands/item_economics/test_phase4b_category_selection.py::test_status_has_exact_per_category_shape_and_scopes_basis_to_each_group` | `ce43ca5f132667b3bba598d8b97aa3bd4f51bc60f6ae7a5e9c38e1cd65144a62` | `1911437b6e71f0995a74b54a31748345f3b1d36a0505deb59ff301fa53d59a3f` |
| `app/beyo_manager/routers/api_v1/item_economics.py` | Removed create-body category field | Failed `...::test_group_router_body_models_keep_category_fields_at_the_http_boundary` | `8ad093a30d7f564c89221d888f2b66fb143572c7686ead57e85f0577e9ae9aee` | `56a99ea50ab28480700e1dcde252b88f1f68044335df283e058e60ae5bee123` |
| `app/beyo_manager/domain/item_economics/serializers.py` | Removed serialized group category | Failed `...::test_category_flip_without_basis_updates_row_and_audits_existing_event` with missing category key | `1c23fd95cfb8f02de24792ee65191d688ae9d8f3f75efa596af08b3d5c60be35` | `c00dfbcfbc0bde16ee05158246f1b71833528e84081b2b687db3179a0bf7b7dc` |
| `app/beyo_manager/services/commands/item_economics/requests/__init__.py` | Removed create request category | Failed all three missing/unknown/wrong-case parametrized rows in `test_group_create_request_rejects_missing_and_non_vocabulary_categories` | `ba623b4e25db9f6f6f72a550f521c821c32958b1e264dfcd3f835eb558d43ee6` | `e095e0053dab19f989623812dede2f5d8b5ee2b692b98688b710bda84e65952c` |
| `app/beyo_manager/services/commands/item_economics/create_production_cost_group.py` | Disabled category pre-check | Failed `...::test_category_create_precheck_reports_taken_identity_and_category` with raw unique error | `51a7b3e37ba605648d0154f10f16543d6efa1c1fce9a2e31e3406206f6ca07e9` | `2fb2c09d4c82a3e3b25960cc3ba3da6f236e90af44d78472f25c1996bb133860` |

The attempted removal of the status query's deleted-basis filter was not
retained as a mutation row: the query loader already excludes deleted basis
rows, so that particular source edit was vacuous rather than a meaningful
arbiter. The production behavior remains correct and the per-category scope
mutation above bites.

## Full-suite baseline failure set

The 23 failures were unchanged from the established baseline:

1. `tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`
2. `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events`
3. `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing`
4. `tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`
5. `tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
6. `tests/integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`
7–9. The three `set_current_stored_amount_inventory` tests in `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py`
10–13. The four batch/ordering tests in `tests/integration/services/commands/working_sections/`
14–15. The two audit-log tests in `tests/integration/test_audit_log.py`
16–17. The two legacy dimension-migration tests in `tests/unit/domain/shopify/test_dimension_migration.py`
18. `tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`
19. `tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
20. `tests/unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`
21–22. The two item-router tests in `tests/unit/test_items_router.py`
23. `tests/unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`

## Architecture Graph

Before implementation, the initialized graph was oriented at the existing
`production_cost_groups` table, create/update commands, configuration-status
endpoint, and item-economics domain. After implementation, one atomic additive
`archgraph_apply_changes` batch recorded six source links:

- table model and migration on `table-production-cost-group`;
- classifier on `domain-item-economics`;
- status query on `endpoint-item-economics-status`;
- create and update command implementations on their existing command nodes.

No new graph nodes or relationships were needed, and the two pending inferred
review items were not adjudicated. Final graph status: 148 nodes, 188 edges,
zero diagnostics, zero stale nodes, 2 pending reviews, revision
`5e4f368df1e17bdbad477428f691e91ad15ece9bd9455b668ebe7bf95b4e76f0`.

## Next session

The checkpoint is deliberately **not approved**. The reviewer should first
resolve OD-1's scope disposition, then verify the implementation against the
phase criteria and mutation ledger. The next phase may consume the category
resolver and the per-category status contract after review closure.
