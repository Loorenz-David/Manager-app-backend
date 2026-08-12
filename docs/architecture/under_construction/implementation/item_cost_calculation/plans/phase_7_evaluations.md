# Phase 7 — Evaluations

```
plan: phase 7
role: phase plan
date: 2026-08-11
state: NOT_STARTED
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

## Review log

(append-only)
