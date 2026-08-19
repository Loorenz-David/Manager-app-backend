---
plan: 3
role: implement
round: 2 (fix)
date: 2026-08-19
state: IMPLEMENTED
actor: Claude (Opus 5) — replacing Codex for this round
---

# Phase 3 fix r2 handoff — three should-fixes, no behaviour change

All three should-fixes are applied inside the two-file perimeter. **The production file changed
zero executable lines**; the test file changed exactly three (one import, two deletions).
Everything else is comment text.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required. No STOP was entered.

## What changed

**F-1 — the two F8 comments (`get_task_price_scenario.py`).** Both dangling `(C10)` references
are gone. Each comment now opens `This line only —`, resolves its cross-reference as
`path:symbol` / `path:test_name` (`get_task_budget_status.py:_load_task_and_item`,
`test_price_scenario_query.py:test_c10_task_resolution_is_workspace_scoped_and_hides_deleted`),
and closes by naming the predicates below it as load-bearing. The coordinator amendment
(`below this one`) is applied verbatim in both, so the count in the sentence matches the
predicates the reader sees: three below in `_current_valuation`, two below in `_typical_block`.
`superseded_at.is_(None)` is no longer sitting under an unqualified "redundant" line.

**F-2 — the inert GUCs (`test_price_scenario_query.py`).** Both
`await db_session.execute(text("SET LOCAL …"))` statements are deleted, `text` is dropped from
the SQLAlchemy import, and the comment above the two UPDATEs now credits only the mechanism that
exists — the `older`-before-`current` update order — states that it was measured, states that
heap order is not a guarantee, and separates the assertions from it by naming the real
determinism source. Per the coordinator amendment the index reference ends at
`models/tables/item_economics/item_valuation.py`, with no line number. (Confirmed present and
greppable: `uix_item_valuations_current`, `item_valuation.py:35` at this checkout.)

**F-3 — the latency acceptance (`get_task_price_scenario.py`).** The F9 decision now lives at
the `budget_status = await get_task_budget_status(ctx)` call site, verbatim: what is re-read,
roughly eight redundant round trips on the no-evaluation branch, why collapsing it means
changing `TaskBudgetStatus` (a contract other screens consume), and what the duplication buys —
status, binding and tenant boundary identical to `get_task_budget_status`.

## N-3 — the sentence C1's second clause was owed

**Before `test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain` existed, dropping
`superseded_at.is_(None)` from `_current_valuation` left the entire phase test file green.**

That clause had never been stated outside `plans/plan_3.md` §3 F4, which archives. It is not
repeated here on authority — it was re-measured this round, with the C1 row removed and the
mutation applied together:

```text
pytest tests/integration/services/queries/item_economics/test_price_scenario_query.py
48 passed in 0.43s
```

Both files were restored byte-identical afterwards (SHA-256 below). C1 is the only row in the
file that can see this mutation at all.

## Mutation ledger (D3)

The C1 named mutation was re-applied at its definition site **after** the F-2 deletion, measured
across the whole non-E2E suite (never `-k`), reverted by file restore, and SHA-256 checked.

| Definition site and mutation | Contract side | Mutation side | Complete observed-red delta | Revert SHA-256 |
|---|---|---|---|---|
| `get_task_price_scenario.py:_current_valuation`, drop `superseded_at.is_(None)` | saved ID `ival_price_chain_current_115c756b10`, price `855000` | saved ID `ival_price_chain_old_115c756b10` — `AssertionError: assert 'ival_price_chain_old_115c756b10' == 'ival_price_chain_current_115c756b10'` | `tests/integration/services/queries/item_economics/test_price_scenario_query.py::test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain` **only** | `07b7842e43d9fbc254e35ffb42ee7ccc9ab8d52c5363212980f95a1bb25086a3` |

Whole-suite arithmetic, diffed and not counted:

```text
Shipped state (this round's fixes applied):  26 failed, 2430 passed, 1 deselected  (122.29s)
C1 mutant:                                   27 failed, 2429 passed, 1 deselected  (122.82s)

diff baseline_ids.txt mutant_ids.txt
16a17
> …::test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain
```

The other 26 IDs are byte-identical between the two runs. **The GUCs were doing nothing**: the
mutant still returns the older row with both `SET LOCAL` statements deleted, which is the fourth
independent measurement agreeing (reviewer 3/3, coordinator, this run) and closes the STOP
condition F-2 named — it did not fire.

Test-file revert SHA-256 (unchanged across the N-3 counterfactual):
`5e52ac0fbb5c55144a847837c885f0e8ffafd4bd0329f83e43f415fbcd45c880`.

## Verification

```text
Focused phase file:  49 passed in 0.51s
Whole non-E2E suite: 26 failed, 2430 passed, 1 deselected   ← D7 exact

ruff check <the two Phase 3 files>          All checks passed!      (F401 clean — `text` gone)
ruff format --check <the two Phase 3 files> 2 files already formatted
git diff --check                            clean
```

Executable-line audit — the complete non-comment diff across **both** files is three lines:

```diff
-from sqlalchemy import delete, func, select, text
+from sqlalchemy import delete, func, select
-        await db_session.execute(text("SET LOCAL enable_indexscan = off"))
-        await db_session.execute(text("SET LOCAL enable_bitmapscan = off"))
```

D1 is therefore exact: zero executable lines changed in `get_task_price_scenario.py`.

## §7 — the drifting test

**It did not appear.** `test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
was **absent from both** of this round's whole-suite runs; the failed set was the same 26 IDs each
time. That is a fifth and sixth observation for master plan §6, and the first two in which the ID
is green in a full-suite run: **implementer 27, implementer 27, coordinator 26, reviewer 26,
this round 26, this round 26 (mutant)**. Consistent with a real-concurrency flake, not with a
persistent failure that some runs miss.

Note for the next reader: this session had to run the suite as `PYTHONPATH=. pytest -m 'not e2e'`
from `app/`; the bare `make test` form failed collection with `ModuleNotFoundError: beyo_manager`
under this shell. Collection is otherwise identical — the 2430/26/1 arithmetic matches the gate.

## Architecture Graph delta

**No graph mutation: 0 nodes, 0 relationships, 0 source links.** This round changed comment text
and deleted two inert test statements; nothing about the graph's model of the code moved. No
`archgraph_*` tool was invoked — N-6 (anchor drift on the pending `ai_inferred` items,
`staleNodeCount` 0 → 1) is routed to the coordinator's pending-review queue and was deliberately
not touched.

## STOPs and scope

None. No third file was needed for any of the three fixes. Nothing from §5 was acted on. Phases 1,
2 and 4 were not opened. Nothing was committed and neither the master plan tracker nor plan 3's
Review log was updated.

## Full write perimeter

From the closing `git status --porcelain --untracked-files=all`.

Session-owned writes:

1. `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py`
2. `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py`
3. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/implementer/2026-08-19_phase3_fix_r2_handoff.md`

**Not this session's — the owner's concurrent, unrelated change**, present in the same status
output and neither touched, staged, reverted nor counted:

- `.archgraph/architecture.yml`
- `app/beyo_manager/services/queries/items/lookup/purchase_api.py`
- `app/tests/unit/services/queries/items/test_lookup_item_by_article_number.py`
