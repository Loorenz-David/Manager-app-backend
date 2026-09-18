# Intention: Stock Report — Scanner demand turned into Manager work

```
status: COLLABORATING — 7 owner cards open (§17); NOT ratified
role: intention (pipeline root artifact)
shaped_from: raw_intention.md (this folder; its content and the owner's answers are preserved in Appendix A)
source_evidence: scanner_source_evidence.md (this folder) — cited below as E1…E6
date: 2026-09-18
round: 0 (initial grounded shaping)
```

Paths are relative to `backend/`. `app/beyo_manager/` is abbreviated `bm/`.

---

## ⚠ OWNER DECISIONS REQUIRED (7)

The seven cards are in **§17**. Everything else in this document is either the owner's own
statement (raw intention + answers), a fact read from the repository, or a **proposal of mine**
— every proposal is listed once, in §16, so it can be struck without reading the whole document.

---

## 1. Objective & hard constraints

Scanner knows what stock is missing. Manager knows who is repairing what. Stock Report joins the
two: each Scanner stock requirement becomes a row on a Manager board, existing task+item pairs are
assigned to that requirement, and the row shows — live — how many are queued, being worked, and
finished-but-not-yet-confirmed by Scanner. History keeps the evolution of the goal.

> Scanner communicates demand. Manager coordinates the work that satisfies it. Assignment state is
> the workflow source of truth. Cached quantities make reads cheap. History preserves the goal.

**Hard constraints**

- **HC-1 — Scanner owns demand.** `quantity_requested` is written only by the Scanner demand
  webhook, always as an absolute value, never as a delta. No Manager user or job writes it
  (pending card 4 for the one possible exception).
- **HC-2 — Assignment state is the truth; counters are a cache.** `StockTaskAssignment.state` is
  authoritative. The three workflow counters are persisted projections, changed only by an
  assignment state change (or creation/deletion), in the same transaction, and always
  reconstructable from the assignments.
- **HC-3 — No counter arithmetic outside the transition operation.** One domain operation owns
  "move an assignment from state A to state B and move the counters with it". Task sync, the
  Scanner webhook, creation, deletion and any repair tool all go through it.
- **HC-4 — Sync follows the task's resulting state.** The assignment is set from what the task
  *is* after a commit, never from an assumed path; `pending → ready` must land in `awaiting`.
- **HC-5 — Replays change nothing.** Delivering any Scanner request twice leaves the database
  exactly as delivering it once.
- **HC-6 — Workflow quantities are never capped by demand.** `quantity_in_queue >
  quantity_requested` is valid.
- **HC-7 — Backend only.** No frontend work. The frontend and the Scanner-side sender each
  receive a published contract (§11), nothing more.

---

## 2. Grounding — what exists today (verified 2026-09-18)

### 2.1 Conventions the new tables must follow
- Every model is `class X(IdentityMixin, Base)` with a `CLIENT_ID_PREFIX`; the primary key is the
  string `client_id` (`bm/models/base/identity.py`). **All foreign keys are `String(64)` to
  `<table>.client_id` with `ondelete="RESTRICT"`** — the raw draft's `int` ids do not exist here.
- Every domain table carries `workspace_id` (`architecture/24_multi_tenancy.md`); every query
  filters on it first. Each new prefix is registered in `bm/models/tables/client_id_prefix_map.md`.
- Enums live in `bm/domain/<domain>/enums.py`; columns use the `configure_sa_enum_values` wrapper
  so Postgres stores `.value` (`bm/models/base/sa_enum.py`).
- Soft delete is the default (`architecture/25_soft_delete.md`): `is_deleted`, `deleted_at`,
  `deleted_by_id`; child handling must be an explicit choice; DB cascade is never relied on.
- Commands own one transaction through `maybe_begin` (`architecture/06_commands_local.md`);
  subordinate operations never open a transaction and never dispatch events; events are
  dispatched after the block exits (`architecture/11_infra_events.md`).

### 2.2 Items and categories
- `ItemCategory` (`bm/models/tables/items/item_category.py`): `name` unique per workspace,
  `major_category` (`ItemMajorCategoryEnum`: `wood`, `seat`). The only existing match-by-name
  precedent is case-insensitive (`bm/services/queries/items/lookup/purchase_api.py:132`).
- `Item` (`bm/models/tables/items/item.py`): `article_number` is **unique per workspace among
  non-deleted items** (`uix_items_workspace_article_number`) but nullable; `quantity` Integer
  default 1 (a set of 8 chairs is one item with quantity 8); `properties` JSONB +
  `properties_signature`.
- `compute_properties_signature` (`bm/domain/items/properties_signature.py`): recursive key sort,
  byte-stable JSON, sha256 hex (64 chars). Values verbatim; **list order is significant**. It is a
  pure function with no Item coupling — reusable as is. The Item-side writer
  (`_properties_snapshot.py`) treats `{}` as "no snapshot"; that rule is Item-specific and is
  **not** reused.

### 2.3 Tasks, their items, and their states
- A task has **at most one active PRIMARY item and any number of RELATED items**
  (`bm/models/tables/tasks/task_item.py`, `uix_task_items_primary_active`). "A task has one item"
  in the raw draft is true only of the PRIMARY item.
- `TaskStateEnum` (`bm/domain/tasks/enums.py`): `pending, assigned, working, stalled, ready,
  resolved, failed, cancelled`. `TERMINAL_TASK_STATES = {resolved, failed, cancelled}`
  (`bm/domain/task_steps/constants.py`). **`cancelled` is live** — `cancel_task.py` writes it.
  `stalled` is never written by any command today.
- **Terminal tasks never reopen.** `resolve_task`, `fail_task`, `cancel_task`, `add_task_steps`
  and `force_task_ready` all refuse a terminal task. The only backward move is `ready → working`
  (`maybe_reopen_task_to_working`). The raw draft's `resolved → working` does not exist.
- **There is no single place where task state changes.** `Task.state` is assigned at:

  | Site | Writes |
  |---|---|
  | `bm/services/commands/tasks/_task_state_transitions.py` `maybe_advance_task_to_working` | `assigned → working` |
  | same file, `maybe_reopen_task_to_working` | `ready → working` |
  | same file, `maybe_evaluate_task_ready` | `* → ready` (the only sanctioned entry to `ready`) |
  | `bm/services/commands/tasks/resolve_task.py` | `→ resolved` |
  | `bm/services/commands/tasks/fail_task.py` | `→ failed` |
  | `bm/services/commands/tasks/cancel_task.py` | `→ cancelled` |
  | `bm/services/commands/task_steps/add_task_steps.py` | `pending → assigned` |
  | `bm/services/commands/task_steps/remove_task_step.py` | `→ pending` |
  | `bm/services/commands/tasks/create_task.py` | initial state |

  The three helpers are reached from `transition_step_state.py`, `_step_transition_core.py`
  (batch + case-pause), `finalize_pending_step_completion.py`, `force_task_ready.py`,
  `add_task_steps.py`, `remove_task_step.py`. The per-step transition body itself exists in three
  mirrored copies by recorded decision (graph node `decision-mirrored-transition-body`).
- Two task-side events the raw draft does not mention also end the pairing the assignment rests
  on: `delete_task.py` (soft delete) and `remove_item_from_task.py` / `add_item_to_task.py`
  (the PRIMARY item can be removed or replaced).

### 2.4 Concurrency, ordering, batches
- House style for denormalized counters is an atomic column-referencing UPDATE
  (`col = col ± n`, `func.greatest(col - n, 0)` on decrement) in the causing transaction
  (`bm/services/commands/cases/message_writes.py`, `soft_delete_message.py`);
  `architecture/32_concurrency.md` names read-then-assign of an aggregate as a defect and offers
  `SELECT … FOR UPDATE` for shared counters.
- User ordering precedent: `set_user_working_sections_order.py` + `_membership_ordering.py`
  (`max + 1` append). Dense order is an **application invariant with no unique constraint**,
  because row-by-row reorders collide transiently (`working_section_membership.py:24-26`).
- Every batch command is all-or-nothing in one transaction, validates references by set
  difference, and names the missing ids (`batch_create_item_issues.py`).

### 2.5 Inbound webhooks
- Webhook routers build `ServiceContext(identity={})`, so **`ctx.workspace_id` is `""`** on those
  paths and must never be read. No default-workspace setting exists; the two existing webhooks
  derive the workspace from an integration row (Shopify) or a mapped worker (Connecteam).
- Static-secret precedent: `bm/services/infra/connecteam/webhook_verifier.py` —
  `hmac.compare_digest`, 401 on mismatch, auth strictly before parsing or any write.
- `bm/routers/api_v1/location_tracker.py` already exists and is the **user-facing** proxy to
  Scanner (JWT roles). `LOCATION_TRACKER_API_KEY` in `bm/config.py` is the **outbound** key.

### 2.6 Serialization and tests
- Read layer serializes inside the query service (`architecture/46_serialization_local.md`);
  `serialize_image_light` is `bm/domain/images/serializers.py:49`; item images are batch-loaded
  per page in one query (`bm/services/queries/tasks/tasks.py:432-448`).
- The suite lives in `app/tests/` and runs from `app/` (`make test`; xdist `-n 6 --dist loadfile`,
  one isolated database per process). Command tests build a module-local `_ctx` and monkeypatch
  `dispatch` at the consumer's import site.

---

## 3. Core workflow

```
Scanner ──demand webhook──▶ find-or-create StockReportItem, set quantity_requested
                             └─ increase? → new goal history record

Manager user ──assign task──▶ StockTaskAssignment (state derived from the task's current state)
                             └─ counters move with it

any task state change ─────▶ assignment re-derived from the task's resulting state
                             └─ counters move; entry into awaiting feeds the goal record

Scanner ──processed webhook (article_number)──▶ awaiting → resolved; quantity_awaiting − 1
```

---

## 4. Domain model

New package `bm/models/tables/stock_report/`, enums in `bm/domain/stock_report/enums.py`.
Every table: `workspace_id`, `client_id`, `created_at`, soft-delete trio.
Field ownership legend — **S** Scanner webhook · **U** Manager user · **Sys** system-derived.

### 4.1 `StockReportItem`

| Field | Type | Writer | Rule |
|---|---|---|---|
| `item_category_id` | FK `item_categories.client_id` | S at creation | immutable after creation |
| `properties` | JSONB, not null | S at creation | immutable; `{}` is a valid value (a category-only requirement) |
| `properties_signature` | String(64), not null | Sys | always `compute_properties_signature(properties)`; never accepted from a caller |
| `quantity_requested` | int ≥ 0, default 0 | **S only** | absolute set; nothing else may overwrite it |
| `quantity_in_queue` / `quantity_in_progress` / `quantity_awaiting` | int ≥ 0, default 0 | **Sys only** | projections (HC-2); DB check `>= 0` |
| `priority` | `high/medium/low`, nullable, default null | U | never written by Scanner |
| `priority_order` | int, nullable | Sys (from U actions) | §7 |

- **No stored `item_major_category`.** It is derived from `ItemCategory.major_category` at read
  time; storing it would be a second copy of a fact (raw §6 listed it as a field, §6.1 called it
  derivable — resolved to derivable).
- **Identity:** at most one non-deleted row per `(workspace_id, item_category_id,
  properties_signature)` — a partial unique index. Find-or-create must be safe under two
  concurrent deliveries of the same new identity.
- A soft-deleted row never blocks a new row of the same identity; a later Scanner delivery
  creates a fresh row with empty history.

### 4.2 `StockTaskAssignment`

| Field | Type | Writer | Rule |
|---|---|---|---|
| `stock_report_item_id` | FK | U at creation | immutable |
| `task_id` | FK `tasks.client_id` | U at creation | immutable |
| `item_id` | FK `items.client_id` | Sys at creation | the task's active PRIMARY item at that moment; immutable |
| `state` | `StockTaskAssignmentStateEnum` | Sys | only through the transition operation (HC-3) |

`StockTaskAssignmentStateEnum`: `in_queue, in_progress, awaiting, resolved, failed`.
Active = `{in_queue, in_progress, awaiting}`. `resolved` and `failed` are **terminal**: nothing
moves an assignment out of them.

- **One active assignment per item:** partial unique index on `(workspace_id, item_id)` where
  state is active and the row is not deleted. Since a task has one PRIMARY item, this also means
  at most one active assignment per task.
- A terminal assignment never blocks a new one for the same item.

### 4.3 `StockReportHistoryRecord`

`type` (`quantity_requested_change | priority_change | priority_order_change`),
`quantity_requested`, `quantity_awaiting`, `priority`, `priority_order`, `created_at`,
`stock_report_item_id`. Append-only except the one field in §6.2. All Sys-written.

### 4.4 `Task.is_stock_assignment`

Boolean, not null, default false, Sys-written. **True exactly when the task has at least one
non-deleted `StockTaskAssignment`, in any state.** Its purposes: cheap task filtering later, and a
cheap skip for task sync on the vast majority of tasks.

---

## 5. Assignment state — the complete mapping

The assignment's state is a function of the task's resulting state (HC-4):

| Task state | Assignment state | Why |
|---|---|---|
| `pending` | `in_queue` | nothing started |
| `assigned` | `in_queue` | steps exist, no work started |
| `working` | `in_progress` | |
| `stalled` | `in_progress` | started and not complete; no command writes it today, mapped so the function is total |
| `ready` | `awaiting` | Manager's work is complete |
| `resolved` | `awaiting` | Manager's work is complete |
| `failed` | `failed` | owner answer |
| `cancelled` | `failed` | owner answer |

Rules:
1. Sync applies only to **active** assignments. A `resolved` or `failed` assignment ignores every
   later task change (e.g. Scanner resolves the item, then the task is reopened `ready → working`:
   the assignment stays `resolved`; putting the item back on the board is a new assignment).
2. `awaiting → resolved` is performed **only** by the Scanner processed webhook, and only from
   `awaiting`.
3. Creation derives the state from the task's state at that moment through the same mapping and
   the same operation — a task already `working` yields `in_progress`, with the counters moved by
   the operation, not written by hand. Creating an assignment for a task that is `failed` or
   `cancelled` is refused.
4. Every committed change of `Task.state`, from every site in §2.3, is reflected on the task's
   active assignment **in the same transaction**. A new state-writing site added later without the
   sync must be caught by a guard that is proven able to fail.
5. Counter effect of any move A → B: `−1` on A's counter if A is active, `+1` on B's counter if B
   is active. Creation is "nothing → B"; deletion is "A → nothing".

---

## 6. History semantics

### 6.1 When a record is written
| Event | Record |
|---|---|
| `quantity_requested` set to a value **greater** than the previous one (creation counts as previous = 0) | one `quantity_requested_change` — a new **goal record** |
| set to an equal or smaller value, including 0 | none |
| user changes `priority` | exactly one `priority_change` (it carries the new `priority_order` too — no second record) |
| user moves the item within its group | one `priority_order_change`, **for the moved item only**; neighbours that shift get none |

Each record snapshots `quantity_requested`, live `quantity_awaiting`, `priority`,
`priority_order` as they are after the change — except that a goal record starts its
`quantity_awaiting` at **0**, because it counts work completed *during* that goal.

### 6.2 The accumulating field
The **current goal record** of an item is its most recent `quantity_requested_change` record.
When an assignment enters `awaiting`, the current goal record's `quantity_awaiting` increases by
one (how re-entries count: card 6). It never decreases when Scanner resolves. Priority records are
never touched after they are written. With no goal record yet (item created at 0), nothing
accumulates.

---

## 7. Priority and ordering

- `priority = null ⇔ priority_order = null` (owner answer). New items are created with both null;
  there is no default priority — null is the "needs triage" signal.
- Within each `(workspace, priority)` group of non-deleted items, `priority_order` is exactly
  `1..n` with no gaps and no duplicates (owner answer), enforced by the commands, not by a unique
  constraint (§2.4).
- Changing priority: the item leaves its group (the group closes the gap) and is appended to the
  destination group at `max + 1` (1 when empty). Changing to null clears the order.
- Changing order: a single item moves to a target position `1..n`; the items between shift by one.
  A target outside `1..n` is a validation error.
- Deleting an item closes the gap in its group.
- Complete read order: `high`, then `medium`, then `low`, each by `priority_order` ascending.
  Null-priority items are ordered by `created_at` ascending, then `client_id`.

---

## 8. Scanner webhooks

New router file `bm/routers/api_v1/location_tracker_webhooks.py` (the existing
`location_tracker.py` stays the user-facing proxy).

**Auth.** Header `x-api-key` (what Scanner already sends to its targets — E4), compared in constant
time with the new setting `MANAGER_API_KEY_TO_LOCATION_TRACKER_APP`. Missing or wrong key → 401
before any parsing or write. **Setting absent → every request is refused** (fail closed).
Workspace: card 3.

**Batches are atomic** (owner answer): any invalid entry rejects the whole request and nothing is
written; the error names every offending entry.

### 8.1 Demand — `[{itemCategory, properties, quantityRequested}]`
- `itemCategory` is a category **name** (E1), matched case-insensitively against non-deleted
  `ItemCategory.name` in the workspace. **Unknown name → the whole batch is rejected**, naming the
  unknown categories. Manager never auto-creates a category (it could not know `major_category`).
- `properties` must be a JSON object (`{}` allowed); `quantityRequested` an integer ≥ 0.
- Two entries in one batch that resolve to the same identity → the batch is rejected (otherwise
  the later one silently overwrites the earlier — see card 1).
- An identity absent from a batch is left untouched; absence is not a zero.
- Per entry: find-or-create, set `quantity_requested`, apply §6.1.

### 8.2 Processed — `[{article_number}]`
- Resolve the non-deleted `Item` by `article_number` in the workspace (unique — §2.2), then its
  active assignment (at most one — §4.2).
- Assignment in `awaiting` → `resolved`.
- **Anything else is a no-op, not an error**: unknown article number, no assignment, assignment
  `in_queue`/`in_progress`, already `resolved`/`failed`. Reason: a retry of a successful call is
  indistinguishable from "nothing eligible", so treating it as an error would break HC-5 — and
  Scanner will report placements for many items that were never assigned here.
- The response reports, per article number, `resolved` or `ignored` with a reason.
- An item with no article number (E6) cannot be resolved by this webhook; it stays `awaiting`
  until its assignment is deleted by a user.

---

## 9. Local Manager API (`bm/routers/api_v1/stock_report.py`)

| Operation | Notes |
|---|---|
| create StockReportItem | card 4 |
| delete StockReportItem | soft-deletes the item, its history, and — through the assignment delete operation — every assignment, so counters and task flags stay right throughout |
| change priority · change priority_order | two separate endpoints (§7) |
| create assignments (batch) · delete assignments (batch) | all-or-nothing; request names tasks; item derived (§4.2); card 7 for the category check |
| GET StockReportItems | `priority=high,medium,low` filter; **omitted → only `priority IS NULL`** (owner answer); unpaginated; order per §7 |
| GET StockTaskAssignments | by StockReportItem `client_id`; non-deleted, all states |

Assignment deletion: removes the assignment's counter contribution if active, soft-deletes it,
recomputes `Task.is_stock_assignment` (§4.4), atomically.

Response shapes: StockReportItem carries the four quantities, priority, order, `properties`, and
an **`item_category`** object `{client_id, name, major_category}` — the raw draft's `item_type`
/ `type_name` naming is dropped so no "ItemType" concept leaks ahead of the Item Domain migration.
Assignment carries `client_id`, `state`, `stock_report_item_id`, `item`, `task` using two new
serializers, `serialize_item_compact` (client_id, article_number, sku, quantity,
item_category_snapshot, item_major_category_snapshot, item_images via `serialize_image_light`,
images batch-loaded once per response) and `serialize_task_compact` (client_id, task_type,
priority, state, title, return_source, ready_by_at, return_method, created_at, updated_at,
closed_at, completed_at). They are used only by this capability.

Roles: mutations `ADMIN, MANAGER`; reads `ADMIN, MANAGER, WORKER, SELLER`.

---

## 10. Facts vs derived values

| Layer | Values |
|---|---|
| Facts from Scanner | category, properties, `quantity_requested` |
| Facts from Manager users | priority, the choice to assign or unassign a task, deletions |
| Facts from the system | assignment `state` (derived from task state at write time, then stored as the workflow truth) |
| Derived, persisted | the three counters; `properties_signature`; `priority_order`; `Task.is_stock_assignment`; the goal record's `quantity_awaiting` |
| Derived, never stored | major category of a StockReportItem |

Every persisted derived value has a stated recomputation: counters = count of non-deleted
assignments by state; the flag = existence of a non-deleted assignment; the signature = the
function of `properties`. Missing data is never inferred: an unknown category is rejected, never
guessed.

---

## 11. External-source strategy

Scanner is the only external system and here it is the **caller**; Manager defines the contract.
Facts about Scanner are in `scanner_source_evidence.md`. The Scanner-side sender does not exist
yet and is not built by this project. This project publishes one handoff for the Scanner pipeline
(the two webhook contracts, the header, the atomic-batch and no-op rules) and one for the frontend
(local API). Tests never call Scanner.

---

## 12. Scope ladder

**Must ship**
1. The three tables, enums, `Task.is_stock_assignment`, migration.
2. The transition operation with counters (HC-2, HC-3).
3. Task-state sync at every site in §2.3, with its guard.
4. Assignment create/delete (batch) and StockReportItem delete.
5. Both Scanner webhooks with auth, atomic batches, idempotency.
6. Goal + priority history; priority and ordering commands.
7. The two GET endpoints and compact serializers.
8. A read-only consistency check that recomputes counters and flags from assignments and reports
   every divergence (it is also how M1 is measured).
9. The two handoff documents.

**Only if cheap** — realtime workspace events after each committed change; a repair mode for the
consistency check.

**Explicitly deferred / non-goals** — any frontend; the Scanner-side sender; migrating existing
task list endpoints to the compact serializers; taking over Scanner's stock rules, locations or
thresholds; automatic assignment of tasks to requirements; restore of deleted rows; pagination.

---

## 13. Measurement ledger

| ID | Observable outcome — measured true means this shipped | Defect family it guards |
|---|---|---|
| **M1** | After every committed operation, each StockReportItem's three counters equal the counts recomputed from its non-deleted assignments by state, and every `Task.is_stock_assignment` equals "has a non-deleted assignment" — including under concurrent transitions on the same item. | counter drift, lost updates, arithmetic applied outside the transition operation |
| **M2** | After a task's state changes by **any** path in §2.3, its active assignment's state equals the §5 mapping of the task's resulting state; terminal assignments are unchanged. | a missed integration site; assuming intermediate states; terminal assignments revived |
| **M3** | Replaying any Scanner request leaves the database identical to one delivery; `quantity_requested` equals the last value Scanner sent; a rejected batch leaves no trace. | double-applied transitions, delta-instead-of-absolute, partial batches |
| **M4** | Payloads differing only in JSON key order resolve to one StockReportItem; there is never more than one live row per identity, nor more than one active assignment per item — including under concurrent requests. | duplicate identities, signature instability, double-booking an item |
| **M5** | Goal records appear only on increases; a goal record's awaiting total never decreases when Scanner resolves; a priority change yields exactly one record; shifted neighbours yield none. | history that misstates the goal; duplicate or noisy records |
| **M6** | In every priority group, orders are exactly `1..n`; `priority` is null exactly when `priority_order` is null; the list endpoint returns the §7 order and, with no filter, only untriaged items. | gaps/duplicates after move, delete or priority change; wrong default listing |
| **M7** | A webhook request without the correct key, or with the key or workspace setting unconfigured, gets 401 and writes nothing. | an open or fail-open inbound endpoint |

Rank: M1, M2, M3 are the reason the capability exists; M4 protects identity; M7 protects the
boundary; M5, M6 protect meaning on the board.

---

## 14. Mechanism invariants already known (for mechanism-inventory to deepen)

1. **Transition operation** — inputs (assignment, target state or none), allowed moves, counter
   effect per §5.5, goal-record effect per §6.2, lock/atomic-update discipline. Silent-failure
   class: counters.
2. **Task-sync hook** — the enumerated sites of §2.3, the skip on `is_stock_assignment = false`,
   and the guard against a future unsynced site (must be shown to redden).
3. **Identity** — signature function reused unchanged; find-or-create under concurrent insert;
   partial unique indexes and their predicates.
4. **Ordering** — gap closing, append, single-item move; concurrent reorders in one group.
5. **Webhook boundary** — verifier, fail-closed configuration, workspace resolution, atomic batch
   validation order (auth → shape → references → writes).
6. **Soft-delete interplay** — every uniqueness, counter and ordering rule excludes deleted rows;
   an item or category soft-deleted while referenced.

---

## 15. Pre-implementation protocol

1. Owner answers the §17 cards; answers are folded here; status → READY_FOR_RATIFICATION.
2. Owner ratifies (explicit act, recorded in §18). Only then: mechanism-inventory.
3. Planner sizes phases at ≤ 8 criteria; every criterion traces to M1–M7 or a mechanism contract.
4. Graph: no Stock Report nodes exist yet (searched 2026-09-18); each phase records its delta.

---

## 16. My proposals — strike any that are wrong

Each is a resolution I made where the raw draft was silent or contradicted the repository.
Ratifying the document ratifies these.

| # | Proposal | Basis |
|---|---|---|
| P1 | String `client_id` foreign keys and `workspace_id` on all three tables | repository convention (§2.1) |
| P2 | Soft delete on all three tables; "delete" in the raw draft means soft delete | `25_soft_delete.md` |
| P3 | No stored major category on StockReportItem | raw §6 vs §6.1 contradiction; facts stored once |
| P4 | `properties = {}` is a valid requirement | Scanner rules may be category-only; the Item-side "empty is nothing" rule is Item-specific |
| P5 | The assignment's item is the task's PRIMARY item, derived, not supplied | §2.3; the only reading consistent with "one task, one item" |
| P6 | `assigned → in_queue`, `stalled → in_progress` | the raw mapping skipped two of eight task states |
| P7 | `resolved` and `failed` assignments are terminal and ignore later task changes | terminal tasks never reopen; a Scanner-resolved item is a closed chapter |
| P8 | `resolved → working` reopening is dropped | it does not exist in this backend (§2.3) |
| P9 | Assignment creation is refused for a failed/cancelled task | it would be born terminal |
| P10 | Header `x-api-key`; new setting distinct from the outbound key; unconfigured = refuse | E4, E5, fail-closed |
| P11 | Unknown category rejects the whole demand batch | follows from atomic batches; categories cannot be invented |
| P12 | Duplicate identities inside one batch reject it | prevents silent overwrite |
| P13 | Non-eligible article numbers are no-ops with a reported reason | forced by HC-5 (§8.2) |
| P14 | Category names match case-insensitively | the one existing precedent |
| P15 | One history record per priority change; reorder records only for the moved item; goal record's awaiting starts at 0 and only the current goal record accumulates | raw §26 asked for this to be investigated |
| P16 | Order is 1-based; reorder is a single-item move | the owner's `1,2,3,4` example; "change an item's order" endpoint |
| P17 | Null-priority items list by creation time | a complete order is required |
| P18 | Response uses `item_category {client_id, name, major_category}` | raw §44 asked to avoid ItemType confusion |
| P19 | Roles: mutations admin/manager; reads all four roles | matches neighbouring routers |
| P20 | A read-only consistency check is in must-ship | it is the instrument for M1 |
| P21 | `is_stock_assignment` is true while any non-deleted assignment exists, including terminal ones | raw §31 sets it on create and clears it on delete only |

---

## 17. Open decisions ledger — owner cards

**Card 1 — One board row per requirement, or per requirement *per location*?**
Story: LC wants 2 light oval dining tables and the showroom wants 1 of the same. Scanner keeps
those as two separate rules. Manager's row has no location, so if Scanner posts them one after the
other the second overwrites the first and the board says "requested 1" when the real need is 3.
- A — Scanner sums across locations and sends one number per category+properties; Manager stays location-free.
- B — Manager adds location to the row's identity: one row per location, each with its own priority and queue.
- Recommendation: **A** — workers repair a kind of item, not a shelf; and it keeps your stated identity.
- On silence: the gate holds.
- Trace: §4.1 identity, §8.1, E1.

**Card 2 — Do the board's work numbers count items or units?**
Story: Scanner says teak dining chairs are short by 8. You assign one task: a set of 8 chairs,
one article number. Counting assignments, the board reads "requested 8 · in queue 1" and looks
seven short forever. Scanner itself counts that set as 8 units across 1 item.
- A — Count units: each assignment stores the item's quantity when created, and the counters add that number.
- B — Count assignments (the raw draft): every set counts as 1; Scanner must then send demand in items, not units.
- Recommendation: **A** — it makes "requested" and "in queue" the same currency without asking Scanner to change its meaning.
- On silence: the gate holds.
- Trace: §4.2, §5.5, M1, E2.

**Card 3 — Which workspace does a Scanner call belong to?**
Story: Scanner's call carries a key, not a logged-in user, so Manager cannot tell whose board to
update. Today there is one workspace; the day a second exists, a guess puts one company's stock
needs on another's board.
- A — A setting names the workspace that the key belongs to; missing setting = calls refused.
- B — "The only workspace"; calls refused as soon as more than one exists.
- C — Scanner sends a workspace id in every request.
- Recommendation: **A** — explicit, fails closed, nothing for Scanner to know.
- On silence: the gate holds.
- Trace: §8 auth, M7, §2.5.

**Card 4 — May a manager create a board row by hand?**
Story: a manager adds "bar cabinets" by hand to queue work Scanner has no rule for. If they can
type a requested number, that 5 stays forever — Scanner never corrects a row it does not know.
If they cannot create rows at all, such work has nowhere to go.
- A — Hand-made rows allowed, always with requested 0; only Scanner ever sets the number.
- B — No hand-made rows; only Scanner creates them. Deleting stays.
- C — Hand-made rows with a typed requested number.
- Recommendation: **A** — keeps "Scanner owns demand" absolute and still gives extra work a home.
- On silence: the gate holds.
- Trace: HC-1, §9.

**Card 5 — A task on the board is deleted, or its main item is swapped. What happens to its assignment?**
Story: a chair task sits "in progress" on the teak row. Someone deletes the task as a duplicate.
Nothing will ever move that assignment again, so the row shows one chair in progress for months.
- A — Both events remove the assignment, exactly as if a user had unassigned it.
- B — Both mark it `failed` (kept visible as history).
- C — Block deleting a task / swapping its item while it is assigned.
- Recommendation: **A** — a deleted task is not failed work, it is work that never was.
- On silence: the gate holds.
- Trace: §2.3 last bullet, §5, M1.

**Card 6 — A finished item is reopened and finished again. Does the goal's history count it twice?**
Story: during the "8 chairs" goal a chair reaches awaiting, a flaw is spotted, the task reopens,
and it is finished again. Counting every arrival, the goal's history says 2 chairs completed when
one chair was.
- A — Count each assignment once, the first time it reaches awaiting.
- B — Count every arrival.
- C — Count arrivals, and subtract when reopened.
- Recommendation: **A** — never double counts, never decreases, and needs no guess about which goal to subtract from.
- On silence: the gate holds.
- Trace: §6.2, M5.

**Card 7 — Should Manager refuse to assign an item of the wrong category?**
Story: someone taps a coffee-table task onto the "Dining Chairs · teak" row. The board then shows
a chair in progress that is really a table. Properties cannot be checked — Scanner's rules use
groups like "wood group: dark" that no item carries — but the category can.
- A — Refuse when the item's category differs from the row's (or the item has none).
- B — No check; any task can go on any row.
- Recommendation: **A** — cheap, and the one mistake the system can actually see.
- On silence: the gate holds.
- Trace: §9 assignments, E3.

---

## 18. Shaping changelog

**Round 0 — 2026-09-18 — initial grounded shaping (intention-shaper).**
- Grounded against the Manager backend and the Scanner repository; evidence doc written.
- Contradictions with the repository resolved: integer ids → string `client_id` FKs; added
  `workspace_id`; "a task has one item" → PRIMARY item; `resolved → working` removed (does not
  exist); `cancelled` confirmed live; "central integration point" replaced by the enumerated
  write-site table because no single point exists.
- Contradictions inside the draft resolved: stored vs derivable major category (P3);
  `item_type` response naming (P18); simultaneous priority/order history (P15).
- Owner answers from the raw draft folded: contiguous order; null priority ⇒ null order; omitted
  filter ⇒ untriaged only; atomic batches; `Item.article_number` lookup; a `failed` assignment
  state for failed/cancelled tasks.
- Raw open question "article number cannot resolve / resolves ambiguously" closed: uniqueness
  makes ambiguity impossible among non-deleted items; non-resolution is a no-op (P13).
- Seven decisions routed to the owner (§17). Status COLLABORATING.

---

## Appendix A — raw-draft map

| Raw section | Where it lives now |
|---|---|
| 2–4 goal, scope, ownership | §1 |
| 5–9 StockReportItem, identity, signature, projections | §4.1, §10, §2.2 |
| 10–16 assignment, cardinality, states | §4.2, §5 |
| 17–19, 51 task sync, backward, cancelled/failed | §2.3, §5 |
| 20–22 arithmetic, atomicity, idempotency | HC-2/3/5, §5.5, §14 |
| 23–26 history | §4.3, §6 |
| 27–28 priority | §7 |
| 29–35 services | §5, §9, §14 (structure left to planning) |
| 36–38 local API | §9 |
| 39–42 webhooks | §8 |
| 43–47 reads and serializers | §9 |
| 48 reconstructability | HC-2, scope item 8, M1 |
| 49 testing philosophy | §13 (tests are purchased against M1–M7) |
| 50 investigation list | §2 |
| 52 invariants 1–18 | HC-1…6, §4–§8, M1–M6 |
| 53 owner answers | §7, §8, §9, §5 — verbatim below |

### Owner answers carried from the raw draft (verbatim, so they survive the draft's deletion)

| Question | Owner answer |
|---|---|
| Should priority orders always be contiguous (1,2,3,4 → 2 leaves → 1,2,3)? | "ues it should be contiguous." |
| Does `priority = null` always imply `priority_order = null`? | "yes it means to priority_order also." |
| GET with no priority parameter: only `priority IS NULL`, or all? | "only priority is null, and there is no default of priority when creating it, that is the point of returning null, for the user to understand what is missing to assign a priority." |
| Scanner batches: atomic, or partial success with per-item errors? | "atomic / all-or-nothing" |
| How does `article_number` map to items? | "this is map by Item.article_number" |
| How are failed/cancelled tasks represented on the assignment? | "for this we can actually add one more state to the StockTaskAssignment.state which is failed for representing the task.state failed and cancelled ( i belive in this backend i only use the failed state no cancelled either way ), and marking that state on the StockTaskAssigment as failed should remove the quantiy_* that it was contributing on the StockReportItems instance" |
