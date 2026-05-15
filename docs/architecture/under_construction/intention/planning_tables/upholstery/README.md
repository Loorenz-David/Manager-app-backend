# Upholstery Planning Contracts

Status: DRAFT - Initial Structured Split
Domain: upholstery
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Translate scratch operational upholstery planning into stable planning contracts with clear ownership boundaries, replay-safe lifecycle semantics, and future runtime/projection compatibility.

## Contract Index

- [upholstery_models.md](upholstery_models.md): upholstery registry ownership and catalog compatibility
- [upholstery_supplier_models.md](upholstery_supplier_models.md): supplier registry ownership and survivability
- [upholstery_supplier_relationship_models.md](upholstery_supplier_relationship_models.md): supplier-to-upholstery sourcing relationship lifecycle support
- [upholstery_inventory_models.md](upholstery_inventory_models.md): inventory planning and projection semantics
- [upholstery_inventory_history_models.md](upholstery_inventory_history_models.md): append-only inventory historical events and replay snapshots
- [upholstery_order_models.md](upholstery_order_models.md): sourcing/procurement order lifecycle and boundaries

## Architectural direction

The domain intentionally separates:
- registry entities
- lifecycle entities
- runtime orchestration entities
- projections/materialized analytics

Current planning must not collapse runtime warehouse movement, reservation, procurement execution, and analytics concerns into registry rows.

## Shared governance principles

- Workspace-scoped ownership across all upholstery entities.
- soft deletion preserves replay, audit, and historical reconstruction compatibility.
- bounded currency enum for current scope:
  - SWEDISH_KRONA
  - DANISH_KRONA
  - EURO
- authoritative lifecycle mutation remains domain-governed.
- runtime systems may influence and recommend, but do not become implicit authority.
- historical replay correctness takes priority over premature optimization.
- image lifecycle ownership remains centralized in contract 43 image architecture; upholstery extends polymorphic link enums when implemented.

## Clarification staging

Operational clarifications that remain unresolved are tracked at the end of each planning contract under Clarifications before implementation.
