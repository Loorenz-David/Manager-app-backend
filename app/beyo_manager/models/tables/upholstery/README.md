# Upholstery Domain — Table Guide

## Tables in this folder

| File | Table | Prefix | Purpose |
|---|---|---|---|
| `upholstery.py` | `upholsteries` | `uph` | Workspace-scoped upholstery catalog registry |
| `upholstery_inventory.py` | `upholstery_inventory` | `uin` | Planning/projection-oriented inventory state per upholstery |
| `upholstery_inventory_history_record.py` | `upholstery_inventory_history_records` | `uih` | Append-only ledger of every inventory movement (the projection's history) |
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
FK → `upholstery_inventory_history_records.client_id` (`use_alter`, `DEFERRABLE INITIALLY DEFERRED`, `ON DELETE SET NULL`). Points at the newest ledger row and is advanced in the same flush as the ledger append.

---

## `upholstery_inventory_history_records` — key rules

- **Append-only, one writer.** Rows are written only by `services/commands/upholstery/_inventory_history.py`, called from the helpers in `_inventory_mutations.py` (every quantity write goes through them; each takes a required `movement: InventoryMovementContext`). Exceptions: the migration baseline (`opening_balance`) and `scripts/backfill/backfill_upholstery_inventory_history.py` (`is_reconstructed = true`). `tests/unit/services/commands/upholstery/test_inventory_mutation_choke_point_guard.py` enforces that no other code assigns a quantity column or skips `movement=`.
- **Snapshots.** Each movement stores `before_*` / `after_*` for all eight quantity buckets; `previous_record_id` chains it to the inventory's previous latest row. `before` ≠ previous `after` (a *chain break*) or current totals ≠ latest `after` (*drift*) means the totals changed outside the recorded paths.
- **Nesting.** Requirement state changes caused by a movement (allocation promotions/demotions) are child rows (`parent_record_id`, `requirement_state_changed`, no snapshot, no chain advance). State-only commands write a zero-delta `allocation_run` parent.
- **Soft references.** `requirement_id`, `item_upholstery_id`, `item_id`, `task_id`, `task_step_id`, `upholstery_order_id` carry no FK (the requirement may be inserted after its ledger row; the ledger outlives deletes).
- **`movement_type`** is a Postgres enum (new values need `ALTER TYPE … ADD VALUE`); **`trigger`** is a plain string backed by `InventoryMovementTriggerEnum`, so new command origins need no migration.
- **Anomalies.** `in_need_clamped_at_zero` marks a movement whose need reduction hit the 0 floor (the projection already held less need than the requirement accounted for).
- Read via `GET /api/v1/upholstery-inventories/{client_id}/history`.

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

- Warehouse movement logs, reservation/lock engines
- Warehouse-specific and location-specific threshold segmentation
- `upholstery_supplier_links` and procurement order lifecycle
- Global catalog template compatibility with workspace-local overrides
