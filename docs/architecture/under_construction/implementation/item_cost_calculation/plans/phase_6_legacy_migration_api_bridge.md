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

- **Forward note (phase-5 re-review r2, N2):** the history query's
  `client_id DESC` tie-breaker has NO arbiter today because every
  `set_item_valuation` call stamps its own `created_at` — no fixture ties.
  THIS phase's legacy money migration bulk-creates valuation rows, plausibly
  sharing one timestamp: that is when the clause becomes load-bearing.
  Verified correction (reviewer-supplied): build two rows with an explicit
  identical `created_at` and assert the `client_id DESC` order in the history
  read. Carry it as a criterion row here.

## Round-0 projection amendments (2026-08-14, coordinator-routed — GOVERNING where they conflict with the text above)

The r0 ledger (23 rows, handoff `2026-08-14_phase6_projection_r0_handoff.md`)
is fully routed. Owner cards 1–2 were ANSWERED in-session and are folded as
**intention round 14** (R14-1…R14-4: the D1 carrier correction, the D3
post-condition restatement, P3 + the skip-deleted clause, the D15/D16/D6
evidence and router corrections) — read §10A.1–§10A.3 AS AMENDED; they
supersede this plan's older prose wherever they differ.

**Live-data census (the criterion arithmetic's pre-counts, measured):** 479
items / 61 workspaces, ALL legacy money columns at 0 non-NULL — every §10A.1
post-condition is vacuous on the live DB (D17). Therefore C1/C2/C3 run on
SEEDED DISPOSABLE databases with non-vacuity arbiters (P-J third ext: a row
proving the seeded eligible set is non-empty), and the §10 recipe is named per
criterion. D18: ZERO test dependents exist for the three keys (grep across
`app/tests/` = 0 files) — a green suite is NOT evidence; C5's mutations are
the only arbiters this surface will ever have.

**D1 (BLOCKER, folded upstream):** the bridge validator raises
`beyo_manager.errors.validation.ValidationError` — never a pydantic
`ValueError` (mangled leading token: executed table in the handoff) and never
a FastAPI-body validator (wrong envelope). C4 asserts the EXACT full message
`ITEM_MONEY_MOVED: item money fields moved to the item-valuation endpoint`
and the `{"error", "ok": false}` envelope at 422.

**D3 (BLOCKER, folded upstream):** C2 gains (i) the run-twice row — second
pass a no-op WITHOUT aborting; (ii) the collision row — item with legacy
money AND a current valuation → journaled, `valuation_client_id` NULL,
valuation untouched. C2/C3's prose clauses are TABULATED, one row per
post-condition (D23).

**D4 (BLOCKER) — C5 is the NINE-row census, not "five payloads":** the
handoff's two tables are the authority — 6 endpoints through
`domain/tasks/serializers.py::serialize_item` (list_tasks, get_task,
coordination threads, 2 upholstery reads, pending-seat-tasks) + 3 through
`domain/items/serializers.py::_serialize_item_base` (list_items, get_item,
and **customer detail's `linked_items[]`** — the never-before-named ninth).
One key-set assertion per endpoint on production serializer output;
parametrize ids name the endpoint; TWO named mutations (re-add the three keys
per serializer function), each declaring its FULL observed red set (the base
mutation should redden rows 7–9 together — design information).

**D5 (BLOCKER):** C4's create_task mutation becomes a PAIR — one per
validator definition site (tasks-file and items-file), both red sets
declared; the create_task fixture pins the no-identifier branch (no
`article_number`/`sku` → `create_item_in_session` directly) AND a second row
takes the find-or-create branch. N named mutations = N ledger rows.

**D6 (BLOCKER):** the four FastAPI router bodies (`_CreateItemBody`
`items.py:68-70`, `_UpdateItemBody` `:91-93`, `_FindOrCreateItemBody`
`:113-115`, `_TaskItemInputBody` `tasks.py:105-107`) are ADDED to Files
expected to change with the instruction: the three keys are **RETAINED**
there this release. One C4 row proves a non-NULL value SURVIVES the router
body into the command validator (the only layer that can silently drop it).

**D7/D2 (owner):** eligibility predicate verbatim per §10A.1(c); P3 rows in
C1 (refusal) and C2 (empty offender set post-condition).

**D8 (delegated):** client_ids minted Python-side (`generate_id("ival")` per
row, executemany) — Postgres cannot produce ULIDs; the eligibility predicate
stays in the SELECT. Precedent `5caae620088c:26-46`.

**D9:** C6's "fresh metadata-create" clause is REPLACED by the two shipped
harnesses: the pg_type/pg_attribute structural row (enum survives with
exactly ONE remaining column user — `item_upholstery_requirements.currency`,
2 → 1) and the FILTERED `compare_metadata` row (P-X caveat stated). The
upgrade→downgrade→upgrade round-trip stays.

**D10:** downgrade re-adds `item_currency` via
`postgresql.ENUM(..., create_type=False)` (exemplar `5caae620088c:20-22`);
`op.drop_column` does not drop the type — the criterion ASSERTS retention.
C3 names its exact revision pair and direction (BOTH downgrades: drop's
re-adds columns NULL, data migration's repopulates from the journal); end
states by STATE QUERIES (L5).

**D11:** the column mapping, written: `item_value_minor →
expected_sale_price_minor`, `item_cost_minor → purchase_cost_minor`,
`item_currency → currency`. C1's byte-equality row names all three pairs
individually (P-O).

**D12 (delegated):** migrated rows emit NO audit events — the journal is the
record; stated so the reviewer does not file the absence.

**D13:** C4's 422 rows run through the shipped TestClient harness
(`test_item_economics_router.py:41-60` precedent — FastAPI() +
include_router + dependency_overrides), named per P-R.

**D14:** the tie-breaker criterion (phase-5 N2) stays but is relabeled a
SYNTHETIC fixture (two rows, explicit identical `created_at`, assert
`client_id DESC`) — the migration writes at most one valuation per item and
cannot produce the tie.

**D16:** on the create-item schema, "key absent" and "key present null"
traverse the identical code path (`model_dump()` without `exclude_unset`
materialises every key) — collapse explicitly per P-G or name why separate.

**D19:** the archgraph note is corrected: `node:table-item` EXISTS (pending,
with the reads_from edge beside it); this phase's delta is ONE node edit
(its description's "until phase 6's migration" sentence) — recorded by the
implementer as an additive note for the coordinator's pass, never
adjudicated.

**D20 (favourable facts, cite don't re-derive):** `env.py` hides `*_journal`
tables from autogenerate BY NAME (a rename forfeits protection — one plan
line); `transaction_per_migration=True` + the 4B rollback make "P1/P2/P3
before any write" structurally true.

**D22:** in scope: `app/beyo_manager/routers/README.md` (12 mirror rows at
the four cited blocks). The frontend doc mirrors
(`frontend/docs/architecture/backend/...`) are OUT of scope → phase-9 drift
batch (recorded there).

**D23:** parametrize ids name the authority row in its CURRENT numbering
(e.g. `10A2-row3-amount-null-currency-refuses-p1`,
`10A3-create-task-present-nonnull-422`); C1's fixture audit per rule 2
(the journal+valuation row must not also satisfy the skip predicate).

**Read-first addition:** exemplar `5caae620088c` (report-first pre-flight
with dependent counts; `create_type=False` at both sites) — the closest
in-tree precedent, previously uncited.

## Review log

(append-only)
