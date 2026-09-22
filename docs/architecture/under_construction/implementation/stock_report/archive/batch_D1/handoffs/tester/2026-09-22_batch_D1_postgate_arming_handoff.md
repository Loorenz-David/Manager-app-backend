---
plan: 12, 13
batch: D1 (post-gate arming round)
role: test
state: OWNER_DECISIONS_PENDING
verdict: 3/3 rows ARMED; 1 owner card
date: 2026-09-22
actor: Opus tester, slot `dq`
---

# Batch D1 — post-gate arming of the three ruled rows, and owner card D-10

**Scope:** plan 12 **C1(p)**, plan 12 **C3(e)**, plan 13 **C3(b)** — the rows the owner ruled and
the coordinator authored after the D1 gate — plus the per-test verdicts owner card **D-10** asked
for. All three rows are **ARMED**. No production code changed. No criterion cell edited, no row
authored.

**Tree:** started and ends at `96e5e33`, clean apart from my two test files.
**Production diff, the reviewer's check, run on the handed-over tree:**

```
$ git diff --name-only HEAD -- app/beyo_manager/ | wc -l
0
```

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — the delete event's workspace comes from the request, not from the row

**Question** — should the `stock_report_item:deleted` event read its workspace from the deleted
row itself, as the registry says, or is reading it from the caller's request good enough?

**Story** — when a manager deletes a stock-report row, the app tells every screen in that
workspace to drop it. Today the message is addressed using the workspace the *request* came from,
not the workspace written on the row being deleted. Those are always the same today, because the
delete refuses anything outside the caller's workspace. But the same deletion routine is about to
get a second caller in the next batch, which deletes rows in a loop rather than one per request.
If that caller ever passes a different workspace, the deletion messages go to the wrong workspace's
screens — and no test anywhere can see it, because at the one caller that exists the two values
are identical by construction.

**Branches**
- **Read it from the row** (a one-line change in the deletion routine): the registry's rule becomes
  true in fact, and the next batch cannot reintroduce the question. Costs one implementer touch of
  already-approved code.
- **Leave it as it is**: correct today, correct for every test that can be written today, and the
  next batch inherits an unwatched assumption.

**Recommendation** — read it from the row: the fix is one line and the second caller lands in the
very next batch, which is exactly when the assumption stops being free.

**On silence** — nothing changes; the row ships armed on its three observable clauses, the fourth
armed by a replacement mutant, and the note carries forward to batch D2. The gate holds.

**Trace** — master plan §6.7; plan 13 C3(b) mutant (ii); `_delete_stock_report_item_cascade.py`
`build_stock_report_item_deleted_event` and its call site; `delete_stock_report_item.py:121`.

---

## 1. Mutations

| M-id | Site (`file:symbol`, def / call-site) | Plan-named? (row) | Landed | Command (scope) | Observed red: test id → assertion / row letter | Reverted |
|---|---|---|---|---|---|---|
| M-P1 | `set_stock_report_item_priority_order.py` — `_find_row` **and** `_lock_row_and_group` (def.): drop the `workspace_id` term | yes, 12 C1(p)(i) | yes (2 + 1 occurrences, printed) | L1 ordering file | `test_order_lookup_refuses_foreign_deleted_and_absent_rows` → `assert await _state(db_session, workspace_id) == before, client_id` — **foreign cell**: the foreign row was reordered and W's own `high` band shifted with it | `git diff --quiet` exit 0 |
| M-P2 | same file — `_find_row` + `_lock_row_and_group` + the post-lock `row.is_deleted` guard (def.): drop `is_deleted = false` | yes, 12 C1(p)(ii) | yes (2 + 1 + 1, printed) | L1 ordering file | same test → same assertion — **soft-deleted cell**: a live `high` row moved `3 → 4`, the renumbering the cell names | `git diff --quiet` exit 0 |
| M-P3 | same file — `_find_row` + the post-lock raise (def.): return instead of raising | yes, 12 C1(p)(iii) | yes (1 + 1, printed) | L1 ordering file | same test → `assert refused == [fg.B, g.D, "sri_absent"]`, observed `[]` — **all three cells answered 200**; the state clauses stayed green, so the red is cleanly on the `NotFound` clause | `git diff --quiet` exit 0 |
| M-E1 | `consistency.py:compute_stock_report_divergences` (def.): widen the `histories` predicate to `IN (QUANTITY_REQUESTED_CHANGE, PRIORITY_ORDER_CHANGE)` | yes, 12 C3(e) | yes (1 site, asserted unique) | L1 ordering file | `test_the_order_record_snapshots_awaiting_without_tripping_the_check` → `assert_stock_report_clean` → `tests/helpers/stock_report.py:143`, the divergence assertion. **1 failed / 17 passed** — C3(d)'s witness stayed green, which is the half-guarded fix this row exists to close | `git diff --quiet` exit 0 |
| M-B1 | `_delete_stock_report_item_cascade.py:build_stock_report_item_deleted_event` (def.): `extra={"stock_report_item_id": client_id}` | yes, 13 C3(b)(i) | yes (1 site, asserted unique) | L1 delete file | `test_cascade_removes_every_assignment_and_soft_deletes_the_row` → `assert deleted_event.extra == {}` (line 358). **1 failed / 5 passed** | `git diff --quiet` exit 0 |
| M-B2 | same builder — "take `workspace_id` from `ctx` rather than the row" | yes, 13 C3(b)(ii) | **cannot land — the code is already in the mutant state** | — | `EQUIVALENT` (unappliable as named). See §4 | n/a, nothing applied |
| M-B2r | same builder, **call site**: `workspace_id=row.client_id` — replacement for M-B2, proposed as a backfill | no (mine) | yes (1 site, asserted unique) | L1 delete file | same test → `assert deleted_event.workspace_id == deleted_row.workspace_id` (line 357). **1 failed / 5 passed** | `git diff --quiet` exit 0 |

**D-10 probes** (not criterion mutations — they answer owner card D-10's conditionals by
execution; all reverted, `git diff --quiet` exit 0 after each):

| P-id | Site | Question it answers | Result |
|---|---|---|---|
| P-D10a | `routers/api_v1/stock_report.py` — `_SetStockReportItemPriorityBody.priority` → `str \| None = None`, `_SetStockReportItemPriorityOrderBody.priority_order` → `int` | are the three `refuse_malformed_bodies` proven one layer down? | router file: **exactly the 3 ids red**, 50 passed, nothing else. Ordering integration file (where C1(m)/C1(n) are armed): **18 passed, fully green** |
| P-D10b | same file — list route `priority: str \| None = None` → `priority: str = ""` | is `…_passes_no_priority_when_the_param_is_absent` guarding a product-visible behaviour? | router file: **only that id red**, 52 passed. List query file: **6 passed**. Combined with the existing green assertion that `_list(identity)` and `_list(identity, "")` return the *same* list, the defect is invisible at the endpoint |
| P-D10c | same file — `priority: StockReportPriorityEnum \| None` → `StockReportPriorityEnum` | is `test_priority_route_accepts_an_explicit_null` the sole guard of a product-visible behaviour? | **only that id red**, 52 passed — a 422 where the published contract promises 200 |
| P-D10d | same file — drop `extra="forbid"` from **both** ordering body models | do the two `refuse_unknown_fields` guard anything else already covers? | **only those 2 ids red**, 51 passed |

**Files a probe touched** (production, all reverted, listed separately from my changes):
- `app/beyo_manager/services/commands/stock_report/set_stock_report_item_priority_order.py`
- `app/beyo_manager/services/queries/stock_report/consistency.py`
- `app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py`
- `app/beyo_manager/routers/api_v1/stock_report.py`

---

## 2. Rows

| Row | Observable (boundary → exact outcome) | Test id | Source | What it detects that nothing else did | M-id(s) | Disposition |
|---|---|---|---|---|---|---|
| 12 C1(p) | `set_stock_report_item_priority_order` as U of W, three calls with target 1 (foreign / soft-deleted / absent) → `NotFound` each; no state anywhere changes; the foreign group byte-identical | `test_order_lookup_refuses_foreign_deleted_and_absent_rows` | **new** | `PATCH …/priority-order` is a second route with its own roles, request model and command module; C1(o) covers the **priority** route only. Before this test, dropping either tenancy term from this command's lookup reddened nothing | M-P1, M-P2, M-P3 | **ARMED** (all three cells, both outcome clauses) |
| 12 C3(e) | `SO(B, 1)` on a row with an `awaiting` assignment of q = 4 → the `priority_order_change` record snapshots `quantity_awaiting == 4` **and** `compute_stock_report_divergences` returns `[]` | `test_the_order_record_snapshots_awaiting_without_tripping_the_check` | **new** | The `2fb7acb` fix excludes **two** record types; C3(d) watches only `priority_change`. Re-admitting `priority_order_change` left all 632 stock-report tests green (re-review probe P3) | M-E1 | **ARMED** |
| 13 C3(b) | `DR(R)` on C1(a)'s fixture → the `stock_report_item:deleted` event for R has `event_name`, `client_id == R`, `workspace_id == R's row's workspace`, `extra == {}` **as equality** | `test_cascade_removes_every_assignment_and_soft_deletes_the_row` | **strengthened** (4 assertions) | The builder was registered in §6.5 and pinned by **nothing** — the re-review set its payload to junk and all six delete tests passed | M-B1 (`extra`), M-B2r (`workspace_id`); M-B2 `EQUIVALENT` | **ARMED** |

Rows in scope = 3 = 3 ARMED + 0 EQUIVALENT + 0 UNFORCEABLE + 0 BLOCKED-*.

## 3. Removed or consolidated tests

None. No test was deleted or merged this round. (Owner card D-10's three deletion candidates were
**kept** — see §5; the condition the owner set for deleting them is not met.)

---

## 4. Mutant M-B2 — why it is `EQUIVALENT`, measured not assumed

The cell says: *"take `workspace_id` from the caller's `ctx` rather than the row → red under a
cross-workspace fixture."*

At `_delete_stock_report_item_cascade.py:201-203`:

```python
    events.append(
        build_stock_report_item_deleted_event(
            client_id=row.client_id, workspace_id=workspace_id
        )
    )
```

`workspace_id` there is the cascade's own keyword parameter. Its only caller today
(`delete_stock_report_item.py:118-125`, confirmed by `grep -rn cascade_delete_stock_report_item
app --include='*.py'` → one call site) passes `workspace_id=ctx.workspace_id`. **So the mutant's
form is what ships**, and applying it is a zero-byte diff.

Nor can a fixture distinguish the two: `_lock_row_and_group` filters `workspace_id ==
ctx.workspace_id` and `row` comes from that result or the command raises `NotFound`, so
`row.workspace_id == ctx.workspace_id` on every path that reaches the builder. The
"cross-workspace fixture" the cell asks for does not exist at this boundary, and building one
would mean calling the builder directly — a narrower surface than the row names, which is the
owner's to change, not mine (doctrine: never move a row's proof to a narrower surface).

Master plan §6.7 states the rule as *"`workspace_id` on every event comes from the entity's row,
never from `ctx`"*. The emitted **value** satisfies it; the **source** does not. That is a
production question, not a verification one, and it is live because 13A is the cascade's second
caller — hence owner card 1. I did **not** file it `BLOCKED-PRODUCTION`: nothing observable is
wrong today, so there is no defect to route to the implementer, only a decision.

I ran **M-B2r** in its place so the `workspace_id` clause is not shipped unarmed.

---

## 5. Owner card D-10 — per-test verdicts, with evidence

Ruled per test, as the owner required. **I authored no criterion row and deleted no test.** The
eighth id in the reviewer's S-3 list — `test_a_row_with_no_assignments_answers_an_empty_list` —
was not in my prompt's scope and is untouched and undecided.

### (a) `test_ordering_routes_refuse_unknown_fields` ×2 — **KEEP** (owner's ruling), and still traceable to **no** row

Documentary check: no criterion row in plan 12 or plan 13 mentions unknown-field rejection,
`extra="forbid"`, or an unexpected key. `C1(m)`/`C1(n)` are about a *value* and a *type*; `C7(a)`–
`C7(l)` and `C5(a)`–`C5(h)` are role cells.

Measured (P-D10d): dropping `extra="forbid"` from both ordering body models reddens **exactly these
two ids and nothing else in the suite's router file** (2 failed / 51 passed). So they are not
redundant — they are the only guard on that contract — but they answer to no rule. **They need a
row, and only the owner writes one.**

### (b) `test_priority_route_accepts_an_explicit_null` — **no existing row covers it; keep**

Re-checked against C1(l) as instructed. C1(l) is `SP(N, null)` at the **command** boundary
(unchanged; no record; no event). It proves the *service* request model accepts `null`. The router
carries a **separate** declaration, `_SetStockReportItemPriorityBody.priority`.

Measured (P-D10c): narrowing that router model to `StockReportPriorityEnum` reddens **only this id**
(1 failed / 52 passed). The failure mode is product-visible and contract-breaking — `PATCH
…/priority` with `{"priority": null}` answers **422** where the published frontend contract
promises 200 and "clear the priority". Nothing else in the suite sees it.

**Verdict: not a restatement of C1(l); keep.** Like (a), it answers to no rule and needs a row the
owner authors.

### (c) `test_list_items_route_passes_no_priority_when_the_param_is_absent` — **C4(b) + C4(d) already cover the behaviour; do not author a row**

Re-checked against C4(b)/C4(d) as instructed.

- C4(b): `GET` with no `priority` → nulls only. C4(d): `priority=` (empty) → nulls only. **Same
  outcome for both inputs**, and that equality is already asserted green at the query boundary:
  `test_no_filter_lists_only_null_priority_rows_by_created_at` asserts `_list(identity, "")` returns
  the identical list to `_list(identity)`.
- Measured (P-D10b): changing the router's default from `None` to `""` reddens **only this id**
  (1 failed / 52 passed) and leaves the list query file green. But by C4(b)+C4(d) that defect
  produces the **identical payload** at the endpoint — it is invisible at the public boundary.
- What remains is an assertion on the argument dict handed to a mocked service
  (`calls[0][1].query_params == {"priority": None}`) — an internal collaborator's call argument,
  which charter rule 2 excludes from being a criterion.

**Verdict: the behaviour is already covered by existing rows; do NOT author a row that restates
them.** Whether to keep the test as an internal smoke check or delete it is a style call I leave
to the owner — I did not delete it, because it is a pre-existing test and deletion authority under
my doctrine covers only tests added in the cycle I am verifying.

### (d) `test_ordering_routes_refuse_malformed_bodies` ×3 — **KEPT; the owner's condition is not met**

The owner's instruction: delete **only if** confirmed by execution that the behaviour is already
proven one layer down.

Measured (P-D10a). The router declares its **own** body models
(`_SetStockReportItemPriorityBody`, `_SetStockReportItemPriorityOrderBody`), separate from the
service's `requests/__init__.py` models that C1(m)/C1(n) pin. Weakening the router's two models:

- `tests/unit/routers/api_v1/test_stock_report_router.py` → **exactly the 3 ids red**, 50 passed;
- `tests/integration/.../test_stock_report_priority_and_ordering.py` (where C1(m)/C1(n) live) →
  **18 passed, fully green**.

The layer below never executes the router's declarations. Deleting these three would leave the
422 contract that the **published frontend contract actually hits** pinned by nothing. **Not
deleted.** They are the same class as (a) and (b): real guards with no rule.

---

## 6. The one L4 stamp

**Pre-run authorization, and a finding against my own session.** I took the L4 once, recorded the
counts, and discarded the failing-ID set before writing it down. A stamp without its both-direction
ID delta cannot be cited, and no narrower scope can produce that delta, so I re-took it. The tree
was byte-identical between the two runs (`git status --porcelain` identical, no file written
between them) and the counts matched exactly. **That is one avoidable full-suite run, ~90 seconds,
and it is over-evidence by the letter of the charter.** Recorded here rather than left for the
reviewer to notice.

```
cd backend/app
BEYO_TEST_SLOT=dq PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q
```

- Tree identity: `96e5e33`, `git status --porcelain` = my two test files only (listed in §7).
- **23 failed / 3742 passed / 1 skipped** (87.03s). First run, same tree: 23 / 3742 / 1 (78.81s).
- Failure-ID delta against the checked-in 23-ID baseline
  (`handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`), **both directions**:
  - observed not in baseline: **0**
  - baseline not observed: **0**

**Arithmetic, derived by command, not typed:**

| Quantity | Command | Value |
|---|---|---|
| tests collected, ordering file | `pytest <file> --collect-only -q` | 18 (was 16) |
| tests collected, delete file | same | 6 (was 6) |
| tests collected, router file | same | 53 (was 53) |
| tests added | `git diff HEAD -- app/tests/ \| grep -c '^+async def test_'` | 2 |
| tests removed | `… grep -c '^-async def test_'` | 0 |
| pass-count delta | 3742 − 3740 | **+2 = 2 added − 0 removed** ✓ |
| rows in scope | §2 | 3 = 3 ARMED |
| plan-named mutations declared | C1(p) 3 + C3(e) 1 + C3(b) 2 | **6** |
| plan-named mutations executed | M-P1, M-P2, M-P3, M-E1, M-B1 run red (5) + M-B2 `EQUIVALENT` (1) | **6** ✓ |
| non-named runs | M-B2r (replacement) + 4 D-10 probes | 5 |
| reverse map | tests touched by this session (2 new + 1 strengthened) → all credited in §2 | no orphans |

---

## 7. Write perimeter

**Changed by me (the only files in my checkpoint commit):**
- `app/tests/integration/services/commands/stock_report/test_stock_report_priority_and_ordering.py`
  — +2 tests (C1(p), C3(e)); `delete` added to the `sqlalchemy` import for the teardown fix.
- `app/tests/integration/services/commands/stock_report/test_delete_stock_report_item.py`
  — +4 assertions inside the existing C1(a) test (C3(b)); no new test.
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_12.md`
  — Review log entry appended (verification half). **No criterion cell touched.**
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_13.md`
  — Review log entry appended (verification half). **No criterion cell touched.**
- this handoff.

**Touched only by a reverted probe** (production; listed separately, none committed): the four
files in §1. `git diff --name-only HEAD -- app/beyo_manager/` → **0 files**.

**Not touched:** the master plan tracker, `OWNER_CARDS_batch_D.md`, any criterion cell, any other
role's prompt or handoff, any production file, any migration or config. `ruff check` clean on both
test files.

---

## 8. Blocked rows, candidate criteria, and what variation I did not spend

**Blocked rows:** none.

**Candidate criteria** (for the coordinator/owner to fold or refuse — I authored none):
1. **The router's own request-model contract has no row.** Five ids
   (`refuse_unknown_fields` ×2, `refuse_malformed_bodies` ×3) and
   `test_priority_route_accepts_an_explicit_null` guard a *second, independent* copy of the 422/200
   contract that the published frontend contract actually hits, measured to be pinned by nothing
   else. This is D-10's real shape: not "eight tests answering to no rule" but **one missing row
   about the HTTP boundary's request models**, plus one genuinely redundant assertion (§5(c)).
2. **C1(o)'s "no state anywhere changes / foreign group byte-identical" clause cannot fail.** Same
   cause as the defect I fixed in my own test (§ plan 12 Review log, item 3): the loop's
   `rollback()` precedes the state read, and `maybe_begin` runs subordinate. It is never exposed
   because `pytest.raises` fires first under all three of its mutants, so the row is armed — but
   that clause is decoration. Not fixed: C1(o) is APPROVED and outside this round's perimeter.
3. **§6.7's "from the row, never from `ctx`" is not true of the deleted-event builder** — owner
   card 1.

**Proposed plan-cell backfills** (the coordinator folds; I edited no cell):
- 12 C1(p) mutation cell: state that all three mutants are sited across `_find_row` **and**
  `_lock_row_and_group` (plus the post-lock guard for (ii)). At `_find_row` alone all three are
  absorbed by the post-lock re-read — the same double guard the D1 tester measured on the priority
  command (M-16a / M-17a).
- 13 C3(b) mutant (ii): replace with M-B2r (`workspace_id=row.client_id` at the call site), and
  record that the named mutant is the code's current state.

**Variation I did NOT spend — where the reviewer's budget buys something new:**
- I did not re-measure the inert `_find_row`-only siting on the `priority-order` command; I reasoned
  from the identical structure and the D1 tester's tree-bound measurement on the `priority`
  command. A reviewer who wants that independently has a cheap, genuinely new measurement.
- I ran **one** mutant shape per named cell and no opposite-sign second shape on any of them.
- C3(e): I did not re-run the wider stock-report surface to re-confirm that no other test guards
  the predicate; the re-review's 632-green probe is tree-bound evidence on a matching predicate.
- C3(b): I asserted the event's four named clauses only. I did not enumerate the other events in
  the dispatch list beyond what C3(a) already pins.
- I spent no L2 or L3 run at all this session.

**Anything I could have hidden, stated plainly:**
1. The wasted second L4 (§6) — my error, ~90 seconds, reported rather than silently absorbed.
2. My first version of the C1(p) test had a clause that **could not fail**, and I only found it
   because mutant (i) came back green on an assertion I expected to fire. I could have recorded the
   red it *did* produce and shipped the inert clause; the whole defect family this project has
   closed four times is exactly that. It is written up in plan 12's Review log, including the fact
   that C1(o) has the same latent shape.
3. Under mutant (i) the first run's real assertion was **masked** by an FK error raised in the
   test's own `finally`, and I initially mis-read the run as "the state clauses passed". I chased it
   with a temporary debug print (inserted, measured, removed from a backup copy — `grep -c DEBUG`
   → 0 on the file I ship) before fixing the teardown so the assertion is what a future run
   reports.
4. M-B2 is recorded `EQUIVALENT` rather than forced red. I could have edited production to make
   the named mutant applicable and then "run" it; that would have been a production change
   dressed as a probe.
