# MASTER_PLAN_declared_worker_states_20260729

## Metadata

- Plan ID: `MASTER_PLAN_declared_worker_states_20260729`
- Type: **master / orchestrator** (plays the intention-plan role for this feature set; phase plans link back here)
- Status: `archived`
- Owner: `David` (product) / `claude-fable-5` (planning) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
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
| D14 | *(revised 2026-07-30, rev 5)* The clock-out response's `analytics` object is **populated in Phase 7** with a **purpose-built kiosk payload** — `{date, timeline, pause_reasons, completed_items, completed_items_truncated, week, rate}` — composed **after** the clock-out transaction, HTTP path only. It deliberately does **not** carry `segments[]`/`segments_truncated` (per-step drill-down stays in the manager endpoints — the kiosk renders totals only) nor the time-based `insights` array (it cannot express the design's unit-based comparisons; `rate` replaces it). Day totals reuse the shared `build_recorded_shift_timeline` helper so kiosk and manager numbers cannot drift, at ~1 query instead of the breakdown's ~5. `null` remains a valid value (graceful degradation: analytics failure never fails a clock-out; safeguard/Connecteam paths never compute it). Future additions inside `analytics` are additive. |

## Phase orchestration

Phases are strictly sequential. **Phase 2 (read/derivation) intentionally lands before Phase 3 (write path)** so there is never a deploy window where declared records exist but the clock-out rebuild discards them.

| Phase | Plan | Delivers | Status |
|-------|------|----------|--------|
| 1 | `../../../archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase1_model_20260729.md` | `UserDeclaredStateRecord` model + migration (inert — nothing reads/writes it yet) | `archived` ✅ (commit `a84610c`, reviewed APPROVED) |
| 2 | `../../../archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md` | State machine + live reconcile + clock-out reconstruction read the new table (still inert — table is empty) | `archived` ✅ (final commit `d952655`, APPROVED by Opus after 5 review rounds / 4 fix cycles; incl. authorized D7-deviation repair migration `c2f4a6b8d0e1`) |
| 3 | `../../../archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase3_commands_20260729.md` | Declare/close commands + routes, auto-pause of working steps, retirement of `/pause` + `/resume` | `archived` ✅ (production final at `a39ae40`, APPROVED at round-4 confirmation `8b0fd78`; K1/L1 concurrency fixes mutation-verified) |
| 4 | `../../../archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase4_clock_surface_20260729.md` | Explicit `/clock-in` + `/clock-out` routes, `GET /current` state endpoint, reasons filter, handoff validation | `archived` ✅ (APPROVED at `ccdffa9`, polish `be47f4d`; R4–R6/R8–R10 closed; helper relocated to `services/queries/users/` per `01_architecture.md:43`; quiet-tree suite 27 failed / 1280 passed = baseline) |
| 5 | `../../../archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase5_device_auth_20260729.md` | `floor` app scope + non-expiring device token + permanent revocation semantics | `archived` ✅ (APPROVED at round 3, `12bbeb7`; N1 CRITICAL revocation bypass closed with 4 defense layers + 19 mock-free probes; test-integrity round closed with reviewer-rerun mutation checks) |
| 6 | `../../../archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase6_kiosk_flow_20260729.md` | `clock_in_code` on work profiles, floor-scoped code exposure in `GET /users` | `archived` ✅ (APPROVED on the **first** round at `b0f35b1`; 37-assertion real-ASGI probe of the floor gate, 4 mutation checks, `pg_enum` label parity on the in-phase `?role=` 500 repair) |
| 7 | `../../../archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase7_clockout_analytics_20260729.md` | **(rev 2, final)** Clock-out `analytics`: day `timeline` + `pause_reasons` + `completed_items` + `week` + `rate`; floor roster sections; roster page cap; two carried Phase 6 items | `archived` ✅ (NEEDS_CHANGES round 1 on F1/F2/F3, APPROVED on re-review with all three reproduced as fixed under reviewer mutation; baseline-worktree failure-node diff empty at `f26ecc6`; F13 cross-endpoint fix and F14 disclosed + tested in a pre-archive fast-follow; F15 midnight-spanning fixture deferred by ruling) |

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
- The shared `count_queries` test fixture is broken and unused (found in Phase 6; a local SQLAlchemy
  listener was used instead for the batching assertion).
- **`pause_reasons.slug` is globally unique, not workspace-scoped** — `CREATE UNIQUE INDEX
  uq_pause_reasons_slug ON pause_reasons (slug)`. Measured on the dev/test DB 2026-07-30: **3132
  workspaces, exactly 1 holding `pause_ended_shift`**, because seeding any second workspace violates
  the index. **Operational impact (not just test noise):** `clock_out_shift_for_user` calls
  `get_system_pause_reason_id(..., "pause_ended_shift")` whenever the worker has open WORKING steps,
  so in any workspace lacking that row a clock-out with active work **fails with 404** — the most
  common clock-out case. This is the root cause of the recurring
  "System pause reason 'pause_ended_shift' is not configured" baseline failure. Pre-existing and
  out of scope for this feature set, but it must be verified in the target database before the kiosk
  goes live. **Superseded as a repo-health item (2026-07-30) by
  `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`**,
  which rules that scoping the index to `(workspace_id, slug)` is a *supporting* change, not the fix:
  the real defect is that a mandatory state transition resolves through a workspace-editable catalog
  row at all. That intention plans the migration to explicit `transition_reason` semantics and names
  **D3, D5 and D14** as the decisions it would amend. Sequencing: **Phase 7 lands first** — its
  `pause_by_reason` contract is already published, and it then serves as a compatibility test for the
  migration's read layer. The pre-go-live database verification above stands regardless, since the
  migration lands later than the kiosk.
- `GET /users?role=` was a guaranteed 500 (disjoint-enum comparison) until Phase 6 repaired it — noted
  because it means any pre-Phase-6 "role filter" evidence in older logs is void.
- Note (Phase 1 reviewer): two of the baseline failures are in
  `test_worker_shift_commands` (clock-out) — **this feature's own domain**. Phase 2/3
  implementers and reviewers must treat exactly those two as baseline, and must not let any NEW
  worker-shift failure hide behind them.

**Canonical measurement (operator, 2026-07-30 at commit `ccdffa9`, quiet tree — no concurrent
sessions): `27 failed / 1275 passed`.** Counts drift between runs (22–28) because the test DB and
Redis are SHARED: a suite run while another session executes probes will report wildly inflated
failures (one Codex run reported 313 failed / 11 errors; re-run on a quiet tree: 27). **Never
accept or report a full-suite number taken while another session is active** — re-run it quiet
before drawing conclusions. Compare failure NODE SETS, not counts.

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
- `2026-07-30`: **Phase 3 completed and archived** (production final `a39ae40`, APPROVED at
  round-4 confirmation `8b0fd78`) after 2 fix cycles + 1 operator doc fix. The legacy/declared
  seam is fully deleted (`/pause`, `/resume`, carve-out, provenance rule). K1/L1 EvalPlanQual
  concurrency fixes mutation-verified load-bearing. Declared-states endpoints are LIVE — handoff
  §6 row flipped. Deploy note in the summary: mid-manual-pause workers reconcile to `IDLE` once
  at deploy (cosmetic; rebuild correct per D7). Summary:
  `implemented_summaries/SUMMARY_declared_worker_states_phase3_commands_20260729.md`.

- `2026-07-30`: **Phase 4 completed and archived** (implementation `20b11c7`, fixes `ccdffa9`,
  polish `be47f4d`). In-app clock surface complete: `/clock-in`, `/clock-out`, `GET /current`,
  `analytics: null` envelope, legacy `/clock` retained. R5 turned out to close a real cross-tenant
  identifier leak; R10 makes that condition operator-visible. Reviewer corrected an operator
  suggestion: shared access helpers belong in `services/queries/users/`, never `services/infra/`
  (`01_architecture.md:43`). Summary:
  `implemented_summaries/SUMMARY_declared_worker_states_phase4_clock_surface_20260729.md`.
- `2026-07-30`: **Phase 5 completed and archived** (implementation `549f480`, security fixes
  `b8946fe`, test-integrity fixes `12bbeb7`) after 3 review rounds / 2 fix cycles. The review caught
  the feature set's most serious defect — an **executed revocation bypass** (blocklisted floor token
  replayed as the refresh cookie minted fresh tokens forever, nullifying D11) — closed with four
  independent defense layers and 19 mock-free probes; then blocked on evidence quality (a revocation
  test that passed for the wrong reason) until discriminating assertions + reviewer-rerun mutation
  checks landed. Residual accepted risks and R3-1 (test-naming rename) recorded in the summary:
  `implemented_summaries/SUMMARY_declared_worker_states_phase5_device_auth_20260729.md`.
- `2026-07-30`: **Phase 6 unblocked** — Phases 3, 4 and 5 are archived.
- `2026-07-30`: **Phase 6 completed and archived** (`b0f35b1`) — APPROVED on the first review round,
  the only phase to do so. The kiosk is functionally complete end to end (floor sign-in → roster with
  codes → confirm → `GET /current` → clock-in / declare / clock-out). Includes an operator-accepted
  in-phase repair of a pre-existing `GET /users?role=` 500 (disjoint Postgres enums compared against
  every value), verified complete by `pg_enum` label parity. Carried to Phase 7: R1-1 (pin the
  index-name constant + cover the `IntegrityError → 409` race) and the duplicate-code `409` message.
  Summary: `implemented_summaries/SUMMARY_declared_worker_states_phase6_kiosk_flow_20260729.md`.
- `2026-07-30`: **Phase 7 unblocked** — Phases 2, 4 and 6 are archived.
- `2026-07-30` (rev 2 of Phase 7): **Phase 8 merged into Phase 7 and the analytics design simplified.**
  After the frontend requirements doc, two operator rulings: the kiosk renders **totals only** (no
  `segments[]` drill-down) and its comparison rows are **unit-based**, which the time-based `insights`
  engine cannot express. So Phase 7 no longer extracts a seam from the manager breakdown (~5 queries +
  per-segment step assembly at the busiest moment); it composes from the cheap shared helpers instead,
  keeping the anti-drift property (same `build_recorded_shift_timeline` as the manager roster) at ~1
  query, and absorbs the former Phase 8 keys. Dropped: `segments`, `segments_truncated`, `insights`.
  Added: `completed_items`, `week`, `rate`. Phase 8's plan/prompts removed as superseded.
- `2026-07-31`: **Phase 7 completed and archived — the final phase; all seven are now archived.**
  NEEDS_CHANGES on round 1 (`claude-opus-5`) blocking on three defects worth remembering: a raised
  roster limit placed in the query service where FastAPI's `Query(...)` validator never reaches it (so
  the cap never actually moved), a regression test that signalled failure by raising inside code wrapped
  in `except Exception` and therefore could not fail, and two committed tests left red by a new internal
  key in a command's return dict. APPROVED on re-review (`claude-sonnet-5`), which reproduced all three
  fixes under its own mutation probes and diffed sorted failure-node sets against a `git worktree` at
  `f26ecc6` — diff empty. A pre-archive fast-follow disclosed and tested **F13**: a round-1 fix rewrote
  `_load_step_and_primary_item`'s keying from `{item_id: task_id}` to `{task_id: item_id}`, which also
  changed the **manager-facing linear-timeline breakdown endpoint** — a surface the plan scoped
  read-only — where the old keying rendered `"item": null` for an item PRIMARY on two tasks. The fix is
  correct and kept; it now has a mutation-verified test on that endpoint. **F15 deferred by ruling and
  carried as a known gap: no fixture exercises a shift literally spanning UTC midnight**, so acceptance
  criterion 5's midnight case is covered only transitively through `build_recorded_shift_timeline`'s own
  suite. Summary:
  `implemented_summaries/SUMMARY_declared_worker_states_phase7_clockout_analytics_20260729.md`.
- `2026-07-30`: **Phase 8 originally added** from `docs/handoff/from_frontend/BACKEND_REQUIREMENTS_clock_kiosk_20260729.md`
  (the frontend built its kiosk UI ahead of the contract, behind null-defaulting adapters). Audit of
  the seven requests: `week` bars, station/line, and roster scale were already reachable from existing
  tables; `completed_items` needed only composition (no product entity exists — items are labelled by
  `article_number` → `sku` per operator ruling); **scheduled shifts and floor announcements do not
  exist as concepts** and are excluded — scheduling explicitly skipped by the operator, announcements
  deferred to a separate feature set; badge numbers deferred (no data). Handoff §5.2 (new keys) and
  §5.3 (nullability conventions, requested by the frontend) added.
- `2026-07-30`: **`INTENTION_system_transition_reasons_20260730` filed** (`under_construction/intention/`),
  superseding the "scope the index to `(workspace_id, slug)`" line in the validation baseline above.
  Tracing from `pause_reason.py` found the runtime slug dependency is **two slugs across three call
  sites** — `pause_ended_shift` in `_clock_worker_shift.py:200`, and `pause_other_task_priority` in
  both `transition_step_state.py:274` and `_step_transition_core.py:114` — so in the 3131 workspaces
  lacking the rows, **task switching fails too**, not only clock-out. Also found: the bootstrap phase
  guards existence by `(workspace_id, slug)` while the index is global, so **creating a second
  workspace should raise `IntegrityError`** (flagged verify-first; traced, not executed). The
  intention names **D3, D5, D14** as the decisions the migration would amend, and asks whether
  `transition_reason` subsumes `manually_recorded` — the provenance concept that cost Phase 2 four
  fix cycles (F1/F2, G1, H1, I1) and settled on a `changed_by_id IS NOT NULL` heuristic. No code
  changed; planning deferred to a separate session, after Phase 7.
- `2026-07-31`: **Phase 7 operator rulings** (mid-implementation, recorded here because they deviate
  from the phase plan text): (1) `completed_items[].total_seconds` = `TaskStep.total_working_seconds`
  **only** — `working + pause + ended_shift` was rejected as booking blocked/overnight time as work;
  (2) floor roster ceiling raised to 1000 (`_FLOOR_MAX_LIMIT`, floor scope only), pagination-walk
  rejected because the kiosk matches a typed code against the full roster; (3) the `_clock_out_at`
  private route channel sanctioned — `clock_out_shift_for_user` stays untouched, so Connecteam and
  the midnight safeguard cannot reach analytics. Operator-found defect fixed: the route's
  `pop("_clock_out_at", datetime.now(...))` default made the timestamp dependency silently optional
  (deleting the producer left the suite green — the only test asserted absence from the *response*,
  which the fallback also satisfies), fabricating a wrong-day `date`/`week` on a midnight-boundary
  clock-out with HTTP 200 and no log. Handoff §5.1's `total_seconds` wording is now narrower than it
  reads and is an **operator to-do after approval** — deliberately not edited mid-implementation.
  A review-prompt addendum carrying these rulings accompanies `REVIEW_phase7_clockout_analytics.md`.

## Open questions

- None blocking. Veto-able defaults flagged inside phase plans: route naming (Phase 3/4), `pause_type = PERSONAL` as the declarable filter (D2, Phase 3).

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved` (operator reads and approves phase plans) → per-phase implementation
- Transition owner: `David`
