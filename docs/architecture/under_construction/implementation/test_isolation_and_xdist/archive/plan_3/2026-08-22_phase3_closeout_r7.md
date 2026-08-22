---
plan: 3
role: implementer
round: 7
date: 2026-08-22
project: test_isolation_and_xdist
---

# Session prompt — plan 3 closeout r7, `test_isolation_and_xdist`

## 1. Role and mode

**The last implementation session of this project.** Phase 3 was APPROVED by re-review r6; this
round is the closeout work the approval routed forward, plus one owner decision that landed after
it. Nothing here is a defect in the approved work.

Four items, all small, all in files you already own:

1. **Retire the perturbation harness** — owner decision, 2026-08-22.
2. **F1** — C8's `--dist` assertion accepts one spelling of a four-spelling option.
3. **F4** — `.env.example`'s reclamation command cannot run, and four `Makefile` targets share the
   gap.
4. **N4** — delete `app/run_pytest_suite.py`, unreferenced dead scaffolding.

**Resolve exactly these four. Add nothing else.** The approved code is approved.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Branch `feat/test-isolation-xdist`.

**Read first, by absolute path, as this session's doctrine:**
`/Users/davidloorenz/agent-skills/pipeline-charter.md` (including **"Test-evidence scope and
reuse"** and **"The owner layer"**) and `/Users/davidloorenz/agent-skills/implementation-executor.md`.
**The charter gained rules 12, 13 and 14 today, promoted from this project. Rule 13 is what F1 is
an instance of; read it before writing the repair.**

**Read then:** `handoffs/reviewer/2026-08-22_phase3_rereview_r6_handoff.md` — F1 at §7, F4 at §7,
its §10 documentation-perimeter enumeration, and §11's "verified correct", which is settled ground
you do not disturb. Then `plans/plan_3.md` §4 task 1 (what the harness was for) and §7.

## 2. Gate check — stop and report if any is false

- `git status --porcelain` is empty.
- `plans/plan_3.md` frontmatter reads `state: APPROVED`.
- `git diff 4b5719d HEAD -- app/` is empty at entry — the approved code is untouched since its
  stamp.
- The architecture graph reports 0 pending, 0 diagnostics.

*(Gates here are written against diffs, never against `HEAD` equalling a sha — standing rule 8,
earned five times in this project, twice by prompts I wrote.)*

## 3. Allowed file perimeter

The gate commit verifies this against `git diff`; anything outside is a finding.

- `app/pytest.ini` — remove the `phase3_collection_probe` marker (item 1), nothing else.
- `app/tests/conftest.py` — remove the `BEYO_TEST_COLLECTION_PROBE` branch (item 1), **leaving
  `BEYO_TEST_COLLECTION_ORDER` untouched.**
- **Delete** `app/tests/connecteam/test_00_phase3_collection_probe.py`,
  `app/tests/integration/test_50_phase3_collection_probe.py`,
  `app/tests/unit/test_zz_phase3_collection_probe.py`.
- **Delete** `app/run_pytest_suite.py`.
- `app/tests/integration/infrastructure/test_database_isolation.py` — F1 only.
- `app/.env.example`, `app/Makefile` — F4.
- `master_plan.md` (§6.1, §6.6, §8), `plans/plan_3.md` (§7 and frontmatter), your handoff.

**Nothing under `app/beyo_manager/`, no requirements manifest, no
`app/tests/database_isolation.py`.**

## 4. Item 1 — retire the perturbation harness

**Owner decision, 2026-08-22**, answering re-review r4's N5. The harness did its job: task 1's
unstable set came back **empty**, so no test in this suite is position-sensitive. It ships inert,
which task 1 required — but nothing schedules its removal, three consuming projects inherit it, and
`pytest.ini`'s marker describes itself as *"temporary phase-3 collection perturbation probe"*,
which is a lie in a config file that ships forever.

Remove: the three probe modules, the `phase3_collection_probe` marker, and the
`BEYO_TEST_COLLECTION_PROBE` branch in `pytest_collection_modifyitems`.

**Two things must survive, and mixing them up is the only way to get this wrong:**

- **`BEYO_TEST_COLLECTION_ORDER` stays.** It is phase 2's reversal hook, it is published in master
  plan §6.1, and it is a different mechanism that happens to live in the same function.
- **Collection must not change.** The probes are filtered out when the variable is unset, so
  deleting them removes zero *selected* tests. **Verify this by ID count, not by pytest's summary
  line** — that line reports a pre-hook total and is misleading here: it shows `2600/2601` where
  the true selected count is 2599. Use `pytest -m 'not e2e' --collect-only -q | grep -c '::'`.
  Expected: **2599 before and after.** If it moves, stop and report.

Record in `master_plan.md` §6.6 that the harness existed, what it measured (an empty unstable set),
and that it was retired at closeout — the *finding* is permanent even though the instrument is not,
and `plans/plan_3.md` §4 task 1 documents how to rebuild it in an hour if a future phase needs it.

## 5. Item 2 — F1

`app/tests/integration/infrastructure/test_database_isolation.py:120-123` asserts the `--dist`
contract as the adjacent pair `--dist` `loadfile` only. `--dist=loadfile` is the same option and
false-reds:

> `AssertionError: shipped parallel default is missing --dist loadfile: ['-ra', '--strict-markers',
> '--strict-config', '-n', '6', '--dist=loadfile']`

Measured by review r6: `1 failed, 52 passed`. The message is false in every particular — the option
was accepted and honoured, and that run showed none of the cross-worker interference that appears
when `--dist` is genuinely absent.

This is **charter rule 13's second clause**, and the instructive part: the worker-count half of this
same assertion was widened to all four spellings two rounds ago to fix S1 and S2, and the adjacent
`--dist` half was written as a literal in the same function. *When a repair converts a literal to a
contract, it converts every literal in that assertion.*

> **The correction, verbatim from review r6:** Accept both spellings, as the worker-count assertion
> already does: `arg == "--dist" and next == "loadfile"` **or** `arg == "--dist=loadfile"`.

**While you are in that predicate, delete the dead clause** review r6 recorded as F6, line 113:
`arg.startswith("-n") and arg != "--"` — `"--"` cannot start with `-n`, so the second half is
unreachable and reads as load-bearing.

**Named mutation, site named** (`app/pytest.ini`, the configuration): set `addopts` to
`--dist=loadfile` and run the criterion module. **Contract: green after the repair** — that is the
repair. Then set `addopts` with `--dist loadfile` removed entirely: **must be red** on the dist
assertion, because that sub-check is guarding a real hazard — under per-test `load` mode review r6
measured cross-worker template corruption, C6's temporary revision wedging another worker's
template. Record both sides.

## 6. Item 3 — F4

`app/.env.example:12` reads
`# BEYO_RECLAIM_LEGACY_TEST_DATABASES=1 pytest -m 'not e2e' -n 0`. Master plan §6.1's row is
`BEYO_RECLAIM_LEGACY_TEST_DATABASES=1 PYTHONPATH=. pytest -m 'not e2e' -n 0`, and §6.1 opens with
*"`PYTHONPATH=.` is required."*

Measured, not inferred:

```
$ env -u PYTHONPATH pytest -n 0 --collect-only -q tests/integration/infrastructure/test_database_isolation.py
ModuleNotFoundError: No module named 'beyo_manager'
```

So an operator who copies the documented one-time reclamation command verbatim gets an import error
and the sweep never runs. Project standing rule 5 — *an environment variable's documentation surface
is part of its contract* — was earned by OD-7 on this exact file.

> **The correction:** add `PYTHONPATH=.` to `.env.example:12`, matching §6.1 exactly.

**The same gap, pre-existing, in the other operator surface:** all four `app/Makefile` test targets
(`:36,39,42,45`) are bare `pytest …` with no `PYTHONPATH=.`, while the `worker:` target three lines
below does export it. Fix the family — four targets, one prefix each. This is not phase-3 drift;
it is the passing-glance clause, and F4's fix should cover it.

**Verify by running one Makefile target** (`make test-unit` is ~9 s) rather than by reading. If a
target already worked because of some other mechanism, say so and leave it.

## 7. Item 4 — N4

Delete `app/run_pytest_suite.py`. `git grep run_pytest_suite` returns nothing outside the file
itself; it calls `pytest.main(["-x"])` from inside a running asyncio loop with no marker filter, so
since the parallel default it would spawn six workers and include `e2e`. Charter rule 4, no dead
scaffolding.

**Confirm the grep yourself before deleting** — an unreferenced file is a claim about the whole
repository, and that is the one hypothesis here that is repository-wide by construction.

## 8. Evidence budget

**This session's L4 budget is exactly 2 runs**, both on the tree you hand over:

1. **The closing stamp at the shipped default** — bare `PYTHONPATH=. pytest -m 'not e2e'`, which is
   six workers. This becomes the phase's published baseline and **the coordinator's gate stamp
   cites it**, so it must be on the exact tree you hand over.
2. **The `-n 0` serial comparator** — §8 publishes both, and removing the harness changes what is
   collected even though it should not change what is *selected*. This is the run that proves it.

Expected, and **a difference is a finding, not a number to publish**: `21 failed / 2578 passed` at
the shipped default and `21 failed / 2577 passed / 1 skipped / 1 deselected` under `-n 0`, the
phase-2 21-ID set, `comm` empty in both directions, collection **2599**.

Each run carries tree identity — SHA plus asserted `git status --porcelain`, or SHA plus a
`git diff` digest if dirty — the enumerated failing-ID set, and both `comm` directions.
**State your L4 count as a number.** Anything beyond these two needs the charter's authorization
line written **before** the run.

**Charter, amended today:** the stamp is defined by the tree, not the count. If you change anything
after stamping, the stamp is void and **re-taking it is not over-budget** — two rounds in this
project lost their stamp to the opposite reading.

Everything else is L1/L2. The `pg_stat_activity` peak is 25 of 100, carried from r2 — cite it, say
it is carried, do not re-measure.

## 9. Scope fences

- **Do not touch the approved work.** `app/tests/database_isolation.py` and everything in
  re-review r6 §11 are settled.
- **Do not change the failing-ID set.** The 21 IDs are this project's product and three other
  projects consume them. If a repair moves them, stop and report — that outranks finishing.
- **`BEYO_TEST_COLLECTION_ORDER` is not the harness.** See §4.
- **Do not write to `.archgraph/`.** The graph is at 194/291 with nothing pending. One known
  summary defect is the coordinator's to fix separately.
- **F7 is out of scope** — `architecture/15_testing.md` documents a `pytest.ini` this repo has
  never had. Pre-existing, unrelated, and not yours.
- **A published handoff is never edited.** Corrections go in yours.

## 10. Closing protocol

1. **The closing L4 stamp at the shipped default, on the tree you hand over**, with tree identity,
   the enumerated failing-ID set, and both `comm` directions. Plus the `-n 0` comparator.
2. **One evidence record per named mutation**, at its named site, definition-vs-call-site stated,
   both sides computed — charter rule 12: one mutation per sub-check, and which bites on which.
3. **Collection proof for item 1**: the ID count before and after, by `grep -c '::'`, not by
   pytest's summary line.
4. **Document writes**: `master_plan.md` §6.1 (F4's command), §6.6 (the harness's retirement and
   what it measured), §8 (the final baseline row, both invocations, with the tree). The §3 tracker
   row is the coordinator's.
5. `plans/plan_3.md` frontmatter → `state: APPROVED` with a closeout note; **do not invent a new
   state** — this round runs after approval, not before it.
6. **Review-log entry** in `plans/plan_3.md` §7.
7. **Handoff** at `handoffs/implementer/2026-08-22_phase3_closeout_r7_handoff.md`, frontmatter
   `plan: 3` / `role: fix` / `state` / `date` / `actor`. Body: what changed, the counts, your
   **cycle-scoped** write perimeter, mutation-probe files listed separately with checksums, every
   probe database and its disposition, and **your L4 count as a number**.
8. **Charter rule 14, new today and relevant here:** if you do not implement a correction quoted
   above, say **which one and why**, in its own section. Divergence is often right; undeclared
   divergence costs the next reader a finding on a non-defect.
9. Anything only the owner can settle goes in the handoff as a **decision card**. If nothing does,
   one line saying so.
10. Your final chat message follows the charter's **owner layer**. Not a paste of the handoff.

The handoff file, not your chat message, is what the coordinator consumes.
