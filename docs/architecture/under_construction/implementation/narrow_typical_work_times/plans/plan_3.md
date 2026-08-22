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
- `planning/owner_decisions.md` — D9, D11.
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
