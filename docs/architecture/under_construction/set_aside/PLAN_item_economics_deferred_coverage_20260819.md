# PLAN — item-economics deferred coverage (set aside 2026-08-19)

```
state: SET ASIDE — owner decision, 2026-08-19
origin: simple_valuation_editor pipeline, phases 3–5
why here: the pipeline folder archives at closeout; these items would archive with it
```

## Why this file exists

Three items were found with evidence during the `simple_valuation_editor` pipeline and
deliberately **not** fixed. Each guards something that is **correct today** and has **no
comment in the tree claiming otherwise** — which is the line the owner drew when choosing the
shortest path to closed.

They are written here rather than in the pipeline folder because that folder moves to
`archive/` and an item recorded only there is an item that gets dropped.

**Every before-state below was measured, not estimated.** Whoever picks these up does not need
to rediscover them — only to confirm they still hold.

---

## 1. The price-scenario handoff is outside the docs accuracy arbiter

`app/tests/unit/docs/test_item_economics_handoff_accuracy.py` calls itself *"the accuracy
arbiter for the two frontend handoffs"*. It covers `_OPERATIONAL` and `_CONFIGURATION`, both
dated 2026-08-15. **`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_price_scenario_20260819.md`
is not a subject of it.**

**Measured (phase 4 re-review r2):** of the 59 tests under `tests/unit/docs/`, **exactly one**
reads either phase-4 document, and it only asserts one string's absence. So "the docs guards
are green" was reporting on other documents — consistent with review r1 finding five
nullability defects and r2 finding a sixth in a document that was green throughout.

**Why it matters:** this is the most arithmetic-dense handoff the project produced and the one
a frontend builds a money screen from. It should be under the same arbiter as its predecessors.

**Tasks**

1. Add `_PRICE_SCENARIO = _HANDOFFS / "to_frontend" / "HANDOFF_TO_FRONTEND_price_scenario_20260819.md"`.
2. Add `_PRICE_SCENARIO_ROUTES = frozenset({"GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario"})`
   and fold it into `_ALL_ROUTES`.
3. Extend the parametrisations taking `(document, routes)` and the four-document
   error-identity sweep at `:175`.
4. **Mind `:169`** — `_heading_routes(_CONFIGURATION) | _heading_routes(_OPERATIONAL) == _ALL_ROUTES`
   asserts the union of *headings* covers every route. The price-scenario handoff documents its
   route in §1 prose, not as a `## GET …` heading, so this either gains the third document
   **or** the route is exempted **with the reason written into the test file**. Do not silently
   loosen it.

**Named mutations:** introduce a route into the handoff's prose that does not exist in the
router → an arbiter test reddens; name a retired error identity → reddens (this already holds
via `test_retired_inline_refusal_identity_is_absent_from_live_sources`; confirm it is not the
*only* thing covering the document).

**Do not extend the arbiter into a nullability checker.** It checks routes, error identities,
status values and envelope keys — string-level facts. Nullability is where every phase-4 defect
actually lived, and that needs its own mechanism and its own inventory.

**Files:** `app/tests/unit/docs/test_item_economics_handoff_accuracy.py` only. **Not the
handoffs** — they are APPROVED text, and a test that requires changing its subject to pass is a
test asserting the wrong thing.

---

## 2. `collapse_terms`'s deleted-term skip has one guard, and it is incidental

`collapse_terms` skips `term.is_deleted is True`
(`app/beyo_manager/domain/item_economics/price_scenario.py:71-72`) — intention §3.1B and §9A.2.

**Measured whole-suite, twice (phase 3 review r1 by the reviewer, reproduced by the
coordinator, ID-diffed):** delete those two lines and **exactly one test reddens in the entire
codebase** —
`tests/integration/services/queries/item_economics/test_price_scenario_query.py::test_phase3_c2_deleted_purchase_term_is_ignored_by_admission_and_model`.
The domain owner file `tests/unit/domain/item_economics/test_price_scenario.py` stays
**53/53 green**.

That row was added by phase 3 to guard something else. So the semantic had **no guard at all**
before phase 3 and now has one that is incidental to it: rename, narrow or move that row and
the semantic silently loses its only test.

**Task:** add a direct row in the domain owner file — a term list containing a deleted
`ITEM_PURCHASE_COST` term, asserting `collapse_terms` ignores it. Fallback if judged
disproportionate: a comment at `price_scenario.py:71` naming the integration row as its sole
guard. **The direct row is preferred; a comment cannot fail.**

**Named mutation:** delete the skip → the observed-red set, measured **across the suite**, now
contains the new domain row. The criterion is that the set **grows**, not that it is one.

**Files:** `app/tests/unit/domain/item_economics/test_price_scenario.py`, or
`app/beyo_manager/domain/item_economics/price_scenario.py` for the fallback comment only.

---

## 3. A dangling cross-reference in `domain/users/serializers.py`

`app/beyo_manager/domain/users/serializers.py:195` carries:

```python
# PRECEDENCE (criterion 13), asserted rather than incidental: …
```

`criterion 13` resolves only inside a pipeline document from an earlier project. The rule the
`simple_valuation_editor` pipeline earned, twice, is: **a cross-reference from production code
must resolve from a clean checkout with no pipeline documents present** — which rules out
criterion IDs, round numbers, mutation nicknames and bare line numbers in one sentence. The
house convention is `path:symbol` and already satisfies it in several places.

**One comment line.** Belongs to whichever pipeline next touches `domain/users/`; it was never
in any `simple_valuation_editor` perimeter.

---

## 4. Two flaky tests, named but not diagnosed

Not a task — a record, so the next person to chase suite instability starts 21 runs ahead.

The `simple_valuation_editor` master plan §6 recorded ±1 drift across three pipelines with the
drifting test *"unidentified"*. Twenty-one full runs at phase 3 gave **two** names:

| Test | Observations |
|---|---|
| `tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]` | red in 2 of 21 runs (both the same session), green in the other 19, **passes 1/1 in isolation** |
| `tests/integration/services/commands/shopify/test_process_shopify_products_integration.py::test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task` | red in 1 of 21 runs; the immediate repeat came back green with the baseline set byte-identical |

**The consequence that matters: it is not one test.** Any attempt to fix "the drifting test"
assuming a single culprit will close half the problem and declare victory. Both are
concurrency- or fan-out-shaped, which is the class whose outcome depends on suite-wide load
rather than on the code.

Confirming either is its own session. **Neither was touched.**
