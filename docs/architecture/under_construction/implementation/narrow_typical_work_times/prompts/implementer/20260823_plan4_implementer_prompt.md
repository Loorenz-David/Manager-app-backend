---
plan: plan_4
role: implementer
round: 1
date: 2026-08-23
---

# Implement phase 4 — the division contract, production-time and budget-allocations

You are the implementing session for **phase 4** of `narrow_typical_work_times`.

**Workspace:** `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
**Test working directory:** `backend/app/`

**Doctrine — read both by absolute path before anything else, and follow them as this
session's doctrine:**
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`
- `/Users/davidloorenz/agent-skills/implementation-executor.md`

*(If you are a Claude session, invoking the `implementation-executor` skill loads the same
document.)*

**`plans/plan_4.md` is your task list. Where this prompt differs from it, the plan file wins.**

---

## 1. Gate check — verify before writing anything

All four must hold. If any disagrees, **stop and report**; do **not** edit the tracker or a
plan header to match this prompt — that converts a coordinator typo into a false project state.

1. `git merge-base --is-ancestor 353a8c9 HEAD` **succeeds** (phase 3's approval-gate commit is
   an ancestor). Do not check `HEAD`'s position — the fold commit for this prompt lands after
   the SHA above and any tip pin would already be stale.
2. `plans/plan_4.md` header reads **`state: PROMPT_READY`** and
   `projection_gate: MANDATORY — SATISFIED`.
3. `master_plan.md` §4 shows phases 1–3 **`APPROVED`** and phase 4 **`PROMPT_READY`**.
4. `plans/plan_4.md` §8 carries **both** 2026-08-23 entries — the projection fold **and** the
   coordinator consumption pass beneath it — and §6B exists. The twenty ledger rows plus five
   consumption rows are amendments already written into the plan you are about to read; if
   either entry is missing you have a partially folded plan, and that is a stop-and-report.

**Tree:** `git status --porcelain` should show only the owner's `.archgraph/` work
(` M .archgraph/agent-operating-policy.md`, `?? .archgraph/backfill/`, `?? .archgraph/contexts/`).
**No modified tracked file under `app/`.** If `app/` is dirty, stop and report.

**Redis must answer `PONG`** before any suite run (master plan §10 — without it this machine
measures 23 failed / 2 errors, not 21, and you will misread your own stamp).

---

## 2. Read order

1. `master_plan.md` §§4, **5**, **6.1**, 6.2, 6.4, 6.5, 6.7, 6.9, 7, **8**, 9, 10.
   §9 is long and it is the single highest-value read in this project: it is ~50 rules, each
   bought with a real defect, and **ten of them were added yesterday by this phase's own
   projection.**
2. `plans/plan_4.md` **in full, including §8's projection-fold entry.** The plan carries
   roughly twenty inline `*(… at the projection fold, L<n>)*` notes. Each one marks a place
   where the plan as originally written was **wrong or unexecutable**, with the measurement
   that shows it. They are not commentary — several name the exact edit you must make.
3. The intention sections and the neighbouring-pipeline authority listed in `plan_4.md` §2.
4. `plans/plan_3.md` §6B and the two notes routed into §2 (N1, N2).
5. Code, whole files: `budget_division.py`, `division_serializers.py`,
   `get_task_production_time.py`, `get_task_budget_allocations.py`, `test_budget_division.py`,
   and `test_live_clock_goldens.py`'s `_seed_golden_fixture` / `_payloads`.

---

## 3. This phase, in one paragraph

The engine turns on. Both division consumers derive a filter spec, call the typicals statement
with it, build `SectionTypicalEvidence`, reconcile through `uniform_basis_v1`, and feed **the
same `SelectedTypical`s** to display and to weights. `divide_production_budget`'s third
parameter becomes `Mapping[str, SelectedTypical]`, `DivisionStep.typical_worker_seconds` and
both fallback reads go, `ALLOCATION_METHOD` becomes v2, §7.2/§7.3's keys ship, and two goldens
regenerate. Phases 1–3 built every part you need; **none of them is load-bearing until this
phase wires it up.**

---

## 4. Not optional — inherited hazards

These are not advice. Each was measured, in this project, at a cost.

- **Task 0 comes first, and it is two things.** Transcribe every row of §6 C0–C13 — **and every
  criterion's prose clauses, not only its row tables** — into executable cases before editing a
  line of production code, and record the red baseline (failing ids **and** count) in §8.
  **Then capture C9(a)'s pre-refactor snapshot**, before the first production edit. After task 1
  that baseline is `f(x) == f(x)` and the criterion is dead.
  A row you cannot transcribe is a **plan defect — stop and report**, never a row to invent.
- **Transcribing a row and *arming* it are different acts.** Tests-first closed the missing-row
  class in phase 2; what survived was fixtures too uniform to discriminate and mutations named
  but never run. Two rows in this plan now state their fixture arithmetic explicitly (C10's
  three category populations must differ; C5(a)'s fixture decides whether the mutant value is
  `1` or a median). **Seed the numbers that make the mutation move, and write them into the
  assertion as exact literals.**
- **Every named mutation runs before you submit, at hypothesis scope, and the ledger records
  which test id failed** — not which test you expected to fail. The ledger's **row count must
  match the plan's mutation count, not its criterion count**; this plan names more than one
  mutation for C0, C1, C5, C7, C9, C10 and C13.
- **After applying a mutation, assert it landed inside the symbol you meant.** A probe that
  lands in the wrong function returns a clean-looking green that reads as "the finding is
  wrong" and is in fact "the mutation was never applied". This project has paid for that twice.
- **C0's escape-1 mutation creates `…/domain/item_economics/sub/leak.py`.** Delete it **and its
  parent directory**, and declare it in your mutation-probe declaration — a leftover sits inside
  your own diff and is indistinguishable from intended work.
- **Never assign to `TaskStep.total_working_seconds`** (HC-1A, charter rule 3). After this phase
  both consumers hand `divide_production_budget` steps whose `total_working_seconds` **is** the
  live figure, alongside typicals that must **not** be. **They live in the same call.** The
  neighbouring pipeline calls a "make it consistent" change here *the most expensive mistake
  available in this feature*, and records that no guard existed anywhere in the repository until
  its own phase 2 round 6. **C1 is that guard. It is critical rank 5. Do not weaken it.**
- **Read the K ≥ 1 statement result by column name, never by position** (§4A K2-a). The shipped
  column order is the reverse of the contract prose, and the domain object's field order is a
  third order again. A positional read publishes a section-wide median as `item_narrowed`.
- **Line numbers in the plan are checksums, not targets.** Four were corrected yesterday and one
  of those corrections needed a further correction. Locate the symbol in the file at the moment
  you edit it; a disagreement means the tree moved and is a stop-and-report.
- **`Fraction` must not appear in either service's source — and C4's mutation goes at the
  definition.** `tests/unit/services/queries/item_economics/test_production_time_contract.py::test_c19_…`
  is a **substring check** over `get_task_production_time.py` and `get_task_budget_allocations.py`
  for the tokens `Fraction`, `ROUND_HALF_EVEN`, `largest` and `//`. An *import* trips it.
  **Measured: clean tree 17 passed; with `from fractions import Fraction` in the production-time
  service, 1 failed / 16 passed.** C4's mutation once named that service as a site; **it is
  struck** — apply the mutation in `budget_division.py` only. Treat C19 as a signal: reaching
  for `Fraction` in a service means the arithmetic has leaked out of the domain layer.
  **That whole directory (17 tests) was outside every path set the projection ran.** Run it.
- **Task 9c updates a contract that cannot fail your suite.** `beyo_manager/routers/README.md`
  is hand-maintained, documents both changed endpoints field by field, and **no test reads it**.
  Nothing will go red if you skip it and nothing will go green when you do it. It is in §4 and
  in your write perimeter. Derive its new rows from the serializers you actually wrote.

## 5. Scope fences

- **No price-scenario.** It never calls division. Its clock, its private ladder and
  `is_estimated` are **phase 5**. In particular: **do not touch `test_price_scenario_query.py`**
  — plan 4 §2 carries a withdrawn instruction telling you to widen a fake there. It was
  measured wrong and re-homed to plan 5. Editing that file is an automatic perimeter finding.
- **`/working-sections/typical-times` stays byte-identical** (D24), and so does
  `serialize_typical_time` and `test_budget_division_routes.py:151`'s key set for it.
- **`golden_budget_status.json` is unchanged, byte for byte.**
- **No statement change** (phase 2 shipped it), **no new domain object** (phase 1 shipped them),
  **no `/statistics/typical-times` route.**
- **Do not push.** The branch is deliberately far ahead of `origin/main`.
- **Architecture graph: do not emit `startLine`/`endLine`** (master plan §8, binding interim
  owner policy). Name the file whose meaning the node describes; explain what the substance
  means and what it affects. One batched `apply_changes` at the end. Never promote, reject or
  edit a review item.

## 6. Evidence budget

**This session's L4 budget is exactly one run** — the closing stamp, mandatory, taken on the
tree you actually hand over. If you change anything after taking it, **re-take it**; the stamp
is defined by the tree, not by the count, and a re-take is not over-budget. Citing a stamp whose
tree you then changed is a finding.

Everything else runs at L1/L2:
- **L1** = `test_narrowed_task_economics.py` / `test_budget_division.py` — the default for every
  named mutation. An L1 miss is already a finding; no wider run is needed to detect it.
- **L2** = `tests/integration/services/queries/item_economics/` +
  `tests/unit/domain/item_economics/` — for C5, C7, C11, C12, whose criteria name cross-file
  bite sets, and for C1(c)'s and C2(c)'s absence sweeps.
- **C13(c)'s repository-root sweep is a committed test, not a suite run.** It does not consume
  the stamp.
- Re-running evidence whose tree identity matches yours, with no variation and no pre-run
  authorization line, is a finding of the same severity as an unrun mutation.

**Expected transient reds, so you do not chase them:** between the payload edit and the golden
regeneration, `test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files` and
`test_budget_status_filter_spec.py::test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical`
are red and go green on regeneration. Neither needs a test edit. **The second is a phase-3
row** — it is not a phase-3 regression.

**Comparator:** the 21-ID failing baseline (master plan §10; enumerated in the frontend handoff
it cites). **A single run is not evidence** — the set can shrink as well as grow, and it moves
when the test population changes. You are adding a test file, so **diff the IDs, do not count
them**, and diagnose any delta rather than reporting it.

## 7. The perimeter

Exactly the files in `plans/plan_4.md` §4 — **eleven modified** (four production, one
hand-maintained doc, six tests/goldens) **and three new**, fourteen in all. Count them in §4
yourself before you start; if your count disagrees with this sentence, §4 wins and the
disagreement is worth a line in your report. *(Both prior drafts of this sentence miscounted —
"nine", then "ten". §9's rule about counts in plan sentences was earned three times in this
project and just fired a fourth. Counting is cheap; trusting a count is not.)*

**§4 was measured twice, not assumed.** A projection probe applied this phase's own payload
additions and reddened four tests, two of them in files the plan originally never named — those
two are now listed, and **task 9a** names the five assertions to widen (**widen, never delete**;
they are the only exact key-set guards on that wire). A second consumption pass then added
`beyo_manager/routers/README.md` (**task 9c**), which the first probe could not see because no
test reads it.

**The lesson is aimed at you, not at the plan:** two passes over the same phase each found a
file the previous one missed, both times a file whose omission produced *no red*. When you
finish, the question that catches the third one is **"what did I change that nothing tested?"**

A write outside §4 is an automatic finding at review. If you find you need one, **stop and
report** rather than taking it.

## 8. Closing protocol

1. **Tests green**, then the L4 stamp on the handover tree.
2. **Every named mutation run**, ledger row per mutation (not per criterion), each naming the
   **observed** failing test id — and say so where an id is inferred rather than observed.
3. **Update state in BOTH places**: `master_plan.md` §4 row 4, and `plans/plan_4.md`'s `state:`
   header **and** §8 Review log. This project has already lost a session start to a fix round
   that updated one and not the other.
4. **Checkpoint commit the moment you reach `IMPLEMENTED`** — subject prefixed
   `CHECKPOINT (not approved):`, **explicit paths only, never `git add -A`**, under the owner's
   standing authorization. Do not stop to ask.
5. **Architecture-graph delta**: one batched `apply_changes` — the two projections and
   `source-file-item-economics-budget-division`. Evidence summaries carry **no counts** and
   **no line spans**.
6. **Run the docs guard** (`PYTHONPATH=. pytest tests/unit/docs/`, ~3 s) and **record the
   result in §8** — master plan §5 says the guard, not judgement, decides whether a
   `docs/domains/item_economics/` file needs updating. The projection measured it green under
   the full payload additions plus v2, so the expected answer is "no file needs updating"; the
   record of having checked is still owed.
7. **Handoff** to `handoffs/implementer/20260823_plan4_implementation_handoff.md`, frontmatter
   `plan`, `role`, `round`, `date`, `state`, `actor`.

## 9. Report back

In the handoff:

- **Your full write perimeter** — documents, code, and tool-recorded state (the graph delta).
  The coordinator diffs this against the tree; an undeclared write is a finding whoever made it.
- **The criteria ledger**: one row per **mutation**, with its site (file · definition vs call
  site), the contract value, the mutant value, and the **observed** failing test id.
- **Task 0's red baseline** — failing ids and count — recorded before any production edit.
- **Every evidence record** with hypothesis, scope, exact command, **tree identity** (SHA +
  asserted-clean `git status --porcelain`; a dirty tree adds a `git diff` digest), result, and
  the failing-ID delta in both directions.
- **Your mutation-probe declaration**: every file touched by a probe, with before/after
  checksums proving the revert — including C0 escape 1's created file and directory.
- **Any judgment call the plan left open**, named as such. The projection routed twenty
  findings and every one is folded, so the plan should determine nearly everything. **Where it
  does not, say so — do not quietly decide.** A plan defect found while implementing is worth
  more reported than worked around.
- **Anything you diverged from.** Divergence is often right — a quoted correction can be
  unimplementable for a reason only the implementer discovers — but an **undeclared** divergence
  costs the next reviewer a finding on a non-defect (charter rule 14).
- **The final chat message is written for the owner**, who has not read the plan: *What I did →
  What I found and what it means for you → What happens next → What needs you.* No section
  numbers, no `file:line`, plain words for every term of art. One pointer line to the handoff.
