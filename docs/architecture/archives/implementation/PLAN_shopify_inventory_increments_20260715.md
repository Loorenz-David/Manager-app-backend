# PLAN_shopify_inventory_increments_20260715

## Metadata

- Plan ID: `PLAN_shopify_inventory_increments_20260715`
- Status: `archived`
- Owner agent: `claude-opus-4-8`
- Created at (UTC): `2026-07-15T05:31:58Z`
- Last updated at (UTC): `2026-07-15T06:39:10Z`
- Related issue/ticket: `<id_or_link>`
- Intention plan: Shopify Inventory Increments to Product Sync (supplied inline; if persisted, `backend/docs/architecture/under_construction/intention/INTENTION_shopify_inventory_increments_20260715.md`)

## Goal and intent

- Goal: After a product-sync item successfully creates or updates a Shopify product/variant, apply **additive** inventory increments to one or more Shopify locations selected per shop by the frontend — never an absolute set, never a decrement.
- Business/user intent: A user syncing an item to Shopify can also say "add N units at location L" for each selected shop, in the same product-sync action, and have it reliably applied exactly once even across retries.
- Non-goals (from intention §15): absolute quantity set, decrements, transfers, reservations, committed/on-hand edits, Shopify→ManagerBeyo sync, auto-location choice, cross-shop location mapping, multi-variant expansion.

## Scope

- In scope:
  - Public API request field for per-location increments, carried through normalization → `ShopifyProductSyncItem.normalized_payload_json` → worker → Shopify infra client.
  - Inventory-item ID resolution, inventory tracking enablement, location activation, and additive adjustment via Shopify Admin GraphQL.
  - Per-location, retry-safe idempotency persisted on the sync item.
  - Location↔shop ownership validation.
  - Shopify scope additions (`read_locations`, `write_inventory`) and missing-scope handling/reauthorization surfacing.
  - A new query + route so the frontend can fetch each shop's locations, plus the frontend location-selection UI and payload construction.
  - Tests at every layer.
- Out of scope: everything in Non-goals; changing the existing create/update/metafield behavior when no adjustments are supplied.
- Assumptions:
  - The existing single-variant model (one variant per product-sync item) is unchanged; inventory is applied to that one variant's inventory item.
  - `inventoryAdjustQuantities` (Admin GraphQL, `2024-x`+) supports multiple `changes` atomically — **verify against `settings.shopify_api_version` during Phase 0** (see Clarifications).
  - **Confirmed with owner (2026-07-15):** the frontend sends each inventory adjustment **tagged with the `shop_integration_id` it belongs to**. So a single request item can still fan out to multiple shops (as today); the normalizer routes each adjustment to the matching per-`(item, shop)` sync item by shop id. No forced one-shop-per-item split is required — the shop tag makes the shop-scoped location IDs unambiguous.

## Clarifications required

- [x] **Resolved — API version.** `settings.shopify_api_version` is pinned to `2026-01`; the implemented batched `inventoryAdjustQuantities` and zero-baseline `inventoryActivate` operations match that contract.
- [x] **Resolved — scopes.** `read_locations` is required for the live locations query and `write_inventory` is required for inventory mutations; the execution gate requires both and product-only sync remains unaffected.
- [x] **Resolved — lost-response/idempotency risk.** The durable ledger, Shopify mutation idempotency keys, and pre-adjust baseline reconciliation are the accepted mitigation for a response lost after Shopify accepts a mutation.
- [x] **Resolved — observability.** Per-location `inventory_result_json`, ledger state, structured worker errors, and the existing product-sync event are sufficient; no new `ShopifyIntegrationEventTypeEnum` value is needed.
- [x] **(Resolved — option b) Retry model / cross-resubmit idempotency.** Verified: `handle_shopify_process_products` never re-raises ([handle_shopify_process_products.py:78-89](../../../../app/beyo_manager/services/tasks/shopify/handle_shopify_process_products.py)), so a failed sync *item* does **not** trigger the worker's task retry ([worker_base.py:193](../../../../app/beyo_manager/services/infra/execution/worker_base.py)); the dominant recovery path is the **user re-submitting the form**, which creates new `ShopifyProductSyncItem` rows. **Decision (owner, 2026-07-15): adopt the durable ledger** — new `shopify_inventory_adjustments` table keyed on `(shop_integration_id, frontend_client_id, shopify_location_id)`, consulted before every adjust (see "Durable inventory-adjustment ledger" and the ledger-based idempotency strategy). This makes AC-6 achievable across re-submits. Duplicate *product* creation remains prevented independently by the identity→UPDATE lookup.
- [x] **Resolved — partial-success status representation.** Inventory failures use the existing `FAILED` item state with per-location outcomes in `inventory_result_json`; no new enum value or migration is needed.
- [x] **Resolved — role gating.** Inventory writes inherit the existing product-sync roles: `ADMIN`, `MANAGER`, `SELLER`, and `WORKER`.

## Acceptance criteria

1. A product-sync request with no inventory field behaves byte-for-byte as today (normalized payload, create/update, metafields, result serialization all unchanged).
2. A request with `inventory_adjustments` for a single-shop item results in the variant's available quantity increasing by exactly the requested delta at each requested location (e.g. 3 + 2 = 5, never "set to 2").
3. Inventory processing runs only after the Shopify product, variant, and inventory-item IDs are known; for a newly created product it waits for the default variant/inventory item.
4. A location ID not belonging to the shop being processed fails **that shop's** sync item with a specific error code and never mutates another shop.
5. Enabling tracking and/or activating an inactive location never itself double-applies the requested delta (idempotent infra preparation).
6. After create/update succeeds and IDs are persisted, an inventory failure marks the item FAILED with an inventory-specific `error_code`; a retry neither creates a duplicate product nor re-applies an already-applied increment.
7. Multi-location: partial results are recorded per location; a retry only re-attempts locations not yet marked applied.
8. Zero → dropped (no-op), negative → rejected, malformed GID → rejected, duplicate location → rejected/consolidated deterministically before any Shopify call.
9. A shop whose stored token lacks the new scopes fails inventory items with a `missing_inventory_scope` code and is surfaced for reauthorization, while product-only syncs for that shop still succeed.
10. The frontend can fetch per-shop locations, select locations + quantities grouped by shop, and submit only complete rows; 0 is preserved as "no increment."

## Contracts and skills

### Contracts loaded

- [architecture/57_shopify_integration.md](../../../../architecture/57_shopify_integration.md): the authoritative extension guide — worker/queue reuse, "task payloads carry IDs only," infra-client boundary ("never call Shopify from a command/handler except the documented OAuth exception; product processing runs on `queue:shopify`"), enum-migration idiom, integration-event and no-secret-serialization rules.
- [architecture/06_commands.md](../../../../architecture/06_commands.md): command shape (`session.begin()`, flush, error-raising) for `process_shopify_products` changes and any new query/command.
- [architecture/07_queries.md](../../../../architecture/07_queries.md): query shape for the new `get_shopify_locations` read.
- [architecture/09_routers.md](../../../../architecture/09_routers.md): `run_service` + `build_ok`/`build_err`, role gating for the new locations route.
- [architecture/46_serialization.md](../../../../architecture/46_serialization.md): result-dataclass → `asdict` output shape for the locations response.
- [architecture/16_background_jobs.md](../../../../architecture/16_background_jobs.md), [architecture/51_worker_runtime.md](../../../../architecture/51_worker_runtime.md): retry semantics — the basis for the idempotency design.
- [architecture/19_integrations.md](../../../../architecture/19_integrations.md): external-adapter pattern for the new inventory GraphQL client.
- [architecture/18_security.md](../../../../architecture/18_security.md): token encryption at rest; never log tokens; scope handling.
- [architecture/30_migrations.md](../../../../architecture/30_migrations.md): additive column + `ALTER TYPE ... ADD VALUE IF NOT EXISTS` idiom.
- [architecture/24_multi_tenancy.md](../../../../architecture/24_multi_tenancy.md): workspace scoping on the new query.

### Local extensions loaded

- `architecture/06_commands_local.md`, `architecture/07_queries_local.md`, `architecture/46_serialization_local.md`: apply if they add project-specific deltas at implementation time (read before writing each layer).

### File read intent — pattern vs. relational

Relational reads already performed (understanding what exists), all confirmed:
- [product_sync_client.py](../../../../app/beyo_manager/services/infra/shopify/product_sync_client.py) — GraphQL ops, `create_shopify_product`/`update_shopify_product`/`_bulk_update_variant` return shapes.
- [_product_sync_orchestrator.py](../../../../app/beyo_manager/services/tasks/shopify/_product_sync_orchestrator.py) — the sync-item lifecycle, identity resolution, "persist IDs before metafields" comment.
- [handle_shopify_process_products.py](../../../../app/beyo_manager/services/tasks/shopify/handle_shopify_process_products.py) — batch loop, per-item error handling, `shopify.products.synced` emit shape.
- [process_shopify_products.py](../../../../app/beyo_manager/services/commands/shopify/process_shopify_products.py), [_product_sync_normalizer.py](../../../../app/beyo_manager/services/commands/shopify/_product_sync_normalizer.py), [product_sync_payloads.py](../../../../app/beyo_manager/domain/shopify/product_sync_payloads.py) — request → normalized `{product, variant, metafields}` → per-`(item, shop)` `ShopifyProductSyncItem` rows.
- [process_shopify_products_request.py](../../../../app/beyo_manager/services/commands/shopify/requests/process_shopify_products_request.py) — pydantic request schema and validators.
- [shopify_product_sync_item.py](../../../../app/beyo_manager/models/tables/shopify/shopify_product_sync_item.py) — columns; `normalized_payload_json`, `shopify_product_id/variant_id`, `error_code/message`.
- [scopes.py](../../../../app/beyo_manager/domain/shopify/scopes.py) — `write_` implies `read_`; missing-scope comparison.
- [graphql_client.py](../../../../app/beyo_manager/services/infra/shopify/graphql_client.py) — `execute_shopify_graphql`, `raise_for_graphql_user_errors`, retryable vs non-retryable error classes.
- [shop_client.py](../../../../app/beyo_manager/services/infra/shopify/shop_client.py) / [metafield_definition_client.py](../../../../app/beyo_manager/services/infra/shopify/metafield_definition_client.py) — infra-client shape to mirror for the locations/inventory client.
- [get_shopify_scope_status.py](../../../../app/beyo_manager/services/queries/shopify/get_shopify_scope_status.py) — query + workspace-scoping template for the locations query.
- Frontend: [ShopifyProductSyncForm.tsx](../../../../frontend/packages/shopify/src/components/ShopifyProductSyncForm.tsx), [ShopifyProductSyncShopField.tsx](../../../../frontend/packages/shopify/src/components/fields/ShopifyProductSyncShopField.tsx), [resolve-shopify-product-sync-submit.ts](../../../../frontend/packages/shopify/src/lib/resolve-shopify-product-sync-submit.ts), [types.ts](../../../../frontend/packages/shopify/src/types.ts) — form/staged-form conventions, per-shop splitting precedent, request/response zod schemas.

No prohibited pattern reads needed — behavioral shapes come from the contracts above.

### Skill selection

- Primary skill: none required beyond the standard backend/frontend implementation flow. This is a planning artifact; implementation happens in a follow-up.
- Router trigger terms: `shopify`, `inventory`, `product sync`.
- Excluded alternatives: `dataviz` — no charts.

## Key architecture findings (research summary)

1. **Lifecycle:** `POST /api/v1/integrations/shopify/products/process` → [process_shopify_products.py:22](../../../../app/beyo_manager/services/commands/shopify/process_shopify_products.py) → `resolve_and_normalize_sync_targets` → `build_normalized_product_sync_payload` → one `ShopifyProductSyncItem` per `(item, target shop)` with `normalized_payload_json = {product, variant, metafields}` → enqueue `SHOPIFY_PROCESS_PRODUCTS` → [handle_shopify_process_products.py](../../../../app/beyo_manager/services/tasks/shopify/handle_shopify_process_products.py) → `sync_one_product_sync_item` → [product_sync_client.py](../../../../app/beyo_manager/services/infra/shopify/product_sync_client.py).
2. **Shared payload across shops today:** the *same* `normalized_payload` dict object is attached to every target shop's row ([_product_sync_normalizer.py:41-48](../../../../app/beyo_manager/services/commands/shopify/_product_sync_normalizer.py)). Because location GIDs are shop-scoped, inventory data **cannot** be shared this way. Since the frontend tags each adjustment with its `shop_integration_id` (owner-confirmed), the normalizer deep-copies the payload per target shop and attaches only that shop's slice of adjustments — no forced one-shop-per-item constraint.
3. **No existing Shopify locations query.** The `location_tracker` infra package is unrelated internal item-location tracking, not Shopify. A new live locations query/client is required (analogous to how `get_shopify_metafield_preferences` fetches definitions live).
4. **Scopes:** `SHOPIFY_APP_SCOPES` env (`app/.env:111`) + `config.py:108`; currently no inventory/location scopes. `write_inventory` implies `read_inventory` via `_expand_implied_scopes` ([scopes.py:32-38](../../../../app/beyo_manager/domain/shopify/scopes.py)); `read_locations` must be added explicitly.
5. **ID persistence guarantee:** IDs are persisted immediately after create/update, before metafields, precisely to avoid duplicate creates on retry ([_product_sync_orchestrator.py:104-109](../../../../app/beyo_manager/services/tasks/shopify/_product_sync_orchestrator.py)). Duplicate-create protection on retry is also inherent: the SKU/barcode identity lookup finds the now-existing product and takes the UPDATE path.
6. **Inventory-item ID is free from the variant bulk update:** both create and update paths funnel through `_bulk_update_variant`. Adding `inventoryItem { id }` to `BULK_UPDATE_VARIANT_MUTATION`'s response yields the inventory-item ID for both paths with **no extra Shopify request**.
7. **Retry reality (verified — important):** `handle_shopify_process_products` catches per-item exceptions, marks the item FAILED, and **returns normally without re-raising** ([handle_shopify_process_products.py:78-89](../../../../app/beyo_manager/services/tasks/shopify/handle_shopify_process_products.py)). The worker's `_schedule_retry_or_fail` only runs when the handler *raises* ([worker_base.py:193](../../../../app/beyo_manager/services/infra/execution/worker_base.py)). **Therefore a failed sync item does not trigger a task retry** — the dominant recovery path is a **user re-submit**, which creates fresh sync-item rows with empty ledgers. A per-item ledger would only guard task-level re-delivery (rare); it does **not** guard cross-resubmit increments. **Resolved** by the durable `shopify_inventory_adjustments` ledger keyed on `(shop_integration_id, frontend_client_id, shopify_location_id)` — see that section and the ledger-based idempotency strategy.

## Contracts and data shapes to define

### Public API input (additive, backward compatible)

Extend `ProcessShopifyProductItemRequest` ([process_shopify_products_request.py](../../../../app/beyo_manager/services/commands/shopify/requests/process_shopify_products_request.py)):

```
inventory_adjustments: list[InventoryAdjustmentRequest] | None = None

class InventoryAdjustmentRequest(BaseModel):
    shop_integration_id: str    # which shop this location/delta belongs to
    location_id: str            # Shopify Location GID (belongs to shop_integration_id)
    quantity_to_add: int
```

Request-layer validation rules (align with existing validator style):
- `shop_integration_id` must be one of the item's resolved target shops (i.e. present in `target_shop_integration_ids` if given, otherwise in the workspace's active shop set) → else reject (`inventory_adjustment_shop_not_targeted`). This is a request/normalization-level structural check; **actual location↔shop ownership is still validated live at execution** (only Shopify can be trusted for that).
- `location_id` must match `gid://shopify/Location/<digits>` → else reject (`ValidationError`).
- `quantity_to_add`: integer; **zero is dropped/normalized away** (not an error → row removed); **negative is rejected**; must be ≤ a sane cap (e.g. 1_000_000).
- Duplicate `(shop_integration_id, location_id)` within one item → reject (`duplicate_inventory_location`) OR consolidate deterministically — **choose reject** for a narrow, predictable contract.
- No single-shop constraint: a single item may carry adjustments for several shops, each tagged with its own `shop_integration_id`. Missing/`None`/empty adjustments → unchanged behavior.

### Internal normalized shape (persisted in `normalized_payload_json`)

Add one key; absence = today's behavior:

```
"inventory": {
    "adjustments": [
        {"location_id": "gid://shopify/Location/123", "quantity_to_add": 2}
    ]
}
```

- Built in `build_normalized_product_sync_payload` from the request item (zeros already dropped, deduped, validated upstream). The stored payload holds **only the adjustments for that one shop** — the `shop_integration_id` tag is consumed during routing and not persisted per-adjustment (it's implicit in the per-`(item, shop)` row).
- Renamed/transformed: frontend `quantityToAdd`/`locationId`/`shopIntegrationId` → snake_case wire; the shop tag is used to route, then dropped; `location_id`/`quantity_to_add` persist unchanged for auditability.
- `resolve_and_normalize_sync_targets` change: for each target shop, deep-copy the base payload and attach `inventory.adjustments = [a for a in item.inventory_adjustments if a.shop_integration_id == shop.client_id]`; omit the `inventory` key entirely when that shop's slice is empty. Deep-copy avoids aliasing the shared payload object across shops.

### Sync-item persistence additions (migration)

Additive columns on `shopify_product_sync_items`:
- `shopify_inventory_item_id: String(255) | None` — resolved inventory-item GID (nullable; only set when adjustments requested).
- `inventory_result_json: JSONB | None` — a **denormalized per-item summary** for the `shopify.products.synced` event payload and the item detail view (what this item requested + the outcome per location). It is **not** the idempotency source of truth — that is the durable ledger table below. Shape:

```
{
  "adjustments": [
    { "location_id": "gid://shopify/Location/123", "requested_delta": 2,
      "outcome": "applied",            // applied | already_applied | failed
      "shopify_error_code": null }
  ]
}
```

### Durable inventory-adjustment ledger — `shopify_inventory_adjustments` (new table, resolves the retry clarification)

The authoritative, cross-resubmit idempotency record. One row per intended increment `(shop, item-identity, location)`. Because a failed sync item is recovered by **user re-submit** (a *new* sync-item row — finding #7), idempotency must key on something stable across re-submits, not on the sync-item `client_id`. The item's `frontend_client_id` (already on `ShopifyProductSyncItem`, the frontend's stable per-item id backed by its draft store) provides exactly that.

Model (`models/tables/shopify/shopify_inventory_adjustment.py`, `IdentityMixin` + `Base`, `CLIENT_ID_PREFIX = "shpia"`):

| Column | Type | Notes |
|---|---|---|
| `client_id` | PK (`shpia_…`) | from IdentityMixin |
| `workspace_id` | FK workspaces | multi-tenancy scope |
| `shop_integration_id` | FK shopify_shop_integrations | which shop |
| `sync_item_id` | FK shopify_product_sync_items, nullable | the item that **last** touched this row (audit/traceability; updated on re-submit) |
| `frontend_client_id` | String(255) | stable item identity — part of the idempotency key |
| `shopify_inventory_item_id` | String(255) | resolved inventory-item GID |
| `shopify_location_id` | String(255) | target Location GID |
| `requested_delta` | Integer | the positive increment |
| `baseline_available` | Integer, nullable | `available` snapshot read immediately before the adjust (lost-response reconciliation) |
| `status` | enum `shopify_inventory_adjustment_status_enum` | `pending` \| `applied` \| `failed` |
| `reference_uri` | String(255) | `managerbeyo://inventory-adjustment/<client_id>`; passed to Shopify `referenceDocumentUri` for traceability (Shopify does **not** dedupe on it) |
| `shopify_error_code` | String(64), nullable | last failure code |
| `applied_at` | DateTime(tz), nullable | when it reached `applied` |
| `created_by_id` | FK users, nullable | who initiated |
| `created_at` / `updated_at` | DateTime(tz) | standard |

**Idempotency key (DB-enforced):** unique index on `(shop_integration_id, frontend_client_id, shopify_location_id)`. This is the single source of truth for "has this item's increment at this location already happened," surviving any number of re-submits.

**Consequence to state in the frontend contract:** because the key includes `frontend_client_id`, re-submitting the *same* item (same draft) is idempotent (skipped), while starting a *fresh* sync (new `frontend_client_id`) is a new, legitimate increment. Editing the quantity on the same draft and re-submitting does **not** add the difference again — deliberate, matching this feature's narrow "add once per item per location" scope (§ Non-goals). A genuinely new increment is a new item.

**New status enum:** `ShopifyInventoryAdjustmentStatusEnum(pending|applied|failed)` in `domain/shopify/enums.py`; created via `create_type=True` + Alembic (additive, per [architecture/30_migrations.md](../../../../architecture/30_migrations.md)).

**Observability:** this table alone satisfies intention §13 — it carries shop, inventory-item, location, delta, status, error code, and reference, and joins to the sync item for product/variant IDs. No separate audit structure needed.

### Locations query response (new read)

`GET /api/v1/integrations/shopify/locations?shop_integration_ids=<id,id>` → workspace-scoped; fans out across the selected shops and returns live locations grouped by shop (mirrors the `{ "shops": [...] }` shape of `get_shopify_metafield_preferences`):

```
{ "shops": [
  { "shop_integration_id": "shpint_…", "shop_domain": "…", "status": "ok",
    "locations": [ { "location_id": "gid://shopify/Location/123", "name": "Warehouse A", "is_active": true } ] },
  { "shop_integration_id": "shpint_…", "shop_domain": "…", "status": "needs_reauth", "locations": [] }
] }
```

`status` is one of `ok` / `needs_reauth` (shop missing `read_locations`) / `error` (live fetch failed) — per-shop isolation so one shop never blanks the whole picker. Result dataclass in `domain/shopify/results.py` + serializer in `domain/shopify/serializers.py`.

### Locations query — how it works

This is a **live read inside an HTTP query**, which is the established pattern for `get_shopify_metafield_preferences` ([get_shopify_metafield_preferences.py](../../../../app/beyo_manager/services/queries/shopify/get_shopify_metafield_preferences.py)) — the one query in the codebase that already calls Shopify inline. Contract 57's "never call Shopify inline from an HTTP handler" rule targets **mutations/business processing** (which must go through `queue:shopify`); read-only lookups feeding a picker are the documented exception (alongside the OAuth token exchange). So locations does **not** need a worker round-trip.

Three pieces, each a smaller copy of an existing shape:

1. **Infra client — `inventory_client.py:fetch_shop_locations`** — GraphQL read over the shared `execute_shopify_graphql`:

   ```graphql
   query GetLocations($first: Int!, $after: String) {
     locations(first: $first, after: $after, includeInactive: true) {
       edges { node { id name isActive } }
       pageInfo { hasNextPage endCursor }
     }
   }
   ```

   Paginates until `hasNextPage` is false (defensive cap, e.g. 250). Returns `[{ "location_id", "name", "is_active" }]`. **`includeInactive: true` is required** — an inactive location is still a valid activation target for inventory (§ Inventory tracking/activation), so the picker must surface it.

2. **Query — `get_shopify_locations.py`** (mirrors `get_shopify_metafield_preferences`):
   - Reads `shop_integration_ids` from `ctx.query_params` (multi-shop fan-out → one call fills the grouped-by-shop UI).
   - Workspace-scopes exactly like that query's `_resolve_integrations`: loads `WHERE workspace_id = ctx.workspace_id AND client_id IN (...) AND is_deleted = false`; a requested id not owned by the workspace → `NotFound` (the IDOR guard).
   - Per shop, checks `has_all_required_scopes(("read_locations",), integration.granted_scopes)` **before** calling Shopify. Missing scope → that shop's slice returns `status: "needs_reauth"` with empty `locations` (no raise), so one un-reauthorized shop doesn't blank the picker and the UI can show a per-shop reauthorize CTA. A live-fetch failure for one shop → `status: "error"`, others still returned.
   - Runs the assembled `{ "shops": [...] }` through the new serializer.

3. **Route — `GET /integrations/shopify/locations`** in [routers/api_v1/shopify.py](../../../../app/beyo_manager/routers/api_v1/shopify.py): standard `run_service` + `build_ok`/`build_err`, same role gate as the metafield-preferences GET (`ADMIN, MANAGER, SELLER, WORKER`).

**Single source of truth for ownership:** `fetch_shop_locations` is reused by the worker at execution time for the live location↔shop ownership validation (§ Location ownership). The picker and the enforcement therefore share one definition of "which locations belong to this shop" and cannot drift.

**No caching/persistence:** locations are few and change rarely; a live fetch per request plus React Query client-side caching is sufficient. Deliberately no server-side cache and no `shopify_locations` table — the intention permits persistence "only when supported by an existing architectural need," and there is none here.

### `shopify.products.synced` result additions

Extend `_success_entry`/`_failure_entry` ([handle_shopify_process_products.py:107-126](../../../../app/beyo_manager/services/tasks/shopify/handle_shopify_process_products.py)) with an optional `inventory` summary (requested vs applied per location) so the frontend can show which increments landed. Backward compatible (new optional field).

## Execution sequence (worker) — chosen ordering and consequences

Chosen order inside `sync_one_product_sync_item`:

```
resolve identity (sku→barcode)        [unchanged]
  ↓
create or update product + variant     [unchanged]
  ↓
persist shopify_product_id / variant_id [unchanged — happens before anything non-idempotent]
  ↓
if payload.inventory present:
    resolve shopify_inventory_item_id   [from bulk-update response; persist it]
    validate every location belongs to this shop (live locations fetch)
    ensure inventory tracking enabled (idempotent)
    per location: activate if no level exists (at 0, never with quantity)
    batched inventoryAdjustQuantities for not-yet-applied locations
    record per-location results in inventory_result_json (two-phase)
  ↓
set metafields                          [unchanged; metafieldsSet is idempotent]
  ↓
mark SUCCEEDED
```

**Ordering decision:** inventory runs **before** metafields (as the intention diagram shows), *and* metafields stays idempotent, so retry is safe regardless of order. The load-bearing guarantee is **not** the ordering but the durable `shopify_inventory_adjustments` ledger: no `(shop, item-identity, location)` increment is ever applied twice, whatever runs after it and however many times the user re-submits. Consequence: an item can reach a "product created + some inventory applied + metafields failed" state; on re-submit, identity resolves to UPDATE (no dup product), already-`applied` ledger rows are skipped, remaining locations are attempted, and metafields are re-applied idempotently.

## Inventory-item resolution (no extra requests)

- Add `inventoryItem { id }` to `BULK_UPDATE_VARIANT_MUTATION`'s `productVariants` selection ([product_sync_client.py:67-83](../../../../app/beyo_manager/services/infra/shopify/product_sync_client.py)) and return it from `_bulk_update_variant` / `create_shopify_product` / `update_shopify_product`.
- Persist to `sync_item.shopify_inventory_item_id`. Treated as **required** whenever adjustments were requested — if missing, fail the item `inventory_item_unresolved` (do not silently skip inventory).
- Also add `inventoryItem { id }` to `FIND_PRODUCT_VARIANTS_BY_IDENTITY_QUERY` as a fallback source for the UPDATE path, but prefer the bulk-update response (single source, both paths).

## Location ownership + tracking/activation (deterministic four-case matrix)

Ownership: fetch the shop's location GID set live (reuse the locations client) at execution; any requested location not in the set → fail the item `location_not_in_shop`. Ownership is shop-state only Shopify can be trusted for, so it is validated at execution, not (only) at request time. Request-time validation is limited to GID format/zero/negative/duplicate.

Tracking + activation, per location (queried via `inventoryItem { tracked }` + `inventoryLevel(locationId:)`):

| Tracked? | Location level exists? | Action |
|---|---|---|
| tracked | active/level exists | `inventoryAdjustQuantities` delta only |
| tracked | no level | `inventoryActivate(item, location)` **at 0**, then adjust delta |
| not tracked | level exists | `inventoryItemUpdate {tracked:true}` (idempotent), then adjust delta |
| not tracked | no level | `inventoryItemUpdate {tracked:true}`, `inventoryActivate` **at 0**, then adjust delta |

**Never** pass a non-zero `available` to `inventoryActivate` — activation is separated from the delta so preparation cannot double-apply (satisfies AC-5). Tracking-enable and activate are both idempotent no-ops if already done.

## Retry-safe increment / idempotency strategy (ledger-based, two-phase)

The authority is the `shopify_inventory_adjustments` table, **not** the sync item — so this holds across user re-submits (the real retry path), not just same-item re-execution.

Per requested `(location, delta)`, inside `_inventory_sync`:
1. **Claim the row:** `INSERT ... ON CONFLICT (shop_integration_id, frontend_client_id, shopify_location_id) DO NOTHING` with `status="pending"`, `requested_delta`, `reference_uri = managerbeyo://inventory-adjustment/<client_id>`; then re-load the row (whether just inserted or pre-existing).
2. **Branch on the loaded row's status:**
   - `applied` → **skip** the Shopify call; record `outcome="already_applied"` in the item summary. (Idempotent hit — this is the re-submit protection.)
   - `pending` with a recorded `baseline_available` (a prior attempt reached step 3 but we never confirmed — the "accepted but response lost" case) → **reconcile**: re-read current `available`; if it equals `baseline_available + requested_delta` the prior adjust landed → mark `applied` without re-adjusting; else treat as not-landed and proceed to step 3.
   - `pending` with no baseline, or `failed` (a genuine prior failure to retry) → proceed to step 3.
3. **Prepare + adjust:** read current `available` → persist as `baseline_available`, commit; ensure tracking/activation (idempotent, activate at 0); then `inventoryAdjustQuantities` (batched across all locations at step 3 this run).
4. **Confirm:** on success → `status="applied"`, `applied_at`, commit; on Shopify userError/rejection → `status="failed"`, `shopify_error_code`, commit.

Residual risk: a concurrent external inventory change between the baseline read and a reconcile re-read can make the `baseline + delta` comparison lie (single-writer assumption per location). Documented and accepted — the `reference_uri` on each Shopify mutation leaves an audit trail for manual reconciliation if it ever matters.

Duplicate-**product** creation is independently prevented by the SKU/barcode identity→UPDATE lookup (finding #5), so a re-submit after a lost create response updates the existing product rather than duplicating it; the ledger covers the increment, which has no such natural identity.

## Partial success across locations

- Prefer **one batched** `inventoryAdjustQuantities` for all not-yet-applied active locations (atomic per Shopify). Locations needing activation are activated first (per-item-per-location), then included in the batch.
- All succeed → all ledger entries `applied`; item SUCCEEDED.
- Batch fails before any change → nothing applied (atomic) → item FAILED `inventory_adjust_failed`; ledger entries stay `pending`; retry re-attempts all pending.
- Activation of location N fails after locations 1..N-1 activated (activation is not batched) → those activated-but-not-adjusted locations have no delta applied yet (activation was at 0) → item FAILED; retry resumes safely (activation idempotent, ledger still pending).
- `inventory_result_json` always records requested-vs-completed per location for observability and frontend display.

## Scopes + installation compatibility

- Add `read_locations,write_inventory` to `SHOPIFY_APP_SCOPES` (`app/.env`, deployment env, Shopify Partner Dashboard app config per [architecture/33_deployment.md](../../../../architecture/33_deployment.md)).
- Define a module-level `_REQUIRED_INVENTORY_SCOPES = ("read_locations", "write_inventory")` (mirrors [lookup_shopify_customers_by_product_identity.py:22](../../../../app/beyo_manager/services/queries/shopify/lookup_shopify_customers_by_product_identity.py)).
- At execution, when adjustments are present, check `has_all_required_scopes(_REQUIRED_INVENTORY_SCOPES, shop.granted_scopes)` before any inventory call. Missing → fail the item `missing_inventory_scope` with a safe message pointing to reauthorization; **do not** attempt the mutation.
- Product-only sync (no adjustments) remains fully functional for shops lacking the new scopes.
- Frontend: when a selected shop's `scope_statuses`/`granted_scopes` lack inventory scopes, disable inventory entry for that shop and surface the existing reauthorize CTA.

## Observability

- Structured logs per inventory op: shop_integration_id, product_id, variant_id, inventory_item_id, location_id, requested_delta, operation (`activate`/`adjust`/`enable_tracking`), success/failure, error_code, `reference_uri`. **Never** log tokens (enforced by existing client; do not add token to logs).
- `inventory_result_json` is the per-item audit record. No new `ShopifyIntegrationEventTypeEnum` value unless Clarification #4 says otherwise; the existing `PRODUCT_SYNC` batch event's `metadata_json` may gain an aggregate inventory count (safe, non-secret).

## Frontend intent

- New API + query: `api/list-shopify-locations.ts` + `api/use-list-shopify-locations-query.ts` (keyed on the selected `shop_integration_ids`) hitting `GET /integrations/shopify/locations?shop_integration_ids=…`, returning the grouped `{ shops: [...] }` shape.
- Form values: extend `ShopifyProductSyncFormSchema` with `inventoryAdjustments: Array<{ shopIntegrationId, locationId, quantityToAdd }>` (default `[]`).
- New independent field component `components/fields/ShopifyProductSyncInventoryField.tsx` (project convention: fields are independent; the form orchestrates). Renders, per selected shop, that shop's fetched locations grouped under a shop header, each with a quantity input. Each emitted row carries `{ shopIntegrationId, locationId, quantityToAdd }`, so a shop's location can never be attributed to another shop.
- Add to a staged step (extend the "target" step or add an "Inventory" step in `useStagedForm`).
- `resolve-shopify-product-sync-submit.ts`: build `inventory_adjustments` (each tagged with its `shop_integration_id`) from rows with `quantityToAdd > 0`, dropping zero/empty rows (preserve `0` as "no increment" — never send it). Attach the full tagged list to the item; the **backend normalizer** routes each adjustment to the right per-shop sync item, so the frontend does **not** need to force a per-shop item split for inventory. Keep the existing metafield-driven split as-is; when metafields already split the item per shop, filter the adjustments to that shop before attaching. No adjustments → unchanged single/multi-shop item.
- `types.ts`: add `InventoryAdjustmentRequestSchema` and extend `ProcessShopifyProductItemRequestSchema` (optional field) + a `ShopifyLocation`/list-response schema.

## Files to create

Backend:
- `app/beyo_manager/services/infra/shopify/inventory_client.py` — GraphQL ops: `fetch_shop_locations`, `resolve_inventory_item_state` (tracked + per-location level presence + current `available`), `enable_inventory_tracking`, `activate_inventory_at_location`, `adjust_inventory_quantities` (batched).
- `app/beyo_manager/services/tasks/shopify/_inventory_sync.py` — orchestration helper called by `sync_one_product_sync_item` (scope check, ownership validation, ledger claim/branch/prepare/adjust/confirm, item summary write).
- `app/beyo_manager/models/tables/shopify/shopify_inventory_adjustment.py` — the durable ledger model (`CLIENT_ID_PREFIX = "shpia"`).
- `app/beyo_manager/services/queries/shopify/get_shopify_locations.py` — workspace-scoped live locations read.
- `app/migrations/versions/<rev>_add_shopify_inventory.py` — additive columns on `shopify_product_sync_items` (`shopify_inventory_item_id`, `inventory_result_json`) **+ create `shopify_inventory_adjustments` table** with its unique index and `shopify_inventory_adjustment_status_enum`.
- Tests (see §Testing).

Frontend:
- `components/fields/ShopifyProductSyncInventoryField.tsx`
- `api/list-shopify-locations.ts`, `api/use-list-shopify-locations-query.ts`

## Files to modify

Backend:
- [process_shopify_products_request.py](../../../../app/beyo_manager/services/commands/shopify/requests/process_shopify_products_request.py) — `InventoryAdjustmentRequest` (with `shop_integration_id`), field + validators (GID/zero/negative/duplicate + "shop targeted" check).
- [product_sync_payloads.py](../../../../app/beyo_manager/domain/shopify/product_sync_payloads.py) — emit `inventory` key.
- [_product_sync_normalizer.py](../../../../app/beyo_manager/services/commands/shopify/_product_sync_normalizer.py) — per-target deep-copy + attach inventory to the single target shop.
- [shopify_product_sync_item.py](../../../../app/beyo_manager/models/tables/shopify/shopify_product_sync_item.py) — new columns.
- [product_sync_client.py](../../../../app/beyo_manager/services/infra/shopify/product_sync_client.py) — `inventoryItem { id }` in bulk-update (and identity) selections; return inventory-item id.
- [_product_sync_orchestrator.py](../../../../app/beyo_manager/services/tasks/shopify/_product_sync_orchestrator.py) — resolve/persist inventory-item id; call `_inventory_sync`; new inventory error codes in the caught-exception set.
- [handle_shopify_process_products.py](../../../../app/beyo_manager/services/tasks/shopify/handle_shopify_process_products.py) — inventory summary in success/failure entries.
- [routers/api_v1/shopify.py](../../../../app/beyo_manager/routers/api_v1/shopify.py) — new `GET /locations` route; extend `ShopifyProcessProductsBody` (item schema) for `inventory_adjustments`.
- `domain/shopify/results.py` + `domain/shopify/serializers.py` — locations result + serializer.
- `app/beyo_manager/config.py` + `app/.env` — `SHOPIFY_APP_SCOPES` add `read_locations,write_inventory`.
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` — document the locations route + the new request field.

Frontend:
- [types.ts](../../../../frontend/packages/shopify/src/types.ts), [ShopifyProductSyncForm.tsx](../../../../frontend/packages/shopify/src/components/ShopifyProductSyncForm.tsx), [resolve-shopify-product-sync-submit.ts](../../../../frontend/packages/shopify/src/lib/resolve-shopify-product-sync-submit.ts), `api/index.ts`, `api/shopify-keys.ts`.

## Implementation plan (phased)

1. **Phase 0 — API-version + scope verification.** Confirm GraphQL mutation names/shapes and scope names against `settings.shopify_api_version`; resolve Clarifications 1–2. Adjust the client method signatures accordingly. No app code merged until confirmed.
2. **Phase 1 — Request + normalization contract.** `InventoryAdjustmentRequest` (shop-tagged), validators, per-shop routing in the normalizer, `inventory` normalized key, per-target attach. Tests: schema validation + normalization/persistence (incl. multi-shop routing) + "no inventory preserves current behavior."
3. **Phase 2 — Persistence.** Migration: additive columns on `shopify_product_sync_items` + new `shopify_inventory_adjustments` table (model, status enum, unique index on `(shop_integration_id, frontend_client_id, shopify_location_id)`). Test the migration applies/round-trips and the unique index rejects a duplicate claim.
4. **Phase 3 — Inventory infra client.** `inventory_client.py` GraphQL ops behind the existing `execute_shopify_graphql`; unit tests via the project's Shopify infra-client mock pattern (locations fetch, tracking, activate, batched adjust, userErrors).
5. **Phase 4 — Inventory-item resolution.** `inventoryItem { id }` in bulk-update; thread the id through create/update return; persist. Tests: create path + update path resolve the id; missing id fails `inventory_item_unresolved`.
6. **Phase 5 — Orchestration + ledger idempotency.** `_inventory_sync.py`: ownership validation, four-case prepare, ledger claim→branch→prepare→adjust→confirm, batched adjust; wire into orchestrator before metafields; add inventory error codes. Tests: create+adjust, update+adjust, multi-location, existing-active-level, activate-inactive, enable-tracking, ownership failure, zero/negative/malformed/duplicate, Shopify userErrors, failure-after-create-no-dup-product, **re-submit (new sync item, same `frontend_client_id`) does not re-apply an `applied` ledger row**, **lost-response reconcile via baseline re-query**, partial-failure, multi-shop isolation.
7. **Phase 6 — Scopes.** Config/env/registry scope additions; execution-time `missing_inventory_scope` gate; tests for missing scope + product-only-still-works.
8. **Phase 7 — Locations query + route + serializer** and handoff doc.
9. **Phase 8 — Result serialization** inventory summary in the synced event; test.
10. **Phase 9 — Frontend.** Locations query, inventory field, form wiring, submit splitting, zod schemas; component + submit-resolver tests.

## Risks and mitigations

- Risk: non-idempotent increment double-applies on re-submit (the real retry path).
  Mitigation: durable `shopify_inventory_adjustments` ledger, DB-unique on `(shop_integration_id, frontend_client_id, shopify_location_id)`, claimed before each adjust; baseline re-query for the lost-response case; identity lookup independently prevents duplicate product create.
- Risk: cross-shop location leakage.
  Mitigation: every adjustment is shop-tagged and routed to its own per-`(item, shop)` sync item; request-level "shop targeted" check + execution-time live ownership validation; per-row `shopIntegrationId` keying on the frontend.
- Risk: activation double-adds when combined with quantity.
  Mitigation: always activate at 0, adjust separately.
- Risk: API-version mismatch on mutation/scopes.
  Mitigation: Phase 0 gate before any code.
- Risk: existing installs lack new scopes.
  Mitigation: explicit `missing_inventory_scope` failure + reauthorize surfacing; product-only sync unaffected.
- Risk: shared normalized-payload aliasing when attaching per-shop inventory slices.
  Mitigation: deep-copy the base payload per target shop before attaching that shop's adjustment slice.

## Validation plan

- `pytest app/tests/unit/services/commands/shopify -k "product"` and the new inventory tests: green.
- `pytest app/tests/integration/services/commands/shopify/test_process_shopify_products_integration.py`: create+adjust and update+adjust paths pass; no-inventory case unchanged.
- Migration up/down applies cleanly on a scratch DB.
- Frontend: `pnpm --filter @beyo/shopify test` for the inventory field + submit resolver.
- Manual/verify: a real (or mocked) shop — 3 on hand + add 2 ⇒ 5; retry the failed-metafields path ⇒ still 5 (no double add).

## Review log

- `2026-07-15` `codex`: Implemented the request, persistence, worker, locations route, frontend, migration, tests, and handoff changes. Focused and integration validation passed; unrelated dimension-migration failures and existing Alembic drift are recorded in the implementation summary.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
