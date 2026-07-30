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
