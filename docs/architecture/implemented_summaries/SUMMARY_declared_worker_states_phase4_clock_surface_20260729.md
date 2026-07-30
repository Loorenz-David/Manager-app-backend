# SUMMARY_declared_worker_states_phase4_clock_surface_20260729

## Metadata

- Summary ID: `SUMMARY_declared_worker_states_phase4_clock_surface_20260729`
- Status: `summarized`
- Owner agent: `Codex` (implementation + fixes) / `Opus` (review ×2, polish) / `claude-fable-5` (lifecycle)
- Created at (UTC): `2026-07-30T12:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase4_clock_surface_20260729.md`
- Master plan: `.../under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (Phase 4 of 7)
- Commits: `20b11c7` (implementation) → `ccdffa9` (R4–R6 fixes) → `be47f4d` (R8/R10 polish)

## What was implemented

- **`POST /worker-shifts/clock-in` / `POST /worker-shifts/clock-out`** — wire the two previously
  orphaned commands. Same role matrix as `/clock` via `resolve_worker_shift_target` (worker = self;
  admin/manager must name a worker). `clock_out_at` is **not** exposed over HTTP.
- **`GET /worker-shifts/current`** — read-only shift snapshot (zero `with_for_update`):
  `clocked_in`, `shift_started_at` (from the latest `STARTED_SHIFT` marker, distinct from
  `state_entered_at`), `state`, `pause_reason`, and the open `declared_state`. Access matrix
  mirrors the clock actions; five state scenarios covered.
- **`analytics: null` envelope** on both clock-out paths (`/clock-out` and the `/clock` toggle's
  clock-out branch only; clock-in never carries the key) — moved into this phase by operator ruling
  2026-07-30 so the handoff is exact from endpoint go-live. Phase 7 populates it.
- **Pause-reasons `pause_type` filter** — already existed; this phase was conformance-only, and the
  handoff's §7 shape was corrected to the endpoint's real paginated envelope.
- **Shared access helper** extracted so the read path reuses the writer's role/membership rules
  without locking; the commands module re-exports it so all five writer call sites are unchanged.

## Fixes and polish applied in review

- **R4** — `clock_out_at` removed from `ClockOutWorkerShiftRequest` entirely (the route model
  dropping extras was the only guard before); the command now uses server UTC unconditionally.
  Verified: the HTTP route is the command's only caller; the `clock_out_shift_for_user` helper and
  `services/tasks/` are untouched, so the midnight safeguard keeps passing its own 00:00.
- **R5** — an unresolvable `par_…` reason now yields `pause_reason: null` **and**
  `reason_text: null`. The reviewer established this closed a **real cross-tenant identifier leak**:
  the reason join is workspace-scoped, so an unresolvable id was by definition foreign and was
  previously shipped to the client.
- **R6** — `GET /current` 404 branch covered at query (`NotFound`) and router (envelope) layers.
- **R8** — the shared helper was relocated from the top level of `services/` (reserved for
  framework primitives) to `services/queries/users/worker_shift_access.py`. **Not** `services/infra/`:
  `architecture/01_architecture.md:43` forbids `services/queries/` from importing `services/infra/`,
  so the operator's original suggestion would have created a harder violation. `git mv` recorded a
  pure rename, keeping the function blob-identical as the reviewer required.
- **R9** — handoff documents `reason_text`'s three-way variance (absent / string / `null`).
- **R10** — a WARNING is now emitted on the unresolvable-reason branch (workspace, user, record,
  unresolved id) per `17_logging.md`. **Judgment call recorded:** the log lives in the query, not the
  serializer where the branch sits, because `01_architecture.md:43` bars `domain/` from any I/O —
  logging in the serializer would have traded R8's layering fix for a fresh violation of the same
  contract. To stop the two sites drifting, the predicate is named once in the domain layer
  (`pause_reason_reference_is_unresolved`, pure) and shared by the serializer ternary and the
  warning; inside the serializer's guard it reduces to the original `startswith`, so R5's behavior
  is unchanged.

## Contract adherence

- `07_queries.md` / `09_routers.md` / `46_serialization.md`: query-service + thin-route + serializer
  conventions.
- `01_architecture.md`: layering respected at both R8 (placement) and R10 (no I/O in `domain/`).
- `28_roles_permissions.md`: single `resolve_worker_shift_target` implementation, no reimplementation.
- `D8`: Connecteam handlers, webhook pipeline and the midnight safeguard untouched — verified
  per-commit by the reviewer.

## Validation evidence

- Independent review round 2: **APPROVED** at `ccdffa9`. The reviewer proved the helper extraction
  byte-identical by **git blob identity** (new file created with the old module's pre-image blob),
  confirmed all five writers still import through the shim, and noted `.one_or_none()` cannot fan
  out because both tables carry partial unique indexes on `(user_id, workspace_id) WHERE exited_at
  IS NULL`.
- Polish verification (`be47f4d`): tests written first and confirmed red on the unresolvable path;
  39 focused tests green; quiet-tree full suite compared against HEAD in a throwaway worktree with
  **empty FAILED-node diff**.
- Operator quiet-tree measurement after both commits: **27 failed / 1280 passed**, baseline node set
  only. Two concurrent-session runs reported 313 and 321 failures respectively — both artifacts of
  the shared test DB/Redis, per the master plan's canonical-baseline rule.
- ruff `check` clean on all touched files (repo-wide 133, below baseline).

## Known gaps or deferred items

- `ruff format --check` drift on three touched files is pre-existing (verified at HEAD); the repo
  gate is `ruff check`.
- The relocated module's basename has no leading underscore (the commands-side shim owns that
  basename). Cosmetic; placement — R8's substance — is as verified.
- Baseline repo-health items unchanged (see master plan's baseline section).

## Handoff notes

- `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`: §4/§5/§7 verified field-for-field
  including enum wire values and the `+00:00` offset. Phase 4 liveness row flipped to ✅ at
  finalization; `reason_text` three-way variance documented in §4.

## Lifecycle transition

- Plan archived to `backend/docs/architecture/archives/implementation/declared_worker_states/`.
- Master plan Phase 4 → `archived`. Phase 6 now blocked only on Phase 5.
