---
plan: 2
role: reviewer (plan-projection)
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-19
actor: Opus 5 (projection r0)
---

# Projection r0 — phase 2 (`simple_valuation_editor`)

## Opening — for the owner

The plan for this phase is sound in what it wants to build, and I found nothing that needs
you personally. What I did find is that seventeen decisions the builder will hit in the
first hour are not actually settled by the documents, so the builder would have had to
invent them and nobody would have known which way they went. One of them matters more than
the rest: the safeguard this phase was supposed to add — a test that catches a specific
mistake in the slider's maths — was written in a form that cannot catch it. I ran the
mistake against the real code and the test stays green, so as written the phase would have
shipped the same false reassurance it exists to remove. That is the fourth time in this
project that a check read convincingly and could not fail, and it is cheap to fix on paper
now. Nothing here needs a decision from you; the coordinator applies the corrections and
the phase starts.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing in this projection needs the owner. Every finding is a plan amendment or a
correction routed to the intention, and each has one defensible resolution that the
coordinator can apply without a preference call.

---

## 1. The finding that mattered — L1 in full

**Plan 2 §2 exception 1 and criterion C16 name a mutation their assertion cannot detect.**
This is the carried fix for N8, the phase‑1 re‑review's own finding that an assertion did
not discriminate. The *fixture* the reviewer supplied is correct; the *assertion form* was
transcribed unchanged from the inert one, so the defect survived its own correction.

Plan 2 §2 (exception 1) and C16 both require:

```
slider_domain(8_919, 0, 0) == slider_domain(8_919, 1, 0)
Named mutation: max(1, quantity) → max(6, quantity) in slider_domain's definition
                → this assertion red.
```

**Both sides computed, against the shipped module at `price_scenario.py:192`:**

| | `slider_domain(8_919, 0, 0)` | `slider_domain(8_919, 1, 0)` | assertion |
|---|---|---|---|
| contract `max(1, quantity)` | `SliderDomain(110, 3_080, 12_100)` | `SliderDomain(110, 3_080, 12_100)` | **green** |
| mutation `max(6, quantity)` | `SliderDomain(114, 3_078, 12_084)` | `SliderDomain(114, 3_078, 12_084)` | **green** |

Measured twice: once against a reference implementation written from §7A.1, once by
`exec`-ing the real module source with the single substring replaced. Both agree.

**The reason is structural, not fixture-dependent.** The mutation replaces the clamp floor,
so it maps `quantity = 0` and `quantity = 1` to *the same divisor*. Any assertion of the
form `f(0) == f(1)` is therefore invariant under it, at every `B`. No choice of fixture can
rescue this assertion form — which is why re-deriving `8_919` (correctly) did not help.

**The plan's own premise is right and its conclusion is wrong.** `B = 8_919` genuinely
discriminates `Q = 1` from `Q = 6` — `(110, 3_080, 12_100)` against `(114, 3_078, 12_084)`
— which is exactly what `B = 1_211_335` failed to do. The discriminating power lives in the
*literal*, not in the equality.

**Proposed amendment** (§2 exception 1 and C16, same text in both):

```
assert slider_domain(8_919, 0, 0) == SliderDomain(
    step_minor=110, min_minor=3_080, max_minor=12_100
)
```

Verified red under the mutation (`114 ≠ 110`) and green under the contract. Note the row
already present at `test_price_scenario.py:377-381` cannot substitute for it: at
`B = 1_211_335` the mutated function still returns `SliderDomain(15_000, 420_000,
1_650_000)`, so that literal is green under the mutation too — measured, not assumed.

**Lesson for the plans** (proposed for master plan §5, beside the rule it extends): *the
rule "compute both sides of a named mutation" applies to the replacement as forcefully as
to the original — and the check is on the **assertion**, not on the fixture. An equality
between two calls is invariant under any mutation that maps both call sites to the same
value; a discriminating fixture reached through a non-discriminating comparison is still
decoration.*

---

## 2. Decision ledger

`P` = plan gap (amendment) · `I` = intention gap (routed upstream, never patched
downstream) · `F` = free choice (delegation to be granted in writing).

| # | Decision point | Class | Proposed routing |
|---|---|---|---|
| L1 | The N8 replacement assertion cannot fail under the mutation it names (§2 ex. 1, C16) | **P** | Replace with the exact literal above, in both places; add the lesson to master plan §5 |
| L2 | `item_binding: detached`/`mismatched` (§9.2) versus §9A.1's table — they collide on **every** occurrence, not sometimes | **I** | New lettered §9.2A: §9.2 wins; define `item`, `typical`, `status`, `can_commit`, `config_fingerprint` on both paths. Then extend C9 |
| L3 | §9A.1 rows B6/B7 say `model` **present**, but with a purchase term and no purchase cost `collapse_terms` returns `None` | **I** | Qualify B6/B7 in §9A.1: present **iff** the model is collapsible; C1's two rows then need a stated fixture each, plus a purchase-term row |
| L4 | Who assembles `PriceModel` — `collapse_terms` returns a 2-tuple, the carrier needs a third field from the basis version | **P** | Name it in task 2 or 5: `int(basis.cost_per_worker_minute_minor.scaleb(4))`, and the `None` branch ⇒ status `item_missing_purchase_cost`, all three blocks `null` |
| L5 | The one-copy rule cannot be satisfied with public names: `_median`, `_step_state_is_excluded` are private, `divide_production_budget` is forbidden by C14 | **P + F** | Decide and record: import the two private helpers (precedent exists for `_load_preview_inputs` only, and only in tests for `budget_division`), or grant the inline form explicitly. Note `state in EXCLUDED_STEP_STATES` is **not** equivalent to `_step_state_is_excluded` |
| L6 | `suggested_price_minor = ceil_to_step(B, domain.step_minor)` is undefined when `domain` is `null` and `B` is not — reachable | **I + P** | §4.4 gains the branch (`null`, matching `domain`); a criterion is added — **`suggested_price_minor` currently has no criterion in either phase** |
| L7 | C6 says `anchors` **absent**; §3.5/§4.1/§12.5 publish `is_fundable: false` and `break_even: null`, i.e. the block present | **P** | Restate C6: `anchors` present with `break_even_price_minor: null`, `is_fundable: false`; `domain: null`. Absence is for the block, not its members |
| L8 | Nothing in plan 2 assigns the load of the committed `ItemCostEvaluation`, yet `ok`, `infeasible` and `item_binding` all require it | **P + F** | Task 1 names it; grant the composition choice (call `get_task_budget_status`, precedent `get_task_production_time.py:26`, or load it directly) |
| L9 | Where `serialize_task_price_scenario` is called — the two router precedents differ, and the router-side one **breaks an existing test** | **P** | Decide in task 8. If router-side, §2's perimeter for `test_item_economics_router.py` widens beyond "one row at `:14`" |
| L10 | C13's identity assertion has no host test: the `_ROUTES` parametrizations assert status + call count only | **P** | Name the host (a new function in `test_item_economics_router.py`) and record it in §2 |
| L11 | C11's "a withheld monetary key is **absent**, never null" is not decidable — the route 403s, so no payload exists | **P** | Drop the second sentence, or restate as "no worker/seller variant is mounted", which C12 already proves |
| L12 | The **empty** participating set (no steps, or every section excluded): `any()` over ∅ is `False`, so `is_estimated: false` beside `total_seconds: 0` | **I** | §5.3A gains the empty case: `is_estimated = sections_total == 0 or any(not usable)`. C6's fixture is then stated as non-empty and a separate empty row added |
| L13 | A participating section with **no row** from `typical_times_statement` (its `WorkingSection` is deleted) | **P** | One sentence in task 3: build the map with `.get()`; `sections_total` counts sections derived from **steps**, never from the statement's rows |
| L14 | `can_commit`'s two formulations in §9A.2 disagree after a configuration drift | **I** | The block form (live selection) governs; delete or qualify the "equivalently: A1, A2, B7, B10" clause. C2 states the predicate is computed from the live selection |
| L15 | C10 says `404` and C9 says `200`, but the only new test file is a **service-level** integration test | **P** | Restate as the service-level outcome (`NotFound`, precedent `test_production_time_query.py:272`), or add a route-level file to §2 — a perimeter change |
| L16 | The mirror test's docstring `:9` reads "the same **23** rows" — already stale by two | **P** | Add to §2's note beside the function name at `:123`; same artifact, no perimeter extension |
| L17 | C17/N6 has no landing point inside this perimeter | **P** | Say in the plan that the assertion is **not** extended, rather than leaving it to the handoff: a purity assertion cannot bind an I/O module, and editing `test_price_scenario.py` beyond §2's two exceptions is a scope breach |

---

## 3. The ledger rows in detail

Only the rows whose reasoning is not obvious from the table.

### L2 — §9.2 and §9A.1 collide on every occurrence

Read at `get_task_budget_status.py:111`:

```python
binding = "detached" if item is None else ("bound" if evaluation is None or evaluation.item_id == item.client_id else "mismatched")
```

- **`mismatched`** requires `evaluation is not None`, so the branch always continues into
  `_build_evaluated_status` (`:127`) and the status is always `ok` or `infeasible` (`:150`).
  §9A.1 rows A1/A2 say `model`/`anchors`/`domain` are **present**; §9.2 says all `null`.
- **`detached`** means `item is None`. Either `evaluation is None` too — status
  `not_evaluated` (`:114`), §9A.1 row B10, **present** — or an evaluation exists and the
  status is `ok`/`infeasible`, again **present**. §9.2 says `null` on both paths, and it is
  the only one that can be honoured: with no `Item` there is no category, no selection, no
  quantity and therefore no model, anchors or band.

So this is not an edge case where two rules *may* disagree; on both binding values they
disagree every time. §9.2 must be declared to win, and the declaration belongs in the
intention, not in the plan.

Undefined on the same two paths, and needed by the serializer on the first request:

- `item` — for `detached` there is no `Item` row at all. §8's payload types `item` as an
  object with four keys and no section makes it nullable. `null` is the only available
  answer; it needs saying.
- `typical` — computable from steps alone, so it can be populated; §9.2 does not say
  whether it should be.
- `status`, `can_commit`, `config_fingerprint` — all derivable (`can_commit` is `false` for
  `detached` because condition 3 fails; `config_fingerprint` is `null` because the model
  is), but derivable is not the same as decided.

C9 currently asserts four keys. It should assert the full row for each binding value.

### L3 — B6/B7 "present" is not total

`resolve_item_economics_status` (`configuration.py:144-168`) walks
`ITEM_READINESS_PRECEDENCE`, which places `ITEM_UNVALUED` and
`ITEM_MISSING_EXPECTED_PRICE` **above** `ITEM_MISSING_PURCHASE_COST`. So:

- no valuation row + a non-deleted `item_purchase_cost` term ⇒ status `item_unvalued` (B6),
  and `collapse_terms(terms, None)` returns `None` (`price_scenario.py:90-91`);
- a valuation with `expected_sale_price_minor = NULL` **and** `purchase_cost_minor = NULL`
  + a purchase term ⇒ status `item_missing_expected_price` (B7), same `None`.

§9A.1 marks both rows **present**, with the reason "configuration fully resolved; only the
price is missing". The purchase cost is missing too, and the status vocabulary cannot say
so because a higher-precedence check has already fired. C1's B6 and B7 rows are therefore
satisfiable only for a cost model **without** a purchase term — which makes the expected
outcome a property of the fixture rather than of the status, exactly what rule 2's
companion forbids.

Note this does not reopen D8 or D9. Under D9's flow the purchase price is set first, which
creates the valuation row and makes the model collapsible; the contradiction bites only
where D9's precondition — the one master plan §8 obligation 6 exists to write down — does
not hold. It is a contract-text correction, not a lived failure.

### L4 — the assembly nobody owns

`collapse_terms` returns `tuple[int, int] | None` (`price_scenario.py:63`). `PriceModel`
(`:26-31`) carries three fields. The third,
`cost_per_worker_minute_ten_thousandths`, comes from
`selection.basis_version.cost_per_worker_minute_minor` — a `Numeric(12,4)` `Decimal`,
canonicalised by §3.1B as `int(value.scaleb(4))`, and guaranteed positive by
`ck_pcbv_cost_per_worker_minute_minor_positive` (`production_cost_basis_version.py:38`).

Plan 2 §3 never says "call `price_scenario.py`", and master plan §4 registers the twelve
public names without saying which the query service uses. Phase 1's own projection raised
this and it was delegated as D-1 with an instruction to register the names at closeout;
the registration happened, but registering the names did not assign the *composition*. The
result is that the single most load-bearing line of this phase — turning ORM rows into the
carrier every published number derives from — is in no task and in no criterion.

Also unassigned: the `None` return. Task 5 lists `item_missing_purchase_cost` among the
seven `null` rows, so the branch is implied, but the plan never connects the `None` to it.

### L5 — the one-copy rule versus the module's `__all__`

Master plan §4: *"the participating-section rule and the median fallback are **imported**
from `budget_division.py` … A second copy of a registered mechanism is a review finding."*

What is actually importable (`budget_division.py:402-411`): `EXCLUDED_STEP_STATES`,
`TYPICAL_*`, `DivisionStep`, `divide_production_budget`, `group_steps_by_section`.

- The **participating set** is not a function. It is the comprehension at `:309-313`,
  built from `group_steps_by_section` (public) and `_step_state_is_excluded` (`:209-210`,
  private, not exported), inside `divide_production_budget` — which C14 forbids calling.
- The **median fallback** is `_median` (`:69-74`), private, not exported.

Three routes, all with a cost, and the plan picks none:

1. import the private names — no precedent in production code (`get_task_production_time.py`
   imports only public names; the only cross-module private import in a service is
   `_load_preview_inputs`, which plan 2 task 2 mandates anyway). Precedent does exist in
   tests: `test_production_time_query.py:12` imports `_section_sort_key`;
2. reimplement — a review finding by master plan §4's own words;
3. use `EXCLUDED_STEP_STATES` and write the membership test inline. **This is not
   equivalent**: `_step_state_is_excluded` compares `_state_value(...)`, i.e. `.value`
   strings, so it tolerates a step whose `state` is a plain string. For ORM `TaskStep` rows
   the two agree today; the divergence is silent and would appear the first time a caller
   passes a `DivisionStep`.

Whichever is chosen, it is a decision, and per the skill it should be granted in writing
rather than taken.

### L6 — the anchor with no criterion, and its undefined branch

`anchors.suggested_price_minor` appears in §8's payload, is derived by §4.4 and §4.4A, is
one of the mockup's seven rendered elements (`suggested 2 025/piece`) — and has **no
acceptance criterion in plan 1 (C1–C22) or plan 2 (C1–C17)**. Phase 1 shipped
`ceil_to_step`; nothing anywhere pins the composition
`ceil_to_step(break_even, step_minor)`.

Its branch is also undefined. §4.4 gives `null` only when `break_even_price_minor` is
`null`, but §7A.1 makes `domain` `null` whenever `min_minor >= max_minor` — reachable with
a non-`null` `B`. Measured against the shipped module: `PriceModel(100_000, 0, 10_000)`
(rate `1.0000` minor/minute — legal under `Numeric(12,4)` and `CHECK > 0`) with
`typical_total_seconds = 60` gives `break_even_price_minor = 1`,
`infeasible_at_or_below_minor = 0`, and `slider_domain(1, 6, 0) is None`. Thirty-four such
(rate, residual, `T`, `Q`) combinations were found in a small sweep.

The corner is degenerate — it needs `B < 80·Q`, i.e. a break-even under about five kronor
— and it is unguarded: an implementer following §4.4 literally writes
`ceil_to_step(B, domain.step_minor)` and gets an `AttributeError` on a `null` `domain`,
which is a 500 where the contract wants a `null`.

### L9 — the composition point decides whether an existing test goes red

Two live precedents in the same router:

- `production-time` (`item_economics.py:371-383`) uses `_run` (`:130`), and the **service**
  serializes (`get_task_production_time.py:82`);
- `budget-status` (`:361-367`) uses `_run_budget_status` (`:135-146`), and the **router**
  serializes.

`test_item_economics_router.py`'s `fake_run_service` (`:63-87`) returns `{"ok": "test"}` for
every command it does not recognise, and returns a hand-built `TaskBudgetStatus` for the two
budget-status commands **precisely because** the router serializes those. So if phase 2
serializes router-side, adding the new row to `_ROUTES` (`:14`) makes
`test_every_item_economics_route_retains_admin_and_manager_access` (`:110-118`, expects
`200`) feed `{"ok": "test"}` into `serialize_task_price_scenario`, and the fake must be
extended too — a change to that file beyond the one row §2 authorises. If the service
serializes, the row is genuinely one line and nothing else moves.

This is the clearest example of the class this gate exists to catch: the plan looks
complete, and the decision that determines whether its declared perimeter is accurate is
not in it.

### L10 — C13 has no host

C13 requires `calls[0][0] is get_task_price_scenario`. The identity precedent it cites lives
in `test_budget_status_route_is_available_to_all_roles` (`:135`, `:138`, `:141`, `:143`),
which is parametrized over `_ALL_ROLE_ROUTES` — the list §2 correctly says this route must
**not** join. The two parametrizations over `_ROUTES` assert `403` + `calls == []` (`:100-107`)
and `200` + `len(calls) == 1` (`:110-118`); neither asserts identity. So C13 needs a new
test function, in a file §2 describes as a one-row edit.

*(Minor: C13 cites the precedent as `:133`. That is the `if` that opens the block; the
assertions are at `:135`–`:143`. Not a defect, but the line moves if anyone edits above it.)*

### L14 — `can_commit`'s two formulations

§9A.2 gives a block form computed from the **live** selection, then says *"Equivalently:
`can_commit` is true exactly for statuses A1, A2, B7 and B10."*

They are not equivalent. A1/A2 are produced by `_build_evaluated_status`
(`get_task_budget_status.py:150`) from the **committed** evaluation and never consult
`resolve_item_economics_status`, so a task that was committed while the configuration was
healthy keeps status `ok` after the cost model version is deleted or its `effective_to`
passes (`configuration.py:52-61` compares against `today_utc()`). The live selection is then
B5, `commit_item_cost_evaluation` refuses at `:229-230`, and the status form publishes
`can_commit: true` for a button whose press is a guaranteed error — the exact failure §11
names and the reason D4 made this field load-bearing.

The block form is the correct one and is the one the plan should cite. C2's "one row per
condition, each fixture violating only its own condition" is satisfiable under the block
form and **not** under the status form, where the configuration conditions are unreachable
for an A1 fixture.

### L12 — the empty participating set

§5.3A's contract is written per section:

```
is_estimated = any participating section is not usable
```

With no participating sections — a task with no steps, or one whose every section's steps
are all in `EXCLUDED_STEP_STATES` (both reachable; the second is C5's own fixture family) —
`any()` over the empty set is `False`. The published block is then
`total_seconds: 0, is_estimated: false, sections_without_sample: 0, sections_total: 0`,
which the screen renders as a *measured* typical of zero. §5.3's no-evidence contract
("`typical_total_seconds` is `0`, `is_estimated` is `true`") and C6 both assert the opposite,
and neither notices that they are describing a non-empty set.

Downstream this is contained — `T = 0` makes `break_even_price_minor` return `None`
(`price_scenario.py:144`) and the slider is suppressed — so the damage is confined to one
boolean that says "measured" about nothing. That is precisely a rule‑6 silent failure: the
number looks plausible and is wrong.

---

## 4. Reality checks

### 4.1 Paths in `plan_2.md` §2 — all nine resolve

| Path | State |
|---|---|
| `services/queries/item_economics/get_task_price_scenario.py` | absent, correctly marked **new** |
| `domain/item_economics/serializers.py` | exists |
| `routers/api_v1/item_economics.py` | exists |
| `tests/unit/routers/test_phase9_item_economics_route_mirror.py` | exists |
| `routers/README.md` | exists |
| `tests/unit/routers/api_v1/test_item_economics_router.py` | exists |
| `tests/integration/services/queries/item_economics/test_price_scenario_query.py` | absent, correctly marked **new** |
| `tests/unit/domain/item_economics/test_price_scenario.py` (exception 1) | exists |
| `domain/item_economics/calculator.py` (exception 2) | exists |

### 4.2 HC-2a's line numbers — re-read at head, all correct

The prompt flagged these as unverified since the intention was written. They have not moved.

| Citation | At head `d32bdf4` |
|---|---|
| `_EXPECTED_ROUTES` `:33` | `_EXPECTED_ROUTES = (` — ✓ |
| count assertions `:126`, `:127` | `assert len(_EXPECTED_ROUTES) == 25` / the dedup assertion — ✓ |
| the test function name `:123` | `def test_the_registry_ships_twenty_five_routes()` — ✓ |
| `_ROUTES` `:14` | ✓ (22 rows) |
| `_ALL_ROLE_ROUTES` `:48` | ✓ (3 rows; 22 + 3 = 25, consistent with both counts) |
| README Quick Index block `:58-82` | first and last item-economics rows — ✓ |

**One defect found in the same artifact** (L16): the module docstring at `:9` reads *"Two
arbiters over the same **23** rows"*. It is stale by two already, and it is the same class
of defect as the function name §2 carries — a comment that lies where a future route author
looks first. Same file, so no perimeter extension.

### 4.3 Cited code — read at the line

| Cited by | Claim | Verdict |
|---|---|---|
| plan 2 task 3 / §5.3A | participating set at `budget_division.py:309-313` | ✓ the `allocated_groups` comprehension |
| §5.3A | `usable` at `:327` | ✓ `typical is not None and _as_fraction(typical) > 0` |
| §5.3A | `_median` at `:69-74`, mean of two middles | ✓ |
| §5.3A | median substitution at `:333-335` (cited `:317-335`) | ✓ |
| §2A | `EXCLUDED_STEP_STATES` `:19-25` | ✓ |
| plan 2 task 2 | `_load_preview_inputs` `_common.py:172-216` | ✓ returns `(selection, terms)`; terms ordered `created_at, client_id` at `:213` |
| §9A.2 cond. 1–5 | `:113-114`, `:115-116`, `:126-127`, `:135-136`, `:229-230` | ✓ (§9A.2 writes `:228-230`; the `if` is at `:229`) |
| §9A.2 asymmetry | `:212-213` — `effective = None` when no valuation | ✓ |
| §6B | `_load_current_valuation` `:176-184` | ✓ (with `FOR UPDATE`, which this endpoint correctly must not copy) |
| §2A | `_ADMITTED_STATES` `:60-68` | ✓ |
| §2.6 | `serialize_user_light` `cases/serializers.py:102-108` | ✓ |
| master plan §4 | `_shape_error` duplicates `calculator.py:124-128` | ✓ verbatim, including the message string |
| §2A.1.3 | `cost_per_worker_minute_minor` CHECK at `production_cost_basis_version.py:38` | ✓ |
| §8A.1 | `ItemValuation.CLIENT_ID_PREFIX == "ival"` | ✓ `item_valuation.py:15` |
| plan 2 C13 | identity precedent `test_item_economics_router.py:133` | ✓ block opens at `:133`, assertions `:135-143` |

**Dependencies on phase 1 verified in the code, not assumed:** the twelve registered public
names all exist and are exported (`price_scenario.py:214-231`); `digits` is public in the
module but registered internal, and nothing in phase 2 needs it; `slider_domain` takes
`(break_even_minor, quantity, infeasible_minor)` and returns `None` for a `None` `B`
(`:187-188`), which is the total form plan 1 task 8 promised; `break_even_price_minor` takes
`(model, typical_total_seconds)` and carries both null conditions (`:144`);
`infeasible_at_or_below_minor` takes `(model)` and returns `SEARCH_CAP_MINOR` at the cap
(`:152`). The phase‑1 file is green: **53 passed** on `tests/unit/domain/item_economics/test_price_scenario.py`.

### 4.4 Architecture graph

Status: initialized, valid, 184 nodes / 276 edges, 0 diagnostics, 6 pending reviews,
revision `42c184f3…`. `source-file-item-economics-price-scenario` exists, `ai_inferred`,
**pending**, production evidence anchored `price_scenario.py:14-211` with no `symbol` on that
entry — matching §6 of the prompt exactly, including the N9 correction.
`projection-item-economics-task-price-scenario` returns no match: **free for this phase's
endpoint**, as recorded. Nothing was written to the graph by this session.

---

## 5. Criteria decidability

Per the skill: could I write the test today, from the artifacts alone, with one exact
expected outcome per case?

| C | Decidable now? | Blocker |
|---|---|---|
| C1 | **No** | L2 (binding rows), L3 (B6/B7 fixture-dependent). Also: "present" needs saying — under a degenerate model or `T = 0`, `domain` is `null` while the status is `ok`, so the five present rows need fixtures with a fundable model, stated |
| C2 | **No** | L14 — which formulation the predicate comes from |
| C3 | Yes | Reachable: five qualifying groups with `total_working_seconds = 0` give `sample_count = 5`, `percentile_cont = 0`, `typical_worker_seconds = 0` — not `NULL` (`get_working_section_typical_times.py:43-46`) |
| C4 | Yes, with effort | The fixture is constructible (two usable typicals differing by an odd amount, e.g. `100`/`101` ⇒ median `100.5` ⇒ `round_half_even(201,2) = 100` per section, `401` total against `402` under sum-quantisation — the "exactly one second" the criterion claims). Each usable section needs its own ≥ 5 qualifying groups, so the fixture is heavy but exact |
| C5 | Yes | The all-deleted-steps section is decidable: `group_steps_by_section` filters `is_deleted` (`:116-117`), so the section produces no group and does not participate |
| C6 | **No** | L7 (absent versus present-with-nulls) and L12 (the empty set) |
| C7 | Yes | §6B's three rows are exact; `currency` reads `.value` per `serialize_item_valuation` precedent |
| C8 | Yes | §9A.3 is complete: full ids, fixed order, `v{CALCULATION_VERSION}`, `null` with a null model |
| C9 | **No** | L2 — the criterion asserts four keys of a row that is otherwise undefined |
| C10 | Partly | Decidable as `NotFound` at service level (precedent `test_production_time_query.py:272`); "404" is not observable in the declared file — L15 |
| C11 | Half | The `403` half is automatic from the `_ROUTES` parametrization. The absent-key half is not decidable at all — L11 |
| C12 | Yes | Plus L16's docstring |
| C13 | **No** | L10 — no host test exists |
| C14 | Yes | An import- or monkeypatch-level assertion that `divide_production_budget` is not called; the module is importable and public |
| C16 | **No** | L1 — as written the assertion cannot fail |
| C17 | Yes, trivially | The compliant answer is "not extended" — L17 |
| C15 | Yes | Precedent is `try/finally` with an explicit `_cleanup` (`test_budget_allocations_query.py`), and the baseline drift caveat is already in master plan §6 |

**Unwritten criterion:** `anchors.suggested_price_minor` (L6). It is a published key and one
of the mockup's seven elements, and no criterion in either phase asserts it.

---

## 6. Method notes, so the evidence can be re-run

- Every number in §1 was computed twice — once from a reference implementation transcribed
  from §7A.1 without reading `price_scenario.py`, once by `exec`-ing the real module source
  with `divisor = max(1, quantity)` replaced by `divisor = max(6, quantity)` in memory. The
  working tree was never mutated; `git status` is clean.
- L6's reachability came from a bounded sweep over legal `(rate_ten_thousandths, residual,
  K, T, Q)` values against the shipped functions, not from an argument.
- The suite was **not** run whole. Master plan §6's instability (25/26/27 with byte-identical
  ID sets) makes a single run non-evidence, and this session changed nothing that could move
  it. The one file I did run — `test_price_scenario.py`, 53 passed — was run to confirm the
  module I mutated in memory is the one at head, not to measure a baseline.
- Per §6 of the prompt, phase 1's arithmetic was composed, not re-derived. Nothing in this
  ledger is a finding against it.

## 7. Write perimeter

From `git status --porcelain --untracked-files=all` and `git diff --name-only` at close:

```
?? docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_phase2_projection_r0_handoff.md
```

One file: this handoff. No code, no test, no plan, no intention, no `.archgraph` write, and
no skeleton retained — the paper derivation was discarded per the skill, and nothing in this
document is implementation guidance.

## 8. Exit gate

`AMENDMENTS_REQUIRED`. Seventeen ledger rows: **four** upstream to the intention (L2, L3,
L12, L14 — plus the two halves of L6), **eleven** plan amendments, **two** written
delegations to grant (L5, L8). Every row must be routed — amendment applied, upstream change
made, or delegation recorded — before the implementer prompt compiles.
