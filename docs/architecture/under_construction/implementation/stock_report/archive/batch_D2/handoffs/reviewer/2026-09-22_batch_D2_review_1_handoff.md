---
batch: D2
phases: [13A, 14]
plan: plan_13A.md, plan_14.md
role: review
round: 1
verdict: CHANGES_REQUESTED
state: REVIEWED
date: 2026-09-22
actor: reviewer (Opus, slot `d2r`)
tree: 072c7da (`app/` byte-identical to the implementer's stamp `fcf2fb8`)
---

# Batch D2 review 1 — phases 13A and 14, 42 criterion rows

**Verdict: CHANGES_REQUESTED.** 39 PASS / 3 FAIL / 0 NOT_VERIFIED. One blocking finding, four
should-fix, eight notes. **The production code of both phases is correct everywhere I could reach
it** — every FAIL is evidence weaker than its own criterion cell, which is this project's dominant
defect class for the thirty-first time.

The three failing rows are **13A C5(b)**, **13A C3(a)** and **13A C5(e)**. All of plan 14 passes.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — fix the lock-order hole now, or file it?

**Question.** Finding S3 needs an edit inside APPROVED phase-13 code. Fix it in this batch, file it
as a post-project backlog item, or accept it permanently?

**Story.** Scanner drops a rule at 09:14 and the delete webhook starts removing that board row.
In the same second a worker on the floor assigns a task to the very same row. For about a
millisecond the webhook has already looked up which assignments exist but has not yet locked
anything, so the worker's brand-new assignment slips in behind its back. The webhook still deletes
it — the data ends up right — but to do so it reaches for a lock it promised never to take in that
order. If a third person happens to be deleting an assignment on that same task at that instant,
the database breaks the tie by killing one of the two requests. Scanner retries and nobody notices;
the worker sees a spinner. Over a year of a busy floor this is a handful of retries, not a data
loss.

**Branches.**
- *Fix now* — one re-discovery under the row lock in two files; reopens an APPROVED phase on the
  project's last day.
- *File it* — the window stays; closeout happens today; the item is written down with its measurement.
- *Accept* — nothing is written down, and the next person reads §7 Q1 as true without qualification.

**Recommendation.** *File it.* The state it leaves is correct; only a rare retry is at stake, and
the same shape has been shipping in phase 13 since it was approved — so this batch is not where it
was introduced and not where it should be judged.

**On silence.** The gate holds: I record it as an open finding and neither fix nor close it.

**Trace.** Finding S3; plan 13A §7 Q1; `process_stock_demand_deleted.py` steps 4.6–4.9;
`delete_stock_report_item.py`; `_delete_stock_report_item_cascade.py` block (i).

## 1. Gate check

| Gate | Result |
|---|---|
| Intention `status: RATIFIED` | **PASS** — `planning/intention.md` header, round 9 ratified 2026-09-19, rounds 10/11 additive-and-corrective by owner ruling, status unchanged |
| Plans present, row counts | **PASS** — `plan_13A.md` 37 rows (`grep -c '^| C[0-9]'` → 37), `plan_14.md` 5 (→ 5). 42 in scope |
| Implementer handoff present, tree named | **PASS** — `fcf2fb8` |
| No tester role for D2 | confirmed — `handoffs/tester/` holds C1, C2, D1 only, so the implementer owns the evidence and every `verification` route below is dispatched to the implementer |

## 2. Perimeter

Consumed from the orchestrator (not re-bought): perimeter exact; `_events.py` and
`stock_demand_request.py` clean; `enums.py` carries `StockDemandDeletedOutcomeEnum` only, no
`INLINE_REPAIR_TRIGGERS`; the handoff re-issue is a 100 %-similarity rename with the old file
unedited in `archived/` and `…match_preview_v2…` untouched; plan 14 C2(a) bites under three
independent mutants.

My own cheap confirmation, one command:

```
$ git diff --stat bb704f5..HEAD -- app/
 app/beyo_manager/domain/stock_report/enums.py      |   15 +
 .../routers/api_v1/location_tracker_webhooks.py    |   22 +
 .../stock_report/process_stock_demand_deleted.py   |  266 ++++
 .../stock_report/stock_demand_deleted_request.py   |   93 ++
 .../commands/stock_report/stock_demand_entries.py  |   37 +-
 .../test_process_stock_demand_deleted.py           | 1501 ++++++++++++++++++++
 .../test_process_stock_demand_deleted_locks.py     |  275 ++++
 app/tests/unit/docs/test_stock_report_docs.py      |  411 ++++++
 .../test_location_tracker_webhooks_router.py       |   66 +
 .../test_stock_demand_deleted_request.py           |  123 ++
 10 files changed, 2808 insertions(+), 1 deletion(-)

$ git diff --stat fcf2fb8..HEAD -- app/      # (empty — app/ is byte-identical to the stamp)
$ git diff --stat fcf2fb8..HEAD -- docs/     # plan_13A.md, plan_14.md, the implementer handoff only
```

Exactly the ten files §4 declares, nothing else. The three documents changed after the stamp are
**not** roots of the plan-14 docs guard (`docs/domains/stock_report/`, the current frontend handoff,
the serializers), so the stamped tree and my tree are functionally identical for every test.

## 3. L4 — one stamp, both ID diffs

Authorization (written before the run): **L4 (b), review entry** — my tree (`072c7da`) differs from
the implementer's stamp tree (`fcf2fb8`) by three documents, and the round's deliverable mandates
one L4 with both ID diffs.

```
$ cd app && BEYO_TEST_SLOT=d2r PYTHONPATH=. .venv/bin/pytest -m 'not e2e' -q
23 failed, 3798 passed, 1 skipped, 2 warnings in 77.01s (0:01:17)
```

Tree identity: `072c7da`; `git status --porcelain` shows one untracked file only (this round's
reviewer prompt); `git diff --quiet -- app/` exit 0.

```
$ comm -23 observed.txt baseline.txt     # observed-not-in-baseline
(empty)
$ comm -13 observed.txt baseline.txt     # baseline-not-observed
(empty)
observed: 23  baseline: 23
```

against `handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`. **Both diffs empty.** The
implementer's 23 / 3798 / 1 reconciles exactly on my tree.

**Reported because I could have hidden it:** my *first* L4 attempt added `-p no:logging` to strip
SQLAlchemy noise. That plugin also owns `caplog`, so 37 tests errored with `fixture 'caplog' not
found` and the run read `23 failed / 3761 passed / 37 errors`. 3761 + 37 = 3798. The run above is
the re-run without the flag and is the only stamp I claim. The same flag produced two `caplog`
errors in the L2 probe run in §6; they are the flag, not the tree.

## 4. PASS / FAIL / NOT_VERIFIED — all 42 rows

**Plan 13A (37): 34 PASS, 3 FAIL, 0 NOT_VERIFIED.**

| Rows | Result |
|---|---|
| C1(a) (b) (c) (d) (e) (f) (g) (h) (i) (j) (k) | **PASS** ×11 (notes N1 on (d), N4 on (i)) |
| C2(a) (b) (c) (d) (e) (f) (g) (h) | **PASS** ×8 |
| C3(a) | **FAIL** — S1 |
| C3(b) (c) (d) (e) | **PASS** ×4 (C3(b)'s step clause accepted as declared, implementer F-5) |
| C4(a) (b) | **PASS** ×2 |
| C5(a) | **PASS** |
| C5(b) | **FAIL** — B1 (blocking) + B2 |
| C5(c) (d) | **PASS** ×2 |
| C5(e) | **FAIL** — S2 |
| C5(f) | **PASS** (note N3) |
| C5(g) | **PASS** — positive half armed; the two sorts by §9 rule 9's structural check, settled, not re-opened |
| C6(a) (b) | **PASS** ×2 (note N2) |
| C7(a) (b) | **PASS** ×2 |

**Plan 14 (5): 5 PASS, 0 FAIL, 0 NOT_VERIFIED.** C1(a) C1(b) C1(c) C1(d) C2(a) — notes N5, N6.

## 5. Findings

### B1 — blocking — route `verification` — 13A C5(b)

**The phase's only multi-row gap-close evidence is not determined by its own fixture, and it can
redden a correct tree.**

`test_c5b_two_rows_of_one_group_each_close_their_own_gap` builds `high` = `A1 R2 C3 D4` and asserts
`(await _fresh_row(env.session, row_c)).priority_order == 2` — C was shifted `3 → 2` by R's cascade
*before* its own deletion. That holds only when the cascade loop reaches **R before C**, and the
loop runs in ascending `client_id` (`process_stock_demand_deleted.py` step 11). Nothing in the
fixture pins `row_r.client_id < row_c.client_id`: `_seed_group`'s guard asserts only
`placed != sorted(placed)`, which the two filler rows satisfy on their own, and `_group_arrangement`
orders the *fillers*, never the two candidates.

The plan's own §6 preamble forbids exactly this: *"a row that asserts the loop's order asserts it
against the seeded ids — `client_id` is a ULID with no monotonic counter and is never creation
order (master plan §10)."* Today the row passes because two `_make_row` calls happen to land in
different milliseconds; that is a timing accident, not a fixture.

**Measured.** Probe: swap the two `_make_row` calls so C is minted first, positions and request
order unchanged, with `assert row_c < row_r` added so the probe is decidable.

```
$ BEYO_TEST_SLOT=d2r PYTHONPATH=. .venv/bin/pytest \
    tests/integration/services/commands/stock_report/test_process_stock_demand_deleted.py -q --tb=line
…/test_process_stock_demand_deleted.py:1180: assert 3 == 2
FAILED …::test_c5b_two_rows_of_one_group_each_close_their_own_gap
1 failed, 32 passed in 13.31s
```

Production is correct in both branches (the group ends dense `A1 D2` either way); it is the row's
*expected outcome* that flips. Two consequences: the phase's answer to carried question Q2 rests on
an unstated premise, and the published 23-ID baseline carries a latent flake.

**Correction.** Pin the premise in the fixture — mint both rows, then decide which identity takes
position 2 from the **minted ids** (`sorted()`), the way `test_c5c` already does for `row_x, row_y`
— and assert the premise before the act, as `_seed_group` asserts the `priority_order` /
`client_id` disagreement. The row must also keep a candidate *after* another candidate in the
group, or the "shifted before its own deletion" clause disappears.

### B2 — should-fix — route `plan` — 13A C5(b)'s cell

The cell states `C's deleted row keeps priority_order 2 (it was shifted 3 → 2 by R's cascade before
its own deletion)`. With R and C at positions 2 and 3 and the loop ascending by `client_id`, that
outcome holds only in one of the two id orders; in the other, C keeps 3 and the group is still
dense. The cell therefore names an outcome its own fixture does not determine — the other half of
B1, separated because its fix is a cell edit, not a test edit.

**Correction.** The cell names which candidate the loop reaches first, as a property of the seeded
ids, and states the retained orders for that case.

### S1 — should-fix — route `verification` — 13A C3(a)

**"Every history record of R soft-deleted with NULL author" is asserted for one of the row's three
history records, and the other two are unguarded anywhere in the domain.**

C3(a)'s fixture seeds the group through the phase-12 priority commands, so R carries
`quantity_requested_change`, `priority_change` and `priority_order_change` history records — the
test's own `_goal_record` helper says so in its docstring. `test_c3a` reads only the
`quantity_requested_change` one (`_goal_record` filters on `type`) and asserts `goal.is_deleted is
True`, `goal.deleted_by_id is None`. The cascade is right: it soft-deletes every non-deleted history
record of the row. Nothing observes it.

**Measured.** Probe: add `StockReportHistoryRecord.type == QUANTITY_REQUESTED_CHANGE` to the
cascade's history soft-delete, so the two priority records survive on a deleted row.

```
$ … pytest tests/integration/services/commands/stock_report/test_process_stock_demand_deleted.py -q
33 passed in 13.41s

$ … pytest tests/integration/services/commands/stock_report/test_delete_stock_report_item.py -q
6 passed in 2.18s

$ … pytest tests/integration/services/commands/stock_report/ \
         tests/unit/services/commands/stock_report/ \
         tests/integration/services/queries/stock_report/ -q
495 passed, 2 errors in 22.67s     # the 2 errors are my own `-p no:logging` (caplog), not the tree
```

Scope L2 (the stock-report domain, by import radius of the cascade) because the hypothesis is an
absence claim bounded to the code that writes stock-report history. **No test in the domain
reddens.**

This also answers the multi-row question in §7: history is the one entity class where a multi-row
Scanner delete can leave live child records behind with no instrument watching.

**Correction.** C3(a) reads **all** of R's history records and asserts each is `is_deleted`,
`deleted_at == ctx.now`, `deleted_by_id IS NULL`; the named mutation is the type-narrowing above.

### S2 — should-fix — route `verification` — 13A C5(e)

**The foreign-workspace half of C5(e) cannot fail, and its fixture is not the cell's.**

The cell requires W′ *"seeded with the identical row, group and **six** assignments, untouched"*.
The test uses the `env` fixture's W′, which is `seed_stock_report_workspace` plus one bare
`StockReportItem` (`quantity_requested=10`, `priority IS NULL`, inserted directly, no history) —
**no priority group, no assignments, no goal record**. Against that shape every branch of
`compute_stock_report_divergences` is unconditionally satisfied: counters (0,0,0) with no
assignments; signature computed from the stored normalized properties; `priority`/`priority_order`
both NULL; no groups, so no `order_density`; no `quantity_requested_change` history, so no
`goal_total`; the seeded task has no assignments, so its flag is `False` as expected. There is no
mutation of the delete path that can make `compute_stock_report_divergences(W′)` non-empty.

C5(e)'s **W** half is armed (M36, `recompute_task_stock_flag` skipped, reddens it). The W′ half —
the half carried question (5) exists for — is decoration.

**Correction.** Seed W′ as the cell says: the same row through `AD`, the same group through the
phase-12 commands, the same six assignments through `CR` + the state moves, then delete in W only.
If the coordinator judges that shape unable to discriminate anything after the retirement of the
cell's second mutant (implementer F-3), that judgement belongs in the cell, not in a silently
narrower fixture — reroute to `plan` in that case.

### S3 — should-fix — route `production` — see owner card 1

**The cascade acts on assignments outside the locked set, so the webhook can take a class-3 task
lock after classes 4 and 5 — the inversion §7 Q1 declares impossible.**

Structurally: step 4.6 discovers assignment ids with an **unlocked** `SELECT`; steps 4.7/4.9 lock
exactly those ids and their task ids; but block (i) of `cascade_delete_stock_report_item` re-selects
`WHERE stock_report_item_id == row.client_id AND is_deleted = false` — the live set at that moment,
not the locked set — and calls `remove_assignment`, which calls `recompute_task_stock_flag`, which
issues `UPDATE tasks …` (`_task_flag.py:set_task_stock_flag`).

Reachable because `create_stock_task_assignments` takes **2 items → 3 tasks → 4 rows** and does
*not* take the class-1 advisory lock:

```
$ grep -rn "acquire_stock_report_order_lock" app/beyo_manager/
… set_stock_report_item_priority.py, set_stock_report_item_priority_order.py,
… delete_stock_report_item.py, process_stock_demand_deleted.py, repair_stock_report.py  (+ the definition)
```

Timeline: the webhook holds the advisory lock and has done step 4.6 (finding, say, no assignments);
a creator session takes items → task T2 → row R (R is not locked yet), inserts an assignment on
(R, T2) and commits; the webhook then locks R, locks nothing at class 3 or 5, and its cascade finds
the new assignment and updates T2 — acquiring class 3 while holding class 4. A concurrent
`delete_stock_task_assignments` holding T2 and waiting on R closes the cycle → `40P01`, one side
aborts. Q1's premise ("every path that soft-deletes a row holds the advisory lock first") covers the
live set **shrinking**; nothing covers the assignment set **growing**.

**Measured** (that the cascade is independent of the locked set): probe — force step 4.6 to discover
nothing, so no class-3 and no class-5 statement is issued at all.

```
$ … pytest tests/integration/services/commands/stock_report/test_process_stock_demand_deleted.py -q --tb=line
…/test_process_stock_demand_deleted.py:1201: assert 0 == 1
FAILED …::test_c5b_two_rows_of_one_group_each_close_their_own_gap
1 failed, 32 passed in 13.31s
```

C3(a) (six assignments on six tasks), C3(b), C3(d), C4(b) and C5(e) all stay **green** with no
assignment or task lock held: the cascade removed all six assignments and cleared all six task flags
outside the locked set. Only C5(b)'s `record_statements` clause notices, and only by counting.

**Not introduced by 13A.** `delete_stock_report_item.py` (APPROVED phase 13) has the identical
shape — unlocked assignment discovery, class-3 over the discovered task ids, the shared cascade
re-selecting. 13A generalizes it to several rows and restates the "no cycle" claim in §7 Q1.

**Correction, if the owner says fix.** After the class-4 lock, re-run the assignment discovery under
the row lock; either extend the class-3/class-5 lock statements to the re-discovered set before the
first cascade, or fail closed with the same `RuntimeError` shape as step 4.10 when the re-discovered
set differs. On the empty-candidate shapes the re-discovery is skipped, so C5(d)'s exact counts of
5 and 4 are unaffected.

### Notes

- **N1 — 13A C1(d).** The cell says `422; nothing written`; the row is discharged by a unit test
  with no database, so the write half is not asserted. The class is covered by C1(j)/C1(k), which
  do assert the live row survives a parse refusal. No action needed beyond the record.
- **N2 — 13A C6(a), C6(b).** §6's preamble makes `assert_stock_report_clean(session, W)` standing
  for every non-drift row. C6(a) has neither it nor `_assert_foreign_untouched`; C6(b) has the
  foreign check only.
- **N3 — 13A C5(f).** The cell says "the foreign counts unchanged"; the test asserts the foreign
  `stock_report_items` count only, not the other three tables.
- **N4 — 13A C1(i).** The folded cell now reads `"quantityRequested": "seven"`; the integration test
  still sends `5` and, as the implementer measured and declared (F-2), cannot fail under the cell's
  own mutation. The unit half carries `"seven"` and is what arms the row. The cell and the
  integration test now disagree — worth one line in the cell so the next reader is not misled.
- **N5 — 14 C1(b).** `_event_names_in_code()` scans `_STOCK_COMMANDS.glob("*.py")`, which is **not**
  recursive, while the stated root is "every `event_name=` site **under**
  `bm/services/commands/stock_report/`". Verified harmless today: the only subpackage is `requests/`
  and it builds no event name (`grep -rn "event_name=" …/stock_report/` returns four sites, all at
  the top level). `rglob` would make the root match its own description.
- **N6 — 14 C1(b), C1(c).** C1(a) pins `len(routes) == 13` and C1(d) pins `len(states) == 6`, so
  neither can go vacuous. C1(b) and C1(c) have no such guard: if the event-name scan or the
  `STOCK_REPORT_[A-Z_]+:` identity regex ever returned the empty set, both loops would pass over
  nothing. Verified non-empty on this tree (13 documented paths, 4 error classes). L-15/L-26 shape.
- **N7 — implementer handoff §6 arithmetic.** "C5 10 (a 1, b 3, c 1, d 1, e 2, f 1, g 2)" — the
  parenthetical sums to 11. The total 10 is right *after* C5(e)'s second mutant is retired (F-3);
  the parenthetical counts the runs, the total counts the declarations. The 54-row ledger and
  "declared 50 / executed 54" both reconcile against the table; the ledger's ID sequence has gaps
  (no M27–M29, M32, M37) which are numbering only, not missing rows.
- **N8 — my own `-p no:logging` error**, recorded in §3.

## 6. What I verified correct, specifically

- **The command's step list is task 3's, in order**: deadline on the first line; verify before parse
  (C1(c)'s 401-not-422 is a real ordering claim, and M2 bites); the X3 guard; `set_config` as the
  first statement inside the block; the advisory lock **before** discovery; tasks → rows+groups →
  assignments; the re-read guard; the ascending-`client_id` cascade loop; the deadline check as the
  last action inside the block.
- **`_lock_rows_and_groups` really is one statement per class for any number of candidates.** The
  group predicate is a subquery inside the class-4 statement, and C5(b) measures the four counts
  under `record_statements`. I checked the two-group case by reading C5(c): two candidates in two
  different priorities make the subquery return two rows, and `IN (SELECT …)` handles it.
- **`ctx.workspace_id` is never read** — the workspace comes from the verifier and is passed
  explicitly to every subordinate; M26 arms it and the mutated value is genuinely `""`.
- **Duplicate candidates cannot arise.** `item_category_key` is `raw.strip().lower()`, and
  `resolve_categories_for_entries` keys resolution by that key, so two distinct keys can never
  resolve to one category id; C1(j) refuses same-key duplicates at parse. `sorted(set(...))` is
  defensive, not load-bearing.
- **The coalescer's `:deleted` rule holds across rows.** In C5(b), C's `:updated` (from R's gap
  close) and R's three `remove_assignment` `:updated` events are all dropped, D's last `:updated`
  survives with `priority_order 2`, and the row asserts the whole list as a multiset with per-name
  counts (L-46 satisfied: `sorted(names) == sorted([...])`, not a subset).
- **Counters in a multi-row delete are covered, indirectly but really.** `assert_stock_report_clean`
  asserts **zero repair records**, and the cascade writes a repair record for any counter that is
  non-zero when its assignment loop ends — so a per-row counter error in a two-row request surfaces
  as a record and reddens C5(b) and C5(c).
- **Plan 14's guard roots are stated in the module docstring and are the real ones**: the app's own
  route table through `create_app()` with `require_roles([...])` resolved through
  `routers/utils/roles.py` (L-38 satisfied — no string-literal grep), §6.7 plus the AST scan of
  `event_name=` sites with the assignment template expanded, the error classes and
  `STOCK_REPORT_*` identities, the state enum, and the serializers resolved to their mapped
  columns' `nullable`.
- **Plan 14 C2(a) is a real equality check with a discriminator.** `documented == shipped` per
  serializer, plus `test_c2a_at_least_one_field_of_each_kind_exists_to_discriminate`, which is the
  L-26 positive observation C1(b)/C1(c) lack. The four serializers resolve cleanly because every
  parameter name is in `_SERIALIZER_MODELS`; sub-shapes (`item`, `task`, `item_images`) are skipped
  by design and the handoff documents `item_images` in prose beside the table, so the equality is
  not silently forcing an incomplete document.
- **Arithmetic.** 37 + 5 = 42 rows. 31 + 2 + 6 + 8 = 47 test functions expanding to
  33 + 2 + 6 + 13 + 2 (router) = 56 ids, which is the L4's +56 pass delta exactly.
- **Trace chain, both directions.** Every test in the five files maps to a row; no orphan test; no
  candidate criterion proposed and none owed.
- **Settled items, not re-opened:** C5(b) mutant (i)'s retirement and the cascade's fresh `SELECT`;
  C5(g)'s two sorts; card D-3; the `_events.py` probes (I confirmed `git diff --stat fcf2fb8..HEAD
  -- app/` is empty, so both probes were reverted).

## 7. The multi-row-delete question, answered

**Yes — one: the history records of the rows deleted in a multi-row request. Nothing else.**

I took the four surfaces the prompt named across a two-row request (C5(b)'s shape) rather than one
row at a time:

| Surface | Multi-row state | Asserted by |
|---|---|---|
| **Counters** | each candidate zeroed by its own cascade; drift on any of them writes a repair record | **yes**, indirectly but soundly — `assert_stock_report_clean`'s zero-repair-record clause in C5(b) and C5(c) |
| **History records** | every non-deleted history record of each candidate is soft-deleted with NULL author | **NO** — only the `quantity_requested_change` record of one row, in C3(a). Finding **S1**; measured green across 495 domain tests with the other two types left live |
| **Events** | exact multiset, per-name counts, the `:deleted` rule applied across rows, `workspace_id` on every event | **yes** — C5(b) and C3(d), as multisets, L-46 satisfied |
| **`assert_stock_report_clean`** | runs after both C5(b) and C5(c) | **yes** — but note it only inspects **live** rows, so it cannot see a deleted row's own residue; that is why S1 is invisible to it |
| **Group ordering** | each cascade closes its gap against the previous one's positions | **yes in code, not in evidence** — finding **B1**: the assertion's expected value depends on an unpinned id order |
| **Locks** | class 3 can be taken after class 4/5 when the assignment set grows mid-request | finding **S3** |

Everything else I looked for came back clean: no cross-row bleed in the counter self-heal (it reads
and writes by `row.client_id`); no coalescer leak (a group row shifted twice keeps only its last
`:updated`, compared against the pre-lock snapshot of **all** locked rows including group members);
no goal-record interference (each row's goal is keyed by its own history record id); and a deleted
row correctly leaving `compute_stock_report_divergences`'s scope rather than being reported as
drift.

## 8. Mutation-probe declaration

Three probes, each applied and reverted in the same act; `git diff --quiet -- app/` exit 0 verified
after each, and `git diff --stat fcf2fb8..HEAD -- app/` is empty at the time of writing.

| Probe | File touched | Purpose | Reverted |
|---|---|---|---|
| P1 | `app/tests/integration/services/commands/stock_report/test_process_stock_demand_deleted.py` | swap the two `_make_row` calls in `test_c5b` (fixture permutation) | `git diff --quiet -- app/` exit 0 |
| P2 | `app/beyo_manager/services/commands/stock_report/_delete_stock_report_item_cascade.py` | narrow the history soft-delete to `QUANTITY_REQUESTED_CHANGE` | `git checkout --`, then `git diff --quiet -- app/` exit 0 |
| P3 | `app/beyo_manager/services/commands/stock_report/process_stock_demand_deleted.py` | force step 4.6's assignment discovery to return nothing | `git checkout --`, then `git diff --quiet -- app/` exit 0 |

**Database and state side effects:** none of mine. Every probe ran through pytest on
`BEYO_TEST_SLOT=d2r`; the tests own their teardown (`purge_stock_report_workspace`, and C2(f)'s own
`finally`). No manual DML, no schema change, no migration, no archgraph write (nothing recorded,
nothing promoted, nothing rejected). No test ran concurrently with another at any point (L-50).

## 9. Carry-forward dispositions

Not applicable in the usual sense — the verdict is CHANGES_REQUESTED, so nothing is carried past an
approval. For the fix round:

| Item | Route | Destination |
|---|---|---|
| B1 | verification | implementer (D2 fix 1) — must be fixed for approval |
| B2 | plan | coordinator — cell edit, before the fix prompt is compiled |
| S1 | verification | implementer (D2 fix 1) |
| S2 | verification | implementer (D2 fix 1), or coordinator if the cell's W′ shape is judged undiscriminating |
| S3 | production | **owner card 1** — fix now / file / accept |
| N1 N2 N3 N4 | verification / plan | implementer and coordinator, cheap; fold with the fix round |
| N5 N6 | verification | implementer (D2 fix 1), one-line each |
| N7 | plan | coordinator — handoff arithmetic, record only |

## 10. Lessons for the plans

1. **"Not sorted ascending" is not "ordered against the key".** `_seed_group`'s guard
   (`placed != sorted(placed)`) is satisfied by any one inversion anywhere in the group, so a
   four-row fixture can pass it while the two rows the criterion is *about* sit in ascending order.
   A group guard has to pin the pair the row depends on, not the list.
2. **A criterion whose outcome depends on a ULID order must say which order, and the fixture must
   produce it by procedure.** §6's preamble already says this for the `priority_order` /
   `client_id` disagreement; C5(b) shows the same rule is needed for the *cascade loop's* order,
   which the preamble mentions in one sentence and no row enforces. L-14's next instalment.
3. **"Every X" in a cell needs a fixture with more than one X and an assertion that counts them.**
   C3(a) says "every history record"; the fixture has three kinds and the test reads one — and the
   helper that reads it documents the other two in its own docstring, which is as close to a warning
   as a codebase gets.
4. **A foreign-workspace control is only a control if it holds the shape under test.** C5(e)'s W′
   was specified correctly and built as a bare row; the cell and the fixture drifted apart with
   nothing to notice.
5. **An unlocked discovery that decides which ids to lock must be re-validated under the lock, or
   the lock set is a claim about a past moment.** §9 rule 4 ("unlocked discovery decides only which
   ids to lock") is sound for *rows*, where Q1's advisory lock closes the window; it is not sound
   for *children* that another path may add. Worth stating in MC-1 rather than per phase.
6. **A docs guard that pins a count cannot go vacuous; one that does not, can.** C1(a) and C1(d)
   carry `len(...) == n`; C1(b) and C1(c) do not. Cheap to make uniform.
