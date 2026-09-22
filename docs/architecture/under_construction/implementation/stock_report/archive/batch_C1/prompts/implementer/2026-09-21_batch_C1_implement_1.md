---
batch: C1
phases: [8, 11]
role: implement
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Sonnet
---

# Batch C1 implementation — phases 8 then 11

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/implementation-executor.md` — **including its section "When
  the project runs a tester", which changes your job. Read that section before Task 0.**
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Read in order: `SR/master_plan.md` (**§3B first**, then §6, §9, §10), then `SR/plans/plan_8.md`,
then `SR/plans/plan_11.md`. The intention is `SR/intention.md` — RATIFIED; it wins over any plan.
HEAD at dispatch: `5b9ceb7`, clean tree.

## This project runs a tester. Your job is narrower than the executor's default.

A separate Opus verification engineer runs **after you and before the reviewer**, on your finished
code. **These move to it and you skip them entirely:**

- Task 0's row-level coverage map, in both directions;
- closing step 1½ — the named mutations and the `executed == declared` count;
- closing step 1¾ — proving each guard able to fail;
- the named-mutation ledger in your handoff.

**Do not run a single mutation. Do not transcribe the criteria tables into tests row by row.**

**What stays yours, unchanged:** make the planned behaviour true; the tests you find *useful to
build it* (red → green on the paths you write, outcomes at a public boundary — charter rule 2);
the existing regression suite; lint and type checks; closing steps 1, 2, 3, 4, 5; the Review log
entry; the graph delta; rule 17's contradiction check.

**Do not pad the test files to look covered.** A row you did not exercise, *named as such*, costs
the tester minutes. A weak test that looks like coverage costs a review round. Naming a gap is the
cheap, correct move here — it is not a failure and it will not be held against you.

## Scope and order

**Phase 8 first, then phase 11** (§7.2: 11 depends on 8). Phase 11 may start once phase 8 is
implemented with its L1 tests green — it does not wait for a review.

Phases 1–7 are **APPROVED and VERIFIED**. Their code is shipped. You call it; you do not change
it. If you believe a phase 1–7 file must change, **stop and report** — that is an owner decision,
not yours.

**Phase 9 does not exist yet** (it is batch C2). Plan 11's fixtures were folded to say so: where a
row once reached a terminal state through `PR`, it now uses `move_assignment` directly. If you
meet a `PR` reference anywhere in plan 11, that is a fold I missed — report it, do not improvise.

## What changed in your plans this morning — read the plans, not this summary

Both plans were folded from the batch C1 projection and six owner cards were ruled. The plan files
are authoritative and complete; this list exists only so nothing surprises you:

- **40 previously empty mutation cells are now filled.** They are the **tester's** instructions,
  not yours. You do not run them. But two of them tell you something about the code you are about
  to write, and you should read them as design constraints: plan 8 C4(k) requires the create
  response to be sorted **ascending by `item_id`**, and plan 8 C5(b) requires the batch commands
  to acquire item locks in **sorted** order.
- **Plan 8 C5(b) is a new criterion row** — the caller's lock order, proven with two real
  sessions. Your job is the production side: acquire the locks in sorted order, deterministically.
- **Plan 8 C1(j) and C1(k) now assert `count_writes(...) == 0`.** The refusal must happen in
  phase 3, *before* any INSERT is attempted. Do not rely on the unique index to produce the
  refusal — the index is the backstop, and a test now checks that you did not reach it.
- **Plan 8 C4(l) is the fourteen-key `serialize_stock_task_assignment` shape** with nested `item`
  and `task`, not seven flat columns. This means `bm/domain/stock_report/serializers.py` — with
  `serialize_stock_task_assignment`, `serialize_item_compact` and `serialize_task_compact`
  (master plan §6.1) — is **due in this phase**. It is in plan 8 §4's file list.
- **Plan 8 C6(g) and plan 11 C1(c)** had unbuildable fixtures and were rebuilt: a task's second
  assignment is reached through a **`failed`** one, never a resolved one (intention §14F F9
  refuses re-assigning an item Scanner has reported, on any row).
- **Plan 11 C4(h) is WITHDRAWN.** The row is struck through in the table. Do not implement it and
  do not write a test for it.
- **Plan 11 C4(b) and C5(b) are marked known-unarmed.** Implement the behaviour as specified; the
  absence of a mutation cell there is deliberate and recorded.

## Standing rules that bite in these two phases

From master plan §9 — read them all, but these are the ones this batch trips over:

- **Rule 16** — `ACTIVE_ASSIGNMENT_STATES` / `TERMINAL_ASSIGNMENT_STATES`, never a spelled list.
  Both plans carry rows whose named mutation is exactly a hand-typed list. A literal
  `state IN ('resolved', 'failed')` is a review finding. The one exception is the DB partial
  indexes, fixed in phase 1.
- **Rule 17 (new today)** — relocating a row's test to a narrower surface is a **criterion change
  and the owner's alone**. If you judge that a row can only be proven at a narrower boundary,
  declare it and stop. Do not quietly prove an endpoint row at a helper.
- **Rule 18 (new today)** — every public signature you register in §6.5 or §6.1 must be pinned by
  a row in your own plan. If you add a name and no row pins it, say so in your handoff.
- **Rule 7** — statement counting only through `record_statements`, and now for one more ratified
  case: plan 8 C1(j)/C1(k)'s refused-before-the-write clause.
- **§10's `client_id` fact (new today)** — ids are ULIDs with no monotonic counter, so **creation
  order is not id order**; measured at 977 of 1999 consecutive pairs out of order. Anything that
  must come back in a defined order sorts explicitly. Never rely on insertion order.

## Environment

From `app/`:
- **L1** `PYTHONPATH=. pytest <file>` — the whole file, never `-k`.
- **L2** the phase's test folders plus the folders of every production module the phase edits —
  for phase 11 that includes `tests/integration/services/commands/tasks`, `…/task_steps`,
  `…/items`.
- **L4** `PYTHONPATH=. pytest -m 'not e2e'` (pytest.ini adds `-n 6 --dist loadfile`). ~2–3 min.

**Baseline: 21 failed / 3445 passed / 2 skipped**, the 21 IDs exactly the published set in
`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3.
Diff your failure IDs against it **in both directions** and print both diffs. A 22nd failure is
either yours or the known load-dependent drifter
(`test_c3_real_concurrent_open_insert_translates_the_loser[model]`) — capture the ID set before
repeating any anomalous run, and say which it was.

**Budget: L1 as you go, one L2 per phase, exactly one L4 at the end.** Nothing else.

Known hazards for these phases are in §10; (d) is the one that catches people —
`TestClient` router tests fake `get_db` and `run_service`.

## Your handoff — the tester contract

At `SR/handoffs/implementer/2026-09-21_batch_C1_implement_1_handoff.md`, frontmatter
(`batch: C1`, `phases: [8, 11]`, `role: implement`, `round: 1`, `state`, `date`, `actor`):

1. **Checkpoint SHA per phase, on a clean tree** (`CHECKPOINT (not approved): …`). Never push.
2. **The one L4 stamp**, with the failure-ID delta in both directions and the pass-count
   arithmetic reconciled (`3445 + n new = ?`).
3. **The production write perimeter** — every file you created or edited, explicitly listed.
4. **"Tests I wrote → the row each aimed at"**, stated as *claims*, not evidence. The tester
   judges sufficiency; you just say what you were aiming at.
5. **One load-bearing pointer per criterion** — the `file:symbol` where the behaviour is made
   true. A hint for the tester, never authority. For the concurrency rows, say **where each lock
   is taken and where the post-lock re-read sits**; that is the pointer the tester most needs and
   the one it cannot cheaply find.
6. **Rows you know you did not exercise.** Name them plainly.
7. **Any place a test would need a seam the production code does not offer** (nowhere to hold a
   lock, no injectable clock). Say what the smallest seam would be; do not add it speculatively.
8. Judgment calls, deviations, and anything you found wrong in the plans.
9. Owner questions as decision cards under `⚠ OWNER DECISIONS REQUIRED (n)`.

## Stop conditions

Stop when: both phases' behaviour is implemented per their plans · every test you wrote is green
· L2 green per phase · one L4 taken and reconciled · lint and type checks clean · the Review log
entry written in each plan · the handoff complete · both checkpoints committed.

**Not reasons to continue:** a coverage figure; a mutation you thought of; a test for a row you
were not asked to exercise; tidying code outside your perimeter.

If you hit something you cannot resolve — a contradiction between a plan and the intention, a
fixture that cannot be built, a required file that does not exist — **stop and report it as a
card.** Six such problems were already found and ruled before you started; finding a seventh is a
good outcome, not a failure. Improvising past one is the expensive failure.
