---
plan: 2
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-21
actor: claude (plan-projection gate, round 0)
project: test_isolation_and_xdist
tree: 0a993e9, `git status --porcelain` clean at open and at close
---

# Phase 2 projection (round 0) — `test_isolation_and_xdist`

## 1. Verdict

**AMENDMENTS_REQUIRED.** Fifteen ledger rows: one intention gap (owner card 1), thirteen plan
gaps, one free choice confirmed as a delegation with added bounds. The implementer prompt should
not compile until row L1 is answered, because task 1 — the phase's largest body of work — is not
implementable as written for one of the three row classes it names.

## 2. What this concluded (owner-readable)

The plan is well aimed and its diagnosis of the problem is right, but one of its central
instructions cannot be carried out as written. The plan says every test must create the rows it
needs instead of borrowing whatever it finds. For two of the three kinds of row that works. For
the third — the "worker"/"manager" role names — the database allows only one row of each name in
existence at a time, so "every test creates its own" makes tests collide with each other instead.
I proved this by running two existing test files together: the second one fails on exactly that
collision, today, in under a second. **One decision needs you personally** (card 1 below): whether
a test may adopt one of these one-of-a-kind rows, or whether we hold the strict rule and accept a
much larger rewrite. Everything else on my list is a wording or coverage fix the coordinator can
apply to the plan without you. Nothing here says the phase is a bad idea; it says four of its
seven acceptance criteria would currently be written as tests that pass whether the code is right
or wrong.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — may a test adopt a one-of-a-kind catalog row, or must it always create its own?

**Question.** For rows the database allows only one of (the `worker` / `manager` role names), may
a test use the existing row if one is there, or must every test create its own?

**Story.** The database permits exactly one row named "worker". Early in a run, one test creates
that row and saves it permanently, and from then on every later test in the run finds it waiting.
About a hundred and twenty tests quietly lean on that. If we now tell each of those tests to make
its own instead, the first succeeds and the second hits the database's one-of-each rule and dies
there. We would trade a hundred failures that appear when the run order changes for a different
hundred that appear when it doesn't.

**Branches.**
- *Adopt-or-create, for one-of-a-kind catalog rows only:* order dependence goes away, no
  collisions; the "never use a row you did not create" rule gains one written exception.
- *Strict create-your-own everywhere:* only possible if tests are also forbidden to save rows
  permanently — far more than the eleven files this phase budgeted.
- *Create the catalog once per run:* the shared-catalog shape you already ruled against.

**Recommendation.** Adopt-or-create for one-of-a-kind catalog rows only, strict create-your-own
for everything else. It is the only branch that fits inside this phase and leaves your earlier
"no shared catalog" ruling standing.

**On silence.** The gate holds; task 1 is not implementable and no implementer prompt compiles.

**Trace.** intention OD-1, OD-3; plan 2 §3 (twelfth file), §4 task 1, C1, C2.

## 3. Decision ledger

| # | Decision point | Classification | Proposed routing |
|---|---|---|---|
| L1 | `Role.name` is globally unique, so "a test may not read a row it did not create" is unsatisfiable for the role class across tests that commit | **intention gap** | **Owner card 1**; OD-3's contract is amended in the intention, then task 1 restated |
| L2 | The twelfth file's defect is a unique-constraint collision, not borrowing; task 1's contract does not reach it, and its C1 row passes before and after the repair | plan gap | Amend §3, §4 task 1 and C1 once L1 answers; give file 12 its own contract row |
| L3 | Task 4 names `_drop_database_if_exists`, but the template shell — the case the task itself calls "the path every first run takes" — wedges inside `inspect()` | plan gap | Amend §4 task 4 to name the marker/inspection probe, and C5(c) to exercise the template path |
| L4 | "empty of application tables" is an adjective; the exact predicate and the exceptions caught are undefined | plan gap | Amend §4 task 4 with the literal predicate and the exception list (charter rule 5) |
| L5 | The N3 host/port comparison has no target-host input in the guard's signature, and its semantics are ambiguous between "equal ⇒ refuse" and "unequal ⇒ refuse" | plan gap | Amend §4 task 3 and C4 to state the signature, the direction, and the `localhost`/`127.0.0.1` normalisation |
| L6 | Plan 1's C2 rejection rows, re-asserted verbatim, are rejected by the *new* pattern rather than by the cause each was written to prove | plan gap | Amend C4: every retained row's name is restated in slot form, plus per-check mutations |
| L7 | The collection-order reversal has no home — a shipped hook is outside §3's perimeter, a local edit contradicts §6's "both taken on the tree handed over" | plan gap | Amend §3, §4 task 6 and §6 to name the mechanism and its tree identity |
| L8 | The slot env-var's **name** is delegated, but whether the resolver validates or normalises the slot is not stated; silent lowercasing merges two checkouts | plan gap (validation) + free choice (name) | Amend §4 task 2 to require fail-closed validation; delegate the name, declared in the handoff and in a durable operator-facing doc |
| L9 | Under the new pattern the legacy `beyo_test_template` (present on the server today) and any `beyo_test_main`/`beyo_test_gw*` left by an interrupted run stop matching, so plan 1 C8's absorb guarantee breaks across the rename | plan gap | Amend §4 task 2 with the one-time disposition of legacy names |
| L10 | C7(a)'s prescribed repair asserts a value its own fixture just wrote, reproducing the row-that-cannot-fail class it exists to remove | plan gap | Amend C7(a) to the production creation path (charter rule 3) |
| L11 | C7(b): the session fixture is torn down **before** `pytest_sessionfinish` (measured); no carrier is named for the before-counts, "the check reddens" has no observable, and its mutation writes to the configured development database | plan gap | Amend C7(b): name the hook, the carrier, the observable, and a probe database for the mutation |
| L12 | C2's "before" quotes `87a4b7a` while a tree-matching stamp for the implementer's own tree exists and is not cited | plan gap | Amend C2 and §6 to cite the `d8bda2c` stamp as the tree-matching comparator |
| L13 | The 2-run L4 budget leaves no diagnostic reversed run mid-cycle; the last round skipped its mandatory stamp under exactly this pressure | plan gap | Amend §6 to state explicitly whether one diagnostic reversal is pre-authorised |
| L14 | Task 1's (a) shared factories vs (b) per-file repair | **free choice — confirmed** | Keep the delegation, with three bounds added (below) |
| L15 | `CREATE DATABASE … TEMPLATE` fails while another session holds the source open — undecidable serially, real the moment workers exist | route upstream | Record against **plan 3**; not a phase-2 obligation |

### On L14 — is the delegation bounded well enough to hand over?

**Yes, with three bounds added.** The class is uniform: eleven of the twelve files carry one or
two `_seed_*` helpers doing `select(Role).where(Role.name == RoleNameEnum.WORKER)).scalar_one()`
and/or an unfiltered `select(Workspace)`, so either shape is a comparable amount of work and the
choice is genuinely the implementer's. Bounds to state with the delegation:

1. One strategy for all twelve — a mixed repair makes the C2 result unattributable.
2. Whichever shape wins, no factory may create a globally-unique catalog row inside a test that
   commits (this is card 1's answer applied).
3. The twelfth file is repaired under its own contract, not under task 1's (L2).

One other item should join the written delegation: the slot environment variable's **name**
(L8) — bounded to lowercase, declared in the handoff, matching plan 1's precedent for the
isolation module's path.

## 4. Findings — reality checks and criteria decidability

Every finding cites the exact artifact and line. Measured claims carry their evidence row from §5.

### F1 (blocking, → card 1) — task 1's contract is unsatisfiable for the role class
`plans/plan_2.md:116` states the contract: *"for the workspace / role / pause-catalog class, a
test may not read a row it or its fixture did not create in the same test."* The three classes do
not behave alike:

| class | constraint | per-test creation safe? |
|---|---|---|
| Workspace | `workspace.py:14` — `name` not unique | yes |
| PauseReason | `pause_reason.py:60` — unique on `(workspace_id, slug)`, and workspaces are per-test | yes |
| **Role** | `role.py:20` — **`name` globally unique** | **no** |

`tests/connecteam/test_clock_actions_integration.py:165-198` creates a `WORKER` role and
**commits** it, so it persists for the rest of the session. Four of the eleven files also commit
(`test_worker_shift_commands.py:360,1711,1821,1925,2220,2269`;
`test_list_users_floor_identification.py:214`; `test_update_user_admin_clock_in_code.py:150,165`;
`test_case_created_step_pause.py` ×10). A factory that creates a `WORKER` role inside any of those
collides with the first one that committed. Measured (E2): `UniqueViolationError: duplicate key
value violates unique constraint "ix_roles_name"`.

Note that the plan's own sanctioned phase-1 fixture already resolves this the other way:
`tests/fixtures/phase1_reference_data.py:22-28` `_role()` is adopt-or-create — i.e. it *reads a
row it may not have created*. The contract as written forbids the pattern the approved phase-1
fixtures use.

### F2 (blocking) — the twelfth file is a different mechanism, and its C1 row cannot fail
`plans/plan_2.md:94-95` folds `test_add_task_steps_integration.py` in as *"the twelfth file and
the other direction of the same class"*, and C1 (`:174-176`) requires each of the twelve, run
alone, to exit with zero failures.

Measured (E1): **the file already passes alone, today, on a fresh worker database — `1 passed in
0.61s`.** Its before-side and after-side are both green, so the row is decoration with a correct
name (charter rule 2's companion). Its actual defect is the collision of F1, reproduced in E2: it
constructs `Role(client_id=…, name=RoleNameEnum.WORKER)` unconditionally at
`test_add_task_steps_integration.py:83`, which is fine on a clean database and fatal once
`test_clock_actions_integration.py` has committed one. Task 1's remedy — *create the rows you
need* — is what **produces** this failure; it cannot also be its repair.

Consequence for C2 (`:190-193`): the predicted new default-order set of **21** depends on
repairing this file, whose repair is unspecified and whose direction card 1 governs.

### F3 (blocking) — task 4 fixes the worker path; the case it describes wedges elsewhere
`plans/plan_2.md:145-148`: *"A `beyo_test_*` database lacking the marker table entirely currently
raises `UndefinedTableError` from `_drop_database_if_exists` … It is reachable on the path every
first run takes: `_ensure_template` creates then marks in two steps."*

Both halves are true of different functions. `_ensure_template`
(`tests/database_isolation.py:250-272`) does **not** reach `_drop_database_if_exists` for an
existing template; it calls `self.inspect(TEMPLATE_DATABASE_NAME)` at `:257`, and `inspect`
(`:149-171`) begins with `SELECT version_num FROM alembic_version` at `:152`.

Measured on a declared probe database (E3), a plain `beyo_test_*` shell:

| entry point | result |
|---|---|
| `_drop_database_if_exists` (the function task 4 names) | `UndefinedTableError: relation "beyo_test_metadata.database_marker" does not exist` |
| `inspect()` (the function `_ensure_template` actually calls) | `UndefinedTableError: relation "alembic_version" does not exist` |

So an implementer who follows task 4 literally closes the worker-shell wedge and leaves the
template-shell wedge — which is the one the task calls unavoidable — raising from a *different*
missing relation. C5 row (c) (`:230-231`, "the real path: interrupt between create and mark, then
start a run → absorbed") tests the template path and would fail against a task-4-literal
implementation. The amendment should name the seam as the inspection/marker probe and require
tolerance of **both** missing relations.

### F4 (should-fix) — "empty of application tables" is an adjective, not a predicate
`plans/plan_2.md:149-150`. Charter rule 5. Undetermined: whether the count is `information_schema`
public tables (as `inspect` does at `:155-161`), whether `alembic_version` counts, whether the
marker schema's absence is part of the predicate, and which exception types are caught. Each
choice is the difference between a wedge that clears and one that persists; F3's measurement shows
two distinct relations can be the missing one.

### F5 (should-fix) — the N3 comparison has no third input, and its direction is ambiguous
`plans/plan_2.md:142-144` asks to *"Compare host, port and database name as a tuple against the
configured URL, not the name alone"*. `assert_disposable_database`
(`tests/database_isolation.py:53-69`) receives only `database_name`, `configured_database_url` and
`marker_present` — a database name has no host, so a tuple comparison needs a target URL the
signature does not carry. Two readings, opposite effects:

- *equality ⇒ refuse* (identity of the protected database): strictly **weakens** today's check —
  a same-named database on another host would become droppable;
- *inequality ⇒ refuse* (confine the tooling to the configured server): what C4's row at `:218-219`
  demands.

Both may be wanted; the plan states one sentence that reads as the first and one criterion row
that requires the second. A trap sits under either: `.env:7` sets the host to `localhost` while
every connection normalises it to `127.0.0.1` (`database_isolation.py:79,107,296`), so a naive
tuple comparison between the connection host and the configured URL mismatches on **every** call
and refuses every drop. The amendment must state the direction, the signature, and the
normalisation.

### F6 (should-fix) — C4's inherited rows become green for the wrong reason
C4 (`plans/plan_2.md:215-216`) re-asserts *"the plan 1 C2 rejection causes … against the new
pattern"*. Three of the six existing rows
(`tests/integration/infrastructure/test_database_isolation.py:40-51`) use `beyo_test_gw0` as the
*valid* name and vary the other cause — configured-database, missing marker, malformed URL. Under
`^beyo_test_[a-z0-9]{1,12}_(template|main|gw[0-9]+)\Z`, `beyo_test_gw0` no longer matches, so each
of those rows is rejected by the **pattern** check and never reaches the cause it was written to
prove. They stay green, the parametrize list still reads exhaustive, and the configured-database
and marker checks become untested. Charter rule 2's companion, exactly.

C4's named mutation does not catch this: `return True` (`:221`) reddens every row regardless of
which sub-check bit. The amendment should restate every retained row's name in slot form and
attach one mutation per sub-check (charter rule 11: a named mutation names where it is applied).

### F7 (should-fix) — the collection-order reversal has no specified home
C2 (`plans/plan_2.md:185`) requires *"one deterministic reversal of
`pytest_collection_modifyitems`"*. Verified: **no such hook exists anywhere in the repository**
(no `pytest_collection_modifyitems`, `pytest_sessionfinish`, `pytest_configure` or
`pytest_sessionstart` in any `.py` under `app/`; the only conftests are `tests/conftest.py` and
`tests/connecteam/conftest.py`). So it must be created, and the plan does not say where or in what
form. The two available shapes both contradict something the plan says:

- a **shipped, env-gated hook** in `tests/conftest.py` — that file is in §3's perimeter only for
  *"the Redis prefix seam, and C7(b)'s residue observation point"* (`:98`), and a permanent hook
  that can reorder the entire suite carries no criterion of its own;
- a **temporary local edit** — then the reversed run is not taken on the handed-over tree, which
  §6 (`:284-285`) states both L4 runs are.

This also decides whether plan 3 can re-run the reversal cheaply, so it is worth settling as a
shipped artefact rather than a session-local trick.

### F8 (should-fix) — slot validation is unstated, and silent normalisation collapses two slots
`plans/plan_2.md:127-128` takes the slot from an environment variable and `:141` constrains it to
`[a-z0-9]{1,12}` — but that constraint is stated for the *guard's pattern*, not for the resolver
that builds the name. `resolve_worker_database_name` (`tests/database_isolation.py:29-36`) is the
precedent: it *raises* on an unsupported worker id. If the slot resolver instead lowercases or
strips, `SLOT=Alpha` and `SLOT=alpha` silently map to one database and the concurrent-checkout
hazard the task exists to remove is reintroduced in its original form. C3 (`:205-207`) has no row
for an invalid slot at the resolver; C4 has one at the guard. Fail-closed at the resolver should be
stated, with a C3 row.

### F9 (should-fix) — the rename orphans today's databases and breaks plan 1 C8 across the boundary
The server currently holds `beyo_test_template` (verified, E0). Under the new pattern that name no
longer matches, so `assert_disposable_database` refuses it and nothing will ever drop it: bounded
naming with a permanent orphan. The same applies to a `beyo_test_main` or `beyo_test_gw*` left by
an interrupted run started before the rename — plan 1 C8's guarantee (*"an interrupted run is
absorbed, not accumulated"*, `plan_1.md:104-106`) silently stops holding across the rename
boundary. The plan should state the one-time disposition.

### F10 (should-fix) — C7(a)'s repair reproduces the class it is repairing
C7(a) (`plans/plan_2.md:249-254`) diagnoses `test_no_row_is_system_managed_any_more`
(`test_system_transition_reasons_retirement.py:198`, verified at that exact line) as vacuous, then
prescribes *"Give it a fixture row and assert the flag is false on that row"*, with the mutation
*"set the fixture row's `is_system_managed = True`"*.

That mutation reddens the test, but the test then asserts a literal its own fixture just wrote —
`phase1_reference_data.py:50` passes `is_system_managed=False` explicitly. If production started
writing `True`, the test stays green, which is the defect C7 exists to remove. Production has two
real writers — `services/commands/pause_reasons/create_pause_reason.py:36` and
`services/commands/bootstrap/phases/seed_pause_reasons.py:102` — plus the model default at
`models/tables/pause_reasons/pause_reason.py:36`. The honest row creates a pause reason **through
the production path** and asserts the flag on the returned row, with the mutation applied at
`create_pause_reason.py:36` (charter rule 3; charter rule 11 on naming the mutation's site).

Minor, same criterion: the row mixes two assertion shapes — *"assert the flag is false on that
row"* versus the mutation's stated both-sides *"contract = 0, mutation = 1"*, which is a count.
State one.

### F11 (should-fix) — C7(b) is not decidable as written, and its mutation writes to the dev database
C7(b) (`plans/plan_2.md:256-261`) moves plan 1's residue proxy *"to a session-level finish hook so
it sees the whole run"*. Four undetermined points, one of them measured:

1. **Ordering, measured (E4):** session-scoped fixture teardown runs **before**
   `pytest_sessionfinish` — hook order `session-fixture-setup → session-fixture-TEARDOWN →
   pytest_sessionfinish`. By the time the hook runs, `isolated_database`
   (`tests/conftest.py:21-33`) has already restored `settings.database_url` and dropped the worker
   database. Whether that is wanted is a design choice the plan does not make; a session-scoped
   finalizer ordered after the last test is the other candidate and sees a different world.
2. **Carrier:** `configured_row_counts_before_run` lives on the `DatabaseIsolation` instance
   (`database_isolation.py:114`) owned by that already-finalised fixture. Nothing is named to
   carry it to the hook.
3. **Observable:** *"the check reddens"* has no meaning for a `pytest_sessionfinish` hook — it
   cannot fail a test; it can only alter the exit status or raise an internal error. Charter rule 1
   requires an automated test, with the environment-lifecycle exemption needing a named automated
   proxy in the suite. Which of the two this is should be stated.
4. **The mutation touches the owner's database.** *"have a test committed near the end of
   collection write a row to the configured database"* directs the implementer to commit a row
   into the development database, against §5A (`:275-277`) and charter rule 7. Re-specify against a
   declared probe database, or state the authorisation and the deletion.

### F12 (note) — C2's "before" cites a tree that is not the implementer's, when a matching one exists
C2 (`:187-188`) gives the before as `22 / 2539 / 1` at `87a4b7a`, and §6 (`:298-299`) correctly
warns that those figures predate fix r4. But a **tree-matching** stamp already exists and is not
cited: `plans/plan_1.md`'s fix-r4 consumption entry records the coordinator's L4 run at the r4
tree — **`22 failed / 2541 passed / 1 deselected in 107.51 s`, failing set byte-identical to the
published 22**. Verified that this stamp covers the implementer's tree: `git diff 5ecfe90 HEAD --
app/` is empty and `5ecfe90` changed documents only, so `app/` at `d8bda2c` is identical to `app/`
at HEAD. Citing it costs nothing and removes a re-measurement the charter would otherwise class as
over-evidence. The reversed-order side (`139 / 2422 / 1`) has no tree-matching equivalent and
remains a class description, as §6 says.

### F13 (note) — the L4 budget leaves no diagnostic reversal, and the last round broke under that pressure
§6 (`:284-289`) sets the budget at exactly two runs, both on the handed-over tree, and requires the
charter's authorisation line before any third. A repair of eleven files against an equality-of-sets
criterion will realistically want one intermediate reversed run to see whether the class is closing
before the final pair is spent. The plan should say plainly whether that run is pre-authorised.
This is not hypothetical: the fix-r4 round skipped its mandatory closing stamp after a prompt
warned three times against re-running, and the coordinator recorded that as a coordinator defect
(`plan_1.md`, fix-r4 consumption entry). The failure mode is a round that under-measures to stay
inside a budget.

### Reality checks that passed
- All twelve file paths in §3 exist under today's tree; **none of the twelve changed between
  `87a4b7a` and HEAD** (`git diff --stat 87a4b7a HEAD -- app/tests/integration` touches only
  `test_database_isolation.py` and `test_system_transition_reasons_retirement.py`), so §3's
  per-file counts remain a valid description of those files today.
- Four sampled files, run alone at HEAD, reproduce §3's counts exactly (E5): `1`, `2`, `4`, `4`.
- Line citations resolve to what the plan claims: `test_worker_shift_commands.py:79` is the
  unfiltered `select(Workspace).order_by(Workspace.client_id)`;
  `services/infra/redis/keys.py:6` is the prefix join;
  `test_system_transition_reasons_retirement.py:198` is `test_no_row_is_system_managed_any_more`.
- All §2 Read-first targets resolve: intention §1, §2.2, §2.3, §5, OD-3, OD-4; plan 1 §5A and the
  fix-r4 consumption entry (which does enumerate four carry-forwards); r3 handoff §B1, N4, and
  N1/N2/N3/N5/N8; all five source files.
- Task 5 (Redis) is sound as diagnosed: `make_key` (`keys.py:4-6`),
  `rate_limit.py:24,34`, `auth.py:7`, `activity_tracker.py:15` and `logout_user.py:53` all read
  `settings.redis_key_prefix` **at call time**, so overriding the attribute works for the same
  reason the database override works. One point to settle when writing C6: `isolated_redis_prefix`
  (`conftest.py:50`) is session-scoped but **not autouse**, so unless it is made autouse the
  override reaches only tests that request `redis_client` — charter rule 10 (the shipped default
  must reach the behaviour). C6's second clause (*"the teardown scans the namespace that was
  actually written"*, `:242-243`) also needs an observable, since a fixture's teardown cannot be
  asserted from inside the test that uses it.
- Charter rule 10 for the slot: the default `main` yields `beyo_test_main_main`, so the shipped
  default configuration does exercise the slot path. No finding.
- Scope fence holds: nothing in tasks 1–6 requires a change under `app/beyo_manager/`, including
  task 5, which reads production key builders without modifying them.

## 5. Evidence records

All at tree `0a993e9`, `git status --porcelain` clean. Session L4 budget was **0** and **0 L4 runs
were taken**; no authorisation line was needed.

| id | hypothesis | scope | command | result |
|---|---|---|---|---|
| E0 | server inventory before and after this session | L1 | `SELECT datname FROM pg_database WHERE datistemplate=false` | before and after identical: `beyo_manager`, `beyo_test_template`, `housing_parser_plan1_20260807`, `postgres` |
| E1 | the twelfth file's C1 before-side is not red | L1 | `PYTHONPATH=. pytest -m 'not e2e' tests/integration/services/commands/task_steps/test_add_task_steps_integration.py -q` | **1 passed in 0.61s** |
| E2 | its failure is a unique-constraint collision, not borrowing | L1 | same file preceded by `tests/connecteam/test_clock_actions_integration.py` | **1 failed, 1 passed in 0.83s**; `asyncpg.exceptions.UniqueViolationError: duplicate key value violates unique constraint "ix_roles_name"` |
| E3 | a marker-less `beyo_test_*` shell wedges on two different relations by entry point | L1 | probe database `beyo_test_gw995`, created and dropped in-session | `_drop_database_if_exists` → `UndefinedTableError … "beyo_test_metadata.database_marker"`; `inspect()` → `UndefinedTableError … "alembic_version"` |
| E4 | session-fixture teardown vs `pytest_sessionfinish` ordering | L1 | isolated 1-test project in the scratchpad, no repo conftest | `session-fixture-setup → session-fixture-TEARDOWN → pytest_sessionfinish` |
| E5 | §3's per-file counts describe today's alone-runs | L2 | each of four files run alone | `test_case_created_step_pause.py` 1 failed/10 passed; `test_backfill_worker_shift_state_records.py` 2 failed/1 passed; `test_curate_shifts_from_connecteam.py` 4 failed; `test_list_workers_linear_timeline.py` 4 failed — matching §3's 1, 2, 4, 4 |

Consumed by citation, not re-measured (per the prompt): the `87a4b7a` reversed-order figures in §3
and C2 (`139 / 2422 / 1`, added 118 / removed 1) — a description of the class, not a stamp on this
tree; and the r3 handoff's per-file enumeration and notes N1–N8.

## 6. Write perimeter

**Documents: one file — this handoff.** No plan, intention, prompt, source or test file was
created, edited or deleted. `git status --porcelain` was clean at session open and at session
close, at `0a993e9` both times.

**Databases touched, and their disposition:**
- `beyo_test_gw995` — created by me as a marker-less probe for E3, dropped by me in the same
  script; absence verified in the same run (E0's after-list).
- `beyo_test_main` — created and dropped by the normal isolation lifecycle on each of the seven
  pytest invocations (E1, E2, E5). Absent at close.
- `beyo_test_template` — read only; it pre-existed this session and still exists (see F9).
- `beyo_manager` (the configured development database) — **never a target**. Every pytest run
  redirected `settings.database_url` to the worker database before any test executed; my own
  scripts connected only to `postgres` and to the probe database. The server's database list is
  byte-identical before and after (E0).

**Filesystem outside the repository:** one throwaway pytest project for E4 under the session
scratchpad (`…/scratchpad/hookorder/`), outside the repository and outside any perimeter.

**Tool-recorded state:** none. No architecture-graph delta; the three `ai_inferred` items from
plan 1 were not touched, per §6 of the plan.

## Appendix A — skeleton (NON-AUTHORITATIVE, discarded)

Recorded only so the coordinator can see what the ledger rows were derived from. **The implementer
must not receive this as guidance**; it is one projection's sketch, not a design, and where it
disagrees with an amended plan the plan wins.

- Task 2/3 forced a signature change on `assert_disposable_database` for both the slot and the
  host/port tuple, and a second one on the marker probe for task 4 — three tasks converging on one
  function is where F5's ambiguity became visible.
- Writing C4's parametrize list from the existing six rows is what surfaced F6: the names had to be
  rewritten in slot form before any row still tested its own cause.
- Sketching C7(b)'s hook is what raised the carrier question, which E4 then answered.
