# Plan 6 — Closeout: the frontend handoff, the living docs, the graph

```
plan: plan_6
project: narrow_typical_work_times
state: APPROVED
projection_gate: WAIVABLE — no rule-6 code surface. The coordinator records a one-line
                 justification if it waives.
```

## 1. Goal

Publish what the frontend must do differently, correct the one **published** instruction this
pipeline supersedes, bring the living docs back into agreement with the code, and leave the
architecture graph accurate.

**Explicitly NOT in this phase:** no production code change, no test-behaviour change, no
golden regeneration, and — the standing rule — **no edit to any published handoff**. If a
production defect is found here, it goes back to the phase that owns it as a fix cycle; it is
not patched from a closeout phase.

## 2. Read first

- Master plan §§4, 5, 6.5, 6.7, 8, 9, 10.
- Intention **header**, then §5 (the two pathways and the statistics-vs-task numeric
  difference), §6.3 (**the exact eligibility phrasing — normative, do not paraphrase**), §6B
  (what the `is_estimated` message actually is), §7 (the always-present rule), §7.1 (D24),
  §7.2, §7.3, §7.4, §9 (what is deferred, with its return paths), **§11.3** in full, §4C
  (what is now unreachable on the wire).
- **Intention §3A C3, and `plans/plan_2.md` §6 C11's named conversion trigger** (phase-2
  review N3). C11 is held **structurally** today — the compiled predicate is asserted to be
  a `coalesce` over the conjunction, because three-valued logic and `FALSE` are
  indistinguishable inside `count(...) FILTER (WHERE …)`. It **converts into a behavioural
  criterion the first time a predicate negates the item match**, and this plan is the one
  whose scope names **`ANSWER_AS_ASKED`** — a complement query is exactly the trigger. If
  this phase writes one, it owes the row: a primary-less task must be **excluded** from the
  negated population too, not swept in via `NULL`.
- `planning/owner_decisions.md` — D18, D19, D20, D23, D24, **D25**.
- Gate handoff §5 item 2 (the `is_estimated` message is materially different from the one §6.4
  was going to send).
- The Review logs of plans 1–5 — **including the projection handoffs' ledgers**, not only the
  intention's sections. A read order built from section numbers misses lettered sections a
  projection added.
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`
  §Worker task-step cards — **read it, do not edit it.**
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` — the
  shape a published handoff takes in this lineage.
- `app/tests/unit/docs/test_item_economics_docs.py` and `test_item_economics_handoff_accuracy.py`
  — **the guard decides which living docs must move, not judgement.**

## 3. Dependencies

**Gate: plan 5 `APPROVED`.**

## 4. Files expected to change

**New**
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_narrow_typical_work_times_<YYYYMMDD>.md`

**Modified — only if the guard names them**
- `docs/domains/item_economics/README.md` · `api.md` · `events.md` · `states.md`
- `app/tests/unit/docs/test_item_economics_docs.py` /
  `test_item_economics_handoff_accuracy.py` (new pinned assertions for the new document)

**Modified — closeout bookkeeping**
- `master_plan.md` (tracker rows to `APPROVED`)
- `plans/plan_<n>.md` Review logs

**Read-only, and a change is a finding**
- Every file under `app/beyo_manager/`, every golden, and
  `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`.

## 5. Ordered tasks

1. **Run the docs guard FIRST**: `PYTHONPATH=. pytest tests/unit/docs/` (59 tests, ~3 s). It
   costs nothing and it is what tells you which living docs are pinned to which semantic
   authorities. A tripwire in this suite has broken a running implementer session's baseline
   from a file in a different phase's perimeter once already.
2. **Write the new dated handoff.** §11.3's obligations, each as its own section:
   - **`ALLOCATION_METHOD` v2**, with §6.3's exact eligibility phrasing quoted, not
     paraphrased: every task is now evaluated under the new rule; allowances are **eligible**
     to change wherever item-category narrowing changes the relative section weights; many
     tasks remain numerically identical (primary items with no category; tasks reconciling to
     `section_wide_uniform`; categories whose narrowed ratios coincide with the section-wide
     ratios); **the contract changes even where an individual numeric result does not.**
   - **Every new field, with its nullability and the reachable state that produces each null.**
     Not a key list — a key list passes while getting the harder half wrong. `applied_filter`
     is the one deliberate `null`, and the state that produces it is "the task's primary item
     has no category, or there is no primary item".
   - **The `is_estimated` clarification — and it carries NO value change.** This is materially
     different from the message §6.4 was going to send. Read literally, §6.4 would have flipped
     the flag to `false` for a task with zero participating sections; §6B keeps that disjunct
     verbatim, so every existing value is preserved. Say plainly: *nothing to change; the
     definition is now written down.* Also state §6.4's genuine content — reconciling to
     `section_wide_uniform` alone does **not** set the flag — and the `sections_without_sample`
     scope (participating sections whose **selected** typical is null or ≤ 0, **not** sections
     without a narrowed sample).
   - **D25's unreachability, so nobody codes a branch for it**: `typical_worker_seconds: 0`
     beside `typical_basis: "item_narrowed"` is **unreachable on every task surface**. The
     reachable zero-statistic form is `section_wide` + `0`, and a zero **is** a statistic — it
     is never published as `insufficient_sample`.
   - **`/working-sections/typical-times` is unchanged** (D24) — no params, no response change.
   - **The statistics-vs-task numeric difference (§5)** stated as *deferred*: the same evidence
     can legitimately produce `540` for task economics and `null` for analytics, and this
     becomes visible only when `/statistics/typical-times` ships (§9). Do not describe an
     endpoint that does not exist.
   - **The worker-card re-pointing, as a supersession.** Name
     `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md` §Worker task-step cards
     and supersede **one instruction** of it: the cards' fallback typical comes from
     `budget-allocations` `steps[].typical_worker_seconds` (already present in the `no_budget`
     state, and item-aware after this pipeline); **the bootstrap `typical-times` fetch, cache
     and join are deleted from the card path.** One batched call per feed page (≤50 task ids)
     remains the cards' single economics source; `typical-times` stays a task-free benchmark
     surface.
     *Why*, in one line the frontend can act on: a client-side cached generic typical beside
     item-aware card figures would contradict production-time's degraded state for the same
     task and section — the last place cross-surface disagreement could survive.
   - **A cost line** for any instruction that changes *when* an endpoint is called. A
     correctness fix to a client instruction needs one: the reviewer who corrects the timing has
     no reason to look at what the call runs, and the frontend has no way to.
3. **Never edit the 2026-08-18 handoff.** Supersession is a new dated document naming the old
   one. An in-place edit of a published handoff cost the frontend four days in this lineage,
   building a feature on a refusal that no longer existed.
4. **Update the living docs the guard names**, and extend the guard with pinned assertions for
   the new document if the existing tests' pattern calls for it (they pin semantic authorities
   by literal). If a document must *describe* a retired identity, describe the behaviour and
   tell the reader to search their own codebase — **do not spell the token**; the retired-identity
   guard's roots cover all of `docs/handoff/`.
   Widen an allowlist rather than removing a filter: removing the guard's extension filter makes
   it crash on a binary file in its own root and go red forever for the wrong reason.
5. **Architecture graph — rewritten at the pre-dispatch lint, 2026-08-24.** The published text
   is superseded in full; it predates the span-removal policy and is wrong in three ways.
   **What it now says:**
   - **This phase changes no code, so it almost certainly owes no graph delta. Check, do not
     assert** — and if nothing changed, say so and record nothing.
   - **Anchoring: follow `.archgraph/agent-operating-policy.md`.** It is committed, authoritative,
     and is the policy's home. Do not take instruction on anchoring from this plan.
   - **Do not gate on `staleNodeCount`, `pendingReviewCount`, or any count under `.archgraph/`.**
     The published text demanded *"0 pending / 0 stale / 0 diagnostics"*. Measured 2026-08-24:
     `staleNodeCount` is **5**, and all five are **outside D31's authorized scope by name**. A
     session gating on zero would halt on a correct tree. `.archgraph/` is the owner's working
     area — **report what you observe there; never gate on it.**
   - **Never promote, reject, edit or re-anchor a graph item on your own judgment.** Adjudication
     is the owner's, `archgraph_repair_anchors` takes one operation per call, and a
     `humanInstruction` string is never authorization.
   - **Known and not yours:** `prompts/maintenance/20260823_archgraph_reanchor_prompt.md` (D29) is
     live, unconsumed, and **scoped to `re-anchor`, an operation measured on 2026-08-24 to change
     evidence-anchor records rather than source-link objects** — it cannot remove a span. It must
     be rewritten before it is ever dispatched. **Do not dispatch or execute it.**

   *Why the published text was wrong:* it demanded accurate **spans** on the nodes plans 2, 4 and
   5 touched and told the session to re-derive each from its symbol — instructing work the
   span-removal policy has retired. This is the correction master plan §8's D30 lesson recorded as
   still owed by plan 6; plan 5's half was applied at its fold.
6. **Close the tracker.** All six rows `APPROVED`. Move closed prompts and handoffs into
   `archive/plan_<n>/` at the coordinator's closeout ritual, together with the gate commit.
   Historical path references are **not** rewritten — they resolve under `archive/` by
   convention.
7. **Read every document in the phase end to end, regardless of delta.** A final round does
   this because the finding that survives is the one in a file nothing changed.

## 6. Tests / acceptance criteria

> **⚠ Trace cells added at the pre-dispatch lint, 2026-08-24 — manifest property 5.** This plan
> was authored before the charter's trace chain and carried none. Assigned below at source, and
> **two published rows were demoted rather than given a trace they do not have**: a row that
> serves no measurement-ledger entry and no mechanism contract is cut, not decorated.
>
> | row | trace | note |
> |---|---|---|
> | **C1** | — | **Demoted to a task obligation.** It guards *this session's own writes*, not a property of the shipped system. Task 1 already runs it first; its planted-defect probe (name the retired identity → the guard reddens) is retained there as a **rule-15 probe**, which is what it always was |
> | **C2** | **M3** · **M6** | Every published field's nullability and the reachable state producing each null — M6 is "published fields mean what their contract says", and the frontend cannot honour a contract it was not told |
> | **C3** | **M6** | D25's unreachable shape: `item_narrowed` beside `0` does not occur, and a zero **is** a statistic. A frontend null-check treating a legitimate `0` as "no data" is M6 failing at the last hop |
> | **C4** | **M3** | The supersession deletes the cached generic typical from the worker-card path — **literally the last place two surfaces could show different typicals for one task**, which is M3's whole subject |
> | **C5** | — | **Demoted to the closeout ritual.** Tracker rows and Review-log completeness are pipeline bookkeeping, not a measurement. Task 6 owns it, and the plan already conceded it is *"not automatable — stated as a reviewer check"* |
>
> **Three criteria remain: C2, C3, C4.** Sizing PASS. Every remaining row traces; the two that
> could not have been made to trace honestly were cut instead.


**C1 — the docs guard is green.** `PYTHONPATH=. pytest tests/unit/docs/` passes, before and
after every write under a guarded root.
*Mutation* — name the retired inline-refusal identity verbatim in the new handoff →
`test_retired_inline_refusal_identity_is_absent_from_live_sources` goes red (its roots cover
all of `docs/handoff/`).
*Both sides* — contract: **zero failures**; mutation: 1 failed, naming the new file's path.
**The count is deliberately not pinned** (corrected at the pre-dispatch lint): the guard collects
**59** today, and **task 4 of this plan adds pinned assertions to it**, so a criterion asserting
`59 passed` would fail on green code after the phase's own work. Derive the count when you run it;
assert the failure count, which is stable.

**C2 — every new payload field in the handoff is annotated nullable-or-not, and every
annotation names a reachable state that produces the null.** Asserted by a pinned docs test
over the new document: for each of `typical_basis`, `sample_count`, `narrowed_sample_count`,
`section_sample_count`, `typical_resolution`, `applied_filter`, the document contains the
field's name **and** an explicit non-nullable / nullable statement; and `applied_filter`'s
nullable statement names the producing state.
*Mutation* — the docs test (definition): drop `applied_filter` from the checked set → the
document could ship with a key list and no nullability, which is exactly how a previous
closeout in this lineage passed the check it was given while getting the harder half wrong.
Contract: six fields checked; mutation: five, and a document missing the one deliberate null
passes.
*Both sides*: with the field absent from the document, contract → red, mutation → green.

**C3 — the handoff states D25's unreachability.** The document contains the claim that
`typical_basis: "item_narrowed"` beside `typical_worker_seconds: 0` does not occur on task
surfaces, and that a zero is published as a statistic (`section_wide` + `0`), never as
`insufficient_sample`. Pinned by literal in the docs test.
*Defect caught*: a frontend branch written for a payload shape that cannot occur, and — worse —
a null-check that treats a legitimate `0` as "no data".

**C4 — the supersession is a supersession.**
(a) The 2026-08-18 handoff is **unchanged** — verified from `git diff` in the session's
perimeter, not from memory.
(b) The new document names that file and the section it supersedes, and supersedes **exactly
one** instruction of it.
(c) It states both halves of the re-pointing: where the fallback typical now comes from, **and**
that the bootstrap `typical-times` fetch/cache/join is deleted from the card path. A blanket
"the cards change" claim needs one statement per member.
*Mutation* — the docs test (definition): check only the "fallback comes from
budget-allocations" half → a document that adds the new source without deleting the old join
passes, and the frontend keeps a cache that is the last source of cross-surface disagreement.
Contract: both halves required; mutation: one.

**C5 — the pipeline's own record is consistent.** All six tracker rows read `APPROVED`; every
plan's Review log is non-empty; the master plan's environment section still matches
`app/pytest.ini` and the published baseline, or has been updated with what changed.
*Not automatable — stated as a reviewer check, not dressed up as a test.*

## 7. Notes

- **The owner-facing message of this pipeline, in product words** (for the closing chat
  message, not for the handoff): the time a task is *expected* to take in each working section
  is now drawn from past work on **the same kind of item**, everywhere the number appears — the
  worker's card, the manager's production-time view, the price scenario and the budget split —
  and when there is not enough same-item history, every surface falls back to the general figure
  **together**, never one at a time.
- **A "record the decision" instruction needs a named medium, or it defaults to the handoff —
  which archives.** Anything decided in this phase that the next reader of the *code* will
  question belongs in a code comment or the master plan, not only here.
- **A comment that asserts a property is a claim.** If this phase writes one ("the three
  predicates below are load-bearing"), drop each and see what goes red **before** the comment
  ships — and sweep the class, not the instance.
- **Verbatim replacement text is unreviewed on arrival.** A re-review's scope is the corrections
  **and** the correcting sentences; four findings in one lineage phase were defects in a
  reviewer's own proposed wording.
- The `/statistics/typical-times` route stays deferred with its contract pre-locked (§7.5,
  §9): `ANSWER_AS_ASKED`, no route override, counts-only diagnostics. Its parser and its policy
  branch shipped in plan 1 — **do not announce the endpoint**, and do not let the handoff imply
  it exists.

## 8. Review log

*(empty — append-only; shared by implementer and reviewer)*

### 2026-08-24 — pre-dispatch lint (coordinator), and the projection waived

**Run per `pipeline-coordinator.md` Responsibility 1c, every property by its command.**

| check | result |
|---|---|
| **Sizing** | **PASS** — 5 published rows, **3 after demotion** (C2, C3, C4) |
| **Intention gate** | **PASS** — `planning/intention.md` header reads `RATIFIED`, checked at source |
| **References resolve** | **PASS.** `tests/unit/docs/` collects; `test_retired_inline_refusal_identity_is_absent_from_live_sources` exists at `test_item_economics_handoff_accuracy.py:221`; all four `docs/domains/item_economics/` files exist; `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md` exists |
| **Counts derived** | **PASS with one correction.** The docs guard collects **59** today (measured, not carried). C2's "six fields" re-counted from its own list = 6 ✓ |
| **Exact outcomes** | **★ FAIL → fixed.** C1's *"contract: 59 passed"* is **invalidated by this plan's own task 4**, which adds pinned assertions to that very suite. A criterion asserting `59 passed` fails on green code after the phase's own work — the same class as plan 5's C7 allowlist, derived from the pre-task tree. Now asserts **zero failures**, count derived at run time |
| **Traces** | **★ FAIL → fixed.** The plan predates the trace chain and carried **no** trace cells. C2 → M3·M6, C3 → M6, C4 → M3. **C1 and C5 were demoted, not decorated** — neither serves a ledger entry or a mechanism contract, and the chain says such a row is cut |
| **Perimeter-vs-guard collision** | **PASS** — no occurrence-count or absence assertion in `tests/unit/docs/` names a file in this phase's perimeter |
| **Standing instructions naming this plan** | **★ FAIL → fixed.** Master plan §8's D30 lesson records plan 6 as **still owing** the graph-paragraph correction. Applied in task 5 |
| **Every verb true of the code it names** | **★ FAIL → fixed.** Task 5 told the session to *"re-derive every span from its symbol"* and to require *"0 pending / 0 stale / 0 diagnostics"*. **Both are false now**: the span-removal policy has retired span emission entirely, and `staleNodeCount` is **5** — all five outside D31's scope by name, so a session gating on zero halts on a correct tree |

**Four failures, all caught before a session opened the plan.** Three of the four are the same
underlying shape: **a sentence that was true when it was written and was never re-derived against
the tree the session would actually open.**

**Projection waived**, per this plan's own `projection_gate: WAIVABLE`. Justification, one line as
the gate requires: **no rule-6 code surface — this phase writes documents, changes no production
code, no test behaviour and no golden**, and the lint above has already discharged the mechanical
half a projection would have found. The owner is session-constrained and this is the cheapest
honest saving available.

### 2026-08-24 — implementation closeout (Codex)

**APPROVED.** Published the new dated frontend handoff and added eight pinned docs cases: six
field/nullability cases for C2, the three-part D25 zero-reachability assertion for C3, and the
two-sided worker-card supersession assertion for C4. The guard moved from 59 to **67 passed**.
The tests-first baseline was **8 failed / 59 passed**; all failures named the not-yet-created
handoff.

Three declared probes were observed and reverted: one planted retired-identity defect reddened
the existing guard; C2's definition mutation demonstrated contract red / mutant green for the
one deliberate nullable field; C4's definition mutation demonstrated contract red / mutant green
when the new source remained but deletion of the old join was no longer required. The 2026-08-18
published handoff stayed byte-identical at SHA-256
`88e1c795e8fa5f87bb183670f514fa52439238efb9ad3c4631b91f4245838bfb`.

The initialized graph was read at 199 nodes / 299 edges with no diagnostics. Existing confirmed
nodes already describe the shared typical-filter/reconciliation boundary; this docs-only phase
has no architectural delta, so nothing was recorded and no owner review or maintenance work was
touched. Final L4: **2716 passed / 21 failed / 1 skipped**, failing-ID delta **∅ / ∅** from plan
5. Owner decisions/cards: **0**.
