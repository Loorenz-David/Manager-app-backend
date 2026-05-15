# Working Sections Domain — Table Guide

## Tables in this folder

| File | Table | Prefix | Purpose |
|---|---|---|---|
| `working_section.py` | `working_sections` | `wsec` | Registry of operational work areas within a workspace |
| `working_section_membership.py` | `working_section_memberships` | `wsme` | Staffing history: which users belong to which sections |
| `working_section_dependency.py` | `working_section_dependencies` | `wsd` | Directed prerequisite graph between sections |
| `working_section_item_category.py` | `working_section_item_categories` | `wsic` | Bridge: which item categories a section can handle |
| `working_section_supported_issue_type.py` | `working_section_supported_issue_types` | `wsit` | Bridge: which issue types a section can handle |

---

## What working sections are (and are not)

Working sections are **stable operational registry entities** — capability topology definitions that describe what a section can work on and who is staffed there.

They are **not**:
- runtime orchestration state containers
- task assignment systems
- queue workers
- realtime presence holders

Do not add to working sections:
- `active_task_count`, `queue_depth`, `busy_workers` — these are runtime analytics projections
- websocket / realtime state
- live execution counters

---

## `working_sections` — key rules for commands

- **Soft-deleted sections may not receive new memberships or new dependency edges.**
- Deleted sections remain historically durable for analytics and operational history.
- `image` field stores SVG content, SVG references, or direct image URLs. It is **not** wired to the managed image domain in this phase.
- `created_by_id` / `updated_by_id` / `deleted_by_id` may be null only for bootstrap or trusted internal system operations.
- Soft-delete consistency: `is_deleted=false` with `deleted_at != null` is invalid.

---

## `working_section_memberships` — key rules for commands

### Membership semantics
Membership represents **staffing capability participation** — which sections a worker belongs to. It is **not** a runtime task assignment or live workload assignment.

### Many-to-many
Users may belong to multiple working sections simultaneously. One assignment does not preclude others.

### Active membership
Active = `removed_at IS NULL`. Enforced via partial unique index `uix_working_section_memberships_active` on `(workspace_id, working_section_id, user_id) WHERE removed_at IS NULL`.

To remove a user: set `removed_at` and `removed_by_id` in the same command — do not delete the row.

### Workspace consistency rule
`working_section_memberships.workspace_id` must match `working_sections.workspace_id` and the user's workspace membership scope. Cross-workspace memberships are forbidden. Enforce in domain validation.

### History durability
All rows are append/lifecycle-oriented. Do not hard-delete membership rows — historical rows are retained for staffing analytics and assignment history reconstruction.

---

## `working_section_dependencies` — key rules for commands

### Semantics
`dependent_section_id` depends on `prerequisite_section_id`. The prerequisite section must complete its phase before the dependent section begins.

This is **operational execution ordering**, not hierarchy or escalation.

### Cycle detection
The database only enforces self-reference prevention (`CHECK dependent_section_id != prerequisite_section_id`). **Cycle detection belongs exclusively to domain guards** — not to the model layer.

### Durability
Dependency removals should remain historically reconstructable. Do not blindly hard-delete dependency history in future operational systems.

---

## Bridge tables (item categories, issue types)

- Both bridges represent **current operational configuration state**, not historical event logs.
- When historical durability is required (e.g. analytics snapshots), downstream systems must snapshot the capability configuration at the time of the event.
- Workspace boundary consistency applies to all bridge rows.

---

## All relationships are workspace-scoped

Cross-workspace relationships are forbidden across all five tables. `workspace_id` is explicit on memberships, dependencies, and both bridge tables. Enforce at both domain validation and relational ownership levels.
