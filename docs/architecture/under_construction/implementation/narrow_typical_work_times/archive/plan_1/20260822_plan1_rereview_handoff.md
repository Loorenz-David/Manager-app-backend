---
plan: plan_1
role: reviewer
round: 2
date: 2026-08-22
verdict: APPROVED
actor: Opus 5
---

# Plan 1 re-review handoff — delta-scoped, round 2

All nine round-1 findings are closed, and every one of them now **bites**: the three
mutants that left the phase suite at 33 passed in round 1 each redden it today, and so do
the two S1 mutants and the F3 parser mutant. The perimeter is exactly what the fix prompt
allowed — the only production change across the whole fix cycle is `_optional_values`, one
hunk, and I confirmed that in one command. The new parser boundary holds under every
scalar I could throw at it and rejects nothing the request grammar can legitimately
produce. Four new notes come out of the delta, none of them blocking: one more escape in
the purity guard (the same family as the two the owner already carried to plan 4), one
grammar-edge residue for plan 2, and two plan-side row attributions that the repair itself
made stale.

Verdict: **APPROVED** — zero blocking, zero should-fix, four notes carried forward.

## ⚠ OWNER DECISIONS REQUIRED (0)

Zero cards. Nothing in this round needs an owner answer. The plan-4 disposition of the two
measured purity escapes is recorded below as agreed, not disputed.

## 1. Perimeter — verified first

**Production change across the fix cycle:** `git diff 8feae38 1590ebe -- app/beyo_manager/`
returns **one file, one hunk**: `typical_filters.py` `_optional_values`, +7/-1. Nothing else
under `app/beyo_manager/` moved. This matches the fix prompt's "F3 only. No other production
edit."

**Checkpoint `1590ebe` itself** touched six paths:

| path | in the fix prompt's declared perimeter? |
|---|---|
| `app/beyo_manager/domain/item_economics/typical_filters.py` | yes — F3 only, and it is F3 only |
| `app/tests/unit/domain/item_economics/test_typical_filters.py` | yes |
| `app/tests/unit/domain/item_economics/test_domain_purity.py` (new) | yes — the named F6 file, at the suggested path |
| `docs/…/plans/plan_1.md` | yes |
| `docs/…/master_plan.md` | yes |
| `.archgraph/architecture.yml` | not named by the prompt; **standing charter affordance**, declared in the handoff's own perimeter — not a finding |

I read the graph delta rather than trusting the ledger: it is **purely additive** — one
inferred `test` node (`test-item-economics-domain-purity-guards`), one `verifies` edge to
`domain-item-economics-typical-filters`, and two `sourceLinks`. No review item was
promoted, rejected or edited; every addition stays `origin: ai_inferred` and pending human
adjudication. I neither promoted nor edited anything.

The other paths inside the `8feae38..1590ebe` span (`planning/intention.md`,
`plans/plan_2.md`, `prompts/`, `handoffs/`) belong to the two intervening **coordinator**
commits `fb1884a` and `047494f`, not to the implementer. **No file changed outside a
declared perimeter.**

## 2. Closure table — each finding checked closed *and* biting

Phase baseline for every row: **41 passed** (round 1: 33). Whole files, never `-k`.

| # | closure | measured — contract side / mutation side | verdict |
|---|---|---|---|
| **B1** | C8 row (g): `test_reconciliation_non_narrowing_spec_stays_section_wide_for_participants` calls `reconcile_task_typicals` with `TypicalFilterSpec()` — non-`None`, non-narrowing — asserting `section_wide_uniform`, `applied_filter is None`, and both participants' full 4-tuples | `effective_spec.is_narrowing` → `(spec is not None)`: **41 passed → 1 failed** (was 33 passed / no bite) | **closed, bites** |
| **B2** | C8 per-section tuples on five reconciliation fixtures | M1 `section_typical_worker_seconds` → `narrowed_typical_worker_seconds`: **41 → 4 failed**. M2 `section_sample_count` → `narrowed_sample_count`: **41 → 4 failed** (both were 33 passed) | **closed, both bite** |
| **S1(a)** | C7 row (n) — non-narrowing, narrowed `(61, 600)`, section `(3, None)`, BROADEN → `("insufficient_sample", None, 3)`; the only row where the two predicates disagree | `evidence.has_section` → `evidence.has_narrowed` in the non-narrowing branch: **41 → 1 failed** (was 33 passed) | **closed, bites** |
| **S1(b)** | C7 rows (h)/(m) assert the whole six-field `SelectedTypical` via a new `assert_full_object` column; both rows compare against the *same* literal object, so T17's cross-policy identity is proved transitively, not as `f(a) == f(b)` | `participates=False` → `True` in **both** non-narrowing returns: **41 → 2 failed**, and the two failures are exactly rows (h) and (m) (was 33 passed) | **closed, bites** |
| **S2** | `_optional_values` rejects `str`/`bytes` and non-iterables with `ValidationError`; C14 rows (o)(p)(q) ship as three independent parametrized cases | full mutant (restore the pre-fix body): **41 → 3 failed**. Split per sub-check: drop the `isinstance` guard only → **2 failed** (rows (o),(p)); drop the `iter()` guard only → **1 failed** (row (q)) | **closed, bites — one mutant per sub-check** |
| **N1** | C4(c)/C17 ship as `test_domain_purity.py`, committed in `1590ebe` | `import hashlib` in `typical_filters.py`: **41 → 1 failed**. `from beyo_manager.models.tables.items.item import Item`: **41 → 1 failed**. Disjoint term sets, so each mutant reddens its own guard | **closed, both bite** |
| **N2** | C8 row (c): `test_reconciliation_row_c_has_a_below_floor_participant_fixture`, `below_floor` at count 3 / median `None`, `usable` at 7/600 | Single-cause, verified by re-derivation: `has_usable_narrowed` fails on the **count** alone. It is the correct recorded non-biting control for C8 mutation (ii) — under (ii), `3 >= 5` is still false, so the basis does not move | **closed** |
| **N3** | plan C8 mutation (vii) attribution | corrected text present, but now stale — see **N9** below | closed with a note |
| **N4** | plan C8 row (h) carries the ⚠ keep-single-cause warning; the single-cause twin `test_missing_participant_row_forces_section_wide_uniform_basis` is still in the tree at `test_typical_filters.py:331` | present, verified by reading | **closed** |
| **N5** | plan C15 prose says `is_deleted IS false` | the committed snapshot `snapshots/typical_times_no_spec_sql.txt` renders `is_deleted IS false` — the plan matches the tree | **closed** |

**Independent corroboration of the cited stamp without re-running it.** My measured phase
baseline moved 33 → 41 (+8: grid row (n), row (c) fixture, row (g), three parser rows, two
purity tests). The cited round-3 L4 moved 2609 → 2617 (+8) with `21 failed` unchanged and
∅/∅ both ways. The two arithmetic independently agree, which is what a consumed stamp
should look like.

## 3. New in the delta — four notes, none blocking

**N6 (note) — the purity guard has a *third* escape, distinct from the two carried: the
C17 half passes vacuously on an empty walk.**
`test_domain_purity.py` derives `PACKAGE_ROOT` by path and never asserts the walk found
anything. *Measured:* repoint `PACKAGE_ROOT` at a non-existent directory →
`test_item_economics_domain_has_no_sqlalchemy_or_model_table_imports` **passes** on an
empty `glob`. Its sibling fails loudly, but only by accident — the C4(c) test reads
`serializers.py` to pin the exception, so it raises `FileNotFoundError`. So the *pair* still
reddens if the package is moved or renamed, and N6's genuinely silent surface is narrow.
*Authority:* plan-reviewer doctrine 2 ("would this loop pass vacuously?"). *Correction:* one
line — assert the walk is non-empty (a contract, not the literal `10`, per charter rule 13).
*Disposition:* **plan 4**, folded into the strengthening already scheduled there. This is
the same guard-over-a-guard family the owner ruled on, so it inherits that ruling; I am not
re-opening it here and it does not block.

**N7 (note) — §3C's boundary is now closed for the two value families and still open for
the remaining ones; and three container shapes still slip through `_optional_values`.**
Measured on the checkpoint tree, no mutation:

| input | `_optional_values` today |
|---|---|
| `"cat_a"`, `b"cat_a"`, `5`, `1.5`, `True` | `ValidationError` — the fix's intended surface, complete for scalars |
| `bytearray(b"ab")`, `memoryview(b"ab")` | `frozenset({'97','98'})` — the byte-wise analogue of the defect S2 closed |
| `{"cat_a": 1, "cat_b": 2}` | `frozenset({'cat_a','cat_b'})` — iterates keys |
| `[None]`, `[5]`, `[["a"]]` | `frozenset({'None'})` / `{'5'}` / `{"['a']"}` — `str()` coercion, unchanged |

And one family over, unchanged by this fix: `parse_spec_from_query_params({"can_have_upholstery": "yes"})`
returns a **narrowing** spec whose field is the string `"yes"`, and `{"major_categories": {"wood": 1}}`
returns `frozenset({WOOD})` from a dict's keys. `major_categories` rejects a bare `str`
only *accidentally* — every `ItemMajorCategoryEnum` value is multi-character, so a
single-character member added later would silently reopen the round-1 defect on that family.

None of these is reachable through master plan §6.8's request grammar (a FastAPI-typed
router dict cannot produce a `bytearray`, a `memoryview`, a bare `dict`, or an unparsed
`can_have_upholstery` string), the route is deferred, and there is no caller — so this is
**not** a phase-1 defect and it is outside the allowed production perimeter. *Disposition:*
**plan 2**, which builds the route: the parser is a public contract there, and the same
"structurally satisfies the annotation" reasoning that produced S2 applies to
`can_have_upholstery` and to the enum family's accidental rejection.

**N8 (note) — C8's closing sentence names rows (a), (b), (e), (f), (j); the tuples landed
on a different five, with no detection gap.**
In the tree the full 4-tuple assertions are on: the row-(b)/(h) two-cause fixture
(`…materializes_missing_rows`), row (c), row (e), row (f), row (g) and row (j). The plan's
own **row (b)** — `test_reconciliation_requires_every_participant_to_have_a_usable_narrowed_value`,
the `zero`/`usable` fixture round 1 measured M1/M2 on — still asserts only
`task_typical_basis`, and row (a) has no dedicated two-participant fixture. *This is
bookkeeping, not coverage:* M1 and M2 each redden **four** tests, and the D25 shape the
plan calls out ("in row (b)'s case the published value is `0`") is asserted — the
`…materializes_missing_rows` fixture's section `b` has narrowed median `0` and asserts
`(1200, section_wide, 61, True)`, so M1 flips it to `0` and the row fails. *Correction:*
re-attribute C8's closing sentence to the rows that carry it, exactly as N3 was handled —
a plan edit, not a fix cycle.

**N9 (note) — the N3 correction is itself stale after the repair it was written beside.**
`plans/plan_1.md` C8 mutation (vii) now reads "in the tree the bite lands on **row (d)'s
fixture and the ghost row**". *Measured on the checkpoint tree:* setting `participates=True`
for every section reddens the fixtures for rows **(d), (e) and (f)** — the new excluded-side
tuples assert `participates=False` — and does **not** touch the ghost row, which is a
*participating* section whose `participates is True` the mutant leaves alone. So the
correction names one fixture that cannot bite and omits two that now do. This is charter
rule 12's second half in the wild: *enumerate the mutations from the code after the repair,
never from the finding that requested it.* *Correction:* plan prose only.

## 4. Areas checked with nothing found

- **The new production hunk, structurally.** `ValidationError` derives from
  `DomainError(Exception)` and is **not** a `ValueError` (MRO measured), so
  `parse_spec_from_query_params`'s `except ValueError` cannot swallow the new rejection and
  re-label it "Typical filter range is invalid." The message is per-key
  (`f"{key} must be a sequence of values."`), so rows (o) and (p) are distinguishable on the
  wire. The `iter()` probe consumes nothing and is `TypeError`-scoped, so it cannot mask a
  genuine iteration failure. No C14 row (a)–(n) changes behaviour under the fix — all 41
  pass, and the cited L4 shows the 21-ID failure set unmoved.
- **The participating branches, by variation rather than reproduction.** Four mutants
  nobody named, all biting: publish `section_typical_worker_seconds` in the *uniform-narrowed*
  participating branch → **3 failed**; publish `section_sample_count` there → **3 failed**;
  drop the `has_section` ternary in the non-uniform participating branch (always label
  `section_wide`) → **1 failed** (the ghost row's `insufficient_sample`/`0`); disclaim
  participation in either participating branch → **2 failed** / **4 failed**. The fourth
  tuple element is load-bearing on both sides now, which it was not in round 1.
- **B1's other half, by variation.** The ledger's mutant leaves `applied_filter` at `None`,
  so it never exercised row (g)'s `applied_filter is None` claim. I mutated the *carrier*
  instead — `effective_spec if effective_spec.is_narrowing else None` → `effective_spec` —
  and got **2 failed**. Both halves of row (g)'s contract are independently guarded.
- **Row (g) and row (n) are single-cause.** Row (g): both participants are usable-narrowed,
  so the non-narrowing spec is the only reason the basis is `section_wide_uniform`. Row (n):
  `has_section` false is the only reason the outcome is `insufficient_sample`. Charter rule 2's
  companion holds for both new rows.
- **Rows (h)/(m)'s full-object assertion.** Both compare against a literal `SelectedTypical`
  built from the same `source_evidence` instance, with `participates=False` and
  `sample_count` spelled out — so the T17 claim is object identity, not a projection, and it
  is asserted as two literal rows rather than as an equality between two calls.
- **The exception pin.** `serializers.py` contains exactly **one** occurrence of
  `config_fingerprint` (line 351) and exactly one occurrence of the pinned fragment, so the
  "strips every occurrence" escape carried to plan 4 is genuinely future-conditional, not
  already live. The package is flat with **10** `*.py` modules, matching what C4(c) records.
- **Settled ground, not re-verified** (round 1): the resolution ladder, the reconciliation
  quantifier, the evidence predicates, the fallback, the median, the constants move, the
  `_median` bridge, the SQL snapshot's honesty and its S3 limitation, C6/C11/C13/C16/C18.

## 5. Disposition of the two carried escapes — agreed

I consumed the coordinator's measurement (`2 passed` each for the non-recursive walk and
the strip-every-occurrence exception) and did not re-derive it. I agree with the owner's
ruling: both are guard-over-a-guard strengthenings, neither is reachable in the current
tree, and neither justifies its own implement-and-stamp cycle. `plans/plan_1.md` C4(c)
states the scope phase 1 actually delivers, so the phase is not approved against a claim it
does not meet. **N6 joins them** at the same destination.

## 6. Carry-forward dispositions

| note | destination | why there |
|---|---|---|
| N6 — the C17 guard passes vacuously on an empty walk | **plan 4** | it edits this package and already carries the two measured purity escapes; one line closes all three |
| N7 — `bytearray`/`memoryview`/`dict` still parse, and `can_have_upholstery` / the enum family are unguarded at the same boundary | **plan 2** | plan 2 builds the route and inherits the parser as a public contract |
| N8 — C8's closing sentence names rows the tree does not carry | **`plans/plan_1.md` C8**, coordinator fold | plan prose only; no coverage gap, so no fix cycle |
| N9 — C8 mutation (vii)'s attribution is stale after the repair | **`plans/plan_1.md` C8**, coordinator fold | plan prose only |
| N1's two measured escapes (carried at the fold) | **plan 4** | owner ruling, unchanged |
| S3 (round 1) | **plan 2** | already recorded at the fold |

## 7. My evidence

**Tree identity.** HEAD `aa158ad`; `git diff 1590ebe HEAD -- app/ .archgraph/` is **empty**
(measured), so my application tree *is* checkpoint `1590ebe`. `git status --porcelain` =
`?? .archgraph/contexts/` only — the same untracked session-context directory present at
every stamp in this phase, on no import path — before my probes, between them, and after.

**L4 runs: 0.** The round-3 stamp is **consumed by citation**: `1590ebe`,
`PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`, Redis preflight `PONG`,
**2617 passed / 21 failed / 0 collection errors**, 2638 collected, IDs added ∅ / removed ∅
against the published 21-ID comparator. Its tree identity matches mine exactly, the
`TZ=UTC` obligation was discharged at round 1 on this phase, and a delta re-review on an
unchanged tree introduces no new condition — so re-running it would be over-evidence and a
finding against this round. The +8/+8 arithmetic in §2 is my independent check on it.

**L1 mutation probes: 15.** All whole-file, never `-k`, each applied to a named definition,
run, and reverted before the next.
Command: `PYTHONPATH=. .venv/bin/python -m pytest -p no:randomly -n 0 <the four phase files> -q`
from `backend/app/`. Files:
`tests/unit/domain/item_economics/test_typical_filters.py`,
`…/test_domain_purity.py`, `…/test_participating_sections.py`,
`tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py`.
**Baseline: 41 passed** (round 1's comparator was 33).

| # | site (file · definition) | mutation | contract | mutant | closes |
|---|---|---|---|---|---|
| M3 | `typical_filters.py` · `reconcile_task_typicals` | `effective_spec.is_narrowing` → `(spec is not None)` | 41 passed | **1 failed** | B1 |
| M1 | same · participating non-uniform branch | `section_typical_worker_seconds` → `narrowed_…` | 41 passed | **4 failed** | B2 (viii) |
| M2 | same · participating non-uniform branch | `section_sample_count` → `narrowed_sample_count` | 41 passed | **4 failed** | B2 (ix) |
| M5 | same · `resolve_section_typical` non-narrowing branch | `evidence.has_section` → `evidence.has_narrowed` | 41 passed | **1 failed** | S1(a) |
| M4 | same · both non-narrowing returns | `participates=False` → `True` | 41 passed | **2 failed** (rows (h),(m)) | S1(b) |
| F3 | same · `_optional_values` | restore the pre-fix one-liner | 41 passed | **3 failed** | S2 |
| F3a | same · `_optional_values` | drop the `isinstance(str, bytes)` guard only | 41 passed | **2 failed** (rows (o),(p)) | S2 sub-check 1 |
| F3b | same · `_optional_values` | drop the `iter()` guard only | 41 passed | **1 failed** (row (q)) | S2 sub-check 2 |
| C4c | same · module imports | add `import hashlib` | 41 passed | **1 failed** | N1 / C4(c) |
| C17 | same · module imports | add `from beyo_manager.models.tables.items.item import Item` | 41 passed | **1 failed** | N1 / C17 |
| V1 | `test_domain_purity.py` · `PACKAGE_ROOT` | repoint at a non-existent package | 41 passed | **1 failed** — the C17 guard **passes vacuously**; only the C4(c) guard reddens, via `FileNotFoundError` | **N6** |
| V2 | `typical_filters.py` · uniform-narrowed participating branch | publish `section_typical_worker_seconds` | 41 passed | **3 failed** | variation |
| V3 | same branch | publish `section_sample_count` | 41 passed | **3 failed** | variation |
| V4 | same · `TaskTypicalSelection` construction | `effective_spec if is_narrowing else None` → `effective_spec` | 41 passed | **2 failed** | variation, B1's other half |
| V5 | same · excluded-section `replace(...)` | `participates=False` → `True` (C8 mutation (vii)) | 41 passed | **3 failed** — rows (d), (e), (f); **not** the ghost row | **N9** |
| V7 | same · participating non-uniform branch | `participates=True` → `False` | 41 passed | **4 failed** | variation |
| V6 | same · uniform-narrowed participating branch | `participates=True` → `False` | 41 passed | **2 failed** | variation |
| V8 | same · participating non-uniform branch | drop the `has_section` ternary, always `"section_wide"` | 41 passed | **1 failed** (ghost row) | variation |

**Non-mutating behaviour probes.** The 22-input parser table in N7 (run against the real
`parse_spec_from_query_params`); the `ValidationError` MRO; the `config_fingerprint`
occurrence count in `serializers.py`; the flat module count of the domain package; the
`is_deleted IS false` rendering in the committed snapshot; the graph delta read from
`git diff` rather than from the ledger.

**Mutation-probe declaration.** Files touched by probes, applied and reverted:
`app/beyo_manager/domain/item_economics/typical_filters.py` and
`app/tests/unit/domain/item_economics/test_domain_purity.py`. Both verified byte-identical
after every probe by sha256 —
`typical_filters.py` `4e85f0d2dfb773b0939953fc195bac574cbc37c3b6c44813b86f1bc23f11ca7b`,
`test_domain_purity.py` `265b327832831bfc7e3b4af416fcde04cadf27eb047b41ab08df08b4234e8edd`,
both unchanged from their pre-probe values and both matching the `sourceLinks` content
hashes the checkpoint recorded. `git status --porcelain` shows no tracked modification, and
the four-file suite returns to **41 passed** after the last revert. No database or state
side effects: every probe was unit-only and no probe ran concurrently with anything else.
No architecture-graph node was promoted, rejected or edited.

## 8. Write perimeter

- `docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/reviewer/20260822_plan1_rereview_handoff.md` — this file.

Nothing else. No code, no plan, no master plan, no intention, no archgraph write.
`git status --porcelain` at close: `?? .archgraph/contexts/` (pre-existing, untracked, not
mine) plus this handoff.

**Declared divergence from `plan-reviewer.md` (charter rule 14).** The skill's closing
protocol has the reviewer append findings to the plan file's Review log and move the
tracker row. This prompt forbids editing the plan, the master plan and the intention, and
states the coordinator writes the Review log line at the fold. I followed the prompt. The
coordinator owns folding §§3 and 6 of this handoff into `plans/plan_1.md` §8 and moving
tracker row 1 to **APPROVED**.

## 9. Lessons for the plans

1. **A repair that lands on a different fixture than the plan named leaves the plan lying
   in a way no suite can catch.** Twice now (N3, then N8/N9) the mechanism was guarded and
   the attribution was wrong, and the second time the *correction itself* went stale
   because it was written from the finding rather than re-derived from the repaired code.
   Charter rule 12 already says to enumerate mutations from the post-repair code; the
   cheap enforcement is that a fix cycle re-states, per named mutation, **which test id
   failed** — the implementer has that output in hand and it costs one column.
2. **A guard that walks a directory needs a row proving the walk found something.** N6 is
   the third escape in one small test file, and all three share a shape: the guard's own
   preconditions are unasserted. Any future absence-criterion in this project should ship
   with a non-emptiness assertion in the same test, stated as a contract, not a count.
3. **"Reject the malformed input" is per-family, and the families drift apart.** S2 closed
   two of the four parameter families; `can_have_upholstery` takes any object verbatim and
   `major_categories` rejects a bare string only because no enum member is one character
   long. When a criterion fixes a boundary for one family, it should enumerate the other
   families and say explicitly which ones are in scope and which are deferred.
