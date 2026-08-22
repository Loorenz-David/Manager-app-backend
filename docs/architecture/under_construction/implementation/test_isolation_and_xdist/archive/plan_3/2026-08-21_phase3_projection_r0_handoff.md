---
plan: 3
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-21
actor: Opus 5 (1M context) — plan-projection gate, independent session, no planning context
---

# Phase 3 projection (round 0) — verdict: AMENDMENTS_REQUIRED

**25 ledger rows. 2 owner decisions. 0 L4 runs taken (budget was 0).**

## 1. Verdict

`AMENDMENTS_REQUIRED`. The plan's *shape* is right — the perturbation gate belongs first, the
template hazard is the correct sharpest risk, and the baseline is correctly named the primary
objective. What it does not determine is **who observes the things it asserts**. Three of its six
criteria describe state that exists only *during* a parallel run, and none names an observer;
one criterion's contract is a disjunction that cannot be written until a delegated free choice is
made; one carried code item has no criterion at all; and the task that owns the phase's sharpest
hazard names one of that hazard's three failure paths.

Two findings are load-bearing enough that the first `-n 2` run will hit them within minutes
(F1, F2), and one is a measured arithmetic trap in the repair the plan asks for (F3).

## 2. What this means, in plain words

The plan for the parallel-test phase is good but not yet finishable as written: several of its
success conditions describe things that happen inside several test processes at once, and it
never says who is supposed to watch them or what exactly they should see. I also found that the
very first parallel run will almost certainly fail in a specific, predictable place — a handful of
our own infrastructure tests check "which databases exist on the server", which stops being a
stable question the moment four test processes are creating and dropping databases at the same
time. That is our test's assumption breaking, not the suite breaking, and the repair is small and
known. Two things need you personally, both about what happens when a measurement comes back
unflattering; they are the next section and they are short. Nothing else needs you — everything
else is a paragraph fix to the plan before the implementer starts.

## ⚠ OWNER DECISIONS REQUIRED (2)

### Card 1 — If the first measurement finds unstable tests, does the phase keep going?

**Question:** If the perturbation probe finds tests whose result changes with the suite's shape
rather than with the code, does phase 3 continue to the worker-count matrix (listing them), or
stop and hand the repair to a further phase?

**Story:** You expect parallel tests this week. The first measurement comes back with four tests
that pass or fail depending on how many tests ran before them. Repairing that class is what the
last phase spent five rounds doing. Measuring speed on top of it produces a number three other
projects will build their next year of measurements on, with the instability silently baked in.

**Branches**
- **Continue, list them, exclude them from the published set** — parallel numbers land this week;
  the new baseline is honest and carries a separately-named unstable list.
- **Stop and repair first** — the baseline is fully clean; parallelism slips by roughly one phase,
  and the speed work waits on a repair of unknown size.
- **Continue and repair inside this phase** — one phase does both; the phase's size becomes
  unknown, which is what phase boundaries exist to prevent.

**Recommendation:** continue and list them — the measurement itself is what tells you how large
the repair is, and a baseline that names its unstable IDs out loud is more useful to the three
consuming projects than a delayed one.

**On silence:** the gate holds. The implementer runs the probe, reports the set, and stops
**before** installing pytest-xdist; no matrix is measured and nothing is published.

**Trace:** plan_3 §4 task 1, §5 C1; master plan §7 perturbation gate; intention §3 phase-3 bullet.

### Card 2 — If parallel and serial disagree and no repair is in scope, what ships as the default?

**Question:** If the failing-test set under parallel execution differs from serial and the repair
is outside this phase's fence, does the shipped default become parallel (with the differing tests
declared not parallel-safe), or stay serial?

**Story:** Four workers cut the suite from about two minutes to well under one. Two tests fail
only in that mode, for reasons that live in application code this phase is not allowed to touch.
Whatever runs by default becomes what every future measurement in three projects is compared
against, and an asterisk that everyone must remember is an asterisk everyone eventually forgets.

**Branches**
- **Parallel default, differing tests declared** — the suite is roughly three times faster; the
  published set carries a caveat two other projects must carry with it.
- **Serial default, parallel numbers reported** — the baseline stays exactly comparable to
  today's, the speed waits for a repair phase. The live-clock phase-4 gate opens either way, since
  it asks for xdist installed and the baseline re-enumerated under the new runner, not for
  parallel-by-default.
- **Repair inside this phase** — fastest end state, phase size unknown (same hazard as card 1).

**Recommendation:** serial default until the differences are repaired — the phase's own stated
primary objective is a baseline the organisation can trust, and a caveat attached to a number
three projects consume is the exact failure this project was started to end.

**On silence:** the gate holds. The implementer reports the full matrix and changes no shipped
default; `pytest.ini` is left as it is and the choice returns to you at the approval gate.

**Trace:** plan_3 §4 task 5, §5 C5, §3 (`pytest.ini`); master plan §6.1, §8; intention
deliverables 12–14.

## 3. Gate check — one item is false, and I proceeded

| Gate item | Result |
|---|---|
| `plan_2.md` frontmatter reads `state: APPROVED` with a `gate_stamp:` line | **FALSE** — see below |
| `plan_3.md` exists, `state: NOT_STARTED`, §7 Review log empty | PASS (`plans/plan_3.md:3`, §7 line 247) |
| `pytest-xdist` not installed; no `-n` in any pytest configuration | PASS — `python -m pip show pytest-xdist` → not found; `import xdist` → `ModuleNotFoundError`; `pytest.ini` `addopts = -ra --strict-markers --strict-config`; no `setup.cfg`, `tox.ini` or `pyproject.toml` exists in `backend/` or `backend/app/` |
| architecture graph: 0 pending, 0 stale, 0 diagnostics | PASS — `archgraph_status`: `pendingReviewCount: 0`, `staleNodeCount: 0`, `diagnostics: []`, 192 nodes / 289 edges |

**The false item is bookkeeping, not substance, so I did not stop.** `plans/plan_2.md:4` still
reads `state: IMPLEMENTED — 2026-08-21 (fix r4; …)` and carries no `gate_stamp:` line, while the
phase is approved everywhere else that records state: master plan §3 tracker row 2 reads
**APPROVED**, plan_2 §7's final entry reads *"Verdict: phase 2 APPROVED"* with the coordinator's
gate stamp at `11b4d02`, and §10 records the approval commit `e57ffaf`. The precondition the gate
protects — *phase 2 is approved* — is verifiably true, so stopping would have spent the session on
a stale line. **Routed as F7 (coordinator, one-line fix).** Note that no plan file in this project
has ever carried a `gate_stamp:` frontmatter key; if the charter row schema is meant to include
one, that is a schema decision, not a phase-2 omission.

## 4. Decision ledger

25 rows. Classification: **plan gap** → amendment before the implementer prompt compiles;
**free choice** → delegate explicitly, in writing; **upstream** → intention/master plan.

| # | Decision point the artifacts do not determine | Class | Proposed routing |
|---|---|---|---|
| L1 | **What a probe test *is*.** Task 1 says "insert no-op tests"; the observation it is chasing was produced by eight *database- and Redis-touching* criterion rows. A `def test_probe(): pass` cannot reproduce that mechanism. | plan gap | Amend task 1: state the probe's shape, and state which hypothesis each shape tests (F6). |
| L2 | **No noise floor.** Insertion preserves every other test's *relative* order, so a differing set is either absolute-position sensitivity or plain run-to-run nondeterminism — and phase 2's own S5 proved this suite has a nondeterministic (object-lifetime) member. Task 1 has no repeat-at-identical-condition run. | plan gap | Amend §4 task 1 and §6: add ≥1 unperturbed repeat as budget row 0; standing rule 7 binds task 1's own result. |
| L3 | **No harness-present control.** Every probe run is on a tree that also contains the new harness. Nothing separates "the probes moved things" from "the harness's mere presence moved things". | plan gap | Add one run with the harness present and zero probes enabled. |
| L4 | **C1's union has no stopping rule.** "The union of IDs that ever differ" over a probe set the plan deliberately does not fix is not a decidable claim: the implementer decides when to stop and the union is a function of that. | plan gap | Require `n` and the positions to be declared **before** the first run (§6 already requires declaring `n`; extend it to the positions and to a re-measure-before-admitting rule per L2). |
| L5 | **Does the harness survive into the handed-over tree?** §3 says "New: a perturbation harness … location yours". If it survives and collects, the republished baseline's collection size includes the probes and three consuming projects inherit them; if it is deleted, the closing stamp's tree is not the tree the probes were measured on. | plan gap | Require the harness to be **collection-neutral unless explicitly enabled** (the `BEYO_TEST_COLLECTION_ORDER` pattern is the precedent), so it can ship inert and the baseline stays clean. |
| L6 | **What "collection position" means.** File-level position (governed by path sort order under `testpaths = tests`) and within-file position are different perturbations with different mechanisms; the plan says "several collection positions" without choosing. | free choice | Delegate explicitly, bounded: the implementer states which axis is probed and how position is controlled. |
| L7 | **Probe collection must be identical in every worker.** xdist aborts a run when workers collect different test lists; a probe mechanism keyed to process or worker identity would trip that. | free choice | Record as a constraint on L5's mechanism. |
| L8 | **Which manifest gets `pytest-xdist`, and pinned to what.** `requirements.txt:48-49` and `requirements-dev.txt` **both** pin `pytest==8.3.5` / `pytest-asyncio==0.25.3`; §3 says "`requirements*.txt` / dependency manifest". | free choice | Delegate, bounded: name the file, pin exactly as its neighbours are pinned, and say why that file. |
| L9 | **The plugin inventory the plan reasons from is wrong.** Master plan §6.1 says "exactly one plugin (`pytest-asyncio`)"; `pytest -VV` today registers **two** third-party plugins — `pytest-asyncio-0.25.3` and **`anyio-4.13.0`**. Task 2's whole argument is that adding a plugin can change collection and reporting. | upstream (master plan §6.1) | Correct §6.1 before the prompt compiles; the pre/post-install serial comparison is unaffected but the inventory it cites must be true. |
| L10 | **The template hazard has three paths; task 3 and C2 name one.** See F1. Concurrent `_ensure_template` can also (a) race two `CREATE DATABASE <template>` calls and (b) **DROP the template while another worker copies or migrates it**. C2's mutation pins one exact error string that the other two paths do not produce. | plan gap | Amend task 3's wording and C2's rows to cover absent-template and stale-template, each with its own exact expected outcome. |
| L11 | **C2's observer.** The existing criterion module already drives lifecycles in-process (`DatabaseIsolation(settings.database_url, worker_id="gw999")`, `test_database_isolation.py:324`), so concurrent starts can be proven **serially**, without the plugin this phase installs. The plan does not say so and an implementer may reach for a real `-n 4` run. | free choice | Delegate explicitly; add the constraint that probe worker ids must not collide with real `gw0…gwN` names, nor with each other if distribution ever goes finer than `loadfile`. |
| L12 | **What exactly gets serialised.** The "other users" of the template are not the copy — they are `inspect()`, `_has_legacy_baseline_source()` and `_set_marker()` connections (`database_isolation.py:322, 336, 318`) and the ~1 s alembic subprocess in `_migrate_and_assert`. A guard around only `_create_database_from_template` leaves the real window open. | plan gap | Task 3 states that the serialised region is the whole of `_ensure_template` + the copy, not the `CREATE DATABASE` statement. |
| L13 | **Task 4's inventory has no output contract and no criterion.** Eleven resource classes are named; only Redis has a criterion (C4). A reviewer has no rubric for the other ten. | plan gap | State that the inventory is a handoff section with a per-class disposition (reached / not reached / isolated / declared), and that C4 covers Redis only. |
| L14 | **C4 is either unobservable or already true.** The prefix is `uuid4`-derived per process (`conftest.py:56`), so two workers *cannot* share one — no work is required and no in-process test can see another process's value. Its second clause ("neither is the shipped default") is already asserted by `test_default_redis_key_uses_the_process_prefix` (`test_database_isolation.py:111-115`), so a new row restating it is decoration with a correct name (charter rule 2's companion). | plan gap | Either define the cross-process observation mechanism concretely (each worker publishes its prefix to a shared artifact; the assertion runs after the run) or rewrite C4 as "confirm and record", not "prove". |
| L15 | **"A higher count if useful and safe" has no definition of safe.** Measured today: PostgreSQL 18.4, `max_connections = 100`, **16 backends already in use**, and `.env` sets `DB_POOL_SIZE=20` / `DB_MAX_OVERFLOW=20` — a per-process ceiling of 40. Three workers filling their pools exhaust the server; `-n auto` is 14 workers. | free choice | Delegate, bounded: the implementer states the connection budget it checked before the highest-count run, and records `pg_stat_activity` peak per matrix row. |
| L16 | **Reversal proves less under xdist than it did serially.** Budget row n+6 reuses `BEYO_TEST_COLLECTION_ORDER=reverse` as "C5's second condition", but under xdist the execution order is the scheduler's, not the collection list's; reversal only permutes *within* a worker's assignment. | plan gap | State what the second condition is claimed to prove under a parallel runner, or replace it with a second condition that varies scheduling. |
| L17 | **"Derive both from the repository" has no correct obvious source for the table count.** Measured: `Base.metadata.tables` = **104**; the migrated template = **107**; the development database = **109**. See F3. | plan gap | Task 6 names the derivation (metadata + `alembic_version` + migration-owned `_journal` tables) **or** replaces the count with a content assertion. It must forbid deriving from the dev database, which re-imports dev contents into the test contract (OD-1's class). |
| L18 | **C6's contract is a disjunction gated on a delegated choice.** "The run proceeds (or fails with an actionable message)" is two outcomes; which applies depends on the free choice task 6 delegates (pinned vs derived), and in the derived branch `EXPECTED_HEAD` no longer exists as a mutation site. | plan gap | Resolve the delegation **before** the implementer prompt compiles, and write C6 as one branch with one exact outcome per row (charter rule 2). |
| L19 | **How a "new revision" is produced for C6.** The row needs an Alembic revision that does not exist. Generating one writes into `migrations/versions/`, which is outside §3's declared perimeter, and charter rule 7 forbids rewriting an applied migration. | plan gap | State the mechanism (a temporary revision file created and removed inside the test, applied only to a disposable database) and require it in the handoff's write perimeter. |
| L20 | **N3 has no criterion.** Task 6 carries two code items; C6 covers N4 only. `_normalised_endpoint` (`database_isolation.py:76-78`) maps the literal `"localhost"` and nothing else; the failure mode is total. | plan gap | Add a criterion row for the endpoint normalisation, or state explicitly that N3 is documentation-only this phase and why. |
| L21 | **The criterion module is itself parallel-hostile.** See F2. `test_database_isolation.py:34-46` and `:325, 332, 334, 363` assert global database membership; other workers and `test_phase6_legacy_migration.py` create and drop databases concurrently. | plan gap | Pre-authorise the worker-scoped repair (the intention's own scope-discipline clause covers it: an invalid fixture assumption whose repair is clear and inside the test perimeter), and make it a C3 row rather than a surprise. |
| L22 | **C3's "during the run" has no observer and races with worker lifetime.** Workers finish at different times and drop their databases in session teardown; "four exist simultaneously" is not a stable proposition, and no test inside the run is positioned to check it. | plan gap | Define the observer and the exact assertion (e.g. each worker asserts its own name and that no sibling name equals it), or invoke charter rule 1's environment-lifecycle exemption **in writing** with a named automated proxy. |
| L23 | **Who republishes the baseline.** §3's "Files expected to change" lists code only. Master plan §8 says phase 3 **replaces** its row, and §6.1's authoritative command changes meaning if a default `-n` lands. | plan gap | Name the document writes and their owner (implementer vs coordinator) in §3. |
| L24 | **Legacy reclamation becomes concurrent.** `BEYO_RECLAIM_LEGACY_TEST_DATABASES=1` is documented in master plan §6.1 as a full-suite invocation; under a parallel default, N workers sweep the same legacy names and `_drop_database_if_exists` (`database_isolation.py:463-465`) races existence-check against drop. | plan gap | Either exclude the sweep from non-controller workers or document the command as serial-only, in §6.1. |
| L25 | **Evidence identity and the L4 total.** Probe runs happen on a dirty tree (the harness), so each needs SHA + `git diff` digest per the charter. The amendments above (L2, L3, L19) add runs, so §6's "state your total L4 count as a number" must be restated after routing. | note | Coordinator restates the budget table with the final number when compiling the prompt. |

## 5. Findings — reality checks and criteria decidability

### F1 — the template hazard is three failure paths; task 3 and C2 name one *(blocking for C2's decidability)*

`_ensure_template` (`app/tests/database_isolation.py:314-343`) runs at the start of **every**
process. Under N simultaneous workers on one shared per-slot template
(`resolve_template_database_name` has no worker component, `:58-59`):

1. **Template absent** (first run after a slot is declared): every worker sees
   `not await self._database_exists(template_name)` (`:316`) and issues
   `CREATE DATABASE <template>` (`:317`). Losers get `DuplicateDatabaseError`, `start()` re-raises
   (`:180-185`), and the worker dies at startup.
2. **Template stale** (the first run after any Alembic revision — i.e. exactly C6's scenario):
   every worker takes the rebuild branch (`:340-343`), which calls `_drop_database_if_exists`
   → `pg_terminate_backend` on every session connected to the template (`:479-487`) → `DROP`.
   One worker therefore **kills another worker's inspection connection and drops the template
   out from under its in-flight `alembic upgrade`.**
3. **Template current** (the steady state): the only window is another worker's short-lived
   connection from `inspect()` (`:322`), `_has_legacy_baseline_source()` (`:336`) or
   `_set_marker()` (`:318`) overlapping a `CREATE DATABASE … TEMPLATE` (`:419-422`) — the
   `source database … is being accessed by other users` failure the plan names.

C2's named mutation ("remove whatever serialisation/retry task 3 adds ⇒ … at least one fails with
`source database … is being accessed by other users`") pins path 3's error string. Under paths 1
and 2 the mutation still bites, but with a **different** error, so a row written to that exact
string will either be un-runnable or will be quietly relaxed at implementation time. **C2 needs one
row per path, each with its own exact expected outcome** (charter rule 2). Note also that paths 2
and 3 are the same event C6 deliberately triggers — C6 and C2 intersect, and neither says so.

*(Not measured: this is a code reading. Reproducing it needs concurrent workers, which needs the
plugin this session may not install — that is itself the finding, per the prompt's §6. The
implementer can reproduce all three serially with in-process `DatabaseIsolation` probes and
`asyncio.gather`, per L11.)*

### F2 — the isolation criterion module will fail under `-n 2`, and it is our assumption that breaks

Four assertion sites read **server-global** database membership:

- `tests/integration/infrastructure/test_database_isolation.py:34-46` — module-scoped autouse
  fixture: the set of `beyo_test_*` databases before the module must equal the set after.
- `:325`, `:332`, `:334`, `:363` — `set(await probe.database_names())`, **unfiltered**, compared
  for exact equality against a snapshot.

Under `-n N`, sibling workers create `beyo_test_<slot>_gwK` at startup and drop them at teardown,
and `tests/integration/migrations/test_phase6_legacy_migration.py` creates and drops
`beyo_manager_phase6_<uuid>` databases in five tests (`:169, 207-209, 262, 314, 351`). With
`--dist loadfile` those two files land on **different workers and run concurrently**, so the
unfiltered snapshots at `:325/:363` see foreign databases appear and vanish mid-assertion.

**Prediction:** this is the first thing the `-n 2` run reddens, and it will present as exactly the
"new failure under parallelism" that C5 forbids absorbing into the baseline. It is not a suite
race — it is a test asserting a global fact that stops being global. The repair (scope both
snapshots to this process's own slot/worker names) is inside the test perimeter and is authorised
by the intention's scope-discipline clause. **Pre-authorise it in the plan** (L21); discovered at
2 a.m. inside a matrix run it will cost a round.

### F3 — "derive the constants from the repository" has a measured arithmetic trap

Task 6 asks for `EXPECTED_HEAD` and `EXPECTED_PUBLIC_TABLE_COUNT`
(`database_isolation.py:28-29`) to be derived rather than pinned. Measured today, this session,
read-only:

| source | value |
|---|---|
| `ScriptDirectory.from_config(Config("alembic.ini")).get_heads()` | `['c1d2e3f4a5b6']` — **exactly** `EXPECTED_HEAD` |
| `len(Base.metadata.tables)` | **104** |
| migrated template / `EXPECTED_PUBLIC_TABLE_COUNT` | **107** |
| development database `beyo_manager`, `information_schema.tables` where `table_schema='public'` | **109** |

The head derives cleanly. **The table count does not.** The 107 is
`104 metadata tables + alembic_version + 2 migration-owned journal tables`
(`ended_shift_collapse_journal`, `item_valuation_migration_journal` — deliberately absent from
ORM metadata by the convention documented at `migrations/env.py:20-31`). The dev database's 109
adds `pg_stat_statements` and `pg_stat_statements_info`, extension artifacts that exist only
there.

So both obvious derivations are wrong: metadata gives **104** (assertion fails on every template
build — the same wedge C6 exists to remove, reintroduced by its own repair), and the dev database
gives **109** *and* re-imports development-database contents into the test contract, which is the
class OD-1 removed. The count's true source is the migration set, not the models. **Amend task 6
to name the derivation, or replace the count with a content assertion** (head + required-table
set, which `_migrate_and_assert:385, 408-412` already carries).

### F4 — C6 cannot be written until task 6's delegation is resolved

C6's contract reads *"the run proceeds (or fails with an actionable message naming the fix)"* — a
disjunction of outcomes, which charter rule 2 names directly as the shape that hides mislabeling.
Which disjunct applies is decided by a **free choice the plan delegates** ("or state why pinning is
right"). In the derived branch, C6's named mutation site (`EXPECTED_HEAD` as a constant) no longer
exists. **Resolve the delegation upstream of the implementer prompt, then write C6 as one branch
with one exact expected outcome per row** (L18).

### F5 — C2, C3 and C4 assert state during a parallel run and name no observer

The prompt asked what observes them, and whether that observer can run without the plugin the
phase installs:

- **C2** — yes, serially: in-process `DatabaseIsolation` probes with concurrent `start()` calls
  reproduce all three F1 paths without xdist. Decidable once L10/L12 land.
- **C3** — no. "Four distinct databases exist **during** the run" and "server membership after ==
  before" are both statements about a whole session, from outside it. Neither is a test.
  Charter rule 1's environment-lifecycle exemption is available (it names "worker start"
  explicitly) but must be invoked **in writing** with a named automated proxy — the module fixture
  at `:34-46` is the natural proxy and is exactly the thing F2 says will break.
- **C4** — no, and it is worse than undecidable: it is already true by construction
  (`conftest.py:56`, `uuid4`), so the criterion as written can neither fail nor drive work (L14).

### F6 — C1's design cannot separate position sensitivity from nondeterminism

Inserting a no-op test at collection position *k* shifts absolute indices but **changes no test's
order relative to any other test**. So a differing failing-ID set under that perturbation is
evidence of sensitivity to absolute position/count *or* of plain run-to-run nondeterminism — and
phase 2's review r3 S5 established that this suite has at least one member whose outcome was a
function of object lifetime, not order. The plan's own standing rule 7 ("a single-occurrence
difference triggers re-measurement, never attribution") therefore binds **task 1's own output**,
which the plan does not say. Additionally, the observation task 1 is chasing came from eight
database- and Redis-touching criterion rows, not from no-ops: the probe as specified may be a
strictly weaker perturbation than the one that produced the evidence. **C1 is decidable only with
a stated stopping rule (L4), a noise-floor control (L2), a harness-only control (L3) and a stated
probe shape (L1).**

### F7 — reality checks

**Passed.** Every path in plan_3 §3 exists (`app/requirements.txt`, `app/requirements-dev.txt`,
`app/pytest.ini`, `app/tests/database_isolation.py`, `app/tests/conftest.py`,
`app/tests/integration/infrastructure/test_database_isolation.py`); the harness is correctly
marked new. Every §2 citation resolves and says what the plan claims: master plan §5 carries
exactly eight standing rules; §6.3 carries a five-condition invariant that matches the code
(`database_isolation.py:17-20, 90-107`); §6.4's Redis claims match `conftest.py:54-91` and
`settings.redis_key_prefix` default `"beyo_manager"` (`config.py:30`); §6.6 matches
`conftest.py:94-103`; §8's provenance of 21-not-26 is present; plan_2 §5 C2 carries the scope
correction the plan cites; the r3 handoff carries S5, N3, N4 and lessons 2–4. Machine is 14 cores
(`hw.ncpu` = `hw.physicalcpu` = 14). Server is `localhost:5433`, databases present:
`beyo_manager`, `beyo_test_main_template`, `housing_parser_plan1_20260807`, `postgres` — **no
worker-database residue**, consistent with §8.

**Failed (2).**
1. Master plan §6.1: *"exactly one plugin (`pytest-asyncio`)"* — `pytest -VV` registers
   **`pytest-asyncio-0.25.3` and `anyio-4.13.0`** (L9).
2. `plans/plan_2.md:4` frontmatter still reads `state: IMPLEMENTED` with no `gate_stamp:` line,
   while master plan §3, plan_2 §7 and commit `e57ffaf` all record APPROVED (§3 of this handoff).

### F8 — the standing question: is phase 3 two phases wearing one number?

**The boundary holds, but only if card 1 is answered before the session starts.** The plan is
correct that repair belongs elsewhere and correct to route the call to the owner. What it does not
do is state the decision *rule*: task 1 "runs first and nothing else starts until it has an
answer", but no answer is mapped to an action. An empty set means proceed; a non-empty set means
the implementer is mid-session, holding a result, with no authority to continue and no authority
to stop. Answering card 1 up front converts a phase-splitting question into a branch the
implementer can execute. With that answered, phase 3 is one phase.

## 6. Write perimeter — one file, this handoff

- **Documents written:** exactly one —
  `handoffs/reviewer/2026-08-21_phase3_projection_r0_handoff.md` (this file). No plan, intention,
  master plan, prompt or Review-log line was edited; the Review-log line is the coordinator's.
- **Code written:** none. `pytest-xdist` was **not** installed; `import xdist` still raises
  `ModuleNotFoundError`.
- **Tool-recorded state:** none. `archgraph_status` was read; no node, edge or review item was
  created, changed or promoted.
- **Databases touched:** none. Four read-only connections were opened during reality checks —
  `beyo_manager` (`information_schema.tables`), `postgres` (`pg_database`, `SHOW max_connections`,
  `SHOW server_version`, `pg_stat_activity` count) — all `SELECT`/`SHOW` only, no DDL, no writes,
  every connection closed. No database was created, dropped or modified; server membership is
  unchanged (`beyo_manager`, `beyo_test_main_template`, `housing_parser_plan1_20260807`,
  `postgres`).
- **Test runs:** none. **L4 count: 0** (budget was 0). Two offline Python probes (Alembic
  `ScriptDirectory`, `Base.metadata`) and `pytest -VV` / `pip show`, all L1 and non-mutating. The
  published `21 / 2561 / 1` at `11b4d02` is **cited, not re-measured**.
- **Tree identity:** `e95d41a`, `git status --porcelain` empty at session entry and immediately
  before this file was written — this handoff is the only diff.

**No skeleton appendix is attached.** The derivation was performed and discarded, per doctrine;
what survived it is the ledger above. The implementer receives no sketch from this session.
