# PLAN_declared_worker_states_phase5_device_auth_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase5_device_auth_20260729`
- Status: `archived` (APPROVED at round 3, `12bbeb7`; summarized and archived)
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-30T09:45:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (decision D11 governs this phase)
- Prerequisite: **none** — this phase touches only auth and may run at any point (recommended early, to unblock frontend auth integration).

## Goal and intent

- Goal: A new `floor` app scope for the always-on shop-floor device: sign-in restricted to ADMIN + MANAGER, issuing a **non-expiring** access token that stays valid until explicitly revoked (logout / blocklist), with all existing scopes' behavior byte-identical.
- Business/user intent: The shop-floor terminal must stay signed in indefinitely — no 30-minute expiry, no refresh dance — while remaining killable if a device is lost or retired.
- Non-goals: Kiosk roster exposure / `clock_in_code` (Phase 6). Any change to existing scopes' token TTLs, refresh flow, or cookies. Device management UI/registry (a lost device is revoked via logout with its token, or by ops via the Redis blocklist — a device registry is a future feature). Phase 5 intentionally adds no route-level `floor` scope gates, so a floor token has its ADMIN/MANAGER API reach until Phase 6 introduces the first floor-gated surface.

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
  Lost-device runbook: find the device's `auth.floor_device_sign_in` structured log by
  workspace, user, and sign-in time; copy its `jti`; then execute
  `SET <redis_key_prefix>:auth:blocklist:<jti> 1` with no `EX`/`PX` option and verify
  `TTL <redis_key_prefix>:auth:blocklist:<jti>` returns `-1`.
- Risk: JWT role and membership claims are static for the lifetime of a floor token.
  Accepted limitation (operator decision): demoting the signing manager or deactivating their
  membership does not invalidate an already-issued floor token. Floor devices are
  business-owned hardware; offboarding must explicitly revoke every device token associated
  with that account via logout or the lost-device runbook above. A per-request database role
  re-check is intentionally out of scope.
- Risk: pre-fix refresh cookies have no `token_type` claim.
  Mitigation: newly issued access/refresh tokens are type-discriminated, while exp-bearing
  type-less refresh tokens remain temporarily accepted for compatibility. Remove the legacy
  type-less branch after `jwt_refresh_token_expire_days` has elapsed from deployment of the
  fix-cycle commit; by then every legitimate outstanding legacy refresh cookie has expired.
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
  - Permanent-revocation unit evidence:
    `test_blocklist_token_without_exp_has_no_ttl PASSED` used `_FakeRedis` and therefore pinned
    the no-`ex` call shape rather than proving server TTL semantics. The logout/reuse test clears
    the claims cache and confirms the same token is then rejected with `401`; real-Redis TTL
    coverage is added in the N5 fix cycle below.
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

- `2026-07-30T08:52:57Z` — Codex fix cycle 1 complete for review findings N1–N7;
  independent re-review pending.
  - **N1 fixed and pinned:** added the reviewer's blocklisted-floor-token refresh probe first.
    It failed before production edits with `Failed: DID NOT RAISE RefreshTokenRejected`, then
    passed after the fix. `refresh_token()` now hard-rejects `scope=floor`, rejects exp-less
    credentials, rejects typed access tokens, requires a `jti`, checks the Redis blocklist before
    minting, and fails closed when the blocklist is unavailable. Newly issued refresh tokens carry
    `token_type=refresh`; newly issued and refreshed access tokens carry `token_type=access`.
    Exp-bearing type-less legacy refresh cookies remain accepted only for the documented
    transition window. Tests additionally pin valid-token floor rejection, revoked non-floor
    refresh rejection, regular access-token confusion rejection, exp-less non-floor rejection,
    legacy type-less compatibility, refreshed access typing, and blocklist failure closure.
  - **N2 fixed and pinned:** Socket.IO connect auth now checks the shared token blocklist after JWT
    decode and rejects both revoked tokens and blocklist infrastructure failures before
    `manager.connect`. Tests use an exp-less floor access token and assert revoked/fail-closed
    rejection.
  - **N3 fixed and pinned:** floor sign-in and logout structured logs now carry the access-token
    `jti`; both tests assert the logged value. The Risks section now contains the lost-device
    Redis revocation runbook (`SET ...` without TTL, then verify `TTL == -1`).
  - **N4 accepted/documented:** Risks now state that role/membership claims remain static and that
    manager offboarding must explicitly revoke all associated business-owned floor-device tokens.
    No live database role re-check was added.
  - **N5 fixed:** corrected the original Review-log evidence to identify `_FakeRedis` accurately
    and added `test_floor_logout_blocklist_has_no_ttl_in_real_redis`, which seeds a real Redis key
    with `EX`, calls production logout, then asserts the value is overwritten and server
    `TTL == -1`. Execution of this new integration test was blocked in this session because the
    environment rejected local-service escalation after its usage quota was exhausted; no
    workaround was attempted. The round-1 reviewer had independently confirmed the same real
    Redis `SET`/`TTL == -1` semantics.
  - **N6 fixed and pinned:** `sign_in_route` now branches explicitly. Floor performs no refresh
    pop/cookie operation; every non-floor scope again uses
    `data.pop("_refresh_token")`. A test asserts missing non-floor refresh data raises `KeyError`.
  - **N7 documented:** Non-goals now state that Phase 5 intentionally adds no route-level floor
    gates and that Phase 6 introduces the first floor-gated surface.
  - Focused auth/socket unit regression:
    `44 passed, 1 deselected`; the deselection is the unchanged pre-existing
    custom-workspace-specialization fixture failure. Broader unit auth/token/socket selector:
    `57 passed, 1` identical known failure, `894 deselected`.
  - Touched-file `ruff check`: `All checks passed!`; `git diff --check`: clean.
  - The planned DB/Redis integration and full-suite baseline commands could not be re-run because
    the environment rejected the required local-service escalation after its usage quota was
    exhausted. These remain explicit re-review gates; no green result is claimed for them here.

- `2026-07-30` — Independent review **round 2 (in progress)** of fix commit `b8946fe`
  (implementation `549f480`). Appended step-by-step; earlier prior sessions were terminated by API
  overloads. Working tree is clean; repo HEAD is `ccdffa9` (Phase 4 fix work sits on top of
  `b8946fe`), so all round-2 judgements are made against `b8946fe`'s **diff**, not the tree.

  **Step 1 — focused auth/socket unit tests at `b8946fe`.** Finding recorded:

  - **R2-1 — HIGH (test integrity) — the `fake_redis` monkeypatch seam does not cover the
    revocation half of the floor logout test, so it can pass for the wrong reason.**
    `app/tests/unit/services/commands/auth/test_logout_user.py:35-39` patches
    `async_client.get_async_redis`. That works for `logout_user._blocklist_token`
    (`services/commands/auth/logout_user.py:50` imports the symbol *inside* the function, so it
    resolves through the patched module attribute at call time). It does **not** work for the
    read side: `b8946fe` introduced `services/infra/auth.py:2`, which binds
    `get_async_redis` at **module import time**, and `routers/utils/jwt_dep.py:9` now imports
    `is_token_blocklisted` from it. Consequently, in
    `test_floor_logout_permanently_revokes_subsequent_request`
    (`test_logout_user.py:63-100`) the write lands in the in-memory `_FakeRedis` while
    `get_jwt_claims` reads **real** Redis. Two mutually exclusive outcomes: with Redis reachable,
    the key is absent → `exists == 0` → no `401` → the test **fails**; with Redis unreachable, the
    exception is swallowed by `jwt_dep._is_blocklisted` into `HTTPException(401,
    "Auth blocklist unavailable.")` → the test **passes for the fail-closed reason, not because
    the token was revoked**. The assertion `exc_info.value.status_code == 401` cannot distinguish
    the two (it checks the status code only, never `detail`). Codex's reported
    `44 passed` was produced in a session that explicitly could not start local services, which is
    consistent with the second branch. Acceptance 3's "subsequent request with the same token →
    `401`" therefore has no sound unit-level evidence. Same seam defect applies to any other test
    relying on `fake_redis` to influence a read through `infra.auth`.

  **Step 2 — is N5 genuinely closed? (verified by reading; the operator's
  `pytest tests/integration/services/commands/auth -q` → `1 passed in 0.05s` was NOT re-executed).**
  Verdict: **N5 is genuinely closed for the exp-less write path, with one residual evidence gap.**

  - The seam is real, not faked. `app/tests/integration/services/commands/auth/test_logout_user_integration.py`
    uses the `redis_client` fixture, which is `redis.from_url(settings.redis_url,
    decode_responses=True)` (`app/tests/conftest.py:53-60`) — a real client, no stub anywhere in
    the fixture chain (`app/tests/conftest.py` is the only conftest on that path and installs no
    Redis double). Production writes through `get_async_redis()`
    (`services/infra/redis/async_client.py:8-12`), also a real client on the same
    `settings.redis_url`. The test `monkeypatch.setattr(settings, "redis_key_prefix",
    isolated_redis_prefix)` and `_blocklist_token` reads `settings.redis_key_prefix` at call time
    (`logout_user.py:53`), so both sides address the identical key.
  - The assertion is non-tautological: the test **seeds** `SET key "stale" EX 60` first, then calls
    production `logout_user`, then asserts `get(key) == "1"` **and** `ttl(key) == -1`. A no-`ex`
    `SET` discarding a pre-existing TTL is genuine server semantics that `_FakeRedis` could not
    have produced (and the fake is not in scope here at all). This is exactly the defect N5 named.
  - `0.05s` is thin-looking but not disqualifying: `app/pytest.ini` has no `-m "not integration"`
    in `addopts`, so the test is selected and run (a deselect would have printed
    `1 deselected`, not `1 passed`), and a localhost Redis `SET`/`GET`/`TTL` round-trip is
    sub-millisecond. Critically, `redis.from_url` connects lazily, so an absent Redis would surface
    as a `ConnectionError` at `redis_client.set(...)` — an **error, not a pass**. A pass therefore
    does imply a live Redis server. Nothing in the test can succeed against a dead Redis.
  - **Residual gap (LOW, new): R2-2 — the "unchanged for expiring tokens" half of acceptance 3 /
    the checklist's "Expiring tokens' blocklist TTL behavior unchanged — asserted against Redis"
    is still fake-only.** The single integration test covers only the exp-less branch; the
    exp-bearing TTL formula is asserted solely against `_FakeRedis.ttl`, which returns the `ex`
    value it was handed (`test_logout_user.py:25-29`, `:50-60`) — i.e. it re-asserts the argument,
    not a server TTL. One integration test in the whole gate directory is minimal coverage; a
    second case seeding no TTL and asserting `0 < ttl <= formula` would close it.

  **Step 3 — N1 exploit probe re-run + each of the four defense layers probed separately.**
  Executed, no mocks: real Redis (`redis://localhost:6379/0`, isolated key prefix
  `beyo_manager:r2probe:<rand>`, cleaned up), real PyJWT `2.10.1`, and the real production
  functions — the floor token was minted by production `build_auth_response` driven by real
  (unpersisted) `User`/`Workspace`/`WorkspaceMembership`/`WorkspaceRole`/`Role` ORM rows, revoked by
  production `logout_user`, and every rejection came from production `refresh_token()` /
  `jwt_dep.get_jwt_claims()` / `services.infra.auth.is_token_blocklisted()` reading real Redis.
  **19 probes, 18 as-designed; the single non-pass is the knowingly-documented legacy window
  (R2-3 below), not a regression.**

  - **N1 is CLOSED.** The round-1 exploit is dead: floor token minted (`has_exp=False`,
    `has_jti=True`, `token_type=access`, response keys exactly
    `['access_token', 'user', 'workspace_id']`) → production logout → real Redis
    `value='1'`, `TTL == -1` → protected route `401 "Token has been revoked."` (claims cache
    cleared, so this is a genuine real-Redis read) → replayed as the `floor_refresh_token` cookie at
    `scope=floor` → **`RefreshTokenRejected(reason='floor_scope_not_refreshable', http=401)`**, no
    token minted. Replaying the *same* revoked token while varying the scope to bypass layer 1
    (`manager`, `worker`, `admin`, `seller`, plus the casing/whitespace variants `FLOOR`, `Floor`,
    `"floor "`) minted **nothing** in any case — the non-floor attempts die on layer 3
    (`reason='refresh_token_invalid'`, exp-less). The bypass is not launderable through the scope
    parameter.
  - **Layer 1 (floor hard-reject) — verified independently.** A fully valid, un-revoked,
    correctly-typed (`token_type=refresh`) floor refresh token is rejected with
    `reason='floor_scope_not_refreshable'`; the check also fires with `refresh_token=None`, proving
    it precedes the cookie-presence check (`refresh_token.py:17-21` before `:22-23`) and cannot be
    probed around by omitting the cookie.
  - **Layer 2 (blocklist check at refresh) — verified independently against real Redis.** A
    non-floor, exp-bearing, `token_type=refresh` token whose `jti` was blocklisted by production
    `_blocklist_token` is rejected with `reason='refresh_token_revoked'`. Discriminating, not
    blanket: the identical token shape with a fresh un-revoked `jti` still refreshes successfully
    and mints `token_type=access` with an `exp`. Layer 2 also still fires on the legacy type-less
    branch (revoked legacy refresh cookie → `refresh_token_revoked`), so the transition branch is
    not a blocklist hole.
  - **Layer 3 (exp-less rejection) — verified independently.** A non-floor token that is correctly
    typed `refresh` but carries no `exp` — i.e. only exp-lessness can stop it — is rejected with
    `reason='refresh_token_invalid'`.
  - **Layer 4 (token_type discrimination) — verified independently.** Exp-bearing
    `token_type=access` → rejected; unknown `token_type='banana'` → rejected (the
    `not in (None, "refresh")` allow-list is closed, not an `!= "refresh"` blacklist); and
    `jti`-less refresh → rejected (`refresh_token.py:41-46`), so the layer-2 blocklist cannot be
    dodged by stripping `jti`. The legacy branch (`exp` present, `token_type` absent) is accepted as
    designed and mints a *new* `jti` plus `token_type=access`.
  - **R2-3 — INFO (documented residual, no action required this phase).** The legacy transition
    branch accepts any exp-bearing type-less token, so a **pre-fix access token** replayed as a
    refresh cookie is still accepted (probe: accepted, minted a fresh access token). This is
    inherent to the compatibility branch — a legacy access token and a legacy refresh token are
    indistinguishable by construction — and it is strictly the *pre-existing* confusion N1 called
    out as "bounded by TTLs". It is bounded here too, and much more tightly than the plan's Risks
    note implies: legacy **access** tokens die after `jwt_access_token_expire_minutes` (30 min),
    not `jwt_refresh_token_expire_days` (30 days). Floor tokens are excluded from this branch
    entirely by layer 3. Worth one clarifying clause in the Risks sunset note; not a defect.

  **Step 4 — N2, N3, N6 and the legacy transition branch.**

  - **N2 — CLOSED, verified by executed probe against real Redis (6/6 as designed).**
    `sockets/handlers.py:28-34` now blocklist-checks after JWT decode and before
    `manager.connect`. Probe (only the non-auth collaborators `manager.connect` /
    `set_user_online` were stubbed, and only so that reaching them is observable — the blocklist
    path was the real `is_token_blocklisted` against real Redis): a live exp-less floor token
    connects (`accepted=True`, `connect` called); the *same* token shape after production
    `logout_user` (`value='1'`, `TTL == -1`) is rejected (`accepted=False`, `connect` **never**
    called); and with the async client repointed at a closed port to force a genuine Redis
    outage, connect is refused (`accepted=False`, `connect` never called) — fail-closed confirmed
    against a real failure, not a raised-mock. The `QUERY_STRING` token path
    (`handlers.py:21`) is covered by the same check (revoked token via query string → rejected),
    so the second credential entry point is not a hole. Codex's unit tests use the correct seam
    (`monkeypatch.setattr(handlers, "is_token_blocklisted", ...)` — patching the name at its point
    of use), so unlike R2-1 they are sound.
    - **R2-4 — INFO.** `handlers.py:29` guards the check with `if jti:`, so a validly signed but
      `jti`-less token connects with no blocklist consultation (probe: `accepted=True`). This
      exactly mirrors `jwt_dep.py:32` (`if jti and await _is_blocklisted(jti)`), is unreachable
      without the signing secret, and every token the app issues carries a `jti` — noted for
      symmetry only, not a Phase 5 defect.
  - **N3 — CLOSED.** `services/commands/auth/sign_in_user.py:73-92` decodes the token it just
    issued and logs `jti` in both the message and the `extra` payload, so the logged value is
    *structurally* the issued token's `jti`; `logout_user.py:16-28` does the same for
    `auth.floor_device_logout`. Pinned by assertions on the value, not just its presence:
    `test_sign_in_user.py:205-226` asserts `record.jti == claims["jti"]` against the decoded
    response token, and `test_logout_user.py:143-172` asserts `record.jti`. The logout log was
    observed emitting live during the Step 3 probe
    (`"event_type": "auth.floor_device_logout", ... jti=c8b41ff2-…`). The Risks section now carries
    the executable lost-device runbook (`SET <prefix>:auth:blocklist:<jti>` with no `EX`, then
    verify `TTL == -1`), which Step 1/Step 3 independently confirmed produces `TTL == -1` on a real
    server. The ops path named in Non-goals is now genuinely operable.
  - **N6 — CLOSED.** `routers/api_v1/auth.py:56-79` branches explicitly on
    `body.app_scope == "floor"`: the floor arm performs no pop and no cookie work; every other
    scope goes through `data.pop("_refresh_token")` with no default, restoring the hard `KeyError`.
    Pinned by `test_auth_router.py::test_non_floor_sign_in_route_fails_loudly_without_refresh_token`
    (`pytest.raises(KeyError, match="_refresh_token")`). No `pop(..., None)` remains on that path.
  - **Legacy transition branch — CONFIRMED still working (executed).** An exp-bearing, `token_type`-less
    refresh cookie for `scope=manager` still refreshes successfully and mints a properly typed
    (`token_type=access`), exp-bearing access token with a **new** `jti`, so outstanding pre-fix
    30-day cookies are not invalidated by the fix. The branch is not a bypass: a revoked legacy
    type-less cookie is still stopped by layer 2 (`reason='refresh_token_revoked'`), and layer 3
    still excludes exp-less (floor) tokens from it. Its one documented cost is R2-3 above.
  - **N4 / N7 (documentation-only outcomes) — present as required.** Non-goals (line 18) states
    Phase 5 intentionally adds no route-level `floor` gates and that Phase 6 introduces the first
    floor-gated surface; Risks carries the static-claims / offboarding paragraph and the legacy
    sunset note.

  **Step 5 — full-suite + `ruff` regression, judged on `b8946fe`'s diff.** Run in detached clean
  worktrees (`git worktree add`) at `b8946fe`, at its **true parent `e57aab7`**, and at `549f480`.
  Note on baselines: `549f480` predates the Phase 4 commits (`20b11c7`, `e57aab7`), so a
  `b8946fe` vs `549f480` delta conflates Phase 4 work; `e57aab7` is the correct isolation baseline
  and is reported alongside. `pytest-randomly` is **not** installed, so collection order is
  deterministic — which matters for R2-5 below.

  - **Full suite — no new failures, failure sets byte-identical.**
    `e57aab7`: `27 failed, 1259 passed`. `b8946fe`: `27 failed, 1272 passed`.
    `549f480`: `27 failed, 1236 passed`. `diff` of the sorted `FAILED` name lists is **empty** for
    both comparisons → the fix commit adds **13** net passing tests over its parent and introduces
    zero new full-suite failures. The only auth-namespace failure at `b8946fe` is the known
    pre-existing `test_sign_in_user_preserves_custom_workspace_role_name`.
  - **`ruff` — strictly improved, zero new findings.** Repo-wide: `e57aab7` = `148` errors,
    `549f480` = `148`, `b8946fe` = `140`. `comm` of the sorted finding lists shows **no new finding
    introduced** and 8 removed — all `E402` in `sockets/handlers.py`, which `b8946fe` fixed by
    moving `logger = logging.getLogger(__name__)` below the imports. None of the 13 touched files
    carries any `ruff` finding at `b8946fe`.
  - **R2-1 escalated to a CONFIRMED new test failure introduced by `b8946fe`** (was a
    test-integrity concern at Step 1; now demonstrated by execution):
    - `pytest tests/unit/services/commands/auth` at the parent `e57aab7`:
      `1 failed, 24 passed` (the single known pre-existing failure).
      At `b8946fe`: **`2 failed, 31 passed`** — the new failure is
      `test_floor_logout_permanently_revokes_subsequent_request`, with
      `Failed: DID NOT RAISE <class 'fastapi.exceptions.HTTPException'>`.
      Running `tests/unit/services/commands/auth/test_logout_user.py` alone reproduces it
      (`1 failed, 4 passed`); the same file at `549f480` is `4 passed`. **Cause:** `b8946fe` moved
      the blocklist read out of the function body into module scope
      (`services/infra/auth.py:2` binds `get_async_redis` at import time; `jwt_dep.py:9` imports
      `is_token_blocklisted` from it), which broke the `fake_redis` seam that patches
      `async_client.get_async_redis`. Acceptance 5's "full auth test suite green" and acceptance 3's
      revocation assertion both fail under this natural invocation.
    - **Why the full suite hides it (and why that is worse, not better):** the async Redis singleton
      (`async_client._async_client`) is bound to the event loop that created it, and `pytest-asyncio`
      gives each test a fresh loop, so any later test touching it raises
      `RuntimeError: got Future <Future pending> attached to a different loop` /
      `Event loop is closed`. In whole-suite order the client is already loop-poisoned by the time
      this test runs, so `is_token_blocklisted` raises, `jwt_dep._is_blocklisted` converts that into
      `HTTPException(401, "Auth blocklist unavailable.")`, and the test's
      `assert exc_info.value.status_code == 401` is satisfied **by the infrastructure failure rather
      than by revocation**. Demonstrated directly: running the integration test first and the unit
      test second yields `2 passed`; running the unit test alone yields `1 failed`. The assertion
      never inspects `detail`, so it cannot tell the two apart. The test is therefore either red or
      a false positive — never valid evidence.
    - **Scope of the redness, stated precisely.** The plan's own Validation-plan selector,
      `pytest tests -q -k "auth or sign_in or token or logout or refresh"`, is **green** modulo the
      known failure at both commits (`e57aab7`: `1 failed, 63 passed`; `b8946fe`:
      `1 failed, 76 passed`) — because the integration test is selected too and runs first,
      poisoning the client and producing the false-positive pass. So the documented gate is *not*
      red; the redness appears under directory- or file-scoped invocation
      (`pytest tests/unit/services/commands/auth`, `… /test_logout_user.py`). Both outcomes are
      failures of evidence: the documented gate is green only for the wrong reason.
  - **R2-5 — MEDIUM (new) — the N5 integration gate is order-fragile and currently green only by
    collection accident.** The same loop-bound singleton breaks
    `test_floor_logout_blocklist_has_no_ttl_in_real_redis` as soon as **any** earlier test in the
    session has used the async Redis client: alone it is `1 passed in 0.03s`, but preceded by one
    unit test that touches the client it fails with
    `RuntimeError: ... attached to a different loop`. It passes in the full suite only because
    `tests/integration/...` sorts before `tests/unit/...` and it happens to be the first
    async-Redis user in the session. The next integration test that touches Redis and sorts ahead of
    it will turn this gate red with an error unrelated to what it asserts. This is a defect in the
    gate's durability, not in the production behavior it verifies (which Step 1/Step 3 confirmed
    independently against a real server).
  - **R2-6 — INFO (altitude).** `routers/api_v1/auth.py:57` branches on the *request* field
    `body.app_scope == "floor"`, duplicating the floor condition the command already owns
    (`sign_in_user.py:130`/`:147`). It is correct today because both read the same value, but the
    floor arm never pops `_refresh_token`, so if the command ever issued one for floor the token
    would be serialized into the JSON body. N6's alternative — an explicit contract flag returned by
    the command — keeps the decision in one place.

  **Step 6 — consolidated round-2 verdict: `NEEDS_CHANGES` (test/evidence integrity only; no
  production-code change required).**

  Round-1's security findings are genuinely closed, each re-verified by executed, mock-free probes
  against real Redis rather than by reading the fix:

  | Finding | Round-1 severity | Round-2 status | Evidence |
  | --- | --- | --- | --- |
  | N1 revocation bypass via `/auth/refresh` | CRITICAL | **CLOSED** | 19-probe run; exploit rejected, all four layers verified in isolation, not launderable via any scope string |
  | N2 socket auth ignores blocklist | HIGH | **CLOSED** | 6-probe run; revoked → refused, real Redis outage → fail-closed, query-string path covered |
  | N3 `jti` never logged | MEDIUM | **CLOSED** | `jti` logged at sign-in and logout, pinned by value-equality assertions; runbook in Risks, `TTL == -1` confirmed on a real server |
  | N4 static role claims | MEDIUM | **ACCEPTED/DOCUMENTED** | Risks paragraph present, per operator decision |
  | N5 fake-Redis TTL evidence | LOW | **CLOSED (behavior)** | real-Redis integration test seeds `EX 60`, asserts overwrite + `TTL == -1`; but see R2-5 |
  | N6 silent `pop(..., None)` | LOW | **CLOSED** | explicit branch; `KeyError` restored and pinned |
  | N7 `require_app_scope` unused | INFO | **DOCUMENTED** | Non-goals sentence present |

  Regression posture is clean: identical 27-failure set at `b8946fe`, its parent `e57aab7`, and
  `549f480`; +13 net passing tests; `ruff` strictly improved (140 vs 148) with zero new findings.

  **Blocking for round 2 (both are test-only):**

  - **R2-1 — MEDIUM — `test_floor_logout_permanently_revokes_subsequent_request` is red under
    file/directory-scoped invocation and a false positive otherwise.** `b8946fe` broke the
    `fake_redis` seam by moving the blocklist read to a module-level import; the test now either
    fails outright or passes because Redis errored (fail-closed), never because the token was
    revoked. Acceptance 3's revocation half — the guarantee D11's entire risk model rests on — has
    no sound automated evidence. Fix: patch the symbol at its point of use
    (`jwt_dep.is_token_blocklisted` or `infra.auth.get_async_redis`) instead of
    `async_client.get_async_redis`, and assert `detail == "Token has been revoked."` so a
    fail-closed `401` can never satisfy the test.
  - **R2-5 — MEDIUM — the N5 integration gate is order-fragile.** The loop-bound
    `async_client._async_client` singleton makes
    `test_floor_logout_blocklist_has_no_ttl_in_real_redis` fail with
    `RuntimeError: ... attached to a different loop` whenever an earlier test in the session touched
    the async client; it is green today only because it happens to be the first such user in
    collection order. Fix: reset `async_client._async_client = None` in a fixture (and ideally
    session-wide for async-Redis users) so the client is created on the running loop.

  **Non-blocking, recorded for follow-up:** R2-2 (LOW — expiring-token blocklist TTL still
  fake-only; add a real-Redis case asserting `0 < ttl <= formula`), R2-3 (INFO — clarify in the
  Risks sunset note that legacy *access* tokens replayed as refresh cookies are bounded by
  `jwt_access_token_expire_minutes`, not `jwt_refresh_token_expire_days`), R2-4 (INFO — `if jti:`
  guard skips the socket blocklist check, mirroring `jwt_dep`), R2-6 (INFO — router duplicates the
  floor condition the command owns).

  No archive/lifecycle flip performed; this stays `under_construction` pending the two test fixes.

- `2026-07-30` — Round 2 test-integrity fixes for R2-1, R2-5, and R2-2.

  - **R2-1 fixed:** `jwt_dep` now resolves the blocklist reader through the
    `services.infra.auth` module at call time, and `infra.auth` resolves the Redis client through
    the `async_client` module at call time. This restores the existing `fake_redis` seam without
    changing production behavior. The floor-logout revocation test now requires `401 "Token has
    been revoked."`; the companion outage test requires `401 "Auth blocklist unavailable."`.
    Before the seam fix, the new discriminating assertion failed with the unavailable detail,
    proving the old status-only assertion was a false positive.
  - **Mutation check:** temporarily changed `is_token_blocklisted` to always return `False` and
    ran `pytest tests/unit/services/commands/auth/test_logout_user.py -q -k
    permanently_revokes`; it failed with `DID NOT RAISE HTTPException`. The production reader was
    restored immediately after the check.
  - **R2-5 fixed:** the real-Redis TTL module now uses a function-scoped fixture that clears a
    prior async Redis singleton before each test and closes/resets the client it creates. This
    prevents a client created on a previous pytest event loop from being reused by the TTL gate.
  - **R2-2 fixed:** added a real-Redis expiring-token TTL test that asserts the blocklist key was
    written and `0 < TTL <= exp_remaining + 60`; the permanent floor-token case continues to seed
    an expiring value and assert Redis returns `TTL == -1` after production logout.
  - **Validation:**
    `pytest tests/unit/services/commands/auth/test_logout_user.py -q` → `6 passed`;
    `pytest tests/integration/services/commands/auth/test_logout_user_integration.py -q` →
    `2 passed`; socket suites followed by that integration module → `5 passed`; normal-order
    `pytest tests -q -k "auth or sign_in or token or logout or refresh"` → `78 passed`, `1`
    known pre-existing custom-workspace-specialization failure, `1225 deselected`; and the auth
    command directory → `33 passed`, the same `1` known failure. Touched-file `ruff check` passed.
    The quiet-tree full suite was also run and reported `321 failed, 986 passed, 2 errors`; this
    does not match the canonical `ccdffa9` baseline (`27 failed, 1275 passed`) and needs separate
    environment/baseline triage. Its auth-namespace failure was only the known specialization test.
  - **R2-3/R2-4/R2-6:** left unchanged. They are documented review observations requiring broader
    policy or contract decisions, outside this test-integrity fix cycle.

  No archive/lifecycle flip performed; this stays `under_construction` pending reviewer approval.

- `2026-07-30` — Round 3 re-review (test integrity only; N1–N7 treated as CLOSED at `b8946fe`
  and not re-litigated). Verdict: **APPROVED**. All four verification targets confirmed by
  executed probes on a quiet tree at `6ffe397`.

  **(1) Blocklist seam patchable; production behavior unchanged.** The entire production delta of
  `12bbeb7` is four token-level edits converting direct-symbol imports to module-attribute lookups
  (`jwt_dep.py:9,65`; `infra/auth.py:2,6`), confirmed by `git diff --word-diff`. Function bodies,
  call arguments, and exception paths are byte-identical; only name binding moved from import time
  to call time. `services/infra/__init__.py` is empty, so no new import side effect or cycle is
  introduced, and `infra/redis/__init__.py` already executed under the previous submodule import.
  Note the seam choice is *better* than the fix the round-2 log proposed: patching
  `async_client.get_async_redis` keeps the real `is_token_blocklisted` in the path, so the test
  still exercises real key construction (`{prefix}:auth:blocklist:{jti}`), whereas stubbing
  `jwt_dep.is_token_blocklisted` at its point of use would have removed that from coverage.

  **(2) Revocation tests assert the REASON; mutation check reproduced independently.** Two
  mutations were applied to `infra/auth.py:is_token_blocklisted` and reverted:
  - forced `return False` → `test_floor_logout_permanently_revokes_subsequent_request` fails with
    `Failed: DID NOT RAISE <class 'fastapi.exceptions.HTTPException'>` (reproduces the
    implementer's reported result exactly);
  - forced `raise RuntimeError` → the same test fails with
    `AssertionError: assert 'Auth blocklist unavailable.' == 'Token has been revoked.'`.

  The second mutation is the decisive one: it is precisely the false positive that the old
  status-only assertion admitted, and the new `detail` assertion now kills it. `"Token has been
  revoked."` (`test_logout_user.py:102`) and `"Auth blocklist unavailable."` (`:128`) are
  confirmed distinguishable. Working tree restored to pristine `HEAD` after each mutation.

  **(3) N5 gate is deterministic.** `test_floor_logout_blocklist_has_no_ttl_in_real_redis`:
  strictly alone → `1 passed`; module alone → `2 passed`; unit-logout module first (the
  previously-failing order) → `8 passed`; socket suites first → `5 passed`. The
  `fresh_async_redis_client` fixture was confirmed **load-bearing**, not incidentally green:
  removing it from both test signatures reproduces
  `RuntimeError: ... got Future <Future pending> attached to a different loop` and
  `RuntimeError: Event loop is closed`. Restored after the probe. `redis_client` was verified to
  be a genuine server (`PING True`, `redis://localhost:6379/0`, Redis 8.6.1), so R2-2's
  real-Redis expiring-TTL claim holds.

  **(4) No production defense logic changed vs `b8946fe`.** The only other production files in the
  `b8946fe..12bbeb7` range (`domain/users/serializers.py`,
  `services/commands/users/clock_out_worker_shift.py`) belong to phase 4's `ccdffa9`, confirmed via
  `git log -- <paths>`; neither touches the auth surface.

  **Suite reconciliation (node sets, not counts).** Codex's `321 failed / 986 passed` is confirmed
  contamination and should be disregarded. Quiet-tree run at `6ffe397`: **27 failed / 1280 passed**
  in 35.21s — matching the operator's measurement exactly. To isolate this commit's regression
  impact the parent `6c33fc2` was run in a dedicated worktree: **27 failed / 1275 passed**, and a
  sorted `diff` of the two failure-node lists is **empty — identical failure node sets**, +5 net
  passing, zero new failures. The single auth-namespace failure
  (`test_sign_in_user_preserves_custom_workspace_role_name`) is present in both sets and is the
  known pre-existing specialization failure. `ruff check` on all four touched files: clean.
  Restored-tree auth surface re-run: `45 passed`, that 1 known failure.

  **New non-blocking finding:**

  - **R3-1 — LOW (test integrity, pre-existing; not introduced by `12bbeb7`) — two floor-refresh
    tests are tautological with respect to the blocklist.**
    `tests/unit/test_auth_router.py:201` and
    `tests/unit/services/commands/auth/test_refresh_token.py:110` are both named for blocklist
    enforcement, but `refresh_token.py:18-21` rejects `app_scope == "floor"` with
    `reason="floor_scope_not_refreshable"` *before* the blocklist read at `refresh_token.py:48`.
    Proven with a call-recorder probe (not inference): the router test passes while asserting
    `BLOCKLIST READER CALLS: []` — the stubbed reader is never invoked; the command-level twin
    asserts only a bare `pytest.raises(RefreshTokenRejected)` with no `reason`, so any rejection
    satisfies it. Both would pass identically if the blocklist branch were deleted.
    **This is a naming/evidence-description defect, not a coverage hole, and not a security
    issue:** for floor scope the real defense *is* the scope guard (separately pinned at
    `test_refresh_token.py:147`), and the blocklist branch itself has sound discriminating coverage
    on the non-floor path — `test_revoked_non_floor_refresh_token_is_rejected` asserts
    `reason == "refresh_token_revoked"` (`:206`) and `test_refresh_fails_closed_when_blocklist_is_unavailable`
    asserts `reason == "refresh_blocklist_unavailable"` (`:317`). Suggested follow-up: rename both
    to reflect that they pin the scope guard, and add the `reason` assertion to the command-level
    one. By contrast the N2 socket gate was probed the same way and is **sound** — a call recorder
    confirmed `_calls == ["revoked-socket-jti"]`, so the reader is genuinely reached there.

  All probe mutations were reverted; `git status` clean at `6ffe397` with no stray worktrees.

## Lifecycle transition

- Current state: `archived`
- Next state: `approved`
- Transition owner: `David`
