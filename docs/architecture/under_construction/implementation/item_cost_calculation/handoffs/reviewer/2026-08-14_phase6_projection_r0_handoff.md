---
plan: phase 6 (legacy migration & API bridge)
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-14
actor: reviewer/projectionist (Claude Opus 5)
---

# Phase 6 projection — round 0 handoff

## Opening (owner-readable)

I did the implementer's first hour of phase 6 on paper, against the code and the
database as they are today rather than as they were when the plan was written three
days ago. The good news first: **there is no legacy money anywhere.** All 479 items
in this workspace's database have every one of the three old price fields empty, so
the "move the old prices into the new price table" step has literally nothing to
move, and nothing can be lost. The bad news is that the plan's safety net — the
loud refusal that is supposed to tell an app "you can't send prices here any more"
— does not work as written: the error message would come back mangled, so the
refusal would be silent in exactly the way this phase exists to prevent. Twenty-three
items need fixing before an implementer starts, five of them blocking. **Nothing
needs the owner** — the two questions this projection raised were answered the same
day (below), and both collapse into ordinary implementation rules, because there are
no prices anywhere to move. Once the coordinator routes the ledger, the implementer
prompt can be compiled.

## ⚠ OWNER DECISIONS REQUIRED (0 open — 2 raised, both ANSWERED 2026-08-14)

**Owner's answer (2026-08-14), in substance:** *this is a new implementation where no
price has ever been written — the whole functionality is not shipped yet — so there is
no worry about the author of the price during migration, because there are no prices
set. And after this implementation ships I will squash the migrations to start fresh,
so the server starts from migration 1.*

Both cards retire to **delegations with named resolutions** (ledger rows D2 and D7).

**Scope check performed before accepting the answer.** The answer is exactly right
about the *new* table: `item_valuations` cannot hold a row on any database, because
the endpoint that writes it has not shipped. The migration's **source**, though, is
the legacy `items` columns, which have been live in item and task CRUD for a long
time — those are what a production database could carry, and they are not covered by
"the functionality is not shipped yet". Measured here: 0 of 479 items, across all 61
workspaces (census above). Corroborating the generalisation to any database:
**no frontend form has ever written the two amounts** (`buildItemFields`,
`normalize-task-form-payload.ts:88-101`, omits them entirely; the items app's
`CreateItemInputSchema` permits them but nothing populates it) and **no currency input
is rendered anywhere** (D15). The population is therefore believed empty everywhere on
write-path evidence, not only on this database's counts — but the migration code must
still be total, which is what the two rules below buy.

**D2 (attribution) → a third pre-flight refusal, P3.** The migration does not need to
name anybody, but it may not crash on an unexpected row either. Symmetric with P1/P2:
attribute a created valuation to the **item's own `created_by_id`**; where an item
carries an amount with a NULL `created_by_id` (legal — `item.py:55`), **refuse before
any write with a row report naming the offending `client_id`s**. This applies §10.2's
own doctrine — currency is never guessed — to attribution; it invents no system user
(the repo has no such convention: no `SYSTEM_USER`, no reserved account, all 6 152
users are real people); and on every known database it is unreachable. Needs one C1
row and one C2 post-condition row, both asserting an empty offender set.

**D7 (deliberately deleted prices) → skip them.** One clause in the eligibility
predicate: an item whose only valuation is soft-deleted is **not** re-valued. Matches
§11A.5(d)/R13-2's intent (deletion is the escape hatch for a mistaken entry) and, like
P3, cannot fire on any database that exists today.

**Consequence of the squash, recorded for the squash project (seed `943065c`).** The
journal exists solely to make the data migration reversible. Once migrations are
squashed to a fresh baseline the data migration file is gone and the journal has no
reader, so the squashed baseline must **drop or exclude
`item_valuation_migration_journal`** — otherwise the fresh schema carries a vestigial
bookkeeping table forever, and nothing will flag it: `env.py`'s
`_MIGRATION_BOOKKEEPING_SUFFIX` filter (`:30`, `:33-48`) deliberately hides `*_journal`
tables from autogenerate. Until the squash lands the journal remains the only recovery
path for legacy amounts (history records already discard old values, §2.1), so it is
built in full this phase.

---

*The two cards as originally raised, retained for the record.*

### Card 1 (ANSWERED — no attribution needed; P3 rule above) — Whose name goes on a price the system moves by itself?

**Question.** When the system moves an old price onto the new price record, which
person should it record as the one who set it?

**Story.** Anna opens a chair from last spring and taps the price history. Every
price row shows who set it and when — that is how she settles "who put 12 000 kr on
this". The very first row was not typed by anyone: the system moved it over from the
old fields during the upgrade. The record refuses to be saved without a person's
name attached, so someone's name will be there. If it says Anna, she will believe
she typed it. If it says the workshop's first admin, that person carries prices they
never saw. Some old items do not even record who created them, so "whoever created
the item" runs out on part of the list.

**Branches.**
- *An admin of the workspace* — one real person becomes the author of every moved
  price; history reads plausibly but wrongly.
- *Whoever created the item, falling back to an admin* — mostly right, still wrong
  on the fallback rows, and two rules to explain forever.
- *A dedicated "system" user record* — history says "moved during upgrade", nobody
  is blamed; costs one extra decision about creating that user.

**Recommendation.** The dedicated system user — it is the only branch where the
history line is true, and price history is the thing this domain exists to make
trustworthy.

**On silence.** The gate holds; no implementer prompt is compiled. Nothing is
guessed.

**Trace.** intention §10.2 step 1, §10A.1; `item_valuations.created_by_id`; ledger D2.

### Card 2 (ANSWERED — skip deleted; rule above) — Should a deliberately deleted price come back?

**Question.** If a manager has already deleted an item's price, should the upgrade
put the old price back on it?

**Story.** In September a manager typed 40 000 kr on a cabinet by mistake, noticed,
and deleted it — deleting is the intended escape hatch for a wrong entry, and the
item went back to "no price". That same cabinet still carries a stale 12 000 kr in
the old fields nobody has looked at for a year. When the upgrade runs, it walks
every item that has anything in the old fields. Unless told otherwise, it will see
"this item has no current price" and helpfully install the stale 12 000 kr — quietly
undoing the manager's correction, on exactly the items where someone already looked
and decided.

**Branches.**
- *Skip items whose price was deleted* — the manager's decision stands; the old
  number stays only in the recovery journal.
- *Install the old price anyway* — no item is left unpriced, but deliberate
  deletions are silently reversed.

**Recommendation.** Skip them. A deletion is a decision somebody made about that
item; the upgrade knows less than they did.

**On silence.** The gate holds; no implementer prompt is compiled.

**Trace.** intention §11A.5(d)/R13-2, §10A.1 idempotency clause, INV-V1; ledger D7.

## Live-data measurements (dev database `beyo_manager`, head `5caae620088c`)

Measured, not assumed — the pre-count the migration criterion's arithmetic must use.

| Population | Count |
|---|---|
| `items` total | **479** |
| `item_value_minor IS NOT NULL` | **0** |
| `item_cost_minor IS NOT NULL` | **0** |
| `item_currency IS NOT NULL` | **0** |
| any of the three non-NULL (⇒ expected journal rows) | **0** |
| §10A.2 P1 refusal class (amount present, currency NULL) | **0** |
| §10A.2 P2 refusal class (amount < 0 with currency) | **0** |
| non-deleted with ≥1 amount (⇒ expected created valuations) | **0** |
| soft-deleted with ≥1 amount (the journal-only row) | **0** |
| currency-only rows (currency set, both amounts NULL) | **0** |
| all-three-NULL rows | **479** |
| `item_valuations` rows | **0** |

Per workspace: 61 workspaces hold items (418 in `ws_01KVX0G0T7Z6NE69YVRVMFAB98`, 1
each in the remaining 60); **`any_money = 0` in every one**. Supporting: PG type
`item_currency_enum` has exactly two column users (`items.item_currency`,
`item_upholstery_requirements.currency`); `item_upholstery_requirements` holds 204
rows with **0** non-NULL `currency` — the R2-1 dormancy claim re-verified today.

**Consequence (D17).** Every §10A.1 post-condition and every C2 arithmetic assertion
is satisfied *vacuously* (`0 == 0`) on the only reachable database. The migration's
behaviour is unobservable here; all of C1/C2/C3 must run against seeded disposable
databases and each needs a non-vacuity arbiter (P-J third extension).

## Decision ledger (23 rows)

| # | Decision point the artifacts do not determine | Class | Sev | Proposed routing |
|---|---|---|---|---|
| D1 | Which exception the bridge validator raises, and what the asserted message is | intention gap + plan gap | **BLOCKER** | amend §6.4 + §10A.3; pin the verified form in C4 |
| D2 | `created_by_id` for migrated valuations (column is NOT NULL) | ~~intention gap~~ → delegation | ~~BLOCKER~~ should-fix | **ANSWERED** — P3 pre-flight refusal; §10A.1 records it |
| D3 | §10A.1 post-condition 2 contradicts the idempotency clause | intention gap | **BLOCKER** | restate pc2 over the journal; amend C2 |
| D4 | C5's "five embedding payloads" — the real surface is 9 endpoints across 2 functions | plan gap | **BLOCKER** | replace C5's list with the enumerated table below |
| D5 | C4's named mutation is inert under the natural create_task fixture | plan gap | **BLOCKER** | re-site the mutation; pin the fixture branch |
| D6 | The four router body models are absent from "Files expected to change" | plan gap | **BLOCKER** | add them; pin "keys RETAINED at the router" |
| D7 | Idempotency predicate wording; soft-deleted-valuation items | plan gap → delegation | should-fix | **ANSWERED** — skip deleted; predicate stated verbatim |
| D8 | How `client_id` is generated inside a set-based INSERT | free choice | should-fix | delegate explicitly (Python-side generation) |
| D9 | C6's "fresh metadata-create" has no harness in this repo | plan gap | should-fix | replace with the shipped structural harness |
| D10 | Downgrade's re-add of `item_currency`; which downgrades C3 runs | plan gap | should-fix | pin `create_type=False`; name the ladder |
| D11 | Which legacy column maps to which valuation column | plan gap | should-fix | write the mapping + byte-equality criterion |
| D12 | Whether migrated rows emit audit events | free choice | should-fix | delegate explicitly (recommend: none) |
| D13 | C4's harness (only the router can produce a 422) | plan gap | should-fix | name the TestClient precedent (P-R) |
| D14 | Phase-5 N2 forward note's premise is false | drift | note | keep the criterion, relabel it synthetic |
| D15 | The M-11 frontend evidence is a misread of the wrong code block | drift | note | correct the plan Note + §10A.3 rationale |
| D16 | `model_fields_set` is inert; create-item route materialises defaults | drift | note | simplify the predicate; P-G on C4's rows |
| D17 | Every migration criterion is vacuous on the live database | reality | note | seeded disposables + non-vacuity arbiters |
| D18 | Zero test dependents exist for the three keys | reality | note | record; C5 has no pre-existing arbiter |
| D19 | The plan's archgraph note is stale — `table-item` exists and is pending | drift | note | phase 6 delta is one node edit, not zero |
| D20 | `env.py` already protects `_journal` tables; per-migration commits | reality (positive) | note | record; no plan change |
| D21 | R5-2 discharged — no interim redaction was assumed anywhere | reality (positive) | note | record; no plan change |
| D22 | OpenAPI mirror scope: backend README vs the frontend doc mirrors | plan gap | should-fix | name in-scope files; route the rest to phase 9 |
| D23 | P-V: C1/C4/C5 counts and parametrize-id naming | plan gap | note | ids name the authority row they discharge |

---

## A. The API bridge

### D1 — BLOCKER — the error identity cannot survive the repo's parse helpers

§6.4 fixes the identity as **the leading token of `message`** and C4 asserts "message
leading token `ITEM_MONEY_MOVED`". §6.4 also says the bridge raises "pydantic
`ValidationError`". Those two cannot both hold. Every command request in the phase's
perimeter is parsed through a helper that catches pydantic's error and re-raises the
repo's `ValidationError` **prefixed with the field locator**:

- `services/commands/items/requests/__init__.py:395-403` (`parse_create_item_request`;
  the same body at `:417-425` update, `:437-…` find-or-create)
- `services/commands/tasks/requests/__init__.py:320-323` (`_raise_validation_error`)

Executed, not reasoned (probe P1 below):

| Validator form | Message that reaches the client |
|---|---|
| `field_validator` raising `ValueError(MSG)` | `item_value_minor: Value error, ITEM_MONEY_MOVED: …` |
| `model_validator` raising `ValueError(MSG)` | `: Value error, ITEM_MONEY_MOVED: …` (leading token **empty**) |
| validator raising `errors.validation.ValidationError(MSG)` | `ITEM_MONEY_MOVED: …`, `http_status` 422 ✅ |

**Verified correction.** The validator raises the repo's
`beyo_manager.errors.validation.ValidationError` (a `DomainError`, not a `ValueError`).
Pydantic v2 propagates non-`ValueError`/`AssertionError` exceptions unwrapped, so it
bypasses the `except PydanticValidationError` block, reaches `run_service`
(`services/run_service.py:41-42`) as a `DomainError`, and `build_err`
(`routers/http/response.py:20-23`) emits `{"error": "ITEM_MONEY_MOVED: …", "ok": false}`
with status 422. Route: amend §6.4's "pydantic `ValidationError`" wording and §10A.3's
"raises `ValidationError`" to name the class by import path; C4 asserts the exact
full message, not a prefix match.

Why this is a blocker rather than a detail: a `ValueError` here does not merely produce
an ugly message — the field-locator prefix means an identity assertion written as
"leading token" fails, and an implementer who "fixes" the test by loosening it to a
substring match ships a bridge whose identity is unregistered. If instead the
validator is placed on the FastAPI body model, FastAPI's own 422 envelope
(`{"detail": [...]}`) replaces the repo's `{"error", "ok"}` shape entirely — a third,
also-wrong outcome.

### D6 — BLOCKER — eight schemas carry the keys, not four; the router bodies are unlisted

§10A.3 and the plan name four request schemas. The keys are declared in **eight**
places; the four the plan omits are the FastAPI-bound bodies:

| # | Schema | File:lines | Listed in plan? |
|---|---|---|---|
| 1 | `_CreateItemBody` | `routers/api_v1/items.py:68-70` | **no** |
| 2 | `_UpdateItemBody` | `routers/api_v1/items.py:91-93` | **no** |
| 3 | `_FindOrCreateItemBody` | `routers/api_v1/items.py:113-115` | **no** |
| 4 | `_TaskItemInputBody` | `routers/api_v1/tasks.py:105-107` | **no** |
| 5 | `CreateItemRequest` | `services/commands/items/requests/__init__.py:195-197` | yes |
| 6 | `UpdateItemRequest` | `…/items/requests/__init__.py:246-248` | yes |
| 7 | `FindOrCreateItemRequest` | `…/items/requests/__init__.py:460-462` | yes |
| 8 | `FindOrCreateItemInput` | `…/tasks/requests/__init__.py:36-38` | yes |

This matters in one direction only, and it is the dangerous one. §10.2 step 2 says
"monetary fields removed from the item create / patch / find-or-create request
schemas" — a natural reading of "request schema" includes rows 1–4. If an implementer
deletes the keys there, no `ConfigDict(extra="forbid")` exists on any of them
(§10A.3's own verification), so pydantic's default `ignore` drops a client's price at
the HTTP boundary and the command-side validator never sees it: **200, money silently
discarded** — the exact failure mode the bridge exists to remove. Route: add rows 1–4
to "Files expected to change" with the instruction that the three keys are **retained**
there, and add a C4 row proving a non-NULL value survives the router body into the
command (otherwise the whole bridge is untested at the only layer that can drop it).

### D5 — BLOCKER — C4's named mutation is inert under the natural fixture

C4: *"deleting the validator from `services/commands/tasks/requests/__init__.py`
(definition site) must turn the create_task present-non-NULL row red."*

`create_task` has two item paths (`services/commands/tasks/create_task.py:189-232`):

- `article_number is None and sku is None` → `create_item_in_session` directly (no
  further request-schema validation);
- otherwise → a nested `ServiceContext` carrying
  `request.item.model_dump(exclude_unset=True)` into `find_or_create_item`, which
  re-parses through **`FindOrCreateItemRequest`** (`find_or_create_item.py:58`) — the
  items-file schema, which carries the same validator per the plan's own file list.

So with any fixture that sets `article_number` or `sku` — i.e. the shape the manager
app actually sends — deleting the tasks-file validator leaves the row **green**,
caught one layer later. This is P-Q's extension repeating verbatim (a plan's named
mutation checked against the implementation it will meet). Route: either pin the
fixture to the no-identifier branch (and say so in the row), or re-site the mutation
as a pair — one per definition site — with both red sets declared (P-I sixth
extension: N named mutations ⇒ N ledger rows).

### D13 — should-fix — C4's harness is unnamed (P-R)

C4 asserts `422` — an HTTP status only the router layer produces. The existing item
router tests call the route coroutine directly with a pre-built body
(`tests/unit/test_items_router.py:9-31`), which never exercises FastAPI body binding.
The shipped precedent that does is `tests/unit/routers/api_v1/test_item_economics_router.py:41-60`
(`FastAPI()` + `include_router` + `dependency_overrides[get_db]/[get_jwt_claims]` +
`TestClient`). Route: name it in the plan, the way §10 names the DB recipe.

### D16 — note — `model_fields_set` is inert, and two C4 rows share one path

§10A.3 rests the bridge on `model_fields_set` distinguishing present-null from absent.
Since both outcomes are *pass*, the predicate reduces to `value is not None`; the
`model_fields_set` machinery adds nothing. Worse, on the create-item path it cannot
work at all: `routers/api_v1/items.py:154` builds `incoming_data=body.model_dump()`
**without** `exclude_unset`, so every key is materialised as `None` before the command
request is constructed. Probe P1(D) confirms `model_fields_set == {item_value_minor,
item_cost_minor}` for a body where the client sent neither key (the update and
find-or-create routes, `:346` and `:227`, do use `exclude_unset=True`; `create_task`
at `tasks.py:335` also does). Consequence for C4: on the create-item schema the
"key absent" and "key present null" rows exercise **the identical code path** — P-G
applies, name them separately required or collapse them explicitly.

### D15 — note — the M-11 frontend evidence is a misread

The plan's Notes and §10A.3 both justify present-null support with *"the manager app
sends `item_value_minor: null` on every task creation
(`use-create-task.ts:84-86`)"*. Lines 84-86 sit inside the block starting at
`primary_item:` (`:71`) — the **optimistic cache entry**, not the request body. The
request body is built by
`packages/task-creation/src/lib/normalize-task-form-payload.ts:88-101`
(`buildItemFields`), which:

- **omits `item_value_minor` and `item_cost_minor` entirely** (they are not in the
  returned object at all);
- emits `item_currency: item.item_currency || undefined` (`:96`) — `undefined`
  serialises to an absent key.

No component renders a currency input: `item.item_currency` appears only in
field-name membership lists (`InternalFormContent.tsx:78`, `ReturnFormContent.tsx:97`,
`PreOrderFormContent.tsx:111`) and as `undefined` defaults
(`…/lib/*-form-default-values.ts`). Net: production task creation sends **all three
keys absent**. The items app's `CreateItemInputSchema`/`UpdateItemInputSchema`
(`features/items/types.ts:56,84`) declare the money keys, but no form writes them —
`:134` only formats for display, `:153` builds an optimistic item.

Direction of the correction: the bridge's chosen shape (reject iff present and
non-NULL) is still right and strictly safer than the alternatives, so **no design
changes**. But the recorded fact is false, and it is load-bearing prose: it tells the
next reader that present-null is exercised in production when nothing is. Route: fix
the Note and §10A.3's parenthetical to cite `normalize-task-form-payload.ts:88-101`,
and state the real risk instead — *if* a currency input is ever mounted, task
creation 422s the moment a user picks a currency.

---

## B. The data migration

### D2 — ANSWERED (was BLOCKER) — `created_by_id` is NOT NULL and the migration has no user

`models/tables/item_economics/item_valuation.py:26`:
`created_by_id … ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=False`.
§10.2 and §10A say nothing about attribution. The obvious fallback is not total:
`models/tables/items/item.py:55` declares `items.created_by_id` **nullable**, so
"copy the item's creator" aborts mid-migration on any legacy item created without
one — precisely the abort class P2 exists to pre-empt, unhandled. The value is
owner-visible: `serialize_item_valuation`
(`domain/item_economics/serializers.py:96-108`) emits `created_by_id` in the history
payload.

**Resolved 2026-08-14 (owner):** no attribution decision is needed — the functionality
is unshipped, no price exists anywhere, and the legacy source columns measure empty on
every write-path check. The gap becomes the **P3 pre-flight refusal** described in the
owner-decisions section: attribute to `items.created_by_id`, refuse with a row report
where an amount exists with a NULL creator. The plan carries it as a third P-class
guard beside P1/P2 (§10A.2's table gains a row), one C1 row, and one C2 post-condition
row asserting an empty offender set. This keeps the migration total without inventing
a user and without guessing an author.

### D3 — BLOCKER — post-condition 2 contradicts the idempotency clause

§10A.1 asserts inside `upgrade`:

> 2. created-valuation count == count of **non-deleted** items with ≥ 1 non-NULL amount

and, four lines later:

> Idempotent by predicate: the copy INSERT excludes items that already have a current
> valuation, so re-execution affects zero rows.

These are incompatible whenever the excluded set is non-empty. Two reachable ways it
is non-empty: (a) **re-running the migration** — every item is already valued, the
INSERT creates 0, pc2 expects N, `RuntimeError`; (b) **phase 5 is live** — `PUT
/api/v1/item-economics/items/{id}/valuation` has shipped, so a manager can price an
item that also carries legacy money; that item is journaled, skipped by the copy, and
pc2 fails. C2 restates the same defect ("valuation count == non-deleted items with ≥1
amount"). Route (intention amendment): state pc2 over the journal —
*count of journal rows with `valuation_client_id IS NOT NULL` == count of non-deleted
items with ≥1 amount that had no current valuation at entry* — and give C2 a row that
runs the migration **twice** and asserts the second run is a no-op *without* aborting.
The phase-5 collision also needs its own C1 row (item with legacy money **and** a
current valuation → journaled, `valuation_client_id` NULL, existing valuation
untouched); the plan has no such row today.

### D7 — should-fix — the idempotency predicate must be INV-V1's predicate, verbatim

"excludes already-valued items" has at least three inequivalent readings. The only
safe one is the partial unique's own predicate
(`uix_item_valuations_current`, `item_valuation.py:35`):
`NOT EXISTS (… item_id = i.client_id AND superseded_at IS NULL AND is_deleted = false)`.
A narrower reading ("any valuation row exists") skips items whose only valuation is
superseded or deleted; a wider one ("no non-deleted row") re-inserts against a live
current row and raises `IntegrityError`. Note the S1/S2/S3 order of §7A.1 does not
apply here: with this predicate the migration only ever writes the *first* row of a
chain, so there is nothing to close and `superseded_by_id` is never set — worth
stating so a reviewer does not look for the missing S1.

**Resolved 2026-08-14 (owner):** items whose only valuation is soft-deleted are
**skipped** — the deletion is a decision somebody made about that item, and the
upgrade knows less than they did. The eligibility predicate therefore reads
`NOT EXISTS (… item_id = i.client_id AND is_deleted = false)` for the skip test
while INV-V1's full predicate remains the conflict the index enforces; state both, so
the difference between "eligible" and "would violate the index" is written down rather
than inferred. Since no valuation exists on any database today the clause cannot fire —
it is written now so the rule is explicit rather than emergent.

### D8 — should-fix — free choice: `client_id` generation

`models/base/identity.py:9-11` generates client_ids as `f"{prefix}_{ULID()}"` in
Python. Postgres cannot produce a ULID, so a single set-based `INSERT … SELECT`
(which the plan's phrasing implies) cannot mint `ival_…` ids of the repo's shape.
Delegate explicitly: the migration SELECTs the eligible rows, generates one
`generate_id("ival")` per row in Python, and inserts with an executemany — the
eligibility predicate (D7) still lives in the SELECT, so idempotency is unchanged.
Precedent for Python-side iteration inside a migration: `5caae620088c:26-46`.

### D11 — should-fix — the column mapping is nowhere written

Neither §10.2, §10A, nor the plan states which legacy column becomes which valuation
column. §2.1 explicitly records that the only two available descriptors **disagree**
about what these fields mean ("estimated business value"/"internal operational cost"
vs sale-side/acquisition-side). Card 1 of round 1 settled the semantics the domain
assigns, so this is not an owner question — but the plan must write the mapping down:
`item_value_minor → expected_sale_price_minor`, `item_cost_minor → purchase_cost_minor`,
`item_currency → currency`. C1's "copied verbatim … byte-equal" row then names all
three pairs individually (P-O: an assertion over three pairs asserts each).

### D12 — should-fix — free choice: audit rows for migrated valuations

`set_item_valuation` records `item_valuation.created` via `audit(...)`
(`set_item_valuation.py:162`), and §6.4 registers that identity. The migration writes
raw SQL and emits nothing. §10.2 is silent. Recommend delegating explicitly to "no
audit rows — the journal is the record", and stating it in the plan, so the reviewer
does not file the absence as a finding (and so nobody adds `audit_logs` writes that
would need a user id they do not have — see D2).

### D14 — note — the phase-5 N2 forward note's premise is false

The note predicts that this phase's bulk creation makes the history query's
`client_id DESC` tie-breaker load-bearing. It does not. `get_item_valuation_history`
(`services/queries/item_economics/get_item_valuation_history.py:23-31`) is scoped to
**one** item and orders `created_at DESC, client_id DESC`; the migration creates **at
most one** valuation per item (D7's predicate). A bulk run therefore produces one row
per item's history — no two rows can tie within any one item's read. The
reviewer-supplied correction (build two rows with an explicit identical `created_at`,
assert `client_id DESC`) is still the right criterion and should be carried, but it
must be labelled a **synthetic fixture**, not a consequence of the migration; an
implementer who tries to produce the tie *through* the migration will not manage it
and may weaken the row.

### D20 — note — two environment facts that hold in the phase's favour

Both verified in `app/migrations/env.py`, recorded so nobody re-derives them:

- `_MIGRATION_BOOKKEEPING_SUFFIX = "_journal"` (`:30`) with `_include_object`
  (`:33-48`) keeps autogenerate from emitting `op.drop_table` for reflected
  `*_journal` tables. The registry's `item_valuation_migration_journal` (§6.1) matches
  the suffix, so the journal is protected **by name** — a rename would silently
  forfeit that protection, which is worth one line in the plan.
- `transaction_per_migration=True` (`:171`) plus the `connection.rollback()` at `:167`
  (the 4B repair) means each migration commits independently and a pre-flight
  `RuntimeError` leaves nothing persisted — §10A.2's "before any write" guarantee is
  structurally true, not merely sequential.

---

## C. The removal surface

### D4 — BLOCKER — the read census is 9 endpoints across 2 serializer functions

The plan says "five embedding payloads"; its own forward hazard (D9, phase-1
projection) says "six `serialize_item` call expressions in five files". Both
undercount, and for different reasons: the six-call figure covers only
`domain/tasks/serializers.py::serialize_item` and ignores the items-side base
serializer, which C5's prose list silently mixes in ("item list/detail"). Re-derived
today, caller-graph first, endpoint census second (the phase-1 D1 lesson):

**`serialize_item` — `domain/tasks/serializers.py:91` (money at `:105-107`)**

| # | Call site | Query service | Endpoint | Roles today |
|---|---|---|---|---|
| 1 | `services/queries/tasks/tasks.py:388` | `list_tasks` | `GET /api/v1/tasks` | ADMIN, MANAGER, WORKER, SELLER |
| 2 | `services/queries/tasks/tasks.py:697` | `get_task` | `GET /api/v1/tasks/{task_id}` | ADMIN, MANAGER, WORKER, SELLER |
| 3 | `services/queries/tasks/list_task_coordination_threads.py:224` | `list_task_coordination_threads` | `GET /api/v1/tasks/customer-coordination/threads` | ADMIN, MANAGER, SELLER |
| 4 | `services/queries/upholstery/upholstery_order_needs.py:595` | `get_upholstery_order_need_items` | `GET /api/v1/upholstery-order-needs/{upholstery_id}/items` | ADMIN, MANAGER |
| 5 | `services/queries/upholstery/upholstery_orders_query.py:496` | `list_upholstery_order_items` | `GET /api/v1/upholstery-orders/items` | ADMIN, MANAGER |
| 6 | `services/queries/items/seat_tasks_pending_upholstery.py:335` | `list_seat_tasks_pending_upholstery` | `GET /api/v1/item-upholsteries/pending-seat-tasks` | ADMIN, MANAGER, WORKER |

**`_serialize_item_base` — `domain/items/serializers.py:90` (money at `:103-105`)**,
reached through `serialize_item_list` (`:120`) and `serialize_item_detail` (`:124`)

| # | Call site | Query service | Endpoint | Roles today |
|---|---|---|---|---|
| 7 | `services/queries/items/items.py:88` | `list_items` | `GET /api/v1/items` | ADMIN, MANAGER, WORKER |
| 8 | `services/queries/items/items.py:144` | `get_item` | `GET /api/v1/items/{client_id}` | ADMIN, MANAGER, WORKER |
| 9 | `domain/customers/serializers.py:35` (inside `serialize_customer_detail`) → `services/queries/customers/customers.py:102` | `get_customer` | `GET /api/v1/customers/{client_id}` (`customer.linked_items[]`) | ADMIN, MANAGER, WORKER |

Row 9 is the one no prior census has ever named: a customer-detail payload embeds
full item rows, money included, through a *different* domain's serializer. Route:
C5's rows are these nine, each a key-set assertion on production serializer output,
with the parametrize id naming the endpoint (P-V extension). Two functions ⇒ two
named mutations (re-adding the three keys to each must redden its own set), and the
declaration states the **full observed red set** (P-I fifth extension) — deleting the
keys from `_serialize_item_base` should redden rows 7-9 together, which is design
information about the shared base.

### D18 — note — there are zero test dependents

The N-f/Projection-practice grep, run over payload keys and not only symbols:
`item_value_minor` / `item_cost_minor` / `item_currency` appear **nowhere** under
`app/tests/` (0 files). `tests/factories/` contains only `.gitkeep` — items are built
inline. No test asserts an exact-dict or key-set over any item payload. Two
consequences: (1) removing the keys breaks **no** existing test, so a green suite is
not evidence the phase worked; (2) every C5 assertion is new, and C5's mutations are
the only arbiters that will ever exist for this surface. Worth stating in the
implementer prompt so "the suite is green" is not offered as coverage.

### D21 — note — R5-2 discharged

The plan asks this projection to verify no interim redaction was assumed anywhere.
Verified: neither `serialize_item` nor `_serialize_item_base` takes an
`include_monetary`-style flag (contrast `serialize_step`, §11A.3); the redaction
precedent `serialize_item_worker_light` (`domain/tasks/serializers.py:422-451`)
carries no money keys at all and is a separate function. WORKER reaches item money
today on rows 1, 2, 6, 7, 8, 9 of D4's census; column removal is what closes it, as
R5-2 decided. No phase 1-5 code assumed otherwise.

### D22 — should-fix — OpenAPI mirror scope

The plan names `routers/README.md`. Actual mirror rows carrying the three keys:

- `app/beyo_manager/routers/README.md` — 12 rows at `:2082-2084`, `:2140-2142`,
  `:2242-2244`, `:2669-2671` (the fourth block is the `item.*`-prefixed create_task
  nested body).
- `frontend/docs/architecture/backend/routers_endpoints/README.md:1918-1920,
  1976-1978, 2078-2080, 2475-2477` and
  `frontend/docs/architecture/backend/tables/README.md:437,467,469` — generated
  mirrors under the **frontend** tree.

The frontend mirrors are outside this phase's declared perimeter and outside the
`Application_contracts` exclusion the goal already states. Route: pin the backend
README as in-scope, and add the frontend doc mirrors to the phase-9 drift batch
explicitly, so their staleness is a recorded decision rather than an oversight
(note `tables/README.md:469` also mirrors the `create_type=True` flag D10 flips).

---

## D. The column drop and its ladder

### D9 — should-fix — C6's "fresh metadata-create" has no harness in this repo

C6 requires "fresh metadata-create succeeds post-drop (proves the `create_type`
ownership flip — R2-1)". There is **no `create_all` anywhere** in the codebase
(verified: the only `create_all` matches under `tests/` are unrelated test *names*,
`test_create_allows_*`), and §10's own disposable recipe is migration-driven
(`scripts/create_db.py` creates an empty database; alembic builds the schema). So the
criterion as written obliges the implementer to invent a harness whose failure mode
nobody has ever seen, to prove a flag that is inert on every path this project ships.

Two better arbiters already exist in-tree, and both are cheap:

- the shipped structural precedent `tests/integration/models/item_economics/test_phase4b_category_schema.py:40-59`
  — reflect `pg_type` / `pg_attribute` on the configured DB and assert
  `item_currency_enum` still exists with **exactly one** remaining column user
  (`item_upholstery_requirements.currency`), measured today as 2 → expected 1;
- `compare_metadata(context, Base.metadata)` from the same file (`:28-29`) for
  model↔DB agreement after the drop — with P-X's caveat stated: it is blind to
  partial-index predicates, `server_default` expressions and comments, so the enum
  ownership itself still needs the structural row above.

Route: replace C6's metadata-create clause with those two rows, keep the
upgrade→downgrade→upgrade round-trip, and — if the metadata-create property is still
wanted — make it an explicit new harness with its own named mutation, not a clause.

### D10 — should-fix — the downgrade's enum re-add, and which downgrades C3 runs

Two under-determined points in the drop migration:

1. **Re-adding the column.** `downgrade` must re-add `item_currency` against a type
   that still exists. `op.add_column` with a bare `sa.Enum(ItemCurrencyEnum,
   name="item_currency_enum")` emits `CREATE TYPE` and fails with `DuplicateObject`.
   The in-tree idiom is `postgresql.ENUM(..., create_type=False)` — exemplar
   `5caae620088c:20-22` used at `:48-51`. Pin it. (Conversely `op.drop_column` does
   **not** drop the type — `5caae620088c:66` is the precedent — so "retains PG type
   `item_currency_enum`" is satisfied by default, and the criterion asserts it rather
   than the implementer engineering it.)
2. **C3's ladder position.** "all three columns restored byte-identically on every
   journaled row" requires downgrading **both** migrations (the drop's downgrade
   re-adds the columns as NULL; the data migration's downgrade repopulates them from
   the journal). C3 does not say so, and a reader can equally take it as a single
   downgrade — which would assert against columns that do not exist. State the exact
   revision pair and the direction, and assert the end state with **state queries,
   never exit codes** (§10 / L5).

### D19 — note — the archgraph note is stale

The plan states "the `Item` table itself is NOT in the graph (research §7); likely
zero new nodes". As of the phase-5 post-approval pass (`3d97721`, nodes created
2026-08-14T10:12:40Z) that is false: **`node:table-item`** exists — type `table`,
name `items`, origin `ai_inferred`, reviewState **pending** — and its description
already reads "…until phase 6's migration — the legacy money columns
(`item_value_minor`, `item_cost_minor`, `item_currency`) that ItemValuation
supersedes". A pending edge
`command-item-economics-set-item-valuation --reads_from--> table-item` sits beside it.
So phase 6's delta is **one node edit** (that sentence stops being true when the
columns drop), not zero; and the node is one of the 6 items in the coordinator's
§8 confirmation queue. Graph state at projection time, unchanged by this session:
revision `bd72c36d79c6…`, 154 nodes / 200 edges, 0 stale, 6 pending.

---

## E. Criteria quality under §9

### D23 — note — counts and ids

- **C5 "five embedding payloads"** — wrong; the table is nine rows across two
  functions (D4). P-V: the criterion names the table its rows enumerate, and the ids
  map one-for-one.
- **C1 "intention tests 13/20"** and **C4 "12 rows"** — both correctly derive from a
  table (§10A.2's five rows expanded to six by the soft-delete split; four schemas ×
  three cases). Per P-V's second extension and the numbering rule, each parametrize id
  names the **authority row** it discharges in that authority's *current* numbering —
  e.g. `10A2-row3-amount-null-currency-refuses-p1`, `10A3-create-task-present-nonnull-422`.
- **C2/C3** carry no row count and enumerate prose clauses; after D3's restatement
  they should be tabulated, one row per asserted post-condition, so a reviewer can
  count them without re-deriving.
- **Sole-predicate audit (rule 2's companion):** C1's "amounts ≥ 0 + currency,
  non-deleted item → journaled + current valuation" fixture must not also satisfy the
  skip predicate; and after D3, the new "already-valued item" row's fixture must carry
  legacy money **and** a current valuation, so the exclusion is the only reason no
  second valuation appears.
- **P-J (static proxies):** C3's "deletion is by `valuation_client_id`, never by
  predicate" is currently proven by a behavioural row (a manually created valuation
  survives). That row is good; if any static `inspect.getsource` proxy is added
  beside it, it needs its own named mutation.

---

## Reality checks — summary of what resolved and what did not

| Plan claim | Verdict |
|---|---|
| Read-first §§5, 6.4, 7, 10 of the master plan | resolve; §6.4 carries the `ITEM_MONEY_MOVED` row (`:340-341`) and the P1/P2 `RuntimeError` row (`:342-343`) |
| Intention §10.2 / §10A entire / §2.1 / §4.7 / §10.4 | resolve and say what the plan claims, except §10A.3's "pydantic ValidationError" (D1) and §10A.1's pc2 (D3) |
| Exemplar `97b60e06d42a` (journaled data migration) | present; journal + pre-flight `RuntimeError` + post-condition + exact `downgrade` idioms all usable verbatim |
| Exemplar `595e7b840926` (partial-unique idiom) | present |
| Exemplar `5caae620088c` (report-first pre-flight, dependent counts) | present — **not cited by the plan**; it is the closer exemplar for a refusal report and for `postgresql.ENUM(create_type=False)`; add it to Read-first |
| Precedent `update_item.py` `model_fields_set` | present (`:55`, `:100`) but inert for this purpose (D16) |
| Contracts `30_migrations`, `06_commands`(+local), `46_serialization`(+local) | all present under `backend/architecture/` |
| Six-site write census (§2.1) | confirmed exactly six: `_create_item_in_session.py:38-40,117-119`; `create_item.py:67-69`; `find_or_create_item.py:30-32` (`_DIRECT_FIELDS` update branch, applied `:99-101`) and `:166-168`; `update_item.py:35-37`; `create_task.py:208-210` |
| "`item_currency_enum` retained for `item_upholstery_requirements`" | confirmed live: 2 column users today, 1 after the drop; `item_upholstery_requirement.py:44` already `create_type=False`, `item.py:41` holds `create_type=True` |
| "Frontend types typed-but-unrendered, breakage risk low" | holds for the two amounts; `item_currency` is a *registered* form field with no rendered input (D15) |
| "the `Item` table is NOT in the graph" | **stale** (D19) |
| Suite baseline 1968/23/1, dev DB at head, economics tables at zero | head `5caae620088c` and `item_valuations = 0` re-verified today; the suite was not re-run (no code touched — see perimeter) |

## Verdict

**AMENDMENTS_REQUIRED** — 23 ledger rows, **5 blocking** (D1, D3, D4, D5, D6), zero
open owner decisions: both cards were raised and answered on 2026-08-14, and D2/D7
now carry named resolutions. The implementer prompt should not be compiled until every
row is routed (amended, upstream-changed, or delegated in writing).

Note for the coordinator on **D3 under the owner's answer**: the "phase 5 already
priced this item" trigger for post-condition 2 is unreachable (nothing has shipped),
but the **re-run** trigger is not — C2 explicitly requires "re-running the copy affects
zero rows", so a test will execute the copy statements twice and the post-condition
will abort on the second pass. D3 stays blocking on its own merits.

## Write perimeter (full)

Documents created — **1**:

- `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase6_projection_r0_handoff.md` (this file)

Documents edited: **this file only**, in one later pass on 2026-08-14 recording the
owner's answer to both cards (opening paragraph, the owner-decisions section, ledger
rows D2/D7 and their detail entries, the verdict). No other artifact was touched.
Code changed: **none** (no file under `app/` or
`frontend/` was written; the plan, the intention and the master plan are untouched,
per the projection doctrine's "you report, you do not fix"). Tool-recorded state:
**archgraph zero delta** — this session issued only `archgraph_status` and two
read-only queries (`search_nodes`, `list_pending_reviews`); revision is
`bd72c36d79c6…` before and after, 154 nodes / 200 edges / 6 pending.

## Probe declaration

Two probes, both outside the repository tree, neither leaving residue:

- **P1 — pydantic error-translation probe.** A heredoc `python3` script run from
  `backend/app/` with `PYTHONPATH=.`, importing only
  `beyo_manager.errors.validation.ValidationError` alongside pydantic, declaring four
  throwaway models in memory. It produced the D1 table and the D16 `model_fields_set`
  observations. No file written, no database touched, no repo file modified.
- **P2 — live-data census.** Read-only `SELECT`s via
  `docker compose exec -T postgres psql -U postgres -d beyo_manager` (counts over
  `items`, `item_valuations`, `item_upholstery_requirements`, `alembic_version`,
  `pg_type`/`pg_attribute`). No DDL, no DML, no disposable database created. The
  configured database remains at head `5caae620088c` with 479 items and 0
  `item_valuations` rows — byte-identical to the state at session start.

**Disposable-DB rehearsal (charter rule 7 / prompt) — NOT performed, and why.** The
prompt makes disposable-DB work mandatory for the migration round-trip, the refusal
path and the journal shape. Every one of those rehearsals requires the two migration
files to exist; they do not — this is round 0, before any implementation, and the
projection doctrine forbids me from writing them ("no code"). Rehearsing the *existing*
head on a disposable database would re-verify only what the 4B fix cycle already
recorded in §10 (cold build to `5caae620088c` in 1.70s, zero residue). I have instead
front-loaded the measurements that the rehearsal would have produced — the exact
pre-counts each post-condition must equal (all zero, D17) and the enum's live column
users (D9/D10) — and D17 records the consequence that matters: on the only reachable
database the rehearsal would have been vacuous. The rehearsal itself belongs to the
implementer session, and the plan should carry it as C6's manual lifecycle check with
the §10 recipe named per criterion.
