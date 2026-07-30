# PLAN_declared_worker_states_phase6_kiosk_flow_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase6_kiosk_flow_20260729`
- Status: `under_construction`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-30T12:45:00Z` (implementer Review-log entry; status intentionally unchanged pending review)
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
  5. Final handoff conformance: verify the full implemented surface against `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` and record the evidence in the Review log. **(operator-owned, ruling 2026-07-30)** the handoff liveness row is flipped by the OPERATOR after the reviewer approves — an implementer must never flip it. This phase's deliverable is conformance evidence in the Review log, not the doc edit.
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
- [x] **Carried from the Phase 5 review (R3-1, trivial — include in this phase):** two floor-refresh
  tests (`tests/unit/test_auth_router.py:201`, `tests/unit/services/commands/auth/test_refresh_token.py:110`)
  have names implying blocklist coverage, but the floor-scope guard fires before the blocklist read
  (proven: `BLOCKLIST READER CALLS: []` while passing). **Rename them to state what they actually
  assert** (floor-scope rejection, not blocklist enforcement). Naming only — do not change assertions
  or production code. Also relevant here because this phase introduces the first `require_app_scope`
  usage (Phase 5 finding N7).

## Acceptance criteria

1. Migration: column + partial unique index apply/downgrade cleanly; duplicate code in one workspace → `IntegrityError` at DB level; same code across workspaces OK.
2. Code management: admin sets/clears a worker's code through the established update path; duplicate in workspace → friendly `409`; `updated_by_id` stamped; length/trim validation enforced.
3. Roster exposure matrix: floor-scope session calling `GET /users?role=worker&compact=true` → every item carries `clock_in_code` (value or `null`) and `email`; full (non-compact) mode likewise; `manager`/`worker`/`admin`/`seller`-scope sessions → fields **absent** and response byte-identical to pre-phase behavior (existing list_users tests unmodified and green).
4. Code fetch is batched (one query for the page) — no per-user query; asserted via query-count or code inspection recorded in the Review log.
5. Regression only (envelope delivered by Phase 4, ruling 2026-07-30): both clock-out routes still carry `"analytics": null`; Phase 4's pinning tests unmodified and green.
6. Full-loop kiosk test: floor sign-in (Phase 5) → `GET /users?role=worker&compact=true` returns the worker with their code → `GET /current` (not clocked in) → `/clock-in` on-behalf → `GET /current` (idle) → declare on-behalf → `GET /current` (declared) → `/clock-out` → response has `analytics: null` and correct `transitioned_steps`.
7. Handoff conformance: every endpoint/shape in `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` matches the implementation (evidence in the Review log). **(operator-owned, ruling 2026-07-30)** the handoff liveness row is flipped by the OPERATOR after the reviewer approves — an implementer must never flip it. This phase's deliverable is conformance evidence in the Review log, not the doc edit.
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
7. Handoff conformance pass; record evidence in the Review log (liveness flip = operator, post-approval).

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

### Implementer entry — 2026-07-30 (Codex)

**Prerequisite check (protocol step 4):** master plan phase table shows Phases 3, 4 **and** 5
`archived` ✅ (rows 60–62). Cleared to proceed.

**Verify-first outcomes (protocol step 6):**

- (a) **Work-profile write path** = `services/commands/users/update_user_admin.py` (the admin PATCH
  `/users/{user_client_id}`). `register_user.py` also creates the row but only at registration; the
  plan's acceptance 2 speaks of an *update* path with `updated_by_id` stamping, so `clock_in_code`
  was added to `update_user_admin` only. Registration-time code assignment was NOT added (not in
  acceptance 2, not in the handoff) — flagged as Q1 below.
- (b) **`email` in the list_users shapes:** already present in the **full** shape
  (`serialize_user_list_item`, `domain/users/serializers.py:55`); **absent** from the **compact**
  shape (`serialize_user_compact_with_role`). So compact gains `clock_in_code` + `email`, full gains
  `clock_in_code` only. Both are asserted in the exposure-matrix tests.

**Implementation (7 production files, 4 new test files):**

| File | Change |
|---|---|
| `models/tables/users/user_work_profile.py` | `clock_in_code` `String(16)` nullable + partial unique index `uix_user_work_profiles_workspace_clock_code` (`WHERE clock_in_code IS NOT NULL`) |
| `migrations/versions/67cfba8fcb2d_…py` | autogenerated column + partial index (see O4 for the trim) |
| `models/tables/users/README.md` | snapshot-rule exemption + code semantics ("identifies, does not authenticate") |
| `services/commands/users/requests/update_user_admin_request.py` | `clock_in_code` field + trim/4–16 validator |
| `services/commands/users/update_user_admin.py` | `_assign_clock_in_code` (workspace-unique pre-check → friendly 409, `IntegrityError` translation for the race), `updated_by_id` stamp on work-profile updates |
| `routers/api_v1/users.py` | `clock_in_code` on `UpdateUserAdminBody` |
| `services/queries/users/list_users.py` | floor-scope-conditional `clock_in_code`/`email`, one batched code query, `?role=` enum-leg repair (P1) |

The floor fields are merged into **already-serialized items** inside `list_users`, not into the
shared serializers — so every other consumer of `serialize_user_compact_with_role` /
`serialize_user_list_item` (tasks, shopify, notifications, working sections, cases…) is provably
untouched, and the floor conditional exists in exactly one place.

**Acceptance criteria — evidence**

| # | Criterion | Evidence |
|---|---|---|
| 1 | Migration + partial index | `alembic upgrade head` → `downgrade -1` → `upgrade head` all clean; `alembic current` = `67cfba8fcb2d (head)`, single head. `tests/integration/models/users/test_user_work_profile_clock_in_code.py` (3 tests): duplicate in one workspace → `IntegrityError` naming the index; same code in two workspaces → OK; two NULLs in one workspace → OK (partiality). |
| 2 | Code management | `tests/integration/services/commands/users/test_update_user_admin_clock_in_code.py` (10 tests): set→clear round trip, trim, profile auto-create, duplicate → `ConflictError` (`http_status == 409`, exact message), own-code reassign is not a conflict, length matrix `["abc","   x   ","",("x"*17)]` → 422, salary-only update leaves the code intact. `updated_by_id == actor` asserted on update; `None` right after creation (README rule). |
| 3 | Roster exposure matrix | `tests/integration/services/queries/users/test_list_users_floor_identification.py` (22 tests). Floor × {compact, full}: exact key set = pre-phase key set ∪ `{clock_in_code, email}`, for a worker with a code, without a code, and **with no work-profile row at all**. Non-floor × {manager, worker, admin, seller, *claim absent*} × {compact, full}: exact pre-phase key set, `clock_in_code` **not in** item (absent, not null), `email` absent in compact. Plus a direct equality pin: floor item minus the two fields **==** manager item. Pagination envelope keys unchanged. |
| 4 | Batched code fetch | Same file: with 4 workers on the page, exactly **one** executed statement mentions `user_work_profiles`; non-floor page issues **zero**. Measured with a local SQL listener (see O3). |
| 5 | `analytics: null` regression | Phase 4's pinning tests left **unmodified** and green: `tests/unit/test_worker_shifts_router.py::test_clock_routes_preserve_analytics_null_contract_by_action` (both routes, both branches), `test_worker_shift_commands.py::test_clock_toggle_clocks_in_then_out` (lines 1001–1004), `::test_manager_can_clock_worker_on_behalf_and_worker_cannot_clock_peer` (line 1102), `::test_clock_out_transitions_working_steps_and_leaves_paused_steps_open` (line 1154 — pre-existing baseline failure, see below). `git diff` on those files is empty. |
| 6 | Full-loop kiosk test | `tests/integration/services/commands/users/test_kiosk_floor_flow.py` — **written first**, verified failing for the right reason before implementation (`TypeError: 'clock_in_code' is an invalid keyword argument for UserWorkProfile`). Real floor sign-in through `sign_in_user` (asserts `app_scope == "floor"`, **no `exp`**, no refresh token) → roster poll returns the worker matched **by code** → `GET /current` exact not-clocked-in shape → on-behalf `/clock-in` → `GET /current` = `idle` → on-behalf declare → `paused_steps == 1` (auto-pause) → `GET /current` = `in_pause` + `declared_state` → `/clock-out` = `{action, user_id, transitioned_steps: 0, analytics: None}` → `GET /current` clocked out. Mock-free (it selects a workspace whose system `pause_ended_shift` reason is configured). Two companions: `transitioned_steps == 1` when a working step is open at clock-out, and email-fallback matching with `clock_in_code = NULL`. |
| 7 | Handoff conformance | Verified **through the router function** `users_router.list_users_route` under a real floor JWT, using the handoff's literal call `?role=worker&compact=true&limit=200`: `200`, envelope `['data','ok','warnings']`, `clock_in_code == "4821"`, `email` matches the user, all handoff §3 keys present, and the same call under a `manager` claim leaks neither field. §4/§5/§5.1/§6 shapes asserted in the kiosk test (incl. `analytics: null`); §8 `409` mapping asserted via `ConflictError.http_status`. Liveness table **not** touched — operator's post-approval step. |
| 8 | Suite + ruff | Full suite **27 failed / 1318 passed**; clean-tree baseline (same machine, quiet tree, `git stash`) **27 failed / 1280 passed**. Failure **node sets are byte-identical** (`diff` → no lines). +38 passed = the 38 new tests. `ruff check` clean on all 12 touched files. |

**P1 — blocker found and repaired: `?role=` on `GET /users` was a guaranteed 500.**
`Role.name` (`role_name_enum`: admin/worker/manager/seller) and `WorkspaceRole.specialization`
(`workspace_role_specialization_enum`: wood_worker/upholstery_worker/quality_control) are **disjoint**
Postgres enums, and the filter compared **both** against every supplied name. Any value therefore hit
`InvalidTextRepresentationError` on one leg — `?role=worker` crashed on the specialization leg,
`?role=wood_worker` on the role leg. Proven pre-existing and unrelated to this phase: a
**`manager`-scope** call (floor code path never entered) crashes identically on the clean stashed tree.
This made acceptance 3 and 6 — and the handoff §3 roster call the frontend is built against —
unachievable, so it was repaired in-phase: each leg now receives only names that are members of its
own enum, and an unrecognised name matches nothing (`false()`) rather than everything. Four tests
cover it; mutation-reverting the filter fails all 22 tests in the file.
**Reviewer, note the caveat:** the "byte-identical non-floor response" guarantee holds for the
serialized **item shape** (pinned per scope and mode). It does **not** hold for `?role=` calls, which
change from a 500 to a working filter **for every scope** — an intentional, disclosed behaviour
change. If the operator prefers this split out into its own repo-health plan, the two commits are
separable: the filter repair touches only the `if role_filter:` block plus its two constants.

**Mutation checks (all reverted; each proves the assertion is load-bearing)**

| Mutation | Result |
|---|---|
| Batched code fetch → per-user loop | 1 failed (the batching test) |
| `is_floor_session` → always `True` | 13 failed (non-floor matrix) |
| Drop the uniqueness pre-check | 10 passed — the `IntegrityError`→409 fallback carries the same message unaided |
| Drop the `updated_by_id` stamp | 1 failed |
| Restore the original both-legs role filter | 22 failed |

**Observations / open items for the reviewer**

- **O1 (doc completeness, not a deviation):** handoff §3's example item omits `workspace_role`, which
  the compact shape has carried since before this phase. Every key the handoff promises is present
  with the promised semantics; the example is a subset. No implementation change made.
- **O2 (baseline):** the one failing node in the plan's targeted `-k` selection,
  `test_worker_shift_commands.py::test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`,
  is a **pre-existing** baseline failure (`System pause reason 'pause_ended_shift' is not configured`
  — the test seeds into a workspace that has no system reasons). Confirmed by running it on the clean
  stashed tree. This is one of the two clock-out baseline failures the master plan warns about; not
  repaired here (scope discipline).
- **O3 (baseline):** the shared `count_queries` fixture in `tests/conftest.py` raises on first use —
  its `async_engine` dependency is **session-scoped** and resolves before the function-scoped
  autouse `init_db()` creates the engine (`AttributeError: 'NoneType' object has no attribute
  'sync_engine'`). It has no other consumers in the suite. I did not touch shared `conftest.py`
  (it also carries a pre-existing ruff F401) and used an equivalent local listener instead.
- **O4 (migration hygiene):** `--autogenerate` swept in unrelated pre-existing schema drift — a
  `DROP CONSTRAINT email_sync_states_connection_id_key` and two `DROP INDEX` on
  `step_state_records`. Those were **removed** from the generated file (acting on them would be
  destructive and out of scope); a comment in the migration records why. Only the column + partial
  index remain.
- **O5 (validation decision):** `clock_in_code: null` clears the code; `""` / whitespace-only is a
  **422**, not a silent clear — the plan's rule is "trimmed, 4–16 chars", and a second clearing
  channel would be invented requirement. Pinned by the length matrix test. Veto-able.
- **Q1 (question for the operator, non-blocking):** there is currently **no read-back surface** for
  an assigned code. `serialize_user_work_profile` was deliberately left unchanged, because D13's
  parenthetical says regular manager sessions "never receive codes" and no acceptance criterion or
  handoff section asks for it. Consequence: a manager who assigns a code knows it (they sent it), but
  a *different* manager device cannot read an existing code back — only a floor session can. If codes
  should be visible on the admin detail endpoint (`GET /users/{id}`), that is a one-line additive
  change to `serialize_user_work_profile`, and the handoff should say so first.

**Lifecycle:** implementation + validation complete. **STOPPING for independent review.** No
implemented summary written, plan not archived, master phase table not flipped, handoff liveness
table not edited — per the review-first gate in the phase prompt.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
