# Upholstery Inventory History Models Plan

Status: DRAFT - Initial Structured Split
Domain: upholstery_inventory_history
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define append-only inventory history lifecycle entities and snapshot anchors to guarantee replay-safe inventory reconstruction, operational correction compatibility, and audit durability.

## 1) Core table

### 1.1 upholstery_inventory_history_records

Columns:
- client_id: String(64) PK, prefix uih
- workspace_id: FK workspaces.client_id, not null, indexed
- upholstery_inventory_id: FK upholstery_inventory.client_id, not null, indexed
- event_type: Enum(upholstery_inventory_history_event_type), not null, indexed
- event_at: DateTime(tz), not null, indexed
- sequence_in_event_at: Integer, not null, default 0
- delta_stored_meters: Numeric(14,3), nullable
- delta_in_use_meters: Numeric(14,3), nullable
- delta_need_meters: Numeric(14,3), nullable
- delta_ordered_meters: Numeric(14,3), nullable
- snapshot_stored_meters: Numeric(14,3), nullable
- snapshot_in_use_meters: Numeric(14,3), nullable
- snapshot_need_meters: Numeric(14,3), nullable
- snapshot_ordered_meters: Numeric(14,3), nullable
- snapshot_total_used_meters: Numeric(14,3), nullable
- snapshot_total_inventory_used_meters: Numeric(14,3), nullable
- snapshot_total_surplus_used_meters: Numeric(14,3), nullable
- snapshot_total_surplus_meters: Numeric(14,3), nullable
- correlation_id: String(64), nullable
- source_entity_type: String(64), nullable
- source_entity_id: String(64), nullable
- reason: String(512), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, upholstery_inventory_id, event_at, sequence_in_event_at)
- CHECK(sequence_in_event_at >= 0)

## 2) Enums

### 2.1 upholstery_inventory_history_event_type
- INVENTORY_INITIALIZED
- INVENTORY_RECONCILED
- INVENTORY_ARCHIVED
- SNAPSHOT_BASELINE
- MANUAL_CORRECTION
- ORDER_PLACED
- ORDER_RECEIVED
- REQUIREMENT_ALLOCATED
- REQUIREMENT_RELEASED
- CONSUMPTION_RECORDED
- RECOMPUTE_ADJUSTMENT

Note: append-only lineage must remain extensible without destructive event mutation. Future-compatible optional extensions may later include PARTIAL_CONSUMPTION and MANUAL_IMPORT.

## 3) Ownership and semantics

Append-only semantics:
- history rows are append-only lifecycle entities.
- operational corrections append compensating history rows; they do not rewrite prior history.
- destructive mutation semantics are forbidden for normal operations.

MANUAL_CORRECTION governance:
- MANUAL_CORRECTION events represent policy-governed operational adjustments.
- corrections must preserve append-only replay compatibility, deterministic reconstruction, and historical lineage durability.
- corrections must occur through compensating lineage rather than destructive mutation, historical rewriting, or retroactive lifecycle replacement.

Replay and snapshot semantics:
- replay can be performed from full append-only history.
- snapshots optimize recomputation and rendering but do not replace append-only lineage.
- if snapshot and replay diverge, replay lineage is authoritative and snapshot reconciliation is required.
- delta_* fields represent incremental lifecycle mutations.
- snapshot_* fields represent reconstruction checkpoints that optimize replay workflows, projection rebuilding, reconciliation operations, and rendering reconstruction.
- snapshot persistence frequency is intentionally deferred.
- future implementations may vary between periodic checkpointing, reconciliation workflows, projection rebuild optimization, and operational replay acceleration.
- snapshot persistence policy must not be prematurely coupled into lifecycle authority semantics.

Audit semantics:
- history records are audit-compatible lifecycle evidence.
- correlation_id and source fields support cross-domain traceability without embedding runtime ownership authority.
- source_entity_type may later evolve into bounded governance enums once cross-domain lineage stabilization, orchestration governance, and replay-boundary contracts are formally established.

Idempotency compatibility semantics:
- correlation_id may later participate in idempotent replay safeguards, reconciliation protection, async deduplication, and webhook duplication protection without becoming authoritative lifecycle identity ownership.

Sequence ordering governance:
- sequence_in_event_at ordering should prefer deterministic domain-generated ordering semantics rather than relying exclusively on DB insertion ordering.
- this preserves replay consistency, distributed worker compatibility, deterministic recomputation, and stable lifecycle ordering.

RECOMPUTE_ADJUSTMENT semantics:
- RECOMPUTE_ADJUSTMENT represents reconciliation-layer corrective projection alignment only.
- it does NOT represent destructive mutation of historical lineage, retroactive lifecycle rewriting, or authoritative replacement of append-only history truth.
- append-only authority and replay-safe correction semantics must be preserved.
- RECOMPUTE_ADJUSTMENT events should originate only from controlled replay workflows, reconciliation jobs, deterministic rebuild operations, and operational correction pipelines.
- avoid arbitrary runtime mutation usage, direct user-edit correction semantics, and destructive lineage rewriting behavior.

Projection-drift philosophy:
- temporary divergence between projected aggregates and replay-derived lineage may occur during async reconciliation, delayed event propagation, distributed processing, and runtime rebuild workflows.
- this does NOT invalidate append-only lineage authority, replay correctness, or deterministic reconstruction semantics.
- replay-safe lineage remains authoritative during reconciliation workflows.

Replay scope boundaries:
- replay workflows are primarily authoritative for lifecycle reconstruction, operational projection rebuilding, replay-safe analytical regeneration, and inventory reconciliation.
- replay workflows are NOT intended for arbitrary uncontrolled cross-domain state regeneration.
- bounded replay authority and domain-governed lifecycle rebuilding must be preserved.

Sequence ordering scope:
- sequence_in_event_at ordering scope is relative to upholstery_inventory_id and event_at.
- this preserves deterministic replay ordering, distributed worker compatibility, and stable recomputation semantics.

## 4) Relationship map

- upholstery_inventory (1) -> (*) upholstery_inventory_history_records
- upholstery_orders (0..1) -> (*) upholstery_inventory_history_records via source_entity fields
- item_upholstery_requirements (0..1) -> (*) upholstery_inventory_history_records via source_entity fields

## 5) Scope boundary

In scope:
- append-only inventory history lifecycle events
- replay-safe snapshots and correction semantics
- audit-compatible operational traceability

Out of scope:
- runtime queue/worker execution internals
- warehouse movement orchestration state machine ownership
- analytics projection storage ownership

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- historical records should not be hard-deleted in normal operations.
- soft deletion of history should be exceptional and policy-governed.
- replay-safe reconstruction durability takes precedence over aggressive cleanup semantics.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.

## 7) Deferred runtime notes

- execution-level worker telemetry remains in runtime/observability entities.
- this table must not become a queue or lock state table.

## 8) Future integration notes

- canonical recompute jobs can rebuild inventory projections from append-only history.
- analytical projections should read from history/snapshots without mutating lifecycle truth.
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability.
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics.
- the upholstery domain architecture intentionally favors append-only lifecycle lineage, replay-compatible projections, rebuildable operational aggregates, and deterministic reconstruction workflows over irreversible mutable runtime-state authority.

## 9) Risks and protections

Risks:
- rewriting history rows and breaking replay determinism.
- using snapshot values as irreversible source of truth.

Protections:
- append-only lifecycle rule with compensating corrections.
- explicit replay-authoritative precedence rule.

## 10) Clarifications before implementation

1. Which event types are mandatory in phase one versus optional extension points?
2. Should sequence_in_event_at be generated by DB ordering policy or domain-level deterministic ordering?
3. Under what governance may history soft deletion ever be permitted, if at all?
