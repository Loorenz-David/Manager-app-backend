# HANDOFF_TO_BACKEND_refresh_token_cookie_scope_collision_20260618

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_refresh_token_cookie_scope_collision_20260618`
- Created at (UTC): `2026-06-18T10:30:00Z`
- Owner agent: `claude-sonnet-4-6`
- Source frontend plan: `n/a — this is a bug report, not a frontend plan`

## Request to backend

- Required backend behavior: Use separate cookie names for the manager and worker refresh tokens so that a login on one app cannot overwrite the refresh token of the other app.
- User-facing impact: After a user has both apps open (or logs into both apps from the same browser), the first app's session silently degrades. When its short-lived access token expires and the client attempts a refresh, the server issues a new access token with the wrong role scope. All subsequent permission-guarded requests return `403 Forbidden` with `"Insufficient role permissions."` — the user cannot perform any write/mutating action without manually reloading and re-logging in.
- Desired timeline: As soon as possible — this is a silent production bug affecting all users who use both apps from the same device.

## Frontend context

- Why the frontend needs this: The frontend api-client (`packages/api-client/src/auth-token.ts`) has no way to detect or recover from a valid-but-wrong-scope access token. The client only retries on `401 Unauthorized`. A `403 Forbidden` with `"Insufficient role permissions."` is treated as a hard error — the client throws and the user is stuck until they manually reload. The root cause is on the backend: both apps share the same `refresh_token` cookie name on the same API domain (`api-manager.beyoworkaroundtheclock.com`), so the last app to log in silently overwrites the other app's refresh token.
- Blocked frontend plan (if any): `n/a`
- Clarifications required:
  - [ ] What cookie name should the managers app expect after the fix? — the frontend `initSession()` call relies on `credentials: "include"` and the cookie being present; if the cookie name changes, no frontend code change is needed, but the backend must document the new name so we can verify in DevTools.
  - [ ] Will the new cookie still be `HttpOnly` and `Secure`? — needed to confirm no frontend storage handling changes are required.

## Expected backend deliverables

1. The `/api/v1/auth/login` endpoint (and any SSO/OAuth callback) sets **two distinct cookie names**: one for manager scope (e.g. `manager_refresh_token`) and one for worker scope (e.g. `worker_refresh_token`). Each is only set when the authenticated user's `app_scope` matches.
2. The `/api/v1/auth/refresh` endpoint reads the cookie whose name matches the expected scope for that endpoint (or a scope parameter), so a worker-scoped cookie cannot produce a manager-scoped access token.
3. Existing `refresh_token` cookie (the current single shared name) is cleared/expired on next login to avoid stale cookies in existing browser sessions.

## Interface expectations

- Endpoint(s): `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh` (and any logout/invalidation endpoint)
- Request shape: No change to request bodies — the fix is entirely in how the backend names and reads the cookies.
- Response shape:
  - Login response: unchanged body; `Set-Cookie` header changes from `refresh_token=...` to `manager_refresh_token=...` or `worker_refresh_token=...` depending on `app_scope`.
  - Refresh response: unchanged — still returns `{ ok: true, data: { access_token: string }, warnings: string[] }`.
- Error cases:
  - If the refresh request arrives with a worker-scoped cookie on the manager refresh endpoint (or vice versa), the backend should return `401 Unauthorized` (not `403`) so the frontend api-client triggers its existing session-expired flow and redirects to login.
- Socket events (if applicable): n/a

## Frontend contract implications

- Architecture contracts affected: none — no frontend code needs to change if the fix is purely cookie-name separation on the backend. The frontend uses `credentials: "include"` and does not reference the cookie name directly.
- Local extension updates needed: none
