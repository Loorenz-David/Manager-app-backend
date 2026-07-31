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
- [x] **Is there a rehearsal database with production-like data?** *Resolved 2026-07-31
      (operator): **yes.*** The `.env` database
      (`postgresql+asyncpg://postgres:postgres@localhost:5433/beyo_manager`) is a dockerised exact
      copy of the current server database, re-downloadable and replaceable on demand.

      **Use it, and use the restorability.** The rehearsal protocol is a deliverable of this phase,
      not an optional extra:

      1. Restore a fresh copy and record the restore point.
      2. Capture "before" labels through the **real read paths** for a sample of every row shape.
      3. Run the migration.
      4. Capture "after" labels the same way; diff them (criterion 7).
      5. Run the zero-remaining-references query (criterion 10).
      6. Restore again, and confirm the restored state matches the recorded restore point.

      Step 6 is what makes the rest trustworthy — a rehearsal that cannot be repeated from a known
      state is an anecdote. Record every figure with which restore it came from.

      **One qualification** (phase 1's F2 finding still stands): the suite also runs against this
      database, so **globals carry accumulated test residue while workspace-scoped figures
      reproduce.** Scope every count; do not size the migration from a global.
- [x] **What member do `pause_case_created` rows map to?** *Resolved 2026-07-31 (operator):
      **none. Leave those rows untouched.***

      The value is stale and carries no real meaning — it was dropped from the live default set and
      survives only as a soft-deleted anchor row that 7 historical rows point at. Minting a
      vocabulary member for it would encode a dead concept into a code-owned enum that then
      outlives the data it describes.

      Leaving them costs nothing and is safer than any alternative:

      - They keep resolving through the anchor to their existing label, so **success criterion 5
        holds by construction** rather than by a migration that has to reproduce it.
      - They carry `pause_reason_id` with `transition_reason` null, so **phase 4's mutual-exclusion
        constraint is unaffected**.
      - The anchor is already soft-deleted and already invisible to `list_pause_reasons`, so nothing
        can select it and the population cannot grow.

      **This is the second population phase 3 no longer touches** (after `pause_ended_shift`).
      Scope is now a single population: rows pointing at `pause_other_task_priority`. Size the work
      accordingly — this is a much smaller migration than this plan originally described.

## Acceptance criteria

1. **Rows pointing at `pause_ended_shift` are LEFT ALONE.** *(Amended 2026-07-31, operator ruling.)*

   Phase 4 no longer retires that row — it stays worker-selectable — so its historical references
   need no migration at all. More importantly, they **must not** be migrated: a worker who picked
   "Ended shift" from the pause sheet produced a row **indistinguishable** from one the clock-out
   wrote (both `state = ended_shift`, both `pause_reason_id = par_…pause_ended_shift`, both
   `transition_reason` null). Backfilling them wholesale would relabel real worker choices as system
   transitions.

   Leaving them costs nothing: the catalog row still exists, so they still resolve, and they carry
   no `transition_reason`, so phase 4's constraint is unaffected. **If you can find a signal that
   distinguishes the two populations, report it — do not act on it.** That is a separate decision.
2. Rows pointing at `pause_other_task_priority` → `OTHER_TASK_PRIORITY`, `pause_reason_id = NULL`.
3. **Rows pointing at `pause_case_created` are LEFT ALONE**, per the clarification. No member is
   added for it. Assert they are unchanged after the migration — this is a real assertion, not a
   note: a `WHERE pause_reason_id = <anchor>` count identical before and after.
4. **Rows pointing at a worker-chosen catalog row are untouched**: `pause_reason_id` intact,
   `transition_reason` as phase 1's `WORKER_PAUSED` ruling determined.
5. **The migration selects by `pause_other_task_priority` alone — never by `is_system_managed`, and
   never including `pause_ended_shift` or `pause_case_created`.**
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
10. **Zero rows left pointing at `pause_other_task_priority` afterwards.** Record the query proving
    it — this is phase 4's entry condition. Rows pointing at `pause_ended_shift` and
    `pause_case_created` are expected to remain and are **not** counted.

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
