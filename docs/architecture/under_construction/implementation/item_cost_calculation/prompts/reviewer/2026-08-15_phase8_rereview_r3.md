---
plan: phase 8 (status & results — status query, result handler, §8B emissions)
role: reviewer (re-review)
round: 3
date: 2026-08-15
---

# Session prompt — re-review phase 8, round 3 (after fix r2)

You are the **re-reviewing agent** for phase 8, round 3. Round 2 closed
12/13 r1 findings and found 2 blocking / 3 should-fix — ALL test-side; fix
r2 delivered exactly the H1–H7 list with ZERO production edits (verified:
the checkpoint contains four test files and two docs, and the three
mutation-target production files hash back to their r2 pre-images). This
round is a THIN delta review: verify the five corrections bite and nothing
regressed. Approval is expected if the arbiters hold — do not manufacture
scope.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Ground

- Your r2 handoff: `handoffs/reviewer/2026-08-15_phase8_rereview_r2_handoff.md`
  (MX1/MX2 mutant hashes; the S1 flake evidence; H-corrections specified).
  Fix handoff: `handoffs/implementer/2026-08-15_phase8_fix_r2_handoff.md`
  (ticked H-list; 6-row ledger with per-row mutant hashes — the P-I 9th
  hard field landed).
- Plan: `plans/phase_8_status_results.md` — A1–A18 + G1–G10 + **H1–H7
  GOVERNING**.
- Checkpoint **`6988364`** (6 files: 4 test + 2 docs; handoff after).
- Coordinator consumption (verified, do not re-litigate): diff-app empty;
  the three mutation-target production files restored byte-identical
  (`d57ca890…`, `5f89e29b…`, `011cf2ae…`); the adopted-probe final hash
  matches the declaration (`7df683f7…`); **MX1 and MX2's mutant hashes in
  the fix ledger REPRODUCE your r2 bytes exactly** (`fdae3c41…`,
  `57c4591f…`).

## Environment facts

- Head `c1d2e3f4a5b6` (unchanged). Declared: focused 146; H3 subset 2×10
  flake-free; full **2138 / 23 / 1**, sorted failure IDs = the phase-1
  set. Graph untouched: 172/254, rev `c74eb913…`, 21 pending held.

## Explicitly OUT of scope (do not re-run)

The other 15 ledger rows (M4–M16, M18, G7/G8) were proven biting in r2
against production files that are byte-identical today — re-running them
is manufactured scope. The settled r1/r2 mechanism re-derivations stand.
One full-suite foreground run suffices (plus the H3 subset loop). Expected
session shape: the four probes below + one suite run + two fixture reads —
if you find yourself past that, it should be because you FOUND something,
and then depth is right.

## Probes (minimum)

- **R3-P1 — MX1/MX2 re-run from YOUR mutant bytes:** apply your own r2
  mutants (hashes reproduce, so `git apply`-equivalent edits should land
  identically); each must redden its named row
  (`test_c4_…` `assert 150 == 120`; `…[P-V-infeasible]`
  `assert 'ok' == 'infeasible'`). Confirm the H1 rows drive
  `get_task_budget_status` (not a hand-built object) and H2's fixture
  carries all three nonzero excluded columns.
- **R3-P2 — the S1 flake is dead:** read the two repaired C1 probe rows —
  candidate-SET assertions, no order dependence; run the pair yourself
  ≥10× (a 2-test subset — seconds per run); regression-sample **M1 and M2
  only** from your r2 mutant bytes (the fix's ledger shows M3/M17 biting
  too — do NOT re-run them; their production files are byte-unchanged
  since your r2 pass).
- **R3-P3 — H4/H5 read hard:** the rebuilt C5 supersession row commits a
  real superseding basis version with a different rate (non-vacuity
  assertion present — the new rate WOULD change the number; P-J 5th ext);
  C3's two steps sit on TWO tasks with their own evaluations, each
  episode 1800. These two are the only newly-authored fixtures this
  cycle — nobody but their author has read them.
- **R3-P4 — H6 ride-alongs:** the re-entry claim counts; the
  `response_model` row quantifies over ALL routes (probe: set one on any
  route → red).
- **R3-P5 — numbers:** full suite foreground yourself; failure set
  byte-compared (sorted diff); collection delta reconciled (echo-row
  deletions vs additions); committing subsets twice, residue named; ruff
  on the perimeter; DB at head after your passes; tree == `6988364` blobs
  at close.

## Closing protocol

1. Verdict, counts from the ledger (P-L). Owner cards only for semantic
   decisions.
2. Mutations: per-row sha256 pairs (before AND mutant — the hard field),
   observed reds, reversion proven.
3. If APPROVED: full carry-forward dispositions table (the 21 pending
   graph items + migration mapping + the three A16 discrepancy filings +
   the status queries' node-type question → the coordinator's
   post-approval pass; the alembic-check drifts + N11 residue class →
   their existing homes; anything new → named landing spot). Anchor spans
   for held items only if something moved (this cycle touched no
   production file — expect none).
4. Deposit AFTER your writes, citing final hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-15_phase8_rereview_r3_handoff.md`
   (full path): findings ledger; closure table for r2's 2B/3S; mutation
   ledger; full write perimeter + probe declaration; lessons.
