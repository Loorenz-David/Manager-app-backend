---
plan: phase 4 (configuration services)
role: implementer
round: 1
date: 2026-08-12
---

# Session prompt — implement phase 4: configuration services

You are the **implementing agent** for phase 4 of the item-cost-calculation pipeline.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path, in this order)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

**The plan file is your task list; where this prompt differs, the plan file wins.**

## Gate check (verify before working; on any failure, stop and report)

- Tracker: phases 1–3 **APPROVED**, phase 4 **PROMPT_READY** (projection r0's
  24-row ledger is fully routed — nothing pending).
- No phase-4 implementer handoff exists (round 1).

## Read order (after doctrine)

1. `master_plan.md` — §§5, 6 entire **as amended 2026-08-12** (three new dual-path
   conflict identities; the audit event vocabulary; `is_applicable` registered;
   the §6.3 enum-order correction; the §6.5 calculator public API your rate
   derivation calls), 9 (P-B…P-Q bind), 10.
2. `plans/phase_4_configuration_services.md` — as amended 2026-08-12: task 2's
   canonicalize-then-derive (R11-1), task 3's index-discrimination idiom, task 4's
   pinned reference predicates, task 5's explicit-ordered-sequence rule, task 6's
   router-model docs, task 7's deliberate no-event absence; the harness block
   (concurrency sessions, seams, timeouts, teardown); criteria C1–C11.
3. Intention: §7A entire, §4.1–§4.4 + §4A, §7.1/§7.4/§7.5, **§6A.1 as amended
   round 11** (persisted-configuration-numerics rule), §6A.4 + R4-2, §6A.6,
   §11A.4, §14 tests 8/10/16.
4. Re-emit the master plan §5 contract resolution (`06_commands`+local,
   `32_concurrency`, `28_roles_permissions`, `36_audit_log`, `09_routers` are the
   load-bearing ones).

## Hard scope fences

- No valuations, evaluations, results, item/task reads; no term edit/delete
  commands (A6); no `EconomicsStatusEnum` reordering (the shipped order stays —
  precedence lives in your explicit sequence); no calculator edits; no workspace
  events from config commands (task 7 — deliberate).
- Serialization stays at the query layer (master plan §5 contract-gap 2).

## Non-optional constraints (from the routed ledger — the plan carries the detail)

- **Canonicalize-then-derive** (R11-1): quantize request numerics to column scale
  (HALF_EVEN) in the request models BEFORE deriving; C4's B1 row asserts the
  173.456 → 173.46/12.0105 fixture and rederive-agreement.
- **Index-name discrimination** (B2/B3): each violated index maps to ITS registered
  identity; unrecognized `IntegrityError` re-raises; the blanket wrap is forbidden.
- **Concurrency rows commit** — follow the harness block exactly (second session,
  interleaving, lock timeout, teardown DELETEs; the injectable `after_lock` seam in
  the delete command is designed, declare it).
- **C6 has TWO mutations, declared separately with observed node ids** (P-I as
  twice-extended); same per-row discipline for every named mutation in C1, C4, C5,
  C8's permutation probe, C11's retention mutation.
- Full-suite baseline before first change: expect 1749 passed / 23 failed /
  1 deselected (N14's Shopify test is order-flaky under load — re-run clean before
  concluding).

## Delegations (granted in writing — plan Notes)

Classifier signature (pure; injected date; explicit-sequence precedence); FastAPI
route syntax + POST creates; test placement; internal helper decomposition within
the registry rule. Nothing else — identities, fixtures, mutation sites, harness
mechanics, and reference predicates are pinned.

## Closing protocol

1. All criteria green (C1–C11); every named mutation run at its site, reverted,
   sha256-verified, **declared per row with observed node ids**.
2. Full suite green vs baseline (failure set byte-identical).
3. Archgraph: orient on the phase-2 table nodes + `domain-item-economics`; at close
   ONE batched `archgraph_apply_changes` — the configuration command/endpoint
   nodes with accurate spans. Never adjudicate. (Reviewer verifies; coordinator
   confirms post-approval per §8.)
4. Tracker row → `IMPLEMENTED` (Note appended; stamps preserved); Review log entry
   per P-L (what was built per criterion).
5. Checkpoint: `CHECKPOINT (not approved): item-cost phase 4 — <summary>`.
   **Deposit the handoff AFTER the checkpoint, citing the FINAL hash.**
6. Handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-12_phase4_implement_r1_handoff.md`
   (full path): frontmatter complete; summary; `⚠ OWNER DECISIONS REQUIRED (n)`;
   implementation vs plan with judgment calls named; test counts; per-row mutation
   declarations; the graph delta (node ids); full write perimeter incl. the final
   checkpoint hash.
