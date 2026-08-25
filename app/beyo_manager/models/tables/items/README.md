# Items Domain — Table Guide

## Tables in this folder

| File | Table | Prefix | Purpose |
|---|---|---|---|
| `item_category.py` | `item_categories` | `itc` | Workspace-scoped item taxonomy by major category |
| `item.py` | `items` | `itm` | Core item registry (furniture piece identity) |
| `item_issue.py` | `item_issues` | `iti` | Lifecycle-oriented issue records attached to items |
| `item_upholstery.py` | `item_upholsteries` | `iup` | Upholstery planning context attached to an item |
| `item_upholstery_requirement.py` | `item_upholstery_requirements` | `iur` | Sourcing and fulfillment lifecycle rows for upholstery |

---

## `item_categories` — key rules for commands

- `major_category` is the high-level classification: `WOOD` or `SEAT`.
- UNIQUE(workspace_id, name) within a workspace.
- Soft-deleted categories should not be assigned to new items. Enforce in domain guards.

---

## `items` — key rules for commands

### Identity fields
- `article_number` and `sku` are **workspace-unique when non-null** via partial unique indexes (`WHERE article_number IS NOT NULL`, `WHERE sku IS NOT NULL`). Two items in the same workspace cannot share the same article number or sku.
- `external_id`, `external_url`, `external_source`, `external_order_id` are interoperability metadata only — not synchronization authority.

### State
- `ItemStateEnum`: `PENDING`, `STALLED`, `FIXING`, `READY`.
- State transitions are enforced by domain guards, not DB constraints.

---

## `item_issues` — key rules for commands

### Lifecycle semantics
Issue rows are **lifecycle entities** — append-oriented operational records, not static registry rows. Resolved issues remain historically relevant.

State machine: `PENDING → FIXING → RESOLVED`. Blocked and deferred paths:
- `BLOCKED`: progression is blocked by dependency, inventory, or external constraint.
- `DEFERRED`: intentionally postponed.
- `SKIPPED`: intentionally not executed in this lifecycle context.

Do not collapse BLOCKED, DEFERRED, and SKIPPED into a single meaning.

### Snapshot on creation
When creating an issue, **snapshot immediately**:
- `issue_type_snapshot` ← current `issue_types.name` (not null)
- `issue_mode_snapshot` ← the mode the issue was raised under
- `placement_of_issue_snapshot` ← where on the item the issue sits

Future config changes must not retroactively alter historical issue records.

### Multiple issues per item
Multiple active issues of the same `issue_type_id` may coexist for the same item unless future domain guards explicitly restrict duplication.

### Durability
Do not hard-delete issue rows. `is_deleted` / `deleted_at` lifecycle only.

---

## `item_upholsteries` — key rules for commands

### Semantics
Represents the **upholstery planning context** for an item. One active upholstery planning context should exist per item at a time (future multi-upholstery support is not implemented in this phase).

- `source`: `INTERNAL` (workspace owns the material) or `CUSTOMER` (customer supplies the material). This is **provenance**, not stock reservation state.
- At most one non-deleted upholstery planning context may exist per item. Creation workflows reuse that context while its active requirement is non-terminal; after `COMPLETED` or `FAILED`, the old context is soft-deleted and a new context is created.
- The partial unique index `uix_item_upholsteries_current_workspace_item` enforces this invariant at the database boundary. Existing duplicate rows must be resolved before that migration can be applied.
- `upholstery_id` is nullable — preserves historical survivability when upstream catalog rows are retired.
- `name` and `code` may preserve sourcing snapshot values independent from catalog evolution (replay-safe rendering).

### `active_requirement_id` (circular FK)
Declared with `use_alter=True` to resolve the DDL ordering cycle between `item_upholsteries` and `item_upholstery_requirements`.

`active_requirement_id` is a **convenience pointer only** — not lifecycle authority. Historical reconstruction must traverse the full `item_upholstery_requirements` lineage, not only this pointer.

### `amount_meters`
`Numeric(12,3)` — Python `Decimal`. Represents **estimated planning requirement**, not authoritative inventory consumption truth.

---

## `item_upholstery_requirements` — key rules for commands

### Semantics
Each row is a **sourcing lifecycle row** — a single fulfillment attempt or sourcing event for the parent upholstery context. Multiple rows may coexist for the same `item_upholstery_id` (staged sourcing, splitting, partial fulfillment).

### `upholstery_inventory_id`
Plain `String(64)`, **no FK constraint** in this phase — the `upholstery_inventory` FK is deferred. A future migration will add the constraint.

### State machine (`ItemUpholsteryRequirementStateEnum`)
`AVAILABLE → NEEDS_ORDERING → ORDERED → IN_USE → COMPLETED`

Terminal failure: `FAILED`. State transitions enforced by domain guards.

### Lifecycle timestamps
Set each timestamp atomically with the corresponding state transition:
- `ordered_at` when entering `ORDERED`
- `in_use_at` when entering `IN_USE`
- `completed_at` when entering `COMPLETED`
- `failed_at` when entering `FAILED`

### `item_currency_enum` Postgres type
This file **owns** `item_currency_enum` (`create_type=True`, `item_upholstery_requirement.py:44`). `item.py` has no currency column at all — its only `create_type=True` is `item_state_enum`. There is no import-order constraint between the two files for this type.

---

## Deferred

- Inventory reservation / lock engines
- Per-issue image attachment (extends `ImageLinkEntityTypeEnum` in the image domain)
- `item_upholstery_requirements.upholstery_inventory_id` FK (awaits `upholstery_inventory_history_records` table)
- Multi-upholstery support per item
- Item external sync / import workflows
