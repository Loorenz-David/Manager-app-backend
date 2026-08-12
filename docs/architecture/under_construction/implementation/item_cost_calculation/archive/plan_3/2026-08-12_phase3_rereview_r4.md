---
plan: phase 3 (canonical calculator)
role: reviewer
round: 4 (re-review, delta-scoped — S6/N14/N16 only)
date: 2026-08-12
---

# Session prompt — re-review phase 3 after fix cycle r4

You are the **re-reviewing agent** for phase 3, round 4 — the narrowest scope of
the phase: three pre-verified corrections. Settled ground is not re-derived;
anything seen wrong in passing is reported.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (settled)

- r1–r3: everything except S6/N14/N16 is settled (see the three Review-log
  entries' verified-ground sections; r3 confirmed B3 total against 17 hostile
  inputs and regression-checked the C7 tripwire).
- **Fix r4 (Codex, checkpoint `71f137b`; handoff deposited AFTER, citing the
  hash — the discipline held this round):** S6's verified cascade fixture
  (`399.5000` → allowance `5.42`/`5.42`); N14 four-key homogeneous payload
  (`error: None` on plain entries) with per-branch observed node ids; N16 ORM
  swap. N12/N13 not taken (optional, compliant).
  Handoff: `handoffs/implementer/2026-08-12_phase3_fix_r4_handoff.md`.
- **Deviation to weigh, not auto-file:** r4's probes ran in the MAIN worktree
  (reverted; final sha256s declared: calculator `03389d0a…af8eb0`, tests
  `6733181e…5daa86`). The checkpoint predates the probes' reversion claim —
  verify both current files hash to the declared values and match `71f137b`'s
  blobs exactly; if they do, the deviation is procedural only (note it), if not
  it is a finding.

## Step 1 — verified perimeter

`git show 71f137b` = exactly four files (+4 lines calculator, ~20 tests, tracker
row, Review log). The handoff deposit commit (`3a80ee3`) carries only the handoff.

## Step 2 — delta probes (the whole scope)

- **R4-P1 (S6 — the one that matters):** re-run the clause deletion
  (`or rate != stored_rate`) yourself: with the new `399.5000` fixture, exactly
  `test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload` must
  fail — the pin now has its arbiter. Verify by hand that at `399.5000` the
  allowance re-derives to exactly the stored `5.42` (so the cascade clause is the
  sole cause).
- **R4-P2 (N14):** every mismatch entry — plain and converted — carries exactly
  the four keys; spot-check one plain-entry `error: None` assertion bites
  (corrupt the key; observed node id).
- **R4-P3 (N16):** the malformed-purchase row holds an unsaved
  `ItemCostEvaluationTerm` (rule 3), consistent with its five siblings.
- **Suite:** 1749 passed / 23 failed / 1 deselected expected (failure set
  byte-identical; N14-flake caveat). Focused 65.

## Closing protocol

1. Review log entry (append-only); tracker verdict — **APPROVED** expected if the
   three items verify; actor stamps preserved.
2. Archgraph read-only: still 1 pending (held node), revision `671fd92a…`, zero
   delta; state it. With approval, the coordinator runs the single held
   adjudication (card 3) — note the calculator's final line numbers for the
   anchors if convenient (spans covering the module header/constants, the term
   family, and `validate_currency_equality`+`rederive`).
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase3_rereview_r4_handoff.md`
   (full path, AFTER your Review-log/tracker writes): summary; `⚠ OWNER DECISIONS
   REQUIRED (n)`; probe results; full write perimeter + probe declaration.
