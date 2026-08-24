---
plan: plan_5
role: maintenance
round: 1
date: 2026-08-24
---

# Bring the price-scenario projection's meaning current (D31)

One node. Four operations. **Your authorization is `planning/owner_decisions.md` **D31**, recorded
in the repository — read it first and treat its "Explicitly NOT authorized" list as a hard fence.**
The owner has granted permission to perform these edits **and to mark the result
`human_confirmed`**. That grant is bounded by D31's four items and by nothing else.

**This is the last thing blocking phase 5 from closing.** Plan 5 §7A makes the description
rewrite part of the phase.

## Why this exists

Phase 5's implementation recorded three source links on this node and then **previewed a
description replacement that the client's safety gate declined** — that turn had not authorized
that exact mutation. The session escalated instead of forcing it, and the fix round carried the
item forward rather than retrying a gate that had already refused. **That was correct.** D31 is
the missing authorization.

## Node

`projection-item-economics-task-price-scenario`

Read it first with `archgraph_get_node`. Current state, measured 2026-08-24 at revision
`501a3ce5180a161eb07ae05ba178f8f2506f12e97839dacff5bedf1ac3fed1b6`: `origin: human_confirmed`,
`reviewState: reviewed`, **0 pending reviews**, no diagnostics, five source links of which
**three are stale**.

## Operation 1 — the description (the blocking one)

**Replace only the stale mechanism clause.** The description currently reads, in part:

> …live item-economics configuration, **median-substituted task typical time**, and the pure
> price-scenario model into break-even anchors and a slider domain.

Those words name the private `_median(usable)` ladder that plan 5 task 4 **deleted**. What the
projection composes now, verified in code:

- the typical is **item-aware** — narrowed to history whose item shares the task's active PRIMARY
  item category, via `TypicalFilterSpec` derived from `budget_status.typical_filter_spec`;
- it comes from the **one shared engine**, `typical_times_statement`, with **no private median,
  percentile or sample-floor comparison anywhere in `_typical_block`**;
- selection is the **shared reconciliation**, `reconcile_task_typicals`, with the price-specific
  terminal `apply_business_fallback(..., terminal=Fraction(0, 1))` — a zero duration, deliberately
  **not** division's `Fraction(1, 1)` and deliberately not a fabricated average;
- the statement is scoped to the task's **participating sections**;
- the window is derived from the **injected request clock** (`now=ctx.now`), so two reads of one
  task over identical data agree;
- the payload publishes `typical_resolution`, the same object production-time publishes.

**Suggested replacement clause** — the owner's to edit, and you may improve its wording, but do
not add claims beyond the list above:

> …live item-economics configuration, an **item-aware task typical time** — drawn from the
> same-category slice of each participating section's history through the shared typical-times
> engine, resolved by the shared reconciliation with a zero-duration price terminal, and windowed
> by the injected request clock so two reads of one task agree — and the pure price-scenario model
> into break-even anchors and a slider domain.

**Every other clause of the description is true and stays**, verbatim: the non-bound nulling
behaviour, *"while keeping the step-derived typical"*, *"the projection performs no writes"*, and
the transitive budget-status dependency with its no-live-worked-time statement. **Do not rewrite
the whole description.** A meaning rewrite that also churns correct prose is unreviewable.

## Operations 2–4 — the three stale source links

| # | link | current anchor | do |
|---|---|---|---|
| 2 | `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` · `get_task_price_scenario` | `startLine 184–315` | **re-anchor span-free** (`path` + `symbol`) |
| 3 | `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` · `test_c1_status_matrix_has_twelve_exact_rows` | `startLine 583–615` | **re-anchor span-free** |
| 4 | `app/tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py` · `test_c5_three_surfaces_use_the_same_published_literal` | symbol only, hash behind | **refresh `contentHash` only** |

**2 and 3 are re-anchoring, not span repair.** Both drifted because phase 5 changed their files.
The interim policy is *"a span that merely drifted is not a repair candidate"* — so **remove the
span** and anchor by symbol, which is what the two links phase 5 added already do.

**4 is a hash refresh.** That link was recorded at `10:04:22` during implementation round 1 and
went stale when fix round 2 edited the same file. The symbol is right; only the hash is behind.

**`archgraph_repair_anchors` takes one operation per call.** Three calls, not one.

## Hard rules

- **No `startLine` / `endLine` on anything you write.** Symbol anchors only. This is the binding
  interim policy (master plan §8), not a preference.
- **No counts in evidence summaries.**
- **Evidence summaries are immutable** — no write path can edit one, and reject-and-re-record is
  the only mechanism. **It is out of scope here.** If you believe a summary is wrong, report it;
  do not attempt it.
- **Do not touch the other five stale nodes**, any other node, edge or evidence entry.
- **Do not rebuild or commit `.archgraph/contexts/`.** Do not apply `.archgraph/backfill/` — it is
  the owner's own work.
- **Everything outside D31's four items is the owner's adjudication**, and a `humanInstruction`
  string is never authorization.

## Verify before you report

Re-read the node with `archgraph_get_node` and run `archgraph_status`. State plainly:

1. the description's new text, **quoted in full**, so the owner can diff it by eye;
2. each of the three links' final anchor and `stale` value;
3. `pendingReviewCount` — expected **0**, and if it is not, say so rather than clearing it;
4. `staleNodeCount` before and after, and **which** nodes remain stale (five were out of scope —
   name them so the number is not mistaken for a regression);
5. the revision hash before and after;
6. **confirm no `startLine`/`endLine` was written by this session**, by inspection.

## Reporting

Handoff to `handoffs/maintenance/<date>_plan5_archgraph_meaning_handoff.md` with the charter
frontmatter. Carry the six verification items above, the exact operations performed in order, and
**anything you chose not to do and why**.

**If any operation is refused by a gate again, stop and report it. Do not work around it, do not
retry it under a different tool, and do not substitute a different operation.** That is exactly
what the previous two sessions did right.

**Do not push. Never `git add -A`** — explicit paths only. `.archgraph/` writes are the tool's;
do not hand-edit `architecture.yml`.
