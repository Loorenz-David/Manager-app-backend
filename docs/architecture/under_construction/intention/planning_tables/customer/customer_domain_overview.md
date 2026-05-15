# Customer Domain Overview

Status: DRAFT - Domain Overview
Domain: customer_domain
Contracts: 01, 03, 04, 05, 06, 07, 08, 09, 10, 15, 17, 20, 21, 24, 25, 27, 28, 31, 35, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Provide the canonical index for customer-domain planning contracts, including naming normalization, ownership boundaries, lineage hierarchy, projection hierarchy, and integration/runtime guardrails.

## 1) File index

- planning/customer/customer_models.md
- planning/customer/customer_history_models.md
- planning/customer/customer_integration_notes.md
- planning/customer/customer_domain_overview.md
- planning/customer/scratch_planning_tables.md (source only)

## 2) Naming normalization

Scratch source wording uses COSTUMER naming.

Formal customer domain naming is:
- customers
- customer_history_records
- customer_id

## 3) Entity map

- Mutable profile entity: customers
- Append-oriented lineage entity: customer_history_records
- Task anchor relationship: tasks.customer_id -> customers.client_id
- Convenience pointer: customers.latest_history_record_id
- Core profile fields: display_name, customer_type, status, primary contact fields, address
- Lookup-support fields: primary_phone_number_normalized, primary_email_normalized

## 4) Source-of-truth hierarchy

Transactional flow:
- Command/orchestration policies transactionally append customer_history_records and update the mutable customers profile row.
- Mutable customer profile rows serve operational reads/UI.
- customer_history_records preserve append-oriented reconstruction lineage.

Truth semantics:
- authoritative lineage: customer_history_records
- mutable customer profile rows are current-state convenience/profile projections over customer history.
- mutable profile projections: customers.display_name, customer_type, status, primary_phone_number, primary_email, primary_phone_number_normalized, primary_email_normalized, address, latest_history_record_id
- task snapshot truth: task contact/address snapshots are task-time records and do not sync backward from customer profile changes

Emission policy:
- customer creation MUST append customer_history_records.
- customer profile/contact/address changes MUST append customer_history_records.
- customer status changes MUST append customer_history_records.
- customer soft deletion/restoration MUST append customer_history_records.
- domain-significant external integration changes MAY emit domain events in future phases.
- direct profile mutation without lineage append is forbidden for domain commands.
- customer events are deferred in this phase.
- customer_history_records are the phase-one lineage mechanism.

## 5) Relationship and boundary summary

- customers are workspace-scoped profile/identity registry records.
- customer/task links are workspace-scoped only.
- cross-workspace links are forbidden.
- customers are not runtime state holders for task/communication/logistics/payment systems.

## 6) Lineage and projection hierarchy

Lineage:
- customer_history_records is append-oriented change history.
- occurred_at captures business change time.
- created_at captures row insertion time.

Projection:
- customers latest pointer and profile fields are mutable convenience state.
- latest pointers are not authoritative truth.
- pointer updates must be transactionally coupled with lineage append.
- profile rows must not be treated as full historical truth.

## 7) Address and contact governance summary

- customer address follows bounded schema (street/post/city/country/municipality/coordinates).
- customer.address is mutable profile data.
- task.address is immutable task-time snapshot context unless corrected by explicit task-domain policy.
- phone/email validation and normalization ownership sits in command/input validation.
- coordinates are optional operational convenience metadata, not legal address truth and not logistics execution authority.
- country and municipality may be normalized later for search/delivery/statistics/regional policy workflows; keep address JSON simple in this phase.

## 8) Soft delete and privacy summary

- customer rows are soft-delete/deactivation compatible.
- deleted customers remain available for privileged historical reconstruction.
- historical tasks remain valid after customer soft deletion.
- hard deletion is out of scope in normal operations.
- GDPR erasure/anonymization/redaction workflows are deferred and must preserve governance boundaries.
- soft deletion is operational lifecycle visibility.
- GDPR erasure/anonymization/redaction is privacy governance.
- these workflows remain separate.
- status=INACTIVE means the customer is not currently active for normal operational use but remains visible according to normal customer query policies.
- is_deleted=true means the customer is removed from normal operational views and is available only through privileged historical/reconstruction workflows.
- status and soft deletion must not drift into duplicate semantics.

## 9) Future compatibility summary

- duplicate detection and customer merge workflows are deferred.
- external linkage to Shopify/POS/messaging/delivery systems is deferred.
- future integrations must keep interoperability metadata separate from lifecycle authority.
- future merge lineage must preserve task continuity and customer history durability.
- preferred merge direction is canonical-customer redirection/alias semantics with lineage append.
- avoid destructive hard rewrites as default merge strategy.
- for future customer_external_links lifecycle semantics, active external link = unlinked_at IS NULL.

Prefix map:
- cus -> customers
- chr -> customer_history_records

Prefix governance note:
- prefixes support client_id generation, debugging, observability, tracing, exports, and replay tooling.
- customer prefixes should be included in future global prefix index/base planning maps.

## 10) Clarification checklist before implementation

1. Should customer_history_records use a bounded enum for change_type in phase one?
2. Should any phone/email uniqueness be policy-scoped per workspace in phase one, or fully deferred?
3. Which GDPR strategy is expected first for historical rows: redaction, anonymization, or hybrid?
4. Should future merge workflows prefer canonical-customer redirection or hard relationship rewrites with lineage append?

Answer:
Yes.
Use bounded enum governance in phase one.

Answer:
Fully defer hard uniqueness.
Add indexed normalized fields for lookup/dedup support, but no uniqueness constraints yet.

Answer:
Hybrid future strategy:
- profile anonymization
- selective redaction of sensitive history payload/change_summary fields
- governed by contract 35

Do not implement GDPR erasure workflows now.

Answer:
Prefer canonical-customer redirection/alias semantics with lineage append.
Avoid destructive hard rewrites as the default strategy.
