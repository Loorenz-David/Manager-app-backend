---
plan: plan_5
role: fix
state: IMPLEMENTED
date: 2026-08-24
actor: Codex
---

# Plan 5 fix round 4 handoff

## Summary

Completed the two dispatched test-only corrections. C1(b) now uses the fixture's category-less
`plain_task`, so it measures the section-wide `375` result and is decoupled from narrowing. The
serialized byte-identity assertion now runs before the numeric assertion. No production code and
no fixture code changed.

## Gate and baseline

- `git status --porcelain -- app/`: empty at opening.
- `plans/plan_5.md` header: `CHANGES_REQUESTED` at opening.
- Master tracker row 5: `CHANGES_REQUESTED` at opening.
- `planning/intention.md` header: `RATIFIED`.
- `redis-cli ping`: `PONG`.
- Check 6 found `narrowed_task` inside `test_c1b_…`, proving this round was outstanding.
- Pre-edit targeted baseline, from `app/` with `BEYO_TEST_SLOT=main PYTHONPATH=.`: **83 passed**
  across the three phase integration files.
- The carried full-suite baseline is **2707 passed / 21 failed / 1 skipped**, with the same 21
  failure IDs used for the closing delta.

## Changes

Modified file:

- `app/tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py`
  - C1(b) context now uses `fixture["plain_task"]`.
  - Byte-identity assertion precedes the exact numeric assertion.
  - Section-wide exact total is `375` on both calls.

The prescribed fake datetime still returns `ctx.now - 1s` and `ctx.now + 1s`; the existing fixture
still pins `max(closed_at) == 2026-08-01 00:00 UTC`, exactly 90 days before frozen
`ctx.now = 2026-10-30 00:00 UTC`. `_narrowing_fixture.py` was not modified.

## Task 0 coverage map

| criterion row | discharging test | assertion shape |
|---|---|---|
| C1(a) | `test_c1a_typical_block_passes_the_request_clock_to_the_statement` | exact delegated `now=ctx.now` and `specs=()` |
| C1(b) | `test_c1b_same_frozen_context_produces_byte_identical_typicals` | exact JSON byte identity first; exact `375` totals second |
| C1(c) | `test_c1c_working_section_typicals_keep_the_default_statement_clock` | exact no-`now` kwarg plus invoked spy |
| C2(a) | parametrized `test_c2_is_estimated_tracks_empty_none_and_zero_selected_typicals` | exact `true`, `0`, `0` |
| C2(b) | same parametrized test | exact `true`, one selected `None`, count `1` |
| C2(c) | same parametrized test | exact `true`, one selected `0`, count `1` |
| C2(d) | `test_c2d_section_wide_uniform_does_not_make_is_estimated_true` | exact `false`, count `0` |
| C3 | `test_c3_counts_only_participating_selected_typicals` | exact counts `3` and `2` |
| C4(a) | `test_c4_price_terminal_and_median_are_duration_values` | exact total `0`, estimated `true` |
| C4(b) | same parametrized test | exact total `2250`, estimated `true` |
| C5(a) | `test_c5_three_surfaces_use_the_same_published_literal` | exact production-time triple `(600, "item_narrowed", 5)` |
| C5(b) | same C5 test | exact participating price total `600` |
| C5(c) | same C5 test | exact budget-allocation triple `(600, "item_narrowed", 5)` |
| C6(a) | `test_c6_price_and_production_resolution_have_the_exact_six_key_shape` | exact six-key price set |
| C6(b) | same C6 test | exact six-key production set |
| C6(c) | same C6 test | exact literal basis/filter/count values |
| C7(a) | `test_c7_typical_block_delegates_statistics_and_has_no_private_terms` | exact one-call spy and private-term absence |
| C7(b) | `test_c7_item_economics_fork_sweep_finds_only_the_shared_median` | exact scoped root/term sweep |
| C7(c) planted proof | same C7 sweep | observed red from temporary private ladder |
| C7(d) planted proof | `test_c13c_excluded_state_logic_has_one_shared_production_owner` | observed red from temporary enum copy |
| C8(a) | `test_c8_divergent_fixture_measures_narrowed_600_against_section_375` | exact served `600` narrowed total |
| C8(b) | same C8 test | exact served `375` plain total; named production-time triple remains the declared N3 deviation |
| C8(c) | same C8 test | exact service edge observed end to end |

Reverse map: all tests in the phase-5 test files cited by the round-3 handoff remain mapped to
these rows; this round added no test. There are no orphan tests.

## Mutation ledger

Summands: `C1 2 · C2 3 · C3 2 · C4 2 · C5 2 · C6 1 · C7 1 · C8 2 = 15` named mutations;
`C7(c) 1 + C7(d) 1 = 2` planted-defect probes; **17 total**.

| row | site and evidence | observed red |
|---|---|---|
| C1(i) | `get_task_price_scenario.py`, `_typical_block` call site: remove `now=ctx.now`; re-run C1(a)+C1(b) | C1(a) `KeyError: 'now'`; C1(b) byte-identity assertion shows differing serialized JSON, with first total `375` and second total `0` |
| C1(ii) | `get_working_section_typical_times.py`, call site: add `now=ctx.now` | cited from round 3: C1(c) `assert 'now' not in captured` |
| C2(i) | `_typical_block` definition: remove empty-set disjunct | cited from round 3: C2(a) tuple changed from `(0, True, 0, 0)` |
| C2(ii) | `_typical_block` definition: flag narrowed-thin evidence instead | cited from round 3: C2(d) `assert True is False` |
| C2(iii) | `_typical_block` definition: change `<= 0` to `< 0` | cited from round 3: C2(c) expected tuple differed |
| C3(i) | `_typical_block` definition: count all selected sections | cited from round 3: C3 `assert 4 == 3` |
| C3(ii) | `_typical_block` definition: count narrowed-thin evidence | cited from round 3: C3 `assert 3 == 2` |
| C4(i) | `_typical_block` fallback call site: `terminal=Fraction(1, 1)` | cited from round 3: C4(a) `assert 3 == 0` |
| C4(ii) | `typical_filters.apply_business_fallback` definition: return terminal for usable values | cited from round 3: C4(b) `assert 1500 == 2250` |
| C5(i) | `_typical_block` call site: use all grouped sections | cited from round 3: C5(b) `assert 750 == 600` |
| C5(ii) | `_typical_block` definition: resolve section-wide evidence | cited from round 3: C5(b) `assert 375 == 600` |
| C6(i) | `serializers.py` definition: omit `comparability_profile` | cited from round 3: exact price six-key set missing the key |
| C7(i) | `_typical_block` definition: replace shared fallback with private ladder | cited from round 3: spy calls `[]` instead of the expected call |
| C8(i) | `_typical_block` definition: `specs = ()` | re-run C8: served assertion `assert 375 == 600` |
| C8(ii) | `get_task_price_scenario.py`, service call site: pass `None` for the derived spec | re-run C8: served assertion `assert 375 == 600` |
| C7(c) planted | temporary private median ladder under the scoped sweep root | cited from round 3: extra `_mutation_probe_private_ladder.py` hit |
| C7(d) planted | temporary enum-member excluded-state copy under the production root | cited from round 3: extra `_mutation_probe_excluded_states.py` hit |

The three round-4 probes were applied and reverted. The other 14 named rows and both planted
probes are cited from the round-3 handoff because their sites and observed reds are unaffected by
this edit, as the v3 prompt permits. No probe was green where a red was required.

## Verification and closing stamp

- Targeted phase surface: **83 passed**.
- Ruff on the changed test: **All checks passed**.
- Authoritative L4 command: `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'`.
- L4 result: **2707 passed / 21 failed / 1 skipped / 2 warnings** in 61.12s.
- Failure-ID delta against the carried round-3/round-2 21-ID baseline: **∅/∅**.
- L4 application identity: `HEAD 09cbebca04359e2cac0c73709fb2f924cb12b5f1` plus
  `sha256(git diff --binary -- app/) =
  93979451b4e19183e84caa33b16dcb70edbe5c09b626a495654ec2f4415661c4`.
- `app/` was dirty only for the intended test-file change at the stamp.

## Perimeter and md5

Fix writes this round:

- `app/tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_5.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- this handoff

Mutation-probe files applied and reverted this round, separate from the fix writes:

- `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` — final md5
  `213a38a03f7ffaafe954bae68d4da16a`

The prior-round cited probe files were not touched in this round. Final md5s of the relevant
unchanged production/fixture files are:

- `get_working_section_typical_times.py` — `48833e4438348f2d01bcf2d00f64bb20`
- `typical_filters.py` — `c888e3d24748edfa6fe22a0c24605b45`
- `serializers.py` — `e4e01db8c82421d7d00ce9e049441aaa`
- `_narrowing_fixture.py` — `0e4f2eabc5b634747bd681fb12b23d59`

`.archgraph/` contains pre-existing owner changes and was neither read for state nor touched.
No graph delta is due: no architectural boundary changed.

## Review log disposition

No judgment call or deviation was introduced beyond the prompt's two corrections. The remaining
N2/N3/N5 and S1 dispositions are carried unchanged from round 3. The L4 failures are the same
pre-existing 21 IDs; no new failure was introduced.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

State: `IMPLEMENTED`; ready for coordinator consumption and re-review.
