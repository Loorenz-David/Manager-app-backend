---
plan: plan_3
role: implementer
round: 2
date: 2026-08-23
actor: Codex
state: IMPLEMENTED
---

# Plan 3 fix round 1 redispatch handoff — evidence corrections

The fix round completed as an evidence-only session. No production file changed; both
pinned L1 mutations were applied, observed, and reverted immediately. No L4 ran.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs you.

## Corrected mutation ledger

| Criterion | Contract side | Mutation side | Result / failing test ID |
|---|---|---|---|
| C4 | Derive the carrier from the loaded PRIMARY item: `TypicalFilterSpec(item_category_ids=frozenset({"cat_chair"}))`. | The query-count-preserving replacement derives below the evaluation load from `evaluation`; against the content-blind double this proves only that the carrier stopped coming from the loaded PRIMARY item, not that it came from the evaluated item specifically. The withdrawn `cat_chair` → `cat_table` both-sides is not claimed. | **Matched:** 2 failed / 11 passed. `test_C4_manager_uses_loaded_primary_item_not_evaluation_item`; `test_C5_empty_status_preserves_no_item_vs_categoryless_item[C5-e-manager-categorized-primary-beyo_manager.services.queries.item_economics.get_task_budget_status-item2-expected2]`. |
| C1 | Field order is `evaluation_id`, `item_id`, `result`, then defaulted `typical_filter_spec`. | Legal swap: `item_id`, `evaluation_id`, `result`, then defaulted `typical_filter_spec`. | **Matched:** 1 failed / 12 passed. `test_C1_task_budget_status_appends_defaulted_spec_after_result`; `At index 11 diff: 'item_id' != 'evaluation_id'`. |
| C-N1(a) no-`WHERE` row | Active RELATED and removed PRIMARY legal shapes flush; a second active PRIMARY raises `IntegrityError`. | Without the partial `WHERE`, the legal shapes fail at their legal flush. | **Matched:** existing observation retained; no re-run required. `test_CN1a_primary_index_is_partial_and_two_legal_shapes_are_valid`. |

The C4 replacement and C1 mutation each ran over the whole contract file from `app/` at
L1 with `-n 0 -p no:randomly`. No L4 was owed or run because production code did not
change; the `186027a` production stamp remains applicable.

## Write perimeter

Before the checkpoint commit, `git status --short` showed:

- `M docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- `M docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_3.md`
- `?? docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/implementer/20260823_plan3_fix_round1_handoff.md`
- ` M .archgraph/agent-operating-policy.md` — owner's live edit, left untouched
- `?? .archgraph/contexts/` — expected, not staged

No file under `app/beyo_manager/` was modified at close. After the checkpoint, only the
owner's Architecture Graph policy edit and the expected untracked context directory
remain outside the committed documentation changes.

Checkpoint SHA: **`07201f3`** (`CHECKPOINT (not approved): record plan 3 fix round 1 evidence`).
This handoff line is the only follow-up documentation change after that checkpoint.
