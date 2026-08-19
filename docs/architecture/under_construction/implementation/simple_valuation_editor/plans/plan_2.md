# Plan 2 — the read model, the route, and the mirror

```
plan: 2
state: NOT_STARTED — blocked on plan 1 APPROVED
date: 2026-08-19
gate: projection r0 REQUIRED (M3 is a statistic, M6 is a fingerprint — master plan §7)
```

**This plan is authored at planning time and will be amended at plan 1's closeout.** The
criteria below are complete in coverage but will absorb plan 1's review lessons and any
forward hazard its reviewer names. That amendment is the coordinator's fold-back
responsibility, not a re-planning session.

## 1. Goal

Assemble the payload and mount it. Phase 1 produced every number; this phase proves the
wiring — that the right rows are loaded, the right statuses branch, the right sections
participate, and that no monetary key reaches a surface that must not see it.

## 2. Files

| Path | Change |
|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | **new** — the query service |
| `app/beyo_manager/domain/item_economics/serializers.py` | **additive** — `serialize_task_price_scenario` only; no existing function touched |
| `app/beyo_manager/routers/api_v1/item_economics.py` | **additive** — one route (HC-2a artifact 4) |
| `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` | HC-2a artifact 1 — `_EXPECTED_ROUTES` +1 row, both count assertions **25 → 26** (`:126`, `:127`), **and the test function's own name**, which reads `test_the_registry_ships_twenty_five_routes` (`:123`) |
| `app/beyo_manager/routers/README.md` | HC-2a artifact 2 — one Quick Index row + one detail section |
| `app/tests/unit/routers/api_v1/test_item_economics_router.py` | HC-2a artifact 3 — `_ROUTES` (`:14`), **not** `_ALL_ROLE_ROUTES` (`:48`): this route is manager-gated |
| `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` | **new** — the criteria below |

**The function name at `:123` is not in HC-2a's enumeration and is required anyway.**
Verified by the coordinator, 2026-08-19: leaving it renames nothing but leaves a test
called `..._twenty_five_routes` asserting 26, which is a comment that lies at exactly the
place a future route author looks first. It is the same artifact, so no perimeter extension
is needed — only the awareness that HC-2a's line list is incomplete.

**No change to `price_scenario.py`.** Phase 1 is settled; a defect found in it is a finding
routed back, not an edit made here.

### Enumerated exceptions carried in from phase 1's closeout

Two edits outside the table above are authorized, each one row, each traceable to a named
phase-1 note. **Nothing else in a phase-1 file may change.**

1. **`app/tests/unit/domain/item_economics/test_price_scenario.py` — N8.** Phase 1's
   `test_quantity_zero_falls_back_to_a_divisor_of_one` carries a second assertion that does
   not discriminate: at `B = 1_211_335` the bands at `Q = 0`, `Q = 1` and `Q = 6` are all
   identical, so a clamp to `6` passes it. **Replace that assertion with a discriminating
   one** using the fixture the reviewer supplied and the coordinator recomputed:

   ```
   B = 8_919:  Q = 1 → SliderDomain(110, 3_080, 12_100)
               Q = 6 → SliderDomain(114, 3_078, 12_084)
   ```

   so `slider_domain(8_919, 0, 0) == slider_domain(8_919, 1, 0)` is red under
   `max(6, quantity)`. **Named mutation:** `max(1, quantity)` → `max(6, quantity)` in
   `slider_domain`'s definition → this assertion red. Keeping the current assertion is the
   one option that leaves a false impression, which is why this is carried rather than
   accepted.
2. **`app/beyo_manager/domain/item_economics/calculator.py` — N11, comment only.** Master
   plan §4 sanctions `_shape_error`'s duplication on condition that **both** sites carry a
   comment pointing at the other. Phase 1 could not write the `calculator.py` half — that
   file is on plan 1 §2's exclusion list — and a one-way pointer is worse than none, since
   the point is that a later consolidation finds both. **Both comments land here, together,
   in the same commit.** No executable line in `calculator.py` may change.

## 3. Tasks

1. Task resolution reusing `get_task_budget_status`'s path (§2.5): task → PRIMARY
   `TaskItem` → `Item`, `item_binding`, `404` for unknown/deleted/cross-workspace.
2. Configuration through `_load_preview_inputs` (§2.3) — **not** a new set of selects.
3. **M3** (§5.3A): participating set per `budget_division.py:309-313`; `usable(t) = t is not
   None and t > 0`; median substituted per section and **quantised per section** at
   substitution; counters count *not-usable*, not *null*. The shared typical statement is
   **imported**, never reimplemented (master plan §4, one-copy rule).
4. **M4** (§6, §6B): the byline, its three author cases and its three absence cases.
   `serialize_user_light`'s three-key shape re-declared with the cross-reference comment at
   **both** sites.
5. **The status branch** (§9A.1): the twelve-row table, D8's version — `model`/`anchors`/
   `domain` present for `ok`, `infeasible`, `item_unvalued`, `item_missing_expected_price`,
   `not_evaluated`; `null` for the other seven.
6. **`can_commit`** (§9A.2): all five conditions, price-independent.
7. **M6 `config_fingerprint`** (§9A.3): full ids, fixed order, `CALCULATION_VERSION` as
   identity, `null` with a null model.
8. Serializer + route, ADMIN/MANAGER only (HC-3), and the four HC-2a artifacts moved
   together.

## 4. Acceptance criteria

| C | Criterion |
|---|---|
| C1 | **The status matrix: twelve rows over all twelve values** (§12A's correction), each asserting its own row of §9A.1 — the seven `null` rows **and** the five present rows. The present half is what fails silently if the predicate is written as `status is OK`. |
| C2 | **`can_commit`, one row per condition**, each fixture violating **only** its own condition (rule 2's companion), plus the two asymmetry rows: valuation-with-null-price ⇒ `true`; **no valuation row ⇒ `false`** even with a price supplied. A test exercising only task state passes against §8's incomplete gloss and proves nothing. |
| C3 | **M3 usability**: a section whose typical is exactly `0` with five qualifying groups — `sections_without_sample` counts it and the median is substituted for it. Under §5.2's superseded "NULL" wording this row is red. |
| C4 | **Median quantisation**: an even number of usable typicals differing by an odd amount so the median is `x.5`, with **two** sections substituted — asserting per-section quantisation, which differs from sum-quantisation by exactly one second on this fixture. |
| C5 | **Participating set**, one row per excluded state — `SKIPPED`, `CANCELLED`, `FAILED` separately, never one row for "an excluded state" (rule 2). Plus a section whose steps are all deleted. |
| C6 | **M3 no-evidence** (D7): no usable typical ⇒ `total_seconds == 0`, `is_estimated true`, `sections_without_sample == sections_total`, and `anchors`/`domain` absent. |
| C7 | **M4 absence rows**: no valuation row ⇒ `saved: null` **and** `currency: null` (§6B, overriding §9.1); a valuation with a NULL price still yields a byline; a byline survives when the user row cannot be loaded (defensive `null`, never a 500). |
| C8 | **M6**: full ids in fixed order; a **new cost model version** changes the fingerprint while **the same version re-read** does not; `null` when the model block is `null`. |
| C9 | **`item_binding`** `detached` and `mismatched` ⇒ `200` with `saved`/`model`/`anchors`/`domain` all `null` (§9.2) — one row each, not one row for "not bound". |
| C10 | **`404`** for unknown, deleted and cross-workspace tasks — three rows (§9.2). The cross-workspace row is the tenant boundary and gets its own criterion per the tenant-boundary-row rule. |
| C11 | **No monetary leak** (HC-3): WORKER and SELLER receive `403`, in the style of the existing role tests. A withheld monetary key is **absent**, never null. |
| C12 | **Route mirror**: all four HC-2a artifacts move together; both counts read 26; the mirror test's own name no longer says "twenty five". |
| C13 | **Service identity** (one-copy rule / service-identity rule): the route's mount is guarded by `calls[0][0] is get_task_price_scenario`, never by status code + call count (precedent `test_item_economics_router.py:133`). |
| C14 | **`divide_production_budget` is not called** by this feature (§10's first cut). Asserted, not assumed — a criterion, because the allocator is the obvious thing for an implementer to reach for when it sees "sections". |
| C16 | **The two carried exceptions land** (§2): the discriminating `Q = 0` row asserts `slider_domain(8_919, 0, 0) == slider_domain(8_919, 1, 0)` and reddens under `max(6, quantity)`; both `_shape_error` cross-reference comments exist, each naming the other's path. |
| C17 | **Purity, if extended** — if this phase adds a C21-style import assertion for the query service, it must handle **relative imports** (N6): `ast.ImportFrom` with `level > 0` carries a partial `node.module` that no forbidden prefix matches, and `from . import x` has `node.module is None` and is skipped entirely. Theoretical in this repo — `app/beyo_manager` contains zero relative imports — which is exactly why it would pass review unnoticed. If the assertion is **not** extended, say so in the handoff rather than leaving it ambiguous. |
| C15 | **Teardown** (rule 11½): every test committing rows deletes them in `finally`; the residue check names its tables. The baseline's ~24 `task_steps` / ~40 `step_state_records` drift is inherited and is never read as evidence. |

## 5. Out of scope

Everything in intention §10's cut list — per-section breakdown, the already-logged card,
the cost-of-work card, the headroom bar, the percentage headline, `terms[]`, a
worker/seller variant, **any write**, multi-task items.

## 6. Review log

*(empty — populated by the reviewer)*
