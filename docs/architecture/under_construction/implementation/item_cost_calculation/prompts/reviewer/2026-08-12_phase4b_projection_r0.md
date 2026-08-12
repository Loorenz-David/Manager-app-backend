---
plan: phase 4B (category-driven group selection)
role: reviewer
round: 0 (plan-projection)
date: 2026-08-12
---

# Session prompt — plan projection (round 0), phase 4B: category-driven group selection

You are the **plan-projection agent** for phase 4B. You implement nothing: you do
the implementer's first hour **on paper** and record every decision the plan fails
to determine. NOTE: this projection runs while phase 4 is still under review —
your reality checks target the tree at the phase-4 checkpoint (`98c75a8` or later
HEAD); flag rather than fail if phase-4 fix cycles have moved code under you.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(project folder: `docs/architecture/under_construction/implementation/item_cost_calculation/`).

## Doctrine (read first, by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

## Gate check

- Tracker: 4B row present, NOT_STARTED, ⚑ MANDATORY; the 4B plan exists
  (`plans/phase_4b_category_selection.md`); its Review log is empty; no 4B
  implementer handoff exists.
- The planner's registry proposals are APPLIED in the master plan (§6.3
  `ItemMajorCategoryEnum`/`item_major_category_enum` row; §6.4
  `ITEM_COST_GROUP_CATEGORY_TAKEN`/`_IMMUTABLE`; §6.5 `resolve_major_category`,
  serializer note, migration slug) — verify presence; absence is a gate failure.

## Read order (after doctrine)

1. `plans/phase_4b_category_selection.md` — the plan you project, incl. its four
   ratified pins (L1 all-rows immutability predicate, L2 unknown-string → missing,
   L3 idempotent same-category update, L4 exact payload shape) and its verified
   in-tree facts section.
2. Intention **§7C entire** (round 12), §11A.4 as amended (12 ordered values),
   §7A.5/§7.4 supersession pointers, R12-1 + pins in `planning/owner_decisions.md`.
3. `master_plan.md` §§6 (as amended today), 9 (P-B…P-Q all bind), 10.
4. In-tree: `domain/items/enums.py:17` (`ItemMajorCategoryEnum`),
   `models/tables/items/item_category.py:24-28` (type ownership),
   `items.item_major_category_snapshot` (the String(64) snapshot the L2 pin
   canonicalizes), and phase 4's shipped `configuration.py` / status query /
   group commands (the code 4B reworks).

## Depth targets

1. **Selection totality (§7C.2):** the classifier's new ordered rule set — total
   over (category present/absent/unknown) × (0/1/2 groups for that category) ×
   basis states? One exact outcome per cell; the INV-G3-unreachable ambiguous row
   retained as defence; `item_missing_major_category` FIRST among group-2 reasons.
2. **Migration (§7C.1):** NOT NULL column on a table that may hold dev test rows —
   the pre-flight's report-never-guess predicate decidable? Downgrade drops the
   column but NOT the reused type (phase-2 M-b lesson); static proxy per P-J;
   which DB each criterion runs against (phase-4 harness block precedent).
3. **INV-G3 races:** dual-path rows incl. the update-flip path; per-clause (b)
   rows (P-M); concurrency rows per the phase-4 harness block.
4. **Immutability predicate (L1):** "any basis version ever" — decidable arbiter
   (C4(b))? Does group delete-and-recreate remain reachable (the escape hatch)?
5. **Payload reshape (L4):** the exact per-category shape; the named breaking
   tests (D8 discipline) — re-verify the list against the CURRENT tree (phase-4
   fix cycles may have added test nodes; the plan's Dependencies section carries
   the greps); P-B null-numerics obligations.
6. **`resolve_major_category`:** sole-reader rule enforceable? (a mutation/probe
   naming direct snapshot-column reads); unknown-string row (L2).
7. **Criteria decidability & first-hour reality:** every row's fixture/outcome
   exact; P-G/P-I(observed ids)/P-K/P-Q discipline; file list complete
   (serializers? status query tests? router changes?).

## Constraints

Read-only; write nothing outside your handoff. Plan defects are ledger rows.
Archgraph read-only (note: 47 pending phase-4 items exist — not yours to touch or
verify; zero delta).

## Closing protocol

Deposit the handoff at
`docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase4b_projection_r0_handoff.md`
(full path): frontmatter complete; `⚠ OWNER DECISIONS REQUIRED (n)` (one line if
zero); decision ledger (severity + routing); citation/decidability verification;
explicit delegation list; full write perimeter. **Deposit before ending the
session.** The implementer prompt compiles only after the ledger is routed AND
phase 4 is APPROVED.
