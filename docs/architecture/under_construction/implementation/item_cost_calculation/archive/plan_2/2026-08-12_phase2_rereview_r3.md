---
plan: phase 2 (schema, models & migration)
role: reviewer
round: 3 (re-review, delta-scoped — single finding)
date: 2026-08-12
---

# Session prompt — re-review phase 2 after fix cycle r3 (B5 only)

You are the **re-reviewing agent** for phase 2, round 3. This is the narrowest
possible re-review: one finding (B5) was open; verify its resolution and nothing
else is re-derived.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` (re-review protocol).
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (settled — do not re-derive)

- **r1:** schema approved on the merits (Review log "Verified correct").
- **r2:** 7/8 r1 items verified closed (full 16-CHECK sweep, 25-row C2 mapping,
  maintenance fix verified); only **B5** remained: INV-G1's (a) row used one group,
  so the index key width had no live arbiter. Notes N8/N12/N13 are next-touch (N12/
  N13 were explicitly optional and NOT taken in fix r3 — that is compliant, not a
  finding); N10/N11 are filed maintenance; N9 recorded.
- **Fix r3 (Codex, checkpoint `e9d6ac6`, final, not amended):** second
  `ProductionCostGroup` in the fixture branch; `sections_conflict` now shares only
  `(workspace_id, working_section_id)`; `sections_removed` is the one-clause
  `removed_at` delta on the second group. Handoff:
  `handoffs/implementer/2026-08-12_phase2_fix_r3_handoff.md`.

## Step 1 — verified perimeter

`git show e9d6ac6` must contain only: the schema test module (+7/−2), the phase-2
plan (Review log), the master-plan tracker row. Anything else is a finding.

## Step 2 — B5 verification (the whole scope)

1. Read the fixture branch: confirm the two memberships share exactly
   `(workspace_id, working_section_id)` and differ in group (the (a) row), and that
   `sections_removed` differs from (a) only in `removed_at` (still on the second
   group).
2. Re-run the key-widening mutation yourself (disposable DB via the §10
   from-scratch recipe; widen `uix_production_cost_group_sections_active` to
   include `production_cost_group_id`, name preserved): exactly
   `sections_conflict` must redden; restore; module green (79). Declare with
   sha/DDL verification.
3. Full suite on HEAD: expect 1684 / 23 / 1, failure set byte-identical to the
   baseline.
4. Anything seen wrong in passing is reported (the clause is real, not decorative)
   — but nothing settled is re-derived.

## Closing protocol

1. Review log entry (append-only); tracker row (yours only): verdict —
   **APPROVED** expected if B5 verifies; CHANGES_REQUESTED otherwise. Note
   appended, actor stamps preserved.
2. Archgraph read-only; zero delta expected (state it; revision `9476e89a…`,
   15 pending).
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase2_rereview_r3_handoff.md`
   (full path): summary; `⚠ OWNER DECISIONS REQUIRED (n)` (one line if zero); B5
   verification evidence; full write perimeter incl. probe declaration. **Deposit
   before ending the session.**
