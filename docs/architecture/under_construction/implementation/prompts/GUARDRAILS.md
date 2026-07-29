# Shopify Pre-Order — Standing Guardrails

Every prompt in this folder references this file. Read it once per session, before writing code.

These are the rules a code model most reliably "helpfully" violates. Each exists because breaking
it causes silent data loss, a security regression, or an error that looks like success.

## Absolute rules

1. **Inventory behavior and sync origin are separate contracts.**
   `inventory_mode` and `sync_origin` must never appear in an HTTP request schema. Every supplied
   location quantity is authoritative and absolute, for both `/products/process` and pre-orders.
   Origin is persisted internally at enqueue time and controls only audit history, socket events,
   and workflow completion. Never infer origin from inventory fields or behavior.

2. **Never send `ignoreCompareQuantity` or `compareQuantity`.**
   Both are deprecated in API `2026-01` and removed in `2026-04`. Use `changeFromQuantity: null`
   to skip the compare check. The document must be valid on `2026-01` *and* unchanged on `2026-04`.

3. **Never derive price from `custom.quantity`.**
   No multiplication, no division, in either direction. The variant price is caller-supplied
   business data written exactly as supplied. (`5200 × 6 = 31200` in the merchant data is a
   coincidence of magnitude, not a rule.)

4. **There is exactly one caller-supplied quantity, and it feeds two places.**

   *(Reversed 2026-07-27. Revs 4–9 required `custom.quantity` and inventory to be **independent**,
   on the evidence that the merchant's live products carry `custom.quantity = "6"` alongside
   `available = 1`. That rule is withdrawn by explicit decision.)*

   | Written to | Value |
   |---|---|
   | Shopify stock, per location | that location's `inventory[].quantity` |
   | the `custom.quantity` metafield | the **sum** across all locations |

   Both derive from `inventory[].quantity` via
   `domain/shopify/preorder_policy.build_preorder_quantity_metafield`.
   **`metafields.quantity` is rejected at the request boundary** — a caller-supplied value would be
   a second source of truth. Rejecting is louder than overwriting.

   **There is no quantity constant** — revs 4–8 wrongly modelled the target as a fixed `1`; it is
   caller input per location, written as an **absolute set** that overwrites existing stock.
   Record `before_available` per location: with an arbitrary overwrite quantity, that audit value
   is the only record of what was there before.

5. **Never substitute an inventory location. Fail instead.**
   Not from array order, not the first active location, not a primary location. If the selected
   location is gone, inactive, or a fulfillment-service location, fail and keep every Shopify ID
   already created. Silently relocating stock is an error that looks like success.

6. **Never hard-code merchant-specific literals** in `domain/` or `services/infra/`:
   the location GID `99221471562`, the metafield definition GID `241114906954`, the SKU
   `CustomTC3`, or the prices `31200.00` / `5200.00`. Tests, fixtures and plan evidence only.

7. **Never call `session.commit()` or `session.rollback()` inside `maybe_begin`.**
   See `backend/architecture/06_commands_local.md`. Subordinate commands collect `pending_events`
   and return them; only the owning command dispatches.
   *(Worker code running under `task_db_session()` is **not** inside `maybe_begin` — its explicit
   commits are correct. Do not convert them.)*

8. **Never call Shopify inside the `create_task` transaction.**
   Task creation writes local rows only. All Shopify I/O happens in the worker, after commit.
   **Do not use `event_bus` as the trigger** — it dispatches post-commit and swallows handler
   exceptions, so a crash there loses the intent permanently. The `ExecutionTask` row is the outbox.

9. **Never auto-delete a Shopify product, variant or media object** on partial failure.
   Persist the partial state with its IDs and fail. Cleanup is a future explicit action.

10. **Money stays a decimal string end to end.** No `float`. No `Decimal` in JSONB.

## Behavioural invariants to preserve

- **Ambiguous exact SKU → `ambiguous_product_match`.** Two distinct Shopify product IDs sharing
  one SKU is a *confirmed production condition* in this merchant's store, not a hypothetical.
  Never auto-select by order, age, price, stock, status or timestamp. Multiple *variants* of the
  **same** product ID remain a single valid match.
- **Product status is `UNLISTED`** — not `ACTIVE`, not `DRAFT`.
- **Till readiness is the requested absolute `available` quantity**, never an `on_hand` write.
- **Persist Shopify IDs before the next stage's first network call.**

## Images (corrected — read this if you have older context)

The S3 bucket is **public**. Verified by anonymous fetch.

- **No presigning.** No TTL, no per-attempt re-minting, no expiry handling, and **no
  `stagedUploadsCreate` fallback**. Compose a plain public URL from the storage key via
  `StorageClient.public_url(key)`.
- Shopify **pulls** the image — nothing is uploaded to it. `CreateMediaInput.originalSource` is a
  URL Shopify's servers fetch once, copying the bytes into their CDN.
- Pass media as the separate `media: [CreateMediaInput!]` argument on `productCreate` /
  `productUpdate`. **Not** the deprecated `productCreateMedia`.
- **WebP is accepted** (as are PNG, JPEG, GIF, HEIC, SVG, TIFF, BMP, PSD). Limits are **20 MB**
  and **25 MP / 5000×5000** — validate locally at command time from `width_px`, `height_px` and
  `file_size_bytes` on `images`.
- Media processing is **asynchronous**. Record the returned `MediaStatus`; **do not poll for
  `READY`**.
- Still compose the URL **at worker time** and never persist it, so a bucket or CDN change cannot
  strand queued rows.
- When no image is supplied, **omit the `media` key entirely** — do not send `null`.

## Regression rule for the shared pipeline

Pre-order rides the shared product-sync pipeline. Any supplied inventory quantity must use
`inventorySetQuantities` with the sync-item idempotency key. `inventoryAdjustQuantities` and the
historical adjustment ledger are not runtime paths. The ledger table is retained read-only for
audit history.

Where a characterisation test exists, that is the arbiter: **if it fails, your change is wrong —
do not update it to match new behaviour without explicit human approval.**

## Scope rule

The existing product sync already does most of this: SKU resolve-or-create, ambiguous-SKU
failure, variant price, `UNLISTED`, metafields in the `custom` namespace, absolute inventory at
chosen locations, **location ownership validation**, and **per-sync replay safety via Shopify's
idempotent mutation contract**.

**If you find yourself reimplementing any of that, stop — you have gone out of scope.**

## Definition of done for every plan

- The plan's named test files exist and pass.
- The pre-existing Shopify suite is green: `pytest app/tests -k shopify`.
- No file outside the plan's "Files" section was modified.
