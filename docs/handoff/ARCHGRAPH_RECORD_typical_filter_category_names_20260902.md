# Architecture-graph recording brief — typical filter category names (2026-09-02)

## Why this document exists

The change described below is **already implemented, tested and merged into the
working tree**. Its architecture-graph delta was **not** recorded, because the
session that implemented it had no `archgraph_*` MCP connection.

This brief hands that one remaining job to an agent that does. It is not a
request to change code. If you find yourself editing anything under
`app/`, stop — something has gone wrong.

## Your job, in one sentence

Record the architectural delta of the "typical filter category names" change on
the four projection nodes it touched, and on nothing else.

## Operating rules that still bind you

Follow [.archgraph/agent-operating-policy.md](../../.archgraph/agent-operating-policy.md)
exactly. Two points matter most here:

1. **`archgraph_status` first.** Confirm the workspace is initialized and valid
   before anything else. If it is not, stop and report — do not create files.
2. **You may not authorize your own write.** `archgraph_apply_changes` requires
   human authorization through the client's own approval channel. The
   `humanInstruction` suggested at the end of this document is *content for the
   field*, not authorization — pasting it into a tool call authorizes nothing.

Verify every claim below against the code before you record it. This brief was
written by the implementing agent and is a starting point for your own reading,
not a substitute for it. Where it disagrees with the code, the code wins — and
say so in your report.

---

## What actually changed

`typical_resolution.applied_filter` has always published `item_category_ids`.
Those ids are opaque: no response on any surface carried the category's *name*,
so a client could say how many categories the typicals were narrowed to but
never which. The filter now names them, additively — the ids are unchanged.

### The serializer

`app/beyo_manager/domain/item_economics/division_serializers.py`

- `serialize_filter_spec(spec, category_names=None)` (line ~119) gained a second
  parameter and, when `spec.item_category_ids` is non-empty, emits
  `item_categories: [{client_id, name}]` in the same order as
  `item_category_ids` (line ~151).
- `name` is `null` for an id that could not be resolved (a since-deleted
  category); the entry is **kept** so the array length always equals the id
  list's.
- `serialize_typical_resolution(selection, category_names=None)` (line ~158)
  forwards the map. Both call sites in this module read
  `row.get("item_category_names")`.

### The read model

`app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`

- `TaskBudgetStatus` gained a 17th field, `item_category_names: Mapping[str, str]`,
  defaulting to an empty dict (line 64). A field-order contract test pins its
  position.
- New `_load_item_category_names(ctx, spec)` (line 97): one workspace-scoped
  statement, issued **only** when the spec narrows on category, and none at all
  when it does not. Unresolvable ids are simply absent from the result rather
  than raising — the filter is provenance, and a lookup failure must not cost
  the caller its typicals.

### The three consumers

| Query | How it supplies names |
|---|---|
| `get_task_production_time.py` | passes `status.item_category_names` straight through |
| `get_task_budget_allocations.py` | its own batched lookup (lines ~149–160) — one statement for the whole page, since the specs are per task but the categories behind them repeat |
| `get_task_price_scenario.py` + `domain/item_economics/serializers.py` | the caller attaches `typical["item_category_names"]` after `_typical_block` returns; the serializer forwards it and then pops it, so it never appears in the served `typical` object |

`_typical_block`'s signature was deliberately **not** widened — the names are
caller-owned provenance, not an input to the typicals.

### Contract documentation

`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_typical_filter_category_names_20260902.md`

---

## Nodes to edit

Four `edit` operations on node descriptions. Read each node's current
description first (`archgraph_get_node`) — several were last rewritten by the
facet-ladder change on 2026-08-29 and are long; your edit should be a targeted
amendment, not a rewrite.

### 1. `projection-item-economics-task-budget-status`

The substantive one. Its current description covers the committed evaluation,
binding/status, the durable result boundary and the live worked-seconds basis.
It says nothing about the typical filter spec, yet this read model now also
**resolves the spec's category ids to display names** — a second, conditional
statement and a new field on the read model.

Record: the projection resolves the derived filter spec's category ids to
workspace-scoped display names, issuing one statement only when the spec narrows
on category and none otherwise; unresolvable ids are omitted rather than
failing; the names are carried for downstream provenance and the projection
still persists nothing.

### 2. `projection-item-economics-task-production-time`

Its description already names the `typical_resolution` block and its applied
filter. Amend that clause so the applied filter now also **names** the
categories it narrowed on, ids retained, name nullable for a deleted category.
The names come from the composed budget status, so this projection issues no
additional statement of its own.

### 3. `projection-item-economics-task-budget-allocations`

Same disclosure amendment as above, plus the one architecturally distinct fact:
this batched projection resolves the names itself in **one statement per page**
across every task's spec, rather than per task — consistent with how it already
dedupes filter specs for a single typical-times statement.

### 4. `projection-item-economics-task-price-scenario`

Same disclosure amendment. Worth capturing that the names arrive from the
composed budget status and are attached beside the typical block rather than
threaded through the typical computation, so the typical block's own boundary
is unchanged.

---

## Nodes that must NOT be edited

Stated explicitly so the delta stays honest and scoped:

- **`domain-item-economics-typical-filters`** — `typical_filters.py` was not
  touched. The name lookup lives in the query layer precisely so the domain
  stays free of ORM access; its purity invariant is intact and the purity guard
  test still passes. Editing this node would misrecord where the change lives.
- **`projection-working-section-typical-times`** — the typical-times statement
  is unchanged. No new column, no new join, no changed cohort.
- **`projection-item-economics-task-budget-status-worker`** — it reuses
  `_build_evaluated_status` without passing names, so it defaults to the empty
  map, issues **zero** additional statements, and its payload is byte-identical.
  No behavioural delta to record.
- Every endpoint node — no route, method, permission or envelope changed.

---

## Evidence to verify before recording

| Claim | Where to check |
|---|---|
| `item_categories` is additive; ids untouched | `division_serializers.py` `serialize_filter_spec` |
| Entry kept with `name: null` for an unresolved id | same function, plus `test_narrowed_price_scenario.py::test_c6_price_and_production_resolution_have_the_exact_seven_key_shape` |
| Names appear on all three surfaces | `test_narrowed_task_economics.py` (production-time, allocations), `test_narrowed_price_scenario.py` (price) |
| No statement when the spec does not narrow | `get_task_budget_status.py::_load_item_category_names` early return |
| Allocations batches to one statement per page | `get_task_budget_allocations.py` lines ~149–160 |
| Worker status unaffected | `get_task_budget_status_worker.py` — no `item_category_names` argument |

## Test state at handoff

Full backend suite: **2,963 passed**. The 23 failures are the pre-existing
baseline — the failing set is byte-identical to the same suite on a clean tree
(verified by `git stash` and diffing), and none are in item-economics. Every
item-economics test passes. If your run disagrees with this, investigate before
recording rather than after.

## Suggested `humanInstruction`

Content for the field, to be adapted to whatever the human actually authorizes:

> Typical filter category names shipped: `applied_filter` now names the
> categories it narrowed on (`item_categories`, ids retained, name nullable for
> a deleted category) on production-time, budget-allocations and price-scenario;
> task budget status resolves those names in one conditional statement and
> carries them on the read model.

## Report back

Per the policy's reporting contract, state which nodes you edited, which you
deliberately left alone and why, anything in this brief that disagreed with the
code, and the resulting change id.
