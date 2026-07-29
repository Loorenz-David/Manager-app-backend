# Review prompt — Declared Worker States, Phase 5: floor device auth

You are reviewing an implementation made by another agent (Codex) in the ManagerBeyo backend (`backend/`). Your job is adversarial verification — this phase is security-sensitive, so be maximally skeptical. Do not fix anything — report.

## Inputs

- Master plan (decision D11): `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Phase plan under review: `.../declared_worker_states/PLAN_declared_worker_states_phase5_device_auth_20260729.md`
- Frontend contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` (§2)
- The implementation diff: `git log`/`git diff` for the phase's commits.

## Review protocol

1. Read the master decision D11, the phase plan, then the diff completely.
2. Map every acceptance criterion to concrete evidence; re-run the validation plan yourself.
3. Record findings in the phase plan's Review log and report them in your reply.

## Phase-specific checklist

- [ ] `_SCOPE_ALLOWED_ROLES["floor"]` is exactly `{ADMIN, MANAGER}` — no WORKER, no SELLER.
- [ ] Floor access token: decode it in a test and assert `"exp" not in claims` and `"jti" in claims`; all other claims identical to a manager-scope token for the same user.
- [ ] NO refresh token issued for floor and NO `Set-Cookie` on floor sign-in (inspect the actual response headers in a test, not just the body).
- [ ] Logout with an `exp`-less token: blocklist key written with `TTL == -1` (persistent) — asserted against Redis, not inferred. Expiring tokens' blocklist TTL behavior unchanged.
- [ ] Revoked floor token → `401` (test handles/clears the 60s claims cache rather than sleeping).
- [ ] `POST /auth/refresh?scope=floor` → clean rejection, no 500.
- [ ] Credential-error opacity: wrong-role floor sign-in returns the same message/status as wrong-password ("Invalid credentials.").
- [ ] **Regression sweep**: existing scopes' sign-in/refresh/logout tests unmodified and green; no change to `jwt_access_token_expire_minutes` / `jwt_refresh_token_expire_days` usage for non-floor scopes.
- [ ] PyJWT missing-`exp` acceptance pinned by a dedicated unit test (not assumed).
- [ ] No new far-future-`exp` hack anywhere (search for large timedelta/date constants) — the design is no-`exp`, not exp-in-100-years.
- [ ] Response shape matches handoff §2 field-for-field.
- [ ] Structured floor sign-in log present; ruff clean; full suite green.

## Adversarial probes (attempt at least these)

- Sign in with `app_scope="floor"` as a WORKER whose password is correct → must be `403`-opaque, and no token of any kind issued.
- Take a floor token, log out, then hit a protected route within the cache window and after — document the actual revocation latency.
- Tamper the token (strip `jti`) — blocklist check must not be bypassable by removing `jti` while remaining validly signed (it can't be re-signed, but verify claims-cache doesn't resurrect revoked entries past TTL).

## Verdict

End your report with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated clause, severity).
