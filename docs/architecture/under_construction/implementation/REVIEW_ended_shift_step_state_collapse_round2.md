# Review prompt — Ended-shift collapse, ROUND 2 (fix verification)

Independent adversarial review. Work from the repo files. Do not fix anything — report.

**Run `git` from `backend/`.** The parent directory is not a repository.

## Scope — narrow

Round 1 returned `NEEDS_CHANGES`: R1 blocking, R2/R3 documentation. **Everything round 1 verified as
holding is out of scope.** Do not re-derive:

- criterion 9 against the journal (39/169/0 + 58 steps)
- E2 row 3, constructed independently
- the six `compute_record_contributions` consumers
- the corruption count (7 + 1 = 8)
- criterion 6's own test, rebuild idempotence, declaration survival
- criterion 10 name preservation, handoff untouched, frontend uncommitted, domain docs

You are verifying the R1 fix, the re-derived sweep, and two recorded notes.

## R1 — the fix, and the one place a subtle bug would hide

The finding: `_TIME_STATES = (WORKING, PAUSED)` was never edited, but its **selected population
changed**. A clock-out force-closed record used to be `ended_shift` and fell outside the tuple; now
it is `paused`, entered at exactly `clock_out_at`, which is also exactly where `scope_start` lands.
The query implementing *"a worker who already clocked out today is skipped"* found the clock-out
itself and healed a closed shift.

- [ ] **`IS DISTINCT FROM`, not `!=` — verify this in the emitted SQL, not the source.**
      `transition_reason` is NULL on every worker-driven record, and `NULL != 'shift_ended'`
      evaluates to NULL, which would discard precisely the rows the query exists to find. Swapping
      it for `!=` should empty the result and break the control test. **Run that mutation.** This is
      the single most likely place for a defect that reads correctly.
- [ ] The predicate is applied at **both** `:139` and `:279` through one shared `_worker_activity()`,
      so the two queries cannot drift apart while answering the same question.
- [ ] **Failing-first, verified by you.** Three of four tests must fail against the unfixed script,
      including the reproduction verbatim (`would_heal shift_start=…17:00` vs
      `skipped_no_current_shift_activity`). Revert the predicate and confirm.
- [ ] **The fourth test is a control and must pass on both sides** — it proves the exclusion is
      narrow rather than a no-op. Confirm it is a genuine control and not vacuous: a test that
      passes either way *because it asserts nothing meaningful* looks identical to one that passes
      because the fix is well-scoped.
- [ ] The `--execute` case asserts **derived rows byte-identical and no open shift row**, not just
      an outcome tag. A tag-only assertion would miss the damage the finding names.
- [ ] They report an **additional manifestation the finding did not name**: a clock-out earlier the
      same day made a genuinely mid-shift worker heal from the clock-out rather than their real
      resume. Confirm that case is covered and that the fix addresses it rather than only the
      clocked-out-for-the-day case.

## The sweep — now on its fourth distinct route

This codebase has produced three separate sweep failure modes: attribute grep (missed a render
site), output-key grep (found it), and now **population change** — a filter that stood still while
the data moved into it, invisible to both.

The implementer re-derived on that basis: every predicate on `StepStateRecord.state` and
`TaskStep.state` (37 sites), reading each constant's definition **at `b59deb0`** to see whether it
contained the member before. Five qualify.

- [ ] **Re-derive it yourself on the population basis** and diff against their five. Anything missed
      is blocking. The question is not "what reads this value" but **"what filter previously
      excluded it, and now doesn't?"**
- [ ] Site 5 (`get_worker_linear_timeline_breakdown.py:234`) is claimed safe by two independent
      guards and now carries a test. They note that *a reading* is what missed R1 — so verify the
      test, not the reasoning.
- [ ] Sites 3 and 4 were handled in round 1; confirm they still are.

## R2 / R3 — recorded, not fixed

- [ ] **R2** is in the Review log's "Deployment ordering" section and is accurate: `deploy.yml`
      runs `alembic upgrade head` before `systemctl restart`, so seven pre-restart query sites bind
      the removed member and raise until the restart. Self-healing, inherent to enum removal.
      Confirm the log separates this from E5 — E5 is about *bucket* correctness during rollout and
      holds; it says nothing about a member vanishing under running processes.
- [ ] **R3 — the implementer corrected round 1's figure**: 21 indexes rebuilt, not eleven
      (`step_state_records` 11, `task_steps` 10), with both tables fully rewritten under
      `ACCESS EXCLUSIVE` — locally ~8,500 rows against 208 reclassified, a factor of forty. Verify
      the index count and that the log tells the deployer to size the window from the **table
      rewrite**, not from 208.

## The out-of-scope observation — judge it, do not inherit it

They report that a worker who clocked in at 08:00 and started their first task at 09:00 makes
`heal_current_shift` raise `IntegrityError` on the open-record index: the clock-in's open `IDLE`
falls outside the rebuild window and collides when the tail reopens. `_run` catches exactly this as
`skipped_raced_live_reconcile`, so it degrades safely.

- [ ] **Confirm it is genuinely pre-existing at `b59deb0`** and involves no `shift_ended` record —
      that is what makes it out of scope rather than collateral damage from this change.
- [ ] Confirm the safe degradation is real, not asserted.
- [ ] They rewrote their test to the script's stated primary case rather than papering over it.
      Judge whether that was the right call or whether it dodges coverage.

## Suite

- [ ] 23 failed / 1453 passed, node set byte-identical at the same run index, +5 over round 1.
      Baseline worktree needs all of `app/.env*`. `ruff check` clean on touched files; the 5
      findings in `transition_step_state.py` are pre-existing (T8) — do not raise them.

## Verdict

`APPROVED` or `NEEDS_CHANGES`, findings with file:line, violated criterion, severity. Record in the
plan's Review log — the only file you modify.

Two notes. The implementer corrected one of round 1's own numbers and surfaced a manifestation the
finding missed — **weight that as care, not as scope creep.** And if it is clean, say so plainly:
R1 was a genuinely hard find, the fix reads correct, and a manufactured fourth round would cost more
than it returns.
