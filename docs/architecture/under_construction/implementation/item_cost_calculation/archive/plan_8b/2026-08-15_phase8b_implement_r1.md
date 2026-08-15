---
plan: phase 8B (inline item prices at task creation — round 18)
role: implementer
round: 1
date: 2026-08-15
---

# Session prompt — implement phase 8B

You are the **implementing agent** for phase 8B — deliberately the SMALLEST
mechanism phase of the project: two production files, reused machinery, no
migration, no new read surface. The projection did your first hour on
paper; its 18 rows are routed and the plan's B1–B10 block is GOVERNING.
The bar set by phase 8's endgame applies in full: zero mutation deferrals,
expected-red ids stated per row BEFORE the runs, per-row mutant hashes.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## The plan — read BOTH layers as one document

`docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_8b_inline_task_prices.md`:
base + the **"Amendments (projection r0)" block B1–B10, GOVERNING**
(trio shape; C5's five rows incl. currency-alone accepted-and-ignored;
C1's six rows; C4 on the OWNING harness with branch-B rows; C3's three
rows + validator-order pin; C6's two harnesses, OpenAPI clause dropped;
the pinned insertion point; the two stability sentences; the reality
pins; the R18-2 routings).

Also read AS AMENDED (round 18 + the R18-3 fold): **intention §7B.6 with
lettered (a)/(b)** — the trio's real shape and the branch-B
existing-item rule (refuse IFF a current valuation exists; never-valued →
v1; deleted/superseded-only → NEXT version, an explicit act distinct from
R15-1); §4.7A (create_task is now the FOURTH registered valuation
writer); §11A.5(c) as corrected; §7B.5 (the savepoint discipline the
birth write sits OUTSIDE of — deliberately). Master plan §6.4
(**`ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`** registered — ValidationError,
message names the item's client_id + points at the valuation endpoint;
`ITEM_MONEY_MOVED` must keep biting), §6.5, §9 ALL (~60 rules).

## Environment facts (projection-verified, 2026-08-15)

- Head `c1d2e3f4a5b6` (NO migration this phase); suite baseline
  **2138 / 23 / 1 = 2161 selected (2162 collected)**; graph 173/256, ALL
  human_confirmed, 0 pending, 0 stale, rev `45b72196…`.
- Exact citations (projection L13): `FindOrCreateItemInput` class at
  `tasks/requests/__init__.py:27` (validator ends :50);
  `create_task.py` — TaskItem flush :306, savepoint `try` :308,
  `begin_nested()` :309, block ends :324; item paths :195-227
  (always-creates) and :228-296 (`find_or_create_item`, `was_created`
  :238); chain writer `_common.py:117-169`; README section
  **`PUT /api/v1/tasks`** at `routers/README.md:2627`.
- `test_phase6_api_bridge.py:87-97` asserts the legacy tokens appear
  NOWHERE in `create_task.py` source — never name a local
  `item_currency`.

## The work (ordered)

1. **The trio (B1):** on `FindOrCreateItemInput` — all optional, `ge=0`,
   currency-iff-amount as a `model_validator(mode="after")` DEFINED AFTER
   `reject_legacy_money` (the order pin, B5); mirror the three fields into
   `_TaskItemInputBody` (`routers/api_v1/tasks.py:95-114`).
2. **The write site (B7):** one site after the TaskItem flush (:306),
   before the savepoint (:308) — both item branches set a newness /
   current-valuation flag. Branch-B logic: current valuation exists +
   trio → raise the registered identity (whole request aborts); no
   current valuation + any amount → chain write (v1 or next version),
   `created_by_id = ctx.user_id`, `item_valuation.created` audit —
   exactly the PUT path's effect set, nothing more (L9's verified list).
   Currency-alone → no write (B2).
3. **Tests per the amended criteria:** C1's six rows (+optional
   zero-price row, declared either way), C2 regression, C3's three rows,
   C4's harness + three rows (refusal w/ byte-unchanged item;
   never-valued accept; deleted-only accept asserting the chain GREW),
   C5's five rows, C6's two harnesses, B8's non-vacuity mirror
   companion.
4. **Mutations — zero deferrals, expected-red ids stated per row BEFORE
   the runs, per-row mutant hashes (P-I 9th hard field):** the valuation-
   write deletion (B3); the refusal-predicate inversion (B4 — both ids);
   the validator-order swap (B5-i); the `reject_legacy_money` deletion
   (B5-ii — the three shipped retention nodes); the `_TaskItemInputBody`
   field deletion (B6). Committing subsets twice, residue scope named
   (rule 11½); the C4 harness owns its teardown.

## Scope fence

Production: `services/commands/tasks/requests/__init__.py`,
`services/commands/tasks/create_task.py`,
`routers/api_v1/tasks.py` (`_TaskItemInputBody` only),
`routers/README.md` (the three `item.*` rows under `PUT /api/v1/tasks` —
NOTHING else in that file; no regeneration attempt). Tests: new phase-8B
file(s) + extending the `test_phase6_api_bridge.py` retention
parametrization (never duplicating it). Docs: master plan tracker + plan
Review log + your handoff. **No migration. No item_economics production
files. No new files beyond tests.** If anything else seems needed, stop
and report.

## Archgraph

Orient read-only (rev `45b72196…`, 0 pending, 0 stale). Delta at end: ONE
additive batch — a **NEW `command-task-create` node** (none exists — B9)
with accurate spans + its edges (writes_to `table-item-valuation` via the
chain; the pre-existing task/item writes recorded at birth), plus
anything genuinely new. Never a delta against a node id you did not
verify exists.

## Closing protocol

1. All criterion rows green; the FULL mutation ledger (site → expected
   red id [stated before the run] → before/mutant sha256 pair → observed
   red → reversion proven); zero deferrals.
2. Suite: expect 2138+N / 23 byte-identical (sorted diff, say so) / 1
   deselected — numbers READ off YOUR foreground run; ruff on the
   perimeter; DB at head `c1d2e3f4a5b6` (no migration — say so);
   disposables (if any) dropped and listed.
3. Tracker → `IMPLEMENTED`; Review log per P-L; FINAL sha256 for every
   file touched.
4. Checkpoint `CHECKPOINT (not approved): item-cost phase 8B implement
   r1 — <summary>`; handoff AFTER (never inside), citing final hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-15_phase8b_implement_r1_handoff.md`
   (full path). `⚠ OWNER DECISIONS REQUIRED (n)` if any arise; full write
   perimeter + probe declaration; every delegation stated (incl. the
   optional zero-price row, either way).
