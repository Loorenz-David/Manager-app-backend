# Architecture-graph recording brief — typical filter properties (2026-09-03)

## Why this document exists

The change below is **already implemented, tested and in the working tree**. Its
architecture-graph delta was **not** recorded, because the session that
implemented it had no `archgraph_*` MCP connection.

This brief hands that job to an agent that does. It is not a request to change
code. If you find yourself editing anything under `app/`, stop.

It is a direct sequel to
[ARCHGRAPH_RECORD_typical_filter_category_names_20260902.md](ARCHGRAPH_RECORD_typical_filter_category_names_20260902.md)
and touches **the same four projection nodes**. Check whether that brief was
recorded first: if it was not, record both deltas together rather than leaving
the earlier one orphaned.

## Your job, in one sentence

Record that the typical filter now publishes the properties snapshot behind its
signature, on the four projection nodes it touched, and on nothing else.

## Operating rules that still bind you

Follow [.archgraph/agent-operating-policy.md](../../.archgraph/agent-operating-policy.md)
exactly. Two points matter most:

1. **`archgraph_status` first.** Confirm the workspace is initialized and valid
   before anything else. If it is not, stop and report — do not create files.
2. **You may not authorize your own write.** `archgraph_apply_changes` requires
   human authorization through the client's own approval channel.

Verify every claim below against the code. Where this brief disagrees with the
code, the code wins — and say so in your report.

---

## What actually changed

`applied_filter.properties_signature` is an opaque hash, so a client could say a
full profile matched but never which one. The only nameable property values were
the facet-ladder rungs, which are owner-declared fallback tiers rather than the
specification. The filter now carries the snapshot the signature hashes, ids and
signature unchanged.

### The serializer

`app/beyo_manager/domain/item_economics/division_serializers.py`

- `serialize_filter_spec(spec, category_names=None, item_properties=None)` gained a
  third parameter and emits `properties` **only** when `spec.properties_signature`
  is not None and a snapshot was supplied. Absent, not `{}`, when either is
  missing — an empty object would assert a different thing from silence.
- `serialize_typical_resolution` forwards it; both call sites in this module read
  `row.get("item_properties")`.

### The read model

`app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`

- `TaskBudgetStatus` gained an 18th field, `item_properties: Mapping[str, object] | None`,
  defaulting to None. A field-order contract test pins its position.
- New `_item_properties_for(spec, item)`: reads the snapshot off the primary item
  the query has already loaded — **zero additional statements**, unlike the
  category names. Gated on the signature, not on the item having properties.

### The three consumers

| Query | How it supplies the snapshot |
|---|---|
| `get_task_production_time.py` | passes `status.item_properties` straight through |
| `get_task_budget_allocations.py` | builds `properties_by_task` from `item_by_id`, already loaded for the page — no statement, where the category names cost one |
| `get_task_price_scenario.py` + `domain/item_economics/serializers.py` | caller attaches `typical["item_properties"]`; the serializer forwards then pops it, so it never appears in the served `typical` object |

`_typical_block`'s signature was again deliberately **not** widened.

### Contract documentation

`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_typical_filter_properties_20260903.md`

---

## Nodes to edit

The same four as the category-names brief. Read each description first
(`archgraph_get_node`) and amend rather than rewrite.

### 1. `projection-item-economics-task-budget-status`

The substantive one. Amend the clause that (after the previous brief) covers
resolving category ids to display names: the projection now **also** carries the
primary item's properties snapshot when the derived spec has a signature. Worth
recording that this costs no statement — it is read off the item the projection
already loads — and that it is gated on the signature rather than on the item, so
a non-signature spec carries nothing.

### 2. `projection-item-economics-task-production-time`

Amend the applied-filter clause: the filter now also publishes the properties
snapshot the signature hashes. Composed from budget status, so no additional
statement of its own.

### 3. `projection-item-economics-task-budget-allocations`

Same disclosure amendment, plus the architecturally distinct fact: this batched
projection resolves the snapshots from the page's already-loaded items rather
than per task and **without** a statement — a different cost profile from the
category names, which it batches into one statement per page.

### 4. `projection-item-economics-task-price-scenario`

Same disclosure amendment. The snapshot arrives from the composed budget status
and is attached beside the typical block rather than threaded through the typical
computation, so the typical block's own boundary is unchanged.

---

## Nodes that must NOT be edited

- **`domain-item-economics-typical-filters`** — `typical_filters.py` was not
  touched. `TypicalFilterSpec` deliberately did **not** gain a properties field:
  it is a frozen, hashable, equality-deduped value object, and a dict field would
  make `hash(spec)` raise. The snapshot is caller-owned display provenance, which
  is why it travels beside the spec rather than inside it. Recording a change
  here would misstate where the change lives.
- **`projection-working-section-typical-times`** — the cohort statement is
  unchanged. No new column, no new join, no changed predicate. The properties
  already fed it via `build_item_properties_match` and `build_item_facet_matches`;
  what changed is only that they are now *disclosed*.
- **`projection-item-economics-task-budget-status-worker`** — reuses
  `_build_evaluated_status` without passing a snapshot, so it defaults to None,
  issues zero additional statements, and its payload is byte-identical.
- Every endpoint node — no route, method, permission or envelope changed.

---

## Evidence to verify before recording

| Claim | Where to check |
|---|---|
| `properties` is additive; signature untouched | `division_serializers.py::serialize_filter_spec` |
| Emitted only beside a signature | `test_properties_ride_only_beside_the_signature_that_explains_them` |
| Absent, never `{}`, when unsupplied | `test_a_signature_without_a_served_snapshot_omits_the_key` |
| Named on the live surfaces | `test_upholstery_facet_rescues_a_new_wood_profile_on_all_surfaces` |
| No extra statement anywhere | `get_task_budget_status.py::_item_properties_for`, `get_task_budget_allocations.py::properties_by_task` |
| Spec stays hashable | `typical_filters.py` — `TypicalFilterSpec` unchanged |

## Test state at handoff

Full backend suite: **23 failures, byte-identical to the pre-change baseline**
(verified by `git stash` and diffing the failing set). None are in item-economics.
Every item-economics test passes. If your run disagrees, investigate before
recording rather than after.

## Suggested `humanInstruction`

> Typical filter properties shipped: `applied_filter` now publishes the property
> snapshot behind `properties_signature` (`properties`, emitted only beside a
> signature, absent rather than empty when unsupplied) on production-time,
> budget-allocations and price-scenario. Task budget status carries it on the read
> model, read off the already-loaded primary item at no statement cost.

## Report back

State which nodes you edited, which you deliberately left alone and why, anything
in this brief that disagreed with the code, and the resulting change id.
