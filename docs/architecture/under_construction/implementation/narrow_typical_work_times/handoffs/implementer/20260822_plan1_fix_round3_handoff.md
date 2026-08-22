---
plan: plan_1
role: implementer
round: 3
date: 2026-08-22
actor: Codex
state: IMPLEMENTED
---

# Plan 1 fix round 3 handoff

The review-cycle defects are closed. The reconciliation suite now constrains the
task-scope short-circuit and every participating-section tuple, the parser rejects
malformed repeatable values at its boundary, and package-wide tests commit the C4(c)
and C17 purity claims. The only production change is `_optional_values`; the engine
logic and SQL snapshot remain otherwise untouched. Checkpoint: `1590ebe`
(`CHECKPOINT (not approved): plan 1 fix round 3 parser and test guards`). No owner
decision is required.

## OWNER DECISIONS REQUIRED (0)

None.

## 1. F1–F7 implementation ledger

All named probes below ran at L1 whole-file scope, never with `-k`, against the named
definition. Each mutation was reverted before the next probe and before the checkpoint.

| Finding | Change and contract side | Mutation side / result |
|---|---|---|
| F1 blocking / C8 row (g) | `reconcile_task_typicals` with `TypicalFilterSpec()`, all participants usable: `section_wide_uniform`, `applied_filter is None`, participant tuples use section-wide values/counts. | `effective_spec.is_narrowing` → `(spec is not None)` produced `item_narrowed_uniform` while `applied_filter` stayed `None`; `test_reconciliation_non_narrowing_spec_stays_section_wide_for_participants` failed. |
| F2 blocking / C8 tuples | Rows (a), (b), (e), (f), (j) assert `(typical_worker_seconds, typical_basis, sample_count, participates)` for every named section. Row (b) publishes section values `(900, section_wide, 61, True)` and `(1200, section_wide, 61, True)`. | In the participating non-uniform branch, `section_typical_worker_seconds` → `narrowed_typical_worker_seconds` changed row (b) to `(0, section_wide, 61)` / `(600, section_wide, 61)` and reddened the whole file. `section_sample_count` → `narrowed_sample_count` changed counts `61/61` to `5/7` and reddened the whole file. |
| F3 should-fix / C14 (o)(p)(q) | `_optional_values` rejects bare `str`, `bytes`, and non-iterable inputs with `ValidationError`; the three malformed cases are independent parametrized rows. | Restoring character-wise iteration made both string rows return specs and made integer `5` raise bare `TypeError`; all three parameter cases failed independently. |
| F4 should-fix / C7 row (n) | Non-narrowing, narrowed `(61, 600)`, section `(3, None)`, BROADEN returns `("insufficient_sample", None, 3)`. | `has_section` → `has_narrowed` changed the result to `("section_wide", None, 3)` and reddened the whole file. |
| F5 should-fix / C7 rows (h)(m) | Rows (h)/(m) compare the complete six-field `SelectedTypical`, including `participates=False` and the evidence object. | Setting `participates=True` in both non-narrowing returns made both full-object assertions fail. |
| F6 recorded / C4(c), C17 | New `test_domain_purity.py` walks every domain module, pins exactly one serializer mapping exception (`config_fingerprint`), and rejects all other hash/fingerprint terms plus `sqlalchemy`/`models.tables`. | Adding `import hashlib` failed the hashing guard. Adding `from beyo_manager.models.tables.items.item import Item` failed the import guard. Both were reverted. |
| F7 recorded / C8 row (c) | Added a two-participant below-floor/usable fixture; it asserts `section_wide_uniform` and exact section-wide tuples for both participants. | No mutation was required; this is the recorded non-biting control for C8 mutation (ii). |

## 2. Test evidence

Focused phase verification after all probes were reverted:

```text
PYTHONPATH=. pytest -q tests/unit/domain/item_economics/test_typical_filters.py tests/unit/domain/item_economics/test_domain_purity.py tests/unit/domain/item_economics/test_participating_sections.py
```

Result: **40 passed**, with the repository's existing pytest-asyncio deprecation
warning output. The new purity module contributes two tests; the malformed parser
rows are three parametrized cases.

Redis preflight before L4: `redis-cli ping` → `PONG`.

Authoritative L4 stamp, run once on the checkpoint tree from `backend/app`:

```text
PYTHONPATH=. pytest -m 'not e2e'
```

Result: **2617 passed, 21 failed, 2 warnings, 0 collection errors** (2638 collected).
Against the published 21-ID comparator in
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md`
§7:

- failure IDs added: **∅**;
- failure IDs removed: **∅**.

The 21 failures are the unchanged published set; no phase test or new parser/purity
failure entered the comparator. The L4 tree identity was checkpoint `1590ebe`, with
no application changes after the checkpoint.

## 3. Architecture Graph

One batched `archgraph_apply_changes` call was made after implementation, using the
pre-write revision `613460d0…be52f`:

- applied 4, skipped 0;
- added inferred test node `test-item-economics-domain-purity-guards`;
- added `test-item-economics-domain-purity-guards --verifies--> domain-item-economics-typical-filters`;
- added source links for `_optional_values` and the purity test module.

Post-write graph status is valid with no diagnostics: 196 nodes, 298 edges, one stale
node, four pending reviews, revision
`c912ec9e893f3d23ed86cc2e32c205d6b51ae585a1ffb400fbf2eb48629a4284`. The additions
remain inferred and pending normal human review. No review or maintenance decision was
enacted.

## 4. Write perimeter

### Fix files committed in checkpoint `1590ebe`

- `.archgraph/architecture.yml` — the graph delta above;
- `app/beyo_manager/domain/item_economics/typical_filters.py` — F3 parser only;
- `app/tests/unit/domain/item_economics/test_typical_filters.py` — F1/F2/F4/F5/F7;
- `app/tests/unit/domain/item_economics/test_domain_purity.py` — F6;
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_1.md`;
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`.

### Handoff created after checkpoint

- `docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/implementer/20260822_plan1_fix_round3_handoff.md`.

### Mutation-probe files applied and reverted

- `app/beyo_manager/domain/item_economics/typical_filters.py`.

### Expected tool/session state

- `.archgraph/contexts/` — expected untracked Architecture Graph session context;
  not rebuilt or committed.

The post-handoff `git status --porcelain` is expected to contain only this handoff and
`.archgraph/contexts/`; no other paths were changed after the checkpoint.
