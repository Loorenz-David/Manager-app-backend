# PLAN_declared_worker_states_phase7_clockout_analytics_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase7_clockout_analytics_20260729`
- Status: `under_construction`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T12:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (decision D14 rev 2 governs this phase)
- Prerequisite: Phases 2, 4 and 6 archived (clock-out rebuild live; explicit clock routes live; `analytics: null` envelope reserved).

## Goal and intent

- Goal: Populate the clock-out response's reserved `analytics` envelope with the worker's **day summary** — linear-timeline resume, drill-down segments, and insights for the clock-out date — by composing the existing worker-stats query machinery per-user. The kiosk renders a "your day" screen from the single clock-out response.
- Business/user intent: The moment a worker clocks out is the natural feedback moment: how long they worked, how their pauses split by reason, their day's timeline, and trend insights — without the device making three extra manager-endpoint calls.
- Non-goals: New metrics or new insight rules (compose what exists). Changing the three manager endpoints (`/worker-stats/linear-timeline`, `/insights`, `/{user_id}/linear-timeline`) — they stay as-is for the manager app. Analytics on the Connecteam / midnight-safeguard clock-out paths (HTTP-only feature). Realtime push.

## Scope

- In scope:
  1. Composite query service `services/queries/worker_stats/get_worker_clock_out_analytics.py`.
  2. A callable **seam** extracted from `get_worker_linear_timeline_breakdown` (explicit `(ctx, user_id, date_from, date_to)` args instead of route params) so the composite and the existing route share one implementation. The route's behavior stays byte-identical.
  3. Wiring: `/clock-out` route and the `/clock` toggle's clock-out branch compute `analytics` **after** the clock-out transaction completes, and attach it to the response. The core command `clock_out_shift_for_user` is untouched (safeguard + Connecteam never compute analytics).
  4. Handoff conformance: `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §5 documents the populated shape (already written, build-ahead) — implement to match; flip its status row.
- Out of scope: everything listed in non-goals; new endpoints.
- Assumptions:
  - **`analytics` shape** (per the handoff §5; all composed from existing serializers):
    ```json
    {
      "date": "2026-07-29",
      "timeline": { …serialize_linear_timeline: working/pause/idle/ended_shift seconds, completed_count, pause_by_reason… },
      "segments": [ …serialize_recorded_shift_segment, same as GET /worker-stats/{user_id}/linear-timeline… ],
      "segments_truncated": false,
      "pause_reasons": { "<par_id>": {"name": …, "image_url": …, "pause_type": …} },
      "insights": [ …serialize_insight… ]
    }
    ```
    `timeline`/`segments`/`segments_truncated`/`pause_reasons` come from the breakdown seam scoped to `(user_id, clock_out_date, clock_out_date)`; `insights` from `compute_worker_insights(ctx, [user_id], clock_out_date)` + `serialize_insight`. The breakdown's `user` key is dropped (the response already carries `user_id`).
  - **Ordering matters**: the timeline/segments read `UserShiftStateRecord` directly, so they are accurate **only after** the clock-out rebuild (Phase 2) is committed/flushed — the composite must run after the clock-out transaction, same request, same session.
  - **Work date** = the UTC date of `clock_out_at`. (Midnight-boundary shifts closed at 00:00 belong to the previous day's date — but those run through the safeguard, which never computes analytics; the HTTP path's `clock_out_at` is always "now".)
  - **Graceful degradation is a hard rule**: any exception inside the analytics composition → `analytics: null` + structured error log (`worker_shift.clock_out_analytics_failed`). A clock-out must NEVER fail or roll back because stats couldn't be computed — the shift is already closed by then.
  - **Insights staleness accepted**: `compute_worker_insights` reads `UserDailyWorkStats`, which the analytics worker updates asynchronously — at the clock-out instant, today's row may lag the just-closed steps by seconds. Accepted for "light stats" (insights lean on multi-day baselines); documented in the handoff. Timeline/segments have no such lag (they read the just-rebuilt records).
  - `/clock` toggle: clock-in branch keeps `analytics` absent from its semantics — only the clock-out branch carries the key (matching Phase 6's `null` placement).

## Clarifications required

- [x] Compute inline vs frontend calling the three manager endpoints? — resolved: inline composite in the clock-out response (one round-trip for the kiosk; the manager endpoints remain available and unchanged).
- [x] **Carried from the Phase 6 review (small, include in this phase — not analytics work):**
  - **R1-1:** `update_user_admin`'s `IntegrityError → 409` race path for duplicate `clock_in_code` has
    no committed test (the pre-check short-circuits every duplicate case), and the index-name string
    is now duplicated in three places — a future rename would silently degrade the race to a `500`.
    Add one assertion pinning the constant to the model's `Index` name (single source it if trivial),
    plus a test exercising the race path itself.
  - **Q1 operational cost (reviewer observation):** a code held by a **deactivated** worker stays
    reserved but is un-findable (no read-back surface, by operator ruling), so the `409` is opaque.
    Change the duplicate-code `409` message to state the code is already in use in this workspace and
    may belong to an inactive worker — actionable without leaking identity. Message only; no logic,
    no new endpoint.
- [x] Sync vs async (job + poll)? — resolved: sync composition — the scope is one worker × one day, bounded by the existing `_MAX_SEGMENTS` guard; measured latency recorded in the Review log. The `analytics: null` degradation path is the pressure valve; if latency ever becomes a problem, D14's envelope lets a future release move to async without a contract break.

## Acceptance criteria

1. Clock-out via `/clock-out` returns populated `analytics` with all six keys; `timeline.pause_by_reason` sums to `timeline.pause_seconds`; declared segments appear with `manually_recorded: true` and their catalog reason resolvable via `pause_reasons`.
1b. **Actor/target split**: on-behalf clock-out (manager token + worker `user_id`) returns analytics for the **worker** — proven by a test where the acting manager has their own shift activity that same day and none of it appears in the response. The composite receives the resolved target id as an explicit argument; `ctx.user_id` (the actor) is used for attribution only, never inside the analytics queries.
2. The `/clock` toggle clock-out branch returns the same `analytics`; its clock-in branch does not carry the key.
3. Equivalence: `analytics.segments`/`timeline` for the day equal the output of `GET /worker-stats/{user_id}/linear-timeline?date_from=<d>&date_to=<d>` called right after (contract test) — proving the seam is shared, not forked.
4. The existing breakdown route's responses are byte-identical to pre-phase behavior (its tests unmodified and green).
5. Analytics reflect the rebuilt shift: a shift whose live records were wrong mid-day (simulated worker lag) still produces correct post-rebuild `analytics` (test builds on Phase 2's rebuild tests).
6. Degradation: a forced exception in the composite (monkeypatched) → clock-out still succeeds (`200`, shift closed, `analytics: null`) + structured error log asserted.
7. Safeguard + Connecteam paths compute nothing: no analytics code reachable from `clock_out_shift_for_user` itself (code inspection recorded in Review log) and their suites unmodified/green.
8. Full suite green; `ruff check` clean; handoff §5 conformance evidenced in the Review log (liveness flip = operator, post-approval).

## Contracts and skills

### Contracts loaded

- `backend/architecture/07_queries.md` (+ local): composite query service structure.
- `backend/architecture/06_commands.md` (+ local): command/route boundary — analytics stays out of the write command.
- `backend/architecture/09_routers.md`: post-transaction composition in the route layer.
- `backend/architecture/46_serialization.md` (+ local): serializer reuse (no new shapes).
- `backend/architecture/20_api_versioning.md`: additive-only inside `analytics`.
- `backend/architecture/22_performance.md`: latency measurement expectation.
- `backend/architecture/15_testing.md`: contract-equivalence test placement.
- `backend/architecture/49_observability_runtime.md`: the degradation log line.

### Local extensions loaded

- `06_commands_local.md`, `07_queries_local.md`, `46_serialization_local.md`.

### File read intent — pattern vs. relational

Permitted relational reads:
- `services/queries/worker_stats/get_worker_linear_timeline_breakdown.py` — the service being seamed (full read required).
- `services/queries/worker_stats/list_workers_linear_timeline.py` — `build_recorded_shift_timeline` / `load_recorded_shift_records` / pause-reasons lookup helpers (already shared with the breakdown).
- `services/queries/analytics/compute_worker_insights.py` + `domain/analytics/serializers.py` — insight computation + serializer shapes.
- `services/commands/users/clock_out_worker_shift.py`, `toggle_worker_shift.py`, `routers/api_v1/worker_shifts.py` — the wiring points (incl. where the transaction boundary sits relative to the route).
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §5 — THE contract (mandatory read).

Prohibited pattern reads: other queries/routes for skeleton → `07`/`09`.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
- Router trigger terms: `worker`, `analytics`, `query`.
- Excluded alternatives: none.

## Implementation plan

1. Extract the breakdown seam (explicit-args function; route delegates to it) — byte-identical route behavior guarded by existing tests.
2. Composite service `get_worker_clock_out_analytics(ctx, user_id, work_date, now)` per the Assumptions shape.
3. Wire into `/clock-out` + `/clock` toggle clock-out branch, after the write transaction, with the try/except → `null` + log degradation.
4. Tests per acceptance 1–7 (equivalence test first — it pins the seam).
5. Measure and record composite latency for a realistic day (Review log).
6. Handoff conformance + status flip; run validation plan.

## Risks and mitigations

- Risk: analytics computation inside the write transaction (locks held during heavy reads / analytics failure rolls back the clock-out).
  Mitigation: hard rule — composition runs after the transaction; degradation path proven by acceptance 6.
- Risk: seam extraction silently changes the manager breakdown endpoint.
  Mitigation: acceptance 4 (existing tests unmodified); the seam is a mechanical parameter lift, not a rewrite.
- Risk: insights mislead right at clock-out (async day-stats lag).
  Mitigation: accepted + documented (handoff §5 note); insights are trend-oriented; timeline/segments — the visually dominant data — are exact.
- Risk: composite latency degrades kiosk UX at end-of-day rush.
  Mitigation: bounded scope (one user × one day, `_MAX_SEGMENTS`); latency measured and recorded; async escape hatch preserved by the envelope design (D14).

## Validation plan

- `pytest app/tests/integration/services/queries/worker_stats -q`: seam equivalence + unchanged breakdown route — green.
- `pytest app/tests/integration/services/commands/users/ -q` + router tests: populated envelope, toggle branch, degradation — green.
- `pytest app/tests -q`: full suite green (incl. untouched connecteam/safeguard suites).
- `ruff check`: clean.

## Review log

- (empty — filled by implementer and reviewer)

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
