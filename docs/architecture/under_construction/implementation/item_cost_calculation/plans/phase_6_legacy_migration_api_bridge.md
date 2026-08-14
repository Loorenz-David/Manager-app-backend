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

## Fix r1 amendments (2026-08-14, coordinator-routed from review r1 — GOVERNING)

Review r1: 2 blocking, 4 should-fix, 11 notes; owner card 1 ANSWERED (leave
deleted prices deleted — **R15-1**, the corrected eligibility predicate in
§10A.1(c) as amended). The reviewer executed the corrections; resolve, don't
relitigate.

**B1 — the pc2 guard becomes real (P-J fourth ext):** `_assert_postconditions`
compares independently-constructed sides per R14(a): created-valuation count ==
count of ELIGIBLE items measured at entry (not a count derived from the same
rows the copy produced). The reviewer's verified correction is executed and
hash-recorded in the Review log (R9: shipped tests stay green; R10: the
skip-one mutant aborts with `left 1 eligible item(s) unmigrated` and rolls
back to `5caae620088c`). Named mutation: the `rows[1:]` skip must ABORT the
upgrade (it exited 0 in r1).

**B2 — the eligibility predicate per R15-1:** `NOT EXISTS (any
item_valuations row for the item)` — never-valued items only. C1 gains one
sole-predicate row PER VALUATION STATE: never-valued (migrated),
current-valued (collision row — journaled only, exists), soft-deleted-only
(SKIPPED — was re-valued in r1), superseded-only (SKIPPED — state the
judgment that this state is command-unreachable but the predicate covers it).

**S1 — the census rows become real (P-V third ext):** each of the nine rows
consumes its `endpoint_id` and asserts through a distinct expression (the
reviewer's R3 probe — inline re-exposure at `upholstery_orders_query.py:496`
— must redden its row; it left all 27 green). Fixtures are ORM `Item`
instances, never `SimpleNamespace` (charter rule 3 / phase-3 N16).

**S2 — row-report content (L4):** each refusal test asserts the offending
`client_id`s appear in the report AND asserts its OWN class's identity in a
message that carries only that class (or asserts the class-specific line).
The reviewer's R2 probe (strip the ids) must redden.

**S3 — three more harness rows:** `PUT /items`, `PATCH /items/{id}`,
`POST /items/find-or-create` each get the end-to-end 422 row through the
TestClient harness (the reviewer already proved the behavior correct — ship
the evidence).

**S4 — parametrize the case tables:** the migration test file's for-loops
become parametrized rows with D23 authority-naming ids; first-failure masking
ends.

**Notes taken this cycle:** N2 the plan/D9 text corrects to "enum users at
head = 2 (incl. the journal's snapshot column); 1 only after the squash" —
the structural row asserts 2 at head; N4 the idempotency row loses its second
sufficient cause and re-runs the post-conditions on the second pass; N5 the
manual-valuation survival row asserts IDENTITY (client_id), not count; N6 an
intermediate state assertion lands between the two downgrades; N7 the tie row
gets its own labeled test (synthetic, per D14); N8 the drop migration's
docstring names its real parent and `print()` becomes a logger call.
**Not this cycle:** N3 (metadata.create_all broken repo-wide) → only-if-cheap
ledger at approval; N9 (deploy ordering) → phase 9; the `node:table-item`
description+summary edits → coordinator's post-approval pass.

**Ledger rule:** probes 1–2 of the r1 ledger were declared against
PRE-checkpoint baselines and probe 1's red set was incomplete — this cycle
re-declares every row against the FINAL committed hashes with full observed
red sets (P-I fifth/sixth/seventh ext).

## Review log

(append-only)
### 2026-08-14 — implementer r1 (Codex) — IMPLEMENTED

Implementation completed under the phase-6 prompt. The write perimeter is the
three-column removal from `items`, the `item_currency_enum` ownership correction
at upholstery requirements, the five command write paths, four retained router
request bodies, four request-schema validators, two serializers, the router
README mirror rows, two migrations, the phase-6 API/serializer/migration tests,
the phase-5 synthetic history tie fixture, and the required tracker/review/
handoff artifacts. No frontend files were changed.

Judgments recorded: the shared request helper raises
`beyo_manager.errors.validation.ValidationError` with the exact
`ITEM_MONEY_MOVED: item money fields moved to the item-valuation endpoint`
message only when a retained field is present and non-null; absent and explicit
null use the same accepted path. Router bodies remain unchanged intentionally
so legacy payloads cannot be silently dropped. The migration follows the
verbatim D7 no-current-valuation predicate, runs all P1/P2/P3 refusals before
any write, uses Python-side `generate_id("ival")`, emits no audit events, and
keeps the rollback journal through the column-drop revision. D14's equal-
`created_at` ordering is a synthetic fixture because the migration creates at
most one valuation per item.

Evidence: phase-specific API and serializer tests plus the disposable-database
migration lifecycle are **29 passed**; the phase-5 history test is **1 passed**
against the configured development profile. The full non-e2e suite is
**1997 passed / 23 established failures / 1 deselected**, with the established
failure set unchanged; ruff and `git diff --check` pass. The configured database
is at `be9dfe42a035` head: `items=480`, migration journal `=0`, legacy `items`
columns `=0`, and the only remaining non-journal `item_currency_enum` user is
`item_upholstery_requirements.currency` (the journal's snapshot column is also
present by design at head). Four generated databases with the
`beyo_manager_phase6_*` prefix were dropped by the migration tests; a final
catalog query found **0** remaining.

Mutation ledger (each named probe was applied, observed, and reverted):

1. Delete the task request validator: baseline
   `9dccde991cde595c8be2fbbfdb8579e43f933f5d73d93b698cd27eea71ffbfac`, mutant
   `945586f71f73e537531f9524569fe80e3e14275a47f4791f946ad521d5706f43`;
   `test_bridge_is_reject_iff_present_and_nonnull[create-task-nested-item-present-nonnull]`
   failed.
2. Delete all three item request validators: baseline
   `0f3b5a79882eaae919996b1aa5e8136e7c2f4c3772154413743a77ca8b98aff8`, mutant
   `c78f68dc15e52f20839b46c31c23f47d73a52b0a4ae96616e6fb486b515b5d0e`;
   exactly six API bridge nodes failed (three non-null schema rows and the
   three per-key rows).
3. Re-add the three item serializer keys: baseline
   `b7fa431a17cd6d69906873771a4c64748b3ff298dffaced962713996d4142104`, mutant
   `808aef9533a525f4642665423fe50ba42baa6ca706c321ddac388ebf9f4abfad`;
   exactly three item serializer nodes failed.
4. Re-add the three task serializer keys: baseline
   `b2ab4e8b5388f21e2b3a69d2da5d3c83c2a423d494387a0131284876c1f77fa4`, mutant
   `2617b8775f0044b4201f8a7322f73674f1a9fc65e68167015f7b9641a0aa68c9`;
   exactly six task/upholstery serializer nodes failed.
5. Remove `item_cost_minor` from the task router body: baseline
   `aafc1f53946b8076fd9a00297343a2c09aa16aa6660021b2da696410313fbd1a`, mutant
   `2d541c16b09a77d9360e221be52df41e52ae2ffc60b547f0df3cf125b7297bef`;
   the router-retention test failed with the expected missing-field assertion.

Architecture Graph closeout: one additive node was recorded,
`table-item-valuation-migration-journal`, with migration evidence; no pending
review item was promoted, edited, rejected, or otherwise adjudicated. The
existing `node:table-item` wording remains pending for the coordinator's
authorized maintenance pass, as required by D19.

Checkpoint and handoff follow the implementation commit. No owner decisions
are required from this implementer session.

### 2026-08-14 — reviewer r1 (Claude Opus 5) — CHANGES_REQUESTED

**2 blocking, 4 should-fix, 11 notes, 1 owner card.** Perimeter verified against
`b940309` (21 files; tree clean before and after every probe). Suite re-run
foreground **1997 passed / 23 failed / 1 deselected** — the 23 are the phase-1
baseline set, byte-identical, one-for-one. Ruff clean on the phase-6 perimeter
(the 131 repo-wide errors live outside it and predate this phase). Configured DB
at `be9dfe42a035 (head)`, journal 0 rows, legacy columns 0, zero
`beyo_manager_phase6_*` databases. Graph read-only: 7 pending (1 new + 6 prior),
zero adjudications.

**B1 (blocking) — §10A.1 post-condition 2 is a tautology; a partial copy passes
and the drop then destroys the money.** `_assert_postconditions`
(`5420acc6a7b3:161-182`) compares `count(journal WHERE valuation_client_id IS NOT
NULL)` against `count(items JOIN journal WHERE <eligibility> AND
j.valuation_client_id IS NOT NULL)`. Both sides range over the same rows by
construction, so the check cannot fail. R14(a)/D3 restated pc2 precisely as
"count of ELIGIBLE non-deleted items with ≥ 1 amount that had no current
valuation at entry" — the shipped form drops the eligible-item side entirely.
EXECUTED on disposable `beyo_manager_rev_p6_pc2`: one eligible seeded item
(5000/2500/euro, non-deleted, attributed), `_copy_eligible_valuations` mutated to
`for row in rows[1:]` (baseline `bdf89d8e…`, mutant `e6ff898b…`) →
**`alembic upgrade 5420acc6a7b3` exits 0**, journal 1 row, `item_valuations`
**0 rows**, version advanced. `be9dfe42a035` then drops the columns and the
amounts exist nowhere but the journal. Authority: intention §10A.1 as amended
R14(a); plan C2; charter rule 6. **Verified correction** (executed): add an
eligible-but-unmigrated counter to `_assert_postconditions` —
`count(items i LEFT JOIN journal j … WHERE i.is_deleted = false AND
{_LEGACY_AMOUNT} AND i.item_currency IS NOT NULL AND {_NON_NEGATIVE_AMOUNTS} AND
i.created_by_id IS NOT NULL AND j.valuation_client_id IS NULL AND NOT EXISTS
(SELECT 1 FROM item_valuations v WHERE v.item_id = i.client_id AND
v.is_deleted = false AND v.client_id IS DISTINCT FROM j.valuation_client_id))`
must be 0. Corrected file `8f5bf7ce…` → shipped migration tests **2 passed**
(collision, soft-deleted and currency-only rows all still pass); corrected +
skip mutation `6086956b…` → **exit 1**, `item money migration left 1 eligible
item(s) unmigrated`, version rolled back to `5caae620088c`, 0 valuations. C2
gains the row that names this mutation.

**B2 (blocking) — the eligibility predicate is neither "no current valuation" nor
"no valuation", and §10A.1(c)'s two untested rows both come out wrong.**
`_NO_CURRENT_VALUATION` (`5420acc6a7b3:27-34`) filters on `is_deleted = false`
only. EXECUTED on disposable `beyo_manager_rev_p6_elig` (unmutated shipped
migration, exit 0):
(a) an item with legacy money whose ONLY valuation is **soft-deleted** →
journaled AND a **new current valuation created** (`ival_01M0030HRDXR8F…`). That
is the exact outcome §10A.1(c) forbids in its own heading — "Deliberately deleted
prices stay deleted … is **not** re-valued (the deletion is a decision somebody
made)" — while matching the verbatim predicate printed two lines below it. The
clause contradicts itself; see owner card 1.
(b) an item with legacy money whose ONLY valuation is **superseded and live** →
journaled, `valuation_client_id` NULL, **no valuation created**. The item has no
*current* valuation (INV-V1: `superseded_at IS NULL AND is_deleted = false`), so
§10A.1(a)'s "no current valuation at entry" makes it eligible; the shipped
predicate treats a superseded row as blocking. Its legacy money never reaches the
valuation surface and `be9dfe42a035` then removes it from `items`.
Neither row exists in C1's fixture set — the shipped seed is {all-null,
currency-only, valid, soft-deleted-item, collision}, and the prompt's own C1 list
named "a soft-deleted-valuation item per (c)". Authority: intention §10A.1(a)/(c);
plan C1; charter rule 2. Correction: owner card 1 settles which reading governs,
then C1 gains one sole-predicate row per valuation state (none / current /
superseded-only / soft-deleted-only) and the predicate is written to match.

**S1 (should-fix) — C5's nine-row census is one assertion wearing nine labels.**
`test_phase6_serializers.py:68` takes `endpoint_id` and never uses it: six rows
call `serialize_item(_item())` with identical input. The items file's
`customer-detail-linked-items` row calls the same `serialize_item_list` as
`items-list`. Nothing ties a row to its endpoint. EXECUTED: re-exposing all three
keys inline at `upholstery_orders_query.py:496` (baseline `b34e8e0e…`, mutant
`99a34732…`) leaves **all 9 serializer rows and all 27 phase-6 unit nodes green**.
D18 records that zero other tests depend on these keys, so these rows are the only
arbiters this read surface will ever have. Authority: plan D4; charter rules 2, 3.
Secondary: the fixture is a `SimpleNamespace`, not an `Item` ORM instance
(rule 3). Correction: each row exercises its endpoint's own serialization
expression (or asserts structurally that the module delegates to the serializer),
and the fixture holds an ORM `Item`.
*(Verified separately: the census itself is factually right — six `serialize_item`
call sites plus `serialize_item_list` at `items.py:88` and
`customers/serializers.py:35` plus `serialize_item_detail` at `items.py:144` = 9,
and no production module references the three keys any more.)*

**S2 (should-fix) — the three refusal rows never assert the row report, and the
shared message makes the token assertion non-discriminating.** The `RuntimeError`
(`5420acc6a7b3:206-212`) always contains all three of `P1`, `P2`, `P3`, so
`assert "P2" in result.stderr` is satisfied by a P1-only refusal. EXECUTED:
stripping every offending `client_id` from the message (baseline `bdf89d8e…`,
mutant `0911d0d8…`) leaves both migration tests **green** — §10A.2's "each
reporting its offending `client_id`s" and C1's "row report names the `client_id`"
have no arbiter. Correction: each refusal row asserts its own seeded `client_id`
appears in the report and that the other two predicates report empty.

**S3 (should-fix) — C4's 12 rows are schema-level; 1 of 4 surfaces is proven
end-to-end.** D13 and the review prompt put C4's rows through the TestClient
harness with the `{"error", "ok": false}` envelope at 422; only
`test_create_task_router_preserves_nonnull_money_into_domain_validator` does. The
other 11 rows call `schema.model_validate` directly. Independently verified by
reviewer probe (read-only, `scratchpad/probe_items_routes.py`): `PUT /items`,
`PATCH /items/{id}` and `POST /items/find-or-create` all return **422** with
exactly `{"error": "ITEM_MONEY_MOVED: item money fields moved to the
item-valuation endpoint", "ok": false}`, and absent / present-null both pass the
validator into the command — **no defect, missing evidence**. Correction: three
more harness rows.

**S4 (should-fix) — the enumerated case tables are for-loops inside two
monolithic tests (D23).** `test_phase6_legacy_migration.py` has no `parametrize`
at all: the three refusals are a `for` loop in one function and C1/C2/C3 share one
303-line function. No id names an authority row (D23 asked for
`10A2-row3-amount-null-currency-refuses-p1` and the like), and the first failing
assertion masks every later row. Authority: D23; plan C1 "one fixture per row";
charter rule 2; phase-5 P-V ext ("a monolithic test cannot discharge an
enumerated criterion").

**Notes.** N1 (P6-B) — 2 of 5 ledger baseline hashes do not match the checkpointed
files: tasks-requests declared `9dccde99…` / actual `20cc5054…`, items-requests
declared `0f3b5a79…` / actual `bf132dd0…`; those two records are unverifiable
against the shipped code. Re-run here: probe 1 (delete task validator,
`20cc5054…` → `f09c3682…`) reddens **two** nodes, not one — the declared
`[create-task-nested-item-present-nonnull]` **plus**
`test_create_task_router_preserves_nonnull_money_into_domain_validator`, so its
red set is incomplete. Probe 2 (`bf132dd0…` → `c8515e21…`) reproduces its declared
six-node red set exactly. Probes 3 (`b7fa431a…` → `808aef95…`, 3 nodes) and 5
(`aafc1f53…` → `2d541c16…`, 1 node) reproduce **byte-identically**, hashes and red
sets both. Added by the reviewer: neutering the shared helper
(`bf132dd0…` → `1d9eec24…`) reddens all 8 bridge-behaviour nodes — D5's items-file
definition-site half.
N2 — D9's "exactly ONE remaining column user (2 → 1)" is arithmetically wrong at
head: cold build empty → head on `beyo_manager_rev_p6_cold` (exit 0, version
`be9dfe42a035`, 0 legacy columns) shows **two** users of `item_currency_enum`,
`item_upholstery_requirements.currency` and the journal's `item_currency`
snapshot. The shipped test asserts only that the upholstery user exists; it never
enumerates the set. Plan lesson: the criterion should read "exactly one
non-journal user".
N3 — `Base.metadata.create_all` cannot complete on a fresh database repo-wide
(`DuplicateTableError: relation "ix_shopify_integration_events_severity" already
exists`) — pre-existing and unrelated to phase 6, and it vindicates D9's
replacement of C6's "fresh metadata-create" clause. Route to the only-if-cheap
ledger.
N4 — the idempotency row satisfies two independent sufficient causes
(`j.valuation_client_id IS NULL` and `_NO_CURRENT_VALUATION`), so it cannot fail
when one breaks (charter rule 2 companion); and the second pass re-runs only
`_copy_eligible_valuations`, never `_assert_postconditions`, so the restated pc2's
survival across a re-run — D3's whole reason for restating it — is unexercised.
N5 — C3's "a manually created valuation SURVIVES" is asserted as
`count(*) == 2`, not by identity; assert `ival_manual` is present.
N6 — C3 never asserts the intermediate state after downgrading only the drop
migration (three columns present and NULL on every row).
N7 — the D14 tie fixture genuinely ties (two rows, one explicit `created_at`,
`ival_tie_z` before `ival_tie_a`) and the query orders
`created_at DESC, client_id DESC`; but it is appended to
`test_valuation_chain_preview_delete_and_history` rather than being its own row,
and carries no "synthetic" label — the prompt asked for both.
N8 — `be9dfe42a035`'s docstring says `Revises: 5caae620088c` while
`down_revision = "5420acc6a7b3"`; and its journal count goes to `print()` rather
than a logger. Cosmetic, but misleading inside a destructive migration.
N9 — deploy ordering is unstated anywhere: `be9dfe42a035` drops columns the
previous release's ORM still selects, so an old process surviving the migration
500s on every item read. One operations line, phase 9.
N10 — the journal node carries no edges (no `writes_to item_valuations`, no
`reads_from items`); additive-minimal is defensible, but the read/write boundary
that phase-5 review r1 N6 filed for `set_item_valuation` is absent here too.
N11 (P6-C, reconciled) — 29 new collected nodes = 18 bridge + 9 serializer + 2
migration; the phase-5 tie row is an assertion inside an existing test and adds 0
to collection, which reconciles "29 focused + 1 tie-breaker" with "+29 collected";
1991 + 29 = 2020 selected ✓. `items` 479 → 480 → **481** after the reviewer's own
full-suite run — the known suite-wide residue class (master plan §10), not
phase-6 tests.

**Verified correct (specifically).** P6-A: the `item_upholstery_requirement.py`
change is exactly the R2-1 `create_type` flip (one line, `False` → `True`) and it
is now the only model declaring the type; the drop migration's downgrade re-adds
`item_currency` with `create_type=False`; cold build empty → head exits 0 with the
enum intact and the journal present at 0 rows. The five write-path files beyond
the prompt fence remove only the three-key writes (verified line by line) and
`Item.__table__` no longer carries the columns. The bridge raises
`beyo_manager.errors.validation.ValidationError`, a `DomainError(Exception)` and
not a `ValueError`, so pydantic cannot wrap it — D1 is met by construction, and
all four surfaces produce the exact message and envelope end-to-end. All four
router bodies retain the three keys (D6). Pre-flight P1/P2/P3 all abort before any
write and persist nothing (journal absent, 0 valuations) — structurally, the
refusals precede `_create_journal`. Downgrade restores all three columns
byte-identically on all four journaled rows including the soft-deleted and
collision ones; the journal is dropped afterwards. The collision row is journaled
with `valuation_client_id` NULL and its existing valuation untouched. The mapping
is byte-equal on all three pairs. `routers/README.md` has zero residual mentions.
Graph: the journal node's two evidence spans (45-75, 200-243) are exact and every
claim holds in both directions; all five prior edge spans still land exactly
(39-44 / 47-52 / 55-60 / 72-78 / 106-110 — `set_item_valuation.py` untouched this
phase, last modified at `8b4ac06`); the `node:table-item` description edit is
correctly LEFT to the coordinator per D19.

**Anchor-spans service (7 pending items, for the coordinator's post-approval
pass).** All exact and unchanged except one summary drift:
`node:table-item-valuation-migration-journal` — 45-75 and 200-243, both exact.
`node:table-item` — span `item.py:1-60` still valid, but the summary's "category
snapshot at :51" drifted to **:46** (the five removed lines) and the phrase
"legacy money columns" is now false; both belong to the same §8 maintenance edit
as the "until phase 6's migration" sentence.
The five `set_item_valuation` edges — `table-production-cost-group` 39-44,
`table-production-cost-basis-version` 47-52, `table-cost-model-version` 55-60,
`table-cost-model-term` 72-78, `table-item` 106-110: all re-verified exact.

**Lessons for the plans.** (i) A post-condition whose two sides are built from the
same construction is a tautology — a criterion mandating an in-migration
post-condition owes a row naming the mutation that must abort it (extends P-J's
non-vacuity rule from tests to production guards). (ii) A parametrize id is a
label, not a probe: when the parameter is not consumed by the test body, N rows
are one row (P-V ext) — an enumerated census criterion should require that each
row's expression differ. (iii) An intention clause whose prose and its own
"verbatim" predicate disagree cannot be discharged by "follow it verbatim"; the
projection's decidability pass should reject a clause where the stated intent and
the given predicate produce different rows. (iv) A refusal criterion naming a row
report owes an assertion on the report's contents, not on its identity token —
especially when one message carries every identity.
