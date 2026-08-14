---
plan: phase 5 (valuation surface)
role: implementer
state: IMPLEMENTED
date: 2026-08-13
actor: Codex
checkpoint: 8b4ac06d797010d1886aebfbfe0c582010ba0ff7
---

# Phase 5 implementer handoff

## Summary

Phase 5 valuation surface is implemented and checkpointed. The surface now supports versioned valuation writes, persisted-rate previews, current valuation deletion with superseded-row immutability, valuation history, request validation, audit events, and the three ADMIN/MANAGER routes.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Verification

- Focused valuation/unit/router suite: **111 passed**.
- Valuation integration and two-session race subset: **each passed twice**.
- Ruff and `git diff --check`: passed.
- Alembic: development DB at `5caae620088c` (head).
- Full suite: **1951 passed, 23 failed, 2 warnings**. The 23 failures are byte-identical to the established non-phase baseline; no phase-5 failure was present.

## Contract points exercised

- Selection and item-readiness resolution use the registered authority functions and explicit readiness precedence.
- Preview envelope is `item_valuation` plus `preview`; non-computable statuses carry null numerics, while `not_evaluated` uses the persisted worker-minute rate.
- The persisted-rate fixture asserts `76800.20`, distinguishing it from raw re-division `76800.00`.
- Set uses close-before-insert ordering and translates `uix_item_valuations_current` to `ITEM_COST_CONCURRENT_VALUATION`.
- The race test uses two real sessions, bounded waits, both no-current and current-row paths, and scoped cleanup of the five valuation-chain tables plus actor/workspace rows.
- History excludes deleted rows and orders by `created_at DESC, client_id DESC`.
- Delete returns the status-only `item_unvalued` preview and rejects superseded rows with `ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE`.

## Mutation probe declaration

Applied-and-reverted probes, with restored hash → mutant hash and observed red set:

| Contract | Restored SHA-256 | Mutant SHA-256 | Observed red set |
|---|---|---|---|
| Readiness precedence: expected-price before purchase-cost | `14dfea80ae0d7ac48f34765de5214556093effc71565701c8d764a434b65916a` | `04b7dd209172e7f552420c90bf202ba925a9da18fa0d569b4c4b329cf28d076a` | `test_item_readiness_uses_registered_order_and_requires_a_purchase_term` |
| Preview consumes persisted rate | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `a3586652a72b2680773171139f22d5a4ddcd699da64c47efdc1124142fc80e33` | `test_valuation_chain_preview_delete_and_history` |
| History hides deleted rows | `6f586d0f4d086abf5a5c035fe4ca07c99ee1d34723b12b871efb2f717cd4e16c` | `ce760b82e31bd56748d8dfddd348df22f8cd9f9fba5af1ce75a16ec658b22bb2` | `test_valuation_chain_preview_delete_and_history` |

Probe-only files touched and restored: `app/beyo_manager/domain/item_economics/configuration.py`, `app/beyo_manager/services/commands/item_economics/set_item_valuation.py`, and `app/beyo_manager/services/queries/item_economics/get_item_valuation_history.py`.

## Full write perimeter

Implementation and verification files in checkpoint `8b4ac06`:

- `app/beyo_manager/domain/item_economics/configuration.py`
- `app/beyo_manager/domain/item_economics/serializers.py`
- `app/beyo_manager/routers/README.md`
- `app/beyo_manager/routers/api_v1/item_economics.py`
- `app/beyo_manager/services/commands/item_economics/_common.py`
- `app/beyo_manager/services/commands/item_economics/requests/__init__.py`
- `app/beyo_manager/services/commands/item_economics/set_item_valuation.py`
- `app/beyo_manager/services/commands/item_economics/delete_item_valuation.py`
- `app/beyo_manager/services/queries/item_economics/get_item_valuation_history.py`
- `app/tests/unit/domain/item_economics/test_configuration.py`
- `app/tests/unit/routers/api_v1/test_item_economics_router.py`
- `app/tests/unit/services/commands/item_economics/test_item_economics_requests.py`
- `app/tests/integration/services/commands/item_economics/test_valuation_surface.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_5_valuation_surface.md`
- `.archgraph/architecture.yml`

This handoff is deposited after the checkpoint and is the only post-checkpoint file.

## Architecture Graph

Duplicate preflight found all five candidates new. One additive batch recorded 5 nodes and 7 relationships for the two commands, three endpoints, accepts/writes-to/reads-from/returns edges, with accurate command/query/route evidence. New graph revision: `b5e6fe094caee2191414a297bb1ab63507ebda8ee4ee54c26cc612a5d940fc94`. No review decisions were made.

## Delegations

- Preview computation is inside the set command transaction.
- The preview envelope uses `item_valuation` and `preview`.
- Unknown item identifiers use the existing `NotFound` behavior.
