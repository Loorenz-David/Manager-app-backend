# ARCHIVE_RECORD_PLAN_system_transition_reasons_phase3_backfill_20260731

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_system_transition_reasons_phase3_backfill_20260731`
- Archived at (UTC): `2026-07-31T21:00:00Z`
- Archive owner agent: `claude-opus-5` (on operator direction, post-review)

## Source references

- Plan: `backend/docs/architecture/archives/implementation/system_transition_reasons/PLAN_system_transition_reasons_phase3_backfill_20260731.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_system_transition_reasons_phase3_backfill_20260731.md`
- Master plan (intention role): `backend/docs/architecture/under_construction/implementation/system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention: `backend/docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
- Debug chain: `none`

## Outcome classification

- Result: `completed`
- Acceptance criteria: all 10 met with evidence. APPROVED at round 2, after `NEEDS_CHANGES` at
  round 1 (3 findings — one medium, two low, **none in the SQL**).
- Validation gates: **not waived.** Rehearsal run end to end with figures attributed to restore
  points; idempotence and byte-exact `downgrade` proven; suite node sets unchanged; `ruff check`
  clean on touched files. The pre-existing repository baseline was neither absorbed nor repaired
  (T8).

## Final notes

- **270 rows rewritten**, single statement, selected through the `pause_other_task_priority` slug
  alone. Two populations were deliberately excluded and proven byte-identical before and after:
  `pause_ended_shift` (169 rows — worker picks and clock-out writes are historically
  indistinguishable) and `pause_case_created` (7 rows — stale value, no member minted, resolving
  through the soft-deleted anchor).
- **The review demonstrated why the narrow predicate mattered.** The reviewer's `ended_shift` count
  was 169 against the recorded 153, the difference being cross-workspace suite residue carrying
  `is_system_managed = true`. A flag-based predicate would have swept all 169 — relabelling real
  worker choices as system transitions, irreversibly.
- **The medium finding was not in the migration.** `transition_reason_backfill_journal` — the record
  that makes this migration reversible — was invisible to `alembic revision --autogenerate`, which
  would have emitted `op.drop_table` on it inside some unrelated future revision. Fixed with an
  `include_object` filter on both configure paths keyed on a reserved `_journal` suffix, verified
  both ways with a no-suffix control. The convention now lives in `architecture/30_migrations.md`,
  independent of the journal itself.
- **Two corrections to stated reasoning, not to behaviour.** The prove-dead argument's FK premise was
  wrong for `user_shift_state_records.reason`, which has no FK — the operator's own review prompt
  carried the same error. And criterion 4 in the intention is now recorded as an **explicit partial
  completion**, closed on the provably-dead arm only.

## Open items at archive time

- **The journal is still present**, by design. Phase 4 owns verifying it intact, dropping it **last**,
  and recording the row count it held. Default if unclear: **keep it.** Dropping it is what makes
  this migration permanently irreversible.
- **Criterion 4 remains a partial completion.** Phase 4 must not upgrade it to fully met — 272 legacy
  strings still sit beside 58 `par_…` ids and nothing in the remaining work changes that.
- **Recorded deviation:** the rehearsal's restore point is a local dump of the `.env` database rather
  than a freshly pulled copy; a fresh pull requires an SSH tunnel through the production bastion,
  which the implementer did not run autonomously.
