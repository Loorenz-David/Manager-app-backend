---
plan: phase 3 (canonical calculator)
role: implementer
round: 1
date: 2026-08-12
---

# Session prompt — implement phase 3: the canonical calculator

You are the **implementing agent** for phase 3 of the item-cost-calculation pipeline.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path, in this order)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

**The plan file is your task list; where this prompt differs, the plan file wins.**

## Gate check (verify before working; on any failure, stop and report)

- Tracker: phase 2 **APPROVED**, phase 3 **PROMPT_READY** (projection r0 ran; its
  18-row ledger is fully routed — nothing pending).
- No phase-3 implementer handoff exists (you are round 1).

## Read order (after doctrine)

1. `master_plan.md` §§5, 6.3–6.5 (incl. the NEW `ITEM_COST_TERM_SHAPE_INVALID`
   identity and the **ORM annotation caveat** — eleven `Mapped[float]` annotations
   lie; §6A.1 governs boundary types), 9 (P-B, P-F, P-G…P-M), 10.
2. `plans/phase_3_canonical_calculator.md` — as amended 2026-08-12: C1 12-row
   table + duplicate-purchase-term row; C2 as a seeded 5×2 table with five
   per-call-site mutations (Q4's tie is PROVEN IMPOSSIBLE — do not attempt it, its
   guard is the quantize-deletion mutation); C5's seeded variance triple; C6 as a
   total type-matrix (bool excluded explicitly; the request-parse row moved to
   phase 4); C7's tripwire form; C8 raises; NEW C9 (ambient-context hostility +
   version constant); the delegation list D1–D5 in Notes.
3. Intention §6A entire **as amended round 8** (§6A.2 localcontext requirement;
   §6A.8 corrected variance bound), §4A (A1–A3, A8), R4-2.
4. Re-emit the master plan §5 contract resolution before coding (`08_domain` —
   pure, no I/O — is the load-bearing one).

## Hard scope fences

- **Pure module only**: no I/O, service, command, router, schema, or persistence;
  no `Decimal(str(v))` request parse (phase 4's); no edits to phase-2 models
  (the `Mapped[float]` annotation fix is phase 9's — do not "fix" it in passing);
  no `EconomicsStatusEnum` logic (phase 4's classifier).
- P-F: this module is the monopoly — but equally, it contains ONLY calculation.

## Non-optional constraints (from the routed projection ledger)

- Every seeded fixture in C2/C5 is **verified** — use the seeded values; if any
  disagrees with your implementation, that is a finding to report, not a fixture
  to adjust.
- All arithmetic inside `decimal.localcontext()` (§6A.2 round 8); every quantize
  passes `rounding=ROUND_HALF_EVEN` explicitly.
- The five C2 mutations are **per call site**; C6's guard mutation is at the shared
  definition site (D3). Run every named mutation (C2×5, C6, C7's FK-read, C9's two),
  revert, sha256-verify, declare per-mutation with reddened row ids (P-I).
- C7 fixtures assign `Decimal` explicitly to Numeric-backed fields (annotation
  caveat) and never set FK/episode-snapshot fields; the tripwire patches raising
  properties over all five excluded fields.
- Errors: `ValidationError(message)` with §6.4 leading-token identities; type
  violations raise `TypeError` per C6's matrix (bool explicitly excluded from int
  acceptance).
- Tests are pure unit tests — no DB, no session (except nothing: even C7 uses
  unsaved instances). Each test names which shared-factory field it varies (P-K/P-M).
- **Full suite before first change**: confirm the baseline (1684 passed / 23 known
  failures / 1 deselected; N14's Shopify test is order-flaky under load — re-run
  clean before concluding anything from it). NOTE: a maintenance session
  (migration-shim r2) may be running concurrently — it touches only
  `migrations/env.py` + one migration file's metadata line; if the baseline moves
  in `migrations`-related tests, coordinate through the coordinator rather than
  investigating yourself.

## Delegations (granted in writing — plan Notes)

D1 public function names (**report the resulting public API in your handoff** —
the coordinator folds it into §6.5; four later phases call these functions);
D2 `tests/unit/domain/item_economics/`; D3 shared entry guard; D4 named
skip-marker constant; D5 rederive re-derives term amounts (adopted in C7).

## Closing protocol

1. All criteria green (C1–C9); every named mutation run/reverted/declared.
2. Full suite green vs baseline.
3. Archgraph: orient on `domain-work-analytics`; at close ONE batched
   `archgraph_apply_changes` — the new item-economics `domain` node (calculator as
   evidence, accurate spans). Never adjudicate pending reviews.
4. Tracker row → `IMPLEMENTED` (Note appended; actor stamps preserved); Review log
   entry per P-L (state what was built per criterion).
5. Checkpoint: `CHECKPOINT (not approved): item-cost phase 3 — <summary>`.
   **The handoff cites the FINAL hash** (do not amend after citing).
6. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-12_phase3_implement_r1_handoff.md`
   (full path): summary; `⚠ OWNER DECISIONS REQUIRED (n)`; implementation vs plan
   with judgment calls named; **the public API report (D1)**; test counts
   before/after; mutation declarations; the graph delta recorded (node id); full
   write perimeter incl. the final checkpoint hash. **Deposit before ending.**
