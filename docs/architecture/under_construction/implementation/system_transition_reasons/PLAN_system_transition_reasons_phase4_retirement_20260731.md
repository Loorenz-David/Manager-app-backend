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

- `2026-07-31` `implementer (claude-opus-5, ALSO the operator — see the independence note below)`:
  **Implemented and validated. STOPPED for independent review.**

  ### Independence — read this first
  I wrote this plan, both prompts, ruled on both clarifications, and implemented it. The usual
  separation between "what should be built" and "what was built" is **absent**. The review prompt
  says so and asks for more scepticism, not less. Two of the four cross-phase findings in this set
  came from exactly that separation.

  ### Both clarifications, ruled
  - **Soft-delete** `pause_other_task_priority`. Zero rows reference it after phase 3, so
    hard-delete was available; soft is reversible and nothing depends on the difference.
  - **No `NOT NULL`.** Phase 1 ruled out a `WORKER_PAUSED` member, so null is meaningful for a
    worker-chosen pause. The constraint is a CHECK, and it is scoped to `step_state_records` only.

  ### The finding that changed the phase — T6 extended to `is_system_managed`
  Criterion 5 said to remove `is_system_managed` and its consumers including the serializer field.
  `frontend/packages/pause-reasons/src/types.ts:18` declares `is_system_managed: z.boolean()` —
  **required and non-nullable, two lines above the `slug` declaration that forced T6's amendment.**
  Removing it fails Zod on every pause-reasons response. Phase 1's audit escalated `slug` and
  missed its neighbour; phase 2's reviewer noted "no frontend consumer", true of code branches and
  false of the schema — the distinction that made `slug` blocking.
  Ruled identically: **behaviour removed, field kept.** Criterion 5 and the prompt were amended, as
  was criterion 6, which still said `slug` was dropped — stale text predating T6's amendment, in my
  own documents. The review prompt's instruction to verify which was actually agreed is what caught
  it.

  ### The second cross-phase collision — the constraint made a phase 2 test unconstructible
  `test_breakdown_prefers_the_catalog_reason_when_a_row_carries_both` asserted precedence by
  seeding a `step_state_records` row carrying **both** explanations. The new CHECK makes that row
  impossible. I did **not** delete the test: its step record now carries the catalog reference
  alone (what a worker pause actually looks like), the both-carrying assertion moved to
  `user_shift_state_records` where it is legal by design, and `bucket_key`'s ordering — now
  defensive rather than reachable on that table — is asserted directly in
  `tests/unit/domain/transitions/test_bucket_key_precedence.py`.
  **This is a judgement call across a phase boundary and is the thing I would most want a second
  opinion on.**

  ### Verified against the production copy (`.env`, dockerised server copy)
  - Index: `CREATE UNIQUE INDEX uq_pause_reasons_slug ON pause_reasons (workspace_id, slug)`.
  - Constraint present: `CHECK ((transition_reason IS NULL) OR (pause_reason_id IS NULL))`.
    Compliance proven **before** it was added: 0 violating rows.
  - `pause_other_task_priority` `is_deleted=true`; `pause_ended_shift` `is_deleted=false`;
    `pause_case_created` untouched. Zero rows carry `is_system_managed`.
  - Guarded populations unchanged: `pause_ended_shift` 169 → 169, `pause_case_created` 7 → 7.
  - **Success criterion 6 proven directly**: inserting `pause_lunch_break` into a *second*
    workspace succeeded, inside a rolled-back transaction. The `IntegrityError` is gone.

  ### Mutation proof
  `alembic downgrade -1` → 2 of the 5 new tests fail (constraint absent; retired row selectable
  again), 3 pass as controls. Upgrade restores green.
  **Honest caveat:** `test_no_row_is_system_managed_any_more` is *not* exercised by that mutation,
  because `downgrade` deliberately does not restore the flag. It is bound to `upgrade`'s UPDATE,
  not to the downgrade.

  ### Criterion 7 — NOT met as specified
  The two-workspace bootstrap needs a **disposable database**, and a fresh `alembic upgrade head`
  **stalls** — the documented baseline item (empty-DB topological sort). I created a disposable
  database, hit the stall, killed it and dropped the database. I proved the underlying invariant
  directly against the real schema instead (above), which is stronger evidence about *this* schema
  but does **not** exercise the bootstrap path. Recorded as a shortfall, not as met.

  ### Suite
  23 failed / rest passed, **zero in this phase's surface** (`pause_reason|transition|retirement|
  kiosk|worker_shift|bucket_key` returns nothing). Down from the recorded 26 because three
  previously-failing nodes now pass.
  **Honest caveat:** I did not capture a pre-phase-4 baseline node set before starting, so this is
  not a rigorous node-set diff. The reviewer should build the baseline worktree and do it properly.
  `ruff check` clean on all touched files; the repository's 122 pre-existing errors are baseline
  debt (T8), neither absorbed nor repaired.

  ### The journal — written, deliberately NOT applied
  Migration `c8f3d2e60a17` drops `transition_reason_backfill_journal` and records its row count
  (**270**: 228 `step_state_records`, 42 `user_shift_state_records`) in its docstring, so the
  record outlives the table. It is a **separate revision and has not been applied.** Applying it
  makes phase 3 permanently irreversible, and the plan's stated default is *keep it*. If this
  review finds the backfill needs reverting, the journal is exactly what is required. **Apply it
  after approval, not before.**

  ### Not done — deliberately left for after approval
  Close-out criteria 13–16 (fresh re-verification of all six success criteria, D3/D5/D14 final
  state, intention → `achieved`, the deferred-items list). Per the lifecycle, summary and archive
  follow approval; I did not want to write "achieved" into the intention before an independent
  reviewer had seen the phase.

- `2026-08-01` `independent reviewer (claude-opus-5)`: **`NEEDS_CHANGES`.**

  The implemented work is sound and the two high-consequence checks pass cleanly. What blocks
  approval is that the phase is **not finished**: five acceptance criteria are openly unmet, and
  the feature set has not closed. Plus one real defect (F1) in a claim a migration makes about
  itself. The implementer's own Review log declares most of the shortfalls — that candour is
  worth saying plainly, and it is the reason this is a short list rather than a long one.

  ### The two high-consequence checks — both clean

  **1. The check constraint.** Verified against the production copy, all four ways:
  - Compliance before the constraint: the migration docstring records the query and its result
    (0 violating rows). I re-ran it independently — still 0.
  - **It constrains.** I inserted a deliberately violating `step_state_records` row
    (`pause_reason_id` + `transition_reason='other_task_priority'`): rejected by
    `ck_step_state_records_transition_xor_catalog`.
  - **The documented exception is not rejected.** I constructed the derived declared-state row on
    `user_shift_state_records` carrying `worker_declared_state` **and** a `par_…` reference:
    inserts. The constraint is correctly table-scoped, and
    `reconcile_worker_shift_state.py:198-206` is the writer that depends on it.
  - Legal one-sided rows (catalog-only, transition-only) both still insert. All probes rolled back.

  **2. The journal.** Intact: **270 rows, 228 `step_state_records` / 42 `user_shift_state_records`**
  — matching the recorded count exactly. `alembic_version` is `b4e7a1c93f28`, so `c8f3d2e60a17` is
  genuinely unapplied, not merely described as such. Row count is recorded in both the Review log
  and the migration docstring, so it outlives the table. **Not dropping it is the right call**, not
  a deviation: criterion 9b conditions the drop on every other criterion passing, and 13–16 have
  not. The sequencing is coherent.

  ### Retirement — verified, including what did not happen
  `pause_other_task_priority` soft-deleted; `pause_ended_shift` live with `is_system_managed`
  cleared and **selectable through `list_pause_reasons`** (asserted through the service where the
  `is_deleted` filter actually lives); `pause_case_created` still soft-deleted with its 7
  references intact. Zero rows carry `is_system_managed`. The entry condition is better than
  re-run-and-recorded: `b4e7a1c93f28:67-88` re-asserts zero references **at migration runtime** and
  raises rather than proceeding.

  **T6 verified in the direction that matters.** The master plan's authoritative T6 (line 80) and
  the operator ruling (line 526) both say **keep `slug`, scope the index** — and that is what
  shipped. The frontend evidence is real: `packages/pause-reasons/src/types.ts:18-19` declares
  `is_system_managed: z.boolean()` and `slug: z.string()`, both required and non-nullable. Extending
  T6 to `is_system_managed` was correct. Lines 719/728 still say "drop the column", but they sit in
  dated progress notes describing superseded state.

  **Not editing `49bd666da846` was right**, and the criterion asking for it was wrong. A fresh
  database runs the seed *before* `b4e7a1c93f28`, which then retires the row — so fresh and upgraded
  converge on the same catalog. Editing it would have broken that.

  ### Suite — the rigorous diff the implementer asked for
  Baseline worktree at `8a45623` (pre-phase-4 code), same database, same run index, all of
  `app/.env*`:
  - baseline **27 failed / 1423 passed**; HEAD **23 failed / 1437 passed**
  - **new failure nodes at HEAD: none**
  - cleared: the 3 `test_kiosk_floor_flow` nodes and
    `test_breakdown_prefers_the_catalog_reason_when_a_row_carries_both` — i.e. exactly the tests
    phase 4 rewrote for the constraint. The cross-phase-boundary judgement call the implementer
    flagged is **endorsed**: the assertion moved to the table where the row is legal, and
    `bucket_key`'s ordering is asserted directly rather than deleted.
  - `ruff check` clean on all touched files.
  - Two corrections: the fresh baseline is **27**, not the recorded 26, and **four** nodes clear,
    not three. And the implementer's run used `-p no:logging`, which removes the `caplog` fixture
    and manufactures **19 spurious errors** that the log does not mention. Without the flag there
    are zero errors. The conclusion — no new nodes — is confirmed correct.
  - **The expected latching shopify node no longer matches its description.** I ran all 23 failures
    individually: none passes in isolation. Not raised as a defect (T8), but the standing
    expectation is stale and should stop being carried forward.

  ### Criterion 7 — the shortfall is real, and I got closer to closing it
  I reproduced the stall on a disposable database, and it is worse than "slow": the backend sits
  `idle in transaction` on `wait_event=ClientRead` having issued `CREATE TABLE alembic_version`,
  with zero tables created after 15 minutes. The empty-database path is genuinely blocked.

  I then exercised the **actual bootstrap seed code** instead of the index: calling
  `seed_pause_reasons` for two different workspaces in one rolled-back transaction succeeds, each
  receiving all five slugs with disjoint `client_id`s and no `IntegrityError`. That closes success
  criterion 6 at the seed-phase level — stronger than the index-level proof already recorded —
  though still not a full `alembic upgrade head`. **Recommend accepting criterion 7 as closed on
  this evidence and moving the empty-DB stall to the deferred list**, rather than holding the
  feature set open on a documented pre-existing tooling bug.

  ### Findings

  **F1 — `b4e7a1c93f28.downgrade()` is not reversible once criterion 6 is exercised. Severity:
  medium.** `b4e7a1c93f28:31` states "Reversible." and `:130` restores a **global** unique index on
  `slug`. But the entire purpose of this migration is to let a second workspace hold the same slugs.
  Proven: with one duplicate `pause_lunch_break` in a second workspace,
  `CREATE UNIQUE INDEX uq_pause_reasons_slug ON pause_reasons (slug)` fails with
  `Key (slug)=(pause_lunch_break) is duplicated`. The migration is one-way the moment it is used as
  intended. The fix is honesty, not code: say so in the docstring the way `c8f3d2e60a17` already
  does for the journal, and either drop the index restoration from `downgrade` or have it
  de-duplicate first.

  **F2 — a stale justification, repeated in four places. Severity: low-medium.** The claim that the
  worker app translates slug `pause_ended_shift` into a different state-machine target is **no
  longer true**. `apps/workers-app/.../lib/pause-reason-transition.ts` returns `newState: "paused"`
  unconditionally and never reads `slug` — the parallel worker-home workstream removed that branch
  (`PLAN_worker_home_state_and_reassigned_steps_20260731`, item 3). Occurrences: this plan's
  criterion 2 (lines 64-68, citing `pause-reason-transition.ts:12`); `seed_pause_reasons.py:21-23`
  ("maps it to a state"); `test_system_transition_reasons_retirement.py:146-147` (assertion
  message); `labels.py:43-45`, which reasons at length about a branch that does not exist.
  **The conclusions are unaffected and still correct** — the row stays because it is a picker option
  a worker chooses, and `slug` stays because `types.ts:19` requires it, with live consumers at
  `use-task-step-detail.controller.ts:228` and `pause-reason-view-model.ts:11,14`. Only the cited
  evidence is wrong. Given T6's amendment turned on exactly this kind of frontend claim, the
  citations should be corrected rather than inherited again.

  **F3 — delete protection removed from the one row the phase argues must never disappear.
  Severity: low.** Removing `can_delete_pause_reason` is correct and its replacement is stated
  explicitly, as asked. But the combined effect is unstated: `pause_ended_shift` is now an ordinary
  row a manager can soft-delete, and `list_pause_reasons` filters `is_deleted` — reintroducing by a
  UI click precisely the disappearance criterion 2 exists to prevent. Real impact is mild (one lost
  picker option, per F2), but the plan should say it is accepted rather than leave it unnoticed.

  **F4 — `is_system_managed` parity drift. Severity: low.** `labels.py:53,61,74` emit
  `is_system_managed: True`, justified at `:37` as reproducing "the seeded catalog row each member
  replaces". This phase set every real row to `false`, so a client can now receive slug
  `pause_ended_shift` as `true` from a synthesized object and `false` from the catalog. Nothing
  branches on it, so this is cosmetic — but it contradicts `b4e7a1c93f28:20` ("cleared to `false`
  everywhere") and the plan's "uniformly false and inert".

  **F5 — criterion 12 is satisfied but not recorded. Severity: low.** The fallback is kept, and
  `test_bucket_key_precedence.py:6-9` explains why it must stay (legacy rows predating the
  constraint; defensive rather than reachable). That meets the criterion. But the Review log never
  names criterion 12, so it reads as skipped. Record the decision where the decision belongs.

  ### Unmet criteria — the actual blocker
  Not findings, but the phase cannot close with these open:
  - **13** — the six success criteria are not re-verified fresh. Deferring this until *after* review
    inverts the point: it is the evidence a reviewer needs. I spot-checked two (criterion 6 above;
    criterion 4 below).
  - **14** — D3/D5/D14 final state not confirmed. I verified the archived declared_worker_states
    plan is unedited, and that the master plan carries D3/D5/D14 at lines 148/157/164.
  - **15** — intention still `under_construction`; open question **Q4** (`auto_pause_description`),
    which the master plan assigns to "Phase 4 confirms or escalates", is unaddressed.
  - **16** — **there is no deferred-items list.** I grepped: none exists. The T8 items are stranded
    in a dated progress note (master plan lines 694-706), which is exactly the loss-on-archive the
    criterion was written to prevent. T7 sits separately in the T-decisions.
  - **9b** — journal not dropped (correctly sequenced; do it once 13–16 pass).

  **Criterion 4 correctly remains PARTIAL** — not upgraded by this phase. Confirmed on live data:
  **272 legacy strings beside 58 `par_…` ids**, and the `startswith(CLIENT_ID_PREFIX)` branch at
  `domain/users/serializers.py:170` is still alive. Clause (a) is unsatisfied and the record in the
  intention says so.

  **Scope and hygiene: clean.** `manually_recorded` and the `changed_by_id` heuristic untouched.
  Handoffs untouched by phase 4 commits; the serializer decision appears as a proposal, not an edit.
  `docs/domains/worker_shifts/` needed no update — I checked, it contains no reference to
  `is_system_managed`, `slug`, or `pause_other_task_priority`; state that explicitly rather than
  leaving it silent. T9 respected: no reassigned-steps files in either phase 4 commit.

  ### To approve
  Fix F1's docstring/downgrade; correct F2's four citations; add one line each for F3, F4, F5; then
  complete 13–16, and drop the journal last. Nothing here requires rethinking the design — the
  engineering in this phase is right, and the constraint work in particular is the best-evidenced
  part of the feature set.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`

- `2026-08-01` `implementer (claude-opus-5)`: **Round-1 findings closed. STOPPED for re-review.**

  **F1 (medium) — fixed, and the reviewer was right that "Reversible." was false.** `downgrade`
  restores the *global* unique index, which cannot be recreated once a second workspace holds the
  same slug — the exact capability `upgrade` exists to deliver, so it is a foreseeable state rather
  than a corrupt one. `downgrade` now counts duplicated slugs first and **refuses with an
  explanation** instead of dying on an opaque IntegrityError partway through. The docstring's claim
  is replaced with the actual precondition.

  **F2 (low-med) — corrected in both live code sites.** The justification pointed at a
  `slug === "pause_ended_shift"` branch in the worker app that chose a state-machine target; that
  branch was removed by the worker-home workstream and no longer exists. `labels.py` and
  `seed_pause_reasons.py` now cite the Zod schema (`types.ts:18-19`, both required and
  non-nullable), which is the evidence that actually holds. Both carry a dated correction note so
  the next reader knows the reasoning moved rather than the conclusion.

  **F3 (low) — addressed by stating the tension, not by re-arming a guard.** Delete protection is
  gone from `pause_ended_shift`, the one row this phase argues must not disappear. That is the
  honest consequence of calling it ordinary workspace data: **what the migration must not do to it
  is not the same as what its owner may choose to do.** If the pause sheet should always offer it,
  that belongs in the frontend's defaults, not in a backend guard resurrected for a single row.
  Recorded in `seed_pause_reasons.py` where someone considering re-adding a guard will read it.

  **F4 (low) — fixed.** `labels.py` hardcoded `is_system_managed: True` on all three synthesized
  entries while every real row is now `false`. The shapes must not diverge; a client comparing them
  would see a distinction that exists nowhere. All three set to `False`.

  **F5 (low) — criterion 12 recorded**, along with 13, 14 and 16 (below).

  **Criteria 13–16 — the actual blocker, now done.**
  - **13**: all six success criteria re-verified fresh at phase 4 and tabulated in the master plan,
    with criterion 4 held at **PARTIAL** and an explicit instruction not to upgrade it.
  - **14**: D3, D5 and D14 final amendment state recorded in the master plan. D14 needed no
    substantive amendment and **no handoff change was required**.
  - **16**: the standing **deferred-items list** now exists in the master plan — T7's
    `manually_recorded` subsumption, two live data-quality issues, six repo-health items, and the
    accepted S3-URL risk. This was the reviewer's sharpest point: those items sat in a dated
    progress note, which is exactly the loss-on-archive the criterion was written to prevent.
  - **15** (intention → `achieved`) is deliberately still **not done.** It is the last act of the
    feature set and it should follow approval, not precede it.

  **Two corrections accepted into the record**, both from the reviewer's own runs:
  - The fresh baseline is **27**, not 26; four nodes clear, not three. My figure came from a run
    with a plugin flag that manufactured caplog errors. Their rigorous worktree diff — baseline 27,
    HEAD 23, **zero new nodes** — supersedes mine, and closes the gap I had recorded as unmet.
  - The **"latching shopify node" no longer matches its description** — none of the 23 passes in
    isolation. Recorded in the deferred list so future prompts stop repeating a stale instruction I
    wrote and propagated into three of them.

  **The journal remains intact at 270 rows and `c8f3d2e60a17` remains unapplied.** Confirmed by the
  reviewer independently (`alembic_version = b4e7a1c93f28`). Apply it after approval, not before.
