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

### Second instance, same session — it is not only `contains`

`edge:source-file-item-economics-budget-division--implements-->projection-item-economics-task-production-time`
reported the same contradiction type and the same `suggestedDecision: "investigate"`:

> Another "implements" edge starting at "source-file-item-economics-budget-division" already
> points at "projection-item-economics-task-budget-allocations".

The sibling edge it names is **`origin: human_confirmed`**. One pure module implementing two
projections is exactly what `budget_division.py` does — it is the shared allocator behind both
the allocations projection and the production-time projection, which is the whole reason both
exist.

**So the check misfires on `implements` too, not just `contains`.** Two of the six items
reviewed at this closeout carried it, both false, both would have been parked by an agent that
took `suggestedDecision` at face value. Whatever the rule is, "a source node may have at most
one edge of a given type" is not true of this graph's human-confirmed content for either type.
Promoted over it; reasoning in `.archgraph/reviews/2026-08-20T04-46-34-665Z--228822.yml`.

---

## Closing note — what the anchors looked like across 11 items

Not a finding, but the reason two of the findings above matter. Of the eleven pending items
reviewed at this closeout, **six carried anchors that did not point where they claimed**:

| Item | Stored | Actual | Kind of wrong |
|---|---|---|---|
| `projection-…-price-scenario` ev0 | 149–273 | 181–311 | drifted (code moved) |
| `projection-…-price-scenario` ev1 | 387–419 | 583–617 | drifted, ~200 lines |
| `projection-…-production-time` ev1 | 172–196 | 191–213 | **wrong region** — inside the preceding test |
| `endpoint-…-production-time` ev1 | 9–16 | 8–14 | **excluded its own evidence** — the parametrize carrying the four roles |
| `…budget-division--implements-->…` | 245–401 | 273–401 | **wrong region** — starts 28 lines inside another function |
| `endpoint-…-production-time` ev0 | 370–381 | 371–382 | off by one, opens on a blank line |

Three of those six were never right — they did not drift, they were recorded wrong. **Line
spans recorded alongside a symbol are worth re-deriving from the symbol at review time rather
than trusting**, and the two that excluded a decorator are the sharper lesson: when a test's
evidence is its `@pytest.mark.parametrize` table, an anchor starting at the `def` points at the
assertion and misses the data it is asserting over.

---

## Addendum to Finding 1 — 2026-08-21 — pipeline coordinator (`live_clock` phase-3 closeout)

**The review path batches fine. Finding 1's defect does not generalise to it.**

Clearing this repo's review queue took **one `archgraph_preview_review_decisions` call
carrying 13 `promote` decisions**, followed by one `archgraph_apply_review_decisions`.
No `INTERNAL_ERROR`, no partial application: all 13 moved `ai_inferred → human_confirmed`
in a single audited record (`.archgraph/reviews/2026-08-21T08-50-39-304Z--eed27f.yml`).

So the one-operation-per-call constraint recorded above is **specific to
`archgraph_repair_anchors` / the maintenance path**, and a session should not generalise
it into "this server cannot batch". That matters in the expensive direction: a 13-item
queue adjudicated one call at a time is 26 round trips for no reason.

**Finding 1's open question is still open.** Its unresolved half was *"whether the trigger
is more than one operation or mixed operation kinds"*, and this session did not test it —
all eight maintenance operations here (2 unlink + 2 link per stale node) were issued one
per call precisely because the finding says to. The cheap experiment it proposes — one
two-`unlink` batch on a node that can spare it — remains undone.

**A second, smaller data point for the closing note's anchor lesson.** Repairing the two
stale nodes required re-deriving four spans, and **all four stored spans were wrong**:

| Link | Stored | Re-derived | Kind of wrong |
|---|---|---|---|
| `…task-production-time` → `get_task_production_time` | 23–45 | **26–121** | ended mid-function after the symbol grew |
| `…task-production-time` → `test_c4_c6a_c6b_…` | 106–158 | **108–160** | off by two at both ends |
| `…task-price-scenario` → `get_task_price_scenario` | 181–311 | **184–315** | drifted under a parallel stream |
| `…task-price-scenario` → `test_c1_status_matrix_…` | 583–617 | **583–615** | start correct (the `parametrize` table), end over-reached into trailing blanks |

That is now **ten of fifteen** anchors inspected across two closeouts that did not point
where they claimed. The closing note above says line spans are worth re-deriving from the
symbol rather than trusted; at this hit rate it is not a precaution, it is the procedure.
