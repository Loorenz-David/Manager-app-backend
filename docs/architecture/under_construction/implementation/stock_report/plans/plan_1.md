# Plan 1 — Foundation: schema, migration, reset, enums, state map, criteria normalization, test kit

```
state: NOT_STARTED
phase: 1 of 15
depends_on: —
projection: mandatory (schema predicates and the identity function are silent-failure mechanisms)
complex: no
```

## 1. Goal

Ship everything later phases build on and nothing that behaves: the four tables plus
`Task.is_stock_assignment`, their one migration, the four reset phases, the domain enums (the
assignment state enum with its **six** members, `resolved_early` included, and the active/terminal
partition), the task→assignment state map, the criteria normalization and signature, the three
settings, and the shared test kit. **Not in this phase:** any command, query, router, event, the
matcher (phase 2), the consistency check (phase 3), the transition operation (phase 4).

## 2. Read first

1. `master_plan.md` §5 (contracts), §6.1–§6.3, §6.5 (reset phases only), §6.8, §9 (rule 16), §10.
2. Intention: top section, §14B B1, §14C rows C1–C2, C21, C22, C32, C34, C45; **§14F F1** (the
   sixth state, terminal, outside the active predicate); §2.1–§2.3; §4.1–§4.4, §4A (MC-3, MC-4
   predicates only), §4B (MC-15 truth and column), §5 (the mapping table), §12A "Must-ship
   addition — workspace reset".
3. `architecture/03_models.md`, `30_migrations.md`, `21_naming_conventions.md`, `25_soft_delete.md`.
4. Existing shapes (relational reads only): `bm/models/tables/items/item_category.py` (a full model
   with authorship + soft-delete trio), `bm/models/tables/tasks/task_item.py` (partial unique indexes
   with `postgresql_where`), `bm/models/tables/tasks/task.py:87-92` (the `onupdate=` this project
   must not copy), `bm/models/base/identity.py`, `bm/models/base/sa_enum.py`,
   `bm/domain/items/properties_signature.py`, `bm/domain/tasks/enums.py:TaskStateEnum`,
   `bm/services/commands/reset/reset_app.py` and one phase file
   (`reset/phases/delete_task_items.py`), `bm/config.py:60-70` (setting declaration shape),
   `app/tests/database_isolation.py:40-60` (how the template is built from the head),
   `app/tests/integration/services/commands/tasks/test_delete_task_upholstery_requirements_integration.py:49-85`
   (the seeding pattern the kit generalises).
5. Scanner `normalizeCriteria`: `apps/backend/src/modules/stock/domain/property-criteria.ts:29-55`
   at Scanner commit `0d80bf2` (read-only, for C4's fixture cells).

## 3. Dependencies

None. Gate: intention header `status: RATIFIED`; `master_plan.md` §6 names every identifier used
below.

## 4. Files expected to change

New: `bm/domain/stock_report/__init__.py`, `enums.py`, `state_map.py`, `criteria_normalization.py`;
`bm/models/tables/stock_report/__init__.py`, `stock_report_item.py`, `stock_task_assignment.py`,
`stock_report_history_record.py`, `stock_report_repair_record.py`;
`app/migrations/versions/<rev>_create_stock_report_tables.py`;
`bm/services/commands/reset/phases/delete_stock_report_repair_records.py`,
`delete_stock_task_assignments.py`, `delete_stock_report_history_records.py`,
`delete_stock_report_items.py`; `app/tests/helpers/stock_report.py`;
`app/tests/unit/domain/stock_report/__init__.py`, `test_criteria_normalization.py`, `test_state_map.py`,
`test_assignment_state_enum.py`;
`app/tests/integration/models/stock_report/__init__.py`, `test_stock_report_schema.py`;
`app/tests/integration/services/commands/reset/__init__.py`, `test_reset_stock_report_phases.py`.

Edited: `bm/models/__init__.py` (register four modules), `bm/models/tables/tasks/task.py` (one
column), `bm/models/tables/client_id_prefix_map.md` (four rows), `bm/config.py` (three fields),
`bm/services/commands/reset/reset_app.py` (four calls first, docstring list updated).

## 5. Tasks (in order)

1. **Enums and state map** per master plan §6.1. `StockTaskAssignmentStateEnum` has six members
   (`in_queue`, `in_progress`, `awaiting`, `resolved`, `failed`, `resolved_early` — intention §14F
   F1); `ACTIVE_ASSIGNMENT_STATES = {in_queue, in_progress, awaiting}` and
   `TERMINAL_ASSIGNMENT_STATES = {resolved, failed, resolved_early}` partition the enum, and every
   later phase reads these two frozensets instead of spelling state lists (master plan §9 rule 16).
   `ASSIGNMENT_STATE_BY_TASK_STATE` is a plain dict literal over all eight `TaskStateEnum` members
   (intention §5 table; no task state maps to `resolved`, `failed`-only, or `resolved_early` — the
   latter is entered only by the Scanner processed webhook, phase 9); no `.get` default anywhere.
2. **Models** per §6.2, exactly: column types, nullability, defaults and `server_default`, the
   partial unique indexes with `postgresql_where=text(...)`, the CHECK constraints, the composite
   indexes, FK `ondelete="RESTRICT"` + `index=True`, no `onupdate=`. Register in `bm/models/__init__.py`.
   Add `is_stock_assignment` to `Task` with `default=False, server_default=sa.false()`.
3. **Migration**: autogenerate with the registered message on top of `ce99896e6f49`; open the file
   and verify against §6.2 (autogenerate may omit partial-index predicates and CHECKs — add them by
   hand inside the generated revision and record that in the handoff); `downgrade()` drops the four
   tables, the four enum types and the `tasks` column. Apply to a disposable DB only (charter rule 7);
   the test template picks the head up automatically.
4. **Reset phases**: four files in the shape of `delete_task_items.py`; call them as the first four
   statements inside `reset_app`'s transaction, in §6.5's order; extend the docstring list.
5. **Settings** per §6.3.
6. **Criteria normalization** per intention MC-3, exactly the value table (7 shapes), keys untouched,
   `str.strip()` then `str.lower()` then set then `sorted()`; `compute_stock_criteria_signature`
   composes the unchanged `compute_properties_signature`.
7. **Test kit** `app/tests/helpers/stock_report.py` per §6.8: `seed_stock_report_workspace`,
   `purge_stock_report_workspace`, `make_ctx`, `capture_dispatch`. The purge deletes, in this order,
   rows of: repair records, assignments, history records, stock rows, `task_items`, `task_steps`
   (and their child tables the kit creates, if any), `tasks`, `items`, `item_categories`,
   `history_records`/`history_record_links` for the workspace, `workspace_memberships`, the
   workspace, then the kit's users. Every function in the kit is called by a test in this phase
   (charter rule 4): `seed`/`purge`/`make_ctx` by C1–C3, `capture_dispatch` by C3(a) (asserting the
   `workspace:reset` event is the only one dispatched).
8. **Tests**, one file per §4, rows below transcribed first, then armed (tests first, from the table).

## 6. Criteria

Every row is a separate obligation; the trace cell names the contract or ledger entry it serves.
"IntegrityError naming X" = `sqlalchemy.exc.IntegrityError` whose `.orig` message contains the
constraint/index name X. Rows that insert conflicting rows run inside a `begin_nested()` savepoint
so the session survives.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | Two live `StockReportItem` rows, same `(W, K, signature)` | second flush → IntegrityError naming `uix_stock_report_items_identity_active` | drop the index (`stock_report_item.py` `__table_args__`) | MC-4 |
| C1(b) | Same identity; first row `is_deleted=True` | second flush succeeds; both rows present | drop `postgresql_where` from that index → (b) fails | MC-4, MC-16 |
| C1(c) | Two assignments on I, different tasks, both `in_queue` | IntegrityError naming `uix_stock_task_assignments_item_active` | drop the index | MC-4 |
| C1(d) | First assignment `resolved`, second `in_queue`, same I | second flush succeeds | drop `state IN (...)` from the predicate | MC-4, MC-16 |
| C1(e) | First assignment `failed`, second `in_queue`, same I | succeeds | same mutation as (d) | MC-4 |
| C1(f) | First assignment `in_queue` but `is_deleted=True`, second `in_queue`, same I | succeeds | drop `is_deleted = false` from the predicate | MC-16 |
| C1(g) | Two active assignments on T, different items | IntegrityError naming `uix_stock_task_assignments_task_active` | drop the index | MC-4 (U15) |
| C1(h) | Same `(K name, signature)` in W and in the foreign workspace | both succeed | drop `workspace_id` from the identity index | M4 |
| C1(i) | First assignment `resolved_early`, second `in_queue`, same I | second flush succeeds (the Postgres enum holds the value and the partial index excludes it) | add `resolved_early` to the index predicate's `state IN (...)` list → IntegrityError | MC-4, §14F F1 ("not active … does not block a new assignment") |
| C1(j) | Two assignments on T, different items, first `resolved_early`, second `in_queue` | succeeds | same mutation on `uix_stock_task_assignments_task_active` | MC-4, §14F F1 |
| C2(a) | `alembic.autogenerate.compare_metadata` against the migrated worker DB (via `run_sync`), diffs filtered to the four new tables and `tasks` | empty list | remove one CHECK from the model → diff non-empty | §6.2 parity |
| C2(b) | Insert row with `quantity_requested = -1` | IntegrityError naming `ck_stock_report_items_quantity_requested_nonneg` | drop the CHECK | MC-1 (checks stay) |
| C2(c) | `quantity_in_queue = -1` | IntegrityError naming `…_quantity_in_queue_nonneg` | drop the CHECK | MC-1 |
| C2(d) | `quantity_in_progress = -1` | IntegrityError naming `…_quantity_in_progress_nonneg` | drop the CHECK | MC-1 |
| C2(e) | `quantity_awaiting = -1` | IntegrityError naming `…_quantity_awaiting_nonneg` | drop the CHECK | MC-1 |
| C2(f) | Assignment with `quantity = 0` | IntegrityError naming `ck_stock_task_assignments_quantity_positive` | drop the CHECK | MC-13 (C21) |
| C2(g) | History record with `quantity_awaiting = -1` | IntegrityError naming `ck_stock_report_history_records_quantity_awaiting_nonneg` | drop the CHECK | MC-5 |
| C2(h) | Raw `INSERT INTO tasks (...)` listing every NOT NULL column except `is_stock_assignment` | succeeds; `SELECT is_stock_assignment` returns `false` | remove `server_default` (model + revision) | MC-15; §10 hazard (a) |
| C3(a) | W holds one row R, one assignment A (credited to G), one goal record G, one repair record (any trigger), plus K, I, T; the foreign workspace holds the same | `reset_app(ctx for W)` returns; `SELECT count(*) … WHERE workspace_id = W` is 0 on all four tables; the workspace row is gone; the foreign workspace's four counts are unchanged; the only dispatched event is `workspace:reset` | move the four phase calls after `delete_tasks` (`reset_app.py`) → FK RESTRICT from `stock_task_assignments.task_id` | §12A reset, M1 |
| C4(a) | `{"k": None}` | `{"k": None}` | — (wildcard passthrough; covered by (d)'s mutation set) | MC-3 |
| C4(b) | `{"k": "  Teak "}` | `{"k": ["teak"]}` | drop `.strip()` → `[" teak "]` | MC-3 |
| C4(c) | `{"k": ""}` | `{"k": ""}` | treat blank as `[]` → red | MC-3 (U4) |
| C4(d) | `{"k": "  "}` | `{"k": "  "}` | same as (c) | MC-3 |
| C4(e) | `{"k": ["Teak", "Dark", " teak "]}` | `{"k": ["dark", "teak"]}` | drop de-duplication → `["dark","teak","teak"]`; drop `sorted` → order kept | MC-3 |
| C4(f) | `{"k": []}` | `{"k": []}` | normalise to `[]` sorted-set path (indistinguishable) — this row bites when the "not understood" branch is removed and `[]` becomes `sorted(set())` = `[]`: **cannot isolate**; the discriminating row is (g) | MC-3 |
| C4(g) | `{"k": ["", "  "]}` | `{"k": ["", "  "]}` | drop the "at least one non-blank" test → `[]` | MC-3 |
| C4(h) | `{"k": ["Teak", 1]}` | `{"k": ["Teak", 1]}` | coerce elements with `str()` → `["1","teak"]` | MC-3 |
| C4(i) | `{"k": 1}` | `{"k": 1}` | wrap scalars → `["1"]` | MC-3 |
| C4(j) | `{"k": 1.0}` | `{"k": 1.0}` (type `float`) | same as (i) | MC-3 |
| C4(k) | `{"k": True}` | `{"k": True}` (type `bool`, not `1`) | same as (i) | MC-3 |
| C4(l) | `{"k": {"a": 1}}` | `{"k": {"a": 1}}` | recurse into dicts → red | MC-3 |
| C4(m) | `{"k": "TEAK"}` | `{"k": ["teak"]}` | drop `.lower()` | MC-3 |
| C4(n) | `{"k": "Straße"}` | `{"k": ["straße"]}` (`str.lower`, not `casefold`, which would give `strasse`) | swap to `casefold` | MC-3 |
| C5(a) | `{"Wood_Type": ["x"], "wood_type": ["x"]}` | both keys kept; signature differs from `{"wood_type": ["x"]}` alone | lower-case keys → collapse | MC-3 (U4) |
| C5(b) | `{" wood_type": ["x"]}` vs `{"wood_type": ["x"]}` | two different signatures | strip keys | MC-3 |
| C5(c) | Every raw payload of C4 and C5 | `normalize(normalize(x)) == normalize(x)` | make `str` wrap twice (`[["teak"]]`) | MC-3 idempotence |
| C5(d) | Six raw payloads with **hand-written** expected normalized dicts in the test | `compute_stock_criteria_signature(raw) == sha256(json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False))` for each | any change to the algorithm (the golden vectors are what redden) | MC-3 version rule |
| C5(e) | `{"k": 1}` vs `{"k": 1.0}` | different signatures | — (follows from (i)/(j) + json.dumps; recorded, not mutated) | MC-3 |
| C5(f) | `{"k": True}` vs `{"k": 1}` | different signatures | — | MC-3 |
| C5(g) | `{"k": [1, 2]}` vs `{"k": [2, 1]}` | different signatures (not-understood list order significant) | sort not-understood lists | MC-3 |
| C5(h) | `{"a": {"x": 1, "y": 2}}` vs `{"a": {"y": 2, "x": 1}}` | same signature | — (property of the reused function) | MC-3 |
| C6(a) | `set(ASSIGNMENT_STATE_BY_TASK_STATE) == set(TaskStateEnum)` | true | delete one key | MC-2 step 4 |
| C6(b) | `pending` | `in_queue` | swap value | §5 |
| C6(c) | `assigned` | `in_queue` | swap | §5 |
| C6(d) | `working` | `in_progress` | swap | §5 |
| C6(e) | `stalled` | `in_progress` | swap | §5, C5 |
| C6(f) | `ready` | `awaiting` | swap | §5 |
| C6(g) | `resolved` | `awaiting` | swap | §5 |
| C6(h) | `failed` | `failed` | swap | §5 |
| C6(i) | `cancelled` | `failed` | swap | §5 |
| C6(j) | `set(ASSIGNMENT_STATE_BY_TASK_STATE.values())` | `== {in_queue, in_progress, awaiting, failed}` — no task state maps to `resolved` or `resolved_early` | map `ready` to `resolved_early` | §5, §14F F2 ("Scanner only") |
| C7(a) | `ACTIVE_ASSIGNMENT_STATES ∪ TERMINAL_ASSIGNMENT_STATES` and `ACTIVE_ASSIGNMENT_STATES ∩ TERMINAL_ASSIGNMENT_STATES` (Python `\|` / `&` on the frozensets) | `== set(StockTaskAssignmentStateEnum)` and `== frozenset()` (a partition — a seventh member added to the enum without a home reddens this row) | add a member to the enum only | MC-1 table totality, §14F F1 |
| C7(b) | `StockTaskAssignmentStateEnum.RESOLVED_EARLY` | `in TERMINAL_ASSIGNMENT_STATES` and `not in ACTIVE_ASSIGNMENT_STATES`; `.value == "resolved_early"` | put it in the active set | §14F F1 (terminal; P42 name) |

Settings (task 5) carry no criterion: they have no behaviour until phase 6, whose instrument (i)
reads the default from the class.

## 7. Notes

- Sizing: 53 criterion rows in 7 criteria; `complex: no` — schema plus pure
  functions, no concurrency or set-based SQL. (Counts re-derived by script after the round-9
  fold; see the delta handoff.)
- Round 9 (2026-09-19): C1(i)–(j), C6(j), C7(a)–(b) added for the sixth state. The partial-index
  predicates are **inclusion** lists of the three active states and need no edit; the enum type
  gains the value in the one migration (it is created in phase 1, so no `ALTER TYPE` is ever
  needed).
- C4(f) is declared unable to isolate its predicate (doctrine: say so); C4(g) is the discriminating
  neighbour. C5(e), C5(f), C5(h) are recorded properties of the reused signature function, not
  mutation targets.
- The golden vectors in C5(d) are hand-derived expected dicts, so the test cannot pin its own
  output (charter rule 15's snapshot trap).
- The kit's `seed_stock_report_workspace` must flush, never commit; tests that call a committing
  command purge in `finally`.
- Migration: verify `postgresql_where` and every `ck_` made it into the revision; autogenerate is
  known to drop them.

## 8. Review log

(empty — append-only, shared by implementer and reviewer)

### Implementer note — Batch A session (2026-09-20)

Schema/domain/reset implementation and focused tests are present and green as part of the Batch-A
perimeter (`139 passed`; scoped Ruff and `git diff --check` clean). The configured development
database was not migrated or downgraded. The complete named-mutation set and pre-edit full-suite
baseline are captured in the Batch-A handoff; this phase remains pending reviewer-owned
graph/checkpoint gates and is not promoted here.

### Review — batch A round 1 (2026-09-20, plan-reviewer, tree `0d5d31d`) — CHANGES_REQUESTED

Rows: 53 — PASS 40 / FAIL 8 / NOT_VERIFIED 5. Full record:
`handoffs/reviewer/2026-09-20_batch_A_review_1_handoff.md`.

- **F-B2 (blocking)** `normalize_stock_criteria` (`criteria_normalization.py:17`) does not filter
  blank elements out of an understood list: `{"k": ["Teak","  ","Dark"]}` → `['', 'dark', 'teak']`;
  MC-3's value table says `sorted({e.strip().lower() for e in v if e.strip().lower() != ""})`.
  Signature/identity divergence. Owner card 1 covers `CRITERIA_NORMALIZATION_VERSION`.
- **F-S4** C1(c)/(g) FAIL: the only index test matches
  `uix_stock_task_assignments_(item|task)_active` on a fixture violating both — the disjunction
  charter rule 2 forbids. C1(d),(e),(f),(h),(j) NOT_VERIFIED. Reviewer probes P3,P4,P6–P9 confirm
  all seven behaviours are **correct**; the coverage is what is missing. One row per letter, each
  naming one index.
- **F-S5** C2(a) FAIL: the row's `compare_metadata` instrument was replaced by a source-text grep of
  the revision file (`tests/unit/domain/stock_report/test_schema_contract.py:98-113`), which cannot
  observe a model↔DB divergence. Reviewer probe P2 ran the real comparison: 0 diffs on the five
  tables. Build the row as written.
- **F-S9** C5(a)/(b) FAIL (the "two different signatures" clause is never asserted); C5(c) FAIL
  (idempotence over one payload, not every C4/C5 payload); C5(d) FAIL (one golden vector, the row
  says six).
- **F-S10** C3(a) FAIL: "the workspace row is gone" unasserted; the test commits two workspaces and
  never purges (charter rule 11½, §9 rule 1); C3(a)'s stated caller `capture_dispatch` was
  hand-rolled instead.
- **F-S14** orphan tests (charter rule 16): `test_schema_contract.py` (4),
  `test_repair_record_values.py` (1), `test_settings.py` (2) — this plan states settings carry no
  criterion — and `tests/integration/helpers/test_stock_report_helper.py` (1, the only caller of
  `purge_stock_report_workspace`; route it, don't delete it).
- **Mutation audit**: C1(a),(b),(c),(f),(g),(h),(i)/(j) and C2(a),(b),(c),(e),(h) were probed against
  `test_schema_contract.py` (ORM metadata / migration source) rather than the DB-level outcome each
  row names. C5(g) and C7(a) never probed (both re-derived as armed).
- Notes: N-4 `reset_app` docstring not extended (task 4); N-5 `tests/unit/domain/stock_report/__init__.py`
  is the only `__init__.py` under `tests/` in the repo; N-6 history-record counters gained an
  undeclared `default=0, server_default="0"`.
- **Lessons**: L-1 the C4 value table has no mixed blank/non-blank list row — the exact MC-3 row the
  implementation got wrong. L-5 C1(c)/(g) should quote rule 2's "expected outputs too" clause.
  L-6 §4 lists `__init__.py` files no test package in this repo uses.

### Implementer fix-round routing — Batch A fix 1 (2026-09-20)

- Candidate criterion: MC-3 normalization must remove blank elements from a list that mixes blank
  and non-blank strings while preserving the non-blank normalized set; the value table did not
  enumerate this input, so the fix-round test records it here rather than editing the criteria table.
- Candidate criteria routed under charter rule 16: the four `test_schema_contract.py` checks, the
  `_text` contract check in `test_repair_record_values.py`, the two settings checks in
  `test_settings.py`, and the retained `test_stock_report_helper.py` purge-kit check. The latter is
  retained because it is the only caller that discharges the kit cleanup obligation.
- Accepted deviations recorded: the existing `test_stock_report_reset.py` filename is used instead
  of the stale `test_reset_stock_report_phases.py` name, and no new `requests/__init__.py` is created
  because the repository convention does not require it.
- The two orphan settings checks in `tests/unit/domain/stock_report/test_settings.py` were deleted
  under charter rule 16 after removing the sole test-package `__init__.py` exposed a duplicate-module
  collection error with `tests/helpers/test_settings.py`; the settings behavior has no stock-report
  criterion.

### Re-review — batch A round 1 fix (2026-09-20, plan-reviewer, tree `983d774`) — APPROVED (phase 1)

Rows: 53 — **PASS 53 / FAIL 0 / NOT_VERIFIED 0** (was 40/8/5). Full record:
`handoffs/reviewer/2026-09-20_batch_A_rereview_1_handoff.md`. The batch verdict is
CHANGES_REQUESTED on plan 3 findings only; nothing in this plan is outstanding.

- **F-B2 CONFIRMED.** `criteria_normalization.py:17-19` filters blank elements;
  `{'k': ['Teak','  ','Dark']}` → `['dark','teak']`. `CRITERIA_NORMALIZATION_VERSION == 1` — the
  owner's ruling held. Removing the filter reddens `test_normalization_value_table[raw5]` and
  `test_signature_uses_normalized_golden_vectors[raw1]`.
- **F-S4 CONFIRMED.** C1(c)–(j) are now seven DB-level rows, each naming **one** index. The
  disjunction is gone: the two unique indexes are `(workspace_id, item_id)` and
  `(workspace_id, task_id)`, and each fixture violates exactly one. All six named mutations run as
  **database** mutations (DDL inside the rolled-back session) and every one flips the outcome —
  except C1(h)'s.
- **C1(h)'s named mutation is an EQUIVALENT MUTANT** (lesson L-10): `item_category_id` is FK-bound to
  one workspace, so dropping `workspace_id` from `uix_stock_report_items_identity_active` changes no
  observable outcome. Recorded as equivalent; no test demanded.
- **F-S5 CONFIRMED.** C2(a) is now the real `compare_metadata` over `run_sync`, filtered to the five
  tables. **The row's named mutation is INERT** (lesson L-11): Alembic does not diff CHECK
  constraints — measured, 33 passed. Calibrated with "remove an index from the model" → RED. The
  CHECKs are covered at DB level by C2(b)–(g); nothing is unguarded.
- **F-S9 CONFIRMED.** C5(a)/(b) assert two different signatures; C5(c) runs over 15 payloads; C5(d)
  ships six hand-written golden vectors. Two measurements worth keeping: C5(c)'s named mutation
  (`str` wraps twice) is still idempotent and so cannot redden its own guard; C5(d)'s "drop
  `sorted()`" reddens on only 4 of 7 `PYTHONHASHSEED` values, because the intermediate is a `set`
  (lesson L-15). Enumeration is 7 payloads short of "every raw payload of C4 and C5" — backlog
  note N-R2, deliberately not blocking, since every branch is represented.
- **F-S10 PARTIAL.** C3(a) now asserts all four clauses including "the workspace row is gone", uses
  the kit's `capture_dispatch` and purges in `finally`; both named mutations redden. Residual: the
  **own** workspace's two kit users are still committed and never deleted (~13 → 2 rows/run) —
  note N-R4.
- **N-4, N-5 CONFIRMED.** Docstring renumbered (it skips 23 and 27 — a pre-existing off-by-one,
  note N-R8); `find app/tests -name __init__.py` is now empty. The duplicate-module collection story
  checks out: `tests/helpers/test_settings.py` contains **no tests** — it is a helper whose `test_*`
  name makes pytest collect it (note N-R9). No basename collides under `app/tests` today, and the
  deleted checks covered settings this plan states carry no criterion until phase 6 (routed there).
- **Lessons**: L-10 (C1(h)'s mutation is equivalent), L-11 (C2(a)'s CHECK mutation is inert),
  L-15 (`sorted()` over a `set` is not deterministically mutation-testable).

### Implementer fix-round routing — Batch A fix 2 (2026-09-20)

Plan 1's migration-schema criterion remains the sole owner of the worker-schema comparison. The
byte-for-byte duplicate test in plan 3 was deleted under charter rule 16; no plan 1 production or
criterion change was needed.

### Re-review — batch A round 2 fix (2026-09-20, plan-reviewer, tree `f2157bd`) — APPROVED

Rows: 53 — **PASS 53 / FAIL 0 / NOT_VERIFIED 0**, unchanged and not re-verdicted. Full record:
`handoffs/reviewer/2026-09-20_batch_A_rereview_2_handoff.md`.

- **F-R3 CONFIRMED.** C2(a)'s test, `test_stock_report_schema.py:264-279`
  (`test_stock_report_migration_matches_runtime_metadata`), is intact and byte-for-byte what
  re-review 1 verified; plan 1 is again the sole owner of the worker-schema comparison. A
  function-name diff of both touched test files across `983d774..f2157bd` shows exactly **one**
  deletion (the plan 3 duplicate) and **zero** additions, so nothing else went with it.
- Nothing else in plan 1's perimeter moved. The cited L4 on `f2157bd` (21 / 3264 / 2, baseline-identical
  both ways) is the regression evidence; its −1 against 3265 is exactly that deletion.
