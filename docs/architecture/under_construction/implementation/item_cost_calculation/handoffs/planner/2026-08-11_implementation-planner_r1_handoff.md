---
plan: master (implementation-planner)
role: planner
round: 1
date: 2026-08-11
state: COMPLETE — master plan + 9 phase plans written; tracker all NOT_STARTED
verdict: PLANNED — hand to pipeline-coordinator
actor: Claude (implementation-planner doctrine, /Users/davidloorenz/agent-skills/implementation-planner.md)
---

# Implementation-planner handoff — item_cost_calculation, round 1

Gate check passed before work: intention header `round 4, resolved — mechanism gate
PASSED`; §17 EMPTY with exit gate PASSED; `owner_decisions.md` CLOSED with both
mechanism-gate cards answered and folded (R4-1, R4-2); no master plan existed and
`plans/` was empty.

The plan set is written: **`master_plan.md`** at the project root (goal, sources of
truth, workflow, tracker, contract resolution, naming registry, sequencing, tool
protocols, standing rules, verified environment topology, only-if-cheap ledger) and
**nine phase plans** in `plans/` (goal + explicit not-in-phase, read-first by
reference, dependencies, files, ordered tasks, enumerated criteria with named
mutations, empty Review logs). Round-4 constraints honored: only §8A.5 **branch A**
is planned (branch B appears nowhere as work); the R4-2 presentation rule is a task
+ criterion in phase 4 (API field docs) and phase 9 (living docs), and a standing
rule (master plan P-D). Sequencing puts the worker money redaction **first** (no
schema dependency; closes the live leak earliest) and the legacy migration **after**
the valuation surface (replacement before removal); the §10A.3 bridge-validator
removal is explicitly out of scope and recorded as a follow-up ledger item.

Registry decisions of note: **`cmvt` replaces the intention's proposed `cmt` prefix**
(collides with `ContentMention | cmt` in `client_id_prefix_map.md`); error
identities travel as the leading token of `DomainError.message` (the implementation
has no `code` field — see coordinator item 1); currency columns reuse the
`ItemCurrencyEnum` Python class with three per-table PG types; the evaluation's
episode snapshots reuse `business_task_type_enum` / `task_return_source_enum` with
`create_type=False` (type ownership pinned, R2-1 lesson).

## ⚠ OWNER DECISIONS REQUIRED (0)

None — nothing in this planning round needed an owner call; the round-4 answers
covered every branch the plans build.

## Phase table

| # | Goal (one line) | Projection gate | Depends on |
|---|---|---|---|
| 1 | Close the `total_cost_minor` WORKER/SELLER leak via fail-closed `serialize_step(include_monetary)` across the five-site census | **MANDATORY** (inventory row 33) | — |
| 2 | Nine item-economics tables + enums + constraints + schema migration | **MANDATORY** (rows 1,3,8,11,12,15 DDL side) | 1 |
| 3 | The pure canonical calculator (§6A entire, `CALCULATION_VERSION`, `rederive`) | **MANDATORY** (rows 1–14) | 2 |
| 4 | Config surface: groups/membership, both version chains + races, guarded deletes, §7A.5 classifier, config status | **MANDATORY** (rows 15–20) | 3 |
| 5 | Valuation surface: chain command + race, validation, history, ephemeral preview | **MANDATORY** (rows 15–16 valuation chain, 34) | 4 |
| 6 | Legacy money migration: journal + P1/P2 pre-flight, API bridge (reject-iff-non-NULL), column drop | **MANDATORY** (rows 31–32) | 5 |
| 7 | Evaluations: §7B commit tx, mirror rule, projections + promotion, auto path | **MANDATORY** (rows 2,5,7,10,14,16,17,19,21–25) | 6 |
| 8 | Status & results: §8A.6 status (+ worker variant), §8A.3 handler, terminal emissions, §8A.5 branch-A re-emit | **MANDATORY** (rows 9,26–30,34) | 7 |
| 9 | Living docs + §2.6/D-1…D-4 drift landing spots | waivable (docs only; waiver recorded in plan) | 8 |

## Probe results

**P-1 (count reconciliation): verified — the table wins.** All **34** inventory-table
rows' "where written" citations resolve to real sections of the intention (§4A
A1–A8, §6A.2–6A.11, §7A.1–7A.6, §7B.1–7B.5, §8A.1–8A.6, §10A.1–10A.3,
§11A.1–11A.4 — each checked against the round-4 document during the full read).
The prose claim of "31 load-bearing mechanisms" matches no derivable partition of
the artifacts (the handoff separately lists 4 mechanisms as already contract-grade,
which would give 34 + 4 = 38 inspected); I treat "31" as a prose miscount with no
downstream effect. **Reconciled count: 34 contract-bearing inventory rows**, and the
phase plans' criteria and projection-gate flags are built over those 34 rows.

**P-2 (inherited citation): now verified first-hand.** The frontend repo was
readable from this session:
`frontend/packages/tasks/src/actions/use-create-task.ts:84-86` sends
`item_value_minor: null, item_cost_minor: null` on every task creation, plus an
`item_currency` passthrough that is null in production flows (the currency field
mounts only in the dev harness — research §5). The phase-6 criteria are nonetheless
planned strictly from §10A.3's predicate (reject iff present-AND-non-NULL), which
holds independent of the citation; the citation's verification is recorded in the
phase-6 notes as the bridge's risk rationale (present-null must pass).

## Could not plan without an owner call

Nothing. Two items were resolvable by planner authority and are recorded as such:
the `cmt` prefix collision (registry decision) and the error-identity carrier
(registry decision §6.4, valid under either resolution of coordinator item 1).

## Coordinator items (not owner decisions)

1. **Contract gap:** canonical `05_errors.md` specifies `code: str` on `DomainError`
   subclasses; `app/beyo_manager/errors/*` implements only `message` + `http_status`
   and no `05_errors_local.md` records the divergence. Route with the §2.6 batch.
2. **Application_contracts scope:** phase 9 lands §2.6-4 / §10.2 doc entries in
   `/Users/davidloorenz/Desktop/Developer/Application_contracts` — a separate
   working directory; confirm scope when compiling that prompt or reroute as a
   maintenance item.
3. **D-3 anchor drift** (`analytics-recompute-step-time-totals`, span 138–211 vs
   symbol 161–234 — re-confirmed this session) remains for the human-authorized
   maintenance channel; no pipeline session repairs it in passing (master plan §8).
4. **Follow-up ledger** (master plan §7/§11): bridge-validator removal ships in the
   release after the frontend stops sending the keys; only-if-cheap items await your
   prompt-time pickup; §2.6-5 dead-code list stays out of scope.
5. **Suite baseline:** the planner verified collection only (1602 tests, 1.72s,
   `PYTHONPATH=.` required — Makefile's bare `pytest` invocation fails at conftest
   import). The phase-1 implementer records the full-suite baseline in its Review
   log before first change.

## Session write perimeter (full)

| Path | Change |
|---|---|
| `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md` | new |
| `…/item_cost_calculation/plans/phase_1_worker_money_redaction.md` | new |
| `…/item_cost_calculation/plans/phase_2_schema_models.md` | new |
| `…/item_cost_calculation/plans/phase_3_canonical_calculator.md` | new |
| `…/item_cost_calculation/plans/phase_4_configuration_services.md` | new |
| `…/item_cost_calculation/plans/phase_5_valuation_surface.md` | new |
| `…/item_cost_calculation/plans/phase_6_legacy_migration_api_bridge.md` | new |
| `…/item_cost_calculation/plans/phase_7_evaluations.md` | new |
| `…/item_cost_calculation/plans/phase_8_status_results.md` | new |
| `…/item_cost_calculation/plans/phase_9_docs_and_drift.md` | new |
| `…/item_cost_calculation/handoffs/planner/2026-08-11_implementation-planner_r1_handoff.md` | this file (new) |

**Nothing else.** No code, no migrations, no edits to `planning/` (intention,
research context, owner decisions, raw intention untouched), no prompt files.
Tool-recorded state: **no archgraph write of any kind** — `archgraph_status` and
seven `archgraph_get_node` reads only (state re-verified: 116 nodes / 157 edges,
revision `b0702c3c…`, 0 stale, 244 pending, `review` mode); no review adjudicated.
No git operation. Repo commands run were read-only (`ls`/`find`/`grep`/`cat`) plus
`PYTHONPATH=. pytest --collect-only -q` (no test executed, nothing written).

## Exit

Per doctrine: plan set written; tracker all NOT_STARTED; hand to
**pipeline-coordinator**. First action for the coordinator: run the projection gate
(round 0) for phase 1, then compile the phase-1 implementer prompt from
`plans/phase_1_worker_money_redaction.md`.
