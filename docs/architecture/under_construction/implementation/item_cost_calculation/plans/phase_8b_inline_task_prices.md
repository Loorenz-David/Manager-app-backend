# Phase 8B — Inline item prices at task creation

```
plan: phase 8B
role: phase plan (coordinator-authored, round 18; the projection gates it)
date: 2026-08-15
state: NOT_STARTED
```

## Goal

Ship §7B.6 (round 18, R18-1): the task-creation item block accepts the
valuation vocabulary (`expected_sale_price_minor`, `purchase_cost_minor`,
`currency` — mirroring `ItemValuationRequest`); on a NEWLY CREATED item with
any of the trio present, valuation version 1 is written through the
registered chain writer inside `create_task`'s transaction BEFORE the
§7B.5 auto-commit savepoint, so the task is priced in one call. On a
matched EXISTING item, inline prices REFUSE (conservative default — the
projection may card it). Legacy money keys stay rejected (`ITEM_MONEY_MOVED`
unchanged). **No new status, read surface, or schema.**

## Read first

1. Intention **§7B.6 (NEW, governing)**, §7B.5 as amended rounds 16,
   §11A.5 (R13-1 first-save-is-v1), §6A.9 (currency), §4.7A.
2. Master plan §6.4 (ITEM_MONEY_MOVED row — must keep biting), §6.5
   (`write_item_valuation_chain_in_session` in `_common.py`; the valuation
   audit events), §9 ALL rules — esp. expected-red (every named mutation
   names its red node id), deferral cap (zero deferrals — this phase is
   small), P-AB (if any helper gains a mode parameter, enumerate its
   gated effects), endpoint-boundary rule.
3. In-tree: `services/commands/tasks/requests/__init__.py`
   (`FindOrCreateItemInput` :25-50 with `reject_legacy_money`),
   `create_task.py` (the item-creation branch and the §7B.5 savepoint at
   :311-ff), `services/commands/item_economics/_common.py` (chain writer),
   `services/commands/item_economics/requests/__init__.py:116-121`
   (`ItemValuationRequest` — the vocabulary being mirrored).

## Dependencies

Phase 8 APPROVED (shipped). Phase 9 BLOCKED on this phase (the frontend
handoff documents the post-8B flow).

## Files expected to change

- `app/beyo_manager/services/commands/tasks/requests/__init__.py`
  (`FindOrCreateItemInput` += the trio; validation: currency required iff
  either amount present; ge=0; legacy rejection untouched)
- `app/beyo_manager/services/commands/tasks/create_task.py` (the valuation
  write on the item-creation branch, before the savepoint; the
  existing-item refusal)
- `routers/README.md` (task-creation body mirror row); tests
- NO migration; NO new files expected (the projection verifies)

## Implementation tasks (ordered)

1. Request vocabulary: the trio on `FindOrCreateItemInput`, mirrored
   semantics (`ge=0`; currency REQUIRED iff either amount present —
   pydantic 422, no domain identity; the §6.4 registry decides if one is
   needed).
2. The birth write: on the created-item path, when any trio field present →
   `write_item_valuation_chain_in_session(...)` (v1: no supersede, R13-1),
   `created_by_id = ctx.user_id`, the registered `item_valuation.created`
   audit event — all inside `maybe_begin`, BEFORE the auto-commit
   savepoint.
3. The existing-item refusal: matched item + any trio field → registered
   refusal identity (propose to the coordinator before use — the 4B N-c
   pattern), `ValidationError`, nothing written.
4. Router body mirror + README row.

## Acceptance criteria (the projection re-derives and hardens these)

**C1 — birth with prices:** create task with a new item + trio → exactly
one valuation row (v1: `superseded_at IS NULL`, `created_by_id` = creator,
figures/currency as sent); in an evaluable workspace the auto-commit fires
(committed evaluation exists, inputs from the valuation, no mirror — C5
row 4 discipline); in an unconfigured workspace the task is created, the
valuation EXISTS, and the skip line logs the resolver status. Named
mutation: delete the valuation write at its definition site → expected red
node named in the plan before implementation.

**C2 — no prices ⇒ byte-old behaviour:** trio absent → no valuation row,
the phase-8 `item_unvalued` flow intact (regression rows = the shipped
phase-7/8 suites stay green; collection delta reconciled).

**C3 — legacy keys still die:** the three legacy names each still 422
`ITEM_MONEY_MOVED` (P-G retention rows — the new trio must NOT soften the
bridge); mixed payload (legacy + new) also 422.

**C4 — existing-item refusal:** matched existing item (with and without a
current valuation) + trio → the registered identity, no valuation written,
no task created (or task created without prices? — the projection pins
the atomicity: recommend REFUSE THE WHOLE REQUEST, nothing written).

**C5 — currency/validation rows:** amount without currency → 422; negative
amounts → 422; currency alone (no amounts) → pinned by the projection
(recommend: accepted-and-ignored OR 422 — decide one).

**C6 — router boundary:** the task-creation body model carries the trio at
the HTTP boundary (phase-6 D6 discipline: deleting them there silently
drops client money — survival row) and OpenAPI advertises them.

## Notes

- The §7B.5 savepoint discipline is untouched: the valuation write is NOT
  inside the savepoint (a valuation that persists while the auto-commit
  rolls back is CORRECT — the price is real even when pricing the task
  fails; state this so nobody "fixes" it) — the projection verifies this
  reading of §7B.6 or cards it.
- Archgraph: delta = the reads/writes this adds to `command-task-create`
  (writes_to table-item-valuation via the shared chain) — small additive
  batch; orient on `command-item-economics-set-item-valuation`,
  `table-item-valuation`.

## Review log

(append-only)
