---
plan: 3
role: review
round: 6
verdict: APPROVED
date: 2026-08-22
actor: Opus 5
---

# Phase 3 re-review r6 handoff — delta-scoped, closing fix r5

## 1. Verdict

**APPROVED.**

No blocking findings. B1 is closed — resolved by a *different* mechanism than review r4
prescribed, and the substitution is the better instrument. S1–S5, N1 and N2 are all resolved.
Two new should-fix findings and five notes, none of which touch the published baseline; all are
routed in §8's carry-forward table.

## 2. What this review concluded

The last real doubt about this phase is gone. The test that was supposed to protect the database
locking — and which passed whether the lock was there or not — now fails the moment the lock is
removed, and it also fails on the subtler one-line change the plan warned about in writing, which
had been shipping green through four rounds. I re-broke the code five different ways to check
that, including one way nobody had tried before. Two small things are worth a follow-up: a
configuration check that would cry wolf if someone spells an option with an equals sign instead of
a space, and a maintenance command in the developer setup file that still cannot be copy-pasted
because it is missing one prefix. Neither changes any number this project publishes, and neither
is worth holding the gate for.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. The one architecture-graph item that would have needed adjudication is
already being handled by the authorised maintenance session and is out of this round's bounds.

---

# Layer 1 — technical review

## 3. Finding 1 — the verified perimeter

`git diff 8501a51 HEAD -- app/`, per prompt §4 (history cannot be used here: the coordinator's
`git add -A` swept fix r5's code into `4b5719d` under a subject describing a different session):

| file | numstat |
|---|---|
| `app/.env.example` | 1 / 1 |
| `app/tests/integration/infrastructure/test_database_isolation.py` | 85 / 8 |

Two files, `+86 / −9` in aggregate — **exactly** fix r5's declared cycle-scoped code perimeter,
and exactly what prompt §2 predicts. **Nothing outside it.** No production code, no `pytest.ini`,
no `app/tests/conftest.py`, no `app/tests/database_isolation.py`, no requirements manifest, no
migration file, no `.archgraph/` path.

Gate checks, all four true at entry: `git status --porcelain` empty;
`git diff 4b5719d HEAD -- app/` empty (this is what sets my L4 budget to 0);
the two-file delta above; graph at **194 nodes / 291 edges / 0 pending / 0 diagnostics**,
revision `e7ab5b2a…`.

**Probe reversion, cited not recomputed** (prompt §4). The three closing checksums reproduce on
my tree, and two of them — `app/tests/database_isolation.py` `86434edf…` and `app/pytest.ini`
`392e7102…` — are byte-identical to the values I published in review r4 *before* applying M4–M7.
My own prior baseline is the proof that fix r5's probes were reverted.

**One correction to the prompt's own arithmetic, not a finding against the round:** prompt §2
attributes `+86/−9` to the criterion module alone. That is the two-file aggregate; the module is
`+85/−8` and `.env.example` is `+1/−1`. The perimeter is unaffected.

## 4. Review r4's findings, one by one

| finding | disposition | verification |
|---|---|---|
| **B1** | **resolved differently** — see §5 | M4 → rows (a)/(b)/(c) red with three distinct errors; M5 → row (c) red. Both re-run at L1 (prompt §5.1 authorises this as the finding's closure) |
| **S1** | **resolved, and its enumeration is now complete** | The guard decides from the option, not from argv shapes. r5 measured `-n 0` and `--numprocesses 0`; **I measured the two spellings it did not** — `-n0` and `--numprocesses=0` — both `52 passed, 1 skipped`, the skip being C8 at `:118` with its own reason string. All four spellings of the option are now covered, across two sessions |
| **S2** | **resolved** | The ini assertion is now a contract (`--dist loadfile` present, `-n` value a positive integer) rather than the literal token sequence `["-n","6","--dist","loadfile"]`. r5's `-n 8` → green is tree-bound and cited. **But the same rule-12 defect now sits on the `--dist` half — finding F1** |
| **S3** | **resolved as specified** | `.env.example:12` now carries `-n 0`, matching r4's quoted correction verbatim. **The resulting command still cannot run — finding F4** |
| **S4** | **resolved** | §6.4 now separates the availability-tolerant isolation-prefix teardown from the two Redis-dependent logout rows; §8 states "Redis reachable at `settings.redis_url`" as an explicit precondition on the phase-3 row and extends the baseline schema to a fourth axis (services). Read, not re-measured — r4 measured both sides |
| **S5** | **resolved** | §6.1's reversed-collection row is now `BEYO_TEST_COLLECTION_ORDER=reverse PYTHONPATH=. pytest -m 'not e2e' -n 0` |
| **N1** | **resolved, and now covered** | Two rows added for `localhost.localdomain` and `ip6-localhost`. **r4's M6 — deleting both literals from `_normalised_endpoint` — left 51 green; it now reddens exactly those two rows and nothing else** |
| **N2** | **resolved** | The hand-constructed sibling-distinctness assertion is deleted from `_assert_concurrent_starts_succeed`. Structurally it removed an assertion, not a row: the diff adds exactly two parametrize tuples and deletes one `assert` line, and the module collects **53** in every one of my nine runs (51 at r4 + 2). The full-suite `+2` to 2599 follows arithmetically from the cited stamp; no collection run was needed |

## 5. B1 — judgment on the new construction (prompt §5.1, item by item)

### 5.1 What the row actually proves

**It proves a different contract than C2 row (c)'s text names, and the different contract is the
right one.** Review r4's prescribed repair — hold a template connection across the copy and assert
the copy waits behind the lock and succeeds — is not implementable: `pg_advisory_lock` is
cooperative between our own processes and has no effect on an external session holding the
template open, so `CREATE DATABASE … TEMPLATE` refuses in the *correct* configuration too. The
implementer was right to build something else. I confirm the coordinator's reading of why.

What shipped asserts: **at the moment `_create_database_from_template` is called, this process
holds a granted advisory lock.** That is precisely plan task 3's invariant — *"the serialised
region is the whole of `_ensure_template` plus the copy"* — and it is deterministic, where any
overlap-timing instrument would have been a flake. The obstruction being removed before the copy
is not a weakness: the held connection is the *detector*, not the hazard.

**So: a different contract, correctly implemented, wearing the old contract's name.** That naming
gap is finding F5 — the same reading trap that produced B1 in the first place, and it costs a
plan-text amendment, not a fix round.

### 5.2 Does the shared connection halve the row's power? — **measured: no, not against the mutations that matter**

The closure does capture one `connection` from the enclosing scope, and only the first probe to
observe its lock closes it. But under **both** named mutations the observer returns false for
**both** probes, so neither closes it and **both** copies fail:

```
M4: [ObjectInUseError('source database "beyo_test_p3current_template" is being accessed by other users'),
     ObjectInUseError('source database "beyo_test_p3current_template" is being accessed by other users')]
M5: [ObjectInUseError(...), ObjectInUseError(...)]
```

The asymmetry would only matter for a defect that removed the lock for one probe and not the
other, which is not a shape any real change takes. The sharper limit is §5.4.

### 5.3 The `asyncio.gather` double-close race — **structurally unreachable, not a flake**

Both probes run in slot `p3current`, so both lock the *same* key
(`hashtextextended('beyo_test_p3current_template', 0)`) on separate sessions. The patched copy runs
**inside** `_template_operation_lock`, so under the shipped code the two probes' observer/close
sequences are mutually excluded by the very lock under test — they cannot interleave. Under M4 and
M5 `lock_held` is false for both, so `close()` is never called at all. There is no configuration
this row can be in where two coroutines reach `close()` concurrently. (The one shape that *would*
make it reachable is §5.4's key narrowing, and that run passed cleanly.)

### 5.4 Does it still bite? — **yes, both, and I found the one shape it does not catch**

| mutation | site | result |
|---|---|---|
| **M4** — `_template_operation_lock` body → bare `yield` | definition, `app/tests/database_isolation.py:381-396` | **3 failed**: (a) `UniqueViolationError`, (b) `InvalidCatalogNameError`, (c) `ObjectInUseError` — three distinct errors, exactly C2's *"each row red with its own error, not one shared string"* |
| **M5** — copy + drop moved outside the lock | **call site**, `start():242-245` | **1 failed** — row (c), `ObjectInUseError`. This is the narrowing plan task 3 warns about in writing, which shipped green through four rounds. **B1's whole point, closed** |
| **M-E** — lock key `template_database_name` → `worker_database_name` (**new shape, nobody has run this**) | definition, same block | **2 failed — (a) and (b). Row (c) stays GREEN** |

**M-E is the honest limit of the new instrument, and it is a note, not a defect.** Narrowing the
key destroys mutual exclusion between workers completely — every process gets its own lock and the
serialised region protects nothing — yet each probe still holds *a* granted advisory lock at its
copy call, so row (c)'s observer says yes and closes the connection. The row checks lock
*presence*, not lock *scope*. C2 as a criterion still catches the mutation, through rows (a) and
(b) reddening; row (c) alone does not. Recorded as **F3** so the next agent does not assume row (c)
covers key changes.

### 5.5 Standing rule 2's companion — **satisfied: exactly one sufficient cause**

Row (c)'s green depends solely on `lock_held`. The only other way the copy could succeed with the
connection still open is `_drop_database_if_exists(template)`'s `pg_terminate_backend`, and that
branch is unreachable here — the seed has already made the template current and marked, so
`_ensure_template` takes no rebuild path. This is not an argument, it is measured: M4's row (c)
raises `ObjectInUseError`, which proves the held connection was still alive at the copy call.

## 6. C8 — the repair and its sub-checks (prompt §5.2)

**Enumerated from the code's branch points, not from the r5 ledger** (project standing rule 4):

| # | branch point | mutation | who ran it | result |
|---|---|---|---|---|
| 1 | skip guard, 4 spellings | `-n 0` / `--numprocesses 0` | fix r5 | both skip, `52 passed / 1 skipped` |
| 1 | — | **`-n0` / `--numprocesses=0`** | **this round** | **both skip, `52 passed / 1 skipped`, skip reason at `:118`** |
| 2 | `--dist loadfile` present | **`--dist loadfile` removed from addopts** | **this round — nobody had** | **red on the dist assertion** (F2) |
| 3 | `-n` value is a positive integer | worker count removed from addopts | fix r5 | red on the worker-count assertion |
| 4 | `PYTEST_XDIST_WORKER` matches `gw\d+` | `PYTEST_ADDOPTS='-n 0'` | fix r5 | red on the env assertion; the guard does not short-circuit it |
| — | tolerance (S2's repair) | `-n 8` | fix r5 | green |

Standing rule 11 is now satisfied — one mutation per sub-check, each named with which bites on
which. Sub-check 2's was missing from the ledger; I ran it (F2).

**The published `1 skipped` is still C8 and still fires under every spelling.** §8's serial
comparator publishes `21 failed / 2577 passed / 1 skipped / 1 deselected` against the shipped
default's `21 failed / 2578 passed`: the arithmetic (2578 = 2577 + 1) identifies the single skip as
C8 without a run, and the guard's four branches are each measured above.

**The skip guard is not over-broad.** `arg.startswith("-n")` could in principle swallow an
unrelated option; `pytest --help` lists no other short option beginning with `-n`, and every long
option in that family (`--nf`, `--no-header`, `--noconftest`, …) begins with `--`, which the
predicate cannot match.

## 7. Findings

### SHOULD-FIX

#### F1 — C8's `--dist` sub-check asserts one spelling of a four-spelling option; `--dist=loadfile` false-reds

**Artifact.** `app/tests/integration/infrastructure/test_database_isolation.py:120-123`.

**Authority.** Master plan §5 rule 12 (*"a criterion asserting a configured value asserts its
contract, not its literal"*) and rule 4; `planning/intention.md` OD-10 (`--dist loadfile` is part
of the default). This is S1's spelling-enumeration defect and S2's literal-vs-contract defect
recurring **in the assertion written to repair both** — the worker-count half got all four
spellings (`-n N`, `-nN`, `--numprocesses N`, `--numprocesses=N`); the `--dist` half got one.

**The defect it would let through.** Not a wrong behaviour — a false red with a false diagnosis, on
a legitimate config edit. Same time-bomb shape as the N4 constant this phase existed to remove.

**Both sides computed (L1, whole criterion module; green side cited from fix r5's `53 passed` on
this tree, checksum-matched):**

| `app/pytest.ini` addopts | result |
|---|---|
| `… -n 6 --dist loadfile` | 53 passed *(cited)* |
| `… -n 6 --dist=loadfile` | **1 failed, 52 passed, 20.69 s** — `AssertionError: shipped parallel default is missing --dist loadfile: ['-ra', '--strict-markers', '--strict-config', '-n', '6', '--dist=loadfile']` |

The message is false in every particular. That the option was accepted and honoured is not an
assumption: the mutated run behaves identically to the shipped default in every other respect —
same 53 collected, same 52 green — and shows **none** of the cross-worker interference that appears
when `--dist` is genuinely absent (F2's run). pytest would have rejected an unparseable value.

**Suggested correction.** Accept both spellings, as the worker-count assertion already does:
`arg == "--dist" and next == "loadfile"` **or** `arg == "--dist=loadfile"`.

#### F4 — `.env.example:12` documents a command that cannot run

**Artifact.** `app/.env.example:12`:
`# BEYO_RECLAIM_LEGACY_TEST_DATABASES=1 pytest -m 'not e2e' -n 0`

**Authority.** Project standing rule 5 (*"an environment variable's documentation surface is part
of its contract"* — earned by OD-7, on this exact file); master plan §6.1, whose row is
`BEYO_RECLAIM_LEGACY_TEST_DATABASES=1 PYTHONPATH=. pytest -m 'not e2e' -n 0`.

S3 is resolved exactly as r4 specified — but r4's quoted correction itself dropped `PYTHONPATH=.`,
and §6.1 opens with *"`PYTHONPATH=.` is required."* Prompt §5.3's expectation that this line now
matches §6.1 character for character is **not met**; it differs by that prefix.

**Measured, not inferred:**

```
$ env -u PYTHONPATH pytest -n 0 --collect-only -q tests/integration/infrastructure/test_database_isolation.py
ImportError while loading conftest '…/app/tests/conftest.py'.
tests/conftest.py:14: from beyo_manager.config import settings
E   ModuleNotFoundError: No module named 'beyo_manager'
```

`pytest.ini` sets no `pythonpath`, so an operator who copies the documented one-time reclamation
command verbatim gets an import error and the legacy sweep never runs. Fails loudly, not silently.

**Same gap, pre-existing, in the other operator surface:** all four `app/Makefile` test targets
(`:36,39,42,45`) are bare `pytest …` with no `PYTHONPATH=.` (`make -n test` → `pytest -m 'not e2e'`),
while the `worker:` target three lines below does export it. Not caused by this phase; reported
under the passing-glance clause because F4's fix should cover the family.

**Suggested correction.** Add `PYTHONPATH=.` to `.env.example:12`, matching §6.1 exactly; consider
the same for the four Makefile targets.

### NOTES

#### F2 — sub-check 2 had no mutation in the ledger; I ran it, and it exposed why `--dist loadfile` is load-bearing

Removing `--dist loadfile` from `addopts` entirely reddens C8 on the dist assertion — a **true**
red, so the sub-check is covered; standing rule 11's enumeration was incomplete in fix r5's ledger,
not in the code.

Worth recording for OD-10: that run also produced **non-deterministic collateral** — run 1
`1 failed, 50 passed, 2 errors`; run 2 `3 failed, 50 passed, 1 error` — including cross-worker
template corruption, where C6's temporary revision leaked into another worker's template:

```
RuntimeError: Migration DDL assertion failed for beyo_test_phase2_template:
expected head p3c6c02deafce4, got 'c1d2e3f4a5b6'
```

OD-10 states *"the per-test `load` mode has never been run against this suite"* and keeps
`--dist loadfile` as part of the default rather than an incidental flag. **That is now measured
rather than asserted**: under `load`, the isolation criterion module is not self-consistent. The
assertion F1 wants respelled is guarding a real hazard.

#### F3 — row (c) observes lock *presence*, not lock *scope*

See §5.4. M-E — key narrowed from the template name to the worker name — leaves row (c) green while
destroying mutual exclusion entirely. C2 still catches it via rows (a) and (b). No fix requested;
recorded so nobody credits row (c) with coverage it does not have. If it is ever cheap to close,
the observer could assert the lock's `objid` equals `hashtextextended(template_name, 0)` rather
than merely existing.

#### F5 — C2 row (c)'s criterion text still names the observer the implementation deliberately does not build

`plans/plan_3.md` §5 C2 row (c) reads *"a held inspection connection overlapping a copy → no
`source database … is being accessed by other users`"*, and the test is still named
`test_concurrent_starts_survive_current_template`. Neither describes what the row now proves —
lock presence at the copy call. **B1 was created by exactly this gap** (a row whose text named an
observer the code did not implement), and leaving it unamended re-arms the trap for the next
reader. The coordinator's fix-r5 consumption entry already states the correct contract; the plan
text and the criterion's own docstring do not. Plan-text amendment, no code change.

#### F6 — dead clause in the skip guard

`app/tests/…/test_database_isolation.py:113` — `arg.startswith("-n") and arg != "--"`. `"--"`
cannot start with `-n`, so the second half is unreachable. Harmless, but it reads as load-bearing.

#### F7 — pre-existing, unrelated to this phase: `architecture/15_testing.md:389-397` documents a `pytest.ini` this repo has never had

It shows `addopts = -v --tb=short`; the real file has carried `-ra --strict-markers
--strict-config` since long before phase 3. Not this phase's drift and not this phase's to fix —
reported under the passing-glance clause because it is the contract document a new agent reads to
learn how tests are configured.

## 8. Carry-forward dispositions

| item | severity | destination |
|---|---|---|
| **F1** — `--dist=loadfile` false red | should-fix | **project closeout** — the session that retires the perturbation harness (r4 N5) already edits `app/pytest.ini` and the criterion module; this is a two-line change in the same file |
| **F4** — `.env.example` missing `PYTHONPATH=.` (+ four Makefile targets) | should-fix | **project closeout**, with the owner — same session, documentation surfaces only |
| **F2, F3, F5, F6** | note | **F5 to the coordinator now** (plan-text amendment before archive, so the archived plan describes what shipped); F2/F3/F6 are recorded here and need no destination |
| **F7** | note | unassigned — pre-existing architecture-doc drift, whoever is next in `architecture/15_testing.md` |
| r4 **N4** (`app/run_pytest_suite.py`), r4 **N5** (perturbation harness) | note | already carried to project closeout — out of this round's bounds, restated so the closeout list is complete |

## 9. Write perimeter

### 9.1 My own writes

| artifact | kind |
|---|---|
| `handoffs/reviewer/2026-08-22_phase3_rereview_r6_handoff.md` | document (this file) |

**Nothing else.** No plan file, no master plan, no intention, no prompt, **no `.archgraph/` path** —
prompt §7 puts the graph out of bounds and I made no graph call other than `archgraph_status` at
the gate. The Review-log line and the tracker row are the coordinator's, per prompt §8.

### 9.2 Mutation-probe files — separate, reverted, checksum-verified

Baselines taken before the first mutation and re-verified after every revert:

| file | SHA-256 before **and** after | mutations applied |
|---|---|---|
| `app/pytest.ini` | `392e7102e99bb3646e402f7652318dc6e55843afedd75189655e406f2b4414b2` | **M-A** (`--dist=loadfile`), **M-B** (`--dist loadfile` removed) |
| `app/tests/database_isolation.py` | `86434edf8eb3efff73e2ad4486967ffc4ba67b8df133b3875bc813336ba6c049` | **M4** (definition, lock body → bare `yield`), **M5** (call site, `start():242-245`), **M-E** (definition, lock key → worker name), **M-C** (definition, two loopback literals deleted) |
| `app/tests/integration/infrastructure/test_database_isolation.py` | `433c8c0ee10488414ca1175c416cb3e9c593efffcb1118a87a90bdb600de9caf` | **none — never mutated**, checksum unchanged throughout |

All three match fix r5's published closing checksums, and the first two additionally match the
values review r4 published before it applied M4–M7. `git status --porcelain` is empty at close.

### 9.3 Databases

| database | disposition |
|---|---|
| `beyo_test_p3absent_*`, `beyo_test_p3stale_*`, `beyo_test_p3current_*`, `beyo_test_p3c6_*`, `beyo_test_phase2_*`, `beyo_test_main_gw*` | created and reclaimed by the criterion module's own fixtures across nine module runs, including the `load`-mode runs that failed mid-test |
| `beyo_manager` | **never a target.** Left at head; the module's configured-database row-count guard passed in every run |
| `housing_parser_plan1_20260807` | untouched |

Final inventory, queried directly at `localhost:5433`: `beyo_manager`, `beyo_test_main_template`,
`housing_parser_plan1_20260807`, `postgres` (+ `template0`/`template1`) — **byte-identical to the
state I found**, residue `beyo_test_main_template` alone. No temporary Alembic revision remains in
`app/migrations/versions/`.

### 9.4 Evidence

**L4 count: 0.** Against a budget of 0. `git diff 4b5719d HEAD -- app/` is empty, so fix r5's runs
2 and 3 are tree-bound to my tree and are cited throughout, never reproduced: `21 failed / 2578
passed` at the shipped default, `21 failed / 2577 passed / 1 skipped / 1 deselected` under `-n 0`,
`comm`-empty in both directions against the phase-2 21-ID set, collection 2599. **No
repository-wide absence claim required a suite run, so the one authorised exception went unused and
no authorization line was written.**

| # | scope | hypothesis | command / mutation | result |
|---|---|---|---|---|
| 1 | L1 | F1: does an equivalent `--dist` spelling false-red? | M-A, `--dist=loadfile` | 1 failed (dist assertion), 52 passed, 20.69 s |
| 2 | L1 | F2: does sub-check 2 bite? | M-B, `--dist loadfile` removed | red on the dist assertion; + non-deterministic cross-worker collateral |
| 3 | L1 | F2: what breaks under `load` mode? | M-B, repeated with full traceback | 3 failed / 1 error; C6's temporary revision wedges another worker's template |
| 4 | L1 | B1: does C2's named mutation redden all three rows with distinct errors? | M4, definition site | 3 failed — `UniqueViolationError` / `InvalidCatalogNameError` / `ObjectInUseError` |
| 5 | L1 | B1: does row (c) now catch the narrowing task 3 names? | M5, call site | 1 failed — row (c), `ObjectInUseError` ×2 |
| 6 | L1 | **F3: does row (c) catch a lock-*key* narrowing?** | M-E, definition site | **2 failed (a, b); row (c) green** |
| 7 | L1 | N1: are the two new endpoint rows covered? | M-C, two literals deleted | 2 failed — exactly the two new rows |
| 8 | L1 | S1: does the 3rd spelling skip? | `-n0`, unmutated | 52 passed, 1 skipped (`:118`) |
| 9 | L1 | S1: does the 4th spelling skip? | `--numprocesses=0`, unmutated | 52 passed, 1 skipped (`:118`) |
| 10 | — | F4: is `PYTHONPATH=.` actually required? | `env -u PYTHONPATH pytest --collect-only` | `ModuleNotFoundError: No module named 'beyo_manager'` |
| 11 | — | is the skip guard over-broad? | `pytest --help`, options beginning `-n` | only `-n`; the rest begin `--` |
| 12 | — | **standing rule 13**: every invocation surface in the repository | `git grep pytest` across the repo | see §10 |

Green sides for rows 1–7 are cited from fix r5's `53 passed` at the shipped default on this
checksum-matched tree, **not re-run** — re-running it would itself be a finding (charter,
over-evidence). Every mutation names its site as file plus definition-vs-call-site: M4, M-E, M-C
are definition-side; M5 is the call site in `start()`; M-A and M-B are the configuration file.

## 10. Standing rule 13 — the documentation perimeter, enumerated

Nobody has published this list; rule 13 requires it of any phase that changes `addopts`. Every
pytest invocation surface in the repository, outside the implementation folder and `.archgraph/`:

| surface | state |
|---|---|
| `app/.env.example:12` | `-n 0` ✓, `PYTHONPATH=.` ✗ — **F4** |
| `app/Makefile:36` `test` | `pytest -m 'not e2e'` — the authoritative shipped-default command ✓; no `PYTHONPATH=.` (F4's family) |
| `app/Makefile:39,42,45` | `test-unit` / `test-integration` / `test-e2e`, all inheriting `-n 6`. r4's N6 refuted the unit regression by measurement. **`test-e2e` I checked rather than assumed: `tests/e2e/` is one `assert True` smoke test — six workers over it is harmless** |
| `app/run_pytest_suite.py` | r4's N4, out of bounds, carried to closeout |
| `.github/workflows/deploy.yml` | contains no pytest invocation — **there is no CI test surface to re-point** |
| `architecture/15_testing.md:389-397` | a config surface, stale since before this phase — **F7** |
| `*.md` elsewhere | no runnable `pytest …` command lines |

## 11. Verified correct, specifically

- **B1 is genuinely closed.** The mechanism the plan warns about in writing (M5) now reddens, and
  the definition-side removal (M4) reddens all three rows with three distinct errors, satisfying
  C2's mutation text exactly.
- **The substituted instrument is sound and deterministic**, and rests on exactly one sufficient
  cause (§5.5) — verified by measurement, not by reading.
- **The `asyncio.gather` double-close race the coordinator flagged is unreachable** in every
  configuration this row can occupy (§5.3).
- **C8's four sub-checks each have a bite, with which-bites-on-which recorded** (§6), and its skip
  guard is complete across all four spellings of the option and not over-broad.
- **The published baseline's identity holds for `HEAD`**: `git diff 4b5719d HEAD -- app/` empty, so
  §8's tree-identity claim is accurate as written, and the `1 skipped` it publishes is C8.
- **Database residue is exactly as found** after nine module runs including four that failed
  mid-lifecycle.

## 12. Lessons for the plans (coordinator folds upstream)

1. **A repair that widens one spelling should widen every spelling in the same assertion.** F1 is
   S1 and S2 recurring inside the code written to fix S1 and S2 — the round enumerated spellings
   for `-n` and then wrote the adjacent `--dist` check as a literal. Rules 4 and 12 both had to be
   applied twice in one function and were applied once. Worth adding to rule 12: *when a repair
   converts a literal to a contract, it converts **every** literal in that assertion.*
2. **When an implementer diverges from a correction quoted in its own prompt, saying so is part of
   the deliverable.** The divergence here was correct and better than the correction, and the
   handoff described the new mechanism without ever saying *"the quoted repair does not work,
   because …"*. The coordinator caught it; a re-reviewer reading only the two artifacts would have
   opened a finding on a non-defect. Suggest a standing rule: **a fix round that does not implement
   a quoted correction states which one and why, in its own section.**
3. **A criterion's row text is amended when the observer changes.** F5. B1 was born when a row's
   text named an observer the code did not build; the repair fixed the code and left the text. The
   archived plan is what the next project reads.
4. **A mutation ledger enumerated from the prose misses the branch a repair just added.** F2:
   `--dist loadfile` became a sub-check in this round and the ledger — enumerated from the previous
   round's three sub-checks — did not grow a row for it. Rule 4's trap, one level up: **enumerate
   sub-checks from the code *after* the repair, not from the finding that requested it.**
5. **"Matches character for character" is a claim a prompt should not make without diffing.**
   Prompt §5.3 asserted `.env.example` matched §6.1 exactly; it differs by `PYTHONPATH=.`, and the
   difference is the one that makes the command fail. A prompt's convenience claims are the round's
   evidence unless the reviewer re-derives them — I did, and it was the only such claim that was
   wrong.
