---
plan: 1
role: implement
round: 1
date: 2026-08-19
state: IMPLEMENTED
actor: Codex
---

# Phase 1 implement r1 handoff — pure price mechanisms

Phase 1 is implemented inside its two-file application perimeter. The new pure module
collapses cost terms, preserves the calculator's integer HALF_EVEN behavior, computes the
price-to-allowance model, searches the break-even and infeasibility boundaries, and derives
the exact-rational slider band. All 21 criteria are covered by 52 new tests. Every named
mutation was observed red and reverted to a byte-identical file.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required.

## What was built

- `app/beyo_manager/domain/item_economics/price_scenario.py`
  - integer `round_half_even` with floor semantics for negative numerators;
  - active-term collapse over the production enum shape, with exact `Decimal.scaleb(3)`
    canonicalisation;
  - the three-stage price → budget → centiminutes → seconds calculation;
  - capped lower-bound searches for break-even and the last infeasible price;
  - exact-rational step helpers, two-significant-digit step derivation, and the
    `break_even_band_v1` arithmetic;
  - no query, ORM-model, SQLAlchemy, service, serializer, or route import.
- `app/tests/unit/domain/item_economics/test_price_scenario.py`
  - 52 tests covering C1–C21, including real unpersisted `CostModelTerm` instances for C4
    and C7 and an AST direct-import purity assertion for C21.

## Delegations and judgment calls

### D-1 — signatures and parameter carrier

Chosen module: `beyo_manager.domain.item_economics.price_scenario`.

Chosen parameter carrier: frozen `PriceModel(residual_percent_milli,
constant_deduction_minor, cost_per_worker_minute_ten_thousandths)`. The frozen
`SliderDomain(step_minor, min_minor, max_minor)` is the result carrier for the band.
`collapse_terms` intentionally returns the specified `tuple[int, int] | None`, so phase 2
can distinguish missing purchase cost before constructing `PriceModel`.

Public functions for the master-plan registry:

1. `round_half_even(a, b)`
2. `collapse_terms(terms, purchase_cost_minor)`
3. `budget_minor(price_minor, model)`
4. `allowed_centimin(price_minor, model)`
5. `allowance_seconds(price_minor, model)`
6. `break_even_price_minor(model, typical_total_seconds)`
7. `infeasible_at_or_below_minor(model)`
8. `floor_to_step(value, step)`
9. `ceil_to_step(value, step)`
10. `digits(value)`
11. `two_significant_digits(a, b)`
12. `slider_domain(break_even_minor, quantity, infeasible_minor)`

Public supporting names are `CostModelTermInput`, `PriceModel`, `SliderDomain`, and
`SEARCH_CAP_MINOR`.

Rationale: one frozen carrier keeps the three model coefficients together across the
per-frame functions and the searches, while leaving term collapse's two specified outcomes
explicit. Module functions keep the two-language arithmetic contract visible rather than
hiding it behind instance methods.

### D-2 — deleted terms

`collapse_terms` filters with `term.is_deleted is True`, so both persisted `False` and the
unflushed ORM default `None` are active. This makes the boundary safe both for phase 1's
real unpersisted instances and for phase 2's already-filtered query result.

### D-3 — missing percentage value

Chosen: reject a percentage term whose `percent_value is None` with
`ValidationError("ITEM_COST_TERM_SHAPE_INVALID: …")`. The same validation also rejects
cross-type value-column mismatches. This preserves the existing calculator's term-shape
semantics for unflushed fixtures even though the database CHECK prevents the state for
persisted rows.

### D-4 — `digits`

Chosen: expose `digits(value)` and test `digits(0) == 1` directly. This avoids obtaining
the same number indirectly from `two_significant_digits` through its independent floor at
one.

No other judgment call or contract deviation was made.

## Criterion → test map

| Criterion | Automated test(s) |
|---|---|
| C1 | `test_c1_round_half_even_positive_operands` (4 enumerated rows) |
| C2 | `test_c2_round_half_even_negative_operands_use_floor_semantics` (4 enumerated rows) |
| C3 | `test_c3_price_percentage_rounding_reaches_a_half_even_tie`; `test_c3_rate_division_reaches_a_half_even_tie`; `test_c3_seconds_conversion_is_tie_free_and_matches_half_up` |
| C4 | `test_c4_collapse_terms_enumerates_model_shapes_with_real_orm_instances` (7 enumerated shapes) |
| C5 | `test_c5_percentage_scale_above_three_is_a_named_shape_error`; `test_c5_numerically_equal_percentage_scale_is_accepted` |
| C6 | `test_c6_purchase_term_with_missing_purchase_cost_returns_none`; `test_c6_purchase_cost_without_purchase_term_is_ignored`; `test_c6_shape_error_raises_while_missing_purchase_cost_returns_none` |
| C7 | `test_c7_collapsed_budget_stays_within_the_integer_error_bound` (7 enumerated real-ORM shapes) |
| C8 | `test_c8_seconds_conversion_keeps_the_two_step_rounding` |
| C9 | `test_c9_break_even_is_the_smallest_price_reaching_the_target`; `test_c9_mockup_break_even_uses_the_exact_integer_search_literal` |
| C10 | `test_c10_break_even_search_is_independent_of_the_slider_band` |
| C11 | `test_c11_search_that_reaches_the_cap_returns_none` |
| C12 | `test_c12_fixed_deduction_boundary_and_domain_floor_are_exact`; `test_c12_degenerate_model_publishes_the_exact_infeasibility_cap`; `test_c12_purely_proportional_mockup_still_runs_the_search` |
| C13 | `test_c13_non_positive_residual_has_no_break_even_or_domain` |
| C14 | `test_c14_step_helpers_apply_directly_to_an_exact_rational` |
| C15 | `test_c15_two_significant_digits_enumerates_integer_lengths` (4 rows); `test_c15_two_significant_digits_is_floored_at_one`; `test_c15_digits_zero_is_exposed_and_asserted_directly` |
| C16 | `test_c16_mockup_slider_domain_is_exact` |
| C17 | `test_c17_quantity_seven_slider_domain_uses_per_piece_derivation` |
| C18 | `test_c18_minimum_resolves_disagreeing_floor_constraints` |
| C19 | `test_c19_domain_is_none_when_the_minimum_reaches_the_maximum` |
| C20 | `test_c20_zero_typical_has_no_break_even_or_domain` |
| C21 | `test_c21_module_has_no_direct_import_from_forbidden_boundaries` |

No criterion lacks an automated test.

## Mutation ledger

Mutation probes touched only the two files listed under “Mutation-probe perimeter”; every
probe was reverted before the final suite.

| Criterion | Named site | Contract value | Mutation value | Observed red | Revert SHA-256 |
|---|---|---|---|---|---|
| C2 | `price_scenario.py`, `round_half_even` definition: replace floor-semantic `divmod` with truncation | `round_half_even(-3, 2) == -2`; all 4 C1 positive rows green | `round_half_even(-3, 2) == -1` | C2 rows `negative-up-to-even` and `lower` failed (`-1 != -2`, `-3 != -4`); C1 remained green | `91dbceb4d00cb07d6ccbd558ea0e4f28fe64c5bc8754ae27ba04d96afe5bc99e` |
| C7 tightness | `test_price_scenario.py`, `_assert_c7_bound` definition: `n + 1 → n` | attained fixture: `delta = 1`, RHS `n + 1 = 2`, so `2 <= 2` | RHS `n = 1`, so `2 <= 1` is false | only `percentage-and-fixed-bound-attained` failed; other 6 C7 rows passed | `560dd0d258c95ffb402dde4c2b1235e49d73048af0862dc040b502c8e66601c9` |
| C7 mechanism | `price_scenario.py`, `collapse_terms` definition: `int(value.scaleb(3)) → int(float(value) * 1000)` | `Decimal("1.001") → 1001`, residual `98_999`, published/persisted `247_498/247_498`, `delta = 0` | float path gives `1000`, residual `99_000`, published/persisted `247_500/247_498`, `delta = 2`, so `4 <= 2` is false | only `one-percentage-float-mutation` failed; other 6 C7 rows passed | `91dbceb4d00cb07d6ccbd558ea0e4f28fe64c5bc8754ae27ba04d96afe5bc99e` |
| C8 | `price_scenario.py`, `allowance_seconds` definition: replace two-step conversion with direct budget → seconds | at budget `7`, two-step result `1` second | direct shortcut result `0` seconds | `test_c8_seconds_conversion_keeps_the_two_step_rounding` failed (`0 != 1`) | `91dbceb4d00cb07d6ccbd558ea0e4f28fe64c5bc8754ae27ba04d96afe5bc99e` |
| C10 | `price_scenario.py`, search cap definition: `2**40 → 2**33` (below `2**34`) | break-even `26_649_350_000` | `None` after the cap is exhausted | `test_c10_break_even_search_is_independent_of_the_slider_band` failed | `91dbceb4d00cb07d6ccbd558ea0e4f28fe64c5bc8754ae27ba04d96afe5bc99e` |
| C17 | `price_scenario.py`, `slider_domain` definition: derive whole-item step first, then ceil it to a multiple of `Q` | at `Q = 7`: `15_400 / 415_800 / 1_647_800` | `15_001 / 420_028 / 1_650_110` | `test_c17_quantity_seven_slider_domain_uses_per_piece_derivation` failed; pytest reported all three dataclass attributes different | `91dbceb4d00cb07d6ccbd558ea0e4f28fe64c5bc8754ae27ba04d96afe5bc99e` |

Final hashes rechecked together after all probes:

```text
91dbceb4d00cb07d6ccbd558ea0e4f28fe64c5bc8754ae27ba04d96afe5bc99e  app/beyo_manager/domain/item_economics/price_scenario.py
560dd0d258c95ffb402dde4c2b1235e49d73048af0862dc040b502c8e66601c9  app/tests/unit/domain/item_economics/test_price_scenario.py
```

## Verification

### Phase tests

Command from `app/`:

```text
PYTHONPATH=. .venv/bin/pytest -q tests/unit/domain/item_economics/test_price_scenario.py
52 passed in 0.14s
```

### Full non-E2E suite

Recorded clean-tree baseline at `f1c0ebb`: **2320 passed / 26 failed / 1 deselected**
(2347 collected).

After phase 1:

```text
PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q
2372 passed, 26 failed, 1 deselected, 2 warnings in 139.77s
```

The pass count rose by exactly 52 and the inherited failure count remained 26, so the
suite-instability rule did not require a repeat or failure-ID diff. No new phase test
failed. The 26 inherited failures remain outside this phase's two-file perimeter.

### Lint

The two changed application files pass both checks:

```text
.venv/bin/ruff check beyo_manager/domain/item_economics/price_scenario.py tests/unit/domain/item_economics/test_price_scenario.py
All checks passed!

.venv/bin/ruff format --check beyo_manager/domain/item_economics/price_scenario.py tests/unit/domain/item_economics/test_price_scenario.py
2 files already formatted
```

Repository-wide `.venv/bin/ruff check .` remains red with **137 pre-existing errors**;
none is in either phase file. The first reported error is the already-present undefined
`datetime` annotation in `budget_division.py:40`, which is outside this phase's perimeter.

## Architecture Graph delta

Orientation reused the human-confirmed `domain-item-economics` node and inspected its
evidence plus the existing `source-file-item-economics-budget-division` branch. Impact at
depth 2 returned no affected nodes. Search for `price scenario`, `expected sold price`, and
`break even slider domain` returned no existing concept.

One batched additive delta was applied at graph revision
`50b3940273f51b9bafeb5a48f08c5970e291d6f9f95abb604af51db5d771f00b`:

- 1 inferred projection node:
  `projection-item-economics-expected-sold-price-scenario`, confidence `0.96`, evidenced by
  `price_scenario.py:25-209` and `test_price_scenario.py:79-417`;
- 1 inferred canonical relationship:
  `domain-item-economics --contains--> projection-item-economics-expected-sold-price-scenario`,
  confidence `0.96`, evidenced by `price_scenario.py:1-11`;
- 0 source links (none inferred without human authorization);
- 0 skipped or duplicate items; 0 diagnostics.

Post-write revision:
`e3758a82cb5c02c020d4c57184a521661d2aa6c3e8d7de4b512ceae4fbd1d642`.
Graph status is valid with 184 nodes, 276 edges, no diagnostics, and no stale nodes. The
two new inferred items are pending human review; no review or maintenance mutation was
attempted.

Exploration budget was depth 2 / maximum 15 new nodes; actual depth 2, 1 new node, 1 new
relationship, and no generated context artifact. No unresolved architecture boundary was
encountered.

## STOPs and coordinator observations

No STOP was hit and no out-of-perimeter application file was needed.

One upstream documentation observation needs coordinator handling: `master_plan.md` §6
currently says **“This phase ADDS routes”** and expects the mirror count to move 25 → 26.
That conflicts with plan 1 and the implementer prompt, both of which explicitly fence phase
1 to pure arithmetic and assign the route to phase 2. No route or mirror artifact was
changed here; the master-plan environment line should be corrected when this handoff is
consumed.

## Full write perimeter

Generated from repository-root `git status --porcelain --untracked-files=all` and
`git diff --name-only`; the project documentation folder was already entirely untracked,
so the status command also lists pre-existing planning/prompt rows that this session did
not write. The session's complete writes are:

1. `.archgraph/architecture.yml` — reported by both `git status` and `git diff --name-only`;
   tool-recorded additive graph delta.
2. `app/beyo_manager/domain/item_economics/price_scenario.py` — reported by `git status` as
   untracked; new production module.
3. `app/tests/unit/domain/item_economics/test_price_scenario.py` — reported by `git status`
   as untracked; new test module.
4. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/implementer/2026-08-19_phase1_implement_r1_handoff.md`
   — reported by `git status` as untracked; this handoff.

The master-plan tracker and plan Review log were not edited, per prompt §10.5.

### Mutation-probe perimeter (applied and reverted; not implementation changes)

1. `app/beyo_manager/domain/item_economics/price_scenario.py`
2. `app/tests/unit/domain/item_economics/test_price_scenario.py`

No probe touched documentation or Architecture Graph state.
