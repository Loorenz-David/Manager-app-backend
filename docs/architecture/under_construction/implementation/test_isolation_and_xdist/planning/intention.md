# Intention — per-worker PostgreSQL test databases, then pytest-xdist

```
status: SHAPED (owner intention 2026-08-21) + coordinator inspection folded (round 1)
role: intention (project root artifact)
owner_decision: this work GATES phase 4 of live_clock_for_working_time_economics
                (that pipeline's master_plan §6 ⛔ block)
date: 2026-08-21
```

## 1. The owner's intention — verbatim, not rewritten

> Task: Introduce safe per-worker PostgreSQL test databases, then enable pytest-xdist
>
> Phase 2 is now complete. Before beginning the next feature phase, I want to address the
> test-infrastructure problem we identified:
>
> 1. The full pytest suite currently operates against a shared development/test PostgreSQL database.
> 2. Some tests outside the economics domain leave persistent rows behind after a full-suite run.
> 3. Repeated full-suite and mutation runs are expensive in wall-clock time.
> 4. We want to eventually use pytest-xdist to parallelize the suite, but parallel execution must not be enabled until database isolation is proven correct.
>
> **Desired architecture.** Each pytest worker must have its own isolated PostgreSQL database
> (`gw0 → db gw0`, `gw1 → db gw1`, …). A non-xdist pytest run must continue to work correctly
> as well. The database lifecycle must be bounded — never an ever-growing collection like
> `test_20260820_001`, `_002`, `_003`.
>
> Open to either **A. Ephemeral worker databases** (create → migrate/setup → test → close
> connections → DROP DATABASE) or **B. Fixed reusable worker databases** (`test_gw0`,
> `test_gw1`, …) reset to a known-clean state between runs. **Choose based on the actual
> repository architecture and measured performance/correctness. Do not choose merely by
> convention.** If persistent worker databases are used, their number and storage consumption
> must remain bounded by the worker topology rather than growing with the number of pytest
> invocations.
>
> **Important constraint: isolation before parallelism.** Do not simply install pytest-xdist,
> add `-n auto`, and declare the work complete. The order must be: (1) inventory current
> pytest + PostgreSQL lifecycle; (2) identify every shared-DB assumption; (3) implement
> per-worker/per-run isolation; (4) prove database cleanup/reset behavior; (5) prove the
> existing suite still behaves correctly serially; (6) enable pytest-xdist; (7) re-run and
> validate the full suite under parallel execution; (8) establish a new authoritative baseline
> failure-ID set. **The previous baseline must not automatically be assumed valid once the
> runner topology changes.**
>
> **First: inspect, don't assume.** Before editing, inspect at minimum: conftest.py files;
> pytest configuration; DB/session fixtures; async SQLAlchemy/asyncpg engine creation;
> application DB configuration; migrations/Alembic setup; fixture scopes; transaction/rollback
> behavior; tests that explicitly commit; tests that spawn background workers/tasks; tests that
> construct application instances; tests that depend on pre-existing DB state; environment
> variables controlling database URLs; existing test database creation/deletion utilities;
> mutation/full-suite runner scripts; any tests or scripts that directly reference the current
> dev/test DB. Trace how a test actually gets from `pytest → fixture → application/session →
> engine → PostgreSQL database`. **I want the isolation boundary placed at the correct
> architectural seam, not patched into individual tests.**
>
> **Existing residue problem.** We previously measured that a full-suite run leaves
> approximately ~116 workspaces, ~101 users, ~19 tasks, ~20 working sections in the shared
> dev/test DB. The item-economics tests themselves were measured as clean; the residue
> originates elsewhere in the wider suite. The new infrastructure should make this class of
> residue harmless across test runs by ensuring the test database is disposable or
> deterministically reset. **Do not spend the project manually repairing 100+ individual tests
> unless investigation proves that is necessary for correctness. Infrastructure-level isolation
> is preferred.**
>
> **Safety requirements.** The implementation must make it structurally difficult or impossible
> for pytest to drop/reset development, staging or production databases, or arbitrary databases
> supplied accidentally through an environment variable. Before destructive DB operations,
> require a strong test-database identity invariant. Database naming/prefix validation may be
> part of the protection, but determine the appropriate invariant from the repository. **A
> malformed configuration must fail closed rather than risk operating on a non-test database.**
>
> **PostgreSQL teardown.** If databases are dropped after runs, handle PostgreSQL connection
> semantics correctly: workers stop using DB → SQLAlchemy/asyncpg pools are disposed →
> remaining test connections are terminated/closed if necessary → database can be safely
> dropped. Teardown must also be considered for normal successful completion, test failure,
> worker failure, and interrupted runs where reasonably possible. **If an interrupted process
> can leave a worker DB behind, the next invocation must safely recognize/reset/reuse/remove
> that bounded DB rather than creating another indefinitely.**
>
> **pytest-xdist.** Only after isolation is proven. Determine an appropriate initial worker
> strategy from the actual machine/test characteristics. **Do not assume `-n auto` is
> automatically optimal.** Compare at least serial, `-n 2`, `-n 4`, and if useful and safe a
> higher worker count. Record wall-clock duration; pass/failure counts; worker count; any
> flaky/new failures; PostgreSQL/resource problems; whether failure IDs differ from the serial
> baseline. **Choose a conservative default if increasing workers produces diminishing returns
> or resource contention.**
>
> **Correctness gate.** Parallelization is accepted only if failures are explainable and
> deterministic. Pay particular attention to: tests depending on execution order;
> module/session-scoped mutable state; shared filesystem state; fixed ports; Redis; background
> workers; global caches; environment mutation; timestamps; unique constraints; tests that
> communicate with processes outside pytest. **Per-worker PostgreSQL isolation solves only
> PostgreSQL interference. Do not infer that the entire suite is parallel-safe merely because
> the DB is isolated.**
>
> **Mutation-testing consequence.** Once xdist changes execution topology, do not trust the
> previous mutation baseline blindly. After the new runner is accepted: run the unmodified full
> suite; record the authoritative baseline failure-ID set; compare with the previous baseline;
> **explain every difference**; only then resume mutation measurements. *A mutation is only
> meaningful relative to a trustworthy baseline.*
>
> **Measurements I want at the end** — a before/after table covering full-suite wall time, DBs
> used, persistent test residue, failure count, failure-ID set, pytest workers. Also report the
> actual database lifecycle implemented, as a diagram.
>
> **Scope discipline.** Do not modify production domain behavior to accommodate the test
> runner. Do not weaken assertions simply to make parallel tests pass. Do not hide failures
> using retries. Do not mark newly failing tests xfail/skip merely because xdist exposed them.
> Do not silently change mutation semantics. If parallelization exposes an actual race,
> ordering dependency, or invalid fixture assumption, report it explicitly and fix it only when
> the correct repair is clear and within the test-infrastructure perimeter. **If resolving it
> requires a production-domain decision, stop and raise an owner decision rather than
> improvising.**
>
> **Deliverable.** A handoff containing: (1) current infrastructure discovered; (2) isolation
> design selected and why; (3) exact files changed; (4) database safety invariant; (5) database
> lifecycle; (6) serial-suite result; (7) parallel-suite results by worker count; (8)
> before/after wall-clock measurements; (9) residue measurements; (10) new authoritative
> baseline failure-ID set; (11) differences from the previous baseline; (12) any tests that
> remain non-parallel-safe and why; (13) recommended default pytest invocation; (14) recommended
> invocation for repeated mutation/full-suite work; (15) remaining risks or follow-up work.
>
> **The primary objective is correct isolation. The secondary objective is faster execution. Do
> not trade correctness or baseline trustworthiness for speed.**

The owner noted that "some parts might be out of date but the goal is there". §2 records what
was measured, and marks which of the intention's premises the measurements change.

---

## 2. Coordinator inspection — measured 2026-08-21, not assumed

The intention's step 1 ("inventory current pytest + PostgreSQL lifecycle") is **discharged
here**, so the implementing session starts from measured fact rather than re-deriving it.
Every claim below was verified at source or by execution on this machine today.

### 2.1 The path from `pytest` to PostgreSQL — and where the seam is

```
pytest
  → tests/conftest.py:initialize_database      (autouse, FUNCTION scope)
  → beyo_manager.models.database:init_db()
  → create_async_engine(settings.database_url) (read at CALL time, every test)
  → _session_factory = async_sessionmaker(_engine)
  → tests/conftest.py:db_session → get_db() → AsyncSession
  → PostgreSQL
```

**The seam is `settings.database_url`, and it is unusually favourable.** `init_db()` reads it
at call time and `initialize_database` is **autouse with function scope**, so the URL is
re-read for *every test*. Overriding `settings.database_url` **once per worker process**
therefore redirects the entire suite with **no per-test patching and no fixture rewriting** —
which is precisely the "correct architectural seam, not patched into individual tests" the
intention asks for. xdist workers are separate processes, so a per-process override is
naturally per-worker.

### 2.2 Facts that change the design

- **Provisioning is cheap — this dissolves the owner's central worry.** The owner wrote: *"if
  every test has to recreate the schema for four dbs we have not improve much performance"*.
  Measured on this machine, against the dev PostgreSQL at `localhost:5433`:

  | operation | measured |
  |---|---|
  | `alembic upgrade head` onto an empty database (**118 revisions**) | **~1.0 s** |
  | `CREATE DATABASE … TEMPLATE …` | **~0.11 s** each (4 in 0.44 s) |
  | `DROP DATABASE` | **~0.11 s** each (4 in 0.44 s) |
  | schema carried by a template copy | **107 tables**, verified on the copy |

  Against a **135-second** suite, provisioning four worker databases from a migrated template
  costs **under half a second**. The premise that recreating schemas would eat the gain is
  **empirically false at this scale**, so the design need not trade cleanliness for speed.

- **A per-test engine is created and disposed ~2515 times per run.** `initialize_database`
  being autouse+function-scoped means `create_async_engine` + `dispose()` per test. This is a
  standing performance question worth measuring during the work (it is *not* required for
  isolation, and must not be "fixed" opportunistically without measurement — changing fixture
  scope changes isolation semantics).

- **The residue mechanism is precisely located.** `db_session` yields from `get_db()` and calls
  `await session.rollback()` **after** the test. A rollback after a test has already
  `commit()`ed is a no-op — so residue is exactly "rows committed by tests that commit". The
  intention's instruction not to repair 100+ tests individually is right: a per-run fresh
  database makes the entire class harmless without touching one test.

- **`tests/conftest.py:count_queries` is broken and unused — dead scaffolding.** Its
  `async_engine` dependency is a **session-scoped** fixture that captures `_engine` once, while
  `close_db()` sets `_engine = None` after every test. Two tests already carry local
  `executed_statements` replacements and say so in their docstrings
  (`test_transition_reason_read_tolerance.py`, `test_list_users_floor_identification.py` —
  the latter states it "resolves before `init_db()` creates it, so it raises on first use (it
  has no other consumers in the suite)"). Charter rule 4 (no dead scaffolding) applies; removal
  is in perimeter, but it is a **finding to report, not a silent deletion**.
  *Not a risk to phase 2's query-count criteria* — those counted via a monkeypatched
  `load_live_worked_seconds` wrapper, independent of the engine.

- **The suite runs on the DEVELOPMENT database.** `app/.env` sets
  `DATABASE_URL=postgresql+asyncpg://…@localhost:**5433**/beyo_manager`. Every baseline this
  organisation has published — including `live_clock` phases 1–3 — was measured there.
- **`app/.env.testing` designates a different server and a stale database.**
  `…@127.0.0.1:**5432**/app_test`, which exists but is stamped `67cfba8fcb2d` with **96
  tables** and lacks `cost_model_versions` and `item_cost_results`. Head is **`c1d2e3f4a5b6`**
  with **107 tables**. It is ~11 tables behind and cannot run the economics suite at all.
- **The migration trap did not fire, but it looked exactly like it would.** `alembic upgrade
  head` exited 0 in ~1 s — the precise signature of the documented trap where migrations log
  success and persist nothing. **Asserted instead of trusted**: 107 tables present,
  `alembic_version = c1d2e3f4a5b6`, `cost_model_versions`/`item_cost_results`/`step_state_records`
  all exist. `migrations/env.py` still carries its `connection.rollback()` guard (line 167).
  **Binding for this project: never accept a migration's exit code as evidence — assert the
  DDL.**
- **The dev PostgreSQL server holds three databases**: `beyo_manager`,
  `housing_parser_plan1_20260807`, `postgres`. Any name outside a strict test pattern is
  therefore someone's real data.
- **Current authoritative baseline: `26 failed / 2515 passed / 1 deselected`**, failure-ID set
  = the 26 enumerated in `live_clock_for_working_time_economics/master_plan.md` §6, measured on
  a clean tree (the shopify stream is committed as of `c0e5407`). **This is the "before" row.**

### 2.3 The design the measurements point to

**Fixed-name, per-run-fresh worker databases, created from a migrated template.** This is
neither the intention's A nor B exactly — it takes the bounded naming of B and the guaranteed
clean state of A, and the measurements say it costs almost nothing:

```
pytest starts
   → resolve worker id (PYTEST_XDIST_WORKER, or "main" when serial)
   → ensure template DB exists and is at head   (rebuild only if its alembic_version ≠ head)
   → DROP IF EXISTS  beyo_test_<worker>          (absorbs any interrupted previous run)
   → CREATE DATABASE beyo_test_<worker> TEMPLATE beyo_test_template   (~0.11 s)
   → override settings.database_url for this process
   → tests execute (every init_db() now lands on the worker DB)
   → dispose pools, terminate stragglers
   → DROP DATABASE beyo_test_<worker>            (best effort)
pytest exits
```

Why this shape:
- **Bounded by construction** — names are `beyo_test_gw0…gwN` / `beyo_test_main`, a set fixed
  by worker topology. An interrupted run leaves at most one database per worker name, and the
  next run's `DROP IF EXISTS` absorbs it. The `test_20260820_001, _002, …` failure mode the
  intention forbids is structurally impossible.
- **No cleaning ritual to get wrong.** The owner proposed "a ritual for cleaning it"; a fresh
  template copy *is* that ritual, at 0.11 s, with no truncation order to maintain and no
  residue class surviving a bug in the ritual.
- **Template built once**, rebuilt only when `alembic_version` ≠ head, so the 1 s migration is
  paid approximately never.

**Safety invariant (fails closed).** Before any `DROP`, all of these must hold, or the run
aborts rather than proceeding:
1. the database name matches `^beyo_test_(template|main|gw\d+)$`;
2. the database is **not** the one named in the configured `DATABASE_URL` (the dev database);
3. the database carries a marker (a dedicated table/row written into the template at build
   time) identifying it as coordinator-created and disposable.
A missing or malformed configuration must abort, never "guess" a target.

---

## 3. Phasing (isolation before parallelism — the owner's constraint, made a gate)

- **Phase 1 — isolation.** Steps 1–5 of the owner's ordering. Ends with the suite passing
  **serially** on per-worker databases with the same failure-ID set, and residue measured at
  zero. `pytest-xdist` is **not installed** in this phase.
- **Phase 2 — parallelism.** Steps 6–8. Install xdist, compare serial / `-n 2` / `-n 4` /
  higher, choose a conservative default, and establish the **new authoritative baseline
  failure-ID set** with every difference from the old one explained.

Phase 2 does not start until phase 1 is APPROVED — the same gating that contained defects
inside a phase boundary three times in `live_clock`.
