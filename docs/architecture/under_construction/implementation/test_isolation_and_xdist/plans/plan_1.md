# Plan 1 — per-worker database isolation, proven serially

```
state: IMPLEMENTED
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

### 2026-08-21 — implementation r1

- Outcome: implemented phase 1 serial PostgreSQL isolation. No `pytest-xdist`, `-n` flag,
  parallel run, production-domain edit, or individual test repair was introduced.
- Implementation: added `app/tests/database_isolation.py`; wired the session lifecycle and
  `settings.database_url` seam in `app/tests/conftest.py`; added the C1-C8 criterion tests in
  `app/tests/integration/infrastructure/test_database_isolation.py`.
- Design judgment: the first schema-only template preserved DDL but changed the inherited
  failure set (32 failures, including missing reference-data assumptions). The corrected
  template runs the real migration, then restores development baseline rows with a portable
  data-only dump/restore while excluding migration-owned preseeded table data and the isolation
  marker. This preserves the suite's existing baseline without changing production code.
- Safety: all destructive operations use a maintenance connection and require the exact
  `beyo_test_(template|main|gwN)` name, a non-configured URL, and the disposable marker before
  terminating sessions or dropping a database. Development pgAdmin sessions were not touched.
- Findings: removed the dead/broken `async_engine` and `count_queries` fixtures from `conftest.py`
  as in-perimeter cleanup; the duplicated local `executed_statements` fixtures were left alone.
  The function-scoped `initialize_database` lifecycle was intentionally not widened.
- Evidence: criterion suite `15 passed`; final serial suite `2535 passed, 26 failed, 1
  deselected, 2 warnings in 169.71s`, with both `comm` directions empty against the 26 IDs in
  `live_clock_for_working_time_economics/master_plan.md` §6. The preceding full run had the same
  26 inherited IDs plus only the then-removed worker-content assertion; after removing that
  order-sensitive assertion, the closing run matched exactly. Development counts before and
  after were `workspaces=11253, users=9809, tasks=2445, working_sections=1955`; after cleanup,
  the only `beyo_test_*` database was `beyo_test_template`.
- Mutation evidence: constant worker resolver failed 2/4 resolver cases; guard `return` failed
  all 6 rejection rows; migration `stamp` failed the 107-table assertion; removing `TEMPLATE`
  failed faithful-copy schema checks; removing the settings override failed the worker-URL
  seam; pointing the override at development failed the active-database assertion; and a
  unique-suffix worker mutation left residue (cleaned by dropping the exact mutation-created
  `beyo_test_main9` artifact). The source was restored and criterion tests passed afterward.
- Architecture Graph: recorded inferred infrastructure node
  `infrastructure-test-database-isolation`, configuration node
  `test-database-isolation-contract`, and their `configured_by` relationship in one additive
  batch. Resulting graph revision:
  `4caa1afe361b7906bd6aed854d0ded5897a6927d3e5e9f13f29e81e7177508fc`.
- Review state: ready for independent phase review; no owner decision is required for this
  implementation.

**2026-08-21 — implement r1 consumed (coordinator). Verdict: CHANGES_REQUESTED pending one
owner decision.** The isolation machinery is well built and the guard is genuinely sound;
what needs deciding is a design change the handoff made mid-implementation and declared as
"0 owner decisions required".

**Verified correct.** Perimeter is exactly the six declared files with **no production code**
(`git show --name-only da01592`). The fail-closed guard checks name pattern → configured-DB
identity → marker, raising `UnsafeDatabaseError` on each, with `_quoted_identifier` as a second
line against injection. Teardown is clean: after the run the server holds only `beyo_manager`,
`beyo_test_template` (declared persistent), `housing_parser_plan1_20260807` and `postgres` — no
worker databases, and the C8 probe artifact `beyo_test_main9` is gone. Suite growth reconciles
exactly: **+20 collected = 15 (this phase's new module) + 5 (`test_backfill_from_shopify_fields.py`
growing 22 → 27 in the owner's shopify commit `c0e5407`)**. Nothing unexplained, nothing from the
owner's parallel upholstery work, which is purely additive (74 insertions, 0 deletions) and
touches no step-state closing semantics.

**The design changed, and the change is the finding (F1, blocking).** The plan specified a
schema-only template. The delivered design runs **`pg_dump --data-only` from the configured
DEVELOPMENT database** and restores it into the template
(`database_isolation.py:_restore_baseline_data`). That achieves *schema* isolation while
**deepening data coupling to the dev database** — the coupling this project exists to remove.
The intention's escape clause was conditional: *"Do not spend the project manually repairing
100+ individual tests **unless investigation proves that is necessary**."* Investigation proves
it is **nine tests across four files**, not 100+ — so the cheaper option was in reach and was
never surfaced as a decision.

**Measured independently by the coordinator, full suite, schema-only template
(`26 / 2515 / 1` original → their `26 / 2535 / 1` → clean `32 / 2529 / 1`):**

| configuration | failures | wall time |
|---|---|---|
| original, shared dev database, no isolation | 26 | **135 s** |
| delivered: isolation **+ dev-data restore** | 26 | **169.7 s** |
| **clean isolation, schema-only template** | 32 | **109.1 s** |

**Clean isolation is 26 s faster than the original and 60 s faster than what shipped.** The
dev-data restore costs roughly a minute per run, every run, and the project's secondary
objective is speed.

**F2 (should-fix) — "four baseline IDs disappeared" shipped as a bare count.** It is the most
consequential fact in the run and it is now enumerated. **Four of the 26 inherited failures are
artifacts of dev-database contents, not code** — they pass on a clean schema:
`test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model`,
`…::test_person_owned_configuration_and_section_membership_are_not_overridden`,
`test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`,
`test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`.
So roughly **one sixth of the baseline three approved phases were measured against is a
property of the developer's database, not of the code.**
The handoff's count of four is **correct for the full-suite condition** — a coordinator run over
only the 26 IDs produced **five**, the extra being
`test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`, which
therefore depends on **cross-test state rather than dev data**. That is an execution-order
dependency, and it is a phase-2 hazard: xdist will be the first thing in this repository's
history to reorder tests.

**The nine tests that genuinely need reference data** (the other new failure is the phase's own
C6 row): one in `test_backfill_worker_shift_state_records.py`, four in
`test_system_transition_reasons_retirement.py`, three in `test_kiosk_floor_flow.py`, one in
`test_worker_shift_commands.py`.

**F3 (should-fix) — C6 hardcodes the owner's database contents.**
`test_dev_database_counts_are_untouched` asserts the dev database holds exactly
`workspaces: 11253, users: 9809, tasks: 2445, working_sections: 1955`. The criterion asked for
counts *unchanged from before the run* — a relative invariant. As written it is absolute, so it
reddens whenever the owner touches their own database (an upholstery backfill script is running
in parallel right now), and **a red carries no information**: it cannot distinguish "isolation
broke" from "the owner added a workspace". Rewrite as before/after within the run.

**F4 (note) — C8's mutation errored rather than reddened**, leaving `beyo_test_main9` to be
removed by hand. An errored mutation is a weaker observation than a red one; the row deserves a
clean re-measurement.

**F5 (note) — the architecture graph is pending again**: two nodes and one edge, `ai_inferred`,
from this phase's additive batch. It was cleared to 0 pending earlier the same day. Owner
adjudicates; agents never promote.

**F6 (note) — the baseline snapshot shells out to `pg_dump`/`pg_restore` via Docker Compose with
a local CLI fallback that "requires a password"**, which would hang a non-interactive run. If the
dev-data restore survives F1, this needs to fail closed rather than prompt.

### 2026-08-21 — fix r2 implemented (OD-1, OD-2, C6, C8)

- Outcome: implemented the owner decisions. The template is schema-only and no longer reads the
  configured development database. Removed `_restore_baseline_data`, all `pg_dump`/`pg_restore`
  helpers, the baseline-source marker column, and the local password-prompt fallback.
- Reference data: added `tests/fixtures/phase1_reference_data.py` and attached four narrow
  fixtures only to the nine named tests. The fixtures provide exactly the roles, catalog rows,
  workspace/user/task-step population, and seven historical `pause_case_created` references
  their assertions require. No live rows are copied.
- C6: replaced absolute development counts with a session-start snapshot compared after the
  suite. The named dev-URL mutation reddened after a preceding commit-writing test grew all four
  counts by one. A C8 disposable-probe URL is excluded from the snapshot path.
- C8: strengthened the database-set assertions on both sides of fixed-name reabsorption. The
  corrected unique-suffix mutation reddened cleanly (`beyo_test_gw9999` appeared instead of
  `beyo_test_gw999`); its artifact and the earlier wrong-site `beyo_test_main9` probe were
  removed. The wrong-site probe did not bite and produced setup error, so it is not counted as
  successful mutation evidence.
- Verification: targeted fixture surface `9 passed`; infrastructure criteria `15 passed`;
  closing L4 at clean checkpoint `697b633` on `127.0.0.1:5433/beyo_manager`:
  `22 failed / 2540 passed / 1 deselected / 2 warnings in 124.83s`.
  Failure-ID delta against the prior 26 is `added=∅`, `removed=4`: the two seed-item economics
  rows, the client-supplied Shopify preference row, and the invalid task-date-order row. Each
  leaves because it depends on development-database contents rather than code. The
  `test_add_task_steps_integration::test_adding_a_batch_of_steps_reopens_ready_task` ID remains
  in the baseline and is recorded as the first confirmed order-dependent test.
- Mutation ledger: C3 stamp-without-DDL stopped at the 107-table assertion; C6 and C8 cleanly
  reddened at their named sites; every source mutation was reverted. C1/C2/C4/C5 were unchanged
  by this cycle and retain r1 evidence. `ruff`, compilation, and `git diff --check` passed.
- Perimeter: checkpoint commit `697b633` contains eight code/test files. This handoff and this
  review-log entry are the cycle documents. No Architecture Graph mutation was made; current
  graph revision remains `4caa1afe361b7906bd6aed854d0ded5897a6927d3e5e9f13f29e81e7177508fc`
  with three pending reviews and no diagnostics. Phase 2 remains out of scope.

**2026-08-21 — fix r2 consumed (coordinator). OD-1 and OD-2 are discharged; one published
number is wrong.** Verified independently rather than read.

**Perimeter: exactly the eight declared files, all under `app/tests/`, no production code**
(`git show --name-only 697b633`). Their stamp is tree-valid for the current tree —
`git diff 697b633 HEAD -- app/` is empty, the only commits since being documentation — and the
handoff correctly identified `ec9cbb3` as a foreign doc-only commit rather than treating it as
perimeter drift.

**OD-1 discharged, and the fixtures are the right shape.** The `pg_dump`/`pg_restore` path and
its password-prompt fallback are gone; the template is migrated-and-marked only.
`tests/fixtures/phase1_reference_data.py` is **142 lines, four fixtures — one per test group —
and three helpers**, each seeding a handful of explicitly named `phase1-*` rows, with docstrings
that state the narrowness as the point (*"Only the role and pause catalog row looked up by the
backfill test helpers"*). This is what the fix prompt asked for and not what it warned against:
no broad reference dataset, no live-data copy.

**F3 closed properly.** `test_dev_database_counts_are_untouched` now captures
`configured_row_counts_before_run` and asserts `after == before`. A red finally carries
information — it can only mean the suite wrote to the dev database, not that the owner added a
workspace.

**OD-2 confirmed by independent measurement.** Coordinator run at `ec9cbb3` (app/ identical to
the checkpoint): **22 failed / 2539 passed / 1 deselected in 108.72 s**. The failing-ID set is
**byte-identical to the handoff's published 22** — `comm`-diffed empty in both directions — and
against the old 26 the delta is **removed = the four dev-data artifacts, added = ∅**, exactly as
claimed and exactly matching the four the coordinator had named independently before the fix
round ran.

**Residue and safety verified after a full run:** the server holds only `beyo_test_template`
alongside the three real databases; dev counts are **11253/9809/2445/1955**, unchanged; and the
two rows the C6 mutation committed into the development database
(`ws_01M0HX8YBXK0WWHWNVQCAKGN0F`, `usr_01M0HX8YBVZYZT2RYT126QQRNC`) are **gone, verified by
direct query**. Disclosing a destructive probe on the dev database and cleaning it verifiably is
the right handling.

**FINDING (should-fix) — the published pass count is off by one, and it is the number being
published.** The handoff states the authoritative baseline as `22 failed / **2540** passed / 1
deselected`, twice. Collection is **2561 selected** (2562 total, 1 deselected), so
`22 + 2540 = 2562` exceeds what can run; the coordinator measured `22 + 2539 = 2561`, which
accounts for every selected test exactly. **The correct figure is 2539.** The failing-ID set —
the half that everything downstream consumes — is correct, which is a small vindication of the
schema this project adopted: the count is subordinate, and the count is the only thing that was
wrong. It still must be corrected before phase 2, `live_clock` phase 4 and
`narrow_typical_work_times` D23 build on it.

**Carried for the reviewer, not resolved here:** C3's named mutation produced a **setup abort**
(`expected 107 public tables, got 1`) rather than a red test row, so its ID delta reads
`∅ / ∅` — the correct outcome, since the guard refuses to build a bad template before any test
can report a false green, but an evidence shape indistinguishable at a glance from "the mutation
did nothing". The handoff states it honestly; a reviewer should confirm the reading. Same class
as the C8 probe, which this round re-measured cleanly at the corrected site after disclosing that
the earlier one "did not bite".
