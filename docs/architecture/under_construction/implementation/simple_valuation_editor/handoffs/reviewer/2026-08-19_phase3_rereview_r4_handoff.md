---
plan: 3
role: review
round: 4
verdict: CHANGES_REQUESTED
date: 2026-08-19
actor: Opus 5 (re-review r4)
---

# Phase 3 re-review r4 — delta-scoped, narrow

**Verdict: CHANGES_REQUESTED.** 0 blocking, 2 should-fix, 6 notes.

**G-1 and G-2 are both closed, and closed well.** Every checkable claim in the new prose
verified — I opened the dataclass and counted, I counted the round trips, I checked the delete
command field by field, I read the index definition, and I re-derived the `can_commit`
conjunct-by-conjunct. All correct. The G-2 row is a good row: all three of its assertions
discriminate independently, including the one nobody had isolated.

**Why not APPROVED.** P1 asked whether `item_id` was still unverified. It is — and so are two
more. I measured all five predicates the two F-1 comments vouch for, whole-suite, one at a time:
**three of the five are asserted by nothing in the codebase, and one of those three is not
load-bearing at all.** That is the G-2 defect three more times, in the same two sentences, found
by running the same probe the coordinator ran one round ago. Approving would apply a weaker
standard to these lines than the coordinator applied to `is_deleted` at r3.

**The fix I am asking for is comment-only and small** — make the two sentences say what is
actually proven. The two missing test rows can go to phase 5; I am not asking for them now.
Three rounds is enough for the *code*, and the code has been right since `ef55f6d`. It is not
enough for a sentence that tells a future reader which lines are safe to delete and is wrong
about three of them.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required.

## 1. Verified perimeter

`git diff --stat ef55f6d..HEAD` and per-commit `git show --stat`:

| Commit | Application files touched |
|---|---|
| `af6589f` (fix r2) | the two allowed files, nothing else |
| `faa7982` (fix r3) | the two allowed files, nothing else |

**No third application file was opened in either round.** Everything else in the range is
pipeline documents plus the two phase-4 frontend handoffs, which belong to `53f6724` (phase 4's
approved close), not to phase 3. Working tree carries only the concurrent owner change — not
reviewed, not touched, not counted.

## 2. E1–E6

| E | Verdict | Independently verified how |
|---|---|---|
| **E1** | **HOLDS** | I ran it myself against `ef55f6d..HEAD` on the **post-reflow** tree: `git diff -U0 ef55f6d HEAD -- get_task_price_scenario.py \| grep '^[+-]' \| grep -v '^[+-][+-]' \| grep -v '^[+-] *#'` → **empty**. Zero executable-line changes in production code across r2 and r3 combined. |
| **E2** | **HOLDS, and the deviation is right** | I read `serialize_task_price_scenario` (`serializers.py:295-314`): `saved_payload` is built wholesale in the `if` and set to `None` in the `else`. A sub-field null check is not merely weaker — it is **unwritable**: `result["saved"]["valuation_id"]` raises `TypeError` when `saved` is `None`. `assert result["saved"] is None` is the strongest available form. Deviation correct. |
| **E3** | **HOLDS** | Coordinator re-measured whole-suite; I did not repeat it (recorded as not-repeated). I did independently isolate the row's third assertion — see N-2. |
| **E4** | **HOLDS** | Confirmed by reading: the G-2 row builds its own token, workspace, user, item and `_scenario_objects()` instance and shares no fixture with C1. Not re-measuring C1's mutation was correct under E4's "if and only if". |
| **E5** | **HOLDS** | `ruff check` → `All checks passed!`; `ruff format --check` → `2 files already formatted`. Run by me on the shipped tree. |
| **E6** | **HOLDS** | My own full run: **26 failed / 2431 passed / 1 deselected** in 132.21 s. The 26 failure IDs are **byte-identical to my own review-r1 set** (`diff` → no output). |

## 3. G-1 and G-2 — both closed

**G-1 — closed.** The clause now reads *"carries item_id and the evaluation result but none of
the objects re-read here — not the Task, the Item, the selection, the terms or the valuation."*
P1 told me to open the dataclass and count rather than trust it, so I did:

- `TaskBudgetStatus` (`get_task_budget_status.py:33-48`) has 14 fields. Exactly **one** is an
  object: `result: ItemCostResult | None`. The clause names it. ✓
- The other 13 are an enum, a `str`, eight `Decimal | None`/`int | None` numerics, and two
  `str | None` ids (`evaluation_id`, `item_id`). **None is an object**, so "none of the objects
  re-read here" survives the fields the sentence does not enumerate. The r2 defect was a
  *false* claim; this is not the same shape. ✓
- The five-item enumeration is **complete for what it claims**. The objects re-read on the
  common branch are Task, Item, selection, terms, valuation — all five named, none carried.
  Two candidates I checked and correctly excluded: `TaskItem` is a local intermediate inside
  `_load_task_and_item` that is never returned by either service, and the `User`/`created_by`
  row is read *only* here — `get_task_budget_status` never loads it — so it is not "re-read".
- **"Roughly eight redundant round trips" is exact, not rough.** `_load_task_and_item` = 3
  (Task, TaskItem, Item); `_current_valuation` = 1; `_load_preview_inputs` = 4 (groups, basis
  versions, cost model versions, terms — `_common.py:172-215`). **3 + 1 + 4 = 8.**

**G-2 — closed, and the row is sound.** Every mechanism claim in its three inline comments
checks out against the code rather than against the sentence:

- *"`delete_item_valuation.py:delete_item_valuation` sets `is_deleted` with `superseded_at`
  still null."* ✓ The command sets **exactly** `is_deleted = True`, `deleted_at`,
  `deleted_by_id` (`:41-43`) — the same three the fixture sets, no field omitted — and it
  *refuses* superseded rows outright (`:37-39`, `ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE`), so
  a soft-deleted row necessarily has `superseded_at` null. The fixture is a faithful post-delete
  state.
- *"reachable from `routers/api_v1/item_economics.py:route_delete_item_valuation`."* ✓ Present
  at `:305`.
- *"`uix_item_valuations_current`'s partial predicate makes the fixture legal."* ✓
  `Index("uix_item_valuations_current", "item_id", unique=True, postgresql_where=text("superseded_at IS NULL AND is_deleted = false"))`
  — an `is_deleted=True` row is outside the index, so a null `superseded_at` is legal.
- *"task ASSIGNED, selection OK, currencies agreeing and no purchase term leave
  valuation-presence as the only false conjunct."* ✓ **This is the one P1 flagged, and it
  holds against `_scenario_objects()`'s actual defaults**, not against the sentence:
  `task_state=ASSIGNED` (and `ASSIGNED ∈ _ADMITTED_STATES`, `commit_item_cost_evaluation.py:60-68`);
  `selection_status=OK` with group/basis/model all set → `selection_ready` True;
  `basis_currency == model_currency == SEK` and the mutant's row is SEK → `currency_agrees`
  True; `with_purchase_term=False` **and** `with_deleted_purchase_term=False` → the purchase
  conjunct is vacuously True. With `valuation is None`, `currency_agrees` is still True
  (`valuation is None` short-circuits its own disjunct). **`valuation is not None` is the sole
  false conjunct.** Exactly as claimed.

## 4. Findings

### H-1 — should-fix — three of the five predicates the F-1 comments call load-bearing are asserted by nothing

P1's third bullet asked about `item_id`. I measured that one and then, because the same
sentence shape appears twice, measured all five. **One mutation at a time** (master plan §5,
*prove each root alone*), each across the **whole non-e2e suite**, each ID-diffed against my own
baseline:

| Predicate | The comment says | Whole-suite result | Reality |
|---|---|---|---|
| `ItemValuation.workspace_id` | redundant, *this line only* | — | ✓ correctly labelled |
| `ItemValuation.item_id` | load-bearing | **26/2431/1 — 0 added, 0 removed** | load-bearing, **unproven** |
| `ItemValuation.superseded_at` | load-bearing | `test_phase3_c1_…` reddens | ✓ proven |
| `ItemValuation.is_deleted` | load-bearing | `test_phase3_g2_…` reddens | ✓ proven (r3) |
| `TaskStep.workspace_id` | redundant, *this line only* | — | ✓ correctly labelled |
| `TaskStep.task_id` | load-bearing | **26/2431/1 — 0 added, 0 removed** | load-bearing, **unproven** |
| `TaskStep.is_deleted` | load-bearing | **26/2431/1 — 0 added, 0 removed** | **not load-bearing at all** |

Three separate full-suite runs, each with a single predicate deleted, each returning the
baseline set unchanged.

**Why nothing catches `item_id`:** every fixture in the suite has one item per workspace, so
there is never a second item's valuation to be returned instead. In production, dropping it
makes `_current_valuation` return *whichever* current, non-deleted valuation the scan reaches
first **in the workspace** — a different item's price and a different colleague's byline on this
item's screen. That is a wider blast radius than either of the two predicates that *are* proven:
those return the wrong row for the right item; this one returns a row for the wrong item.

**Why nothing catches `TaskStep.task_id`:** the eight `_typical_block` tests use
`_TypicalSession`, a fake whose `execute()` ignores the statement entirely and returns
pre-built rows, so the `WHERE` is never evaluated. Dropping it in production sums **every task's
steps in the workspace** into one task's typical time — a wrong break-even, a wrong slider
domain, and a wrong suggested price, with no error.

**`TaskStep.is_deleted` is the interesting one: the comment has it exactly backwards.**
`group_steps_by_section` skips deleted steps in Python (`budget_division.py:118-119`,
*"Collapse non-deleted steps"*), so the SQL predicate cannot change a result — it is a second
line of defence, the same category as the `workspace_id` line the comment's own first clause is
about. `test_c5_deleted_steps_do_not_create_a_participating_section` proves the **Python**
filter, not this predicate; it passes through the fake session and never issues SQL.

This is charter rule 11's *"a comment that asserts a property is a claim"* — the rule this phase
earned one round ago, on this file, in these sentences.

**Verbatim replacement — `get_task_price_scenario.py:75-79`. ⚠ REVIEWER PROSE, UNREVIEWED —
one reader only (me); see §6 lesson 3.**

```python
            # This line only — workspace_id is redundant defence-in-depth: item_id is
            # already resolved workspace-scoped by
            # get_task_budget_status.py:_load_task_and_item, proven by
            # test_price_scenario_query.py:test_c10_task_resolution_is_workspace_scoped_and_hides_deleted.
            # All three below are load-bearing; two are proven. Drop superseded_at and
            # test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain goes red;
            # drop is_deleted and test_phase3_g2_soft_deleted_valuation_is_hidden_from_the_price_screen
            # goes red. item_id is NOT proven — measured whole-suite at re-review r4, deleting
            # it reddens nothing, because no fixture holds two items in one workspace. Drop it
            # in production and this returns another item's valuation: its price, its byline.
```

**Verbatim replacement — `get_task_price_scenario.py:93-97`. ⚠ REVIEWER PROSE, UNREVIEWED.**

```python
                    # This line only — workspace_id is redundant defence-in-depth:
                    # task_id is already resolved workspace-scoped by
                    # get_task_budget_status.py:_load_task_and_item, proven by
                    # test_price_scenario_query.py:test_c10_task_resolution_is_workspace_scoped_and_hides_deleted.
                    # Neither predicate below is proven — measured whole-suite at re-review r4,
                    # dropping either reddens nothing, because every _typical_block test uses
                    # the _TypicalSession fake and never issues this SQL. They differ in what
                    # they do: task_id is load-bearing (without it this sums every task's steps
                    # in the workspace), while is_deleted is defence-in-depth only —
                    # budget_division.py:group_steps_by_section already skips deleted steps.
```

Both replacements are comment-only; E1 is preserved. The two missing rows (`item_id`,
`TaskStep.task_id`) are routed to phase 5 in §5 rather than requested now.

---

### H-2 — should-fix — the corrected claim was never propagated: two live documents still say `TaskBudgetStatus` carries no objects

P3 sent me to `plans/plan_3.md` §6 to check whether the Review log is true of the tree. Its
final paragraph reads:

> **Confirmed by the review and not to be re-raised:** … F9's refusal is correct because
> `TaskBudgetStatus` **carries no objects** …

**That is the exact sentence r3 was spent removing from the code.** It carries
`result: ItemCostResult | None`. The correction landed in `get_task_price_scenario.py` and in
the fix handoff, and never reached the two documents that outlive them.

Grepped from the project root, the live instances are:

| Document | Line | Survives closeout? |
|---|---|---|
| `plans/plan_3.md` §6 Review log | *"carries no objects"* | Yes — moves to `archive/plan_3/` as the phase's durable record |
| `master_plan.md` | `:62` — *"carries `item_id` and no object, so collapsing needs a third file"* | **Yes, and longest of all** — the master plan does not archive with the phase |

`master_plan.md` now contradicts itself two rows apart: `:60` correctly records that
*"carries item_id and no objects"* **was** the G-1 defect, while `:62` still asserts it. A reader
scanning the tracker top-down meets the correction first and the error second.

The remaining hits are **correct as they stand and must not be touched**: my own r1 handoff
(`:250`) quoting the text I proposed, and the `fix_r2` / `fix_r3` / `rereview_r4` prompts
quoting the defect in order to fix or describe it. Those are consumed rows — the charter
forbids rewriting a published handoff, and rewriting them would erase the provenance of the
correction.

**Ownership note:** the false clause originated in *my* r1 replacement text. My r1 handoff's C6
row stated it correctly (`carries item_id: str | None and result: ItemCostResult | None`); the
verbatim comment I supplied lost the qualification, and the compression into the Review log
kept the lossy form. This finding is against my own output, propagated.

**Verbatim replacement — `plans/plan_3.md` §6, final paragraph. ⚠ REVIEWER PROSE, UNREVIEWED.**

```markdown
**Confirmed by the review and not to be re-raised:** F6's block was genuinely dead
(`detached ⟺ item is None`); F9's refusal is correct because `TaskBudgetStatus` carries
`item_id` and `result: ItemCostResult | None` but **none of the objects re-read here** — not the
`Task`, the `Item`, the selection, the terms or the valuation — so collapsing it needs a third
file; `_current_valuation` needs no `ORDER BY` because `uix_item_valuations_current` is a
partial unique index; `can_commit` true under `mismatched` is deliberate and tested; and the
C1 teardown satisfies rule 11½ with the residue block correctly outside the `try/finally`.
```

**Verbatim replacement — `master_plan.md:62`, the clause only. ⚠ REVIEWER PROSE, UNREVIEWED.**

```markdown
F9's refusal is true because `TaskBudgetStatus` carries `item_id` and `result: ItemCostResult | None` but none of the objects re-read at the call site — not the `Task`, the `Item`, the selection, the terms or the valuation — so collapsing needs a third file;
```

Both are coordinator-owned documents; I wrote neither.

## 5. Notes

**N-1 — P3's three Review-log corrections are all true of the tree.** Checked one by one:
(1) the F5 premise — I re-measured the half-up mutation at r1 and confirmed C4 red / C3 green;
the statement *"the pair pins the rounding mode; neither row does alone"* is exact. (2) C1's
second clause is now discharged in the plan, correctly. (3) The F4 fixture-guidance correction
is accurate — the UPDATE order is the mechanism, and F-2's comment now says so at the fixture.
**Only the closing "not to be re-raised" paragraph is wrong, and that is H-2.**

**N-2 — the G-2 row meets the standard C1 was held to, on all four counts P2 named.**
(a) Rule 11½: teardown in `try/finally` naming `item_valuations`, `items`, `users`,
`workspaces`; residue block outside — same shape as C1, correct on the failure path. ✓
(b) Rule 2's companion: I isolated `result["currency"] is None` — the assertion the coordinator
had not — by neutralising the other two and re-running the mutant. It fails on its own:
`assert 'swedish_krona' is None`. **All three assertions discriminate independently**, confirming
the r3 handoff's table rather than taking it. ✓ (c) The `deleted_at`/`deleted_by_id` fixture
matches the command field-for-field (§3). ✓ (d) Four tables are the complete write set: the row
adds only those four, `_scenario_objects()`'s five other ORM objects are never added to the
session so no cascade can reach them, `get_task_price_scenario` is a pure read, and
`grep -rn "listens_for\|event.listen" beyo_manager/models/` finds only two engine-level logging
hooks (`database.py:34,38`) — **no ORM write listener on any of the four**. The new row copied
C1's property, not just its shape. ✓

**N-3 — `TaskStep.is_deleted.is_(False)` is genuinely redundant, and that is worth recording
separately from H-1.** It duplicates `group_steps_by_section`'s Python filter. It is harmless
and arguably good defence-in-depth at the SQL boundary; the finding is only that the comment
calls it load-bearing. Recorded so a future round does not "fix" it by deleting the predicate
instead of the sentence.

**N-4 — the r3 handoff's service-file SHA is pre-reflow.** It records
`b248b3c7…`; the committed file at `faa7982` is `3bdc6403…` (fix r2 at `af6589f` was
`07b7842e…`). The difference is the coordinator's post-handoff reflow of G-1's paragraph, which
the r4 prompt discloses — the ragged short line is gone and the block is flush. **Not a defect**;
recorded because a perimeter reconstruction that trusts the handoff's hash would flag a
phantom change. The test-file hash `c9d59c19…` does match, exactly.

**N-5 — the drifting test: four more observations, all absent.** I ran the whole suite four
times this round (one baseline, three single-predicate mutants), every one **26 failed / 2431
passed / 1 deselected**, and
`test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
appeared in **none** of them. Running tally now **fourteen** observations: implementer r1b 27,
27; everything since 26. The two reds remain the implementer's r1b pair and nothing has
reproduced them. Not touched.

**N-6 — architecture graph: unchanged since review r1, drift confirmed, nothing repaired.**
`archgraph_status` reads **187 nodes / 278 edges / 11 pending / staleNodeCount 1**, revision
`df61961d…` — **byte-identical to my r1 reading**, which confirms the r3 handoff's "0 nodes, 0
relationships, 0 source links" and that no `archgraph_*` mutation was made in either fix round.
The `+1 node / +1 pending` versus the r1b close remains the concurrent owner change
(`domain-purchase-api-sek-price-normalization`), not phase 3. The r3 handoff's routing note is
correct by construction: the new row is inserted at former line 887, **after** the C1 span
`416–448`, so that anchor is unmoved and only anchors below it (`test_c14_…`, `test_c16_…`)
have shifted. Coordinator-owned; I read status and nothing else — no review, promotion,
rejection, edit, maintenance or context write.

## 6. Lessons for the plans

1. **When a comment names N predicates as load-bearing, that is N claims, and each needs its own
   probe.** G-2 tested one of the five and found it hollow; the round stopped there. Three of
   the remaining four were hollow too. **The sweep is for the class, not the instance** — this
   project's own rule, earned at the r1b blocker, and this is the fourth round it would have
   saved. A sentence with a count in it (`the three below`, `the two below`) is a checklist.
2. **A fake session makes a `WHERE` clause untestable, and the tests that look like they cover
   it do not.** Eight `_typical_block` tests pass through `_TypicalSession`, whose `execute()`
   ignores the statement entirely. `test_c5_deleted_steps_…` reads exactly like coverage of
   `TaskStep.is_deleted.is_(False)` and proves a Python filter instead. **Before citing a test
   as proof of a SQL predicate, check that the test issues SQL** — the phase-2 lesson
   *"a file whose every dependency is monkeypatched is a unit test"* has this corollary and did
   not state it.
3. **Verbatim replacement text needs a second reader, and the loop is not yet closed.** r2 and
   r3 were both opened by defects in the previous round's prose; this round's H-2 is a defect in
   *my own* r1 prose that survived two rounds because the correction was applied to the code and
   not grepped for. The existing rule (*"a re-review's scope is the corrections and the
   correcting sentences"*) is right but incomplete: **after correcting a claim in code, grep
   every live document for the old form in the same edit** — the plan's Review log and the
   master plan tracker are the two that outlive the fix handoff.
4. **A Review log entry is a compression, and compression is where qualifications die.** My r1
   C6 row said `item_id` *and* `result: ItemCostResult | None`; the log said "no objects". The
   log is what survives closeout, so it is the copy that most needs the qualification, not
   least.
5. **"Three rounds is enough" is right about code and not about evidence.** The production file
   has been correct since `ef55f6d` — zero executable lines changed in three rounds, which E1
   proves. Every round since has been about whether the file tells the truth about itself. That
   is worth saying in the master plan: **a phase whose fix rounds change only comments is not
   a phase that is dragging; it is a phase whose code was right and whose evidence was not.**

## 7. Carry-forward dispositions

| # | Item | Destination |
|---|---|---|
| H-1 rows | Two missing rows: a second item in one workspace (`item_id`), and a real-session `_typical_block` row with a second task's steps (`TaskStep.task_id`) | **Phase 5.** Not requested this round; the comment fix makes the tree honest without them |
| N-3 | `TaskStep.is_deleted` is redundant with the Python filter | Recorded in H-1's replacement text; no code change |
| N-2 (r1) | `collapse_terms`'s deleted-skip guarded only by an integration row in another layer | **Phase 5**, unchanged from r1 |
| N-4 | r3 handoff's pre-reflow SHA | Coordinator note only; no artifact edit (handoffs are not rewritten) |
| N-5 | Drifting test, 14 observations | **Master plan §6**, coordinator-owned |
| N-6 | Graph anchor drift below the C1 span; staleNodeCount 1 | **Coordinator**, existing pending-review queue |

## 8. Mutation-probe declaration

All probes applied and reverted; both files confirmed **byte-identical to `HEAD` (`faa7982`)**
by SHA-256 after the final revert:

| File | SHA-256 after revert | Matches |
|---|---|---|
| `get_task_price_scenario.py` | `3bdc6403cf4a1641ae2395fae236709ee2c95249034db53d21fe607888588a62` | committed `faa7982` ✓ |
| `test_price_scenario_query.py` | `c9d59c196e2edc1c107ca8ba065f9d28ca1bc1d9ca17623a4a120fb39dc74568` | r3 handoff's ledger ✓ |

Probes run, each singly and reverted before the next:

1. `_current_valuation` — drop `ItemValuation.item_id == item_id`. Focused ×1, **whole suite ×1,
   ID-diffed**.
2. `_typical_block` — drop `TaskStep.task_id == task_id`. Focused ×1, **whole suite ×1,
   ID-diffed**.
3. `_typical_block` — drop `TaskStep.is_deleted.is_(False)`. Focused ×1, **whole suite ×1,
   ID-diffed**.
4. Test file — G-2 row's `saved` and `can_commit` assertions neutralised, combined with the
   `ItemValuation.is_deleted` mutation, to isolate `result["currency"] is None`. Focused ×1.

Four whole-suite runs this round including the baseline, each 26/2431/1.

**State side effects: none.** No `VACUUM` this round. Row state verified after:
`item_valuations` at **1 live row**, and
`select count(*) from workspaces where client_id like 'ws_price_%'` → **0**, so both the C1 and
G-2 teardowns are clean including on the mutated-fail paths they ran on. No Redis, no queue, no
external service. `ruff check` / `ruff format --check` re-run clean after the final revert.

`git status --porcelain --untracked-files=all` after all reverts shows only the three concurrent
owner-change paths — no probe residue.

## 9. Full write perimeter

This session wrote exactly one file:

1. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_phase3_rereview_r4_handoff.md`

No code, no plan file, no master-plan tracker row, no Review log, no architecture-graph mutation
(`archgraph_status` read only).
