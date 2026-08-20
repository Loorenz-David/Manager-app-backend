---
plan: 2
role: reviewer
round: 3
date: 2026-08-20
project: live_clock_for_working_time_economics
---

# Session prompt — plan 2 review (round 3), `live_clock_for_working_time_economics`

## 1. Role and workspace

You are the **plan reviewer** for phase 2. This is the **first review of this phase** —
run the full checklist, not a delta scope. Implement r1 went straight to a
coordinator-dispositioned fix cycle (r2) because three criteria were measurably absent;
no reviewer has yet seen any of this phase.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (tests: `PYTHONPATH=. pytest -m 'not e2e'`)
Project folder:
`backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

**Read these two files first and follow them as this session's doctrine**, by absolute
path: `/Users/davidloorenz/agent-skills/pipeline-charter.md` and
`/Users/davidloorenz/agent-skills/plan-reviewer.md`. If you are a Claude session,
invoking the `plan-reviewer` skill loads the second; read the charter regardless.

## 2. Gate check — stop and report if any is false

- `master_plan.md` §3 shows phase 1 **APPROVED** and phase 2 **REVIEWING**.
- `plans/plan_2.md` §7 carries three consumption entries: projection r0, implement r1,
  fix r2.
- Working tree clean; `HEAD` at the fix checkpoint or later.

## 3. Read order

1. `plans/plan_2.md` **in full** — §5's C1–C12 are the contract you review against, and
   §7's three consumption entries tell you what is already settled and by whom.
2. `master_plan.md` §4 (N-1…N-4), §5 (**fifteen earned rules**), §6 (environment, the
   enumerated failure-ID set, the three flaky tests, the `TZ` fact, and the post-phase-2
   test-environment plan), **§7 including *Recognized external commit streams*.**
3. `planning/intention.md` — §1A HC-1A/HC-3A through round 4e, §4.1/§4.1A, §4.3A, §2.6,
   §5.2, §9A.
4. The diff under review: `git diff 487b98a..HEAD -- app/` (implement r1 + fix r2).
5. The two handoffs under `handoffs/implementer/` for this phase.

## 4. What is already settled — do not re-spend effort here

The coordinator verified these independently; re-deriving them is waste. Report only if
you find them **wrong**.

- **Perimeter, both rounds.** Implement r1 = the declared 12 files; fix r2 = test-only,
  zero `app/beyo_manager/` lines.
- **Baseline.** 26 / 2476 / 1 on the post-cap tree, failing-ID set identical to §6's
  enumeration in both directions.
- **Six mutations measured by the coordinator at implement r1** (C3, C5, C6 `latest_state_record`,
  C6 E-A eager load, C7, and the four clock call sites), and **two re-measured after fix r2**:
  C6 `created_at` ⇒ exactly 1 added ID; C8 loop-local ⇒ exactly 2. Both were **∅** before
  the fix.
- **The C6 ordering fixtures are correct at source** — row 2 ties `entered_at` so
  `created_at` decides; row 3 keeps them distinct and swaps `created_at`; they are not
  merged.
- **The production code matches plan §3/§4** file by file, including
  `typical_worker_seconds=None` being behaviour-preserving.

## 5. Depth targets — where this phase can still be silently wrong

Charter rule 6. In this order:

- **F-L4, the corrupted ledger row (plan §7, fix r2 entry).** Ledger row 4 claims seven
  added IDs for the C6 `created_at` mutation; the coordinator measured **one**, and six of
  the seven are structurally impossible or belong to the parallel cap stream. Treat every
  row measured in that window as suspect: **re-measure a sample of two or three rows
  yourself**, whole-suite, both-direction ID diff, and say whether the ledger reproduces.
  A ledger that cannot be reproduced is a finding regardless of whether the code is right.
- **C9's vacuity.** C9 names no production mutation — correctly, the plan specifies none.
  Its contract is three-point (`2040` → `1440` → `2040`). Ask the question the criterion
  cannot ask itself: **is there a single production change that satisfies all three
  points wrongly?** If yes, name the mutation the plan should have carried.
- **The C11/C12 shared call-site test.** Four distinct call-site mutations each redden the
  *same* single test. Coverage holds; diagnosis does not. Judge whether that is acceptable
  or whether one of the four could regress unnoticed behind another's failure.
- **HC-5 across surfaces, on the payload rather than the fold.** Every criterion asserts
  the fold or one surface. Walk the *payloads* of E-P, E-B (both faces) and E-A for one
  fixture and check no derived field disagrees — the phase's whole purpose (§5.2
  criterion 3).
- **HC-1A on the E-A path specifically.** C5's rows cover the surfaces; confirm nothing in
  the batch path writes a step attribute, including through `DivisionStep` construction.
- **Charter 11½ on the C9 fixture.** It drives a production transition that enqueues an
  outbox row. Does it own its teardown?

## 6. Constraints and protocol

- **Perimeter check is step 1** and must consult §7's *Recognized external commit streams*:
  files in the cap stream's list are foreign-but-expected; anything else outside the
  declared perimeters is an automatic finding. **A golden JSON moved by a cap commit is an
  escalation to the owner, not an attribution.**
- **Measure on the tree you actually run on.** The cap stream commits into this repo while
  we work; never carry a pass count between rounds. Diff the enumerated failure-ID set.
- Any mutation you run: full suite, both-direction ID diff, revert, verify the revert.
- Citations are `path:symbol`, never bare line numbers.
- You write your handoff and nothing else — no code, no plan edits, no tracker row.
- Never promote, reject or edit an archgraph review item; three sit pending the owner.

## 7. Closing protocol

Deposit at `handoffs/reviewer/2026-08-20_phase2_review_r3_handoff.md`, frontmatter
`plan: 2`, `role: reviewer`, `round: 3`, `verdict`, `date`, `actor`.

- Verdict: **APPROVED** or **CHANGES_REQUESTED**.
- An owner-readable opening (3–5 sentences, no citations), then
  `⚠ OWNER DECISIONS REQUIRED (n)` — decision cards in the charter format, or one line
  saying none.
- Findings as **blocking / should-fix / notes**, each with its exact citation and, where
  it names a defect, **the mutation that must turn a test red** and both sides of it.
- Your re-measurement of the sampled ledger rows, with the IDs you observed.
- Lessons for the plans, routed by artifact (intention / master plan / this plan /
  next phase).
- Your **full write perimeter** from `git status` / `git diff --name-only` — which for
  this session must be exactly the one handoff file.
