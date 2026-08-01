# PLAN_ended_shift_step_state_collapse_20260801

## Metadata

- Plan ID: `PLAN_ended_shift_step_state_collapse_20260801`
- Status: `under_construction`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-08-01T00:00:00Z`
- Last updated at (UTC): `2026-08-01T00:00:00Z`
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

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
