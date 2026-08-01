# SUMMARY_system_transition_reasons_phase3_backfill_20260731

## Metadata

- Summary ID: `SUMMARY_system_transition_reasons_phase3_backfill_20260731`
- Status: `summarized`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-07-31T21:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/system_transition_reasons/PLAN_system_transition_reasons_phase3_backfill_20260731.md`
- Master plan: `backend/docs/architecture/under_construction/implementation/system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
- Related debug plan: `none`

## What was implemented

Phase 3 of four. **The only irreversible phase in the set** — it rewrites historical rows.

Migration `97b60e06d42a_backfill_other_task_priority_transition_.py` moves historical rows whose
`pause_reason_id` points at `pause_other_task_priority` onto `transition_reason =
OTHER_TASK_PRIORITY` with `pause_reason_id = NULL`. **270 rows** — 228 on `step_state_records`, 42
on `user_shift_state_records` — as a single statement, sized from the workspace-scoped figure
measured quiescent.

Also delivered: the R14 fix to `app/scripts/backfill/backfill_worker_shift_state_records.py`
(carried forward from phase 2 as sharing that mechanism), and **criterion 11 discharged** — the
`startswith(CLIENT_ID_PREFIX)` branch in `domain/users/serializers.py` proved dead by test rather
than removed.

### What it deliberately did NOT touch

Two of the three original populations were removed from scope by operator ruling before
implementation, which is why this phase is much smaller than first planned:

- **`pause_ended_shift` (169 rows)** — a worker's pick and a clock-out write are historically
  indistinguishable (same state, same id, `transition_reason` null on both). Migrating them would
  relabel real worker choices as system transitions, irreversibly and undetectably.
- **`pause_case_created` (7 rows)** — a stale value with no member minted. They keep resolving
  through the soft-deleted anchor, which satisfies success criterion 5 by construction rather than
  by a migration that has to reproduce it.

Both were verified byte-identical before and after, not merely equal in count.

### Selection, and why it is narrow by construction

Both UPDATEs select through `JOIN pause_reasons pr ON pr.client_id = <ref> AND pr.slug =
'pause_other_task_priority'` — that one slug alone, never `is_system_managed`, never a slug set.
A pre-flight assertion refuses to run if any selected row already carries a `transition_reason`.
The migration self-asserts at runtime that the guarded populations are identical before and after
and that zero references remain, raising otherwise. `user_declared_state_records` appears in no DML
statement.

The review demonstrated why that matters: the reviewer's own `ended_shift` count was 169 against the
recorded 153, the extra ~18 being cross-workspace suite residue carrying `is_system_managed = true`.
**A flag-based predicate would have swept all 169.**

### Reversibility

Post-cutover writers produce rows shape-identical to backfilled ones, so no predicate can find "the
backfilled rows" afterwards. The migration therefore journals every rewritten row —
`transition_reason_backfill_journal`, 270 rows, recording table, `client_id` and previous reference —
and `downgrade` restores exactly those rows. Proven byte-exact against a restore point.

## Review history

Round 1 `NEEDS_CHANGES` (3 findings, none in the SQL); round 2 **APPROVED**, no new findings.

The migration itself was verified correct in round 1 by per-population row-level md5 over all
columns against the reviewer's own restore point — not by accepting recorded figures — and confirmed
byte-identical in round 2.

### The finding worth remembering

**The journal was invisible to autogenerate.** Created in raw SQL, in no ORM metadata, and `env.py`
had no `include_object` filter — so the next `alembic revision --autogenerate` would have emitted
`op.drop_table` on it, destroying what this migration's own docstring calls the only record that
makes it reversible. It would have landed as a plausible line inside an unrelated migration with
nothing to prompt a question.

Fixed with an `include_object` filter on both configure paths, keyed on a reserved `_journal`
suffix, proven both ways against a scratch database **with a no-suffix control table** that drops in
both runs — the control being what proves the filter suppresses the right drops rather than drops
generally.

The convention has since been written into `architecture/30_migrations.md`, deliberately
**independent of this journal**, which phase 4 deletes.

### Two smaller corrections

- The prove-dead argument claimed the reference "cannot dangle" on FK grounds. Only
  `step_state_records` and `user_declared_state_records` have FKs to `pause_reasons`; the branch
  reads `user_shift_state_records.reason`, a plain `String(512)` with **no FK**. The conclusion held,
  the stated reason did not. *The operator's own review prompt carried the same error.*
- The intention was left stale on criterion 4; it now records an **explicit partial completion** —
  closed on the provably-dead arm only, with clause (a) not satisfied and not reachable
  (272 legacy strings beside 58 `par_…` ids).

## Carried forward to phase 4

- **The journal must be verified intact, dropped last, and its row count recorded.** Phase 3
  deferred its removal naming an owner but no default — the phase 2 procedural failure repeating —
  so phase 4's plan was amended to own it, with "keep it" as the stated default.
- Criterion 4 stays a **partial** completion. Phase 4 must not upgrade it to fully met.

## Validation

Rehearsal run end to end against a dump of the `.env` database (a dockerised copy of the server
database), with every figure attributed to its restore point, and the database returned to the state
it was found in. Idempotence proven by re-running `upgrade()`; `downgrade` proven byte-exact.
Label parity re-derived **against the database**, not the migration's mapping. Suite node sets
unchanged; `ruff check` clean on touched files.

**One recorded deviation:** the protocol's "restore a fresh copy" step requires an SSH tunnel through
the production bastion, which the implementer did not run autonomously. The restore point is a local
dump of the current copy rather than a freshly pulled one.
