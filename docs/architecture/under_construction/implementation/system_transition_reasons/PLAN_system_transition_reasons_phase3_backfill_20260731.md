# PLAN_system_transition_reasons_phase3_backfill_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase3_backfill_20260731`
- Status: `under_construction`
- Owner agent: `claude-fable-5 (implementer)`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T18:20:00Z`
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

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
