# Plan 4 — The division contract, production-time and budget-allocations

```
plan: plan_4
project: narrow_typical_work_times
state: CHANGES_REQUESTED
projection_gate: MANDATORY — SATISFIED (round 0, 2026-08-23, AMENDMENTS_REQUIRED, fully routed)
```

## 1. Goal

Turn the engine on for task economics: both division consumers derive a spec, call the
statement with specs, build `SectionTypicalEvidence`, reconcile through
`uniform_basis_v1`, and feed **the same `SelectedTypical`s** to display and to weights.
`divide_production_budget`'s third parameter becomes `Mapping[str, SelectedTypical]`,
`DivisionStep.typical_worker_seconds` and both fallback reads are removed,
`ALLOCATION_METHOD` becomes v2, and §7.2/§7.3's new keys ship.

**Explicitly NOT in this phase:** price-scenario — it never calls division, and its clock
change, its private ladder and `is_estimated` are **plan 5**. `/working-sections/typical-times`
stays byte-identical (D24). No new domain object (plan 1 shipped them). No statement change
(plan 2 shipped it). No `/statistics/typical-times` route.

**Why two consumers are in one phase:** changing `divide_production_budget`'s third parameter
breaks both call sites at once, and a phase must close green.

## 2. Read first

- Master plan §§4, **5**, **6.1**, 6.2, 6.4, 6.5, 6.7, 6.9, 7, **8**, 9, 10.
  Three of these are added at the projection fold (L17) and each binds this phase directly:
  **§5** carries the `architecture/*.md` authority (*"any phase touching errors, commands,
  queries or routers reads the matching numbered file before writing"* — you touch queries)
  **and** the living-docs guard obligation (*"any phase changing a published payload or a
  method constant checks whether the guard names a file it must update — the guard, not
  judgement, decides"* — you do both; the projection measured the guard **green** under the
  full payload additions plus v2, so no `docs/domains/item_economics/` file needs editing,
  but §11's record of the check is still owed). **§6.1** is cited by task 1 and was unlisted.
  **§8** is the tool-protocol home; §7 of this plan paraphrased it more weakly and has been
  corrected — read §8, not the paraphrase.
- Intention **header**, then §2.2 F-C/F-D/F-E/**F-F (stale — see §2B S-4)**/F-G/F-H,
  §2B S-4, S-5, S-6, S-7, §3.5, §3.6, **§3B** in full, §4.3, **§4A** K1–K4
  (**including §4A K2-a** — the shipped `K ≥ 1` column order is the reverse of K2's prose;
  **read the result by column name, never by position**. You are a consumer of this
  statement; K2-a is inside your K1–K4 range by adjacency, and named here so it is not
  picked up by luck — phase-2 re-review N-b), **§4B**,
  **§4C**, §4.5, §6.1, §6.2 rows 2/3/6, §6.3, §6.4 (**superseded on `is_estimated` by §6B —
  but §6B's division half binds here**), **§6C** in full, §7.2, §7.3, §8, §11.1 rows
  T1/T2/T3/T4/T5/T6/T7/T8/T9/T16/T21, **§11A** in full (T10a, T16b as amended by §4C, T23,
  T24, and the correction to §8), §11.2.
- ~~**`test_price_scenario_query.py`'s `fake_status` …** Widen the fake before you read the
  field.~~ **WITHDRAWN at the projection fold (L15, measured 2026-08-23) — do not act on it.**
  All four `fake_status` installs patch the **price-scenario** module
  (`test_price_scenario_query.py:47` binds `module = import_module("…get_task_price_scenario")`;
  the installs are `:574`, `:978`, `:1120`, `:1279`). Repo-wide, **nothing** fakes
  `get_task_budget_status` for `get_task_production_time` — it resolves the real service in
  every test that runs it. Price-scenario is **explicitly not in this phase** (§1), so you
  never reach the fake, and editing `test_price_scenario_query.py` would put you outside §4's
  perimeter — an automatic finding at review. The obligation is **plan 5's**, where it now
  lives, with the corrected count of four fakes rather than one.
- **`test_live_clock_goldens.py`** — C12 names it and task 10 cannot be done without it. Read
  its `_seed_golden_fixture` and `_payloads` helpers: they are how the goldens are regenerated,
  and `test_budget_status_filter_spec.py` imports the same three symbols (L17).
- **`plans/plan_3.md` §6B, and the two phase-3 review notes routed here (2026-08-23).** You
  are the **first publisher** of `typical_filter_spec`, so both fire in this phase:
  - **N1 — a key-set criterion must serialize a *service-produced* object, not a locally
    constructed one.** Phase 3's manager key-set row serializes a hand-built
    `TaskBudgetStatus` whose `typical_filter_spec` is the dataclass default `None`, so it is
    **blind to a value-gated publish** (`if spec is not None: payload[...]`). **Measured
    twice** — review probe P2 and coordinator re-verification, both **3 failed / 125 passed**
    with `test_C2_manager_budget_status_payload_has_the_existing_exact_key_set` staying
    **green** while the worker row and both goldens go red. **When you edit that row to
    publish the field, give it a populated spec or build the status through
    `get_task_budget_status`** — otherwise your new publishing criterion inherits the same
    blindness on the face that carries money.
  - **N2 — `_ScalarSession`'s length is an unstated assertion about the query count**, and
    **eight rows** in `test_budget_status_filter_spec.py` depend on it (C4 ×2, C3a, C5 ×5).
    **Trigger, not a scheduled task: the first phase that adds or removes a query in either
    budget-status service turns all eight red with `RuntimeError: coroutine raised
    StopIteration`, a message that names nothing.** If this phase changes either service's
    query sequence, **make the double content-aware in the same round** (dispatch on the
    statement's target entity) rather than extending the value list. Phase 3 paid a full fix
    round to this mechanism; master plan §9 carries the rule.
- `planning/owner_decisions.md` — D2, D7, D9, D12, D16, D18, D20, D22, D23, **D25**.
- Gate handoff §2 rows 5, 8, 12, 14 and §5.
- **The neighbouring pipeline's approved authority, read at source:**
  `docs/architecture/archives/live_clock_for_working_time_economics/planning/intention.md`
  §1A HC-1A (never assign to `TaskStep.total_working_seconds`), §2.5A (the eight-row settled
  consumer inventory — row 5 is this statement), §4.3A (**three** paths from worked seconds
  to `allowance_seconds`; path 3 is the typicals statement).
- Code: `budget_division.py` (whole file); `division_serializers.py` (whole file);
  `get_task_production_time.py` (whole file); `get_task_budget_allocations.py` (whole file);
  `test_budget_division.py`.
- **INHERITED TRIPWIRE — read it before you write a line of either service.**
  *(Added at the coordinator consumption fold — C-2, measured 2026-08-23.)*
  `app/tests/unit/services/queries/item_economics/test_production_time_contract.py::test_c19_division_has_one_allocator_and_services_only_consume_it`
  asserts, for **both** `get_task_production_time.py` and `get_task_budget_allocations.py`,
  that their source contains none of the tokens **`Fraction`**, `ROUND_HALF_EVEN`, `largest`,
  or `//`. It is a **substring check on the file**, so an *import* trips it as surely as
  arithmetic does. **Measured on the clean tree: 17 passed; with `from fractions import
  Fraction` added to `get_task_production_time.py`, 1 failed / 16 passed** at the `Fraction`
  assertion.
  **This is a signal, not an obstacle**, and it is satisfiable: the weight ladder and its
  `terminal=` live in `budget_division.py` (task 2), `apply_business_fallback` is imported
  there at module scope (task 1), and the services only ever hand over `SelectedTypical`s.
  If you find yourself reaching for `Fraction` inside a service, the arithmetic has leaked
  out of the domain layer and C19 is telling you so. **C4's mutation is therefore applied at
  the definition, never at the service call site** — see §6B C-2.
  The whole directory `tests/unit/services/queries/item_economics/` (17 tests) is outside
  every path set this phase's projection ran; treat it as unmeasured until you run it.

## 3. Dependencies

**Gate: plan 3 `APPROVED`.** production-time reads `status.typical_filter_spec`, which plan 3
adds; budget-allocations derives its own from `item_by_id` / `primary_by_task`.

## 4. Files expected to change

**Modified — production**
- `app/beyo_manager/domain/item_economics/budget_division.py`
- `app/beyo_manager/domain/item_economics/division_serializers.py`
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`

**Modified — documentation (unguarded by any test — see §6B C-1)**
- `app/beyo_manager/routers/README.md` — **added at the coordinator consumption fold (C-1).**
  It enumerates, field by field, the exact response schema of **both** endpoints this phase
  changes: `data.budget_allocations[].steps[].*` and `data.budget_allocations[].allocation_method`
  (≈`:1660-1680`), and `data.allocation_method` + `data.sections[].typical` (≈`:1700-1725`).
  Its own header states the rule: *"Hand-maintained. No generator exists in this repository…
  A route added without editing this file silently rots it."* **No test reads this file** —
  the living-docs guard roots at `docs/domains/item_economics/`, which is why probe P1 came
  back green on it and why a test-based projection could not see it. See task 9c.

**Modified — tests / goldens**
- `app/tests/unit/domain/item_economics/test_budget_division.py`
- `app/tests/unit/routers/api_v1/test_budget_division_routes.py` — **added at the projection
  fold (L1, measured).** Its `:155` / `:158` exact key-set assertions redden under §7.2/§7.3
  and do **not** self-heal. See task 9a.
- `app/tests/integration/services/queries/item_economics/test_production_time_query.py` —
  **added at the projection fold (L1, measured).** Its `:206` v1 literal and `:207` / `:208`
  exact key sets redden and do **not** self-heal. See task 9a.
- `app/tests/unit/domain/item_economics/test_domain_purity.py` — **added at the projection
  fold (L2).** C0 mandates three edits to this file; it was absent from this list, so the
  implementer's declared perimeter and the reviewer's `git diff` would have disagreed on the
  one file C0 exists to change.
- `app/tests/integration/services/queries/item_economics/goldens/golden_production_time.json`
- `app/tests/integration/services/queries/item_economics/goldens/golden_budget_allocations.json`

**New**
- `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py`
- `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`
- `app/tests/integration/services/queries/item_economics/snapshots/no_category_task_prerefactor.json`
  — **added at the projection fold (L4).** The pre-refactor payload snapshot C9(a) diffs
  against, captured in **task 0** on the plan-1 SQL-snapshot pattern. Written once, before any
  production edit, and **never regenerated** — re-capturing from a refactored tree restores
  exactly the `f(x) == f(x)` vacuity §11A repaired T11 to remove (master plan §9).

**Read-only, and a change is a finding**
- `goldens/golden_budget_status.json` · `get_task_price_scenario.py` ·
  `get_working_section_typical_times.py` · the plan-1 SQL snapshot.

## 5. Ordered tasks

0. **Tests-first, and the C9(a) baseline.** *(Added at the projection fold — L5. Plan 4 is
   the largest phase and had no task 0; plans 2 and 3 both opened with one, `plans/plan_3.md`
   routes N2 to **"plan 4 task 0"** by name, and master plan §9 carries the earned rule
   "tests-first shrinks the transcription-failure class".)*
   - Transcribe **every row of §6 C0–C13** — and every criterion's **prose** clauses, not only
     its row tables (§9's closing-sentence rule) — into executable cases in
     `test_narrowed_task_economics.py` / `test_budget_division.py`, before editing a line of
     production code. Record the red baseline (failing ids **and** count) in §8.
     A row that cannot be transcribed is a **plan defect — stop and report**, never a row to
     invent.
   - **Capture C9(a)'s pre-refactor snapshot here** (L4): seed the no-category task, serve
     production-time and budget-allocations against it, and commit both payloads to
     `snapshots/no_category_task_prerefactor.json`. This must happen **before any production
     edit** — after task 1 the "baseline" is `f(x) == f(x)`.
   - **N2's trigger is inert for this phase — record that, do not act on it.** Measured at the
     projection: neither budget-status service is in this perimeter and neither phase-4 service
     gains a query (task 8's spec derives from the already-loaded `item_by_id` /
     `primary_by_task`; task 7's from `status.typical_filter_spec`), so
     `_ScalarSession`'s eight rows in `test_budget_status_filter_spec.py` are unaffected.
   - **N1 binds when you edit phase 3's key-set row** to publish `typical_filter_spec`: give it
     a **populated** spec or build the status through `get_task_budget_status`. A hand-built
     `TaskBudgetStatus` carries the dataclass default `None` and is blind to a value-gated
     publish.
1. **`divide_production_budget`'s third parameter becomes `Mapping[str, SelectedTypical]`.**
   Annotate under `if TYPE_CHECKING:`; at runtime keep reading through the existing
   `_value(obj, name)` helper, which already accepts objects and mappings alike. Import
   `apply_business_fallback` from `typical_filters` at module scope — the cycle was broken in
   plan 1 by moving the constants (master plan §6.1).
2. **The weight ladder delegates to `apply_business_fallback(..., terminal=Fraction(1, 1))`.**
   Usable = not `None` and `> 0`; the arithmetic is identical to today's, and D22's two
   terminals stay two. `Fraction(1,1)` is **also a division-by-zero guard**: with
   `terminal = 0` and no usable typical anywhere in the task, every resolved weight is `0`,
   `total_weight` is `0`, and `budget_division.py:344-350`'s `… / total_weight` — the division
   itself is at **`:348`** — **raises** (§11A's correction to §8). C4's mutation therefore
   reddens by raising.
   *(Span corrected at the projection fold, L14, re-derived twice. The plan cited `:338-343`,
   which is the **fallback block** — `median(usable)`, `Fraction(1,1)`, the `weight <= 0`
   loop — not the division. **All four** of this plan's `budget_division.py` citations were
   low by 5–7 lines, consistent with plan 1's added import block at the head of the file.
   Master plan §9: a line number handed to a session is a claim with a shelf life. Every
   corrected number below is a **checksum to compare against, never the target** — locate the
   symbol in the file at the moment you edit it, and a disagreement is a stop-and-report,
   because it means the tree moved again.)*
3. **`_step_result` emits `typical_basis` and `sample_count`** from the `SelectedTypical`,
   and its `typicals.get(section_id, _value(step, "typical_worker_seconds"))` becomes a
   lookup whose miss is contracted by **§3B B4** — never a `KeyError`, never a step-attribute
   read. Section rows carry the same two fields.
4. **Remove `DivisionStep.typical_worker_seconds` and both fallback reads**
   (`budget_division.py:271`'s two-argument `.get` default and `:329`'s
   `if typical is None` branch, whose step-attribute read spans **`:330-333`**).
   *(Spans corrected at the projection fold, L14, re-derived twice. The plan cited `:264` and
   `:324`; `:264` is the `typicals: Mapping[str, int | None]` **parameter annotation** and
   `:324` is `usable: list[Fraction] = []` — this task instructed the implementer to delete
   something at `:264`, where there is nothing to delete.)*
   **The removal edits two PRODUCTION files** —
   `get_task_production_time.py:50-62` and `get_task_budget_allocations.py:217-229` both pass
   `typical_worker_seconds=None` (**both verified correct at the fold**) — plus the test
   constructors. §11.1 says "8 test constructors"; measured, `DivisionStep(` appears 8× in
   `test_budget_division.py` but only **6** pass the field, and the `typical=` argument passes
   number **20**. All three counts are correct as written.
   **The larger surface is a fourth one this task did not count** (L16): there are **24**
   `divide_production_budget(` call sites in the same file, whose int/`None`-valued third
   argument (**23** typicals-shaped dict literals; the other two matches are `allowances ==`
   assertions) becomes `Mapping[str, SelectedTypical]` once task 1 changes the parameter and
   task 3 makes `_step_result` read `typical_basis` and `sample_count` off it. **Those literals,
   not the `typical=` passes, supply the values C3(b) and C5(a)/(b) assert.** Count all four
   surfaces at source before editing.
   `:329`'s surrounding `if typical is None` branch is **not** deleted — only the read inside it.
5. **`ALLOCATION_METHOD` → `static_proportional_section_v2`** (§6.3, D20). §6.3's phrasing is
   **normative for the frontend handoff** and must not be paraphrased: *"Every task is now
   evaluated under the new rule; allowances are **eligible** to change wherever item-category
   narrowing changes the relative section weights… The contract changes even where an
   individual numeric result does not."*
6. **`divide_production_budget`'s internal exclusion predicate delegates to
   `participating_sections`** (§6.1) — one implementation, not a fourth copy.
7. **production-time.** Spec from `status.typical_filter_spec`. `specs=()` when the spec is
   non-narrowing or `None`; otherwise `specs=(spec,)` (§4A K3: callers normalize, and pass
   only *narrowing* specs). Keep `now=ctx.now` — **unchanged**. Build
   `SectionTypicalEvidence` per section, `participating_sections(steps)`, then
   `reconcile_task_typicals`. **Reconcile BEFORE division** (F-D): the
   `allowed_worker_minutes is None` branch returns early computing no participating set, yet
   production-time still renders sections, so the no-budget branch must also get a complete
   reconciled block. The **same** `SelectedTypical`s feed the `typicals` display block and
   the division weights.
   Note §2B S-7: production-time scopes the statement to **every** step's section.
8. **budget-allocations.** Derive one spec per task from `item_by_id` / `primary_by_task`
   (already loaded — zero additional queries). **Dedupe by value** into an ordered sequence of
   *narrowing* specs; a task whose spec is non-narrowing maps to `spec_index = None` and takes
   `narrowed_* := section_*` with a section-wide basis (§4A K3, §3B B1). **One statement call
   for the batch.** If every task's spec is non-narrowing, pass `specs=()`. Keep
   `now=ctx.now` — unchanged. Per-task reconciliation, then division.
   Register the local name `spec_index_by_task` for the mapping back.
9. **§7.2 / §7.3 payloads.** `division_serializers.py` enumerates its keys explicitly
   (`:36-47`, `:102-108`) — new fields must be added **by name**, with the always-present
   defaults of §7. Add `serialize_filter_spec` and `serialize_typical_resolution` here
   (master plan §6.5) so plan 5 imports one implementation.
9a. **Widen the two pre-existing exact-shape assertions.** *(Added at the projection fold —
    L1, measured. Probe P1 applied §7.2/§7.3's key additions to all four serializers and
    flipped `ALLOCATION_METHOD` to v2 on tree `c560779`: baseline **344 passed / 0 failed**,
    mutated **4 failed / 399 passed**. Two of the four are in files this plan never named,
    and neither self-heals.)* **Five assertions, named:**
    - `test_budget_division_routes.py:155` — `set(serialize_budget_allocation(task))` gains
      `typical_resolution`;
    - `test_budget_division_routes.py:158` — `set(serialize_budget_step(...))` gains
      `typical_basis` and `sample_count`;
    - `test_production_time_query.py:206` — the exact literal
      `ALLOCATION_METHOD == "static_proportional_section_v1"` becomes `…_v2`;
    - `test_production_time_query.py:207` — the task-entry key set gains `typical_resolution`;
    - `test_production_time_query.py:208` — the step key set gains `typical_basis` and
      `sample_count`.

    **Widen, never delete.** These are the only exact key-set guards on the budget-allocations
    wire; deleting one converts a caught regression into a silent one.
    **Not in scope:** `test_budget_division_routes.py:151`'s `serialize_typical_time` key set
    is the `/working-sections/typical-times` serializer, which D24 holds byte-identical.
    Verified at the fold: it is a distinct function, untouched by §7.2/§7.3. A change to it is
    a finding.
9c. **Update the hand-maintained router contract.** *(Added at the coordinator consumption
    fold — C-1.)* `app/beyo_manager/routers/README.md` documents both changed endpoints as
    field-by-field response tables. Add the new rows in the same format and flip nothing else:
    - `GET …/tasks/{task_client_id}/budget-allocations` — under
      `data.budget_allocations[].steps[]`, add `typical_basis` and `sample_count`; under
      `data.budget_allocations[]`, add `typical_resolution`.
    - `GET …/tasks/{task_client_id}/production-time` — under `data`, add `typical_resolution`;
      keep the existing `data.sections[].typical` row and add the section-level keys §7.2
      ships.
    **Derive each row from the serializer you actually wrote, not from this list** — this list
    is a checklist of places to look, and master plan §9 says a count in a plan sentence that
    counts to nothing is worse than no count.
    **Nothing tests this file.** It cannot fail your suite, which is exactly why it is a task
    and not a criterion: the only thing standing between it and rot is you doing it. Declare
    it in your write perimeter.
10. **Goldens.** Regenerate `golden_production_time.json` and `golden_budget_allocations.json`
    on the post-live-clock baseline. **The live-clock fixture is NOT taught to narrow.** It has
    no COMPLETED steps (F-H), so post-refactor it yields counts `0`, basis
    `insufficient_sample`, `task_typical_basis: "section_wide_uniform"`, `applied_filter: null`
    and — one section — an unchanged allowance.
    **Regeneration is approved only if the diff is key additions plus exactly one value
    change** — `allocation_method` `static_proportional_section_v1` →
    `static_proportional_section_v2`, **twice per file**. *(Corrected at the projection fold,
    L3, measured: both goldens carry the constant as a **value**, twice each — under
    `frozen_no_drift` and `idle_no_result` — so task 5's flip puts a value change in the diff
    **by construction**. The blanket "key additions only" phrasing was false as written and
    would have failed its own gate.)* Any changed `allowance_seconds`, `left_seconds`,
    `share_state`, `worked_seconds` or budget figure means the refactor moved something it was
    not supposed to move: that is a **gate failure, not a regeneration**.
11. Tests per §6. **Run the living-docs guard** (`PYTHONPATH=. pytest tests/unit/docs/`) and
    **record the result in §8** — master plan §5: the guard, not judgement, decides whether a
    `docs/domains/item_economics/` file needs updating. (The projection measured it green under
    the full payload additions plus v2, so the expected answer is "none"; the record of having
    checked is still owed.) Record the architecture-graph delta (one batched `apply_changes`,
    **no `startLine`/`endLine`** — master plan §8). Update state in **both** places: the
    `master_plan.md` §4 tracker row **and** this file's `state:` header and §8 Review log.

## 6. Tests / acceptance criteria

### C0 — inherited: strengthen the domain-purity guard (three measured escapes)

**Carried here from phase 1** (owner ruling 2026-08-22: a guard-over-a-guard does not
justify its own implement-and-stamp cycle; it belongs to the phase that already edits the
code it guards — this one). `app/tests/unit/domain/item_economics/test_domain_purity.py`
holds phase 1's C4(c) and C17 as committed tests. **Three escapes were measured on the
approved phase-1 tree; do not re-measure them, close them:**

| # | escape | measured | fix |
|---|---|---|---|
| 1 | the package walk is `glob("*.py")`, **non-recursive** — a module in a future subpackage is never scanned | `import hashlib` in `…/item_economics/sub/leak.py` → **2 passed** | `rglob("*.py")` |
| 2 | the pinned exception strips **every** occurrence of `config_fingerprint`, not the pinned line, so a second use in another shape is erased before the assertion sees it | a second, differently-shaped use appended to `serializers.py` → **2 passed** | strip only the pinned occurrence; keep the `count(...) == 1` pin |
| 3 | the C17 half **passes vacuously on an empty walk** — nothing asserts the walk found anything (its sibling fails only by accident, via `FileNotFoundError` when it reads `serializers.py` to pin the exception) | `PACKAGE_ROOT` repointed at a non-existent directory → that test **passes** | assert the walk is non-empty, **as a contract, not the literal `10`** (rule 13) |

*Named mutations, all three required, both sides:* re-apply each escape above; each must
now redden. **Escape 1's mutation creates a file inside the production package** (L20):
`…/domain/item_economics/sub/leak.py` must be deleted **and its parent directory removed** —
a leftover sits inside your own diff and is indistinguishable from intended work (charter,
checkpoint rationale). Declare it by name in the round's mutation-probe declaration.
*Measured at the fold, so escape 3's fix is not written as a literal:* the package has **no
subpackage** and **10** modules today, so escape 1's `rglob` fix changes nothing until its
mutation creates the file, and escape 3 asserts **non-emptiness as a contract, never `== 10`**
(rule 13). `serializers.py` contains **exactly one** occurrence of `fingerprint` (`:351`), so
escape 2's prescribed fix produces no false red. Plus the two regression probes that already bite and must continue to:
`import hashlib` in `typical_filters.py`, and
`from beyo_manager.models.tables.items.item import Item`.
*Defect caught:* a purity guard that phases 4 and 5 rely on while it silently guards
nothing — escape 3 is the shape that makes the whole file a no-op.
*Standing rule this earned (master plan §9):* **a guard that walks a directory needs a row
proving the walk found something.** Three escapes in one small file, all the same shape:
the guard's own preconditions were unasserted.

---

Hypothesis scope: L1 = `test_narrowed_task_economics.py` / `test_budget_division.py`.
C1's third row and C13's sweep are **absence claims** and run at **L4** with their roots and
term sets stated. C5, C7, C11 and C12 name cross-file bite sets and run at L2 =
`tests/integration/services/queries/item_economics/` + `tests/unit/domain/item_economics/`.

**C1 — typicals stay settled-basis (§6C, T24). Critical rank 5.**

**Fixture — three preconditions, all load-bearing** *(added at the projection fold, L8; the
plan stated none, and rows (a)/(b) pass under the defect without them)*: a chair task with
**two participating sections**, an **open WORKING record in section A**, and both `ctx.now`
values **inside the same 90-day window**. Mutations (i)/(ii) substitute `live_seconds` for
**section A's** typical.
1. **≥ 2 participating sections.** `budget_division.py:345-350` computes
   `raw_shares[s] = Fraction(distributable,1) * w_s / total_weight`. With **one** participating
   section `w/total == 1` for every value of `w`, so allowances are invariant under **any**
   weight change and mutation (i) is inert *by arithmetic* — the row-that-cannot-fail shape
   this project has paid for eleven times.
2. **The substituted section must contain the open WORKING step.** The mutations pass
   `live_seconds[step]` into one section's typical; if that section's steps are all settled,
   `live_seconds[step]` is identical at both `ctx.now` values and the mutation moves nothing.
3. **The two `ctx.now` values must not straddle the 90-day cutoff**, which is derived from the
   clock (§4A K1) — a straddling pair moves the typicals *legitimately* and the row reddens for
   the wrong reason.

(a) **production-time**: a task with an open WORKING record, served **twice at two `ctx.now`
values** over identical database state → every `allowance_seconds` is identical across the
two calls, asserted as exact literals per section.
(b) **budget-allocations**: the same task, the same two `ctx.now` values → the same equality,
asserted separately. (One probe per member: a blanket "both consumers are settled" claim needs
its own row per consumer.)
(c) **absence, L2, roots stated** *(rewritten at the projection fold, L9 — the original could
not return ∅ and so could not decide its own claim)*:
`app/beyo_manager/domain/item_economics/typical_filters.py` **and this phase's
evidence-construction helper** contain none of `live_seconds`, `load_live_worked_seconds`,
`total_working_seconds`. **Expected ∅ / ∅**, as a committed test (§9: absence criteria ship as
tests, never as a session grep).
*Why the root shrank, and what did not shrink with it:* the original claim was **semantic**
("no site reachable from `divide_production_budget`'s inputs passes a live-derived value into
a typical") but its instrument was a three-term sweep from the repository root expecting ∅ —
and that sweep **cannot** return ∅. `total_working_seconds` is present *by design* at
`budget_division.py:42` (the dataclass field) and at five read sites (`:133`, `:234`, `:273`,
`:321`, `:391`) — **citations re-derived at the coordinator consumption fold (C-3); the
projection's own `:45` / `:271` / `:331` / `:334` were wrong, and this fold had transcribed
them unverified.** The finding's substance is unaffected: six occurrences in one file, all
legitimate. And both services carry
`total_working_seconds=live_seconds[step.client_id]` verbatim
(`get_task_production_time.py:55`, `get_task_budget_allocations.py:222`) — which **is** the
live-clock contract, not a defect. "Within the typicals path" is not a mechanically checkable
qualifier. The semantic claim keeps its real guards: **mutations (i)/(ii) on rows (a)/(b)**,
which are what actually discriminate. This row now guards the narrower thing it can prove —
that the pure engine and the evidence builder never learned the live clock.
*Mutations, one per sub-check*:
(i) `get_task_production_time` (call site): pass `live_seconds[step]` into one section's
`SelectedTypical.typical_worker_seconds` → **row (a)** flips: contract, allowances identical;
mutation, that section's weight ticks, `total_weight` changes, `_largest_remainder`
redistributes, and **every** section's allowance moves between the two calls.
(ii) `get_task_budget_allocations` (call site): the same substitution → **row (b)** flips;
row (a) does **not** — recorded per rule 12.
*Why this row exists*: the neighbouring pipeline calls a "make it consistent" change here
**"the most expensive mistake available in this feature"**, and records that no guard against
it existed anywhere in the repository until its own phase 2 round 6. After this phase, both
consumers hand `divide_production_budget` `DivisionStep`s whose `total_working_seconds` **is**
the live figure, alongside typicals that must not be. **The two live in the same call.**
*Also binding*: charter rule 3 / HC-1A — no code in this phase assigns to
`TaskStep.total_working_seconds`, ever. Assert it: after serving both endpoints against the
open-record task, the column re-read from the database is unchanged.

**C2 — `ALLOCATION_METHOD` is v2 on every surface that publishes it.**
Assert the exact literal `"static_proportional_section_v2"` on production-time's task block
and on every budget-allocations task entry.
(c) **absence, L2, root = `app/beyo_manager/` plus the two regenerated goldens, term =
`static_proportional_section_v1`. Expected ∅.** *(Root and term added at the projection fold,
L10 — §9 requires an absence claim to state both, and this one had neither.* ***Run from the
repository root the claim is false and must be:*** *three published frontend handoffs
(`HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`,
`…_share_state_answer_20260819.md`, `…_worker_step_card_budget_allocations_20260822.md`) and
the archived `simple_production_budget_division` plan set carry the v1 string as **history**,
and §9 forbids rewriting a published handoff. Published handoffs and archived plans are out of
root by construction — the new value is announced to the frontend in **phase 6**.)*
*Measured at the fold, so the root is known to be exactly right:* v1 has **three** publish
sites in `app/beyo_manager/` — `division_serializers.py:56`, `:129` and
`get_task_budget_allocations.py:255` — plus the definition at `budget_division.py:25`, and
`test_production_time_query.py:206`, which task 9a converts. No fourth.
*Mutation* — `budget_division.ALLOCATION_METHOD` (definition): revert to v1.
*Both sides* — contract: both payloads carry v2; mutation: both carry v1.
*Rule 13 note*: this criterion pins a configured **value** as an exact literal, deliberately.
The version string **is** the contract the frontend keys on (D20, §6.3) — it is not the
time-bomb shape rule 13 forbids, which is pinning an incidental setting.

**C3 — `DivisionStep.typical_worker_seconds` is gone, and its absence is total.**
(a) `"typical_worker_seconds" not in {f.name for f in fields(DivisionStep)}`.
(b) `divide_production_budget` given a section id present in the steps and **absent** from
the selection mapping produces a step row with `typical_worker_seconds: None`,
`typical_basis: "insufficient_sample"`, `sample_count: 0`, and its `allowance_seconds`
computed — never a `KeyError` (§3B B4).
(c) A soft-deleted working section named by a task's steps produces row (b)'s shape end to
end on production-time.
*Mutation* — `budget_division._step_result` (definition): index the selection mapping with
`[]`.
*Both sides* — contract (b): the row exists with those three values; mutation: `KeyError`.
*Defect caught*: today's two-argument `typicals.get(section_id, _value(step,
"typical_worker_seconds"))` fires its default only on a **missing key**, never on a `None`
value — an accidental cover that D18's removal deletes. §3B B4 is what replaces it.

**C4 — T4 row (a): the division terminal, and its second job.**
Fixture: a task where **no** participating section has a usable typical (all `None`).
Assert every `allowance_seconds` is the even split of `distributable_seconds` — exact
literals — and that the neutral weight appears **nowhere** as seconds on the payload.
*Mutation* — ~~`get_task_production_time` (call site) /~~ **`budget_division` (definition)
only**: pass `terminal=Fraction(0, 1)` to `apply_business_fallback`.
**The call-site option is struck at the coordinator consumption fold (C-2, measured).** The
terminal is set inside `budget_division.py` and never threaded through a service; applying
this mutation at `get_task_production_time` puts the token `Fraction` into that file, which
reddens `test_c19_division_has_one_allocator_and_services_only_consume_it` (**1 failed / 16
passed**, measured) — a *collateral* red in a file this plan does not list, not the
`ZeroDivisionError` the row claims. That is the "fails for the wrong reason" shape.
*Both sides* — contract: the even split; mutation: `total_weight == 0` and
`budget_division.py:348` raises `ZeroDivisionError` (span corrected at the fold, L14; verified
reachable — with `terminal=Fraction(0,1)` and no usable typical every resolved weight is `0`,
so `total_weight` is `Fraction(0,1)` and the division raises, **provided `allocated_groups` is
non-empty, which this fixture guarantees**). **The row reddens by raising, not by
asserting a different number** — say so in the test's docstring, because a reader who expects
a value mismatch will "fix" the test.
*T4 row (b)* — price-scenario's `Fraction(0,1)` terminal — is **plan 5 C4**. Each row bites on
its own terminal.

**C5 — layer-2 visibility on division surfaces (T16, T16b′, §6.4, §3B B2).**
| # | fixture | expected step/section row |
|---|---|---|
| a | participating section whose **selected** value is `None` (section-wide count below floor) | `typical_worker_seconds: null`, `typical_basis: "insufficient_sample"`, `sample_count: <section_sample_count>` (§3B B3), `allowance_seconds` present and non-null |
| b | **T16b′** — a `section_wide_uniform` task with a participating section whose **section-wide** median is `0` at count ≥ floor | `typical_worker_seconds: 0`, `typical_basis: "section_wide"`, `sample_count: <n>`, `allowance_seconds` present |
| c | task level, row (a)'s task | `sections_by_basis.insufficient_sample >= 1` |
*Mutations, one per sub-check*:
(i) `budget_division._step_result` (definition): emit the filled weight as
`typical_worker_seconds` → **row (a)** flips `null` → **the resolved fallback weight** (a
non-null value; **row (a)'s fixture states which**). Row (b) does not bite.
*(Observable restated at the projection fold, L12. The plan said the flip is `null` → `1`,
"the `Fraction(1,1)` rendered". That is true **only if no participating section in the fixture
has a usable typical** — `budget_division.py:339` is
`fallback = median(usable) if usable else Fraction(1, 1)`. C5(a)'s fixture is not pinned, and
C5(c) asks the same task for `sections_by_basis.insufficient_sample >= 1`, which implies other
sections exist; if any of them is usable the mutated value is the **median of those**, not `1`,
and the ledger's stated observable would be wrong. Master plan §9: a named mutation's stated
bite set is a claim, and it decays. **Pin C5(a)'s fixture — "no participating section has a
usable typical", which makes the flip exactly `1` — or write the resolved fallback into the
row. Either is acceptable; leaving it unstated is not.**)*
(ii) `_step_result` / `division_serializers` (definition): publish `null` +
`insufficient_sample` for a zero-valued statistic → **row (b)** flips `0`/`section_wide` →
`null`/`insufficient_sample`. Row (a) does not bite — recorded per rule 12.
*§4C note, so row (b)'s fixture is not "corrected" back*: §11A's original T16b used **7
same-category groups all summing 0** and expected `typical_basis: "item_narrowed"`. D25 made
that shape unreachable on task surfaces — a zero narrowed median now disqualifies the
narrowed rung. The **reachable** zero form is `section_wide` + `0`, which is row (b). The
assertion (a zero statistic is disclosed as a statistic, never as `insufficient_sample`) is
unchanged.

**C6 — `sections_by_basis` counts participating sections only, and sums to
`participating_section_count` (§7.2).**
Fixture: 3 participating (0 `item_narrowed` / 2 `section_wide` / 1 `insufficient_sample`) and
1 **excluded** section whose independently-resolved basis is `item_narrowed`.
Assert `sections_by_basis == {"item_narrowed": 0, "section_wide": 2,
"insufficient_sample": 1}` (exact dict literal) and `participating_section_count == 3`, and
that the two agree: `sum(sections_by_basis.values()) == participating_section_count`.
*Mutation* — `division_serializers.serialize_typical_resolution` (definition): count every
section in `selected` instead of the participating ones.
*Both sides* — contract `{0, 2, 1}` summing to 3; mutation `{1, 2, 1}` summing to 4 ≠ 3.
*Defect caught*: excluded rows blurring the reconciliation story the object exists to tell.

**C7 — T9 excluded independence, both directions, on the wire.**
(a) a thin **excluded** section beside participating sections that are all
`has_usable_narrowed` → `task_typical_basis` stays `"item_narrowed_uniform"` **and** the
excluded row shows its **section-wide** value with `typical_basis: "section_wide"`.
(b) mirrored — a well-sampled narrowed **excluded** section on a `section_wide_uniform`
task → the excluded row shows `"item_narrowed"` while every participating row shows
`"section_wide"`.
*Mutations — two, one per row* *(the second added at the projection fold, L11: C7 had two rows
and one mutation, so row (b) shipped unarmed — charter rule 12)*:
(i) `typical_filters.reconcile_task_typicals` (definition): include excluded ids in
the quantifier → **row (a)** flips `item_narrowed_uniform` → `section_wide_uniform`.
(ii) `typical_filters.reconcile_task_typicals` (definition): give excluded sections the task's
uniform basis instead of resolving them independently → **row (b)** flips the excluded row's
`item_narrowed` → `section_wide`. It **also** flips row (a)'s excluded row `section_wide` →
`item_narrowed`; both bites recorded per rule 12.
*Row (b) is verified reachable at source, not hypothetical* (fold): the excluded branch calls
`resolve_section_typical(evidence, effective_spec, BROADEN_TO_SECTION)`
(`typical_filters.py:314`), whose first rung (`:201-206`) returns
`("item_narrowed", narrowed_typical_worker_seconds, narrowed_sample_count)` when
`has_usable_narrowed`.
*Both sides* — exact `task_typical_basis` string literals, and exact `typical_basis` literals
on the excluded row.
*Note*: plan 1 C8 row (e) observes the **same** mutation at the domain layer. This row is
**variation, not redundancy** — a different site and a different observable (the serialized
payload rather than the returned object), which is exactly what the charter's reuse rule buys
independent verification with.
*Consequence, stated so it is never reported as a bug*: an excluded row's `typical_basis` may
differ from the participating rows' uniform basis, in either direction.

**C8 — T8: the no-budget branch reconciles (F-D).**
Fixture: a task whose economics status is outside `{OK, INFEASIBLE}` (so
`allowed_worker_minutes is None`).
Assert production-time still returns a **complete** `typical_resolution` block — all six keys
present, `task_typical_basis` a real value, `applied_filter` populated for a chair task — and
a complete per-section `typical` block for every rendered section, with
`allowance_seconds: null` and `share_state: "no_budget"`.
**Fixture precondition, added at the projection fold (L13):** C8's task uses **only the two
well-sampled sections**. `reconcile_task_typicals` sets `task_typical_basis ==
"item_narrowed_uniform"` only when **every** participating section has `has_usable_narrowed`
(`typical_filters.py:279`), and master plan §6.9's seed gives ≥5 same-category groups in **two**
sections and **<5 in a third**. If the fixture task's steps span all three, the basis is
`section_wide_uniform` and the row fails for a reason that is not the defect.

*Mutation* — `get_task_production_time` (call site): guard the evidence/reconcile block with the
same `status.status in {OK, INFEASIBLE}` condition already used for the budget argument
(`get_task_production_time.py:99-106`, verified at the fold) → the no-budget task's
`typical_resolution` is absent.
*(Mutation replaced at the projection fold, L13. The original — "move reconciliation inside
`divide_production_budget`" — is a **multi-file refactor with no single site**, and "inside" is
ambiguous; a named mutation must be a legal, small, **sited** edit (charter rule 11). The
replacement has the same bite in one line, and it is the defect shape F-D actually warns
about: a careless implementer reuses the status guard and silently drops the no-budget
branch's reconciliation.)*
*Both sides* — contract: `typical_resolution` present with `task_typical_basis ==
"item_narrowed_uniform"`; mutation: the `allowed_worker_minutes is None` early return
(`budget_division.py:292-312` — span corrected at the fold, L14; `:285-305` lands on
`) -> dict[str, Any]:`) computes no participating set, so the block is absent.

**C9 — T3 + T23: the no-category task converges, and its new string fields tell the truth.**
Fixture: a task whose primary item has no `item_category_id`.
(a) **Every pre-existing numeric field is unchanged** on production-time and
budget-allocations, diffed against **`snapshots/no_category_task_prerefactor.json`** — the
payload pair captured in **task 0, before any production edit**. §4A K5's wording is normative
and must not be paraphrased: here "unchanged" means *every pre-existing numeric field
unchanged*, **not** byte-identical, since §7.2/§7.3 add keys.
*(Baseline added at the projection fold, L4 — as written the row could not be executed. The
fixture is created **in this phase** (`_narrowing_fixture.py` is a §4 **New** entry and does
not exist on today's tree, verified), so there was no pre-refactor payload for it and no task
captured one. By the time task 11 writes the tests the production code is already refactored,
so any "baseline" taken then is `f(x) == f(x)` — the exact vacuity §11A repaired T11 to remove.
The snapshot follows the plan-1 SQL-snapshot pattern and is **never regenerated**: a red C9(a)
in a later round is a **finding**, not a re-capture.)*
(b) The statement is called with `specs=()` — the K == 0 shape.
(c) `task_typical_basis == "section_wide_uniform"`, every participating `typical_basis ==
"section_wide"`, `applied_filter is None`.
*Mutations, one per sub-check*:
(i) `typical_filters.derive_spec_from_primary_item` (definition): return a non-empty spec for
category-less items → **rows (b), (c)** flip: the statement takes the K ≥ 1 branch and
`applied_filter` is non-null.
(ii) `typical_filters.reconcile_task_typicals` (definition): consult `has_narrowed` before
checking `spec.is_narrowing` → **row (c)** flips `section_wide_uniform` →
`item_narrowed_uniform` beside a **null** filter. **Row (a) does not bite** — it asserts
numeric identity, and these are new string fields. That is precisely why T23 exists as a
separate row.

**C10 — batch dedupe: K distinct specs, one statement call.**

**Fixture: 50 tasks — 20 chair, 15 table, 10 stool, 5 with no category — plus completed
history per category whose populations are DISCRIMINATING.** *(Second clause added at the
coordinator fold; see "the layer below" note under the mutations.)* The chair, table and stool
populations must yield **different `sample_count`s and different medians**, and no median may
equal the mean of another's groups. A fixture that seeds every category alike satisfies row
(c) under both the contract and the mutation — master plan §9, *a uniform fixture is an inert
fixture*.

Assert: (a) exactly **one** execution of `typical_times_statement` in the request;
(b) `K == 3` — the five category-less tasks are **not** members of the sequence (§4A K3);
(c) **the chair task at fixture position 0** carries the chair population's `sample_count` on
its step rows, asserted as an exact literal *(subject pinned at the fold, L6 — otherwise the
assertion is silently satisfied by whichever chair task the implementer happens to pick)*;
(d) each of the five category-less tasks carries `typical_basis: "section_wide"` and
`applied_filter: null`.

**The instrument for (a) AND (b)** *(rewritten at the projection fold, L7 — row (b) had no
instrument at all, and the fixture caution read as forbidding the only one that works)*: a
`wraps`-style spy installed on **`get_task_budget_allocations.typical_times_statement`**. It
counts the single call *and* captures the `specs=` sequence — which is the only place `K` is
observable, since §4A K2 puts neither `spec_index` nor `K` on the wire or in any domain object
— while **delegating to the real builder**, so the request still issues SQL.
**Spy the builder, not the session:** `get_task_budget_allocations` issues **eleven**
`session.execute` calls per request (measured), so a session-level spy cannot identify the
typicals statement without inspecting compiled SQL. The name is imported into the service
module (`get_task_budget_allocations.py:37`), so `monkeypatch.setattr(module,
"typical_times_statement", spy)` is the install.

*Mutations, one per sub-check* — both in `get_task_budget_allocations` (call site):
(i) dedupe by `id(spec)` instead of by value → **row (b)** flips `K == 3` → `K == 45`.
(ii) map each task to **`(spec_index + 1) % K`** instead of to its spec's position in the
deduped sequence → **row (c)** flips: contract, the chair task's step rows carry the **chair**
population's `sample_count`; mutation, they carry the **table** population's. Row (b) does not
bite — `K` is unchanged. Recorded per rule 12.
*(Mutation (ii) replaced at the projection fold, L6. The original — "map tasks to `spec_index`
by task insertion order" — **cannot achieve its stated bite on a 50-task fixture**. Per §4A K2
`spec_index ∈ [0, K)` and the statement emits exactly one row per (live section × spec_index),
so with 50 tasks and `K == 3`, insertion-order indices run 0–49: task 0 (a chair task) maps to
index 0 → chair, so **the mutation is inert**; only task 1 produces the claimed observable; and
tasks 3–49 map to indices with **no row in the result** → zero evidence →
`insufficient_sample` / count 0, a **different red from the one the criterion claims.** The row
was exposed to both failure shapes this project has paid for: it could not fail if the asserted
chair task was the first one, and it failed for the wrong reason for 17 of the remaining 19.
The replacement is in range by construction.)*

***The layer below, added by the coordinator:*** *L6 fixes the mutation's **site** but not the
fixture's **arithmetic**. Under `(spec_index + 1) % K` the chair task reads the table
population — which only reddens row (c) if the two populations report **different**
`sample_count`s. C10's fixture line counts **tasks** (20/15/10/5); `sample_count` counts
**completed section groups in the 90-day window**, which this fixture line never states. Seed
the three categories' history to distinct counts and distinct medians, and write those numbers
into the row as the exact literals it asserts. (Master plan §9, twice over: "confirm the
fixture contains a row the mutation moves", and "a fold that corrects a defect one layer down
inherits the obligation to check the layer below it.")*

*Defect caught*: Critical rank 3 (two specs meaning one population becoming two indices) and
Critical rank 2 (a mis-keyed row attributing one category's history to another task), observed
at the caller rather than at the SQL.
*Fixture caution*: the corpus rule — **before citing a test as proof of a SQL predicate, check
that the test issues SQL.** **Rows (c) and (d) must run against a real session; the spy in
(a)/(b) delegates, so it is one.** *(Restated at the fold, L7 — the original read "only row (a)
uses the spy", which closed the only instrument row (b) has.)*

**C11 — HC-2, first half (T6a): production-time and budget-allocations agree.**
For every participating section of the same task at the same frozen `ctx.now`, the triple
`(typical_worker_seconds, typical_basis, sample_count)` from production-time's section
`typical` block **equals** budget-allocations' step row's — asserted per section as exact
literals on **both** sides, never as an equality between two calls.
*Mutation* — `get_task_budget_allocations` (call site): resolve typicals locally instead of
through the shared selection (e.g. take `section_typical_worker_seconds` unconditionally).
*Both sides* — contract: both surfaces report `(540, "item_narrowed", 7)`-shaped triples;
mutation: budget-allocations reports `(600, "section_wide", 61)` where production-time reports
`(540, "item_narrowed", 7)`. *(Quote corrected at the projection fold, L19: the contract side
read `("540", …)` and the mutation side `(600, …)` — inconsistent within one criterion.
`typical_worker_seconds` is an **int** on the wire (`division_serializers.py:103`, no
`_decimal` wrapper), so the unquoted form is right. A stray quote inside an exact-literal
criterion is the transcription class master plan §9 names.)*
*This row also discharges charter rule 10* (operational reachability): its fixture is an
ordinary seeded chair task under the **shipped default** configuration, and it asserts
`task_typical_basis == "item_narrowed_uniform"` — the narrowing path is reached by the
defaults, not only by tests.

**C12 — goldens: key additions plus one named value change.**
*Automated half*: after regeneration, the live-clock golden fixture's payloads carry the new
keys at their documented defaults — `typical_basis: "insufficient_sample"`,
`narrowed_sample_count: 0`, `section_sample_count: 0`, `sample_count: 0`,
`task_typical_basis: "section_wide_uniform"`, `applied_filter: null`,
`sections_by_basis` summing to `participating_section_count` — asserted as literals in
`test_narrowed_task_economics.py`, and the byte-golden tests in `test_live_clock_goldens.py`
are green.
*Review half, not automatable and stated as such*: the reviewer diffs each regenerated golden
against its predecessor and confirms the change is **key additions plus exactly one value
change — `allocation_method` `static_proportional_section_v1` → `static_proportional_section_v2`,
twice per file.** Any changed `allowance_seconds`, `left_seconds`, `share_state`,
`worked_seconds` or budget figure is a **gate failure, not a regeneration**.
*(Corrected at the projection fold, L3. "Key additions only" was **false by construction** and
this review half instructed the reviewer to fail the gate on the phase's own approved version
bump: measured, `golden_production_time.json` and `golden_budget_allocations.json` each carry
the constant as a **value**, twice — under `frozen_no_drift` and `idle_no_result`. §5 task 10
and master plan §7 gate 3 carry the same corrected enumerated form; the three now agree.)*
*Mutation for the automated half* — `division_serializers` (definition): default
`typical_basis` to `"section_wide"` instead of `"insufficient_sample"` when no evidence exists
→ the literals flip and the byte-goldens go red.
*Perimeter*: `golden_budget_status.json` is unchanged, byte for byte.

**C13 — one participating-set implementation, on the wire (T7 repaired).**
(a) `divide_production_budget`'s `allocated_groups` predicate and the services' participating
set resolve to `participating_sections`.
**Observable, added at the projection fold (L18)** — as written this was a structural claim
with no assertion: **monkeypatch `budget_division.participating_sections` to a disagreeing form
and assert that the division's section rows AND both services' rendered sets all move.** One
implementation is observable precisely as *"one patch moves all three"*; three copies are
observable as *"one patch moves one"*. `participating_sections` is defined at
`budget_division.py:212` and exported (`:418`), so the patch site is a module attribute.
(b) A section whose only step is `FAILED` renders `share_state: "excluded"` with
`allowance_seconds: null` and appears in **no** weight.
(c) **absence, L4, root = repository root, terms stated**: no private copy of the
excluded-state predicate remains. Search terms: `SKIPPED`, `CANCELLED`, `FAILED`,
`EXCLUDED_STEP_STATES`, `_step_state_is_excluded`. Expected: every hit outside
`budget_division.py` and the enum definitions is a **test** fixture, enumerated by name.
*Mutation* — `budget_division` (definition): reintroduce a private excluded set that omits
`FAILED`.
*Both sides* — contract: the FAILED-only section is `"excluded"` with a `null` allowance;
mutation: it becomes an allocated group, gains an allowance, and **every** other section's
allowance moves (`distributable_seconds` is unchanged but `total_weight` grows).
*Note*: §11.1's original T7 mutation ("reintroduce a private predicate in one service") was
inert — a faithful copy is what an implementer writes, and a faithful copy agrees. Naming the
**disagreeing form** is what makes it bite.

## 6B. Coordinator consumption fold — corrections to §6A (2026-08-23)

The projection ledger was consumed adversarially at source before this prompt was dispatched.
**Nineteen of its twenty rows were verified and are carried unchanged**; L14's four corrected
citations were re-derived independently and are all exactly right (`:271`, `:329`/`:331`,
`:344-350` with `/ total_weight` at `:348`, `:292`). What follows is what consumption **added
or corrected**. Provenance matters here: rows C-1 and C-2 are defects the projection's
instrument could not have found, and C-3 is a defect this fold introduced by transcribing.

**C-1 — blocking — the phase changes a documented contract that no test guards.**
`app/beyo_manager/routers/README.md` enumerates both changed endpoints field by field. It is
hand-maintained (*"No generator exists in this repository… A route added without editing this
file silently rots it"*), and `git log` shows the neighbouring pipeline's phases edited it as
implementation work. It appeared in neither §2 nor §4. **Why the projection missed it:** its
instrument was a test run, and the living-docs guard roots at `docs/domains/item_economics/`,
so probe P1 was green on this file *by construction*. **A green suite is evidence about the
suite's reach, never about a surface the suite does not read.** Routed: §4 *Modified —
documentation*, task 9c.

**C-2 — blocking — an inherited tripwire forbids exactly what C4's mutation instructed.**
`test_production_time_contract.py::test_c19_…` asserts `"Fraction" not in source` for both
services. C4 named `get_task_production_time` **(call site)** as a site for
`terminal=Fraction(0, 1)`. **Measured:** clean tree 17 passed; token added, **1 failed / 16
passed** at line 17. Probe reverted, `md5` identical, `app/` clean. **Why the projection missed
it:** the whole directory `tests/unit/services/queries/item_economics/` lay outside all four
path groups its probe ran. Routed: §2 read-first tripwire, C4's mutation site struck.
*Standing rule earned:* **a probe's path set is a claim about coverage, and an unmeasured
directory is not a green one.**

**C-3 — should-fix — this fold transcribed the projection's citations without re-deriving
them.** L9's supporting spans were wrong (`:45` / `:271` / `:331`×2 / `:334`); the field is at
`budget_division.py:42` and the five reads at `:133`, `:234`, `:273`, `:321`, `:391`. The
finding's substance stands. **This is the sharpest lesson of the round: the fold that carried
L14 — the row whose entire subject is that line numbers decay — copied a neighbouring row's
line numbers unchecked.** A citation is not more reliable for having arrived inside a finding
about unreliable citations. Corrected in place.

**C-4 — note — the fold over-delivered on L3, correctly.** L3 named only C12's blanket "key
additions only" phrasing. §5 task 10 carried the same sentence, and the fold fixed **both**.
Recorded because a fold that goes beyond its ledger is the good direction and should be
visible as a pattern, not silent.

**C-5 — note — `test_production_time_query.py` is in the perimeter for a second, independent
reason.** Beyond L1's key-set and v1-literal assertions, it **imports `DivisionStep`** (`:11`),
so task 4's field removal reaches it directly. Two independent reasons to edit one file is
worth stating, so a reviewer who closes the first does not conclude the file is done.

**Seal scored at this fold** (coordinator-private, outside the repo). Verdict and row count
inside band; blocking count **over-predicted** (predicted 8–16, ledger delivered 6) — though
consumption then added the two above, landing the phase at 8. **Both unhinted Layer-0
predictions failed, and failed identically:** the `fake_status` surface was measured at one
site and generalized (three predicted, **four** actual), and `division_serializers.py:56`'s
defaulted read was called invisible to C2's mutation without tracing who supplies the row —
`get_task_budget_allocations.py:255` supplies the constant itself, so the mutation reaches
both faces. *Standing rule earned:* **a measurement at one site is not a measurement of the
surface; a claim about a surface owes a sweep of it.**

## 7. Notes

- **F-F is stale, and stale in the direction that costs a round.** Its conclusion survives
  (`DivisionStep.typical_worker_seconds` is always `None` in production) but its stated reason
  is wrong: production now hands `DivisionStep` dataclasses that **do** carry the attribute,
  explicitly set to `None`. Hence two production files in the removal perimeter.
- **F-C is stale on the word "identical".** The three step loads still agree exactly on their
  WHERE predicates — which is what §6.1 rests on — but `production_time.py:30-41` adds
  `selectinload(TaskStep.latest_state_record)` and an `order_by` the other two lack. §6.1's
  shared function takes `steps` and is unaffected.
- **S-6:** production-time's section typical and budget-allocations' step rows are **not**
  pass-throughs — `division_serializers.py:102-108` and `:36-47` enumerate their keys
  explicitly with `typical.get("sample_count", 0)`-style defaults. New fields must be added
  **by name**, or they will silently not ship.
- **F-E:** excluded sections' typicals are display-only — they appear in zero computations.
  Weights iterate `allocated_groups` only.
- **No pace factor, no scaled values, no raw mixed ratios** (D12): every emitted
  `typical_worker_seconds` is identically an integer produced by the SQL, never a product or
  ratio of two of them. Plan 1 C9 pins this at the domain layer; this phase must not
  reintroduce it in a serializer.
- The unused narrowed **seconds** value is never published on task surfaces (§3.6) — only its
  **count** (`narrowed_sample_count`) is, and only on production-time.
- **Architecture-graph delta expected**: `projection-item-economics-task-production-time`,
  `projection-item-economics-task-budget-allocations` and
  `source-file-item-economics-budget-division`. One batched `apply_changes`; evidence
  summaries carry **no counts**; and — **corrected at the projection fold (L17), because this
  paraphrase was weaker than the policy it paraphrases** — the master plan §8 interim owner
  policy is binding and absolute: ***do not emit `startLine`/`endLine`.*** Name the file whose
  meaning the node describes and explain what that substance means for the application and
  what it affects. (The earlier wording here, "prefer symbol anchors over line spans, but not
  both on one entry", reads as permitting a span. It does not. Read §8, not this line.)
- **Expected transient reds, recorded so a reviewer does not read a regression into them**
  (projection L1 / refutation 2): between the payload edit and the golden regeneration,
  `test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files` and
  `test_budget_status_filter_spec.py::test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical`
  are **red, and green after regeneration** — neither needs a test edit, because both re-read
  the golden file from disk. **The second is a phase-3 row**, and its red is this phase's
  regeneration, not a phase-3 regression.

## 8. Review log

*(append-only; shared by implementer and reviewer)*

### 2026-08-23 — projection round 0 consumed and folded (coordinator)

**Handoff:** `handoffs/reviewer/20260823_plan4_projection_handoff.md` — Opus 5, projection r0,
verdict `AMENDMENTS_REQUIRED`, **6 blocking / 10 should-fix / 4 notes / 0 owner cards**, tree
`c560779` with `app/` clean.

**All 20 ledger rows routed; none deferred, none waived.** Homes:

| row | severity | folded into |
|---|---|---|
| L1 | blocking | §4 (two test files added) · **§5 task 9a** (five named assertions) · §7 (transient golden reds) |
| L2 | blocking | §4 (`test_domain_purity.py`) |
| L3 | blocking | §6 C12 review half · §5 task 10 · master plan §7 gate 3 |
| L4 | blocking | §6 C9(a) · §4 *New* (snapshot) · §5 task 0 |
| L5 | blocking | **§5 task 0** (tests-first, the C9(a) capture, N2 recorded inert, N1 restated) |
| L6 | blocking | §6 C10 mutation (ii) + row (c) subject **+ a coordinator amendment one layer down** |
| L7 | should-fix | §6 C10 instrument for rows (a)/(b); fixture caution restated |
| L8 | should-fix | §6 C1 fixture — three preconditions |
| L9 | should-fix | §6 C1(c) — rescoped L4→L2 with real roots |
| L10 | should-fix | §6 C2(c) — root and term stated |
| L11 | should-fix | §6 C7 mutation (ii) |
| L12 | should-fix | §6 C5 mutation (i) observable |
| L13 | should-fix | §6 C8 mutation replaced + fixture precondition |
| L14 | should-fix | §5 tasks 2/4 · §6 C4 · §6 C8 — four spans |
| L15 | should-fix | §2 bullet **withdrawn**; obligation moved to `plans/plan_5.md` §2 |
| L16 | should-fix | §5 task 4 — the fourth, larger edit surface |
| L17 | note | §2 Read-first (master plan §§5, 6.1, 8; `test_live_clock_goldens.py`) · §7 graph paragraph |
| L18 | note | §6 C13(a) — observable added |
| L19 | note | §6 C11 — quote corrected |
| L20 | note | §6 C0 — escape-1 cleanup named |

**Verified by variation before folding, not by reproduction** (charter, test-evidence reuse:
the projection's tree identity matches this one, so its two evidence rows are consumed by
citation). Independently re-derived by locating symbols rather than reading the projection's
ranges: all four drifted `budget_division.py` spans — **including one correction to the
projection's own correction: the step-attribute fallback read spans `:330-333`, not `:331`**;
the five task-9a assertion sites; `serialize_typical_time` as a distinct, out-of-scope
function; the four `fake_status` installs, found by a **repo-wide** `setattr` grep rather than
by the file the projection named; the v1 constant's three publish sites and its spread outside
`app/`; both goldens' twice-each `allocation_method` value; §4A K2's `spec_index ∈ [0, K)`
contract; C0's three escapes and the 10-module / no-subpackage package shape;
`typical_times_statement`'s import into the service module (`:37`) and its **eleven**
`session.execute` siblings (the projection wrote "12+" — recorded as measured);
`participating_sections` at `:212`; C7(b)'s reachability at `typical_filters.py:314` →
`:201-206`; `get_task_production_time.py:99-106`.

**One coordinator finding beyond the ledger**, folded into C10. L6 corrects mutation (ii)'s
**site** but not the fixture's **arithmetic**. C10's fixture line counts *tasks* (20/15/10/5)
while row (c) asserts a *`sample_count`*, which counts completed section groups in the 90-day
window — a quantity the fixture never states. Under the corrected mutation the chair task
reads the table population, which reddens row (c) **only if the two populations differ**.
Master plan §9's *"a fold that corrects a defect one layer down inherits the obligation to
check the layer below it"*, firing on the projection's own correction.

**Perimeter check — clean.** The projection declared its write perimeter as this handoff file
alone, and reported `?? .archgraph/backfill/` as *not its own*. Confirmed and closed: that
directory is the **owner's**, generated 2026-08-23 12:04–12:05 by
`ArchitectureGraph/scripts/backfill-evidence-spans.py` (its `summary.json` names the workspace,
its README names the script), part of the D29 span-removal policy work — **not an undeclared
write by any pipeline session**. `git diff --stat -- app/` empty at the projection's exit, as
declared.

**Evidence budget honoured: 0 L4 runs, correctly.** A projection is pre-implementation, and
C1(c)'s and C13(c)'s absence claims belong to the implementing round. Probe P1 ran at L2 with
both touched files' checksums asserted restored. No over-evidence, no unauthorized run.

**What the projection did NOT close, and the implementer therefore owns:** every criterion's
transcription (task 0), every named mutation's execution, and the fixture arithmetic C10 and
C5(a) now demand. A projection proves the plan is buildable; it proves nothing about the build.

### 2026-08-23 — coordinator consumption of the projection (second pass, §6B)

The ledger above was re-consumed at source before dispatch. **Nineteen of twenty rows verified
and carried unchanged**; L14's four corrected citations re-derived independently and all
correct. Added or corrected — full detail in **§6B**:

| row | severity | folded into | why the layer above missed it |
|---|---|---|---|
| C-1 | **blocking** | §4 *Modified — documentation* · §5 task 9c | the surface has no test, so a test-based probe was green on it by construction |
| C-2 | **blocking** | §2 tripwire · §6 C4 mutation site struck | the guard's directory was outside all four of the probe's path groups |
| C-3 | should-fix | §6A L9's citations, corrected in place | this fold transcribed them from the ledger without re-deriving |
| C-4 | note | — (recorded) | none: the fold correctly went **beyond** L3's stated scope |
| C-5 | note | §4 rationale | a second independent reason to edit an already-listed file |

**Measurements taken this pass:** `tests/unit/services/queries/item_economics/` baselined at
**17 passed** on the clean tree; with `Fraction` present in `get_task_production_time.py`,
**1 failed / 16 passed**. Probe reverted, `md5` identical, `git diff -- app/` empty. Repo-wide
sweeps: `divide_production_budget` referenced in 8 files (2 of them string-scans, not callers);
`DivisionStep` in 5; `ALLOCATION_METHOD` publish sites exactly 3, all reached by C2's mutation.

**Provenance note, recorded deliberately.** §6A and this section were written by two different
coordinator sessions against the same handoff. The second found two blocking defects the first
did not, and one defect *in* the first. That is the case for consuming a fold as an artifact
rather than trusting it — the same rule this project already applies to implementer handoffs,
now shown to apply to the coordinator's own output.

### 2026-08-23 — implementation round (Codex)

Implementation reached `IMPLEMENTED`. The declared perimeter was edited; focused,
domain, service, documentation, and mutation evidence are recorded in
`handoffs/implementer/20260823_plan4_implementation_handoff.md`. The approval-gate
L4 result and checkpoint commit are recorded there for the reviewer.

### 2026-08-23 — coordinator consumption of implementation round 1 → `CHANGES_REQUESTED`

**Handoff:** `handoffs/implementer/20260823_plan4_implementation_handoff.md`, checkpoint
`0efbbd4`. **Perimeter is exact** — 14 files declared, 14 modified, no undeclared write,
`.archgraph/` correctly unstaged. **The production engineering is sound and is not the
problem**: both consumers derive a spec, call the statement once, reconcile through
`uniform_basis_v1`, and feed the same `SelectedTypical`s to display and weights.
**The round is owed for evidence**, and one row is the shape this project has paid for most.

**B1 — blocking — C9(a) cannot fail, and I measured it.** The plan's §4 entry for the
snapshot is explicit: *"Written once, before any production edit, and **never regenerated** —
re-capturing from a refactored tree restores exactly the `f(x) == f(x)` vacuity §11A repaired
T11 to remove."* The shipped test does the opposite, at
`test_narrowed_task_economics.py`:

```python
if not SNAPSHOT.exists():
    SNAPSHOT.write_text(json.dumps(current, sort_keys=True, indent=2) + "\n")
expected = json.loads(SNAPSHOT.read_text())
```

**Measured:** removed the snapshot → **8 passed**, no failure; the test **re-created the file
from post-refactor output**, and the regenerated file **contains `typical_resolution`** — a key
that does not exist pre-refactor, proving the capture was post-refactor. Original restored,
`md5` `96f91c9c…` identical, `git status -- app/` clean.
Compounding, and the handoff says so itself: *"its numeric values were reconciled manually to
the task-0 pre-refactor payload rather than regenerated."* So the committed baseline is a
**hand-edited** artifact guarded by a **self-healing** read. The criterion the projection spent
a blocking finding (L4) to create is currently the one criterion that cannot fail.
**Correction:** the test **reads** the snapshot and **fails if it is absent**
(`assert SNAPSHOT.exists()`), never writes it. Re-capture it honestly: check out the
pre-refactor tree for the fixture, produce both payloads, commit the file, and record in §8
the commit it was captured from.

**B2 — blocking — three criteria have no committed test.** Task 0 required every row of
C0–C13 transcribed. `test_narrowed_task_economics.py` holds **8** tests covering C1, C3, C4,
C5, C6, C7, C9, C12, C13. Missing entirely:
- **C8** (the no-budget branch reconciles, F-D) — `no_budget` appears **0×** in the file.
- **C10** (batch dedupe, `K == 3`, the 50-task fixture) — the handoff defers it: *"not
  represented as a separate committed fixture in this round… a reviewer follow-up."*
- **C11** (production-time and budget-allocations agree per section) — the row that also
  discharges **charter rule 10**, operational reachability under shipped defaults.
Net suite growth is **+10** tests (2674 → 2684) for the largest phase in the project.

**B3 — blocking — the mutation ledger is short of the mutation count.** The plan names **21**
mutations; the ledger has **16** rows. Absent: C0's two standing regression probes, C9(ii),
and **C10(i) and C10(ii)** — the latter two declared *"verified by source inspection"*.
Master plan §9: **a never-run mutation is not evidence of anything, including of what it would
catch.** C10(ii) is also the mutation the projection spent blocking finding **L6** repairing,
so it has now been corrected twice and executed zero times.

**B4 — blocking — task 0's red baseline was never recorded.** Task 0 required the failing ids
and count in §8 before any production edit. The §8 entry records none and the handoff records
none. That record is the only evidence that tests-first happened at all; without it, B2's three
missing criteria are indistinguishable from three criteria that were never transcribed.

**S1 — should-fix — the baseline was compared by count, not by id.** The handoff reports
`2684 passed / 21 failed / 1 skipped` and *"the 21 failures are the inherited baseline set…
no phase-focused test is in that failure list"*. Master plan §10 is explicit that the
comparator is **the 21-ID set, not the count**; "no phase test among them" is a weaker claim
that a coincidental swap would satisfy. The re-review's L4 discharges this with a programmatic
id diff.

**S2 — should-fix — C2's budget-allocations half rests on the golden alone.** The exact-literal
v2 assertion exists for production-time (`test_production_time_query.py:206`). C2 requires it
*"on production-time's task block **and on every budget-allocations task entry**"*.

**Verified correct — do not re-verify.**
1. **Perimeter exact**: declared 14, modified 14, `.archgraph/` unstaged as instructed.
2. **Task 9c was done** — `routers/README.md` +24 lines. It could not fail the suite and it
   was done anyway; recorded because the coordinator's seal predicted it would be skipped.
3. **C12's review half passes, diffed programmatically**: `golden_production_time.json`
   +8 keys, `golden_budget_allocations.json` +6 keys, and **exactly 4 value changes across
   both files, every one of them `allocation_method` v1 → v2.** No `allowance_seconds`,
   `left_seconds`, `share_state`, `worked_seconds` or budget figure moved. **The refactor did
   not move a number** — the safety property this whole phase exists to preserve.
4. **C2's absence half holds**: `static_proportional_section_v1` has zero occurrences in
   `app/beyo_manager/`.
5. **The C19 tripwire survived**: `tests/unit/services/queries/item_economics/` **17 passed**,
   and `Fraction` appears **0×** in both services. The consumption fold's C-2 was acted on.
6. **Graph evidence is policy-correct**: three new source links, `path` + `symbol` +
   `contentHash`, **zero spans**.
