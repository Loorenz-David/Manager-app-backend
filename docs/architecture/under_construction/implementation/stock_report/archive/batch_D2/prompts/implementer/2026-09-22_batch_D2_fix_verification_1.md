---
batch: D2
phases: [13A]
role: implement (verification fix round)
round: 1
state: PROMPT_READY
date: 2026-09-22
actor: orchestrator
model: Opus
---

# Batch D2 — verification fix round 1. Three rows. No production code.

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/implementation-executor.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Review: `SR/handoffs/reviewer/2026-09-22_batch_D2_review_1_handoff.md` — **read §5 in full.**
Plan: `SR/plans/plan_13A.md`.

**Review round 1 returned CHANGES_REQUESTED: 39 PASS / 3 FAIL over 42 rows.** All three failures
are **verification** defects. **The production code is right** — the reviewer planted three faults
and the code behaved correctly every time. **You are fixing tests, not behaviour.**

## Scope — exactly three rows

### 1. B1 (blocking) — 13A C5(b)'s test can go red on a healthy build

`test_c5b`'s `assert (await _fresh_row(env.session, row_c)).priority_order == 2` holds **only if**
`row_r.client_id < row_c.client_id`. The cascade loop runs ascending `client_id`, and
`_seed_group`'s guard (`placed != sorted(placed)`) is satisfied by the two filler rows alone — so
it never pins the pair the assertion actually depends on. The reviewer minted C first, with
positions and request order unchanged, and got:

```
…/test_process_stock_demand_deleted.py:1180: assert 3 == 2
FAILED …::test_c5b_two_rows_of_one_group_each_close_their_own_gap
```

**On correct code.** This is worse than an unarmed row: it is a **flaky test that can poison the
23-ID baseline**, which is the artifact every gate in this project depends on.

**`test_c5c` already does this correctly** for `row_x, row_y` using
`sorted(low_properties, reverse=True)`. **Copy that pattern.** Plan 13A §6's own preamble already
forbids what C5(b) did: *"a row that asserts the loop's order asserts it against the seeded ids."*

**Prove the fix**: re-run the reviewer's probe — mint C first, positions and request order
unchanged — and show the test **still green**. A fix that only passes in the original order has not
fixed anything.

### 2. S1 — 13A C3(a) checks one history-record kind out of three

The row promises every history record is removed. The fixture creates **three kinds**; the test
reads **one**. The reviewer made the code deliberately leave two of the three behind and **all 33
tests in the phase passed, all 6 in the neighbouring phase, and 495 across the stock-report area**.

**Widen the assertion to all three kinds and count them.** "Every X" needs a fixture with more than
one X and an assertion that counts them. Then plant the reviewer's mutant — leave two kinds behind —
and show the row **red**.

### 3. S2 — 13A C5(e)'s foreign-workspace control is empty

The plan asks the second workspace to hold the **same shape**: the same row, the same priority
group, the same **six** assignments. It was built holding a single bare row, so the comparison
passes whatever the delete code does. **Build the control the plan asked for**, then show it
discriminates.

## Everything else

The reviewer raised notes **N1–N7**. Read them and fix what is cheap and clearly right; **report
anything you decline and why.** Do not expand scope beyond that.

## Hard limits

- **No production code.** `git diff --name-only -- app/beyo_manager/` must be **empty** at the end.
  If you believe a test cannot be fixed without a production change, **stop and report** — do not
  make the change.
- **Owner card 1 (finding S3, the lock-order window) is NOT yours.** It is with the owner and it
  touches APPROVED phase-13 code. Do not fix it, do not work around it, do not mention it in a test.
- **You author no criterion row and edit no criteria table.** Mutation and fixture cells are the
  orchestrator's: propose replacement text in your handoff and I apply it. Review logs are yours.

## Environment

**Slot `BEYO_TEST_SLOT=d2f` on every pytest command** — every one, and **never two suites at once,
even on your own slot.** `pytest.ini` carries `-n 6 --dist loadfile`.

Baseline: the checked-in 23-ID set. **Expected L4: 23 failed / 3798 passed / 1 skipped**, both ID
diffs empty. If you add a test the pass count rises by exactly that many — say so and reconcile it.
**Budget: exactly one L4.**

## Handoff

`SR/handoffs/implementer/2026-09-22_batch_D2_fix_verification_1_handoff.md`: the diff; per row the
new assertion, the mutation you ran, its observed red and its revert proof; **the B1 re-ordering
probe green**; your disposition of N1–N7; the L4 with both ID diffs; proposed plan-cell text for
anything I should fold; owner questions under `⚠ OWNER DECISIONS REQUIRED (n)`.

Checkpoint: `CHECKPOINT (not approved): stock_report batch D2 verification fix 1 — B1, S1, S2`.

**Report what you could hide.** Every session in this batch has, including the reviewer whose first
L4 carried a flag that removed `caplog` and produced 37 spurious errors, and my own three
concurrent runs on one slot that faked a 959-failure catastrophe.

**Never push. Commit with explicit paths, never `git add -A`.**

## Stop conditions

B1 green under **both** id orders · S1 widened to three kinds and counted, mutant red · S2's control
built and discriminating · N1–N7 dispositioned · production diff **empty** · one L4 at 23 with both
ID diffs · lint clean · Review log written · handoff complete · checkpoint committed.
