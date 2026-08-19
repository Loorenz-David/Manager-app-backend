---
plan: 1
role: implement
round: 2
date: 2026-08-19
state: IMPLEMENTED
actor: Codex
---

# Phase 1 fix r2 handoff — quantity guard evidence and mutation ledger

Both review-r1 should-fix findings are resolved within the authorized two-file application
perimeter. The arithmetic is unchanged. The existing zero-quantity clamp now has an explicit
storage-gap comment and a regression test, and all seven mutation probes were re-measured
against the whole test file with their complete red sets recorded.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required.

## F1 — zero-quantity divisor guard

`test_quantity_zero_falls_back_to_a_divisor_of_one` now contains both required assertions:

1. `slider_domain(1_211_335, 0, 29)` equals
   `SliderDomain(step_minor=15_000, min_minor=420_000, max_minor=1_650_000)`.
2. The same zero-quantity result equals `slider_domain(1_211_335, 1, 29)`, directly pinning
   the clamp-to-one behavior.

The only production edit is a two-line comment at `slider_domain`'s divisor. It points to
intention §§2.7/9.4 and explains that storage has no quantity `CHECK`, so a legacy zero must
be clamped before use as a divisor. The expression remains `max(1, quantity)`.

Named mutation, applied at the `slider_domain` definition:

```text
divisor = max(1, quantity)  →  divisor = quantity
```

- Contract side: `SliderDomain(step_minor=15000, min_minor=420000,
  max_minor=1650000)`, and the `Q=0` result equals the `Q=1` result.
- Mutation side: `ValueError: b must be positive` from `two_significant_digits`.
- Complete observed-red set from the whole file:
  `test_quantity_zero_falls_back_to_a_divisor_of_one`.

## F2 — re-measured whole-file mutation ledger

Each mutation below was applied at the named definition site, followed by a run of the
entire `tests/unit/domain/item_economics/test_price_scenario.py`. No run used `-k` or a node
ID. Each probe was reverted before the next probe, and both files were hash-checked after
every revert. The measured sets agree exactly with prompt §4; there is no disagreement to
report.

| Row | Named mutation and computed sides | Complete observed-red set | Revert SHA-256 |
|---|---|---|---|
| C2 truncation | `round_half_even`: floor-semantic `divmod` → truncation. Contract: `-3/2 → -2`, `-7/2 → -4`; mutation: `-1`, `-3`. | `test_c2_round_half_even_negative_operands_use_floor_semantics[negative-up-to-even]`; `test_c2_round_half_even_negative_operands_use_floor_semantics[lower]` | source `6e00d426e7ac578387b1cb09dced7afb66830bed8461840344339fb817201b2a` |
| C7 tightness | `_assert_c7_bound`: `n + 1 → n`. Contract: attained fixture has `delta=1`, RHS `2`; mutation RHS `1`. | `test_c7_collapsed_budget_stays_within_the_integer_error_bound[percentage-and-fixed-bound-attained]` | test `819684c08b881b6b5dcaa2dfbf2b287fe90ac17eeaa6a09dfd16a283669de1da` |
| C7 mechanism | `collapse_terms`: `int(value.scaleb(3)) → int(float(value) * 1000)`. Contract: `1.001 → 1001`, residual `98_999`, published/persisted `247_498/247_498`, delta `0`; mutation: `1000`, residual `99_000`, `247_500/247_498`, delta `2`. | `test_c7_collapsed_budget_stays_within_the_integer_error_bound[one-percentage-float-mutation]` | source `6e00d426e7ac578387b1cb09dced7afb66830bed8461840344339fb817201b2a` |
| C8 shortcut | `allowance_seconds`: two-step conversion → direct budget-to-seconds conversion. Contract at budget `7`: `1`; mutation: `0`. | `test_c8_seconds_conversion_keeps_the_two_step_rounding`; `test_c9_mockup_break_even_uses_the_exact_integer_search_literal`; `test_c10_break_even_search_is_independent_of_the_slider_band`; `test_c12_fixed_deduction_boundary_and_domain_floor_are_exact`; `test_c12_purely_proportional_mockup_still_runs_the_search` | source `6e00d426e7ac578387b1cb09dced7afb66830bed8461840344339fb817201b2a` |
| C10 cap | `SEARCH_CAP_MINOR`: `2**40 → 2**33`. Contract: break-even `26_649_350_000` and infeasibility cap `2**40`; mutation: break-even `None` and cap `2**33`. | `test_c10_break_even_search_is_independent_of_the_slider_band`; `test_c12_degenerate_model_publishes_the_exact_infeasibility_cap` | source `6e00d426e7ac578387b1cb09dced7afb66830bed8461840344339fb817201b2a` |
| C17 derive-then-snap | `slider_domain`: per-piece derivation → derive whole-item step then snap. At `Q=7`, contract `15_400 / 415_800 / 1_647_800`; mutation `15_001 / 420_028 / 1_650_110`. | `test_c12_fixed_deduction_boundary_and_domain_floor_are_exact`; `test_c17_quantity_seven_slider_domain_uses_per_piece_derivation`; `test_c18_minimum_resolves_disagreeing_floor_constraints` | source `6e00d426e7ac578387b1cb09dced7afb66830bed8461840344339fb817201b2a` |
| F1 guard | `slider_domain`: `max(1, quantity) → quantity`. Contract: exact `15_000 / 420_000 / 1_650_000` band and `Q=0 == Q=1`; mutation: `ValueError: b must be positive`. | `test_quantity_zero_falls_back_to_a_divisor_of_one` | source `6e00d426e7ac578387b1cb09dced7afb66830bed8461840344339fb817201b2a` |

The six original probes reddened `2, 1, 1, 5, 2, 3` tests respectively; the new F1 probe
reddened one. Clean whole-file runs after the edits and again after all reverts each passed
all 53 tests.

Final and post-revert hashes:

```text
6e00d426e7ac578387b1cb09dced7afb66830bed8461840344339fb817201b2a  app/beyo_manager/domain/item_economics/price_scenario.py
819684c08b881b6b5dcaa2dfbf2b287fe90ac17eeaa6a09dfd16a283669de1da  app/tests/unit/domain/item_economics/test_price_scenario.py
```

## Notes deliberately not acted on

No note from prompt §5 (N1–N7) was acted on. In particular, no computation, shape
validation, pre-check branch, import rule, or public name was changed.

## Verification

From `app/`:

```text
PYTHONPATH=. .venv/bin/pytest -q tests/unit/domain/item_economics/test_price_scenario.py
53 passed

.venv/bin/ruff check beyo_manager/domain/item_economics/price_scenario.py tests/unit/domain/item_economics/test_price_scenario.py
All checks passed!

.venv/bin/ruff format --check beyo_manager/domain/item_economics/price_scenario.py tests/unit/domain/item_economics/test_price_scenario.py
2 files already formatted
```

Full non-E2E suite before this fix: **2372 passed / 26 failed / 1 deselected**.

Full non-E2E suite after this fix:

```text
PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q
2373 passed, 26 failed, 1 deselected, 2 warnings in 137.89s
```

The pass count increased by exactly the one new regression test and the inherited failure
count remained 26, so the prompt's repeat-and-diff rule was not triggered.

## Architecture Graph delta

Graph orientation and closing status reused the pending inferred
`source-file-item-economics-price-scenario` node. This fix adds no architectural concept,
relationship, or boundary, so the additive delta is **0 nodes / 0 relationships / 0 source
links**. No review or maintenance mutation was attempted.

Closing graph status remains valid at revision
`084fd3e9f52930a2877331a228f2798aeafdeba3dae7bc73f9b75070c1d1869b`, with 184 nodes,
276 edges, 6 pending reviews, 0 diagnostics, and 0 source-link stale nodes.

The pending node's descriptive evidence now has address/content drift: the production
evidence's relevant end moved from line 209 to 211, and the test evidence now ends at line
426 and covers 53 rather than 52 tests. That pending-review metadata was not changed because
the fix prompt permits only the two application edits plus this required handoff, and review
or anchor mutation requires a separate authorized graph-review action.

## Full write perimeter

Generated at close from repository-root `git status --porcelain --untracked-files=all` and
`git diff --name-only`. This session wrote exactly:

1. `app/beyo_manager/domain/item_economics/price_scenario.py` — two-line comment only.
2. `app/tests/unit/domain/item_economics/test_price_scenario.py` — one new test.
3. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/implementer/2026-08-19_phase1_fix_r2_handoff.md` — this required handoff.

The same status commands also reported eight pre-existing coordinator/reviewer paths that
were present before this session and were preserved without edits:

1. `.archgraph/architecture.yml`
2. `.archgraph/reviews/2026-08-19T15-13-32-988Z--741606.yml`
3. `docs/architecture/under_construction/implementation/simple_valuation_editor/master_plan.md`
4. `docs/architecture/under_construction/implementation/simple_valuation_editor/planning/intention.md`
5. `docs/architecture/under_construction/implementation/simple_valuation_editor/plans/plan_1.md`
6. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_phase1_review_r1_handoff.md`
7. `docs/architecture/under_construction/implementation/simple_valuation_editor/prompts/implementer/2026-08-19_phase1_fix_r2.md`
8. `docs/architecture/under_construction/implementation/simple_valuation_editor/prompts/reviewer/2026-08-19_phase1_review_r1.md`

The master-plan tracker and plan 1 Review log were not edited. Mutation probes temporarily
touched only the two application files above and were fully reverted.
