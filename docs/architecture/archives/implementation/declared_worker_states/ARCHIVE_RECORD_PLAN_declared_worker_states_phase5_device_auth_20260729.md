# ARCHIVE_RECORD_PLAN_declared_worker_states_phase5_device_auth_20260729

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_declared_worker_states_phase5_device_auth_20260729`
- Archived at (UTC): `2026-07-30T13:00:00Z`
- Archive owner agent: `claude-fable-5` (on operator direction, post-approval)

## Source references

- Plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase5_device_auth_20260729.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_declared_worker_states_phase5_device_auth_20260729.md`
- Master plan (intention role): `.../under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Debug chain: none (handled in-review across 2 fix cycles / 3 rounds)

## Outcome classification

- Result: `completed_after_critical_security_finding_and_fix_cycles`
- Acceptance criteria: all met. Final APPROVED at `12bbeb7` after three independent review rounds.
- **This phase's review caught the most serious defect of the feature set**: an executed revocation
  bypass (blocklisted floor access token replayed as the refresh cookie mints fresh tokens forever),
  which nullified D11's entire risk model. Fixed with four independent defense layers and verified by
  19 mock-free probes including cross-scope replay.
- Round 2 then blocked on *evidence quality* rather than behavior: the revocation test passed for the
  wrong reason (broken fake-Redis seam + `status_code`-only assertion) and would have kept passing
  with the revocation check deleted. Closed with a restored patchable seam, reason-discriminating
  assertions, and mutation checks re-run independently by the reviewer.

## Final notes

- The floor device can now be trusted: non-expiring token, permanently revocable, revocation
  enforced at HTTP, refresh and socket paths, with the ops revocation path made usable by logging
  `jti` at sign-in.
- Accepted residual risks are documented in the summary (D11 leaked-token profile, N4 static claims
  on demotion, ≤60s revocation latency, permanent blocklist growth).
- R3-1 (tautological floor-refresh test names) is carried as a trivial rename; it is a naming defect,
  not a coverage or security hole, and was proven so by a call-recorder probe.
- Reviewer improvement worth reusing: the chosen seam patches `async_client.get_async_redis` rather
  than the point-of-use symbol, keeping real key construction inside the covered path — preferable to
  the operator's original round-2 suggestion.
- Process note: a Codex full-suite run reported 321 failures purely from shared DB/Redis contention
  with the concurrent Phase 4 session. Quiet-tree truth: 27 failed / 1280 passed, node sets identical
  to parent.
