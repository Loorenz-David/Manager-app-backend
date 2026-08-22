---
plan: plan_1
role: implementer
round: 2
state: IMPLEMENTED
verdict: IMPLEMENTED
date: 2026-08-22
actor: Codex
---

# Plan 1 fix round 2 handoff

The coordinator's four criteria-coverage gaps are closed. The test suite now contains
the missing C7, C10, and C14 assertions; no production logic changed. The checkpoint
is `8feae38` (`CHECKPOINT (not approved): plan 1 fix round 2 coverage`).

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## 1. Fix ledger

| Finding | Change | Result |
|---|---|---|
| F1 | Added C7 row (i) with narrowed `(3, None)`, section `(4, 800)`, `BROADEN_TO_SECTION` → `insufficient_sample` / `None` / `4`. Amended the plan's C7 row (i) to the same asymmetric fixture. | Both named mutations reddened the row: returning `narrowed_sample_count` changed `4 → 3`; returning section seconds changed `None → 800`. |
| F2 | Added C14 row (c) both-bounds `(60, 80)`, row (h)'s `can_have_upholstery=True` half, and row (m) `designers` → `frozenset({"dsg_a", "dsg_b"})`. | All three enumerated parser omissions are now asserted in the existing parser test. |
| F3 | Extended the C10 ghost-row assertion to `typical_worker_seconds is None`, both evidence seconds `None`, both evidence counts `0`, basis, sample count, and participation. | The `_zero_evidence` mutation to `SectionTypicalEvidence(section_id, 0, 0, 0, 0)` reddened: selected seconds changed `None → 0`. |
| F4 | Corrected the round-2 record of the two measured handoff claims. | Snapshot final byte measured `0x65`; forbidden-term grep has one pre-existing out-of-scope hit, `serializers.py:351` `config_fingerprint`. |
| F5 | No guard added. | Phase 1 has no production caller yet; the inherited contract is `participating_section_ids ⊆ section_ids`, which phases 4 and 5 must preserve when wiring callers. No violating path was found. |

Production file `app/beyo_manager/domain/item_economics/typical_filters.py` was not
changed by the fix. The `_median = median` compatibility alias remains as directed;
its removal stays routed to phase 5.

## 2. Named mutation evidence

All three probes used L1 whole-file scope; none used `-k`. Each probe was applied to the
named production definition, the full test file was run, and the mutation was reverted
before the next probe. The probe tree content was the eventual checkpoint tree
`8feae38`; the production file is absent from that checkpoint's diff.

### F1(a) sample-count source

- Hypothesis: the non-narrowing insufficient branch must report
  `section_sample_count`.
- Site: `app/beyo_manager/domain/item_economics/typical_filters.py`,
  `resolve_section_typical` definition; replaced that return with
  `narrowed_sample_count`.
- Scope/command: L1 whole file —
  `PYTHONPATH=. .venv/bin/pytest -n 0 tests/unit/domain/item_economics/test_typical_filters.py`
  from `backend/app/`.
- Contract: 31 collected, 31 passed; row (i) sample count `4`.
- Mutation: 30 passed, 1 failed; row (i) sample count `3`.
- Reverted: yes; `typical_filters.py` is not a fix change.

### F1(b) insufficient seconds disclosure

- Hypothesis: the non-narrowing insufficient branch must return seconds `None`.
- Site: `app/beyo_manager/domain/item_economics/typical_filters.py`,
  `resolve_section_typical` definition; replaced `None` with
  `section_typical_worker_seconds`.
- Scope/command: same L1 whole-file command as F1(a).
- Contract: 31 collected, 31 passed; row (i) seconds `None`.
- Mutation: 30 passed, 1 failed; row (i) seconds changed to `800`.
- Reverted: yes; `typical_filters.py` is not a fix change.

### F3 ghost-evidence seconds

- Hypothesis: a materialized insufficient ghost row must not disclose either seconds
  value.
- Site: `app/beyo_manager/domain/item_economics/typical_filters.py`, `_zero_evidence`
  definition; replaced `SectionTypicalEvidence(section_id, None, 0, None, 0)` with
  `SectionTypicalEvidence(section_id, 0, 0, 0, 0)`.
- Scope/command: same L1 whole-file command as F1(a).
- Contract: 31 collected, 31 passed; selected and evidence seconds are `None`.
- Mutation: 30 passed, 1 failed; selected ghost seconds changed to `0`.
- Reverted: yes; `typical_filters.py` is not a fix change.

## 3. Test evidence

Focused phase perimeter, after all probes were reverted:

```text
PYTHONPATH=. .venv/bin/pytest -n 0 tests/unit/domain/item_economics/test_typical_filters.py tests/unit/domain/item_economics/test_participating_sections.py tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py tests/unit/domain/item_economics/test_budget_division.py
```

Result: **50 passed**. The extra test over round 1 is the newly added C7 row.

The one authoritative L4 stamp, taken on the tree handed over:

```text
PYTHONPATH=. pytest -m 'not e2e'
```

Working directory: `backend/app/`. Six xdist workers; Redis reachable. Result:
**2609 passed, 21 failed, 2 warnings, 0 collection errors**, 2630 collected. Against
the published 21-ID comparator in
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7:

- failure IDs added: **∅**;
- failure IDs removed: **∅**.

The checkpoint tree identity is `8feae38`; after the checkpoint, the only pre-handoff
worktree status entry was the expected untracked `.archgraph/contexts/` session context.

## 4. Measured handoff corrections

- `app/tests/unit/services/queries/working_sections/snapshots/typical_times_no_spec_sql.txt`
  has no trailing newline; its last byte measured **`0x65`** (`e`, the end of
  `working_sections.name`).
- From the repository root, the requested term set
  `hashlib|sha1|sha256|md5|fingerprint|digest` over
  `app/beyo_manager/domain/item_economics/` returned exactly one hit:
  `app/beyo_manager/domain/item_economics/serializers.py:351` —
  `config_fingerprint`. It is a pre-existing price-scenario configuration fingerprint,
  unrelated to typical-filter spec identity. Therefore the narrower claim remains true:
  this pipeline introduces no spec hash, digest, or fingerprint.

## 5. Architecture Graph

Start status was valid and initialized: 195 nodes, 297 edges, revision
`613460d0edc09f2416ab6b44d40fd957e3f69930f4c4750d6610fa62391be52f`, one stale node,
two pending reviews, and no diagnostics. The existing pending inferred node
`domain-item-economics-typical-filters` already represents this pure domain boundary;
the fix is test/document coverage only. No graph mutation was performed: applied `0`,
skipped `0`. No review or maintenance decision was enacted.

## 6. Write perimeter

### Fix files changed and committed

- `app/tests/unit/domain/item_economics/test_typical_filters.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_1.md`

### Handoff file created after the checkpoint

- `docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/implementer/20260822_plan1_fix_round2_handoff.md`

### Mutation-probe files, applied and reverted, separate from fix changes

- `app/beyo_manager/domain/item_economics/typical_filters.py`

### Tool-recorded / expected worktree state

- `.archgraph/contexts/` — expected untracked Architecture Graph session context;
  not rebuilt or committed.

No other paths were changed. Checkpoint commit: `8feae38`.
