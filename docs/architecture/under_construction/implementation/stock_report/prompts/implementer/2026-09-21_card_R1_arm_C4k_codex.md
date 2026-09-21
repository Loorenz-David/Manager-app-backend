---
phase: 10 (follow-up, owner card R-1)
role: implementer
round: 2
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Codex
---

# Arm plan 10 C4(k) — and C4(j) with it

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/implementation-executor.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Plan: `SR/plans/plan_10.md`, rows **C4(k)** and **C4(j)**. Authority: `SR/planning/intention.md`
**§5B MC-2 "The guard"** — RATIFIED, including today's four-forms amendment.

Previous round: `970096f` ("Extend task-state write-site guard") and its handoff
`SR/handoffs/implementer/2026-09-21_card_R1_guard_extension_handoff.md`.

**This round writes tests only. The collector is already correct — do not change it.**

## Why you are here

Round 1 extended the collector and I verified it independently: I planted all five shapes and the
guard **caught every one**, then reverted clean. That work is good and is not in question.

What round 1 did not do is **arm the row**. Its only change to the test file was the module
docstring, which reassigned C4(k) to "the tester's arming work". **A docstring is not a test** —
this pipeline has a standing lesson on exactly that shape (L-32: a guard's docstring is not a
guard).

The consequence is concrete. The guard's C4(a) control rows assert facts about the **current
tree**, and there are **zero live instances** of these constructs. So if someone reverted a
collector extension tomorrow, **nothing in the suite would go red**. The detection exists in the
code and is pinned by nothing. That is the row-that-cannot-fail shape this project has found
eleven times in one batch, and it is what this round closes.

**C4(j) is in the same state** — there is no `test_c4j_*` anywhere; its five forms were only ever
verified by manual plant-and-revert. Same harness, ~5 more cases. Arm it in this round too.

## How to arm it — use the seam that already exists

**Do not plant constructs into production files.** A permanent plant would make the guard fail
forever, and a temp-file plant is fragile.

`_task_state_write_scanner.py` already exposes the right seam: **`_FileVisitor`**, which walks one
parsed module and collects into `.sites`. Drive it over **source strings**:

```python
tree = ast.parse(SOURCE)
visitor = _FileVisitor("beyo_manager/_probe.py", _collect_import_aliases(tree))
visitor.visit(tree)
assert visitor.sites  # collected
```

Mirror how `collect_write_sites()` drives it (same file, ~line 345) — in particular pass the
import aliases, because several constructs only resolve through them.

One parametrized test per row, one case per construct, each asserting the construct **is
collected** (and assert something about *which* site, not merely that the list is non-empty — a
test that passes on any collection is barely a test).

### C4(k)'s five cases — all five verified by me to be caught today

1. `Task.__table__.update().where(Task.client_id == cid).values(state="working")`
2. `update(Task.__table__).values(state="working")`
3. `for task.state in states:` (and a `with … as task.state` case if cheap)
4. `builtins.setattr(task, "state", "working")`
5. `Task(**{"state": "working"})`

### C4(j)'s five cases

The annotated assignment `task.state: TaskStateEnum = …`, a tuple-target assignment writing
`task.state`, an `update`/`insert` reached through an **import alias**, a `Task(…)` reached
through an alias, and raw `text("UPDATE tasks SET state = …")`.

Note `collect_write_sites()` de-duplicates by `(path, line)` — a chained table write visits both
the `.values(...)` and the inner `.update()`. Put each case on its own line and be aware of this
when asserting.

## Named mutations — run them, one per extension

For **each** collector extension, revert it, observe the corresponding case go red, restore it.
**Do not collapse these into one run.** A mirrored guard can pass as a *combination* while each
individual line is inert — that is lesson **L-36**, earned in the review that produced this card.

Prove each revert with `git diff --quiet`.

## Environment

**Set `BEYO_TEST_SLOT=r1b` on every pytest command** — `pytest.ini` carries `-n 6 --dist loadfile`,
so even a single-file run claims six worker databases. A batch D round may be running concurrently.

```
cd app && BEYO_TEST_SLOT=r1b PYTHONPATH=. pytest tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py
cd app && BEYO_TEST_SLOT=r1b PYTHONPATH=. pytest -m 'not e2e'
```

**Clean baseline for that file is `7 passed`** — your round should raise it. **Your L4 gate is 23
failures, not 21** (master plan §10): the published 21-ID set plus the two `test_database_isolation`
IDs red under any named slot. Full-suite baseline: **23 failed / 3668 passed / 1 skipped**.

## What not to do

- **Do not change the collector or any production code.** If you believe either must change, stop
  and report — that is an owner decision.
- Do not register anything in the registry; there are still zero live instances.
- Do not widen the scanner's roots. `tests` and `migrations` stay excluded.
- Do not edit `master_plan.md`, the intention, or any criterion cell — plan Review log entries
  only. **Commit with explicit paths, never `git add -A`. Never push.**

## Handoff

`SR/handoffs/implementer/2026-09-21_card_R1_arm_C4k_handoff.md`: the diff · C4(k) and C4(j) green
with every case asserting a specific collected site · **each named mutation observed red and
reverted, with its `git diff --quiet` proof, one per extension** · the new `N passed` for the
guard file · one L4 at 23 with both ID diffs and reconciled arithmetic · anything you found wrong
· owner questions under `⚠ OWNER DECISIONS REQUIRED (n)`.

Checkpoint: `CHECKPOINT (not approved): arm C4(k) and C4(j)`.

## Stop conditions

C4(k) and C4(j) each armed by a checked-in test whose cases assert specific collected sites · every
named mutation run individually, red, and reverted · zero production-code changes · one L4 at 23 ·
lint clean · Review log written · handoff complete · checkpoint committed.
