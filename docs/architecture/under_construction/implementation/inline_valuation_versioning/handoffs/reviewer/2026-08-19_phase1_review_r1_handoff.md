---
plan: 1
role: review
round: 1
verdict: CHANGES_REQUIRED
state: CHANGES_REQUESTED
date: 2026-08-19
actor: Claude (reviewer)
pipeline: inline_valuation_versioning
---

# Reviewer handoff — phase 1, round 1

**Verdict: CHANGES_REQUIRED.** One should-fix (S1), five notes, zero blocking.

The mechanism is correct. M1 is implemented faithfully — the compare/inherit/version
decision, the zero-write no-op, the credit, the chain — and every behavioural criterion
(C1–C8, C10) closes under mutation. The single defect is in the **standing guard for C9**:
the test that exists to keep the retired identity from creeping back does not cover the
perimeter C9 states, and I demonstrated that with a probe. The identity is genuinely absent
today; what fails is the tripwire, not the state.

Fix perimeter is one file already inside HC-1
(`app/tests/unit/docs/test_item_economics_handoff_accuracy.py`), a two-line change.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — authorize a graph anchor correction that is not this phase's doing?

**Question.** May a follow-up maintenance session widen `command-task-create`'s
whole-function evidence anchor from lines 72–580 to 72–594, or should it be left alone?

**Story.** The architecture graph stores, for each piece of the system, the exact lines of
code that back its claim. For task creation it records "lines 72 to 580". The function
actually runs to line 594 — the last fourteen lines, where the response handed back to the
app is assembled, sit outside the recorded range. Nothing is wrong today: the graph reports
zero stale nodes because it only checks where a claim *starts*. But the next agent that
reads "this is the whole command" and edits near the end is working past the edge of the
map. This is old — it was recorded on 15 August, and this phase neither caused it nor
touched it.

**Branches.**
- *Authorize* — one maintenance edit moves the end line; the map matches the code again.
- *Leave it* — harmless today, and the drift grows the next time the function does.

**Recommendation.** Authorize it, batched into the next graph-maintenance session rather
than a session of its own — it is not worth interrupting this phase's close.

**On silence.** Nothing happens; the anchor stays as-is and the gate does not hold on it.

**Trace.** graph node `command-task-create` evidence span; review note N5.

## What I re-derived independently (settled ground)

Everything below I verified myself; the coordinator's prior checks were extended, not
repeated.

**Suite.** Two full independent runs, `PYTHONPATH=. pytest -m 'not e2e'` from `backend/app`:
**2320 passed / 26 failed / 1 deselected**, 117.7s and 118.2s. The 26 failure-ID sets are
**byte-identical to each other and to the 26 declared in the implementer handoff**. Zero
drift observed across the two runs.

**Test arithmetic reconciles.** 2340 → 2346 selected, Δ = +6 = (−2 removed) + (+8 added).
Removed: the rejection integration test, and the retired identity's generated parameter case
in the literal registry. Added: C1–C5, C8 integration + C9, C10 unit. Confirmed against the
diff, not the claim.

**Ruff** clean on all three changed Python files (re-run, not taken on trust).

**The production branch is faithful to M1** (`create_task.py:316-367`):
- The falsy-zero trap is avoided — inheritance keys on `is not None`, so a request price of
  `0` (allowed by `Field(ge=0)`) is kept, not treated as omitted.
- A `NULL` field on the current valuation inherits correctly, including the common seeded
  shape `(1000, None, SEK)`.
- The check constraint `ck_item_valuations_amount_present` cannot be violated by
  inheritance: `(None, None)` is unreachable, since the trigger guarantees at least one
  request amount and the constraint guarantees the current row is not `(None, None)`.
- **No type coercion across the persistence boundary.** `ItemCurrencyEnum` is a plain
  `enum.Enum`, not a `str` subclass, so an enum-vs-string comparison would silently make
  every triple "different". It cannot arise: the column is
  `SAEnum(ItemCurrencyEnum, …)` (`item_valuation.py:22`) and the request field is
  `ItemCurrencyEnum | None`, so both sides of the tuple hold enum members.
- No variable shadowing — `expected_sale_price_minor`, `purchase_cost_minor`,
  `current_valuation`, `should_write_valuation` appear only inside the branch; the retired
  `item_has_current_valuation` is gone with no surviving reader.

**HC-2 holds structurally, not just behaviourally.** Across `beyo_manager/`, `ItemValuation`
is constructed in exactly one place (`_common.py:148`) and `superseded_at` /
`superseded_by_id` are written on that table in exactly one place (`_common.py:146,166`).
The other supersede writes (`commit_item_cost_evaluation.py:292,344`) target
`ItemCostEvaluation`, a different table. No second valuation writer was introduced.

**HC-4 holds.** The trigger (`:316-322`) is byte-identical to its pre-change form; the diff
carries it as unchanged context.

**The no-op writes nothing.** Structural, not inferred: the writer call *and* the
`item_valuation.created` audit are both inside `if should_write_valuation:`. C2/C4/C8 also
assert it behaviourally — row count, surviving `client_id`, unchanged `created_by_id`,
`superseded_at IS NULL`, `superseded_by_id IS NULL`, and zero valuation audit rows. C2's
"before" assertion (`:568`) makes the audit count non-vacuous. "Writes an identical row" is
excluded on both readings.

**The identity is retired.** Repo-wide grep from `backend/`: zero hits under `app/` and
`docs/handoff/`. Nine surviving occurrences, all in `item_cost_calculation` planning/archive
files — provenance, correctly untouched.

**The precedence-disagreement audit passes for every new fixture**, including the two the
prompt singled out:
- **C1's fixture cannot pass if the creator were wrong.** It seeds *two distinct users* —
  the valuation creator and the task creator — and asserts the old row keeps the former
  while the new row carries the latter. Probe P3 confirms: crediting anyone else reddens C1
  and only C1.
- **C4 really is "partial input whose inherited field makes the triple identical."** Current
  `(1200, 400, SEK)`; request sends `purchase_cost_minor: 400` alone; the omitted expected
  price inherits 1200, making the triple identical. It bites **independently on both**
  upstream mutations — breaking inheritance (P1) and dropping the equality check (the
  coordinator's C2 probe) each redden C4 on their own. That is exactly the confound C2 and
  C3 each carry a second reason for, and C4 is not decoration.

**The deleted-assertion mapping is honest.** The removed
`test_c4_row_1_current_valuation_refusal_rolls_back_item_mutation_and_task` pinned four
things. Rows 1, 3 and 4 of the handoff's table are correct as written. Row 2 ("the rejection
rolled back task, task-item and matched-item mutation") is the one where *deliberately
retired* does the most work — and it is the right answer: there is no refusal path left, so
there is nothing to roll back, and a writer failure still unwinds the whole `maybe_begin`
transaction exactly as before. No behaviour it pinned is silently uncovered.

**Rule 11½ (teardown) and rule 4 (no dead scaffolding) hold.** Every new test commits and
owns a `try/finally` calling `_cleanup_committed_workspace`, which opens with `rollback()`
so cleanup runs on the failure path too. All three new `_seed_economic_workspace`
parameters, the `_valuation_audits` helper and `*additional_user_ids` have test callers in
this phase.

**The architecture graph's post-state is as claimed and accurate.** 183 nodes / 275 edges,
revision `0f36b07a…`, 4 pending, 0 diagnostics, 0 stale. I read the code first, then the
stored claim: `command-task-create`'s description now states the inherit/compare/version
behaviour *and* that the audit is recorded only when a row is written — both true. The
`writes_to → table-item-valuation` anchor 316–367 is the branch exactly. The re-recorded
`reads_from → table-item` anchor 236–248 is exactly `find_or_create_item`, the `was_created`
capture, the `Item` load and the `NotFound` guard. Not re-flagged; confirmed settled. (One
older imprecision, N5, card 1.)

**C10's rewritten §9.1 reads correctly to a frontend developer.** All six required facts are
present and the title no longer names a refusal: it re-prices, an omitted field keeps its
current value, differing amounts *or currency* write a new version credited to the task
creator, identical values write nothing at all (row, supersession and audit each named), an
unvalued item still starts a chain without resurrecting a deleted row, and
`PUT /items/{id}/valuation` is called out as continuing to replace wholesale. No residual
refusal claim survives anywhere in the document — the three remaining uses of "refus*"
(`:46`, `:288`, `:579`) are about legacy money keys and commit-status identities, unrelated.

## Ledger

### S1 — should-fix — C9's guard does not cover the perimeter C9 states

**File.** `app/tests/unit/docs/test_item_economics_handoff_accuracy.py:220-225`
(`test_retired_inline_refusal_identity_is_absent_from_live_sources`).

**Authority.** plan_1.md acceptance criterion **C9** — "`ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`
is absent from **`app/`** and from **`docs/handoff/`**"; charter standing rule 1
(criteria are met by automated tests, never manual commands).

**What is wrong.** The test scans three roots — `_PACKAGE` (`app/beyo_manager`),
`_APP_ROOT / "tests"`, and `_HANDOFFS` (`docs/handoff/**to_frontend**`) — and only `*.py`
and `*.md`. C9 names `app/` and `docs/handoff/`. `app/` also contains `scripts/`,
`migrations/`, `run.py`, `seed_*.py`; `docs/handoff/` also contains `from_frontend/` and
`presentation_system/`. The implementer's own bite map claims this test fires when the
identity is "retained **anywhere** under live package/tests/handoff sources"; that claim is
false as written.

**Mutation that demonstrates it (P6, run and reverted).** Wrote the literal
`ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` into `app/scripts/_reviewer_probe_c9.py` **and**
`docs/handoff/from_frontend/_reviewer_probe_c9.md`, then ran the docs-accuracy suite:
**51 passed** — fully green, both plants invisible. Both files deleted; tree verified clean.

**Suggested correction.** Widen the roots to match the criterion:
`_HANDOFFS` → `_BACKEND_ROOT / "docs" / "handoff"`, and `_PACKAGE, _APP_ROOT / "tests"` →
`_APP_ROOT`. If `_APP_ROOT` proves too broad in practice (it will sweep `__pycache__`,
`.venv`, log files), scope it by excluding those rather than by narrowing back to two
subdirectories — and if any root is deliberately left out, say so in the criterion, not
silently in the test. Re-running the P6 plant must turn this test red.

**Note on severity.** The criterion's *state* is satisfied — I verified repo-wide, twice,
that the identity appears nowhere under `app/` or `docs/handoff/`. What does not close is
the automated durability of that state, which is the whole purpose of C9 and the reason it
was written as a standing assertion rather than a one-off check. This is the last phase of
the project, so there is no later phase to carry it to.

### N1 — note — an undeclared rename, contradicting "DECISIONS: None"

The implementer renamed the pre-existing phase-8b test
`test_c1_inline_birth_writes_valuation_and_handles_exact_auto_statuses` →
`test_c7_…` and its six parameter ids `C1-row-*` → `C7-row-*`. Nothing in plan_1.md T3 or
HC-1 asks for this, and it is absent from the handoff's DECISIONS section, which says
"None". It was also not forced: the new criterion-1 test is
`test_c1_different_inline_values_version_chain_and_credit_task_creator`, a different function
name, so the two could have coexisted without a pytest collision.

Cost: two citations in *closed, approved* provenance now resolve to nothing —
`item_cost_calculation/archive/plan_8b/2026-08-15_phase8b_implement_r1_handoff.md:49` cites
the old function name in its mutation-probe table, and
`…/2026-08-15_phase8b_review_r1_handoff.md:187` cites the `C1-row-*` ids in its coverage
table.

The rename is defensible on readability and I am **not** asking for it to be reverted — that
would break this plan's citations instead, and the charter forbids rewriting archives.
The correction is one line of recording: note the `C1-row-* → C7-row-*` mapping in plan_1's
Review log so the archived evidence stays followable.

### N2 — note — two criterion-numbering vocabularies now share one test file

`test_phase8b_inline_task_prices.py` now carries eight tests numbered against *this* plan's
C1–C10 and seven still numbered against `item_cost_calculation` phase 8b's criteria
(`test_c2_absent_inline_prices_…`, `test_c3_legacy_money_rejection_…`,
`test_c4_row_3_…`, `test_c4_row_4_…`, `test_c5_inline_validation_rows_…`,
`test_c5_row_3_…`, `test_c6_router_body_…`, `test_c6_create_task_endpoint_…`). Renaming C1
resolved the head-on collision and left the rest, so `grep test_c4` now returns three tests
spanning two vocabularies. No functional impact; it makes the next reviewer's
criterion→test lookup ambiguous. Cheapest durable fix is a comment banner in the file
naming which range belongs to which plan.

### N3 — note — where C8's trigger guard actually binds (rule 11 bookkeeping)

C8 bites on the canonical broadening but not on a narrower one. Recorded so the next
session does not have to rediscover it:
- **P4a**, `inline_price_requested = request.item is not None` → **C8 red**, plus phase-8b's
  `test_c2_absent_inline_prices_…` and `test_c5_row_3_currency_alone_…`. (C8 bites because
  currency is taken from the request and never inherited, so a price-less request produces
  `currency=None`, which differs from the stored currency and forces a write.)
- **P4b**, adding `or request.item.currency is not None` to the trigger → **C8 stays green**;
  only phase-8b's `test_c5_row_3_currency_alone_…` reddens. C8's fixture sends neither
  amount nor currency, so a currency-only broadening never reaches it.

Not a defect — the suite catches both, and P4b's input class is a different criterion's.
Worth recording per rule 11 ("when two tests divide the labour, the criterion records which
test bites on which mutation").

### N4 — note — the review prompt's stated evidence base spans two pipelines

The prompt names `git diff aa95d5e 6f82579 -- app/tests/` as "the whole evidence base".
`aa95d5e` ("docs: record phase 2 checkpoint hash") predates
`simple_production_budget_division`'s closeout, so that range also carries four test files
from the previous pipeline (`test_budget_allocations_query.py`,
`test_production_time_query.py`, `test_budget_division.py`,
`test_lookup_item_by_article_number.py`). This phase's actual test evidence is
`7262cea..6f82579` — the checkpoint against its own parent, six files. I reviewed the
latter. Lesson for prompt compilation: name the checkpoint's parent, not a remembered hash.

### N5 — note — a pre-existing graph anchor understates the function it maps

Graph node `command-task-create` carries a whole-function evidence anchor of
`create_task.py:72-580`. The function runs 72–594; the response-assembly block at 588–594
falls outside. Recorded 2026-08-15 and untouched by this phase — the graph reports 0 stale
because staleness keys on the start of a claim. **Not a finding against phase 1.** Routed to
owner-authorized graph maintenance; see card 1.

## Criterion → test → mutation table

Definition-site mutations unless marked. All applied to the **post-Ruff final files** and
reverted (see the probe declaration).

| # | Test | Mutation | Site | Bites |
|---|---|---|---|---|
| C1 | `test_c1_different_inline_values_version_chain_and_credit_task_creator` | **P3** `created_by_id=resolved_item.created_by_id` | `create_task.py:365` (**call site**) | **C1 only** ✅ |
| C2 | `test_c2_identical_inline_values_are_a_zero_write_noop` | force `should_write_valuation = True` | `create_task.py:347-355` | C2 **+ C4** ✅ (coordinator, post-Ruff; not repeated) |
| C3 | `test_c3_partial_inline_request_inherits_omitted_current_value` | **P1** pass `request.item.expected_sale_price_minor` through unmerged | `create_task.py:337-341` | C3 **+ C4** ✅ |
| C4 | `test_c4_partial_effectively_identical_request_is_a_zero_write_noop` | both of the above | as above | **bites on each independently** ✅ |
| C5 | `test_c5_currency_only_change_creates_a_new_version` | **P2** drop currency from both comparison tuples | `create_task.py:347-355` | **C5 only** ✅ |
| C6 | `test_c6_never_valued_existing_item_accepts_first_inline_price` | not separately probed — asserts a valuation exists with an exact figure, unreachable without the writer | — | non-vacuous by construction |
| C7 | `test_c7_inline_birth_writes_valuation_and_handles_exact_auto_statuses` (6 exact rows) | unchanged phase-8b coverage, renamed only (N1) | — | inherited |
| C8 | `test_c8_no_inline_price_leaves_existing_valuation_untouched` | **P4a** `inline_price_requested = request.item is not None` | `create_task.py:316-322` | **C8** + 2 phase-8b tests ✅ |
| C8 | " | **P4b** add `or request.item.currency is not None` | `create_task.py:316-322` | ⚠ **not C8** — phase-8b `test_c5_row_3_…` only (N3) |
| C9 | `test_retired_inline_refusal_identity_is_absent_from_live_sources` | **P6** plant the identity in `app/scripts/` and `docs/handoff/from_frontend/` | test roots | ❌ **nothing bites** — **S1** |
| C10 | `test_operational_handoff_documents_inline_repricing_contract` | **P5** replace the no-op sentence in §9.1 with a paraphrase | operational handoff `:9.1` | **C10 only** ✅ |

**Ruling on the C10 wording change** (prompt item 4): the implementer's edit of the
validation overview from "the inline-pricing **refusal** … [has] integration coverage" to
"inline-pricing **versioning**" was **required by C10, not scope creep.** C10 forbids the
document asserting the retired refusal *anywhere*, and that sentence asserted both that a
refusal exists and that a test covers it — after this phase, neither is true. The
replacement claim is also true (C1–C5 are that coverage). It stayed inside HC-1 file 4.

## Mutation-probe declaration

Six probes. Every one applied to the committed post-Ruff file, run, and reverted.

| Probe | File touched | Revert | Verified |
|---|---|---|---|
| P1 (C3) | `app/beyo_manager/services/commands/tasks/create_task.py` | `git checkout --` | sha256 `10c5f350…` |
| P2 (C5) | same | `git checkout --` | sha256 `10c5f350…` |
| P3 (C1) | same | `git checkout --` | sha256 `10c5f350…` |
| P4a (C8) | same | `git checkout --` | sha256 `10c5f350…` |
| P4b (C8) | same | `git checkout --` | sha256 `10c5f350…` |
| P5 (C10) | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` | `git checkout --` | `git status` clean |
| P6 (C9) | **created** `app/scripts/_reviewer_probe_c9.py`, `docs/handoff/from_frontend/_reviewer_probe_c9.md` | `rm` | `git status` clean, both absent |

Final state verified: `git status --short` empty; `create_task.py` sha256
`10c5f350bf6d8e624a0bf9f2612510785c77435c1c3f8f69b2acee33f1772986` — identical to the
implementer's declared final hash; repo-wide grep for the identity returns zero hits under
`app/` and `docs/handoff/`.

**Database/state side effects:** none beyond what the suite itself does. All probe runs were
scoped to `test_phase8b_inline_task_prices.py` + `test_item_economics_handoff_accuracy.py`,
whose fixtures own their teardown (rule 11½) and seed a fresh uuid-tokened workspace per
test. Two full suite runs were executed; per the master plan §6 caveat these accrue
`task_steps` rows from tests outside this pipeline, so row counts are not a clean baseline
for the next session — failure **IDs** are.

**Architecture graph:** read-only (`archgraph_status`, `archgraph_get_node`). Zero
mutations, zero records written. Revision unchanged at `0f36b07a…`.

## Write perimeter

Exactly one file, as the prompt directed:
`docs/architecture/under_construction/implementation/inline_valuation_versioning/handoffs/reviewer/2026-08-19_phase1_review_r1_handoff.md`

The tracker row and the plan-file Review log entry are **deliberately not written** — they
fall outside the declared perimeter. Exact text for the coordinator to apply is below so
nothing is lost.

### Text for the coordinator — master plan §3 tracker row

> | 1 | M1 compare/inherit/version in `create_task`, identity retired, tests | **CHANGES_REQUESTED** | 2026-08-19 | Claude (reviewer) | Review r1: mechanism correct, one should-fix. C1–C8 and C10 all bite under mutation (7 probes across 6 sites, all reverted, `create_task.py` back to `10c5f350…`); suite 2320/26/1 twice with byte-identical ID sets; HC-2 and HC-4 verified structurally; graph post-state confirmed accurate. **S1: C9's standing guard scans `app/beyo_manager` + `app/tests` + `docs/handoff/to_frontend`, not the `app/` and `docs/handoff/` that C9 names — the identity planted in `app/scripts/` and `docs/handoff/from_frontend/` left the docs-accuracy suite fully green.** Fix is two lines in HC-1 file 2. Notes N1–N5. Handoff: `handoffs/reviewer/2026-08-19_phase1_review_r1_handoff.md`. |

### Text for the coordinator — plan_1.md Review log

> - **review r1 (2026-08-19, Claude) — CHANGES_REQUIRED.** Mechanism verified correct and
>   complete against M1: inheritance keys on `is not None` (a `0` price is kept, not treated
>   as omitted), a `NULL` current field inherits, `(None, None)` is unreachable so
>   `ck_item_valuations_amount_present` cannot be hit, and the currency comparison is
>   enum-to-enum on both sides (`SAEnum(ItemCurrencyEnum)` column vs `ItemCurrencyEnum`
>   request field) so the plain-`Enum`-vs-`str` trap does not arise. HC-2 confirmed
>   structurally — one `ItemValuation` construction and one supersede site in the whole
>   package. HC-4 confirmed — trigger byte-identical. No-op proven structurally (writer and
>   audit both inside the guard) and behaviourally. Suite 2320/26/1 on two independent runs,
>   26 IDs byte-identical to baseline and to each other; arithmetic (−2/+8) reconciles
>   against the diff; Ruff clean. Precedence-disagreement audit passes: C1 seeds two distinct
>   users so a wrong creator cannot pass, and C4 bites independently on both the inheritance
>   and the equality mutation. Deleted-assertion mapping honest. C10's §9.1 rewrite carries
>   all six required facts; the "inline-pricing refusal" → "versioning" edit was **required by
>   C10**, not scope creep. Graph post-state independently confirmed accurate (183/275,
>   `0f36b07a…`, anchors 316-367 and 236-248 checked line-by-line).
>   **S1 (should-fix):** `test_retired_inline_refusal_identity_is_absent_from_live_sources`
>   scans `app/beyo_manager`, `app/tests`, `docs/handoff/to_frontend` and only `*.py`/`*.md`,
>   while C9 names `app/` and `docs/handoff/`; the identity planted in `app/scripts/` and
>   `docs/handoff/from_frontend/` left all 51 docs-accuracy tests green. C9's *state* holds
>   (verified repo-wide twice) but its durability is unguarded, and this is the last phase, so
>   there is nowhere to carry it. Widen the roots; re-running the plant must turn it red.
>   **Notes:** N1 undeclared rename of phase-8b's `test_c1_inline_birth_…` → `test_c7_…` and
>   `C1-row-*` → `C7-row-*`, contradicting "DECISIONS: None" and orphaning two archived
>   citations (`plan_8b` implement handoff `:49`, review handoff `:187`) — record the mapping,
>   do not revert. N2 two criterion vocabularies now share the test file. N3 C8 bites on a
>   fully-dropped trigger but not on a currency-only broadening (phase-8b `test_c5_row_3_…`
>   catches that one). N4 the r1 prompt's `aa95d5e` evidence base spans two pipelines; the
>   phase's range is `7262cea..6f82579`. N5 pre-existing graph anchor `72-580` vs a function
>   running to `594` — owner card 1.

## Lessons for the plans

1. **A criterion that names a search root binds the test to that root.** C9 was written as
   "absent from `app/` and from `docs/handoff/`" and the test implemented a subset. This is
   the *same failure mode* that produced the r1 blocker and earned the master plan's
   **verification-scope rule** — a claim that something appears nowhere is only as good as
   the directory the search ran in. That rule was applied to the implementer's *manual*
   verification but never propagated to the *automated guard* the criterion demands.
   Suggested amendment to the verification-scope rule: "…and when the claim is pinned by a
   test, the test's roots are part of the claim — state them in the criterion and probe the
   guard by planting the string in each named root."
2. **Renaming a pre-existing test identifier is a decision and must be declared.** N1 was
   reasonable and undeclared. Suggested addition to the implementer prompt's DECISIONS
   framing: renames of identifiers cited by closed-phase artifacts are decisions, because
   archives cannot be rewritten to follow them.
3. **Prompt compilation: name the checkpoint's parent, not a remembered hash** (N4). One
   line of `git log --oneline -1 <sha>` at compile time would have caught it.
4. **What worked and should be kept.** C4 earned its place — it is the only row that bites
   on both the inheritance and the equality mutation, and without it a broken-inheritance fix
   could have been "verified" by C2 alone. C1's two-user fixture is the right shape for any
   P-CREDIT criterion and should be the template. Naming the mutation *and its site*
   (definition vs call) in the criterion text made four of the five probes mechanical to
   construct.
