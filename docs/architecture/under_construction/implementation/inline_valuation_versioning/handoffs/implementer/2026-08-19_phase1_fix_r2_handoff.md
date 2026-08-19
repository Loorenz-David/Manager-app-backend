---
plan: 1
role: fix
state: IMPLEMENTED
round: 2
date: 2026-08-19
actor: Codex
pipeline: inline_valuation_versioning
---

# Implementer handoff — phase 1, fix round 2

Resolved review-r1 S1: C9's automated guard now covers the `app/` and
`docs/handoff/` perimeters the criterion names. The required reviewer plants both turn the
guard red, the final docs-accuracy suite is green, and the full-suite failure-ID set is
unchanged.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Checkpoint

- Commit: `e9531dcb9f5226c79c65696b9e0116f1f7b4a08e`
- Subject:
  `CHECKPOINT (not approved): inline valuation versioning — C9 guard perimeter`
- Final test-file SHA-256:
  `3af7c8d49e96087ce4357f5a15d7f0df65e8fdda4673b3c49ea76c8fd5e4d9e8`

## What changed

- `_HANDOFFS` now denotes all of `docs/handoff/`; the two named published handoffs resolve
  through its `to_frontend/` child.
- `test_retired_inline_refusal_identity_is_absent_from_live_sources` now scans all `*.py`
  and `*.md` files under `_APP_ROOT` and `_HANDOFFS`, rather than only
  `app/beyo_manager/`, `app/tests/`, and `docs/handoff/to_frontend/`.
- `app/.venv/` is explicitly excluded from the app scan. No application source subtree is
  excluded: top-level modules, `scripts/`, `migrations/`, tests, and the package are all
  inside the guard.
- Plan 1 now records fix r2 as implemented and carries the N1 historical rename mapping:
  `test_c1_inline_birth_writes_valuation_and_handles_exact_auto_statuses` →
  `test_c7_inline_birth_writes_valuation_and_handles_exact_auto_statuses`, with
  `C1-row-*` → `C7-row-*`.

## DECISIONS I HAD TO MAKE

1. Exclude only `app/.venv/`. It is the installed dependency environment, not a live
   application source root, and scanning it would extend C9 into third-party packages.
   Cache and log directories needed no additional exclusion because the guard reads only
   `*.py` and `*.md`; no live source root was narrowed.
2. Keep the r1b C1→C7 rename and record it, as directed. Reverting it would break this
   plan's citations and would not repair the archived phase-8b references.
3. Do not apply Ruff's whole-file formatter. `ruff format --check` reported that this
   legacy module would be reformatted; an exploratory format produced broad unrelated
   churn, which was completely reverted before the final probe, suite, diff, and
   checkpoint. `ruff check` is clean on the final scoped edit.

## Required C9 mutation probe — observed red output

Both temporary plants were applied to the final-form test file and reverted.

1. With both plants present, the focused C9 test exited 1 and reported:

   ```text
   AssertionError: PosixPath('.../backend/app/scripts/_reviewer_probe_c9.py')
   ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM is contained here
   1 failed in 0.18s
   ```

2. After deleting the app plant while leaving the handoff plant present, the same test
   exited 1 and reported:

   ```text
   AssertionError: PosixPath('.../backend/docs/handoff/from_frontend/_reviewer_probe_c9.md')
   ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM is contained here
   1 failed in 0.25s
   ```

3. Both plants were then deleted. The complete docs-accuracy module returned to
   **51 passed**. Repository-root `rg` over `app/` and `docs/handoff/`, excluding only
   `app/.venv/**`, returned no retired-identity hit.

## Verification

- Docs-accuracy module after cleanup: **51 passed**.
- Full suite from `backend/app/`, `PYTHONPATH=. pytest -m 'not e2e' --tb=short`:
  **2346 selected / 2320 passed / 26 failed / 1 deselected**.
- Failure-ID diff against the exact 26-ID r1b list in
  `2026-08-19_phase1_implement_r1b_handoff.md`: added `[]`; removed `[]`.
- Changed-file Ruff lint: passed.
- `git diff --check`: passed.
- Final pre-checkpoint live-root search: no hit.

Two discarded command invocations were not verification evidence: one used `.venv/bin`
from `backend/` instead of `backend/app/`; a second ran from `backend/` and therefore did
not load `app/.env`. The authoritative focused and full runs above used the master plan's
required `backend/app/` working directory.

## Full write perimeter (generated from Git)

Checkpoint paths from `git show --format= --name-only e9531dc`:

1. `app/tests/unit/docs/test_item_economics_handoff_accuracy.py`
2. `docs/architecture/under_construction/implementation/inline_valuation_versioning/plans/plan_1.md`

Post-checkpoint queue artifact from `git status --short`:

3. `docs/architecture/under_construction/implementation/inline_valuation_versioning/handoffs/implementer/2026-08-19_phase1_fix_r2_handoff.md`

No production file, master tracker, prompt, reviewer artifact, or Architecture Graph state
was changed. The master tracker remains coordinator-owned because the fix prompt's explicit
cycle perimeter excludes it.

## Mutation-probe files touched and reverted (separate from fix changes)

1. `app/scripts/_reviewer_probe_c9.py` — created, produced the app-root red failure, deleted.
2. `docs/handoff/from_frontend/_reviewer_probe_c9.md` — created, produced the handoff-root
   red failure, deleted.

Both paths are absent from the final tree. Tool-recorded state delta: none. Architecture
Graph delta: none, as explicitly required by the fix prompt.

## Coordinator follow-up

- Consume this handoff and move the master tracker from fix-r2 prompt-ready to the next
  review state.
- Compile a delta-scoped re-review prompt against checkpoint `e9531dc`.
