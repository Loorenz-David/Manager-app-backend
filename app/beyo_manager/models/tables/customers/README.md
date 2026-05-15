# Customers Domain — Table Guide

## Tables in this folder

| File | Table | Prefix | Purpose |
|---|---|---|---|
| `customer.py` | `customers` | `cus` | Workspace-scoped customer identity and contact registry |
| `customer_history_record.py` | `customer_history_records` | `chr` | Immutable append-oriented profile-change lineage |

> **Naming note:** the original scratch source used "costumer". All formal naming uses `customer` / `customers`.

---

## Boundary rules

Customers are **registry/profile anchors** — not runtime state containers. Do not add to customers:
- active-task counters
- communication runtime state
- delivery / logistics runtime state
- websocket presence fields
- payment / accounting ownership

---

## `customers` — key rules for commands

### Circular FK
`customers.latest_history_record_id` → `customer_history_records.client_id` is declared with `use_alter=True`. This is a **convenience pointer only** — it is not the reconstruction source. Full history traversal must use `customer_history_records`.

Pointer updates must be **transactionally coupled** with the history row append.

### Mandatory history coupling
Every domain command that mutates a customer **must** append a `customer_history_records` row in the same transaction. Mutations without a history row are forbidden.

Commands that require history appends:
- customer creation → `CREATED`
- profile / contact / address changes → `PROFILE_UPDATED`, `CONTACT_UPDATED`, `ADDRESS_UPDATED`
- status changes → `STATUS_UPDATED`
- soft deletion → `SOFT_DELETED`
- restoration → `RESTORED`
- merge / redact / anonymize → `MERGED`, `REDACTED`, `ANONYMIZED`
- corrections / retractions → `CORRECTION`, `RETRACTION`

### Contact fields
- `primary_phone_number` and `primary_email` are raw operational input values. Validation and normalization belong to command/input validation.
- `primary_phone_number_normalized` / `primary_email_normalized` are lookup/dedup support fields. They are **not unique constraints** in this phase.
- Normalization must not force false validity for incomplete or local-format phone numbers.

### Address shape (JSON schema)
```json
{
  "street_address": "string",
  "post_number": "string",
  "city": "string",
  "country": "string",
  "municipality": "string",
  "coordinates": { "lat": 0.0, "lng": 0.0 }
}
```
Fields are optional unless a specific command flow requires them.

### Soft delete vs status vs privacy
- `is_deleted=true` → removed from normal operational views; available only via privileged reconstruction workflows.
- `status=INACTIVE` → not currently active but visible under normal query policies.
- GDPR erasure / anonymization / redaction is a **separate privileged flow** — not ordinary soft deletion.
- `is_deleted=false` with `deleted_at != null` is an invalid state. Enforce consistency.

### Task snapshots
`tasks` stores its own `address`, `primary_phone_number`, `primary_email` at task-creation time. **Customer profile edits must never retroactively overwrite historical task snapshots.**

### Uniqueness strategy
Do not enforce global uniqueness on display_name or primary contact fields. Duplicate detection and merge workflows are deferred future flows.

---

## `customer_history_records` — key rules

- Append-only. Do not update existing history rows.
- `occurred_at` is the business-event timestamp; `created_at` is the system-write timestamp.
- `payload` (JSON) should capture the before/after state snapshot for the change type.
- `correlation_id` links related events across a distributed transaction or command.
- Soft delete on history rows is exceptional — only for corrections / retractions with a corresponding append.

---

## No-cascade-delete

FK delete behavior is RESTRICT on all relationships. Deleting a customer or workspace while history rows exist must raise a DB error.

---

## Deferred

- `customer_external_links` table (Shopify, POS, external order systems)
- Merge / alias / deduplication tables
- Communication logs and multi-contact support
