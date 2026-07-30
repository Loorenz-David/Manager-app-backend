# PLAN_declared_worker_states_phase4_clock_surface_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase4_clock_surface_20260729`
- Status: `under_construction`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T12:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (decisions D8, D10 govern this phase)
- Prerequisite: Phase 3 archived (declare/close live; `/pause`/`/resume` gone).

## Goal and intent

- Goal: Complete the in-app clock surface so the frontend can drive the whole day without Connecteam: explicit `POST /clock-in` + `POST /clock-out` routes (wiring the two already-written, currently orphaned commands), a `GET /current` state endpoint, a `pause_type` filter on the reasons listing (if missing), and the frontend handoff document.
- Business/user intent: The worker's app becomes the single clock interface. Connecteam keeps functioning in parallel (D8) until the operator decides to decommission it — out of scope here.
- Non-goals: Removing `POST /clock` (kept — existing frontend uses it). Touching Connecteam handlers or the midnight safeguard (D8). Realtime/socket push of shift state (future). Timeline/stats endpoint changes (none needed).

## Scope

- In scope:
  1. Routes `POST /clock-in` and `POST /clock-out` on `routers/api_v1/worker_shifts.py`, wiring the existing unwired commands `services/commands/users/clock_in_worker_shift.py` and `clock_out_worker_shift.py`. Same role matrix as `/clock` (`require_roles([ADMIN, MANAGER, WORKER])` + `resolve_worker_shift_target` semantics). `clock_out` route body accepts optional `user_id` only — **do not expose `clock_out_at`** over HTTP (it exists for the midnight safeguard; exposing backdated clock-out to clients is an audit hole).
  1b. *(moved here from Phase 6, operator ruling 2026-07-30)* The clock-out response — on BOTH `POST /clock-out` and the `/clock` toggle's clock-out branch — carries the reserved `"analytics": null` key (D14 envelope; Phase 7 populates it). Clock-in responses never carry the key. All pre-existing response keys unchanged (additive-only).
  2. Query service `services/queries/users/get_current_worker_shift_state.py` + route `GET /current` (query param `user_id` optional; same access rule as clock: workers omit it → self; admin/manager must pass it).
  3. Reasons listing: verify `services/queries/pause_reasons/list_pause_reasons.py` + its route support filtering by `pause_type`; if not, add an optional `pause_type` query param (additive) so the declare picker can fetch PERSONAL reasons only.
  4. Handoff validation: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` was written **ahead of implementation** (the frontend builds against it in parallel). This phase's deliverable is conformance: implement `GET /current` and the clock routes to match it field-for-field, Conformance evidence goes in the Review log; **(operator-owned, ruling 2026-07-30)** the handoff liveness row is flipped by the OPERATOR after the reviewer approves — an implementer must never flip it. This phase's deliverable is conformance evidence in the Review log, not the doc edit. Any needed deviation → operator decision + handoff update first.
- Out of scope: Connecteam decommission; manager dashboards; new stats.
- Assumptions:
  - **`GET /current` response** (serializer per `46`; all timestamps UTC ISO):
    ```json
    {
      "user_id": "usr_...",
      "clocked_in": true,
      "shift_started_at": "2026-07-29T06:58:00Z",
      "state": "in_pause",
      "state_entered_at": "2026-07-29T09:12:00Z",
      "pause_reason": {"id": "par_...", "name": "Lunch break", "image_url": "..."} ,
      "declared_state": {
        "id": "uds_...",
        "pause_reason": {"id": "par_...", "name": "Lunch break", "image_url": "..."},
        "description": null,
        "entered_at": "2026-07-29T09:12:00Z"
      }
    }
    ```
    - `clocked_in` = open `UserShiftStateRecord` exists; `state`/`state_entered_at` from that row; `shift_started_at` = latest `STARTED_SHIFT` marker `<= now`.
    - `pause_reason` resolved by joining `state.reason` against `pause_reasons.client_id` when it matches; a legacy free-text reason (frozen manual rows) serializes as `pause_reason: null` plus `reason_text: <raw>` — additive, no error.
    - `declared_state` = the open `UserDeclaredStateRecord` if any, else `null`. Not clocked in → `clocked_in: false`, all state fields `null`.
    - Read-only: no locks (`with_for_update` is for writers only).
  - **Access for `GET /current`**: reuse the `resolve_worker_shift_target` role rules but through a read-only variant — extract the role-check + membership query into a shared helper if reuse would otherwise lock or duplicate; keep the existing writer path behavior byte-identical.
  - `/clock` toggle stays; the handoff marks it "legacy, prefer explicit routes".
- Assumption (verify first): `list_pause_reasons` may already accept a type filter — the router imports `PauseTypeEnum`. If so, item 3 is documentation-only.

## Clarifications required

- [x] Expose `clock_out_at` for corrections? — resolved: no (audit hole); manual time corrections are a future manager-tooling feature.
- [x] Separate `GET /current` per role vs one route? — resolved: one route, `user_id` optional, same matrix as clock actions.

## Acceptance criteria

1. `POST /clock-in`: worker self-clock-in works; double clock-in → `409`; manager with `user_id` works; manager without `user_id` → `403` (existing `resolve_worker_shift_target` semantics). `POST /clock-out`: symmetric; clock-out runs the full existing pipeline (reconstruction, step closure, `ENDED_SHIFT`) — asserted via the returned `transitioned_steps` and record state.
2. `POST /clock` keeps all existing behavior (regression) — with exactly one additive change: its clock-out branch (and `/clock-out`) now returns `"analytics": null`; clock-in responses carry no such key (tests pin both).
2b. Pause-reasons listing: the handoff §7 shape was corrected (2026-07-30) to the endpoint's real paginated envelope — no backend change; conformance check only.
3. `GET /current` matrix: worker self (clocked out / idle / working / step-paused / declared) each returns the documented shape; manager with `user_id` reads another worker; worker passing `user_id` of someone else → `403`; legacy free-text pause row serializes per spec without error.
4. Reasons listing filterable by `pause_type=personal` (pre-existing or added); response contract otherwise unchanged.
5. Implemented `GET /current` + clock routes match `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` field-for-field (conformance asserted by contract tests keyed to the handoff's documented shapes). **(operator-owned, ruling 2026-07-30)** the handoff liveness row is flipped by the OPERATOR after the reviewer approves — an implementer must never flip it. This phase's deliverable is conformance evidence in the Review log, not the doc edit.
6. Full suite green; `ruff check` clean.

## Contracts and skills

### Contracts loaded

- `backend/architecture/07_queries.md` + `07_queries_local.md`: query-service structure for `get_current_worker_shift_state`.
- `backend/architecture/09_routers.md`: route wiring.
- `backend/architecture/46_serialization.md` (+ local): response serializer.
- `backend/architecture/28_roles_permissions.md`: role matrix reuse.
- `backend/architecture/05_errors.md`: `403`/`404`/`409` mapping.
- `backend/architecture/20_api_versioning.md`: additive-change rules for the reasons listing.
- `backend/architecture/23_documentation.md`: handoff doc conventions (existing handoffs as relational reference for structure).
- `backend/architecture/15_testing.md`: router/query test placement.

### Local extensions loaded

- `07_queries_local.md`: pagination/read conventions (listing filter).
- `46_serialization_local.md`: output-shape deltas.

### File read intent — pattern vs. relational

Permitted relational reads:
- `services/commands/users/clock_in_worker_shift.py`, `clock_out_worker_shift.py` — exact request/response of the commands being wired (and confirming `clock_out_at` stays internal).
- `services/commands/users/_worker_shift_access.py` — role/membership logic to share with the read path.
- `services/queries/pause_reasons/list_pause_reasons.py` + `routers/api_v1/pause_reasons.py` — current filter capability (the verify-first item).
- `routers/api_v1/worker_shifts.py` — router being extended.
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` — THE contract this phase implements against (mandatory read).
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_linear_timeline_20260719.md` — prior handoff shape (relational: what the frontend already consumes).
- Models touched by the read (`user_shift_state_record.py`, `user_declared_state_record.py`, `pause_reason.py`).

Prohibited pattern reads: other query services for skeleton → `07`; other routers for wiring → `09`; other serializers for shape → `46`.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
- Router trigger terms: `router`, `query`, `handoff`.
- Excluded alternatives: none.

## Implementation plan

1. Wire `POST /clock-in` + `POST /clock-out` (thin routes over existing commands; `clock_out_at` never parsed from HTTP).
2. Extract/reuse the access check for reads; build `get_current_worker_shift_state` query service + serializer per the Assumptions shape.
3. Route `GET /current`; wire in router.
4. Verify reasons-listing filter; add `pause_type` param if absent (additive).
5. Tests: acceptance 1–4 (router tests + query integration tests incl. the 5-state `GET /current` matrix and legacy free-text case).
6. Conformance pass against the floor-app handoff; record evidence in the Review log (the liveness flip is the operator's post-approval step).
7. Run validation plan.

## Risks and mitigations

- Risk: read path accidentally reuses `resolve_worker_shift_target` verbatim and inherits writer-oriented behavior (worker-role-only target constraint is correct, but keep it read-only — no locks).
  Mitigation: explicit extraction step 2; writer path byte-identical (existing tests guard it).
- Risk: legacy free-text `reason` rows crash the reason join.
  Mitigation: LEFT-join semantics + `reason_text` fallback; dedicated test (acceptance 3).
- Risk: frontend builds against the handoff while Connecteam still writes shifts → surprising states (e.g., clocked in via Connecteam, app shows it — correct and intended).
  Mitigation: handoff explicitly documents that both interfaces write the same shift machinery (D8) and `GET /current` reflects either.

## Validation plan

- `pytest app/tests/unit/test_worker_shifts_router.py -q`: all routes incl. new ones — green.
- `pytest app/tests/integration/services/queries/ -q`: current-state matrix + reasons filter — green.
- `pytest app/tests -q`: full suite green.
- `ruff check`: clean.

## Review log

- `2026-07-30T08:06:02Z` — Codex implementation complete; independent review pending.

  **Implementation**
  - Added thin `POST /clock-in` and `POST /clock-out` routes over the existing
    `clock_in_worker_shift` / `clock_out_worker_shift` commands. The HTTP body contains only
    optional `user_id`; a router contract test proves an attempted `clock_out_at` field is not
    forwarded to the command.
  - Added the reserved `"analytics": null` envelope to explicit clock-out and only to the
    `/clock` toggle's clock-out branch. Clock-in responses carry no `analytics` key; all
    pre-existing keys are unchanged.
  - Extracted the byte-identical worker target role/membership resolver to the shared
    `services/worker_shift_access.py`; the old command-local module remains as a compatibility
    re-export, so all existing writer imports and behavior are preserved.
  - Added read-only `get_current_worker_shift_state` plus `GET /current`. Its single state read
    uses workspace-scoped LEFT joins for current/declaration pause reasons and contains no
    `with_for_update`. Serialization matches handoff §4, including `+00:00` ISO timestamps,
    clocked-out null fields, step-pause vs declared-state shapes, and the legacy free-text
    `reason_text` fallback.
  - Verified the pause-reasons query and route already support `pause_type=personal` and already
    return the corrected paginated handoff §7 envelope. No pause-reasons code or contract changed.

  **Acceptance / handoff conformance evidence**
  - `pytest tests/unit/test_worker_shifts_router.py -q` → `27 passed`. Pins role registration,
    existing-command wiring, 403/409 propagation, exact current-state envelope forwarding,
    `clock_out_at` exclusion, and `analytics` presence/absence on both explicit and toggle routes.
  - `pytest tests/integration/services/queries/users/test_get_current_worker_shift_state.py
    tests/integration/services/queries/pause_reasons/test_pause_reasons_queries.py -q` →
    `8 passed`. Covers clocked out, idle, working, step-paused, declared, legacy free-text,
    manager-on-behalf, manager-without-target, worker-peer denial, no `FOR UPDATE`, workspace
    target resolution, PERSONAL filtering, pagination, and workspace isolation.
  - `pytest tests/integration/services/queries/ -q` → `69 passed`.
  - Focused clock-action acceptance set (toggle in/out, direct double-in, direct out-without-in,
    manager on-behalf + missing-target + double-out) → `4 passed`. The complete
    `test_worker_shift_commands.py` run → `39 passed, 2 failed`; both failures are the exact
    master-plan baseline seed gaps in clock-out tests (missing system pause-reason rows), not new
    failures. The focused green tests pin `analytics: null`, no clock-in key, symmetric conflicts,
    on-behalf access, and the unchanged clock machinery.
  - `pytest tests -q` → `1261 passed, 25 failed, 2 warnings`. The failed list is a strict subset of
    the independently established pre-Phase-3 27-failure baseline recorded in the archived Phase
    3 plan; all failures remain in the documented bootstrap/items/task-steps/upholstery/
    working-sections/audit/shopify/auth/worker-stats/router/worker-shift baseline families. No
    Phase 4 test failed.
  - Ruff on every touched Python file → `All checks passed!`. Repository-wide
    `ruff check .` → `141` pre-existing errors, matching the independently recorded Phase 3
    repository baseline and below the master plan's original `149`; no touched file appears.
  - `git diff --check` → clean.
  - Field-for-field manual pass against handoff §§4, 5, and corrected 7 → conformant. Per the
    operator's review-first instruction, the operator-owned handoff liveness table remains
    unchanged until approval.

  **Scope controls**
  - No Connecteam handler, webhook pipeline, midnight safeguard, pause-reasons implementation,
    model, migration, timeline/stats endpoint, or frontend handoff file was modified.
  - No implemented summary was written; no plan/master status was flipped; no archive move was
    performed. Lifecycle state is implementation complete, awaiting independent review.

- `2026-07-30T08:55:00Z` — Independent review (Opus 5), round 1 — **NEEDS_CHANGES** (one blocking
  item; implementation itself conforms).

  **Review environment caveat (affects method, not verdict)**
  - The repository is **not a git repository** (`git log`/`git diff`/`git diff --check` all fail with
    `fatal: not a git repository`). Diff-based checklist items could not be executed as written.
    Substituted method: full read of every implementation file + mtime-based change detection
    (`find … -newermt`) + import-graph checks. The plan's own Review log claims `git diff --check →
    clean`, which is not reproducible here — flagged so the operator can reconcile.

  **Verified conformant**
  - `POST /clock-in` / `POST /clock-out` are thin wrappers over the existing commands
    (`worker_shifts.py:58-89`). `clock_in_worker_shift.py` is byte-unmodified (mtime predates the
    phase); `clock_out_worker_shift.py` changed only by the authorized `"analytics": None` key
    (`clock_out_worker_shift.py:40`, plan scope 1b / acceptance 2).
  - `clock_out_at` unreachable over HTTP: `WorkerClockBody` (`worker_shifts.py:26-27`) carries only
    `user_id`; pydantic's default `extra="ignore"` drops the field, proven by
    `test_worker_shifts_router.py:95-107`. Probed independently — not forwarded.
  - `/clock` toggle preserved; `analytics: None` added to the clock-out branch only
    (`toggle_worker_shift.py:56-63`), regression-pinned at command level by
    `test_worker_shift_commands.py:981-1010` (`"analytics" not in clock_in_result`) — passing.
  - `GET /current` is read-only: no `with_for_update` in `services/queries/users/` or
    `services/worker_shift_access.py` (grep clean); `test_get_current_worker_shift_state.py:150-178`
    asserts `_for_update_arg is None` on every executed statement.
  - Access matrix tested (worker self / manager on-behalf / manager without target `403` / worker on
    peer `403`) and all five state scenarios covered (clocked out, idle, working, step-paused,
    declared) — `test_get_current_worker_shift_state.py:149-345`, all green.
  - Legacy free-text `reason` → `pause_reason: null` + `reason_text` (`serializers.py:171-172`),
    tested at `test_get_current_worker_shift_state.py:288-311`. No 500 path.
  - `shift_started_at` sourced from `max(STARTED_SHIFT.entered_at) <= now`
    (`get_current_worker_shift_state.py:22-32`), **not** the open row's `entered_at` — confirmed
    empirically (probe returned `shift_started_at` 06 ms earlier than `state_entered_at`).
  - Reasons listing: filter was **pre-existing** — `pause_reasons.py:56` (`pause_type` `Query`) and
    `list_pause_reasons.py:15-27`. No pause-reasons file was modified. Plan item 3 is
    documentation-only, as the verify-first assumption anticipated.
  - Connecteam surface untouched (D8): no file under `services/tasks/connecteam/`,
    `services/infra/connecteam/`, or `services/tasks/users/auto_clock_out_open_shifts.py` has a
    post-phase mtime; the safeguard still calls the `clock_out_shift_for_user` helper
    (`auto_clock_out_open_shifts.py:9,52`), so it never receives the `analytics` envelope — matches
    D14's "safeguard/Connecteam paths never compute it".
  - Field-for-field handoff conformance (§4, §5, §7) confirmed against the implemented shapes,
    including `UserShiftStateEnum` wire values (`idle|working|in_pause`) and the `+00:00` offset
    (columns are `DateTime(timezone=True)`, so `.isoformat()` emits the documented suffix).
  - Ruff on all nine touched files → `All checks passed!`.

  **Adversarial probes (all three executed, all pass)**
  - Manager `GET /current` on a non-member user → `NotFound` → `404`. ✅
  - `GET /current` immediately after declare → `state: "in_pause"`, `declared_state.id` equals the
    declare response's id, `state_entered_at == declared_state.entered_at`, `pause_reason` resolved.
    ✅
  - Double `POST /clock-in` → `ConflictError` (`409`) and **zero** additional
    `user_shift_state_records` rows (2 before, 2 after). ✅

  **Findings**
  - **R1 — BLOCKING (medium, doc).** Acceptance criterion 5 second half is unmet: the handoff
    liveness table at `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md:18`
    still reads `| 4 | GET /current, POST /clock-in, POST /clock-out (§4, §5) | ❌ not yet |`. That
    table is the frontend's declared single source of truth ("no phase is live until its row shows
    ✅", same file line 325-327), so the contract currently tells the frontend to keep mocking a
    surface that is implemented and green. The Review log records an operator "review-first"
    instruction for this deferral, which the reviewer cannot verify — operator to confirm or Codex
    to flip the row.
  - **R2 — informational (no action).** Master plan Phase 4 row (`MASTER_PLAN…:61`) is still
    `under_construction`. The review prompt's checklist asks for it, but the master plan's own
    per-phase workflow (step 4) places the table update *after* approval. Resolved in the master
    plan's favor — not a defect. Master plan correctly NOT archived (Phases 5–7 remain).
  - **R3 — informational (no action).** The review prompt's "diff must not touch
    `clock_out_worker_shift.py`" and "`/clock` toggle untouched" items are superseded by plan scope
    1b + acceptance 2 (operator ruling 2026-07-30). Both touches are exactly the `analytics` key and
    nothing else.
  - **R4 — hardening (low).** `ClockOutWorkerShiftRequest` still parses `clock_out_at` from
    `ctx.incoming_data` (`clock_out_worker_shift.py:12-14`). The audit hole is closed *only* by the
    route model dropping extras; there is no command-layer guard and no command-layer test. Any
    future route that forwards a raw body dict, or an `extra="allow"` config change, silently
    re-opens backdated clock-out. Consider asserting `clock_out_at is None` unless an internal
    caller flag is set. Not a plan violation — correct as shipped.
  - **R5 — hardening (low).** The `reason_text` fallback (`serializers.py:171-172`) fires on *any*
    unresolved reason join, not only on legacy free text. Today the join omits `is_deleted`, and
    pause reasons are soft-deleted only, so it is unreachable; but if the join is ever tightened or a
    reason is hard-deleted, the client would receive a raw `par_…` client_id inside `reason_text`,
    which the handoff (§4) documents as human-readable free text.
  - **R6 — test gap (low).** The `404` branch of `GET /current` (manager naming a non-worker /
    non-member) has no test, though the reviewer's probe confirms the behavior. The access-matrix
    test covers only the two `403` branches.
  - **R7 — evidence discrepancy (informational).** Independent full-suite re-run:
    `1259 passed, 28 failed` vs the Review log's `1261 passed, 25 failed`. Reconciled: no Phase 4
    file is among the failures. `test_worker_shifts_router.py` → `27 passed`;
    `test_get_current_worker_shift_state.py` → all green;
    `tests/integration/services/queries/` → `68 passed, 1 failed`. The deltas are (a) two auth
    failures including `test_blocklisted_floor_access_token_cannot_bypass_revocation_via_refresh` —
    **Phase 5 work-in-progress that is already sitting in this same working tree** (`auth.py`,
    `sign_in_user.py`, `logout_user.py` all carry post-Phase-4-plan mtimes), and (b)
    `test_list_pause_reasons_returns_offset_pagination_and_workspace_scope`, a dirty-test-DB
    non-idempotency: `PauseReason` declares `Index("uq_pause_reasons_slug", "slug", unique=True)`
    (`pause_reason.py:47`) — globally unique, not workspace-scoped — so re-seeding the first
    workspace hits `UniqueViolationError` on `waiting_for_upholstery`. Pre-existing baseline family;
    the file was not modified by this phase. Only Phase-4-adjacent failure is
    `test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`, reproduced as the
    documented baseline seed gap (`NotFound: System pause reason 'pause_ended_shift' is not
    configured`).
    Operator note: reviewing Phase 4 against a tree that already contains uncommitted Phase 5 code
    weakens every "full suite" claim for both phases.

  **Verdict: NEEDS_CHANGES** — R1 only. R4/R5/R6 are optional hardening; R2/R3/R7 need no code change.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`

## Fix-cycle review log

- `2026-07-30T09:25:40Z` — Codex fix cycle for R4-R7 complete; back to independent review.

  **Changes and pinning tests**
  - **R4:** Removed `clock_out_at` from `ClockOutWorkerShiftRequest`; the command now always
    supplies `datetime.now(timezone.utc)` to `clock_out_shift_for_user`. The midnight safeguard
    continues to call that helper directly and was not changed. Command-layer
    `test_direct_clock_out_ignores_supplied_clock_out_at` pins that a raw incoming
    `clock_out_at` cannot backdate the `ENDED_SHIFT` marker.
  - **R5:** The current-state serializer now emits `reason_text: null` when an unresolved paused
    reason starts with `PauseReason.CLIENT_ID_PREFIX`; non-ID legacy text remains unchanged.
    `test_current_state_serializes_legacy_free_text_reason` pins the legacy branch and
    `test_current_state_does_not_expose_unresolvable_pause_reason_id` pins the catalog-ID branch.
  - **R6:** `test_current_state_uses_clock_action_access_matrix` now proves a manager targeting a
    non-member raises `NotFound`; router test
    `test_current_route_preserves_non_member_not_found_status` pins the resulting `GET /current`
    `404` envelope.

  **Validation and evidence hygiene**
  - Focused R4-R6 tests → `4 passed`; full router file → `28 passed`; standalone
    `test_get_current_worker_shift_state.py` → `8 passed`; ruff on all five touched Python files
    → `All checks passed!`.
  - The combined current-state/pause-reasons command reached the known
    `test_list_pause_reasons_returns_offset_pagination_and_workspace_scope` seed collision
    (`uq_pause_reasons_slug` / `waiting_for_upholstery`). The broader integration-query run
    failed across unrelated query families, including tests that pass standalone; the command
    suite likewise failed broadly with environment `PermissionError` failures. The full suite
    reported `979 passed, 313 failed, 11 errors`; it is not a usable new-failure signal in this
    shared test environment. No production fix outside Phase 4 scope was attempted.
  - Phase 5's concurrent auth work remains outside this fix cycle and was not modified or staged.
    The full-suite failure list includes
    `tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`,
    which is auth-phase; the pause-reason seed collision and the other non-auth broad-run failures
    are baseline/environment failures, not attributed to these Phase 4 changes.
  - Locally executed `git diff --check` completed clean. This is a local observation only; the
    previous reviewer reported that its sandbox could not run git, so no claim is made for that
    environment.

- `2026-07-30T09:54:25Z` — Independent review (Opus 5), **round 2** — **APPROVED**. R4/R5/R6 verified
  closed; three low findings recorded for follow-up (none blocking).

  **Method / environment**
  - `git` **is** available in this environment when run from `backend/` (the repo root is
    `backend/.git`; round 1's `fatal: not a git repository` came from invoking git one level up, at
    `ManagerBeyo-app/`). Round 2 therefore used real diffs — `git show 20b11c7`, `git show ccdffa9`,
    `git show <rev>:<path>` — not mtimes. Both Phase 4 commits were reviewed as commits; the working
    tree (which also carries Phase 5 history through `49df920`) was not used as the unit of review.
  - Files touched by the two commits, in total: `domain/users/serializers.py`,
    `routers/api_v1/worker_shifts.py`, `services/commands/users/_worker_shift_access.py`,
    `clock_out_worker_shift.py`, `toggle_worker_shift.py`,
    `services/queries/users/get_current_worker_shift_state.py`,
    `services/worker_shift_access.py`, three test files, this plan. Nothing else.

  **R4 — CLOSED (verified)**
  - `clock_out_at` is gone from the model itself, not merely dropped by the route:
    `ClockOutWorkerShiftRequest` now has only `user_id` (`clock_out_worker_shift.py:12-13`), and the
    command assigns `clock_out_at = datetime.now(timezone.utc)` unconditionally with no fallback
    expression (`clock_out_worker_shift.py:25`).
  - Sole caller confirmed by grep: `routers/api_v1/worker_shifts.py:13,86`. No task, scheduler, or
    other command invokes the command function.
  - `_clock_worker_shift.py` is untouched by **both** commits (`git show --stat <rev> --
    …/_clock_worker_shift.py` → empty for each) and keeps its own `clock_out_at` parameter
    (`_clock_worker_shift.py:135`, used at `:154,170,178,181,212,220-221`). `services/tasks/` is
    likewise untouched by both commits; the safeguard still passes its computed `midnight` straight
    into the helper (`auto_clock_out_open_shifts.py:52-57`). The safeguard's clock_out_at path is
    structurally unaffected by R4.
  - Both midnight tests green:
    `test_midnight_safeguard_closes_previous_day_shift_and_allows_new_day` (`:2152`) and
    `test_midnight_safeguard_preserves_open_legacy_manual_pause` (`:2246`) → `2 passed`. Neither is
    inside any hunk of either commit (all `test_worker_shift_commands.py` hunks land in `998-1123`).
  - The pinning test is genuinely discriminating: `test_direct_clock_out_ignores_supplied_clock_out_at`
    feeds `{"clock_out_at": "2000-01-01T00:00:00+00:00"}` through `ctx.incoming_data` at the **command**
    layer and asserts `ENDED_SHIFT.entered_at == 2026-07-30T12:00Z` (frozen). It would fail if the
    field were still honoured. → `1 passed`.

  **R5 — CLOSED (verified), and the fix closes a reachable case, not only a hypothetical one**
  - `serializers.py:171-176`: `reason_text` is emitted only when the unresolved value is not
    `par_`-shaped; id-shaped-but-unresolvable yields `pause_reason: null` **and**
    `reason_text: null`. Prefix constructed as `f"{PauseReason.CLIENT_ID_PREFIX}_"` and
    `CLIENT_ID_PREFIX == "par"` (`pause_reason.py:12`) → `"par_"`, correct (no double underscore).
  - Both branches pinned: `test_current_state_serializes_legacy_free_text_reason` asserts the full
    envelope incl. `reason_text: "legacy meeting"`;
    `test_current_state_does_not_expose_unresolvable_pause_reason_id` asserts `pause_reason is None`
    and `reason_text is None` (the subscript also pins that the key is *present*, not dropped).
  - Extension of round 1's framing: the reason join is workspace-scoped
    (`get_current_worker_shift_state.py:57-58`), so an id belonging to **another workspace** was
    already unresolvable before any join tightening. Pre-R5 that would have shipped a foreign
    tenant's `par_…` id to the client. R5 closes a cross-tenant identifier leak, not just a
    future-proofing gap.

  **R6 — CLOSED (verified)**
  - Query layer: `test_current_state_uses_clock_action_access_matrix` now ends with a manager naming
    a non-member → `pytest.raises(NotFound)`. Router layer:
    `test_current_route_preserves_non_member_not_found_status` drives the route with a `NotFound`
    outcome and asserts `404` plus the exact `{"error": …, "ok": false}` envelope through the real
    `build_err`. Access matrix is now 403/403/404 + manager-on-behalf success.

  **Pre-check claims — falsification attempts, results**
  - *"Access-helper extraction is a pure move"* — **CONFIRMED, stronger than claimed.** Git blob
    identity proves it: the new `services/worker_shift_access.py` is created with blob `d03af3c`,
    which is exactly the pre-image blob of `services/commands/users/_worker_shift_access.py` in the
    same commit. Byte-identical by construction, not by inspection.
  - *"Old module re-exports; Phase 3's writer path unchanged"* — **CONFIRMED.** The shim is
    `import` + `__all__` (`_worker_shift_access.py:1,4`), and every writer still imports through the
    shim: `clock_in_worker_shift.py:7`, `clock_out_worker_shift.py:7`, `toggle_worker_shift.py:11`,
    `declare_worker_state.py:27`, `close_declared_worker_state.py:14`. Only the new query service
    imports the new path.
  - *"Neither commit touches Connecteam, the midnight safeguard, auth, or the handoff"* —
    **CONFIRMED** against the complete two-commit file list above. Also untouched: models,
    migrations, pause-reasons implementation, master plan.
  - *"analytics appears only on the clock-out branch"* — **CONFIRMED.** `clock_out_worker_shift.py:39`
    (always) and `toggle_worker_shift.py:56-63` (guarded by `if action == "clock_out"`).
    `clock_in_worker_shift.py` is untouched by both commits and returns `{"action", "user_id"}` only.
  - *"GET /current has zero `with_for_update`"* — **CONFIRMED** by reading the whole query service
    plus the runtime assertion `all(statement._for_update_arg is None …)` in
    `test_current_state_returns_clocked_out_shape_without_write_lock`.
  - Additional probe (not in the pre-check): the single `select(...).one_or_none()`
    (`get_current_worker_shift_state.py:70`) could in principle raise `MultipleResultsFound` → 500 if
    the outer joins fanned out. It cannot: both `user_shift_state_records` and
    `user_declared_state_records` carry partial unique indexes on `(user_id, workspace_id) WHERE
    exited_at IS NULL` (`user_shift_state_record.py:48-53`, `user_declared_state_record.py:49-55`),
    and the two reason joins are on unique `client_id`. No 500 path. Relatedly, a stale open declared
    row cannot survive a clock-out: the helper clamps it (`_clock_worker_shift.py:159-179`).
  - Handoff conformance re-checked field-for-field against §4 (current-state envelope, `idle |
    working | in_pause`, clocked-out all-null shape, `+00:00` note) and §5 (`/clock-in` →
    `{action,user_id}`; `/clock-out` → `{action,user_id,transitioned_steps,analytics}`; toggle
    clock-out adds the key, clock-in never has it). Conformant.

  **Validation (quiet tree, no concurrent session)**
  - `pytest tests/unit/test_worker_shifts_router.py -q` → **28 passed**.
  - `pytest tests/integration/services/queries/users/test_get_current_worker_shift_state.py -q` →
    **8 passed**.
  - R4 pinning test + both midnight safeguard tests → **3 passed**.
  - `pytest tests -q` → **27 failed, 1275 passed** — an exact match to the operator's canonical
    baseline at `ccdffa9`, and the failure **node set** is entirely baseline families
    (bootstrap/items/pause-reasons/shopify/task-steps/tasks/upholstery/working-sections/audit/
    shopify-domain/auth/worker-stats/serializers/routers). Only worker-shift failure is the
    documented seed gap `test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`; the
    only auth failure is `test_sign_in_user_preserves_custom_workspace_role_name` (Phase 5 domain).
    No Phase 4 test failed. Codex's `313 failed / 11 errors` is disregarded per the master plan's
    shared-DB rule.
  - `ruff check` on all ten touched files → **All checks passed!**. Repo-wide `ruff check .` →
    **133 errors**, below the recorded 149/141 baselines, none in a touched file. (No ruff config
    exists — default `E`/`F` only, so import ordering is not linted.)

  **Findings (all low, none blocking)**
  - **R8 — low (layering). S1 CONFIRMED, but its proposed remedy is wrong.**
    `services/worker_shift_access.py` is a domain-specific module placed at the top level of
    `services/`, which `architecture/01_architecture.md:60-78` reserves for framework primitives
    (`context.py`, `outcome.py`, `run_service.py`; `work_context.py` is domain-agnostic and has its
    own contract `39`). It also sidesteps the same file's domain-grouping rule (`:80-95`: every layer
    groups by `<domain>/`). **However** S1's suggested fix — put it under `infra/` "as Phase 5's
    equivalent helper does" — would be a *harder* violation: `01_architecture.md:43` forbids
    `services/queries/` from importing `services/infra/` at all, so the new query service could not
    reach it. The S1 comparison is also not apples-to-apples: Phase 5's `services/infra/auth.py` is a
    pre-existing module it *modified* (`b8946fe`, 8 lines), not a helper it created. The
    contract-clean placement is `services/queries/users/_worker_shift_access.py` — queries are the one
    layer both callers may import, with precedent at `_clock_worker_shift.py:21` (a command importing
    `services/queries/pause_reasons/get_system_pause_reason`). Cosmetic today; worth normalizing
    before more shared shift logic accumulates.
  - **R9 — low (doc). S2 CONFIRMED, operator-owned.** Handoff §4 (`…floor_app_20260729.md:143`)
    documents only `pause_reason: null` + `reason_text: "<raw>"`. The new variant introduced by R5 —
    `pause_reason: null` + `reason_text: null` — is undocumented, while the same handoff states "Any
    contract change will be edited **here first**" (`:25`) and this plan's scope item 4 requires
    deviations to go through the handoff first. Related nit for the same edit: `reason_text` now has
    three-way variance (absent when the reason resolves, `null` when id-shaped-unresolvable, a string
    for legacy text) — worth one sentence so the frontend does not read absence as a distinct state.
    The handoff is operator-owned, so this is an operator follow-up, not a Codex defect.
  - **R10 — low (observability). NEW.** The R5 branch is silent: when `state == IN_PAUSE` and `reason`
    is a `par_`-shaped id that does not resolve in the workspace, the response is fully nulled
    (`serializers.py:171-176`) with no log line anywhere in the read path. That condition is a
    data-integrity signal — a dangling or cross-tenant reason reference — and R5 makes it invisible to
    operators as well as clients. `architecture/17_logging.md:23` classes exactly this shape
    (degraded-but-recoverable / non-fatal validation issue) as `WARNING`, and the sibling write path
    already logs its analogous clamp (`_clock_worker_shift.py:171-179`, INFO). Recommend a
    `logger.warning` carrying `workspace_id`, `user_id`, and the unresolved value.
  - Round-1 items: **R1 CLOSED** by operator ruling (handoff liveness row is operator-owned, flipped
    only post-approval; the stale clause was removed from plans 4/6/7) — not re-raised. R2/R3
    unchanged (informational). **R7 resolved**: this round's suite matches the canonical baseline node
    for node, and git was available, so the round-1 evidence discrepancy and the mtime substitution
    are both retired.

  **Verdict: APPROVED.** R4/R5/R6 closed and independently verified; no functional defect found at
  any severity. R8/R9/R10 are low follow-ups that do not gate the phase; R9 belongs to the operator's
  post-approval handoff edit and can ride along with the liveness-row flip.

- `2026-07-30T10:20:00Z` — Post-approval polish pass (Opus 5) for **R8 + R10**. No behavior change
  for R8; R10 adds one observability log line. R9 operator-owned (handoff untouched); R1/R7 closed.

  **R8 — relocated the shared access helper**
  - `git mv app/beyo_manager/services/worker_shift_access.py
    app/beyo_manager/services/queries/users/worker_shift_access.py`. Git records it as a pure rename
    (`git diff --cached -M --stat` → `services/{ => queries/users}/worker_shift_access.py | 0`,
    `1 file changed, 0 insertions(+), 0 deletions(-)`), so the reviewer's blob-identity property is
    preserved — `resolve_worker_shift_target`'s body is byte-identical to its pre-image.
  - Two import sites updated, both mechanical: the writer shim
    `services/commands/users/_worker_shift_access.py` (still re-exporting the symbol, so all five
    writer call sites are untouched) and `services/queries/users/get_current_worker_shift_state.py`.
    `grep -rn "services.worker_shift_access"` over `*.py` is clean; remaining hits are historical
    prose in this plan's earlier log entries, left as written.
  - Destination is the prompt's path, `queries/users/worker_shift_access.py`. The round-2 finding
    text (`:459`) wrote it with a leading underscore; the non-underscore form was used because the
    prompt specifies it and because the writer shim already owns the `_worker_shift_access.py`
    basename — two same-named modules in one feature would be a readability trap. Placement (the
    substance of R8) is exactly as the reviewer verified. **Operator: cosmetic, flag if you disagree.**
  - No registration risk: `services/queries/` has no auto-discovery (`grep` for
    `import_module`/`pkgutil`/`walk_packages` over `beyo_manager/` → no hits); every query is
    imported explicitly by its router. Helper modules already coexist under `queries/`
    (`queries/utils/`, `queries/items/lookup/`).

  **R10 — WARNING on the unresolvable-reason branch**
  - Log placed in the **query**, not in the serializer where the branch itself lives:
    `01_architecture.md:43` bars `domain/` from `models/`, `services/`, and **any I/O**, so emitting
    from `domain/users/serializers.py` would trade R8's layering fix for a fresh violation of the
    same contract. `services/queries/` may log and does elsewhere (5 precedents, e.g.
    `queries/items/lookup_item_by_article_number.py`).
  - To keep the two sites from drifting, the branch predicate is now named once in the domain layer —
    `pause_reason_reference_is_unresolved(current, pause_reason)` (`serializers.py`, pure, no I/O) —
    and consumed by both the serializer's `reason_text` ternary and the new query-side warning.
    Inside the serializer's existing guard (`is_paused and reason is not None and pause_reason is
    None`) the predicate reduces to the original `startswith` check, so R5's behavior is unchanged.
  - `get_current_worker_shift_state` logs at WARNING per `17_logging.md:23`, in the feature's
    structured `worker_shift.*` style matching the sibling clamp at `_clock_worker_shift.py:171-179`:
    `worker_shift.current_state_unresolved_pause_reason | workspace_id=%s user_id=%s
    shift_record_id=%s pause_reason_id=%s` — all four fields the finding asked for, including the
    shift record id and the unresolved `par_…` value.

  **Gate evidence**
  - New tests (written before the fix, confirmed red on the unresolvable path while both negatives
    passed): `test_current_state_warns_on_unresolvable_pause_reason_id` asserts exactly one WARNING
    carrying all four fields; `test_current_state_does_not_warn_for_resolved_or_legacy_reason[True]`
    and `[False]` assert the event is absent on the resolved-id and legacy free-text paths.
  - `test_get_current_worker_shift_state.py` → `11 passed`. Worker-shift/router/backfill set
    (`test_worker_shift_commands.py`, `test_reconcile_worker_shift_state.py`,
    `test_worker_shifts_router.py`, `test_backfill_worker_shift_state_records.py`) → `84 passed`,
    `1 failed` = the documented baseline seed gap
    `test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`.
  - **Full suite, quiet tree, `-m 'not e2e'` → `27 failed / 1279 passed`.** Per the master plan's
    compare-node-sets-not-counts rule, the same suite was run at `HEAD` (`6c33fc2`) in a throwaway
    `git worktree` — `27 failed / 1274 passed` — and `diff` of the two `FAILED` node lists is
    **empty: zero new failures, identical node sets**. The `+5` passes are this pass's 3 new tests
    plus Phase 5's uncommitted test additions, which are present in the working tree only. The 4
    non-worker-shift failures seen in focused runs (2 × `test_pause_reasons_commands`,
    `test_list_pause_reasons_returns_offset_pagination_and_workspace_scope`,
    `test_serialize_case_type_entry_returns_contract_fields`) were each reproduced at `HEAD` in that
    worktree, confirming baseline rather than regression.
  - `ruff check` on all five touched files → **All checks passed!**. `ruff format --check` reports
    drift on `serializers.py`, `get_current_worker_shift_state.py`, and the test file, but the same
    files already fail that check at `HEAD` (verified in the baseline worktree) — pre-existing, and
    the repo gate is `make lint` = `ruff check`, which passes. No new format drift introduced.
  - Parallel-run discipline held: Phase 5's in-flight auth changes
    (`jwt_dep.py`, `services/infra/auth.py`, two auth test files) and its plan edit were neither
    modified nor staged; the commit stages only the four Phase 4 files and this plan.
