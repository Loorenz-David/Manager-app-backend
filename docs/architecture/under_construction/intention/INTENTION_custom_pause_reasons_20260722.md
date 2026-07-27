# INTENTION_custom_pause_reasons_20260722

## Goal

Replace the static `StepEventReasonEnum` (`app/beyo_manager/domain/task_steps/enums.py`) with a
database-backed, user-managed `pause_reasons` table, so the workspace can define, edit, and retire
its own pause reasons instead of relying on a fixed code enum that requires a deploy to change.

## Why

- Pause reasons today are hardcoded (`WAITING_FOR_UPHOLSTERY`, `PAUSE_LUNCH_BREAK`,
  `PAUSE_COFFEE_BREAK`, `PAUSE_ENDED_SHIFT`, `PAUSE_CASE_CREATED`, `PAUSE_MEETING`,
  `PAUSE_OTHER_TASK_PRIORITY`). Adding, renaming, or retiring a reason currently requires a code
  change, a migration to the Postgres enum type, and a deploy.
- The business wants pause reasons to be workspace-configurable data: a name, an optional image,
  a type (personal vs. blocker-for-other-work), a description, and a flag that forces the worker
  to type a free-text reason when that pause reason is selected.
- Two of the seven current values are not worker-selected — they are assigned automatically by
  backend logic (`PAUSE_OTHER_TASK_PRIORITY` on auto-pause-on-conflict,
  `PAUSE_ENDED_SHIFT` on clock-out). The new system must keep those automatic paths working
  without hardcoding a table row's opaque `client_id` in application code.

## Outcome wanted

- A `pause_reasons` table with full CRUD (`GET`/`PUT`/`PATCH`/`DELETE`, matching this repo's
  existing create-via-PUT, update-via-PATCH convention) that the frontend can use to render
  pause-reason pickers and an admin management screen.
- `StepStateRecord` (and every code path that currently assigns a `StepEventReasonEnum` member)
  migrated to reference a `pause_reasons` row instead of an enum member, with existing historical
  data backfilled so nothing breaks.
- The two system-triggered reasons remain protected (cannot be deleted, resolved by a stable
  internal identifier) while the rest become fully user-editable/deletable like any other
  workspace reference data.

## Status

Implemented, summarized, and archived through one gated Phase A/Phase B delivery cycle. The repository-wide
test run still contains unrelated dirty-tree failures documented in the implementation summary.

## Linked implementation plans

| Plan | Status | Summary | Frontend handoffs |
|---|---|---|---|
| `PLAN_custom_pause_reasons_20260722` | archived | `docs/architecture/implemented_summaries/SUMMARY_PLAN_custom_pause_reasons_20260722.md` | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_pause_reasons_crud_20260722.md`; `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_pause_reasons_analytics_breakdown_20260722.md`; `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_pause_reasons_step_transition_contract_20260722.md` |

## Progress notes

- Phase A: `pause_reasons` domain, schema, bootstrap seed, CRUD, router, realtime events, and CRUD
  handoff completed and validated.
- Phase B: nullable FK/backfill and separate enum cleanup migrations completed; automatic system
  reason lookup, frontend transition validation, serializers, shift reconstruction, backfill, and
  analytics consumers now use `pause_reason_id`.
- ~~Operational release gate: deploy Phase A, manually invoke secret-gated bootstrap in existing
  environments and verify the seven slugs/idempotency, then deploy Stage 7 and validate its
  reconciliation before Stage 8 cleanup.~~ Superseded below — this manual gate is no longer
  required.
- Post-archive correction (2026-07-22): added migration `49bd666da846_seed_default_pause_reasons`
  between the table-creation migration (`ad5da5b32355`) and the FK/backfill migration
  (`fb10ac7fd439`, re-pointed to it), so `alembic upgrade head` alone seeds the 7 default
  `pause_reasons` rows — no manual `POST /api/v1/bootstrap` call needed before the backfill runs.
  The bootstrap `seed_pause_reasons` phase is unchanged and stays a harmless idempotent no-op
  wherever the migration already ran (`ON CONFLICT (slug) DO NOTHING` vs. the phase's own by-slug
  guard — whichever runs first wins). **Not yet validated end-to-end**: the shared dev database
  this was written against is already at `head` with real data (132 workspaces, 3472
  `step_state_records`, 348 already carrying a `pause_reason_id`), so downgrading it to test the
  new migration in place would have destroyed that backfill (Stage 8's downgrade doesn't restore
  `reason`, Stage 7's downgrade drops `pause_reason_id` outright) — deliberately not done. Needs a
  disposable database (or a fresh environment) to confirm `alembic upgrade head` from scratch
  actually seeds correctly before this is trusted for a real deploy.
- Post-archive corrections (2026-07-22, found during review): fixed missing FK indexes on
  `PauseReason.updated_by_id`/`deleted_by_id`, the `models/__init__.py` registration-comment
  convention, and a missing `credited_user_id` on `transition_step_state.py`'s auto-pause record.
  Fixed a silent breaking change in `GET /api/v1/worker-stats/linear-timeline` (`pause_by_reason`
  keys had gone opaque with no lookup map, unlike the drill-down breakdown endpoint) by adding the
  same `pause_reasons` map there, with a new regression test. Wrote the missing
  `HANDOFF_TO_FRONTEND_pause_reasons_step_transition_contract_20260722.md` — the `reason` →
  `pause_reason_id` rename on the step-transition endpoints (`POST .../transition` and
  `.../transition-batch`) had shipped with no frontend handoff at all. Still open: a pre-existing
  `NameError` in `_step_transition_core.py` (missing `select` import, predates this feature) that
  crashes the auto-pause-on-conflict path, and several test-coverage gaps flagged during review.
