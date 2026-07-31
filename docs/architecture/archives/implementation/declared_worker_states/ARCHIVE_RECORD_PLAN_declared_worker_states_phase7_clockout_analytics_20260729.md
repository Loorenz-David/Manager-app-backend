# ARCHIVE_RECORD_PLAN_declared_worker_states_phase7_clockout_analytics_20260729

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_declared_worker_states_phase7_clockout_analytics_20260729`
- Archived at (UTC): `2026-07-31T00:00:00Z`
- Archive owner agent: `claude-opus-5` (on operator direction, post-approval + F13/F14 fast-follow)

## Source references

- Plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase7_clockout_analytics_20260729.md` (rev 2)
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_declared_worker_states_phase7_clockout_analytics_20260729.md`
- Master plan (intention role): `.../under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Debug chain: none

## Outcome classification

- Result: `completed_after_fixes` — **NEEDS_CHANGES** on round 1 (`claude-opus-5`, blocking F1/F2/F3),
  **APPROVED** on re-review (`claude-sonnet-5`) with all three blockers reproduced as fixed under the
  reviewer's own mutation probes. F13/F14 closed in a post-approval, pre-archive fast-follow.
- Rev 2 rewrote the phase and absorbed the former Phase 8: the `get_worker_linear_timeline_breakdown`
  seam extraction and both `segments[]` and `insights` were dropped by operator ruling — the kiosk
  renders totals only, and its comparison rows are unit-based, which the time-based insights engine
  cannot express. `rate` replaced `insights`.
- Operator rulings embedded: `total_seconds` = `TaskStep.total_working_seconds` only (the
  `working + pause + ended_shift` alternative was rejected as inflating the card with non-productive
  time); no shift scheduling (it does not exist); F15 deferred rather than built.

## Behaviour change outside this phase's scope (must not be lost)

`_load_step_and_primary_item` in `services/queries/worker_stats/get_worker_linear_timeline_breakdown.py`
was rewritten during the round-1 fixes: the intermediate map went from `{item_id: task_id}` to
`{task_id: item_id}`. The old keying collapsed an item that is PRIMARY on two tasks into one entry,
dropping the other task's mapping.

**This changed a shipped surface the plan scoped read-only** — the helper also backs the manager-facing
linear-timeline breakdown endpoint (`GET /users/{user_id}/linear-timeline/breakdown`), where the old
keying rendered `"item": null` for the dropped task's step details. The fix is correct and was kept, but
it shipped with no test and no Review log entry and was found only by diffing against `HEAD`. It is now
disclosed in the Review log and covered by a mutation-verified test on the **breakdown** endpoint
(`test_step_details_resolve_the_primary_item_of_each_task`), which fails against the old keying while all
five pre-existing tests in that file still pass.

The lesson generalises: acceptance criterion 14's "manager worker-stats endpoints untouched" check is
exactly what should have caught this, and reading the diff — not just the tests — is what did.

## Known gap carried past archive

**F15 — no fixture exercises a shift that literally spans a UTC midnight boundary.** Every seeded shift
in the Phase 7 suite begins and ends inside one day, or sits at a boundary at :00/:10. Acceptance
criterion 5 explicitly names a midnight-spanning shift, so this is an accepted shortfall against it, not
a satisfied criterion: `timeline` and `week` bucketing across a true midnight split is verified only
transitively through the shared `build_recorded_shift_timeline` helper's own test suite. Deferred by
operator ruling; anyone touching week bucketing should build this fixture first.

Also carried: F7's residual (the `rate` baseline dedups per item by construction and matches today's
units, but the baseline side is not stress-tested with duplicate completions).

## Final notes

- The kiosk is complete end to end: floor sign-in → roster with codes and working sections → confirm →
  `GET /current` → clock-in / declare / clock-out with a full day summary at the clock-out moment.
- The anti-drift property is the design's core: kiosk day totals and the manager roster's come from the
  same `build_recorded_shift_timeline` call, asserted equal to a same-range computation rather than to
  hard-coded numbers, so the two surfaces cannot silently diverge.
- Round 1's three blockers are each worth remembering as a class:
  **F1** — a raised limit placed in the query service is invisible to FastAPI's `Query(...)` validator, so
  the cap never actually moved; service-layer tests cannot see a router-level cap.
  **F2** — a regression test that signals failure by raising inside code wrapped in `except Exception`
  cannot fail. The fix records the call and asserts it never happened.
  **F3** — adding an internal key to a command's return dict breaks direct-caller tests even when the
  HTTP boundary pops it.
- Suite discipline held: the re-reviewer built its own `git worktree` at `f26ecc6` and diffed sorted
  `FAILED` node sets rather than counts — diff empty, +18 = the new tests.
- **This was the final phase.** With Phase 7 archived, all seven phases of the declared-worker-states
  feature set are complete.
