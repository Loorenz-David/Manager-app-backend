---
subject: stock_report — owner cards parked during the unattended batch D run
date: 2026-09-21
actor: orchestrator
status: OPEN — nothing here has been applied
---

# Owner cards parked during batch D

**Read this with `FINALIZATION_STEPS.md`.** That file is the plan; this one is the short list of
things the plan could not decide.

**The rule I am holding myself to overnight** (recorded in `FINALIZATION_STEPS.md`): I rule cards
along the ratified intention, but I **park anything that turns on a domain invariant or a
published contract**. Those land here with their evidence, and the batch keeps moving around
them. The reason is measured, not caution: earlier today I read a nullable column and a permissive
request model as evidence of a domain rule, called it "decisive", and was wrong — you caught it.
Unattended, nobody catches it.

**Nothing below is applied.** Each card states what I would do, so a one-word answer is enough.

---

## Card D-1 — `PATCH …/priority-order` has no tenancy criterion

**Class:** criterion row. **Authoring a row is yours, always** — so this is a proposal, not an
amendment. I have not touched plan 12.

**The gap.** Plan 12 **C1(o)** enumerates all three visibility cells — foreign workspace,
soft-deleted, absent — for the `PATCH …/priority` route. There is **no equivalent row for
`PATCH …/priority-order`**, which is a second route with its own `require_roles` list, its own
request model, and its own command module.

**Why it is probably harmless, and why that is not the point.** The two commands share the same
row-lookup shape, so the behaviour is most likely already right. What is missing is the row that
would notice if it were not. This pipeline has now found the same shape eleven times in one batch
— *a row whose evidence is delegated to something that never performs the check* — and three
unarmed promises were closed in a single day (C4(i), C4(j), C4(k)). A second route whose tenancy
is asserted only by its sibling's row is that shape.

**Cost if you say yes:** three assertions in a file the tester is already writing. Near zero.

**Proposed cell text** — a new row **C1(p)**, modelled exactly on C1(o) and using the same
cross-workspace reference the §6 preamble already defines:

> | C1(p) | three calls as U of W — `SO(row of the foreign workspace, 1)`, `SO(a soft-deleted row of W, 1)`, `SO("sri_absent", 1)`. The foreign row is a **cross-workspace reference** (preamble): same category, same properties, same `high` group with the same orders, so tenancy is the only reason it refuses | `NotFound` each; no state anywhere changes; the foreign workspace's group is byte-identical | three mutants at `set_stock_report_item_priority_order.py`'s row lookup (def.), **all three runs recorded** (L-34's three visibility cells): (i) drop the `workspace_id` term → the foreign row is found and reordered; (ii) drop `is_deleted = false` → the soft-deleted row is reordered and its live neighbours are renumbered around it → `order_density` diverges; (iii) return the serialized row instead of raising when the lookup finds nothing → the absent id answers 200 | M4 |

**One claim in that text I verified rather than assumed.** Mutant (ii) says `order_density`
diverges. `compute_stock_report_divergences` loads rows under
`StockReportItem.is_deleted.is_(False)` (`consistency.py:126`) and then walks each priority group
expecting `1..n` dense (`:184-197`), so a soft-deleted row that gets reordered shifts its **live**
neighbours and the group stops being dense. The divergence kind is right.

**If you would rather not add a row:** say so and I will record the gap as a known-uncovered
surface in plan 12 §7, which is honest and costs nothing. The wrong outcome is silence.

---

## Card D-2 — where `stock_report_item:deleted` is built (likely self-resolving)

**Class:** registry, not criterion — **I can apply this one** and expect to.

Plan 13 never says where the `stock_report_item:deleted` event is constructed. §6.5's `_events.py`
registers only the `:updated` and assignment builders, and `stock_report_item:created` is built
**inline** in `apply_stock_demand.py` — so both a shared builder and an inline construction have a
shipped precedent, and the plan is genuinely silent rather than wrong.

I told the implementer to pick one and state the exact `file:symbol`, and I register it in §6.5 in
the same act (§9 rule 18). It matters because **plan 14's C1(b) accuracy guard** is rooted in
`_events.py` plus every `event_name=` site: a name built somewhere no registry entry explains is
exactly what that guard exists to catch.

**Listed here only so you can see it was noticed and closed, not so you have to answer it.**

---

## Card D-3 — plan 13A's conditional validator extraction (D2, not yet live)

**Class:** perimeter over an APPROVED file. **Parked — this is yours.**

Plan 13A §4 makes the shared per-field validator extraction **conditional**: *"only if the
per-field validators must be exposed for reuse."* §7 records the recommendation to extract with no
behaviour change, and notes plainly that this is *"silent freedom over a phase-7 APPROVED file."*

**I will not let an implementer resolve that on its own judgement**, and I will not resolve it
myself either, because it is a perimeter question over approved code rather than a question the
intention settles. Before D2 starts I will write the decision into the D2 prompt one way or the
other; if you are awake by then, it is a one-word answer. My recommendation, for the record:
**extract, with a behaviour-preserving refactor and phase 7's suite green unchanged as the proof**
— the same shape as D1's authorised `_row_values` consolidation, which the registry already
ordered for the same reason (one shared helper, divergence is the failure mode).

---

## Carried OUT of the pipeline entirely — not cards, not for tonight

Repeated from `FINALIZATION_STEPS.md` so this file stands alone:

1. **The mandatory-category enforcement gap.** An Item cannot validly exist without a category,
   but the backend does not enforce it and `Item.item_category_id` is nullable; the invariant has
   been held by frontend validation. Needs its own intention, a migration, a **backfill audit** for
   category-less rows already in the database, and a decision for every existing caller.
2. **`test_database_isolation.py` slot-sensitivity** — a foreign APPROVED project's file. Costs
   nothing today: both IDs are named in the 23-ID baseline.
3. **The `migrations` exclusion from the MC-2 write-site guard.** A migration can change task state
   invisibly, in **any** form — arguably a wider door than the four constructs card R-1 closed.
   Noticed 2026-09-21, never ruled.
