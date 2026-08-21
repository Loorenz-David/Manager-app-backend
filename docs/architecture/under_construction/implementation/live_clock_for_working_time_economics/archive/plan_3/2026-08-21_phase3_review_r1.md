---
plan: 3
role: reviewer
round: 1
date: 2026-08-21
project: live_clock_for_working_time_economics
---

# Session prompt — plan 3 review r1 (first review), `live_clock_for_working_time_economics`

## 1. Role and workspace

You are the **first review** of phase 3: D9, the frozen percent blocks. You did not write
this code and must not assume it is correct — or wrong. Your output is findings and a
verdict; you **never fix**, and you never relitigate the plan (plan complaints are
"lessons", not blockers).

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (suite: `PYTHONPATH=. pytest -m 'not e2e'`)
Project folder:
`backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

**Read these two files first and follow them as this session's doctrine** (plain
markdown, by absolute path):

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

If you are a Claude session, invoking the `plan-reviewer` skill loads (2); read (1)
regardless.

## 2. Gate check — stop and report if any of these is false

- `master_plan.md` §3 shows phases 1 and 2 **APPROVED** and phase 3 at **REVIEWING**.
- The checkpoint commit is **`5b8329b`** (`CHECKPOINT (not approved): implement phase 3
  D9`), parent `88c8f5f`, and the working tree is clean at it.
- `plans/plan_3.md` carries four Review-log entries (two coordinator pre-round, one
  implementer, one coordinator consumption).
- No unconsumed handoff sits in `handoffs/reviewer/`.

## 3. The evidence policy changed — read this before you run anything

Charter **"Test-evidence scope and reuse"** (2026-08-21) governs this review, and it
changes what independence means:

- **Do not reproduce identical commands on an unchanged tree.** The implementer's L4
  stamp — `26 failed / 2486 passed / 1 deselected`, baseline IDs unchanged both
  directions — is **tree-bound and already verified cryptographically** by the
  coordinator: the declared dirty-tree digest `d2ca0320…` reproduces exactly as the
  `app/` + `docs/domains/` diff between `88c8f5f` and `5b8329b`. Cite it. Re-run the full
  suite only if **your** tree differs from `5b8329b`, or you change code.
- **Spend your budget on variation instead**: a site, condition, fixture or mutant shape
  nobody has tried; the cases the tests do not cover; and whether the *scope* each
  criterion was proven at was sufficient for its hypothesis.
- Mutation probes run at the scope their hypothesis requires (`plans/plan_3.md` §5B
  assigns one per row). An absence claim ("nothing anywhere guards X") is L4 by
  construction; "this named row bites" is not.
- Every evidence record you produce carries hypothesis · scope · command · tree identity ·
  result · ID delta. Declare your probes and prove they were reverted.

## 4. Read order

1. `plans/plan_3.md` in full — §5 criteria (C1, C2, C3, C4a, C4b, C4c, C5, C6a, C6b),
   §5A (what phase 2 earned), §5B (fixture numbers + scopes), §6 (three traps), §6A
   (delegations P3-D1…P3-D3), §7 Review log.
2. `handoffs/implementer/2026-08-21_phase3_implement_r1_handoff.md` — the ledger you are
   auditing.
3. `master_plan.md` §4 (N-4, the `D`-namespace registry), §5 (earned rules — they bind),
   §6 (environment; the **graph is not clean**: 9 pending / 2 stale; repo-wide ruff has
   136 pre-existing errors; the ⛔ phase-4 gate).
4. `planning/intention.md` §5.3 + **§5.3A**, §4.1A B, §4.2, §9A T13, §10.3 D9,
   **§10.4 OD-10**.
5. The diff itself: `git show 5b8329b`.

## 5. Settled ground — do NOT re-spend the round here

The coordinator verified all of the following independently at consumption. Re-deriving
them is waste; **contradicting** one is a finding and worth reporting loudly.

- **Perimeter**: 10 declared items = 10 files in `5b8329b`, no others.
- **Tool state**: `archgraph_status` revision `120c4c38…` is byte-identical to the
  pre-session reading — no graph writes occurred.
- **Lint**: ruff clean on the five changed files; the repo-wide 136 errors are unchanged
  from the parent commit.
- **Ledger arithmetic**: 2479 + 7 = 2486; all three L4 rows total 2512 collected; the C5
  site asymmetry (E-P reddens `test_c17`, E-B does not; neither reddens C1/C2) is
  internally consistent with the `variance = 0.00` fixture.
- **`test_c17` class sweep**: it is the **only** test in the repository asserting
  `final.percent == budget.percent`.
- **N-4's identity**: verified at every boundary by the projection and re-derived by the
  coordinator at nine quantization-stressing values. Do not re-litigate it.

## 6. Probes — extracted from the implementer's report and the coordinator's consumption

Each is a question, not an accusation. Answer it with evidence.

- **P1 — two criteria in one test function.** C4b is asserted inside
  `test_c1_ep_final_freezes_while_budget_percent_ticks` (declared, and permitted by
  P3-D2). The coordinator checked both criteria carry independent exact literals. Your
  question is the one after that: **because both mutations report the same test ID, the
  ledger cannot attribute which assertion bit** — the same attribution weakness the plan
  flagged for the goldens test. Is that acceptable evidence, or should C4b be its own row?
  Judge it; do not assume the coordinator's answer.
- **P2 — C3's after-state coincidence.** In C3's *after* state the live and frozen
  percents **both equal `80.00`**. The row survives because its `before` assertion
  discriminates. Verify that nothing load-bearing rests on the coincidence, and say
  whether the row should assert `before["budget"]` (≈ `120.00`) so the live percent is
  shown *moving* rather than merely landing.
- **P3 — is the C6a/C6b pair actually complete?** The claim is that C6a kills a
  status-based blanking implementation and C6b kills a positive-fallback one. Attack it:
  write the wrong implementation that passes **both** rows, or prove none exists.
  C6b does not assert `status` — does that matter?
- **P4 — the degenerate fixture, used deliberately.** C1/C2/C4b/C4c sit on
  `_make_live_fixture` at `variance = 0.00`, where `actual` and `actual + variance`
  coincide. §5B sanctions this for those rows. Confirm each of those four rows still has
  a *sufficient* discriminator there, and that no row silently depends on the degeneracy.
- **P5 — the shipped prose.** `docs/domains/item_economics/README.md` and `states.md`
  were edited, and the `_serialize_production_time_final` docstring was corrected. A
  comment asserting a property is a claim and inherits the mutation rule (master §5).
  Verify what the new text **asserts** is true, and sweep the class: does any other
  document under `docs/domains/` or `docs/architecture/` still carry the old
  "`percent_consumed` is null for infeasible" rule without the live/frozen split? (The
  published frontend handoff carries it deliberately and is **phase 4's** to correct —
  not a finding here.)
- **P6 — `test_c17` recorded, not retargeted.** The implementer left a test whose name
  asserts D9's negation, green by fixture coincidence, and recorded that in the Review
  log. The plan permitted either. Assess the judgment on its merits: is a recorded
  coincidence sufficient, or does a knowingly-misleading test name now ship?
- **P7 — what the phase does not guard.** Beyond the criteria: is there a path that
  reaches either frozen percent that no row covers? The manager face, the price-scenario
  endpoint (a **shipped** consumer of `get_task_budget_status`), the item-lifetime
  economics serializer. Scope your answer's evidence accordingly — an absence claim over
  the repository is L4 and needs its search terms recorded beside it (master §5).

## 7. Closing protocol

Per `plan-reviewer.md`: a **mutation-probe declaration** (every file touched, reverted,
verified) and every database/state side effect restored; a **carry-forward dispositions
table** if you approve with open notes; tracker row (REVIEWING → APPROVED /
CHANGES_REQUESTED — **your row only**); technical findings appended to
`plans/plan_3.md`'s Review log (layer 1, lean); and a **handoff file** at
`handoffs/reviewer/2026-08-21_phase3_review_r1_handoff.md` (frontmatter `plan`,
`role: review`, `verdict`, `date`, `actor`) carrying the verdict, findings by severity,
lessons for the plans, and any owner item as a **decision card** in the charter's
`⚠ OWNER DECISIONS REQUIRED` section (one line if there are none).

Your final chat message carries the **layer-2 human briefing**: a 2–4 sentence plain-language
state of the build, then a short faithful narrative for every blocking and should-fix
finding, told in the owner's domain with concrete kronor and minutes — the frozen
percentage on a finished job is a number a person reads as history, so make the
consequence felt in those terms.

The handoff file, not the chat message, is what the coordinator consumes.
