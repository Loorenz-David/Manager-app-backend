---
plan: phase 8B (inline item prices at task creation)
role: fix
state: IMPLEMENTED
date: 2026-08-15
actor: Codex
---

# Phase 8B fix r2 — implementer handoff

## Summary

Fix r2 is implemented within the cycle fence. The test harness now covers the
superseded-only existing-item branch using the three production valuation
commands, and C4 rows 2/3 capture all rollback-sensitive identifiers into plain
locals before their `try` blocks. No production code was changed.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Findings resolved

- F1/S1: C4 row 4 seeds v1 → v2 → delete(v2), asserts v1 superseded/not
  deleted, v2 deleted/not superseded, asserts no current valuation, then
  creates the task and asserts the chain grows to three rows with v3 current.
- F2/S2: C4 rows 2/3 capture `workspace_id`, `user_id`, `item_id`, and the
  matched item's article number before commit/rollback-sensitive work. Their
  cleanup no longer dereferences expired ORM instances on a failure path.
- F3: the mutation records below pin deletion/inversion sites by line and
  state the observed scope. State claims are backed by the SQL query recorded
  below.

## Mutation ledger

All mutations were applied, run, and reverted. The restored production hash is
`e9c2ccc1bfda4c133149195e530977860eaefba31508b30e492a42bd6e41d547`.

| mutation | expected red | observed red and scope | mutant SHA-256 |
|---|---|---|---|
| M6: delete `ItemValuation.superseded_at.is_(None)` at `create_task.py:331` (line 331 only, definition site) | `test_c4_row_4_superseded_only_existing_item_accepts_and_grows_chain` | Exactly 1 failed / 21 passed over the full phase-file scope (`test_phase8b_inline_task_prices.py`) | `98dc2c252e8f5bdac1ea7ecc5aeff0391fd6fd081f684d45dbf86ada718174bd` |
| M2: invert `if item_has_current_valuation` at `create_task.py:337` (line 337, definition site) | `test_c4_row_2_never_valued_existing_item_accepts_inline_price` | Exactly 1 failed in the one-row scope; the intended refusal was raised | `f0776418c7cdc77faf76907bc47545ce70d244106e35d6e88ba9f09940cb2f95` |

Both mutation runs restored the production file before subsequent verification.

## Verification

- Focused phase file: **22 passed**.
- Full non-E2E foreground suite: **2184 passed / 23 established failures /
  1 deselected**; **2208 collected, 1 deselected**. The 23 failure IDs remain
  byte-identical to the established phase-1 baseline.
- Ruff: clean on `tests/integration/services/commands/item_economics/test_phase8b_inline_task_prices.py`.
- Database: `c1d2e3f4a5b6 (head)`; no migration was created or run.
- Final test-file SHA-256:
  `12c6ad5bd81c03f668dbd9a8a2716c7eec2020e7fadaac748f99b5bf090daf39`.

The post-M2 and close state query was:

```sql
SELECT 'workspaces', count(*) FROM workspaces WHERE name LIKE 'phase8b %'
UNION ALL SELECT 'users', count(*) FROM users WHERE username LIKE 'phase8b_%'
UNION ALL SELECT 'categories', count(*) FROM item_categories WHERE name LIKE 'Wood category %'
UNION ALL SELECT 'audits', count(*) FROM audit_logs WHERE actor_label LIKE 'phase8b%'
UNION ALL SELECT 'valuations', count(*) FROM item_valuations
  WHERE workspace_id IN (SELECT client_id FROM workspaces WHERE name LIKE 'phase8b %');
```

Result in both checks: `workspaces|0`, `users|0`, `categories|0`, `audits|0`,
`valuations|0`.

## Checkpoint

Checkpoint commit: `4369a27` — `CHECKPOINT (not approved): item-cost phase
8B fix r2 — test integrity`.

## Full write perimeter

Fix changes:

- `app/tests/integration/services/commands/item_economics/test_phase8b_inline_task_prices.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_8b_inline_task_prices.md`
- this handoff file, deposited after the checkpoint

Mutation probes, applied-and-reverted separately from the fix changes:

- `app/beyo_manager/services/commands/tasks/create_task.py` — M6 and M2 only;
  restored byte-identically to the pre-probe production hash above.

Tool-recorded state:

- Architecture Graph was read-only: 174 nodes, 260 edges, revision
  `53fdbc785621c38a295ae90ac09c67339ca654563d0b2f6480d034fc11868fd1`, five
  pending reviews, zero stale nodes, zero diagnostics, zero delta.
- No other test file, production file, migration, `.archgraph` file, or
  disposable database was changed or created.

## Coordinator fold-ups

The tracker is `IMPLEMENTED` for fix r2. The phase plan Review log contains the
F1/F2 results, mutation hashes, focused/full counts, database head, graph
zero-delta statement, and final test-file hash. F4 remains held for the
post-approval human graph pass; no graph mutation was performed in this cycle.
