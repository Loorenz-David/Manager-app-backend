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
| 3 | Parallelism: install xdist, serial / `-n 2` / `-n 4` / higher matrix, conservative default, **new authoritative baseline re-enumerated under the new runner** | **PROJECTED_PENDING** | 2026-08-21 | coordinator | **Gated**: see §7's perturbation gate. Does not begin its worker matrix until collection-perturbation sensitivity is characterised on a *serial* runner. Carries six items from phase 2's closeout table. `plans/plan_3.md` authored 2026-08-21; projection r0 prompt compiled and awaiting a session. |
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
8. **The closing stamp is defined by the tree, not by the count.** Two rounds read a numeric L4
   budget as forbidding a re-stamp after they had invalidated their own. *(A charter amendment
   is proposed to the owner; until it lands, prompts state it explicitly.)*

## 6. Environment

**This section is the citable authority. Prompts point here; they do not restate it.**

### 6.1 Commands

Run from `backend/app/`. `PYTHONPATH=.` is required.

| purpose | command |
|---|---|
| full suite (authoritative) | `PYTHONPATH=. pytest -m 'not e2e'` |
| full suite, reversed collection | `BEYO_TEST_COLLECTION_ORDER=reverse PYTHONPATH=. pytest -m 'not e2e'` |
| collection size only | `PYTHONPATH=. pytest -m 'not e2e' --collect-only -q` |
| isolation criterion module | `PYTHONPATH=. pytest -q tests/integration/infrastructure/test_database_isolation.py` |
| one-time legacy reclamation | `BEYO_RECLAIM_LEGACY_TEST_DATABASES=1 PYTHONPATH=. pytest -m 'not e2e'` |

Machine: **14 cores** (`hw.ncpu` = `hw.physicalcpu` = 14). Runner: pytest 8.3.5,
`asyncio_mode = auto`, exactly one plugin (`pytest-asyncio`). **No randomizer is installed** — a
`-p no:randomly` in any inherited command is disabling a plugin that does not exist.
`pytest-xdist` is **not installed** as of phase 2's approval; installing it is phase 3's first
code change.

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

### 6.4 Redis

Not a hard dependency, deliberately. `isolated_redis_prefix` is session-scoped **autouse** and
overrides `settings.redis_key_prefix` per process — the setting, not `os.environ`, because every
production key builder (`services/infra/redis/keys.py:6`, `routers/utils/rate_limit.py:24,34`,
`services/infra/auth.py:7`, `services/infra/sleep/activity_tracker.py:15`,
`logout_user.py:53`) reads the attribute at call time. Teardown deletes the process prefix
**best-effort**: an unreachable Redis produces warnings, not errors, so the failing-ID set is not
a function of Redis availability.

### 6.5 Schema constants — and the time bomb

`database_isolation.py` hardcodes `EXPECTED_HEAD = "c1d2e3f4a5b6"` and
`EXPECTED_PUBLIC_TABLE_COUNT = 107`. **The next Alembic revision makes `_ensure_template` rebuild
and `_migrate_and_assert` then raise `RuntimeError`, wedging the suite until a human edits the
file.** Known, carried to phase 3, deliberately not fixed inside phase 2's fence
(review r3 N4).

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

| Phase | Approved | Tree | Suite | Failing-ID set |
|---|---|---|---|---|
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
