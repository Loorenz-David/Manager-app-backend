---
plan: plan_4
role: implementer
round: 4
date: 2026-08-24
---

# Fix round 4 — phase 4, `narrow_typical_work_times`

The delta re-review returned `CHANGES_REQUESTED` with **0 blocking**. Both round-1 blocking
findings are closed, **B1 is closed and biting**, the production engineering is settled, and
**no production change is requested.** This is three test-file edits plus four notes.

**This is the round that closes the phase.** Its tree is the approval-gate tree, so its L4 is
the gate stamp — **run, not cited.**

**Workspace:** `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
**Test working directory:** `backend/app/`

**Doctrine first:** `/Users/davidloorenz/agent-skills/pipeline-charter.md`,
`/Users/davidloorenz/agent-skills/implementation-executor.md`.

**`plans/plan_4.md` is your task list. Where this prompt differs, the plan wins** — and §6 C5(c)
and C13(c) were **amended at the fold**, so read them there rather than from this summary.

## Gate check — stop and report if any fails

1. `git merge-base --is-ancestor 24af53a HEAD` succeeds. **Do not pin `HEAD`.**
2. `plans/plan_4.md` header reads **`state: CHANGES_REQUESTED`**; `master_plan.md` §4 row 4 agrees.
3. `plans/plan_4.md` §8 ends with **"2026-08-24 — delta re-review consumed → fix round 4
   (coordinator)"**.
4. `git status --porcelain -- app/` is **empty**. `.archgraph/` is the owner's — expected whatever
   it contains.

`redis-cli ping` → `PONG` before any run.

## Perimeter

Three test files, and nothing else:
- `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`
- `app/tests/unit/domain/item_economics/test_budget_division.py`
- `app/tests/unit/domain/item_economics/test_domain_purity.py`

Plus `plans/plan_4.md` §8 and the `master_plan.md` §4 row.

**No production file is in scope.** If a finding appears to need one, **stop and report** — that
instruction has paid for itself twice in this phase.

## S1 — C13(c) is blind to a faithful private copy

**Measured by the reviewer:** a faithful local copy of `_step_state_is_excluded` in
`get_task_price_scenario.py`, preserving the occurrence count at 2, leaves the guard **green**
(351 passed). Only a *disagreeing* copy is caught, and by behavioural tests elsewhere. C13's own
note says *"a faithful copy is what an implementer writes"* — **so the row currently misses the
only shape it exists to catch.** The proxy fails because a local `def` plus one call site is also
exactly 2 occurrences in an allowed file.

Three changes, all in `test_c13c_excluded_state_logic_has_one_shared_production_owner`:

1. **Make "documented import" mechanical:** for every hit except `budget_division.py`, assert
   `"def _step_state_is_excluded" not in path.read_text()`.
2. **Close the different-name hole** with the claim the reviewer measured available and I
   re-measured: **0** files under `app/beyo_manager/` contain a set/frozenset literal naming two
   or more of `SKIPPED` / `CANCELLED` / `FAILED`. Assert that absence.
3. **Declare the divergence** (charter rule 14) in your handoff: the shipped sweep uses **2**
   terms and the `app/beyo_manager/` root, where C13(c) as originally written named 5 terms and
   the repository root. **The narrowing is right** — the three state names appear across many
   production files, so a name-enumerated allowlist over them is a rule-13 time bomb — it simply
   has to be *stated*. §6 C13(c) is amended to say so; your handoff should say you followed it.

**Count at source.** I measure **38** files under `app/beyo_manager/` mentioning the three state
names; the re-review quoted 40. Neither number goes into an assertion — but if you write one,
derive it yourself. This phase has now had five wrong counts.

## S2 — the fixtures publish a triple production cannot reach

Round-1 S1 removed the impossible `(value, "section_wide", 0)` from `_step_result`. The
`SelectedTypical` conversion then hand-built it 23 times: `test_budget_division.py:14` is
`def selected(section, value, basis="section_wide", count=0)`, so every row that used to pass a
bare `None` now publishes `section_wide` with a null value, and every int row publishes
`section_wide` with `sample_count: 0` — unreachable, because the floor is
`TYPICAL_MIN_SAMPLE_SIZE = 5`. **That file contains 0 `typical_basis` assertions, so the drift is
invisible.** No criterion is weakened today; it is a fixture proving arithmetic through a state
the domain cannot produce, in the file §5 task 4 named, introduced by the round raised to delete
that very triple.

**Fix either way:** keep the bare `None` mapping value for the None-valued rows (the
`selected is None` branch handles it — the reviewer measured
`{"missing": None}` → `(None, 'insufficient_sample', 0)`), or pass
`basis="insufficient_sample"`; and give the helper a `count` consistent with its basis
(`>= TYPICAL_MIN_SAMPLE_SIZE` when the basis is `section_wide`), or derive the basis from the
value so an inconsistent pair cannot be written.

## S3 — C1(c)'s test still carries the root the plan struck

§6 C1(c)'s second root — *"this phase's evidence-construction helper"* — **never existed**, and
the plan now says so. The test still asserts over `inspect.getsource(selected)`, a **test-local**
helper, still has `assert roots` on a one-literal list, and is still named
`test_c1c_typicals_and_evidence_helper_do_not_import_live_clock_terms` — a name that promises a
guard over the evidence builder.

- Delete `helper_source` and its assertion.
- Replace `assert roots` with something that can fail — `assert all(path.exists() for path in roots)`.
- Rename to `test_c1c_typical_filters_does_not_import_live_clock_terms`.

**No new assertion is required.** The surviving half bites (1 failed / 222 passed at `:514`), and
the reviewer's span-scoped structural guard over the two services is routed to **plan 5** as a
note, not a plan-4 obligation.

## Notes to close

- **N1** — `test_c2c` builds `files` from `beyo_manager` **and** the goldens directory in one
  comprehension, so `assert files` is satisfied by the first root alone and a wrong goldens path
  would scan nothing while staying green. **Assert non-emptiness per root.** Fifth instance of
  this shape in this phase.
- **N2** — the recursive-walk mutation still does not reach its own sub-check: under
  `rglob`→`glob` the red is `assert modules` inside the helper (`test_domain_purity.py:13`),
  because `tmp_path` holds only the nested module. **Write one `.py` at the top of `tmp_path`
  too**, so `glob` leaves the helper green and `assert nested in modules` is the assertion that
  fires. Third generation of this shape; one line.
- **N4** — ledger rows 4/5, 9/10 and 25/26 name a mutation without its **site**. Rows 20–22 do it
  properly. Give every row file plus definition-vs-call-site.
- **N7** — the two converted dict entries in
  `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections` are
  over-indented.

## The ledger

Rebuild it from the plan, not from the previous handoff. **§6 names 23 mutations**, summing
C0=5, C1=2, C2=1, C3=1, C4=1, C5=2, C6=1, C7=2, C8=1, C9=2, C10=2, C11=1, C12=1, C13=1, plus the
C10(d) anti-regression = **24 minimum**, plus S1's new `def` mutation.

**Every retained row whose test file this round edits must be re-run** — all three perimeter
files carry ledger rows, so in practice: re-run rather than retain, and where you do retain, say
per row why the citation survives. This is the rule the C8/C11 case earned and the re-review then
applied to C1's and C6's rows unprompted.

## Evidence budget — this is the approval gate

**Exactly 1 L4 run, and it must be RUN on the tree you hand over, never cited.** Phase 3's
precedent is explicit; phase 2 lost the ability to stamp its own gate tree by deferring.

`BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'` — **verbatim**; extra flags invalidate the
stamp. Compare the failing set **by id** against the published 21-ID block, programmatically, and
report ∅/∅ or name the difference. Everything else at L1/L2.

## Closing protocol

1. Every mutation run, both sides, observed ids **and sites**.
2. The gate L4 stamp plus the programmatic id diff.
3. Append your round-4 entry to `plans/plan_4.md` §8; set the header **and** `master_plan.md` §4
   row 4 to **`IMPLEMENTED`** — both.
4. Checkpoint commit, **explicit paths**, never `git add -A`, never push.
5. No graph delta expected; if you record one, declare it.

## Report back

- What you changed per finding; what you did not, and why.
- Your full write perimeter — it will be diffed.
- The rebuilt ledger with sites.
- **The gate stamp and the id diff** — this is the number the phase closes on.
- Your declared rule-14 divergence for C13(c)'s terms and root.
