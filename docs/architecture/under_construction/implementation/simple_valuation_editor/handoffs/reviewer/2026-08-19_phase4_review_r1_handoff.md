---
plan: 4
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-19
actor: Opus 5 (review r1)
---

# Phase 4 review r1 — the price-scenario handoff and the production-time reply

**Verdict: CHANGES_REQUESTED.** 3 blocking, 4 should-fix, 3 notes.

Both documents are substantially right, and the two things this round was told to attack
hardest — §4's BigInt transcription and §4's worked example — are **correct**, re-executed
independently against the shipped module (612 cases, 0 mismatches; `855 000 → 188 100 →
14 469 → 8 681 s`). C1, C2, C4, C5 and C6 all hold. The failures are concentrated in **C3**,
and they share one root: **the price-scenario handoff describes the payload's nullability as
a function of `status`, while the shipped query gates it on four independent conditions** —
`item_binding`, the *live* selection, currency agreement, and whether the model collapses.
§6.1 already tells the reader this for `can_commit` ("computed from the **live**
configuration, not from the displayed status"); §5.2 and §2 do not carry the same rule for
the blocks they govern, and four nullable fields are documented as always present.

All three blocking findings were **reproduced against the shipped code**, not reasoned about.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing here needs the owner. Every finding is a text correction the coordinator owns, and
none reopens a ratified decision — D1, D4, D5, D8, D9, D10 and D16 all stand exactly as
written. B3 asks the handoff to state a contract the intention already carries (§9.5); it
does not propose a new one.

---

## Findings

### BLOCKING

#### B1 — §5.2's block rule is stated over `status` alone; the code gates on four conditions, and two of them are absent from the document

**Where.** `HANDOFF_TO_FRONTEND_price_scenario_20260819.md` §5.2, first paragraph:

> `model` is present for five statuses: `ok`, `infeasible`, `item_unvalued`,
> `item_missing_expected_price`, `not_evaluated`. It is `null` for the other seven — the five
> configuration failures, `item_missing_purchase_cost`, and `currency_mismatch`.

**What the code does** (`get_task_price_scenario.py:196-207`, `:238-246`). The blocks are
published only when **all** of:

1. `budget_status.item_binding == "bound"` — **not in the document at all**;
2. `budget_status.status in _MODEL_STATUSES` — the five the document lists;
3. `selection_ready` — the **live** selection resolved (`:168-174`) — **not in the document**;
4. `currency_agrees` (`:175-183`) — **not in the document**;
5. `collapse_terms(...) is not None` (`:207`) — in the document, but scoped to B6/B7 only.

**Reproduced, not inferred.** Two runs against the shipped service through the phase-2
integration fixture (`_run_scenario`), both reverted, nothing written:

| Scenario | `status` | `model` / `anchors` / `domain` | `config_fingerprint` | Document says |
|---|---|---|---|---|
| committed task, live cost model version expired | `"ok"` | **all `null`** | `null` | present |
| `item_binding: "mismatched"` | `"not_evaluated"` | **all `null`** | `null` | present |

The first case is not hypothetical — it is the exact case §6.1 already describes one page
later ("a task committed while the configuration was healthy can still read `ok` after its
cost model version expires"), and it is exercised by the shipped suite as the
`committed_live_model_expired` row of `test_c2_can_commit_uses_each_live_admission_condition`
(`test_price_scenario_query.py:459`). The second is guaranteed by construction: `mismatched`
requires a committed evaluation (`get_task_budget_status.py:111`), so the status is *always*
`ok` or `infeasible` — two of the five the document promises. `test_c9_non_bound_binding_governs_the_full_payload`
(`:567-590`) asserts every block `null` on both non-`bound` bindings.

**Violated authority.** Intention §9.2A — *"`item_binding` wins over the status table —
always, not sometimes"* — a section that exists *because* §9.2 and §9A.1's table collide on
every occurrence of a non-`bound` binding. Also §9A.1's "the `model` block is always built
from the **live** selection … never from the committed evaluation's snapshot."

**Proposed replacement** for §5.2's first paragraph (verbatim):

> `model`, `anchors`, `domain` and `config_fingerprint` are published together or not at
> all. **Four things must hold at once**; `status` is only one of them.
>
> 1. **`item_binding` is `"bound"`.** Under `detached` or `mismatched` all four are `null`
>    **whatever the status says** — and `mismatched` always reports `ok` or `infeasible`,
>    so status alone will tell you the blocks are there when they are not. Check the
>    binding first. (§7.4.)
> 2. **`status` is one of** `ok`, `infeasible`, `item_unvalued`,
>    `item_missing_expected_price`, `not_evaluated`. It is `null` for the other seven — the
>    five configuration failures, `item_missing_purchase_cost`, and `currency_mismatch`.
> 3. **The *live* configuration still resolves and its currency still agrees.** `ok` and
>    `infeasible` come from the *committed* snapshot and do not consult the live
>    configuration, so a task committed while the configuration was healthy reports `ok`
>    after its cost model version expires — with every block `null`. This is the same live
>    /displayed split §6.1 describes for `can_commit`, and the two always move together.
> 4. **The model collapses** — a cost model with a purchase-cost term and no purchase cost
>    available yields `null` blocks under any status, the same as
>    `item_missing_purchase_cost`.
>
> **Treat `model === null` as the switch, never `status`.** Every rule above is a way for
> the blocks to be missing under a status that looks healthy.

The paragraph beginning "**This is the important one:** the screen works for an item nobody
has priced yet" stays where it is and is correct; the "One qualification" paragraph is
absorbed into item 4 above and should be deleted to avoid stating the rule twice.

Also add a **§7.4** (or extend §2) stating the non-`bound` payload from intention §9.2A —
`item` populated on `mismatched` and `null` on `detached`; `saved`, `currency`, `model`,
`anchors`, `domain`, `config_fingerprint` all `null` on both; `typical` populated on both;
`can_commit` `false` on `detached` and **as resolved on `mismatched`** (verified: `true` in
the reproduction above, with no model on screen).

---

#### B2 — four nullable fields are documented as always present; the document claims it was written from the serializer

**Where.** §2's payload block. C3 makes a wrongly-stated nullability a finding, and §2's own
opening line is *"Written from the shipped serializer, not from a design document."* Walked
key by key against `serialize_task_price_scenario` (`serializers.py:288-365`) and the query's
`typical` (`:138-146`) / `anchors` (`:222-231`) blocks, **all 46 keys ship and all 46 are
documented — none missing, none extra.** Four nullabilities are wrong:

| Key | Ships as | §2 shows | Reachable when | Authority |
|---|---|---|---|---|
| `currency` | `valuation.currency if valuation is not None else None` (`:259`) | `"swedish_krona"`, no annotation | **`item_unvalued`** — the flagship case of §5.2 — and every non-`bound` binding | intention §6B ("`currency` … is `null` exactly when `saved` is `null`"), §8A.1 (flagged ⚠ *undefined for an unvalued item*) |
| `item.article_number` | `String(128) NULL` (`item.py:22`) | `"0000608"`, no annotation | any item without an article number | intention §8A ("travels as `null`") |
| `item.label` | `items.item_category_snapshot`, `String(255) NULL` (`item.py:45`) | `"Dining chairs"`, no annotation | any item with no category snapshot — which is also `item_missing_major_category` | intention §8A |
| `saved.expected_sale_price_minor` | `Integer NULL` (`item_valuation.py:20`) | `855000`, no annotation | **`item_missing_expected_price`** — the state §6.2 tells the frontend to *create on purpose* | intention §6B (row 2 of its table) |

**Reproduced:** `status: "item_unvalued"` returns `currency: null` with `model` fully
populated — i.e. the screen renders a live slider and a price with no currency to format it
in. Three of the four were already recorded in the intention's own key-by-key walk (§8A),
which is where a serializer-derived document should have picked them up.

**Proposed replacement** — annotate §2 in place:

```jsonc
  "currency": "swedish_krona",       // null whenever "saved" is null — including the
                                     // unpriced item of §5.2. Do not format money with it
                                     // unchecked.
  "item": {                          // null when item_binding is "detached"
    "client_id": "itm_…",
    "article_number": "0000608",     // nullable
    "label": "Dining chairs",        // the item's category snapshot — nullable
    "quantity": 6
  },
  "saved": {                         // null when there is no valuation row, and on any
                                     // non-"bound" item_binding
    "valuation_id": "ival_…",
    "expected_sale_price_minor": 855000,   // null under item_missing_expected_price —
                                           // the state §6.2's flow deliberately creates
```

and add one line under the block: **"Every `…_minor` field, `currency` and both `item` string
fields are nullable. The screen's first render for a brand-new item has `saved: null`,
`currency: null` and a fully populated `model`."**

---

#### B3 — `config_fingerprint` is the document's only staleness signal, and it is provably blind to the typical, the break-even, the suggested price and the whole band

**Where.** §6.3, final paragraph:

> `config_fingerprint` is `cost_model_version_id:basis_version_id:v{calculation_version}`.
> Compare it across polls to detect a configuration change; it is `null` exactly when `model`
> is.

Every clause is true. Together with §Frontend-action-required 1 ("Fetch once per screen open")
they are also the *whole* of what the document says about staleness, and a reader will take an
unchanged fingerprint to mean unchanged numbers. It does not.

**What the fingerprint does not cover** — intention §9A.3, stated explicitly and dropped here:

> It does **not** cover `quantity`, `item_category_snapshot`, the task's step set, or the
> typical (which moves whenever any task in the workspace completes a step); §9.5 already
> assigns those to refetch-on-event.

Verified at source. `typical.total_seconds` is a **workspace-wide** median of completed
section totals over a **rolling 90-day window whose cutoff is `datetime.now(timezone.utc)`**
(`get_working_section_typical_times.py:23-46`). So it moves on any other task's step
completion **and on the passage of time alone**, with no row written to this task at all.
`break_even_price_minor` is a function of it (`get_task_price_scenario.py:216-219`), and
`suggested_price_minor` and every value in `domain` are functions of the break-even
(`:220-231`). All four move under an **unchanged** `config_fingerprint`.

**And the save-time reconciliation cannot catch it.** §6.3 tells the frontend to assert the
commit response's `production_budget_minor` and `allowed_worker_minutes`. Both are functions
of the price and the model only (§4's three operations) — **neither depends on the typical.**
So the one divergence the document's staleness story does not detect is also the one its
reconciliation is structurally unable to see.

**Consequence.** The chip's flip point, the suggestion marker and both slider ends can drift
under the manager's thumb, and the document as written gives the frontend no reason to
refetch and no way to notice.

**Proposed replacement** for §6.3's final paragraph (verbatim):

> `config_fingerprint` is `cost_model_version_id:basis_version_id:v{calculation_version}`; it
> is `null` exactly when `model` is. It covers **the configuration and nothing else** — the
> rate and the whole term set, because cost model terms are immutable for the life of their
> version.
>
> **It does not cover the typical, and therefore does not cover the anchors or the band.**
> `typical.total_seconds` is a workspace-wide median over a rolling 90-day window, so it moves
> when *any* task in the workspace completes a step — and, because the window slides, with
> time alone. `break_even_price_minor`, `suggested_price_minor` and all three `domain` values
> are derived from it, so **all five can change between two polls with an identical
> fingerprint**, and the commit-response reconciliation above cannot see it: the budget and
> the allowance are functions of the price and the model, never of the typical.
>
> It also does not cover `item.quantity` or `item.label`.
>
> **So: refetch the scenario on item-changed and step-transition events for this task**, not
> only on a fingerprint mismatch. The screen is short-lived, so in practice this is one
> refetch on the events you already receive — but a screen left open across a step transition
> is pricing against a break-even that has moved.

---

### SHOULD-FIX

#### S1 — the production-time reply's "no clock read anywhere in `services/queries/item_economics/`" is false, and §6 presents it as verified

**Where.** `HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md` §1, *Why not
Option A*:

> **There is no clock read anywhere in `services/queries/item_economics/`** — no
> `datetime.now`, no `func.now`. The entire read surface is a pure function of stored state,
> which is what makes two calls a minute apart identical, makes the budget-status and
> production-time screens agree by construction, and makes responses reproducible.

and §6: *"a repository-wide search confirming no clock read in
`services/queries/item_economics/`."* Plan 4 §3.2 records the same claim as delivered
("enforced structurally by there being **no clock in the layer**").

**There are two direct clock reads in that exact directory:**

- `get_economics_configuration_status.py:38` — `today = today_utc()`
- `get_task_budget_allocations.py:188` — `today_utc()` — and this is **E-A**, one of the four
  surfaces the live-clock pipeline targets.

`today_utc()` is `datetime.now(timezone.utc).date()` (`_common.py:47-48`). The original search
evidently matched `datetime.now` / `func.now` literally and missed the wrapper.

`get_task_price_scenario.py` reaches the clock twice more, transitively: `_load_preview_inputs`
→ `today_utc()` (`_common.py:203`) for version applicability, and `typical_times_statement` →
`datetime.now(timezone.utc)` (`:23`) for the 90-day window. So "two calls a minute apart
identical" and "responses reproducible" are false for at least three endpoints in the family,
including the one this pipeline just shipped (this is the mechanism behind B3).

**The verdict is unaffected.** `share_state` really is settled-only, and §1's citations
(`budget_division.py:364`, `:134`, `:266`, `:327-335`) are all accurate — I checked each at
the line. What fails is the *reason offered*, and it is offered as structural.

**Proposed replacement** for the paragraph (verbatim):

> Making all three live cascades further than it looks. `worked_seconds` on this endpoint is
> `TaskStep.total_working_seconds` and nothing else (`budget_division.py:134`, `:266`) — a
> stored column, never a clock difference — and `share_state` compares it against an allowance
> derived from the same settled column, which is why two calls a minute apart return the same
> verdict. (The read family is not clock-free in general: version applicability and the
> typical's 90-day window both read the clock. What is clock-free is the worked-seconds basis
> itself, which is the invariant that matters here.) Option A would put the first *worked-time*
> clock into this layer to serve a verdict whose provisionality you can already detect.

§6 should say what was actually verified: **"`worked_seconds` is `total_working_seconds` and
nothing else at `budget_division.py:134` and `:266`"** — a claim that holds — rather than a
directory-wide absence that does not.

---

#### S2 — §4's error-bound illustration reintroduces the exact `n` conflation intention §3.2A corrected

**Where.** §4, *It is an approximation, and here is the bound*:

> The difference is bounded by `(n + 1) / 2` minor units, where `n` is the number of
> percentage terms — for a two-term model, **at most 1 öre**, which at the rate above is about
> 0.07 seconds.

With `n` defined as *the number of percentage terms* — which is correct, and is §3.2A's own
definition — a two-percentage-term model has `n = 2` and a bound of **1.5** öre, not 1. And 1
öre at the published rate (1 300 minor/minute) is **0.046 s**; the quoted 0.07 s is the
1.5-öre figure. A reader who applies the formula the sentence just gave them gets a different
number from the sentence's own illustration.

Intention §3.2A calls this out by name: *"§3.2 computes '≤ 1 minor unit … about 0.07 seconds'.
The two halves use different `n` … Both are correct for their own `n`."* The correction was
made in the intention and lost on the way into the handoff.

**Proposed replacement** (verbatim):

> The difference is bounded by `(n + 1) / 2` minor units, where `n` is the number of
> **percentage** terms in the model (not the term count). One percentage term ⇒ ≤ 1 öre ⇒
> about **0.046 s** at the rate above; two ⇒ ≤ 1.5 öre ⇒ about **0.07 s**. Either way the
> largest error is under a tenth of a second against a display quantised to whole minutes. We
> assert this bound by test against the real persisted path, over seven model shapes.

("seven model shapes" is correct — `test_c7_collapsed_budget_stays_within_the_integer_error_bound`
carries exactly seven parametrised rows.)

---

#### S3 — §8.1's opening sentence overstates what the production-time screen deducts, and its own next sentence contradicts it

**Where.** §8.1:

> This screen's `AT PRICE` ignores time already spent, including time lost to cancelled or
> failed steps. The production-time screen's distributable total does **not** — it deducts
> that time.

Read plainly, "that time" is "time already spent, including time lost to cancelled or failed
steps", so the sentence claims the production-time screen deducts *all* time already spent. It
does not. `distributable_seconds = max(0, budget_seconds − charged_seconds)`
(`budget_division.py:314-315`), and `charged_seconds` sums `total_working_seconds` over
**excluded** steps only — `SKIPPED`, `CANCELLED`, `FAILED` (`:308`, `EXCLUDED_STEP_STATES`
`:19-25`). Time worked on completed or in-progress steps is *allocated*, never removed.

The next sentence gets it right ("differ by exactly that amount", i.e. the excluded-step
time), which makes this the failure mode the section exists to prevent, inverted: a manager
told the screens differ by all elapsed work will look at a task with four hours of completed
work and no excluded steps, find no gap, and file *this* document as wrong.

**Violated authority.** Intention §5.4 and master plan §8 obligation 2, both of which say
"by exactly `charged_seconds`" and define it as excluded steps' consumed seconds.

**Proposed replacement** for the first two sentences (verbatim):

> This screen's `AT PRICE` is the allowance for the **whole job**, before any of it is worked.
> The production-time screen shows what is left to distribute, and it subtracts one thing this
> screen does not: `charged_seconds` — the time already logged on steps that were **skipped,
> cancelled or failed**. Time worked on ordinary steps is subtracted by neither; it is
> allocated, not removed.

---

#### S4 — §4's "you may treat that third rounding as inert" invites dropping a rounding that is not inert

**Where.** §4:

> Two of the three operations can actually land on a tie (the price × residual multiply, and
> the rate division). The seconds conversion is provably tie-free over integers — a fact we
> tested, so you may treat that third rounding as inert.

Tie-free is not inert. `round_half_even(3c, 5)` still rounds: the shipped worked example is
`round_half_even(43 407, 5) = 8 681`, not `8 681.4`. A reader who takes "inert" to mean "you
can skip it" and writes `(centimin * 3n) / 5n` gets the same answer for positive operands and
a different one for negative — and this section's own preceding paragraph says negatives are
reachable on this screen. Concretely: `allowed_centimin = −1n` gives **−1 s** under the
reference algorithm and **0 s** under BigInt division. That is the one operation the document
told them they could stop thinking about.

**Proposed replacement** (verbatim):

> Two of the three operations can actually land on a tie (the price × residual multiply, and
> the rate division). The seconds conversion is provably tie-free over integers — `3·cm mod 5`
> is never `2.5` — so **the half-even tie rule never fires there**. It still rounds, and you
> still call `roundHalfEven` for it: BigInt `/` truncates toward zero, which disagrees on
> negative operands (`allowed_centimin = −1n` → `−1n` half-even, `0n` truncated). Use the
> function for all three.

---

### NOTES

**N1 — §5.4's divisibility guarantee is stated over `quantity`, not `max(1, quantity)`.**
"every value is a multiple of `step_minor`, which is itself a multiple of `quantity`" —
`slider_domain` uses `divisor = max(1, quantity)` (`price_scenario.py:193-198`), so at
`quantity = 0` (the legacy row §8.2 warns about) `step_minor` is a multiple of 1 and
`min_minor / quantity` divides by zero. §8.2 gives the right divisor three sections later and
§3's table points at §5.4, so nothing breaks in practice; the sentence should read "a multiple
of `max(1, quantity)` — see §8.2" so the guarantee is true where it is stated. Intention §7A.1
states it over `Q = max(1, quantity)`.

**N2 — §5.3's `is_fundable: false` enumeration is presented as exhaustive and is not.**
"a cost model whose terms consume the whole price, or no typical evidence at all" covers
`residual_percent_milli <= 0` and `typical_total_seconds == 0` (`price_scenario.py:145-147`).
`break_even_price_minor` also returns `null` when the search exceeds `SEARCH_CAP_MINOR = 2**40`
(`:126-129`), reachable only under an extreme-but-legal configuration (a near-zero residual
with a very high rate). Worth one clause — "or when no representable price funds it" — since
the frontend's handling is the same either way.

**N3 — §6.1's purchase-cost condition is a property of stored state, not of the commit
endpoint.** The commit endpoint accepts `purchase_cost_minor` in the body and substitutes it
into `effective` (`commit_item_cost_evaluation.py:221-225`, `:396-412`), so a commit carrying a
purchase cost can succeed where `can_commit` is `false`. `can_commit` is deliberately
price-and-purchase-independent (intention §9A.2: "a GET cannot know which price the user will
choose"), and this screen's Save sends only the price, so the field is conservative and never
wrongly `true` — the direction that matters. Recorded so that a later "Save also sets the
purchase cost" optimisation finds the asymmetry instead of concluding `can_commit` is broken.

---

## What I verified correct

### C3 — the key-by-key walk (P3), in full

Every key of `serialize_task_price_scenario` (`serializers.py:288-365`) against §2's JSON.
**46 keys ship; 46 are documented. Zero undocumented keys, zero documented keys that do not
ship.**

| Block | Keys shipped | In §2 | Nullability |
|---|---|---|---|
| top level | `task_id`, `status`, `item_binding`, `can_commit`, `currency`, `calculation_version`, `config_fingerprint`, `item`, `saved`, `model`, `typical`, `anchors`, `domain` (13) | all 13 ✓ | `currency` **wrong (B2)**; `item`/`saved`/`model`/`anchors`/`domain`/`config_fingerprint` **incomplete (B1)** |
| `item` | `client_id`, `article_number`, `label`, `quantity` (4) | all 4 ✓ | `article_number`, `label` **wrong (B2)** |
| `saved` | `valuation_id`, `expected_sale_price_minor`, `purchase_cost_minor`, `created_at`, `created_by` (5) | all 5 ✓ | `expected_sale_price_minor` **wrong (B2)**; `purchase_cost_minor` ✓; `created_by` ✓ |
| `saved.created_by` | `client_id`, `username`, `profile_picture` (3) | all 3 ✓ | ✓ ("null only if the user row cannot be loaded" — matches §6B case 3) |
| `model` | `cost_model_version_id`, `basis_version_id`, `residual_percent_milli`, `constant_deduction_minor`, `cost_per_worker_minute_ten_thousandths`, `is_purely_proportional` (6) | all 6 ✓ | ✓ (whole block, per B1) |
| `typical` (`get_task_price_scenario.py:138-146`) | `total_seconds`, `is_estimated`, `sections_without_sample`, `sections_total`, `method`, `window_days`, `min_sample_size` (7) | all 7 ✓ | ✓ — **always present**, correctly stated, and correct on non-`bound` bindings too |
| `anchors` (`:222-231`) | `is_fundable`, `break_even_price_minor`, `suggested_price_minor`, `infeasible_at_or_below_minor` (4) | all 4 ✓ | ✓ — "present whenever `model` is; members may be null" is exactly right (same `if collapsed is not None` block); `infeasible_at_or_below_minor` correctly stated as never null |
| `domain` | `rule`, `min_minor`, `max_minor`, `step_minor` (4) | all 4 ✓ | ✓ |

**The document's claim that it was written from the serializer is borne out for key *names*
and *scales* — the integer-scaled fields, the `_milli` / `_ten_thousandths` suffixes, the
`is_purely_proportional` derivation, `label` = `item_category_snapshot`. It is not borne out
for nullability**, where three of the four misses were already recorded in intention §8A.

### C4 — the literals, re-checked at source

| Claimed | Verified | Where |
|---|---|---|
| `break_even_price_minor 1 211 335` | ✓ | `test_c18_suggested_price_rounds_to_the_domain_step:597` |
| `suggested_price_minor 1 215 000` | ✓ | same test, `:598` |
| `max_minor 1 650 000`, `min_minor 420 000`, `step_minor 15 000` | ✓ recomputed by hand through `slider_domain(1 211 335, 6, 29)`: `step_per_piece = two_significant_digits(1 211 335, 480) = 2 500`; `floor_to_step(423 967.25) = 420 000`; `ceil_to_step(1 635 302.25) = 1 650 000` | `price_scenario.py:183-212`, intention §7A.2 |
| `infeasible_at_or_below_minor 29` | ✓ | `test_c6…:518` |
| `ival_` prefix | ✓ | `ItemValuation.CLIENT_ID_PREFIX` |
| `allowance_seconds(855 000) = 8 681` | ✓ recomputed: `188 100 → 14 469 → 8 681` | below |

The four values §8A retired (`ivl_`, `1211364`, `1635000`, `infeasible: 0`) appear nowhere;
`ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` appears once, in the sentence retiring it.

### §4's BigInt transcription — re-executed independently

I did not take the coordinator's run on trust. The `roundHalfEven` **verbatim as printed in
the handoff** was run in Node and compared against `round_half_even` extracted verbatim from
the shipped `price_scenario.py`, over the same case space: divisors `2, 3, 5, 100 000,
13 000 000` × numerators `−60 … +60` (605), plus the exact operands of all three published
operations at `P = 855 000`, plus §9's four suggested assertions. **612 cases, 0 mismatches.**
§9's four assertions return `−2, −2, 2, 2` on the shipped implementation, exactly as printed.

The worked example recomputed on the shipped module: `budget = 188 100`, `centimin = 14 469`,
`seconds = 8 681` = 144.683 min → **`2h 25m`** at nearest-minute, `2h 24m` truncated. §4's
display-rounding sentence and §9's validation step 2 are both correct.

The tie-reachability claim is sound: `2r = 5` is unreachable because `2r` is even, so the
seconds conversion cannot tie (intention §3.1A's third table row). S4 is about the wording
built on top of that fact, not the fact.

### C1 — the six obligations (P6)

| # | Master plan §8 | Where | Traceable |
|---|---|---|---|
| 1 | M1 arithmetic for a second language | §4 (three operations, BigInt reference, `Number` forbidden, `Math.round` named, display rounding, the bound) | §3.1/§3.1A, HC-5 ✓ |
| 2 | Name the accepted divergence | §8.1 | D5, §5.4 ✓ — present, wording is S3 |
| 3 | The Save flow | §6 / §6.1 / §6.3 (one call, `can_commit: false` **disables**, reconciliation "mandatory, not advisory") | D4, §11 ✓ |
| 4 | Amend §8.4's display prohibition only | §7.2 — lifts the prohibition, restates the contract as "not negotiable" | D1 ✓ |
| 5 | Amend §6's status→treatment table | §7.1, scoped "for this endpoint only" with "Other endpoints are unchanged" | D8, §9A.1 ✓ |
| 6 | Save cannot create the first valuation row | §6.2, opening with **"This is the one thing in this document whose omission is silent"** | D9, §9A.2 ✓ |

All six present, all six traceable, and obligation 6 carries the silent-omission framing the
master plan demanded of it. **C1 holds.** §7.1's paraphrase of the old table ("null everywhere
but `ok` and `infeasible`") slightly under-quotes the original, which also excepts
`not_evaluated` inside the valuation endpoint's `preview` key — harmless, since §7.1's
amendment adds `not_evaluated` anyway.

### P2 — `can_commit`'s seven conditions, diffed against the code

§6.1's prose against `get_task_price_scenario.py:184-191` and the admission path in
`commit_item_cost_evaluation.py`:

| §6.1 says | Code | |
|---|---|---|
| the task exists and is not deleted | `_load_task_and_item` filters `is_deleted`, raises `404` (`get_task_budget_status.py:52-60`); commit at `:113-114` | ✓ |
| state ∈ `PENDING, ASSIGNED, WORKING, STALLED, READY` | `_ADMITTED_STATES` — those five exactly (`commit_item_cost_evaluation.py:60-68`) | ✓ **enumerated correctly, all five, no extras** |
| an active PRIMARY item exists and its row is not deleted | `TaskItem.role == PRIMARY, removed_at IS NULL` then `Item.is_deleted is False` (`:118-136`); query side via `item is not None` | ✓ |
| a current valuation row exists | `valuation is not None` (`:187`) — and this is the §9A.2 asymmetry: `effective` is `None` whenever no row exists, **regardless of the price in the body** (`commit_…:212-213`) | ✓ **and correctly reflected in §6.2** |
| the configuration resolves | `selection_ready` (`:168-174`) | ✓ |
| the currency agrees | `currency_agrees`, three-way (`:175-183`) | ✓ |
| a purchase cost is present if the model has a purchase term | `not _has_purchase_term(terms) or valuation.purchase_cost_minor is not None` (`:190`) | ✓ — see N3 for the one direction it is stated more strongly than the endpoint enforces |

**Seven conditions, seven in the code, none missing, none inverted.** §6.1's second paragraph
("computed from the **live** configuration, not from the displayed status") is correct and is
the sharpest sentence in the document — B1 exists because §5.2 does not say the same thing
about the blocks. The one gap: `can_commit` is **`true` under `item_binding: "mismatched"`**
with no model on screen (`:238-246` forces `false` only for `detached`, matching intention
§9.2A's "as resolved"); §6.1 does not mention binding — folded into B1's proposed §7.4.

### C5 — the two shelf lives (P5)

**The expiry notice is correctly placed and correctly absent.**

- The production-time reply's §4 is strong enough. It leads with a warning heading, states the
  reversal concretely (all three fields, on that endpoint), gives the instruction as behaviour
  — *"build it behind one flag, in one place, not baked into the component. Its removal should
  be a single change"* — and is honest that it has **no date**: *"Its intention is resolved; it
  has not passed its mechanism-inventory gate, so it has no date."* Verified against
  `live_clock_for_working_time_economics/planning/intention.md`: status `RESOLVED (round 2)`,
  0 owner cards, `NOT plan-ready until the mechanism-inventory gate passes` (`:4-5`); the
  reversal on `production-time` is §4.1's E-P row (`:280`); the concurrency-averaged basis is
  §3.1 (`:194-199`); the "25 minutes into a 3-minute allowance" figure is that intention's own
  (`:448`). **§4's claim about that pipeline is accurate.** It also correctly quarantines what
  does *not* expire (§2's correction, §3's ratio caveats).
- The price-scenario handoff correctly carries **no** such caveat. Verified structurally, not
  by absence: the live-clock intention's §2.6 records the price-scenario endpoint as an
  in-flight neighbour and states *"its payload deliberately carries no progress block (its D5
  ratified gross-of-progress), so it does not consume the live figure in v1"*, and §4.1's
  surface table lists only E-P, E-B (both faces) and E-A. `get_task_price_scenario` consumes
  `get_task_budget_status` for `status` and `item_binding` only — and that table marks `status`
  as "OK↔INFEASIBLE unchanged (allowance-driven, not worked-driven)". **No published
  price-scenario number can move under the live clock. C5 holds.**

I read the live-clock artifacts only far enough to judge §4's accuracy, as instructed, and
reviewed nothing of that pipeline.

### C2 and C6

- **C2 — verified independently against git, not against the tree.** `git log --name-status
  docs/handoff/to_frontend/` shows plan 4's footprint as `A`, `A` (2f6723b) and one `M`
  (3f60f6a) of a file plan 4 itself created. **No published handoff was edited by this phase.**
  The last in-place edit of `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` is
  `6f82579`, the inline-valuation-versioning checkpoint — the one §7's apology is about.
- **C6** — both files carry the statement and name what they amend. Price-scenario: *"This
  document supersedes nothing and edits nothing … it does so by reference (§7)"*, naming the
  2026-08-15 operational handoff and three of its sections. Production-time reply: metadata
  *"Amends by reference … §*Live time* — that file is not edited (§5)"*, plus §5's adoption of
  the convention. ✓

### Other claims checked at source and found correct

- Route, roles and the `403`: `@router.get("/tasks/{task_client_id}/price-scenario")` with
  `require_roles([ADMIN, MANAGER])` (`routers/api_v1/item_economics.py:385-396`). ✓
- The production-time reply's four citations, each read at the line: `budget_division.py:364`
  (`"over_share" if worked > allowance`), `:134` and `:266` (`worked_seconds` is
  `total_working_seconds` and nothing else), `:327-335` (the median substitution for a null or
  zero typical). ✓
- §5.1's participation rule — "at least one non-deleted step that is not `SKIPPED`,
  `CANCELLED` or `FAILED`" — matches `_step_state_is_excluded` / `EXCLUDED_STEP_STATES`
  (`budget_division.py:19-25`, `:209-210`) and the query's filter (`:96-100`). ✓
- §5.1's `is_estimated` contract, **including the empty-set case** ("or that there are no
  participating sections at all") — `sections_total == 0 or sections_without_sample > 0`
  (`:140`). This is one of P4's named candidates and it is documented correctly. ✓
- §5.3's `infeasible_at_or_below_minor` "never null … often not zero, for the example model
  29" — `infeasible_at_or_below_minor` returns an `int` on every path (`:150-154`). ✓
- §6.3's "`config_fingerprint` … is `null` exactly when `model` is" — same `model_data is not
  None` guard (`:247-252`). ✓ (Its *coverage* is B3.)
- §4's "over seven model shapes" —
  `test_c7_collapsed_budget_stays_within_the_integer_error_bound` carries exactly seven
  parametrised rows. ✓
- §9's "105 tests", "34 mutations", "0 blocking" — match the phase-1 and phase-2 review
  handoffs. ✓
- §5.4's band rationale and the `2 750` divergence — matches D10's ratification verbatim and
  §7A.2's redone worked check; the "Render the ends you are given" instruction is the right
  operational form of it. ✓
- §7.2's quotation of §8.4 ("Do not show '1000 × 5' anywhere near these figures") is verbatim
  from the 2026-08-15 file. ✓
- §7.3 and the apology: the refusal really is retired (inline-valuation-versioning, closed
  2026-08-19), and the in-place edit really did happen at `6f82579`. ✓

### P4's other named candidates — checked, and clean

`is_estimated`'s empty-set case, `infeasible_at_or_below_minor` being non-zero, and
`config_fingerprint`'s null-coupling are each documented correctly (above). **The third
divergence the probe was looking for is the fourth question it named** — whether a published
number can decrease between two polls. It can, and that is B3.

---

## Suite

**No code changed in this phase**, so the suite is context, not evidence. Run anyway on a
clean tree from `backend/app/` with `PYTHONPATH=. pytest -m 'not e2e'`:

**2 425 passed / 26 failed / 1 deselected in 125.09s** — identical to the figure §9 of the
price-scenario handoff publishes to the frontend, and to the phase-2 approval-gate measurement.
The failures land in the same inherited files (`test_items_router.py`,
`test_upholstery_inventories_router.py`, …). Master plan §6's binding rule applies — a count
alone is noise; only an ID added or removed across repeated runs is a finding — and the count
matched on the first run, so no repeat was needed. **§9's published suite claim is accurate.**

The two feature test files were read in full for the probes above and are unmodified.

---

## Mutation-probe declaration

**No file in the repository was modified by this session — no probe was applied and none
needed reverting.** All reproduction was done by *calling* the shipped service through the
existing phase-2 integration fixture from an out-of-tree script, with `monkeypatch` substitutes
restored on the same call stack and no database session ever committed. The two probe scripts
live in the session scratchpad
(`…/scratchpad/rhe.js`, `…/scratchpad/probe_test.py` — the latter unused, superseded by an
inline runner) and are outside the repository.

**Database side effects: none.** The fixture uses an in-memory session double; nothing was
written, so nothing was restored.

**Full write perimeter — one file:**

- `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_phase4_review_r1_handoff.md` (this file)

**I wrote no application file, no handoff to the frontend, and no plan or tracker row.** Every
correction above is a finding with proposed text, not an edit. Plan 4's Review log and the
master plan tracker are the coordinator's.

**Not written by me, seen in the tree:** the working tree was **clean** at the start and end
of this session — plan 3's implementer had not yet landed changes under `app/`, and
`implementation/live_clock_for_working_time_economics/` is committed rather than untracked.
Neither is mine.

---

## Lessons for the plans

1. **A payload contract's nullability needs its own enumerated criterion, separate from its
   key list.** C3 says "every payload key … matches the shipped serializer", and it was met:
   all 46 keys are right. Every failure in this round's C3 was a *nullability*, and the
   criterion's wording let a document pass the check it was given while getting the harder half
   wrong. Future handoff phases: **"every nullable field is annotated as nullable, and every
   annotation names a reachable status or binding that produces the null."** Three of the four
   misses were already written down in intention §8A — the criterion just never asked.

2. **When a document is written from the code, name the intention's key-by-key walk as a
   second source, not as the thing being replaced.** Plan 4 §3.1 makes "written from the
   serializer, not from the intention's §8 example" a virtue — correctly, since §8's example
   carried four wrong values. But §8**A** is not the example; it is the corrected walk, and it
   held three of the four nullabilities and the `n`-conflation correction (S2) that the handoff
   then re-broke. The rule to record: *avoid the example, read the corrections.*

3. **A rule stated in one section and its exception stated in another is one rule for the
   reader and two for the author.** §6.1 states the live-vs-displayed split precisely, for
   `can_commit`. §5.2 governs the same split for the blocks and does not. Both were written in
   the same sitting by the same author. A handoff phase should carry a criterion that **any
   invariant appearing in two sections is stated identically in both, or once with a
   cross-reference** — the two sections here are four pages apart and only one of them is on
   the path a frontend dev reads before writing the null check.

4. **"Executed, not merely written" should extend to prose that asserts an absence.** §4's
   BigInt block was executed and is flawless. §1 of the production-time reply asserts an
   *absence* ("no clock read anywhere in …") and was verified by a grep for two literals, which
   the codebase's own wrapper defeats (S1). Absence claims need the search *term set* recorded
   next to them, or they need restating as the presence claim they are actually standing in
   for.

5. **The projection gate's L2/L3 findings did not reach the handoff.** Intention §9.2A (`L2`,
   binding wins over the status table) and §9A.1's `†` (`L3`, B6/B7 collapse) were both
   projection-round corrections. The `†` made it into the handoff as §5.2's "One qualification";
   §9.2A did not appear at all, and it is the wider of the two. When a closeout handoff is
   planned, its read order should name **the projection handoffs' ledgers**, not only the
   intention sections — a lettered section added by a projection is exactly the kind a
   section-number read list misses.

6. **This phase justified its own gate.** Plan 4 §5 predicted the failure mode ("whether
   anything in either document is *true but misleading*") and named three places to attack.
   Two of the three were clean; the third (§6.1 vs `commit_item_cost_evaluation`) was clean
   too. All three blocking findings came from the probes that asked for something the plan did
   *not* nominate — P3's key-by-key nullability walk and P4's "is there a third?". Consistent
   with the master plan §7 lesson already on the books: **an artifact's own "what to attack"
   line is a hypothesis by its author.** It held again here, one level up — the *plan's*
   nomination missed as cleanly as an intention's would.
