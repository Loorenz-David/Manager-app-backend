---
plan: plan_4
role: implementer
round: fix-round-2-correction-2
state: IMPLEMENTED
date: 2026-08-24
actor: Codex
checkpoint_base: e7b2c41
---

# Plan 4 — fix round 2 correction 2 implementer handoff

## Result

The C10(d) production defect is fixed in
`app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`.
For a mixed-spec batch (`K >= 1`), a category-less task has `spec_index is None` and now
uses the section-wide row at index `0` for its section evidence. The section-wide columns
are spec-independent. The `K == 0` path is unchanged, and the narrowed branch is unchanged.

No fixture workaround remains and no other production file was changed in correction2.

## Scope and checkpoint

The correction2 prompt lifted the round-2 production fence for this one existing perimeter
file only. The prior four-file work-in-progress was checkpointed before this correction as:

`e7b2c41 CHECKPOINT (not approved): continue plan 4 fix round 2`

The current app write perimeter is exact: the only app file changed after that checkpoint is
`app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`. Temporary
mutation edits were reverted. Owner-owned `.archgraph/` changes remain outside the app scope
and were not touched.

## Acceptance evidence

### C10(d) red → green

Before the production edit, the dedicated test failed:

`tests/integration/services/queries/item_economics/test_narrowed_task_economics.py::test_c10_batch_dedupes_specs_once_and_preserves_category_index`

The category-less rows reported `insufficient_sample` in the mixed-spec batch. After the
fallback fix, the same test passed (`1 passed`). The whole phase integration file passed:

`11 passed in 1.22s`

The focused L2 command passed:

`PYTHONPATH=. python3 -m pytest -n 0 tests/integration/services/queries/item_economics tests/unit/domain/item_economics tests/unit/services/queries/item_economics tests/unit/docs -q`

Result: `422 passed in 9.08s`.

### B1 snapshot bite

The committed no-category snapshot was temporarily moved out of the test directory and the
phase integration file was run. The immutable-baseline assertion failed at
`test_c9_no_category_snapshot_and_empty_spec_converge` with `1 failed, 10 passed in 1.24s`.
The snapshot was restored immediately. The test does not recreate it and is not
self-healing.

### B4 baseline sentence

The original task-0 red baseline was not recorded before the prior fix round. This is stated
explicitly rather than reconstructed after the fact. The correction2 C10(d) red is recorded
above with its exact test ID and count.

### S1 and L4

The one permitted L4 run was executed from the app test root with the non-e2e suite. Its
pytest log recorded:

`21 failed, 2687 passed, 1 skipped, 2 warnings in 49.57s`

The exact 21 `FAILED` IDs were sorted and compared programmatically with the published
21-ID block in `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md`:

`actual − published: ∅`

`published − actual: ∅`

The pytest process completed. The shell wrapper then attempted to assign zsh's read-only
`status` variable and printed `zsh:1: read-only variable: status`; no second L4 run was
taken, and the pytest result above is the authoritative result.

### S2

The exact `allocation_method == "uniform_basis_v2"` assertion is present on every
budget-allocation task entry, alongside the production-time task assertion.

## Mutation ledger — 22 observed rows

The first 16 rows are the standing evidence from the prior implementer checkpoint
(`0efbbd4`), whose mutation sites and tests were unchanged by correction2. The final six
rows were executed during correction2. Every temporary mutation was reverted before the
handoff was written.

| # | Criterion / mutation | Observed red test |
|---:|---|---|
| 1 | C0: make the domain walk use only a glob and omit the recursive subpackage/leak path | `test_item_economics_domain_walk_is_recursive` |
| 2 | C0: strip all text and remove the second fingerprint check | `test_item_economics_domain_has_no_spec_identity_hashing` |
| 3 | C0: remove the non-empty package assertion | `test_item_economics_domain_walk_requires_a_nonempty_package` |
| 4 | C1: replace the production live-value clock with a fixed value | `test_c1_both_consumers_keep_settled_typicals_when_live_clock_moves` |
| 5 | C1: replace the allocations live-value clock with a fixed value | `test_c1_both_consumers_keep_settled_typicals_when_live_clock_moves` |
| 6 | C2: mutate the definition to publish the v1 method | `test_prechange_payloads_match_byte_golden_files` |
| 7 | C3: make `_step_result` lookup strict | `test_c3_missing_selection_is_an_honest_terminal_and_not_a_key_error` |
| 8 | C4: publish terminal zero instead of equal business allocation | `test_c4_no_usable_typicals_use_equal_business_allocation_without_publishing_terminal` (ZeroDivisionError) |
| 9 | C5: publish null for the no-usable-typicals result | `test_c4_no_usable_typicals_use_equal_business_allocation_without_publishing_terminal` |
| 10 | C5: publish zero for the no-usable-typicals result | `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections` |
| 11 | C6: count all selected rows instead of participating rows | `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections` |
| 12 | C7: include excluded sections in the quantifier | `test_c7_excluded_sections_resolve_independently_in_both_directions` |
| 13 | C7: resolve excluded sections from the answer-as-asked branch | `test_c7_excluded_sections_resolve_independently_in_both_directions` |
| 14 | C9: provide a non-empty no-category spec where the empty-spec path is required | `test_c9_no_category_snapshot_and_empty_spec_converge` |
| 15 | C12: default the production section to section-wide | `test_c12_defaults_are_always_present_on_the_production_section` |
| 16 | C13: omit the `FAILED` status from the serializer | `test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` and `test_c8_c9_excluded_and_mixed_sections_keep_task_charge` |
| 17 | C0 standing regression: add `import hashlib` to the domain filters | `test_item_economics_domain_has_no_spec_identity_hashing` |
| 18 | C0 standing regression: import a SQLAlchemy item model into the domain filters | `test_item_economics_domain_has_no_sqlalchemy_or_model_table_imports` |
| 19 | C9(ii): classify all section evidence as narrowed without usable narrowed evidence | `test_c9_no_category_snapshot_and_empty_spec_converge` |
| 20 | C10(i): dedupe specs by object identity instead of equality | `test_c10_batch_dedupes_specs_once_and_preserves_category_index` |
| 21 | C10(ii): shift the post-dedupe spec indices in range | `test_c10_batch_dedupes_specs_once_and_preserves_category_index` |
| 22 | C10(d) anti-regression: change the corrected fallback from `(section_id, 0)` back to `(section_id, None)` | `test_c10_batch_dedupes_specs_once_and_preserves_category_index` |

Rows 17–22 were run as temporary source mutations and restored immediately. The correction2
production line is therefore represented by row 22's anti-regression, not by claiming that
the implemented passing line is itself red evidence.

## Files changed in this correction

- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_4.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- this handoff

## Owner decisions required

None.

## Architecture graph

No graph delta is required. The correction repairs an existing lookup branch inside an
already-mapped service and does not add or remove an architectural component or boundary.
