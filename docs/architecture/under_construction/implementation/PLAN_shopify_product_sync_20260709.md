# PLAN_shopify_product_sync_20260709

## Metadata

- Plan ID: `PLAN_shopify_product_sync_20260709`
- Status: `under_construction`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-09T00:00:00Z`
- Last updated at (UTC): `2026-07-09T00:00:00Z`
- Related issue/ticket: `Shopify create-or-update product capability`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_shopify_product_sync_20260709.md`

## Goal and intent

- Goal: Add a batched, workspace-scoped, background-processed "create or update Shopify products" capability that reuses the existing Shopify OAuth/GraphQL/worker/event infrastructure (`57_shopify_integration.md`) end to end — router -> command -> DB tracking rows -> `queue:shopify` worker task -> GraphQL lookup/create/update -> per-item status + one socket event.
- Business/user intent: Let a workspace push its catalog into one or more connected Shopify shops from ManagerBeyo, with visible per-item/per-shop progress, without the request blocking on Shopify's API and without ever risking a duplicate product for an item that already exists in the target shop.
- Non-goals:
  - Product image/media upload (explicitly deferred to a follow-up plan).
  - Multi-variant products or product options.
  - Shopify's structured `TaxonomyCategory` taxonomy.
  - Deleting/archiving Shopify products.
  - Any change to OAuth, webhook intake/HMAC, or webhook subscription sync.
  - Syncing from an internal ManagerBeyo catalog entity (Item/Upholstery) — this capability operates purely on the request payload; see "Resolved decisions" item 1.

## Scope

- In scope:
  - One new table (`shopify_product_sync_items`) tracking per-(item, shop) sync status.
  - One new `TaskType` (`SHOPIFY_PROCESS_PRODUCTS`) and payload dataclass, routed on the existing `queue:shopify` queue.
  - One new worker handler registered in `workers/shopify_worker.py`'s `HANDLER_MAP`.
  - New GraphQL infra functions for product lookup-by-identity, create, update, and metafield sync — reusing `execute_shopify_graphql`/`raise_for_graphql_user_errors` unmodified.
  - A payload normalizer/builder layer translating the frontend's raw item payload into a Shopify-ready create/update payload, with a defaults layer (status defaults to `DRAFT`).
  - One new admin route: `POST /api/v1/integrations/shopify/products/process`, added to the existing `routers/api_v1/shopify.py` router (no new router file).
  - One new `ShopifyIntegrationEventTypeEnum` value (`PRODUCT_SYNC`), written once per submitted batch.
  - One new socket event, emitted once per completed batch to the workspace room, summarizing succeeded/failed (item, shop) operations.
  - Unit + integration tests mirroring the existing `tests/{unit,integration}/.../shopify/` tree.
- Out of scope:
  - Product image/media mutations (`productCreateMedia`/`stagedUploadsCreate`) — not called anywhere in this plan.
  - Multi-variant/product-options support.
  - `TaxonomyCategory`-based category mapping — `product_category` maps only to the legacy `productType` string.
  - Any internal Item/Upholstery catalog linkage.
  - Production deployment/systemd wiring (the worker process already exists and already runs this queue; no new process to deploy).
- Assumptions:
  - The current single Alembic head is `d4f8a1b2c3e4` (confirmed via `python -m alembic heads` on `2026-07-09`, from `app/`). **Re-run `alembic heads` immediately before writing the first migration** — this branch has many uncommitted changes and the head may have moved.
  - `settings.shopify_api_version` is `"2026-01"` by default (`app/beyo_manager/config.py:111`). The exact GraphQL mutation field names for `productCreate`/`productUpdate`/`productVariantsBulkUpdate`/`metafieldsSet` at this API version are **not verified** in this plan — see "Clarifications required" item 1.
  - `ShopifyShopIntegration.access_token_encrypted` and workspace-scoping conventions are unchanged from `57_shopify_integration.md`.
  - The frontend's per-item `client_id` (Section 8 of the source spec) is a frontend-local identifier, not a ManagerBeyo `Item`/`Upholstery` `client_id` — this plan does not attempt to resolve it against any internal catalog table.

## Clarifications required

- [ ] `Should this capability additionally gate on the caller's current WorkingSection.allows_shopify_product_modifications flag (app/beyo_manager/models/tables/working_sections/working_section.py), in addition to require_roles([ADMIN, MANAGER])?` — This boolean column was added to `WorkingSection` in this same working tree (uncommitted, already plumbed through `create_working_section`/`edit_working_section`/serializers/queries) but is not yet consumed as an authorization check anywhere. It is plausible it was added specifically to gate this capability. The source spec for this plan never mentions working sections. **Recommendation**: do not gate on it in this phase — use role-based gating only (`require_roles([ADMIN, MANAGER])`), consistent with every other Shopify admin route, and leave the flag for the user to wire into a future phase if it was intended for a different (e.g. shop-floor worker UI) purpose. This blocks nothing structural; Codex can proceed with the recommendation, but the user should confirm before this plan moves to `approved`.
- [ ] `Exact Shopify Admin GraphQL Input field names for ProductCreateInput / ProductUpdateInput / ProductVariantsBulkInput / MetafieldsSetInput at api_version=settings.shopify_api_version.` — This plan's Phase 2 (GraphQL infra) provides a best-known-shape draft based on Shopify's documented Admin API design (see "Resolved decisions" item 7 and the mutation drafts in Implementation plan step 5), but it has not been verified against a live schema introspection call. **This blocks only Phase 2's mutation-writing step**, not the rest of the plan (DB schema, router, task wiring, lookup-by-search — which reuses the already-proven `productVariants(query: ...)` search pattern from `product_identity_client.py` — can all be implemented first). Before writing the final mutation strings, Codex must either introspect the live schema (`{ __type(name: "ProductVariantsBulkInput") { inputFields { name type { name } } } }` via `execute_shopify_graphql` against a real connected dev shop) or consult Shopify's official Admin API changelog for `2026-01`, and record the confirmed field names in this plan's Review log before implementing Phase 2.

## Acceptance criteria

1. `POST /api/v1/integrations/shopify/products/process` validates the request, resolves target shop(s), persists one `ShopifyProductSyncItem` row per (item, shop) pair with `status=PENDING`, writes one `ShopifyIntegrationEvent(event_type=PRODUCT_SYNC)`, enqueues exactly one `SHOPIFY_PROCESS_PRODUCTS` task, and returns `{"queued": true, "task_id": ..., "sync_item_client_ids": [...], "target_count": N}` — all without any synchronous Shopify GraphQL call.
2. Omitting `target_shop_integration_ids` on an item targets every `ACTIVE` shop integration in the caller's workspace; an explicit list is validated against the workspace's own shop integrations (`NotFound`/`ValidationError` on a foreign or inactive shop id — never silently dropped, never another workspace's shop).
3. The worker handler (`handle_shopify_process_products`) loads all `ShopifyProductSyncItem` rows for the task's `sync_item_client_ids`, and for each row: looks up the target shop's existing product by SKU (falling back to barcode), creates or updates accordingly, and writes the row's `status`/`shopify_product_id`/`shopify_variant_id`/`error_code`/`error_message` — one row's failure does not stop the rest of the batch or the rest of the task.
4. A single-variant product is created via `productCreate` (product-level fields) followed by `productVariantsBulkUpdate` on the auto-created default variant (SKU/barcode/price/weight); an existing product is updated via `productUpdate` + `productVariantsBulkUpdate` on the matched variant. Metafields are written via one `metafieldsSet` call per product. No `productVariantsBulkCreate` call is made (single-variant scope only).
5. Two or more Shopify products/variants matching the same exact SKU or barcode in one shop is treated as `error_code="ambiguous_product_match"` for that (item, shop) row — the system never guesses which one to update.
6. No response, `ShopifyProductSyncItem` field, or socket payload ever includes `access_token_encrypted` or any other secret value.
7. Exactly one socket event (`"shopify.products.synced"`) is emitted to the requesting workspace's room after the task completes, containing `succeeded`/`failed` lists keyed by the caller's own `frontend_client_id` + `shop_integration_id` — never a per-item-per-shop flood of individual events.
8. `TaskType.SHOPIFY_PROCESS_PRODUCTS` is routed only on `queue:shopify` (`QUEUE_MAP`), registered only in `workers/shopify_worker.py`'s `HANDLER_MAP`, and no other queue/worker is touched.
9. This plan adds no image/media mutation, no multi-variant mutation, no `TaxonomyCategory` lookup, and no OAuth/webhook-intake/webhook-subscription-sync code changes.

## Resolved decisions

These design questions are resolved for this plan by direct inspection of the actual codebase and by extrapolation from its established precedents, not by generic contract examples.

1. **No internal Item/Upholstery catalog linkage.** This capability operates purely on the fields present in the request payload; the caller's per-item `client_id` is treated as an opaque frontend-local identifier, never resolved against `Item`/`Upholstery`/any other ManagerBeyo catalog table. (Confirmed by direct inspection: `models/tables/upholstery/upholstery.py` has no `sku`/`shopify_product_id` field, and the source spec's own request contract never references an internal entity id.)
2. **Role gating — `ADMIN` + `MANAGER`, not `SELLER`.** Unlike the read-only `lookup_shopify_customers_by_product_identity` route (which deliberately added `SELLER` as a first-time carve-out for a read-only lookup), this capability writes to Shopify and creates durable DB rows — kept at the same gating level as every other state-mutating Shopify admin route pair (`ADMIN`+`MANAGER` for actions that don't disable/remove state, `ADMIN`-only reserved for destructive ones like disconnect). `SELLER` can be added later behind an explicit permission if shop-floor product entry becomes a requirement.
3. **Omitted `target_shop_integration_ids` -> every `ACTIVE` shop integration in the workspace.** Matches `enqueue_shopify_webhook_sync_for_workspace`'s already-established "fan out to every shop in the workspace" precedent (`57_shopify_integration.md`'s "Supporting multiple shops per workspace" section) rather than rejecting an otherwise well-formed request that simply didn't specify shops.
4. **`product_category` maps only to Shopify's legacy `productType` string field**, never the structured `TaxonomyCategory` taxonomy. The taxonomy requires a separate category-tree lookup dependency this plan does not introduce; `productType` is a plain string on `ProductInput` with no such dependency. A future phase can add taxonomy support without changing this plan's schema (the normalized payload already carries a plain string).
5. **Two or more exact SKU/barcode matches across distinct parent products is an explicit failure, never a silent pick.** `select_exact_variant_match` (Phase 3) raises `ShopifyProductLookupAmbiguousError` (`error_code="ambiguous_product_match"`) for that row rather than guessing — writing to the wrong product is a worse outcome than a visible per-row failure the frontend can surface to the user.
6. **Metafields use one fixed `namespace="custom"` and coerce every value to `type: "single_line_text_field"` in phase 1.** The source spec confirms the backend does not need to validate metafield business meaning and defers the namespace decision to this plan; a single fixed namespace with string-typed values is the smallest safe default. Richer per-key typing/namespacing is a documented future enhancement, not attempted here.
7. **The GraphQL mutation shapes in Phase 2 are a best-known draft, not verified ground truth.** They follow Shopify's documented Admin API design (`productCreate`/`productUpdate` for product-level fields, `productVariantsBulkUpdate` for the single default variant, `metafieldsSet` for metafields — all already-established mutation names in Shopify's Admin API), reusing this codebase's proven `productVariants(query: ...)` search shape unmodified for lookup. Exact input-object field names must still be confirmed against the live schema for `settings.shopify_api_version` before implementation — see "Clarifications required" item 2.

## Contracts and skills

### Contracts loaded

- `architecture/57_shopify_integration.md`: The authoritative extension guide for this exact integration — "Adding a new Shopify task type," "Adding a new admin route," "Adding a new integration event type," and the "Never call Shopify's API inline from an HTTP request handler" rule this whole plan is built around.
- `architecture/04_context.md`: `ServiceContext` identity/session boundaries for the new command.
- `architecture/05_errors.md`: `ValidationError`, `NotFound`, `ExternalServiceError`/`ShopifyGraphQLError` hierarchy reused unmodified for the new command and infra functions.
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: Command/request-parser structure for `process_shopify_products`; `maybe_begin` is **not** used here (this command is not embedded by a parent command — it uses the canonical `ctx.session.begin()` per the local contract's own carve-out).
- `architecture/07_queries.md` + `architecture/07_queries_local.md`: Not directly needed (this plan adds no new list/detail query), loaded for consistency since the router file already follows it for sibling routes.
- `architecture/09_routers.md`: New route structure, added to the existing `shopify.py` router object.
- `architecture/21_naming_conventions.md`: File/function naming for the new modules.
- `architecture/40_identity.md`: `IdentityMixin`/`CLIENT_ID_PREFIX` for the new table (`shpsi`).
- `architecture/41_user.md`, `architecture/42_event.md`, `architecture/48_presence.md`: Core contracts per the goal-mapping guide; no direct new usage beyond existing conventions already followed by sibling Shopify code.
- `architecture/03_models.md`: New table column/index/enum conventions for `ShopifyProductSyncItem`.
- `architecture/16_background_jobs.md`: Task type / payload dataclass / worker registration contract — "Task payloads carry IDs only" is the reason `ShopifyProcessProductsPayload` holds only `sync_item_client_ids`, not denormalized item data.
- `architecture/30_migrations.md`: Additive-migration idiom, exact `ALTER TYPE ... ADD VALUE IF NOT EXISTS` pattern for the two new enum values.
- `architecture/15_testing.md`: Test tier placement, mirrored onto the existing `tests/{unit,integration}/.../shopify/` folder structure.

### Local extensions loaded

- `architecture/06_commands_local.md`: `maybe_begin` transaction-propagation rule reviewed and explicitly not applicable here (see above).
- `architecture/07_queries_local.md`: Offset-pagination override reviewed; not applicable (no list query added).

### Deviation from `13_sockets.md`

`architecture/13_sockets.md` documents a native-FastAPI-WebSocket + Redis-pub/sub architecture. **The actual running implementation uses `python-socketio`** (`sockets/manager.py`'s `get_sio()`/`sio.enter_room()`/`sio.emit()`, `sockets/register.py`, `sockets/worker_emitter.py`'s `socketio.AsyncRedisManager`) — confirmed by direct inspection on `2026-07-09`. There is no `13_sockets_local.md` companion documenting this drift. This plan follows the **real, running implementation** (`sockets/worker_emitter.py`, `sockets/rooms.py`, the `handle_sync_email_threads_targeted.py` precedent below), not `13_sockets.md`'s code samples, because writing against the documented-but-nonexistent native-WebSocket API would not actually work. Flagging this drift explicitly rather than silently picking one.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** -> read the contract instead (`06_commands.md`, `09_routers.md`, `16_background_jobs.md`, etc.)
- **What exists** -> reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand `session.add`/`flush`/error-raising shape -> `06_commands.md`
- Reading another router to understand handler wiring -> `09_routers.md`

Permitted for this plan (already read once during drafting; re-read only to confirm nothing changed before implementation):
- `app/beyo_manager/routers/api_v1/shopify.py`, `routers/api_v1/__init__.py` — router this plan extends, exact mount/prefix.
- `app/beyo_manager/workers/shopify_worker.py`, `domain/execution/enums.py`, `domain/execution/payloads/shopify.py`, `services/infra/execution/task_router.py`'s `QUEUE_MAP`, `services/infra/execution/task_factory.py` — exact existing task-type/payload/queue wiring this plan extends.
- `app/beyo_manager/services/infra/shopify/graphql_client.py` (`execute_shopify_graphql`, `raise_for_graphql_user_errors`), `services/infra/shopify/product_identity_client.py` (the proven `productVariants(query: "sku:\"...\"")`/`"barcode:\"...\""` search pattern, `_quote_shopify_search_term`, `_clean_str`) — the exact lookup-query shape this plan's new lookup client copies.
- `app/beyo_manager/domain/shopify/customer_lookup.py` — the exact-match/identity-precedence pattern (SKU preferred, barcode fallback) this plan's product identity matching mirrors.
- `app/beyo_manager/services/queries/shopify/lookup_shopify_customers_by_product_identity.py` — the exact per-shop try/except/partial-failure-aggregation pattern this plan's per-item-per-shop processing mirrors.
- `app/beyo_manager/services/commands/shopify/enqueue_shopify_webhook_sync_for_shop.py`, `services/commands/shopify/_events.py` (`create_shopify_integration_event`) — exact `create_instant_task(..., event_client_id=...)` + event-then-task ordering this plan's command mirrors.
- `app/beyo_manager/services/tasks/emails/handle_sync_email_threads_targeted.py`, `domain/execution/payloads/sync_email_threads_targeted.py` — the exact "one task, payload carries a list of IDs, handler loops internally, emits one summary socket event with per-item results" pattern this plan's task/payload/handler directly copies (this is the closest existing precedent for a batched, partial-failure-tolerant worker task in this codebase).
- `app/beyo_manager/sockets/worker_emitter.py`, `sockets/rooms.py`, `sockets/manager.py`, `sockets/register.py` — the real (socketio-based) push mechanism this plan's socket emission uses.
- `app/beyo_manager/models/tables/shopify/shopify_integration_event.py`, `shopify_shop_integration.py`, `models/base/identity.py` — exact column/prefix conventions for the new table.
- `app/beyo_manager/domain/shopify/enums.py`, `domain/shopify/scopes.py` (`has_all_required_scopes`) — exact enum members and scope-check helper this plan's new enums/authorization extend.
- `app/beyo_manager/config.py` — `shopify_api_version`, `shopify_app_scopes` fields.
- `app/migrations/versions/c3f7a9d2e4b1_add_shopify_execution_task_types.py`, `ab12cd34ef56_add_disconnect_to_shopify_integration_event_type.py`, `677ed7131bb2_create_shopify_integration_foundation.py` — exact migration idiom (enum `ADD VALUE IF NOT EXISTS`, `CREATE TABLE` with `postgresql.ENUM(..., create_type=False)` for enum columns already created by a prior migration) this plan's three new migrations copy.
- `app/tests/integration/services/queries/shopify/test_lookup_shopify_customers_by_product_identity_query.py` — real async-pytest fixture/style (`db_session`, `@pytest.mark.integration`) this plan's new tests follow (not `15_testing.md`'s generic Flask-style sample).

### Skill selection

- Primary skill: `none`
- Router trigger terms: `none`
- Excluded alternatives: none — this plan was drafted directly from a user-authored capability spec, no `intention_planning` skill invocation needed.

### Contracts intentionally not selected for this plan

- `12_infra_redis.md`, `51_worker_runtime.md`, `49_observability_runtime.md`, `54_ci_cd_runtime.md`: Not selected — this plan calls `create_instant_task` with a new task type on the already-existing `queue:shopify`/`workers/shopify_worker.py`; it defines no new queue, no new worker process, no new Redis usage pattern.
- `13_sockets.md`, `56_realtime_layer.md`: Read for context (see "Deviation" note above) but not followed as written — the real `python-socketio` implementation is followed instead.
- `19_integrations.md`: No new external adapter type — this plan's infra functions are plain additions to the existing `services/infra/shopify/` GraphQL-adapter pattern.
- `24_multi_tenancy.md`, `25_soft_delete.md`, `28_roles_permissions.md`, `18_security.md`: Implicitly satisfied by following `57_shopify_integration.md`'s established workspace-scoping/role-gating/no-secret-serialization precedent exactly; not separately elaborated.
- `46_serialization.md`, `46_serialization_local.md`: This plan's router response is a small ack shape (`{"queued", "task_id", "sync_item_client_ids", "target_count"}`), not a full result-dataclass serialization — no new `results.py`/`serializers.py` entries are required beyond what's noted in Implementation plan step 8.
- `33_deployment.md`, `31_health_observability.md`: No new process to deploy; the existing `queue:shopify` worker already runs and already needs no new systemd unit.
- `34_file_storage.md`: Image/media handling is out of scope for this plan.

## Implementation plan

### File-to-concept mapping

The source spec names conceptual services (`find_shopify_products`, `create_shopify_products`, `update_shopify_products`, `create_or_update_shopify_products`, `process_items_in_shopify`). Mapped onto this codebase's actual layering:

| Spec concept | Real file | Layer |
|---|---|---|
| `process_items_in_shopify` (router-triggered: validate, normalize, persist, enqueue) | `services/commands/shopify/process_shopify_products.py` | command |
| Payload builders/normalizers, defaults | `domain/shopify/product_sync_payloads.py` | domain |
| Identity matching / duplicate-match policy | `domain/shopify/product_sync_identity.py` | domain |
| `find_shopify_products` (GraphQL search) | `services/infra/shopify/product_sync_client.py::find_product_variant_by_identity` | infra |
| `create_shopify_products` / `update_shopify_products` (GraphQL mutations) | `services/infra/shopify/product_sync_client.py::create_shopify_product`, `update_shopify_product`, `set_shopify_product_metafields` | infra |
| `create_or_update_shopify_products` (per-item orchestration, worker-triggered) | `services/tasks/shopify/_product_sync_orchestrator.py::sync_one_product_sync_item` | task-private helper |
| Worker task handler | `services/tasks/shopify/handle_shopify_process_products.py` | task |
| DB/event tracking for frontend status | `models/tables/shopify/shopify_product_sync_item.py` | model |
| Socket/event emission | `sockets/worker_emitter.py::emit_to_workspace_room` (new), called from the task handler | sockets |

### Phase 1 — Schema, enums, task wiring

1. Add `ShopifyProductSyncOperationEnum(StrEnum)` (`CREATE`, `UPDATE`) and `ShopifyProductSyncItemStatusEnum(StrEnum)` (`PENDING`, `PROCESSING`, `SUCCEEDED`, `FAILED`) to `domain/shopify/enums.py`, following the existing `StrEnum` style in that file. (No `PARTIALLY_SUCCEEDED` item-level status — partial success is a *batch*-level concept, expressed by the mix of statuses across the batch's rows, not a single row's own status; a single (item, shop) row is always fully succeeded or fully failed.)

2. Add `PRODUCT_SYNC = "product_sync"` to `ShopifyIntegrationEventTypeEnum` in `domain/shopify/enums.py`.

3. Add `SHOPIFY_PROCESS_PRODUCTS = "shopify_process_products"` to `TaskType` in `domain/execution/enums.py`, `SHOPIFY_` prefix convention, grouped with the other four Shopify task types.

4. Add `TaskType.SHOPIFY_PROCESS_PRODUCTS: "queue:shopify"` to `QUEUE_MAP` in `services/infra/execution/task_router.py` — no other queue.

5. Add `ShopifyProcessProductsPayload` to `domain/execution/payloads/shopify.py`:
   ```python
   @dataclass(frozen=True)
   class ShopifyProcessProductsPayload:
       workspace_id: str
       requested_by_user_id: str
       sync_item_client_ids: list[str]
   ```
   IDs only, per `16_background_jobs.md` — the handler re-loads each `ShopifyProductSyncItem` row from Postgres by `client_id`; no product field is denormalized into the payload.

6. Create `models/tables/shopify/shopify_product_sync_item.py`:
   ```python
   class ShopifyProductSyncItem(IdentityMixin, Base):
       CLIENT_ID_PREFIX = "shpsi"
       __tablename__ = "shopify_product_sync_items"
       __table_args__ = (
           Index("ix_shopify_product_sync_items_workspace_status", "workspace_id", "status"),
           Index("ix_shopify_product_sync_items_shop_integration_status", "shop_integration_id", "status"),
       )

       workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True)
       shop_integration_id: Mapped[str] = mapped_column(String(64), ForeignKey("shopify_shop_integrations.client_id", ondelete="RESTRICT"), nullable=False, index=True)
       frontend_client_id: Mapped[str] = mapped_column(String(255), nullable=False)  # the caller's own per-item id, opaque to us
       requested_operation: Mapped[ShopifyProductSyncOperationEnum | None] = mapped_column(SAEnum(...), nullable=True)  # None until the worker decides create vs update
       status: Mapped[ShopifyProductSyncItemStatusEnum] = mapped_column(SAEnum(...), nullable=False, default=PENDING, index=True)
       normalized_payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)  # builder/normalizer output — the single source of truth the worker reads
       shopify_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
       shopify_variant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
       error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
       error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
       created_by_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True)
       created_at / updated_at: standard UTC pattern per 03_models.md
   ```
   Register the import in `models/__init__.py` next to the other `shopify` table imports.

7. Three additive Alembic migrations, chained off the confirmed current head `d4f8a1b2c3e4` (**re-verify with `alembic heads` before writing**):
   - `create_shopify_product_sync_items_table` (`down_revision="d4f8a1b2c3e4"`) — `op.create_table(...)` for the new table plus its two new native enum types (`create_type=True` the first time each is referenced), copying `677ed7131bb2`'s `CREATE TABLE` shape.
   - `add_shopify_process_products_task_type` (chained after the above) — `op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_process_products'")`, copying `c3f7a9d2e4b1` exactly.
   - `add_product_sync_to_shopify_integration_event_type` (chained after the above) — `op.execute("ALTER TYPE shopify_integration_event_type_enum ADD VALUE IF NOT EXISTS 'product_sync'")`, copying `ab12cd34ef56` exactly.

### Phase 2 — GraphQL infra (product lookup, create, update, metafields)

**Blocked on "Clarifications required" item 2 for the exact mutation field names — do the schema verification first.**

8. Create `services/infra/shopify/product_sync_client.py`. Lookup query copies `product_identity_client.py`'s proven shape exactly:
   ```graphql
   query FindProductVariantsByIdentity($searchQuery: String!, $first: Int!) {
     productVariants(first: $first, query: $searchQuery) {
       edges { node { id sku barcode product { id status } } }
     }
   }
   ```
   `searchQuery` built the same way as `product_identity_client.py`'s `_quote_shopify_search_term` (`sku:"value"` / `barcode:"value"`) — duplicate this small private helper locally rather than importing another file's `_`-prefixed function, matching this codebase's existing per-file-helper convention.

   Draft mutation shapes (unverified — confirm against live schema first):
   ```graphql
   mutation CreateProduct($input: ProductInput!) {
     productCreate(input: $input) {
       product { id status variants(first: 1) { edges { node { id } } } }
       userErrors { field message }
     }
   }

   mutation UpdateProduct($input: ProductInput!) {
     productUpdate(input: $input) {
       product { id status }
       userErrors { field message }
     }
   }

   mutation BulkUpdateVariant($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
     productVariantsBulkUpdate(productId: $productId, variants: $variants) {
       productVariants { id sku barcode }
       userErrors { field message }
     }
   }

   mutation SetMetafields($metafields: [MetafieldsSetInput!]!) {
     metafieldsSet(metafields: $metafields) {
       metafields { id key namespace }
       userErrors { field message }
     }
   }
   ```
   Every mutation call is followed by `raise_for_graphql_user_errors(user_errors=..., operation_name=..., shop_domain=...)` — reuse unmodified, exactly as every existing Shopify infra function does.

9. `find_product_variant_by_identity(*, shop_domain, access_token_encrypted, sku, barcode) -> list[dict]` — runs the SKU search first (if `sku` given), then the barcode search (if `barcode` given and SKU search returned no exact match), mirroring `_lookup_customer_matches_for_shop`'s SKU-preferred/barcode-fallback precedence from `services/queries/shopify/lookup_shopify_customers_by_product_identity.py`.

10. `create_shopify_product(*, shop_domain, access_token_encrypted, normalized_payload) -> dict` — calls `productCreate` with product-level fields (`title`, `descriptionHtml`, `status` defaulting to `DRAFT`, `tags`, `productType`), reads the default variant id off the response, then calls `productVariantsBulkUpdate` with SKU/barcode/price/`inventoryItem.measurement.weight`. Returns `{"shopify_product_id", "shopify_variant_id"}`.

11. `update_shopify_product(*, shop_domain, access_token_encrypted, shopify_product_id, shopify_variant_id, normalized_payload) -> dict` — calls `productUpdate` for product-level fields (only if any are present in the normalized payload), then `productVariantsBulkUpdate` on the already-known `shopify_variant_id` for variant-level fields.

12. `set_shopify_product_metafields(*, shop_domain, access_token_encrypted, shopify_product_id, metafields) -> None` — one `metafieldsSet` call per product, `namespace="custom"` fixed for phase 1 (per "Resolved decisions" item 6), all values coerced to `type: "single_line_text_field"` strings.

### Phase 3 — Domain layer (identity matching, payload normalization)

13. Create `domain/shopify/product_sync_identity.py`:
    - `IdentityType = Literal["sku", "barcode"]` (reuse the existing type alias shape from `customer_lookup.py`).
    - `select_exact_variant_match(variant_nodes: list[dict], *, identity_type, identity_value) -> ProductSyncMatchResult` — filters `product_identity_client.py`-shaped nodes to exact matches (same `_clean_str` comparison as `customer_lookup.py`), then:
      - 0 exact matches -> `found=False`.
      - 1 exact match -> `found=True`, extract `shopify_product_id`/`shopify_variant_id`.
      - >=2 exact matches across **more than one distinct parent product** -> raise a new `ShopifyProductLookupAmbiguousError(DomainError)` (`error_code="ambiguous_product_match"`) — never silently pick one (see "Resolved decisions" item 5).
      - >=2 exact matches on the **same** parent product (e.g. Shopify's search index returning duplicate edges) -> treat as one match, no error.

14. Add `ShopifyProductLookupAmbiguousError` to `errors/external_service.py` (or a new small `errors/` addition) as a `DomainError` subclass, `http_status=409`.

15. Create `domain/shopify/product_sync_payloads.py`:
    - `build_normalized_product_sync_payload(item: ProcessShopifyProductItemRequest) -> dict` — pure function, no I/O. Maps: `title`, `description` -> `descriptionHtml`, `status` (default `"draft"` if omitted — the defaults layer described in the source spec, kept as one small dict-merge function so it's trivially extendable later), `tags`, `product_category` -> `productType`, `price` (kept as the Shopify decimal-string format), `weight`/`weight_unit` -> `{"value": ..., "unit": <mapped WeightUnit>}`, `sku`, identity value (`item_article_number`/`article_number` -> `barcode`), `metafields` dict -> a list of `{"key", "value", "type": "single_line_text_field"}` (namespace applied at the infra layer, not here).
    - Weight unit mapping table: `{"kg": "KILOGRAMS", "g": "GRAMS", "lb": "POUNDS", "oz": "OUNCES"}` — unrecognized unit raises `ValidationError` in the request parser (Phase 4), not here (this function only runs on already-validated input).

### Phase 4 — Command (router-triggered: validate, resolve shops, normalize, persist, enqueue)

16. Create `services/commands/shopify/requests/process_shopify_products_request.py`:
    - `ProcessShopifyProductItemRequest(BaseModel)`: `client_id: str` (frontend's own id, required, non-blank), `target_shop_integration_ids: list[str] | None = None`, `title: str`, `description: str | None`, `status: str | None`, `tags: list[str] = []`, `product_category: str | None`, `price: str | None`, `weight: WeightRequest | None` (nested model: `value: float`, `unit: str`), `sku: str | None`, `item_article_number: str | None`, `metafields: dict[str, str] = {}`.
      - `@model_validator`: at least one of `sku`/`item_article_number` required (mirrors `ShopifyProductIdentityLookupRequest`'s `_require_identity` pattern in `lookup_shopify_customers_by_product_identity.py`).
      - `@field_validator` on `weight.unit`: must be one of the four supported units.
    - `ProcessShopifyProductsRequest(BaseModel)`: `items: list[ProcessShopifyProductItemRequest]` (min length 1).
    - `parse_process_shopify_products_request(data: dict) -> ProcessShopifyProductsRequest` — standard `model_validate` + `ValidationError` conversion, per `06_commands.md`.

17. Create `services/commands/shopify/_product_sync_normalizer.py` (private helper, per `06_commands.md`'s "commands must not call other commands" — this is a plain helper, not a command): `resolve_and_normalize_sync_targets(session, *, workspace_id, request) -> list[tuple[ShopifyShopIntegration, ProcessShopifyProductItemRequest, dict]]`:
    - Loads the workspace's `ACTIVE` shop integrations (same query shape as `lookup_shopify_customers_by_product_identity`'s integration-loading query).
    - For each item: resolves its target shop set — omitted `target_shop_integration_ids` -> every `ACTIVE` shop in the workspace (see "Resolved decisions" item 3); an explicit id not present in the workspace's active shop set -> raise `NotFound` for the whole request (fail fast at validation time, not silently dropped — this is a request-shape error, not a per-item runtime failure).
    - Calls `build_normalized_product_sync_payload` (Phase 3) once per item, reused across that item's shop targets.
    - Returns the flat list of (shop, item, normalized_payload) tuples the command will persist as rows.

18. Create `services/commands/shopify/process_shopify_products.py`:
    ```python
    async def process_shopify_products(ctx: ServiceContext) -> dict:
        request = parse_process_shopify_products_request(ctx.incoming_data)

        async with ctx.session.begin():
            targets = await resolve_and_normalize_sync_targets(ctx.session, workspace_id=ctx.workspace_id, request=request)

            sync_items = [
                ShopifyProductSyncItem(
                    workspace_id=ctx.workspace_id,
                    shop_integration_id=shop.client_id,
                    frontend_client_id=item.client_id,
                    status=ShopifyProductSyncItemStatusEnum.PENDING,
                    normalized_payload_json=normalized_payload,
                    created_by_id=ctx.user_id,
                )
                for shop, item, normalized_payload in targets
            ]
            ctx.session.add_all(sync_items)
            await ctx.session.flush()  # assigns client_id for every row

            event = await create_shopify_integration_event(
                ctx.session,
                workspace_id=ctx.workspace_id,
                shop_integration_id=sync_items[0].shop_integration_id,  # see note below
                event_type=ShopifyIntegrationEventTypeEnum.PRODUCT_SYNC,
                severity=ShopifyIntegrationEventSeverityEnum.INFO,
                message=f"Product sync batch enqueued for {len(sync_items)} (item, shop) operations.",
                metadata_json={"item_count": len(request.items), "target_count": len(sync_items)},
                created_by_id=ctx.user_id,
            )

            task = await create_instant_task(
                session=ctx.session,
                task_type=TaskType.SHOPIFY_PROCESS_PRODUCTS,
                payload=asdict(ShopifyProcessProductsPayload(
                    workspace_id=ctx.workspace_id,
                    requested_by_user_id=ctx.user_id,
                    sync_item_client_ids=[row.client_id for row in sync_items],
                )),
                event_client_id=event.client_id,
            )

        return {
            "queued": True,
            "task_id": task.client_id,
            "sync_item_client_ids": [row.client_id for row in sync_items],
            "target_count": len(sync_items),
        }
    ```
    **Note on `event.shop_integration_id`**: `ShopifyIntegrationEvent.shop_integration_id` is `nullable=False` (one event = one shop) but this batch can span multiple shops. Resolve by writing **one `PRODUCT_SYNC` event per distinct shop** in the batch (loop over the distinct shops in `targets`, one `create_shopify_integration_event` call each, all sharing the same `event_client_id`-linked task via a list — but `create_instant_task` only accepts one `event_client_id`). **Decision**: write one event per distinct shop touched by the batch (matching `enqueue_shopify_webhook_sync_for_workspace`'s "one event+task pair per shop" precedent from the archived admin-routes plan), but only pass `event_client_id=` from the **first** shop's event to `create_instant_task` (the task is one row regardless of shop count; the other per-shop events exist for each shop's own history feed but are not individually task-linked — acceptable, since `event_client_id` is a traceability convenience, not a correctness requirement, and `ShopifyProductSyncItem` rows are already the authoritative per-shop tracking mechanism).

### Phase 5 — Worker task handler and orchestration

19. Create `services/tasks/shopify/_product_sync_orchestrator.py` (private helper, worker-side): `sync_one_product_sync_item(session, *, sync_item: ShopifyProductSyncItem, shop: ShopifyShopIntegration) -> None`:
    - Sets `sync_item.status = PROCESSING`, flush.
    - Extracts `sku`/`barcode` identity from `sync_item.normalized_payload_json`.
    - Calls `find_product_variant_by_identity` (Phase 2), then `select_exact_variant_match` (Phase 3).
    - On `found=True` -> `requested_operation = UPDATE`, calls `update_shopify_product`.
    - On `found=False` -> `requested_operation = CREATE`, calls `create_shopify_product`.
    - Calls `set_shopify_product_metafields` if the normalized payload has any metafields.
    - On success: `status = SUCCEEDED`, sets `shopify_product_id`/`shopify_variant_id`.
    - On `ShopifyGraphQLError`/`ShopifyProductLookupAmbiguousError`: `status = FAILED`, `error_code`/`error_message` set from the exception; **does not raise** — the caller (the handler's loop) must continue to the next row. This function is a per-row try/except boundary, not a per-batch one.

20. Create `services/tasks/shopify/handle_shopify_process_products.py`:
    ```python
    async def handle_shopify_process_products(raw: dict, task_client_id: str) -> None:
        payload = ShopifyProcessProductsPayload(**raw)
        succeeded, failed = [], []

        async with task_db_session() as session:
            rows = (await session.execute(
                select(ShopifyProductSyncItem).where(
                    ShopifyProductSyncItem.client_id.in_(payload.sync_item_client_ids),
                    ShopifyProductSyncItem.workspace_id == payload.workspace_id,
                )
            )).scalars().all()
            shops_by_id = {row.client_id: row for row in (await session.execute(
                select(ShopifyShopIntegration).where(ShopifyShopIntegration.client_id.in_({r.shop_integration_id for r in rows}))
            )).scalars().all()}

            for row in rows:
                shop = shops_by_id.get(row.shop_integration_id)
                if shop is None or not (shop.access_token_encrypted or "").strip():
                    row.status = ShopifyProductSyncItemStatusEnum.FAILED
                    row.error_code = "missing_access_token"
                    failed.append(_failure_entry(row))
                    continue
                try:
                    await sync_one_product_sync_item(session, sync_item=row, shop=shop)
                except Exception as exc:  # last-resort per-row guard — orchestrator already catches Shopify errors
                    row.status = ShopifyProductSyncItemStatusEnum.FAILED
                    row.error_code = "unexpected_error"
                    row.error_message = str(exc)[:1024]
                (succeeded if row.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED else failed).append(
                    _success_entry(row) if row.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED else _failure_entry(row)
                )
            await session.commit()

        await emit_to_workspace_room(
            workspace_id=payload.workspace_id,
            event="shopify.products.synced",
            payload={"task_id": task_client_id, "succeeded": succeeded, "failed": failed},
        )
    ```
    This handler never raises — an unrecoverable per-row failure is recorded on that row, not propagated to the worker's retry machinery (a retry would re-process already-succeeded rows in the same batch; row-level idempotency across a whole-task retry is out of scope for phase 1, matching the source spec's "avoid failing the whole batch" requirement over exact-once retry semantics). Follows `handle_shopify_sync_webhooks_for_shop.py`'s `task_db_session()`-per-handler-invocation shape, and `handle_sync_email_threads_targeted.py`'s "aggregate succeeded/failed lists, emit one summary event at the end" shape.

21. Register in `workers/shopify_worker.py`'s `HANDLER_MAP`: `TaskType.SHOPIFY_PROCESS_PRODUCTS: handle_shopify_process_products`.

22. Add `HANDLER_TIMEOUT_SECONDS["shopify_process_products"] = 900` (15 minutes) in `services/infra/execution/worker_base.py` — a batch of N items each requiring 2-4 GraphQL calls will exceed the 300s default for even moderately sized batches; the actual number should be set based on a realistic max batch size decided during implementation (this plan does not specify a hard max-items-per-request cap — recommend adding one, e.g. 200, as a `ValidationError` in the request parser, Phase 4 step 16, to keep this timeout bounded and predictable; **Codex should pick this number and document it in the Review log**).

### Phase 6 — Socket emission

23. Add `emit_to_workspace_room` to `sockets/worker_emitter.py`, mirroring `emit_to_user_room` exactly:
    ```python
    async def emit_to_workspace_room(*, workspace_id: str, event: str, payload: dict) -> None:
        await _get_worker_socket_manager().emit(event, payload, room=workspace_room(workspace_id))
    ```
    (`workspace_room` already imported from `sockets/rooms.py` in that file's sibling pattern.)

### Phase 7 — Router

24. Add to `routers/api_v1/shopify.py`:
    ```python
    class ShopifyProductSyncWeightBody(BaseModel):
        value: float
        unit: str

    class ShopifyProductSyncItemBody(BaseModel):
        client_id: str
        target_shop_integration_ids: list[str] | None = None
        title: str
        description: str | None = None
        status: str | None = None
        tags: list[str] = []
        product_category: str | None = None
        price: str | None = None
        weight: ShopifyProductSyncWeightBody | None = None
        sku: str | None = None
        item_article_number: str | None = None
        metafields: dict[str, str] = {}

    class ShopifyProcessProductsBody(BaseModel):
        items: list[ShopifyProductSyncItemBody]

    @router.post("/products/process")
    async def process_shopify_products_route(
        body: ShopifyProcessProductsBody,
        claims: dict = Depends(require_roles([ADMIN, MANAGER])),
        session: AsyncSession = Depends(get_db),
    ):
        outcome = await run_service(
            process_shopify_products,
            ServiceContext(identity=claims, incoming_data=body.model_dump(), session=session),
        )
        if not outcome.success:
            return build_err(outcome.error)
        return build_ok(outcome.data)
    ```
    Static path `/products/process` — no wildcard conflict with any existing `/shops/{shop_integration_id}` route (per `09_routers.md`'s declaration-order rule, this is safe regardless of position since it doesn't share a path segment, but add it near the other `POST` routes for readability).

### Phase 8 — Documentation and tests

25. Update `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` with the new route's request/response contract and the new `shopify.products.synced` socket event shape — required per `57_shopify_integration.md`'s explicit "keep this doc from drifting" rule.

26. Tests (mirroring the existing `tests/{unit,integration}/.../shopify/` tree exactly):
    - `tests/unit/domain/shopify/test_product_sync_identity.py` — 0/1/ambiguous exact-match cases.
    - `tests/unit/domain/shopify/test_product_sync_payloads.py` — normalizer defaults (status->draft), identity mapping (`item_article_number`->`barcode`), weight-unit mapping.
    - `tests/unit/services/infra/shopify/test_product_sync_client.py` — mock `execute_shopify_graphql`, assert query/variables shape per function.
    - `tests/unit/services/commands/shopify/test_process_shopify_products.py` — request validation (identity required, weight unit validation), monkeypatched session.
    - `tests/integration/services/commands/shopify/test_process_shopify_products_integration.py` — DB-backed: omitted `target_shop_integration_ids` fans out to every active shop; explicit foreign shop id -> `NotFound`; persists one row per (item, shop); enqueues exactly one `SHOPIFY_PROCESS_PRODUCTS` task; writes at least one `PRODUCT_SYNC` event.
    - `tests/unit/services/tasks/shopify/test_handle_shopify_process_products.py` — one item succeeds, one fails (mocked GraphQL client), asserts both appear in the emitted socket payload's correct list, asserts the handler does not raise.
    - `tests/integration/services/tasks/shopify/test_shopify_worker_handlers_integration.py` (extended) — DB-backed row status transitions `PENDING -> PROCESSING -> SUCCEEDED/FAILED`.
    - `tests/unit/workers/test_shopify_worker.py` (extended) — `SHOPIFY_PROCESS_PRODUCTS` present in `HANDLER_MAP`, mapped to the correct handler.
    - `tests/unit/domain/execution/test_shopify_execution_contracts.py` (extended) — new task type registered in `QUEUE_MAP` exclusively on `"queue:shopify"`; payload dataclass round-trips via `asdict`/`**raw`.
    - `tests/unit/test_shopify_router.py` (extended) — `ADMIN`/`MANAGER` accepted, `WORKER`/`SELLER` rejected (`403`) with zero command invocations, for `/products/process`.
    - `tests/integration/models/shopify/test_shopify_foundation_constraints.py` (extended, or a new sibling file) — `ShopifyProductSyncItem` FK/index/enum constraints.

## Risks and mitigations

- Risk: The draft GraphQL mutation field names (Phase 2) are wrong for `settings.shopify_api_version`, causing every create/update call to fail with `graphql_user_errors` or a schema validation error at runtime.
  Mitigation: "Clarifications required" item 2 makes schema verification an explicit, blocking first sub-step of Phase 2, not an assumption baked into the merged code.
- Risk: A batch large enough to exceed the worker's handler timeout (Phase 5 step 22) leaves the task `IN_PROGRESS` until stale-task recovery resets it to `OPEN`, causing a full re-run of already-succeeded rows (this handler is not row-level idempotent across a full task retry).
  Mitigation: Cap batch size in the request parser (Phase 4 step 16) to a number the chosen timeout comfortably covers; document the chosen cap and timeout together in the Review log. A future phase could make `sync_one_product_sync_item` skip rows already in `SUCCEEDED`/`FAILED` at the top of the loop for full retry-idempotency — deliberately deferred here since the source spec did not request exactly-once retry semantics, only "one failure doesn't abort the batch."
- Risk: Two exact SKU matches on genuinely different Shopify products (a real data-quality problem on the merchant's Shopify side) silently picks the wrong one to update.
  Mitigation: "Resolved decisions" item 5 / Acceptance criterion 5 make this an explicit `ambiguous_product_match` failure on that row, never a silent choice.
- Risk: `ShopifyIntegrationEvent.shop_integration_id` being `NOT NULL` while a batch spans multiple shops could tempt an implementer into either skipping the event entirely or picking an arbitrary shop, losing per-shop audit visibility.
  Mitigation: Implementation plan step 18's note makes "one event per distinct shop in the batch" the explicit, non-optional design.
- Risk: The `13_sockets.md` contract's native-WebSocket sample code is followed literally instead of the real `python-socketio` implementation, producing socket code that silently never fires because it targets a system that isn't running.
  Mitigation: The "Deviation from `13_sockets.md`" section makes the real implementation the mandatory reference, with exact file paths to copy from.
- Risk: The unresolved `WorkingSection.allows_shopify_product_modifications` question is implemented as a guess in either direction without the user's confirmation, and turns out to contradict the intended design of that already-in-flight (uncommitted) feature.
  Mitigation: "Clarifications required" item 1 states both the recommendation and why it's genuinely uncertain; this plan should not move to `approved` until the user answers it (structural work in Phases 1, 2, 3, 5, 6, 7 does not depend on the answer and can proceed in parallel — only the router's `require_roles(...)` call in Phase 7 step 24 and the command's authorization check, if any is added, are affected).

## Validation plan

- `py_compile` on every new/changed module.
- `python -m alembic heads` re-confirms a single head before writing migrations; `alembic upgrade head` applies all three new migrations cleanly against a live dev Postgres.
- `pytest app/tests/unit/domain/shopify/` (extended): identity-matching and payload-normalization unit tests pass.
- `pytest app/tests/unit/services/infra/shopify/` (extended): GraphQL infra unit tests pass (mocked `execute_shopify_graphql`).
- `pytest app/tests/unit/services/commands/shopify/` and `app/tests/integration/services/commands/shopify/` (extended): request validation, workspace-scoped shop resolution, row/event/task creation all pass.
- `pytest app/tests/unit/services/tasks/shopify/` and `app/tests/integration/services/tasks/shopify/` (extended): handler partial-success behavior and DB-backed status transitions pass.
- `pytest app/tests/unit/workers/test_shopify_worker.py app/tests/unit/domain/execution/test_shopify_execution_contracts.py` (extended): task/queue/handler registration assertions pass.
- `pytest app/tests/unit/test_shopify_router.py` (extended): role-gating assertions pass.
- Manual/documented check: trigger `POST /products/process` against a real connected dev Shopify shop with one clearly-new SKU and one already-existing SKU in the same batch; confirm one `productCreate` and one `productUpdate` path both complete, both rows reach `SUCCEEDED`, and exactly one `shopify.products.synced` socket event is observed on the workspace room.

## Review log

- `2026-07-09` `Claude`: Drafted this plan from a detailed user-authored capability spec, after reading `57_shopify_integration.md` end to end and the full existing Shopify router/worker/infra/domain/command/query/model/test code, the async-execution (`16_background_jobs.md`), router (`09_routers.md`), command (`06_commands.md`/`06_commands_local.md`), model (`03_models.md`), migration (`30_migrations.md`), testing (`15_testing.md`), and socket (`13_sockets.md`, found stale against the real `python-socketio` implementation) contracts, and confirming the current single Alembic head (`d4f8a1b2c3e4`) directly via `python -m alembic heads`. Discovered an already-added-but-unused `WorkingSection.allows_shopify_product_modifications` flag in the same uncommitted working tree and left it as an open clarification rather than guessing its intended purpose. Left the exact Shopify Admin GraphQL mutation field names as an explicit, scoped-to-Phase-2 open clarification rather than presenting an unverified guess as ground truth. Left in `under_construction` pending both clarifications.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `Codex` (after the user answers both items in "Clarifications required")
