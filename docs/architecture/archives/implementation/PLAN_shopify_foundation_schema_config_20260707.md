# PLAN_shopify_foundation_schema_config_20260707

## Metadata

- Plan ID: `PLAN_shopify_foundation_schema_config_20260707`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-07T19:40:28Z`
- Last updated at (UTC): `2026-07-08T06:35:34Z`
- Related issue/ticket: `Shopify integration foundation schema/config/domain`
- Intention plan: `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`
- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_integration_master_20260707.md`

## Goal and intent

- Goal: Add the foundation plan for Shopify settings, schema, migrations, domain enums/helpers, webhook registry definitions, and focused tests.
- Business/user intent: Prepare ManagerBeyo for secure multi-shop Shopify linking without implementing OAuth, webhooks, API execution, workers, routes, UI, or imports yet.
- Non-goals:
  - OAuth route implementation.
  - OAuth callback implementation.
  - Shopify token exchange implementation.
  - Shopify GraphQL request execution implementation.
  - Webhook HTTP route implementation.
  - Webhook subscription API calls to Shopify.
  - Background worker implementation.
  - Background task handler implementation.
  - Admin route implementation.
  - Frontend UI work.
  - Historical product/order imports.
  - Creation of remaining child implementation plans (phases 2-7 of the master plan).

## Scope

- In scope:
  - Shopify settings/config/env fields.
  - SQLAlchemy table models using plural table names.
  - Alembic migration for new tables, enums, indexes, FKs, and constraints.
  - Token storage field strategy with `access_token_encrypted` only.
  - Domain Shopify enums.
  - Scope normalization/comparison helpers.
  - Central Shopify webhook registry definitions.
  - Shopify debug logging config flag definition only, not full logging implementation.
  - Tests for domain helpers and table constraints where appropriate.
- Out of scope:
  - Any HTTP router, OAuth callback, Shopify external API client, webhook route, queue/worker, handler, admin route, frontend work, or historical import.
  - `domain/shopify/results.py` and `domain/shopify/serializers.py` (see Implementation plan step 4).
  - Shopify token encryption/decryption call sites (see Resolved decisions below).
- Assumptions:
  - Use plural table names unless implementation-time model inspection proves a ManagerBeyo convention conflict.
  - Offline Admin API token model stores `access_token_encrypted` and does not store refresh tokens.
  - Raw webhook payload storage is initially in `shopify_webhook_intakes.raw_payload`; future object storage is outside this child.
  - The domain registry is the source of truth for desired webhook topics.

## Resolved decisions

These previously open clarifications are resolved for this child plan and must not be re-opened during implementation.

1. **Token encryption.** The backend already has a field encryption system at `app/beyo_manager/services/infra/crypto/field_encryption.py`, using `FIELD_ENCRYPTION_KEY` via `settings.field_encryption_key` (`app/beyo_manager/config.py`). Shopify token encryption must reuse this existing key/config — do not add a new Shopify-specific encryption key or setting. `access_token_encrypted` is the token storage column (string/text). This child does not implement Shopify token encryption/decryption call sites; that usage belongs to the OAuth/token phase (phase 2). `encrypt_field`/`decrypt_field` may be imported only if strictly required by a test in this child, but no Shopify command/service in this child should call them.
2. **Config structure.** `app/beyo_manager/config.py` defines a single `Settings(BaseSettings)` class using `Field(default=..., alias="ENV_VAR")` per field, grouped under `# <Section>` comments, with `settings = Settings()` at module scope. Add Shopify fields to this same class under a `# Shopify` comment, following the exact same style (see Implementation plan step 3). Shopify fields must not be added to `_require_critical_settings` — the backend must still boot before Shopify is configured.
3. **Client ID prefixes.** The following prefixes are reserved and confirmed free of collision against `app/beyo_manager/models/tables/client_id_prefix_map.md` and all existing `CLIENT_ID_PREFIX` values: `shpint` (`shopify_shop_integrations`), `shpoau` (`shopify_oauth_states`), `shpwhs` (`shopify_webhook_subscriptions`), `shpwhi` (`shopify_webhook_intakes`), `shpevt` (`shopify_integration_events`). Per `IdentityMixin.generate_id` (`app/beyo_manager/models/base/identity.py`), the prefix constant itself must **not** include a trailing underscore — `generate_id` appends `_` automatically (e.g. `CLIENT_ID_PREFIX = "shpint"` produces `shpint_01ARZ...`).

## Clarifications required

None. See Resolved decisions above.

## Acceptance criteria

1. The plan defines five Shopify tables: `shopify_shop_integrations`, `shopify_oauth_states`, `shopify_webhook_subscriptions`, `shopify_webhook_intakes`, and `shopify_integration_events`.
2. Schema supports multiple Shopify shops per workspace and enforces, via partial unique constraints/indexes, one active-like Shopify integration per normalized `shop_domain` globally and one active-like Shopify integration per `workspace_id + shop_domain` (see Implementation plan step 7 for the active-like status set).
3. Token schema stores encrypted offline access tokens using `access_token_encrypted` (string/text) and does not include `refresh_token_encrypted`. Token encryption reuses the existing `FIELD_ENCRYPTION_KEY` / `settings.field_encryption_key`; no new Shopify-specific encryption key is added.
4. OAuth state schema supports expiring, one-time, workspace/user-bound state.
5. Domain helpers normalize/sort/dedupe scopes and compare requested vs granted scopes.
6. Webhook registry defines the initial topics and their required scopes, callback path, payload format, and enabled flag.
7. Foundation work adds no routers, commands that call Shopify, workers, handlers, frontend code, `domain/shopify/results.py`, or `domain/shopify/serializers.py`.
8. Shopify config fields are added to the existing `Settings` class in `app/beyo_manager/config.py` using the existing `Field(default=..., alias=...)` style and are not added to `_require_critical_settings`.

## Contracts and skills

### Contracts loaded

- `architecture/01_architecture.md`: Keep schema in models, pure rules in domain, external communication out of this child.
- `architecture/03_models.md`: SQLAlchemy 2.x model style, table import rules, FK/index/enum/relationship rules.
- `architecture/08_domain.md`: Scope helpers, shop domain normalization helpers, enums, and webhook registry must be pure.
- `architecture/21_naming_conventions.md`: Plural table names, singular model files/classes, env var names, constraint/index naming.
- `architecture/30_migrations.md`: Alembic autogenerate/review/upgrade expectations.
- `architecture/40_identity.md`: `client_id` primary keys and String(64) FK strategy.
- `architecture/41_user.md`: User FK strategy for created/updated actor fields.
- `architecture/42_event.md`: Event table guidance for persistent Shopify integration lifecycle events.
- `architecture/46_serialization.md`: Confirms serializer/result placeholders belong to the later admin routes/serializers phase, not this child (see Implementation plan step 4).
- `architecture/15_testing.md`: Unit tests for pure domain helpers and focused integration tests for constraints where practical.
- `architecture/17_logging.md`: Define Shopify debug flag and forbid secret/raw payload logging in later phases.
- `architecture/18_security.md`: Sensitive token/state/webhook requirements that schema must support.
- `architecture/24_multi_tenancy.md`: Workspace isolation and workspace-owned domain records.
- `architecture/25_soft_delete.md`: Soft-delete fields and filtering strategy for unlinkable integration rows.

### Local extensions loaded

- `architecture/40_identity_local.md`: Existing prefix reservations checked; see Resolved decisions for the confirmed `shpint`/`shpoau`/`shpwhs`/`shpwhi`/`shpevt` prefixes.
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

Permitted for this child:
- `app/beyo_manager/config.py` for existing settings structure and naming.
- `app/beyo_manager/models/__init__.py` for model import registration.
- Existing workspace/user model files only to confirm FK table names and relationship names.
- Recent `app/migrations/versions/` files only to confirm migration head/branch state and naming.

### Skill selection

- Primary skill: `none`
- Router trigger terms: `none`
- Excluded alternatives: `skills/cross_cutting/intention_planning/SKILL.md` — source intention already exists.

### Contracts intentionally not selected for this child

- `09_routers.md`: Relevant later, but this child must not add routes.
- `06_commands.md`, `07_queries.md`: Relevant later, but this child must not add Shopify commands/queries beyond possibly tests around pure helpers.
- `16_background_jobs.md`, `12_infra_redis.md`, `51_worker_runtime.md`: Relevant to later worker phases, but no task types, queues, or workers are implemented here.
- `19_integrations.md`: Relevant later for Shopify API/OAuth/webhook clients, but external communication is excluded here.
- `33_deployment.md`, `31_health_observability.md`, `54_ci_cd_runtime.md`: Relevant to deployment child, not foundation schema/config implementation.
- `13_sockets.md`, `56_realtime_layer.md`: No realtime behavior in Shopify foundation.
- `34_file_storage.md`: Raw payload object storage is future work, not this child.

## Implementation plan

1. Read parent plan and preserve inherited decisions.
   - Inherited: multiple shops per workspace; one active integration per shop domain globally; offline access tokens; no refresh token field; generic future webhook endpoint; domain registry owns desired topics; no historical imports.

2. Inspect only relational files needed for names.
   - Check settings structure in `app/beyo_manager/config.py`.
   - Check model registration in `app/beyo_manager/models/__init__.py`.
   - Check workspace/user table names for FKs.
   - Check migration heads before generating a migration.

3. Add Shopify config/settings fields to the existing `Settings` class in `app/beyo_manager/config.py`, under a new `# Shopify` comment, using the same `Field(default=..., alias="ENV_VAR")` style as every other field in that class:
   - `shopify_client_id: str | None = Field(default=None, alias="SHOPIFY_CLIENT_ID")`
   - `shopify_client_secret: str | None = Field(default=None, alias="SHOPIFY_CLIENT_SECRET")`
   - `shopify_app_scopes: str = Field(default="", alias="SHOPIFY_APP_SCOPES")`
   - `shopify_redirect_uri: str | None = Field(default=None, alias="SHOPIFY_REDIRECT_URI")`
   - `shopify_api_version: str = Field(default="2026-01", alias="SHOPIFY_API_VERSION")`
   - `shopify_webhook_base_url: str | None = Field(default=None, alias="SHOPIFY_WEBHOOK_BASE_URL")`
   - `shopify_integration_debug_logs: bool = Field(default=False, alias="SHOPIFY_INTEGRATION_DEBUG_LOGS")`
   - `shopify_webhook_secret: str | None = Field(default=None, alias="SHOPIFY_WEBHOOK_SECRET")`
   - Do not add any of these fields to the `required` list in `_require_critical_settings` — the backend must still boot before Shopify is configured.
   - No new encryption-key setting is added; Shopify token encryption reuses `settings.field_encryption_key` (see Resolved decisions).
   - Do not add full logging implementation; this step only defines the `shopify_integration_debug_logs` flag.

4. Add `domain/shopify/` foundation modules.
   - `enums.py`: integration status, OAuth state status if needed, webhook subscription status, webhook intake status, integration event type, event severity, payload format.
   - `scopes.py`: normalize a single scope string, parse config scope string, dedupe/sort scopes, compare requested vs granted, return missing/extra/outdated status.
   - `shop_domains.py`: pure normalization/validation for `mystore`, `mystore.myshopify.com`, and `https://mystore.myshopify.com` into lowercase `mystore.myshopify.com`; reject invalid domains.
   - `webhook_registry.py`: central desired definitions with topic, callback path for the future generic endpoint, required scopes, payload format, enabled flag.
   - Do not create `domain/shopify/results.py` or `domain/shopify/serializers.py` in this phase. Admin/frontend serialized response shapes belong to the later admin routes and serializers phase (master plan phase 6). When that phase is implemented, responses must expose only non-sensitive shop integration columns and must exclude `access_token_encrypted` and any other secrets.

5. Define initial webhook registry topics.
   - `app/uninstalled`
   - `orders/create`
   - `orders/updated`
   - `orders/paid`
   - `orders/cancelled`
   - `products/create`
   - `products/update`
   - `products/delete`
   - Registry callback path should target the future generic route path, not per-topic route paths.

6. Add SQLAlchemy models under `app/beyo_manager/models/tables/shopify/`.
   - `shopify_shop_integration.py` -> table `shopify_shop_integrations`, `CLIENT_ID_PREFIX = "shpint"`.
   - `shopify_oauth_state.py` -> table `shopify_oauth_states`, `CLIENT_ID_PREFIX = "shpoau"`.
   - `shopify_webhook_subscription.py` -> table `shopify_webhook_subscriptions`, `CLIENT_ID_PREFIX = "shpwhs"`.
   - `shopify_webhook_intake.py` -> table `shopify_webhook_intakes`, `CLIENT_ID_PREFIX = "shpwhi"`.
   - `shopify_integration_event.py` -> table `shopify_integration_events`, `CLIENT_ID_PREFIX = "shpevt"`.
   - Add all model imports to `app/beyo_manager/models/__init__.py`.
   - Add all five prefixes to `app/beyo_manager/models/tables/client_id_prefix_map.md`.

7. Planned table fields, storage types, and constraints.
   - Storage type conventions for this child (existing SQLAlchemy/Postgres convention):
     - Use `JSONB` for: `granted_scopes`, `requested_scopes`, `required_scopes`, `raw_payload`, `metadata`.
     - Use `String`/`Text` for: `access_token_encrypted`, `state`, `shop_domain`, `remote_subscription_id`, `last_error_message`.
     - Use timezone-aware `DateTime(timezone=True)` (or the project's existing equivalent) for all `*_at` datetime columns.
   - Active-like vs. inactive statuses for `shopify_shop_integrations.status` (used by the partial unique constraints below):
     - Active-like: `pending_install`, `active`, `needs_reauth`, `scopes_outdated`, `webhooks_outdated`, `error`. (`error` counts as active-like: a failed integration must not free up the shop for linking to another workspace until it is explicitly `disabled`, `uninstalled`, or soft-deleted.)
     - Inactive: `disabled`, `uninstalled`, and any row where `is_deleted = true`.
   - `shopify_shop_integrations`:
     - `client_id`, `workspace_id`, `shop_domain`, `shop_name`, `provider`, `status`, `access_token_encrypted`, `access_token_expires_at`, `granted_scopes`, `requested_scopes`, `api_version`, `installed_at`, `uninstalled_at`, `last_connected_at`, `last_health_check_at`, `last_health_check_status`, `last_error_code`, `last_error_message`, `created_by_id`, `updated_by_id`, `created_at`, `updated_at`, `is_deleted`, `deleted_at`.
     - Indexes: workspace/status, shop_domain/status, created_at, is_deleted.
     - Constraints: partial unique index enforcing one active-like integration per normalized `shop_domain` globally (`postgresql_where` restricted to the active-like status set and `is_deleted = false`); partial unique index enforcing one active-like integration per `workspace_id + shop_domain` under the same condition.
   - `shopify_oauth_states`:
     - `client_id`, `workspace_id`, `user_id`, `shop_domain`, `state`, `requested_scopes`, `redirect_after_success`, `expires_at`, `consumed_at`, `created_at`.
     - Indexes: state unique, workspace/user, shop_domain, expires_at, consumed_at.
     - Constraint: `state` unique; callback phase will enforce consumed/expired behavior.
   - `shopify_webhook_subscriptions`:
     - `client_id`, `workspace_id`, `shop_integration_id`, `topic`, `callback_url`, `remote_subscription_id`, `format`, `required_scopes`, `status`, `installed_at`, `last_verified_at`, `last_install_attempt_at`, `last_error_code`, `last_error_message`, `created_at`, `updated_at`.
     - Indexes: workspace/shop integration, topic/status, remote_subscription_id.
     - Constraint: unique desired topic per `shop_integration_id + topic`.
   - `shopify_webhook_intakes`:
     - `client_id`, `workspace_id`, `shop_integration_id`, `shop_domain`, `topic`, `webhook_id`, `dedupe_key`, `raw_payload`, `status`, `attempts`, `retryable`, `received_at`, `processing_started_at`, `processed_at`, `last_error`, `created_at`, `updated_at`.
     - Indexes: workspace/status, shop integration/topic, received_at, webhook_id.
     - Constraint: unique `dedupe_key`.
   - `shopify_integration_events`:
     - `client_id`, `workspace_id`, `shop_integration_id`, `event_type`, `severity`, `message`, `metadata`, `created_by_id`, `created_at`.
     - Indexes: workspace/shop integration, event_type, severity, created_at.

8. Alembic migration plan.
   - Generate via `alembic revision --autogenerate -m "create_shopify_integration_foundation"`.
   - Review generated migration for enum type names, FKs, indexes, partial unique indexes, JSON/JSONB types, timezone-aware datetimes, and no unrelated drift.
   - Prefer additive-only migration.
   - If partial unique indexes are needed for active-only constraints, add reviewed `op.create_index(..., unique=True, postgresql_where=...)` blocks if autogenerate does not produce them.

9. Tests.
   - Domain tests for shop domain normalization.
   - Domain tests for scope normalization, dedupe/sort, missing scope detection, and unchanged scope comparison.
   - Registry tests that required initial topics exist, are enabled, and use the generic callback path.
   - Constraint tests where practical: duplicate active-like shop domain globally (including an `error`-status row blocking a new link), duplicate active-like workspace/shop, an inactive-status row (e.g. `disabled`/`uninstalled`/soft-deleted) not blocking a new active-like link for the same shop domain, duplicate OAuth state, duplicate subscription topic, duplicate webhook intake dedupe key.

## Risks and mitigations

- Risk: Partial unique constraints are implemented incorrectly and allow duplicate active-like shop domains, or incorrectly treat `error` as inactive and allow a failed integration's shop domain to be linked elsewhere.
  Mitigation: Add explicit migration review and constraint tests covering the full active-like status set.
- Risk: Foundation accidentally starts OAuth or webhook behavior.
  Mitigation: Keep commands, routers, infra clients, workers, and handlers out of this child.
- Risk: Token model includes refresh tokens unnecessarily.
  Mitigation: Store `access_token_encrypted` only for offline Shopify tokens unless the token model changes.
- Risk: Webhook registry drifts from table rows.
  Mitigation: Registry is code/config source of truth; table tracks installed remote state only.
- Risk: Serializer/result placeholder files creep into this phase and grow into a parallel DTO architecture.
  Mitigation: Do not create `domain/shopify/results.py` or `domain/shopify/serializers.py` in this phase; that work belongs to the admin routes/serializers phase and must follow `46_serialization.md`.

## Validation plan

- `alembic revision --autogenerate -m "create_shopify_integration_foundation"`: migration generated from models only.
- `alembic upgrade head`: migration applies cleanly in development/test database.
- `alembic current`: database is at expected head after upgrade.
- `pytest tests/unit/domain/shopify`: domain helpers and registry pass.
- Focused model/constraint tests: duplicate active integration/domain and dedupe constraints fail as expected.

## Review log

- `2026-07-07` `Codex`: Created first child implementation plan scoped to Shopify foundation schema/config/domain only.
- `2026-07-08` `User/GPT review`: Resolved all three open clarifications (token encryption reuses existing `FIELD_ENCRYPTION_KEY`/`field_encryption_key`; Shopify config fields added to the existing `Settings` class in `app/beyo_manager/config.py` in the existing `Field(alias=...)` style, excluded from `_require_critical_settings`; Shopify `CLIENT_ID_PREFIX` values `shpint`/`shpoau`/`shpwhs`/`shpwhi`/`shpevt` confirmed collision-free). Defined the active-like status set (`pending_install`, `active`, `needs_reauth`, `scopes_outdated`, `webhooks_outdated`, `error`) vs. inactive (`disabled`, `uninstalled`, soft-deleted) for the partial unique constraints. Specified JSONB vs. string/text storage types per column. Removed `domain/shopify/results.py` and `domain/shopify/serializers.py` from phase-one scope; that work moves to the admin routes/serializers phase. No blockers remain; status moved to `approved`.
- `2026-07-08` `Codex implementation`: Implemented the approved Shopify foundation scope only: settings fields, pure `domain/shopify/` foundation modules, five Shopify table models, model registration, client ID prefix reservations, and Alembic migration `677ed7131bb2_create_shopify_integration_foundation`. Validated with `alembic upgrade head`, `alembic current`, focused Shopify unit tests (`16 passed`), and combined focused Shopify unit/integration tests (`22 passed`). Autogenerate exposed unrelated existing drift in `workspace_roles` and `email_sync_states`; those changes were intentionally excluded from the migration to keep scope aligned with this child plan.

## Lifecycle transition

- Current state: `archived`
- Next state: `parent plan / later Shopify child`
- Transition owner: `Codex`
