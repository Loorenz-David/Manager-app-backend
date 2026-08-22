# Master plan — test isolation and pytest-xdist

```
role: master plan (coordination hub; indexes the tables, is not a row itself)
created: 2026-08-21, at phase 2's approval gate
why_late: phases 1 and 2 ran without one. Both reviewers flagged the cost (review r3 N8,
          lesson 6): the charter's environment-topology section had no home, so the exact
          commands, the database-safety rules, the Redis dependency and the baseline caveats
          were scattered across three plan files and every prompt, and were restated — twice
          inconsistently — in prompts instead of being cited.
owner_decision: this work GATES phase 4 of live_clock_for_working_time_economics
                (that pipeline's master_plan §6 ⛔ block). The gate is satisfied when
                **phase 3** closes, not phase 2 — its wording requires xdist plus a baseline
                re-enumerated under the new runner.
```

## 1. Mission

Give every pytest process its own PostgreSQL database, created fresh from a migrated template
and dropped afterwards, behind a fail-closed invariant that makes it structurally impossible to
touch the development database — then, and only then, parallelise.

The owner's intention is recorded verbatim at `planning/intention.md` §1 and is the semantic
authority. Its two governing constraints:

- **Isolation before parallelism.** Never install xdist and declare victory; prove isolation,
  then prove order-independence, then parallelise.
- **The previous baseline is not automatically valid once the runner topology changes.**

## 2. Folder layout

Per the charter's positional-state rule — live work sits in its role folder, closed work moves
to `archive/plan_<n>/` at the approval gate, and a state transition is a file move.

```
master_plan.md            this file — the hub
planning/intention.md     the owner's intention (§1 verbatim) + measured inspection + OD-1…OD-7
plans/plan_<n>.md         one row per phase: goal, tasks, criteria, Review log
prompts/<role>/           live directives awaiting or serving a session
handoffs/<role>/          unconsumed session reports awaiting the coordinator
archive/plan_<n>/         closed rows, partitioned by phase
```

## 3. Phase registry & tracker

Newest first; superseded rows kept as provenance.

| Phase | Scope | State | Date | Actor | Note |
|---|---|---|---|---|---|
| 3 | Parallelism: install xdist, serial / `-n 2` / `-n 4` / higher matrix, conservative default, **new authoritative baseline re-enumerated under the new runner** | **IMPLEMENTED** | 2026-08-22 | Codex (r1, fix r2, fix r3) + Opus 5 (projection r0) + coordinator | **Four rounds, no review yet — review r4 is next.** Perturbation gate returned an **empty** unstable set, so the phase stayed one phase. `-n 6 --dist loadfile` is the shipped default under **OD-10** (owner, 2026-08-22, after OD-9's escape condition was met): 52.62 s against 150.70 s serial, same 21-ID set. Original gate note: see §7's perturbation gate. Does not begin its worker matrix until collection-perturbation sensitivity is characterised on a *serial* runner. Carries six items from phase 2's closeout table. `plans/plan_3.md` authored 2026-08-21; projection r0 returned AMENDMENTS_REQUIRED with **25 ledger rows** (2 of its 8 findings were defects in coordinator-authored documents); all routed, OD-8 and OD-9 answered, implement r1 compiled. |
| 2 | Order-independence and per-checkout isolation, still serial | **APPROVED** | 2026-08-21 | Codex (r1, fix r2, fix r4) + Opus 5 (projection r0, review r3) + Sonnet 5 (review r3 comparison) + coordinator (gate stamp) | **Five rounds.** Repaired the ~118-test order class across 12 files under OD-6's adopt-or-create contract; added the slot discriminator, the fail-closed slot resolver, endpoint confinement, both wedge shapes, Redis isolation, and the collection-order hook. **The projection gate paid for itself in one round** — four of seven criteria would have shipped as tests that pass whether the code is right or wrong, three of them coordinator-authored. Review r3 found two blocking defects nobody else had: an inert `BEYO_TEST_SLOT` and a sweep that dropped other checkouts' live databases on every process. Gate stamp taken by the coordinator because the round's own pair predated an eight-row change. |
| 1 | Per-worker database isolation, proven serially | **APPROVED** | 2026-08-21 | Codex (r1, fix r2, fix r4) + Opus 5 (review r3) + coordinator | Four rounds. Established the seam (`settings.database_url`, re-read per test), the fail-closed guard, the migrated template, and bounded worker names. Converted dev-data coupling into **test-order** coupling for ~118 tests — discovered by review r3, deferred to phase 2 as OD-3. |

## 4. Naming registry

- **`OD-<n>`** — owner decisions, in `planning/intention.md` §4. OD-1…OD-7 are assigned.
- **`B<n>` / `S<n>` / `N<n>`** — a review round's blocking / should-fix / note findings. **Scoped
  to their round**, never globally unique: "B2" means different things in phase 1 and phase 2.
  Always cite as "phase 2 review r3 B2".
- **`C<n>`** — acceptance criteria, scoped to their plan file.
- **`L<n>`** — projection ledger rows, scoped to their projection round.
- Round numbers are **continuous across roles within a phase**: r0 projection, r1 implement,
  r2 fix, r3 review, r4 fix. A round number identifies a session, not a role.

## 5. Standing rules earned by this project

Each came from a measured defect. These supplement the charter, never replace it.

1. **Never accept a migration's exit code as evidence — assert the DDL.** The documented Alembic
   trap makes `upgrade` log success, exit 0, and persist nothing. During phase 1's inspection it
   exited 0 in ~1 s, which is exactly what the trap looks like; only asserting 107 tables
   distinguished them. `migrations/env.py:167` carries the `connection.rollback()` guard.
2. **A test may not read a row it did not create — except globally-unique catalog rows, which it
   adopts-or-creates and never creates unconditionally** (OD-6). Both the naive rule and its
   opposite were measured and refuted: seeding a shared catalog moves the error to
   `AttributeError`, and strict create-your-own collides on `ix_roles_name`.
3. **A destructive branch without a criterion row is not covered, whatever the ledger says.**
   Phase 2's legacy sweep — the widest destructive path in the module — had no row and dropped
   other checkouts' databases on every process. A reviewer affirmed guard coverage by reading the
   implementer's ledger; two sub-checks reddened nothing.
4. **Enumerate sub-checks from the code's branch points, not from the prose.** `_parse_database_url`
   is four checks wearing one name; disabling it wholesale looked like coverage for all four.
5. **An environment variable's documentation surface is part of its contract.** `.env` is parsed
   by pydantic-settings, which never populates `os.environ` — so an `os.getenv` read of a
   `.env`-documented variable is inert. Test the variable the way an operator sets it, not
   through a keyword argument.
6. **"The two measured orders agree" is not "order-independent".** See §7's gate.
7. **A single-occurrence failing-ID difference triggers re-measurement, never attribution.** This
   project lost one round to a difference labelled "known" and part of another to one labelled
   "pre-existing order seams". In both cases the label preceded the evidence.
8. **A gate check must not assert a state the act of dispatching changes.** Three times now a
   coordinator-authored precondition went stale between writing and dispatch: a prompt pinned
   `HEAD 5ecfe90` and the authoring commit invalidated it within the minute; plan_2's frontmatter
   was left at `IMPLEMENTED` because an approval script's replacement silently no-opped; and a
   phase-3 gate check demanded `state: PROJECTED` while authoring the prompt moved the plan to
   `PROMPT_READY`, correctly blocking a session. **Write the check against what the gate protects,
   in a form dispatch cannot falsify** — `git diff <sha> HEAD -- app/` is empty, not `HEAD` equals
   a sha; the state a live prompt implies, not the state it was written under. And assert every
   scripted edit, because a silent no-op is indistinguishable from success.
9. **The closing stamp is defined by the tree, not by the count.** Two rounds read a numeric L4
   budget as forbidding a re-stamp after they had invalidated their own. *(A charter amendment
   is proposed to the owner; until it lands, prompts state it explicitly.)*
10. **When a criterion enumerates per-row mutation outcomes, the consuming session diffs the
    implementer's ledger against that enumeration, row by row.** C2's text read *"each row red
    with its own error, not one shared string"*; r1's ledger recorded row (c) green, in writing;
    the ledger was read by three coordinator consumptions and the diff was never taken. The
    review that finally took it found the row could not fail **and** that the narrowing task 3
    warns about in writing ships with all 51 tests green. A row's presence is not its coverage,
    and a ledger entry is a claim, not evidence.
11. **A named mutation must be shown to reach every sub-check, not merely to redden the test.**
    Sequential assertions short-circuit: C8's addopts check reddens first and returns, so its
    behavioural half — the one that proves work was distributed — was never executed by the
    mutation that was supposed to cover it. Rule 4 says enumerate sub-checks from branch points;
    this is its missing half — **enumerate the mutations too, one per sub-check, and record which
    bites on which.** The charter already requires this of two tests dividing the labour; it
    applies equally to two assertions inside one test.
12. **A criterion asserting a configured value asserts its contract, not its literal.** C8
    required `["-n", "6", "--dist", "loadfile"]` while OD-10 explicitly permits raising the
    count; `-n 8` produces a red suite whose message says the parallel default is *missing* while
    eight workers are demonstrably running. This is N4's time-bomb shape, reintroduced by the
    criterion written to enforce the decision that permits the change. Assert *a positive
    integer*, not `6`.
13. **A shipped-default change has a documentation perimeter, and it is wider than the master
    plan.** Making `-n 6` the default silently re-pointed every command anyone had memorised. Fix
    r3 found one (the legacy sweep); review r4 found two more, one of them in `.env.example` —
    the file OD-7 already taught this project is part of a variable's contract. **Any phase that
    changes `addopts` enumerates every invocation surface in the repository, with the `git grep`
    output in its handoff.**

## 6. Environment

**This section is the citable authority. Prompts point here; they do not restate it.**

### 6.1 Commands

Run from `backend/app/`. `PYTHONPATH=.` is required.

| purpose | command |
|---|---|
| full suite (shipped default, authoritative) | `PYTHONPATH=. pytest -m 'not e2e'` |
| full suite (serial comparator) | `PYTHONPATH=. pytest -m 'not e2e' -n 0` |
| full suite, reversed collection | `BEYO_TEST_COLLECTION_ORDER=reverse PYTHONPATH=. pytest -m 'not e2e'` |
| collection size only | `PYTHONPATH=. pytest -m 'not e2e' --collect-only -q` |
| isolation criterion module | `PYTHONPATH=. pytest -q tests/integration/infrastructure/test_database_isolation.py` |
| one-time legacy reclamation (serial-only; do not combine with xdist) | `BEYO_RECLAIM_LEGACY_TEST_DATABASES=1 PYTHONPATH=. pytest -m 'not e2e' -n 0` |

Machine: **14 cores** (`hw.ncpu` = `hw.physicalcpu` = 14). Runner: pytest 8.3.5,
`asyncio_mode = auto`, **two** registered third-party plugins — `pytest-asyncio-0.25.3` **and
`anyio-4.13.0`** (`pytest -VV`). *(Corrected 2026-08-21: this section said "exactly one plugin",
inherited from phase 1's inspection and never re-checked. Phase 3's task 2 argues that adding a
plugin changes collection and reporting, so the inventory it reasons from has to be true.)*
**No randomizer is installed** — a
`-p no:randomly` in any inherited command is disabling a plugin that does not exist.
`pytest-xdist==3.6.1` is pinned in `app/requirements-dev.txt` for phase 3. The shipped default
is `-n 6 --dist loadfile`; the explicit `-n 0` invocation above remains the serial comparator.

### 6.2 Database topology

Server `localhost:5433` (every connection normalises `localhost` → `127.0.0.1`).

| database | role |
|---|---|
| `beyo_manager` | **the development database. Never a target of anything.** |
| `housing_parser_plan1_20260807` | unrelated real data — a reminder that any name outside the test pattern is someone's |
| `beyo_test_<slot>_template` | migrated template, persistent, rebuilt only when `alembic_version ≠ head` |
| `beyo_test_<slot>_<worker>` | per-process worker database: `main` when serial, `gw0…gwN` under xdist |

**Slot** = the per-checkout discriminator, so two git worktrees do not destroy each other.
`BEYO_TEST_SLOT`, `[a-z0-9]{1,12}`, default `main`. Resolution order:
**`os.environ` → `settings.test_slot` (i.e. `.env`) → `"main"`**. Invalid values **raise**; they
are never normalised, because silently lowercasing `Alpha` to `alpha` merges two checkouts and
reintroduces the hazard the slot exists to remove.

Boundedness is by construction: *slots × (workers + 1)*, and a slot exists only because a human
declared one. **Never name the template by migration head** — every head ever checked out would
leave a template behind, which is the `test_20260820_001, _002, …` growth the intention forbids.

### 6.3 The safety invariant (fails closed)

Before any destructive operation, all must hold or the run aborts:

1. the name matches the slot-scoped pattern
   `^beyo_test_[a-z0-9]{1,12}_(template|main|gw[0-9]+)\Z` — `[0-9]` not `\d` (Unicode digits),
   `\Z` not `$` (trailing newline) — **or** the legacy pattern
   `^beyo_test_(template|main|gw[0-9]+)\Z`. *(Corrected 2026-08-21 after the graph-maintenance
   session found this section narrower than the code: `assert_disposable_database:90-93` accepts
   either, and it must — §6.3's own legacy reclamation could not drop anything if the guard
   rejected legacy names.)*
2. **endpoint confinement** — the target's normalised `(host, port)` matches the configured
   server; this tooling does not operate on a server it was not pointed at;
3. **configured-database identity** — the target is not the configured `(host, port, database)`
   tuple; name comparison alone can be fooled;
4. the database carries the disposability marker (`beyo_test_metadata.database_marker`,
   `marker_key = 'test_database_v1'`) — **or** is a marker-less shell with **zero `public`
   tables**, which is definitionally a half-created artifact of this tooling. Note the default:
   `public_table_count` is `None` unless supplied, and `None != 0`, so an unmarked database is
   refused unless a caller has actually counted its tables — fail-closed by omission;
5. the URL parses, uses a PostgreSQL driver, and carries host, username and database.

`_quoted_identifier` is ASCII-only as defence-in-depth behind the pattern. Only
`asyncpg.exceptions.UndefinedTableError` is tolerated around inspection probes — **never a bare
`except Exception`**; that is how phase 1's B2 swallowed its own refusal.

**Legacy reclamation is opt-in.** Pre-slot names (`beyo_test_template`, `beyo_test_main`,
`beyo_test_gwN`) are reclaimed only under `BEYO_RECLAIM_LEGACY_TEST_DATABASES=1`. It was
unconditional for one round, and a 1.30-second unit run dropped another checkout's live database.

### 6.3a Connection budget — the ceiling on worker count

Measured 2026-08-21: PostgreSQL 18.4, **`max_connections = 100`**, ~16 backends already in use by
the developer's own tools. `.env` sets **`DB_POOL_SIZE=20`** and **`DB_MAX_OVERFLOW=20`**, a
per-process ceiling of **40**. So ~84 connections are free and **three workers at full pool
exhaust the server**; `-n auto` on 14 cores is arithmetically impossible without changing one of
these numbers.

Actual usage is far below the ceiling — `initialize_database` is autouse and function-scoped, so
a test holds one or two connections, not forty. The ceiling is a risk under load rather than a
certainty. **Any worker-count decision states the connection budget it checked and records the
`pg_stat_activity` peak it observed** (phase 3, L15).

Phase 3 measured total `pg_stat_activity` peaks while running the full suite with the completed
criterion module and the monitor's own connection included: `-n 2` = 21, `-n 4` = 23, and
`-n 6` = 25. All are below the server ceiling. The shipped default is `-n 6`; raising the count
still requires a measurement, not an edit.

### 6.4 Redis

Not a hard dependency, deliberately. `isolated_redis_prefix` is session-scoped **autouse** and
overrides `settings.redis_key_prefix` per process — the setting, not `os.environ`, because every
production key builder (`services/infra/redis/keys.py:6`, `routers/utils/rate_limit.py:24,34`,
`services/infra/auth.py:7`, `services/infra/sleep/activity_tracker.py:15`,
`logout_user.py:53`) reads the attribute at call time. Teardown deletes the process prefix
**best-effort**: an unreachable Redis produces warnings, not errors, so the failing-ID set is not
a function of Redis availability.

### 6.5 Schema constants — and the time bomb

`database_isolation.py` derives the Alembic head from the migration scripts and derives the public
table count at runtime as `len(Base.metadata.tables)` plus the enumerated non-metadata tables
`alembic_version`, `ended_shift_collapse_journal`, and `item_valuation_migration_journal`.
Migration-owned journal tables remain deliberately outside ORM metadata. A temporary new revision
therefore invalidates the template by head and is reconciled without editing a constant. This is
the phase-3 resolution of the carried N4 time bomb.

### 6.6 Collection order

`BEYO_TEST_COLLECTION_ORDER` — unset means untouched order; `reverse` reverses exactly once;
**any other value raises `pytest.UsageError`**, never silently treated as off. Shipped rather
than session-local so both L4 runs are taken on the same tree and phase 3 can reuse it.

## 7. Gates

### Projection — instantiated, not retired
Mandatory when a phase touches charter rule 6's silent-failure list. Phase 2 qualified three
times over (ordering, derivation keys, destructive operations) and its projection returned
**AMENDMENTS_REQUIRED** with 15 rows, so the gate has **not** begun self-retiring. **Phase 3
qualifies too** — a worker-count matrix is derivation plus ordering plus destructive lifecycle.

### ⛔ Perturbation gate — phase 3's first obligation (added 2026-08-21 at phase 2's approval)

**Phase 3 does not begin its worker-count matrix until collection-perturbation sensitivity is
characterised on a *serial* runner.**

Phase 2 measured that default order and one deterministic reversal produce identical failing-ID
sets — `21 / 2561 / 1` both ways, `comm` empty in both directions. It also produced
counter-evidence to the general claim, inside its own fix-r4 verification: with **eight extra
criterion rows temporarily present, the failing-ID set differed.** The round attributed the
extras to pre-existing order seams and restored collection size rather than reporting the
divergence as a result.

Inserting eight rows is a far smaller perturbation than distributing every test across workers,
which is the first thing phase 3 does. Measure parallelism before quantifying this and the first
`-n 4` number mixes two effects, and the new authoritative baseline inherits both.

### Approval
A phase reaches APPROVED only on a stamp taken on the tree actually handed over. Where a round's
stamp predates its own later change, the coordinator takes the gate stamp and records the
deviation (done twice: phase 1 r4, phase 2 r4).

## 8. Published baselines

A baseline is `failure-ID set + tree identity + database identity`, **with the count explicitly
subordinate** — the schema `live_clock` earned at its re-review r3. The ID set is the durable
half; compare against it, never the count.

**Baseline schema (extended 2026-08-22, review r4 S4):** a published row states its **failing-ID
set + tree identity + database identity + the services that must be reachable**. Review r4 measured
the fourth axis: with Redis down the suite returns 23 failures and 2 teardown errors, not 21,
because two logout rows assert against a live Redis by name and the `redis_client` fixture's
teardown has no `ConnectionError` guard. §6.4 asserts the opposite and is wrong.

| Phase | Approved | Tree | Suite | Failing-ID set |
|---|---|---|---|---|
| **3** | *not yet — fix r3, pending review* | **`b96802f`**, clean at all three L4 runs | **shipped default:** 21 failed / 2576 passed (52.62 s; second run 53.26 s); **serial comparator:** 21 failed / 2575 passed / 1 skipped / 1 deselected (150.70 s); `pg_stat_activity` peak 25/100 for the shipped six-worker default is carried from the completed r2 matrix | **serial 21-ID set** from phase 2; both shipped-default runs and the serial comparator have empty `comm` in both directions, so no parallel-only ID is added |
| **2** | 2026-08-21 | **`11b4d02`**, clean | **`21 failed / 2561 passed / 1 deselected`**, default 116.20 s and reversed 117.83 s | **21 IDs**, enumerated in `archive/plan_2/2026-08-21_phase2_fix_r4_handoff.md`; `comm`-empty in both directions, coordinator-measured at the gate |
| 1 | 2026-08-21 | `5ecfe90` | `22 failed / 2541 passed / 1 deselected` | the published 22 |

**Provenance of the number, because three downstream consumers depend on it.** The historical 26
became 22 when OD-2 retired four failures that were artifacts of *development-database contents*
rather than code — roughly one sixth of the baseline three approved `live_clock` phases were
measured against was never a statement about the code. It became **21** when phase 2 repaired
`test_add_task_steps_integration::test_adding_a_batch_of_steps_reopens_ready_task`. All 21
remaining are the pre-existing foreign failure stream, unchanged by this project.

Consumers: `live_clock_for_working_time_economics` phase 4, `narrow_typical_work_times` D23, and
this project's own phase 3 — which **replaces** this row under the new runner and must explain
every difference.

## 9. Recognized external commit streams

The owner runs parallel work on this machine (upholstery, Shopify). A perimeter check attributes
files belonging to those streams instead of raising a finding; anything outside them is still a
finding. The authoritative list is `live_clock_for_working_time_economics/master_plan.md` §7 —
**cited, not duplicated**, so the two cannot drift.

`main` is deliberately many commits ahead of `origin/main`; these changes exist only on this
machine until the live-clock work finishes. That is an owner decision, not drift.

## 10. Commits

Checkpoint commits at every `IMPLEMENTED`, prefixed `CHECKPOINT (not approved):`, under standing
owner authorization so no round stops to ask. **Never squashed** — the record of what each round
actually saw is the provenance that makes "every probe was reverted" and "nothing changed outside
the perimeter" verifiable at all. The approval-gate commit captures code plus the archive move
together.

| Phase | Approval gate |
|---|---|
| 2 | `e57ffaf` |
| 1 | `5ecfe90` |
