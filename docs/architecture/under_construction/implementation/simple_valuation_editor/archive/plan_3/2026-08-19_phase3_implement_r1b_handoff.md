---
plan: 3
role: implement
round: 1b
date: 2026-08-19
state: IMPLEMENTED
actor: Codex
---

# Phase 3 implement r1b handoff — carried Phase 2 repairs

Phase 3 is implemented inside the exact two-file application perimeter. The start-of-round
baseline measured **2425 passed / 26 failed / 1 deselected**, matching the r1b gate after the
coordinator's document fix.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required.

## What changed

- `_current_valuation` now has a real committed database-chain guard: an older superseded
  valuation and its current successor are persisted, and the projection must serialize the
  successor's ID and price.
- `_has_purchase_term` ignores `is_deleted is True`, matching `collapse_terms` over the same
  list. A deleted purchase term no longer disables commit while the model ignores it.
- A median fixture with usable values `{11, 12}` pins per-section HALF_EVEN quantisation:
  the substituted section is 12 and the total is 35, rather than truncation's 34.
- The duplicate integration-level `test_c16_discriminating_literal_is_exact` was removed.
  The pure domain test remains the sole owner of the quantity-zero literal.

## F6, F8 and F9 decisions

**F6 — removed.** The detached-only `can_commit = False` block was dead: detached means
`item is None`, and the original `can_commit` conjunction already requires `item is not
None`. Removing the block leaves the existing detached row green while making it clear that
the earlier conjunction owns the behavior.

**F8 — retained both predicates with comments.** The `TaskStep.workspace_id` and
`ItemValuation.workspace_id` filters remain as redundant defense-in-depth. Their actual
tenant boundary is the workspace-scoped `_load_task_and_item` resolution proven by C10; the
comments now say this explicitly instead of presenting the filters as independently
load-bearing. Globally unique task/item client IDs make additional cross-workspace rows at
these two downstream sites weak evidence compared with C10's real-session boundary rows.

**F9 — accepted the duplicate reads.** Collapsing them inside this phase's two-file perimeter
would require either duplicating `get_task_budget_status`'s status/binding/tenant resolution
or changing that shared service's return contract in a prohibited third file. The common
no-evaluation path therefore retains its redundant round trips so D-6's semantic identity
remains exact. This is a recorded latency acceptance, not an unnoticed outcome.

## Criterion → test map

| Criterion | Automated evidence |
|---|---|
| C1 | `test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain` commits an `item_valuations` chain, asserts the current valuation ID and `855000` price, and verifies zero residue across `item_valuations`, `items`, `users`, and `workspaces`. |
| C2 | `test_phase3_c2_deleted_purchase_term_is_ignored_by_admission_and_model` asserts `can_commit is True` and a collapsed model with zero constant deduction. |
| C3 | `test_phase3_c3_half_even_median_differs_from_truncation` asserts total 35 for `{11, 12, None}`. |
| C4 | `test_c16_discriminating_literal_is_exact` is absent from the integration file; `test_quantity_zero_falls_back_to_a_divisor_of_one` is the sole observed-red test for the suite-wide definition mutation. |
| C5 | F6 is absent; the existing `test_c9_non_bound_binding_governs_the_full_payload` still proves detached behavior. Both F8 comments point to `test_c10_task_resolution_is_workspace_scoped_and_hides_deleted`. |
| C6 | F9 was accepted for the reason above. The unchanged phase-2 C1, C2, C9 and C10 rows all pass in the 49-test focused file. |
| C7 | Focused file: 49/49. Full-suite arithmetic and the one external concurrency discrepancy are recorded below with the complete ID delta. |

## Mutation ledger

Every named mutation was applied at the definition site, measured with the whole non-E2E
suite (never `-k`), reverted with `apply_patch`, and SHA-256 checked byte-identical. Each
whole-suite run had the inherited 26-ID baseline plus exactly the one observed-red ID below:
**2426 passed / 27 failed / 1 deselected**.

| Definition site and mutation | Contract side | Mutation side | Complete observed-red delta | Revert SHA-256 |
|---|---|---|---|---|
| `get_task_price_scenario.py:_current_valuation`, drop `superseded_at.is_(None)` | saved ID `ival_price_chain_current_<token>`, price `855000` | saved ID `ival_price_chain_old_<token>`, price `700000` | `test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain` only | `6900297d3b3617bf10f36f796e78dbee91a303e33eb021667c37350407acc775` |
| `get_task_price_scenario.py:_has_purchase_term`, restore unfiltered `any(...)` | deleted purchase term: `can_commit=True`; model constant deduction `0` | `can_commit=False`; model still collapses with constant deduction `0` | `test_phase3_c2_deleted_purchase_term_is_ignored_by_admission_and_model` only | `6900297d3b3617bf10f36f796e78dbee91a303e33eb021667c37350407acc775` |
| `get_task_price_scenario.py:_typical_block`, `round_half_even(...) → int(resolved)` | `{11,12,None}` totals `35` (`11.5 → 12`) | totals `34` (`11.5 → 11`) | `test_phase3_c3_half_even_median_differs_from_truncation` only | `6900297d3b3617bf10f36f796e78dbee91a303e33eb021667c37350407acc775` |
| `price_scenario.py:slider_domain`, `max(1, quantity) → max(6, quantity)` | `slider_domain(8919,0,0) = SliderDomain(110,3080,12100)` | `SliderDomain(114,3078,12084)` | `test_quantity_zero_falls_back_to_a_divisor_of_one` only | `948a7a0f990ad409f26ff97a173fc0eeb2211970d0c9d5e7e1059277aba04542` |

The first candidate form of the C1 database fixture was not accepted into this ledger:
PostgreSQL returned the current row first even after the predicate was removed, so the
contract and mutation sides did not differ. The fixture was strengthened before the recorded
run by forcing a heap scan and a deterministic live-tuple order. The recorded mutant then
returned the older row and reddened exactly C1.

## Verification

Focused phase file:

```text
49 passed in 0.47s
```

Lint and formatting:

```text
.venv/bin/ruff check <the two Phase 3 Python files>
All checks passed!

.venv/bin/ruff format --check <the two Phase 3 Python files>
2 files already formatted

git diff --check
clean
```

Full non-E2E suite arithmetic:

```text
Start baseline: 2425 passed / 26 failed / 1 deselected
Expected:       2425 - 1 duplicate + 3 new rows = 2427 passed / 26 failed / 1 deselected
Observed:       2426 passed / 27 failed / 1 deselected
```

The observed set was repeated and diffed rather than accepted by count. Both repeats had the
same one-ID addition outside Phase 3:

```text
tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py::
test_c3_real_concurrent_open_insert_translates_the_loser[model]
```

That test passed **1/1 in isolation immediately between the repeated full-suite runs**. It
was not in this round's measured start baseline, no Phase 3 test or implementation file
imports it, and addressing its full-suite-only concurrency behavior would require a third
implementation/test file. It was therefore left untouched and is reported as external suite
noise. All other 26 failure IDs are byte-identical to the start baseline.

## Architecture Graph delta

No graph mutation was made: **0 nodes, 0 relationships, 0 source links**. Closing status at
revision `2d76dab324a988e087a529ce230c19c0b02e72077a593f93f581f262375f58c1`
reported 186 nodes, 278 edges, 0 diagnostics, 0 stale nodes, and 10 pending reviews.

The pending inferred projection's stored addresses did drift even though `archgraph_status`
and `archgraph_get_node` reported `stale: false`: the service symbol moved from stored
`149–273` to `152–274`, and the C1 table/test span moved from stored `387–419` to `416–448`.
Per the prompt, these pending coordinator-owned anchors were reported and not repaired. No
review, promotion, rejection, maintenance mutation, or context write was attempted.

## STOPs and scope

No implementation STOP was entered. The final-suite-only concurrency ID is the sole closing
verification discrepancy; fixing or suppressing it would require touching a prohibited third
application/test file, so this session stopped at evidence and did not broaden scope.

## Full write perimeter

Populated from the closing `git status --porcelain --untracked-files=all` and
`git diff --name-only` outputs after this handoff was created.

Session-owned writes:

1. `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py`
2. `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py`
3. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/implementer/2026-08-19_phase3_implement_r1b_handoff.md`

The same status output reported the concurrent untracked
`docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_phase4_rereview_r3_handoff.md`.
This session did not create, read, edit, stage, or commit it.
