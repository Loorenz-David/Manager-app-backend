---
plan: plan_2
role: implement
round: 2
state: BLOCKED
date: 2026-08-25
actor: Codex
---

# Plan 2 implementation round 2 handoff — C19 continuation and checkpoint

The owner-authorized code continuation is complete, but Plan 2 is **not ready for independent
review** because the repository-wide stamp remains order-sensitive.
C19 now recognizes the planned budget-signal service as the third consumer of the single shared
allocator, serializer formatting churn has been removed, all focused evidence is green, and the
Architecture Graph delta is recorded. Two unchanged-tree full-suite runs produced different unrelated
additions rather than the required durable 21-ID set.

## ⚠ OWNER DECISIONS REQUIRED (1)

### OD-1 — stabilize the order-dependent baseline before checkpointing?

- **Question:** Should the coordinator authorize a separate test-stabilization cycle before Plan 2 closes?
- **Story:** The feature tests pass, but the full suite changes failures depending on which test file reaches an empty worker database first. That makes a clean release stamp a matter of scheduling luck rather than code quality.
- **Branches:** **Stabilize** — make the affected tests seed their own prerequisites and assert deterministic ordering; **Waive** — accept a checkpoint despite a non-empty, varying baseline delta.
- **Recommendation:** **Stabilize**, because a waiver would make later regressions indistinguishable from scheduling noise.
- **On silence:** Plan 2 stays `PROMPT_READY` and uncheckpointed.
- **Trace:** Closing L4 evidence; C10 ordering test; three `clock_in_code` fixture tests.

## Continuation outcome

- Amended only C19's exact allocator-consumer set, adding `get_task_budget_signals` beside
  `get_task_budget_allocations` and `get_task_production_time`. Its assertions against local
  `Fraction`, `ROUND_HALF_EVEN`, `largest`, and floor-division reimplementations remain intact,
  as does the one-exported-allocator assertion.
- Restored `division_serializers.py` to its pre-round-1 formatting everywhere outside the two
  new budget-signal serializer functions and their two `__all__` entries. The resulting tracked
  diff is additive-only for those four additions.
- Left `get_task_budget_signals.py` and `test_budget_signals_query.py` byte-identical to the
  round-1 handover, as required.

## Gate, contract, and coverage record

The intention header remained `RATIFIED`; Plan 1 was `APPROVED`; Plan 2 was `PROMPT_READY`;
and the Plan-2 Review log contained the 2026-08-25 owner authorization before the continuation
edit. Contract resolution did not change:

| Status | Authority | Continuation application |
|---|---|---|
| selected | `15_testing.md` | C19 remains a unit contract test at its existing mirrored location and asserts the exact closed set. |
| selected/local | `46_serialization.md` + `46_serialization_local.md` | The existing item-economics inline-serialization convention remains; this round only removes unrelated formatting churn. |
| selected | Master-plan M6 / §6.1 | The owner-approved C19 test file is now inside the phase-specific pre-existing-file perimeter. |
| excluded | Every other product, route, sibling service, integration-test, and contract file | No expansion beyond the bounded prompt occurred. |

Continuation Task 0 has one row:

| Obligation | Test ID | Assertion-shape assessment |
|---|---|---|
| C19 inherited consumer-set update | `tests/unit/services/queries/item_economics/test_production_time_contract.py::test_c19_division_has_one_allocator_and_services_only_consume_it` | Exact: equality on the three permitted importing services, followed by the unchanged anti-reimplementation loop and exact one-allocator export assertion. |

Before editing, C19 failed **1/1** with `get_task_budget_signals` as the sole extra set member.
That is both the honest continuation red baseline and proof that the closed-set guard can observe
the defect this amendment addresses. No new test was authored.

## Retained mutation evidence

The prompt explicitly forbade rerunning the round-1 mutation ledger. Its evidence remains valid:

- service SHA-256 stayed
  `41934cd4491ab259edf8f87e232f4ecc91ec3f99eba27065f49b2d5895aff453`;
- Plan-2 integration-test SHA-256 stayed
  `2d85889c60aefb910033236830dd365fbb1cba4583647bfc881eceb9c4fcb453`;
- neither additive budget-signal serializer function changed; only formatting in older sibling
  functions was restored.

Therefore all **18/18** named mutation rows and **2/2** exception-probe rows in the round-1
handoff survive this continuation. No mutation probe was applied in round 2, so its separate
probe-only file list is empty.

## Evidence

Pre-close dirty-tree identity: base `HEAD`
`bd83950355fc5f70806ad2a5971317a7815c6485`; tracked binary-diff SHA-256 before this handoff
was added `1c21884aca517a979148b1928273c1a1a2ee0b5d27ba87503d4d9b546b9930ac`.
Relevant closing file hashes:

- service: `41934cd4491ab259edf8f87e232f4ecc91ec3f99eba27065f49b2d5895aff453`;
- serializer: `bc1f56cc057317211a1298c2bac9387d754c6530fac29fffb7604cf6ce4ff577`;
- integration test: `2d85889c60aefb910033236830dd365fbb1cba4583647bfc881eceb9c4fcb453`;
- C19 contract test: `aa3e0d07c345b96d5598eb647028bce3f840d12cb4441c668ff2306c65ee1852`.

| Scope | Exact result |
|---|---|
| L1 red | C19 before amendment: **1 failed**, sole extra member `get_task_budget_signals`. |
| L1 C19 | Exact C19 node after amendment: **1 passed**. |
| L1 phase | `test_budget_signals_query.py`: **28 passed**. |
| L2 | Master-plan item-economics radius: **639 passed** in 7.33s. |
| Static | `ruff check` on the two round-2 changed app/test files: passed. `ruff format` was intentionally not run because the prompt requires the older sibling formatting to remain byte-identical. |
| L4 run 1 | `PYTHONPATH=. pytest -m 'not e2e'`: **22 failed / 2785 passed / 1 skipped**. Sole addition: `test_c10_batch_dedupes_specs_once_and_preserves_category_index`; removals `∅`. The ID set was captured before recovery. |
| L1 anomaly check | Exact C10 node: **1 passed** without a tree change. |
| L4 recovery | The charter-authorized anomalous-stamp recovery: **24 failed / 2783 passed / 1 skipped**. C10 was absent; additions were the three tests in `test_user_work_profile_clock_in_code.py`; removals `∅`. |
| L1 recovery check | `test_user_work_profile_clock_in_code.py`: **3 failed** because its helper found zero of the two workspaces it expects another test file to have seeded. This confirms order-dependent fixture coupling outside Plan 2. |

Redis answered `PONG` immediately before the first L4 run. The recovery run followed the
master-plan flaky-capture rule after the first extra ID was captured and passed alone. The
second, different anomaly means no authoritative empty-delta stamp exists for this cycle.

## Architecture graph

The architecture-graph skill influenced closeout by recording the independently named read
projection rather than treating the new service as only a file-level detail. Opening status was
valid at revision `344f99e481463b7753ebc56356222ed6c6fab2c6636e77fb66870b547b384db0`,
with 204 nodes, 308 edges, 6 stale nodes, and 3 pending review items in `review` permission
mode. Required searches and reads reused the allocation projection, allocation endpoint,
admin/manager money decision, Item Economics domain, task-step/evaluation/step-state sources,
live-worked-seconds projection, and allocator source-file anchor.

Duplicate preflight classified all seven candidates as new. One additive batch recorded:

1. projection `projection-item-economics-task-budget-signals`;
2. `domain-item-economics --contains-->` the projection;
3. four projection `--reads_from-->` edges to `table-task-step`,
   `table-item-cost-evaluation`, `projection-live-worked-seconds`, and
   `table-step-state-record`;
4. `source-file-item-economics-budget-division --implements-->` the projection.

All seven changes were applied, none skipped, with no diagnostics. Closing revision is
`d5d20c2521be7e37599a09bdd9c7315a849f5e9687f9f6f90171bc0a3fed4c31`: 205 nodes,
314 edges, 6 stale nodes, and 10 pending review items. No endpoint, source link, generated
context, maintenance item, or review decision was written. Exploration budget was depth 1,
one new node, and six new relationships; unresolved architecture is the intentionally deferred
phase-3 endpoint only.

## Full write perimeter

Round-2 cycle changes:

1. `app/tests/unit/services/queries/item_economics/test_production_time_contract.py` — C19 set only;
2. `app/beyo_manager/domain/item_economics/division_serializers.py` — formatting restoration only outside retained additive functions/exports;
3. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_2.md` — append-only round-2 Review-log entry;
4. this handoff;
5. Architecture Graph tool state — one projection node and six edges in
   `.archgraph/architecture.yml`.

Any later authorized checkpoint must also capture the uncommitted round-1 phase outputs: the
new service, new integration test, and round-1 implementer handoff, together with the
already-folded owner authority artifacts required to interpret them. Pre-existing graph/bootstrap edits,
`docs/archgraph-anchor-observations.md`, `remaining_production_pressure/`, worker-pressure
handoffs, and unrelated coordinator/reviewer queue artifacts remain outside this cycle and are
not attributed to it.

No checkpoint was made: the prompt requires acceptable closing evidence before the
`IMPLEMENTED` transition and checkpoint, and the full-suite failing-ID delta is not empty.

Next step after OD-1: the coordinator either dispatches a separately authorized stabilization
cycle and then a fresh Plan-2 close, or records an explicit baseline waiver. Until then the
implementation and additive graph delta are preserved, and Plan 2 remains `PROMPT_READY`.
