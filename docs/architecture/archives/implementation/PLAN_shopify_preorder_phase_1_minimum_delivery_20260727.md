# PLAN_shopify_preorder_phase_1_minimum_delivery_20260727

## Metadata

- Plan ID: `PLAN_shopify_preorder_phase_1_minimum_delivery_20260727`
- Status: `archived`
- Phase: **1 of 1** — this is the whole critical path
- Parent plan: `PLAN_shopify_preorder_product_20260727.md` (rev 8 — research **R1–R13**)
- Depends on: `PLAN_shopify_product_sync_characterisation_net_20260727.md` (the drift detector —
  this plan edits the same live files). Phase 0 is **complete and non-blocking**; its one deferred
  gate (0.2, storefront absence) is folded into this plan's dev-store verification below.
- Owner agent: `codex`
- Created at (UTC): `2026-07-27T00:00:00Z`
- Last updated at (UTC): `2026-07-27T21:00:00Z`
- Supersedes: rev 7's phases 1, 3, 4, 5, 7, 8, 9, 10, 11

## Goal and intent

- Goal: when a `PRE_ORDER` task is created, provision the corresponding Shopify product — SKU,
  price, metafields, image, and one unit of stock at the chosen location — so staff can sell it
  in Zettle.
- Intent: reuse the existing `/products/process` pipeline, which already does most of this
  (**R13**). Add only what is missing.
- Non-goals: no Shopify order/customer/draft order; no new table; no new task type; no stage
  machine; no parallel worker path. Those are either unnecessary or backlog in the parent plan.

## What already works and must not be rebuilt

Verified against `/products/process` as it stands (**R13**):

SKU resolve-or-create · ambiguous-SKU failure · variant SKU + price · `UNLISTED` (the normalizer
uppercases whatever is passed) · single-shop targeting · tags / product type / description ·
metafields in the `custom` namespace with an explicit type · inventory at a chosen location ·
**location ownership validation** (`_inventory_sync.py:53-70`) · **per-task replay safety** (the
ledger is unique on `(shop, frontend_client_id, location)`) · worker, queue, retry, socket.

**If you find yourself reimplementing any of the above, stop — you have gone out of scope.**

## Scope — five items

1. **`public_url(key)`** on `StorageClient` and its implementations, plus a
   `STORAGE_PUBLIC_BASE_URL` setting so a CDN can be slotted in later. The bucket is public but
   no application code composes an unsigned URL today (**R3**).
2. **`media` support** on `productCreate` / `productUpdate` in `product_sync_client.py`, plus an
   `image_id` field on the product-sync item request.
3. **Image limit validation** at command time — 20 MB, 25 MP — from `width_px`, `height_px` and
   `file_size_bytes` already on `images`.
4. **Absolute inventory set** for pre-order mode: `inventorySetQuantities` with `@idempotent` and
   `changeFromQuantity: null`, plus an `inventory_mode` discriminator. The **quantity is
   caller-supplied per location** (rev 9), not a constant.
5. **The trigger**: `process_shopify_products` → `maybe_begin`, and `create_task` calling it.

## Guardrails

Read `prompts/GUARDRAILS.md`. The rules that bite here:

- **`inventory_mode` must never appear in any HTTP request schema.** Only the pre-order command
  sets `set`. `/products/process` stays additive-only, permanently — an inventory-mode flag on
  the general route would let a bad caller wipe real merchant stock.
- **Never send `ignoreCompareQuantity` or `compareQuantity`** — deprecated in `2026-01`, removed
  in `2026-04`. Send `changeFromQuantity: null`.
- **Two caller-supplied quantities travel in one request. Never cross them.**
  `custom.quantity` is a **product metafield** describing item composition. The inventory
  `quantity` is **per location** and drives `inventorySetQuantities`. Inventory must never be
  read from, multiplied by, or influenced by the metafield. Live proof they differ:
  `custom.quantity = "6"` on a product with `available = 1` (R11).
- **Price is written exactly as supplied.** Never derived from any metafield.
- **No Shopify call inside the `create_task` transaction.**
- **No `commit`/`rollback` inside `maybe_begin`.**
- **No merchant literals** (the Västberga GID, `CustomTC3`, the metafield definition GID) in
  `domain/` or `services/infra/`.

## Contracts to load

- `backend/architecture/06_commands.md` + **`06_commands_local.md`** — `maybe_begin` owner vs
  subordinate. Load both; the local file is load-bearing.
- `backend/architecture/16_background_jobs.md` — `create_instant_task`; the `ExecutionTask` row
  *is* the outbox (**R2**). **Do not use `event_bus` as the trigger** — it dispatches post-commit
  and swallows handler exceptions, so a crash there loses the pre-order.
- `backend/architecture/19_integrations.md` — GraphQL documents live only in `services/infra/shopify/`.
- `backend/architecture/30_migrations.md` — additive migration idiom.
- `backend/architecture/34_file_storage.md` — storage keys and the client interface.
- `backend/architecture/28_roles_permissions.md` — the role gate.

## Schema delta — one enum, three columns

```python
class ShopifyInventoryModeEnum(StrEnum):
    ADD = "add"      # existing additive ledger behaviour — the default
    SET = "set"      # absolute overwrite with the caller-supplied quantity, pre-order only
```

On `shopify_product_sync_items`:

| Column | Type | Null | Default |
|---|---|---|---|
| `inventory_mode` | `shopify_inventory_mode_enum` | no | `add` + server_default |
| `shopify_media_id` | `String(255)` | yes | — |
| `media_status` | `String(32)` | yes | — |

Plus `ShopifyIntegrationEventTypeEnum.PREORDER` (additive `ALTER TYPE … ADD VALUE IF NOT EXISTS`).

**No `task_id` column** — `frontend_client_id = task_id` carries it and is what the existing
ledger already dedupes on. **No idempotency-key column** — it is computed at worker time from
`(sync_item.client_id, location_id)`, both already present.

Two migrations, both additive. Existing rows get `inventory_mode = 'add'` from the server default;
no backfill.

## Files

### Add

| Path | Purpose |
|---|---|
| `app/beyo_manager/services/commands/shopify/_create_preorder_sync_item_in_session.py` | subordinate helper `create_task` calls |
| `app/beyo_manager/services/tasks/shopify/_product_media_resolver.py` | compose the public image URL at worker time |
| `app/migrations/versions/<rev>_add_preorder_columns_to_shopify_product_sync_items.py` | enum + 3 columns |
| `app/migrations/versions/<rev>_add_preorder_to_shopify_integration_event_type.py` | `ALTER TYPE … ADD VALUE` |

### Modify

| Path | Change |
|---|---|
| `app/beyo_manager/config.py` | `STORAGE_PUBLIC_BASE_URL` |
| `services/infra/storage/base.py` + `s3_client.py` + `local_client.py` | `public_url(key)` |
| `domain/shopify/enums.py` | `ShopifyInventoryModeEnum`, `ShopifyIntegrationEventTypeEnum.PREORDER` |
| `models/tables/shopify/shopify_product_sync_item.py` | the three columns |
| `services/infra/shopify/product_sync_client.py` | optional `media` on create/update + media selection set |
| `services/infra/shopify/inventory_client.py` | `set_inventory_quantity` with `@idempotent` |
| `services/commands/shopify/requests/process_shopify_products_request.py` | `image_id` / `image_url` / `image_alt_text`; image-limit validation |
| `domain/shopify/product_sync_payloads.py` | carry the image reference into the normalized payload |
| `services/commands/shopify/process_shopify_products.py` | `ctx.session.begin()` → `maybe_begin` |
| `services/tasks/shopify/_product_sync_orchestrator.py` | resolve + attach media; **one** `inventory_mode` branch |
| `services/commands/tasks/requests/__init__.py` | `ShopifyPreorderSectionInput` on `CreateTaskRequest` |
| `services/commands/tasks/create_task.py` | task-type + role gate, subordinate call, return-dict addition |
| `services/tasks/shopify/handle_shopify_process_products.py` | emit `shopify.preorder.processed` for pre-order rows |

## Implementation notes

### Media (R3)

Shopify **pulls** the image. `CreateMediaInput` is `originalSource: String!`,
`mediaContentType: MediaContentType!` (`IMAGE`), optional `alt`. Pass it as the separate `media`
argument on `productCreate` / `productUpdate` — **not** the deprecated `productCreateMedia`, and
not `metafieldsSet`-style separate calls.

Resolver: `S3` → `storage.public_url(image.image_url)` (the column holds the storage **key**);
`EXTERNAL` / `SHOPIFY` → `image.image_url` verbatim. Validate `https`. Compose at worker time so a
bucket or CDN change cannot strand queued rows; never persist the URL.

Record `shopify_media_id` and `media_status`. **Do not poll for `READY`** — processing is
asynchronous and the product existing at the till does not depend on it.

When no image is supplied, **omit the `media` key entirely** — do not send `null`, which would
change the document product sync emits today.

### Inventory (R5)

```graphql
mutation PreorderInventorySet($input: InventorySetQuantitiesInput!, $idempotencyKey: String!) {
  inventorySetQuantities(input: $input) @idempotent(key: $idempotencyKey) {
    inventoryAdjustmentGroup { createdAt reason referenceDocumentUri
                               changes { name delta quantityAfterChange } }
    userErrors { code field message }
  }
}
```

Variables: `name: "available"`, `reason: "correction"`,
`referenceDocumentUri: "managerbeyo://preorder/<sync_item_id>"`, and **one `quantities` entry per
selected location**, each carrying the **caller-supplied** `quantity` and `changeFromQuantity: null`.

**The quantity is caller input, not a constant.** Validate it as a non-negative `int` (rejecting
`bool`), capped at `1_000_000` to match the existing `_MAX_INVENTORY_INCREMENT`. `0` is legal and
means "clear the stock at this location".

Key: `shopify-preorder:<sync_item.client_id>:inventory-set` — a pure function of one value already
on the row. The whole set operation for a sync item is one logical action, so one key covers all
its locations, and a retry reproduces it exactly regardless of how many locations are involved.

Before the set: validate each location belongs to the shop and is active (the `set` path bypasses
`sync_inventory_adjustments`, so it needs its own check — mirror `_inventory_sync.py:53-70`), then
read the current `available` per location via `resolve_inventory_item_state` and record it as an
audit value. Enable tracking / activate the level if needed. **`add` mode is untouched** — same
ledger, same behaviour, same document.

**Why the audit value matters more now.** The overwrite is confirmed *and* the quantity arbitrary,
so `inventory_result_json` is the only record of what stock existed before a pre-order replaced it.
Persist `before_available` per location, alongside `compare_protection: "explicitly_bypassed"`.

### Trigger (R2)

Inside `create_task`'s **existing** `maybe_begin`, after `flush()` assigns `task.client_id`:
reject when `task_type is not PRE_ORDER` (`ValidationError`) or `ctx.role_name` is outside
`{admin, manager, seller}` (`PermissionDenied`) — both **before** any row is written, both local.
The pre-order section carries `inventory: [{location_id, quantity}]` — the same shape as today's
`inventory_adjustments`, with `quantity` replacing `quantity_to_add` because the semantics are
absolute. Then call the helper with `frontend_client_id = task.client_id` and `inventory_mode = SET`. Add
`"shopify_preorder": {…}` to the return dict. **Do not touch** the `pending_events` block.

## Acceptance criteria

1. Creating a `PRE_ORDER` task with a `shopify_preorder` section commits the sync item and an
   `OPEN` `ExecutionTask` **in the same transaction** as the `Task`; an exception later rolls back all three.
2. **No Shopify HTTP call during task creation** — asserted by test.
3. Non-`PRE_ORDER` task type, or a role outside `{admin, manager, seller}`, is rejected before any write.
4. On the dev store: the product is `UNLISTED`, **absent from the storefront — this is deferred
   Phase 0 gate 0.2, and it is the one criterion whose failure is a scope change rather than a
   bug** (see the risk below), has the supplied
   title / SKU / price / metafields / image, and shows **`available` equal to the quantity the
   caller selected** at each chosen location.
5. An existing SKU is reused and its price overwritten; **two distinct products sharing the SKU
   fail `ambiguous_product_match`** with no writes (this will occur — see R11).
6. **`custom.quantity = "6"` with an inventory selection of `2` yields `available = 2`.** Use
   different numbers so a wrong wiring cannot coincidentally pass.
6a. **An absolute set overwrites**: a location holding `5` with a selection of `2` ends at `2`,
   and `inventory_result_json` records `before_available: 5`.
7. Price reaches Shopify byte-identical to the caller's string.
8. Replaying task creation creates no second product and leaves the quantity at the selected value.
9. An image over 20 MB or 25 MP is rejected **at command time**, before the product exists.
10. `/products/process` behaviour is unchanged: `add` mode, the additive ledger, no `media` key
    when none is supplied, and a byte-identical `shopify.products.synced` payload.
11. `inventory_mode` is absent from every HTTP request schema.
12. `SHOPIFY_APP_SCOPES` unchanged; no merchant reauthorization.

## Validation plan

- `pytest app/tests/unit/services/infra/storage` — `public_url` for s3 / local / external; base-URL override honoured.
- `pytest app/tests/unit/services/infra/shopify` — `media` present only when supplied; **a call
  with no media emits today's document**; `@idempotent` present; `changeFromQuantity` explicit;
  `ignoreCompareQuantity` / `compareQuantity` absent; the additive document unchanged.
- `pytest app/tests/unit/services/tasks/shopify` — media resolver per provider; the single
  `inventory_mode` branch; **`custom.quantity = "6"` + inventory selection `2` → the mutation
  sends `quantity: 2`** (different numbers, so a crossed wiring fails); a location holding `5`
  set to `2` ends at `2` with `before_available: 5` recorded; multiple locations in one
  `quantities` array share one `@idempotent` key; quantity `0` is accepted; negative and `bool`
  rejected; duplicate SKU → zero writes; `add` mode still uses the ledger.
- `pytest app/tests/unit/services/commands/shopify` — image-limit validation; `image_id` XOR `image_url`.
- `pytest app/tests/integration/services/commands/tasks` — atomicity, rollback, role gate,
  task-type gate, `execute_shopify_graphql` never called.
- **Guard tests:** no request model exposes `inventory_mode`; `process_shopify_products` produces
  only `add` rows; `TaskType` gained no member; no merchant literal in `domain/` or `services/infra/`.
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
- `pytest app/tests` — full suite. `create_task` and product sync are both live paths.

## Risks and mitigations

- Risk: **the `UNLISTED` product leaks onto the storefront** (deferred Phase 0 gate 0.2, now
  verified here after implementation rather than before).
  Mitigation: probability is low — the merchant's live products are all `UNLISTED` and Shopify
  documents the status as excluded from search, collections and recommendations; the only
  realistic leak path is a sales channel with `autoPublish: true`.
  **If it happens, it is not a code fix.** No other `ProductStatus` works (`ACTIVE` is
  storefront-visible; `DRAFT` is invisible to Zettle). It requires `publishableUnpublish`,
  `read_publications` + `write_publications`, a Partner Dashboard change and a **merchant OAuth
  reauthorization for every installed shop**. Escalate for scope approval; do not work around it.
  Verification during the dev-store check: storefront search, `/collections/all`,
  `/sitemap_products_1.xml`, and `resourcePublications` on the created product. **A direct
  `/products/<handle>` URL loading is expected and is not a failure** — that is what `UNLISTED`
  means.
- Risk: the shared client/orchestrator changes regress live product sync.
  Mitigation: every addition is opt-in by payload; assert that a no-media, `add`-mode item emits
  the document it emits today; run the full suite.
- Risk: absolute set reaches the general HTTP route.
  Mitigation: `inventory_mode` is not in any request schema; guard test.
- Risk: a lost `productCreate` response duplicates the product.
  Mitigation: **accepted, unchanged from today** — this exists in product sync now. It is fixed by
  `PLAN_shopify_product_sync_duplicate_fix_20260727.md`, deliberately out of scope here.
- Risk: the absolute set destroys stock on a reused SKU — now with an **arbitrary** quantity, not
  just `1`.
  Mitigation: explicitly chosen (rev 9, after the additive alternative was put with its stock
  arithmetic and declined). `before_available` is recorded per location in `inventory_result_json`,
  making every overwrite auditable and hand-reversible. This is the audit trail's main purpose.
- Risk: the two caller-supplied quantities get crossed — `custom.quantity` reaching the inventory
  mutation, or the inventory quantity landing in the metafield.
  Mitigation: the regression test uses **different** numbers on purpose, so a crossed wiring
  cannot coincidentally pass. Keep it that way.

## Lifecycle transition

- Current state: `approved`
- Next state: `implemented` → `summarized` → `archived`
- Transition owner: `codex`
