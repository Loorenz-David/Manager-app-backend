# SUMMARY_system_transition_reasons_phase4_retirement_20260731

## Metadata

- Summary ID: `SUMMARY_system_transition_reasons_phase4_retirement_20260731`
- Status: `summarized`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-08-01T00:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/system_transition_reasons/PLAN_system_transition_reasons_phase4_retirement_20260731.md`
- Master plan: `backend/docs/architecture/under_construction/implementation/system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## What was implemented

Phase 4 of four — the final phase. It retires the machinery that served system pause reasons and
makes the new invariants enforceable by the database.

- **`uq_pause_reasons_slug` scoped to `(workspace_id, slug)`.** It was globally unique, so a slug
  could exist in exactly one workspace database-wide — which is why bootstrapping a second workspace
  raised `IntegrityError` and only one workspace ever received the default catalog.
- **`pause_other_task_priority` soft-deleted**, after re-asserting zero references at migration time.
- **`get_system_pause_reason_id` and `can_delete_pause_reason` deleted.** The guard blocked deletion
  of rows the backend resolved by slug; no such row exists any more.
- **CHECK constraint on `step_state_records`** — a row carries a transition reason or a catalog
  reference, never both. Scoped to that table only: a declaration projection on
  `user_shift_state_records` carries both **by design**.
- **The seed no longer marks anything system-managed** and drops `pause_other_task_priority`.
  Migration `49bd666da846` was deliberately not edited — it is applied history.

### Two things kept that the plan originally said to remove

Both were caught during implementation, and both would have broken the worker app.

- **`slug`** — phase 1's audit found live frontend consumers, decisively
  `types.ts:19` `slug: z.string()`, required and non-nullable. T6 was amended before this phase.
- **`is_system_managed`** — `types.ts:18` declares it `z.boolean()`, required and non-nullable,
  **two lines above `slug`**. Phase 1's audit escalated one and missed its neighbour. Removing it
  fails Zod on every pause-reasons response, not merely on a branch that reads it. T6 was extended
  to cover it, on identical evidence.

Both survive as **inert published contract**: uniformly `false`/present, read by nothing for
behaviour. The distinction that made them blocking — *the schema requires it* versus *no code
branches on it* — is the one worth carrying forward.

## Review history

Round 1 `NEEDS_CHANGES` (F1 medium, F2–F5 low). Round 2 `NEEDS_CHANGES` — mechanical only, three
stale citations and two gaps in the deferred list, none touching logic.

### F1 — the migration claimed reversibility it did not have

`downgrade` restores the **global** unique index, which cannot be recreated once a second workspace
holds the same slug — the exact capability `upgrade` delivers. It now counts duplicates first and
**refuses with an explanation** rather than dying on an opaque `IntegrityError` partway through.
Verified both ways: clean downgrade succeeds, downgrade with a planted duplicate refuses.

### The journal incident

While restoring state after an unrelated test, the implementer ran `alembic upgrade head`. `head`
had moved to include the journal-drop revision, and **270 rows recording which rows phase 3 rewrote
were destroyed by a command nobody thinks of as destructive.**

Recovered exactly — and the round-2 reviewer proved the recovery was exact rather than plausible:
`previous_pause_reason_id` is a single constant across all 270 rows, and the reconstructed
`client_id` set matched the live `other_task_priority` rows with all four set-differences zero.
**That was only possible because this database has no post-cutover traffic.** With live traffic the
backfilled rows and newly-written ones are indistinguishable and the record would be gone.

The fix outlives the incident: `c8f3d2e60a17` now refuses without
`ALLOW_DROP_BACKFILL_JOURNAL=yes`, and **the pattern is in `architecture/30_migrations.md`** so the
next migration-owned bookkeeping table gets the guard without anyone rediscovering why. Being a
separate revision was not protection, because `upgrade head` is what people type.

### A cross-phase collision worth remembering

The new constraint made a phase 2 test unconstructible — it asserted precedence by seeding a step
record carrying both explanations. Rather than delete an approved test, its step record now carries
the catalog reference alone, the both-carrying assertion moved to the table where it is legal, and
`bucket_key`'s ordering is asserted directly as the defensive behaviour it now is.

## Independence

This phase was planned, prompted, ruled on and implemented by the **same agent**, because the
operator's implementer window was occupied. The review prompt said so and asked for more scepticism.
Both review rounds found real defects, including one the implementer's own design was meant to
prevent.

## Validation

Constraint compliance proven by query **before** it was added (0 violating rows). Guarded
populations byte-identical: `pause_ended_shift` 169, `pause_case_created` 7. Second-workspace
`IntegrityError` proven gone twice — by a rolled-back duplicate insert, and by the reviewer's own
run of the real `seed_pause_reasons` path. Baseline node-set diff (reviewer's, rigorous): 27
baseline → 23 HEAD, **zero new nodes**.

**Criterion 7 not met as written** — the two-workspace bootstrap needs a disposable database and a
fresh `alembic upgrade head` stalls, itself a recorded repo-health item. Accepted on substitute
evidence at the reviewer's recommendation.

**Success criterion 4 remains PARTIAL** — closed on the provably-dead arm only. 272 legacy strings
still sit beside 58 `par_…` ids, and the three-way `reason_text` suppression is published contract.
Not reachable under the standing rulings.
