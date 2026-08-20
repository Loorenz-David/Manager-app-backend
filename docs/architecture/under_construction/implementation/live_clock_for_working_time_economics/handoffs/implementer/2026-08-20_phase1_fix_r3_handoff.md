---
plan: 1
role: fix
round: 3
state: IMPLEMENTED
actor: Codex
date: 2026-08-20
---

# Phase 1 fix-cycle r3 handoff

Added the missing C12 rounding-locus proof only. The fixture separates rounding
the live share from rounding the settled-plus-live sum: two batch steps accrue
63 seconds, each receives 31.5 live seconds, and only one carries `settled=1`,
so the expected values are 33 and 32.

## Owner decisions required

**⚠ OWNER DECISIONS REQUIRED (0)**

None.

## Change and verification

- Added `test_c12_rounding_locus_is_share_before_settled_addition` with the
  amended C12 arithmetic and the required one-line docstring.
- Rows C12(a) and C12(b) were left unchanged.
- Focused tests: **23 passed**.
- Ruff: **all checks passed**.
- Final clean whole non-e2e suite: **26 failed, 2459 passed, 1 deselected,
  2 warnings**; the failure IDs are exactly the inherited 26 IDs from master
  plan §6.
- Checkpoint: `bc309e2 CHECKPOINT (not approved): prove live-clock rounding locus`.

## Mutation ledger

All probes were applied at the loader definition site, run against the whole
non-e2e suite, reverted, and hash-verified. `B` means exactly the master plan
§6 baseline set of 26 failure IDs. The restored loader hash after every probe
is:

`6d11b922fbec3031be49adf1313b6d1685bef95659caf81f2b6cb7e918fa82ca`

| Mutation | Result and complete added-ID set |
|---|---|
| M-locus: accumulate raw `contribution.seconds`, return `int(round(settled_seconds + live_by_step.get(step_id, 0)))` | The first run had a count anomaly (**26 failed / 2459 passed / 1 deselected**) although the new locus ID appeared, so it was repeated under the baseline-flake rule. Repeat: **27 failed / 2458 passed / 1 deselected** = `B ∪ {test_live_worked_seconds.py::test_c12_rounding_locus_is_share_before_settled_addition}`. C12(a) and C12(b) stayed green. |
| M-mode: `int(math.floor(x + 0.5))` in place of `int(round(x))` | **27 failed / 2458 passed / 1 deselected** = `B ∪ {test_live_worked_seconds.py::test_c12_half_even_rounding_is_applied_to_each_half_second_share}`. C12(a) and C12(c) stayed green. |
| M-float: raw `contribution.seconds` accumulation alone | **29 failed / 2456 passed / 1 deselected** = `B ∪ {test_live_worked_seconds.py::test_c12_loader_output_values_are_ints, test_live_worked_seconds.py::test_c12_half_even_rounding_is_applied_to_each_half_second_share, test_live_worked_seconds.py::test_c12_rounding_locus_is_share_before_settled_addition}`. |

## Cycle-scoped perimeter

Intended fix files:

- `app/tests/integration/services/queries/item_economics/test_live_worked_seconds.py`
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/plans/plan_1.md` — §7 review log only
- this handoff file

Mutation-probe file, applied temporarily and reverted after each probe:

- `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py` —
  restored byte-identically; no production change shipped.

No `.archgraph` state or master plan tracker was changed. The graph remains
valid and untouched because this cycle changes only test proof and its log.
