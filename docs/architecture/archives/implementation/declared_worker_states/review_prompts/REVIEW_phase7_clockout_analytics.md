# Review prompt — Declared Worker States, Phase 7 (FINAL): clock-out analytics

You are performing an independent, adversarial code review. Work from the repo files; assume no prior
conversation. Do not fix anything — report.

## Inputs

- Plan under review: `.../declared_worker_states/PLAN_declared_worker_states_phase7_clockout_analytics_20260729.md (read rev 2)`
- Implementer prompt (constraints they were held to): `.../codex_prompts/PROMPT_phase7_clockout_analytics.md`
- Contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §3, §5.1, §5.3
- Frontend requirement: `docs/handoff/from_frontend/BACKEND_REQUIREMENTS_clock_kiosk_20260729.md`
- Master plan incl. the "Repository validation baseline" section.

## Checklist

- [ ] `completed_items` field-for-field per §5.1. `reference` fallback tested in all three cases
      (article_number → sku → null). `image_url` null when no linked image; the "first image" rule is
      **deterministic** (assert it, don't accept incidental ordering). `issues_count` matches
      `ItemIssue` rows. `working_section` comes from the completing step and is null-safe.
- [ ] `total_seconds` definition is recorded in the Review log and matches what the code computes —
      and the handoff's task-level caveat is accurate. If they diverge, that is a finding.
- [ ] Empty case: a worker who completed nothing gets `[]`, not absent/null.
- [ ] `week` = Mon–Sun of the clock-out date, all days present (zeros for no-shift), buckets equal to a
      same-range `build_recorded_shift_timeline` computation, `totals` == sum of `days` (invariant
      assertion, not hard-coded numbers). Confirm `UserDailyWorkStats` was NOT used.
- [ ] **Query budget** — the acceptance criterion most likely to be faked. Verify the listener actually
      counts (mutate to a per-item / per-day loop and confirm the test fails). One range query for the
      week; batched loads for images, sections, issue counts.
- [ ] Degradation: force an exception in each new composer → `analytics: null` **in full** (not
      partial), clock-out still `200`, shift closed, structured error log.
- [ ] Floor roster sections: probe the **real ASGI app** (`create_app()` + minted tokens, so middleware
      and `require_roles` are in the path) — present for floor, **absent (not null)** for
      manager/worker/admin/seller in compact AND full modes. Item shapes otherwise byte-identical.
- [ ] Roster cap: >200-worker workspace fully reachable; test exists with >200 rows.
- [ ] Untouched: manager worker-stats endpoints, shared serializers, Phase 4's `analytics: null`
      pinning tests, Connecteam, midnight safeguard (empty diffs / unmodified tests).
- [ ] `/clock` toggle's clock-out branch carries the same `analytics`; its clock-in branch has no
      such key.
- [ ] Multi-tenancy: every new query workspace-scoped — probe an item/issue/section from another
      workspace cannot leak in.
- [ ] Actor/target split: on-behalf clock-out returns the **worker's** items and week, never the acting
      manager's (acceptance 2 — the acting manager should hold their own same-day activity that must not appear).
- [ ] Suite: quiet tree, failure **node sets** compared against a baseline worktree (diff must be
      empty); ruff clean on touched files. Reject any count-only comparison.

## Adversarial probes (attempt at least these)

- An item completed twice / by two workers on the same day — no duplicate cards, correct attribution.
- An item whose task has multiple items — verify the mapping picks the right one and `total_seconds`
  isn't double-counted across cards.
- A clock-out spanning midnight or on a Monday — week boundaries hold.
- An item with a soft-deleted image link or a soft-deleted section — null-safe, no 500.
- A worker with >the defensive cap of completed items — truncation surfaced, not silently dropped.

## Rev-2 specific checks (this phase was rewritten)

- [ ] **No seam was extracted** from `get_worker_linear_timeline_breakdown`, and NO `segments[]` or
      `insights` keys are emitted. Rev 1 planned both; rev 2 dropped them. Their presence is a finding.
- [ ] `timeline` comes from the SHARED `build_recorded_shift_timeline` helper (anti-drift property) —
      assert it equals a same-range computation, and confirm the helper was not copied/forked.
- [ ] `pause_reasons` resolves every key present in `timeline.pause_by_reason`.
- [ ] `rate`: `units_per_hour` consistent with `completed_items` units and `timeline.working_seconds`;
      `baseline_days: 0` → `baseline_units_per_hour: null` (first-ever shift); baseline computed
      without per-day round trips.
- [ ] Carried Phase 6 items delivered: the index-name constant is pinned to the model's `Index` with a
      test that exercises the `IntegrityError → 409` race, and the duplicate-code `409` message
      mentions a possible inactive holder.
- [ ] Composite latency measured and recorded in the Review log.

## Verdict

End with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated clause,
severity). Record findings in the plan's Review log; that should be the only file you modify.
