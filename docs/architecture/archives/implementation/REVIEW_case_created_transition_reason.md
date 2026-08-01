# Review prompt — Case-created transition reason

Independent adversarial review. Work from the repo files; assume no prior conversation.
Do not fix anything — report.

**Run `git` from `backend/`.** The parent directory is not a repository.

Creating a case on a task now pauses that task's working steps, with a typed
`transition_reason = case_created` and the case type in the description. Small change: one enum
member, one label entry, one new module, one call in `create_case.py`, tests. **No migration** — if
anything appears under `app/migrations/versions/`, that is a finding.

## Inputs

- Plan: `docs/architecture/under_construction/implementation/PLAN_case_created_transition_reason_20260801.md`
  — four rulings, ten acceptance criteria.
- Implementer prompt: `.../PROMPT_case_created_transition_reason.md`
- Living docs: `docs/domains/worker_shifts/`, `docs/repo_health.md`
- Implementation commit: `9497360`

## Start with criterion 7 — it caught a real defect, and the class generalises

The requirement: **the case must survive a failed pause.** The case is the user's intent; the pause
is a side effect.

The implementer found that `try`/`except` around the pause is *not sufficient*. A failed pause rolls
back its transaction, which expires every ORM object on the session — so building `create_case`'s
response afterwards attempted lazy IO outside an `await` and raised `MissingGreenlet`. **The side
effect's failure became a failure of the user's action anyway.** Fixed by snapshotting the response
before the pause runs.

- [ ] **Reproduce it.** Monkeypatch the pause to raise, and confirm: the case exists, the response
      is well-formed, the error is logged, and **no second exception escapes**. A test asserting
      only "no exception from the pause" would miss exactly what they found.
- [ ] Revert the snapshot (build the response after the pause instead) and confirm the test fails.
      If it still passes, the test is not binding to the fix.
- [ ] Check the same shape elsewhere in the change: anything reading ORM attributes *after* a
      rollback-capable block.

## The four rulings — verify none was quietly improved

| # | Ruling | What to check |
|---|---|---|
| 1 | **Every working step on the task pauses** | Criterion 5 must use **two** working steps. They claim controls: a same-task `PENDING` step and a different-task `WORKING` step. Verify both controls stay untouched — that is what proves the selection is scoped rather than broad. |
| 2 | **Customer cases skip, explicitly** | Not a null check that happens to fall through. Confirm the skip is written as a decision a reader can see. |
| 3 | **Closing a case does NOT resume the step** | The tempting addition. Grep for any resume/unpause path touching case closure. Its presence is a finding regardless of how well it is written. |
| 4 | **No migration, no backfill** | `app/migrations/versions/` untouched; the 7 historical rows unchanged. |

## Criterion 4 — the zero-catalog test

- [ ] Case creation pauses the step in a workspace holding **no `pause_reasons` rows**, and the test
      **asserts the catalog is empty before acting** rather than assuming it. This is the property
      four phases of prior work exist to guarantee.

## The transition path

They reused `_apply_step_transition` — the path clock-out and declarations already take — rather
than writing the `StepStateRecord` inline, so the `PROCESS_STEP_TRANSITION` outbox reconciles the
derived timeline.

- [ ] Confirm that reuse is real, and that the derived timeline actually follows. A row written
      inline with the timeline not updating is the failure this avoids — assert the derived
      segments, not just the step record.
- [ ] **The partial unique index**: a step with an existing open state record must have it closed
      before the pause opens, inside the same transaction. Construct that case; the index will
      reject a second open row, and it would do so inside the user's request.

## The sweep

They read both untested repair scripts by hand and report neither needs a change:
`heal_open_shifts_today.py:88-93` filters on `shift_ended` alone and must keep selecting
`case_created` (genuine in-shift activity), which it does; `backfill_worker_shift_state_records.py`
passes the value through and buckets via `bucket_for`.

They also name the population that **did** move: a step that used to stay `WORKING` now becomes
`PAUSED`, so clock-out and task-switch stop finding it — correct in both, since it is already paused.

- [ ] **Verify that population claim independently.** It is the third failure mode in
      `docs/repo_health.md` — a filter that was never edited becoming wrong because data moved into
      or out of its selection. Two sound sweeps have already missed an instance of it in this
      codebase. Ask specifically: does anything depend on that step still being `WORKING`?

## Contract, docs and scope

- [ ] `description` carries the case type, and behaves sensibly when `type_label` is `None` (both
      `case_type_id` and `type_label` are nullable).
- [ ] **`image_url: None` is correct and ruled** — the retired catalog row was seeded with a null
      image and no asset exists in the repository. The segment renders label-only. **Do not raise
      it.**
- [ ] `docs/domains/worker_shifts/` updated in the same change and *accurate*, not merely edited.
      Spot-check two claims against code.
- [ ] **No `docs/handoff/to_frontend/` file was edited by the implementer.** They correctly escalated
      the client-side conflict instead; the operator wrote
      `HANDOFF_TO_FRONTEND_remove_case_created_pause_20260801.md` separately.

## The escalation they raised — confirm the backend half is right

The workers app still fires its own pause after case creation, using a reason looked up by the slug
of a soft-deleted row. It resolves to nothing, so **40 reasonless paused records** exist. With the
backend now pausing first, that follow-up attempts `PAUSED → PAUSED` and is rejected.

- [ ] Confirm the backend behaves correctly in that scenario: the case is created, the step is
      paused **once**, with the reason — and the rejection of the client's follow-up is a clean
      `409`/validation error rather than anything that corrupts state or double-pauses.
- [ ] That is the whole backend obligation here. The client fix is a separate handoff; **do not
      treat the client's error as a defect in this change.**

## Suite

- [ ] Baseline worktree at `f2cd58f` with all of `app/.env*`: they report **23 failed / 1453 passed**
      reproducing baseline, and **23 failed / 1463 passed** with the change — failure node sets
      identical at run index 1. They also describe **9 tests**; +10 passing nodes. Reconcile that
      (a parametrised case would explain it) — small, but unexplained arithmetic in a validation
      claim is worth thirty seconds.
- [ ] `ruff` clean on the six touched files; `transition_step_state.py` untouched, so its 5
      pre-existing findings stand (`docs/repo_health.md`).

## Verdict

`APPROVED` or `NEEDS_CHANGES`, findings with file:line, violated criterion, severity. Record in the
plan's Review log — the only file you modify.

Two notes. The implementer escalated two things rather than deciding them, and found a defect the
criterion's obvious reading would have missed — **weight that as care, not as scope creep.** And
this is a small change at the end of a long sequence of feature sets; if it is clean, say so
plainly rather than finding something to justify the round.
