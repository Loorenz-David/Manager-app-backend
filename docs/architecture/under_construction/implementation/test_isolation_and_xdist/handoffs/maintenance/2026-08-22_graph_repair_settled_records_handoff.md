---
plan: 3
role: maintenance
round: 1
state: completed
date: 2026-08-22
actor: Codex
---

# Architecture-graph repair of three settled records

The graph had three records pointing at old locations after phase 3 moved the test code, and one of those records also described a template-reuse rule that the code had deliberately removed. I verified the current symbols in the working tree, repaired the five moved evidence spans, and left the unchanged fixture span alone. I replaced the stale edge record with the rule the code implements and completed its required second review pass. Nothing remains for the owner to decide.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

## Record: `node:infrastructure-test-database-isolation`

### Claim and source verification

The record describes the per-process disposable PostgreSQL lifecycle, including startup, destructive cleanup, and the pytest fixture seam. I verified `DatabaseIsolation.start` at `app/tests/database_isolation.py:234-252`, `_drop_database_if_exists` at `app/tests/database_isolation.py:539-565`, and the `isolated_database` fixture at `app/tests/conftest.py:22-37`. The fixture span was unchanged and was confirmed without modification; the separate `assert_disposable_database` function is present at `app/tests/database_isolation.py:148-175` and remains the guard called by the destructive path.

### Operation

Applied `archgraph_repair_anchors` to evidence indexes 0 and 1 only:

- `DatabaseIsolation.start`: `167-185` → `234-252`
- `DatabaseIsolation._drop_database_if_exists`: `463-489` → `539-565`

The prior addresses are preserved under `metadata.evidenceHistory`. The record remains `human_confirmed`; no summary or topology change was made.

## Record: `node:test-database-isolation-contract`

### Claim and source verification

The record describes the bounded worker-name contract, asserted template migration, and development-database preservation. I verified `resolve_worker_database_name` at `app/tests/database_isolation.py:103-112`, `_migrate_and_assert` at `app/tests/database_isolation.py:449-490`, and `test_dev_database_counts_are_untouched` at `app/tests/integration/infrastructure/test_database_isolation.py:614-647`.

### Operation

Applied `archgraph_repair_anchors` to all three evidence entries:

- `resolve_worker_database_name`: `46-55` → `103-112`
- `DatabaseIsolation._migrate_and_assert`: `364-414` → `449-490`
- `test_dev_database_counts_are_untouched`: `277-311` → `614-647`

The prior addresses are preserved under `metadata.evidenceHistory`. The record remains `human_confirmed`; no summary or topology change was made.

## Record: `edge:infrastructure-test-database-isolation--configured_by-->test-database-isolation-contract`

### Claim and source verification

The edge claims that the isolation lifecycle is governed by the test database isolation contract. I verified `DatabaseIsolation._ensure_template` at `app/tests/database_isolation.py:398-428`. The implementation reuses an existing template only when it has the disposable marker, its Alembic head equals the head derived at runtime from the migration scripts, it contains every required public table, and it lacks the legacy baseline column; otherwise it drops and rebuilds the template. There is no public-table count comparison or expected-count constant in this path.

### Operation: reject-and-re-record

The settled edge was deleted with a previewed and client-approved maintenance change because its immutable evidence summary falsely required a public-table count and expected constants. The same edge ID was then re-recorded with the current evidence span and returned to the review queue as `ai_inferred`.

### Operation: second-pass confirmation

The re-recorded edge was independently read through `archgraph_get_review_item`, its source file and current span were present, and the known `configured_by` warning was evaluated against the owner-authorized override. The corrected record was previewed and then promoted in a separate review decision. It is now `human_confirmed`.

### Corrected summary

Replaced:

> An existing template is reused only when it carries the marker, its Alembic head and public-table count match the expected constants, and it has no legacy baseline_source column; otherwise it is dropped and rebuilt. A marker-less template that still has tables is refused outright rather than replaced, while a marker-less empty shell is absorbed.

With:

> An existing template is reused only when it carries the disposable marker, its Alembic head equals the head derived at runtime from the migration scripts, it contains every required public table, and it does not carry the legacy baseline column; otherwise it is dropped and rebuilt.

## Final `archgraph_status`

- Nodes: **194**
- Edges: **291**
- Pending reviews: **0**
- Diagnostics: **0**
- `staleNodeCount`: **0**
- Revision: `e7ab5b2aa34ebd309766071c010d469ffd3f7151cb346c6669a0854d6911f756`

Counts are unchanged at 194/291. The temporary edge count of 290 occurred only between the authorized delete and re-record operations; the final topology is unchanged.

## Full write perimeter

Graph state and audit records:

- `.archgraph/architecture.yml` — anchor repairs and the delete/re-record/confirmation lifecycle.
- `.archgraph/changes/2026-08-22T10-56-56-190Z--69cb0d.yml` — anchor-repair audit.
- `.archgraph/changes/2026-08-22T10-57-11-305Z--cd312d.yml` — client-approved stale-edge deletion audit.
- `.archgraph/reviews/2026-08-22T10-58-10-846Z--422a41.yml` — second-pass edge confirmation audit.

Handoff:

- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/handoffs/maintenance/2026-08-22_graph_repair_settled_records_handoff.md`

No file under `app/` was edited. No plan, master plan, intention, prompt, node, or unrelated edge was written.
