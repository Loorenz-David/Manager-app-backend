---
batch: D1
phases: [13]
role: test (fix round, verification route only)
round: 2
state: PROMPT_READY
date: 2026-09-22
actor: orchestrator
model: Opus
---

# Batch D1 — verification fix round 1. Two items, and nothing else.

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/verification-engineer.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

**This is a narrow fix round.** The D1 review came back `CHANGES_REQUESTED` with findings routed
three ways. **Exactly two are yours.** Everything else is either parked with the owner or waiting
on a ruling, and **the batch cannot be approved tonight whatever you do** — so there is no
pressure to make anything look finished.

Inputs: `SR/handoffs/reviewer/2026-09-21_batch_D1_review_1_handoff.md` (findings **S-1** and
**N-4**) and `SR/handoffs/tester/2026-09-21_batch_D1_test_1_handoff.md` (your predecessor's
ledger, same role, different session).

**Your slot: `BEYO_TEST_SLOT=dt2` on every pytest command.** `pytest.ini` carries
`-n 6 --dist loadfile`, so even a single-file run claims six worker databases.

## Item 1 — S-1: plan 13 C4(a)'s ordering row cannot fail

**The row** says the assignment list comes back *"ordered by `created_at`, `client_id`"*. **The
fixture cannot tell that apart from two weaker orderings.** The reviewer measured it: ordering by
`client_id` alone passes (five runs), ordering by `created_at` alone passes, and **only a full
reversal reddens.** So a change that dropped the date entirely would ship unnoticed.

The cause is that the four assignments are created in a tight loop through `_CR`, so their
`created_at` values do not reliably differ, and `client_id` is a ULID with **no monotonic
counter** (master plan §10 — measured at 977 of 1999 consecutive pairs out of order).

**This is the exact twin of the plan 12 C4(b) defect your predecessor found and fixed the same
evening**, and its fix is the template: the plan's own §6 preamble already demands that the seed
order the data *against* its ordering key. Here that means **`created_at` ascending must
disagree with `client_id` ascending** — so pick the pair deliberately, by sorting the real ids at
runtime and assigning timestamps against that order, never by trusting insertion order.

**A second weakness in the same test, while you are in it.** The expected order is currently
derived by re-running the same `ORDER BY` in the test:

```python
expected_order = (await db_session.execute(
    select(StockTaskAssignment.client_id).where(...).order_by(
        StockTaskAssignment.created_at.asc(), StockTaskAssignment.client_id.asc())
)).scalars().all()
assert ids == list(expected_order)
```

That mirrors production's own clause rather than pinning an answer. With a fixture whose two
orderings disagree you can assert an **explicitly constructed expected list**, which is strictly
stronger. Do that.

**Prove it with three mutation runs, each recorded separately** (§9 rule 8):

1. order by `client_id` alone → **must now be red** (it is green today);
2. order by `created_at` alone → **must now be red** (green today);
3. the full reversal → still red.

If any of the first two stays green, the fixture still does not discriminate and you are not done.

## Item 2 — N-4: plan 13 C2(a) never asserts `target_kind`

C2(a)'s outcome names the repair record's full shape — `{stock_report_item, R, quantity_in_queue,
stored "3", recomputed "0", inline:delete_stock_report_item}` — and the test does not assert
`target_kind`. Add it. Master plan §6.5 maps `counter_*` divergences to
`StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM`, so this pins a mapping nothing else in the
batch pins. One assertion.

## What you must NOT do

- **Do not touch production code.** Both items are test-side. The batch's one production defect
  is parked with the owner (card D-5) and is **not yours** — if you think you have found another,
  stop and report it.
- **Do not edit any plan cell and do not author any criterion row.** Both items are changes to
  *tests*, not to plans. C4(a)'s fixture cell already demands the disagreement; you are
  implementing what it says, not amending it.
- **Do not touch, delete, or "fix" the red test.**
  `test_the_priority_record_snapshots_the_live_awaiting_counter` is **deliberately red** — it is
  the witness for card D-5 and documents input → expected → observed. Your L4 will therefore show
  **24 failures, not 23, and that is correct.** Dropping an assertion to ship a green suite would
  hide a live data-corruption path.
- **Do not re-arm anything else.** §3B: the tester re-arms only the rows whose test or mutation
  site the fix touches. That is C4(a) and C2(a).

## Environment

Baseline is the checked-in 23-ID set at
`SR/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`. **Your expected L4 is
24 failed / 3739 passed / 1 skipped** — the 23 plus the declared witness. Diff your failure IDs
both ways and print both; a red that is neither in the file nor the witness is yours.

**Budget:** L1 on the two files as you go, **one L4** at the end. Mutation runs at hypothesis
scope — never an L4 per mutant.

## Deliverable

`SR/handoffs/tester/2026-09-22_batch_D1_fix_verification_1_handoff.md`: the diff; C4(a)'s three
mutation runs each observed and each reverted with its `git diff --quiet` proof; C2(a)'s added
assertion and the one mutation that proves it bites; your L4 with both ID diffs and the pass
arithmetic; and anything you found wrong.

**Report what you could hide.** Every session in this project's overnight runs has self-reported
something costly, including both of the sessions before you in this batch. That is the norm here.

**Never push. Commit with explicit paths, never `git add -A`.**
