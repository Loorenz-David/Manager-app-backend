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

- `2026-07-30` — Independent review round 1 (Opus, adversarial) of commit `549f480`: **NEEDS_CHANGES**.
  Uncommitted Phase-4 work in the tree was excluded; all gates re-run against detached clean
  worktrees at `549f480` vs `cc6a1e9`.

  **Verified green** — `_SCOPE_ALLOWED_ROLES["floor"] == {ADMIN, MANAGER}` (no WORKER/SELLER);
  claim parity proven by probe (floor claim set == manager claim set **minus `exp`**, zero value
  diffs outside `exp`/`jti`/`app_scope`); no refresh token and no `Set-Cookie` on floor sign-in
  (`raw_headers` asserted); credential opacity (wrong-password and wrong-role both raise
  `PermissionDenied("Invalid credentials.")`, `403`); PyJWT `2.10.1` missing-`exp` acceptance pinned
  by dedicated unit tests; **no far-future-`exp` hack** anywhere (grep for large timedeltas/date
  constants clean); response shape matches handoff §2 field-for-field; structured
  `auth.floor_device_sign_in` log present; `ruff check` clean on all seven touched files.
  Regression sweep: full suite at `549f480` = `27 failed, 1236 passed`; at `cc6a1e9` =
  `27 failed, 1219 passed`; **failure sets byte-identical** (`diff` empty) → +17 new passing tests,
  zero new failures. Auth selector: 63 passed vs 46 at baseline, same single pre-existing
  `test_sign_in_user_preserves_custom_workspace_role_name` failure. Real-Redis check confirms
  `SET k v` without `EX` yields `TTL == -1` and clears a pre-existing TTL.

  **Findings**

  - **N1 — CRITICAL — revocation is bypassable; permanent blocklisting is defeated.**
    `services/commands/auth/refresh_token.py:11-41` performs **no blocklist check**, and
    `routers/api_v1/auth.py:113` sources the refresh token from the client-controlled
    `floor_refresh_token` cookie. A floor **access** token satisfies every check `refresh_token()`
    makes (valid signature; `app_scope == "floor" == requested_scope`; no `exp` to reject). Proven
    by executed probe: blocklist `device-jti` permanently (`ttl == -1`) → protected route returns
    `401` → replay the *same revoked token* at `POST /auth/refresh?scope=floor` → a fresh
    `app_scope=floor`, `role_name=manager` access token with a **new, non-blocklisted `jti`** is
    minted and passes `get_jwt_claims`. Because the floor token never expires, this can be repeated
    forever. Violates acceptance 3, master **D11** ("`jti` kept so the existing Redis blocklist can
    revoke a lost/retired device"), handoff §2 ("Revocation = `POST /auth/logout` — permanent"), and
    the Risks section's "permanent-revocation logout" mitigation. The underlying
    access-token-accepted-as-refresh-token confusion is pre-existing for all scopes (also proven),
    but it was bounded there by token TTLs; Phase 5 makes it **unbounded and permanent** and turns
    it into the single point of failure of D11's entire risk model.
  - **N2 — HIGH — socket auth never consults the blocklist.** `sockets/handlers.py:22-38` decodes
    the token and connects with no `_is_blocklisted` call. Pre-existing, but for every other scope
    it self-heals at token expiry; an exp-less floor token authenticates WebSocket connections
    **forever after revocation**. Violates D11's revocation guarantee for the socket channel.
  - **N3 — MEDIUM — the documented ops last-resort is not operable.** The Non-goals/Risks sections
    name "ops via the Redis blocklist" as the fallback for a lost device, but the floor sign-in log
    (`services/commands/auth/sign_in_user.py:73-83`) records only `user_id`/`workspace_id` — the
    `jti` is never persisted or logged anywhere. With no device registry (explicit non-goal), the
    only working revocation path is "still be holding the token and call logout", which is precisely
    what is unavailable when a device is lost. The stated mitigation cannot be executed.
  - **N4 — MEDIUM — role/membership changes never revoke a floor token.** Claims are static and
    `routers/utils/jwt_dep.py:16-37` never re-reads the DB. Demoting an ADMIN/MANAGER to WORKER, or
    deactivating their membership, leaves their floor token fully valid indefinitely. Self-heals in
    ≤30 min for other scopes; never for floor. Not acknowledged in the plan's Risks section or the
    handoff.
  - **N5 — LOW — `TTL == -1` is asserted against a fake, not Redis.**
    `tests/unit/services/commands/auth/test_logout_user.py:19-31`: `_FakeRedis.ttl` is defined as
    `-1 if ex is None`, so `test_blocklist_token_without_exp_has_no_ttl` is tautological with
    respect to the fake. The Review log entry above states "asserted against Redis"; it is asserted
    against a stub. Reviewer independently confirmed the real-Redis semantics hold, so the
    *behavior* is correct — only the evidence claim is overstated.
  - **N6 — LOW — `data.pop("_refresh_token", None)` silently degrades.**
    `routers/api_v1/auth.py:59-61`: a missing refresh token was previously a hard `KeyError`. Any
    future scope that fails to issue one now returns a cookie-less session that looks successful.
    Prefer branching on the scope explicitly, or an explicit contract flag from the command.
  - **N7 — INFO — `require_app_scope` is used on zero routes.** `routers/utils/jwt_dep.py:51` is
    defined but never referenced in `beyo_manager/`. The floor token is therefore a full
    ADMIN/MANAGER credential across the **entire** API, not confined to floor/kiosk endpoints. The
    Risks section's "bounded by ADMIN/MANAGER-only scope" is literally true but reads weaker than it
    is: this is exactly a manager session that never expires. Phase 6 will need
    `require_app_scope("floor")` for the D13 `clock_in_code` exposure.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
