---
plan: 10 (follow-up, owner card R-1)
role: implement
state: CHECKPOINT_NOT_APPROVED
date: 2026-09-21
actor: Codex
---

# Card R-1 follow-up — arm C4(k) and C4(j)

`CHECKPOINT (not approved): arm C4(k) and C4(j)`

## Outcome

The follow-up is complete as a tests-only change. The guard now has checked-in source probes for
all required C4(j) and C4(k) constructs. The collector, production code, registry, scan roots,
and acceptance criteria were not changed.

Changed files:

- `app/tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py`
- this handoff
- the owner-card review-log entry appended to `plans/plan_10.md`

The scanner was temporarily mutated for the required proof matrix but every mutation was reverted;
its final working-tree diff is empty. Concurrent edits in `plans/plan_12.md`, `plan_13.md`,
`plan_13A.md`, and `plan_14.md` were left untouched.

## Checked-in test arming

The parametrized C4(j) test covers and asserts the exact site key and class for:

1. annotated `task.state: TaskStateEnum = ...`;
2. tuple target `task.state, other = ...`;
3. `update` imported as an alias;
4. `Task` imported as an alias;
5. raw `text("UPDATE tasks SET state = ...")`.

The parametrized C4(k) test covers and asserts the exact site key and class for:

1. `Task.__table__.update().where(...).values(state=...)`;
2. `update(Task.__table__).values(state=...)`;
3. `for task.state in ...`;
4. `with ... as task.state`;
5. `builtins.setattr(task, "state", ...)`;
6. `Task(**{"state": ...})`.

The helper uses `_collect_import_aliases` and de-duplicates by `(path, line)`, matching
`collect_write_sites()` and ensuring chained table writes do not produce a duplicate assertion.

## Verification

- Targeted guard with `BEYO_TEST_SLOT=r1b`: **18 passed**.
- Ruff on the test module and scanner: **All checks passed**.
- Mutation proof: **9 declared / 9 executed / 9 red / 9 reverted**.
  - Annotated assignment: 1 red.
  - Tuple target: 1 red.
  - Aliased update/insert: 1 red.
  - Aliased `Task`: 1 red.
  - Raw SQL: 1 red.
  - Task table reference: 2 red.
  - `for`/`with` targets: 2 red.
  - Qualified `builtins.setattr`: 1 red.
  - Dict-unpacked constructor: 1 red.
- Every mutation was followed by a passing `git diff --quiet` proof against the scanner.
- L4, `BEYO_TEST_SLOT=r1b PYTHONPATH=. pytest -m 'not e2e'`: **23 failed / 3679 passed / 1 skipped**.
  This is `23 = 21 published failures + 2 named slot-isolation failures`, and
  `23 + 3679 + 1 = 3703` collected tests. The 11 newly added guard cases account for the pass-count
  increase over the prior 3668-pass baseline; no new L4 failure ID was introduced.

## Architecture Graph

The initialized graph was status-checked and the task-state guard node was inspected. This
tests-only round introduces no runtime architectural concept or boundary, so no graph mutation was
appropriate.

### ⚠ OWNER DECISIONS REQUIRED (0)

None for this follow-up.

## Commit / checkpoint

The requested checkpoint remains not approved until the owner accepts the handoff and the plan's
review log entry. No push was performed.
