# SUMMARY_refresh_token_cookie_scope_collision_20260618

## Metadata

- Summary ID: `SUMMARY_refresh_token_cookie_scope_collision_20260618`
- Status: `implemented`
- Owner agent: `codex`
- Created at (UTC): `2026-06-18T11:08:23Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_refresh_token_cookie_scope_collision_20260618.md`
- Related debug plan (optional): none

## What was implemented

- Switched auth refresh cookies from a shared `refresh_token` name to scope-specific names via `{app_scope}_refresh_token`, while still clearing the legacy cookie on sign-in and logout.
- Added scope enforcement in both sign-in and refresh flows so only allowed roles can claim an app scope and refresh requests must match the `app_scope` embedded in the JWT.
- Changed `RefreshTokenRejected` responses to HTTP `401` and removed the stale `app_scope == "admin"` bypass in backend permission middleware.

## Files changed

- `backend/app/beyo_manager/errors/permissions.py`: set `RefreshTokenRejected.http_status` to `401`.
- `backend/app/beyo_manager/services/commands/auth/sign_in_user.py`: added static scope-to-role validation and changed the default app scope to `manager`.
- `backend/app/beyo_manager/services/commands/auth/refresh_token.py`: required refresh scope and validated it against the refresh token claims.
- `backend/app/beyo_manager/routers/api_v1/auth.py`: introduced scope-specific cookie helpers, required `scope` on refresh, and deleted the legacy refresh cookie on sign-in/logout.
- `backend/app/beyo_manager/routers/middleware/backend_permission.py`: removed the special-case `admin` app-scope bypass.
- `backend/app/tests/unit/services/commands/auth/test_refresh_token.py`: updated refresh service coverage for scope-required and scope-mismatch paths.
- `backend/app/tests/unit/services/commands/auth/test_sign_in_user.py`: added sign-in scope authorization coverage.
- `backend/app/tests/unit/test_auth_router.py`: added router coverage for cookie naming, legacy-cookie cleanup, and refresh payload wiring.

## Contract adherence

- `backend/architecture/10_auth.md`: kept refresh cookies `HttpOnly`/configured and preserved router-owned cookie setting and deletion responsibilities.
- `backend/architecture/09_routers.md`: kept route handlers thin by wiring request data into `ServiceContext` and reusing response helpers.
- `backend/architecture/18_security.md`: sign-in scope validation fails with the same generic `Invalid credentials.` response used for bad credentials.

## Validation evidence

- `/bin/zsh -lc 'cd backend/app && PYTHONPATH=. .venv/bin/pytest tests/unit/services/commands/auth/test_refresh_token.py tests/unit/services/commands/auth/test_sign_in_user.py tests/unit/test_auth_router.py'`: passed, `12 passed`.

## Known gaps or deferred items

- Existing shell/integration scripts still include `app_scope: "admin"` in several places. Admin-role logins still work, but manager-role flows that rely on the old default or send `"admin"` should be updated separately if those scripts are meant to represent manager-app behavior.

## Handoff notes (if needed)

- From frontend dependency: `backend/docs/handoff/from_frontend/HANDOFF_TO_BACKEND_refresh_token_cookie_scope_collision_20260618.md`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_refresh_token_cookie_scope_collision_20260618.md`
