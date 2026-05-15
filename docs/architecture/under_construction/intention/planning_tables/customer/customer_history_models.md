# Customer History Models Plan

Status: DRAFT - Initial Structured Split
Domain: customer_history
Contracts: 01, 03, 06, 08, 21, 24, 25, 35, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define append-oriented customer profile change lineage for reconstruction-safe operational history, audit compatibility, and future correction/replay workflows.

## Naming correction from scratch source

The scratch source references COSTUMER_HISTORY_RECORD.

This formal planning uses:
- customer_history_records

## 1) Core table

### 1.1 customer_history_records

Columns:
- client_id: String(64) PK, prefix chr
- workspace_id: FK workspaces.client_id, not null, indexed
- customer_id: FK customers.client_id, not null, indexed
- change_type: Enum(customer_history_change_type), not null, indexed
- occurred_at: DateTime(tz), not null, indexed
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- payload: JSON, nullable
- change_summary: String(512), nullable
- correlation_id: String(64), nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, customer_id, occurred_at)
- INDEX(workspace_id, customer_id, created_at)

## 2) Enums

### 2.1 customer_history_change_type
- CREATED
- PROFILE_UPDATED
- CONTACT_UPDATED
- ADDRESS_UPDATED
- STATUS_UPDATED
- SOFT_DELETED
- RESTORED
- MERGED
- REDACTED
- ANONYMIZED
- CORRECTION
- RETRACTION

Bounded enum governance:
- bounded enum governance starts in phase one.
- future values may be added through migrations when taxonomy matures.
- avoid free-string drift in history lineage.

## 3) Ownership and semantics

Lineage semantics:
- customer_history_records are append-oriented lineage rows.
- rows represent profile/contact/address change history.
- lineage rows are not mutable profile state.
- corrections should append compensating lineage rather than destructively rewriting prior rows.

Timeline semantics:
- occurred_at means when the customer change happened.
- created_at means when the lineage row was inserted.
- created_at must not be overloaded as event occurrence time.

Change payload semantics:
- payload should carry structured change context needed for reconstruction/correction.
- change_summary is human-oriented operational context.
- correlation_id may support replay/idempotency/reconciliation grouping, but is not primary identity.

Payload governance:
- preferred payload shape:
	- before: {}
	- after: {}
	- changed_fields: []
	- reason: string
- before and after contain bounded snapshots of changed fields where needed.
- changed_fields enumerates modified customer profile fields.
- reason captures correction/retraction/update context where applicable.
- payload must not become arbitrary hidden customer profile state.
- for REDACTED and ANONYMIZED changes, payload.before should not preserve raw personal data unless explicitly allowed by privacy governance.

Privacy-sensitive history note:
- payload and change_summary may contain personal data.
- both fields must remain compatible with future redaction/anonymization workflows.
- change_summary must not be treated as safe/non-sensitive metadata.
- free-text summaries may require privacy governance later.
- REDACTED and ANONYMIZED change records must avoid storing the sensitive values that were removed.
- privacy-governed history records should avoid preserving raw removed values unless explicitly allowed by privacy governance.

Soft-delete lineage note:
- customer_history_records are truth-bearing lineage records.
- customer_history_records should not be soft-deleted during normal operations.
- normal cleanup must not remove or hide lineage rows.
- if visibility suppression is required, it must be treated as correction, retraction, or privacy-governance metadata and handled through explicit lineage policy.
- soft deletion of lineage rows is exceptional and must be treated as correction/retraction metadata, not normal cleanup.
- hard deletion is forbidden in normal operations.
- replay systems must define whether soft-deleted lineage rows are included, excluded, or compensated.
- correction/retraction should prefer append-oriented lineage.

Latest pointer coupling rule:
- updates to customers.latest_history_record_id must be transactionally coupled with the append operation that created the new history row.
- latest pointer updates must not happen independently from lineage append.

Emission policy:
- customer creation MUST append customer_history_records.
- customer profile/contact/address changes MUST append customer_history_records.
- customer status changes MUST append customer_history_records.
- customer soft deletion/restoration MUST append customer_history_records.
- direct customer profile mutation without history append is forbidden for domain commands.
- domain-significant external integration changes MAY emit domain events in future phases.

Transactional coupling rule:
- profile row mutation, history append, latest pointer update, updated_at, and updated_by_id must be committed in the same transaction.

## 4) Relationship map

- customers (1) -> (*) customer_history_records
- workspaces (1) -> (*) customer_history_records

## 5) Scope boundary

In scope:
- append-oriented customer profile/contact lineage
- replay-safe customer reconstruction support
- audit-compatible change chronology

Out of scope:
- mutable customer profile row ownership
- communication runtime logs
- messaging thread lifecycle

## 6) Operational rules

- workspace_id must match customer.workspace_id.
- cross-workspace history links are forbidden.
- history rows are append-oriented and must remain reconstruction-safe.
- soft-delete consistency must hold: is_deleted=false with deleted_at!=NULL is invalid, and is_deleted=true with deleted_at IS NULL is invalid.

No-cascade-delete rule:
- customer lineage and task relationships must not cascade-delete from customers or workspaces.
- use RESTRICT / NO ACTION semantics for historical durability.

## 7) Deferred runtime notes

- do not place websocket/message delivery state into customer_history_records.
- do not place queue/process runtime internals into lineage rows.

## 8) Future integration notes

- future customer merge workflows may append merge-linkage lineage records.
- future GDPR governance may require policy-governed anonymization/redaction workflows that preserve operational reconstruction boundaries.
- future replay/recompute systems may consume customer_history_records with customer/task lineage for deterministic rebuilds.
- soft deletion is operational lifecycle visibility.
- GDPR erasure/anonymization/redaction is privacy governance.
- these are separate workflows and must be governed separately.

## 9) Risks and protections

Risks:
- rewriting lineage destructively and breaking replay correctness.
- treating latest pointers as authoritative truth.

Protections:
- append-oriented lineage contract.
- explicit latest-pointer-as-projection rule.
- compensating correction policy.

## 10) Clarifications before implementation

1. Should change_type use bounded enum governance in phase one, or remain string-based until real change taxonomy stabilizes?
2. Should payload favor before/after snapshots, patch-style changes, or both?
3. Should privileged correction flows require explicit correction_type/retraction metadata in this phase?

Answer:
Use bounded enum governance in phase one.

Answer:
Use a bounded before/after + changed_fields payload structure.

Answer:
Yes.
Correction and retraction flows should use explicit change_type values and include reason metadata in payload.
