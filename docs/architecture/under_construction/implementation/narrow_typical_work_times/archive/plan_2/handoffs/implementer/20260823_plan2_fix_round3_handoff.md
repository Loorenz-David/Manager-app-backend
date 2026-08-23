---
plan: plan_2
role: implementer
round: 3
date: 2026-08-23
actor: Codex (GPT-5)
state: IMPLEMENTED
---

# Plan 2 fix-round-3 handoff

This round changed no production code. It armed the three review guards that could not
fail, completed the named fixture/document follow-ups, and checkpointed the five intended
phase files at `8718092` (`CHECKPOINT (not approved): plan 2 fix round 3 evidence`). The
checkpoint is an ancestor of the current `HEAD`; a separate authorized Architecture Graph
maintenance session subsequently committed `88092c6`, outside this round's perimeter.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. The graph queue remains owned by the separate maintenance session; this implementer
session did not adjudicate, promote, reject, edit, or remove any graph review item.

## Prompt-item disposition

| item | disposition |
|---|---|
| S1 — C5 population definition | Fixed. C5 now seeds one marked-wrong, one deleted, one non-`COMPLETED`, and one outside-window step. It retains literal `20` / `76` assertions, adds `section_sample_count == base.sample_count`, and is now the first criterion explicitly asserting agreement between the duplicated no-spec and K≥1 population builders. |
| S2 — narrowed typical value at index ≥1 | Fixed. Added one K=2 row with five groups per index and distinct literal medians `30` and `80`; both narrowed values and counts are asserted. |
| S3 — explicit enum rejection | Fixed. The bare-string row pins `must be a sequence of values`; the valid and malformed enum fixtures derive the `WOOD` value so the one-character-member scenario reaches the intended guard. |
| S4 — column order | No code or C2 change. The shipped tuple was confirmed against §4A K2-a: names and set are contractual, order is not, and consumers read by name. |
| S5 — measurement prose | Fixed. Added one paragraph disclosing cumulative seeding and positions 1–11, no `ANALYZE`, default-estimate `cost` semantics, requested-but-unrecorded `BUFFERS`, and the undecidable 1.9× explanation. No re-measurement was performed. |
| N4 — C10 row (c) | Fixed. The width fixture now includes a NULL-width task of its own. |
| C8 decorative median | Deleted the inert equal-`100` median assertion. The count assertion remains because outer attachment moves it from 6 to 17 under fan-out. |
| Not in scope | No production changes, no plan-3 one-active-primary rows, and no graph queue adjudication. |

## Verification

- C0 unit baseline: `BEYO_TEST_SLOT=r3c0b PYTHONPATH=. pytest --tb=no tests/unit/domain/item_economics/test_typical_filters.py` → **43 passed**.
- Narrowing-file baseline: `BEYO_TEST_SLOT=r3int PYTHONPATH=. pytest tests/integration/services/queries/working_sections/test_typical_times_narrowing.py` → **24 passed, 1 skipped**.
- L2 contract baseline after the new tests: `BEYO_TEST_SLOT=r3l2base PYTHONPATH=. pytest tests/unit/services/queries/working_sections/ tests/integration/services/queries/working_sections/` → **63 passed, 1 skipped**. The reviewer's tree-bound comparator was **62 passed, 1 skipped**.
- Docs guard: `PYTHONPATH=. pytest tests/unit/docs/` → **59 passed**.
- Redis pre-check: `redis-cli ping` → **PONG**.

## Mutation ledger

All probes were applied and reverted. The final production checksum/diff is clean; the
probe files were not part of the checkpoint. Mutation-side commands used the documented
L2 directories from `backend/app/` and the whole C0 unit file at L1.

| hypothesis / mutation site | contract side | mutation side | failing test ID(s) |
|---|---|---|---|
| S1a / K≥1 `TaskStep.recorded_time_marked_wrong.is_(False)` deleted in `typical_times_statement` | L2: 63 passed / 1 skipped | 62 passed / 1 skipped | `tests/integration/services/queries/working_sections/test_typical_times_narrowing.py::test_spec_index_preserves_input_order_and_section_population_is_constant` |
| S1b / K≥1 `TaskStep.state == COMPLETED` deleted in `typical_times_statement` | L2: 63 passed / 1 skipped | 62 passed / 1 skipped | `tests/integration/services/queries/working_sections/test_typical_times_narrowing.py::test_spec_index_preserves_input_order_and_section_population_is_constant` |
| S1c / K≥1 `TaskStep.is_deleted.is_(False)` deleted in `typical_times_statement` | L2: 63 passed / 1 skipped | 62 passed / 1 skipped | `tests/integration/services/queries/working_sections/test_typical_times_narrowing.py::test_spec_index_preserves_input_order_and_section_population_is_constant` |
| S1d / K≥1 `latest_closed_at >= cutoff` replaced with `true()` in `typical_times_statement` | L2: 63 passed / 1 skipped | 62 passed / 1 skipped | `tests/integration/services/queries/working_sections/test_typical_times_narrowing.py::test_spec_index_preserves_input_order_and_section_population_is_constant` |
| S2 / typical coalesce `index == position` changed to `index == 0` in `typical_times_statement` | L2: 63 passed / 1 skipped | 62 passed / 1 skipped | `tests/integration/services/queries/working_sections/test_typical_times_narrowing.py::test_each_spec_index_selects_its_own_narrowed_typical` |
| S3a / remove `str` from `_optional_categories`'s guard | L1: 43 passed | 42 passed / 1 failed | `tests/unit/domain/item_economics/test_typical_filters.py::test_parser_rejects_mapping_and_byte_iterable_repeatable_values[params4-major_categories]` |
| S3b / shorten `ItemMajorCategoryEnum.WOOD` to one character with the enum-family string guard removed | L1: 43 passed | 42 passed / 1 failed | `tests/unit/domain/item_economics/test_typical_filters.py::test_parser_rejects_mapping_and_byte_iterable_repeatable_values[params4-major_categories]` |

The S1 result is the requested cross-branch agreement proof: every deleted K≥1 population
filter moves a seeded row and reddens C5. S2's value-column failure is independent of the
already-existing count-column coverage. The initial diagnostic one-character-only probe
also exposed a hard-coded valid-list fixture; deriving both enum fixtures from the member
value closed that unrelated path before the named combined probe was run.

## L4 full-suite stamp

Authoritative command: `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'` from
`backend/app/`, after `redis-cli ping` returned `PONG`. Result: **21 failed, 2661 passed,
1 skipped, 2 warnings in 55.94s**.

Against the approved 21-ID baseline: **added ∅; removed ∅**. No phase-2 test ID entered
the failing set. The 21 failures remain outside this phase's perimeter; the count is one
higher than round 2 because this round added a test, while the failure-ID set is unchanged.

## Full write perimeter

Intended files changed and checkpointed by this session:

- `app/tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`
- `app/tests/unit/domain/item_economics/test_typical_filters.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/planning/query_cost_measurements.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_2.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- this handoff

Mutation-probe files, applied and reverted with no production diff:

- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
- `app/beyo_manager/domain/item_economics/typical_filters.py`
- `app/beyo_manager/domain/items/enums.py`

Architecture Graph: **no delta from this implementation session**. The graph is the
separate authorized maintenance perimeter. During this session an external maintenance
commit `88092c6` changed `.archgraph/architecture.yml`, created its review record, and
updated the maintenance handoff; those artifacts were not staged or included in checkpoint
`8718092`. The expected generated `.archgraph/contexts/` directory remains untracked.

At handoff creation, `git status --short` showed the separate maintenance handoff modified
and `.archgraph/contexts/` untracked; no phase file or production file was dirty. The
checkpoint SHA is `8718092` and must be treated as the round's code/content baseline, not as
a pin for `HEAD`.
