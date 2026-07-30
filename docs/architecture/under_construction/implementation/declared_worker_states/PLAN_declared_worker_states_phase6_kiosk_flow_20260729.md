# PLAN_declared_worker_states_phase6_kiosk_flow_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase6_kiosk_flow_20260729`
- Status: `under_construction`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T12:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (decisions D12–D14 govern this phase)
- Prerequisite: Phases 3, 4 **and** 5 archived (on-behalf declare/close, `GET /current` + clock routes, and the `floor` scope all live).

## Goal and intent

- Goal: The kiosk worker flow — workers identify at the shared floor device by **clock-in code or working email**, matched **client-side** against the polled roster (D13 rev 3): the backend adds `clock_in_code` to the existing `GET /users` response for floor-scope sessions only. Plus the clock-out response's reserved `analytics` envelope (D14).
- Business/user intent: Workers without personal devices (or with hands full) operate their whole shift day from the wall terminal in seconds: type code → tap "yes, that's me" → clocked in. The roster lives in the device's TanStack cache, so matching is instant — no lookup round-trip.
- Non-goals: A server-side identify endpoint (dropped, D13 rev 3 — matching is client-side). Computing actual clock-out analytics (future feature — this phase only reserves the response slot, D14). Device registry/management. PIN-style secrecy guarantees (the code identifies, the human confirms, the device's manager token authorizes — the code is not a password).

## Scope

- In scope:
  1. Migration + model: `clock_in_code` on `UserWorkProfile` — `String(16)`, nullable; partial unique index `uix_user_work_profiles_workspace_clock_code` on `(workspace_id, clock_in_code)` `WHERE clock_in_code IS NOT NULL`.
  2. Code management: extend the existing work-profile admin update path (**verify-first**: locate where `salary_per_hour_*` / work-profile fields are set — expected `services/commands/users/update_user_admin.py` and/or `register_user.py` — and follow that established path) to set/clear `clock_in_code`. Validation: trimmed, 4–16 chars, workspace-unique → friendly `409` on conflict. `updated_by_id` stamped per the users-README rule.
  3. Floor-scoped code exposure in the roster: `services/queries/users/list_users.py` — when `ctx.identity["app_scope"] == "floor"`, each returned user item (compact and full modes) gains two additive fields: `"clock_in_code": <str | null>` and `"email": <str>` (email enables the email-matching path at the device; **verify-first** whether `email` is already present in the serialized shapes — if so, only `clock_in_code` is added). Codes are fetched in **one** batched query over `UserWorkProfile` for the page's user ids (no N+1). For any other `app_scope`, the response is **byte-identical to today** — the fields must be absent, not `null`.
  4. *(moved to Phase 4, operator ruling 2026-07-30)* The clock-out `"analytics": null` envelope ships with Phase 4 (the phase that makes the routes live). This phase only keeps its regression tests green.
  5. Final handoff conformance: verify the full implemented surface against `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`; mark all phases live in its status line.
- Out of scope: analytics computation; worker app changes; Connecteam anything (D8); any new lookup/identify endpoint.
- Assumptions:
  - Client-side matching is UI sugar, not an authorization grant — the *action* endpoints (`/clock-in`, `/clock-out`, `/declared-states*`) perform all authorization/validation regardless of what the device matched locally.
  - The device treats the roster cache as *who*, never *what state*: after confirmation it fetches `GET /current?user_id=…` fresh before rendering actions (documented in the handoff — backend needs nothing for this beyond Phase 4).
  - `clock_in_code` is unset (`NULL`) for workers until a manager assigns one; email fallback always works — rollout needs no backfill.
  - Codes are workspace-unique, not globally unique (two workspaces may both use "1234").

## Clarifications required

- [x] Code format? — resolved: free string 4–16 chars (managers may use numeric PINs or short mnemonics); veto in review.
- [x] Server-side identify endpoint vs client-side matching? — resolved (D13 rev 3): client-side against the polled roster; `clock_in_code` exposed in `GET /users` for floor-scope sessions only. Accepted trade-off recorded in the master plan rev-3 note.
- [x] Should regular manager/worker sessions receive codes in `GET /users`? — resolved: no — floor scope only; other scopes' responses stay byte-identical.

## Acceptance criteria

1. Migration: column + partial unique index apply/downgrade cleanly; duplicate code in one workspace → `IntegrityError` at DB level; same code across workspaces OK.
2. Code management: admin sets/clears a worker's code through the established update path; duplicate in workspace → friendly `409`; `updated_by_id` stamped; length/trim validation enforced.
3. Roster exposure matrix: floor-scope session calling `GET /users?role=worker&compact=true` → every item carries `clock_in_code` (value or `null`) and `email`; full (non-compact) mode likewise; `manager`/`worker`/`admin`/`seller`-scope sessions → fields **absent** and response byte-identical to pre-phase behavior (existing list_users tests unmodified and green).
4. Code fetch is batched (one query for the page) — no per-user query; asserted via query-count or code inspection recorded in the Review log.
5. Regression only (envelope delivered by Phase 4, ruling 2026-07-30): both clock-out routes still carry `"analytics": null`; Phase 4's pinning tests unmodified and green.
6. Full-loop kiosk test: floor sign-in (Phase 5) → `GET /users?role=worker&compact=true` returns the worker with their code → `GET /current` (not clocked in) → `/clock-in` on-behalf → `GET /current` (idle) → declare on-behalf → `GET /current` (declared) → `/clock-out` → response has `analytics: null` and correct `transitioned_steps`.
7. Handoff conformance: every endpoint/shape in `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` matches the implementation; status line marks all phases live.
8. Full suite green; `ruff check` clean.

## Contracts and skills

### Contracts loaded

- `backend/architecture/03_models.md` + `30_migrations.md`: column + partial index migration.
- `backend/architecture/07_queries.md` (+ local): the list_users query extension.
- `backend/architecture/09_routers.md`: route wiring; gating composition (`require_app_scope` + `require_roles`).
- `backend/architecture/06_commands.md` (+ local): work-profile update + clock-out envelope edits.
- `backend/architecture/18_security.md`: rate limiting, anti-enumeration response discipline.
- `backend/architecture/28_roles_permissions.md`: scope/role gate composition.
- `backend/architecture/46_serialization.md` (+ local): reuse of `serialize_user_working_section_member`; snapshot reuse.
- `backend/architecture/20_api_versioning.md`: additive-only on clock responses.
- `backend/architecture/15_testing.md`: placement.

### Local extensions loaded

- `06_commands_local.md`, `07_queries_local.md`, `46_serialization_local.md`.

### File read intent — pattern vs. relational

Permitted relational reads:
- `models/tables/users/user_work_profile.py` — model being extended (+ its README rules: snapshot-before-mutate does NOT apply to `clock_in_code` — it is operational identity, not compensation history; note this in the README).
- `services/commands/users/update_user_admin.py`, `register_user.py` — the established work-profile write path (the verify-first item).
- `services/queries/users/list_users.py` + `domain/users/serializers.py` — the roster query/serializers being extended (incl. whether `email` is already serialized — the verify-first item).
- `routers/api_v1/users.py` — the roster route (wiring unchanged; claims already flow via `ServiceContext`).
- `services/commands/users/clock_out_worker_shift.py`, `toggle_worker_shift.py` — response envelopes being extended.
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` — THE contract (mandatory read).

Prohibited pattern reads: other queries/commands/routers for skeleton → `07`/`06`/`09`.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
- Router trigger terms: `worker`, `query`, `migration`, `security`.
- Excluded alternatives: none.

## Implementation plan

1. Migration + model field + partial unique index; README note (`clock_in_code` exempt from compensation-snapshot rule).
2. Verify-first: locate the work-profile write path; extend it with `clock_in_code` (validation + friendly `409`).
3. Verify-first: is `email` already in the list_users serialized shapes? Then extend `list_users` with the floor-scope-conditional fields (`clock_in_code`, and `email` if missing), batched code fetch, both compact and full modes.
4. Regression guard: assert non-floor responses byte-identical (existing tests unmodified).
5. (dropped — envelope delivered by Phase 4 per ruling 2026-07-30; keep its tests green.)
6. Tests per acceptance 1–6 (the full-loop kiosk test is the flagship — write it first).
7. Handoff conformance pass; update status line (acceptance 7).

## Risks and mitigations

- Risk: the roster + codes live in the kiosk device's memory (anyone at the device could read them via devtools).
  Mitigation: accepted trade-off (master rev-3 note) — same trust boundary as the device's manager token; codes are identification-not-authentication by design (D12); the human-confirm step and manager-authorized device are the trust anchors. Documented in the handoff.
- Risk: codes leak into the regular manager/worker apps via the shared endpoint.
  Mitigation: floor-scope-conditional serialization with byte-identical non-floor responses (acceptance 3); existing list_users tests unmodified are the regression proof.
- Risk: the device acts on a stale roster (worker clocked in via Connecteam since the last poll).
  Mitigation: cache decides *who*, never *what* — mandatory fresh `GET /current` after confirm (handoff §9 flow); action endpoints validate state server-side regardless.
- Risk: `analytics` envelope forgotten on the `/clock` toggle branch.
  Mitigation: acceptance 5 covers both routes explicitly.
- Risk: future analytics computation bloats clock-out latency.
  Mitigation: out of scope now; the reserved-null design lets the future implementation choose sync-vs-async without a breaking change (D14) — note carried into the implemented summary.

## Validation plan

- `alembic upgrade head` / `downgrade -1` / `upgrade head`: clean.
- `pytest app/tests/integration/ -q -k "list_users or work_profile or kiosk or clock"`: new suites green.
- `pytest app/tests -q`: full suite green.
- `ruff check`: clean.

## Review log

- (empty — filled by implementer and reviewer)

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
