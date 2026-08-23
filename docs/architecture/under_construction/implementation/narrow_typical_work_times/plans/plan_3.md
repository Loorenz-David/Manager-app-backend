# Plan 3 — `TaskBudgetStatus` carries the derived spec

```
plan: plan_3
project: narrow_typical_work_times
state: CHANGES_REQUESTED
projection_gate: MANDATORY
```

## 1. Goal

Stop discarding the active PRIMARY `Item` that `_load_task_and_item` already loads: carry
the **derived spec** on `TaskBudgetStatus`, additively, across **all five** construction
surfaces — including the WORKER/SELLER face this pipeline's own §6.2 table never names.

**Explicitly NOT in this phase:** **no payload change on any surface.** No serializer
publishes the new field. `golden_budget_status.json`, `golden_production_time.json` and
`golden_budget_allocations.json` are all unchanged. No consumer *uses* the spec yet — plan 4
is the first reader. No statement call changes. No change to `divide_production_budget` or to
`ALLOCATION_METHOD`.

## 2. Read first

- Master plan §§4, 6.2, 7, 9, 10.
- Intention **header**, then §2.2 F-A (**stale — see §2B S-1/S-2/S-3**), §2B S-1, S-2, S-3,
  §3.2, §6.2 row 1, **§6A** in full, §7 (the always-present rule).
- **Intention §3A C3, and `plans/plan_2.md` §6 C11's named conversion trigger** (phase-2
  review N3). C11 holds `coalesce(<conjunction>, FALSE)` structurally today because no
  fixture can separate it from three-valued logic. **It converts into a real behavioural
  criterion the first time any predicate negates the item match** — a `NOT item_match`, an
  `is_(False)` on it, or an `ANSWER_AS_ASKED` complement query. **If this phase writes one,
  the criterion is yours to add.** The trigger was well stated and routed to nobody, which
  is why it is now in a Read-first list.
- **Intention §4A K2-a** — the shipped `K ≥ 1` column order is the reverse of K2's prose.
  **Read the statement's result by column name, never by position** (phase-2 review S4).
- `planning/owner_decisions.md` — D9, D11, **D27**.
- Gate handoff §2 row 12 and §3 (S-1, S-2, S-3).
- Code, read at source: `get_task_budget_status.py` (the whole file — `TaskBudgetStatus`,
  `_load_task_and_item`, `_empty_status`, `_build_evaluated_status`, and every call site of
  the two helpers); `get_task_budget_status_worker.py` (the whole file, 53 lines);
  `routers/api_v1/item_economics.py` (the manager-vs-worker face selector);
  `domain/item_economics/serializers.py` (the budget-status serializers — read to confirm
  they are **not** touched).

## 3. Dependencies

**Gate: plan 2 `APPROVED`.** This phase imports `TypicalFilterSpec` and
`derive_spec_from_primary_item` from plan 1; it does not depend on plan 2's SQL, but the
serial gate holds (master plan §7).

## 4. Files expected to change

**Modified**
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py`

**New**
- `app/tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py`

Anything else is a finding — in particular any serializer, any golden, and
`get_task_production_time.py` / `get_task_price_scenario.py` / `get_task_budget_allocations.py`.

## 5. Ordered tasks

1. **Re-read `TaskBudgetStatus` at source and write down its field list before editing.**
   §6A A1 says "13 fields"; measured 2026-08-22 it carries **14**
   (`get_task_budget_status.py:38-51`), the fourteenth being `result: ItemCostResult | None`
   added by the live-clock pipeline. The contract (additive only, appended last, with a
   default) is unaffected by the count; the count is a documentation defect reported
   upstream, not a licence to reason from the number.
2. **A1 — additive only.** Add exactly one field, **appended last, with a default**:
   `typical_filter_spec: TypicalFilterSpec | None = None`. No existing field's name, type,
   order or value changes. `_empty_status`'s and `_build_evaluated_status`'s existing outputs
   are untouched. **The budget-status serializer is untouched.**
3. **A2 — carry the derived spec, not the `Item`.** Compute it once with
   `derive_spec_from_primary_item` at the load site. Do **not** put the ORM `Item` on a
   read-model dataclass that crosses three services, and do not leave each consumer to
   re-derive — that is the fork HC-1 exists to prevent, one layer up.
4. **A3 — which item derives it.** The **active PRIMARY `Item` loaded by
   `_load_task_and_item`**, never `evaluation.item_id`. The spec describes "work comparable
   to the task at hand"; the evaluation's item is a historical binding.
   **Recorded consequence, so it is not later "fixed":** on a `mismatched` task,
   `typical_resolution.applied_filter` (plan 4) will describe the **current primary** item
   while `item_id` names the **evaluated** one. That combination is C4 below, and it is
   correct.
5. **A4 — resolve the `None` ambiguity rather than record its expiry.** §6A A4 offers two
   branches; this plan takes the first: **pass the item through at all four `_empty_status`
   call sites** — `get_task_budget_status.py:121, :132` and
   `get_task_budget_status_worker.py` (both of its `_empty_status` calls). After this,
   `typical_filter_spec is None` means **"no active primary item"** and
   `TypicalFilterSpec()` means **"a primary item with no `item_category_id`"**, and the two
   stop being indistinguishable.
   *Why the stronger branch:* in V1 both collapse to `TypicalFilterSpec()` and the ambiguity
   is harmless, but it stops being harmless the moment `COMPARABILITY_PROFILE` v2 adds a
   non-category axis — the exact silent-policy drift D11 exists to prevent. Four argument
   passes now removes an expiry the v2 return path would otherwise inherit as an obligation.
   Verify the call-site list at source before editing; §6A's line numbers are from
   2026-08-22 and this document's lineage has watched line numbers drift twice.
6. **A5 — the worker face is a row of §6.2's table.** `get_task_budget_status_worker`
   gains the field through the shared helpers and **must not publish it**. Its own comment —
   *"must not inherit a future manager change"* — is the standing instruction, and this is a
   manager change. §6.2's table is **six** rows and the worker is the **seventh surface** —
   that is how the intention's §6.2 header and §6A A5 both put it. *(Plan 3 originally
   compressed this into "the table is seven rows", which is false; corrected per projection
   reality check 18. Do not use it as a checklist.)*
7. Tests per §6. Update the tracker row and the Review log.

## 6. Tests / acceptance criteria

Hypothesis scope: L1 = `test_budget_status_filter_spec.py`. C2 and C6 name cross-file bite
sets (the goldens and three consumer suites) and run at L2 =
`tests/integration/services/queries/item_economics/`.

**C1 — additive, appended last, defaulted.**
Assert `[f.name for f in fields(TaskBudgetStatus)]` equals the exact fourteen existing names
in order, **followed by** `"typical_filter_spec"`; and that the field's default is `None`
(constructing `TaskBudgetStatus` without it succeeds).
*Mutation* — `get_task_budget_status.TaskBudgetStatus` (definition): insert the new field
before `result`.
*Both sides* — contract: index 13 is `"result"` and index 14 is `"typical_filter_spec"`;
mutation: index 13 is `"typical_filter_spec"`. Exact list literal, not a length check.
*Defect caught*: positional construction anywhere in the lineage silently rebinding two
fields. This is a shipped cross-pipeline dataclass with two construction helpers and five
construction surfaces.

**C2 — no payload moves, on any of the four surfaces.**
(a) `golden_budget_status.json` is byte-identical — the existing golden test is green with
**no edit to the golden**.
(b) The serialized **manager** budget-status payload's key set contains none of
`"typical_filter_spec"`, `"item_category_ids"`, `"major_categories"`, `"designers"`,
`"width_cm"`, `"height_cm"`, `"depth_cm"`, `"can_have_upholstery"`.
(c) `golden_production_time.json` and `golden_budget_allocations.json` are byte-identical.
*Mutation* — `domain/item_economics/serializers.py` (definition): add the field to the
budget-status serializer.
*Both sides* — contract (a): golden test green; mutation: red with one added key.
Row (b) also bites on the mutation; row (c) does **not** — recorded per rule 12, and row (c)
bites instead on "publish the spec from `serialize_task_production_time`".

**C3 — the worker face gains the field and does not publish it.**
(a) `get_task_budget_status_worker` returns a `TaskBudgetStatus` whose `typical_filter_spec`
equals `TypicalFilterSpec(item_category_ids=frozenset({chair_id}))` for a chair task.
(b) The worker route's serialized payload key set is **unchanged** — asserted as an exact
frozenset literal, not as a subset check.
*Mutation* — the worker serializer (call site): publish the field.
*Both sides* — contract (b): the exact existing key set; mutation: that set plus one key.
*Defect caught*: the money-redacted face inheriting a manager change — the failure its own
comment was written to prevent.

**C4 — A3: the spec derives from the loaded primary item, never from the evaluation's item.**
Fixture: a **`mismatched`** task — a committed evaluation bound to item **X** (category
`table`), and an active PRIMARY `TaskItem` pointing at item **Y** (category `chair`), with
`item_binding == "mismatched"`.
Assert, on both the manager and the worker face:
`status.item_binding == "mismatched"`; `status.item_id == X.client_id` (**unchanged
behaviour**); `status.typical_filter_spec == TypicalFilterSpec(item_category_ids=frozenset({Y.item_category_id}))`.
*Mutation* — `_build_evaluated_status` (call site): derive the spec from `evaluation.item_id`
instead of from the loaded `item`.
*Both sides* — contract: the spec names **Y's** category (`chair`); mutation: it names
**X's** (`table`). Exact frozenset literals.
*Defect caught*: the whole task's narrowing population silently drawn from a historical
binding — §2B S-2, which the intention never resolved until §6A A3.

**C5 — A4: `None` vs `TypicalFilterSpec()` are distinguishable, at all four `_empty_status`
call sites.** One row per call site (the blanket-claim rule: a "these four are handled
together" claim needs one probe per member).
| # | surface | task shape | expected |
|---|---|---|---|
| a | manager, `NOT_EVALUATED` (no item) | no active primary item | `typical_filter_spec is None` |
| b | manager, no evaluation, item present | primary item with `item_category_id IS NULL` | `== TypicalFilterSpec()` |
| c | worker, `NOT_EVALUATED` (no item) | no active primary item | `is None` |
| d | worker, no evaluation, item present | primary item with `item_category_id IS NULL` | `== TypicalFilterSpec()` |
Plus (e): manager, no evaluation, item **with** a category → the populated spec.
*Mutation* — `get_task_budget_status_worker.py` (call site): stop passing the item at the
second `_empty_status` call.
*Both sides* — contract row (d): `TypicalFilterSpec()`; mutation: `None`. Rows (a)–(c) do not
bite on that call site — recorded, and each has its own call-site mutation of the same shape.
*Defect caught*: "no primary item" and "a primary item with no category" collapsing into one
value, which is harmless in V1 and is silent policy drift at `COMPARABILITY_PROFILE` v2.

**C6 — the three consumer suites are green with no edits.**
`test_production_time_query.py`, `test_budget_allocations_query.py`,
`test_price_scenario_query.py` and `test_live_clock_goldens.py` pass unchanged.
*Mutation* — `get_task_budget_status.py` (definition): change `item_id`'s value on the
evaluated path from `evaluation.item_id` to `item.client_id`.
*Both sides* — contract: `test_price_scenario_query.py`'s binding rows green; mutation: the
`mismatched` binding rows go red, because `item_id` and the binding label stop agreeing.
*Defect caught*: the tempting "while I am in here, make `item_id` consistent with the spec"
edit. A3 says the two deliberately differ.

---

### C-N1 — the "one active primary item per task" rule is guarded, at both layers

**Carried here by owner ruling D27** (phase-2 review card 1). This rule is what makes the
whole pipeline's `TaskItem` join fan-out-free — plan 2 §2's central claim rests on it — and
the phase-2 review confirmed it is **enforced twice and tested zero times**. This is the
phase that buys the rows, because it is where the first real surface reads the narrowed
number.

**Two rows, not one — the two layers fail independently:**

**(a) The database backstop.** Insert a second `TaskItem` with `role = PRIMARY` and
`removed_at IS NULL` on the same `(workspace_id, task_id)` as an existing active primary →
`IntegrityError`. The index is `uix_task_items_primary_active` on
`(workspace_id, task_id) WHERE role = 'primary' AND removed_at IS NULL`
(`models/tables/tasks/task_item.py:52-58` — the `Index(` call; the projection
corrected plan 3's `:53`, and intention F-B's citation was the accurate one).
*Mutation*: drop the index in the test's transaction (or assert against
`pg_indexes` that it exists **with its `WHERE` clause** — the partiality is the point: two
*removed* primaries, and a primary plus a *related* item, must both remain legal).
*Both sides* — contract: `IntegrityError` on the second active primary, **and** the two
legal shapes insert cleanly; mutation: the second active primary inserts.

**(b) The application guard.** `add_item_to_task` with a second primary raises
`ConflictError("Task already has an active primary item.")`
(`add_item_to_task.py:47-57`). **No test file in the repository references
`add_item_to_task` at all** — measured by the phase-2 reviewer, and the message appears
only in production code.
*Mutation*: delete the pre-check → the call reaches the database and raises `IntegrityError`
instead, or succeeds if (a)'s index is also gone.
*Both sides* — contract: `ConflictError` with that message; mutation: a different exception
type. **Pin the message, not just the type** (phase-2 review S3's rule: a `match=` is an
assertion and gets the same enumeration discipline as any other).

**⚠ Undetermined, and the projection owes an answer (re-review N-c).** Row (a) asserts an
`IntegrityError` **and** two clean inserts in the same criterion. On a session that has just
raised `IntegrityError`, PostgreSQL **aborts the transaction** and every later statement
fails until a rollback or a savepoint. This criterion does not say whether the legal shapes
are inserted **before** the violating one, or inside a nested savepoint. **Get it wrong and
the row either fails for the wrong reason or swallows its own evidence** — a green row that
proves nothing, which is the class this project has now paid for six times. Settle it on
paper in the projection round; it costs one sentence there and a debugging session here.

*Defect caught*: if a future migration or refactor quietly drops either guard, a task with
two active primaries is **counted twice**, the section's typical drifts upward, and nothing
errors anywhere — the business starts quoting longer jobs than its own history supports.
D27 records why deferring from phase 2 was safe: the reviewer read the index out of the
live migrated database and it is present and correct **today**. That is a measurement with
a shelf life, which is exactly what a test replaces.

### §6A. Projection fold — corrections (2026-08-23)

The plan-3 projection (`AMENDMENTS_REQUIRED`, 15 rows / **8 blocking** / 0 owner cards)
found the **production tasks executable as written** and **a third of the test evidence not
executable**: four of eight named mutations either point at code that does not exist or
would fire without catching what their criterion was written to catch. It measured each
against the real code instead of reading the prose.

**§6A wins over §5 and §6 wherever they differ.** The coordinator verified the four
load-bearing claims independently at source before folding (L1, L4, L5, L6(ii) — all four
confirmed).

#### Tasks — three corrections before any criterion

**T-L1 (blocking) — passing the item is necessary and NOT sufficient.**
`derive_spec_from_primary_item(None)` returns **`TypicalFilterSpec()`, not `None`**
(`typical_filters.py:71-75`: `getattr(item, "item_category_id", None)` → `None` → empty
spec). That is plan 1's shipped contract, and it collapses **exactly the two cases C5 exists
to separate**. An implementer who reads task A4 literally — pass the item, call the derive
function — gets `TypicalFilterSpec()` on the no-item path and rows (a)/(c) fail while the
plan, the intention and the helper all appear to agree.
**The value carried is `None if item is None else derive_spec_from_primary_item(item)`,
computed at the load site.** `derive_spec_from_primary_item` is **not changed** — "fixing"
it to return `None` for `None` silently breaks a shipped contract and is forbidden by §6.1's
fold rule.

**T-L2 (blocking) — the helper signature is declared here, not left to the implementer.**
`_empty_status(status, *, binding, item_id, typical_filter_spec: TypicalFilterSpec | None)`
and the same **required keyword-only** parameter on `_build_evaluated_status`. **No
default** — fail-closed (charter rule 11), so a future fifth call site cannot silently drop
it; the default lives on the dataclass per C1 and nowhere else.

**T-L8 (blocking) — the branch that would not close green is closed now.**
§5 A2's "computed once at the load site" has a reading — *inside `_load_task_and_item`,
returning a 3-tuple* — that breaks `get_task_price_scenario.py:196` (a file §4 puts **out of
perimeter**) and `test_price_scenario_query.py`'s `fake_task_and_item` (`:562-563`), both C6
files. **`_load_task_and_item` keeps its 2-tuple return**; the spec is computed in
`get_task_budget_status` and `get_task_budget_status_worker`, immediately after that call.

#### Criteria

| # | Correction |
|---|---|
| **C1** | Supply the literal (L9) — the fourteen existing names in order, then the new one: `["status", "item_binding", "actual_worker_seconds", "actual_worker_minutes", "remaining_worker_minutes", "percent_consumed", "variance_worker_minutes", "production_budget_minor", "allowed_worker_minutes", "consumed_cost_minor", "variance_cost_minor", "evaluation_id", "item_id", "result", "typical_filter_spec"]`. State **0-based** for the index claim (L14): index 13 is `result`, 14 is `typical_filter_spec`. **Honesty note (L10):** both existing `TaskBudgetStatus(...)` constructions are **keyword**, so C1's "positional construction" hazard is a *future* risk, not a present one — say so rather than implying a live bug. |
| **C2** | **(a) and (c) are ONE observable with ONE bite** (L11): `test_live_clock_goldens.py:326-332` asserts all three goldens in a single loop that short-circuits at the first mismatch, so per-row attribution is impossible. Record them as one. Row **(b) becomes an exact 14-key frozenset**, not a disjointness check (L9; master plan §9 prefers the literal): `{"status", "item_binding", "actual_worker_seconds", "actual_worker_minutes", "remaining_worker_minutes", "percent_consumed", "variance_worker_minutes", "result", "production_budget_minor", "allowed_worker_minutes", "consumed_cost_minor", "variance_cost_minor", "evaluation_id", "item_id"}`. Row (c)'s alternative mutation site is **`division_serializers.py:112`** (`serialize_task_production_time`), *not* `serializers.py` — confirmed it would bite. |
| **C3** | **BLOCKING — the named mutation site does not exist** (L5). There is exactly **one** budget-status serializer, `serialize_task_budget_status(status, *, include_monetary)` (`serializers.py:231-276`), and the worker face is that same function called with `include_monetary=False` (`routers/api_v1/item_economics.py:146`). As written, C2's and C3's mutations are **the same edit**. The real distinction is **placement inside one function**: adding the key to the **shared `payload` dict** (`:245-262`) reaches **both** faces — *that is literally the "worker inherits a manager change" defect C3 exists to catch*, so it is **C3's mutation**, biting C2(a), C2(b) **and** C3(b); adding it inside `if include_monetary:` (`:263-273`) is **C2's mutation**, biting C2(a) and C2(b) only and leaving C3(b) green. Row (b)'s exact 9-key literal: `{"status", "item_binding", "actual_worker_seconds", "actual_worker_minutes", "remaining_worker_minutes", "percent_consumed", "variance_worker_minutes", "result", "allowed_worker_minutes"}`. **(b) asserts the service-level call** `serialize_task_budget_status(worker_status, include_monetary=False)` — the exact call the route makes — not the route (L12), since §4 puts the new file under `tests/integration/services/queries/`. |
| **C4** | **BLOCKING — the mutation reddens the row but cannot catch the defect** (L3). `derive_spec_from_primary_item` is duck-typed, so deriving "from `evaluation.item_id`" passes a **`str`**, which has no `item_category_id`, and yields `TypicalFilterSpec()` — **not X's category**. The plan's stated both-sides is measurably false, and the mutant's red is indistinguishable from "the spec was never derived at all". **The mutation must produce an `Item`, not an id:** re-load `Item` by `evaluation.item_id` and derive from **that ORM instance**. Both sides — contract `frozenset({Y.item_category_id})` (`chair`); mutation `frozenset({X.item_category_id})` (`table`). **C4 also inherits C6's item_id-consistency mutation** (see C6). |
| **C5** | **BLOCKING ×2.** See **T-L1** for the value expression — without it the criterion is unsatisfiable. And restate the mutation as a **value** mutation, well-defined under T-L2's no-default signature (L2): *`get_task_budget_status_worker.py:48` (call site): pass `typical_filter_spec=None`* → contract row (d) `TypicalFilterSpec()`, mutation `None`. *(The plan's "stop passing the item" wording becomes a `TypeError` under a required parameter, which is not the stated both-sides.)* Rows (a)–(c) still need **one call-site mutation each** — write them out; "each has its own of the same shape" is a blanket claim, and master plan §9 makes the ledger checkable against the count. |
| **C6** | **BLOCKING — the mutation reddens nothing in its declared scope** (L4), measured twice: `test_price_scenario_query.py::_run_scenario` **monkeypatches `get_task_budget_status` away** (`:559-560`, installed `:574`), so the `mismatched` rows never execute the mutated function and assert `item_binding` but **never `item_id`** — repo-wide, no consumer suite asserts it; and both `golden_budget_status.json` tasks are `item_binding: "bound"` with `item_id` equal to the loaded primary, so the edit leaves all three goldens byte-identical. **(i) Move the item_id-consistency mutation to C4**, whose `mismatched` fixture can see it, and record C4 as its bite. **(ii) Give C6 a mutation its own files can see:** *add the field **without** a default* → the two keyword `TaskBudgetStatus(...)` constructions at `tests/unit/routers/api_v1/test_item_economics_router.py:70` and `:208` break. **(iii)** C6 says "the **three** consumer suites" and names **four** — fix the count (rule 2), and **name the router test file**, which sits outside the declared L2 root and is a real consumer. |
| **C-N1(a)** | **BLOCKING ×3** (L6). **(i) Insert order, settled — this is what N-c/D27 owed.** `db_session` (`tests/conftest.py:107-110`) rolls back at teardown and the test never commits, so charter rule 11½ needs no explicit DELETE — **say so**, or a later round adds a teardown that cannot run on an aborted transaction. Seed the workspace/task/items/first active primary **and both legal shapes first**, flushing each; the **violating insert is last, inside a savepoint**: `with pytest.raises(IntegrityError): async with db_session.begin_nested(): db_session.add(second_active_primary); await db_session.flush()`. **(ii) The fixture defect that would have made the row green under its own mutation.** `task_items` carries a **second** partial unique index — `uix_task_items_active` on `(workspace_id, task_id, item_id) WHERE removed_at IS NULL` (`task_item.py:44-51`) — so if the second active PRIMARY reuses the first's `item_id`, the `IntegrityError` comes from the **wrong index** and dropping `uix_task_items_primary_active` leaves the row **green**. **The second active primary must name a different item**, and so must both legal shapes; the two *removed* primaries are exempt from both indexes. **(iii)** Rule 12: three sub-checks, one mutation. Add *recreate `uix_task_items_primary_active` **without** its `WHERE`* → both legal inserts fail and nothing else does. And the `pg_indexes` check is an **alternative assertion**, not a mutation — the plan offers it as one. |
| **C-N1(b)** | **BLOCKING — the both-sides is false as written** (L7). `add_item_to_task` carries a **second** pre-check at `:59-68` raising `ConflictError("Item already active on this task.")`, so on a same-item fixture deleting the primary pre-check lands on that one: **same exception type**, different message. The row still reddens — but only because the criterion pins the message (S3's rule, correctly carried). **State the fixture requirement** (different item, per C-N1(a)(ii)) and restate: *mutation: `ConflictError` → `IntegrityError`; and if the fixture reuses the item, `ConflictError` with the **other** message — which is why the message is pinned.* *(Refuted while checking: the row needs **no Redis** — the `ConflictError` path returns before `event_bus.dispatch` (`:94`); and `maybe_begin` runs in **subordinate** mode once the seed is flushed, so the raise leaves the session clean.)* |

#### Refuted — recorded because a refutation is a result

- **"`_empty_status` cannot tell the two cases apart"** — **refuted and re-aimed.** The call
  sites already carry the information (`:121`/`:38` are the `item is None` branch; `:132`/`:48`
  hold a live `Item`). The blocker is one layer down, in the helper (T-L1). **This matters:
  the fix is a two-token expression at the load site, and "fix the helper" is the wrong
  repair.**
- **C4's `mismatched` fixture is cheap to build** — "a **committed** evaluation" means
  `kind = COMMITTED`, **not** a database commit. `test_live_clock_goldens.py::_seed_golden_fixture`
  is a working template, and `_load_preview_inputs` degrades gracefully on empty cost
  configuration, so C5's rows (b)/(d)/(e) need no economics seeding. The only additions are
  two `ItemCategory` rows.
- **The worker face is better covered than the plan claims** — `golden_budget_status.json`
  already contains the **worker** payload byte-exactly (`test_live_clock_goldens.py:305-309`).
  What is wrong on that face is the *count* and the *mutation site*, not the coverage.
- **"Five construction surfaces" counts to nothing** (reality check 19). Measured: 2
  production construction sites, 4 `_empty_status` call sites, 6 helper call sites, 2 test
  constructions. The phrase is inherited from §6A and harmless — the tasks work off the
  measured call sites — **but it is not a checklist and must not be used as one.**

---

### §6B. Coordinator consumption fold — corrections to §6A (2026-08-23)

**§6B wins over §6A wherever they differ.** The implementation is **correct and complete**:
the production diff is exactly what §6A prescribed (`None if item is None else
derive_spec_from_primary_item(item)` at both load sites, 2-tuple `_load_task_and_item`,
required keyword-only carrier with no default, `item_id=evaluation.item_id` preserved,
`typical_filters.py` untouched). **No production change is required by this fold.** Every
correction below is to the *evidence* — and two of them are corrections to §6A itself.

#### The structural finding — a content-blind double encodes the query count

`_ScalarSession` (`test_budget_status_filter_spec.py:41-51`) is a **content-blind iterator**:
`scalar()` returns the next value in a list regardless of what was asked for. Its length
therefore encodes **the expected number of queries**. Any mutation that adds or removes a
query exhausts it and raises `RuntimeError: coroutine raised StopIteration` — a red that is
**indistinguishable from the semantic failure the criterion is asserting**, and that
splashes onto unrelated rows.

This is the **second-sufficient-cause** family that C-N1(a)(ii) belongs to, one layer over:
there the fixture satisfied two causes, here the *double* does.

**C4-a (blocking, and this corrects §6A) — the prescribed mutation cannot run.**
§6A C4 prescribed "re-load `Item` by `evaluation.item_id` and derive from that ORM instance"
with both-sides `frozenset({"cat_chair"})` → `frozenset({"cat_table"})`. **Measured by the
coordinator, that mutation does not produce that observable.** The reload consumes the fake
session's second value, so the run yields:

```
FAILED test_C4_manager_uses_loaded_primary_item_not_evaluation_item
  RuntimeError: coroutine raised StopIteration      # not "got cat_table"
+ 3 C5 rows red as collateral (C5-a, C5-b, C5-e)    # fixture exhaustion, not semantics
```

§6A went one step — *the mutation must produce an `Item`, not an id* — and not the second:
**the fixture must be able to supply that `Item`.** A content-blind double never can.
The ledger row claiming "both observed X/table instead of Y/chair" is therefore **not
reproducible** and must be withdrawn.

**The replacement, measured green-to-red by the coordinator.** Keep the query count
unchanged and change only the *source*: move the derivation below the evaluation load and
derive from `evaluation` itself. Result — **2 failed / 11 passed**, the C4 row failing on
its own assertion, cleanly:

```
FAILED test_C4_manager_uses_loaded_primary_item_not_evaluation_item     # assertion
FAILED test_C5_...[C5-e-manager-categorized-primary]                    # assertion
```

**Say plainly what C4 proves.** Against a content-blind double, C4 can demonstrate *"the
carrier stopped coming from the loaded PRIMARY item"* — it **cannot** demonstrate *"it came
from the evaluated item specifically"*, because no mutation can make the double return a
different `Item`. Record the narrower claim rather than the wider one.

**C1-a (should-fix, and this also corrects §6A) — C1's mutation names no failing test.**
"Move the defaulted field before non-default `result`" is rejected by Python **at class
creation**: `TypeError: non-default argument 'result' follows default argument`. It is a
**collection** error, so it names no failing test id — which §6A's own evidence budget
requires ("the id, not 'the file reddened'"). It is also unfalsifiable as a criterion probe:
`result` is the last non-default field, so the language, not the test, forbids the position.

**C1's ordering assertion is nonetheless armed** — the coordinator measured it. Swap two
*existing* fields (`evaluation_id` / `item_id`), which is legal Python and leaves every
keyword construction working:

```
FAILED test_C1_task_budget_status_appends_defaulted_spec_after_result
  At index 11 diff: 'item_id' != 'evaluation_id'     # 1 failed, 12 passed
```

**That is C1's mutation.** The old one demonstrated Python's grammar, not the criterion.

**C-N1(a)-a (minor) — the no-`WHERE` row names no test id.** "Legal shapes failed at their
legal flush" is a description, not an id. State it.

#### Refuted by the coordinator — recorded because a refutation is a result

- **C3's worker key-set assertion bites on the assertion, not on a crash.** The ledger's
  parenthetical ("the worker path also encountered JSON serialization of the leaked spec
  object") reads as though the worker row might be red for the wrong reason. Measured: under
  the shared-`payload` mutation **both** key-set tests fail on the frozenset comparison —
  `Extra items in the left set: 'typical_filter_spec'` — and the `TypeError: Object of type
  TypicalFilterSpec is not JSON serializable` is confined to the **golden** test, a
  different row. **C3 is sound as recorded**; only the prose is ambiguous.
- **`asyncio_mode = auto`** (`app/pytest.ini:7`), so the three `@pytest.mark.integration`
  tests that carry no `@pytest.mark.asyncio` **do** run. The inconsistent marking is
  cosmetic, not a silent skip.
- **C-N1(a) avoided its own trap.** The five seeded items are distinct, so the violating
  insert reuses no `item_id` and the `IntegrityError` comes from
  `uix_task_items_primary_active` and not from `uix_task_items_active`. §6A(ii) held.

#### Notes — no action

- **C5-b is inert against a wrong-source derivation.** Under the corrected C4 mutation it
  **passes**, because deriving from the wrong source yields `TypicalFilterSpec()` — exactly
  the value C5-b asserts. It remains armed against **its own** named hazard (pass `None` at
  the item-present call site), which is what it is for. Recorded so a later round does not
  mistake its green for wrong-source coverage.
- **`C5-e-manager-categorized-primary` earned its place.** The implementer added a fifth
  parametrize case the plan did not require, and it is the **only** C5 row that catches a
  wrong-source derivation. Keep it.

---

## 7. Notes

- **F-A is stale and is not a basis for reasoning.** Its "`TaskBudgetStatus` carries only
  `item_id` (`:47`)" was true of a smaller object; the dataclass now carries `result` and
  `item_id` sits at `:50`. Read the class, not the grounding.
- `_empty_status` has **four** call sites across two files, and `_build_evaluated_status`
  has two. The worker file imports both helpers directly
  (`get_task_budget_status_worker.py:9-14`), which is why a change to either reaches a
  surface no table in the intention names.
- This is a small phase deliberately. It is separated from plan 4 because it mutates a
  shipped cross-pipeline dataclass consumed by another pipeline's endpoint
  (`get_task_price_scenario.py:195`) and by a money-redacted face — a gate here contains that
  blast radius inside one boundary instead of inside plan 4's much larger one.
- No architecture-graph node is expected to change in this phase. **That is a claim to check
  against the graph, not to assert:** four "no delta" claims in the neighbouring pipeline
  were wrong, and only the review-item timestamps showed it.

## 8. Review log

### 2026-08-23 — implementer round 1 (Codex)

- **Outcome:** implemented the additive `typical_filter_spec` carrier on `TaskBudgetStatus`, deriving it from the loaded active PRIMARY item in both manager and worker services. The worker continues to share the helper while retaining its own redacted serializer boundary; no serializer, route, consumer, or golden payload was changed.
- **Task 0 / red baseline:** transcribed the §6/§6A contract into `app/tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py`. Before implementation the new file collected and ran with **9 failed / 4 passed**; failures were the expected missing-field/attribute contract failures with no import or fixture failures.
- **Judgment calls recorded:** `_load_task_and_item` remains a two-tuple; derivation is immediately after each load with `None if item is None else derive_spec_from_primary_item(item)`; `_empty_status` and `_build_evaluated_status` receive required keyword-only carrier arguments; evaluated `item_id` remains `evaluation.item_id`; C-N1(a) seeds legal shapes before the violating insert, uses distinct item IDs, and isolates that insert in a savepoint; no graph node was added because the existing projection boundary and architecture meaning did not change.
- **Positive evidence:** the phase contract file passed **13 tests**; the integration/router command passed **124 tests** in the focused invocation; the full item-economics integration directory had **128 passed** before the final stamp; Redis returned `PONG`.
- **Mutation ledger:** every named §6A mutation was run against the base tree and reverted immediately. Each red result is recorded here so the reviewer can reproduce the bite:

  | Criterion | Mutation | Both-sides result / failing test ID |
  |---|---|---|
  | C1 | Move the defaulted field before non-default `result`. | Collection failed with dataclass `TypeError: non-default argument 'result' follows default argument`; C1 could not collect. |
  | C2 | Add `typical_filter_spec` inside the manager serializer's `include_monetary` mapping. | **3 failed / 125 passed** at L2: `test_C2_manager_budget_status_payload_has_the_existing_exact_key_set`, `test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical`, `test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files`. |
  | C2(c) | Publish the field from `division_serializers.serialize_task_production_time`. | **2 failed / 126 passed** at L2: `test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical`, `test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files`. |
  | C3 | Add the field to the shared serializer payload. | **4 failed / 124 passed** at L2: `test_C2_manager_budget_status_payload_has_the_existing_exact_key_set`, `test_C2_and_C3a_worker_service_serialization_is_not_a_payload_change`, `test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical`, `test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files`; the worker golden path also raised JSON serialization on the leaked spec object. |
  | C4 | Reload `Item` by `evaluation.item_id` and derive from that item. | **2 failed**: `test_C4_manager_uses_loaded_primary_item_not_evaluation_item`, `test_C4_worker_uses_loaded_primary_item_not_evaluation_item`; both observed X/table instead of Y/chair. |
  | C4 item-id consistency | Set evaluated status `item_id` from the loaded item instead of `evaluation.item_id`. | **2 failed**: the two C4 tests above; both observed Y instead of the required evaluated X. |
  | C5(a) | Pass `TypicalFilterSpec()` into the manager no-item empty-status call. | **1 failed**: `test_C5_empty_status_preserves_no_item_vs_categoryless_item[C5-a-manager-no-primary]`. |
  | C5(b)/(c) manager item-present | Pass `None` into the manager item-present empty-status call. | **1 failed**: `test_C5_empty_status_preserves_no_item_vs_categoryless_item[C5-b-manager-categoryless-primary]`. |
  | C5(c) worker no-item | Pass `TypicalFilterSpec()` into the worker no-item empty-status call. | **1 failed**: `test_C5_empty_status_preserves_no_item_vs_categoryless_item[C5-c-worker-no-primary]`. |
  | C5(d) worker item-present | Pass `None` into the worker item-present empty-status call. | **1 failed**: `test_C5_empty_status_preserves_no_item_vs_categoryless_item[C5-d-worker-categoryless-primary]`. |
  | C6 | Remove the dataclass default from `typical_filter_spec`. | **7 failed / 232 passed** across integration/router coverage: C1, C2 manager construction, and the four role/unknown-role router tests (`test_budget_status_route_is_available_to_all_roles[...]` ×4, `test_budget_status_audience_predicate_fails_closed_for_unknown_role`). |
  | C-N1(a) index removal | Drop `uix_task_items_primary_active` before the violating insert. | **1 failed**: `test_CN1a_primary_index_is_partial_and_two_legal_shapes_are_valid` (`DID NOT RAISE IntegrityError`). |
  | C-N1(a) no-WHERE index | Recreate `uix_task_items_primary_active` without its partial predicate. | Legal active RELATED/removed PRIMARY shapes failed at their legal flush, proving the predicate is required. |
  | C-N1(b) command guard | Remove the explicit active-PRIMARY precheck from `add_item_to_task`. | **1 failed**: `test_CN1b_add_item_to_task_has_the_explicit_primary_conflict_guard`; database `IntegrityError` replaced the pinned `ConflictError` message. |

- **L4 stamp:** authoritative command `PYTHONPATH=. pytest -m 'not e2e'` from `app/`, with default `BEYO_TEST_SLOT=main`, produced **2674 passed, 21 failed, 1 skipped, 2 warnings** across **2696 collected items** in 48.83s. The 21 failing IDs are exactly the approved baseline set in the live-working-time-clock handoff: no new failures and no baseline failures disappeared. The set is unchanged in both directions (added-to-baseline: none; baseline-not-in-current: none). The failures are unrelated existing failures in Shopify migration, auth role shape, upholstery/inventory fixtures, bootstrap, item routers, working sections, worker stats, case-type serialization, and audit log.
- **Architecture graph:** rechecked the initialized graph at revision `364223242014a733822256e445824b7160bcda2e1cc4a6e3f9e9d930b5419a47` (198 nodes / 298 edges, 0 diagnostics, 1 pending review, 2 stale nodes). The phase changes a field inside an existing projection contract and adds no boundary or node meaning. One attempted empty `archgraph_apply_changes` call was rejected by the tool's minimum-one-change validation; no graph mutation was made, and the pending review item was untouched.
- **Environment / deviations:** Redis was available (`PONG`); no implementation deviations from the approved plan. The expected untracked `.archgraph/contexts/` directory remains outside the checkpoint commit.
