# Plan 2 — order-independence and per-checkout isolation, still serial

```
state: PROMPT_READY — 2026-08-21 (projection r0 consumed, 16 rows routed; implement r1 authored)
phase: 2
date: 2026-08-21
actor: coordinator (authoring + projection fold)
depends_on: plan_1 APPROVED (2026-08-21, `5ecfe90`). Gates plan 3 (xdist) and, through it,
            live_clock_for_working_time_economics phase 4.
scope_fence: pytest-xdist is NOT installed in this phase either. Parallelism is plan 3,
             ratified by the owner as OD-5 (intention §3 amended, §4 OD-5).
projection_gate: SATISFIED. Round 0 returned AMENDMENTS_REQUIRED with 15 rows; a 16th was
                 lifted from its "reality checks that passed". All routed — see §7.
```

## 0. Why this is a phase of its own (OD-5, owner-ratified 2026-08-21)

The intention's §3 phasing named two phases: isolation, then parallelism. Phase 1 shipped
isolation and, in doing so, **converted dev-data coupling into test-order coupling for ~118
tests** (OD-3). Three carry-forwards then landed on phase 2 alongside xdist: the ~118-test
repair, the slot discriminator for concurrent checkouts (intention §5), and B2's second shape.

Those three are the *precondition* for a meaningful parallel measurement, and they end at a
clean, falsifiable boundary: **the suite's failure-ID set is invariant under collection
order, proven serially.** Until that holds, the first `-n 4` run measures a pre-existing
order dependency surfacing under a new distribution — which is exactly what OD-3's binding
sequence forbids ("the repair lands **before** `pytest-xdist` is installed").

Splitting also contains defects the way every gate in this organisation has: a
CHANGES_REQUESTED on ~11 files of test repair would block an xdist measurement that was
never the problem. Plan 3 then becomes what the intention actually asks for — a measurement
phase (deliverables 6–14), cheap and mostly evidence.

**What is unchanged:** OD-3's binding sequence, the intention's isolation-before-parallelism
constraint, and the requirement that the baseline be re-enumerated under the new runner
before any mutation result is trusted on it. Only the plan boundary moves. `live_clock`
phase 4's ⛔ gate is satisfied when **plan 3** closes, not this one.

## 1. Goal

Three things become true, serially, with no plugin installed:

1. **No test's outcome depends on another test having run.** Every file in OD-3's class
   passes when run alone on a fresh worker database, and passes when preceded by the file
   that currently poisons it, because each helper creates the rows it needs and adopts only
   the ones the database allows exactly one of (OD-6).
2. **Two checkouts can run pytest at the same time without destroying each other's
   databases**, via a slot discriminator ahead of the worker id — with the safety invariant
   still failing closed under the widened name pattern.
3. **The isolation seam covers every shared resource the suite touches, not only
   PostgreSQL** — Redis included, per the intention's own correctness-gate list.

**NOT in this phase:** no `pytest-xdist`, no `-n` flag, no parallel run, no worker-count
matrix, no new authoritative baseline under a changed runner (plan 3 owns all of these). No
production domain change. No fixture-scope optimisation (plan 1 C7's fence still stands).

## 2. Read first

1. `planning/intention.md` — §1 (owner's intention verbatim), §2.2 (measured facts you need
   not re-derive), §2.3 (the design and the safety invariant), **§5 (the concurrent-checkout
   hazard — this phase's task 2 in full)**, **OD-3** (the ~118-test class and its binding
   sequence), **OD-6 (the repair contract — read this before task 1)**, OD-4 and OD-5.
2. `plans/plan_1.md` — §5A traps (all four still apply), and the Review log's fix-r4
   consumption entry, which enumerates this phase's four carry-forwards.
3. `archive/plan_1/2026-08-21_phase1_review_r3_handoff.md` — the enumeration of the 118 by
   file (§B1), the Redis mechanism (N4), and notes N1/N2/N3/N5/N8. **Cite this; do not
   re-derive it.**
4. `handoffs/reviewer/2026-08-21_phase2_projection_r0_handoff.md` — §4's findings carry the
   measurements behind most of this plan's amendments, with exact lines. **Its Appendix A is
   non-authoritative and must not be read as guidance**; where it disagrees with this plan,
   this plan wins.
5. Source: `app/tests/database_isolation.py`, `app/tests/conftest.py`,
   `app/tests/fixtures/phase1_reference_data.py`, `app/beyo_manager/config.py`,
   `app/beyo_manager/services/infra/redis/keys.py`.

## 3. Files expected to change

- **The eleven files of OD-3's class**, enumerated so the perimeter is a list and not a
  description (counts are the reversed-order failures measured at `87a4b7a`; the projection
  confirmed none of these files changed between `87a4b7a` and HEAD, and reproduced four of
  the counts exactly at HEAD):

  | failures | file (under `app/tests/`) |
  |---:|---|
  | 41 | `integration/services/commands/users/test_worker_shift_commands.py` |
  | 25 | `integration/services/queries/users/test_list_users_floor_identification.py` |
  | 11 | `integration/services/queries/users/test_get_current_worker_shift_state.py` |
  | 11 | `integration/services/commands/users/test_update_user_admin_clock_in_code.py` |
  | 8 | `integration/services/commands/users/test_worker_shift_realtime_events.py` |
  | 6 | `integration/services/queries/worker_stats/test_transition_reason_read_tolerance.py` |
  | 5 | `integration/services/queries/worker_stats/test_get_worker_linear_timeline_breakdown.py` |
  | 4 | `integration/services/queries/worker_stats/test_list_workers_linear_timeline.py` |
  | 4 | `integration/scripts/backfill/test_curate_shifts_from_connecteam.py` |
  | 2 | `integration/scripts/backfill/test_backfill_worker_shift_state_records.py` |
  | 1 | `integration/services/commands/cases/test_case_created_step_pause.py` |

- **`integration/services/commands/task_steps/test_add_task_steps_integration.py`** — the
  twelfth file, repaired under **its own contract** (§4 task 1b), not under task 1's. It is a
  different mechanism and the earlier draft of this plan got that wrong.
- `app/tests/database_isolation.py` — slot discriminator and its fail-closed resolver, the
  widened-but-strict pattern, the two host/port checks, and the marker/inspection probe.
- `app/tests/conftest.py` — the Redis prefix seam, the residue observation point, and the
  **collection-order hook** (task 6).
- `app/tests/fixtures/` — shared row factories, if task 1 resolves that way.
- `app/tests/integration/infrastructure/test_database_isolation.py` — criterion rows.
- `app/tests/integration/services/commands/test_system_transition_reasons_retirement.py` —
  C7(a) only.
- Nothing under `app/beyo_manager/`. Phase 1 held this line across four rounds, and the
  projection confirmed no task in this phase requires crossing it — including task 5, which
  reads the production key builders without modifying them. If you believe you must cross it,
  stop and raise an owner decision instead.

## 4. Ordered tasks

### 1. Repair the borrowing helpers — under OD-6's contract, not the earlier strict rule

The class is **not** a missing catalog: the coordinator tested that hypothesis last round and
it was refuted (seeding four roles left the same 41 failing, the signature merely moving to
`AttributeError`). The class is **helpers that read rows they did not create** —
`test_worker_shift_commands.py:79` does `select(Workspace).order_by(Workspace.client_id)`
with no filter and adopts whatever workspace exists.

**Contract — read OD-6 in full; it is the authority, this is the summary:**

| class | constraint | rule |
|---|---|---|
| `Workspace` | `name` not unique (`workspace.py:14`) | create per test |
| `PauseReason` | unique on `(workspace_id, slug)`, workspaces per test (`pause_reason.py:60`) | create per test |
| **`Role`** | **`name` globally unique** (`role.py:17-21`) | **adopt-or-create** — never assume present |

A factory that *creates* a `WORKER` role inside a committing test collides with whatever
committed first (`UniqueViolationError` on `ix_roles_name`, measured). Four of the eleven
files commit. `phase1_reference_data.py:22-28` `_role()` is already adopt-or-create and is
the precedent to follow.

**This composition is proven sufficient on the worst file before you start.** Applying it to
the single helper `_seed_workspace_worker` (`test_worker_shift_commands.py:78-89`) takes that
file from `41 failed / 1 passed` to **`42 passed in 4.48 s`**, run alone. Coordinator probe,
reverted byte-identical. You are not exploring; you are applying a measured repair to ten
more files.

**Explicit delegation (granted on purpose).** Whether this lands as *(a)* shared row
factories in `app/tests/fixtures/` reused by all eleven files, or *(b)* per-file helper
repair, is yours — the class is uniform, so either is comparable work. Bounds:
1. **One strategy for all eleven.** A mixed repair makes C2's result unattributable.
2. **No factory creates a globally-unique catalog row inside a test that commits** (OD-6).
3. Whichever shape wins, factories create rows per test on demand; they never seed a shared
   catalog (OD-1 stands).
4. The twelfth file is repaired under task 1b, not this task.

### 1b. The twelfth file — a unique-constraint collision, not borrowing

`test_add_task_steps_integration.py:83` constructs `Role(client_id=…, name=RoleNameEnum.WORKER)`
**unconditionally**. Alone on a fresh database that is fine — measured, `1 passed in 0.61 s`.
Once `test_clock_actions_integration.py` has committed a `WORKER` role it is fatal — measured,
`1 failed, 1 passed`, `UniqueViolationError`. Task 1's remedy (*create the rows you need*) is
what **produces** this failure; it cannot also be its repair.

**Repair:** adopt-or-create at that site, per OD-6.
**Its evidence is the paired run, not the alone run** — see C1(b).

### 2. Slot discriminator, with a fail-closed resolver

`beyo_test_<slot>_<worker>`; slot from an environment variable (**name delegated** — choose
it, declare it in the handoff, and document it where an operator running a second worktree
will find it, matching plan 1's precedent for the isolation module's path). Default `main`,
so serial-in-the-default-slot reads `beyo_test_main_main` and the shipped default exercises
the slot path (charter rule 10). Template is **per slot** (`beyo_test_<slot>_template`),
keeping the existing `alembic_version ≠ head → rebuild` comparison.

**The resolver validates and never normalises.** `resolve_worker_database_name`
(`database_isolation.py:29-36`) is the precedent: it *raises* on an unsupported worker id.
A resolver that lowercases or strips maps `SLOT=Alpha` and `SLOT=alpha` onto one database and
**reintroduces the exact collision this task exists to remove** — silently, which is worse
than the bug. Reject anything outside `[a-z0-9]{1,12}` rather than coercing it.

**Do not name the template by migration head** (`…_template_<head>`), the shape the intention
floated as "or better". Every head ever checked out would leave a template behind — the
unbounded `test_20260820_001, _002, …` growth the intention forbids, reintroduced through the
back door. Per-slot is bounded at *slots × (workers+1)* and a slot exists only because a
human declared one.

**One-time disposition of the legacy names.** The server holds `beyo_test_template` today
(verified). Under the new pattern that name no longer matches, so the guard refuses it and
**nothing will ever drop it** — bounded naming with a permanent orphan. The same applies to a
`beyo_test_main` or `beyo_test_gw*` left behind by a run started before the rename, which
silently breaks plan 1 C8's absorb guarantee across the boundary. State and implement the
disposition: recognise the pre-rename names as disposable for the purpose of a one-time
sweep, and say in the handoff whether that recognition is permanent or removable later.

### 3. Widen the pattern without opening it

- `\d` → `[0-9]` (N1: `\d` is Unicode-aware, so `gw٠`/`gw๐`/`gw０` pass today — no unsafe drop
  results because `_quoted_identifier` is ASCII-only, but the guard's first line should not be
  the one relying on the second).
- `$` → `\Z` (N2).
- Slot constrained to `[a-z0-9]{1,12}` **in the guard's pattern and independently at the
  resolver** (task 2).
- **Two host/port checks, both wanted, stated separately** — the earlier draft collapsed them
  into one ambiguous sentence:
  - **(i) Identity of the protected database — equality ⇒ refuse.** Today the guard compares
    *names only*, so it can be fooled. Compare the normalised `(host, port, database)` tuple.
  - **(ii) Confinement to the configured server — inequality ⇒ refuse.** This tooling has no
    business dropping a database on a server it was not pointed at. Without (ii), (i) alone
    would *weaken* today's check by making a same-named database on another host droppable.
  Together they are strictly stronger than what ships today.
- **Normalisation is load-bearing.** `.env:7` sets the host to `localhost` while every
  connection normalises to `127.0.0.1` (`database_isolation.py:79,107,296`). A naive tuple
  comparison mismatches on **every** call and refuses every drop — the suite would not run.
  Normalise both sides before comparing and say how.
- `assert_disposable_database` (`:53-69`) receives only `database_name`,
  `configured_database_url` and `marker_present` — a name has no host. **State the new
  signature in the handoff**; three tasks converge on this one function.

### 4. Close B2's second shape — at the seam that actually wedges

The earlier draft named `_drop_database_if_exists` and then described the template path.
**Both halves are true of different functions**, which the projection measured on a probe
database:

| entry point | missing relation |
|---|---|
| `_drop_database_if_exists` | `beyo_test_metadata.database_marker` |
| `inspect()` — what `_ensure_template` actually calls at `:257` | `alembic_version` |

`_ensure_template` (`:250-272`) does **not** reach `_drop_database_if_exists` for an existing
template; `inspect` (`:149-171`) begins with `SELECT version_num FROM alembic_version` at
`:152`. An implementer following the old wording literally would close the worker-shell wedge
and leave the template-shell wedge — the one the task calls unavoidable.

**Repair the marker/inspection probe seam so both missing relations are tolerated**, and make
the absent-marker case droppable **only when the database is also empty of application
tables**. That predicate is literal, not adjectival (charter rule 5):

- **Empty** ≡ zero rows in `information_schema.tables WHERE table_schema = 'public'`.
  `alembic_version` lives in `public`, so a migrated-but-unmarked database has ≥ 1 and is
  **refused**. The marker schema (`beyo_test_metadata`) is not in `public`, so its absence is
  orthogonal to the count.
- **Caught exception:** `asyncpg.exceptions.UndefinedTableError` only — both wedge shapes
  raise it. Never a bare `except Exception`; that is how the original B2 swallowed its own
  refusal.

Anything carrying tables and no marker still refuses. Fail-closed is not traded for
availability; it is made precise.

### 5. Isolate Redis per process

`isolated_redis_prefix` (`conftest.py:50-61`) mutates `os.environ`, while `make_key`
(`services/infra/redis/keys.py:4-6`), `rate_limit.py:24,34`, `auth.py:7`,
`activity_tracker.py:15` and `logout_user.py:53` all read `settings.redis_key_prefix` **at
call time** — so the fixture isolates nothing and its teardown scans a namespace nothing
writes to. Override the *setting* per process: the same seam, working for the same reason the
database override works.

**It is session-scoped but not autouse**, so as written the override would reach only tests
that request `redis_client`. The shipped default configuration must reach the behaviour
(charter rule 10) — make it autouse, or state why not.

### 6. Prove order-independence — with a shipped hook, not a local edit

C2 requires a deterministic reversal of collection order. **No `pytest_collection_modifyitems`
hook exists anywhere in the repository** (verified: no collection, sessionstart, sessionfinish
or configure hooks under `app/`; the only conftests are `tests/conftest.py` and
`tests/connecteam/conftest.py`). So it must be created, and the two obvious shapes each
contradict something:

- a **temporary local edit** → the reversed run is not taken on the tree handed over, which
  §6 requires of both L4 runs;
- an **unconstrained shipped hook** → a permanent mechanism that can reorder the entire suite,
  carrying no contract of its own.

**Resolution: ship it, gate it on an environment variable, default off, and give it a
criterion (C8).** Then both L4 runs are taken on the same tree and differ only by that
variable — two conditions, one tree, no contradiction. Plan 3 also needs the reversal, so it
belongs in the repository rather than in a session's scratchpad.

## 5. Acceptance criteria

Each row names the defect it would catch and carries one named mutation with both sides
computed and its **site named**. Rows asserting documented third-party behaviour do not
appear — the database's `TEMPLATE` feature and Alembic applying migrations were proven at
plan 1 C3/C4 and are not re-proven here.

- **C1 — the order-coupling is gone, measured two ways because the class has two mechanisms.**

  **(a) The eleven borrowing files pass alone.**
  *Defect caught:* a helper that reads a row it did not create, which passes only because an
  earlier-collected test committed one — invisible in default order, fatal the moment anything
  reorders.
  *Rows:* each of the eleven files in §3, run **alone** against a fresh worker database, exits
  with zero failures. The §3 counts are the before-side; `test_worker_shift_commands.py` alone
  is `41 failed, 1 passed` today and `42 passed` under the repair proven in task 1.
  **Named mutation, site named:** restore the unfiltered
  `select(Workspace).order_by(Workspace.client_id)` at the repaired `_seed_workspace_worker`
  ⇒ contract = `42 passed`, mutation = 41 red with
  `AttributeError: 'NoneType' object has no attribute 'client_id'`.

  **(b) The twelfth file survives the file that poisons it.**
  *Defect caught:* unconditional creation of a globally-unique row, which is invisible alone
  and fatal in company — and which task 1's remedy would *create* rather than remove.
  *Row:* `test_add_task_steps_integration.py` run **preceded by**
  `tests/connecteam/test_clock_actions_integration.py`. Before: `1 failed, 1 passed`
  (`UniqueViolationError` on `ix_roles_name`). After: `2 passed`.
  **The alone-run is explicitly NOT this row's evidence** — it is `1 passed` before and after,
  so it cannot fail and proves nothing.
  **Named mutation, site named:** restore the unconditional `Role(...)` construction at
  `test_add_task_steps_integration.py:83` ⇒ contract = `2 passed`, mutation = `1 failed`.

  *Scope:* L2 per file — twelve targeted runs, not a suite run each.

- **C2 — the failure-ID set is invariant under collection order.**
  *Defect caught:* an order dependency surviving into plan 3, where it would appear as
  nondeterministic parallel flakiness and be attributed to xdist rather than to the suite.
  *Contract:* default order and the task-6 reversal produce **the same failing-ID set**,
  `comm`-empty both ways.
  *Before-side, default order — cite the tree-matching stamp, do not re-measure it:*
  **`22 failed / 2541 passed / 1 deselected in 107.51 s`** at `d8bda2c`, failing set
  byte-identical to the published 22 (`plan_1.md`, fix-r4 consumption entry). That stamp
  covers your tree: `app/` at `d8bda2c` is identical to `app/` at HEAD, since `5ecfe90`
  changed documents only.
  *Before-side, reversed order:* `139 / 2422 / 1` (`added = 118, removed = 1`) at `87a4b7a` —
  **a description of the class, not a stamp on your tree**; no tree-matching equivalent exists
  and one is not owed.
  *Predicted after:* the published 22 **minus**
  `test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`,
  which task 1b repairs — **21**, identical in both orders. Any other difference is a
  **finding to explain, not a number to update** (plan 1 C7's rule; the intention is explicit
  that a changed set must be explained).
  **No named mutation** — an equality claim over the whole suite under two conditions, L4 by
  construction (charter: coupling discovery). C1's mutations are what prove the repair bites.

- **C3 — two slots never collide, and an invalid slot is refused rather than coerced.**
  *Defect caught:* two git worktrees running pytest simultaneously; both resolve to
  `beyo_test_main`, the second's `DROP IF EXISTS` destroys the first's database mid-run, and
  both rebuild a shared template out from under each other — failures that look like
  flakiness and are not.
  *Rows, exact strings:* slot `alpha` + `PYTEST_XDIST_WORKER=gw0` → `beyo_test_alpha_gw0`;
  slot `alpha`, no xdist → `beyo_test_alpha_main`; slot unset, no xdist →
  `beyo_test_main_main`; templates for slots `alpha` and `main` are distinct names.
  *Plus, at the resolver:* `Alpha`, `al pha`, `alpha_beta`, `""`, and a 13-character slot each
  **raise**; none is silently normalised to a valid name.
  **Named mutation, two sites:** (i) drop the slot from the name derivation ⇒ contract = the
  name sets of two slots are disjoint, mutation = identical; (ii) replace the resolver's
  rejection with `slot.lower().strip()` ⇒ contract = `Alpha` raises, mutation = `Alpha` and
  `alpha` both yield `beyo_test_alpha_main`, red.

- **C4 — the widened pattern is still closed, and every row still tests its own cause.**
  *Defect caught:* the guard is the only thing between this tooling and the owner's
  development database; widening its pattern to admit a slot is exactly when a hole gets
  introduced — and when previously-meaningful rows go green for the wrong reason.
  *Rows:* the plan 1 C2 rejection causes, **each with its name restated in slot form.** Three
  of the six existing rows (`test_database_isolation.py:40-51`) use `beyo_test_gw0` as the
  *valid* name while varying another cause (configured-database, missing marker, malformed
  URL). Under the new pattern `beyo_test_gw0` no longer matches, so each would be rejected by
  the **pattern** check and never reach the cause it was written to prove — staying green
  while the parametrize list still reads exhaustive. Restate them as `beyo_test_main_gw0`.
  *Plus one row per new cause:* a slot containing `_`; uppercase; longer than 12 characters; a
  Unicode digit in the worker index (N1); a trailing newline (N2); a database matching the
  name on a **different host or port** (task 3 check ii); and the configured database
  identified by full tuple rather than name alone (task 3 check i).
  **Named mutations — one per sub-check, sites named.** A single `return True` reddens every
  row regardless of which check bit, so it cannot detect F6's failure mode. Disable each
  sub-check independently — pattern, configured-tuple, confinement, marker, URL-parse — and
  record which rows redden for each. **A sub-check whose disabling reddens nothing has no
  row that tests it.**

- **C5 — a half-created shell is droppable; a populated one is not; both wedge shapes clear.**
  *Defect caught:* an interrupt between create and mark leaves a marker-less database that
  raises `UndefinedTableError` and wedges every later run until a human drops it by hand.
  *Rows:* (a) a correctly-named database with **no marker schema and zero `public` tables** →
  dropped, run proceeds; (b) the same name carrying `public` tables and no marker →
  `UnsafeDatabaseError`, and the database **still exists afterwards**; (c) the **template**
  path — interrupt between `_create_database(TEMPLATE)` and `_set_marker(TEMPLATE)`, then
  start a run → absorbed, no manual step. **(c) must exercise the template, not the worker**:
  they fail on different missing relations, and the template is the one every first run hits.
  **Named mutation, site named:** make the absent-marker branch unconditional ⇒ contract =
  row (b) refuses, mutation = row (b) drops a populated database, red. *This mutation is what
  proves availability was bought without spending fail-closed.*

- **C6 — the Redis prefix a test observes is the worker's, and the shipped default reaches it.**
  *Defect caught:* `isolated_redis_prefix` sets `os.environ` after `settings` is parsed, so
  every production key builder keeps returning `beyo_manager` — the fixture isolates nothing
  today, and under plan 3's workers the rate-limit, auth and activity keys would be shared
  across processes, producing interference indistinguishable from a race.
  *Rows:* (a) inside a test that requests **no Redis fixture**, `make_key("ns", "x")` returns
  a process-scoped prefix and **not** `beyo_manager` — this row is what proves charter rule 10,
  since the fixture is session-scoped but not autouse today; (b) the teardown deletes keys
  under the prefix that was actually written — assert from a **subsequent** test or an
  explicit finalizer, since a fixture's teardown cannot be observed from inside the test using
  it.
  **Named mutation, site named:** remove the `settings.redis_key_prefix` override ⇒ contract =
  a process-scoped prefix, mutation = `beyo_manager`, red on (a). *Same shape as plan 1 C5,
  the row that proved the database seam end-to-end.*

- **C7 — two rows that cannot fail are given contracts.**
  **(a)** *Defect caught:* `test_no_row_is_system_managed_any_more`
  (`test_system_transition_reasons_retirement.py:198`) asserts
  `count(*) WHERE is_system_managed = true` is 0 against a schema-only template where
  `pause_reasons` is **empty** — it passes on an empty table and would keep passing if
  production started setting the flag.
  *The repair must not reproduce the class.* Asserting a literal the test's own fixture just
  wrote (`phase1_reference_data.py:50` passes `is_system_managed=False` explicitly) fails the
  same way. **Create the pause reason through the production path**
  (`services/commands/pause_reasons/create_pause_reason.py`) and assert the flag on the
  returned row (charter rule 3 — read what the code *can do*, not what a fixture wrote).
  **Named mutation, site named:** set the flag at `create_pause_reason.py:36` ⇒ contract = the
  created row's flag is false, mutation = true, red. State one assertion shape — the flag on
  the row, not a count.
  *Production has two other writers to keep in view:* `seed_pause_reasons.py:102` and the
  model default at `pause_reason.py:36`.
  **(b)** *Defect caught:* plan 1's C6 residue proxy runs as an ordinary test and observes only
  the tests collected before it (N5) — residue written by anything ordered after it is
  unmeasured, and under plan 3 "ordered after" stops being predictable at all.
  *Placement is measured, not assumed:* session-fixture teardown runs **before**
  `pytest_sessionfinish` (`session-fixture-setup → session-fixture-TEARDOWN →
  pytest_sessionfinish`), so a `sessionfinish` hook would run after `isolated_database`
  (`conftest.py:21-33`) has already restored `settings.database_url` and dropped the worker
  database — and `configured_row_counts_before_run` lives on that already-finalised instance
  (`database_isolation.py:114`). **Put the check in `isolated_database`'s own teardown, before
  it restores the URL and drops the database.** The carrier question then disappears, and a
  raising teardown fails the session — the observable "the check reddens" needs.
  **Named mutation, site named — and it does NOT touch the development database:** commit a
  row to a **declared probe database** and point the before/after comparison at it ⇒ contract
  = counts equal, mutation = counts differ, teardown raises. Directing a test to commit into
  the configured database would violate §5A and charter rule 7.

- **C8 — the collection-order hook is off by default and reverses exactly once when asked.**
  *Defect caught:* a permanent, shipped mechanism that can reorder the entire suite, with no
  contract — and, worse, one that silently reorders in normal runs and quietly invalidates
  every measurement taken afterwards.
  *Rows:* with the variable unset, collection order is byte-identical to `--collect-only`
  without the hook; with it set, the order is exactly reversed; an unrecognised value is
  **refused**, not treated as off.
  **Named mutation, site named:** make the hook reverse unconditionally ⇒ contract = default
  order unchanged, mutation = the default run reorders, red.

## 5A. Traps this plan inherits

- **All four of plan 1 §5A still apply** — assert DDL never exit codes; compute both sides of
  every fixture before choosing it; report rather than silently delete dead scaffolding; do
  not "fix" the per-test engine churn opportunistically.
- **The cheap hypothesis for task 1 is already refuted.** Seeding a catalog does not fix the
  class; it moves the error. If you find yourself authoring a shared seed, re-read OD-3.
- **The strict rule is also refuted.** "Every test creates its own" collides on `Role`. OD-6
  is the contract; the earlier phrasing in this plan was wrong and the projection measured it.
- **A published handoff is never edited.** Corrections to numbers published in earlier rounds
  are recorded in *this* cycle's handoff. Fix r4 rewrote r2's measurement and destroyed the
  provenance of a real error; the coordinator restored the file.
- **Interrupted-run probes touch real databases.** Every probe database you create is declared
  and verified absent at close, and the configured development database is left untouched
  (charter rule 7).
- **The eleven files currently pass.** You are repairing green tests, so a careless repair
  reads as success in default order and is caught only by C2's reversal. Run C1's row for a
  file before believing its repair.
- **Three tasks converge on `assert_disposable_database`.** Change its signature once,
  deliberately, and declare it — not three times as each task arrives.

## 6. Evidence budget and notes

**This phase's L4 budget is exactly 3 runs.**

1. **One diagnostic reversal, pre-authorised**, taken mid-cycle when you judge the repair
   close to complete. No authorisation line is needed — this line *is* the authorisation.
   It exists because a repair of eleven files against an equality-of-sets criterion needs to
   see whether the class is closing before the closing pair is spent, and because the last
   round **skipped its mandatory closing stamp** under exactly this pressure, which the
   coordinator recorded as a coordinator defect. Under-measuring to stay inside a budget is
   the failure mode this line prevents.
2. **The closing pair**, both on the tree you hand over: default order (this is the mandatory
   closing stamp) and the task-6 reversal.

Any run beyond these three requires the charter's authorization line, written **before** it.

Everything else is L1/L2: twelve file-scoped runs for C1, the criterion module for C3–C8, and
every named mutation at its own site's hypothesis scope.

- **Cite, do not re-measure:** the `d8bda2c` stamp (`22 / 2541 / 1`, failing set byte-identical
  to the published 22) is tree-matching for your tree and is C2's default-order before-side.
  Re-running it is over-evidence and a finding against the round.
- The `87a4b7a` reversed-order figures are a class description, not a stamp; say so when you
  use them.
- Evidence records carry hypothesis · scope · exact command · tree identity · result · ID
  delta in both directions. Tree identity is the checkpoint SHA plus an asserted-clean
  `git status --porcelain`; a dirty tree adds a `git diff` digest.
- Recognized foreign commit streams still run alongside this work (live_clock master plan §7).
  Attribute, do not raise, files belonging to them.
- The three `ai_inferred` architecture-graph items from plan 1 remain **owner-adjudicated and
  deliberately unconfirmed**. Do not promote them; record any delta additively as plan 1 did.
- **Carried to plan 3, not this phase:** `CREATE DATABASE … TEMPLATE` fails while another
  session holds the source database open. Undecidable serially; real the moment workers exist.

## 7. Review log

### 2026-08-21 — projection r0 (independent). Verdict: AMENDMENTS_REQUIRED

Full ledger, findings and evidence:
`handoffs/reviewer/2026-08-21_phase2_projection_r0_handoff.md`.

Fifteen rows returned; a sixteenth was lifted by the coordinator from the handoff's own
"reality checks that passed". **All sixteen are routed and the gate is satisfied.** The round
found that **four of seven criteria would have been written as tests that pass whether the
code is right or wrong** — the row-that-cannot-fail class, caught on paper before a line was
written.

| # | Routed to | Disposition |
|---|---|---|
| L1 | intention **OD-6** | `Role.name` is globally unique; the strict contract was unsatisfiable. Owner ratified adopt-or-create for globally-unique catalog rows only. |
| L2 | §3, §4 task **1b**, C1(b) | Twelfth file is a collision, not borrowing; its alone-run row was decoration. Now evidenced by the paired run. |
| L3 | §4 task 4, C5(c) | Seam renamed to the marker/inspection probe; both missing relations tolerated; (c) exercises the template path. |
| L4 | §4 task 4 | Literal predicate (`public` table count, `alembic_version` counts, marker schema orthogonal) + `UndefinedTableError` only. |
| L5 | §4 task 3, C4 | Split into two checks with opposite directions, both wanted; signature declared; `localhost`/`127.0.0.1` normalisation named. |
| L6 | C4 | Every retained row restated in slot form; one mutation per sub-check, since `return True` cannot detect the failure mode. |
| L7 | §3, §4 task 6, §6, **C8** | Shipped env-gated hook, default off, with its own criterion. Both L4 runs stay on the handed-over tree. |
| L8 | §4 task 2, C3 | Resolver validates and never normalises; rows for `Alpha`/`al pha`/`alpha_beta`/`""`/13 chars. Variable name stays delegated. |
| L9 | §4 task 2 | One-time disposition of `beyo_test_template` and pre-rename worker names, which the rename would otherwise orphan. |
| L10 | C7(a) | Repair moved to the production creation path; mutation site named at `create_pause_reason.py:36`. |
| L11 | C7(b) | Check placed in `isolated_database`'s teardown (measured hook order); carrier problem dissolved; mutation moved off the dev database. |
| L12 | C2, §6 | The `d8bda2c` stamp cited as the tree-matching before-side. |
| L13 | §6 | Budget raised to 3: one pre-authorised diagnostic reversal plus the closing pair. |
| L14 | §4 task 1 | Delegation kept, four bounds added. |
| L15 | **plan 3** | `TEMPLATE` source-in-use failure — undecidable serially. |
| **L16** *(coordinator, from its reality checks)* | §4 task 5, C6(a) | `isolated_redis_prefix` is session-scoped but **not autouse**, so the override would reach only tests requesting `redis_client` — charter rule 10. C6(a) now proves it from a test requesting no Redis fixture. |

**2026-08-21 — projection r0 consumed (coordinator).** Verified rather than read.

**Perimeter: exactly one file, its own handoff** (`git status --porcelain` shows only that
untracked path; `git diff` on tracked files is empty). The declared probe database
`beyo_test_gw995` is absent and the server list is unchanged. **L4 budget was 0 and 0 L4 runs
were taken** — compliant, and the first session in this project to spend nothing on
re-measurement.

**F1 confirmed at source, and it is the round's centre.** `Role.name` carries `unique=True`
(`role.py:17-21`). `phase1_reference_data.py:22-28` `_role()` is adopt-or-create — so the
contract this plan shipped forbade the shape its own approved phase-1 fixtures use. That is a
coordinator defect in plan authoring, caught before any file was written.

**The owner's answer was verified sufficient before dispatch, by variation rather than
reproduction.** The projection proved the strict rule *breaks*; nobody had measured whether
the adopted rule *works*. Applying OD-6's composition — create-your-own `Workspace`,
adopt-or-create `Role` — to the single helper `_seed_workspace_worker`
(`test_worker_shift_commands.py:78-89`) took that file from **41 failed / 1 passed** to
**42 passed in 4.48 s**, run alone. Ten lines, one helper, the worst of the eleven. The other
three `scalar_one()` sites in that file needed no change. Probe reverted; file verified
byte-identical (`0c7d0c99…c209f39` before and after).

**Its arithmetic reconciles except in one place.** §1 says "thirteen plan gaps"; the ledger
carries **twelve** (L2–L13), with L15 classified `route upstream` and L14 a free choice. L8
is dual-classified, which may be the source. Cosmetic — every row is individually classified
correctly and routing is unaffected.

**What the coordinator got wrong, recorded because the pattern repeats.** Three of this
round's blocking-or-should-fix findings are defects in criteria I wrote: a contract that
contradicted the fixtures it cited (F1), a criterion row green on both sides (F2), and a
repair prescription that reproduced the very class it was removing (F10). All three are the
row-that-cannot-fail class in its planning form — **the twelfth, thirteenth and fourteenth
instances this organisation has recorded**, and the first caught before implementation. The
gate paid for itself in one round.
