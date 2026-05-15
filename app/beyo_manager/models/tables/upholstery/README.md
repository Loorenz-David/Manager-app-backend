# Upholstery Domain — Table Guide

## Tables in this folder

| File | Table | Prefix | Purpose |
|---|---|---|---|
| `upholstery.py` | `upholsteries` | `uph` | Workspace-scoped upholstery catalog registry |
| `upholstery_inventory.py` | `upholstery_inventory` | `uin` | Planning/projection-oriented inventory state per upholstery |
| `upholstery_inventory_threshold_policy.py` | `upholstery_inventory_threshold_policies` | `utp` | Workspace-scoped inventory warning and escalation policies |

---

## `upholsteries` — key rules for commands

Upholsteries are **mutable catalog-facing registry entities**. They represent catalog truth, not inventory execution state.

- `code` is workspace-unique when non-null: partial unique index `uix_upholsteries_workspace_code WHERE code IS NOT NULL`.
- Downstream lifecycle entities (orders, requirements) may snapshot `name` and `code` to preserve rendering stability when registry values evolve.
- **Image ownership is centralized.** Images attach via the polymorphic image-link system (extend `ImageLinkEntityTypeEnum`). Do not add image blobs or upholstery-specific image tables.
- Soft-deleted upholsteries remain operationally queryable for privileged reconstruction and replay.

---

## `upholstery_inventory` — key rules for commands

### What this table is
A **replay-compatible operational aggregate projection** derived from append-only lifecycle history. It represents planning/projection state — not authoritative warehouse movement execution.

### What it is not
- Not a warehouse movement log
- Not a reservation lock authority
- Not a procurement orchestrator
- Not accounting valuation truth

### Quantity fields (`current_*`, `total_*`)
All quantity fields are `Numeric(14,3)` stored as Python `Decimal`. They are **recomputable projections**:
- `current_stored_amount_meters`, `current_amount_in_use_meters`, `current_amount_in_need_meters`, `current_amount_ordered_meters`
- `total_upholstery_used_meters`, `total_upholstery_used_inventory_meters`, `total_upholstery_used_surplus_meters`, `total_upholstery_surplus_meters`

If these values diverge from append-only history reconstruction, **append-only lineage takes precedence**.

### `inventory_condition`
A synthesized operational visibility projection (`AVAILABLE`, `LOW_STOCK`, `OUT_OF_STOCK`). Derived deterministically from projected quantity, demand, and threshold-policy evaluation. Prefer domain-derived deterministic projection over arbitrary manual mutation. Precedence: `OUT_OF_STOCK` overrides `LOW_STOCK` when both conditions are satisfied.

### `latest_projection_history_id`
Plain `String(64)`, **no FK constraint** in this phase — `upholstery_inventory_history_records` table is deferred. A future migration will add the FK when that table is introduced.

### `projected_inventory_value_minor` / `currency`
Operational planning/reference valuation only. Not authoritative accounting truth. Currency represents the current planning context, not procurement costing truth.

### One row per upholstery
UNIQUE(workspace_id, upholstery_id). Single inventory planning row per upholstery per workspace in this phase.

---

## `upholstery_inventory_threshold_policies` — key rules for commands

Threshold policies are **evaluation/governance layers only** — not inventory ownership, warehouse authority, or procurement execution.

### Scope
- `WORKSPACE_DEFAULT`: applies to all upholstery in the workspace unless overridden.
- `UPHOLSTERY`: applies to a specific upholstery. CHECK constraint enforces `upholstery_id IS NOT NULL` when scope is UPHOLSTERY.

### Precedence (apply in domain layer)
UPHOLSTERY-scoped policy overrides WORKSPACE_DEFAULT for the same evaluation context.

### Temporal windows
`effective_from` / `effective_to` support time-bounded policy governance. Queries for active policy must filter accordingly.

### Fields
- `low_stock_minimum_meters`: `Decimal`, absolute threshold in meters.
- `low_stock_ratio`: `Decimal`, ratio between 0 and 1 (CHECK constraint).
- `out_of_stock_epsilon_meters`: `Decimal`, near-zero threshold.
- `escalation_policy`: `NONE`, `RECOMMEND_REORDER`, or `ESCALATE_TO_PROCUREMENT`.
- `warning_tier`: `NORMAL`, `LOW_STOCK_WARNING`, or `URGENT_REORDER`.

### Determinism
Threshold-policy evaluation must remain deterministic and replay-compatible. Identical inputs must produce identical `inventory_condition` outcomes.

---

## Deferred

- `upholstery_inventory_history_records` (history/audit table; FK on `latest_projection_history_id` is deferred)
- Warehouse movement logs, reservation/lock engines
- Warehouse-specific and location-specific threshold segmentation
- `upholstery_supplier_links` and procurement order lifecycle
- Global catalog template compatibility with workspace-local overrides
