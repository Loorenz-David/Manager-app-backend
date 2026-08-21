# Plan 3 — parallelism, and a baseline worth trusting

```
state: PROJECTED — 2026-08-21 (projection r0 consumed; 25 ledger rows routed; OD-8 and OD-9 answered)
hub: ../master_plan.md (tracker §3, environment §6, gates §7, baselines §8)
phase: 3
date: 2026-08-21
actor: coordinator (authoring)
depends_on: plan_2 APPROVED (2026-08-21, `e57ffaf`). Satisfies live_clock phase 4's ⛔ gate.
projection_gate: MANDATORY. Ordering, derivation keys and destructive lifecycle, all at once —
                 charter rule 6 three times over, same as phase 2, whose projection returned 15
                 ledger rows.
```

## 1. Goal

Install `pytest-xdist`, choose a worker count from measurement rather than convention, and
**republish the authoritative failure-ID set under the new runner with every difference
explained.** The intention's deliverables 6–14 land here.

The secondary objective is speed. **The primary objective is a baseline the rest of the
organisation can build on** — `live_clock` phase 4 and `narrow_typical_work_times` D23 consume
whatever this phase publishes, and a fast suite measured against an untrustworthy baseline is
worth less than the slow one it replaced.

**NOT in this phase:** no production domain change. No weakened assertions, no retries, no
`xfail`/`skip` applied to tests that parallelism exposes — the intention forbids each by name.
If parallelisation reveals a real race, ordering dependency or invalid fixture assumption, report
it; fix it only when the correct repair is clear and inside the test-infrastructure perimeter, and
**raise an owner decision rather than improvising** if it needs a production-domain call.

## 2. Read first

1. `../master_plan.md` — **§6 is the environment authority** (commands, topology, the five-step
   invariant, Redis, the schema constants). §5's eight standing rules. §7's gates. §8's baseline
   provenance, which explains why the number is 21 and not 26.
2. `planning/intention.md` — §1 verbatim, especially the **correctness gate** (the list of shared
   resources that PostgreSQL isolation does *not* solve) and the **mutation-testing consequence**;
   §2.2's runner inventory; §3's phase-3 bullet, which carries this phase's first gate.
3. `plans/plan_2.md` §5 C2 — read the **scope correction** appended to it. It is the reason task 1
   exists.
4. `archive/plan_2/2026-08-21_phase2_review_r3_handoff.md` — S5 (object lifetime, not order),
   N3, N4, and lessons 2–4.

## 3. Files expected to change

- `app/requirements*.txt` / dependency manifest — `pytest-xdist`.
- `app/pytest.ini` — only if a default `-n`/`--dist` is adopted; **state it explicitly if so**,
  because it changes what every future bare `pytest` invocation measures.
- `app/tests/database_isolation.py` — template-copy contention (task 3), and N3/N4 (task 6).
- `app/tests/conftest.py` — only if worker-scoped resource isolation requires it.
- `app/tests/integration/infrastructure/test_database_isolation.py` — criterion rows.
- **New:** a perturbation harness for task 1 — location yours, declared in the handoff.
- Nothing under `app/beyo_manager/`. The `config.py` carve-out is spent (OD-7); if you need it
  again, raise a decision card.

## 4. Ordered tasks

### 1. The perturbation gate — before `pytest-xdist` is installed

**This runs first and nothing else starts until it has an answer.** Phase 2 proved the failing-ID
set is invariant under *reversal*. It also produced counter-evidence to the general claim, inside
its own fix-r4 verification: **with eight extra criterion rows temporarily present, the failing-ID
set differed.** That round attributed the extras to "pre-existing order seams" and restored
collection size rather than reporting the divergence.

xdist redistributes every test across processes — a perturbation orders of magnitude larger than
eight rows. Measure parallelism first and the first `-n 4` number mixes two effects, and the new
authoritative baseline inherits both.

**Deliverable:** the set of test IDs whose pass/fail outcome is a function of collection position
rather than of code, **enumerated**, or a demonstration that the set is empty. Insert no-op tests
at several collection positions on the **serial** runner and diff the failing-ID sets against the
published 21. The count and placement are yours; the enumeration is not optional.

**OD-8 makes the outcome a branch you can execute, not a question you must stop on.** A non-empty
set is **enumerated and published as a separately-named unstable list**, excluded from the
authoritative failing-ID set, and **the phase continues** to the matrix. You never repair that
class here.

**Four things the projection established this task needs, or it cannot answer what it promises:**

1. **State the probe's shape.** "No-op tests" is the wrong instrument: the observation being
   chased came from eight **database- and Redis-touching** criterion rows. `def test_probe(): pass`
   shifts indices without reproducing the mechanism. Say which shape tests which hypothesis.
2. **A noise floor.** Insertion shifts absolute position but changes **no test's order relative to
   any other**, so a differing set is *either* position sensitivity *or* plain run-to-run
   nondeterminism — and phase 2's S5 proved this suite has a nondeterministic member (object
   lifetime). **At least one unperturbed repeat run** is budget row 0, and **standing rule 7 binds
   this task's own output**: a single-occurrence difference is re-measured, never attributed.
3. **A harness-only control.** Every probe run happens on a tree that also contains the new
   harness. One run with the harness present and **zero probes enabled** separates "the probes
   moved things" from "the harness's presence moved things".
4. **Declare `n` and the positions before the first run.** "The union of IDs that ever differ" is
   only decidable if the probe set is fixed in advance; otherwise the union is a function of when
   you chose to stop.

**The harness must be collection-neutral unless explicitly enabled** — the
`BEYO_TEST_COLLECTION_ORDER` pattern is the precedent. It ships inert, so the closing stamp is
taken on the same tree the probes ran on **and** the republished baseline does not inherit probe
tests that three consuming projects would then carry. Its enable mechanism must produce an
**identical collection list in every worker**: xdist aborts when workers disagree, so nothing may
key off process or worker identity.

**Delegated, bounded:** which positional axis you probe — file-level (path sort order under
`testpaths = tests`) or within-file — and how you control position. State the choice and why.

### 2. Install `pytest-xdist`, and re-establish serial

Installing a plugin changes collection and reporting even at `-n 0`. *(Master plan §6.1 was
corrected at this fold: the suite registers **two** third-party plugins today, `pytest-asyncio`
and `anyio` — not one. Task 2's argument is unaffected but the inventory it cites is now true.)*
**Take a fresh serial stamp with xdist installed** before any parallel run: that, not the pre-install 21, is the comparator
every parallel measurement is diffed against. Any difference between pre-install and
post-install serial is a finding to explain — the plugin should not change outcomes, and if it
does, that is the most important thing this phase will discover.

**Delegated, bounded:** which manifest gets the pin. `requirements.txt` and `requirements-dev.txt`
**both** pin `pytest==8.3.5` / `pytest-asyncio==0.25.3` today. Name the file, pin exactly as its
neighbours are pinned, and say why that file.

### 3. Template-copy contention — the hazard that only exists once workers do

`CREATE DATABASE … TEMPLATE …` **fails while any other session holds the source database open.**
Phase 2's projection recorded this (ledger row L15) as undecidable serially and routed it here.
With N workers starting at once, worker 2's copy can collide with worker 1's connection to the
template, and the failure surfaces as a startup error that looks like flakiness.

**It is three failure paths, not one**, and the plan previously named only the third:

1. **Template absent** (first run after a slot is declared): every worker sees the template
   missing and issues `CREATE DATABASE <template>`; losers get `DuplicateDatabaseError` and die at
   startup.
2. **Template stale** (the first run after *any* Alembic revision — i.e. exactly C6's scenario):
   every worker takes the rebuild branch, and `_drop_database_if_exists` runs
   `pg_terminate_backend` on every session connected to the template. **One worker kills another's
   inspection connection and drops the template out from under its in-flight `alembic upgrade`.**
3. **Template current** (steady state): a short-lived `inspect()` / `_has_legacy_baseline_source()`
   / `_set_marker()` connection overlaps a `CREATE DATABASE … TEMPLATE`, producing
   `source database … is being accessed by other users`.

**The serialised region is the whole of `_ensure_template` plus the copy — not the
`CREATE DATABASE` statement.** The "other users" are those inspection connections and the ~1 s
alembic subprocess inside `_migrate_and_assert`; a guard around the copy alone leaves the real
window open.

Solve it deliberately — serialise, retry with backoff, or build per-worker templates — and say
which and why. **Do not discover it as an intermittent failure during the matrix**; it will be
attributed to the wrong cause. Note that paths 2 and 3 are the same event **C6 deliberately
triggers**, so C2 and C6 intersect by construction.

**Delegated, bounded:** all three paths are reproducible **serially**, in-process, with concurrent
`DatabaseIsolation(...)` `start()` calls under `asyncio.gather` — the criterion module already
drives lifecycles that way. You do not need `-n 4` to prove C2. Probe worker ids must not collide
with real `gw0…gwN` names, nor with each other.

### 4. Shared resources that PostgreSQL isolation does not cover

The intention's correctness gate names them: execution order, module/session-scoped mutable
state, shared filesystem state, fixed ports, **Redis**, background workers, global caches,
environment mutation, timestamps, unique constraints, and processes outside pytest. Its closing
sentence is binding:

> *Per-worker PostgreSQL isolation solves only PostgreSQL interference. Do not infer that the
> entire suite is parallel-safe merely because the DB is isolated.*

**Inventory them against this suite**, state which are actually reached, and isolate or declare
each. The inventory is a **handoff section with a per-class disposition** — *reached / not reached
/ isolated / declared* — so a reviewer has a rubric for all eleven rather than for the one that
happens to carry a criterion. **C4 covers Redis only**; the other ten are covered by the
disposition table.

Redis already has a `uuid4`-derived per-**process** prefix (`conftest.py:56`), so two workers
cannot share one — see C4, which is a confirm-and-record row rather than a proof obligation.

### 5. The measurement matrix, and a conservative default

Serial, `-n 2`, `-n 4`, and a higher count if useful and safe (the machine has **14 cores**).
Per run record: wall-clock, pass/fail counts, worker count, distribution mode, any new or flaky
failures, PostgreSQL or resource problems, and whether the failing-ID set differs from the serial
comparator.

**"Safe" has a measured definition here, and it is tighter than it looks.** Master plan §6.3a:
`max_connections = 100`, ~16 already in use, and a per-process pool ceiling of 40
(`DB_POOL_SIZE=20` + `DB_MAX_OVERFLOW=20`). **Three workers at full pool exhaust the server, and
`-n auto` is 14 workers.** Real usage sits far below the ceiling, so this is a risk rather than a
certainty — which is exactly why it must be measured: **state the connection budget you checked
before the highest-count run, and record the `pg_stat_activity` peak per matrix row.**

**Start with `--dist loadfile`**, which keeps a file's tests on one worker so file-local ordering
survives; treat any move to finer distribution as a **separate, measured step** with its own row,
not a tweak. Choose a conservative default if more workers bring diminishing returns or
contention — `-n auto` is not assumed optimal, and per §6.3a may not even be reachable.

**OD-9 fixes what ships:** the default **stays serial** unless the parallel failing-ID set matches
the serial comparator exactly. Report the whole matrix either way; leave `pytest.ini` alone unless
the sets agree.

### 6. The two carried code items

- **N4, the time bomb.** `EXPECTED_HEAD = "c1d2e3f4a5b6"` and `EXPECTED_PUBLIC_TABLE_COUNT = 107`
  are hardcoded, so the next Alembic revision makes `_ensure_template` rebuild and
  `_migrate_and_assert` raise `RuntimeError` — **the suite wedges until a human edits the file.**
  **The delegation is resolved here rather than left open, because the projection measured that
  both obvious derivations are wrong.** `ScriptDirectory.from_config(...).get_heads()` returns
  `['c1d2e3f4a5b6']` — the head derives cleanly. **The table count does not:**
  `len(Base.metadata.tables)` is **104**, the migrated template is **107**, and the development
  database is **109**. The 107 is `104 + alembic_version + 2 migration-owned "_journal" tables`,
  which are deliberately absent from ORM metadata by the convention documented at
  `migrations/env.py:20-31`. Deriving from metadata would fail on **every** template build — the
  same wedge C6 exists to remove, reintroduced by its own repair — and deriving from the dev
  database both gives 109 and re-imports development contents into the test contract, which is
  the class OD-1 removed.

  **Binding: derive the head from the migration scripts, and replace the table *count* with a
  content assertion** — head plus a required-table set, which `_migrate_and_assert` already
  partly carries. The brittle number goes away rather than acquiring a cleverer source.
- **N3.** `_normalised_endpoint` maps only the literal string `"localhost"`. `LOCALHOST`, `::1`,
  `0.0.0.0` or a hostname alias mismatch and make **every** drop refuse, so the suite cannot
  start. Fail-closed and therefore safe, but the failure mode is total and the diagnosis
  non-obvious.

### 8. Pre-authorised: scope the criterion module's global assertions to this worker

**This will be the first thing `-n 2` reddens, and it is our assumption breaking, not the suite.**
`test_database_isolation.py:34-46` (module-scoped autouse) and `:325, :332, :334, :363` assert
**server-global** `beyo_test_*` membership — a set-equality against a snapshot. Under `-n N`,
sibling workers create and drop their databases concurrently, and
`tests/integration/migrations/test_phase6_legacy_migration.py` creates and drops
`beyo_manager_phase6_<uuid>` databases in five tests; under `--dist loadfile` those two files land
on **different workers and run at the same time**.

Scope both snapshots to this process's own slot/worker names. **This repair is pre-authorised** —
it is an invalid fixture assumption whose repair is clear and inside the test perimeter, which the
intention's scope-discipline clause explicitly covers. It gets a C3 row rather than being
discovered at 2 a.m. inside a matrix run.

### 9. Legacy reclamation under a parallel runner

`BEYO_RECLAIM_LEGACY_TEST_DATABASES=1` is documented in master plan §6.1 as a full-suite
invocation. Under N workers, all N sweep the same legacy names and `_drop_database_if_exists`
races its own existence-check against another worker's drop. Either exclude the sweep from
non-controller workers, or document the command as **serial-only** in §6.1. State which.

### 7. The deliverables the intention asks for by name

A **before/after table** covering full-suite wall time, databases used, persistent test residue,
failure count, failing-ID set and worker count; and the actual database lifecycle **as a
diagram**. These are deliverables 8, 9 and the closing request of §1 — not optional decoration.

**Document writes are part of this phase's perimeter, and they are the implementer's**, except the
tracker row: master plan **§8 replaces its phase-3 row** with the new baseline, **§6.1's command
table** changes meaning if a default `-n` ever lands (per OD-9 it will not, this phase), and
**§6.3a** gains the measured peak. The master plan §3 tracker row stays the coordinator's.

## 5. Acceptance criteria

Each names the defect it would catch and carries a named mutation with its site named and both
sides computed. No criterion asserts documented third-party behaviour. **Amended 2026-08-21 after
projection r0: three criteria described state that exists only during a parallel run and named no
observer; one could not fail; one carried item had no row at all.**

- **C1 — collection-position sensitivity is enumerated, not assumed away.**
  *Defect:* a parallel measurement that attributes to xdist an order sensitivity already present,
  permanently corrupting the baseline three other projects consume.
  *Contract:* `n` and the probe positions are **declared before the first run**. For each, the
  failing-ID set is `comm`-diffed against the published 21 in both directions. Row 0 is an
  **unperturbed repeat** (noise floor) and row 0b is **harness-present, probes disabled**. An ID
  is admitted to the unstable set only if it differs **and survives re-measurement** — standing
  rule 7 binds this task's own output. Deliverable: the enumerated union, or a demonstration that
  it is empty.
  **No named mutation** — an equality claim over the whole suite under several declared
  conditions, L4 by construction. The declared positions *are* the evidence.

- **C2 — concurrent worker startup survives all three template paths.**
  *Defect:* `_ensure_template` runs at the start of every process against one shared per-slot
  template, so simultaneous starts collide — and the run dies at startup intermittently, which
  gets attributed to parallelism in general.
  *Rows — one per path, each with its own exact expected outcome, because the three produce
  different errors:* (a) **template absent**, N concurrent starts → all obtain a database, no
  `DuplicateDatabaseError`; (b) **template stale**, N concurrent starts → the rebuild happens once
  and no worker's inspection connection or in-flight `alembic upgrade` is killed; (c) **template
  current**, a held inspection connection overlapping a copy → no
  `source database … is being accessed by other users`.
  *Observer:* in-process `DatabaseIsolation` probes under `asyncio.gather`, **serially** — this
  does not require the plugin.
  **Named mutation, site named:** remove task 3's serialisation around `_ensure_template` ⇒
  contract = all three rows green, mutation = each row red **with its own error**, not one shared
  string. A row pinned to path (c)'s message alone would be un-runnable for (a) and (b).

- **C3 — worker databases are disjoint, all are reclaimed, and the criterion module survives siblings.**
  *Defect:* two workers sharing a database — cross-talk indistinguishable from a race; and the
  isolation module's own global-membership assertions breaking under siblings, which reads as "a
  new failure under parallelism" and would be wrongly absorbed into the baseline.
  *Rows:* (a) **each worker asserts its own database name and that no sibling name equals it** —
  this is the observer, inside the run, replacing the unobservable "four exist simultaneously";
  (b) after the run, server membership equals before — **charter rule 1's environment-lifecycle
  exemption is invoked here in writing**, with the module fixture as the named automated proxy;
  (c) the criterion module's membership snapshots are **scoped to this process's own slot/worker
  names** (task 8) and stay green while a sibling worker and
  `test_phase6_legacy_migration.py` create and drop databases concurrently.
  **Named mutation, site named:** make the resolver ignore `PYTEST_XDIST_WORKER` ⇒ contract = N
  distinct names, mutation = one name N times, red on (a). Second site: revert (c)'s scoping ⇒
  green serially, red under `-n 2`.

- **C4 — Redis isolation is confirmed and recorded, not re-proven.**
  *Defect:* none available to catch — and that is the finding. The prefix is `uuid4`-derived per
  process (`conftest.py:56`), so two workers **cannot** share one, and
  `test_default_redis_key_uses_the_process_prefix` already asserts it is not the shipped default.
  A new row restating either would be decoration with a correct name.
  *Contract:* the handoff **records** that Redis isolation holds per worker by construction,
  citing the existing row, and states the cross-process observation it would take to prove it if
  the mechanism ever changes. **No new test, no named mutation** — writing one here would be the
  row-that-cannot-fail class, which this project has recorded fourteen times.

- **C5 — the parallel failing-ID set equals the serial one, or every difference is explained.**
  *Defect:* a baseline that silently absorbed a parallelism-induced failure, making every future
  mutation measurement meaningless.
  *Contract:* at the chosen default, `comm`-diffed both directions against the **post-install
  serial** comparator (not the pre-install 21). Any difference is **explained with evidence, never
  updated into the baseline**, and per standing rule 7 a single-occurrence difference triggers
  **re-measurement, not attribution**.
  *Second condition:* **not reversal.** Under xdist the execution order is the scheduler's, not
  the collection list's, so `BEYO_TEST_COLLECTION_ORDER=reverse` only permutes within a worker's
  assignment and proves far less than it did serially. Use a condition that varies **scheduling**
  — a second run at the chosen default, requiring identical sets — and state what it claims.
  **No named mutation** — L4 by construction.

- **C6 — a new migration does not wedge the suite.**
  *Defect:* the next Alembic revision makes the template rebuild and `_migrate_and_assert` raise,
  stopping every run until a human edits a constant.
  *Contract — one branch, not a disjunction, now that task 6's delegation is resolved:* the head
  derives from the migration scripts and the brittle table **count** is replaced by a content
  assertion. With a new revision applied to a disposable database, **the template rebuilds and the
  suite runs.**
  *Mechanism:* the revision does not exist and must be produced — a temporary revision file
  created and removed **inside the test**, applied only to a disposable database, never a rewrite
  of an applied migration (charter rule 7). Declare it in the handoff's write perimeter, since
  `migrations/versions/` is outside §3.
  **Named mutation, site named:** pin the derived head to a stale revision ⇒ contract = the run
  proceeds, mutation = the wedge returns, red. *Note C6 and C2(b) trigger the same event; each
  states its own expected outcome.*

- **C7 — endpoint normalisation does not silently refuse every drop.**
  *Defect:* `_normalised_endpoint` (`database_isolation.py:76-78`) maps only the literal string
  `"localhost"`. `LOCALHOST`, `::1`, `0.0.0.0` or a hostname alias mismatch the configured
  endpoint and **every** drop refuses, so the suite cannot start — fail-closed and therefore safe,
  but total, and the diagnosis is non-obvious. N4 got a criterion; N3 did not.
  *Rows:* a configured/target pair differing only by one of those spellings resolves to the same
  endpoint; a genuinely different host still refuses.
  **Named mutation, site named:** remove the normalisation ⇒ contract = the pair matches, mutation
  = refused, red. *If this phase decides N3 is documentation-only, say so explicitly and why —
  but then delete this criterion rather than leaving it unmet.*

## 5A. Traps this plan inherits

- **All of plan 1 §5A and plan 2 §5A still apply.** Assert DDL, never a migration's exit code.
  Compute both sides of every fixture before choosing it. Report dead scaffolding rather than
  deleting it silently.
- **Standing rule 7 is the one this phase will be tempted to break.** A single new failing ID
  under `-n 4` will look explainable. Re-measure it; do not name it.
- **Standing rule 8.** Your closing stamp is defined by the tree you hand over. If you change
  anything after stamping, the stamp is void and re-taking it is **not** over-budget.
- **Do not restate the environment.** Master plan §6 is the authority; two rounds have already
  restated it inconsistently into prompts. Cite it.
- **The topology-fold trap.** Phase 2 folded new criterion rows into existing tests to keep
  collection size constant, which preserved comparability and cost attribution — a driver check
  now reddens through a test named for unmarked databases. **Do not let measurement convenience
  drive test design.** If adding rows perturbs the baseline, that is task 1's subject, not a
  reason to avoid adding rows.
- **S5's class.** One test's outcome was a function of object lifetime, not order: 13 test files
  create a second session and the repository carries 89 `refresh()` calls. Under workers, that
  class gets a new axis.

## 6. Evidence budget

This phase is a measurement matrix, so **the matrix is the budget** (charter: "a phase whose own
criteria enumerate L4 measurements states that enumerated matrix as its budget"). Each row is a
distinct condition and therefore variation, not repetition.

| # | run | purpose |
|---|---|---|
| 0 | serial, unperturbed **repeat** | C1's noise floor — separates position sensitivity from nondeterminism (L2) |
| 0b | serial, harness present, **probes disabled** | C1's harness-only control (L3) |
| 1–n | perturbation probes, serial, pre-install | task 1 / C1 — **`n` and the positions declared before the first run** (L4) |
| — | the published `21 / 2561 / 1` at `11b4d02` | the control, **cited not re-run** |
| n+1 | serial, xdist installed | the comparator every parallel run is diffed against |
| n+2 | `-n 2 --dist loadfile` | matrix |
| n+3 | `-n 4 --dist loadfile` | matrix |
| n+4 | higher count, if useful and safe | matrix |
| n+5 | the chosen default, on the tree you hand over | **the mandatory closing stamp** |
| n+6 | a **second run at the chosen default** | C5's second condition — varies scheduling, which reversal no longer does under xdist (L16) |

So the total is **n + 8**. Declare `n` and the probe positions in the handoff **before** the first
run, and state the total as a number once `n` is fixed. Anything beyond the enumerated matrix needs
the charter's authorization line, written before it. Everything else is L1/L2.

**State your total L4 count as a number.** Two reviewers spent effort disambiguating a previous
round's prose; it should have been one line.

## 7. Review log

### 2026-08-21 — projection r0 (independent). Verdict: AMENDMENTS_REQUIRED

Full ledger, findings and evidence: `handoffs/reviewer/2026-08-21_phase3_projection_r0_handoff.md`.
**25 rows, 8 findings, 2 owner cards, 0 L4 runs against a budget of 0.** Both cards answered —
**OD-8** (a non-empty unstable set is listed, and the phase continues) and **OD-9** (the shipped
default stays serial until parallel and serial agree).

The round's diagnosis of the plan: *"What it does not determine is **who observes the things it
asserts**."* Three of six criteria described state existing only during a parallel run and named
no observer; one could not fail; one carried item had no criterion; and the task owning the
phase's sharpest hazard named one of that hazard's three failure paths.

| # | Routed to | Disposition |
|---|---|---|
| L1–L7 | §4 task 1, C1 | Probe shape stated (no-ops cannot reproduce a mechanism produced by DB- and Redis-touching rows); noise-floor repeat and harness-only control added as budget rows 0/0b; `n` **and positions** declared before the first run; harness must be collection-neutral unless enabled and identical across workers; positional axis delegated. |
| L8 | §4 task 2 | Manifest choice delegated, bounded — both requirements files pin pytest today. |
| **L9** | **master plan §6.1** | *"Exactly one plugin"* was **false** — `pytest -VV` registers `pytest-asyncio` **and `anyio-4.13.0`**. Corrected; task 2 reasons from that inventory. |
| L10, L12 | §4 task 3, C2 | Three failure paths, not one; the serialised region is the whole of `_ensure_template` plus the copy, not the `CREATE DATABASE` statement. |
| L11 | §4 task 3, C2 | All three paths reproduce **serially** with in-process probes under `asyncio.gather` — the plugin is not needed to prove C2. |
| L13 | §4 task 4 | The inventory is a handoff section with a per-class disposition; C4 covers Redis only. |
| L14 | C4 | Rewritten as **confirm-and-record**. The prefix is `uuid4`-derived per process, so it cannot fail — a new row would be the row-that-cannot-fail class again. |
| **L15** | **master plan §6.3a** (new), §4 task 5 | Measured: `max_connections = 100`, ~16 in use, per-process pool ceiling 40. **Three workers at full pool exhaust the server; `-n auto` is 14.** Connection budget must be checked and `pg_stat_activity` peak recorded per row. |
| L16 | C5 | Reversal proves far less under xdist (execution order is the scheduler's). Second condition replaced with one that varies **scheduling**. |
| **L17, L18** | §4 task 6, C6 | **Delegation resolved rather than left open.** Head derives cleanly; the table count does not — metadata **104**, template **107**, dev **109**, the difference being `alembic_version` + two migration-owned `_journal` tables absent from ORM metadata by documented convention. Both obvious derivations are wrong, so the count is replaced by a content assertion and C6 becomes one branch. |
| L19 | C6 | The new revision is a temporary file created and removed inside the test, applied only to a disposable database; declared in the write perimeter. |
| L20 | **C7** (new) | N3 had no criterion. Endpoint normalisation gets one, or is declared documentation-only in writing. |
| L21 | §4 task 8 (new), C3(c) | The criterion module's global membership assertions are **pre-authorised** for worker scoping — this is the first thing `-n 2` will redden and it is our assumption breaking, not the suite. |
| L22 | C3(a)(b) | Observer defined: each worker asserts its own name and sibling-disjointness; the after-equals-before claim invokes charter rule 1's environment-lifecycle exemption **in writing** with a named proxy. |
| L23 | §4 task 7 | Document writes named and assigned — §8's baseline row and §6.3a's peak are the implementer's; the §3 tracker row is the coordinator's. |
| L24 | §4 task 9 (new) | Legacy reclamation races under N workers; excluded from non-controller workers or documented serial-only. |
| L25 | §6 | Budget restated at **n + 8** with the two control rows added. |
| **F7.2** | `plans/plan_2.md` frontmatter | Still read `state: IMPLEMENTED` with no `gate_stamp:` while the tracker, §7 and commit `e57ffaf` all recorded APPROVED. **Coordinator defect** — the approval script replaced a string the fix round had already changed, and the replacement was not asserted, so it failed silently. Fixed. |

**2026-08-21 — projection r0 consumed (coordinator).** Four claims re-measured independently
before routing: the plugin inventory (**two**, confirmed at `pytest -VV`), plan_2's frontmatter
(confirmed stale), the connection budget (`max_connections=100`, 16 in use, `DB_POOL_SIZE=20` +
`DB_MAX_OVERFLOW=20`), and F3's arithmetic — the template's `_journal` tables are exactly
`ended_shift_collapse_journal` and `item_valuation_migration_journal`, and the convention that
keeps them out of ORM metadata is documented at `migrations/env.py:20-31`, so `104 + 1 + 2 = 107`
holds.

**Two of the round's eight findings are defects in documents the coordinator wrote**, and both had
survived a reading by two other sessions: a false plugin inventory that phase 3's own task 2
argues from, and a phase-approval that never reached the artifact recording the phase's state.
The gate found them before an implementer built on either.

**The standing question is answered: phase 3 is one phase.** The projection's judgment —
*"the boundary holds, but only if card 1 is answered before the session starts"* — is right, and
OD-8 now maps every outcome of task 1 to an action, converting a phase-splitting question into a
branch the implementer can execute.
