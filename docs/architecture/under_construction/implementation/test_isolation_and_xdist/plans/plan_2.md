# Plan 2 — order-independence and per-checkout isolation, still serial

```
state: NOT_STARTED
phase: 2
date: 2026-08-21
actor: coordinator (authoring)
depends_on: plan_1 APPROVED (2026-08-21, `5ecfe90`). Gates plan 3 (xdist) and, through it,
            live_clock_for_working_time_economics phase 4.
scope_fence: pytest-xdist is NOT installed in this phase either. Parallelism is plan 3,
             ratified by the owner as OD-5 (intention §3 amended, §4 OD-5).
projection_gate: MANDATORY, not waived. This phase touches ordering, derivation/naming
                 keys and destructive database operations — charter rule 6's list, three
                 times over.
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

1. **No test's outcome depends on another test having run.** Every one of the 11 files in
   OD-3's class passes when run alone on a fresh worker database, because each helper
   creates the rows it needs instead of adopting whatever the database happens to hold.
2. **Two checkouts can run pytest at the same time without destroying each other's
   databases**, via a slot discriminator ahead of the worker id — with the safety invariant
   still failing closed under the widened name pattern.
3. **The isolation seam covers every shared resource the suite touches, not only
   PostgreSQL** — Redis included, per the intention's own correctness-gate list.

**NOT in this phase:** no `pytest-xdist`, no `-n` flag, no parallel run, no worker-count
matrix, no new authoritative baseline under a changed runner (plan 3 owns all of these). No
production domain change. No fixture-scope optimisation (plan 1 C7's fence still stands).

## 2. Read first

1. `planning/intention.md` — §1 (owner's intention verbatim; the correctness gate lists
   ordering first and Redis explicitly), §2.2 (measured facts you need not re-derive),
   §2.3 (the design and the safety invariant), **§5 (the concurrent-checkout hazard — this
   phase's task 2 in full)**, **OD-3** (the ~118-test class and its binding sequence),
   **OD-4** (already discharged in fix r4).
2. `plans/plan_1.md` — §5A traps (all four still apply), and the Review log's fix-r4
   consumption entry, which enumerates this phase's four carry-forwards.
3. `archive/plan_1/2026-08-21_phase1_review_r3_handoff.md` — the enumeration of the 118 by
   file (§B1), the Redis mechanism (N4), and notes N1/N2/N3/N5/N8. **Cite this; do not
   re-derive it.** Its measurements were taken at `87a4b7a`, before fix r4's three test-file
   edits; the reversed-order figures are therefore valid as the *class* description and are
   restated as this plan's "before" side, not as a stamp on your tree.
4. Source: `app/tests/database_isolation.py`, `app/tests/conftest.py`,
   `app/tests/fixtures/phase1_reference_data.py`, `app/beyo_manager/config.py`,
   `app/beyo_manager/services/infra/redis/keys.py`.

## 3. Files expected to change

- **The 11 files of OD-3's class**, enumerated here so the perimeter is a list and not a
  description (counts are the reversed-order failures measured at `87a4b7a`):

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

  Plus **`integration/services/commands/task_steps/test_add_task_steps_integration.py`** —
  the twelfth file and the *other* direction of the same class (see C2).
- `app/tests/database_isolation.py` — slot discriminator, widened-but-strict pattern, the
  host/port comparison (N3), and the absent-marker-table branch (B2 shape 2).
- `app/tests/conftest.py` — the Redis prefix seam, and C7(b)'s residue observation point.
- `app/tests/fixtures/` — shared row factories, if task 1 resolves that way (§4 task 1).
- `app/tests/integration/infrastructure/test_database_isolation.py` — criterion rows.
- `app/tests/integration/services/commands/test_system_transition_reasons_retirement.py` —
  C7(a) only.
- Nothing under `app/beyo_manager/`. Phase 1 held this line across four rounds; if you
  believe you must cross it, stop and raise an owner decision instead.

## 4. Ordered tasks

1. **Repair the borrowing helpers.** The class is *not* a missing catalog — the coordinator
   tested that hypothesis and it was refuted (seeding four roles left the same 41 failing,
   the signature merely moving to `AttributeError`). The class is **helpers that read rows
   they did not create**: `test_worker_shift_commands.py:79` does
   `select(Workspace).order_by(Workspace.client_id)` with no filter and adopts whatever
   workspace exists.

   **Contract:** for the workspace / role / pause-catalog class, a test may not read a row
   it or its fixture did not create in the same test.

   **Explicit delegation (granted on purpose, not taken silently):** whether this lands as
   *(a)* shared row factories in `app/tests/fixtures/` reused by all twelve files, or *(b)*
   per-file helper repair, is the implementer's call, made once and stated in the handoff
   with its reason. `phase1_reference_data.py` already exists and is deliberately narrow —
   growing it into a broad reference dataset is the failure mode OD-1 was ratified against,
   so if you choose (a), the factories create per-test rows on demand; they do not seed a
   shared catalog. The projection gate confirms or reshapes this before the implement prompt
   compiles.

2. **Slot discriminator.** `beyo_test_<slot>_<worker>`, slot from an environment variable
   (name it; declare it) defaulting to `main`, so serial-in-the-default-slot reads
   `beyo_test_main_main` and each worktree declares its own. The template is **per slot**
   (`beyo_test_<slot>_template`), keeping the existing `alembic_version ≠ head → rebuild`
   comparison.

   **Do not name the template by migration head** (`…_template_<head>`), the shape the
   intention floated as "or better". It is worse: every head ever checked out leaves a
   template behind, which is the unbounded `test_20260820_001, _002, …` growth the intention
   forbids, reintroduced through the back door. Per-slot is bounded at *slots × (workers+1)*
   and a slot exists only because a human declared one.

3. **Widen the pattern without opening it.** `\d` → `[0-9]` (N1: `\d` is Unicode-aware, so
   `gw٠`/`gw๐`/`gw０` pass today — no unsafe drop results, because `_quoted_identifier` is
   ASCII-only, but the guard's first line should not be the one relying on the second).
   `$` → `\Z` (N2). Constrain the slot to `[a-z0-9]{1,12}`. Compare **host, port and
   database name** as a tuple against the configured URL, not the name alone (N3) — this is
   the axis the whole task exists on.

4. **Close B2's second shape.** A `beyo_test_*` database lacking the marker *table* entirely
   currently raises `UndefinedTableError` from `_drop_database_if_exists` and wedges every
   later run. It is reachable on the path every first run takes: `_ensure_template` creates
   then marks in two steps. Make the absent-marker-table case **droppable only when the
   database is also empty of application tables** — a half-created shell of this tooling's
   own making. Anything carrying tables and no marker still refuses. Fail-closed is not
   traded for availability; it is made precise.

5. **Isolate Redis per process.** `isolated_redis_prefix` mutates `os.environ`, while
   `make_key` (`services/infra/redis/keys.py:6`) and the rate-limit, auth and
   activity-tracker builders all read `settings.redis_key_prefix`, parsed at import — so the
   fixture isolates nothing and its teardown scans a namespace nothing writes to. Override
   the *setting* per process, the same seam and the same reason the database override works.

6. **Prove order-independence.** Default order and reversed order, failure-ID sets
   `comm`-diffed in both directions. This is the phase's gate and C2 is its criterion.

## 5. Acceptance criteria

Each row names the defect it would catch and carries one named mutation with both sides
computed. Rows asserting documented third-party behaviour do not appear — the database's
`TEMPLATE` feature and Alembic applying migrations were proven at plan 1 C3/C4 and are not
re-proven here.

- **C1 — every file in the class passes alone.**
  *Defect caught:* a helper that reads a row it did not create, which passes only because an
  earlier-collected test committed one — invisible in default order, fatal the moment
  anything reorders.
  *Rows:* each of the twelve files in §3, run **alone** against a fresh worker database,
  exits with zero failures. Enumerate all twelve; the reversed-order counts in §3 are the
  "before" side. `test_worker_shift_commands.py` alone currently reads `41 failed, 1 passed`.
  **Named mutation:** restore the unfiltered `select(Workspace).order_by(Workspace.client_id)`
  in one repaired helper ⇒ contract = that file passes alone, mutation = `NoResultFound` /
  `AttributeError: 'NoneType' object has no attribute 'client_id'` across its rows, red.
  *Scope:* L2 per file — twelve targeted runs, not a suite run each.

- **C2 — the failure-ID set is invariant under collection order.**
  *Defect caught:* an order dependency surviving into plan 3, where it would appear as
  nondeterministic parallel flakiness and be attributed to xdist rather than to the suite.
  *Contract, both directions stated as literals:* default order and one deterministic
  reversal of `pytest_collection_modifyitems` produce **the same failing-ID set**,
  `comm`-empty both ways. The "before" is `22 / 2539 / 1` default vs `139 / 2422 / 1`
  reversed (`added = 118, removed = 1`), measured at `87a4b7a`.
  **The `removed = 1` is a repair target, not a tolerance.**
  `test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
  *fails* in default order and *passes* reversed — it depends on state another test creates,
  in the opposite direction from the other 118. Repairing it removes it from the baseline, so
  **the predicted new default-order set is the published 22 minus that ID — 21.** Any other
  difference is a **finding to explain, not a number to update** (plan 1 C7's rule, and the
  intention is explicit that a changed set must be explained).
  **No named mutation** — this is an equality claim over the whole suite under two
  conditions, L4 by construction (charter test-evidence section: coupling discovery). C1's
  mutation is what proves the repair bites.

- **C3 — two slots never collide.**
  *Defect caught:* two git worktrees running pytest simultaneously; both resolve to
  `beyo_test_main`, the second's `DROP IF EXISTS` destroys the first's database mid-run, and
  both rebuild a shared template out from under each other — failures that look like
  flakiness and are not.
  *Rows, exact strings:* slot `alpha` + `PYTEST_XDIST_WORKER=gw0` → `beyo_test_alpha_gw0`;
  slot `alpha`, no xdist → `beyo_test_alpha_main`; slot unset, no xdist →
  `beyo_test_main_main`; templates for slots `alpha` and `main` are distinct names.
  **Named mutation:** drop the slot from the name derivation ⇒ contract = the name sets of
  two slots are disjoint, mutation = identical, red on every row.

- **C4 — the widened pattern is still closed.**
  *Defect caught:* the guard is the only thing standing between this tooling and the owner's
  development database; widening its pattern to admit a slot is precisely when a hole gets
  introduced.
  *Rows:* the plan 1 C2 rejection causes, **re-asserted against the new pattern** — this is
  variation, not repetition: the predicate changed, so the earlier evidence's tree identity
  no longer covers it — plus one row per new cause: a slot containing `_`; uppercase; longer
  than 12 characters; a Unicode digit in the worker index (N1); a trailing newline (N2); and
  a database matching the name on a **different host or port** than the configured URL (N3).
  Each asserts the guard raises and that no `DROP` is issued.
  **Named mutation:** replace the guard body with `return True` ⇒ contract = every row
  rejects, mutation = every row accepts, red throughout.

- **C5 — a half-created shell is droppable; a populated one is not.**
  *Defect caught:* B2's surviving shape — an interrupt between `_create_database` and
  `_set_marker` leaves a marker-less database that raises `UndefinedTableError` and wedges
  every later run until a human drops it by hand.
  *Rows:* (a) a correctly-named database with **no marker schema and zero application
  tables** → dropped, the run proceeds; (b) the same name carrying application tables and no
  marker → `UnsafeDatabaseError`, and the database **still exists afterwards**; (c) the real
  path: interrupt between create and mark, then start a run → absorbed, no manual step.
  **Named mutation:** make the absent-marker branch unconditional ⇒ contract = row (b)
  refuses, mutation = row (b) drops a populated database, red. *This mutation is the one that
  proves availability was bought without spending fail-closed.*

- **C6 — the Redis prefix a test observes is the worker's, not the shared default.**
  *Defect caught:* `isolated_redis_prefix` sets `os.environ` after `settings` is parsed, so
  every production key builder keeps returning `beyo_manager` — the fixture isolates nothing
  today, and under plan 3's workers the rate-limit, auth and activity keys would be shared
  across processes, producing interference indistinguishable from a race.
  *Row:* inside a test, `make_key("ns", "x")` returns a prefix scoped to this process and
  **not** `beyo_manager`; the `redis_client` teardown scans the namespace that was actually
  written.
  **Named mutation:** remove the `settings.redis_key_prefix` override ⇒ contract = a
  process-scoped prefix, mutation = `beyo_manager`, red. *Same shape as plan 1 C5, which is
  the row that proved the database seam end-to-end.*

- **C7 — two rows that cannot fail are given contracts.**
  (a) *Defect caught:* `test_no_row_is_system_managed_any_more`
  (`test_system_transition_reasons_retirement.py:198`) asserts
  `count(*) WHERE is_system_managed = true` is 0 against a schema-only template where
  `pause_reasons` is **empty** — it passes on an empty table and would keep passing if the
  flag came back. Give it a fixture row and assert the flag is false *on that row*.
  **Named mutation:** set the fixture row's `is_system_managed = True` ⇒ contract = 0,
  mutation = 1, red.
  (b) *Defect caught:* plan 1's C6 residue proxy runs as an ordinary test and therefore
  observes only the tests collected before it (N5) — residue written by anything ordered
  after it is unmeasured, and under plan 3 "ordered after" stops being predictable at all.
  Move the observation to a session-level finish hook so it sees the whole run.
  **Named mutation:** have a test committed near the end of collection write a row to the
  configured database ⇒ contract = the check reddens, mutation-before-the-fix = green.

## 5A. Traps this plan inherits

- **All four of plan 1 §5A still apply** — assert DDL never exit codes; compute both sides of
  every fixture before choosing it; report rather than silently delete dead scaffolding;
  do not "fix" the per-test engine churn opportunistically.
- **The cheap hypothesis for task 1 is already refuted.** Seeding a catalog does not fix the
  class. If you find yourself authoring a shared seed, re-read OD-3 — that path was measured
  and it moves the error rather than removing it.
- **A published handoff is never edited.** Corrections to numbers published in earlier rounds
  are recorded in *this* cycle's handoff. Fix r4 rewrote r2's measurement and destroyed the
  provenance of a real error; the coordinator restored the file.
- **Interrupted-run probes touch real databases.** Every probe database you create is
  declared and verified absent at close, and the configured development database is left
  untouched (charter rule 7). Plan 1's rounds did this well — `beyo_test_gw996..999` were all
  disclosed and removed.
- **The 118 currently pass.** You are repairing tests that are green, which means a careless
  repair reads as success in default order and is only caught by C2's reversal. Run C1's
  file-alone row before believing any individual repair.

## 6. Evidence budget and notes

**This phase's L4 budget is exactly 2 runs**, both taken on the tree handed over: the
**default-order** full suite (which is also the mandatory closing stamp) and the
**reversed-order** full suite. They are two distinct conditions, so both are variation, not
redundancy — this enumerated matrix *is* the budget (charter: "a phase whose own criteria
enumerate L4 measurements states that enumerated matrix as its budget"). Any further L4 run
requires the charter's authorization line, written **before** the run.

Everything else is L1/L2: twelve file-alone runs for C1, the criterion module for C3–C7, and
every named mutation at its hypothesis scope.

- Evidence records carry hypothesis · scope · exact command · tree identity · result · ID
  delta in both directions (charter "Test-evidence scope and reuse"). Tree identity is the
  checkpoint SHA plus an asserted-clean `git status --porcelain`; a dirty tree adds a
  `git diff` digest.
- The `87a4b7a` measurements quoted in §3 and C2 predate fix r4's three test-file edits.
  Cite them as the class description; do not present them as a stamp on your tree.
- Recognized foreign commit streams still run alongside this work (live_clock master plan
  §7). Attribute, do not raise, files belonging to them.
- The three `ai_inferred` architecture-graph items from plan 1 remain **owner-adjudicated and
  deliberately unconfirmed** — the owner deferred them pending this phase. Do not promote
  them; if this phase changes the isolation contract, record the delta additively as plan 1
  did.

## 7. Review log

*(empty — this plan has not been implemented)*
