# SUMMARY_PLAN_shopify_metafield_preferences_delete_capability_20260713

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_metafield_preferences_delete_capability_20260713`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-13T10:44:52Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_delete_capability_20260713.md`
- Intention plan: `—`

## What was implemented

- Added flat-list request parsing for `{"client_ids": [...]}`.
- Added an atomic, workspace-scoped batch soft-delete command that rejects missing, foreign-workspace, and already-deleted IDs without partial writes.
- Added `DELETE /api/v1/integrations/shopify/metafield-preferences` for admin, manager, seller, and worker roles.
- Added parser, route, role-gating, real-DB delete, isolation, idempotency/error, and delete-then-recreate restoration tests.

## Validation evidence

- Focused unit tests: 11 passed.
- Delete integration tests: 4 passed.
- Ruff and `git diff --check`: passed.
- Full unit suite: 396 passed, 12 unrelated/pre-existing failures.
- Alembic current: `b4c5d6e7f8a9 (head)`.

## Lifecycle transition

- State: `summarized`
- Next state: `archived`
- Archive target: `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_delete_capability_20260713.md`
