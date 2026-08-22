---
plan: 3
role: maintenance
round: 2
state: completed
date: 2026-08-22
actor: Codex
---

# One-record architecture-graph correction

I corrected the one architecture record whose description omitted the safety behavior for a
marker-less database. The code confirms that an empty shell may be absorbed, but a marker-less
database containing public tables is refused rather than replaced. The record was removed,
re-recorded with that complete rule, and confirmed again. Nothing needs the owner to decide.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

## Code verification: `DatabaseIsolation._ensure_template`

I read `app/tests/database_isolation.py:398-428`. If the template does not exist, the lifecycle
creates it, marks it, and migrates it. If it exists without the disposable marker, an empty public
schema is dropped, recreated, marked, and migrated; any public tables cause
`UnsafeDatabaseError`, so the database is refused and not rebuilt. A marked template is reused
only when its runtime-derived Alembic head matches, all required public tables are present, and
the legacy `baseline_source` column is absent; otherwise that marked template is dropped and
rebuilt.

## Operation 1 — delete

I previewed and applied one client-approved maintenance deletion:

`edge:infrastructure-test-database-isolation--configured_by-->test-database-isolation-contract`

No incident edges were cascaded. Audit record:
`.archgraph/changes/2026-08-22T12-04-32-029Z--8cca8a.yml`.

## Operation 2 — re-record

I re-recorded the same edge ID with the same source, target, relationship type, description,
confidence, and `_ensure_template` evidence address. The corrected evidence summary was:

> An existing template is reused only when it carries the disposable marker, its Alembic head equals the head derived at runtime from the migration scripts, it contains every required public table, and it lacks the legacy baseline column; a marked template failing any of those is dropped and rebuilt. A marker-less template is not rebuilt by default — it is refused outright with UnsafeDatabaseError if it still has public tables, and absorbed only if it is an empty shell.

It replaced:

> An existing template is reused only when it carries the disposable marker, its Alembic head equals the head derived at runtime from the migration scripts, it contains every required public table, and it does not carry the legacy baseline column; otherwise it is dropped and rebuilt.

The re-record passed a dry-run with no skips or diagnostics, then was written as `ai_inferred`.
The expected conflicting-canonical-relationship warning was evaluated: the separate
`configured_by` edge to `configuration-shipped-pytest-parallel-default` is legitimate under the
prior review r4 decision that this relationship type does not impose cardinality.

## Operation 3 — second-pass confirmation

I read the re-recorded item back with `archgraph_get_review_item`; its file, symbol, span, and
corrected summary were present. I previewed one `promote` decision with no warnings and applied it
through the client approval gate. The edge is now `human_confirmed`. Review audit record:
`.archgraph/reviews/2026-08-22T12-05-10-886Z--9566d3.yml`.

## Stale inline reference reported, not fixed

The separate node record
`node:infrastructure-test-database-isolation` still says that
`_drop_database_if_exists` passes its result to `assert_disposable_database (lines 81-107)`.
The current function span is `app/tests/database_isolation.py:148-175`; the call site remains
`app/tests/database_isolation.py:539-565`. Because the stale line range is embedded inside an
immutable summary, anchor repair cannot correct it. I recommend leaving it for now rather than
spending a third same-day re-record on a prose-only inline reference; route it separately if the
coordinator decides the accuracy benefit outweighs that churn.

## Final `archgraph_status`

- Nodes: **194**
- Edges: **291**
- Pending reviews: **0**
- Diagnostics: **0**
- `staleNodeCount`: **0**
- Revision: `cec60a24005ac83da1e396070b36eac1dc3b963a8f1e7526dded2dc5e0225eb9`

The final counts match the required 194/291/0/0. No test was run; the prompt's L4 evidence budget
was zero, and the correction was verified by reading the implementation against the record.

## Full write perimeter

- `.archgraph/architecture.yml` — one edge deletion, one edge re-record, and the final confirmed edge state.
- `.archgraph/changes/2026-08-22T12-04-32-029Z--8cca8a.yml` — client-approved deletion audit.
- `.archgraph/reviews/2026-08-22T12-05-10-886Z--9566d3.yml` — client-approved promotion audit.
- `docs/architecture/under_construction/implementation/test_isolation_and_xdist/handoffs/maintenance/2026-08-22_graph_repair_marker_less_clause_handoff.md` — this handoff.

No source file under `app/` was edited. No node, unrelated edge, project document, plan, or review
item outside this one edge was written.
