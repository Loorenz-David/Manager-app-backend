# Plan 1 — The pure typicals domain, and the pre-refactor SQL snapshot

```
plan: plan_1
project: narrow_typical_work_times
state: IMPLEMENTED
projection_gate: MANDATORY — ran 2026-08-22, AMENDMENTS_REQUIRED, folded same day (§8)
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

- Master plan §§4, **5** (the `architecture/` contract system and the two recorded
  mirror-rule deviations), 6 (incl. §6.8's request grammar), 7, 9, 10 (naming registry,
  sequencing, standing rules, environment and evidence budgets).
- Intention **header** (the section-letter precedence rule), then §3.1–§3.7, **§3A**,
  **§3B**, **§3C** (parser error boundary), §4.1, §4.3, **§4A K5** (why the compiled
  string is `now`-independent — task 1 and C15 rest on it), **§4B**, **§4C** (with its
  round-8 `is not None` correction), §4.5, §6.1, §8, §9 (the deferred statistics
  contract), §11.1 rows T3/T5/T7/T9/T10/T11/T12/T13/T14/T17/T20/T21, **§11A** in full.
  (T20 is phase-2 context only; **T17 lands here, in C7 row (m)**.)
- `planning/owner_decisions.md` — D4, D6, D11, D12, D13, D15, D16, D17, D19, D22, **D25**.
- `handoffs/reviewer/20260822_mechanism_inventory_gate_handoff.md` §2 rows 3, 7, 8, 14, 15,
  16 and §5.
- `architecture/08_domain.md` (annotation and purity rules) and
  `architecture/15_testing.md` (mirror rule — two recorded deviations, master plan §5).
- Code: `app/beyo_manager/domain/item_economics/budget_division.py` (constants,
  `EXCLUDED_STEP_STATES`, `_step_state_is_excluded`, `_median`, `_as_fraction`, `_value`,
  `__all__`); `app/beyo_manager/models/tables/items/item.py`;
  `app/beyo_manager/models/tables/items/item_category.py`;
  `app/beyo_manager/errors/validation.py`;
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
- `app/tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py`
- `app/tests/unit/services/queries/working_sections/snapshots/typical_times_no_spec_sql.txt`

No `__init__.py` anywhere under `app/tests` — the tree has zero and collection relies on
unique basenames; all three new basenames are unique repo-wide (projection R3, measured).

**Modified**
- `app/beyo_manager/domain/item_economics/budget_division.py` — import + re-export the
  three constants; `_median` moves out to `typical_filters.median` and internal call
  sites rename `_median(` → `median(` (master plan §6.1); add `participating_sections`.
  **No other executable line changes.**
- `master_plan.md` (tracker row 1 only) and this file (Review log + `state:` only) — the
  charter's closing bookkeeping, task 11.

**Recorded, not files:** the phase's architectural delta lands as **one batched
`archgraph_apply_changes`** at session end (master plan §8) — expected: the new domain
module. The snapshot is captured by a **transient command** (task 1), never a committed
script; a capture script under `app/` is a perimeter finding.

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
   **Capture mechanics (projection fold, L11):** the compile incantation lives in
   **exactly one place** — a module-level helper in `test_typical_times_sql_identity.py`
   (write the test file's helper first, then capture) — and the capture is a transient
   command invoking that helper, so capture and C15 cannot drift. The exact compile call
   is delegated to the implementer (recorded in the prompt), with two fixed constraints:
   the file is written and compared **byte-exact with no trailing newline**
   (`write_text(s)` / `read_text() == s`), and the capture command itself appears
   verbatim in the Review log entry so the act is reproducible.
2. Move `TYPICAL_METHOD`, `TYPICAL_WINDOW_DAYS`, `TYPICAL_MIN_SAMPLE_SIZE` into
   `typical_constants.py` verbatim. Import them back into `budget_division.py` and keep all
   three in its `__all__` (already present, `budget_division.py:402-410`) so **no existing
   import site changes**. Master plan §6.1 records why. In the same task, move `_median`
   verbatim to `typical_filters.median` (public — it gains external callers) and rename
   `budget_division`'s internal call sites; the even-length rule `(a+b)/2` is pinned by
   C18 (L1).
3. `TypicalFilterSpec` with the seven fields of §3.1 and `__post_init__`
   canonicalization per **§3A C1**: empty collection → `None`; `(None, None)` **kept**;
   `lo > hi` raises `ValueError`. `is_narrowing` is exactly "at least one field is not
   `None`". The frozen dataclass's own field-wise `__eq__`/`__hash__` **is** the dedupe key.
   **No hash, digest or fingerprint anywhere.**
   Docstring the `(None, None)` form explicitly: it means **"the dimension is recorded"**,
   not "no constraint" (§3A C2) — an implementer reading it as a no-op writes `TRUE` and the
   population silently doubles.
4. `COMPARABILITY_PROFILE`, `derive_spec_from_primary_item` (§3.2), and
   `parse_spec_from_query_params` with the parameter names fixed in master plan §6.8 and
   the **request grammar** fixed there too (typed-dict input, absent-key ≡ `None`-value,
   enum conversion): client-triggerable rejections raise **`ValidationError`** per §3C;
   `__post_init__` keeps `ValueError`. Annotation without breaking F-J is delegated in
   the implementer prompt (local `Protocol`, never a `models.tables` import).
5. `SectionTypicalEvidence` (§3.3) with `has_narrowed`, `has_section` and **`has_usable_narrowed`**
   (§4C **as corrected in round 8**: `has_narrowed and narrowed_typical_worker_seconds
   is not None and narrowed_typical_worker_seconds > 0` — total over every dataclass
   shape, not only SQL-produced ones). `has_narrowed` stays §3.3's pure count predicate.
   Floors read `TYPICAL_MIN_SAMPLE_SIZE`, never a literal.
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
   **Two contracts fixed at the projection fold (L2, L3):**
   (a) **the zero-evidence row is materialized for every id in `section_ids` before the
   quantifier runs** — a participating section absent from `evidence_by_section`
   therefore forces `section_wide_uniform` (its materialized row is not usable-narrowed),
   never `item_narrowed_uniform` by omission from the quantified set;
   (b) **`applied_filter = spec if (spec is not None and spec.is_narrowing) else None`**
   — `spec=None` is accepted and behaves exactly like a non-narrowing spec (the B1
   short-circuit), and a narrowing spec is carried by identity, verbatim.
8. `apply_business_fallback` (§8) — using `median` from this same module (task 2) — with
   the signature in master plan §6.2 and an
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
11. Closing bookkeeping (the full perimeter §4 declares): update the master plan tracker
    row and this file's Review log + `state:`, and record the phase's architectural delta
    as one batched `archgraph_apply_changes` (master plan §8).

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
(c) `(60, None)` → constructs, `is_narrowing True`. (d) `(None, 80)` → constructs,
`is_narrowing True` — one-bounded bands are legal (§3A C2, master plan §6.8) and the
`lo > hi` guard must be None-safe (projection L7).
*Mutations, one per sub-check (rule 12)* — all in `__post_init__` (definition):
(i) delete the range validation → **row (a)** flips: contract raises, mutation constructs.
Row (b) does not bite on (i) — recorded.
(ii) tighten the guard to `lo >= hi` → **row (b)** flips: contract constructs, mutation
raises. Row (a) does not bite on (ii) — recorded.
(iii) drop the `is not None` conjuncts from the range guard → **rows (c) and (d)** flip:
contract constructs, mutation raises `TypeError` (`60 > None`). Rows (a)/(b) do not bite
on (iii) — recorded.
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
(c) **absence, root and terms stated (projection L16 — the root is the §6.6 claim's
scope, not one module)**: under `app/beyo_manager/domain/item_economics/`, run from the
repository root, none of the tokens `hashlib`, `sha1`, `sha256`, `md5`, `fingerprint`,
`digest` appears in any module this pipeline adds or modifies (pre-existing modules are
sampled by the same grep and were clean at projection time).
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
`has_usable_narrowed False`; (h) narrowed count **floor**, median **`None`** →
`has_usable_narrowed False` — **returns, never raises** (§4C round-8 correction: the
dataclass permits this shape; `None > 0` is a `TypeError` without the `is not None`
conjunct).
*Mutations, one per sub-check* — all in `SectionTypicalEvidence` (definition):
(i) `has_narrowed`: `>=` → `>` — **rows (b), (e), (f)** flip `True`→`False`; row (a) does not.
(ii) `has_usable_narrowed`: drop the `> 0` conjunct — **row (e)** flips `False`→`True`; rows
(f), (g) do not.
(iii) `has_usable_narrowed`: `> 0` → `>= 0` — **row (e)** flips; recorded as a second shape
of the same sub-check because `>= 0` is the likelier slip than deletion.
(iv) `has_section`: `>=` → `>` — **row (d)** flips `True`→`False`; row (c) does not
(projection L5: without this, no row bites on a `has_section` slip).
(v) `has_usable_narrowed`: drop the `is not None` conjunct — **row (h)** flips: contract
`False`, mutation raises `TypeError`. Rows (e)–(g) do not bite on (v) — recorded.
*Defect caught*: D25 — a section whose narrowed history is all zeros declared "known", so
the least-informative section decides the basis for every other section on the task.

**C7 — `resolve_section_typical` is total over its full grid** — for `BROADEN_TO_SECTION`
the axes are **(has_usable_narrowed, has_section)**; for `ANSWER_AS_ASKED` they are
**(has_narrowed, has_section)** (§4C: the AS_ASKED branch quantifies the count predicate,
not usability — projection L4's relabel) — **plus the non-narrowing short-circuit under
each policy.** One row per cell, including the SQL-impossible-but-dataclass-permitted
cells (section floor unmet while the narrowed side is populated); each row's fixture makes
its own predicate the only reason its outcome holds. The section-F AS_ASKED rows double as
the proof that the AS_ASKED branch never reads `has_section`.
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
| i | **non-narrowing** | (3, None) | (4, 800) | BROADEN | `insufficient_sample` / `None` / `4` |
| j | narrowing | (7, 540) | (3, None) | BROADEN | `item_narrowed` / `540` / `7` — the first rung does not consult `has_section` |
| k | narrowing | (7, 540) | (3, None) | AS_ASKED | `item_narrowed` / `540` / `7` |
| l | narrowing | (2, None) | (3, None) | AS_ASKED | `insufficient_sample` / `None` / `2` — differs from row (g) only in the section columns, proving AS_ASKED never reads them |
| m | **non-narrowing** | (61, 600) — as row (h) | (61, 600) | **AS_ASKED** | `section_wide` / `600` / `61` — **T17 lands here**: byte-identical `SelectedTypical` to row (h)'s, asserted as two literal rows, not `f(a) == f(b)` |
Rows (j)–(l) are SQL-impossible (the narrowed population is a subset of the section
population) but dataclass-permitted — the totality this criterion proves (projection L4).
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
(v) return `section_sample_count` in the AS_ASKED insufficient branch → **row (g)** flips
`2` → `61` (and row (l) flips `2` → `3`) — the other half of §3.6's split `sample_count`
rule, which mutation (iv) alone leaves uncovered (projection L6).
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
| h | one participating id in `section_ids` **absent from `evidence_by_section`** + one usable-narrowed participant | **`section_wide_uniform`** — the zero-evidence row is materialized for every id in `section_ids` *before* the quantifier runs (task 7 (a), projection L2); the ghost's row shows `insufficient_sample` / `None` / `0` |
| i | `spec=None`, all participants usable-narrowed | `section_wide_uniform`, `applied_filter is None` — `None` behaves exactly like a non-narrowing spec (task 7 (b), projection L3) |
| j | a **narrowing** spec, all participants usable-narrowed | `item_narrowed_uniform`, **`applied_filter is spec`** — carried by identity, verbatim |
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
(vi) quantify over `evidence_by_section`'s keys instead of `participating_section_ids`
(i.e., skip the materialization) → **row (h)** flips `section_wide_uniform` →
`item_narrowed_uniform` (projection L2's mutation). Rows (a)–(g) do not bite on (vi).
(vii) set `participates=True` for every section → **rows (e) and (f)** flip the excluded
row's `participates` `False` → `True` (projection L20 — otherwise an inverted
`participates` is invisible until it surfaces as a wrong `participating_section_count`
on the wire in phase 4).
*Both sides* are exact-literal assertions on the `task_typical_basis` **string** and on each
section's `(typical_worker_seconds, typical_basis, sample_count, participates)` tuple
(projection L20 adds the fourth element).

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
zero is unusable and takes the in-task median (`typical_filters.median`, whose
even-length rule C18 pins — row (d)'s `750` is `(600+900)/2` and is arithmetically
correct only under that rule; projection L1/decidability).
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
mutation `{A, B, E}`. E stays out because **both** of its states are excluded — the
predicate is existential over non-excluded steps; mutation (iii) bites because dropping
`CANCELLED` makes E's cancelled step a participating one (wording corrected at the
projection fold, L21 — the prior note read as though SKIPPED alone were load-bearing).

**C14 — `parse_spec_from_query_params`, one row per parameter family (charter rule 4: the
deferred route's parser ships now, with callers). Rewritten at the projection fold
(L8/L9): inputs are the router's already-typed dict per master plan §6.8's request
grammar and intention §3C — never URL query strings.**
Rows: (a) `{}` → `TypicalFilterSpec()`; (b) `{"item_category_ids": ["a", "b"]}` →
`frozenset({"a", "b"})`; (c) `{"width_cm_min": 60, "width_cm_max": 80}` → `(60, 80)`;
(d) `{"width_cm_min": 60}` alone → `(60, None)`; (e) `{"width_cm_max": 80}` alone →
`(None, 80)`; (f) **neither key** → the field stays `None`, **not** `(None, None)` — the
two mean different populations; (g) `{"width_cm_min": 81, "width_cm_max": 80}` →
`ValidationError` (§3C — client-triggerable, never a bare `ValueError`); (h)
`{"can_have_upholstery": True}` → `True`, and `{"can_have_upholstery": False}` → `False`
(False is a value, not an absence); (i) an unknown key → ignored; (j)
`{"width_cm_min": None, "item_category_ids": None}` → both fields stay `None` —
**an explicit `None` value is equivalent to an absent key** (routers pass `None` for
unset `Query(None)` params); (k) `{"major_categories": ["wood", "seat"]}` →
`frozenset({ItemMajorCategoryEnum.WOOD, ItemMajorCategoryEnum.SEAT})`; (l)
`{"major_categories": ["stone"]}` → `ValidationError` (§3C: silently ignoring an
unrecognised category answers a different narrowed question); (m)
`{"designers": ["dsg_a", "dsg_b"]}` → `frozenset({"dsg_a", "dsg_b"})`; (n)
`{"item_category_ids": []}` → the field stays `None` (§3A C1 canonicalization through
the parser path).
*Mutations, one per sub-check* — all in `parse_spec_from_query_params` (definition):
(i) emit `(None, None)` when neither bound is supplied → **row (f)** flips `is_narrowing`
`False` → `True` and the spec stops equalling `TypicalFilterSpec()`.
(ii) treat an explicit `None` value as a supplied value → **row (j)** raises or emits
`(None, None)` where the contract keeps the field `None`.
(iii) skip unknown-value rejection for `major_categories` (drop them instead) → **row
(l)** flips `ValidationError` → a spec narrowed to `frozenset()`→`None` — silently
section-wide.
(iv) let the dataclass's `ValueError` propagate uncaught from the parser → **row (g)**
flips `ValidationError` → `ValueError`.
*Defect caught*: "no width filter" silently becoming "only items whose width is
recorded"; a user typo surfacing as a 500; an unknown category silently un-narrowing the
question.

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
The test module's docstring names the **two causes of a red** (projection L19): a
statement change — the real HC-4 finding — or a SQLAlchemy/dialect version bump, whose
remedy is a re-derivation under the recorded-authorization rule in master plan §9, never
a silent re-capture. The snapshot is written once and never regenerated (same rule).

**C16 — the constants move is invisible to every import site (projection L14).**
Rows: (a) `budget_division.TYPICAL_METHOD is typical_constants.TYPICAL_METHOD`, and the
same identity for `TYPICAL_WINDOW_DAYS` and `TYPICAL_MIN_SAMPLE_SIZE` — three rows;
(b) the three values as exact literals: `"median_completed_section_totals"`, `90`, `5` —
here the literal **is** the contract (master plan §6.7; rule 13's stated exception).
*Mutations, one per sub-check* — `budget_division.py` (definition):
(i) drop one name from the re-export → the identity row for that name flips to
`ImportError`/`AttributeError` at the citing module.
(ii) `typical_constants.py` (definition): `TYPICAL_WINDOW_DAYS = 91` → row (b)'s literal
flips `90` → `91`.
*Defect caught*: a "verbatim move" that silently drops a name or drifts a value — six
live import sites would follow it.

**C17 — F-J holds in the phase that creates the new domain module (projection L17).**
Absence, root and terms stated, run from the repository root: no `sqlalchemy` and no
`models.tables` import anywhere under `app/beyo_manager/domain/item_economics/`.
*Mutation* — `typical_filters.py` (definition): add
`from beyo_manager.models.tables.items.item import Item`.
*Both sides* — contract: the grep finds nothing; mutation: one hit. (L10 is exactly the
pressure that produces this import; the delegated `Protocol` is the sanctioned path.)

**C18 — `median`'s even-length rule is byte-for-byte the old `_median`'s (projection L1).**
Rows: (a) `median([Fraction(600), Fraction(900)]) == Fraction(750)` — even length takes
`(ordered[m-1] + ordered[m]) / 2`; (b) `median([Fraction(300), Fraction(600),
Fraction(900)]) == Fraction(600)` — odd length takes `ordered[m]`; (c) **unsorted odd**
input `[Fraction(900), Fraction(300), Fraction(600)]` → `Fraction(600)` — the function
sorts before indexing.
*Mutations, one per sub-check* — `typical_filters.median` (definition):
(i) return `ordered[middle]` for even length → **row (a)** flips `750` → `900`. Rows
(b)/(c) do not bite on (i) — recorded.
(ii) drop the sort → **row (c)** flips `600` → `300` (the middle of the unsorted list).
Rows (a)/(b) do not bite on (ii) — recorded ((a) only by luck of ordering, (b) is
pre-sorted by construction).
*Defect caught*: a re-implemented median whose even-length or ordering behavior drifts —
phase 4's allowances would move silently (the exact drift L1 names).

## 7. Notes

- **Import direction after this phase:** `typical_constants ← typical_filters ←
  budget_division`. Adding an import from `typical_filters` back into `typical_constants`,
  or from `budget_division` into `typical_filters` at module scope in the other direction,
  re-creates the cycle this move exists to break.
- **F-J stands, and is now a criterion (C17):** zero `sqlalchemy` / `models.tables`
  imports in `domain/item_economics/`. `typical_filters.py` must not break it — it takes
  duck-typed objects and reads them the way `budget_division._value` already does.
  **Annotation without breaking F-J (projection L10, delegated in the implementer
  prompt):** `derive_spec_from_primary_item` reads `getattr(item, "item_category_id",
  None)` and is annotated via a local `typing.Protocol` — never a `models.tables` import,
  not even under `TYPE_CHECKING` (C17's grep is textual and `architecture/08_domain.md`'s
  purity table is the authority). **No `Mapping` branch** — C5's rows are all
  attribute-shaped, and an untested branch is charter-rule-4 dead weight.
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
  **Coordinator decision at the fold (2026-08-22): not exercised.** The ledger was large
  (21 rows) but its weight was routing, not criteria volume — the projection itself
  located the bottleneck in three paragraphs across two documents, all folded. The phase
  ships whole; the option lapses.

## 8. Review log

*(append-only; shared by implementer and reviewer)*

- **2026-08-22 · projection round 0 · Opus 5 · AMENDMENTS_REQUIRED → folded same day by
  the coordinator.** 21 ledger rows (11 blocking) + 7 reality checks, zero owner cards
  (`handoffs/reviewer/20260822_plan1_projection_handoff.md`). All rows routed: intention
  round 8 (§3C parser error boundary; §4C `is not None` correction — the latter a
  coordinator-sealed gap the projection missed, folded as C6 rows (h)/mutation (v));
  master plan §5 (the `architecture/` system exists — R1), §6.1/§6.2 (`median` moves),
  §6.8 (request grammar), §9 (snapshot-never-regenerated); this plan — tasks 1, 2, 4, 5,
  7, 8, 11, §2/§4 corrections (R2 path, R3 no-`__init__`, §4A K5 read-first), criteria
  C2/C4/C6/C7/C8/C11/C13/C14/C15 amended, **C16–C18 added** (59 → 62 project criteria).
  C8-split option consciously not exercised. State → PROJECTED.

- **2026-08-22 · implementation round 1 · Codex · IMPLEMENTED.** Captured the
  pre-refactor PostgreSQL SQL snapshot before production edits; added the pure
  typical-filter specification, evidence/policy/resolution/reconciliation engine,
  business fallback, median, and shared participating-section rule; moved and
  re-exported the three typical constants without changing their values; moved
  `_median` verbatim as `median`; added the phase test files and snapshot guard.
  The local Protocol annotation for `derive_spec_from_primary_item` is the
  delegated F-J choice; no `models.tables` or SQL imports enter the domain. The
  focused phase perimeter passed 49 tests, and the named mutation probes were run
  at whole-file L1 scope and reverted; their ledger is in
  `handoffs/implementer/20260822_plan1_implementation_handoff.md`.

  Capture command (verbatim):

  ```text
  PYTHONPATH=. .venv/bin/python -c 'from datetime import datetime, timezone; from tests.unit.services.queries.working_sections.test_typical_times_sql_identity import SNAPSHOT_PATH, compile_typical_times_sql; no_clock = compile_typical_times_sql(); fixed_clock = compile_typical_times_sql(now=datetime(2026, 8, 22, tzinfo=timezone.utc)); assert no_clock == fixed_clock; SNAPSHOT_PATH.write_text(no_clock); assert SNAPSHOT_PATH.read_text() == no_clock'
  ```

  Judgment calls: the parser accepts the already-typed query-parameter mapping and
  translates client-triggerable range/category failures to `ValidationError`; the
  domain constructor retains `ValueError`; `None` specs canonicalize to the empty
  spec; and missing section evidence is materialized as a zero-evidence row. The
  snapshot file has no trailing newline and is not to be regenerated. The one
  authoritative L4 stamp is recorded in the handoff after the checkpoint commit.

- **2026-08-22 · implementation round 1 perimeter repair · Codex.** The first full-suite
  attempt exposed existing imports of private `budget_division._median` in the price-
  scenario query, causing collection errors after the planned move. Added the
  compatibility alias `_median = median` in `budget_division.py`; this keeps all existing
  import sites unchanged while retaining one median implementation. Focused phase tests
  returned to 49 passed. The initial full-suite result is not the closing stamp; a clean
  re-run after this repair is required and will be recorded in the handoff.

- **2026-08-22 · implementation round 1 L4 stamp · Codex.** On the repaired code
  checkpoint, `PYTHONPATH=. pytest -m 'not e2e'` completed with 2608 passed, 21 failed,
  2 warnings, and no collection errors. The failing-ID set is exactly the published
  21-ID comparator: added IDs ∅ and removed IDs ∅. Tree identity is code checkpoint
  `8ff6ecc` with no phase-perimeter changes after the compatibility repair; only the
  expected untracked `.archgraph/contexts/` session files are present.

- **2026-08-22 · coordinator consumption pass · CHANGES_REQUESTED before review.**
  Verified at source: the engine's logic is correct at every site checked (ladder,
  quantifier, materialization, `applied_filter` identity, `has_usable_narrowed`
  totality, F-J purity — grep clean); the snapshot was captured pre-refactor with the
  both-clock-forms equality asserted before the write, and its last byte is not a
  newline. Four **criteria-coverage** gaps found — rows this plan enumerates that the
  test files omit, three of them rows the projection fold specifically added:
  **(F1)** C7 row (i) absent — the non-narrowing *insufficient* branch of
  `resolve_section_typical` has **zero** coverage (every other non-narrowing row has
  `section_sample_count = 61`); the plan's own row (i) numbers are symmetric and cannot
  bite, so the fix prompt asymmetrizes them and amends C7 in the same edit.
  **(F2)** C14 rows (c) both-bounds, (h) `True` half, and **(m) `designers`** absent —
  (m) is projection ledger L9's omission lapsing a second time.
  **(F3)** C10's ghost row asserts basis/count/participates but **not the seconds** —
  `_zero_evidence` returning `(0, 0, 0, 0)` stays green while publishing
  `typical_worker_seconds: 0` beside `insufficient_sample`, the false-disclosure shape
  §3B B2 / T16b forbid, which reaches the wire in phase 4.
  **(F4)** two handoff claims are not what the tree measures: the snapshot's last byte
  is `0x65`, not `0x6e`; and the C4(c) term-set grep is **not** empty at the stated root
  — `serializers.py:351 "config_fingerprint"`, pre-existing and unrelated to spec
  identity, so §6.6's claim holds but the measurement must be reported as it reads.
  Round-1 judgment calls all accepted, incl. the `_median = median` alias: the plan and
  the projection both missed that a private name had a cross-module importer
  (`get_task_price_scenario.py:13`). The alias stays; **its removal is routed to phase
  5**, which owns that file. Fix prompt:
  `prompts/implementer/20260822_plan1_fix_round2_prompt.md`. State → `CHANGES_REQUESTED`.

- **2026-08-22 · implementation fix round 2 · Codex · IMPLEMENTED.** Closed the four
  criteria-coverage gaps from the coordinator's fix prompt without changing production
  logic. Added C7 row (i) with an asymmetric `(3, None)` narrowed / `(4, 800)` section
  fixture so both insufficient-sample outputs are mutation-discriminating; added C14's
  both-bounds, upholstery-`True`, and `designers` rows; and expanded C10's ghost-row
  assertions to both seconds and all evidence fields, including `None` seconds. The
  handoff corrects the measured snapshot last byte to `0x65` and reports the one
  pre-existing out-of-scope `config_fingerprint` grep hit. F5 remains structurally held:
  participating section IDs are contractually a subset of `section_ids`; no guard was
  added. Named mutations were run at L1 whole-file scope and reverted; the one
  authoritative L4 stamp is recorded in the round-2 handoff.
