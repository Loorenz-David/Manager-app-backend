# Plan 5 — register the price-scenario handoff with the accuracy arbiter

```
plan: 5
state: NOT_STARTED — blocked on plan 3 APPROVED (shares no files, but shares a baseline)
date: 2026-08-19
gate: projection WAIVED — one test file, no new mechanism
origin: phase 4 re-review r2, R8 and lesson 3; §1B added from phase 3 review r1, N-2
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

## 1B. A second, unrelated goal — and the perimeter widening it forces

**Phase 3's review found that a phase-1 domain semantic has exactly one guard in the whole
codebase, and it is in an integration file two layers away.**

`collapse_terms` skips `term.is_deleted is True` (`price_scenario.py:71-72`) — intention §3.1B
and §9A.2. Delete those two lines and run the **whole** non-e2e suite: **exactly one test
reddens**, `test_phase3_c2_deleted_purchase_term_is_ignored_by_admission_and_model`, an
integration row added by phase 3 to guard something else. The domain owner file
`tests/unit/domain/item_economics/test_price_scenario.py` stays **53/53 green**. Measured by
the reviewer and reproduced whole-suite by the coordinator, ID-diffed, one added and none
removed.

So the semantic had **no guard at all** before phase 3, and now has one that is incidental to
it. Rename, narrow or move that row and the semantic silently loses its only test.

**Task:** add a direct row in the domain owner file — a term list containing a deleted
`ITEM_PURCHASE_COST` term, asserting `collapse_terms` ignores it — **or**, if that is judged
disproportionate, a comment at `price_scenario.py:71` naming the integration row as its sole
guard. **Decide and record which.** A direct row is preferred; the comment is the fallback,
and it is strictly weaker because a comment cannot fail.

> **This widens the perimeter from one file to two (or three), and that is recorded
> deliberately.** Plan 5 was scoped to the docs arbiter alone. The reason for folding this in
> rather than opening plan 6: `price_scenario.py` and its domain test are **phase 1's files,
> APPROVED and closed**, so no open plan can reach them, and this is the last plan in the
> project — the alternative is the closeout sweep, where an unguarded domain semantic is
> exactly the kind of item that gets dropped. If the implementer judges the widening wrong,
> **that is a STOP and a report**, not a judgement call.

## 2. Files — one for §1, up to two more for §1B

| Path | |
|---|---|
| `app/tests/unit/docs/test_item_economics_handoff_accuracy.py` | §1, additive |
| `app/tests/unit/domain/item_economics/test_price_scenario.py` | §1B, additive — **one row, nothing else touched** |
| `app/beyo_manager/domain/item_economics/price_scenario.py` | §1B fallback only — **one comment line**, and only if the direct row is declined |

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
| C6 | **§1B**: either the direct domain row exists, or the fallback comment does, and the handoff states which and why. |
| C7 | **§1B named mutation**: delete `collapse_terms`'s `if term.is_deleted is True: continue` → the observed-red set, measured **across the suite**, now contains the new domain row. Record both sides. **Before this plan, that set was exactly one test and it was in an integration file** — so the criterion is that the set grows, not that it is one. |

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
