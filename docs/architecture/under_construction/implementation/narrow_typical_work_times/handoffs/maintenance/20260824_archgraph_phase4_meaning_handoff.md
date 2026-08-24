---
plan: plan_4
role: maintenance
round: 1
date: 2026-08-24
actor: Codex
authorization: D30
---

# Phase 4 architecture-graph meaning handoff

## Description rewrites

### `projection-item-economics-task-production-time`

Before:

> The task-scoped, read-only production-time view that composes manager budget status with section grouping, section typicals, and deterministic per-step time allowances. Its worked-seconds basis is each non-deleted step's settled working seconds plus the concurrency-averaged share of any open WORKING interval, resolved once per request through the shared live worked-seconds loader and passed both to budget status and into the allocator's response-only step rows, persisted nowhere. It includes ordered section rows and a flat time-only final snapshot without monetary fields, persisted calculation results, or schema changes. It preserves the existing budget-status readiness and tenant boundary while exposing section metadata and live state snapshots.

After:

> The task-scoped, read-only production-time view composes manager budget status with active PRIMARY-item category-narrowed typical-time evidence, ordered section grouping, and deterministic per-step time allowances. For each task it derives the typical filter from the active PRIMARY item's category and reconciles participating sections through uniform_basis_v1: usable narrowed evidence must be available for every participating section to select one item-narrowed basis, otherwise the participating task falls back together to section-wide, while excluded sections resolve independently. The same SelectedTypical values feed both the displayed typicals and the division weights, and the response carries a typical_resolution block with the task basis, applied filter, participating-section counts by basis, reconciliation method, and comparability profile, plus per-section typical_basis, narrowed_sample_count, and section_sample_count and allocation_method static_proportional_section_v2. Each non-deleted step's worked-seconds input remains its settled working seconds plus the concurrency-averaged share of any open WORKING interval, resolved once per request through the shared live-worked-seconds loader and persisted nowhere. It preserves the tenant boundary and time-only shape, including ordered section rows and a flat final snapshot, and does not expose monetary fields, persist derived results, or change the underlying working-sections typical-times projection.

### `projection-item-economics-task-budget-allocations`

Before:

> The batched, read-only task view that combines current committed evaluation budgets, non-deleted live steps, section typicals, and item-economics readiness into per-step allowances. Each step's worked-seconds input is its settled working seconds plus the concurrency-averaged share of any open WORKING interval, taken from one shared live worked-seconds map loaded once per request and persisted nowhere. It omits unknown or cross-workspace tasks, charges non-deleted excluded steps, and degrades evaluation-less tasks to explicit no-budget states without persisting derived values. Its invariant is that the response's time-only fields reconcile with the same non-deleted step set used by budget status.

After:

> The batched, read-only task view combines current committed evaluation budgets, non-deleted live steps, item-category-narrowed typical-time evidence, and item-economics readiness into per-step allowances. It derives one filter spec per task, deduplicates equal specs into an ordered sequence, issues one typical-times statement for the batch, and maps each task to its spec position; a non-narrowing task uses spec_index None and resolves against the spec-independent section-wide columns. Participating sections are reconciled through uniform_basis_v1 and excluded sections resolve independently, so one task-wide basis governs the selected typicals used both for displayed step values and for division weights; the response exposes typical_resolution, per-step typical_basis and sample_count, and allocation_method static_proportional_section_v2. Each step's worked-seconds input remains its settled working seconds plus the concurrency-averaged share of any open WORKING interval, taken from one shared live-worked-seconds map loaded once per request and persisted nowhere. It omits unknown or cross-workspace tasks, charges non-deleted excluded steps, and degrades evaluation-less tasks to explicit no-budget states without persisting derived values; its time-only fields reconcile with the same non-deleted step set used by budget status.

## Pending review adjudication

I chose **reject, re-record span-free, then approve**. The content was sound, but both original evidence entries carried `startLine`/`endLine` despite also carrying symbols; because evidence summaries are immutable, reject-and-re-record is the only way to preserve the claims without writing policy-violating spans. This also avoids recreating the exact stale-span condition that caused the prior D28/D29 rejection.

The implementation and test evidence were verified in:

- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py :: typical_times_statement`
- `app/tests/integration/services/queries/working_sections/test_typical_times_narrowing.py :: test_cardinality_is_section_cross_spec_total_and_history_less_sections_are_materialized`

Preview diff for the rejection:

```text
reject: node:source-symbol-working-section-typical-times-statement-narrowing
removedIncidentEdgeIds: []
warnings: []
```

Preview diff for the corrected approval:

```text
promote: node:source-symbol-working-section-typical-times-statement-narrowing
from: ai_inferred
to: human_confirmed
reject/edit/deprecate/investigate: []
warnings: []
```

## Evidence and status

This session wrote **2 evidence entries; 0 carry spans**. The final node inspection confirmed both entries retain only `path` + `symbol`.

Status before writes:

```text
initialized=true, valid=true
nodes=198, edges=298
pending=1, stale=5, diagnostics=[]
revision=0196645b90b22bd172810b5f4458b1d155ea0fc06552b16552d3931dcd7db9f2
permissionMode=review, allowMaintenance=true, allowAnchorRepair=true
```

Status after writes:

```text
initialized=true, valid=true
nodes=198, edges=298
pending=0, stale=5, diagnostics=[]
revision=a055b5ce3a03e9670fc66609f43bea34ef3c7cb115795f1ed6bcbae07930fc79
permissionMode=review, allowMaintenance=true, allowAnchorRepair=true
```

## Write perimeter and recorded state

The settled-graph maintenance batch edited only the two authorized projection descriptions. Its tool record is `.archgraph/changes/2026-08-24T07-41-29-762Z--e10a44.yml`; both edits were client-approved under D30.

The review perimeter was only `node:source-symbol-working-section-typical-times-statement-narrowing`: one reject, one same-id span-free re-record with two evidence entries, and one promote. The additive re-record was applied at revision `e3a2d0669e7f87d1dfe58ac300c70d800e45947e3c8208031c47adad73e25f71`. The reject record is `.archgraph/reviews/2026-08-24T07-41-39-758Z--7a09a9.yml`; the approval record is `.archgraph/reviews/2026-08-24T07-41-56-303Z--6d086b.yml`. No other node, edge, source link, stale link, or evidence entry was changed. No application file was edited, and no test suite was run, as required by the prompt.

## Not acted on

- The five pre-existing stale nodes and the four stale source links on the production-time projection were left untouched; D30 explicitly identifies those as content-hash drift, not repair candidates.
- D29's three deferred operations were not enacted.
- `.archgraph/backfill/` was not touched; it remains the owner's work.
- `git status --porcelain -- app/` was not empty at verification: it showed existing modifications in `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`, `app/tests/unit/domain/item_economics/test_budget_division.py`, and `app/tests/unit/domain/item_economics/test_domain_purity.py`. This session did not modify those files.
- No plan file or tracker was updated.
