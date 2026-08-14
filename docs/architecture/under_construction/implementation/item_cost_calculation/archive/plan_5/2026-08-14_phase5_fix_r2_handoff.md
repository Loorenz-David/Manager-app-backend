---
plan: phase 5 (valuation surface)
role: fix
state: IMPLEMENTED
date: 2026-08-14
actor: Codex
---

# Phase 5 fix r2 handoff

S1 and the N3 ride-along are resolved. The L15 structural guard now quantifies
over every module in `module_sources`: each in-scope
`item_major_category_snapshot` occurrence must be the registered
`resolve_major_category(item.item_major_category_snapshot)` argument, with
`unmediated == {}`. The non-generalizing `ItemMajorCategoryEnum(` assertion was
removed. The currency mismatch parametrization now documents the clause each
equal-pair id arbitrates.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

## Verification

- `PYTHONPATH=. pytest -q tests/unit/domain/item_economics/test_configuration.py`:
  **9 passed**.
- Focused selector (the phase-5 selector from the re-review handoff): **363
  passed**.
- Full `PYTHONPATH=. pytest -m 'not e2e'`: **1968 passed / 23 failed / 1
  deselected / 2 warnings**, collection 1992 total / 1991 selected. The 23
  failures are byte-identical to the established phase-1 baseline; no phase-5
  test failed.
- Ruff on `app/tests/unit/domain/item_economics/test_configuration.py`:
  passed. `git diff --check`: passed.
- Alembic: `5caae620088c (head)`.

## Mutation ledger

The three governing mutant hashes and restored hashes are copied from the
re-review correction declaration. Each named mutation reddened
`test_item_major_category_snapshot_is_read_only_by_the_registered_resolver`
and was reverted before closeout.

| Mutation | Mutant sha256 | Restored sha256 | Observed red node |
|---|---|---|---|
| M4a — inline preview chain in `set_item_valuation._load_preview_inputs` | `df1f79b3a23081cf21cc785f6660999fdc3648d786fd074167bcb074cbfb7c88` | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | `test_item_major_category_snapshot_is_read_only_by_the_registered_resolver` |
| M4b — second unmediated reader in the same module | `e1ca06250fc7d8924e6e2d935bda00b9a03ece4bafdfee117afd013b88d3c6c0` | `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` | same |
| M4c — snapshot-classifying helper in `delete_item_valuation.py` | `88c9f5aa59adca10e948fdc2c29acb12b77dce7eb491b615e73ff853d5f628ae` | `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1` | same |

Local equivalent probes were also applied and reverted in the main worktree;
their observed mutant hashes were, respectively,
`e818fa2b74af93c79e1e0709c93e5281d17f3fb1ff5ffb1fddf2306a80fcfad7`,
`c4abb17d4135df01e9e1029fc01a7ca905a66ff0b382570762fa41b8ff975332`, and
`ead1b99984188576209f01abbf97603d93f1e07562788742532be009ef0dd65f`; all
reddened the guard. The final production files match the governing restored
hashes exactly.

## Write perimeter

- Code/test changed: `app/tests/unit/domain/item_economics/test_configuration.py`
  only; final sha256
  `da1c4e28144e1466887b542f9ae078679c8f400dfbae1bd97776fd97df319a87`.
- Documents changed: the phase-5 tracker row in `master_plan.md` and the
  append-only Review log in `plans/phase_5_valuation_surface.md`; this handoff
  was deposited after the checkpoint.
- Mutation-probe files touched and reverted: `set_item_valuation.py`,
  `delete_item_valuation.py`. Their final hashes are
  `05587c2b331a341df9234d670507320dc63d4859966fa53ada68017e7655bda8` and
  `ab9aebbe6c5047264f051510ba4961f075e6cf8daf8504db6922274214bb3fc1`.
- No production code change; no disposable files; no database mutation was
  retained. The configured DB remains at head.

## Architecture Graph

Read-only orientation and closeout: revision
`b5e6fe094caee2191414a297bb1ab63507ebda8ee4ee54c26cc612a5d940fc94`, 153
nodes / 195 edges / 12 pending reviews, zero delta. The test-only change adds
no independently named architecture.

Checkpoint: `e71b5b4` — `CHECKPOINT (not approved): item-cost phase 5 fix r2 —
L15 guard quantified`.

