# Plan 3 — `TaskBudgetStatus` carries the derived spec

```
plan: plan_3
project: narrow_typical_work_times
state: NOT_STARTED
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
   manager change. With it, §6.2's table is **seven** rows, not the "all four" its header
   claims.
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
(`models/tables/tasks/task_item.py:53`).
*Mutation*: drop the index in the test's transaction (or assert against
`pg_indexes` that it exists **with its `WHERE` clause** — the partiality is the point: two
*removed* primaries, and a primary plus a *related* item, must both remain legal).
*Both sides* — contract: `IntegrityError` on the second active primary, **and** the two
legal shapes insert cleanly; mutation: the second active primary inserts.

**(b) The application guard.** `add_item_to_task` with a second primary raises
`ConflictError("Task already has an active primary item.")`
(`add_item_to_task.py:46-57`). **No test file in the repository references
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

*(empty — append-only; shared by implementer and reviewer)*
