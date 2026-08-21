# Plan 1 — per-worker database isolation, proven serially

```
state: NOT_STARTED
phase: 1
date: 2026-08-21
depends_on: nothing. Gates live_clock_for_working_time_economics phase 4.
scope_fence: pytest-xdist is NOT installed in this phase. Parallelism is phase 2.
```

## 1. Goal

Every pytest process runs against its own PostgreSQL database, created fresh from a migrated
template and dropped afterwards, with a fail-closed safety invariant that makes it structurally
impossible to touch the dev database. The suite must pass **serially** with the **same
failure-ID set** as today, and leave **zero residue**.

**NOT in this phase:** no `pytest-xdist`, no `-n` flag, no parallel run. No production domain
change. No repair of individual tests' commit behaviour (infrastructure makes it harmless). No
change to fixture *scopes* as an optimisation — see C7.

## 2. Read first

1. `planning/intention.md` — the owner's intention verbatim (§1) and the **measured**
   inspection (§2). §2.1 gives you the seam; §2.2 gives you facts you do not need to re-derive;
   §2.3 gives the design and the safety invariant.
2. Source: `app/tests/conftest.py`, `app/beyo_manager/models/database.py`,
   `app/beyo_manager/config.py`, `app/migrations/env.py`, `app/pytest.ini`.

## 3. Files expected to change

- `app/tests/conftest.py` — the worker-database lifecycle and the `settings.database_url`
  override. This is the seam; the isolation belongs here, not in individual tests.
- A new module for the destructive operations and the safety invariant (name it; the plan does
  not dictate the path — declare it in the handoff). Keeping `CREATE`/`DROP` and the invariant
  out of `conftest.py` makes the invariant unit-testable, which C2 requires.
- `app/tests/unit/...` — new tests for the safety invariant (C2) and the name resolution (C1).
- Nothing under `app/beyo_manager/` except `config.py` **only if** a test-database setting is
  genuinely required there; prefer keeping test-only concerns in `tests/`. If you must touch
  it, say so and why — the reviewer will check it against this line.

## 4. Ordered tasks

1. **Build the invariant first, and its tests, before anything can drop a database.** C2's rows
   must exist and pass before the lifecycle code is wired up. This is the one ordering the plan
   insists on: the guard precedes the gun.
2. Template management: create/refresh `beyo_test_template` by running migrations onto it, and
   **assert the DDL afterwards — never the exit code** (intention §2.2; the trap's signature is
   an `alembic upgrade` that exits 0 in about a second).
3. Worker lifecycle in `conftest.py`: resolve worker id → drop-if-exists → create from template
   → override `settings.database_url` → (tests) → dispose pools → terminate stragglers → drop.
4. Serial proof: full suite, failure-ID set diffed both directions, residue measured.

## 5. Acceptance criteria

Each row is lettered, carries one named mutation, and states both sides.

- **C1 — worker-name resolution.** Under xdist the name derives from the worker id; with no
  xdist it is the serial name. Rows: `PYTEST_XDIST_WORKER=gw0` → `beyo_test_gw0`;
  `gw11` → `beyo_test_gw11`; unset → `beyo_test_main`. Assert exact strings.
  **Named mutation (the resolver function):** return a constant name regardless of worker id ⇒
  contract = three distinct names, mutation = one name three times, red.
- **C2 — the safety invariant fails closed.** One row per rejection cause, each asserting the
  guard **raises** and that no `DROP` is issued: (a) a name not matching
  `^beyo_test_(template|main|gw\d+)$` — include `beyo_manager` itself, and
  `beyo_test_gw0; DROP DATABASE beyo_manager` as an injection-shaped row; (b) the database named
  in the configured `DATABASE_URL`, even if it were somehow renamed to match the pattern;
  (c) a database lacking the disposability marker; (d) a missing/malformed `DATABASE_URL`.
  **Named mutation (the guard function):** replace its body with `return True` ⇒ contract = four
  rejections, mutation = four acceptances, red on every row.
  **This row is the reason task 1 exists.** The guard must be exercised without a live server.
- **C3 — the template carries the full schema at head.** After template build:
  `alembic_version` equals the repository head **and** the table count matches a freshly
  migrated database **and** `cost_model_versions`, `item_cost_results`, `step_state_records`
  all exist. Assert the DDL, not the migration's exit code.
  **Named mutation:** stamp the template without running migrations (`alembic stamp head`
  equivalent) ⇒ contract = 107 tables, mutation = 0 tables with the version row present, red.
  *This mutation reproduces the documented trap's exact signature, which is why it is the
  named one.*
- **C4 — a worker database is a faithful copy.** A database created from the template has the
  same table count and head revision as the template.
  **Named mutation:** create the worker database **without** `TEMPLATE` ⇒ contract = 107 tables,
  mutation = 0, red.
- **C5 — the suite actually runs on the worker database, not the dev database.** A test asserts
  that the live `settings.database_url` (and the engine's URL) names `beyo_test_*` and **not**
  `beyo_manager`. This is the row that proves the seam works end-to-end.
  **Named mutation:** remove the `settings.database_url` override ⇒ contract = a `beyo_test_*`
  name, mutation = `beyo_manager`, red.
- **C6 — residue is zero across two consecutive runs.** Run the suite twice; after the second,
  the dev database's `workspaces`/`users`/`tasks`/`working_sections` counts are **unchanged from
  before the first run**, and the worker databases no longer exist. Contract states the
  before-numbers as literals.
  **Named mutation:** point the override back at the dev database ⇒ contract = unchanged counts,
  mutation = counts grow, red.
- **C7 — the failure-ID set is unchanged.** Full serial suite on the new infrastructure:
  `comm`-diff the failing-ID set in **both directions** against the 26 enumerated in
  `live_clock_for_working_time_economics/master_plan.md` §6. Any difference is a **finding to
  explain, not a number to update** — the intention is explicit that the old baseline is not
  automatically valid, and equally that a changed set must be *explained*.
  **No mutation** — this is an equality claim over the whole suite, and its scope is L4 by
  construction (charter test-evidence section: baseline re-enumeration).
- **C8 — an interrupted run is absorbed, not accumulated.** Create `beyo_test_main` by hand,
  leave it behind, then start a run: it is dropped and recreated, and the database count on the
  server returns to its pre-run value. Assert the server's database list is identical before and
  after.
  **Named mutation:** make creation use a unique suffix per invocation ⇒ contract = the database
  set returns to its original membership, mutation = it grows by one per run, red. *This is the
  `test_20260820_001, _002, …` failure mode the intention forbids, made falsifiable.*

## 5A. Traps this plan inherits (each already cost someone a round)

- **Never accept a migration's exit code as evidence — assert the DDL.** The documented trap
  makes `alembic upgrade` log success, exit 0, and persist nothing. During inspection it exited
  0 in ~1 s, which is exactly what the trap looks like; only asserting 107 tables distinguished
  them. C3's named mutation exists to keep that distinction alive.
- **A fixture whose expected value is the same under the defect proves nothing.** Before
  choosing any fixture, compute the value under the contract *and* under the mutation and
  confirm they differ. Four of `live_clock`'s eleven "row that cannot fail" instances were
  fixtures sitting where two forms coincide.
- **`count_queries` in `conftest.py` is dead and broken** (intention §2.2). You will be editing
  that file. Removing it is in perimeter (charter rule 4), but **report it as a finding rather
  than deleting it silently**, and note the two local `executed_statements` duplicates.
- **Do not "fix" the per-test engine churn opportunistically.** `initialize_database` being
  autouse+function-scoped costs ~2515 engine create/dispose cycles, and widening its scope looks
  like free speed — but fixture scope *is* isolation semantics here. Measure it, report it, and
  leave the change to phase 2 or a decision card.

## 6. Notes

- Destructive verification only on disposable databases; the configured dev database is left at
  head and untouched (charter rule 7).
- The `CREATE`/`DROP` connection cannot be to the database being dropped — use a maintenance
  connection (`postgres`), and terminate stragglers with `pg_terminate_backend` before dropping.
- Evidence records carry hypothesis · scope · command · tree identity · result · ID delta
  (charter "Test-evidence scope and reuse"). C7 is L4; every other row is L1/L2.

## 7. Review log

(empty — append-only)
