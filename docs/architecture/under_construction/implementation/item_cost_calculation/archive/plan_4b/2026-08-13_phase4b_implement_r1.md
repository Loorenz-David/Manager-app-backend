---
plan: phase 4B (category-driven group selection, §7C)
role: implementer
round: 1
date: 2026-08-13
---

# Session prompt — implement phase 4B (category-driven group selection)

You are the **implementing agent** for phase 4B. The gate is open: phase 4 is
**APPROVED** (closeout `8ca2bf9`).
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## The plan — read ALL THREE layers as one document

`docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_4b_category_selection.md`:

1. the base plan (tasks 1–9, criteria C1–C8);
2. **"Round-0 projection amendments" — GOVERNING where they conflict** (L-5
   present-means-not-None; L-4's struck seeded-row clause; L-6 explicit
   client_ids on unsaved fixtures; V2b; L-13's filtered compare_metadata;
   L-15's dependent-count pre-flight report; L-12's doc target);
3. **"Prompt-time dependency re-verification" — GOVERNING for task 8**: the
   named test-change list is the amendments' six items PLUS T8-7…T8-10
   (the fix cycles added `test_phase4_fix_coverage.py` and a router payload
   row; every second same-workspace active group takes SEAT).

Also read: master plan §§5, 6 (registry as amended for 4B), 9 (P-A…P-W all
bind — esp. P-V ids name the authority row; P-I every enumerated row's
mutation is EXECUTED with the observed pytest node id, never reasoned about),
10; intention §7C entire + §11A.4 + §7A.5; R12-1 + pins in
`planning/owner_decisions.md`; phase 4's plan for the shipped code and
harness precedent (its archived handoffs live in `archive/plan_4/`).

## Environment facts (verified at prompt time, 2026-08-13)

- Dev DB `production_cost_groups` is at **0 rows** (closeout purge), so the
  task-1 pre-flight passes on the configured DB. Migration head `90cdd23a828e`
  — re-verify with `alembic heads` before writing the revision.
- `PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`; postgres
  `127.0.0.1:5433`, redis `127.0.0.1:6380`. Baseline: **23 known failures,
  byte-identical to the phase-1 list** (N14 flake caveat recorded). Current
  full-suite collection: 1915 / passing 1892.
- Disposable-DB recipe for C1's manual rows and DDL-site mutations: master
  plan §10 (DATABASE_URL override; drop afterwards; configured DB stays at
  head — charter rule 7).

## Discipline highlights (the bars phase 4 was held to)

- **Tests are the deliverable, not an afterthought:** every criterion row
  ships in this cycle with its named mutation run, observed node id recorded,
  and the mutant reverted (sha256 pair per row). Phase 4 lost two rounds to
  count-matching (P-V) and vacuous filter rows (P-W) — C2/C5/C6's rows name
  the authority row in their parametrize ids and their fixtures compete for
  the asserted slice.
- **Run all enumerated mutations** — including ones you expect an existing
  arbiter to cover (P-I fourth extension; the fix-r3 ledger under-declared
  exactly this way).
- Every synchronization or wait is bounded (P-T ext). No concurrency harness
  is needed in this phase (C3(d) is collapsed per the amended L-4 judgment).
- Rule 11½ with SCOPE: state which tables your residue check scanned.
- Mutation-probe hygiene: probes in the main worktree are acceptable (the
  managed-.git precedent) — apply, run, revert, and record BOTH sha256s per
  probe against the REAL file paths (fix-r3's handoff garbled its probe
  paths; declare paths exactly as they exist).

## Scope fence

Write perimeter: the migration file; the eight production files listed in the
plan's "Files expected to change"; `models/tables/item_economics/README.md`
(L-12); new 4B test files under `tests/{unit,integration}/…/item_economics/`;
the task-8 named test edits (six + T8-7…T8-10) — nothing else. **The items
domain is untouched (owner pin 2).** No new routes, no role-gate changes, no
category filter on list queries. If a task seems to require a file outside
the perimeter, stop and report.

## Archgraph

Orient read-only first (`archgraph_status`, get_node on
`table-production-cost-group`, the group create/update command nodes, the
status endpoint node — all human_confirmed as of revision `657b8f03…`).
Delta at end: ONE batched `apply_changes` with accurate evidence spans
(column/index on the table node, classifier + status-query semantic updates,
the two command reworks). Never adjudicate pending items (2 are pending —
the N7 cost-model-term edges; leave them). Discrepancies → the
`archgraph-discrepancies` skill, never silent workarounds.

## Closing protocol

1. All criterion rows green; the mutation ledger per-row with observed pytest
   node ids + sha256 pairs (P-I; real paths).
2. Full suite: expect 1892+N passed / 23 known failures byte-identical / 1
   deselected; run any committing subset twice (rule 11½, scope stated).
   Ruff clean on changed files. Dev DB left at head.
3. Tracker row → `IMPLEMENTED`; plan Review log entry (P-L: items, never
   bare counts).
4. Checkpoint `CHECKPOINT (not approved): item-cost phase 4B implement r1 —
   <summary>`; deposit the handoff AFTER the checkpoint, citing the FINAL
   hash, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-13_phase4b_implement_r1_handoff.md`
   (full path). `⚠ OWNER DECISIONS REQUIRED (n)` heading; full write
   perimeter + probe declaration.
