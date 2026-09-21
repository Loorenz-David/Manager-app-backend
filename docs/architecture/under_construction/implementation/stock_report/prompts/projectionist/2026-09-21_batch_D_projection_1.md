---
batch: D
phases: [12, 13, 13A, 14]
role: projectionist
round: 0
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Opus
---

# Batch D round 0 — projection and the lesson fold

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/plan-projection.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Plans: `SR/plans/plan_12.md`, `plan_13.md`, `plan_13A.md`, `plan_14.md`.
Authority: `SR/planning/intention.md` — RATIFIED, and it **wins over any plan**.

Batch D is **106 rows / 22 criteria** (12 → 45/7 · 13 → 19/6 · 13A → 37/7 · 14 → 5/2). Re-derive
with the committed `SR/count_criteria.py`; **never type a total**.

Batch shape is `projection + lesson fold → implementer → tester → reviewer` (master plan §225).
**You are the fold.** This is the highest-leverage round in the batch and the reason it exists:
across this pipeline's history, ~5/6 of rework was plan defects, and 26 of 30 first-review FAILs
were tests weaker than their row. Every defect you catch here costs a paragraph; caught in review
it costs a round.

## 1. The lesson fold — your first and largest job

**The master plan's own finding: *"plans 8–13A have never received a lesson fold."*** The batch C1
fold touched only plans 8 and 11. Your targets are **12, 13 and 13A**.

The register is `SR/master_plan.md` **§9A**, lessons **L-1…L-31** in table form, with **L-32…L-39**
defined outside it (L-32/L-33 in the batch C1 review handoff; L-34/L-35 in the phase 8A tracker
note; L-36…L-39 in `handoffs/reviewer/2026-09-21_batch_C2_review_2_handoff.md`). **Read all of
them, including the eight outside the table** — the register is not complete on its own.

Lessons whose §9A "Fold targets" column names 12, 13 or 13A:

> L-1, L-2, L-3, L-5, L-7, L-9, L-10, L-11, L-12, L-13, L-14, L-15, L-16, L-17, L-19, L-22, L-24,
> L-26, L-29, L-30

Treat that list as a **starting point, not a closed set** — verify it against the register
yourself, and check L-32…L-39 for targets nobody has assigned yet. **L-17 is marked highest
yield** (the preambles of 12, 13, 13A). **L-22** names a specific bound to audit: 13A **C5(d)'s
`≤ 7`** — "bound the shape you derived; no `≤` on a derived count".

**Authority split — this is the hard constraint.** Several lessons cannot be folded by you because
folding them means authoring or restating a criterion row, which is **reserved to the owner**.
§9A's "Authority split" marks these owner-only: **L-1, L-2, L-3, L-5, L-17's outcome half, L-22,
L-29** — verify that list at the source. For each, **write the exact proposed cell text and the
reasoning, and carry it as an owner card. Do not apply it.** Batch your cards so the owner rules
them in one pass.

## 2. The empty mutation cells

**27 rows across your plans carry an empty (`—`) mutation cell**: plan 12 has 16, plan 13 has 6,
plan 13A has 5. These are part of the 94-cell debt §9A records.

**Classify each one; do not reflexively fill them.** The measured precedent across 67 cells was
57 fold / 5 tester / 5 genuinely-unfailable, and **3 of 34 proposals were wrong at the site** —
so check the site before proposing. Three outcomes per cell:

1. **Foldable now** — you can name the mutation from the plan and the code. Propose the cell text.
2. **Tester's** — the mutation depends on how the test is built; route it to the tester round.
3. **Genuinely unfailable** — say so explicitly and say *why*, with the mechanism. A row that
   cannot fail is a finding, not a pass. If its evidence is delegated elsewhere, **name where and
   verify that the delegate actually performs the check** — batch C2's C2(a) was ruled
   "UNFAILABLE BY DESIGN with evidence delegated to the C4 guard" and **the guard performed no
   such check**, so the row had no evidence of any kind. That is the single most expensive defect
   this pipeline has found. Look for its shape here.

## 3. Plan 13A §7 — the six §14E questions. Not waivable.

13A's projection is **mandatory and not waivable** (§7.2, rule 17: Postgres lock re-evaluation and
deadlock shapes). The owner waived the §14E *mechanism-inventory* re-check on the condition that
**its six carried questions are answered here**. Work through plan 13A §7 question by question and
answer each against the code and the intention — not against the plan's own summary of them.

13A is the batch's risk concentration: multi-row cascade, deterministic contention rows, sorted
`VALUES` / sorted `FOR UPDATE`. Spend accordingly.

## 4. Also confirm

- **CF-2 → plan 13A C5(g)** is authored and present (sorted VALUES / sorted `FOR UPDATE` do not
  deadlock). It was assigned to batch D and is owed by 13A's own round. Confirm it exists and is
  armable.
- **Standard projection checks** on all four plans: every cited path exists; every intention
  citation says what the plan claims; criteria counts match `count_criteria.py`; no phase exceeds
  the eight-criteria cap; §7 mutation ledgers reconcile with the rows.
- **Dependencies.** 12 depends on 5 (VERIFIED — clear). 13 depends on 12 and 8. 13A depends on 13
  and **9**; 14 depends on 13A, 11 and **10**. Phases 9 and 10 are IMPLEMENTED but **not yet
  VERIFIED** — batch C2's owner gate call is outstanding. Note anything in 13A or 14 that assumes
  a 9/10 behaviour which the C2 rounds changed: F-1 restored `state.in_(ACTIVE_ASSIGNMENT_STATES)`
  to the sync's discovery query, and `resolve_processed_group` gained a `from_state == target`
  short-circuit, an early return and a zero-delta event guard.
- **Phase 14 carries the frontend handoff** and must cover the **match-preview endpoint**
  (phase 8A, CLOSED/VERIFIED today). The current ratified contract is
  `handoffs/to_frontend/HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md` and it is
  **correct as written** — `item_category_id` is **required**. Do not propose a v3. No lesson in
  the register targets 14; check whether that is right or an oversight.

## 5. What not to do

- **Do not author or restate any criterion row.** Propose; the owner applies. This is absolute.
- Do not edit `master_plan.md` or the intention. Plan edits only, plus your handoff.
- Do not change production or test code. This round writes documents.
- Do not re-derive counts by hand — run `count_criteria.py`.
- **Commit with explicit paths, never `git add -A`** (another agent may be writing into this tree).
  **Never push.**

## 6. Handoff

`SR/handoffs/projectionist/2026-09-21_batch_D_projection_1_handoff.md`:

1. **The fold**: every lesson considered, where it landed, and what you changed — plus every
   lesson you judged not-applicable and why (that is evidence too).
2. **The 27 empty cells**, one line each, classified 1/2/3 with reasoning.
3. **Plan 13A §7's six §14E questions**, each answered against the code.
4. Projection checks per plan: paths, citations, counts, sizing.
5. Defects found in the plans, routed `production | verification | plan`.
6. Owner cards under `⚠ OWNER DECISIONS REQUIRED (n)` — each with proposed cell text, the
   reasoning, branches, and your recommendation.

## Stop conditions

Every lesson in the register considered against 12/13/13A · the owner-only ones proposed but not
applied · all 27 empty cells classified · 13A §7's six questions answered · four plans
projection-checked · counts re-derived by script · defects routed · cards raised · handoff
complete.
