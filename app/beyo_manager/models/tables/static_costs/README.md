# Static Costs Domain — Table Guide

## Tables in this folder

| File | Table | Prefix | Purpose |
|---|---|---|---|
| `static_cost.py` | `static_costs` | `scst` | Reusable workspace-scoped operational cost reference entries |

---

## What static costs are (and are not)

Static costs are **configuration/reference records** shared across multiple domains. They are:
- reusable cost presets for task planning, item costing, upholstery planning
- operational convenience reference values

They are **not**:
- ledger entries
- payroll truth
- procurement authority
- final invoiced cost records
- inventory valuation truth
- accounting book lines

---

## Money storage

- `cost_minor` stores money as an **integer minor-unit value** (e.g. 100 SEK = 10000 öre).
- `currency` determines the minor-unit interpretation.
- **Never use floating-point for monetary values.**

---

## Key rules for commands

### Snapshot on use
When a domain applies a static cost to a durable lifecycle record, it **must snapshot** the following values at the time of application:
- `cost_name` (or equivalent label)
- `cost_minor`
- `currency`

Historical records must not depend exclusively on the mutable live `static_costs` row. If the static cost row changes later, historical records must remain correct from their snapshot.

### Soft delete
- Soft-deleted costs are not available for new selection or use.
- Historical records that already snapshotted the values remain valid.
- Hard deletion is forbidden in normal operations.
- `is_deleted=false` with `deleted_at != null` is an invalid state.

### Updates are auditable
`updated_at` / `updated_by_id` must reflect every change. If cost-change reconstruction becomes a future requirement, a `static_cost_history_records` table would be introduced — but this is not implemented in this phase.

---

## Deferred

- Global/cross-workspace static cost templates
- Version-aware static cost history records
- Category/type taxonomy for cross-domain cost classification
