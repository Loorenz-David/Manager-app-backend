# Implementer prompt — Case-created transition reason

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

Creating a case on a task should pause that task's working steps. It used to; the capability was
removed and nobody noticed, so today a worker who raises a case stays "working" on the timeline while
the problem is discussed. This restores it.

**This is a small change.** One enum member, one label entry, one call in `create_case.py`, and
tests. **No migration** — ruling 4 removed data work from scope entirely. If a file appears under
`app/migrations/versions/`, something has gone wrong.

## Protocol

1. Load and follow `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process as: implement → validate → review-log entry → **STOP for independent review.**
   Summary/archive only after the reviewer approves.
2. Read, in order:
   - `docs/domains/worker_shifts/` — all three files, including its "Known gaps" section, which
     names this missing capability.
   - Your plan: `docs/architecture/under_construction/implementation/PLAN_case_created_transition_reason_20260801.md`
     — the four rulings, ten acceptance criteria, five steps.
   - `docs/repo_health.md` — specifically the sweep note at the bottom.
3. **No clarifications are open.** All four were ruled by the operator. If a case arises that they do
   not cover, escalate in the Review log and **stop** — do not choose.

## Why this is a transition reason and not a pause reason

A worker does not pick "case created" from the pause sheet. **The system** stops the step because a
case was raised. Under T1/T2 that makes it a code-owned `transition_reason` with
`pause_reason_id = NULL`.

Do **not** revive the retired `pause_case_created` catalog row. Four phases of work went into
removing system behaviour's dependency on workspace-editable rows that may not exist in a given
workspace; putting one back would undo exactly that.

**The case type goes in the `description`**, following the existing precedent at
`transition_step_state.py:265` — `"started working with {article_number or sku}"`. The
`transition_reason` says *what class of thing happened*; the `description` says *which one*. That
split is why this does not become `CASE_CREATED_DAMAGE`, `CASE_CREATED_MISSING_PART`, and so on.

## The four rulings — settled, not suggestions

| # | Ruling |
|---|---|
| 1 | **Every working step on the task pauses.** A task may have several under `allows_batch_working`. All of them. |
| 2 | **Customer cases skip.** No task, no step. Make the skip **explicit in code**, not a consequence of a null check — so the next reader sees it was decided rather than unhandled. |
| 3 | **Closing a case does NOT resume the step.** It looks like the obvious completion of the feature. It is out of scope. A case closing does not mean the worker is back at the bench. |
| 4 | **The 7 historical rows are left alone.** No migration, no backfill. |

## Things already in place that you should use rather than rebuild

- **`type_label` already resolves the case type name.** `create_case.py:64-67` sets it from
  `case_type.name` when `case_type_id` is present, and otherwise keeps whatever the caller supplied.
  So criterion 8 is nearly free — use `type_label`, and decide what the description says when it is
  `None` (both fields are nullable).
- **The record shape exists**: `transition_step_state.py:268-280`. Same fields, same `created_by_id`
  and `credited_user_id` handling. Follow it rather than inventing one.
- **Read paths need nothing.** Every surface already resolves `transition_reason` through the shared
  label map. A new member flows through for free — but assert it on one timeline surface (criterion
  9) rather than trusting it.

## Two things that will bite if you rush them

**Criterion 7 — the case must survive a failed pause.** The case is the user's intent; the pause is
a side effect. If writing the step record fails, the case must still exist and the error must be
logged. Same reasoning that put clock-out analytics outside its write transaction. Prove it with a
monkeypatched failure, not by inspection.

**The partial unique index.** A step may already have an open state record. Close it before opening
the pause, exactly as the task-switch path does. Do not assume the step has none — the index will
reject you, and it will do so inside the user's case-creation request.

## The sweep — low risk here, but check two files by hand

This change **adds** a member rather than changing what an existing value means, so the
population-change failure mode described in `docs/repo_health.md` is unlikely to apply.

But `heal_open_shifts_today.py` and `backfill_worker_shift_state_records.py` both select on step
state, both have **no test coverage**, and both have already shipped defects from exactly this class.
A new `PAUSED` record carrying an unfamiliar `transition_reason` is worth five minutes against those
two before you call the sweep done. State the result either way.

## Definition of done

- All ten acceptance criteria met with evidence.
- **The zero-catalog test** (criterion 4): case creation pauses the step in a workspace holding
  **no `pause_reasons` rows**. This is the property four phases of work exist to guarantee — assert
  it, do not assume it.
- Criterion 5 asserted with a task carrying **two** working steps, not one.
- Criterion 6: a customer case and a task with no working step both create the case and pause
  nothing — no error, no empty record.
- `docs/domains/worker_shifts/` updated in the same change, including removing the "creating a case
  does not pause the working step" entry from its Known gaps once it is no longer true.
- Full suite: no new failure nodes vs. baseline — **node sets** at the same run index, baseline
  worktree with all of `app/.env*` (`.env.testing` alone cannot start the app). Last measured:
  **23 failed / 1453 passed**. **Run `git` from `backend/`** — the parent is not a repository.
- `ruff check` clean on touched files; the 5 findings in `transition_step_state.py` are pre-existing
  (`docs/repo_health.md`) — leave them.
- **T9 commits**: explicit paths, never `git add -A`. Domain docs ride with the implementation.
- Review log entry. Then **STOP** — no summary, no archive, no handoff edit.
