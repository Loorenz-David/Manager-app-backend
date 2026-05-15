# Item Models Plan

Status: DRAFT - Initial Structured Split
Domain: item
Contracts: 01, 03, 08, 21, 24, 25, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define the item registry model and its durable ownership boundaries without embedding runtime orchestration or analytics-derived state.

## 1) Core table

### 1.1 items

Columns:
- client_id: String(64) PK, prefix itm
- workspace_id: FK workspaces.client_id, not null, indexed
- article_number: String(128), nullable, indexed
- sku: String(128), nullable, indexed
- state: Enum(item_state), not null, indexed
- item_category_id: FK item_categories.client_id, nullable (category registry may evolve per workspace)
- quantity: Integer, not null, default 1
- designer: String(255), nullable
- height_in_cm: Integer, nullable
- width_in_cm: Integer, nullable
- depth_in_cm: Integer, nullable
- item_value_minor: Integer, nullable
- item_cost_minor: Integer, nullable
- item_currency: Enum(item_currency_enum), nullable
- item_position: String(255), nullable
- external_id: String(255), nullable
- external_url: String(1024), nullable
- external_source: String(128), nullable
- external_order_id: String(255), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, article_number) WHERE article_number IS NOT NULL
- UNIQUE(workspace_id, sku) WHERE sku IS NOT NULL
- INDEX(workspace_id, state)

## 2) Enums

### 2.1 item_state
- PENDING
- STALL
- FIXING
- READY

### 2.2 item_currency_enum (bounded governance, this phase)
- SWEDISH_KRONA
- DANISH_KRONA
- EURO

Note: item_currency should use this bounded enum for current operational scope. Future ISO-4217 or monetary infrastructure may replace or expand this strategy. item_major_category is defined in item_category_models and is the authoritative classification source; classification derives exclusively through item_category_id.

## 3) Ownership and semantics

Registry semantics:
- items are operational registry entities
- item rows must not carry queue/runtime executor state
- item rows must not store derived analytics counters

Classification semantics:
- item classification derives exclusively through item_category_id → item_categories.major_category
- items do not carry a redundant major_category field
- classification authority must not drift across entities
- item_category_id remains the single classification ownership anchor

State semantics:
- item.state represents high-level business operational visibility state
- item.state does NOT represent task-step execution runtime, worker lock ownership, orchestration state, or queue execution state
- future runtime systems may influence, recommend, or derive item state transitions, but runtime systems do not own item registry lifecycle authority directly
- item.state may later derive from multiple operational domains including task-step runtime systems, blocking upholstery requirements, issue lifecycle systems, and operational readiness policies
- item.state remains a domain-owned business lifecycle field; no single runtime subsystem becomes exclusive state authority
- item.state is a synthesized business-operational field owned by domain orchestration policies
- authoritative lifecycle mutation ownership belongs to domain orchestration boundaries
- runtime execution systems do not become exclusive registry-state authority
- this protects replay correctness, future automation compatibility, runtime/domain separation, and future websocket/runtime orchestration boundaries
- this architecture intentionally separates execution runtime truth from synthesized business operational visibility

Future cross-domain runtime influence:
- future task-step runtime systems may influence multiple operational domains simultaneously including item states, issue progression, upholstery progression, operational analytics, and timing projections
- however, each domain preserves independent lifecycle ownership
- task runtime systems must not collapse lifecycle boundaries into execution-only semantics

item_state lifecycle guidance:
- PENDING: item exists operationally, active work has not meaningfully started, and item is awaiting downstream operational progression
- STALL: item progression is blocked by operational conflict (for example: missing upholstery/materials, unresolved blocking issue, or dependency conflict)
- future runtime systems may later introduce dedicated blocking-reason entities, operational dependency records, and task/runtime dependency chains without collapsing those concerns directly into item.state
- FIXING: active operational work is currently occurring; this state may later derive from task-step runtime execution systems
- READY: item is operationally considered prepared for downstream business usage only
- READY does NOT automatically imply ecommerce publication approval, public listing readiness, delivery release readiness, commercial approval workflows, or downstream inventory reservation approval
- READY must not be prematurely coupled to commercial or public lifecycle domains in this planning phase

Value and cost semantics:
- item_value_minor represents estimated business value semantics
- item_cost_minor represents internal operational cost semantics
- these fields must not be prematurely bound to accounting ledgers, inventory valuation engines, procurement cost authority, or tax/accounting systems in this planning phase

Position semantics:
- item_position represents temporary human-operational warehouse placement metadata and operational convenience metadata only
- it is NOT canonical inventory location authority, logistics runtime state, movement-history ownership, task-runtime positioning authority, authoritative movement history, historical warehouse reconstruction, logistics replay truth, or runtime movement auditing
- future systems may introduce item movement/runtime systems, warehouse-location runtime entities, or task/location orchestration systems without replacing historical item-position semantics immediately
- future movement/location systems may later provide dedicated historical runtime tracking independently
- item_position remains on items for this phase; do not move this concern into task runtime planning yet

External reference semantics:
- external_* fields are interoperability metadata only
- they are NOT runtime orchestration authority, synchronization truth ownership, workflow state containers, or execution routing systems
- these fields exist for integrations, imports, interoperability linkage, and external-reference reconstruction only

Source-enum isolation semantics:
- external_source is domain-local provenance metadata for integrations
- source enums are not interchangeable across domains (for example: external_source, issue_source, item_upholstery_source, item_upholstery_requirement_source)
- avoid cross-domain semantic assumptions, shared orchestration interpretation, and implicit workflow coupling

Measurement-unit governance:
- measurement units are intentionally normalized at the storage layer for replay and analytical consistency
- dimensions are stored in centimeters in item fields; this supports import compatibility and future conversion systems

Nullable-FK survivability semantics:
- nullable foreign keys may intentionally preserve historical survivability when registries evolve, catalogs are retired, integrations are removed, or deferred domains are archived
- replay-safe historical reconstruction is prioritized over aggressive FK rigidity in this planning phase

## 4) Relationship map

- workspaces (1) -> (*) items
- item_categories (1) -> (*) items
- items (1) -> (*) item_issues
- items (1) -> (*) item_upholsteries
- items (*) -> (*) tasks via future bridge (deferred; see integration notes)

## 5) Scope boundary

In scope:
- item registry identity and descriptive operational attributes
- durable ownership and soft-delete lifecycle

Out of scope:
- assignment queues
- worker execution progress
- task orchestration state
- analytics projections

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- cross-workspace references are forbidden.
- soft delete must preserve historical reconstruction compatibility.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.
- historical systems must not rely exclusively on mutable live fields such as designer, position, or category labels.
- item_category_id is the authoritative classification anchor; classification must not be inferred from item-level fields.
- operational lifecycle durability and replay correctness take precedence over premature live-query optimization during this planning phase.
- avoid collapsing historical lifecycle semantics into dashboard-oriented shortcuts or introducing runtime denormalization prematurely.
- future automation or AI-assisted systems may recommend transitions, classify operational states, propose issue categorization, and suggest lifecycle actions, but authoritative lifecycle mutation remains domain-governed.
- AI and automation systems do not become direct lifecycle authority; auditability, replay correctness, and operational governance boundaries must remain preserved.

## 7) Deferred runtime notes

Task relationship compatibility:
- the domain must remain compatible with future item-task runtime linking
- do not introduce runtime scheduler fields on items (worker_id, queued_at, lock metadata)

## 8) Future integration notes

Planned future integrations:
- task runtime relation table (item_task_links or domain-equivalent)
- supplier/order ingestion
- historical snapshot projection for mutable display fields
- items may attach images through the shared polymorphic image-link system defined in contract 43_image
- future implementation should extend ImageLinkEntityTypeEnum with item-related entity values rather than creating item-specific image ownership tables
- image ownership, annotations, and event lifecycle remain delegated to the centralized image domain architecture
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics

## 9) Risks and protections

Risks:
- overloading item.state with runtime semantics
- misuse of external fields as process authority

Protections:
- explicit runtime separation rule
- clear workspace ownership and soft-delete lifecycle constraints

## 10) Clarifications before implementation

1. Should article_number uniqueness be mandatory per workspace, or optional with partial unique behavior?
2. Is quantity always integer count, or must fractional quantity be supported for bulk materials?
3. Should item_currency default from workspace settings when value/cost is provided?
