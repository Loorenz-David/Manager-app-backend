# Customer Integration Notes

Status: DRAFT - Integration Boundary Notes
Domain: customer_integrations
Contracts: 01, 03, 08, 21, 24, 35, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Document integration boundaries for the customer domain with task orchestration, privacy governance, and future external customer systems while preserving registry/profile ownership.

## 1) Task domain integration

- tasks may reference customers through tasks.customer_id.
- customers are profile anchors; tasks own task-time operational snapshots.
- task-level phone/email/address fields remain task-time snapshots.
- customer profile updates must not retroactively mutate historical task snapshots.
- historical task reconstruction relies on task lineage plus snapshots, not live customer row only.
- task-time customer snapshots may be corrected only through task-domain correction policies, not automatically through customer profile updates.

## 2) Contact and communication boundary

- customer phone/email fields are registry contact data.
- customer rows do not own communication runtime pipelines.
- communication logs, messaging threads, and delivery receipts are out of scope in this phase.
- future communication systems may reference customers without transferring customer profile authority.

## 3) Privacy and GDPR boundary

- customers may carry personal data and must remain privacy-aware.
- GDPR erasure/anonymization/redaction workflows are deferred.
- future privacy workflows must preserve required historical durability and legal/audit boundaries.
- privacy erasure and operational reconstruction can require separate governance workflows.
- do not implement GDPR erasure tables in this phase.
- soft deletion is operational lifecycle visibility.
- GDPR erasure/anonymization/redaction is privacy governance.
- these are separate workflows.

## 4) External system compatibility

Potential future integrations:
- Shopify customers
- external order/POS systems
- messaging systems
- delivery systems

Integration rule:
- future external linkage fields are interoperability metadata only.
- external linkage metadata is not synchronization authority, lifecycle authority, or orchestration truth.

## 5) Merge and dedup compatibility

- duplicate customer identities are expected in real operations.
- duplicate detection/merge flows are deferred.
- future merge workflows must preserve:
  - task relationship continuity
  - customer history lineage durability
  - replay-safe reconstruction behavior
- do not create merge tables in this phase.
- future merge workflows should prefer canonical-customer redirection and alias/linkage semantics.
- avoid destructive hard relationship rewrites and duplicate deletion without lineage as default behavior.

## 6) Runtime separation guardrails

Do not place on customers:
- active task counters
- communication runtime states
- delivery/runtime execution states
- websocket presence
- queue/process runtime artifacts

These concerns belong to:
- task orchestration domain
- communication systems
- logistics systems
- future runtime/projection domains

## 7) Emission and lineage policy

- customer creation MUST append customer_history_records.
- customer profile/contact/address changes MUST append customer_history_records.
- customer status changes MUST append customer_history_records.
- customer soft deletion/restoration MUST append customer_history_records.
- domain-significant external-integration changes MAY emit domain events in future phases.
- latest_history_record_id is convenience projection, not lineage authority.
- full customer reconstruction always traverses customer_history_records.
- customer events are deferred in this phase.
- customer_history_records are the phase-one lineage mechanism.

## 8) Operational durability rules

- all integrations must preserve workspace boundaries.
- cross-workspace customer/task links are forbidden.
- customer lineage and task relationships must not cascade-delete from customers or workspaces.
- use RESTRICT / NO ACTION semantics for historical durability.
- soft deletion of lineage rows is exceptional and correction-oriented.

## 9) Future external links direction

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
- active external link = unlinked_at IS NULL.

## 10) Clarifications before implementation

1. Should future external linkage prefer a single minimal external_ref model or provider-specific linkage records?
2. Should privacy workflows prefer irreversible anonymization for historical rows over selective redaction in some jurisdictions?
3. Should customer merge commands emit both customer_history_records and domain events when merge support is introduced?
