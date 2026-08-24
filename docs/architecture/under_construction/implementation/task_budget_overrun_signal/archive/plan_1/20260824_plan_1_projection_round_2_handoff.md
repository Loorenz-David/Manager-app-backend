---
plan: plan_1
role: projection
round: 2
date: 2026-08-24
verdict: AMENDMENTS_REQUIRED
actor: Codex (GPT-5)
---

Phase 1 is not ready to hand to an implementer yet. The rule itself is fully settled and
nothing needs an owner decision, but four small gaps still leave room for two different test
implementations to claim success. The coordinator can fix all four in the phase plan without
changing product meaning, after which the phase should be projected again. No code was edited
and no tests or probes were run.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required; every finding is a plan-local precision amendment.

## Decision ledger

| ID | Decision point | Classification | Proposed routing |
|---|---|---|---|
| PROJ-01 | Task 0 requires intention §12A P3 for C4(e), but the closed Read-first selection omits P3. | plan gap | Add P3 to the §12A selection in plan §2, or replace the Task-0 citation with an already-listed authority that contains the full excluded-row derivation. |
| PROJ-02 | C5(b) names the same four-field assertion as C5(a) but supplies only two expected values, while MUT-17 requires a projected-cost assertion on C5(b). | plan gap | Replace C5(b)'s expected value with the explicit four-tuple `(152, 9, 152, 9)`. |
| PROJ-03 | MUT-18 and MUT-19 name “the two-step `price_scenario` inverse” but do not fix the actual two rounding operations. A mutation author must choose an inverse rather than transcribe one. | plan gap | Spell the mutant out at both call sites, including the intermediate centiminute rounding and the final minor-unit rounding (or cite a listed source block that fixes those exact expressions). Keep C5(c) as the witnessing row. |
| PROJ-04 | Master-plan §6.2 fixes `NO_CURRENCY: Final[str] = "no_currency"`, but C7/C8 never assert that constant's exact type and value; the vocabulary and literal-count checks can pass while the public sentinel is wrong. | plan gap | Extend C7(a) (or add an addressable C7 row) with `type(NO_CURRENCY) is str` and `NO_CURRENCY == "no_currency"`; add a named wrong-value mutation and update the closed mutation count/ledger. |

No intention gap and no free-choice delegation was found.

## Reality checks and decidability

### Gate and artifact reality

- `master_plan.md:99-105` has phase 1 at `NOT_STARTED`, with projection mandatory and the
  round-0/1 amendments folded.
- `plans/plan_1.md:298-303` contains exactly the coordinator's two 2026-08-24 projection-fold
  entries and no implementer or reviewer entry.
- `planning/intention.md:4-10`, `:69`, and `:2090-2102` establish `RATIFIED`, round 10,
  mechanism-inventory complete, and no owner decision open. The stale historical wording in
  the §10 heading does not reopen the header gate.
- Both files in `plans/plan_1.md:47-55` are absent and therefore correctly marked `NEW`.
  Every listed pre-existing source path exists. The cited source symbols and line anchors resolve
  in the current tree: `DivisionStep`, `_budget_seconds`, `_state_value`, `_governing_step`,
  `_step_state_is_terminal`, `divide_production_budget`, the allocator floor, the calculator
  guards and money function, the two enums/constants, the copied fixture helpers, and the purity
  sweep.
- Architecture Graph status was valid at revision
  `344f99e481463b7753ebc56356222ed6c6fab2c6636e77fb66870b547b384db0`: 204 nodes,
  308 edges, 6 stale nodes, 3 pending reviews, permission mode `review`, and no diagnostics.
  The prescribed budget search and three anchor reads resolved. They create no phase-1 decision
  and no graph delta; no graph write or review/maintenance mutation was made.

### Findings

#### PROJ-01 — Task-0 authority is outside the declared Read-first selection

`plans/plan_1.md:27-31` limits §12A to P1, P7, P8, P11 and P12. Task 0 then directs the
implementer to re-derive C4(e) from P3 at `plans/plan_1.md:59-65`. P3 exists at
`planning/intention.md:2142`, so this is not a broken citation; it is an input-closure defect.
The fixture and expected result are otherwise exact and source-derivable. Adding P3 to the
Read-first selection removes the contradiction without changing a criterion.

#### PROJ-02 — C5(b) does not state its four-field expected outcome

At `plans/plan_1.md:136-140`, C5(a) defines a four-field assertion and a four-tuple, while C5(b)
says `same` but gives only `(152, 9)`. At `plans/plan_1.md:199-202`, MUT-17 explicitly depends
on C5(b)'s projected-cost assertion. The allocator shape makes both pairs `(152, 9)`, and the
plan's own probe output at `plans/plan_1.md:274-282` confirms the money result, but the criterion
must say `(152, 9, 152, 9)` so a test author cannot reasonably implement only the incurred pair.

#### PROJ-03 — the two-step money mutant is not mechanically transcribable

`plans/plan_1.md:201-202` fixes the call site and witnessing row for MUT-18/19 but not the
mutant expression. The semantic authority at `planning/intention.md:707-713` says the forbidden
derivation double-rounds through whole centiminutes, and `:785-793` fixes 40 seconds as its
witness, but neither the plan's Read-first code list (`plans/plan_1.md:33-41`) nor the mutation
row states the two exact inverse operations. The intended mutant can be derived from additional
source exploration, but choosing how to invert a forward rounding chain is precisely silent
freedom. Record the exact intermediate and final expressions in the mutation rows.

#### PROJ-04 — the fixed sentinel constant is not closed by the API criteria

Master-plan §6.2 fixes `NO_CURRENCY` at `master_plan.md:168-172`. C7(a) checks only
`CURRENCY_VOCABULARY`; C7(b) checks the persisted enum and uses the sentinel as a comparator;
C7(c) counts the literal; and C7(d) prevents spelling the three persisted values
(`plans/plan_1.md:159-166`). C8's fixed-surface rows cover the four state constants, floor,
dataclass and callables but not `NO_CURRENCY` (`plans/plan_1.md:168-176`). A module can therefore
carry a wrong `NO_CURRENCY` value while constructing the vocabulary from the one permitted
literal and still satisfy every stated assertion. Pin the sentinel directly and give that
assertion its own wrong-value mutation.

### Criterion-by-criterion decidability

| Criterion | Result |
|---|---|
| C1 | Decidable. All eight enum members, the enum-to-string boundary, the derived terminal set, the with/without-`y` work-ahead cases, and the typed-out-set mutant have exact outcomes. |
| C2 | Decidable. The allocator emits `-600/+600`, so the inside-sum clamp, seconds, cost and verdict are exact and MUT-03 reaches all three rows. |
| C3 | Decidable. D1's unequal-typical excluded-step fixture, D9's two clamps, second-domain operands and exact returned-field types are fixed. |
| C4 | Decidable after PROJ-01 closes the declared input set. The 59/60 boundary, empty/all-excluded D10 cases and sum-guard mutant have exact results. |
| C5 | Not fully decidable until PROJ-02 and PROJ-03 are folded. All other call identity, type, sign, precision, zero-cost and rate-scaling rows are exact. |
| C6 | Decidable. The six reachable state rows, both populated pairs, precedence competition, sub-floor populated projection and unreachable-row invariant all have exact tuples. |
| C7 | Behavior is decidable, but the fixed sentinel API is incomplete until PROJ-04 is folded. The derived vocabulary, persisted-enum absence probe and one-literal rule are otherwise exact. |
| C8 | Decidable for every surface it names: state constants/set, floor, exact dataclass fields, frozen behavior and all four callable signatures. |

The 34 declared mutation rows are consecutively numbered and each has a stated bite row. Their
ledger is not actually closed until PROJ-03 fixes the two-step mutant expression and PROJ-04
adds the missing sentinel mutation and updates the derived total.

## Trace verification

### Forward: criterion row to authority

- C1, C3, C4 and C8 resolve to M1 and their cited projection contracts.
- C2 resolves to M3 and the per-section-clamp contract.
- C5 resolves to M2 and the money-call contracts. PROJ-02/03 concern decidability and mutation
  transcription, not the semantic root.
- C3, C6, C7 and C8 resolve to M4 and the D9/D10, row, vocabulary and API contracts.
- No criterion claims M5 or M6 in this pure-rule phase.

No trace cell points at an unrelated ledger entry. PROJ-04 is a missing closure assertion for an
already traced M4 contract, not a new measurement objective.

### Reverse: claimed measurement to criterion

| Claimed phase measurement | Serving criteria |
|---|---|
| M1 — backend projection rule and boundaries | C1, C3, C4, C8 |
| M2 — money identity and exact call behavior | C5 |
| M3 — per-section clamp prevents cancellation | C2, C4 |
| M4 — explicit state/row vocabulary and rule output | C3, C6, C7, C8 |

All M1–M4 measurements claimed by phase 1 are served. No unclaimed M5/M6 work is introduced, and
the test plan does not imply a test without an addressable criterion row once the four amendments
are folded.

## Write perimeter and evidence budget

Session write:

- `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/reviewer/20260824_plan_1_projection_round_2.md` — new, this handoff only.

Tool-recorded state:

- Architecture Graph: read-only status/search/node reads; no delta.
- No other external or repository state mutation.

Full repository status at close (the entries other than this handoff were pre-existing and were
not modified by this session):

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
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/reviewer/20260824_plan_1_projection_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/reviewer/20260824_plan_1_projection_round_2.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/master_plan.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_2.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_3.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/planner/20260824_implementation_planner_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/planner/20260824_mechanism_inventory_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/reviewer/20260824_plan_1_projection_round_0.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/reviewer/20260824_plan_1_projection_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/reviewer/20260824_plan_1_projection_round_2.md
?? docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md
```

L4 runs: 0; tests executed: 0.
