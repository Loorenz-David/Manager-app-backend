---
plan: phase 3 (canonical calculator)
role: reviewer
round: 2 (re-review, delta-scoped)
date: 2026-08-12
---

# Session prompt — re-review phase 3 after fix cycle r2

You are the **re-reviewing agent** for phase 3. Delta-scoped per the charter —
settled ground is not re-derived; anything seen wrong in passing is reported.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` (re-review protocol).
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (settled — do not re-derive)

- **r1 (Claude, CHANGES_REQUESTED):** arithmetic verified at every seeded cell
  (six recomputed by hand), all nine original mutations re-run and biting,
  perimeter exact, purity clean, rederive closed-set held, P3-6 counterfactual
  positive. Settled ground is the r1 Review log entry.
- **Owner cards (answered, folded as intention round 9):** R9-1 mismatch =
  `REDERIVE_MISMATCH` marker (never ValidationError); R9-2 both defensive guards
  absorbed with required rows; card 3 graph node HELD (post-approval single
  adjudication — not your scope beyond noting it unchanged).
- **Fix r2 (Codex, checkpoint `8378a1b672831e56c89bffe6843d1e815fd9383e`, final):**
  B1 localcontext wraps + C9 extended to all Decimal-arithmetic functions; B2 the
  system-`None` money row + inferred-zero mutation; S1 per-value assertions;
  S2 carrier → `REDERIVE_MISMATCH` structured payload; S3 both docstring tokens;
  three absorbed-guard rows; `__all__` (16 + 2 Protocols + 2 markers). Optional
  N1/N5/N6 not taken (compliant — they were optional).
  Handoff: `handoffs/implementer/2026-08-12_phase3_fix_r2_handoff.md`.

## Step 1 — verified perimeter

`git show 8378a1b` must contain only: `calculator.py`, `test_calculator.py`, the
plan's Review log, the master-plan tracker row. Anything else is a finding.
Declared final hashes: calculator `1c9a75fa…eb5d20`, tests `971232312a…cc885b`.

## Step 2 — delta probes

- **R2-P1 (B1 closed for real — the P-N check):** read every public function once
  more and confirm NONE performs Decimal arithmetic outside `localcontext()` now;
  re-run the B1 mutation (remove `calculate_remaining_worker_minutes`'s wrapper)
  and confirm its C9 row reddens under lowered ambient precision.
- **R2-P2 (B2):** re-run the inferred-zero mutation (`_require_money` system
  branch → `return 0`) — the new row must redden; also verify the row drives a
  genuinely system-supplied parameter (P-M extension: the row names its
  parameter).
- **R2-P3 (S2 carrier):** grep production paths — zero `ITEM_COST_SNAPSHOT_MISMATCH`
  and zero `ValidationError` raises on mismatch; `rederive`'s mismatch return is
  the structured `REDERIVE_MISMATCH` payload (marker + field/rederived/stored
  entries) per intention §6A.11 round 9; the C7 fixture asserts marker AND exact
  payload.
- **R2-P4 (S1):** the currency rows assert each value individually (no `or`) —
  re-run the message-weakening mutation; per P-O, 2 of 3 rows (or better) must
  redden.
- **R2-P5 (absorbed guards + S3 + `__all__`):** the three R9-2 rows exist with
  exact identities and bite (drop each guard branch briefly on a disposable
  worktree); S3 asserts a bump token AND a never-bump token against the module
  docstring; `__all__` equals exactly the §6.5 registered surface (20 names).
- **Suite:** full run — expect 1743 passed / 23 failed / 1 deselected, failure set
  byte-identical to baseline (N14 flake caveat).

## Closing protocol

1. Review log entry (append-only); tracker verdict (**APPROVED** expected if the
   delta verifies) — actor stamps preserved.
2. Archgraph read-only: confirm still 1 pending item (the held node), revision
   `671fd92a…`, zero delta from the fix; state it.
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase3_rereview_r2_handoff.md`
   (full path): summary; `⚠ OWNER DECISIONS REQUIRED (n)`; probe results; findings
   if any (verbatim clauses); full write perimeter + mutation-probe declaration.
   **Deposit before ending the session.**
