---
plan: plan_1
role: projection
round: 1
date: 2026-08-24
verdict: AMENDMENTS_REQUIRED
actor: Codex (GPT-5)
---

The pure budget rule is semantically determined: its arithmetic, state order, currency boundary, and fixed data shape can all be implemented without asking the owner anything further. The revised plan is not ready to dispatch, however, because five test/mutation mappings do not prove the production seams they claim to prove. All five are plan-local corrections; the ratified intention remains coherent and no product decision is being reopened. The coordinator should fold the amendments below and commission another static projection before compiling the implementer prompt.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required; every ledger row routes to a plan amendment.

## Decision ledger

| ID | Decision point | Classification | Proposed routing |
|---|---|---|---|
| PROJ-01 | How the tests prove both production money call sites use the shipped function with exact `int` seconds and a `Decimal` rate | plan gap | Replace C5(g)'s direct calculator-guard test with a recording wrapper/spy around `budget_signal.calculate_consumed_cost_minor`, exercised through `compute_budget_signal` on a fixture with distinct over/projected operands (P-H2 is suitable). Assert exactly two calls, in order, with `(100, rate)` and `(1900, rate)`, `type(seconds) is int`, `seconds >= 0`, and a `Decimal` rate. Split MUT-08, MUT-15 and MUT-16 by over versus projected call site, update each must-redden row and the derived closed-set count. Retain C5(a)–(c) as the independent numeric witnesses for the two prohibited derivations. |
| PROJ-02 | Whether a precedence swap must redden the sub-floor both-pairs case C6(c) | plan gap | Remove C6(c) from MUT-18's must-redden set. A literal swap that preserves the `projected_over_seconds >= 60 and has_work_ahead` predicate leaves P-H3 at `over`, because its projection is only 30 seconds. C6(b) and C6(g) are the genuine precedence competitions. |
| PROJ-03 | How the currency-derivation guard is isolated from vocabulary membership | plan gap | Change MUT-22 to a derived-vocabulary mutant that preserves all four members while typing the persisted three, e.g. `frozenset({"swedish_krona", "danish_krona", "euro", NO_CURRENCY})`. As written, omitting `NO_CURRENCY` also reddens C7(a), contradicting “C7(d) only” and failing to isolate the no-respelling guard. Re-derive the mutation count if the amendment changes row structure. |
| PROJ-04 | How the dataclass closed-surface mutation reaches C8(c) rather than failing module import | plan gap | Make MUT-26 importable, for example by adding `task_id: str = ""` as the final field, or by updating the constant construction in the same mutant. A required ninth field makes `NO_BUDGET_SIGNAL = BudgetSignal(...)` raise during import, so no C8(c) test id or assertion line can be recorded. |
| PROJ-05 | Whether the master plan's fixed callable API is actually closed by C8 | plan gap | Add a C8 row that checks the exact names, parameter kinds (including `compute_budget_signal`'s keyword-only boundary), and resolved annotations/return types for `contributes`, `remaining_commitment`, `has_work_ahead`, and `compute_budget_signal`. Add named, importable mutations for the independently asserted signature sub-checks and update the closed-set count. Do not invent an `__all__` contract: the master plan fixes callable signatures, not an export-list mechanism. |

No ledger row is an intention gap or a free choice. The proposed amendments specify proof mechanics only; they do not alter D1–D10, M1–M6, or any mechanism contract.

## Reality check

### Dispatch gates

| Gate | Evidence | Result |
|---|---|---|
| Phase state and projection requirement | `master_plan.md:99-105`, phase-1 tracker row | PASS — `NOT_STARTED`; projection mandatory; round-0 amendments folded; re-projection required |
| Review-log shape | `plans/plan_1.md:290-294` | PASS — exactly the coordinator's 2026-08-24 round-0 fold entry |
| Intention authority | `planning/intention.md:1-24`, `:2080-2102` | PASS — `RATIFIED`, round 10; owner re-ratification recorded; mechanism-inventory complete; no owner decision open |

### Paths, symbols, and fixed inputs

- Both phase files are correctly marked new and are absent: `app/beyo_manager/domain/item_economics/budget_signal.py` and `app/tests/unit/domain/item_economics/test_budget_signal.py`.
- Every cited production symbol resolves at the stated source: `DivisionStep` (`budget_division.py:35`), `_state_value` (`:55`), `_budget_seconds` (`:69`), `_governing_step` (`:180`), `_step_state_is_terminal` (`:202`), `divide_production_budget` (`:289`), and the distributable floor (`:328`).
- The exact calculator guards and call resolve at `calculator.py:83-120` and `:326-341`; the call accepts exact `int` seconds and a `Decimal` rate and performs no sign guard.
- `TERMINAL_STEP_STATES` resolves at `task_steps/constants.py:4-9`; all eight step-state values resolve at `task_steps/enums.py:4-12`; the persisted currency enum remains exactly the three members at `items/enums.py:11-14`.
- The fixture helpers resolve at `test_budget_division.py:15-33`, and `test_domain_purity.py:6-50` recursively sweeps the future module and rejects the listed purity substrings and SQL/model imports.
- Static source search finds no current quoted `no_currency` literal under `app/beyo_manager`; the planned constant will therefore be the first and sole occurrence if implemented as fixed.
- The plan declares 27 mutation rows and currently contains 27. PROJ-01 and PROJ-05 require the coordinator to re-derive, not hand-edit, the replacement count.
- The non-authoritative implementation skeleton was derived task-by-task and discarded. No implementation guidance beyond routed test-contract corrections is retained here.

## Criteria decidability and mutation reach

| Criterion | Paper result |
|---|---|
| C1 | Decidable. The allocator emits string states, `completed` retains integer `left_seconds`, and excluded terminal states emit `None`; MUT-01/MUT-02 have distinct reachable bite. |
| C2 | Decidable. P-A yields `-600` and `600`; the per-section clamp gives commitment/projection `600`, whereas sum-then-clamp gives `0`. |
| C3 | Decidable. P-C, P-D, and P-B distinguish the two D9 clamps, served clamp, task-pot operand, and exact returned field types. |
| C4 | Decidable. The `59/60` boundary and P-E/P-F/P3 shapes separate the floor from the contributing-set guard. |
| C5 | **Not fully decidable as written.** Numeric rows decide the shipped money outputs, but C5(g) does not traverse either production call site and the singular MUT-08/MUT-15/MUT-16 wording does not close the independently required over/projected calls (PROJ-01). |
| C6 | Decidable after correcting one false reach claim. All six reachable state rows and the derived over-implies-projection invariant are concrete; C6(c) does not redden under a predicate-preserving precedence swap (PROJ-02). |
| C7 | Decidable after isolating MUT-22. C7(a) and C7(d) are individually assertable, but the current mutant breaks both instead of only the derivation row (PROJ-03). |
| C8 | **Incomplete as “fixed public API”.** Constants, floor, dataclass fields, and frozen behavior are decidable, but MUT-26 dies at import (PROJ-04) and the four fixed callable signatures have no closed criterion/mutation proof (PROJ-05). |

## Exact finding locations

- **PROJ-01:** `plans/plan_1.md:131-144`, `:190`, `:197-198`; `master_plan.md:201-223`; authority `planning/intention.md:746-783`.
- **PROJ-02:** `plans/plan_1.md:151-157`, `:200`; authority `planning/intention.md:1107-1167` and precision amendment §6A.2A.
- **PROJ-03:** `plans/plan_1.md:159-166`, `:204`; authority `planning/intention.md:983-1001`.
- **PROJ-04:** `plans/plan_1.md:168-175`, `:208`; fixed constructor and field order at `master_plan.md:188-207`.
- **PROJ-05:** fixed callable signatures at `master_plan.md:182-207`; partial criterion at `plans/plan_1.md:168-175`.

## Trace verification

### Forward: criterion row to authority

| Rows | Trace target | Result |
|---|---|---|
| C1(a-d) | §§3.2, 3A.2, 3A.3 → M1 | VALID — predicate representation and all eight states support every assertion |
| C2(a-c) | §§3.3, 3A.4 → M3 | VALID — each row isolates the per-section clamp |
| C3(a-d) | §§3.4, 3A.4, 3A.5, 6A.3 → M1/M4 | VALID — D1 and D9 support the exact operands, clamps, states, and integer outputs |
| C4(a-e) | §§3.3, 3A.4, 3A.6 → M1/M3 | VALID — D6/D10 support the floor and no-work-ahead boundaries |
| C5(a-g) | §§4.2, 4A.1-4A.3, §12A P8 → M2 | TARGET VALID; PROOF INCOMPLETE — C5(g) is attached to the right authority but does not exercise the claimed production seam |
| C6(a-h) | §§5.3, 6, 6A.2, 6A.3 → M4 | VALID — all reachable rows and precedence are supported; only MUT-18's claimed bite set is wrong |
| C7(a-d) | §§5.1, 5A.3 → M4 | VALID — vocabulary, persistence boundary, sentinel uniqueness, and derivation are all supported; mutant isolation needs repair |
| C8(a-d) | master §6.2, §§3.3, 5A.3 → M1/M4 | PARTIAL — covered assertions trace correctly, but the callable portion of the cited fixed API is absent |

### Reverse: claimed phase outcomes to rows

| Claimed outcome | Serving rows | Result |
|---|---|---|
| M1 — backend projection rule | C1, C3, C4, C8(b) | COVERED, subject to C8 callable-surface amendment |
| M2 — shared money function | C5 | INCOMPLETE until PROJ-01 closes both production call sites |
| M3 — no cross-section cancellation | C2, C4 | COVERED |
| M4 — explicit, complete domain verdict vocabulary/shape | C3, C6, C7, C8 | COVERED, subject to PROJ-04/05 proof mechanics |

M5 belongs to the live service phase and is not claimed here. M6 is enforced for phase 1 by the closed two-new-file perimeter and the no-change rule; this phase does not claim a behavioral sibling-surface criterion. No criterion row is untraced, and no M1-M4 target is silently absent; the defects are strength and mutation-reach defects on existing traces.

## Architecture-graph orientation

- **Inspected:** valid graph at revision `344f99e481463b7753ebc56356222ed6c6fab2c6636e77fb66870b547b384db0`; 204 nodes, 308 edges, 6 pre-existing stale nodes, 3 pending reviews, no diagnostics. Read `domain-item-economics`, `projection-item-economics-task-budget-allocations`, `endpoint-item-economics-task-budget-allocations`, and `decision-money-audience-admin-manager-only`, including their evidence/source-link state.
- **Impact:** bounded depth 2 from `projection-item-economics-task-budget-allocations`; 6 direct and 30 transitive entries, none classified possible. This confirms the future rule belongs inside the pure Item Economics boundary and consumes the allocator projection without moving an endpoint or money-audience boundary in phase 1.
- **Reused:** the existing Item Economics domain and task-budget-allocation projection/endpoint anchors; no new architectural concept is asserted before code exists.
- **Created:** none. No graph mutation, review decision, maintenance preview, source link, or generated context was attempted.
- **Unresolved:** the phase-1 closing delta remains correctly “none or one `source_file` node” until implementation exists. The six stale nodes and three pending reviews are pre-existing and not part of this gate.
- **Budget/permission:** read-only use within `permissionMode: review`; traversal depth 2; 0 new nodes; 0 relationships; 0 context characters; 0 writes.

## Write perimeter and evidence budget

Session-owned write:

- `docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/reviewer/20260824_plan_1_projection_round_1.md`

Full repository status from `git status --porcelain=v1 --untracked-files=all` at close (all entries other than this handoff pre-existed the session and were not modified here):

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
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/master_plan.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_2.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_3.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/planner/20260824_implementation_planner_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/planner/20260824_mechanism_inventory_round_1.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/reviewer/20260824_plan_1_projection_round_0.md
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/reviewer/20260824_plan_1_projection_round_1.md
?? docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md
```

L4 runs: 0; tests executed: 0.
