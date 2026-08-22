---
plan: 2
role: review
round: 1
verdict: APPROVED
date: 2026-08-19
actor: Opus 5 (review r1)
---

# Phase 2 review r1 — the price-scenario read model, serializer, route and mirror

**Verdict: APPROVED.** 0 blocking, 1 should-fix (a record correction, routed to the
coordinator, not the implementer), 11 notes.

Phase 2 holds. Every mechanism this phase ships was re-derived against its semantic
authority and then attacked: **34 mutations applied to the shipped code, one at a time,
each file run whole, each reverted and hash-verified**. **27 reddened a test.** Of the seven
that did not: two were not real mutations (an enum `is` → `==` that is equivalent for enum
members, and a `sections_total` form superseded by a sharper probe that *did* redden), one is
provably dead code (F6), and **four are genuine coverage gaps** — F4, F5 and F8 ×2. None of
the seven is a wrong value: no mutation produced a wrong-but-green payload, and none of the
four gaps hides a defect in the shipped code.

The one measurable discrepancy is in the implementer's mutation ledger, not in the code: the
single named mutation reddens **two** tests across two files, not the one recorded — phase
1's F2 in the new shape the coordinator predicted, now measured across the whole suite.

Suite re-measured independently from `backend/app/` with
`PYTHONPATH=. pytest -m 'not e2e'`: **2425 passed / 26 failed / 1 deselected** in 115.83s,
matching the expected figure exactly; the 26 failure IDs are byte-identical to the
implementer's inherited set, so no repeat run was required.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Correct two drifted evidence spans on the new graph nodes, and add the sibling `implements` edge?

**Question.** Re-record the price-scenario projection's two evidence spans and add
`source-file-item-economics-price-scenario --implements--> projection-…-task-price-scenario`?

**Story.** Ask the graph in six months "what proves the twelve-status branch" and it points
you at lines 405–429 of the integration test. Line 405 is the right test — but its twelve
rows sit at 387–404, outside the span, and 422–429 are a different test's decorators. The
projection's own service span stops two lines before the function's closing bracket. Nothing
is broken today; the reader is simply aimed slightly off, toward the wrong test.

**Branches.** Re-record → the graph points at what it describes, one coordinator session.
Leave → the drift compounds as the files grow, and the nodes stay pending.

**Recommendation.** Re-record both spans and add the `implements` edge in one review-path
batch: the sibling pattern (`budget_division → production-time`) is unambiguous and the two
spans are provably wrong against the files at head.

**On silence.** Nothing breaks and the gate does not hold; the nodes stay `ai_inferred`.

**Trace.** `projection-item-economics-task-price-scenario` (both source links + evidence),
`source-file-item-economics-price-scenario`. See F7.

---

## Findings

### F1 — should-fix — the mutation ledger's observed-red set is one test; it is two

**What is wrong.** The r1c handoff's ledger records the observed-red set for
`max(1, quantity) → max(6, quantity)` at `price_scenario.py:slider_domain` as
`test_quantity_zero_falls_back_to_a_divisor_of_one` only, "52 other tests passed",
measured by running `tests/unit/domain/item_economics/test_price_scenario.py` whole.

**Measured true set.** Mutation applied at the definition site, **whole non-e2e suite** run
(2423 passed / 28 failed / 1 deselected, i.e. the inherited 26 plus exactly two):

```
tests/unit/domain/item_economics/test_price_scenario.py::test_quantity_zero_falls_back_to_a_divisor_of_one
tests/integration/services/queries/item_economics/test_price_scenario_query.py::test_c16_discriminating_literal_is_exact
```

Set-diffed against the unmutated run: two IDs added, none removed, nothing else in the
suite moved.

**Violated authority.** Master plan §5, *"a mutation ledger's observation is a property of
the whole file, not of the test you were watching"* — the observation was whole-file, but
the same literal is asserted in a **second file** (`test_price_scenario_query.py:731`), so
whole-file is no longer the right unit. The rule needs widening; see lesson L1.

**No code defect.** The understatement is in the safe direction: the guard is stronger than
recorded, not weaker. C16(a) is satisfied twice over.

**Suggested correction.** The coordinator corrects the ledger row at the closeout fold —
either to the two-test set above, or (if F2 is resolved by deletion) the row becomes correct
as written. **Routed to the coordinator, not the implementer**: the correction is one table
cell in a consumed handoff and touches no code or test. This is why it does not hold the
gate.

### F2 — note — the C16 literal is asserted in two files; the duplicate is what broke the ledger

`plan_2.md` §2 exception 1 authorised **replacing** the inert assertion in
`test_price_scenario.py`. That was done exactly (`:379-386`, inert equality → exact
`SliderDomain(110, 3_080, 12_100)` literal, verified in the diff — one assertion, nothing
else in the file moved). `test_c16_discriminating_literal_is_exact`
(`test_price_scenario_query.py:731`) is an **additional** copy of the same assertion on the
same function, in an authorised file — so not a perimeter breach.

**Judgment: it does not earn its place.** It adds one thing over the unit copy — that the
query-service module binds `slider_domain` from the right module — which is already implied
by every anchors assertion in the same file. Against that it costs two things: it splits
ownership of a guard the plan deliberately placed in one file, and it is the direct cause of
F1. It also carries `@pytest.mark.integration` while opening no session and touching no
database.

**Suggested correction.** Delete it and let `test_price_scenario.py` own the guard, which
also makes F1's ledger row correct as written. Coordinator's call.

### F3 — note — `_has_purchase_term` ignores `is_deleted`; `collapse_terms` does not

`get_task_price_scenario.py:63-68` tests every term in the list; `collapse_terms`
(`price_scenario.py:71-72`) skips `is_deleted is True`. Both consume the **same** `terms`
list in the same call.

**Violated authority.** Intention §3.1B and §9A.2 both scope the purchase term to
*non-deleted* rows.

**Unreachable today**, which is why it is a note: `_load_preview_inputs`
(`_common.py:207-215`) filters `CostModelTerm.is_deleted.is_(False)` in SQL, so a deleted
term never reaches either function. Probe confirms no test distinguishes the two forms.

**Failure it would produce** if a future caller ever passes unfiltered terms: `can_commit`
would demand a purchase cost for a term the model correctly ignores — `false` on a button
whose press would in fact have succeeded.

**Suggested correction.** Mirror `collapse_terms`' guard: skip `term.is_deleted is True`.

### F4 — note — M4's "current valuation" predicate is asserted by no test in either phase

`_current_valuation` (`:71-79`) filters `superseded_at IS NULL AND is_deleted = false`,
exactly as §6B requires and as `_load_current_valuation` and
`write_item_valuation_chain_in_session` do. **Probe: deleting `superseded_at.is_(None)`
leaves the entire phase test file green** — no fixture builds a supersession chain.

**Violated authority.** None — the code is correct. The gap is in the criteria: C7 covers
M4's *absence* rows only, and §6B's resolution predicate has no criterion in plan 1 or plan 2.

**Failure it guards.** The byline and the saved price would be read from an arbitrary
historical chain row: a stale price under the wrong person's name, with no error.

**Suggested correction.** A criterion in the closeout phase: two chain rows for one item,
one superseded, asserting `saved.valuation_id` is the current one.

### F5 — note — the per-section quantisation's rounding *mode* is unguarded

C4's fixture (usable typicals `10, 11` → median `10.5`) yields `41` under half-even **and**
under truncation, because `10.5` rounds to the even `10` either way.

- **Probe — truncation** (`int(resolved)` in place of `round_half_even(...)`): **no test
  reddened.**
- **Probe — half-up**: C4 red. **Probe — quantise the sum instead of each section**: C4 red.

So C4 proves *per-section vs sum* quantisation, which is what it was written for, but not
half-even vs truncation, which §5.3A also contracts.

**Suggested correction.** Add usable typicals `{11, 12}` (median `11.5` → half-even `12`,
truncation `11`) alongside the existing pair.

**Contained impact**: at most 0.5 s per substituted section against a display quantised to
whole minutes — which is why this is a note, not a defect.

### F6 — note — the `detached` `can_commit` override is dead

```python
if budget_status.item_binding == "detached":
    can_commit = False
```

`detached ⟺ item is None` (`get_task_budget_status.py:111`), and `can_commit` already
requires `item is not None` (`:185`). **Probe: removing the block reddens nothing**, and it
provably cannot: the two predicates are the same fact. It is harmless and it documents
§9.2A's row, so removal is optional — but as written it reads like a live guard.

**Suggested correction.** Keep it with a one-line comment naming it as belt-and-braces for
§9.2A, or drop it.

### F7 — note (→ card 1) — two graph evidence spans are wrong; one sibling edge is missing

Re-anchored against the files at head:

| Recorded | Actual | |
|---|---|---|
| `get_task_price_scenario.py:get_task_price_scenario` **149–271** | function is **149–273** | stops two lines inside the closing `return` |
| `test_price_scenario_query.py:test_c1_status_matrix_has_twelve_exact_rows` **405–429** | def+body is **405–419**; **422–429** are the *next* test's decorators; the twelve-row `parametrize` table the summary describes is at **387–404** | overruns into an unrelated test **and** excludes its own evidence |
| `item_economics.py:route_get_task_price_scenario` 385–396 | 385–396 | ✓ exact |
| `test_item_economics_router.py:test_price_scenario_route_mounts_…` 147–153 | 147–153 | ✓ exact |

**Type and naming are correct.** `projection` / `endpoint` and the ids
`projection-item-economics-task-price-scenario` /
`endpoint-item-economics-task-price-scenario` match the sibling family
(`…-task-production-time`, `…-task-budget-allocations`) exactly, as do the tags and the
`accepts` direction. Not reusing `source-file-item-economics-price-scenario` for the new
query service was right — that node is contracted as the *pure* module and its description
turns on having no session.

**Missing edge.** The sibling pattern is
`source-file-item-economics-budget-division --implements--> projection-…-task-production-time`.
The price-scenario projection consumes `price_scenario.py` in exactly that relation and has
no such edge.

**I promoted, rejected and edited nothing.** All nine items remain pending; the graph is at
revision `ea100e05…`, 186 nodes / 277 edges / 0 diagnostics / 0 stale, unchanged by this
session.

### F8 — note — the "integration" file is fake-driven, and the two new workspace predicates are unexercised

Eight of the file's thirteen test functions run through `_run_scenario`, which monkeypatches
`get_task_budget_status`, `_load_task_and_item`, `_current_valuation`, `_load_preview_inputs`
**and** `_typical_block`. Only `test_c10_…` opens a session. The `_TypicalSession` /
`_UserSession` stand-ins ignore the statement entirely.

**Measured consequence.** Probes: dropping `TaskStep.workspace_id == ctx.workspace_id` from
`_typical_block`'s select → **no test reddened**; dropping
`ItemValuation.workspace_id == ctx.workspace_id` from `_current_valuation` → **no test
reddened**.

**Why this is a note and not a should-fix.** Both predicates are present and correct by
reading, and both are *redundant*: `task_id` and `item_id` are resolved workspace-scoped
upstream by `_load_task_and_item`, and client_ids are prefixed ULIDs. The endpoint's real
tenant boundary is that resolution, and C10 covers it with three rows against a live
database, including the cross-workspace row. Verified structurally rather than behaviourally,
per doctrine 3.

The fixtures do respect rule 3 where it bites: real `Task`, `Item`, `ItemValuation`, `User`,
`CostModelTerm`, `ProductionCostBasisVersion` and `EconomicsSelection` objects throughout,
never hand-built dicts.

### F9 — note — the task, item and configuration are each loaded twice per request

`get_task_price_scenario` calls `get_task_budget_status(ctx)` (which itself runs
`_load_task_and_item`, and on the no-evaluation branch `_load_preview_inputs` **and** the
current-valuation select), then repeats `_load_task_and_item` at `:153`, the valuation at
`:161` and `_load_preview_inputs` at `:166`. On the common branch — a task with no committed
evaluation, which is the state this screen exists to resolve — that is roughly eight
redundant round trips per open.

Correctness is unaffected (D-6 chose `get_task_budget_status` deliberately, and reusing it is
what keeps the status, binding and tenant boundary identical to the other screens). Passing-
glance clause; route to the closeout phase or accept.

### F10 — note — `test_c16_reciprocal_comment_pairs_are_present`: the form, judged

**It works.** Probed each of the four comments **alone**, deleted, file run, reverted,
hash-verified: all four turn the test red individually. "Prove each root alone" satisfied —
no single deletion hides behind another.

**The form's trade.** A substring assertion against module source is brittle one way (a
reworded comment reddens a test in a file nobody associates with comments) and blind the
other (a correct comment in the wrong function still passes). Here the trade is **right**:
what is being protected *is* a pointer string, so pinning the string is the direct
expression of master plan §4's sanction condition, and placement is not what a later
consolidation depends on. Worth recording only so the next author knows the comment text is a
fixed token, not prose.

### F11 — note — C2's `no_primary` and `deleted_item` rows are one fixture wearing two names

Both set `with_item=False`; §9A.2's conditions 3 (no active PRIMARY `TaskItem`) and 4 (its
`Item` row deleted) are distinct in `commit_item_cost_evaluation`, but `_load_task_and_item`
collapses both to `item is None`, so **they cannot be separated at this layer**. The rows are
not wrong and neither passes for the wrong reason — but neither proves its own condition
alone, and the plan does not say so.

**Authority.** Master plan §5, *"say in the plan when a criterion deliberately cannot isolate
its predicate"* (earned at plan 1 N3, which is exactly why C13's inability to bite was
recorded rather than raised). C2 should have carried the same sentence.

## What I verified correct — specifically

**Suite and environment.** 2425 / 26 / 1, re-measured independently, matching. Both profiles
resolved and compared: the prescribed default is `.env` → `localhost:5433/beyo_manager`; the
discarded run's `APP_ENV=testing` resolves `.env.testing` → `127.0.0.1:5432/app_test`, a
**different database**, so the schema-stale run could not have touched the prescribed one
(P7). Residue check on the configured database after all my runs: `ws_price_%` = 0,
`tsk_price_%` = 0. The only DB-touching test uses the `db_session` fixture, which is
`get_db()` inside `async with` plus an explicit `rollback()`, and additionally deletes in
`finally` — rule 11½ satisfied twice over.

**Ruff judgment — the implementer's call was correct.** Reconstructed all five unformatted
roster files from the **baseline** `302c3ab` and ran `ruff format --check` on them: all five
would already reformat at baseline. Formatting them would have rewritten executable lines
inside `calculator.py` and four others whose authorisation is comment-only or one-row.
`ruff check` passes on all ten roster Python files; the two new files are fully formatted.

**M3 — the statistic.** The participating-set expression is byte-identical to the allocator's
(`budget_division.py:309-313`), reached through the imported `_step_state_is_excluded`, so the
`.value` semantics D-5 flagged are preserved and this screen cannot disagree with the
production-time screen about which sections count. §2A.1.1's step-level typical fallback is
correctly **not** copied. The allocator's `Fraction(1,1)` weight fallback is correctly
**not** copied (§5.3) — probe: substituting it reddens two tests. `sections_total` derives
from steps, never from statement rows — probe: `len(typicals)` reddens C19 and C6. The
defensive `.get()` bites (probe: `[...]` → C19 + C6 red). `usable = not None and > 0` bites
at both sites (probes on the comprehension filter and the loop's test each redden C3).
`is_estimated`'s empty-set clause bites (probe → C6-empty red). Per-section quantisation
bites against sum-quantisation (probe → C4 red).

**The status matrix.** `_MODEL_STATUSES` = {OK, INFEASIBLE, ITEM_UNVALUED,
ITEM_MISSING_EXPECTED_PRICE, NOT_EVALUATED} — exactly §9A.1's A1/A2/B6/B7/B10. Probe:
narrowing it to {OK, INFEASIBLE} — the `status is OK`-style defect the criterion exists to
catch — reddens **five** tests including C1. **P4 discharged**: every "present" row uses the
fundable mockup model (residual 22 000, K = 0, rate 13 000 000, T = 12 300 → `B = 1 211 335`,
domain non-null), so `domain is not None` is a real assertion and not an artefact; the B6/B7
rows use a model with no purchase term, and the separate
`test_c1_b6_b7_purchase_term_without_cost_collapses_all_blocks` supplies §9A.1's `†` row with
a purchase term and no cost, asserting all three blocks null.

**`can_commit` — P5 discharged.** Computed from the live selection
(`selection_ready`/`currency_agrees` off `_load_preview_inputs`), never from
`budget_status.status`. Each of the five conjuncts probed **alone**; every one reddens C2. The
asymmetry row genuinely constructs the drift rather than asserting it abstractly:
`committed_live_model_expired` sets the *committed* status to `ok` while the *live* selection
is `NOT_CONFIGURED_NO_COST_MODEL_VERSION`, which is precisely §9A.2's retraction scenario, and
it publishes `false`. `no_valuation → false` and `null_expected_price → true` both hold.

**M6 — the fingerprint.** Full ids, no truncation, `cmv:pcbv:v{CALCULATION_VERSION}` in fixed
order, `null` exactly when the model block is `null`. Three independent probes each redden
C8: order swapped, `v{CALCULATION_VERSION}` dropped, basis id sourced from the wrong
selection field.

**M1's carrier assembly (L4).** `int(selection.basis_version.cost_per_worker_minute_minor.
scaleb(4))` — probe with `scaleb(3)` reddens two tests. `Numeric(12,4)` bounds the value at
8 integer digits, so `scaleb(4)` stays far inside the default decimal precision and `int()`
cannot truncate anything real. `CHECK > 0` (`production_cost_basis_version.py:38`) makes the
`allowed_centimin` division safe with no zero-guard, per §2A.1.3.

**`suggested_price_minor` (L6, §4.4B).** `null` whenever `domain` is `null`, not only when
`break_even` is — probe dropping the `domain is not None` conjunct reddens C18's null-domain
row with the `AttributeError` the contract exists to prevent. The mockup row asserts
`1 211 335 → 1 215 000` exactly.

**§9.2A over §9A.1.** `binding_is_bound` gates the whole model/anchors/domain block and blanks
`saved`, `currency` and `config_fingerprint` on both non-`bound` paths; `item` is `null` for
`detached` and populated for `mismatched`; `typical` stays populated on both. Probe disabling
the blanking reddens C9. `currency` tracks `saved` per §6B — probe sourcing it from the basis
version reddens C7 and C9.

**Perimeter, exceptions, mirror.** `git diff --name-only 302c3ab 48705b3 -- app/` = 11 files,
matching §2's roster row for row. All three comment-only exceptions are comment-only in the
diff (1 + 1 + 2 lines, zero executable change); both reciprocal pairs land in the same commit
and each names the other's path. Route mirror: `_EXPECTED_ROUTES` +1 with `_ADMIN_MANAGER`,
both counts 26, the function renamed to `…_twenty_six_routes`, and the stale docstring
corrected 23 → 26. `_ROUTES` gained the row (not `_ALL_ROLE_ROUTES`), so C11's WORKER/SELLER
`403` rows come for free, and C13's new function asserts
`calls[0][0] is item_economics.get_task_price_scenario` — service identity, not status code.
C14 asserts the allocator's absence from the module source. C17's decision is stated
explicitly in the handoff as the criterion requires. D-7's service-side choice keeps §2's
perimeter exact and the router-side STOP was correctly not entered.

## Carry-forward dispositions

| id | disposition | destination |
|---|---|---|
| F1 | correct the ledger row to the two-test set (or delete F2's copy, which makes it correct as written) | **coordinator**, closeout fold of the r1c handoff; plus the L1 amendment to master plan §5 |
| F2 | decide: delete the duplicate, or keep it and record the two-file set | **coordinator**, same fold |
| F3 | skip `is_deleted is True` in `_has_purchase_term` | closeout phase perimeter |
| F4 | criterion asserting the supersession-chain predicate | closeout phase criteria; origin §6B |
| F5 | add a `{11, 12}` median fixture to C4 | closeout phase criteria; origin §5.3A |
| F6 | comment or remove the dead `detached` override | closeout phase, optional |
| F7 | re-record two spans, add the `implements` edge | **owner card 1** → human-authorization backlog |
| F8 | tenant rows for the two new queries, or record them as redundant defence | closeout phase criteria |
| F9 | collapse the duplicated loads | closeout phase, or accept with a recorded reason |
| F10 | none — recorded as a confirmed reading | lesson only |
| F11 | say in C2 that conditions 3 and 4 cannot be isolated at this layer | master plan §5 / plan amendment |

## Lessons for the plans

- **L1 — widen the whole-file rule.** Master plan §5 says a ledger's observation is a
  property of the *whole file*. F1 is the case that breaks it: the same assertion now lives in
  two files, so a correct whole-file run still understates. **The observation is a property of
  every file that asserts the mutated symbol — measure across the suite.** Earned twice now
  (plan 1 F2, plan 2 F1), and cheap: one full run instead of one file run.
- **L2 — "replace" does not say whether a second copy is allowed.** `plan_2.md` §2 exception 1
  authorised replacing an assertion; the implementer replaced it *and* added a copy in another
  authorised file, in good faith, and that copy is what made the ledger wrong. An exception
  that relocates a guard should say where the guard is allowed to live afterwards.
- **L3 — apply the "cannot isolate" sentence to C2.** Master plan §5 already carries the rule
  (plan 1 N3); C2 needed it and did not get it. Conditions 3 and 4 of §9A.2 collapse to one
  predicate at the read-model layer.
- **L4 — a criterion naming a rounding mode needs a fixture where the modes disagree.** C4's
  fixture separates per-section from sum quantisation and cannot separate half-even from
  truncation, because its median is `x.5` with `x` even. A mode named in a contract is a
  mechanism; charter rule 2's enumeration discipline applies to it.
- **L5 — a file whose every dependency is monkeypatched is a unit test.** Marking it
  `integration` implies a session and a tenant boundary that eight of its thirteen functions
  do not have. Either the marker or the fixtures should move; the plan should say which.
- **L6 — §6B states a resolution predicate no criterion asserts.** "Current valuation" is
  defined three times in the intention and pinned nowhere in either phase. When a contract
  names a `WHERE` clause, that clause is a criterion row.

## Mutation-probe declaration

Every probe applied alone, the target file run whole, reverted, and checksum-verified
byte-identical against the pre-probe baseline.

| File | Probes applied | SHA-256 after revert | Identical to baseline |
|---|---|---|---|
| `app/beyo_manager/domain/item_economics/price_scenario.py` | 2 (`max(1,·)→max(6,·)`; `_shape_error` comment deleted) | `948a7a0f990ad409f26ff97a173fc0eeb2211970d0c9d5e7e1059277aba04542` | yes |
| `app/beyo_manager/domain/item_economics/calculator.py` | 1 (comment deleted) | `6767fe49b320a189f5debc257ed4530950788e9087833f4c3a1881981f54ed64` | yes |
| `app/beyo_manager/domain/item_economics/serializers.py` | 1 (comment deleted) | `d0a0e3e7c9c8607aceb003a6258d6f643e502fcf57cc3c9fcb5b600fbfa5013c` | yes |
| `app/beyo_manager/domain/cases/serializers.py` | 1 (comment deleted) | `b026dfd630f417d4f5cb9b3709838979c2ecdc7c308fa41ae26341225231cce9` | yes |
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | 29 (status gate, model gate, 4× `can_commit` conjuncts, `is_estimated`, quantisation ×3, `.get()`, usability ×2, median fallback, `sections_total` ×2, fingerprint ×3, binding blanking, `is_fundable`, suggested-price guard, detached override, workspace scoping ×2, supersession filter, enum comparison, rate scale, currency source) | `c276ce6989d8c4343ee56618f2e2027c3f92a36ccc3c95513c9d53085009b7b5` | yes |

`price_scenario.py`'s post-revert hash also matches the value the implementer declared in the
r1c ledger, independently confirming that revert.

**Database state.** No probe wrote to any database. The full suite was run three times
(unmutated, mutated, unmutated) against the configured `beyo_manager` database; residue
afterwards: `workspaces LIKE 'ws_price_%'` = 0, `tasks LIKE 'tsk_price_%'` = 0. Inherited
`task_steps` / `step_state_records` drift is baseline noise per master plan §6 and is not read
as evidence. The `app_test` database was never connected to.

**Working tree.** `git status --porcelain --untracked-files=all` at the repository root shows
only the three untracked `live_clock_for_working_time_economics/planning/` files — a different
project, out of scope, neither read nor touched by this session.

## Full write perimeter

1. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_phase2_review_r1_handoff.md` (this file)

No application file, test, plan, master plan, tracker row, plan 2 Review log or architecture-
graph record was written by this session. All probe edits were reverted and hash-verified
above. Scratch artifacts (probe scripts, run logs, failure-ID sets) live outside the
repository in this session's scratchpad.
