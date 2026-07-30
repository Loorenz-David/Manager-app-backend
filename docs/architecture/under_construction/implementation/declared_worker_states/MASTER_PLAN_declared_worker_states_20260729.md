# MASTER_PLAN_declared_worker_states_20260729

## Metadata

- Plan ID: `MASTER_PLAN_declared_worker_states_20260729`
- Type: **master / orchestrator** (plays the intention-plan role for this feature set; phase plans link back here)
- Status: `under_construction`
- Owner: `David` (product) / `claude-fable-5` (planning) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T17:23:21Z`
- Related issue/ticket: `n/a` (originates from design session 2026-07-29: replace Connecteam clock interface + explainable worker states)
- Builds on: `archives/implementation/PLAN_worker_shift_state_recording_20260720.md` (the shift-state recording machinery this feature set extends)

## Goal

Centralize worker clock-in/clock-out inside the app (replacing Connecteam as the day-to-day interface) and let workers **declare what they are doing when not working a task step** — recorded pause/action states backed by the manager-editable `pause_reasons` catalog — so a worker's daily linear timeline has no unexplained idle time (idle becomes *truly unaccounted* time only).

## Why this matters

Today the worker's linear timeline (`UserShiftStateRecord`) is derived exclusively from task-step transitions. Anything a worker does off-task (cleaning, meetings, loading, breaks beyond the single manual pause) collapses into `idle`, and the worker cannot explain it. Managers see idle blocks with no story. Additionally, clock-in/out runs through Connecteam, splitting the operational surface across two products.

## Architecture (target state)

```
StepStateRecord             (source: what the worker did on task steps)
UserDeclaredStateRecord     (source: what the worker DECLARED they were doing)   ← NEW
UserShiftStateRecord        (derived: live provisional during the day; rebuilt at clock-out)
pause_reasons               (catalog: manager-editable reasons; PERSONAL = declarable)
```

`UserShiftStateRecord` remains fully derived. The clock-out reconstruction sweeps **both** source tables into one deterministic timeline. This removes today's awkward case where manual pauses (source data) live inside the derived table and must be fished out and re-emitted by the rebuild.

## Cross-phase decisions (binding for every phase)

| # | Decision |
|---|----------|
| D1 | Declared states live in a new source table `user_declared_state_records` (prefix `uds`), mirroring `StepStateRecord`'s pause shape. `UserShiftStateRecord` stays derived-only. |
| D2 | Reasons come from the existing `pause_reasons` catalog. Declarable = same workspace, `is_deleted = false`, `pause_type = PERSONAL`. `description` required iff `requires_description`. No new enum of activity types. |
| D3 | No new `UserShiftStateEnum` value. A declared state surfaces on the derived timeline as `IN_PAUSE` + `reason = pause_reason_id` + `manually_recorded = true`. `manually_recorded` is hereby redefined as "sourced from a worker declaration" (legacy meaning: manual pause — compatible). |
| D4 | Live-state precedence: open WORKING step > open declared state > open PAUSED step > IDLE. |
| D5 | Declaring auto-pauses all open WORKING steps **with the declared `pause_reason_id`** (step analytics and shift timeline tell the same story). Starting/resuming a step auto-closes the open declared state — implemented at the reconcile seam, not in step commands. Declaring while a declared state is open = switch (close + open, same transaction). |
| D6 | Clock-out closes any open declared record at `clock_out_at` (source-side clamp) and the reconstruction folds declared intervals into the sweep as `paused` intervals. Midnight safeguard inherits both for free (it delegates to clock-out). |
| D7 | `POST /pause` + `POST /resume` are retired (Phase 3) and replaced by declared-state routes. Legacy `manually_recorded` rows in `user_shift_state_records` are frozen — **no data migration**; the rebuild keeps folding legacy manual rows indefinitely (harmless, needed for shifts open across the deploy). |
| D8 | Connecteam handlers, webhook pipeline, and the midnight safeguard are **untouched** by this feature set. Connecteam decommission is a separate future decision, not a phase here. |
| D9 | Declaring requires an open shift (`409` otherwise). Declaration never auto-clocks-in. |
| D10 | *(revised 2026-07-29, rev 2)* Declare/close accept an optional `user_id` with the **exact same access matrix as clock actions** (`resolve_worker_shift_target`): a worker acts on themself only; admin/manager must name a worker. Required by the shop-floor device (D13). `created_by_id`/`closed_by_id` record the acting account (the device's manager identity when on-behalf). |
| D11 | New app scope `floor` (roles: ADMIN + MANAGER) for the always-on shop-floor app. Sign-in with `app_scope="floor"` issues a **non-expiring** access token (no `exp` claim; `jti` kept so the existing Redis blocklist can revoke a lost/retired device). Floor sessions get **no refresh cookie** (nothing to refresh). Blocklist entries for floor `jti`s are persisted **without TTL**. Existing scopes' token behavior is untouched. |
| D12 | Worker identification at the device = `clock_in_code` (new nullable, workspace-unique column on `user_work_profiles`) **or** working email. Identification is profile lookup only — it never issues tokens; the device's floor token authorizes the subsequent on-behalf action. |
| D13 | *(revised 2026-07-29, rev 3)* Kiosk flow = **local match → human confirm → fresh state → act**. No identify endpoint. The device polls the existing roster `GET /users?role=worker&compact=true` (TanStack cache); `clock_in_code` is included in that response **only when the session's `app_scope == "floor"`** (regular manager/worker sessions never receive codes). The frontend matches the typed code/email against the cached roster, shows the worker for confirmation, then fetches `GET /current?user_id=…` (fresh — the cache decides *who*, never *what state*) and calls the on-behalf action endpoints. |
| D14 | *(revised 2026-07-29, rev 4)* The clock-out response's `analytics` object is **populated in Phase 7** with the worker's day summary — `{date, timeline, segments, segments_truncated, pause_reasons, insights}` — composed from the existing worker-stats machinery (breakdown seam + `compute_worker_insights`), computed **after** the clock-out transaction on the HTTP path only. `null` remains a valid value (graceful degradation: analytics failure never fails a clock-out; safeguard/Connecteam paths never compute it). Future additions inside `analytics` are additive. |

## Phase orchestration

Phases are strictly sequential. **Phase 2 (read/derivation) intentionally lands before Phase 3 (write path)** so there is never a deploy window where declared records exist but the clock-out rebuild discards them.

| Phase | Plan | Delivers | Status |
|-------|------|----------|--------|
| 1 | `../../../archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase1_model_20260729.md` | `UserDeclaredStateRecord` model + migration (inert — nothing reads/writes it yet) | `archived` ✅ (commit `a84610c`, reviewed APPROVED) |
| 2 | `../../../archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md` | State machine + live reconcile + clock-out reconstruction read the new table (still inert — table is empty) | `archived` ✅ (final commit `d952655`, APPROVED by Opus after 5 review rounds / 4 fix cycles; incl. authorized D7-deviation repair migration `c2f4a6b8d0e1`) |
| 3 | `PLAN_declared_worker_states_phase3_commands_20260729.md` | Declare/close commands + routes, auto-pause of working steps, retirement of `/pause` + `/resume` | `needs_changes` (round 2) — K1–K4 fixed & mutation-verified at `820e175`; remaining: L1 (minor: reconcile's inline locked select bypasses the K1-hardened helper — analytics-worker path unpatched), L2 (operator-fixed: stale archived claim in progress notes). Fix cycle 2 via `codex_prompts/PROMPT_phase3_fixes_round2.md`. |
| 4 | `PLAN_declared_worker_states_phase4_clock_surface_20260729.md` | Explicit `/clock-in` + `/clock-out` routes, `GET /current` state endpoint, reasons filter, handoff validation | `under_construction` |
| 5 | `PLAN_declared_worker_states_phase5_device_auth_20260729.md` | `floor` app scope + non-expiring device token + permanent revocation semantics | `under_construction` |
| 6 | `PLAN_declared_worker_states_phase6_kiosk_flow_20260729.md` | `clock_in_code` on work profiles, floor-scoped code exposure in `GET /users`, clock-out `analytics: null` envelope | `under_construction` |
| 7 | `PLAN_declared_worker_states_phase7_clockout_analytics_20260729.md` | Populated clock-out `analytics` (day timeline + segments + insights via existing worker-stats machinery), final handoff validation | `under_construction` |

Dependency note: Phase 5 touches only auth and has **no dependency on Phases 1–4** — it may be implemented at any point (including first, to unblock frontend auth integration). Phase 6 requires Phases 3, 4 **and** 5. Phase 7 requires Phases 2, 4 and 6 and closes the feature set. The frontend builds in parallel against `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`, which was written **ahead of implementation** and is the authoritative API contract for all phases — implementations must conform to it; any deviation must be resolved in the handoff first (operator decision), never silently.

### Per-phase workflow (operator: David)

1. Pass `codex_prompts/PROMPT_phase<N>_*.md` to Codex. Codex processes the phase plan under the `plan_lifecycle_orchestrator` skill.
2. When Codex reports completion, pass `review_prompts/REVIEW_phase<N>_*.md` to the review agent.
3. If the review finds defects → back to Codex with the review findings (recorded in the phase plan's Review log).
4. When the review approves: Codex (or the operator) writes the implemented summary, archives the phase plan, and updates this master table's Status column.
5. Only then start phase N+1.

### Repository validation baseline (recorded 2026-07-29, during Phase 1)

The repository has pre-existing validation debt, verified against the pre-Phase-1 git state
(evidence in the Phase 1 plan's Review log):

- **22 stable failing tests** (bootstrap, items, task_steps, tasks, upholstery, working_sections,
  audit, shopify, auth, worker_stats, routers) + at least one **non-idempotent flaky test**
  (`test_create_uses_client_supplied_id_for_new_preference` — hardcoded client_id, fails on any
  re-run against a dirty test DB).
- **149 `ruff check .` errors** in untouched files.
- **Fresh empty-DB `alembic upgrade head` stalls** in the historical revision graph's topological
  sort (existing DBs at head upgrade fine).
- `client_id_prefix_map.md` records `ussr` for `UserShiftStateRecord` whose real prefix is `uss`
  (pre-existing typo, found by the Phase 1 reviewer).
- Note (Phase 1 reviewer): two of the baseline failures are in
  `test_worker_shift_commands` (clock-out) — **this feature's own domain**. Phase 2/3
  implementers and reviewers must treat exactly those two as baseline, and must not let any NEW
  worker-shift failure hide behind them.

**Binding rule for every phase and every reviewer:** wherever a phase plan or review prompt says
"full suite green" / "ruff clean", read it as **"no NEW failures or errors relative to this
baseline, and all in-scope/new tests green; touched files ruff-clean."** Implementers must not
absorb baseline repairs into a phase (scope discipline); reviewers must not block on baseline
items. Repairing the baseline is separate repo-health work outside this feature set.

### Lifecycle / archiving note (overrides the skill's flat-path `mv`)

Phase plans live in this subfolder for compactness. On archive, **preserve the subfolder**: move to
`backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_....md`.
When all four phases are archived, set this master plan's status to `archived` and move the entire folder (including prompts) to `archives/implementation/declared_worker_states/`.

## Success criteria (feature set as a whole)

1. A worker can clock in, declare "Cleaning" (or any PERSONAL reason), have their working steps auto-paused under that reason, return to a task (declaration auto-closes), and clock out — and the closed shift's timeline shows working / declared / idle segments with **zero unexplained collapse** of declared time into idle.
2. The derived timeline (`UserShiftStateRecord`) after clock-out is deterministic: rebuild output is identical whether or not the analytics worker was up during the shift.
3. The frontend can drive the whole day from the app alone: clock state readable via `GET /current`, reasons pickable from the catalog, no Connecteam interaction required (Connecteam keeps working in parallel per D8).
4. All existing worker-stats endpoint contracts remain backward-compatible (additive-only changes).
5. The shop-floor app signs in once with `app_scope="floor"` (admin/manager account), holds a non-expiring token, and workers clock in/out and declare states at the device via clock-code/email identification + confirmation — with the token permanently revocable via logout if the device is lost.
6. The implemented API matches `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` exactly (the frontend was built against it in parallel).

## Progress notes

- `2026-07-29`: Master plan + 4 phase plans + codex/review prompts created. No implementation started.
- `2026-07-29` (rev 2): Shop-floor device requirements added — D10 revised (on-behalf declare/close), D11–D14 added, Phases 5–6 created, Phase 3 amended to the on-behalf matrix, Phase 4's handoff deliverable re-pointed at the pre-written floor-app handoff. Frontend build starts in parallel against the handoff.
- `2026-07-29` (rev 3): Identify endpoint dropped in favor of client-side matching against the polled roster (`GET /users?role=worker&compact=true`), with `clock_in_code` exposed in that response only to floor-scope sessions (D13 rev 3). Phase 6 + handoff §3 updated. Accepted trade-off: the whole roster + codes lives in the kiosk device's memory — same trust boundary as the device's manager token (codes are identification, not authentication, per D12).
- `2026-07-29`: **Phase 1 completed and archived** (commit `a84610c`). Implemented by Codex, reviewed APPROVED by Opus (independent re-run of all gates + detached-worktree baseline diff proving inertness). Validation waiver recorded for the pre-existing repo baseline; baseline rule added for remaining phases. Summary: `implemented_summaries/SUMMARY_declared_worker_states_phase1_model_20260729.md`.
- `2026-07-29` (rev 4): Phase 7 added — the clock-out `analytics` envelope is populated with the worker's day summary (timeline resume + drill-down segments + insights) composed from the existing worker-stats services via a shared seam (D14 rev 4). Final-phase lifecycle duties move from Phase 6 to Phase 7.
- `2026-07-29`: **Phase 2 completed and archived** (final commit `d952655`) after 5 independent
  review rounds / 4 fix cycles — findings F1–F5, G1–G3, H1/H2/T1, I1/I2 all resolved and
  reviewer-verified; APPROVED with only informational J1 (addressed via migration docstring) and
  J2 (carried). Includes the operator-authorized D7 deviation: provenance-repair migration
  `c2f4a6b8d0e1`. Summary:
  `implemented_summaries/SUMMARY_declared_worker_states_phase2_derivation_20260729.md`. Every
  post-round-1 finding sat at the legacy/declared seam — Phase 3 deletes that seam; its review
  must scrutinize removal completeness.
- `2026-07-29/30`: Phase 3 implemented (declare/close commands + handoff-conformant routes,
  catalog validation, on-behalf access, `_apply_step_transition` auto-pause, synchronous
  same-session reconcile, F4/F6 obligations, total pause/resume retirement) and in **review fix
  cycles** — K1–K4 fixed and mutation-test-verified at `820e175`; round 2 open (L1: delegate the
  reconcile's inline locked select to the K1-hardened helper). The phase table row is
  authoritative; the implementer's earlier "completed and archived" note was premature and is
  superseded by this entry (review finding L2).

## Open questions

- None blocking. Veto-able defaults flagged inside phase plans: route naming (Phase 3/4), `pause_type = PERSONAL` as the declarable filter (D2, Phase 3).

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved` (operator reads and approves phase plans) → per-phase implementation
- Transition owner: `David`
