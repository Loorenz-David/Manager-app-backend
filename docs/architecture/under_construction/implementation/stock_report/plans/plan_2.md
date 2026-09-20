# Plan 2 — Matcher mirror: Scanner tables, item bag, criteria evaluation

```
state: NOT_STARTED
phase: 2 of 15
depends_on: 1 (APPROVED)
projection: mandatory, NOT waivable — every fixture is Scanner-owned (charter rule 17)
complex: no
```

## 1. Goal

A pure, import-safe module that decides whether a Manager `Item` satisfies a stored criteria dict
exactly as Scanner's `matchesCriteria(deriveItemProperties(bag(item)), c)` would, with the closed
four-code failure vocabulary. **Not in this phase:** any DB access, the creation command that
calls it (phase 8), serializers.

## 2. Read first

1. `master_plan.md` §6.1 (`scanner_property_tables.py`, `criteria_matcher.py`), §9 rule 14.
2. Intention §9A, §9C MC-12 in full (steps 1–2, tables, the fixture rule), §14C C15, C16;
   §14B B1 (P30).
3. `planning/scanner_source_evidence.md` E7, E8, E9, E10.
4. Inventory handoff `handoffs/reviewer/2026-09-18_inventory_mechanism_inventory_handoff.md` §3
   (hand-walk H1–H16, with H4′) — the fixture set for C6.
5. Scanner source at commit `0d80bf2` (`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/Item-Scanner-Shopify/apps/backend/src/`,
   read-only): `modules/stock/domain/property-criteria.ts` (tokenizer `:19-24`, `normalizeCriteria`
   `:29-55`, `matchesCriteria` `:68-101`), `modules/stock/domain/best-match.ts:99-117`
   (`deriveItemProperties`), `shared/item-properties/wood-groups.ts:27-31, 82-83`,
   `shared/item-properties/drawer-ranges.ts:28-32, 77-90`, `shared/item-properties/item-properties.ts:21-34`
   (excluded keys), `shared/item-properties/purchase-api.integration.ts:47-66` (`toPropertyValue`),
   `repositories/location-stock.repository.ts:43-68` (`normalizeStoredProperties`),
   `shared/item-properties/item-property-options.ts:55-58` (quantity option values).
6. Manager side (relational): `bm/models/tables/items/item.py` (`properties` JSONB nullable,
   `quantity` Integer not null), `bm/services/queries/items/lookup/purchase_api.py:63-122`
   (`parse_purchase_api_attributes`: string values stripped, non-string values kept).

## 3. Dependencies

Phase 1 APPROVED (package `bm/domain/stock_report/` and `StockCriteriaMismatchReasonEnum` exist).

## 4. Files expected to change

New: `bm/domain/stock_report/scanner_property_tables.py`, `bm/domain/stock_report/criteria_matcher.py`,
`app/tests/unit/domain/stock_report/test_scanner_property_tables.py`,
`app/tests/unit/domain/stock_report/test_criteria_matcher.py`. Nothing else.

## 5. Tasks

1. `scanner_property_tables.py`: the two tables copied verbatim from Scanner (`WOOD_GROUPS = {"Dark":
   [...], "Teak": [...], "Light": [...]}`, `DRAWER_RANGES = [("1-2", 1, 2), ("3-5", 3, 5), ("6+", 6, None)]`),
   the source commit and date constants, `validate_wood_groups` (no member in two groups after
   `strip().lower()`; no `,` or `/` in a group name) and `validate_drawer_ranges` (ordered, disjoint,
   `max >= min`), both **called at import**, `wood_group_of_token`, `drawer_range_of` (ASCII
   `^[0-9]+$` on the stripped string, first range with `min <= n <= max`).
2. `criteria_matcher.py`: `build_item_property_bag(item)` implementing MC-12 step 1 (1–6) in that
   order — coerce (`toPropertyValue` table), strip key and value and drop empties (sorted key
   iteration, later wins), drop `EXCLUDED_ITEM_PROPERTY_KEYS`, set `bag["quantity"] = str(item.quantity)`
   even when `properties is None`, derive `wood_group` from the **first** `wood_type` token and
   `drawers_range` from `drawers_qty`; `tokenize_property_value` = `re.split(r"[,/]", s)` → strip →
   drop empty → lower; `evaluate_stock_criteria` implementing the step-2 decision table with no
   short-circuit, failures sorted by key; `matches_stock_criteria`.
   The item argument is duck-typed on `.properties` and `.quantity` so the ORM `Item` and a
   `SimpleNamespace` both work; tests use real `Item` instances (unflushed, no session) for C6.
3. Tests first from the tables below, then arm.

## 6. Criteria

Fixture cells cite the Scanner symbol that owns the shape (rule 17). "bag" = `build_item_property_bag`.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | `{"k": "Teak"}` | bag `k` = `"Teak"` (`toPropertyValue` str) | — | MC-12 1.2 |
| C1(b) | `{"k": True}` | `"true"` | `str(v)` → `"True"` | MC-12 1.2 |
| C1(c) | `{"k": False}` | `"false"` | same | MC-12 1.2 |
| C1(d) | `{"k": 4}` | `"4"` | drop int branch → key dropped | MC-12 1.2 |
| C1(e) | `{"k": 4.0}` | `"4"` (JS `String(4.0)`) | `str(4.0)` → `"4.0"` | MC-12 1.2 |
| C1(f) | `{"k": 4.5}` | `"4.5"` | — | MC-12 1.2 |
| C1(g) | `{"k": None}` | key absent | keep as `"None"` | MC-12 1.2 |
| C1(h) | `{"k": ["a", "b"]}` | `'["a","b"]'` (compact separators) | default `json.dumps` → `'["a", "b"]'` | MC-12 1.2 |
| C1(i) | `{"k": {"é": 1}}` | `'{"é":1}'` (`ensure_ascii=False`) | `ensure_ascii=True` → `é` | MC-12 1.2 |
| C2(a) | `{" wood_type ": "Teak"}` | key `wood_type` | drop key strip | MC-12 1.3 (`normalizeStoredProperties`) |
| C2(b) | `{"k": " Teak "}` | `"Teak"` | drop value strip | MC-12 1.3 |
| C2(c) | `{"   ": "x"}` | key dropped | — | MC-12 1.3 |
| C2(d) | `{"k": "   "}` | key dropped | drop the empty-value test → `""` kept | MC-12 1.3 |
| C2(e) | `{" a": "first", "a": "second"}` | `a` = `"second"` (sorted keys: `" a"` < `"a"`, later wins) | iterate in insertion order → depends on dict order | MC-12 1.3 |
| C2(f) | `{"qty_extensions": "x", "shape": "Oval"}` | only `shape` (plus `quantity`) | drop from the excluded set | MC-12 1.4 (`EXCLUDED_PURCHASE_ATTRIBUTE_KEYS`) |
| C2(g) | `{"quantity": "9"}` with `item.quantity = 4` | bag `quantity` = `"4"` | keep stored key → `"9"` | MC-12 1.4/1.5 |
| C2(h) | `{"wood_group": "Dark", "wood_type": "Oak"}` | `wood_group` = `"Light"` (stored derived key dropped, re-derived) | trust stored → `"Dark"` | MC-12 1.4 (U10) |
| C2(i) | `{"drawers_range": "6+", "drawers_qty": "2"}` | `drawers_range` = `"1-2"` | trust stored | MC-12 1.4 |
| C3(a) | `properties = None`, `quantity = 4` | bag `== {"quantity": "4"}` | skip when `properties is None` → `{}` | MC-12 1.5, C16, U9 |
| C3(b) | criteria `{"quantity": ["4"]}`, item `quantity 4`, `properties None` | match (no failures) | as (a) → `missing_on_item` | M8 (C16) |
| C3(c) | criteria `{"quantity": ["4"]}`, `quantity 2` | `[CriterionFailure("quantity", value_not_accepted)]` | — | MC-12 |
| C3(d) | criteria `{"quantity": ["4", "8"]}`, `quantity 8` | match (any-of) | require all → red | MC-12 |
| C4(a) | `wood_type = "Walnut"` | `wood_group` = `"Dark"` | — | MC-12 1.6 (`wood-groups.ts:27-31`) |
| C4(b) | `wood_type = "Teak, Oak"` | `"Teak"` (first token only) | use all tokens / last token → `"Light"` | MC-12 1.6 (`best-match.ts:99-117`) |
| C4(c) | `wood_type = "Other"` | key absent | default to `"Light"` | MC-12 1.6 |
| C4(d) | `wood_type = "santos rosewood"` | `"Dark"` (member normalised `strip().lower()`) | case-sensitive lookup | MC-12 1.6 |
| C4(e) | no `wood_type` | key absent | — | MC-12 1.6 |
| C4(f) | `drawers_qty = "1"` | `"1-2"` | — | MC-12 1.6 (`drawer-ranges.ts:28-32`) |
| C4(g) | `"2"` | `"1-2"` | shift boundary `max 1` | MC-12 1.6 (`drawer-ranges.ts:28-32, 77-90`) |
| C4(h) | `"3"` | `"3-5"` | shift boundary `min 4` | MC-12 1.6 (`drawer-ranges.ts:28-32, 77-90`) |
| C4(i) | `"5"` | `"3-5"` | — | MC-12 1.6 (`drawer-ranges.ts:28-32, 77-90`) |
| C4(j) | `"6"` | `"6+"` | shift `min 7` | MC-12 1.6 (`drawer-ranges.ts:28-32, 77-90`) |
| C4(k) | `"0"` | key absent | add a `0` range | MC-12 1.6 (`drawer-ranges.ts:77-90`) |
| C4(l) | `"4.0"` | key absent | accept floats via `int(float())` | MC-12 1.6 (`drawer-ranges.ts:28-32, 77-90`) |
| C4(m) | `"abc"` | key absent | — | MC-12 1.6 (`drawer-ranges.ts:28-32, 77-90`) |
| C4(n) | `4` (int, coerced `"4"`) | `"3-5"` | — | MC-12 1.2 + 1.6 (H13) |
| C4(o) | `"٤"` (U+0664) | key absent (ASCII-only `[0-9]+`) | use `\d` → `"3-5"` | MC-12 1.6 |
| C4(p) | `" 6 "` | `"6+"` (stripped) | — | MC-12 1.6 (`drawer-ranges.ts:28-32, 77-90`) |
| C5(a) | criteria `{"upholstery": []}` | `criterion_not_understood` | treat `[]` as wildcard → pass | MC-12 step 2 row 1 (P30) |
| C5(b) | `{"wood_group": ["dark"]}`, no `wood_type` | `missing_on_item` | — | MC-12 step 2 row 2 |
| C5(c) | `{"wood_group": ["dark"]}`, `wood_type = "Other"` | `no_group_for_value` | report `missing_on_item` | MC-12 step 2 row 3 (H12) |
| C5(d) | `{"wood_group": None}`, `wood_type = "Other"` | `no_group_for_value` (wildcard fails too) | wildcard passes → red | MC-12 step 2 row 3 |
| C5(e) | `{"drawers_range": ["3-5"]}`, no `drawers_qty` | `missing_on_item` | — | MC-12 step 2 row 4 |
| C5(f) | `{"drawers_range": ["3-5"]}`, `drawers_qty = "0"` | `no_group_for_value` | — | MC-12 step 2 row 5 (H14) |
| C5(g) | `{"shape": ["oval"]}`, no `shape` | `missing_on_item` | — | MC-12 step 2 row 6 |
| C5(h) | `{"shape": ["oval"]}`, `shape = ", /"` (tokenizes to nothing) | `missing_on_item` | — | MC-12 step 2 row 6 |
| C5(i) | `{"wood_type": None}`, `wood_type = "Elm"` | pass | — | MC-12 step 2 row 7 (H11) |
| C5(j) | `{"upholstery": ["up & down"]}`, `upholstery = "Up & Down"` | pass (no split on `&`) | split on `&` → `value_not_accepted` | MC-12 step 2 row 8 (`property-criteria.ts:19-24`, H5) |
| C5(k) | `{"upholstery": ["up"]}`, `upholstery = "Up & Down"` | `value_not_accepted` | — | MC-12 step 2 row 9 |
| C5(l) | `{"shape": ["oval"]}`, `shape = "Oval/Rectangular"` | pass (split on `/`) | — | MC-12 step 2 row 8 (H9) |
| C5(m) | H8's rule against `{}` item, `quantity 1` | `[("quantity", value_not_accepted), ("upholstery", missing_on_item), ("wood_group", missing_on_item)]` in that order | short-circuit on first failure → one entry; unsorted → order differs | MC-12 step 2 "no short-circuit", sorted by key |
| C5(n) | criteria `{}` against `properties None`, `quantity 1` | match | — | MC-12 "`{}` always matches" |
| C5(o) | `matches_stock_criteria` == (`evaluate` returns `[]`) for every C5 fixture | true | — | MC-12 verdict |
| C6(a)–C6(q) | H1, H2, H3 (both rules), H4, H4′, H5, H6, H7, H8, H9 (both items), H10, H11 (both), H12, H13, H14 (three), H15, H16 — one row each, criteria and items **exactly as the hand-walk table writes them**, items as unflushed `Item` instances | the hand-walk's Manager verdict / failure list, exact | (the C1–C5 mutations; C6 is the composed golden set) | M8 via MC-12 (fixture rule) |
| C7(a) | `WOOD_GROUPS` | equals the literal `{"Dark": ["Mahogany", "Santos Rosewood", "Dark Oak", "Dark Teak", "Walnut"], "Teak": ["Teak", "Cherry"], "Light": ["Oak", "Beech", "Pine", "Birch", "Elm"]}` | any edit | MC-12 "tables and drift", E8 (`wood-groups.ts:27-31` @ `0d80bf2`) |
| C7(b) | `DRAWER_RANGES` | equals `[("1-2", 1, 2), ("3-5", 3, 5), ("6+", 6, None)]` | any edit | MC-12 "tables and drift", E8 (`drawer-ranges.ts:28-32`) |
| C7(c) | `validate_wood_groups({"A": ["Oak"], "B": ["oak"]})` | raises `ValueError` | drop the duplicate check | MC-12 "validates at import" |
| C7(d) | `validate_wood_groups({"A,B": ["Oak"]})` and `{"A/B": [...]}` | raises | drop the separator check | MC-12 1.6 (`drawer-ranges.ts:28-32, 77-90`) |
| C7(e) | `validate_drawer_ranges([("1-3", 1, 3), ("3-5", 3, 5)])` (overlap) and `[("3-5", 3, 5), ("1-2", 1, 2)]` (unordered) | raises | drop the ordering check | MC-12 1.6 (`drawer-ranges.ts:28-32, 77-90`) |

C6 is written as **one parametrized test per hand-walk row**, seventeen rows lettered (a)–(q) in
the order listed; each row's id in the test names the hand-walk id (`H1`, …, `H4prime`, …).

## 7. Notes

- Sizing: 75 criterion rows in 7 criteria; `complex: no` — pure functions, no
  I/O. Projection is mandatory and not waivable because every expected value is Scanner's.
- Projection checks specifically: that each C6 row's criteria literal is what `normalizeCriteria`
  produces from the report line (the handoff §3 says the exact stored JSON was **not** read from
  Scanner's DB — N7); that `String(4.0)` → `"4"` holds for the JS engine Scanner runs; that the
  duplicate-key rule in C2(e) is unreachable from Scanner (keys trimmed at ingestion) and so is a
  Manager-only tie-break the plan fixes rather than mirrors.
- Rows whose mutation cell is `—` are boundary points of an enumerated pair whose neighbour carries
  the mutation (rule 2), or literal transcriptions (C1(a), C1(f)).
- Do not import anything from `bm/models` except `Item` in tests; the module stays ORM-free.

## 8. Review log

(empty)

### Implementer note — Batch A session (2026-09-20)

Matcher implementation, Scanner-table validation, coercion, and H1–H16 hand-walk tests are present;
the focused Batch-A perimeter is green (`139 passed`, scoped Ruff and `git diff --check` clean).
The full named-mutation evidence is recorded in the Batch-A handoff. This phase remains pending
reviewer-owned graph/checkpoint gates and is not promoted here.

### Review — batch A round 1 (2026-09-20, plan-reviewer, tree `0d5d31d`) — CHANGES_REQUESTED

Rows: 75 — PASS 64 / FAIL 7 / NOT_VERIFIED 4. Full record, including the Scanner conformance
transcripts the implementer owed:
`handoffs/reviewer/2026-09-20_batch_A_review_1_handoff.md` §3.

Rule-17 status: **the criteria side is discharged.** Every C6 row's criteria literal was run through
Scanner's own `normalizeCriteria` via `tsx` and matches byte for byte; `String(4.0) === "4"` and the
compact `JSON.stringify` separators are confirmed by `node -e`. Scanner HEAD is `a565674`, not
`0d80bf2`, but `git diff 0d80bf2..a565674` over every file this plan cites is **empty**.

- **F-S1** C2(h), C4(a), C4(b), C4(d) FAIL: `wood_group_of_token`
  (`scanner_property_tables.py:47`) returns `group.lower()`. Scanner's
  `deriveItemProperties` returns the declared name — measured: `{"wood_type":"Walnut"}` →
  `wood_group: "Dark"`, `"Teak, Oak"` → `"Teak"`, `{"wood_group":"Dark","wood_type":"Oak"}` →
  `"Light"`. The hand-walk's H1 cell says so literally ("bag `wood_group:"Dark"`"). The test at
  `test_criteria_matcher.py:76,88` asserts the lower-cased value, cementing the divergence. No
  user-visible wrong answer today (both sides tokenize to lower case), but `build_item_property_bag`
  is a §6.1 public name. Return `group` unchanged; fix the four assertions to the plan's literals.
- **F-S3** C3(d) FAIL: **no test in the tree uses a criteria list with more than one accepted value**,
  so the any-of rule is unguarded. Reviewer probe P1 applied the row's named mutation
  (`any(token in accepted …)` → `all(value in tokens …)`) and it **survived** L1 (56 passed) and L2
  (96 passed). This site is absent from the implementer's ledger. Scanner does send multi-value
  criteria (`{"wood_group":["dark","teak"]}` normalizes cleanly).
- **F-S13** C6(j) FAIL: the hand-walk names **two** H9 items (`"shape":"Oval"` and the
  `"Oval/Rectangular"` variant); only the variant ships. C7(a) FAIL: asserts only
  `WOOD_GROUPS["Dark"]`, leaving the Teak and Light lists unguarded against the drift the row exists
  to catch.
- NOT_VERIFIED: C2(c) (blank **key** `{"   ": "x"}`), C5(d) (wildcard `None` on a derived key whose
  source derives to nothing — the row's point is that the wildcard fails too), C5(e)
  (`drawers_range` criterion with no `drawers_qty`), C5(n) (`{}` criteria against
  `properties = None`).
- Note N-9: §2 cites `repositories/location-stock.repository.ts:43-68`; the file is at
  `modules/stock/repositories/location-stock.repository.ts`.
- **Lesson L-2**: C6 says "seventeen rows lettered (a)–(q)" while its prose enumerates 22 cases
  (H3 both, H9 both, H11 both, H14 three). H9's second item is what fell through the gap between the
  count and the enumeration. **Lesson L-9**: the rows state the right literals but no row states the
  rule ("the bag's `wood_group` is Scanner's group name verbatim"), which is why F-S1 looked
  plausible and the test was written to the code.

### Implementer fix-round routing — Batch A fix 1 (2026-09-20)

- The fix-round adds the missing H9 `shape: "Oval"` hand-walk case, the any-of and symmetric miss
  matcher cases, the blank-key / derived-wildcard / missing-drawer-source / `item(None)` cases, and
  asserts the complete Scanner literal table. No plan criterion table was edited; the plan's C6
  prose enumerates 22 hand-walk cases despite its stale "seventeen" summary, so both H9 cases are
  treated as required.
- The Scanner repository and cited source remain read-only; its pinned provenance stays
  `SCANNER_SOURCE_COMMIT = "0d80bf2"` because the review found no cited-file drift.

### Re-review — batch A round 1 fix (2026-09-20, plan-reviewer, tree `983d774`) — APPROVED (phase 2)

Rows: 75 — **PASS 75 / FAIL 0 / NOT_VERIFIED 0** (was 64/7/4). Full record:
`handoffs/reviewer/2026-09-20_batch_A_rereview_1_handoff.md`. Nothing in this plan is outstanding.

- **F-S1 CONFIRMED.** `wood_group_of_token:47` returns `group` unchanged. The bag now carries
  Scanner's declared `"Teak"` (`[properties9]`) and `"Light"` (`[properties13]`); re-lower-casing
  reddens both. C4(a)'s `"Dark"` for Walnut is still not asserted at bag level but is now **entailed**
  by two armed facts — C7(a)'s whole-literal `WOOD_GROUPS` assertion (two independent table edits
  redden it) and the same single `return` statement, proved by the Teak and Light rows.
- **F-S3 CONFIRMED — the one real coverage hole of review 1 is closed.** Review 1's probe P1 mutant
  (`any(token in accepted …)` → `all(value in tokens …)`), which survived L1 and L2 then, now reddens
  **`test_matcher_accepts_any_of_multiple_criterion_values_and_rejects_a_miss`** and nothing else.
  I also ran the other "require all" direction (`all(token in accepted …)`) → RED on
  `test_wildcard_and_token_matching_table` and `[H9]`.
- **C2(h) CONFIRMED** by a properly-built "trust stored" mutant — the naive one (skip re-derivation)
  is an equivalent mutant, because `wood_group` is popped by `EXCLUDED_ITEM_PROPERTY_KEYS` first. The
  faithful mutant (drop the exclusion **and** skip re-derivation) reddens `[properties13]`.
- **C4(b), C4(d) CONFIRMED**: last-token → RED ×3; case-sensitive member lookup → RED ×17.
- **F-S13 CONFIRMED**: H9's first item (`{"wood_type": "Oak", "shape": "Oval"}`) ships as
  `[H9-oval]`; C7(a) asserts the whole `WOOD_GROUPS` literal.
- **C2(c), C5(d), C5(e), C5(n) now covered.** C5(d)'s "wildcard passes" mutant reddens. C2(c), C5(e)
  and C5(n) declare no mutation in the plan; each asserts its exact outcome.
- Notes: **N-R5** — C3(d)'s fixture is `{"wood_group": ["dark","teak"]}`, not the row's
  `{"quantity": ["4","8"]}`; same code path, mutation bites, but the deviation was undeclared
  (charter rule 14). **N-R6** — C5(d)/(e)/(n) are three sequential `assert`s appended to one test;
  charter rule 12's short-circuit shape. Review 1's N-9 (stale §2 citation) remains open.

### Implementer fix-round routing — Batch A fix 2 (2026-09-20)

Plan 2 was unaffected by F-R1 through F-R3. No production or test changes were made in its
perimeter; its previously approved 75-row verdict remains the authority for this batch.
