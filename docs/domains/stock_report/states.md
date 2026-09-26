# Stock Report — states, cascades and soft deletes

Living document for the `stock_report` domain (`architecture/23_documentation.md`,
`25_soft_delete.md` — "document the cascade strategy in `states.md`"). Written from
the shipped code; `app/tests/unit/docs/test_stock_report_docs.py` fails when the six
assignment states drift from `StockTaskAssignmentStateEnum`.

## 1. The assignment state machine

An assignment binds one stock-report row to one (task, item) pair. Its state is a
projection of the task's state, except for the two exits Scanner owns.

| State | Active or terminal | Counter it feeds | Who writes it |
|---|---|---|---|
| `in_queue` | active | `quantity_in_queue` | creation (`POST /assignments`), and the task-state sync |
| `in_progress` | active | `quantity_in_progress` | the task-state sync |
| `awaiting` | active | `quantity_awaiting` | the task-state sync |
| `resolved` | terminal | — | **Scanner only**, through the items-processed webhook, and only from `awaiting` |
| `failed` | terminal | — | the task-state sync, from any active state |
| `resolved_early` | terminal | — | **Scanner only**, through the items-processed webhook, from `in_queue` or `in_progress` |

`ACTIVE_ASSIGNMENT_STATES` and `TERMINAL_ASSIGNMENT_STATES` are the two frozensets
that partition the enum. Every predicate, branch and recomputation that asks "is this
active" reads one of them; a hand-typed state list is a review finding (master plan
§9 rule 16) — that rule exists because `resolved_early` was added after ten phases
were planned, and every hand-typed terminal list would have counted it as active.

**What `resolved_early` means on the board.** The physical item was processed by
Scanner while the assignment was still `in_queue` or `in_progress` — the task was
never marked ready. Its units leave the counters, the goal keeps its credit, the task
is untouched and still running, and the assignment is kept as the trace of what
happened. It is a success state, not an error; `resolved` is the same success reached
along the expected path, from `awaiting`.

**Allowed moves** (`_move_assignment._assert_allowed_move`): creation enters any
active state; an active state moves to any other active state, to `failed`, or to its
Scanner exit; a terminal state moves nowhere; any state may be soft-deleted. Anything
else raises `IllegalAssignmentMove`, which is a programming error (500), never a
domain error.

**Counters are a cached projection.** Each move applies one guarded,
column-referencing `UPDATE … RETURNING` with `-q` on the state it leaves and `+q` on
the state it enters, and never an ORM attribute write. A move that would drive a
counter negative is the inline self-heal trigger: the counters are recomputed from the
live assignments, a `stock_report_repair_records` row is written with the trigger
`inline:<caller>` and the move proceeds.

## 1.5 The snapshot layer (2026-09-26)

The live tables above are Scanner's mirror. Everything a Manager user sees goes
through a **version**: `stock_report_snapshot_versions` holds at most one active
version per workspace (`uix_stock_report_snapshot_versions_active`, a partial unique
index on `closed_at IS NULL`), and `stock_report_item_snapshots` holds one row per
live stock-report row inside it.

- `quantity_requested` on the snapshot is **frozen** at creation. The row's own keeps
  following Scanner.
- The snapshot's three counters are **derived from the row while the snapshot is
  active** (the serializer reads the row) and **frozen from the row when it closes**
  (`create_stock_report_snapshot_version`'s freeze, or the deletion cascade). No
  assignment move writes the counters on the snapshot table.
- **Completion never decrements on resolve** (owner ruling, addendum 2026-09-26):
  `quantity_resolved` on the snapshot is the sum of the quantities of the row's
  assignments that reached `resolved` / `resolved_early` while the snapshot was
  active — credited by `_snapshot_resolved.credit_snapshot_resolved` from
  `resolve_processed_group` (the processed webhook) and from `move_assignment` on a
  terminal target. Monotonic, never frozen or zeroed. The **wire** `quantity_awaiting`
  is the live/frozen awaiting **plus** `quantity_resolved`; it still falls when an
  assignment leaves awaiting for anything but resolved (MC-5 parity). It is not
  recomputable (assignments carry no resolved timestamp), so no consistency kind
  covers it. The processed webhook therefore takes the snapshot lock class between
  rows and assignments (MC-1 order).
- A version's **progress** (`GET …/snapshots/versions/active`, and per row of
  `GET …/snapshots/versions`) is computed over its prioritised snapshots whose row is
  not deleted: target `Σ max(0, requested − missing)`, done `Σ min(target, awaiting)`
  with the wire awaiting above; live counters while a snapshot is active, frozen ones
  once closed (the per-snapshot `closed_at`, the serializer's own test).
- `priority` / `priority_order` live on the snapshot, never on the row (the columns
  were dropped). A group is `(workspace_id, priority)` over **active** snapshots;
  the two `PATCH` ordering routes take the row's id and move its active snapshot.
  `ck_stock_report_item_snapshots_priority_order_pairing` makes a half-null position
  unstorable, so there is no `priority_order_nullness` check any more.
- `quantity_missing` is bounded by `max(0, quantity_requested − (in_queue +
  in_progress + awaiting + quantity_resolved))` and is **clamped down** by `move_assignment` on an
  assignment's creation — the only move that raises the covered quantity. A new
  version starts it at 0.
- Opening a version closes the previous one in the same transaction and takes
  every live row `FOR UPDATE` for its duration; a concurrent Scanner demand webhook
  can hit its `lock_timeout` and retry. Accepted.

## 2. Soft-delete predicates

| Entity | Live means |
|---|---|
| `stock_report_items` | `is_deleted = false`. The unique identity index `(workspace_id, item_category_id, properties_signature)` is partial on the same predicate, so a soft-deleted row never blocks a new one with the same identity |
| `stock_task_assignments` | `is_deleted = false`; the two "one active per item / per task" unique indexes additionally require an active state |
| `stock_report_history_records` | `is_deleted = false` |
| `stock_report_repair_records` | no soft-delete columns — repair records are append-only and are removed only by the workspace reset |
| `stock_report_snapshot_versions` | no soft delete: **closing is the lifecycle**. Active means `closed_at IS NULL`; a closed version is immutable history that `apply-priorities` can copy from |
| `stock_report_item_snapshots` | no soft delete. Active means `closed_at IS NULL` (`uix_stock_report_item_snapshots_row_active`: at most one per row). It closes with its version, or alone when its row is deleted mid-version |

An absent row, a soft-deleted row and a row in another workspace are **one** answer on
every read: `404`. A soft-deleted row is outside the live-identity predicate, so the
next Scanner demand for that identity creates a **new** row rather than reviving it.

## 3. Cascade strategy

### 3.1 Row deletion — by a user and by Scanner

`cascade_delete_stock_report_item` is the one implementation, with two callers: the
user-facing `DELETE /api/v1/stock-report/items/{client_id}` (phase 13) and the Scanner
delete webhook (phase 13A). It takes every stamp value as an argument and reads no
request context, so the Scanner caller passes `actor_user_id=None` and the whole
cascade stamps NULL authorship — a Scanner-caused change records no one.

In order:

1. every non-deleted assignment of the row, ascending `client_id`, is removed through
   `remove_assignment` — the counter statement, the goal step, the task-flag
   recompute, one `stock_task_assignment:deleted` event each. **Assignments in every
   state go**, terminal ones included;
2. the second self-heal trigger runs **once**, after the loop: each counter's
   recomputed value is now 0, and a non-zero stored value is drift — repaired with a
   record, and the deletion proceeds;
3. the row's **active snapshot** closes its priority group's gap: every active
   snapshot ordered after it moves down one, and each shifted neighbour emits
   `stock_report_item_snapshot:updated`; the snapshot is then closed (`closed_at`,
   counters frozen at 0) and **keeps its own `priority` and `priority_order`** — it is
   outside every group now, so its position is a historical fact. The version stays
   open;
4. the row is soft-deleted;
5. its history records are soft-deleted (`deleted_*` only — they carry no `updated_*`
   columns);
6. one `stock_report_item:deleted`. The coalescer drops any `:updated` for a row that
   also carries a `:deleted` in the same request.

**Tasks, task steps and items are never touched** by this cascade. The only write it
makes outside the stock-report tables is the tasks' `is_stock_assignment` flag, which
is recomputed per task and set with a self-assigning `updated_at` so no task timestamp
moves.

The Scanner delete webhook may delete **several** rows in one request. It takes the
locks once — the ordering advisory lock, then tasks, then the candidate rows, then
their active snapshots together with every active snapshot of their priority groups,
then the assignments — and then runs one cascade per row in ascending `client_id`. Each cascade closes its own gap against the
positions the previous one left, so two rows of the same group both end correct.

### 3.2 Task deletion, PRIMARY unlink, item deletion

A task's deletion, the removal of a task's PRIMARY item, and an item's deletion each
remove the affected assignments through the same `remove_assignment` operation, with
the deleting user as the author. The stock-report row itself survives — only its
assignments go, and its counters fall by their quantities.

### 3.3 Category changes

An item that holds a live stock-report assignment cannot change its item category:
the guard raises `Unassign this item from the stock report before changing its
category.` on both item writers.

### 3.4 The workspace reset

`reset_app` deletes the four stock-report tables **first**, before `delete_tasks` —
repair records, assignments, history records, rows, in that order. They are hard
deletes and they take soft-deleted rows with them, which is what keeps the FK
`RESTRICT` on `tasks` and `items` satisfiable.

## 4. Events

| Event | `extra` |
|---|---|
| `stock_report_item:created` | `{}` |
| `stock_report_item:updated` | `quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting` |
| `stock_report_item:deleted` | `{}` |
| `stock_report_item_snapshot:updated` | `stock_report_item_id`, `version_id`, `priority`, `priority_order`, `quantity_missing`, `quantity_resolved` — `client_id` is the **snapshot's** |
| `stock_report_snapshot_version:created` | `snapshot_count` — `client_id` is the version's |
| `stock_report_snapshot_version:closed` | `snapshot_count` |
| `stock_task_assignment:created` | `stock_report_item_id`, `task_id`, `state` |
| `stock_task_assignment:state-changed` | the same three |
| `stock_task_assignment:deleted` | the same three |

`state` carries any of the six values in §1. `workspace_id` on every event comes from
the entity's own row, never from the request context — the webhook paths have no
workspace in their context at all.

Events are built after the transaction block exits normally, from committed values,
and dispatched once per request by the owning command. Within one request the
coalescer keeps the net change per entity: the last `:updated` per row (and per
snapshot), dropped entirely when the payload equals the entity's initial values, when
the same row also carries a `:created` or a `:deleted`, or — for a snapshot — when its
row is deleted in the same request.
