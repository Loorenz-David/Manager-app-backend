# PLAN_shopify_webhook_history_records_20260709

## Metadata

- Plan ID: `PLAN_shopify_webhook_history_records_20260709`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-09T14:00:00Z`
- Last updated at (UTC): `2026-07-08T10:25:30Z`
- Related issue/ticket: `Shopify integration webhook history records (phase 6.1)`
- Intention plan: `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`
- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_integration_master_20260707.md`
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_foundation_schema_config_20260707.md` — phase 1 foundation (`ShopifyWebhookIntake`, `ShopifyIntegrationEvent`, `ShopifyShopIntegration` models).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_oauth_linking_20260707.md` — phase 2 (`routers/api_v1/shopify.py`, role policy precedent).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_registry_sync_20260707.md` — phase 3 (webhook subscription sync/remove; not a direct data source for this plan, referenced for context only).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_intake_execution_20260708.md` — phase 4 (`ShopifyWebhookIntake` rows this plan's query reads: `topic`, `webhook_id`, `status`, `retryable`, `attempts`, `received_at`, `processing_started_at`, `processed_at`, `last_error`, `created_at`, `updated_at`).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_worker_execution_20260708.md` — phase 5 (`SHOPIFY_PROCESS_WEBHOOK` handler transitions intake rows through `RECEIVED -> PROCESSING -> PROCESSED` and records `WEBHOOK_PROCESSED` events this plan's query surfaces).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_admin_routes_serializers_20260709.md` — phase 6 (`routers/api_v1/shopify.py` admin router this plan extends; `domain/shopify/results.py`/`serializers.py` this plan extends with two new result/serializer pairs; `require_roles([ADMIN, MANAGER])` role-gating precedent this plan reuses verbatim; workspace-scoped-lookup-then-`NotFound` pattern from `get_shopify_shop_integration.py` this plan reuses verbatim; offset-pagination envelope shape from `list_shopify_shop_integrations.py` this plan reuses verbatim). Confirmed implemented and archived — this plan reads the actual code, not the plan text, per "Previous decisions inherited" below.

## Goal and intent

- Goal: Add a workspace-scoped, role-gated `GET` route that returns a paginated, newest-first, merged timeline of a single Shopify shop's webhook history — `ShopifyWebhookIntake` delivery rows and webhook-related `ShopifyIntegrationEvent` audit rows — safe for direct frontend consumption, filling the one missing admin/frontend read surface phase 6 did not build.
- Business/user intent: Let an admin or manager viewing one connected Shopify shop see what actually happened with its webhooks over time (received, ignored, deduped-away, processed, sync-triggered, disconnect-triggered) in one chronological feed, the same way the existing task flow-record view lets a user see a task's history/step timeline in one feed — without exposing any raw webhook payload, token, or secret in the process.
- Non-goals:
  - New Shopify webhook intake, sync, or worker behavior — this plan only reads rows phases 4-6 already write.
  - New task types, queue mappings, or execution-layer changes.
  - Product/order business processing or historical imports.
  - Frontend UI implementation.
  - Deployment/systemd/PM2 changes (master phase 7's concern, not touched or modified by this plan).
  - Any new Shopify API/GraphQL call — this is a pure local-database read.
  - Database schema changes — the existing indexes on both source tables are sufficient for this plan's Python-level merge-and-paginate approach (see "Resolved decisions" item 7); no migration is added.
  - Optional filters (`record_type`, `topic`, `status`, `severity`, `event_type`) — deferred; only `limit`/`offset` are implemented in this phase, per explicit instruction to keep filters minimal until the frontend actually needs them.

## Scope

- In scope:
  - `GET /api/v1/integrations/shopify/shops/{shop_integration_id}/webhooks/history` — one new route on the existing `routers/api_v1/shopify.py` router, at the already-registered `/api/v1/integrations/shopify` prefix.
  - `services/queries/shopify/get_shopify_webhook_history_records.py` — one new query function.
  - Two new frozen result dataclasses in `domain/shopify/results.py`: `ShopifyWebhookIntakeHistoryRecordResult`, `ShopifyIntegrationEventHistoryRecordResult`.
  - Two new serializer functions in `domain/shopify/serializers.py`: `serialize_shopify_webhook_intake_history_record`, `serialize_shopify_integration_event_history_record`, plus one new defensive metadata-filtering helper, `_filter_safe_metadata`.
  - Workspace-scoped shop verification (existing, non-deleted) before any history row is read, reusing the exact `get_shopify_shop_integration.py` pattern.
  - Offset pagination (`limit`/`offset`, default `limit=10`, max `limit=200`) with a `limit + 1` fetch trick per source, Python-level merge across both sources, newest-first sort with a deterministic tie-breaker, then a single combined-page slice — mirroring `task_flow_records.py`'s algorithm shape exactly (not its task-specific entity logic).
  - Role gating: `ADMIN`/`MANAGER` allowed, `WORKER`/`SELLER` rejected — identical to phase 6's `GET /shops`/`GET /shops/{id}` routes.
  - Tests: route role-gating, workspace isolation, soft-deleted-shop `NotFound`, query newest-first ordering, pagination/`has_more` correctness, serializer no-secret/no-raw-payload assertions, intake-record and event-record field-shape assertions, empty-history response shape, and a route-path assertion confirming this route lives under `/api/v1/integrations/shopify`, not `/api/v1/shopify/webhooks`.
- Out of scope:
  - New Shopify webhook intake behavior, worker behavior, task types, or queue mappings.
  - New webhook processing business logic; product/order processing; historical imports.
  - Frontend UI.
  - Deployment/systemd/PM2 changes; phase 7 is not touched or modified.
  - Any Shopify API/GraphQL call.
  - Database schema changes (no migration).
  - Optional query filters beyond `limit`/`offset`.
- Assumptions:
  - Phase 6 is implemented, archived, and reviewed — confirmed by direct inspection of the actual code on `2026-07-09` (`routers/api_v1/shopify.py`, `domain/shopify/results.py`, `domain/shopify/serializers.py`, `services/queries/shopify/get_shopify_shop_integration.py`, `services/queries/shopify/list_shopify_shop_integrations.py` all read directly, not assumed from plan text). No verification checklist is needed for phase 6 in this plan, unlike every prior phase-to-phase transition in this series — phase 6 is already done, and this plan is written against its real code from the start.
  - `task_flow_records.py` is used strictly as an algorithm-shape reference (workspace-scoped parent verification first, `limit`/`offset`/max-limit clamping, Python-level raw-list-build-then-sort-then-slice, `limit + 1` `has_more` trick, response envelope with a `<name>` list key and a `<name>_pagination` object). None of its task/history/step-specific entity logic, imports, or table joins are reused.

## Previous decisions inherited

- **Offset pagination, not cursor pagination** (`07_queries_local.md`, confirmed in phase 6): `limit`/`offset` query params, default/max limits, `limit + 1` fetch trick, `has_more` in a `<name>_pagination` object — this plan's envelope (`webhook_history_records` / `webhook_history_records_pagination`) follows this exactly, matching `shops`/`shops_pagination` from phase 6's `list_shopify_shop_integrations`.
- **Workspace-scoped lookup, then `NotFound`, before any related data is read** (phase 6's `get_shopify_shop_integration.py`): `ShopifyShopIntegration.workspace_id == ctx.workspace_id`, `client_id == shop_integration_id`, `is_deleted.is_(False)`; `NotFound("Shopify shop integration not found.")` on a miss — this plan's query reuses this exact three-condition check verbatim as its first step, before touching either history source table.
- **Role gating is the flat `role_name`/`require_roles([...])` mechanism** (confirmed unused-elsewhere-in-codebase granular permission system, per phase 6's own confirmed finding) — this plan uses `Depends(require_roles([ADMIN, MANAGER]))`, identical to phase 6's `GET /shops` and `GET /shops/{id}` routes, since this is a same-sensitivity read (shop-level detail, not a destructive/sync-triggering action).
- **`domain/shopify/results.py` + `domain/shopify/serializers.py` is the canonical pattern for this domain**, not the emails/tasks dict-only shortcut (phase 6's explicit, documented choice) — this plan extends both existing files rather than introducing a third file or a plain-dict return shape, keeping the Shopify domain internally consistent even though the task-flow-record reference pattern itself uses plain dicts (see "Resolved decisions" item 1).
- **No secret/token/HMAC/raw-payload value ever appears in a Shopify response** (phases 2-6's consistent discipline) — this plan's serializers exclude `raw_payload` entirely by construction (no such field on either result dataclass) and defensively filter `metadata_json` keys, per "Resolved decisions" item 6.

## Clarifications required

None. Every design question below was resolved by direct inspection of phase 6's actual implemented code and the two source table models — no open ambiguity depends on a future decision.

## Resolved decisions

These design questions are resolved by direct inspection of the actual codebase on `2026-07-09` (file:line references reflect that state).

1. **Merged webhook flow records (Option B), not intake-only (Option A).** Both source tables cleanly support a shop-scoped, time-ordered merge: `ShopifyWebhookIntake` has `shop_integration_id` + `received_at` (indexed: `ix_shopify_webhook_intakes_shop_integration_topic`, `ix_shopify_webhook_intakes_received_at`), and `ShopifyIntegrationEvent` has `shop_integration_id` + `created_at` (indexed: `ix_shopify_integration_events_workspace_shop_integration`, `ix_shopify_integration_events_created_at`) — no schema mismatch or missing column blocks a merge. Option B is chosen because it produces a materially richer, more useful timeline than intake rows alone: `ShopifyIntegrationEvent` rows already capture `WEBHOOK_SYNC` (post-OAuth and manual sync triggers), `WEBHOOK_RECEIVED` (every intake outcome, including `IGNORED`/duplicate-adjacent cases that never even reach a `SHOPIFY_PROCESS_WEBHOOK` task), `WEBHOOK_PROCESSED` (phase 5's worker completion), and now `DISCONNECT` (phase 6) — a shop's full webhook-related story is genuinely split across both tables today, not just theoretically. Result dataclasses stay separate per source (`ShopifyWebhookIntakeHistoryRecordResult`, `ShopifyIntegrationEventHistoryRecordResult`) rather than one shared dataclass, since the two row shapes are genuinely different (retry/attempt fields vs. event/severity fields) — each is serialized independently, then both are merged as plain dicts in the query, mirroring how the query layer (not the result layer) does the merging in `task_flow_records.py` too.
2. **Discriminator field is `record_type`, not the task-domain precedent's `type`.** `domain/tasks/serializers.py`'s `serialize_history_flow_record`/`serialize_step_flow_record` use a bare `"type"` key (`"history_record"` / `"task_step"` / `"task_step_group"`) for the same purpose. This plan intentionally uses `record_type` instead, per explicit instruction, rather than silently matching the task-domain's `type` key — `record_type` is also the clearer choice here specifically because `ShopifyIntegrationEvent` rows already have their own, semantically different `event_type` field (`INSTALL`/`REAUTHORIZE`/`WEBHOOK_SYNC`/.../`DISCONNECT`) in the same serialized object; a bare `type` key sitting next to `event_type` in one JSON object would read ambiguously to a frontend developer, whereas `record_type` (the *merge-source* discriminator) vs. `event_type` (the *domain* value) is unambiguous. Values: `"webhook_intake"` | `"integration_event"`.
3. **Route path: `GET /api/v1/integrations/shopify/shops/{shop_integration_id}/webhooks/history`, not the suggested `/webhook-history`.** The task brief's suggested path (`.../shops/{id}/webhook-history`, a single kebab-case segment) is a workable alternative, but this plan proposes the nested form instead because it matches this router's own existing, more specific precedent more closely: phase 6 already added `POST /shops/{shop_integration_id}/webhooks/sync` (nested `webhooks/` segment, action suffix). `GET /shops/{shop_integration_id}/webhooks/history` reuses the identical `webhooks/` segment with a different action suffix (`history` vs. `sync`), which is a tighter match to this specific router's own convention than a new top-level kebab-case segment would be. No other admin route in this router uses a bare kebab-case action suffix directly under `/shops/{id}/` except `reauthorize-url`, which is a single action verb, not a sub-resource — `webhooks/history` better fits the "sub-resource under shop" shape this new route actually has. This is the one exact path this plan commits to; no alternative is left open.
4. **`limit`/`offset` are read from query params via `dict(request.query_params)`, matching every other phase-6 `GET` route exactly** (`list_shopify_shop_integrations_route`, `get_shopify_scopes_route`) — the router passes `query_params=dict(request.query_params)` into `ServiceContext`, and the query function parses/clamps `limit`/`offset` itself (`_parse_int`-style helper, default `limit=10`, max `limit=200`, `offset >= 0`), matching `list_shopify_shop_integrations.py`'s exact parsing shape (adapted for this plan's smaller default of `10`, per the task brief's explicit instruction, vs. phase 6's `50` default for the shop list — a deliberately different default because a history feed is read more like an activity stream, matching `task_flow_records.py`'s own `DEFAULT_FLOW_RECORDS_LIMIT = 10`).
5. **Sort key: `(timestamp, client_id)` descending, source-appropriate timestamp per row type.** `ShopifyWebhookIntake` rows sort by `received_at` (the row's own "this happened at" moment, already indexed); `ShopifyIntegrationEvent` rows sort by `created_at` (the row's only timestamp). Both are combined into one raw list of `(timestamp, source_type, row)` tuples and sorted `reverse=True` on `(timestamp, row.client_id)`, exactly mirroring `task_flow_records.py`'s `raw.sort(key=lambda x: (x[0], x[2].client_id), reverse=True)` tie-breaker shape (using `client_id` instead of a second timestamp field, since `client_id`s in this codebase are lexicographically sortable creation-ordered identifiers, giving a deterministic tie-break for two rows with an identical microsecond-truncated timestamp).
6. **`metadata_json` is defensively filtered by key-substring, dropping benign fields as an acceptable false-positive.** `_filter_safe_metadata(metadata: dict | None) -> dict | None` in `domain/shopify/serializers.py` drops any key whose lowercased name contains `token`, `secret`, `hmac`, `signature`, `authorization`, `code`, `raw_payload`, `payload`, `raw_response`, or `provider_response`, per explicit instruction. This is intentionally conservative: it will also drop currently-safe keys like `reason`-adjacent `error_code`/`integration_status`-shaped names that merely happen to contain `"code"` as a substring (e.g. phase 4's `metadata_json["reason"] = "inactive_shop_integration"` survives, but a hypothetical future `metadata_json["error_code"] = ...` would not). This trade-off is deliberate and matches the explicit "defensively safe" instruction — the only cost of over-filtering is a frontend seeing slightly less metadata than it could; the cost of under-filtering is a leaked secret. No currently-existing Shopify event `metadata_json` value observed in phases 2-6's actual code (`shop_domain`, `topic`, `webhook_id`, `intake_status`, `reason`, `integration_status`, `processing_status`, `sync_status`, `processing_mode`, `action`, `previous_status`, `new_status`, `remove_webhooks_task_id`, `removed_topics`, `failed_topics`) is dropped by this filter today — confirmed by checking every `metadata_json={...}` literal across phases 2-6's commands/handlers directly.
7. **No schema change, no new index — Python-level merge is acceptable for this first implementation, per explicit instruction.** Neither source table has a composite `(shop_integration_id, <timestamp>)` index today (`ShopifyWebhookIntake` has `shop_integration_id` and `received_at` indexed separately; `ShopifyIntegrationEvent` has `(workspace_id, shop_integration_id)` and `created_at` indexed separately) — each per-source query still filters efficiently by the existing single-column/composite indexes before the Python-level merge, and the merge itself only operates on rows already scoped to one shop (not a global/cross-workspace scan), matching the same bounded-fan-out shape `task_flow_records.py` already accepts for one task's history. If a single shop's webhook volume grows large enough to make full per-shop table scans expensive, a future phase can add a composite index or move pagination fully into SQL — explicitly deferred, not attempted here, consistent with "Python-level pagination is acceptable for a first flow-record implementation."
8. **Optional filters (`record_type`, `topic`, `status`, `severity`, `event_type`) are explicitly deferred, not stubbed.** Only `limit`/`offset` are implemented. No unused filter parameter, no `TODO`, no dead branch is added for the deferred filters — they are simply not present in this phase's query signature, per explicit instruction to keep this phase's scope to "frontend pull access to history," not "advanced search."

## Acceptance criteria

1. `GET /api/v1/integrations/shopify/shops/{shop_integration_id}/webhooks/history` is registered on the existing `routers/api_v1/shopify.py` router at the existing `/api/v1/integrations/shopify` prefix — no new router file, no new `include_router` call, and the route does not exist under `/api/v1/shopify/webhooks` (the external Shopify-facing router).
2. The route requires `ADMIN` or `MANAGER` via `Depends(require_roles([ADMIN, MANAGER]))`; a `WORKER` or `SELLER` JWT is rejected (`403`) before any query logic runs.
3. The query verifies the `ShopifyShopIntegration` row exists in `ctx.workspace_id`, matches the given `shop_integration_id`, and is not soft-deleted (`is_deleted.is_(False)`) before reading any history row; a shop integration belonging to another workspace, a nonexistent id, or a soft-deleted shop all resolve as `NotFound`, never as data.
4. The response envelope is exactly `{"webhook_history_records": [...], "webhook_history_records_pagination": {"limit", "offset", "has_more"}}`, with `limit` defaulting to `10`, clamped to a max of `200`, and `offset` clamped to `>= 0`.
5. Records are ordered strictly newest-first across both sources combined, using each source's own timestamp (`received_at` for intake rows, `created_at` for event rows) with `client_id` as a deterministic tie-breaker.
6. Each record includes `"record_type": "webhook_intake"` or `"record_type": "integration_event"` and only the safe fields listed in "Resolved decisions" item 1/the Scope section — never `raw_payload`, never a raw HMAC/token/secret value, and never an unfiltered `metadata_json` (event records only).
7. `metadata_json` on event records has every key whose lowercased name contains `token`, `secret`, `hmac`, `signature`, `authorization`, `code`, `raw_payload`, `payload`, `raw_response`, or `provider_response` removed before serialization.
8. An empty history (a shop with zero intake rows and zero events) returns `{"webhook_history_records": [], "webhook_history_records_pagination": {"limit": <requested>, "offset": <requested>, "has_more": false}}`, not an error.
9. This phase adds no new Shopify task type, queue mapping, worker behavior, migration, or frontend code, and does not modify `PLAN_shopify_deployment_validation_20260709.md` (phase 7) in any way.

## Contracts and skills

### Contracts loaded

- `architecture/04_context.md`: `ServiceContext` identity/session/query_params boundaries for the new query, matching phase 6's existing query construction exactly.
- `architecture/05_errors.md`: `NotFound` for the workspace-scoped shop lookup miss; no new error subclass is introduced.
- `architecture/07_queries.md` + `architecture/07_queries_local.md`: Offset pagination (`limit`/`offset`, `has_more`, `<name>_pagination` envelope key) — the local contract this plan follows exclusively, matching `list_shopify_shop_integrations.py` and `task_flow_records.py`.
- `architecture/09_routers.md`: The router stays I/O only; the new route calls exactly one query via `run_service`, matching every existing route in `shopify.py`.
- `architecture/15_testing.md`: Test-tier placement for query tests (workspace isolation, pagination, ordering), serializer tests (no-secret assertions), and route tests (role gating, path placement).
- `architecture/17_logging.md`: This phase adds no new logging beyond what phases 4-6 already emit — a read-only query needs no additional log line beyond `run_service`'s existing error-boundary logging.
- `architecture/18_security.md`: IDOR prevention via the workspace-scoped `shop_integration_id` lookup (same pattern as every other phase-6 route); no arbitrary cross-workspace history exposure.
- `architecture/24_multi_tenancy.md`: The query is workspace-first — both source-table reads are additionally constrained by the already-verified `shop_integration_id`, which is itself workspace-verified first.
- `architecture/25_soft_delete.md`: Soft-deleted shop integrations are excluded via the same `is_deleted.is_(False)` check phase 6 already established; this plan does not introduce any new soft-delete semantics of its own (neither source table this plan reads is itself soft-deletable).
- `architecture/28_roles_permissions.md`: Confirmed (again, by direct code inspection, not re-derived) that flat `role_name`/`require_roles([...])` is the actual enforced gate; this plan uses it exactly as phase 6 did for same-sensitivity read routes.
- `architecture/46_serialization.md`: Two new result dataclasses + two new serializer functions in the existing `domain/shopify/results.py`/`serializers.py`, following the exact pattern phase 6 established — no new DTO architecture, no third file.

### Local extensions loaded

- `architecture/07_queries_local.md`: Elevated here (see Contracts loaded) since it materially changes this query's envelope shape versus the generic cursor-pagination doc.
- `architecture/40_identity_local.md`: No new prefixes needed — this plan reads existing `shpwhi`/`shpevt`-prefixed rows, it does not create new identity-bearing rows.
- `architecture/46_serialization_local.md`: Confirmed empty stub, no local override — canonical `46_serialization.md` pattern followed directly, consistent with phase 6.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** -> read the contract instead (`06_commands.md`, `07_queries.md`, `09_routers.md`, `46_serialization.md`, etc.)
- **What exists** -> reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another query to understand the general `ServiceContext`/`session.execute` shape -> `06_commands.md`/`04_context.md`
- Reading another router to understand handler wiring -> `09_routers.md`
- Reading another serializer to understand the general dataclass-and-`asdict()` convention -> `46_serialization.md`

Permitted for this child (all already read once during this plan's drafting; re-read only to confirm nothing changed before implementation):
- `app/beyo_manager/routers/api_v1/shopify.py` (phase 6, implemented) — exact existing route/role-gating/`ServiceContext`-construction shape this plan's new route matches.
- `app/beyo_manager/services/queries/shopify/get_shopify_shop_integration.py`, `list_shopify_shop_integrations.py` (phase 6, implemented) — exact workspace-scoped-lookup-then-`NotFound` pattern and exact offset-pagination parsing/envelope shape this plan's new query matches.
- `app/beyo_manager/domain/shopify/results.py`, `serializers.py` (phase 6, implemented) — exact existing dataclass/serializer-function conventions this plan's two new result/serializer pairs must match, and confirmation of every currently-existing `metadata_json` key this plan's filter must not accidentally break.
- `app/beyo_manager/models/tables/shopify/shopify_webhook_intake.py`, `shopify_integration_event.py`, `shopify_shop_integration.py` — exact column names/types/indexes for the two new serializers and the workspace-scoped lookup.
- `app/beyo_manager/services/queries/tasks/task_flow_records.py` — algorithm shape only (workspace-scoped parent check first, limit/offset clamping, raw-list-build-then-sort-then-slice, `limit + 1` `has_more` trick, envelope shape) — not its task/history/step-specific entity logic, per explicit instruction.
- `app/beyo_manager/routers/utils/roles.py`, `routers/utils/jwt_dep.py` — confirmed unchanged `ADMIN`/`MANAGER`/`WORKER`/`SELLER` constants and `require_roles` shape (already directly re-confirmed during this plan's drafting; no further re-read needed at implementation time unless these files show as changed).
- `app/beyo_manager/errors/not_found.py` — exact `NotFound` constructor signature, to match phase 6's exact usage.

### Skill selection

- Primary skill: `none`
- Router trigger terms: `none`
- Excluded alternatives: `skills/cross_cutting/intention_planning/SKILL.md` — source intention already exists.

### Contracts intentionally not selected for this child

- `06_commands.md`: No command is added — this phase is read-only.
- `16_background_jobs.md`, `12_infra_redis.md`, `51_worker_runtime.md`, `49_observability_runtime.md`: No task type, queue, or worker code.
- `19_integrations.md`: No external Shopify API/GraphQL call — pure local-database read.
- `03_models.md`, `30_migrations.md`: No new table or migration.
- `33_deployment.md`, `31_health_observability.md`, `54_ci_cd_runtime.md`: Not relevant to a single read-only admin route; phase 7 (deployment/validation) is not touched or modified by this plan.
- `13_sockets.md`, `56_realtime_layer.md`, `34_file_storage.md`, `20_api_versioning.md`: Not relevant.

## Implementation plan

1. Add `ShopifyWebhookIntakeHistoryRecordResult` and `ShopifyIntegrationEventHistoryRecordResult` frozen dataclasses to `domain/shopify/results.py`, with fields per the Scope section's safe-field lists (each including `record_type: str`), placed alongside the three existing Shopify result dataclasses.

2. Add `serialize_shopify_webhook_intake_history_record(row: ShopifyWebhookIntake) -> ShopifyWebhookIntakeHistoryRecordResult` and `serialize_shopify_integration_event_history_record(row: ShopifyIntegrationEvent) -> ShopifyIntegrationEventHistoryRecordResult` to `domain/shopify/serializers.py`, plus the private `_filter_safe_metadata(metadata: dict | None) -> dict | None` helper per "Resolved decisions" item 6, used only by the event-record serializer.

3. Add `services/queries/shopify/get_shopify_webhook_history_records.py`:
   - Parse and clamp `limit` (default `10`, max `200`) and `offset` (`>= 0`) from `ctx.query_params`, matching `list_shopify_shop_integrations.py`'s parsing shape.
   - Verify the `ShopifyShopIntegration` row (workspace-scoped, non-deleted) exists; raise `NotFound` on a miss, before reading either history source.
   - Fetch `ShopifyWebhookIntake` rows for the shop (no separate `limit`/`offset` at the SQL level — the full per-shop set is fetched, bounded by the shop scope, per "Resolved decisions" item 7) and `ShopifyIntegrationEvent` rows for the shop, in two separate `select()` calls.
   - Build a raw sortable list of `(timestamp, source_type, row)` tuples (`received_at` for intake rows, `created_at` for event rows).
   - Sort `reverse=True` on `(timestamp, row.client_id)`.
   - Apply the `limit + 1` Python-level offset-pagination slice; compute `has_more`.
   - Serialize the page: intake rows via `serialize_shopify_webhook_intake_history_record`, event rows via `serialize_shopify_integration_event_history_record`, each wrapped in `asdict(...)`.
   - Return `{"webhook_history_records": [...], "webhook_history_records_pagination": {"limit", "offset", "has_more"}}`.

4. Add `GET /shops/{shop_integration_id}/webhooks/history` to `routers/api_v1/shopify.py`, calling the new query via `run_service`, gated by `Depends(require_roles([ADMIN, MANAGER]))`, matching the exact `ServiceContext(identity=claims, incoming_data={"shop_integration_id": shop_integration_id}, query_params=dict(request.query_params), session=session)` construction shape used by `list_shopify_shop_integrations_route`/`get_shopify_scopes_route`.

5. Tests:
   - Route tests: `ADMIN`/`MANAGER` allowed; `WORKER`/`SELLER` rejected (`403`) with zero query invocation; a shop integration id belonging to another workspace resolves `404`/`NotFound`; a soft-deleted shop integration resolves `404`/`NotFound`; the route path is confirmed to live under `/api/v1/integrations/shopify` and not `/api/v1/shopify/webhooks`.
   - Query tests: newest-first ordering across a mix of intake and event rows with distinct and colliding timestamps (tie-break by `client_id`); `limit`/`offset`/`has_more` correctness across page boundaries; an empty-history shop returns an empty list with a correct pagination object, not an error.
   - Serializer tests: intake-record serialization includes exactly the documented safe fields and never `raw_payload`; event-record serialization includes exactly the documented safe fields and never an unfiltered `metadata_json`; a direct `_filter_safe_metadata` unit test asserts every blocked substring (`token`, `secret`, `hmac`, `signature`, `authorization`, `code`, `raw_payload`, `payload`, `raw_response`, `provider_response`) is actually dropped, case-insensitively, and that every currently-real Shopify event metadata key (`shop_domain`, `topic`, `webhook_id`, `intake_status`, `reason`, `integration_status`, `processing_status`, `sync_status`, `processing_mode`, `action`, `previous_status`, `new_status`, `remove_webhooks_task_id`, `removed_topics`, `failed_topics`) survives unfiltered.

## Risks and mitigations

- Risk: `_filter_safe_metadata`'s substring-based filtering drops a currently-real, safe metadata key because its name happens to contain one of the blocked substrings (e.g. a hypothetical future `error_code` key would be dropped because it contains `"code"`).
  Mitigation: "Resolved decisions" item 6 documents this trade-off explicitly as an accepted, deliberate over-filtering; the serializer test in Implementation plan step 5 explicitly locks in today's known-safe key list so any future key addition that gets unexpectedly dropped is caught by a failing test, not silently discovered in production.
- Risk: Fetching all `ShopifyWebhookIntake`/`ShopifyIntegrationEvent` rows for one shop before pagination (Python-level merge) becomes slow for a shop with an unusually large webhook history.
  Mitigation: "Resolved decisions" item 7 explicitly accepts this bounded (single-shop-scoped, not global) trade-off for a first implementation, matching `task_flow_records.py`'s own accepted precedent; a future phase can add a composite index or move to SQL-level pagination if real-world volume ever proves this insufficient — not attempted here.
- Risk: A future contributor adds `raw_payload` or an unfiltered `metadata_json` directly to one of the new result dataclasses "for convenience," reintroducing a leak this plan was specifically designed to prevent.
  Mitigation: Neither result dataclass has a `raw_payload` field at all (nothing to filter, nothing to forget to filter), and `metadata_json` only ever reaches the event-record serializer through `_filter_safe_metadata` — the serializer test in Implementation plan step 5 fails immediately if either safeguard is bypassed.
- Risk: The chosen route path (`/shops/{id}/webhooks/history`) is confused with the external-facing `/api/v1/shopify/webhooks` route by a future contributor skimming route names.
  Mitigation: Acceptance criteria item 1 and the route-path test in Implementation plan step 5 explicitly assert this route is registered under `/api/v1/integrations/shopify`, matching the same explicit-path-assertion discipline phase 4's own `test_shopify_webhook_route_is_reachable_at_exact_path_and_not_under_integrations_prefix` test established for the reverse case.
- Risk: `ShopifyIntegrationEvent` rows unrelated to webhooks (if any non-webhook event type is ever added to the enum in a future phase) get pulled into this "webhook history" feed, diluting its purpose.
  Mitigation: Every current `ShopifyIntegrationEventTypeEnum` member (`INSTALL`, `REAUTHORIZE`, `WEBHOOK_SYNC`, `WEBHOOK_RECEIVED`, `WEBHOOK_PROCESSED`, `HEALTH_CHECK`, `ERROR`, `DISCONNECT`) is plausibly relevant to a shop's operational timeline, and the task brief's own suggested safe-field list for event records includes all of them without an event-type filter — this plan does not filter by `event_type` (per "Resolved decisions" item 8, filters are deferred), so this is a known, accepted scope, not an oversight; a future phase can add an `event_type` allow-list filter if a future non-webhook event type needs excluding.

## Validation plan

- `pytest tests/unit/domain/shopify/test_serializers.py` (extended): new no-secret/no-raw-payload assertions for both new serializer functions, plus the `_filter_safe_metadata` unit test, pass.
- `pytest tests/integration/services/queries/shopify/` (extended, e.g. a new `test_shopify_webhook_history_query.py`): workspace isolation, soft-delete exclusion, newest-first ordering, pagination/`has_more` correctness, and empty-history shape all pass against a real Postgres instance.
- `pytest tests/unit/test_shopify_router.py` (extended): role-gating tests for the new route pass, matching phase 6's own role-gating test shape.
- Manual/documented check: confirm no captured test fixture response body for this route contains a token-shaped, secret-shaped, or HMAC-shaped string, or a `raw_payload` key, across a mixed intake+event fixture.

## Review log

- `2026-07-09` `Codex`: Drafted the phase 6.1 child implementation plan (Shopify webhook history records) after confirming phase 6 is fully implemented and archived — read phase 6's actual code directly (`routers/api_v1/shopify.py`, `domain/shopify/results.py`/`serializers.py`, `get_shopify_shop_integration.py`, `list_shopify_shop_integrations.py`) rather than its plan text, since no verification-checklist gate was needed this time. Chose merged webhook flow records (Option B) over intake-only, grounded in the actual shape of both source tables and every real `metadata_json` key currently in use across phases 2-6. Chose the route path `/shops/{shop_integration_id}/webhooks/history` over the suggested `/webhook-history`, as a closer match to this router's own existing `/shops/{shop_integration_id}/webhooks/sync` precedent. Deferred all optional filters. No blockers found — phase 6's actual code fully supports this plan's design with no gaps, so this plan moves directly to `approved` on creation, per the explicit instruction that it need not wait for or be gated on phase 7.
- `2026-07-08` `Codex`: Implemented the Phase 6.1 Shopify webhook history read surface on the existing admin router, extended the Shopify result/serializer layer with webhook-intake and integration-event history records, and added conservative event metadata filtering. Validated with `py_compile`, the Shopify domain unit suite, and the Shopify router unit suite. The new DB-backed history query suite could not run to completion because PostgreSQL on port `5433` was unavailable in this session.

## Lifecycle transition

- Current state: `approved`
- Next state: `implemented`
- Transition owner: `Codex`
