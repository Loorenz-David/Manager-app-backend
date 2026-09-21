# Plan 14 — Frontend handoff and domain docs (thin; refine at prompt time)

```
state: NOT_STARTED
phase: 14 of 15
depends_on: 13A, 11, 10 (APPROVED)   — 13A implies 13, 9, 7
projection: waivable (documents; no mechanism)
complex: no
```

## 1. Goal

Publish the local API to the frontend team and write the domain documents the repo contract
requires, from the **shipped** routers and serializers — including the sixth assignment state
`resolved_early` (what it means on the board: Scanner processed the item before the task was
`ready`; the trace of a forgotten step) and the refusal `already_processed_by_scanner`, and the
three Scanner webhooks in `api.md`. **Not in this phase:** any code change; any edit to the Scanner
v1 or v2 file (nothing is owed to Scanner — intention §18, 2026-09-19 revisions of rounds 8 and 9).

## 2. Read first

1. `master_plan.md` §6.1 (the state enum), §6.4, §6.6, §6.7, §6.9, §9 rules 11, 15.
2. Intention §9, §9A–§9E (what the frontend must know: roles, the override retry contract, the two
   structured errors, event names and payloads, the response shapes), §11, §14B B3 (`is_stock_assignment`
   is not surfaced), §12 (what is deferred: no history read endpoint, no pagination, no local row
   creation), **§14E** (the delete webhook: what a user sees — a row and its assignments vanish when
   Scanner changes or removes a rule, and are re-added by hand; E10), **§14F F1, F3, F9, F10, P45**
   (the state, that the task is untouched, the creation refusal, the traceability surface; the
   deferred "forgotten items" view).
3. The shipped code: `bm/routers/api_v1/stock_report.py`, `bm/domain/stock_report/serializers.py`,
   `bm/errors/stock_report.py`, `bm/services/commands/stock_report/requests/__init__.py`.
4. `architecture/23_documentation.md`, `25_soft_delete.md` ("document the cascade strategy in
   `states.md`"); an existing handoff for shape: the newest file under `docs/handoff/to_frontend/`;
   `app/tests/unit/docs/test_item_economics_docs.py` (the docs-accuracy guard shape).

## 3. Dependencies

Phases 10, 11, 13A APPROVED (every route, error, state and event exists).

## 4. Files expected to change

New: `docs/handoff/to_frontend/STOCK_REPORT_API_v1_<YYYYMMDD>.md`, `docs/domains/stock_report/api.md`,
`docs/domains/stock_report/states.md`, `app/tests/unit/docs/test_stock_report_docs.py`.

## 5. Tasks (refine at prompt time)

1. `api.md`: every route of master plan §6.6 with method, path, roles, request body, response body,
   error identities/codes; the **three** webhooks (demand, processed, delete) with a pointer to the
   Scanner v2 file (`docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v2_20260919.md`).
2. `states.md`: the assignment state machine (plan 4 task 1's six-state table — MC-1 as amended by
   §14F), which actor performs each entry (the sync, the Scanner processed webhook for `resolved`
   and `resolved_early`), the cascade strategy for row deletion by a user **and by Scanner (13A)**,
   task deletion, PRIMARY unlink and item deletion (MC-14, MC-16), the soft-delete predicates.
3. The frontend handoff: the routes, roles, payload shapes **with nullability per field**, the
   override retry contract (MC-13), the two structured errors **with the closed reason vocabulary
   of `stock_assignment_refused` (master plan §6.4), `already_processed_by_scanner` explained in
   product words**, the event names and payloads (the `state` values an assignment event can carry
   — all six), the meaning of `resolved_early` for the board (units already out of the counters,
   task still running, the assignment kept as the trace), that a Scanner rule change deletes a row
   with its assignments (E10: users re-add by hand), what is not built (history read, pagination,
   local row creation, `is_stock_assignment` not surfaced, no "forgotten items" view — P45), and the
   consistency/repair endpoints for admin tooling.
4. The docs guard: parses the router module's routes and role lists and asserts each appears in
   `api.md`; asserts every event name in `_events.py` appears in the handoff; asserts every error
   class in `bm/errors/stock_report.py` and every registered identity appears in both; asserts
   every member of `StockTaskAssignmentStateEnum` appears in `states.md` and in the handoff.
5. Run `pytest tests/unit/docs/` before and after writing.

## 6. Criteria

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | `test_stock_report_docs.py` over `api.md` | every `(method, path, roles)` the router declares is present — the three webhook routes included; a route removed from the doc reddens | delete one route line from `api.md` | §6.6, M9 |
| C1(b) | over the handoff | every event name built in `_events.py` appears | delete one | MC-19 |
| C1(c) | over both | every error class and registered identity of `bm/errors/stock_report.py` / master plan §6.4 appears | delete one | MC-13, §6.4 |
| C1(d) | over `states.md` and the handoff | every `StockTaskAssignmentStateEnum.value` appears in both (six, `resolved_early` included) | delete `resolved_early` from `states.md` | §14F F10, §6.1 |
| C2(a) | the handoff's payload tables | every nullable field of the three serializers is annotated nullable and names the condition that produces the null (reviewer reads the serializers) | — (review) | §9B, master plan §9 rule 15 |

## 7. Notes

- Sizing: 5 criterion rows in 2 criteria; `complex: no`. Deliberately thin;
  the coordinator refines the tasks at prompt time from the shipped code. (Counts re-derived by
  script after the round-8/9 fold; see the delta handoff.)
- Rounds 8–9 (2026-09-19): depends on 13A (the third webhook must exist before `api.md` lists it);
  C1(d) added; tasks 1–4 name the new state, the new reason and the delete webhook.
- The guard's roots are `docs/domains/stock_report/` and the one handoff file; state the roots in
  the test (verification-scope rule).

**Added by the batch D projection + fold, 2026-09-21 (round 0). Nothing below changes a criterion outcome.**

- **Two frontend handoffs for this project are already published**, both under
  `docs/architecture/under_construction/implementation/stock_report/handoffs/to_frontend/`:
  `HANDOFF_TO_FRONTEND_stock_report_api_20260921.md` (all batch-D endpoints, tagged PROVISIONAL,
  and it explicitly promises "the backend derives the nullability contract from shipped code in
  phase 14") and `HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md` (the ratified
  preview contract, **correct as written**, `item_category_id` required — no v3). §4 names a third
  file in a **different folder** (`docs/handoff/to_frontend/`) under a **different convention**
  (`STOCK_REPORT_API_v1_<date>.md`), which would leave three live documents and supersede two
  published contracts without saying so. Reconciling the file name, the folder and the
  supersession sentence is a plan/owner call before the prompt compiles.
- **The match-preview endpoint is missing from this plan's tasks.** §2 cites neither §14G nor
  MC-21, and tasks 1 and 3 never name `POST /items/{client_id}/match-preview` — the only phase-8A
  surface the frontend has to build against. C1(a) would catch the route mechanically (it parses
  the router), but nothing makes tasks 1/3 document its request body, its check vocabulary or the
  required `item_category_id`.
- **C1(b)'s stated root cannot see four of the six event names.** `_events.py` contains one
  literal (`stock_report_item:updated`) plus the f-string `f"stock_task_assignment:{kind}"`;
  `stock_report_item:created` is built in `apply_stock_demand.py:271`, and
  `stock_report_item:deleted` will be built wherever phase 13 puts it. A guard rooted in
  `_events.py` alone would assert one name and pass. The root has to be every `event_name=` site
  under `bm/services/commands/stock_report/` plus the three `kind` values — or master plan §6.7's
  list. Changing a row's root is an owner card.
- **L-38.** Before the docs guard is called armed, grep the whole repo — tests included — for how
  routes, roles and event names are actually written, and plant that spelling. The router declares
  roles as `Depends(require_roles([ADMIN, MANAGER, WORKER]))` with the constants imported by name,
  not as string literals; a guard that greps for `"admin"` finds nothing and passes.
- **No register lesson names phase 14, and that is an oversight, not a judgement.** L-15 (a
  `sorted()` over a `set` needs ≥ 3 elements or the assertion is the guard), L-26 (an absence
  instrument deserves one positive observation) and L-32 (name the property, not the statement)
  all bear on a docs guard whose whole job is an absence claim. Charter rule 15 applies in full:
  each of C1(a)–C1(d) ships with the planted deletion observed red, which the cells already name.

## 8. Review log

(empty)
