# ARCHIVE_RECORD_PLAN_system_transition_reasons_phase4_retirement_20260731

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_system_transition_reasons_phase4_retirement_20260731`
- Archived at (UTC): `2026-08-01T00:00:00Z`
- Archive owner agent: `claude-opus-5` (on operator direction, post-review)

## Source references

- Plan: `backend/docs/architecture/archives/implementation/system_transition_reasons/PLAN_system_transition_reasons_phase4_retirement_20260731.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_system_transition_reasons_phase4_retirement_20260731.md`
- Master plan: `backend/docs/architecture/under_construction/implementation/system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention: `backend/docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
- Debug chain: `none`

## Outcome classification

- Result: `completed`
- Acceptance criteria: 15 of 16 met with evidence. **Criterion 7 recorded as accepted on substitute
  evidence**, not as met — the two-workspace bootstrap requires a disposable database and a fresh
  `alembic upgrade head` stalls (a recorded repo-health item). The reviewer reproduced the stall,
  exercised the real `seed_pause_reasons` path for two workspaces instead, and recommended
  acceptance.
- Reviews: round 1 `NEEDS_CHANGES` (1 medium, 4 low); round 2 `NEEDS_CHANGES` (documentation only,
  no logic).
- Validation gates: **not waived.** Constraint compliance proven by query before the constraint was
  added; guarded populations byte-identical; rigorous baseline node-set diff by the reviewer
  (27 → 23, zero new nodes); `ruff check` clean on touched files.

## Final notes

- **The feature set's goal is met.** No runtime path resolves a pause reason by slug. Clock-out and
  task switching work in a workspace with an empty catalog, and bootstrapping a second workspace
  succeeds.
- **Two fields were kept that the plan said to remove**, both caught during implementation and both
  breaking the worker app if removed: `slug` and `is_system_managed` are declared required and
  non-nullable in the frontend schema, two lines apart. Phase 1's audit escalated one and missed the
  other. They survive as inert published contract. The distinction that made them blocking — *the
  schema requires it* versus *no code branches on it* — is the transferable lesson.
- **The journal incident is the most valuable thing in this phase's record.** A routine
  `alembic upgrade head` destroyed the 270-row record of what phase 3 rewrote, because being a
  separate revision is not protection when `head` is what people type. Recovery was exact only
  because this database has no post-cutover traffic. The guard
  (`ALLOW_DROP_BACKFILL_JOURNAL=yes`) and the pattern in `architecture/30_migrations.md` outlive it.
- **Criterion 4 stays PARTIAL.** Closed on the provably-dead arm only; 272 legacy strings sit beside
  58 `par_…` ids and the three-way `reason_text` suppression is published contract. Do not upgrade
  it to met.
- **Independence was absent.** The same agent planned, prompted, ruled on and implemented this
  phase. Both review rounds found real defects, one of them a failure of the implementer's own
  protective design.

## Open items at archive time

- **The journal is dropped** (`c8f3d2e60a17` applied deliberately with the acknowledgement,
  logging 270 rows). Phase 3's backfill is now permanently irreversible **on this database**.
- **Nothing is deployed.** Phases 1–4 are applied to the local production *copy* only. The server
  is still on `a7d21f4c8b03`. The deploy order matters: the journal must be alive while phase 3 runs
  there, so `ALLOW_DROP_BACKFILL_JOURNAL` must **not** be set on the run that applies the backfill.
- **The standing deferred-items list** lives in the master plan — T7's `manually_recorded`
  subsumption, two live data-quality issues, the 5 F401s this set inherited, the
  `backfill_worker_shift_state_records.py` declared-rows destruction, and four repo-health items.
