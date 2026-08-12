# node:analytics-recompute-step-time-totals — anchor drift (D-3)

## Finding (reporter: mechanism-inventory gate session, 2026-08-11)

- **Observed:** node evidence cites
  `app/beyo_manager/services/tasks/analytics/process_step_transition.py:138-211`
  for symbol `_recompute_step_time_totals`; the symbol sits at `:161-234`.
  Same file, same symbol, semantics agree — anchors only.
- **Recorded in:** the gate handoff
  (`item_cost_calculation/archive/…/2026-08-11_mechanism-inventory_r1_handoff.md`, D-3)
  and master plan §8. **Process note:** the reporter declared it "filed per the
  archgraph-discrepancies protocol" but never wrote the `open/` ledger file — this
  resolved record was created directly by the fixer from the handoff's observation.
  (Lesson for reporter sessions: "filed" means a file in `open/`, not a handoff row.)
- Independently re-observed by the item-cost planner (2026-08-12) and the phase-1
  projection session (2026-08-12) — same drift, same conclusion.

## Fixer verification (coordinator session, 2026-08-12)

Read the cited lines BEFORE the stored claim (anti-pattern rule). Own reading:
`_recompute_step_time_totals` (161–234) derives per-user min/max windows over the
step's time-bearing records (189–197), re-runs the concurrency sweep via
`compute_record_contributions` (207–210), and absolutely SETs
`total_*_seconds`/`_count` (221–223), `inaccurate_*` (224) and `total_cost_minor`
from working+paused seconds × salary rate (226–233) — idempotent by construction.
Stored claim and `inferenceReason` (vestigial `increment_step_time_metrics` has no
callers — consistent with the item-cost research census §2.6-5) verified exact.
Disagreement with reporter: none.

## Outcome

- **Decision applied:** `promote` **with anchors** (138-211 → 161-234), origin
  `ai_inferred` → `human_confirmed`. Owner authorization: David, coordinator
  session 2026-08-12 ("yes you can close the D-3 anchor drift").
- **Audit record:** `.archgraph/reviews/2026-08-12T10-23-51-250Z--45ed55.yml`
- **Graph revision:** `b0702c3c…` → `810325a0…`; pending reviews 244 → 243.
- **Not included (scope kept to the filed finding):** the node's three outgoing
  edges (`writes_to table-task-step`, `calls src-compute-record-contributions`,
  `governed_by decision-recompute-not-increment`) carry the same stale `138-211`
  span and remain pending — queued for the item-cost phase-8/9 graph-delta
  adjudication batch (standing owner authorization of 2026-08-12).
