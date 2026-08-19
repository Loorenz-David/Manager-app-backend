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

   **Assert the exact literal, never an equality between two calls:**

   ```python
   assert slider_domain(8_919, 0, 0) == SliderDomain(
       step_minor=110, min_minor=3_080, max_minor=12_100
   )
   ```

   **Named mutation:** `max(1, quantity)` → `max(6, quantity)` in `slider_domain`'s
   definition → this row red (the mutation returns `114 / 3_078 / 12_084`).

   > **Corrected at the projection r0 fold (2026-08-19, L1) — the coordinator's carried fix
   > was itself inert.** This exception originally required
   > `slider_domain(8_919, 0, 0) == slider_domain(8_919, 1, 0)`. **That assertion cannot fail
   > under the mutation it names, at any `B`**: `max(6, ·)` maps `quantity = 0` and
   > `quantity = 1` to the *same divisor*, so any `f(0) == f(1)` is invariant under it. The
   > reviewer's fixture was right — `B = 8_919` genuinely separates `Q = 1` (`110 / 3_080 /
   > 12_100`) from `Q = 6` (`114 / 3_078 / 12_084`) — but the *assertion form* was
   > transcribed unchanged from the inert one it replaced, so the defect survived its own
   > correction. Verified both ways against the shipped module: the equality form stays green
   > under the mutation, the literal form goes red.
   >
   > **The discriminating power lives in the literal, not in the equality.** The existing row
   > at `test_price_scenario.py:377-381` cannot substitute: at `B = 1_211_335` the mutated
   > function still returns `15_000 / 420_000 / 1_650_000`, measured.
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
   together. **The mirror file's stale docstring at `:9` ("the same **23** rows") is
   corrected with the function name at `:123`** — same artifact, no perimeter extension
   (L16).

9. **Assemble `PriceModel`** (L4) — the single most load-bearing line of this phase, and it
   was in no task and no criterion. `collapse_terms` returns `tuple[int, int] | None`; the
   carrier needs a third field:
   `cost_per_worker_minute_ten_thousandths = int(selection.basis_version.cost_per_worker_minute_minor.scaleb(4))`
   (§3.1B's canonicalisation; positive by `ck_pcbv_cost_per_worker_minute_minor_positive`,
   `production_cost_basis_version.py:38`). **The `None` return maps to status
   `item_missing_purchase_cost` with all three blocks `null`** (§9A.1 row B8, and the B6/B7
   qualification added at §9A.1).

10. **`anchors.suggested_price_minor`** (L6) — `ceil_to_step(break_even, step_minor)`, and
    **`null` whenever `domain` is `null`**, not only when `break_even` is (§4.4B). This key
    had no criterion in either phase.

### Delegations — granted explicitly, not taken silently

- **D-5 — how the participating set and the median are reached** (L5). Master plan §4's
  one-copy rule says both are *imported* from `budget_division.py`. Neither is importable:
  the participating set is a comprehension at `:309-313` inside `divide_production_budget`
  (which C14 forbids calling), and `_median` (`:69-74`) and `_step_state_is_excluded`
  (`:209-210`) are private and not in `__all__`. **The implementer chooses** between
  importing the private names (no production precedent; test precedent at
  `test_production_time_query.py:12`) and building the set inline from the public
  `group_steps_by_section` + `EXCLUDED_STEP_STATES`. **Reimplementing `_median` is not on
  the table** — that is the copy the rule forbids. **One trap, stated because it is silent:**
  `state in EXCLUDED_STEP_STATES` is **not** equivalent to `_step_state_is_excluded`, which
  compares `.value` strings and so tolerates a step whose `state` is a plain string. For ORM
  `TaskStep` rows they agree today. Report the choice; the coordinator records it.
- **D-6 — how the committed evaluation is loaded** (L8). Nothing in this plan assigned it,
  yet `ok`, `infeasible` and `item_binding` all require it. **The implementer chooses**
  between calling `get_task_budget_status` (precedent: `get_task_production_time.py:26`) and
  loading the evaluation directly. Report the choice.
- **D-7 — where `serialize_task_price_scenario` is called** (L9). Both router precedents are
  live in the same file: `production-time` serializes **service-side**
  (`get_task_production_time.py:82`), `budget-status` serializes **router-side**
  (`item_economics.py:361-367`). **This decision changes this plan's declared perimeter**, so
  it is delegated with its consequence stated: if you serialize router-side, adding the row
  to `_ROUTES` makes `test_every_item_economics_route_retains_admin_and_manager_access` feed
  `fake_run_service`'s `{"ok": "test"}` into the serializer, and that fake must be extended
  too — a change to `test_item_economics_router.py` beyond the one row §2 authorises.
  **If you choose router-side, that is a STOP and a report, not an edit.** Service-side keeps
  §2 accurate.

## 4. Acceptance criteria

| C | Criterion |
|---|---|
| C1 | **The status matrix: twelve rows over all twelve values** (§12A's correction), each asserting its own row of §9A.1 — the seven `null` rows **and** the five present rows. The present half is what fails silently if the predicate is written as `status is OK`. **Two fixture constraints, stated because otherwise the outcome is a property of the fixture rather than of the status** (L3, and C1's own decidability): the B6 and B7 rows use a cost model **without** a purchase term, or with a purchase cost present, per §9A.1's `†` qualification — plus **one further row** with a purchase term and no purchase cost asserting all three blocks `null`; and every "present" row uses a **fundable** model, since a degenerate model or `T = 0` makes `domain` `null` while the status is still `ok`. |
| C2 | **`can_commit`, one row per condition**, each fixture violating **only** its own condition (rule 2's companion), plus the two asymmetry rows: valuation-with-null-price ⇒ `true`; **no valuation row ⇒ `false`** even with a price supplied. A test exercising only task state passes against §8's incomplete gloss and proves nothing. **The predicate is computed from the LIVE selection** (§9A.2's block form), never from the status — §9A.2's "equivalently A1/A2/B7/B10" shorthand is retracted, and one row proves why: a task committed while the configuration was healthy keeps status `ok` after its cost model version expires, where the status form would publish `can_commit: true` for a button whose press is a guaranteed error. |
| C3 | **M3 usability**: a section whose typical is exactly `0` with five qualifying groups — `sections_without_sample` counts it and the median is substituted for it. Under §5.2's superseded "NULL" wording this row is red. |
| C4 | **Median quantisation**: an even number of usable typicals differing by an odd amount so the median is `x.5`, with **two** sections substituted — asserting per-section quantisation, which differs from sum-quantisation by exactly one second on this fixture. |
| C5 | **Participating set**, one row per excluded state — `SKIPPED`, `CANCELLED`, `FAILED` separately, never one row for "an excluded state" (rule 2). Plus a section whose steps are all deleted. |
| C6 | **M3 no-evidence** (D7), **two rows, and the fixtures are stated** (L7, L12): (a) a **non-empty** participating set with no usable typical ⇒ `total_seconds == 0`, `is_estimated true`, `sections_without_sample == sections_total > 0`; (b) an **empty** participating set — no steps, or every section excluded ⇒ `sections_total == 0` and **`is_estimated true`** per §5.3A's corrected line, where `any()` over the empty set would otherwise publish `false` and render a *measured* typical of zero. In both: **`anchors` is present with `break_even_price_minor: null` and `is_fundable: false`; `domain` is `null`.** Absence is a property of the block, not of its members — §3.5, §4.1 and §12.5 all publish the anchors block populated with nulls. |
| C18 | **`suggested_price_minor`** (L6, §4.4B) — a key with no criterion in either phase until now. One row asserting `ceil_to_step(break_even, step_minor)` on the mockup's data (`1_215_000`), and one asserting **`null` when `domain` is `null` with a non-`null` break-even** — reachable at `PriceModel(100_000, 0, 10_000)` with `T = 60`, which gives `break_even = 1` and `slider_domain(1, 6, 0) is None`. Without the second row, an implementer following §4.4 literally writes `ceil_to_step(B, domain.step_minor)` and ships an `AttributeError` — a 500 where the contract wants a `null`. |
| C7 | **M4 absence rows**: no valuation row ⇒ `saved: null` **and** `currency: null` (§6B, overriding §9.1); a valuation with a NULL price still yields a byline; a byline survives when the user row cannot be loaded (defensive `null`, never a 500). |
| C8 | **M6**: full ids in fixed order; a **new cost model version** changes the fingerprint while **the same version re-read** does not; `null` when the model block is `null`. |
| C9 | **`item_binding`** `detached` and `mismatched` — one row each, not one row for "not bound", **each asserting the full payload row of §9.2A**, not four keys of an otherwise-undefined shape (L2). Per §9.2A: `saved`/`model`/`anchors`/`domain` `null` and `config_fingerprint` `null` on both; `item` **`null`** for `detached` and populated for `mismatched`; `typical` **populated** on both; `can_commit` `false` for `detached`. §9.2A governs over §9A.1's table on every non-`bound` binding — these are not edge cases, they collide every time. |
| C10 | **Unknown, deleted and cross-workspace tasks — three rows** (§9.2), asserted at the **service level as `NotFound`** (precedent `test_production_time_query.py:272`), because the only new test file in §2 is a service-level integration test and a `404` is not observable there (L15). Adding a route-level file would be a perimeter change; if one is wanted, that is a STOP and a report. The cross-workspace row is the tenant boundary and gets its own criterion per the tenant-boundary-row rule. |
| C11 | **No monetary leak** (HC-3): WORKER and SELLER receive `403`, in the style of the existing role tests. *(The former second sentence — "a withheld monetary key is absent, never null" — is **struck**: the route `403`s, so no payload exists in which a key could be absent. It is not decidable, and C12 already proves the only thing it meant, namely that no worker/seller variant is mounted. L11.)* |
| C12 | **Route mirror**: all four HC-2a artifacts move together; both counts read 26; the mirror test's own name no longer says "twenty five". |
| C13 | **Service identity** (service-identity rule): the route's mount is guarded by `calls[0][0] is get_task_price_scenario`, never by status code + call count. **This needs a NEW test function in `test_item_economics_router.py`** (L10) — the cited precedent lives in `test_budget_status_route_is_available_to_all_roles` (`:135-143`), which is parametrized over `_ALL_ROLE_ROUTES`, the list this route must **not** join; and the two `_ROUTES` parametrizations assert only `403` + `calls == []` and `200` + `len(calls) == 1`. §2 describes that file as a one-row edit; it is one row **plus this function**. |
| C19 | **The typical map is built defensively** (L13): a participating section with **no row** from `typical_times_statement` — reachable when its `WorkingSection` is deleted — resolves through `.get()` to a `None` typical and is counted in `sections_without_sample`. `sections_total` counts sections derived from **steps**, never from the statement's rows; a `KeyError` here would be a 500 on an ordinary data state. |
| C14 | **`divide_production_budget` is not called** by this feature (§10's first cut). Asserted, not assumed — a criterion, because the allocator is the obvious thing for an implementer to reach for when it sees "sections". |
| C16 | **The two carried exceptions land** (§2): the discriminating `Q = 0` row asserts `slider_domain(8_919, 0, 0) == slider_domain(8_919, 1, 0)` and reddens under `max(6, quantity)`; both `_shape_error` cross-reference comments exist, each naming the other's path. |
| C17 | **Purity is NOT extended to the query service — decided here, not left to the handoff** (L17). A purity assertion cannot bind an I/O module: the query service exists to hold a session and ORM queries, so the forbidden-prefix set has no meaning for it. And phase 1's assertion lives in `test_price_scenario.py`, which §2 opens for exactly one edit — extending it there would be a scope breach. **N6 is therefore recorded and closed, not carried further**: if a future phase ever does extend a C21-style assertion, it must handle **relative imports** (N6): `ast.ImportFrom` with `level > 0` carries a partial `node.module` that no forbidden prefix matches, and `from . import x` has `node.module is None` and is skipped entirely. Theoretical in this repo — `app/beyo_manager` contains zero relative imports — which is exactly why it would pass review unnoticed. If the assertion is **not** extended, say so in the handoff rather than leaving it ambiguous. |
| C15 | **Teardown** (rule 11½): every test committing rows deletes them in `finally`; the residue check names its tables. The baseline's ~24 `task_steps` / ~40 `step_state_records` drift is inherited and is never read as evidence. |

## 5. Out of scope

Everything in intention §10's cut list — per-section breakdown, the already-logged card,
the cost-of-work card, the headroom bar, the percentage headline, `terms[]`, a
worker/seller variant, **any write**, multi-task items.

## 6. Review log

*(empty — populated by the reviewer)*
