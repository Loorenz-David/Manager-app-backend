---
plan: phase 8 (status & results — status query, result handler, §8B emissions)
role: reviewer (projection)
round: 0 (pre-implementation projection gate)
date: 2026-08-14
---

# Session prompt — phase 8 projection, round 0

You are the **projectionist** for phase 8 — the last mechanism phase: the
live status query (manager + worker faces), the result handler that freezes
actuals at episode close, and the §8B boundary emissions. The plan was
written 2026-08-12, BEFORE rounds 13–16 and phases 4B/5/6/7 shipped. Find
where it no longer survives contact; deposit an amendment ledger.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

## Ground

- Plan under projection: `plans/phase_8_status_results.md` **including its
  accumulated forward notes** — D23 (its C7 says "all eleven values"; the
  shipped `EconomicsStatusEnum` has TWELVE), N15 (rederive marker is an
  integrity signal, never proof of corruption), 4B N3/N4 (redundant deleted
  clause; `status.value == "ok"` string compare), phase-7 N6 (the
  `_load_preview_inputs` vs `_load_live_inputs` two-loader drift hazard —
  this phase owes the structural pin), and the inherited C13 router
  completeness arbiter + D16 rederive-escalation discipline.
- Also inherited from phase-7 re-review r2: **R2-N2** — the C10 event seam's
  visibility assertion is loop-guarded and could go vacuous; phase 8 owns
  the one-line hardening (`assert checked == 1`).
- And from phase-5 review r1: **N2** — `delete_item_valuation`'s response
  hardcodes `item_unvalued`; this phase's status vocabulary work is where
  that gets consumed or corrected.
- Semantic authority: intention §8A ENTIRE (§8A.1 consumption read one
  expression; §8A.2 two-cost-numbers boundary; §8A.3 result-handler
  idempotency; §8A.4 replay identity column set; §8A.5 re-emit R4-1; §8A.6
  live status), **§8B entire** (round 6: result computed at EVERY episode
  boundary, READY/reopen hooks, widened guard, C6b), §11A (exposure
  predicate; §11A.2 census; §11A.3 worker serializer has NO monetary keys —
  P-H's structural criterion; §11A.4 twelve-value vocabulary as amended
  §7C.3), §4A (state snapshot + nullable closed_at + refresh at reopen),
  §7B.3 (item_binding: bound/mismatched/detached — the status query
  surfaces it).
- Registry: master plan §6.4 (incl. the phase-7 status→identity mapping
  table), §6.5 (the worker handler `process_item_cost_result`, task type +
  `"queue:analytics"` routing, `ItemCostResultPayload(workspace_id,
  task_id)` frozen dataclass, `get_task_budget_status` /
  `get_task_budget_status_worker` as SEPARATE services, budget-status route
  all-roles with role-split serialization); §9 P-A…P-AB + ALL extensions
  bind — note the six phase-7-review rules AND the four re-review rules
  (P-AB + companion, adoption-fidelity, P-I 9th, P-S template, deferral
  rule, P-T 3rd/P-Q 4th/P-R 2nd).
- Shipped reality: phases 3–7 (head `be9dfe42a035`; items carry NO money;
  `resolve_economics_selection` / `resolve_item_economics_status`;
  evaluations + projections + auto path live with 5 routes; the rederive
  marker consumed by `list_task_evaluations` with the ERROR idiom;
  `_ROUTES` is 21 rows with a set-equality completeness arbiter).

## Environment facts (verified at phase-7 closeout, 2026-08-14)

- Head `be9dfe42a035` (phase 8 SHOULD need no migration — verify the plan
  agrees; `item_cost_results` shipped in phase 2); suite baseline
  **2076 / 23 / 1 deselected = 2099 selected**; failure set = the phase-1
  list. Economics tables all 0 rows.
- Graph: **166 nodes / 239 edges, 0 pending, 0 stale, ALL human_confirmed**,
  revision `b0f9127d…`. `list_task_evaluations` is typed `projection` (the
  read-model convention) — this phase's two status queries should expect
  the same treatment in their delta.
- Integration tests on the queue path need the analytics worker (master
  plan §10 Makefile caveat); in-process handler invocation is the default
  test seam.

## Projection axes (minimum — the ledger is yours)

1. **Rounds 13–16 drift:** every claim about status vocabulary, valuation
   reads, group resolution, or item money predates the category contract,
   R13-1's preview key, R15-1, and round 16. The status query consumes the
   phase-5 resolvers and the §6.4 mapping — never re-derives.
2. **C7's enumeration vs the shipped enum** (D23): twelve members, one
   parametrize id each, expressions differing per row (P-V 3rd ext).
3. **§8A.3 idempotency + §8A.4 replay identity:** recompute-and-SET, no
   dedupe; the replay column set against `computed_at`; "result exists but
   evaluation gone" is unreachable (INV-E2) — build no handling.
4. **§8B boundaries:** which transitions emit (READY, reopen, close), the
   widened guard, C6b; §4A refresh-at-reopen. The transition core shipped
   phases ago — re-run the dependency greps against the CURRENT
   `task_steps`/transition files, not the plan's memory of them.
5. **The money boundary (P-H):** the worker status payload has NO monetary
   keys — the structural criterion for the HTTP layer (no `response_model`
   re-adding fields), the separate-serializer rule (§11A.3), and the
   role-split handler on ONE route. Payload-key greps for every new key
   (Projection practice).
6. **The two-loader pin (phase-7 N6):** decide the shape — one shared
   predicate or an equality property row — and give it an arbiter that a
   future divergence actually reddens.
7. **Criteria quality under §9 as it stands** — including the new rules:
   lock criteria name counterparty MODES (P-T 3rd); prescribed fixtures are
   checked against engine semantics (P-Q 4th); second-session criteria name
   the committing harness (P-R 2nd); parameter-gated helpers enumerate
   effects read off the code (P-AB + companion); named mutations phrased
   for byte-reproducibility (P-I 9th); deferral defers work, not risk.
8. **Decidability:** reject any clause whose prose and verbatim predicate
   disagree.

## Closing protocol

1. Deposit an amendment LEDGER (numbered rows, severity, section amended,
   verified corrections — executed where cheap). `⚠ OWNER DECISIONS
   REQUIRED (n)` for anything semantic (story-shaped cards, branches +
   recommendation + on-silence).
2. No code, no plan edits, archgraph READ-ONLY (state revision `b0f9127d…`,
   0 pending — zero delta).
3. Deposit at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase8_projection_r0_handoff.md`
   (full path, AFTER your writes): ledger; any live measurements; full
   write perimeter + probe declaration.
