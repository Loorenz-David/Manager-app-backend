---
plan: phase 5 (valuation surface)
role: implementer
state: IMPLEMENTED
date: 2026-08-14
actor: Codex
checkpoint: a0cebde86102f9787d3ac5120e48350f399b1c39
---

# Phase 5 fix r1 implementer handoff

## Summary

Phase 5 fix r1 is implemented and checkpointed. The valuation delete lookup now
uses the full current-row predicate, and the test surface now proves the
12-value preview enumeration, resolver delegation, independent currency
clauses, precedence, history ordering, race observables, request acceptance,
and persisted-rate arithmetic.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Verification

- Focused phase suite: **62 passed**.
- Required race subset: **1 passed twice consecutively**.
- Full non-e2e suite: **1968 passed / 23 failed / 1 deselected / 2 warnings**.
  The 23 failures are the established baseline set; no phase-5 test failed.
- Targeted Ruff and `git diff --check`: passed. Repository-wide Ruff reports
  122 pre-existing findings outside this change perimeter.
- Alembic development database: `5caae620088c` (head).
- Architecture Graph: read-only, zero delta; 153 nodes / 195 edges, revision
  `b5e6fe094caee2191414a297bb1ab63507ebda8ee4ee54c26cc612a5d940fc94`.

## Contract points exercised

- Delete-then-reset-then-delete leaves exactly one live `INV-V1` current row and
  permits deletion of the new valuation; supersession history and audit events
  remain ordered and complete.
- C5 has 12 explicit ids covering status rows, sole predicates, and reachability
  judgments. Preview rows assert null numerics where required and leave
  `item_cost_evaluations` unchanged.
- The preview loader delegates the major-category snapshot to
  `resolve_major_category`; no inline enum classification is permitted.
- Currency mismatch uses the two independent equal-pair clauses. A fixture
  proves missing purchase cost precedes currency mismatch.
- History reads use `created_at DESC, client_id DESC`, are byte-identical on
  repeat, hide deleted rows, and assert the current-row count.
- Request validation rejects missing currency and accepts expected-only,
  cost-only, and both-value requests.
- Persisted rate `13.0000` produces the expected `76923.08`; raw re-division
  mutants redden the valuation-chain test.

## Mutation probe declaration

All probes were applied, observed, and reverted. The restored hashes below are
the final committed-file hashes; the observed red sets are the actual failed
test ids.

| Contract | Restored SHA-256 | Mutant SHA-256 | Observed red set |
|---|---|---|---|
| B1-revert: remove delete `is_deleted IS false` | `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1` | `23cfe90f65bf7b4c1ba536bbf86304e22ba65ccf3cafffac792d2b71ed75e365` | `test_valuation_chain_preview_delete_and_history` |
| M4: bypass `resolve_major_category` | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `e818fa2b74af93c79e1e0709c93e5281d17f3fb1ff5ffb1fddf2306a80fcfad7` | C5 missing-expected, missing-purchase, currency-mismatch, not-evaluated, no-basis, no-model; chain |
| M5.a: drop valuation-basis currency clause | `75087586aae405c57117f6417720743102fbc4003336ce2e6e25689800d68bde` | `ee22880184daa7b86ffc367b02fcc1563261cb61f5d9bf1869ecd1544790a957` | `test_item_readiness_rejects_each_currency_mismatch_pair[basis-model]` |
| M5.c: drop basis-model currency clause | `75087586aae405c57117f6417720743102fbc4003336ce2e6e25689800d68bde` | `796ad66ee15e530ac57751ea87c9e5de2c9bd15d2ee43fb74427c2de57f0716b` | `test_item_readiness_rejects_each_currency_mismatch_pair[valuation-basis]` |
| M3.2: swap purchase-cost/currency precedence | `75087586aae405c57117f6417720743102fbc4003336ce2e6e25689800d68bde` | `bf241b9d507a70a250224ee5b71558ca216bdf128cab055b25d3ee17247548cf` | `test_item_readiness_purchase_cost_precedes_currency_mismatch` |
| M8: drop history ordering | `6f586d0f4d086abf5a5c035fe4ca07c99ee1d34723b12b871efb2f717cd4e16c` | `8847d378bfb0cae10b324b0e0365125cd78f13311b7e64f72217722c3db87ef2` | `test_valuation_chain_preview_delete_and_history` |
| M8b: reverse history ordering | `6f586d0f4d086abf5a5c035fe4ca07c99ee1d34723b12b871efb2f717cd4e16c` | `f663c2536dcc446baf777a6208d1ac413e185e80f91982c57b8c770428f98f48` | `test_valuation_chain_preview_delete_and_history` |
| M9: drop history `is_deleted` filter | `6f586d0f4d086abf5a5c035fe4ca07c99ee1d34723b12b871efb2f717cd4e16c` | `ce760b82e31bd56748d8dfddd348df22f8cd9f9fba5af1ce75a16ec658b22bb2` | `test_valuation_chain_preview_delete_and_history` |
| M10: substitute calculated rate | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `6cc9084f18ae23e360ec56446ff3af4dc4c48b6a3212c844ffa081bf3e964664` | `test_valuation_chain_preview_delete_and_history` |
| M10b: raw re-division | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `f20f70d6a3eaa8e188a867b202cd9cb94a8dc316c999a6af16e65fb9a7994b7e` | `test_valuation_chain_preview_delete_and_history` |
| M7a: remove created audit | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `f8bc46fc9397e03c64b4e6153df21b87dd5135f10c38e3b16dd276d9130f89ee` | `test_valuation_chain_preview_delete_and_history` |
| M7b: remove deleted audit | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `c15fbe56688c06767f7d73fb629913ffab66d64bf3e6bac5a489576d056bd58f` | `test_valuation_chain_preview_delete_and_history` |
| M11: suppress supersession back-link | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `e0f6b2551d39b9a255fdebd4c860d48f4ba1be5a73508476483d1da4183a71b3` | `test_valuation_chain_preview_delete_and_history` |
| M12: insert before close | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `3df0489c30c839d2123493a17ff2c03a8c9af941b2870e3bcccb3e8255a6a18e` | chain and race tests |

Probe-only files touched and restored: `app/beyo_manager/services/commands/item_economics/set_item_valuation.py`, `app/beyo_manager/domain/item_economics/configuration.py`, `app/beyo_manager/services/queries/item_economics/get_item_valuation_history.py`, and `app/beyo_manager/services/commands/item_economics/delete_item_valuation.py`.

## Full write perimeter

Checkpoint `a0cebde86102f9787d3ac5120e48350f399b1c39` contains:

- `app/beyo_manager/domain/item_economics/configuration.py`
- `app/beyo_manager/services/commands/item_economics/delete_item_valuation.py`
- `app/tests/integration/services/commands/item_economics/test_valuation_surface.py`
- `app/tests/unit/domain/item_economics/test_configuration.py`
- `app/tests/unit/services/commands/item_economics/test_item_economics_requests.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_5_valuation_surface.md`

Post-checkpoint, this handoff is the only newly written file. No Architecture
Graph mutation was made.

Final committed file hashes:

- `delete_item_valuation.py`: `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1`
- `configuration.py`: `75087586aae405c57117f6417720743102fbc4003336ce2e6e25689800d68bde`
- `test_valuation_surface.py`: `f010b43f2cd36b46351077f049828b3d61472c04e5488d53c6499fd055cc530a`
- `test_configuration.py`: `9ad0b6eafbbbe2579ae8d5b4f174e5a5d73d087badb0a4b753ec7d1aada27483`
- `test_item_economics_requests.py`: `26ed1e6d58feb05eab71fc47dc78f9218a70664088f701eef2c013109d123d6c`
- `master_plan.md`: `8b9a8e109cbb025ac5c5e7d7d14a09ce4c2916caf346c54e8c1efc930c42d075`
- `phase_5_valuation_surface.md`: `70bc9bbb265f30e6ea196584f4eaeb75872686b8b78137f881cc1c3b3df2f852`

## Checkpoint

`CHECKPOINT (not approved): item-cost phase 5 fix r1 — valuation surface evidence and delete predicate`

Commit: `a0cebde86102f9787d3ac5120e48350f399b1c39`
