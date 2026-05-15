# Upholstery Inventory Models Plan

Status: DRAFT - Initial Structured Split
Domain: upholstery_inventory_planning
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define upholstery inventory planning and projection semantics while preserving strict separation from warehouse execution runtime, reservation engines, and procurement orchestrator ownership.
Formalize threshold-policy governance as a dedicated interpretation layer that remains replay-compatible, deterministic, and non-authoritative relative to append-only lifecycle lineage.

## 1) Core table

### 1.1 upholstery_inventory

Columns:
- client_id: String(64) PK, prefix uin
- workspace_id: FK workspaces.client_id, not null, indexed
- upholstery_id: FK upholsteries.client_id, not null, indexed
- minimum_to_have: Integer, nullable
- maximum_to_have: Integer, nullable
- projected_inventory_value_minor: Integer, nullable
- currency: Enum(upholstery_currency_enum), nullable
- planning_position: String(255), nullable
- inventory_condition: Enum(upholstery_inventory_condition), not null, indexed
- current_stored_amount_meters: Numeric(14,3), nullable
- current_amount_in_use_meters: Numeric(14,3), nullable
- current_amount_in_need_meters: Numeric(14,3), nullable
- current_amount_ordered_meters: Numeric(14,3), nullable
- total_upholstery_used_meters: Numeric(14,3), nullable
- total_upholstery_used_inventory_meters: Numeric(14,3), nullable
- total_upholstery_used_surplus_meters: Numeric(14,3), nullable
- total_upholstery_surplus_meters: Numeric(14,3), nullable
- latest_projection_history_id: FK upholstery_inventory_history_records.client_id, nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, upholstery_id)
- CHECK(minimum_to_have IS NULL OR minimum_to_have >= 0)
- CHECK(maximum_to_have IS NULL OR maximum_to_have >= 0)
- CHECK(maximum_to_have IS NULL OR minimum_to_have IS NULL OR maximum_to_have >= minimum_to_have)
- CHECK(projected_inventory_value_minor IS NULL OR projected_inventory_value_minor >= 0)

### 1.2 upholstery_inventory_threshold_policies

Columns:
- client_id: String(64) PK, prefix utp
- workspace_id: FK workspaces.client_id, not null, indexed
- scope: Enum(threshold_policy_scope), not null, indexed
- upholstery_id: FK upholsteries.client_id, nullable, indexed
- low_stock_minimum_meters: Numeric(14,3), nullable
- low_stock_ratio: Numeric(8,4), nullable
- out_of_stock_epsilon_meters: Numeric(14,3), nullable
- escalation_policy: Enum(sourcing_escalation_policy), nullable
- warning_tier: Enum(inventory_warning_tier), nullable
- effective_from: DateTime(tz), nullable
- effective_to: DateTime(tz), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, scope, upholstery_id, effective_from)
- CHECK(low_stock_minimum_meters IS NULL OR low_stock_minimum_meters >= 0)
- CHECK(low_stock_ratio IS NULL OR (low_stock_ratio >= 0 AND low_stock_ratio <= 1))
- CHECK(out_of_stock_epsilon_meters IS NULL OR out_of_stock_epsilon_meters >= 0)
- CHECK(effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from)
- CHECK(scope != 'UPHOLSTERY' OR upholstery_id IS NOT NULL)

## 2) Enums

### 2.1 upholstery_inventory_condition (synthesized projection field)
- AVAILABLE
- LOW_STOCK
- OUT_OF_STOCK

Semantics:
- AVAILABLE: projected operational inventory sufficiently satisfies current known need.
- LOW_STOCK: inventory remains operationally available but projected thresholds indicate approaching shortage risk. LOW_STOCK derives from threshold-policy evaluation against current projections and operational planning guidance.
- OUT_OF_STOCK: projected inventory availability is insufficient for current operational demand.

Note: inventory_condition is a synthesized operational visibility projection. It derives from projected inventory quantities, projected operational demand, threshold policies, and sourcing projections. Domain-derived deterministic projection behavior is preferred over arbitrary manual mutation. Nuanced operational semantics between AVAILABLE and OUT_OF_STOCK should derive from threshold-policy systems rather than proliferating visibility states. inventory_condition resolution must follow deterministic domain-defined precedence ordering; example: OUT_OF_STOCK precedence overrides LOW_STOCK when both threshold conditions are simultaneously satisfied.

### 2.2 upholstery_currency_enum (bounded governance, this phase)
- SWEDISH_KRONA
- DANISH_KRONA
- EURO

Note: bounded currency governance applies to current operational scope. Future monetary infrastructure may evolve independently.

### 2.3 threshold_policy_scope
- WORKSPACE_DEFAULT
- UPHOLSTERY

### 2.4 sourcing_escalation_policy
- NONE
- RECOMMEND_REORDER
- ESCALATE_TO_PROCUREMENT

### 2.5 inventory_warning_tier
- NORMAL
- LOW_STOCK_WARNING
- URGENT_REORDER

Note: future threshold-policy extensions may introduce additional warning tiers and critical inventory interpretation layers without forcing premature expansion of inventory_condition visibility states.

## 3) Ownership and semantics

Inventory planning semantics:
- upholstery_inventory rows represent planning/projection-oriented inventory state.
- these rows are not authoritative warehouse movement execution logs.
- these rows are not reservation lock authority or procurement orchestrator runtime state.
- upholstery_inventory behaves as a replay-compatible operational aggregate projection derived from append-only lifecycle history semantics.

Quantity semantics:
- current_* and total_* quantity fields represent operational projections at the current reconstruction scope.
- these fields are recomputable, reconcilable, and replay-compatible.
- they are NOT authoritative warehouse-runtime truth, immutable operational counters, or movement-runtime ownership.
- historical replay correctness and recomputation compatibility take priority over denormalized shortcut optimization.
- append-only lineage remains authoritative over projected aggregates.
- total_upholstery_used_meters, total_upholstery_used_inventory_meters, total_upholstery_used_surplus_meters, and total_upholstery_surplus_meters are replay-compatible aggregate projections derived from lifecycle lineage.
- where authoritative historical lineage exists, these total_* fields remain recomputable, replay-compatible, and reconstruction-safe.
- do not interpret total_* fields as irreversible immutable counters.

Valuation semantics:
- projected_inventory_value_minor represents operational planning/reference valuation semantics only.
- it is NOT authoritative accounting valuation truth, finalized inventory costing, immutable financial ledger value, or accounting-book ownership.
- currency on upholstery_inventory represents current operational planning/reference valuation context only.
- it is NOT authoritative accounting valuation currency, immutable procurement costing truth, or financial ledger ownership.
- future procurement history may involve mixed sourcing currencies and evolving procurement valuation semantics.
- historical procurement replay must derive from lifecycle snapshots and sourcing history entities.

Projection-update ownership semantics:
- projected quantity fields such as current_stored_amount_meters, current_amount_in_use_meters, current_amount_in_need_meters, and current_amount_ordered_meters are domain-maintained operational projections.
- these values evolve through lifecycle actions including requirements, sourcing events, order lifecycle changes, inventory reconciliation, and operational corrections.
- append-only inventory history lineage remains authoritative over projected aggregates during reconciliation workflows.

Append-only lineage authority:
- projected aggregate rows are recomputable, reconcilable, and non-authoritative relative to append-only lineage.
- replay determinism, reconstruction durability, and reconciliation compatibility must be preserved.
- if projected aggregate values diverge from append-only history reconstruction, append-only lineage takes precedence.
- latest_projection_history_id is convenience/projection linkage only; lifecycle replay must not depend exclusively on latest-reference shortcuts.

Inventory condition semantics:
- inventory_condition is a synthesized operational visibility projection derived from projected inventory quantities, demand, and threshold policies.
- inventory_condition may be physically persisted as an operational projection optimization while remaining logically derivable from authoritative projection inputs, threshold-policy evaluation, and replay-compatible lifecycle semantics.
- inventory_condition should prefer deterministic domain-derived projection behavior rather than arbitrary manual mutation.
- inventory_condition resolution must follow deterministic domain-defined precedence ordering to preserve replay consistency, deterministic recomputation, and stable analytical reconstruction.
- procurement lifecycle progression belongs exclusively to upholstery_orders and sourcing lifecycle entities.
- states such as ORDERED, APPROVED, RECEIVED, and FAILED represent procurement lifecycle semantics, not inventory visibility semantics.
- strict separation between inventory projections and procurement lifecycle ownership must be preserved.

Threshold-policy layer semantics:
- upholstery_inventory_threshold_policies represent evaluation/governance layers only.
- threshold-policy rows are not inventory ownership rows, warehouse runtime authority, reservation engines, movement execution systems, or procurement lifecycle authority.
- threshold-policy systems govern operational warning visibility, low-stock semantics, sourcing recommendation behavior, escalation guidance, and operational inventory interpretation.
- threshold-policy systems do not become authoritative inventory lineage, warehouse execution truth, or inventory movement authority.
- threshold-policy evaluation is workspace-scoped; different workspaces may define different low-stock tolerance, sourcing escalation rules, inventory-warning sensitivity, and reorder guidance.
- inventory_condition remains synthesized operational projection visibility while threshold-policy systems participate in evaluation logic, condition interpretation, and warning escalation semantics.
- threshold-policy rows do not replace inventory projections, append-only lineage, or lifecycle reconstruction authority.

Deterministic evaluation semantics:
- threshold-policy evaluation must remain deterministic and replay-compatible.
- inventory_condition derivation must produce stable outcomes when replaying identical projection inputs, identical threshold policies, and identical lifecycle lineage.
- this preserves deterministic replay, stable analytical reconstruction, and projection rebuild compatibility.

Partial availability philosophy:
- partial operational fulfillment semantics should derive from projected quantity calculations, requirement lifecycle interpretation, and threshold-policy evaluation rather than dedicated inventory visibility states during this planning phase.
- avoid prematurely proliferating inventory-condition enums before dedicated warehouse/runtime systems exist.

Threshold semantics:
- minimum_to_have and maximum_to_have represent operational planning guidance only.
- they are not hard reservation guarantees, warehouse execution truth, or immutable inventory constraints.
- threshold policies participate in inventory_condition derivation, sourcing recommendations, and planning visibility projections, not authoritative warehouse runtime enforcement.
- threshold-policy evaluation is workspace-scoped unless future global governance layers are formally introduced.
- future inventory threshold-policy entities may later define workspace-specific stock warning ranges, low-stock thresholds, sourcing escalation policies, operational inventory-warning tiers, and reorder recommendations.
- these threshold-policy systems should remain domain-governed, replay-compatible, and projection-oriented without collapsing warehouse-runtime authority into planning entities.
- future threshold-policy systems may later support warehouse-specific thresholds, location-specific thresholds, sourcing-region policies, and operational-zone inventory evaluation without invalidating replay-safe lineage, projection rebuild philosophy, or deterministic reconstruction semantics.

Future AI/prediction compatibility:
- future implementations may support projected consumption forecasting, seasonal inventory adjustments, supplier-delay risk projections, and AI-assisted sourcing recommendations.
- authoritative lifecycle mutation remains domain-governed.
- AI systems remain advisory and non-authoritative to preserve replay correctness, auditability, and deterministic operational governance.

Planning position semantics:
- planning_position is temporary planning-oriented operational metadata only.
- it is not authoritative warehouse-runtime positioning truth or historical movement reconstruction authority.
- future warehouse-runtime systems may introduce dedicated movement-history entities independently of planning_position.

## 4) Relationship map

- upholsteries (1) -> (0..1) upholstery_inventory
- upholstery_inventory (1) -> (*) upholstery_orders
- upholstery_inventory (1) -> (*) upholstery_inventory_history_records
- upholstery_inventory (1) -> (*) item_upholstery_requirements (future FK compatibility)
- workspaces (1) -> (*) upholstery_inventory_threshold_policies
- upholsteries (1) -> (*) upholstery_inventory_threshold_policies (when scope is UPHOLSTERY)

## 5) Scope boundary

In scope:
- inventory planning thresholds and projection fields
- sourcing readiness visibility semantics
- compatibility with order and requirement lifecycle entities
- threshold-policy governance and deterministic evaluation semantics

Out of scope:
- warehouse movement execution runtime
- reservation/lock orchestration engines
- accounting valuation authority
- analytics materialization ownership
- autonomous procurement execution authority

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- inventory projections should be reconstructable from historical entities where available.
- hard deletion of inventory rows with lifecycle dependencies is forbidden in normal operations.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.

## 7) Deferred runtime notes

- do not add movement transaction logs directly to inventory planning rows.
- do not add reservation lock fields or runtime conflict-resolution flags to this table.
- do not transform threshold-policy rows into hidden warehouse-runtime orchestration or autonomous ordering systems.

## 8) Future integration notes

- dedicated inventory runtime entities for movement, reservation, and reconciliation.
- inventory projection read models generated from lifecycle history and runtime events.
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability.
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics.
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics.
- future runtime systems may later segment inventory projections by warehouse, operational location, sourcing scope, and runtime reservation context without invalidating append-only replay semantics, projection rebuild philosophy, or historical reconstruction compatibility. Current planning intentionally preserves forward compatibility for future inventory segmentation systems.
- the upholstery domain architecture intentionally favors append-only lifecycle lineage, replay-compatible projections, rebuildable operational aggregates, and deterministic reconstruction workflows over irreversible mutable runtime-state authority.
- threshold-policy entities participate in operational interpretation, projection evaluation, and sourcing recommendation visibility while append-only lifecycle lineage remains authoritative for historical reconstruction.

## 9) Risks and protections

Risks:
- treating projected counters as irreversible runtime truth.
- embedding reservation/warehouse runtime authority into planning rows.
- allowing threshold-policy rows to drift into hidden runtime orchestration authority.

Protections:
- explicit recompute/replay-first semantics.
- deferred runtime separation contract.
- deterministic, workspace-scoped threshold-policy governance with replay compatibility.

## 10) Clarifications before implementation

1. Should inventory rows allow multiple concurrent planning contexts per upholstery (for example by location), or remain single-row-per-upholstery in this phase?
2. Which quantity fields are required snapshots versus fully derivable projections in the first implementation phase?
3. Should projected_inventory_value_minor remain optional for all inventory rows, or become required for selected workspace policies?
4. Should WORKSPACE_DEFAULT and UPHOLSTERY-scoped threshold policies use strict precedence (UPHOLSTERY override first) in this phase?
