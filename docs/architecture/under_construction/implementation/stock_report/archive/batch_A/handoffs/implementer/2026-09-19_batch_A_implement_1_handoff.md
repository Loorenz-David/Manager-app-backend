---
plan: batch A (1, 2, 3)
role: implement
round: batch_A-implement-1
state: PARTIAL_NOT_READY_FOR_REVIEW
date: 2026-09-19
actor: Codex
---

# Batch A implementation handoff

## Gate check record

1. Intention header: `status: RATIFIED`.
2. Batch A tracker: `IMPLEMENTATION_PROMPT_READY`.
3. Start tree: clean.
4. Alembic head before implementation: `['ce99896e6f49']`.

## Current implementation state

This batch is not ready for review. The session established the phase-1 schema/domain foundation,
generated revision `10d97764a5a7_create_stock_report_tables.py` from autogenerate, removed the
three unrelated schema-drift operations it emitted, and added initial phase-2 matcher and phase-3
consistency/repair scaffolding. It did not complete the specified criterion-by-criterion tests,
mutation ledger, routes, locking implementation, repair ordering semantics, L2, L4, or graph delta.
Accordingly no phase is claimed IMPLEMENTED and no checkpoint was made.

### Migration hand edits

The generated revision had unrelated removals for `email_sync_states` and `step_state_records`; those
were removed from both directions. The planned check constraints and partial-index predicates are
present. The configured development database was not upgraded or downgraded.

### Verification performed

- `python -m compileall -q beyo_manager`: passed.
- Domain import probe: four stock tables registered; active/terminal assignment-state partition is true.
- `pytest tests/unit/domain -q --maxfail=1`: 705 passed, then an unrelated existing failure:
  `tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_seat_height_without_height_maps_without_zero_values`.
  The observed extra result is `extensions_quantity: '0'`; no stock-report code is in that path.
- Current focused stock-report evidence: 28 tests passed across domain, schema, consistency,
  repair, and router surfaces before later focused additions; individual later checks include
  consistency (4), repair (4), schema (3), settings (2), and router roles (8), all green.
- Focused new-source `ruff check`: clean. A broad L4 was started but its final process output was
  truncated before a trustworthy failure-ID set could be recorded, so it is intentionally not
  claimed as a batch L4 stamp.
- Latest combined focused perimeter: `41 passed` (unit domain, schema integration, consistency
  integration, repair integration, and stock-report router tests); `git diff --check` passed.
- Latest full Batch-A-focused perimeter (including reset integration): `76 passed`; `git diff --check`
  passed. This is progress evidence only, not the required final L2 stamp: named mutation probes,
  the coverage map, final review logs, the graph delta, and the two-way L4 baseline comparison remain.
- Latest focused perimeter after Scanner coercion, reset-order, priority-group net-repair, and raw-SQL
  server-default coverage: `79 passed`; scoped `ruff check` and `git diff --check` passed.
- Latest focused perimeter after repair-event emission, full live row/assignment locks, and expanded
  divergence-kind coverage: `83 passed`; `git diff --check` passed. A broad L4 was also allowed to
  complete, but the tool detached before exposing its terminal summary; its cache contains a heavily
  pre-existing mixed failure set, so this is not a valid L4 stamp or two-way comparison.
- Schema integration now has nine passing checks, including terminal-to-active partial-index release
  and active duplicate rejection.
- Current full Batch-A-focused stamp: `87 passed`; scoped `ruff check` and `git diff --check` passed.
- Current full Batch-A-focused stamp after the exhaustive state-map and real-ORM matcher vectors:
  `97 passed`; `git diff --check` passed.
- Scanner matcher hand-walk H1–H16, including H3/H4/H9/H11/H14 variants, now runs against
  unflushed real `Item` instances: `54 passed` in `test_criteria_matcher.py`.
- The seed kit now uses F0's seat-category and canonical item properties, and purge removes its
  deterministic users; helper/query/repair integration evidence: `16 passed`.
- The migration downgrade now explicitly removes all four owned PostgreSQL enum types; its structural
  contract test passes (`2 passed`).
- Consistency reads now use `populate_existing=True`, so raw-SQL drift planted in the same session is
  observable; the task-flag repair proof also verifies task stamps remain unchanged (`7 passed`).
- Current full Batch-A-focused stamp: `122 passed`; `git diff --check` passed.
- Repair now re-runs the consistency instrument before returning and raises on any remaining
  non-signature divergence; its suite remains green (`8 passed`).
- Goal-total manual repair now has a direct history-record target/record proof; repair suite:
  `9 passed`.
- Repair now re-derives divergences under row/assignment locks, and repair-record warnings accept an
  optional delta diagnostic; the repair suite remains green.
- Current full Batch-A-focused stamp: `124 passed`; scoped `ruff check` and `git diff --check` passed.
- Raw-SQL drift visibility is now covered for both task flags and identity-mapped stock-report rows;
  consistency suite: `10 passed`.
- Current full Batch-A-focused stamp: `125 passed`; `git diff --check` passed.
- `repair_stock_report.not_repaired` now returns full signature divergence records (rather than bare
  kind strings), matching Plan 3 C4(a); repair suite remains green (`10 passed`).
- Final focused perimeter rerun: `139 passed` across the Batch-A domain, model, helper, query,
  repair, reset, and router tests; scoped `ruff check` passed and `git diff --check` passed.
- A disposable pre-edit HEAD baseline completed: `3103 passed, 21 failed, 1 skipped` in 70.32s.
  The 21 failure IDs are existing non-stock-report failures.
- Current full non-E2E run after the additional deleted-assignment coverage: `3231 passed,
  21 failed, 1 skipped` in 67.83s. The failure IDs match the pre-edit non-stock-report baseline;
  no stock-report failure is present. This is a valid two-way comparison, but L4 is not claimed
  green because the repository baseline itself has 21 failures.
- The infrastructure assertion that hard-coded the former 109-table count now derives the expected
  count from `expected_public_tables()`, so the four new stock-report tables are treated as a
  legitimate schema extension while the unenumerated-table guard remains active.
- Latest full non-E2E run after the additional contract tests: `3241 passed, 21 failed, 1 skipped`;
  the 21 failures are outside the stock-report perimeter, and no Batch-A test failed. The known
  baseline failure count remains unchanged while the passing count increased with the new tests.

## Write perimeter

Changed/created paths are the stock-report domain/models/services/migration, task flag, settings,
client-id map, and reset integration shown by `git status --short`. The temporary mutation probes
listed below were restored immediately; no scratch files were retained.

### Mutation evidence (in progress)

| Plan row | Temporary mutation | Observed red test | Restored |
|---|---|---|---|
| Plan 3 C1(a) | omitted `quantity_in_queue` from the counter-divergence field loop | `test_counter_and_signature_divergences_are_reported` failed: expected `counter_in_queue` was missing | yes |
| Plan 1 C4(m) | removed `.lower()` from understood string normalization | `test_normalization_value_table` failed for `Teak` and `Straße` vectors | yes |
| Plan 2 C5(j) | expanded tokenizer delimiters to include `&` | `test_wildcard_and_token_matching_table` failed: `Up & Down` became `value_not_accepted` | yes |
| Plan 3 C6(f) | serialized `None` as text rather than SQL NULL in repair records | `test_repair_records_one_net_change_per_priority_order_field` failed: expected NULL but saw `"None"` | yes |
| Plan 2 C4(o) | changed drawer numeric recognition from ASCII `[0-9]` to Unicode `\d` | `test_scanner_tables_and_drawer_ascii_rules` failed: Arabic-Indic `٤` mapped to `3-5` | yes |
| Plan 1 C6(b) | mapped `pending` to `in_progress` | `test_task_state_map_is_exact[pending-in_queue]` failed | yes |
| Plan 3 C1(k) | removed the stock-report-item workspace predicate | `test_consistency_does_not_report_foreign_workspace_drift` leaked foreign counter/signature drift | yes |
| Plan 1 C4(n) | changed `str.lower()` normalization to `str.casefold()` | `test_normalization_value_table[raw12-expected12]` failed: `Straße` became `strasse` instead of `straße` | yes |
| Plan 1 C4(h) | changed the list guard from `all(isinstance(v, str))` to `any(...)` | `test_normalization_value_table[raw6-expected6]` failed on mixed `['Teak', 1]` with an AttributeError | yes |
| Plan 1 C4(g) | removed the `any(v.strip() for v in value)` non-blank guard | `test_normalization_value_table[raw5-expected5]` failed: all-blank list normalized to `['']` | yes |
| Plan 1 C4(b) | removed `.strip()` from scalar normalization | `test_normalization_value_table[raw1-expected1]` failed: `"  Teak "` retained whitespace | yes |
| Plan 1 C4(e) | replaced `sorted(set(...))` with an order-preserving list comprehension | normalization and signature golden-vector tests failed on duplicate/order-sensitive values | yes |
| Plan 1 C7(b) | removed `resolved_early` from `TERMINAL_ASSIGNMENT_STATES` | `test_assignment_state_partition_includes_resolved_early_as_terminal` failed: the enum partition was incomplete | yes |
| Plan 2 C5(m) | returned matcher failures in encounter order instead of sorting by criterion key | `test_matcher_reports_all_sorted_failures` failed: `wood_group` appeared before `quantity` | yes |
| Plan 3 C6(a) | stopped sorting `NULL` priority orders after assigned orders during repair | `test_repair_applies_nullness_before_priority_density` failed with the null row taking the first slot | yes |
| Plan 2 C2(d) | skipped the `EXCLUDED_ITEM_PROPERTY_KEYS` removal pass | `test_build_item_property_bag_scanner_table` failed: `qty_extensions` leaked into the bag | yes |
| Plan 2 C2(a) | removed numeric `.0` coercion (`str(value).removesuffix(".0")`) | scanner bag table failed for numeric `4.0`, producing `"4.0"` instead of `"4"` | yes |
| Plan 2 C1(b) | removed `/` from the Scanner tokenizer delimiter set | `test_wildcard_and_token_matching_table` failed for `Oval/Rectangular` | yes |
| Plan 2 C3(a) | replaced derived wood-group assignment with `None` | scanner property-bag table failed for Teak/Oak group derivation | yes |
| Plan 3 C1(m) | removed `populate_existing=True` from the stock-report row consistency read | `test_consistency_observes_raw_counter_drift_in_an_identity_mapped_row` failed to observe the planted counter drift | yes |
| Plan 3 C6(b) | changed the Core flag update's `updated_at=Task.updated_at` self-assignment to `Task.created_at` | `test_task_flag_repair_does_not_change_task_stamps` failed: the task timestamp changed | yes |
| Plan 3 C6(e) | cleared `changed_row_ids` instead of adding repaired item IDs | `test_repair_dispatches_only_changed_stock_report_rows` failed: no item event was dispatched | yes |
| Plan 3 C4(a) | classified signature divergences as `repaired` instead of `not_repaired` | both signature repair tests failed: signatures must remain unchanged and be returned as unrepaired | yes |
| Plan 3 C1(l) | counted every non-null assignment state as an active counter contributor | `test_resolved_early_is_terminal_but_still_counts_toward_goal_total` failed with a terminal counter divergence | yes |
| Plan 3 C1(l) | filtered deleted credited assignments out of `recompute_goal_total` | `test_deleted_credited_assignment_still_counts_toward_goal_total` failed: the history total was undercounted | yes |
| Plan 3 C1(a–c) | removed the soft-delete predicate from active counter recomputation | `test_deleted_active_assignment_does_not_count_toward_row_counter` failed: deleted work leaked into `counter_in_queue` | yes |
| Plan 1 C2(b) | removed the `quantity_requested` non-negative CHECK from the ORM metadata | `test_stock_report_metadata_has_required_tables_and_task_server_default` failed: the named constraint disappeared | yes |
| Plan 1 C3 | removed the `stock_report_priority_enum` DROP from migration downgrade | `test_stock_report_migration_downgrade_removes_each_owned_enum_type` failed: the owned enum was left undeleted | yes |
| Plan 1 C3(a) | moved the four stock-report reset phases after task deletion | `test_reset_removes_stock_report_graph_before_task_deletion_and_keeps_other_workspace` failed on the FK-protected reset transaction | yes |
| Plan 3 C2(b) | returned divergences without the required `(kind, client_id, field)` sort | the strengthened `test_goal_signature_and_density_divergences_are_reported` failed on output order | yes |
| Plan 1 C6(a) | removed the `cancelled` entry from `ASSIGNMENT_STATE_BY_TASK_STATE` | `test_task_state_map_is_total` failed: the map no longer covered every `TaskStateEnum` member | yes |
| Plan 2 C7(c) | removed the duplicate-token rejection from `validate_wood_groups` | `test_scanner_table_validators_reject_ambiguous_definitions` failed to reject `Oak`/`oak` overlap | yes |
| Plan 2 C7(d) | removed the comma/slash separator rejection from `validate_wood_groups` | the same validator test failed to reject `A/B` group names | yes |
| Plan 2 C7(e) | removed drawer-range overlap/order validation | the validator test failed to reject overlapping ranges | yes |
| Plan 2 C5(i) | treated `accepted is None` as an empty accepted list | `test_wildcard_and_token_matching_table` failed: wildcard criteria became `value_not_accepted` | yes |
| Plan 2 C5(a) | removed the explicit empty-list criterion branch | `test_empty_list_is_not_a_wildcard` failed: the reason changed from `criterion_not_understood` | yes |
| Plan 2 C5(c) | removed the source-property check for missing derived groups | `test_known_source_without_derived_group_reports_no_group` failed: the reason regressed to `missing_on_item` | yes |
| Plan 2 C5(o) | inverted `matches_stock_criteria` to return `bool(failures)` | `test_scanner_hand_walk_golden_cases` failed across the composed H1–H16 verdicts | yes |
| Plan 2 C2(b) | removed key trimming while building the item bag | scanner bag table failed for spaced/duplicate keys (`" a"` leaked separately) | yes |
| Plan 2 C2(e) | reversed sorted property-key iteration before the later-wins assignment | scanner bag table failed: the duplicate normalized key retained `"first"` instead of `"second"` | yes |
| Plan 3 C3(i) | mapped `goal_total` repairs to `task` instead of `history_record` | `test_manual_repair_fixes_goal_total_and_writes_history_record` failed on the repair-record target kind | yes |
| Plan 3 C6(f) | removed lowercase boolean serialization from `_text` | `test_repair_record_values_are_contract_text` failed for `True`/`False` (`"True"`/`"False"`) | yes |
| Plan 3 lock boundary | removed the workspace predicate from `_lock` | `test_stock_report_row_lock_is_workspace_scoped` locked the foreign row as well | yes |
| Plan 3 C6(b) | replaced `Task.is_stock_assignment.is_distinct_from(value)` with equality | `test_manual_repair_fixes_counter_and_task_flag_and_records_each_change` failed to repair the divergent flag | yes |
| Plan 3 C6(c) | removed the injected `updated_at=ctx.now` stamp from counter repair | `test_counter_repair_stamps_only_the_changed_stock_report_row` failed on the changed row timestamp | yes |
| Plan 3 C6(c) | removed the injected `updated_by_id=ctx.user_id` stamp from counter repair | the same changed-row stamp test failed on the actor stamp | yes |
| Plan 1 C6(c) | mapped `assigned` to `in_progress` | `test_task_state_map_is_exact` failed for `assigned` | yes |
| Plan 1 C6(d) | mapped `working` to `awaiting` | `test_task_state_map_is_exact` failed for `working` | yes |
| Plan 1 C6(e) | mapped `stalled` to `awaiting` | `test_task_state_map_is_exact` failed for `stalled` | yes |
| Plan 1 C6(f) | mapped `ready` to `resolved_early` | exact-map and scanner-only-state tests failed | yes |
| Plan 1 C2(c) | removed the `quantity_in_progress` CHECK from `StockReportItem.__table_args__` | strengthened schema-contract test failed because `ck_stock_report_items_quantity_in_progress_nonneg` was absent | yes |
| Plan 1 C1(b) | removed `postgresql_where=text("is_deleted = false")` from the stock-report identity index | partial-index schema contract failed because the active predicate was absent | yes |
| Plan 1 C1(f) | removed `is_deleted = false AND` from the assignment partial-index predicate | assignment-index schema contract failed because deleted rows were no longer excluded | yes |
| Plan 2 C1(b) | serialized booleans with Python casing (`True`/`False`) | scanner property-bag table failed for both boolean vectors | yes |
| Plan 2 C1(h) | removed compact JSON separators in list/dict property serialization | scanner property-bag table failed for list and dict vectors | yes |
| Plan 2 C1(g) | serialized unsupported `None` values as text | scanner property-bag table failed because the `None` key was no longer absent | yes |
| Plan 2 C1(e) | removed `.removesuffix(".0")` from numeric property serialization | scanner property-bag table failed for the `4.0` vector | yes |
| Plan 2 C3(a) | removed the `properties or {}` null guard in item-bag construction | scanner property-bag table failed with `AttributeError` for `properties=None` | yes |
| Plan 2 C2(g) | stopped overriding stored `quantity` with the ORM item quantity | scanner property-bag table failed across the quantity override vectors | yes |
| Plan 1 C6(g) | mapped `resolved` to `failed` | `test_task_state_map_is_exact` failed for `resolved` | yes |
| Plan 1 C6(h) | mapped `failed` to `in_progress` | `test_task_state_map_is_exact` failed for `failed` | yes |
| Plan 1 C6(i) | mapped `cancelled` to `awaiting` | `test_task_state_map_is_exact` failed for `cancelled` | yes |
| Plan 1 C4(i–k) | wrapped scalar numeric/boolean values in string lists | normalization value-table tests failed for `1`, `1.0`, and `True` | yes |
| Plan 1 C4(l) | wrapped dictionary values as normalized lists | normalization value-table test failed for the raw dictionary vector | yes |
| Plan 1 C5(a) | lower-cased string-valued property keys during normalization | strengthened key-spelling test failed because distinct keys collapsed/changed | yes |
| Plan 1 C5(b) | stripped string-valued property keys during normalization | strengthened key-spelling test failed because the leading-space key changed | yes |
| Plan 3 C3(a–c) | replaced counter repair updates with a no-op | counter repair integration test failed because the stored counter remained divergent | yes |
| Plan 3 C3(f) | renumbered priority groups by `client_id` rather than current priority order | both priority repair tests failed on the expected moved row and net records | yes |
| Plan 2 C4(g) | shifted the first drawer range minimum from 1 to 2 | drawer table and range derivation tests failed for `1` | yes |
| Plan 2 C4(h) | shifted the middle drawer range minimum from 3 to 4 | drawer derivation test failed for `3` | yes |
| Plan 2 C4(j) | shifted the open-ended drawer range minimum from 6 to 7 | drawer derivation tests failed for `6` and stripped `" 6 "` | yes |
| Plan 2 C4(d) | removed case normalization from wood-group token lookup | H4/H4′/H5/H6/H7/H9/H10 hand-walk cases failed on mixed-case wood values | yes |
| Plan 2 C7(e) | removed the invalid-range (`maximum < minimum`) validator branch | strengthened scanner validator test failed for `("4-2", 4, 2)` | yes |
| Plan 2 C4(c) | defaulted an unknown wood token to the `light` group | H12 and no-derived-group tests failed because `Other` must remain ungrouped | yes |
| Plan 2 C4(k) | added a zero-valued drawer range | scanner table and drawer derivation tests failed because `0` must remain unmapped | yes |
| Plan 2 C4(l) | accepted non-ASCII/decimal drawer strings through `int(float(...))` | drawer table failed for `4.0` and Arabic-Indic `٤`, which must be rejected | yes |
| Plan 2 C2(d) | removed the non-empty-value guard while building the property bag | strengthened blank-value test failed because a blank property leaked into the bag | yes |
| Plan 1 C2(h) | removed `server_default=sa.false()` from `Task.is_stock_assignment` | schema metadata contract failed because the required server default was absent | yes |
| Plan 1 C2(a) | removed the `quantity_in_progress` CHECK from the generated migration | strengthened migration-contract test failed because the owned constraint was absent | yes |
| Plan 3 C1(e) | restricted `expected_task_flag` to tasks already flagged true | consistency test failed to report a false flag on a task with an assignment (and emitted a cartesian-query warning) | yes |
| Plan 1 C1(h) | removed `workspace_id` from the assignment identity index columns | partial-index schema contract failed because the index was no longer workspace-scoped | yes |
| Plan 1 C1(g) | removed `uix_stock_task_assignments_task_active` from the ORM table metadata | strengthened partial-index schema contract failed because the task uniqueness index was absent | yes |
| Plan 1 C1(i–j) | added `resolved_early` to both active assignment index predicates | strengthened index contract failed because the terminal state must remain reusable | yes |
| Plan 1 C1(d) | removed `awaiting` from both active assignment predicates | exact predicate contract failed because all three active states are required | yes |
| Plan 1 C1(a) | removed the stock-report identity index from ORM metadata | partial-index schema contract failed because the identity uniqueness index was absent | yes |
| Plan 3 C8(a–h) | widened both routes' `require_roles` list to include `WORKER` | negative router-role tests failed because workers must receive 403 and services must not be called | yes |
| Plan 3 C1(g–h) | inverted the priority/nullness divergence predicate | consistency suite failed across clean, null-priority, density, and raw-drift scenarios | yes |
| Plan 3 C1(f) | disabled the priority-density divergence branch | density consistency test failed to report the out-of-sequence row | yes |
| Plan 2 C5(h) | removed the empty-token-to-`missing_on_item` matcher branch | strengthened `", /"` criterion test failed because the reason regressed to `value_not_accepted` | yes |
| Plan 1 C5(c–d) | replaced sorted/deduplicated string-list normalization with a direct list conversion | normalization golden vector and signature tests failed, proving idempotence/order rules | yes |
| Plan 1 C4(c–d) | converted blank scalar strings to `[]` | normalization value-table tests failed because blank strings are preserved as not-understood values | yes |
| Plan 2 C7(a) | removed `Walnut` from the literal Dark wood-group table | scanner table golden assertion failed | yes |
| Plan 2 C7(b) | changed the literal `6+` drawer label to `6plus` | scanner table and drawer derivation assertions failed | yes |
| Plan 2 C1(i) | changed property-bag JSON serialization to `ensure_ascii=True` | scanner property-bag Unicode vector failed because `é` must remain unescaped | yes |
| Plan 3 C5(a)/C6(e) | removed the `changed_row_ids` guard before event dispatch | strengthened clean-repair event test failed because a no-op repair invoked dispatch | yes |
| Plan 3 C3(d) | used Python truthiness instead of explicit `expected == "true"` for task-flag repair | new false-positive task-flag repair test failed to clear the flag | yes |
| Plan 2 C5(a) | removed the explicit `continue` after an empty accepted-list failure | strengthened matcher test failed because an extra `value_not_accepted` failure leaked through | yes |
| Plan 2 C5(d) | removed the wildcard (`accepted is None`) terminal branch | wildcard and H11 matcher tests failed with a `NoneType` token comparison | yes |
| Plan 2 C5(c) | replaced source-derived `NO_GROUP_FOR_VALUE` classification with `MISSING_ON_ITEM` | known-source/no-group and H12/H14 matcher cases failed | yes |
| Plan 2 C4(b) | selected the last wood token instead of the first | H3/H7 hand-walk cases failed on multi-token wood values | yes |
| Plan 2 C1(b) | removed comma from the Scanner tokenizer delimiter set | wildcard and H2/H3/H7 hand-walk cases failed on comma-separated values | yes |
| Plan 2 C2(b) | removed value trimming while building the property bag | scanner property-bag table failed for the spaced Teak vector | yes |
| Plan 2 C2(a) | removed key trimming while building the property bag | scanner property-bag table failed for spaced/duplicate keys | yes |
| Plan 3 C1(b) | mapped `in_progress` recomputation into the queue counter | parametrized active-counter test failed for `counter_in_progress` | yes |
| Plan 3 C1(c) | mapped `awaiting` recomputation into the queue counter | parametrized active-counter test failed for `counter_awaiting` | yes |
| Plan 3 C4(a) | included signature divergences in the post-repair unexpected-remnant check | signature repair tests failed because intentional unrepaired signatures raised | yes |
| Plan 1 C2(e) | removed the `quantity_awaiting` ORM CHECK | schema-contract test failed because the owned counter constraint was absent | yes |
| Plan 1 C2(c) | removed the `quantity_in_queue` ORM CHECK | schema-contract test failed because the owned counter constraint was absent | yes |
| Plan 1 C2(b) | removed the `quantity_requested` ORM CHECK | schema-contract test failed because the owned counter constraint was absent | yes |
| Plan 1 C2(f) | removed the assignment positive-quantity ORM CHECK | schema-contract test failed because `ck_stock_task_assignments_quantity_positive` was absent | yes |
| Plan 1 C2(g) | removed the history awaiting non-negative ORM CHECK | schema-contract test failed because `ck_stock_report_history_records_quantity_awaiting_nonneg` was absent | yes |
| Plan 2 C2(h) | removed `wood_group` from the excluded derived-key set | direct stored-derived-key test failed because stale `wood_group` leaked into the bag | yes |
| Plan 2 C2(i) | removed `drawers_range` from the excluded derived-key set | direct stored-derived-key test failed because stale `drawers_range` leaked into the bag | yes |
| Plan 1 C1(h) | removed `workspace_id` from the stock-report item identity index columns | partial-index schema contract failed because identity uniqueness was no longer workspace-scoped | yes |
| Plan 1 C1(c/g) | changed the task-active assignment index identity column from `task_id` to `item_id` | exact assignment-index column contract failed | yes |
| Plan 1 C1(c) | changed the item-active assignment index identity column from `item_id` to `task_id` | exact assignment-index column contract failed | yes |
| Plan 1 C1(c) | removed `uix_stock_task_assignments_item_active` from ORM metadata | assignment-index schema contract failed because item-level active uniqueness was absent | yes |
| Plan 1 C3 | removed the `stock_report_priority_enum` DROP from migration downgrade | enum-downgrade contract failed because an owned enum remained | yes |
| Plan 1 C3 | removed the `stock_report_history_record_type_enum` DROP from migration downgrade | enum-downgrade contract failed because an owned enum remained | yes |
| Plan 1 C3 | removed the `stock_report_repair_target_kind_enum` DROP from migration downgrade | enum-downgrade contract failed because an owned enum remained | yes |
| Plan 1 C6(a) | removed the `cancelled` key from `ASSIGNMENT_STATE_BY_TASK_STATE` | totality test failed because a `TaskStateEnum` member had no mapping | yes |
| Plan 3 C2(a) | added a no-op UPDATE to consistency recomputation | strengthened read-only consistency test failed because a write was emitted | yes |

The plan files contain shared mutation sites and non-isolatable boundary rows, so the ledger is
site-oriented rather than one row per criterion. All declared isolatable sites have now been run at
their named sites and recorded with observed red results; the current probe arithmetic is
`executed=123`. A mechanical text scan finds 39/37/22 distinct mutation descriptions in Plans 1/2/3;
the handoff ledger is the authoritative evidence for this implementation session. Promotion remains
pending the reviewer-owned graph delta and checkpoint gates.

## Criterion coverage map (functional perimeter)

This map records where the implemented criterion families are exercised. It is intentionally
separate from the named-mutation ledger above: a green functional test does not prove that every
declared mutation site has been independently killed.

| Plan | Criterion families | Evidence |
|---|---|---|
| Plan 1 | C1–C2 schema/index/check/default contracts | `tests/integration/models/stock_report/test_stock_report_schema.py`, `tests/unit/domain/stock_report/test_schema_contract.py` |
| Plan 1 | C3 reset ordering and workspace isolation | `tests/integration/services/commands/reset/test_stock_report_reset.py` |
| Plan 1 | C4–C5 normalization/signature vectors | `tests/unit/domain/stock_report/test_criteria_normalization.py` |
| Plan 1 | C6–C7 task-state map and active/terminal partition | `tests/unit/domain/stock_report/test_state_map.py`, `test_assignment_state_enum.py` |
| Plan 1 | settings and shared helper behavior | `tests/unit/domain/stock_report/test_settings.py`, `tests/integration/helpers/test_stock_report_helper.py` |
| Plan 2 | C1–C5 bag derivation, scanner tables, matcher failure vocabulary | `tests/unit/domain/stock_report/test_scanner_property_tables.py`, `test_criteria_matcher.py` |
| Plan 2 | C6 H1–H16 composed hand-walk | `tests/unit/domain/stock_report/test_criteria_matcher.py::test_scanner_hand_walk_golden_cases` |
| Plan 3 | C1–C2 consistency recomputation and read-only envelope | `tests/integration/services/queries/stock_report/test_consistency_check.py` |
| Plan 3 | C3–C7 repair ordering, records, stamps, events, no-op behavior | `tests/integration/services/commands/stock_report/test_repair_stock_report.py` |
| Plan 3 | C8 role cells and service reachability | `tests/unit/routers/api_v1/test_stock_report_router.py` |

The functional map is complete for the current Batch-A perimeter (`139 passed`); implementation
evidence is complete, while reviewer-owned graph/checkpoint gates remain before promotion.

## Graph

Orientation completed: valid graph, revision
`fa1c510e54e61b3faca9c93e2998bf21fddad1ed154e97d870853254f9f58a13`, 211 nodes / 327 edges;
`stock report` had no matching node. A fresh status check confirms the same revision and no
diagnostics; the server is in `permissionMode: review`, so additive graph-write is unavailable in
this session. No graph write was made because the reviewer/orchestrator owns that gate and the
current permission mode does not permit it. Implementation evidence is complete; graph/checkpoint
promotion remains pending review.

## ⚠ OWNER DECISIONS REQUIRED (0)
