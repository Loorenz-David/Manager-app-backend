---
plan: phase 3 (canonical calculator)
role: reviewer
round: 1
date: 2026-08-12
---

# Session prompt — review phase 3 (first review, full checklist)

You are the **reviewing agent** for phase 3 of the item-cost-calculation pipeline.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — FIRST review: full
   checklist, adversarial re-derivation, mutation-tested tests.

## Gate check

- Tracker: phase 3 **IMPLEMENTED** (Codex, checkpoint
  `2a860b271d3e4349894315c4d4243debaeb9a4cf` — final, cited in full).
- Handoff: `handoffs/implementer/2026-08-12_phase3_implement_r1_handoff.md`.

## Read order (after doctrine)

1. `plans/phase_3_canonical_calculator.md` — criteria as amended 2026-08-12
   (C1 12-row + duplicate-term row; C2 seeded 5×2 table + five per-site mutations;
   C5 seeded triple; C6 total type matrix; C7 tripwire; C8 raises; C9) + the
   implementer's Review log entry.
2. Intention §6A entire **as amended round 8** (localcontext requirement; corrected
   variance bound), §4A, R4-2.
3. `master_plan.md` §§6.3–6.5 (incl. the folded D1 public API and the ORM
   annotation caveat), 9 (P-B, P-F, P-G…P-M).
4. The implementer handoff — judgment calls are your probe list.
5. The diff: `git show 2a860b2`.

## Coordinator probes (verify, don't trust)

- **P3-1 (mutations, sampled independently):** re-run at least M-Q2 (the
  Diophantine tie), M-Q4 (quantize deletion), C7's FK-read mutation, and C9(b)
  (localcontext removal under lowered precision) — disposable worktree, revert,
  sha256-verify against the declared hashes
  (calculator `088e6514…845e90`, tests `9096962c…733fd1`).
- **P3-2 (seeded fixtures verbatim):** every C2 cell and C5's variance triple use
  the plan's seeded values with the plan's exact expected outputs; re-compute at
  least three by hand. If any test adjusted a seeded value, that is a finding.
- **P3-3 (C6 totality):** every cell of the type matrix has an asserting row
  (bool explicitly rejected for all three int-spec classes; enum value-string →
  `TypeError`; None user-supplied → named identity; None system-supplied →
  `TypeError`). Count rows against cells.
- **P3-4 (purity + localcontext coverage):** no I/O imports anywhere in
  `calculator.py` (P-F / `08_domain`); C9 probes only Q1/Q3 — verify by reading
  that EVERY public function's arithmetic runs inside the `localcontext()`
  (a function outside the wrapper passes C9 while violating §6A.2-as-amended).
- **P3-5 (rederive):** reads only the §6A.11 closed set (tripwire covers the three
  FKs + two episode snapshots); re-derives and compares each term `amount_minor`
  (D5 adopted); `REDERIVE_SKIPPED` is the single named constant returned on
  version mismatch, never a second path returning bare None.
- **P3-6 (declared test change):** the handoff says the C9 precision fixture "was
  strengthened as an intended test change" — verify the change strengthened (made
  the mutation bite harder), not weakened, the criterion.
- **P3-7 (graph delta, §8 standing flow):** one pending item —
  `node:domain-item-economics` (calculator evidence spans 1–26, 137–212, 371–425).
  Read the calculator at those spans BEFORE the stored claim (anti-pattern rule);
  report claim/anchor verdicts and a recommended decision. Do NOT adjudicate.
- **P3-8 (API report):** the module's actual public surface equals the 16 names
  folded into master plan §6.5 — nothing extra exported, nothing missing.

## Scope-fence verification

Pure module only: no service/command/router/schema/persistence; no phase-2 model
edits (the `Mapped[float]` annotations stay wrong until phase 9); no
`EconomicsStatusEnum` logic; no request-layer parse (moved to phase 4).

## Constraints

- Full suite per master plan §10; baseline 1684→1738 passed / 23 failed /
  1 deselected (the +54 must be exactly the calculator suite; failure set
  byte-identical; N14's Shopify flake may need one clean re-run).
- Findings → Review log (append-only), severity + verbatim correction clauses;
  tracker row yours only, actor stamps preserved. Findings, not patches.
- Mutation probes in disposable worktrees only; revert, sha256, declare.

## Closing protocol

1. Review log entry; tracker verdict (APPROVED / CHANGES_REQUESTED).
2. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase3_review_r1_handoff.md`
   (full path): summary; `⚠ OWNER DECISIONS REQUIRED (n)`; probe results
   P3-1…P3-8 (P3-7 as claim/anchor/recommendation); findings; lessons; full write
   perimeter incl. probe declaration. **Deposit before ending the session.**
