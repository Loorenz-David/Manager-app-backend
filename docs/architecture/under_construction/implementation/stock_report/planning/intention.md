# Intention: Stock Report — Scanner demand turned into Manager work

```
status: RATIFIED — by the owner (David): ratified 2026-09-18, re-ratified 2026-09-18 incl. §14B, and 2026-09-19 incl. round 7 (§14D), round 8 (§14E) and round 9 (§14F, card 14, P42–P45); see §18
role: intention (pipeline root artifact)
shaped_from: raw_intention.md (deleted by the owner after ratification; its section map and the owner's verbatim answers are preserved in Appendix A)
source_evidence: scanner_source_evidence.md (this folder) — cited below as E1…E10
date: 2026-09-18
round: 9 (early Scanner resolution into the terminal state `resolved_early` — §14F; card 14 answered; re-ratified 2026-09-19; 0 cards open)
round 10 (2026-09-21): §14G added — match preview + MC-21. **Additive by owner ruling: the gate holds and no re-ratification was required**, because the section adds a read-only surface over already-ratified checks and changes no contract, invariant or outcome. Status above is unchanged and only the owner writes it.
round 11 (2026-09-22): §14H added — the two **response-shape** drifts between this document and the code + published frontend contract, corrected in this document's favour of what already ships. **Corrective by owner ruling** (card D-4: *"amend intention §9 to four keys — and sweep §9 for other drift, not just this key"*); no behaviour, contract, invariant or outcome moves, because §14H changes only where this document had fallen behind code that is VERIFIED and a contract already published. Status above is unchanged and only the owner writes it.
```

Paths are relative to `backend/`. `app/beyo_manager/` is abbreviated `bm/`.

---

## Status — RATIFIED (round 9, 2026-09-19); no owner decision open

Re-ratified by the owner after two additions made while the implementation-planner was running:
- **Round 8 (§14E):** a third Scanner webhook deletes a board row when a Scanner rule's criteria
  change or the rule is removed. The owner waived a mechanism-inventory re-check; its questions are
  planner obligations (§14E "Carried to the planner").
- **Round 9 (§14F):** Scanner's processed report on an assignment whose task is not yet `ready`
  moves it to the new terminal state **`resolved_early`** — units leave the counters, the task is
  untouched, the units are credited to the current goal (card 14 → A), and the state stays as the
  trace of a forgotten step.

**Read §14B–§14F with the rest:** later amendments win over earlier sections, in the order stated
in §14C, with §14F last and strongest.

**Next:** the orchestrator hands the implementation-planner the §14E and §14F deltas.

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

### 4A. Row identity — contracts MC-3, MC-4 (mechanism-inventory, round 6)

**MC-3 — criteria normalization and the row signature** (serves M4; supersedes §2.2 "list order is
significant" and §4.1 "stored verbatim" for the reasons in §14C).

A pure function `normalize_stock_criteria(raw: dict) -> dict` in `bm/domain/stock_report/`
(module name is the planner's). **Input:** the `properties` value of one demand entry exactly as
`json.loads` returns it from the raw request bytes. The webhook reads raw bytes (§8B), so no
Pydantic coercion touches this field. Keys are always `str`. A key repeated inside one JSON object
has already been resolved by the decoder (last occurrence wins) before this function sees it.
Scanner cannot produce a repeated key (`JSON.stringify`).

| Decoded value `v` of one key | Understood? | Stored and signed as |
|---|---|---|
| `None` | yes (wildcard) | `None` |
| `str`, and `v.strip().lower() != ""` | yes | `[v.strip().lower()]` |
| `str`, blank after `strip()` (`""`, `"  "`) | **no** | `v` unchanged |
| `list` whose every element is `str`, at least one non-blank after `strip()` | yes | `sorted({e.strip().lower() for e in v if e.strip().lower() != ""})` |
| `list` whose every element is `str`, none non-blank (includes `[]`) | **no** | `v` unchanged |
| `list` holding any non-`str` element (`int`, `float`, `bool`, `None`, `list`, `dict`) | **no** | `v` unchanged |
| `int`, `float`, `bool`, `dict` | **no** | `v` unchanged |

- Operation order per string element: `str.strip()` (no argument: Unicode whitespace per
  `str.isspace`), then `str.lower()` (full Unicode lowercase), then de-duplicate by equality, then
  `sorted()` (code-point order). This mirrors Scanner's `normalizeCriteria`
  (`apps/backend/src/modules/stock/domain/property-criteria.ts:29-55`: trim → toLowerCase →
  Set → sort). Two differences have no effect on identity: JS sorts UTF-16 code units, and JS
  `trim` also removes U+FEFF. Manager signs its own normalized form, and only the resulting *set*
  must agree.
- **Keys are never normalized.** Case, whitespace and spelling are kept byte for byte:
  `"Wood_Type"` and `"wood_type"` are two keys, so they make two rows. Scanner's keys come from a
  closed option list (`stock.contract.ts:validateStockCriteria` against
  `item-property-options.ts:ITEM_PROPERTY_OPTIONS`), so this never splits a Scanner rule.
- **"Unchanged" means the decoded Python value as it is.** So `1` ≠ `1.0` (`json.dumps` gives `1` /
  `1.0`), `true` ≠ `1`, list order inside a not-understood list is significant, and key order
  inside a nested `dict` is not (the signature sorts keys recursively).
- **Idempotence:** `normalize(normalize(x)) == normalize(x)` for every `x`. This makes Scanner's
  already-normalized payload (E3) and a hand-reordered one the same row.
- **Signature:** `properties_signature = compute_properties_signature(normalize_stock_criteria(raw))`.
  The existing function (`bm/domain/items/properties_signature.py:compute_properties_signature`)
  is used unchanged. **Stored `properties` is the normalized dict, the value that was signed.**
  The GET endpoints return the stored (normalized) value. The demand webhook echoes `properties`
  **as received**, so Scanner can match the echo to its own rule (v1 handoff §3.4).
- **Relationship to Scanner:** identical on every value Scanner accepts (`str`, `list[str]` with
  one or more non-blank, `null`). Scanner *throws* on everything else (empty or blank list,
  non-string element, non-list value). Manager accepts it, stores it as received (P30), and the
  matcher reports it as `criterion_not_understood` (MC-12).
- **Version:** no stored version column. The module declares
  `CRITERIA_NORMALIZATION_VERSION = 1`, and a golden-vector test pins the signature of a fixed set
  of payloads. Any change to the algorithm ships with a data migration that re-signs every
  non-deleted row and merges rows that collide. Changing the function without that migration
  silently forks identities, and the golden vectors are what redden.
- **Invariant (M4), proven through the webhook endpoint with real JSON bytes:** entries differing
  only in (a) key order, (b) list element order, (c) list element case or outer whitespace,
  (d) duplicate list elements, or (e) a bare string vs a one-element list resolve to **one** row.
  Entries differing in key case or whitespace, or in any not-understood value, resolve to **two**.
  Each of (a)–(e) is its own row, and so is each "two rows" case.

**MC-4 — find-or-create, and the uniqueness predicates** (serves M4).

- `uix_stock_report_items_identity_active`: unique on `(workspace_id, item_category_id,
  properties_signature)` `WHERE is_deleted = false`. A soft-deleted row is outside the predicate, so
  the next delivery creates a fresh row with empty history (§4.1).
- **Find-or-create:** `INSERT … ON CONFLICT (workspace_id, item_category_id, properties_signature)
  WHERE is_deleted = false DO NOTHING RETURNING client_id`. If nothing is returned, the existing
  row is `SELECT`ed by the same three columns plus `is_deleted = false`. There is no
  IntegrityError path. The row is then locked in the MC-1 order. The form is set-based: one multi-row
  INSERT whose VALUES are sorted by `(item_category_id, properties_signature)`, then one
  `SELECT … FOR UPDATE ORDER BY client_id` over every identity in the request, never a statement
  per entry. Sorting the VALUES means two concurrent batches with overlapping new identities wait
  on each other instead of deadlocking.
- **Invariant:** two concurrent first deliveries of one new identity leave exactly one non-deleted
  row. Both requests return 200, both entries are `applied`, and `stock_report_item:created` is
  emitted exactly once, by the request whose INSERT returned the row. Proven with two sessions
  released by a barrier, counting rows and events.
- `uix_stock_task_assignments_item_active`: unique on `(workspace_id, item_id)` `WHERE
  is_deleted = false AND state IN ('in_queue','in_progress','awaiting')`. `resolved`, `failed` and
  deleted rows are outside it (§4.2 "a terminal assignment never blocks a new one").
- `uix_stock_task_assignments_task_active` *(new, mechanism only)*: the same predicate on
  `(workspace_id, task_id)`. §4.2 derives "a task has at most one active assignment" from the
  PRIMARY rule; this index makes the derivation a DB fact. The task sync (MC-2) can then read with
  `scalar_one_or_none()` and never has to choose among several.
- **Error contract on the race path (charter rule 2):** creation takes the Item lock before its
  checks (MC-13), so a concurrent second creation for the same item waits. It then sees the
  first's committed row in the pre-check and fails with reason `item_already_assigned`. An
  `IntegrityError` naming either assignment index is mapped to the same reason (a backstop for a
  path that skips the lock). The test runs two concurrent creations of the same item on two
  different rows. It asserts exactly one active assignment **and** the reason code on the losing
  request, not only the row count.

### 4B. Stored system fields — contracts MC-15, MC-17 (round 6)

**MC-15 — `Task.is_stock_assignment`** (serves M1).
- **Truth:** `EXISTS (non-deleted stock_task_assignments row with this task_id)`, in any state.
- **Writers:** (i) assignment creation sets `true`; (ii) the assignment delete operation, after
  soft-deleting, re-evaluates `EXISTS` with a fresh query in the same transaction and writes
  `false` when none remain. Nothing else writes it. Terminal moves do not change it (P21).
- **Write form:** `UPDATE tasks SET is_stock_assignment = :v, updated_at = tasks.updated_at WHERE
  client_id = :id AND is_stock_assignment IS DISTINCT FROM :v`. The explicit self-assignment of
  `updated_at` is what stops the column's `onupdate=` (`bm/models/tables/tasks/task.py:90-92`)
  from firing. The flag is a system field, so flipping it never moves the task's `updated_at` or
  `updated_by_id`, and never reorders a task list. An ORM attribute write would fire `onupdate`.
- **Readers:** filtering only. The task sync does **not** read it (MC-2 step 3). It is never
  serialized (§14B B3).
- **Invariant (M1):** after every committed operation, flag == `EXISTS(…)` for every task touched.
  A flip leaves `tasks.updated_at` and `updated_by_id` byte-identical. Planted defect: write the
  flag as an ORM attribute, so `updated_at` moves and the row turns red.

**MC-17 — authorship, as (operation × table × column)** (serves M9; §4.5 made total).
A new table never declares `onupdate=`. Every stamp below is an explicit assignment, and a cell
not listed stays unchanged. The *actor* is the command's `ctx.user_id`, with `""` stored as NULL.
For the dormant deferred-completion worker it is the payload's `performed_by_user_id`.

| Operation | `stock_report_items` | `stock_task_assignments` | `stock_report_history_records` |
|---|---|---|---|
| Demand creates a row | `created_by_id` NULL; `updated_*` NULL | — | goal record `created_by_id` NULL |
| Demand changes `quantity_requested` | `updated_*` unchanged | — | goal record (if any) `created_by_id` NULL |
| Any counter move (sync, Scanner, create, delete) | `updated_*` unchanged | — | goal total: no stamp |
| User changes priority | moved row: `updated_by_id` = actor, `updated_at` = now; shifted neighbours unchanged | — | `created_by_id` = actor |
| User moves order | same as priority | — | `created_by_id` = actor |
| User deletes a row | `deleted_*` and `updated_*` = actor, now | via the delete op (below) | every record: `deleted_*` = actor, now |
| User creates assignments | — | `created_by_id` = actor; `updated_*` NULL (creation is not a move) | — |
| Task sync moves an assignment | — | `updated_by_id` = actor of the task command (**the performer, `ctx.user_id`, not `credited_user_id`**: a manager acting for a worker is recorded), `updated_at` = the command's `now` | — |
| Scanner resolves | — | `updated_by_id` = NULL, `updated_at` = now | — |
| Assignment deleted (user unassign, task deleted, PRIMARY item unlinked, item deleted, row deleted) | — | `deleted_by_id` = actor, `deleted_at` = now; `updated_*` unchanged | — |
| Flag flip on `tasks` | — | — | (`tasks.updated_*` unchanged, MC-15) |

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

### 5A. The transition operation — contracts MC-1, MC-11, MC-16 (mechanism-inventory, round 6)

**MC-1 — one operation moves an assignment and its counters** (serves M1; HC-2, HC-2a, HC-3).

`move_assignment(session, assignment, target, *, workspace_id, actor_user_id, now) -> list[event]`.
`target` is a `StockTaskAssignmentStateEnum` member, or `DELETE`. Creation first inserts the row
with no counted state and then calls this with the mapped state ("nothing → B"). It never opens,
commits or dispatches. It takes `workspace_id` as an argument and **never reads `ctx`**, because
its callers include webhook paths where `ctx.workspace_id == ""` and a worker with no `ctx` (MC-2).

**Allowed moves — total table.** Rows are *from*, columns are *to*. ✓ = allowed, with the only
requester that may ask for it. ✗ = never requested; reaching one raises a programming error, which
is not a domain error. `=` = same state: no write, no event, not a move.

| from \ to | in_queue | in_progress | awaiting | resolved | failed | DELETE |
|---|---|---|---|---|---|---|
| ∅ (creation) | ✓ create | ✓ create | ✓ create | ✗ | ✗ (creation is refused for failed/cancelled, §5 r3) | ✗ |
| in_queue | = | ✓ sync | ✓ sync (e.g. force-ready of a pending task) | ✗ | ✓ sync | ✓ delete op |
| in_progress | ✓ sync (working → pending when every step is removed, §14C) | = | ✓ sync | ✗ | ✓ sync | ✓ delete op |
| awaiting | ✓ sync (ready/resolved → pending, §14C) | ✓ sync (reopen) | = | ✓ **Scanner only** | ✓ sync | ✓ delete op |
| resolved | — sync skips (§5 r1) | — | — | = | — | ✓ delete op |
| failed | — sync skips | — | — | — | = | ✓ delete op |

**Counter effect** (§5 rule 5): `q` = the assignment's stored `quantity`. `−q` on *from*'s counter
if *from* is active, `+q` on *to*'s if *to* is active. One statement per move:
`UPDATE stock_report_items SET quantity_in_queue = quantity_in_queue + :dq, quantity_in_progress =
quantity_in_progress + :dp, quantity_awaiting = quantity_awaiting + :da WHERE client_id = :id
RETURNING quantity_requested, quantity_in_queue, quantity_in_progress, quantity_awaiting,
priority, priority_order`. This is column-referencing, so there is never a read-then-assign (§2.4,
`32_concurrency.md`). The RETURNING values are the only source for event payloads, because an ORM
instance loaded earlier is stale after a Core UPDATE.

**When a move would drive a counter below 0 — self-heal** (owner, card 9 → C, round 7; §14D D1).
Only drift can cause this: with correct counters `col ≥ q` always holds for the *from* counter.
- *Guarded statement.* The UPDATE above carries `AND quantity_in_queue + :dq >= 0 AND
  quantity_in_progress + :dp >= 0 AND quantity_awaiting + :da >= 0`. The row is already locked
  (lock order step 4) and exists, so **0 rows returned means exactly "a counter would go
  negative"**. There is no clamp (`greatest`) anywhere in this operation.
  *(Re-check, round 7.)* The WHERE clause is **exactly** `client_id = :id` plus the three guards —
  no `workspace_id`, `is_deleted` or any other predicate, because either would make 0 rows
  ambiguous. Workspace and liveness are settled before the statement runs: the step-4 lock selects
  the row by `client_id`, `workspace_id` and `is_deleted = false`, and the move runs only after
  step 5's re-read found the assignment non-deleted, which implies a live row (MC-16: a row is
  never soft-deleted before its assignments). A repair statement that itself returns ≠ 1 row is a
  programming error (500), never a second repair.
- *Write order — every path, every target (re-check, round 7).* The operation first writes the
  assignment's own columns and flushes: its new `state`; for `DELETE`, its soft-delete
  (`is_deleted`, `deleted_at`, `deleted_by_id` per MC-17); its `updated_*` per MC-17; its credit
  memory change per MC-5. Only then does it issue the guarded counter UPDATE, and after that the
  goal-total statement. So the flush precedes any recomputation without a separate branch. The
  soft-delete belongs to `move_assignment(…, DELETE)`: where MC-14 and MC-16 say "`move_assignment(…,
  DELETE)`, soft-delete it", the second clause names this same write and is not repeated.
  **Creation:** the assignment is inserted with `state` = the target and flushed (the insert *is*
  the own-columns write of `∅ → B`), and the operation is told the move is `∅ → B` by its caller —
  it never infers `∅` from the stored `state`, which is `NOT NULL`. Creation cannot trip the guard
  (every delta is `≥ 0`, and a zero delta cannot fail while the DB checks hold), and were it to,
  the recomputation already counts the new assignment, which is the correct post-move value.
- *Inline repair, same transaction, same lock.* On 0 rows: the moving assignment's new `state`
  (or its soft-delete) is already written and flushed (write order above); then one statement sets all three
  counters to their recomputed absolute values — Σ `quantity` of the row's non-deleted assignments
  in that state (the MC-20 `counter_*` definition, the one definition of "correct") — with the
  same RETURNING list. The absolute values replace the delta; the delta is not applied on top.
  The move then proceeds normally (goal effect, flag, events from the RETURNING values).
- *Why the recomputation cannot race (re-check, round 7; MC-11).* Its inputs are the `state`,
  `is_deleted` and `quantity` of the row's assignments. `quantity` is immutable, and **every
  writer of an assignment's `state`, `is_deleted` or credit memory holds that assignment's row
  lock (step 4) before writing** — creation (MC-13 phase 2), the sync (MC-2 step 5), the Scanner
  resolve (MC-10), every delete path (MC-14, MC-16), and the manual repair (§12A). Under READ
  COMMITTED the recomputation statement's snapshot is taken after this transaction holds the lock,
  so it sees every earlier lock holder's committed writes plus this transaction's flushed ones,
  and no other writer can change an input until commit. A new writer of those columns that skips
  the row lock breaks this premise; the MC-11 two-session instrument is its test.
- *Trace* (card 9a → A): one repair record (§12A) per counter column where
  `stored_before + delta ≠ recomputed`, trigger `inline:<operation>`, `created_by_id` NULL, plus
  one `logger.warning` per record naming the row, field, stored and recomputed values **and the
  move's delta for that column**. At least the column that would have gone negative always qualifies.
  *(Re-check, round 7.)* `stored_before` is read **in this transaction after the guarded UPDATE
  returned 0 rows**, by a fresh `SELECT` of the three columns (the row is locked by this
  transaction, so the read is current) or by the repair statement's own pre-update values. It is
  never taken from an ORM instance, which is stale after any earlier Core UPDATE of the same row in
  the same transaction (the row-deletion cascade, the grouped processed update). `delta` is the
  per-column delta of *this* statement (for a grouped statement, the group's sum, §8B D6 plan).
  The record's `stored_value` is `stored_before` (§12A: "the value before the operation"), so an
  inline record may read `stored = recomputed` (the instrument's `0 → 0`): the record's existence,
  not the pair's difference, is the correction, and the warning's delta carries the magnitude.
- *Second trigger — row deletion* (P36): MC-16's "counters are asserted to be 0 before the row's
  soft-delete" becomes: after every assignment is moved out, any counter ≠ 0 is set to 0 (its
  recomputed value, since no non-deleted assignment remains) with a repair record,
  `inline:delete_stock_report_item`. The deletion is not blocked.
- The DB checks `ck_stock_report_items_*_nonneg` (`>= 0`) **stay**. They are now reachable only by
  a defect in the repair itself, and then abort the transaction (500, nothing commits).
- Inline repair fires only on the *downward* case. A counter that drifted **upward** never
  triggers it; only the consistency check finds it and only the manual repair command fixes it
  (§12A), which is why that command is must-ship.
- *Instrument:* plant drift by raw SQL (`quantity_in_queue = 0` while a q = 4 assignment is
  queued), run the move, assert: the move succeeded, all three counters equal the recomputation,
  exactly one repair record with `stored = 0`, `recomputed = 0` for `in_queue` and none for the
  columns that were right, and MC-20 returns `[]`. Planted defect: drop the `>= 0` guard from the
  WHERE → the DB check aborts and the row reddens.
  *Two more instrument rows (re-check, round 7), each with its own planted defect:*
  (b) **DELETE write order** — the same planted drift, then the user deletes the queued
  assignment: `quantity_in_queue` ends 0, one record (`stored 0`, `recomputed 0`), MC-20 `[]`.
  Planted defect: issue the soft-delete after the counter statement → the recomputation still
  counts the assignment, `quantity_in_queue` ends 4, MC-20 reports it.
  (c) **Fresh `stored_before`** — a row with A1 (q = 2) and A2 (q = 3), `A1.client_id <
  A2.client_id` (the cascade's order), both queued, drift planted
  as `quantity_in_queue = 3` (truth 5); delete the row. A1's move leaves 1 (no repair); A2's move
  would write −2 → repair to 0 with one record `stored 1`, `recomputed 0`,
  `inline:delete_stock_report_item`. Planted defect: read `stored_before` from the row's ORM
  instance (3, loaded at the lock) → `3 − 3 = 0 = recomputed` → no record, and the row reddens.

**Goal effect:** §6A (MC-5), applied in the same call after the counter UPDATE.

**Global lock order** (every Stock Report path, and every task command once it syncs). Always
acquire in this order, never backwards, and within each class in ascending `client_id`:

1. `pg_advisory_xact_lock(hashtext('stock_report_order:' || workspace_id))` (ordering operations
   only, MC-7);
2. `items` rows: `SELECT … FOR UPDATE` (assignment creation, `delete_item`, the category guard);
3. `tasks` rows: `SELECT … FOR UPDATE`, or the task command's own `UPDATE` of `tasks.state`,
   flushed before step 4 (MC-2);
4. `stock_report_items` rows: `SELECT … FOR UPDATE` with `populate_existing`;
5. `stock_task_assignments` rows: `SELECT … FOR UPDATE` with `populate_existing`, then **re-read
   `state` and `is_deleted` after the lock** and decide on those values;
6. `stock_report_history_records`: row UPDATE (goal totals) and INSERT.

An unlocked read is allowed only to discover ids to lock (assignment → its `stock_report_item_id`
and `task_id`, both immutable). The existing precedent orders Items → Tasks
(`bm/services/commands/items/cancel_upholstery_requirements.py:lock_and_filter_items_without_active_tasks`,
used by `delete_task`), which is consistent with this order.

**MC-11 — two writers on one assignment** (serves M1, M2; §14B B5 made mechanical). The Scanner
resolve and the task sync both lock the row (step 4) and then the assignment (step 5), and both
re-read the state after the lock. Under Postgres' default READ COMMITTED, a `SELECT … FOR UPDATE`
that waited returns the latest committed version, and `populate_existing` makes the ORM instance
take it. So the second writer always decides on what the first committed:

| Order | First commits | Second then sees | Final assignment | Counters (net) | Goal record G it was credited to |
|---|---|---|---|---|---|
| Scanner first | awaiting → resolved; `awaiting −q` | `resolved` → sync skips (§5 r1), no write, no event | resolved | awaiting −q | unchanged; credit kept |
| Task reopen first | awaiting → in_progress; `awaiting −q`, `in_progress +q` | `in_progress` → Scanner entry `ignored`, reason `not_awaiting`, no write | in_progress | awaiting −q, in_progress +q | `G −q`, credit cleared |

Proven with two sessions released by a barrier after each has done its unlocked id discovery.
Each order is forced by which session takes the row lock first. Each row asserts assignment state,
all three counters, G's total, the credit memory, and the events of both requests.

**MC-16 — soft-delete interplay: every predicate, and the delete cascade** (serves M1, M4, M6).

| Rule | Deleted-row predicate |
|---|---|
| Row identity (MC-4) | `stock_report_items.is_deleted = false` |
| One active assignment per item / per task | `is_deleted = false AND state IN active` |
| Counters (M1 recomputation) | Σ `quantity` over `is_deleted = false` assignments by state. A deleted assignment contributes 0, because the delete op moved its units out before soft-deleting it |
| `Task.is_stock_assignment` | `EXISTS is_deleted = false` assignment |
| Ordering groups (MC-7) | `stock_report_items.is_deleted = false` |
| "Current goal record" (MC-5) | most recent `is_deleted = false` goal record of the row |
| Goal total recomputation (MC-5) | **includes** soft-deleted assignments (a resolved assignment keeps its credit when deleted) |
| Category lookup (demand, creation) | `item_categories.is_deleted = false` |
| Item lookup (processed, creation, guard) | `items.is_deleted = false` |
| Task lookup (creation) | `tasks.is_deleted = false` |

A row, assignment or history record, once soft-deleted, is never written again. The one exception
is a goal record's total, which may still be *decremented* by an assignment credited to it while
that assignment is deleted inside the **same** row-deletion transaction, before the record's own
soft-delete (order below). No command soft-deletes an `ItemCategory` today (only the workspace
reset hard-deletes, §12A), so a row whose category is later deleted keeps working and serializes
the deleted category's name.

**Row-deletion cascade order** (§9 "delete StockReportItem"), inside one transaction: advisory lock
→ lock the Tasks of the row's non-deleted assignments (ascending) → lock the row and its priority
group (ascending) → lock the assignments (ascending). Then, for each assignment in ascending
`client_id`: `move_assignment(…, DELETE)` (units out, goal subtraction if awaiting), soft-delete
it, recompute its task's flag. Then close the row's gap in its group (MC-7), soft-delete the row
(`deleted_*` plus `updated_*`, MC-17), and soft-delete its history records. The row's three
counters are asserted to be 0 before its soft-delete (round 7: a non-zero counter is repaired to
0 with a repair record and the deletion proceeds — MC-1 second trigger, §14C C39). The row is never soft-deleted before its
assignments.

### 5B. Task-state sync and task-side removals — contracts MC-2, MC-14 (round 6)

**MC-2 — the sync** (serves M2; HC-4; §5 rule 4).

`sync_task_stock_assignments(session, changed: list[tuple[Task, TaskStateEnum]], *, workspace_id,
actor_user_id, now) -> list[event]`. `changed` holds each task with the state the command captured
when it loaded it. It takes no `ctx`, because the deferred-completion worker has none.

1. **Where it is called:** once per command, inside the command's transaction, after the
   command's **last** write to `Task.state`, with every task whose `state` differs from the
   captured one. Every dispatching command already captures the loaded state (`old_task_state`,
   `old_task_states`, or `original_state` in resolve/fail/cancel/force-ready) for its own event or
   history record. A task whose state did not **net**
   change is not passed. So `remove_task_step`'s `ready → pending → ready` inside one transaction
   moves nothing, which is what HC-4 requires ("never from an assumed path").
2. **First statement: `await session.flush()`**, so this transaction holds the task rows' locks
   (its own UPDATE) before any read.
3. **Per task, ascending `client_id`:** a fresh query for the non-deleted active assignment of
   that `task_id` (at most one, MC-4). None → skip. This query **is** the "cheap skip" of §4.4.
   The ORM `task.is_stock_assignment` is not read, because it was loaded before the lock and may
   predate a creation that committed in between. (Creation locks the Task row, MC-13, so no
   creation can commit *after* step 2.)
4. `target = MAP[task.state]`, where `task.state` is the value this transaction wrote. `MAP` is §5
   over all eight `TaskStateEnum` members (`bm/domain/tasks/enums.py:TaskStateEnum`). A test
   asserts `set(MAP) == set(TaskStateEnum)`, so a ninth member fails loudly rather than defaulting.
5. Lock the row, then the assignment (MC-1). Re-read. If it is now terminal or deleted → skip. If
   `state == target` → skip. Otherwise `move_assignment` with `actor_user_id` and `now`.
6. Return the events. The command appends them to its own pending list and dispatches after
   commit (`architecture/06_commands_local.md` "Event emission rule").

*Why command level and not inside the three helpers:* the helpers set intermediate states within
one transaction. `remove_task_step` writes `→ pending` and then `maybe_evaluate_task_ready` may
write `→ ready`. A helper-level sync would move the assignment awaiting → in_queue → awaiting: it
would un-credit and re-credit the goal, possibly onto a *different* goal record, and emit two
spurious events. `maybe_advance_task_to_working` is a plain `def` with no session, which does not
matter at command level.

**Write-site audit: the complete list of sync call sites.** Search, 2026-09-18: scope is
`app/beyo_manager/**/*.py` and `app/scripts/**/*.py`, excluding `app/tests/**` and `app/migrations/**`.
Terms: `\.state\s*=[^=]` (every attribute write named `state`), `setattr\(`, `update\(\s*Task`,
`(^|[^A-Za-z_])Task\(` with a `state=` keyword, `text\(` containing `tasks`, and callers of the
three helpers and of `_apply_step_transition`. Result: 8 `Task.state` assignments + 1 constructor
(the §2.3 table is complete for *writes*). Every other `.state =` hit is an execution task,
scheduler, case, step or requirement. Every `setattr` loop names a constant field set that
excludes `state` (`update_task.py:_DIRECT_FIELDS`, `update_task_post_handling.py:_DIRECT_FIELDS`).
§2.3's list of *callers* is incomplete: it omits three drivers of the core.

| # | Sync call site (function) | Writes reached | Session / transaction owner | Actor | Event path |
|---|---|---|---|---|---|
| S1 | `task_steps/transition_step_state.py:transition_step_state` | advance, evaluate-ready | `ctx.session`, own `maybe_begin` | `ctx.user_id` | appended to `pending_events` |
| S2 | `task_steps/transition_step_state_batch.py:transition_step_state_batch` (all `changed_tasks`, one call) | advance, evaluate-ready via core | same | `ctx.user_id` | appended to `pending_events` |
| S3 | `tasks/force_task_ready.py:force_task_ready` | evaluate-ready (core + direct) | same | `ctx.user_id` (manager) | appended to `pending_events` |
| S4 | `tasks/resolve_task.py:resolve_task` | `→ resolved` | same | `ctx.user_id` | its dispatch list |
| S5 | `tasks/fail_task.py:fail_task` | `→ failed` | same | `ctx.user_id` | its dispatch list |
| S6 | `tasks/cancel_task.py:cancel_task` | `→ cancelled` | same | `ctx.user_id` | its dispatch list |
| S7 | `task_steps/add_task_steps.py:add_task_steps` | `pending → assigned`, reopen `ready → working` | same | `ctx.user_id` | appended to `pending_events` |
| S8 | `task_steps/remove_task_step.py:_remove_task_steps_in_session` (serves `remove_task_step` and `remove_task_steps`) | `→ pending`, evaluate-ready | caller's `maybe_begin` | `ctx.user_id` | returned in its tuple → `_dispatch_remove_step_events` |
| S9 | `services/tasks/task_steps/finalize_pending_step_completion.py:handle_finalize_pending_step_completion` (dormant worker) | evaluate-ready | own `get_db_session()` + `session.begin()` | payload `performed_by_user_id` | its `pending_events` |

Registered as **no sync**, with the reason the guard checks:
- `tasks/create_task.py:create_task` — `Task(state=…)`: no assignment can reference a task that
  does not exist yet.
- Core drivers that pass the literal `new_state=TaskStepStateEnum.PAUSED`, so neither helper can
  fire: `users/declare_worker_state.py:declare_worker_state`,
  `users/_clock_worker_shift.py:clock_out_shift_for_user`,
  `cases/_case_created_step_pause.py:pause_task_working_steps_for_case`.

**The guard (§5 rule 4; charter rule 15)**, `test_task_state_write_sites_are_registered`, an AST
test over the scope above:
- It collects (a) every assignment whose target is an attribute named `state`; (b) every
  `setattr(…)` call; (c) every `update(Task)` / `insert(Task)`; (d) every `Task(…)` call with a
  `state=` keyword; (e) every call to `maybe_advance_task_to_working`,
  `maybe_reopen_task_to_working`, `maybe_evaluate_task_ready` and `_apply_step_transition`;
  **(f) every raw-SQL construct naming the `tasks` table — `text(…)` and
  `session.execute` of a non-ORM statement** (owner, 2026-09-21, batch C2 review card 4).
- **Collection must be by construct, not by spelling** (owner, 2026-09-21, card 4). Classes
  (a)–(f) are satisfied only if the collector sees them **however they are written**: an
  annotated assignment (`task.state: X = …`), a tuple-target assignment, and a call reached
  through an **import alias** all count. The batch C2 reviewer planted five such forms in a live
  file at once and the guard passed without a murmur — four of them inside classes (a), (c) and
  (e) that this list already named, including one the collector's own docstring claimed to
  handle. Nothing in the codebase uses those forms today, so nothing is broken; what was broken
  is the guard's ability to catch the next person who does.
- **Four further forms, on the owner's ruling of 2026-09-21 (batch C2 re-review card 1 / R-1).**
  The re-reviewer planted eleven shapes and four still passed. The collector must also see:
  **(c-bis)** the write made through the **table object** rather than the mapper —
  `Task.__table__.update()…values(state=…)` and `update(Task.__table__)`; **(a-bis)** an
  attribute target bound by a **`for` target** (`for task.state in …`) or a **`with … as`
  target**; **(b-bis)** `setattr` reached through `builtins` (`builtins.setattr(task, "state", …)`);
  **(d-bis)** `Task(**{"state": …})` — the keyword supplied by **dict unpacking** rather than
  written literally. These are the same classes (a)–(d) the list already names, in four more
  spellings, so the by-construct clause above already governs them; they are enumerated here only
  because they were measured to slip past. **Zero live instances** in `beyo_manager/` or
  `scripts/` at the time of the ruling.
- **Two exclusions, stated so they are ruled rather than assumed** (orchestrator note on the same
  ruling). The collector's scope is `beyo_manager/` and `scripts/`, excluding any path containing
  `tests` or `migrations`. **Test files are therefore never scanned** — the three
  `Task.__table__.update()` sites in this project's own tests are outside the guard's reach and
  extending the class list does not bring them in; they are evidence that the idiom is a team
  habit, which is the reason to close the gap, not evidence of a coverage failure.
  **Migrations are likewise never scanned**, so a migration writing task state is invisible
  whatever form it uses. That exclusion is **not yet ruled** and is carried as an open owner
  question, not a decision.
- **The guard must also assert a negative** (owner, 2026-09-21, batch C2 review card 2): **no
  call to `sync_task_stock_assignments` appears inside `maybe_advance_task_to_working`,
  `maybe_reopen_task_to_working`, `maybe_evaluate_task_ready` or the shared step-transition
  core.** This is the "why command level" rule made checkable. Without it a task moving
  `ready → in_queue → ready` inside one save would credit and un-credit the same units, possibly
  against two different goals. The reviewer planted exactly that call and the guard passed, so
  **this rule has never actually been guarded** — the assertion is one line and the guard already
  performs the positive form of the same check.
- A checked-in registry classifies every collected site as `task_write → sync site` (S1–S9),
  `no_sync: <reason>`, `paused_driver`, or `not_task: <model>`. The test fails on any unregistered
  site and on any stale registry entry. For each `task_write`, it asserts the named sync function
  contains a call to `sync_task_stock_assignments`. For each `paused_driver`, it asserts the
  `new_state=` argument is literally `TaskStepStateEnum.PAUSED`.
- **Required probe rows**, each planted, observed red and reverted, one per sub-check (charter
  rule 12):
  - P-a: add `task.state = TaskStateEnum.STALLED` inside `tasks/update_task.py:update_task`;
  - P-b: add `setattr(task, "state", TaskStateEnum.READY)` in the same function;
  - P-c: add `await session.execute(update(Task).values(state=TaskStateEnum.READY))` in the same
    function;
  - P-d: add a call to `maybe_evaluate_task_ready(...)` in the same function;
  - P-e: delete the `sync_task_stock_assignments` call from `tasks/resolve_task.py:resolve_task`
    (the call site, not the definition);
  - P-f: change `users/_clock_worker_shift.py:clock_out_shift_for_user`'s `new_state=` to
    `TaskStepStateEnum.COMPLETED`.
- The guard proves registration. **M2 behaviour** is proven separately: one production-path row
  per sync site S1–S8 (S9 while it is dormant: one row that drives the handler directly), each
  asserting the assignment's state against `MAP[resulting state]`.

**MC-14 — task-side and item-side removals** (serves M2, M8; §5 rule 6, §14B B4/B6).

| Hook | Where, exactly | Lock order | What it does |
|---|---|---|---|
| Task deleted | `tasks/delete_task.py:delete_task`, after the existing task `FOR UPDATE` and before `task.is_deleted = True` | Items → Task (existing) → rows → assignments | every non-deleted assignment of the task, **any state**, through `move_assignment(DELETE)`; flag recompute; events appended to its `events` list |
| PRIMARY item unlinked | `tasks/remove_item_from_task.py:remove_item_from_task` (it loads no Task today) | **new:** Task `FOR UPDATE` → rows → assignments | only when the removed `TaskItem.role == PRIMARY`: every non-deleted assignment with that `(task_id, item_id)`, any state. Removing a RELATED item does nothing (no assignment can exist on one). A swap is removal then add; `add_item_to_task` needs no hook |
| Item deleted | `items/delete_item.py:delete_item` (it loads the Item without a lock today) | **new:** Item `FOR UPDATE` → Tasks → rows → assignments | every non-deleted assignment of the item, any state (B4 "the assignment follows"); the item's tasks are untouched (P31) |
| Category change refused (B6) | `items/update_item.py:_update_item_in_session`, which covers both `update_item` and `task_post_handling/complete_task_post_handling.py`'s call | Item `FOR UPDATE` | when `item_category_id` is in `model_fields_set` **and** differs from the stored value (None-aware): lock, re-compare, then if a non-deleted assignment in `in_queue/in_progress/awaiting` exists for the item → `ConflictError` (409), message "Unassign this item from the stock report before changing its category." Setting the same value is not a change and is not refused |
| Category change through find-or-create | `items/find_or_create_item.py:find_or_create_item`, existing-item branch (also reached from `tasks/create_task.py:create_task`) | Item `FOR UPDATE` | **owner, cards 10 and 10a → A (round 7; §14D D3):** the same refusal as the row above — when the incoming category differs from the stored one (None-aware) and the item has a non-deleted assignment in `in_queue/in_progress/awaiting`: lock, re-compare, `ConflictError` (409) with the same message. Raised inside `create_task`'s transaction, so **the whole task creation fails and nothing is written** (no task, no step, no item change). The same category, or an item with no active assignment, behaves as today |

**The find-or-create guard, made exact (re-check, round 7).**
- *Condition:* `"item_category_id" in request.model_fields_set` **and** the incoming value differs
  from the stored one (None-aware), exactly as in the `update_item` row. `create_task` forwards
  `request.item.model_dump(exclude_unset=True)` (`create_task.py:253-256`), so an omitted category
  is never a change; without the `model_fields_set` term, the request's default `None` would read
  as "set to null" and refuse every task naming a board item.
- *Placement:* in `find_or_create_item.py:find_or_create_item`, inside its existing-item branch,
  before its first write to `existing` (the `_DIRECT_FIELDS` `setattr` loop): lock the matched
  Item `FOR UPDATE` with `populate_existing`, re-compare, query the active assignment, raise. The
  function's `maybe_begin` is subordinate under `create_task` (`transaction.py:maybe_begin`), no
  `begin_nested` wraps the call (`create_task.py:259`), and neither earlier step in `create_task`
  commits or dispatches (`note_writes.py`, `find_or_create_customer.py`: no `commit`, no event bus),
  so the `ConflictError` rolls back the task insert, notes and customer with the rest; events are
  dispatched only after the block.
- *Callers — each gets the 409, and refusing is right for each.* Search 2026-09-19,
  `find_or_create_item` over `app/beyo_manager/**/*.py` excluding `app/tests/**`: exactly two —
  `tasks/create_task.py:create_task` (the only caller of `create_task` is
  `routers/api_v1/tasks.py:route_create_task`) and `routers/api_v1/items.py:route_find_or_create_item`
  (`POST /api/v1/items/find-or-create`, ADMIN/MANAGER). The second is an item edit by another name —
  the door B6 already closes — so the same refusal is the ratified rule there. The
  `create_item_in_session` branch of `create_task` (no article number, no SKU) always creates a new
  item and needs no guard. No third writer of an existing item's category exists: `item_category_id\s*=[^=]`
  over the same scope returns the two item writes (`update_item.py:74`, `find_or_create_item.py:103`)
  and otherwise only constructors and queries of other models; no `update(Item)` / `UPDATE items`
  form exists, and both `setattr` loops iterate `_DIRECT_FIELDS` sets that exclude the category.
- *Lock order:* `create_task` holds `pg_advisory_xact_lock(hashtext(workspace_id))` and its own
  newly inserted (flushed, uncommitted) Task row when the guard takes the Item lock. Neither can close a
  cycle: that advisory key is taken by `create_task` alone (search `pg_advisory_xact_lock`, same
  scope: `create_task.py:99` and `create_case.py:72`'s unrelated key), and a new, uncommitted task
  row is invisible to every other transaction, so none can wait on it. No *existing* Task is locked
  before the Item, so MC-1's Items → Tasks order holds.

Deleting a *terminal* assignment moves no counter and touches no goal total (MC-5); it removes the
row from the board and clears the task flag if it was the last one. "Leaves no assignment behind"
(M2) is read as *no non-deleted assignment*, whatever its state.

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

### 6A. History arithmetic — contracts MC-5, MC-6 (mechanism-inventory, round 6)

**MC-6 — when a record is written, and what it snapshots** (serves M5).

- **Comparison base:** the row's **stored** `quantity_requested`, read after the row lock (MC-1
  step 4) in the demand transaction. For a newly inserted row it is `0`. A goal record is written
  iff `new > stored`. Examples, each a test row: `0→5` record; `5→5` none (and no write at all,
  MC-9); `5→3` none; then `3→4` **record** (4 > the stored 3, even though the goal was 5 two
  deliveries ago; "greater than the previous one" is taken literally); `4→0` none; `0→0` on a new
  row: row created, no record.
- **Priority change** `X→Y` with `X ≠ Y` (null included): exactly one `priority_change` record,
  carrying the new `priority` and new `priority_order` (null when `Y` is null). `X == Y` is a
  no-op: no record, no write, no stamp, no event (§14B B2).
- **Order move** to target `t ≠ current`: exactly one `priority_order_change` record, for the
  moved row only. Shifted neighbours get none. `t == current` is a no-op.
- **Timing and values:** each record is inserted **after** all row mutations of its operation (its
  own row and any shifted neighbours), inside the same transaction, with `created_at` = the
  operation's `now` (never a DB default, so records of one operation share one instant). It
  snapshots the row's values as they stand at that moment: `quantity_requested`, `priority`,
  `priority_order`, and `quantity_awaiting` = the row's live counter. The one exception is a goal
  record, whose `quantity_awaiting` starts at **0** (§6.1).
- A skipped demand entry (`category_not_found`) and a rejected request write no record.

**MC-5 — the goal record's running total, as a total event table** (serves M5; §6.2 made
exact).

*Current goal record* of a row = its non-deleted `quantity_requested_change` record with the
greatest `(created_at, client_id)`. It is read **after** the row lock (MC-1 step 4). The demand
webhook inserts goal records under the same lock, so a credit and a new goal serialize and the
credit always lands on whatever is current once the lock is held.

| Event on an assignment (quantity `q`) | Credit memory before | Effect on history | Credit memory after |
|---|---|---|---|
| Enters `awaiting` (from creation, `in_queue` or `in_progress`), a current goal record `G` exists | NULL | `G.quantity_awaiting += q` | `G` |
| Enters `awaiting`, the row has no goal record | NULL | none | NULL |
| `awaiting → resolved` (Scanner) | `R` or NULL | none: the record keeps the units (§6.2) | **unchanged** (kept) |
| `awaiting → in_queue / in_progress / failed` (sync) | `R` | `R.quantity_awaiting −= q`, even if `R` is no longer current | NULL |
| `awaiting → DELETE` (any delete path) | `R` | `R.quantity_awaiting −= q` | NULL (row soft-deleted) |
| Any of the three rows above | NULL (it entered awaiting before any goal existed) | none | NULL |
| `resolved → DELETE` | `R` or NULL | none: resolved work stays counted; deleting the board entry does not un-complete it | unchanged |
| `in_queue / in_progress / failed` → anything | NULL (by construction) | none | NULL |
| `R` soft-deleted, `−= q` due | — | happens only inside the row-deletion transaction, before `R`'s own soft-delete (MC-16 order); the arithmetic runs on `R` regardless | — |

- The write form is `UPDATE stock_report_history_records SET quantity_awaiting = quantity_awaiting
  ± :q WHERE client_id = :r` (column-referencing, same transaction as the move).
- **Floor.** With this table the total is exactly Σ `q` of the assignments whose memory points at
  it, so a correct system never needs a floor, and a floor can only fire on drift. §6.2's "floored
  at 0" is **replaced by self-heal** (owner, card 9 → C, round 7; §14D D1): there is no
  `greatest(…, 0)`. The subtraction is `… SET quantity_awaiting = quantity_awaiting − :q WHERE
  client_id = :r AND quantity_awaiting − :q >= 0`. 0 rows (the record is locked and exists) means
  the total would go negative: the assignment's credit memory is cleared and flushed first, then
  `R.quantity_awaiting` is set to the recomputation below, one repair record is written (target
  kind `history_record`, field `quantity_awaiting`, trigger `inline:<operation>`) with a warning,
  and the move proceeds. A DB check `ck_stock_report_history_records_quantity_awaiting_nonneg`
  (`>= 0`) stays as the backstop for a defect in the repair itself. Upward drift of a goal total
  is found by MC-20 and fixed only by the manual repair command (§12A).
  *(Re-check, round 7.)* **What protects `R`:** no lock is taken on `R` itself. `R` belongs to the
  moving assignment's row (credits only ever go to that row's current goal record, and
  `stock_report_item_id` is immutable), and **every writer of any goal total of a row holds that
  row's lock (MC-1 step 4)** — the move, the row-deletion cascade, the manual repair; the demand
  webhook only *inserts* goal records, under the same lock. So `R` is serialized by its row's lock
  whether or not it is still current. `R` exists because the assignment's FK references it and
  only the workspace reset hard-deletes history. The guarded UPDATE's WHERE is exactly
  `client_id = :r` plus the guard (no `is_deleted`, no `workspace_id`), as in MC-1. **Order:** the
  credit memory is cleared as part of the assignment's own-columns write, flushed before any
  statement on `R` (MC-1 write order), so the Σ excludes the moving assignment. `stored_before`
  for the record is read fresh, as in MC-1. Since `stored_before − q < 0 ≤ recomputed`, the rule
  `stored + delta ≠ recomputed` always yields exactly the one record stated above.
- **Recomputation (§10 made exact):** `R.quantity_awaiting = Σ quantity` over **all**
  `stock_task_assignments` with `credited_history_record_id = R`, **including soft-deleted ones**.
  This is §10's "currently crediting it plus those Scanner resolved while credited to it": the
  memory is cleared on every un-credit and kept on resolve, so the two phrasings are the same
  set. There is no contradiction with §6.2 once "kept on resolve" and "deleted rows included" are
  stated.
- **Worked sequence (a test row, exact values):** row at 10, goal `G1` (awaiting 0).
  (1) assignment `A` (q = 4) enters awaiting → `G1 = 4`, `A→G1`.
  (2) demand 10→12 → `G2` created, awaiting 0.
  (3) the task reopens → `A` in_progress → `G1 = 0`, `A→NULL`.
  (4) the task is ready again → `A` awaiting → credits the current goal → `G2 = 4`, `A→G2`.
  (5) Scanner resolves `A` → `G2 = 4`, `A→G2` kept.
  (6) the row is deleted → `A` (resolved) deleted: no counter move, `G2` stays 4; history soft-deleted.
  Recompute: `G1 = Σ{} = 0` ✓, `G2 = Σ{A} = 4` ✓. The floor never engages in this sequence.

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

### 7A. Dense ordering — contract MC-7 (mechanism-inventory, round 6)

Serves M6. A *group* is `(workspace_id, priority)` over non-deleted rows, with `priority ∈ {high,
medium, low}`. Rows with null priority have null order and form no group. Orders are 1-based.
There is no unique constraint (§2.4). Every shift is **one** column-referencing statement
(`priority_order = priority_order ± 1 WHERE <group> AND priority_order BETWEEN …
RETURNING client_id, <six event fields>`), and each returned row gets one `:updated` event (MC-19).

**Before/after tables** (group `high` = A1 B2 C3 D4; group `low` = X1 Y2):

| Operation | Rule | After |
|---|---|---|
| Move C to 1 | `t < p`: rows with order in `[t, p−1]` +1; mover → `t` | A2 B3 C1 D4 |
| Move A to 3 | `t > p`: rows in `[p+1, t]` −1; mover → `t` | B1 C2 A3 D4 |
| Move B to 2 | `t == p`: no-op (B2) | unchanged, no record, no event |
| Move to 0 or 5 | `t ∉ 1..n` (n = group size read after the locks) | 422, reason `target_out_of_range` |
| Move a null-priority row | — | 422, reason `row_has_no_priority` |
| B: high → low | source: rows with order > p −1; mover: priority = low, order = max(low)+1 (1 if empty), computed without the mover | high A1 C2 D3; low X1 Y2 B3 |
| B: high → null | source closes its gap; mover order = null | high A1 C2 D3; B null/null |
| row N (null) → high | appended at max+1 | high … D4 N5 |
| B: high → high, or null → null | no-op (B2) | unchanged |
| Delete C | source closes its gap; the deleted row keeps its own priority/order values (it is outside every group) | high A1 B2 D3 |

The accepted request values are `priority ∈ {"high","medium","low", null}` and an integer `t`.
Anything else → 422.

**Serialization.** Every ordering operation (priority change, move, row delete) first takes
`pg_advisory_xact_lock(hashtext('stock_report_order:' || workspace_id))`. That serializes ordering
operations workspace-wide and removes the phantom case: another operation moving a row *into* a
group after this one read the group. It then `SELECT … FOR UPDATE`s every non-deleted row of the
source and destination groups (plus the target row) in one statement ordered by `client_id`, and
only then reads positions and `n`. Other paths never take the advisory lock, and they take row
locks in ascending order (MC-1), so the two cannot form a cycle.

| Race in one group | What serializes it | Outcome |
|---|---|---|
| Two moves | advisory lock | the second computes on the first's committed orders; both land; still 1..n |
| Move vs priority change | advisory lock | same; the priority change's append reads `max` after the move |
| Delete vs move | advisory lock | the move that runs second sees `n−1`; a target that became `n` is out of range → 422 |
| Ordering op vs counter move on the same row | the row lock (step 4) | independent columns; both commit |

**Read order** (GET): `CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3
END, priority_order ASC`, and for the null-priority listing `created_at ASC, client_id ASC`. The
`priority` query parameter is a comma list of `high|medium|low`. Omitted or empty → `priority IS
NULL` only (owner answer). An unknown token → 422.

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

### 8A. Endpoint names and wire envelope (added 2026-09-18 so the Scanner sender can be built in parallel — naming only, no semantic change)

Both are `POST`, JSON body = the array of §8.1 / §8.2, header `x-api-key`. The router is mounted
beside the existing user-facing one, following the `…/<integration>/webhooks/<topic>` shape of
`/api/v1/connecteam/webhooks/time-activity` (`bm/routers/api_v1/__init__.py`):

| Webhook | Path |
|---|---|
| Demand (§8.1) | `POST /api/v1/location-tracker/webhooks/stock-demand` |
| Processed (§8.2) | `POST /api/v1/location-tracker/webhooks/items-processed` |

Envelope is the backend's standard one (`bm/routers/http/response.py`): success
`{"data": …, "ok": true, "warnings": []}`; failure `{"error": "<message>", "ok": false}` with the
HTTP status carrying the class — **401** bad/missing key or unconfigured receiver, **422**
malformed body or duplicate identity, **5xx** receiver fault. The error is a human-readable
string, not a structure. Success `data`:
- demand: `{"results": [{"itemCategory", "properties", "outcome": "applied" | "category_not_found"}]}`, one per entry, request order;
- processed: `{"results": [{"article_number", "outcome": "resolved" | "ignored", "reason": <string|null>}]}`, one per entry, request order.

Two small things the v1 handoff states and this document had not (mine; mechanism-inventory
confirms or routes them): an **empty array is malformed** (422) on both webhooks, and **the same
article number twice in one processed request is not an error** — the second occurrence is simply
`ignored`, which is what replay-safety already implies.

The published copy for the Scanner team is
`docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v1_20260918.md`. Mechanism-inventory may tighten
the `reason` vocabulary and the 4xx split; any change to a published field ships as a **v2
handoff file**, never as an edit to v1.

### 8B. Webhook boundary — contracts MC-8, MC-9, MC-10 (mechanism-inventory, round 6)

These contracts fit **inside** the published v1 handoff (`docs/handoff/to_scanner/
STOCK_REPORT_WEBHOOKS_v1_20260918.md`). Where one tightens a field v1 marks "may tighten" (the
processed `reason` values), the closeout Scanner handoff must ship it as a **v2 file** (§14C C36).
Nothing here edits v1.

**MC-8 — validation order, one table per failure** (serves M7, M3).

| Step | Check | Failure → status, body | Reads / writes before this step |
|---|---|---|---|
| 1 | The route takes `Request` and reads raw bytes. **No typed body parameter**: FastAPI would parse and 422 a body before step 2 runs | — | none |
| 2 | Configuration: `MANAGER_API_KEY_TO_LOCATION_TRACKER_APP` and the workspace setting (proposed alias `LOCATION_TRACKER_WEBHOOK_WORKSPACE_ID`; the planner registers the name) are each non-`None` and non-blank after `strip()` | 401 | none |
| 3 | Header `x-api-key` present (Starlette headers are case-insensitive) and equal: `hmac.compare_digest(provided.encode("utf-8"), configured.encode("utf-8"))` | 401 | none |
| 4 | The configured workspace id names an existing `workspaces` row | 401 | this one `SELECT` |
| 5 | Body decodes as UTF-8 JSON | 422 | none further |
| 6 | Top level is an array with ≥ 1 entry; every entry has a valid shape (tables below) | 422 | none |
| 7 | Duplicates: demand, two entries with the same `(lower(strip(itemCategory)), properties_signature)` → 422. Processed: duplicates are **not** an error (v1 §4.3) | 422 (demand) | none |
| 8 | References: demand category per entry (skip = `category_not_found`); processed item → assignment per entry (MC-10) | per-entry outcome in a 200 | lookups |
| 9 | Writes, one transaction; events after commit | 200 / 5xx | — |

- **All 401 bodies are identical**: `{"error": "Unauthorized.", "ok": false}`. The cause (which
  setting is missing, header absent, mismatch, unknown workspace) is logged, never returned.
- **Bytes, not `str`, in `compare_digest`:** the `str` form raises `TypeError` on a non-ASCII
  header value, which surfaces as a 500 instead of a 401. The precedent
  (`bm/services/infra/connecteam/webhook_verifier.py:23`) compares `str` and has that defect. It is
  not copied (§14C C24).
- **Workspace to commands:** steps 8–9 run in a service that receives `workspace_id` as an
  argument resolved at step 4, and it passes it explicitly to every subordinate (find-or-create,
  `move_assignment`, history, events). `ctx.workspace_id` (which is `""` here, §2.5) is never read.
  Guard: the webhook tests build `ServiceContext(identity={})` exactly as the router does, and
  assert that rows carry the configured workspace id. Planted defect: read `ctx.workspace_id` in
  the demand service → the FK to `workspaces` fails and the test reddens.
- **422 body:** v1's `{"error": "<message>", "ok": false}`. The message names **every** offending
  entry by zero-based index and the defect (§8 "the error names every offending entry"), for
  example `"Malformed request: entry 0: quantityRequested must be an integer >= 0; entries 2 and 5
  resolve to the same identity."` Scanner is told not to parse it (v1 §3.4).

**Demand entry defects: a total table.** An entry is a JSON object. **Unknown keys are ignored**,
because v1 does not forbid them, and forbidding them would break a sender that adds a field.

| Field | Accepted | Defect → whole request 422 |
|---|---|---|
| `itemCategory` | `str` with non-blank `strip()` | missing, non-string, blank |
| `properties` | JSON object (`dict`), `{}` allowed, any value shapes inside (MC-3) | missing, `null`, array, string, number, boolean |
| `quantityRequested` | `type(v) is int` (so `true` / `false` and `5.0` are defects), `0 ≤ v ≤ 2147483647` | missing, non-integer, negative, too large |
| whole entry | object | array, string, number, `null` |
| two entries | — | same identity key (step 7) |
| unknown category | — | **not a defect**: `category_not_found`, entry skipped (P27) |

**Processed entry defects:** an entry is an object with `article_number` a `str`, non-blank after
`strip()`. Missing, non-string or blank → 422. Unknown keys are ignored.

**Category resolution (demand step 8):** among non-deleted categories of the workspace, first an
**exact** name match on `strip(itemCategory)`. Failing that, a case-insensitive match
(`func.lower(ItemCategory.name) == func.lower(:name)`, with Postgres `lower` on both sides so
Python and Postgres casing cannot diverge). Exactly one → that category. Zero, **or more than
one** → `category_not_found`, with the ambiguity logged. Case-variant names can coexist because
`uq_item_categories_workspace_name` is case-sensitive (`bm/models/tables/items/item_category.py`),
and the precedent `purchase_api.py:_find_category_id_by_name` picks one arbitrarily with
`.limit(1)`. That is not copied. v1 has no third outcome. Scanner's names equal Manager's seeded
names exactly (`bootstrap/phases/seed_item_categories.py`), except `Serving Trolleys`, which
Manager lacks and which will read `category_not_found`.

**Success bodies (v1 §3.4 / §4.3, unchanged):** demand `results[i] = {"itemCategory": <as
received>, "properties": <as received>, "outcome": "applied" | "category_not_found"}`. Processed
`results[i] = {"article_number": <as received>, "outcome": "resolved" | "ignored", "reason":
null | "item_not_found" | "no_open_assignment" | "not_awaiting"}`, in request order.

**MC-9 — what "a replay changes nothing" means** (serves M3; HC-5).

*Changes nothing* = the second delivery issues **no INSERT, UPDATE or DELETE** against
`stock_report_items`, `stock_task_assignments`, `stock_report_history_records` or `tasks`, and
dispatches **no event**. This is stronger than "rows compare equal". It is the only definition an
instrument can hold: none of the new tables uses `onupdate=` (MC-17), so an UPDATE writing equal
values would leave every row identical and still be a write.
- Demand: under the row lock, `new == stored` → **no statement is issued** (never an ORM
  assignment of an equal value). A new row is only inserted when its identity is absent. A second
  delivery of the same body therefore issues none.
- Processed: the second delivery finds the assignment `resolved` → `ignored`/`no_open_assignment`,
  and nothing is issued.
- **Instrument:** a SQLAlchemy `before_cursor_execute` listener counting INSERT/UPDATE/DELETE
  statements on those four tables during the second delivery, expecting 0, plus the captured event
  list, expecting empty. Planted defect: remove the equality short-circuit in the demand path →
  the listener counts 1 and the row reddens. A row-snapshot comparison alone could not see this
  defect.
- The response of a replay may differ from the first (processed: `resolved` then `ignored`). HC-5
  is about the database.
- **Arrival order ≠ send order** (the v1 handoff §6.3 hazard). An older demand request that lands
  after a newer one is not a replay: it writes the older numbers, and can write a **goal record
  that never existed** (newer 3, then older 5 → 5 > 3). The next full push heals the number; the
  phantom goal record stays. **Owner, card 11 → A (round 7; §14D D4):** no send-time stamp, no
  `x-sent-at`, no new column, no `stale` outcome; the v1 handoff stands. The protection is the
  sender's: the payload is built at send time (v1 §6.3), so a retry never carries old numbers.
- **The one residual case, closed on Manager's side** (owner, card 11a → A; §14D D5): a first
  call that is still running inside Manager after Scanner gave up on it (Scanner's client timeout
  is 8 s — `outbound-webhook-worker.ts:DISPATCH_TIMEOUT_MS`) could commit after the fresher retry.
  So the demand webhook runs under one new named setting with default **5 s**
  (`STOCK_DEMAND_WEBHOOK_TIMEOUT_MS = 5000`; the planner registers the final name), applied in
  two parts **(re-check, round 7 — the round-7 text claimed the per-statement limits keep the
  request under 8 s; they do not, see below)**:
  1. **The guarantee — a request deadline.** `deadline = time.monotonic() + budget`, taken at
     handler entry (MC-8 step 1, before the body is read, so a wait for a pooled connection counts
     against it). The **last action inside the owning transaction block, after the last write and
     immediately before the commit**, is `if time.monotonic() >= deadline: raise` a `DomainError`
     subclass with `http_status = 503` (the planner names it). So **no demand request commits
     later than `budget` after it entered Manager** — which is what card 11a asked for.
  2. **Per-statement limits.** The owning transaction's **first statement** is
     `SELECT set_config('statement_timeout', :ms, true), set_config('lock_timeout', :ms, true)`
     with `:ms = str(budget)`. A parameterized `SET LOCAL … = :v` is a syntax error on this stack
     (asyncpg sends `$1`; measured: `ProgrammingError`, SQLSTATE `42601`), and `set_config(…, true)`
     is its transaction-local equivalent. They stop one stuck statement or lock wait from running
     on; **they bound each statement, not the sum** (measured: two 250 ms statements under a
     300 ms limit commit after 0.51 s), which is why part 1 exists. At equal values the statement
     timer, started first, fires first even on a lock wait (measured: SQLSTATE `57014`, not
     `55P03`); `lock_timeout` is kept as ratified.
  - *One owning transaction, nothing before it.* MC-8 steps 4–9 run inside **one** owner-mode
    `maybe_begin` opened before step 4, and no statement is executed on the session before it:
    an earlier statement would autobegin a transaction, `maybe_begin` would then yield in
    subordinate mode (`transaction.py:maybe_begin`), nothing would commit, and a test sharing the
    session would still read the uncommitted rows. `set_config` is therefore the first statement
    of the request.
  - *No leak:* the settings end with the transaction; measured on the same pooled connection, the
    next transaction reads the server defaults.
  - *What the caller sees:* a statement or lock timeout reaches our code as
    `sqlalchemy.exc.DBAPIError` — **exactly that class, not `OperationalError`** — whose `.orig`
    is the asyncpg adapter's generic `Error` with `.orig.sqlstate` `57014` (statement) or `55P03`
    (lock) (installed SQLAlchemy 2.0.40 maps asyncpg's `QueryCanceledError` /
    `LockNotAvailableError` through `PostgresError → Error`, `dialects/postgresql/asyncpg.py:
    _asyncpg_error_translate`; reproduced 2026-09-19). The demand service does not catch it; the
    transaction block rolls back and `run_service`'s unexpected-error branch answers **500**. The
    deadline answers **503**. Both are 5xx, which Scanner's worker retries (it retries any
    non-2xx that is not 4xx, `outbound-webhook-worker.ts:72-91`).
  - *Liveness is not guaranteed below 8 s.* A request whose statements are each under the limit
    can still run past Scanner's 8 s client timeout (`outbound-webhook-worker.ts:12`,
    `DISPATCH_TIMEOUT_MS = 8_000`, re-read 2026-09-19 at Scanner `0d80bf2`) before reaching the
    deadline check. It then commits nothing (part 1), and Scanner sees its own timeout, not a 5xx.
    See the sender note below.
  - *Instrument (charter rule 10 — the shipped default is proven applied), three rows:*
    (i) with the setting unset, the statement listener (MC-9) records the demand request's first
    statement as the `set_config` call with both parameters equal to `str(<the setting's declared
    default>)`, read from the settings class rather than typed as a literal (charter rule 13).
    Planted defect: open the transaction with any other statement first → red;
    (ii) with the setting unset, a second session holds `FOR UPDATE` on a row the batch names for
    longer than the default; the webhook answers 500 no sooner than the default and before the
    holder releases, every row and history record is byte-identical to before, and no event is
    dispatched. Planted defect: drop the `set_config` statement → the request waits until the
    holder releases and only then answers (503, from the deadline), so the status-and-timing
    assertion reddens;
    (iii) the deadline: `time.monotonic` as seen by the demand module is advanced past the
    deadline just before the check → 503, nothing written, no event. Planted defect: delete the
    check → the request commits and the row reddens.
  - *Sender notes for the closeout handoff (additive, no v2):* a Scanner sender using another
    client timeout must keep Manager's setting below it; and **Scanner's existing worker drops,
    rather than retries, its own client timeout** — `AbortSignal.timeout` rejects with name
    `TimeoutError` and message `"The operation was aborted due to timeout"`, and `isRetryableError`
    matches on the *message* (`"TimeoutError"` is never in it; reproduced on Node 22.22.3), so the
    job completes without a retry. A stock-demand sender built on that worker must classify its
    timeout as retryable, or a Manager request that outlives 8 s loses that push until the next
    one.

**D6 statement plan — set-based, and consistent with MC-4, MC-6 and MC-9** (re-check, round 7;
§14D D6). D6 names the statements; this fixes their order and when each is omitted. As written,
MC-4's "one multi-row INSERT … ON CONFLICT DO NOTHING … over every identity in the request"
contradicts MC-9: a replay would still *issue* that INSERT (inserting 0 rows), and the MC-9
listener counts statements, not rows. This plan ships (§14C C42). Demand, inside the owning
transaction of MC-9:
1. `set_config` (MC-9). 2. The workspace `SELECT` (MC-8 step 4). 3. **Categories:** one `SELECT`
of the workspace's non-deleted categories whose `lower(name)` is in the request's set of
`lower(strip(itemCategory))`; exact-then-unique resolution (MC-8) is done in memory. 4. **Discovery,
unlocked:** one `SELECT` of `client_id`, `item_category_id`, `properties_signature` of the
non-deleted rows whose `(item_category_id, properties_signature)` is in the request's set — identity
columns only, no ORM entity load (an unlocked read only discovers ids, MC-1). 5. **Insert the
absent identities only:** one multi-row `INSERT … ON CONFLICT (…) WHERE is_deleted = false DO
NOTHING RETURNING client_id, item_category_id, properties_signature`, VALUES sorted by
`(item_category_id, properties_signature)`, inserted with `quantity_requested = 0`; **omitted when
step 4 found every identity**. A row it returns is "inserted by this request" (comparison base 0,
MC-6; `:created`, MC-4/MC-19); an identity it skips on conflict was inserted concurrently and is
treated as existing. 6. **Lock:** one `SELECT … FOR UPDATE ORDER BY client_id` over every identity
of the request (new and existing), returning current values (with `populate_existing` if it loads
entities). Its values are MC-6's comparison base for existing rows — never step 4's. 7. **One bulk
UPDATE** of `quantity_requested` for the rows where `new ≠ base` (`UPDATE … FROM (VALUES …)`,
`RETURNING` the event fields); **omitted when none** — this is MC-9's equality short-circuit at set
level. 8. **One bulk INSERT** of goal records for the rows where `new > base`; omitted when none.
9. The deadline check (MC-9 part 1). Then commit, then events.
- *MC-4 holds:* inserts are sorted, then all locks are taken in one sorted statement, the ordering
  MC-4's two-barrier test already exercises; step 4 takes no lock, so it adds no wait edge. Two
  concurrent first deliveries both find the identity absent at step 4, the second's INSERT waits
  on the first and skips it, and the second then compares under the lock against the first's
  committed value.
- *MC-9 holds:* a replay issues steps 1–4 and 6 (all `SELECT`) and omits 5, 7 and 8 — zero
  INSERT/UPDATE/DELETE on the four tables.
- *The D6 criterion counts **every** statement the request executes, `SELECT` included* (the same
  `before_cursor_execute` listener, unfiltered). A write-only count cannot see the defect D6
  forbids — a per-entry `SELECT` loop. The row compares batches of 3 and of 300 entries **of the
  same shape** (all new; all changed; all unchanged; one with an unknown category), expecting
  equal counts per shape and at most 8 statements (steps 1–8). Planted defect: resolve categories
  with one `SELECT` per entry → the 300-entry count differs and the row reddens.
- **Processed, grouped per row** (D6 "likewise groups its counter updates per row"): each entry
  is still decided per MC-10 and MC-11 (lock the row, then the assignment, re-read). The counter
  effect of every assignment moving `awaiting → resolved` on one row is one guarded statement
  with the summed delta (`quantity_awaiting − Σq`), issued after every one of those assignments'
  `resolved` states is written and flushed (MC-1 write order), rows in ascending `client_id`. On
  0 rows the MC-1 inline repair runs once for that row, with the group's summed delta in the
  record rule and the trigger `inline:items_processed`. This is `move_assignment` in grouped form,
  not a second counter path: HC-3 holds, one module owns it.

**MC-10 — processed resolution** (serves M3).

1. `number = article_number.strip()`, then an **exact, case-sensitive** equality with
   `items.article_number` among non-deleted items of the workspace. Inner spaces, slashes and
   leading zeros are significant: `"04 2 001 0034"` matches only an item stored as exactly that. No
   inner folding: Manager's write path only strips outer whitespace
   (`bm/services/commands/items/requests/__init__.py` `strip_or_none`), and folding could make two
   stored numbers equal and break the uniqueness the lookup relies on. Items whose
   `article_number` is NULL can never match (§8.2, E6).
2. The outcome is decided in this order (closed enum; each is a test row):
   `item_not_found` (no non-deleted item) → `no_open_assignment` (the item has no non-deleted
   assignment in `in_queue/in_progress/awaiting`; covers never-assigned and terminal-only) →
   `not_awaiting` (the open one is `in_queue` or `in_progress`) → `resolved` (it was `awaiting`: lock
   the row, then the assignment, re-read, and still `awaiting` → move to `resolved`; if it changed
   under the lock, report what the re-read says).
3. A duplicate number later in the same request is evaluated after the earlier one's effect (same
   transaction), so it reads `no_open_assignment`.
4. Whether Manager's stored numbers are spelled like Scanner's barcodes is **not measured**
   (§14C, open evidence N1). The live report shows `04 2 001 0034` and `87392074 / 17733559`.

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

Response shapes **— SUPERSEDED ON TWO POINTS BY §14H (2026-09-22, owner card D-4): `item_category` is four keys, not three, and Assignment is fourteen keys, not five. Read §14H before deriving anything from this paragraph.** StockReportItem carries the four quantities, priority, order, `properties`, and
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

### 9C. Assignment creation and the matcher mirror — contracts MC-12, MC-13 (mechanism-inventory, round 6)

**MC-12 — the matcher, made equal to Scanner's by construction** (serves M8; §9A made exact).

*"Manager's verdict equals Scanner's matcher"* (M8) means the following. For a Manager `Item`
(the ORM instance, as the production path holds it) and a stored criteria dict `c`, Manager's
verdict equals Scanner's
`matchesCriteria(deriveItemProperties(bag(item)), c)`
(`apps/backend/src/modules/stock/domain/property-criteria.ts:68-101`,
`best-match.ts:99-117`), for every `c` Scanner itself accepts. Here `bag(item)` is the string bag
Scanner would hold had it ingested this item's Manager properties through its purchase-API path.
Scanner commit `0d80bf2`, read 2026-09-18.

**Step 1: build the bag** from `Item.properties` (JSONB as asyncpg decodes it: `dict | None`,
values `str | int | float | bool | None | list | dict`) and `Item.quantity` (non-null `int`):
1. `properties is None` → start from `{}`.
2. Coerce every value exactly as Scanner's `toPropertyValue`
   (`shared/item-properties/purchase-api.integration.ts:47-66`) does:

   | Python value | Becomes |
   |---|---|
   | `str` | itself |
   | `bool` | `"true"` / `"false"` |
   | `int` | `str(v)` |
   | `float`, integral | `str(int(v))` (JS `String(3.0)` is `"3"`) |
   | `float`, non-integral | `repr(v)` |
   | `None` | key dropped |
   | `list` / `dict` | `json.dumps(v, separators=(",", ":"), ensure_ascii=False)` |

   Known divergence: exponent-form floats (`1e-07` in Python vs `1e-7` in JS), which occur in no
   property.
3. Trim key and value with `str.strip()`, and drop the pair if either is empty. This mirrors
   Scanner's `normalizeStoredProperties` (`repositories/location-stock.repository.ts:43-68`). A
   key collision after trimming (Scanner cannot meet one; its keys are trimmed at ingestion) is
   resolved by iterating keys in `sorted()` order, later wins.
4. Drop `qty_extensions`, `quantity`, `wood_group`, `drawers_range`. This is Scanner's
   `EXCLUDED_PURCHASE_ATTRIBUTE_KEYS` (`shared/item-properties/item-properties.ts:21-34`): the
   derived keys are never trusted from storage, and neither is set size.
5. **Relocated key:** `bag["quantity"] = str(item.quantity)`. It is added **even when
   `properties` is NULL**, because set size is a column fact in Manager (E9). Comparison is
   token equality on decimal strings: criterion `["4"]` matches `Item.quantity == 4`, and `"04"`
   cannot arise (Scanner's option values are `"1"`…`"10"`, `"12"`, `item-property-options.ts:55-58`).
6. **Derived keys** (E8). `wood_group`: if `wood_type` is in the bag, take its **first** token
   (tokenizer below), look it up in `WOOD_GROUPS` with members normalized by `strip().lower()`, and
   on a hit set `bag["wood_group"]` to the group name (`"Dark" | "Teak" | "Light"`)
   (`wood-groups.ts:27-31, 82-83`). `drawers_range`: if `drawers_qty` is in the bag,
   `s = value.strip()`, and it must fully match `[0-9]+`. That is ASCII-only on purpose: Python's
   `\d` also matches non-ASCII digits and JS's does not. Then take the first `DRAWER_RANGES` entry
   with `min ≤ int(s) ≤ max` (`1-2`, `3-5`, `6+`; `0` → none) (`drawer-ranges.ts:28-32, 77-90`). No
   hit → the key is absent.

**Step 2: evaluate every criteria key** (no short-circuit, so every failure is reported). The
tokenizer is `re.split(r"[,/]", s)` → `strip()` → drop empty → `lower()`. It never splits on `&`
(`property-criteria.ts:19-24`). Per key `k` with stored value `a`:

| Condition, checked in this order | Result |
|---|---|
| `a` is neither `None` nor a non-empty `list[str]` (a not-understood value, MC-3) | `criterion_not_understood` |
| `k == "wood_group"`: `wood_type` absent from the bag or yields no tokens | `missing_on_item` |
| `k == "wood_group"`: the source is present but derived no group (e.g. `Other`) | `no_group_for_value` (a wildcard `null` fails here too) |
| `k == "drawers_range"`: `drawers_qty` absent or blank | `missing_on_item` |
| `k == "drawers_range"`: present but in no range (`0`, `abc`, `-1`) | `no_group_for_value` |
| any other `k`: absent from the bag, or its value yields no tokens | `missing_on_item` |
| `a is None` | pass |
| any element of `a` is among the value's tokens | pass |
| otherwise | `value_not_accepted` |

The verdict is *match* iff no key failed. `{}` always matches. The reason vocabulary is **closed**:
`missing_on_item`, `value_not_accepted`, `no_group_for_value`, `criterion_not_understood`.

**Tables and drift:** `WOOD_GROUPS` and `DRAWER_RANGES` live in one module in
`bm/domain/stock_report/`, with the Scanner file paths, commit `0d80bf2` and the date beside them.
Like Scanner, the module validates at import: no member in two groups, no `,` or `/` in a name,
ranges ordered and disjoint (`wood-groups.ts:49-73`, `drawer-ranges.ts:49-71`).

**Fixture rule (charter rule 17):** every Scanner-owned shape in a criterion's fixture cites one
of the `file:symbol`s above. The criteria come from the real rules in `LC-STOCK-REPORT.md`,
normalized as `normalizeCriteria` does. The Manager item bags come from
`bm/services/queries/items/lookup/purchase_api.py:parse_purchase_api_attributes` output (string
values stripped; non-string values kept as they are, which is why step 2 exists). The hand-walk in
the round-6 handoff is the starting fixture set.

**MC-13 — creation checks, their order, and the override retry** (serves M8, M1, M4).

Request: `{"entries": [{"stock_report_item_id": str, "task_id": str, "item_id": str,
"override_property_mismatch": bool = false}, …]}`, with ≥ 1 entry. Unknown fields → 422 (a local
API, so strict).

| Phase | What | On failure |
|---|---|---|
| 0 | shape (Pydantic) | 422 |
| 1 | batch duplicates: the same `item_id` in two entries → `duplicate_item_in_batch`; the same `task_id` in two entries → `duplicate_task_in_batch` (every index involved is listed) | collected into phase 3's error |
| 2 | locks: Items (asc) → Tasks (asc) → rows (asc), existing ones only (MC-1) | — |
| 3 | per entry, in this order, the **first** failing reason: `stock_report_item_not_found` (absent, deleted or other workspace) · `task_not_found` · `item_not_found` · `item_not_task_primary` (no `TaskItem` with that `task_id`, `item_id`, `role = primary`, `removed_at IS NULL`) · `task_failed_or_cancelled` · `item_already_assigned` (any non-deleted active assignment of the item, on any row) · `item_has_no_category` · `category_mismatch` | **any** phase 1 or 3 failure → 422 `stock_assignment_refused`, listing `{index, reason}` for every failing entry; nothing written; property results not reported |
| 4 | the matcher (MC-12) on every entry | entries that fail with `override_property_mismatch = false` → 409 `stock_assignment_property_mismatch`, listing for **every** such entry `{index, stock_report_item_id, task_id, item_id, failures: [{key, reason}] sorted by key}`; nothing written |
| 5 | writes, per entry in ascending `item_id`: insert the assignment (`quantity = max(item.quantity, 1)`, `property_mismatch_overridden` = the entry failed phase 4 and was overridden), `move_assignment(∅ → MAP[task.state])`, flag `true` | — |

- Precedence: a batch with any hard failure answers 422 even if other entries also mismatch, so the
  frontend never offers an override for a batch that would fail anyway.
- The flag on an entry that matches is ignored, and `false` is stored (§9A).
- **Error envelope (local API only; not a Scanner surface):** these two errors carry structure, so
  the router renders them explicitly, following `routers/api_v1/auth.py`'s `code` precedent:
  `{"error": <message>, "ok": false, "code": "stock_assignment_refused" |
  "stock_assignment_property_mismatch", "details": [...]}`. Every other error uses `build_err`.
- **Frontend retry contract** (for the frontend handoff): on 409, show the listed failures and, on
  confirmation, resend the **whole batch** with `override_property_mismatch: true` on the listed
  entries. The retry is evaluated from scratch. Anything may have changed in between, so a
  now-hard-failing entry answers 422 and the retry does not "remember" the first response.
- Resolved tasks may be assigned (their assignment is born `awaiting` and credits the current goal,
  MC-5). Only `failed` and `cancelled` are refused (§5 r3).

### 9D. Realtime events — contract MC-19 (mechanism-inventory, round 6)

Registered as mechanism contract **MC-19**. It is not a ledger entry (§13A). Built on
`build_workspace_event` / `WorkspaceEvent` (`client_id`, `workspace_id`, `extra`)
(`bm/services/infra/events/build_event.py`).

**Net-change rule.** Per request, each touched row and each touched assignment is snapshotted at
its first lock, and its values after the last write are compared to that snapshot. **At most one
event per entity per request**, and only on a net difference: for a row, any of `quantity_requested`,
the three counters, `priority`, `priority_order`; for an assignment, `state`. A no-op, a replay, a
rolled-back request, or a move that returns to its start inside one transaction emits nothing.
Events are built only after the transaction block exits normally, and dispatched then.

| Operation | Events |
|---|---|
| Demand, new row | `stock_report_item:created` only (no `:updated` for the same row in the same request) |
| Demand, existing row, quantity changed | `stock_report_item:updated` |
| Demand, unchanged or skipped entry | none |
| Processed, resolved | `stock_task_assignment:state-changed` + one `stock_report_item:updated` per touched row |
| Assignment creation | `stock_task_assignment:created` per entry + one `:updated` per touched row (always a net change: `q ≥ 1` lands in an active counter) |
| Assignment deletion (any path) | `stock_task_assignment:deleted` per assignment + `:updated` per row whose counters net-changed (deleting a terminal assignment moves no counter, so no `:updated`) |
| Task sync | `stock_task_assignment:state-changed` per moved assignment + `:updated` per touched row |
| Priority change / move | `:updated` for the moved row + one per shifted neighbour |
| Row deletion | `stock_report_item:deleted` for the row, `stock_task_assignment:deleted` per assignment, `:updated` per shifted neighbour; no `:updated` for the deleted row |

**Payloads (`extra`):**
- `stock_report_item:updated`: `{"quantity_requested": int, "quantity_in_queue": int,
  "quantity_in_progress": int, "quantity_awaiting": int, "priority": "high"|"medium"|"low"|null,
  "priority_order": int|null}`, taken from committed values (`RETURNING` or a refreshed instance,
  never a pre-UPDATE ORM attribute).
- `stock_report_item:created` and `:deleted`: `{}`.
- The three assignment events: `{"stock_report_item_id": str, "task_id": str, "state": str}`, with
  the state after the move (for `:deleted`, the state at deletion).

`workspace_id` comes from the entity's row, never from `ctx` (§2.5). Event hand-up from task
commands: the MC-2 site table.

### 9E. Roles — contract MC-18 (mechanism-inventory, round 6)

Serves M9. Refusal happens in the router, through the existing dependency
`Depends(require_roles([...]))` (`bm/routers/utils/jwt_dep.py:require_roles`). It answers **403
"Insufficient role permissions."** before the service runs, so nothing is read or written. The 36
cells (28 from round 6, plus 8 for the consistency report and repair, round 7), each a test row (✓ = the request reaches the service; ✗ = 403):

| Operation (endpoint) | ADMIN | MANAGER | WORKER | SELLER |
|---|---|---|---|---|
| GET rows | ✓ | ✓ | ✓ | ✓ |
| GET assignments of a row | ✓ | ✓ | ✓ | ✓ |
| create assignments | ✓ | ✓ | ✓ | ✗ |
| delete assignments | ✓ | ✓ | ✓ | ✗ |
| change priority | ✓ | ✓ | ✗ | ✓ |
| change priority order | ✓ | ✓ | ✗ | ✓ |
| delete a row | ✓ | ✓ | ✗ | ✗ |
| read the consistency report (§12A; P35) | ✓ | ✓ | ✗ | ✗ |
| run the manual repair (§12A; owner, card 9b) | ✓ | ✓ | ✗ | ✗ |

The webhooks carry no role: they are key-authenticated (MC-8). A role-cell test sends a **valid**
body, because FastAPI decodes JSON before it runs dependencies, so an undecodable body would
answer 422 before the role check. The cell asserts the role refusal, not body handling.

---

## 10. Facts vs derived values

| Layer | Values |
|---|---|
| Facts from Scanner | category, properties, `quantity_requested` |
| Facts from Manager users | priority, the choice to assign or unassign a task, deletions |
| Facts from the system | assignment `state` (derived from task state at write time, then stored as the workflow truth) |
| Derived, persisted | the three counters; `properties_signature`; `priority_order`; `Task.is_stock_assignment`; the goal record's `quantity_awaiting` |
| Derived, never stored | major category of a StockReportItem |

Every persisted derived value has a stated recomputation: counters = **sum of the stored
`quantity`** of non-deleted assignments by state (HC-2a); the flag = existence of a non-deleted
assignment; the signature = the function of `properties`; a goal record's total = the stored
quantities of the assignments currently crediting it plus those Scanner resolved while credited
to it. Missing data is never inferred: an unknown category is skipped and reported (§8.1), never
guessed. The assignment's `quantity` is a **copied fact** (the item's quantity at creation), not a
derived value — it is deliberately never recomputed.

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
11. **Self-healing repair** (owner, round 7, cards 9/9a/9b — moved up from "deferred"): inline
    repair inside the transition operation, the repair-record table, and the ADMIN/MANAGER manual
    repair command with its consistency-report endpoint. §5A MC-1, §6A MC-5, §12A. The tests use it.

**Only if cheap** — nothing.

**Explicitly deferred / non-goals** — any frontend; the Scanner-side sender; migrating existing
task list endpoints to the compact serializers; taking over Scanner's stock rules, locations or
thresholds; ~~a repair mode for the consistency check~~ (**reversed by the owner in round 7** —
now must-ship item 11); repairing a row's `properties_signature` (reported only, §12A); automatic assignment of tasks to requirements; restore of deleted rows; pagination;
a local endpoint for creating StockReportItems by hand (the service supports it; nothing calls it);
bringing Shopify-sourced properties onto Manager items (E10).

### 12A. Consistency check and workspace reset — contract MC-20, plus one must-ship addition (mechanism-inventory, round 6)

**MC-20 — the read-only consistency check** (serves M1; P20; §12 item 8). It is a query function
in `bm/services/queries/stock_report/`, taking `(session, workspace_id)`. How it is exposed (CLI
under `architecture/53_operational_cli.md`, or an ADMIN endpoint) is the planner's choice and does
not change the contract. It recomputes and compares:

| `kind` | Stored | Expected |
|---|---|---|
| `counter_in_queue` / `counter_in_progress` / `counter_awaiting` | the row's column | Σ `quantity` of the row's non-deleted assignments in that state |
| `task_flag` | `tasks.is_stock_assignment` | `EXISTS` non-deleted assignment for the task, over every task of the workspace that has either |
| `order_density` | the orders of a group | exactly `1..n` with no gaps or duplicates |
| `priority_order_nullness` | `(priority, priority_order)` | both null or both non-null, on non-deleted rows |
| `goal_total` | `quantity_awaiting` of each goal record | Σ `quantity` of **all** assignments credited to it, deleted included (MC-5) |
| `signature` | `properties_signature` | `compute_properties_signature(properties)`, and `properties == normalize_stock_criteria(properties)` (MC-3 idempotence) |

Output: `{"workspace_id", "checked_at", "divergences": [{"kind", "client_id", "field", "stored",
"expected"}]}`, sorted by `(kind, client_id, field)`. An empty list means consistent.
**Read-only:** it issues no INSERT, UPDATE or DELETE. The same statement-counting listener as MC-9
asserts 0. **Proof it can observe (charter rule 15):** one planted drift per `kind`, each written
by raw SQL after a clean setup (e.g. `UPDATE stock_report_items SET quantity_in_queue =
quantity_in_queue + 1`). Each must produce exactly one divergence of that kind, with the exact
stored and expected values. That makes eight probe rows. The M1 tests end every scenario by
asserting the check returns `[]`.

**Repair — the write mode of the same recomputation** (owner, round 7: cards 9 → C, 9a → A,
9b → A; §14D D1–D2; serves M1, M5, M6). The check above stays read-only. Repair is a **separate
command** that calls the same recomputation functions, so "correct" has one definition.

*Two callers.* (1) **Inline**, from `move_assignment` and the row-deletion cascade, for one row or
one goal record, when a value would go negative (§5A MC-1, §6A MC-5). (2) **Manual**, a command
for a whole workspace, ADMIN/MANAGER only (§9E):
`POST /api/v1/stock-report/repair`, with the report at `GET /api/v1/stock-report/consistency`
(same two roles, P35). The planner may register other paths; the role cells do not move.

*What the manual command fixes* — per `kind`:

| `kind` | Repaired? | How |
|---|---|---|
| `counter_*` | yes | set to the recomputed Σ |
| `goal_total` | yes | set to the recomputed Σ (deleted assignments included, MC-5) |
| `task_flag` | yes | the MC-15 Core UPDATE (never moves `tasks.updated_at`) |
| `order_density` | yes | renumber the group `1..n`, keeping the current relative order; ties broken by ascending `client_id` |
| `priority_order_nullness` | yes | `priority` null → `priority_order` set null; `priority` set with a null order → appended at the end of its group (`max + 1`), before the density renumber |
| `signature` | **no — reported only** | re-signing a row can make it collide with another live row (MC-4); merging two rows is not a repair. The response lists these under `not_repaired` |

*Mechanics.* One transaction. Locks in MC-1 order: the workspace advisory lock first (it renumbers
groups), then the tasks whose flag diverges, then every non-deleted row, then assignments, then
history records — each class ascending. It runs the check under those locks, repairs, and re-runs
the check; the response is `{"repaired": [<divergence>…], "not_repaired": [<divergence>…]}` where
`not_repaired` holds only `signature` kinds. A clean workspace issues **zero** INSERT/UPDATE/DELETE
(the MC-9 listener) and emits no event. Rows it changes get `updated_at`/`updated_by_id` = the
caller (MC-17); inline repairs stamp nothing beyond what the move itself stamps. Events follow
the MC-19 net-change rule: one `stock_report_item:updated` per row whose event fields net-changed.
No history record is written by a repair (a renumber is not a user move).
*Mechanics, made exact (re-check, round 7).*
- *Which tasks are locked.* After the advisory lock, an **unlocked** pre-pass of the `task_flag`
  check lists the diverging tasks; they are locked ascending, then the rows, and the check re-runs
  under the locks. Correctness does not depend on the task locks: the flag's input (non-deleted
  assignments) is frozen by the row locks, because every writer of an assignment holds its row's
  lock (MC-1). The task locks exist only so the `tasks` UPDATE never waits out of order. A task
  that diverges under the locks but was missed by the pre-pass (only a defect racing the repair
  can make one) is still repaired; its UPDATE takes the lock late, and the worst outcome is a
  deadlock abort (500, nothing written), never a wrong value.
- *Stamps.* "Rows it changes" means `stock_report_items` rows: every such row whose counters or
  `priority_order` the command changes — including rows moved only by a renumber — gets
  `updated_at` = the command's `now`, `updated_by_id` = the caller. `tasks` are never stamped
  (MC-15's Core UPDATE); history records have no `updated_*`. This extends MC-17's table with a
  "manual repair" row (§14C C41); inline repairs stamp nothing beyond what the move stamps.
- *Events.* `stock_report_item:updated` per row whose event fields net-changed (counters,
  `priority_order`); `goal_total` and `task_flag` repairs emit nothing (no event exists for those
  entities, MC-19).
- *"Zero statements" (instrument d)* is counted by the MC-9 listener over the four MC-9 tables
  **plus `stock_report_repair_records`**. Lock statements (`SELECT … FOR UPDATE`, the advisory
  lock) are `SELECT`s and are not counted.

*The trace — table `stock_report_repair_records`* (owner, card 9a → A; the planner registers the
final name and prefix). Append-only, `IdentityMixin`, `workspace_id` (FK, RESTRICT), and:

| Column | Meaning |
|---|---|
| `target_kind` | enum: `stock_report_item`, `history_record`, `task`, `group` |
| `target_client_id` | the corrected entity's `client_id` (for `group`: the row whose order changed). **No FK** — the record outlives its target (P33) |
| `field` | the corrected column, e.g. `quantity_in_queue`, `quantity_awaiting`, `is_stock_assignment`, `priority_order` |
| `stored_value` | the value **before** the operation, as text |
| `recomputed_value` | the value written, as text |
| `trigger` | `inline:<operation>` (e.g. `inline:task_sync`, `inline:delete_assignments`, `inline:items_processed`, `inline:delete_stock_report_item`) or `manual` |
| `created_by_id` | the caller for `manual`; **NULL for inline** (the actor of the move is not the author of the repair) |
| `created_at` | the operation's `now` |

*Record fields, made exact (re-check, round 7).*
- `target_kind` by divergence kind: `counter_*` → `stock_report_item`; `goal_total` →
  `history_record`; `task_flag` → `task`; `priority_order_nullness` → `stock_report_item`;
  `order_density` → `group`.
- **One record per `(target_client_id, field)` per operation.** When one manual run changes a
  row's `priority_order` twice (the nullness repair appends it, then the density renumber moves
  it), it writes one record: `stored_value` = the value before the command, `recomputed_value` =
  the final value, `target_kind` = `stock_report_item` (the row's own inconsistency is the cause).
  A row changed only by the renumber gets `group`. A field whose final value equals its value
  before the command gets no record.
- Values as text: an `int` as its decimal form, a `bool` as `"true"` / `"false"` (Postgres
  `bool::text`, **not** Python's `str(True)`), and a null value as SQL `NULL` —
  `stored_value` and `recomputed_value` are nullable (`priority_order` null ↔ non-null).
- `trigger` is a closed set: `manual`, or `inline:` + one of `create_assignments`, `task_sync`,
  `delete_assignments` (user unassign), `delete_task`, `remove_item_from_task`, `delete_item`,
  `items_processed`, `delete_stock_report_item` — the caller of `move_assignment` (or of the
  cascade) that triggered it. `create_assignments` cannot fire on a correct system (MC-1) and is
  listed so the set is total.

Exactly **one record per corrected field**, and one `logger.warning` per record. No soft-delete
trio and no `updated_*`: a record is never edited or removed, except by the workspace reset. It is
not served by any endpoint in this project (the planner may add a read; none is required).
`order_density` repairs write one record per row whose `priority_order` changed.

*Instruments.* (a) For each of the eight planted-drift probes above except `signature`: run the
manual repair → the check returns `[]` for that kind, exactly one repair record with the planted
stored value and the expected recomputed value, trigger `manual`, author = caller. (b) `signature`
probe: still reported after repair, listed in `not_repaired`, no record. (c) Upward drift
(`quantity_in_queue + 1`): no inline repair fires through any move (the counter never goes
negative) — only the manual command clears it; this is the row that proves the command is needed.
(d) Clean workspace: zero statements, zero records, zero events. (e) Every M1/M5/M6 scenario
still ends by asserting the check returns `[]` **and** the repair-record table is empty — a
scenario that only passes because it self-healed is a failure (the defect families of M1 must not
hide behind the repair).
*(e), made exact (re-check, round 7).* It applies to every scenario that plants no drift. The two
assertions are **one shared helper** (check `[]` **and** zero repair records for the scenario's
workspace, `WHERE workspace_id = :ws`), so neither can be called without the other. **Proof it
bites (charter rule 15):** plant `from`'s delta as `−2q` in `move_assignment` (a double
decrement). A queued `q = 4` assignment moving to `in_progress` then trips the guard, self-heals,
and leaves the counters correct, so the check alone still returns `[]`; only the repair-record
assertion reddens. That probe is a required ledger row.

**Must-ship addition — workspace reset** (grounding: `bm/services/commands/reset/reset_app.py`
hard-deletes tasks, items, item categories and users). With `ondelete="RESTRICT"` foreign keys
from the three new tables, the reset would fail on the first workspace holding a stock row. New
reset phases hard-delete, in this order: `stock_report_repair_records` (round 7), then
`stock_task_assignments`, then
`stock_report_history_records`, then `stock_report_items`. They run before `delete_tasks`,
`delete_items`, `delete_item_categories` and `delete_users`. *(Re-check, round 7: exactly, they
are the **first four phases** of `reset_app`, before `delete_task_events`. The users phase is
`phases/delete_users.py:delete_orphan_bootstrap_users`, and `delete_workspace` runs last, so the
repair records' `workspace_id` and `created_by_id` foreign keys are cleared before either.
`stock_report_repair_records` holds no FK to the other three, so its place among the four is free;
the other three follow their FKs: assignments → history (`credited_history_record_id`) → rows.)* Invariant: a reset of a workspace
holding one row of each of the four new tables succeeds and leaves none. It traces to M1 (a board that cannot
be reset cannot be re-measured). Scope ladder: with §12 item 1.

---

## 13. Measurement ledger

| ID | Observable outcome — measured true means this shipped | Defect family it guards |
|---|---|---|
| **M1** | After every committed operation, each StockReportItem's three counters equal the **sums of stored assignment quantities** recomputed from its non-deleted assignments by state, and every `Task.is_stock_assignment` equals "has a non-deleted assignment" — including under concurrent transitions on the same item. **Round 7:** when stored values were already wrong, an operation that would write a negative value repairs that row first and succeeds, leaving exactly one repair record per corrected field; the manual repair brings a drifted workspace back to a clean consistency report. A correct system writes no repair record. | counter drift, lost updates, arithmetic applied outside the transition operation |
| **M2** | After a task's state changes by **any** path in §2.3, its active assignment equals the §5 mapping of the task's resulting state; terminal assignments are unchanged; a deleted task or an item removed from its task leaves no assignment behind. **Round 9:** an assignment that Scanner resolved early stays `resolved_early` whatever the task does afterwards. | a missed integration site; assuming intermediate states; terminal assignments revived; orphaned assignments counted forever |
| **M3** | Replaying any Scanner request leaves the database identical to one delivery; `quantity_requested` equals the last value Scanner sent; a rejected batch leaves no trace; an entry with an unknown category writes nothing, is reported back as not found, and does not stop the other entries. **Round 8:** a Scanner deletion removes the named row with every assignment on it, whatever their state, leaves every task untouched, and a replay of it changes nothing. | double-applied transitions, delta-instead-of-absolute, partial batches |
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

### 13A. Mechanism-contract register — trace targets for planner criteria (mechanism-inventory, round 6)

*MC-21 added 2026-09-21 (§14G, additive): one evaluation of an assignment's acceptability, two callers — the creation command takes the first failure, the match preview takes the whole list. Serves M4.*

The ledger above is unchanged. It still holds nine entries against the 3–7 guideline, by the
owner's acceptance, and none is merged or renumbered. Each contract below is a trace target in
its own right. A criterion cites `MC-n` and, through it, the ledger entry it serves.

| Contract | Mechanism | Lives in | Serves |
|---|---|---|---|
| MC-1 | transition operation, counter arithmetic, inline self-heal, global lock order | §5A | M1 |
| MC-2 | task-state sync, its site registry and guard | §5B | M2 |
| MC-3 | criteria normalization and signature | §4A | M4 |
| MC-4 | find-or-create; uniqueness predicates; race error | §4A | M4 |
| MC-5 | goal-record running total; self-heal of a negative total | §6A | M5 |
| MC-6 | history write rules and snapshots | §6A | M5 |
| MC-7 | dense ordering and its serialization | §7A | M6 |
| MC-8 | webhook validation order, auth, entry-defect tables | §8B | M7, M3 |
| MC-9 | replay = zero statements, zero events; arrival order; the demand time limit (cards 11, 11a) | §8B | M3 |
| MC-10 | processed resolution and its outcome vocabulary | §8B | M3 |
| MC-11 | two writers on one assignment | §5A | M1, M2 |
| MC-12 | matcher mirror, bag construction, reason vocabulary | §9C | M8 |
| MC-13 | creation checks, order, override retry | §9C | M8, M1, M4 |
| MC-14 | task-side and item-side removals; category guard on both writers (`update_item`, `find_or_create_item`) | §5B | M2, M8 |
| MC-15 | `Task.is_stock_assignment` truth and write form | §4B | M1 |
| MC-16 | soft-delete predicates; deletion cascade order | §5A | M1, M4, M6 |
| MC-17 | authorship table | §4B | M9 |
| MC-18 | role cells | §9E | M9 |
| MC-19 | realtime events | §9D | **mechanism contract only**: criteria trace to `MC-19` itself (§14 item 8) |
| MC-20 | consistency check; repair (inline + manual) and the repair-record table; workspace reset | §12A | M1, M5, M6 |

**Ledger entries that are too weak as trace targets without their contract** (findings; the
wording of the entries is unchanged):
- **M2**: "any path in §2.3" is not a checkable set, because §2.3 omits three drivers. The
  checkable set is the MC-2 registry. M2 criteria trace through MC-2.
- **M3**: "identical to one delivery" is only observable as MC-9's zero-statement definition.
- **M8**: "equals Scanner's matcher" is only decidable through MC-12's composition (the bag plus
  Scanner's functions).
- **M1**: "including under concurrent transitions" needs MC-11's two-session instrument. A
  sequential test cannot fail on a lost update.

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

### 14A. Seeds for mechanism-inventory (added after ratification, 2026-09-18 — questions, not decisions)

A post-ratification read found these unstated. None changes what was ratified; each is a place
where two implementers could diverge, so each must leave mechanism-inventory as a contract or as
an owner card — never be decided in code.

1. **Shape of `properties` on the demand webhook.** Scanner's criteria are `key → list of strings
   | null` (E3). §8.1 only says "a JSON object". Does Manager reject any other value shape? And
   does it trust Scanner's normalization (lowercased, sorted lists) for identity, or normalize
   again itself? A list sent in a different order is a different signature today (§2.2).
2. **No-op user actions.** Setting the priority an item already has, or moving it to the position
   it already holds: no history record, no authorship stamp, no event — presumably, by the same
   reasoning as the Scanner no-op in §9B. Not yet written.
3. **`Task.is_stock_assignment` visibility.** Stored for later task filtering. Whether any
   existing task response exposes it in this project is unstated; the default reading is no.
4. **An assigned item that changes underneath the assignment** — soft-deleted, moved to another
   category, or its article number edited while `awaiting`. §9A checks only at creation; the
   processed webhook looks the item up live.
5. **Races between the two writers of one assignment** — Scanner resolving while the task reopens
   in the same instant. §5 says who may do what; it does not say who wins.

### 14B. Amendment — the owner's answers to the 14A seeds (2026-09-18, round 5)

Where this section and an earlier one disagree, **this section wins**. It amends §4.1, §8.1, §9A,
§5 and §2.2 without renumbering them.

**B1 — Row identity ignores order, including inside lists (owner: "order shouldn't matter when
comparing"; the payload is one dictionary).** Amends §4.1 / §8.1. The existing signature function
sorts keys but treats list order as significant (§2.2), so Manager **normalizes the criteria
before signing and stores the normalized form**, mirroring Scanner's own `normalizeCriteria` (E3):
- a value that is a string becomes a one-element list;
- a list of strings is trimmed, lowercased, de-duplicated and sorted;
- `null` stays `null` (wildcard);
- then `compute_properties_signature` is applied, unchanged, to the normalized object.
So `{"wood_group": ["Teak","Dark"]}` and `{"wood_group": ["dark","teak"]}` are one row.
*Mine (P30):* any other value shape (number, nested object, mixed list) is stored verbatim, signed
with key-sorting only, and is never a reason to reject Scanner's request; at assignment time such
a criterion cannot be evaluated and counts as a property mismatch with reason
`criterion not understood` — overridable like any other. `properties` itself not being an object
still rejects the request (§8).

**B2 — A user action that changes nothing does nothing (owner).** Setting the priority a row
already has, or moving it to the position it already holds, returns early: no write, no history
record, no authorship stamp, no event. Same rule as the Scanner no-op in §9B.

**B3 — `Task.is_stock_assignment` is not surfaced (owner).** It is stored and maintained; no
existing or new task response exposes it in this project.

**B4 — An assigned item that changes afterwards.** Grounding, because the owner's picture and the
backend differ: the backend **does** have `DELETE /items/{id}` (`bm/services/commands/items/
delete_item.py` — soft-deletes the item and touches no task), and `update_item.py` **does** allow
`item_category_id` and `article_number` to change. The frontend simply never calls them that way.
- **Item deleted** (owner: "the assignment follows"): deleting an item removes its non-deleted
  assignment through the assignment delete operation, in the same transaction. Whether deleting
  an item should also delete its task is existing behaviour outside this project — not changed.
- **Article number edited:** nothing to do. The processed webhook looks the item up live, so the
  new number is the one that resolves.
- **Category changed while assigned:** card 8 below.

**B5 — Two writers at the same instant.** There is no queue: a Scanner call and a task change are
two independent requests, each in its own database transaction. The rule is therefore:
**the two are serialized on the assignment, and the second is evaluated against what the first
left.** Scanner first → the assignment is `resolved`, which is final, so the reopening task leaves
it alone (§5 rule 1). Task reopen first → the assignment is `in_progress`, so Scanner's report is
ignored as "not awaiting" (§8.2) and **is not remembered**: the item finishes again, waits in
`awaiting`, and stays there until Scanner reports it again or a user removes the assignment. How
the serialization is achieved (row lock vs atomic conditional update) is mechanism-inventory's
contract; that it happens, and what each order yields, is decided here.

**B6 — Category guard (owner, card 8 → A).** `update_item` refuses a change of `item_category_id`
while the item has an **active** assignment, with a conflict error telling the caller to unassign
first. A terminal (`resolved`/`failed`) or deleted assignment does not block. This is the one
change this project makes to an existing item command besides B4's deletion hook; it is what keeps
§9A rule 2 true after creation. Scope ladder: must ship, with §12 item 4.

*Card 8 as presented, for the record:* refuse (A) / allow and leave the assignment (B) / allow and
auto-remove (C); recommendation A; owner chose **A**.

### 14C. Supersession ledger — which sentence ships (mechanism-inventory, round 6)

§14B was appended, not woven in, and the same is true of this round's contracts. Where an earlier
sentence and a later section disagree, **the later section wins**, in this order: §14B, then the
lettered contracts §4A–§13A, then §1–§13. Earlier text is left as ratified, so citations stay
true. This table is the authority on each conflict. *Unilateral* = decided by this gate as a
consequence of ratified text, listed for owner ratification in the round-6 handoff. *Card* = open
at round 6; all were answered in round 7 and the rows below carry the answers (C38–C40 added).

| # | Earlier sentence | Later / source | Ships | What the other side would have shipped |
|---|---|---|---|---|
| C1 | §2.2 "list order is significant … reusable as is" | §14B B1, MC-3 | normalize, then the unchanged function | two rows for one Scanner rule re-sent in another order |
| C2 | §4.1 `properties` "stored verbatim" | §14B B1, MC-3 | stored normalized; webhook echo as received | a GET showing Scanner's spelling, signature ≠ f(stored) |
| C3 | §8.1 "`properties` must be a JSON object" | P30, MC-8 | stands for the object itself; value shapes inside never reject | — (no conflict once scoped) |
| C4 | §9A "the check happens once, at creation" | §14B B6 | stands for **properties**; the category is held by refusal after creation | — (scoped: item 3 vs item 2) |
| C5 | §2.3 "`stalled` is never written by any command today" | source | **false**: `create_task.py:create_task` accepts any `TaskStateEnum` in `request.state` for non-sellers without steps (`:109-113`); the §5 map already covers it | a map missing `stalled` would crash on a real row |
| C6 | §2.3 "Terminal tasks never reopen" | source | **false**: `remove_task_step.py:_remove_task_steps_in_session` sets `task.state = PENDING` when no steps remain, with no terminal or deleted guard (`:224-227`). MC-1 allows `awaiting → in_queue`; §5 r1 keeps `failed` assignments final | a transition table refusing `awaiting → in_queue` would 500 a user's step removal |
| C7 | §2.3 "`* → ready` (the only sanctioned entry to `ready`)" | source | **false** for creation: `create_task` can create a task already `ready`/`resolved`. No Stock Report effect (no assignment exists at creation) | — (reported upstream, handoff) |
| C8 | §2.3 "The three helpers are reached from …" (six callers) | MC-2 | incomplete: `declare_worker_state`, `_clock_worker_shift.clock_out_shift_for_user`, `_case_created_step_pause.pause_task_working_steps_for_case` also drive the core (PAUSED only; registered and guarded) | a registry missing three call sites the guard must police |
| C9 | §4.4 "a cheap skip for task sync" (via the flag) | MC-2 step 3 (*unilateral*) | the skip is an indexed assignment query; the flag is not read by the sync | a stale-flag skip leaving an assignment `in_queue` behind a `working` task |
| C10 | §6.2 "floored at 0" and §2.4 house style `greatest(…, 0)` vs §4.1 "DB check `>= 0`" and HC-2 "always reconstructable" | card 9 → **C** (owner, round 7; §14D D1) | **neither**: no floor and no plain failure — a guarded UPDATE, and on a would-be negative the row (or goal record) is recomputed from assignments in the same transaction, a repair record is written, and the move proceeds; the `>= 0` checks stay as backstop | A: a worker blocked until a developer repairs the row. B: drift hidden behind a clamp |
| C11 | §3 diagram "awaiting → resolved; quantity_awaiting − 1" | HC-2a | `− q` (units) | a set of 8 leaving 7 units "awaiting" forever |
| C12 | §8 "Either setting absent … every request refused" (no status) | M7, MC-8 | 401, identical body | — |
| C13 | §8 "a duplicate identity rejects the whole request" (both webhooks by its wording) | §8A, v1 handoff §4.3 | demand only; processed duplicates are evaluated in order (MC-10) | a Scanner batch lost to a 4xx its worker never retries |
| C14 | §8.1 "matched case-insensitively" | MC-8 (*unilateral*) | exact first, then case-insensitive only if unique, else `category_not_found` | an arbitrary pick between case-variant categories (`.limit(1)` precedent) |
| C15 | §9A reasons "missing on item / value not accepted / no group for value" and P30 "criterion not understood" | MC-12 | one closed enum of four snake_case codes | two vocabularies |
| C16 | §9A "An item with no properties matches only empty criteria" | §9A relocated `quantity` key, MC-12 step 1.5 (*unilateral*) | a set-size-only rule can match an item whose properties are NULL | refusal (`missing_on_item`) on set size for every property-less item |
| C17 | §10 goal total "currently crediting it plus those Scanner resolved while credited" | MC-5 | same set, stated as Σ over all credited assignments, **deleted included** | a recompute that drops user-deleted resolved work and reports false drift |
| C18 | §12 item 8 "recomputes counters and flags" | MC-20 (*unilateral*) | also order density, null⇔null, goal totals, signatures | drift in M5/M6/M4 fields with no instrument |
| C19 | §14 item 5 "auth → shape → references → writes" | MC-8 | config → key → workspace → decode → shape → duplicates → references → writes | — |
| C20 | §15 item 3 and Appendix A "M1–M7" | §13 | M1–M9 plus MC-19 | orphaned M8/M9 criteria |
| C21 | §4.2 "`quantity` … floor 1" | MC-13 | `max(item.quantity, 1)`; `Item.quantity` is non-null with default 1 and validated `>= 1` on update | — |
| C22 | §4.3 "Append-only" | §9, MC-16 | append-only for content; the soft-delete trio is set when the row is deleted; goal totals move per MC-5 | — |
| C23 | §5 r6 / M2 "leaves no assignment behind" | MC-14 (*unilateral*) | every non-deleted assignment of the pair, **any state** (terminal ones too); the same for item deletion | resolved rows of a deleted task still listed on the board |
| C24 | §2.5 "static-secret precedent … `hmac.compare_digest`" | MC-8 | compare **bytes** | a 500 on a non-ASCII header |
| C25 | §8A "The error is a human-readable string, not a structure" | MC-13 | stands for the webhooks; the local API's two assignment errors carry `code` + `details` | an override the frontend cannot drive by machine |
| C26 | §8A processed `reason: <string|null>` (free text in v1) | MC-10 | closed codes `item_not_found`, `no_open_assignment`, `not_awaiting`; ships to Scanner as a **v2 handoff file** at closeout | Scanner parsing prose that changes |
| C27 | §9 "delete StockReportItem … atomically" | MC-16 | the cascade order in §5A | a row soft-deleted before its assignments' units are moved out |
| C28 | §4.5 "the worker whose step transition moved the task" | MC-17 (*unilateral*) | the performer (`ctx.user_id`), which is the manager when a manager acts for a worker | a credited worker recorded for an action they did not take |
| C29 | §4.5 assignment `updated_by` table (creation, deletion unstated) | MC-17 (*unilateral*) | NULL at creation; deletion stamps only `deleted_*` | — |
| C30 | §14B B6 "the one change this project makes to an existing item command besides B4" | source: `items/find_or_create_item.py:find_or_create_item` also rewrites `item_category_id` on an existing item (reached from `create_task`) | cards 10, 10a → **A** (owner, round 7; §14D D3): both writers are guarded; `create_task` fails as a whole with the same 409 | a board row holding an item of another category, entered through task creation |
| C31 | §14B B4 "`delete_item` soft-deletes the item and touches no task" | source | true; the hook adds an Item lock (MC-14) | — |
| C32 | (absent) workspace reset | `reset/reset_app.py` | new reset phases (§12A) | a reset that fails on the first stock row |
| C33 | (absent) `remove_item_from_task` / `delete_item` locking | MC-14 (*unilateral*) | new Task / Item row locks | a creation racing an unlink, leaving an assignment on an item no longer on the task |
| C34 | §4.2 "at most one active assignment" per task (derived) | MC-4 (*unilateral*) | also a DB partial unique index | the derivation holds only while every hook fires |
| C35 | §9B "`:created` … carries the row's `client_id`" + "`:updated` whatever caused it" | MC-19 (*unilateral*) | a created row emits `:created` only | two events for one new row |
| C36 | §8A "an **empty array is malformed**" and "the same article number twice … not an error" (marked "mine" by the shaper) | MC-8, MC-10 | **confirmed** as written | — |
| C37 | v1 handoff §6.3 (sender-side ordering mitigation only) | cards 11 → **A**, 11a → **A** (owner, round 7; §14D D4–D5) | v1 stands, no stamp; Manager adds a 5 s demand time limit below Scanner's 8 s client timeout | B: a v2 handoff, a column and a `stale` outcome for a case the sender already prevents |
| C38 | §12 "a repair mode for the consistency check" deferred (owner, round 3) | owner, round 7 (card 9 → C, 9b → A) | **must-ship** (§12 item 11, §12A) | a self-heal with no tool behind it; upward drift unfixable without a developer |
| C39 | §5A MC-16 "The row's three counters are asserted to be 0 before its soft-delete" | §5A MC-1 second trigger (P36) | a non-zero counter is set to 0 with a repair record; the deletion proceeds | a row that cannot be deleted because its numbers drifted |
| C46 | §8.1 / v1 handoff §3.2 rule 4 "When a rule is deleted in Scanner, send a final `0` … it has no 'delete' webhook"; §11 "the two webhook contracts" | §14E E1–E2 (owner, round 8, card 12 → A) | a removed or changed rule is deleted through `…/webhooks/stock-demand-deleted`; a satisfied rule is still demand `0`; three Scanner webhooks | retired rules kept at 0 forever, and a changed rule leaving its old row on the board |
| C47 | §5 rule 2 "`awaiting → resolved` is performed only by the Scanner processed webhook, and only from `awaiting`"; MC-1 table `in_queue`/`in_progress` → `resolved` ✗ | §14F F1–F2 (owner, round 9) | the Scanner webhook also moves `in_queue`/`in_progress` → `resolved_early` (terminal); `awaiting → resolved` unchanged | a forgotten step leaving the assignment stuck in `awaiting` forever |
| C48 | MC-10 step 2 `not_awaiting` (ignored, no write); MC-8 success-body `reason` enum; v1 handoff §4.2 "not remembered" | §14F F5, P43 | `resolved` with reason `early`; `not_awaiting` retired | Scanner's report silently dropped |
| C49 | MC-11 "Task reopen first" row (Scanner `ignored`, `not_awaiting`) | §14F F6 | Scanner re-reads `in_progress` → `resolved_early` | — |
| C50 | P32 "ignored and not remembered" | §14F | superseded (P32 struck in part) | — |
| C40 | §6.2 and P26 "floored at 0" | MC-5 (round 7) | no floor; self-heal | see C10 |
| C41 | MC-17 "Any counter move … `updated_*` unchanged" | §12A manual repair, stamps (re-check, round 7) | the **manual** repair stamps every `stock_report_items` row it changes with the caller; inline repair and every move stamp nothing | a manual repair that leaves no author on the rows it rewrote, or an inline repair stamping a worker as editor |
| C42 | MC-4 "one multi-row INSERT … over every identity in the request" | MC-9 zero-statement replay; §8B D6 statement plan (re-check, round 7) | discover unlocked, INSERT only the absent identities (omitted when none), then one sorted `FOR UPDATE` | every replay issuing an INSERT, so the MC-9 instrument reddens on a correct system, or is weakened to count rows |
| C43 | MC-9 (round 7) "with the set-based, fixed-statement-count demand path the request stays under Scanner's 8 s" | measured: the limits are per statement (re-check, round 7) | a request deadline checked immediately before commit (503), plus the per-statement limits | a slow request made of fast statements committing after Scanner gave up: the phantom goal card 11a closed |
| C44 | MC-14 / MC-16 "`move_assignment(…, DELETE)`, soft-delete it" | MC-1 write order (re-check, round 7) | the soft-delete is written by `move_assignment`, before its counter statement; callers do not repeat it | a recomputation counting the assignment being deleted, or two writes of `deleted_*` |
| C45 | MC-1 "Creation first inserts the row with no counted state" | MC-1 write order (re-check, round 7) | inserted with `state` = the target (`NOT NULL`); the caller tells the operation the move is `∅ → B` | a nullable `state` column whose NULL rows are neither active nor terminal and escape the partial unique indexes |

### 14D. Amendment — the owner's answers to the mechanism-inventory cards (2026-09-18, round 7)

Source: the "Final owner answers" table of
`handoffs/reviewer/2026-09-18_inventory_mechanism_inventory_handoff.md`. The owner's words are
quoted; the contract text that implements each is named. §14D wins over §14B, the lettered
contracts and §1–§13 wherever they disagree.

| # | Card | Owner's words | What ships | Lives in |
|---|---|---|---|---|
| D1 | 9 → C | "I will actually prefere for the repair tool to be build and in those cases where negative values are trying to be recorded the repair tool runs first to then allow the transaction. so the repair tool is improtant to have it working in this implemtnation already ( which will be used already for tests technically )" | Self-heal: a would-be negative counter or goal total triggers a recomputation of that row / record inside the same transaction and lock; the action then succeeds. No clamp, no blocked worker. **Material — reverses the round-3 "repair deferred".** | §5A MC-1, §6A MC-5, §12 item 11, §12A |
| D2 | 9a → A, 9b → A | "9a A , 9b A" | Every repair leaves one record per corrected field plus a warning; ADMIN/MANAGER get a manual whole-workspace repair that fixes counters, goal totals, the task flag, order gaps and order nullness; signatures are reported only | §12A, §9E |
| D3 | 10, 10a → A | "yes that is correct that category re-assignment should not happen also on that task creation situation." / "10a A" | `find_or_create_item`'s existing-item branch refuses a category change for an item with an active assignment; `create_task` fails as a whole, 409 | §5B MC-14 |
| D4 | 11 → A | "i have already resolve this type of situations on the scanner handoff, the scanner will read the current requested values so it will not have stall payloads that can fabricate those types of issues. the transaction thus continues to be indepotent." | No send-time stamp; the v1 Scanner handoff is unchanged | §8B MC-9 |
| D5 | 11a → A | "11a A" | The demand webhook runs under a 5 s statement and lock timeout (a named setting), below Scanner's 8 s client timeout; an abort is a 5xx that Scanner retries | §8B MC-9 |
| D6 | — (owner, shaper session, 2026-09-18) | "i belive we can make it sql efficient" | Both webhooks are handled inside the request (no Manager background worker). The demand webhook is **set-based**: a fixed number of SQL statements per request whatever the number of entries (categories by name set; existing rows by `(item_category_id, properties_signature)` set, locked; one bulk insert with conflict handling; one bulk update of changed rows only; one bulk history insert). §8.1 "per entry" states the rule per rule, not a query loop. A criterion bounds the statement count with the MC-9 listener (same count for 3 and for 300 entries). The processed webhook likewise groups its counter updates per row | §8.1, §8B |

**Not a product change, stated so it is not lost:** the three false absence claims of §2.3 (C5–C7)
and the missing callers (C8) are corrected by §14C and MC-2; §2.3's own sentences are left as
ratified.

### 14E. Amendment — Scanner deletes a board row (owner, 2026-09-19, round 8)

**Owner's words (verbatim):** "the scanner app should be capable of deleting a stock instance,
that is because the user in the scanner app might cahnge the criteria for a stock track instance
and the scanner app should send the delete request of the old one and then the new creation of
the new one. this process of deletion should use the same find query engine the find or create
uses, but it is find and delete process, this is destructive process even for the current
assignments the stock instance is tracking in the manager app. few seconds after or in parallel
the new stock instance will be received by the manager app from the scanner app and then the user
must manually add the assignments again if they match criteria, this is a rare process but it must
exist specially in the beginning process of setting up the criterias."

**Grounding.** The destructive part already exists and is ratified: the user-facing row deletion
(§9 "delete StockReportItem", §5A MC-16 cascade order, MC-1 second self-heal trigger, §9D MC-19
row-deletion events). The lookup already exists: the demand webhook's category match (MC-8, U6)
and identity (MC-3 normalization + signature, MC-4 predicates). This amendment adds a **third
Scanner webhook** that joins the two, and nothing else.

| # | What ships | Status |
|---|---|---|
| E1 | **Scope of the delete.** Sent when a Scanner rule's criteria change (owner) **and when a rule is removed outright** (owner, card 12 → A): a rule that no longer exists in Scanner no longer exists on the board. This replaces v1/§8.1's "when a rule is deleted in Scanner, send a final 0" (§14C C46). A *satisfied* rule is still sent as demand `0` and its row stays; "absent from a demand request means untouched" also stays | owner, card 12 → A |
| E2 | **Endpoint.** `POST /api/v1/location-tracker/webhooks/stock-demand-deleted`, header `x-api-key`, same key, same workspace setting, same validation order as demand (MC-8 steps 1–6: config → key → workspace → decode → shape → duplicates). Body: a JSON array, at least one entry, of `{"itemCategory": str, "properties": object}` — the demand entry without `quantityRequested` (a `quantityRequested` field, if sent, is ignored like any unknown field, U7). Empty array → 422; two entries resolving to one identity → 422, whole request rejected | proposal P37 |
| E3 | **Ordering between delete-old and create-new — the sender guarantees it** (owner, card 13 → A). (a) Per Scanner shop, stock messages (demand and delete) are sent **one at a time**, in the order Scanner produced them; the next is not sent until the previous has a final answer (2xx, 4xx, or retries exhausted). (b) A delete is **re-validated at send time**: just before sending, Scanner checks that no location holds the old (category, properties) any more; if one does again (the rule flipped back, or P41's other-location case), the delete is **skipped**, not sent. Manager adds no ordering defence of its own beyond the deadline (E9) | owner, card 13 → A |
| E4 | **Lookup — the same engine as find-or-create** (owner): category by MC-8's rule (exact, then case-insensitive only if unique), properties normalized and signed by MC-3, row found by MC-4's live-identity predicate (`is_deleted = false`, same workspace, same `(item_category_id, properties_signature)`). Nothing is created | owner |
| E5 | **Effect — the existing row-deletion cascade, unchanged** (MC-16 order, MC-1 second self-heal trigger): every non-deleted assignment of the row, **any state** (in_queue, in_progress, awaiting, resolved, failed), through `move_assignment(DELETE)`; each task's `is_stock_assignment` recomputed; the row's gap closed in its priority group (MC-7); the row and its history soft-deleted. **Tasks, task steps and items are never touched** — a task keeps running, it is simply no longer on the board | owner ("destructive … even for the current assignments") |
| E6 | **Authorship.** `deleted_by_id` and `updated_by_id` NULL on everything it writes (Scanner is not a user, MC-17) | follows from §4.5 |
| E7 | **Response.** `{"data": {"results": [{"itemCategory", "properties", "outcome": "deleted" | "not_found" | "category_not_found"}]}, "ok": true, "warnings": []}`, one per entry in request order, echoing as received. `not_found` = no live row with that identity (never created, or already deleted — what a replay reads). Neither `not_found` nor `category_not_found` is an error; other entries are still applied | proposal P38 |
| E8 | **Idempotency (M3).** A replay reads `not_found` for every entry and issues zero INSERT/UPDATE/DELETE and no event (MC-9's definition and instrument) | follows from HC-5 |
| E9 | **Time limit.** The 5 s request deadline and `set_config` limits of MC-9 D5 apply unchanged. A delete that Scanner gave up on must not commit after a later demand for the same identity has recreated the row — the same argument as card 11a | proposal P39 |
| E10 | **What the new row starts with.** A later demand for the same or the new identity creates a **fresh** row: new `client_id`, no priority (untriaged, §7), no assignments, goal history from 0 (§6.1). Nothing is carried over from the deleted row. Users re-add assignments by hand (owner); the category and property checks of §9A apply as always | owner + proposal P40 |
| E11 | **The location trap (from E1 of the evidence doc).** Manager's row is the **sum across Scanner locations** of one (category, properties). If the changed rule was at one location and another location still has the old (category, properties), deleting Manager's row would destroy live demand and its assignments; the next demand push would recreate the row with no assignments. So the **sender rule** is: send the delete **only when no location in Scanner still holds the old (category, properties)**; otherwise send the new, lower sum through the demand webhook | proposal P41 (sender rule, goes into the Scanner handoff) |
| E12 | **Events.** Exactly MC-19's "Row deletion" row: `stock_report_item:deleted` for the row, `stock_task_assignment:deleted` per assignment, `stock_report_item:updated` per shifted neighbour in its priority group | follows from MC-19 |
| E13 | **Roles.** None — key-authenticated like the other webhooks. The user-facing row delete stays ADMIN/MANAGER (MC-18 unchanged) | follows from MC-18 |

**Ledger.** M3 gains one sentence (below, marked round 8). No ID added or moved.

**Carried to the planner — the owner waived a mechanism-inventory re-check of §14E
(2026-09-19: "I will not launc a mechanism inventory after this ratification").** The plan must
answer each of these with a stated rule and a criterion that can fail (questions, not decisions): (1) lock order of the
cascade (advisory lock → tasks → row → assignments → history) against a concurrent demand request
naming the same identity (demand locks rows, never tasks or the advisory key) and against the
processed webhook (row → assignment) — any cycle? (2) the find step of the cascade for **several
rows in one request**: sorted ascending, one advisory lock, and whether a request deleting two
rows of the same priority group closes both gaps correctly; (3) whether the D6 statement bound
applies (it need not: deletes are rare; state a bound or say why none); (4) the replay instrument
for a row whose cascade self-healed; (5) the MC-20 check after a Scanner deletion; (6) the
workspace reset is unaffected (no new table).

**Where it lands in the plan (for the orchestrator):** it depends on the row-deletion cascade
(plan phase 13) and the demand endpoint's verifier/validation (plan phase 7). The natural home is
phase 13 (cascade + its second caller), or a phase directly after it. The planner decides.

### 14F. Amendment — Scanner resolves an assignment before the task is ready (owner, 2026-09-19, round 9)

**The owner's words (verbatim):** "option A sounds really good, so your proposition is to perhaps
add a new state so that for those cases the assignment gains a state near to resolved which takes
it out of the quantity counts already, but when the task transitions to ready it doesn't need to
wait to resolved as that special state has already moved the quantities outside the counts and it
also keeps that state for tracabitlity to undertand the "forgoten" items the wokerker forgot to
mark as ready and reached the scanner app domain". The case, in the owner's earlier words: "this
can happen given the worker forgot to complete one step and the item continued through the
pipeline."

| # | What ships | Status |
|---|---|---|
| F1 | **New state `resolved_early`** in `StockTaskAssignmentStateEnum`: *Scanner processed the item while Manager's task had not reached `ready`*. **Terminal**, like `resolved` and `failed`: nothing moves an assignment out of it except deletion. Not active: it holds no counter and does not block a new assignment under the one-active-per-item / per-task indexes (MC-4) | owner (name: P42) |
| F2 | **Transitions.** Added to MC-1's table: `in_queue → resolved_early` and `in_progress → resolved_early`, requester **Scanner only** (the processed webhook). `awaiting → resolved` is unchanged; `awaiting → resolved_early` never happens. `resolved_early → DELETE` by every delete path, like `resolved`. Counter effect by §5 rule 5: `−q` on the *from* counter, nothing added | owner |
| F3 | **The task is never touched.** Its state, steps and flag stay as they are (`is_stock_assignment` stays true while the non-deleted assignment exists, P21). When the worker later finishes the step and the task reaches `ready`, the sync skips the assignment because it is terminal (§5 rule 1) — no wait, no second resolution. If the task instead fails, is cancelled or reopens, the assignment also stays `resolved_early` | owner |
| F4 | **Goal credit on entering `resolved_early`** (owner, card 14 → A): exactly as on entering `awaiting` — the row's current goal record `G` gets `G.quantity_awaiting += q` and the assignment remembers `G` (`credited_history_record_id`); with no goal record, nothing is credited. Because the state is terminal, the credit is **never removed**, except by the row-deletion cascade's history soft-delete (like `resolved`). MC-5 gains two rows: *enters `resolved_early` from `in_queue`/`in_progress`, `G` exists → `G += q`, memory `G`*; *…, no goal record → none, memory NULL*; and `resolved_early → DELETE` behaves as `resolved → DELETE` (no subtraction, memory kept) | owner, card 14 → A |
| F5 | **Processed webhook (MC-10) decision order becomes:** `item_not_found` → `no_open_assignment` → `awaiting` → **`resolved`** (reason `null`) → `in_queue` / `in_progress` → **`resolved`** with reason **`early`** (P43). The reason `not_awaiting` is **retired**: no active state is ignored any more. Lock, re-read after the lock, decide on what the re-read says (unchanged) | owner + P43 |
| F6 | **Two writers (MC-11)** — the "Task reopen first" row is replaced: the sync commits `awaiting → in_progress`, then Scanner re-reads `in_progress` → `resolved_early` (`in_progress −q`; goal per card 14; the earlier credit was already removed by the reopen). New row: *Scanner first while `in_progress`* → `resolved_early`; the sync then sees a terminal state and skips. Both orders end with no assignment in an active state and counters equal to the recomputation | follows |
| F7 | **Replay.** A second report finds `resolved_early` → `ignored` / `no_open_assignment`, zero statements (MC-9) | follows |
| F8 | **Events.** `stock_task_assignment:state-changed` with `"state": "resolved_early"`, plus `stock_report_item:updated` for the row (MC-19 "Processed, resolved" row) | follows |
| F9 | **Re-adding the same pair.** Creating an assignment for a `(task_id, item_id)` pair that already has a non-deleted `resolved` or `resolved_early` assignment is **refused**, reason `already_processed_by_scanner` (a hard 422 failure in MC-13's order, after `item_not_task_primary`). Scanner reports an item once; a re-added pair would wait in `awaiting` forever. A **new** task for the same item (it came back for repair) is not affected | proposal P44 |
| F10 | **Traceability surface.** The state is visible wherever assignments are: the row's assignment list (GET, all states), realtime events, and the consistency check's recomputations (terminal, so never counted). No new endpoint now; a workspace-wide "forgotten items" view is deferred | proposal P45 |
| F11 | **Consistency and repair (MC-20).** Unchanged definitions: counters sum active states only; a goal total sums all assignments credited to it, `resolved_early` included (card 14 → A) | follows |

**Ledger.** M2 gains one sentence (below, marked round 9). M5 is read with card 14's answer.

**Superseded (§14C C47–C50):** §5 rule 2 ("`… → resolved` only from `awaiting`"), MC-1's table row
for `in_queue` / `in_progress` → resolved (✗), MC-10's `not_awaiting`, MC-11's "Task reopen first"
row, P32's "a Scanner report that arrives while the item is back in progress is ignored and not
remembered", and the v1 handoff §4.2 "not remembered" paragraph.

**Where it lands in the plan (for the orchestrator):** phase 1 (enum member, terminal set),
phase 4 (transition table), phase 5 (goal credit per card 14), phase 8 (creation refusal F9),
phase 9 (processed decision order F5, MC-11 rows F6), phase 10 (sync skip — already covered by
"terminal", one test row).

---

### 14G. Amendment — match preview before an assignment is created (owner, 2026-09-21, round 10)

**Additive. The intention gate holds** (owner ruling, 2026-09-21): this section adds a read-only
surface over checks that are already ratified. It changes no existing contract, no invariant, no
outcome and no mechanism in MC-1…MC-20. Nothing computed here is new; only its reachability is.

**The problem.** A user building a task and an item to fulfil a board row learns whether the pair
is acceptable only by creating both and calling `POST /stock-report/assignments`. Two of MC-13's
refusals — `item_has_no_category` and `category_mismatch` — have **no override**, so by the time
the user sees one the item exists and cannot be used for the purpose it was made for. A property
mismatch is recoverable but costs a second request. The board therefore teaches its users to
create garbage and then discover it.

**MC-21 — one evaluation, two callers** (serves M4; new contract, registered in §13A).

> The acceptability of an `(item, task, row)` triple is decided by **exactly one implementation**.
> It evaluates every check MC-13 phase 3 names, **in MC-13's precedence order**, and returns the
> per-check results in that order. `create_stock_task_assignments` consumes the **first failure**
> and refuses with it; the preview consumes the **whole list** and reports it. Neither re-implements
> the other's checks, and neither may hold a check the other lacks.
>
> The evaluation is a **pure function of already-fetched entities** — it performs no I/O, so the
> creation path may supply row-locked entities and the preview plain reads. This is already true
> of `_phase3_reason` (`create_stock_task_assignments.py`), which takes `locked_rows`,
> `locked_tasks`, `locked_items`, `primary_pairs`, `processed_pairs` and `active_item_ids` and
> queries nothing; the contract makes that property binding rather than incidental.
>
> **Why a contract and not a note:** a second implementation of the ordering would drift from the
> first, and the drift surfaces as a preview that promises what the create then refuses — the
> failure mode this endpoint exists to remove. MC-13's order is deliberately not intuitive
> (`item_already_assigned` precedes `item_has_no_category` and `category_mismatch`), so a
> re-derivation would very likely get it wrong.

**The endpoint.** `POST /api/v1/stock-report/items/{client_id}/match-preview`, roles **ADMIN,
MANAGER, WORKER** — the set that may create an assignment. **Single, not batch** (owner,
2026-09-21). Read-only: it writes nothing, locks nothing and reserves nothing.

Request:

| Field | Type | Meaning |
|---|---|---|
| `task_id` | `str \| null` | the task the assignment would go on. **Null means "a task that does not exist yet"** — see the construction rule below. |
| `article_number` | `str \| null` | identifies an existing item. At most one live item per workspace carries a given value (partial unique index). |
| `sku` | `str \| null` | same; `article_number` and `sku` are alternatives, not both. |
| `item_category_id` | `str` | the candidate's category — compared by identity to the row's, as MC-13 does. |
| `properties` | `dict` | the candidate's property snapshot. |
| `quantity` | `int` | **required.** `quantity` is a matched criterion, not metadata: `build_item_property_bag` sets `bag["quantity"]`, and board criteria routinely constrain it. Omitting it would evaluate every quantity criterion against nothing. |

Response:

| Field | Meaning |
|---|---|
| `can_proceed` | no non-advisory check failed, property mismatches aside |
| `override_required` | property failures exist and are overridable with `override_property_mismatch` |
| `refusal_reason` | **what `create` would refuse with** — the first failure in MC-13's order, or null |
| `property_failures` | `[{key, reason}]`, the **same element shape** as the 409's `details[].failures[]`, reasons from `StockCriteriaMismatchReasonEnum` |
| `matched_item_client_id` | the live item the identifier resolved to, or null |
| `values_source` | `"stored"` or `"supplied"` — **which values were actually evaluated**; see the resolution rule below |
| `checks` | `[{check, result, advisory}]` in MC-13 order; `result` ∈ `pass` / `fail` / `pass_by_construction` / `not_evaluated` |

**The resolution rule — stored values win** (owner, 2026-09-21, round 10 card 2). When
`article_number` or `sku` resolves to a live item, the evaluation uses **that item's stored
category, properties and quantity**, and the body's `item_category_id`, `properties` and
`quantity` are ignored. `values_source` reads `"stored"`. When nothing resolves, the body's values
are used and it reads `"supplied"`.

This is not a convenience. `create` will act on the stored item, so a preview that honoured the
body's values could answer `true` where `create` answers `false` — **the exact divergence MC-21
forbids**. `values_source` exists so the caller can see which of the two happened rather than
having to infer it from `matched_item_client_id`, and so the divergence is observable in a test
rather than only in production.

**The construction rule.** With `task_id` null the caller is creating the task in the same act, so
**four** checks **pass by construction** and are reported `pass_by_construction`, never `pass`:
the task does not exist yet (`task_not_found` cannot fire), a new task is `pending`
(`task_failed_or_cancelled` cannot fire), the item will be PRIMARY on it
(`item_not_task_primary` cannot fire), and it has no prior assignment pair
(`already_processed_by_scanner` cannot fire).

> **⚠ Corrected 2026-09-21 — this clause said "three" and omitted `task_not_found`.** My
> omission when authoring §14G. The shipped code is right and so is the published frontend
> handoff (v2, "Four checks report `pass_by_construction`"): the evaluator's
> `PASS_BY_CONSTRUCTION_CHECKS` frozenset holds the three named above, and
> `preview_stock_task_assignment_match.py:132` adds `task_not_found` on the null-`task_id` path.
> That has to be so — with no task there is no task to find, and reporting it as a *failure*
> would make `can_proceed` false for every no-task-yet preview, which is the exact case this
> endpoint exists to serve. Found by reconciling the authority against the published handoff and
> the code, not by a review. **Owner card at the C2 gate for ratification of this wording**; the
> behaviour is unchanged and nothing needs to be rebuilt. With `task_id` supplied, all three are evaluated
against the real task. **A preview taken with a null `task_id` does not license a create against
an existing task**, and the response says so by construction because the caller can see which
results were assumed rather than measured.

**Three semantics that must not be softened.**

1. **`item_already_assigned` is advisory, always** (`advisory: true`). Another actor may take the
   item between preview and create. A subsequent refusal is correct behaviour, not a defect in
   either call. Every other check is stable between the two.
2. **An unresolved `article_number` / `sku` is a normal outcome, not a 404.** It means "no such
   item yet" — the creation case this endpoint exists for — and the category, property and
   quantity checks still run against the supplied values.
3. **The preview is not a promise.** It answers *"would this triple be accepted right now?"*, not
   *"will the create succeed?"*. Any client rendering it as a guarantee has mis-read it.

A soft-deleted, foreign or absent row in the path is `NotFound`, as every other read of a row is
(MC-16, M4).

**The reverse query is dropped** (owner, 2026-09-21). "Given this item, which board rows does it
match?" was raised, considered and **rejected as unneeded** — it would require ordering and
pagination decisions over all rows for no current caller. Recorded here so it is not re-proposed
as an oversight. If a caller appears, it is a new amendment.

### 14H. Amendment — response shapes in §9 had fallen behind the code (owner card D-4, 2026-09-22, round 11)

**This amendment corrects this document, not the code.** Both shapes below are **VERIFIED** in
`app/beyo_manager/domain/stock_report/serializers.py` and **published** to the frontend in
`HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md`. §9's prose had fallen behind them. Later
amendments win over earlier sections (§18), so **§14H is the authority for response shapes** and
§9's "Response shapes" paragraph is superseded on these two points only.

**The risk this closes is the one this project has already been bitten by:** the intention is the
document everything is re-derived from. Someone re-deriving the board from §9 would drop a key the
app renders and nine keys the frontend already consumes.

#### (a) `item_category` is **four** keys, not three

§9 says `{client_id, name, major_category}`. The shipped shape is:

```jsonc
"item_category": { "client_id": "ictg_…", "name": "Dining Chairs",
                   "major_category": "…", "image_url": "https://… | null" }
```

`image_url` was added on the **owner's own instruction of 2026-09-21** so the category's picture
reaches the stock-report board. `ItemCategory.image_url` is nullable, and **on a category with no
image the key is present and `null`, never absent** — an omitted key and a null key are different
things to a renderer. The published contract states it as `string | null` (§6.1). Pinned by plan 12
**C4(e)**, armed on three mutants including the one that proves the *present-and-null* half is
independently asserted rather than riding on the populated row's key-set check.

The rest of §9's sentence stands: there is still **no `item_type` key**, so no "ItemType" concept
leaks ahead of the Item Domain migration.

#### (b) Assignment is **fourteen** keys, not five

This is the drift the sweep found, and it is the larger of the two. §9 says *"Assignment carries
`client_id`, `state`, `stock_report_item_id`, `item`, `task`"* — five. The shipped and published
shape is **fourteen** (published contract §6.2, marked VERIFIED there):

```jsonc
{ "client_id": "sta_…", "state": "…", "stock_report_item_id": "sri_…",
  "task_id": "tsk_…", "item_id": "itm_…", "quantity": 2,
  "property_mismatch_overridden": false, "credited_history_record_id": "… | null",
  "created_at": "…", "created_by_id": "… | null",
  "updated_at": "…", "updated_by_id": "… | null",
  "item": { /* serialize_item_compact, 7 keys */ },
  "task": { /* serialize_task_compact, 12 keys */ } }
```

The nine keys §9 omitted are not new: `task_id`, `item_id`, `quantity`,
`property_mismatch_overridden`, `credited_history_record_id` and the four audit stamps. §9 was
naming the *interesting* keys in prose and was read afterwards as an exhaustive list, which is how
the gap survived to phase 13.

#### (c) What the sweep checked and found **correct** — recorded so it is not re-swept

The ruling asked for §9 to be swept rather than patched at one key. Compared against shipped code,
key by key:

| §9 shape | Shipped | Verdict |
|---|---|---|
| `item_category` | `serialize_stock_report_item` | **DRIFT — (a)**, 3 → 4 |
| Assignment | `serialize_stock_task_assignment` | **DRIFT — (b)**, 5 → 14 |
| `serialize_item_compact` (7 named) | 7 keys, same names, same order | **exact match** |
| `serialize_task_compact` (12 named) | 12 keys, same names, same order | **exact match** |
| StockReportItem "four quantities, priority, order, `properties`" | also `client_id`, `properties_signature`, `created_at`, `updated_at`, `created_by_id`, `updated_by_id` | **prose, not a key list** — it names what the capability is *about* and never claimed to be exhaustive. Left as prose deliberately; the exhaustive shape is plan 12 **C4(e)** and published contract §6.1, and duplicating a 14-key list into three documents is how (b) happened |

**The general lesson, and it is why (c) exists:** §9's failure was not a wrong key, it was **prose
being read as a specification**. Where a shape must be exact, the criterion row and the published
contract are the authority and this document points at them.

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
| P30 | Criteria values Manager cannot normalize are stored verbatim and become an overridable mismatch, never a rejected Scanner request | the raw draft allowed nested JSON; rejecting would let one odd rule block all demand |
| P31 | Deleting an item removes its assignment; it does not start deleting tasks | the owner's "the assignment follows", kept inside this project's perimeter |
| P32 | Concurrent Scanner/task writers are serialized on the assignment; ~~a Scanner report that arrives while the item is back in progress is ignored and not remembered~~ (**superseded round 9, §14F**: it resolves the assignment early) | follows from §5 rule 1 and §8.2 as ratified; stated so nobody builds a queue or a replay buffer |
| P33 | Repair records carry no FK to the thing they corrected, are never edited or soft-deleted, survive the deletion of their target, and are removed only by the workspace reset | an audit trail that disappears with the row it explains is no trail; round 7 fold |
| P34 | An inline repair writes a record only for the columns that were actually wrong (`stored + delta ≠ recomputed`), not for all three counters | the owner asked for a trace of defects (9a), not a log of every recomputation |
| P35 | The consistency report is an endpoint for ADMIN and MANAGER (`GET …/stock-report/consistency`), beside the repair command | card 9b's own story: "a manager sees it in the consistency report and presses repair"; the round-6 contract left the exposure to the planner |
| P36 | Deleting a board row whose counters are not 0 after its assignments are removed sets them to 0 with a repair record instead of failing | the same self-heal rule (D1) applied to the one other place a drifted number could block a user |
| P37 | The delete webhook is its own endpoint, `…/webhooks/stock-demand-deleted`, body `[{itemCategory, properties}]`, with demand's validation order, 422 rules and key (depends on card 13 → A; under B it is an entry kind of the demand request instead) | the owner described "a delete request … then the new creation"; mirrors the two existing webhooks |
| P38 | Delete outcomes are `deleted`, `not_found`, `category_not_found`; a missing row or category is never an error | the same skip-and-report rule the owner chose for unknown categories in round 3; makes replays harmless |
| P39 | The demand webhook's 5 s deadline applies to the delete webhook too | a late-committing delete could erase a row a later demand recreated — card 11a's own argument |
| P40 | A recreated row carries nothing over from the deleted one (no priority, no history, no assignments) | there is no link between the two identities; the owner already expects assignments to be re-added by hand |
| P41 | Scanner sends a delete only when no location still holds the old (category, properties); otherwise it sends the new sum as demand | Manager's row is location-free (round 1, card 1); deleting it for one location's edit destroys another location's live demand |
| P42 | The new state is named `resolved_early` | short, sorts next to `resolved`, and says what happened; rename freely |
| P43 | Scanner's response for an early resolution is `outcome: "resolved"`, `reason: "early"`; `not_awaiting` is retired | Scanner's job is done either way, so the outcome is the same; the reason tells Scanner's logs that Manager's task was unfinished |
| P44 | Creating an assignment for a `(task, item)` pair already resolved or resolved early by Scanner is refused (`already_processed_by_scanner`) | Scanner will not report that item again, so a re-added pair would sit in `awaiting` forever — the exact gap round 9 closes |
| P45 | No new endpoint for forgotten items now; the state shows in the existing assignment list and events | keeps the round small; a workspace-wide view is a frontend-driven follow-up |
| P21 | `is_stock_assignment` is true while any non-deleted assignment exists, including terminal ones | raw §31 sets it on create and clears it on delete only |

---

## 17. Open decisions ledger

### Open

None.

### Closed (round 10 — 2026-09-21)

- **Match preview before creation** — build it. §14G, MC-21. Prompted by the frontend hitting the
  real problem: `category_mismatch` and `item_has_no_category` have no override, so the user
  learns only after creating an item they cannot use.
- **`quantity` in the preview request** — required. It is a matched criterion
  (`build_item_property_bag` sets `bag["quantity"]`), not metadata; omitting it would silently
  mis-evaluate every quantity criterion. Found by reading the matcher, not by design.
- **Batch or single** — single.
- **Shared evaluation vs a second implementation** — shared, and made binding as MC-21 rather
  than left as guidance.
- **`assumes_new_task` flag vs optional `task_id`** — optional `task_id`. It is strictly more
  capable and mirrors the create entry shape, so the two inputs cannot drift.
- **Does §14G re-open the intention gate?** No — additive, gate holds.
- **Reverse query ("which rows does this item match?")** — **dropped**, not deferred. No caller
  now, and it would need ordering and pagination decisions over all rows. Recorded so it is not
  re-proposed as an oversight.

### Closed (round 9)

| Card | Owner answer | Folded into |
|---|---|---|
| 14 early-resolved units and the goal | A — credited to the current goal record, never removed (terminal) | §14F F4, F11; §6A MC-5 (two rows added via F4) |

### Closed (round 8)

| Card | Owner answer | Folded into |
|---|---|---|
| 12 rule removed outright in Scanner | A — the board row is deleted too, through the same webhook | §14E E1, C46, v1 handoff §3.2 rule 4 + §4A |
| 13 ordering of delete-old / create-new | A — the sender guarantees it: one stock message at a time per shop; a delete re-validated at send time and skipped if the old pair exists again | §14E E3, v1 handoff §4A, §6.3 |

### Closed (round 7 — mechanism-inventory cards)

| Card | Owner answer | Folded into |
|---|---|---|
| 9 counts already wrong when a task moves | **C** (the owner's own branch): repair first, then let the action through; the repair tool ships now | §14D D1, §5A MC-1, §6A MC-5, §12 item 11, §12A, C10, C38 |
| 9a does an automatic repair leave a trace | A — a permanent record and a warning | §14D D2, §12A |
| 9b manual repair and who runs it | A — ADMIN/MANAGER command; signatures reported only | §14D D2, §12A, §9E |
| 10 / 10a category change through a new task | A / A — the task creation is refused | §14D D3, §5B MC-14, C30 |
| 11 old demand message arriving late | A — no stamp; v1 handoff stands | §14D D4, §8B MC-9, C37 |
| 11a slow first call | A — Manager time limit 5 s | §14D D5, §8B MC-9 |

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

**Post-ratification consistency pass — 2026-09-18 (shaper; no semantic change, gate not reopened).**
- §10 still described counters as a *count* of assignments and an unknown category as *rejected* —
  both superseded by ratified rounds 1 and 3. Corrected to match HC-2a and §8.1.
- Header `shaped_from` updated: the owner deleted the raw draft after ratification.
- §14A added (lettered, nothing renumbered): five unstated points routed to mechanism-inventory
  as questions. None is decided here.

**Round 5 — 2026-09-18 — amendment §14B; gate RE-OPENED (owner: David).**
- The owner answered the five §14A seeds. B1 changes what makes two rows the same row — a material
  semantic change — so per the charter the status returns to COLLABORATING until re-ratified.
- B1 identity normalization; B2 no-op early return; B3 flag not surfaced; B4 item deletion removes
  the assignment, category change routed as card 8; B5 serialization semantics (the owner assumed
  a queue; there is none — corrected in the text).
- Grounding correction recorded in B4: item deletion and category change **are** possible through
  the backend today, contrary to the owner's picture of the app.
- M4 and M8 are unchanged in wording and now also cover B1 and card 8 respectively.

**Re-ratification — 2026-09-18 — owner: David.**
- Owner's words: "perfect, about the card 1: A is corrrect . after you finished making this
  modifications you can make the prompt for the mechanism inventory" — the single open card was
  card 8; the instruction to proceed to the next gate is the approval of amendment §14B.
- Surface presented: the five §14B answers as folded (B1 identity normalization, B2 no-op early
  return, B3 flag hidden, B4 item deletion / article number, B5 concurrent writers with the
  no-queue correction), the three proposals marked mine (P30–P32), and card 8.
- Card 8 → **A**, folded as B6. Ledger unchanged (M1–M9); M4 covers B1, M8 covers B6.
- Status → **RATIFIED**. Next gate: mechanism-inventory
  (`prompts/reviewer/2026-09-18_inventory_mechanism_inventory.md`).

**Naming addition — 2026-09-18 (shaper, at the owner's request for a Scanner handoff; no semantic change, gate not reopened).**
- §8A added: the two webhook paths, the standard envelope, the per-entry result shapes. Grounded on
  the existing router mounting and `build_ok` / `build_err`.
- Noted for mechanism-inventory (prompt MI-9 updated): absolute demand values are only
  self-correcting if a **stale delivery cannot land after a fresh one**; Scanner's existing
  outbound worker retries a job with the payload frozen at enqueue time. The v1 handoff asks
  Scanner to build the payload at send time and to re-push the full set periodically; whether
  Manager should additionally defend itself (a sent-at stamp) is an open mechanism question.

**Round 6 — 2026-09-18 — mechanism-inventory gate (reviewer role; intention at `2ee6f5b`).**
- **Twenty mechanism contracts** written as lettered sections: §4A (MC-3, MC-4), §4B (MC-15,
  MC-17), §5A (MC-1, MC-11, MC-16), §5B (MC-2, MC-14), §6A (MC-5, MC-6), §7A (MC-7), §8B (MC-8,
  MC-9, MC-10), §9C (MC-12, MC-13), §9D (MC-19), §9E (MC-18), §12A (MC-20 plus the workspace-reset
  addition). §13A registers every contract against M1–M9, with MC-19 as a mechanism contract.
  Nothing is renumbered, and no earlier sentence is edited.
- **§14C, the supersession ledger:** 37 rows (C1–C37) naming which sentence ships. Three
  absence claims of §2.3 were measured false against source (C5 `stalled` is creatable; C6 a
  terminal task returns to `pending` when its last step is removed; C7 `ready` is creatable). One
  caller list is incomplete (C8). The §6.2 floor conflicts with §4.1's check (C10). B6 missed a
  second writer of an item's category (C30).
- **Aligned with the published v1 Scanner handoff** (`2ee6f5b`): no v1 field is changed. The
  processed `reason` codes (C26) and card 11's option B would each ship as a v2 file at closeout.
- **Three owner cards opened (9, 10, 11)**, at the top of this document and in §17. No contract
  here changes ratified product behaviour, so the status stays **RATIFIED**. Card 11 → B *would*
  be a material change and re-open the gate. The planner starts on nothing until the three are
  answered.
- Unilateral resolutions (marked *unilateral* in §14C) are listed for ratification in
  `handoffs/reviewer/2026-09-18_inventory_mechanism_inventory_handoff.md`.

**Round 7 — 2026-09-19 — shaper folds the owner's answers to the mechanism-inventory cards.**
- Source: the inventory handoff's "Final owner answers" table (cards 9 → C, 9a, 9b, 10, 10a, 11,
  11a → A). Recorded with the owner's words in the new **§14D** (D1–D5), plus D6 (demand webhook
  is set-based and synchronous — the owner's expectation from the shaper session).
- **Material change → the gate re-opened.** Card 9 → C reverses the round-3 decision "repair mode
  deferred": self-healing repair, the repair-record table and the manual repair command are now
  must-ship (§12 item 11). Status `RATIFIED → READY_FOR_RATIFICATION` (no card is open, so the
  document does not rest in COLLABORATING). Only the owner writes RATIFIED.
- Contract text that waited on a card was rewritten to the chosen branch: §5A MC-1 (guarded
  UPDATE + inline repair + second trigger on row deletion), §6A MC-5 (no floor), §8B MC-9 (no
  stamp; 5 s time limit with a rule-10 instrument), §5B MC-14 last row. §9E MC-18 grew from 28 to
  36 cells. §12A gained the repair contract and the repair-record table; the reset gained a phase.
- Ledger: **M1's wording gained one sentence** (self-heal observable; "a correct system writes no
  repair record"). No ID added, moved or merged. §13A rows MC-1, MC-5, MC-9, MC-14, MC-20 updated.
- §14C: C10, C30, C37 resolved; C38–C40 added. §16: P33–P36 added (mine, strikeable). §17: no open
  cards.
- The published v1 Scanner handoff is untouched. Closeout still owes Scanner one additive note
  (keep Manager's demand time limit below the sender's client timeout) and the v2 file for the
  processed `reason` codes (C26).
- The inventory gate's 21 unilateral resolutions (U1–U21) are put to the owner with this
  re-ratification.

**Re-ratification — 2026-09-19 (owner, David).** Owner's words: "perfect, i approve it, and you
can commit it also." Covers round 7 in full: §14D D1–D6, the rewritten MC-1/MC-5/MC-9/MC-14/MC-18
and the §12A repair contract, M1's added sentence, P33–P36 (none struck), and U1–U21 (none
struck). Status → **RATIFIED**. Next gate: the mechanism-inventory re-check
(`prompts/reviewer/2026-09-19_inventory_mechanism_inventory_recheck.md`).

**Round 7 re-check — 2026-09-19 — mechanism-inventory gate, verdict `PASS`.** Perimeter: MC-1,
MC-5, MC-9, MC-14, MC-18, MC-20 repair, D6. Handoff:
`handoffs/reviewer/2026-09-19_inventory_mechanism_inventory_recheck_handoff.md`. Round-7 text
tightened in place and marked *(re-check, round 7)*; no round 0–6 sentence edited, and the
conflicts with round-6 text are ledgered as §14C C41–C45.
- **MC-1:** exact WHERE (no workspace or deleted predicate); write order for every path and target
  (own columns flushed before the counter statement; the soft-delete belongs to the operation;
  creation inserts with the target state); the no-race premise of the recomputation (every
  assignment writer holds the row lock); `stored_before` read fresh, never from the ORM; the
  warning carries the delta; two more instrument rows, (b) and (c), with planted defects.
- **MC-5:** `R` is protected by its row's lock, not a lock of its own; exact WHERE; memory flushed
  before the Σ; exactly one record follows from the rule.
- **MC-9:** the round-7 claim "the request stays under 8 s" was false, since the limits are per
  statement (measured). Added a request deadline checked immediately before commit (503); the
  limits are applied via `set_config(…, true)`, because a parameterized `SET LOCAL` is a syntax
  error on asyncpg (measured); one owning transaction with nothing before it; the exact exception
  class (`DBAPIError`, SQLSTATE 57014 / 55P03) → 500; the rule-10 instrument rewritten as three
  runnable rows; Scanner's 8 s re-confirmed; a second sender note (Scanner's worker drops its own
  timeouts instead of retrying them).
- **D6:** a statement plan that keeps MC-9 true (the absent-identity INSERT is omitted on a
  replay), MC-4's ordering, and MC-6's comparison base; the statement-count criterion counts every
  statement, `SELECT` included; processed grouping defined as `move_assignment` in grouped form.
- **MC-14:** the `model_fields_set` term; placement before the first write; both callers of
  `find_or_create_item` named, with refusal right for each; absence of a third category writer
  searched; lock order argued.
- **§12A:** `target_kind` mapping; one record per `(entity, field)` per operation; value-as-text
  rules; closed `trigger` set; how the tasks to lock are discovered; stamps; events; the table set
  counted by instrument (d); (e) as one helper with a planted probe; exact reset phase position.
- **MC-18:** passes unchanged (9 operations × 4 roles = 36; both new endpoints named in §12A).
- None of this changes product behaviour: the deadline is card 11a's own words ("abandons any
  demand call that runs past about 5 seconds"), and the rest is mechanism. So the gate is not
  re-opened and no card is raised.

**Scanner handoff revised before handover — 2026-09-19 (shaper, at the owner's request; no semantic change, gate not reopened).**
- The owner had not yet handed the v1 file to Scanner, so a short-lived v2 was withdrawn and its
  content folded into `docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v1_20260918.md` itself. The
  v1 file becomes immutable on handover; later changes ship as v2.
- Folded in: the closed processed `reason` codes (C26, MC-10) and article-number matching; the 5 s
  demand limit with its 503/500 answers (MC-9, D5); both MC-9 sender notes (keep the client
  timeout above Manager's; `isRetryableError` drops its own timeout, re-check X1); "no sent-at
  field", so building the payload at send time is required (D4); the U6/U7 clarifications
  (category match, `Serving Trolleys` absent in Manager, unknown fields ignored).
- Closeout therefore no longer owes the C26 v2 file or the MC-9 sender notes. §14C C26's "ships as
  a v2 handoff file at closeout" and MC-9's "for the closeout handoff" are satisfied by this
  revision.

**Round 8 — 2026-09-19 — owner requirement: Scanner deletes a board row (shaper).**
- Added while the implementation-planner was running on the round-7 ratification. New third
  Scanner webhook, recorded as **§14E** (E1–E13) with the owner's words; it reuses the ratified
  lookup (MC-3, MC-4, MC-8) and the ratified row-deletion cascade (MC-16) and adds no table.
- **Material:** a new external contract, and it reverses v1/§8.1's "no delete webhook". Status
  `RATIFIED → COLLABORATING`; cards 12 and 13 open; proposals P37–P41; M3 gained one sentence.
- Found while grounding: Manager's row is the sum across Scanner locations (round 1), so a delete
  for one location's edit can destroy another location's live demand — P41 makes that a sender rule.
- Next: owner answers 12–13 → fold → owner ratifies → mechanism-inventory re-check of §14E only →
  the orchestrator hands the planner the delta. The Scanner handoff (v1, not yet handed over) is
  revised in place after ratification.

**Round 8 fold and re-ratification — 2026-09-19 (owner, David).** Owner's words: "about the card
12: A . card 13: A . and i agree with you P37-P41 . I will not launc a mechanism inventory after
this ratification".
- E1 (card 12 → A) and E3 (card 13 → A) rewritten to the chosen branches; §14C C46; §17 closed.
- P37–P41 accepted, none struck. Status → **RATIFIED**.
- **The owner waived the mechanism-inventory re-check for §14E.** Its six questions are now
  planner obligations (§14E "Carried to the planner"), to be checked by the phase's round-0
  projection. This is a deliberate departure from the pipeline order, recorded here so no later
  gate reads the absence of an inventory handoff for §14E as an omission.
- The Scanner handoff v1 (not yet handed over) was revised in place: new §4A, §1, §3.2 rule 4,
  §6.3, §7.

**Round 9 — 2026-09-19 — owner requirement: early Scanner resolution (shaper).**
- The owner asked what happens when Scanner reports an item while the task is not `ready` (a
  forgotten step). Answer under rounds 0–8: ignored, not remembered, later stuck in `awaiting`.
  The owner chose a new terminal state that takes the units out of the counters at once and stays
  as the trace: recorded as **§14F** (F1–F11) with the owner's words.
- **Material:** it allows a transition MC-1 forbade, retires a response code in the Scanner
  contract and strikes part of P32. Status `RATIFIED → COLLABORATING`; card 14 (goal credit) open;
  proposals P42–P45; M2 gained one sentence; §14C C47–C50.
- The task is never touched by Scanner; this keeps HC-4's direction (task → assignment) and adds
  one Scanner-only exit from the active states.
- Next: card 14 → fold → owner ratifies → the orchestrator hands the planner the delta; the v1
  Scanner handoff (not yet handed over) is revised in place (§4.2, §4.3).

**Round 9 fold and re-ratification — 2026-09-19 (owner, David).** Owner's words: "about card 14 :
"A" is correct . now after that answer you can rattified the intention again, commit it again".
- F4 written to card 14 → A (credit to the current goal, never removed); §17 closed.
- P42–P45 accepted, none struck. Status → **RATIFIED**.
- Scanner handoff v1 (not yet handed over) revised in place: §1, §4.2, §4.3, §7.

**Scanner handoff — v1 restored, v2 published — 2026-09-19 (shaper, at the owner's word; no semantic change).**
- The owner had handed over the **original** v1 (`2ee6f5b`). The in-place revisions of rounds 7–9
  were therefore reverted from `STOCK_REPORT_WEBHOOKS_v1_20260918.md`, which again reads exactly as
  handed, and the full current contract ships as
  `docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v2_20260919.md` — complete on its own, with a
  "What changed since v1" table.
- Section numbers were kept, so every reference in this document to a revised "v1 handoff" section
  (§3.1.1, §3.5, §4A, §4.2, §4.3, §6.3, §6.6, §7) now reads as **v2** of that section. The
  "Scanner handoff revised before handover" entry above is superseded by this one.

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
