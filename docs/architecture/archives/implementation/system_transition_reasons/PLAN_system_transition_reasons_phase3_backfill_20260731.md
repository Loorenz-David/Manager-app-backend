# PLAN_system_transition_reasons_phase3_backfill_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase3_backfill_20260731`
- Status: `archived`
- Owner agent: `claude-fable-5 (implementer)`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T19:15:00Z`
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

- [x] **Batched or single-statement?** *Resolved 2026-07-31 (implementer): **single
      statement, from the figure 270.*** Re-measured workspace-scoped and quiescent before
      deciding: 228 `step_state_records` (phase 1's STABLE figure, reproduced exactly) +
      42 `user_shift_state_records` `par_…` references = 270 rows total. Three orders of
      magnitude below any batching threshold; each table is one indexed UPDATE inside the
      migration's transaction.
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

- `2026-07-31` `implementer (claude-fable-5)`: **Implemented and validated. STOPPED for
  independent review.** Deliverables: migration `97b60e06d42a_backfill_other_task_priority_transition_.py`,
  the R14 fix to `app/scripts/backfill/backfill_worker_shift_state_records.py`, criterion 11
  discharged by prove-dead test (`tests/unit/domain/transitions/test_prefix_branch_post_backfill.py`),
  new script test, and the rehearsal run end to end with restores. Evidence below.

  **Batching decision — single statement, from the figure 270** (see the resolved
  clarification above: 228 step + 42 derived, workspace-scoped, quiescent, phase 1's STABLE
  step figure reproduced exactly). The 98 scoped `par_…` values on the derived table resolve
  as: otp 42 / coffee 15 / lunch 18 / meeting 1 / upholstery 22 — **zero** `par_…` references
  to `pause_ended_shift` or `pause_case_created` exist on the derived table.

  **Selection (criterion 5).** Both UPDATEs select through
  `JOIN pause_reasons pr ON pr.client_id = <ref> AND pr.slug = 'pause_other_task_priority'` —
  the one slug alone; never `is_system_managed`, never a slug set. A pre-flight assertion
  refuses to run if any selected row already carries a `transition_reason` (contradictory row;
  measured 0). The migration self-asserts at runtime that the guarded populations
  (ended_shift refs, case_created refs, `user_declared_state_records` count) are identical
  before and after, and that zero references remain, raising otherwise.
  `user_declared_state_records` appears in no DML statement.

  **Reversibility — criterion 8's stronger branch.** Post-cutover writers produce rows
  shape-identical to backfilled ones, so no predicate can find "the backfilled rows" later.
  The migration journals every rewritten row (`transition_reason_backfill_journal`:
  table_name, client_id, previous reference; 270 rows) and `downgrade` restores exactly those
  rows and drops the journal — proven byte-exact below. **Proposal for the operator:** phase 4
  should drop the journal once the production backfill is verified; until then it is what
  keeps this one-way-looking migration genuinely reversible.

  **Rehearsal (every figure attributed to its restore).**
  - **R0** = pg_dump (custom) of the `.env` database, 2026-07-31 19:52 local, quiescent
    (zero active backends), alembic head `a7d21f4c8b03`. sha256
    `da2062d14ba853239344eb87b13f105a45162b95017dde8a35611c5d98a30dff`; kept with its
    fingerprint at `secretes/_dumps/phase3_rehearsal_R0_*_20260731.*`. Fingerprint =
    order-insensitive per-table md5 over all columns: step 5865:`f57737bf…`, uss
    4165:`fc85c903…`, declared 0, pause_reasons 7:`8023352a…`.
    *Recorded deviation:* protocol step 1 says "restore a fresh copy"; a fresh copy requires
    the SSH tunnel through the production bastion (`secretes/refresh_local_from_rds.sh`),
    which I did not run autonomously. The restore point is a local dump of the current copy —
    same known-state repeatability, no production access. Operator may re-run from a fresh
    download if the distinction matters.
  - **Before/after labels through the real read paths:** the production query services called
    directly (`list_workers_linear_timeline`, `get_worker_linear_timeline_breakdown`,
    `get_worker_clock_out_analytics`, plus the current-state serializer over every open row)
    for 5 sample users over the full history window — covering every row shape: `par_…otp`,
    worker-chosen `par_…`, all six legacy slug strings, `unspecified`, NULL, and step rows
    FK→otp / ended_shift / case_created / worker reasons. **Parity: 29/29 checks OK; 291
    paused breakdown segments field-exact**, modulo exactly the two phase-2-decided key
    mappings: bucket key `par_…otp` → `other_task_priority` (identical name / image_url /
    pause_type on both sides), and the nested step `pause_reason` object rendering the
    synthesized catalog shape (`client_id` = the enum value, `created_at` = the owning
    record's `entered_at`, every display field byte-equal — R2/R9 as phase 2 decided).
    Legacy slug bucket keys (incl. the 132 `pause_other_task_priority` strings) render
    identically before and after — including their pre-existing non-resolution in the roster
    lookup map, which phase 1 logged and this phase does not change.
  - **Zero-reference query (verbatim), result `0|0`, run post-migration on R0+migration:**
    ```sql
    SELECT
      (SELECT count(*) FROM step_state_records ssr
       JOIN pause_reasons pr ON pr.client_id = ssr.pause_reason_id
       WHERE pr.slug = 'pause_other_task_priority') AS step_refs,
      (SELECT count(*) FROM user_shift_state_records uss
       JOIN pause_reasons pr ON pr.client_id = uss.reason
       WHERE pr.slug = 'pause_other_task_priority') AS uss_par_refs;
    ```
    Rows pointing at `pause_ended_shift` and `pause_case_created` remain by design and are
    not counted (criterion 10).
  - **Untouched populations proven by count and by hash** (criteria 1, 3, 4): scoped step
    counts identical before/after — ended_shift 153, case_created 7, coffee 52, lunch 71,
    meeting 15, upholstery 45; every legacy uss string count identical (otp-slug 132,
    case_created 6, unspecified 13, …); `user_declared_state_records` 0 throughout;
    `pause_reasons` table md5 byte-identical. Worker-chosen rows keep `pause_reason_id`
    intact with `transition_reason` NULL — consistent with phase 1's ruling, which minted no
    `WORKER_PAUSED` member (the catalog reference alone carries the worker-chosen case).
    Note: scoped ended_shift measures 153 where phase 1 recorded 152 — one row of accumulated
    residue since phase 1's measurement; the invariant proven here is before==after within
    one restore, which holds exactly.
  - **Idempotence (criterion 9):** every data statement re-executed verbatim after the
    upgrade: `INSERT 0 0`, `INSERT 0 0`, `UPDATE 0`, `UPDATE 0`; journal still 270. The
    predicates are self-excluding (a migrated row carries no catalog reference and a non-null
    `transition_reason`), so a second run selects nothing.
  - **upgrade → downgrade → upgrade:** post-downgrade md5s equal R0 exactly
    (step `f57737bf…`, uss `fc85c903…`), journal dropped; post-re-upgrade md5s equal the
    first post-upgrade state exactly (step `faba0ad3…`, uss `00a65cb5…`), journal 270 again.
  - **Final restore:** DB dropped, recreated, restored from the R0 dump; every fingerprint
    equals the recorded restore point (alembic revision, all four table md5s, no journal).
    The local database is **left in this verified R0 state** (migration not applied) for the
    reviewer.

  **Criterion 11 — discharged on the prove-dead arm; the branch itself must stay.** Finding:
  the suppression arm of the prefix branch is not incidental code — it implements the
  published three-way `reason_text` contract
  (`HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §5.3/§4: an unresolvable catalog
  reference renders `reason_text: null`; "the backend deliberately does not expose the raw
  identifier"), asserted verbatim by `test_reason_text_contract_conformance.py`. Removing it
  would be a unilateral change to an operator-owned contract. What the backfill removes is
  its **input population**:
  - Post-migration, every `par_…` id remaining on the derived table resolves in its own
    workspace. Whole-database workspace-scoped join finds **2** non-resolving rows — the same
    two cross-workspace rows phase 1 already recorded as test-workspace residue: open
    `in_pause` rows in suite-created workspaces pointing at the dev workspace's
    `pause_coffee_break`. Mechanism verified, not assumed: test seeders resolve `PauseReason`
    by slug with **no workspace predicate** (e.g. `_add_step_record` in the backfill script's
    own test file), and the still-global `uq_pause_reasons_slug` guarantees they find the dev
    row. Shared-test-database residue (T8 measurement artefact), not app behaviour: every
    production writer validates the reason against the caller's workspace before persisting,
    and catalog rows are never hard-deleted, so a stored reference can neither be foreign nor
    dangle. In the real workspace the count is **0**.
  - `test_prefix_branch_post_backfill.py` enumerates the complete post-backfill shape set of
    `reason` (NULL ± transition, resolving `par_…` id, all six legacy slugs, `unspecified` —
    the measured distinct set) and proves none reaches the suppression arm. The branch is
    dead with respect to every row the migration leaves behind and stays as
    contract-mandated defence.
  - **Flag for the operator (master success criterion 4):** under the standing rulings
    (ended_shift references stay; legacy strings preserved; the published three-way
    contract), `reason` continues to hold both catalog ids and legacy strings, so full
    removal of prefix-inspection would require either migrating the legacy strings (refused
    by criterion 6) or amending the published handoff (operator-owned). Criterion 4 is met in
    its "provably dead" reading; the "gone" reading is not reachable inside this phase's
    constraints. The reviewer should rule which reading closes it.

  **`backfill_worker_shift_state_records.py` (R14) fixed:** `_load_day_intervals` selects
  `transition_reason` into `LinearInterval`; `_records_from_segments` writes it onto rebuilt
  `IN_PAUSE` rows — mirroring `_reconstruct_shift_middle`. New test
  `test_backfill_carries_transition_reason_onto_rebuilt_rows` proves a system-typed step
  pause rebuilds into a segment bucketing as `other_task_priority` and resolving in the
  breakdown lookup. Sweep: all four `LinearInterval(` construction sites in the repository
  now carry the field. The script's documented declared-rows limitation stands, out of scope.

  **Domain docs deliberately unchanged, with reasoning:** the README's overloaded-`reason`
  caveat remains true after this phase — 56 worker-chosen `par_…` ids and 272 legacy strings
  still share the column, and the serializer still inspects the prefix (contract-mandated,
  above). The prompt's rewrite instruction was conditioned on the branch going away; it did
  not. Nothing in `docs/domains/worker_shifts/` became false.

  **Validation.** `ruff check` clean on all four touched files. Suite compared **run-1 vs
  run-1, each from a fresh R0 restore** (the restorability makes the like-for-like run-index
  rule exact and no latching node appeared): baseline (phase-3 files stashed, unmigrated R0)
  **26 failed / 1397 passed / 0 errors**; this tree (files restored, migration applied)
  **26 failed / 1408 passed / 0 errors** — +11 passed = the 11 new tests, and the failure
  **node sets are identical** (diff empty). Both runs sit on the recorded sanity anchor
  (26/~1400, zero collection errors), measured from `backend/app/` in the main tree per the
  master plan's baseline-worktree corrections.

  **Commits (T9):** implementation commit = the four app files only; this plan edit committed
  separately. The parallel reassigned-steps files and the operator's in-flight master-plan
  edit verified unstaged before each commit.

  **STOP** — awaiting independent review. No summary, no archive, no phase-table flip, no
  handoff edit.

- `2026-07-31` `independent reviewer`: **`NEEDS_CHANGES`.** Three findings, none of them in the SQL.
  **History access: yes** — `git rev-parse` run from `backend/`, root confirmed, full log read.

  **What I verified myself, from my own restore point, not from the figures above.** I took my own
  `pg_dump` of the local database before touching it (`reviewer_pre.dump`), captured a snapshot
  including **per-population row-level md5 over all columns**, ran `alembic upgrade head`, and
  diffed. The database is left exactly as I found it (`a7d21f4c8b03`, no journal, every fingerprint
  equal to my pre-review baseline).

  - **The two untouched populations are byte-identical, by my hashes, not by counts.**
    `pause_ended_shift` 169 step rows `1cd76bf6…` and `pause_case_created` 7 step rows
    `ae593b74…` are **absent from the before/after diff entirely** — as are the 6
    `literal:pause_case_created` derived rows (`fb22d135…`), all four worker-chosen step
    populations (coffee 208 / lunch 71 / meeting 15 / upholstery 45), and the `pause_reasons`
    table itself (`8fd5ea50…`). `user_declared_state_records` appears in no DML statement in the
    file; note its evidentiary value here is **code-read only**, since the table is empty in this
    database and the guard over it is vacuously true.
  - **My ended_shift figure is 169, not the 153 recorded above.** The difference is ~18
    cross-workspace suite-residue rows in test workspaces. That *strengthens* the check rather than
    weakening it: my hash covers the residue rows too, and they are exactly the
    `is_system_managed = true` rows in a second workspace that the prompt asks be constructed as a
    probe. They did not move. The `is_system_managed = true` set is `{pause_other_task_priority,
    pause_ended_shift}` — a predicate on that flag would have swept all 169 ended_shift rows.
    The WHERE clause selects on `pr.slug = 'pause_other_task_priority'` alone, and
    `uq_pause_reasons_slug` is **globally unique**, so that resolves to exactly one catalog row.
  - **Idempotent, by re-running the real `upgrade()`** — not by re-executing the statements.
    `alembic stamp a7d21f4c8b03` then `alembic upgrade head` against already-migrated data:
    **empty diff**, journal still 270.
  - **`downgrade` restores byte-exactly.** Post-downgrade snapshot is **identical to my
    pre-migration baseline**, whole-table md5s included; journal dropped.
  - **The refusal guard is real, not decorative.** I planted a contradictory row (otp reference +
    `transition_reason` already set) and ran the migration: it raised, left no journal, and left
    `alembic_version` at `a7d21f4c8b03`. Transactional DDL means a failed run cannot leave a
    partial journal behind.
  - **Label parity re-derived independently for two shapes**, against the database rather than the
    migration's dict. `domain/transitions/labels.py` is checked against the actual catalog rows:
    `name`, `image_url`, `pause_type`, `requires_description`, `is_system_managed` are byte-equal
    for both `pause_other_task_priority` and `pause_ended_shift`. The parity is *not*
    self-referential — the migration writes only the enum string; the labels come from a separate
    code artifact whose values I compared to the rows being retired.
  - **Volume 270 reproduced exactly** (228 step + 42 derived; all target rows sit in one
    workspace, so scoped and global agree here). Single statement is justified.
  - **Legacy strings preserved** — 272 of them, my count, criterion 6 holds. **Criterion 11's
    `LEGACY_VALUES` set is the true measured distinct set** (7 values); I re-measured it.
  - Suite arithmetic **does** close: 10 new tests in the new unit file + 1 appended to the
    pre-existing integration file = the 11 claimed. All 13 in those files pass; `ruff` clean.
    (I initially read this as 13 new tests; the integration file already carried 2.)

  **F1 — MEDIUM — `transition_reason_backfill_journal` is invisible to autogenerate, and the only
  instruction to drop it lives in a document that gets archived.**
  `migrations/versions/97b60e06d42a…py:112-123` creates the journal in raw SQL. It appears **nowhere
  in `Base.metadata`** (zero references under `beyo_manager/`), and `migrations/env.py:18,25,40`
  sets `target_metadata = Base.metadata` with **no `include_object`/`include_name` filter**. The
  next `alembic revision --autogenerate` will therefore emit
  `op.drop_table('transition_reason_backfill_journal')` — silently destroying what this migration's
  own docstring (lines 20-24) calls *"the only record that makes this migration reversible"*, on the
  one phase in this set that cannot otherwise be undone. Compounding it: the hand-off names an owner
  (*"the operator"*) but **no default**, and `PLAN_…phase4_retirement_20260731.md` contains **zero
  occurrences of "journal"** — the deferral exists only in this Review log. This is the phase-2
  procedural lesson repeating: a deferral with an owner but no default, recorded only in the file
  that gets frozen. *Violates criterion 8 (durability of the reversibility mechanism) and the
  phase-2 procedural rule.* Fix is documentary and small: record the journal in phase 4's plan with
  an explicit default for "phase 4 does not act", and protect it from autogenerate (an
  `include_object` exclusion, or a `# noqa`-style note in phase 4's entry conditions).

  **F2 — LOW — the "cannot dangle" premise behind criterion 11 is not backed by the schema on the
  table the branch actually reads.** Both this plan (criterion 11, bullet 1) and
  `tests/unit/domain/transitions/test_prefix_branch_post_backfill.py:16` justify deadness with
  *"catalog rows are never hard-deleted, so a stored reference can neither be foreign nor dangle."*
  But `pause_reason_reference_is_unresolved` reads `UserShiftStateRecord.reason`
  (`domain/users/serializers.py:152-171`), and I enumerated `pg_constraint`: exactly **two** FKs
  reference `pause_reasons` — `step_state_records.pause_reason_id` and
  `user_declared_state_records.pause_reason_id`, both `ON DELETE RESTRICT`.
  **`user_shift_state_records.reason` has no foreign key at all.** On the one table this branch
  reads, nothing structural prevents a dangling `par_…` id; the claim rests on operational
  convention, not the constraint it cites. (The review prompt's own "do not probe hard-delete, the
  FK raises" instruction inherits the same error — it is true for the two FK-bearing tables and
  false for this one.) **Bounded impact:** the branch is retained as contract-mandated defence, so
  behaviour is safe either way. This is an accuracy defect in the discharge argument, not a data
  defect — but it is the kind the prompt asks to be named even when the outcome looks right.

  **F3 — LOW — the intention was left stale.**
  `INTENTION_system_transition_reasons_20260730.md:320-323` still reads *"Criterion 4 — not yet …
  **Phase 3's backfill discharges it.**"* Phase 3 has now run and reached a materially different
  conclusion — dead in one reading only, with the branch permanently retained under a published
  operator-owned contract. No commit touches the intention. *Mitigating:* the implementer surfaced
  the question for ruling rather than quietly closing it, which is the right instinct.

  **Ruling on criterion 4, as requested.** It closes on the *"provably dead"* arm — but only that
  arm, and this should be written down rather than absorbed. The criterion has two clauses
  (`INTENTION…:225-226`): (a) *"No field in the shift/step state model requires prefix-sniffing to
  determine its meaning"*; (b) *"the `startswith(CLIENT_ID_PREFIX)` branch … is gone or provably
  dead."* Clause (b) is satisfied, and both governing documents had already chosen that arm — the
  master plan's binding item 2 says in terms *"After the backfill it can be shown dead — that is
  what closes master-plan success criterion 4."* Clause (a) is **not** satisfied and is not
  reachable under the standing rulings: `reason` still carries 272 legacy strings beside 58 `par_…`
  ids, and `serializers.py:170` still sniffs. Record clause (a) as an explicit non-completion with
  its blocking constraint (the published three-way `reason_text` contract), or reopen it as its own
  item. Do not let it close by implication.

  **Checked and clean:** WHERE clause selects by identity, not by flag or pattern (criterion 5);
  zero-reference query reproduces `0|0` and I re-ran it; `user_declared_state_records` untouched;
  `backfill_worker_shift_state_records.py` picked up (R14), all four `LinearInterval` sites carry
  the field; phase 1's `image_url` premise correctly **not** re-derived — I confirmed the literals
  are byte-identical in `seed_pause_reasons.py`, migration `49bd666da846` and `labels.py`, and that
  bootstrap force-overwrites the column, so "the icon lives in code" is sound. **Domain docs
  correctly left unchanged** — the README caveat (`worker_shifts/README.md:61-64`) remains true, and
  I spot-checked it against code and schema: the prefix inspection still exists at
  `serializers.py:170`, and the declared `string(32)` / `string(512)` / `not null` types match the
  live columns. No plan references or phase numbers were introduced into the living docs.
  **Rehearsal:** the final restore was performed — the database sits at `a7d21f4c8b03` with no
  journal, which only the restore explains. Its step-1 deviation (local dump rather than a fresh
  production download) is disclosed and reasonable. Note the whole-table md5s have since drifted
  from the recorded R0 (step 5895 vs 5865, uss 4193 vs 4165) through post-restore suite residue, so
  *"left in this verified R0 state for the reviewer"* was no longer literally true when I began —
  immaterial, since before-vs-after within one restore is the invariant that matters and I measured
  my own.

  **On "would a mistake have been caught".** Mostly yes, and by more than one mechanism: the
  in-migration guards raise rather than warn, and the refusal path aborts atomically — I confirmed
  both by planting a row. One gap worth naming: `_GUARDED_COUNTS_SQL` compares **counts only**, so
  it would not catch a guarded row being modified in place (e.g. a `transition_reason` written onto
  an `ended_shift` row) without its catalog reference changing. The actual UPDATE predicates make
  that unreachable in this file, so it is a robustness note, not a defect — but the guard is
  weaker than the prose around it implies.

- `2026-07-31` `implementer (claude-fable-5)`: **Round-1 fix cycle complete (F1, F2, F3).
  STOPPED for re-review.** No SQL touched; the migration file is unchanged from the reviewed
  commit `2f96915`.

  **F1 — fixed in `app/migrations/env.py`, predicate general by convention.** Added an
  `include_object` filter wired into both the offline and online `context.configure` calls. The
  excluded case is exactly `type_ == "table" and reflected and compare_to is None` — a table
  present in the database with no ORM counterpart, the only case autogenerate answers with
  `drop_table` — scoped by the naming convention `*_journal`, now documented in `env.py` as the
  marker for migration-owned bookkeeping tables. Any future raw-SQL bookkeeping table using the
  suffix inherits the protection; a genuine ORM table that happened to use the suffix has a
  metadata counterpart (`compare_to is not None`) and is unaffected. The journal deliberately
  gains no model, per the fix brief.

  **Proof, both ways, then discarded.** Against the database with the migration applied (journal
  present): with the filter, `alembic revision --autogenerate` produced scratch revision
  `d9293879e57e` containing **no reference to the journal and no `drop_table` at all**; with the
  filter stashed, scratch revision `810c3d53f84d` contained
  `op.drop_table('transition_reason_backfill_journal')` (line 21) — the exact destruction F1
  predicted, plus a `create_table` for it in `downgrade`. Both scratch revisions were deleted;
  `ls migrations/versions/ | grep scratch` confirms none remain; the filter was restored via
  `git stash pop`. The database was then downgraded back to `a7d21f4c8b03` (the state the review
  left it in). `ruff check migrations/env.py` clean.

  **F2 — the discharge argument corrected at its living site.** The module docstring of
  `tests/unit/domain/transitions/test_prefix_branch_post_backfill.py` no longer claims the
  reference "cannot dangle": it now states that `user_shift_state_records.reason` is a plain
  `String(512)` with **no foreign key**, that nothing referential prevents a stale or foreign id
  in principle — only the writers' workspace validation does — that the resolving-`par_…` shape is
  *measured, not guaranteed*, and that the branch is **defence, not dead code**. Grep confirms no
  "cannot dangle" / "never hard-deleted" phrasing survives anywhere in the phase's files. The
  false version in my round-0 entry above stands as history; this entry is its correction. (Noted:
  the review prompt's "the FK raises" probe instruction carries the same error for this table —
  operator-owned, not edited.)

  **F3 — the intention now records an explicit partial completion.** New dated progress note in
  `INTENTION_system_transition_reasons_20260730.md` (above the phase 2 entry): criterion 4 closes
  on **clause (b) — provably dead — only**, as the reviewer ruled; clause (a) — no field requiring
  prefix-sniffing — is recorded as **NOT satisfied and not reachable under the standing rulings**,
  with the blocking constraint named (272 legacy strings beside 58 `par_…` ids; the suppression
  behaviour is the published three-way `reason_text` contract) and the FK-absence fact from F2
  carried there too, so downstream readers see met-in-part, not met.

  **Validation of the fix:** `test_prefix_branch_post_backfill.py` 10/10 green; ruff clean on both
  touched files. Suite not re-run: `env.py` executes only under alembic (autogenerate proof above
  is its behavioural test), and the test-docstring and intention edits contain no executable
  change.

  **Commits (T9):** fix commit = `app/migrations/env.py` +
  `app/tests/unit/domain/transitions/test_prefix_branch_post_backfill.py`; docs commit = the
  intention note + this entry. Parallel reassigned-steps files and the operator's master-plan edit
  verified unstaged.

  **STOP** — awaiting re-review.

- `2026-07-31` `independent reviewer (round 2)`: **`APPROVED`.** All three round-1 findings are
  discharged. No new findings. The SQL was not re-reviewed (round 1's per-population md5
  verification stands) — but the identity claim behind that was checked: the migration file
  `97b60e06d42a_backfill_other_task_priority_transition_.py` has exactly one commit in its history
  (`2f96915`), `git diff 3698a70^ HEAD` on it is empty, and it has no working-tree delta. Byte
  identity to the reviewed commit confirmed.

  **F1 — CLOSED. Proof reproduced independently, both ways, with controls.** I did not run the
  backfill or touch the operator's database. I built a scratch database
  (`beyo_autogen_probe` on the same cluster), stamped `alembic_version` at head `97b60e06d42a`,
  and created three orphan tables — the real journal DDL copied from the migration, plus two
  controls: `zz_control_orphan` (no suffix) and `zz_future_bookkeeping_journal` (suffix, unrelated
  name). Autogenerate against that database, twice:
  - **Filter wired (HEAD as committed)** — revision `20c8cf00bcc5`: `upgrade()` contains
    `op.drop_table('zz_control_orphan')` (line 2255) and **no mention of either `_journal` table
    anywhere in the file**. Alembic's own log emits `Detected removed table 'zz_control_orphan'`
    and nothing for the journals.
  - **Filter unwired** (the two `include_object=_include_object` kwargs removed, nothing else) —
    revision `68fb43b918ea`: `upgrade()` contains `op.drop_table('transition_reason_backfill_journal')`
    (line 2256) and `op.drop_table('zz_future_bookkeeping_journal')` (line 2257), with `downgrade()`
    re-creating them. This is exactly the destruction F1 predicted.

  The `zz_control_orphan` control is the load-bearing half: it is dropped in **both** runs, so the
  filter is not suppressing orphan drops in general — only suffix-matching ones. The
  `zz_future_bookkeeping_journal` control confirms the predicate is genuinely suffix-general, not
  keyed to the phase-3 table's name.

  **Both configure paths carry it, verified by reading** — `env.py:58` (`run_migrations_offline`)
  and `env.py:73` (`_do_run_migrations`, the online path). Symmetric; neither path is bare.

  **Predicate narrowness.** `type_ == "table" and reflected and compare_to is None` is correct and
  each condition is load-bearing; `reflected and compare_to is None` is precisely "in the database,
  absent from metadata", the only shape autogenerate answers with `drop_table`. One precision note
  on the docstring at `env.py:37-39` ("a genuine ORM table that happened to use the suffix would
  have a metadata counterpart and is unaffected"): that holds while the model exists, but at the
  moment a model is *intentionally deleted* its table also reflects with `compare_to is None`, and
  the filter would suppress that legitimate drop if the table's name ended in `_journal`. The
  predicate cannot distinguish the two cases — safety rests entirely on the suffix being reserved.
  It currently is: `grep '__tablename__'` across the repository returns **zero** ORM tables ending
  in `_journal`. Not a defect; recorded so the docstring's guarantee is not read as stronger than
  it is.

  **Cleanup verified.** Neither scratch revision named in the round-1 entry (`d9293879e57e`,
  `810c3d53f84d`) survives in `app/migrations/versions/`, nor anywhere in `app/`. My own two probe
  revisions were removed from `versions/` (copies kept outside the repo), `env.py` was restored
  with `git checkout` and again shows both wirings, and the scratch database was dropped. The
  operator's database is untouched: `alembic current` reports `a7d21f4c8b03`, head is
  `97b60e06d42a`, migration not applied, no journal — the state round 1 left it in.

  **On the convention — adequate here, but it does not propagate.** The mechanism is right and the
  generality-by-convention choice is the correct trade-off for this fix; a name-specific filter
  would have been worse. Two observations, neither blocking:
  - **Discoverability is the real weakness.** The convention is documented only in `env.py`. The
    person who needs it — someone writing a raw-SQL bookkeeping table *inside a migration* — reads
    `architecture/30_migrations.md`, which has a "Seeding required reference data in migrations"
    section and a "Migration review checklist" and mentions neither `_journal`, `include_object`,
    nor migration-owned tables (grep across all of `architecture/` returns zero hits). A future
    `backfill_log` or `migration_audit` gets no protection and fails exactly as this one would
    have. **I do think it belongs in the migrations contract** — two lines under the seeding
    section would close it. Phase 4 already owns the journal's retirement and is the natural home;
    not a reason to hold phase 3.
  - `env.py:20-30` documents the marker clearly enough on its own terms — a reader of the filter
    understands the suffix is deliberate, not coincidence. That half of the question is fine.

  **F2 — CLOSED, and the FK claim verified first-hand, not inherited.** Against the live database:
  `user_shift_state_records` carries exactly three foreign keys (`changed_by_id`, `user_id`,
  `workspace_id`, all to `client_id`, all `ON DELETE RESTRICT`); `reason` is
  `character varying(512)` with `has_fk = false`. Exactly two FKs in the schema reference
  `pause_reasons` — `step_state_records.pause_reason_id` and
  `user_declared_state_records.pause_reason_id`. This matches the model
  (`models/tables/users/user_shift_state_record.py:33`, a bare `mapped_column(String(512))`).
  The corrected docstring at `test_prefix_branch_post_backfill.py:18-28` states all five things
  accurately: no FK, nothing referential prevents a stale or foreign id, only writer-side workspace
  validation does, the resolving-`par_` shape is measured not guaranteed, and the branch is defence
  rather than dead code. Greps for `cannot dangle` / `never hard-deleted` / `neither be foreign nor
  dangle` find the phrasing surviving in exactly one place — line 277 of this file, inside the
  round-0 entry, which is history and correctly left alone. Minor: the round-1 claim at line 478
  ("no ... phrasing survives anywhere in the phase's files") is literally overstated by that one
  occurrence, but the very next sentence names it as retained history, so the record is not
  misleading. The operator-owned review prompt's "the FK raises" instruction still carries the
  error; the round-1 entry discloses that and correctly did not edit it.

  **F3 — CLOSED.** `INTENTION_system_transition_reasons_20260730.md:311-329` records criterion 4 as
  an explicit partial completion, not a closure by implication: clause (b) satisfied on the
  provably-dead arm, clause (a) stated as **NOT satisfied and not reachable**, both blocking
  constraints named (272 legacy slug strings beside 58 `par_…` ids; the suppression behaviour is
  the published three-way `reason_text` contract, floor-app handoff §5.3/§4), and a closing
  instruction to downstream readers to treat it as **met-in-part**. A reader landing on that
  criterion alone cannot come away thinking it fully met — the heading itself says
  "closed on ONE arm only".

  **T9 commit hygiene — clean.** `git log --stat` on `3698a70` shows two files (`app/migrations/env.py`,
  `test_prefix_branch_post_backfill.py`); on `e51e1fd`, two files (this plan, the intention).
  Nothing outside phase 3's working set was staged. The master plan's last commit is `41271b6`,
  well before both, so the operator's edit was not swept in. (For the record: the parallel
  reassigned-steps workstream committed its own files as `213cac7` and `f512eb1` while this review
  was running — its own working set only, unrelated to phase 3.)

  **Suite not re-run — justified, and spot-checked.** `grep -rl "import alembic\|from alembic\|
  migrations.env\|command.upgrade"` over `app/tests/` returns nothing, and `conftest.py` has no
  alembic reference, so `env.py` does not execute under pytest. The autogenerate differential above
  is that file's behavioural test. The two documentation edits contain no executable change.

  **Verdict: `APPROVED`.** Phase 3 is done. The only carry-forward is the advisory above — put the
  `_journal` convention into `architecture/30_migrations.md` so it reaches the people who need it.

## Lifecycle transition

- Current state: `archived`
- Next state: `n/a` (APPROVED round 2, summarized and archived)
- Transition owner: `David`
