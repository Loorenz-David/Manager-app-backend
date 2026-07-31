# Implementer prompt — System Transition Reasons, Phase 4: retirement & close-out

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

**This is the final phase.** It retires the machinery that served system pause reasons, makes the new
invariants enforceable by the database, and closes the feature set out.

**Two fields are retained deliberately, and dropping either breaks the worker app.** `slug` and
`is_system_managed` are both declared **required and non-nullable** in
`frontend/packages/pause-reasons/src/types.ts` (lines 19 and 18). Removing either from the
serializer fails Zod validation on every pause-reasons response. This phase removes their
*behaviour* — the slug lookup, the delete guard — and keeps the fields as inert published contract.
See criteria 5 and 6. It is the smallest phase in the set — and it contains the two moments where the whole set can
still go wrong.

## Protocol

1. Load and follow `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process as: implement → validate → review-log entry → **STOP for independent review.**
   Summary/archive only after the reviewer approves.
2. Read, in order:
   - `docs/domains/worker_shifts/` — all three files.
   - `.../system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md` — decisions
     **T1–T9**, the **"Phase 1 inventory"**, and every carried-forward item recorded by phases 2
     and 3.
   - Your plan: `.../system_transition_reasons/PLAN_system_transition_reasons_phase4_retirement_20260731.md`
   - `architecture/30_migrations.md` — including the new "Migration-owned bookkeeping tables"
     section, which governs the journal you are about to remove.
3. **Clarifications.** Two are open, both operator-decidable. Escalate and wait; do not choose.

## The two moments that matter

Everything else in this phase is subtraction. These two are not.

### 1. The check constraint (criteria 10–11)

Adding a constraint that fails validation against real data is a failed deploy, not a failed test.

**Prove compliance by query first**, on the restored production copy, and record the query and its
result. Only then add the constraint. Then prove it actually constrains — insert a deliberately
violating row and confirm it is rejected.

Remember the **documented exception**: mutual exclusion holds on `step_state_records`, but **not**
on the derived declared-state row, which carries `WORKER_DECLARED_STATE` *and* its catalog reference
by design. A constraint that rejects that row is wrong, and it will pass a naive test because the
naive test seeds a step record.

### 2. The journal drop (criteria 9a–9c)

`transition_reason_backfill_journal` is what makes phase 3's backfill reversible. Dropping it is the
act that makes the migration **permanently irreversible**.

- **Verify it is intact before anything else in this phase.** If it is missing, STOP and report —
  do not proceed. Recovery options narrow sharply once this phase's own changes land.
- **Drop it last**, after every other criterion in this phase passes.
- **Record the row count it held** in the Review log, so the record of what was rewritten survives
  the table.
- **Default if anything is unclear: keep it.** An orphaned table costs kilobytes; a missing one
  costs the ability to undo a migration over production data.

## What is retired, and what is emphatically not

| Row | Action |
|---|---|
| `pause_other_task_priority` | **Retire** — the only row this phase retires |
| `pause_ended_shift` | **Keep, and make it an ordinary worker-selectable reason** — clear `is_system_managed`, leave it visible and editable |
| `pause_case_created` | **Already soft-deleted. Do nothing.** Hard-deleting it violates `ondelete="RESTRICT"` and destroys labels success criterion 5 requires |

**Entry condition:** zero rows reference `pause_other_task_priority`. Re-run phase 3's query — do not
trust the recorded result. **Non-zero references to the other two are expected and legitimate**;
`pause_ended_shift` stays selectable so workers create new ones, and `pause_case_created` holds 7
historical rows phase 3 deliberately preserved. Do not "clean" either.

## Why `pause_ended_shift` stays — do not optimise this away

It looks like an inconsistency: a phase that retires system rows, keeping one. It is not.

Retiring the **machinery** is this phase's job — the slug lookup, the delete guard, runtime
resolution. Retiring the **row** is not, because a worker legitimately picks it, and
`list_pause_reasons` filters `is_deleted`, so soft-deleting it removes it from the pause sheet. The
worker app maps that slug to a state machine target and has no other way to produce it.

That is the feature set's own thesis: a catalog row is fine; a catalog row that **system behaviour
depends on** is not.

## `is_system_managed` — remove the behaviour, keep the field

`can_delete_pause_reason` returns `not is_system_managed`. That is **delete protection**, not a
label. Remove it and its call sites: once no row is system-managed there is nothing left to protect.
State that explicitly rather than leaving it implied.

**Keep the column and the serializer field.** `types.ts:18` declares it required and non-nullable, so
removing it fails Zod on every pause-reasons response — the same failure mode that forced T6's
amendment for `slug`, two lines below it in the same file. After this phase it is uniformly `false`
and inert: retained to satisfy a published contract, not to carry meaning.
`domain/transitions/labels.py` must keep emitting it too, so the real and synthesized shapes stay
identical.

## Close-out is a deliverable, not paperwork (criteria 13–16)

- **Re-verify all six master-plan success criteria fresh, end to end.** Do not inherit them from the
  phases that first claimed them. In particular re-run criterion 1 (clock-out in a zero-catalog
  workspace) and criterion 6 (second-workspace bootstrap, on a **disposable** database).
- **D3, D5, D14** carry their final amendment state in **this** feature set's master plan. The
  declared_worker_states plan is archived — verify no phase edited it.
- **The intention moves to `achieved`**, its linked-plans table updated, its open questions answered
  or explicitly closed. Note that its success criterion 4 is recorded as a **partial** completion —
  closed on the provably-dead arm only. Do not upgrade that to fully met.
- **Collect deferred items into one visible list**: T7's `manually_recorded` subsumption, and every
  repo-health item found but not fixed across phases 1–4 (T8). Deferred work that lives only in a
  phase Review log is lost the moment the phase archives.

## Hard constraints

- **Do not touch `manually_recorded` or the `changed_by_id` heuristic** (T7). This is the last phase
  and it will be tempting. It is still a scope violation.
- **Do not edit `docs/handoff/to_frontend/`.** Operator-owned; serializer changes are **proposed** in
  the Review log.
- **Do not edit archived plans** — declared_worker_states or phases 1–3.
- **T9 — commits.** Stage explicit paths; never `git add -A`. A parallel feature set is live in this
  tree.
- **`docs/domains/worker_shifts/`** — update it in this change if anything you do makes it untrue;
  say explicitly if nothing does.

## Validation

- **Run `git` from `backend/`.** The parent is not a repository. If `git rev-parse` fails you are one
  level too high — this has silently degraded two reviews in this codebase.
- **A baseline worktree needs all of `app/.env*`.** `.env.testing` alone cannot start the app.
- **Compare failure node sets at the same run index, and expect one latching node** — a shopify test
  that passes in isolation, sits outside the diff, and does not clear on re-runs. Verify it matches
  that description; do not absorb it (T8).
- **Any sweep must be re-derived by a second, different route.** Three rounds of phase 2 turned on a
  sweep that rested on one grep pattern. State results as a list with `file:line`, never as a count.

## Definition of done

- All 16 acceptance criteria met with evidence.
- Constraint compliance proven by query **before** the constraint was added; the constraint proven to
  reject a violating row; the declared-state exception proven **not** rejected.
- Journal verified intact, dropped last, row count recorded.
- Second-workspace bootstrap succeeds on a disposable database.
- All six success criteria re-verified fresh, not inherited.
- Intention moved to `achieved` with criterion 4 recorded as partial.
- Deferred items collected in one list in the master plan.
- Full suite per the rules above; `ruff check` clean on touched files.
- Review log entry with both clarification rulings. Then **STOP** — no summary, no archive, no
  phase-table flip, no handoff edit.
