---
plan: phase 8B (inline item prices at task creation — round 18, R18-1)
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-15
actor: Claude (reviewer role, projection gate)
---

# Phase 8B projection — round 0

## Opening (owner-readable)

The plan for pricing an item while creating its task is sound in shape and reuses
machinery that already ships — nothing new has to be built, no database change is
needed, and the risky part (a price that survives even when the automatic budget
calculation fails) is correct as written. But the plan describes the new price
fields as copying the existing price screen "exactly", and they cannot: on the
price screen a currency is always required, whereas on task creation the whole
price block is optional. Left as written, an implementer would either make every
task creation demand a currency or quietly invent their own rule. Eighteen items
are recorded below; most are one-paragraph corrections I have already verified
against the running code.

**One decision needs you personally** (card 1): what should happen when a manager
re-uses an item that already exists and types a price anyway. The plan's current
answer is to refuse the whole request. I think that is too strict for the common
case and recommend a narrower rule. Until you answer, the gate holds and the
implementer prompt is not compiled.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — When a manager re-uses an item they've handled before and types a price anyway, should the whole task creation be refused?

**Question.** Refuse always, refuse only when the item already has a price, or
accept and let the new price replace the old one?

**Story.** A manager makes a return task for a chair the workshop has restored
before, so they type its article number and the system finds the existing chair.
The new form shows price fields, so out of habit they fill in 4 500 kr. Today's
planned answer is a red error and no task at all — they must clear both fields and
start again. Meanwhile most of the workshop's older chairs exist in the system but
have never had a price at all: those are exactly the ones a manager most wants to
price while making the task, and they would be refused too.

**Branches.**
- **A — refuse always** (the plan's current default): habit-typing costs a retry
  every time, and the never-priced back catalogue can never be priced in one call.
- **B — refuse only if that item already carries a price; if it has none, save the
  price as its first one:** an existing price is never touched by a task creation,
  and the unpriced back catalogue gets priced in the same call.
- **C — accept always, replacing the old price:** one call every time, but a task
  creation can now change a chair's standing price, which quietly re-budgets every
  future task for it.

**Recommendation.** **B** — it keeps the whole point of A (a task creation can
never change a price that already exists) while removing the friction that matters
most, since after this change the majority of matched items have no price at all.

**On silence.** The gate holds: the plan keeps A, the implementer prompt is not
compiled, and the acceptance rows below stay unwritten — A and B need materially
different tests.

**Trace.** intention §7B.6 (existing-item clause); plan C4; ledger L4, L11;
owner_decisions R18-1.

---

## Decision ledger (18 rows)

Severity: **H** = blocks prompt compilation · **M** = amend before compiling ·
**L** = record/route, does not block.

| # | Sev | Decision point | Classification | Routing |
|---|---|---|---|---|
| L1 | H | "mirroring `ItemValuationRequest` exactly" is false against shipped code | plan gap + intention gap | amend plan Goal/task 1; lettered amendment to §7B.6 |
| L2 | H | C5 "currency alone" left undecided | plan gap (delegated to this session) | **decided below** — amend C5 |
| L3 | H | C1 "the auto-commit fires" is not true for 3 of 5 reachable shapes | plan gap (rule 2) | amend C1 into 5 enumerated rows |
| L4 | H | C4's "no task created" is unsatisfiable without the owner-mode harness | plan gap (P-R 2nd ext.) | amend C4; name harness + rollback row |
| L5 | H | C3 "mixed payload also 422" has three different outcomes | plan gap (rule 2, P-O) | amend C3 into 3 rows; pin validator order |
| L6 | M | C6 names no harness; the OpenAPI clause has no in-tree precedent | plan gap (P-R) | amend C6; name harness or drop clause |
| L7 | M | "the item-creation branch" — there are two | plan gap | amend task 2 with the pinned insertion point |
| L8 | M | Birth-write failure refuses the whole request — unstated | plan gap | one sentence in plan Notes |
| L9 | — | §7B.5 interaction rows: the plan's reading is CORRECT | verified by construction | record; keep as stability row w/ non-vacuity |
| L10 | M | §4.7A writers list and §11A.5(c) contradict R18-1 | intention gap | route upstream (lettered amendments) |
| L11 | M | Existing-item refusal identity unregistered | registry | proposal below; contingent on card 1 |
| L12 | L | Plan's archgraph note names a node that does not exist | reality check | amend Notes |
| L13 | L | Three stale line citations | reality check | corrected below |
| L14 | L | `routers/README.md` — route is PUT, table pre-drifted | reality check + scope fence | 8B adds 3 rows; drift → §2.6 / phase 9 |
| L15 | L | `quantity` vs per-unit pricing | free choice → delegate | no 8B logic; sentence for R18-2 |
| L16 | L | Multi-item is moot for 8B | verified | record so review does not re-derive |
| L17 | L | A phase-6 structural test constrains `create_task.py` source text | reality check | one line in plan Notes |
| L18 | L | Response gives no signal whether the task got priced | free choice → delegate | record for R18-2 |

---

## L1 — H — the mirror claim is false (plan Goal, task 1; intention §7B.6)

The plan and §7B.6 both say the trio mirrors `ItemValuationRequest` **exactly**,
glossed as "ge=0 amounts; currency required whenever either amount is present".
The shipped model
(`app/beyo_manager/services/commands/item_economics/requests/__init__.py:116-119`):

```python
class ItemValuationRequest(_Request):
    expected_sale_price_minor: int | None = Field(default=None, ge=0)
    purchase_cost_minor: int | None = Field(default=None, ge=0)
    currency: ItemCurrencyEnum          # unconditionally REQUIRED
```

`currency` is required **unconditionally** — there is no currency-iff-amount rule
anywhere on the PUT surface. The gloss describes a model that does not exist.

An exact mirror is also unimplementable here: on task creation the entire block is
optional (absent trio is the overwhelmingly common case, §10A.3), so a required
`currency` would 422 every task creation that omits prices.

**Proposed amendment (plan Goal + task 1).** Drop "exactly". State the 8B shape
directly: all three fields optional, `ge=0` on both amounts, and `currency`
required **iff** either amount is present. Add one sentence recording that this
DIVERGES from `ItemValuationRequest`, and why (the PUT surface's block is the
request; here it is an optional sub-block).

**Upstream (intention §7B.6).** Same correction, as a lettered clause — do not
renumber (charter, §7A precedent).

---

## L2 — H — C5 "currency alone (no amounts)": DECIDED — accepted and ignored

The plan delegated this to the projection ("recommend: accepted-and-ignored OR
422 — decide one"). Decided: **accepted and ignored** — 200, **no valuation row
written**, the item stays `item_unvalued`, task creation otherwise unchanged.

Two verified reasons:

1. **A currency-only valuation row is impossible at the database.**
   `app/beyo_manager/models/tables/item_economics/item_valuation.py:34` carries
   `CheckConstraint("expected_sale_price_minor IS NOT NULL OR purchase_cost_minor
   IS NOT NULL", name="ck_item_valuations_amount_present")` (= §4.7A's "at least
   one of the two amounts is non-NULL"). If a currency-only payload ever reached
   the chain writer, the flush would raise `IntegrityError`, and
   `translate_integrity_error` (`_common.py:38-44`) only translates **registered
   index names** — a CHECK violation falls through to `raise exc`, reaching
   `run_service`'s generic handler as "An unexpected internal error occurred."
   A 500 on a typo.
2. **422 would reproduce a hazard §10A.3 already recorded.** §10A.3 notes, of the
   legacy key: *"if a currency input is ever mounted, task creation 422s the moment
   a user picks one."* Phase 8B exists to make the frontend mount exactly such an
   input. A currency-alone 422 means a manager who picks a currency and then leaves
   the price blank cannot create the task at all.

Accepted-and-ignored does not violate P-B (no inferred zeros): nothing is inferred,
no money is discarded, and the item's status is unchanged from a trio-absent
request.

**Proposed C5 (five rows, exact outcomes, no disjunction):**

| row | payload | expected |
|---|---|---|
| C5.1 | `expected_sale_price_minor` set, `currency` absent | 422, `item.currency` message; no valuation |
| C5.2 | `purchase_cost_minor` set, `currency` absent | 422, `item.currency` message; no valuation |
| C5.3 | `currency` alone, both amounts absent | **200**, task created, **no valuation row**, status `item_unvalued` |
| C5.4 | `expected_sale_price_minor: -1` + `currency` | 422 from `ge=0`; no valuation |
| C5.5 | `purchase_cost_minor: -1` + `currency` | 422 from `ge=0`; no valuation |

C5.3 needs the sole-predicate companion (rule 2): assert **zero** rows in
`item_valuations` for the item, not merely "no current row".

`expected_sale_price_minor: 0` with a currency is **valid** (`ge=0`, and the CHECK
is satisfied) and is NOT a C5 row — it is a priced item whose expected sale price
is zero. Worth one C1 row instead (it produces a computable, zero-budget
evaluation); flagged, implementer's call whether to add it.

---

## L3 — H — C1 "the auto-commit fires" is false for three of five reachable shapes

C1 asserts that with "a new item + trio" the auto-commit fires in an evaluable
workspace. Whether it fires is decided by `resolve_item_economics_status`
(`app/beyo_manager/domain/item_economics/configuration.py:129-169`) walking
`ITEM_READINESS_PRECEDENCE` (`:33-39`), and three reachable trio shapes skip:

| # | inline trio | model has an `item_purchase_cost` term? | resolver | auto-commit |
|---|---|---|---|---|
| 1 | expected + purchase + currency | yes | `NOT_EVALUATED` | **commits** |
| 2 | expected + currency | no | `NOT_EVALUATED` | **commits** |
| 3 | expected + currency | yes | `ITEM_MISSING_PURCHASE_COST` | skip line |
| 4 | purchase + currency | either | `ITEM_MISSING_EXPECTED_PRICE` | skip line |
| 5 | expected + purchase + currency, currency ≠ basis/model | either | `CURRENCY_MISMATCH` | skip line |

Row 3's gate is `has_purchase_term` (`configuration.py:147-152`) — the status fires
**only** when the selected model version carries an `item_purchase_cost` term
(§11A.4 row 7), so rows 2 and 3 differ solely in the fixture's model terms and both
are required (P-M companion: state which field the row varies).

**In every one of the five rows the valuation row EXISTS.** That is the phase's
actual claim and the rows share it; what differs is the evaluation and the skip
line. Row 5 is a lived scenario worth its own name — a manager prices a chair in
euro in a krona-configured workspace: the price is recorded, the budget is not.

**Proposed amendment.** Replace C1's single sentence with these five rows plus the
existing unconfigured-workspace row (six total). Each names its **one exact**
expected outcome — for the skip rows, the exact
`item_economics.auto_commit_skipped | … status=<value>` literal (§7B.5's verbatim
shape, phase-7 review-r1 N3 vocabulary). No row may assert a status disjunction.

Call-graph rule (phase-8 review L3): rows 3, 4 and 5 must not share a call graph
with row 1 — each drives a distinct resolver branch, which they do; the parametrize
id names the authority row it discharges (P-V ext.).

---

## L4 — H — C4's atomicity claim needs its harness named, and "nothing written" is a rollback claim

C4 asks the projection to pin the atomicity; the recommendation (refuse the whole
request) is right, but as written the criterion is not satisfiable and the wrong
harness makes it vacuous.

**(a) The refusal only rolls anything back in `maybe_begin` OWNER mode.**
`create_task` wraps everything in `maybe_begin(ctx.session)`
(`create_task.py:82`), and `maybe_begin`
(`services/commands/utils/transaction.py:22-26`) **yields without opening a
transaction** when the session is already in one. A test that calls `create_task`
with the default `db_session` fixture runs in **subordinate** mode: the raise
propagates, but the `Task` row flushed at `create_task.py:177-178` is still there,
and an assertion of "no task created" fails — or worse, is written to match the
wrong behaviour.

The in-tree precedent does it correctly:
`tests/integration/services/commands/item_economics/test_phase7_evaluations.py:167-206`
calls `await db_session.commit()` **before** invoking `create_task`, so
`session.in_transaction()` is false and `maybe_begin` owns (and therefore rolls
back). It also wraps the body in `try/finally` with `_cleanup_committed_fixture`
— charter rule 11½, mandatory here since the row commits.

**Proposed amendment:** C4 names that harness explicitly — *"the fixture is
committed before the call so `maybe_begin` owns the transaction (precedent
`test_phase7_evaluations.py:167`); the test owns a `try/finally` teardown."*

**(b) "Nothing written" is broader than "no valuation row".** The refusal can only
be decided after the item is resolved, and on the matched-existing path
`find_or_create_item` has already **mutated the matched item** before returning:
it assigns every field in `_DIRECT_FIELDS`
(`services/commands/items/find_or_create_item.py:22-36, 92-95`), may re-snapshot
the category (`:97-114`), always stamps `updated_at`/`updated_by_id` (`:116-117`),
and may enqueue a zone push (`:119-120`). The task row, its notes and its TaskItem
are also already flushed.

So C4 needs a row asserting the **matched item is byte-unchanged after the
refusal** (pick a field the payload would have overwritten — e.g. send a different
`designer` alongside the prices and assert the stored value is the original), not
only "no valuation row exists". Without it the criterion passes while the item is
silently half-updated by a refused request.

**(c) Enumerate both sub-cases** the plan already hints at: matched item **with** a
current valuation and matched item **without** one. Under card-1 branch A both
refuse; under branch B they differ, which is precisely why the card blocks.

---

## L5 — H — C3's mixed payload has three outcomes, and one of them is definition-order dependent

`reject_legacy_money` is a `model_validator(mode="after")` at
`services/commands/tasks/requests/__init__.py:48-50`, delegating to
`reject_legacy_item_money_values` (`items/requests/__init__.py:14-17`), which
raises the repo `ValidationError` (a `DomainError`) so it propagates out of
pydantic unwrapped (§10A.3 / R14-1). Adding a currency-iff-amount rule as a second
`model_validator(mode="after")` puts two validators on one model, and **pydantic
runs after-validators in definition order**. Three mixed cases, three outcomes:

| case | payload | outcome |
|---|---|---|
| (a) | legacy non-null + a *valid* trio | `ITEM_MONEY_MOVED` — either order |
| (b) | legacy non-null + amount-without-currency | **whichever validator is defined first wins** |
| (c) | legacy non-null + a negative amount | pydantic's `ge=0` field error **always** wins — field constraints run before any after-validator, so the response is `item.expected_sale_price_minor: Input should be greater than or equal to 0`, **never** `ITEM_MONEY_MOVED` |

C3's "mixed payload (legacy + new) also 422" is satisfied by all three, which is
exactly the disjunction charter rule 2 and P-O forbid — and case (b) is a coin flip
on where the implementer types the new method.

**Proposed amendment.** Pin `reject_legacy_money` **first in definition order** (the
bridge must not be shadowed by the new vocabulary's own validation) and enumerate
(a), (b), (c) as three rows with exact expected messages. Case (c) is documented
as a known, accepted precedence, not a bridge failure.

**Named mutation (charter rule 11 + expected-red rule).** *Move the new
currency-iff-amount validator above `reject_legacy_money` in
`services/commands/tasks/requests/__init__.py` (definition site)* → row (b) must
turn red. The plan names the expected red pytest node id before implementation.

The three existing single-key retention rows (P-G) already ship at
`tests/unit/test_phase6_api_bridge.py:33-60` (`create-task-nested-item-*`) — C3's
retention rows extend that parametrization rather than duplicating it, and per
P-G(a) they get their own named mutation ("delete `reject_legacy_money` from
`FindOrCreateItemInput`" → the three `create-task-nested-item-present-nonnull`
nodes redden).

---

## L6 — M — C6 names no harness (P-R), and its OpenAPI clause has no precedent

C6 is load-bearing: `_TaskItemInputBody` (`routers/api_v1/tasks.py:95-114`) is a
**hand-maintained mirror** of `FindOrCreateItemInput` with pydantic's default
`extra="ignore"`, so omitting the trio there means a client's price is silently
discarded at the HTTP boundary and the request 200s — D6's exact silent failure,
one layer up. Verified: the route is `PUT /api/v1/tasks`
(`tasks.py:329-342`) and it forwards `body.model_dump(exclude_unset=True)`.

Two in-tree harness precedents, both usable as-is:
- **field-presence introspection** —
  `tests/unit/routers/api_v1/test_item_economics_router.py:225-231`
  (`model_fields` + `is_required()`);
- **endpoint survival** — `tests/unit/test_phase6_api_bridge.py:105-133`, which
  builds a `FastAPI()`, `include_router`s the tasks router, overrides `get_db` and
  `get_jwt_claims`, monkeypatches `run_service`, and asserts the value survives to
  the domain validator.

The endpoint-boundary rule (phase-8 review L4) requires the **endpoint** row, not
only the `model_fields` row — so both.

**"OpenAPI advertises them" has no precedent:** there is no `app.openapi()`
assertion anywhere under `tests/` (verified). Either name `app.openapi()`
introspection as the harness or delete the clause — as written it ships satisfiable
by inspection, which is what P-R exists to prevent.

**Named mutation:** *delete the three fields from `_TaskItemInputBody` at its
definition site (`routers/api_v1/tasks.py:95`)* → the survival row must redden;
plan names the expected red node id.

---

## L7 — M — "the item-creation branch" — there are two, and newness is decided differently in each

`create_task` has two item paths:

- **`create_task.py:195-227`** — taken when `article_number is None and sku is
  None`; calls `create_item_in_session`; **always creates**. No `was_created` flag
  exists or is needed.
- **`create_task.py:228-296`** — calls `find_or_create_item`; newness is
  `item_result["was_created"]` (`:238`), which
  `find_or_create_item` returns `False` for a match found by
  `workspace_id AND is_deleted = false AND (article_number = X OR sku = Y)`,
  `.limit(1)` (`find_or_create_item.py:75-89`).

So "matched existing item" is decidable — but only inside branch two, and only
after that call has already run.

**Proposed amendment (task 2).** Pin one insertion point serving both branches:
after the TaskItem flush (`create_task.py:306`) and before the savepoint block
(`:307-309`), with each branch setting a local newness flag. Alternatively record
this as an explicit delegation — but not silently: the two branches are where an
implementer most plausibly wires the write once and misses the other.

---

## L8 — M — a failed birth write refuses the whole request; state it

The plan's Notes correctly defend the write sitting **outside** the savepoint. The
converse is unstated: because it is outside, any exception there aborts
`create_task`'s whole transaction — task creation fails. `IntegrityError` from the
chain writer's flush (`_common.py:158-161`) reaches
`translate_integrity_error`, which re-raises anything unregistered (`:44`), and a
poisoned PostgreSQL transaction cannot commit the task either (the §7B.5 hazard, in
a new place).

This is **safe by construction**, and the reason belongs in the plan: the item is
newly created inside this same transaction, so no concurrent writer can hold
`uix_item_valuations_current` for it, and the only other failure mode
(`ck_item_valuations_amount_present`) is prevented at the request boundary by L2.
One sentence beside the existing "so nobody 'fixes' it" note.

---

## L9 — verified — the §7B.5 interaction rows hold by construction

All four checks in projection axis 4 verified against shipped code; the plan's
reading is **correct** and needs no card.

1. **The pre-check sees the valuation.**
   `auto_commit_item_cost_evaluation_in_session`
   (`commit_item_cost_evaluation.py:423-456`) re-reads the current valuation from
   the session at `:439` (`_load_current_valuation`); the chain writer flushes at
   `_common.py:159`. A write placed before `create_task.py:307` is visible. ✔
2. **Savepoint rollback leaves the valuation.** The savepoint opens at
   `create_task.py:309`, strictly after the write; `begin_nested()` rollback
   reverts only statements issued inside it. ✔
3. **C5-row-4 (auto path never mirrors) survives the inline birth — by
   construction.** The auto path calls the shared helper with **no** override
   kwargs (`:450-455`), so `effective.*` is copied from the valuation
   (`:215-227`) and `expected_price`/`purchase_cost` are those same values
   (`:236-237`). The mirror predicate at `:347-350` fires only when
   `(expected_price, purchase_cost) != (valuation.expected_sale_price_minor,
   valuation.purchase_cost_minor)` — an equality that cannot fail on this path.
   With inline birth the inputs ARE the valuation's, so the identity is preserved
   rather than newly relied upon. ✔
4. **Effect set of the birth write matches the PUT path.** `set_item_valuation`
   (`set_item_valuation.py:71-84`) does exactly: chain write + `audit(ctx,
   "item_valuation.created", "item_valuation", valuation.client_id)`. No history
   record, no workspace event, no preview persistence. The plan's task 2 lists
   precisely these — complete, and nothing extra (P-AB companion clause: verified
   by reading the call site, not by modelling it). ✔

**One caveat on the C1 no-mirror row.** Asserted as-is it is a "nothing changed"
row, which P-J's fifth extension (phase-8 re-review-r2 L3) requires be proven
non-vacuous. Pair it with a companion row on the explicit commit path where an
override **does** mirror, so the assertion is shown capable of failing.

---

## L10 — M — two intention statements now contradict R18-1 (route upstream)

Home-artifact rule: these are intention edits, not plan patches.

1. **§4.7A** (`planning/intention.md:487-488`): *"Writers: the specialized
   valuation command (§11), the §7.2 mirror step, and the §10.2 data migration."*
   §7B.6 adds `create_task` as a **fourth** writer of `item_valuations`. A closed
   writer list that is silently incomplete is exactly the kind of sentence a later
   phase reasons from.
2. **§11A.5(c)** (`:1886-1887`): *"(Task/item creation remains money-free per
   R1-3/§10.2 — the valuation endpoint is the only money surface.)"* R18-1 reverses
   this directly, and §11A.5 is a **cited semantic authority for this very phase**.

Both as lettered amendments; do not renumber (charter, §7A precedent).

---

## L11 — M — proposed refusal identity (4B N-c pattern; contingent on card 1)

For §6.4, contingent on branch **A** or **B**:

- **`ITEM_COST_INLINE_PRICE_ON_EXISTING_ITEM`** — raised as `ValidationError`
  (§6.4's default carrier), message format `<IDENTITY>: <human sentence>`, the
  sentence naming the matched item's `client_id` and pointing at the valuation
  endpoint as the price-change surface. Single-path (application pre-check only —
  no DB arbiter exists, so P-S's reachability judgment is: **DB path unreachable,
  satisfied by the pre-check row plus this note**, never by an invented fixture).

Register before use. Under branch **C** no identity is needed and this row is
withdrawn.

---

## L12 — L — the plan's archgraph note names a node that does not exist

Plan Notes: *"delta = the reads/writes this adds to `command-task-create`"*.
Verified read-only this session: `archgraph_status` → 173 nodes / 256 edges,
revision `45b721965a17…`, 0 stale, 0 pending. **There is no `command-task-create`
node**, and no node for `create_task` under any id — `archgraph_get_node` returns
`NODE_NOT_FOUND`, and a `command`-typed search over "task" returns 14 nodes, none
of them `create_task`.

The phase-7 auto path is recorded only inside
`command-item-economics-commit-item-cost-evaluation`, whose evidence span is
`_commit_item_cost_evaluation_in_session:187-393` — it does not reach
`create_task.py` at all.

So 8B's delta is a **new node plus edges** (or a new evidence span on an existing
node), not a delta to an existing one. Amend the Notes to say which, so the
implementer does not improvise a node id at closeout.

---

## L13 — L — citation corrections (verified against the tree)

| plan/authority says | actual |
|---|---|
| `FindOrCreateItemInput` :25-50 | class at **:27**, validator ends :50 |
| `create_task.py` savepoint at :311-ff | `try` at **:308**, `begin_nested()` at **:309**, block ends **:324** |
| §10A.3: `tasks/requests/__init__.py:36-38` | **:37-39** |
| §6.5: chain writer "currently inline at `set_item_valuation.py:128-159`" | already extracted (phase 7) — `_common.py:117-169`; historical note, no action |

Also **verified as claimed**: `ItemValuationRequest` at `:116-121` ✔; **no new
files needed** (both target files exist) ✔; **no migration needed** — `ItemValuation`
and its CHECK/index already ship, head migration `c1d2e3f4a5b6_add_process_item_
cost_result_task_type.py` present on disk ✔.

---

## L14 — L — README: the route is PUT, and the table is already drifted (scope fence)

`routers/README.md` has **no `POST /api/v1/tasks` section** — task creation is
documented at **`### PUT /api/v1/tasks`** (`:2627`, operationId
`route_create_task_api_v1_tasks_put`). The plan's "task-creation body mirror row"
lands there.

Its body table is stale independently of 8B. Against `_CreateTaskBody`/
`_TaskItemInputBody` (`tasks.py:95-201`) it is missing `item.item_zone`,
`item.can_have_upholstery`, `notes[].plain_text`, `notes[].users_read_list`,
`steps[].ready_by_at` and the whole `shopify_preorder` block; and its six
`item_issues[]` rows (`issue_severity_id`, `base_time_seconds`, `time_multiplier`,
`issue_name_snapshot`, `severity_name_snapshot`, …) name fields
`_TaskItemIssueBody` (`:117-126`) does not have.

The absent legacy money rows are **not** drift — phase 6 removed them deliberately
(`b940309`, 12 deletions) while D6 retains the keys in the router bodies.

Despite the "*Autogenerated from FastAPI OpenAPI*" banner there is **no generator
in-tree** (no script, no Makefile target; phases 4–8 each hand-edited the file).
So this is a hand edit, and the implementer must **not** attempt a regeneration —
it would sweep unrelated drift into 8B's write perimeter.

**Fence:** 8B adds its three `item.*` rows under `PUT /api/v1/tasks` and touches
nothing else. The pre-existing drift routes to intention §2.6 and phase 9's
changed-endpoints deliverable (R18-2).

---

## L15 — L — `quantity` does not participate in economics (delegate: no logic)

Verified: zero occurrences of `quantity` under `domain/item_economics/`,
`services/commands/item_economics/` and `services/queries/item_economics/`. A
valuation is per-**item** and quantity-agnostic (§4.7A) — an item with
`quantity: 5` and `purchase_cost_minor: 1000` records 1000, not 5000, and no
budget arithmetic multiplies by it.

8B changes nothing here and the implementer writes no quantity logic. Whether a
manager reads the field as per-unit is a **frontend-handoff sentence** (phase 9 /
R18-2), not an 8B mechanism. Recorded so the question is answered once.

---

## L16 — L — multi-item is moot for 8B (verified, no criterion needed)

`CreateTaskRequest.item` is a single optional `FindOrCreateItemInput`
(`tasks/requests/__init__.py:226`) — not a list — and its TaskItem is always
`TaskItemRoleEnum.PRIMARY` (`create_task.py:298-304`). Additional items arrive only
through `add_item_to_task`, which 8B does not touch. So "which item(s) may carry
the trio" has exactly one answer by construction: the one item the payload can
carry, always PRIMARY. Recorded so the reviewer does not re-derive it and so no
speculative multi-item criterion is written.

---

## L17 — L — a phase-6 structural test constrains `create_task.py`'s source text

`tests/unit/test_phase6_api_bridge.py:87-97` asserts the literal strings
`item_value_minor`, `item_cost_minor` and `item_currency` appear **nowhere** in
`create_task.py`'s source. The new field is `currency`, so the test stays green —
but an implementer who names a local variable `item_currency` reddens a phase-6
guard for no reason. One line in the plan's Notes.

---

## L18 — L — the response carries no signal that the task was priced

`create_task` returns `{client_id, task_scalar_id, item_id, item_sku}`
(`create_task.py:527-532`). After 8B, a caller who priced a task inline cannot tell
from the response whether the auto-commit fired — they must call
`GET /tasks/<id>/budget-status`. The plan's "no new read surface" is the right
call for 8B; recorded so R18-2's frontend handoff documents the two-call flow
rather than leaving the frontend to discover it.

---

## Live measurements (this session)

- **Collection:** `PYTHONPATH=. pytest --collect-only -q` from `backend/app/` →
  **2162 tests collected in 1.58s** — matches master plan §10's "2161 selected
  (2162 collected)". Database reachable; no connection noise.
- **Head:** `git log -1` → `fe06dfa`, working tree **clean**. Migration
  `c1d2e3f4a5b6_add_process_item_cost_result_task_type.py` present in
  `migrations/versions/`.
- **Architecture graph:** `archgraph_status` → initialized, valid, **173 nodes /
  256 edges**, revision `45b721965a174fdf2e506bdb847ea26a496f803c7eb182fb6d6f0f598f3815a4`,
  **0 stale, 0 pending**, no diagnostics. Matches the prompt's stated ground.
- **Full suite NOT run.** The projection role is read-only and time-boxed, and the
  2138/23/1 baseline is already verified by three independent sessions (§10). No
  baseline claim is made or amended by this session.

---

## Write perimeter (full, declared)

**Documents written — one file, this handoff:**
- `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-15_phase8b_projection_r0_handoff.md`

**Code:** none. **Plans / intention / master plan:** none — every correction above
is *proposed*, none applied (plan-projection doctrine: report, never fix).

**Tool-recorded state (archgraph): ZERO DELTA.** Read-only calls only —
`archgraph_status` ×1, `archgraph_search_nodes` ×5, `archgraph_get_node` ×2. No
`apply_changes`, no review decisions, no maintenance. Revision unchanged at
`45b72196…`, 0 pending, 0 stale — verify by re-running `archgraph_status`.

**Mutation probes: NONE DECLARED AND NONE RUN.** No test was executed beyond
`--collect-only`; no source file was edited, so no probe could be left behind. Any
fresh mtime under `app/` is not this session's.

---

## Exit gate

**Verdict: AMENDMENTS_REQUIRED.** Eighteen ledger rows; five blocking (L1–L5), six
to amend before compiling (L6–L8, L10, L11 + L6's harness), and one owner card.
The implementer prompt compiles when every row is routed **and** card 1 is
answered — L4's and L11's rows cannot be written until it is.

Non-empty ledger: the projection gate does **not** self-retire on this phase
(charter — two consecutive empty ledgers required).

## Appendix — non-authoritative

No skeleton is attached. The per-file sketches produced while projecting were
discarded deliberately: anything the implementer needs is either already in the
plan or is one of the amendments above, and shipping a sketch would make this
session a second planner.
