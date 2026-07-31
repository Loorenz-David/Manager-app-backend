# PLAN_system_transition_reasons_phase4_retirement_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase4_retirement_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: retire the system catalog rows and everything that existed to serve them — the slug lookup,
  `slug` itself, its global unique index, `is_system_managed` — then make the new invariants
  enforceable by the database and close the feature set out.
- Business/user intent: `pause_reasons` becomes what it was always meant to be, a catalog of things
  a worker chooses. Dropping `uq_pause_reasons_slug` also **fixes the second-workspace
  `IntegrityError`** (success criterion 6) as a consequence of the design rather than as a patch.
  Constraints are where the guarantee stops depending on every future writer remembering.
- Non-goals: any behavioural change; `manually_recorded` (T7 — deferred).

## Scope

- In scope: retiring the one system row (`pause_other_task_priority`); deleting `get_system_pause_reason_id`; removing
  `is_system_managed` and its consumers; dropping `slug` and `uq_pause_reasons_slug`; the bootstrap
  seed phase and seed migration; check constraints; final verification and close-out.
- Out of scope: worker-choosable catalog rows and the CRUD surface, beyond removing system-row
  special-casing.
- Assumptions: phases 1–3 archived. **Entry condition: phase 3's zero-remaining-references query
  returns zero. Re-run it — do not trust the recorded result.**

## Clarifications required

- [ ] **Soft-delete or hard-delete `pause_other_task_priority`?** It is now the **only** row this
      phase retires. `pause_ended_shift` stays selectable (criterion 2), and `pause_case_created` is
      already soft-deleted and keeps 7 historical references (operator ruling 2026-07-31, phase 3
      clarification) — **retiring it is a no-op; do not touch it.** Soft-delete is safer (FK intact,
      reversible) but leaves rows a manager could see unless filtered. Hard-delete is only possible
      because phase 3 guarantees zero references, and `ondelete="RESTRICT"` will enforce that for
      us. **Recommend soft-delete**; escalate for the ruling.
- [ ] **Does `transition_reason` become `NOT NULL`**, or does null remain meaningful for
      worker-chosen pauses? Resolve from **phase 1's recorded `WORKER_PAUSED` ruling**, not by
      re-deciding it. If null is meaningful, the constraint is a check
      (`transition_reason IS NOT NULL OR pause_reason_id IS NOT NULL`) rather than `NOT NULL`.

## Acceptance criteria

### Retirement

1. **Entry condition re-verified**: zero rows reference `pause_other_task_priority`. Freshly run and
   recorded. If non-zero, STOP — phase 3 is incomplete.

   **References to `pause_ended_shift` and `pause_case_created` are expected and legitimate** — the
   first stays selectable so workers create new ones; the second holds 7 historical rows phase 3
   deliberately preserved. Do not treat a non-zero count on either as a failure, and do not
   "clean" them.
2. **`pause_ended_shift` is NOT soft-deleted. It becomes an ordinary worker-selectable pause reason**
   — `is_system_managed` cleared, left visible and editable like any other workspace row.

   *Amended 2026-07-31, operator ruling.* The original criterion said all three system rows are
   retired and disappear from every picker. That breaks the worker app.
   `list_pause_reasons.py:19` filters `is_deleted.is_(False)`, so soft-deleting the row removes it
   from the pause sheet — and the worker app currently translates that specific slug into a
   different state machine target
   (`frontend/apps/workers-app/.../lib/pause-reason-transition.ts:12`). Remove the row and a worker
   can no longer end a shift from the pause sheet at all.

   Retiring the **machinery** is this phase's job: the slug lookup, `is_system_managed`, and the
   runtime resolution. Retiring the **row** is not, because the row still has a legitimate use as a
   thing a worker picks. That is the whole distinction this feature set exists to draw — a catalog
   row is fine; a catalog row that system behaviour depends on is not.

   `pause_other_task_priority` is different: no worker picks it. Retire that one per the
   clarification's ruling.

   `pause_case_created` is **already** soft-deleted and stays that way, still serving as the FK
   target for 7 historical rows phase 3 deliberately leaves in place. There is nothing to retire —
   verify its state and move on. Hard-deleting it would violate `ondelete="RESTRICT"` and destroy
   labels that success criterion 5 requires.

3. Retired rows no longer appear in any worker-facing picker or manager-facing catalog list, and
   `pause_ended_shift` still does. **Assert against the actual endpoint response**, not the query.
4. `get_system_pause_reason_id` is **deleted** (success criterion 3), with its module if nothing else
   lives there, and its tests.
5. **`is_system_managed`: the BEHAVIOUR is removed, the COLUMN and the serializer field STAY.**
   *(Amended 2026-07-31 during implementation — same evidence and same ruling as T6.)*

   Remove `domain/pause_reasons/guards.py::can_delete_pause_reason` and its call sites — that
   function returning `not is_system_managed` was **delete protection**, and once no row is
   system-managed there is nothing left to protect. State that explicitly rather than leaving it
   implied.

   **Do NOT remove the serializer field or drop the column.**
   `frontend/packages/pause-reasons/src/types.ts:18` declares `is_system_managed: z.boolean()` —
   **required and non-nullable**, two lines above the `slug` declaration that forced T6's amendment.
   Removing it fails Zod validation on *every* pause-reasons response, not merely on a branch that
   reads it. Phase 1's audit escalated `slug` and missed its neighbour; the phase 2 reviewer's note
   that "`is_system_managed` has no frontend consumer" is true of *code branches* and false of the
   *schema*, which is the distinction that made `slug` blocking.

   After this phase the column is uniformly `false` and inert — retained to satisfy a published
   contract, not to carry meaning. `create_pause_reason.py`'s hardcoded `False` stays.
   `domain/transitions/labels.py` must keep emitting it in the synthesized object so the two shapes
   stay identical.

6. **`slug` is KEPT; `uq_pause_reasons_slug` is scoped to `(workspace_id, slug)`** (**T6 as
   amended** — see the master plan). Phase 1's out-of-repo audit found live consumers, the decisive
   one being `types.ts:19` `slug: z.string()`, required and non-nullable. **Do not drop the column.**
   Scoping the index is what resolves the second-workspace `IntegrityError`.
7. **Second-workspace bootstrap succeeds** — the mirror of phase 1's `IntegrityError` reproduction.
   Create two workspaces through the ordinary path on a **disposable** database and prove it is
   gone. This is success criterion 6.
8. The bootstrap seed phase and seed migration `49bd666da846` no longer seed system rows, and their
   duplicated `_PAUSE_REASONS` tuples are reconciled — both files carry comments requiring the other
   to be updated in step. Leaving them inconsistent is a finding.
9. Serializer output for pause reasons no longer includes removed fields, and the change is
   **proposed** to the operator for the handoff — not written into it.

### The phase 3 backfill journal — this phase owns its removal

Phase 3's migration writes `transition_reason_backfill_journal`, a raw-SQL table recording exactly
which rows it rewrote. Its own docstring calls it *"the only record that makes this migration
reversible"*.

**Added 2026-07-31**, because phase 3's deferral named an owner but no default — the same procedural
failure that cost phase 2 two review rounds, and the reason T-decisions now require both.

9a. **Verify the journal is still intact** before anything else in this phase. If it is missing,
    phase 3's migration is no longer reversible and that is a STOP: report it rather than
    proceeding, because the recovery options narrow sharply once phase 4's own changes land.

9b. **Drop the journal, deliberately and last** — after every other criterion in this phase passes,
    not before. Dropping it is the act that makes the backfill permanently irreversible, so it
    belongs at the point where the feature set is otherwise complete and verified.

9c. **Record the drop in the Review log** with the row count it held at the time, so the record of
    what was rewritten survives the table itself.

**Default if this phase is somehow reached without a ruling:** keep the journal. An orphaned table
costs a few kilobytes; a missing one costs the ability to undo a migration over production data.

### Constraints

10. The mutual-exclusion invariant is enforced by a check constraint: a row carrying a system
   `transition_reason` must have `pause_reason_id IS NULL`. This is the database making **T2** true
   rather than trusting future writers.
11. **Every existing row satisfies the constraint before it is added** — verified by query,
    recorded, not assumed. Adding a constraint that fails validation against production data is the
    failure mode this criterion exists to prevent.
12. Phase 1's `pause_reason_id` fallback in the read paths: either removed with proof no row can
    reach it, or **kept with a comment explaining why it must stay**. Silently leaving dead code is
    a finding; so is removing a branch legacy rows still need. Phase 3's parity evidence decides
    which.

### Close-out

13. All six master-plan success criteria re-verified **end-to-end and fresh** — not inherited from
    the phases that first claimed them. In particular criterion 1 (clock-out in a zero-catalog
    workspace) and criterion 6 (second-workspace bootstrap) are re-run.
14. **D3, D5 and D14** carry their final amendment state in this feature set's master plan,
    consistent with what shipped. The declared_worker_states plan is archived — verify no phase
    edited it.
15. The intention plan moves to `achieved`, its linked-plans table is updated to the four-phase set,
    and its open questions are answered or explicitly closed.
16. Deferred items collected into one visible list in the master plan: T7's `manually_recorded`
    subsumption, plus any repo-health item found but not fixed across phases 1–4 (T8).

## Contracts and skills

### Contracts loaded

- `backend/architecture/04_migrations.md`, `03_models.md`, `46_serialization.md`
- `backend/architecture/23_documentation.md`: close-out discipline.

### File read intent — pattern vs. relational

- Permitted (relational): `pause_reason.py`; `guards.py`; `create_pause_reason.py`; the pause-reason
  serializer; `seed_pause_reasons.py`; migrations `49bd666da846` / `fb10ac7fd439`; every Review log
  from phases 1–3, to **verify** criteria rather than trust them.
- Prohibited (pattern): style reads.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Re-run phase 3's zero-references query. If non-zero, STOP.
2. Escalate both clarifications.
3. Retire the rows; assert absence from pickers and catalog listings via real endpoint responses.
4. Delete `get_system_pause_reason_id` and its tests; remove `is_system_managed` and each consumer.
5. Drop `slug` and `uq_pause_reasons_slug`; reconcile the seed phase and seed migration.
6. Two-workspace bootstrap test on a disposable database.
7. Verify constraint compliance by query, then add the constraint migration.
8. Decide phase 1's fallback: remove with proof, or keep with a comment.
9. Re-verify all six success criteria fresh; finalise D3/D5/D14; move the intention to `achieved`;
   collect deferred items.
10. Review log entry; handoff proposal, not edit. STOP for final review.

## Risks and mitigations

- Risk: an out-of-repo consumer of `slug` breaks silently after the column is gone.
  Mitigation: criterion 5 depends on phase 1's audit; the operator's T6 ruling was explicitly
  conditional on it finding nothing.
- Risk: removing `is_system_managed` removes delete protection something else quietly relied on.
  Mitigation: criterion 4 requires confirming what depended on it before removal.
- Risk: the constraint fails validation against production data mid-deploy.
  Mitigation: criterion 10 requires proving compliance by query first.
- Risk: the fallback is removed while legacy rows still need it, breaking historical labels.
  Mitigation: criterion 11 ties the decision to phase 3's parity evidence.
- Risk: success criteria are marked met by citing earlier phases' claims.
  Mitigation: criterion 12 requires fresh re-verification.
- Risk: the seed phase and seed migration drift, so a fresh database and an upgraded one end up with
  different catalogs.
  Mitigation: criterion 7 requires reconciling both.

## Validation plan

- Zero-references query returns zero, freshly run.
- Two-workspace bootstrap succeeds on a disposable database.
- `grep -rn "get_system_pause_reason_id\|is_system_managed\|slug" app/beyo_manager` returns nothing
  in the pause-reasons domain.
- Fresh-database `alembic upgrade head` produces a catalog with no system rows.
- Pre-constraint compliance query returns zero violating rows; the constraint rejects a deliberately
  invalid insert.
- All six success criteria re-verified fresh, with evidence.
- Full suite: no new failure nodes vs. baseline (node sets, not counts).
- `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
