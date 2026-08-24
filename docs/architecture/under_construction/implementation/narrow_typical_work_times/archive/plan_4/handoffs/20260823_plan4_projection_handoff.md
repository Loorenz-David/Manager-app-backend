---
plan: plan_4
role: reviewer
round: 0
date: 2026-08-23
actor: Opus 5 (projection r0)
verdict: AMENDMENTS_REQUIRED
---

# Projection handoff — plan 4, `narrow_typical_work_times`

## Opening

Plan 4 is buildable and its engineering is largely right — the criteria are sharp, the
mutations mostly bite, and every domain object it depends on already exists in the code
exactly as the plan describes. But the plan says which files it will touch, and that list is
wrong: I changed the payloads the way phase 4 will change them and measured **two existing
tests, in two files the plan never names, that go red and stay red**. A phase must close
green, so as written it cannot. Four more rows cannot be executed at all — one criterion
compares against a "before" picture that nothing captures, one mutation was designed against
a 3-item list but is applied to a 50-item one, and the goldens are gated on a rule ("only new
keys appear") that the phase's own version bump breaks in both files. Nothing here needs the
owner; every correction is derivable and written out below.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Every finding is a plan amendment derivable from the code or the
intention; no product semantics, contract or authorization is in question.

---

## Ledger

### L1 — **blocking** — §4 "Files expected to change" is incomplete; two out-of-perimeter tests break

**Where:** `plans/plan_4.md` §4, *Modified — tests / goldens*.

**What is wrong:** the list names `test_budget_division.py` and the two goldens. Phase 4's
§7.2/§7.3 key additions and the `ALLOCATION_METHOD` v2 flip redden two tests in two files
that are named neither in §4 nor in §2's Read-first.

**Evidence (measured, probe P1 — see the probe declaration):** I added §7.2/§7.3's new keys to
all four serializers in `division_serializers.py` and flipped `ALLOCATION_METHOD` to
`static_proportional_section_v2`, then ran the scoped surface.

- Baseline, tree `c560779` clean: `tests/integration/services/queries/item_economics/` +
  `tests/unit/domain/item_economics/` + `tests/unit/routers/api_v1/test_budget_division_routes.py`
  → **344 passed / 0 failed**.
- Mutated, same paths + `tests/unit/docs/` → **4 failed / 399 passed**.

The four:

| test | why | self-healing? |
|---|---|---|
| `tests/unit/routers/api_v1/test_budget_division_routes.py::test_time_payload_serializers_have_exact_money_free_key_sets` | `:155` exact key set on `serialize_budget_allocation` (gains `typical_resolution`); `:158` exact key set on `serialize_budget_step` (gains `typical_basis`, `sample_count`) | **no — needs an edit** |
| `tests/integration/services/queries/item_economics/test_production_time_query.py::test_c11_c12_c20_c24_e2_and_e3_agree_and_keep_e2_shape` | `:206` pins the exact literal `ALLOCATION_METHOD == "static_proportional_section_v1"`; `:207` task-entry key set; `:208` step key set | **no — needs an edit** |
| `…/test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files` | re-reads the golden file from disk | yes, on regeneration |
| `…/test_budget_status_filter_spec.py::test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical` | phase-3 row; imports `GOLDEN_DIR`/`_payloads`/`_seed_golden_fixture` from the file above and asserts the same thing | yes, on regeneration |

**Correction:** add to §4 *Modified — tests / goldens*:

```
- app/tests/unit/routers/api_v1/test_budget_division_routes.py
- app/tests/integration/services/queries/item_economics/test_production_time_query.py
```

and add to §5, after task 9:

> **9a. Widen the two pre-existing exact-shape assertions.** Five assertions, named:
> `test_budget_division_routes.py:155` (+`typical_resolution`), `:158`
> (+`typical_basis`, +`sample_count`); `test_production_time_query.py:206` (v1 → v2),
> `:207` (+`typical_resolution`), `:208` (+`typical_basis`, +`sample_count`). Widen, never
> delete — these are the only exact key-set guards on the budget-allocations wire.

Record in §7 that the two golden byte-identity tests are expected red between the payload
edit and the regeneration, and green after — including the **phase-3** row, so a reviewer
does not read a phase-3 regression into it.

### L2 — **blocking** — §4 omits `test_domain_purity.py`, which C0 mandates three edits to

**Where:** `plans/plan_4.md` §4 vs §6 C0.

C0 requires three fixes to `app/tests/unit/domain/item_economics/test_domain_purity.py`
(`glob` → `rglob`; strip only the pinned occurrence; assert the walk is non-empty). §4 does
not list the file, so the implementer's declared perimeter and the reviewer's `git diff`
check will disagree on the one file C0 exists to change.

**Correction:** add `app/tests/unit/domain/item_economics/test_domain_purity.py` to §4
*Modified — tests / goldens*.

### L3 — **blocking** — C12's "key additions only" is false by construction

**Where:** §6 C12 *Review half*; §5 task 10; master plan §7 gate 3.

**Evidence:** both regenerated goldens carry the constant as a **value**:
`golden_production_time.json` → `"allocation_method":"static_proportional_section_v1"` (twice,
`frozen_no_drift` and `idle_no_result`); `golden_budget_allocations.json` → the same, twice.
Task 5 flips it to v2. So the diff necessarily contains a **value change**, and C12's review
half instructs the reviewer to treat exactly that as a gate failure.

§5 task 10 and master plan §7 gate 3 state the *correct*, enumerated form ("any changed
`allowance_seconds`, `left_seconds`, `share_state`, `worked_seconds` or budget figure"). C12's
blanket phrase is the one that is wrong.

**Correction:** replace C12's review-half sentence with:

> the reviewer diffs each regenerated golden against its predecessor and confirms the change
> is **key additions plus exactly one value change — `allocation_method`
> `static_proportional_section_v1` → `static_proportional_section_v2`, twice per file.** Any
> changed `allowance_seconds`, `left_seconds`, `share_state`, `worked_seconds` or budget
> figure is a **gate failure, not a regeneration**.

### L4 — **blocking** — C9(a) has no baseline and cannot be executed as written

**Where:** §6 C9 row (a): *"compared against the pre-refactor payload for the same fixture."*

The fixture is created **in this phase** — `_narrowing_fixture.py` is listed under §4 *New*,
and it does not exist on today's tree (verified: `find tests -name _narrowing_fixture.py` →
nothing). There is therefore no pre-refactor payload for it, and no task in §5 captures one.
By the time task 11 writes the tests, the production code is already refactored, so any
"baseline" taken then is `f(x) == f(x)` — the exact vacuity §11A repaired T11 to remove.

**Correction (preferred):** add a task 0 (see L5) that seeds the no-category task and commits
its production-time and budget-allocations payloads as a snapshot file **before any production
edit**, on the plan-1 SQL-snapshot pattern; C9(a) then diffs against that committed file and
asserts every pre-existing numeric field is unchanged. Add the snapshot path to §4 *New*.
**Alternative, weaker but executable:** restate C9(a) as exact literals for every pre-existing
numeric field, derived from the fixture arithmetic and written into the row.

### L5 — **blocking** — plan 4 has no task 0, and plan 3's approved Review log routes work to one

**Where:** §5 (tasks 1–11).

`plans/plan_3.md:574` routes N2 to **"plan 4 task 0"**, and plan 3's own Review log records its
task 0 as the tests-first red baseline (`plans/plan_3.md:493`: "9 failed / 4 passed … no import
or fixture failures"). Plan 2 did the same. Master plan §9 carries the earned rule
("Tests-first shrinks the transcription-failure class"). Plan 4 — the largest phase, 14
criteria, 4 production files — starts at task 1 with a production change. L4's snapshot also
has nowhere to live without a task 0.

**Correction:** insert:

> **0. Tests-first.** Transcribe every row of §6 C0–C13 into an executable case in
> `test_narrowed_task_economics.py` / `test_budget_division.py` and record the red baseline
> (failing ids and count) in §8 before editing any production file. Capture C9(a)'s
> pre-refactor snapshot here (L4). N2's trigger is inert for this phase (reality check 12) —
> record that rather than acting on it.

### L6 — **blocking** — C10 mutation (ii)'s stated bite is not achievable on a 50-task fixture

**Where:** §6 C10, *Mutations* (ii).

The mutation: *"map tasks to `spec_index` by task insertion order rather than by the spec's
position in the deduped sequence"*, claimed bite: *"the chair task's `sample_count` is the
chair population's (e.g. 20); mutation, it is the table population's (e.g. 15)"*.

**Evidence:** intention §4A K2 — `spec_index ∈ [0, K)` positionally indexes the caller's own
`specs` sequence, and the statement emits *"exactly one row per (live non-deleted working
section × spec_index)"*. With 50 tasks and `K == 3`, task-insertion-order indices run 0–49.
Consequences, per task position:

- task 0 (a chair task) → `spec_index = 0` → chair, **the mutation is inert**;
- task 1 (a chair task) → `spec_index = 1` → table — the only position that produces the
  claimed observable;
- tasks 3–49 (17 further chair tasks and all others) → indices with **no row in the result**
  → zero evidence → `insufficient_sample` / count 0, which is a *different* red from the one
  the criterion claims.

So the row is exposed to both shapes the project has paid for: it **cannot fail** if the
asserted chair task is the first one, and it **fails for the wrong reason** for 17 of the
remaining 19.

**Correction:** replace mutation (ii) with a mis-mapping that is in range by construction:

> (ii) `get_task_budget_allocations` (call site): map each task to `(spec_index + 1) % K`
> instead of to its spec's position → **row (c)** flips: contract, the chair task's step rows
> carry the chair population's `sample_count`; mutation, they carry the table population's.
> Row (b) does not bite — `K` is unchanged. Recorded per rule 12.

and pin row (c)'s subject: *"the chair task at fixture position 0"*, so the assertion is not
silently satisfied by whichever chair task the implementer happens to pick.

### L7 — **should-fix** — C10(b) names no observable, and the plan's spy sentence reads as forbidding one

**Where:** §6 C10 row (b) and *Fixture caution*.

`K` and `spec_index` reach neither the wire nor any domain object (§4A K2: *"Neither
`spec_index` nor any column name appears in a domain object or on the wire"*). Row (b) —
`K == 3`, the five category-less tasks not members — has no instrument. The *Fixture caution*
then says *"only row (a) uses the spy"*, which reads as closing the one instrument that works.

**Derived, not carded** (the answer follows from the code): a `wraps`-style spy installed on
`get_task_budget_allocations.typical_times_statement` satisfies (a) and (b) at once — it counts
the single call **and** captures the `specs=` sequence, while delegating to the real builder so
the request still issues SQL. Rows (c)/(d) are unaffected. Note `get_task_budget_allocations`
issues **12+** `session.execute` calls per request, so a spy on `session.execute` cannot
identify the typicals statement without inspecting the compiled SQL — spy the builder, not the
session.

**Correction:** give row (b) that instrument in the row, and change the caution to *"rows (c)
and (d) must run against a real session; the spy in (a)/(b) delegates, so it is one."*

### L8 — **should-fix** — C1's fixture preconditions are unstated, and rows (a)/(b) can pass under the defect

**Where:** §6 C1 rows (a)/(b) and mutations (i)/(ii).

Three preconditions carry the row, and the plan states none:

1. **≥ 2 participating sections.** `budget_division.py:345-350` computes
   `raw_shares[s] = Fraction(distributable,1) * w_s / total_weight`. With one participating
   section, `w/total == 1` for every value of `w`, so allowances are invariant under **any**
   weight change and mutation (i) is inert by arithmetic. This is the row-that-cannot-fail
   shape.
2. **The substituted section must contain the open WORKING step.** Mutations (i)/(ii) pass
   `live_seconds[step]` into *"one section's"* typical. If that section's steps are all settled,
   `live_seconds[step]` is identical at both `ctx.now` values and the mutation moves nothing.
3. **The two `ctx.now` values must not straddle the 90-day cutoff.** The cutoff is derived from
   the clock (§4A K1), so a straddling pair moves the typicals legitimately and the row reddens
   for the wrong reason.

**Correction:** state all three in C1's fixture line, e.g.: *"Fixture: a chair task with **two**
participating sections, an open WORKING record in section A, and both `ctx.now` values inside
the same 90-day window. Mutations (i)/(ii) substitute `live_seconds` for **section A's**
typical."*

### L9 — **should-fix** — C1(c)'s term set does not decide C1(c)'s claim

**Where:** §6 C1 row (c).

The claim is semantic (*"no site reachable from `divide_production_budget`'s inputs passes a
value derived from `load_live_worked_seconds` into a typical…"*); the instrument is a three-term
sweep expecting **∅**. The sweep cannot return ∅: `total_working_seconds` is present by design
at `budget_division.py:45` (the dataclass field) and at five read sites (`:271`, `:321`, `:331`
twice, `:334`), and both services contain `total_working_seconds=live_seconds[step.client_id]`
verbatim (`get_task_production_time.py:55`, `get_task_budget_allocations.py:222`) — which is the
live-clock contract, not a defect. "Within the typicals path" is not a mechanically checkable
qualifier. §9 also requires absence criteria to ship as committed tests, never as a session
grep.

**Correction:** scope the committed sweep to where ∅ is true and meaningful:

> (c) **absence, L4, roots stated**: `app/beyo_manager/domain/item_economics/typical_filters.py`
> and this phase's evidence-construction helper contain none of `live_seconds`,
> `load_live_worked_seconds`, `total_working_seconds`. Expected ∅/∅.

The semantic claim keeps its real guards — mutations (i)/(ii) on rows (a)/(b).

### L10 — **should-fix** — C2's absence half states no root and no term set, and cannot use the repository root

**Where:** §6 C2, *"and that no payload anywhere carries `static_proportional_section_v1`"*.

§9 requires an absence claim to state its root and term set. Run from the repository root the
claim is **false and must be**: three published frontend handoffs
(`HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md:90,170,187`,
`…_share_state_answer_20260819.md:100,122`, `…_worker_step_card_budget_allocations_20260822.md:62`)
and the archived `simple_production_budget_division` plan set carry the v1 string as history,
and §9 forbids rewriting a published handoff.

**Correction:** *"(c) **absence, L2, root = `app/beyo_manager/` plus the two regenerated goldens,
term = `static_proportional_section_v1`.** Expected ∅. Published handoffs and archived plans are
out of root by construction — the new value is announced to the frontend in phase 6."*

### L11 — **should-fix** — C7 has two rows and one mutation

**Where:** §6 C7 (rule 12).

Row (b) — a well-sampled narrowed **excluded** section on a `section_wide_uniform` task showing
`item_narrowed` — is unarmed; C7's only mutation is stated to flip row (a).

**Verified reachable at source:** `typical_filters.reconcile_task_typicals`' excluded branch
calls `resolve_section_typical(evidence, effective_spec, BROADEN_TO_SECTION)`, whose first rung
returns `("item_narrowed", narrowed_typical_worker_seconds, narrowed_sample_count)` when
`has_usable_narrowed`. So row (b) is a real shape, not a hypothetical.

**Correction:** add

> (ii) `typical_filters.reconcile_task_typicals` (definition): give excluded sections the task's
> uniform basis instead of resolving them independently → **row (b)** flips `item_narrowed` →
> `section_wide`. It also flips row (a)'s excluded row `section_wide` → `item_narrowed`; both
> bites recorded per rule 12.

### L12 — **should-fix** — C5 mutation (i)'s stated post-mutation value is fixture-dependent

**Where:** §6 C5, mutation (i): *"emit the filled weight as `typical_worker_seconds` → row (a)
flips `null` → `1` (the `Fraction(1,1)` rendered)."*

`budget_division.py:339` is `fallback = median(usable) if usable else Fraction(1, 1)`. The
filled weight is `1` **only if no participating section in that fixture has a usable typical**.
C5(a)'s fixture is not pinned, and C5(c) asks the same task for
`sections_by_basis.insufficient_sample >= 1`, which implies other sections exist. If any of them
is usable, the mutated value is the median of those, not `1`, and the ledger's stated observable
is wrong — the shape §9 names as *"a named mutation's stated bite set is a claim, and it decays"*.

**Correction:** either pin C5(a)'s fixture ("no participating section has a usable typical") or
restate the observable: *"row (a) flips `null` → the resolved fallback weight (a non-null
integer-valued `Fraction`); the fixture states which."*

### L13 — **should-fix** — C8's mutation is a refactor, and its contract side has an unstated fixture precondition

**Where:** §6 C8.

*Mutation:* "`get_task_production_time` (call site): move reconciliation inside
`divide_production_budget`" is a multi-file refactor with no single site, and "inside" is
ambiguous. A named mutation should be a legal, small, sited edit.

**Correction:** *"`get_task_production_time` (call site): guard the evidence/reconcile block with
the same `status.status in {OK, INFEASIBLE}` condition already used for the budget argument
(`get_task_production_time.py:99-106`) → the no-budget task's `typical_resolution` is absent."*
Same bite, one line, and it is the defect shape F-D actually warns about.

*Contract side:* C8 asserts `task_typical_basis == "item_narrowed_uniform"` for a chair task.
`reconcile_task_typicals` sets that only when **every** participating section has
`has_usable_narrowed`; master plan §6.9's seed gives ≥5 same-category groups in **two** sections
and **<5 in a third**. If the fixture task's steps span all three, the basis is
`section_wide_uniform` and the row fails for a reason that is not the defect.
**Correction:** state that C8's task uses only the two well-sampled sections.

### L14 — **should-fix** — four of four `budget_division.py` citations have drifted

**Where:** §5 tasks 2 and 4; §6 C4 and C8.

Re-derived by locating each symbol on tree `c560779`:

| plan cites | plan says it is | actual | what is at the cited line |
|---|---|---|---|
| `:264` | the two-argument `.get` default | **271** | `typicals: Mapping[str, int \| None],` — a parameter annotation |
| `:324` | the `if typical is None` read | **329** (`if`), read at **331** | `usable: list[Fraction] = []` |
| `:338-343` | `… / total_weight` | **344–350**; the `/ total_weight` is at **348** | the fallback block (`Fraction(0,1)` / `median(usable)` / the `weight <= 0` loop) |
| `:285-305` | the `allowed_worker_minutes is None` early return | **292–312** | `) -> dict[str, Any]:` |

All four are low by 5–7 lines, consistent with plan 1's added import block at the head of the
file. §9: *"a line number handed to a session is a claim with a shelf life"* — and task 4 instructs
the implementer to delete something at `:264`, where there is nothing to delete.

**Verified correct and not to be re-derived:** `get_task_production_time.py:50-62` ✓;
`get_task_budget_allocations.py:217-229` ✓; `division_serializers.py:36-47` ✓ (the function is
36–46); `division_serializers.py:102-108` ✓; `production_time.py:30-41` ✓ (the file is
`get_task_production_time.py` — the §7 note drops the `get_task_` prefix).

### L15 — **should-fix** — the `fake_status` widening is a plan-5 obligation, misrouted into plan 4

**Where:** §2, third bullet: *"The first phase that reads `budget_status.typical_filter_spec`
gets an `AttributeError` from it — phase 3 does not … but you do. Widen the fake before you read
the field."*

**Evidence:** `test_price_scenario_query.py:47` binds
`module = import_module("beyo_manager.services.queries.item_economics.get_task_price_scenario")`,
and every `monkeypatch.setattr(module, "get_task_budget_status", fake_status)` (`:574`, `:978`,
`:1120`, `:1279`) patches **that** module. Repo-wide, nothing fakes `get_task_budget_status` for
`get_task_production_time` — it resolves the real service everywhere (`test_production_time_query.py`,
`test_live_clock_goldens.py`, `test_phase2_live_surfaces.py` all run it against `db_session`).
Phase 4 does not touch price-scenario (§1: *"Explicitly NOT in this phase"*), so it never reaches
the fake. Acting on the instruction would edit `test_price_scenario_query.py`, which is not in §4
— an automatic perimeter finding at review.

**Second half:** plan-3 projection L15 named **one** fake at `:559-560`. The surface is **four**
(`:559`, `:955`, `:1097`, `:1256`); the latter three are three-line `SimpleNamespace(status=…,
item_binding=…)` constructions.

**Correction:** delete the bullet from plan 4 §2 and move it to `plans/plan_5.md`'s Read-first,
with the corrected count of four fakes and their four line numbers.

### L16 — **should-fix** — §5 task 4 counts the smaller edit surface and not the larger one

**Where:** §5 task 4.

The plan's three counts are **all correct as measured** (see reality check 4). What is uncounted
is the third argument: **24 `divide_production_budget(` call sites** in
`test_budget_division.py`, each passing an int/None-valued typicals mapping (25 typicals-shaped
dict literals matched, two of which are `allowances ==` assertions → 23 argument sites). Task 1
changes that parameter to `Mapping[str, SelectedTypical]` and task 3 makes `_step_result` read
`typical_basis` and `sample_count` off it, so **every one of those literals must become a
`SelectedTypical`** — and it is those literals, not the `typical=` passes, that supply the values
C3(b) and C5(a)/(b) assert.

**Correction:** append to task 4: *"and the **24** `divide_production_budget(` call sites in the
same file, whose int-valued third argument (23 literals) becomes `Mapping[str, SelectedTypical]`.
That is the larger surface and the one that carries C3/C5's asserted values. Count at source
before editing."*

### L17 — **note** — Read-first omissions

- **Master plan §5** (contract resolution) is not listed. It carries the
  `architecture/*.md` authority (*"Any phase touching errors, commands, queries or routers reads
  the matching numbered file before writing"* — phase 4 touches queries) and the living-docs
  guard obligation (*"Any phase changing a published payload or a method constant checks whether
  the guard names a file it must update"* — phase 4 does both).
- **Master plan §8** (tool protocols) is not listed, and §7's graph paragraph paraphrases it more
  weakly: §7 says *"prefer symbol anchors over line spans, but not both on one entry"*; §8's
  interim owner policy is binding and absolute — ***"do not emit `startLine`/`endLine`."***
- **Master plan §6.1** is cited by task 1 but not listed.
- **`test_live_clock_goldens.py`** is named by C12 but appears in neither §2 nor §4. The
  implementer must read its `_seed_golden_fixture` / `_payloads` to regenerate the goldens at all.

### L18 — **note** — C13(a) names no observable

*"`divide_production_budget`'s `allocated_groups` predicate and the services' participating set
resolve to `participating_sections`"* is a structural claim with no assertion. **Derived, not
carded:** monkeypatch `budget_division.participating_sections` to a disagreeing form and assert
that both the division's section rows and each service's rendered set move — one implementation is
observable precisely as "one patch moves all three". Add it to the row.

### L19 — **note** — C11's exact literal is quoted inconsistently

Contract side reads `("540", "item_narrowed", 7)`; mutation side reads `(600, "section_wide", 61)`.
`typical_worker_seconds` is an int on the wire (`division_serializers.py:103`, no `_decimal`
wrapper). A stray quote inside an exact-literal criterion is the transcription class §9 names.

### L20 — **note** — C0 escape 1's mutation creates a file inside the production package

`…/domain/item_economics/sub/leak.py` must be deleted **and its parent directory removed**; a
leftover sits inside the implementer's own diff and is indistinguishable from intended work
(charter, checkpoint rationale). Name it in the round's mutation-probe declaration.

---

## Reality checks (verified correct — do not re-verify)

1. **Gate.** Master plan §4: phases 1–3 `APPROVED`, phase 4 `PROJECTING`; `plans/plan_4.md`
   header `state: PROJECTING`. The two agree.
2. **Tree.** `git merge-base --is-ancestor 353a8c9 HEAD` succeeds; `git status --porcelain` shows
   only ` M .archgraph/agent-operating-policy.md` (owner's live edit) and `?? .archgraph/contexts/`.
   No modified tracked file under `app/`.
3. **Every phase-1/2/3 output the plan depends on exists as described.** `typical_filters.py`
   carries `COMPARABILITY_PROFILE`, `RECONCILIATION_METHOD`, `TypicalFilterSpec` (+`is_narrowing`),
   `derive_spec_from_primary_item`, `parse_spec_from_query_params`, `SectionTypicalEvidence`
   (+`has_narrowed`/`has_section`/`has_usable_narrowed`), `TypicalResolutionPolicy`,
   `SelectedTypical`, `resolve_section_typical`, `TaskTypicalSelection`, `reconcile_task_typicals`,
   `apply_business_fallback` (with the `isinstance(terminal, Fraction)` entry guard),
   `median`. `TaskBudgetStatus.typical_filter_spec` is the last field, defaulted `None`
   (`get_task_budget_status.py:56`). `typical_times_statement(workspace_id, *, now=None, specs=())`
   (`get_working_section_typical_times.py:28-35`).
4. **§5 task 4's three counts are all correct.** Measured in `test_budget_division.py`:
   `DivisionStep(` **8×**; **6** of them pass `typical_worker_seconds`; `typical=` appears **20×**.
5. **§7 sequencing constraint 4 holds.** `get_task_production_time.py:50-62` and
   `get_task_budget_allocations.py:217-229` both construct `DivisionStep(..., typical_worker_seconds=None, ...)`.
   `DivisionStep(` exists in exactly three files repo-wide (those two plus `test_budget_division.py`).
6. **C0's three escapes are all still present and reproducible on today's tree** — no other phase
   closed them. `test_domain_purity.py:10` is `PACKAGE_ROOT.glob("*.py")` (non-recursive);
   `:22` is `source.replace("config_fingerprint", "")` (strips every occurrence);
   `:26-29` has no non-emptiness assertion, and its sibling reads `serializers.py` at `:16` so it
   fails only by `FileNotFoundError`. Two supporting measurements: `serializers.py` contains
   **exactly one** occurrence of `fingerprint` (`:351`), so escape 2's prescribed fix produces no
   false red; and `domain/item_economics/` has **no subpackage** and **10** modules, so escape 1's
   `rglob` fix changes nothing today (its mutation must create the file) and escape 3's fix must
   assert non-emptiness rather than `== 10` (rule 13), exactly as the plan says.
7. **C5 row (b) / T16b′ is reachable exactly as written.** `has_section` is count-based
   (`section_sample_count >= TYPICAL_MIN_SAMPLE_SIZE`, `typical_filters.py:149-150`), and the
   participating non-uniform branch emits `section_typical_worker_seconds` verbatim, so a
   section-wide median of `0` at count ≥ floor yields `typical_basis: "section_wide"`,
   `typical_worker_seconds: 0`.
8. **C6's mutation bites as stated.** The excluded section resolves independently through
   `resolve_section_typical(..., BROADEN_TO_SECTION)` to `item_narrowed`, so counting all of
   `selected` instead of the participating ids gives `{1, 2, 1}` summing to 4 ≠ 3.
9. **C4's mutation reddens by raising, as the plan says.** With `terminal=Fraction(0,1)` and no
   usable typical, `apply_business_fallback` returns all-zero weights, `total_weight` is
   `Fraction(0,1)`, and `budget_division.py:348`'s `/ total_weight` raises `ZeroDivisionError`.
   (Holds only while `allocated_groups` is non-empty, which C4's fixture guarantees.)
10. **C2's constant mutation reaches every publish site.** Repo-wide there are exactly three in
    `app/beyo_manager/`: `division_serializers.py:129` (production-time task block),
    `division_serializers.py:56` (`row.get("allocation_method", ALLOCATION_METHOD)`), and
    `get_task_budget_allocations.py:255`, which supplies the row consumed by `:56`. No fourth.
11. **The living-docs guard does not pin the new keys or the method constant.** `tests/unit/docs/`
    stayed green under probe P1 (full payload additions + v2). No file under
    `docs/domains/item_economics/` needs updating in phase 4 — but plan 4 should record that the
    check was made (master plan §5: *"the guard, not judgement, decides"*).
12. **N2's trigger does not fire in phase 4.** Neither budget-status service is in the perimeter,
    and neither phase-4 service gains a query: task 8's spec derives from the already-loaded
    `item_by_id`/`primary_by_task`, task 7's from `status.typical_filter_spec`. `_ScalarSession`'s
    eight rows in `test_budget_status_filter_spec.py` are unaffected.
13. **C13(b) is reachable as written.** A FAILED-only group fails
    `any(not _step_state_is_excluded(step) …)` (`budget_division.py:316-320`), so it is not in
    `allocated_groups` and renders `share_state: "excluded"` with `allowance_seconds: None`.
14. **§4's *New* entries are genuinely new.** Neither `_narrowing_fixture.py` nor
    `test_narrowed_task_economics.py` exists on this tree.
15. **D20 says what §5 task 5 says it says.** `planning/owner_decisions.md:122-126` carries the
    ruling and the owner's precision requirement verbatim, including *"The contract changes even
    where an individual numeric result does not."*

## Refutations (things I set out to break and could not)

- **"C2's mutation cannot see budget-allocations."** `serialize_budget_allocation` reads
  `row.get("allocation_method", ALLOCATION_METHOD)` — a caller-supplied override with the constant
  only as a default, which looked like an escape from the definition-side mutation. It is not:
  `get_task_budget_allocations.py:255` supplies the constant itself, so reverting the definition
  flips both faces. The only caller-supplied literal in the repository is a hand-built fixture at
  `test_budget_division_routes.py:132`, and it is `static_proportional_v1` — a different string,
  which also means C2's absence half does not trip on it.
- **"The two golden byte-identity tests need editing."** They do not. Both re-read the golden file
  from disk (`(GOLDEN_DIR / f"golden_{name}.json").read_text().strip()`), so regeneration closes
  them without a test edit. They failed under probe P1 only because the probe changed payloads
  without regenerating — the expected transient. Worth recording in §7 so a reviewer does not read
  a phase-3 regression into the second one.
- **"The docs guard forces a `docs/domains/item_economics/` edit."** Measured green under P1
  (reality check 11).
- **"C5(a)'s two assertions are two independent sufficient causes."** They are not.
  `typical_worker_seconds: null` and `typical_basis: "insufficient_sample"` both follow from
  `section_sample_count < TYPICAL_MIN_SAMPLE_SIZE`, but the second is produced by
  `reconcile_task_typicals` and the first by the SQL's own floor, so the row still discriminates a
  reconciliation defect that changes the basis while the value stays null.

---

## Tree projected against

```
$ git log --oneline -1
c560779 docs(narrow-typicals): dispatch phase-4 projection, and name the in-flight state the machine lacked
```

`git status --porcelain` at entry:

```
 M .archgraph/agent-operating-policy.md      (owner's live edit — untouched)
?? .archgraph/contexts/                      (expected)
```

at exit:

```
 M .archgraph/agent-operating-policy.md
?? .archgraph/backfill/                      (NOT MINE — see below)
?? .archgraph/contexts/
?? docs/.../handoffs/reviewer/20260823_plan4_projection_handoff.md   (this file)
```

**`?? .archgraph/backfill/` appeared during this session and this session did not create it.** No
`archgraph_*` tool was called at any point in this projection, and no probe wrote outside the two
files declared below. It is reported rather than absorbed: the most likely explanation is the
owner's concurrent archgraph policy work (the modified `agent-operating-policy.md` is the same
work), but a projection cannot assert that, so the coordinator should confirm its provenance
before the next perimeter check treats it as a baseline.

`git diff --stat -- app/` is **empty** at exit. No file under `app/` was left modified. No
production code, test or golden was edited. No document outside this handoff was written.

## Mutation-probe declaration

One probe, **P1**, applied and reverted within this session.

**Hypothesis:** phase 4's §7.2/§7.3 key additions and the `ALLOCATION_METHOD` v2 flip redden
pre-existing tests outside `plans/plan_4.md` §4's declared perimeter.

**Files touched, with checksums:**

| file | before | after probe | after revert |
|---|---|---|---|
| `app/beyo_manager/domain/item_economics/division_serializers.py` | `b43d805632dac749f08d846e837d0258` | (5 key additions) | `b43d805632dac749f08d846e837d0258` ✓ |
| `app/beyo_manager/domain/item_economics/budget_division.py` | `1191db5fdd50eeac9f2ed28043080632` | (`ALLOCATION_METHOD` → v2) | `1191db5fdd50eeac9f2ed28043080632` ✓ |

**Edits, each asserted to have landed inside the intended symbol** (each `replace` guarded by an
`assert count == 1`, then re-grepped by line):
`serialize_budget_step` +`typical_basis` +`sample_count` (landed `:46`, `:47`);
`serialize_budget_allocation` +`typical_resolution` (`:59`);
`serialize_production_time_section`'s `typical` block +`typical_basis` +`narrowed_sample_count`
+`section_sample_count` (`:111-113`); `serialize_task_production_time` +`typical_resolution`
(`:136`); `budget_division.ALLOCATION_METHOD` (`:25`).

**Evidence records:**

| # | scope | command | tree identity | result |
|---|---|---|---|---|
| E1 (baseline) | L2 + routes | `BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest tests/integration/services/queries/item_economics/ tests/unit/domain/item_economics/ tests/unit/routers/api_v1/test_budget_division_routes.py -n 0 -p no:randomly -q` | `c560779`, `app/` clean | **344 passed / 0 failed**, 7.26s |
| E2 (mutated) | E1's paths + `tests/unit/docs/` | same invocation, paths as above plus `tests/unit/docs/` | `c560779` + P1 diff | **4 failed / 399 passed**, 8.90s — ids in L1 |

`redis-cli ping` → `PONG` before both runs. No concurrent suite session in this checkout. **No L4
run** — this is a projection and nothing has been implemented; the absence claims C1(c) and C13(c)
belong to the implementing round, not to this one.

## Verdict

**AMENDMENTS_REQUIRED** — 6 blocking, 10 should-fix, 4 notes, 0 owner cards.
The blocking six (L1–L6) must land in `plans/plan_4.md` before the implementer prompt is compiled;
L1, L2 and L5 also change §4 and §5, which the prompt is generated from.
