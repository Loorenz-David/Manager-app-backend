# Phase 8A implementer handoff

Date: 2026-09-21  
Phase: 8A — stock assignment match preview  
Agent: Codex  
Status: implemented; checkpoint pending reviewer approval

## Result

Implemented the MC-21 shared assignment-check evaluator, extracted the existing create-path inputs,
added the read-only match-preview service and route, and preserved create behavior. The preview
evaluates the same nine checks in MC-13 order, returns per-check results, reports advisory
assignment conflicts without blocking, and never writes an assignment.

## Evidence

The required before/after extraction gate was run against the unchanged plan-8 suite:

| run | command from \`app/\` | result |
|---|---|---|
| before extraction | \`PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py\` | \`42 passed in 5.55s\` |
| after extraction | same command | \`42 passed in 5.71s\` |

Targeted new/changed tests:

\`PYTHONPATH=. pytest tests/unit/domain/stock_report/test_stock_report_assignment_checks.py tests/integration/services/queries/stock_report/test_preview_stock_task_assignment_match.py tests/unit/routers/api_v1/test_stock_report_router.py\`

Result: \`49 passed in 3.99s\`.

The authoritative L4 was run once after implementation:

\`PYTHONPATH=. pytest -m 'not e2e' -q --disable-warnings --tb=short\`

Result: \`21 failed, 3575 passed, 1 skipped\`.

Pass arithmetic: baseline \`3547 passed\` + \`28\` new phase test cases (\`22\` preview integration,
\`1\` evaluator unit, \`5\` router cases) = \`3575 passed\`.

Failure-ID comparison against the published baseline:

\`\`\`
current - published baseline: ∅
published baseline - current: ∅
\`\`\`

The identical 21 IDs are the published set in
\`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md\` §3:
the seven bootstrap/items/upholstery/working-sections integration IDs, two audit-log IDs, two
dimension-migration IDs, the auth sign-in ID, worker-stats split ID, case-type serializer ID,
two item-router IDs, and the upholstery-inventory router ID. No new or missing failure ID was
observed.

The one skipped test is the pre-existing explicit cost-matrix measurement skip.

## Mutation ledger

Plan 8A declares \`10 named + 16 class-2 = 26\` mutations. Executed arithmetic is exactly:

\`\`\`
C1: 1 named (C1b) + 3 class-2 (C1a i–iii) = 4
C2: 1 named (C2b) + 1 class-2 (C2a) = 2
C3: 1 named (C3a) + 3 class-2 (C3b, C3c, C3d i–ii) = 4
C4: 0 named + 7 class-2 (C4a i–iii, C4b i–ii, C4c i–ii) = 7
C5: 1 named (C5a) + 1 class-2 (C5b) = 2
C6: 6 named (C6a–f) + 0 class-2 = 6
TOTAL: 10 named + 16 class-2 = 26 executed
\`\`\`

Twenty-five mutants were observed red and reverted. The sole exception was C1(a)(i), dropping
\`Task.is_deleted\` from the preview lookup: the shared evaluator independently checks
\`task.is_deleted\`, so this mutation is observationally equivalent in the current architecture,
not an unarmed row. The plan should either broaden that mutant to remove both guards or classify
it as equivalent.

C6(f) is withdrawn in the plan's §7 note, but its declared site was still probed as a proposed
backfill: removing the path \`client_id\` injection made the router assertion fail. The guard is
retained because the path-to-service mapping is otherwise silent.

The named mutations were: evaluator early return, planted preview insert, advisory-set removal,
pass-by-construction-set removal, each of the four preview role mutations, body
\`extra="forbid"\` removal, and path-client injection removal. The class-2 sites were the preview
lookup predicates, response key set, refusal-reason derivation, unresolved-item error branch,
transient quantity construction, request quantity/alternative validation, and task-id assumption
conditional. Each was applied only temporarily and reverted.

## Proposed backfills for the class-2 blank

The sites used for the 16 class-2 probes are the proposed backfill map:

- C1(a): preview task \`is_deleted\` lookup, preview item/primary-pair input, and preview
  \`item_not_task_primary\` input.
- C2(a): exact response-key assembly, including \`values_source\`.
- C3(b): \`refusal_reason\` derivation when an advisory failure is present.
- C3(c): unresolved-item branch before candidate construction.
- C3(d): transient candidate construction with and without the request quantity.
- C4(a): row existence, soft-delete, and workspace predicates.
- C4(b): required quantity declaration and the alternatives validator.
- C4(c): live-item and workspace predicates.
- C5(b): conditional application of \`PASS_BY_CONSTRUCTION_CHECKS\` only when \`task_id\` is absent.

C1(a)(i) is the equivalent mutation described above and needs the plan decision before it can be
made a genuinely independent guard mutation.

## Production write perimeter

Owned implementation files:

- \`app/beyo_manager/domain/stock_report/enums.py\`
- \`app/beyo_manager/domain/stock_report/assignment_checks.py\`
- \`app/beyo_manager/services/queries/stock_report/assignment_check_inputs.py\`
- \`app/beyo_manager/services/queries/stock_report/preview_stock_task_assignment_match.py\`
- \`app/beyo_manager/services/commands/stock_report/create_stock_task_assignments.py\`
- \`app/beyo_manager/routers/api_v1/stock_report.py\`
- \`.archgraph/architecture.yml\` — additive architecture delta for the preview endpoint and evaluator domain

Test files:

- \`app/tests/unit/domain/stock_report/test_stock_report_assignment_checks.py\`
- \`app/tests/integration/services/queries/stock_report/test_preview_stock_task_assignment_match.py\`
- \`app/tests/unit/routers/api_v1/test_stock_report_router.py\`

The plan Review log is appended separately. Plans 9 and 10 have unrelated active worktree edits and
were not staged or modified by this phase.

## Checks and architecture

- \`ruff check\` over the changed implementation and test files: passed.
- \`python3 -m compileall -q app/beyo_manager app/tests\`: passed.
- \`git diff --check\`: passed before checkpoint staging.
- Architecture Graph: valid; 230 nodes, 358 edges, no diagnostics; revision
  \`6df549d436ade66e8a2fb254455953f4b9161342b73b14054bd0d822f82155ed\`.
- The graph delta is additive and remains pending review under the workspace's review permission mode.

## Judgment calls and owner questions

- Stored item values win over supplied values when an identifier resolves; \`values_source\` makes
  that decision visible in the response.
- Unresolved identifiers are a normal preview outcome, not \`NotFound\`; item-dependent checks are
  \`not_evaluated\`, while property matching still uses supplied values.
- \`article_number\` and \`sku\` are strict alternatives; sending both is a validation error.
- The phase leaves create's behavior covered by the unchanged plan-8 suite rather than duplicating
  its nine-check criteria.

### ⚠ OWNER DECISIONS REQUIRED (2)

1. Accept or revise the C1(a)(i) mutation definition so the preview lookup guard is independently
   distinguishable from the evaluator's deletion guard.
2. Confirm whether the withdrawn C6(f) path-wiring guard should remain as a non-blocking regression
   test/backlog item or be removed from the implementation test file.

## Checkpoint

Checkpoint commit subject is \`CHECKPOINT (not approved): phase 8A match preview\`.
The SHA is recorded in the final response after commit. The owned phase paths are committed
explicitly; unrelated changes to plans 9 and 10 remain uncommitted and untouched.

