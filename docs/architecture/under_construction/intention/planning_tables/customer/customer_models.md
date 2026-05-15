# Customer Models Plan

Status: DRAFT - Initial Structured Split
Domain: customer_registry
Contracts: 01, 03, 08, 21, 24, 25, 35, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define the customer registry/profile model as a workspace-scoped operational identity and contact anchor while preserving replay-safe historical compatibility with task orchestration and future privacy governance.

## Naming correction from scratch source

The scratch source uses COSTUMER/COSTUMER_HISTORY_RECORD wording.

This formal planning normalizes naming to:
- customers
- customer_history_records
- customer_id

Do not use costumer/costumers in formal model naming.

## 1) Core table

### 1.1 customers

Columns:
- client_id: String(64) PK, prefix cus
- workspace_id: FK workspaces.client_id, not null, indexed
- display_name: String(255), not null
- customer_type: Enum(customer_type), not null, default UNKNOWN, indexed
- status: Enum(customer_status), not null, default ACTIVE, indexed
- primary_phone_number: String(64), nullable
- primary_email: String(255), nullable
- primary_phone_number_normalized: String(64), nullable, indexed
- primary_email_normalized: String(255), nullable, indexed
- address: JSON, nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- latest_history_record_id: FK customer_history_records.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, display_name)
- INDEX(workspace_id, primary_phone_number)
- INDEX(workspace_id, primary_email)
- INDEX(workspace_id, primary_phone_number_normalized)
- INDEX(workspace_id, primary_email_normalized)

Normalized index semantics:
- normalized-field indexes are lookup/dedup support indexes only.
- they are not uniqueness constraints in this phase.

Note on uniqueness strategy:
- do not enforce global uniqueness on display_name.
- do not enforce hard uniqueness on primary phone/email fields in this phase.
- duplicate detection and merge workflows are deferred to future policy-governed flows.

## 2) Enums

### 2.1 customer_type
- PERSON
- COMPANY
- UNKNOWN

### 2.2 customer_status
- ACTIVE
- INACTIVE

## 3) Ownership and semantics

Registry semantics:
- customers are operational identity/profile records.
- customers own mutable contact/profile convenience state.
- customers are relationship anchors for task and future order/return/pre-order systems.

Boundary semantics:
- customers are not task runtime state containers.
- customers are not communication runtime systems.
- customers are not payment/accounting systems.
- customers are not logistics execution systems.
- customers are not websocket presence/runtime state holders.

Profile mutability semantics:
- display_name, primary contact fields, and address are mutable profile fields.
- profile mutability is expected and does not replace historical lineage.
- customer_history_records remain authoritative for profile-change lineage reconstruction.

Display-name semantics:
- display_name is the operational customer display label.
- display_name is not legal identity authority.
- display_name may represent a person, company, placeholder, or externally imported customer label.
- future legal/company identity fields may be introduced later if required.

Customer-type semantics:
- customer_type is operational classification only.
- customer_type does not create payment/accounting/legal identity ownership.
- future workflows may use customer_type for display/routing policies.

Status semantics:
- status is operational lifecycle visibility.
- status is separate from soft deletion.
- soft deletion controls deletion/deactivation visibility.
- status=INACTIVE means the customer is not currently active for normal operational use but remains visible according to normal customer query policies.
- is_deleted=true means the customer is removed from normal operational views and is available only through privileged historical/reconstruction workflows.
- status and soft deletion must not drift into duplicate semantics.
- future states such as MERGED, REDACTED, or ANONYMIZED are deferred unless policy requires them.

Contact field semantics:
- primary_phone_number and primary_email are primary operational contact fields only.
- validation belongs to command/input validation.
- normalization ownership belongs to command/input validation.
- raw values preserve operational input/display context.
- normalized fields support lookup/search/dedup workflows.
- normalized fields are not unique in this phase.
- primary_email_normalized should use lowercase normalized email semantics.
- primary_phone_number_normalized may be null if the raw phone number cannot be safely normalized.
- normalization should not force false validity when raw phone values are incomplete, invalid, local-format, or messy.
- communication preferences and communication logs are out of scope for this phase.
- future customer_contact_methods may support multiple phones/emails.

Address schema governance:
- address follows bounded schema:
  - street_address: string
  - post_number: string
  - city: string
  - country: string
  - municipality: string
  - coordinates (optional):
    - lat: float (optional)
    - lng: float (optional)
- customer.address is mutable customer profile contact/location context.
- customer.address is not logistics execution truth.
- address JSON may be partial.
- individual address fields are optional unless command validation for a specific workflow requires them.
- task.address is a task-time snapshot and must not be auto-overwritten by customer profile edits.
- coordinates are operational convenience metadata only.
- coordinates are not legal address truth.
- coordinates are not logistics execution authority.
- country and municipality may later be normalized for search, delivery, statistics, or regional policy workflows.
- keep address JSON simple in this phase; do not normalize country/municipality into separate tables yet.
- dedicated address/contact snapshot entities may be introduced later.

Latest pointer semantics:
- latest_history_record_id is a convenience/projection pointer only.
- full reconstruction must traverse customer_history_records lineage.
- pointer updates must be transactionally coupled with the history append that created the referenced row.

Circular FK implementation note:
- customers.latest_history_record_id -> customer_history_records.client_id and customer_history_records.customer_id -> customers.client_id create a circular reference pattern.
- latest_history_record_id may require nullable FK creation and post-insert update.
- migration ordering and ORM relationship configuration must avoid circular insert problems.

Profile mutation and lineage coupling:
- customer creation MUST append customer_history_records.
- customer profile/contact/address changes MUST append customer_history_records.
- customer status changes MUST append customer_history_records.
- customer soft deletion/restoration MUST append customer_history_records.
- direct profile mutation without history append is forbidden for domain commands.
- profile row mutation, history append, latest_history_record_id update, updated_at, and updated_by_id must be transactionally coupled in the same command transaction.

System-created attribution policy:
- created_by_id is nullable only for trusted system/bootstrap/internal operations.
- system-created customers should preserve creation provenance through customer_history_records metadata when created_by_id is null.
- null actor attribution must not become opaque operational history.

Duplicate identity realism:
- operational customer identity is often messy.
- phone/email may be missing, shared, mistyped, or later corrected.
- future soft-match dimensions may include normalized phone, normalized email, display_name similarity, address similarity, external references, and task relationship patterns.
- duplicate detection is policy-driven.
- duplicate detection is not enforced via aggressive early DB uniqueness.
- architecture should prefer safe duplicate detection/merge workflows later over aggressive early uniqueness constraints.

## 4) Relationship map

- workspaces (1) -> (*) customers
- customers (1) -> (*) customer_history_records
- customers (1) -> (*) tasks via tasks.customer_id

Task relationship semantics:
- a customer may have many tasks.
- tasks.customer_id references customers.client_id.
- task-level phone/email/address fields remain task-time operational snapshots.
- customer profile updates must not retroactively mutate historical task snapshots.

Prefix map:
- cus -> customers
- chr -> customer_history_records

Prefix governance note:
- prefixes support client_id generation, debugging, observability, tracing, exports, and replay tooling.
- customer prefixes should be registered in any future global prefix index/base planning map.

## 5) Scope boundary

In scope:
- customer identity/profile registry
- contact ownership fields
- task anchor relationship ownership
- replay-compatible profile lineage coupling

Out of scope:
- CRM campaign systems
- messaging/communication timeline systems
- logistics runtime state
- payment/accounting ownership
- websocket runtime/session state

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- cross-workspace customer/task links are forbidden.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft deletion is operational lifecycle visibility.
- GDPR erasure/anonymization/redaction is privacy governance.
- these are separate workflows.
- soft deletion does not equal privacy erasure.
- soft-delete consistency must hold: is_deleted=false with deleted_at!=NULL is invalid, and is_deleted=true with deleted_at IS NULL is invalid.
- hard deletion is out of scope for normal operations.
- deleted customers remain queryable for privileged historical reconstruction where policy allows.
- historical tasks remain valid when linked customers are soft-deleted.
- customer restoration is privileged and domain-governed.
- restoration is not silent flag flipping.
- restoration must append customer_history_records using change_type=RESTORED.
- all timestamps are persisted in UTC. Workspace timezone is used only for operational grouping/projection policies where explicitly defined.

No-cascade-delete rule:
- customer lineage and task relationships must not cascade-delete from customers or workspaces.
- use RESTRICT / NO ACTION semantics for historical durability.

## 7) Deferred runtime notes

- do not place active-task counters on customers.
- do not place communication runtime status on customers.
- do not place delivery/logistics runtime status on customers.
- do not place websocket presence fields on customers.
- runtime/projection systems may derive such views later without changing customer registry ownership.

## 8) Future integration notes

Future compatibility targets:
- Shopify customer linkage
- external order/POS systems
- messaging/contact systems
- delivery systems

Integration boundary rule:
- interoperability metadata, if added later, is integration context only.
- integration metadata is not synchronization authority or workflow truth ownership.

Merge workflow compatibility:
- future duplicate detection/merge workflows may be required.
- future merges must preserve task-history continuity and customer-history lineage durability.
- do not implement merge tables in this phase.
- future merge workflows should prefer canonical-customer redirection and alias/linkage semantics.
- avoid destructive hard relationship rewrites as default behavior.
- avoid deleting duplicates without lineage.

Future external links direction:
- a future customer_external_links model may include:
  - workspace_id
  - customer_id
  - provider
  - external_customer_id
  - external_url
  - linked_at
  - unlinked_at
- external links are interoperability metadata only.
- external links are not synchronization authority, lifecycle authority, or task orchestration truth.

## 9) Risks and protections

Risks:
- overloading customer rows with runtime orchestration state.
- aggressive uniqueness constraints that break real-world customer operations.
- retroactive mutation of task-time customer snapshots.

Protections:
- strict registry-profile boundary semantics.
- append-oriented customer history lineage contract.
- explicit task snapshot durability rule.
