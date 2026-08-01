# PLAN_case_created_transition_reason_20260801

## Metadata

- Plan ID: `PLAN_case_created_transition_reason_20260801`
- Status: `under_construction`
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

## Clarifications required — all three are operator decisions

- [ ] **1. Which step pauses?** A case links to a **TASK** or a **CUSTOMER**
      (`CaseLinkEntityTypeEnum`), never to a step. A task may have several steps, and more than one
      may be `WORKING` (`allows_batch_working`). Options: every working step on that task; only the
      one the acting user is working; or the most recently started. **Recommend: every working step
      on the task** — the case is about the task, and leaving a sibling step running contradicts the
      reason for pausing at all.
- [ ] **2. Cases on a customer — skip entirely?** No task, so no step. **Recommend: yes, skip**, and
      make that explicit in code rather than implicit in a null check.
- [ ] **3. Does closing the case resume the step?** Today nothing would. **Recommend: no** — a case
      closing does not mean the worker is back at the bench, and auto-resuming would put someone
      "working" who is not there. If the operator wants resumption, it is a separate change with its
      own reasoning, not a default.
- [ ] **4. The 7 historical `pause_case_created` rows.** They point at the soft-deleted anchor and
      still resolve to their label. **Recommend: leave them.** Backfilling to `CASE_CREATED` buys
      one representation instead of two, but `pause_ended_shift` is already in that same state and
      nothing depends on it. If backfilled, it needs a journal — those rows carry per-row
      information (`30_migrations.md`).

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

1. Resolve the four clarifications. Do not choose.
2. Add the enum member and the `labels.py` entry.
3. In `create_case.py`, after the case and its links commit: resolve the task, find its working
   step(s), write the auto-pause record(s). Follow the shape at
   `transition_step_state.py:268-280` — same fields, same `created_by_id` and `credited_user_id`
   handling.
4. Tests for criteria 3–9, including the zero-catalog case.
5. Update `docs/domains/worker_shifts/states.md`.
6. Review log entry with the four rulings. **STOP for independent review.**

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

## Sequencing

**Do not start until `PLAN_ended_shift_step_state_collapse_20260801` is approved and archived.** That
work is under review now and touches `TransitionReasonEnum` and every bucket path; adding a member
mid-review would collide with the reviewer's diff and its node-set comparison.

## Review log

- `<date>` `<reviewer>`: `<feedback>`

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
