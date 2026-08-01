# PLAN_ended_shift_step_state_collapse_20260801

## Metadata

- Plan ID: `PLAN_ended_shift_step_state_collapse_20260801`
- Status: `archived`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-08-01T00:00:00Z`
- Last updated at (UTC): `2026-08-01T11:30:00Z`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_ended_shift_step_state_collapse_20260731.md`
- Predecessor set: `MASTER_PLAN_system_transition_reasons_20260731.md` — **phases 1–4 must be
  archived before this plan begins.** It reads `transition_reason` on historical rows, which
  phase 3 backfills.

## Goal and intent

- Goal: remove `TaskStepStateEnum.ENDED_SHIFT`. A step that stops because a shift ended is
  `PAUSED`; *why* it stopped is carried by `transition_reason` (system) or `pause_reason_id`
  (the worker's choice).
- Business/user intent: `ENDED_SHIFT` is a **state encoding a reason** — the same category error
  the predecessor set removed from the pause catalog. "The worker ended their shift" is a fact
  about the worker, already recorded on `UserShiftStateRecord`. Duplicating it into the step's
  state vocabulary forces a fake choice into the worker's pause sheet, where picking a *reason*
  silently changes the *state-machine target*.
- Non-goals:
  - `UserShiftStateEnum.ENDED_SHIFT` is untouched. That is the worker's shift state and the
    correct home for the concept.
  - Clock-out's behaviour is unchanged (E1). No step is force-closed that is not force-closed today.
  - `total_ended_shift_seconds` / `total_ended_shift_count` are **kept**, with their names and
    meanings. Only their derivation changes.
  - `domain/task_steps/aggregate_metrics.py` is dead code (E3). Deleting it is a separate cleanup.

## Scope

### In scope

1. A derived bucket key at the two places that read a record's state as an analytics label.
2. The clock-out writer emitting `PAUSED` instead of `ENDED_SHIFT`.
3. The enum migration and the historical **reclassifying** backfill (E2).
4. Subtractive removal of `ENDED_SHIFT` from four membership sets and the state machine.
5. Frontend: delete `pause-reason-transition.ts`, simplify its two call sites.
6. Handoff update — `HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md` §6.1 already
   documents this as pending; its liveness row flips when this ships (operator-owned).

### Out of scope

- Deleting `aggregate_metrics.py`. Dead, but deleting dead code inside an irreversible migration
  set adds review surface for no user-visible gain.
- The `pause_ended_shift` catalog row's existence. It **stays selectable** (E4).
- Any change to `manually_recorded` or the `changed_by_id` heuristic (predecessor T7).

### Assumptions

- Phases 1–4 of `system_transition_reasons` are archived. Historical `step_state_records` carry
  `transition_reason`; `SHIFT_ENDED` is populated on the clock-out path.
- Verified 2026-08-01 and binding on this plan:
  - `increment_step_time_metrics` has **zero callers** (E3).
  - `clock_out_shift_for_user` closes `WORKING` records only
    (`_clock_worker_shift.py:95-122`, `state == WORKING`) — the basis for E1.
  - `LinearInterval.transition_reason` is already populated
    (`_reconstruct_shift_middle.py:120-128`), so the timeline re-key has its input.

## Clarifications required

Both blocking questions are **resolved**; no clarification is open.

- [x] **Does clock-out force-close `PAUSED` steps?** — **No** (operator ruling, 2026-08-01). See E1.
- [x] **Reclassify or preserve historical worker-picked ended-shift rows?** — **Reclassify**
  (operator, 2026-08-01). See E2.

If a case arises that E1–E5 do not cover, escalate in the Review log and stop. Do not choose.

## Design decisions

Prefixed `E…` to avoid collision with the reassigned-steps set's `D1–D7` and the
transition-reasons set's `T1–T9`.

### E1 — Clock-out keeps closing `WORKING` steps only

**Operator ruling, 2026-08-01.** A `PAUSED` record measures **how long the item stood still for a
stated reason** — an item metric, not shift accounting. An item waiting three days on "waiting for
upholstery" has a three-day pause, and that number is the point. Force-closing it at clock-out
would destroy the measurement.

Consequences, both intended:

- A step paused by a worker and left open across the night accrues that whole span into
  `total_pause_seconds`, attributed to the chosen reason. **This is correct classification, not
  corruption** — and it is pre-existing behaviour for every pause reason today, not something this
  plan introduces.
- `total_ended_shift_seconds` is therefore narrower than "all off-shift time". It is the
  **unattributed** bucket: the item stopped because the shift ended and nobody said why — i.e. the
  system force-closed a step that was still `WORKING`.

Rejected: clock-out also closing `PAUSED` steps; splitting that into a preceding feature set. Both
were proposed during the ruling and both destroy the item-stillness metric.

### E2 — Historical rows are **reclassified**, not preserved

**Operator, 2026-08-01.** The backfill converts historical `ended_shift` rows so past and future are
measured the same way. Reports change retroactively; that is accepted, and it is the reason the
migration is irreversible.

Mapping — and the distinction that makes it correct:

| Historical row | Becomes | Bucket after |
|---|---|---|
| `state='ended_shift'`, `transition_reason='shift_ended'` (system clock-out) | `state='paused'`, reason unchanged | `ended_shift` — unchanged |
| `state='ended_shift'`, `pause_reason_id` set (worker picked it in the sheet) | `state='paused'`, `pause_reason_id` unchanged, **no** `transition_reason` written | **moves** to `pause`, attributed to the reason |
| `state='ended_shift'`, neither set | `state='paused'`, `transition_reason='shift_ended'` | `ended_shift` |

The third row is the judgement call: a pre-phase-2 clock-out wrote `ENDED_SHIFT` with no
`transition_reason`, and its meaning is unambiguously "the system stopped this". Typing it
preserves its bucket. **Do not** apply that default to a row carrying a `pause_reason_id` — that
would silently re-type a worker's choice as a system transition.

`task_steps.state='ended_shift'` → `'paused'`. The step table carries no reason column; a step
whose current state is a system-ended pause is indistinguishable from an ordinary paused step,
which already matches how a normally-paused step behaves.

### E3 — `aggregate_metrics.py` is dead; the real site is `compute_record_contributions`

The intention's original trace named `domain/task_steps/aggregate_metrics.py:17-25` as the
bucketing site. **Verified 2026-08-01: `increment_step_time_metrics` has zero callers.** Re-keying
it would change nothing while looking like the work was done.

The actual single point is `services/queries/analytics/averaged_time.py::compute_record_contributions`,
which selects `StepStateRecord.state.label("state")` (`:66`) under
`StepStateRecord.state.in_(_TIME_STATES)` (`:81`, constant at `:27`). Every consumer buckets on the
emitted `.state`. **Six consumers**, three of which the original trace missed:

| Consumer | Missed by the original trace? |
|---|---|
| `services/tasks/analytics/process_step_transition.py` | no |
| `services/queries/worker_stats/get_worker_daily_step_breakdown.py` | no |
| `services/queries/worker_stats/list_workers_totals.py` | **yes** |
| `services/queries/analytics/reconcile_user_time.py` | **yes** |
| `services/queries/analytics/estimation_sample.py` | **yes** |
| `services/queries/analytics/averaged_time.py` (self) | — |

Emit a derived bucket key at that one select and all six keep working untouched. This is the
highest-blast-radius line in the plan: wrong, and every analytics surface misbuckets silently.

### E4 — `pause_ended_shift` stays selectable; `pause-reason-transition.ts` still dies

The catalog row remains an ordinary workspace-editable pause reason with no special handling
anywhere (operator, 2026-07-31: *"if the user selected ended shift on pause reason for a task step,
that is precisely a pause reason, thus a pause state"*).

`pause-reason-transition.ts` is deleted regardless — not because the row goes away, but because it
maps a reason onto a state that ceases to exist. After this set, every pause reason produces
`new_state: "paused"`.

This also settles the predecessor set's open question: phase 4 kept the row selectable on an
**interim** justification (removing it would break the sheet). Under E4 the row is kept on its own
merit, and no further retirement is pending.

### E5 — The derived bucket expression is additive and inert before the migration

Both re-key sites use the same shape:

```
bucket = 'ended_shift'  when state = 'paused' AND transition_reason = 'shift_ended'
       = state          otherwise
```

Before the migration a clock-out row is `state='ended_shift'`, so the `otherwise` branch already
yields `ended_shift`. After it, the first branch does. **The expression is correct at every point
in the rollout**, which is what lets the readers ship before the writer and the migration.

`_TIME_STATES` must keep **both** `ENDED_SHIFT` and `PAUSED` until the migration lands, then drop
`ENDED_SHIFT`. Dropping it early makes historical rows vanish from every total.

## Acceptance criteria

1. No code path writes `TaskStepStateEnum.ENDED_SHIFT`; the member is gone from
   `task_step_state_enum` in the database and from the Python enum.
2. Clock-out with an open `WORKING` step produces `state='paused'`,
   `transition_reason='shift_ended'`, `pause_reason_id IS NULL`.
3. **Characterization, written first, asserting different things per path** (per the intention's
   amended criterion 3):
   - clock-out force-close → `total_ended_shift_seconds` / `_count` **equal** before and after;
   - worker-picked ended-shift pause left open overnight → the time **moves** to
     `total_pause_seconds`, attributed to the chosen reason.
4. A worker selecting any pause reason produces `state='paused'` with that `pause_reason_id`; the
   frontend sends no `new_state` other than `"paused"`.
5. The linear timeline still distinguishes "paused while present" from "off shift", for both new
   and reclassified historical rows.
6. Clocking in the morning after leaving a step open derives the worker to `idle`, not `in_pause`
   — the `entered_at_or_after` guard at `reconcile_worker_shift_state.py:172` becomes
   load-bearing here and needs its own test, not an inherited one.
7. All six `compute_record_contributions` consumers produce identical output for an unchanged
   scenario. Verified per consumer, not assumed from the shared helper.
8. `frontend/.../lib/pause-reason-transition.ts` is deleted and its two call sites simplified.
9. Reclassification is correct per E2's three-row table, including that a row carrying
   `pause_reason_id` is **never** given `transition_reason='shift_ended'`.
10. `total_ended_shift_seconds` / `_count` and `ended_shift_seconds` / `ended_shift_open_count`
    remain in every payload that carries them today — published contract, unchanged.

## Contracts and skills

### Read order

- `backend/architecture/<canonical>.md`, then `<canonical>_local.md` where present.

### Contracts loaded

Core, per `task_system/backend_contract_goal_mapping_guide.md`: `01`, `04`, `05`,
`06` + `_local`, `07` + `_local`, `09`, `21`, `40` + `_local`, `41` + `_local`, `42` + `_local`,
`48` + `_local`.

### Added from guide

- `03_models.md` + `30_migrations.md`: trigger — a native-enum change across two tables plus an
  irreversible backfill. **The highest-risk contract pair in this plan.**
- `46_serialization.md` + `_local`: the published `ended_shift` fields must survive verbatim.
- `22_performance.md`: the backfill touches every historical `step_state_records` row.
- `15_testing.md` + `50_testing_strategy.md`: characterization-first, and the six-consumer sweep.
- `25_soft_delete.md`: the backfill must not resurrect soft-deleted rows or skip live ones.

### Excluded contracts

- `55_query_filters_local.md`: no search surface.
- `11_infra_events.md`, `13_sockets.md`: no event shape changes — the step still transitions, and
  `task:step-state-changed` already carries the new state value.
- `47_notifications_local.md`: no notification change.

### Skill selection

- Primary: `skills/domains/content/add_command/SKILL.md` — the writer cutover and the migration.
- Secondary: `skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
- Excluded: `skills/domains/identity/*` — the worker's shift state is explicitly out of scope.

## Implementation plan

Ordered. Readers before writers before the migration — the same discipline the predecessor set's
T4 encodes, and for the same reason: at no point may a row exist that the readers cannot bucket.

### Step 1 — Characterization tests (no production change)

Cover the two paths of criterion 3, and at least one assertion per `compute_record_contributions`
consumer that has published output. Seed a step, close it both ways, assert the bucket totals.

These must **fail** if the derived key in Step 2 is wrong. Verify that by writing them first and
watching them pass against current code, then breaking Step 2 deliberately later.

### Step 2 — The derived bucket key (additive, inert)

`averaged_time.py::compute_record_contributions`: replace the emitted
`StepStateRecord.state.label("state")` with E5's `CASE` expression. Keep `_TIME_STATES` containing
both `ENDED_SHIFT` and `PAUSED`.

Same expression in `_reconstruct_shift_middle.py:120-128`, where `LinearInterval(state=row.state.value)`
becomes the derived value — `transition_reason` is already selected there, so no query change is
needed.

Run Step 1's tests. They must pass **unchanged** — this step is behaviour-preserving by
construction (E5).

### Step 3 — Six-consumer verification

For each consumer in E3's table, assert output is identical to pre-Step-2 for an unchanged
scenario. Three were missing from the original trace; treat all six as unverified until tested.

### Step 4 — Writer cutover

`_clock_worker_shift.py:203`: `new_state=TaskStepStateEnum.PAUSED`. `transition_reason` is already
`SHIFT_ENDED` there from the predecessor set — do not touch it.

New rows now take E5's first branch. Step 1's tests still pass; add one asserting a *new* clock-out
row buckets as `ended_shift` while carrying `state='paused'`.

### Step 5 — Frontend

Delete `pause-reason-transition.ts`. Both call sites
(`PauseReasonSheetPage.tsx:100,129`) send `new_state: "paused"` unconditionally; the
`requiresDescription` branch it also carried moves to reading `reason.requires_description`
directly. Cross-repo commit.

### Step 6 — Migration and reclassifying backfill

Per E2's table. `task_step_state_enum` is native and shared by `task_steps.state` and
`step_state_records.state`, so removing the member means recreating the type and rewriting both
columns.

**Measure volumes first**, workspace-scoped and with the suite quiescent, per the predecessor's
standing instruction. Do not size the batch from a global count.

Irreversible. This is the step that destroys history if the row selection is wrong.

### Step 7 — Subtractive cleanup

Only after Step 6. Drop `ENDED_SHIFT` from: `TIME_BEARING_STATES`
(`domain/task_steps/constants.py:14`), `_roster.py:25`,
`get_worker_working_sections.py:19`, `get_user_last_active_step_record.py:16`,
`_TIME_STATES` in both `averaged_time.py:27` and `get_worker_daily_step_breakdown.py:62`, and the
state machine (`transition_step_state.py:54-70`). Then the Python enum member.

All four membership sets already contain `PAUSED`, so this is subtractive with no behaviour change.

### Step 8 — Handoff and summary

`HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md` §6.1 already documents this as
pending. Propose the §6.1 rewrite and the liveness flip **in the Review log** — both
operator-owned. Do not edit the handoff.

## Risks and mitigations

- **Risk:** the derived bucket key is wrong and every analytics surface misbuckets silently. No
  test watches this today.
  **Mitigation:** Step 1 before Step 2; Step 3's per-consumer sweep; deliberately break the
  expression and confirm the tests fail.
- **Risk:** the backfill re-types a worker's choice as a system transition (E2 row 3 applied to
  row 2).
  **Mitigation:** criterion 9; assert on a seeded row carrying `pause_reason_id` that
  `transition_reason` stays null.
- **Risk:** `_TIME_STATES` loses `ENDED_SHIFT` before the migration, making historical rows vanish
  from every total.
  **Mitigation:** Step 7 is explicitly gated on Step 6.
- **Risk:** the morning-after `in_pause` regression (criterion 6). The guard exists but is
  currently redundant for this case and becomes load-bearing.
  **Mitigation:** its own test, not an inherited one.
- **Risk:** frontend and backend land out of order — a client sending `new_state: "ended_shift"`
  after the enum member is gone gets a `422`.
  **Mitigation:** Step 5 before Step 6. A client sending `"paused"` against pre-migration backend
  is already valid, so frontend-first is the safe order.

## Validation plan

| Check | Expected |
|---|---|
| Step 1 tests before Step 2 | pass against current code |
| Same tests after Step 2 | pass **unchanged** |
| Deliberately break the `CASE` expression | Step 1 tests fail |
| Per-consumer output diff (6) | identical for an unchanged scenario |
| Clock-out integration | `state='paused'`, `transition_reason='shift_ended'`, buckets `ended_shift` |
| Worker-picked ended-shift pause overnight | buckets `pause`, attributed to the reason |
| Clock in the morning after | worker derives `idle` |
| Backfill on seeded historical rows | E2's three-row table exactly; `pause_reason_id` rows keep null `transition_reason` |
| `grep -rn "ENDED_SHIFT" app/beyo_manager` | `UserShiftStateEnum` hits only |
| `pytest -q` from `backend/app`, default plugins | no new failure nodes vs. baseline; **reject any run with non-zero errors or failures in the hundreds** — see the predecessor master plan's "Validation baseline" for the three known traps |

## Review log

- `2026-08-01` `planning session`: authored after the operator resolved both blocking questions.
  Recorded two corrections to the intention's traced evidence: `aggregate_metrics.py` is dead code
  (E3), and three of the six `compute_record_contributions` consumers were unlisted. Verified
  `clock_out_shift_for_user` closes `WORKING` only (the basis for E1) and that
  `LinearInterval.transition_reason` is already populated (the timeline re-key has its input).

- `2026-08-01` `implementation session`: steps 1–7 implemented in plan order. **Awaiting independent
  review — no summary written, no archive, no handoff edited.**

  ### Criterion 7 — the six consumers, verified per consumer

  Each has its own test in
  `tests/integration/services/queries/analytics/test_ended_shift_bucket_collapse.py`, asserting
  explicit values rather than inheriting a result from the shared helper. All six were treated as
  unverified regardless of whether the original trace listed them.

  | # | Consumer | Test | What it asserts |
  |---|---|---|---|
  | 1 | `services/queries/analytics/averaged_time.py` (self) | `test_clock_out_force_close_stays_in_the_ended_shift_bucket` | the emitted `.state` is `ended_shift`, and no `paused` contribution appears |
  | 2 | `services/tasks/analytics/process_step_transition.py` | same test | `total_ended_shift_seconds=54000`, `_count=1`, `total_pause_seconds=0` |
  | 3 | `services/queries/analytics/reconcile_user_time.py` | `test_reconcile_user_day_time_buckets_the_clock_out_span_as_ended_shift` | the worker's day row: `total_ended_shift_seconds=54000`, `total_pause_seconds=0` |
  | 4 | `services/queries/worker_stats/get_worker_daily_step_breakdown.py` | `test_daily_step_breakdown_buckets_the_clock_out_span_as_ended_shift` | `totals.ended_shift_seconds` **and** the per-step `contribution` |
  | 5 | `services/queries/analytics/estimation_sample.py` | `test_estimation_sample_buckets_the_clock_out_span_as_ended_shift` | the `(section, "ended_shift")` sample key, which is a key in a published estimate |
  | 6 | `services/queries/worker_stats/list_workers_totals.py` | `test_list_workers_totals_reports_an_open_clock_out_record_as_ended_shift` | the live `running` slice — the only consumer reading **open** records — and its published `ended_shift_seconds` / `ended_shift_open_count` |

  Verified by a **second, different route**: rather than re-running the same grep over call sites,
  the set was re-derived from the *output keys*. `grep -rn '"ended_shift"' beyo_manager scripts`
  returns 38 sites; every one is a bucket-dict key, a published field name, a type comment, or
  `UserShiftStateEnum` — no unlisted consumer of `compute_record_contributions.state` exists. That
  sweep also turned up the two omissions below.

  Emptiness of the sweep was checked, not assumed: corrupting the `CASE`'s `else` branch fails 6 of
  the module's tests, and after the writer cutover corrupting the *first* branch fails 8. Before the
  cutover the first branch is genuinely inert (E5), so that check is only meaningful once step 4 has
  landed — it was re-run there, not only at step 2.

  ### Two sites the plan's step 7 and E3's table both missed

  Found by the output-key route, not by the symbol grep:

  - **`scripts/backfill/backfill_worker_shift_state_records.py:91-102`** builds `LinearInterval`s
    from step records exactly as `_reconstruct_shift_middle` does, and at `:136` reads an
    `ended_shift` segment as *"the shift ended here"* to place the day's end marker. Its
    `_TIME_STATES` **did** include `ENDED_SHIFT` (unlike the rebuild's), so before this change it
    saw those records directly. Left alone, the collapse would have turned that span into an
    ordinary `IN_PAUSE` segment and the backfilled shift would never have ended at the right
    instant — silently, on a script whose whole job is repairing history. It now goes through the
    same `bucket_for`. **This is a third re-key site; the plan named two.**
  - **`scripts/backfill/backfill_averaged_time.py:37`** holds a third copy of `_TIME_STATES`.
    Subtractive, like the others, but absent from step 7's list.

  ### The rebuild path gained a new input, and it needed its own test

  `_reconstruct_shift_middle` loads `WORKING`/`PAUSED` only. Before this change a clock-out
  force-closed step was in neither, so the rebuild never saw one; after it, such a step is `PAUSED`
  and lands in the sweep. `test_rebuild_reads_a_shift_ended_pause_as_off_shift_and_stays_idempotent`
  covers it. Proven failing-first: without `bucket_for` there, the shift-ended span is rebuilt as a
  **second `IN_PAUSE` segment** (`assert 2 == 1`) — a worker shown as paused, credited to a system
  transition, for hours they were not on site. Both standing invariants are asserted in that test:
  the rebuild is idempotent over identical sources, and the worker's own pause survives with its
  catalog reference. `test_declaration_survives_the_clock_out_rebuild` (declarations) still passes
  unchanged.

  ### Criterion 3 — the two paths assert opposite things, and the second failed first

  - Clock-out force-close: equality, pinned to explicit values, unchanged from step 1 through step 7.
  - Worker-picked ended-shift pause: written to assert the **new** classification and run against
    pre-change code first, where it failed twice — the record was `ENDED_SHIFT` rather than `PAUSED`,
    and the rebuild produced **zero** `IN_PAUSE` rows for it (the span fell through to idle,
    unattributed). Both now pass. Evidence retained in the session scratchpad.

  ### Criterion 9 — asserted directly, on real data and on a seeded row of each shape

  Measured workspace-scoped with the suite quiescent, local DB at `c8f3d2e60a17`:
  **208** `step_state_records` in `ended_shift` (E2 row 1: **39**, row 2: **169**, row 3: **0**;
  0 conflicted, 0 soft-deleted, 0 typed as another transition) and **58** `task_steps`. One
  workspace holds 153 of the 169 row-2 rows, so on this database the population E2's row 2 protects
  is the *dominant* one — this line was not academic here.

  After the migration, asserted against the journal (the live rows are no longer distinguishable,
  which is the point): of the 169 worker-picked rows, **0** were typed as a system transition and
  **0** lost their `pause_reason_id`; all 39 row-1 rows kept `transition_reason='shift_ended'`; all
  208 are now `paused`.

  Row 3 has zero rows on this database, so its branch was proven by rehearsal instead of left
  untested: downgrade → seed one record of each of E2's three shapes plus an `ended_shift` task step
  → upgrade → assert each outcome exactly → downgrade, delete the seed, upgrade. All three matched
  the table, including that row 3's default did not reach the row carrying a `pause_reason_id`.
  The database was returned to exactly its real population (39/169/0/58) afterwards.

  ### The migration is reversible — this contradicts the plan, deliberately

  The plan states the migration is irreversible. **With the journal it is not**, and the journal is
  warranted for precisely the reason `architecture/30_migrations.md` gives: after the cutover a
  newly-written clock-out row is byte-identical to a rewritten row-1, and a worker's pause is
  identical to a rewritten row-2, so no predicate can identify the rewritten rows afterwards.
  `ended_shift_collapse_journal` records every touched row with its previous state, previous
  transition reason, and which E2 rule claimed it; `downgrade()` re-adds the enum member and
  restores exactly those rows, and refuses outright if the journal is gone rather than restoring by
  predicate into live data.

  A full **downgrade → upgrade round trip was run on the local database**: the downgrade restored
  208 records and 58 steps to the exact pre-migration distribution (39/169/0) with the enum member
  back, and the re-upgrade reproduced identical counts.

  What is *not* undone by any of this is the reporting change E2 chose: a worker-picked ended-shift
  pause moves from `total_ended_shift_seconds` to `total_pause_seconds` and past reports read
  differently. The journal does not soften that — it only means the rows can be put back.

  **The journal is not dropped by this change.** Whichever later change makes this one permanently
  irreversible must drop it deliberately, last, and record the row count it held.
  *(Corrected 2026-08-01: an earlier wording said "behind an explicit environment acknowledgement,
  the pattern `c8f3d2e60a17` established". That pattern was withdrawn in `4bece10` — a migration
  that raises mid-`upgrade head` stops the deploy before the service restart. `30_migrations.md`
  now says to leave such a revision off the chain instead, or do the drop operationally.)*

  ### Deployment ordering — the two databases are not in the same state

  *(Both facts below were corrected by the operator on 2026-08-01; the originals came from the
  implementer prompt and were stale by the time this ran.)*

  Local is at `c8f3d2e60a17`; **the server is at `d8e4f1a2c6b7`** — verified by `alembic current`
  on the server, and **three revisions earlier than this plan originally stated**
  (`a7d21f4c8b03`). That matters: the server predates `595e7b840926`, so it has **no
  `user_declared_state_records` table and no `clock_in_code` column**. The deploy therefore carries
  **two** undeployed feature sets — `declared_worker_states` and `system_transition_reasons` — plus
  this one. Eight migrations:

      d8e4f1a2c6b7 (server) → 595e7b840926 → c2f4a6b8d0e1 → 67cfba8fcb2d
      → a7d21f4c8b03 → 97b60e06d42a → b4e7a1c93f28 → c8f3d2e60a17 → 2645b4327b17

  Two consequences for whoever deploys:

  - The server has not run phase 3's backfill, so its `ended_shift` rows may include E2 **row 3**
    (untyped), which is empty locally. That branch is exercised only by the rehearsal above. This
    is the most important unknown in the deploy.
  - **`c8f3d2e60a17` no longer requires a flag.** Its `ALLOW_DROP_BACKFILL_JOURNAL` guard was
    removed in `4bece10`, before this work was reviewed. A plain `alembic upgrade head` now runs
    the whole chain — no explicit revision targets, no environment variable.

  #### There is a window where the old code runs against the new enum (R2)

  *Recorded here because this is where the deployer looks; raised in review round 1.*

  `.github/workflows/deploy.yml:32-36` runs `alembic upgrade head`, then
  `apply_db_triggers.py`, **then** `systemctl restart`. So the readers ship *after* the
  migration, not before it — the opposite of the order E5 reasons about. E5's property is about
  **rollout correctness of the bucket** (the expression yields `ended_shift` at every point), and
  that still holds. It says nothing about the enum member disappearing from under processes that
  are still running, which is a separate matter and is real.

  Between the migration and the restart, every old-code query binding the removed member raises:

      asyncpg.exceptions.InvalidTextRepresentationError:
        invalid input value for enum task_step_state_enum: "ended_shift"

  Seven pre-restart sites do that: `averaged_time._TIME_STATES` (and through it all six
  analytics consumers), `_roster.TIME_STATES`, `get_worker_daily_step_breakdown._TIME_STATES`
  and `_WORK_STATES`, `get_user_last_active_step_record._ACTIVE_STATES`,
  `get_worker_working_sections._ACTIVE_STATES`, and `process_step_transition`'s
  `TIME_BEARING_STATES` in the analytics worker. The worker-facing working-sections read is among
  them, so this is visible to workers, not only to reporting.

  **It self-heals on restart and is inherent to removing an enum member** — it is not a defect in
  this work. Leaving the member in the type and dropping it in a later deploy is the alternative,
  and that is the operator's call, not this session's.

  #### The window's length is set by the table rewrite, not by the 208 rows (R3)

  The reclassified population — 208 records, 58 steps — is **not** what governs the deploy.
  `_recreate_enum` (`2645b4327b17:96-111`) issues two `ALTER TABLE … ALTER COLUMN state TYPE …
  USING` statements, and each **rewrites every row of its table and rebuilds every index on it,
  under `ACCESS EXCLUSIVE`**. Measured locally just now:

  | Table | Rows rewritten | Indexes rebuilt |
  |---|---|---|
  | `step_state_records` | 6,164 | 11 |
  | `task_steps` | 2,389 | 10 |

  So the cost driver is ~8,500 rows and **21** index rebuilds locally, against 208 rows of actual
  reclassification — a factor of forty. Production volumes are unmeasured. Two `count(*)`s on the
  server before deploying give the real figure; sizing the risk from 208 will be wrong.

    The guard was withdrawn because the transition-reason journal it protected held the *same*
    `previous_pause_reason_id` on every row, so its entire content was a list of row ids derivable
    from the rewritten rows; and because raising inside `alembic upgrade head` — which this repo's
    deploy workflow runs **before** `systemctl restart` — left the schema migrated, the new code
    pulled but not running, and services never restarted. See `architecture/30_migrations.md`.

    **This does not weaken the judgement made for `ended_shift_collapse_journal` above** — that one
    holds genuinely per-row information (three E2 row shapes with different previous states), which
    is exactly the distinction the contract now asks for. Keeping it was right; guarding its drop
    with a raising migration would not be.

  ### Proposed for the operator — §6.1 of the reassigned-steps handoff (not edited)

  `HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md` §6.1 documents this work as pending.
  Both the rewrite and the liveness flip are operator-owned and were **not** touched. Proposed
  wording for §6.1:

  > `TaskStepStateEnum` no longer has an `ended_shift` member. A step the shift ended under is
  > `paused`; the reason travels in `transition_reason` (`shift_ended`) or `pause_reason_id`. Clients
  > must not send or switch on `new_state: "ended_shift"` — it now returns `422`.
  > `total_ended_shift_seconds` / `total_ended_shift_count` are **unchanged** in every step payload,
  > including the reassigned-steps endpoints, and `"ended_shift"` remains a timeline **state string**
  > — it is a derived label, not a step state, and only its derivation moved.

  Step 5's frontend work was **already present in the workers-app working tree** when this session
  reached it, matching `HANDOFF_TO_FRONTEND_remove_pause_reason_transition_20260801.md`:
  `pause-reason-transition.ts` and its test deleted, both `PauseReasonSheetPage.tsx` call sites
  sending `new_state: "paused"` unconditionally, the `requiresDescription` branch reading
  `reason.requires_description` directly, no references remaining, and the unit and Playwright specs
  asserting `new_state: "paused"` for the `pause_ended_shift` pick. Verified, not authored.
  **Nothing was committed in the frontend repository** — that tree carries a large amount of
  unrelated in-progress work, and committing into it is the operator's call, not this session's.

  ### Judgement calls made without escalating, for review

  - **`aggregate_metrics.py` had to be touched.** It is dead (E3, zero callers, deletion out of
    scope) but referenced the enum member being removed, so it could not be left as-is. Taken the
    smallest edit that leaves it *correct* rather than quietly wrong: it now buckets through the
    shared `bucket_for` and takes an optional `transition_reason`. It remains dead and still slated
    for separate deletion — this is not the E3 work and is not offered as such.
  - **A new module, `domain/analytics/time_buckets.py`**, holds the bucket rule once. E5's expression
    is applied at three sites in two languages of expression (one SQL `CASE`, two Python); a shared
    constant plus a pure predicate is what makes "the same expression" checkable rather than
    asserted. The SQL `CASE` stays in the query layer.
  - **Four existing tests asserted the old writer's state** and were updated to the new truth rather
    than deleted. Where the change made an assertion weaker — the force-closed step and a
    worker-paused step are now both `paused` —
    `test_clock_out_transitions_working_steps_and_leaves_paused_steps_open` was **strengthened** to
    separate them by `transition_reason` and to assert the worker's pause record is untouched, which
    is E1's invariant stated directly.
  - **`models/tables/tasks/README.md` said "`PAUSED` and `ENDED_SHIFT` are distinct interruption
    types. Do not collapse them."** Corrected — leaving it would have been a document asserting the
    opposite of the code.

  ### Validation

  | Check | Result |
  |---|---|
  | `pytest -q` from `backend/app`, default plugins | **23 failed, 1448 passed** — failure node set **byte-identical** to the baseline (23 at `b59deb0`, re-measured this session, matching the stated `8a6af89` baseline), +11 new passing |
  | `ruff check` on touched files | clean. The 5 remaining findings are all unused imports in `transition_step_state.py` and are **pre-existing** — identical count against the stashed baseline, unrelated to this change, left alone |
  | `grep -rn "ENDED_SHIFT" app/beyo_manager` | `UserShiftStateEnum` hits only, plus the derived `ENDED_SHIFT_BUCKET` label |
  | Enum member in the database | gone: `pending,working,paused,blocked,completed,skipped,failed,cancelled` |
  | Rows left in `ended_shift` | 0 in both tables |

- `2026-08-01` `independent review session`: **`NEEDS_CHANGES`** — one missed sweep site
  (blocking), one unflagged deploy-window hazard, one unmeasured volume. Everything else
  verified independently and holds, including the two lines the change could not afford to get
  wrong.

  ### Findings

  **R1 — `scripts/backfill/heal_open_shifts_today.py:112` is a fourth site the sweep missed.**
  *Severity: blocking. Criterion 7 (the sweep), same class as the two the implementer found.*

  Its `_TIME_STATES` is `(WORKING, PAUSED)` and always was — so no grep for `ENDED_SHIFT`, and no
  grep for the output key `"ended_shift"`, can reach it. It is not a **re-key** site; it is a
  site whose selected **population changed**. Before the collapse a clock-out force-closed record
  was `ended_shift` and fell outside that tuple; now it is `paused` and falls inside, and its
  `entered_at` is exactly `clock_out_at` — so it satisfies `entered_at >= scope_start` where
  `scope_start` is the last clock-out (`:95-115`).

  That query *is* the mechanism behind the script's documented contract: *"A worker who has
  already clocked out today … is skipped."* It no longer skips them. Reproduced against the live
  code by clocking a worker in, seeding a working step, clocking out, and calling
  `heal_current_shift(..., execute=False)`:

      HEAL OUTCOME: would_heal shift_start=2026-07-20T17:00:00+00:00 start_source=first_task
      expected:     skipped_no_current_shift_activity

  With `--execute` that writes a `STARTED_SHIFT` marker at the clock-out instant, replaces the
  day's durationful rows via `reconstruct_shift_middle(shift_start=clock_out_at, now)`, and then
  deliberately re-opens the tail (`:186-188`) — leaving a clocked-out worker with an open shift
  record running to `now`, breaking the *"one open record ⟺ worker on shift"* invariant that same
  block names. The script has no test coverage of any kind.

  This is the identical failure mode the implementer caught in
  `backfill_worker_shift_state_records.py`, on the identical class of file, and it is why the
  prompt makes a missed sweep site blocking. The fix is one line — `bucket_for`, or an explicit
  `transition_reason <> 'shift_ended'` predicate — but the population change wants a test, since
  nothing currently watches this script at all.

  **R2 — E5's ordering property does not hold in this repo's deploy shape.**
  *Severity: medium. E5 / the "Deployment ordering" section of the implementation log.*

  E5 reasons that the derived expression is correct at every point *"which is what lets the
  readers ship before the writer and the migration."* `.github/workflows/deploy.yml:33-36` runs
  `alembic upgrade head`, then `apply_db_triggers.py`, **then** `systemctl restart`. The readers
  therefore ship *after* the migration, not before it: for the whole length of the migration
  chain the old processes are still serving against a database whose enum has already lost
  `ended_shift`.

  Every old-code query that binds the member then raises. Confirmed against the live migrated
  database:

      asyncpg.exceptions.InvalidTextRepresentationError:
        invalid input value for enum task_step_state_enum: "ended_shift"

  Seven sites in the pre-restart code do that: `averaged_time._TIME_STATES` (and through it all
  six analytics consumers), `_roster.TIME_STATES`, `get_worker_daily_step_breakdown._TIME_STATES`
  / `_WORK_STATES`, `get_user_last_active_step_record._ACTIVE_STATES`,
  `get_worker_working_sections._ACTIVE_STATES`, and `process_step_transition`'s
  `TIME_BEARING_STATES` in the analytics worker. The worker-facing working-sections read is among
  them.

  Self-healing on restart, and inherent to removing an enum member — but it is not stated
  anywhere, and the log's "Deployment ordering" section is where whoever deploys will look. It
  belongs there, alongside the row-3 unknown. The alternative (leave the member in the type,
  drop it in a later deploy) is a decision for the operator, not a defect in this work.

  **R3 — the volume that was measured is not the volume that governs the deploy.**
  *Severity: low. `22_performance.md`, listed as a loaded contract.*

  What is recorded is the reclassified population: 208 records, 58 steps. The cost and lock
  driver is `_recreate_enum` (`2645b4327b17:96-111`), whose two `ALTER TABLE … ALTER COLUMN state
  TYPE … USING` statements rewrite **every row** of `step_state_records` and `task_steps` and
  rebuild all eleven indexes on the former, under `ACCESS EXCLUSIVE`. Locally that is 6,157 and
  2,389 rows; the production figure is unmeasured, and it — not 208 — sets the length of R2's
  window. One `count(*)` on the server before deploying closes this.

  ### Verified independently — these hold

  - **Criterion 9, checked against the journal directly rather than accepting the counts.**
    Journal partitions 39 / 169 / 0 plus 58 `task_steps`, matching what was claimed. Of the 169
    row-2 rows: **0** typed as a system transition, **0** that lost their `pause_reason_id`, **0**
    not now `paused`. Of the 39 row-1 rows, **0** lost `transition_reason='shift_ended'`. No
    journal row whose `previous_state` was anything but `ended_shift`, no orphans, no
    soft-deleted rows swept in. `ck_step_state_records_transition_xor_catalog` confirmed present,
    so "both set" is genuinely unreachable.
  - **E2 row 3 constructed independently, not inherited.** The migration's three predicates were
    replayed verbatim against a seeded population containing row 3 *and* a row-2 row whose
    catalog reference is the `pause_ended_shift` row itself — the case where the default would do
    the most damage. Result: 1 / 2 / 1, exact partition, nothing left in `ended_shift`, the
    control row untouched, and **row 3's `transition_reason` default reached neither row-2 row**.
    The branch with no local instances behaves as the table says.
  - **The sweep, re-derived by a third route.** Neither the symbol grep (plan) nor the output-key
    grep (implementer): every reader of `StepStateRecord.state`, every `LinearInterval(`
    construction site, and every copy of a `_TIME_STATES`-shaped constant. That route reproduces
    both sites the implementer found and surfaces exactly one they did not — R1. Four copies of
    the constant exist, not three.
  - **The corruption check is non-empty, and the count is right.** Corrupting the SQL `CASE`'s
    first branch fails 7 of the module's 11 tests; corrupting `bucket_for` fails the 8th
    (`test_rebuild_reads_a_shift_ended_pause_as_off_shift_and_stays_idempotent`). 8 total, as
    claimed — split across the rule's two expressions, which is what the shared module buys.
  - Criterion 7: all six consumers have their own test asserting explicit values. Criterion 6 has
    its **own** test (`:809`), not an inherited one, and it asserts `IDLE` on the morning after.
    Rebuild idempotence and the worker's own pause surviving with its catalog reference are both
    asserted in the same test. Criterion 10: every published name intact — no serializer in the
    diff.
  - Suite reproduced: **23 failed, 1448 passed**, and the new module's 11 all pass. The only three
    failures inside touched domains fail for pre-existing infrastructure reasons — a test double
    with a stale signature, a session-fixture transaction clash, and role seeding. *Note for the
    record:* a literal baseline-worktree comparison is no longer possible — the suite runs against
    the shared `.env` database, which is already migrated, so baseline code cannot execute against
    it at all (that is R2 in miniature).
  - Ruff: 5 findings in `transition_step_state.py`, identical against `b59deb0` — pre-existing,
    left alone correctly.
  - Handoff untouched, no liveness row flipped, §6.1 proposed only. Nothing committed in the
    frontend repository — its last commit predates this work and the deletions sit uncommitted in
    the tree, exactly as described. `docs/domains/worker_shifts/` updated in this change; two
    claims spot-checked against code and both accurate — the current-shift scoping of the
    precedence table (`reconcile_worker_shift_state.py:172`) and clock-out pausing worked steps
    only (`_clock_worker_shift.py:118-121, 200-209`). Remaining `ENDED_SHIFT` mentions in those
    docs are all `UserShiftStateEnum`, which is correct. No plan references, no phase numbers, no
    "previously".

  ### Judged, not raised

  - **The journal, and the reversal.** The right call, and the reasoning is the distinction
    `30_migrations.md` asks for. Confirmed it records enough to reverse row-by-row — per-row
    `previous_state` and `previous_transition_reason` plus which rule claimed each row — and that
    `downgrade()` restores by joining that table, refusing outright if it is gone rather than
    falling back to a predicate. What it does not undo (E2's reporting change) is stated plainly
    in both the migration docstring and the log. **Nothing drops the journal**, so the table lives
    in production indefinitely: an item needing a later decision, deliberately, not a defect.
  - **`increment_step_time_metrics` was edited, not left alone.** Contrary to what the review
    brief expected, but correctly: it referenced the enum member being removed, so leaving it
    would have left code naming something that no longer exists and would have broken the plan's
    own `grep -rn "ENDED_SHIFT"` gate. Zero callers confirmed, so the edit is inert; it is
    minimal and it was disclosed rather than presented as the E3 work. Accepted.
  - `ended_by` (linear-timeline drill-down) and `list_workers_last_interacted_step`'s `state` will
    no longer emit the string `"ended_shift"`. Both are downstream of the intended semantics, and
    the frontend handles them (`segment-adapter` only branches on `"completed"`; the step-state
    zod unions still accept the old value). Worth one clause in the §6.1 proposal; not a defect.
  - Self-reported weaknesses — the step-2 corruption check being meaningless, row 3 resting on a
    rehearsal — are accurate and were the right things to flag. Both were re-checked here and both
    stand up.

  ### To clear the verdict

  R1 only. R2 and R3 are for the operator's deploy decision and want a note in the log, not code.

- `2026-08-01` `fix cycle, round 1`: **R1 fixed. R2 and R3 recorded in "Deployment ordering"
  above. Awaiting re-review.**

  ### R1 — the fix

  `scripts/backfill/heal_open_shifts_today.py` now excludes `transition_reason = 'shift_ended'`
  from the two queries that ask *"has this worker done anything?"*, via one documented predicate
  `_worker_activity()` (`:70-93`) used at `:139` and `:279`. That restores the exact population
  each query had when a force-closed record was its own state, and it reads the mark the record
  already carries — no state special-case, no timestamp proxy, nothing that names the removed
  member.

  `IS DISTINCT FROM`, not `!=`: `transition_reason` is NULL on every worker-driven record, and
  `NULL != 'shift_ended'` is NULL, which would have discarded exactly the rows the query exists
  to find. Confirmed in the emitted SQL: `transition_reason IS DISTINCT FROM $4`.

  **`:279` (the candidate scan) assessed on the same grounds and fixed too.** Its population
  changed identically — a worker whose only record today is their own clock-out became a
  candidate where before they were not. On its own it is *not* harmful once `:139` is fixed,
  because the per-worker gate is what decides; the effect is that the reported `candidates=`
  count stops meaning "workers with activity today". Restored anyway, so the two queries keep
  answering the same question.

  ### R1 — tests, proven failing-first

  The script had none; that is why this was invisible. New file
  `tests/integration/scripts/backfill/test_heal_open_shifts_today.py`, seeded by driving the
  **real** clock-in/clock-out commands so it is pinned to what the writer actually produces, and
  asserting the premise (`state=paused`, `entered_at == clock_out_at`,
  `transition_reason='shift_ended'`) so it cannot pass vacuously if the writer changes again.

  Against the unfixed script, **3 of 4 fail** — including the reviewer's reproduction verbatim:

      test_worker_who_clocked_out_today_is_skipped
        AssertionError: assert 'would_heal shift_start=2026-07-20T17:00:00+00:00
                                start_source=first_task' == 'skipped_no_current_shift_activity'

  | Test | Unfixed | Fixed |
  |---|---|---|
  | `test_worker_who_clocked_out_today_is_skipped` | **fails** — `would_heal … 17:00` | passes |
  | `test_execute_writes_nothing_for_a_worker_who_clocked_out` | **fails** — writes a marker and reopens the tail | passes |
  | `test_worker_who_clocked_back_in_after_clocking_out_is_still_healed` | **fails** — heals from 17:00 (the clock-out) instead of 17:30 (the real resume) | passes |
  | `test_worker_still_mid_shift_is_healed` | passes | passes |

  The fourth is the control the fix must not break — it passes on both sides deliberately, which
  is the evidence that the exclusion is narrow rather than a no-op. The third is an extra
  manifestation the finding did not name: even for a worker who genuinely *is* mid-shift, a
  clock-out earlier the same day made the healed shift start at the clock-out instead of at their
  real resume.

  The `--execute` case asserts the full derived-row shape is byte-identical before and after
  **and** that no open shift row exists — the damage the finding names is a clocked-out worker
  left with an open shift, and a tag-only assertion would not have caught it.

  ### The sweep, re-derived on the basis the finding names

  Not "what reads this value" but **"what filter previously excluded `ended_shift` and now
  admits it?"** Derived by listing every predicate on `StepStateRecord.state` and
  `TaskStep.state` (37 sites), then reading each constant's definition **at `b59deb0`** to see
  whether it contained the member before. A tuple that *did* contain it has an unchanged
  population; one that did not, does not.

  Five sites qualify. Complete list:

  | # | Site | Pre-collapse filter | Status |
  |---|---|---|---|
  | 1 | `scripts/backfill/heal_open_shifts_today.py:139` | `_TIME_STATES` (`:58`) — no `ENDED_SHIFT` | **R1 — was broken, fixed** |
  | 2 | `scripts/backfill/heal_open_shifts_today.py:279` | same tuple | **fixed** — benign alone, restored for consistency |
  | 3 | `beyo_manager/services/commands/users/_reconstruct_shift_middle.py:110` | `_STEP_TIME_STATES` (`:38`) — no `ENDED_SHIFT` | handled in round 1 (`bucket_for` + failing-first test) |
  | 4 | `beyo_manager/services/commands/users/reconcile_worker_shift_state.py:171` | inline `(WORKING, PAUSED)` | handled — the `entered_at_or_after` guard at `:172`, criterion 6 test |
  | 5 | `beyo_manager/services/queries/worker_stats/get_worker_linear_timeline_breakdown.py:234` | inline `(WORKING, PAUSED)` | population widened; **now tested**, see below |

  Everything else is one of: a tuple that already contained the member (`TIME_BEARING_STATES`,
  `_roster.TIME_STATES`, `get_worker_daily_step_breakdown._TIME_STATES` / `_WORK_STATES`,
  `get_user_last_active_step_record._ACTIVE_STATES`,
  `get_worker_working_sections._ACTIVE_STATES`, both backfill `_TIME_STATES`); an equality on
  `COMPLETED`/`WORKING`/`PENDING`, which no reclassified row can satisfy; a `notin_(TERMINAL_…)`,
  which excluded neither state; a caller-supplied filter (`tasks.py:155,427`,
  `list_working_section_steps.py:124`) where the new semantics are the intended ones; or **no
  state filter at all** (`list_workers_last_interacted_step`,
  `get_worker_linear_timeline_breakdown._load_record_outcomes`), where the population never
  changed and only the emitted label did.

  **Site 5 was the one worth a test rather than a reading**, since a reading is what missed R1.
  `test_timeline_drilldown_never_shows_the_clock_out_record_as_a_paused_step` asserts the
  force-closed record appears in **no** segment's `steps` — neither in the shift it ended (it is
  entered at the clock-out instant, so it starts at or after the end of every segment of that
  shift) nor in the next morning's (the `entered_at >= current_shift_start` carryover guard,
  which the code already documents as mirroring `reconstruct_shift_middle`). Two independent
  guards, both now covered; if either goes, a worker's timeline grows a paused block covering the
  night. **The day-two half is mutation-checked** — see the R4 entry below for what it took to
  make it detect its own regression.

  ### Out of scope, observed while testing — not fixed

  Seeding a worker who clocked in at 08:00 and started their first task at 09:00 makes
  `heal_current_shift` raise `IntegrityError` on the open-record unique index: `shift_start`
  becomes 09:00, so the open `IDLE` the clock-in wrote at 08:00 falls **outside** the rebuild
  window, is never closed, and collides when the tail is reopened. `_run` catches exactly this
  and reports `skipped_raced_live_reconcile`, so it degrades safely in production.

  This is **pre-existing and independent of the collapse** — no `shift_ended` record is involved
  and the behaviour is identical at `b59deb0`. Recorded, not fixed: it is outside this plan, and
  the test was rewritten to the script's stated primary case (a mid-shift worker with no marker
  at all) rather than papering over it.

  ### Validation

  | Check | Result |
  |---|---|
  | `pytest -q` from `backend/app`, default plugins | **23 failed, 1453 passed** — failure node set **byte-identical** to the baseline at the same run index; +5 over round 1 (4 heal-script, 1 timeline drill-down) |
  | `ruff check` on touched files | clean; the 5 pre-existing `transition_step_state.py` unused imports are unchanged and still out of scope |
  | R1 reproduction | fails before, passes after — output quoted above |

- `2026-08-01` `independent review, round 2`: **`APPROVED`.** R1 is genuinely fixed, the fix is
  correct at the one place it could have been subtly wrong, and the sweep re-derived
  independently on the population basis returns the same five sites with nothing missed. One
  non-blocking evidence gap (R4), recorded below — behaviour is correct, the test that is claimed
  to cover it does not.

  ### R1 — verified fixed

  - **`IS DISTINCT FROM` confirmed in the emitted SQL, not the source.** Compiling
    `_worker_activity()` against the postgres dialect yields
    `step_state_records.transition_reason IS DISTINCT FROM %(transition_reason_1)s`; no bare `!=`
    anywhere in the statement.
  - **The `!=` mutation was run.** Swapping it collapses the predicate to NULL for every
    worker-driven record and **fails the control test** plus the clocked-back-in test (2 failed,
    2 passed). The two "must skip" tests still pass — for the wrong reason, everything excluded —
    which is precisely why the control is the test that matters here. It has real power against
    the exact defect this line invites.
  - **Failing-first reproduced independently.** Reverting both call sites to the bare tuple gives
    **3 failed, 1 passed**, matching the recorded table node for node, including the reproduction
    verbatim: `would_heal shift_start=2026-07-20T17:00:00+00:00 start_source=first_task` where
    `skipped_no_current_shift_activity` is required.
  - **The extra manifestation is real and is fixed.** With the predicate reverted,
    `test_worker_who_clocked_back_in_after_clocking_out_is_still_healed` fails with
    `shift_start=…17:00` (the clock-out) rather than `…17:30` (the real resume) — a genuinely
    mid-shift worker healed from the wrong instant. The finding did not name this case; the fix
    covers it because it removes the record rather than special-casing the clocked-out worker.
  - **The control is not vacuous**, on two counts: it asserts a specific marker instant, exactly
    one open row and its state, and no ended-shift marker; and it is the test the `!=` mutation
    breaks.
  - **The `--execute` assertion is not vacuous.** The shape it compares is four real rows
    (`started_shift, idle, working, ended_shift`), so `after == before` is a meaningful equality,
    and the separate "no open shift row" assertion is the one that names the damage.
  - `_worker_activity()` is applied at both `:139` and `:279`; the two queries cannot drift.
    Fixing `:279` is defensible on its own terms — the reported `candidates=` count otherwise
    stops meaning what it says.

  ### The sweep — re-derived independently, same five

  Derived without reference to their list: every predicate on `StepStateRecord.state` and
  `TaskStep.state` at HEAD, then each constant's definition read **at `b59deb0`**, keeping only
  those where the filter admits `PAUSED` and did **not** admit `ENDED_SHIFT` before. Result:
  `heal_open_shifts_today` (both call sites), `_reconstruct_shift_middle:110`,
  `reconcile_worker_shift_state:171`, `get_worker_linear_timeline_breakdown:234`. **The same
  five. Nothing missed.**

  Confirmed excluded for the stated reasons: every other constant genuinely contained the member
  at `b59deb0` (`TIME_BEARING_STATES`, `_roster.TIME_STATES`, both breakdown tuples, both
  `_ACTIVE_STATES`, `averaged_time._TIME_STATES`, both backfill copies); `reconcile:96` passes
  `(WORKING,)` only, so no reclassified row can enter; `notin_(TERMINAL_STEP_STATES)` admitted
  both states before and after; the caller-supplied filters (`tasks.py:155,427`,
  `list_working_section_steps.py:124`) are API query params where "a step the shift ended under
  is paused" is the intended new semantics. Sites 3 and 4 confirmed still handled.

  ### R4 — the day-two half of the site-5 test has no power *(non-blocking)*

  *`tests/…/test_ended_shift_bucket_collapse.py:859-882`. Severity: low — evidence, not
  behaviour. No criterion violated.*

  The log states of site 5: *"Two independent guards, both now covered; if either goes, a
  worker's timeline grows a paused block covering the night."* The first half of that is true and
  the test earns it — instrumenting the day-one assertion shows it running against 4 segments and
  1 shown step, so the force-closed record is excluded from a genuinely populated set.

  The day-two half is vacuous. It asserts over an **empty** set (`0` steps shown), because the
  fixture leaves the worker `IDLE` on day two and `_STEP_STATE_FOR_SHIFT` attaches step records
  only to `WORKING`/`IN_PAUSE` segments — so no step record of any kind can appear, guard or no
  guard. **Deleting the `entered_at >= current_shift_start` guard from
  `get_worker_linear_timeline_breakdown.py:322` leaves the test passing.**

  The guard is nonetheless load-bearing, which is what makes this worth recording rather than
  dismissing. Reconstructing day two so the worker genuinely derives `IN_PAUSE` (clock in, start
  a step, pause it for a stated reason) and re-running with the guard removed puts yesterday's
  force-closed record into this morning's timeline — `steps shown` goes 1 → 2 and the carryover
  is among them. That is exactly the regression the log names, it is real, and the suite does not
  currently catch it.

  So site 5 is **safe**, and the *reasoning* about it is right; but one of its two guards is
  still verified only by a reading, which is the thing this round was asked to check. Closing it
  is a fixture change — give day two a real pause segment — not a code change. Recommended
  before archive; the wording "both now covered" should be corrected either way.

  ### R2 / R3 — recorded accurately

  - **R2** is in "Deployment ordering", and it correctly separates itself from E5: E5 governs
    bucket correctness during rollout and still holds; a member vanishing under running processes
    is a different matter. `deploy.yml` confirmed — `alembic upgrade head` at `:33`,
    `apply_db_triggers.py` at `:34`, `systemctl restart` at `:36`. The seven pre-restart binding
    sites are listed correctly.
  - **R3 — their correction to round 1 is right and round 1 was wrong.** Measured: 11 indexes on
    `step_state_records` and 10 on `task_steps` = **21**, both tables fully rewritten under
    `ACCESS EXCLUSIVE`, ~8,500 rows locally against 208 reclassified. Round 1's "eleven" counted
    `step_state_records` alone. The log tells the deployer to size the window from the table
    rewrite and to take two `count(*)`s on the server first, which is the right instruction.

  ### The out-of-scope observation — judged, and it holds

  Reproduced both sides. The clock-in-at-08:00 / first-task-at-09:00 scenario raises
  `UniqueViolationError` on the open-record index under HEAD **and** under the `b59deb0` version
  of the script loaded side by side, in a scenario containing no `shift_ended` record at all.
  Genuinely pre-existing and independent of this change. The degradation is real code, not an
  assertion — `_run:327-331` catches `IntegrityError`, rolls back, and reports
  `skipped_raced_live_reconcile` per worker without losing the batch.

  Rewriting the test to the script's stated primary case was the **right call**: a worker mid-shift
  with no marker at all is problem #1 in the script's own docstring, it exercises the heal path end
  to end, and it is what makes the control a control. Asserting the collision instead would have
  pinned a pre-existing bug as expected behaviour. Recording it unfixed and out of scope is the
  correct disposition.

  ### Suite

  **23 failed, 1453 passed** — reproduced exactly, +5 over round 1 as claimed (4 heal-script, 1
  timeline drill-down). The failure node set is **byte-identical** to the set captured in round 1:
  23 nodes, `diff` clean. `ruff check` clean on all round-2 touched files; the 5 pre-existing
  `transition_step_state.py` findings are unchanged and were not raised.

  ### Verdict

  **`APPROVED`.** R1 was a hard find and the fix is the right shape — it restores the population
  by reading the mark the record already carries, rather than special-casing a state or inferring
  from timestamps, and it got the NULL semantics right at the one line where getting them wrong
  would have read as correct. R4 is an evidence gap on a site that is safe, worth a fixture change
  and a corrected sentence, not another round.

- `2026-08-01` `fix cycle, R4 remainder`: **the carryover test now detects its own regression.**
  Test-only; no production code touched.

  ### Why the previous fixture could not fail

  `a408ef0` fixed the vacuity (day two produced steps, and today's own record was asserted
  present), but deleting the guard still left the test green. The reason is the attachment rule,
  not the timing: a step record joins a segment only when the segment's shift state maps to the
  record's **own** step state (`_STEP_STATE_FOR_SHIFT`: `WORKING→WORKING`, `IN_PAUSE→PAUSED`).

  Yesterday's carryover is `paused`, so the only block it can ever land in is an **IN_PAUSE**
  one — and day two had none. It was working all day. With no paused block anywhere in the
  timeline, the guard is never consulted for that record, and `force_closed not in shown_next`
  was satisfied by the shape of the day rather than by the guard.

  So both earlier versions passed for a reason unrelated to what they claimed to test: the first
  over an empty set, the second over a set that could not have contained the record either way.

  ### The arrangement that makes the guard load-bearing

  Day two now pauses a step for a catalog reason at 10:00 and resumes at 11:00, so the rebuilt
  timeline carries an `IN_PAUSE` block. Yesterday's force-closed record is still open — never
  resumed, which is what makes it a carryover — so it overlaps that block on both time
  conditions, and **only** `entered_at >= current_shift_start` keeps it out. The test asserts the
  block exists and holds *exactly* today's pause, plus a guard that day two derives exactly one
  such block, so a future change that removes the pause cannot silently restore the old blindness.

  ### Mutation check — both directions, as asked

  Deleting `and (current_shift_start is None or step_record.entered_at >= current_shift_start)`
  from `get_worker_linear_timeline_breakdown.py:484`:

      AssertionError: yesterday's carryover must not appear in this morning's timeline
      assert 'ssr_…40DDS9' not in {'ssr_…40DDS9', 'ssr_…0KJAH', 'ssr_…85CVF', 'ssr_…7TBKP'}

  and, with that assertion bypassed so the sharper one is reached, the paused block itself —
  the **1 → 2 the reviewer measured**:

      assert {…} == {…}
      Extra items in the left set: 'ssr_01KYYFT0MP69VJBMF5WEAZCZK7'

  Guard restored → passes. Both runs recorded; nothing else in the test file or that module
  changed.

  One correction to the R4 finding for the record: the carryover guard is the
  `current_shift_start` clause at `:484`, not `:238-241`. Lines 238-241 are the query's
  window-overlap clause, which does **not** exclude the carryover — the record exits at day
  two's clock-in, so it satisfies `exited_at > window_start` and is selected into
  `step_records` before segment attachment is considered. That is why the guard at `:484` is the
  one that matters, and it is the one the mutation check removes.

  ### Validation

  | Check | Result |
  |---|---|
  | `pytest -q` from `backend/app`, default plugins | **23 failed, 1453 passed** — failure node set **byte-identical** to the baseline at the same run index; unchanged from the previous round, this being test-only |
  | Guard deleted → target test | **fails**, output above |
  | Guard restored → target test | passes; module 12/12 |

## Lifecycle transition

- Current state: `archived` — implemented, reviewed twice, **`APPROVED`**; R4 remainder closed
- Next state: `approved` — summary and archive may proceed
- Transition owner: `David`
