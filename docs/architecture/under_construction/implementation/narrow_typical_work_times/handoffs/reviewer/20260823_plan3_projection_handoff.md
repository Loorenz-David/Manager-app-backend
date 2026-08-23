---
plan: plan_3
role: projection
round: 0
date: 2026-08-23
verdict: AMENDMENTS_REQUIRED
actor: Opus 5 (plan-projection, fresh session)
---

# Plan-3 projection — `TaskBudgetStatus` carries the derived spec

## 1. Opening (owner-readable)

Phase 3 is a small, well-shaped change and its production tasks are executable as written.
What is not executable is a **third of its test evidence**: four of the plan's eight named
mutations either point at code that does not exist, or would go off without catching the
thing the criterion was written to catch. I measured each one against the real code rather
than reading the prose, and three of the four are wrong in a way that would have looked
green. One further problem sits in the production tasks: the rule this phase adds — "tell
*no item* apart from *an item with no category*" — is quietly cancelled by a helper the
previous phase already shipped, and the plan's instruction, followed literally, produces
the collapse it exists to prevent.

Nothing here needs the owner. Every row is a paragraph amendment the coordinator can fold
before the implementer prompt is compiled, and I have supplied the exact values and the
corrected mutations so the fold is transcription, not redesign. **Verdict:
`AMENDMENTS_REQUIRED`** — 8 blocking, 7 non-blocking.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. (Two architecture-graph items are already open with the owner from
phase 2; this projection adds no third.)

---

## 2. Gate check

| # | Check | Result |
|---|---|---|
| 1 | master plan §4: phases 1 & 2 `APPROVED`, phase 3 not yet implementing | **PASS** — 1 `APPROVED` 2026-08-22, 2 `APPROVED` 2026-08-23; row 3 reads `PROJECTED` (in flight), i.e. this session. `plans/plan_3.md` header still reads `state: NOT_STARTED`, consistent with "the projection is the transition". |
| 2 | `git merge-base --is-ancestor a2712d3 HEAD` | **PASS** (`HEAD` = `55b404d`; ancestry, not tip, per §3's corollary) |
| 3 | `git status --porcelain` clean but for `?? .archgraph/contexts/` | **PASS** — that one line only |

---

## 3. Decision ledger

Blocking = an implementer would have to stop and ask. Every row names the criterion or task
it attaches to, what cannot be executed, and the correction.

### L1 — **BLOCKING** · task A4 / C5 rows (a) and (c) · *plan gap*

**`derive_spec_from_primary_item(None)` returns `TypicalFilterSpec()`, not `None`.**
`typical_filters.py:71-75` is `getattr(item, "item_category_id", None)` → `None` →
`TypicalFilterSpec()`. So the shipped plan-1 contract (§3.2: "item is None **or**
`item_category_id` is None → empty spec") collapses **exactly the two cases C5 requires to
differ**.

Passing the item through the four call sites (A4) is necessary but **not sufficient**. An
implementer who reads A4 literally — pass the item, call the derive function — gets
`TypicalFilterSpec()` on the no-item path and rows (a)/(c) fail, with the plan, the
intention and the shipped helper all apparently agreeing. The other tempting resolution —
"fix" `derive_spec_from_primary_item` to return `None` for `None` — silently breaks plan
1's shipped contract and is forbidden by §6.1's fold rule.

**Correction (one sentence in §5 task 5, one in C5):** the value carried is
`None if item is None else derive_spec_from_primary_item(item)`, computed at the load site;
`derive_spec_from_primary_item` is **not** changed and keeps its `None → TypicalFilterSpec()`
rule for callers that pass an item they already know exists.

### L2 — **BLOCKING** · task A4 / C5's mutation · *plan gap + free choice*

**The plan never states the new parameter of `_empty_status` / `_build_evaluated_status`** —
name, type, or whether it defaults. That decision changes what C5's named mutation does:

- default `= None` → "stop passing the item at the second `_empty_status` call" yields the
  value `None`, i.e. the plan's stated both-sides;
- **no default** (fail-closed, charter rule 11 — a future fifth call site cannot silently
  drop it) → the same edit is a `TypeError`, and the plan's stated both-sides is false.

**Correction:** declare the signature —
`_empty_status(status, *, binding, item_id, typical_filter_spec: TypicalFilterSpec | None)`
and the same required keyword-only parameter on `_build_evaluated_status`, **no default**
(the default lives on the dataclass, per C1, and nowhere else) — and restate C5's mutation
as a **value** mutation that is well-defined under either choice:
> *Mutation* — `get_task_budget_status_worker.py:48` (call site): pass
> `typical_filter_spec=None`. Contract row (d): `TypicalFilterSpec()`; mutation: `None`.

### L3 — **BLOCKING** · C4's named mutation · *plan gap*

**The mutation reddens the row but cannot catch the defect the criterion names.** Measured:
`derive_spec_from_primary_item` is duck-typed (`getattr`), so deriving "from
`evaluation.item_id`" passes a **`str`**, which has no `item_category_id`, and returns
`TypicalFilterSpec()` — **not** X's category. Two consequences:

1. the plan's *Both sides* ("mutation: it names **X's** (`table`)") is **measurably false**;
2. the mutant's red is identical to the red of "the spec was never derived at all", so the
   row cannot discriminate the historical-binding defect it exists to prove.

**Correction:** the mutation must produce an `Item`, not an id —
> *Mutation* — `_build_evaluated_status` (call site): re-load `Item` by `evaluation.item_id`
> and derive the spec from **that** ORM instance.
> *Both sides* — contract: `frozenset({Y.item_category_id})` (`chair`); mutation:
> `frozenset({X.item_category_id})` (`table`).

### L4 — **BLOCKING** · C6's named mutation · *plan gap*

**The mutation reddens nothing in its declared L2 scope.** Two independent measurements:

- `test_price_scenario_query.py::_run_scenario` **monkeypatches `get_task_budget_status`
  away** (`:559-560` `fake_status` → `SimpleNamespace(status, item_binding)`; installed at
  `:574`). The `mismatched` binding rows (`:777-800`) never execute the mutated function,
  and they assert `item_binding`, `item`, `saved`, `currency`, `model`, `anchors`,
  `domain`, `config_fingerprint`, `typical.sections_total`, `can_commit` — **never
  `item_id`**. Repo-wide: no assertion on `item_id` exists in any of the three consumer
  suites.
- Both `golden_budget_status.json` tasks are `item_binding: "bound"` with `item_id` equal to
  the loaded primary (`itm_live_clock_golden_idle` / `…_frozen`), so `item_id ←
  item.client_id` leaves all three goldens **byte-identical**.

So the "tempting consistency edit" C6 says it guards is, today, **unguarded by every file
C6 names**. The guard the phase actually buys is **C4's own row** (`status.item_id ==
X.client_id` on the `mismatched` fixture).

**Correction:** (i) move the item_id-consistency mutation to **C4**, where the fixture can
see it, and record C4 as its bite; (ii) give C6 a mutation its own named files can see —
the natural one is *"add the field **without** a default"*, which breaks the two
`TaskBudgetStatus(...)` constructions at
`tests/unit/routers/api_v1/test_item_economics_router.py:70` and `:208` (see L10).

### L5 — **BLOCKING** · C3's mutation site · *plan gap*

**"The worker serializer (call site)" does not exist.** There is exactly one budget-status
serializer — `serialize_task_budget_status(status, *, include_monetary)`
(`domain/item_economics/serializers.py:231-276`) — and the worker face is that same function
called with `include_monetary=False` at `routers/api_v1/item_economics.py:146`. As written,
C2's mutation and C3's mutation are **the same edit**, and the plan asserts they bite
different rows.

The distinction the phase actually needs is **placement inside one function**:

- add the key to the **shared `payload` dict** (`serializers.py:245-262`) → it reaches
  **both** faces. *This is literally the "worker inherits a manager change" defect C3 exists
  to catch* — it is C3's mutation.
- add the key inside `if include_monetary:` (`:263-273`) → manager only — C2's mutation,
  which leaves C3(b) green.

**Correction:** restate both as `serializers.py` (definition), distinguished by placement,
and say which rows each bites (C3's mutation bites C2(a), C2(b) **and** C3(b); C2's bites
C2(a) and C2(b) only).

### L6 — **BLOCKING** · C-N1(a) fixture · *plan gap* (this is the row N-c/D27 owed, plus one more)

**(i) The insert-order answer N-c asked for.** Settled on paper:

- `db_session` (`tests/conftest.py:107-110`) yields a session and **rolls back at teardown**;
  the test never commits, so charter rule 11½ is satisfied without an explicit DELETE — say
  so in the plan, so a later round does not add a teardown that cannot run on an aborted
  transaction.
- Order: seed the workspace/task/items/first active primary and **both legal shapes first**,
  flush each; the **violating insert is last**, wrapped in a savepoint so the session
  survives it:
  ```python
  with pytest.raises(IntegrityError):
      async with db_session.begin_nested():
          db_session.add(second_active_primary)   # different item_id — see (ii)
          await db_session.flush()
  ```
  The savepoint rollback leaves the session usable for any assertion after the raise; put
  the legal shapes first anyway, so the row is robust to a later reorder.

**(ii) The fixture defect N-c did not reach — this one makes the row green under its own
mutation.** `task_items` carries a **second** partial unique index,
`uix_task_items_active` on `(workspace_id, task_id, item_id) WHERE removed_at IS NULL`
(`models/tables/tasks/task_item.py:44-51`). If the second active PRIMARY reuses the first
one's `item_id`, the `IntegrityError` comes from the **wrong index**, and the named mutation
(drop `uix_task_items_primary_active`) leaves the row **green** — the exact "fixture
satisfying two independent sufficient causes" shape charter rule 2's companion names.
**The second active primary must name a different item.** Both legal shapes need distinct
`item_id`s for the same reason, except the two *removed* primaries, which are exempt from
both indexes.

**(iii) Rule 12 — three sub-checks, one mutation.** Row (a) asserts a violation **and** two
legal shapes. Dropping the index bites only the violation. Add the second mutation:
*recreate `uix_task_items_primary_active` **without** its `WHERE` clause* → both legal
inserts fail, and nothing else does. And say that the parenthetical `pg_indexes` check is an
**alternative assertion**, not a mutation — as written the plan offers it as one.

### L7 — **BLOCKING** · C-N1(b)'s *Both sides* · *plan gap*

**"Mutation: a different exception type" is false as written.** `add_item_to_task` carries a
**second** pre-check immediately after the primary one — `:59-68`, raising
`ConflictError("Item already active on this task.")`. On a same-item fixture, deleting the
primary pre-check lands on that one: **the same exception type**, a different message. The
row still reddens — but only because the criterion pins the message (S3's rule, correctly
carried), and the plan's stated both-sides misdescribes why.

With L6(ii)'s different-item fixture the mutation reaches the flush and raises
`IntegrityError` exactly as the plan says. **Correction:** state the fixture requirement in
the criterion, and restate the both-sides as *"mutation: `ConflictError` →
`IntegrityError` — and, if the fixture reuses the item, `ConflictError` with the other
message, which is why the message is pinned."*

*Refuted while checking (both were plausible blockers):* the `ConflictError` path returns
before `event_bus.dispatch` (`:94`), so the row needs **no Redis**; and `maybe_begin`
(`services/commands/utils/transaction.py`) runs in **subordinate** mode once the seed has
been flushed, so it neither commits nor rolls back and the raise leaves the session clean.
The seed must be flushed before the call — it must be anyway, for the pre-check to see the
first primary.

### L8 — **BLOCKING** · task A2 vs task A4 · *free choice with one silently-breaking branch*

§5 A2 says the spec is *"computed once … at the load site"*; A4 says *"pass the **item**
through at all four `_empty_status` call sites"*. One reading of "the load site" is **inside
`_load_task_and_item`**, returning a 3-tuple. That branch breaks
`get_task_price_scenario.py:196` (`task, item = await _load_task_and_item(ctx)`) — a file
§4 puts **out of perimeter** — and `test_price_scenario_query.py`'s `fake_task_and_item`
(`:562-563`), which returns a 2-tuple. Both are C6 files; the phase would not close green.

**Correction:** delegate the choice explicitly and close the bad branch —
`_load_task_and_item` **keeps its 2-tuple return**; the spec is computed in
`get_task_budget_status` and `get_task_budget_status_worker`, immediately after that call.

### L9 — non-blocking · C1, C2(b), C3(b) · *values specified as exact and not supplied*

Three criteria demand exactness and supply no literal — the shape that cost phase 1 three
findings. All three are transcribable **now**; measured this session:

**C1 — the fourteen existing names, in order** (`get_task_budget_status.py:38-51`):
```python
["status", "item_binding", "actual_worker_seconds", "actual_worker_minutes",
 "remaining_worker_minutes", "percent_consumed", "variance_worker_minutes",
 "production_budget_minor", "allowed_worker_minutes", "consumed_cost_minor",
 "variance_cost_minor", "evaluation_id", "item_id", "result", "typical_filter_spec"]
```
**C2(b) — the manager payload key set** (14, read off `golden_budget_status.json`):
`{"status", "item_binding", "actual_worker_seconds", "actual_worker_minutes",
"remaining_worker_minutes", "percent_consumed", "variance_worker_minutes", "result",
"production_budget_minor", "allowed_worker_minutes", "consumed_cost_minor",
"variance_cost_minor", "evaluation_id", "item_id"}`
**C3(b) — the worker payload key set** (9):
`{"status", "item_binding", "actual_worker_seconds", "actual_worker_minutes",
"remaining_worker_minutes", "percent_consumed", "variance_worker_minutes", "result",
"allowed_worker_minutes"}`

One correction of form: **C2(b) as written is a disjointness check** ("contains none of
…"), not an exact set — only C3(b) demands the frozenset literal. Master plan §9 ("prefer an
exact literal") applies to both: make C2(b) the exact 14-key frozenset.

### L10 — non-blocking · C6's file list · *plan gap*

Two defects in one sentence. (i) C6 says *"the **three** consumer suites"* and then names
**four** files (rule 2: a sentence with a count is a checklist). (ii) It omits a real
consumer: `tests/unit/routers/api_v1/test_item_economics_router.py` constructs
`TaskBudgetStatus` twice (`:70`, `:208`) and exercises `_run_budget_status` for
worker/seller/unknown roles. It sits **outside** the declared L2 root
(`tests/integration/services/queries/item_economics/`), so a scope stated as that root does
not cover it. Name it in C6, or state that C6's scope is `tests/` for this criterion.

*Refuted while checking:* both constructions are **keyword**, all fourteen fields, so an
appended defaulted field keeps them green — C1's "positional construction anywhere in the
lineage" hazard is a future risk, not a present one. Say so, so the rationale is honest.

### L11 — non-blocking · C2 rows (a) and (c) · *decidability*

**Rows (a) and (c) are one test id.** `test_live_clock_goldens.py:326-332` asserts all three
goldens inside a single loop in `test_prechange_payloads_match_byte_golden_files`, and the
loop short-circuits at the first mismatch (`production_time` is compared first). So "row (c)
does **not** bite on the mutation" is not observable: the moment the serializer mutation is
applied, the one test is red and no row-level attribution is possible.

**Correction:** record (a)+(c) as **one observable with one bite**, and give (b) and C3(b)
their own ids in the new file (they are the rows that can carry independent bites).
*Considered and rejected:* pinning each golden's `sha256` as three separate assertions —
it works, but phase 4 regenerates two of the three goldens (§7 constraint 3), so it plants
the rule-13 time bomb one phase downstream.

Row (c)'s alternative mutation also needs its site: `serialize_task_production_time` is in
**`division_serializers.py:112`**, not `serializers.py`. **Confirmed it would bite** —
`get_task_production_time.py:107` returns that serializer's output and the golden dumps the
query result directly, so the production-time golden does pass through it.

### L12 — non-blocking · C3(b)'s level · *decidability*

C3(b) says *"the worker **route**'s serialized payload"*, but §4 puts the new file under
`tests/integration/services/queries/…`, which exercises services, not routes (a route test
needs the role gate and `build_ok`'s envelope). Since `_run_budget_status`
(`routers/api_v1/item_economics.py:136-146`) is a thin selector, say explicitly that the row
asserts `serialize_task_budget_status(worker_status, include_monetary=False)` — the exact
call the route makes, and the one `test_live_clock_goldens.py:308` already uses.

### L13 — non-blocking · line and count drift · *plan gap*

See §4. Four claims drifted; the corrections are one token each.

### L14 — non-blocking · C1's index base · *decidability*

C1 says "index 13 is `result` and index 14 is `typical_filter_spec`". That is right
**0-based** and wrong 1-based (where 13 = `item_id`). The list literal is the real
assertion, so this is one word — say "0-based".

### L15 — non-blocking · route the amendment forward · *upstream routing*

`test_price_scenario_query.py`'s `fake_status` returns
`SimpleNamespace(status=…, item_binding=…)` (`:559-560`). The **first phase that reads**
`budget_status.typical_filter_spec` gets an `AttributeError` from that fake. Not a phase-3
defect — no consumer reads the field here, and C6 holds — but §9's *"route an amendment to
its consumers, and name them as files"* rule applies: one Read-first line in **plan 4** and
in **plan 5**, naming
`tests/integration/services/queries/item_economics/test_price_scenario_query.py:559-580`.

---

## 4. Reality checks — every plan claim re-derived at source

| # | Claim (plan 3) | Verdict |
|---|---|---|
| 1 | `TaskBudgetStatus` carries **14** fields at `get_task_budget_status.py:38-51` | **CONFIRMED** — exact lines, exact count; list in L9 |
| 2 | §6A A1's "13 fields" is stale | **CONFIRMED** (the intention already carries the correction; the count is 14) |
| 3 | C1: index 13 = `result`, index 14 = `typical_filter_spec` | **CONFIRMED** 0-based (see L14) |
| 4 | `_empty_status` has **four** call sites — `get_task_budget_status.py:121, :132`, `get_task_budget_status_worker.py:38, :48` | **CONFIRMED** — all four addresses exact |
| 5 | `_build_evaluated_status` has **two** call sites | **CONFIRMED** (`get_task_budget_status.py:134`, worker `:53`) |
| 6 | The worker file is **53 lines** and imports both helpers at `:9-14` | **CONFIRMED** (both) |
| 7 | `get_task_budget_status_worker` returns a `TaskBudgetStatus` | **CONFIRMED** (`:22`) — C3(a) is buildable |
| 8 | Plan 1 shipped `TypicalFilterSpec` + `derive_spec_from_primary_item` | **CONFIRMED** — `typical_filters.py:26-68` and `:71-75`; the derive rule is the one that breaks C5 (L1) |
| 9 | The budget-status serializer is a single function in `serializers.py` | **CONFIRMED** — `:231-276`; **but** "the worker serializer" does not exist (L5) |
| 10 | `golden_budget_status.json` unchanged by this phase | **CONFIRMED as achievable** — the payload is built by name, so an appended field cannot move it |
| 11 | The three goldens are byte-asserted | **CONFIRMED, and in ONE test id** (`test_live_clock_goldens.py:326-332`) — L11 |
| 12 | C6's four named files exist under `tests/integration/services/queries/item_economics/` | **CONFIRMED** (all four; the `goldens/` dir is there too, so the stated L2 root does contain the goldens) |
| 13 | `get_task_price_scenario.py:195` calls budget-status and re-loads the item | **CONFIRMED** — `:195` and `:196` |
| 14 | `uix_task_items_primary_active` at `models/tables/tasks/task_item.py:53` | **DRIFTED** — the `Index(` call is `:52-58` (intention F-B's citation is the correct one). The `WHERE` clause matches D27's live-database reading exactly. |
| 15 | The application guard at `add_item_to_task.py:46-57` | **DRIFTED** — `:47-57` (`if request.role == PRIMARY:` is at `:47`) |
| 16 | `ConflictError("Task already has an active primary item.")` | **CONFIRMED verbatim** at `:57` |
| 17 | "No test file in the repository references `add_item_to_task` at all" | **CONFIRMED** — 0 files under `tests/` |
| 18 | §5 task 6: "§6.2's table is **seven** rows" | **DRIFTED** — the table is **six** rows; the worker is the **seventh surface**. Both the intention's §6.2 header and §6A A5 say it that way; plan 3 compresses it into a false sentence. |
| 19 | "**five** construction surfaces" (§1, §6A title) | **NOT DERIVABLE from any measurement.** Measured: 2 construction sites in production (`:85`, `:185`), 4 `_empty_status` call sites, 6 helper call sites, 2 further `TaskBudgetStatus(...)` in `tests/unit/routers/api_v1/test_item_economics_router.py`. Nothing counts to five. The phrase is inherited from §6A and harmless (the tasks work off the measured call sites), but it should not be used as a checklist. |
| 20 | Intention §7's "always-present, non-nullable" wire rule | **CONFIRMED and inapplicable** — it governs *payload* fields; this phase publishes nothing |
| 21 | The new field reaches production-time | **CONFIRMED** — `get_task_production_time.py:48` calls `get_task_budget_status`; nothing reads the field yet, as the plan says |
| 22 | §4's "anything else is a finding" perimeter | **CONFIRMED sufficient** for the production change, given L8's closure of the `_load_task_and_item` branch |

---

## 5. Depth areas — what I refuted

Doctrine: a refuted hypothesis is a result.

1. **"`_empty_status` cannot tell the two cases apart" — REFUTED, and re-aimed.** The call
   sites carry the information already: `:121`/`:38` are on the `item is None` branch and
   `:132`/`:48` hold a live `Item`. The blocker is one layer down — `derive_spec_from_primary_item`'s
   own `None → TypicalFilterSpec()` rule (L1). This matters: the fix is a two-token
   expression at the load site, not a redesign of the helper, and "fix the helper" is the
   wrong repair.
2. **"C2(b) and C3(b) both demand an unsupplied frozenset literal" — HALF REFUTED.** Only
   C3(b) does; C2(b) is a disjointness check. Both are transcribable now — values in L9.
3. **"Can C4's `mismatched` fixture be built?" — REFUTED, it is cheap.** "A **committed**
   evaluation" means `kind = COMMITTED` (`ItemCostEvaluationKindEnum`), **not** a database
   commit — `db_session` rolls back at teardown and nothing in this file needs to commit.
   `test_live_clock_goldens.py::_seed_golden_fixture` is a working template for every table
   involved, and `_load_preview_inputs` (`services/commands/item_economics/_common.py:172-212`)
   degrades gracefully on empty cost configuration, so C5's rows (b)/(d)/(e) need no
   economics seeding either. The only additions are two `ItemCategory` rows
   (`workspace_id`, `name`, `major_category` are the required columns) — `Item.item_category_id`
   FKs to `item_categories.client_id` (`models/tables/items/item.py:30-32`).
4. **"The worker face is under-covered" — REFUTED; it is better covered than the plan
   claims.** `golden_budget_status.json` already contains the **worker** payload
   (`test_live_clock_goldens.py:305-309`), byte-exactly, so C3(b)'s content is guarded today
   and C3 adds an exact key-set literal with its own test id. What is wrong on the worker
   face is the *count* (item 18) and the *mutation site* (L5), not the coverage.
5. **Two C-N1(b) blockers that were not blockers** — Redis and transaction ownership. See
   L7's closing paragraph.

**Confirmed, not refuted:** depth areas 3 (mutation prose that has never been run — three
instances: L3, L4, L7), 4 (blanket claims with one probe — L6(iii) and C5's "each have their
own call-site mutation of the same shape", which L2 now writes out for the one that is
named), 6 (the aborted transaction — settled in L6(i)), and 8 (fixture arithmetic — L4's
all-`bound` goldens and L6(ii)'s wrong-index fixture are both instances).

---

## 6. Criteria decidability summary

| Criterion | Transcribable as written? | Blocking rows |
|---|---|---|
| C1 | **Yes**, once the fourteen names are supplied and the index base is stated | L9, L14 |
| C2 | **Partly** — (a)/(c) collapse to one id; the mutation needs its placement | L5, L9, L11 |
| C3 | **No** — the named mutation site does not exist | L5, L9, L12 |
| C4 | **Fixture yes, mutation no** | L3 |
| C5 | **No** — the value it demands cannot be produced by the instruction it gives | L1, L2 |
| C6 | **No** — the mutation reddens nothing in scope | L4, L10 |
| C-N1(a) | **No** — insert order undetermined **and** the fixture would be green under its own mutation | L6 |
| C-N1(b) | **Yes**, with a corrected both-sides and the fixture requirement | L7 |

---

## 7. Write perimeter (this session)

`git status --porcelain` at session end, on `main` at `55b404d`, read off the command and
not retyped:

```
?? .archgraph/contexts/
?? docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/reviewer/20260823_plan3_projection_handoff.md
```

`.archgraph/contexts/` was already untracked at session start; this session neither created
nor touched it. The second line is this handoff.

- **Written:** this file only — `handoffs/reviewer/20260823_plan3_projection_handoff.md`.
- **Code:** none. **Plans/intention/master plan:** none (projection never edits).
- **Tool-recorded state (archgraph):** none — no `archgraph_*` call was made this session;
  orientation and delta recording belong to implementing sessions (master plan §8).
- **Commands run:** read-only (`git status`, `git merge-base --is-ancestor`, `git log`,
  `cat`/`sed`/`grep`, one `python3 -c` that only *read* `golden_budget_status.json`). No
  test run: this is a paper gate, and every measurement above is a source read, not an
  execution.
- **Baseline:** untouched; no L4 stamp taken or owed by this session.

**L4 runs: 0; tests executed: 0.** No skeleton is attached — it was discarded, per
doctrine; §§3–6 carry only the conclusions it produced.
