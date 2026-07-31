# PLAN_system_transition_reasons_phase8_historical_backfill_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase8_historical_backfill_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: one-time migration setting `transition_reason` on historical rows that point at a system
  catalog row, and nulling their `pause_reason_id` — so the catalog rows become unreferenced and
  phase 9 can retire them.
- Business/user intent: **T5, retire.** This is the phase that makes one representation true
  everywhere, and the one that can destroy history if wrong.
- Non-goals: retiring the catalog rows (phase 9); constraints (phase 10); worker-chosen pauses,
  whose `pause_reason_id` is correct and must not be touched.

## Scope

- In scope: a data migration over `step_state_records` and `user_shift_state_records`.
- Out of scope: `user_declared_state_records` — every row there is a genuine worker choice with a
  `NOT NULL` catalog reference. **Touching it is a defect.**
- Assumptions: phases 1–7 archived. Phase 0's volume report exists and sizes this work.

## Clarifications required

- [ ] Batched or single-statement? Decided by phase 0's volume report, not by preference. Record the
      figure the decision was made from.
- [ ] Is there a rehearsal database with production-like data? If not, say so plainly — a backfill
      validated only against seeded test data carries materially more risk, and the operator should
      know before it runs.

## Acceptance criteria

1. Rows whose `pause_reason_id` points at `pause_ended_shift` → `transition_reason = SHIFT_ENDED`,
   `pause_reason_id = NULL`.
2. Rows pointing at `pause_other_task_priority` → `OTHER_TASK_PRIORITY`, `pause_reason_id = NULL`.
3. **`pause_case_created` rows** → the member decided here and recorded. This is the soft-deleted
   anchor row that historical data points at (intention Finding 4, corrected). It has no live
   equivalent transition, so it likely needs its own member — decide explicitly, do not fold it into
   another value.
4. Rows pointing at any **worker-chosen** catalog row are **untouched**: `pause_reason_id` intact,
   `transition_reason` still null (or set per phase 1's ruling on `WORKER_PAUSED`).
5. `user_shift_state_records.reason` holding a `par_…` id for a system row is migrated consistently
   with its source rows; free-text legacy values are preserved, not discarded.
6. **Label parity proven** (master-plan success criterion 5): for a sample of rows of every shape,
   the human-visible label after migration equals the label before. Capture before/after from the
   actual read paths, not from the migration's own logic — otherwise the test proves only that the
   migration agrees with itself.
7. `downgrade` restores the previous state, or the migration explicitly documents that it is
   irreversible and why. An undocumented one-way migration is a finding. Note the precedent: the
   custom_pause_reasons feature set shipped migrations whose downgrades did not restore data, and
   that fact blocked testing later.
8. Idempotent: running it twice changes nothing the second time.
9. Zero rows left pointing at a system catalog row afterwards — the query proving it is recorded.
   This is phase 9's entry condition.

## Contracts and skills

### Contracts loaded

- `backend/architecture/04_migrations.md`: migration conventions.
- `backend/architecture/23_documentation.md`: recording the evidence.

### File read intent — pattern vs. relational

- Permitted (relational): `fb10ac7fd439` and `49bd666da846` for how the previous backfill and
  anchor-row logic worked — this migration must not contradict them; phase 0's inventory.
- Prohibited (pattern): reading unrelated migrations for style.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Resolve both clarifications; record the volume figure and the rehearsal-database answer.
2. Decide and record the `pause_case_created` mapping (criterion 3).
3. Write the migration; make it idempotent.
4. Capture before/after labels through the real read paths for a sample of every row shape.
5. Run the zero-remaining-references query; record it.
6. Test `upgrade` → `downgrade` → `upgrade`, or document irreversibility.
7. Review log entry with volumes, label-parity evidence, and the remaining-references query. STOP.

## Risks and mitigations

- Risk: a worker-chosen `pause_reason_id` is nulled, destroying real user data with no way back.
  Mitigation: criterion 4 plus criterion 7's downgrade requirement. The migration must select by
  the three specific system rows, never by `is_system_managed` alone — a mislabelled row would then
  widen the blast radius silently.
- Risk: label parity is "proven" by the migration's own mapping.
  Mitigation: criterion 6 requires capture through the real read paths.
- Risk: validated only against seeded data, then run against production volumes and shapes.
  Mitigation: the second clarification surfaces this to the operator before it runs.

## Validation plan

- Before/after label parity for every row shape.
- Zero rows referencing system catalog rows afterwards.
- Re-run: no further changes (idempotence).
- `upgrade`/`downgrade`/`upgrade` cycle, or documented irreversibility.
- Full suite: no new failure nodes vs. baseline.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
