# Plan 8A — Assignment match preview: one acceptability evaluation, two callers

```
state: NOT_STARTED
phase: 8A (extends phase 8; runs after batch C1 APPROVED and before batch C2 = 9 → 10)
depends_on: 8 (VERIFIED, batch C1 APPROVED at `798fc69`)
projection: mandatory (the acceptability decision is a silent-failure mechanism; charter rule 6)
flow: reduced, by owner ruling 2026-09-21 — projection → implement → orchestrator review by hand.
      No tester session and no independent reviewer: the implementer sites and arms every
      deliberate `—` mutation cell itself (master plan §3B, *Mutation cells*, class 2).
complex: no — read-only surface plus a mechanical extraction; no locks, no writes, no concurrency
```

## 1. Goal

Ship intention **§14G**: `POST /api/v1/stock-report/items/{client_id}/match-preview`, the read-only
answer to *"would this (item, task, row) triple be accepted right now?"*, and the **MC-21**
extraction it rests on — the acceptability decision of MC-13 phase 3 lifted out of
`create_stock_task_assignments.py` into one implementation that returns **every** check's result in
MC-13's order, of which `create_stock_task_assignments` consumes the first failure and the preview
consumes the whole list.

**Not in this phase:** the reverse query ("which rows does this item match?" — dropped by the owner,
§14G last paragraph); any change to what MC-13 refuses, to the matcher (MC-12), to the creation
writes, or to any other command; batching the preview (single, by owner ruling); the frontend
contract (phase 14).

## ⚠ OWNER DECISIONS REQUIRED (3)

Three places where §14G does not settle an outcome. None is resolved in this plan; each blocks a
criterion row named in §7, and the phase is not dispatchable until all three are ruled.

**Card 1 — what does the preview say when there is no item yet?**
*Question:* When no live item matches the article number (or neither identifier was sent), do the
four item-dependent checks report `not_evaluated`, leaving `can_proceed` true and `refusal_reason`
null — or do they fail with `item_not_found`?
*Story:* A worker is about to build a dining chair for a board row. He opens the preview first,
precisely so the board can tell him whether the category and the properties he is planning will be
accepted before he makes anything. If the answer comes back "cannot proceed — item not found", the
board refuses the one case this endpoint was built for, and he learns nothing until he has already
made a chair he cannot use.
*Branches:* **not evaluated** — the preview answers "nothing stands in your way except these
property problems", which is the intended use · **failed** — the preview always says no until the
item exists, and the feature loses its reason to exist · **mixed** — not evaluated, but the
reported reason still reads `item_not_found`, which a frontend will render as a refusal anyway.
*Recommendation:* not evaluated, with `can_proceed` true — §14G calls this "the creation case this
endpoint exists for".
*On silence:* the gate holds. The row is not authored and the phase is not dispatched.
*Trace:* intention §14G semantics 2 and response table; plan 8A C3(c) and §7 "rows owed".

**Card 2 — when the article number does find an item, which values are matched?**
*Question:* Are the checks and the matcher run against the stored item's category, properties and
quantity, or against the ones typed into the request?
*Story:* A manager previews an existing chair by its article number, but types in the properties he
is about to change it to. If the preview reads what he typed, it can answer "accepted" while the
create a second later refuses — create always reads the stored item. Within a week the board's
users learn the preview lies, which is exactly the failure it was added to remove.
*Branches:* **stored wins** — preview and create can never disagree; the typed fields are used only
when no item was found · **supplied wins** — the preview answers a hypothetical and may contradict
create · **mixed** — stored category, typed properties and quantity; two rules to explain and to
test.
*Recommendation:* stored wins whenever an item resolves; the typed fields are the "no item yet"
path. One evaluation, two callers, one answer.
*On silence:* the gate holds; the row is not authored and the phase is not dispatched.
*Trace:* §14G request table and MC-21; plan 8A C1(a) case (ii), C3(d), §7 "rows owed".

**Card 3 — with no task, what does the "task not found" check say?**
*Question:* When `task_id` is null, does `task_not_found` also read "assumed" like the other three,
or plain "passed", or "not evaluated"?
*Story:* The user is creating the task in the same act, so there is no task that could be missing.
The response is meant to let the screen show which answers were assumed rather than measured. If
this one reads a plain "passed", the board displays a green check about a task nobody has created
yet — the one thing §14G's construction rule was written to prevent.
*Branches:* **assumed** — a fourth `pass_by_construction`, consistent with the ratified three, but
the ratified list names three · **passed** — reads as measured and quietly overstates the answer ·
**not evaluated** — honest, but a different word for the same situation as the other three.
*Recommendation:* assumed, for the same reason the other three are.
*On silence:* the gate holds; C5(a) ships without this clause and the phase is not dispatched.
*Trace:* §14G construction rule; plan 8A C5(a) and §7 "rows owed".

## 2. Read first

1. **Intention §14G in full** (round 10, 2026-09-21) — the authority; it wins over this plan.
   With it: §9C **MC-13** phase 3 as amended by §14F F9/P44 (the nine checks and their order),
   **MC-12** (what the matcher returns), §9E **MC-18** (role cells), §5A **MC-16** (soft-delete
   predicates → `NotFound`), §13A (MC-21's registration; it serves **M4**).
2. `master_plan.md` §6.1 (`enums.py`, `criteria_matcher.py`), §6.4 (error classes), §6.5
   (`create_stock_task_assignments.py`, the queries package), §6.6 (routes and the explicit
   error rendering), §9 rules 1, 2, 7, 16, 17, 18, 19, §9B ruling 1 (`client_id` travels in the
   path), §10 (environment, baseline, the ULID ordering measurement), §3B (how this project runs
   roles; *Mutation cells* classes 1–3).
3. `plans/plan_8.md` **in full, including its Review log** — its 67 criterion rows are the standing
   evidence for everything the extraction moves, and §7 of this plan depends on them staying green.
4. Repo, as shipped at `798fc69`:
   `bm/services/commands/stock_report/create_stock_task_assignments.py` (`_phase3_reason:124-155`,
   the three lookups `:76-121`, the phase-3 loop `:196-214`),
   `bm/domain/stock_report/criteria_matcher.py` (`evaluate_stock_criteria`,
   `build_item_property_bag` — reads only `item.properties` and `item.quantity`),
   `bm/services/queries/stock_report/get_stock_report_consistency.py` (the read-service shape),
   `bm/routers/api_v1/stock_report.py` (`_run`, the three `extra="forbid"` body models),
   `bm/models/tables/items/item.py:83-96` (`uix_items_workspace_article_number`,
   `uix_items_workspace_sku` — partial unique, `… IS NOT NULL AND is_deleted = false`),
   `bm/routers/api_v1/app_update_presentations.py:286-296` (precedent: a **query** service receiving
   a path `client_id` through `incoming_data`),
   `bm/services/commands/stock_report/repair_stock_report.py` (precedent: a command importing from
   `services/queries/stock_report/consistency.py`, which is why the shared input fetcher may live in
   the queries package).

## 3. Dependencies

Phase 8 **VERIFIED**, batch C1 **APPROVED** (`798fc69`). Nothing else: this phase adds no state, no
migration and no event, and it is independent of phases 9–14.

**Gate obligation, not a criterion row (see §7):** the extraction is a refactor of an APPROVED
file. It is complete only when **plan 8's own test files pass unchanged** — no test edited, none
added, none deleted, in:

- `app/tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py`
- `app/tests/integration/services/commands/stock_report/test_create_stock_task_assignments_race.py`
- `app/tests/integration/services/commands/stock_report/test_delete_stock_task_assignments.py`
- `app/tests/unit/routers/api_v1/test_stock_report_router.py`
- `app/tests/unit/domain/stock_report/test_stock_report_serializers.py`

Both runs are recorded — once **before** the extraction and once **after**, same command, same
files — because "unchanged" is a two-sided claim and only the pair measures it. That pair is the
evidence for half 1; it is cheap, it already exists, and no row in §6 duplicates it.

## 4. Files expected to change

**New:**
- `bm/domain/stock_report/assignment_checks.py` — the MC-21 evaluation (pure, no I/O).
- `bm/services/queries/stock_report/assignment_check_inputs.py` — the three non-locking lookups both
  callers need, moved out of the command unchanged.
- `bm/services/queries/stock_report/preview_stock_task_assignment_match.py` — the preview service.
- `app/tests/unit/domain/stock_report/test_stock_report_assignment_checks.py`
- `app/tests/integration/services/queries/stock_report/test_preview_stock_task_assignment_match.py`

Both new test filenames were checked against the whole tree on 2026-09-21 and collide with nothing
(§9 rule 19: bare filenames are module names in this repo).

**Edited:**
- `bm/domain/stock_report/enums.py` — one enum added.
- `bm/services/commands/stock_report/create_stock_task_assignments.py` — **an APPROVED phase-8
  file**; `_phase3_reason` and the three `_lookup_*` helpers leave it, their call sites adapt.
  Nothing else in the file changes: not the phases, not the order, not the writes, not the response.
- `bm/routers/api_v1/stock_report.py` — one route and one body model.
- `app/tests/unit/routers/api_v1/test_stock_report_router.py` — the new route's role cells and its
  `extra="forbid"` cell (the file's existing tests are untouched).

## 5. Tasks

**Names this phase registers.** They are fixed here and are owed as an amendment to master plan
§6.1/§6.5/§6.6 by the coordinator (this session writes one file only). §9 **rule 18** applies: each
is pinned by a row in §6.

1. **`enums.py`** — add `StockAssignmentCheckResultEnum`: `PASS = "pass"`, `FAIL = "fail"`,
   `PASS_BY_CONSTRUCTION = "pass_by_construction"`, `NOT_EVALUATED = "not_evaluated"` (§14G's
   response table; the vocabulary is closed). Serialized by `.value`, never the member (the MC-19
   lesson, master plan §6.5 `_events.py`).

2. **`bm/domain/stock_report/assignment_checks.py`** — the MC-21 implementation:

   ```python
   @dataclass(frozen=True)
   class AssignmentCheckResult:
       check: str                                  # MC-13's reason name
       result: StockAssignmentCheckResultEnum
       advisory: bool

   ADVISORY_CHECKS = frozenset({"item_already_assigned"})        # §14G semantics 1
   PASS_BY_CONSTRUCTION_CHECKS = frozenset({                     # §14G construction rule
       "task_failed_or_cancelled", "item_not_task_primary", "already_processed_by_scanner",
   })

   def evaluate_assignment_checks(
       *, row, task, item, task_id: str | None, item_id: str | None,
       primary_pairs, processed_pairs, active_item_ids,
       assumed: Mapping[str, StockAssignmentCheckResultEnum] | None = None,
   ) -> list[AssignmentCheckResult]: ...

   def first_failed_check(results) -> str | None: ...
   ```

   **This is a move, not a rewrite.** The nine branches are `_phase3_reason`'s nine branches
   (`create_stock_task_assignments.py:134-155`) in the same order, with the same predicates,
   including the three `is_deleted` tests the batch-C1 fix round added. What changes:
   - the function takes the already-fetched `row` / `task` / `item` (or `None`) instead of the three
     dicts — MC-21's words are "a pure function of already-fetched entities", and the preview holds
     entities, not lock maps; the dict lookups move to the create call site;
   - it does not return early: every check appends one `AssignmentCheckResult`, in order, so the
     returned list always has **nine** elements;
   - a check named in `assumed` is reported with the given result and **not evaluated** (the preview
     passes the construction-rule map; `create` passes nothing);
   - `advisory` is `check in ADVISORY_CHECKS`, a report-only attribute: **it must not change what
     `first_failed_check` returns**, or `create` would stop refusing `item_already_assigned`.
     Plan 8 C1(j)/C1(k) are the standing evidence for that and must stay green.
   `first_failed_check` returns the `check` of the first `FAIL`, or `None`. It is the **only**
   producer of both `create`'s refusal reason and the preview's `refusal_reason` — §14G defines the
   latter as "what `create` would refuse with", and one producer is the cheapest way to make that
   true rather than merely tested.

3. **`bm/services/queries/stock_report/assignment_check_inputs.py`** — move
   `_lookup_primary_pairs`, `_lookup_processed_pairs` and `_lookup_active_item_ids`
   (`create_stock_task_assignments.py:76-121`) here **verbatim** as one public entry point,
   `fetch_assignment_check_inputs(session, *, workspace_id, task_ids, item_ids)`, returning the
   three sets. They are plain `SELECT`s with no `FOR UPDATE`, so both callers can share them, and a
   second copy of `processed_pairs`' state filter or `active_item_ids`' `ACTIVE_ASSIGNMENT_STATES`
   predicate (§9 rule 16) is exactly the drift MC-21 exists to prevent. The command imports it; the
   precedent for a command importing from `services/queries/stock_report/` is
   `repair_stock_report.py` → `consistency.py`.

4. **`create_stock_task_assignments.py`** — delete `_phase3_reason` and the three `_lookup_*`
   helpers; the phase-3 loop becomes
   `reason = first_failed_check(evaluate_assignment_checks(row=locked_rows.get(entry.stock_report_item_id), task=locked_tasks.get(entry.task_id), item=locked_items.get(entry.item_id), task_id=entry.task_id, item_id=entry.item_id, …))`.
   No other line of the file changes. Run the §3 before/after pair.

5. **`preview_stock_task_assignment_match(ctx) -> dict`**
   (`bm/services/queries/stock_report/preview_stock_task_assignment_match.py`). Read-only: no
   `maybe_begin`, no lock, no write, no event (§14G: "it writes nothing, locks nothing and reserves
   nothing"). Order:
   1. parse `ctx.incoming_data` with a module-local Pydantic model — `client_id` (injected by the
      router), `task_id: str | None`, `article_number: str | None`, `sku: str | None`,
      `item_category_id: str`, `properties: dict`, `quantity: int` (**required**; §14G:
      `build_item_property_bag` sets `bag["quantity"]` and board criteria constrain it). A parse
      failure raises `beyo_manager.errors.validation.ValidationError` (422) through the same
      `_raise_validation_error` shape as `requests/__init__.py`.
   2. the row: `workspace_id == ctx.workspace_id`, `client_id ==`, `is_deleted is false`; absent →
      `NotFound` (§14G last line; MC-16).
   3. the task, when `task_id` is not null: same three predicates. A task that is absent, deleted or
      foreign is **not** a `NotFound` — it is the `task_not_found` check.
   4. the candidate item, when an identifier is given: by `article_number` **or** `sku`, live and in
      this workspace (the two partial unique indexes make at most one). No hit → `matched_item_client_id`
      is null; that is a normal outcome, never a 404 (§14G semantics 2).
   5. `fetch_assignment_check_inputs(...)` for the ids that resolved.
   6. `evaluate_assignment_checks(...)`, with `assumed = {c: PASS_BY_CONSTRUCTION for c in
      PASS_BY_CONSTRUCTION_CHECKS}` when `task_id is None`, and `{}` otherwise.
   7. the matcher: `evaluate_stock_criteria(candidate, row.properties)` where `candidate` carries
      the properties and quantity being previewed. Build it as a **transient `Item` instance**
      (`Item(properties=…, quantity=…)`, never added to the session) so the matcher holds the object
      type production holds (charter rule 3) and `build_item_property_bag` is exercised, not
      bypassed. The matcher always runs and reports **every** failure (MC-12 has no short-circuit),
      whatever phase 3 said.
   8. the response, exactly §14G's seven keys: `can_proceed` (no **non-advisory** check reported
      `FAIL`; property mismatches do not clear it), `override_required` (`property_failures` is
      non-empty), `refusal_reason` (`first_failed_check`, advisory failures included — it is what
      `create` would refuse with), `property_failures` (`[{key, reason}]`, `reason` the
      `StockCriteriaMismatchReasonEnum` value, sorted by key — the **same element shape** as the
      409's `details[].failures[]`), `matched_item_client_id`, `checks`
      (`[{check, result, advisory}]`, nine entries in MC-13 order).
   **Blocked on owner cards 1–3** (§8): which result the item-dependent checks carry when no item
   resolved, which values are matched when an identifier does resolve, and what `task_not_found`
   reports when `task_id` is null. Do not choose; the gate holds.

6. **Router** — `@router.post("/items/{client_id}/match-preview")`,
   `Depends(require_roles([ADMIN, MANAGER, WORKER]))`, a body model with
   `ConfigDict(extra="forbid")` (the shape the batch-C1 fix round landed on the other three), and
   `incoming_data={**body.model_dump(), "client_id": client_id}` (§9B ruling 1). It goes through
   `_run`; it raises neither structured assignment error, so nothing is added to
   `_STRUCTURED_ASSIGNMENT_ERRORS`.

7. **Tests, written from §6's table, one row at a time.** With no tester this round, the implementer
   also sites every `—` cell on the code it has just written, runs it, and records the red
   (master plan §3B class 2; charter rule 15 for the two planted-defect rows). Every run is
   whole-file, never `-k` (§9 rule 8).

## 6. Criteria

Fixture **F0** (master plan §6.8): workspace **W**, manager **U**, category **K** (Dining Chairs),
item **I** (`quantity 4`, `properties {"wood_type": "Teak", "upholstery": "Down"}`,
`article_number "SR-<suffix>"`, category K), task **T** (`pending`, PRIMARY = I), row **R**
(category K, criteria `{"wood_group": ["teak"]}`, `quantity_requested 10`).

`PV(body)` = `preview_stock_task_assignment_match(make_ctx(session, seeded, role_name="worker",
incoming_data={**body, "client_id": R.client_id}))`. `CR(entries)` = plan 8's create command.
**The acceptable body** `B0` = `{"task_id": T, "article_number": I.article_number,
"item_category_id": K, "properties": I.properties, "quantity": 4}`; a row that names a field
overrides that field of `B0` and changes nothing else.

Every outcome below is computed from **F0**'s own values plus the row's own deltas, side effects
included. A fixture makes its row's predicate the **only** reason its outcome holds. An outcome that
disagrees with its own fixture is a plan defect: report it, never reconcile it in the test.
Every row asserts the request left the workspace unchanged and ends with
`assert_stock_report_clean` (§9 rules 1 and 2) — the surface is read-only, so this holds for
refusal rows too.

Tenancy rows (C4(a) case 3, C4(c) case 2) use a **cross-workspace reference**: the foreign entity is
otherwise a valid target of this request, so tenancy is the only reason the outcome holds.

**Mutation cells.** A `—` cell is a **deliberate class-2 blank** (master plan §3B): the outcome is
real but the line that makes it true lives in a file this phase has not written yet, so naming a
site now would name a site that may not exist — the defect that cost plan 8 C5(b) a round. Each
blank carries its note; the implementer sites it on the real code, runs it, and records the red.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | Three triples, each refused by `create` for a different one of the three entities the preview looks up itself. (i) T raw-set `is_deleted = true`; (ii) I in **K2** and `item_category_id: K2` in the body (so the outcome holds whichever side card 2 rules for); (iii) I's PRIMARY `TaskItem` raw-set to RELATED. Per case the test calls **both** `CR([{R, T, I}])` and `PV(B0 + the case's field)` and compares | per case, `PV(...)["refusal_reason"] == ` the `reason` of the `{index: 0}` element of the `StockAssignmentRefused` `CR` raises — **both sides computed in the test, neither typed**; the values are (i) `task_not_found`, (ii) `category_mismatch`, (iii) `item_not_task_primary`; nothing written by either call | — *(class 2, one per case: the only possible divergence is the preview's own entity lookup, since the decision itself is shared — e.g. for (i), drop `is_deleted` from the preview's task read. The site is in the new preview module)* | **MC-21** ("neither may hold a check the other lacks"), MC-13 phase 3, M4 |
| C1(b) | Unit, transient production instances (charter rule 3): `row` in K1; `task` `state FAILED`; `item` in K2 with `quantity 1`; `task_id`/`item_id` given; `primary_pairs = set()`, `processed_pairs = set()`, `active_item_ids = {item_id}`; `assumed` omitted | `evaluate_assignment_checks` returns **nine** results whose `check` values are, in order, `stock_report_item_not_found`, `task_not_found`, `item_not_found`, `item_not_task_primary`, `already_processed_by_scanner`, `task_failed_or_cancelled`, `item_already_assigned`, `item_has_no_category`, `category_mismatch`; exactly four are `fail` (`item_not_task_primary`, `task_failed_or_cancelled`, `item_already_assigned`, `category_mismatch`) and the other five `pass`; `advisory` is true on `item_already_assigned` and false on the other eight; `first_failed_check(...) == "item_not_task_primary"` | return as soon as a check fails (`assignment_checks.py:evaluate_assignment_checks`, definition site) → the list is four long and the last three results are absent | **MC-21** ("returns the per-check results in that order"), MC-13 phase 3 order, §9 rule 18 |
| C2(a) | `PV(B0)` — every check passes | the response has **exactly** the **eight** §14G keys — the seven of the ratified response table plus **`values_source`**, added by the owner 2026-09-21 so a caller can see whether the stored item or its own supplied values were evaluated (owner card 2); `can_proceed true`; `override_required false`; `refusal_reason None`; `property_failures == []`; `matched_item_client_id == I.client_id`; `values_source == "stored"`; `checks` is the nine MC-13 names in order, every `result == "pass"`, `advisory` true only on `item_already_assigned` | — *(class 2: the response is assembled in the new preview module; site the key set or the `pass` mapping there)* | §14G response table, MC-21, §9 rule 18 |
| C2(b) | `PV(B0)` on the same acceptable triple — the one case where a write would be plausible | no `stock_task_assignment` row exists for (R, T, I) after the call; R's counters are still `(0, 0, 0)` with `quantity_requested 10`; `T.is_stock_assignment` is still `false`; `assert_stock_report_clean` | **planted defect (charter rule 15):** insert and flush a `StockTaskAssignment` for the previewed triple inside `preview_stock_task_assignment_match` (definition site) → the row exists and the counters move | §14G ("writes nothing, locks nothing and reserves nothing"), M1 |
| C3(a) | `CR([{R, T, I}])` first, so I carries an active `in_queue` assignment; then `PV(B0)` — the same triple | the `item_already_assigned` entry of `checks` is `{result: "fail", advisory: true}`; **`can_proceed` is `true`**; every other check `pass` | remove `item_already_assigned` from `ADVISORY_CHECKS` (`assignment_checks.py`, definition site) → `advisory` reads false **and** `can_proceed` flips to false | §14G semantics 1, MC-13, M4 |
| C3(b) | the C3(a) fixture and call | `refusal_reason == "item_already_assigned"` — `can_proceed true` and a non-null `refusal_reason` coexist, because the reason is what `create` would refuse with, advisory or not | — *(class 2: the preview's `refusal_reason` derivation — e.g. filter advisory failures out of it — is in the new module)* | §14G response table + semantics 1, MC-21 |
| C3(c) | Two cases, both otherwise `B0`: (i) `article_number: "SR-does-not-exist"`; (ii) `article_number: None, sku: None`. Both send `item_category_id: K`, `properties: {}`, `quantity: 1` | no error is raised (in particular **not** `NotFound`); `matched_item_client_id is None`; `property_failures == [{"key": "wood_group", "reason": "missing_on_item"}]` — computed from the **supplied** `properties` and `quantity` against R's criteria, not from I; `override_required true` | — *(class 2, planted defect, charter rule 15: make the preview raise `NotFound` when the identifier resolves to nothing; site it in the new module)* | §14G semantics 2, MC-12, M8 |
| C3(d) | A second row **R2** in K whose criteria are `{"quantity": ["4"]}` only, previewed in the path. Two cases, otherwise `B0` with `article_number: None`: (i) `quantity: 4`; (ii) `quantity: 7` | (i) `property_failures == []` and `override_required false`; (ii) `property_failures == [{"key": "quantity", "reason": "value_not_accepted"}]` and `override_required true`. **`can_proceed` is deliberately not asserted by this row**: no item resolves here, so owner card 1 owns it | — *(class 2, one per case: the preview's construction of the candidate — e.g. build it without the request's `quantity`, which `build_item_property_bag` would then read off a default)* | §14G request table (`quantity` is a matched criterion), MC-12 step 1.5, M8 |
| C3(e) | **Authored by the owner, card 1, 2026-09-21.** C3(c)'s two cases (i) an `article_number` matching no live item and (ii) neither identifier sent, both otherwise `B0` with a `task_id` present and acceptable | the four **item-dependent** checks — `item_not_found`, `item_already_assigned`, `item_has_no_category`, `category_mismatch` — each read `result == "not_evaluated"`; `refusal_reason is None`; **`can_proceed` is `true`** even though no item exists; `matched_item_client_id is None`; `values_source == "supplied"`. The property and quantity checks still run against the supplied values (C3(c)) | force the unresolved-item path to report `item_not_found` as a **failure** rather than `not_evaluated` (`preview_stock_task_assignment_match.py`, definition site) → `can_proceed` flips to `false` and `refusal_reason` becomes `item_not_found`, which is the answer that would make this endpoint refuse the one case it exists for | §14G semantics 2 ("a normal outcome, not a 404 — the creation case this endpoint exists for"), MC-21; owner card 1 |
| C3(f) | **Authored by the owner, card 2, 2026-09-21.** An item I **does** resolve by `article_number`, and the request deliberately disagrees with it: I is stored with category K, `properties {"wood_group": "teak"}` and `quantity 4`, while the body sends `item_category_id: K2`, `properties: {"wood_group": "oak"}` and `quantity: 7`. R's criteria accept teak and quantity 4 | the evaluation reads **the stored item**, not the body: `property_failures == []`, `category_mismatch` reads `pass`, `can_proceed true`, `matched_item_client_id == I`, and **`values_source == "stored"`** — the field exists so a caller can see that its typed values were not the ones evaluated (owner, 2026-09-21). Were the body's values used instead, the row would report a category mismatch and an oak failure | evaluate against the request's `item_category_id`/`properties`/`quantity` when an item resolved (`preview_stock_task_assignment_match.py`, definition site) → the preview answers `false` where `create` would answer `true`, the exact preview-lies-to-create divergence MC-21 forbids | §14G request table, MC-21 ("one evaluation, two callers"); owner card 2 |
| C4(a) | Three cases in the path, body `B0`: (i) `client_id` of no row; (ii) R raw-set `is_deleted = true`; (iii) a row in a **foreign** workspace that is otherwise a valid target (same category, same criteria) | each raises `NotFound`; nothing read back changes | — *(class 2, one per case: the preview's row lookup — drop the existence branch, the `is_deleted` predicate, the `workspace_id` predicate)* | §14G ("a soft-deleted, foreign or absent row in the path is `NotFound`"), MC-16, M4 |
| C4(b) | Two malformed bodies: (i) `B0` without `quantity`; (ii) `B0` with **both** `article_number` and `sku` set to live values | each raises `beyo_manager.errors.validation.ValidationError` (`http_status 422`); nothing else is read | — *(class 2: the request model in the new preview module — drop the required-`quantity` declaration; drop the alternatives constraint)* | §14G request table (`quantity` **required**; `article_number` and `sku` "are alternatives, not both"), MC-13 phase 0 (a local API, so strict) — see §7 for the reading of "not both" |
| C4(c) | Two cases, body `B0` with the named `article_number`: (i) the value belongs only to a **soft-deleted** item in W; (ii) the value belongs only to a live item in a **foreign** workspace that is otherwise a valid candidate (same category, same properties) | `matched_item_client_id is None` in both; no error; the response is otherwise the C3(c) shape | — *(class 2, one per case: the preview's item lookup — drop `is_deleted`, drop `workspace_id`)* | §14G request table ("at most one **live** item per workspace"), MC-16, M4, §9 rule 1 |
| C5(a) | `PV(B0 + {"task_id": None})` — everything else acceptable | **four** entries — `task_not_found`, `task_failed_or_cancelled`, `item_not_task_primary`, `already_processed_by_scanner` — each read `result == "pass_by_construction"` (**owner card 3, 2026-09-21: `task_not_found` is the fourth, for the same reason as the other three — with `task_id` null the task will exist by create time, so the check passes by construction; §14G named three because those were the interesting ones, not because the list was exhaustive**) and **never** `"pass"`; the four checks that do not depend on a task — `stock_report_item_not_found`, `item_not_found`, `item_already_assigned`, `item_has_no_category`, `category_mismatch` — are evaluated and `pass`; `can_proceed true` and `refusal_reason None`, which card 3 has now settled. **`task_not_found`'s result is deliberately not asserted**: owner card 3 owns it | remove `item_not_task_primary` from `PASS_BY_CONSTRUCTION_CHECKS` (`assignment_checks.py`, definition site) → with no task there is no primary pair, so it is evaluated and reports `fail`, and `can_proceed` flips | §14G construction rule, MC-21 |
| C5(b) | `task_id: T` supplied, with one planted cause per assumed check: `CR([{R, T, I}])` → `move_assignment(in_queue → awaiting)` → `move_assignment(awaiting → resolved)`; then raw-set the (T, I) `TaskItem.role` to RELATED and raw-set `T.state = cancelled`; then `PV(B0)` | all three of `item_not_task_primary`, `already_processed_by_scanner`, `task_failed_or_cancelled` read `result == "fail"` — measured, never assumed, and all three reported because the evaluation does not short-circuit; `item_already_assigned` is `pass` (the assignment is terminal, so the item is not active); `can_proceed false`; `refusal_reason == "item_not_task_primary"` (first in MC-13's order among the three) | — *(class 2: the preview's choice of `assumed` — e.g. apply `PASS_BY_CONSTRUCTION_CHECKS` regardless of `task_id`; the conditional is in the new module)* | §14G construction rule ("with `task_id` supplied, all three are evaluated against the real task"), MC-13 order, §14F F9 |
| C6(a)–C6(d) | `POST /api/v1/stock-report/items/sri_1/match-preview` as admin / manager / worker / seller, router unit shape (`TestClient`, `dependency_overrides[get_jwt_claims]`, faked `run_service` — `test_stock_report_router.py`'s `client()` helper) | reached (200) / reached / reached / **403**, and for seller the service is never called | `require_roles([...])` on the match-preview route (`bm/routers/api_v1/stock_report.py`, route decorator) — four mutants, one per sub-row, each run separately: drop `ADMIN` → (a) reddens · drop `MANAGER` → (b) · drop `WORKER` → (c) · add `SELLER` → (d) | §14G ("roles ADMIN, MANAGER, WORKER — the set that may create an assignment"), MC-18, M9 |
| C6(e) | the same router shape, an otherwise valid body plus one unknown top-level field | status 422; the service is never called | drop `ConfigDict(extra="forbid")` from the match-preview body model (`bm/routers/api_v1/stock_report.py`, definition site) → the field is dropped and the request succeeds 200 | MC-13 phase 0 ("unknown fields → 422"); batch C1 review S1, the same defect on the sibling routes |
|~~C6(f)~~| the same router shape, valid body, path `.../items/sri_42/match-preview` |**WITHDRAWN to a §7 note, 2026-09-21.** The row asserts at the faked `run_service` seam, not at a user-visible boundary — the only row in this plan that does. The owner's standing rule of 2026-09-19 is that implementation-coupled test demands are **backlog notes, never blocking**, so it is recorded in §7 instead of shipped as a criterion. The risk it named is real (a dropped path param is silent), but proving it through the fake proves the fake's wiring|—| §9B ruling 1 (`client_id` travels in the path), §14G endpoint path — **boundary declared in §7** |

## 7. Notes

- **C6(f) withdrawn to this note (owner rule of 2026-09-19, applied 2026-09-21).** The row
  asserted that the path `client_id` reaches the service, observed through the faked
  `run_service` seam — the only row in this plan not stating a user-visible outcome. The owner's
  standing rule is that implementation-coupled test demands are **backlog notes, never
  blocking**. Recorded here rather than shipped as a criterion. **The risk is real and is not
  discharged by this note:** if the route stops injecting the path parameter, every request
  silently previews against the wrong row or parse-fails, and nothing in this plan would catch
  it. This repo's router tests fake `get_db`, so no DB-backed HTTP row is available to prove it
  honestly. If phase 14 or a later phase gains a real HTTP fixture, this is the first thing to
  point it at.
- **`values_source` (owner, 2026-09-21, card 2).** The response carries an eighth key,
  `"stored" | "supplied"`, naming which values the evaluation actually used. It exists because
  card 2's ruling is correct but surprising: a caller who types changed properties, gets
  `can_proceed true`, and does not realise the **stored** item was evaluated has no way to see
  why. The rule is made visible rather than left silent. Intention §14G's response table is
  amended in the same act.

**The two halves carry very different evidence, on purpose.**

- **The extraction touches `create_stock_task_assignments.py`, an APPROVED phase-8 file.** Its
  evidence is **plan 8's suite passing unchanged** (§3's before/after pair), not new rows. Plan 8's
  67 armed rows already pin every one of the nine checks, its `is_deleted` predicates (C1(v),
  C1(w)), the two adjacent-pair order rows (C1(t), C1(u)), the all-or-nothing behaviour and the
  refusal envelope. They exercise the moved code through the same command on the same fixtures; if
  they stay green, the move is proven by evidence that already exists and was already adversarially
  reviewed.
- **Rows deliberately NOT written for the extraction half**, each an explicit under-specification:
  1. **No parallel rows for the nine MC-13 checks.** Plan 8 C1(a)–C1(w) own them. Re-asserting them
     against the extracted function would buy a second copy of the same discrimination at the price
     of nine rows a reviewer must probe — charter rule 16 and master plan §3B's over-evidence rule
     both bite.
  2. **No row for MC-13's precedence order as such.** C1(b) pins the returned order once, which is
     the genuinely new observable; the *refusal* order is plan 8 C1(t)/C1(u)'s.
  3. **No matcher rows.** MC-12 is plan 2's, unchanged here; C3(c)/C3(d) assert the preview's use of
     it, not its verdicts.
  4. **No row for "`create`'s behaviour is unchanged".** That is not a criterion, it is the gate in
     §3; a row asserting it would either restate a plan-8 row or assert nothing.
  5. **No concurrency row, and none is needed.** The preview takes no lock, holds no transaction and
     writes nothing, so there is no interleaving whose outcome differs. **Plan 8 C5(a)'s two-session
     fixture is explicitly not to be copied**: it was measured this round not to force its race (the
     lock was removed and the test stayed green 9 runs of 9, because one session's connection is
     warm and the other's opens lazily after the barrier), and the owner accepted that as a known
     gap. Reproducing the shape here would buy a row that cannot fail. §14G semantics 1 already says
     what happens when another actor takes the item between preview and create: a later refusal is
     correct behaviour, not a defect.
  6. **No row for §14G semantics 3 ("the preview is not a promise").** It is a rule about how a
     client may read the answer; it has no observable of our own. It is carried into the frontend
     contract (phase 14), not into a test.
- **The preview half is new surface and carries ordinary criteria** — the request fields including
  `quantity`, the response's seven keys, the roles, the construction rule and its
  `pass_by_construction` results, the advisory check, the unresolved identifier that is not a 404,
  `NotFound` on the row in the path, and the property-failure element shape.

**Boundaries each row is proven at (§9 rule 17 — stated, never quietly chosen).** C1(b) is proven at
the pure function (it is a pure function's contract). C1(a), C2, C3, C4(a), C4(c), C5 are proven at
the **service** boundary via `PV(...)`, which is plan 8's own shorthand for this project's command
and query rows. C4(b) is proven at the service boundary too, because that is where the plan puts the
parse; **C6(e) additionally proves the endpoint refuses an unknown field**, which is the one place
batch C1 found the two boundaries disagreeing (review S1). C6(a)–C6(f) are proven at the router, in
the shipped router-unit shape. **C6(f) is the one row in this plan asserting a value at a seam rather
than a user-visible outcome** — the context handed to the faked `run_service`. It is here because
nothing else can see the path-param injection (this repo's router tests fake `get_db`, so a
DB-backed HTTP test is not the house shape — master plan §10 hazard (d)), and a wrong injection key
would leave every service row green. Declared rather than assumed; the owner may strike it, and if
struck the injection ships unproven and should be said so in the frontend contract.

**Two readings I have taken, flagged rather than buried.**
1. **"`article_number` and `sku` are alternatives, not both" (C4(b) case ii)** is read as a
   constraint on the request, so sending both is a 422, MC-13 phase 0 being strict for a local API.
   If the owner meant "`sku` is ignored when `article_number` is present", C4(b)(ii) changes to a
   `matched_item_client_id` assertion. Not carded, because §14G states a rule and only the error
   identity is left to convention — but it is a frontend-visible choice.
2. **`checks[].check` carries MC-13's reason names** (`item_already_assigned`, …), the vocabulary
   already registered in master plan §6.4 and already used by `refusal_reason`. A second naming for
   the same nine things would be a §6 registry violation.

**Registry additions owed to the coordinator** (this session writes one file, so master plan §6 is
not edited here): §6.1 — `StockAssignmentCheckResultEnum` in `enums.py`, and the module
`assignment_checks.py` with `AssignmentCheckResult`, `ADVISORY_CHECKS`,
`PASS_BY_CONSTRUCTION_CHECKS`, `evaluate_assignment_checks`, `first_failed_check`; §6.5 —
`assignment_check_inputs.py` (`fetch_assignment_check_inputs`) and
`preview_stock_task_assignment_match.py` (`preview_stock_task_assignment_match(ctx) -> dict`) under
`bm/services/queries/stock_report/`, and the removal of `_phase3_reason` / the three `_lookup_*`
helpers from the `create_stock_task_assignments.py` row; §6.6 — the route row
`POST /api/v1/stock-report/items/{client_id}/match-preview` → `preview_stock_task_assignment_match`,
roles ADMIN/MANAGER/WORKER, phase 8A; §4/§4A — the tracker rows for this phase.

**Environment and standing rules that bite here.**
- Baseline for any L4 in this phase: **21 failed / 3547 passed / 1 skipped** at `798fc69`, the 21
  failure IDs being the published set (master plan §10); diff both directions.
- §9 **rule 7**: no statement counting anywhere in this plan. The read-only claim (C2(b)) is proven
  by observable state, not by counting writes, so no sixth ratified use is requested.
- §9 **rule 16**: `active_item_ids` keeps reading `ACTIVE_ASSIGNMENT_STATES` and `processed_pairs`
  its two terminal members through the moved code; no literal state list is introduced.
- §10 **ULID ordering**: no fixture in §6 depends on creation order, and none may be written to
  (`client_id` order is a coin flip — 977 of 1999 pairs out of order).
- §9 **rule 19**: the two new test filenames were checked against the whole tree; they collide with
  nothing.
- Sizing: 6 criteria (counts derived from the table by script, see below), well inside the
  charter's ≤ 8.

**Row and mutation counts, derived from §6's table (16 table lines, C6(a)–C6(d) being four rows —
not typed):** **19 criterion rows across 6 criteria**. **10 rows carry a named mutation**, over
**7 sites** and **10 mutants**: the early return in `evaluate_assignment_checks` (C1(b)), the
planted insert in the preview module (C2(b), charter rule 15), `ADVISORY_CHECKS` (C3(a)),
`PASS_BY_CONSTRUCTION_CHECKS` (C5(a)), the route decorator (C6(a)–C6(d), four mutants, one per
sub-row), the body model (C6(e)) and the path injection (C6(f)). **9 rows carry a deliberate
class-2 blank**, and their notes ask for one mutation per enumerated case — 3 for C1(a), 3 for
C4(a), 2 each for C3(d), C4(b) and C4(c), 1 each for C2(a), C3(b), C3(c) and C5(b) = **16 to be
sited** by the implementation round. Declared set = **10 named + 16 sited = 26**; the round reports
`executed == declared` against that arithmetic, re-derived from this table rather than copied
(charter manifest properties 3 and 4).

**This plan is not dispatchable until owner cards 1–3 are ruled.** Cards 1 and 3 decide outcome
cells that do not yet exist; card 2 decides a fixture the endpoint's main use case depends on. Rows
owed once they are ruled, to be authored by the owner or by the coordinator under the owner's
ruling (criterion-row authorship is reserved — master plan §3B):
- **on card 1** — one row for the unresolved-identifier case fixing the `result` of
  `item_not_found`, `item_not_task_primary`, `already_processed_by_scanner` and
  `item_already_assigned`, and with it `can_proceed` and `refusal_reason`. C3(c) today asserts only
  the clauses §14G ratifies and deliberately asserts nothing about those four; C3(d) defers
  `can_proceed` for the same reason.
- **on card 2** — one row for a resolved identifier whose stored category/properties/quantity
  **differ** from the supplied ones, pinning which side the checks and the matcher read. C1(a) case
  (ii) was built card-proof (both sides agree) so that it survives either ruling.
- **on card 3** — one clause added to C5(a) for `task_not_found`'s result when `task_id` is null.

## 8. Review log

*(append-only, shared by the implementer and the reviewer.)*

### 2026-09-21 — implementer round 1 — Codex

- Implemented the shared MC-21 evaluator, extracted create-path inputs, added the read-only
  assignment match-preview service and route, and added the evaluator/preview/router tests.
- Required extraction gate: plan-8 create suite was `42 passed` before and `42 passed` after.
  Targeted phase suite: `49 passed`.
- One authoritative L4: `21 failed, 3575 passed, 1 skipped`; current-minus-published and
  published-minus-current failure-ID sets are both empty. Pass arithmetic is `3547 + 28 = 3575`.
- Mutation ledger executed exactly `10 named + 16 class-2 = 26`; `25` were red and reverted.
  C1(a)(i) was equivalent because the shared evaluator independently checks task deletion and is
  reported for owner/coordinator disposition. C6(f) is withdrawn by the §7 note but its declared
  path-wiring site was probed as a non-blocking backfill.
- Architecture Graph delta recorded the preview endpoint and assignment acceptability evaluator;
  graph status was valid with no diagnostics at revision
  `6df549d436ade66e8a2fb254455953f4b9161342b73b14054bd0d822f82155ed`.
- Full evidence, mutation sites, proposed backfills, perimeter, and the two owner questions are in
  `handoffs/implementer/2026-09-21_phase_8A_implement_1_handoff.md`.
