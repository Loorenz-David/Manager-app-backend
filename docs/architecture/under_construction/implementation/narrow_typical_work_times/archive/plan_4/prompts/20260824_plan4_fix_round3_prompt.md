---
plan: plan_4
role: implementer
round: 3
date: 2026-08-24
---

# Fix round 3 — phase 4, `narrow_typical_work_times`

Review round 1 (Opus 5) returned `CHANGES_REQUESTED`: **2 blocking / 5 should-fix / 11 notes /
0 owner cards**.

**The production engineering is not in question and is not to be relitigated.** Two independent
sessions have now attacked it. The `spec_index is None` fix survives all three attacks, the
weight-ladder delegation is term-for-term the code it replaced, and **the refactor moved no
number** — proven by a leaf-set diff of both goldens: 0 leaves removed, 0 pre-existing numeric
leaves changed, exactly 4 value changes, all `allocation_method`. **This round is coverage.**

**Workspace:** `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
**Test working directory:** `backend/app/`

**Doctrine, by absolute path, first:**
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`
- `/Users/davidloorenz/agent-skills/implementation-executor.md`

**`plans/plan_4.md` is your task list. Where this prompt differs from it, the plan file wins.**

## Gate check — stop and report if any fails

1. `git merge-base --is-ancestor 9693a26 HEAD` succeeds (correction 2's checkpoint is an
   ancestor). **Do not pin `HEAD`** — doc commits land on top while you work.
2. `plans/plan_4.md` header reads **`state: CHANGES_REQUESTED`**, and `master_plan.md` §4 row 4
   agrees.
3. `plans/plan_4.md` §8 ends with the entry **"2026-08-24 — review round 1 consumed → fix round
   3 (coordinator)"**. If it is absent you have an unfolded plan.
4. `git status --porcelain -- app/` is **empty**. Anything under `.archgraph/` is the owner's live
   work, **expected whatever it contains** — never enumerate, diff, or halt on it.

`redis-cli ping` → `PONG` before any suite run.

## Task 0 — the completeness pass, and it comes first

The review's own process note is why this is task 0 rather than a closing check:

> *"Both blocking findings are criteria with no committed test — the same class as round 1's B2.
> B2's list was assembled by reading the new test file and asking 'which criteria are missing?',
> which finds criteria with **no** test but not criteria whose test asserts something **weaker**,
> and not **absence rows** with no test file to be missing from."*

**Walk `plans/plan_4.md` §6 criterion by criterion and row letter by row letter — C0 through C13,
absence rows included — and produce a table with one line per row letter:** the row, the test id
that discharges it, and whether the assertion is the **shape the row specifies** or something
weaker. Put it in your handoff. **Any row whose cell you cannot fill is a finding you have just
found; report it rather than inventing coverage.**

Do this before writing code. It is the instrument that would have caught all five of this
round's findings before dispatch.

## Blocking

### B1 — C5's three rows need real fixtures

C5 carries §3B's layer-2 visibility contract on the division wire, and none of its three rows is
implemented as specified. **Measured by the reviewer: republishing a zero section-wide median at
count ≥ floor as `insufficient_sample` leaves 346 passed at C5's own declared L2 scope.** A
corroborating sweep found **no** `SectionTypicalEvidence(` construction anywhere in `tests/`
carrying a zero section value at count ≥ floor.

Write all three on a **real session**:
- **row (a)** — a participating section whose section-wide count is strictly between 1 and
  `TYPICAL_MIN_SAMPLE_SIZE`. Assert the wire triple with `sample_count` as an **exact literal
  equal to that count** — *not* `0`. Today the nearest thing is `test_c3_…:60-67`, which covers
  the **missing-key** shape whose count is `0`: a different branch, and `0` is precisely the
  value §3B B3 exists to distinguish.
- **row (b)** — a section with ≥ `TYPICAL_MIN_SAMPLE_SIZE` completed section totals **all summing
  to 0**. Assert `(0, "section_wide", <n>)` as exact literals on **both** the step row and the
  section row, with the allowance present. §4C exists solely to say this is the *reachable* zero
  form; a clause naming a reachable shape is naming a fixture somebody must build.
- **row (c)** — on **row (a)'s task**, `sections_by_basis["insufficient_sample"] >= 1`.

Then run C5's mutations (i) and (ii) against these rows and **record which assert each bit.**

The projection fold left an instruction on this row that was never satisfiable because the
fixture did not exist: *"pin C5(a)'s fixture — 'no participating section has a usable typical',
which makes the flip exactly `1` — or write the resolved fallback into the row. Either is
acceptable; leaving it unstated is not."* Satisfy it now.

### B2 — C1(c) and C13(c) must ship as committed tests

Both criterion texts require it in so many words, and master plan §10 already budgets C13(c) as
an L1 committed test walking the repository. **Their substance is TRUE — the reviewer verified
both — so this is the form defect §9 names:** *"C4(c) and C17 were re-measured correct at review;
the defect was the form, so later phases inherited an unguarded claim."* Plan 5 inherits both.

- **C1(c)** — `typical_filters.py` and this phase's evidence-construction helper contain none of
  `live_seconds`, `load_live_worked_seconds`, `total_working_seconds`.
- **C13(c)** — **read §6 C13(c) as amended before writing this one.** Its expectation was false
  as written and has been corrected: `get_task_price_scenario.py:14`/`:134` are production hits
  and are a legitimate **import of the shared predicate**, not a private copy. Pin the exceptions
  **by name**, those two lines included, so removing an exception cannot silently widen the claim.

**Each test asserts non-emptiness of its own walk as a contract before asserting the term set** —
that is the C0 escape-3 lesson, and this phase has now produced three generations of that shape.

## Should-fix

- **S1 — the `_step_result` tolerance branch** (`budget_division.py:270-278`). Unreachable
  production code (`elif selected is not None:` makes its own `else` arm dead) publishing the
  triple `(value, "section_wide", 0)`, which is **impossible** under the contract — `section_wide`
  is count-gated and §3B B3 requires `sample_count` to *be* that count. Nothing asserts it:
  mutating it to `("item_narrowed", 99)` leaves **494 passed**. It exists to avoid converting the
  23 int-valued third-argument literals in `test_budget_division.py` — the surface §5 task 4
  named explicitly — and the divergence is **undeclared** (charter rule 14; the code comment is
  the only record). **Convert the 23 literals** (the pattern is the phase file's own `selected()`
  helper at `test_narrowed_task_economics.py:51-53`) **and delete the branch**, so the
  `Mapping[str, SelectedTypical]` annotation becomes load-bearing. Take **N4** with it: `step()`'s
  now-unused `typical=None` parameter (`test_budget_division.py:13`) and its callers.
  If you keep the branch deliberately, it needs a criterion row **and** a declared divergence
  sentence — say so and stop rather than deciding it silently.
- **S2 — `test_item_economics_domain_walk_is_recursive` is `f(x) == f(x)`**
  (`test_domain_purity.py:31`): its right-hand side re-implements `_domain_modules`. Reverting
  `rglob` → `glob` **alone** leaves 4 passed — green under the escape it is named for. Have the
  test build a subpackage under `tmp_path`, point `PACKAGE_ROOT` at it (the sibling test shows the
  idiom) and assert the walk **finds the nested module**: a positive claim about a fixture the
  test controls.
- **S3 — C2's production-time literal.** One line: `assert e3["allocation_method"] ==
  "static_proportional_section_v2"`. Both existing v2 assertions read `e2`/`e2_row`, which are
  **budget-allocations**. Then re-run C2's mutation and record **both** failing ids. *(The
  coordinator's round-1 closure row misread this variable; §6 C2 now names the surface.)*
- **S4 — the ledger owes two rows, and the count is 23.** The reviewer ran both missing mutations
  and both bite, so **no re-run is owed** — transcribe its observed results: **C8** at `:198`
  (`assert 'section_wide_uniform' == 'item_narrowed_uniform'`) and **C11** at `:290`
  (`(540, 'section_wide', 7) != (540, 'item_narrowed', 7)` on both sections, with a collateral
  C10 bite `assert [27] == [7]`). **The count is 23**, summing per criterion as
  C0=5, C1=2, C2=1, C3=1, C4=1, C5=2, C6=1, C7=2, C8=1, C9=2, C10=2, C11=1, C12=1, C13=1.
  Your final ledger is those 23 plus the anti-regression row = **24**, plus whatever B1 adds.
- **S5 — C1(a)/(b) are `f(a) == f(b)`** with no exact literals and no non-emptiness guard, on the
  **Critical rank 5** row. The criterion says *"asserted as exact literals per section"*. Assert
  `allowance_seconds` per section as exact literals on both `ctx.now` calls and both surfaces, and
  add the non-emptiness assertion. **Record the siting that makes (i)/(ii) bite** — the *accruing
  open* step, not merely "one section's typical"; the reviewer's first attempt at this probe went
  green because it landed on the settled `tsp_failed` step.

## Notes to close in this round

**N1** — "§6A" is cited four times (§6B's title, §8's C-3 row, §8's provenance note) but no `## 6A`
section exists; plan 4 folded its amendments in place. Add a pointer stub or rewrite the citations
as "§6 as amended at the projection fold".
**N2** — record the living-docs guard result in §8. Measured on this tree: `pytest tests/unit/docs
-q` → **59 passed**, matching master plan §10.
**N3** — `division_serializers.py:110-111` hardcodes `"uniform_basis_v1"` and
`"primary_item_category_v1"` where it should read `RECONCILIATION_METHOD` /
`COMPARABILITY_PROFILE`. A future bump would leave this branch publishing the old value on every
no-selection payload, both goldens included. Tests may keep the literal (rule 13); **production
reads the constant.**
**N5** — C6 ships `{1,1,1}`/3 where the criterion specifies `{"item_narrowed": 0,
"section_wide": 2, "insufficient_sample": 1}`/3. Discriminating power is equivalent, so either
restore the specified distribution or record why it changed — and **assert the criterion's
`sum(sections_by_basis.values()) == participating_section_count` clause**, which is currently
true only by coincidence of 1+1+1.
**N6** — C10 `:242` (`len(captured_specs[0]) == 3`) is unreachable: `:238`'s exact 3-tuple
comparison subsumes it. Drop or re-purpose it. *(And for the record: C10(i) fails at `:238`, not
`:242` — the coordinator's note inferred those lines and got one wrong.)*
**N7** — dead conditionals in the `elif specs:` arm: `task_spec_index is not None` is always true
there, since the `None` case `continue`s above. Residue from before the fix; tidy it.
**N10** — C0 escape 2's fix drops the plan's prescribed `count(...) == 1` pin in favour of
`replace(..., 1)`. The direction is **safe and arguably stronger** (a reworded pinned line makes
the replace a no-op and the term survives, so it fails closed) — but it is an **undeclared**
divergence. Write the reasoning into your handoff.

**Not yours:** **N9** (graph delta node identity) is the **owner's** — do not act on it.
**N11** (uniform fixture multisets) is routed to **plan 5**.

## Perimeter

`plans/plan_4.md` §4 plus, for this round only:
- `app/tests/unit/domain/item_economics/test_budget_division.py` (S1's 23 literals, N4)
- `app/tests/unit/domain/item_economics/test_domain_purity.py` (S2)
- wherever B2's two committed absence tests belong — **declare the paths you choose.**

A write outside that set is an automatic finding. If you need one, **stop and report** — that
instruction has paid for itself twice in this phase.

## Evidence budget

**Exactly 1 L4 run** — the closing stamp on the tree you hand over, with the programmatic 21-ID
diff computed from it. Everything else at L1/L2. Note the serial comparator was **already spent**
by the review (`-n 0` → 21 failed / 2686 passed / 2 skipped, set ∅/∅); do not repeat it. Any
additional L4 needs the charter's authorization line written **before** the run.

## Closing protocol

1. Task 0's completeness table, in the handoff.
2. Every mutation run, both sides, **observed** ids and the assert each bit.
3. The single L4 stamp plus the id diff.
4. Append your round-3 entry to `plans/plan_4.md` §8; set the header **and** `master_plan.md` §4
   row 4 to **`IMPLEMENTED`** — both, they are two records of one state.
5. Checkpoint commit, **explicit paths**, never `git add -A`, never push.
6. No graph delta expected; if you record one, declare it.

## Report back

- The completeness table.
- What you changed per finding, and what you did **not** change and why.
- Your full write perimeter — it will be diffed.
- The ledger: 24+ rows, observed ids, assert lines.
- The L4 stamp and the id diff.
- For S1: whether you deleted the branch or kept it, and if kept, the declared divergence.
