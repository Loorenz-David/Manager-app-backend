---
plan: master_plan
role: planner
round: 0
date: 2026-08-22
state: PLANNED — master plan + six phase plans written, all phases NOT_STARTED
actor: Opus 5 (1M context), implementation-planner session
---

# Handoff — implementation-planner, `narrow_typical_work_times`

## 1. Opening summary

**The plan set is written: one master plan and six phase plans, every phase
`NOT_STARTED`. Zero owner cards.**

Gate check passed on entry, all four items: the intention header reads **RESOLVED (round
6), 0 owner cards open, D1–D25 settled** with the mechanism-inventory contracts written
(§2B, §3A, §3B, §4A, §4B, §4C, §6A, §6B, §6C, §11A); `owner_decisions.md`'s ledger is empty
and the three gate resolutions are marked **Ratified 2026-08-22**; the gate handoff exists
with verdict PASS-WITH-CONTRACTS and its one card resolved to D25; no `master_plan.md`
existed.

Six phases, strictly serial. The shape is **layer-first, then surface-by-surface**: the pure
engine, then the SQL, then the small additive carrier, then the two division consumers
together (they are forced together by one signature change), then price-scenario, then
closeout. Five of the six are projection-mandatory.

Seven decisions the artifacts left open are recorded in §6 below. None is owner-decidable —
each is a technical choice with no product consequence — but each is a place where a
downstream session would otherwise have guessed.

**L4 runs: 0.** Documents-only planning. No suite, no test execution at any scope, except
the docs guard (L1) named in §8.

## ⚠ OWNER DECISIONS REQUIRED (0)

**Nothing needs you.** Every question this planning session met was answerable from D1–D25,
the mechanism contracts, or the code. The seven planner decisions in §6 are technical and
reversible; none changes what the feature does for a user.

## 2. The six phases, and why each boundary is where it is

| # | Phase | Why the boundary is here |
|---|---|---|
| 1 | Pure typicals domain + the pre-refactor SQL snapshot | The whole engine is SQL-free and has no production caller, so it can be built and mutation-tested in isolation. **It also has to hold the T11 snapshot capture**: the pre-refactor compiled SQL string must be committed before any statement change lands, and this is the only phase where the tree is still pre-refactor. |
| 2 | Statement extension + the §12 measurements | Four of the inventory's five Critical mechanisms live in this one function and its predicate module. No consumer passes a spec yet, so **no payload moves and no golden regenerates** — the riskiest SQL in the pipeline lands with a zero-payload blast radius. |
| 3 | `TaskBudgetStatus` carries the derived spec | Small, additive, and it mutates a **shipped cross-pipeline dataclass** consumed by another pipeline's endpoint and by a money-redacted WORKER/SELLER face. A gate here contains that blast radius inside its own boundary instead of inside phase 4's much larger one. The lineage has already paid one round on this object. |
| 4 | Division contract + production-time + budget-allocations | **Forced together.** Changing `divide_production_budget`'s third parameter to `Mapping[str, SelectedTypical]` breaks both call sites at once, and a phase must close green. This is also where D18's removal edits two production files and where both changed goldens regenerate. |
| 5 | Price-scenario | It never calls division, so it separates cleanly — and it is the phase where T6's cross-service equality can finally be asserted over all three surfaces. It carries the ratified clock move and the `is_estimated` correction. |
| 6 | Closeout | Documents and the graph only. No production code, and no edit to a published handoff. |

## 3. Projection-gate triggers, per phase

The charter makes PROJECTED risk-triggered: mandatory when a phase touches a rule-6
silent-failure mechanism. The gate handoff's inventory is the risk map.

| # | Gate | Rule-6 surface it touches |
|---|---|---|
| 1 | **MANDATORY** | Spec dedupe identity (**Critical**, rank 3) · basis/count totality (High, 8) · the reconciliation quantifier (Medium, 15) · the resolution ladder (16) |
| 2 | **MANDATORY** | Spec→predicate translation (**Critical**, 1) · K-spec result shape (**Critical**, 2) · two-population FILTER arithmetic (**Critical**, 4) · LEFT-not-INNER (High, 10) · no fan-out (High, 11) · HC-4 byte-identity (13) |
| 3 | **MANDATORY** | `TaskBudgetStatus` across five construction surfaces (Medium-high, 12) — and A3's "which item derives the spec" is a question the intention did not answer until §6A |
| 4 | **MANDATORY** | Settled-basis guard (**Critical**, 5) · layer-2 terminals and the division-by-zero role (14) · basis/count totality on the wire (8) · the clock × spec signature (High, 6) |
| 5 | **MANDATORY** | `is_estimated` (High, 9) · the clock (High, 6) · the layer-2 terminal (14) |
| 6 | **WAIVABLE** | No rule-6 code surface. If the coordinator waives it, one recorded line. |

The gate is self-retiring: two consecutive empty ledgers demote it to optional for this
project, recorded in the master plan.

## 4. Risks and uncertainties for the coordinator

1. **Phase 1 is the largest pure-code phase — fifteen criteria.** It holds together as "the
   engine", but if its projection ledger comes back large, `plan_1.md` §7 records the clean
   split point: C1–C7 (spec, profile, evidence, policy) and C8–C15 (reconciliation, fallback,
   participating-set, snapshot), with the snapshot capture moving to whichever half runs
   first. Recorded as an option, not a recommendation.
2. **The snapshot capture is the one task that cannot be recovered.** If phase 1 ships without
   it, or captures it after touching `typical_times_statement`, T11 degrades back to
   `f(x) == f(x)` and HC-4 becomes unverifiable for the rest of the pipeline. Phase 1 task 1
   is deliberately the first task in the whole project, and it carries a stop-and-report
   condition: if the two clock forms do **not** compile to the same string, §4A K5's
   reasoned-not-measured claim has failed and every downstream HC-4 criterion rests on it.
3. **Phase 2's §12 matrix is a document, not a test.** Charter rule 1 says criteria are met by
   automated tests, so I did **not** dress the measurement up as one. It is a
   conditional-acceptance gate the reviewer checks against
   `planning/query_cost_measurements.md`, and it must carry **all ten** rows — five shapes ×
   {current statement, new statement}. §2B flagged that §12 states no count, and an unstated
   count is where a matrix silently ships at six.
4. **Phase 4 is the heavy one**: four production files, one test file with a 20-site
   mechanical edit, two goldens, and the Critical settled-basis guard. It cannot be split
   without leaving the tree red mid-phase. Expect more review rounds here than anywhere else,
   and budget for them rather than compressing.
5. **The golden regeneration reading.** D23 says "goldens regenerate once". Two goldens change,
   both in phase 4, in one act — which I read as satisfying it. Recorded in master plan §7 so a
   reviewer does not read a gate failure into two files moving at once. The keys-only criterion
   is per golden and is unchanged: **any changed numeric value is a gate failure, not a
   regeneration.**
6. **Phase 5 inherits a blind spot it must not extend.** `test_price_scenario_query.py`'s
   `_TypicalSession` discards the statement and pops pre-built results, so eight existing
   `_typical_block` tests never issue SQL. Every phase-5 row that constrains the statement call
   or the clock must run against a real session; `plan_5.md` §6 opens with that as a standing
   fixture rule.
7. **Five of the intention's own named mutations were inert** (T5, T7, T11, T14, T19) and §11A
   repaired them. Every mutation in these plans states both sides. The failure mode to watch in
   review is **re-introduction**: an implementer or reviewer reading §11.1 alone, without
   §11A, will write the inert form back. The plans name the inert version and say "do not
   re-introduce it" at each site.
8. **`TaskBudgetStatus` carries 14 fields, not 13.** §6A A1 says 13. Measured at source
   2026-08-22, `get_task_budget_status.py:38-51` carries fourteen, the fourteenth being
   `result: ItemCostResult | None`. The contract (additive only, appended last, defaulted) is
   unaffected — but §6A's own §2B lineage is about counted sentences being wrong, so this one
   is reported rather than silently corrected. **Upstream fix belongs in the intention**, not
   in a plan.
9. **The archived live-clock master plan's graph citation is stale.** It records 194 nodes /
   291 edges at revision `cec60a24…`; measured this session, the graph is **194 nodes / 296
   edges, revision `7241b831c3bd…`, 0 pending / 0 stale / 0 diagnostics**. This is a stale
   citation in an archived document, **not** a graph/code disagreement — nothing to file under
   `archgraph-discrepancies`. Master plan §8 carries the measurement and the instruction to
   cite the measurement, never a document's copy of it.
10. **Two suite runs in one checkout collide.** Both take the default `BEYO_TEST_SLOT` and
    therefore target the same `beyo_test_main_gw0…gw5` databases. Never run two concurrent
    suite sessions here; distinct worktrees need distinct slots. This bites hardest if the
    coordinator is tempted to run a projection and an implement session at once.

## 5. Semantic gaps routed upward

Two, both documentation defects in the intention rather than open questions. Neither blocks a
phase; both belong in the intention, per the home-artifact rule, and I did **not** patch them.

- **§6A A1's "13 fields"** — measured 14 (item 8 above).
- **§6.2's header still says "all four"** over a table that §6A A5 makes **seven** rows.
  §2B's count check already recorded the six-row form; §6A added the seventh and the header
  was not revisited. Cosmetic, but this document's own §2B is a monument to counted sentences
  going wrong.

## 6. Decisions this planner made, and why

Each is a place the artifacts left a real choice. None is owner-decidable; all are recorded so
a downstream session finds a decision rather than a gap.

1. **`typical_constants.py` — the three typical constants move to a leaf module.**
   `typical_filters` needs `TYPICAL_MIN_SAMPLE_SIZE`; `budget_division` needs
   `apply_business_fallback` from `typical_filters` at runtime (D22/§8: one implementation, two
   terminals). That is a circular import. Moving `TYPICAL_METHOD`, `TYPICAL_WINDOW_DAYS` and
   `TYPICAL_MIN_SAMPLE_SIZE` to a leaf module and re-exporting them from `budget_division`
   breaks it, changes no value, and changes **no call site** — `budget_division.__all__`
   already exports all three. Import direction after V1: `typical_constants ← typical_filters
   ← budget_division`.
2. **`apply_business_fallback`'s signature.** §8 writes `-> resolved values`. Fixed as
   order-preserving `Sequence[int | None] -> list[Fraction]`, `terminal` keyword-only, with an
   `isinstance(terminal, Fraction)` entry guard that fails closed — which is §11A T14's repair
   and charter rule 11 (safety rules bind at boundaries).
3. **`reconcile_task_typicals`'s signature**, written nowhere: it takes the evidence mapping,
   the spec, the participating set **and the task's full section set**. The fourth argument is
   what makes §3B B4 total — a section in the task's steps and absent from the evidence yields
   the zero-evidence row rather than a `KeyError`.
4. **`SelectedTypical` carries `sample_count`.** §3.6 defines the value; §3.5's shape omits the
   field. Carrying it means no consumer re-derives §3.6's rule — the fork HC-1 forbids, one
   layer up.
5. **§6A A4: pass the item through at all four `_empty_status` call sites**, rather than record
   the ambiguity's expiry beside the field's default. §6A offers both. The stronger branch costs
   four argument passes and removes an obligation the `COMPARABILITY_PROFILE` v2 return path
   would otherwise inherit — the silent policy drift D11 exists to prevent.
6. **The deferred statistics route's query-parameter names** (`item_category_ids`,
   `major_categories`, `designers`, `width_cm_min`/`_max`, `height_cm_min`/`_max`,
   `depth_cm_min`/`_max`, `can_have_upholstery`), fixed in master plan §6.8. `parse_spec_from_query_params`
   ships in phase 1 per §9, and its parameter names are fixed nowhere upstream. Flagged because
   they become a public contract when the route ships. One semantic point is pinned there: both
   bounds absent means the field is **not set**, never `(None, None)` — those are different
   populations.
7. **§3A C3's `coalesce(…, FALSE)` is marked STRUCTURALLY HELD** (plan 2, C11) with its trigger
   named. No fixture can separate `NULL` from `FALSE` today inside `count(...) FILTER`; the
   interim instrument asserts the compiled predicate's shape, and the criterion converts to a
   behavioural row the first time any predicate negates the item match. Planner doctrine
   requires this rather than a criterion that looks testable and is not.

## 7. Write perimeter

Generated from `git status --porcelain`, not retyped. Repo root
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`, branch `main`,
HEAD `1e479df`. **Nothing committed, nothing pushed. No code, no tests, no graph writes.**

```
$ git status --porcelain          # re-taken on the tree handed over
?? .archgraph/contexts/
?? docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/planner/
?? docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md
?? docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/
```

Written by this session (8 paths, all inside the declared perimeter):

```
docs/.../narrow_typical_work_times/master_plan.md
docs/.../narrow_typical_work_times/plans/plan_1.md
docs/.../narrow_typical_work_times/plans/plan_2.md
docs/.../narrow_typical_work_times/plans/plan_3.md
docs/.../narrow_typical_work_times/plans/plan_4.md
docs/.../narrow_typical_work_times/plans/plan_5.md
docs/.../narrow_typical_work_times/plans/plan_6.md
docs/.../narrow_typical_work_times/handoffs/planner/20260822_planner_handoff.md
```

Not written by this session: `.archgraph/contexts/` (the impact context, built 2026-08-22 by
the coordinator, **read-only** here).

**`prompts/coordinator/` was not opened.** The seal is intact for this round.

**Architecture graph: zero `archgraph_*` write calls.** Oriented read-only via
`archgraph_status` and `archgraph_read_current_context`. **No discrepancies to file** — the
context reports "Stale source-link warnings: None", and status reports 0 pending / 0 stale /
0 diagnostics at revision `7241b831c3bd…`.

## 8. Evidence

**L4 runs: 0.** The budget held exactly. No suite was started at any scope; no test was
executed. Every code fact cited in the plans was read at source this session
(`get_working_section_typical_times.py`, `budget_division.py`, `get_task_production_time.py`,
`get_task_budget_allocations.py`, `get_task_price_scenario.py`, `get_task_budget_status.py`,
`get_task_budget_status_worker.py`, `division_serializers.py`, `app/pytest.ini`,
`tests/unit/docs/`), and where it disagreed with the intention that disagreement is reported in
§4 and §5 rather than folded silently.

**L1 docs guard**, run per the session prompt:

```
$ cd app && PYTHONPATH=. pytest tests/unit/docs/
6 workers [59 items]
59 passed in 3.23s
```

Scope L1. Tree: HEAD `1e479df`, worktree dirty with exactly this session's document writes
(perimeter in §7). Result: clean, no failures, no errors.

Stated precisely, because "I ran the guard" and "the guard covers what I wrote" are different
claims: **the guard's roots are `app/` and `docs/handoff/`**
(`test_item_economics_handoff_accuracy.py:22-24`) plus `docs/domains/item_economics/`
(`test_item_economics_docs.py:20`). This session wrote only under
`docs/architecture/under_construction/`, which **none** of those roots covers — so the run is a
precaution, not a coverage claim. The first session that writes under a guarded root is
**plan 6**, and `plan_6.md` task 1 makes running the guard its first act.

## 9. Exit

Plan set written; tracker all `NOT_STARTED`; zero owner cards. Hand to the
**pipeline-coordinator**, whose next act is the phase-1 projection prompt (the gate is
mandatory) under `prompts/reviewer/` as `round: 0`.

Expect the plans to change — review lessons will tighten criteria mid-flight. That is the
system working, and folding them in is the coordinator's, per the home-artifact rule:
semantic changes amend the intention, skeleton changes amend the master plan, phase-local
changes amend the plan file. Never the other way round.
