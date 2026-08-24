---
plan: plan_1
role: projection
round: 0
date: 2026-08-24
verdict: AMENDMENTS_REQUIRED
actor: Codex (GPT-5)
---

Phase 1 is not ready for implementation yet. The product decisions are complete and nothing
needs the owner, but the plan contains six proof or dispatch defects that would force the
implementer to improvise or would let an incorrect implementation appear covered. The pure
rule itself is derivable from the ratified authority; the coordinator should amend the plan
and send it through projection again before compiling the implementer prompt.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required; every ledger row is a plan correction for the coordinator.

## Verdict

`AMENDMENTS_REQUIRED`. The decision ledger is non-empty. No intention gap or owner-only free
choice was found.

## Decision ledger

| ID | Decision point | Classification | Proposed routing |
|---|---|---|---|
| PROJ-01 | How MUT-08 proves both exact calculator-input types and exact `BudgetSignal` field types | plan gap | Split the probe: retain a pre-call `Decimal` mutant for the calculator guard, and add a constructor/output mutant (or an explicitly malformed local signal checked by the same assertion helper) that reaches C3(d). Enumerate the exact-type sub-checks the amended probe set covers and update the closed mutation count. |
| PROJ-02 | How the typed-out currency-vocabulary mutant isolates derivation from sentinel uniqueness | plan gap | Change MUT-21 to type out only the three persisted values and union `{NO_CURRENCY}`, or record both C7(c) and C7(d) in its bite set. The first form preserves the intended C7(d)-only isolation. |
| PROJ-03 | Which phase proves that rate scaling is exact on an ORM-read `Numeric(12,4)` value | plan gap | Keep a phase-1 pure arithmetic example only if its trace is narrowed accordingly; route the authority's ORM-read invariant and positive committed-rate condition to the service/integration consumer phase. Do not claim that C5(f)'s hand-built `Decimal`s discharge §4A.2. |
| PROJ-04 | How the fixed public API is protected | plan gap | Add structural criterion rows and named probes for at least `BUDGET_STATES`, the four state constants, `PROJECTED_OVER_FLOOR_SECONDS`, the exact `BudgetSignal` field surface, and `frozen=True`/immutability. Task 1 currently forbids writing these missing tests because no criterion row purchases them. |
| PROJ-05 | What Task 0 means by re-deriving “every figure” | plan gap | Extend §7's probe to emit every allocator/money figure the criteria ask the implementer to diff, notably C4(e) and the three C5(f) scaling values, or narrow Task 0's statement and name the separate derivation source for each omitted row. |
| PROJ-06 | What base path the Read-first source references use | plan gap | Rewrite the source paths consistently as repository-relative `app/beyo_manager/domain/...` or working-directory-relative `beyo_manager/domain/...`; retain `tests/...` as working-directory-relative. The current mixed path bases do not resolve from the declared `backend/app/` working directory. |

## Findings

### PROJ-01 — MUT-08 reddens before C3(d)'s asserted sub-check is reached

- **Artifact:** `plans/plan_1.md:115,176,191-192`; `master_plan.md:220-223`;
  `app/beyo_manager/domain/item_economics/calculator.py:326-340`.
- **Finding:** MUT-08 changes `over_seconds` to a `Decimal`. The fixed skeleton calls
  `calculate_consumed_cost_minor(over_seconds, rate)` before constructing or returning the
  signal, and the calculator rejects non-exact `int` seconds at its entry guard. C3(d) may be
  reported red because the call raises, but its assertion over returned fields never runs.
  That violates the plan's own rule that each mutation must reach its named sub-check.
- **Correction:** separate the call-input mutant from an output-field mutant/probe and update
  the closed mutation ledger. A red exception is valid evidence for §4A.1's call guard; it is
  not evidence that C3(d)'s field-type loop can observe a malformed returned field.

### PROJ-02 — MUT-21's declared bite set is false

- **Artifact:** `plans/plan_1.md:158-161,188-189`; `master_plan.md:171-172`;
  `planning/intention.md:990-1000`.
- **Finding:** the correct module already contains the sole quoted sentinel in
  `NO_CURRENCY = "no_currency"`. MUT-21 adds a second quoted `"no_currency"` inside the
  typed-out vocabulary. C7(c)'s package-wide literal count therefore becomes two, while
  C7(d) also sees the three typed persisted values. The ledger says C7(d) only, which cannot
  be the observed result of the specified mutation.
- **Correction:** isolate derivation with
  `frozenset({"swedish_krona", "danish_krona", "euro"}) | {NO_CURRENCY}` so C7(d) alone
  reddens, or truthfully declare both bite rows.

### PROJ-03 — C5(f) cannot discharge the authority it cites in this phase

- **Artifact:** `plans/plan_1.md:12-22,127-139`; `planning/intention.md:795-813`.
- **Finding:** C5(f) supplies hand-built `Decimal` rates to the pure rule. Section 4A.2
  explicitly requires the scaling invariant to be asserted on a value read back through the
  ORM, because scale 4 is the fact that makes `int(rate.scaleb(4))` exact; it also derives
  positive committed rates from the commit path. Phase 1 explicitly permits only pure unit
  tests and no database, so the criterion and its authority cannot both be satisfied here.
- **Correction:** narrow C5(f) to the pure transformation it can prove and route the ORM-read
  scale/positivity invariant to the service integration phase, or deliberately widen this
  phase and its file/environment perimeter. The former preserves the planned pure seam.

### PROJ-04 — fixed API elements can be omitted or weakened while every listed criterion stays green

- **Artifact:** `master_plan.md:168-208`; `plans/plan_1.md:63-70,79-161,256-265`.
- **Finding:** the fixed API requires `BUDGET_STATES`, four named state constants,
  `PROJECTED_OVER_FLOOR_SECONDS`, and a frozen dataclass with an exact field surface. The
  criteria exercise behavioral string results and the sentinel, but no row asserts
  `BUDGET_STATES`, the public state/floor constants as API, or frozen immutability. Removing
  `BUDGET_STATES` or changing `@dataclass(frozen=True)` to a mutable dataclass does not change
  any stated expected result. Task 1 simultaneously says tests may be written only from the
  criteria table, so the implementer has no authorized way to close this coverage hole.
- **Correction:** add addressable structural rows and one named failing probe per sub-check;
  include exact fields/no `task_id`/no `currency`, immutability, the state vocabulary, and the
  public floor constant.

### PROJ-05 — Task 0's supplied probe cannot re-derive every claimed figure

- **Artifact:** `plans/plan_1.md:58-60,119-139,194-254`.
- **Finding:** Task 0 says to run §7 and diff every figure in the criteria tables. The probe
  has no C4(e) shape (skipped 600 plus cancelled 300 under `60.00`) and never emits C5(f)'s
  `scaleb(4)` results for `0.0001` or `99999999.9999` (nor its asserted `37500` field). It
  therefore cannot perform the declared complete diff.
- **Correction:** add those fixtures/output rows to §7, or replace “every figure” with an
  enumerated coverage list and name the independent derivation for every excluded figure.

### PROJ-06 — Read-first source paths do not resolve from the declared working directory

- **Artifact:** `plans/plan_1.md:33-40`; `master_plan.md:387-400`.
- **Finding:** the environment fixes the working directory at `backend/app/`. From there,
  `tests/unit/...` resolves, but `domain/item_economics/budget_division.py` and the other
  `domain/...` references do not; their actual working-directory-relative base is
  `beyo_manager/domain/...`. Repository-relative source paths are
  `app/beyo_manager/domain/...`. The source symbols and stated line anchors do exist at the
  corrected paths.
- **Correction:** make the path base explicit and consistent throughout the Read-first row.

## Reality check

- Gate artifacts resolved: master tracker phase 1 is `NOT_STARTED` with mandatory projection;
  the plan Review log is empty; the intention header is `RATIFIED`, round 10, and its round-10
  changelog says mechanism inventory is complete with no owner decision open.
- Both expected change files are correctly marked new and are absent:
  `app/beyo_manager/domain/item_economics/budget_signal.py` and
  `app/tests/unit/domain/item_economics/test_budget_signal.py`.
- All cited source symbols resolve at their corrected paths: `DivisionStep` line 35,
  `_state_value` line 55, `_budget_seconds` line 69, `_governing_step` line 180,
  `_step_state_is_terminal` line 202, `divide_production_budget` line 289, and the allocator
  floor line 328. The calculator guard and money function resolve at lines 83-120 and 326-340.
- Source confirms the critical premises: section state is serialized to `str`; terminal
  constants contain enum members; allocator rows carry integer-or-`None` `left_seconds` and
  floor distributable seconds per the authority; the calculator exact-type guard rejects a
  `Decimal` seconds input before signal construction.
- `test_budget_division.py:15-33` contains the copyable `selected` and `step` helpers.
  `test_domain_purity.py` recursively sweeps item-economics Python modules and includes both
  prohibited words named by the plan.
- There is no prior-phase implementation dependency. No configuration or plumbing decision
  was hidden in this pure phase.

## Criteria decidability

| Criterion | Paper result |
|---|---|
| C1 | Decidable from the eight-member enums, allocator state serialization, and terminal/excluded partitions. MUT-01 and MUT-02 are statically distinguishable. |
| C2 | Decidable. The per-section clamp produces 600 and the sum-clamp mutant produces zero. |
| C3 | Behavioral figures are decidable and D9/D1 are fully determined. C3(d)'s claimed MUT-08 evidence is not reachable (PROJ-01). |
| C4 | The 59/60 pair and D10 empty-set cases are decidable. C4(e)'s expected result is derivable, but it is missing from the mandatory Task-0 probe (PROJ-05). |
| C5 | Rows (a)-(e) are decidable and distinguish the two prohibited money derivations. Row (f) is calculable in pure code but cannot meet its cited ORM-backed contract (PROJ-03). |
| C6 | All six reachable state rows, precedence competition, both populated pairs, and the unreachable-row invariant are decidable from the authority. |
| C7 | The criteria themselves are decidable and the local copied-enum guard can prove it observes a fourth member. MUT-21's declared isolated bite set is impossible (PROJ-02). |

The non-authoritative implementation skeleton used for this check was discarded and is not
included here as implementer guidance.

## Trace verification

### Forward: criterion to authority

- C1 resolves to §3.2/§3A.2/§3A.3 and M1.
- C2 resolves to §3.3/§3A.4 and M3.
- C3 resolves to D1/D9, §3A.4/§3A.5, and M1/M4.
- C4 resolves to D6/D10, §3A.4/§3A.6, and M1/M3.
- C5(a)-(e) resolve to the mandatory money call, exact input guard, 40-second inverse witness,
  and zero-minor boundary under M2. C5(f)'s §4A.2 trace is not discharged as written
  (PROJ-03).
- C6 resolves to the reachable decision table, D2/D8/D9, both-pairs rule, and M4.
- C7 resolves to the wire-only sentinel contract and M4.

### Reverse: claimed phase measurements to criteria

- M1 is served by C1, C3, and C4.
- M2 is served by C5(a)-(e); the production-path half of §4A.2 remains unrouted in this plan.
- M3 is served by C2 and C4.
- M4 is served by C3, C6, and C7.

No criterion row is untraced. The only semantic trace defect is the overclaim at C5(f); the
remaining ledger entries concern proof reachability, fixed-API completeness, probe completeness,
and reference resolution.

## Architecture-graph orientation

- **Status:** initialized and valid; permission mode `review`; 204 nodes, 308 edges, revision
  `344f99e481463b7753ebc56356222ed6c6fab2c6636e77fb66870b547b384db0`; 6 stale nodes and
  3 pending reviews were pre-existing observations.
- **Inspected/reused:** `projection-item-economics-task-budget-allocations`,
  `endpoint-item-economics-task-budget-allocations`, and
  `decision-money-audience-admin-manager-only`, including their evidence, relationships, and
  source links. The existing allocation projection's four `reads_from` edges and source-file
  implementation anchor support the plan's reuse boundary.
- **Impact:** bounded at maximum depth 2; reached depth 2 with 6 direct and 30 transitive
  entries, no possible entries, and no truncation.
- **Unresolved/pre-existing:** the allocation projection's accepted test source link is stale;
  it is unrelated to this plan-amendment verdict and was not repaired. The project instruction
  forbids reading or overwriting the current generated context, so context cost was 0.
- **Created/changed:** none. Exploration budget: depth 2/2, new graph nodes 0/0, context
  characters 0. No graph review, maintenance, or additive mutation was attempted.

## Write perimeter and evidence budget

Session-authored filesystem change: only this handoff. No code, test, plan, intention, tracker,
prompt, or graph file was edited by this session. The full post-write `git status --short
--untracked-files=all` perimeter is:

```text
 M .archgraph/architecture.yml
 M docs/archgraph-anchor-observations.md
 M docs/architecture/under_construction/implementation/task_budget_overrun_signal/planning/intention.md
?? .archgraph/backfill/README.md
?? .archgraph/backfill/batch-01.json
?? .archgraph/backfill/batch-02.json
?? .archgraph/backfill/batch-03.json
?? .archgraph/backfill/batch-04.json
?? .archgraph/backfill/batch-05.json
?? .archgraph/backfill/batch-06.json
?? .archgraph/backfill/batch-07.json
?? .archgraph/backfill/batch-08.json
?? .archgraph/backfill/batch-09.json
?? .archgraph/backfill/batch-10.json
?? .archgraph/backfill/batch-11.json
?? .archgraph/backfill/needs-repair.md
?? .archgraph/backfill/pending-review.md
?? .archgraph/backfill/span-only.md
?? .archgraph/backfill/summary.json
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/planner/20260824_implementation_planner_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/planner/20260824_mechanism_inventory_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/reviewer/20260824_plan_1_projection_round_0.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/master_plan.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_2.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_3.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/planner/20260824_implementation_planner_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/planner/20260824_mechanism_inventory_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/reviewer/20260824_plan_1_projection_round_0.md
?? docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md
```

All entries except this handoff pre-existed the session and were left untouched.

**L4 runs: 0; tests executed: 0.** No probe, collection, test, or suite command was run.
