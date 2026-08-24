---
plan: plan_5
role: fix
state: IMPLEMENTED
date: 2026-08-24
actor: Codex
---

# Plan 5 fix round 5 handoff

## Summary

Completed both requested test-only corrections. `_narrowing_fixture.py` now exports
`DIVERGENT_BOUNDARY_CLOSED_AT`, and the existing divergent seed uses that constant. C1(b)
derives its frozen clock from that boundary plus `TYPICAL_WINDOW_DAYS`. C1(d) directly executes
the spec-branch statement and asserts narrowed sample counts of `5` at `FROZEN` and `0` at
`FROZEN + timedelta(seconds=1)`. No production file changed. This was the last fix round.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

## Gate and baseline

- Opening `git status --porcelain -- app/`: empty.
- `plans/plan_5.md` header: `CHANGES_REQUESTED`.
- Master tracker row 5: `CHANGES_REQUESTED`.
- `planning/intention.md` header: `RATIFIED`.
- `redis-cli ping`: `PONG`.
- Opening typed-clock check found `datetime(2026, 10, 30, ...)` in the test; the edit removed it.
- Pre-edit targeted baseline: **71 passed** across `test_narrowed_price_scenario.py`,
  `test_price_scenario_query.py`, and `test_budget_allocations_query.py`.

## Task 0 coverage map

| criterion row | discharging test | assertion shape |
|---|---|---|
| C1(a) | `test_c1a_typical_block_passes_the_request_clock_to_the_statement` | delegated `now=ctx.now` and `specs=()` exact |
| C1(b) | `test_c1b_same_frozen_context_produces_byte_identical_typicals` | JSON byte identity first; exact `375` total second; clock derived |
| C1(c) | `test_c1c_working_section_typicals_keep_the_default_statement_clock` | delegated spy invoked and exact absence of `now` |
| C1(d) | `test_c1d_spec_branch_uses_the_injected_clock_at_the_statement_level` | real statement; exact narrowed counts `5` inside / `0` outside |
| C2(a) | `test_c2_is_estimated_tracks_empty_none_and_zero_selected_typicals` | exact `true`, total `0`, totals `0` |
| C2(b) | same parametrized test | exact `true` and `sections_without_sample == 1` |
| C2(c) | same parametrized test | exact `true` and `sections_without_sample == 1` |
| C2(d) | `test_c2d_section_wide_uniform_does_not_make_is_estimated_true` | exact `false`, count `0` |
| C3(i/ii) | `test_c3_counts_only_participating_selected_typicals` | exact counts `3` and `2` |
| C4(a/b) | `test_c4_price_terminal_and_median_are_duration_values` | exact `0` and `2250` totals, with estimated state |
| C5(a/b/c) | `test_c5_three_surfaces_use_the_same_published_literal` | exact shared production-time, price, and allocation values |
| C6(a/b/c) | `test_c6_price_and_production_resolution_have_the_exact_six_key_shape` | exact six-key sets and literal basis/filter/count values |
| C7(a/b) | `test_c7_typical_block_delegates_statistics_and_has_no_private_terms`; `test_c7_item_economics_fork_sweep_finds_only_the_shared_median` | exact delegation and scoped fork sweep |
| C8(a/b/c) | `test_c8_divergent_fixture_measures_narrowed_600_against_section_375` | real divergent fixture, exact `600` vs `375`, end-to-end service edge |

Reverse map: the remaining tests in the phase-5 test files retain the fix-round-4 mappings;
the new C1(d) test is the only added test and maps above. No orphan tests were added.

## Mutation ledger

Summands: `C1 3 · C2 3 · C3 2 · C4 2 · C5 2 · C6 1 · C7 1 · C8 2` = **16 named mutations**;
`C7(c) 1 + C7(d) 1` planted-defect probes = **2**; **18 total rows**.

| row | site and evidence | observed result |
|---|---|---|
| C1(i) | `get_task_price_scenario.py`, `_typical_block` call site: remove `now=ctx.now`; L1 C1(a)+C1(b) | C1(a) `KeyError: 'now'`; C1(b) failed at the **byte-identity assertion** (line 131), before the numeric assertion, with differing serialized JSON |
| C1(ii) | `get_working_section_typical_times.py`, call site: add `now=ctx.now` | cited from fix round 4: C1(c) exact no-`now` assertion reddened |
| C1(iii) | `get_working_section_typical_times.py:40`, cutoff definition: ignore injected `now` | **C1(d) alone** reddened: outside narrowed sample was `5`, not exact `0` |
| C2(i) | `_typical_block` definition: remove `sections_total == 0` disjunct | cited: C2(a) exact tuple red, `is_estimated` changed `true` → `false` |
| C2(ii) | `_typical_block` definition: use narrowed-thin evidence for the flag | cited: C2(d) exact boolean red, `true is False` |
| C2(iii) | `_typical_block` definition: change `<= 0` to `< 0` | cited: C2(c) exact tuple red |
| C3(i) | `_typical_block` definition: count all selected sections | cited: C3 exact count red, `4 != 3` |
| C3(ii) | `_typical_block` definition: count narrowed-thin evidence | cited: C3 exact count red, `3 != 2` |
| C4(i) | `_typical_block` fallback call site: use `terminal=Fraction(1, 1)` | cited: C4(a) exact total red, `3 != 0` |
| C4(ii) | `typical_filters.apply_business_fallback` definition: return terminal for usable values | cited: C4(b) exact total red, `1500 != 2250` |
| C5(i) | `_typical_block` call site: use all grouped sections | cited: C5(b) exact price total red, `750 != 600` |
| C5(ii) | `_typical_block` definition: resolve section-wide evidence | cited: C5(b) exact price total red, `375 != 600` |
| C6(i) | `serializers.py` definition | cited: exact six-key set missing `comparability_profile` |
| C7(i) | `_typical_block` definition | cited: delegation spy observed the private-ladder call mismatch |
| C8(i) | `_typical_block` definition: set `specs = ()` | cited: C8 served narrowing result red, `375 != 600` |
| C8(ii) | `get_task_price_scenario.py` service call site: pass `None` for derived spec | cited: C8 served narrowing result red, `375 != 600` |
| C7(c) planted | temporary private median ladder under the scoped item-economics roots | cited: extra private-ladder hit |
| C7(d) planted | temporary enum-member excluded-state copy under the production root | cited: extra excluded-state-owner hit |

The prompt explicitly required re-running C1(i) and C1(iii); those were run on this tree. The
remaining 14 named rows and 2 planted probes are cited from fix round 4 because their sites and
assertion bodies were unchanged; C1(b)'s changed assertion path was covered by the C1(i) re-run.

## Verification

- Focused C1(b)/C1(d) check: **2 passed**.
- Final targeted phase surface: **72 passed**.
- Focused Ruff on both changed test/fixture files: **All checks passed**.
- Authoritative L4: `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'` →
  **2708 passed / 21 failed / 1 skipped / 2 warnings** in 54.79s.
- Failure-ID delta against the carried 21-ID baseline: **∅/∅**. The 21 failures are pre-existing.
- Redis remained reachable; no configured database was targeted destructively.

## Perimeter and md5

Fix writes this round:

- `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py`
- `app/tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_5.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- this handoff

Mutation-probe files, applied and reverted, separate from the fix writes:

- `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` — final md5
  `213a38a03f7ffaafe954bae68d4da16a`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` — final md5
  `48833e4438348f2d01bcf2d00f64bb20`

Changed fixture/test final md5s:

- `_narrowing_fixture.py` — `77a18d369b197722dabffc353460ddf1`
- `test_narrowed_price_scenario.py` — `163af57f09785d52ce7b6dec6d024a73`

`.archgraph/` was not changed by this session. Its pre-existing owner/maintenance changes remain
outside this fix perimeter; no graph delta is due because no architectural boundary changed.

## Closing stamp

Application tree identity at the L4 stamp: `HEAD` plus the application diff digest recorded by
the coordinator; `git status --porcelain -- app/` contains only the two intended test/fixture
files. No production file is in the final application diff. The plan tracker row and plan header
are now `IMPLEMENTED`.

**State:** `IMPLEMENTED`.
