# ARCHIVE_RECORD_PLAN_ended_shift_step_state_collapse_20260801

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_ended_shift_step_state_collapse_20260801`
- Archived at (UTC): `2026-08-01T00:00:00Z`
- Archive owner agent: `claude-opus-5` (on operator direction, post-review)

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_ended_shift_step_state_collapse_20260801.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_ended_shift_step_state_collapse_20260801.md`
- Intention: `backend/docs/architecture/under_construction/intention/INTENTION_ended_shift_step_state_collapse_20260731.md`
- Prompts: `.../archives/implementation/PROMPT_ended_shift_step_state_collapse.md`,
  `REVIEW_ended_shift_step_state_collapse.md`, `REVIEW_ended_shift_step_state_collapse_round2.md`
- Debug chain: `none`

## Outcome classification

- Result: `completed`
- Acceptance criteria: all ten met with evidence, criterion 7 verified per consumer.
- Reviews: round 1 `NEEDS_CHANGES` (1 blocking, 2 documentation); round 2 `APPROVED` with one low
  finding (R4), closed afterwards and mutation-verified in both directions.
- Validation gates: **not waived.** 23 failed / 1453 passed, node set byte-identical at the same run
  index; `ruff` clean on touched files; the repository's pre-existing findings neither absorbed nor
  repaired (T8).

## Final notes

- **`TaskStepStateEnum.ENDED_SHIFT` is gone.** A step stopped by a shift ending is `paused`, and the
  reason travels separately. `total_ended_shift_seconds` narrows to the *unattributed* bucket — the
  item stopped and nobody said why.
- **R1 is the most transferable finding this codebase has produced.** A filter that was never edited
  became wrong because the data moved into its selection. Two sound sweeps — attribute grep, then
  output-key grep — were both structurally blind to it. The question that finds this class is
  *"what filter previously excluded this value, and now doesn't?"* Both files it has bitten
  (`heal_open_shifts_today.py`, `backfill_worker_shift_state_records.py`) are offline repair scripts
  with no test coverage, which is why nobody notices.
- **`IS DISTINCT FROM`, not `!=`.** `transition_reason` is NULL on every worker-driven record, so
  `NULL != 'shift_ended'` evaluates to NULL and would discard exactly the rows the query exists to
  find. The wrong version reads perfectly.
- **A test can pass for a reason unrelated to its claim, twice over.** R4's assertion was first
  vacuous (empty set), then non-vacuous but still incapable of detecting the regression, because a
  paused carryover can only attach to an `IN_PAUSE` block and day two had none. Only the third
  arrangement made the guard load-bearing. Non-vacuous is not the same as load-bearing.
- **The plan's "irreversible" claim was contradicted, correctly.** The journal holds genuinely
  per-row information across three row shapes, unlike the transition-reason journal whose rows
  shared one constant — the distinction `architecture/30_migrations.md` now asks for.

## Open items at archive time

- **`ended_shift_collapse_journal` is never dropped.** Deliberate and better than the alternative,
  but it lives in production indefinitely and wants a later decision.
- **Nothing is deployed.** The server is at `d8e4f1a2c6b7`; this is eight migrations across three
  feature sets. Snapshot first, capture the before-numbers on the server, then `alembic upgrade head`.
- **A pre-existing `IntegrityError` in `heal_current_shift`** (open-record index collision when a
  clock-in's `IDLE` falls outside the rebuild window) reproduces identically at `b59deb0` and
  degrades safely as `skipped_raced_live_reconcile`. Recorded, not fixed.
