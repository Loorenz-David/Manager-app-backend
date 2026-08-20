# tooling — `archgraph_repair_anchors` batching, and the `contains` canonical check

<!--
NAMING DEVIATION, recorded deliberately. The convention is one file per graph ITEM, named
after its id. These two findings are about the SERVER'S BEHAVIOUR, not about any node or
edge, so no item id names them. Filed here anyway because the ledger is where graph findings
live and a tooling defect that misroutes future sessions is worth more than a single wrong
node — one of the two has already misrouted this project once.
-->

## Finding 1 — 2026-08-20 — pipeline coordinator (`simple_valuation_editor` closeout)

**Found while:** repairing drifted source links on `projection-item-economics-task-price-scenario`
at the close of the `simple_valuation_editor` pipeline.

**Kind:** other (tool behaviour)

### What the tool does

Measured in sequence, same node, same session, each call's `expectedRevision` taken from the
previous result:

| Call | Operations | Result |
|---|---|---|
| 1 | **4 ops** — `unlink` idx 1, `unlink` idx 0, `link`, `link` | **`INTERNAL_ERROR`**, empty `details`, nothing written |
| 2 | 1 op — `unlink` idx 1 | applied |
| 3 | 1 op — `unlink` idx 0 | applied |
| 4 | 1 op — `link` | applied |
| 5 | 1 op — `link` | applied |

Calls 2–5 carried the same `itemId`, the same operation kinds and the same payloads as call 1.
**The only difference was one operation per call.** All four succeeded and produced change
records under `.archgraph/changes/`, `authorizerSource: anchor-repair`.

### What the project believed

The `simple_valuation_editor` master plan §5 and this repo's `archgraph-discrepancies` skill
both record:

> `archgraph_repair_anchors` returns `INTERNAL_ERROR` on such items (reproduced twice, on a
> re-anchor and on an unlink/link batch) … pending `ai_inferred` items are reachable only by
> the review path.

### Where they disagree

**The pending `ai_inferred` state is not the cause.** The node in call 1 was already
`human_confirmed` — promoted minutes earlier in the same session — and it still failed. Then
the identical work succeeded one operation at a time.

Re-reading the earlier evidence: the two historical reproductions were *"a re-anchor and an
**unlink/link batch**"*. Both were multi-operation. So the original diagnosis attributed to
the item's review state what the batch size appears to explain.

**This matters because the wrong lesson is expensive.** A session that believes pending items
are unreachable by `repair_anchors` reaches for `reject`-and-re-record instead — which
destroys provenance and sends a rebuilt copy to the back of the review queue — when four
single-operation calls would have done it.

**What is NOT established:** whether the trigger is *more than one operation* or *mixed
operation kinds*. Call 1 had both. Distinguishing them costs one two-`unlink` batch on a node
that can spare it; it was not done here rather than churn a just-corrected record.

**Proposed decision:** investigate — this is a server-side defect, not a graph-content
decision. The `INTERNAL_ERROR` carries an empty `details` object, so the server log is the
only place the real cause is visible.
**Confidence:** high on the observation, medium on the batching-vs-mixed-kinds attribution.

**Blocks my task:** no — the single-operation sequence completed the repair.
`staleNodeCount` went 1 → 0.

---

## Finding 2 — 2026-08-20 — pipeline coordinator (`simple_valuation_editor` closeout)

**Found while:** reviewing `edge:domain-item-economics--contains-->source-file-item-economics-price-scenario`.

**Kind:** other (tool behaviour — false positive)

### What the graph contains

`archgraph_get_review_item` reported **four** `contradictions`, all
`conflicting-canonical-relationship`, all of this shape:

> Another "contains" edge starting at "domain-item-economics" already points at
> "projection-item-economics-task-budget-status", not "source-file-item-economics-price-scenario".

…and `suggestedDecision: "investigate"` on the strength of them.

Read from `.archgraph/architecture.yml` directly, `domain-item-economics` already has four
`contains` edges — to `projection-item-economics-task-budget-status`,
`projection-item-economics-lifetime`, `projection-item-economics-task-budget-allocations`
and `projection-working-section-typical-times` — and **all four are `origin: human_confirmed`.**

### Where they disagree

A domain containing many things is not a contradiction; it is what `contains` means, and this
graph's own human-verified content says so four times over. The check appears to treat
`contains` as canonical — at most one target per source — which is right for a relationship
like `accepts` and wrong for a containment hierarchy.

**The cost is not the noise, it is the suggestion.** `suggestedDecision` flipped to
`investigate` on four false positives, and an agent that defers to it parks a correct edge
instead of promoting it. This will recur on **every** future `contains` edge in a populated
domain, which is every one worth recording.

The underlying claim was verified independently and promoted: `price_scenario.py` sits in
`beyo_manager/domain/item_economics/` beside `budget_division.py` and `calculator.py`, and its
lines 1–11 are exactly the import block, importing only that package's enums plus
`errors.validation`.

**Proposed decision:** investigate — either exempt hierarchical relationship types from the
canonical-conflict check, or downgrade the finding from `contradiction` to a note that does
not move `suggestedDecision`.
**Confidence:** high.

**Blocks my task:** no — promoted over the false positives, with the reasoning in the review
record `.archgraph/reviews/2026-08-20T04-39-02-258Z--6e129c.yml`.
