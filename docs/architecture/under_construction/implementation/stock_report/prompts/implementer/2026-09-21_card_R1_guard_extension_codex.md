---
phase: 10 (follow-up, owner card R-1)
role: implementer
round: 1
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Codex
---

# Owner card R-1 — teach the write-site guard four more constructs

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/implementation-executor.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

Authority: `SR/planning/intention.md` **§5B MC-2 "The guard"** — RATIFIED, and **amended by the
owner today** with the four forms below plus an exclusions note. Read that section first; it wins
over any plan. Your row is **plan 10 C4(k)**, authored on the same ruling.

Source finding: `SR/handoffs/reviewer/2026-09-21_batch_C2_review_2_handoff.md`, finding **R-1**.

**This is a small, self-contained change.** One test-support file, one test file, one plan Review
log entry. Do not touch production code — there is nothing to fix in it.

## Background, in one paragraph

MC-2's rule is that a task's state may never be written without the stock board being told. The
guard (`test_task_state_write_sites_are_registered`) enforces it by AST-scanning `beyo_manager/`
and `scripts/`, collecting every task-state write and failing the build on any site not in a
checked-in registry. It is strong for the forms it recognises. The batch C2 re-reviewer planted
eleven shapes and **four still passed unnoticed**. Nothing in the codebase writes state those ways
today, so this is a blind spot in the alarm, not a live leak.

## The four constructs to collect

In `app/tests/unit/services/commands/stock_report/_task_state_write_scanner.py`:

1. **The table object rather than the mapper** — `Task.__table__.update()…values(state=…)` and
   `update(Task.__table__)`. This is class **(c)** in another spelling, and it is the one the
   team already writes by habit.
2. **`for`-target and `with … as`-target** attribute writes — `for task.state in …`,
   `with … as task.state`. Class **(a)**: the target is an attribute named `state`, it is simply
   not bound by a plain `Assign` node.
3. **`setattr` through `builtins`** — `builtins.setattr(task, "state", …)`. Class **(b)**.
4. **Dict-unpacked keyword** — `Task(**{"state": …})`. Class **(d)**: a `state=` keyword supplied
   by `**` rather than written literally.

Collect them **by construct, not by spelling** — that clause is ratified and it is the whole
point. An aliased import, an annotated form or an unusual binding of the same construct must all
be seen.

## Your row — plan 10 C4(k)

Plant all of the above **in one live file at once** and assert the guard fails on every one, each
reported as an unregistered site.

**Site the plants at EOF** of plan 10 §7's already-authorized perimeter file
(`app/beyo_manager/services/commands/tasks/update_task.py`), after every registered line, so no
registered site's line number moves. This matters: the registry is keyed by `(path, line)`, and a
plant inserted mid-file shifts entries and produces failures that look like detections but are
only drift. I made exactly that mistake today and had to re-run the measurement clean.

**Named mutation:** revert each new collector extension in turn → the corresponding plant goes
unnoticed. **Run each one, observe red, revert, and prove the revert with `git diff --quiet`.**
Four extensions, so four probes. Do not collapse them into one run — a mirrored guard can pass as
a *combination* while each individual line is inert (lesson L-36 from the same review).

Also fold **N-12**: the guard test module's docstring omits class (f). Correct it and mention the
four new forms while you are there.

## Environment

**Set `BEYO_TEST_SLOT=r1` on every pytest command** — `pytest.ini` carries `-n 6 --dist loadfile`,
so even a single-file run claims six worker databases.

```
cd app && BEYO_TEST_SLOT=r1 PYTHONPATH=. pytest tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py
cd app && BEYO_TEST_SLOT=r1 PYTHONPATH=. pytest -m 'not e2e'
```

**Your gate is 23 failures, not 21** — the published 21-ID set plus the two
`test_database_isolation` IDs that are red under any named slot (master plan §10 ruling). That is
a pass. Baseline before your change: **23 failed / 3668 passed / 1 skipped**.

**Clean baseline for the guard file specifically: `7 passed`.** Confirm that before you start, so
you can tell a detection from a pre-existing failure.

## What not to do

- **Do not change production code.** If you believe a production file must change, stop and report
  — that is an owner decision.
- **Do not register anything in the registry.** There are zero live instances of these four forms
  in `beyo_manager/` or `scripts/`. Grep and confirm this yourself, and **report what you find**.
  If you find a live instance, stop and report rather than registering it.
- Do not widen the scanner's roots. `tests` and `migrations` stay excluded — that exclusion is
  recorded in §5B and the migrations half is an **open owner question**, not yours to settle.
- Do not edit `master_plan.md`, the intention, or any criterion cell — plan Review log entries
  only. **Commit with explicit paths, never `git add -A`. Never push.**

## Handoff

`SR/handoffs/implementer/2026-09-21_card_R1_guard_extension_handoff.md`: the diff · C4(k) green
with all plants caught · **each of the four mutations observed red and reverted, with its
`git diff --quiet` proof** · your grep for live instances of the four forms · N-12 folded · one L4
at 23 with both ID diffs and reconciled arithmetic · anything you found wrong · owner questions
under `⚠ OWNER DECISIONS REQUIRED (n)`.

Checkpoint message: `CHECKPOINT (not approved): owner card R-1 — guard extension`.

## Stop conditions

All four constructs collected · C4(k) armed and each of its four mutations red and reverted ·
zero production-code changes · zero new registry entries · N-12 folded · one L4 at 23 · lint clean
· Review log written · handoff complete · checkpoint committed.
