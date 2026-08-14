---
plan: phase 5 (valuation surface)
role: reviewer
round: 2 (re-review, delta-scoped — B1–B4, S1–S5, N1)
date: 2026-08-14
---

# Session prompt — re-review phase 5 after fix cycle r1

You are the **re-reviewing agent** for phase 5, round 2. Delta-scoped;
review r1's "Verified correct" list is settled ground.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (settled)

- r1 (your predecessor): surface right, evidence didn't hold — B1 REAL defect
  (delete-then-reset undeletable), B2 C5 enumeration unbuilt, B3 L15 row
  absent, B4 currency clauses un-arbitrable pairwise (transitivity), S1–S5,
  N1 (L12's named mutation inert). Every correction was executed by r1.
- Fix r1 (Codex, checkpoint `a0cebde`, final): production diff exactly TWO
  lines (delete predicate +1; redundant middle currency clause −1); the rest
  test-side. Handoff:
  `handoffs/implementer/2026-08-14_phase5_fix_r1_handoff.md`.
- Coordinator consumption (settled): perimeter exact (7 files, handoff-only
  deposit); arithmetic READ and exact (1968/23/1 = 1991 selected, +18);
  **both final production hashes are byte-identical to files YOUR PREDECESSOR
  produced** — `ab9aebbe…` (delete_item_valuation.py) = r1's B1
  correction-verification file, `75087586…` (configuration.py) = r1's M5.b
  probe (the 2-clause reduction). The fix shipped the verified corrections
  exactly. M5's observed cross-mapping (drop val≠basis → `[basis-model]`
  reds) is consistent with ids renamed to the pair held EQUAL — confirm the
  renaming reads that way.

## Step 1 — perimeter (fast)

`git show a0cebde --stat` = the 7 declared files; `git status --porcelain`
clean; `git diff a0cebde..HEAD -- app/` empty. Ruff on changed files.

## Step 2 — delta probes (the r1-green mutations must now bite)

- **R2-P1 (B1, through the SHIPPED surface):** PUT → DELETE → PUT → DELETE on
  one item succeeds end-to-end; afterwards exactly one INV-V1-current row and
  the state carries two `superseded_at IS NULL` rows. Re-run the B1-revert
  mutation (expect the delete row red; mutant hash `23cfe90f…` = the old
  unfixed file).
- **R2-P2 (B2, P-V):** C5's 12 parametrize ids map one-for-one onto §11A.4's
  values — no duplicates/omissions; the two recorded judgments present
  (`ok`/`infeasible` task-scoped; ambiguous INV-G3-unreachable); sample three
  rows' fixtures for sole-predicate; every row asserts null numerics where
  owed AND `item_cost_evaluations` unchanged. Re-run M4 (inline snapshot
  read) — expect the B3 structural row plus C5 rows red where r1 saw 345
  green.
- **R2-P3 (B4/S1):** re-run both 2-clause drops (each reds exactly its
  renamed id) and M3.2 (precedence swap 2↔3 — reds the new S1 fixture where
  r1 saw green); confirm the B4 reduction did not weaken the three fixtures
  (all three states still reject).
- **R2-P4 (S2/S3/L13):** the shared delete-then-reset fixture proves C4's
  re-set row, C6's three-supersession ordered history (re-run M8 and M8b —
  both r1-green, both must red), byte-identical re-read, and the INV-V1
  current-count assertion.
- **R2-P5 (S4/S5):** both race blocks now count INV-V1-current `== 1` and
  path (i) asserts its blocking observable; C3 carries the missing-currency
  reject + three accept rows + the phase-2 node-id citations. Run the race
  subset twice; residue scope named.
- **R2-P6 (N1):** the fixture's persisted rate is `13.0000` → `76923.08`;
  re-run BOTH M10 (the named calculator swap — inert in r1) and M10b — both
  must red.
- **Suite:** expect 1968/23/1, failure set byte-identical to the phase-1
  baseline; state numbers read off your run.

## Step 3 — graph (read-only)

Zero delta expected this cycle (revision `b5e6fe09…`, 153/195, 12 pending —
NOT yours to adjudicate). Spot-check that r1's anchor-spans table is still
valid for the two files this fix touched: `delete_item_valuation.py` (+1 line
— the node span 17-43 and writes_to span 38-41 may have shifted) and
`configuration.py` (−1 line — N7's recommended `resolve_economics_selection`
span 80-126 may have shifted). Deliver corrected final spans for any that
moved — the coordinator's post-approval pass depends on them.

## Closing protocol

1. Review log entry; tracker verdict (**APPROVED** expected if the delta
   verifies); stamps preserved.
2. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase5_rereview_r2_handoff.md`
   (full path, AFTER your writes): summary; `⚠ OWNER DECISIONS REQUIRED (n)`;
   probe results with copy-pasted sha256 pairs; corrected anchor spans if any;
   full write perimeter + probe declaration.
