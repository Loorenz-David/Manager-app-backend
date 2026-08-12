# Phase 6 — Legacy money migration & API bridge

```
plan: phase 6
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Move legacy item money into `item_valuations` and remove it from the item surface:
the journaled data migration with pre-flight refusals, the loud API bridge
(reject-iff-present-and-non-NULL), write-path and serializer removal, and the
column-drop migration. **NOT in this phase:** deleting the bridge validator (a
recorded follow-up for a later release — master plan §7), evaluations, or any
Application_contracts edit (routed in phase 9).

## Read first

1. `master_plan.md` §§5, 6.4 (`ITEM_MONEY_MOVED` message), 7 (sequencing note), 10
   (DB safety).
2. Intention **§10.2 (round-1 form), §10A entire** (journal scope, pre-flight
   totality, bridge predicate), §2.1 (legacy census — the migration's evidence),
   §4.7 (consequences incl. R2-1 enum-type ownership), §10.4 (frontend blast
   radius).
3. Exemplars in-tree: `migrations/versions/97b60e06d42a_*.py` (journaled data
   migration), `595e7b840926_*.py` (partial-unique idiom). Precedent for
   null-vs-omit: `update_item.py` `model_fields_set` usage.
4. Contracts: `30_migrations`, `06_commands`+local, `46_serialization`+local
   (+ core).

## Dependencies

Phase 5 APPROVED (the replacement money surface must exist before item CRUD loses
money — replacement before removal).

## Files expected to change

- `migrations/versions/<new>_migrate_item_money_to_valuations.py` (data + journal)
- `migrations/versions/<new>_drop_item_money_columns.py` (follow-up file — never a
  rewrite of an applied migration, charter rule 7)
- `app/beyo_manager/services/commands/items/requests/__init__.py` (3 schemas ×
  bridge validator; the three keys stay declared solely to drive it)
- `app/beyo_manager/services/commands/tasks/requests/__init__.py` (nested item
  schema × same validator)
- `app/beyo_manager/services/commands/items/_create_item_in_session.py`,
  `create_item.py`, `find_or_create_item.py` (incl. the `_DIRECT_FIELDS` update
  branch), `update_item.py`, `services/commands/tasks/create_task.py` (write-path
  removal per §2.1's six-site write census)
- `app/beyo_manager/models/tables/items/item.py` (drop the three columns;
  `create_type` ownership of `item_currency_enum` moves to
  `item_upholstery_requirement.py` — R2-1)
- `app/beyo_manager/domain/items/serializers.py`, `domain/tasks/serializers.py`
  (`serialize_item` — stop emitting the three fields; five embedding payloads per
  §2.1's read census)
- `routers/README.md` OpenAPI mirrors; tests

## Implementation tasks (ordered)

1. **Data migration** per §10A.1/§10A.2: journal
   `item_valuation_migration_journal(item_client_id PK, item_value_minor,
   item_cost_minor, item_currency, valuation_client_id NULL)` covering **every**
   items row with any of the three columns non-NULL **regardless of `is_deleted`**;
   current `ItemValuation` rows only for non-deleted items with ≥1 amount, copied
   verbatim; **P1/P2 pre-flight refusals run before any write**, each reporting
   offending `client_id`s (`RuntimeError`, registry §6.4); the three §10A.1
   post-conditions asserted inside `upgrade`; copy INSERT idempotent by predicate
   (excludes already-valued items); `downgrade` restores all three columns on every
   journaled row, deletes created valuations **by `valuation_client_id` only**, then
   drops the journal.
2. **API bridge** (§10A.3): one shared validator on the four request schemas —
   `ValidationError` iff a removed key is present with a non-NULL value
   (`model_fields_set` distinguishes present-null from absent); message per registry
   (`ITEM_MONEY_MOVED: …`). Present-null and absent both pass and are ignored.
3. **Write-path removal:** no command writes the three columns anywhere (six-site
   census §2.1); serializers stop emitting them (keys absent, not null) across the
   five embedding payloads.
4. **Column-drop migration** (separate file): drops the three columns for every row;
   retains PG type `item_currency_enum`; flips `create_type` so the upholstery
   column owns type creation (metadata-create on a fresh schema must still work).
5. OpenAPI mirror rows updated.

## Acceptance criteria

Migration tests on disposable DBs only (rule 7); rule-1 exemption applies to the
manual lifecycle check with the in-suite automated proxy below.

**C1 — §10A.2 totality (one fixture per row, sole-predicate; intention tests 13/20):**
- all-NULL row → skipped, not journaled;
- currency-only row → journaled, **no valuation** (and no zero-amount valuation);
- amount + NULL currency → migration REFUSES (P1) before any write, row report
  names the `client_id`;
- negative amount + currency → REFUSES (P2) before any write, row report;
- amounts ≥ 0 + currency, non-deleted item → journaled + current valuation verbatim
  (value, cost, currency byte-equal);
- amounts ≥ 0 + currency, **soft-deleted** item → journaled, no valuation (the row a
  non-deleted-only journal loses — test 20's reason).

**C2 — post-conditions & idempotency:** journal count == items with any non-NULL
column; valuation count == non-deleted items with ≥1 amount; every created valuation
current + non-deleted + NOT NULL currency; re-running the copy affects zero rows.

**C3 — downgrade exactness:** all three columns restored byte-identically on every
journaled row **including the soft-deleted one**; a valuation created manually
after upgrade (not in the journal) **survives** downgrade — proving deletion is by
`valuation_client_id`, never by predicate; journal table gone afterwards.

**C4 — §10A.3 bridge (intention test 19), enumerated per schema × case (12 rows):**
for each of {create item, patch item, find-or-create, create_task nested item} ×
{key absent → success + no valuation/money write; key present null → success + no
write; key present non-NULL → 422, message leading token `ITEM_MONEY_MOVED`}.
Plus per-key rows on the create-item schema: `item_value_minor` / `item_cost_minor`
/ `item_currency` each non-NULL → 422 (the shared validator covers all three keys).
Named mutation: deleting the validator from
`services/commands/tasks/requests/__init__.py` (definition site) must turn the
create_task present-non-NULL row red.

**C5 — serializer removal:** across the five embedding payloads (item list/detail;
task-list `primary_item`; task-detail `item`; coordination-thread item;
upholstery-order item — §2.1 read census) the three keys are **absent** (key-set
assertions on production serializer output).

**C6 — schema lifecycle proxy:** automated upgrade→downgrade→upgrade round-trip of
BOTH new migrations on a scratch schema; fresh metadata-create succeeds post-drop
(proves the `create_type` ownership flip — R2-1).

## Notes

- The bridge risk case verified by the planner 2026-08-12: the manager app sends
  `item_value_minor: null, item_cost_minor: null` on every task creation and passes
  `item_currency` through (`frontend/packages/tasks/src/actions/use-create-task.ts:84-86`);
  production flows send it null (the currency field mounts only in the dev harness).
  Present-null passing is therefore load-bearing — a "key present ⇒ reject" bridge
  breaks task creation on day one (M-11).
- History records already discard old values (`update_item.py`) — the journal is the
  ONLY recovery path for legacy amounts; treat its scope rules as immovable.
- Frontend types are typed-but-unrendered (§10.4) — breakage risk low; coordinator
  routes the frontend-schema cleanup separately.
- Archgraph: delta = evidence updates on the items branch if mapped (the `Item`
  table itself is NOT in the graph — research §7); likely zero new nodes; state it.
- **Forward hazard from the phase-1 projection (D9, 2026-08-12) — resolve at this
  phase's projection before the implementer prompt:** this plan says "five embedding
  payloads"; the projection counted **six `serialize_item` call expressions in five
  files** (`services/queries/tasks/tasks.py:387` `list_tasks` and `:696` `get_task`;
  `list_task_coordination_threads.py:224`; `upholstery/upholstery_order_needs.py:595`;
  `items/seat_tasks_pending_upholstery.py:335`;
  `upholstery/upholstery_orders_query.py:496`). Same call-expressions-vs-surfaces
  error class as the phase-1 D1 census finding — this phase's projection re-derives
  the full caller/endpoint graph of `serialize_item` before criteria C5 is trusted.
- **Owner decision (projection card 1 → R5-2, 2026-08-12):** the worker-reachable
  item-money exposure deliberately survives phases 1–5 and ends here, by column
  removal. This phase's projection verifies no interim redaction was assumed anywhere.

## Review log

(append-only)
