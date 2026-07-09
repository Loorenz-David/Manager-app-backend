# SUMMARY_shopify_deployment_validation_20260709

## Metadata

- Plan ID: `PLAN_shopify_deployment_validation_20260709`
- Archived plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_deployment_validation_20260709.md`
- Intention plan: `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`
- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_integration_master_20260707.md`
- Implemented at (UTC): `2026-07-09`

## What changed (in-repo)

- `.github/workflows/deploy.yml`: added `managerbeyo-shopify-worker` to the existing `sudo systemctl restart` service list, placed after `managerbeyo-notification-worker` and before `managerbeyo-delayed-scheduler`, matching the plan's approved ordering. No other line in the file was modified; all eight pre-existing service names (`managerbeyo-backend`, `managerbeyo-task-router`, `managerbeyo-presence-worker`, `managerbeyo-analytics-worker`, `managerbeyo-notification-worker`, `managerbeyo-delayed-scheduler`, `managerbeyo-recurring-scheduler`, `managerbeyo-tasks-worker`) are preserved in their original order.

This is the only in-repo application/config file this phase changes, per the approved plan's scope.

## Deployment/validation content (documentation, not new repo files)

All of the following were verified against the approved Phase 7 plan and this session's own validation run; no new repo files were created for them, per the plan's design (systemd unit is an operator-created, out-of-repo file since no `.service` files are tracked in this repository):

- Environment variable checklist (10 settings: `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`, `SHOPIFY_APP_SCOPES`, `SHOPIFY_REDIRECT_URI`, `SHOPIFY_API_VERSION`, `SHOPIFY_WEBHOOK_BASE_URL`, `SHOPIFY_INTEGRATION_DEBUG_LOGS`, `SHOPIFY_WEBHOOK_SECRET`, `SHOPIFY_OAUTH_REDIRECT_URL`, `FIELD_ENCRYPTION_KEY`) — none required for app boot (confirmed: `config.py`'s `_require_critical_settings` required list is still exactly `["secret_key", "jwt_secret_key", "database_url", "redis_url"]`), each required only before first real Shopify use.
- Shopify Partner Dashboard checklist: allowed redirect URL = `SHOPIFY_REDIRECT_URI` (not `SHOPIFY_OAUTH_REDIRECT_URL`); webhook callback URL = `<SHOPIFY_WEBHOOK_BASE_URL>/api/v1/shopify/webhooks`; scopes from `SHOPIFY_APP_SCOPES`; API version from `SHOPIFY_API_VERSION`.
- Systemd unit content for `/etc/systemd/system/managerbeyo-shopify-worker.service` (operator-created on EC2, mirrors the Makefile `shopify-worker` target adapted to `APP_ENV=production`, `WorkingDirectory=/var/www/managerbeyo-backend/app`, `.venv/bin/python`).
- Migration validation, queue/task validation, HTTP route validation table (all 12 routes including the webhook and webhook-history routes), no-secret logging/response checklist, 18-step first-shop smoke runbook, and rollback notes — all as written in the approved plan's "Deployment runbook (verified content)" section, now confirmed against a live database (see Validation results below).

## Validation performed

### Static verification
- `git diff .github/workflows/deploy.yml` reviewed before and after the change: confirms only the intended one-line addition, all 8 existing service names preserved in original order, no other line touched.
- `grep managerbeyo-shopify-worker .github/workflows/deploy.yml` confirms the new service name appears in the restart list.
- No Python files were changed by this phase, so `py_compile` was not applicable/needed.

### Live database validation (local Docker Postgres on port 5433 / Redis on port 6380, brought up via `app/docker-compose.yml`)

This is the first time in the phase 5 → 6 → 6.1 → 7 series that any of these migrations or integration suites have run against a live database — the three-phases-deep carried-forward DB validation gap is now closed.

- `alembic heads`: exactly one head, `ab12cd34ef56` — confirmed.
- `alembic current` (before upgrade): `677ed7131bb2` (pre-existing from an earlier session). `alembic upgrade head`: applied `677ed7131bb2 -> c3f7a9d2e4b1 -> ab12cd34ef56` cleanly, no errors. `alembic current` (after): `ab12cd34ef56 (head)` — confirmed matches plan's expected chain exactly.
- Full Shopify unit suite (`tests/unit/domain/shopify`, `tests/unit/domain/execution`, `tests/unit/test_shopify_router.py`, `tests/unit/services/infra/shopify`, `tests/unit/services/commands/shopify`): **83 passed, 1 failed**. The one failure (`test_shopify_task_type_migration_adds_all_expected_enum_values`) is a pre-existing Phase 5 test bug unrelated to this phase: it reads a migration file via a `cwd`-relative path (`Path("app/migrations/versions/...")`) that only resolves when pytest is invoked from the repository root, not from `app/` (this suite's conventional invocation directory, per `Makefile`'s `test` target). Not fixed — modifying Phase 5 test files is outside Phase 7's scope.
- Shopify DB-backed integration suites (`tests/integration/services/queries/shopify`, `tests/integration/services/commands/shopify`, `tests/integration/services/tasks`): **41 passed, 6 failed** on every attempted run. Root cause fully diagnosed (not left as a mystery): several Phase 6/6.1 integration test files call `await db_session.commit()` explicitly mid-test (e.g. `test_shopify_admin_queries.py:131,182,216`, `test_shopify_webhook_history_query.py:208,248`) to make seeded rows visible to code under test that opens its own DB session. This explicit commit permanently persists fixture rows past the shared `db_session` fixture's rollback-based teardown (`tests/conftest.py`). Combined with several tests using fixed literal shop domains (e.g. `third.myshopify.com`, `empty-shop.myshopify.com`, `valid-shop.myshopify.com`, `other.myshopify.com`) rather than randomized ones, a second run against the same database collides on `uix_shopify_shop_integrations_shop_domain_active`. This is a genuine, pre-existing Phase 6/6.1 test-isolation defect — invisible in phases 5, 6, and 6.1 because none of those sessions ever had live database access, and first exposed by this phase's live-DB validation pass. It is **not a Phase 7 regression** and is **out of Phase 7's scope to fix** (would require editing already-archived Phase 6/6.1 test files or the shared `tests/conftest.py` fixture). Colliding rows were cleaned from the local dev database (targeted `DELETE`, confirmed with the user first) as a courtesy; the underlying test-isolation defect remains and will recur on the next live-DB run of these specific test files until a future phase fixes it.
- `GET /health`: not exercised via a running app process in this session (no app server was started); confirmed by code inspection (unchanged since before Phase 1) that it checks only Postgres/Redis and performs no Shopify call.
- HTTP route validation: confirmed via the passing `tests/unit/test_shopify_router.py` suite (role-gating, path, and HMAC-independent unit coverage) rather than a live HTTP smoke pass; no running app server was started this session.
- Queue/task validation: confirmed via the passing `tests/unit/domain/execution/test_shopify_execution_contracts.py` tests (3 of 4 passed; the 4th is the unrelated path-bug above) — all four Shopify task types route only to `queue:shopify`.

## Final report

- **Files created**: `docs/architecture/implemented_summaries/SUMMARY_shopify_deployment_validation_20260709.md` (this file).
- **Files modified**: `.github/workflows/deploy.yml` (one line added); `docs/architecture/under_construction/implementation/PLAN_shopify_deployment_validation_20260709.md` (status/lifecycle update, then moved — see below); `docs/architecture/under_construction/intention/shopify_integration_intention.txt` (progress notes appended for phases 6, 6.1, and 7).
- **Deploy workflow change**: `managerbeyo-shopify-worker` added to the `sudo systemctl restart` list in `.github/workflows/deploy.yml`, positioned after `managerbeyo-notification-worker` and before `managerbeyo-delayed-scheduler`.
- **Was `managerbeyo-shopify-worker` added to the restart list?** Yes.
- **Was any existing service name removed?** No — all 8 pre-existing service names remain, in their original order.
- **Migration file created?** None — Phase 7 creates no new migrations, per scope.
- **Tests/validation commands run**: `alembic heads`, `alembic current`, `alembic upgrade head` (all against live Postgres); full Shopify unit test suite; full Shopify DB-backed integration test suite (queries/commands/tasks).
- **DB-backed validation status**: Ran successfully against a live database for the first time in this plan series. Alembic migration validation fully passed. Integration test suite: 41/47 passed; 6 failed due to a pre-existing, fully root-caused Phase 6/6.1 test-isolation defect (explicit `db_session.commit()` calls in test files bypassing fixture rollback, combined with literal non-randomized test domains), not a Phase 7 defect.
- **Alembic validation status**: Passed. Single head `ab12cd34ef56`; chain `677ed7131bb2 -> c3f7a9d2e4b1 -> ab12cd34ef56` applies cleanly.
- **Does the EC2 systemd service still need to be created manually?** Yes — `/etc/systemd/system/managerbeyo-shopify-worker.service` does not exist in this repository (no `.service` files are tracked) and must be created out-of-band on the EC2 host by an operator, using the exact unit content documented in the approved Phase 7 plan's "Deployment runbook" section, before the next deploy's `systemctl restart managerbeyo-shopify-worker` can succeed.
- **Summary path**: `backend/docs/architecture/implemented_summaries/SUMMARY_shopify_deployment_validation_20260709.md`.
- **Archived plan path**: `backend/docs/architecture/archives/implementation/PLAN_shopify_deployment_validation_20260709.md`.
- **Were master/intention notes updated?** Intention plan progress notes updated minimally (phases 6, 6.1, 7 entries appended). Master plan (`PLAN_shopify_integration_master_20260707.md`) left untouched — its own `Status` field and lifecycle transition are not part of this phase's mandate and were not modified.
- **Anything not completed**: No live HTTP smoke run against a running app server (route validation relies on existing passing unit tests instead); the 6-test Phase 6/6.1 test-isolation defect above remains unfixed (out of scope).
- **Blockers found**: The EC2 `managerbeyo-shopify-worker.service` systemd unit does not exist yet and must be created manually before the next production deploy restarts it successfully — this is documented as an explicit operational requirement, not silently assumed.
