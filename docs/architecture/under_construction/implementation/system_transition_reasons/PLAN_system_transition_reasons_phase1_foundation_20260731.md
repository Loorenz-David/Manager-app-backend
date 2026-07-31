# PLAN_system_transition_reasons_phase1_foundation_20260731

## Metadata

- Plan ID: `PLAN_system_transition_reasons_phase1_foundation_20260731`
- Status: `under_construction`
- Owner agent: `<implementer>`
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Master plan: `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal and intent

- Goal: establish the evidence, the vocabulary, the schema, and read tolerance — in that order,
  within one phase — so that phase 2 can cut every writer over in a single pass.
- Business/user intent: nothing here changes observable behaviour. Nothing writes
  `transition_reason` yet, so every existing response stays byte-identical. That is what makes this
  phase safe to deploy on its own and safe to review in one pass.
- Non-goals: no writer changes; no backfill; no constraints; no catalog changes; no
  `manually_recorded` work (T7 — deferred).

## Scope

- In scope: the inventory (step A); `TransitionReasonEnum`; nullable `transition_reason` on
  `step_state_records` and `user_shift_state_records`; the additive migration; the shared label map;
  read tolerance across every path the inventory finds.
- Out of scope: `UserDeclaredStateRecord` (T3 — no column); every writer;
  `get_system_pause_reason_id` (still live, still called — phase 2 removes its callers);
  `manually_recorded` and the `changed_by_id` heuristic (T7 — touching either is a scope violation).
- Assumptions: declared_worker_states Phase 7 is archived.

## Clarifications required

- [ ] **Which database are the inventory figures taken from, and is it representative of
      production?** Blocks because phase 3's backfill strategy is chosen from these numbers.
- [ ] **Does a worker-chosen step pause need a `WORKER_PAUSED` member**, or is the catalog reference
      alone sufficient? Decides whether `transition_reason` is "system transitions only" (null for
      worker-chosen pauses) or "every transition typed". Cheap now, expensive after phase 2.
      Record the ruling and its reasoning.
- [ ] **Where does the shared label map live**, given `01_architecture.md:43` forbids
      `services/queries/` importing `services/infra/`? A prior feature set's operator proposed
      exactly that and was corrected by review. Likely `domain/`.

## Acceptance criteria

### Step A — inventory (do this first; it defines the rest of the phase)

1. **Read-path audit**: an exhaustive `file:line` list of every location that resolves a
   `pause_reason_id` into a label, name, or map — services, serializers, analytics composers,
   migrations. Audit from the model **outward** (inbound references to `PauseReason` and
   `pause_reason_id`), not by guessing at call sites. **This list is the checklist for step D**; a
   path missed here ships broken in phase 2. It must contain the three runtime call sites the
   intention names (`_clock_worker_shift.py:200`, `transition_step_state.py:274`,
   `_step_transition_core.py:114`) — their absence proves the method was wrong.
2. **Volume report**: total `step_state_records`; how many carry a non-null `pause_reason_id`; how
   many point at each of the three system rows (`pause_ended_shift`, `pause_other_task_priority`,
   `pause_case_created`); the same split for `user_shift_state_records.reason` by "looks like a
   `par_…` id" vs free text vs null; total `user_declared_state_records`. Each figure with the query
   text and the database it came from.
3. **Per-workspace distribution**: how many workspaces hold any `pause_reasons` row, and how many
   hold each system slug. (Intention expects 3132 / 1 — confirm or correct.)
4. **Out-of-repo slug-consumer audit (T6)**: search handoff documents, export/report code, webhook
   payload builders, and API response shapes for anything surfacing `pause_reasons.slug`. The
   operator ruled "drop the column" *conditional on this finding nothing*. **Escalate rather than
   proceed if it finds a consumer.**
5. **Label-resolution strings**: for each of the three system rows, the exact human-visible string
   historical data resolves to today. Phase 3 must reproduce these; master-plan success criterion 5
   is unverifiable without them.
6. **Second-workspace `IntegrityError` confirmed or refuted by execution**, on a **disposable**
   database — not by inspection, and not against the shared database. If it does not raise, the
   intention's Finding 2 is wrong and must be corrected. Reporting that is success.

### Step B — vocabulary

7. `TransitionReasonEnum` in the domain layer, following existing enum conventions (lowercase
   values — see `ddc5bf50153b_rename_enum_labels_to_lowercase`). Members at minimum: `SHIFT_ENDED`,
   `OTHER_TASK_PRIORITY`, `WORKER_DECLARED_STATE`, plus whatever the clarification resolves.

### Step C — schema

8. Nullable, indexed `transition_reason` on `step_state_records` and `user_shift_state_records`. No
   default, no constraint. **No column on `user_declared_state_records`** (T3) — if you believe T3
   is wrong, STOP and escalate rather than adding it.
9. Migration is additive-only and reversible: `upgrade` adds, `downgrade` drops, no data touched.
   Verify `upgrade` → `downgrade` → `upgrade` leaves the schema identical.
10. Column type recorded in the Review log with reasoning — native PG enum vs constrained string.
    Note this repo has already paid to remove a native enum once (`b58cdffb5ccc` dropped
    `step_event_reason_enum`), which is evidence for the string+check approach.

### Step D — read tolerance

11. **Every** path from criterion 1 resolves a `transition_reason` row to a label, and a
    `pause_reason_id` row exactly as today. The audit list is the checklist — each entry ticked with
    its test.
12. Label resolution lives in **one** place and is imported. Duplicated maps are a finding.
13. **Precedence is explicit and tested**: if a row somehow carries both, which wins is asserted,
    not incidental. It should not happen after phase 2, but "shouldn't happen" is not a behaviour.
14. New behaviour proven by **seeding `transition_reason` rows directly in tests** — the only way to
    exercise it before writers exist. Each read path gets one.
15. The kiosk clock-out analytics `pause_by_reason` / `pause_reasons` contract (published, live)
    is unchanged, and every key still resolves — including the literal `"unspecified"` key, which is
    part of the published contract. Re-run its existing tests.
16. Query counts unchanged — resolution is from an in-memory map. Prove with a local SQLAlchemy
    listener; the shared `count_queries` fixture is broken.

### Whole-phase

17. **Zero behaviour change, proven**: no existing test modified, no endpoint response gains a
    field, no serializer surfaces the new column.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: layering — where the enum and the shared map live.
- `backend/architecture/03_models.md`, `04_migrations.md`: model and migration conventions.
- `backend/architecture/07_queries.md`, `46_serialization.md`: read-path conventions.

### File read intent — pattern vs. relational

- Permitted (relational): every file the inventory surfaces; `step_state_record.py`,
  `user_shift_state_record.py`, `user_declared_state_record.py` for exact fields; existing domain
  enums for conventions; `b58cdffb5ccc` / `ddc5bf50153b` for this repo's enum history.
- Prohibited (pattern): reading another model for column-declaration style (`03_models.md`), another
  serializer for output shape (`46_serialization.md`).

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`

## Implementation plan

1. Answer the database clarification. Run step A in full and record it in the master plan under
   "Phase 1 inventory", with query text.
2. If step A's slug audit finds a consumer, STOP and escalate before continuing.
3. Resolve the `WORKER_PAUSED` and label-map-location clarifications; record both rulings.
4. Add the enum; add the columns; generate the additive migration.
5. Walk the audit list in order: add `transition_reason` resolution, keep `pause_reason_id`
   untouched, add a seeded test per path.
6. Assert precedence; re-run the kiosk contract tests; prove query counts unchanged.
7. Prove zero behaviour change.
8. Review log entry: both rulings, the column-type reasoning, and the audit list with each entry's
   test. STOP for independent review.

## Risks and mitigations

- Risk: a read path missed in step A fails in phase 2 — in production, on the deploy meant to *fix*
  an outage.
  Mitigation: criterion 1 fixes the audit method (model-outward); criterion 11 binds step D to it
  literally; the reviewer is told to re-derive the audit independently rather than trust the list.
- Risk: the new branch is never exercised because nothing writes the column, so tests pass
  vacuously.
  Mitigation: criterion 14 requires directly seeded rows; the reviewer should mutate the resolution
  and confirm tests fail.
- Risk: inventory figures from the shared dev database are mistaken for production.
  Mitigation: criterion 2 requires the database named alongside every figure.
- Risk: the disposable-database test is run against the shared database and damages it.
  Mitigation: criterion 6 says disposable; if none can be provisioned, STOP.
- Risk: a native PG enum makes every future member a migration and is costly to remove.
  Mitigation: criterion 10 forces an explicit recorded choice.

## Validation plan

- Every inventory figure reproducible from its recorded query text.
- Every audit entry has a passing test seeding `transition_reason` directly.
- Existing responses byte-identical; existing tests unmodified.
- `alembic upgrade head` → `downgrade -1` → `upgrade head`: schema identical.
- Query-count listener shows no new round trips.
- Full suite: no new failure nodes vs. baseline — compare **node sets**, not counts. A baseline git
  worktree needs `app/.env.testing` copied in (`.gitignore` excludes `app/.env.*`), or it reports
  wildly inflated failures. Verify config parity with a small smoke run in both trees first.
- `ruff check` clean on touched files.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
