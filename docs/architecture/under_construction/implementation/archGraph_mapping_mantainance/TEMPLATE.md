# <item id, e.g. node:analytics-reconcile-user-day-time>

<!--
One file per graph item. Name it after the item id with `:` and `/` replaced by `-`.
If the file exists, APPEND a new finding block — do not overwrite. Two agents finding
the same node is signal.

Copy one Finding block per discrepancy. Keep it to five minutes.
-->

## Finding — <YYYY-MM-DD> — <reporting agent / session role>

**Found while:** <what you were actually doing — shaping the intention, planning phase 3, …>

**Kind:** rationale | enumeration | mechanism | stale-address | missing | other

<!--
`rationale` and `enumeration` are where this graph's errors have clustered. `mechanism`
claims have held up well, so a mechanism finding is worth extra care before filing.
-->

### What the code says

<!--
Addresses first. This is the part the fixer re-derives from, so it must be checkable.
Quote or describe what is actually there. Do NOT lead with your conclusion.
-->

- `path/to/file.py:120-134` — <what this code does, in your own words>
- `path/to/other.py:44` — <…>

### What the graph claims

<!-- The stored description or evidence summary, quoted. -->

> <quoted claim>

### Where they disagree

<!-- One or two sentences. The specific mismatch, not a general worry. -->

**Proposed decision:** reject | deprecate | promote-with-anchors | edit | investigate
**Confidence:** high | medium | low

<!--
low is fine and useful. File it and move on rather than turning this into an
investigation — the fixer re-derives independently anyway.
-->

**Blocks my task:** yes | no
<!-- yes = I could not proceed without resolving this. Raises priority for the fixer. -->

---

## Resolution — <filled by the fixer>

**Decision applied:** <decision> · **Audit record:** `.archgraph/reviews/<file>.yml`
**Date:** <YYYY-MM-DD>

**Independent reading:** <what the fixer found when re-deriving from the cited
addresses, before reading the reporter's conclusion>

**Disagreement with the report:** <none | what differed — this is how the flow learns
where reporters go wrong>

<!-- On resolution, move this file from open/ to resolved/. -->
