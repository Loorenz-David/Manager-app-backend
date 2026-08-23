---
role: maintenance
date: 2026-08-23
actor: Codex
authorization: D28
---

# Architecture-graph queue adjudication handoff

## Dispositions verified at source

The opening queue contained exactly seven items, as authorized by D28. Each cited
path and span was opened directly from the working tree.

1. `edge:domain-item-economics--contains-->domain-item-economics-typical-filters` — **approved**. `app/beyo_manager/domain/item_economics/typical_filters.py:1–333` contains the pure typical-time rules inside the Item Economics domain package.
2. `node:domain-item-economics-typical-filters` — **approved**. `app/beyo_manager/domain/item_economics/typical_filters.py:1–333` contains `TypicalFilterSpec`, evidence predicates, resolution policies, reconciliation, fallback, and median logic using domain values and a local protocol.
3. `edge:test-item-economics-domain-purity-guards--verifies-->domain-item-economics-typical-filters` — **approved**. `app/tests/unit/domain/item_economics/test_domain_purity.py:26–29` scans the domain package for forbidden SQLAlchemy and model-table dependencies.
4. `node:test-item-economics-domain-purity-guards` — **approved**. `app/tests/unit/domain/item_economics/test_domain_purity.py:13–23` and `:26–29` contain the package-wide identity-hashing and persistence-dependency guards.
5. `edge:source-symbol-working-section-typical-times-statement-narrowing--implements-->projection-working-section-typical-times` — **approved**. `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py:28–142` contains the ordered-filter projection statement and its preserved no-spec branch.
6. `node:source-file-working-section-typical-item-filter` — **approved**. `app/beyo_manager/services/queries/working_sections/_typical_item_filter.py:13–49` contains `build_item_match`, including range `IS NOT NULL` predicates and the NULL-safe conjunction.
7. `node:source-symbol-working-section-typical-times-statement-narrowing` — **rejected for repair**. Its production evidence at `get_working_section_typical_times.py:28–142` was accurate, but its test evidence cited `test_typical_times_narrowing.py:199–224`, which is now a different test. The claimed test begins at line 232 and its verified body is `:232–253`.

The full six-promote / one-reject preview was read before application. The review
batch was applied under the owner authorization recorded as D28. The rejected item
was re-recorded with the same id in one `archgraph_apply_changes` batch and remains
pending; it was not approved by this session.

## Stale nodes investigated

- `projection-item-economics-task-production-time`: the source link to
  `app/beyo_manager/domain/item_economics/budget_division.py`, symbol
  `_governing_step`, lines 188–208, has a stale content hash. Its other two source
  links are current.
- `domain-item-economics-typical-filters`: the source link to
  `app/beyo_manager/domain/item_economics/typical_filters.py`, symbol
  `_optional_values`, lines 78–88, has a stale content hash.

Both files and spans still exist. Clearing either stale flag requires a separately
authorized maintenance re-accept/re-anchor of that specific source link after
source verification. No deprecation, removal, unlink, link, or anchor repair was
performed; D28 did not authorize those mutations.

## Measured post-session state

At the final status check: **198 nodes / 298 edges**, revision
`364223242014a733822256e445824b7160bcda2e1cc4a6e3f9e9d930b5419a47`, **1 pending / 2
stale / 0 diagnostics**. The single pending item is the corrected re-record of
`node:source-symbol-working-section-typical-times-statement-narrowing`.

## Write perimeter

The graph changed `.archgraph/architecture.yml` and the review audit record
`.archgraph/reviews/2026-08-23T06-03-04-540Z--061a53.yml`. Documentation changes are
this handoff and the graph measurement line in `master_plan.md`. The expected
untracked `.archgraph/contexts/` directory was not rebuilt or staged. No application
code or tests were changed by this session, and no tests were run.

The worktree also contained unrelated pre-existing modifications in phase-2 files;
they were left untouched and are not included in the maintenance commit.

## Commit

Primary maintenance commit SHA: to be recorded after the explicit-path commit.
