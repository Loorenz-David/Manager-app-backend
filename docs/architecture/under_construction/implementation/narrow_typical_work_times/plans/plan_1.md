# Plan 1 — The pure typicals domain, and the pre-refactor SQL snapshot

```
plan: plan_1
project: narrow_typical_work_times
state: NOT_STARTED
projection_gate: MANDATORY
```

## 1. Goal

Build the whole **pure** typicals engine — spec, profile, evidence, policy, resolution,
reconciliation, business fallback, participating-set — as one SQL-free domain layer with
no production caller, and **capture the pre-refactor compiled SQL string of
`typical_times_statement` while the tree is still pre-refactor**.

**Explicitly NOT in this phase:** no change to `typical_times_statement`'s body or
signature; no `_typical_item_filter.py`; no consumer wiring; no payload change; no
serializer change; no change to `divide_production_budget`'s signature or to
`ALLOCATION_METHOD`; no golden regeneration. The three constants **move** modules but keep
their values and every existing import site.

## 2. Read first

- Master plan §§4, 6, 7, 9, 10 (naming registry, sequencing, standing rules, environment
  and evidence budgets).
- Intention **header** (the section-letter precedence rule), then §3.1–§3.7, **§3A**,
  **§3B**, §4.1, §4.3, **§4B**, **§4C**, §4.5, §6.1, §8, §9 (the deferred statistics
  contract), §11.1 rows T3/T5/T7/T9/T10/T11/T12/T13/T14/T17/T20/T21, **§11A** in full.
- `planning/owner_decisions.md` — D4, D6, D11, D12, D13, D15, D16, D17, D19, D22, **D25**.
- `handoffs/reviewer/20260822_mechanism_inventory_gate_handoff.md` §2 rows 3, 7, 8, 14, 15,
  16 and §5.
- Code: `app/beyo_manager/domain/item_economics/budget_division.py` (constants,
  `EXCLUDED_STEP_STATES`, `_step_state_is_excluded`, `_median`, `_as_fraction`, `_value`,
  `__all__`); `app/beyo_manager/models/tables/items/item.py`;
  `app/beyo_manager/models/tables/item_economics/…/item_category.py`;
  `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
  (read only — the snapshot's subject).

## 3. Dependencies

None. This is the first phase. The tree must be at the D23 baseline (master plan §10)
before the snapshot is captured.

## 4. Files expected to change

**New**
- `app/beyo_manager/domain/item_economics/typical_constants.py`
- `app/beyo_manager/domain/item_economics/typical_filters.py`
- `app/tests/unit/domain/item_economics/test_typical_filters.py`
- `app/tests/unit/domain/item_economics/test_participating_sections.py`
- `app/tests/unit/services/queries/working_sections/__init__.py` (if the package needs it)
- `app/tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py`
- `app/tests/unit/services/queries/working_sections/snapshots/typical_times_no_spec_sql.txt`

**Modified**
- `app/beyo_manager/domain/item_economics/budget_division.py` — import + re-export the
  three constants; add `participating_sections`. **No other executable line changes.**

Anything else is a finding.

## 5. Ordered tasks

1. **Capture the snapshot FIRST, before touching anything else.** Compile
   `typical_times_statement(workspace_id="ws_snapshot")` against the PostgreSQL dialect
   **without `literal_binds`** and write the string verbatim to
   `snapshots/typical_times_no_spec_sql.txt`. Compile it again with `now=<a fixed
   datetime>` and assert the two strings are equal before writing — the cutoff enters as a
   bound parameter, so the compiled string is `now`-independent (§4A K5). If they are not
   equal, **stop and report**: K5's reasoned-not-measured claim has failed and every
   downstream HC-4 criterion rests on it.
2. Move `TYPICAL_METHOD`, `TYPICAL_WINDOW_DAYS`, `TYPICAL_MIN_SAMPLE_SIZE` into
   `typical_constants.py` verbatim. Import them back into `budget_division.py` and keep all
   three in its `__all__` (already present, `budget_division.py:402-410`) so **no existing
   import site changes**. Master plan §6.1 records why.
3. `TypicalFilterSpec` with the seven fields of §3.1 and `__post_init__`
   canonicalization per **§3A C1**: empty collection → `None`; `(None, None)` **kept**;
   `lo > hi` raises `ValueError`. `is_narrowing` is exactly "at least one field is not
   `None`". The frozen dataclass's own field-wise `__eq__`/`__hash__` **is** the dedupe key.
   **No hash, digest or fingerprint anywhere.**
   Docstring the `(None, None)` form explicitly: it means **"the dimension is recorded"**,
   not "no constraint" (§3A C2) — an implementer reading it as a no-op writes `TRUE` and the
   population silently doubles.
4. `COMPARABILITY_PROFILE`, `derive_spec_from_primary_item` (§3.2), and
   `parse_spec_from_query_params` with the parameter names fixed in master plan §6.8.
5. `SectionTypicalEvidence` (§3.3) with `has_narrowed`, `has_section` and **`has_usable_narrowed`**
   (§4C). `has_narrowed` stays §3.3's pure count predicate. Floors read
   `TYPICAL_MIN_SAMPLE_SIZE`, never a literal.
6. `TypicalResolutionPolicy` and `resolve_section_typical` (§3.4 as amended by §4C, §3B B1,
   §3.6, §3B B3). The ladder, total over (has_usable_narrowed, has_section) × policy:
   `BROADEN_TO_SECTION` prefers a **usable** narrowed value (floor met **and** median `> 0`),
   else the section rung, else insufficient; `ANSWER_AS_ASKED` is **deliberately unchanged**
   — it answers the narrowed question as asked and a sufficient-count median of `0` **is**
   the honest answer. The asymmetry is the two policies' whole point.
   **`spec.is_narrowing is False` short-circuits first**, without consulting the narrowed
   columns at all (§3B B1).
7. `SelectedTypical`, `TaskTypicalSelection`, `reconcile_task_typicals` (§4.3 as amended by
   §4C, §3B B4). The quantifier quantifies **`has_usable_narrowed`**, and the participating
   set must be **non-empty** — `all()` over an empty set is vacuously true and would emit
   `item_narrowed_uniform` for a task with no participating sections. Excluded sections
   resolve **independently** through `resolve_section_typical(..., BROADEN_TO_SECTION)` and
   never influence the task basis. Every emitted `typical_worker_seconds` is identically an
   integer the SQL produced — never a product or ratio of two of them.
8. `apply_business_fallback` (§8) with the signature in master plan §6.2 and an
   `isinstance(terminal, Fraction)` **entry guard that fails closed** (§11A T14). Usable =
   not `None` and `> 0`. Docstring: the two terminals are `Fraction(1,1)` for division and
   `Fraction(0,1)` for price-scenario, **the difference is intentional and must not
   converge**, and `Fraction(1,1)` is additionally a **division-by-zero guard** — with
   `terminal = 0` and no usable typical anywhere, every weight is 0, `total_weight` is 0,
   and `budget_division.py:338-343`'s `… / total_weight` raises (§11A's correction to §8).
   Output of this function never reaches a serializer.
9. `participating_sections(steps)` in `budget_division.py` (§6.1): sections with ≥1 step
   outside `EXCLUDED_STEP_STATES`, over non-deleted steps. Reuse `_step_state_is_excluded`
   and `_value`; do not write a second predicate.
10. Tests per §6. Every helper added has a test caller in this phase (charter rule 4).
11. Update the master plan tracker row and this file's Review log.

## 6. Tests / acceptance criteria

Each criterion names the defect it catches. Mutations state **file · definition-vs-call-site**
and **both sides**. Every named mutation runs before submitting, at hypothesis scope (L1:
`test_typical_filters.py`, `test_participating_sections.py`, `test_typical_times_sql_identity.py`).

**C1 — empty collections canonicalize to `None`, one row per collection field.**
Rows: `item_category_ids`, `major_categories`, `designers`, each constructed with
`frozenset()`.
Assert per row: `spec == TypicalFilterSpec()`, `hash(spec) == hash(TypicalFilterSpec())`,
`spec.is_narrowing is False`.
*Mutation* — `typical_filters.TypicalFilterSpec.__post_init__` (definition): delete the
empty-collection normalization.
*Both sides* — contract: `spec == TypicalFilterSpec()` → `True`, `is_narrowing` → `False`.
Mutation: `==` → `False` (`frozenset()` vs `None`), `is_narrowing` → `True`.
*Defect caught*: a parse producing an empty collection becomes a narrowed population of 0
that `BROADEN_TO_SECTION` silently answers section-wide — HC-3's shape.

**C2 — `lo > hi` is rejected at construction; `lo == hi` is not.** One row per range field
(`width_cm`, `height_cm`, `depth_cm`) × two boundary rows.
(a) `(81, 80)` → `pytest.raises(ValueError)`. (b) `(80, 80)` → constructs, `is_narrowing True`.
*Mutations, one per sub-check (rule 12)* — both in `__post_init__` (definition):
(i) delete the range validation → **row (a)** flips: contract raises, mutation constructs.
Row (b) does not bite on (i) — recorded.
(ii) tighten the guard to `lo >= hi` → **row (b)** flips: contract constructs, mutation
raises. Row (a) does not bite on (ii) — recorded.
*Defect caught*: an empty band makes `narrowed_sample_count = 0` for every section, which
`BROADEN_TO_SECTION` answers section-wide with no signal that the question was unanswerable.

**C3 — `(None, None)` is kept and is narrowing.**
Assert `TypicalFilterSpec(width_cm=(None, None)).is_narrowing is True` and
`!= TypicalFilterSpec()`.
*Mutation* — `__post_init__` (definition): normalize `(None, None)` to `None`.
*Both sides* — contract `is_narrowing` `True`; mutation `False`.
*Defect caught*: "the dimension is recorded" silently becomes "no constraint" and the
population doubles.

**C4 — the spec is the dedupe key, and there is no hash anywhere.**
(a) `len({TypicalFilterSpec(item_category_ids=frozenset({"a","b"})),
TypicalFilterSpec(item_category_ids=frozenset({"b","a"}))}) == 1`.
(b) two specs meaning different populations stay `2`.
(c) **absence, module-scoped, terms stated**: reading the source of `typical_filters.py`,
none of the tokens `hashlib`, `sha1`, `sha256`, `md5`, `fingerprint`, `digest` appears.
*Mutation* — `TypicalFilterSpec` (definition): declare the dataclass `eq=False`.
*Both sides* — contract (a) `1`; mutation (a) `2`.
*Defect caught*: two specs meaning the same population become two `spec_index` values (a
redundant scan and a mis-keyed row), or two different populations collapse into one — the
Critical-ranked dedupe-identity mechanism.

**C5 — `derive_spec_from_primary_item` is total, on real ORM instances (rule 3).**
Rows: (a) `item is None` → `TypicalFilterSpec()`; (b) an `Item` instance with
`item_category_id is None` → `TypicalFilterSpec()`, `is_narrowing False`; (c) an `Item`
instance with a category → `TypicalFilterSpec(item_category_ids=frozenset({that_id}))`.
*Mutation* — `derive_spec_from_primary_item` (definition): return a non-empty spec for
category-less items.
*Both sides* — contract row (b) `is_narrowing` `False`; mutation `True`. (T3's mutation.)

**C6 — the three evidence predicates, at the floor boundary, per population.**
Counts are written as `TYPICAL_MIN_SAMPLE_SIZE - 1` and `TYPICAL_MIN_SAMPLE_SIZE`, never as
`4` and `5` (rule 13).
Rows: (a) narrowed count floor−1 → `has_narrowed False`; (b) floor → `True`; (c) section
count floor−1 → `has_section False`; (d) floor → `True`; (e) narrowed count floor, median
`0` → `has_usable_narrowed False` while `has_narrowed True`; (f) narrowed count floor,
median `1` → `has_usable_narrowed True`; (g) narrowed count floor−1, median `600` →
`has_usable_narrowed False`.
*Mutations, one per sub-check* — all in `SectionTypicalEvidence` (definition):
(i) `has_narrowed`: `>=` → `>` — **rows (b), (e), (f)** flip `True`→`False`; row (a) does not.
(ii) `has_usable_narrowed`: drop the `> 0` conjunct — **row (e)** flips `False`→`True`; rows
(f), (g) do not.
(iii) `has_usable_narrowed`: `> 0` → `>= 0` — **row (e)** flips; recorded as a second shape
of the same sub-check because `>= 0` is the likelier slip than deletion.
*Defect caught*: D25 — a section whose narrowed history is all zeros declared "known", so
the least-informative section decides the basis for every other section on the task.

**C7 — `resolve_section_typical` is total over (has_usable_narrowed, has_section) × policy,
plus the non-narrowing short-circuit.** One row per cell; each row's fixture makes its own
predicate the only reason its outcome holds.
| # | spec | narrowed (count, median) | section (count, median) | policy | expected basis / seconds / sample_count |
|---|---|---|---|---|---|
| a | narrowing | (7, 540) | (61, 600) | BROADEN | `item_narrowed` / `540` / `7` |
| b | narrowing | (7, **0**) | (61, 600) | BROADEN | `section_wide` / `600` / `61` |
| c | narrowing | (2, None) | (61, 600) | BROADEN | `section_wide` / `600` / `61` |
| d | narrowing | (2, None) | (3, None) | BROADEN | `insufficient_sample` / `None` / `3` (§3B B3) |
| e | narrowing | (7, 540) | (61, 600) | AS_ASKED | `item_narrowed` / `540` / `7` |
| f | narrowing | (7, **0**) | (61, 600) | AS_ASKED | `item_narrowed` / **`0`** / `7` (§4C: deliberately unchanged) |
| g | narrowing | (2, None) | (61, 600) | AS_ASKED | `insufficient_sample` / `None` / `2` (§3.6) |
| h | **non-narrowing** | (61, 600) — equal to section by construction | (61, 600) | BROADEN | `section_wide` / `600` / `61` |
| i | **non-narrowing** | (3, None) | (3, None) | BROADEN | `insufficient_sample` / `None` / `3` |
*Mutations, one per sub-check* — all in `resolve_section_typical` (definition):
(i) collapse the two policy branches → **row (g)** flips `insufficient_sample`/`None` →
`section_wide`/`600`. (T12/T13.)
(ii) consult `has_narrowed` before checking `spec.is_narrowing` → **row (h)** flips
`section_wide` → `item_narrowed`. (T23/§3B B1; **T3 does not constrain this** — T3 asserts
numeric identity and these are new string fields.)
(iii) in the `BROADEN_TO_SECTION` first rung, test `has_narrowed` instead of
`has_usable_narrowed` → **row (b)** flips `section_wide`/`600` → `item_narrowed`/`0`. Rows
(e)–(g) do not bite on (iii) — the `ANSWER_AS_ASKED` branch is deliberately untouched.
(iv) return `narrowed_sample_count` for row (d)'s `sample_count` → **row (d)** flips `3` → `2`.
*Defect caught, row f vs row b*: the two policies must diverge on **identical evidence** —
economics prefers usable values, analytics reports the asked statistic. A single shared
branch is HC-3.

**C8 — `reconcile_task_typicals`: the quantifier, and the empty participating set.**
| # | fixture | expected `task_typical_basis` |
|---|---|---|
| a | 2 participating, both `has_usable_narrowed` | `item_narrowed_uniform`, both take narrowed values |
| b | A: narrowed count 5, median **0**; B: narrowed count 7, median 600 | **`section_wide_uniform`**, both take section-wide values (T10b′) |
| c | A: narrowed count 3 (below floor); B: usable | `section_wide_uniform` (T10a) |
| d | participating set **empty**, one excluded section with usable narrowed evidence | `section_wide_uniform` |
| e | 2 participating all usable-narrowed + 1 **excluded** section that is thin | `item_narrowed_uniform`; the excluded row shows its **section-wide** value (T9) |
| f | mirrored: participating on `section_wide_uniform` + a well-sampled narrowed **excluded** section | `section_wide_uniform`; the excluded row shows `item_narrowed` |
| g | **non-narrowing** spec | `section_wide_uniform`, `applied_filter is None` |
*Mutations, one per sub-check* — all in `reconcile_task_typicals` (definition):
(i) `all(...)` → `any(...)` → **row (b)** flips `section_wide_uniform` →
`item_narrowed_uniform` (and A's row becomes `0`/`item_narrowed`). Row (a) does not bite.
(ii) quantify `has_narrowed` instead of `has_usable_narrowed` → **row (b)** flips; **row (c)
does not** (its count is below the floor either way) — recorded per rule 12.
(iii) drop the `participating non-empty` conjunct → **row (d)** flips `section_wide_uniform`
→ `item_narrowed_uniform` (`all()` over ∅ is vacuously true).
(iv) include excluded ids in the quantifier → **row (e)** flips `item_narrowed_uniform` →
`section_wide_uniform`.
(v) resolve excluded sections with the task's uniform basis instead of independently →
**row (f)** flips the excluded row's basis `item_narrowed` → `section_wide`.
*Both sides* are exact-literal assertions on the `task_typical_basis` **string** and on each
section's `(typical_worker_seconds, typical_basis, sample_count)` triple.

**C9 — no hidden pace model (T5, repaired).** Fixture: three participating sections with
narrowed values `600`, `900`, `300`, all usable.
Assert the emitted `typical_worker_seconds` multiset is exactly `{600, 900, 300}` as `int`.
*Mutation* — `reconcile_task_typicals` (definition): emit a participating section's value
multiplied by the ratio of two others.
*Both sides* — contract `600`; mutation `600 × (900/300) = 1800`.
*Note*: §11.1's original T5 mutation named a **fallback** value, which lives in
`apply_business_fallback` and is never serialized — inert. Do not re-introduce it.

**C10 — a section with no evidence row is total, not a `KeyError` (§3B B4).**
Fixture: `section_ids` contains `wsec_ghost`; `evidence_by_section` does not.
Assert `selected["wsec_ghost"]` exists with `narrowed_sample_count 0`, `section_sample_count
0`, both seconds `None`, `typical_basis "insufficient_sample"`, `sample_count 0`.
*Mutation* — `reconcile_task_typicals` (definition): index the evidence mapping with `[]`.
*Both sides* — contract: the row exists with those values; mutation: `KeyError`.
*Defect caught*: this replaces the accidental cover that `_step_result`'s two-argument
`typicals.get(section_id, <step attr>)` provides today and that D18's removal deletes.

**C11 — `apply_business_fallback` binds its terminal at the boundary (T14, repaired).**
Rows: (a) `selected_values=[600, 900]`, `terminal=1` (an `int`) → `TypeError`.
(b) `selected_values=[None, None]`, `terminal=Fraction(1,1)` → `[Fraction(1,1), Fraction(1,1)]`.
(c) `selected_values=[None, None]`, `terminal=Fraction(0,1)` → `[Fraction(0,1), Fraction(0,1)]`.
(d) `selected_values=[0, 600, 900]` → `[Fraction(750,1), Fraction(600,1), Fraction(900,1)]` —
zero is unusable and takes the in-task median.
*Mutations, one per sub-check* — all in `apply_business_fallback` (definition):
(i) delete the `isinstance(terminal, Fraction)` entry guard → **row (a)** flips: contract
raises `TypeError`, mutation returns `[Fraction(600,1), Fraction(900,1)]` with no raise.
Rows (b)–(d) do not bite on (i).
(ii) return `Fraction(0,1)` instead of `terminal` → **row (b)** flips `Fraction(1,1)` →
`Fraction(0,1)`; row (c) does not.
(iii) treat `0` as usable → **row (d)** flips element 0 from `Fraction(750,1)` to
`Fraction(0,1)`. (T21's domain half.)
*Note*: the original T14 mutation ("pass a policy where a terminal belongs") was inert —
annotations do not enforce, and with any usable value the terminal is never touched. The
entry guard is what makes the row bite on **any** fixture.

**C12 — the two terminals are used verbatim and never converge (D22).** Covered by C11 rows
(b) and (c) as two literal assertions, not as an equality between two calls.
The `ZeroDivisionError` half of T4 — `terminal=Fraction(0,1)` inside
`divide_production_budget` → `total_weight = 0` → raise — is **forward to plan 4 C4**,
because division is not wired until then.

**C13 — `participating_sections`, one row per state, on real `TaskStep` instances (rule 3).**
Fixture sections: A (one COMPLETED step), B (one WORKING step), C (one FAILED step only),
D (one COMPLETED step that is `is_deleted=True`), E (one SKIPPED + one CANCELLED).
Assert `participating_sections(steps) == frozenset({"A", "B"})`.
*Mutations, one per sub-check*:
(i) `budget_division.participating_sections` (definition): consult an excluded set that
omits `FAILED` → contract `{A, B}`; mutation `{A, B, C}`. (T7, repaired — "reintroduce a
private predicate" is inert when the copy is faithful, and a faithful copy is what an
implementer writes.)
(ii) same (definition): drop the `is_deleted` filter → contract `{A, B}`; mutation
`{A, B, D}`.
(iii) same (definition): omit `CANCELLED` from the excluded set → contract `{A, B}`;
mutation `{A, B, E}`. Row E's second step (SKIPPED) is what makes E stay out under the
contract, so this row is not covered by (i).

**C14 — `parse_spec_from_query_params`, one row per parameter family (charter rule 4: the
deferred route's parser ships now, with callers).**
Rows: (a) no params → `TypicalFilterSpec()`; (b) repeated `item_category_ids` → the
frozenset; (c) `width_cm_min=60&width_cm_max=80` → `(60, 80)`; (d) `width_cm_min=60` alone →
`(60, None)`; (e) `width_cm_max=80` alone → `(None, 80)`; (f) **neither** → the field stays
`None`, **not** `(None, None)` — the two mean different populations; (g)
`width_cm_min=81&width_cm_max=80` → `ValueError` propagates; (h) `can_have_upholstery=true`
→ `True`; (i) an unknown parameter → ignored.
*Mutation* — `parse_spec_from_query_params` (definition): emit `(None, None)` when neither
bound is supplied → **row (f)** flips `is_narrowing` `False` → `True` and the spec stops
equalling `TypicalFilterSpec()`.
*Defect caught*: "no width filter" silently becoming "only items whose width is recorded".

**C15 — HC-4's snapshot, captured pre-refactor and asserted at both clock forms (T11,
repaired).** Two rows, each an assertion against the **committed literal snapshot**, never
an equality between two calls:
(a) `typical_times_statement("ws_snapshot")` compiled without `literal_binds` equals the
snapshot file's contents.
(b) `typical_times_statement("ws_snapshot", now=datetime(2026, 8, 22, tzinfo=timezone.utc))`
compiled the same way equals the **same** snapshot.
*Mutation* — `get_working_section_typical_times.typical_times_statement` (definition):
delete `WorkingSection.is_deleted.is_(False)` from the outer `WHERE`.
*Both sides* — contract: both strings equal the snapshot; mutation: the string loses
`working_sections.is_deleted = false` and both rows go red.
*Notes*: compile **without** `literal_binds` — with it the cutoff inlines and the assertion
becomes a clock race. The original T11 (`compiles to today's SQL string`, expected side
obtained by calling the same function) was vacuous: `f(x) == f(x)` survives any mutation of
`f`. The snapshot file is the fix, and it is only honest if it is captured **now**.
Plan 2 inherits this test unchanged and adds its own mutation ("make the item joins
unconditional").

## 7. Notes

- **Import direction after this phase:** `typical_constants ← typical_filters ←
  budget_division`. Adding an import from `typical_filters` back into `typical_constants`,
  or from `budget_division` into `typical_filters` at module scope in the other direction,
  re-creates the cycle this move exists to break.
- **F-J stands:** zero `sqlalchemy` / `models.tables` imports in
  `domain/item_economics/`. `typical_filters.py` must not break it — it takes duck-typed
  objects and reads them the way `budget_division._value` already does.
- `resolve_section_typical`'s `policy` is an **enum argument**; the terminal is a `Fraction`
  argument named `terminal` of `apply_business_fallback`. **No function accepts both, and no
  boolean exists in either signature** — a confused hand-off must be a `TypeError`, not a
  semantic bug (§3.4, D15).
- The naming rule (§3.6) is contract-grade: *every basis field describes the value it sits
  next to*. "Best available but unused" is never a field. The unused narrowed **seconds**
  value is never published on task surfaces.
- If the projection gate's ledger for this phase is large, the coordinator may split it at
  **C8** — C1–C7 (spec, profile, evidence, policy) and C8–C15 (reconciliation, fallback,
  participating-set, snapshot) are separable, and C15's capture task moves to whichever half
  runs first. Recorded as an option, not a recommendation.

## 8. Review log

*(empty — append-only; shared by implementer and reviewer)*
