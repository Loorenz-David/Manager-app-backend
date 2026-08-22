# Intention — per-worker PostgreSQL test databases, then pytest-xdist

```
status: SHAPED (owner intention 2026-08-21) + coordinator inspection folded (round 1)
role: intention (semantic authority — §1 is the owner's words, unrewritten)
hub: ../master_plan.md — tracker, environment topology, gates, published baselines.
     Environment facts are cited from there, never restated here or in prompts.
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
- **Runner inventory: pytest 8.3.5, and exactly one plugin — `pytest-asyncio`.** `pytest-xdist`
  is **not** installed (as phase 1 requires) and **no randomizer is installed**, so a
  `-p no:randomly` seen in an earlier session's command was disabling a plugin that does not
  exist. Two consequences, both for phase 2: **test execution order is deterministic today**
  (collection order), so the stability of the 26-ID set has never been tested against
  reordering; and **xdist will be the first thing in this repository's history to change that
  order.** The intention's correctness gate lists "tests depending on execution order" first
  for good reason — under `--dist load` any order-coupling that exists has simply never been
  exercised. Phase 2 should prefer `--dist loadfile` initially (keeps a file's tests on one
  worker, so file-local ordering survives) and treat a switch to finer distribution as a
  separate, measured step.

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

**Amended 2026-08-21 (OD-5): three phases, not two.** The original two-phase shape is kept
below as provenance; the middle phase was inserted because phase 1's own outcome created it.

- **Phase 1 — isolation.** Steps 1–5 of the owner's ordering. Ends with the suite passing
  **serially** on per-worker databases with the same failure-ID set, and residue measured at
  zero. `pytest-xdist` is **not installed** in this phase. **APPROVED 2026-08-21 (`5ecfe90`).**
- **Phase 2 — order-independence and per-checkout isolation, still serial.** The
  preconditions phase 1 created or exposed: OD-3's ~118-test repair, the slot discriminator
  (§5), B2's surviving no-marker-table shape, Redis isolation, and the two rows that cannot
  fail. Ends when the failure-ID set is **invariant under collection order**, proven
  serially. `pytest-xdist` is **still not installed**.
- **Phase 3 — parallelism.** Steps 6–8, unchanged from what phase 2 originally was. Install
  xdist, compare serial / `-n 2` / `-n 4` / higher (the machine has 14 cores), choose a
  conservative default, and establish the **new authoritative baseline failure-ID set** with
  every difference from the old one explained.

  **First gate, added at phase 2's approval (2026-08-21) — prove invariance under *perturbation*,
  not only under reversal.** Phase 2 measured that default order and one deterministic reversal
  produce identical failing-ID sets. It also produced counter-evidence to the general claim, in
  its own fix-r4 verification: with eight extra criterion rows temporarily present, the failing-ID
  set **differed**. Inserting rows is a far smaller perturbation than distributing every test
  across workers, which is the first thing phase 3 does. **So phase 3 does not begin its
  worker-count matrix until it has characterised what a collection perturbation does to the
  failing-ID set on a serial runner** — otherwise the first `-n 4` measurement mixes parallelism
  with an unquantified order sensitivity, and the new authoritative baseline inherits both.

  Binding consequence for the baseline: **a single-occurrence failing-ID difference triggers
  re-measurement, never attribution.** Phase 2 lost a round to a difference that was labelled
  "known" and a second to one labelled "pre-existing order seams"; in both cases the label
  preceded the evidence.

No phase starts until its predecessor is APPROVED — the same gating that contained defects
inside a phase boundary three times in `live_clock`.

---

## 4. Owner decisions

### OD-1 — the template carries schema only; the nine data-dependent tests get fixtures (2026-08-21)

Raised because phase 1 shipped a design the plan did not specify: the template was seeded with
a `pg_dump --data-only` of the **development** database, so every test's outcome remained a
function of that database's contents. **Owner: clean isolation, fix the nine.**

Ratified: the template is **schema-only** (migration-owned seed rows only, plus the disposability
marker). The reference data the nine tests need is supplied explicitly rather than inherited from
whatever happens to be in dev. The `pg_dump`/`pg_restore` path — and with it finding F6's
password-prompt fragility — is removed.

The evidence that decided it, coordinator-measured:

| configuration | failures | wall time |
|---|---|---|
| original, shared dev database, no isolation | 26 | 135 s |
| as delivered: isolation **+ dev-data restore** | 26 | 169.7 s |
| **schema-only template** | 32 | **109.1 s** |

Clean isolation is **26 s faster than the original and 60 s faster than what shipped**, before
xdist contributes anything. The intention's own clause — *"do not repair 100+ individual tests
**unless investigation proves that is necessary**"* — resolves the other way once the number is
measured: it is **nine tests across four files**, not 100+.

**The nine** (each currently passing only because dev rows exist):
`test_backfill_worker_shift_state_records.py::test_backfill_matches_sweep_read_and_is_idempotent`;
`test_system_transition_reasons_retirement.py` ×4
(`…constraint_does_not_reject_the_declared_state_projection`,
`…constraint_rejects_a_step_record_carrying_both_explanations`,
`…pause_ended_shift_is_still_selectable_through_the_endpoint`,
`…retirement_left_the_guarded_populations_alone`);
`test_kiosk_floor_flow.py` ×3 (`…clock_out_reports_working_steps_it_force_closed`,
`…full_loop_from_floor_sign_in_to_clock_out`,
`…roster_matches_worker_without_a_clock_code_by_email`);
`test_worker_shift_commands.py::test_clock_out_reconstructs_middle_from_step_history`.

### OD-2 — the authoritative baseline is republished at ~22, with every difference explained (2026-08-21)

**Owner: republish as ~22, explained.** Four of the 26 inherited failures are **artifacts of
dev-database contents, not code defects** — they pass on a clean schema, so roughly one sixth of
the baseline that three approved phases were measured against was never a statement about the
code:

1. `test_seed_item_economics_configuration.py::test_human_successors_permanently_freeze_bootstrap_basis_and_model`
2. `test_seed_item_economics_configuration.py::test_person_owned_configuration_and_section_membership_are_not_overridden`
3. `test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`
4. `test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`

Each is the same shape — a test that assumes an empty or clean database and meets rows that a
developer's day left behind (a seed that is already seeded, a "create" whose row already exists).

**A fifth is order-dependent, not data-dependent.**
`test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task` passes when
only the 26 baseline IDs are run and fails in a full suite on the same schema-only database, so
it depends on **state another test creates**. It stays in the baseline and is flagged for phase 2:
**xdist will be the first thing in this repository's history to reorder tests**, and this is the
first confirmed member of the class that will break when it does.

Expected new baseline once OD-1's nine are fixed: **~22 inherited failures**, enumerated and
published with database identity and tree identity per the schema `live_clock`'s phase 3 earned.
`live_clock` phase 4 and `narrow_typical_work_times` D23 consume that number, so it is published
once, honestly, rather than carried forward because it is familiar.

---

## 5. Open design question — concurrent checkouts (raised 2026-08-21, owner planning git worktrees)

**The isolation design is per-*worker*, not per-*checkout*, and that breaks the owner's plan to
run parallel work trees.** `resolve_worker_database_name` derives the name from
`PYTEST_XDIST_WORKER` alone — serial → `beyo_test_main`, xdist → `beyo_test_gw0…` — and
`TEMPLATE_DATABASE_NAME` is the single fixed `beyo_test_template`. **Nothing in either name is
derived from which checkout is running.**

Consequences if two git worktrees run pytest at the same time, which is precisely what worktrees
are for:

1. **Worker-database collision.** Both resolve to `beyo_test_main`. The second run's startup
   does `DROP IF EXISTS` and **destroys the first run's database mid-run**. The first run then
   fails in ways that look like flakiness and are not.
2. **Template clobbering, and it is the worse half.** Both share `beyo_test_template`. Two
   checkouts on different branches are very likely at **different migration heads**, so each run
   sees the other's template as stale and rebuilds it — repeatedly, out from under a live run.
   The failures would be nondeterministic and would look like the suite's own instability.

Neither is a defect in what was built — the plan specified bounded names keyed to worker
topology and that is what it delivered. It is a **requirement that did not exist when the plan
was written** and does now.

**Proposed shape (not yet decided):** add a *slot* discriminator ahead of the worker id —
`beyo_test_<slot>_<worker>`, where `slot` comes from an environment variable defaulting to
`main`, so each worktree declares its own. The guard pattern widens to
`^beyo_test_[a-z0-9]{1,12}_(template|main|gw\d+)$` and stays strict. Boundedness is preserved:
the database count becomes *slots × (workers + 1)*, and a slot only exists because a human
declared one — no per-invocation growth. **Name the template per slot as well**, or better, key
it to the migration head (`…_template_<head>`), which makes "rebuild when the schema changes"
fall out of the naming instead of needing a comparison.

**Recommended sequencing:** do **not** fold this into fix r2 — a session is editing those files
right now, and this is a new requirement rather than a correction to the round's findings. Take
it as the first item of **phase 2**, before xdist, since phase 2 already reopens exactly this
code and the slot discriminator composes naturally with the worker discriminator.

**And the owner's own instinct is the operative conclusion:** create the worktrees *after* this
project lands, not before. Every stream needs the new test infrastructure, so a worktree cut
today would carry the old shared-database behaviour and would have to be rebased onto the new
one anyway.

### OD-3 — the ~118 order-dependent tests are repaired in phase 2, before xdist (2026-08-21)

**Owner: defer to phase 2, first item.** Review r3 established, and the coordinator reproduced,
that OD-1's "nine tests" was an artifact of pytest's default collection order: the template
carries `roles=0, pause_reasons=0, workspaces=0` while the development database carries
`roles=4, pause_reasons=8`, so before phase 1 every test found a populated catalog *regardless
of order*. Under a reversed collection order the suite reads `139 failed / 2422 passed`
(**+118, −1**), and `test_worker_shift_commands.py` run alone gives **41 failed / 1 passed** —
the single pass being the one test fix r2 fixtured.

**The cost is not a catalog.** The coordinator tested the cheap hypothesis — seed the four roles
and eight pause reasons — and it is **refuted**: with the roles seeded the same 41 still fail,
the signature merely moving to `AttributeError: 'NoneType' object has no attribute 'client_id'`,
because `test_worker_shift_commands.py:79` does `select(Workspace).order_by(Workspace.client_id)`
**with no filter** and adopts whatever workspace happens to exist. The class is *helpers that
borrow arbitrary pre-existing rows*, and the repair is to make each create what it needs —
roughly eleven files.

**Binding sequence for phase 2:** the repair lands **before** `pytest-xdist` is installed, so the
first parallel run measures parallelism rather than a pre-existing order dependency surfacing
under a new distribution. Phase 2 already reopens this code for the slot discriminator (§5), so
the repair, the discriminator and the reorder are measured against one another in the same round.

**Phase 1 closes with the number corrected in writing, not with the repair done.** Deliverable 12
is restated as a class of ~118, with the reorder measurement recorded; the previously published
"one remaining non-parallel-safe test" understated it by two orders of magnitude.

### OD-8 — an unstable-test finding does not stop phase 3; it is listed (2026-08-21)

**Owner: continue and list them, recommendation accepted.** Phase 3's task 1 probes whether any
test's outcome is a function of the suite's shape rather than of the code. Until now the plan said
task 1 "runs first and nothing else starts until it has an answer" — but mapped **no answer to an
action**, which would leave the implementer mid-session holding a result with authority neither to
continue nor to stop.

**The rule, now binding:** a non-empty set is **enumerated and published as a separately-named
unstable list**, excluded from the authoritative failing-ID set, and the phase **continues** to
the worker-count matrix. Repairing that class is not phase 3's work.

Why: the measurement is what tells us how large the repair is, and a baseline that names its
unstable IDs out loud is more useful to the three consuming projects than a delayed one. The
rejected branches were stopping (parallelism slips a phase for a repair of unknown size) and
repairing in-phase (the phase's size becomes unknown, which is what phase boundaries exist to
prevent).

### OD-10 — parallel becomes the shipped default, at six workers (2026-08-22)

**Owner: make it the default. Coordinator recommended waiting; the owner reaffirmed, and the
reason given is the stronger one.** *"That is the whole point of this implementation — to have
what was being tested faster, and what will be built part of that speed."*

**Supersedes OD-9's default clause only.** OD-9's condition — *the default stays serial unless the
parallel failing-ID set matches the serial comparator exactly* — was satisfied on 2026-08-22 by
fix r2: after the `app_update_presentations` fixture repair, `-n 2`, `-n 4` and `-n 6` each
returned the phase-2 21-ID set with `comm` empty in both directions. OD-9's reasoning about
asterisks is not overturned; its condition was met, and this records the answer.

**The default is `-n 6 --dist loadfile`, not `-n auto`.** Three reasons, all measured or
structural, and the coordinator's call rather than the owner's:

1. **`-n auto` is 14 workers here, and nothing has ever been measured above 6.** Shipping an
   unmeasured configuration as the default is the failure mode this project exists to end.
2. **The wall-time curve is already flat.** 2 → 4 workers saved 19.2 s; 4 → 6 saved 3.7 s. The
   floor under `--dist loadfile` is the slowest single file, and more workers cannot go below it.
3. **The advisory lock makes startup cost linear in worker count.** Every worker serialises
   through `_template_operation_lock` to copy the template, so worker 14 waits behind thirteen
   copies. Past some count the startup queue eats the parallel win — that count has not been
   measured either.

`--dist loadfile` is part of the default, not an incidental flag: every row of the phase-3 matrix
was measured with it, and the per-test `load` mode has never been run against this suite.

**Raising the count later requires a measurement, not an edit** — master plan §6.3a's rule stands:
any worker-count decision states the connection budget it checked and records the observed
`pg_stat_activity` peak. At six workers that peak is 25 of 100.

**The serial run does not disappear; it becomes the comparator.** `PYTHONPATH=. pytest -m 'not e2e'`
stays the published serial reference so a future divergence between the two modes is detectable at
all — a parallel-only baseline with nothing to compare against is how a scheduling bug becomes
invisible.

**Consequence, charter rule 10 (operational reachability):** parallel execution is now
config-gated behaviour reached by the shipped default, so phase 3 owes a criterion proving the
default configuration actually runs in parallel. A default that silently degrades to one worker
would leave every downstream number describing a mode nobody runs.

### OD-9 — the shipped default stays serial until parallel and serial agree (2026-08-21)

**Superseded in its default clause by OD-10 (2026-08-22); its condition was met, not overruled.**


**Owner: serial default until the differences are repaired, recommendation accepted.** If the
failing-ID set under parallel execution differs from serial and the repair is outside phase 3's
fence, the phase **reports the full matrix and changes no shipped default**. `pytest.ini` is left
as it is.

Why: phase 3's own primary objective is a baseline the organisation can trust, and a caveat
attached to a number three projects consume is the exact failure this project was started to end.
An asterisk everyone must remember is an asterisk everyone eventually forgets.

**This does not delay `live_clock`.** Its ⛔ phase-4 gate asks for xdist installed and the baseline
re-enumerated under the new runner — **not** for parallel-by-default. The gate opens either way.

The speed is not lost, only deferred: the matrix is measured and published, so flipping the
default later is a one-line change against numbers already in hand.

### OD-7 — the test slot becomes a settings field (2026-08-21)

**Owner: settings field, recommendation accepted.** Raised by review r3 as blocking B1.

`resolve_test_slot` reads the slot with `os.getenv`, while the only place the repository
documents the variable is `app/.env.example:8-10` — and `.env` is parsed by pydantic-settings,
which **never populates `os.environ`**. Measured twice, independently by the reviewer and the
coordinator: with `BEYO_TEST_SLOT=shopify` in the `.env` that `settings` actually reads,
`os.getenv` returns `None` and the resolver yields `beyo_test_main_main`. **An operator who
configures the slot exactly where they were told to gets no slot at all**, and the second
checkout then drops the first's database mid-run — intention §5's hazard, surviving behind a
variable that looks set.

**Ratified:** add a `BEYO_TEST_SLOT` field to `app/beyo_manager/config.py` and resolve the slot
from settings with an `os.environ` override, so both `.env` and an exported variable work.

**This does not breach the production fence — it uses a provision written before phase 1
started.** `plans/plan_1.md` §3: *"Nothing under `app/beyo_manager/` except `config.py` **only
if** a test-database setting is genuinely required there."* This is that case, and the change is
one declarative field with no behaviour.

The rejected branch was keeping `os.getenv` and moving the documentation to a tests README. It
costs nothing in production code but requires remembering to prefix every invocation in a second
worktree, and **forgetting is silent destruction rather than an error message** — the failure
mode this project exists to remove.

### OD-6 — a test may adopt a globally-unique catalog row; everything else it creates (2026-08-21)

**Owner: adopt-or-create for globally-unique catalog rows only, recommendation accepted.**
This amends OD-3's repair contract, which phase 2 plan §4 had stated as the unqualified *"a
test may not read a row it did not create."* That rule is **unsatisfiable for one of the
three row classes it covers**, and the phase-2 projection proved it rather than argued it.

`Role.name` carries `unique=True` (`models/tables/roles/role.py:17-21`) — the database permits
exactly one `worker` row in existence. `tests/connecteam/test_clock_actions_integration.py`
creates one and **commits** it, and four of the eleven files commit too. So a factory that
creates its own `WORKER` role inside any committing test collides with whatever committed
first: measured, `UniqueViolationError: duplicate key value violates unique constraint
"ix_roles_name"`. The strict rule would trade ~118 failures that appear when order changes
for a different set that appears when it does not.

The other two classes have no such constraint — `Workspace.name` is not unique
(`workspace.py:14`) and `PauseReason` is unique only on `(workspace_id, slug)` with
workspaces created per test (`pause_reason.py:60`) — so both are created per test.

**The amended contract:**

> For the workspace and pause-catalog classes, a test creates the rows it needs and may not
> read a row it did not create. For **globally-unique catalog rows** (today: `Role`), a test
> uses **adopt-or-create** — take the existing row if present, create it if absent. It may
> never assume one is present.

This is not a new pattern: `tests/fixtures/phase1_reference_data.py:22-28` `_role()` is
already adopt-or-create, so the strict rule as written forbade the shape the approved phase-1
fixtures use.

**Verified sufficient before dispatch, not assumed.** The coordinator applied exactly this
composition — create-your-own `Workspace`, adopt-or-create `Role` — to the single helper
`_seed_workspace_worker` in the worst file, `test_worker_shift_commands.py:78-89`. Run alone
that file goes from **41 failed / 1 passed** to **42 passed in 4.48 s**. One helper, roughly
ten lines. The probe was reverted and the file verified byte-identical
(`0c7d0c99efef16f0343b7fbccc9a0a2b4cb25af7f59f3c8cc2ecc9f98c209f39` before and after).

What this does *not* license: a shared catalog seeded once per run. OD-1's ruling stands —
adopt-or-create happens inside the test's own fixture, per test.

**Clause corrected 2026-08-21 (review r3, N5 — coordinator-authored defect).** This paragraph
originally closed *"and no factory may create a globally-unique row inside a test that commits."*
That forbids the **create** branch of adopt-or-create: on a fresh database the first committing
test that needs a `WORKER` role must create it, so the clause contradicted the contract two
paragraphs above it. The rule intended, and now stated:

> A factory **never creates a globally-unique row unconditionally.** It adopts an existing row
> when one is present and creates it only when absent. The prohibition is on unconditional
> creation, not on creation.

`adopt_or_create_role` was right; the wording was wrong. `plans/plan_2.md` §4 task 1 bound 2
inherits the corrected phrasing.

### OD-5 — xdist moves to its own phase; phase 2 ends at order-independence (2026-08-21)

**Owner: split, recommendation accepted.** §3's phasing is amended above. The reason the
boundary exists is not tidiness: **OD-3 already binds the ~118-test repair to land *before*
`pytest-xdist` is installed**, so the two bodies of work were already sequential — the split
only draws a gate around a boundary the project had committed to.

What it buys: phase 2 ends at a falsifiable claim — *the failure-ID set is invariant under
collection order, proven serially* — and a CHANGES_REQUESTED on eleven files of test repair
no longer blocks a parallel measurement that was never the problem. Phase 3 becomes what the
intention's §1 actually asks for in deliverables 6–14: a measurement phase, mostly evidence.

Unchanged by this decision: the isolation-before-parallelism constraint, OD-3's binding
sequence, and the requirement that the authoritative baseline be re-enumerated and
republished **under the new runner** before any mutation result is trusted on it. Only the
plan boundary moved. `live_clock` phase 4's ⛔ gate is satisfied when **phase 3** closes, not
phase 2 — the gate's own wording is "xdist + per-worker isolation implemented and the
baseline re-enumerated under the new runner."

### OD-4 — the two retirement tests are rewritten against production behaviour (2026-08-21)

**Owner: rewrite.** `test_pause_ended_shift_is_still_selectable_through_the_endpoint` documents
itself as guarding `list_pause_reasons`' `is_deleted` filter; review r3 deleted that filter from
the production query and ran the full suite to a **byte-identical `22 / 2539 / 1`, added ∅ /
removed ∅** — so a soft-deleted pause reason could reappear on the worker's pause sheet and
nothing in the repository would notice. `test_retirement_left_the_guarded_populations_alone`
asserts "7 preserved references" against seven rows its own fixture inserted four lines earlier.

Rewrite both against production behaviour — soft-delete a fixture row and assert it vanishes from
the picker — restoring coverage of a live worker-facing screen. Deleting them was the alternative
and loses that coverage entirely.
