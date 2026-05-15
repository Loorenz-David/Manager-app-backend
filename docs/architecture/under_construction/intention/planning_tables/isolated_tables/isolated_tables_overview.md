# Isolated Tables Overview

Status: DRAFT - Shared Reference Layer
Domain: isolated_tables
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define the shared, workspace-scoped reference/configuration tables that do not belong naturally to one operational domain but are reused by multiple domain plans.

This layer is intentionally small and controlled. It exists for reusable reference data, not for runtime state, analytics projections, or hidden domain lifecycle ownership.

## 1) Layer purpose

Isolated/shared tables are allowed when they are:
- reused by multiple domains
- configuration or reference oriented
- stable across the application phase
- not naturally owned by one operational domain

Isolated/shared tables are not allowed to become:
- generic miscellaneous tables
- runtime authority containers
- lifecycle event stores
- analytics projections
- domain-specific history systems
- hidden business logic holders

If a table develops domain-specific lifecycle semantics, it should move into the owning domain planning folder.

## 2) Workspace boundary rules

- Shared reference tables are workspace-scoped unless a very strong future reason for global shared records is documented.
- workspace_id must be present, not null, and indexed on shared operational reference tables.
- workspace-specific configuration preserves operational autonomy.
- cross-workspace reuse is out of scope for this phase.
- a workspace must never read another workspace's shared reference rows through normal operational flows.
- client_id remains the stable API/database identifier; workspace_id remains the ownership boundary.

Workspace scope is preferred because shared costs and other operational references may legitimately differ between workspaces even when the table shape is reused globally.

## 3) Relationship rules

- Do not force every domain to FK directly to shared reference tables.
- Domains may reference shared records directly when the reference is current configuration lookup data.
- Historical or lifecycle records should snapshot the applied shared values instead of depending exclusively on mutable live rows.
- shared reference tables must not become hidden historical truth stores.
- a nullable reference FK is acceptable when a domain needs survivability during future catalog evolution or when the reference is optional by design.

## 4) Snapshot rules

When a domain applies a shared reference value to a historical or lifecycle record, the domain should snapshot the fields needed for replay and later reconstruction.

Snapshot policy:
- snapshot the applied shared name or label
- snapshot the applied monetary value when relevant
- snapshot the applied currency when relevant
- snapshot any classification or description needed for future reconstruction

Historical records must not depend exclusively on mutable live shared rows.

This preserves:
- historical correctness
- replay safety
- future correction compatibility

## 5) Mutability and history rules

- Shared configuration/reference tables may remain mutable.
- Changes should be auditable through updated_at / updated_by_id fields.
- Domain-specific historical accuracy must be preserved by snapshotting in the consuming domain.
- Do not introduce dedicated history tables here unless the phase explicitly requires reconstruction of shared-reference edits themselves.
- If history/versioning becomes necessary later, it should be introduced deliberately rather than by default.

## 6) Soft-delete rules

Shared reference tables should be soft-deleted, not hard-deleted.

Soft-delete expectations:
- soft-deleted shared rows are not available for new selection/use
- historical records that already snapshotted the shared row remain valid
- hard deletion is out of scope for normal operations
- soft delete must be consistent: is_deleted = false with deleted_at IS NOT NULL is invalid, and is_deleted = true with deleted_at IS NULL is invalid

Soft deletion preserves operational reconstruction and replay compatibility. It is not equivalent to irreversible destruction semantics.

## 7) Naming and prefix governance

- Each shared table must have an explicit prefix documented for client_id generation.
- Prefixes must not collide with existing planned prefixes.
- Prefixes should be short, traceable, and stable.
- Prefix documentation belongs in the owning table contract, not only in the overview.

Proposed shared-reference prefix map:
- scst -> static_costs
- cur -> currency_governance is not a table prefix in this phase because currency remains enum-governed

## 8) Static vs dynamic boundary

Shared tables are for reusable configuration/reference data.

They are not:
- runtime calculated values
- final invoiced values
- ledger authority
- payroll truth
- procurement authority
- inventory valuation truth
- analytics projections

When another domain needs historical accuracy, it should snapshot the shared reference values it used at the time.

## 9) Clarification questions before implementation

1. Should static_costs be workspace-scoped from day one?
2. Should static cost changes require dedicated history/versioning in phase one, or is updated_at/updated_by_id enough?
3. Should static costs be selectable globally by type/category later?
4. Should domains reference static_cost_id directly, or only snapshot applied values?
5. Is the bounded currency enum enough for this phase, or is a formal currency table required later?
