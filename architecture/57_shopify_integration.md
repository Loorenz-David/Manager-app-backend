# 57 — Shopify Integration

## What this document covers

The Shopify integration links Shopify shops to ManagerBeyo workspaces, keeps webhook subscriptions in sync, receives and processes Shopify webhooks asynchronously, and exposes admin routes for managing linked shops. This document describes how the layer is **actually implemented** — file structure, data model, the three core flows (OAuth link, webhook intake, webhook subscription sync), the dedicated worker/queue, and — most importantly — **where and how to extend it** as more Shopify functionality (new webhook topics, real business processing, new admin actions) gets added.

Built across the master plan's 7 phases: `docs/architecture/archives/implementation/PLAN_shopify_integration_master_20260707.md` and its child plans. If you are about to add Shopify functionality, read this document first — do not re-derive the pattern from scratch or copy a different domain's shape.

---

## Architecture overview

```
Frontend / Admin UI
        │  JWT (admin/manager)
        ▼
routers/api_v1/shopify.py            (prefix /api/v1/integrations/shopify)
        │  install-url, shops, reauthorize-url, disconnect,
        │  webhooks/sync, webhooks/history, scopes, oauth/callback
        ▼
services/commands/shopify/*  +  services/queries/shopify/*
        │  writes                        reads
        ▼
Postgres  (shopify_shop_integrations, shopify_oauth_states,
           shopify_webhook_subscriptions, shopify_webhook_intakes,
           shopify_integration_events)

Shopify (external)
        │  OAuth redirect
        ▼
GET /api/v1/integrations/shopify/oauth/callback   (HMAC/state verified, no JWT)

        │  webhook delivery
        ▼
POST /api/v1/shopify/webhooks                     (HMAC verified, no JWT)
        │  routers/api_v1/shopify_webhooks.py
        ▼
enqueue_or_record_shopify_webhook                 (verify → dedupe → persist → enqueue)
        │
        ▼
ExecutionTask (queue:shopify)  ──────────────────────────┐
        │                                                 │
        ▼                                                 ▼
services/infra/execution/task_router.py           workers/shopify_worker.py
  (routes by QUEUE_MAP to queue:shopify)             (run_worker + HANDLER_MAP)
                                                          │
                                                          ▼
                                          services/tasks/shopify/handle_*.py
                                                          │
                                                          ▼
                                          services/commands/shopify/*  (same
                                          commands the admin routes call, e.g.
                                          sync_shopify_webhook_subscriptions_for_shop)
```

Everything Shopify-related routes through the **existing** execution/worker/queue layer (contracts [16_background_jobs.md](16_background_jobs.md), [51_worker_runtime.md](51_worker_runtime.md), [12_infra_redis.md](12_infra_redis.md)) — there is no Shopify-specific queue mechanism, no separate retry system, and no separate task table.

---

## File structure

```
beyo_manager/
├── domain/
│   ├── shopify/
│   │   ├── enums.py            # ShopifyIntegrationStatusEnum, ShopifyOAuthStateStatusEnum,
│   │   │                       # ShopifyWebhookSubscriptionStatusEnum, ShopifyWebhookIntakeStatusEnum,
│   │   │                       # ShopifyIntegrationEventTypeEnum, ShopifyIntegrationEventSeverityEnum,
│   │   │                       # ShopifyWebhookPayloadFormatEnum
│   │   ├── webhook_registry.py # SHOPIFY_WEBHOOK_REGISTRY — the single source of truth for which
│   │   │                       # webhook topics exist — see "Adding a new webhook topic" below
│   │   ├── scopes.py           # parse_scope_config, compare_requested_and_granted_scopes,
│   │   │                       # has_all_required_scopes
│   │   ├── shop_domains.py     # normalize_shop_domain
│   │   ├── results.py          # frozen dataclasses returned by queries (never ORM rows)
│   │   └── serializers.py      # ORM row → result dataclass, incl. _filter_safe_metadata
│   └── execution/
│       └── payloads/
│           └── shopify.py      # frozen dataclasses for the 4 Shopify ExecutionTask payloads
├── models/tables/shopify/
│   ├── shopify_shop_integration.py     # shpint_ — one row per linked shop
│   ├── shopify_oauth_state.py          # shpoau_ — short-lived OAuth handshake state
│   ├── shopify_webhook_subscription.py # shpwhs_ — desired-vs-installed webhook topic per shop
│   ├── shopify_webhook_intake.py       # shpwhi_ — one row per received webhook delivery
│   └── shopify_integration_event.py    # shpevt_ — audit/activity trail (install, sync, disconnect, ...)
├── services/
│   ├── commands/shopify/
│   │   ├── create_shopify_install_url.py
│   │   ├── create_shopify_reauthorize_url.py
│   │   ├── handle_shopify_oauth_callback.py
│   │   ├── disconnect_shopify_shop.py
│   │   ├── enqueue_shopify_webhook_sync_for_shop.py
│   │   ├── enqueue_shopify_webhook_sync_for_workspace.py
│   │   ├── enqueue_or_record_shopify_webhook.py     # inbound webhook verify/dedupe/persist/enqueue
│   │   ├── sync_shopify_webhook_subscriptions_for_shop.py  # registry reconciliation (see below)
│   │   ├── _events.py          # create_shopify_integration_event — every command uses this
│   │   ├── _redirect.py        # build_shopify_oauth_redirect_url, validate_redirect_after_success_key
│   │   ├── _linking.py         # link_or_update_shopify_shop_record
│   │   ├── _webhook_sync.py    # record_webhook_sync_pending (post-OAuth boundary)
│   │   └── _callback_errors.py # ShopifyOAuthCallbackError
│   ├── queries/shopify/
│   │   ├── list_shopify_shop_integrations.py
│   │   ├── get_shopify_shop_integration.py
│   │   ├── get_shopify_scope_status.py
│   │   └── get_shopify_webhook_history_records.py
│   ├── tasks/shopify/           # worker-side handlers — (raw_payload: dict, task_client_id: str) -> None
│   │   ├── handle_shopify_process_webhook.py
│   │   ├── handle_shopify_sync_webhooks_for_shop.py
│   │   └── handle_shopify_remove_webhooks_for_shop.py
│   └── infra/shopify/
│       ├── oauth_client.py               # build_shopify_install_url, exchange_oauth_code_for_offline_token
│       ├── hmac_verifier.py               # is_valid_shopify_oauth_callback_hmac, is_valid_shopify_webhook_hmac
│       └── webhook_subscription_client.py # create/list/delete remote webhook subscriptions (GraphQL)
├── workers/
│   └── shopify_worker.py        # HANDLER_MAP + run_worker("queue:shopify", HANDLER_MAP)
└── routers/api_v1/
    ├── shopify.py                # admin routes, prefix /api/v1/integrations/shopify
    └── shopify_webhooks.py       # inbound webhook route, prefix /api/v1/shopify
```

For the full request/response contract of every route, see `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md`. This document explains the *architecture*; that one explains the *API surface*.

---

## Data model

| Table | Prefix | Purpose | Key constraint |
|---|---|---|---|
| `shopify_shop_integrations` | `shpint_` | One row per linked shop | Partial unique index on `shop_domain` where `is_deleted=false AND status IN (pending_install, active, needs_reauth, scopes_outdated, webhooks_outdated, error)` — **one active integration per normalized shop domain, globally, across all workspaces.** Disabled/uninstalled rows don't count, so a shop can be re-linked after disconnect. |
| `shopify_oauth_states` | `shpoau_` | Short-lived (10 min TTL) OAuth handshake state, one-time use | `state` is a `secrets.token_urlsafe(32)` value; consumed exactly once via `SELECT ... FOR UPDATE` in the callback |
| `shopify_webhook_subscriptions` | `shpwhs_` | Desired-vs-installed state per `(shop_integration_id, topic)` | One row per topic per shop; `status` reflects the last reconciliation outcome |
| `shopify_webhook_intakes` | `shpwhi_` | One row per received webhook delivery | `dedupe_key = f"{shop_integration_id}:{topic}:{webhook_id}"`, unique — deliveries are deduped via `INSERT ... ON CONFLICT DO NOTHING` |
| `shopify_integration_events` | `shpevt_` | Append-only audit/activity trail | Every command writes one via `create_shopify_integration_event` — this is the backbone of Route 7's history feed |

`ShopifyShopIntegration.access_token_encrypted` is the only secret at rest — encrypted via `FIELD_ENCRYPTION_KEY` (contract [18_security.md](18_security.md)). Nothing else in the schema is sensitive by design; `shopify_webhook_intakes.raw_payload` is JSONB and **is** sensitive-adjacent (may contain customer/order data) — it is stored but never serialized back out (see "No-secret serialization" below).

---

## Flow 1 — OAuth install/link

```
1. Frontend: POST /install-url { shop_domain }
   → create_shopify_install_url: normalizes shop_domain, creates a ShopifyOAuthState
     (status=PENDING, expires_at=now+10min, random `state`), returns Shopify's
     authorize URL (services/infra/shopify/oauth_client.py:build_shopify_install_url)

2. Browser redirects to Shopify's consent screen, merchant approves.

3. Shopify redirects to GET /api/v1/integrations/shopify/oauth/callback?shop=...&state=...&hmac=...&code=...
   → handle_shopify_oauth_callback:
     a. Verifies HMAC over the raw query string (hmac_verifier.is_valid_shopify_oauth_callback_hmac)
     b. Loads the ShopifyOAuthState by `state` with SELECT ... FOR UPDATE
     c. Validates: shop matches, status==PENDING, not expired, no `error` param, `code` present
     d. Exchanges the code for an offline access token (oauth_client.exchange_oauth_code_for_offline_token)
     e. link_or_update_shopify_shop_record: creates or updates the ShopifyShopIntegration row
        (this is what makes multi-shop-per-workspace and re-link-after-disconnect work — it is
        NOT a plain insert)
     f. record_webhook_sync_pending: enqueues SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP so subscriptions
        get installed immediately after a successful link — the caller never has to call
        Route 6/8 manually right after install
     g. Marks the OAuth state CONSUMED
   → Always responds 302, never JSON — redirects to SHOPIFY_OAUTH_REDIRECT_URL (a ManagerBeyo
     FRONTEND url, distinct from SHOPIFY_REDIRECT_URI which is the Shopify-facing callback URL
     itself) with `?success=&shop_domain=&error_code=`
```

**Every failure path in step 3 raises `ShopifyOAuthCallbackError`** (`error_code` one of `invalid_signature`, `invalid_state`, `state_shop_mismatch`, `state_already_consumed`, `state_expired`, `access_denied`, `missing_code`, `token_exchange_failed`) and the router still redirects (never returns raw JSON to the merchant's browser) — see `routers/api_v1/shopify.py:shopify_oauth_callback_route`.

---

## Flow 2 — Inbound webhook intake + async processing

```
1. Shopify: POST /api/v1/shopify/webhooks
   Headers: X-Shopify-Hmac-Sha256, X-Shopify-Topic, X-Shopify-Shop-Domain, X-Shopify-Webhook-Id

2. enqueue_or_record_shopify_webhook (services/commands/shopify/enqueue_or_record_shopify_webhook.py):
   a. Verify HMAC over the raw body (hmac_verifier.is_valid_shopify_webhook_hmac) — reject before
      any DB write if invalid
   b. Require X-Shopify-Webhook-Id
   c. Normalize shop_domain, look up the ShopifyShopIntegration — if none exists, respond
      {"outcome": "unknown_shop"} and do nothing else (still HTTP 200 — never make Shopify retry
      for a shop we don't recognize)
   d. Dedupe on dedupe_key via INSERT ... ON CONFLICT DO NOTHING — if the row already existed,
      respond {"outcome": "duplicate"}
   e. If the integration is DISABLED/UNINSTALLED, or the topic has no entry in
      SHOPIFY_WEBHOOK_REGISTRY, mark the intake IGNORED (retryable=False) and stop — no task
      is enqueued for ignored intakes
   f. Otherwise mark RECEIVED, write a WEBHOOK_RECEIVED integration event, and enqueue
      SHOPIFY_PROCESS_WEBHOOK with payload {webhook_intake_id}
   g. Always returns quickly — no Shopify API calls happen inline on this path (contract
      19_integrations.md's webhook-receipt contract: verify, persist/dedupe, enqueue, return fast)

3. Worker (workers/shopify_worker.py, queue:shopify) picks up SHOPIFY_PROCESS_WEBHOOK
   → handle_shopify_process_webhook (services/tasks/shopify/handle_shopify_process_webhook.py):
     Loads the intake row FOR UPDATE, skips if already PROCESSING/PROCESSED/FAILED/IGNORED
     (idempotent on duplicate task delivery), marks PROCESSING → PROCESSED, writes a
     WEBHOOK_PROCESSED integration event.
```

**Load-bearing gap to know about before adding real functionality:** `handle_shopify_process_webhook` currently does **no topic-specific business logic**. It marks every received webhook `PROCESSED` unconditionally and logs `"processing_mode": "no_business_processor_yet"`. There is no `orders/create` handler that creates a ManagerBeyo order, no `products/update` handler that syncs inventory — none of that exists yet. This is intentional (the master plan's phase decomposition scoped "receive and route" separately from "act on the payload"), but it means **this is the primary place you will extend** when adding real Shopify-driven functionality. See "Adding real business processing for a webhook topic" below.

---

## Flow 3 — Webhook subscription sync (registry reconciliation)

`sync_shopify_webhook_subscriptions_for_shop` (`services/commands/shopify/sync_shopify_webhook_subscriptions_for_shop.py`) is the one function that talks to Shopify's GraphQL API to create/remove webhook subscriptions. It runs identically whether triggered by:
- the post-OAuth automatic enqueue (Flow 1 step 3f),
- an admin manually hitting Route 6/8,
- or the worker executing a `SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP` / `SHOPIFY_RECONCILE_SHOP` task (both task types map to the same handler — see `workers/shopify_worker.py`'s `HANDLER_MAP`).

It is a **full reconciliation loop**, not an incremental diff: for every `ShopifyWebhookDefinition` in `SHOPIFY_WEBHOOK_REGISTRY`, it compares the registry's desired state against what's actually installed on Shopify's side (queried live via `list_remote_webhook_subscriptions`, matched by `callback_url`, not cached) and against the local `shopify_webhook_subscriptions` mirror table, then:

| Registry state | Remote state | Local scopes | Action |
|---|---|---|---|
| `enabled=True` | not installed | has required scopes | Create remote subscription → local row `ACTIVE` |
| `enabled=True` | already installed | has required scopes | Verify only → local row `ACTIVE` |
| `enabled=True` | any | **missing** required scopes | Skip Shopify call → local row `FAILED`, `last_error_code="missing_required_scope"` |
| `enabled=False` | installed | — | Delete remote subscription → local row `REMOVED` |
| topic removed from registry entirely | installed | — | Delete remote subscription → local row `REMOVED` (this is how you retire a topic — see below) |

A `ShopifyGraphQLError` from any single topic's create/delete call is caught per-topic (`failed_topics`) — one topic failing does not abort the sync for the others. One `WEBHOOK_SYNC` integration event is written at the end summarizing `created_topics`/`removed_topics`/`verified_topics`/`missing_scope_topics`/`failed_topics`.

---

## Product-sync inventory increments

Product sync accepts optional, shop-tagged positive inventory adjustments. The command normalizes them into one payload per target shop, and the Shopify worker applies product/variant changes before inventory changes and metafields. Inventory changes use Shopify's additive `inventoryAdjustQuantities` operation and never set or decrement stock.

The `shopify_inventory_adjustments` ledger is the durable idempotency boundary. Its unique key is `(shop_integration_id, frontend_client_id, shopify_location_id)`; applied rows are skipped on resubmission, while pending rows use a baseline re-query before an adjustment is retried. Per-location outcomes are stored on `shopify_product_sync_items.inventory_result_json`, and an inventory failure leaves the sync item `FAILED` with an inventory-specific error code.

The locations query is workspace-scoped and reads live Shopify locations, including inactive locations. Inventory execution validates location ownership again at worker time. `read_locations` and `write_inventory` are required for inventory-enabled syncs; product-only syncs remain unaffected when those scopes are missing.

## Worker & queue wiring

- Queue: `queue:shopify` — dedicated, shared by all four Shopify task types (`services/infra/execution/task_router.py`'s `QUEUE_MAP`). Do not add a Shopify task type to any other queue, and do not route a non-Shopify task type onto `queue:shopify`.
- Task types (`domain/execution/enums.py`): `SHOPIFY_PROCESS_WEBHOOK`, `SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP`, `SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP`, `SHOPIFY_RECONCILE_SHOP`.
- Payloads (`domain/execution/payloads/shopify.py`): each is a frozen dataclass with exactly the IDs the handler needs to re-load state from Postgres — never denormalized business data. `ShopifyProcessWebhookPayload(webhook_intake_id)`, `ShopifySyncWebhooksForShopPayload(shop_integration_id)`, `ShopifyRemoveWebhooksForShopPayload(shop_integration_id)`, `ShopifyReconcileShopPayload(shop_integration_id)`.
- Worker: one dedicated process, `python -m beyo_manager.workers.shopify_worker` (`make shopify-worker` locally; `managerbeyo-shopify-worker` systemd unit in production — see [33_deployment.md](33_deployment.md) and the archived `PLAN_shopify_deployment_validation_20260709.md` for the exact unit file). `HANDLER_MAP` in `workers/shopify_worker.py` maps task type → async handler function `(raw: dict, task_client_id: str) -> None`. `SHOPIFY_RECONCILE_SHOP` currently points at the same handler function as `SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP` (both do a full reconciliation — `RECONCILE_SHOP` exists as a distinct task type for a future periodic/scheduled reconciliation job, not yet wired to a scheduler).
- Enqueueing always goes through `create_instant_task(session, task_type, payload, event_client_id=...)` (`services/infra/execution/task_factory.py`) — never construct an `ExecutionTask` row directly. `event_client_id` links the task back to the `ShopifyIntegrationEvent` that triggered it, which is how Route 7's history feed can show "this sync produced this task."

---

## Security model

- **OAuth callback HMAC**: verified over the raw query string using `SHOPIFY_CLIENT_SECRET`, before any DB read (`hmac_verifier.is_valid_shopify_oauth_callback_hmac`).
- **Webhook HMAC**: verified over the raw request body using `SHOPIFY_WEBHOOK_SECRET` (falls back to `SHOPIFY_CLIENT_SECRET` if unset), before any DB read (`hmac_verifier.is_valid_shopify_webhook_hmac`). Both HMAC checks use `hmac.compare_digest` — never `==`.
- **Access tokens**: encrypted at rest via `FIELD_ENCRYPTION_KEY` (`access_token_encrypted` column). Never serialized in any query/route response — no `ShopifyShopIntegrationResult` field exposes it.
- **OAuth state**: one-time use, 10-minute TTL, workspace/user-bound, consumed via `SELECT ... FOR UPDATE` to prevent a double-submit race.
- **No-secret serialization**: `domain/shopify/serializers.py:_filter_safe_metadata` strips any `ShopifyIntegrationEvent.metadata_json` key whose name contains `token`, `secret`, `hmac`, `signature`, `authorization`, `code`, `raw_payload`, `payload`, `raw_response`, or `provider_response` (case-insensitive) before Route 7 serializes it. **When you add a new command that writes `metadata_json`, do not rely on this filter as your only safeguard — do not put a raw token/secret/payload into `metadata_json` in the first place.** The filter is a defense-in-depth backstop, not a license to be careless upstream.
- **Multi-tenancy**: every admin query/command filters or checks `workspace_id` (contract [24_multi_tenancy.md](24_multi_tenancy.md)). Three commands (`disconnect_shopify_shop`, `create_shopify_reauthorize_url`, `enqueue_shopify_webhook_sync_for_shop`) use `ctx.session.get()` + a manual `integration.workspace_id != ctx.workspace_id` check rather than filtering in the `WHERE` clause the way the query files do — functionally equivalent (both reject cross-workspace access as `NotFound`), but if you add a new single-shop command, prefer the query files' `WHERE workspace_id=...` style for consistency.

---

## How to scale this integration

### Adding a new webhook topic

1. Add a `ShopifyWebhookDefinition` to `SHOPIFY_WEBHOOK_REGISTRY` in `domain/shopify/webhook_registry.py` — `topic` (Shopify's topic string, e.g. `"customers/create"`), `callback_path` (always `SHOPIFY_WEBHOOK_CALLBACK_PATH`, do not invent a per-topic path — there is only one inbound route), `required_scopes` (a tuple; `sync_shopify_webhook_subscriptions_for_shop` will mark the subscription `FAILED` with `missing_required_scope` for any shop that hasn't granted these), `payload_format` (`ShopifyWebhookPayloadFormatEnum.JSON` — the only value that currently exists), `enabled=True`.
2. If the new topic needs a scope not already in `SHOPIFY_APP_SCOPES`, update that env var and the Shopify Partner Dashboard app configuration (contract [33_deployment.md](33_deployment.md) / the deployment runbook) — shops that installed before the scope was added will need to go through Route 4 (reauthorize) before the subscription can be created.
3. That's it for making Shopify *send* the webhook — `sync_shopify_webhook_subscriptions_for_shop` picks up new registry entries automatically on the next sync (post-OAuth, manual, or scheduled) for every shop with the required scopes. No new admin route, no new migration.
4. To actually *do something* with the incoming payload, see the next section — adding a registry entry alone only gets you as far as `handle_shopify_process_webhook` marking it `PROCESSED` with no business effect.

### Retiring a webhook topic

Remove its `ShopifyWebhookDefinition` from `SHOPIFY_WEBHOOK_REGISTRY` entirely (don't just set `enabled=False` unless you want to keep it installed-but-paused — see the reconciliation table above for the difference). The next sync will delete the remote subscription and mark the local row `REMOVED` for every shop, via the "topic removed from registry entirely" branch in `sync_shopify_webhook_subscriptions_for_shop`.

### Adding real business processing for a webhook topic

This is the main extension point. `handle_shopify_process_webhook` currently has one unconditional code path. To add topic-specific behavior:

1. In `handle_shopify_process_webhook.py`, after loading the `intake` row (which has `.topic` and `.raw_payload` already persisted — no need to re-fetch from Shopify), branch on `intake.topic` and delegate to a new per-topic processor, e.g. `services/tasks/shopify/processors/process_orders_create.py`. Keep the row-locking (`SELECT ... FOR UPDATE`), the `_NON_PROCESSABLE_STATUSES` skip-if-already-handled check, and the `PROCESSING` → terminal-status transition exactly as they are — that idempotency guarantee is what makes duplicate task delivery and Shopify's own webhook retries safe. Only the body between "mark PROCESSING" and "mark PROCESSED" should change per topic.
2. A processor receives `intake.raw_payload` (already-parsed JSON, already dedupe-verified, already HMAC-verified — do not re-verify anything) and `intake.shop_integration_id`/`shop_domain` to resolve which workspace/shop this belongs to.
3. On a processor failure, set `intake.status = ShopifyWebhookIntakeStatusEnum.FAILED`, populate `intake.last_error`, and decide retryability: `intake.retryable` was already set `True` by the intake command for any registered topic — if the failure is transient (e.g. a downstream write conflict), leave a `FAILED` status for the existing execution-layer retry mechanism (contract [51_worker_runtime.md](51_worker_runtime.md)) to re-attempt via the task's own retry policy, not by re-queuing a second `SHOPIFY_PROCESS_WEBHOOK` task yourself.
4. Write a domain-specific integration event via `create_shopify_integration_event` if the outcome is worth surfacing in Route 7's history feed — but note `get_shopify_webhook_history_records`'s `WEBHOOK_HISTORY_EVENT_TYPES` allow-list currently only includes `WEBHOOK_SYNC`, `WEBHOOK_RECEIVED`, `WEBHOOK_PROCESSED`, `DISCONNECT`. A new business-outcome event type (e.g. "order imported") needs its own `ShopifyIntegrationEventTypeEnum` value (see below) added to that allow-list if it should appear in the same feed, or it can be queried separately if it belongs to a different UI surface (e.g. an orders list, not an integration activity log).
5. Business processors that create/update other ManagerBeyo domain rows (orders, products, etc.) should call **that domain's own commands**, not write to its tables directly from `services/tasks/shopify/` — the Shopify layer should stay a thin adapter that translates Shopify payloads into calls against the existing domain command layer, mirroring how `sync_shopify_webhook_subscriptions_for_shop` treats Shopify as external infra and never reaches into unrelated tables.

### Adding a new Shopify task type

1. Add the value to `TaskType` in `domain/execution/enums.py` (follow the `SHOPIFY_` prefix convention already used).
2. Add a payload dataclass to `domain/execution/payloads/shopify.py` — IDs only, no denormalized data (see "Worker & queue wiring" above).
3. Add `TaskType.SHOPIFY_<NAME>: "queue:shopify"` to `QUEUE_MAP` in `services/infra/execution/task_router.py`.
4. Write the handler in `services/tasks/shopify/handle_shopify_<name>.py` — signature `async def handle(raw: dict, task_client_id: str) -> None`, load the payload dataclass from `raw`, open a session via `get_db_session()`, do the work inside `session.begin()`.
5. Register it in `HANDLER_MAP` in `workers/shopify_worker.py`.
6. Enqueue it from whichever command/handler triggers it via `create_instant_task(session, TaskType.SHOPIFY_<NAME>, payload=asdict(...), event_client_id=...)`.
7. No new migration is needed purely for a new task type — `task_type_enum` values are added via an additive `ALTER TYPE ... ADD VALUE IF NOT EXISTS` migration (see `migrations/versions/c3f7a9d2e4b1_add_shopify_execution_task_types.py` for the exact pattern to copy).

### Adding a new admin route (query or command)

Follow the existing split exactly — do not introduce a new pattern:
- **Query** (`services/queries/shopify/`): read-only, takes `ctx.incoming_data`/`ctx.query_params`, returns a `dict` built from `asdict(serialize_...(row))`. Always filter by `ctx.workspace_id` in the `WHERE` clause.
- **Command** (`services/commands/shopify/`): a write. If it touches Shopify's API, delegate to `services/infra/shopify/` (never call `httpx`/GraphQL directly from a command). If it should show up in Route 7's history, call `create_shopify_integration_event`. If it should trigger async work, call `create_instant_task`, not an inline Shopify API call.
- Add a result dataclass to `domain/shopify/results.py` and a serializer function to `domain/shopify/serializers.py` if the response includes a new shape — reuse `ShopifyShopIntegrationResult`/`ShopifyWebhookSubscriptionResult`/etc. where the shape already matches; don't create a near-duplicate dataclass.
- Wire the route in `routers/api_v1/shopify.py` (admin-facing, JWT-protected — mount under the existing router, do not create a new `APIRouter()`), following the existing `run_service` + `build_ok`/`build_err` pattern. Pick the role gate (`admin`+`manager` vs. `admin`-only) by matching the closest existing route's risk level — anything that mutates external Shopify state or disables an integration is `admin`-only; read-only and "start an OAuth flow" routes are `admin`+`manager`.
- Update `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` with the new route's contract — that document is the frontend team's only source of truth for this API surface; don't let it drift.

### Adding a new integration event type

Add the value to `ShopifyIntegrationEventTypeEnum` in `domain/shopify/enums.py`, then an additive migration (`ALTER TYPE shopify_integration_event_type_enum ADD VALUE IF NOT EXISTS '...'` — see `migrations/versions/ab12cd34ef56_add_disconnect_to_shopify_integration_event_type.py` for the exact pattern). If the new event type should appear in Route 7's webhook-history feed, add it to `WEBHOOK_HISTORY_EVENT_TYPES` in `services/queries/shopify/get_shopify_webhook_history_records.py` — it is an explicit allow-list, not "every event type by default," by design (keeps that feed's contents matching its name; OAuth-lifecycle events like `INSTALL`/`REAUTHORIZE` are deliberately excluded).

### Supporting multiple shops per workspace / multiple workspaces — already built in, no work needed

The schema and every query/command already assume this:
- `shopify_shop_integrations` has no unique constraint on `workspace_id` alone — a workspace can have arbitrarily many shop rows.
- The only uniqueness constraint is on `shop_domain` globally (see "Data model" above) — a given Shopify store can only be actively linked to one workspace at a time, which is a deliberate anti-double-processing safeguard, not an oversight.
- `enqueue_shopify_webhook_sync_for_workspace` (Route 8) and `get_shopify_scope_status` (Route 9, no `shop_integration_id`) already fan out across every shop in a workspace — use these as the template for any new "do X for every shop" command/query rather than writing a new loop pattern.

### Public/installable Shopify app (currently single-app/custom install model)

Shopify app credentials (`SHOPIFY_CLIENT_ID`/`SHOPIFY_CLIENT_SECRET`) come from environment config, not from a database row — this was a deliberate phase-1 decision so that moving from "one custom app for one shop" to "one public app installable by many merchants" requires no schema change, only an env/config change plus (eventually) Shopify's public-app review process. Nothing in the command/query/worker layer assumes a single app identity — `ShopifyShopIntegration.provider` already exists as a string column specifically so a second provider (or a second Shopify app identity) could be distinguished later without a migration, though nothing currently branches on it.

---

## Rules

- **`SHOPIFY_WEBHOOK_REGISTRY` is the single source of truth for webhook topics.** Never hardcode a topic string outside the registry (`domain/shopify/webhook_registry.py`) — the sync command, the intake command's "unsupported topic" check, and the subscription client all key off it.
- **Never call Shopify's API inline from an HTTP request handler.** Webhook subscription creation/removal and any future business processing must go through the worker (`queue:shopify`), enqueued via `create_instant_task`. The one exception already in the codebase is the OAuth token exchange itself (`exchange_oauth_code_for_offline_token`), which is inline in the callback because the merchant's browser is synchronously waiting for the redirect — even that call has an explicit timeout via the shared HTTP client config (contract [19_integrations.md](19_integrations.md)).
- **Both HMAC checks happen before any database read.** Do not restructure either command to look up the shop/state before verifying the signature.
- **`handle_shopify_process_webhook`'s row-lock + status-skip pattern must be preserved by any future per-topic processor.** This is what makes duplicate webhook delivery and duplicate task execution both safe. Never remove the `SELECT ... FOR UPDATE` or the `_NON_PROCESSABLE_STATUSES` early-return.
- **`sync_shopify_webhook_subscriptions_for_shop` is a full reconciliation, not an incremental diff.** Do not write a second, separate "install just this one topic" code path — extend the registry and let reconciliation handle it, or you will end up with two sources of truth for subscription state.
- **Task payloads carry IDs only, never denormalized business data.** A handler always re-loads current state from Postgres by ID rather than trusting stale data captured at enqueue time.
- **Every command that changes shop/subscription state writes a `ShopifyIntegrationEvent`.** This is what makes Route 7's history feed meaningful — a new command that silently mutates state without an event is a gap, not a shortcut.
- **`metadata_json` on integration events must not contain secrets even before the serializer's filter runs.** The filter is a backstop; do not depend on it.
- **One active `ShopifyShopIntegration` per normalized `shop_domain`, globally** — enforced at the DB level by a partial unique index, not just application logic. Do not add a code path that bypasses this by writing directly to the table outside `link_or_update_shopify_shop_record`.
- **New Postgres enum values are added via `ALTER TYPE ... ADD VALUE IF NOT EXISTS`, never a destructive enum rebuild.** Copy `migrations/versions/c3f7a9d2e4b1_add_shopify_execution_task_types.py` or `ab12cd34ef56_add_disconnect_to_shopify_integration_event_type.py` as the template (contract [30_migrations.md](30_migrations.md)).
- **`SHOPIFY_REDIRECT_URI` (Shopify-facing OAuth callback) and `SHOPIFY_OAUTH_REDIRECT_URL` (ManagerBeyo frontend post-callback redirect) are different settings — do not conflate them.** Confusing the two breaks OAuth with a confusing Shopify-side redirect-URI-mismatch error.

---

## Related contracts

- [16_background_jobs.md](16_background_jobs.md), [51_worker_runtime.md](51_worker_runtime.md), [12_infra_redis.md](12_infra_redis.md) — the execution/worker/queue layer this integration reuses unmodified.
- [19_integrations.md](19_integrations.md) — external adapter pattern and webhook-receipt contract this integration follows.
- [18_security.md](18_security.md) — HMAC, encryption, and IDOR-prevention rules.
- [24_multi_tenancy.md](24_multi_tenancy.md), [25_soft_delete.md](25_soft_delete.md) — workspace scoping and soft-delete conventions this integration's tables follow (`is_deleted` on `shopify_shop_integrations`, no hard deletes on disconnect).
- [30_migrations.md](30_migrations.md) — additive-migration idiom used for every Shopify enum change.
- [33_deployment.md](33_deployment.md) — env var checklist, systemd worker registration, deployment runbook (see also the archived `PLAN_shopify_deployment_validation_20260709.md` for the fully verified operational checklist).
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` — the API contract for every route this document's architecture backs.
