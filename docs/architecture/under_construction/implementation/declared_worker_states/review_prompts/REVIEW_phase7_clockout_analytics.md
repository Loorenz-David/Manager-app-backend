# Review prompt — Declared Worker States, Phase 7: clock-out analytics envelope

You are reviewing an implementation made by another agent (Codex) in the ManagerBeyo backend (`backend/`). Your job is adversarial verification. Do not fix anything — report.

## Inputs

- Master plan (decision D14 rev 2): `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Phase plan under review: `.../declared_worker_states/PLAN_declared_worker_states_phase7_clockout_analytics_20260729.md`
- Frontend contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §5
- The implementation diff: `git log`/`git diff` for the phase's commits.

## Review protocol

1. Read D14 rev 2, the phase plan, then the diff completely.
2. Map every acceptance criterion to concrete evidence; re-run the validation plan yourself.
3. Record findings in the phase plan's Review log and report them in your reply.

## Phase-specific checklist

- [ ] `analytics` carries exactly the six documented keys (`date`, `timeline`, `segments`, `segments_truncated`, `pause_reasons`, `insights`) built from EXISTING serializers — grep for new hand-rolled dict shapes duplicating `serialize_linear_timeline`/`serialize_recorded_shift_segment`/`serialize_insight`; duplication is a blocking finding.
- [ ] Seam extraction: the manager breakdown route delegates to the same function the composite calls; the route's existing tests are UNMODIFIED and green. Diff the extraction line-by-line for behavior changes (default args, date handling, truncation).
- [ ] Equivalence contract test exists: clock-out `analytics.timeline`/`segments` ≡ `GET /worker-stats/{user_id}/linear-timeline` for the same user/day.
- [ ] Composition runs AFTER the write transaction — inspect the wiring: no analytics queries inside the `maybe_begin` block holding the clock-out locks; `clock_out_shift_for_user` diff is empty (or import-only).
- [ ] Degradation proven: monkeypatched exception → `200`, shift closed, `analytics: null`, structured error log (`worker_shift.clock_out_analytics_failed`) asserted. Confirm the except clause is scoped to the composition only (it must not swallow clock-out errors).
- [ ] `/clock` toggle: clock-out branch has populated `analytics`; clock-in branch has no such key.
- [ ] Safeguard + Connecteam suites unmodified and green; no analytics import reachable from `services/tasks/`.
- [ ] Work date = UTC date of `clock_out_at`; declared segments in `analytics.segments` carry `manually_recorded: true` + resolvable reason (test evidence).
- [ ] **Actor/target split**: grep the composite and its call sites for `ctx.user_id` / `ctx.identity` — the analytics queries must use only the resolved target worker id (plan acceptance 1b). The on-behalf test (manager with own same-day activity clocking out a worker) exists and passes; any actor-id leakage into an analytics query is a blocking finding.
- [ ] `timeline.pause_by_reason` sums to `timeline.pause_seconds` (invariant test).
- [ ] Latency measurement recorded in the Review log with the seeded-day description.
- [ ] Handoff §5 conformance verified field-for-field; status row flipped.
- [ ] Full suite green; ruff clean.
- [ ] Final-phase lifecycle: master archived + folder moved ONLY after this review approves.

## Adversarial probes (attempt at least these)

- Clock out a worker with a still-open declared state and a still-open working step: `analytics` must show the declared segment clamped at clock-out and the step force-closed — consistent with `transitioned_steps`.
- Clock out a worker whose analytics worker was "down" all day (no live reconcile writes): rebuilt `analytics` still correct (leans on Phase 2).
- Clock out a worker with zero activity (clock-in → clock-out, nothing else): `analytics.timeline` is all idle, `segments` well-formed, `insights` empty or valid — no division-by-zero/empty-day crash.
- Insights staleness: assert the response is served even when `UserDailyWorkStats` has no row for today.

## Verdict

End your report with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated clause, severity).
