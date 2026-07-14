# PLAN_shopify_metafield_preferences_20260713

## Metadata

- Plan ID: `PLAN_shopify_metafield_preferences_20260713`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-13T00:00:00Z`
- Last updated at (UTC): `2026-07-13T09:05:27Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/pulling_and_storing_metafields.md`

## Goal and intent

- Goal: Add a backend capability that remembers which Shopify product metafield definitions a workspace previously selected for a given internal item category, scoped per Shopify shop integration, and exposes create + targeted-read routes so the Shopify product creation form can auto-load the metafields relevant to the selected category — across one or more Shopify shop integrations in a single request.
- Business/user intent: The frontend silently persists metafield-definition selections while a user completes the Shopify product creation workflow (no explicit "configure mapping" UI). A workspace can have multiple linked Shopify shops, and a single product-creation session may target several of them at once, so the create and read capabilities must operate on a set of shops, not just one. On subsequent product-creation flows for the same category + shop(s), the form pre-loads those definitions with their current Shopify-side characteristics (name, type, validations, choices) so the user doesn't have to re-search for them, per shop.
- Non-goals: persisting metafield *values* on individual products; mirroring Shopify definition characteristics (name/namespace/key/description/type/validations/choices) locally; creating/updating/deleting Shopify metafield definitions; auto-deleting stale preferences during a read; building the frontend selector UI; bulk preference replacement; an admin preference-management page; partial-success creation across shops (this phase is all-or-nothing per request — see §Risks); treating a Shopify metafield-definition GID, or a matching namespace/key/name, as portable across shops. Full non-goal list in intention doc §12.

## Scope

- In scope:
  - New table `shopify_metafield_preferences` (workspace + shop integration + item category + Shopify definition GID + sequence order + enabled flag, standard audit/soft-delete columns) — unchanged by the multi-shop requirement; every row is already shop-scoped (see §17 rationale under Implementation plan step 1).
  - `create_shopify_metafield_preferences` command (plural — batch): accepts one shared `item_category_id` plus a list of shop-specific `(shop_integration_id, shopify_metafield_definition_id, sequence_order)` selections, validates every referenced item category/integration/definition, and creates/restores/re-enables/updates-sequence each selection idempotently, atomically across the whole request.
  - `get_shopify_metafield_preferences` query, now explicitly multi-shop: accepts one-or-more `shop_integration_ids` (always required) plus two independently-triggerable, combinable sub-flows — the **category flow** (`item_category_ids`) and the **search flow** (`q`) — each executed **independently per requested shop**, never mixing definition IDs, domains, or tokens across shops. Results are grouped by shop in the response.
  - Shopify infra client functions remain single-shop-per-call (unchanged signatures): single-node lookup, batched-nodes lookup, and a paginated PRODUCT-metafield-definitions listing used by the local name-matching search. All multi-shop orchestration (looping over requested shops, calling each shop's function once with that shop's own `shop_domain`/`access_token_encrypted`) lives in the command/query service layer, never inside the infra client.
  - Domain result dataclasses + serializers for the merged-preference view and the raw-search-result view (per selection/definition, unchanged shape); a composite per-shop-grouped response serializer; a small domain helper module for query-param normalization (including a new `normalize_shop_integration_ids`) and local/remote merge logic.
  - Two routes on the existing `routers/api_v1/shopify.py` router: `POST /metafield-preferences` (batch create body) and `GET /metafield-preferences` (no path parameter — shop selection moves entirely into the required `shop_integration_ids` query parameter).
  - Alembic migration for the new table (indexes + partial unique constraint) — unchanged.
  - Unit/integration tests per intention doc §13 plus the multi-shop test list in Implementation plan step 10.
- Out of scope: everything in intention doc §12 (see Non-goals above); any frontend work; any change to the existing product-creation/sync flow or webhook flows; partial-success responses when only some requested shops succeed (all-or-nothing only, this phase).
- Assumptions:
  - "Active and usable" for a Shopify integration means `status == ShopifyIntegrationStatusEnum.ACTIVE` and `is_deleted is False` — mirrors the only existing precedent for an admin-triggered Shopify read (`lookup_shopify_customers_by_product_identity.py`), which filters on `status == ACTIVE`. Applied independently to every requested integration, not just the first.
  - No `ShopifyIntegrationEvent` is written by either the create command or the query (see open clarification below).
  - Response payload casing follows this codebase's existing convention (snake_case) throughout, including the new `shops[]` grouping — no camelCase transformation layer exists anywhere in the backend.
  - **Combined-mode response shape, per shop**: when both `item_category_ids` and `q` are supplied, each shop's entry in `shops[]` independently contains both `item_categories`/`unavailable_definition_ids` (category flow) and `search_results` (search flow), non-deduplicated against each other. See open clarification below — unchanged in scope from the prior single-shop revision, just now applied per shop instead of globally once.
  - `only_my_preferences` has no effect on the search flow, in any shop — it only filters local preference rows by `created_by_id`, meaningless for a live Shopify catalog search.
  - Search result cap and mechanism (unchanged, applied **per shop**): the search flow collects at most `SEARCH_RESULTS_LIMIT = 20` matches *per requested shop* by paging that shop's `metafieldDefinitions` connection (queried with `ownerType` passed as a `$ownerType: MetafieldOwnerType!` variable set to the shared `SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` constant — see step 5) in pages of `SHOPIFY_METAFIELD_DEFINITION_PAGE_SIZE = 100`, filtering each page's `name` locally by case-insensitive substring match, stopping at the per-shop match cap or `hasNextPage: false`. There is no global cap across shops — five requested shops can return up to `5 × SEARCH_RESULTS_LIMIT` total matches.
  - Create-result ordering preserves the request's `preferences[]` order; query shop ordering preserves the requested `shop_integration_ids` order (both explicit acceptance criteria — see below).
  - A validation failure anywhere in a multi-shop request (an invalid item category, an invalid/inactive/foreign integration, a definition that fails Shopify validation for its shop, a Shopify transport failure for any one shop) fails the **entire** request — no partial creation, no partial query results. See the new atomicity risk below.

## Clarifications required

- [ ] `should this command emit a ShopifyIntegrationEvent (e.g. a new METAFIELD_PREFERENCE_SAVED event type)?` — the intention doc doesn't ask for one and it's a category-level, not shop-level, change, but `57_shopify_integration.md` states every state-changing command should write one. Skipping it is the default in this plan; confirm before or right after implementation if Route 7's activity feed should reflect this. In the multi-shop design, if this resolves to "yes," the command would need to write one `ShopifyIntegrationEvent` per distinct shop touched by the request (events are shop-scoped rows), not one event for the whole batch.
- [x] ~~is "PRODUCT" the exact GraphQL enum literal for MetafieldDefinition.ownerType?~~ — **Resolved:** Shopify's Admin GraphQL schema defines `PRODUCT` as the `MetafieldOwnerType` value for product-owned metafield definitions. GraphQL listing operations pass `"PRODUCT"` through a variable typed as `MetafieldOwnerType!`, and fetched definitions are accepted only when their returned `ownerType` equals the shared `SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` constant. A development-store schema introspection check confirms that `MetafieldOwnerType.enumValues` includes `PRODUCT`; this verification is not performed during production requests. This clarification no longer blocks implementation. See Implementation plan step 5 and the schema-contract verification in the Validation plan.
- [x] ~~does Shopify's metafieldDefinitions(query:) filter support a substring/partial match on the "name" field?~~ — **Resolved:** Shopify does not document `name` as a supported `metafieldDefinitions(query:)` search field. The implementation does not use `name:*term*` or any other assumed Shopify search-DSL syntax for visible-name search. The backend paginates `PRODUCT` metafield definitions (per shop) and performs case-insensitive substring matching against `MetafieldDefinition.name` in Python, stopping when the configured per-shop result limit is reached or Shopify has no additional pages. See Implementation plan step 5.
- [x] ~~is Shopify shop selection identified by domain or by integration ID?~~ — **Resolved:** Shopify shop selection is identified by `ShopifyShopIntegration.client_id`, not by a raw shop domain. Both create and query operations support one or more selected Shopify integrations. The backend resolves each integration's authoritative `shop_domain` and encrypted access token from the database — the frontend never supplies `shop_domain` as request authority (it may appear in the response as descriptive metadata only). Because Shopify metafield-definition GIDs are shop-specific, create requests carry a separate definition ID for each shop-specific preference selection. Query and search results are grouped by shop, and Shopify calls are executed independently per integration. See Implementation plan steps 6–9.
- [ ] `should search_results and item_categories be deduplicated/cross-referenced when both item_category_ids and q are supplied, within the same shop's entry?` — this plan's default is "no, independent sections per shop" (see Assumptions above); confirm with whoever owns the frontend picker UX before treating this as final.

## Acceptance criteria

The capability is complete when:

1. The frontend can create metafield preferences for one or more Shopify integrations in one request.
2. Every create selection contains its own integration ID, definition ID, and sequence order.
3. Every Shopify definition is validated against its corresponding shop — never against a different selected shop's credentials.
4. Multi-shop creation is atomic: any invalid integration, invalid definition, or database failure anywhere in the request rolls back the entire command, leaving zero preference rows created or modified.
5. The query route accepts one or more `ShopifyShopIntegration.client_id` values via a required `shop_integration_ids` query parameter, with no shop-scoped path parameter.
6. The backend resolves authoritative `shop_domain`/`access_token_encrypted` from the `shopify_shop_integrations` table for every referenced integration — the frontend never supplies a raw shop domain as request authority.
7. Category preferences are queried and hydrated independently per shop (a separate `nodes(ids:)` batch call per shop, never a cross-shop batch).
8. The search flow is executed independently per shop, using that shop's own domain/token.
9. Both query result types are grouped under a top-level `shops[]` array in the response.
10. Definition IDs, domains, and access tokens are never mixed across Shopify shops, in either the create command or the query.
11. Result limits (`SEARCH_RESULTS_LIMIT`) apply per shop, not globally across all requested shops.
12. The response preserves the requested shop order (`shop_integration_ids` for the query; `preferences[]` order for the create command's result list).
13. Raw shop domains are never accepted as request authority in either route.
14. The `shopify_metafield_preferences` table continues to store only the shop-specific preference relationship — no raw `shop_domain`, no Shopify-controlled definition characteristics.
15. Automated tests cover multi-shop creation, atomic rollback, per-shop category hydration, per-shop search, authorization, and Shopify failure paths (Implementation plan step 10).

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: baseline layering (router → service → domain → model).
- `backend/architecture/04_context.md`: `ServiceContext` shape — `incoming_data`/`query_params`/`identity`/`session`, `ctx.workspace_id`/`ctx.user_id` never read from `incoming_data`.
- `backend/architecture/05_errors.md`: `DomainError` subclasses (`NotFound`, `ValidationError`, `ConflictError`, `PermissionDenied`, `ExternalServiceError`) and the `run_service` error boundary.
- `backend/architecture/06_commands.md` + `06_commands_local.md`: command skeleton; local `maybe_begin` transaction helper — **the atomicity requirement for multi-shop create (acceptance criterion 4) is satisfied by this existing mechanism**: one `maybe_begin` block wraps the entire batch, all validation happens before any `session.add()`, and any exception anywhere in the block propagates to the owning transaction's rollback. No new transaction primitive is needed.
- `backend/architecture/07_queries.md` + `07_queries_local.md`: local override — offset pagination is **not** used here (this query is a targeted, non-paginated lookup by explicit ID lists, matching `lookup_shopify_customers_by_product_identity.py`'s shape).
- `backend/architecture/09_routers.md`: router skeleton, `ServiceContext` construction, path-param merging into `incoming_data`. The query route no longer has a path parameter (see §8 below) — `shop_integration_ids` moves entirely into `query_params`.
- `backend/architecture/21_naming_conventions.md`: file/function/table naming used throughout this plan.
- `backend/architecture/40_identity.md`: `IdentityMixin`, `CLIENT_ID_PREFIX` registry — this plan registers `shpmfp`.
- `backend/architecture/41_user.md`, `42_event.md`, `48_presence.md`: loaded per core-contract policy; not independently load-bearing for the multi-shop correction.
- `backend/architecture/03_models.md`: table-file contract, mandatory FK indexing, composite/partial unique index conventions — unaffected by the multi-shop change (see step 1).
- `backend/architecture/08_domain.md`: where domain guards/normalizers/mergers belong vs. models/services.
- `backend/architecture/30_migrations.md`: migration review checklist; still a single new-table migration, no change.
- `backend/architecture/46_serialization.md`: services return dataclasses, routers pick the serializer view; the new `shops[]`-grouped composite response is an explicitly exempted "computed dict" shape, same reasoning as the prior single-shop composite response, one level deeper.
- `backend/architecture/24_multi_tenancy.md`: `workspace_id` always from `ctx.workspace_id`, always the first query filter — now applied to a **set** of integrations and a **set** of categories per request, not a single one each.
- `backend/architecture/25_soft_delete.md`: `is_deleted`/`deleted_at` pair, restore pattern, mandatory `is_deleted.is_(False)` filtering — applied per selection in the batch create, per shop in the query.
- `backend/architecture/28_roles_permissions.md`: role constants and `require_roles([...])` — this app's actual role set is `ADMIN, WORKER, MANAGER, SELLER` from `routers/utils/roles.py`.
- `backend/architecture/57_shopify_integration.md`: **primary contract for this feature** — file structure, data model conventions, the "never call Shopify inline from an HTTP request handler" rule and its scope (see the inline-calls finding below), and the security-model note on `ctx.session.get()` + manual workspace check for single-row ownership — now generalized to a `select(...).where(client_id.in_(ids), workspace_id==...)` batch-ownership check for multiple integrations at once (see step 6/8).

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: `maybe_begin` — wraps the entire multi-shop create batch in one transaction (see Contracts loaded above).
- `backend/architecture/07_queries_local.md`: offset-pagination override — explicitly **not applied** here; this query is a targeted-by-ID-set lookup, not a list.

### Finding that shapes the implementation — inline Shopify calls are already an established pattern for reads

`57_shopify_integration.md`'s rule "Never call Shopify's API inline from an HTTP request handler" is written in the context of webhook subscription mutations and business processing, which route through `queue:shopify` via `create_instant_task`. Reading the actual codebase shows this does **not** extend to read-only, request-time Shopify lookups that the caller needs synchronously to render a response:

- `services/queries/shopify/lookup_shopify_customers_by_product_identity.py` — an existing **query** service, invoked synchronously from `POST /customers/by-product-identity`, calls Shopify's GraphQL API inline for **multiple shops in a loop** (it already iterates every `ACTIVE` integration in the workspace, partitioning successes/failures per shop) and returns the live result directly in the HTTP response. This is the closest existing precedent for this plan's per-shop-loop design, not just for "inline calls are fine," but specifically for "looping per-shop with per-shop credentials is an established pattern."
- `services/commands/shopify/process_shopify_products.py` (the mutating "create/update a Shopify product" command) is the counter-example: it does **not** call Shopify inline — it persists rows and enqueues a task, and the actual mutation calls happen in the worker.

The distinction the codebase draws is **mutation vs. read**, not **command vs. query**: a command/query that *writes to Shopify* goes through the worker; one that *only reads from Shopify* to answer the current request runs inline, with `ShopifyGraphQLRetryableError`/`ShopifyGraphQLNonRetryableError` surfacing as `ExternalServiceError` (502) through `run_service`. Both new services in this plan are reads (metafield-definition validation, metafield-definition hydration/search) — neither creates, updates, or deletes anything in Shopify — so both call Shopify inline, synchronously, once per requested shop.

One nuance this plan does **not** copy from `lookup_shopify_customers_by_product_identity.py`: that query treats a single shop's Shopify failure as a per-shop partial failure (collects `failed_shops`, keeps going). This plan's multi-shop create and query instead fail the **entire** request on any single shop's failure (see Assumptions and the atomicity acceptance criteria) — a deliberate, narrower choice for this feature, not an oversight; partial-success handling is explicitly out of scope for this phase.

### File read intent — pattern vs. relational

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead.
- **What exists** → reading is legitimate.

Permitted (relational reads), already done during planning, safe to re-open during implementation:
- `models/tables/items/item_category.py`, `models/tables/shopify/shopify_shop_integration.py` — exact columns/FKs.
- `services/commands/shopify/create_shopify_reauthorize_url.py` — the `ctx.session.get()` + manual workspace check idiom, now generalized to a batch `select(...).where(client_id.in_(ids))` for multiple integrations.
- `services/commands/issue_types/create_issue_type.py` — the `select(...).where(workspace_id==, client_id==, is_deleted.is_(False))` + `raise NotFound` idiom, and specifically its "validate a set of referenced entities, dedupe checks by ID, only insert junction rows for validated ones" loop shape (`create_issue_type.py`'s `linked_item_category_ids`/`linked_working_section_ids` loops) — the closest existing precedent in this codebase for "validate N referenced entities in one command before writing N related rows," directly analogous to validating N shop integrations before creating N preference rows.
- `services/queries/shopify/lookup_shopify_customers_by_product_identity.py` — the inline-Shopify-read-from-a-query precedent, and its per-shop-loop structure (see Finding above).
- `services/infra/shopify/graphql_client.py`, `product_identity_client.py` — `execute_shopify_graphql` signature, error semantics, module-level `_QUERY = """..."""` convention.
- `services/commands/shopify/_events.py` — only if the "emit an event" clarification resolves to yes.
- `domain/shopify/results.py`, `domain/shopify/serializers.py`, `domain/users/serializers.py` (`serialize_user_working_section_member`) — exact existing shapes to extend rather than duplicate.
- `routers/api_v1/shopify.py` — existing imports, role gates per route, router-level route ordering. Note: the query route no longer follows the `/shops/{shop_integration_id}/...` sub-route grouping (see step 9) since it is no longer scoped to one shop's path segment.
- `migrations/versions/677ed7131bb2_create_shopify_integration_foundation.py` — table-creation migration shape; `alembic heads` output (current head: `a3d4e5f6a7b8`).
- `models/__init__.py` — where to add the new table import.
- `tests/unit/services/queries/shopify/test_lookup_shopify_customers_by_product_identity.py`, `tests/integration/services/commands/shopify/test_shopify_admin_commands.py`, `tests/unit/test_shopify_router.py`, `tests/integration/models/shopify/test_shopify_foundation_constraints.py` — existing test fixture/mocking patterns to mirror.

### Skill selection

- Primary skill: none — document-only planning task per the mapping guide's "Document-only protocol (no resolver)."
- Excluded alternatives: `16_background_jobs.md` / `51_worker_runtime.md` / `12_infra_redis.md` (Worker-driven backend bundle) — both new services remain synchronous reads with an established inline precedent, not worker-routed mutations, even when looped per-shop; `11_infra_events.md` / `13_sockets.md` — no realtime/socket surface and (per the open clarification) likely no domain event.

## Implementation plan

1. **Model** — `models/tables/shopify/shopify_metafield_preference.py`: `ShopifyMetafieldPreference(IdentityMixin, Base)`, `CLIENT_ID_PREFIX = "shpmfp"`, `__tablename__ = "shopify_metafield_preferences"`. **No structural change for multi-shop support** — the table already carries `shop_integration_id` as part of its identity, so every row is already shop-specific; there is nothing to add. Columns, copying `ItemCategory`'s exact audit/soft-delete shape (this codebase hand-declares these per table — there is no shared mixin):
   - `workspace_id: String(64) FK workspaces.client_id ondelete=RESTRICT, nullable=False, index=True`
   - `item_category_id: String(64) FK item_categories.client_id ondelete=RESTRICT, nullable=False, index=True`
   - `shop_integration_id: String(64) FK shopify_shop_integrations.client_id ondelete=RESTRICT, nullable=False, index=True`
   - `shopify_metafield_definition_id: String(255), nullable=False` — stores the raw Shopify GID string, scoped implicitly to `shop_integration_id`; the same GID string appearing under two different `shop_integration_id` values is not the same resource and both rows are valid/independent (see Risks).
   - `sequence_order: Integer, nullable=False`
   - `is_enabled: Boolean, nullable=False, default=True, server_default=text("true")`
   - `created_at`, `created_by_id` (FK users.client_id, ondelete=RESTRICT, nullable=True, index=True), `updated_at` (nullable, `onupdate=`), `updated_by_id` (FK users.client_id, ondelete=RESTRICT, nullable=True), `is_deleted` (default False), `deleted_at` (nullable), `deleted_by_id` (FK users.client_id, ondelete=RESTRICT, nullable=True) — exact shape copied from `item_category.py`.
   - No `shop_domain` column, and none is ever added — the domain is always resolved live from `shopify_shop_integrations.shop_domain` at request time, never persisted redundantly on the preference row.
   - `__table_args__`:
     - `Index("ix_shopify_metafield_preferences_workspace_shop_category", "workspace_id", "shop_integration_id", "item_category_id")`
     - `Index("ix_shopify_metafield_preferences_workspace_shop_category_creator", "workspace_id", "shop_integration_id", "item_category_id", "created_by_id")`
     - `Index("uix_shopify_metafield_preferences_active_scope", "workspace_id", "shop_integration_id", "item_category_id", "shopify_metafield_definition_id", unique=True, postgresql_where=text("is_deleted = false"))` — the four-column scope (workspace + shop + category + definition) is exactly what keeps two shops' identical-GID rows independent and two different-GID rows for the same shop+category both insertable.
   - Register the new module in `models/__init__.py` alongside the other `models.tables.shopify` imports (alphabetically, after `shopify_integration_event`, before `shopify_oauth_state`).

2. **Migration** — `alembic revision --autogenerate -m "create_shopify_metafield_preferences_table"` against local HEAD `a3d4e5f6a7b8`. Review the generated file against `677ed7131bb2_create_shopify_integration_foundation.py`'s shape. Unaffected by the multi-shop correction — no schema change was needed.

3. **Domain: results + serializers** — `domain/shopify/results.py`: add (unchanged from the prior revision — these are per-selection/per-definition shapes, not per-shop-group shapes):
   ```python
   @dataclass(frozen=True)
   class ShopifyMetafieldPreferenceResult:
       client_id: str
       item_category_id: str
       shop_integration_id: str
       shopify_metafield_definition_id: str
       name: str | None
       namespace: str | None
       key: str | None
       description: str | None
       type: str | None
       validations: list[dict] | None
       sequence_order: int
       is_enabled: bool
       created_at: str
       updated_at: str | None
       created_by: dict | None

   @dataclass(frozen=True)
   class ShopifyMetafieldDefinitionResult:
       shopify_metafield_definition_id: str
       name: str | None
       namespace: str | None
       key: str | None
       description: str | None
       type: str | None
       validations: list[dict] | None
   ```
   `domain/shopify/serializers.py`: add `serialize_shopify_metafield_preference(r: ShopifyMetafieldPreferenceResult) -> dict` and `serialize_shopify_metafield_definition(r: ShopifyMetafieldDefinitionResult) -> dict` (both unchanged plain field mappings).

   **Composite, per-shop-grouped response serializer — replaces the single-shop version:**
   ```python
   def serialize_shopify_metafield_preferences_response(data: dict) -> dict:
       return {
           "shops": [
               {
                   "shop_integration_id": shop["shop_integration_id"],
                   "shop_domain": shop["shop_domain"],
                   "item_categories": [
                       {
                           "item_category_id": category["item_category_id"],
                           "metafield_preferences": [
                               serialize_shopify_metafield_preference(r)
                               for r in category["metafield_preferences"]
                           ],
                       }
                       for category in shop["item_categories"]
                   ],
                   "unavailable_definition_ids": shop["unavailable_definition_ids"],
                   "search_results": [
                       serialize_shopify_metafield_definition(r)
                       for r in shop["search_results"]
                   ],
               }
               for shop in data["shops"]
           ]
       }
   ```
   `data["shops"]` is a plain list of dicts assembled by the query service (step 8) — not a new dataclass. This keeps the same "computed/composite result is an exempt plain-dict shape" reasoning from `46_serialization.md` that already applied to the single-shop version, just with one more level of grouping. Results from different shops are never flattened into one `item_categories`/`search_results` list — each shop's dict is self-contained.

4. **Domain: metafield-preference helpers** — `domain/shopify/metafield_preferences.py` (pure functions, no DB/HTTP access):
   - `SHOPIFY_METAFIELD_DEFINITION_GID_PATTERN` + `is_shopify_metafield_definition_gid(value: str) -> bool` — unchanged.
   - `normalize_item_category_ids(raw: str | None) -> list[str]` — unchanged; optional, `[]` means "category flow not requested."
   - `parse_only_my_preferences(raw: object) -> bool` — unchanged.
   - `normalize_search_query(raw: str | None) -> str | None` — unchanged; `None` means "search flow not requested."
   - `merge_metafield_preference_with_definition(...)`, `map_shopify_metafield_definition_node(...)` — unchanged, both still operate on one selection/definition at a time regardless of how many shops are being processed.
   - **New:** `normalize_shop_integration_ids(raw: str | None) -> list[str]` — identical normalization contract to `normalize_item_category_ids`: split on `,`, trim whitespace, drop empty values, dedupe while preserving first-seen order, return `[]` for missing/whitespace-only input. Used for the query's now-required `shop_integration_ids` param. Unlike `item_category_ids`, an empty result here is always a validation error in the query service (`shop_integration_ids` is mandatory, not one-of-two-optional) — the normalizer itself stays symmetric with `normalize_item_category_ids` and does not special-case that; the mandatoriness is enforced by the caller (step 8).

5. **Infra: Shopify metafield-definition client** — `services/infra/shopify/metafield_definition_client.py`. All three functions remain single-shop-per-call (unchanged from the prior revision): every function takes exactly one `shop_domain`/`access_token_encrypted` pair and returns data for that one shop. This is a deliberate boundary — **the infra client never knows about "multiple shops."** All looping over requested shops — calling each of these functions once per shop with that shop's own credentials — happens in the command (step 7) and query (step 8) service layers. This keeps the infra layer trivially testable (one shop in, one shop's data out) and makes it structurally impossible for a bug in the client to leak one shop's token into another shop's request.

   **Shared owner-type constant** — defined once in this module, imported by the command and query layers wherever a "is this a product metafield definition" check is needed. No raw `"PRODUCT"` string literal is repeated anywhere else in the codebase for this feature:
   ```python
   SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE = "PRODUCT"
   ```

   - `GET_METAFIELD_DEFINITION_BY_ID_QUERY` — `query GetMetafieldDefinition($id: ID!) { node(id: $id) { id ... on MetafieldDefinition { id name namespace key description ownerType type { name } validations { name value } } } }`. `async def fetch_shopify_metafield_definition_by_id(*, shop_domain, access_token_encrypted, definition_id) -> dict | None` — returns `data["node"]` (may legitimately be `None`, not an error). Shopify's `node(id:)` field takes no `ownerType` argument, so this function does not filter by owner type itself — it returns whatever node Shopify resolves, `ownerType` field included, and leaves the `SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` comparison to the caller (command step 7, query step 8). Keeping this function a thin, honest "fetch by ID, no opinions" wrapper avoids two different places deciding what counts as "not found."
   - `GET_METAFIELD_DEFINITIONS_BY_IDS_QUERY` — same shape with `nodes(ids: $ids)`. `async def fetch_shopify_metafield_definitions_by_ids(*, shop_domain, access_token_encrypted, definition_ids) -> dict[str, dict | None]` — same "no `ownerType` argument, caller checks the returned field" contract, applied per ID in the returned map.
   - `LIST_PRODUCT_METAFIELD_DEFINITIONS_QUERY` — used by the search flow's pagination. Passes `ownerType` as a **typed GraphQL variable**, not an embedded literal, so Shopify's schema validates the enum value directly and the value exists in exactly one place in the codebase (the constant above):
     ```graphql
     query ListProductMetafieldDefinitions($ownerType: MetafieldOwnerType!, $first: Int!, $after: String) {
       metafieldDefinitions(ownerType: $ownerType, first: $first, after: $after) {
         nodes {
           id
           name
           namespace
           key
           description
           ownerType
           type { name }
           validations { name value }
         }
         pageInfo {
           hasNextPage
           endCursor
         }
       }
     }
     ```
     Called with `variables={"ownerType": SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE, "first": ..., "after": ...}`. Because Shopify filters server-side on `ownerType` here, every returned node is already product-owned — `ownerType` is still requested in the selection set (consistency with the other two queries, and cheap defense-in-depth), but no additional client-side rejection is needed on this path specifically.
   - `async def fetch_shopify_product_metafield_definitions_page(*, shop_domain, access_token_encrypted, first, after) -> ShopifyMetafieldDefinitionPage` — thin wrapper around `execute_shopify_graphql(..., operation_name="ListProductMetafieldDefinitions")`, passing `ownerType=SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` internally (callers of this function never supply an owner type — this module only ever deals in product metafields). Returns `ShopifyMetafieldDefinitionPage(nodes: list[dict], has_next_page: bool, end_cursor: str | None)`.
   - `async def search_shopify_metafield_definitions_by_name(*, shop_domain, access_token_encrypted, search_term, result_limit=SEARCH_RESULTS_LIMIT) -> list[dict]` — paginates via `fetch_shopify_product_metafield_definitions_page` (`SHOPIFY_METAFIELD_DEFINITION_PAGE_SIZE = 100`), matches each page's `name` field with case-insensitive substring comparison against `search_term`, stops at `result_limit` matches or when Shopify reports no more pages (unchanged logic from the prior revision — see the resolved DSL clarification above for why no `query:` search argument is used).

   **Where the `ownerType` check actually happens:** the command (step 7) and query (step 8) compare a fetched node's `ownerType` field against `SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` — imported from this module, never re-declared as a raw string — for any node retrieved via the two node/nodes lookups. The listing query needs no equivalent client-side check, since Shopify's own `ownerType` argument already scopes that result set server-side.

6. **Command: request parser** — replaces the single-selection parser from the prior revision. New location: `services/commands/shopify/requests/create_shopify_metafield_preferences_request.py`:
   ```python
   class CreateShopifyMetafieldPreferenceSelectionRequest(BaseModel):
       shop_integration_id: str
       shopify_metafield_definition_id: str
       sequence_order: int = Field(ge=0)

       @field_validator("shopify_metafield_definition_id")
       @classmethod
       def _validate_gid_shape(cls, value: str) -> str:
           if not is_shopify_metafield_definition_gid(value):
               raise ValueError("shopify_metafield_definition_id must be a Shopify MetafieldDefinition GID.")
           return value

   class CreateShopifyMetafieldPreferencesRequest(BaseModel):
       item_category_id: str
       preferences: list[CreateShopifyMetafieldPreferenceSelectionRequest] = Field(min_length=1)

       @model_validator(mode="after")
       def _reject_duplicate_selections(self) -> "CreateShopifyMetafieldPreferencesRequest":
           seen = set()
           for selection in self.preferences:
               key = (selection.shop_integration_id, selection.shopify_metafield_definition_id)
               if key in seen:
                   raise ValueError(
                       "Duplicate preference selection for the same shop_integration_id "
                       "and shopify_metafield_definition_id."
                   )
               seen.add(key)
           return self
   ```
   `parse_create_shopify_metafield_preferences_request(data: dict) -> CreateShopifyMetafieldPreferencesRequest`, raising `ValidationError` on a `PydanticValidationError`, mirroring the existing try/except shape used elsewhere in this domain.

   **Duplicate identity is `(shop_integration_id, shopify_metafield_definition_id)`, not `shop_integration_id` alone** — a request may legitimately contain several different definitions for the same shop (the user selecting multiple metafields for one category on one shop), and this is explicitly allowed, not just tolerated. Only an exact repeat of both fields together is rejected.

   Every `shopify_metafield_definition_id` is still validated for GID shape per-selection (field-level, before the request even reaches the command); existence and `ownerType` are still confirmed live against Shopify per-selection in the command (step 7), never here.

7. **Command** — renamed from `create_shopify_metafield_preference` (singular) to **`create_shopify_metafield_preferences`** (plural, batch). New location: `services/commands/shopify/create_shopify_metafield_preferences.py`:
   ```python
   async def create_shopify_metafield_preferences(
       ctx: ServiceContext,
   ) -> list[ShopifyMetafieldPreferenceResult]:
   ```
   Execution flow, all inside one `async with maybe_begin(ctx.session):` block (this single block is what makes the whole batch atomic — see Contracts loaded above):

   1. **Parse the request** (step 6) — `item_category_id` plus `preferences: list[...]`, already GID-shape-validated and de-duplicated by `(shop_integration_id, shopify_metafield_definition_id)` at the Pydantic layer.
   2. **Resolve identity** — `workspace_id`/`created_by_id` from `ctx.identity` only, never from the request body.
   3. **Validate the item category once** — `select(ItemCategory).where(workspace_id==ctx.workspace_id, client_id==request.item_category_id, is_deleted.is_(False))`; `None` → `raise NotFound`. One lookup regardless of how many shop selections reference it, since `item_category_id` is shared across the whole payload.
   4. **Resolve all requested integrations in one query** — build the deduplicated set of `shop_integration_id`s across `request.preferences`, then `select(ShopifyShopIntegration).where(workspace_id==ctx.workspace_id, client_id.in_(requested_integration_ids), is_deleted.is_(False))`. For every requested ID not present in the result, or present but `status != ShopifyIntegrationStatusEnum.ACTIVE` → `raise NotFound`/`raise ValidationError` (same distinction as the prior single-shop revision: missing/wrong-workspace/deleted is `NotFound`, found-but-inactive is `ValidationError`) — **before any Shopify call or DB write**. Build `integrations_by_id: dict[str, ShopifyShopIntegration]` from the validated rows.
   5. **Validate every definition against its own shop** — for each selection in `request.preferences` (not deduplicated by definition ID across shops — a definition must be validated once per shop it's selected for, since the same GID string in two shops' selections refers to two different Shopify resources): look up `integrations_by_id[selection.shop_integration_id]`, call `fetch_shopify_metafield_definition_by_id(shop_domain=integration.shop_domain, access_token_encrypted=integration.access_token_encrypted, definition_id=selection.shopify_metafield_definition_id)` **using that integration's own credentials**. If the result is `None`, not a `MetafieldDefinition`, or `definition.get("ownerType") != SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` (constant imported from `services/infra/shopify/metafield_definition_client.py`, step 5 — never a re-declared `"PRODUCT"` literal) → `raise NotFound("Shopify metafield definition not found.")`. Let `ShopifyGraphQLRetryableError`/`ShopifyGraphQLNonRetryableError` propagate. Collect the validated definition payload per selection (`{selection_index: definition_node}` or keyed by `(shop_integration_id, shopify_metafield_definition_id)`) for reuse in step 8 without re-fetching. **Shop A's integration is never used to validate a selection whose `shop_integration_id` is shop B** — this is enforced structurally by looking up the integration per-selection from `integrations_by_id`, not by holding one "current shop" variable across the loop.
   6. **Create, restore, or update — per selection, same idempotent rule as the prior single-shop revision, now applied independently to each `(shop_integration_id, shopify_metafield_definition_id)` pair:**
      - `select(ShopifyMetafieldPreference).where(workspace_id==, shop_integration_id==selection.shop_integration_id, item_category_id==request.item_category_id, shopify_metafield_definition_id==selection.shopify_metafield_definition_id)` — no `is_deleted` filter (need soft-deleted rows to restore).
      - No row → create; existing soft-deleted row → restore + update `sequence_order`; existing disabled row → re-enable + update `sequence_order`; existing active row → update `sequence_order` only if it differs. Exactly the four-way branch from the prior revision, unchanged in logic, just invoked once per selection in a loop.
      - **Updating one shop's preference row never touches another shop's row** — each selection's `select(...)` is scoped by its own `shop_integration_id`, so there is no shared mutable state across iterations beyond the shared `item_category_id`.
   7. **Atomicity** — no explicit rollback code is needed: steps 3–5 (all validation, including every Shopify call) complete, for every selection, before step 6 performs its first `session.add()`/`flush()`. If any validation fails, the function raises before any write is staged. If a failure occurs *during* step 6 (e.g. a DB constraint violation on a later selection), the exception propagates out of the `maybe_begin` block, which rolls back the whole transaction — including any earlier selections in the same request that had already been flushed but not committed. No preferences are ever created for only the successful shops; a full-batch failure leaves zero rows changed.
   8. **Return results** — build one `ShopifyMetafieldPreferenceResult` per processed selection (via `merge_metafield_preference_with_definition`, reusing the definition payload collected in step 5 and a `created_by` dict resolved once for `ctx.user_id`), **in the same order as `request.preferences`** — the list comprehension iterates the original request list, not a dict/set, so ordering is preserved by construction rather than by an explicit re-sort.

   Return `list[ShopifyMetafieldPreferenceResult]` (services return dataclasses, not dicts, per `46_serialization.md`) — the router applies `serialize_shopify_metafield_preference` to each entry.

8. **Query** — `services/queries/shopify/get_shopify_metafield_preferences.py`, `async def get_shopify_metafield_preferences(ctx: ServiceContext) -> dict`:
   - Read `shop_integration_ids`, `item_category_ids`, `only_my_preferences`, and `q` from `ctx.query_params` (all query params now — there is no path parameter). Normalize via `normalize_shop_integration_ids`, `normalize_item_category_ids`, `parse_only_my_preferences`, `normalize_search_query`.
   - **Validation**: normalized `shop_integration_ids` empty → `raise ValidationError("Provide shop_integration_ids and at least one of item_category_ids or q.")`. Same message also covers the case where `shop_integration_ids` is present but both `item_category_ids` and `q` are empty/`None`.
   - **Resolve all requested integrations in one workspace-scoped query** — `select(ShopifyShopIntegration).where(workspace_id==ctx.workspace_id, client_id.in_(shop_integration_ids), is_deleted.is_(False))`. Any requested ID missing from the result, or present but not `ACTIVE`, → fail the entire request (`NotFound`/`ValidationError`, same distinction as the command). Build an **ordered** mapping keyed by the original `shop_integration_ids` order (not DB return order, which is unspecified) — e.g. iterate the normalized ID list and look each one up in a `{id: integration}` dict built from the query result — so the final response can preserve the frontend's requested shop order (acceptance criterion 12).
   - **For each integration, in requested order, build that shop's response entry independently:**
     - **Category flow** (runs per-shop only when `item_category_ids` is non-empty): identical logic to the prior single-shop revision, but scoped to `shop_integration_id == this_integration.client_id` in the preference query, and — critically — the deduplicated definition-ID list and the `fetch_shopify_metafield_definitions_by_ids` call are built **per shop, from only that shop's preference rows**. A definition ID belonging to shop A's rows is never combined into shop B's `nodes(ids:)` batch call, even if the same literal GID string happens to also appear among shop B's rows (which would itself indicate a data problem, not a reason to merge the calls). A returned node is routed into that shop's `unavailable_definition_ids` (rather than `item_categories`) when it is `None`, not a `MetafieldDefinition`, or its `ownerType` does not equal `SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` (step 5) — same three-way check as the create command, applied per node here instead of per selection. Item-category workspace-ownership validation (`select(ItemCategory.client_id).where(...)`) happens once, shared across all shops, since `item_category_ids` is not shop-specific input.
     - **Search flow** (runs per-shop only when `q` is non-`None`): `search_shopify_metafield_definitions_by_name(shop_domain=this_integration.shop_domain, access_token_encrypted=this_integration.access_token_encrypted, search_term=q)` — called once per requested shop, each call independently capped at `SEARCH_RESULTS_LIMIT` and paginating that shop's own `metafieldDefinitions` connection. No global cap or dedup across shops (see Assumptions).
     - Any `ShopifyGraphQLRetryableError`/`ShopifyGraphQLNonRetryableError` from any shop's category-flow or search-flow call propagates and fails the **entire** request — no partial results for the other, already-succeeded shops are returned (see Assumptions/Non-goals: partial success across shops is out of scope this phase).
     - Assemble `{"shop_integration_id": ..., "shop_domain": this_integration.shop_domain, "item_categories": [...], "unavailable_definition_ids": [...], "search_results": [...]}` for this shop. `shop_domain` here is purely descriptive response metadata resolved from the validated DB row — it was never accepted as request input.
   - Return `{"shops": [<per-shop dict above>, ...]}` in requested-shop order — a plain dict of dicts/dataclasses (exempt "computed result" shape per `46_serialization.md`); the router calls `serialize_shopify_metafield_preferences_response` (step 3).

9. **Router** — edit `routers/api_v1/shopify.py`:
   - **Create body models** (replace the single-selection body from the prior revision):
     ```python
     class ShopifyMetafieldPreferenceSelectionBody(BaseModel):
         shop_integration_id: str
         shopify_metafield_definition_id: str
         sequence_order: int = Field(ge=0)

     class ShopifyMetafieldPreferencesCreateBody(BaseModel):
         item_category_id: str
         preferences: list[ShopifyMetafieldPreferenceSelectionBody] = Field(min_length=1)
     ```
   - `POST /metafield-preferences` (unchanged path) → roles `[ADMIN, MANAGER, SELLER, WORKER]` → `ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)` → `run_service(create_shopify_metafield_preferences, ctx)` → on success, `build_ok([serialize_shopify_metafield_preference(result) for result in outcome.data])` — serializing the list result, not a single object.
   - **`GET /metafield-preferences`** (replaces `GET /shops/{shop_integration_id}/metafield-preferences` — no path parameter, no shop-scoped sub-route grouping) → roles `[ADMIN, MANAGER, SELLER, WORKER]` → `ServiceContext(incoming_data={}, query_params=dict(request.query_params), identity=claims, session=session)` → `run_service(get_shopify_metafield_preferences, ctx)` → `build_ok(serialize_shopify_metafield_preferences_response(outcome.data))`. All of `shop_integration_ids`, `item_category_ids`, `q`, `only_my_preferences` arrive purely as query-string params — the route forwards `dict(request.query_params)` wholesale, same mechanism as before, just with one more recognized key and zero path params. Because this route's path (`/metafield-preferences`) shares no prefix segment with any existing `/shops/{shop_integration_id}/...` route, there is no route-declaration-ordering conflict to manage (`09_routers.md`'s wildcard-ordering rule only matters within a shared path prefix).
   - Update the two command/query imports to the renamed modules (`create_shopify_metafield_preferences`, unchanged `get_shopify_metafield_preferences`).

10. **Tests** — replaces the prior revision's test list. Organized by the same grouping used in the requirements:

    **Multi-shop create** (`tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py`, real DB session mirroring `test_shopify_admin_commands.py`, `monkeypatch` on `fetch_shopify_metafield_definition_by_id` keyed by shop domain so each mocked shop returns its own definition set):
    1. Creating preferences for two valid Shopify integrations in one request.
    2. Creating several different metafield preferences for the same shop in one request.
    3. Rejecting an exact duplicate `(shop_integration_id, shopify_metafield_definition_id)` entry in one payload (Pydantic-level `ValidationError`, never reaches the command body).
    4. Confirming each definition is validated against its corresponding shop (assert the mock was called with each selection's own `shop_domain`/`access_token_encrypted`).
    5. Confirming shop A's token is never used to validate shop B's definition (assert on the exact credentials passed per call, not just call count).
    6. Confirming a failure validating the second shop's definition rolls back the first shop's already-processed (but not yet committed) preference — query the table after the failed call and assert zero rows exist for either shop.
    7. Rejecting an integration outside the authenticated workspace (`NotFound`, whole request fails).
    8. Rejecting an inactive or soft-deleted integration (`NotFound`/`ValidationError` per the missing-vs-inactive distinction, whole request fails).
    9. Preserving create-result ordering according to the request's `preferences[]` order, including when shops are interleaved (e.g. shop B selection before shop A selection in the payload).
    10. Confirming idempotency independently per shop — repeating the same multi-shop request twice does not duplicate rows for either shop, and updating only one shop's `sequence_order` in a repeat request does not touch the other shop's row.

    **Multi-shop category query** (`tests/integration/services/queries/shopify/test_get_shopify_metafield_preferences.py`, real DB session + monkeypatched `fetch_shopify_metafield_definitions_by_ids` keyed by shop domain):
    11. Querying preferences for multiple shops and one item category.
    12. Querying multiple shops and multiple item categories.
    13. Performing exactly one batched `nodes(ids:)` request per shop (assert call count equals requested-shop count, not requested-preference-row count).
    14. Never combining definition IDs from different shops into one request (assert each call's `definition_ids` argument only contains IDs belonging to that shop's own preference rows).
    15. Using the correct domain and token for every shop's call.
    16. Returning item categories grouped under the correct shop in the response.
    17. Preserving `sequence_order` independently within each shop/category group.
    18. Reporting unavailable definition IDs under the correct shop (a definition unavailable in shop A does not appear in shop B's `unavailable_definition_ids`, even if shop B also references a same-string GID).
    19. Preserving requested `shop_integration_ids` order in the `shops[]` response array, independent of DB row insertion/return order.
    20. Failing the entire request when one requested integration is invalid (no partial `shops[]` entries for the valid ones).

    **Multi-shop search** (same query test file; monkeypatched `search_shopify_metafield_definitions_by_name` keyed by shop domain):
    21. Running an independent name search for every requested shop.
    22. Returning a separate `search_results` array per shop.
    23. Applying `SEARCH_RESULTS_LIMIT` per shop (a 3-shop request with 20+ matches available in each shop returns up to 60 total, not 20).
    24. Confirming `only_my_preferences` does not affect `search_results` for any shop.
    25. Confirming identical visible names from two shops remain separate results (both appear, under their respective shop's `search_results`, never merged).
    26. Failing the entire request when Shopify search fails for one shop, even if other shops' searches already succeeded.
    27. Confirming no partial-success response is returned in that failure case (assert the whole `outcome.success` is `False`, not that some `shops[]` entries are present and others missing).

    **Router** (`tests/unit/test_shopify_router.py`, `monkeypatch.setattr(shopify_router, "run_service", _fake_run_service)` per the file's existing pattern):
    28. Requiring `shop_integration_ids` on the `GET /metafield-preferences` route (missing param reaches the query service and fails validation — router-level test only confirms the param is forwarded, not that it's individually enforced at the route layer, since that's the service's job per `09_routers.md`).
    29. Confirming the GET route has no shop-integration path parameter (route registered as `/metafield-preferences`, not `/shops/{shop_integration_id}/metafield-preferences`).
    30. Passing all query parameters (`shop_integration_ids`, `item_category_ids`, `q`, `only_my_preferences`) through `ServiceContext.query_params` unmodified.
    31. Accepting the new batch create body (`item_category_id` + `preferences[]`) and passing `body.model_dump()` through `ServiceContext.incoming_data`.
    32. Serializing the create command's list result — `build_ok` receives a list of serialized dicts, not a single dict.
    33. Serializing the query response as `shops[]` via `serialize_shopify_metafield_preferences_response`.

    **Infra client** (`tests/unit/services/infra/shopify/test_metafield_definition_client.py` — still single-shop-per-call, so no new multi-shop test cases belong here; multi-shop orchestration is tested at the command/query level above, per the infra boundary decision in step 5). All mocked against `execute_shopify_graphql`:
    - `fetch_shopify_metafield_definition_by_id` / `fetch_shopify_metafield_definitions_by_ids`: null node, non-`MetafieldDefinition` node, node with `ownerType` other than `SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` (assert the function still returns the raw node — filtering is the caller's job, per step 5's "thin wrapper" decision — not that the function itself raises or filters), batched partial-null response.
    - `search_shopify_metafield_definitions_by_name` / `fetch_shopify_product_metafield_definitions_page`: first page has enough matches (pagination stops early); first page has too few (next page requested via `endCursor`); no matches across all pages (`hasNextPage: false` terminates the loop); case-insensitive matching; substring-against-`name` matching; empty/missing `name` doesn't raise; stop exactly at `SEARCH_RESULTS_LIMIT`; `ShopifyGraphQLRetryableError`/`ShopifyGraphQLNonRetryableError` from any page request propagates.
    - **Owner-type contract regression guards**: the variables dict passed to `execute_shopify_graphql` for `ListProductMetafieldDefinitions` contains `"ownerType": SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` (not a hardcoded `"PRODUCT"` string duplicated in the test — import the same constant the production code imports, so a future rename can't silently desync test from implementation) and contains no `query` key (regression guard against reintroducing the removed DSL assumption).
    - **Schema-contract verification (separate from the mocked suite above)** — per the resolved clarification, do not rely solely on mocked responses to prove Shopify actually accepts `PRODUCT` as a `MetafieldOwnerType` value. Add one of: a manually-run GraphQL introspection query (`query MetafieldOwnerTypeValues { __type(name: "MetafieldOwnerType") { enumValues { name } } }`) documented as a one-off check; a small diagnostic script under `scripts/` that runs it against a configured development Shopify store; or an optional integration test gated behind a dev-store credential env var (skipped by default in CI, matching how any other real-Shopify-store-dependent check in this codebase would be gated). Whichever form is chosen, it asserts the returned `enumValues` list includes `PRODUCT`, and it must never run as part of a normal production request — it is a one-time (or CI-optional) schema-contract check, not request-path code.

    **Model constraints** (`tests/integration/models/shopify/test_shopify_metafield_preference_constraints.py`, unchanged from the prior revision): table exists, FKs enforced, partial unique index enforced per the four-column scope (confirms two shops can hold the same definition GID as independent active rows — this is the model-level proof backing acceptance criterion 10), lookup indexes present.

## Risks and mitigations

- Risk: Reusing one Shopify metafield-definition GID across several shops could create invalid mappings, because Shopify definitions belong to the shop where they were created — a GID valid in shop A may not exist, or may reference a completely unrelated field, in shop B.
  Mitigation: Every create entry includes both `shop_integration_id` and `shopify_metafield_definition_id` (never definition ID alone). The backend validates each definition against that exact selection's integration — using that integration's own `shop_domain`/`access_token_encrypted` — before committing any preference row (step 7, step 5 of the command flow). Multi-shop requests are atomic (`maybe_begin`, single transaction, validation-before-write ordering), so a validation failure against one shop prevents all rows in the request — including any other shop's already-valid selections — from being committed.
- Risk: Partial-success semantics (some shops succeed, some fail) are explicitly not supported this phase; a workspace linking many shops and submitting a large batch request has a higher chance that at least one shop's Shopify call transiently fails, aborting the whole batch even though most shops would have succeeded.
  Mitigation: Accepted as a phase-1 tradeoff per the requirements — "partial-success creation is outside this phase." If this proves painful in practice (e.g. workspaces routinely selecting 5+ shops), a follow-up could introduce per-shop retry or a partial-success response mode as a separate, explicitly-scoped change; do not build it speculatively now.
- Risk: The "no `ShopifyIntegrationEvent`" assumption is wrong and Route 7's activity feed is expected to show preference saves, now further complicated by "one event per shop touched" vs. "one event for the whole batch" being an open design question if this clarification resolves to "yes."
  Mitigation: Flagged as an open clarification; both event-granularity options are small, additive follow-ups that don't require restructuring the atomic-transaction design above.
- Risk: Calling Shopify inline from both the create command and the query, once per requested shop (rather than routing through the worker), could be judged a contract violation on a literal reading of `57_shopify_integration.md`.
  Mitigation: Documented above with the specific existing precedent (`lookup_shopify_customers_by_product_identity.py`) that already loops per-shop with per-shop credentials, inline; both new calls are reads, matching that precedent's scope.
- Risk: Shopify's `nodes(ids:)` response order is not guaranteed to match the input `ids` order in every API version, which would silently corrupt the `definition_id → node` zip in `fetch_shopify_metafield_definitions_by_ids` — now called once per shop, so this risk exists independently per shop rather than once globally.
  Mitigation: Match by the node's own `id` field in the response rather than positional zip; only fall back to positional handling for `null` entries.
- Risk: The partial unique index predicate (`is_deleted = false` only) means a disabled-and-not-deleted row plus a separate insert attempt could theoretically race under concurrent create calls — now with more surface area since one multi-shop request touches several rows across several shops in one transaction.
  Mitigation: Same class of race already accepted elsewhere in this codebase; the partial unique index is the backstop that turns a race into an `IntegrityError` (and, per this plan's atomicity design, an `IntegrityError` on any one row rolls back the *entire* batch, which is actually a stronger safety property here than in the single-shop version).
- Risk: A search with few or no matches may require reading every page of product metafield definitions from Shopify — now multiplied by the number of requested shops, since each shop's search runs its own independent pagination loop.
  Mitigation: Page size 100, per-shop stop at `SEARCH_RESULTS_LIMIT`, frontend expected to debounce. No persistent definition mirroring in this phase. A short-lived per-shop operational cache is a possible later optimization if observed multi-shop search traffic/latency requires it — not built speculatively now.

## Validation plan

- `alembic upgrade head` locally after generating the migration: table + all indexes + partial unique constraint created without errors; `alembic downgrade -1` cleanly reverses it.
- `pytest backend/app/tests/integration/models/shopify/test_shopify_metafield_preference_constraints.py` — model/constraint coverage, including the two-shops-same-GID independence proof.
- `pytest backend/app/tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py` — Implementation plan step 10, "Multi-shop create," items 1–10.
- `pytest backend/app/tests/integration/services/queries/shopify/test_get_shopify_metafield_preferences.py` — step 10, "Multi-shop category query" (11–20) and "Multi-shop search" (21–27).
- `pytest backend/app/tests/unit/test_shopify_router.py` — step 10, "Router," items 28–33.
- `pytest backend/app/tests/unit/services/infra/shopify/test_metafield_definition_client.py` — single-shop client-level coverage per the expanded list in Implementation plan step 10 (null node, wrong `ownerType`, pagination stop conditions, no `query:` DSL argument sent, `ownerType` variable equals the shared constant).
- **Schema-contract verification (dev-store only, not part of CI's default run):** run the `MetafieldOwnerTypeValues` introspection query (step 10) against a configured development Shopify store and confirm `PRODUCT` appears in the returned `enumValues`. This closes the loop the mocked test suite structurally cannot: mocks are written using the same `SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE` constant the production code uses, so they'd stay green even if that constant's value were wrong — only a real round-trip to Shopify's schema proves the value itself is correct. Run this once during implementation (and again only if Shopify's schema is suspected to have changed), not on every CI run and never on a production request path.
- Manual/exploratory (no frontend exists yet, backend-only): hit both routes with `httpx`/`curl` against two real or sandbox Shopify dev stores linked to the same test workspace, confirming (a) a definition GID from store 1 is correctly rejected when submitted against store 2's `shop_integration_id`, and (b) the `GET /metafield-preferences?shop_integration_ids=...` response groups results under the correct `shops[]` entries with correct `shop_domain` metadata. This is the one thing mocked-Shopify unit/integration tests cannot fully substitute for — real cross-shop GID behavior.

## Review log

- `2026-07-13` `claude`: Initial plan drafted from intention doc + direct codebase research (single-shop create/query, single-node and batched-nodes Shopify lookups).
- `2026-07-13` `claude`: Decoupled `item_category_ids` from being required in the query and added an optional `q` name-search flow against Shopify's live `metafieldDefinitions`, combinable with the category flow.
- `2026-07-13` `claude`: **Correction** — removed an incorrect assumption that Shopify supports a `name:*term*` search-DSL expression on `metafieldDefinitions(query:)`. Replaced it with a paginated `ListProductMetafieldDefinitions($first, $after)` query and local Python case-insensitive substring matching against `name`, stopping at `SEARCH_RESULTS_LIMIT` matches or when Shopify's pages are exhausted.
- `2026-07-13` `claude`: **Multi-shop correction**, per user requirements — reworked both the create command and the query to operate over one-or-more Shopify shop integrations per request instead of exactly one. Create: renamed `create_shopify_metafield_preference` → `create_shopify_metafield_preferences`, new batch request shape (`item_category_id` + `preferences[]`, each carrying its own `shop_integration_id`/`shopify_metafield_definition_id`/`sequence_order`), every definition validated against its own shop's credentials, whole-request atomicity via the existing `maybe_begin` transaction (validate-everything-before-writing-anything). Query: replaced the `GET /shops/{shop_integration_id}/metafield-preferences` path-parameter route with `GET /metafield-preferences` plus a required `shop_integration_ids` query parameter; category and search flows now run independently per requested shop, never mixing definition IDs/domains/tokens across shops; response restructured to a top-level `shops[]` array, each entry self-contained with its own `shop_domain` (descriptive only), `item_categories`, `unavailable_definition_ids`, and `search_results`. Added `normalize_shop_integration_ids`. Confirmed the model needs no structural change (already shop-scoped) and the infra client functions stay single-shop-per-call by design, with orchestration living entirely in the service layer. Added the new resolved clarification (shop selection by `client_id`, never raw domain) and a new risk (cross-shop GID reuse). Rewrote the test list, acceptance criteria, and validation plan around the multi-shop shape.
- `2026-07-13` `claude`: **Resolved the `MetafieldOwnerType.PRODUCT` clarification**, per user confirmation against Shopify's Admin GraphQL schema — `PRODUCT` is correct and no longer treated as unverified. Introduced one shared constant, `SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE = "PRODUCT"`, in `services/infra/shopify/metafield_definition_client.py` (step 5), replacing every previously-scattered raw `"PRODUCT"` string comparison in the command (step 7) and query (step 8). The listing query used by the search flow (`ListProductMetafieldDefinitions`) now passes `ownerType` as a typed `$ownerType: MetafieldOwnerType!` GraphQL variable instead of an embedded literal, so Shopify's schema validates it directly; the single-node and batched-nodes queries continue requesting `ownerType` in their response selection sets and rely on the caller comparing against the shared constant, since `node(id:)`/`nodes(ids:)` take no owner-type argument. Added a schema-contract introspection check (`MetafieldOwnerTypeValues` query against `__type(name: "MetafieldOwnerType")`) to Implementation plan step 10 and the Validation plan, explicitly scoped as a dev-store/CI-optional check that never runs on a production request path and is not something the mocked unit test suite can substitute for. Removed all remaining language suggesting the enum spelling was unverified or implementation-blocking.
- `2026-07-13` `codex`: Implemented the multi-shop model, migration, domain helpers/results/serializers, single-shop Shopify metafield-definition client, atomic batch create command, grouped multi-shop query/search service, routes, frontend handoff documentation, and focused unit coverage. Validation evidence: 88 focused unit tests passed, Ruff and compile checks passed, and Alembic reports revision `b4c5d6e7f8a9` as the head. Live PostgreSQL migration/application checks remain unverified because the local database connection was unavailable in this environment.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
