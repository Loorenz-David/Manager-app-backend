---
batch: D1
phases: [12, and an owner-authorized amendment to APPROVED phase 3]
role: implement (fix round, production route only)
round: 1
state: PROMPT_READY
date: 2026-09-22
actor: orchestrator
model: Opus
authority: owner, 2026-09-22 — "yes i approve the fix (only assignment reconciliation against goal records)"
---

# Batch D1 — production fix round 1. One defect. Nothing else.

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/implementation-executor.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

**You are fixing exactly one defect, in code that is APPROVED and VERIFIED, under an explicit
owner authorization quoted in this prompt's header. Nothing else in this repository is yours.**

## The owner's ruling, verbatim and scoped

> "yes i approve the fix ( only assignment reconciliation against goal records )."

That parenthesis is the specification. **The assignment-reconciliation rule applies to goal
records and to nothing else.**

## The defect

`compute_stock_report_divergences` (`app/beyo_manager/services/queries/stock_report/consistency.py`,
the `histories` loop at **:200-222**) walks **every** `StockReportHistoryRecord` in the workspace
and asserts that its `quantity_awaiting` equals the sum of the assignment quantities credited to
it (`credited_history_record_id`). It applies no filter on record **type**.

That reconciliation is only meaningful for a **goal record**. The other two types carry a
`quantity_awaiting` that is a **frozen snapshot**, not a running total — nothing is ever credited
to them, so the expected value is always `0` and any non-zero snapshot is reported as a permanent
divergence. Pressing repair then writes `quantity_awaiting = 0` over the snapshot, destroying an
append-only record.

**The ratified authority, which the code contradicts:**
- intention **§14C** divergence table (line 1594): the `goal_total` rule is
  *"`quantity_awaiting` of **each goal record**"*;
- intention **§6.2** (line 794) and **MC-5** (line 836): a *goal record* is the row's
  **`quantity_requested_change`** record.

**Why it surfaced only now:** phase 12 is the first code in the project that ever writes a
`priority_change` or `priority_order_change` record. Until this batch the only history records in
existence were goal records, for which the rule is correct. The defect was latent and
unreachable. **Phase 3 is not being blamed; it is being corrected where a new caller exposed it.**

## The fix, and the one design decision already made for you

**Add the type predicate to the `histories` selection in `consistency.py` so the `goal_total`
rule is computed over `quantity_requested_change` records only.** Use
`StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE` — never a spelled string (§9 rule
16's habit).

**One filter is the whole fix, and you must NOT mirror it into the repair.** I checked the callers
before writing this: `compute_stock_report_divergences` has exactly three consumers —
`repair_stock_report.py`, `get_stock_report_consistency.py`, and the test helper
`assert_stock_report_clean`. **`repair_stock_report` obtains its divergence list only from this
function** (`:170`, `:217`, `:294`) and never constructs one itself. So once the check stops
emitting these entries, the repair's `goal_total` branch can never receive one.

A second type guard on the repair's `UPDATE` would therefore be **an unreachable mirror that no
test could ever arm** — which this project already has a lesson about (**L-37**, earned in batch
C2, where exactly such a guard was shipped and recorded as permanently unarmable). **Do not add
it.** If your own reading of the callers disagrees with mine, **stop and report** rather than
adding it on judgement.

## What proves the fix

1. **The witness test goes green.**
   `app/tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py::test_the_priority_record_snapshots_the_live_awaiting_counter`
   is currently **red on purpose** — it is plan 12 **C3(d)**, and it is the whole reason this
   batch is blocked. It must pass **without being edited.** If you find yourself changing that
   test, you are fixing the wrong thing.

2. **Phase 3's own suite is green, unchanged, with no edits to its test files.** That is the proof
   the amendment is inert for everything that was already correct. Run at minimum
   `tests/integration/services/commands/stock_report/` and any file exercising
   `repair_stock_report` / `get_stock_report_consistency`, and name the files and counts.

3. **One named mutation, run and reverted:** revert your filter and confirm the witness test goes
   red again, with `git diff --quiet` exit 0 afterwards. One mutation, not a campaign.

4. **Report whether a goal record's own reconciliation still bites** — i.e. that you narrowed the
   rule without disabling it. Find an existing test that catches a wrong `quantity_awaiting` on a
   *goal* record and confirm it still fails under a deliberate drift. If no such test exists,
   **say so plainly** — that is a finding worth more than a clean report.

## Perimeter — and it is tiny

**Allowed:** `app/beyo_manager/services/queries/stock_report/consistency.py` (the `histories`
selection only), and plan Review logs in `SR/plans/plan_12.md` and `SR/plans/plan_3.md`.

**Forbidden:** everything else. Specifically: no change to `repair_stock_report.py`, no change to
any test file, no change to `master_plan.md` or the intention, and **no criterion row authored or
restated** — that is the owner's, always. If you believe plan 3 needs a criterion row pinning
"the health check ignores non-goal records", **write it in the Review log as a candidate** and
leave it; do not add it to a criteria table.

## Environment

**Slot: `BEYO_TEST_SLOT=dp` on every pytest command** (`pytest.ini` carries `-n 6 --dist loadfile`;
even a single-file run claims six worker databases).

Baseline is the checked-in 23-ID set at
`SR/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`.

> **Your expected L4 is 23 failed / 3739 passed / 1 skipped** — the witness that made it 24 is
> exactly what you are fixing, so it should return to the baseline set. **A 24th failure means
> the fix did not work; a 22 means you broke something that was already red for another reason.**
> Diff your failure IDs both ways and print both. Pass count should not move: you add no test.

**Budget:** L1 on the witness file, one L2 over the stock_report surface, **exactly one L4**.

## Handoff

`SR/handoffs/implementer/2026-09-22_batch_D1_fix_production_1_handoff.md`: the diff; the witness
test green and the exact command; phase 3's suite green with file names and counts; the one
mutation observed red and reverted with its `git diff --quiet` proof; your answer to proof item 4;
the L4 with both ID diffs; anything you found wrong; owner questions under
`⚠ OWNER DECISIONS REQUIRED (n)`.

Checkpoint: `CHECKPOINT (not approved): stock_report D1 production fix — goal_total applies to goal records only`.

**Report what you could hide.** Every session in this batch has self-reported something costly,
including a fabricated placeholder SHA. That norm is the point.

**Never push. Commit with explicit paths, never `git add -A`.**

## Stop conditions

The filter in place · the witness green **unedited** · phase 3's suite green with no test file
touched · one mutation red and reverted · one L4 at **23** with both ID diffs · lint clean ·
Review logs written · handoff complete · checkpoint committed.

**Not reasons to continue:** another defect you noticed (report it), the unreachable repair guard,
tidying, or a test you think is missing.
