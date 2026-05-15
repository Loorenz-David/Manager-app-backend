# Issue Types Domain — Table Guide

## Tables in this folder

| File | Table | Prefix | Purpose |
|---|---|---|---|
| `issue_type.py` | `issue_types` | `ist` | Workspace-scoped problem taxonomy registry |
| `issue_severity.py` | `issue_severities` | `iss` | Severity weighting registry (affects timing estimates) |
| `issue_category_config.py` | `issue_category_configs` | `icc` | Time-windowed base-time configuration per (issue_type, item_category) |

---

## What this domain is (and is not)

These are **mutable operational registries** for issue classification. They define the taxonomy and timing inputs that `item_issues` and task planning systems consume.

They are **not**:
- runtime error event streams
- worker failure telemetry
- queue retry categories
- analytics projections

---

## `issue_types` — key rules for commands

- `source` describes **intake and operational provenance** of the issue taxonomy (`INTERNAL_INSPECTION`, `CUSTOMER`, `SUPPLIER`, `IMPORTED`). It does **not** represent assignment routing, worker ownership, or execution authority.
- `source` enums are domain-local. Do not treat `issue_source` as interchangeable with `item_upholstery_source` or other domain-specific source enums.
- Soft-deleted issue types **may not be assigned to new item issues**. Enforce in domain guards.
- Taxonomy changes should be audited because changing a type name can affect downstream timing and analytics. When reconstruction correctness matters, downstream entities must snapshot the name at use time (`issue_name_snapshot` on `item_issues`).
- UNIQUE(workspace_id, name) — names are unique within a workspace.

---

## `issue_severities` — key rules for commands

- `time_multiplier` is a `Numeric(8,4)` value (Python `Decimal`). **Never `float`.**
- The multiplier is applied by domain logic: `base_time_seconds × time_multiplier = timing estimate`.
- Severity changes should be auditable. Historical item issues must preserve the applied multiplier via `time_multiplier` snapshot on `item_issues.time_multiplier`.
- `CHECK(time_multiplier >= 0)` enforced at DB level.
- Soft-deleted severities may not be assigned to new item issues.

---

## `issue_category_configs` — key rules for commands

- Defines the `base_time_seconds` for a given `(issue_type_id, item_category_id)` combination.
- Supports **temporal effective windows** via `effective_from` / `effective_to`. Queries for active config must filter accordingly.
- `CHECK(effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from)`.
- UNIQUE on `(workspace_id, issue_type_id, item_category_id, effective_from)` — allows multiple time-windowed configs for the same combination.
- When base time is applied to an `item_issue`, it must be snapshotted into `item_issues.base_time_seconds`. Future config changes must not retroactively mutate historical issue timing.

---

## Mutable-registry durability rule

These registries are intentionally mutable. Mutations must be auditable. Historical systems must preserve reconstruction compatibility via name and multiplier snapshots on downstream entities. The architecture favors mutable operational registries with historical durability protections over immutable frozen registries.

---

## Deferred

- SLA policy integration
- Global taxonomy templates with workspace-local overrides
- Dedicated historical snapshot systems for exports and analytics
