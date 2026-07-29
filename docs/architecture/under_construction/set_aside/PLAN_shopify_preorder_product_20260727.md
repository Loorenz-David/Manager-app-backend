# PLAN_shopify_preorder_product_20260727

> **Revision 10 — superseding inventory/origin decision (2026-07-28).** All Shopify product-sync
> producers now submit authoritative absolute location quantities through one shared worker and
> `inventorySetQuantities`. `inventory_mode` remains only as a one-release compatibility column
> and is never used to classify a workflow or select a mutation. `sync_origin` plus
> `source_entity_type`/`source_entity_id` identify standard syncs and pre-order tasks explicitly
> from enqueue time. The additive ledger is historical and read-only. Any older section below
> claiming `/products/process` is additive, that `inventory_mode` identifies a pre-order, or that
> `inventoryAdjustQuantities` remains a runtime path is superseded by this revision and by
> `SUMMARY_shopify_absolute_inventory_and_sync_origins_20260728.md`.
>
> **Revision 9 — the inventory quantity is caller-supplied, not a hard-coded `1`.** Confirmed with the merchant: the frontend sends a **quantity per selected location**, exactly as the existing `inventory_adjustments` contract does, with the UI defaulting that field to `1`. The write remains an **absolute set** (overwrite), not additive. This deletes `PREORDER_INVENTORY_QUANTITY = 1` everywhere and generalises the target to caller input — while **preserving** the rule that `custom.quantity` (a product metafield) never influences stock. Those are now two distinct caller inputs and must not be conflated. Phase 0 gates 1, 3 and 4 are also resolved below; **gate 2 remains open**.
>
> **Revision 8 — scope cut to a minimum delivery; the image path collapsed.** Two findings: (a) the S3 bucket is **public**, so no presigning, no TTL, no `stagedUploadsCreate` fallback — `R3` is corrected and was previously **wrong**; (b) an overlap audit found that after rev 7's convergence, most of the remaining plan is **optional hardening rather than pre-order requirements**. The delivery is now **one minimum plan** (`PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`) plus **two standalone improvement tickets** that stand on their own merits. Everything else is retained below as a **documented backlog**, not a critical path. See **R13**.
>
> **Revision 7 — converged onto the existing product-sync pipeline instead of building a parallel one.** A review of the overlap found ~70% of rev 6 was reimplementing `/products/process`. Pre-order is now a **second thin entry point onto a shared, staged product-writing core**, reusing `ShopifyProductSyncItem`, `TaskType.SHOPIFY_PROCESS_PRODUCTS` and the existing worker handler. This deletes the `shopify_preorder_operations` table and its migration, the `shppre` prefix, the new task type and its payload, the `QUEUE_MAP`/`HANDLER_MAP`/timeout entries, one enum and the results module — and fixes the lost-`productCreate`-response duplicate bug for **product sync as well**. The destructive absolute-inventory-set mode is deliberately **not** reachable from the `/products/process` HTTP route. See R12.
>
> **Revision 6 — the inventory location is now selected by the seller in the request, not configured on the integration.** The seller picks the Shopify location from the existing locations endpoint; the backend validates the GID locally at command time, commits it atomically with the task as durable intent, re-validates it against Shopify at worker time, and **freezes it for the life of the operation**. Changing the business's location tomorrow affects only new pre-orders. This removes an entire configuration layer: the `zettle_inventory_location_id` column, its admin route and rollout prerequisite, `SHOPIFY_PREORDER_REQUIRE_VERIFIED_ZETTLE_LOCATION`, the three-way resolution hierarchy, the `acknowledge_not_zettle_synced` override contract, the `PARTIALLY_PROVISIONED` state, and the `INVENTORY_LOCATION_RESOLVED` stage. See R7.
>
> **Revision 5 — corrected against live merchant-store evidence (SKU `CustomTC3`), not documentation alone.** Seven corrections: product status is **`UNLISTED`, not `ACTIVE`**; **duplicate exact SKUs already exist in production** and must fail ambiguously; the candidate Zettle location is **`gid://shopify/Location/99221471562` (Västberga Warehouse)**; till-readiness is **`available = 1`**, not `on_hand = 1`; the real `custom.quantity` metafield is **`single_line_text_field`**, not `number_integer`; the quantity metafield stays **completely independent** of inventory; and the variant **price is never derived** from it. See R11 for the evidence and R4 for the status change.
>
> History: rev 1 planned the full pre-order → Shopify **order** workflow (customer upsert, draft order, payment-pending completion); that scope was withdrawn because staff complete the sale in **Zettle**. Rev 2 reduced it to product provisioning. Rev 3 corrected the `@idempotent` finding, made the Zettle-synchronized inventory location execution-critical, and adopted the forward-compatible compare-and-swap contract. Rev 4 added caller-supplied product **metafields** written in the same mutation as the product and removed the `quantity` request field. The product-only architecture, durability model, worker stages, retry strategy and contracts from rev 2–4 are preserved unchanged.

## Metadata

- Plan ID: `PLAN_shopify_preorder_product_20260727`
- Status: `under_construction` — **stays under construction until every Phase 0 gate has a recorded outcome in the Review log**
- Owner agent: `claude-opus-5`
- Created at (UTC): `2026-07-27T00:00:00Z`
- Last updated at (UTC): `2026-07-27T00:00:00Z`
- Related issue/ticket: `<id_or_link>`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_shopify_preorder_product_20260727.md`

## Goal and intent

- Goal: when a `PRE_ORDER` task is created in ManagerBeyo, asynchronously create-or-resolve the corresponding Shopify product on one explicitly targeted shop, set its primary variant's SKU and price, attach the supplied product image, and set the inventory quantity to `1` **at the Shopify location that the merchant's Zettle integration synchronizes** — durably, idempotently and resumably, with every Shopify identifier persisted.
- Business/user intent: staff complete the actual sale in **Zettle**, which mirrors the Shopify product library. The product must already exist in Shopify with the correct price and one unit of stock **visible at the till** before staff reach it. A successful inventory write to a location Zettle does not read is not a successful pre-order — the operation must say so rather than report ordinary success.
- Non-goals:
  - **No Shopify order, draft order, checkout or payment of any kind.**
  - **No Shopify customer creation or lookup.** No customer PII reaches Shopify.
  - No multi-shop fan-out — one pre-order targets exactly one shop integration.
  - No storefront publication and no sales-channel publish/unpublish calls (see R4).
  - No automatic deletion of Shopify products on partial failure.
  - No change to `/products/process`.
  - **No dual-write** of inventory to more than one location.

## Scope

### In scope

- A **required `inventory_location_id`** on the pre-order request, seller-selected from the existing locations endpoint, validated locally at command time and against Shopify at worker time, and frozen for the life of the operation (R7). **No new column on `shopify_shop_integrations`, no admin route, no rollout prerequisite.**
- Extension of `ShopifyProductSyncItem` with `mode`, `stage` and the pre-order columns, plus a partial unique index and a CHECK constraint (R12). **No new table, no new task type, no new worker registration.**
- Restructuring `_product_sync_orchestrator.py` into the shared staged core used by both modes — which also fixes product sync's latent duplicate-product bug.
- New command + in-session helper callable from `create_task`, plus an optional `shopify_preorder` section on `CreateTaskRequest` gated to `TaskTypeEnum.PRE_ORDER` and roles `admin` / `manager` / `seller`.
- New Shopify infra capability: product media **and caller-supplied metafields** on create and update, product reconciliation by operation tag, primary-location resolution, absolute inventory set with `@idempotent` and the forward-compatible `changeFromQuantity` contract.
- Worker-time resolution of metafield definitions addressed by GID, reusing the existing `metafield_definition_client` unchanged.
- Resumable five-stage worker orchestrator with explicit location resolution.
- Worker-time composition of the image URL from the **public** S3 bucket (R3).
- `ShopifyIntegrationEventTypeEnum.PREORDER` + additive enum migration.
- Socket.IO terminal event `shopify.preorder.processed` carrying `zettle_ready`.
- Preservation of Shopify `userErrors` field paths and safe messages (backwards-compatible extension of `raise_for_graphql_user_errors`).
- Unit / service / worker / infra-client tests plus a manual dev-store checklist.
- Architecture doc update and a frontend handoff.

### Out of scope

- Admin route to list or retry pre-order operations (follow-up plan).
- ~~Repairing the lost-response duplicate exposure in the generic product-sync orchestrator~~ — **now in scope** as of rev 7. Converging on one orchestrator means the tag-reconciliation fix lands for product sync too; that was a decisive argument for converging (R12).
- Any Shopify↔Zettle configuration on the merchant side.
- Webhook-driven reconciliation of the product.
- Multi-variant / product-options products — the pre-order product always has exactly one variant.

### Assumptions

- Shopify Admin GraphQL API version `2026-01` (`config.py:117`). Every contract below was verified against that version's reference.
- Money is a decimal **string** end to end. No `float`, no `Decimal` in JSONB.
- One pre-order per ManagerBeyo task per shop; the task `client_id` is the default operation idempotency key.
- The inventory quantity is **caller-supplied per selected location** (rev 9), mirroring the existing `inventory_adjustments` contract, with the UI defaulting the field to `1`. The write is an **absolute set** — it overwrites whatever stock is at that location. It is **never** derived from the `custom.quantity` metafield (R10); those are two distinct caller inputs.
- The shop's default currency is used.

---

## Decisions of record

| Question | Decision | Consequence |
|---|---|---|
| **Pipeline** | **Shared core, two entry points** — *decided in rev 7* | Pre-order and product sync run through one staged orchestrator and one table (`ShopifyProductSyncItem` + nullable pre-order columns). No new table, no new task type, no parallel worker path (R12). |
| **Absolute inventory set exposure** | **Not caller-settable.** Only the pre-order command can select it | `/products/process` keeps additive-only semantics; a bad HTTP caller cannot wipe stock (R12) |
| Order creation | **None.** Product provisioning only | Customer / draft-order / order stages do not exist |
| Inventory semantics | **Set to exactly 1** (absolute) | `inventorySetQuantities`, not the additive `inventoryAdjustQuantities`. The `shopify_inventory_adjustments` ledger is **not** reused (R5). |
| Existing SKU | **Reuse the product, overwrite the price** — but only after the match is proven unique | Duplicate exact SKUs are a **confirmed production condition** (R11). Ambiguity must be resolved before any overwrite occurs. |
| **Duplicate exact SKU** | **Fail `ambiguous_product_match`** — *evidence-confirmed in rev 5* | The merchant store already holds two distinct products on SKU `CustomTC3`. The worker never auto-selects by order, age, price, stock, status or timestamp (R11). |
| How Zettle sees the product | **Zettle imports the whole Shopify library** | No `publishablePublish`; no publication scopes; **no merchant reauthorization** |
| **Product visibility** | **`UNLISTED`** — *corrected in rev 5* | Every product in the merchant's live Shopify/Zettle workflow is `UNLISTED`. Shopify defines it as *"active but you need a direct link to view it… doesn't show up in search, collections, or product recommendations"* — which satisfies both requirements at once (R4). Rev 4's `ACTIVE` and its unsupported "ACTIVE is required for Zettle visibility" claim are removed. |
| **Till readiness** | **`available = 1`**, never `on_hand = 1` — *clarified in rev 5* | The store proves `on_hand = 1, committed = 1 → available = 0` is **not** sellable (R11). `inventorySetQuantities` keeps `name: "available"`. |
| **Variant price** | **Caller-supplied business data, written exactly as given** | Never derived from `custom.quantity` — no multiplication, no division (R11) |
| **Inventory location** | **Seller-selected per pre-order, then frozen for the life of the operation** — *revised in rev 6* | `inventory_location_id` is a required field of the normal request. The backend validates it locally at command time, commits it atomically with the task, re-validates it against Shopify at worker time, and never substitutes another location. No integration-level configuration, no resolution hierarchy, no override contract (R7). |
| **`@idempotent`** | **Adopt now** — *corrected in rev 3* | Supported and optional in `2026-01`, mandatory from `2026-04`. Deterministic key derived from the logical operation. |
| **Compare-and-swap** | **Use `changeFromQuantity: null`, not `ignoreCompareQuantity: true`** — *new in rev 3* | The forward-compatible shape is already writable on `2026-01` and survives the `2026-04` removals unchanged (R5) |
| **Product metafields** | **Caller-supplied, written in the same mutation as the product** — *new in rev 4* | `ProductCreateInput.metafields` / `ProductUpdateInput.metafields` — no separate `metafieldsSet` round trip and no separate failure stage (R10) |
| **`custom.quantity` metafield** | **Product data. Never touches inventory** — *rev 4, still holds* | One caller-supplied metafield among others, describing item composition. The inventory target is a **separate** caller input and is never derived from it (R10) |
| **Inventory quantity** | **Caller-supplied per location, absolute set** — *corrected in rev 9* | The frontend sends `{location_id, quantity}` per chosen location (UI default `1`), exactly like `inventory_adjustments`. `inventorySetQuantities` **overwrites** the location's stock rather than adding to it |
| **Image source** | **AWS S3, public bucket** — *corrected in rev 8* | A plain public URL composed from the storage key at worker time. No presigning, no TTL, no staged-upload fallback. WebP accepted; 20 MB / 25 MP limits validated locally (R3) |
| **Delivery scope** | **Minimum first, hardening as backlog** — *decided in rev 8* | One minimum plan + two standalone improvement tickets. The rest of this document is a backlog, not a critical path (R13) |
| Trigger surface | `TaskTypeEnum.PRE_ORDER`; roles `admin`, `manager`, `seller` | Enforced in `create_task` before any row is written |
| Scopes | **Unchanged** | `write_products`, `read_products`, `read_locations`, `write_inventory` are already granted (`config.py:108-113`) |

---

## Research findings

### R1 — Reuse map (what already exists)

| Concern | Existing implementation | Decision |
|---|---|---|
| GraphQL transport, retryable/non-retryable classification, throttling | `services/infra/shopify/graphql_client.py` | Reuse; **extend** `raise_for_graphql_user_errors` (R6) |
| Exact-SKU variant lookup | `product_sync_client.py:find_product_variant_by_identity` + `domain/shopify/product_sync_identity.py:select_exact_variant_match` | Reuse directly, called with `sku=…, barcode=None` |
| Product create / update / variant bulk update | `product_sync_client.py:create_shopify_product`, `update_shopify_product`, `_bulk_update_variant` | **Do not call as-is** — neither passes `media`, and both apply generic product-sync defaults. Add a pre-order client reusing the same mutation documents (promote `BULK_UPDATE_VARIANT_MUTATION` to a shared constant rather than copying it). |
| Location listing + ownership validation | `inventory_client.py:fetch_shop_locations`; ownership check at `_inventory_sync.py:53-70` | Reuse `fetch_shop_locations`; **extend** the query per R7 |
| Inventory item state (tracked / level exists / current available) | `inventory_client.py:resolve_inventory_item_state` | Reuse — it already returns `available`, which becomes the audited `before_available` (R9) |
| Inventory tracking + level activation | `inventory_client.py:enable_inventory_tracking`, `activate_inventory_at_location` | Reuse verbatim — both are prerequisites for any quantity write |
| Additive inventory + durable ledger | `adjust_inventory_quantities`, `_inventory_sync.py`, `shopify_inventory_adjustments` | **Not reused, not modified** — see R5 |
| Scope checking | `domain/shopify/scopes.py:has_all_required_scopes` | Reuse |
| Execution task creation / routing / retry | `task_factory.create_instant_task`, `task_router.py`, `worker_base.py` | Reuse; one entry added to each map |
| Integration audit events | `services/commands/shopify/_events.py:create_shopify_integration_event` | Reuse |
| Worker → client realtime | `sockets/worker_emitter.py:emit_to_workspace_room` | Reuse |
| Transaction composition | `services/commands/utils/transaction.py:maybe_begin` (`06_commands_local.md`) | Reuse — `create_task` already opens it at `create_task.py:50` |
| Public object URLs | **Nothing exists** — `StorageClient` exposes only presigned GET/PUT | **Add** `public_url(key)` + `STORAGE_PUBLIC_BASE_URL`, composed at worker time (R3) |

### R2 — Durable-intent architecture: the outbox already exists

`create_instant_task` inserts the `ExecutionTask` + `ExecutionPayload` rows using the **caller's** session inside the caller's open transaction (`task_factory.py:25-42`); nothing touches Redis there. The separate `task_router` process only ever reads **committed** `OPEN` rows and pushes them to `queue:shopify` (`task_router.py:113-138`); it is woken by `LISTEN task_open` but has an unconditional `FALLBACK_POLL_SECONDS = 30` timeout, so delivery never depends on the notification arriving.

| Required guarantee | How it is met |
|---|---|
| Task not rolled back because Shopify is unavailable | No Shopify network call happens inside the transaction — only local rows are written |
| Shopify job not dispatched before the task transaction commits | The router reads committed rows only |
| A crash between task creation and dispatch cannot lose the intent | The operation row **and** the `ExecutionTask` row commit atomically with the `Task` row; a crash before routing leaves an `OPEN` row the router picks up next poll |
| Replaying task-created cannot duplicate Shopify resources | `UNIQUE (shop_integration_id, idempotency_key)` makes the operation a singleton; the stage machine resumes rather than restarts |

**`event_bus` must NOT be the durable trigger.** `services/infra/events/event_bus.py:22-33` dispatches in-process **after** commit and swallows every handler exception, so a crash or handler failure between commit and dispatch would permanently lose the pre-order intent. The event bus stays reserved for realtime fan-out exactly as `create_task.py:344-365` uses it today.

### R3 — Image URLs — **CORRECTED in rev 8: the bucket is public**

**Rev 7 asserted "There is no permanently public image URL." That was wrong.** The claim was
inferred from the code — `StorageClient` (`services/infra/storage/base.py`) exposes only
presigned GET/PUT, `config.py` has no public-base or CDN setting, and every image read goes
through `generate_presigned_get_url` — but the *bucket policy* was never checked. It is public.

Verified directly: an object was fetched anonymously at
`https://<bucket>.s3.<region>.amazonaws.com/images/ws_…/case_conversation_message/ccm_…/<uuid>.webp`.

Corrected facts:

- `confirm_upload.py:140` stores the **S3 storage key** in `images.image_url` for uploaded images
  (provider `S3`) — so the key still needs composing into a URL.
- `create_from_url.py:32-34,60` stores a real absolute `http(s)` URL for externally-sourced
  images (provider `EXTERNAL`) — usable verbatim.
- **The application has no code path that emits an unsigned URL.** The bucket is public, but
  nothing composes `https://{bucket}.s3.{region}.amazonaws.com/{key}`. That is the actual gap:
  a `public_url(key)` method on `StorageClient` plus a `STORAGE_PUBLIC_BASE_URL` setting so a
  CDN can be slotted in front later. Roughly ten lines.

Consequences — **substantially simpler than rev 7**:

- **No presigning, no TTL, no per-attempt re-minting, no expiry-during-backoff risk.**
- **The `stagedUploadsCreate` fallback is dropped entirely** from the contingency list.
- The Phase 0 gate on "can Shopify fetch the URL" drops from a real risk with an expensive
  fallback to a formality.
- The request still accepts `image_id` (preferred) or `image_url`, and
  `normalized_payload_json` still stores only the **reference**, never a resolved URL — the URL
  is still composed at worker time so that changing the bucket or introducing a CDN does not
  strand pre-orders already queued. That property is cheap and worth keeping.

**Shopify pulls the image; nothing is uploaded to it.** `CreateMediaInput` (verified, `2026-01`):
`originalSource: String!` — *"an external URL or a staged upload URL"* — plus
`mediaContentType: MediaContentType!` (`IMAGE`) and optional `alt`. Shopify's servers GET the URL
and copy the bytes into their own CDN, once, at creation time.

**Format and limits** (verified):
- **WebP is accepted** — as are PNG, JPEG, GIF, HEIC, SVG, TIFF, BMP and PSD. The pipeline stores
  `.webp`, so this was load-bearing.
- **Max 20 MB** and **max 25 megapixels / 5000×5000 px**. The `images` table already stores
  `width_px`, `height_px` and `file_size_bytes`, so this is a cheap **local** check at command
  time — a clear validation error beats a `userErrors` failure after the product already exists.
- **Media processing is asynchronous.** `MediaStatus` is `UPLOADED` → `PROCESSING` → `READY`
  (or `FAILED`). Record the status returned by the mutation; **do not poll for `READY`** — the
  product existing at the till does not depend on transcoding being finished.

**Unrelated security observation, recorded because it surfaced here:** the public object fetched
during verification was a `case_conversation_message` image — customer conversation content,
world-readable to anyone holding the URL. Keys are UUIDs, so this is an unlisted-link security
model rather than an open directory, and the bucket name suggests a dev environment. Worth
confirming separately that production uses the same policy deliberately and that `s3:ListBucket`
is **not** public. This feature neither depends on that property nor makes it worse.

### R4 — Product visibility, verified for `2026-01`

- `productCreate(product: ProductCreateInput!, media: [CreateMediaInput!])` — the separate `media` argument is the current, non-deprecated media path (the third `input: ProductInput` argument is deprecated). Creates exactly one initial variant. **"Products are created in unpublished state by default."**
- `productUpdate(product: ProductUpdateInput, media: [CreateMediaInput!])` — **also accepts `media`**, and is the documented way to add media to an existing product. Nothing here uses the deprecated `productCreateMedia`.
- No publication call is part of this workflow.

**Product status is `UNLISTED` (corrected in rev 5).**

Rev 4 specified `status: ACTIVE` on the reasoning that a `DRAFT` product is invisible to sales channels. That reasoning was never evidence-backed for Zettle specifically, and the merchant store contradicts the conclusion: **every product in the live Shopify/Zettle workflow — including both `CustomTC3` products — has `status: UNLISTED`** (R11). The claim *"ACTIVE is required for Zettle visibility"* is **withdrawn**; nothing verified supports it.

`UNLISTED` is a real, settable `ProductStatus` value in `2026-01`, documented as: *"The product is active but you need a direct link to view it. The product doesn't show up in search, collections, or product recommendations. It will be returned in Storefront API and Liquid only when referenced individually by handle, id, or metafield reference."* It is available from API version `2025-10` upward (older versions translate it to `active` and cannot change a product out of it), and it appears on both `ProductCreateInput` and `ProductUpdateInput`.

That semantic is a better fit than rev 4's "ACTIVE + rely on non-publication" construction: it is *active* — so sales channels and apps can see the product — while being structurally absent from storefront search, collections and recommendations. It satisfies both requirements in one field rather than depending on the absence of an `autoPublish` publication.

- Residual risk is now smaller but not zero: `UNLISTED` products are still returned by the Storefront API when referenced directly by handle or id. **Phase 0 gates 1–2** verify empirically that a newly created `UNLISTED` product (a) is imported into Zettle and (b) does not surface on the Online Store.
- Contingency, unchanged and still unbuilt: if gate 2 fails, `publishableUnpublish` + `read_publications`/`write_publications` + merchant reauthorization — a scope change to be approved. **Do not add publication scopes or publish/unpublish mutations unless that gate fails.**

### R5 — Absolute inventory set: verified contract, `@idempotent`, and the 2026-04 migration path

**Correction of record.** Rev 2 of this plan (and the agent's stored reference memory) claimed *"`@idempotent` does not exist in 2026-01 and rejects the whole document."* **That is wrong.** Verified against shopify.dev:

- `@idempotent` **is supported in `2026-01` as an optional idempotency mechanism** for `inventorySetQuantities` and the sibling inventory mutations.
- It becomes **mandatory from `2026-04`**.
- Syntax — the directive is placed immediately after the mutation field and its arguments:

```graphql
mutation PreorderInventorySet($input: InventorySetQuantitiesInput!, $idempotencyKey: String!) {
  inventorySetQuantities(input: $input) @idempotent(key: $idempotencyKey) {
    inventoryAdjustmentGroup {
      createdAt
      reason
      referenceDocumentUri
      changes { name delta quantityAfterChange }
    }
    userErrors { code field message }
  }
}
```

The stored reference memory has been corrected. **Do not describe `@idempotent` as a future blocker — adopt it now.**

**`InventorySetQuantitiesInput` (2026-01):**

| Field | Type | Notes |
|---|---|---|
| `name` | `String!` | allowed values `available` \| `on_hand` — use **`available`**, consistent with the existing inventory code and with what Zettle reads |
| `quantities` | `[InventoryQuantityInput!]!` | |
| `reason` | `String!` | required; use `"correction"` (always accepted); a stocking-specific reason is a Phase 0 refinement |
| `referenceDocumentUri` | `String` | `managerbeyo://preorder/<operation_id>` |
| `ignoreCompareQuantity` | `Boolean` | **deprecated with a removal date in 2026-01; removed in 2026-04** |

**`InventoryQuantityInput` (2026-01):**

| Field | Type | Notes |
|---|---|---|
| `inventoryItemId` | `ID!` | |
| `locationId` | `ID!` | |
| `quantity` | `Int!` | the absolute target — `1` |
| `changeFromQuantity` | `Int` | "The quantity currently expected at this location, before setting the new quantity." Compare-and-swap; `null` skips the check; a mismatch fails with `CHANGE_FROM_QUANTITY_STALE` |
| `compareQuantity` | `Int` | **deprecated with a removal date in 2026-01; removed in 2026-04** |

**Design consequence — adopt the forward-compatible shape now.** Rev 2 planned `ignoreCompareQuantity: true`. That field is already deprecated and disappears in `2026-04`. The equivalent, non-deprecated way to say "overwrite unconditionally" is to **omit `ignoreCompareQuantity` entirely and pass `changeFromQuantity: null` explicitly**. That document is valid on `2026-01` today and survives the `2026-04` removals **unchanged**. Use it.

**Why the compare check is deliberately skipped.** This workflow is intentionally the **source of truth for the pre-order unit**: the business rule is "make it exactly 1", agreed in full knowledge that a reused SKU's existing stock is overwritten. Passing `changeFromQuantity: null` therefore permits ManagerBeyo to overwrite a concurrent inventory change. The prior quantity is still read and recorded as an **audit value** (R9) — explicitly *not* used as a compare-and-set guard under the current business rule.

**`userErrors` type.** `InventorySetQuantitiesUserError` **does** expose `code` — unlike the plain `UserError` returned by `inventoryItemUpdate` / `inventoryActivate`, which has **no `code` field** in this version. Select fields accordingly per mutation.

**2026-04 upgrade checklist — this is more than "add an idempotency key":**
1. `@idempotent` becomes **mandatory** — already satisfied if this plan ships as written.
2. `InventorySetQuantitiesInput.ignoreCompareQuantity` is **removed** — already satisfied (never sent).
3. `InventoryQuantityInput.compareQuantity` is **removed** — already satisfied (never sent).
4. **Verify the `changeFromQuantity` contract**, which is the surviving compare-and-swap mechanism: confirm that explicitly passing `null` still means "skip the check" and that `CHANGE_FROM_QUANTITY_STALE` is the mismatch code. Do not assume parity with `2026-01`.
5. Re-check the additive `inventoryAdjustQuantities` path used by product sync against the same directive requirement — that path is **not** in this plan's scope but shares the API version.

### R6 — `userErrors` fidelity

`raise_for_graphql_user_errors` (`graphql_client.py:233-251`) currently discards every message and raises one opaque `graphql_user_errors` code. Backwards-compatible extension:
- Add `ShopifyGraphQLUserErrorsError(ShopifyGraphQLNonRetryableError)` carrying `user_errors: tuple[dict, ...]` — each `{"field": list[str] | None, "message": str[:300], "code": str | None}`.
- `raise_for_graphql_user_errors` raises the new **subclass**, keeping `error_code="graphql_user_errors"` as the default, so every existing `except ShopifyGraphQLError` / `exc.error_code` call site (`_product_sync_orchestrator.py:140-143`, `_inventory_sync.py:150-156`) is unaffected.
- Add an optional `error_code=` override so pre-order clients attach stage-specific codes.
- Only `field`, `message` and (where the typed error exposes it) `code` are retained. Never the raw response, never the variables.

### R7 — The inventory location is seller-selected and operation-frozen (rewritten in rev 6)

Revs 3–5 treated the location as integration-level configuration: a `zettle_inventory_location_id` column, an admin route to populate it, a three-way resolution hierarchy (`shopify_default` / `configured_zettle_location` / `explicit_override`), an `acknowledge_not_zettle_synced` escape hatch, and a `PARTIALLY_PROVISIONED` terminal state to describe "provisioned, but not where we expected". **All of that is removed.**

The seller knows which till the item is going to. Making them say so is simpler than inferring it, and it lets the business move warehouses without a backend change or a migration.

**The model is now one path:**

1. The frontend loads the shop's locations from the existing `GET /integrations/shopify/locations` endpoint and presents a selector.
2. The seller picks one. The GID travels in the pre-order request as `inventory_location_id`.
3. The backend validates it **locally** and commits it as durable intent, atomically with the task.
4. The worker **re-validates it against Shopify** before touching inventory, and writes to that location or fails. It never substitutes another.

**Why not keep the column as an optional default?** Because a default belongs in the UI, not the schema. The frontend can seed the selector from the last-used location or from the Phase 0-verified Västberga GID without the backend owning a column, a route, a migration and a rollout prerequisite for it. Retaining it "just as a hint" would reintroduce exactly the two-sources-of-truth ambiguity this revision removes. **Recommendation: drop it entirely.** If a server-side default is later wanted, it is an additive column with no impact on this design, because the operation already stores its own frozen location.

**Split validation by what each side can do without calling Shopify.** Shopify must never be called inside the task-creation transaction (R2), so validation is deliberately split:

| | Command time (local only, no network) | Worker time (before the inventory mutation) |
|---|---|---|
| GID shape matches `^gid://shopify/Location/\d+$` | ✅ | — |
| Shop integration belongs to the workspace, is active, has a token | ✅ | — |
| Location belongs to **that** shop | — | ✅ via `fetch_shop_locations` |
| Location is still **active** | — | ✅ `isActive` |
| Location can **hold inventory** | — | ✅ `isFulfillmentService == false` |
| Persist as durable intent | ✅ | — |

**"Do not trust a location ID merely because the frontend supplied it."** A well-formed GID for a location in a *different* merchant's shop is indistinguishable from a valid one without asking Shopify — so the ownership check is a hard worker-time gate, not an optimisation. It is the same check the inventory sync already performs (`_inventory_sync.py:53-70`).

**"Capable of holding inventory"** is defined as `isActive == true` **and** `isFulfillmentService == false`. Inventory at a fulfillment-service location is managed by that third-party service and cannot be freely set, so writing there would fail or silently mislead. `shipsInventory` is surfaced to the selector as an informational hint but is **not** a gating condition — it describes shipping behaviour, not inventory capability (the same mistake rev 2 made with `fulfillsOnlineOrders`).

**Freezing.** The location is written once, at command time, and is never recomputed. Every retry reuses the persisted `inventory_location_id` and the `inventory_idempotency_key` derived from it (R8). Changing the business's preferred location tomorrow affects only **newly created** pre-orders; queued and retrying operations keep the location chosen when they were created. Silently switching would put stock at the wrong till or in the wrong warehouse — an error that looks like success, which is the failure mode this whole design exists to prevent.

**If the location becomes invalid after task creation** — deactivated, deleted, or moved to another shop — the worker fails with `preorder_inventory_location_invalid`, retaining every Shopify product and variant ID already created. No automatic substitution. A correction workflow (re-enqueue against a new location) is a follow-up, deliberately out of scope here.

**What this deletes:** the `zettle_inventory_location_id` column and its migration, `set_shopify_zettle_inventory_location` and its request and `PATCH /shops/{id}/zettle-location` route, `SHOPIFY_PREORDER_REQUIRE_VERIFIED_ZETTLE_LOCATION`, the command-time `preorder_zettle_location_not_configured` rejection, `ShopifyPreorderLocationResolutionEnum` and its three values, `ShopifyPreorderInventoryOverrideRequest` with `acknowledge_not_zettle_synced`, the `PARTIALLY_PROVISIONED` status, the `outcome_code` column, `inventory_location_resolution`, `inventory_location_is_zettle_synced`, the `INVENTORY_LOCATION_RESOLVED` stage, the `preorder_location.py` resolution policy module, and four error codes. The feature is no longer disabled when nothing is configured, because there is nothing to configure.

### R8 — Deterministic inventory idempotency key (new in rev 3)

Shopify recommends a random UUID to avoid collisions and documents no charset or length limit. A random key would defeat the purpose here — a **retry must reuse exactly the same key**. Format:

```
shopify-preorder:<preorder_operation_id>:inventory-set:<location_numeric_id>
```

where `<location_numeric_id>` is the trailing numeric segment of the Shopify Location GID (`gid://shopify/Location/123` → `123`), so the key contains no `/` or `//` sequences.

Example: `shopify-preorder:shpsi_a1b2c3d:inventory-set:74188390481`

Properties, each covered by a test:
- **Deterministic** — a pure function of `(operation.client_id, inventory_location_id)`.
- **Stable across retries** — depends on **neither** `attempt_count`, the `ExecutionTask` client id, any timestamp, nor the worker instance.
- **Distinct per operation** — two pre-orders never share a key, because `client_id` is unique.
- **Persisted and reconstructable** — written at **command time**, alongside `inventory_location_id`, in the same transaction as the task (rev 6: both inputs are known then, so there is nothing to resolve later) *and* recomputable from the two persisted identifiers, so a missing column cannot cause a key change.
- Because the seller-selected location is frozen from the moment the operation is created and never recomputed (R7), the key is frozen with it — including across a change to the business's preferred location.

Shopify-level idempotency is **additional** protection. The absolute set is already replay-safe (setting to 1 twice yields 1) and the resumable state machine remains the primary mechanism; `@idempotent` guards the narrow window where a request is delivered twice and the response to the first is lost.

Phase 0 verifies that this key **format and length** are accepted, and that replaying the identical mutation with the same key is accepted safely.

### R9 — Auditing the destructive inventory overwrite

Before the absolute set, the worker calls the existing `resolve_inventory_item_state` (which already returns `available`, `tracked`, `level_exists`) and records the reading. Persisted in `inventory_result_json`:

```json
{
  "location_id": "gid://shopify/Location/74188390481",
  "before_available": 4,
  "target_quantity": 1,
  "location_name": "Västberga Warehouse",
  "compare_protection": "explicitly_bypassed",
  "idempotency_key": "shopify-preorder:shpsi_a1b2c3d:inventory-set:74188390481",
  "outcome": "applied"
}
```

`before_available` is an **audit value only** — under the current business rule it is deliberately *not* passed as `changeFromQuantity`, because the workflow is intentionally authoritative for the pre-order unit. `compare_protection: "explicitly_bypassed"` records that choice on every row so the decision is legible at audit time rather than buried in code.

### R10 — Product metafields, and why `quantity` is not the inventory target (new in rev 4)

The caller supplies metafield values to store on the created/updated product. One of them has key `quantity`.

> **⚠️ SUPERSEDED 2026-07-27 (rev 10).** The independence rule below was **reversed by explicit
> decision**: `custom.quantity` is now **derived** from the inventory selection — the sum of
> `inventory[].quantity` across all locations — and is **rejected** if a caller supplies it. One
> seller-entered number drives both the till stock and the product's quantity field. See the
> Review log entry for 2026-07-27 (rev 10) and
> `domain/shopify/preorder_policy.build_preorder_quantity_metafield`.
>
> The evidence that motivated the original rule is still accurate and worth keeping: the merchant's
> live `CustomTC3` products carry `custom.quantity = "6"` alongside `available = 1`, so the two
> numbers **have** historically differed. That is what made independence look correct. The decision
> to unify them is a change to what the field means going forward, not a correction of the evidence.
>
> Everything below is retained for that evidence and for the reasoning trail.

**`custom.quantity` is metafield data, not inventory input — and this still holds in rev 9.**

There are now **two** caller-supplied quantities, and conflating them is the single easiest mistake to make in this feature:

| Input | Meaning | Where it goes |
|---|---|---|
| `custom.quantity` metafield | describes the furniture set / item composition | a product metafield, written by `productCreate` / `productUpdate` |
| inventory `quantity` per location | how many sellable units exist at that till | `inventorySetQuantities` |

They are independent. R11's live evidence is the proof: `custom.quantity = "6"` alongside
`available = 1` on the same product. Inventory must **never** be calculated from, multiplied by,
or otherwise influenced by `custom.quantity`.

Rev 3's `ShopifyPreorderProductRequest.quantity: int = 1` conflated the two and was removed;
`custom.quantity` is one entry in the generic `metafields` list, so adding, renaming or dropping
metafields needs no backend change. **Rev 9 correction:** the inventory quantity is not the fixed
constant rev 4–8 described — it is caller-supplied per location, as an absolute set. The
independence rule is unchanged; only the source of the inventory number moved from a constant to
the caller's inventory selection.

**Verified for `2026-01`:** both `ProductCreateInput` and `ProductUpdateInput` expose `metafields: [MetafieldInput!]` — *"The custom fields to associate with the product for the purposes of adding and storing additional information."* Metafields therefore ride along in the **same mutation** as the product fields and the media, which is strictly better than product sync's separate `metafieldsSet` call (`product_sync_client.py:230-263`): one fewer round trip, atomic with the product write, and no separate partial-failure stage to model. **This plan does not call `metafieldsSet`.**

**`MetafieldInput` (2026-01):**

| Field | Type | Requirement |
|---|---|---|
| `namespace` | `String` | **required when creating**, optional when updating; 3–255 chars, alphanumeric/hyphen/underscore |
| `key` | `String` | **required when creating**, optional when updating; 2–64 chars, alphanumeric/hyphen/underscore |
| `type` | `String` | **required when creating or updating a metafield without a definition**; optional when a definition already exists |
| `value` | `String` | optional; **always stored as a string regardless of the metafield's type** |
| `id` | `ID` | optional; namespace+key is the preferred addressing form |

**Accepted caller shapes**, resolved in this order:

1. `{"definition_id": "gid://shopify/MetafieldDefinition/241114906954", "value": "6"}` — **preferred.** `namespace`, `key` and `type` are resolved from the definition, so a definition rename or type change cannot silently produce a mistyped metafield. This is also the shape the existing metafield-preferences system already speaks: `shopify_metafield_preferences.shopify_metafield_definition_id` stores exactly this GID, and `metafield_definition_client.fetch_shopify_metafield_definitions_by_ids` already selects `namespace`, `key`, `type { name }` and `validations`.
2. `{"namespace": "custom", "key": "quantity", "type": "single_line_text_field", "value": "6"}` — fully explicit, no lookup.
3. `{"key": "quantity", "value": "6"}` — shorthand. `namespace` defaults to `SHOPIFY_PREORDER_METAFIELD_NAMESPACE` (default `"custom"`, matching product sync's hardcoded namespace) and `type` is omitted, which Shopify accepts **only when a definition already exists** for that namespace/key. Documented as such; a missing definition surfaces as a `userErrors` entry with the field path.

**The merchant's real `quantity` definition (verified, R11):**

| | |
|---|---|
| Definition ID | `gid://shopify/MetafieldDefinition/241114906954` |
| Namespace | `custom` |
| Key | `quantity` |
| Type | **`single_line_text_field`** — *not* `number_integer` |

Rev 4's examples presented this as `number_integer`; that was an invention and is corrected everywhere. The type is nonetheless **never hard-coded** into generic metafield logic — shape 1 resolves it dynamically at worker time, which is exactly why a wrong guess in a doc example costs nothing at runtime. The correction matters for the *tests and Phase 0 fixtures*, which must exercise the real shape rather than a plausible one.

**Definition resolution happens at worker time, never at command time** — resolving shape 1 requires a Shopify query, and no Shopify network call may occur inside the task-creation transaction (R2). The normalized payload stores the caller's shape verbatim; the worker performs at most **one** `fetch_shopify_metafield_definitions_by_ids` call for all definition-addressed entries before building the `MetafieldInput` list.

**Value stringification** reuses the existing `_stringify_metafield_value` rule (`product_sync_payloads.py:137-140`): strings pass through, everything else is `json.dumps`'d with compact separators. That yields `3` for an int and `"a,b"`-free compact JSON for lists — correct for `number_integer`, `list.single_line_text_field` and the reference types alike.

**No scope change.** Writing product metafields is covered by `write_products`; reading metafield definitions by `read_products`. Both are already granted. Metaobject-reference metafields need no extra scope to *write* — the caller supplies the metaobject GID as the value.

### R11 — Live merchant-store evidence: SKU `CustomTC3` (new in rev 5)

An exact-SKU query against the merchant's production store returned **two distinct products sharing the SKU `CustomTC3`**:

| | Older product | Newer product |
|---|---|---|
| Product GID | `gid://shopify/Product/15648379797834` | `gid://shopify/Product/15930838548810` |
| `status` | **`UNLISTED`** | **`UNLISTED`** |
| `price` | `31200.00` | `5200.00` |
| `custom.quantity` | `"4"` | `"6"` |
| `available` | **`0`** | **`1`** |
| `on_hand` | `1` | `1` |
| `committed` | `1` | `0` |

Both variants share: `sku: CustomTC3`, `tracked: true`, `requiresShipping: true`, `inventoryPolicy: DENY`, `taxable: false`, `barcode: null`. Inventory is activated on **one** location only:

- `gid://shopify/Location/99221471562` — **Västberga Warehouse**, `isActive: true`, `shipsInventory: true`

Seven conclusions, each of which changes the plan:

**1. `UNLISTED`, not `ACTIVE`.** Both live products are `UNLISTED`, so that status is empirically compatible with the merchant's working Zettle flow. Rev 4's `ACTIVE` policy and its "ACTIVE is required for Zettle visibility" justification are withdrawn (R4).

**2. Duplicate exact SKUs are a *confirmed production condition*, not a hypothetical.** Rev 4 treated `ambiguous_product_match` as defensive programming. It is not — the very first SKU examined already violates uniqueness. This reclassifies the ambiguity branch from "edge case" to "expected path that will fire on real data", and it raises the stakes of the reuse-and-overwrite-price rule: silently picking one of these two products would overwrite either a `31200.00` or a `5200.00` price at random. The rules are therefore made explicit and mandatory:

> 1. Operation-tag lookup runs **first**.
> 2. If no operation-tag match, run the exact-SKU lookup.
> 3. Group exact matches **by distinct Shopify product ID**.
> 4. Exactly **one** distinct product ID may be reused.
> 5. Two or more distinct product IDs → **fail `ambiguous_product_match`**.
>
> The worker must **never** auto-select using result order, oldest/newest, creation timestamp, price, inventory availability, or product status. No price overwrite may occur until ambiguity is resolved by a human.

The existing `select_exact_variant_match` (`domain/shopify/product_sync_identity.py:44-46`) already implements exactly this grouping-and-raise behaviour, so this is a documentation and test correction rather than new logic. Multiple *variants* of the **same** product remain a single valid match; only distinct **product IDs** are ambiguous.

**3. Västberga Warehouse is the location Zettle is believed to read** — `gid://shopify/Location/99221471562`, the only location with activated inventory on these products, `isActive: true`, `shipsInventory: true`. **As of rev 6 this informs the frontend's default selector option, not a backend restriction.** Phase 0 gate 3 still confirms Zettle actually reads it, because that answer is what makes the default a *good* default — but the seller can pick any valid location, and the backend has no opinion about which one is "the Zettle location". **The GID must not be hard-coded into reusable frontend or backend code** — it belongs in this plan's evidence and, at most, in a frontend default that remains user-changeable.

**4. `available`, not `on_hand`, defines till readiness.** The older product proves the distinction concretely: `on_hand = 1` with `committed = 1` yields `available = 0` — a unit that exists but cannot be sold. The newer product's `on_hand = 1, committed = 0 → available = 1` is the sellable state. `inventorySetQuantities` therefore keeps `name: "available"` and the target `1`. **Do not change the target to `on_hand`.** The audit read continues to record `before_available`, which is the same quantity the readiness rule is stated in.

**5. `custom.quantity` is `single_line_text_field`.** Corrected in R10.

**6. The quantity metafield is completely independent of inventory.** The newer product is the proof: `custom.quantity = "6"` while `available = 1` — two different numbers on the same product. `custom.quantity` describes the furniture set or item composition; Shopify inventory counts sellable units at the till. Inventory must never be calculated from, multiplied by, or otherwise influenced by `custom.quantity`. *(Rev 9: the inventory number is now caller-supplied per location rather than a constant `1`, which makes this separation **more** important, not less — two caller-supplied quantities now travel in the same request.)*

**7. Price must never be derived from quantity.** The two products invite a false inference — `31200.00` with `quantity "4"`, `5200.00` with `quantity "6"` — and the numbers do not support any consistent formula in either direction (`31200/4 = 7800`; `5200/6 ≈ 866.67`; `5200 × 6 = 31200` is a coincidence of magnitude, not a rule, and inverts the operand roles). The variant price is **caller-supplied business data written exactly as supplied**. The worker must never compute `price × quantity` or `price ÷ quantity` from `custom.quantity`.

**Variant field policy, from the observed defaults.** Both products agree on all five, so the plan sets them deliberately rather than leaving them to Shopify's defaults — while explicitly *not* expanding into a general product-settings system:

| Field | Location in the API | Decision |
|---|---|---|
| `inventoryItem.tracked` | `InventoryItemInput` | **`true`, mandatory.** An untracked item cannot hold a quantity, so Zettle would see no stock. |
| `inventoryPolicy` | `ProductVariantsBulkInput` | **Set explicitly to `DENY`**, matching every observed product. Prevents overselling a one-off pre-order unit. |
| `inventoryItem.requiresShipping` | `InventoryItemInput` | **Set explicitly to `true`**, matching every observed product — these are physical furniture items. |
| `taxable` | `ProductVariantsBulkInput` | **Configuration-driven, not assumed.** `taxable: false` is observed on both products, but nothing establishes it as a platform rule rather than this merchant's pre-order tax policy. Exposed as `SHOPIFY_PREORDER_VARIANT_TAXABLE` (default `false`, matching observation) so a second merchant is not silently forced into it. **Phase 0 gate 10 confirms the intent.** |
| `barcode` | `ProductVariantsBulkInput` | **Left `null` unless supplied.** Observed `null` on both. Not added to the request contract in this plan. |

### R12 — Convergence onto the existing product-sync pipeline (new in rev 7)

Revs 2–6 designed pre-order as a parallel pipeline. An overlap review against `/products/process` as it exists today showed that was largely unnecessary:

| Pre-order requirement | Already in product sync? |
|---|---|
| Resolve-or-create by exact SKU | ✅ identical (`find_product_variant_by_identity` + `select_exact_variant_match`) |
| Ambiguous SKU → fail, never guess | ✅ already raises `ShopifyProductLookupAmbiguousError` |
| Variant SKU + price | ✅ identical `productVariantsBulkUpdate` |
| Product status `UNLISTED` | ✅ **already works** — `_normalize_status` uppercases whatever is passed (`product_sync_payloads.py:91-95`) |
| Single target shop | ✅ one entry in `target_shop_integration_ids` |
| Tags, product type, description | ✅ identical |
| Worker, queue, retry, backoff, socket wiring | ✅ same queue, same `SHOPIFY_PROCESS_PRODUCTS` task, same handler |
| Metafields | ⚠️ present, but `custom` namespace hardcoded and no `definition_id` resolution |
| Inventory at a location | ⚠️ **additive only** (`quantity_to_add`) |
| Product image | ❌ absent |
| Variant policy (`inventoryPolicy`, `requiresShipping`, `taxable`) | ❌ absent |
| Resumable stages | ❌ absent |
| Task linkage + per-task idempotency | ❌ absent |

**Roughly 70% of rev 6 was a reimplementation.** Genuinely new: absolute inventory set, media, variant policy, the stage machine, task linkage and metafield-definition resolution — six items, four of them small.

**The decisive argument is drift.** Two places that write products to Shopify means every fix lands in one and not the other. This plan already produced evidence for that: the lost-`productCreate`-response duplicate gap (state-machine R-note) exists in product sync **today**, and rev 6 deferred it to a follow-up ticket precisely because the pipelines were separate. Converging fixes it once, for both.

**Where the two flows genuinely differ is lifecycle, not mechanism.** Product sync is *declarative and repeatable* — "make Shopify match this payload", safe to re-run whenever a price changes. Pre-order is *one-shot provisioning tied to a task*. That difference is real but narrow, and it is handled by two columns and a partial index rather than by a second pipeline.

**The one thing that must not be shared is the destructive mode.** An `inventory_mode: "set"` flag reachable from the general-purpose `/products/process` route would let a bad or buggy caller wipe real stock. So the mode is **not part of any HTTP request schema** — it is set by `_create_preorder_sync_item_in_session`, which only `create_task` calls. The HTTP route keeps additive-only semantics permanently. Media and variant policy *are* shared, because they are harmless and useful to both.

**Shape:**

```
create_task ──> _create_preorder_sync_item_in_session ─┐   mode = preorder
                                                       ├─> ShopifyProductSyncItem
POST /products/process ──> process_shopify_products ───┘   mode = product_sync
                                                              │
                                                              ▼
                                          TaskType.SHOPIFY_PROCESS_PRODUCTS  (unchanged)
                                                              │
                                                              ▼
                                          handle_shopify_process_products    (unchanged entry)
                                                              │
                                                              ▼
                                          shared staged orchestrator
                                            ├ tag / exact-SKU resolve      (shared)
                                            ├ product + metafields + media (shared)
                                            ├ variant + policy             (shared)
                                            └ inventory: additive │ set-to-1
```

**What this deletes from rev 6:** the `shopify_preorder_operations` table, its migration and its `shppre` prefix registration; `TaskType.SHOPIFY_CREATE_PREORDER_PRODUCT`, `ShopifyCreatePreorderProductPayload`, and its `QUEUE_MAP` / `HANDLER_TIMEOUT_SECONDS` / `HANDLER_MAP` entries and enum migration; `handle_shopify_create_preorder_product.py`; `preorder_results.py`; and one status enum (the existing `ShopifyProductSyncItemStatusEnum` already has exactly `pending`/`processing`/`succeeded`/`failed`). Roughly **half the new files**, with every safety property from revs 3–6 preserved.

**What it costs:** `ShopifyProductSyncItem` gains ~10 nullable columns that only matter in pre-order mode, and the orchestrator gains mode branches at one stage. That is the "one function, two modes" smell, accepted deliberately as cheaper than two pipelines that drift apart.

### R13 — Minimum scope: what is actually required (new in rev 8)

Rev 7 converged pre-order onto the product-sync pipeline but kept an eleven-phase structure. A
second audit asked a sharper question — *not* "what would a robust pre-order system look like",
but **"what does the existing system already do, and what is the smallest delta?"**

Already working in `/products/process` today, needing **no** change:

| Requirement | Status |
|---|---|
| Resolve-or-create by exact SKU | ✅ |
| Ambiguous SKU → fail, never guess | ✅ `select_exact_variant_match` already raises |
| Variant SKU + price | ✅ |
| Product status `UNLISTED` | ✅ `_normalize_status` uppercases whatever is passed |
| Single target shop | ✅ one entry in `target_shop_integration_ids` |
| Tags, product type, description | ✅ |
| **Metafields incl. `custom.quantity`** | ✅ the normalizer accepts `{"quantity": {"type": "single_line_text_field", "value": "6"}}`, and hardcodes namespace `custom` — which **is** this merchant's namespace |
| **Inventory at a chosen location** | ✅ `inventory_adjustments: [{shop_integration_id, location_id, quantity_to_add}]` |
| **Location ownership validation** | ✅ `_inventory_sync.py:53-70` already rejects a location not in the shop |
| **Per-task replay safety** | ✅ the ledger is unique on `(shop, frontend_client_id, location)` with `on_conflict_do_nothing` and skips `APPLIED` rows — set `frontend_client_id = task_id` and a replayed task-created event does not double stock |
| Worker, queue, retry, backoff, socket | ✅ same infrastructure |

**Genuinely required, and nothing else:**

1. `public_url(key)` on `StorageClient` + `STORAGE_PUBLIC_BASE_URL` (R3).
2. `media` argument on `productCreate` / `productUpdate` in `product_sync_client.py`, plus an
   `image_id` field on the request.
3. Image size / dimension validation at command time (20 MB, 25 MP).
4. Absolute inventory set — see the business-rule note below.
5. `process_shopify_products` → `maybe_begin`, and `create_task` calling it with one item, one
   shop, `frontend_client_id = task_id`.

**Minimum schema delta: one enum and three columns**, not the fourteen in rev 7's table.
`inventory_mode` (`add` | `set`, default `add`, **never caller-settable**) plus
`shopify_media_id` and `media_status` for observability. `task_id` is unnecessary because
`frontend_client_id` carries it; the `@idempotent` key is derived at worker time from
`sync_item.client_id`, so it needs no column.

**Rev 9 note on item 4.** The inventory quantity is **caller-supplied per location**, not a fixed
`1`, so the request carries `inventory: [{location_id, quantity}]` — the same shape as today's
`inventory_adjustments`, with `quantity` replacing `quantity_to_add` because the semantics are
absolute rather than additive. `inventory_mode` is what distinguishes the two, and it is set by
the command, never by a caller.

**Everything else in this document is backlog**, and falls into three buckets:

- **Standalone improvements**, worth doing with or without pre-orders — extracted as their own
  tickets: `userErrors` fidelity (R6), and the staged orchestrator + operation-tag reconciliation
  that closes the lost-`productCreate`-response duplicate bug (R12 / state-machine R-note).
- **Hardening** — the frozen-location model, `is_fulfillment_service` filtering, the partial
  unique index, the pure policy modules, definition-ID metafield resolution. These defend against
  failure modes the existing ledger and validation largely already cover. Pull them in if
  something bites.
- **Documentation** — the architecture-doc and handoff work, to be scaled to what is actually built.

**Business-rule note — resolved in rev 9.** The additive-versus-absolute question was put to the
merchant explicitly, with the stock arithmetic and the deleted-work list shown for each. The
answer was **absolute set with a caller-supplied quantity**: the frontend chooses a location *and*
a quantity for it, and that quantity **overwrites** whatever stock is at that location rather than
adding to it. The additive alternative — which would have removed `inventorySetQuantities`,
`@idempotent`, the `changeFromQuantity` contract and the key derivation — was declined. It is
recorded here only so a future reader knows it was weighed, not overlooked.

Because the overwrite is now confirmed **and** the quantity arbitrary, the `before_available`
audit value (R9) becomes more load-bearing, not less: it is the only record of what stock existed
before a pre-order replaced it.

---

## Acceptance criteria

1. Creating a `PRE_ORDER` task with a `shopify_preorder` section returns the normal task-creation response plus `shopify_preorder: {…}`, and commits exactly one operation row and one `OPEN` `ExecutionTask` **in the same transaction** as the `Task` row.
2. No Shopify HTTP call occurs during the task-creation request — asserted by a test that `execute_shopify_graphql` is never awaited inside `create_task`.
3. A non-`PRE_ORDER` task type, or a role outside `admin`/`manager`/`seller`, carrying a `shopify_preorder` section is rejected before any row is written.
4. On the dev store the worker produces a product that is **`UNLISTED`**, **not visible on the online store**, with the supplied title/description/product type/tags, one variant with the supplied SKU and price, `inventoryPolicy: DENY`, `requiresShipping: true`, `tracked: true`, the supplied image attached, **every supplied metafield written with the correct namespace/key/type**, and **`available = 1`** at the resolved location.
4a. **Till readiness is asserted on `available`, not `on_hand`.** A product left at `on_hand = 1, committed = 1, available = 0` is **not** reported as ready.
5. When the SKU resolves to **exactly one** distinct product, no second product is created; the existing product is updated, its price overwritten, and its metafields written.
5a. **A `custom.quantity` metafield of `"6"` alongside an inventory selection of `2` yields `available = 2`** — the two caller-supplied quantities are independent, and the metafield never reaches the inventory mutation. Use **different** numbers in this test so a wrong wiring cannot coincidentally pass.
5d. **Two distinct products sharing the exact SKU fail with `ambiguous_product_match`** before any product, price or inventory write. No selection is made by result order, age, price, stock, status or timestamp. (Confirmed production condition — R11.)
5e. **The variant price is written byte-identically to what the caller supplied.** No code path multiplies or divides it by any metafield value.
5b. **Metafields are written by the same `productCreate`/`productUpdate` mutation** — no `metafieldsSet` call is made anywhere in this workflow.
5c. A metafield addressed by `definition_id` resolves its namespace/key/type from Shopify at worker time, in **one** batched definition query regardless of how many entries use that form.
6. Every Shopify identifier (product, variant, inventory item, media) is persisted **before** the next stage's first network call.
7. Re-running the same task's pre-order (duplicate replay, worker retry, manual re-enqueue) creates **zero** additional Shopify products and leaves the quantity at `1`; the workflow resumes from the last confirmed stage.
8. A `productCreate` whose response is lost does not produce a duplicate on retry — the retry finds the orphan by its operation tag.
9. A failure at any stage leaves the operation non-successful with the exact stage, an `error_code` from the taxonomy, a safe message, retained `userErrors` field paths, and every already-created Shopify ID intact. No Shopify resource is ever deleted.
10. **The operation cannot report `SUCCEEDED` unless `available = 1` was written at the exact location the seller selected.** `zettle_ready: true` means precisely that.
11. **A location that is missing from the shop, inactive, or a fulfillment-service location fails before the inventory mutation** with `preorder_inventory_location_invalid` — product and variant IDs retained, never reported as success.
12. **A well-formed GID belonging to a different shop is rejected at worker time**, proving the backend does not trust a location merely because the frontend supplied it.
13. **The worker never substitutes a location** — not from array order, not the first active location, not a primary location, not the previously used one.
14. **The selected location is stable across retries** — a retry reuses the persisted `inventory_location_id` verbatim, including after the business changes its preferred location. Newly created pre-orders may use a different location without disturbing queued ones.
14a. **The location is committed atomically** with the `Task`, the operation row and the `ExecutionTask`; a rollback anywhere in `create_task` leaves none of them.
14b. **`ShopifyProductSyncItem.inventory_location_id` and `normalized_payload_json.inventory.location_id` always agree.**
15. **Replaying the inventory stage sends the same `@idempotent` key**; two different operations produce different keys; the key is independent of attempt count, execution-task id, timestamp and worker instance.
16. **Retrying after a lost inventory response is safe** and leaves the quantity at `1`.
17. **The prior available quantity is recorded** in `inventory_result_json` before the overwrite.
18. **No dual inventory write occurs** — exactly one `inventorySetQuantities` call per operation per attempt, against exactly one location.
19. The `inventorySetQuantities` document sends `@idempotent(key: …)`, sends `changeFromQuantity` explicitly, and **never** sends `ignoreCompareQuantity` or `compareQuantity`.
20. `shopify.preorder.processed` is emitted to the workspace room exactly once per terminal outcome, carrying the full `inventory` block and `zettle_ready`.
21. No access token, raw Shopify response, or customer PII appears in `shopify_integration_events.metadata_json` or any log line.
22. **`SHOPIFY_APP_SCOPES` is unchanged and no shop needs reauthorization**, unless the Phase 0 storefront gate fails and storefront unpublication is required.
23. The existing Shopify test suite is unchanged and green; `shopify_inventory_adjustments` and `/products/process` behavior are untouched.

---

## Contracts and skills

### Contracts loaded

Core (always):
- `backend/architecture/01_architecture.md`: layer boundaries — router → command → domain → infra.
- `backend/architecture/04_context.md`: `ServiceContext` fields (`workspace_id`, `user_id`, `role_name`, `identity`, `session`, `incoming_data`).
- `backend/architecture/05_errors.md`: `DomainError` subclasses and `http_status` mapping (`ValidationError`, `NotFound`, `PermissionDenied`, `ExternalServiceError`).
- `backend/architecture/06_commands.md` + `06_commands_local.md`: command shape; `maybe_begin` owner/subordinate semantics; no `commit`/`rollback` inside; subordinates must not dispatch events.
- `backend/architecture/07_queries.md` + `07_queries_local.md`: read-only query shape (locations query extension).
- `backend/architecture/09_routers.md`: `run_service` + `build_ok`/`build_err`, role gates (the Zettle-location admin route).
- `backend/architecture/21_naming_conventions.md`: file/function/enum naming.
- `backend/architecture/40_identity.md`: `IdentityMixin`, `CLIENT_ID_PREFIX`, prefix-map registration.
- `backend/architecture/41_user.md`: `created_by_id` conventions.
- `backend/architecture/42_event.md` + `42_event_local.md`: domain-event shape already in `create_task`.
- `backend/architecture/48_presence.md` + `48_presence_local.md`: workspace room semantics.

Goal bundle — **Worker-driven backend** + **Replayable async runtime**:
- `backend/architecture/16_background_jobs.md`: `ExecutionTask` lifecycle, `create_instant_task`, payload-carries-IDs-only rule.
- `backend/architecture/12_infra_redis.md`: queue naming, `queue:shopify`.
- `backend/architecture/51_worker_runtime.md`: handler signature, retry/backoff, timeout registration.
- `backend/architecture/52_replayability.md`: resumable-stage, idempotency-key and reconciliation requirements.
- `backend/architecture/49_observability_runtime.md`: structured-log field discipline.
- `backend/architecture/11_infra_events.md`: event-bus boundaries — cited to justify *not* using it (R2).
- `backend/architecture/53_operational_cli.md`: manual re-enqueue entry point.

Trigger expansions:
- `backend/architecture/19_integrations.md`: adapter pattern — GraphQL documents live only in `services/infra/shopify/*`.
- `backend/architecture/18_security.md`: encrypted credentials, no-secret serialization.
- `backend/architecture/24_multi_tenancy.md`: workspace and shop isolation.
- `backend/architecture/25_soft_delete.md`: active/not-deleted integration filters.
- `backend/architecture/03_models.md`: new database model + new column.
- `backend/architecture/30_migrations.md`: additive `ALTER TYPE … ADD VALUE IF NOT EXISTS`, additive column.
- `backend/architecture/13_sockets.md`: Socket.IO completion event.
- `backend/architecture/15_testing.md` + `50_testing_strategy.md`: the test matrix.
- `backend/architecture/32_concurrency.md`: `SELECT … FOR UPDATE` on the operation row; concurrent-inventory reasoning in R5.
- `backend/architecture/33_deployment.md`: env checklist — confirming **no** scope change and, as of rev 6, **no configuration rollout prerequisite** at all.
- `backend/architecture/34_file_storage.md`: presigned GET, TTL, storage keys.
- `backend/architecture/43_image.md` + `43_image_local.md`: `images.image_url` semantics per provider.
- `backend/architecture/28_roles_permissions.md`: the `admin`/`manager`/`seller` gate.
- `backend/architecture/57_shopify_integration.md`: the integration's architecture doc — this plan updates it.

### Local extensions loaded

- `06_commands_local.md`: `maybe_begin` replaces `session.begin()`; subordinate mode performs **no** commit/rollback; only `add`/`flush`/`execute` inside; subordinates return `pending_events` rather than dispatching. **Directly load-bearing.**
- `07_queries_local.md`: offset pagination overrides cursor pagination.
- `42_event_local.md`: app-specific workspace-event payload shape.
- `43_image_local.md`: confirms `image_url` is the stored access reference.
- `48_presence_local.md`: workspace room naming used by `emit_to_workspace_room`.

Read order applied: canonical first, then the `_local` companion; local wins for this app only.

### File read intent — pattern vs. relational

All files opened during planning were **relational** reads (what exists / what fields / how wired): `shopify.py`, `process_shopify_products.py`, `_product_sync_orchestrator.py`, `_product_sync_normalizer.py`, `product_sync_payloads.py`, `product_sync_client.py`, `graphql_client.py`, `inventory_client.py`, `_inventory_sync.py`, `product_sync_identity.py`, `shopify_product_sync_item.py`, `shopify_shop_integration.py`, `handle_shopify_process_products.py`, `shopify_worker.py`, `worker_base.py`, `task_router.py`, `task_factory.py`, `event_bus.py`, `create_task.py`, `tasks/requests/__init__.py`, `image.py`, `stable_presign.py`, `s3_client.py`, `get_download_url.py`, `confirm_upload.py`, `create_from_url.py`, `get_shopify_locations.py`, `config.py`, `enums.py`, `_events.py`, `transaction.py`, `permissions.py`.

Prohibited pattern reads during implementation:
- Do **not** open another command to learn `session.add`/`flush`/error-raising shape → `06_commands.md` + `06_commands_local.md`.
- Do **not** open another router to learn handler wiring → `09_routers.md`.
- Do **not** open another serializer to learn output shape → `46_serialization.md`.

### Skill selection

- Primary skill: none — the repository has no `SKILL.md` files (`task_system/` contains only `README.md` and `backend_contract_goal_mapping_guide.md`). Contract routing is document-only per the guide's "Document-only protocol (no resolver)".
- Router trigger terms: `worker`, `retry`, `replay`, `idempotency`, `integration`, `migration`, `socket`, `image`, `multi-tenancy`, `roles`, `deterministic testing`.
- Excluded alternatives: n/a.

---

## Database schema, state machine and constraints

### No new column on `shopify_shop_integrations`

Rev 5's `zettle_inventory_location_id` column, its additive migration and its rollout prerequisite are **removed** (R7). The location lives on the operation row, chosen per pre-order. `shopify_shop_integrations` is unchanged by this plan.

### No new table — `shopify_product_sync_items` is extended

Rev 6's `shopify_preorder_operations` table, its migration and its `shppre` prefix are **removed** (R12). A pre-order **is** a `ShopifyProductSyncItem` in `preorder` mode. Its existing `client_id` (`shpsi_…`) is the operation identifier used throughout the contracts below — wherever earlier revisions said "operation id", read `ShopifyProductSyncItem.client_id`.

Columns already present and reused unchanged: `workspace_id`, `shop_integration_id`, `frontend_client_id`, `requested_operation`, `status`, `normalized_payload_json`, `shopify_product_id`, `shopify_variant_id`, `shopify_inventory_item_id`, `inventory_result_json`, `error_code`, `error_message`, `created_by_id`, `created_at`, `updated_at`.

**Added columns — all nullable except `mode` and `stage`, so every existing row and every existing code path is unaffected:**

| Column | Type | Null | Used by | Notes |
|---|---|---|---|---|
| `mode` | `shopify_product_sync_mode_enum` | no | both | `product_sync` (default, server_default) \| `preorder`. **Not settable from any HTTP request** — only `_create_preorder_sync_item_in_session` writes `preorder` |
| `stage` | `shopify_product_sync_stage_enum` | no | **both** | default `queued`, server_default. The resume point. Adopting it for product sync too is what fixes the lost-response duplicate bug there |
| `task_id` | `String(64)` FK `tasks.client_id` RESTRICT | yes | pre-order | indexed; the traceability reference. `NULL` for ordinary syncs |
| `shopify_media_id` | `String(255)` | yes | both | populated when an image was supplied |
| `media_status` | `String(32)` | yes | both | Shopify `MediaStatus` at accept time — not waited on |
| `inventory_location_id` | `String(255)` | yes | pre-order | the **seller-selected** GID, written at command time, **frozen** (R7). `NULL` for product sync, which carries *many* locations in `normalized_payload_json.inventory.adjustments` instead |
| `inventory_location_name` | `String(255)` | yes | pre-order | resolved at worker time during validation, for the socket payload |
| `inventory_target_quantity` | `Integer` | yes | pre-order | always `1` today |
| `inventory_before_available` | `Integer` | yes | pre-order | audit value read immediately before the overwrite (R9) |
| `inventory_compare_protection` | `String(32)` | yes | pre-order | `explicitly_bypassed` |
| `inventory_idempotency_key` | `String(255)` | yes | pre-order | the deterministic `@idempotent` key (R8), written at command time |
| `inventory_applied_at` | `DateTime(tz)` | yes | pre-order | |
| `error_fields_json` | `JSONB` | yes | both | retained `userErrors` `[{field, message, code}]` (R6) |
| `attempt_count` | `Integer` | no | both | default `0`, server_default, incremented at worker entry |
| `last_attempted_at` | `DateTime(tz)` | yes | both | |

**Constraints and indexes:**

- **Partial unique index — the durable per-task duplicate guard:**
  ```sql
  CREATE UNIQUE INDEX uix_shopify_product_sync_items_preorder_task
    ON shopify_product_sync_items (shop_integration_id, task_id)
    WHERE task_id IS NOT NULL AND mode = 'preorder';
  ```
  This is what makes converging safe. Product sync's lifecycle is *repeatable* — re-syncing the same `frontend_client_id` to update a price later is normal and must stay unconstrained — while pre-order's is *one-shot*. The partial predicate gives each mode the uniqueness it needs without imposing either on the other. Existing rows all have `task_id IS NULL`, so the index is a no-op for them and needs no backfill.
- `CHECK (mode <> 'preorder' OR (task_id IS NOT NULL AND inventory_location_id IS NOT NULL AND inventory_idempotency_key IS NOT NULL))` — the three fields that are conceptually non-null for a pre-order are enforced at the database level despite being nullable columns, so the shared table cannot hold a malformed pre-order.
- `Index("ix_shopify_product_sync_items_task", "task_id")`
- The two existing indexes (`workspace_status`, `shop_integration_status`) are unchanged.

No `models/__init__.py` registration, no prefix-map entry and no `README` inventory change are needed — the model already exists.

### Enums (`domain/shopify/enums.py`)

```python
class ShopifyProductSyncModeEnum(StrEnum):        # new in rev 7
    PRODUCT_SYNC = "product_sync"
    PREORDER = "preorder"

class ShopifyProductSyncStageEnum(StrEnum):       # new in rev 7 — used by BOTH modes
    QUEUED = "queued"
    PRODUCT_CREATED = "product_created"           # product exists; metafields + media accepted
    VARIANT_CONFIGURED = "variant_configured"     # sku + price + policy written
    INVENTORY_SET = "inventory_set"               # inventory applied
```

**No new status enum** — the existing `ShopifyProductSyncItemStatusEnum` already has exactly `pending` / `processing` / `succeeded` / `failed`. Rev 6's `ShopifyPreorderOperationStatusEnum` and `ShopifyPreorderStageEnum` are replaced by the two above, which are named for the shared table rather than for pre-orders because both modes use them.

**Rev 6 removals:** `PARTIALLY_PROVISIONED` existed only to say "provisioned somewhere other than the configured Zettle location" — a distinction that cannot arise now that the seller names the location. `ShopifyPreorderLocationResolutionEnum` is deleted entirely: there is nothing to resolve. `INVENTORY_LOCATION_RESOLVED` is deleted as a stage because the location is already frozen at command time; what remains is *validation*, which is a cheap idempotent read folded into the inventory stage and **re-run on every attempt** rather than skipped by a stage guard — re-validating catches a location that was deactivated between attempts, which a resume-skip would miss. That leaves two new enums instead of three, and four stages instead of five.

`status` carries the lifecycle; `stage` carries the resume point. Keeping them separate lets "product created, inventory failed" be `status=FAILED, stage=VARIANT_CONFIGURED` without a retry reverse-engineering a compound value.

Also add `ShopifyIntegrationEventTypeEnum.PREORDER = "preorder"` — one new value; the boundary and outcome go in `metadata_json["stage"]` / severity. (Product sync keeps writing `PRODUCT_SYNC` events, so the two modes remain distinguishable in the history feed.)

**`TaskType` is unchanged.** Rev 6's `SHOPIFY_CREATE_PREORDER_PRODUCT`, its payload dataclass, its `QUEUE_MAP` / `HANDLER_TIMEOUT_SECONDS` / `HANDLER_MAP` entries and its `ALTER TYPE task_type_enum` migration are all **removed** — pre-orders ride `TaskType.SHOPIFY_PROCESS_PRODUCTS` with its existing ID-only `ShopifyProcessProductsPayload(workspace_id, requested_by_user_id, sync_item_client_ids)`, sending a one-element list. The existing 900 s handler timeout already covers it.

### State machine

```
QUEUED
  ├─ reconcile by operation tag  (products(query:"tag:managerbeyo-preorder-<operation_id>"))
  └─ else exact-SKU lookup
  → resolve metafield definitions   (one fetch_shopify_metafield_definitions_by_ids call,
                                     only when any entry is addressed by definition_id)
  → build [MetafieldInput!]  (namespace/key/type/value)
        ├─ found     → productUpdate(product{…, metafields}, media)
        └─ not found → productCreate(product{…, metafields}, media)
  → persist shopify_product_id + shopify_media_id + media_status + requested_operation
PRODUCT_CREATED
  → productVariantsBulkUpdate  (sku, price, inventoryItem.tracked = true)
  → persist shopify_variant_id + shopify_inventory_item_id
VARIANT_CONFIGURED
  → validate the SELLER-SELECTED location against Shopify   (always re-run, never skipped)
        fetch_shop_locations → the GID must be present, isActive, and not a fulfillment service
        → persist inventory_location_name
        → on any failure: preorder_inventory_location_invalid, product/variant IDs retained
  → resolve_inventory_item_state  → persist inventory_before_available
  → enable tracking / activate level at the selected location if needed
  → inventorySetQuantities @idempotent(key: <frozen key>), name "available",
                           quantity 1, changeFromQuantity: null
  → persist inventory_result_json + inventory_applied_at
INVENTORY_SET
  → status = SUCCEEDED
```

**The location is not resolved here — it was chosen by the seller and frozen at command time** (R7), together with `inventory_idempotency_key`. This stage only *validates* it. Validation is a cheap idempotent read, so it is **re-run on every attempt** rather than guarded by the stage machine: a location deactivated between attempts must be caught, not skipped.

**Freezing rule.** `inventory_location_id` and `inventory_idempotency_key` are written once, in the task-creation transaction, and are reused verbatim on every retry. Nothing recomputes them. Changing the business's preferred location tomorrow affects only **newly created** pre-orders; a queued or retrying operation keeps the location the seller picked when it was created.

**Never substitute.** If the selected location is gone, inactive, moved to another shop, or is a fulfillment-service location, the worker **fails** with `preorder_inventory_location_invalid`. It does not fall back to a primary location, the first active location, or anything else. Silently relocating stock is an error that looks like success — the exact failure mode this design exists to prevent.

**No dual write.** Exactly one `inventorySetQuantities` call, against exactly one location, per attempt.

**Terminal-status rule.** `SUCCEEDED` requires *all* of: the product exists; SKU, price and variant policy are configured; the media mutation was accepted per policy (or no image was supplied); inventory tracking is enabled; the inventory level is activated **at the selected location**; and `available` is set to exactly `1` there. Anything less is `FAILED` with all Shopify IDs retained.

**R-note — the create→variant duplicate gap.** The SKU is written by `productVariantsBulkUpdate`, *not* by `productCreate`. If `productCreate` succeeds but the variant update fails, a naive retry's SKU lookup finds nothing and creates a **second** product. Two mitigations, both required and both retained from rev 2:
1. Persist `shopify_product_id` and advance to `PRODUCT_CREATED` immediately after `productCreate` returns.
2. For a **lost `productCreate` response**, tag every pre-order product `managerbeyo-preorder-<operation_id>` at creation, and query by that tag at `QUEUED` **before** the SKU lookup. Exactly one hit → adopt. More than one → fail `ambiguous_preorder_product`.

The generic product-sync orchestrator has the same exposure. **Follow-up ticket only** — explicitly out of scope here.

---

## Normalized contracts

### 1. Internal request (`services/commands/shopify/requests/create_shopify_preorder_request.py`)

```python
class ShopifyPreorderMetafieldRequest(BaseModel):
    """One caller-supplied product metafield. See R10 for the three accepted shapes."""
    definition_id: str | None = None   # gid://shopify/MetafieldDefinition/…  (preferred)
    namespace: str | None = None       # defaults to SHOPIFY_PREORDER_METAFIELD_NAMESPACE
    key: str | None = None             # required unless definition_id is given
    type: str | None = None            # required unless a definition supplies it
    value: object                      # stringified on normalization; never lost to float

class ShopifyPreorderProductRequest(BaseModel):
    title: str                        # non-blank after strip
    sku: str                          # non-blank after strip
    price: str                        # decimal string, >= 0, at most 2 dp
    description: str | None = None
    product_category: str | None = None
    tags: list[str] = []
    metafields: list[ShopifyPreorderMetafieldRequest] = []   # e.g. the `quantity` metafield
    image_id: str | None = None       # img_ client id  (preferred)
    image_url: str | None = None      # absolute https:// (externally hosted images)
    image_alt_text: str | None = None

class CreateShopifyPreorderRequest(BaseModel):
    task_id: str
    shop_integration_id: str
    inventory_location_id: str                    # gid://shopify/Location/<digits> — REQUIRED
    idempotency_key: str | None = None            # defaults to task_id
    product: ShopifyPreorderProductRequest
```

**`inventory_location_id` is a required field of the normal request** (rev 6). The seller picks it from the locations selector; there is no override contract, no `acknowledge_not_zettle_synced`, and no integration-level fallback. The wire shape is:

```json
{
  "shopify_preorder": {
    "shop_integration_id": "shpint_…",
    "inventory_location_id": "gid://shopify/Location/99221471562",
    "product": { "…": "…" }
  }
}
```

Validation rules (raised as `ValidationError` via the existing `parse_*` wrapper idiom):
- `price`: `re.fullmatch(r"\d+(\.\d{1,2})?", value)` — validated **as a string**; `decimal.Decimal` used only for the `>= 0` check, then discarded. Never `float`; never `Decimal` in JSONB.
- **`metafields`**: each entry must supply either `definition_id` **or** `key`; `namespace`/`key` are validated against Shopify's charset and length rules (3–255 and 2–64, alphanumeric/hyphen/underscore) when supplied explicitly; `definition_id` must match `^gid://shopify/MetafieldDefinition/\d+$`; duplicate `(namespace, key)` or duplicate `definition_id` entries are rejected (`duplicate_metafield`); `value` may not be `None`. Numeric values keep full precision — a `Decimal`/`int` is stringified, never routed through `float`.
- **There is no product-level `quantity` field.** The inventory quantity travels in the inventory selection (`{location_id, quantity}` per location, rev 9); a `custom.quantity` metafield is ordinary product data (R10). Two different inputs, never crossed.
- `inventory_location_id`: **required, non-blank**, matching `_SHOPIFY_LOCATION_GID_PATTERN` from `process_shopify_products_request.py:10`. A missing or malformed value rejects the request before anything is written. This is the **only** location check that can happen without calling Shopify — ownership, active status and inventory capability are worker-time gates (R7).
- `image_id` and `image_url` are mutually exclusive; at most one; both may be omitted.
- `image_url`: `urlparse` → scheme exactly `https`, non-empty netloc, no userinfo, not a loopback/private host. Rejects `http`, `blob:`, `data:`, `file:`.
- `tags`: strings, stripped, blanks dropped.

Command-time (pre-Shopify, local reads only) rejections:
- Shop integration missing, cross-workspace, not `ACTIVE`, or without a token → `NotFound` / the corresponding error code, before anything is written.
- Malformed `inventory_location_id` → `validation_failed`.

There is **no** "not configured" rejection any more — nothing needs configuring, so the feature can never be disabled for a shop that is otherwise healthy.

### 2. Normalized persisted payload (`domain/shopify/preorder_payloads.py:build_normalized_preorder_payload`)

Pure function, no I/O. Stored verbatim in `normalized_request_json`:

```jsonc
{
  "product": {
    "title": "…",
    "descriptionHtml": "…|null",
    "status": "UNLISTED",
    "productType": "…|null",
    "tags": ["managerbeyo-preorder", "managerbeyo-task-tsk_x", "managerbeyo-preorder-shpsi_y"]
  },
  "variant": {
    "price": "5200.00",                        // caller-supplied verbatim — never derived from quantity
    "inventoryPolicy": "DENY",
    "taxable": false,                          // SHOPIFY_PREORDER_VARIANT_TAXABLE
    "inventoryItem": { "sku": "CustomTC3", "tracked": true, "requiresShipping": true }
  },
  "metafields": [
    { "definition_id": "gid://shopify/MetafieldDefinition/241114906954", "value": "6" },
    { "namespace": "custom", "key": "quantity", "type": "single_line_text_field", "value": "6" },
    { "namespace": "custom", "key": "notes", "type": "single_line_text_field", "value": "…" }
  ],
  "image": { "image_id": "img_x" },            // or {"image_url": "https://…"} or null
  "image_alt_text": "…|null",
  "inventory": {
    "location_id": "gid://shopify/Location/99221471562",  // seller-selected, frozen
    "quantity_name": "available",              // till readiness is available=1, never on_hand=1
    "target_quantity": 2                       // caller-supplied per location — never from a metafield
  },
  "traceability": { "task_id": "tsk_x", "requested_by_user_id": "usr_z", "operation_id": "shpsi_y" }
}
```

`tracked: true` is mandatory — an untracked inventory item cannot hold a quantity, so Zettle would see the product with no stock.

Metafield `value`s are **already stringified at normalization time** so the persisted payload is byte-stable across retries and no numeric precision is lost between enqueue and execution. `namespace`/`key`/`type` are stored exactly as the caller supplied them — entries addressed by `definition_id` are resolved at worker time (R10), because resolving them requires a Shopify call that must not happen in the task transaction.

**Canonical location representation.** The seller-selected GID appears in **both** `normalized_payload_json.inventory.location_id` (as immutable caller intent, alongside the rest of the request snapshot) and the dedicated `ShopifyProductSyncItem.inventory_location_id` column (as the queryable, indexed, non-null execution value). The **column is authoritative** for every code path; the JSON copy exists so the persisted request snapshot is complete and self-describing. A consistency test asserts the two are always equal, so the duplication can never become ambiguity. `inventory.target_quantity` and `quantity_name` are policy constants recorded for audit, not caller-supplied values.

### 3. Worker payload — **unchanged, reused as-is** (rev 7)

```python
@dataclass(frozen=True)
class ShopifyProcessProductsPayload:      # already exists; no change
    workspace_id: str
    requested_by_user_id: str
    sync_item_client_ids: list[str]
```

A pre-order enqueues this with a one-element `sync_item_client_ids`. Still IDs only; the task id and the selected location live on the row, not in the payload. Rev 6's `ShopifyCreatePreorderProductPayload` is deleted.

### 4. Inventory GraphQL document (`services/infra/shopify/inventory_client.py`)

```graphql
mutation PreorderInventorySet($input: InventorySetQuantitiesInput!, $idempotencyKey: String!) {
  inventorySetQuantities(input: $input) @idempotent(key: $idempotencyKey) {
    inventoryAdjustmentGroup {
      createdAt
      reason
      referenceDocumentUri
      changes { name delta quantityAfterChange }
    }
    userErrors { code field message }
  }
}
```

Variables:

```jsonc
{
  "idempotencyKey": "shopify-preorder:shpsi_a1b2c3d:inventory-set:74188390481",
  "input": {
    "name": "available",
    "reason": "correction",
    "referenceDocumentUri": "managerbeyo://preorder/shpsi_a1b2c3d",
    "quantities": [{
      "inventoryItemId": "gid://shopify/InventoryItem/…",
      "locationId": "gid://shopify/Location/74188390481",
      "quantity": 1,
      "changeFromQuantity": null
    }]
  }
}
```

`ignoreCompareQuantity` and `compareQuantity` are **never sent** — both are deprecated in `2026-01` and removed in `2026-04`. `changeFromQuantity: null` is the non-deprecated way to skip the compare check and is the same document `2026-04` will accept.

### 5. Command response

```json
{ "queued": true,
  "preorder_operation_id": "shpsi_…",
  "task_id": "tsk_…",
  "shop_integration_id": "shpint_…",
  "shopify_task_id": "exe_…",
  "inventory_location_id": "gid://shopify/Location/99221471562" }
```

`preorder_operation_id` is the `ShopifyProductSyncItem.client_id` (`shpsi_` prefix, not the deleted `shppre_`). The field name is kept so the frontend contract reads naturally.

The selected location is echoed back so the UI can confirm what was committed. It is never `null` — a pre-order without a location is not a valid request.

`create_task` returns its existing payload plus `"shopify_preorder": { …the above… }` when the section was supplied, and omits the key entirely otherwise.

### 6. Socket.IO terminal event — `shopify.preorder.processed`, workspace room

```json
{ "task_id": "tsk_…",
  "preorder_operation_id": "shpsi_…",
  "shop_integration_id": "shpint_…",
  "status": "succeeded",
  "stage": "inventory_set",
  "requested_operation": "create",
  "shopify_product_id": "gid://shopify/Product/…",
  "shopify_variant_id": "gid://shopify/ProductVariant/…",
  "shopify_inventory_item_id": "gid://shopify/InventoryItem/…",
  "shopify_media_id": "gid://shopify/MediaImage/…",
  "media_status": "READY",
  "inventory": {
    "location_id": "gid://shopify/Location/99221471562",
    "location_name": "Västberga Warehouse",
    "quantity_name": "available",
    "target_quantity": 1,
    "before_available": 0,
    "outcome": "applied"
  },
  "zettle_ready": true,
  "error_code": null, "error_message": null }
```

**`zettle_ready` is retained but redefined** (rev 6): it now means *"successfully provisioned at the location the seller selected"* — i.e. `status == "succeeded"` and `available = 1` was written at `inventory_location_id`. It is no longer a comparison against an integration-level configured location, because there isn't one. The field stays because the frontend uses it as the single "is this ready at the till?" signal, and keeping the name avoids churn in the client. The rev-2 `warnings` array and the rev-5 `outcome_code` are both **removed** — with a seller-selected location there is no partial-provisioning case left to describe.

Nullable media fields are emitted as `null` when no image was supplied. Emitted exactly once, **after** the DB session closes (same placement as `handle_shopify_process_products.py:96`), on every terminal outcome.

**Two events from one handler (rev 7).** `handle_shopify_process_products` now partitions its finished rows by `mode` and emits:
- `shopify.products.synced` — for `product_sync` rows, **byte-identical to today's payload**, so no existing frontend consumer changes;
- `shopify.preorder.processed` — for `preorder` rows, the payload above.

A task's rows are always one mode in practice, so exactly one event fires per task; the partition exists so a hypothetical mixed batch still routes correctly rather than silently mislabelling rows.

---

## Retry and reconciliation behavior per external boundary

| Boundary | Failure mode | Persisted state | Behavior |
|---|---|---|---|
| Tag reconciliation query | transport/throttle | `stage=QUEUED` | Idempotent read; retryable error propagates → `RETRY_SCHEDULED` with backoff |
| Tag reconciliation | >1 product carries the operation tag | `status=FAILED, error_code=ambiguous_preorder_product` | Never auto-resolved |
| Exact-SKU lookup | **>1 distinct product ID matched — a confirmed production condition (R11)** | `stage=QUEUED, status=FAILED, error_code=ambiguous_product_match` | Existing `ShopifyProductLookupAmbiguousError` via `select_exact_variant_match`. **Never auto-selected** by result order, age, price, stock, status or timestamp. No price overwrite occurs. Resolution is a human merging or re-SKU-ing the duplicates in Shopify, then re-enqueueing. Multiple *variants* of the same product ID remain a valid single match |
| `productCreate` | `userErrors` | `stage=QUEUED, status=FAILED, error_code=preorder_product_create_failed` + `error_fields_json` | Retry re-runs tag reconciliation first — an orphan from a lost response is adopted, not duplicated |
| `productCreate` | timeout / lost response | `stage=QUEUED` | The tag query is the reconciliation. Load-bearing anti-duplicate mechanism (criterion 8) |
| `productUpdate` (reuse path) | any | `stage=QUEUED` | Idempotent by construction — same id, same fields |
| Metafield definition lookup | definition GID not found | `stage=QUEUED, status=FAILED, error_code=preorder_metafield_definition_not_found` | Never falls back to a guessed namespace/key — the definition is the contract |
| Metafield definition lookup | transport/throttle | `stage=QUEUED` | Idempotent read; retryable error propagates |
| Metafields (inside create/update) | `userErrors` on a metafield entry | `stage=QUEUED, status=FAILED, error_code=preorder_product_create_failed` (or `…_update_failed`) with `error_fields_json` carrying the `metafields.<n>.<field>` path | Not a separate stage — metafields are written by the product mutation, so a metafield rejection fails the product write atomically. Nothing partial is left behind, and the retry re-sends the identical input |
| Media attach (inside create/update) | `userErrors`, unreachable URL | `stage=QUEUED, status=FAILED, error_code=preorder_media_failed` | The URL is a stable public object URL (R3), so there is no expiry to handle. Shopify's asynchronous media *processing* (`MediaStatus=PROCESSING`) is recorded, not waited on. Over-limit images (20 MB / 25 MP) are rejected locally at command time, before the product exists |
| `productVariantsBulkUpdate` | any | `stage=PRODUCT_CREATED, status=FAILED, error_code=preorder_variant_update_failed` | Product id retained; retry resumes at the variant stage; the mutation is idempotent |
| Location validation | selected GID not present in the shop's locations (wrong shop, or deleted) | `stage=VARIANT_CONFIGURED, status=FAILED, error_code=preorder_inventory_location_invalid` | **Fails before any inventory mutation.** All product/variant IDs retained. **Never substitutes another location.** This is also the check that stops a frontend-supplied GID belonging to a different merchant's shop |
| Location validation | selected location is inactive, or is a fulfillment-service location | `stage=VARIANT_CONFIGURED, status=FAILED, error_code=preorder_inventory_location_invalid` | Same. Correction is a new pre-order (or a future explicit re-target workflow), never a silent switch |
| Location validation | transport error | `stage=VARIANT_CONFIGURED` | Retryable; validation re-runs next attempt against the **same** frozen location |
| **Every retry** | — | location + key frozen since command time | Validation re-runs (cheap idempotent read, catches drift); the persisted `inventory_location_id` and `@idempotent` key are reused verbatim and are **never** recomputed |
| `resolve_inventory_item_state` | any | `stage=VARIANT_CONFIGURED` | Idempotent read; `before_available` is re-read on each attempt and the latest reading is the audited one |
| `enable_inventory_tracking` / `activate_inventory_at_location` | any | `stage=VARIANT_CONFIGURED, status=FAILED` | Both idempotent; retry re-reads state first. Activation targets the selected location only |
| `inventorySetQuantities` | `userErrors` (typed, exposes `code`) | `stage=VARIANT_CONFIGURED, status=FAILED, error_code=preorder_inventory_set_failed` | Retry re-sends the identical document with the identical `@idempotent` key against the identical location |
| `inventorySetQuantities` | timeout / lost response | `stage=VARIANT_CONFIGURED` | **Three independent protections, no reconciliation query needed:** (1) the absolute set is naturally replay-safe — setting to `1` twice yields `1`; (2) the same `@idempotent` key lets Shopify collapse a duplicate delivery; (3) the resumable stage machine bounds what is re-run |
| Whole task | `max_try=3` exhausted | `ExecutionTask.state=FAIL`; operation stays non-successful with all IDs | Recoverable by enqueueing a new task for the same operation id; the stage machine resumes with the frozen location and key. No Shopify resource is deleted |

**Compensation policy: none.** No stage ever deletes a Shopify product or media object.

### Error taxonomy → `error_code`

`validation_failed`, `preorder_not_allowed_for_task_type`, `preorder_role_not_permitted`, `missing_shop_integration`, `shop_not_active`, `missing_access_token`, `missing_required_scope`, `image_not_found`, `image_url_invalid`, **`duplicate_metafield`**, **`preorder_metafield_definition_not_found`**, **`preorder_metafield_definition_lookup_failed`**, `ambiguous_preorder_product`, `ambiguous_product_match`, `preorder_product_create_failed`, `preorder_product_update_failed`, `preorder_media_failed`, `preorder_variant_update_failed`, **`preorder_inventory_location_invalid`** (the single rev-6 code covering "the seller-selected location is not present in this shop, is inactive, or cannot hold inventory" — it replaces rev 5's `preorder_inventory_location_not_zettle_synced`, `preorder_zettle_location_not_configured`, `preorder_zettle_location_invalid`, `preorder_zettle_location_unresolved` and `location_not_in_shop`), `inventory_item_unresolved`, `preorder_inventory_activate_failed`, `preorder_inventory_set_failed`, plus the transport codes `graphql_client.py` already produces (`timeout`, `connection_error`, `transport_error`, `rate_limited`, `server_error`, `auth_error`, `validation_error`, `throttled`, `graphql_errors`, `missing_data`).

The rev-2 warning code `inventory_location_not_default` and the rev-5 `outcome_code` field are both **removed** — with a seller-selected location, an operation either provisions where it was told to or fails.

---

## Files to add or modify

### Add

| Path | Purpose |
|---|---|
| `app/beyo_manager/domain/shopify/preorder_policy.py` | fixed product policy — `PREORDER_PRODUCT_STATUS = "UNLISTED"`, `PREORDER_INVENTORY_POLICY = "DENY"`, `PREORDER_REQUIRES_SHIPPING = True`, `PREORDER_INVENTORY_TRACKED = True`, `PREORDER_INVENTORY_QUANTITY_NAME = "available"` (rev 9: there is **no** quantity constant — the quantity is caller-supplied per location; the policy only fixes the quantity *name*), and `build_preorder_tags(task_id, operation_id)`. **No merchant-specific location GID, definition GID, SKU or price may appear in this file or anywhere else in `domain/` or `services/infra/`.** |
| `app/beyo_manager/domain/shopify/preorder_payloads.py` | `build_normalized_preorder_payload` — pure normalizer |
| `app/beyo_manager/domain/shopify/preorder_metafields.py` | pure: `normalize_preorder_metafields(entries)` (validation, stringification, duplicate detection) and `build_metafield_inputs(normalized, resolved_definitions)` → `[MetafieldInput!]` (R10) |
| `app/beyo_manager/domain/shopify/product_sync_stages.py` | `should_run_stage(current, candidate)` + stage ordering — pure. Named for the shared core because **both modes** use it |
| `app/beyo_manager/domain/shopify/preorder_idempotency.py` | `build_inventory_idempotency_key(operation_client_id, location_gid)` — pure, deterministic (R8) |
| `app/beyo_manager/domain/shopify/preorder_location.py` | pure **validation** policy (rev 6 — no longer a resolution hierarchy): `is_selectable_location(location) -> bool` — `isActive and not isFulfillmentService` — plus `assert_location_selectable(selected_gid, shop_locations)` raising `preorder_inventory_location_invalid`. Shared by the worker validator and, in spirit, by the frontend's selector filter |
| `app/beyo_manager/services/commands/shopify/requests/create_shopify_preorder_request.py` | pydantic request + parser for the pre-order section |
| `app/beyo_manager/services/commands/shopify/_create_preorder_sync_item_in_session.py` | the subordinate helper `create_task` calls: resolve the shop, validate locally, normalize, write **one `ShopifyProductSyncItem` with `mode=preorder`**, write the integration event, enqueue `SHOPIFY_PROCESS_PRODUCTS`. **The only place permitted to set `mode=preorder` or the absolute-inventory target.** No commit, no dispatch |
| `app/beyo_manager/services/commands/shopify/enqueue_shopify_preorder_product.py` | `maybe_begin` owner wrapper for standalone/retry use |
| `app/beyo_manager/services/tasks/shopify/_product_media_resolver.py` | worker-time image-URL resolution (S3 presign vs external), fresh per attempt. Named for the shared core — usable by product sync once it gains an image field |
| `app/beyo_manager/services/tasks/shopify/_preorder_location_validator.py` | worker-side validation of the **frozen, seller-selected** location: `fetch_shop_locations` → present + `isActive` + not a fulfillment service → returns the name for the socket payload. **Re-run every attempt; never resolves or substitutes** |
| `migrations/versions/<rev>_add_preorder_columns_to_shopify_product_sync_items.py` | the ~14 additive columns, 2 new enum types, the partial unique index and the CHECK constraint. **No new table** |
| `migrations/versions/<rev>_add_preorder_to_shopify_integration_event_type.py` | `ALTER TYPE … ADD VALUE IF NOT EXISTS 'preorder'` |
| test files | see Validation plan |

**Deleted from rev 6's Add list:** `preorder_results.py`, `shopify_preorder_operation.py`, `_preorder_operation_writes.py`, `preorder_product_client.py` (folded into the shared `product_sync_client.py` — see Modify), `_preorder_orchestrator.py` (folded into `_product_sync_orchestrator.py`), `handle_shopify_create_preorder_product.py` (the existing handler is reused), the `create_shopify_preorder_operations` migration and the `task_type_enum` migration. Nine files down to six, and one migration fewer.

### Modify

| Path | Change |
|---|---|
| `app/beyo_manager/config.py` | add `shopify_preorder_metafield_namespace: str = Field(default="custom", alias="SHOPIFY_PREORDER_METAFIELD_NAMESPACE")` and `shopify_preorder_variant_taxable: bool = Field(default=False, alias="SHOPIFY_PREORDER_VARIANT_TAXABLE")` (R11 — observed `false`, kept configuration-driven rather than assumed universal). **`SHOPIFY_APP_SCOPES` is not touched.** |
| `app/beyo_manager/services/infra/shopify/metafield_definition_client.py` | **no change** — `fetch_shopify_metafield_definitions_by_ids` is reused as-is; it already selects `namespace`, `key`, `type { name }` and `validations` |
| `app/beyo_manager/domain/shopify/enums.py` | `ShopifyProductSyncModeEnum`, `ShopifyProductSyncStageEnum`, `ShopifyIntegrationEventTypeEnum.PREORDER` |
| `app/beyo_manager/models/tables/shopify/shopify_product_sync_item.py` | the ~14 additive columns, the partial unique index and the CHECK constraint |
| `app/beyo_manager/domain/execution/enums.py` | **no change** (rev 7 — no new task type) |
| `app/beyo_manager/domain/execution/payloads/shopify.py` | **no change** (rev 7 — `ShopifyProcessProductsPayload` is reused) |
| `app/beyo_manager/services/infra/execution/task_router.py` | **no change** |
| `app/beyo_manager/services/infra/execution/worker_base.py` | **no change** — the existing `shopify_process_products: 900` timeout covers both modes |
| `app/beyo_manager/workers/shopify_worker.py` | **no change** |
| `app/beyo_manager/services/tasks/shopify/handle_shopify_process_products.py` | partition finished rows by `mode` and emit `shopify.products.synced` (unchanged payload) and/or `shopify.preorder.processed`; carry `attempt_count` bookkeeping |
| `app/beyo_manager/services/tasks/shopify/_product_sync_orchestrator.py` | **the shared core.** Becomes staged (`should_run_stage`, persist-before-next-call), gains operation-tag reconciliation before the SKU lookup (**fixes the lost-response duplicate bug for product sync too**), media attach, variant policy, metafield-definition resolution, and a single mode branch at the inventory step: additive ledger (`product_sync`) vs absolute set (`preorder`) |
| `app/beyo_manager/services/commands/shopify/process_shopify_products.py` | `ctx.session.begin()` → `maybe_begin` so the shared write path can run inside `create_task`'s transaction; set `mode=product_sync` explicitly |
| `app/beyo_manager/services/commands/shopify/_product_sync_normalizer.py` | accept the pre-order single-shop shape alongside the existing fan-out |
| `app/beyo_manager/services/infra/shopify/inventory_client.py` | add `fetch_primary_location` (singular `location` query, `id` omitted); extend `GET_SHOP_LOCATIONS_QUERY` with `shipsInventory` (**not** `fulfillsOnlineOrders`, and **not** the deprecated `isPrimary`); add `set_inventory_quantity` with the `@idempotent` document above |
| `app/beyo_manager/services/infra/shopify/product_sync_client.py` | **absorbs rev 6's separate `preorder_product_client.py`**: add the `media: [CreateMediaInput!]` argument and inline `metafields` to `create_shopify_product` / `update_shopify_product`, add `find_product_by_operation_tag`, add variant-policy fields to the bulk-variant call, and return `metafields(first: N) { nodes { id namespace key type } }` so writes are observable in logs. Existing callers pass no media/metafields/policy and behave exactly as today |
| `app/beyo_manager/services/infra/shopify/graphql_client.py` | R6: `ShopifyGraphQLUserErrorsError`, optional `error_code=` override, retained `{field, message, code}` — fully backwards compatible |
| `app/beyo_manager/errors/external_service.py` | the new exception class |
| `app/beyo_manager/models/tables/shopify/shopify_shop_integration.py` | **no change** (rev 6 — the column is gone) |
| `app/beyo_manager/domain/shopify/results.py` + `serializers.py` | add `ships_inventory` and **`is_fulfillment_service`** to `ShopifyLocationResult` (currently `location_id`, `name`, `is_active` only) so the selector can filter to inventory-capable locations |
| `app/beyo_manager/services/infra/shopify/inventory_client.py` (locations query) | extend `GET_SHOP_LOCATIONS_QUERY` with `shipsInventory` and `isFulfillmentService`, and surface both through `fetch_shop_locations` — used by both the selector endpoint and the worker validator |
| `app/beyo_manager/services/queries/shopify/get_shopify_locations.py` | pass the two new booleans through; **this is the endpoint the frontend's location selector reads.** No new route is added |
| `app/beyo_manager/routers/api_v1/shopify.py` | **no change** (rev 6 — the `zettle-location` route is gone) |
| `app/beyo_manager/services/commands/tasks/requests/__init__.py` | `ShopifyPreorderSectionInput` + `shopify_preorder: … \| None = None` on `CreateTaskRequest` |
| `app/beyo_manager/services/commands/tasks/create_task.py` | inside the existing `maybe_begin`, after `task.client_id` exists: validate task type + role, call the subordinate helper, add the result to the return dict. `pending_events` untouched. |
| `app/beyo_manager/models/__init__.py` | register the new table module |
| `app/beyo_manager/models/__init__.py`, `client_id_prefix_map.md`, `models/tables/README.md` | **no change** (rev 7 — `ShopifyProductSyncItem`/`shpsi` is already registered) |
| `architecture/57_shopify_integration.md` | new "Flow 4 — Pre-order product provisioning" section: mutation sequence, stage machine, Zettle-location contract, idempotency strategy, partial-provisioning semantics, `create_task` integration point, API-version upgrade notes, new Rules |
| `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_preorder_product_20260727.md` (new) | see the handoff section below |

---

## Frontend handoff contract

**The seller selects the inventory location.** Rev 5's read-only field, "setup required" state and advanced-override path are all removed.

**Location selector — the standard and only path:**

1. Load locations for the selected Shopify integration from the existing endpoint: `GET /api/v1/integrations/shopify/locations?shop_integration_ids=shpint_…`.
2. Show only **active, inventory-capable** locations — `is_active === true && is_fulfillment_service === false`. Inactive and fulfillment-service locations must not be selectable; the backend rejects them at worker time, so offering them only produces a late failure.
3. Display the location **name** plus a stable identifying detail (the GID, or its trailing numeric id) so two similarly named warehouses are distinguishable.
4. Let the seller select the intended location.
5. **Require a selection** before the Shopify pre-order section can be submitted.
6. Send the chosen Shopify Location GID as `shopify_preorder.inventory_location_id`.
7. Preserve the selection in the form while the task request is being prepared, so a validation error elsewhere on the form does not silently clear it.

**Defaulting.** `Västberga Warehouse` / `gid://shopify/Location/99221471562` will appear as an available option and **may** be pre-selected if the product requirements define a defaulting policy — but it must remain user-changeable, and **the GID must not be hard-coded in reusable frontend code.** Prefer a data-driven default (last used for this shop, or the single option when a shop has exactly one selectable location) over a literal.

**Reading the result.** `zettle_ready: true` means the product is provisioned with `available = 1` at the location the seller picked. The terminal event's `inventory` block echoes `location_id` and `location_name`, so the UI can state *where* the stock landed rather than just that it succeeded.

**Error states worth distinguishing in the UI:**
- `preorder_inventory_location_invalid` — the selected location is gone, inactive, or not inventory-capable. Actionable: create a new pre-order against a valid location.
- `ambiguous_product_match` — merchant data problem: two Shopify products share this SKU. Not fixable in ManagerBeyo; someone must merge or re-SKU them in Shopify (this **will** occur — see R11).

Also documented: the optional task-create pre-order payload, the immediate queued response including the committed `inventory_location_id`, the asynchronous completion event with the full `inventory` block, recoverable vs terminal error codes, and how to deep-link to the resulting Shopify product in Admin.

---

## Implementation plan

### Phase 0 — Dev-store verification spike (hard gate, no production code)

Each item records an outcome in the Review log. The plan stays `under_construction` until all sixteen are recorded. Gates 1–10 are the concrete tests required by the rev-5 evidence review; 11–16 carry over from rev 4.

**Product visibility**
1. A newly created **`UNLISTED`** product **appears in Zettle**.
2. That same product **does not appear on the Online Store**. Failure here — and only failure here — triggers the publication contingency (`publishableUnpublish` + `read_publications`/`write_publications` + reauthorization) and a scope-change approval.

**Location**
3. Inventory written at **`gid://shopify/Location/99221471562` (Västberga Warehouse)** appears in Zettle. This confirms the location that should be the frontend's **default selector option** — it is no longer written into any backend configuration.
4. Inventory written **only to another active Shopify location does not** make the item available in Zettle — confirming why the seller's choice matters and must be recorded, not inferred.
4a. The locations endpoint **returns Västberga Warehouse** for this shop, with `is_active: true` and `is_fulfillment_service: false`.
4b. **Inactive locations are not selectable** — they are returned by the endpoint (it passes `includeInactive: true`) but filtered out of the selector, and rejected by the worker if forced.
4c. **The backend rejects a location belonging to a different Shopify shop** — submit a valid GID from another shop and confirm `preorder_inventory_location_invalid` with no inventory written anywhere.
4d. **The worker fails safely if the selected location is deactivated after task creation** — deactivate between enqueue and execution, confirm `preorder_inventory_location_invalid`, product/variant IDs retained, and no fallback location used.
4e. **Inventory is written only to the selected location** — verify every other location's quantity is untouched.
4f. **Retries never change the selected location** — force a failure after `VARIANT_CONFIGURED`, retry, confirm the same GID and the same idempotency key.
4g. **A newly created pre-order can use a newly selected location**, while an **existing queued operation retains its original frozen location** — run both concurrently and confirm they land in different places.

**Inventory semantics**
5. **`available = 1` is the till-ready state.**
6. **`on_hand = 1` with `committed = 1` and `available = 0` is *not* till-ready** — reproducing the older `CustomTC3` product's state and confirming the readiness rule must be stated in `available`.

**Metafields**
7. **`custom.quantity = "6"` with type `single_line_text_field` remains independent from the inventory target of `1`** — the product shows one available unit regardless of the metafield value. Confirm `SHOPIFY_PREORDER_METAFIELD_NAMESPACE` (default `custom`) matches the real definition, and that all three caller shapes are accepted inside `productCreate`/`productUpdate` — including `type` omitted against definition `gid://shopify/MetafieldDefinition/241114906954`.

**Ambiguity**
8. A **duplicate exact-SKU lookup returns an ambiguity failure rather than silently selecting a product.** Reproduce against the real `CustomTC3` duplicates and confirm no product, price or inventory write occurs.

**Price**
9. **The supplied variant price is transferred to Zettle unchanged** — no rounding, no currency drift, and no relationship to `custom.quantity`.

**Variant policy**
10. Confirm the intended values or preservation behavior for **`inventoryPolicy`**, **`requiresShipping`** and **`taxable`**. Specifically: decide whether `taxable: false` is a merchant-specific pre-order tax policy (→ keep it configuration-driven via `SHOPIFY_PREORDER_VARIANT_TAXABLE`) or a rule that should be caller-supplied per pre-order.

**API contract (carried over from rev 4)**
11. Shopify's media fetcher can retrieve an image from a **presigned S3 GET URL** produced by `S3Client.generate_presigned_get_url`; record the returned `MediaStatus`.
12. The exact `inventorySetQuantities` document is accepted by `2026-01`, **including the optional `@idempotent` directive** and `changeFromQuantity: null`, with **no** `ignoreCompareQuantity`.
13. Repeating the same inventory mutation with the **same idempotency key** is accepted safely; record the observed behavior (collapsed vs re-executed) and confirm the key format/length is accepted.
14. Confirm the `changeFromQuantity` skip-the-check behavior on `2026-01` so the `2026-04` upgrade note is accurate rather than assumed.
15. *(Informational only, no longer load-bearing)* Compare the singular `location` query (`id` omitted) and `shipsInventory` against the verified Västberga GID, and record whether an inferred default would have produced the right answer — useful for judging whether a future server-side default is worth adding.
16. Confirm `UNLISTED` is accepted by `ProductCreateInput.status` **and** `ProductUpdateInput.status` on this store, and that an existing `UNLISTED` product can be updated without its status being coerced.

Record the observed **product-sync and stock-sync behavior**, not just the documented behavior — merchant-specific Zettle configuration can change the result.

### Phase 1 — Domain, model, migrations

12. Add `ShopifyProductSyncModeEnum`, `ShopifyProductSyncStageEnum` and `ShopifyIntegrationEventTypeEnum.PREORDER`. **No `TaskType` change.**
13. Add `preorder_policy.py`, `product_sync_stages.py`, `preorder_payloads.py`, `preorder_metafields.py`, `preorder_idempotency.py`, `preorder_location.py` — all pure, unit-tested in this phase.
14. Extend the `ShopifyProductSyncItem` model with the additive columns, the partial unique index and the CHECK constraint. **No new model, no registration, no prefix-map entry, no change to `shopify_shop_integrations`.**
15. Write the two additive migrations (columns + 2 enum types + index + constraint; `ALTER TYPE … ADD VALUE IF NOT EXISTS` for the event-type enum — never a destructive enum rebuild). Verify on a copy of production data that the partial index builds cleanly against existing rows (all of which have `task_id IS NULL`).

### Phase 2 — Infra clients

17. Extend `graphql_client.raise_for_graphql_user_errors` per R6 and add `ShopifyGraphQLUserErrorsError`. **Re-run the full existing Shopify test suite before proceeding** — this touches every current caller.
18. Extend `inventory_client.py`: `fetch_primary_location`, `shipsInventory` on the locations query, and `set_inventory_quantity` with the `@idempotent` + `changeFromQuantity` document.
19. Extend `product_sync_client.py` in place: `media` + inline `metafields` on create/update, `find_product_by_operation_tag`, variant-policy fields, metafield selection set. **Existing callers must be byte-identical in behaviour when they pass none of the new arguments** — gate on the existing product-sync tests before continuing.
20. **No `preorder_product_client.py`.** Every document goes through `execute_shopify_graphql`; no `httpx`; no GraphQL string outside `services/infra/shopify/`.

### Phase 3 — Commands and request

21. Add `create_shopify_preorder_request.py` with the full validation rule set.
22. Surface `ships_inventory` and `is_fulfillment_service` through `fetch_shop_locations`, `ShopifyLocationResult`, the serializer and `get_shopify_locations`, so the **existing** locations endpoint can back the frontend selector. **No new route, no admin command, no rollout prerequisite.**
23. Change `process_shopify_products.py` from `ctx.session.begin()` to `maybe_begin`, and set `mode=ShopifyProductSyncModeEnum.PRODUCT_SYNC` explicitly on the rows it creates. Behaviour otherwise unchanged; gate on the existing integration tests.
24. Add `_create_preorder_sync_item_in_session.py`: single-shop resolution (`workspace_id` + `is_deleted is False` + `status == ACTIVE` + non-blank token), local scope pre-check via `has_all_required_scopes(("write_products", "read_products", "read_locations", "write_inventory"), …)`, **persist `mode=preorder`, `task_id`, the seller-selected `inventory_location_id` and the derived `inventory_idempotency_key`**, image reference resolution to an `img_` id (existence + not-deleted only — **no presigning here**), normalization, `pg_insert(...).on_conflict_do_nothing` against the **partial unique index** `(shop_integration_id, task_id) WHERE mode='preorder'` + re-select (the `_inventory_sync._claim_ledger_row` idiom at lines 226-247) so a replay adopts the existing row, `create_shopify_integration_event(PREORDER, INFO)`, then `create_instant_task(TaskType.SHOPIFY_PROCESS_PRODUCTS, ShopifyProcessProductsPayload(..., sync_item_client_ids=[row.client_id]), event_client_id=event.client_id)`. Returns IDs + the selected location. **Never commits, never dispatches.**
25. Add `enqueue_shopify_preorder_product.py` — `maybe_begin` owner wrapper.

### Phase 4 — Worker orchestration

26. Add `_product_media_resolver.py`: load the `Image` row, branch on `storage_provider` — `S3` → `storage.public_url(image.image_url)`; `EXTERNAL` / `SHOPIFY` → verbatim — validate `https`, return the URL. Composed at worker time so a bucket or CDN change cannot strand queued rows; never persisted. **No presigning** (R3).
27. Add `_preorder_location_validator.py`: fetch the shop's locations, assert the **frozen** `inventory_location_id` is present, `isActive`, and not a fulfillment service; persist `inventory_location_name`; **fail with `preorder_inventory_location_invalid` rather than substitute**. Runs on every attempt.
28. **Restructure `_product_sync_orchestrator.py` into the shared staged core** — this is the highest-risk step in the plan, because it touches live product-sync behaviour:
    a. Introduce the stage machine (`should_run_stage`, persist IDs + stage before the next network call) for **both** modes.
    b. Add operation-tag reconciliation before the exact-SKU lookup — **this is what fixes the lost-`productCreate`-response duplicate bug for product sync**.
    c. Add media attach, inline metafields (with one batched `fetch_shopify_metafield_definitions_by_ids` for `definition_id`-addressed entries) and variant policy — all no-ops when the payload omits them.
    d. Branch **once**, at the inventory step: `product_sync` → the existing additive `sync_inventory_adjustments` ledger path, untouched; `preorder` → validate location, read `before_available`, absolute `set_inventory_quantity`.
    e. Keep `FOR UPDATE`, the `PROCESSING`/`SUCCEEDED` early-return, `attempt_count`, and the existing exception classification: `ShopifyGraphQLNonRetryableError` / ambiguity errors → `FAILED` with a stage-specific code; **`ShopifyGraphQLRetryableError` propagates** so the execution layer retries with backoff.
    f. **Never recompute the location or the idempotency key.**
29. Extend `handle_shopify_process_products.py`: partition finished rows by `mode` and emit `shopify.products.synced` (payload unchanged) and/or `shopify.preorder.processed` after the session closes. **No `QUEUE_MAP` / `HANDLER_TIMEOUT_SECONDS` / `HANDLER_MAP` change.**

### Phase 5 — create_task integration

30. Add `ShopifyPreorderSectionInput` to `CreateTaskRequest` (no `task_id` field, no `mode` field — mode is never caller-settable).
31. In `create_task`, inside the existing `maybe_begin` and after `await ctx.session.flush()` has assigned `task.client_id` (`create_task.py:146`): reject the section when `request.task_type is not TaskTypeEnum.PRE_ORDER` (`ValidationError`) or when `ctx.role_name` is outside `{admin, manager, seller}` (`PermissionDenied`), then call the subordinate helper with `task_id=task.client_id`. Add `"shopify_preorder": {…}` to the return dict. Do not touch the `pending_events` block.

### Phase 6 — Docs and handoff

32. Update `architecture/57_shopify_integration.md`, including the API-version upgrade notes for `2026-04`.
33. Write the frontend handoff per the contract above, including the manual dev-store checklist.

### Phase 7 — Tests

34. Implement the full matrix below.

---

## Risks and mitigations

- Risk: the `UNLISTED` product still reaches the storefront — either via an `autoPublish` sales channel, or because `UNLISTED` products remain retrievable through the Storefront API by direct handle/id reference.
  Mitigation: **Phase 0 gate 2 is hard**, and `UNLISTED` materially reduces the exposure versus rev 4's `ACTIVE` (no search, no collections, no recommendations by definition). The contingency (`publishableUnpublish` + two new scopes + reauthorization) is a scope change to approve, not to absorb silently.
- Risk: **duplicate exact SKUs block real pre-orders in production.** This is not hypothetical — `CustomTC3` already has two products (R11), so the ambiguity path will fire on live data, and a seller will see a pre-order fail for a reason they cannot fix themselves.
  Mitigation: failing loudly is the correct behavior — the alternative silently overwrites one of two very different prices. The error code is specific (`ambiguous_product_match`) and the frontend handoff documents it as a merchant-data problem requiring a human to merge or re-SKU the duplicates in Shopify. Worth raising with the merchant **before** rollout: an audit of how widespread duplicate SKUs are will predict how often this fires.
- Risk: **the seller picks a location Zettle does not read**, so the product never reaches the till even though the operation reports success.
  Mitigation: this is the residual cost of moving the choice to the user, and it is accepted deliberately — the alternative (rev 5) required configuration that could equally be wrong, and could not be corrected without a backend change. Mitigations: the selector shows only active, inventory-capable locations; the Phase 0-verified Västberga location is the recommended default; and the terminal event echoes `location_name` so the seller can see where stock landed rather than inferring it. **`zettle_ready` now asserts "provisioned where you asked", not "provisioned where Zettle reads"** — the plan is explicit about that narrower meaning rather than overclaiming.
- Risk: a location valid at task-creation time is deactivated before the worker runs.
  Mitigation: validation is re-run on **every** attempt rather than skipped by a stage guard, so drift is caught rather than silently written through. The operation fails with a precise code and keeps its product/variant IDs.
- Risk: setting inventory to an absolute `1` destroys existing stock on a reused SKU.
  Mitigation: **explicitly chosen behavior.** `inventory_before_available` and `compare_protection: "explicitly_bypassed"` are recorded on every row, making each overwrite auditable and hand-reversible.
- Risk: the `@idempotent` key format is rejected, or Shopify's replay semantics differ from the documentation.
  Mitigation: Phase 0 gates 8–9. The absolute set is replay-safe *without* the directive, so a Phase 0 surprise degrades gracefully rather than blocking the feature.
- ~~Risk: Shopify cannot fetch the presigned S3 URL~~ — **retired in rev 8.** The bucket is public
  and the object URL was fetched anonymously; WebP is an accepted Shopify format. The
  `stagedUploadsCreate` fallback is dropped. Residual: an image exceeding 20 MB or 25 MP is
  rejected by Shopify — mitigated by validating locally at command time from the `width_px` /
  `height_px` / `file_size_bytes` already stored on `images`.
- Risk: a lost `productCreate` response duplicates the product because the SKU is only written by the *next* mutation.
  Mitigation: operation-tag reconciliation before every create, plus persisting the product id before the variant mutation.
- Risk: **converging regresses live product sync.** This is the dominant new risk in rev 7 and it is real — `_product_sync_orchestrator.py` and `product_sync_client.py` are in production use, and Phase 4 step 28 restructures the former.
  Mitigation: every new capability is **opt-in by payload** — a `product_sync` row omits media, metafields-by-definition, variant policy and the absolute-inventory branch, so its path through the shared core is the existing path plus stage bookkeeping. Three gates: (1) Phase 2 and Phase 3 each stop until the pre-existing Shopify suite is green; (2) a characterisation test captures the exact GraphQL documents and variables product sync emits today and asserts they are unchanged after the restructure; (3) the `mode` branch is a **single** point in the orchestrator, not scattered conditionals. Adopting the stage machine for product sync is a deliberate behaviour change — it is what fixes its duplicate bug — and is covered by its own tests rather than assumed harmless.
- Risk: **absolute inventory set leaks into the general product route**, letting an HTTP caller wipe stock.
  Mitigation: `mode` is absent from every HTTP request schema; only `_create_preorder_sync_item_in_session` writes `preorder`; a guard test asserts no request model exposes `mode` or an inventory-mode field, and that `process_shopify_products` only ever produces `product_sync` rows.
- Risk: the shared table accumulates pre-order-only nullable columns that a product-sync reader misinterprets.
  Mitigation: the CHECK constraint makes a malformed pre-order unrepresentable, and every pre-order-only column is documented as such in the schema table. Accepted as the deliberate cost of convergence (R12).
- Risk: the R6 change to `raise_for_graphql_user_errors` regresses product sync or inventory sync.
  Mitigation: the new exception is a **subclass** and the default `error_code` is unchanged; Phase 2 gates on the existing Shopify suite passing.
- Risk: the `2026-04` upgrade breaks the inventory mutation.
  Mitigation: the document this plan ships is **already `2026-04`-shaped** — `@idempotent` present, `ignoreCompareQuantity`/`compareQuantity` never sent. The remaining upgrade work is verifying the `changeFromQuantity` contract and auditing the additive product-sync path, both in R5's checklist.
- Risk: `create_task` becomes coupled to Shopify.
  Mitigation: `create_task` imports exactly one function and passes a dict; it never imports a GraphQL client or `execute_shopify_graphql`.
- Risk: PII leaking into integration events or logs.
  Mitigation: this feature sends **no** customer data to Shopify. `metadata_json` and log lines carry IDs, stage, outcome and error codes only, enforced by a test inspecting emitted metadata keys.

---

## Validation plan

### Automated

**Pure domain**
- `test_preorder_payloads.py`: normalization; **`status: "UNLISTED"`**; `inventoryPolicy: "DENY"`; `requiresShipping: true`; `tracked: true`; `taxable` follows `SHOPIFY_PREORDER_VARIANT_TAXABLE`; `barcode` absent unless supplied; tag construction; **price preserved byte-identically as a string** (`"5200.00"` in → `"5200.00"` out, never `5200.0`); image reference stored as id/url and **never** as a signed URL; the resolved location is absent from the normalized payload; **`inventory.quantity_name == "available"`**; **`inventory.target_quantity` is always `1` regardless of any `quantity` metafield value**; **no `quantity` field is read from the request**.
- `test_preorder_price_independence.py`: property-style — for a grid of prices and `custom.quantity` values (including the real `("31200.00", "4")` and `("5200.00", "6")` pairs), the normalized variant price **always equals the input** and is never a product or quotient of the two. Guards against a future contributor "helpfully" deriving one from the other.
- `test_preorder_metafields.py`: all three caller shapes normalize correctly **using the real definition** (`gid://shopify/MetafieldDefinition/241114906954`, `custom` / `quantity` / **`single_line_text_field`**); `namespace` defaults to the configured value in the shorthand shape; `type` is omitted when a definition supplies it and required otherwise; **a `single_line_text_field` quantity of `"6"` is preserved as the string `"6"`** and never coerced to a number; **values are stringified without passing through `float`** (a `Decimal("19.99")` and a large int survive exactly); lists/dicts are compact-JSON encoded; duplicate `(namespace, key)` and duplicate `definition_id` are rejected with `duplicate_metafield`; an entry with neither `definition_id` nor `key` is rejected; namespace/key charset and length rules are enforced; `build_metafield_inputs` merges resolved definitions onto definition-addressed entries and raises `preorder_metafield_definition_not_found` for an unresolved GID.
- `test_product_sync_identity.py` (extended — **evidence-driven**): fixtures built from the real `CustomTC3` response. Two distinct product IDs sharing one exact SKU → `ShopifyProductLookupAmbiguousError`; **two variants of the same product ID → a single valid match, not an error**; three-plus distinct products → still one ambiguity error; the raise happens regardless of which product appears first, is newer, is cheaper, has stock, or has a different status — asserted by permuting the fixture order and mutating each of those attributes.
- `test_product_sync_stages.py`: every `(current, candidate)` stage pair resolves to the correct skip/run decision across the four stages; **location validation is never stage-guarded** — asserted by confirming the inventory stage always calls the validator regardless of entry stage.
- `test_preorder_idempotency.py`: **deterministic key generation**; the same `(operation_id, location)` always yields the same key; **different operation ids yield different keys**; the key is unchanged when attempt count / execution-task id / timestamp / worker id vary; the location GID's numeric suffix is used so the key contains no `/`; the key round-trips from the two persisted identifiers.
- `test_preorder_location.py`: `is_selectable_location` is `true` only for `isActive and not isFulfillmentService` — asserted across all four combinations; `assert_location_selectable` raises `preorder_inventory_location_invalid` when the GID is absent from the shop's list, inactive, or a fulfillment-service location, and passes otherwise; **the function has no code path that returns a different location than the one passed in** (asserted by returning only `None`/raising, never a location).

**Infra clients**
- `test_product_sync_client.py` (extended): create-with-media; update-with-media; operation-tag lookup with 0/1/2 hits; variant policy fields; `userErrors` field paths retained; **`metafields` is sent inside the `productCreate`/`productUpdate` input**; **the pre-order path issues no `metafieldsSet` document**; a metafield `userErrors` entry surfaces its `metafields.<n>.<field>` path; **a call that passes no media/metafields/policy emits the exact document it emits today** (part of the characterisation suite).
- `test_inventory_client.py` (extended): **the `inventorySetQuantities` document contains `@idempotent(key: $idempotencyKey)`**; the variables send `changeFromQuantity` explicitly and send **neither** `ignoreCompareQuantity` **nor** `compareQuantity`; `name: "available"`; `reason` present; `referenceDocumentUri` present; typed `InventorySetQuantitiesUserError` selects `code`; `fetch_primary_location` omits the `id` argument; the locations query selects `shipsInventory` and **not** the deprecated `isPrimary`.
- `test_graphql_client.py` (extended): the new subclass; default `error_code` unchanged; `error_code=` override; retained `{field, message, code}`.

**Worker**
- `test_preorder_image_resolver.py`: S3 → presigned; `EXTERNAL` → verbatim; deleted image → `image_not_found`; non-https resolved URL → `image_url_invalid`; a fresh URL is minted on each call.
- `test_product_sync_orchestrator.py` (pre-order mode cases):
  - full success (create path) → `SUCCEEDED`, `zettle_ready: true`;
  - full success (reuse path with price overwrite) → no second product;
  - **a `custom.quantity` metafield of `"6"` (type `single_line_text_field`) alongside an inventory selection of `2` produces `quantity: 2`, `name: "available"` in the inventory mutation** — the single most important regression guard for this feature. Rev 9: use **different** numbers for the two caller-supplied quantities so a crossed wiring cannot coincidentally pass;
  - **duplicate exact SKU (the real `CustomTC3` pair) fails `ambiguous_product_match` before any product, price or inventory mutation** — asserted by verifying zero write calls were made;
  - the created product carries `status: "UNLISTED"`, `inventoryPolicy: "DENY"`, `requiresShipping: true`, `tracked: true`;
  - **the variant price sent to Shopify equals the caller's string exactly** for both `"31200.00"` and `"5200.00"`;
  - **definition-addressed metafields trigger exactly one batched definition lookup**, and zero lookups when every entry is explicit;
  - an unresolved definition GID fails with `preorder_metafield_definition_not_found` before the product mutation;
  - no-metafields path sends no `metafields` key at all;
  - no-image path;
  - ambiguous SKU; ambiguous operation tag;
  - lost `productCreate` response → tag reconciliation adopts the orphan, creates nothing new;
  - failure at each stage persists the right stage/code and retains all IDs;
  - resume from each stage performs only the remaining calls;
  - retryable transport error propagates, non-retryable is captured;
  - **the seller-selected location is used verbatim** — the mutation targets exactly the GID that arrived in the request;
  - **a GID absent from the shop's locations fails** `preorder_inventory_location_invalid` before any inventory mutation, product/variant IDs retained — this is the "frontend supplied a location from another shop" case;
  - **an inactive location fails**; **a fulfillment-service location fails**;
  - **validation runs on every attempt** — a location deactivated between attempt 1 and attempt 2 is caught on attempt 2 rather than skipped;
  - **the location never changes between retries** — asserted by mutating any hypothetical external default between attempts and confirming the frozen value still wins;
  - **no substitution on failure** — asserted by verifying zero inventory calls against any location other than the selected one;
  - **two operations with different selected locations each write only to their own**, proving a business location change affects new pre-orders only;
  - **the same `@idempotent` key is sent on retry**;
  - **the prior available quantity is recorded** before the overwrite;
  - **no dual write** — exactly one `inventorySetQuantities` call against exactly one location;
  - retry after a lost inventory response leaves the quantity at `1`.
- `test_handle_shopify_process_products.py` (extended, pre-order cases): the `shopify.preorder.processed` payload for `succeeded` / `failed`, including the full `inventory` block with `location_id` **and** `location_name`, `zettle_ready`, and nullable media fields; **no `warnings` array and no `outcome_code`**; `zettle_ready` is `true` only when status is `succeeded` and the write landed at the selected location.
- `test_shopify_worker.py`: `HANDLER_MAP` covers the new task type.

**Service / integration**
- `test_shopify_preorder_enqueue_integration.py`: inactive / cross-workspace / unknown `shop_integration_id` → `NotFound`; missing token → failure before any Shopify call; **missing or malformed `inventory_location_id` → `validation_failed` with nothing written**; **a well-formed GID is accepted at command time without any Shopify call** (ownership is a worker-time gate); the persisted `inventory_location_id` equals what was submitted; `inventory_idempotency_key` is derived from it and persisted in the same transaction; unique-constraint replay adopts the existing row.
- `test_create_task_shopify_preorder_integration.py`: happy path writes `Task` + operation + `OPEN` `ExecutionTask` in one transaction **with the selected location committed atomically**; a later exception rolls back all three, leaving no orphaned location intent; `execute_shopify_graphql` never called; **`operation.inventory_location_id == normalized_request_json["inventory"]["location_id"]`**; non-`PRE_ORDER` task type rejected; `worker` role rejected with `PermissionDenied`; `seller` role accepted.
- `test_get_shopify_locations.py` (extended): the response carries `is_active`, `ships_inventory` and `is_fulfillment_service` for every location, so the selector can filter without a second call.
- `test_shopify_preorder_constraints.py`: the `(shop_integration_id, idempotency_key)` unique constraint and FK RESTRICT behavior.
- **Scope guard test**: assert `settings.shopify_app_scopes` still parses to exactly the pre-existing scope set — **no publication scopes and no reauthorization introduced** unless the Phase 0 storefront gate fails.
- **Ledger guard test**: assert no `preorder`-mode code path writes to `shopify_inventory_adjustments`, and that `product_sync` mode still does.
**Convergence regression guards (rev 7) — these gate the whole plan**
- `test_product_sync_characterisation.py`: capture the exact GraphQL documents and variables that a representative `product_sync` item emits **before** the restructure, and assert they are byte-identical after. Covers create path, update path, metafields, and multi-location additive inventory.
- `test_product_sync_orchestrator.py` (extended): a `product_sync` row still uses the **additive ledger** and never `inventorySetQuantities`; multi-location adjustments still work; `mode` defaults to `product_sync` for rows created by `process_shopify_products`; the new stage machine resumes a product-sync item correctly and its tag reconciliation prevents the previously-latent duplicate.
- **Mode-exposure guard test**: no HTTP request model (`ShopifyProcessProductsBody`, `ProcessShopifyProductItemRequest`, `ShopifyPreorderSectionInput`) exposes `mode` or any inventory-mode field; `process_shopify_products` produces only `product_sync` rows; only `_create_preorder_sync_item_in_session` can produce `preorder` rows.
- `test_shopify_product_sync_item_constraints.py`: the **partial unique index** rejects a second `preorder` row for the same `(shop_integration_id, task_id)` but permits many `product_sync` rows with the same `frontend_client_id`; the CHECK constraint rejects a `preorder` row missing `task_id`, `inventory_location_id` or `inventory_idempotency_key`, and permits a `product_sync` row with all three `NULL`.
- **Task-type guard test**: assert `TaskType` gained no new member and `QUEUE_MAP` / `HANDLER_MAP` are unchanged.
- `test_handle_shopify_process_products.py` (extended): a batch of `product_sync` rows emits `shopify.products.synced` with a payload **identical to today's**; a `preorder` row emits `shopify.preorder.processed`; a mixed batch emits both, correctly partitioned.

- **Merchant-leakage guard test**: grep-style assertion that no merchant-specific literal from R11 — the Västberga location GID `99221471562`, the metafield definition GID `241114906954`, the SKU `CustomTC3`, or the prices `31200.00` / `5200.00` — appears anywhere under `domain/` or `services/infra/`. These belong in configuration, fixtures and this plan's evidence only.
- **Quantity-name guard test**: assert every pre-order inventory call sends `name: "available"`; no code path sends `on_hand`.

**Suite-level**
- `pytest app/tests` — green, with the pre-existing Shopify suite unchanged.
- `alembic upgrade head` then `alembic downgrade -1` on a scratch DB — clean both ways (enum `ADD VALUE` is not reversible; the downgrade drops the table and the column and documents the retained enum values).

### Manual dev-store checklist (goes into the handoff doc)

1. Open the pre-order form: the location selector lists the shop's active, inventory-capable locations, including Västberga Warehouse, and shows name plus identifying detail.
2. Create a `PRE_ORDER` task with a `shopify_preorder` section as a `seller`, selecting Västberga; confirm the API responds immediately, echoes `inventory_location_id`, and made no Shopify call.
3. Watch the **Shopify worker** terminal — not the API server. Those logs only appear there, and the worker must be **restarted** to pick up code changes.
4. Shopify Admin: the product exists, is **`UNLISTED`**, carries the `managerbeyo-preorder` tags, has the right title/price/SKU, `inventoryPolicy: DENY`, `requiresShipping: true`, the image attached, **shows every supplied metafield with the expected namespace/key/type (including `custom.quantity` as `single_line_text_field`)**, and shows **`available = 1`** at Västberga Warehouse.
4a. Set `custom.quantity` to `"6"` and confirm Shopify Admin and Zettle both still show exactly **one** available unit.
4b. Confirm the price shown in Zettle matches the supplied price exactly.
4c. Submit a pre-order whose SKU matches the real `CustomTC3` duplicates: it fails with `ambiguous_product_match`, and neither existing product's price or stock is touched.
5. Storefront: the product is **not** findable.
6. Zettle: the product appears in the POS library with the right price and stock.
7. Re-submit the identical request: no second product; quantity still `1`; the same idempotency key in the worker logs.
8. Submit a second pre-order with the **same SKU** and a different price: the existing product is updated, price overwritten, no duplicate; `inventory_before_available` records the prior quantity.
9. Submit with an explicit override to a non-Zettle location: terminal `partially_provisioned`, `zettle_ready: false`, and the stock does **not** appear in Zettle.
10. Submit with a **different** selected location: stock lands there and only there; Västberga is untouched. Then submit a third pre-order back at Västberga and confirm both behave independently.
11. Deactivate the selected location between enqueue and execution: the operation fails `preorder_inventory_location_invalid`, the product and variant survive, and no other location receives stock.
12. Kill the worker between `VARIANT_CONFIGURED` and `INVENTORY_SET`; restart; confirm the same location and idempotency key are reused and the quantity lands at `1`.

---

## Clarifications required

All design questions are resolved.

**Rev 8 retired most of these gates.** 0.7 is answered by the R11 merchant evidence and already
handled by the existing normalizer's dict form; 0.8 is proven by R11; **0.11 is answered** — the
bucket is public, the object was fetched anonymously, and WebP is an accepted Shopify format;
0.4a–0.4g, 0.12–0.15 belong to hardening that is now backlog, not the minimum.

**Rev 9 — three of the four are now resolved. One remains.**

- [x] **0.1 — PASS.** A newly created `UNLISTED` product **is** imported into Zettle (merchant
      confirmation, 2026-07-27). This was the load-bearing assumption of the feature.
- [→] **0.2 — DEFERRED** *(David's decision, 2026-07-27)* into Phase 1's post-implementation
      dev-store verification, where acceptance criterion 4 already requires storefront absence.
      Rationale: low probability (all the merchant's live products are `UNLISTED`; the status is
      documented as excluded from search, collections and recommendations), and deferring removes
      a blocking step at no cost. **Consequence accepted:** if it fails, the required
      `publishableUnpublish` + `read_publications` / `write_publications` + **merchant
      reauthorization** is discovered *after* implementation. It is not a parameter change — no
      other `ProductStatus` works, since `ACTIVE` is storefront-visible and `DRAFT` is invisible
      to Zettle.
- [x] **0.3 — RETIRED.** Whether Zettle syncs a *particular* location is not a backend concern:
      the frontend chooses the location and the merchant owns that operational mapping. Consistent
      with the seller-selected model (R7).
- [x] **0.4 — RESOLVED.** The price is the **full product price straight from the form**, not
      per-unit and not derived from any quantity. Already enforced (R11 §7); nothing to verify.

<details>
<summary>Rev 7's full sixteen-gate list — superseded, retained for traceability and for whichever
hardening ticket eventually needs it</summary>

- [ ] 0.4-old inventory written only to another active location does **not** make the item available in Zettle
- [ ] 0.4a the locations endpoint returns Västberga with `is_active: true`, `is_fulfillment_service: false`
- [ ] 0.4b inactive locations are not selectable and are rejected if forced
- [ ] 0.4c a location belonging to another Shopify shop is rejected at worker time
- [ ] 0.4d a location deactivated after task creation fails safely, product/variant IDs retained, no fallback
- [ ] 0.4e inventory is written only to the selected location
- [ ] 0.4f retries never change the selected location or the idempotency key
- [ ] 0.4g a new pre-order can use a newly selected location while an existing queued operation keeps its frozen one
- [ ] 0.5 `available = 1` confirmed as the till-ready state
- [ ] 0.6 `on_hand = 1` + `committed = 1` + `available = 0` confirmed **not** till-ready
- [ ] 0.7 `custom.quantity = "6"` (`single_line_text_field`) stays independent of the inventory target of `1`
- [ ] 0.8 duplicate exact-SKU lookup fails ambiguously instead of silently selecting a product
- [ ] 0.9 the supplied variant price reaches Zettle unchanged
- [ ] 0.10 intended values / preservation behavior confirmed for `inventoryPolicy`, `requiresShipping` and `taxable`
- [ ] 0.11 Shopify can fetch the presigned S3 image URL
- [ ] 0.12 the `inventorySetQuantities` document (with `@idempotent`, with `changeFromQuantity`, without `ignoreCompareQuantity`) is accepted by 2026-01
- [ ] 0.13 replaying with the same idempotency key is accepted safely; the key format/length is accepted
- [ ] 0.14 `changeFromQuantity: null` skip-the-check behavior confirmed on 2026-01
- [ ] 0.15 singular `location` query / `shipsInventory` compared against the verified Västberga GID
- [ ] 0.16 `UNLISTED` accepted by both `ProductCreateInput.status` and `ProductUpdateInput.status` without coercion

</details>

## Review log

- `2026-07-27` `claude-opus-5`: rev 1 — planned the full order-creation workflow (customer upsert, `draftOrderCreate`, `draftOrderComplete` payment-pending).
- `2026-07-27` `David`: scope withdrawn — no order is created; Zettle handles the sale. Answered five clarifications: set inventory to exactly 1; Zettle imports the whole product library; keep the location picker with a non-default warning; reuse existing SKU and overwrite price; images are AWS S3; trigger is `TaskTypeEnum.PRE_ORDER` for roles admin/manager/seller.
- `2026-07-27` `claude-opus-5`: rev 2 — rewritten to the product-only workflow. Customer, draft-order and order stages removed. No scope change, no reauthorization.
- `2026-07-27` `David`: rev 2 review — (a) the `@idempotent` finding is wrong: the directive is supported and optional in 2026-01 and mandatory from 2026-04, so adopt it now with a deterministic key; (b) the location must be execution-critical, not warning-only — a write to a non-Zettle location must not report success; (c) `fulfillsOnlineOrders` is not a default-inventory-location signal; strengthen discovery and add a config field; (d) document that the 2026-04 upgrade also changes the compare-and-swap contract; (e) keep the tag reconciliation and file generic product-sync repair as a separate ticket.
- `2026-07-27` `claude-opus-5`: rev 3 — corrections applied and verified against shopify.dev:
  - **`@idempotent` corrected.** Confirmed supported/optional in `2026-01`, mandatory from `2026-04`; exact syntax captured; adopted now with the deterministic key `shopify-preorder:<operation_id>:inventory-set:<location_numeric_id>` (R8). The agent's stored reference memory carrying the wrong claim has also been corrected.
  - **Compare-and-swap improved beyond the brief.** Research showed `ignoreCompareQuantity` (input) and `compareQuantity` (quantity input) are *already deprecated with removal dates in `2026-01`* and **removed in `2026-04`**, with `changeFromQuantity` as the survivor (`null` = skip; mismatch → `CHANGE_FROM_QUANTITY_STALE`). Rev 2's planned `ignoreCompareQuantity: true` is therefore replaced by `changeFromQuantity: null`, which is valid on `2026-01` today **and** is already the `2026-04` shape — so the upgrade needs no document change, only verification.
  - **Location made execution-critical.** `inventory.location_id` removed from the normal request; new `shopify_shop_integrations.zettle_inventory_location_id` + admin route; new `INVENTORY_LOCATION_RESOLVED` stage that freezes the location and the idempotency key; new `PARTIALLY_PROVISIONED` status and `zettle_ready` flag; `SUCCEEDED` now requires a confirmed Zettle-synced write. The `warnings: ["inventory_location_not_default"]` mechanism is deleted.
  - **Discovery strengthened.** `fulfillsOnlineOrders` dropped as a signal; `Location.isPrimary` confirmed deprecated with `shipsInventory` as Shopify's stated replacement; the non-deprecated primary-location resolution is the singular `location` query with `id` omitted. The worker fails rather than guessing.
  - **Schema, state machine, audit fields, acceptance criteria, Phase 0 (11 gates), frontend handoff and the test matrix** all rewritten per the review brief.
  - Generic product-sync duplicate repair explicitly moved to a follow-up ticket and out of this plan's scope.
- `2026-07-27` `David`: rev 3 addition — the service will also receive **metafield values** to write on the product. One has key `quantity` and stores the quantity passed in. The inventory quantity at the location is **fixed at 1 and is not taken from that `quantity` parameter**.
- `2026-07-27` `claude-opus-5`: rev 4 — metafields added and the `quantity` conflation removed:
  - **New R10.** Verified for `2026-01` that both `ProductCreateInput` and `ProductUpdateInput` expose `metafields: [MetafieldInput!]`, so metafields are written by the **same mutation** as the product and media. No `metafieldsSet` call — one fewer round trip than product sync, atomic with the product write, and no separate partial-failure stage to model.
  - **`quantity` is no longer a request field.** Rev 3's `ShopifyPreorderProductRequest.quantity: int = 1` conflated metafield data with the inventory target and is removed. `quantity` is now one ordinary entry in a generic `metafields` list, and the inventory target is the `PREORDER_INVENTORY_QUANTITY = 1` policy constant. Adding, renaming or dropping metafields now needs no backend change.
  - **Three caller shapes** supported (`definition_id` preferred, explicit `namespace/key/type`, or shorthand `key` against an existing definition), with `MetafieldInput`'s real requirement rules captured: namespace/key required on create, `type` required only when no definition exists, `value` always a string.
  - **Definition resolution moved to worker time** — resolving a `definition_id` needs a Shopify call, which must not happen inside the task-creation transaction (R2). One batched `fetch_shopify_metafield_definitions_by_ids` call, reusing the existing client unchanged.
  - Values are stringified at normalization so the persisted payload is byte-stable across retries and **no numeric precision is lost to `float`**.
  - Metafield rejections fail the product write atomically and surface their `metafields.<n>.<field>` path through the rev-3 `userErrors` retention; three new error codes added.
  - Acceptance criteria 5a–5c, Phase 0 gates 12–13, manual step 4a and dedicated `test_preorder_metafields.py` coverage added — including the load-bearing regression guard that **a `quantity` metafield of `25` still produces exactly one available unit**.
  - Still no scope change: `write_products` covers metafield writes, `read_products` covers definition reads.
- `2026-07-27` `David`: rev 4 review — supplied **live merchant-store evidence for SKU `CustomTC3`** (two duplicate products, `UNLISTED` status, Västberga Warehouse location, `available`/`on_hand`/`committed` readings, the real `custom.quantity` definition, and the observed variant field defaults) with seven required corrections.
- `2026-07-27` `claude-opus-5`: rev 5 — corrections applied. **These are grounded in the merchant's live store, not documentation alone**, and where documentation was consulted it was to confirm the API supports what the store already does:
  - **`UNLISTED` replaces `ACTIVE`.** Both live `CustomTC3` products are `UNLISTED`, and the rev-4 claim that "ACTIVE is required for Zettle visibility" is **withdrawn as unsupported**. Independently confirmed that `UNLISTED` is a real `ProductStatus` in `2026-01`, settable on both `ProductCreateInput` and `ProductUpdateInput` (available from `2025-10`), documented as *"active but you need a direct link to view it… doesn't show up in search, collections, or product recommendations."* That is a **better** fit than rev 4's construction: it satisfies "visible to Zettle" and "absent from the storefront" in one field instead of depending on the absence of an `autoPublish` publication. Applied to the decisions table, R4, the policy module, the normalized payload, acceptance criteria, Phase 0, tests and the architecture-doc task.
  - **Duplicate exact SKUs reclassified from hypothetical to confirmed production condition.** The very first SKU examined already violates uniqueness. The five reconciliation rules are now explicit and mandatory, with the prohibition on auto-selecting by order/age/price/stock/status/timestamp stated as a rule rather than implied. Materially: silently picking one of these two would have overwritten either a `31200.00` or a `5200.00` price at random. `select_exact_variant_match` already behaves correctly, so this is a documentation and test correction — new evidence-driven fixtures permute order and mutate each tempting selection attribute.
  - **Västberga Warehouse (`gid://shopify/Location/99221471562`) recorded as the candidate Zettle location**, to be written into `zettle_inventory_location_id` **after** gate 3 confirms it. Explicit configuration, never dynamic guessing — and a new leakage-guard test asserts the GID never appears in `domain/` or `services/infra/`.
  - **`available`, not `on_hand`, defines till readiness.** The older product (`on_hand = 1`, `committed = 1`, `available = 0`) is the concrete proof that an existing unit is not a sellable one. `name: "available"` retained; target unchanged; `before_available` remains the audit read, stated in the same quantity as the readiness rule.
  - **`custom.quantity` corrected to `single_line_text_field`** (definition `gid://shopify/MetafieldDefinition/241114906954`). Rev 4's `number_integer` was invented. Runtime is unaffected because definition-addressed metafields resolve dynamically — but Phase 0 fixtures and tests now exercise the real shape, and a new assertion checks `"6"` stays the string `"6"`.
  - **Quantity/inventory separation strengthened with the real numbers.** `custom.quantity = "6"` alongside `available = 1` is the live proof that these describe different things — item composition versus one sellable unit at the till. `PREORDER_INVENTORY_QUANTITY = 1` stands, and the headline regression test now uses the merchant's real metafield type.
  - **Price independence made explicit.** The `31200.00 / "4"` and `5200.00 / "6"` pair invites a false inference; no consistent formula exists in either direction. The plan now states that price is caller-supplied data written verbatim, and adds a property-style test over both real pairs that fails if any code path multiplies or divides price by a metafield value.
  - **Variant field policy recorded from the observed defaults** without expanding into a product-settings system: `tracked: true` mandatory; `inventoryPolicy: DENY` and `requiresShipping: true` set deliberately; `taxable` made configuration-driven (`SHOPIFY_PREORDER_VARIANT_TAXABLE`, default `false`) rather than assumed universal — gate 10 decides whether it is merchant policy or should be caller-supplied; `barcode` left `null` unless supplied. Confirmed against the API that `tracked`/`requiresShipping` live on `InventoryItemInput` while `inventoryPolicy`/`taxable` live on `ProductVariantsBulkInput`.
  - Phase 0 expanded from 13 to **16 gates**; architecture, scope boundaries, durability model, worker stages, retry strategy and contracts otherwise unchanged.
- `2026-07-27` `David`: rev 5 review — the location must be **seller-selected in the frontend**, not integration-level configuration, so the business can change locations without a backend change. Remove the column, its admin route, the rollout prerequisite, the config flag, the override contract, the resolution hierarchy and `PARTIALLY_PROVISIONED`. Validate locally at command time and against Shopify at worker time; freeze per operation; never substitute.
- `2026-07-27` `claude-opus-5`: rev 6 — location model rewritten. This is a **net simplification**: one required request field replaces a column, a migration, an admin route + command + request, a config flag, a three-value enum, an override sub-request, a terminal status, a stage, a domain policy module and four error codes.
  - **`inventory_location_id` is now a required field of the normal request**, sent by the seller's selector and echoed in the queued response.
  - **Validation split by capability, not preference** — GID shape and shop/workspace checks are local and happen at command time; ownership, active status and inventory capability require Shopify and happen at worker time. A well-formed GID from a *different* merchant's shop is indistinguishable locally, so the ownership check is a hard worker-time gate: *"do not trust a location merely because the frontend supplied it."*
  - **"Can hold inventory" defined as `isActive && !isFulfillmentService`.** `shipsInventory` is surfaced as an informational hint but deliberately **not** a gate — it describes shipping, not inventory capability, which is the same category error rev 2 made with `fulfillsOnlineOrders`.
  - **Frozen at command time, not at a worker stage.** Both the location and the derived idempotency key are now known when the operation row is written, so `INVENTORY_LOCATION_RESOLVED` had nothing left to do and was deleted. What remains is *validation*, which is deliberately **re-run on every attempt** instead of stage-guarded — a resume-skip would miss a location deactivated between attempts.
  - **Canonical representation resolved explicitly**: the non-null column is authoritative for execution, the `normalized_request_json` copy keeps the request snapshot self-describing, and a consistency test asserts they never diverge — so duplication cannot become ambiguity.
  - **`zettle_ready` retained but narrowed** to "provisioned at the location the seller selected". Keeping the name avoids client churn; the plan states the narrower meaning explicitly rather than overclaiming that it proves Zettle visibility.
  - **Recommended dropping the column entirely rather than keeping it as an optional default** — a default belongs in the UI, and retaining a backend hint would reintroduce the two-sources-of-truth ambiguity this revision removes. Noted that adding a server-side default later is purely additive, since each operation already carries its own frozen location.
  - **Residual risk stated plainly**: the seller can now pick a location Zettle does not read. That is the accepted cost of user choice; mitigations are the filtered selector, the Phase 0-verified default, and echoing `location_name` in the terminal event so stock placement is visible rather than inferred.
  - Phase 0 gained gates 4a–4g covering selector contents, cross-shop rejection, post-creation deactivation, single-location writes, retry stability and the change-location-tomorrow case. The Västberga GID is now evidence and a frontend default — never backend configuration, and still barred from `domain/` and `services/infra/` by the leakage-guard test.
- `2026-07-27` `David`: rev 6 review — asked how different this really is from the existing product-creation flow, and whether to reuse it with flags instead. Chose **shared core, two entry points**.
- `2026-07-27` `claude-opus-5`: rev 7 — converged onto the existing pipeline. The overlap audit (R12) found ~70% of rev 6 was reimplementation, including several things product sync **already does correctly today** — `UNLISTED` works via `_normalize_status`'s uppercase, single-shop targeting works via `target_shop_integration_ids`, and ambiguous-SKU failure is already implemented. Changes:
  - **Deleted:** the `shopify_preorder_operations` table, its migration and the `shppre` prefix; `TaskType.SHOPIFY_CREATE_PREORDER_PRODUCT`, `ShopifyCreatePreorderProductPayload` and their `QUEUE_MAP` / `HANDLER_TIMEOUT_SECONDS` / `HANDLER_MAP` entries and enum migration; `handle_shopify_create_preorder_product.py`; `preorder_product_client.py`; `_preorder_orchestrator.py`; `preorder_results.py`; and one status enum (the existing `ShopifyProductSyncItemStatusEnum` already matched). Nine new files became six; four migrations became two.
  - **Shared:** one staged orchestrator, one client, one table, one task type, one worker handler. The `mode` branch occurs at exactly one point — the inventory step.
  - **The decisive argument was drift**, not line count: the lost-`productCreate`-response duplicate bug exists in product sync *today*, and rev 6 deferred it to a follow-up precisely because the pipelines were separate. Converging fixes it once, so it moved from "out of scope" into scope.
  - **Lifecycle difference handled by two columns and a partial index**, not a second pipeline: `UNIQUE (shop_integration_id, task_id) WHERE task_id IS NOT NULL AND mode='preorder'` gives pre-order its one-shot guarantee while leaving product sync's repeatable re-sync unconstrained. A CHECK constraint makes a malformed pre-order unrepresentable in the shared table.
  - **The one thing deliberately not shared is the destructive mode.** `mode` appears in no HTTP request schema; `/products/process` keeps additive-only inventory permanently, so a bad HTTP caller cannot wipe stock. Guard tests enforce it.
  - **New dominant risk recorded and gated:** the restructure touches live product-sync code. Mitigations are payload-opt-in behaviour, a characterisation test asserting today's GraphQL documents are byte-identical after the change, phase gates on the pre-existing suite, and a single well-located mode branch.
  - Every safety property from revs 3–6 is preserved: seller-selected frozen location, deterministic `@idempotent` key, `available = 1`, `UNLISTED`, ambiguous-SKU failure, quantity/inventory independence, price never derived, no automatic deletion, no scope change.
- `2026-07-27` `David`: rev 7 review — (a) asked why the existing product-creation system is not
  sufficient and why so much is being rebuilt; (b) confirmed by direct fetch that the S3 bucket is
  **public**, contradicting rev 7's R3.
- `2026-07-27` `claude-opus-5`: rev 8 — scope cut and R3 corrected:
  - **R3 was wrong and is corrected.** Rev 7 inferred "no permanently public image URL" from the
    code — `StorageClient` exposes only presigned GET/PUT and nothing composes a plain URL — but
    never checked the bucket policy. The bucket is public; an object was fetched anonymously.
    The real gap is that **no application code emits an unsigned URL**, which is a ~10-line
    `public_url(key)` addition. Presigning, TTL handling, per-attempt minting and the
    `stagedUploadsCreate` fallback are all **removed**.
  - **Verified additionally:** Shopify *pulls* the image via `CreateMediaInput.originalSource`
    (nothing is uploaded to it); **WebP is accepted** — load-bearing, since the pipeline stores
    `.webp`; limits are **20 MB / 25 MP**, now validated locally at command time from data the
    `images` table already holds; media processing is asynchronous and `READY` is **not** waited on.
  - **New R13 — minimum scope.** A second audit asked "what is the smallest delta?" rather than
    "what would a robust system look like". The existing `/products/process` already covers SKU
    resolution, ambiguity failure, price, `UNLISTED`, metafields in the `custom` namespace,
    inventory at a chosen location, **location ownership validation**, and **per-task replay
    safety via the existing ledger**. Genuinely required: `public_url`, `media` on the product
    mutations, image-limit validation, the absolute set, and the `maybe_begin` + `create_task`
    wiring. **Minimum schema delta is one enum and three columns**, not fourteen.
  - **Delivery restructured** from eleven phases to: one minimum plan, two standalone improvement
    tickets (`userErrors` fidelity; the staged-orchestrator duplicate-product fix — both valuable
    with or without pre-orders), and this document as the retained backlog.
  - **Phase 0 cut from sixteen gates to four** — the only questions a dev store can answer:
    does Zettle import an `UNLISTED` product, does it stay off the storefront, does Zettle read
    the chosen location's inventory, does the price arrive unchanged. The full list is retained
    above, collapsed, for traceability.
  - **Set-to-1 retained** as the decision of record. The additive `+1` alternative — which would
    remove `inventorySetQuantities`, `@idempotent`, the key module and the `changeFromQuantity`
    contract — is documented in R13 as an available scope reduction, not a reopened question.
  - All findings R1–R12 are retained unchanged; they are where the `UNLISTED`, duplicate-SKU,
    `available`-vs-`on_hand`, metafield and convergence evidence lives.
- `2026-07-27` `David`: Phase 0 partial outcomes and an inventory clarification — **0.1 PASS**
  (Zettle imports an `UNLISTED` product); **0.3 retired** (the frontend chooses the location; which
  locations Zettle syncs is not a backend concern); **0.4 resolved** (the price is the full product
  price from the form, not per-unit and not derived from quantity). **0.2 not yet run.**
  On inventory: *"just like in the current system the choice of location comes with the choice of
  quantity for that store location, and that quantity is independent making changes to whatever
  quantity is in a product."* Confirmed on follow-up as **absolute set with a caller-supplied
  quantity**, not additive.
- `2026-07-27` `claude-opus-5`: rev 9 — inventory quantity corrected:
  - **`PREORDER_INVENTORY_QUANTITY = 1` is deleted.** Revs 4–8 modelled the inventory target as a
    fixed constant. It is not: the frontend sends a **quantity per selected location**, mirroring
    the existing `inventory_adjustments` contract, with the UI defaulting the field to `1`. The
    request now carries `inventory: [{location_id, quantity}]`; `quantity` replaces
    `quantity_to_add` because the semantics are absolute, and `inventory_mode` distinguishes the
    two paths.
  - **Absolute set confirmed, additive declined.** The alternative was put explicitly with the
    stock arithmetic and the deleted-work list; the answer was overwrite. Recorded in R13 so a
    future reader knows it was weighed.
  - **The metafield-independence rule is preserved and strengthened.** There are now **two**
    caller-supplied quantities in one request — `custom.quantity` (product data) and the inventory
    quantity — which makes conflating them the easiest available mistake. R10 now carries a table
    distinguishing them, and the headline regression test uses **different** numbers
    (`custom.quantity = "6"`, inventory `2` → `available = 2`) so a wrong wiring cannot
    coincidentally pass.
  - **`before_available` becomes more load-bearing**, not less: with an arbitrary overwrite
    quantity it is the only record of what stock existed before a pre-order replaced it.
  - Phase 0 recorded: 0.1 PASS, 0.3 retired, 0.4 resolved, **0.2 still open** — and 0.2 is the one
    that can change scope.
- `2026-07-27` `David`: deferred Phase 0 gate 0.2 to the post-implementation verification —
  implement first, test after, on the grounds that product-creation parameters are cheap to
  correct. **Phase 0 is now complete and blocks nothing.**
- `2026-07-27` `claude-opus-5`: deferral recorded, with one correction stated: a 0.2 failure is
  **not** a parameter change. No alternative `ProductStatus` satisfies both requirements —
  `ACTIVE` is storefront-visible, `DRAFT` is invisible to sales channels and therefore to Zettle.
  The fix is `publishableUnpublish` plus `read_publications` / `write_publications` plus a
  **merchant OAuth reauthorization for every installed shop**, which is an operational step the
  merchant performs, not something a debugging pass patches. The risk is genuinely low and the
  deferral is reasonable; the consequence is that a reauthorization cycle, if needed, surfaces
  after implementation. Gate 0.2 is folded into Phase 1's acceptance criterion 4 (which already
  required storefront absence) with an explicit verification method — storefront search,
  `/collections/all`, `/sitemap_products_1.xml`, and `resourcePublications` on the product — and
  a note that a direct `/products/<handle>` URL loading is **expected**, not a leak.
  Also split the characterisation net into its own plan and prompt, since it gates two
  workstreams and "stop halfway through a plan" was a fragile instruction.
- `2026-07-27` `claude-opus-5`: lifecycle processing per
  `skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`. All five implementing plans moved to
  `archives/implementation/` with `ARCHIVE_RECORD_*` files and status set to `archived`; a missing
  summary was written for Phase 0. Two stale duplicates — `PLAN_shopify_admin_routes_serializers_20260709.md`
  and `PLAN_shopify_webhook_history_records_20260709.md` — were byte-identical to the copies already
  in `archives/implementation/` and were deleted from `under_construction/` per the skill's cleanup
  protocol 3a. **This document was deliberately not archived** — see "Why this document is not
  archived" below. Two outcomes were classified `completed_with_validation_followups` rather than
  `completed`, because their plans' own gates (Phase 1 dev-store verification, duplicate-fix human
  diff review) have not been executed; recording them as complete would have overstated the state.
- `2026-07-27` `David`: rev 10 — **the `custom.quantity` metafield should be derived from the
  inventory quantity**, not supplied separately. Confirmed on follow-up: the **backend** derives it,
  and for multi-location pre-orders it is the **sum** across locations.
- `2026-07-27` `claude-opus-5`: rev 10 implemented. This **reverses** the independence rule that
  revs 4–9 hardened (R10, R11 §6, the guardrails, the headline regression test and the frontend
  handoff all asserted the two must never be crossed). The reversal is deliberate and is a change
  to what the field *means*, not a correction of the evidence — the merchant's live products
  genuinely do carry `custom.quantity = "6"` alongside `available = 1`, which is why independence
  looked right.
  - New `domain/shopify/preorder_policy.py` holds the derivation plus the `UNLISTED` status and the
    metafield key/type, so the rule lives in the domain layer rather than inline in a command.
  - `custom.quantity` = `str(sum(inventory[].quantity))`, typed `single_line_text_field` to match
    the merchant's real definition.
  - **A caller-supplied `metafields.quantity` is rejected at the request boundary** rather than
    silently overwritten — a form still sending it gets a clear error instead of watching its value
    vanish. Every other metafield key passes through untouched.
  - R10 above is marked superseded rather than deleted; the evidence in R11 §6 is still valid and
    still worth reading before anyone reopens this.
  - Full suite re-run against the pristine baseline: no new failures (four apparent additions were
    confirmed pre-existing `pause_reasons` / `worker_shift` order-dependent flakes, which fail in
    isolation and reference nothing in this change).
- `<YYYY-MM-DD>` `<reviewer>`: `<feedback>`

## Delivery artefacts — all child plans archived 2026-07-27

Every implementing plan has been implemented, summarised and archived. Each is now at
`backend/docs/architecture/archives/implementation/`, with an `ARCHIVE_RECORD_*` at
`backend/docs/architecture/archives/` and a `SUMMARY_*` at
`backend/docs/architecture/implemented_summaries/`.

| Document | Role | Result |
|---|---|---|
| `PLAN_shopify_preorder_phase_0_dev_store_verification_20260727.md` | dev-store gates | `completed_with_validation_followups` — gate 0.2 deferred, not run |
| `PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md` | **the critical path** | `completed_with_validation_followups` — dev-store verification outstanding |
| `PLAN_shopify_product_sync_characterisation_net_20260727.md` | prerequisite safety net | `completed` |
| `PLAN_shopify_product_sync_error_fidelity_20260727.md` | standalone improvement | `completed` |
| `PLAN_shopify_product_sync_duplicate_fix_20260727.md` | standalone bug fix | `completed_with_validation_followups` — human diff-review gate not recorded |
| **this document** | research record (R1–R13) and hardening backlog | **stays here — see below** |

## Why this document is not archived

It is **not an implementing plan**. Rev 8 explicitly redefined it as the research record and the
hardening backlog, and rev 9 confirmed that shape. Two reasons it stays in
`under_construction/implementation/`:

1. **The lifecycle contract forbids moving it.** Its status is `under_construction`, and the
   `plan_lifecycle_orchestrator` skill states that plans which are `under_construction` or
   `approved` must not be archived. Only `archived`-status plans move.
2. **Archiving would bury live work.** R13's three hardening buckets — the frozen-location model,
   `is_fulfillment_service` filtering, the partial unique index, the pure policy modules,
   definition-ID metafield resolution — are unbuilt and deliberately deferred, not abandoned.
   R1–R13 are also where the `UNLISTED`, duplicate-SKU, `available`-vs-`on_hand`, metafield and
   convergence evidence lives, and where the `2026-04` API-upgrade checklist sits.

**To promote a backlog item**, cut a new implementation plan citing the relevant research finding,
rather than reopening this one.

## Outstanding across the delivery

- **Dev-store verification of Phase 1**, which carries **deferred gate 0.2** (storefront absence).
  A leak is a scope change — `publishableUnpublish` plus `read_publications` / `write_publications`
  plus merchant reauthorization — not a bug fix.
- **The duplicate-fix human diff-review gate**, and its real-endpoint latency measurement.

## Lifecycle transition

- Current state: `under_construction` — **intentional and terminal for this document's current role**
- Next state: none pending. It becomes `archived` only when its backlog is exhausted or explicitly
  abandoned, not when the pre-order feature ships.
- Transition owner: `David`
