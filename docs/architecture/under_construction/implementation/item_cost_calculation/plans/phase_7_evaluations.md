# Phase 7 — Evaluations

```
plan: phase 7
role: phase plan
date: 2026-08-11
state: IMPLEMENTED
```

## Goal

Ship the economic decision itself: the commit transaction (with PRIMARY binding,
currency resolution, snapshotting, the INV-E1 chain, and the mirror rule),
projections + promotion, the auto path inside `create_task`, and the evaluation
history read. **NOT in this phase:** the status query, result handler, or any
emission (phase 8); worker-facing payloads (phase 8).

## Read first

1. `master_plan.md` §§5, 6 (registry: commands, routes, identities), 9 (P-B, P-F),
   10.
2. Intention §4.5 (+A2/A8), §7.2 (narrative), **§7A + §7B entire** (the binding
   procedure — §7B.1's order governs §7.2), §7.3, §7.4, §6A.9 (currency), §6A.11
   (closed snapshot set), §9.1, cards 3 (auto path) + R1-4.
3. Precedents in-tree: savepoint —
   `services/commands/users/reconcile_worker_shift_state.py` (`begin_nested`,
   verified at `:278` on 2026-08-12); event-after-transaction —
   `services/commands/tasks/resolve_task.py` (dispatch outside `maybe_begin`).
4. Contracts: `06_commands`+local (subordinate-command event rule), `32_concurrency`,
   `36_audit_log`, `42_event`+local (+ core).

## Dependencies

Phase 6 APPROVED (commit runs on the final item schema; valuation is the only money
source).

## Files expected to change

- `app/beyo_manager/services/commands/item_economics/commit_item_cost_evaluation.py`,
  `create_item_cost_projection.py`, `delete_item_cost_projection.py`,
  `promote_item_cost_projection.py` + `requests/__init__.py` additions
- `app/beyo_manager/services/commands/tasks/create_task.py` (auto path — §7B.5
  savepoint block only; nothing else in the file changes)
- `app/beyo_manager/services/queries/item_economics/list_task_evaluations.py`
- `app/beyo_manager/domain/item_economics/serializers.py` (evaluation + term
  drill-down serialization)
- `routers/api_v1/item_economics.py` (evaluation/projection routes);
  `routers/README.md` mirrors; tests

## Implementation tasks (ordered)

1. **Commit** per §7B.1's nine steps, one transaction: task `FOR UPDATE` + §7B.2
   admission (total over all 8 states + deleted); §7B.3 PRIMARY resolution
   (`ITEM_COST_NO_PRIMARY_ITEM` when absent); config resolution per §7A.3/§7A.5
   with `FOR SHARE` (§7A.6); valuation + inputs + currency per §6A.9 (request
   overrides allowed for price/purchase cost; `ITEM_COST_EXPECTED_PRICE_REQUIRED` /
   `ITEM_COST_PURCHASE_COST_REQUIRED` per registry); calculator (nothing written
   before it succeeds); S1→S2→S3 on the evaluation chain (INV-E1;
   `ITEM_COST_CONCURRENT_COMMIT`); snapshot columns = exactly §6A.11's closed set +
   provenance FKs + episode snapshots; term snapshot rows written by the calculator
   outputs only.
2. **Mirror rule** per §7B.4: Python-tuple comparison on loaded ORM values
   (`None == None` is True — never SQL); fires iff figures differ; mirror row via
   the valuation chain S1→S2→S3 **in the same transaction**, carrying both figures +
   `V`'s currency, `created_by_id` = committing user; concurrent valuation write ⇒
   the whole commit fails `ITEM_COST_CONCURRENT_VALUATION` (no half-applied state).
3. **Projections** (§7.3): create from current committed / another projection /
   scratch, any inputs overridden, same calculator; freely soft-deletable;
   **promotion** = the commit procedure with the projection's inputs +
   `promoted_from_id`; the projection row is left byte-unchanged.
4. **Auto path** (§7B.5): in `create_task`, pre-checks first (§7A.5 rows 1–5 pass ∧
   current valuation with non-NULL expected price ∧ purchase cost present iff the
   model has a purchase term); execution inside
   `async with ctx.session.begin_nested():`; any exception → savepoint rollback,
   WARNING log with `task_id`/`item_id`/exception class, never re-raised; task
   creation never fails from this block.
5. History record + `item_economics:evaluation-committed` workspace event dispatched
   **after** the transaction; evaluation history query (committed chain ordered by
   `committed_at` + projections + term drill-down).

## Acceptance criteria

**C1 — snapshot immutability (intention test 2; HC-1/HC-7):** commit; then supersede
the item's valuation AND both config chains; committed evaluation + term rows
byte-identical; `rederive` on the stored ORM rows reproduces rate/budget/allowance
bit-for-bit.

**C2 — chain order & race (tests 3/17):** second commit for a task with a current
evaluation succeeds (fails under insert-before-close — the row's reason); exactly
one current afterwards, superseded row back-linked; INV-E1 DB conflict path (two
sessions past S1) → exactly one current + loser's exact
`ITEM_COST_CONCURRENT_COMMIT`.

**C3 — §7B.2 admission, all nine rows:** PENDING/ASSIGNED/WORKING/STALLED/READY
accept (explicit path); RESOLVED/FAILED/CANCELLED → `ITEM_COST_TASK_TERMINAL`;
deleted task → `NotFound`. STALLED accepted although nothing writes it today —
keyed to the enum, not to current writers.

**C4 — §7B.3:** no active PRIMARY → `ITEM_COST_NO_PRIMARY_ITEM`; on success
`evaluation.item_id == P.item_id`.

**C5 — mirror rows (§7B.4; intention test 12's mirror rows):**
- override differs from valuation → mirror row created via chain (both figures,
  committing user, same transaction);
- inputs equal → no mirror row;
- purchase cost NULL on both sides, price equal → **no** mirror (the
  `None == None` row — a SQL-NULL implementation fires here and turns it red);
- auto path → never mirrors (by construction);
- concurrent valuation write during commit → whole commit fails
  `ITEM_COST_CONCURRENT_VALUATION`; **no evaluation row exists** afterwards
  (atomicity: never an evaluation without its mirror or vice versa).

**C6 — configuration/selection at commit (§7A.5; test 10):** the five failure
fixtures (sole-predicate each) → exact identities; 0/1/2-group rows → exact
outcomes (`ITEM_COST_NO_COST_GROUP` / proceed / `ITEM_COST_AMBIGUOUS_COST_GROUP`
naming count + ids).

**C7 — currency & inputs (§6A.9; test 9):** unvalued item →
`ITEM_COST_ITEM_UNVALUED`; three mismatch rows (valuation≠basis, valuation≠model,
basis≠model), each naming its pair; missing expected price →
`ITEM_COST_EXPECTED_PRICE_REQUIRED`; purchase cost: model-with-term + missing →
`ITEM_COST_PURCHASE_COST_REQUIRED`, model-without-term + missing → commit succeeds
(2 rows).

**C8 — projections & promotion (HC-2 command side):** projection creation computes
via the calculator and persists `kind = projection`; promotion creates a committed
evaluation carrying the projection's inputs + `promoted_from_id`, supersedes the
previous committed one, and leaves the projection row byte-unchanged; deleting a
projection never touches committed rows.

**C9 — auto path (§7B.5; card 3):** success row — task creation with an evaluable
workspace + valued item yields a committed evaluation whose inputs came from the
valuation (and no mirror row — C5); eight pre-check-false rows (each §7A.5 failure,
unvalued, missing expected price, missing purchase-cost-with-term) → task created,
**no** evaluation, no error. **Named mutation (charter rule 11):** replacing the
`begin_nested()` savepoint with a plain `try/except` around the same body in
`services/commands/tasks/create_task.py` (definition site) must turn red the test in
which the evaluation INSERT itself raises (induced §7A.2 conflict or patched
calculator) and which asserts the task row commits and is readable afterwards.

**C10 — event & history:** `item_economics:evaluation-committed` dispatched after
the transaction (captured via the event-bus test seam); history record written;
neither occurs on a failed commit.

## Notes

- Statement order is load-bearing (M-1): never insert before S1; never
  `ON CONFLICT DO NOTHING/UPDATE` on chain indexes — the conflict is the arbiter.
- Resolution runs ONCE at creation and is snapshotted; never re-run against an
  existing evaluation (§7A.3; HC-1).
- Committed evaluations are never deletable (INV-E2); there is no delete surface to
  build — the router exposes none.
- `evaluation.currency` comes only from the valuation; requests never carry a
  currency (§6A.9).
- Archgraph: delta = evaluation command/endpoint nodes + edges to the task/item
  tables; orient on `table-task-item`, `helper-task-state-transitions`.

- **Forward note (phase-3 re-review r3, N15):** `REDERIVE_MISMATCH` conversions also swallow programmer errors (wrong-typed objects) by design — when this phase's services log/escalate the marker, the copy must say "integrity check failed", never assert "data corruption"; and callers rely on the R10-2 homogeneous payload shape (`error` key always present).

- **Forward item (phase-4 projection, B5):** phase 4's `FOR UPDATE` delete guard
  has no production counterparty until THIS phase ships §7B.1's `FOR SHARE`
  version resolution — a criterion here must exercise the delete-vs-commit race
  against the real commit path (the phase-4 test used an injected seam).

- **Forward item (4B projection N-c):** §7C.2's missing-category REFUSAL on the
  commit path needs a registered identity (`ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY`
  — propose to the coordinator before use); 4B ships only the status side.

## Amendments (projection r0, 2026-08-14) — GOVERNING

Where this block contradicts the sections above, THIS BLOCK WINS. Routed from
the projection r0 handoff (23 rows) + owner card 1 (R16-1) + intention round 16
+ master plan §6.4/§6.5 registrations of the same date.

### A1 — Files expected to change (corrected)

The list above gains:
- `services/commands/item_economics/_common.py` — `INDEX_IDENTITIES` +=
  `uix_item_cost_evaluations_current` → `ITEM_COST_CONCURRENT_COMMIT` (uniform
  conflict sentence STANDS, §6.4); receives the valuation-chain writer and the
  workspace-config loader extracted from `set_item_valuation.py`.
- `services/commands/item_economics/set_item_valuation.py` — **refactor-only**
  (D19): the inline chain S1→S2→S3 (`:128-159`) and `_load_preview_inputs`
  move to `_common.py`; call sites re-pointed; zero behavior change. **P-Z
  binds:** the phase-5 focused valuation suite green before AND after, plus a
  before/after property row asserting identical chain rows for one
  set+supersede+delete sequence.
- `tests/unit/routers/api_v1/test_item_economics_router.py` — five `_ROUTES`
  rows + the C13 completeness arbiter.
- **No migration.** D8's enum branch is dissolved (R16-1): the history record
  is TASK-linked; `history_record_entity_type_enum` is untouched.
- The `create_task.py` fence is amended (R16-4): the savepoint block PLUS the
  conditional `pending_events` append; no existing statement in the file moves.

### A2 — Task amendments

- **Task 1 (commit):** step 4 resolves the current valuation **`FOR UPDATE`**
  (R16-2). Refusals translate statuses via the §6.4 mapping table — the
  resolver gate runs BEFORE the calculator; C7's rows exercise the resolver
  route (the calculator's own identities are armor).
- **Task 3 (projections/promotion):** promotion re-runs §7B.2 admission, takes
  the task `FOR UPDATE` (it IS the commit procedure), and verifies the
  projection belongs to the task and is not soft-deleted (D21). Both commit and
  promotion route through the registered
  `_commit_item_cost_evaluation_in_session` helper (§6.5, D10).
- **Task 4 (auto path):** pre-check = active PRIMARY item ∧
  `resolve_item_economics_status(...) is NOT_EVALUATED` (§7B.5 as restated,
  R16-3 — the enumeration above is superseded). Both log lines verbatim per
  §7B.5 (D17). Event via `pending_events` append after the savepoint exits
  normally (R16-4).
- **Task 5 (history/read):** the history record is a TASK-linked
  `HistoryRecord` (`entity_type = TASK`, `change_type = UPDATED`, precedent
  `resolve_task.py:61`; `from_value`/`to_value` = superseded/new figures) —
  visible through `get_task_flow_records` with no flow-service change (R16-1).
  The evaluations read follows §6.5's four pins (D15) and owns the rederive
  marker per §6.5 (D16): `REDERIVE_MISMATCH` → ERROR log, "integrity check
  failed" copy, read still renders.

### A3 — Criteria restated (win over C1–C10 above)

- **C1 gains row 1b (D13):** a hand-written basis row whose persisted
  `cost_per_worker_minute_minor` ≠ the value derived from its own inputs →
  the committed snapshot equals the DERIVED rate (recompute decision, §6.5);
  named mutation: swapping the snapshot source to the persisted column must
  redden exactly this row (P-Q: the fixture is the only place the routes
  disagree).
- **C2 (D3, P-S judgment RECORDED):** `ITEM_COST_CONCURRENT_COMMIT`'s DB path
  is UNREACHABLE from every phase-7 surface — §7B.1 step 1's task `FOR UPDATE`
  serializes same-task commits (INV-E1 is `(task_id)`-scoped) and different
  tasks never contend. The identity is armor: its row drives the conflict from
  a second session doing a direct `ItemCostEvaluation` INSERT (precedent
  `test_phase4_fix_coverage.py:521`) and asserts the exact translated identity.
  The as-written "two sessions past S1" row is DELETED — it rewarded removing
  the task lock.
- **C5 gains row 6 (D4/R16-2):** a concurrent `set_item_valuation` that
  COMMITS between the commit's step-4 read and step 9 → afterwards the item's
  current valuation carries the manager's figures, not the mirror's (bounded
  wait, P-T); named mutation: deleting `FOR UPDATE` from the step-4 valuation
  read (definition site) must redden exactly this row.
- **C6 restated against §7C.2 (D11):** parametrize id per authority row —
  `item_missing_major_category` → `ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY`;
  no group for the category → `ITEM_COST_NO_COST_GROUP`; ambiguous →
  **unreachable** (INV-G3's live partial-unique
  `uix_production_cost_groups_major_category_active` forbids two active groups
  per category; P-S: discharged by 4B's pure-resolver test + this recorded
  note, never a command fixture); no basis version at all AND none applicable
  today → `ITEM_COST_NO_BASIS_VERSION` (two rows, one identity, pinned); no
  model version → `ITEM_COST_NO_COST_MODEL_VERSION`. The "0/1/2-group" counting
  and "five fixtures" are DELETED (pre-round-12).
- **C7 route note (D1):** each mismatch/missing-input row asserts the identity
  raised by the RESOLVER gate (§6.4 mapping), reached before the calculator
  runs.
- **C8 restated (D21/D22):** promotion rows — RESOLVED task + live projection
  → `ITEM_COST_TASK_TERMINAL`; promote a projection belonging to ANOTHER task
  (URL is projection-keyed) → `NotFound`; promote a soft-deleted projection →
  `NotFound`. "Byte-unchanged" gets its basis: EVERY column of the projection's
  `item_cost_evaluations` row, read from a SECOND session before and after the
  promote, equal on all columns **including `updated_at`** (the column carries
  `onupdate` — the implementation must not touch the ORM row; a stale
  identity-map comparison does not discharge this).
- **C9 restated (D6/D7):** the pre-check-false table is §11A.4's, TEN rows,
  one parametrize id each, expressions differing per row (P-V):
  `item_missing_major_category`, `not_configured_no_cost_group`,
  `not_configured_ambiguous_cost_group` (**unreachable** — same P-S discharge
  as C6; drive the resolver directly), `not_configured_no_basis_version`,
  `not_configured_no_cost_model_version`, `item_unvalued`,
  `item_missing_expected_price`, `item_missing_purchase_cost`,
  `currency_mismatch`, and the no-PRIMARY-item row. Each: task created, no
  evaluation row, no error, `item_economics.auto_commit_skipped` INFO line
  with the status token. The "eight rows" phrasing is DELETED.
  **Savepoint mutation fixture PINNED (D6):** the patched-calculator branch is
  INERT (a Python exception before any INSERT never poisons the transaction)
  and the induced-§7A.2-conflict branch is unreachable on a fresh task — both
  are DELETED. The fixture is a REAL failed SQL statement: seed the model with
  two `fixed_amount` terms of `2147483647` each, expected sale price `0` → the
  budget (−4 294 967 294) overflows `production_budget_minor` (`Integer`) and
  PostgreSQL rejects the INSERT inside the savepoint. Assert: the task row is
  committed and readable from a second session; the
  `item_economics.auto_commit_failed` WARNING line fires (D17). Named mutation
  unchanged: `begin_nested()` → `try/except` at the definition site in
  `create_task.py` must redden this test.
- **C10 restated (D20/R16-1):** the "event-bus test seam" does not exist —
  the seam is a per-module monkeypatch of `event_bus.dispatch` **on the module
  that dispatches**: the commit command's module for the explicit path, and
  `create_task`'s for the auto path (patching the command's symbol cannot see
  the auto path's event). After-commit observable: the fake `dispatch` reads
  the evaluation row from a SECOND session and asserts it is visible.
  History: the TASK-linked `HistoryRecord` exists AND appears in
  `get_task_flow_records`' response for the task. Neither event, nor history
  record, nor audit row on a failed commit.

### A4 — New criteria

- **C11 — the task lock (D3, P-T form):** observable
  `second_commit_blocked_while_task_locked` — counterparty
  `SELECT … FROM tasks … FOR UPDATE` in `commit_item_cost_evaluation.py`;
  bounded wait (phase-4 C3/C6 harness precedent, r2-L3 bounds); named
  mutation: deleting `.with_for_update()` at the definition site must redden
  it. Promotion shares the lock (D21) — one row proves it on the promote path.
- **C12 — FOR SHARE outcome, two chains × two orderings (D5, phase-4 B5
  discharged):** parametrized over the BASIS and MODEL chains (both delete
  guards hold `FOR UPDATE`, `delete_production_cost_basis_version.py:22` /
  `delete_cost_model_version.py:22`):
  (row 1) delete locks first, commit second → commit blocks AT RESOLUTION,
  re-reads, finds no applicable version → `ITEM_COST_NO_BASIS_VERSION` (/
  `_NO_COST_MODEL_VERSION`); **no evaluation row exists**;
  (row 2) commit resolves first, delete second → delete blocks on the shared
  lock, re-runs its reference check, finds the new evaluation →
  `ITEM_COST_BASIS_VERSION_IN_USE` (/ `_MODEL_VERSION_IN_USE`).
  Waits bounded (P-T). Named mutation: deleting the `read=True` lock clause
  from the commit path's configuration resolution (definition site) must
  redden **row 1 only** — row 2 is covered by the free FK `KEY SHARE` and a
  declaration claiming both rows redden is the P-I fifth-extension defect.
  The GROUP row needs NO lock and gets none: `delete_production_cost_group.py`
  takes no row lock and group deletion is transitively blocked by its basis
  versions' own guards — recorded so nobody adds a lock with no counterparty.
- **C13 — router surface (D14, P-R/P-J):** five new `_ROUTES` rows (both
  role-gate tests parametrize over them), PLUS the completeness arbiter:
  `{(method, path) for the router's routes} == {(method, path) for _ROUTES}` —
  named mutation: registering a route without its `_ROUTES` row must redden
  it. (This arbiter is the one phase 8 inherits.)
- **C14 — evaluations read (D15/D16):** asserts the §6.5 pins — envelope
  `{"evaluations": [...], "projections": [...]}`; committed order
  `committed_at DESC, client_id DESC` with the current row first; projections
  `created_at DESC, client_id DESC`; terms `created_at ASC, client_id ASC`
  (fixture with equal `created_at` so the tie-break is the arbiter);
  unpaginated. Marker row: a hand-corrupted snapshot (stored rate ≠ derivable)
  → response still renders, `REDERIVE_MISMATCH` logged at ERROR with
  "integrity check failed" copy (never "corruption" — N15).

### A5 — Cross-phase routing

- D23 → phase-8 plan forward note (its C7 says "all eleven values"; the
  vocabulary is 12 — `item_missing_major_category` missing).
- §7B.1 step 9's `resolve_task.py` citation narrowed to `:102-104` (round 16).

## Review log

(append-only)

- **2026-08-14 — projection r0 (Claude): AMENDMENTS_REQUIRED.** 23 rows (12
  blocking, 10 should-fix, 1 note), 1 owner card. Handoff:
  `handoffs/reviewer/2026-08-14_phase7_projection_r0_handoff.md`. Environment
  re-verified (head `be9dfe42a035`; all seven economics tables 0 rows; PG
  18.4); payload-key greps zero hits; N15 wording clean; C3 total as written;
  live graph counts corrected to 155/200 (coordinator's closeout figure was
  one high on each). Coordinator routed all 23 rows same day: owner card 1 →
  R16-1 (team flow, TASK-linked record — D8's migration branch dissolved);
  intention round 16 (R16-2 mirror-race lock, R16-3 resolver pre-check + log
  lines, R16-4 pending_events); §6.4 mapping table +
  `ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY` + audit rows; §6.5 phase-7
  registrations; this GOVERNING block (A1–A5). Gate CLEARED; implementer
  prompt `prompts/implementer/2026-08-14_phase7_implement_r1.md`.

- **2026-08-14 — implementer r1 (Codex): IMPLEMENTED.** Production perimeter:
  four evaluation/projection commands, request additions, shared `_common.py`
  valuation-chain/config-loader extraction, refactor-only valuation call-site,
  evaluation serializers/query, `create_task` savepoint auto path, five routes,
  router README, and phase-7 tests. No migration; configured development DB
  verified at `be9dfe42a035` (head). Focused phase surface: 88 router tests +
  4 integration tests passed; full non-E2E run: 2037 passed, 23 established
  baseline failures, 1 deselected (failure set unchanged from phase 6's
  2012/23/1 baseline after the phase additions). Added coverage includes the
  calculator-backed commit/projection/promotion/read flow, rederive integrity
  marker logging, task auto-commit success, overflow savepoint rollback, and
  extracted valuation set/supersede/delete chain invariants. Ruff and compile
  checks passed. Architecture Graph delta was one additive batch: 11 nodes and
  39 relationships, revision `0a71061554fa2123d7e2fba7ff853c328fb1405676194dd0d2cc7f067938266c`;
  the two pre-existing pending reviews were not adjudicated.

  Mutation ledger (executed in the main worktree and fully reverted): C9
  savepoint deletion (`create_task.py`, definition site) changed the file hash
  from `f1daef7f3e40456eeefa3cd6d6a3518c4f1abffc0eb44710de8e2d1b4205e4c8`
  to `51588d730467e2eb88bb6d052f5a4a3d914dbe961d6685c2e5462c674cf20589` and
  reddened `test_phase7_auto_commit_overflow_rolls_back_savepoint_and_keeps_task`
  with a `PendingRollbackError`; the restored file hash returned to the former
  value and the same test passed. C13 route-registration mutation changed
  `item_economics.py` from `87fcb318050bb089e3e8a5f101e2c47a7def0f68ed85da17d016d4ae544840ae`
  to `ce5d6486955dad28fb214dc7407a101e222e876d0e0c173510b7046956e81116` and
  reddened `test_router_route_pairs_match_the_authoritative_route_table` with
  the extra `GET /phase7-route-mutation`; the restored file hash returned to
  the former value and the same test passed. Other named concurrency mutations were
  not run in this implementer session; the corresponding behavioral rows and
  route completeness arbiter are present for the reviewer’s mutation pass.
