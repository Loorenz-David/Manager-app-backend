# PLAN_shopify_integration_master_20260707

## Metadata

- Plan ID: `PLAN_shopify_integration_master_20260707`
- Status: `under_construction`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-07T19:40:28Z`
- Last updated at (UTC): `2026-07-07T19:40:28Z`
- Related issue/ticket: `Shopify integration architecture`
- Intention plan: `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`

## Goal and intent

- Goal: Define the full Shopify integration architecture and decompose implementation into safe child plans.
- Business/user intent: Allow ManagerBeyo workspaces to link one or more Shopify shops, manage OAuth/webhooks securely, and process Shopify API/webhook work through the existing execution layer with a dedicated Shopify queue/worker path.
- Non-goals: This master plan is not implemented directly; it does not create code, migrations, routes, workers, or deployment scripts. Automatic historical product/order imports are explicitly out of scope for phase one.

## Scope

- In scope:
  - Full phase order, dependency graph, shared architectural rules, contract selections, and acceptance gates.
  - Child phase definitions for foundation, OAuth, webhook subscription sync, webhook intake/enqueue, dedicated worker execution, admin routes/serializers, and deployment/validation.
  - Shared security rules for encrypted offline access tokens, OAuth state, webhook HMAC verification, logging redaction, workspace isolation, and one active integration per Shopify shop domain globally.
- Out of scope:
  - Direct implementation.
  - Remaining child implementation plans after the first foundation child.
  - Frontend UI implementation.
  - Product/order historical import jobs after OAuth.
  - A separate DTO architecture; serialized frontend shapes must use the existing domain serializer pattern.
- Assumptions:
  - The application package is `app/beyo_manager`.
  - Shopify Admin API work should prefer GraphQL.
  - Shopify offline Admin API tokens require `access_token_encrypted` only; no `refresh_token_encrypted` unless a future selected token model proves refresh tokens are required.
  - A single generic Shopify webhook endpoint will be used in the webhook phase; topic routing comes from Shopify headers and the central domain registry.

## Clarifications required

- [ ] Confirm the encryption primitive/key source for `access_token_encrypted` — blocks safe token storage implementation, but not foundation planning.
- [ ] Confirm exact role/permission names for "admin can disconnect/sync" and "admin or manager can link" — blocks route authorization in later admin/OAuth plans.
- [ ] Resolve serialization contract precedence: `07_queries.md` says queries serialize, while `46_serialization.md` says services return dataclasses and routers call domain serializers. This plan follows the intention plan and `46_serialization.md` for Shopify response shapes.

## Acceptance criteria

1. Future child plans can implement the Shopify integration in small, reviewable phases without re-deciding architecture.
2. Every child phase has owners, non-owners, required contracts, dependencies, file areas, acceptance criteria, validation expectations, and drift-prevention notes.
3. Shared rules prevent business logic in routers, direct external calls outside infra, unencrypted token storage, raw webhook payload logging, and blocking webhook processing.
4. The first child plan is `PLAN_shopify_foundation_schema_config_20260707.md` and no other child plans are created yet.

## Contracts and skills

### Contracts loaded

- `architecture/01_architecture.md`: Layer dependency rules; routers are I/O only, commands write, queries read, domain is pure, infra owns external adapters.
- `architecture/04_context.md`: ServiceContext identity/session boundaries for future commands and queries.
- `architecture/05_errors.md`: Safe domain errors and error boundary behavior for Shopify OAuth/webhook/API failures.
- `architecture/06_commands.md`: Write-operation structure for OAuth linking, webhook sync, disconnect, intake creation, and enqueue commands.
- `architecture/07_queries.md`: Read-operation structure and workspace-first filtering for admin Shopify list/detail/scope queries.
- `architecture/09_routers.md`: Router boundaries and route registration expectations for admin and webhook routes.
- `architecture/21_naming_conventions.md`: Table, route, env, command, query, serializer, index, and file naming rules.
- `architecture/40_identity.md`: `client_id` identity model and FK strategy for all addressable Shopify tables.
- `architecture/41_user.md`: User FK/audit pattern for `created_by_id` and `updated_by_id`.
- `architecture/42_event.md`: Event/audit pattern and execution linkage used by Shopify integration events where appropriate.
- `architecture/48_presence.md`: Core contract selected by guide; no direct Shopify work expected.
- `architecture/03_models.md`: SQLAlchemy 2.x model, relationship, enum, index, and table import constraints.
- `architecture/08_domain.md`: Pure domain rules for enums, scope comparison, shop domain normalization, webhook registry definitions, and serializers.
- `architecture/30_migrations.md`: Alembic migration generation/review and zero-downtime schema rules.
- `architecture/15_testing.md`: Test tier and folder expectations for domain, model/constraint, command, route, and worker tests.
- `architecture/16_background_jobs.md`: Execution task, payload, queue map, task router, handler, and worker rules for Shopify deferred work.
- `architecture/12_infra_redis.md`: Redis queue/key constraints; Redis is transport only, not Shopify durable state.
- `architecture/51_worker_runtime.md`: Dedicated worker lifecycle, explicit task registration, idempotency, graceful shutdown, and worker logs.
- `architecture/49_observability_runtime.md`: Structured runtime logs, correlation propagation, worker observability, and health diagnostics.
- `architecture/54_ci_cd_runtime.md`: CI validation order for migrations, startup, health/readiness, and runtime wiring.
- `architecture/33_deployment.md`: EC2/deploy ordering, env var promotion, worker registration, rollback, and smoke checks.
- `architecture/31_health_observability.md`: Health/readiness expectations and non-checking of external providers in `/health`.
- `architecture/46_serialization.md`: Domain result/serializer pattern for frontend-facing Shopify response shapes.
- `architecture/17_logging.md`: Module loggers, required context, external-call logging, and forbidden secrets/raw payloads.
- `architecture/18_security.md`: Webhook HMAC verification, boundary validation, IDOR prevention, CORS/secrets rules.
- `architecture/19_integrations.md`: External adapter pattern, timeout/retry rules, webhook receipt pattern, and no direct provider SDK scatter.
- `architecture/24_multi_tenancy.md`: Workspace ownership, workspace-scoped domain data, and membership-based authorization.
- `architecture/25_soft_delete.md`: Soft-delete semantics for unlinking/disabled Shopify integration rows.

### Local extensions loaded

- `architecture/06_commands_local.md`: Use `maybe_begin` only when Shopify commands become composable; no manual commit/rollback inside it.
- `architecture/07_queries_local.md`: Use offset pagination for list queries instead of cursor pagination.
- `architecture/40_identity_local.md`: Existing prefix reservations must be checked before choosing Shopify model prefixes.
- `architecture/41_user_local.md`: No Shopify-specific local delta.
- `architecture/42_event_local.md`: No Shopify-specific local delta.
- `architecture/48_presence_local.md`: No Shopify-specific local delta.
- `architecture/46_serialization_local.md`: No Shopify-specific local delta.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** -> read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** -> reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape -> `06_commands.md`
- Reading another router to understand handler wiring -> `09_routers.md`
- Reading another serializer to understand output shape -> `46_serialization.md`

Permitted (relational reads — understanding what exists):
- Reading `app/beyo_manager/config.py` for settings names and config class structure.
- Reading `app/beyo_manager/models/__init__.py` and related table files for import paths, existing mixins, FK names, and workspace/user table names.
- Reading execution-layer files for current task enum, queue map, task factory, payload, and worker entrypoint wiring before Shopify execution phases.
- Reading migration heads and recent migrations to avoid branch drift and naming conflicts.

### Skill selection

- Primary skill: `none`
- Router trigger terms: `none`
- Excluded alternatives: `skills/cross_cutting/intention_planning/SKILL.md` — request is implementation planning from an existing intention, not creation of a new intention plan.

### Contract selection notes

- Selected from guide core: all core contracts are required by the local guide.
- Added CRUD/foundation contracts: `03_models.md`, `08_domain.md`, `30_migrations.md`, `15_testing.md`, `46_serialization.md`, `24_multi_tenancy.md`, `25_soft_delete.md`.
- Added worker/runtime contracts: `16_background_jobs.md`, `12_infra_redis.md`, `51_worker_runtime.md`, `49_observability_runtime.md`.
- Added deployment/runtime contracts: `33_deployment.md`, `31_health_observability.md`, `54_ci_cd_runtime.md`.
- Added security/integration/logging contracts: `17_logging.md`, `18_security.md`, `19_integrations.md`.
- Intentionally not selected now:
  - `13_sockets.md`, `56_realtime_layer.md`: Shopify phase one has no realtime/socket UI requirement.
  - `34_file_storage.md`: Raw webhook payload remains in Postgres intake for early implementation; S3/object storage is future work.
  - `18 rate limit trigger expansion beyond security`: Webhook endpoints must not be app-rate-limited; infrastructure WAF/rate limits can be handled outside this plan.
  - `52_replayability.md`, `53_operational_cli.md`: Useful later for replay/admin tooling, but not required for the first child plan or minimum phase-one architecture.
  - `55_query_filters_local.md`: Admin Shopify list filters are simple initially.
  - `22_performance.md`, `32_concurrency.md`: No bulk import or high-contention sync is included in phase-one implementation.

## Implementation plan

1. Child phase 1: `PLAN_shopify_foundation_schema_config_20260707.md`
   - Owns: settings/config fields, SQLAlchemy models, Alembic migration, indexes/constraints, encrypted token field strategy, domain enums, scope normalization/comparison helpers, central webhook registry definitions, optional serializer placeholder, logging flag definition, and foundation tests.
   - Must not touch: OAuth routes/callback/token exchange, Shopify GraphQL execution, webhook HTTP route, webhook subscription API calls, workers, task handlers, admin routes, frontend UI, or historical imports.
   - Required contracts: `01`, `03`, `08`, `21`, `30`, `40`, `41`, `42`, `46`, `15`, `17`, `18`, `24`, `25`.
   - Dependencies: Intention plan and this master plan only.
   - Expected files/areas: `app/beyo_manager/config.py`, `app/beyo_manager/domain/shopify/`, `app/beyo_manager/models/tables/shopify/`, `app/beyo_manager/models/__init__.py`, `app/migrations/versions/`, `tests/unit/domain/shopify/`, model/constraint tests if local test conventions support them.
   - Acceptance criteria: Five plural tables exist by model/migration plan, one active shop domain globally is enforceable, workspace can have multiple shops, offline token storage uses `access_token_encrypted` only, OAuth state fields support expiring one-time use, webhook registry includes initial topics, scope helpers normalize/sort/dedupe/compare.
   - Validation expectations: Alembic autogenerate review, upgrade/check where available, focused domain helper tests, table/constraint tests where practical.
   - Risks/drift prevention: Do not start implementing OAuth "because state exists"; do not add refresh token fields unless Shopify token model changes; do not log raw payloads; do not introduce DTO classes outside domain serializers/results.

2. Child phase 2: Shopify OAuth linking flow
   - Owns: install URL command, OAuth state creation/consumption, HMAC/query validation, token exchange orchestration, link/update shop integration command, scope status marking, safe frontend redirect, enqueue of webhook sync after successful link.
   - Must not touch: direct webhook processing, webhook subscription reconciliation internals beyond enqueueing sync, dedicated worker implementation, historical imports.
   - Required contracts: `04`, `05`, `06`, `08`, `09`, `17`, `18`, `19`, `24`, `25`, `46`, plus foundation plan.
   - Dependencies: Phase 1 complete.
   - Expected files/areas: `services/commands/shopify/`, `services/infra/shopify/`, `routers/api_v1/shopify.py` or equivalent integration router, `domain/shopify/serializers.py`, config.
   - Acceptance criteria: OAuth state is expiring, one-time use, workspace/user-bound; install URL accepts normalized shop domains only; token exchange stores encrypted offline token; callback creates/updates one shop integration; redirect exposes only safe status; webhook sync task is enqueued; no historical imports are enqueued.
   - Validation expectations: command tests with mocked Shopify infra, callback validation tests, redirect-safety tests, no-secret logging checks.
   - Risks/drift prevention: Token exchange belongs in infra, not router; callback command owns writes; avoid arbitrary redirect URLs.

3. Child phase 3: Shopify webhook registry and subscription sync
   - Owns: idempotent desired-vs-installed webhook subscription sync, Shopify webhook subscription infra client, subscription table status transitions, install/remove/reconcile commands.
   - Must not touch: inbound webhook HTTP route processing beyond registry definitions, worker process startup except enqueue payload definitions if needed.
   - Required contracts: `06`, `08`, `16`, `17`, `18`, `19`, `30`, plus phases 1-2.
   - Dependencies: OAuth can enqueue sync; foundation subscription model/registry exists.
   - Expected files/areas: `services/commands/shopify/`, `services/infra/shopify/`, `domain/shopify/webhook_registry.py`, `domain/execution/payloads/`.
   - Acceptance criteria: Sync is idempotent for one shop; remove is idempotent; desired definitions are code/config driven; remote subscription IDs/status/errors are persisted; unsupported/disabled topics are not installed.
   - Validation expectations: mocked Shopify GraphQL tests; status transition tests; retryable vs non-retryable error classification.
   - Risks/drift prevention: Do not manually insert webhook definitions from commands; no direct HTTP calls from commands.

4. Child phase 4: Shopify webhook intake and execution enqueue
   - Owns: one generic webhook route, HMAC verification on raw body, topic/header validation, shop integration resolution, intake persistence, dedupe, event recording, enqueue `SHOPIFY_PROCESS_WEBHOOK`, fast response.
   - Must not touch: heavy domain processing, Shopify API calls, subscription installation.
   - Required contracts: `05`, `06`, `08`, `09`, `16`, `17`, `18`, `19`, plus phases 1-3.
   - Dependencies: Foundation intake table and registry; execution task types/payloads available if split with phase 5.
   - Expected files/areas: webhook router, `services/commands/shopify/enqueue_or_record_shopify_webhook.py`, `services/infra/shopify/hmac_verifier.py`, intake/event models.
   - Acceptance criteria: Invalid HMAC rejected; duplicate dedupe key returns 200 without duplicate enqueue; valid supported topic creates intake and enqueue; raw payload is persisted only in intake and never logged; route returns quickly.
   - Validation expectations: HTTP route tests using raw body, HMAC tests, dedupe tests, enqueue assertion tests.
   - Risks/drift prevention: Routers verify/pass raw inputs only; no heavy processing inline; webhook endpoints stay unauthenticated by ManagerBeyo JWT and authenticated by Shopify HMAC.

5. Child phase 5: Dedicated Shopify worker execution
   - Owns: Shopify task types, payload dataclasses, queue map to `queue:shopify`, dedicated worker entrypoint, handler registry, handlers for process webhook/sync/remove/reconcile, idempotency guards, retry/dead-letter behavior, worker logs.
   - Must not touch: admin UI routes except task enqueue dependencies, schema except execution enum migrations if not done earlier.
   - Required contracts: `16`, `12`, `51`, `49`, `17`, `42`, plus phases 1-4.
   - Dependencies: Intake/enqueue commands and webhook sync commands exist.
   - Expected files/areas: `domain/execution/enums.py`, `domain/execution/payloads/shopify.py`, task factory/queue map, `workers/shopify_worker.py`, handler modules.
   - Acceptance criteria: Shopify task types route only to Shopify queue; Shopify worker registers only Shopify handlers; handlers deserialize typed payloads first, use DB task session, delegate business logic to commands/services, and are idempotent.
   - Validation expectations: queue map tests, worker handler registration tests, payload deserialization tests, retry/idempotency tests.
   - Risks/drift prevention: Do not mix Shopify jobs into unrelated workers; no implicit task discovery; no payload mutation.

6. Child phase 6: Shopify admin routes and serializers
   - Owns: frontend-facing routes for listing shops, detail, install URL, reauthorize URL, disconnect, webhook sync, scope status, plus domain results/serializers.
   - Must not touch: worker runtime internals, webhook HMAC route behavior, historical imports.
   - Required contracts: `04`, `05`, `07`, `07_local`, `09`, `24`, `28_roles_permissions.md` if exact permission names are needed, `46`.
   - Dependencies: Foundation, OAuth commands, webhook sync commands, execution enqueue path.
   - Expected files/areas: `routers/api_v1/shopify.py`, `services/queries/shopify/`, `services/commands/shopify/`, `domain/shopify/results.py`, `domain/shopify/serializers.py`.
   - Acceptance criteria: Routes are workspace-scoped; admin/manager permissions match clarified policy; list queries use offset pagination; serializers omit encrypted tokens and internal secrets; disconnect soft-deletes/disables and clears or revokes token where possible.
   - Validation expectations: route tests, permission tests, workspace isolation tests, serializer no-secret tests.
   - Risks/drift prevention: Business logic must not enter routers; queries own reads; commands own writes; no new DTO architecture.

7. Child phase 7: Deployment and validation
   - Owns: env var promotion, EC2 process config for Shopify worker, health/readiness validation for queue/worker registration where appropriate, deployment smoke tests, operational rollback notes.
   - Must not touch: feature behavior except config/process wiring.
   - Required contracts: `33`, `31`, `49`, `54`, `51`, plus all earlier phases.
   - Dependencies: Worker entrypoint and queue map complete.
   - Expected files/areas: EC2/PM2/systemd/process files in repo, deployment docs/scripts, health/readiness validation docs.
   - Acceptance criteria: Required Shopify env vars documented and set before code deploy; Shopify worker can be started/stopped independently; deploy checklist includes migration first for additive schema and worker registration; smoke validation covers OAuth config presence, queue routing, and webhook endpoint availability without external Shopify dependency.
   - Validation expectations: app startup, health/readiness, migration upgrade, worker startup logs, queue binding checks.
   - Risks/drift prevention: Do not check Shopify external API in `/health`; keep env secrets outside source; rollback app before touching DB.

## Shared architecture rules

- Shopify business logic must not live in routers.
- Routers are HTTP input/output only.
- Commands own writes.
- Queries own reads.
- Domain owns enums, pure rules, scope comparison, shop domain normalization, webhook registry definitions, result dataclasses, and serializers.
- Infra owns Shopify API/OAuth/HMAC/token/webhook external communication helpers.
- Shopify webhook/API work must use the existing execution layer when it should not block HTTP.
- Shopify must have a dedicated worker/queue path, e.g. `queue:shopify`.
- Shopify access tokens must be encrypted at rest.
- Raw webhook payloads must not be logged.
- OAuth state must be expiring, one-time use, and workspace/user-bound.
- Webhook routes must verify, persist/dedupe, enqueue, and return quickly.
- Webhook installation/sync after OAuth is required.
- Automatic historical product/order imports are out of scope for phase one.
- Serialized frontend response shapes must use the existing domain serializer pattern, not a new DTO architecture.
- Multiple Shopify shops per workspace must be supported.
- A normalized Shopify shop domain can only have one active integration globally across all workspaces.
- Use offline Shopify access tokens for shop integrations.
- Do not add `refresh_token_encrypted` unless a future selected Shopify token model requires refresh tokens.
- Initial webhook topics: `app/uninstalled`, `orders/create`, `orders/updated`, `orders/paid`, `orders/cancelled`, `products/create`, `products/update`, `products/delete`.

## Future child-plan drift prevention

- Every child plan must list this master plan and all prior completed child plans in its metadata or scope section.
- Every child plan must include a "Previous decisions inherited" subsection summarizing the relevant decisions from earlier plans instead of re-deciding them.
- Child plans must not read unrelated implementation files for patterns already governed by contracts.
- If a child plan needs to change a shared rule here, it must add an explicit "Master-plan deviation requested" entry with the reason and impact.
- Each child plan must keep its scope narrow enough that it can be reviewed and implemented independently.

## Risks and mitigations

- Risk: OAuth, webhook sync, and intake work collapse into one large unsafe implementation.
  Mitigation: Child plans must enforce phase boundaries and list must-not-touch areas.
- Risk: Duplicate processing if one Shopify shop is active in multiple workspaces.
  Mitigation: Foundation schema must enforce one active integration per normalized `shop_domain` globally, excluding inactive/deleted/uninstalled rows.
- Risk: Leaked secrets or merchant payloads.
  Mitigation: Token encryption, redacted structured logs, no raw payload logs, no token fields in serializers.
- Risk: Webhook route timeout causes Shopify retries and duplicates.
  Mitigation: Verify, persist/dedupe, enqueue, return quickly.
- Risk: Execution-layer drift.
  Mitigation: Dedicated Shopify worker/queue must use existing task types, payloads, task factory, queue map, retry, and worker lifecycle contracts.

## Validation plan

- Master-plan review: confirm phase boundaries, dependencies, and shared rules before approving child implementation.
- For each child plan: validate only its scope and inherited decisions.
- For deployment phase: run migration, app startup, health/readiness, worker startup, and queue-binding validation before production rollout.

## Review log

- `2026-07-07` `Codex`: Created master coordination plan from Shopify intention and selected backend contracts.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `Codex`
