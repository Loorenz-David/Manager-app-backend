---
plan: planning (project-level — belongs to no phase)
role: planner (implementation-planner doctrine)
round: 1
date: 2026-08-24
state: PLAN SET WRITTEN — master plan + 3 phase plans, tracker all NOT_STARTED
verdict: n/a (planning produces no verdict); manifest lint PASSED on all five properties
actor: Claude Fable 5, implementation-planner role
---

# Implementation-planner round 1 — Task Budget Overrun Signal

## Summary

Gate check passed on entry: `planning/intention.md` reads `status: **RATIFIED**` (round 9,
2026-08-24), records the owner's re-ratification on §10.6, and states mechanism-inventory is
complete with nothing marked OPEN. Tree `f376928`; `app/` byte-identical to the
`narrow_typical_work_times` gate (`git diff --stat 49a6e50 HEAD -- app/` empty).

**Written: one master plan and three phase plans** (7 / 8 / 6 criteria; 21 / 17 / 9 named
mutations), every criterion row addressable, every heading carrying a trace cell, every one
of the ledger's six outcomes and all 22 registered contracts (plus the numbered §3.1, §3.2,
§3.3, §3.4, §4.1, §4.2, §5, §7.3) reachable from at least one trace cell. **Three phases,
not the intention's tentative two**: the service/serializer/route half alone registers more
than eight independent contracts, and the service's dict return is a stable seam. Every
expected figure in the criteria tables was **derived** by running the shipped allocator and
calculator (the probe is reproduced in plan 1 §7 and executes verbatim — verified).

**Six planner findings** (§5), two of them corrections to the intention's contract text
(precision, not meaning). **No owner decision is needed.**

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Every decision D1–D10 is answered in the intention; the plan set
takes no call on the owner's behalf.

## 1. Write perimeter — documents, code, tool-recorded state

**Documents written — five, all inside the permitted set:**
1. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/master_plan.md` — NEW
2. `…/task_budget_overrun_signal/plans/plan_1.md` — NEW
3. `…/task_budget_overrun_signal/plans/plan_2.md` — NEW
4. `…/task_budget_overrun_signal/plans/plan_3.md` — NEW
5. `…/task_budget_overrun_signal/handoffs/planner/20260824_implementation_planner_round_1.md` — this file, NEW

**Not written:** the intention, any source or test file, either `from_frontend` handoff,
`docs/archgraph-anchor-observations.md` (per the prompt's standing finding: not altered, not
relied on), `Application_contracts`, `.archgraph/`.
**One write outside the repository, declared:** the harness's persistent memory entry for
this project (`~/.claude/projects/…/memory/project_task_budget_overrun_signal.md`) updated to
record "plans written, next gate projection of phase 1". Not a repo file; declared so the
perimeter claim can be checked against the tree rather than reconstructed.
**Scratch (session scratchpad, outside the repo):** `plan_probe.py`, `plan1_probe.py`.
**Code: none. Tests: none. Suite: not run** (only `--collect-only` and pure-domain probes).
**Architecture graph: zero writes.** Reads: `archgraph_status` (204 nodes / 308 edges, valid,
6 stale, 3 pending, mode `review`); `archgraph_search_nodes` for "budget allocations" (3 hits)
and "budget signal" (**0 hits** — no node exists yet); `archgraph_get_node` on
`projection-item-economics-task-budget-allocations`,
`endpoint-item-economics-task-budget-allocations`,
`decision-money-audience-admin-manager-only`. `archgraph_compute_impact` **not** called — the
project adds nodes and touches no existing node's boundary. `archgraph_build_context` **not**
called; `.archgraph/contexts/current-task.md` untouched. **Nothing committed.**

## 2. Plan-file inventory

| File | Phase | Criteria | Rows | Mutations | Projection gate |
|---|---|---|---|---|---|
| `plans/plan_1.md` | pure rule `budget_signal.py` | 7 | 34 | 21 | mandatory |
| `plans/plan_2.md` | service + serializer | 8 | 28 | 17 | mandatory |
| `plans/plan_3.md` | route + HC-2a + `to_frontend` handoff | 6 | 20 | 9 | waivable (coordinator) |

Counts derived by grep over the files this session (`^### C[0-9] —`, `^\| C[0-9]\([a-z]\)`,
`^\| MUT-`), not typed.

## 3. Manifest-lint evidence (charter's five properties)

1. **Identity** — every criterion heading is `C<n>` and every row `C<n>(<letter>)`; 34 + 28 + 20 addressable rows.
2. **References resolve** — every `file:line` newly introduced by the plans was re-read on
   `f376928` after writing: `item_economics.py:123-134, :346-360`; `README.md:79, :1648-1702`;
   `test_item_economics_router.py:14, :49, :101, :112, :125, :186`; mirror test `:33, :60, :115-128`;
   `test_budget_allocations_query.py:31, :131, :178-208`; `division_serializers.py:22-23, :57-71, :210-220`;
   `calculator.py:83-120, :326-341`; `budget_division.py:35, :55, :69, :180, :202, :289, :328`;
   `item_cost_evaluation.py:30-39, :56`; `handoff_accuracy.py:24-35, :226-233`;
   `live_worked_seconds.py:18-30`; `context.py:24`; `constants.py:4-9`; `enums.py:4-12`, `:11-14`.
3. **Counts derived** — mirror count `26` read at `:127`; `_ROUTES` length **23** and
   `_ALL_ROLE_ROUTES` **3** parsed by `ast`; README item-economics rows **26** by `grep -c`;
   docs guard **67** and item-economics radius **147** by `--collect-only`; file perimeter of
   plan 3 **7** (4 MOD + 3 NEW) summed from its table; every fixture figure from the probe.
4. **Closed mutation sets** — each plan's heading count equals its table's row count
   (21/21, 17/17, 9/9) and every mutation row names the criterion row(s) it must redden.
5. **Trace cells** — 21 of 21 criterion headings carry `trace **… → M<n>**`; coverage by
   grep: M1 ← plans 1, 2; M2 ← 1, 2; M3 ← 1; M4 ← 1, 2, 3; M5 ← 2; M6 ← 2, 3. All 22
   lettered contracts and the eight numbered ones appear in at least one trace cell (the lint
   first caught §3.1/§3.2/§5 cited only through their lettered deepenings; fixed in place).

What the lint does **not** see (charter): whether a row's assertion is weaker than its row, or
whether a guard can fail — plan 1 C1(d), C7(b–d) and plan 2 C7(b) are the rows where that
risk concentrates, and each carries a planted-defect mutation for exactly that reason.

## 4. Contract resolution (master plan §5, summarized)

Two copies of the contract system: canonical `Application_contracts/backend/architecture/`
(55 files) and the repo-local `backend/architecture/` (69 files: the 55 + 14 `*_local.md` +
3 app-only). **Independently verified: no `item-economics` / `budget-allocations` /
`item_economics` string exists anywhere in `Application_contracts`** — no published endpoint
row; nothing there needs one. **Selected:** 01, 04, 05 + `05_local`, 07 + `07_local`, 08,
09, 15, 21, 22, 25, 28, 29 §B, 46 + **`46_local`**. **Excluded, with reason:** 29 §B step 6 /
README rule 11 (endpoint shape in `docs/domains/<domain>/api.md`) — intention §7A.6 forbids
it and the docs guard accepts only the hand-written 23-route set; the documentation home is
`routers/README.md` (HC-2a artifact 2) plus the dated `to_frontend` handoff. Also excluded:
`07_local` pagination, 12, 18, 37, 47 (all deferred by §8). **Local baseline:** charter rules
+ master plan §9.

## 5. Planner findings — routed, none blocking

| # | Finding | Route |
|---|---|---|
| **F1** | **Intention §6A.2 row 4 is unreachable** and its third column header is stale. `over_seconds > 0 ⇒ raw − actual < 0 ⇒ projected_over_seconds ≥ 1` — derived and confirmed by the allocator (P-H4: all steps completed, 1 s past the pot → `over 1 / projected 1`). The three fixtures the table maps to "row 4" all carry non-zero projections (they are row 3 shapes with the D10 guard false). The header still says `remaining_commitment > 0` where D10 made it a set test. Precision only; the cascade in §6 is unaffected. Plans enumerate the six reachable rows and add the derived invariant `over ⇒ projected ≥ over` (plan 1 C6(h)). | coordinator → intention, a lettered note on §6A.2; no gate re-open |
| **F2** | **The two-step price-scenario inverse agrees with the shipped figure at 136 s and 152 s** (the half-tie durations where the exact rational disagrees); its first disagreement at rate `3.7500` is **40 s** (`2` shipped vs `3`). §4A.1's "each was measured to disagree" holds in aggregate (502 cases), not at the rows §4.2 names. Plan 1 C5(c) adds the 40-second row so MUT-15 has something to redden. | intention §4A.1 note (optional); plans already carry it |
| **F3** | **§7A.7's serializer placement is the local contract, not a deviation.** `backend/architecture/46_serialization_local.md` lists item-economics query services among the inline-serializing layer and rules that a change keeps serialization where the surrounding code has it. Reviewers must not file it. | master plan §5; intention §7A.7 may cite the local file |
| **F4** | **The contract system exists in two places** and the prior project's master plan already corrected itself on this once (its §5 says "no contract system" was wrong). The local `_local.md` files are authoritative extensions; `05_local` confirms §7A.3's "identity is a prefix, no code field" from the contract side. | master plan §5 |
| **F5** | **Documentation definition-of-done conflicts with the docs guard** for this path (README rule 11 vs `test_no_document_invents_a_fully_qualified_item_economics_path`). Resolved by exclusion, with the intention's instruction and the precedent that the three newer sibling routes are also absent from `api.md` (grep finds only `budget-status`). | master plan §5 |
| **F6** | **§6A.1's "must still compute the status for the no-evaluation branch" has no observable.** On this surface a task without an evaluation is `no_budget` whatever that branch returns. Planned as *structurally held* (plan 2 §7 note: copy the branch verbatim; reviewer confirms by source inspection) rather than as a row that cannot fail. | plan 2 note; intention §6A.1 may soften the sentence |

**Routing hazards from the inventory's §6, honoured:** the two-phase guess was not
preserved (three phases, reason in master plan §1); 22 registrations were discharged by
shared rows where the plans say so (e.g. §3A.4 by plan 1 C2/C3/C4; §7A.6 by plan 2 C1(b) and
plan 3 C4); the six rows-that-cannot-fail are named in master plan §9 rule 7 and each has the
escaping fixture in a criterion; the `to_frontend` handoff carries the **three corrections**
as pinned sentences (plan 3 C6(b)) and is kept out of `docs/domains/item_economics/*`; the
graph delta stays with the implementing phases (master plan §8).

**HC-2 / D5 preserved:** the worker-time-pressure handoff was read only to confirm it asks
for additive fields on `budget-allocations` — a different project. Nothing in the plan set
touches `budget-allocations`; the four HC-2a artifacts are the only pre-existing files any
phase edits (master plan §6.1, §9 rule 6).

**Standing coordinator finding recorded** as master plan §9 rule 1 (session write perimeters
are closed; an external standing brief never silently expands a prompt's allowed files) — a
process lesson, no criterion.

## 6. Environment evidence (master plan §10)

Verified at source this session: `app/pytest.ini` (`-n 6 --dist loadfile`, strict markers,
`asyncio_mode = auto`); `app/Makefile` (four `PYTHONPATH=. pytest` targets); `tests/conftest.py`
+ `tests/database_isolation.py` (disposable per-process databases from
`beyo_test_<slot>_template`, `BEYO_TEST_SLOT`, server `localhost:5433`); the docs guard collects
**67**; the five item-economics test files this project touches or mirrors collect **147**.
**Last published stamp cited, not measured: 21 failed / 2716 passed / 1 skipped** (narrow
plan-6 closeout, 2026-08-24) on an `app/` tree byte-identical to this one. The planner ran no
test; phase 1's implementer takes the first stamp on its own tree. The purity guard
`test_domain_purity.py` sweeps the new domain module automatically and greps for `digest`
— recorded as master plan §9 rule 9 so nobody writes the word in a docstring.

## 7. Source evidence inspected

Read at source on `f376928`: `get_task_budget_allocations.py` (whole), `division_serializers.py`
(whole), `budget_division.py:24-60, :69, :180-222, :289, :328`, `calculator.py` (def index,
`:326-341`), `live_worked_seconds.py:18-30`, `services/context.py:24`, `run_service.py:40-70`,
`routers/http/response.py`, `errors/validation.py`, `routers/api_v1/item_economics.py:1-40,
:60-80, :123-134, :336-372`, `routers/README.md:1-30, :58-83, :1648-1702`, `task_steps/constants.py`,
`task_steps/enums.py`, `items/enums.py:8-16`, `item_cost_evaluation.py:25-60`,
`typical_filters.py:325-344`, the two HC-2a test artifacts (whole), `test_budget_division_routes.py:54-140`,
`test_budget_allocations_query.py` (structure + `:1-140`), `test_budget_division.py:1-60`,
`test_domain_purity.py` (whole), `test_item_economics_docs.py` / `test_item_economics_handoff_accuracy.py`
(guards), `narrow_typical_work_times/master_plan.md` §5, §10 and `plans/plan_5.md` head (format
precedent), `Application_contracts/backend/README.md`, `…/architecture/README.md` (navigation
matrix), `07_queries.md`/`46_serialization.md` (headings), and the repo-local `05_errors_local.md`,
`07_queries_local.md`, `46_serialization_local.md`, `29_feature_workflow.md`/`15_testing.md`
(headings).

**Probes (pure domain, no DB, from `backend/app/` with `PYTHONPATH=. .venv/bin/python`):**
the fixture derivation reproduced in plan 1 §7 (run twice: once as scratch, once extracted
verbatim from the plan file to prove it executes); plan 2 C1(a)'s two-typical derivation
(`A: 3600, B: 1800` → allowances 2400/1200, projected `0`; equal split → `600`); the money
rows at `3.7500` (`40→2/exact 2/two-step 3`, `136→9/8/9`, `152→9/10/9`); the minute-domain
divergence (`3602 s` → true `2`, minute-domain `1`). The shaper's §12 and the inventory's §12A
probes were **cited, not re-run** — same `app/` tree.

## 8. Unresolved decision cards

**None.**

## 9. The explicit next gate

**Coordinator.** Consume this handoff; fold F1 (and optionally F2/F6) into the intention as
lettered notes; then **lint `plans/plan_1.md`** and compile the **projection prompt for
phase 1** (round 0, reviewer role) — projection is **mandatory** for phase 1 (money call,
derivations, the D9/D10 boundary). Only after the projection handoff's ledger is fully routed
does the phase-1 implementer prompt compile. Tracker rows stay `NOT_STARTED` until then.
No implementation prompt was authored by this session.
