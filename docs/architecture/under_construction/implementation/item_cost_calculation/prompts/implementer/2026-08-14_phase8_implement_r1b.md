---
plan: phase 8 (status & results)
role: implementer (continuation)
round: 1b (implement r1 was consumed INCOMPLETE — this is not a review fix cycle)
date: 2026-08-14
---

# Session prompt — phase 8 implement r1b (complete the round)

You are the **implementing agent** continuing phase 8. Round r1 (checkpoint
`ae12f23`) delivered the production surface but was consumed INCOMPLETE: one
confirmed production defect, a wrong environment diagnosis, and the closing
protocol unmet. The coordinator has already root-caused the defect — do not
re-diagnose; fix, prove, and close.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## What r1 got wrong (read A18 in the plan — GOVERNING)

1. **The enum migration is missing.** `TaskType.PROCESS_ITEM_COST_RESULT`
   exists in Python only; PostgreSQL's `task_type_enum` was never extended,
   so EVERY emit dies at INSERT with `invalid input value for enum
   task_type_enum: "process_item_cost_result"`. The coordinator reproduced
   the full suite at **2065 / 47 / 1**: all 24 non-established failures are
   task-boundary paths killed by your own emits (force-ready ×6,
   ended-shift ×5, finalize-pending ×4, worker-shift ×1, +8 more).
2. **The "dirty database" diagnosis was false.** Measured: `roles` = 4 rows
   / 4 distinct names; zero duplicate working sections. Every failure r1
   called environmental is an established phase-1 baseline member (#14–23 —
   the audit-log `ws_test` FK rows included). Never diagnose from pattern;
   read one traceback.
3. **The closing protocol was unmet**: 5 unit tests against ~60 amended
   criterion rows; no integration criteria; a BLANKET mutation deferral
   (§9's deferral rule requires per-row deferral in the ledger); no final
   hashes; the R2-N2 hardening skipped.

## The work (ordered)

1. **The migration (A18):** one alembic revision on head `be9dfe42a035` —
   `ALTER TYPE task_type_enum ADD VALUE 'process_item_cost_result'` — slug
   `add_process_item_cost_result_task_type`, following
   `migrations/versions/f2c3d4e5f6a7_add_shopify_process_products_task_type.py`
   (the in-tree precedent; PG 18.4). Upgrade the configured dev DB and
   assert the member by STATE QUERY (`pg_enum`), never exit code (L5).
   Downgrade note per the precedent's shape. §10's head entry moves to your
   new revision at checkpoint — update it.
2. **Re-establish the baseline:** full non-E2E foreground run — expect
   **2076+N / 23 byte-identical to the phase-1 list / 1 deselected**,
   numbers READ off the run. If ANY failure outside the phase-1 list
   remains, stop and report with the traceback; do not diagnose in prose.
3. **Build the criteria** — C1–C11 as amended (A1–A17), every enumerated
   row with a parametrize id naming its authority row (P-V). The r1 unit
   files stay; the bulk is integration: C2/C3/C4 (buckets, dilution,
   consumption rows), C5 (idempotency/replay incl. the computed_at-advance
   observation and the ON CONFLICT update path), C6/C6b (straggler + total
   admission incl. ASSIGNED/STALLED), C7 (twelve members, per-row producer,
   the selection-OK-never-leaks hazard row), C8, C9 (declared worker key
   set + enumerated families disjointness), C10 (all four emission points —
   ZERO-notification-target fixtures on the terminal rows; EXACT event
   counts, two for a ready-making transition), C11 (lifetime read's five
   pins incl. the snapshot-vs-live mutation), the A15 same-warning equality
   rows, the A10 loader-equality row + non-vacuity, the A6 split route
   tables with both P-G mutations.
4. **R2-N2 hardening** in `test_phase7_evaluations.py` (`assert checked ==
   1` after the loop) — it is IN the fence (A14).
5. **The mutation ledger, per row** (P-I; phrased for byte-reproducibility,
   9th ext): C1's three filter deletions; A15's re-resolution removal; the
   emission deletions at their DEFINITION sites (one per touch point — the
   reopen one must redden through the `add_task_steps` path); the guard
   narrowing on the straggler re-emit (READY half); C7's hazard-row
   producer swap; C9's serializer mutation; C11's live-field swap; A6's two
   P-G mutations; A13's computed_at freeze. N named = N rows, per-row
   sha256 pairs COPY-PASTED, observed pytest ids, reversion proven. If you
   defer ANY row, the ledger says so per row with the reason.
6. Any committing subset twice, residue scope named (rule 11½); bounded
   waits (P-T); ruff on the perimeter.

## Scope fence

The r1 fence (plan A-block + r1's shipped files) PLUS: the new migration
file, `app/migrations/` only for that one revision; the phase-8 test files
you now build; `test_phase7_evaluations.py` (R2-N2 only). Production code
beyond the migration changes ONLY if a criterion you build proves a defect —
each such edit named in the handoff with its red-then-green evidence. NO
router/production drive-by edits. If anything else seems needed, stop and
report.

## Archgraph

READ-ONLY this round — your r1 delta (21 pending, rev `c74eb913…`) is held
for post-approval; the three discrepancy filings stand. The MIGRATION is new
architecture: add it to the graph delta as ONE small additive batch (the
migration source-link on the execution/task-type surface) or record it in
the handoff for the coordinator — state which you did.

## Closing protocol

1. All criterion rows green; the full per-row mutation ledger.
2. Suite numbers READ off YOUR foreground run; failure set byte-compared to
   the phase-1 list (say "byte-identical" only after the diff); DB at YOUR
   new head (state the revision + the pg_enum state query result);
   disposables dropped and listed.
3. Tracker stays `IMPLEMENTED` (r1b note appended); Review log entry per
   P-L; FINAL sha256 for EVERY production file the phase now touches
   (r1's + the migration) — copy-pasted, never retyped.
4. Checkpoint `CHECKPOINT (not approved): item-cost phase 8 implement r1b —
   <summary>`; handoff AFTER, citing the final hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-14_phase8_implement_r1b_handoff.md`
   (full path). `⚠ OWNER DECISIONS REQUIRED (n)` if any arise; full write
   perimeter + probe declaration; state every delegation exercised.
