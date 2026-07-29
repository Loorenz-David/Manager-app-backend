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
  2. Query service `services/queries/users/get_current_worker_shift_state.py` + route `GET /current` (query param `user_id` optional; same access rule as clock: workers omit it → self; admin/manager must pass it).
  3. Reasons listing: verify `services/queries/pause_reasons/list_pause_reasons.py` + its route support filtering by `pause_type`; if not, add an optional `pause_type` query param (additive) so the declare picker can fetch PERSONAL reasons only.
  4. Handoff validation: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` was written **ahead of implementation** (the frontend builds against it in parallel). This phase's deliverable is conformance: implement `GET /current` and the clock routes to match it field-for-field, and record in the handoff's status line that Phases 1–4's endpoints are now live. Any needed deviation → operator decision + handoff update first.
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
2. `POST /clock` still works unchanged (regression).
3. `GET /current` matrix: worker self (clocked out / idle / working / step-paused / declared) each returns the documented shape; manager with `user_id` reads another worker; worker passing `user_id` of someone else → `403`; legacy free-text pause row serializes per spec without error.
4. Reasons listing filterable by `pause_type=personal` (pre-existing or added); response contract otherwise unchanged.
5. Implemented `GET /current` + clock routes match `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` field-for-field (conformance asserted by contract tests keyed to the handoff's documented shapes); the handoff's status line records Phases 1–4 as live.
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
6. Conformance pass against the floor-app handoff; update its status line (acceptance 5).
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

- (empty — filled by implementer and reviewer)

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
