# SUMMARY_declared_worker_states_phase6_kiosk_flow_20260729

## Metadata

- Summary ID: `SUMMARY_declared_worker_states_phase6_kiosk_flow_20260729`
- Status: `summarized`
- Owner agent: `Opus` (implementation) / `Opus` (independent review) / `claude-fable-5` (lifecycle)
- Created at (UTC): `2026-07-30T15:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase6_kiosk_flow_20260729.md`
- Master plan: `.../under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (Phase 6 of 7)
- Commits: `b0f35b1` (implementation) + `eb8a8c6` (operator rulings/docs)

## What was implemented

- **`clock_in_code` on `user_work_profiles`** — `String(16)`, nullable, with a workspace-scoped
  partial unique index (`(workspace_id, clock_in_code) WHERE clock_in_code IS NOT NULL`), so the same
  code may exist in different workspaces. Migration `67cfba8fcb2d`; upgrade→downgrade→upgrade verified
  in Postgres with the exact partial predicate restored.
- **Assignment through the established admin path** (`update_user_admin`, i.e.
  `PATCH /api/v1/users/{user_client_id}`): trimmed, 4–16 chars, workspace-unique with a friendly
  `409`, `updated_by_id` stamped. `null` clears; `""` is a `422` (operator-accepted: an empty string
  is almost always a UI bug and should fail loudly). `register_user` deliberately untouched — it only
  creates profiles at registration.
- **Floor-scoped roster exposure** — `list_users` merges `clock_in_code` (and, in compact mode,
  `email`) into already-serialized items **only** when `app_scope == "floor"`. The merge happens in
  `list_users`, not in the shared serializers, so the serializers' other consumer is provably
  untouched and the floor conditional exists in exactly one place. Codes come from a single batched
  query over `UserWorkProfile` for the page's ids.
- **Phase 5 R3-1 renames** — the two floor-refresh tests now say what they actually assert
  (floor-scope rejection, not blocklist enforcement); names and docstrings only.

## In-phase repair (operator-accepted, disclosed)

`GET /users?role=` was a **guaranteed 500 for every value and every scope** before this phase:
`Role.name` and `WorkspaceRole.specialization` are disjoint Postgres enums, and each supplied value
was compared against both, so `?role=worker` always died on the specialization leg
(`InvalidTextRepresentationError`). Acceptance 3 and 6 and the handoff §3 roster call the frontend is
built against all depend on that filter, so it was repaired in-phase rather than delivering an
unusable surface: values are split by the enum that can represent them, and an unrecognised role
matches **nothing** (`false()`) rather than everything.

Reviewer verification: reproduced the pre-phase 500 in a baseline worktree for `worker`,
`wood_worker` and nonsense values under both manager and floor scope; post-repair an unknown role
returns `200` with 0 rows; and `pg_enum` labels were compared against the Python split sets — they
match exactly, so no DB label is silently dropped. **The repair is complete, not merely
non-crashing.** Disclosed behavior change: `?role=` goes 500 → working filter for every scope (no
client can have depended on a 500); no serialized item shape changed for any scope.

## Contract adherence

- `03_models.md` / `30_migrations.md`: column + hand-verified partial unique index; single head.
- `07_queries.md`: floor conditional lives in the query, not the domain serializers.
- `28_roles_permissions.md` / `18_security.md`: scope-conditional exposure; a `seller` token is
  rejected at the route entirely by `require_roles`.
- `20_api_versioning.md`: additive-only for floor sessions; absent (not `null`) for all others.

## Validation evidence

- Independent review **APPROVED**. The reviewer did not trust the query-layer tests (which build
  identity dicts by hand) and instead ran a **37-assertion probe through the real ASGI app**
  (`create_app()` + `httpx.ASGITransport`, so middleware and `require_roles` are in the path) with
  tokens minted by `sign_in_user`. Observed at the wire: floor/compact carries `clock_in_code` +
  `email`; manager/worker/admin in compact and full modes have both fields **absent, not null**;
  seller gets `403` at the route.
- **Marginal exposure precisely scoped by the review**: `email` was already in the full shape for
  every scope pre-phase, so the genuinely new exposure is `clock_in_code` (floor) plus compact-mode
  `email` (floor).
- **Four mutation checks re-run by the reviewer**, each failing exactly the claimed test: batching →
  per-user loop; `is_floor_session = True`; dropping the `else false()`; dropping the `updated_by_id`
  stamp. (The batching assertion uses a local SQLAlchemy listener because the shared `count_queries`
  fixture is broken — the reviewer confirmed the assertion is real.)
- Suite parity by node set: HEAD 27 failed / 1318 passed; baseline worktree at `41c507e` 27 failed /
  1280 passed; sorted FAILED-node diff **empty** (+38 = exactly the new tests). Phase 4's pinning
  tests, the shared serializers, both clock commands and the whole Connecteam surface have empty
  diffs. `ruff check` clean on all 12 touched files.

## Known gaps or deferred items

- **R1-1 (low, carried to Phase 7)**: the `IntegrityError → 409` race path in `update_user_admin` has
  no committed test — the pre-check short-circuits every duplicate test — and it depends on an
  index-name string now duplicated in three places, so a future rename would silently degrade the
  race to a `500`. Fix = one assertion pinning the constant to the model's `Index` name (+ ideally a
  single source for it).
- **Q1 deferral cost (recorded by the reviewer, carried to Phase 7)**: a code held by a **deactivated**
  worker stays reserved but is un-findable with no read-back surface, so the `409` is opaque to the
  manager. Mitigation chosen: make the `409` message state that the code is already in use in this
  workspace and may belong to an inactive worker — actionable without leaking identity.
- **R1-4 (informational)**: the implementer's "~10 other consumers" of the shared serializers is
  actually one module; the substantive untouched claim is true and was verified.
- Repo-health: broken shared `count_queries` fixture (recorded in the master baseline).

## Handoff notes

- `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`: §3 liveness row flipped to ✅. Operator
  fixed two review findings in the doc — the row no longer claims a "management surface" the handoff
  never described (§3 now points at `PATCH /api/v1/users/{user_client_id}` and states the floor app
  only *reads* codes), and §8's stale "anti-enumeration identify misses" reference from the dropped
  identify endpoint is gone. §3 also records that there is no code read-back surface.

## Lifecycle transition

- Plan archived to `backend/docs/architecture/archives/implementation/declared_worker_states/`.
- Master plan Phase 6 → `archived`. **Phase 7 (final) is now unblocked.**
