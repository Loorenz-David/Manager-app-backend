# Accurate costs & projections — pre-intention research

```
status: RAW MATERIAL (not an intention, not a plan)
role:   input to a future /intention-shaper run
date:   2026-08-16
source: design conversation, David + Claude, 2026-08-12 → 2026-08-16
depends_on: item_cost_calculation v1 — CLOSED 2026-08-15, all phases APPROVED
```

## What this folder is

The design direction and verified repo evidence for the work that comes **after**
`item_cost_calculation` v1 (closed 2026-08-15 — every track below is unblocked today). It is deliberately *not* an intention: nothing here is
resolved, no owner decisions are recorded, and no mechanism contracts exist. It is
the raw material you feed to `/intention-shaper` when you are ready to narrow one of
these tracks into something buildable.

Item cost v1 answers **"what can this item afford?"**. Everything here answers
**"what will this item actually take?"** — and the payoff is putting the two numbers
side by side.

## Contents

| File | What it is | Editable? |
|---|---|---|
| `raw_intention.md` | The design direction: principles, mechanisms, roadmap | yes — this is the draft |
| `research_findings.md` | Verified code facts with `file:line` citations | **record — never edit** |

Follow the same discipline as `item_cost_calculation`: evidence documents are records.
If a fact in `research_findings.md` turns out to be wrong, route it as a drift finding
and record the correction — do not patch the record silently.

## How to use it

1. Pick **one** track from `raw_intention.md` §8 (they are separable on purpose).
2. Re-verify the relevant rows of `research_findings.md` — the citations date to
   2026-08-16 and this codebase moves.
3. Run `/intention-shaper` with that track's section as the raw intention.
4. The mechanism-inventory gate will have plenty to chew on: §3's principles are
   stated as prose here, not as contracts.

## The one thing to do before anything else

`raw_intention.md` §5.4 — the **identifiability query**. One day of SQL that
determines whether per-issue time coefficients are solvable at all in your data. It
changes what §6 looks like, and it is the question the previous (deleted) issue-timing
implementation appears to have never asked.
