---
plan: phase 7 (evaluations — commit/supersede, projections, auto-commit)
role: implementer
round: 1
date: 2026-08-14
---

# Session prompt — implement phase 7 (the heart of the domain)

You are the **implementing agent** for phase 7: the commit transaction, the
mirror rule, projections/promotion, the auto path inside `create_task`, and
the evaluations read. The projection did your first hour on paper; its 23 rows
are routed and the plan's amendment block is GOVERNING.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## The plan — read BOTH layers as one document

`docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_7_evaluations.md`:
the base plan + forward notes + the **"Amendments (projection r0)" block —
GOVERNING wherever the two conflict** (A1 file list, A2 task amendments,
A3 restated criteria C1–C10, A4 new criteria C11–C14, A5 routing).

Also read AS AMENDED (intention round 16): **§7B.1 (step 4's `FOR UPDATE` on
the valuation; step 9's TASK-linked history record)**, **§7B.4's corrected
race clause (both orderings)**, **§7B.5 as restated (resolver-total
pre-check, verbatim log lines, `pending_events` discipline)**, §7B.2/§7B.3,
§7A entire, §7C, §7.3, §6A.9, §6A.11, §4A, §11A.4. Master plan: §6.4 (the
**status→identity mapping table** — THE translation, never re-derived;
`ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY` now registered; the `_common.py`
evaluations-index row with the uniform conflict sentence standing), §6.5
(**Phase-7 additions**: the `_commit_item_cost_evaluation_in_session` helper,
the `_common.py` extractions with P-Z property tests, the rate-snapshot
RECOMPUTE decision, serializers/requests/`label`/`source`, the four
evaluations-read pins, the rederive-marker ERROR escalation), §9 P-A…P-AA +
ALL extensions, §10.

Precedents (all re-verified at projection time): savepoint
`reconcile_worker_shift_state.py:278`; subordinate transaction
`create_task.py:76` (`maybe_begin`); dispatch-outside-transaction
`resolve_task.py:102-104`; history record `resolve_task.py:61`
(TASK-linked — your form); in-session helpers `_create_item_in_session` /
`_create_history_record_in_session` (same file); direct-INSERT race precedent
`test_phase4_fix_coverage.py:521`; bounded-wait harness = phase-4's C3/C6.

## Environment facts (verified at projection time, 2026-08-14)

- git HEAD `133590c`; alembic head `be9dfe42a035`; suite baseline
  **2012/23/1 deselected = 2035 selected**; dev DB at head; all seven
  economics tables at 0 rows (journal present, 0 rows).
- Payload-key greps for every key this phase introduces: **zero hits** — no
  shipped assertion collides.
- `_ROUTES` in `test_item_economics_router.py` is a hand-maintained 16-row
  list; your five routes join it (C13).
- The four `create_task` integration files run in unconfigured workspaces —
  every auto-path pre-check false, **no change expected there**; you OWE the
  run that confirms it (the auto path touches every task creation in the
  suite).
- **No migration in this phase.** The history record is TASK-linked (R16-1);
  `history_record_entity_type_enum` is untouched.

## Discipline highlights

- **One transaction, §7B.1's order exactly.** Task `FOR UPDATE` (step 1);
  valuation `FOR UPDATE` (step 4 — R16-2, the mirror-race lock); config
  `FOR SHARE` (step 3); calculator before any write; S1→S2→S3; never insert
  before S1; never `ON CONFLICT` on chain indexes.
- **Commit, promotion, and the auto path are ONE procedure** — the registered
  `_commit_item_cost_evaluation_in_session` helper. Promotion re-runs §7B.2
  admission, takes the task lock, and verifies projection ownership +
  liveness (A2/C8). The auto path appends the event to `pending_events` only
  after the savepoint exits normally and NEVER dispatches (R16-4).
- **Refusals translate via §6.4's mapping table** — the resolver gate runs
  before the calculator; consume `resolve_economics_selection` /
  `resolve_item_economics_status`, never re-derive selection.
- **Snapshots from calculator outputs only** (P-F); the rate snapshot is
  RECOMPUTED, never copied from the basis row (D13; C1 row 1b has the fixture
  where the two disagree).
- **Both auto-path log lines verbatim** (§7B.5):
  `"item_economics.auto_commit_skipped | task_id=%s item_id=%s status=%s"`
  INFO; `"item_economics.auto_commit_failed | task_id=%s item_id=%s error=%s"`
  WARNING. C9 asserts the second.
- **N named mutations = N ledger rows** (P-I sixth ext); full observed red
  sets with observed pytest node ids; divergence from prediction FLAGGED
  (C12's `read=True` deletion must redden row 1 ONLY — claiming both is the
  fifth-extension defect); per-row sha256 pairs COPY-PASTED, never retyped;
  distinct hash per reused label; suite numbers READ off the run, never
  derived.
- **P-S rows are discharged as recorded** — `ITEM_COST_CONCURRENT_COMMIT` via
  direct INSERT from a second session (C2); the ambiguous-group rows via the
  pure resolver (C6/C9); no command-level fixture can reach either, and a
  criterion that "passes" by removing a lock is a defect, not a pass.
- **Bounded waits on every concurrency row** (P-T r2-L3 — an unbounded wait
  hung a prior suite for 120 s); run any committing subset twice, residue
  scope named (rule 11½).
- **P-Z on the D19 extraction**: phase-5 focused valuation tests green before
  AND after the `set_item_valuation.py` refactor, plus the before/after
  property row (identical chain rows for one set+supersede+delete sequence).
- Parametrize ids name the authority row in its CURRENT numbering (P-V);
  each row's expression must differ, not just its id.

## Scope fence

Production: `services/commands/item_economics/commit_item_cost_evaluation.py`,
`create_item_cost_projection.py`, `delete_item_cost_projection.py`,
`promote_item_cost_projection.py`, `requests/__init__.py`, `_common.py`
(index row + the two D19 extractions), `set_item_valuation.py`
(**refactor-only** — call sites re-pointed, zero behavior change),
`services/commands/tasks/create_task.py` (savepoint block + conditional
`pending_events` append; NO existing statement moves),
`services/queries/item_economics/list_task_evaluations.py` (new),
`domain/item_economics/serializers.py` (evaluation + term),
`routers/api_v1/item_economics.py` (five routes) + `routers/README.md`
mirrors. Tests: new phase-7 files + `test_item_economics_router.py`
(`_ROUTES` + C13 arbiter) + the P-Z rows. Docs: master plan tracker + plan
Review log + your handoff. **No migration. No phase-5/8 behavior changes.**
If anything else seems needed, stop and report.

## Archgraph

Orient read-only first (revision `53261a23…`, **155 nodes / 200 edges**,
2 pending — NOT yours to adjudicate). Delta at end: ONE batched additive
`apply_changes` — the four command nodes, the query node, five endpoint
nodes, edges to `table-task`/`table-item-cost-evaluation`/valuation tables,
the `evaluation-committed` event node; accurate spans; write-site evidence
in the command modules, never a blanket router anchor (phase-4's P4-6
lesson).

## Closing protocol

1. All criterion rows green (C1–C14 as amended); the full mutation ledger.
2. Suite: expect 2012+N / 23 byte-identical to the phase-1 list / 1
   deselected (numbers READ off the run); the four `create_task` integration
   files confirmed unchanged-green; any committing subset twice with residue
   scope named; ruff on changed files; configured DB at head `be9dfe42a035`
   (this phase adds no migration — say so explicitly).
3. Tracker → `IMPLEMENTED`; Review log per P-L (items, never bare counts).
4. Checkpoint `CHECKPOINT (not approved): item-cost phase 7 implement r1 —
   <summary>`; handoff AFTER, citing the FINAL hash, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-14_phase7_implement_r1_handoff.md`
   (full path). `⚠ OWNER DECISIONS REQUIRED (n)` if any arise; full write
   perimeter + probe declaration; state every delegation choice you
   exercised.
