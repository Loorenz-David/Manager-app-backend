---
plan: phase 8B (inline item prices at task creation — round 18, R18-1)
role: reviewer (projection)
round: 0 (pre-implementation projection gate)
date: 2026-08-15
---

# Session prompt — phase 8B projection, round 0

You are the **projectionist** for phase 8B — a deliberately SMALL mechanism
phase born from an owner decision this morning: task creation accepts the
valuation vocabulary inline, so an item can be born with its prices and the
task priced in one call. The plan is coordinator-authored (round 18, hours
old) — your job is less drift-hunting than HARDENING: the mechanism reuses
shipped machinery, and the failure modes are integration seams, not new
ground. Do the implementer's first hour on paper; deposit an amendment
ledger.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

## Ground

- Plan under projection: `plans/phase_8b_inline_task_prices.md`
  (coordinator-authored — treat its criteria as DRAFTS to harden, not
  settled text).
- Semantic authority: **intention §7B.6 (NEW, round 18)** + the R18-1
  record in `planning/owner_decisions.md` (incl. the conservative
  existing-item default the owner accepted subject to your carding);
  §7B.5 as amended (the savepoint discipline; the §7B.6 note that the
  valuation write sits OUTSIDE the savepoint — verify that reading or
  card it); §11A.5 R13-1; §6A.9; §10A.3 (the bridge that must keep
  biting).
- Registry: §6.4 (ITEM_MONEY_MOVED; the refusal identity to be proposed),
  §6.5 (the chain writer + audit events), §9 ALL (~55 rules — the
  expected-red rule, deferral cap, structural-filter, distinct-values,
  scenario-fixture, endpoint-boundary, hand-written-literal,
  pipeline-ends all have obvious application here).
- Shipped reality: head `c1d2e3f4a5b6`; baseline **2138 / 23 / 1 = 2161
  selected**; graph 173/256 ALL human_confirmed, 0 pending, 0 stale, rev
  `45b72196…`; the phase-7/8 suites are the regression net (C2's claim).

## Projection axes (minimum — the ledger is yours)

1. **The find-or-create seam:** `FindOrCreateItemInput` serves both
   branches — enumerate what "matched existing item" means in the shipped
   code (client_id match? sku? article_number?) and whether the refusal
   can even be decided before the find-or-create resolves. The C4
   atomicity pin (refuse the WHOLE request) needs the transaction shape
   verified.
2. **The owner's conservative default (existing-item refusal):** pressure-
   test the story — a manager re-uses an item on a new task and passes
   prices out of habit; is a hard 422 the right experience, or should
   this be an owner card? If you card it, story-shaped, with the
   supersede-via-chain branch priced honestly (it is the PUT semantics
   inline — one rule — but lets task creation silently change a price).
3. **Multi-item and quantity:** the item block carries `quantity` and
   tasks can carry multiple items (§9.1 PRIMARY) — which item(s) may
   carry the trio? The PRIMARY only? Enumerate.
4. **The §7B.5 interaction rows:** valuation write BEFORE the savepoint;
   auto-commit sees it; savepoint rollback leaves the valuation (the plan
   says this is CORRECT — verify against §8/§7 semantics or card);
   C5-row-4 (auto path never mirrors) must stay true with the inline
   birth (the inputs ARE the valuation's — verify by construction).
5. **Validation rows** (C5): currency-iff-amount, currency-alone,
   negatives, zero; pydantic-vs-domain boundary per §6.4's carrier rules;
   the mixed legacy+new payload row.
6. **Criteria quality under §9 as it stands:** every named mutation names
   its expected red node id; no row shares a call graph with another;
   the bridge-retention rows are P-G-shaped; distinct values where
   exclusion is claimed.
7. **Dependencies greps** (the plan says NO new files, NO migration —
   verify against the tree; payload-key greps for the trio on task
   payloads).
8. **Decidability:** reject any clause whose prose and verbatim predicate
   disagree.

## Closing protocol

1. Deposit an amendment LEDGER (numbered rows, severity, section amended,
   verified corrections — executed where cheap). `⚠ OWNER DECISIONS
   REQUIRED (n)` for anything semantic — the existing-item default is the
   likely card; story-shaped, branches + recommendation + on-silence.
2. No code, no plan edits, archgraph READ-ONLY (state revision
   `45b72196…`, 0 pending, 0 stale — zero delta).
3. Deposit at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-15_phase8b_projection_r0_handoff.md`
   (full path, AFTER your writes): ledger; live measurements; full write
   perimeter + probe declaration.
