# Static Cost Models Plan

Status: DRAFT - Shared Reference Table
Domain: isolated_tables
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define a reusable operational cost reference table for values that are shared across multiple domains but do not belong naturally to a single operational domain.

Static costs are configuration/reference records. They are not ledger entries, payroll truth, procurement authority, or final invoiced cost records.

## 1) Core table

### 1.1 static_costs

Suggested columns:
- client_id: String(64) PK, prefix scst
- workspace_id: FK workspaces.client_id, not null, indexed
- name: String(255), not null
- description: String(1024), nullable
- cost_minor: Integer, not null
- currency: Enum(currency_enum), not null
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Optional future-only fields should not be added unless a concrete cross-domain reuse requirement appears.

## 2) Cost semantics

- cost_minor stores money in integer-like minor units.
- Do not use floating-point money values.
- The currency determines the minor-unit interpretation.
- Example: 100 SEK = 10000 when using öre-level minor units.
- Example: 15 EUR = 1500 when using cent-level minor units.
- cost_minor is fixed monetary storage for configuration semantics, not a calculated float.
- Future money helper or value-object logic may be introduced in the domain layer later.

## 3) Static vs dynamic distinction

Static costs are reusable configuration/reference costs.

They are not:
- runtime calculated costs
- final invoiced costs
- supplier order costs
- inventory valuation truth
- accounting ledger lines
- historical task cost truth

When a domain needs historical accuracy, it must snapshot the values applied at the time instead of depending only on the live static_costs row.

## 4) Snapshot compatibility

Domains that apply a static cost to historical or lifecycle records must snapshot:
- cost name
- cost_minor
- currency
- relevant description or classification

Historical records must not depend exclusively on mutable live static_costs rows.

This preserves:
- historical correctness
- replay safety
- future correction compatibility

## 5) Mutability and history

Static costs may remain mutable configuration records.

Change semantics:
- updated_at / updated_by_id must reflect changes
- changes should be auditable
- domain consumers that need historical accuracy must snapshot the applied values

Do not add static_cost_history_records in phase one unless reconstruction of static-cost edits becomes an explicit requirement.

Future note:
- static cost history/versioning may be introduced later if cost changes require reconstruction.

## 6) Soft delete

Static costs should be soft-deleted, not hard-deleted.

Rules:
- soft-deleted static costs are not available for new selection/use
- historical records that already snapshotted the static cost remain valid
- hard deletion is out of scope for normal operations
- is_deleted = false with deleted_at IS NOT NULL is invalid
- is_deleted = true with deleted_at IS NULL is invalid

Soft delete preserves the ability to reconstruct historical records without allowing retired configuration to be reused in new flows.

## 7) Relationship strategy

- Some domains may reference static_cost_id directly for current configuration lookup.
- Historical or lifecycle records should snapshot applied values.
- static_cost_id is optional depending on the consuming domain's use-case.
- Do not turn static_costs into a hidden source of historical truth.
- Do not force a direct FK when the consuming domain only needs a snapshot at application time.

## 8) Integration guidance

Likely consumers:
- task planning flows that need reusable cost presets
- item or upholstery planning flows that need repeatable operational cost references
- future cross-domain workflow templates that need a shared cost vocabulary

Integration guidance:
- consumers should read static costs as configuration input
- consumers should snapshot applied values when generating durable records
- consumers should not use static costs as live accounting authority

## 9) Clarification checklist before implementation

1. Should static_costs be workspace-scoped from day one?
2. Should static cost changes require dedicated history/versioning in phase one, or is updated_at/updated_by_id enough?
3. Should static costs be selectable globally by type/category later?
4. Should domains reference static_cost_id directly, or only snapshot applied values?
5. Is the bounded currency enum enough for this phase, or is a formal currency table required later?
