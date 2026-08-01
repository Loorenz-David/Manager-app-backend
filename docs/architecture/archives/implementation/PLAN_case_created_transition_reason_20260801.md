# PLAN_case_created_transition_reason_20260801

## Metadata

- Plan ID: `PLAN_case_created_transition_reason_20260801`
- Status: `archived`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-08-01T00:00:00Z`
- Related: `archives/.../system_transition_reasons/` (established `transition_reason`);
  `PLAN_ended_shift_step_state_collapse_20260801.md` (**must archive first** — see Sequencing)

## Goal and intent

- Goal: when a case is created on a task, the task's working step **pauses**, carrying
  `transition_reason = CASE_CREATED` and a description naming the case type.
- Business intent: raising a case means work has stopped. Today the step keeps running, so the
  timeline shows a worker still working while a problem is being discussed. This is a **restoration**
  — the capability existed, was removed at some point, and its absence went unnoticed.
- Non-goals: resuming the step when the case closes (see clarification 3); cases on customers;
  changing what a case is or who can raise one.

## Why this is a transition reason, not a pause reason

A worker does not pick "case created" from the pause sheet. **The system** stops the step because a
case was raised — the same shape as auto-pause on task switch. Under T1/T2 that makes it a
code-owned `transition_reason` with `pause_reason_id = NULL`.

Reviving the old `pause_case_created` catalog row would rebuild exactly what the
`system_transition_reasons` set dismantled: a mandatory system behaviour depending on a
workspace-editable row that may not exist. As an enum member it is present by construction in every
workspace, needs no seeding, and no manager can rename or delete it.

**The description carries the per-instance detail**, exactly as task-switch does with
`"started working with {article_number or sku}"`. That split — `transition_reason` for *what class
of thing happened*, `description` for *which one* — is why this does not become a family of
`CASE_CREATED_DAMAGE` / `CASE_CREATED_MISSING_PART` members.

## Clarifications — all four resolved

**All four resolved 2026-08-01 by operator approval of the recommended defaults.** No clarification
is open; these are rulings, not suggestions. If a case arises that they do not cover, escalate in
the Review log and stop — do not choose.

- [x] **1. Which step pauses? — EVERY working step on the task.** A case links to a **TASK** or a
      **CUSTOMER** (`CaseLinkEntityTypeEnum`), never to a step, and a task may have several steps
      `WORKING` at once under `allows_batch_working`. All of them pause: the case is about the task,
      and leaving a sibling step running contradicts the reason for pausing at all.
- [x] **2. Cases on a customer — SKIP.** No task, therefore no step. Make the skip **explicit in
      code** rather than letting it fall out of a null check, so the next reader sees it was decided
      rather than unhandled.
- [x] **3. Closing the case does NOT resume the step.** A case closing does not mean the worker is
      back at the bench, and auto-resuming would show someone working who is not there. Resumption
      stays a deliberate human action. If it is ever wanted automatically, that is a separate change
      with its own reasoning — **do not add it here**, even if it looks like an obvious completion.
- [x] **4. The 7 historical `pause_case_created` rows are LEFT ALONE.** They point at the
      soft-deleted anchor and still resolve to their label, so success is already satisfied by
      construction. Backfilling them to `CASE_CREATED` would buy one representation instead of two,
      but `pause_ended_shift` is already in exactly that state and nothing depends on it. **No
      migration is in scope for this plan.** Should that change later, those rows carry per-row
      information and would need a journal (`30_migrations.md`).

## Acceptance criteria

1. `TransitionReasonEnum.CASE_CREATED = "case_created"` exists. Confirm it fits
   `transition_reason`'s `String(32)`.
2. `domain/transitions/labels.py` gains an entry — name and `image_url`, so the segment renders with
   a label and icon like every other transition. Reuse the retired catalog row's image URL; it was
   hardcoded in the seed and never workspace-authored.
3. Creating a case on a task with a working step pauses it, with
   `transition_reason = CASE_CREATED`, `pause_reason_id = NULL`, and
   `description = "case created: {case_type name}"`.
4. **Zero-catalog test**: the above works in a workspace holding **no `pause_reasons` rows**. This
   is the property the whole predecessor feature set exists to guarantee; assert it here rather than
   assuming it.
5. Per clarification 1, the right set of steps pauses — asserted with a task carrying two working
   steps, not one.
6. A case on a customer, and a case on a task with **no** working step, both create the case
   normally and pause nothing. No error, no empty record.
7. **Case creation still succeeds if the pause fails.** The case is the user's intent; the pause is a
   side effect. Wrap it so a failure logs and does not roll back the case — the same reasoning that
   put clock-out analytics outside its write transaction.
8. The case type name is resolved from the case's `case_type`, with a sensible description when
   `case_type_id` is null (the field is nullable, and `type_label` may carry free text instead).
9. Existing read paths render the new transition without change — they resolve through the shared
   map. Assert on one timeline surface rather than trusting it.
10. `docs/domains/worker_shifts/states.md` lists the new member; the case/step interaction is
    described where a reader would look for it.

## Implementation steps

1. Add the enum member and the `labels.py` entry. (All four clarifications are already ruled —
   see above. No decisions are yours to make.)
2. In `create_case.py`, after the case and its links commit: resolve the task, find its working
   step(s), write the auto-pause record(s). Follow the shape at
   `transition_step_state.py:268-280` — same fields, same `created_by_id` and `credited_user_id`
   handling.
3. Tests for criteria 3–9, including the zero-catalog case and the two-working-step task.
4. Update `docs/domains/worker_shifts/states.md`.
5. Review log entry. **STOP for independent review.**

## Risks and mitigations

- Risk: pausing inside the case-creation transaction makes a step-state failure roll back the case.
  Mitigation: criterion 7 — the pause is a side effect and must not be able to fail the user's
  action.
- Risk: the wrong step pauses, or several do when one should.
  Mitigation: clarification 1 is a ruling, not an inference; criterion 5 asserts it with a
  two-working-step task.
- Risk: a partial-unique-index violation if the step already has an open state record.
  Mitigation: close the existing open record before opening the pause, exactly as the task-switch
  path does. Do not assume the step has none.
- Risk: scope creep into case resumption.
  Mitigation: clarification 3 rules it out explicitly as a separate change.

## Validation plan

- Zero-catalog case creation pauses correctly.
- Two-working-step task behaves per clarification 1.
- Customer case and no-working-step task: case created, nothing paused, no error.
- Forced failure in the pause path: case still created, error logged.
- Full suite: no new failure nodes vs. baseline — **node sets** at the same run index, baseline
  worktree with all of `app/.env*`. Run `git` from `backend/`.
- `ruff check` clean on touched files.

## Sequencing — UNBLOCKED

*(Updated 2026-08-01.)* `PLAN_ended_shift_step_state_collapse_20260801` is **approved and archived**,
and the `system_transition_reasons` package is archived. Nothing blocks this plan.

Two things that changed while it waited, both in your favour:

- **`TransitionReasonEnum` is stable again.** The collapse work removed `ENDED_SHIFT` from
  `TaskStepStateEnum` but did not touch the transition vocabulary, so adding `CASE_CREATED` is
  purely additive to a settled enum.
- **The migration chain is settled at `2645b4327b17`.** This plan adds no migration (ruling 4), so
  it does not extend that chain at all.

One inherited caution, now recorded in
[`docs/repo_health.md`](../../../repo_health.md): when you change what a value means, ask not only
what reads it and what emits it, but **what filter previously excluded it and now doesn't.** This
plan introduces a *new* member rather than changing an existing one, so that risk is low — but
`heal_open_shifts_today.py` and `backfill_worker_shift_state_records.py` both select on step state
and have no test coverage. A new `PAUSED` record with an unfamiliar `transition_reason` is worth
five minutes against those two before you call the sweep done.

## Review log

- `2026-08-01` `claude-opus-5` (implementer): **Implemented; awaiting independent review.** No
  migration was written — `app/migrations/versions/` is untouched.

  **What changed**

  | File | Change |
  |---|---|
  | `domain/transitions/enums.py:27` | `CASE_CREATED = "case_created"` |
  | `domain/transitions/labels.py:96-103` | Label entry |
  | `services/commands/cases/_case_created_step_pause.py` | New — the pause itself |
  | `services/commands/cases/create_case.py:215-230` | One call, plus a response snapshot (see below) |
  | `docs/domains/worker_shifts/README.md`, `states.md` | Domain docs, same change |
  | `tests/integration/services/commands/cases/test_case_created_step_pause.py` | 9 tests |
  | `tests/unit/domain/transitions/test_transition_reason_domain.py:83-90` | Column-width guard |

  **Acceptance criteria — evidence**

  | # | Evidence |
  |---|---|
  | 1 | `enums.py:27`. Fits `String(32)` at 12 chars, and now asserted for *every* member against both columns rather than eyeballed — `test_every_enum_member_fits_the_persisted_column`. |
  | 2 | `labels.py:96-103`. **See the image-URL finding below — this is the one criterion that did not resolve as written.** |
  | 3 | `test_zero_catalog_case_on_task_pauses_the_working_step`: `transition_reason = case_created`, `pause_reason_id IS NULL`, `description = "case created: Damaged item"`. |
  | 4 | Same test. `_assert_zero_catalog` runs first, so a fixture that started seeding reasons cannot make it pass vacuously. |
  | 5 | `test_every_working_step_on_the_task_pauses` — **two** working steps, plus a `PENDING` step on the same task and a `WORKING` step on a different task, both asserted untouched. |
  | 6 | `test_customer_case_creates_the_case_and_pauses_nothing`, `test_task_with_no_working_step_...`, and `test_case_on_an_unlinked_entity_pauses_nothing`. Each asserts the case exists and the step's record count is still 1 — no error, no empty record. The customer skip is an explicit branch (`_case_created_step_pause.py:113-117`), not a null check. |
  | 7 | `test_case_survives_a_failed_pause`. Monkeypatched failure, not inspection. Injected at the **second** of two steps, so it also proves the pause is all-or-nothing rather than leaving the task half paused. **This test found a real bug — see below.** |
  | 8 | Uses `type_label`, which `create_case.py:64-67` already resolves. Three shapes covered: case type name, caller free text, and neither (`"case created"`). |
  | 9 | `test_roster_timeline_buckets_and_labels_the_new_transition` — asserted on `list_workers_linear_timeline`, including that no `pause_by_reason` key fails to resolve. No read path was edited. |
  | 10 | `states.md` vocabulary table (now four members) plus the description/member split; the interaction itself is in `README.md`'s business rules next to the clock-out rule, which is where a reader looking for "what pauses a step" already is. |

  **Criterion 7 caught a real defect, not just a hypothetical.** With the pause placed before
  `create_case`'s `return`, a failed pause rolled back its own transaction, which **expired every
  ORM object on the session**; building the response then attempted lazy IO outside an await and
  raised `MissingGreenlet`. The side effect's failure became a failure of the user's action —
  exactly what the criterion forbids. Fixed by snapshotting the response off the ORM objects
  *before* the pause runs (`create_case.py:209-219`). Worth noting for review: the "wrap it in
  try/except" reading of criterion 7 is not sufficient on its own — what follows the call matters
  too.

  **Escalation 1 — criterion 2's image URL does not exist.** The criterion says to reuse the
  retired catalog row's image URL. There is none to reuse:
  - `migrations/versions/fb10ac7fd439_...py:71-90` inserts the `pause_case_created` anchor with a
    literal `NULL` image.
  - It is deliberately absent from both places the hardcoded S3 URLs live —
    `bootstrap/phases/seed_pause_reasons.py:48` and `migrations/versions/49bd666da846_...py:46-51`.
  - No `pause_reasons/case_created.webp` exists anywhere in the repository; the five that do are
    `coffee_break`, `ended_shift`, `lunch_break`, `meeting`, `other_task_priority`.

  So the entry carries `image_url: None` — reproduced-as-null, the same honest `None`
  `worker_declared_state` carries, arrived at differently. **This renders the segment with a label
  and no icon, which is not what criterion 2 asked for.** Reported rather than decided: if an icon
  is wanted, it is a new asset and an operator call, not something to invent here.

  **Escalation 2 — the workers app still fires its own pause, and it will now 400.**
  `frontend/.../use-task-step-detail.controller.ts:684-696` still auto-transitions the step to
  `paused` after a case is created, using a pause reason looked up by
  `slug === "pause_case_created"` (`:227`) — which resolves to `undefined` today, since that row is
  soft-deleted and absent from `GET /pause-reasons`. That is the mechanism by which the capability
  was lost. With the backend pausing the step first, that follow-up request now hits
  `PAUSED → PAUSED`, which `_ALLOWED_TRANSITIONS` (`transition_step_state.py:61-64`) rejects:
  `"Cannot transition step from paused to paused."` The case is created and the step is correctly
  paused, but the worker may see an error. Not covered by any of the four rulings, backend-only
  scope, and the protocol forbids a handoff edit — so it is raised here and **not acted on**.

  **The sweep — checked by hand, stated as a list.** This change *adds* a member rather than
  changing what one means, so the population-change mode is unlikely; the two untested repair
  scripts were still read line by line.
  - `scripts/backfill/heal_open_shifts_today.py:88-93` — the only transition-reason filter in that
    file excludes `shift_ended` alone. A `case_created` pause is genuine in-shift activity and must
    stay selected, which it does. Its rebuild delegates to `reconstruct_shift_middle`, which carries
    `transition_reason` generically. **No change needed.**
  - `scripts/backfill/backfill_worker_shift_state_records.py:99,104,149-153` — passes
    `transition_reason` straight through and derives its bucket via `bucket_for`. **No change
    needed.**
  - `domain/analytics/time_buckets.py:29-33` and its SQL twin
    `services/queries/analytics/averaged_time.py:41-50` — both special-case `shift_ended` only, so
    `case_created` falls to `else` and buckets as ordinary `paused` time. Correct: a worker
    interrupted by a case was present.
  - Every other reader (`domain/users/serializers.py:196-216`,
    `domain/tasks/serializers.py:197`, `services/queries/worker_stats/*`) resolves through the
    shared map with no member enumeration.
  - The population that *did* change: a step that used to stay `WORKING` now becomes `PAUSED`.
    `_load_open_working_step_rows` (clock-out, declarations) and `fetch_open_user_working_record`
    (task-switch auto-pause) therefore stop finding it — correct in both cases, since it is already
    paused and clock-out leaves already-paused steps alone by design.

  **Design notes for the reviewer**
  - Reuses `_apply_step_transition` rather than hand-writing a `StepStateRecord`. It is the path
    both other "the system paused a worker's step" callers already take (`_clock_worker_shift.py:198`,
    `declare_worker_state.py:127`), and it is what emits the `PROCESS_STEP_TRANSITION` outbox task
    whose handler reconciles the derived shift timeline (`process_step_transition.py:80-86`).
    Writing the record inline would have produced the row but not the timeline.
  - The open record is closed by that core in the same transaction that opens the pause, so the
    partial unique index is satisfied by construction rather than by assumption; asserted directly
    (exactly one open record remains, and it is the pause).
  - `credited_user_id` comes off the **closed record**, not from `ctx.user_id`. A manager raising a
    case on a worker's task must not acquire a pause segment on their own shift timeline;
    `created_by_id` still records who caused it. Falls back to the actor only if the closed record
    names nobody.
  - No realtime step event is dispatched for the pause, matching clock-out, which also does not.

  **Validation**
  - Full suite, baseline worktree at `f2cd58f` with all of `app/.env*` copied in: **23 failed /
    1453 passed**, reproducing the recorded baseline exactly. With the change: **23 failed / 1463
    passed** (+10 = the 9 new integration tests and 1 new unit test). Failure **node sets** at run
    index 1 are byte-identical — `diff` of the sorted `FAILED` node lists is empty.
  - `ruff check` clean on all six touched files. `transition_step_state.py` was not touched, so its
    5 pre-existing findings are untouched.
  - Observation, not acted on: `docs/repo_health.md`'s "`_step_transition_core.py` `NameError`"
    entry looks stale — `select` is imported at `_step_transition_core.py:21`, and every other name
    on that auto-pause path resolves. Left alone; the entry is not mine to delete on a read alone.

- `2026-08-01` `claude-opus-5` (independent reviewer): **APPROVED.** No blocking findings. Two
  non-blocking observations, both recorded below rather than acted on.

  This is a small change at the end of a long sequence, and it is clean. Every ruling holds as
  written, nothing was quietly improved, and the two escalations were the right calls.

  **Criterion 7 — reproduced, and the fix is binding.** Reverted the snapshot (built the response
  after the pause instead of before) and re-ran `test_case_survives_a_failed_pause`: it fails with
  `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called` escaping `create_case`, at
  `sqlalchemy/util/_concurrency_py3k.py:123`. Restored; tree verified clean. The implementer's
  reading is right and the "wrap it in try/except" reading is genuinely insufficient — the test
  binds to the ordering, not merely to the swallow. Checked the same shape elsewhere in the change:
  nothing else reads an ORM attribute after the rollback-capable block (`create_case.py:230` returns
  a plain dict; `type_label` is a local `str`).

  **The four rulings.**

  | # | Verdict |
  |---|---|
  | 1 | Held. `test_every_working_step_on_the_task_pauses` uses two `WORKING` steps and keeps **both** controls — a `PENDING` step on the same task and a `WORKING` step on a different task — asserted untouched, including no `PAUSED` record on the unrelated step. That is what proves the selection is scoped and not broad. |
  | 2 | Held, and explicit. `_case_created_step_pause.py:116-117` is a dedicated `CUSTOMER` branch placed *ahead* of the general guard at `:118-119`. A reader sees a decision, not a fall-through. |
  | 3 | Held. No resume path exists. `update_case_state.py` touches no step state, and `grep` across `services/commands/cases/` returns zero `StepStateRecord` / `TaskStepStateEnum` / `_apply_step_transition` references outside the new module. |
  | 4 | Held. `git diff f2cd58f..9497360 -- app/migrations/versions/` is empty. |

  **Criterion 4 — the zero-catalog test.** `_assert_zero_catalog` runs *before* the action in the
  write-path tests and fails loudly if a fixture ever starts seeding. Correctly asserted, not
  assumed.

  **The transition path — reuse confirmed, timeline follows, index confirmed.** Probed directly:
  creating a case increments the `PROCESS_STEP_TRANSITION` `execution_tasks` count by exactly one,
  so the derived-timeline reconciliation really is emitted rather than a bare row being written.
  The partial unique index exists and is exactly as the plan's risk describes —
  `uix_step_state_records_active ON step_state_records (workspace_id, step_id) WHERE exited_at IS
  NULL`. The pre-existing open record is closed in the same transaction that opens the pause;
  exactly one open record remains and it is the pause.

  **The sweep — the population claim verified independently.** Walked all 30 call sites keyed on
  `TaskStepStateEnum.WORKING`, not only the two the implementer named.
  - `heal_open_shifts_today.py:88-93` — `state IN (WORKING, PAUSED) AND transition_reason IS
    DISTINCT FROM 'shift_ended'`. A `case_created` pause stays selected. Correct as reported.
  - `reconcile_worker_shift_state.py:171-174` — loads both states and derives from
    `open_working_count`, so the worker's shift state correctly becomes `IN_PAUSE`. Not named in
    the sweep; behaves correctly.
  - `finalize_pending_step_completion.py:70` — `if step.state != WORKING: return` **would** skip a
    step a case had paused. Dormant: the only producer of `PENDING_STEP_COMPLETION` is commented
    out at `transition_step_state.py:193-225`. Not reachable; noted so the next person who
    re-enables the undo window knows to look.
  - The remainder (`_roster.py`, `get_worker_working_sections.py`,
    `get_user_last_active_step_record.py`, the analytics `_TIME_STATES` pairs) are display surfaces
    where `PAUSED` is the intended reading.
  - **The one live dependency on the step still being `WORKING` is the state machine itself** — see
    observation 2.

  **Escalation 2, backend half — correct.** Reproduced the client's follow-up end to end: the case
  is created, the step is paused **once** with `transition_reason = case_created`, and the follow-up
  `PAUSED → PAUSED` is rejected as `ValidationError("Cannot transition step from paused to
  paused.")` from inside `transition_step_state`'s own `session.begin()`, so it rolls back with
  nothing written. Afterwards: exactly one `PAUSED` record, exactly one open record, step state
  intact. No corruption, no double-pause. The backend obligation is met; the client fix is the
  operator's separate handoff and is not counted against this change.

  **Contract, docs and scope.** `description` carries the case type and degrades to `"case created"`
  when both `case_type_id` and `type_label` are null — all three shapes covered.
  `docs/domains/worker_shifts/` is accurate, not merely edited: spot-checked the customer-skip claim
  against `_case_created_step_pause.py:116-117` and the "four members" / description-split claim
  against `enums.py` and `build_case_created_description`. No `docs/handoff/to_frontend/` file
  appears in `9497360`; the handoff is the operator's `39a1044`. The `image_url: None` ruling is
  accepted and not raised.

  **Suite.** Reproduced at `HEAD`: **23 failed / 1463 passed**, matching the implementer's report
  exactly. The arithmetic reconciles as the plan already states — +10 nodes = 9 integration + 1
  unit (`test_every_enum_member_fits_the_persisted_column`); no parametrisation involved. None of
  the 23 touches cases, transitions or worker shifts; the nearest one
  (`test_endpoint_split.py`) fails on an unrelated stale test double
  (`empty_page() got an unexpected keyword argument 'roles'`). `ruff check` clean on all six touched
  files. `transition_step_state.py` is untouched by the diff and still reports its 5 findings. The
  implementer's stale-entry observation about `_step_transition_core.py` is also correct — `select`
  is imported at line 21 — and they were right to leave it.

  **Observation 1 (non-blocking, no criterion) — the pause emits no `task:step-state-changed`.**
  The design note justifies this as "matching clock-out", which is the weaker of the two available
  precedents: clock-out is self-initiated, whereas the closer analogue — the task-switch auto-pause
  — *does* broadcast the auto-paused step (`transition_step_state.py:470-488`). A case may be raised
  by a manager on a worker's live step, and that worker's client is never told. This is also why
  escalation 2 bites at all: the client's `step?.state !== "working"` guard
  (`use-task-step-detail.controller.ts:684`) reads a cache the backend just invalidated without
  saying so, so the guard passes and the request goes out. Emitting the event would make the stale
  state self-healing and remove the deploy-ordering coupling the handoff currently carries. Not
  required by any criterion and deliberately not acted on — an operator call.

  **Observation 2 (non-blocking, doc-level) — resume-before-complete is undocumented.**
  `_ALLOWED_TRANSITIONS` has no `PAUSED → COMPLETED` edge. Confirmed by probe: after a case pause,
  completing the step returns `ValidationError("Cannot transition step from paused to completed.")`.
  A worker interrupted by a manager-raised case must now resume before completing, where previously
  the step stayed `WORKING` and completed directly. This is *consistent* with clarification 3 —
  resumption is a deliberate human action — but it is the one real consequence of the population
  moving, and it is written down in neither `docs/domains/worker_shifts/` nor the handoff. Worth a
  sentence next to the pause rule in `README.md` whenever this area is next touched.

## Lifecycle transition

- Current state: `archived`
- Previous states: `under_construction` → `approved` (one review round) → `summarized` → `archived`
- Transition owner: `David`
- Summary: `implemented_summaries/SUMMARY_case_created_transition_reason_20260801.md`
- Archive record: `archives/implementation/ARCHIVE_RECORD_PLAN_case_created_transition_reason_20260801.md`
