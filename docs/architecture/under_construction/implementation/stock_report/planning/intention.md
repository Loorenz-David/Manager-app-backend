# Intention: Stock Report — Scanner demand turned into Manager work

```
status: RATIFIED — by the owner (David), 2026-09-18; see §18 "Ratification"
role: intention (pipeline root artifact)
shaped_from: raw_intention.md (this folder; its content and the owner's answers are preserved in Appendix A)
source_evidence: scanner_source_evidence.md (this folder) — cited below as E1…E10
date: 2026-09-18
round: 4 (ratified as of this round)
```

Paths are relative to `backend/`. `app/beyo_manager/` is abbreviated `bm/`.

---

## ⚠ OWNER DECISIONS REQUIRED (0)

None open. All seven round-0 cards and both round-1 confirmations are answered (§17), and the
owner ratified the document on 2026-09-18 (§18). Everything else in this document is either the owner's own
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
  webhook, always as an absolute value, never as a delta, **in units** (a set of 8 chairs is 8).
  No Manager user or job writes it.
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
- **HC-2a — Everything on the board is counted in units.** An assignment is worth the item's
  quantity as it was when the assignment was created; the counters are sums of those stored
  quantities, never a count of assignments (owner, round 1).
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
Every table: `workspace_id`, `client_id`, `created_at`, soft-delete trio, and **authorship**
(owner, round 4 — §4.5).
Field ownership legend — **S** Scanner webhook · **U** Manager user · **Sys** system-derived.

### 4.1 `StockReportItem`

| Field | Type | Writer | Rule |
|---|---|---|---|
| `item_category_id` | FK `item_categories.client_id` | S at creation | immutable after creation |
| `properties` | JSONB, not null | S at creation | immutable; Scanner's rule criteria, stored verbatim (E3, E7); `{}` is a valid value (a category-only requirement) |
| `properties_signature` | String(64), not null | Sys | always `compute_properties_signature(properties)`; never accepted from a caller |
| `quantity_requested` | int ≥ 0, default 0 | **S only** | absolute set; nothing else may overwrite it |
| `quantity_in_queue` / `quantity_in_progress` / `quantity_awaiting` | int ≥ 0, default 0 | **Sys only** | projections (HC-2); DB check `>= 0` |
| `priority` | `high/medium/low`, nullable, default null | U | never written by Scanner |
| `priority_order` | int, nullable | Sys (from U actions) | §7 |

- **No stored `item_major_category`.** It is derived from `ItemCategory.major_category` at read
  time; storing it would be a second copy of a fact (raw §6 listed it as a field, §6.1 called it
  derivable — resolved to derivable).
- **Identity:** at most one non-deleted row per `(workspace_id, item_category_id,
  properties_signature)` — a partial unique index. **There is no location in the identity**:
  Scanner sums a requirement across its locations before sending (owner, round 1; E1). Find-or-create must be safe under two
  concurrent deliveries of the same new identity.
- A soft-deleted row never blocks a new row of the same identity; a later Scanner delivery
  creates a fresh row with empty history.

### 4.2 `StockTaskAssignment`

| Field | Type | Writer | Rule |
|---|---|---|---|
| `stock_report_item_id` | FK | U at creation | immutable |
| `task_id` | FK `tasks.client_id` | U at creation | immutable |
| `item_id` | FK `items.client_id` | U at creation | immutable; must be the task's active **PRIMARY** item — related items are refused (owner, round 2: related items are an unused legacy concept) |
| `credited_history_record_id` | FK history record, nullable | Sys | the goal record this assignment's units are currently counted in (§6.2); null when not counted |
| `quantity` | int ≥ 1 | Sys at creation | copy of `Item.quantity` at creation (floor 1); **never updated afterwards** — it is what this assignment adds to and removes from the counters |
| `property_mismatch_overridden` | bool, default false | Sys at creation | true when the assignment was created with the override flag over a property mismatch (§9A) |
| `state` | `StockTaskAssignmentStateEnum` | Sys | only through the transition operation (HC-3) |

`StockTaskAssignmentStateEnum`: `in_queue, in_progress, awaiting, resolved, failed`.
Active = `{in_queue, in_progress, awaiting}`. `resolved` and `failed` are **terminal**: nothing
moves an assignment out of them.

- **One active assignment per item:** partial unique index on `(workspace_id, item_id)` where
  state is active and the row is not deleted. Because only the PRIMARY item can be assigned and a
  task has at most one, **a task has at most one active assignment**.
- A terminal assignment never blocks a new one for the same item.

### 4.3 `StockReportHistoryRecord`

`type` (`quantity_requested_change | priority_change | priority_order_change`),
`quantity_requested`, `quantity_awaiting`, `priority`, `priority_order`, `created_at`,
`stock_report_item_id`. Append-only except the one field in §6.2. All Sys-written.

### 4.4 `Task.is_stock_assignment`

Boolean, not null, default false, Sys-written. **True exactly when the task has at least one
non-deleted `StockTaskAssignment`, in any state.** Its purposes: cheap task filtering later, and a
cheap skip for task sync on the vast majority of tasks.

### 4.5 Authorship — who is behind a change (owner, round 4)

Same column shapes as the rest of the backend (`created_by_id` / `updated_by_id`, nullable FKs to
`users.client_id`; `updated_at` beside `updated_by_id`; `deleted_by_id` already in the trio).
**Null always means "no Manager user did this" — Scanner or the system.** A user is never
invented for Scanner.

| Table | `created_by_id` | `updated_by_id` / `updated_at` |
|---|---|---|
| `StockReportItem` | null when Scanner's demand created it | stamped when a **user-owned** field changes: priority, order (for the item the user moved — shifted neighbours are not stamped), deletion. Scanner setting the requested quantity and counters moving stamp nothing: those are not a user's edit to the row. |
| `StockTaskAssignment` | the user who assigned it | the user whose action moved its state (the worker whose step transition moved the task, the manager who failed the task); null when Scanner resolved it |
| `StockReportHistoryRecord` | the user for a priority or order record; null for a goal record (Scanner caused it) | none — records are append-only (the goal total in §6.2 is system arithmetic) |

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
5. Counter effect of any move A → B, with `q` = the assignment's stored `quantity`: `−q` on A's
   counter if A is active, `+q` on B's counter if B is active. Creation is "nothing → B";
   deletion is "A → nothing". A later change of `Item.quantity` moves nothing.
6. **The pairing can end from the task side** (owner, round 1): soft-deleting a task removes all
   of its assignments, and removing the PRIMARY item from a task (`remove_item_from_task`; a swap
   is a removal followed by an add) removes that item's assignment — both through the assignment
   delete operation, exactly as if a user had unassigned it.

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

### 6.2 The goal record's running total (owner, round 2 — option C)
The **current goal record** of an item is its most recent `quantity_requested_change` record.

- **Credit.** When an assignment enters `awaiting`, the current goal record's `quantity_awaiting`
  increases by the assignment's `quantity`, and the assignment remembers that record
  (`credited_history_record_id`). With no goal record yet (item created at 0), nothing is
  credited and nothing is remembered.
- **Scanner resolving never subtracts.** `awaiting → resolved` leaves the goal record untouched —
  the work was completed during that goal, and stays counted.
- **Un-completing subtracts.** When an assignment leaves `awaiting` by any route other than
  Scanner resolving — the task reopens (`→ in_progress`), the task fails or is cancelled from
  ready (`→ failed`), or the assignment is deleted while awaiting — its `quantity` is subtracted
  from **the record it was credited to** (not from whichever record is current by then), floored
  at 0, and the memory is cleared. Finishing again credits the then-current goal record.
- Net meaning of the field: *units whose work was completed during this goal and has not been
  undone.* Priority records are never touched after they are written.

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
**Workspace** (owner, round 1): a second new setting names the workspace the key belongs to.
Either setting absent, or naming a workspace that does not exist → every request refused.

**Batches are atomic for malformed input** (owner answer): an entry of the wrong shape or type, or
a duplicate identity, rejects the whole request and nothing is written; the error names every
offending entry. **One exception, by owner correction in round 3:** an unknown category is not
malformed input — see §8.1.

### 8.1 Demand — `[{itemCategory, properties, quantityRequested}]`
- `itemCategory` is a category **name** (E1), matched case-insensitively against non-deleted
  `ItemCategory.name` in the workspace. **Unknown name → that entry is skipped and reported back;
  every other entry is applied** (owner, round 3). The request still succeeds. The response lists
  every entry with its outcome — `applied` or `category_not_found` — echoing the category name and
  properties so Scanner can tell which rule was not taken. Manager never auto-creates a category
  (it could not know `major_category`). A skipped entry writes nothing at all.
- `properties` must be a JSON object (`{}` allowed); `quantityRequested` an integer ≥ 0, in
  **units**, already **summed across Scanner's locations** for that category+properties.
- Two entries in one batch that resolve to the same identity → the batch is rejected (otherwise
  the later one silently overwrites the earlier — the per-location trap of E1).
- An identity absent from a batch is left untouched; absence is not a zero.
- Per entry: find-or-create, set `quantity_requested`, apply §6.1.

### 8.2 Processed — `[{article_number}]`
- Resolve the non-deleted `Item` by `article_number` in the workspace (unique — §2.2), then its
  active assignment (at most one — §4.2).
- Assignment in `awaiting` → `resolved`, for the whole assignment: `quantity_awaiting` drops by
  its stored `quantity`. There is no partial resolution of a set.
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
| ~~create StockReportItem~~ | **no local endpoint now** (owner, round 1): the find-or-create service is written to be reusable, but only the Scanner demand webhook calls it. Not denied — deferred (§12). |
| delete StockReportItem | soft-deletes the item, its history, and — through the assignment delete operation — every assignment, so counters and task flags stay right throughout |
| change priority · change priority_order | two separate endpoints (§7) |
| create assignments (batch) · delete assignments (batch) | all-or-nothing; each create entry names `stock_report_item`, `task_id`, `item_id`; checks in §9A |
| GET StockReportItems | `priority=high,medium,low` filter; **omitted → only `priority IS NULL`** (owner answer); unpaginated; order per §7 |
| GET StockTaskAssignments | by StockReportItem `client_id`; non-deleted, all states |

Assignment deletion: removes the assignment's counter contribution if active, soft-deletes it,
recomputes `Task.is_stock_assignment` (§4.4), atomically.

### 9A. What is checked when an assignment is created (owner, round 1)

In order, per entry; the batch is all-or-nothing:

1. **References exist** in the workspace, non-deleted; the item is the task's active PRIMARY item;
   the task is not `failed`/`cancelled`; the item has no other active assignment.
2. **Category — hard refusal.** The item's `item_category_id` must equal the requirement's. An
   item with no category is refused. No override exists.
3. **Properties — refusal that can be overridden.** The item is evaluated against the
   requirement's criteria with Scanner's own rules (below). On mismatch the request fails with a
   **dedicated, machine-readable error** that lists, per offending entry, the criteria keys that
   failed and why (`missing on item` / `value not accepted` / `no group for value`). Re-sending
   the entry with `override_property_mismatch: true` creates it and stores
   `property_mismatch_overridden = true`. The flag on an entry that matches is ignored and stores
   false. The check happens **once, at creation**; later edits to the item never re-evaluate it.

**The match, mirrored from Scanner (E7–E9) so both applications agree on what "satisfies" means:**

- Empty criteria match any item. An item with no properties matches only empty criteria.
- Every criteria key must be satisfied: the item carries the key with a non-empty string value,
  and the accepted list is `null` (any value) or contains at least one of the item's tokens.
- Tokens: split on `,` and `/` only (never `&`), trim, lowercase; accepted values are compared
  lowercased.
- Two **derived keys**, computed from the item before matching, never stored:
  `wood_group` from the **first** `wood_type` token (table in E8), and `drawers_range` from
  `drawers_qty` (`1-2`, `3-5`, `6+`). A value in no group/range derives nothing and fails the key.
- One **relocated key**: Scanner's criteria key `quantity` (set size) is evaluated against the
  column `Item.quantity`, because Manager does not keep set size in `properties` (E9).
- The two tables live in one code-owned module in `bm/domain/stock_report/`, with the Scanner
  source file and date recorded beside them. They are a **copy**: Scanner's are marked
  provisional, and an edit there must be mirrored here (evidence doc, sender note 8).

Known limit, accepted: Scanner fills item properties from Shopify **and** the purchase API,
Manager from the purchase API only (E10). A key Scanner knows only from Shopify will read as
"missing on item" here. That is exactly the case the override exists for.

### 9B. Realtime events (owner, round 3)

Built on the existing workspace event path (`build_workspace_event` + `dispatch`,
`architecture/11_infra_events.md`), following the existing `<entity>:<verb>` names
(`task:state-changed`, `item:updated`, `working_section:created`).

| Event | When | Carries |
|---|---|---|
| `stock_report_item:created` | Scanner's demand creates a row | the row's `client_id` |
| `stock_report_item:updated` | a row's requested quantity, any of its three work quantities, its priority or its order changed — whatever caused it (Scanner, a user, a task changing state) | `client_id`, the four quantities, `priority`, `priority_order` |
| `stock_report_item:deleted` | a row is deleted | `client_id` |
| `stock_task_assignment:created` / `:state-changed` / `:deleted` | an assignment is created, moves state, or is removed | `client_id`, `stock_report_item_id`, `task_id`, `state` |

Rules: dispatched only **after** the transaction commits, never inside it; nothing is emitted for
a rolled-back request or a no-op (a replayed Scanner request that changes nothing emits nothing);
a change that shifts neighbours' order emits one `:updated` per row whose order changed; when the
change comes from a task-state command, that command dispatches these events alongside its own
(subordinate operations return pending events, they never dispatch — `06_commands_local.md`).
On webhook paths the workspace comes from the row, never from the (empty) request identity.

Response shapes: StockReportItem carries the four quantities, priority, order, `properties`, and
an **`item_category`** object `{client_id, name, major_category}` — the raw draft's `item_type`
/ `type_name` naming is dropped so no "ItemType" concept leaks ahead of the Item Domain migration.
Assignment carries `client_id`, `state`, `stock_report_item_id`, `item`, `task` using two new
serializers, `serialize_item_compact` (client_id, article_number, sku, quantity,
item_category_snapshot, item_major_category_snapshot, item_images via `serialize_image_light`,
images batch-loaded once per response) and `serialize_task_compact` (client_id, task_type,
priority, state, title, return_source, ready_by_at, return_method, created_at, updated_at,
closed_at, completed_at). They are used only by this capability.

**Roles** (owner, round 4):

| Operation | ADMIN | MANAGER | WORKER | SELLER |
|---|---|---|---|---|
| read rows · read assignments | ✓ | ✓ | ✓ | ✓ |
| create assignments · delete assignments | ✓ | ✓ | ✓ (workers handle inventory today) | ✗ |
| change priority · change priority order | ✓ | ✓ | ✗ | ✓ |
| delete a row | ✓ | ✓ | ✗ | ✗ |

A role outside its row is refused before anything is read or written.

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
10. **Realtime events** (owner, round 3 — moved up from "only if cheap"; the event infrastructure
    exists, this adds new event names on it). §9B.

**Only if cheap** — nothing.

**Explicitly deferred / non-goals** — any frontend; the Scanner-side sender; migrating existing
task list endpoints to the compact serializers; taking over Scanner's stock rules, locations or
thresholds; **a repair mode for the consistency check** (owner, round 3: after the whole
implementation, the owner has a place in mind for it); automatic assignment of tasks to requirements; restore of deleted rows; pagination;
a local endpoint for creating StockReportItems by hand (the service supports it; nothing calls it);
bringing Shopify-sourced properties onto Manager items (E10).

---

## 13. Measurement ledger

| ID | Observable outcome — measured true means this shipped | Defect family it guards |
|---|---|---|
| **M1** | After every committed operation, each StockReportItem's three counters equal the **sums of stored assignment quantities** recomputed from its non-deleted assignments by state, and every `Task.is_stock_assignment` equals "has a non-deleted assignment" — including under concurrent transitions on the same item. | counter drift, lost updates, arithmetic applied outside the transition operation |
| **M2** | After a task's state changes by **any** path in §2.3, its active assignment equals the §5 mapping of the task's resulting state; terminal assignments are unchanged; a deleted task or an item removed from its task leaves no assignment behind. | a missed integration site; assuming intermediate states; terminal assignments revived; orphaned assignments counted forever |
| **M3** | Replaying any Scanner request leaves the database identical to one delivery; `quantity_requested` equals the last value Scanner sent; a rejected batch leaves no trace; an entry with an unknown category writes nothing, is reported back as not found, and does not stop the other entries. | double-applied transitions, delta-instead-of-absolute, partial batches |
| **M4** | Payloads differing only in JSON key order resolve to one StockReportItem; there is never more than one live row per identity, nor more than one active assignment per item — including under concurrent requests. | duplicate identities, signature instability, double-booking an item |
| **M5** | Goal records appear only on increases; a goal record's awaiting total never decreases when Scanner resolves, and decreases by exactly the assignment's units — on the record that was credited — when completed work is undone; a priority change yields exactly one record; shifted neighbours yield none. | history that misstates the goal; double counting a re-finished item; subtracting from the wrong goal; duplicate or noisy records |
| **M6** | In every priority group, orders are exactly `1..n`; `priority` is null exactly when `priority_order` is null; the list endpoint returns the §7 order and, with no filter, only untriaged items. | gaps/duplicates after move, delete or priority change; wrong default listing |
| **M9** | Each operation is refused for every role outside its row of the role table and allowed for every role inside it; every user-caused change records that user, and every Scanner- or system-caused change records none. | a role reaching an operation it was not given; a change with no author or with the wrong one |
| **M8** | An assignment whose item is of another category is always refused; one whose item fails the requirement's criteria is refused with the dedicated error unless the override flag is sent, and then is created and marked as overridden. For the same item and criteria, Manager's verdict equals Scanner's matcher. | wrong work on the board; a silent mismatch; the two applications disagreeing on what satisfies a rule |
| **M7** | A webhook request without the correct key, or with the key or workspace setting unconfigured, gets 401 and writes nothing. | an open or fail-open inbound endpoint |

Rank: M1, M2, M3 are the reason the capability exists; M4 protects identity; M7 protects the
boundary; M9 protects who may act and who is recorded; M8, M5, M6 protect meaning on the board.
(M8 and M9 were added in rounds 1 and 4 and keep their numbers so no earlier ID moves. Nine
entries against a 3–7 guideline: kept because each guards a distinct failure; the owner may
merge.)

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
7. **Criteria matcher** — tokenizer, wildcard, the two derived-key tables, the relocated
   `quantity` key; fixtures taken from Scanner's real rules, not invented (charter rule 17).
8. **Event emission** — after-commit only, none on rollback or no-op, pending-events hand-up from
   subordinate operations into the task-state commands. Criteria for §9B trace here.

---

## 15. Pre-implementation protocol

1. ~~Owner answers the §17 cards~~ — done, rounds 1–4.
2. ~~Owner ratifies~~ — done 2026-09-18 (§18). **Next gate: mechanism-inventory.**
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
| P5 | ~~The assignment's item is derived from the task's PRIMARY item~~ — **struck by the owner, round 1**: the caller supplies `task_id` and `item_id`; the item must be the task's PRIMARY item (round 2). | |
| P6 | `assigned → in_queue`, `stalled → in_progress` | the raw mapping skipped two of eight task states |
| P7 | `resolved` and `failed` assignments are terminal and ignore later task changes | terminal tasks never reopen; a Scanner-resolved item is a closed chapter |
| P8 | `resolved → working` reopening is dropped | it does not exist in this backend (§2.3) |
| P9 | Assignment creation is refused for a failed/cancelled task | it would be born terminal |
| P10 | Header `x-api-key`; new setting distinct from the outbound key; unconfigured = refuse | E4, E5, fail-closed |
| P11 | ~~Unknown category rejects the whole demand batch~~ — **struck by the owner, round 3**: the entry is skipped and reported back, the rest is applied (§8.1). | |
| P12 | Duplicate identities inside one batch reject it | prevents silent overwrite |
| P13 | Non-eligible article numbers are no-ops with a reported reason | forced by HC-5 (§8.2) |
| P14 | Category names match case-insensitively | the one existing precedent |
| P15 | One history record per priority change; reorder records only for the moved item; goal record's awaiting starts at 0 and only the current goal record accumulates | raw §26 asked for this to be investigated |
| P16 | Order is 1-based; reorder is a single-item move | the owner's `1,2,3,4` example; "change an item's order" endpoint |
| P17 | Null-priority items list by creation time | a complete order is required |
| P18 | Response uses `item_category {client_id, name, major_category}` | raw §44 asked to avoid ItemType confusion |
| P19 | ~~Roles: mutations admin/manager; reads all four roles~~ — **replaced by the owner's matrix, round 4** (§9). Mine within it: sellers cannot assign, workers cannot prioritize, only admin/manager delete a row — the owner named what each role gains; everything unnamed stays closed. | |
| P20 | A read-only consistency check is in must-ship | it is the instrument for M1 |
| P22 | The assignment stores the item's quantity once, at creation; later quantity edits never move the board | the only way unit counters stay reconstructable (HC-2) |
| P23 | The override flag is per entry, and its use is stored on the assignment | a batch can mix clean and overridden entries; the board can later show which were forced |
| P24 | The property check mirrors Scanner's matcher exactly, including the relocated `quantity` key | otherwise the warning fires on items Scanner would count, or stays silent on ones it would not |
| P25 | A task-side removal (task deleted, item unlinked) uses the same delete operation as a user unassigning | owner's answer A to card 5; one code path for counters |
| P26 | History subtraction goes to the record the assignment was credited to, floored at 0, and applies to every exit from awaiting except Scanner resolving (reopen, fail/cancel from ready, deletion while awaiting) | the owner chose "subtract on reopen"; this makes it exact when the goal changed in between, and consistent for the other two ways completed work gets undone |
| P27 | Malformed entries and duplicate identities still reject the whole request; only "category not found" is per-entry | the owner's atomic answer stands for sender bugs; the round-3 correction was specifically about unknown categories |
| P28 | The realtime event names and payloads of §9B; a no-op emits nothing | existing naming convention; an event for nothing would make the board flicker on every Scanner retry |
| P29 | Authorship semantics of §4.5: null = Scanner/system; a row's `updated_by` tracks user-owned fields only; shifted neighbours are not stamped; an assignment's `updated_by` is the user whose action moved it | the owner asked for created_by/updated_by; these are the readings that keep "who did this" truthful |
| P21 | `is_stock_assignment` is true while any non-deleted assignment exists, including terminal ones | raw §31 sets it on create and clears it on delete only |

---

## 17. Open decisions ledger

### Open

None.

### Closed (rounds 1–2)

| Card | Owner answer | Folded into |
|---|---|---|
| 1 location | Scanner sums across locations; Manager stays location-free; recorded for the Scanner sender | §4.1, §8.1, evidence doc sender notes |
| 2 units | count units | HC-2a, §4.2 `quantity`, §5.5, §6.2, §8.2, M1 |
| 3 workspace | A — a setting names the workspace | §8 |
| 4 hand-made rows | not denied, not built now: the service is reusable, only the Scanner webhook calls it; assignments are created by the manager from `task_id` + `item_id` | §9, §12, P5 struck |
| 5 task deleted / item unlinked | A — the assignment is removed | §5.6, M2, P25 |
| 6 history on re-finish | **C** — the history total goes down when completed work is reopened, never when Scanner resolves (round 2) | §6.2, M5, P26 |
| conf. 1 assignable items | main (PRIMARY) item only; related items are an unused legacy concept (round 2) | §4.2, §5 |
| conf. 2 set size | the warning includes set size, read from the item's quantity; drawer range mirrored too (round 2) | §9A |
| 7 category / properties | category mismatch refused; property mismatch refused with a readable error unless the override flag is sent; grouping tables mirrored into Manager | §9A, M8, E7–E10 |

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

**Round 1 — 2026-09-18 — owner answers to the round-0 cards (owner: David).**
- Cards 1, 2, 3, 5, 7 answered and folded; card 4 answered by reframing (see §17 "Closed").
- **Units** now run through the whole model: assignment `quantity` stored at creation, counters
  and the goal record move by it, Scanner resolves a whole assignment.
- **P5 struck by the owner**: the caller supplies `task_id` and `item_id`. A task may therefore
  hold several assignments; sync moves all active ones. Confirmation 1 opened on which roles.
- **Card 7 grew a mechanism.** The owner wants properties checked with an overridable refusal.
  Scanner's matcher was read and mirrored (E7–E9): tokenizer, wildcard, two derived keys
  (`wood_group`, `drawers_range` — there are exactly two), and one relocated key (`quantity`).
  New §9A, new ledger entry **M8**, new mechanism 7, P22–P25. The source gap between the two
  applications' item properties (E10) is recorded as an accepted limit the override covers.
- Local "create StockReportItem" endpoint moved from the API to deferred.
- Card 6 re-asked: the owner's answer addressed the live counters (already settled), not the
  history total. Status stays COLLABORATING.

**Round 2 — 2026-09-18 — remaining answers (owner: David).**
- Card 6 → **C**. §6.2 rewritten: credit on entering awaiting, no change on Scanner resolving,
  subtraction when completed work is undone. `credited_history_record_id` added so the
  subtraction lands on the right goal (P26, mine). M5 widened.
- Confirmation 1 → PRIMARY item only. Round 1's "several assignments per task" reverted: at most
  one active assignment per task.
- Confirmation 2 → set size checked against `Item.quantity`; `drawers_range` mirrored alongside
  `wood_group`. The Shopify/purchase-app property gap (E10) acknowledged by the owner as a known
  limit until item identity is centralized; the override is the accepted answer.
- Open decisions ledger empty. Status → READY_FOR_RATIFICATION (the shaper's claim; only the
  owner's explicit approval writes RATIFIED).

**Round 3 — 2026-09-18 — owner corrections at the ratification surface (owner: David).**
- The surface was not approved as presented, so the document returned to COLLABORATING, the three
  corrections were folded, and READY_FOR_RATIFICATION is claimed again.
- **Realtime events → must ship.** New §9B, mechanism 8, P28. Kept out of the measurement ledger
  (already 8 entries against a 3–7 guideline); its criteria trace to mechanism 8.
- **Repair mode → deferred** until after the whole implementation.
- **Unknown category no longer rejects the batch** (P11 struck): skipped, reported per entry,
  the rest applied. This narrows the owner's earlier "atomic" answer to malformed input and
  duplicate identities (P27, mine). M3 widened.

**Round 4 — 2026-09-18 — owner corrections (owner: David).**
- The owner confirmed every listed proposal except roles. **Role matrix replaced** (§9): workers
  may create and delete assignments; sellers may change priority and order; row deletion stays
  admin/manager.
- **Authorship added to all three tables** (§4.5) — the owner noted `created_by` / `updated_by`
  were missing. Semantics are mine (P29). New ledger entry **M9** (roles + authorship).
- READY_FOR_RATIFICATION claimed again.

**Ratification — 2026-09-18 — owner: David.**
- Owner's words: "perfect, i approved it", given in reply to the round-4 surface.
- Surface presented (cumulative over rounds 2–4): the intended outcome; the measurement ledger
  M1–M9 verbatim (M1–M8 in round 2, M3 widened in round 3, M9 added in round 4); the scope
  boundaries as corrected in round 3 (realtime events ship; repair mode deferred); the full list
  of standing proposals in plain language (round 3), all confirmed by the owner except roles; the
  role matrix and authorship rules (round 4); unresolved decisions: none.
- Status → **RATIFIED**. Any later material semantic change re-opens the gate (status back to
  COLLABORATING until re-ratified); amendments use lettered sections and never renumber.

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
