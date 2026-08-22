# Plan 5 — Price-scenario: the injected clock, the shared reconciliation, `is_estimated`

```
plan: plan_5
project: narrow_typical_work_times
state: NOT_STARTED
projection_gate: MANDATORY
```

## 1. Goal

Bring the fourth consumer onto the shared engine: `_typical_block` moves to the **injected
request clock**, computes its participating set through `participating_sections`, consumes the
shared reconciliation instead of its private ladder, keeps `terminal = Fraction(0, 1)`, and
publishes `typical_resolution` — with `is_estimated`, `sections_total` and
`sections_without_sample` defined under **§6B**, whose whole point is that the value does
**not** change.

**Explicitly NOT in this phase:** no change to division, to production-time, to
budget-allocations, to `ALLOCATION_METHOD`, to any golden, or to
`/working-sections/typical-times` — which **keeps its own wall-clock read** (D24), the one
place where "extend the determinism contract" is the wrong instinct. No
`/statistics/typical-times` route.

## 2. Read first

- Master plan §§4, 6.2, 6.5, 7, 9, 10.
- Intention **header**, then §2.1 (price-scenario's row), §2A (the clock split, verbatim),
  §2B S-6, S-7, §3.6, §3B B2, §4.3, **§4A K1** in full, §4.5, §6.1, §6.2 row 4, §6.4
  (**SUPERSEDED on `is_estimated` by §6B**), **§6B** in full, §7.4, §8, §11.1 rows
  T4/T6/T7/T14/T21, **§11A** T27 and the correction to §8.
- `planning/owner_decisions.md` — D14, D19, D22, D24.
- Gate handoff §2 rows 6, 9, 14 and **§5 item 3** (the ratified clock move).
- **Neighbouring authority, at source:**
  `docs/architecture/archives/live_clock_for_working_time_economics/planning/intention.md`
  §1A **HC-3A** — and specifically the sentence this phase lapses: the default wall-clock read
  is justified only as *"the compatibility shim for its callers **outside this pipeline** (the
  working-sections surface and the price-scenario typical block, both settled-basis and out of
  scope)"*.
- `plans/plan_4.md` §6 C11 and its Review log (T6's first half).
- Code: `get_task_price_scenario.py` (whole file — `_typical_block` at `:100-179`,
  `get_task_price_scenario` at `:184-315`); `domain/item_economics/serializers.py:364` (the
  typical pass-through); `domain/item_economics/price_scenario.py`;
  `tests/integration/services/queries/item_economics/test_price_scenario_query.py` — **read
  `_TypicalSession` before writing a test.**

## 3. Dependencies

**Gate: plan 4 `APPROVED`.** C5 asserts equality against production-time's payload, which plan
4 ships. The spec comes from plan 3's `TaskBudgetStatus` or from the item price-scenario
re-loads itself (§6.2 row 4, `:196`).

## 4. Files expected to change

**Modified**
- `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py`
- `app/beyo_manager/domain/item_economics/serializers.py` (the `typical` block gains
  `typical_resolution`; it imports `serialize_typical_resolution` from
  `division_serializers.py` — **one implementation, not a second**)

**New**
- `app/tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py`

**Modified — tests**
- `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py`

**Read-only, and a change is a finding**
- `get_working_section_typical_times.py` · `budget_division.py` ·
  `get_task_production_time.py` · `get_task_budget_allocations.py` · all three goldens.

## 5. Ordered tasks

1. **The clock moves to `ctx.now`** (§4A K1, ratified 2026-08-22).
   `_typical_block` calls `typical_times_statement(ctx.workspace_id, now=ctx.now, specs=…)`.
   `ServiceContext.now` is always present (`context.py:24`, `default_factory`), so this is a
   one-line argument; **no payload key moves.**
   *Why*: HC-2 requires every task-scoped consumer to observe identical layer-1 evidence
   **including counts**. The 90-day cutoff is clock-derived, so two surfaces reading the clock
   at different instants can straddle the boundary for a group whose `max(closed_at)` sits at
   it, and disagree on `sample_count` and therefore on the median — an HC-2 violation with no
   error, and it makes C5 undecidable.
   **`/working-sections/typical-times` keeps the default.** It is task-free, HC-2 does not bind
   it, and D24 requires it byte-identical. Do not "make it consistent".
2. **Derive the spec.** From the active PRIMARY `Item` price-scenario already loads
   (`:195-196`), or equivalently from `budget_status.typical_filter_spec` (plan 3). Use one
   source and say which in a comment. Pass `specs=()` when the spec is non-narrowing (§4A K3).
3. **Participating set via `participating_sections`** (§6.1). `_typical_block` keeps its step
   query and its own participating computation, but the **predicate** is the shared one — the
   current inline `any(not _step_state_is_excluded(step) …)` becomes a call.
   **§2B S-7 is load-bearing here**: price-scenario scopes the statement to the
   **participating** sections only, where production-time scopes it to every step's section.
   That difference is contract, not drift, and C5 asserts it.
4. **Consume the shared reconciliation.** Build `SectionTypicalEvidence`, call
   `reconcile_task_typicals`, and **drop the private ladder as a rule**. Resolution goes
   through `apply_business_fallback(..., terminal=Fraction(0, 1))` — a **duration**;
   averaging would fabricate time inside a number managers read as an estimate, and
   `0` + `is_estimated: true` is the honest answer (D22).
5. **`is_estimated` per §6B — the contract, verbatim:**
   ```
   is_estimated := (participating_section_count == 0)
                   OR (layer 2 fired for >= 1 participating section)
   ```
   The `participating_section_count == 0` disjunct is **retained verbatim**. Only the second
   disjunct's *definition* is clarified: "layer 2 fired" means the **selected** typical was
   `None` or `<= 0` for that section — exactly the set `sections_without_sample` counts today,
   **so the value is unchanged in every case**.
   §6.4's genuine content survives intact: reconciling to `section_wide_uniform` **alone** does
   not set the flag.
   *Read §6.4 literally and you ship a behaviour change*: defined as exactly "layer 2 fired for
   ≥ 1 participating section", a task with **zero** participating sections has zero such
   sections, so `is_estimated` becomes **False** where today it is **True**, beside
   `total_seconds: 0` — a manager reading "measured, and it is zero" instead of "estimated".
   §6B is the correction; T27/C2(a) is its guard.
6. **The two existing fields, defined under the new regime** (§6B): `sections_total :=
   participating_section_count` (meaning unchanged); `sections_without_sample` := the count of
   **participating** sections whose **selected** typical is `None` or `<= 0`. Under
   `section_wide_uniform`, a section with a usable section-wide value is **not** counted even
   though its narrowed sample was thin. The tempting misreading — "sections without a
   *narrowed* sample" — silently re-scopes a published field.
7. **§7.4:** add `typical_resolution` (the same object as §7.2) to the `typical` block. It
   serializes through the existing pass-through at `serializers.py:364` — note §2B S-6:
   `:353` is the item block's `"label"`, not the typical pass-through.
8. Tests per §6. Record the architecture-graph delta. Update the tracker row and the Review log.

## 6. Tests / acceptance criteria

Hypothesis scope: L1 = `test_narrowed_price_scenario.py` / `test_price_scenario_query.py`.
C5 and C7 name cross-file bite sets and run at L2 =
`tests/integration/services/queries/item_economics/`; C7's sweep row is an **absence claim** at
**L4** with its root and terms stated.

**⚠ Fixture rule for this whole phase.** `test_price_scenario_query.py`'s `_TypicalSession`
(`execute(self, _statement)` discards the statement and pops pre-built results) means **eight
existing `_typical_block` tests never issue SQL**, and none of that query's predicates can be
observed through them. **Before citing any test in this phase as proof of a SQL-level or
clock-level behaviour, check that it issues SQL.** Every row below that constrains the
statement call runs against a real session.

**C1 — the clock, in both directions.**
(a) `_typical_block` calls `typical_times_statement` with `now=ctx.now` — asserted through a
spy that **delegates**.
(b) **Determinism**: a task whose history contains a group with `max(closed_at)` placed
**exactly at the 90-day boundary** relative to a frozen `ctx.now`, served twice at two
different wall-clock instants with the **same** frozen `ctx.now` over identical database state
→ the serialized `typical` block is **byte-identical** across the two calls.
(c) `get_working_section_typical_times` calls the statement with **no** `now` argument (D24),
and its payload is unchanged.
*Mutations, one per sub-check*:
(i) `get_task_price_scenario._typical_block` (call site): drop the `now=` argument → **rows
(a), (b)** flip: the cutoff derives from a wall-clock read, the boundary group falls on
different sides of it in the two calls, and `sections_without_sample` / `total_seconds` differ
between them.
(ii) `get_working_section_typical_times` (call site): pass `now=ctx.now` → **row (c)** flips.
*Both sides* — row (b) contract: two identical JSON strings; mutation: two strings differing in
`total_seconds`.
*Why (c) exists*: this phase extends an APPROVED pipeline's determinism contract to a fourth
surface that pipeline deliberately excluded. Extending it to a **fifth** would break D24's
byte-identity requirement. The two rows are opposite directions and both are contract.

**C2 — `is_estimated`, one row per disjunct (§6B, T27).**
| # | fixture | `is_estimated` | also |
|---|---|---|---|
| a | a task whose every section is excluded → participating set empty | `true` | `total_seconds: 0`, `sections_total: 0` |
| b | ≥1 participating section whose **selected** typical is `None` | `true` | `sections_without_sample >= 1` |
| c | ≥1 participating section whose **selected** typical is `0` | `true` | the `<= 0` half |
| d | every participating section has a usable selected value, on a **`section_wide_uniform`** task | `false` | `sections_without_sample: 0` |
*Mutations, one per row*:
(i) `_typical_block` (definition): drop the `sections_total == 0` disjunct → **row (a)** flips
`true` → `false` beside `total_seconds: 0`. Rows (b)–(d) do not bite.
(ii) `_typical_block` (definition): define the second disjunct as "participating sections
without a **narrowed** sample" → **row (d)** flips `false` → `true` (its narrowed samples are
thin, which is why the task is `section_wide_uniform`). Rows (a)–(c) do not bite.
(iii) `_typical_block` (definition): change the layer-2 trigger `<= 0` to `< 0` → **row (c)**
flips `true` → `false`. Rows (a), (b), (d) do not bite.
(iv) `_typical_block` (definition): set the flag whenever `task_typical_basis ==
"section_wide_uniform"` → **row (d)** flips `false` → `true`; this is §6.4's genuine content
asserted as a **negative**.
*Both sides* — exact boolean literals beside their `total_seconds` and `sections_without_sample`
values.

**C3 — `sections_total` and `sections_without_sample` keep their published meanings (§6B).**
Fixture: 3 participating sections — one usable, one selected-`None`, one selected-`0` — plus 1
excluded section.
Assert `sections_total == 3` (**participating** only, not 4) and `sections_without_sample == 2`.
*Mutations, one per sub-check*:
(i) `_typical_block` (definition): count every section in `selected` for `sections_total` →
contract `3`; mutation `4`.
(ii) `_typical_block` (definition): count narrowed-thin participating sections for
`sections_without_sample` → contract `2`; mutation `3` (the usable section's narrowed sample is
thin on this fixture).

**C4 — T4 row (b): the price terminal, and it does not converge with division's.**
(a) No usable typical anywhere in the task → `total_seconds: 0` and `is_estimated: true`.
(b) A mixed task — participating selected values `600`, `900`, and one `None` → the unusable
section takes the in-task median: `total_seconds == 600 + 900 + 750 == 2250`.
*Mutations, one per sub-check* — both at `_typical_block`'s `apply_business_fallback` call site:
(i) pass `terminal=Fraction(1, 1)` → **row (a)** flips `total_seconds` `0` → `3` (one second
per participating section). Row (b) does not bite — with usable values present the terminal is
never reached.
(ii) return the terminal instead of the median when usable values exist → **row (b)** flips
`2250` → `1500`.
*Both sides* — exact integer literals.
*Note*: `Fraction(1,1)` is division's terminal because `0` starves a section **and** because
`0` makes `total_weight` zero and raises; `Fraction(0,1)` is price-scenario's because a
fabricated average inflates a number managers read as an estimate. **The docstring records that
the difference is intentional and must not converge** (D22, §8).

**C5 — HC-2 complete (T6b): all three surfaces agree, and the set restriction is itself
asserted.**
For one task at one frozen `ctx.now`, on a fixture with a **participating** section and an
**excluded** section that both have typicals:
(a) per participating section, price-scenario's contribution and production-time's
`(typical_worker_seconds, typical_basis, sample_count)` agree — exact literals on both sides,
never an equality between two calls;
(b) `price_scenario.total_seconds == Σ` of the resolved values over the **participating** set
only — division renders excluded groups, price-scenario does not;
(c) the same triple equals budget-allocations' step row (closing the three-way agreement plan 4
C11 opened).
*Mutation* — `_typical_block` (call site): compute over all of `selected` instead of the
participating set → **row (b)** flips: contract `total_seconds == 1500`; mutation `2100` (the
excluded section's typical joins the sum).
*Second mutation* — `get_task_price_scenario` (call site): resolve typicals locally instead of
through the shared selection → **rows (a), (c)** flip: contract `(540, "item_narrowed", 7)`;
mutation `(600, "section_wide", 61)`.

**C6 — `typical_resolution` on §7.4 is the same object as §7.2, by construction.**
(a) The serialized `typical_resolution` key set from price-scenario equals the **exact
frozenset literal** `{"task_typical_basis", "reconciliation_method", "comparability_profile",
"applied_filter", "participating_section_count", "sections_by_basis"}`.
(b) The same exact frozenset literal is asserted for production-time's block in the same test.
(c) For the same task and frozen `now`, both blocks' values equal the same **literals** —
`task_typical_basis == "item_narrowed_uniform"`, `applied_filter == {"item_category_ids":
["icat_chair"]}`, `participating_section_count == 3`.
*Mutation* — `domain/item_economics/serializers.py` (definition): build the price-scenario
block with a private builder instead of importing `serialize_typical_resolution`, omitting
`comparability_profile`.
*Both sides* — contract: the six-key frozenset on both surfaces; mutation: five keys on
price-scenario.
*Assertion-form note*: two literal assertions, **not** `price_keys == production_keys` — an
equality between two calls is invariant under a mutation that changes both, and this project's
lineage has shipped four inert checks of exactly that shape.

**C7 — HC-1: no consumer forks the statistic.**
*Presence form (automated, and the one the verdict rests on)*: `_typical_block` computes no
median of its own — it calls `apply_business_fallback` **exactly once** and contains no
`Fraction`-median construction, no `percentile` computation and no comparison against
`TYPICAL_MIN_SAMPLE_SIZE`. Asserted by reading the function's source and by a spy on
`apply_business_fallback`.
*Absence sweep (L4, reviewer-verified, root = repository root, terms stated)*: `percentile_cont`
· `TYPICAL_MIN_SAMPLE_SIZE` · `_median` · `median(`. Expected: hits only in
`typical_constants.py`, `typical_filters.py`, `get_working_section_typical_times.py`,
`budget_division.py` and enumerated test files. Any other hit is a fork.
*Mutation* — `_typical_block` (definition): reintroduce the private `usable` / `_median(usable)`
ladder → the spy records zero `apply_business_fallback` calls and the source assertion fails.
*Why the presence form is primary*: the corpus rule — *record the search terms beside an
absence claim, or restate it as the presence claim it is standing in for*. A directory-wide
"no median anywhere" claim was published as verified in this lineage once and was wrong,
defeated by the codebase's own wrapper.

## 7. Notes

- **The accepted duplication stays.** `get_task_price_scenario` deliberately re-reads task,
  item, valuation and preview inputs that `get_task_budget_status` already loaded (~8 redundant
  round trips), and the comment at `:184-195` records why. This phase does not collapse it —
  that is a different change with a different justification.
- **`_typical_block` keeps its own step query.** §6.2 row 4 says so: it keeps the step query
  and the participating computation, now via §6.1, and drops only the **ladder**.
- **The comment block at `get_task_price_scenario.py:105-121` is a claim, and it inherits rule
  2.** It asserts which of three `WHERE` predicates are load-bearing, and the lineage paid four
  rounds establishing it. If this phase changes that query at all, the comment is re-verified
  by dropping each predicate, not preserved on faith.
- **A cross-reference from production code must resolve from a clean checkout with no pipeline
  documents present.** No criterion IDs, round numbers, mutation nicknames or bare line numbers
  in comments — the house convention is `path:symbol`.
- **Architecture-graph delta expected**: `projection-item-economics-task-price-scenario` (its
  clock and its typicals path). One batched `apply_changes`; **no counts in evidence
  summaries**; symbol anchors preferred over line spans, but never both on one entry. That node
  has drifted twice in this lineage — **re-derive its span from the symbol, never trust the
  stored one.**

## 8. Review log

*(empty — append-only; shared by implementer and reviewer)*
