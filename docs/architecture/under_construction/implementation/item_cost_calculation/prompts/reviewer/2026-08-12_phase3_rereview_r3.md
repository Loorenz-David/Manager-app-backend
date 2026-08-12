---
plan: phase 3 (canonical calculator)
role: reviewer
round: 3 (re-review, delta-scoped — B3/S4/S5 only)
date: 2026-08-12
---

# Session prompt — re-review phase 3 after fix cycle r3

You are the **re-reviewing agent** for phase 3, round 3. Delta-scoped; settled
ground is not re-derived; anything seen wrong in passing is reported.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` (re-review protocol).
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (settled — do not re-derive)

- **r1 + r2:** everything except B3/S4/S5 is settled (see the r1 and r2 Review-log
  entries' verified-ground sections; r2 closed all six r1 findings and swept every
  public callable under hostile context).
- **Owner decisions:** R10-1 — `rederive` is TOTAL over all malformed inputs
  (intention §6A.11 round-10 paragraph: three enumerated input classes, no
  `ValidationError` escapes on any path, rate→allowance cascade pinned). Card 3:
  the graph node stays held (1 pending item — verify unchanged, do not touch).
- **Fix r3 (Codex, checkpoint `8908619`, final = HEAD, unamended):** B3 all three
  conversion seams; S4 verified fixture swap; S5 four branch rows + cascade row;
  per-row mutations declared. Handoff:
  `handoffs/implementer/2026-08-12_phase3_fix_r3_handoff.md`.
  **Gate-check adjustment:** the handoff was committed INSIDE the checkpoint (it
  is one of the five files in `8908619`) rather than deposited after it, so it
  cites no checkpoint hash — a process slip, already recorded by the coordinator;
  do not file it again. The hash is verified from git directly.

## Step 1 — verified perimeter

`git show 8908619` = exactly five files: `calculator.py`, `test_calculator.py`,
the handoff, the plan's Review log, the master-plan tracker row. Declared final
hashes: calculator `e5f42531…611a49`, tests `d7251cde…97ba30`.

## Step 2 — delta probes (the whole scope)

- **R3-P1 (B3 totality — the R10-1 check):** exercise all three malformed-input
  classes live on unsaved ORM instances (zeroed stored rate; NULL typed term
  value; NULL purchase cost on a purchase term) — each must return the
  `REDERIVE_MISMATCH` payload, never raise. Then go hunting for a FOURTH escape
  route the enumeration might have missed (e.g. a non-Decimal snapshot value, a
  negative stored rate, an unknown `calculation_type` member) — R10-1 says TOTAL;
  adversarially test the totality, not just the three named classes.
- **R3-P2 (per-row mutations, sampled):** re-run at least B3 class (a)'s re-raise
  mutation and S5's cascade-inversion mutation; confirm each reddens exactly its
  named row. sha256-verify reverts against the declared hashes.
- **R3-P3 (S4):** the swapped fixture is in BOTH C9 tuples; removing
  `calculate_percent_consumed`'s wrapper reddens the row (the r2 counterfactual
  is now the shipped fixture).
- **R3-P4 (S5 payloads):** each of the four field-branch rows asserts its exact
  payload (field, rederived_value, stored_value); the cascade row asserts the
  exact two-entry field list.
- **Suite:** expect 1749 passed / 23 failed / 1 deselected, failure set
  byte-identical (N14 caveat). Focused: 65.

## Closing protocol

1. Review log entry (append-only); tracker verdict — **APPROVED** expected if the
   delta verifies; actor stamps preserved.
2. Archgraph read-only: still 1 pending (the held node), revision `671fd92a…`,
   zero delta; state it.
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase3_rereview_r3_handoff.md`
   (full path, deposited AFTER your Review-log/tracker writes, citing nothing that
   would need amending): summary; `⚠ OWNER DECISIONS REQUIRED (n)`; probe results;
   findings if any; full write perimeter + probe declaration. **Deposit before
   ending the session.**
