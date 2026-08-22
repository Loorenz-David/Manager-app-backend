# Master plan — simple_valuation_editor

```
state: **CLOSED — all five phases APPROVED; archived 2026-08-22.** Code complete and
       all work queues empty. **Header corrected at archive time:** the previous line
       read "closeout ritual and graph remain", which was true when written and was not
       refreshed afterwards; the graph has since been driven to 0 pending / 0 stale /
       0 diagnostics by later projects, and this pipeline holds no open queue. If a
       closeout step was in fact skipped, §3's tracker — not this line — is the record
       that would show it.
date: 2026-08-19
phases: 5 — see §3. Phases 3 and 4 ran in parallel (app/ vs docs/handoff/); phase 5 was
        opened by re-review r2's R8, was blocked on phase 3, and is now unblocked.
```

## 1. Mission

Ship **one read-only endpoint** — `GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario` —
that hands the "Expected sold price" screen the closed set of constants it needs to
project the consequences of a price live, at every frame of a slider drag, without a
network round trip.

The item-economics domain already owns the price → budget → allowance function as pure,
no-I/O code. This pipeline publishes the function's **inputs** instead of one evaluated
output at a time. It persists nothing, changes no existing payload, and is deleted by
removing what it added.

Authorities: `planning/intention.md` (RESOLVED and PLAN-READY, round 4),
`planning/owner_decisions.md` (D1–D10, ledger empty).

## 2. Folder layout

Charter tables: `planning/` (intention, owner decisions), `plans/`, `prompts/<role>/`,
`handoffs/<role>/`, `archive/plan_<n>/`. State is positional — closed plans move to
`archive/` **and** their own `state:` line is corrected at closeout (carried from
`simple_production_budget_division`, where a plan sat in `plans/` reading `PROMPT_READY`
after approval, and from `inline_valuation_versioning`, where the correction was applied).

`prompts/coordinator/` holds standing coordinator documents — never handed to a session.

**One extension to the archive partition, recorded because it deviates from the charter's
`archive/plan_<n>/` scheme.** The mechanism-inventory ran *before* any phase existed, so
its spent prompt, consumed handoff and opened seal have no `plan_<n>` to belong to. They
are archived under **`archive/gate_inventory/`**. The rule the scheme actually encodes —
state is positional, a consumed row never sits in a live table — is preserved; only the
partition key changes, because the partition key is the phase and this work predates
phases. Historical references to `prompts/reviewer/…` and `handoffs/reviewer/…` for these
three files resolve there, and are not rewritten.

**Closeout ritual performed 2026-08-19.** All five plans and every prompt and handoff they
consumed now sit under `archive/plan_<n>/`; `plans/`, `prompts/implementer/`,
`prompts/reviewer/`, `handoffs/implementer/` and `handoffs/reviewer/` are empty. **State is
positional and now correct: nothing sits in a live table.**

**The non-rewriting rule above is general, not specific to the gate.** §3's tracker and the
archived plans cite dozens of `plans/plan_<n>.md`, `prompts/<role>/…` and `handoffs/<role>/…`
paths as they stood when written. **Those are not rewritten** — each resolves to
`archive/plan_<n>/<same basename>`, the basenames are unique across the project, and rewriting
them would edit consumed rows to make a filing decision look like it was always true. The
charter's own rule against revising a published handoff is the same rule.

## 3. Phase registry & tracker

Five phases. The two gate rows come first, then one row per phase — **newest state first**;
rows marked *superseded* are the same phase's earlier states, kept as provenance.

| Phase | Scope | State | Date | Actor | Note |
|---|---|---|---|---|---|
| — | Mechanism-inventory gate over intention §3–§9 (M1, M1b, M2, M2b, M3, M4, M5, M6) | **PASSED** | 2026-08-19 | Opus 5 (inventory) + coordinator (fold) | Eight mechanisms swept, twelve lettered sections added, nothing renumbered. Three owner cards raised and all three closed (D8, D9, D10). Coordinator verified the load-bearing claims independently rather than consuming them: break-even `1 211 335` re-derived (the intention's `1 211 364` solved a real-arithmetic equation instead of §4.1's least-integer search — off by 29), `ival` prefix, `usable = not None and > 0` at `budget_division.py:326`, and the commit path ignoring a request price when no valuation row exists (`:212-213`). **One defect found in the delta and corrected at the fold**: §9A.1's "can return only nine of the twelve" is ten, contradicted by its own B1–B10 table and by §12A. Ledger empty; intention now `RESOLVED and PLAN-READY (round 4)`. |
| — | Implementation planning | **DONE** | 2026-08-19 | coordinator | Two phases, split at the domain/service boundary the codebase already draws (`budget_division.py` / `calculator.py` are pure; `services/queries/` does I/O). Criteria built from §12 + §12A's eleven obligations. **HC-2 extended to a fourth artifact** — one new pure domain module — recorded in plan_1 §2 under the HC-1a precedent, no new owner card. |
| 1 | The pure price mechanisms: `round_half_even`, the collapsed form, the break-even and infeasibility searches, the step helpers, the band. No I/O. | **APPROVED** | 2026-08-19 | Opus 5 (re-review r3) | **0 blocking, 0 should-fix. F1 and F2 closed**, both verified independently rather than read off the handoff: F1's mutation reddens exactly the one new test whole-file; F2's six re-measured sets match the reviewer's own r1 measurements test-for-test, which is the non-circular half of that check. Suite **2373/26/1** — measured independently by implementer, coordinator and reviewer. Perimeter `+11 / −0` across exactly two files. Four new notes, all routed: **N8** (the coordinator's own strengthening assertion does not discriminate — `max(6, quantity)` leaves 53 green) → plan 2 §2 with a verified fixture; **N9** (graph symbol/span mismatch, also the coordinator's) → owner card 1, does not hold the gate; **N10** → registered as C22; **N11** → plan 2 task 4. N2 closed as accepted, N6 to plan 2. Checkpoints `b72821c` → `aea97ca`. |
| 1 | *(prior row — fix r2)* | *superseded* | 2026-08-19 | Codex (fix r2) | F1 and F2 addressed inside the two-file perimeter, checkpoint `aea97ca`. Coordinator verified: `git diff b72821c aea97ca -- app/` is exactly the two allowed files; the production change is **two comment lines** and nothing else; the new test carries both required assertions; suite re-measured independently at **2373/26/1** (+1). No note from the fix prompt's §5 was acted on — confirmed by reading the diff, not the claim. Graph re-recorded twice this session (owner card 1, then a self-correction for span drift and a stale count in my own evidence summary). Re-review prompt at `prompts/reviewer/2026-08-19_phase1_rereview_r3.md`. |
| 1 | *(prior row — review r1)* | *superseded* | 2026-08-19 | Opus 5 (review r1) | **0 blocking, 2 should-fix, 7 notes.** The arithmetic is correct — the reviewer re-derived every published number from a reference implementation written from the intention alone, without importing the module, and all 22 values matched; 18 of its own 22 mutations bit. **F1**: `slider_domain`'s `max(1, quantity)` guard has **no test** — deleting it leaves all 52 green, and `quantity = 0` is a documented live input (§2.7: no CHECK constraint) that then raises `ValueError` instead of returning a band. Coordinator re-confirmed both sides. **F2**: three of six ledger rows understate their observed-red set (C8 reddens 5, C17 3, C10 2) — all from `-k`-filtered runs; no defect hidden. Owner card 1 answered: re-record the graph node as `source_file`. Fix prompt at `prompts/implementer/2026-08-19_phase1_fix_r2.md`. |
| 1 | *(prior row — implement r1)* | *superseded* | 2026-08-19 | Codex (implement r1) | 52 tests, C1–C21 all mapped, checkpoint `b72821c`. Coordinator verified at consumption: perimeter clean (2 app files + declared `.archgraph` write); suite **2372/26/1** re-measured independently (+52, inherited 26 unchanged); revert hashes recomputed and matching; rule 3 fixtures confirmed to use real unflushed `CostModelTerm`. **One ledger inaccuracy found by re-applying a probe**: the C10 mutation reddens **two** tests, not the one recorded — C12's chained `== SEARCH_CAP_MINOR == 2**40` also bites. Both failures correct; the record was taken from a filtered run. Review prompt at `prompts/reviewer/2026-08-19_phase1_review_r1.md` carries it as probe P1. |
| 1 | *(prior row — projection r0)* | *superseded* | 2026-08-19 | Opus 5 (projection r0) + coordinator (fold) | Projection returned `AMENDMENTS_REQUIRED`, **0 owner cards**, 17 ledger rows — 4 upstream, 11 plan amendments, 4 written delegations — **all routed before the implement prompt compiled**. Three named mutations (C7, C17, C10) proved unable to fail and were replaced; `infeasible_at_or_below_minor` for the mockup is **29**, not the `0` §4.2A claimed. Design survived intact: M1's form faithful to the shipped calculator, all four literals exact, the bound holds on every shape. Coordinator re-derived each load-bearing claim, including confirming the unflushed-ORM `is_deleted = None` trap empirically. |
| 2 | The read model, the route, the mirror: M3, M4, M6, the status table, `can_commit`, HC-2a's four artifacts. | **APPROVED** | 2026-08-19 | Opus 5 (review r1) | **0 blocking, 1 should-fix (coordinator-routed, no code), 11 notes.** 34 mutations applied one at a time, each file run whole, each reverted and hash-verified — **27 reddened**; of the seven that did not, two were not real mutations, one is provably dead code, four are coverage gaps, and **none produced a wrong-but-green payload**. Suite 2425/26/1, failure IDs byte-identical. **F1**: the r1c ledger's observed-red set is one test where two is measured — the coordinator's probe P1, confirmed across the whole suite; corrected in plan 2's Review log rather than in the consumed handoff, which is provenance. Seven notes batched into **plan 3** rather than a fix round. Card 1 (graph spans + missing `implements` edge) relayed; does not hold the gate. Checkpoint `48705b3`. |
| 3 | The seven carried repairs from phase 2's review (F2–F9). Code only. | **APPROVED** | 2026-08-19 | Opus 5 (r1, r4) + Claude (r2, r3) + coordinator | Four rounds, 0 blocking in every one, **all seven criteria MET since r1**. **The production file has been correct since `ef55f6d`: `git diff -U0 ef55f6d -- get_task_price_scenario.py` filtered of comments is empty — zero executable lines across the entire fix history.** Every round after r1 was about whether the file tells the truth about itself, and each one found that it did not. **r4 is why the phase took four**: P1 asked whether one predicate was still unverified, and the reviewer swept all five the two `WHERE` comments vouch for — one mutation at a time, whole-suite, ID-diffed — finding **three asserted by nothing and one not load-bearing at all** (`TaskStep.is_deleted` duplicates a Python filter in `group_steps_by_section`; the comment had it backwards). Coordinator reproduced independently: the `group_steps_by_section` skip and `_TypicalSession.execute`'s statement discard by reading, and the `item_id` mutation whole-suite — **which required the repeat rule to survive** (see §6: the first run read 27 on an unrelated shopify flake, the repeat came back 26 with the baseline set, and a single run would have been read as the mutation biting). **H-2 is the finding that generalises**: the `TaskBudgetStatus` correction r3 spent a round on reached the code and the handoff and **neither document that outlives them** — this tracker contradicted itself two rows apart. Both repaired. **One coordinator amendment to r4's verbatim text**, recorded: the `_typical_block` replacement opened *"This line only"* and then revealed a second redundant predicate three lines down; restructured so the opener matches. **One coordinator correction to the coordinator's own amendment**, found by re-reading it: it credited all three measurements to r4 when `workspace_id` was measured at r1. **No r5 was spent** — the surviving prose states measurements rather than judgements, and every one was independently reproduced; the two rows that would let the comments say "proven" are registered as **plan 5 §1C** with their before-state recorded. Five rules earned, in §5. |
| 3 | *(prior row — fix r3)* | *superseded* | 2026-08-19 | Claude Opus 5 (fix r3) | **Both coordinator findings closed, and G-2's gap was reproduced before the row was written.** Coordinator re-verified everything rather than reading the ledger: **E1 across r2 and r3 combined — the non-comment diff of `get_task_price_scenario.py` against `ef55f6d` is empty**, so the entire fix history changed **zero executable lines of production code**; ruff clean; suite **26 / 2431 / 1** with failure IDs byte-identical; hashes matching (`b248b3c7…`, `c9d59c19…`). **G-2's mutation re-measured whole-suite**: dropping `ItemValuation.is_deleted.is_(False)` reddens exactly the new row, one ID added, none removed. **And the consequence was isolated, not inferred** — with the row's first two assertions neutralised under the mutant, `assert result["can_commit"] is False` fails `assert True is False`: **the deleted valuation really does readmit commit**, which is the failure the finding predicted. **The implementer improved on the criterion and said so**: E2 asked for four field-level null checks, but `serialize_task_price_scenario` emits `saved` wholesale, so `assert result["saved"] is None` strictly dominates them — three of the four would have been assertions that cannot fail, the exact defect this phase exists to remove. E4 answered "no fixture shared", so C1's mutation was correctly not re-measured. **One coordinator repair**: the verbatim splice left a ragged short line; the implementer flagged it and **correctly declined to reflow text issued verbatim**, so the coordinator did it and re-verified E1 after. Re-review prompt at `prompts/reviewer/2026-08-19_phase3_rereview_r4.md` — narrow, and P1 is the whole point: **both of this phase's last two rounds were opened by defects in the previous round's replacement text**, and the prose now in the tree has had exactly one reader who is not independent. |
| 3 | *(prior row — fix r2)* | *superseded* | 2026-08-19 | Claude Opus 5 (fix r2) | **Fix r2 applied correctly and completely** — the review's three should-fixes, both coordinator amendments included, verbatim. Coordinator verified rather than read: the service file's diff is **pure comment, zero executable lines**; the test file's complete non-comment diff is **three lines** (one import, two deletions); ruff clean with **F401 clean**; suite **26 / 2430 / 1** with failure IDs byte-identical; both file hashes matching the ledger. **D3 re-measured on the shipped tree**: with both `SET LOCAL` statements deleted, the C1 mutation still reddens exactly `test_phase3_c1_…` suite-wide — **the GUCs were doing nothing**, fifth independent agreement, F-2's STOP condition formally closed. *(Round run by Claude — the owner's Codex credit was exhausted; no protocol change.)* **Two coordinator findings on the newly-landed comment text open r3**, both found by re-reading it as if the coordinator had written it, which after two amendments is partly true. **G-1**: the F-3 comment says `TaskBudgetStatus` "carries item_id and no objects" — it carries `result: ItemCostResult \| None`; the review's own C6 row had the qualification and the replacement text lost it, discrediting the paragraph at the one moment it must be believed. **G-2 is the substantive one and it is F4's exact twin**: F-1's replacement calls `ItemValuation.is_deleted.is_(False)` load-bearing, and **deleting it leaves the focused file 49/49 green** — while `delete_item_valuation.py:41` soft-deletes valuations behind a **live route** (`routers/api_v1/item_economics.py:305`), so a regression would serve a deleted valuation's price and byline and flip `can_commit` to true on a row the user deleted. **A comment asserting a property is a claim, and this one was the first thing to test it.** Fix prompt at `prompts/implementer/2026-08-19_phase3_fix_r3.md`. |
| 3 | *(prior row — review r1)* | *superseded* | 2026-08-19 | Opus 5 (review r1) | **0 blocking, 3 should-fix, 6 notes. All seven criteria MET** — the reviewer's own summary: *"the endpoint is correct and every one of the seven repairs does what it was asked to do."* **All three should-fixes are one shape — a record that does not survive the reader it was written for**, and together they answer the question plan 3 §3 actually asked and the r1b handoff answered narrowly: *were the decisions recorded*, not *were they made*. **F-1** the F8 comments dangle at `(C10)` **and** sit as the first line inside a multi-predicate `WHERE`, one row above `superseded_at.is_(None)` — the very filter this phase's C1 row exists to protect. **F-2** the C1 fixture's two `SET LOCAL` planner GUCs are **inert**: the reviewer measured that deleting them keeps the mutant red 3/3 while swapping the two UPDATEs turns it green 3/3, and the coordinator **reproduced the decisive half independently** (GUCs kept, UPDATEs swapped → 49/49 green). The determinism is the UPDATE order alone, and the file's one comment credits the half that does nothing. **F-3** F9's latency acceptance lives only in a handoff that archives → moved to the call site. Coordinator also reproduced **N-2** whole-suite: deleting `collapse_terms`'s `is_deleted` skip reddens **exactly one test in the entire codebase**, phase 3's new C2 row, with the domain file 53/53 green — so a phase-1 domain semantic had **no guard at all** before this phase and now has one, two layers away. **Two coordinator amendments to the reviewer's verbatim text, both recorded in the fix prompt**: a count mismatch (*"three predicates below"* above four), and `item_valuation.py:35` — a bare line number inside the very finding that outlaws unresolvable references. Reviewer declared a `VACUUM (ANALYZE, FULL)` on `item_valuations` as the durability half of P2. Fix prompt at `prompts/implementer/2026-08-19_phase3_fix_r2.md`. |
| 3 | *(prior row — implement r1b)* | *superseded* | 2026-08-19 | Codex (implement r1b) | 3 new rows, 1 duplicate deleted, checkpoint `ef55f6d`, **0 owner cards**. Perimeter exactly the two allowed files (`+3/−2` and `+183/−13`); no third file touched and no STOP entered. Coordinator verified at consumption rather than reading the ledger: suite re-measured **26 / 2430 / 1** with failure IDs byte-identical, the count reconciling exactly against the concurrent owner change to `purchase_api.py` (`2425 +3 −1 +3`); **all four named mutations re-applied whole-suite at their definition sites and reverted byte-identical**, every observed-red set matching the ledger — including **C4's**, the criterion that had been wrong in phases 1 and 2 and is now measurably one test. Also confirmed independently: the `int(resolved)` mutant leaves C4's own row green, which is the half of plan §3's F5 premise the implementer did not record; F6's block is genuinely dead (`detached ⟺ item is None`, and `can_commit` already requires `item is not None`); F9's refusal is true because `TaskBudgetStatus` carries `item_id` and `result: ItemCostResult \| None` but none of the objects re-read at the call site — not the `Task`, the `Item`, the selection, the terms or the valuation — so collapsing needs a third file; and `_current_valuation` needs no `ORDER BY` because `uix_item_valuations_current` is a partial unique index — **recorded so it is not re-raised**. **One coordinator finding, seeded as review probe P1**: the two F8 comments name `(C10)`, a criterion label that archives at closeout — the only two criterion-ID references in the whole `app/beyo_manager/` tree — and the handoff's C5 row claims they name the test function, which they do not. **A second result worth the round**: the implementer measured 27 twice with the extra ID `test_c3_real_concurrent_open_insert_translates_the_loser[model]`, the coordinator measured 26 with it absent — the same test red and green on identical code, giving §6's "unidentified" drifting test a name for the first time in three pipelines. Review prompt at `prompts/reviewer/2026-08-19_phase3_review_r1.md`, five probes. |
| 3 | *(prior row — prompt compiled)* | *superseded* | 2026-08-19 | coordinator | `plans/plan_3.md`, 7 criteria, two-file perimeter. Projection **WAIVED** — no new mechanism, and review r1 computed every expected value. Prompt at `prompts/implementer/2026-08-19_phase3_implement_r1.md`. **F4 is the one with teeth**: the supersession predicate is unasserted and the previous pipeline made chains a common state. F6/F8/F9 are decisions the implementer may resolve either way — only an *unrecorded* outcome is unacceptable. |
| 5 | The two predicates the shipped comments call **unproven**: `ItemValuation.item_id` and `TaskStep.task_id`. Two rows, then two comment edits. | **APPROVED** | 2026-08-19 | Claude Opus 5 (implement r1) + coordinator | **Both gaps closed on the first round, 0 owner cards, no STOP, no third file.** Coordinator re-measured both named mutations whole-suite rather than reading the ledger: dropping `ItemValuation.item_id` reddens exactly `test_phase5_c2_…`, dropping `TaskStep.task_id` reddens exactly `test_phase5_c3_…` — one ID added, none removed, each up from r4's measured **0/0**. Suite **26 / 2433 / 1**, failure IDs byte-identical to the set carried since `ef55f6d`. **`get_task_price_scenario.py`'s non-comment diff against `ef55f6d` is still empty** — zero executable lines across **five** rounds. **`test_phase5_c3_…` is the first real-SQL exercise `_typical_block` has ever had**; the other eight drive a fake session whose `execute()` discards the statement, which is why `task_id` went unasserted through four rounds — and the coordinator verified *eight distinct test functions*, not eight occurrences, because a count is one of the two error-prone classes. Two implementer judgements, both right and both self-reported: the C3 fixture took the **richer** form (five history tasks per section) because without real samples both sections resolve to the zero fallback and `total_seconds` is 0 under contract *and* mutant, leaving only `sections_total` to bite; and *"no test of it is possible"* was softened to the measured statement for `is_deleted`, declining to ship a fresh absolute in the edit that removes two stale ones. **One coordinator correction at the fold**: both new comments scoped an absence claim to *"the suite"* where the true and operative scope is *fixtures reaching this query* — the project's own rule arriving a third time, after a directory and a term set. **No review round was spent**; the reason is recorded in plan 5 §6, and it is that r4 already swept the whole predicate population of both queries, so no unswept class remained. |
| 5 | *(prior row — prompt compiled)* | *superseded* | 2026-08-19 | coordinator | `plans/plan_5.md` §1C, 8 criteria, two-file perimeter. Projection **WAIVED** — no new mechanism, and both before-states were measured whole-suite at re-review r4 (**0 added / 0 removed** each, the `item_id` one reproduced by the coordinator with a repeat). **Scope narrowed by owner decision on the shortest-path-to-closed line**: §1 (arbiter registration) and §1B (`collapse_terms`' guard) each protect something correct today that no comment claims otherwise, so both were **SET ASIDE** to `set_aside/PLAN_item_economics_deferred_coverage_20260819.md` along with N-5 and the two named flaky tests, with every measured before-state carried over so nothing must be rediscovered. **§1C stayed because it is the one item the tree is actively lying about** — phase 3 shipped comments saying these two predicates are load-bearing and NOT proven, and that sentence is honest only until someone makes it false. **Declared narrow reopening of an APPROVED phase**: two additive rows plus comment-only edits, with the empty-non-comment-diff against `ef55f6d` re-verified as an explicit criterion. The prompt carries phase 3's heap-order trap forward by name so the `item_id` fixture does not repeat the inert-GUC round. Prompt at `prompts/implementer/2026-08-19_phase5_implement_r1.md`. |
| 4 | The frontend handoff and the production-time reply. Documentation only. | **APPROVED** | 2026-08-19 | Opus 5 (r1, r2, r3) + coordinator | Three review rounds, 24 findings, **all applied**; r3 returned 0 blocking. The two documents the frontend builds from are correct: 46 keys with their nullability, a BigInt rounding function executed against the server's own over 612 cases, the four conditions that empty the numeric blocks plus the binding rule overriding them, `domain` singled out as the one block that can be null while the others are present, the Save flow with D9's unenforceable precondition, the staleness boundary with a debounce, and a settled-only answer with an honest expiry. **Every blocking finding across three rounds was the coordinator's.** Five rules earned, in §5. |
| 4 | *(prior row — r2)* | *superseded* | 2026-08-19 | Opus 5 (review r2) | 2026-08-19 | Opus 5 (review r1) + coordinator (fold) | 3 blocking, 4 should-fix, 3 notes, 0 owner cards — **all text, all the coordinator's, all applied verbatim**. Every failure was in C3 and shared one root: nullability described as a function of `status` where the code gates on five conditions. **B1** the block rule (two conditions absent; reproduced against the shipped service), **B2** four nullable fields shown as always present (three already recorded in intention §8A), **B3** `config_fingerprint` blind to the typical — which moves with *time alone* on a rolling 90-day window, carrying break-even, suggested and the whole band with it. **S1** published a false absence claim as verified: `today_utc()` wraps `datetime.now` and defeated the literal grep. §4's BigInt block and the worked example were re-executed and are correct. Six rules earned, in §5. |
| 4 | *(prior row)* | *superseded* | 2026-08-19 | coordinator | `plans/plan_4.md`, 6 criteria. Both files new; **nothing edited** — amend-by-reference, the convention the frontend asked for. Written from the shipped serializer, not the intention's example. **Split from plan 3 so it could run in parallel** — no shared files. Awaiting a light review of C3/C4 (every key and literal against code). |

**Phases 3 and 4 run in parallel.** Plan 3 touches only `app/`, plan 4 only `docs/handoff/`.
| 2 | *(prior row — implement r1c)* | *superseded* | 2026-08-19 | Codex (implement r1c) | 52 new tests, C1–C19 mapped, checkpoint `48705b3`, route mirror 25 → 26. **Three blockers preceded it, all on coordinator artifacts, all correct** — perimeter contradictions and a miscount; zero files were changed across them. Coordinator verified at consumption: perimeter exactly **11/11** against the roster; the three comment-only exceptions read as comment-only in the diff (1 + 1 + 2 lines, zero executable change) and both reciprocal pairs name each other; the `test_price_scenario.py` exception is exactly the one assertion, inert equality → exact literal; D-5 took the import branch, preserving the `.value` semantics; suite **2425/26/1** re-measured independently (+52). **One discrepancy found**: the ledger's observed-red set is one test, but the same literal is asserted in a second file (`test_price_scenario_query.py:731`), so the true set is two — phase 1's F2 in a new shape, seeded as review probe P1. Review prompt at `prompts/reviewer/2026-08-19_phase2_review_r1.md`. |
| 2 | *(prior row — projection r0)* | *superseded* | 2026-08-19 | Opus 5 (projection r0) + coordinator (fold) | Projection returned `AMENDMENTS_REQUIRED`, **0 owner cards**, 17 ledger rows — 5 upstream, 10 plan amendments, 3 written delegations (D-5, D-6, D-7) — **all routed before the implement prompt compiled**. Headline: **the carried N8 fix was itself inert** — `f(0) == f(1)` is invariant under `max(6, ·)` at every `B`; coordinator re-verified both forms against the shipped module. Also found: §9.2 and §9A.1 collide on *every* non-`bound` binding (not an edge case); `can_commit`'s status shorthand is unsafe after a config drift; the empty participating set publishes `is_estimated: false`; `suggested_price_minor` had **no criterion in either phase** and crashes on a null domain; HC-2a's line numbers all re-verified correct at head. Criteria 15 → 19. |

## 4. Naming registry

Reserved before any code exists, so two sessions cannot pick two names for one thing.

**Phase 1's public surface — registered at closeout under delegation D-1.** These twelve
names are phase 2's interface; phase 2 cites them rather than choosing its own.

Module `beyo_manager.domain.item_economics.price_scenario`. Carriers: `PriceModel`
(frozen: `residual_percent_milli`, `constant_deduction_minor`,
`cost_per_worker_minute_ten_thousandths`), `SliderDomain` (frozen: `step_minor`, `min_minor`,
`max_minor`), `CostModelTermInput` (Protocol), `SEARCH_CAP_MINOR`. Functions:
`round_half_even`, `collapse_terms`, `budget_minor`, `allowed_centimin`, `allowance_seconds`,
`break_even_price_minor`, `infeasible_at_or_below_minor`, `floor_to_step`, `ceil_to_step`,
`two_significant_digits`, `slider_domain` — and **`digits`, which is INTERNAL to phase 1**
(N7): a generic integer helper with no domain meaning, public only because a criterion
asserted it directly. Phase 2 calls `two_significant_digits`, never `digits`.

| Thing | Name | Home |
|---|---|---|
| Query service | `get_task_price_scenario` | `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` |
| Route | `GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario` | `app/beyo_manager/routers/api_v1/item_economics.py` |
| Serializer | `serialize_task_price_scenario` | `app/beyo_manager/domain/item_economics/serializers.py` |
| Slider-band rule label | `break_even_band_v1` | `domain.rule` in the payload (HC-6) |
| Typical method label | `median_completed_section_totals` | existing `TYPICAL_METHOD` (`budget_division.py:16`) — **reused, never re-declared** |

Binding constraints on names and copies:

- **`basis` is taken.** It means `production_cost_basis_version` in this domain. No new
  meaning for it (intention §8).
- **One-copy rule** (earned `simple_production_budget_division` r1 lesson 4). The typical
  statement, the participating-section rule and the median fallback are **imported** from
  `budget_division.py` / `get_working_section_typical_times.py`, never reimplemented.
  HC-2 forbids *changing* those modules; it does not forbid calling them. A second copy
  of a registered mechanism is a review finding.
- **`serialize_user_light`'s three-key shape is re-declared, not imported** (intention §6,
  a deliberate decision). Both sites carry a comment pointing at the other so a later
  consolidation finds both. This is the one sanctioned duplication in the pipeline; any
  other requires a decision.
- The `round_half_even(a, b)` integer helper is **one** function. If it appears in both
  the query service and a domain module, that is a finding, not a convenience.
- **`_shape_error` — second sanctioned duplication, coordinator decision at the review r1
  fold (2026-08-19, N5).** `price_scenario.py:53-57` reproduces `calculator.py:124-128`
  verbatim, including the published message string that `test_calculator.py:501` asserts
  exactly. **Sanctioned, with two conditions**: (a) both sites carry a comment pointing at
  the other, exactly as `serialize_user_light`'s duplication does; (b) **a third copy is
  forbidden** — phase 2's query service imports one of the two rather than reproducing it.
  Reason for sanctioning rather than extracting: the alternative is for a pure domain module
  to import from `calculator.py` solely for a message formatter, and the duplicated *string*
  is already pinned by an exact-match test in the calculator's own suite, so a drift between
  the copies fails loudly there. The identity token itself is correctly **reused from the
  registered set, never minted**.
- **`digits` is internal to phase 1** (N7). It is a generic integer helper with no domain
  meaning; phase 2 calls `two_significant_digits` and never `digits`. Registered as internal
  when D-1's twelve public names are folded into this section at phase 1 closeout.

## 5. Standing rules

Charter rules 1–11½ apply in full, plus every rule earned by the three prior pipelines.
The ones that bite hardest on *this* feature, restated because they are load-bearing here
rather than merely inherited:

- **Rule 5 — no adjectives for mechanisms.** "A nice step", "near", "sensible band" are
  not specifications. Any surviving adjective in a mechanism is a gate failure, not a
  style note. This rule is the reason the inventory gate is open (§7).
- **Rule 2 — enumerate, never sample**, with its companion: each row's fixture makes its
  own predicate the ONLY reason its outcome holds. The status matrix and the M3 fallback
  rows are exactly where a shared-cause fixture would pass for the wrong reason.
- **Rule 3 — invariants proven on the production object type.** The M1 fidelity test holds
  real `CostModelTerm` ORM instances; the shape guard inside `calculate_term_amount` is
  part of what is being proven (intention §12.7).
- **Rule 6 — effort by silent-failure risk.** This whole feature is rule-6 surface: money
  arithmetic, quantization, a rounding-mode contract, a monotonicity argument, a search,
  and an ordering-free statistic. Nothing here fails loudly.
- **Rule 11 — named mutations name their site** (file, definition-vs-call-site). Intention
  §12.2 already names one; the planner enumerates the rest.
- **Precedence-disagreement rule** — a fixture pinning a ranked rule makes every level of
  it disagree.
- **No-weaker-assertions rule** — exact literals; absence asserted as absence, never as
  zero (intention §9.1 depends on this distinction being testable).
- **Perimeter-by-path rule** — every handoff declares its full write perimeter by path,
  generated from `git`, never retyped.
- **Verification-scope rule** (earned `inline_valuation_versioning`) — a claim that
  something appears *nowhere* is only as good as the directory the search ran in. State
  the root; run "appears nowhere" searches from the **repository root**. This cost an
  implementer round last pipeline.
- **Widen the allowlist, never remove the filter** — if the docs-accuracy guard's coverage
  is extended, add extensions. Removing its extension filter makes it crash on a binary
  `.docx` in its own root and go red forever for the wrong reason.
- **Prove each root alone** — a combined probe proves *something* caught it; single-target
  probes prove *each target*.
- **MVP calibration** (owner-raised 2026-08-16) — mutation ledgers with observed-red are
  mandatory for rule-6 mechanisms and tenant boundaries; routes, serializers, role
  admission and envelopes get ordinary tests with no ledger row. **Note the consequence
  for this pipeline: the calibration does not buy a cheap review here**, because almost
  everything this feature ships is rule-6.

### Rules earned before the first line of code

- **A worked example is a test, not an illustration** (coordinator, 2026-08-19). An
  intention that reproduces a mockup's numbers from its own rule is claiming the rule is a
  rule and not a fit. That claim is checkable by arithmetic at inventory time, for free,
  before an implementer spends a round on it. Do the arithmetic. (Earned in §7's gate
  assessment; it then found six of ten worked examples not following their own rule.)
- **A named mutation is not accepted until someone has computed both sides of it**
  (projection r0, 2026-08-19). Charter rule 11 says a named mutation must turn a test red.
  It does not say who checks that the mutation *can*. Three of this phase's mutations were
  proved inert — one could only weaken a `<=` bound, one asserted the property the mutation
  preserves by construction, one named a mutation of a circular definition that no
  implementer could write. All three read perfectly well in prose. **The check is cheap and
  mechanical: state the value under the contract and the value under the mutation, and
  confirm they differ.** A mutation whose two sides were never computed is a claim, not a
  guard.
- **WIDENED (phase 2 review r1, F1/L1): a ledger's observation is a property of every file
  that asserts the mutated symbol — measure across the SUITE.** The whole-file rule below
  was earned in phase 1 and broke in phase 2: the same literal came to be asserted in a
  second file, so a *correct* whole-file run still understated the set (one test recorded,
  two measured). Earned twice now, and the fix is cheap — one full run instead of one file
  run, with the failure-ID sets diffed against the unmutated baseline.
- **An exception that RELOCATES a guard must say where the guard may live afterwards**
  (phase 2 review r1, L2). `plan_2.md` §2 exception 1 authorised *replacing* an assertion;
  the implementer replaced it **and** added a copy in another authorised file, in good
  faith — and that copy is what made the ledger wrong. "Replace" answers what happens at the
  old site and is silent about new ones.
- **A criterion naming a rounding MODE needs a fixture where the modes disagree** (phase 2
  review r1, L4/F5). C4's median was `x.5` with `x` even, so half-even and truncation give
  the same answer and only per-section-vs-sum quantisation was actually pinned. A mode named
  in a contract is a mechanism; rule 2's enumeration discipline applies to it.
- **A file whose every dependency is monkeypatched is a unit test** (phase 2 review r1,
  L5/F8). Marking it `integration` implies a session and a tenant boundary that eight of its
  thirteen functions did not have. Either the marker or the fixtures should move, and the
  plan should say which.
- **When a contract names a `WHERE` clause, that clause is a criterion row** (phase 2 review
  r1, L6/F4). §6B defines "current valuation" three times — `superseded_at IS NULL AND
  is_deleted = false` — and no criterion in either phase asserted it; deleting the
  supersession filter left the whole phase file green.
- **A mutation ledger's observation is a property of the whole file, not of the test you
  were watching** (review r1, 2026-08-19). Companion to the rule above. Three of six ledger
  rows understated their result because the observation came from a `-k`-filtered run: C8's
  mutation reddens **five** tests, C17's **three**, C10's **two**. Every extra failure was
  correct — but **an unexpected reddening is exactly the signal the ledger exists to
  surface, and a filtered run cannot produce it.** Re-apply, run the file whole, record the
  complete set. This belongs in the executor doctrine, not only in this project.
- **Every `max(`, `min(` and `or 0` in a contract is a candidate criterion row** (review r1,
  F1). §7A.1 states `Q = max(1, quantity)` inline, §9.4 explains the division-by-zero it
  prevents, and §2.7 proves the input is live — three sections carrying the hazard and no
  criterion carrying a row. Deleting the guard left all 52 tests green. **Guards stated in a
  parenthesis are still guards, and guards are what silently disappear.**
- **A `>=` in a contract implies two rows, not one** (review r1, N2). Charter rule 2's
  adjacent-pair discipline applies to comparison operators, not only to ranked orders.
- **Say in the plan when a criterion deliberately cannot isolate its predicate** (review r1,
  N3). Plan 1 task 4 did this for C13 — which is why C13's inability to bite was recorded as
  a confirmed reading instead of raised as a finding. Where a criterion *can* bite, name the
  mutation; where it cannot, say so and why.
- **VERIFICATION-SCOPE, EXTENDED: an absence claim is only as good as its TERM SET, not just
  the directory it ran in** (phase 4 review r1, S1). The `inline_valuation_versioning` version
  of this rule was about the *root*; this one is about the *terms*. "No clock read anywhere in
  `services/queries/item_economics/`" was published to the frontend **as verified**, from a
  grep for `datetime.now|utcnow|func.now`. The codebase's own `today_utc()` wrapper defeated
  it — two calls in that exact directory. **Record the search terms beside an absence claim,
  or restate it as the presence claim it is standing in for.** Here the honest form was
  narrower and stronger: *`worked_seconds` is `total_working_seconds` and nothing else at
  `budget_division.py:134` and `:266`* — a claim that holds and that the verdict actually
  rested on.
- **"Executed, not merely written" must extend to prose asserting an absence** (same finding).
  §4's BigInt block was executed over 612 cases and was flawless; the sentence three pages
  later asserting a directory-wide absence was not executable and was wrong. The care went
  where the code was, not where the risk was.
- **A blanket "these N are published together" claim needs one probe per member** (phase 4 r3,
  F1). It survived two review rounds because it was true for three of its four subjects, and
  both rounds read it as a unit. This is charter rule 2 applied to **prose**: a criterion over a
  grouped claim enumerates one row per member, because the member that differs is invisible
  inside a list of members that don't.
- **A correctness fix to a client instruction needs a cost line** (phase 4 r3, F2). The
  reviewer who corrects *when* to call an endpoint has no reason to look at what the call runs,
  and the frontend has no way to. Here the corrected instruction asked for an unbounded
  workspace aggregate per step transition, from every open screen.
- **Grep before calling a field-level fix done — standing, not a remedy** (phase 4 r2 lesson 3,
  confirmed by r3's P1). Three rounds of corrections leaked to unnamed sites; the round where
  the coordinator grepped first was the round where nothing leaked. It cost three greps. It
  caught a fourth site on the very next finding, one the review had not named.
- **Verbatim replacement text is unreviewed on arrival.** It is still the right protocol — it is
  what made these rounds cheap — but a re-review's scope is always the corrections *and* the
  correcting sentences. Across r2 and r3, four findings were defects in a reviewer's own
  proposed wording.
- **A final round reads every document in the phase end to end, regardless of delta** (r3
  lesson 5). F3 sat in a file nothing had changed that round, in the four-line action list, and
  contradicted the section it pointed at.
- **A payload contract's NULLABILITY needs its own criterion, separate from its key list**
  (phase 4 review r1, L1). C3 asked that every key match the serializer — and all 46 did.
  Every failure was a *nullability*, so the document passed the check it was given while
  getting the harder half wrong. Future handoff phases: **"every nullable field is annotated
  as nullable, and every annotation names a reachable status or binding that produces the
  null."**
- **Avoid the example; read the corrections** (L2). "Written from the serializer, not the
  intention's §8 example" was right — that example carried four wrong values. But §8**A** is
  not the example, it is the *corrected walk*, and it already held three of the four missed
  nullabilities and the `n`-conflation this handoff then re-broke. Skipping a document's
  errata along with its errors is how a correction gets made twice.
- **An invariant appearing in two sections is stated identically in both, or once with a
  cross-reference** (L3). §6.1 stated the live-vs-displayed split precisely for `can_commit`;
  §5.2 governed the same split for the model block and did not. Same author, same sitting,
  four pages apart — and only one of them sits on the path a frontend dev reads before writing
  a null check.
- **A read order built from section numbers misses lettered sections a projection added**
  (L5). §9.2A — *binding wins over the status table* — was a projection-round insert, and it
  never reached the handoff; §9A.1's `†` did, but only as a footnote. A closeout phase's read
  order names **the projection handoffs' ledgers**, not only intention sections.
- **A tripwire's roots are wider than the pipeline that widened them — including for the
  coordinator** (phase 3 implement blocker, 2026-08-19). Naming a retired error identity in a
  *new* handoff tripped
  `test_retired_inline_refusal_identity_is_absent_from_live_sources`, whose roots cover all of
  `docs/handoff/` — roots this coordinator widened, in an earlier pipeline, for exactly this
  reason. It broke a running implementer session's baseline from a file in a different
  phase's perimeter.
  **Two consequences.** (1) **Before writing any document under a guarded root, run that
  guard** — `pytest tests/unit/docs/` costs 1.3 s. (2) When a document must *describe* a
  retired identity, describe the behaviour and tell the reader to search their own codebase;
  do not spell the token. Explaining the omission in one line is more useful than the token
  anyway — it tells the reader the convention.
  **Parallel phases share a baseline.** Plan 3 and plan 4 have disjoint file perimeters and
  still collided, because a test's roots are not a perimeter. When two phases run at once,
  each session's baseline is the *other* session's live output.
- **When an obligation is reciprocal, BOTH sites must be inside the perimeter — and the
  sweep is for the class, not the instance** (implement r1b blocker, 2026-08-19). Three
  consecutive implementer sessions blocked on the same shape: an obligation requiring a
  comment at two sites while only one site was authorized. The first two fixes patched the
  instance in front of me and the next instance blocked the next session. **The fix that
  ended it was a grep**: every "comment at both sites" obligation across the master plan, the
  plan and the intention, resolved in one pass — exactly two of them, now both enumerated in
  `plan_2.md` §2's roster. **When a blocker reveals a *pattern*, search for every instance
  before writing the correction.** Patching instances serially costs one session each.
- **A perimeter's file count belongs in the plan, stated once, not computed by whoever needs
  it** (same blocker). The r1b prompt said "nine files" where 7 + 3 = 10, and the plan's own
  exception header still said "Two edits" when there were three. A count restated in a
  second document is a count that drifts; `plan_2.md` §2 now carries the roster and the
  prompt points at it.
- **When a correction lands in two places, fix both in the same edit — a criterion is a
  place** (implement r1 blocker, 2026-08-19). L1's fix was applied to `plan_2.md` §2 and not
  to C16, which still carried the retired equality form; the plan then contradicted itself
  and blocked an implementer session. **After amending a plan's task or perimeter text, grep
  the criteria for the old form.** The charter's home-artifact rule stops a change being
  patched *downstream*; it does not stop one being applied *incompletely* within its home.
- **A perimeter stated as a blanket prohibition must be narrowed the moment an exception
  needs it** (same blocker). §2 read "No change to `price_scenario.py`" while an enumerated
  exception required a comment in that very file. Both statements were mine and one had to
  give. Prefer *"no change to any executable line"* over *"no change"* wherever a
  comment-only exception is foreseeable.
- **The mutation check is on the ASSERTION FORM, not on the fixture** (phase 2 projection,
  L1 — earned against the coordinator, immediately after the rule below and in the act of
  applying it). The fix for N8 replaced a non-discriminating fixture with a discriminating
  one and kept the assertion form `f(0) == f(1)`. That form is invariant under
  `max(1, ·) → max(6, ·)` **at every `B`**, because the mutation maps both call sites to the
  same divisor. A right fixture reached through a wrong comparison is still decoration.
  **Prefer an exact literal over an equality between two calls**: the literal carries the
  discriminating power, the equality throws it away. Four inert checks in this project now,
  two of them mine.
- **A fixture whose expected value is the same under the defect proves nothing, even when
  the assertion beside it bites** (re-review r3, N8 — earned against the coordinator). The
  strengthening assertion `slider_domain(B, 0, I) == slider_domain(B, 1, I)` was specified to
  pin the clamp *target*. At the fixture's own `B`, the bands at `Q = 0`, `Q = 1` and `Q = 6`
  are identical, so `max(6, quantity)` passes it. **Before adding an assertion that claims to
  discriminate, evaluate the function at the values it is meant to tell apart** — here, one
  call each at `Q = 1` and `Q = 6` would have shown they coincide. An assertion that reads as
  evidence and is not is worse than its absence, because it stops anyone looking again.
- **On a pending `ai_inferred` item, EVIDENCE can be re-anchored but SOURCE LINKS cannot —
  those need reject-and-re-record** (card 1 of phase 2's review, 2026-08-19). The review
  path's `edit` decision carries `anchors`, which reaches the evidence entries and nothing
  else. `archgraph_repair_anchors` returns `INTERNAL_ERROR` on such items (reproduced twice,
  on a re-anchor and on an unlink/link batch); `preview_maintenance_changes` refuses them by
  design; and `apply_changes` refuses an overlapping-but-different link so it cannot append a
  competing mapping. **Why it is worth the reject:** a source link's `contentHash` drives
  staleness detection, so a drifted span wires that alarm to the wrong region — it fires on
  edits to an unrelated test and stays silent on edits to the rows the claim rests on. A
  monitoring signal pointed at the wrong lines is worse than none.
- **⚠ CORRECTED at the 2026-08-20 closeout — the first clause of this rule was wrong, and
  wrong in the expensive direction.** `archgraph_repair_anchors`'s `INTERNAL_ERROR` is **not**
  caused by the item being pending `ai_inferred`. At closeout it failed on a
  **`human_confirmed`** node, and then the identical work succeeded **one operation per call**:
  a 4-op batch (2 `unlink` + 2 `link`) returned `INTERNAL_ERROR` with empty `details` and wrote
  nothing, while four single-op calls with the same payloads all applied. Re-reading this
  rule's own evidence, both historical reproductions were multi-operation — *"a re-anchor and
  an **unlink/link batch**"* — so the original diagnosis attributed to the review state what
  the batch appears to explain. **Why it mattered:** believing the tool unreachable sends a
  session to `reject`-and-re-record, which destroys provenance and returns a rebuilt copy to
  the back of the queue, when a sequence of single calls would have done it. Filed at
  `archGraph_mapping_mantainance/open/tooling-repair-anchors-batch-and-contains-canonical-check.md`;
  whether the trigger is *multiple operations* or *mixed kinds* is not established.
- **The review path's `anchors` reach EVIDENCE entries only — NOT `sourceLinks`** (coordinator,
  2026-08-20). A `promote` carrying `anchors` repaired both evidence addresses on
  `projection-item-economics-task-price-scenario` and preserved the old ones under
  `metadata.evidenceHistory` exactly as documented — and `staleNodeCount` stayed at **1**,
  because the node's two `sourceLinks` still pointed at the pre-phase-3 spans with
  `stale: true`. **Staleness is computed from `sourceLinks`, so re-anchoring evidence alone
  leaves the alarm aimed at the wrong lines while the record reads as repaired.** Fixing them
  is `unlink` then `link` through `repair_anchors`, one operation per call; the server
  recomputes `contentHash` itself. Verified: `staleNodeCount` 1 → 0.
- **A pending `ai_inferred` item can only be corrected through the REVIEW path, and its
  preview must be verified by reading the `anchors` block** (coordinator, 2026-08-19, N9
  fix). `preview_maintenance_changes` refuses pending `ai_inferred` items by design — the
  review path with an `edit` decision carrying `anchors` is the route. *(This rule's original
  second reason, that `repair_anchors` refuses them, is corrected above.)*
  Then the trap the archgraph skill names fired live: a preview whose `anchors` array had
  been dropped produced **the identical `decisionSetHash`** (`19159d56…`) as the one that
  carried it. Applying it would have recorded a decision and moved nothing. **The hash does
  not cover anchors. Read the `anchors` block, every time.**
- **Don't put counts in evidence summaries** (coordinator, fix r2 fold — earned on my own
  record within an hour of writing it). An archgraph evidence summary is **immutable through
  both review and maintenance**: a stale number in one can only be corrected by rejecting the
  item and re-recording it. Describe what the evidence shows, never how many of them there
  are; prefer symbol anchors over line spans — **but not both on one entry** (N9), since a
  symbol-based re-anchor then silently narrows a module-wide span to that one symbol.
- **Corollary — inert mutations are inherited, not invented.** All three came from §12A,
  faithfully transcribed into the plan. A wrong criterion propagates downstream unchanged
  because each layer is copying, not re-deriving. Corrections therefore go **upstream first**
  (home-artifact rule), or the next phase plan copies the same defect from the same source.
- **"Record the decision" needs a named medium, or it defaults to the handoff — which
  archives** (review r1, phase 3). Three of that phase's seven repairs were decisions rather
  than code, and the plan asked for each to be *"recorded in the handoff with its reason."*
  The implementer complied exactly, and **two of the three were then invisible to the reader
  they were written for**: F8's justification pointed at a criterion label that archives, and
  F9's latency acceptance lived only in a document that archives. **A criterion asking for a
  recorded decision must name where the record lives after closeout** — code comment, master
  plan, or graph node. The call site wins whenever the reader is the person who will question
  the code, because it is the only medium that cannot be archived away.
- **A cross-reference from production code must resolve from a clean checkout with no
  pipeline documents present** (review r1, phase 3 — the testable form of the rule
  `force_task_ready` earned). This rules out criterion IDs, round numbers, mutation nicknames
  and **bare line numbers** in one sentence. The house convention is `path:symbol` and already
  satisfies it in four places. *Earned twice in one round*: the review found `(C10)` in the
  tree, and the coordinator then found `item_valuation.py:35` inside the review's own verbatim
  replacement text — **reviewer prose enters the tree with no second reader**, the same lesson
  phase 4 earned across r2 and r3.
- **A test's determinism aid is a mechanism, and rule 5 applies to it** (review r1, phase 3).
  *"Forcing a heap scan and a deterministic live-tuple order"* is two adjectives standing in
  for a contract, and **one of the two did nothing** — one probe each showed which. When a
  fixture has to be strengthened before its ledger row is accepted, **the strengthening is
  itself a claim that needs its own both-sides check.** The failure it sets up is specific:
  the next editor preserves the conspicuous scaffolding and reorders the plain lines that
  actually carry the discrimination.
- **A comment that asserts a property is a claim, and it inherits rule 2** (coordinator, fix
  r2 fold, phase 3). The correction for a *dangling* cross-reference ended
  *"the three predicates below this one are load-bearing"* — a positive, checkable statement
  about three predicates, written without checking any of them. **One was untested**:
  deleting `ItemValuation.is_deleted.is_(False)` left the phase file 49/49 green, while a live
  `DELETE` route makes soft-deleted valuations an ordinary state. So the fix for a comment
  nobody could resolve produced a comment nobody had verified — **and the honest label made
  the reader more likely to trust the unverified part**, because the same line now correctly
  disclaims the one predicate that *is* redundant. When a comment says a thing is load-bearing,
  drop it and see what goes red **before** the comment ships.
  **Extended at re-review r4, and the extension is the whole point: sweep the class, not the
  instance.** r3 probed *one* of the five predicates those two sentences vouch for and stopped
  there. r4 probed all five, one mutation at a time, each whole-suite and ID-diffed:
  **three of the five were asserted by nothing, and one of the three was not load-bearing at
  all** — `TaskStep.is_deleted.is_(False)` duplicates a Python filter in
  `group_steps_by_section` and cannot change a result, so the comment had it exactly backwards.
  **A sentence with a count in it — "the three below", "the two below" — is a checklist**, and
  this project's own blocker rule (*when a finding reveals a pattern, search for every
  instance before writing the correction*) applies to prose as much as to code. Fourth round it
  would have saved.
- **A fake session makes a `WHERE` clause untestable, and the tests that look like they cover
  it do not** (re-review r4). `_TypicalSession.execute(self, _statement)` discards the
  statement and pops pre-built results, so the eight `_typical_block` tests never issue SQL and
  none of that query's predicates can be observed.
  `test_c5_deleted_steps_do_not_create_a_participating_section` reads exactly like coverage of
  `TaskStep.is_deleted.is_(False)` and proves the **Python** filter instead. **Before citing a
  test as proof of a SQL predicate, check that the test issues SQL.** The phase-2 lesson *"a
  file whose every dependency is monkeypatched is a unit test"* has this corollary and did not
  state it.
- **After correcting a claim in code, grep every live document for the old form in the same
  edit** (re-review r4, H-2). The `TaskBudgetStatus` correction landed in the service file and
  in the fix handoff and reached **neither document that outlives them** — plan 3's Review log
  and this tracker, where one row recorded the correction while another asserted the error two
  rows apart. **A Review log entry is a compression, and compression is where qualifications
  die**: the reviewer's own r1 criterion row named `result: ItemCostResult | None` correctly;
  the log said "no objects". The log is what survives closeout, so it is the copy that most
  needs the qualification, not least.
- **"Enough rounds" is a judgement about code, not about evidence** (re-review r4). Phase 3's
  production file has been correct since `ef55f6d` — **zero executable lines changed across
  three fix rounds**, proven by diffing the non-comment delta. Every round since has been about
  whether the file tells the truth about itself. **A phase whose fix rounds change only comments
  is not a phase that is dragging; it is a phase whose code was right and whose evidence was
  not**, and stopping early there ships a file that lies to the next reader about which lines
  are safe to delete.
- **A comment at the head of a multi-predicate `WHERE` annotates the whole block to a
  skimmer** (review r1, phase 3). Two of this project's rounds were spent on filters nobody
  asserted; a "Redundant defence-in-depth" line one row above the very predicate the phase
  existed to protect is the converse error, and worse. Scoping language — *"this line only"*,
  *"the three below this one are load-bearing"* — costs six words.
- **A criterion naming a rounding MODE needs a fixture where the modes disagree — and one
  fixture rarely settles all of them** (extended at review r1, phase 3). C3's `11.5` separates
  half-even from truncation and **not** from half-up; C4's `10.5` carries the half-up half.
  **The pair pins the mode; neither row does alone.** The earlier form of this rule read as
  though one fixture could.

## 6. Environment

- Working directory `backend/app/`; infra `make dev-up`; tests
  `PYTHONPATH=. pytest -m 'not e2e'`.
- **Start baseline: 2320 passed / 26 failed / 1 deselected** (2347 collected), head
  `f1c0ebb`, branch `main`. **Measured by the coordinator, 2026-08-19, on a clean tree** —
  a full run of `PYTHONPATH=. pytest -m 'not e2e'` completed in 118.54s. The figure is
  verified, not carried over from the previous pipeline's closeout, and the 26 failure IDs
  are byte-identical to that closeout set.
- **PHASE 2 adds routes**; phase 1 adds none. The route-mirror counts move 25 → 26 (HC-2a)
  in phase 2 only. *Corrected 2026-08-19 at the implement r1 fold — this line read "This
  phase ADDS routes" from when the project was a single phase, and after the split it
  contradicted plan 1's own perimeter. Raised by the implementer, who was right to flag it
  rather than reconcile it silently.*
- **SUITE INSTABILITY — measured at ±1 in BOTH directions.** On unchanged code the failure
  count has been observed at **25, 26 and 27** across separate full runs, with byte-identical
  ID sets and no duplicates. Inherited, not introduced by any of these pipelines.
  **The drifting test now has a name, after three pipelines of "unidentified".** On commit
  `ef55f6d`, four independent full runs by three observers split two-and-two, and the single
  differing ID was the same one every time:

  ```
  tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py::
  test_c3_real_concurrent_open_insert_translates_the_loser[model]
  ```

  | Observer | Failed | That ID |
  |---|---|---|
  | Implementer (phase 3 r1b), run 1 | 27 | present |
  | Implementer, run 2 | 27 | present |
  | Coordinator | 26 | absent |
  | Reviewer (phase 3 r1) | 26 | absent |

  It passes **1/1 in isolation**, and it is a *real-concurrency* test — the one kind whose
  outcome depends on suite-wide load rather than on the code. **A leading candidate, not a
  confirmed diagnosis**; confirming it is its own session and is outside every plan in this
  project. Nothing was touched.
  **Tally as of re-review r4 — 21 full runs, and only the first two are red**: implementer r1b
  27, 27; every run since 26, across coordinator (×8), reviewer r1 (×1), fix r2 (×2), fix r3
  (×2), re-review r4 (×4), coordinator r4 (×2).
  **A SECOND drifting test exists, and this section's one-test model was wrong.** On the
  coordinator's first `item_id` mutant run at r4 the suite read 27, and the added ID was
  neither the concurrency test nor anything the mutation could reach:

  ```
  tests/integration/services/commands/shopify/test_process_shopify_products_integration.py::
  test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task
  ```

  The run was repeated per this section's own rule and came back **26 with the baseline set
  byte-identical**, so the shopify row was a flake and the `item_id` finding stands. **But it
  is a different flake from the concurrency one**, observed once in 21 runs. So the ±1 drift
  is not one test misbehaving; it is **at least two**, and any future attempt to "fix the
  drifting test" that assumes a single culprit will close half the problem and declare victory.
  **What produced both names was recording the ID rather than the count, every time** — the
  discipline was already in this section; only the bookkeeping was missing. **And the repeat
  rule is what saved the finding**: a single 27 would have been read as the mutation biting.
  **Binding consequence: a single run is not evidence.** A run disagreeing with the
  baseline count is repeated and its **ID set** diffed before any conclusion is drawn. Only
  an ID added or removed across repeated runs is a finding. A count alone — higher or lower
  — is noise.
- The suite leaves ~24 `task_steps` and ~40 `step_state_records` behind per full run, from
  tests outside these pipelines. Row-count drift is never evidence of a code change.
- **Nothing in this pipeline writes to the database.** A handoff reporting new rows from
  this feature's own tests is reporting a defect, not residue.

## 7. Gates

### Mechanism-inventory — REQUIRED, NOT WAIVED (coordinator, 2026-08-19)

The two prior pipelines waived this gate and were right to: one was a comparison with two
inputs, the other a composition of two already-contracted mechanisms. **This one is the
case the gate was built for.** Charter rule 6 triggers on every mechanism the feature
ships:

| Mechanism | Rule-6 trigger |
|---|---|
| M1 §3.1 | money arithmetic, quantization, an explicit rounding-mode contract that must hold in **two languages** (Python server, BigInt client) |
| M1 §3.2 | a numeric error bound asserted as a contract |
| M2 §4.1 | a search whose correctness rests on a monotonicity argument |
| M3 §5.2 | a statistic with a substitution fallback that must agree with a second screen |
| M5 §7.2 | a derived band with a step rule |

A silent-failure mechanism without a contract-grade definition is a gate failure, and
this feature is nothing but silent-failure mechanisms: every one of them produces a number
that looks plausible when it is wrong.

**Gate result, 2026-08-19: PASSED.** All eight mechanisms left with contract-grade
definitions; three owner cards raised and closed (D8–D10); ledger empty.

**Calibration outcome — the seal, opened.** Before authoring the prompt the coordinator
found three defects by arithmetic and sealed them in
`prompts/coordinator/2026-08-19_inventory_calibration_seal.md`, unopened by the session
(mtime confirmed). All three were found independently by the sweep, two of them deeper
than the seal had them: M5's band (the seal had three contradictions; the sweep added that
no step ladder produces 15 000 and that the `min_minor` floor sits off-grid),
`infeasible_at_or_below_minor` undefined, and the §12.6 status-matrix miscount — where the
sweep went past the seal entirely and found that the resolver cannot produce `ok` or
`infeasible` at all, which is what turned a test-criterion defect into owner card 1 and a
screen that would have been blank for every first pricing.

Two conclusions worth keeping:

- **The seal's method hint was the only assistance given**, and the sweep found findings 2
  and 3 without one. The gate is not a rubber stamp of the coordinator's own reading.
- **The document's self-assessment pointed away from its weakest section**, exactly as the
  seal predicted. §14's closing line nominated M1's error bound and M2's monotonicity;
  both survived. Every defect worth a round was in a mechanism nobody flagged. **Standing
  consequence: an intention's own "what to attack" line is a hypothesis by the author, and
  a prompt must forbid it as a scope.** That instruction is now doctrine for this project.

**Not everything the sweep produced was right.** §9A.1's "the resolver can return only
nine of the twelve" is ten, contradicted by its own B1–B10 table and by §12A's correct
"eleven non-`ok` values". Found by the coordinator at the fold and corrected in place with
its reason left visible. Enumeration is one of the two clusters the graph-review evidence
identifies as failure-prone, and this one sat *inside a correction of a miscount*.

**Exit condition (met):** every mechanism in the table has a contract-grade definition **in
the intention**, added as lettered sections (§7A style) so no existing citation is
renumbered, with a changelog entry.

### Projection — REQUIRED (pre-declared)

Charter rule 6 triggers hard; the trigger list above is the same list. The projection gate
is **not** waivable for any phase implementing M1, M2 or M5. It may be waived, with a
recorded one-line justification, for a phase that ships only the route mount and role
admission.

*If an implementer finds an uncontracted mechanism, that is a STOP, not a judgement call.*

### Review

**Full rounds, not the light MVP round.** The MVP calibration's cheap first review is
earned by a projection having walked the mechanisms against real data *and* by most of the
surface being non-rule-6. The second condition fails here.

### Closeout obligations — the frontend handoff (tracked here so they cannot scatter)

**This pipeline writes backend code only.** No frontend file is in any perimeter. But the
feature's value is realised by a screen this repo does not contain, and the intention
places four obligations on the closeout handoff in four different sections. They are
collected here because an obligation recorded only at its point of origin is an obligation
that gets dropped at the gate.

| # | Obligation | Origin |
|---|---|---|
| 1 | **The M1 arithmetic, specified for a second language.** Per operation: integer arithmetic on both sides, BigInt, no float, never a language `round()` (half-away-from-zero). The client executes this function every frame; an ambiguity here makes two screens disagree at the chip's flip point. | §3.1, HC-5 |
| 2 | **Name the accepted divergence.** On a task carrying excluded-step time this screen's `AT PRICE` exceeds the production-time screen's distributable total by exactly `charged_seconds`. D5 ratified it; an accepted inconsistency nobody wrote down is indistinguishable from an undetected one. | §5.4, D5 |
| 3 | **The Save flow**: Save is `POST …/evaluations/commit`; `can_commit: false` **disables** the button; reconciling the commit response against the displayed figures is mandatory, not advisory. | §11, D4 |
| 4 | **Amend §8.4 of `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`** — its *display prohibition* only. Its contract (a valuation is per item, never per unit) is unchanged and stays. | D1 |
| 5 | **Amend §6's status→treatment table in the same document.** D8 publishes `model`/`anchors`/`domain` under `item_unvalued` and `item_missing_expected_price`, where that table says the numerics are `null`. A live consumer reads it. HC-3 is untouched — this endpoint is ADMIN/MANAGER only. | D8, §9A.1 |
| 6 | **State that Save cannot create a valuation row.** With no current valuation the commit path refuses regardless of the price in the body, so `can_commit` is `false` and the purchase price must be set first through `PUT /items/{id}/valuation`. This is the written form of D9's precondition. | D9, §9A.2 |

Obligations 4 and 5 edit a published document and therefore need an enumerated file
perimeter of their own when the closeout phase is planned. Neither is a licence to revise
that handoff generally.

**Obligation 6 is different in kind and must not be dropped as boilerplate.** D9 —
Save stays one call — is the only decision in this pipeline whose soundness rests on
something outside this repository: a frontend flow that sets the purchase price, and
therefore creates the valuation row, before the price screen is reachable. The backend
cannot enforce it and will not fail loudly if it stops holding; the screen will simply
save nothing, every press. Writing the precondition into the handoff is what converts an
assumption about another codebase into a contract. Unwritten, it is a defect waiting for
the first optimisation that skips the prompt.

### Commits

Checkpoint commits at every `IMPLEMENTED`, prefixed `CHECKPOINT (not approved):`, under
the owner's standing authorization. The phase is committed again at its approval gate.
Checkpoints are never squashed.
