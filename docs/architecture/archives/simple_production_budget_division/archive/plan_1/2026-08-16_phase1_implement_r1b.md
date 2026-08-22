---
plan: 1
role: implementer
round: 1b (fix round before first review)
date: 2026-08-16
pipeline: simple_production_budget_division
---

# Implement round 1b — plan 1 fix round (coordinator consumption findings K1–K6)

Round 1 shipped sound-looking production code but is not reviewable yet: one
phase-caused red test was mislabeled as environmental, the observed-red mutation
ledger covers 1 of ~20 named mutations, one criterion's test is missing entirely,
and the handoff gives review no criterion→test map. You fix exactly these things.
**No production-behavior changes are expected in this round** — if fixing a test or
probing a mutation reveals a genuine production defect, STOP, record it, and report
rather than redesigning silently.

## Read first

1. `plans/plan_1.md` — the Review log's **Round 1 consumption (K1–K6)** entry and
   criteria C1–C21 (with C9b–C9e, C13b).
2. `planning/intention.md` — HC-1a as extended round 6 (FOUR authorized v1
   artifacts); §3/§4 unchanged otherwise.
3. Your r1 handoff and checkpoint `0b85701` (your baseline).

## Fix items (exactly these)

- **F1 (K1)** — Make the second route mirror green BY ADDITION:
  `app/tests/unit/routers/api_v1/test_item_economics_router.py` — add the E2 row(s)
  to `_ROUTES` (`:14`) / `_ALL_ROLE_ROUTES` (`:48`) so the parametrized role tests
  and `test_router_route_pairs_match_the_authoritative_route_table` cover
  `GET /tasks/budget-allocations` like every sibling route. This file is now the
  fourth HC-1a artifact; additions only, nothing else in it changes. Note: adding
  to those tables enrolls E2 in that file's parametrized role/shape tests — make
  sure the row's body/roles entries are correct for an all-four-roles GET.
- **F2 (K3)** — Complete the observed-red mutation ledger: for EVERY named
  mutation in C1–C21 (including C9b–C9e's SQL-site mutations and C5's two rows),
  apply the mutation at its named site, run the named test, record the exact red
  output line, revert byte-for-byte. The handoff carries one record per mutation:
  mutation text (byte-reproducible), test node id, observed red line, revert
  confirmation. A mutation that does NOT go red is a STOP item (the test is
  decoration — report it, do not "fix" it silently).
- **F3 (K4)** — Add C13b: the service-invoking test pinning
  `remove_task_step` ⇒ `state=SKIPPED AND is_deleted=True` on the removed row
  (fixture precedent: `test_phase8_status_results.py:51-84` style setup/teardown).
- **F4 (K6)** — Handoff carries a criterion→test table: every criterion C1–C21
  (each lettered row separately) → exact pytest node id(s), or "NOT COVERED —
  STOP item" if you find a gap. Review will audit against this table.
- **F5 (K2/C18)** — Full suite re-run, foreground, from `backend/app/`:
  `PYTHONPATH=. pytest -q -m 'not e2e'`. Expected failure set = the 23 v1 baseline
  IDs byte-identical (`item_cost_calculation/plans/phase_1_worker_money_redaction.md:198-220`)
  + exactly the 3 foreign `test_seed_item_economics_configuration.py` IDs (owner's
  in-flight bootstrap work, NOT yours, do not touch it) + ZERO others. Record
  totals and the full failure-id list in the handoff.

## Perimeter

Allowed writes: `test_item_economics_router.py` (F1, additions only),
`test_budget_allocations_query.py` (F3), your four phase test files if F2/F4
reveal gaps needing new test rows, the handoff, and the tracker/review-log rows
that are yours. NOTHING else — no production module changes without a STOP item
justifying them, no other v1 files, and do NOT re-commit
`.archgraph/architecture.yml` (K5: your r1 checkpoint already carried foreign
graph state; this round makes no graph changes — no `apply_changes`, the r1 delta
stands).

## Checkpoint + handoff

Checkpoint commit when green-per-F5:
`CHECKPOINT (not approved): plan1 implement r1b — mirror fix + mutation ledger`.
Handoff:
`handoffs/implementer/2026-08-16_phase1_implement_r1b_handoff.md` — frontmatter
(`round: 1b, state: IMPLEMENTED`), checkpoint hash, full write perimeter, F5
totals + failure list, the complete F2 ledger, the F4 table, STOP items.
