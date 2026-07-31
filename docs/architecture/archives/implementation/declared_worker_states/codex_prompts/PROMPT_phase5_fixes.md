# Codex prompt — Phase 5 FIX CYCLE (review verdict: NEEDS_CHANGES — CRITICAL security finding)

You are fixing review findings on the Phase 5 implementation (`backend/`), commit `549f480`. The
findings, with an executed exploit probe, are in the **Review log** of
`backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase5_device_auth_20260729.md`.
Read that first. Parallel-run discipline still applies: touch ONLY the auth surface (+ socket auth
handler for N2) and your phase plan's Review log.

## N1 (CRITICAL): revocation is bypassable via /auth/refresh

Proven exploit: a permanently blocklisted floor ACCESS token, replayed as the
`floor_refresh_token` cookie, is accepted by `refresh_token()` (no blocklist check, no
token-type check, no exp to reject) and mints a fresh non-blocklisted token — repeatable forever.
The access-token-as-refresh-token confusion is pre-existing for every scope, but TTLs bounded it;
floor makes it unbounded. **Fix ALL FOUR layers (defense in depth):**

1. **Hard-reject `scope == "floor"` in `refresh_token()`** — floor sessions are issued no refresh
   token by design; any floor refresh attempt is invalid by construction.
2. **Blocklist-check the presented token's `jti`** in `refresh_token()` before minting anything —
   a revoked credential must never refresh, in any scope.
3. **Reject `exp`-less tokens at refresh** — a token without `exp` is structurally an access
   token under this design and can never be a refresh credential.
4. **Type-discriminate tokens going forward:** new refresh tokens carry `token_type: "refresh"`
   at issuance (all scopes); `refresh_token()` accepts `token_type == "refresh"` OR — legacy
   transition — a token WITH `exp` and WITHOUT `token_type` (outstanding 30-day cookies keep
   working; document the sunset: the legacy branch can be removed after
   `jwt_refresh_token_expire_days` from deploy). Access tokens (with or without `exp`) never
   pass.

**Required tests:** the reviewer's exact probe as a regression test (blocklisted floor token →
refresh → MUST reject); floor-scope refresh always rejects even with a valid token; revoked
NON-floor refresh token → rejected (layer 2 for all scopes); access-token-as-refresh-cookie for a
regular scope → rejected via layer 4; legacy `exp`-bearing type-less refresh token → still works
(transition); new refresh tokens carry `token_type`.

## N2 (HIGH): socket auth never checks the blocklist

`handlers.py:22-38` authenticates WebSockets without `_is_blocklisted`. Pre-existing, but an
`exp`-less floor token authenticates sockets FOREVER after revocation — in-scope because this
phase created unbounded tokens. Add the blocklist check to socket auth (mirror `get_jwt_claims`
semantics, incl. fail-closed). Test: revoked token → socket auth rejected.

## N3 (MEDIUM): jti never logged — ops revocation path is fictional for a lost device

Add `jti` to the floor sign-in structured log (and to the logout log if absent). Then write the
one-paragraph ops runbook into the plan (Risks section): lost device → find the device's floor
sign-in log line (user/time) → take its `jti` → `SET <prefix>:auth:blocklist:<jti>` with no TTL.
Test: the log record contains the jti of the issued token.

## N4 (MEDIUM — OPERATOR DECISION: accept + document, no live re-check)

Demoting/deactivating a manager does not invalidate their existing floor token (claims are
static; `get_jwt_claims` never re-reads the DB). **Decision: accepted limitation** — a floor
device is business-owned hardware and offboarding must revoke its token explicitly; a per-request
DB role re-check is disproportionate. The handoff §2 already carries the operator-added
disclosure. You: document the same limitation + offboarding requirement in the plan's Risks
section. No code.

## N5 (LOW): make the TTL evidence real

The `TTL == -1` assertion runs against `_FakeRedis` whose `ttl()` returns `-1 if ex is None` —
tautological. Add/convert an integration test asserting `TTL == -1` against REAL Redis (the
integration suites already have it), and correct the Review-log evidence claim.

## N6 (LOW): restore loud failure

`data.pop("_refresh_token", None)` silently tolerates a missing refresh token for ANY scope.
Make the control flow explicit: floor → no pop, no cookie; every other scope → `data.pop("_refresh_token")`
(hard KeyError restored).

## N7 (INFO): no action here — pinned for Phase 6

`require_app_scope` is referenced by zero routes, so a floor token is currently a full
ADMIN/MANAGER API credential. Phase 6 introduces the first floor-gated surface. Add one sentence
to the plan's Non-goals acknowledging this is intentional at this phase.

## Protocol

1. Fix on top of `549f480`. The N1 probe-regression test comes FIRST and must fail against the
   current code before the fix.
2. Re-run the phase Validation plan + baseline rule (no NEW failures; existing-scope refresh
   flows byte-identical except the four documented rejection layers; touched files ruff-clean).
3. Append a fix-cycle entry to the plan's Review log (per finding: change + pinning test).
4. **Do NOT archive/summarize/flip anything** — back to the reviewer
   (`review_prompts/REVIEW_phase5_device_auth.md`) after; archive only on APPROVED.
5. One fix commit referencing N1–N6. Stage only auth-surface + socket-handler + plan files.
