---
batch: C2
phases: [9, 10]
role: implement
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Sonnet
---

# Batch C2 implementation — phase 9, then phase 10

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/implementation-executor.md` — **including "When the project
  runs a tester", which narrows your job. Read that section before Task 0.**
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Read in order: `SR/master_plan.md` (**§3B first**, then §6, §9's 19 standing rules, §10), then
`SR/plans/plan_9.md`, then `SR/plans/plan_10.md`. The intention is `SR/planning/intention.md` —
RATIFIED, and it wins over any plan.

## This project runs a tester. Your job is narrower.

A separate Opus verification engineer runs **after you and before the reviewer**. **These move to
it and you skip them entirely:**

- Task 0's row-level coverage map, in both directions;
- closing step 1½ — the named mutations and `executed == declared`;
- closing step 1¾ — proving each guard able to fail;
- the named-mutation ledger in your handoff.

**Do not run a single mutation. Do not transcribe the criteria tables into tests row by row.**

**What stays yours:** make the planned behaviour true; the tests you find *useful to build it*
(red → green, outcomes at a public boundary); the existing regression suite; lint and type
checks; closing steps 1, 2, 3, 4, 5; the Review log; the graph delta; rule 17's contradiction
check.

**Do not pad the test files to look covered.** In batch C1 the implementer named a long list of
rows it had not exercised and that was exactly right — it cost the tester minutes and cost the
round nothing. A weak test that *looks* like coverage costs a review round.

## Scope and order

**Phase 9 first, then phase 10** (§7.2: 10 depends on 9). Phase 10 may start once phase 9 is
implemented with its L1 tests green — it does not wait for a review.

Phases 1–8 and 11 are **APPROVED and VERIFIED**. You call that code; you do not change it. If you
believe an approved file must change, **stop and report** — that is an owner decision.

## Your test slot — set it on every pytest command

Another workstream (phase 8A) is active in this repository right now.

> **Set `BEYO_TEST_SLOT=c2` on every pytest invocation**, not just the L4. `pytest.ini` carries
> `-n 6 --dist loadfile`, so even a single-file run claims six worker databases. The slot gives
> you your own set (`beyo_test_c2_gw0…gw5`) and its own template:
>
> ```
> BEYO_TEST_SLOT=c2 PYTHONPATH=. pytest <file>
> BEYO_TEST_SLOT=c2 PYTHONPATH=. pytest -m 'not e2e'
> ```
>
> The first run in a fresh slot builds its template at the Alembic head, so it is slower once.
> Omitting the variable silently shares the default slot with the other workstream and makes
> both results worthless while looking like genuine failures.

## What the projection changed, and the two things it saved you from

Both plans were folded from the batch C2 projection and five owner cards were ruled. **The plans
are authoritative**; this list exists so nothing surprises you.

**Phase 10's C5 rows were rebuilt, and the old wording would have stopped you dead:**

- The previous fixture asked the first session to hold the row lock open until the second had
  issued its `FOR UPDATE`. **There is no such seam.** Both participants run whole production
  commands that take and release their own locks inside `maybe_begin`; neither can be made to
  hold one open for the other.
- The previous mutation said "skip the post-lock re-read". **There is no separate re-read
  statement.** The re-read *is* `_locks.py:22-41`'s `populate_existing=True`, which refreshes the
  identity-mapped instance in place — deleting it there would change every locking caller in the
  project.

**The replacement, now in plan 10 §6's preamble:** a third **referee** session takes the row's
`FOR UPDATE` and holds it; each participant's command is started as a task and **observed to
block**; the referee commits and both are awaited. Postgres queues the waiters in arrival order,
so the order is *forced* rather than raced. **Both observed blocks are assertions of the row, not
setup** — they are what proves the order held *and* that each session finished its unlocked
discovery read before the other committed. The precedent is shipped and APPROVED:
`test_apply_stock_demand.py:821-867`. **A barrier is not used** — it releases both sides at once
and expresses a race, not an order.

Other folds worth knowing: plan 9 §4 gained two files its own tasks require editing
(`_move_assignment.py`, `enums.py`) — without them the reviewer would flag correct work as a
perimeter violation. Both plans gained a §7 perimeter bullet authorising named mutations in
approved phases' files. Plan 9's §6 preamble now says that where a row states `q = n`, the
fixture sets item I's `quantity` to `n` before `CR` — F0's default is `4`, not the `8` some C4
rows assume.

**Rows that cannot fail, already labelled — do not try to make them bite:** plan 10 **C2(a)** and
**C7(b)** are marked UNFAILABLE BY DESIGN by owner ruling, with their real evidence named. Plan
10 **C4(a)** is a deliberate class-2 blank (it is the guard's control row).

## Standing rules that bite here

- **Rule 16** — `ACTIVE_ASSIGNMENT_STATES` / `TERMINAL_ASSIGNMENT_STATES`, never a spelled list.
  Both plans carry rows whose named mutation *is* a hand-typed list, so the real code must use
  the frozensets or those rows are inert.
- **Rule 17** — relocating a row's proof to a narrower surface is the **owner's**. Declare and
  stop; never quietly prove an endpoint row at a helper.
- **Rule 18 (new)** — every public signature you register in §6.5/§6.1 must be pinned by a row in
  your own plan. Plan 9 C8(c) is that row for `resolve_processed_group`.
- **Rule 19 (new)** — new test files need names unique across the **whole** test tree; bare
  filenames are module names here and a clash is a silent collection error.
- **§10** — `client_id` order is **not** creation order (ULIDs, no monotonic counter; measured at
  977 of 1999 consecutive pairs out of order). Plan 9 groups and orders rows: never assume
  insertion order, and sort real ids at runtime where an order is asserted.

## Environment

**Baseline: 21 failed / 3547 passed / 1 skipped** at `798fc69`. The **invariant is the 21-ID
failure set**, not the pass count — diff your failure IDs against the published set in
`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3
in **both directions** and print both. Reconcile the pass count arithmetic exactly.

**Budget:** L1 as you go, one L2 per phase, **exactly one L4** at the end. Nothing else.

## Your handoff — the tester contract

`SR/handoffs/implementer/2026-09-21_batch_C2_implement_1_handoff.md`:

1. **Checkpoint SHA per phase**, on a clean tree (`CHECKPOINT (not approved): …`). Never push.
2. **The one L4 stamp**, both ID diffs, pass-count arithmetic reconciled.
3. **The production write perimeter** — every file created or edited, explicitly.
4. **"Tests I wrote → the row each aimed at"**, as *claims*, not evidence.
5. **One load-bearing pointer per criterion** — the `file:symbol` where the behaviour is made
   true. For C5, say **where each lock is taken, where the referee's lock sits, and where the
   post-lock state is read** — that is the pointer the tester most needs and cannot cheaply find.
6. **Rows you know you did not exercise.** Name them plainly; that is the cheap, correct move.
7. **Any place a test would need a seam the production code does not offer.** The last batch's
   C5 rows failed exactly here — if the referee choreography cannot be built as written, say so
   rather than improvising a variant.
8. Judgment calls, deviations, anything wrong you found in the plans.
9. Owner questions under `⚠ OWNER DECISIONS REQUIRED (n)`.

## Stop conditions

Both phases implemented per their plans · every test you wrote green · L2 green per phase · one
L4 reconciled · lint and type checks clean · Review logs written · handoff complete · both
checkpoints committed with explicit paths (never `git add -A`).

**Not reasons to continue:** a coverage figure; a mutation you thought of; a test for a row you
were not asked to exercise; tidying outside the perimeter.

If you hit a contradiction, an unbuildable fixture, or a required file that does not exist —
**stop and report it as a card.** Five such problems were found and ruled before you started;
finding a sixth is a good outcome. Improvising past one is the expensive failure.
