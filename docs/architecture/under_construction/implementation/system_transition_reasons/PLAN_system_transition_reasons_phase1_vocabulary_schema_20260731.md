# PLAN_system_transition_reasons_phase1_vocabulary_schema_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase1_vocabulary_schema_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: introduce the code-owned transition vocabulary and add it to the two source-side tables as a
  nullable column, with **nothing reading or writing it**.
- Business/user intent: a purely additive phase that can deploy at any time with zero behaviour
  change, so every later phase has a column to move into without carrying a schema migration of its
  own.
- Non-goals: no writer changes; no reader changes; no backfill; no constraints; no catalog changes.

## Scope

- In scope: `TransitionReasonEnum` in the domain layer; nullable `transition_reason` columns on
  `step_state_records` and `user_shift_state_records`; the additive migration; model-level tests.
- Out of scope: `UserDeclaredStateRecord` (T3 — no column); every call site; `pause_reasons`.
- Assumptions: phase 0 is archived and its inventory recorded.

## Clarifications required

- [ ] Does a worker-chosen step pause need a `WORKER_PAUSED` member at all, or is the catalog
      reference alone sufficient to identify that case? Blocks because the answer decides whether
      `transition_reason` is "system transitions only" (null for worker-chosen pauses) or "every
      transition typed". Cheap to settle now, expensive after writers ship. **Record the ruling and
      its reasoning in the Review log.**

## Acceptance criteria

1. `TransitionReasonEnum` exists in the domain layer alongside the other task-step/user enums,
   following the repo's existing enum conventions (lowercase values — see migration
   `ddc5bf50153b_rename_enum_labels_to_lowercase`). Members at minimum: `SHIFT_ENDED`,
   `OTHER_TASK_PRIORITY`, `WORKER_DECLARED_STATE`, plus whatever the clarification above resolves.
2. `step_state_records.transition_reason` added: **nullable**, indexed, no default, no constraint.
3. `user_shift_state_records.transition_reason` added: same shape.
4. **No column on `user_declared_state_records`** (T3). If the implementer believes T3 is wrong,
   STOP and escalate — do not add it.
5. Migration is additive-only and reversible: `upgrade` adds, `downgrade` drops, no data touched in
   either direction. Verify `upgrade` then `downgrade` then `upgrade` leaves the schema identical.
6. **Zero behaviour change, proven**: no existing test changes, and no existing endpoint response
   gains a field. Serializers must not surface the new column.
7. Column type choice recorded in the Review log with reasoning — native PG enum vs. constrained
   string. Note that this repo has already paid the cost of removing a native enum once
   (`b58cdffb5ccc` dropped `step_event_reason_enum`), which is evidence for the string+check
   approach; state which was chosen and why.
8. Model-level tests: the column accepts every enum member and null; the enum's values match what
   the migration writes.

## Contracts and skills

### Contracts loaded

- `backend/architecture/03_models.md`: model/table conventions.
- `backend/architecture/04_migrations.md`: migration conventions.
- `backend/architecture/01_architecture.md`: layering — the enum belongs in `domain/`, not `models/`.

### File read intent — pattern vs. relational

- Permitted (relational): `step_state_record.py` and `user_shift_state_record.py` for exact field
  names and existing index/constraint shapes; `domain/pause_reasons/enums.py` and
  `domain/task_steps/enums.py` for existing enum conventions; `b58cdffb5ccc` and `ddc5bf50153b` for
  the history of enum handling in this repo.
- Prohibited (pattern): reading unrelated models to learn column-declaration style — `03_models.md`
  covers it.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Resolve the clarification; record the ruling.
2. Add `TransitionReasonEnum` to the domain layer.
3. Add the nullable column to both models with an index.
4. Generate the additive migration; verify it is add/drop only.
5. Model-level tests for accepted values and null.
6. Verify zero behaviour change: full suite shows no new failure nodes; no serializer surfaces the
   column.
7. Review log entry with the clarification ruling and the column-type reasoning. STOP for review.

## Risks and mitigations

- Risk: a native PG enum makes every future member addition a migration, and removing it later is
  costly — this repo has already done that once.
  Mitigation: criterion 7 forces an explicit, recorded choice rather than a default.
- Risk: the additive column is accidentally surfaced by a serializer that reflects model fields.
  Mitigation: criterion 6 requires proving no endpoint response changed.
- Risk: index on a high-volume table locks on deploy.
  Mitigation: size it against phase 0's volume report; if large, use a concurrent index build and
  say so in the Review log.

## Validation plan

- `alembic upgrade head` → `downgrade -1` → `upgrade head`: schema identical, no data lost.
- Full suite: no new failure nodes vs. the recorded baseline (node sets, not counts; see the master
  plan's validation baseline, including the worktree `.env.testing` trap).
- `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
