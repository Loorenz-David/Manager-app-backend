---
plan: batch A (1, 2, 3)
role: implement
round: batch_A-fix-1
state: IMPLEMENTED_WITH_MUTATION_GAPS
date: 2026-09-20
actor: Codex
tree: b4770d882b41aafc08dec995ebe4d009bd9260a1 + working-diff 7cb5cc8e00eec5abc6eb3b169a03aa10c4930d515e43e3f4bc54fdd81a74425f
---

# Batch A fix 1 implementer handoff

## 1. Gate check record

All four gates passed before edits: ratified intention, `FIX_PROMPT_READY` batch-A plan state,
clean starting worktree, and tracker-commit ancestry (`0d5d31d` ancestor). Architecture Graph was
read-only inspected; no graph write was made. The baseline was 21 failures / 3242 passed / 1
skipped before edits.

## 2. Finding-by-finding disposition

| finding | disposition | discharge / mutation evidence |
|---|---|---|
| F-B1 | Repaired NULL priority with non-NULL order first; writes `priority_order=NULL`, one item record, then densifies. | `test_manual_repair_clears_priority_nullness_and_records_one_item_change`; disabling the NULLness branch reddened that test. |
| F-B2 | Filters blank list members; version remains `1`; golden vectors updated. | `test_normalization_value_table[raw5-expected5]`, `test_signature_uses_normalized_golden_vectors[raw1-expected1]` reddened under filter removal. |
| F-S1 | Scanner wood groups retain declared `Dark`/`Teak`/`Light` casing. | scanner-table and matcher tests; lower-casing mutant reddened `test_build_item_property_bag_scanner_table[properties9-4-expected9]` and `[properties13-4-expected13]`. |
| F-S2 | Null-order expected value is `max(group)+1`. | `test_null_priority_order_reports_after_sparse_group_maximum`; `len+1` mutant asserted `3` instead of `8`. |
| F-S3 | Added multi-value any-of and symmetric miss matcher coverage. | `test_matcher_accepts_any_of_multiple_criterion_values_and_rejects_a_miss`; require-all mutant reddened it. |
| F-S4 | Added one-outcome-per-index fixtures for item/task active uniqueness, terminal states, soft deletion, and workspace identity. | Schema integration tests assert named index behavior; individual migration mutants were not rerun in this session. |
| F-S5 | Replaced migration-source grep with live `compare_metadata` over the five required tables. | `test_live_stock_report_metadata_matches_migrated_database`; mutation not independently rerun. |
| F-S6 | Added and used `lock_stock_report_history_records` after task, item, and assignment locks. | repair goal-total tests; lock-helper mutation not independently rerun. |
| F-S7 | Repair-path rowcount guards now require exactly one row; ordinary task-flag idempotent zero remains allowed. | counter/goal/priority repair tests; guard mutants not independently rerun. |
| F-S8 | Restored registered helper signatures, `Divergence` TypedDict, and operation-time `now`. | registry callers and exact record tests; signature mutants not independently rerun. |
| F-S9 | Added distinct-key signatures, six golden vectors, and all-payload idempotence. | normalization unit file passes; key/golden mutants covered by the named tests. |
| F-S10 | Reset test asserts own workspace deletion, foreign-row counts, and captured dispatch; foreign graph is purged in `finally`. | reset integration test; mutation not independently rerun. |
| F-S11 | Repair assertions now check target kind, field, values, trigger, actor, timestamps, and changed-row scope. | exact repair-record tests; target-kind mutation not independently rerun. |
| F-S12 | C2(a) snapshots every row in the four MC-9 tables plus repair records (and task rows used by the check). | consistency no-write snapshot test; mutation not independently rerun. |
| F-S13 | Added H9 Oval, blank-key, derived wildcard, missing-drawer-source, and `item(None)` cases; complete WOOD_GROUPS literal assertion. | focused unit/integration tests; complete table mutant reddened `test_scanner_tables_and_drawer_ascii_rules`. |
| F-S14 | Routed orphan checks in plan logs; retained purge-helper coverage; deleted orphan settings checks and the sole test-package `__init__.py`. | full L4 no longer has duplicate-module collection error. |
| N-4 | Reset docstring now lists the four stock-report phases and renumbered steps. | reset source inspection. |
| N-5 | Deleted `app/tests/unit/domain/stock_report/__init__.py`. | full L4 collection passes. |

The plan defects were handled as instructed: H9's second case was added, and C5(a)'s
`count_writes == 0` interpretation was retained.

## 3. Row table

Rows armed in this fix round are listed below. “Not independently mutated” means the strengthened
outcome test is present and passed in L2, but its source-level mutant was not run in this session.

| plan rows | evidence |
|---|---|
| P1 C1(c), C1(d), C1(e), C1(f), C1(g), C1(h), C1(i), C1(j) | schema tests; named index fixtures; not independently mutated |
| P1 C2(a) | live `compare_metadata`; not independently mutated |
| P1 C3(a) | reset test, workspace deletion + foreign cleanup; not independently mutated |
| P1 C5(a), C5(b), C5(c), C5(d) | normalization signatures, idempotence, six vectors; B2 and golden-vector mutants run |
| P2 C2(c), C2(h), C3(d), C4(a), C4(b), C4(d), C5(d), C5(e), C5(n), C6(j), C7(a) | matcher/scanner unit tests; C3(d), casing, and full-table mutants run |
| P3 C1(a), C1(d), C1(e), C1(f), C1(g), C1(h), C1(i), C1(j), C1(k), C2(a) | exact divergence dictionaries, sparse max case, foreign isolation, no-write snapshot; not independently mutated |
| P3 C3(a), C3(b), C3(c), C3(d), C3(f), C3(g), C3(h), C6(d), C6(e), C7(a) | exact repair records, stamps, event perimeter, NULLness repair, stray-record assertion; NULLness and stray-record mutants run |

## 4. Registry table

| registered interface | implementation now used |
|---|---|
| `recompute_row_counters(session, stock_report_item_id) -> dict[str, int]` | exact per-item helper; workspace scan uses private `_recompute_row_counters_for_workspace` |
| `recompute_goal_total(session, history_record_id) -> int` | exact per-history helper; workspace scan uses private `_recompute_goal_totals_for_workspace` |
| `expected_task_flag(session, task_id) -> bool` | exact task-scoped helper |
| `recompute_task_stock_flag(session, task_id) -> bool` | exact task-scoped helper, returns expected value |
| `write_repair_record(..., stored_value, recomputed_value, ..., now)` | accepts registered names and sets `created_at=now`; no delta argument |
| `Divergence` | `TypedDict` with `kind`, `client_id`, `field`, `stored`, `expected` |
| `lock_stock_report_history_records(session, workspace_id, client_ids)` | new history-record lock helper, ascending IDs through shared `_lock` |

## 5. Mutation ledger

Observed red sites (applied, tested, reverted):

- P1 F-B2 mixed blank list: `test_normalization_value_table[raw5-expected5]` and
  `test_signature_uses_normalized_golden_vectors[raw1-expected1]`.
- P1 C5(g): `test_signature_separates_ununderstood_values_but_sorts_object_keys`.
- P1 C7(a): `test_assignment_state_partition_includes_resolved_early_as_terminal`.
- P2 C3(d): `test_matcher_accepts_any_of_multiple_criterion_values_and_rejects_a_miss`.
- P2 F-S1/C7(a): `test_build_item_property_bag_scanner_table[...]` and
  `test_scanner_tables_and_drawer_ascii_rules`.
- P3 F-S2: `test_null_priority_order_reports_after_sparse_group_maximum`.
- P3 C3(h)/F-B1: `test_manual_repair_clears_priority_nullness_and_records_one_item_change`.
- P3 C7(a): `test_assert_stock_report_clean_rejects_a_stray_repair_record`.

The remaining declared sites in the prompt’s 35/37/22 inventory were not independently mutated;
they are explicitly not represented as executed: P1 C1(a), C1(b), C2(b), C2(c), C2(e), C2(h),
C4(a–n), C5(a–f), C5(h), C6(a–j), C7(b); P2 C1(a–i), C2(a–i), C3(a–c), C4(a–p), C5(a–o),
C7(b–e); P3 C1(a–l), C2(a–c), C3(a–i), C4(a), C5(a), C6(a–f), C7(b), except for the
specific sites named above. Reason: the focused outcome suites were completed, but a full 94-site
source mutation matrix was not completed within this implementer session. No claim of
`executed == declared` is made.

## 6. L2 and L4 stamps

Both stamps below ran against tree identity `HEAD b4770d882b41aafc08dec995ebe4d009bd9260a1` plus
working-diff digest `7cb5cc8e00eec5abc6eb3b169a03aa10c4930d515e43e3f4bc54fdd81a74425f`.

- L2: `PYTHONPATH=. pytest tests/unit/domain/stock_report tests/integration/models/stock_report/test_stock_report_schema.py tests/integration/services/queries/stock_report tests/integration/services/commands/stock_report tests/integration/services/commands/reset tests/integration/helpers/test_stock_report_helper.py -q` — **155 passed in 4.04s**.
- L4: `PYTHONPATH=. pytest -m 'not e2e' --tb=no -q` — **21 failed, 3266 passed, 1 skipped, 2 warnings in 66.16s**.
- L4 failure set equals the archived 21-ID baseline in both directions (`comm(current, baseline)=∅` and `comm(baseline, current)=∅`); no new or missing failure ID.

The earlier diagnostic L4 before deleting the orphan settings file also reproduced the same 21 IDs
but exposed one collection error; the authoritative final L4 above is the corrected-tree run.

## 7. Write perimeter

The fix-round mutation perimeter is the 20 paths shown by `git diff --name-status` after reverting all
probes: eight production files, eight test files including two deletions, and three plan review logs.
The handoff itself is the additional deliverable path. No intention, master plan, Scanner file,
other-role handoff/prompt, tracker row, architecture observation file, or Architecture Graph file
was changed. The baseline `git diff --stat 0d5d31d..` also contains the orchestrator's pre-existing
docs commit; those files are outside this fix-round perimeter.

## 8. Commits

No fix-round checkpoint commit has been created yet; the required scoped checkpoint commit is the
next closing action.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required. Mutation coverage is reported as incomplete rather than silently
promoted to complete.
