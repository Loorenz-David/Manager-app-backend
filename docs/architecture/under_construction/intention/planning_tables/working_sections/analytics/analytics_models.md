# Working Section Analytics Models Plan

<!-- PLAN_analytics_aggregate_models_20260515: COMPLETED 2026-05-15 -->
<!-- Summary: backend/docs/architecture/implemented_summaries/SUMMARY_analytics_aggregate_models_20260515.md -->
<!-- Archived Plan: backend/docs/architecture/archives/implementation/PLAN_analytics_aggregate_models_20260515.md -->
<!-- Archive Record: backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_analytics_aggregate_models_20260515.md -->

Status: REFINED - Clarifications Resolved  
Domain: working_sections_analytics  
Contracts: 01, 03, 08, 21, 40, 42
Created: 2026-05-12
Updated: 2026-05-13

## Objective

Define foundational aggregate model structures for worker statistics and work tracking, without introducing full event-sourcing, runtime state, or analytics pipelines yet.

Shared aggregate base rules and reusable metrics mixins are defined in [planning/base/base_models.md](../../base/base_models.md).

## 1) Aggregate model set

### 1.1 user_lifetime_stats (lifetime aggregate)

Columns:
- client_id: String(64) PK, prefix usr_stat
- workspace_id: FK workspaces.client_id, not null, indexed
- user_id: FK users.client_id, not null
- user_display_name_snapshot: String(255), not null (snapshot)
- created_at: DateTime(tz), not null
- updated_at: DateTime(tz), not null
- inherited aggregate metrics mixin columns (see [planning/base/base_models.md](../../base/base_models.md))

updated_at clarification:
- aggregate rows intentionally mutate over time
- updated_at tracks projection mutation lifecycle
- replay/recompute operations may mutate this row repeatedly
- this differs intentionally from append-oriented lifecycle records where mutable update tracking is minimized

Role:
- mutating aggregate row (single aggregate row per user per workspace)
- lifetime operational aggregate, not an append-only historical record

See [planning/base/base_models.md](../../base/base_models.md) for shared mutable aggregate rules.

Constraints:
- UNIQUE(workspace_id, user_id)

### 1.2 user_daily_work_stats (daily per user)

Columns:
- client_id: String(64) PK, prefix udwr
- workspace_id: FK workspaces.client_id, not null, indexed
- user_id: FK users.client_id, not null
- user_display_name_snapshot: String(255), not null (snapshot)
- work_date: Date, not null
- created_at: DateTime(tz), not null
- updated_at: DateTime(tz), not null
- inherited aggregate metrics mixin columns (see [planning/base/base_models.md](../../base/base_models.md))

Constraints:
- UNIQUE(workspace_id, user_id, work_date)
- INDEX(user_id, work_date DESC)

work_date rule:
- work_date is computed using workspace operational timezone, not UTC calendar boundaries

### 1.3 user_section_daily_work_stats (daily per user per section)

Columns:
- client_id: String(64) PK, prefix usdwr
- workspace_id: FK workspaces.client_id, not null, indexed
- user_id: FK users.client_id, not null
- working_section_id: FK working_sections.client_id, not null
- section_name_snapshot: String(255), not null (snapshot)
- user_display_name_snapshot: String(255), not null (snapshot)
- work_date: Date, not null
- created_at: DateTime(tz), not null
- updated_at: DateTime(tz), not null
- inherited aggregate metrics mixin columns (see [planning/base/base_models.md](../../base/base_models.md))

Constraints:
- UNIQUE(workspace_id, user_id, working_section_id, work_date)
- INDEX(working_section_id, work_date DESC)

work_date rule:
- work_date is computed using workspace operational timezone, not UTC calendar boundaries

### 1.4 working_section_daily_work_stats (daily per section)

Purpose:
- section-level operational throughput
- staffing analytics
- section-level historical reporting
- operational performance breakdowns

Columns:
- client_id: String(64) PK, prefix wsdws
- workspace_id: FK workspaces.client_id, not null, indexed
- working_section_id: FK working_sections.client_id, not null
- section_name_snapshot: String(255), not null (snapshot)
- work_date: Date, not null
- created_at: DateTime(tz), not null
- updated_at: DateTime(tz), not null
- inherited aggregate metrics mixin columns (see [planning/base/base_models.md](../../base/base_models.md))

Recommended constraints:
- UNIQUE(workspace_id, working_section_id, work_date)
- INDEX(working_section_id, work_date DESC)

work_date rule:
- work_date is computed using workspace operational timezone, not UTC calendar boundaries

Derived aggregate clarification:
- this remains a derived aggregate table, not source-of-truth runtime state

### 1.5 client_id prefix reference

Compressed prefixes are intentional and must remain documented centrally.

| Prefix   | Table                              |
|----------|------------------------------------|
| usr_stat | user_lifetime_stats                |
| udwr     | user_daily_work_stats              |
| usdwr    | user_section_daily_work_stats      |
| wsdws    | working_section_daily_work_stats   |

Prefix strategy rules:
- compressed prefixes are intentional and must not be converted to verbose prefixes
- prefix consistency matters for observability, debugging, replay tooling, exports, and operational tracing
- new aggregate tables must register their prefix here before use

## 2) Reusable base reference

See [planning/base/base_models.md](../../base/base_models.md) for the shared mutable aggregate rules and reusable aggregate metrics mixins used by these stats tables and future derived models.

## 3) Aggregate vs event boundaries

Keep in this phase:
- aggregates only (lifetime + daily)
- transactional in-band updates in command execution

Do not add yet:
- user_shift_event logs
- resolved_items_log event tables
- external analytics pipelines/materialized workers

See [planning/base/base_models.md](../../base/base_models.md) for all shared aggregate boundary rules, including: aggregate-derived-state, authoritative-runtime-source, write-authority, historical-correction ownership, replay/recompute compatibility, compensating-adjustment, idempotency, no-runtime-state, no-business-logic-in-aggregates, no-direct-registry-mutation, aggregate-drift recoverability, and aggregate-scope.

## 4) Denormalization policy

Allowed snapshots:
- user_display_name_snapshot on aggregate rows
- section_name_snapshot on user_section_daily_work_stats and working_section_daily_work_stats

Not allowed:
- comma-separated section_names
- free-form blobs replacing relational keys

See [planning/base/base_models.md](../../base/base_models.md) for snapshot policy, no-direct-registry-mutation rule, and aggregate-drift recoverability rule.

Future analytical dimensions must use:
- dedicated aggregate tables
- dimensional aggregate relationships
- explicit analytical breakdown models

instead of JSON-array aggregate storage.

Examples:
- user_daily_issue_type_stats
- user_daily_item_category_stats

Clarification:
- issue/category analytics are analytical dimensions
- they are also derived aggregate projections, not canonical operational history entities
- they remain rebuildable and recomputable
- they are not blob-style aggregate metadata
- they are not JSON aggregate collections

Reason:
- JSON aggregate arrays create replay difficulty, indexing limitations, aggregation complexity, historical-correction problems, and poor analytical scalability

## 5) Performance and scaling

Expected pressure points:
- row lock contention on same user/day updates
- growth of lifetime aggregate width over time

Near-term strategy:
- accept row-level locking at current human throughput
- add targeted composite indexes
- preserve narrow schema and avoid speculative columns

Future trigger points:
- if per-user/day write contention becomes material, evaluate lock strategies
- if analytical dimensions expand, introduce dedicated aggregate tables rather than JSON arrays

Future partitioning awareness:
- daily aggregate tables are future candidates for date-based partitioning, analytical partition strategies, and archival partitioning if analytical scale or retention pressure requires it
- this phase does not implement partitioning, but the architecture should remain partition-compatible

See [planning/base/base_models.md](../../base/base_models.md) for UTC timestamp policy and aggregate-scope clarification.

## 6) Clarifications before implementation

Q1: Should work_date be computed in workspace timezone or UTC?

Answer:
Confirmed. work_date is computed using workspace operational timezone, not UTC calendar boundaries.

---

Q2: Must user_lifetime_stats be eagerly created during user creation?

Answer:
Confirmed. user_lifetime_stats should be eagerly created during user provisioning.

Reason:
- avoids lazy-create race conditions
- simplifies aggregate orchestration
- avoids null aggregate lookup paths

---

Q3: What is the acceptable max size for JSON issues/items arrays before mandatory migration?

Answer:
Resolved by architecture change. JSON-array aggregate storage is no longer allowed in this plan.
Future issue/category analytics must use dedicated aggregate tables, analytical dimension tables, and explicit relational aggregate models instead of JSON-array aggregate storage.

---

Q4: Should section-level daily aggregate table (working_section_daily_work_stats) be added in Phase 2 or postponed?

Answer:
Confirmed. working_section_daily_work_stats should be added in Phase 2.
Section-level operational analytics are considered foundational operational reporting infrastructure.
