---
plan: test_isolation_and_xdist/plans/plan_1.md
role: review
round: 3
verdict: CHANGES_REQUESTED
date: 2026-08-21
actor: claude-opus-5
---

# Phase 1 review r3 handoff — per-worker PostgreSQL isolation

**Verdict: CHANGES_REQUESTED.** The isolation machinery itself is sound and I confirm every
piece of settled ground the prompt listed. What blocks is not the code: it is that the number
OD-1 was decided on — *"nine tests across four files, not 100+"* — is an artifact of pytest's
default collection order. Under one deterministic reordering, **118 further tests fail**, all
with the same missing-reference-data signature. The intention's own escape threshold ("100+")
is crossed, and the handoff's deliverable 12 ("Remaining non-parallel-safe test", singular)
understates the class by two orders of magnitude. Phase 2 is xdist, which reorders by
construction.

Two blocking findings, two should-fix, eight notes. No production behaviour is wrong; nothing
here risks the developer's database.

---

## ⚠ OWNER DECISIONS REQUIRED (2)

### Card 1 — the reference-data repair is ~127 tests, not nine. Fix now, or take it into phase 2?

**Question.** Do the ~118 newly-identified order-dependent tests get reference fixtures inside
phase 1, get deferred to phase 2 as its first work item, or get accepted as-is?

**Story.** Today your suite is green at 22 known failures because the second file pytest
collects, `test_clock_actions_integration.py`, happens to commit the four worker/manager role
rows into the fresh database before anything else needs them. One hundred and eighteen tests
downstream quietly borrow those rows. The moment xdist splits the suite across four workers,
most workers never run that file at all — so those tests land on an empty catalog and go red in
clumps that move every run. You would spend a week reading it as "xdist made the suite flaky",
because that is exactly what it will look like.

**Branches.**
- *Fix in phase 1* — the phase grows by roughly 11 files of fixture work, but phase 2 starts on
  a suite that is genuinely order-independent and its first parallel run means something.
- *Defer to phase 2* — phase 1 closes now with the number corrected in writing; phase 2 opens
  with a known ~118-test repair ahead of installing xdist, and its first baseline is the honest one.
- *Accept as-is* — every future baseline is valid only for the exact default collection order,
  and the first reorder invalidates it silently.

**Recommendation.** Defer to phase 2, first item, before xdist is installed — phase 2 already
reopens this code for the slot discriminator, and the repair and the reorder belong in the same
round where they can be measured against each other.

**On silence.** The gate holds at CHANGES_REQUESTED; nothing is guessed.

**Trace.** intention §1 (the "100+" clause), intention §4 OD-1, plan_1 C7, fix-r2 handoff
deliverables 11/12/15.

### Card 2 — two retirement tests now assert their own fixture. Repair or retire them?

**Question.** For the two tests in `test_system_transition_reasons_retirement.py` that can no
longer observe what they were written to guard, do we rewrite them against production code, or
delete them?

**Story.** One of them says in its own docstring that it exists because `list_pause_reasons`
filters `is_deleted`, so a soft-delete would silently strip a reason from the worker's pause
sheet. I deleted that filter from the production query and ran all 2 561 tests: every single one
stayed green, byte-identically. A worker's pause sheet could start offering retired reasons
nobody can resolve, and nothing in this repository would say a word. The other test asserts
"7 preserved historical references" against seven rows the fixture inserted four lines earlier.

**Branches.**
- *Rewrite* — point them at production behaviour (soft-delete a fixture row, assert it vanishes
  from the picker); costs a small edit and restores real coverage.
- *Delete* — honest about the fact that a clean-schema suite structurally cannot observe a
  property of the developer's data; loses the `is_deleted` filter coverage entirely unless a
  replacement is written.

**Recommendation.** Rewrite. The `is_deleted` filter is live production behaviour on a
worker-facing screen and is currently unguarded; the rewrite is a few lines.

**On silence.** The gate holds; the tests stay as they are and the coverage stays absent.

**Trace.** plan_1 §5A ("a fixture whose expected value is the same under the defect proves
nothing"), charter rule 2 companion, findings S1/S2.

---

## Findings

### B1 (blocking) — "nine tests need reference data" is an artifact of collection order; the measured figure is ≥127

**What is wrong.** OD-1 was ratified on the finding that the schema-only template breaks
*nine* tests, which resolved the intention's escape clause — *"Do not spend the project manually
repairing 100+ individual tests unless investigation proves that is necessary"* (intention §1) —
in favour of fixtures. Nine is the number that fail **in pytest's default collection order
only**. `tests/connecteam/test_clock_actions_integration.py` is the **second file collected**;
at line 166 it creates `Role(name=RoleNameEnum.WORKER)` and at line 198 it commits. Every later
test that resolves a role or catalog row by name inherits it from that commit.

**Measurement (L4, coupling discovery — charter test-evidence (d)).** Identical tree, identical
command, one deterministic reordering of `pytest_collection_modifyitems`:

| condition | result |
|---|---|
| default order (control, this machine) | `22 failed / 2539 passed / 1 deselected in 107.29 s` |
| reversed collection order | `139 failed / 2422 passed / 1 deselected in 101.13 s` |

ID delta reversed-vs-control: **added = 118, removed = 1**. Reproduced twice with identical
counts. The 118 fall in 11 files:

```
41  services/commands/users/test_worker_shift_commands.py
25  services/queries/users/test_list_users_floor_identification.py
11  services/queries/users/test_get_current_worker_shift_state.py
11  services/commands/users/test_update_user_admin_clock_in_code.py
 8  services/commands/users/test_worker_shift_realtime_events.py
 6  services/queries/worker_stats/test_transition_reason_read_tolerance.py
 5  services/queries/worker_stats/test_get_worker_linear_timeline_breakdown.py
 4  services/queries/worker_stats/test_list_workers_linear_timeline.py
 4  scripts/backfill/test_curate_shifts_from_connecteam.py
 2  scripts/backfill/test_backfill_worker_shift_state_records.py
 1  services/commands/cases/test_case_created_step_pause.py
```

Every sampled failure is the same signature: `sqlalchemy.exc.NoResultFound: No row was found
when one was required` on a role or pause-reason lookup. `test_worker_shift_commands.py` run
alone gives `41 failed / 1 passed` — the one pass is the test fix r2 gave a fixture.

**This is caused by phase 1, and it is not a bug in phase 1's code.** The configured database
holds 4 `roles` and 8 `pause_reasons` rows (verified by direct query), so before this phase every
test found a populated catalog regardless of order. Phase 1 correctly removed that dev-data
coupling for four tests and converted it into **test-order coupling** for ~118 more. The
project's stated purpose was to remove the first kind; the second kind is strictly worse for
phase 2, because xdist's default `--dist load` distributes individual tests across workers, so
most workers never run the committing file at all.

**Related correction to OD-1's text.** OD-1 ratifies a template carrying "migration-owned seed
rows only". There are none: `49bd666da846_seed_default_pause_reasons.py::upgrade` opens with
`SELECT client_id FROM workspaces LIMIT 1` and `return`s when it is `None`, which is always true
on a fresh database. Verified — the built template holds `roles=0, pause_reasons=0,
workspaces=0, users=0`.

**Violated authority.** `planning/intention.md` §1 (the 100+ clause) and §4 OD-1; fix-r2 handoff
deliverables 11, 12 and 15.

**Suggested correction.** No perimeter code changes. Correct the published characterisation:
deliverable 12 is a class of ≥118, not one named test; record the coupling source and the
reorder measurement; route the repair per owner card 1.

### B2 (blocking) — an interrupted run leaves a database that can never be reabsorbed, and every later run aborts

**What is wrong.** `DatabaseIsolation.start()` (`app/tests/database_isolation.py:136-137`)
creates the worker database and marks it in **two separate steps**. A database created with
`CREATE DATABASE … TEMPLATE beyo_test_template` inherits the template's marker row, whose
`database_name` column reads `beyo_test_template`. `_marker_present_on_connection`
(`:236-249`) requires `marker_key = $1 AND database_name = $2`, so between the two steps the
worker database reports **`marker_present = False`** — and `assert_disposable_database` refuses
to drop it. Forever.

Three compounding factors:
1. `start()`'s cleanup is `except Exception` (`:139`), which does **not** catch
   `KeyboardInterrupt` — the ordinary way a developer stops a slow suite.
2. Even when it does run, the cleanup is `best_effort=True` (`:140`), so
   `_drop_database_if_exists` swallows the guard's refusal (`:420-422`) and the database is
   left behind silently.
3. C8 (`test_fixed_name_reabsorbs_an_interrupted_worker`) only ever exercises the easy half: it
   calls `probe._set_marker(probe.worker_database_name)` at line 113 before asserting
   reabsorption, so it tests a leftover marked with its *own* name and never the window that
   actually wedges.

**Measurement (L1, varied mutant shape).** Simulated the interruption at exactly that point,
then started pytest the way a developer would:

```
left behind: beyo_test_main   marker_present = False
$ PYTHONPATH=. pytest tests/unit/test_items_router.py
E  tests.database_isolation.UnsafeDatabaseError: Database lacks the disposable marker: 'beyo_test_main'
3 errors in 0.72s
```

Not one test can run until a human drops the database by hand; after a manual `DROP DATABASE`
the suite recovers immediately. Also measured, on a disposable `beyo_test_gw777`: an empty
marker table is correctly refused (good), a marker row naming a different database is refused
(good), the best-effort path leaves the database in place (`still exists = True`), and a fresh
`DatabaseIsolation.start()` fails with the same error.

**Violated authority.** `plans/plan_1.md` C8 — "an interrupted run is absorbed, not
accumulated"; charter rule 11 (a safety test that survives the defect it exists to prevent).

**Suggested correction.** Make creation-and-marking atomic from the guard's point of view —
either set the marker in the same step that creates the database, or let the drop guard accept a
marker row whose `marker_key` matches regardless of `database_name` (the row can only be there
because this code put it there). Then extend C8 with a row that leaves a database behind
**without** re-marking it, which is the mutation that must turn C8 red. Under xdist this
multiplies by worker count.

### S1 (should-fix) — `test_retirement_left_the_guarded_populations_alone` now asserts only its own fixture

**What is wrong.** The test body
(`app/tests/integration/services/commands/test_system_transition_reasons_retirement.py:161-186`)
is two raw-SQL `COUNT`s and no call into `beyo_manager` at all. `transition_reason_reference_data`
inserts exactly seven `pause_case_created` step-state records (`phase1_reference_data.py:100`,
`for index in range(7)`) and exactly one `pause_ended_shift` record; the test then asserts
`anchor_refs == 7` and `ended_shift_refs > 0`. The fixture is the sole determinant. The property
it was written for — that the phase-4 retirement migration left the real database's historical
references intact — operates on rows that exist *before* the migration runs, and the fixture
inserts *after* it, so no change to `b4e7a1c93f28` can move either count.

**Measurement (L1).** Changed `range(7)` → `range(8)` in the fixture:
`AssertionError: expected the 7 preserved pause_case_created references, found 8`. Reverted;
`shasum` back to `2846232733f8…`.

**Violated authority.** Charter rule 2 companion — "each row's fixture makes its own predicate
the ONLY reason the expected outcome holds"; `plans/plan_1.md` §5A ("a fixture whose expected
value is the same under the defect proves nothing").

**Suggested correction.** See owner card 2.

### S2 (should-fix) — the `is_deleted` filter on the worker's pause sheet is now unguarded by the entire suite

**What is wrong.** `test_pause_ended_shift_is_still_selectable_through_the_endpoint` documents
itself as guarding `list_pause_reasons`' `is_deleted` filter. Its second assertion
(`"pause_other_task_priority" not in slugs`) was what bit: the configured database holds that
slug with `is_deleted = true` (verified by direct query), so removing the filter used to surface
it. `transition_reason_reference_data` never creates that slug and creates nothing soft-deleted,
so the assertion is now true by construction.

**Measurement (L4 — absence claim, charter test-evidence (d)).** Deleted
`PauseReason.is_deleted.is_(False)` from
`beyo_manager/services/queries/pause_reasons/list_pause_reasons.py:17-20` and ran the full suite:

```
22 failed, 2539 passed, 1 deselected in 109.55s
added = ∅   removed = ∅
```

Byte-identical to the baseline. **No test anywhere in the repository guards the filter.**
Reverted; `shasum` back to `45ddd137416a…`, `git status --porcelain` empty.

**Violated authority.** Charter rule 2 companion; the test's own docstring at
`test_system_transition_reasons_retirement.py:133-136`.

**Suggested correction.** See owner card 2.

---

## Notes

- **N1 — the guard's name pattern accepts Unicode digits.** `TEST_DATABASE_PATTERN`
  (`database_isolation.py:15`) and `resolve_worker_database_name` (`:34`) both use `\d`, which is
  Unicode-aware in Python. `beyo_test_gw٠` (Arabic-Indic), `beyo_test_gw๐` (Thai) and
  `beyo_test_gw０` (fullwidth) all pass `assert_disposable_database`. **No unsafe `DROP` results**
  — `_quoted_identifier` (`:73`) is ASCII-only and refuses all three, so defence-in-depth holds
  and the run aborts. Recommend `[0-9]+` (or the `(?a)` flag) in both regexes before phase 2
  widens the pattern for the slot discriminator.
- **N2 — `^…$` is safe only because every caller uses `fullmatch`.** Measured: `.match()` accepts
  `'beyo_test_main\n'` while `.fullmatch()` rejects it. The `$` makes the pattern *look*
  anchored, so a future edit to `.match()` is a natural-looking change that reopens it.
  Recommend `\Z`.
- **N3 — "not the configured database" is a name check, not an identity check.** The guard
  compares `configured.database == database_name` only; host and port are never considered.
  Measured: dropping `beyo_test_main` is blessed while the configured URL is
  `…@10.0.0.5:5432/beyo_manager`. Not exploitable today, because every connection is built from
  the configured URL's host — but it is precisely the axis the recorded concurrent-checkout
  hazard (intention §5, commit `ec9cbb3`) sits on, and the marker is the only thing separating
  two checkouts' databases. Already routed to phase 2; recorded here only to confirm the reading.
- **N4 — Redis is not isolated, and its cleanup targets a namespace production code never
  writes.** `isolated_redis_prefix` (`conftest.py:50-61`) mutates `os.environ["REDIS_KEY_PREFIX"]`,
  but `settings.redis_key_prefix` was parsed at import and does not re-read the environment.
  Measured: `settings.redis_key_prefix` stays `'beyo_manager'` after the mutation. Production key
  builders (`services/infra/redis/keys.py:6`, `routers/utils/rate_limit.py:24,34`,
  `services/infra/auth.py:7`, `services/infra/sleep/activity_tracker.py:15`) all read that
  attribute, so they write to the shared unprefixed namespace, while `redis_client`'s teardown
  deletes `{prefix}:test:{hex}:*`. Contrast the database seam, which correctly assigns
  `settings.database_url` on the object. Phase 2 must treat Redis as shared across workers.
  Search terms: `redis_key_prefix`, `redis_url`, `REDIS_KEY_PREFIX`, `scan_iter`.
- **N5 — C6's in-suite proxy covers only the prefix of the suite that runs before it.**
  `test_dev_database_counts_are_untouched` compares `configured_row_counts_before_run` (captured
  at session start) against counts taken *at the moment the test runs*. Anything a
  later-ordered test commits to the configured database is invisible to it. Under xdist each
  worker's window differs, and concurrent workers read the dev counts at different instants. The
  F3 fix is right; the coverage is positional.
- **N6 — P2 resolved: C3's setup abort is the correct outcome, and its criterion row is not
  dead.** The stated mutation aborts in `_migrate_and_assert` before collection, which is the
  stronger result — no test can report a false green against a bad template. The `∅ / ∅` delta
  was missing the evidence that the *test* can fail, so I supplied it: with the
  `EXPECTED_PUBLIC_TABLE_COUNT` check removed from `_migrate_and_assert` **and** `alembic
  upgrade` replaced by `alembic stamp`, and the template dropped so it rebuilds,
  `test_template_has_migrated_head_and_full_schema` reddens `assert 1 == 107`, taking C4's
  `test_worker_is_a_faithful_template_copy` with it (`2 failed, 13 passed`). Recommend recording
  that two-step mutation as C3's evidence row.
- **N7 — the published pass count is confirmed wrong.** Independently measured `2539`, not the
  handoff's `2540`. The 22-ID set is byte-identical to the published set, `comm`-empty both
  directions.
- **N8 (passing glance) — `test_no_row_is_system_managed_any_more` is now vacuous.** It counts
  `pause_reasons WHERE is_system_managed = true` on a database where migrations seed nothing and
  `_pause_reason` sets `is_system_managed=False` explicitly. It is not one of the nine and was
  not touched by this phase; it is green by construction.

---

## Verified correct

- **Perimeter.** Exactly the eight files of `697b633`, all under `app/tests/`, no production
  code. `git diff 697b633 HEAD -- app/` is empty; `git status --porcelain` empty at entry and exit.
- **Baseline, re-derived not cited.** `22 failed / 2539 passed / 1 deselected in 107.29 s`;
  failing-ID set `comm`-diffed against the handoff's published 22 — **empty in both directions**.
- **The fail-closed guard holds under attack.** Refused: `beyo_test_GW0`, `BEYO_TEST_MAIN`,
  `'beyo_test_main\n'`, `'beyo_test_main\nDROP DATABASE beyo_manager'`, `'beyo_test_main '`,
  `beyo_test_maın` (dotless i), the configured database, a `None` URL, a malformed URL, a
  database whose marker table exists but is empty, and a database whose marker row names a
  different database. `resolve_worker_database_name` refuses `GW0`, `'gw0 '`, `'gw1\n'`.
- **Fixture narrowness.** 142 lines, four fixtures, explicit `phase1-*` rows, no live-data copy.
  The backfill, kiosk and worker-shift fixtures supply **preconditions only** — a `Role` row for
  the FK, a `PauseReason` resolvable by slug so a step can be paused — while the assertions
  remain about shift reconstruction, backfill and kiosk flows. Those three groups pass P1. Only
  the transition-reason group fails it (S1/S2). The fixtures `flush()` inside the test's
  transaction rather than committing, so they leave no residue of their own.
- **C3/C4/C5 bite.** Demonstrated above (N6) and by `test_application_database_seam_points_at_worker`
  asserting both `settings.database_url` and `database_module._engine.url.database`.
- **Residue.** After three full suite runs, two template rebuilds and every probe: the server
  holds `beyo_manager`, `beyo_test_template`, `housing_parser_plan1_20260807`, `postgres`.
  Dev counts `11253/9809/2445/1955` — unchanged. `SELECT count(*) FROM workspaces WHERE name LIKE
  'phase1-%'` = **0**.
- **Scope fence.** `pytest-xdist` is not installed (`importlib.util.find_spec('xdist') is None`);
  no `-n` anywhere outside documentation and one docstring.

---

## Mutation-probe declaration

Every probe applied and reverted; every checksum verified byte-identical against its pre-probe
value; `git status --porcelain` empty at close.

| File | Probe | Pre/post `sha256` |
|---|---|---|
| `beyo_manager/services/queries/pause_reasons/list_pause_reasons.py` | removed `PauseReason.is_deleted.is_(False)` (S2) | `45ddd137416aa3f25a9c17216e78f1e633bad74b5f0ac235ad2485956991286b` |
| `app/tests/fixtures/phase1_reference_data.py` | `range(7)` → `range(8)` (S1) | `2846232733f8068ce3f9d28e16bce6da49ed6ba641c00f1171ef8ec7fde57013` |
| `app/tests/database_isolation.py` | `alembic stamp` + DDL count assertion removed (N6) | `158fd49311f5d268c52d75fcbece07c3e4a544dcc6457f90dc9e9518a727e1fb` |

Files created **outside** the repository (never in perimeter):
`scratchpad/reverse_order_probe.py`, `scratchpad/guard_probe.py`.

Databases created and removed, verified absent:

| Database | Purpose | Removal |
|---|---|---|
| `beyo_test_gw777` | P3/P4 guard attacks (empty marker, foreign marker row, wedge) | dropped in the probe's `finally`; verified absent |
| `beyo_test_main` | left deliberately unmarked to reproduce the B2 wedge on the real pytest path | dropped manually; suite verified to start again |
| `beyo_test_template` | dropped twice to force rebuilds (N6 mutant, then clean) | rebuilt clean; `15 passed` on the criterion file |

Rows written to the configured database: **none**. All dev-database access was read-only
`SELECT`; counts and `phase1-%` check confirm it.

---

## Evidence ledger

| Hypothesis | Scope · command | Tree identity | Result · ID delta |
|---|---|---|---|
| Baseline reproduces at my tree | L4 · `PYTHONPATH=. pytest -q --tb=no -m 'not e2e'` | `87a4b7a`, `app/` == `697b633`, status empty | `22 / 2539 / 1` in 107.29 s; vs published 22: `added ∅ / removed ∅` |
| The failure set is order-independent | L4 coupling discovery · same command + `-p reverse_order_probe` | same | **refuted** — `139 / 2422 / 1`; `added = 118 / removed = 1` |
| The removed ID is order-dependent (P6) | same run | same | confirmed — `test_adding_a_batch_of_steps_reopens_ready_task` is the single member of the 22 that flips green |
| One file alone shows the same class | L1 · that file only | same | `41 failed / 1 passed`; the pass is the fixtured test |
| The coupling source is an early committing test | inspection · `test_clock_actions_integration.py:166,198` + `--collect-only` head | same | confirmed — 2nd file collected, creates and commits `Role(WORKER)` |
| The catalog was previously supplied by dev data | L1 read-only query | same | dev holds `roles=4`, `pause_reasons=8`; template holds `roles=0, pause_reasons=0` |
| Any test guards `list_pause_reasons`' `is_deleted` filter | L4 absence claim · full suite under the mutant | mutant tree; reverted, checksum verified | **refuted** — `22 / 2539 / 1`, `added ∅ / removed ∅` |
| The 7-reference assertion is fixture-determined | L1 · retirement file under `range(8)` | mutant tree; reverted | confirmed — `1 failed, 4 passed`, "expected 7 … found 8" |
| C3's criterion test can itself redden | L1 · criterion file, lifecycle assertion removed + `alembic stamp`, template rebuilt | mutant tree; reverted, template rebuilt clean | confirmed — `2 failed, 13 passed`, `assert 1 == 107` |
| The guard resists name/marker/URL attacks | L1 · 9 pattern rows, 8 worker-id rows, 2 host rows, 3 live marker states | `87a4b7a` clean | 6/9 refused; 3 Unicode-digit rows accepted by the pattern and refused by `_quoted_identifier` |
| An interrupted run is reabsorbed (C8) | L1 varied mutant · interrupt between CREATE and `_set_marker`, then real pytest | `87a4b7a` clean | **refuted** — `UnsafeDatabaseError`, 3 errors, 0 tests run; manual `DROP` required |
| Redis is isolated per run | L1 · import `settings`, mutate env, re-read | `87a4b7a` clean | **refuted** — `settings.redis_key_prefix` stays `'beyo_manager'` |
| Residue is zero | L1 read-only · `pg_database`, dev counts, `phase1-%` | after all runs and probes | `beyo_test_*` = `{beyo_test_template}`; `11253/9809/2445/1955`; `phase1-%` = 0 |

---

## Lessons for the plans

1. **A "how many tests depend on X" count is only valid for the order it was measured in.**
   The investigation behind OD-1 measured nine on a suite whose second file commits the catalog.
   Any future criterion of the form "N tests need Y" should state the collection order it was
   measured under, or be measured under at least two orders.
2. **C7's shape ("the failure-ID set is unchanged") passes while the suite becomes far more
   fragile.** An equality claim over one ordering cannot see coupling. The phase-2 plan should
   carry a criterion over a *reordered* run, not only the default one — it costs one extra L4
   and it is the single cheapest instrument for the class phase 2 is about to hit.
3. **Two-step create-then-mark is a fail-closed construction with a wedge in the middle.** Any
   criterion asserting "an interrupted run is absorbed" must name the interruption *point*, not
   just the outcome — C8 named the outcome and tested the point that cannot fail.
4. **A criterion whose named mutation aborts setup needs a second, deeper mutation to show the
   test row is load-bearing.** C3's `∅ / ∅` was honest but unfalsifiable as recorded; the
   two-step mutation (remove the earlier guard, then apply the named one) is the general recipe
   and belongs in the plan template.
5. **An override applied to `os.environ` is not an override.** The database seam assigns
   `settings.database_url`; the Redis seam mutates the environment and silently does nothing.
   Plans that specify a configuration override should name the object and attribute, not the
   variable.

---

## Carry-forward dispositions

Not applicable — the verdict is CHANGES_REQUESTED, so nothing is carried past an approval gate.
On the next round, N1–N5 and N8 are the candidates for a dispositions table; N6 and N7 are
discharged by this handoff.

## Human-authorization backlog

- Three Architecture Graph items remain `ai_inferred` and pending human review
  (`infrastructure-test-database-isolation`, `test-database-isolation-contract`, and their
  `configured_by` edge). Graph revision unchanged at
  `4caa1afe361b7906bd6aed854d0ded5897a6927d3e5e9f13f29e81e7177508fc`. No graph mutation was made
  this round; agents never promote.

## Write perimeter for this session

- documents: this handoff; the `plans/plan_1.md` Review-log entry and its tracker `state` line.
- code: none (all probes reverted, checksums verified).
- tool-recorded state: no Architecture Graph delta.
