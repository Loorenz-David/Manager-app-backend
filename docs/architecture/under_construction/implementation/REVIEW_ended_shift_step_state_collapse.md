# Review prompt — Ended-shift step state collapse

Independent adversarial review. Work from the repo files; assume no prior conversation.
Do not fix anything — report.

**Run `git` from `backend/`.** The parent directory is not a repository; `backend/` and `frontend/`
are separate ones. Agents in the predecessor feature set ran it one level too high, concluded there
was none, and silently downgraded their verification.

This change removes `TaskStepStateEnum.ENDED_SHIFT` — a state that encoded a reason. It rewrites
historical rows irreversibly-in-reporting-terms, re-keys every analytics bucket, and touches the
clock-out rebuild. The migration has run on a copy of production, never on production.

## Inputs

- Plan: `docs/architecture/under_construction/implementation/PLAN_ended_shift_step_state_collapse_20260801.md`
  — decisions **E1–E5**, ten acceptance criteria, eight steps, and the implementer's Review log.
- Implementer prompt: `.../PROMPT_ended_shift_step_state_collapse.md`
- Intention: `.../intention/INTENTION_ended_shift_step_state_collapse_20260731.md`
- Living domain docs: `docs/domains/worker_shifts/`

**Two facts in the Review log were corrected by the operator after the work ran** (commit
`dd5b3b6`) — the server's revision, and the removal of the `ALLOW_DROP_BACKFILL_JOURNAL` guard.
Both were stale inputs from the implementer prompt, not implementer errors. Do not raise them.

## Start here — the weakest evidence in the change

### E2 row 3 is proven by rehearsal only

The three-row reclassification table is the heart of the migration. **Row 3** — `state='ended_shift'`
with neither a `transition_reason` nor a `pause_reason_id`, typed to `shift_ended` — has **zero
instances locally**. The implementer proved it by seeding one, migrating, asserting, and restoring.

**The server almost certainly has them**: it is at `d8e4f1a2c6b7`, predating the transition-reason
work entirely, so every clock-out it ever wrote produced exactly that shape.

So the branch with the least real-data evidence is the one that will process the most production
rows. Read that code path with that in mind, and construct your own row-3 case rather than
inheriting theirs.

### Criterion 9 is the line that cannot be got wrong

A row carrying a `pause_reason_id` must **never** be given `transition_reason='shift_ended'` — that
silently re-types a worker's stated choice as a system transition, and after the fact the two are
indistinguishable. Of 208 local `ended_shift` records, **169 are row 2** (worker-picked), 153 of
them in one workspace.

Verify against the journal yourself: zero row-2 rows typed as a system transition, zero that lost
their `pause_reason_id`. Do not accept the implementer's count.

## The sweep — this has been the recurring defect

Three review rounds of a predecessor phase turned on a sweep that rested on one grep pattern. What
finally closed it was re-deriving by a **different route** — output keys rather than call sites.

The implementer used that technique and **found a third re-key site the plan and E3's table both
missed**: `backfill_worker_shift_state_records.py:136`, which builds `LinearInterval`s like the
clock-out rebuild and reads an `ended_shift` segment to place the day's end marker. Left alone,
every backfilled shift would have ended at the wrong instant — silently, on the script whose job is
repairing history.

- [ ] **Re-derive the sweep yourself, by a route neither of them used**, and diff against their
      list. Anything missed is blocking.
- [ ] Criterion 7 requires all six `compute_record_contributions` consumers verified **per
      consumer**, not inferred from the shared helper. Check each.
- [ ] `domain/task_steps/aggregate_metrics.py::increment_step_time_metrics` has **zero callers**.
      Confirm it was left alone — editing it changes nothing while looking exactly like the work.

## Ordering and the inert-before-migration property (E5)

The derived bucket expression is correct at every point in the rollout, which is what allows readers
to ship before the writer and the migration.

- [ ] Verify the expression's first branch really is inert before the writer cutover, and that
      `_TIME_STATES` kept **both** `ENDED_SHIFT` and `PAUSED` until the migration. Dropping
      `ENDED_SHIFT` early makes historical rows vanish from every total.
- [ ] The implementer notes their corruption check is **meaningless at step 2** for exactly this
      reason and that they re-ran it at step 4. Good catch — confirm the step-4 run is the one
      recorded, and that corrupting the `CASE` still fails the 8 tests they claim.

## The rebuild gained a new input

`_reconstruct_shift_middle` loads `WORKING`/`PAUSED` only, so before this change it never saw a
clock-out force-closed step. Now it does.

- [ ] Reproduce the failing-first claim: without the derived bucket, the shift-ended span rebuilds
      as a second `IN_PAUSE` segment — a worker shown as paused, credited to a system transition,
      for hours they were not on site.
- [ ] **Rebuild idempotence and declaration survival.** Four fix cycles were spent on these in an
      earlier feature set. Run the rebuild twice over the same source data and assert identical
      output; declare a state, clock out, assert the declaration survives.
- [ ] Criterion 6 — the `entered_at_or_after` guard at `reconcile_worker_shift_state.py:172` becomes
      load-bearing here. Confirm it has its **own** test, not an inherited one, and that clocking in
      the morning after leaving a step open derives `idle`, not `in_pause`.

## The journal — judge the reversal, do not assume it

The implementer **contradicted the plan deliberately**: the plan calls the migration irreversible,
they kept a journal and ran a full `downgrade` → `upgrade` round trip.

That is the right call under `architecture/30_migrations.md`, and the reasoning is the distinction
the contract asks for: their journal holds genuinely **per-row** information (three row shapes with
different previous states), unlike the transition-reason journal whose rows all shared one constant.

- [ ] Confirm the journal actually records enough to reverse row-by-row, and that `downgrade` uses
      it rather than a predicate.
- [ ] Confirm what they said it does **not** undo — E2's reporting change — is stated plainly.
- [ ] **Nothing drops this journal.** That is deliberate and better than the alternative, but it
      means the table lives in production indefinitely. Flag it as an item needing a later decision;
      do not treat it as a defect.

## Contract, scope and docs

- [ ] Criterion 10 — `total_ended_shift_seconds` / `_count` and `ended_shift_seconds` /
      `ended_shift_open_count` remain in **every** payload that carries them today, unchanged in
      name and meaning. Only their derivation moved.
- [ ] Criterion 5 — the timeline still distinguishes "paused while present" from "off shift", for
      both new and reclassified historical rows.
- [ ] The `§6.1` handoff rewrite is **proposed in the Review log, not applied**. Confirm no
      `docs/handoff/to_frontend/` file was edited and no liveness row flipped.
- [ ] Step 5 (frontend) was **verified, not authored** — the work was already in that tree from the
      existing handoff. Confirm nothing was committed in the frontend repository.
- [ ] `docs/domains/worker_shifts/` updated **in this change** and *accurate*, not merely edited —
      spot-check two claims against code. `states.md` described the old step-state vocabulary and
      must no longer.
- [ ] No plan references, phase numbers, or "previously" in the domain docs.

## Suite

- [ ] Failure **node sets** at the same run index, baseline worktree with all of `app/.env*`
      (`.env.testing` alone cannot start the app). Claim: 23 failed / 1448 passed, node set
      byte-identical to baseline, +11 new passing.
- [ ] The 5 remaining ruff findings in `transition_step_state.py` are **pre-existing** (T8) —
      confirm identical against a stashed baseline; do not raise them.

## Verdict

`APPROVED` or `NEEDS_CHANGES`, findings with file:line, violated criterion, severity. Record in the
plan's Review log — the only file you modify.

Two notes. The implementer found a real site both the plan and the intention's trace missed, and
flagged their own step-2 check as meaningless — **weight self-reported weaknesses as evidence of
care, not as findings.** And if the change is clean, say so plainly; a manufactured finding at the
end of a long feature set costs more than it is worth.
