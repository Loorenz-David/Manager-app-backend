# Plan Archives

Completed work, moved out of `under_construction/` so that folder holds only what is
live. **Nothing here is in flight.** Each entry keeps its full pipeline folder — master
plan, plans, planning, and `archive/plan_<n>/` session rows — so the provenance of every
decision survives the move.

`TEMPLATE_ARCHIVE_RECORD.md` describes the older single-file convention
(`PLAN_<slug>_<date>.md` + a separate archive record). Pipeline projects archive as whole
folders instead; the master plan's own §3 tracker is the archive record.

## Archived 2026-08-22

| Project | Closed | What it shipped | Where its durable output lives |
|---|---|---|---|
| `live_clock_for_working_time_economics` | 2026-08-22 (gate `4063fc6`, merged `57d8c25`) | Live worked-seconds basis on production-time, budget-status (both faces) and budget-allocations; frozen blocks derive their percent from the stored result alone | **The published baseline for `narrow_typical_work_times` D23 is in `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7**, not in this folder |
| `test_isolation_and_xdist` | 2026-08-22 (merge `0aae85e`) | Per-process disposable test databases + six xdist workers; suite 132 s → 51 s | The runner and baseline facts are folded into that same handoff §7; the enumerated 21 IDs are in its own `archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` |
| `inline_valuation_versioning` | 2026-08-19 | Task creation re-prices an already-priced item instead of refusing it (D17 inherit, D18 currency, zero-write no-op) | Behaviour is in the code and in `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` §9.1 |
| `simple_production_budget_division` | 2026-08-17 | E1 typical-times + E2 budget-allocations; 4 review rounds, 0 production defects | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md` |
| `simple_valuation_editor` | 2026-08-19 (all five phases) | The price-scenario read endpoint | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_price_scenario_20260819.md`. **Its `master_plan.md` §5 is the shared earned-rules corpus (~30 rules, six pipelines) that later master plans adopt by reference — it is cited as doctrine, not only as history** |

### Two notes for whoever reads these later

**Header lines were corrected at archive time, not rewritten.** `live_clock`'s said
`IN PROGRESS` and `simple_valuation_editor`'s said "closeout ritual and graph remain";
both were stale convenience lines that no gate had refreshed. Each now says so explicitly
above its corrected text. **§3's tracker, never the header, is the authority on what
happened.**

**Paths inside archived documents were not rewritten.** A citation written as
`under_construction/implementation/<project>/…` inside one of these folders resolves under
`archives/<project>/…` by convention — the same rule that governs `archive/plan_<n>/`
inside each pipeline. Historical references are evidence of what a session actually saw;
rewriting them destroys that. Only one document was repointed: the
2026-08-22 frontend handoff, because it had not yet been delivered and would otherwise
have shipped thirteen dead pointers to the receiving team.

## Still live in `under_construction/implementation/`

`archGraph_mapping_mantainance` is **not** archived despite being older than most of the
above: it is a standing register of architecture-graph tooling findings, **one of which is
still open**, and several master plans name it as required reading before any
`archgraph_repair_anchors` call. `item_cost_calculation` cites it by relative path.
It stays until its open finding closes.
