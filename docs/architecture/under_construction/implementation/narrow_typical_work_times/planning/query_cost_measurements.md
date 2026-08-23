# Phase-2 query-cost measurements

Measured 2026-08-22 on the disposable PostgreSQL test database with
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`. The committed harness is
`app/tests/integration/services/queries/working_sections/_narrowing_seed.py`.

Seed cardinalities are exact for every row: one live working section, one completed
step per task, 20 distinct primary-item categories, all closed one day ago inside the
90-day window. Every section has at least five section-wide qualifying groups; the
single-task row is intentionally a shape probe and therefore has no typical value.
The new statement uses one outer `spec_index` cross join and active-primary item joins.

| shape | statement | tasks | specs | planning ms | execution ms | top node | cost | note |
|---|---:|---:|---:|---:|---:|---|---:|---|
| single task | current | 1 | 0 | 0.204 | 0.061 | Aggregate | 16.42 | copy: current is spec-blind |
| 20 tasks × 5 categories | current | 20 | 5 | 0.091 | 0.059 | Aggregate | 16.42 | copy: current is spec-blind |
| 20 tasks × 10 categories | current | 20 | 10 | 0.099 | 0.060 | Aggregate | 16.42 | copy: current is spec-blind |
| 20 tasks × 20 categories | current | 20 | 20 | 0.098 | 0.068 | Aggregate | 16.42 | copy: current is spec-blind |
| no-spec | current | 20 | 0 | 0.101 | 0.060 | Aggregate | 16.42 | copy: current is spec-blind |
| single task | new | 1 | 0 | 0.096 | 0.037 | Aggregate | 16.42 | HC-4 no-spec branch |
| 20 tasks × 5 categories | new | 20 | 5 | 0.460 | 0.296 | Aggregate | 34.01 | outer attachment |
| 20 tasks × 10 categories | new | 20 | 10 | 0.964 | 0.751 | Aggregate | 37.25 | outer attachment |
| 20 tasks × 20 categories | new | 20 | 20 | 1.396 | 1.466 | Aggregate | 49.39 | outer attachment |
| no-spec | new | 20 | 0 | 0.113 | 0.087 | Aggregate | 16.42 | copy: HC-4 equals current shape |
| 50 tasks × 20 categories | new | 50 | 20 | 1.003 | 2.758 | Aggregate | 49.39 | API ceiling, not a realistic page |

The five constant-by-construction cells are the five current-statement rows plus the
new no-spec row: the current statement does not inspect specs, and the new no-spec
branch returns the pre-refactor statement byte-for-byte. The measurements are
observational only; D26 sets no performance threshold for this phase. Nothing was an
order of magnitude outside the expected small-page range in this disposable seed.

The seeding is cumulative: `collect_measurement_matrix` uses one database session, does
not clean up between cases, and measures the rows in the table order shown above (positions
1 through 11). Each workspace's seed cardinality is exact, but later rows are measured
against the table containing every earlier workspace's rows. The harness did not run
`ANALYZE`, so `cost` is PostgreSQL's default planner estimate, not an observed runtime
quantity; this is why the identical query reports `16.42` for both the 1-task and 20-task
current-statement seeds. The harness requests `BUFFERS`, but records no buffer values in
the document. Consequently, the 1.9× execution-time difference for the 50-task ×
20-category row is undecidable from this document: it may reflect spec fan-out, table
growth from cumulative seeding, or both.
