# SUMMARY_declared_worker_states_phase5_device_auth_20260729

## Metadata

- Summary ID: `SUMMARY_declared_worker_states_phase5_device_auth_20260729`
- Status: `summarized`
- Owner agent: `Codex` (implementation + 2 fix cycles) / `Opus` (review ×3) / `claude-fable-5` (lifecycle)
- Created at (UTC): `2026-07-30T13:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase5_device_auth_20260729.md`
- Master plan: `.../under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (Phase 5 of 7)
- Commits: `549f480` (implementation) → `b8946fe` (N1–N6 security fixes) → `12bbeb7` (R2-x test integrity)

## What was implemented

- **New `floor` app scope** (ADMIN + MANAGER only) for the always-on shop-floor device. Sign-in with
  `app_scope="floor"` issues an access token with **no `exp` claim** (all other claims identical to a
  manager token — proven by claim-parity probe), retains `jti`, and issues **no refresh token and no
  refresh cookie**.
- **Permanent revocation**: logout of an `exp`-less token writes its `jti` to the Redis blocklist
  **with no TTL** (`TTL == -1`), asserted against a real Redis server.
- **`jti` in the floor sign-in structured log** so a lost device can be revoked by ops without
  holding its token (the plan's documented fallback was previously unusable — finding N3).
- **PyJWT missing-`exp` behavior pinned** by unit test (PyJWT 2.10.1); no far-future-`exp` hack.
- Existing scopes (`manager`/`worker`/`seller`/`admin`) unchanged: same TTLs, refresh cookies and
  logout semantics.

## The critical security finding (N1) and its fix

**The independent reviewer executed a working revocation bypass against `549f480`.** A permanently
blocklisted floor *access* token, replayed as the `floor_refresh_token` cookie, was accepted by
`refresh_token()` — no blocklist check, no token-type check, and no `exp` to reject — minting a
fresh, non-blocklisted token. Repeatable indefinitely. The access-token-as-refresh-token confusion
was pre-existing for every scope, but TTLs bounded it; a non-expiring floor token made it
**unbounded and permanent**, nullifying D11's entire risk model: a "revoked" lost device would have
stayed live forever.

**Fixed with four independent layers** (operator decision: defense in depth — a security boundary
must not rest on one check):

1. `scope == "floor"` is hard-rejected at refresh (floor sessions are issued no refresh token).
2. The presented token's `jti` is blocklist-checked before anything is minted — for every scope.
3. `exp`-less tokens are rejected at refresh (structurally an access token under this design).
4. `token_type` discrimination: new refresh tokens carry `token_type: "refresh"`; the accept rule is
   a closed allow-list, with a legacy transition branch for outstanding `exp`-bearing, type-less
   cookies (sunsets after `jwt_refresh_token_expire_days` from deploy). `jti`-less refresh is also
   rejected so the blocklist cannot be dodged.

**Verification (round 2):** 19 mock-free probes on N1 alone — real Redis, real PyJWT, tokens minted
by production `build_auth_response` on real ORM rows — including cross-scope replay
(manager/worker/admin/seller) and casing variants to dodge layer 1. Every layer isolated with a
control (e.g. a revoked non-floor refresh is rejected while an identical un-revoked one still
succeeds).

- **N2 (HIGH)**: socket auth never checked the blocklist — an `exp`-less token would have
  authenticated WebSockets forever after revocation. Fixed and probed (6 probes), including
  fail-closed on a real Redis outage and the query-string token path.
- **N4 / N7**: accepted-and-documented operator decisions — demoting a manager does not invalidate an
  already-issued floor token (claims are static; offboarding must revoke the device — disclosed in
  handoff §2), and `require_app_scope` is intentionally unused until Phase 6 introduces the first
  floor-gated surface.

## Test-integrity round (R2-x) — why it mattered

Round 2 approved the security fixes but blocked on evidence: the revocation test **passed for the
wrong reason**. Moving the blocklist read to a module-level import broke the fake-Redis seam; in
whole-suite order the loop-bound async client raised, `_is_blocklisted` failed closed into
`401 "Auth blocklist unavailable."`, and the test asserted `status_code` only — so it would have
kept passing with the revocation check deleted.

Fixed in `12bbeb7`:
- **Seam restored** as module-attribute lookup (four token-level edits; `--word-diff` confirmed
  bodies byte-identical, binding moved from import time to call time). The reviewer noted this seam is
  **better than round 2 proposed**: patching `async_client.get_async_redis` keeps the real
  `is_token_blocklisted` — and therefore real key construction — in the covered path, whereas
  stubbing at the point of use would have removed it from coverage.
- **Discriminating assertions**: revocation tests assert `"Token has been revoked."`, with a companion
  test asserting the distinct `"Auth blocklist unavailable."` path. Reviewer re-ran both mutations
  independently: `return False` → test fails (`DID NOT RAISE`); `raise RuntimeError` → test fails on
  the detail comparison — the exact false positive the old assertion admitted.
- **N5 gate de-fragilised**: the real-Redis TTL test was green by collection accident (async loop
  binding). A function-scoped client fixture makes it deterministic — verified alone, in-module,
  after the previously-failing unit order, and after the socket suites; and proven load-bearing by
  removing the fixture and reproducing the loop error.
- **R2-2**: the expiring-token TTL case now also runs against real Redis (`PING True`, Redis 8.6.1).

## Contract adherence

- `10_auth.md` / `18_security.md`: token issuance, blocklist semantics, credential-error opacity
  (wrong-role floor sign-in returns the same `403 "Invalid credentials."` as a wrong password).
- `12_infra_redis.md`: blocklist key conventions; no-TTL entries for `exp`-less tokens.
- `06_commands.md` / `09_routers.md`: cookie handling stays in the router; auth commands unchanged in
  structure.

## Validation evidence

- Three independent review rounds; final **APPROVED** at `12bbeb7`.
- Node-set discipline: reviewer's quiet-tree run at `6ffe397` = 27 failed / 1280 passed, matching the
  operator's measurement; parent `6c33fc2` in a separate worktree = 27 failed / 1275 passed; sorted
  FAILED-node diff **empty** — +5 net passing, zero new failures. ruff clean on all touched files.
- Codex's own 321-failure run was shared DB/Redis contention (Phase 4 session running concurrently)
  — confirmed and disregarded by the reviewer.

## Known gaps or deferred items

- **R3-1 (LOW, pre-existing, non-blocking)**: two floor-refresh tests
  (`test_auth_router.py:201`, `test_refresh_token.py:110`) are **tautological w.r.t. the blocklist** —
  the floor-scope guard fires before the blocklist read, so a call-recorder probe shows
  `BLOCKLIST READER CALLS: []` while the test passes. A **naming defect, not a coverage hole**: for
  floor scope the real defense is the scope guard (separately pinned), and the blocklist branch has
  sound discriminating coverage on the non-floor path. Fix = rename the tests to say what they
  assert. Scheduled as a trivial rename alongside Phase 6.
- **Accepted risk (D11)**: a leaked floor token never expires. Bounded by ADMIN/MANAGER-only scope,
  opaque credential errors, sign-in rate limiting, permanent-revocation logout, and the ops blocklist
  path (now usable thanks to N3's `jti` logging). Revocation latency ≤60s (claims cache).
- **N4**: role demotion does not invalidate issued floor tokens — offboarding must revoke the device.
- Permanent blocklist entries accumulate (one per retired device session; negligible volume).

## Handoff notes

- `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §2 verified field-for-field; the floor
  sign-in/logout row is flipped to ✅ at finalization. §2 also carries the operator-added offboarding
  disclosure (N4) and the ≤60s revocation-latency note.

## Lifecycle transition

- Plan archived to `backend/docs/architecture/archives/implementation/declared_worker_states/`.
- Master plan Phase 5 → `archived`. **Phase 6 is now unblocked** (Phases 3, 4, 5 all archived).
