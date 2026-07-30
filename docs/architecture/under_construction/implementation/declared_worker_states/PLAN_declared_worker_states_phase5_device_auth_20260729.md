# PLAN_declared_worker_states_phase5_device_auth_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase5_device_auth_20260729`
- Status: `under_construction`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T12:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (decision D11 governs this phase)
- Prerequisite: **none** — this phase touches only auth and may run at any point (recommended early, to unblock frontend auth integration).

## Goal and intent

- Goal: A new `floor` app scope for the always-on shop-floor device: sign-in restricted to ADMIN + MANAGER, issuing a **non-expiring** access token that stays valid until explicitly revoked (logout / blocklist), with all existing scopes' behavior byte-identical.
- Business/user intent: The shop-floor terminal must stay signed in indefinitely — no 30-minute expiry, no refresh dance — while remaining killable if a device is lost or retired.
- Non-goals: Kiosk roster exposure / `clock_in_code` (Phase 6). Any change to existing scopes' token TTLs, refresh flow, or cookies. Device management UI/registry (a lost device is revoked via logout with its token, or by ops via the Redis blocklist — a device registry is a future feature).

## Scope

- In scope:
  1. `services/commands/auth/sign_in_user.py`: add `"floor": {ADMIN, MANAGER}` to `_SCOPE_ALLOWED_ROLES`; for `app_scope == "floor"`, `build_auth_response` issues the access token **without an `exp` claim** (keeps `jti` and all other claims) and returns **no refresh token**.
  2. `routers/api_v1/auth.py::sign_in_route`: skip setting the refresh cookie when the response carries no refresh token (floor sessions have nothing to refresh).
  3. `services/commands/auth/logout_user.py`: when the access token has no `exp`, the `jti` blocklist entry must be written **without TTL** (permanent). Verify-first: read how the blocklist TTL is currently derived before changing.
  4. `routers/api_v1/auth.py::refresh_route` behavior for `scope=floor`: must fail cleanly (no cookie exists → existing `RefreshTokenRejected` path). Verify + test, no new code expected.
  5. Structured log on floor sign-in (`auth.floor_device_sign_in | user_id workspace_id`) — devices signing in is an operationally notable event.
- Out of scope: everything in Phase 6; token rotation policies; device naming.
- Assumptions:
  - PyJWT's `jwt.decode` treats `exp` as optional — a token without `exp` passes `get_jwt_claims` unchanged. **Verify-first** against the installed PyJWT version; if it errors, use `options={"verify_exp": ...}`-free issuance with a far-future date is NOT acceptable — the correct fix is confirming default-optional behavior (it is the PyJWT default) and adding a unit test that pins it.
  - The `jti` Redis blocklist (`jwt_dep._is_blocklisted`) already fails **closed** (blocklist unavailable → 401) — acceptable and unchanged for floor tokens.
  - The 60s claims cache in `jwt_dep` delays revocation by ≤60s — accepted (documented in the handoff).
  - Sign-in rate limiting (`ip_rate_limit(10, 60, "sign-in")`) already covers the floor scope — unchanged.
  - Response shape for floor sign-in matches `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §2 exactly (same `{access_token, user, workspace_id}` as today, minus refresh side effects).

## Clarifications required

- [x] Truly non-expiring vs very-long-lived? — resolved: non-expiring (no `exp`), revocation via permanent `jti` blocklist (D11). Operator accepts the risk profile; sign-in stays role- and rate-limited.
- [x] Refresh cookie for floor? — resolved: none. One token, stored by the device app.

## Acceptance criteria

1. Sign-in with `app_scope="floor"`: manager account → success, token decodes with **no `exp` claim**, response contains no refresh token, no `Set-Cookie` for a refresh cookie; admin → success; worker/seller → `403` ("Invalid credentials." — same opaque message as other scope mismatches).
2. The floor token passes `get_jwt_claims` and works against a protected route; a unit test pins PyJWT's accept-missing-`exp` behavior.
3. Logout with a floor token: the `jti` is blocklisted with **no TTL** (`redis TTL == -1` asserted); subsequent request with the same token → `401` (within the documented ≤60s claim-cache window — test bypasses/clears the cache).
4. `POST /auth/refresh?scope=floor` → clean rejection (no 500).
5. Existing scopes regression: `manager`/`worker`/`admin`/`seller` sign-in still issue `exp`-bearing access tokens + refresh cookie; logout blocklist TTL for expiring tokens unchanged; full auth test suite green.
6. Structured floor sign-in log emitted.
7. `ruff check` clean.

## Contracts and skills

### Contracts loaded

- `backend/architecture/10_auth.md`: auth architecture, token issuance, blocklist rules.
- `backend/architecture/06_commands.md` (+ local): command discipline for the auth command edits.
- `backend/architecture/09_routers.md`: cookie handling stays in the router.
- `backend/architecture/18_security.md`: rate limiting, credential-error opacity.
- `backend/architecture/12_infra_redis.md`: blocklist key conventions/TTL semantics.
- `backend/architecture/15_testing.md`: auth test placement.
- `backend/architecture/49_observability_runtime.md`: structured log shape.

### Local extensions loaded

- `06_commands_local.md`: session-call safety (auth commands).

### File read intent — pattern vs. relational

Permitted relational reads:
- `services/commands/auth/sign_in_user.py`, `logout_user.py`, `refresh_token.py` — the files being modified (current TTL derivation is the verify-first item).
- `routers/api_v1/auth.py`, `routers/utils/jwt_dep.py` — cookie/claims handling being touched.
- `config.py` — existing auth settings (no new settings expected).
- Existing auth tests — extend, don't fork.

Prohibited pattern reads: other commands/routers for structure → `06`/`09`.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
- Router trigger terms: `auth`, `token`, `security`.
- Excluded alternatives: none.

## Implementation plan

1. Verify-first pair: PyJWT missing-`exp` behavior (pin with unit test) + current logout blocklist TTL derivation (relational read).
2. `sign_in_user.py`: scope entry + conditional token issuance (no `exp`, no refresh) for floor.
3. `sign_in_route`: conditional cookie skip.
4. `logout_user.py`: permanent blocklist entry for `exp`-less tokens.
5. Floor sign-in structured log.
6. Tests per acceptance 1–6.
7. Conformance check against handoff §2; run validation plan.

## Risks and mitigations

- Risk: a leaked floor token never dies on its own.
  Mitigation: accepted trade-off (D11) bounded by: ADMIN/MANAGER-only scope, opaque credential errors, sign-in rate limit, permanent-revocation logout, and ops-level Redis blocklist as last resort. The handoff instructs the frontend to store the token in secure device storage, never in URLs/logs.
- Risk: permanent blocklist entries accumulate forever.
  Mitigation: negligible volume (one per retired device session); documented in the implemented summary.
- Risk: some middleware assumes `exp` exists in claims.
  Mitigation: grep for `exp` usage across `routers/middleware/` + services during implementation; acceptance 2 exercises a protected route end-to-end.

## Validation plan

- `pytest app/tests -q -k "auth or sign_in or token or logout or refresh"`: new + regression auth tests green.
- `pytest app/tests -q`: full suite green.
- `ruff check`: clean.

## Review log

- `2026-07-30T07:51:58Z` — Codex implementation complete; independent review pending.
  - Implemented D11 in the auth-only file set: `floor` permits ADMIN/MANAGER, access tokens
    retain `jti` but omit `exp`, no refresh token/cookie is issued, and logout writes exp-less
    JTIs to the existing Redis blocklist key without a TTL. Existing scope branches retain their
    access/refresh expiry calculations, cookie behavior, and expiring blocklist TTL formula.
  - Added the structured `auth.floor_device_sign_in` log with `user_id` and `workspace_id`.
  - Verify-first evidence: installed PyJWT `2.10.1` decoded an exp-less token successfully; the
    pinned `get_jwt_claims` tests cover direct decode and a protected HTTP route. The pre-change
    logout code derived TTL as `max(int(exp - time.time()) + 60, 1)` and skipped missing `exp`;
    the existing formula remains unchanged for exp-bearing tokens.
  - Decoded floor-token evidence:
    `response_keys=['access_token', 'user', 'workspace_id']`,
    `has_exp=False`, `has_jti=True`, `app_scope='floor'`.
  - Permanent-revocation evidence:
    `test_blocklist_token_without_exp_has_no_ttl PASSED` with explicit
    `assert await redis.ttl(key) == -1`; the logout/reuse test clears the claims cache and
    confirms the same token is then rejected with `401`.
  - Floor/auth regression focus:
    `32 passed, 1 deselected` (the deselection is the recorded pre-existing custom-workspace-role
    fixture failure). This covers manager/admin success, worker/seller opaque rejection, no
    refresh response field or `Set-Cookie`, protected-route use, permanent logout, floor refresh
    rejection, structured logging, and all four existing scopes.
  - Plan auth selector with local PostgreSQL:
    `63 passed, 1 failed, 1199 deselected`; the sole failure is the same pre-existing
    `test_sign_in_user_preserves_custom_workspace_role_name` string-fixture error present at
    clean pre-implementation HEAD.
  - Full suite current:
    `1238 passed, 25 failed, 2 warnings`. Detached clean-worktree comparison at `cc6a1e9`:
    `1221 passed, 25 failed, 2 warnings`, with the exact same 25 failing test names. The 17 added
    Phase 5 tests all pass; zero new full-suite failures.
  - Touched-file `ruff check`: `All checks passed!`. Repository `ruff check .`: `141` existing
    errors; detached `cc6a1e9` comparison also reports the identical `141` errors.
  - `git diff --check`: clean. Handoff §2 response and side-effect shape confirmed; no master,
    handoff/liveness, summary, archive, user-command, or worker-shift-router file was edited.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
