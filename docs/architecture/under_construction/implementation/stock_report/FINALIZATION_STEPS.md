---
subject: stock_report — finalization steps after batch D
date: 2026-09-21
actor: orchestrator
authority: owner, stated 2026-09-21 before an unattended overnight run of batch D
---

# Finalization steps — owner's plan, recorded verbatim in intent

The owner set these out before sleeping, for an overnight run of batch D. The morning goal is the
**wiring stage — the final stage before live testing.** Work through them in order.

## 0. Batch D itself

**D1 = phases 12 + 13**, approved, **then D2 = phases 13A + 14.** D1 must be APPROVED before D2
starts: phase 13's fresh-read requirement (the cascade re-reads a row's `priority_order` each
iteration, because the previous deletion's gap-close makes a held copy stale) is **only testable
from 13A**, so running them together would seal phase 13 before its one test exists.

## 1. `item_category.image_url` on stock-report instances — ALREADY FOLDED, do not re-do

The owner asked for this as a post-batch serialization addition, promised to the frontend.

**It is already in plan 12** (§5 item 5 and its Review log), because it belongs there: 
`serialize_stock_report_item(row, *, category)` is **phase 12's own new function** and already
receives the resolved category object. No join, no query change, no approved code reopened.

The `item_category` block is now **four** keys: `client_id`, `name`, `major_category`,
`image_url`. `ItemCategory.image_url` is `Mapped[str | None]`, `String(1024)`, nullable
(`models/tables/items/item_category.py:23`), so it is `str | None` and must be **emitted as
`None`, never omitted** — an absent key and a null key are different things to a renderer.

**Verify at D1's gate that its row was actually armed** (a mutation dropping the key must redden
it). If phase 12 ships it as a key nobody asserts, that is a finding, not a pass.

## 2. The frontend documentation

Only after batch D is complete and step 1 is verified.

Per **owner card 7** (ruled 2026-09-21), phase 14 produces this, and the ruling is binding:

- a **NEW file**, new date in the filename, in **`handoffs/to_frontend/`** (the project folder —
  *not* the repo-wide `backend/docs/handoff/to_frontend/`, which holds another project's work),
  under the existing `HANDOFF_TO_FRONTEND_stock_report_*` naming scheme;
- an explicit **`supersedes:`** frontmatter key naming every document it replaces;
- superseded files **MOVED to an archive subfolder — never edited, never deleted**;
- a first section stating plainly which document is current and which are historical;
- it **must document match-preview**, with **`item_category_id` REQUIRED**;
- **no v3 of the preview contract.** `HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md`
  is correct, stays ratified, is **not** superseded and is **not** archived. The new document
  points at it as the source for that endpoint's semantics.

**Never rewrite a published handoff in place.** An in-place edit once cost the frontend four days.
This is the single most expensive mistake available in this step.

## 3. Read the frontend's own implementation docs

**Only after closure.** Path:

```
/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/frontend/docs/architecture/under_construction/implementation/stock_report
```

Read what is there and produce **what the frontend must now change in order to use the backend**.
The owner reads this in the morning; it feeds the **wiring stage**, the last step before live
testing. So it should be actionable and concrete, not a restatement of the API.

## 4. Closeout (required by the master plan, not optional)

1. **The final L4 and baseline comparison** — §3B defers these to closeout explicitly; batch gates
   do not satisfy them.
2. **Revisit the five "adjacent" baseline failures** (§10.1). The owner ruled "fix none, revisit at
   closeout" on 2026-09-19. That decision now comes due. **Owner's, not mine.**
3. **Graph delta** — one batched `apply_changes` per batch implementation (§3B).
4. **Archive** D's spent prompts and consumed handoffs to `archive/batch_D/`.
5. Approval-gate commits for D1 and D2.

## Carried OUT of this pipeline — needs its own intention, do not absorb into D

- **The mandatory-category enforcement gap.** An Item cannot validly exist without a category
  (owner, 2026-09-21), but the backend does not enforce it and `Item.item_category_id` is
  nullable; the invariant has been held by frontend validation. Needs a migration, a **backfill
  audit** for any category-less rows already present, and a decision for every existing caller.
- **`test_database_isolation.py` slot-sensitivity** — unruled owner card; a foreign APPROVED
  project's file. Costs nothing today (both IDs are named in the 23-ID baseline).
- **The `migrations` exclusion** from the MC-2 write-site guard — a migration can change task state
  invisibly, whatever form it uses. Noticed 2026-09-21, never decided.

## The limit the orchestrator set on itself for the unattended run

Owner cards are ruled along the intention **except** any card that turns on a **domain invariant**
or a **published contract**. Those are parked with their evidence and left for the owner, and the
rest of the batch keeps moving.

The reason is measured, not cautious-by-default: on 2026-09-21 the orchestrator read a nullable
column and a permissive request model as evidence of a domain rule, called it "decisive", and was
wrong — the owner caught it. Unattended, nobody catches it, and the failure mode there is
propagating an internal enforcement gap outward into a published contract, which is the one
direction retreat is expensive from.
