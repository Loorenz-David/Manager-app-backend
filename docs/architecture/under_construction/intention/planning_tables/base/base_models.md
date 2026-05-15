# Base Models Plan

Status: REFINED - Shared Base Rules
Domain: base_models
Contracts: 01, 03, 08, 21, 24, 40, 42
Created: 2026-05-13

## Objective

Define shared mutable aggregate rules and reusable aggregate metrics mixins for stats tables and future derived models.

## 1) Shared aggregate rules

Aggregate rows are mutable projection rows.

Aggregate systems intentionally mutate existing aggregate records over time.

These aggregates are:
- projection state
- not append-only event streams
- not immutable historical records

Aggregate-derived-state rule:
- aggregate tables are derived operational projection state
- they must remain rebuildable from runtime operational sources, historical records, and future replay/recompute systems
- aggregates are not canonical source-of-truth entities

Authoritative-runtime-source clarification:
- future runtime execution systems and operational history systems are expected to become the authoritative analytical source inputs
- examples include future task-step runtime systems, operational lifecycle records, execution history systems, and future runtime orchestration history
- analytics aggregates derive from operational runtime truth, not the inverse

Aggregate-write-authority rule:
- aggregate mutation belongs exclusively to command-layer orchestration flows and trusted aggregation/update services
- queries, routers, serializers, and read systems must not directly mutate aggregate rows

Historical-correction ownership clarification:
- historical correction flows belong exclusively to command-layer orchestration systems, replay/recompute systems, and trusted correction flows
- manual aggregate mutation should be avoided outside controlled correction/recompute orchestration

Replay/recompute compatibility rule:
- aggregate rows must remain replay-compatible
- future systems may rebuild, recompute, backfill, and correct aggregates from runtime and historical operational sources
- the architecture intentionally favors replayability, deterministic recomputation, and operational correction safety

Partial-window replay clarification:
- replay/recompute systems may operate on partial aggregate windows, targeted replay ranges, and bounded operational correction scopes
- not only full-table rebuilds
- the architecture must remain compatible with partial replay, localized recompute, and targeted correction orchestration

Deterministic-input rule:
- aggregate computation inputs must remain deterministic, replay-safe, and reproducible
- aggregate computation must not depend on mutable live lookups, websocket runtime state, external APIs, or non-deterministic runtime systems
- replay/recompute determinism is a foundational architectural requirement

Compensating-adjustment clarification:
- aggregate mutation flows may apply compensating adjustments during replay, recompute, correction, and backfill
- aggregate systems must support decrement operations, correction deltas, and replay-safe recomputation behavior
- do not assume aggregate mutation is increment-only

Idempotency compatibility rule:
- aggregate mutation flows must remain idempotency-compatible
- replay/recompute systems must avoid duplicate aggregate mutation, double-application of operational totals, and replay drift
- future correction systems must remain safe to rerun

Backfill/import replay-safety clarification:
- historical import and backfill systems must remain replay-safe, deterministic, and idempotent
- backfill orchestration must not introduce duplicate aggregate mutation, replay drift, or non-deterministic correction behavior

No-runtime-state rule:
- analytics aggregates store derived statistical state and historical operational projections
- they do not store live orchestration state, websocket runtime state, current task ownership, or active execution runtime state
- those concerns belong to runtime execution systems, orchestration systems, and websocket/presence systems

No-business-logic-in-aggregates rule:
- analytics aggregates must not become business-rule authority containers
- do not drive workflow transitions from aggregates
- do not authorize operational state from aggregates
- do not derive orchestration decisions exclusively from aggregates
- business rules belong to runtime execution systems, domain rules, and orchestration systems, not analytics projections

No-direct-registry-mutation rule:
- analytics aggregates must not directly mutate user identity ownership, workspace ownership, or working section registry ownership
- snapshot fields exist exclusively for historical rendering durability and replay-safe analytical rendering
- aggregates are not synchronization-authority entities

Aggregate-drift recoverability rule:
- aggregate drift is considered operationally recoverable through replay, recompute, backfill, and correction flows
- aggregates are intentionally rebuildable projection state, not irreplaceable operational truth

Replay-authority clarification:
- replay/recompute systems are authoritative over existing aggregate state
- existing aggregate rows may be corrected, recomputed, overwritten, or rebuilt during trusted replay/recompute orchestration

Aggregate-dependency-boundary clarification:
- aggregates derive from runtime execution and historical operational systems
- runtime systems must not depend on analytics aggregates as operational authority
- avoid architecture inversion where orchestration systems, workflow systems, or execution systems depend on aggregate projections for operational truth

Analytical-dimension aggregate semantics:
- future analytical dimension tables such as user_daily_issue_type_stats and user_daily_item_category_stats are also derived aggregate projections
- they are replay/recompute-compatible projection state
- they are not canonical operational history, event stores, or blob-style metadata containers

Aggregate-scope clarification:
- analytics aggregates represent operational reporting convenience, analytical projections, and derived statistical state
- they are not accounting ledgers, payroll ledgers, immutable financial systems, or canonical operational history
- these tables are analytical convenience projections only, not business-rule authority containers

UTC timestamp policy:
- all timestamps are persisted in UTC
- frontend/UI layers are responsible for localization and human-readable rendering
- operational calculations remain UTC-based

Snapshot policy:
- snapshot fields exist to preserve historical rendering durability
- historical analytics systems must not depend exclusively on mutable live registry rows
- historical correctness is prioritized over fully live-derived rendering

Snapshot-mutation prohibition:
- snapshot fields must not be retroactively synchronized with mutable registry entities
- examples: user_display_name_snapshot, section_name_snapshot
- historical analytics rendering durability is prioritized over live registry synchronization

## 2) Reusable aggregate metrics mixins

Use Python mixins in models/base (not table inheritance):
- AggregateMetricsCountsMixin
- AggregateMetricsTimeMixin
- AggregateMetricsTotalsMixin
- AggregateMetricsCostMixin

Safety rule:
- these mixins are column-only and contain no FK; no declared_attr needed
- any FK mixin must use declared_attr

Naming semantics:
- aggregate metrics mixin naming is preferred over work-record mixin naming
- the naming should clearly communicate aggregate reuse, statistical composition, and projection-oriented ownership

Partitioning compatibility:
- shared aggregate design should remain compatible with future date-based partitioning, analytical partition strategies, and archival partitioning where table scale or retention pressure requires it

Aggregate-granularity philosophy:
- aggregate granularity must remain intentional, operationally meaningful, and reporting-driven
- avoid speculative aggregate fragmentation, arbitrary time-bucket proliferation, and over-specialized aggregate projections
- aggregate granularity should reflect demonstrated operational reporting value

Projection-explosion guard:
- new aggregate projections require demonstrated operational reporting value before introduction
- avoid uncontrolled proliferation of speculative projections, redundant aggregate tables, and overlapping analytical models
- projection growth must remain intentional and operationally justified

Aggregate-window ownership clarification:
- aggregate window ownership belongs to dedicated projection models
- do not overload aggregate tables with mixed granularity semantics, multi-window projection ownership, or overloaded temporal aggregation responsibilities
- daily aggregates, weekly aggregates, and monthly aggregates should remain separate projection models when introduced

Operational-read-optimization clarification:
- analytics aggregates exist to optimize operational reads, not operational writes
- aggregates are reporting projections, analytical conveniences, and derived read models
- they are not runtime execution authority, workflow ownership systems, or orchestration state containers
- this distinction is foundational to the architecture

## 3) Usage guidance

Stats tables and future derived models should reference this file for shared aggregate rules and reusable metrics mixins instead of duplicating the base semantics inline.