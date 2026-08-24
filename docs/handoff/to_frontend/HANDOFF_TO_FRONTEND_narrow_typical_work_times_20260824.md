# HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_narrow_typical_work_times_20260824`
- Created at (UTC): `2026-08-24`
- Status: backend closeout; frontend action required
- Scope: item-aware typical work times on production-time, budget-allocations, price-scenario,
  and worker task-step cards
- This is a new dated handoff. No published handoff was edited.

## 1. `ALLOCATION_METHOD` v2

`ALLOCATION_METHOD` is now `static_proportional_section_v2`.

Every task is now evaluated under the new rule; allowances are **eligible** to change wherever
item-category narrowing changes the relative section weights. Many tasks remain numerically
identical: primary items with no `item_category_id` (empty spec); tasks reconciling to
`section_wide_uniform`; categories whose narrowed ratios coincide with the section-wide ratios.
**The contract changes even where an individual numeric result does not.**

Frontend action: accept the v2 derivation label and key any explanatory copy from the served
`allocation_method`. Do not infer that an unchanged allowance means the old contract is still in
effect.

## 2. New fields, nullability, and defaults

All keys below are always present on the surfaces that publish them. A default describes the
fallback serializer shape; it is not permission for the client to omit or invent the key.

- `typical_basis` is **non-nullable**, always present, and defaults to
  `"insufficient_sample"` when no selected typical is available. It names the population behind
  `typical_worker_seconds`: `"item_narrowed"`, `"section_wide"`, or
  `"insufficient_sample"`.
- `sample_count` is **non-nullable**, always present, and defaults to `0`. It counts the
  population named by `typical_basis`, not necessarily the narrowed population.
- `narrowed_sample_count` is **non-nullable**, always present, and defaults to `0`. It is raw
  same-item-category evidence and appears in production-time's per-section `typical` object.
- `section_sample_count` is **non-nullable**, always present, and defaults to `0`. It is raw
  section-wide evidence and appears in production-time's per-section `typical` object.
- `typical_resolution` is **non-nullable**, always present, and defaults to the complete
  section-wide/zero-count object shown below.
- `applied_filter` is the one **nullable** new field. Its key is always present; its value is
  `null` when the task's primary item has no category, or there is no primary item.

The task-level object is identical on production-time, every budget-allocations task entry, and
price-scenario's `typical` block:

```json
{
  "typical_resolution": {
    "task_typical_basis": "section_wide_uniform",
    "reconciliation_method": "uniform_basis_v1",
    "comparability_profile": "primary_item_category_v1",
    "applied_filter": null,
    "participating_section_count": 0,
    "sections_by_basis": {
      "item_narrowed": 0,
      "section_wide": 0,
      "insufficient_sample": 0
    }
  }
}
```

Every nested key is non-nullable except `applied_filter`:

- `task_typical_basis` defaults to `"section_wide_uniform"`.
- `reconciliation_method` defaults to `"uniform_basis_v1"`.
- `comparability_profile` defaults to `"primary_item_category_v1"`.
- `participating_section_count` defaults to `0`.
- `sections_by_basis` defaults to all three named counts at `0`.

When `applied_filter` is not null, it is the filter actually derived for the task. In V1 that is
normally `{"item_category_ids": ["…"]}`. Filter axes that are not active are omitted inside this
object; the `applied_filter` key itself is never omitted.

Surface placement:

- Production-time: `sections[].typical` gains `typical_basis`, `narrowed_sample_count`, and
  `section_sample_count`; its existing `sample_count` now follows the selected basis. The task
  root gains `typical_resolution`.
- Budget-allocations: each task entry gains `typical_resolution`; each `steps[]` row gains
  `typical_basis` and `sample_count`. The two raw evidence counts are deliberately not repeated on
  every list row.
- Price-scenario: the existing `typical` object gains `typical_resolution`.

## 3. `is_estimated`: no frontend rule change, but narrowing can move the value

Nothing to change; the definition is now written down. `is_estimated` remains true when there are
zero participating sections, or when layer 2 fired for at least one participating section. The
zero-section disjunct is retained, so the clarified definition does not reverse any existing
value. Reconciling to `section_wide_uniform` alone does **not** set the flag.

`sections_total` remains the participating-section count. `sections_without_sample` remains the
count of **participating** sections whose **selected** typical is `null` or `<= 0`—the sections
where layer 2 fired. It does not mean "sections without a narrowed sample"; a usable selected
section-wide value is not counted merely because its narrowed sample was thin.

There is one important before/after qualification: `is_estimated` is unchanged under
`section_wide_uniform`, and it moves under `item_narrowed_uniform` wherever the narrowed and
section-wide medians differ in usability. For example, usable same-category history can replace
an unusable section-wide zero and correctly move the flag from `true` to `false`. That is the
feature working, not a regression and not a new client rule.

## 4. Do not implement a narrowed-zero task branch

`typical_basis: "item_narrowed"` beside `typical_worker_seconds: 0` is **unreachable on every
task surface**. Task economics requires a usable narrowed median greater than zero; otherwise the
whole participating task reconciles to section-wide figures, and excluded sections independently
follow the same usable-narrowed rule.

The reachable zero-statistic form is `typical_basis: "section_wide"` beside
`typical_worker_seconds: 0`. A zero is a statistic and is never published as
`insufficient_sample`. Render the served zero; do not convert it to null or "no typical yet".

The future analytics policy is deliberately different: an explicit narrowed question may
honestly return an item-narrowed zero. That future surface is not a task surface and is not live
yet.

## 5. `/working-sections/typical-times` is unchanged

`GET /api/v1/working-sections/typical-times` has no new query parameters and no response change.
It remains a task-free benchmark surface. Item-category narrowing reaches task screens
automatically through their task-scoped endpoints; do not add a manual category filter to this
route.

## 6. Deferred analytics difference

`/statistics/typical-times` does not exist yet. When it ships, it will answer an explicit filtered
question under `ANSWER_AS_ASKED`, while task economics uses `BROADEN_TO_SECTION` and uniform task
reconciliation. The same evidence can therefore legitimately produce `540` for task economics
and `null` for analytics. One is the usable task figure after the permitted fallback; the other
is the honest answer that the explicitly requested population is insufficient.

Do not build against, announce, or call the deferred endpoint from this handoff. Its future return
path is a route and serializer over the already shared evidence engine.

## 7. Worker task-step cards: supersede one source instruction

This section supersedes `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`
§Worker task-step cards. This supersedes **exactly one instruction** in that section.

The cards' fallback typical now comes from `budget-allocations`
`steps[].typical_worker_seconds`. It is already present in the `no_budget` state and is now
item-aware. Delete the bootstrap `typical-times` fetch, cache, and join from the card path.

Keep one batched
`GET /api/v1/item-economics/tasks/budget-allocations?task_ids=…` call per visible feed page, with
1–50 task ids. It remains the cards' single economics source. The separate
`/working-sections/typical-times` endpoint remains available as the task-free benchmark described
above, but the cards no longer consume it.

Why: a client-cached generic typical beside item-aware card figures could contradict
production-time's degraded state for the same task and section. Removing that join closes the
last place cross-surface disagreement could survive.

**Cost:** remove one bootstrap request plus its client cache and join. No replacement request is
added; the existing one-batch-per-feed-page budget-allocations call remains, capped at 50 task ids.

## 8. Frontend validation checklist

- Confirm v2 is accepted even on a fixture whose numeric allowances match v1.
- Confirm all new keys above are present on no-budget and insufficient-sample responses, including
  the complete default `typical_resolution` object.
- Confirm `applied_filter: null` for both a category-less primary item and a task with no primary
  item.
- Confirm a usable item-narrowed task and a section-wide task render the served basis and count
  without reverse-engineering them.
- Confirm `section_wide` plus `0` renders as a zero statistic, not as missing data.
- Confirm worker cards make no bootstrap typical-times request and use the batched step value in
  the no-budget state.

## Provenance

Semantic authority: the ratified `narrow_typical_work_times` intention, especially the response
contracts, the allocation-method statement, the D25 zero rule, the `is_estimated` clarification,
and the frontend closeout obligation. This handoff supersedes the one worker-card source
instruction named above and leaves every other published instruction in the 2026-08-18 document
unchanged.
