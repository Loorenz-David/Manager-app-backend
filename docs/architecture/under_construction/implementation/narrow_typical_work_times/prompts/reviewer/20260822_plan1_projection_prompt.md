---
plan: plan_1
role: projection
round: 0
date: 2026-08-22
---

# Session prompt — plan-projection (round 0), phase 1 of `narrow_typical_work_times`

## Role and workspace

You are the **plan-projection gate** for phase 1 (the pure typicals domain + the
pre-refactor SQL snapshot): you do the implementer's first hour on paper, **without
permission to improvise**, adversarial to the plan's author — assume every task hides a
decision the artifacts do not actually determine. Run as Opus 5, in a fresh session.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Do not push. Do not commit. Do not edit the plan, the intention, or
  any code** — you report; the coordinator routes.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below: `<project>/`).

Doctrine, read first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

## Gate check (stop-and-report if any fails)

1. `<project>/master_plan.md` §4 tracker: phase 1 `NOT_STARTED`, projection MANDATORY.
2. `<project>/plans/plan_1.md` exists with an empty Review log.
3. `<project>/planning/intention.md` header: RESOLVED (round 7), 0 owner cards open.

## Inputs discipline (the skill's rule 1, instantiated)

Read **only what the implementer will get**:

- `<project>/plans/plan_1.md` — the subject.
- Its §2 Read-first list, in full: the named master plan sections, the named intention
  sections (honour the header's **section-letter precedence rule**), the named
  owner-decision entries, the named gate-handoff rows, and the named code files.
- The actual codebase, without restriction.

**Do NOT read:** `<project>/handoffs/planner/` (planning-session context — what you
cannot derive from the artifacts, the implementer cannot either), or anything under
`<project>/prompts/coordinator/` (coordinator-private).

## Depth allocation (by silent-failure risk — these are the phase's rule-6 mechanisms)

Deep passes on: the spec's canonicalization and dedupe identity (C1–C4); the resolution
ladder's and reconciliation quantifier's totality **over every evidence shape the
dataclasses permit**, not only the shapes SQL produces (C6–C8, C10); the query-parameter
parser as a future public contract (C14); and the snapshot capture (task 1 / C15) — its
exact mechanics, reproducibility, and the both-clock-forms claim it rests on. Config
plumbing (the constants move) gets a glance.

These are named as *areas*, not conclusions — what you find there is yours.

## Procedure (the skill's, in brief)

Walk the plan task by task; write the skeleton (signatures, control flow, per-file
sketches) on paper. Every point where you must stop and choose goes into the **decision
ledger**: plan gap → proposed plan amendment; intention gap → route upstream; free
choice → proposed explicit delegation. Then the reality checks (every path in §4 exists
or is marked new; every cited section resolves and says what the plan claims) and
criteria decidability (could you write each test right now, from the artifacts alone,
with one exact expected outcome per case?).

## Evidence budget

**This session's L4 budget is exactly 0 runs, and its test-execution budget is 0 at
every scope.** This is a paper gate: static reading only. The docs guard is not required
— your one output file lands under `docs/architecture/under_construction/`, which the
guard's roots (`app/`, `docs/handoff/`, `docs/domains/item_economics/`) do not cover.

## Write perimeter (declared in full in your handoff; anything else is a finding)

- `<project>/handoffs/reviewer/20260822_plan1_projection_handoff.md` — your report.
- Nothing else. The skeleton is **discarded** (or attached only as a clearly-marked
  non-authoritative appendix). One line in plan_1's Review log is written by the
  coordinator at the fold, not by you.

## Closing protocol

Handoff at `<project>/handoffs/reviewer/20260822_plan1_projection_handoff.md`,
frontmatter `plan: plan_1`, `role: projection`, `round: 0`, `date`, `verdict`
(**PROJECTED_CLEAN** | **AMENDMENTS_REQUIRED**), `actor`. Body, in order:

1. Owner-readable opening (3–5 sentences, no citations or jargon).
2. `⚠ OWNER DECISIONS REQUIRED (n)` — cards in charter format, or the one-line "zero
   cards".
3. The decision ledger as a table: decision point / classification (plan gap ·
   intention gap · free choice) / proposed routing.
4. Reality-check and decidability findings, each with the exact artifact and line.
5. Full write perimeter from `git status`, and the line "L4 runs: 0; tests executed: 0".

Your final chat message is the charter's **owner layer**: what you did → what it means →
what happens next → what needs you; plain product words; one pointer line naming the
handoff file.
