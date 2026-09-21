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
   deferred "forgotten items" view), **§14G and MC-21** (the match-preview endpoint: what the
   preview answers, that it runs the same acceptability decision as creation, and that
   `item_category_id` is **required** — owner ruling, round 3, 2026-09-21).
3. The shipped code: `bm/routers/api_v1/stock_report.py`, `bm/domain/stock_report/serializers.py`,
   `bm/errors/stock_report.py`, `bm/services/commands/stock_report/requests/__init__.py`,
   `bm/domain/stock_report/assignment_checks.py` and
   `bm/services/queries/stock_report/preview_stock_task_assignment_match.py` (phase 8A).
4. `architecture/23_documentation.md`, `25_soft_delete.md` ("document the cascade strategy in
   `states.md`"); `app/tests/unit/docs/test_item_economics_docs.py` (the docs-accuracy guard shape).
5. **The two frontend documents already published for this project**, both under
   `handoffs/to_frontend/` in this project folder — read both before writing a line:
   `HANDOFF_TO_FRONTEND_stock_report_api_20260921.md` (every batch-D endpoint, tagged PROVISIONAL,
   and it promises in §0 and §8 that the nullability contract arrives in **this** phase) and
   `HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md` (the **ratified** preview
   contract — correct as written, `item_category_id` required, and the source of truth for that
   endpoint's semantics).

## 3. Dependencies

Phases 10, 11, 13A APPROVED (every route, error, state and event exists).

## 4. Files expected to change

New: `docs/architecture/under_construction/implementation/stock_report/handoffs/to_frontend/HANDOFF_TO_FRONTEND_stock_report_api_<YYYYMMDD>.md`
(a **new** file with a **new date**, in the folder the project's two published handoffs already
live in and under their naming scheme), `docs/domains/stock_report/api.md`,
`docs/domains/stock_report/states.md`, `app/tests/unit/docs/test_stock_report_docs.py`.

Moved (content **not** edited): the superseded handoffs go to
`…/handoffs/to_frontend/archived/`.

**Owner card 7, ruled 2026-09-21 — the supersession protocol, and it is not optional.**
A published handoff is **never rewritten in place**; an in-place edit is what cost the frontend
four days on a previous project, and the guard against it is positional, not editorial. So:
- the new handoff is a **new file with a new date** in the **same folder** under the **same**
  `HANDOFF_TO_FRONTEND_stock_report_*` name — never an edit to, and never a reuse of, an existing
  filename;
- its frontmatter carries an explicit **`supersedes:`** key naming **every** document it replaces
  (at minimum `HANDOFF_TO_FRONTEND_stock_report_api_20260921.md`);
- the superseded files are **moved** into `archived/` — not deleted, not edited, so their content
  stays recoverable and the record of what the frontend was told still reads true;
- its **first section** states plainly which document is current and that the others are
  historical.
- **`…_match_preview_v2_20260921.md` is NOT superseded and is NOT moved.** It is the ratified
  contract for that endpoint and it is correct as written; there is **no v3**. The new handoff
  documents match-preview and points at v2 for that endpoint's semantics.

## 5. Tasks (refine at prompt time)

1. `api.md`: every route of master plan §6.6 with method, path, roles, request body, response body,
   error identities/codes — **thirteen routes, the phase-8A `POST /items/{client_id}/match-preview`
   included** (owner card 7, 2026-09-21: it was missing from this plan, and it is the one board
   endpoint the frontend can already build against); the **three** webhooks (demand, processed,
   delete) with a pointer to the Scanner v2 file
   (`docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v2_20260919.md`).
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
   consistency/repair endpoints for admin tooling. **Plus, from owner card 7 (2026-09-21):** a
   first section naming this document as the current one and the archived ones as historical, the
   `supersedes:` frontmatter key of §4, and **the match-preview endpoint** — its request body with
   `item_category_id` **required** (owner ruling round 3; the preview is never more permissive than
   item creation), its check vocabulary, what `pass_by_construction` and `not_evaluated` mean for a
   candidate item that does not exist yet, and a pointer to the ratified v2 preview handoff as the
   source of truth for that endpoint's semantics.
4. The docs guard: parses the router module's routes and role lists and asserts each appears in
   `api.md`; asserts every error class in `bm/errors/stock_report.py` and every registered
   identity appears in both; asserts every member of `StockTaskAssignmentStateEnum` appears in
   `states.md` and in the handoff. **Event names (owner card 6, 2026-09-21):** the roots are
   **master plan §6.7's list** and every `event_name=` site under
   `bm/services/commands/stock_report/` — including the three values of the
   `stock_task_assignment:{kind}` template — and the guard fails **in both directions** (a name in
   the code missing from the handoff, and a name in the handoff that no site builds). Rooting it in
   `_events.py` alone is the defect the card forbids: that module holds one literal name,
   `stock_report_item:created` is built at `apply_stock_demand.py:271`, and
   `stock_report_item:deleted` wherever phase 13 puts it. State the roots in the test
   (verification-scope rule).
5. Run `pytest tests/unit/docs/` before and after writing.

## 6. Criteria

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | `test_stock_report_docs.py` over `api.md` | every `(method, path, roles)` the router declares is present — the three webhook routes included; a route removed from the doc reddens | delete one route line from `api.md` | §6.6, M9 |
| C1(b) | over the handoff, with the guard's roots stated in the test | every event name in **master plan §6.7** and every name constructed at an `event_name=` site under `bm/services/commands/stock_report/` (the `stock_task_assignment:{kind}` template's three values included) appears in the handoff; a name present in the code and absent from the handoff reddens, **and so does the reverse** | two mutants, **both runs recorded** (one per direction, L-13): (i) delete one event name from the handoff → red; (ii) add a name to §6.7 / a new `event_name=` site that the handoff does not carry → red. Rooting the guard in `_events.py` alone is itself the defect this row now forbids: that module holds one literal name, `stock_report_item:created` is built at `apply_stock_demand.py:271` and `stock_report_item:deleted` wherever phase 13 puts it | MC-19 |
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

- **Supersession — APPLIED, owner card 7 ruled 2026-09-21 (with a correction this plan now
  carries).** Two frontend documents for this project are already published, both under
  `handoffs/to_frontend/` in this project folder. The plan previously named a third file in a
  different folder under a different convention, which would have left three live documents with
  nothing saying which wins. The ruling is **supersede — but never in place**: a new file with a
  new date, same folder, same name scheme, a `supersedes:` frontmatter key, the superseded files
  **moved** to `archived/` unedited, and a first section naming the current document. §4 carries
  the protocol. The match-preview **v2** handoff is **not** superseded and **not** moved: it is
  the ratified contract for that endpoint, `item_category_id` is required, and there is no v3.
- **The match-preview endpoint — APPLIED, owner card 7.** §2 now cites §14G/MC-21 and the two
  shipped 8A modules; tasks 1 and 3 now name the route, its required `item_category_id` and its
  check vocabulary. C1(a) catches the route mechanically because it parses the router; the tasks
  are what make its *contract* reach the document.
- **C1(b)'s root — APPLIED, owner card 6 ruled 2026-09-21.** `_events.py` contains one literal
  (`stock_report_item:updated`) plus the f-string `f"stock_task_assignment:{kind}"`;
  `stock_report_item:created` is built in `apply_stock_demand.py:271`, and
  `stock_report_item:deleted` will be built wherever phase 13 puts it — so a guard rooted there
  asserts one name and passes. The row and task 4 now root it in master plan §6.7 **plus** every
  `event_name=` site under `bm/services/commands/stock_report/`, failing in both directions.
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


---

## Review log — 2026-09-21: the frontend handoff was written early; task 3 becomes a re-verification

**The owner asked for the frontend document before batch D ran**, so the frontend could implement
against a reliable contract and the morning's wiring would be a pointer move rather than a
negotiation. It is published:

`handoffs/to_frontend/HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md`

Card 7's protocol was followed exactly: a **new** dated file in this project's own
`handoffs/to_frontend/`, a `supersedes:` key, and the two superseded documents **moved** to
`handoffs/to_frontend/archived/` — moved, not edited, not deleted. **`…match_preview_v2…` was not
superseded and not archived**; it remains the ratified authority for that endpoint's semantics and
the new document points at it. No v3 exists.

**Every line is tagged VERIFIED or SPECIFIED.** VERIFIED = read out of shipping code on
2026-09-21, field by field, by a dedicated sweep. SPECIFIED = pinned by a criterion row in plans
12/13/13A, not yet built — **six of the thirteen routes**. The document states the guarantee
plainly: build against a SPECIFIED shape, and if the code ships differently that is a **backend
defect**, not a contract change the frontend absorbs. That is the strongest honest promise
available for unwritten code, and the two tiers are never blurred.

**Task 3 therefore changes from *author* to *re-verify and re-issue*.** When this phase runs, the
six SPECIFIED routes will have shipped. The job is to re-read each against the code, flip its tag
to VERIFIED, correct anything that moved, and — **only if something moved** — publish a new dated
file superseding this one, moving it to `archived/`. If nothing moved, say so in the handoff and
leave the published file alone. **Never edit it in place.**

This is strictly better than authoring it here: the document now gets a verification pass at the
end of the batch instead of being born unverified, and the frontend gets to start today.

**Tasks 1, 2 and 4 are unchanged**, and C1(b)'s widened root (owner card 6) now has a real target
to guard — the published file — rather than one that does not exist yet.
