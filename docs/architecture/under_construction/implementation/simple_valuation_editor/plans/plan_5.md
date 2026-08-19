# Plan 5 — register the price-scenario handoff with the accuracy arbiter

```
plan: 5
state: NOT_STARTED — blocked on plan 3 APPROVED (shares no files, but shares a baseline)
date: 2026-08-19
gate: projection WAIVED — one test file, no new mechanism
origin: phase 4 re-review r2, R8 and lesson 3
```

## 1. Goal

`app/tests/unit/docs/test_item_economics_handoff_accuracy.py` calls itself *"the accuracy
arbiter for the two frontend handoffs"*. It covers `_OPERATIONAL` and `_CONFIGURATION` — both
dated 2026-08-15. **`HANDOFF_TO_FRONTEND_price_scenario_20260819.md` is outside it.**

The consequence, measured by re-review r2: of the 59 tests under `tests/unit/docs/`, exactly
**one** reads either phase-4 document, and it only asserts one string's absence. So "the docs
guards are green" reported on documents other than the one under review — which is consistent
with r1 finding five nullability defects and r2 finding a sixth in a document that was green
throughout.

This is the most arithmetic-dense handoff this project has produced, and it is the one a
frontend builds a money screen from. It should be under the same arbiter as its predecessors.

## 2. Files — one

| Path | |
|---|---|
| `app/tests/unit/docs/test_item_economics_handoff_accuracy.py` | additive |

**Nothing else.** Not the handoffs — they are APPROVED text by the time this runs, and a test
that requires changing its subject to pass is a test asserting the wrong thing. **If the
arbiter's assertions fail against the shipped handoff, that is a finding routed back, not an
edit to the document.**

## 3. Tasks

1. Add `_PRICE_SCENARIO = _HANDOFFS / "to_frontend" / "HANDOFF_TO_FRONTEND_price_scenario_20260819.md"`.
2. Add `_PRICE_SCENARIO_ROUTES = frozenset({"GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario"})`
   and fold it into `_ALL_ROUTES`.
3. Extend the existing parametrisations that take `(document, routes)` and the four-document
   error-identity sweep at `:175` to include it.
4. **Mind `:169`** — `_heading_routes(_CONFIGURATION) | _heading_routes(_OPERATIONAL) == _ALL_ROUTES`
   asserts the union of *headings* covers every route. The price-scenario handoff documents its
   route in §1 prose, not as a `## GET …` heading, so this assertion must either gain the third
   document **or** the new route must be exempted with a stated reason. **Decide and record
   which — do not silently loosen it.**

## 4. Acceptance criteria

| C | Criterion |
|---|---|
| C1 | The price-scenario handoff is a subject of the route-mirror, status-vocabulary and error-identity assertions the other two handoffs already face. |
| C2 | The `:169` union assertion is either extended or exempted, **with the reason written into the test file**, and the choice is stated in the handoff. |
| C3 | **Named mutation:** introduce a route into the handoff's prose that does not exist in the router → an arbiter test reddens. Both sides computed; whole-suite run. |
| C4 | **Named mutation:** name a retired or unregistered error identity in the handoff → reddens (this already holds via `test_retired_inline_refusal_identity_is_absent_from_live_sources`; confirm it is not the *only* thing covering the document). |
| C5 | Suite at or above plan 3's closing baseline. Failure IDs diffed, not counted. |

## 5. What this phase cannot do, and should not try

The arbiter checks **routes, error identities, status values and envelope keys** — string-level
facts. It cannot check nullability, which is where every phase-4 defect actually lived. **Do not
extend it into a nullability checker**; that is a different mechanism and would need its own
inventory. Registering the document closes the drift channel the arbiter was built for and
leaves the one it was not.

Master plan §5 carries the lesson separately: a payload contract's nullability needs its own
enumerated criterion, and that belongs in the *plan* that writes the document, not in a test.

## 6. Review log

*(empty)*
