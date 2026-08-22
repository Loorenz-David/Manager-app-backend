---
plan: plan_1
role: projection
round: 0
date: 2026-08-22
verdict: AMENDMENTS_REQUIRED
actor: Opus 5 (plan-projection gate, fresh session)
---

# Plan-projection handoff — phase 1, `narrow_typical_work_times`

## 1. Opening

I wrote phase 1 on paper — every object, every function, every test — using only the
documents the builder will be handed, and stopped at each point where those documents did
not tell me what to do next. The phase is sound in its shape and its ordering; the frozen
copy of the old database query, the one thing in this phase that can never be redone later,
can be taken exactly as described. But twenty-one places came up where a careful builder
would have to invent an answer, and eleven of them would change how the finished feature
behaves rather than only how it reads. Nothing here needs you personally: every one of them
is a paragraph the planner or the coordinator can settle, and none reopens a question you
have already answered. My recommendation is to fold the amendments first and only then
write the builder's instructions.

## ⚠ OWNER DECISIONS REQUIRED (0)

Zero cards. Nothing in this phase needs the owner — phase 1 ships a pure domain layer with
no production caller and no wire change, and every gap below is settled by the planner or
the coordinator from artifacts that already exist.

## 2. Decision ledger

Twenty-one rows. **Blocking** = the implementer cannot proceed without inventing a contract
that is observable in the finished product. Ordered by severity.

| # | Decision point | Classification | Proposed routing |
|---|---|---|---|
| L1 | **`apply_business_fallback` has no median implementation available to it.** §8/plan task 8 say `median(usable)`; `_median` lives in `budget_division.py:69`, and plan §7 (`plan_1.md:333-336`) forbids `typical_filters` importing `budget_division`. `_median` is not in §4's perimeter, so it cannot move; a second copy is what an implementer writes, and its even-length rule (`(a+b)/2`, `budget_division.py:69-74`) must match byte-for-byte or phase 4's allowances move silently. **Blocking.** | plan gap (+ master plan §6.1) | Amend `plan_1.md:45-60` and `master_plan.md:128-144`: move `_median` to `typical_constants.py` (widening that module beyond constants, or adding a third leaf module), have `budget_division` import it back, and add a criterion pinning the even-length rule with the mutation "return `ordered[middle]` for even length". If duplication is chosen instead, record it as deliberate with phase 4 named as the de-duplication point. |
| L2 | **The reconciliation quantifier's behaviour on a participating section absent from `evidence_by_section`.** §3B B4 makes a *missing* section total; it does not say whether the zero-evidence row is materialized for all of `section_ids` **before** the quantifier runs. Quantifying over `evidence_by_section ∩ participating` yields `item_narrowed_uniform`; quantifying over `participating_section_ids` with zero-evidence defaults yields `section_wide_uniform`. Both are defensible readings of `master_plan.md:198-204`; they differ on the task-level basis string for a real shape (a soft-deleted section carrying a WORKING step). **Blocking.** | plan gap | Amend plan task 7 (`plan_1.md:99-106`): "the zero-evidence row is materialized for every id in `section_ids` before the quantifier runs; a participating section with no evidence therefore forces `section_wide_uniform`." Add C8 row (h): one participating ghost + one usable-narrowed participant → `section_wide_uniform`; mutation — quantify over `evidence_by_section` keys instead of `participating_section_ids`. |
| L3 | **`applied_filter`'s derivation from the `spec` parameter.** The parameter is `TypicalFilterSpec \| None` (`master_plan.md:201`) and the field is `\| None` (`master_plan.md:196`), so three inputs exist — `None`, empty spec, narrowing spec — and only "non-narrowing → `None`" is asserted (C8 row g, `plan_1.md:230`). Whether `None` is accepted at all, and whether a narrowing spec is carried verbatim, is unstated. **Blocking.** | plan gap | Amend plan task 7: `applied_filter = spec if (spec is not None and spec.is_narrowing) else None`. Add two C8 rows (`spec=None`; a narrowing spec carried by identity). |
| L4 | **C7's grid is not total** (`plan_1.md:192-219`). The stated grid is `(has_usable_narrowed, has_section) × policy` = 8 cells + non-narrowing; four are absent: BROADEN×(usable T, section F); AS_ASKED×(has_narrowed T, section F); AS_ASKED×(has_narrowed F, section F); and **AS_ASKED × a non-narrowing spec** — which is T17, listed as required reading at `plan_1.md:29` and landing in no criterion. The first three are SQL-impossible but dataclass-permitted, which is the totality this gate was asked to check. Also: the AS_ASKED branch quantifies `has_narrowed`, not `has_usable_narrowed` (§4C), so the criterion's own grid label is wrong for half its rows. | plan gap | Add the four rows with exact expected triples; relabel the grid `(has_usable_narrowed, has_section)` for BROADEN and `(has_narrowed, has_section)` for AS_ASKED. The AS_ASKED×section-F rows double as the proof that the AS_ASKED branch never reads `has_section`. |
| L5 | **C6 names no mutation for `has_section`** (`plan_1.md:182-191`). Rows (c) and (d) assert the section floor boundary; all three mutations target `has_narrowed`/`has_usable_narrowed`, so no row bites on a `has_section` slip — charter rule 12. | plan gap | Add mutation (iv): `has_section`: `>=` → `>`, row (d) flips `True` → `False`. |
| L6 | **C7 mutation (iv) covers only half of §3.6's split `sample_count` rule** (`plan_1.md:215`). It flips row (d) (BROADEN → `section_sample_count`). The AS_ASKED half (row g asserts `2` = `narrowed_sample_count`) has no mutation. | plan gap | Add mutation (v): return `section_sample_count` in the AS_ASKED insufficient branch → row (g) flips `2` → `61`. |
| L7 | **C2 has no one-bounded range row** (`plan_1.md:136-146`). `(60, None)` and `(None, 80)` are legal (§3A C2, `master_plan.md:307-310`), and the `lo > hi` guard must be None-safe or it raises `TypeError`. Rows (a)/(b) both supply two bounds, so the None-safety sub-check has no direct bite — it survives only indirectly through C14(d)/(e), whose own decidability is L8. | plan gap | Add C2 rows (c) `(60, None)` and (d) `(None, 80)` constructing with `is_narrowing True`; mutation — drop the `is not None` conjuncts from the range guard → both flip to `TypeError`. |
| L8 | **C14 is not decidable as written** (`plan_1.md:301-313`). Its rows are written in URL query-string syntax (`width_cm_min=60&width_cm_max=80`, `can_have_upholstery=true`), but this repo's `ctx.query_params` is a plain `dict` of already-typed values built by the routers (`context.py:23`; `routers/api_v1/working_sections.py:139`). Three contracts are therefore unfixed: the `params` type (Starlette `QueryParams` with `.getlist` vs `Mapping[str, Any]`), scalar coercion (`"60"` → `60`? what does a non-numeric width do?), and boolean grammar (`"true"` only, or `"1"`/`"True"`/`"false"`?). §6.8 (`master_plan.md:297-311`) fixes the parameter *names* and calls them the deferred route's public contract; §7.5 (`intention.md:1221-1234`) pins only the response. **Blocking, and it is the future public contract the depth allocation flagged.** | plan gap + master plan gap | Amend `master_plan.md:297-311` with the request grammar: the `params` type, per-family value shape, coercion failures, and the boolean spelling set. Then C14 becomes writable. |
| L9 | **C14 omits two of its own parameter families.** The criterion says "one row per parameter family"; `major_categories` and `designers` have no row, though §6.8 fixes both and `major_categories` additionally needs a string → `ItemMajorCategoryEnum` conversion (`domain/items/enums.py:17`) with an unknown-value contract. Charter rule 2. | plan gap | Add rows (j) repeated `major_categories` → the enum frozenset; (k) an unrecognised major-category value → the grammar's stated outcome; (l) repeated `designers` → the frozenset. |
| L10 | **How `typical_filters` reads a duck-typed item, and how its signatures are annotated.** It cannot import `_value` (import direction, `plan_1.md:333-336`) and cannot import `Item` (F-J, `plan_1.md:337-339`), yet `architecture/08_domain.md` ("Type hints") forbids unannotated parameters — and `master_plan.md:163-164` ships `derive_spec_from_primary_item(item)` and `parse_spec_from_query_params(params)` unannotated. An implementer resolving the annotation rule reaches for `from beyo_manager.models.tables.items.item import Item` and breaks F-J. | free choice | Delegate in writing, with both constraints named: plain `getattr(item, "item_category_id", None)`; annotate via a local `Protocol` or a `TYPE_CHECKING`-guarded import. Add charter rule 4's corollary: **no `Mapping` branch unless a C5 row exercises it** — C5's three rows are all attribute-shaped. |
| L11 | **Snapshot capture mechanics and the artifact that performs it** (task 1, `plan_1.md:64-71`). Undetermined: the exact compile call (`statement.compile(dialect=postgresql.dialect())`, and whether `str()` of the result), whether a trailing newline is written, and **what file does the capture** — §4's perimeter has no script, and §4 line 60 says "anything else is a finding", so an ad-hoc script under `app/` is a self-inflicted perimeter breach. | free choice + plan gap | Delegate the compile incantation, requiring the capture and C15 to call one shared helper so they cannot drift; require byte-exact write/read (no trailing newline, or one, stated). Amend §4 to permit a scratch capture path outside `app/` (or a `pytest`-run one-shot deleted in the same commit). |
| L12 | **Nothing forbids regenerating the snapshot in a later phase.** Plan 2 "inherits this test unchanged" (`plan_1.md:330`), but a red C15 in phase 2 is answerable by re-running the capture, which restores exactly the `f(x) == f(x)` vacuity §11A repaired T11 to remove. | plan gap (standing rule) | Add to `master_plan.md` §9: "`typical_times_no_spec_sql.txt` is written once, in phase 1, and never regenerated. A red C15 in any later phase is a finding, never a regeneration." |
| L13 | **§4 perimeter contradicts task 11 and master plan §8.** Task 11 (`plan_1.md:117`) writes `master_plan.md` and `plans/plan_1.md`; §8 (`master_plan.md:387-390`) requires one batched `archgraph_apply_changes` and expects a phase-1 delta. §4 (`plan_1.md:45-60`) lists neither, and closes "Anything else is a finding". | plan gap | Amend §4 to declare the full perimeter the charter's row schema requires: code + tests + the two documents + the tool-recorded archgraph delta. |
| L14 | **The re-export move has no criterion.** Task 2 moves three constants "verbatim" across six live import sites (`division_serializers.py:8-12`, `get_task_price_scenario.py:10-12`, `get_task_production_time.py:10-12`, `get_working_section_typical_times.py:9-13`, plus two tests). No criterion asserts the values survive or that the re-export holds; charter rule 4 asks every added surface to have a test caller. | plan gap | Add C16: `budget_division.TYPICAL_METHOD is typical_constants.TYPICAL_METHOD` (and the two others), plus the three values as literals — here the literal *is* the contract (`master_plan.md:287-295`). Mutations: drop one name from the re-export → `ImportError` at the citing module; change `TYPICAL_WINDOW_DAYS` to `91` → the literal row flips. |
| L15 | **`ValueError` vs the repo's `ValidationError`.** §3A C1 and C2/C14(g) fix `ValueError`. This repo's domain layer uses both — `ValidationError` (HTTP 422, `errors/validation.py:4`) for anything a client can trigger, `ValueError` for programmer preconditions (`domain/item_economics/price_scenario.py:46`). C14 row (g) makes the parser's `ValueError` part of the deferred route's contract, so a user typing `width_cm_min=81&width_cm_max=80` gets a 500, not a 422. | intention gap | Route upstream: either amend §3A C1 to raise `ValidationError` at the parser boundary while `__post_init__` keeps `ValueError`, or record the 500 as accepted and name the future route's translation obligation. Not owner-shaped — the route is deferred and its own phase will own the surface. |
| L16 | **C4(c)'s absence claim is narrower than the claim it stands for.** The criterion greps one module (`plan_1.md:160-162`); §6.6 claims "no spec hash, digest or fingerprint is introduced **anywhere in this pipeline**" (`master_plan.md:284-285`), and `master_plan.md:456-457` requires absence claims to state their root and run from the repository root. | plan gap | Either restate C4(c) as the module-scoped claim it is (and drop the pipeline-wide reading), or widen the root to `app/beyo_manager/domain/item_economics/` with the term set unchanged. |
| L17 | **F-J has no criterion in the phase that creates the new domain module.** Plan §7 states it as prose (`plan_1.md:337-339`). It currently holds (measured: zero `sqlalchemy`/`models.tables` imports in `domain/item_economics/`), and L10 is exactly the pressure that breaks it. | plan gap | Add C17, absence with root and term set: no `sqlalchemy` or `models.tables` import in `app/beyo_manager/domain/item_economics/`. Mutation: add `from beyo_manager.models.tables.items.item import Item` to `typical_filters.py`. |
| L18 | **T13's separate instrument is dropped.** §11.1 records "T12 bites on the branch, T13 on the sweep" (`intention.md:1341`); plan C7 mutation (i) folds both into one branch mutation (`plan_1.md:209-210`). | plan gap | Either add the property-style sweep over an evidence grid, or record the divergence explicitly (charter rule 14's shape) so the reviewer does not open a finding on a deliberate cut. |
| L19 | **C15's snapshot is SQLAlchemy-version-fragile.** A dependency bump reddens a test whose failure message asserts an HC-4 violation that has not occurred. Deliberate (the literal *is* the contract), but unstated. | plan gap (documentation) | One docstring line in `test_typical_times_sql_identity.py` naming the two causes of a red: a statement change (the real finding) or a SQLAlchemy/dialect version change (re-derive, then re-freeze under a recorded authorization). |
| L20 | **`SelectedTypical.participates` is asserted nowhere.** C8 asserts the `(seconds, basis, sample_count)` triple (`plan_1.md:242-243`); C10 asserts five fields and not this one. A `participates` inverted for excluded sections is invisible in phase 1 and surfaces as a wrong `participating_section_count` on the wire in phase 4. | plan gap | Add `participates` to C8's asserted tuple, with the mutation "set `participates=True` for every section" → rows (e)/(f) flip. |
| L21 | **C13's fixture E carries two independent exclusion causes.** E has one SKIPPED and one CANCELLED step (`plan_1.md:290`); the note at `plan_1.md:298-300` reads as though SKIPPED alone is load-bearing. It is not a rule-2 defect — the predicate is existential over *non*-excluded steps, so removing either state from the excluded set does flip the row — but the recorded reasoning is wrong and will read as a defect to the reviewer. | plan gap (wording) | Restate: "E stays out because both of its states are excluded; mutation (iii) bites because dropping `CANCELLED` makes E's cancelled step a participating one." |

## 3. Reality-check findings

Each verified against the tree at `2d83f40`.

**R1 — `master_plan.md:104-113` declares an affordance absent that exists.** §5 states "This
repo has no `architecture/*.md` contract system with a goal-mapping guide", reasoning from
`docs/architecture/`. The system is at **`backend/architecture/`**: 69 files, `README.md`
reading "Canonical backend contracts live here", including `01_architecture.md` (layer map
and hard dependency rules), `08_domain.md`, `15_testing.md`, `21_naming_conventions.md`,
`05_errors_local.md`. Under the charter's project-affordance rule these are authoritative for
*how to write code*, and three of them bind phase 1 directly: `08_domain.md`'s
"fully annotated signatures, no `Any`" (L10, and `master_plan.md:163-164` ships two
unannotated signatures); `08_domain.md`'s domain-purity table (F-J's independent source);
`15_testing.md:47`'s "test files mirror the module they test" — which two of the three new
test files do not (`test_participating_sections.py` mirrors nothing; the module is
`budget_division.py`, and `test_typical_times_sql_identity.py` mirrors
`get_working_section_typical_times.py`). The goal-mapping guide is genuinely thin (a
three-line README), so §5's conclusion is defensible for *routing*; its premise is not.
**Routing:** amend `master_plan.md:104-113` to record the system, its thin index, and which
files bind; add `architecture/08_domain.md` and `architecture/15_testing.md` to `plan_1.md`
§2. Deviations from the mirror rule are fine — recorded, not silent.

**R2 — `plan_1.md:36` cites a path that does not exist.**
`app/beyo_manager/models/tables/item_economics/…/item_category.py`. There is no
`item_category.py` under `models/tables/item_economics/` (that package holds ten cost-model
and valuation tables). The real path is
**`app/beyo_manager/models/tables/items/item_category.py`** — `ItemCategory.major_category`
at line 23, the column §3A C2 names. Correct the read-first list.

**R3 — `plan_1.md:52` proposes a file the repo's convention forbids.**
`tests/.../working_sections/__init__.py` "(if the package needs it)": there are **zero**
`__init__.py` files anywhere under `app/tests` (measured), `pytest.ini` sets no
`--import-mode`, so collection relies on unique basenames — and all three new basenames are
unique repo-wide (measured, no duplicates). The package does not need it, and with §4's
"anything else is a finding" the conditional is a trap in both directions. Delete the line.

**R4 — `plan_1.md:29` lists T17 as required reading; no criterion lands it.** See L4. T20 is
also listed and lands in no phase-1 criterion, but that one is correct — it is a SQL-layer
row belonging to phase 2, read here for context. T17 is not: "empty spec: both policies
return identical objects" is pure phase-1 surface and is exactly what §3B B1's short-circuit
makes true.

**R5 — `plan_1.md:23-38` omits §4A, which task 1 depends on.** Task 1 (`plan_1.md:69`) cites
"§4A K5" as the reason the compiled string is `now`-independent, and C15's whole design rests
on it. §4A is not in the read-first list. The claim itself is **sound**: the cutoff reaches
SQL as a bound parameter (`get_working_section_typical_times.py:46`, a Python `datetime`
compared to `grouped_steps.c.latest_closed_at`), so without `literal_binds` it renders as a
named bind and the string is clock-independent — as are the two `workspace_id` comparisons,
which is why the snapshot's `"ws_snapshot"` never appears in the file. Add §4A (at minimum
K5) to §2.

**R6 — citations that resolve correctly, checked because the plan leans on them.**
`budget_division.py:402-410` — `__all__` opens at 402 and lists all three constants
(`plan_1.md:74-75` ✓). `budget_division.py:338-343` — the `raw_shares` comprehension
containing `/ total_weight`, with `total_weight` computed at 337 (`plan_1.md:112-114` ✓).
`master_plan.md:334-343`'s phase-1 dependency: `git diff --stat dc76db8 HEAD -- app/` is
**empty**, so the tree is at the D23 baseline and the snapshot may be captured (`plan_1.md:41-43` ✓).
`TaskStep.total_working_seconds` is `Integer, nullable=False, default=0`
(`models/base/aggregate_metrics.py:6`), so §4B's non-NULL chain holds ✓.
`TaskStepStateEnum` carries every state C13's fixture needs ✓, and `EXCLUDED_STEP_STATES`
(`budget_division.py:19-25`) is `{SKIPPED, CANCELLED, FAILED}` ✓.

**R7 — operational note, not a finding.** `.archgraph/contexts/current-task.md` exists
(21 KB, built 2026-08-22) but is **untracked** (`git status`: `?? .archgraph/contexts/`).
`master_plan.md:385-387` tells every implementing session to read it and not rebuild it; a
reviewer working from a clean clone will not have it. Worth one line in the implementer
prompt, or a decision to commit it.

## 4. Decidability findings

Per the skill's step 5 — could the test be written right now, from the artifacts alone, with
one exact expected outcome per case?

- **Writable as-is:** C1, C3, C4(a)(b), C5, C6 (rows), C9, C11, C12, C13, C15.
- **Writable after a one-line amendment:** C2 (L7), C4(c) (L16), C7 (L4/L6), C8 (L2/L3/L20),
  C10 — its five asserted values hold under both readings of whether `wsec_ghost`
  participates, so it is not blocked, but the reading itself must be fixed by L2 or the row
  is passing for two different reasons.
- **Not writable:** **C14** (L8/L9) — the parameter grammar does not exist in any artifact,
  so no row has one exact expected outcome; and **C11 row (d)**'s `Fraction(750,1)` is
  arithmetically correct only under `budget_division._median`'s even-length rule, which L1
  leaves without a source.

## 5. Write perimeter

From `git status --porcelain` at the repo root
(`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`), HEAD `2d83f40`:

```
?? .archgraph/contexts/          # pre-existing, untracked before this session, not written by it
```

Written by this session — exactly one file, and nothing else:

- `docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/reviewer/20260822_plan1_projection_handoff.md`

No code, no plan, no intention, no tracker row, no Review log line, no archgraph mutation.
The paper skeleton is discarded and is not attached. Nothing committed, nothing pushed.

**L4 runs: 0; tests executed: 0.**

## 6. Exit gate

Twenty-one ledger rows, of which eleven are blocking. Per the charter's PROJECTED gate, the
implementer prompt compiles only after every row is routed. Recorded for the coordinator:
`plan_1.md:346-350` already offers the C8 split as an option if this ledger came back large —
it did, and the split remains an option, not a recommendation. The routing bottleneck is not
the criteria count but L1, L2 and L8, which are three paragraphs in two documents.
