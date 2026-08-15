# Phase 8B implementer handoff — r1

Date: 2026-08-15  
Role: implementation-executor  
Checkpoint: `513856d17a3a59cfd448073d095b6c78e8b678df`  
Checkpoint subject: `CHECKPOINT (not approved): item-cost phase 8B implement r1 — inline task prices at task creation`

## Result

Phase 8B is implemented within the governing scope. `FindOrCreateItemInput`
accepts optional `expected_sale_price_minor`, `purchase_cost_minor`, and
`currency`; amounts are non-negative and currency is required iff an amount is
present. `create_task` writes one valuation-chain row after the PRIMARY
`TaskItem` flush and before the existing auto-commit savepoint, refuses a
matched item only when an active current valuation exists, and records the
existing valuation audit event. Currency-only input is accepted and ignored.
The task router body and the three `PUT /api/v1/tasks` README rows carry the
new vocabulary, while legacy money keys still terminate at `ITEM_MONEY_MOVED`.

The matched-item branch is covered for never-valued and deleted-only histories:
the former creates v1 and the latter creates the next chain version. A current
valuation refusal rolls back the whole request, including a changed designer
sent in the lookup payload.

## Verification

- Focused phase plus retained bridge scope: **66 passed**.
- Full foreground non-E2E suite from `app/`: **2183 passed / 23 established
  failures / 1 deselected**, **2207 collected**. The 24 retained bridge nodes
  plus 21 phase nodes reconcile the collection increase from 2162 to 2207;
  the sorted failure IDs are byte-identical to the established 23-item
  baseline.
- Ruff: clean on every touched Python file.
- Database: configured development database reports
  `c1d2e3f4a5b6 (head)`. No migration was created or run.
- No disposable database was created. The four exact `phase8b` workspaces
  left by the intentionally inverted-predicate mutant were removed by the
  owning test teardown helper after the probe; no phase-8B fixture residue was
  retained.

## Mutation ledger

The expected-red node IDs were declared before the probes. Every mutant was
run in isolation, observed to redden its named arbiter, and reverted. The
restored hash is the final shipped hash.

| Mutant | Expected red ID(s) | Mutant SHA-256 | Observed red | Restored SHA-256 |
|---|---|---|---|---|
| Delete the valuation write at its definition site | `test_c1_inline_birth_writes_valuation_and_handles_exact_auto_statuses[C1-row-1-full-trio-purchase-term-commits-True-True-item_values0-committed]` | `create_task.py` `e19300d27bec38bd6b5110c1df2b2253411f6724ad4e5ec90e8dcbfdc281eefa` | 1 failure: valuation count was 0 instead of 1 | `create_task.py` `e9c2ccc1bfda4c133149195e530977860eaefba31508b30e492a42bd6e41d547` |
| Invert the current-valuation refusal predicate | `test_c4_row_1_current_valuation_refusal_rolls_back_item_mutation_and_task`; `test_c4_row_2_never_valued_existing_item_accepts_inline_price`; `test_c4_row_3_deleted_only_existing_item_accepts_and_grows_chain` | `create_task.py` `f0776418c7cdc77faf76907bc47545ce70d244106e35d6e88ba9f09940cb2f95` | All 3 named C4 rows reddened | `create_task.py` `e9c2ccc1bfda4c133149195e530977860eaefba31508b30e492a42bd6e41d547` |
| Move `require_currency_for_amounts` above `reject_legacy_money` | `test_c3_legacy_money_rejection_precedes_inline_currency_validation[C3-row-2-legacy-plus-amount-without-currency-payload1-ITEM_MONEY_MOVED]` | `requests/__init__.py` `f4670bdeaab4a0aad48e238c4b6e479c4e1def9078ffc300d4c5e4d1712c9d24` | 1 failure: `item.currency` won instead of `ITEM_MONEY_MOVED` | `requests/__init__.py` `2bc2b7bb018357d2e437096aac8e81263adddffae1e7a1c9c09fbe564b1e9da4` |
| Delete `reject_legacy_money` | `test_bridge_is_reject_iff_present_and_nonnull[create-task-nested-item-item_value_minor-present-nonnull]`; `test_bridge_is_reject_iff_present_and_nonnull[create-task-nested-item-item_cost_minor-present-nonnull]`; `test_bridge_is_reject_iff_present_and_nonnull[create-task-nested-item-item_currency-present-nonnull]` | `requests/__init__.py` `dbfe1548b9ea68212532b470131bcbd0f61cd9fb05b0a5c8c6913f02695b5142` | All 3 shipped retention nodes reddened | `requests/__init__.py` `2bc2b7bb018357d2e437096aac8e81263adddffae1e7a1c9c09fbe564b1e9da4` |
| Delete the three `_TaskItemInputBody` trio fields | `test_c6_create_task_endpoint_preserves_trio_into_domain_validator` | `tasks.py` `aafc1f53946b8076fd9a00297343a2c09aa16aa6660021b2da696410313fbd1a` | 1 failure: endpoint payload retained only `article_number` | `tasks.py` `6a3654dd7aa602bc5f7435960f9bdce06e82d521c585e418a54962ef67061560` |

Mutation deferrals: **zero**.

## Architecture Graph

Read-only orientation was performed before the delta. The verified pre-change
state was 173 nodes / 256 edges, revision
`45b721965a174fdf2e506bdb847ea26a496f803c7eb182fb6d6f0f598f3815a4`, with no
stale or pending items. One additive batch then recorded:

- new command node `command-task-create`;
- `writes_to` → `table-item-valuation`;
- `writes_to` → `table-task`;
- `writes_to` → `table-task-item`;
- `reads_from` → `table-item`.

Post-delta state is 174 nodes / 260 edges, revision
`53fdbc785621c38a295ae90ac09c67339ca654563d0b2f6480d034fc11868fd1`, zero
stale, five pending inferred items, permission mode `review`. No promotion,
rejection, maintenance edit, or other human-gated graph action was performed.

## Write perimeter

Production:

- `app/beyo_manager/services/commands/tasks/requests/__init__.py`
- `app/beyo_manager/services/commands/tasks/create_task.py`
- `app/beyo_manager/routers/api_v1/tasks.py` (`_TaskItemInputBody` only)
- `app/beyo_manager/routers/README.md` (three rows under `PUT /api/v1/tasks`)

Tests:

- `app/tests/integration/services/commands/item_economics/test_phase8b_inline_task_prices.py`
- `app/tests/unit/test_phase6_api_bridge.py` (retention parametrization only)

Docs/state:

- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_8b_inline_task_prices.md`
- this handoff
- `.archgraph/architecture.yml` (one additive batch)

No migration, item-economics production file, new read surface, or other file
was changed. The optional zero-price row was **not delegated**: the shipped
`ge=0` contract is covered by the negative-value rows, while C1 uses positive
amounts only. No owner decisions are required.

## Final SHA-256

The handoff is deposited after the checkpoint, so its own self-hash is omitted
from this table. All other touched files have these final hashes:

| File | SHA-256 |
|---|---|
| `.archgraph/architecture.yml` | `53fdbc785621c38a295ae90ac09c67339ca654563d0b2f6480d034fc11868fd1` |
| `app/beyo_manager/routers/README.md` | `291aae658bf026c9ad1f68e031c07e367c13b5fa36bd90e95b51efab6150fdec` |
| `app/beyo_manager/routers/api_v1/tasks.py` | `6a3654dd7aa602bc5f7435960f9bdce06e82d521c585e418a54962ef67061560` |
| `app/beyo_manager/services/commands/tasks/create_task.py` | `e9c2ccc1bfda4c133149195e530977860eaefba31508b30e492a42bd6e41d547` |
| `app/beyo_manager/services/commands/tasks/requests/__init__.py` | `2bc2b7bb018357d2e437096aac8e81263adddffae1e7a1c9c09fbe564b1e9da4` |
| `app/tests/unit/test_phase6_api_bridge.py` | `68a34b62f37339434acfecbf1fd13ecd1130d8700669d810fd3799572b7e4a38` |
| `app/tests/integration/services/commands/item_economics/test_phase8b_inline_task_prices.py` | `f23d7724b8e8f92fd0cbd24c65064be62e524caabfef805661fcd4b41cfe9855` |
| `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md` | `af80abeb3e79e61ad1b850046d416eff6b6845bd1a5b5c642b1897d2660bfee2` |
| `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_8b_inline_task_prices.md` | `5a3bc45d943fec75ea33ba4befd2395c2c21047ceb4ff6363eb57450cdd8bb9b` |

⚠ OWNER DECISIONS REQUIRED (0)
