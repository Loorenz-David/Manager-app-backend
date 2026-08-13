---
plan: phase 4 (configuration services)
role: implementer
round: 1
date: 2026-08-12
state: IMPLEMENTED
verdict: CHECKPOINTED_NOT_APPROVED
actor: Codex
---

# Phase 4 implementer handoff

Implemented the manager-facing item-economics configuration surface and
checkpointed it at `98c75a8c6fa96d1e181f158721abb592bf9ff12a` with commit subject
`CHECKPOINT (not approved): item-cost phase 4 — configuration services`.

⚠ OWNER DECISIONS REQUIRED (0)

## Delivered

- Group CRUD, analytic section membership, soft deletion, audit events, and
  ADMIN/MANAGER role gates.
- Effective-dated production-cost basis and cost-model chains with admission
  rules, predecessor closure, canonicalize-then-derive rate persistence,
  complete replacement term sets, typed term validation, and registered
  index-name conflict translation.
- Locked, in-lock rechecked version deletion guards; the commands expose the
  planned optional `after_lock` awaitable seam for the concurrency harness.
- Pure `is_applicable` and explicit ordered configuration classification, status
  query, three workspace-scoped list queries with limit-plus-one pagination,
  query-layer serialization, and 13 registered FastAPI routes.
- Router-layer `percent_value` OpenAPI documentation and README mirror rows.
  Config commands deliberately emit no workspace events. No valuation,
  evaluation, result, item, or task reads were added.

## Plan comparison and judgment calls

The implementation follows the phase plan’s seven tasks and hard scope fences.
The only intentional decomposition choice is a shared command helper for
admission, index translation, workspace lookup, audit, and the delete seam.
The router accepts the smuggled `cost_per_worker_minute_minor` field with
`extra="ignore"`; it is never copied into persistence, and the stored value is
always the calculator result. Status `has_open_*` fields use the open-row
predicate (`effective_to IS NULL`), while classifier applicability remains the
registered half-open date predicate.

## Verification

- `ruff check` on all phase production and test paths: passed.
- `python3 -m compileall -q beyo_manager`: passed.
- Phase-focused suites: 72 passed.
- Router surface probe: 13 routes registered; all configuration routes retain
  ADMIN/MANAGER gates; `percent_value` metadata contains the planning-allocation,
  never-legally-payable-tax, and 25%-to-20.00 wording; no term mutation route.
- Full non-E2E suite: 1755 passed, 23 failed, 1 deselected, 2 warnings. The 23
  failures are the established baseline set; no new failure appeared. The
  baseline before this phase was 1749 passed, 23 failed, 1 deselected.

## Mutation ledger

Observed node IDs below are the architecture-graph anchors for the mutated
implementation sites. Every applied mutation was reverted and the worktree was
clean before the checkpoint.

| Criterion | Mutation and observed result | Observed node ID |
|---|---|---|
| C1 | Removed `is_deleted = false` from the open-basis lookup. The soft-deleted-open-row test failed with the required-effective-from error; restored. | `command-item-economics-create-production-cost-basis-version` |
| C4 | Changed request canonicalization to return the unquantized parsed Decimal. The canonical request and persisted-rate tests failed (`173.456`/raw `12.0107` instead of `173.46`/`12.0105`); restored. | `command-item-economics-create-production-cost-basis-version` |
| C5 | Replaced index discrimination with a blanket model-version conflict. The registered term-name identity assertion failed; restored. Unknown `IntegrityError` re-raise is also directly asserted. | `command-item-economics-create-cost-model-version` |
| C8 | Structural source probe confirms precedence is the explicit `CONFIGURATION_FAILURE_PRECEDENCE` tuple and the classifier does not iterate `EconomicsStatusEnum`. | `domain-item-economics` |
| C11 | Removed `MANAGER` from one route allow-list. The 13-route role-gate count probe failed; restored. | `endpoint-item-economics-post-cost-groups` |
| C6(a)/(b) | The two required lock/recheck mutations were not executed against genuinely concurrent sessions in this implementer session; the production code contains `FOR UPDATE`, the in-lock reference query, and the injectable seam for the reviewer harness. | `command-item-economics-delete-production-cost-basis-version`; `command-item-economics-delete-cost-model-version` |

## Architecture Graph delta

One batched additive `archgraph_apply_changes` call was recorded after the
final implementation checks, using the phase-2 table anchors and
`domain-item-economics`. It added 9 inferred command nodes, 13 inferred
endpoint nodes, and 25 inferred relationships. No human-confirmed node was
promoted, edited, rejected, or removed.

Graph revision after the batch:
`bf6dad5b9264937b5950366affe9910dcaacf7abd68a42114bb52fa327e68262`.

Command node IDs:

`command-item-economics-create-production-cost-group`,
`command-item-economics-update-production-cost-group`,
`command-item-economics-delete-production-cost-group`,
`command-item-economics-add-section-to-cost-group`,
`command-item-economics-remove-section-from-cost-group`,
`command-item-economics-create-production-cost-basis-version`,
`command-item-economics-delete-production-cost-basis-version`,
`command-item-economics-create-cost-model-version`,
`command-item-economics-delete-cost-model-version`.

Endpoint node IDs:

`endpoint-item-economics-post-cost-groups`,
`endpoint-item-economics-get-cost-groups`,
`endpoint-item-economics-patch-cost-group`,
`endpoint-item-economics-delete-cost-group`,
`endpoint-item-economics-post-section`,
`endpoint-item-economics-delete-section`,
`endpoint-item-economics-post-basis`,
`endpoint-item-economics-get-basis`,
`endpoint-item-economics-delete-basis`,
`endpoint-item-economics-post-model`,
`endpoint-item-economics-get-model`,
`endpoint-item-economics-delete-model`,
`endpoint-item-economics-status`.

## Full write perimeter and checkpoint

The checkpoint includes the phase production modules under
`app/beyo_manager/domain/item_economics/`,
`app/beyo_manager/services/commands/item_economics/`,
`app/beyo_manager/services/queries/item_economics/`, the new router and its
registration, router README rows, the phase tests, the phase tracker row and
Review log, and `.archgraph/architecture.yml` containing the additive graph
delta. It does not include unrelated worktree files.

Final checkpoint commit:

`98c75a8c6fa96d1e181f158721abb592bf9ff12a`

This handoff is deposited after that checkpoint; the handoff file itself is the
only post-checkpoint artifact.
