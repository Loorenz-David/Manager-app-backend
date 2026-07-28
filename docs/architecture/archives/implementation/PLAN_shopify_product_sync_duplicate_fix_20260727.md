# PLAN_shopify_product_sync_duplicate_fix_20260727

## Metadata

- Plan ID: `PLAN_shopify_product_sync_duplicate_fix_20260727`
- Status: `archived`
- Type: **standalone bug fix** — independent of the pre-order delivery
- Related plan: `PLAN_shopify_preorder_product_20260727.md` (rev 8 — the state-machine R-note, **R12**)
- Depends on: nothing
- Owner agent: `codex`
- Created at (UTC): `2026-07-27T00:00:00Z`
- Last updated at (UTC): `2026-07-27T21:00:00Z`

## The bug

`sync_one_product_sync_item` creates a product and then, in a **second** mutation, writes the SKU:

- `_product_sync_orchestrator.py:100-113` — `create_shopify_product` → persist ids →
  `_bulk_update_variant`, and the SKU lives on `inventoryItem.sku` in that *second* call.

So if `productCreate` succeeds but the response is lost — timeout, worker SIGKILL, network drop —
the execution layer retries, the retry's exact-SKU lookup finds **nothing** (the SKU was never
written), and it creates a **second Shopify product**.

This exists in production today. It is not introduced by any pending work, and it is silent: the
operator sees a successful sync and a duplicate product appears in Shopify.

Discovered while planning pre-orders; extracted here because it stands on its own.

## Goal and intent

- Goal: make a product-sync item resumable, so a lost response is reconciled rather than duplicated.
- Non-goals: no pre-order behaviour, no `inventory_mode`, no media, no metafield changes. This is
  a bug fix to the existing path only.

## Two mitigations, both required

1. **Persist before the next call.** `shopify_product_id` is already persisted before the
   metafields call (`:108-113`); extend the same discipline so it is committed **before** the
   variant mutation, and record a `stage` so a retry knows what is already done.

2. **Reconcile by operation tag.** Tag every created product with
   `managerbeyo-sync-<sync_item_id>` and query
   `products(first: 2, query: "tag:managerbeyo-sync-<id>")` **before** the SKU lookup.
   One hit → adopt it as the update path. Two or more → fail `ambiguous_operation_tag`.
   This is what covers the case where the `productCreate` **response itself** was lost.

## Prerequisite — the safety net must already exist

`PLAN_shopify_product_sync_characterisation_net_20260727.md` must be **implemented and green**
before this work starts. It captures the exact GraphQL documents and variables product sync emits
today, in `app/tests/unit/services/tasks/shopify/test_product_sync_characterisation.py`.

If that file does not exist, **stop** — do not write it inline and do not proceed without it. This
plan modifies live production code and the snapshot is the only drift detector.

**If it fails during this work, the change under test is wrong.** Do not edit it to match new
behaviour beyond the two documented deltas below.

## Scope

### Add

| Path | Purpose |
|---|---|
| `app/beyo_manager/domain/shopify/product_sync_stages.py` | `should_run_stage` + ordering — pure |
| `app/migrations/versions/<rev>_add_stage_to_shopify_product_sync_items.py` | one enum + one column |

*(The characterisation test is **not** added here — it is a prerequisite delivered by its own plan.)*

### Modify

| Path | Change |
|---|---|
| `domain/shopify/enums.py` | `ShopifyProductSyncStageEnum` (`queued`, `product_created`, `variant_configured`, `inventory_set`) |
| `models/tables/shopify/shopify_product_sync_item.py` | `stage` column, non-null, `queued` + server_default |
| `services/infra/shopify/product_sync_client.py` | `find_product_by_operation_tag`; include the operation tag on create |
| `services/tasks/shopify/_product_sync_orchestrator.py` | stage machine, persist-before-next-call, tag reconciliation |

## Implementation steps

1. Confirm the characterisation test exists and is green. If not, stop.
2. Add the enum, the `stage` column and the migration (additive, server default, no backfill).
3. Add `find_product_by_operation_tag` returning product id + first variant id + inventory item id;
   two or more hits → raise.
4. In the `queued` stage, run the tag query **before** the exact-SKU lookup. One hit → adopt and
   take the update path. Zero → fall through to the existing SKU/barcode logic, unchanged.
5. Include `managerbeyo-sync-<sync_item.client_id>` in the tags sent on create.
6. Persist `shopify_product_id` and set `stage = product_created`, committing **before** the
   variant call. Then variant ids → `variant_configured`. Then inventory → `inventory_set`.
7. Guard each stage with `should_run_stage` so a retry does only the remaining work.
8. **Leave the inventory step alone** — the additive `sync_inventory_adjustments` ledger path is
   untouched.
9. Preserve the existing exception classification: non-retryable and ambiguity errors → `FAILED`;
   `ShopifyGraphQLRetryableError` **propagates** so the execution layer retries with backoff.
10. Keep the existing explicit `await session.commit()` calls — this runs in the worker via
    `task_db_session()`, **not** inside `maybe_begin`. Do not convert them.

## The two permitted characterisation deltas

- created products carry one extra tag,
- a tag query runs before the SKU lookup.

Nothing else may change. If anything does, stop and report.

## Test contract

`test_product_sync_orchestrator.py` (extend):

- **lost `productCreate` response → the retry's tag query adopts the orphan and creates nothing new** ← the bug
- two products carrying the same operation tag → `ambiguous_operation_tag`, no writes
- two distinct products sharing an exact SKU → `ambiguous_product_match` (unchanged)
- `shopify_product_id` is persisted **before** the variant mutation (assert commit ordering)
- resume from each stage performs only the remaining calls
- multi-location additive inventory still works and still uses the ledger
- retryable errors propagate; non-retryable are captured

## Done signal

```
pytest app/tests/unit/services/tasks/shopify/test_product_sync_characterisation.py -v
pytest app/tests/unit/services/tasks/shopify/test_product_sync_orchestrator.py -v
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
pytest app/tests
```

Run the **full** suite — this is a live path.

## ⚠️ Human review gate

Stop after implementation. State in the summary: the two characterisation deltas and nothing else;
every stage-commit boundary introduced; confirmation the inventory step is byte-for-byte
unchanged; and the added latency from one extra tag query per sync item.

## Risks and mitigations

- Risk: silent behavioural drift in live product sync.
  Mitigation: the characterisation net, the full-suite gate, and the review gate.
- Risk: the extra tag query adds a Shopify call per item.
  Mitigation: accepted — one cheap indexed query is what closes the duplicate hole. Report the
  measured latency.

## Relationship to the pre-order delivery

`PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md` explicitly **accepts** this bug as
pre-existing and out of scope. Doing this ticket first would benefit pre-orders too, but neither
blocks the other.

## Lifecycle transition

- Current state: `implemented`
- Next state: **human review** → `summarized` → `archived`
- Transition owner: David for the human review gate
