# Architecture graph — discrepancy ledger

Where agents in the build flow file disagreements between `.archgraph` and the code,
and where a dedicated fixer session picks them up.

The protocol lives in the **`archgraph-discrepancies` skill**
(`.claude/skills/archgraph-discrepancies/SKILL.md`). This file is the map; the skill is
the instructions.

```
open/       filed, not yet resolved     one file per graph item
resolved/   decision applied            same file, with a Resolution block appended
TEMPLATE.md copy one Finding block per discrepancy
```

## Why this exists

The graph was mapped in a single fast pass and is mostly **unverified**: 29 records are
`human_confirmed`, 244 are `ai_inferred` — asserted by one AI session and never checked.

Reviewing all of it in bulk is not proportionate. Instead the flow verifies on demand:
agents report what they trip over, a fixer resolves it, and a capability's nodes reach
`human_confirmed` by the time its implementation plans cite them.

## The rule for reporters

**File it, then carry on.** Do not detour into a review workflow, and do not silently
work around a wrong node — the silent workaround is the only outcome that loses
information permanently.

Record what you *observed*, with `path:line`, separately from what you *concluded*. The
fixer re-derives independently, so addresses are worth more than verdicts.

## The gate

Before compiling implementation prompts for a capability: enumerate the nodes its plans
will cite (`archgraph_get_neighbors` / `archgraph_compute_impact` from its entry nodes),
read `origin` on each, and report a count — *"14 of 14 cited nodes human_confirmed"*.

Any `ai_inferred` in that set is a gate failure. A plan citing an unverified node
inherits its error silently.

Nodes outside the set stay pending, deliberately. Pending is an honest state that
blocks nothing.

## Two things worth knowing before you file

Errors in this graph cluster in **rationale** (invented "why"s, sometimes written over
a documented reason in the same comment block) and **enumeration** (wrong counts, often
transcribed faithfully from stale code comments). Mechanism descriptions have held up.

And the trap: reading a node's stored `inferenceReason` and agreeing with it is not
verification. Open the cited lines and say what the code does *before* reading the
claim.
