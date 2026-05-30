# HANDOFF_TO_BACKEND_auth_refresh_cookie_playwright_local_20260530

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_auth_refresh_cookie_playwright_local_20260530`
- Created at (UTC): `2026-05-30T09:28:24Z`
- Last updated at (UTC): `2026-05-30T09:28:24Z`
- Owner agent: `github-copilot`
- Source frontend plan: `docs/architecture/archives/implementation/PLAN_38_case_task_info_to_cases_package_20260530.md`

## Request to backend

- Required backend behavior:
  - Ensure sign-in sets a refresh cookie that is usable in local Playwright runs against frontend at `http://localhost:5173` through Vite proxy.
  - Ensure refresh immediately succeeds after sign-in when cookie is present (`POST /api/v1/auth/refresh` should return 200, not 403).
  - For local HTTP environments, cookie must not be rejected by browser policy.
  - If refresh token rotation invalidates prior sessions per user, support concurrent test sessions in dev/test (or apply a grace strategy) so repeated sign-ins from E2E workers do not invalidate each other.
- User-facing impact:
  - Current behavior causes sign-in success followed by refresh failure and session-expired redirect loops in E2E runs.
  - This blocks reliable real-auth Playwright regression runs and introduces false failures unrelated to feature behavior.
- Desired timeline:
  - High priority for local dev + CI stability for real-data E2E.

## Frontend context

- Why the frontend needs this:
  - Frontend correctly signs in and stores access token, but subsequent refresh requests fail with 403 in local test runs.
  - A failed refresh triggers session-expired handling and clears auth state, breaking route-level tests.
- Blocked frontend plan (if any): `docs/architecture/under_construction/intention/INTENTION_frontend_auth_refresh_stability_realdata_e2e_20260530.md`
- Clarifications required:
  - [ ] Does backend currently invalidate all previous refresh sessions when a new sign-in occurs for the same user? — this directly affects multi-worker Playwright behavior.
  - [ ] Which cookie attributes are currently set in local/dev (`Domain`, `Secure`, `SameSite`, `Path`, `HttpOnly`, `Max-Age`)? — needed to verify browser acceptance.
  - [ ] Is refresh expected to require extra headers or anti-CSRF tokens in this environment? — frontend currently sends credentials include with standard cookie-based refresh.

## Expected backend deliverables

1. Refresh cookie policy for local/dev that works with `localhost:5173` proxy flow:
   - `Domain`: omitted (host-only) or explicitly compatible with localhost.
   - `Secure`: `false` for local HTTP.
   - `SameSite`: compatible with same-origin proxy flow (typically `Lax`).
2. `POST /api/v1/auth/refresh` accepts cookie immediately after successful sign-in in local/dev.
3. Session model that tolerates repeated sign-ins during E2E:
   - either allow multiple active refresh sessions per user in dev/test,
   - or implement refresh rotation with grace window / session binding that does not invalidate sibling worker sessions abruptly.
4. Clear error contract for refresh rejection:
   - distinguish truly invalid session from race/invalidation cases where retry strategy can be applied.
5. Backend verification note (short) confirming tested scenario:
   - sign-in then immediate refresh,
   - repeated sign-ins from multiple browser contexts,
   - no 403 cascade for valid active sessions.

## Interface expectations

- Endpoint(s):
  - `POST /api/v1/auth/sign-in`
  - `POST /api/v1/auth/refresh`
- Request shape:
  - Sign-in: unchanged (email/password/app_scope)
  - Refresh: cookie-based, no body required by frontend
- Response shape:
  - Refresh success returns access token envelope as currently consumed by frontend
- Error cases:
  - 403 should only occur for truly invalid/expired sessions, not immediate post-sign-in valid flow
- Socket events (if applicable):
  - none

## Frontend contract implications

- Architecture contracts affected:
  - `architecture/12_auth.md`: refresh + session restoration behavior under cookie auth.
  - `architecture/17_testing.md`: reliable real-auth E2E baseline.
  - `architecture/34_runtime_validation.md`: reduce false negatives from auth instability.
- Local extension updates needed:
  - `architecture/12_auth_local.md` may need a backend-confirmed cookie/session policy note after backend delivers.

## Evidence summary from recent local runs

- Observed sequence in backend logs:
  - `POST /api/v1/auth/sign-in` → `200 OK`
  - immediate `POST /api/v1/auth/refresh` → `403 Forbidden`
- Resulting effect:
  - frontend session-expired path triggers; authenticated test routes become unavailable; Playwright tests fail due to missing expected UI state.
