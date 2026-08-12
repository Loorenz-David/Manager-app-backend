---
plan: phase 1 (worker money redaction)
role: implementer
round: 1
date: 2026-08-12
---

# Session prompt — implement phase 1: worker money redaction

You are the **implementing agent** for phase 1 of the item-cost-calculation pipeline.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path, in this order)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` — shared charter.
2. `/Users/davidloorenz/agent-skills/implementation-executor.md` — your session
   doctrine. Follow it end to end (gate check, read order, contract-faithful
   implementation, closing protocol).

**The plan file is your task list; where this prompt differs, the plan file wins.**

## Gate check (verify before working; on any failure, stop and report)

- `master_plan.md` §4 tracker shows phase 1 **PROMPT_READY** (projection round 0 ran;
  its ledger is fully routed into the artifacts you will read — nothing is pending).
- No phase-1 implementer handoff exists (you are round 1).
- Phase 1 has no predecessor to be APPROVED.

## Read order (after doctrine)

1. `master_plan.md` — §§3, 5 (including BOTH recorded contract gaps), 6.4–6.5, 9, 10.
2. `plans/phase_1_worker_money_redaction.md` — your task list and acceptance
   criteria, as amended 2026-08-12 (rows 15b, 17–25; tasks 2–3; Notes).
3. Intention §11A.1–§11A.3 **including the §11A.2 round-5 correction** (the
   eight-endpoint census) and §17/round-5 changelog context as needed.
4. Re-emit the master plan §5 contract resolution before coding (your doctrine's
   obligation) — noting the §5 divergence records: serialization stays at the query
   layer in the files you touch; error identities travel in `message`.

Line numbers in the artifacts date to 2026-08-11/12 — verify by symbol name.

## Hard scope fences (violations are automatic review findings)

- Nothing item-economics: no new tables, services, routers, or payload shapes.
- `serialize_item` and the item money fields are **untouchable** (owner decision
  R5-2: that exposure ends in phase 6 by column removal, not here).
- The three round-5 endpoint query services
  (`list_reassigned_steps.py`, `list_pending_step_acknowledgments.py`,
  `list_workers_last_interacted_step.py`) are **read-only for you** — design (a)
  makes the builders carry the fix; an edit there is out of perimeter.
- No relocation of serialization to routers (master plan §5 contract-gap 2 — the
  `46_serialization` divergence is recorded; do not "fix" it in passing).
- ADMIN/MANAGER payloads keep money everywhere, including both worker-stats
  endpoints (site 5, endpoint 8).

## Non-optional constraints (from the routed projection ledger)

- The derivation helper is **allow-list** form; hardcoded booleans at any derivation
  point are forbidden (plan tasks 2–3).
- The criteria harness is query-service-level integration testing exactly as the
  plan's criteria preamble pins it (router-idiom tests with stubbed `run_service` are
  forbidden for the payload rows; they cannot catch M2–M5).
- Present-rows assert equality against the seeded non-NULL value, never bare key
  presence.
- The two existing tests named in the plan's Notes are handled exactly as pinned
  there (minimum-edit keyword fix; role-re-parametrization with a Review-log record).
- **Before your first change:** run the full suite (`PYTHONPATH=. pytest -m 'not e2e'`
  from `backend/app/`) and record the baseline (counts + any pre-existing failures)
  in the plan's Review log (master plan §10 assigns this to you).

## Explicit delegation list (decisions granted to you on purpose — from the projection)

1. Test file placement and names, within `15_testing`'s mirror layout.
2. Fixture/factory design for seeding the step graph — constraint: seed with
   `flush()` on the rolled-back `db_session` fixture, never commit; any factory you
   add must have a caller in this phase.
3. Whether the role→bool derivation helper lives beside `serialize_step` or
   elsewhere sensible — it must exist in exactly one place.
4. Whether row 16's unit test builds a `TaskStep` or passes a stub.
5. Ordering of the implementation tasks.

## Closing protocol (per your doctrine; summarized)

1. All criteria rows green; run each named mutation (M1–M6 + the two blanket-False
   probes) and confirm its listed rows turn red; **revert every probe** and declare
   the probe file list in your handoff.
2. Full suite green against the recorded baseline.
3. Archgraph: `archgraph_status` + orient on `table-task-step` at start; at close
   record the delta in one batched `archgraph_apply_changes` — expected ≈ zero new
   nodes; if zero, state the zero-delta explicitly in the handoff. Never adjudicate
   pending reviews.
4. Tracker row → `IMPLEMENTED` (your row only); Review log entry in the plan file
   (baseline, key-set change record, judgment calls).
5. Checkpoint commit under the standing authorization, subject prefixed
   `CHECKPOINT (not approved): item-cost phase 1 — <summary>`.
6. Deposit the handoff at
   `handoffs/implementer/2026-08-12_phase1_implement_r1_handoff.md` with frontmatter
   (`plan`, `role`, `round`, `date`, `state`, `verdict`, `actor`) and body: summary;
   `⚠ OWNER DECISIONS REQUIRED (n)` (one line if zero); what was implemented vs the
   plan, with every judgment call named (the reviewer probes these); test counts
   before/after; mutation-probe run + reversion declaration; the session's **full
   write perimeter** (every file, every tool-recorded state change, the checkpoint
   commit hash).
