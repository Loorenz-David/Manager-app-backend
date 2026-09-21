---
phase: 8A
role: implement
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
agent: Codex (terra)
---

# Phase 8A — implement the assignment match preview

You are a **Codex** session. Skills are not auto-loaded for you, so **read these two files by
absolute path first and follow them as session doctrine** — they are plain markdown:

1. `/Users/davidloorenz/agent-skills/implementation-executor.md`
2. `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

**Your plan is `SR/plans/plan_8A.md`. It is the task list and it wins over this prompt.**
Its authority is `SR/planning/intention.md` **§14G** and contract **MC-21** — RATIFIED, and
they win over the plan. Read §14G before you write code.

HEAD at dispatch: `ba961b0`. Batch C1 is APPROVED; phases 1–8 and 11 are VERIFIED and shipped.

## This round has no tester and no independent Claude reviewer

By owner ruling (2026-09-21, master plan §3B), phase 8A runs
**projection → implement → review**, both halves on Codex. There is no verification-engineer
session behind you. **So you own the proof as well as the code:**

- every criterion row in plan 8A gets a test asserting **that row's exact outcome at that row's
  boundary**;
- every row whose mutation cell **names a site** gets that mutation run, observed red, and
  reverted;
- every cell that is a **deliberate class-2 blank** (the note says so in the cell) gets a site you
  choose on the real code, run, and **reported as a proposed backfill** in your handoff — you do
  not edit the plan cell;
- report `executed == declared`, with the per-criterion summands printed. Plan 8A §7 records the
  declared set as **26** for this round; derive it yourself from the table and say so if you get
  a different number.

## The two halves, and why they are verified differently

**Half 1 — the extraction. This is a refactor of APPROVED code.** MC-21 requires one
implementation of the acceptability decision: it evaluates every MC-13 phase-3 check **in MC-13's
precedence order** and returns per-check results. `create_stock_task_assignments` consumes the
first failure; the preview consumes the whole list.

`_phase3_reason` today is already a pure function of fetched entities — no I/O — which is why
this is a move, not a rewrite. **The checks, their order and their reason strings do not change.**

**Its proof is that plan 8's existing suite passes unchanged.** Do this explicitly:

```
# before you touch anything
PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py
# after the move
PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py
```

Paste both results in your handoff. **Write no new criterion tests for this half** — plan 8A says
so deliberately and explains why. Adding parallel tests here is over-specification and will be
held against the round, not credited to it.

**Half 2 — the preview endpoint.** New surface, ordinary criteria, armed as above.

## Things that will catch you

- **`quantity` is a matched criterion, not metadata.** `build_item_property_bag` sets
  `bag["quantity"]`. Omitting it from the evaluation silently mis-answers every quantity rule.
- **Stored values win** when an item resolves by `article_number`/`sku`; the supplied values are
  the no-item-yet path (plan 8A C3(f), owner card 2). The response's `values_source` says which
  was used. Getting this backwards makes the preview answer `true` where `create` answers
  `false`, which is precisely what MC-21 forbids.
- **Rule 16:** `ACTIVE_ASSIGNMENT_STATES` / `TERMINAL_ASSIGNMENT_STATES`, never a spelled list.
- **Rule 17:** moving a row's proof to a narrower surface is the **owner's** call. If you think a
  row can only be proven somewhere cheaper than it names, **stop and report** — do not quietly
  relocate it.
- **Rule 19:** every new test file needs a name unique across the **whole** test tree. This repo
  has no `__init__.py` under `tests/`, so pytest keys modules by bare filename; a duplicate is a
  *collection error* in which the second file silently never runs. Prefix the domain.
- **§10 `client_id` fact:** ids are ULIDs with no monotonic counter (measured: 977 of 1999
  consecutive pairs out of order). Never assume creation order.
- **Do not copy plan 8 C5(a)'s two-session race fixture.** It was measured this batch **not to
  force its race**. This phase is read-only and needs no concurrency row.

## Names

Plan 8A §4 lists every file and symbol. Master plan §6's registry has **not yet been updated**
with them (the orchestrator does that) — **plan 8A is authoritative for names this round.** If a
name in plan 8A collides with an existing one in §6, stop and report rather than choosing.

## Environment — and one hard coordination rule

From `app/`: **L1** `PYTHONPATH=. pytest <file>` (whole file, never `-k`). **L4**
`PYTHONPATH=. pytest -m 'not e2e'` (`pytest.ini` adds `-n 6 --dist loadfile`).

**Baseline: 21 failed / 3547 passed / 1 skipped** at `798fc69`; the 21 failure IDs are the
published set in
`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3.
Diff your failure IDs against that set **in both directions** and print both. Reconcile the pass
count exactly.

> **⚠ Only one workstream may run the suite at a time.** The test databases are fixed names
> (`beyo_test_main_gw0…gw5`, cloned per xdist worker). Another workstream (batch C2) is active in
> this same repository. A concurrent full run corrupts both results **and looks like a genuine
> failure**. Confirm with the owner before your L4, and take exactly one.

## Your handoff

`SR/handoffs/implementer/2026-09-21_phase_8A_implement_1_handoff.md`: checkpoint SHA on a clean
tree · the before/after plan-8 suite results for the extraction · the one L4 with both ID diffs
and the pass-count arithmetic · the production write perimeter · the **mutation ledger**
(`executed == declared`, summands printed) · proposed backfills for every class-2 blank you
sited · rows you could not arm, classified and explained · judgment calls and anything you found
wrong in the plan · owner questions under `⚠ OWNER DECISIONS REQUIRED (n)`.

Commit checkpoints as `CHECKPOINT (not approved): …` with **explicit paths, never `git add -A`**.
**Never push.** Do not edit `master_plan.md` or any criteria cell; plan Review log entries only.

## Stop conditions

Behaviour implemented per plan 8A · every row armed or explicitly classified · the extraction's
before/after suite results recorded · one L4 reconciled · lint and type checks clean · Review log
written · handoff complete · checkpoint committed.

**Not in scope:** anything in plans 9–14, refactoring beyond MC-21's extraction, tidying outside
the perimeter, or extra tests for the extraction half. If you believe something else is broken,
**report it — do not fix it.**
