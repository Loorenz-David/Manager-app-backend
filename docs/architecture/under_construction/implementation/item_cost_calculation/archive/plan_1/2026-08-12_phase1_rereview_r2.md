---
plan: phase 1 (worker money redaction)
role: reviewer
round: 2 (re-review, delta-scoped)
date: 2026-08-12
---

# Session prompt — re-review phase 1 after fix cycle r2

You are the **re-reviewing agent** for phase 1. This is a **delta-scoped re-review**
per the charter protocol — settled ground is not re-derived.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` (re-review protocol in
   "Review protocol").
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (what is settled, and by whom)

- **Review r1 (Claude, CHANGES_REQUESTED):** the redaction itself was approved on
  the merits — eight-endpoint census independently re-derived, mutation battery
  8/8 re-run in a disposable worktree, zero regressions (23 pre-existing failures,
  sets byte-identical at `545e504` and `4416570`), perimeter exact, scope fences
  held. The settled ground is enumerated under **"Verified correct"** in the
  phase-1 Review log and in
  `handoffs/reviewer/2026-08-12_phase1_review_r1_handoff.md` — do not re-derive
  it; anything seen wrong in passing is still reported (this clause catches real
  bugs; it is not decorative).
- **Open items resolved by fix r2 (Codex, checkpoint `ed99e7e`):** S1 (five ADMIN
  criteria rows untested) and S2 (baseline record wrong — verified 23, not 22).
  Optional notes N3/N4/N6 were declined (documented). N1/N2 are routed to phase 9;
  N5 is a coordinator process lesson — none of these is re-review scope.
- Fix handoff: `handoffs/implementer/2026-08-12_phase1_fix_r2_handoff.md`.

## Step 1 — verified perimeter (mandatory first step)

`git show ed99e7e` must contain **only** the fix prompt's allowed files: the four
test modules, the phase-1 plan (Review log), and the master-plan tracker row.
Anything else is an automatic finding. Note: coordinator docs commits (`d457d84`,
`6adb34d`, `e82da72`, `e801d09`, `3e40646`, `65a20f0`) sit around the checkpoint —
attribute them to the coordinator; the fixer's perimeter is the single commit
`ed99e7e`.

## Step 2 — full adversarial depth on the changed seam (probes)

- **R2-P1 (the reshaped function):** the reassigned/pending test was parametrized
  over manager/admin — verify the WORKER redaction assertions (criteria rows 19 and
  22) **survived the reshaping** and still execute (collected and passing, asserting
  key ∉ dict), and that all five S1 rows (9, 12, 17, 20, 23) now have live tests
  asserting `== 4321` (equality, not presence).
- **R2-P2 (baseline record):** the S2 correction line under the implementer r1
  entry is append-only (nothing above it altered), carries the verified pair
  (`545e504` → 1578/23/1; `4416570` → 1600/23/1), and its 23-item list matches the
  r1 reviewer's verified list exactly.
- **R2-P3 (liveness of the new rows):** fix r2 ran no mutation probes. Run the two
  blanket-`False` probes (site-5 derivation; `build_step_record_payload`
  derivation) and confirm the new ADMIN rows go red alongside their MANAGER
  neighbours (rows 15b/15 and 23/24); re-run M4/M5 since their witness tests were
  reshaped. Disposable worktree, revert, sha256-verify, declare.
- **Arithmetic:** collection 1624 → 1629 must equal exactly the added parametrize
  rows; full suite 1605 passed / 23 failed / 1 deselected against the recorded
  baseline.

## Step 3 — full suite + spot-check of dependents

`PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/` (containers up via
`make dev-up`; a run with connection noise is never evidence — stop and report).

## Closing protocol

1. Review log entry (append-only) in the phase-1 plan; tracker row (yours only):
   **APPROVED** or **CHANGES_REQUESTED** with a one-line note — keep existing
   actor stamps intact.
2. Archgraph: read-only orientation; zero delta expected (state it).
3. Deposit the handoff at
   `handoffs/reviewer/2026-08-12_phase1_rereview_r2_handoff.md` (frontmatter
   `plan`, `role`, `round: 2`, `date`, `state`, `verdict`, `actor`): summary;
   `⚠ OWNER DECISIONS REQUIRED (n)` (one line if zero); probe results R2-P1…P3;
   findings (if any) with verbatim correction clauses; lessons for the plans; full
   write perimeter incl. mutation-probe declaration. **Deposit the handoff before
   ending the session** — it is part of the work, and the coordinator's closeout
   is blocked without it.
