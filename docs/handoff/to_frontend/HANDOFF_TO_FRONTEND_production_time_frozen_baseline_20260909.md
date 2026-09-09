# HANDOFF_TO_FRONTEND_production_time_frozen_baseline_20260909

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_production_time_frozen_baseline_20260909`
- Created at (UTC): `2026-09-09T11:40:00Z`
- Owner agent: `Claude`
- Source plan: owner-ratified direct implementation, raised from a live payload where the
  production-time card rendered "7h29m worked, of 6h43m, over by 3h26m".
- This is an **addendum** to
  `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`. It adds one key
  inside `final` and supersedes nothing.

## Backend delivery context

`GET /api/v1/item-economics/tasks/{task_client_id}/production-time` returns two blocks
that describe the same worked time:

- `budget` — recomputed at request time from the **current committed evaluation**.
- `final` — the stored `item_cost_results` row, frozen at the episode's last boundary.

`final.variance_worker_minutes` is `allowed - actual` **against the allowance that was
current when the row was written**, and that allowance was never published. A card that
pairs `budget.allowed_worker_minutes` (Y) with `final.variance_worker_minutes` (Z)
therefore straddles two baselines, and on `tsk_01KXX4NWRCGRAC0VJNP44JQHPS` it rendered as
449.78 worked, of 403.20 allowed, over by 206.82 — arithmetically impossible on its face.

Two things changed.

**1. The drift itself is fixed.** Committing an evaluation is now a result boundary: it
enqueues the same `PROCESS_ITEM_COST_RESULT` recompute that task-state transitions do,
whenever the task is `working` or `ready`. Before this, the recompute fired only on state
transitions, so re-pricing a `ready` task moved the live allowance and left the stored row
frozen against the superseded one — for a task that may never transition again, forever.
Promotion of a projection inherits the emit (it runs the same commit procedure);
projections themselves emit nothing.

The reconciliation is asynchronous — the analytics worker handles the queued task — so a
read taken between the commit and the recompute can still show the two blocks disagreeing.
That window is the reason for the second change.

**2. `final` now publishes its own baseline**, so the frozen trio is self-consistent
whatever the live block says.

## Frontend action required

1. **New key inside `final`**: `"allowed_worker_minutes_snapshot"` — a decimal string, the
   allowance `final`'s own `variance_worker_minutes` and `percent_consumed` were computed
   against. Additive; every other key in `final` is unchanged, and `final` stays money-free.

   ```json
   "budget": {
     "allowed_worker_minutes": "403.20",
     "actual_worker_seconds": 26987,
     "actual_worker_minutes": "449.78",
     "remaining_worker_minutes": "-46.58",
     "percent_consumed": "111.55"
   },
   "final": {
     "actual_worker_minutes": "449.78",
     "allowed_worker_minutes_snapshot": "242.96",
     "variance_worker_minutes": "-206.82",
     "percent_consumed": "185.13",
     "task_state_snapshot": "ready",
     "computed_at": "2026-09-03T15:22:29.707477+00:00"
   }
   ```

2. **Never mix the two blocks in one sentence.** Inside `final`,
   `allowed_worker_minutes_snapshot - actual_worker_minutes == variance_worker_minutes`
   holds exactly, and `percent_consumed` is that same pair. Inside `budget`, the same
   identity holds with `remaining_worker_minutes`. Across the two it holds only when they
   agree. Stop inverting `actual + variance` to recover the baseline — read the key.

3. **`allowed_worker_minutes_snapshot` is present whenever `final` is.** It is never null
   while `final` is an object; `final` itself is still `null` for a task with no stored
   result row.

## Which one is authoritative

- **The live `budget` block is authoritative for the allowance.** It is the only block that
  reflects a re-price at all.
- **`final` is authoritative for what the episode's economics were at its last boundary.**
  It is the analytics record and the only block that does not move under the reader.

For a **closed (terminal) task** the question does not arise: commits are refused once a
task is terminal (`ITEM_COST_TASK_TERMINAL`) and no further time accrues, so the last
boundary's recompute is the final word and the two blocks carry the same numbers. Display
either — prefer `final`, since it is the one that cannot tick.

For a **non-terminal task** — `ready` above all, which is what a "closed card" usually
renders — `budget` is what the manager is deciding against and `final` is history. If you
show both, label the frozen pair with its own baseline
(`allowed_worker_minutes_snapshot`); if you show one, show `budget`.

## Not in this delivery

`GET /tasks/{task_client_id}/budget-status` has the same straddle in its `result` block and
does **not** yet carry `allowed_worker_minutes_snapshot`; its envelope is fixed by
`HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`, and adding the key there is a
separate addendum. Until then, `result.actual_worker_minutes + result.variance_worker_minutes`
is that block's frozen baseline.

Existing `item_cost_results` rows are **not** backfilled by this change. A stale row
converges on its task's next boundary — including any future commit. The one-shot
reconciliation is
`python3 -m scripts.backfill.reconcile_stale_item_cost_results --execute`
(dry-run by default); it recomputes through the production handler, so historical rows can
be reconciled on demand rather than left to drift.
