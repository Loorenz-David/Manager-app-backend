---
phase: 8A
role: plan
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Opus
---

# Plan phase 8A — assignment match preview

Read by absolute path first: `/Users/davidloorenz/agent-skills/implementation-planner.md` and
`/Users/davidloorenz/agent-skills/pipeline-charter.md`.

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

**Write exactly one file: `SR/plans/plan_8A.md`.** No other file, no commit, no code.

## The authority

`SR/planning/intention.md` **§14G** (round 10, 2026-09-21) specifies this phase completely —
the endpoint, the request and response fields, the construction rule, the three semantics that
must not be softened, and **MC-21**, the new mechanism contract. Read it before anything else.
It is RATIFIED and it wins over this prompt.

Then read `SR/master_plan.md` — §6 (naming registry), §9 (standing rules, now 19 of them), §10
(environment), §3B (how this project runs roles) — and `SR/plans/plan_8.md`, whose command this
phase extends and whose criteria rows constrain it.

## Why 8A and not 15

It extends phase 8's command and depends on **phase 8 only**. Phase 14 is the frontend-handoff
and docs phase and must stay last, so a numeric successor would misstate the order. 13A sets the
letter-suffix precedent. Sequence: it runs after batch C1 is APPROVED and **before** batch C2
(phases 9 → 10).

## The shape of the work

Two halves, with very different risk, and the plan should treat them differently.

**Half 1 — the extraction (a refactor of APPROVED code).** MC-21 requires one implementation of
the acceptability decision, evaluating every MC-13 phase-3 check in MC-13's precedence order and
returning per-check results; `create_stock_task_assignments` takes the first failure, the preview
takes the whole list. Today that logic is `_phase3_reason` in
`bm/services/commands/stock_report/create_stock_task_assignments.py` — already a **pure function
of fetched entities** (`locked_rows`, `locked_tasks`, `locked_items`, `primary_pairs`,
`processed_pairs`, `active_item_ids`; no I/O), which is why the extraction is a move rather than
a rewrite. Its return shape changes from "first reason" to "results in order".

**This half needs few or no new criterion rows, and you should say so explicitly rather than
inventing them.** Phase 8's 67 armed rows already pin every one of those checks and their order;
if they stay green through the refactor, the refactor is proven by evidence that already exists.
Manufacturing parallel rows for it is over-specification — charter rule 16 and the tester
doctrine's over-evidence rule both bite. What the plan *should* carry is the obligation that
plan 8's suite passes unchanged, and a row for the one genuinely new property: that
`create`'s refusal for a given triple and the preview's `refusal_reason` for the same triple are
**the same value** — that is MC-21's observable, and nothing today proves it.

**Half 2 — the preview endpoint itself.** This is new surface and needs ordinary criteria:
the request fields (including **`quantity`**, which §14G explains is a matched criterion and not
metadata), the response fields, roles, the `task_id`-null construction rule and its
`pass_by_construction` results, the advisory `item_already_assigned`, the unresolved-identifier
case that is *not* a 404, `NotFound` on a deleted/foreign/absent row, and the property-failure
element shape being identical to the 409's.

## Constraints that will catch you

- **Rule 16:** `ACTIVE_ASSIGNMENT_STATES` / `TERMINAL_ASSIGNMENT_STATES`, never a spelled list.
- **Rule 17:** relocating a row's proof to a narrower surface is the owner's call. The preview is
  a *command* with a router; say which boundary each row is proven at and do not quietly choose
  the cheaper one.
- **Rule 19:** any new test file needs a name unique across the whole test tree — bare filenames
  are module names in this repo.
- **§10:** `client_id` order is not creation order (ULIDs, no monotonic counter, measured at 977
  of 1999 pairs out of order). Do not write a fixture that assumes insertion order.
- **Every criterion row is 5 columns:** `| Row | Fixture / input | Exact outcome | Named mutation
  (site) | Trace |`. An outcome is computed from the row's own fixture, side effects included.
  A fixture must make the row's predicate the **only** reason the outcome holds.
- **Name a mutation only where you can name a real site.** Half the sites here do not exist yet;
  where the site is an implementation choice, leave the cell `—` **with a one-line note saying
  the blank is deliberate** (master plan §3B's *Mutation cells* bullet, class 2). A cell naming a
  site that turns out not to exist costs a round — that happened this batch, on plan 8 C5(b).

## The fix round has landed — plan against the current tree

Batch C1 is **APPROVED** (`798fc69`); phases 8 and 11 are VERIFIED. The tree is stable and
`_phase3_reason` is in its final shape — read it directly rather than imagining it. It now
refuses a soft-deleted Task and a soft-deleted Item as well as absent ones (plan 8 C1(v), C1(w)),
and its parameters are unchanged: `locked_rows`, `locked_tasks`, `locked_items`, `primary_pairs`,
`processed_pairs`, `active_item_ids`. It still performs **no I/O**, which is the property MC-21
depends on.

Suite baseline for anything you cite: **21 failed / 3547 passed / 1 skipped**, the 21 failure IDs
being the published set in master plan §10.

One caveat worth knowing before you write a concurrency row: plan 8 **C5(a)**'s two-session race
fixture was measured this round **not to force its race** — the lock was removed and the test
stayed green 9 runs out of 9, because one session's connection is warm and the other's opens
lazily after the barrier. The owner accepted that as a known gap. **Do not copy that fixture
pattern into this phase.** This phase is read-only and should need no two-session row at all; if
you think it needs one, say why rather than reaching for the existing shape.

## Deliverable

`SR/plans/plan_8A.md`, in the house shape of the other plan files: goal, contract resolution,
files expected to change, tasks, criteria table with its §6 preamble, notes, Review log stub.

Say plainly in §7:
- that the extraction touches `create_stock_task_assignments.py`, an **APPROVED** phase-8 file,
  and that plan 8's suite passing unchanged is the evidence for it;
- which rows you chose **not** to write for the extraction half, and why — an explicit
  under-specification with a reason is worth more than rows nobody needs;
- any place §14G is ambiguous. **Do not resolve an ambiguity by choosing** — raise it as an owner
  card under `⚠ OWNER DECISIONS REQUIRED (n)`.

This phase runs a reduced flow by owner ruling (2026-09-21): **projection → implement →
orchestrator review by hand.** No tester session and no independent reviewer. Write the plan so
that a single implementer can arm every row it carries.
