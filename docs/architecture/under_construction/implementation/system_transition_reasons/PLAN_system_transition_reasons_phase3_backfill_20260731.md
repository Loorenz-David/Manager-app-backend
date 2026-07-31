# PLAN_system_transition_reasons_phase3_backfill_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase3_backfill_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: one-time migration setting `transition_reason` on historical rows that point at a system
  catalog row, and nulling their `pause_reason_id`, so those catalog rows become unreferenced and
  phase 4 can retire them.
- Business/user intent: **T5, retire.** This is the phase that makes one representation true
  everywhere — and the one phase in this set that can destroy real history if it is wrong.
- Non-goals: retiring the catalog rows (phase 4); constraints (phase 4); worker-chosen pauses, whose
  `pause_reason_id` is correct and must not be touched.

## Scope

- In scope: a data migration over `step_state_records` and `user_shift_state_records`.
- Out of scope: `user_declared_state_records` — every row there is a genuine worker choice with a
  `NOT NULL` catalog reference. **Touching it is a defect.**
- Assumptions: phases 1–2 archived. Phase 1's volume report and label-resolution strings exist.

## Clarifications required

- [ ] **Batched or single-statement?** Decided by phase 1's volume report, not by preference.
      Record the figure the decision was made from.
- [ ] **Is there a rehearsal database with production-like data?** If not, say so plainly — a
      backfill validated only against seeded test data carries materially more risk, and the
      operator should know that before it runs, not after.
- [ ] **What member do `pause_case_created` rows map to?** It is the soft-deleted anchor row that
      historical data points at (intention Finding 4). It has no live equivalent transition, so it
      likely needs its own member. **Decide explicitly; do not fold it into another value.**

## Acceptance criteria

1. Rows whose `pause_reason_id` points at `pause_ended_shift` → `transition_reason = SHIFT_ENDED`,
   `pause_reason_id = NULL`.
2. Rows pointing at `pause_other_task_priority` → `OTHER_TASK_PRIORITY`, `pause_reason_id = NULL`.
3. `pause_case_created` rows → the member decided in the clarification, recorded with reasoning.
4. **Rows pointing at a worker-chosen catalog row are untouched**: `pause_reason_id` intact,
   `transition_reason` as phase 1's `WORKER_PAUSED` ruling determined.
5. **The migration selects by the three specific system rows — never by `is_system_managed` alone.**
   A single mislabelled row would otherwise silently widen the blast radius to real worker choices.
   This is the most important line in this plan.
6. `user_shift_state_records.reason` holding a `par_…` id for a system row is migrated consistently
   with its source rows; free-text legacy values are **preserved, not discarded**.
7. **Label parity proven** (master-plan success criterion 5): for a sample of rows of every shape,
   the human-visible label after migration equals the label before. Capture before/after **through
   the real read paths**, not from the migration's own logic — otherwise the test proves only that
   the migration agrees with itself.
8. `downgrade` restores the previous state, or the migration explicitly documents that it is
   irreversible and why. An undocumented one-way migration is a finding. Precedent: the
   custom_pause_reasons feature set shipped migrations whose downgrades did not restore data, and
   that fact later blocked testing entirely.
9. **Idempotent** — running it twice changes nothing the second time.
10. **Zero rows left pointing at a system catalog row afterwards.** Record the query proving it —
    this is phase 4's entry condition.

## Contracts and skills

### Contracts loaded

- `backend/architecture/04_migrations.md`: migration conventions.
- `backend/architecture/23_documentation.md`: recording evidence.

### File read intent — pattern vs. relational

- Permitted (relational): migrations `fb10ac7fd439` and `49bd666da846` for how the previous backfill
  and anchor-row logic worked — this migration must not contradict them; phase 1's inventory
  section.
- Prohibited (pattern): reading unrelated migrations for style.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Resolve all three clarifications. Record the volume figure, the rehearsal-database answer, and
   the `pause_case_created` mapping with reasoning.
2. Write the migration. Select by the three specific rows (criterion 5). Make it idempotent.
3. Capture before/after labels through the real read paths for a sample of every row shape.
4. Run the zero-remaining-references query; record it verbatim.
5. Test `upgrade` → `downgrade` → `upgrade`, or document irreversibility with reasoning.
6. Review log entry with volumes, label-parity evidence, and the remaining-references query. STOP.

## Risks and mitigations

- Risk: a worker-chosen `pause_reason_id` is nulled, destroying real user data with no way back.
  Mitigation: criteria 4, 5 and 8. Selecting by the three specific rows rather than by
  `is_system_managed` is what bounds the blast radius.
- Risk: label parity is "proven" by the migration's own mapping.
  Mitigation: criterion 7 requires capture through the real read paths.
- Risk: validated only against seeded data, then run against production volumes and shapes.
  Mitigation: the rehearsal-database clarification surfaces this to the operator **before** it runs.
- Risk: the `pause_case_created` anchor is corrupted, breaking historical labels that nothing else
  can reconstruct.
  Mitigation: criterion 3 forces an explicit decision; criterion 7 proves the labels still resolve.

## Validation plan

- Before/after label parity for every row shape, captured through real read paths.
- Zero rows referencing system catalog rows afterwards.
- Re-run: no further changes (idempotence).
- `upgrade` → `downgrade` → `upgrade`, or documented irreversibility.
- Full suite: no new failure nodes vs. baseline (node sets, not counts).
- `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
