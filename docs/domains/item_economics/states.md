# Item Economics States

Three state-carrying things live here: the **economics status** a task or item reports,
the **evaluation chain**, and the **result row's lifecycle**.

---

## `EconomicsStatusEnum` — the one status vocabulary

Twelve values, code-owned (never a catalog row), used identically by the budget-status
query, the valuation endpoint's preview, and the auto-commit log line.

Resolution is a branch, not a flat list. **The evaluated branch is checked first.**

### Branch A — a current committed evaluation exists

The configuration is irrelevant here: the snapshot is self-sufficient.

| Value | When |
|---|---|
| `infeasible` | `allowed_worker_minutes ≤ 0` |
| `ok` | otherwise |

### Branch B — no current committed evaluation

The reason, in this precedence order. **First match wins.**

| # | Value | When |
|---|---|---|
| 1 | `item_missing_major_category` | The item's major-category snapshot is absent or is not a known value. The category is a precondition of every later check. |
| 2 | `not_configured_no_cost_group` | The workspace has no active cost group for that category |
| 3 | `not_configured_ambiguous_cost_group` | More than one active group for that category — structurally unreachable under the one-active-group-per-category index, retained as the classifier's total-order defence |
| 4 | `not_configured_no_basis_version` | The selected group has no basis version applicable today |
| 5 | `not_configured_no_cost_model_version` | The workspace has no cost-model version applicable today |
| 6 | `item_unvalued` | The item has no current valuation |
| 7 | `item_missing_expected_price` | The valuation carries no `expected_sale_price_minor` |
| 8 | `item_missing_purchase_cost` | The valuation carries no `purchase_cost_minor` — **only when** the selected model version carries an `item_purchase_cost` term |
| 9 | `currency_mismatch` | The valuation, basis-version and model-version currencies are not all equal |
| 10 | `not_evaluated` | Everything above is satisfied; nobody has committed yet |

The order above is the **evaluation order**, and it is the order to publish. The order the
values happen to be declared in carries no precedence: precedence lives in two explicit
ordered sequences in `domain/item_economics/configuration.py`
(`CONFIGURATION_FAILURE_PRECEDENCE` for rows 1–5, `ITEM_READINESS_PRECEDENCE` for rows
6–10), never in enum iteration.

**Numerics rule.** For every value except `ok` and `infeasible`, the payload's numeric
fields are `null` — never `0`, never omitted. `percent_consumed` is `null` for
`infeasible` as well. The single carve-out is the valuation endpoint's `preview` key,
where the computable state `not_evaluated` carries fully computed
`production_budget_minor` and `allowed_worker_minutes`.

---

## `item_binding` — how the evaluation relates to the task's item

Reported alongside the status on the budget-status endpoint.

| Value | Meaning |
|---|---|
| `bound` | The task has an active PRIMARY item and no committed evaluation names a different one |
| `detached` | The task has no active PRIMARY item |
| `mismatched` | A committed evaluation exists and names a different item than the task's current PRIMARY |

`mismatched` is the interesting one: the item on the task changed after the economics
were committed. The committed figures still describe the item they were committed for.

---

## The evaluation chain

An evaluation is either `committed` or a `projection`, and the two never mix.

```
                    ┌─────────────┐
   commit ─────────►│  committed  │◄──────── promote
                    │  (current)  │
                    └──────┬──────┘
                           │  a newer commit lands
                           ▼
                    ┌─────────────┐
                    │ superseded  │   superseded_at set, superseded_by_id → the new row
                    └─────────────┘

                    ┌─────────────┐
   project ────────►│ projection  │──── delete ───► soft-deleted
                    └──────┬──────┘
                           │ promote → creates a NEW committed row
                           ▼           carrying promoted_from_id;
                    (projection unchanged)
```

Rules the chain enforces:

- **At most one current committed evaluation per task** — a partial unique index is the
  arbiter, not application logic. Two racing commits produce
  `ITEM_COST_CONCURRENT_COMMIT` (409) for the loser.
- **Committed rows are never deletable.** There is no delete path in the API or the code.
- **Superseding never edits.** The old row keeps every figure it was committed with;
  `superseded_at` and `superseded_by_id` are the only fields that change.
- **Promotion does not mutate the projection.** It runs the same commit procedure and
  stamps `promoted_from_id` on the new committed row.
- **Projections are read by nothing operational** — not worker surfaces, not analytics,
  not the result row.

The valuation chain works identically: one current row per item, a change writes a
superseding row, superseded rows are immutable, and the current row is the only deletable
one.

---

## The result row's lifecycle

`item_cost_results` is **not** written once at the end. It is a continuously-converging
snapshot of the episode's economics, **recomputed and SET at every lifecycle boundary**.

"Final" is not a flag — it is `task_state_snapshot` being terminal with `task_closed_at`
set.

### Emission points — the complete list

Every one enqueues the same `PROCESS_ITEM_COST_RESULT` execution task, which the analytics
worker handles.

| # | Boundary | Where |
|---|---|---|
| 1 | Every sanctioned entry into READY | `maybe_evaluate_task_ready` — the only route into READY, so all its callers inherit the emit |
| 2 | Every reopen back to WORKING | `maybe_reopen_task_to_working` |
| 3 | The three terminal transitions | `resolve_task`, `fail_task`, `cancel_task` |
| 4 | Time that settles after a boundary | `handle_process_step_transition`, after the time rollup, **iff** the step's task is READY or terminal |

Point 4 is what keeps the row honest: a worker who closes a straggling step after the task
was resolved changes the task's working seconds, and without a re-emit the stored result
would disagree with a live recompute forever, silently.

Redundant emissions are free — the handler recomputes and SETs, so running it twice with
no change in between is a no-op on every compared column.

### Handler admission — total over all eight task states

| Task state at handler time | Handler behaviour |
|---|---|
| `WORKING` | compute and upsert (admitted so the reopen refresh is honest) |
| `READY` | compute and upsert |
| `RESOLVED` | compute and upsert |
| `FAILED` | compute and upsert |
| `CANCELLED` | compute and upsert |
| `PENDING` | log and return, writing nothing |
| `ASSIGNED` | log and return, writing nothing |
| `STALLED` | log and return, writing nothing |

No v1 emission point can fire in the bottom three. The refusal exists so a replayed or
operator-re-emitted event cannot fabricate a result for an episode that never started.

The handler also returns without writing when the task is soft-deleted, or when there is
**no current committed evaluation** — it writes and deletes nothing in that case, rather
than storing zeros.

### Idempotency and replay

`unique (task_id)` is the idempotency key, and the write is
`INSERT … ON CONFLICT (task_id) DO UPDATE`. There is no other dedupe key and no
delivery-count assumption.

Because the evaluation is resolved **at handler time**, a commit that lands between a
boundary and the handler run is picked up by that run or by any later replay.

Replay identity is over this column set: `evaluation_id`, `item_id`,
`actual_worker_seconds`, `actual_worker_minutes`, `consumed_cost_minor`,
`variance_worker_minutes`, `variance_cost_minor`, `task_closed_at`,
`task_state_snapshot`, `calculation_version`. **`computed_at` is refreshed on every
recompute and is excluded from every identity assertion**, as is any `updated_at`-shaped
column.

For any interleaving of READY entries, reopens, terminal transitions and straggler
settlements, the stored row equals the handler's recompute at the last-fired boundary. A
task that re-reaches READY after a reopen converges onto the new totals with no special
case — there is no delete path anywhere in this lifecycle.
