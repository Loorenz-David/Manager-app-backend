# Codex prompt — Phase 5 FIX CYCLE, ROUND 2 (verdict: NEEDS_CHANGES — test integrity only)

Round-1 security findings **N1–N7 are verified CLOSED** by the reviewer with mock-free probes
(real Redis, real PyJWT, production token minting): 19 probes on N1 incl. cross-scope replay and
casing variants, all four defense layers isolated with controls; N2 fail-closed confirmed; N3/N6
closed; legacy transition branch works and is blocklist-checked. **No production-code change is
required by this round** — do not touch the defense logic.

The remaining findings are about **test integrity**, and they matter: the revocation test
currently passes for the WRONG REASON, so the security property has no sound evidence even though
it is genuinely implemented. Full details in the Review log of
`.../declared_worker_states/PLAN_declared_worker_states_phase5_device_auth_20260729.md`.

**Parallel-run discipline:** Phase 4 is active in this tree. Touch ONLY auth/socket/test files and
your own plan. Stage explicitly — never `git add -A`.

## R2-1 (MEDIUM) — restore the patchable seam AND make the assertion discriminating

`b8946fe` moved the blocklist read to a module-level import (`infra/auth.py:2`, `jwt_dep.py:9`),
breaking the fake_redis seam: `pytest tests/unit/services/commands/auth` goes from `1 failed,
24 passed` at parent `e57aab7` to `2 failed, 31 passed`. In whole-suite order it *passes* — but
only because the loop-bound async Redis singleton raises, `_is_blocklisted` converts that to
`HTTPException(401, "Auth blocklist unavailable.")`, and the test asserts `status_code` only.
A revoked-token test that also passes when Redis is simply broken proves nothing.

**Two-part fix, both required:**
1. **Seam:** make the blocklist call patchable again — reference it through its module
   (`from beyo_manager.services.infra import auth` … `await auth.is_token_blocklisted(jti)`) or an
   equivalent injectable seam, so unit tests can substitute a fake without import-time binding.
   Behavior in production must be identical.
2. **Discriminating assertions:** every revocation test must assert the 401 is *because the token
   is revoked* — assert on `detail` (or a distinguishable error identity), not `status_code` alone.
   Add a companion negative test: with the blocklist backend unavailable, the failure surfaces as
   the "Auth blocklist unavailable" path and is NOT mistaken for revocation. These two cases must
   be distinguishable by assertion, in both unit and whole-suite ordering.

**Gate:** `pytest tests/unit/services/commands/auth` must be green in isolation AND in whole-suite
order, with the revoked-token test failing if you mutate the blocklist to always-return-False.
State that mutation check in your Review-log entry.

## R2-5 (MEDIUM) — de-fragilise the N5 integration gate

The real-Redis TTL test passes alone but dies with `RuntimeError: … attached to a different loop`
if preceded by any test that touched the async client — it is green today by collection accident.
Fix the loop binding (e.g. function-scoped client/fixture, or dispose/reset the async singleton
between tests) so the test is deterministic in any order. **Gate:** it passes both alone and when
run after `tests/integration/services/commands/auth`-adjacent suites that touch the async client;
show both invocations in the Review log.

## R2-2 / R2-3 / R2-4 / R2-6 (non-blocking)

Address R2-2 if cheap — the expiring-token TTL assertion is still fake-only, so the *positive*
TTL case has the same evidence weakness R2-1 describes; extending the real-Redis integration test
to cover it closes the pair. R2-3/R2-4/R2-6: apply the reviewer's recommendations where they are
one-liners; if any needs a judgement call, note it in the Review log and leave it — do not expand
scope.

## Protocol

1. Fix on top of the current HEAD. For R2-1, write the discriminating assertions FIRST and confirm
   the current tests pass under a broken-blocklist mutation (proving the weakness), then fix.
2. Re-run: focused auth/socket suites in isolation AND in whole-suite order; the N5 gate in both
   orders; full suite on a QUIET tree (no other session running — see the master plan's canonical
   baseline note: 27 failed / 1275 passed at `ccdffa9`); ruff on touched files.
3. Append a round-2 fix entry to the plan's Review log with the mutation-check evidence.
4. **Do NOT archive/summarize/flip anything** — back to the reviewer afterwards; archive only on
   APPROVED.
5. One fix commit referencing R2-1/R2-5 (+ any non-blocking items you addressed).
