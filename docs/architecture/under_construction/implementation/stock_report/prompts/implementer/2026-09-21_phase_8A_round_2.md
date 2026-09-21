---
phase: 8A
role: fix
round: 2
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Sonnet
---

# Phase 8A round 2 — make the supplied `item_category_id` take effect

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/implementation-executor.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)

Plan: `SR/plans/plan_8A.md` — **read §7's "Round 2" note first**, then C3(e) (corrected) and
**C3(g)** (new). Authority: `SR/planning/intention.md` **§14G** and **MC-21**, RATIFIED, which win
over the plan.

**Phase 8A was APPROVED at `fec7d43` and has been reopened for this one defect.** Everything else
in it is verified and shipped — do not revisit it.

## The defect, precisely

The request's `item_category_id` is **inert**. It appears exactly twice in
`app/beyo_manager/services/queries/stock_report/preview_stock_task_assignment_match.py`: the
request model, and the line building the transient `candidate` item. From there:

- `evaluate_stock_criteria(candidate, row.properties)` reads `properties` and `quantity` **only**
  — the criteria matcher never reads a category.
- `evaluate_assignment_checks(...)` is passed **`item=matched_item`**, not `candidate`.
- In the no-item branch, `assumed` marks `item_has_no_category` and `category_mismatch` as
  `NOT_EVALUATED`.

So on **both** branches the supplied category changes no output. With an item it is correctly
discarded in favour of the stored one; with no item it is read by nothing.

**Why this is a defect and not a missing feature.** §14G semantics 2 has always said that when no
item resolves, *"the category, property and quantity checks still run against the supplied
values"*, and the published v2 frontend handoff says the same. Plan 8A C3(e) and the code were the
only two artifacts that disagreed, and C3(e) has now been corrected by the owner.

**Why it matters.** `category_mismatch` is one of only two MC-13 refusals with **no override**. A
form supplying a mismatched category gets `can_proceed: true`, creates the item, and only then
discovers it can never be assigned — the exact failure §14G exists to remove, and precisely the
preview/create divergence **MC-21 forbids**.

## The fix

1. Pass **`candidate`** as `evaluate_assignment_checks`'s `item=` argument.
2. In the no-item branch, the `assumed` NOT_EVALUATED set becomes exactly **four**:
   `item_not_found`, `item_not_task_primary`, `already_processed_by_scanner`,
   `item_already_assigned`. **Remove `item_has_no_category` and `category_mismatch` from it.**
3. Keep `item_id=None` when nothing resolved, so those four stay genuinely unevaluable.
4. **Do not change the stored-item branch.** When an item resolves, `candidate` *is* the matched
   item, so stored values keep winning and `values_source` stays `"stored"` — C3(f) already pins
   this and must stay green.

Watch the interaction with the null-`task_id` path: `task_not_found`,
`task_failed_or_cancelled`, `item_not_task_primary` and `already_processed_by_scanner` are
`pass_by_construction` there, and that `assumed.update(...)` runs **after** the no-item block, so
it must keep winning for those two overlapping checks. C3(e) and C5(a) both cover this — if you
cannot keep both green, **stop and report**, do not reorder on a guess.

## Your rows

**C3(g)** is new and yours to arm — three cases, no item resolving:

| case | supplied | expected |
|---|---|---|
| (i) | `item_category_id: K` (R's own) | `category_mismatch` **pass**, `item_has_no_category` **pass**, `can_proceed true` |
| (ii) | `item_category_id: K2` (different) | `category_mismatch` **fail**, `can_proceed` **false**, `refusal_reason == "category_mismatch"` |
| (iii) | `item_category_id: null` | `item_has_no_category` **fail**, `refusal_reason == "item_has_no_category"` |

All three: `matched_item_client_id is None`, `values_source == "supplied"`.

Its named mutation is in the cell: pass `matched_item` instead of `candidate`, and case (ii)
regresses to `not_evaluated` / `can_proceed true`. **Run it, observe red, revert, prove the revert
with `git diff --quiet`.**

**C3(e) was corrected** — its four are now `item_not_found`, `item_not_task_primary`,
`already_processed_by_scanner`, `item_already_assigned`. Its existing test asserts the old,
wrong four and **will need updating**; that is expected, not a regression. Say so plainly.

## Environment

**Set `BEYO_TEST_SLOT=a8` on every pytest command** — a batch C2 fix round is running
concurrently on slot `c2` and in different files. `pytest.ini` carries `-n 6 --dist loadfile`.

```
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest <file>
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest -m 'not e2e'
```

**Your gate is 23 failures, not 21** — the published 21-ID set plus the two
`test_database_isolation` IDs that are red under any named slot (master plan §10 ruling). That is
a pass. Baseline: **23 failed / 3661 passed / 1 skipped**.

**Also re-run phase 8's own suite** — it is the MC-21 extraction's standing guarantee and must
stay at `42 passed`:

```
cd app && BEYO_TEST_SLOT=a8 PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py
```

`create` must be **completely unaffected** by this change. If it moves at all, stop and report.

## Out of scope

The C2 fix round owns `sync_task_stock_assignments.py`, `_move_assignment.py`,
`_task_state_write_scanner.py` and plans 9/10 — **do not touch them**, and do not report their
movement. Commit with **explicit paths, never `git add -A`**. Never push. Do not edit
`master_plan.md`, the intention, or any criterion cell — plan Review log entries only.

## Handoff

`SR/handoffs/implementer/2026-09-21_phase_8A_round_2_handoff.md`: the diff · C3(g)'s three cases
green · **its mutation observed red and reverted, with the proof** · the C3(e) test update and why
· phase 8's `42 passed` unchanged · one L4 at 23 with both ID diffs and reconciled arithmetic ·
anything you found wrong · owner questions under `⚠ OWNER DECISIONS REQUIRED (n)`.

Checkpoint `CHECKPOINT (not approved): phase 8A round 2`.

## Stop conditions

The supplied category takes effect · C3(g) armed and its mutation red · C3(e) updated to the
corrected four · C3(f) and C5(a) still green · phase 8 still `42 passed` · one L4 at 23 · lint
clean · Review log written · handoff complete · checkpoint committed.
