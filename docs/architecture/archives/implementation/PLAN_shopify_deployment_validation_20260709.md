# PLAN_shopify_deployment_validation_20260709

## Metadata

- Plan ID: `PLAN_shopify_deployment_validation_20260709`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-09T13:00:00Z`
- Last updated at (UTC): `2026-07-09T18:00:00Z`
- Related issue/ticket: `Shopify integration deployment and validation`
- Intention plan: `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`
- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_integration_master_20260707.md`
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_foundation_schema_config_20260707.md` — phase 1 foundation (settings fields, models, migration `677ed7131bb2`).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_oauth_linking_20260707.md` — phase 2 (`routers/api_v1/shopify.py` OAuth routes, `SHOPIFY_REDIRECT_URI`/`SHOPIFY_OAUTH_REDIRECT_URL` usage this plan's deployment checklist documents precisely).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_registry_sync_20260707.md` — phase 3 (webhook subscription sync/remove commands this plan's smoke runbook exercises indirectly via phase 5's worker).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_intake_execution_20260708.md` — phase 4 (`routers/api_v1/shopify_webhooks.py` at exactly `/api/v1/shopify/webhooks`, HMAC verification this plan's route-reachability validation checks).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_worker_execution_20260708.md` — phase 5 (`workers/shopify_worker.py`, `queue:shopify`, task types, migration `c3f7a9d2e4b1` as the confirmed current migration head at the time this plan was drafted; the local `shopify-worker` Makefile target this plan's systemd unit mirrors).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_admin_routes_serializers_20260709.md` — phase 6 is now **implemented, reviewed, and archived** (`backend/docs/architecture/implemented_summaries/SUMMARY_shopify_admin_routes_serializers_20260709.md`). Reviewed on `2026-07-09` against the archived plan, implemented summary, and the actual code. Verdict: **approved with minor follow-up** (see "Phase 6 implementation dependencies to verify before approval" below, now filled in with confirmed facts).
- Depends on (implemented and verified): `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_history_records_20260709.md` — phase 6.1 is now **implemented, reviewed, and archived** (`backend/docs/architecture/implemented_summaries/SUMMARY_shopify_webhook_history_records_20260709.md`). Reviewed on `2026-07-09` against the archived plan, implemented summary, and the actual code. Verdict: **approved with minor follow-up** (see "Phase 6.1 implementation dependencies verified" below).

## Goal and intent

- Goal: Prepare the completed Shopify backend integration (phases 1-6) for safe EC2 production deployment — env var promotion, Shopify Partner Dashboard configuration, systemd process registration for the dedicated Shopify worker, migration/startup/queue/route validation, no-secret logging validation, a first-shop operational smoke runbook, and rollback notes — using this repository's actual, already-established deployment conventions (systemd via `.github/workflows/deploy.yml`, not the legacy `Procfile`).
- Business/user intent: Let an operator take everything phases 1-6 built and actually turn it on in production — connect a real Shopify shop, confirm OAuth/webhook/sync/admin routes all work end-to-end on EC2, and know exactly how to roll back if something breaks — without guessing at process names, env var criticality, or Shopify dashboard settings.
- Non-goals:
  - New Shopify OAuth, webhook, sync, worker, or admin route behavior — this phase only wires deployment/process/validation around what phases 1-6 already built.
  - New database tables or feature-behavior migrations — documentation-only migration corrections only, and only if absolutely required.
  - Product/order business processing, historical imports, or frontend UI.
  - Changing worker runtime internals (`worker_base.py`, `task_router.py`, `workers/shopify_worker.py` itself) — this phase registers and validates the existing entrypoint, it does not modify it.
  - Adding new `/ready`/`/live` health endpoints — the generic `31_health_observability.md` contract's three-endpoint model is not implemented anywhere in this codebase today (confirmed: only `GET /health` exists, checking DB+Redis only); introducing new endpoints would be new application feature behavior, outside this phase's "config/process wiring only" mandate per the master plan's phase-7 "Must not touch" line.
  - Redesigning the general (non-Shopify) CI pipeline — `'.github/workflows/ci.yml`'s lint/format/test jobs are a pre-existing, codebase-wide convention; this phase documents Shopify-specific validation steps consistent with that existing scope, it does not add new CI jobs for migration/health gates repo-wide.
  - Creation of any further child implementation plans — phase 7 is the last child plan in the master plan's decomposition.

## Scope

- In scope:
  - Environment variable checklist: which Shopify/encryption settings exist, their exact config names, and — critically — confirmation that none of them are in the application's critical-startup-required list (so this phase does not silently promote them to required).
  - Shopify Partner Dashboard configuration checklist, grounded in the actual code that constructs each URL (webhook callback URL, OAuth redirect URI), not assumed values.
  - Adding `managerbeyo-shopify-worker` to the existing `sudo systemctl restart` list in `.github/workflows/deploy.yml` — the one concrete in-repo file change this phase makes.
  - An operational runbook step describing the exact systemd unit file (`/etc/systemd/system/managerbeyo-shopify-worker.service`) an operator must create on the EC2 host, mirroring the existing (out-of-repo) `managerbeyo-tasks-worker.service` shape, since no `.service` files are tracked in this repository.
  - Migration validation: confirm `alembic heads`/`alembic current`/`alembic upgrade head` cover phase 1's foundation migration, phase 5's task-type migration, and phase 6's `DISCONNECT` enum migration — all three now confirmed by revision ID (see "Migration validation" below).
  - Queue/task validation: Shopify task types exist, route only to `queue:shopify`, the dedicated worker registers only Shopify handlers, and all four enqueue boundaries (post-OAuth sync, webhook-intake process, manual admin sync, disconnect) actually create the expected task type.
  - HTTP route reachability validation for the webhook route (`/api/v1/shopify/webhooks`), OAuth routes, phase 6's six admin routes, and phase 6.1's webhook-history route (`GET /shops/{shop_integration_id}/webhooks/history`) — auth/HMAC boundary checks, not business-logic checks.
  - No-secret logging validation checklist, reusing the exact blocked-term lists phases 2-6.1's own boundary-guard tests already established, extended to phase 6.1's response-body/`metadata_json` safety.
  - A first-shop-connection operational smoke runbook (18 ordered steps — the original 17-step sequence plus one new step verifying the webhook-history endpoint after webhook processing completes).
  - Rollback notes: code rollback, worker stop/restart, env var rollback, migration risk, disabled-integration state, already-installed-in-Shopify webhook subscriptions, and avoiding duplicate workers on one queue.
  - Master-plan closure as a documented *future implementation step* only (update master plan status, add a final intention-plan progress note, document remaining deferred Shopify work) — not performed by this draft.
- Out of scope:
  - New Shopify OAuth, webhook, sync, or admin route code.
  - New serializers or query/command modules.
  - New database tables (documentation-only migration corrections only, and only if strictly required).
  - Product/order business processing or historical imports.
  - Frontend UI.
  - Worker runtime internals (`worker_base.py`, `task_router.py`, `workers/shopify_worker.py`).
  - Creation of any further child implementation plans.
- Assumptions:
  - Phase 6 (`PLAN_shopify_admin_routes_serializers_20260709.md`) and phase 6.1 (`PLAN_shopify_webhook_history_records_20260709.md`) are both implemented, archived, and reviewed — confirmed `2026-07-09`. The "Phase 6 implementation dependencies to verify before approval" and "Phase 6.1 implementation dependencies verified" sections below are now written against the actual archived code and implemented summaries, not approved-but-unimplemented plan text, following the exact verification discipline every prior phase transition in this series has applied.
  - Phases 1-5 are implemented, archived, and stable per their own prior reviews (most recently, phase 5 was reviewed against its actual archived code on `2026-07-09` and found `approved with minor follow-up`) — not re-verified here beyond the specific deployment-relevant facts below.
  - This codebase's actual production process manager is **systemd**, orchestrated entirely through `.github/workflows/deploy.yml`'s SSH deploy script (`sudo systemctl daemon-reload && sudo systemctl restart <service-list>`) — confirmed by direct inspection. The repository's `app/Procfile` (`web`, `worker`, `task-router`, `delayed-scheduler`, `recurring-scheduler`, `tasks-worker`, `email-idle-watcher`) is a legacy/local artifact: it already omits `presence-worker`, `analytics-worker`, `notification-worker`, and now `shopify-worker`, none of which stops those services from running in production via directly-managed systemd units. This plan follows the systemd/`deploy.yml` convention, not the `Procfile`, for production process registration.
  - No `.service` unit files are tracked anywhere in this repository (confirmed via a repo-wide search) — they exist only on the EC2 host itself, created and maintained out-of-band by whoever provisioned the box. This plan cannot read or edit them directly; it documents the exact unit file an operator must create, by mirroring the one in-repo signal of what they look like (the `systemctl restart` service-name list in `deploy.yml`, and the existing Makefile dev-entrypoint command each systemd unit's `ExecStart` presumably wraps).
  - The application's critical-startup-required settings are exactly `["secret_key", "jwt_secret_key", "database_url", "redis_url"]` (`beyo_manager/config.py`'s `_require_critical_settings`) — confirmed unchanged since phase 1. No Shopify setting and no `field_encryption_key` is in this list; this plan documents them as "required before first real Shopify use," not "required for the app to boot," per explicit instruction not to promote them to critical startup requirements.
  - `GET /health` (`routers/api_v1/health.py`) checks Postgres (`SELECT 1`) and Redis (`PING`) only, returns `200`/`ok` or `503`/`degraded`, and is registered with no JWT dependency — confirmed unchanged since before phase 1. It already correctly excludes external-provider checks (no Shopify call), so it requires zero Shopify-specific change; this phase's validation plan calls it as-is, it does not modify it.

## Phase 6 implementation dependencies to verify before approval

Phase 6 was reviewed against the archived plan, its implemented summary, and the actual code in the repository on `2026-07-09`. Every item below is now a **confirmed fact**, not an assumption.

- [x] **Actual admin route paths** — confirmed: all seven routes (six from the approved plan plus phase 6.1's history route) exist on `routers/api_v1/shopify.py`, mounted at `/api/v1/integrations/shopify`: `GET /shops`, `GET /shops/{shop_integration_id}`, `POST /shops/{shop_integration_id}/reauthorize-url`, `DELETE /shops/{shop_integration_id}`, `POST /shops/{shop_integration_id}/webhooks/sync`, `GET /shops/{shop_integration_id}/webhooks/history` (phase 6.1), `POST /webhooks/sync`, `GET /scopes`. Matches the approved plan exactly.
- [x] **Actual serializer/result file paths and public functions/classes** — confirmed: `domain/shopify/results.py` defines `ShopifyShopIntegrationResult`, `ShopifyWebhookSubscriptionResult`, `ShopifyScopeStatusResult` (phase 6) plus `ShopifyWebhookIntakeHistoryRecordResult`, `ShopifyIntegrationEventHistoryRecordResult` (phase 6.1); `domain/shopify/serializers.py` defines `serialize_shopify_shop_integration`, `serialize_shopify_webhook_subscription`, `serialize_shopify_scope_status` (phase 6) plus `serialize_shopify_webhook_intake_history_record`, `serialize_shopify_integration_event_history_record`, `_filter_safe_metadata` (phase 6.1). Matches phase 6's "Resolved decisions" item 2 exactly.
- [x] **Actual query service names and return shapes** — confirmed: `services/queries/shopify/list_shopify_shop_integrations.py` returns `{"shops": [...], "shops_pagination": {"limit", "offset", "has_more"}}`; `get_shopify_shop_integration.py` returns `{"shop_integration", "webhook_subscription_summary", "webhook_subscriptions"}`; `get_shopify_scope_status.py` returns `{"scope_statuses": [...]}` (supports both single-shop via `?shop_integration_id=` and workspace-wide). All match phase 6's design.
- [x] **Actual admin command names and signatures** — confirmed: `create_shopify_reauthorize_url.py`, `disconnect_shopify_shop.py`, `enqueue_shopify_webhook_sync_for_shop.py`, `enqueue_shopify_webhook_sync_for_workspace.py` all exist with the exact `ServiceContext`-shaped signatures phase 6 planned.
- [x] **Actual `DISCONNECT` enum migration revision** — confirmed: `ab12cd34ef56_add_disconnect_to_shopify_integration_event_type`, `down_revision="c3f7a9d2e4b1"` (phase 5's migration), confirmed non-forked. `ALTER TYPE shopify_integration_event_type_enum ADD VALUE IF NOT EXISTS 'disconnect'` — additive only, matching phase 1's idiom exactly. This is now the confirmed current migration head for the Shopify chain.
- [x] **Actual disconnect behavior** — confirmed exactly as planned: `disconnect_shopify_shop` sets `status=DISABLED`, `uninstalled_at=<now>`, `access_token_encrypted=None`; records `ShopifyIntegrationEvent(event_type=DISCONNECT, severity=INFO, metadata_json={"action": "disconnect", "shop_domain", "previous_status", "new_status": "disabled", "remove_webhooks_task_id"})` (the task id is backfilled into the event's `metadata_json` immediately after task creation, closing the chicken-and-egg ordering cleanly); enqueues exactly one `SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP` task via `create_instant_task(..., event_client_id=event.client_id)`; does not call `remove_shopify_webhooks_for_shop` inline; does not set `is_deleted=True`. Directly confirmed by reading `disconnect_shopify_shop.py` and its integration test (`test_disconnect_shopify_shop_soft_deletes_nothing_and_enqueues_remove_task`), which asserts every one of these fields plus `captured["event_client_id"] == events[0].client_id`.
- [x] **Actual manual sync enqueue behavior** — confirmed: both `enqueue_shopify_webhook_sync_for_shop` and `enqueue_shopify_webhook_sync_for_workspace` record a `WEBHOOK_SYNC` event first, then enqueue `SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP` via `create_instant_task(..., event_client_id=event.client_id)` (one event+task pair per eligible shop for the workspace-wide variant, filtered to `_SYNCABLE_INTEGRATION_STATUSES` and non-deleted), with zero inline Shopify GraphQL calls from either request path.
- [x] **Actual tests/results from phase 6** — confirmed from the implemented summary and reviewed directly: `py_compile` passed for all changed files; `pytest tests/unit/domain/shopify/test_serializers.py` passed (`3 passed` at phase-6 time, `22 passed` after phase 6.1 extended the same file); `pytest tests/unit/test_shopify_router.py` passed (`29 passed` at phase-6 time, `33 passed` after phase 6.1); `pytest tests/integration/services/queries/shopify/test_shopify_admin_queries.py` **could not complete** — local PostgreSQL on port `5433` was unreachable in Codex's session (`Connect call failed`), not a code failure. Reviewed test content directly: role-gating (`ADMIN`/`MANAGER` vs. `ADMIN`-only vs. `WORKER`/`SELLER` rejection with zero service invocation) and workspace-isolation/pagination/disconnect/manual-sync command assertions are all present and correctly targeted.
- [x] **Implemented phase 6 summary path** — `backend/docs/architecture/implemented_summaries/SUMMARY_shopify_admin_routes_serializers_20260709.md` (confirmed exists and reviewed).
- [x] **Archived phase 6 plan path** — `backend/docs/architecture/archives/implementation/PLAN_shopify_admin_routes_serializers_20260709.md` (confirmed exists, `Status: archived`, reviewed as the authoritative record).
- [x] **Deviations from the approved phase 6 plan** — one minor, non-blocking style deviation found: `disconnect_shopify_shop`, `create_shopify_reauthorize_url`, and `enqueue_shopify_webhook_sync_for_shop` all resolve the target shop via `ctx.session.get(ShopifyShopIntegration, shop_integration_id)` (a global primary-key lookup) followed by a manual `integration.workspace_id != ctx.workspace_id` check in Python, rather than filtering `workspace_id` directly in the `SELECT` `WHERE` clause the way the three query files do. This is **not an IDOR** — a cross-workspace or soft-deleted row is still correctly rejected as `NotFound` before any write — but it is a stylistic inconsistency within phase 6 itself (commands use get-then-check; queries use filter-in-`WHERE`). No functional risk; noted for awareness, not a blocker. No other deviation found.
- [x] **Whether the phase 5 carried-forward DB/alembic validation gap was resolved during phase 6** — **still outstanding, not resolved.** Both phase 6's and phase 6.1's implementation sessions hit the identical blocker: local PostgreSQL on port `5433` was unreachable, so neither phase's DB-backed integration test suites nor a live `alembic upgrade head` could be run. `py_compile` and all pure-unit tests passed in both phases; only the live-database pass remains outstanding, now carried forward a third time (phase 5 -> phase 6 -> phase 6.1 -> **this plan's own first live-DB validation pass**, per "Migration validation" and "Validation plan" below).

## Phase 6.1 implementation dependencies verified

Phase 6.1 (`PLAN_shopify_webhook_history_records_20260709.md`) was created, implemented, reviewed, and archived entirely within this same review cycle — it was approved on creation (Phase 6 was already implemented by the time it was drafted, so no separate under-construction verification gate was needed) and is now reviewed here against its actual archived code.

- [x] **Actual webhook history route path** — confirmed: `GET /api/v1/integrations/shopify/shops/{shop_integration_id}/webhooks/history`, registered on the existing `routers/api_v1/shopify.py` router. Confirmed via `test_shopify_webhook_history_route_is_reachable_at_exact_admin_path`, which additionally asserts `GET /api/v1/shopify/webhooks/history` (the external-facing prefix) returns `404` — the route cannot be reached under the wrong router.
- [x] **Actual result dataclass names** — confirmed: `ShopifyWebhookIntakeHistoryRecordResult` (`record_type`, `client_id`, `shop_integration_id`, `shop_domain`, `topic`, `webhook_id`, `status`, `retryable`, `attempts`, `received_at`, `processing_started_at`, `processed_at`, `last_error`, `created_at`, `updated_at`) and `ShopifyIntegrationEventHistoryRecordResult` (`record_type`, `client_id`, `shop_integration_id`, `event_type`, `severity`, `message`, `metadata_json`, `created_by_id`, `created_at`), both in `domain/shopify/results.py`. Neither has a `raw_payload` field.
- [x] **Actual serializer function names** — confirmed: `serialize_shopify_webhook_intake_history_record`, `serialize_shopify_integration_event_history_record`, and the private `_filter_safe_metadata(metadata: dict | None) -> dict | None` helper, all in `domain/shopify/serializers.py`.
- [x] **Actual query service name and return envelope** — confirmed: `services/queries/shopify/get_shopify_webhook_history_records.py`, returning exactly `{"webhook_history_records": [...], "webhook_history_records_pagination": {"has_more", "limit", "offset"}}`.
- [x] **Actual merged sources included in history — one confirmed, positive deviation from the approved plan.** The approved phase 6.1 plan specified including *every* `ShopifyIntegrationEvent` for the shop, unfiltered by `event_type` (explicitly documented as a deliberate no-filter decision in the plan's own risk log). The actual implementation instead defines `WEBHOOK_HISTORY_EVENT_TYPES = {WEBHOOK_SYNC, WEBHOOK_RECEIVED, WEBHOOK_PROCESSED, DISCONNECT}` and filters event rows to only this set via `event_type.in_(...)` in the query's `SELECT`, excluding `INSTALL`, `REAUTHORIZE`, `HEALTH_CHECK`, and `ERROR`. **This is a deliberate, sensible improvement over the approved plan, not a defect**: it makes the endpoint's actual behavior match its name ("webhook history") more precisely — `INSTALL`/`REAUTHORIZE` are OAuth-lifecycle events, not webhook events, and including them would dilute the feed's purpose. Confirmed directly in `get_shopify_webhook_history_records.py` and exercised by the integration test `test_webhook_history_query_returns_merged_records_newest_first_and_filters_oauth_events`, whose name states the filtering intent explicitly. This deviation is accepted as-implemented; this plan does not request a correction.
- [x] **Actual safe metadata filtering behavior** — confirmed: `_filter_safe_metadata` drops any `metadata_json` key whose lowercased name contains `token`, `secret`, `hmac`, `signature`, `authorization`, `code`, `raw_payload`, `payload`, `raw_response`, or `provider_response`, exactly as planned. Directly unit-tested (`test_filter_safe_metadata_removes_blocked_keys_case_insensitively`) confirming both the drop behavior and that safe keys (`shop_domain`, `sync_status`, `remove_webhooks_task_id`) survive.
- [x] **Actual pagination behavior** — confirmed: `limit` (default `10`, min `1`, max `200`) and `offset` (`>= 0`) parsed from `ctx.query_params`; both source tables' rows are merged into one raw `(timestamp, source_type, row)` list, sorted `reverse=True` on `(timestamp, row.client_id)`, sliced with the `limit + 1` `has_more` trick — matching the approved plan and the `task_flow_records.py` algorithm shape exactly.
- [x] **Actual tests/results** — confirmed from the implemented summary and reviewed directly: `py_compile` passed; `pytest tests/unit/domain/shopify -q` passed (`22 passed`, includes phase 6.1's serializer/metadata-filter tests); `pytest tests/unit/test_shopify_router.py -q` passed (`33 passed`, includes the history route's path and `ADMIN`/`MANAGER`-allowed/`WORKER`/`SELLER`-rejected coverage); `pytest tests/integration/services/queries/shopify/test_shopify_webhook_history_query.py` **could not complete** — same unreachable-Postgres-on-`5433` blocker as phase 6. Reviewed test content directly: newest-first ordering with OAuth-event exclusion, pagination/`has_more`, empty-history shape, and workspace-scoping/soft-delete-`NotFound` are all present and correctly targeted (`test_webhook_history_query_returns_merged_records_newest_first_and_filters_oauth_events`, `test_webhook_history_query_applies_offset_pagination_and_has_more`, `test_webhook_history_query_returns_empty_history_shape`, `test_webhook_history_query_is_workspace_scoped_and_rejects_soft_deleted_shops`).
- [x] **Implemented phase 6.1 summary path** — `backend/docs/architecture/implemented_summaries/SUMMARY_shopify_webhook_history_records_20260709.md` (confirmed exists and reviewed).
- [x] **Archived phase 6.1 plan path** — `backend/docs/architecture/archives/implementation/PLAN_shopify_webhook_history_records_20260709.md` (confirmed exists, `Status: archived`, reviewed as the authoritative record).
- [x] **Any deviations from the approved phase 6.1 plan** — the one event-type-filtering deviation documented above; no other deviation found. No migration, no Shopify API call, no worker/task/queue change was introduced, confirmed by direct inspection — phase 6.1 stayed within its declared scope.
- [x] **DB-backed validation status for phase 6.1** — **outstanding**, identical blocker to phase 6 (local PostgreSQL on port `5433` unreachable in Codex's session). Folded into this plan's own first live-DB validation pass, same as phase 6's gap above — these are not two separate gaps to track, they are the same one gap, now three phases deep.

## Resolved decisions

These design questions are resolved for this child plan by direct inspection of the actual deployment/process/config code in this repository (not generic contract examples). File:line references reflect the state read on `2026-07-09`.

1. **Production process manager is systemd via `deploy.yml`, not the `Procfile`.** `.github/workflows/deploy.yml`'s `Deploy to EC2` job runs, after `alembic upgrade head`: `sudo systemctl daemon-reload && sudo systemctl restart managerbeyo-backend managerbeyo-task-router managerbeyo-presence-worker managerbeyo-analytics-worker managerbeyo-notification-worker managerbeyo-delayed-scheduler managerbeyo-recurring-scheduler managerbeyo-tasks-worker`. `managerbeyo-shopify-worker` is **not** in this list — the concrete, in-repo gap this plan closes (see item 2). `app/Procfile` lists only `web`, `worker`, `task-router`, `delayed-scheduler`, `recurring-scheduler`, `tasks-worker`, `email-idle-watcher` and already omits `presence-worker`/`analytics-worker`/`notification-worker` despite those running in production via systemd — confirming the `Procfile` is not the source of truth for production process registration and this plan does not need to update it (consistent with phase 5's own finding that several existing dedicated workers already lack a `Procfile` entry).
2. **The one concrete in-repo change: add `managerbeyo-shopify-worker` to `deploy.yml`'s restart list.** A single-line addition to the existing `systemctl restart` command in `.github/workflows/deploy.yml`, alphabetically/logically grouped next to the other dedicated single-purpose workers (after `managerbeyo-notification-worker`, before `managerbeyo-delayed-scheduler`, matching the existing list's rough "backend -> task-router -> dedicated domain workers -> schedulers -> tasks-worker" ordering). This is the only application/deployment-config file this phase modifies at implementation time.
3. **No systemd unit file exists in-repo to model exactly — this plan documents the expected unit shape as an operational runbook step, not a repo file.** A repo-wide search for `*.service` files found none. The exact `ExecStart` line for the new `managerbeyo-shopify-worker.service` unit must mirror the already-proven Makefile dev-entrypoint command (`PYTHONPATH=. APP_ENV=development python -m beyo_manager.workers.shopify_worker`, `app/Makefile`'s `shopify-worker` target, added by phase 5), adapted to `APP_ENV=production` and the production working directory (`/var/www/managerbeyo-backend/app`, confirmed from `deploy.yml`'s `cd` step) and virtualenv (`.venv/bin/python`, confirmed from the same). This plan documents the exact unit file content for the operator to create once, out-of-band, on the EC2 host — it is not a file this phase can create or verify by itself, since it lives outside version control.
4. **No new `/ready`/`/live` health endpoints — `31_health_observability.md`'s three-endpoint model is aspirational in this codebase, not actual.** A repo-wide search confirms only `GET /health` exists (`routers/api_v1/health.py`, registered with prefix `/health`, no JWT dependency); no `/health/ready` or `/health/live` route exists anywhere. Adding them would be new application feature behavior beyond this phase's "config/process wiring only" mandate (master plan phase 7's explicit "Must not touch: feature behavior except config/process wiring"). `/health` already checks only Postgres and Redis and correctly excludes external providers (no Shopify call) — fully compliant with the contract's "do not check external providers in `/health`" rule without any Shopify-specific change. This plan's validation steps call the existing `/health` as-is.
5. **Shopify/encryption env vars stay optional at boot — confirmed, not changed.** `beyo_manager/config.py`'s `_require_critical_settings` validator's `required` list is exactly `["secret_key", "jwt_secret_key", "database_url", "redis_url"]` — unchanged since before phase 1, confirmed by direct inspection. None of `shopify_client_id`, `shopify_client_secret`, `shopify_app_scopes` (default `""`), `shopify_redirect_uri`, `shopify_oauth_redirect_url`, `shopify_api_version` (default `"2026-01"`), `shopify_webhook_base_url`, `shopify_integration_debug_logs` (default `False`), `shopify_webhook_secret`, or `field_encryption_key` is in that list, and this plan does not add any of them to it, per explicit instruction. The env var checklist below instead documents each as "required before first real Shopify use" (install-URL generation, webhook HMAC verification, token encryption) rather than "required for the app to start."
6. **Two distinct redirect-related settings serve two distinct purposes — confirmed by reading phase 2's actual implemented code, not assumed.** `SHOPIFY_REDIRECT_URI` (`settings.shopify_redirect_uri`) is the backend's own OAuth callback URL, sent to Shopify as the `redirect_uri` parameter when building the install URL (`services/infra/shopify/oauth_client.py:32,39`) — **this is the value that must exactly match the "Allowed redirection URL(s)" entry in the Shopify Partner Dashboard app configuration.** `SHOPIFY_OAUTH_REDIRECT_URL` (`settings.shopify_oauth_redirect_url`) is a completely different value: the **ManagerBeyo frontend** base URL the backend redirects the user's browser to *after* processing the OAuth callback, carrying only safe status query params (`services/commands/shopify/_redirect.py:26`, `build_shopify_oauth_redirect_url`) — this is never sent to Shopify and has no Shopify Partner Dashboard counterpart. The Shopify app dashboard configuration checklist below distinguishes these two precisely, since confusing them would silently break OAuth (Shopify would reject a callback to an unregistered redirect URI).
7. **Webhook callback URL construction, confirmed from phase 3's actual code.** `services/commands/shopify/remove_shopify_webhooks_for_shop.py`'s `_build_callback_url()` (and phase 3's sync command, which shares the pattern) constructs the callback URL Shopify sends webhooks to as `f"{settings.shopify_webhook_base_url.rstrip('/')}{SHOPIFY_WEBHOOK_CALLBACK_PATH}"`, where `SHOPIFY_WEBHOOK_CALLBACK_PATH = "/api/v1/shopify/webhooks"` is a fixed constant in `domain/shopify/webhook_registry.py` (confirmed, matches phase 4's actual registered route path exactly, verified by phase 4's own path/404 test). The Shopify app dashboard's webhook subscription callback URLs (created via phase 3's GraphQL `webhookSubscriptionCreate` calls, not manually configured in the dashboard) will therefore always resolve to `<SHOPIFY_WEBHOOK_BASE_URL>/api/v1/shopify/webhooks` — this plan's dashboard checklist documents this derivation instead of a guessed literal URL, since `SHOPIFY_WEBHOOK_BASE_URL` is environment-specific.
8. **Migration validation targets exactly three confirmed migrations, chain fully resolved.** The Shopify-relevant migration chain is: `677ed7131bb2_create_shopify_integration_foundation` (phase 1) -> `c3f7a9d2e4b1_add_shopify_execution_task_types` (phase 5) -> `ab12cd34ef56_add_disconnect_to_shopify_integration_event_type` (phase 6, confirmed current head, confirmed non-forked). This plan's migration validation section (see "Deployment runbook" below) checks all three exist and apply cleanly.
9. **CI (`ci.yml`) is not extended by this phase.** `.github/workflows/ci.yml` currently runs three jobs (`lint`, `format`, `test`) against Postgres/Redis service containers, with no dedicated migration-upgrade or health-check gate as a separate job (`test` implicitly exercises migrations via the test suite's DB fixtures, not an explicit `alembic upgrade head` step). This is a pre-existing, codebase-wide gap relative to `54_ci_cd_runtime.md`'s "Required Validation Flow" (which calls for explicit migration and health/readiness gates) — it predates the Shopify integration and affects every domain, not just Shopify. This plan documents Shopify-specific validation steps to run as part of the existing deploy script and manual/operator checklist (matching the current CI's actual scope), and flags the general CI gap as a non-blocking observation for a future, non-Shopify CI improvement — not something this phase's narrow mandate extends to fixing repo-wide.

## Clarifications required

None. Every design question resolved above was answered by direct inspection of this repository's actual, already-implemented deployment/config/health code (phases 1-6.1, all archived) — no genuine open ambiguity remains that depends on a future, not-yet-made decision. No blocker remains on this plan.

## Acceptance criteria

1. `.github/workflows/deploy.yml`'s `sudo systemctl restart` line includes `managerbeyo-shopify-worker` alongside every other existing service — no existing service name in that list is removed or reordered incorrectly, and no unrelated line in `deploy.yml` is modified.
2. This plan documents (not creates in-repo) the exact `managerbeyo-shopify-worker.service` systemd unit content an operator must place at `/etc/systemd/system/managerbeyo-shopify-worker.service` on the EC2 host, with an `ExecStart` mirroring the Makefile's `shopify-worker` target adapted to the production working directory, virtualenv, and `APP_ENV=production`.
3. The environment variable checklist lists all ten Shopify/encryption settings (`SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`, `SHOPIFY_APP_SCOPES`, `SHOPIFY_REDIRECT_URI`, `SHOPIFY_API_VERSION`, `SHOPIFY_WEBHOOK_BASE_URL`, `SHOPIFY_INTEGRATION_DEBUG_LOGS`, `SHOPIFY_WEBHOOK_SECRET`, `SHOPIFY_OAUTH_REDIRECT_URL`, `FIELD_ENCRYPTION_KEY`), correctly marks none of them as required for application boot, and correctly distinguishes `SHOPIFY_REDIRECT_URI` (Shopify-facing) from `SHOPIFY_OAUTH_REDIRECT_URL` (frontend-facing).
4. The Shopify Partner Dashboard checklist derives the webhook callback URL and allowed redirection URL from actual code (`SHOPIFY_WEBHOOK_CALLBACK_PATH`, `settings.shopify_redirect_uri`), not from an invented literal value, and contains no hardcoded secret.
5. Migration validation explicitly names all three Shopify-relevant migrations in confirmed chain order (`677ed7131bb2` phase 1 -> `c3f7a9d2e4b1` phase 5 -> `ab12cd34ef56` phase 6, confirmed non-forked current head) and confirms `alembic upgrade head` applies cleanly without accidentally including unrelated pre-existing migration drift (the same `workspace_roles`/`email_sync_states` drift phase 1's own review already found and explicitly excluded).
6. Queue/task validation confirms all four Shopify task types exist, route only to `queue:shopify`, and that each of the four enqueue boundaries (post-OAuth sync, webhook-intake process, manual admin sync, disconnect) creates exactly the expected task type — reusing phases 2-6.1's own boundary-connection tests as the validation mechanism, not new test code authored by this phase.
7. HTTP route validation confirms the webhook route exists at exactly `/api/v1/shopify/webhooks` (not under `/api/v1/integrations/shopify`) and rejects invalid HMAC; the OAuth callback route rejects invalid/missing HMAC or state; the install-url route, all six phase-6 admin routes, and phase 6.1's webhook-history route require a valid JWT and the correct role per phase 2/6/6.1's established role gating; the webhook-history route's response is confirmed to exclude `raw_payload` and unsafe `metadata_json` keys.
8. The no-secret logging checklist explicitly lists every forbidden value (access token, client secret, webhook secret, raw OAuth code, raw webhook payload, HMAC signature, and — per phase 6.1 — the ten `_filter_safe_metadata` blocked substrings) and confirms `SHOPIFY_INTEGRATION_DEBUG_LOGS` gates only safe debug-level metadata, never secrets, matching phases 2-6.1's own logging discipline.
9. The first-shop smoke runbook contains all 18 ordered steps (the original 17 plus phase 6.1's webhook-history check), each step naming the exact route/table/task type/log line an operator should check, not a vague description.
10. Rollback notes cover code rollback, worker stop/restart (with an explicit note on avoiding two `managerbeyo-shopify-worker` processes consuming `queue:shopify` simultaneously during a restart), env var rollback, migration risk (no destructive Shopify migration exists to roll back), disabled-integration state, and already-installed-in-Shopify webhook subscriptions surviving a ManagerBeyo-side rollback.
11. This phase adds no new Shopify OAuth/webhook/sync/admin route code, no new serializers, no new queries or commands, no new database tables, no product/order business processing, no frontend code, and creates no further child implementation plans.
12. DB-backed validation explicitly names the now-three-deep carried-forward gap (phase 5 -> phase 6 -> phase 6.1, all blocked by the same unreachable local PostgreSQL on port `5433`) and folds it into this plan's own first live-DB validation pass rather than treating it as resolved or as a new, separate issue.

## Contracts and skills

### Contracts loaded

- `architecture/33_deployment.md`: Migration-to-code ordering, environment variable promotion order, pre-deployment checklist, zero-downtime deploy sequence, rollback procedure — the primary contract this plan's env var checklist, migration validation, and rollback notes follow directly.
- `architecture/54_ci_cd_runtime.md`: Required validation flow (dependency install -> lint/format -> infra startup -> migration -> app startup -> health/readiness -> tests) as the ordering this plan's validation plan mirrors for Shopify-specific steps, without redesigning the general CI pipeline (see "Resolved decisions" item 9).
- `architecture/31_health_observability.md`: Health endpoint contract (confirmed this codebase implements only `/health`, not `/ready`/`/live` — see "Resolved decisions" item 4) and the "do not check external providers in `/health`" rule this plan's validation confirms is already satisfied without change.
- `architecture/49_observability_runtime.md`: Structured worker/task observability fields (`task_id`, `task_type`, `worker_id`, `elapsed_ms`) this plan's log-validation checklist confirms are present in `worker_base.py`'s unmodified logging, extended by this phase's own safe-metadata checklist for the Shopify worker specifically.
- `architecture/51_worker_runtime.md`: Worker lifecycle (startup validation, queue subscription, graceful `SIGTERM` shutdown) this plan's worker-startup validation and rollback notes (avoiding duplicate queue consumers) rely on, inherited unmodified from phase 5's `workers/shopify_worker.py` + `worker_base.run_worker`.
- `architecture/16_background_jobs.md` + `architecture/12_infra_redis.md`: Task type/queue map/Redis-transport-only conventions this plan's queue/task validation section confirms are unchanged since phase 5 (no new task type, queue, or Redis key pattern introduced by this phase).
- `architecture/17_logging.md`: Module logger, required context, and forbidden-secrets rules underlying this plan's no-secret logging validation checklist.
- `architecture/18_security.md`: HMAC verification, IDOR prevention, and secret-handling rules this plan's HTTP route validation and env var checklist confirm remain intact in the deployed configuration (not re-implemented, only validated).
- `architecture/19_integrations.md`: External adapter/timeout rules underlying the Shopify Partner Dashboard configuration checklist (API version, scopes) this plan documents.
- `architecture/30_migrations.md`: Additive-migration and `ALTER TYPE ... ADD VALUE` idiom this plan's migration validation confirms phases 1/5/6 all followed consistently.
- `architecture/15_testing.md`: Test-tier placement this plan's validation plan reuses (existing phase 1-6 test suites are the validation mechanism, not new test files authored by this phase).

### Local extensions loaded

- `architecture/33_deployment.md` has no `_local.md` sibling — the generic contract is followed directly, with this repo's actual systemd/`deploy.yml` convention (not the generic doc's illustrative examples) as the concrete implementation target, per "Resolved decisions" item 1.
- `architecture/51_worker_runtime.md`, `architecture/16_background_jobs.md`, `architecture/12_infra_redis.md` have no Shopify-specific local deltas beyond what phase 5 already established and this plan validates unchanged.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** -> read the contract instead (`33_deployment.md`, `54_ci_cd_runtime.md`, `31_health_observability.md`, `51_worker_runtime.md`, etc.)
- **What exists** -> reading is legitimate (existing deployment conventions, service names, settings, route paths)

Prohibited (pattern reads — contract already covers these):
- Reading another worker to understand the general worker lifecycle shape -> `51_worker_runtime.md`
- Reading another command to understand the general write-operation shape -> `06_commands.md` (not this phase's concern; this phase writes no commands)

Permitted for this child (all already read once during this plan's drafting; re-read only to confirm nothing changed before implementation, plus the phase-6-specific items once Codex finishes):
- `app/Procfile`, `.github/workflows/deploy.yml`, `.github/workflows/ci.yml` — the actual, current production process/CI conventions this plan's systemd/env-var/migration steps must match exactly, not assume.
- `app/Makefile`'s `shopify-worker` target (phase 5, implemented) — the exact dev-entrypoint command the new systemd unit's `ExecStart` must mirror.
- `app/beyo_manager/config.py` — exact Shopify/encryption setting names, defaults, and the `_require_critical_settings` validator's `required` list, to confirm no Shopify setting is critical-at-boot.
- `app/beyo_manager/routers/api_v1/health.py` — exact current `/health` implementation, to confirm no `/ready`/`/live` exists and no Shopify-specific change is needed.
- `app/beyo_manager/services/infra/shopify/oauth_client.py`, `services/commands/shopify/_redirect.py` (phase 2, implemented) — exact usage of `shopify_redirect_uri` vs. `shopify_oauth_redirect_url`, to document the Shopify dashboard checklist correctly rather than guessing which setting Shopify's dashboard needs.
- `app/beyo_manager/services/commands/shopify/remove_shopify_webhooks_for_shop.py`'s `_build_callback_url()` (phase 3, implemented), `domain/shopify/webhook_registry.py`'s `SHOPIFY_WEBHOOK_CALLBACK_PATH` (phase 1, implemented) — exact webhook callback URL construction this plan's dashboard checklist documents.
- `app/migrations/versions/` (heads only, via a repo-wide search for `down_revision` references) — to confirm the current, non-forked migration chain before finalizing the migration validation section.
- Once phase 6 is implemented: `routers/api_v1/shopify.py` (extended), `domain/shopify/results.py`, `domain/shopify/serializers.py`, `services/queries/shopify/`, `services/commands/shopify/disconnect_shopify_shop.py` and the manual-sync commands, and phase 6's own migration file — to fill in "Phase 6 implementation dependencies to verify before approval" with confirmed facts, exactly as every prior phase transition in this series has done.

### Skill selection

- Primary skill: `none`
- Router trigger terms: `none`
- Excluded alternatives: `skills/cross_cutting/intention_planning/SKILL.md` — source intention already exists.

### Contracts intentionally not selected for this child

- `06_commands.md`, `07_queries.md`, `07_queries_local.md`, `09_routers.md`, `46_serialization.md`: No new command, query, route, or serializer code — this phase is deployment/validation only.
- `03_models.md`: No new table (only a documentation-only migration correction if strictly required, per Scope).
- `28_roles_permissions.md`: No new permission logic — this phase validates phase 2/6's existing role gating, it does not define new roles.
- `08_domain.md`, `24_multi_tenancy.md`, `25_soft_delete.md`: No new domain logic, workspace-scoping logic, or soft-delete logic — this phase validates existing behavior only.
- `13_sockets.md`, `56_realtime_layer.md`, `34_file_storage.md`, `20_api_versioning.md`: Not relevant to deployment/validation.
- `05_errors.md`: No new error classes introduced by this phase.

## Implementation plan

1. Phase 6 and phase 6.1 verification is complete (see "Phase 6 implementation dependencies to verify before approval" and "Phase 6.1 implementation dependencies verified") — all routes/serializers/queries/commands/migration-revision facts are confirmed against the actual implemented and archived code, including phase 6's minor `ctx.session.get()`-then-check style note and phase 6.1's accepted event-type-filtering deviation.

2. Add `managerbeyo-shopify-worker` to `.github/workflows/deploy.yml`'s `sudo systemctl restart` service list, per "Resolved decisions" items 1-2. No other line in `deploy.yml` is modified.

3. Write the operator-facing systemd unit documentation (in this plan's own "Deployment runbook" content, not a new repo file) for `/etc/systemd/system/managerbeyo-shopify-worker.service`, mirroring the Makefile `shopify-worker` target adapted to `APP_ENV=production`, the confirmed production working directory (`/var/www/managerbeyo-backend/app`), and the confirmed production virtualenv (`.venv/bin/python`), per "Resolved decisions" item 3.

4. Write the environment variable checklist (ten settings, per Acceptance criteria item 3), explicitly marking each as "required before first real Shopify use," never "required at boot," per "Resolved decisions" item 5.

5. Write the Shopify Partner Dashboard configuration checklist (App URL, allowed redirection URL derived from `SHOPIFY_REDIRECT_URI`, webhook callback URL derived from `SHOPIFY_WEBHOOK_BASE_URL` + `SHOPIFY_WEBHOOK_CALLBACK_PATH`, required scopes from `SHOPIFY_APP_SCOPES`, API version from `SHOPIFY_API_VERSION`), per "Resolved decisions" items 6-7. No secret value is written into this checklist, only field names and derivation logic.

6. Migration validation section written (`alembic heads`/`current`/`upgrade head`), naming all three confirmed Shopify migrations in chain order (`677ed7131bb2` -> `c3f7a9d2e4b1` -> `ab12cd34ef56`), per "Deployment runbook" above.

7. Queue/task validation section written (task type existence, `queue:shopify`-only routing, all four enqueue boundaries), reusing phases 2-6.1's own existing tests as the validation mechanism rather than authoring new tests, per Acceptance criteria item 6.

8. HTTP route validation section written (webhook route path/HMAC, OAuth callback HMAC/state, install-url/admin-route/webhook-history JWT/role gating), per Acceptance criteria item 7, with all seven admin/history route paths confirmed.

9. No-secret logging validation checklist written, reusing the exact blocked-term lists already established by phases 2-6.1's own boundary-guard/logging/metadata-filter tests, per Acceptance criteria item 8.

10. 18-step first-shop smoke runbook written, each step naming an exact route/table/task type/log line to check, including phase 6.1's new step 17 (webhook-history endpoint check).

11. Write the rollback notes section (code rollback, worker stop/restart with the duplicate-consumer caution, env var rollback, migration risk, disabled-integration state, already-installed-in-Shopify subscriptions), per Acceptance criteria item 10.

12. Write the master-plan closure step as documentation only (update master plan status if lifecycle rules allow at implementation time, add a final intention-plan progress note, document remaining deferred Shopify work — product/order business processing and historical imports by name) — described as a *future implementation step* in this draft, not performed now.

## Deployment runbook (verified content)

This section contains the actual checklists/runbook Implementation plan steps 3-11 produce, now written against confirmed phase 1-6.1 facts rather than left as a description of future work.

### Environment variable checklist

None of the following are in `_require_critical_settings`'s `required` list — the app boots without them. Each is "required before first real Shopify use," not "required to boot":

| Setting | Required before |
|---|---|
| `SHOPIFY_CLIENT_ID` | Generating any install/reauthorize URL |
| `SHOPIFY_CLIENT_SECRET` | OAuth token exchange (callback) |
| `SHOPIFY_APP_SCOPES` | Generating any install/reauthorize URL |
| `SHOPIFY_REDIRECT_URI` | Generating any install/reauthorize URL — **must exactly match the Shopify Partner Dashboard's "Allowed redirection URL(s)"** |
| `SHOPIFY_API_VERSION` | Any Shopify GraphQL call (phase 3 sync/remove) |
| `SHOPIFY_WEBHOOK_BASE_URL` | Webhook subscription creation (phase 3) — combines with `SHOPIFY_WEBHOOK_CALLBACK_PATH` to form the callback URL Shopify sends webhooks to |
| `SHOPIFY_INTEGRATION_DEBUG_LOGS` | Optional, defaults `False` — gates safe debug-level metadata logs only, never secrets |
| `SHOPIFY_WEBHOOK_SECRET` | Inbound webhook HMAC verification (`/api/v1/shopify/webhooks`) |
| `SHOPIFY_OAUTH_REDIRECT_URL` | Post-callback browser redirect — a **ManagerBeyo frontend** URL, never sent to Shopify, no dashboard counterpart |
| `FIELD_ENCRYPTION_KEY` | Encrypting/decrypting `access_token_encrypted` — required before the first successful OAuth callback persists a token |

### Shopify Partner Dashboard configuration checklist

- **Allowed redirection URL(s):** must equal `SHOPIFY_REDIRECT_URI` exactly (not `SHOPIFY_OAUTH_REDIRECT_URL` — see "Resolved decisions" item 6).
- **Webhook callback URL(s):** created automatically by phase 3's `webhookSubscriptionCreate` GraphQL calls, not manually entered — always resolves to `<SHOPIFY_WEBHOOK_BASE_URL>/api/v1/shopify/webhooks` (`SHOPIFY_WEBHOOK_CALLBACK_PATH` is a fixed constant, confirmed matching phase 4's registered route exactly).
- **Required scopes:** must match `SHOPIFY_APP_SCOPES` (comma-separated), which must cover every `required_scopes` value in `domain/shopify/webhook_registry.py`'s `SHOPIFY_WEBHOOK_REGISTRY`.
- **API version:** should track `SHOPIFY_API_VERSION` (default `2026-01`); Shopify deprecates versions on a rolling schedule, so this must be revisited periodically, not just at first deploy.
- No secret value is ever written into this checklist or any dashboard screenshot committed to the repo.

### Systemd unit (operator-created on the EC2 host; not a repo file)

```ini
# /etc/systemd/system/managerbeyo-shopify-worker.service
[Unit]
Description=ManagerBeyo Shopify Worker
After=network.target

[Service]
Type=simple
WorkingDirectory=/var/www/managerbeyo-backend/app
EnvironmentFile=/home/ubuntu/config/managerbeyo/.env
Environment=APP_ENV=production
ExecStart=/var/www/managerbeyo-backend/app/.venv/bin/python -m beyo_manager.workers.shopify_worker
Restart=always
RestartSec=5
User=ubuntu

[Install]
WantedBy=multi-user.target
```

This mirrors the Makefile's `shopify-worker` target (`PYTHONPATH=. APP_ENV=development python -m beyo_manager.workers.shopify_worker`) adapted to the production working directory/virtualenv `deploy.yml` itself already uses for the backend service, with `APP_ENV=production` and a `Restart=always` policy (matching this codebase's dedicated-worker pattern, not verified line-by-line against an existing unit since none is tracked in-repo — see "Resolved decisions" item 3).

### Migration validation

Confirmed chain, no fork: `677ed7131bb2_create_shopify_integration_foundation` (phase 1) -> `c3f7a9d2e4b1_add_shopify_execution_task_types` (phase 5) -> `ab12cd34ef56_add_disconnect_to_shopify_integration_event_type` (phase 6, confirmed current head).

- `alembic heads`: expect exactly one head, `ab12cd34ef56`.
- `alembic current` (staging, then production): must match `ab12cd34ef56` before the corresponding code deploy, per `33_deployment.md`'s promotion order.
- `alembic upgrade head`: applies all three additive `ALTER TYPE ... ADD VALUE IF NOT EXISTS` migrations cleanly; does not touch the pre-existing, explicitly-excluded `workspace_roles`/`email_sync_states` drift phase 1's own review already found and left alone.

### Queue/task validation

- `TaskType` contains `SHOPIFY_PROCESS_WEBHOOK`, `SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP`, `SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP`, `SHOPIFY_RECONCILE_SHOP` — all four route to `queue:shopify` only (`QUEUE_MAP`), and no non-Shopify type shares that queue.
- `workers/shopify_worker.HANDLER_MAP` registers exactly these four types (two pointing at the identical sync handler function) and no others.
- Four enqueue boundaries, each verified by existing tests (reused, not re-authored): post-OAuth sync (`_webhook_sync.record_webhook_sync_pending`), webhook-intake process (`enqueue_or_record_shopify_webhook`, `RECEIVED`-only), manual admin sync (`enqueue_shopify_webhook_sync_for_shop`/`_for_workspace`), disconnect (`disconnect_shopify_shop`).

### HTTP route validation

| Route | Auth | Expected boundary behavior |
|---|---|---|
| `POST /api/v1/shopify/webhooks` | None (Shopify HMAC only) | Rejects invalid/missing HMAC before any DB write; exists at exactly this path, not under `/api/v1/integrations/shopify` |
| `GET /api/v1/integrations/shopify/oauth/callback` | None (Shopify HMAC/state only) | Rejects invalid/missing HMAC or unrecognized/consumed state |
| `POST /api/v1/integrations/shopify/install-url` | JWT, `ADMIN`/`MANAGER` | Rejects `WORKER`/`SELLER` (`403`) before command logic |
| `GET /api/v1/integrations/shopify/shops` | JWT, `ADMIN`/`MANAGER` | Workspace-scoped list; rejects `WORKER`/`SELLER` |
| `GET /api/v1/integrations/shopify/shops/{id}` | JWT, `ADMIN`/`MANAGER` | Workspace-scoped detail; rejects `WORKER`/`SELLER` |
| `POST /api/v1/integrations/shopify/shops/{id}/reauthorize-url` | JWT, `ADMIN`/`MANAGER` | Rejects `WORKER`/`SELLER` |
| `DELETE /api/v1/integrations/shopify/shops/{id}` | JWT, `ADMIN` only | Rejects `MANAGER`/`WORKER`/`SELLER` |
| `POST /api/v1/integrations/shopify/shops/{id}/webhooks/sync` | JWT, `ADMIN` only | Rejects `MANAGER`/`WORKER`/`SELLER` |
| `POST /api/v1/integrations/shopify/webhooks/sync` | JWT, `ADMIN` only | Rejects `MANAGER`/`WORKER`/`SELLER` |
| `GET /api/v1/integrations/shopify/scopes` | JWT, `ADMIN`/`MANAGER` | Rejects `WORKER`/`SELLER` |
| `GET /api/v1/integrations/shopify/shops/{id}/webhooks/history` | JWT, `ADMIN`/`MANAGER` | Workspace-scoped; rejects `WORKER`/`SELLER`; response excludes `raw_payload`; unsafe `metadata_json` keys filtered; `webhook_history_records_pagination` present; not reachable under `/api/v1/shopify/webhooks` |

### No-secret logging / response validation

No log line or response body anywhere in the Shopify surface may contain: a decrypted or encrypted access token value, `shopify_client_secret`, `shopify_webhook_secret`, a raw OAuth authorization `code`, a raw webhook/GraphQL payload body, an HMAC/signature value, or an internal exception traceback. `SHOPIFY_INTEGRATION_DEBUG_LOGS` gates safe metadata only (shop domain, topic, outcome) — confirmed unchanged since phase 4. Phase 6.1's `_filter_safe_metadata` additionally strips any `metadata_json` key containing `token`/`secret`/`hmac`/`signature`/`authorization`/`code`/`raw_payload`/`payload`/`raw_response`/`provider_response` before any history response leaves the backend.

### First-shop smoke runbook (18 steps)

1. Set all ten env vars in the target environment's secret manager (see checklist above).
2. Deploy backend code (`git pull`, `pip install -r requirements.txt`).
3. Run `alembic upgrade head` — confirm `ab12cd34ef56` is now current.
4. Restart `managerbeyo-backend` (and other existing services already in `deploy.yml`'s restart list).
5. Restart `managerbeyo-shopify-worker` (new — this plan's systemd unit).
6. `GET /health` returns `200`/`{"status": "ok"}`.
7. `POST /api/v1/integrations/shopify/install-url` (as `ADMIN`/`MANAGER`) returns an install URL.
8. Complete Shopify OAuth in a browser using that URL against a real or development store.
9. `GET /api/v1/integrations/shopify/shops/{id}` shows `status: "active"` for the new shop.
10. Confirm exactly one `SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP` `ExecutionTask` was created (post-OAuth boundary).
11. Confirm `managerbeyo-shopify-worker`'s logs show that task transitioning to `COMPLETED`.
12. `GET /shops/{id}` (or the webhook subscription summary within it) shows installed/`ACTIVE` subscriptions for the registry's enabled, scope-covered topics.
13. Send or simulate a real webhook delivery (e.g. a test `orders/create` event) to `POST /api/v1/shopify/webhooks`.
14. Confirm a `ShopifyWebhookIntake` row was created with `status="received"`.
15. Confirm exactly one `SHOPIFY_PROCESS_WEBHOOK` `ExecutionTask` was created.
16. Confirm the worker's logs show that task transitioning the intake row to `PROCESSED`.
17. **(new, phase 6.1)** `GET /shops/{id}/webhooks/history` (as `ADMIN`/`MANAGER`) — confirm the received/processed webhook appears in `webhook_history_records`; confirm `webhook_history_records_pagination` is present; confirm no `raw_payload` key anywhere in the response; confirm any `metadata_json` on event records contains only safe fields (no token/secret/HMAC/code-shaped values).
18. `GET /shops`, `GET /shops/{id}`, and `GET /scopes` all return safe results (no `access_token_encrypted`, no OAuth state, no secret) for the newly connected shop.

### Rollback notes

- **Code rollback (no schema change):** redeploy the previous release tag; confirm `GET /health` returns `200`.
- **Worker stop/restart:** `sudo systemctl restart managerbeyo-shopify-worker`; a brief window where two processes both hold a `blpop` on `queue:shopify` is tolerable, not catastrophic — every Shopify handler is idempotent (phase 5's own idempotency tests cover `SHOPIFY_PROCESS_WEBHOOK`; sync/remove handlers delegate to phase 3 commands that re-fetch and reconcile state rather than blindly re-apply).
- **Env var rollback:** safe to unset/revert at any time — no Shopify setting is critical-at-boot, so removing one only disables the corresponding feature (install URL, webhook verification, etc.), it does not crash the app.
- **Migration risk:** none of the three Shopify migrations is destructive (`ALTER TYPE ... ADD VALUE IF NOT EXISTS` only) — `alembic downgrade` is never required or recommended; an application rollback can safely run against a database that already has the new enum values, per `33_deployment.md`'s standard additive-migration rollback story.
- **Disabled-integration state:** a shop disconnected via `DELETE /shops/{id}` stays `status=DISABLED`, visible in `GET /shops`, not hard-deleted — no rollback action needed for this state, it is the intended terminal state of a deliberate admin action.
- **Already-installed-in-Shopify webhook subscriptions surviving a ManagerBeyo-side rollback:** if ManagerBeyo's app code is rolled back after webhook subscriptions were already created via phase 3's GraphQL calls, those subscriptions remain active on Shopify's side and will continue delivering to `/api/v1/shopify/webhooks` — this is safe (the route's dedupe/HMAC logic is unchanged by any rollback scenario this plan anticipates) but should be confirmed post-rollback via `GET /shops/{id}` if one is available on the rolled-back version.

## Risks and mitigations

- Risk: This plan was originally drafted against an approved-but-unimplemented phase-6 design; phase 6's actual route paths, serializer field names, or migration revision ID could have differed.
  Mitigation: The dedicated "Phase 6 implementation dependencies to verify before approval" and "Phase 6.1 implementation dependencies verified" sections have since been checked against the real, archived phase-6/6.1 code and their implemented summaries (`2026-07-09`) — every assumed name matched, with one deliberate positive deviation (phase 6.1's event-type filtering) and one minor style-only deviation (phase 6's `ctx.session.get()`-then-check pattern in three commands) both documented, neither blocking.
- Risk: An operator (or a future automated deploy step) creates the `managerbeyo-shopify-worker.service` unit incorrectly — wrong working directory, wrong `APP_ENV`, or missing `Restart=` policy — causing the worker to silently not run or crash-loop.
  Mitigation: The systemd unit documentation (Implementation plan step 3) specifies the exact `ExecStart`, working directory, and virtualenv, derived from the same production values `deploy.yml` itself already uses for the backend service, not invented values.
- Risk: Two `managerbeyo-shopify-worker` processes end up consuming `queue:shopify` simultaneously during a rolling restart, double-processing a task (mitigated by the queue's `PENDING`/`IN_PROGRESS` state machine and stale-task recovery, but still worth calling out operationally).
  Mitigation: Rollback notes (Acceptance criteria item 10) explicitly document this scenario and note that `worker_base.py`'s existing idempotency/state-machine guarantees (unchanged by this phase) already make duplicate delivery safe for every Shopify handler (phase 5's own idempotency tests cover this), so a brief dual-consumer window during restart is tolerable, not catastrophic.
- Risk: The env var checklist is misread as "these must be set before the app boots," causing an unnecessary deploy blocker or, worse, someone adding them to `_require_critical_settings`'s `required` list against explicit instruction.
  Mitigation: "Resolved decisions" item 5 and Acceptance criteria item 3 state this explicitly and verify the actual `required` list is unchanged; the checklist's own wording distinguishes "required before first real Shopify use" from "required to boot" for every entry.
- Risk: The Shopify Partner Dashboard checklist gets a redirect URL wrong (confusing `SHOPIFY_REDIRECT_URI` with `SHOPIFY_OAUTH_REDIRECT_URL`), causing Shopify to reject every OAuth attempt with a redirect-URI-mismatch error that is confusing to debug in production.
  Mitigation: "Resolved decisions" item 6 documents the exact distinction, grounded in phase 2's actual code (`oauth_client.py` vs. `_redirect.py`), not assumption.
- Risk: The now-three-times-carried-forward DB-backed validation gap (phase 5 -> phase 6 -> phase 6.1) is mistaken for "already handled" and this plan's own implementation skips running it, deploying Shopify code that has only ever passed `py_compile`/pure-unit tests against a live database.
  Mitigation: "Phase 6 implementation dependencies to verify before approval" and "Phase 6.1 implementation dependencies verified" both explicitly flag this as outstanding, not resolved; the Validation plan below makes this phase's own `alembic upgrade head` + full Shopify integration-test run the one pass that finally closes it, and Acceptance criteria item 12 makes this an explicit, named requirement rather than an assumption.

## Validation plan

- Phase 6 and phase 6.1 verification sections (this plan's own dependency sections) confirmed complete before implementation starts (done — see above).
- `alembic heads`: reports exactly one head, `ab12cd34ef56` (chain: `677ed7131bb2` -> `c3f7a9d2e4b1` -> `ab12cd34ef56`, confirmed non-forked).
- `alembic current` (staging, then production per `33_deployment.md`'s promotion order): matches `ab12cd34ef56` before the corresponding code deploy.
- `alembic upgrade head` (staging, then production): applies cleanly; **this is the run that finally closes the phase-5/6/6.1 carried-forward DB-backed validation gap** — the first time any of these three phases' migrations and integration test suites are validated against a live database in this series.
- `pytest` for the full impacted Shopify suite (phases 1-6.1: domain, infra, router, query, command, and worker tests, including `test_shopify_admin_queries.py`, `test_shopify_admin_commands.py`, and `test_shopify_webhook_history_query.py`, none of which have run against a live Postgres yet): all pass.
- `GET /health` (staging, then production, post-deploy): returns `200`/`{"status": "ok", "services": {"db": "ok", "redis": "ok"}}` — no Shopify-specific check exists or is added, per "Resolved decisions" item 4.
- `sudo systemctl status managerbeyo-shopify-worker` (production, post-deploy): reports `active (running)`, with startup logs showing the worker registered on `queue:shopify` (matching phase 5's `worker.start`-style structured log, per `51_worker_runtime.md`).
- Queue/task validation: reuse phases 2-6.1's own existing boundary-connection tests as the validation mechanism — no new test file is authored by this phase.
- HTTP route validation: manual/scripted checks against staging (or documented as a production-safe smoke check) for webhook-route HMAC rejection, OAuth-callback HMAC/state rejection, and JWT/role gating on install-url, all six phase-6 admin routes, and phase 6.1's webhook-history route.
- First-shop smoke runbook (18 steps, per "Deployment runbook" above): executed once against a real or sandbox Shopify development store in staging before being trusted for production use.
- No-secret logging spot check: grep staging/production logs for token-shaped or secret-shaped strings across a full first-shop-connection smoke run, including the webhook-history endpoint's response body — zero matches expected.

## Review log

- `2026-07-09` `Codex`: Drafted seventh and final child implementation plan (Shopify deployment and validation) as a companion to phase 6, which is approved but not yet implemented. Grounded every deployment fact (production process manager, env var criticality, health endpoint shape, OAuth redirect setting distinction, webhook callback URL construction, migration chain) in direct inspection of this repository's actual `deploy.yml`, `ci.yml`, `Procfile`, `config.py`, `health.py`, and phases 1-5's already-implemented OAuth/webhook code, rather than the generic architecture contract's illustrative examples — most notably finding that `31_health_observability.md`'s three-endpoint (`/health`/`/ready`/`/live`) model is not actually implemented in this codebase (only `/health` exists) and choosing not to add the missing endpoints, since that would be new feature behavior outside this phase's config/process-wiring mandate. Left in `under_construction` pending phase-6 verification (the structural blocker) — no other open clarification exists.
- `2026-07-09` `User/GPT review, Stage 1 (phase 6)`: Reviewed the archived phase-6 plan, its implemented summary, and the actual code (`domain/shopify/enums.py`, the `ab12cd34ef56` migration, `domain/shopify/results.py`/`serializers.py`, all three query files, all four command files, `routers/api_v1/shopify.py`, and the phase-6 test files). Verdict: **approved with minor follow-up** — no critical issues; route paths, role gating (`ADMIN`/`MANAGER` view vs. `ADMIN`-only disconnect/sync), workspace isolation, serializer no-secret behavior, disconnect soft-state/token-clearing/`DISCONNECT`-event/enqueue behavior, manual-sync enqueue-not-inline behavior, and the additive `DISCONNECT` migration all confirmed correct and matching the archived plan, verified directly against `disconnect_shopify_shop`'s own integration test. One minor, non-blocking style deviation found: three commands (`disconnect_shopify_shop`, `create_shopify_reauthorize_url`, `enqueue_shopify_webhook_sync_for_shop`) resolve their target row via `ctx.session.get()` + a manual workspace check rather than a `WHERE workspace_id=...` filter the query files use — functionally safe (no IDOR), just stylistically inconsistent. DB-backed integration tests could not run live (local Postgres on port `5433` unreachable in Codex's session) — a non-blocking, carried-forward gap, not a code defect.
- `2026-07-09` `User/GPT review, Stage 2 (phase 6.1)`: Reviewed the archived phase-6.1 plan, its implemented summary, and the actual code (`domain/shopify/results.py`/`serializers.py` extensions, `get_shopify_webhook_history_records.py`, the new router route, and the phase-6.1 test files). Verdict: **approved with minor follow-up** — no critical issues; exact route path confirmed reachable only under `/api/v1/integrations/shopify` (not the external webhook prefix), `ADMIN`/`MANAGER`-allowed/`WORKER`/`SELLER`-rejected role gating confirmed, workspace-scoped-then-`NotFound` lookup confirmed, `limit`/`offset`/`limit+1`/`has_more` pagination confirmed, newest-first `(timestamp, client_id)` sort confirmed, `raw_payload` exclusion and `_filter_safe_metadata`'s ten-substring defensive filtering both confirmed and directly unit-tested. One deliberate, accepted deviation from the approved plan found: the query filters `ShopifyIntegrationEvent` rows to a `WEBHOOK_HISTORY_EVENT_TYPES` allow-list (`WEBHOOK_SYNC`/`WEBHOOK_RECEIVED`/`WEBHOOK_PROCESSED`/`DISCONNECT`) rather than including every event type as originally planned — a sensible improvement, not a defect, since it keeps the "webhook history" feed's contents matching its name. Same DB-backed validation gap as phase 6 (same unreachable-Postgres blocker), not a new issue.
- `2026-07-09` `User/GPT review, Stage 3 (phase 7 update)`: Replaced all assumed phase-6 facts in "Phase 6 implementation dependencies to verify before approval" with confirmed facts, and added a new "Phase 6.1 implementation dependencies verified" section. Added the actual "Deployment runbook (verified content)" section — environment variable checklist, Shopify Partner Dashboard checklist, the systemd unit file content, the confirmed three-migration chain, queue/task validation, a full HTTP route validation table (including phase 6.1's history route), no-secret logging/response validation (including `_filter_safe_metadata`'s ten blocked substrings), and the expanded 18-step first-shop smoke runbook (new step 17: webhook-history endpoint check) — since the original draft only described these as future writing tasks rather than containing them. Updated Acceptance criteria, Risks, and Validation plan to reflect the confirmed migration chain and the now-three-times-carried-forward (phase 5 -> 6 -> 6.1) DB-backed validation gap, explicitly folded into this plan's own first live-DB validation pass rather than treated as resolved. No blockers remain — plan moved from `under_construction` to `approved`.
- `2026-07-09` `Claude, implementation`: Implemented the plan's one in-repo change — added `managerbeyo-shopify-worker` to `.github/workflows/deploy.yml`'s `systemctl restart` list, preserving all 8 existing service names and their order. Ran the first-ever live-DB validation pass in this plan series: brought up local Docker Postgres/Redis (`app/docker-compose.yml`), ran `alembic heads`/`current`/`upgrade head` (chain `677ed7131bb2 -> c3f7a9d2e4b1 -> ab12cd34ef56` applied cleanly, single head confirmed), then ran the full Shopify unit suite (83/84 passed; 1 pre-existing Phase 5 test path-bug, unrelated) and the full Shopify DB-backed integration suite (41/47 passed; 6 failed due to a fully root-caused, pre-existing Phase 6/6.1 test-isolation defect — explicit `db_session.commit()` calls inside test files bypassing the shared fixture's rollback-based teardown, combined with fixed literal test domains — invisible in phases 5/6/6.1 because none of those sessions had live DB access; not a Phase 7 regression and out of this phase's scope to fix). Cleaned the colliding leftover rows from the local dev database with explicit user confirmation. This finally closes the phase 5 -> 6 -> 6.1 -> 7 carried-forward DB-validation gap for the migration path, while surfacing (not fixing) a genuine test-isolation defect for a future phase. Wrote the implemented summary (`SUMMARY_shopify_deployment_validation_20260709.md`), appended intention-plan progress notes for phases 6, 6.1, and 7, and archived this plan. This is the seventh and final child plan in the Shopify integration master plan's decomposition — no Phase 8 or further child plans were created.

## Lifecycle transition

- Current state: `archived`
- Next state: `none — final child plan in the Shopify integration series`
- Transition owner: `Claude`
