---
plan: phase 6 (legacy money migration & API bridge)
role: reviewer
round: 2 (re-review, delta-scoped — B1, B2, S1–S4 + named notes)
date: 2026-08-14
---

# Session prompt — re-review phase 6 after fix cycle r1

You are the **re-reviewing agent** for phase 6, round 2. Delta-scoped; review
r1's "Verified correct" list is settled ground.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (settled)

- r1: behavior verified correct across the bridge, refusals, restoration,
  removal and cold build; CHANGES_REQUESTED on B1 (tautological pc2 guard —
  your predecessor's corrections R9/R10 are hash-recorded in the r1 Review
  log entry), B2 (the eligibility predicate re-valued deliberately-deleted
  prices — owner card 1 answered, folded as **R15-1**: eligibility =
  `NOT EXISTS (any item_valuations row)`, never-valued items only), S1–S4,
  11 notes.
- Fix r1 (Codex, checkpoint `51d8b7c`, deposit `73779ec` handoff-only):
  migration +23 (guard + predicate), drop migration +7 (N8 docstring/logger
  — the fix prompt's perimeter LINE said one file while its items included
  N8 on the drop file; the implementer resolved the coordinator's
  inconsistency sensibly — recorded, not a finding), 4 test files, 2 docs.
- Coordinator consumption (settled): collection exact (2012+23 = 2035
  selected, +15); the final migration hash matches the declared baseline
  (`a3228a85…`); all three ledger probes declared against FINAL hashes (the
  r1 defect class closed).

## Step 2 — delta probes (the r1 defects must now bite)

- **R2-P1 (B1):** re-run the `rows[1:]` skip mutation on a seeded disposable
  — `alembic upgrade` must ABORT with the unmigrated-count message and roll
  back (it exited 0 in r1); the shipped tests stay green at baseline (the
  correction is not over-tight).
- **R2-P2 (B2, the four valuation states):** on seeded disposables with the
  UNMUTATED shipped migration: never-valued → migrated; current-valued →
  journaled only (collision, valuation untouched — by IDENTITY per N5, not
  count); **soft-deleted-only → SKIPPED** (was re-valued in r1);
  superseded-only → SKIPPED (the recorded unreachability judgment present).
  Each row sole-predicate; the seeded eligible set proven non-empty.
- **R2-P3 (S1):** the R3 probe (inline key re-exposure at
  `upholstery_orders_query.py`) reddens EXACTLY the `upholstery-orders` row,
  eight others green (it left all 27 green in r1); spot-check two more rows'
  expressions actually differ and consume their endpoint id; fixtures are ORM
  `Item` rows.
- **R2-P4 (S2):** the R2 mutant (empty refusal id lists) reddens all three
  refusal rows; each row asserts its own class's report contents.
- **R2-P5 (S3/S4):** the three added TestClient rows (PUT/PATCH/
  find-or-create) return 422 with the exact message + envelope; the migration
  case tables are parametrized with authority-naming ids (no for-loop
  masking).
- **Notes:** N2 (plan text + structural row assert TWO enum users at head,
  incl. the journal snapshot); N4 (idempotency single-cause; post-conditions
  re-run on pass 2); N6 (intermediate assertion between the downgrades); N7
  (the tie test labeled synthetic, own node); N8 (docstring parent correct;
  logger not print).
- **Suite:** 2012/23/1 re-run yourself (failure set byte-identical to the
  phase-1 baseline); ruff; configured DB at head `be9dfe42a035`, journal 0
  rows; zero disposables remain (catalog query).

## Step 3 — graph (read-only)

Zero delta expected: 7 pending (journal node + the 6 phase-5 items) — NOT
yours. Confirm the r1 anchor-spans service still holds after this fix (the
data migration file changed: the journal node's evidence spans `45-75` /
`200-243` may have shifted by the +23 — deliver corrected spans if so; all
other spans anchor in untouched files).

## Closing protocol

1. Review log entry; tracker verdict (**APPROVED** expected if the delta
   verifies); stamps preserved.
2. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase6_rereview_r2_handoff.md`
   (full path, AFTER your writes): probe results with copy-pasted sha256
   pairs; corrected journal-node spans if moved; `⚠ OWNER DECISIONS REQUIRED
   (n)`; disposables listed and dropped; full write perimeter.
