# Plan 5 — the two predicates the comments call unproven

```
plan: 5
state: APPROVED — implement r1, 2026-08-19. Closing suite 26 / 2433 / 1
date: 2026-08-19
gate: projection WAIVED — no new mechanism; both before-states measured whole-suite at
      re-review r4 and quoted below
scope: §1C ONLY. §1 and §1B were SET ASIDE by owner decision on 2026-08-19 and now live at
      `docs/architecture/under_construction/set_aside/PLAN_item_economics_deferred_coverage_20260819.md`,
      which also carries N-5 and the two named flaky tests. They are kept below, struck
      through in their headings, so the routing that produced them stays legible — but they
      are NOT this plan's scope and must not be implemented here.
origin: phase 3 re-review r4, H-1
```

## 0. Why the scope narrowed, recorded because it was a judgement

Plan 5 originally carried three unrelated concerns. The owner chose the shortest path to
closed, on a line worth writing down: **§1 and §1B each guard something that is correct today
and that no comment in the tree claims otherwise. §1C does not** — phase 3 shipped two
comments in production code that say, in as many words, that `item_id` and `TaskStep.task_id`
are **NOT proven**. That sentence is honest only until someone makes it false, and it is the
one piece of this project that is actively telling a future reader something it would rather
not have to.

## ~~1. Goal~~ — SET ASIDE, see the scope line above

`app/tests/unit/docs/test_item_economics_handoff_accuracy.py` calls itself *"the accuracy
arbiter for the two frontend handoffs"*. It covers `_OPERATIONAL` and `_CONFIGURATION` — both
dated 2026-08-15. **`HANDOFF_TO_FRONTEND_price_scenario_20260819.md` is outside it.**

The consequence, measured by re-review r2: of the 59 tests under `tests/unit/docs/`, exactly
**one** reads either phase-4 document, and it only asserts one string's absence. So "the docs
guards are green" reported on documents other than the one under review — which is consistent
with r1 finding five nullability defects and r2 finding a sixth in a document that was green
throughout.

This is the most arithmetic-dense handoff this project has produced, and it is the one a
frontend builds a money screen from. It should be under the same arbiter as its predecessors.

## ~~1B. A second, unrelated goal~~ — SET ASIDE, see the scope line above

**Phase 3's review found that a phase-1 domain semantic has exactly one guard in the whole
codebase, and it is in an integration file two layers away.**

`collapse_terms` skips `term.is_deleted is True` (`price_scenario.py:71-72`) — intention §3.1B
and §9A.2. Delete those two lines and run the **whole** non-e2e suite: **exactly one test
reddens**, `test_phase3_c2_deleted_purchase_term_is_ignored_by_admission_and_model`, an
integration row added by phase 3 to guard something else. The domain owner file
`tests/unit/domain/item_economics/test_price_scenario.py` stays **53/53 green**. Measured by
the reviewer and reproduced whole-suite by the coordinator, ID-diffed, one added and none
removed.

So the semantic had **no guard at all** before phase 3, and now has one that is incidental to
it. Rename, narrow or move that row and the semantic silently loses its only test.

**Task:** add a direct row in the domain owner file — a term list containing a deleted
`ITEM_PURCHASE_COST` term, asserting `collapse_terms` ignores it — **or**, if that is judged
disproportionate, a comment at `price_scenario.py:71` naming the integration row as its sole
guard. **Decide and record which.** A direct row is preferred; the comment is the fallback,
and it is strictly weaker because a comment cannot fail.

> **This widens the perimeter from one file to two (or three), and that is recorded
> deliberately.** Plan 5 was scoped to the docs arbiter alone. The reason for folding this in
> rather than opening plan 6: `price_scenario.py` and its domain test are **phase 1's files,
> APPROVED and closed**, so no open plan can reach them, and this is the last plan in the
> project — the alternative is the closeout sweep, where an unguarded domain semantic is
> exactly the kind of item that gets dropped. If the implementer judges the widening wrong,
> **that is a STOP and a report**, not a judgement call.

## 1C. THE SCOPE — two rows phase 3 could not write for itself

Re-review r4 measured all five predicates the two `get_task_price_scenario.py` `WHERE`
comments vouch for, one mutation at a time, whole-suite and ID-diffed. **Three of the five are
asserted by nothing.** One (`TaskStep.is_deleted`) turned out to be redundant with a Python
filter and needs no test — the comment was corrected instead. **The other two need rows, and
phase 3 closed with its comments telling the truth about that rather than hiding it.**

| Predicate | Why nothing catches it | What a regression does |
|---|---|---|
| `ItemValuation.item_id == item_id` | Every fixture holds one item per workspace, so there is never a second item's valuation to return instead | Returns **another item's** current valuation — its price, its colleague's byline — on this item's screen. A wider blast radius than either predicate that *is* proven: those return the wrong row for the right item |
| `TaskStep.task_id == task_id` | All eight `_typical_block` tests use `_TypicalSession`, whose `execute()` discards the statement, so the `WHERE` is never evaluated | Sums **every task's steps in the workspace** into one task's typical time — a wrong break-even, slider domain and suggested price, with no error |

**Task:** two rows against a real session.

1. A second item in the same workspace, each with its own current valuation → assert `saved`
   carries **this** item's. **Named mutation:** drop `ItemValuation.item_id == item_id` → red.
2. A `_typical_block` row that issues real SQL — a second task in the same workspace with its
   own steps → assert the typical reflects only the requested task. **Named mutation:** drop
   `TaskStep.task_id == task_id` → red. **This one cannot use `_TypicalSession`**; that is the
   entire reason the gap exists.

**Both mutations must be measured across the whole suite**, and each row's fixture must make
its own predicate the only reason its outcome holds — the companion to rule 2 that this
project has now spent four rounds on.

**When these land, the two comments must be updated to say so** (`get_task_price_scenario.py`,
comment-only). A comment that says *"item_id is NOT proven"* after a test proves it is the same
defect class in the opposite direction. **That file is phase 3's and closed** — so this is a
declared, comment-only reopening, not a scope drift. If it looks like more than that, STOP.

## 2. Files — exactly two, both §1C's

| Path | |
|---|---|
| `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` | additive — two rows |
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | **comment-only** — the two `WHERE` comments, once the rows exist |

**Set aside and NOT in this perimeter:** `tests/unit/docs/test_item_economics_handoff_accuracy.py`,
`tests/unit/domain/item_economics/test_price_scenario.py`,
`domain/item_economics/price_scenario.py`.

**Nothing else.** Not the handoffs — they are APPROVED text by the time this runs, and a test
that requires changing its subject to pass is a test asserting the wrong thing. **If the
arbiter's assertions fail against the shipped handoff, that is a finding routed back, not an
edit to the document.**

## ~~3. Tasks~~ — SET ASIDE with §1

1. Add `_PRICE_SCENARIO = _HANDOFFS / "to_frontend" / "HANDOFF_TO_FRONTEND_price_scenario_20260819.md"`.
2. Add `_PRICE_SCENARIO_ROUTES = frozenset({"GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario"})`
   and fold it into `_ALL_ROUTES`.
3. Extend the existing parametrisations that take `(document, routes)` and the four-document
   error-identity sweep at `:175` to include it.
4. **Mind `:169`** — `_heading_routes(_CONFIGURATION) | _heading_routes(_OPERATIONAL) == _ALL_ROUTES`
   asserts the union of *headings* covers every route. The price-scenario handoff documents its
   route in §1 prose, not as a `## GET …` heading, so this assertion must either gain the third
   document **or** the new route must be exempted with a stated reason. **Decide and record
   which — do not silently loosen it.**

## 4. Acceptance criteria

**C1–C7 were set aside with §1 and §1B.** They live in the set-aside plan and are not
criteria here.

| C | Criterion |
|---|---|
| C1 | Both rows exist, both against a **real session**, and the `_typical_block` row does **not** use `_TypicalSession` — that fake's `execute(self, _statement)` discards the statement, which is the entire reason the gap exists. |
| C2 | **Named mutation**, at the definition site, whole-suite, both sides computed: drop `ItemValuation.item_id == item_id` → the new item row red. **Before-state, measured twice at re-review r4 (reviewer, then coordinator with a repeat): 0 added, 0 removed.** |
| C3 | **Named mutation**, separately and one at a time: drop `TaskStep.task_id == task_id` → the new typical row red. **Before-state, measured at re-review r4: 0 added, 0 removed.** |
| C4 | Rule 2's companion holds for each row: its own predicate is the only reason its outcome holds. The item row must fail if it reads the *other* item's valuation; the typical row must fail if it sums the *other* task's steps. |
| C5 | Rule 11½: each row that commits owns its teardown in `try/finally`, naming its tables, with residue assertions **outside** it. Copy `test_phase3_c1_…` / `test_phase3_g2_…`, whose shape two review rounds confirmed. |
| C6 | The two `WHERE` comments updated to name the new rows as proof. **A comment still saying "NOT proven" after the proof exists is the same defect in the opposite direction** — and it is the defect this plan exists to remove, so leaving it would make the plan self-defeating. |
| C7 | `ruff check` and `ruff format --check` clean on both files. |
| C8 | Suite **26 / 2433 / 1** — two rows added. Failure IDs **diffed, not counted**; master plan §6 binding, and see §5. |

## 5. Two things that will bite

**The suite has at least two flaky tests, and a single run is not evidence.** Master plan §6
carries 21 observations and two named IDs. If your count disagrees, **repeat and ID-diff before
concluding** — at re-review r4 a coordinator run read 27 on an unrelated shopify flake, and the
immediate repeat came back 26 with the baseline set byte-identical. A single 27 would have been
read as the mutation biting, and the finding would have been wrong.

**`get_task_price_scenario.py` and `test_price_scenario_query.py` are phase 3's files and phase
3 is APPROVED.** This is a **declared, narrow reopening**: two additive test rows and two
comment edits. It is not a licence to revise either file. The production file has had **zero
executable-line changes since `ef55f6d`** across four rounds — C6 must not break that; the
comment edits are comment edits. **If a task appears to need more, that is a STOP and a report.**

## 6. Review log

**No review round was spent, and that is a coordinator decision worth recording rather than
leaving as an absence.**

Every other phase in this project went through at least one review, and every review found
something real. This one did not, for a reason specific to it: **the class this phase belongs
to was already swept.** Re-review r4 measured *all five* predicates in the two `WHERE` clauses
this file contains — that is the whole population, not a sample — and phase 5 closes the two
it found unproven. There is no unswept class left in this perimeter, which is what the r4
sweep would otherwise have been re-run to find.

**What the coordinator verified independently, at consumption:**

| | |
|---|---|
| Perimeter | exactly plan 5 §2's two files, plus the handoff. No third file. |
| Comment-only | `git diff -U0 ef55f6d -- get_task_price_scenario.py` filtered of comments is **empty**, re-run after the coordinator's own edit. Zero executable-line changes in production code, now across **five** rounds. |
| C2 mutation | drop `ItemValuation.item_id` → whole suite **27 / 2432 / 1**, exactly `test_phase5_c2_…` added, none removed |
| C3 mutation | drop `TaskStep.task_id` → whole suite **27 / 2432 / 1**, exactly `test_phase5_c3_…` added, none removed |
| Baseline | **26 / 2433 / 1**, failure IDs byte-identical to the set carried since `ef55f6d` |
| Lint | `ruff check` and `ruff format --check` clean |
| **The count claim** | the `_typical_block` comment says *"the other eight"* drive the fake session. **Verified as eight distinct test functions**, not eight occurrences — counts are one of the two error-prone classes and this project has been wrong about one before. |

**One coordinator correction, applied at the fold.** Both new comments carried an absence
claim scoped to *"the suite"* — *"until it existed nothing in the suite did"* and *"every other
fixture in the suite holds a single item."* Read literally that is false: other test files do
build several items in one workspace. The true and operative claim is about fixtures **reaching
this query**, which is what makes the predicate unobservable. Both narrowed to that.
This is the project's own rule arriving one last time: **an absence claim is only as good as
the scope it names**, earned twice before — once on a directory, once on a term set, and now
on a suite.

**Confirmed and not to be re-raised:** the C2 fixture handles the heap-order trap by insert
order with **no planner GUCs**, and says so at the fixture including that heap order is not a
guarantee; the C3 fixture takes the richer form deliberately, because without real samples both
sections resolve to the zero fallback and `total_seconds` would be 0 under contract **and**
mutant, leaving only `sections_total` to discriminate; both teardowns satisfy rule 11½ with
residue assertions outside the `try/finally`, and both name the complete set of tables they
write. `TaskStep.is_deleted` remains described as defence-in-depth with no test, which r4's N-3
established as the correct outcome rather than a gap.

**The implementer's one self-reported judgement was right.** They first wrote *"no test of it is
possible"* for `is_deleted` and softened it to the measured statement, on the grounds that r4
established it *reddens nothing* and *cannot change a result* — not that no test could exist.
Declining to ship a fresh absolute in the same edit that removes two stale ones is exactly the
discipline this phase is about.
