---
plan: phase 5 (valuation surface)
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-13
actor: reviewer/projectionist (Claude Opus 5)
---

# Phase 5 projection — round 0 handoff

## Opening (owner-readable)

I did the implementer's first hour of phase 5 on paper, against the code as it
stands today rather than as it stood when the plan was written three days ago.
The plan is broadly sound — the valuation chain, the race, the deletion rules and
the history read all survive contact — but the **preview** (the estimate the
pricing screen shows after a price is saved) does not: the piece of code the plan
expects to exist only half exists, and the plan's own acceptance rules contradict
a standing rule about showing numbers. Sixteen items need fixing before an
implementer starts, six of them blocking. **Two questions need you personally**
— one about whether the pricing screen may show estimated numbers at all, one
about whether a deleted price stays visible in an item's history. Nothing else
needs the owner. Once those two are answered and the coordinator routes the
ledger, the implementer prompt can be compiled.

## ⚠ OWNER DECISIONS REQUIRED (2)

### Card 1 — May the pricing screen show estimated numbers?

**Question.** When a manager saves a price, should the response show the
production budget and the worker-minute allowance, even though nobody has
committed an evaluation for that item yet?

**Story.** Anna types 12 000 kr as the expected sale price for a wooden cabinet
and saves. The whole reason she uses this screen is to see "this leaves 4 300 kr
of production budget, about 330 worker-minutes" *before* she commits anything.
But we also have a standing rule that until a real evaluation exists, every money
and minute field must come back blank rather than as a number, so nobody mistakes
a guess for a decision. The two rules collide exactly here, and every preview row
in the plan depends on which one wins.

**Branches.**
- *Show the numbers* — Anna gets the estimate she came for; the payload must
  carry it under its own "preview" key so no screen ever renders it as a
  committed figure.
- *Keep them blank* — the endpoint returns a status word only, and the pricing
  screen cannot show an estimate at all until an evaluation is committed on a task.

**Recommendation.** Show the numbers, under a preview-only payload key that never
merges with committed figures — the estimate is this endpoint's stated purpose,
and the blank rule exists to stop *unknown* inputs reading as zero, not to hide a
fully computed projection.

**On silence.** The gate holds; phase 5 is not compiled. No guess is made.

*Trace: intention §11 (valuation endpoint), §11A.4 null-numerics rule, §11A.5;
master plan §9 P-B; phase-5 plan task 2 and C5.*

### Card 2 — Does a deleted price stay in the item's history?

**Question.** When a manager deletes an item's current price, should that price
still appear in the item's price history afterwards?

**Story.** In March someone typed 1 200 kr for a chair, noticed it was the wrong
item, and deleted it. In August a colleague opens that chair's price history to
explain a margin to a customer. Either they see the March entry sitting there
marked as deleted, or the history simply starts at the corrected price as if the
mistake never happened.

**Branches.**
- *Hide deleted entries* — the history reads as the real pricing story; a
  mistyped entry disappears along with the mistake.
- *Show deleted entries, marked* — nothing is ever lost, but the list carries
  corrections every reader has to interpret.

**Recommendation.** Hide them — deleting the current price is the documented
escape hatch for a mistaken entry, while genuinely superseded prices (the actual
history) can never be deleted at all, so nothing real is lost either way.

**On silence.** The gate holds; the history query ships with no stated filter and
the plan's phrase "history retained" stays ambiguous.

*Trace: intention §4.7A, §7.5; phase-5 plan task 4, C4, C6.*

---

## Amendment ledger

16 rows: **6 blocking**, **10 should-fix**, plus 7 notes below. Every "verified
correction" was checked against the tree or executed, never reasoned about
(P-I fourth extension).

| # | Severity | Amends | Decision point | Classification |
|---|---|---|---|---|
| L1 | blocking | task 2; master §6.5; Files list | The preview has no way to obtain the *selected* group/basis/model rows | plan gap + registry |
| L2 | blocking | task 2; master §6.3/§6.5 | §11A.4 group-2 rows 5–9 have no owner, no name, no precedence sequence | plan gap + registry |
| L3 | blocking | C5; §11A.4; master §9 P-B | `not_evaluated` with numbers contradicts the null-numerics rule | intention gap → **owner card 1** |
| L4 | blocking | C5 | The preview criterion samples a 12-value ordered vocabulary (5 rows) | plan gap |
| L5 | blocking | C4 row 1; master §6.5 routes | `ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE` is unreachable through the registered surface | plan gap (P-S) |
| L6 | blocking | C4; task 3 | "subsequent status reads `item_unvalued`" names no surface that exists in phase 5 | plan gap |
| L7 | should-fix | task 1; C3 | `ITEM_COST_VALUATION_AMOUNT_REQUIRED` loses its leading-token position through the shipped parser | plan gap (verified) |
| L8 | should-fix | Files expected to change | Three files that must change are absent from the list | reality check |
| L9 | should-fix | task 1/3; master §6.4 | Audit events for this phase are unregistered and uncriterioned | registry + plan gap |
| L10 | should-fix | C3 | The DB-CHECK half of C3 already shipped in phase 2 | reality check (P-L) |
| L11 | should-fix | C2 | The race harness, its seam and its fixture are unnamed | plan gap (P-T) |
| L12 | should-fix | Notes → criteria | The N7 persisted-rate arbiter is a Note, not a criterion | plan gap (P-Q) |
| L13 | should-fix | task 4; C6 | History predicate and ordering underdetermined | plan gap → **owner card 2** (visibility half) |
| L14 | should-fix | Dependencies; task 2; Read first | Round-12 prose drift | plan gap |
| L15 | should-fix | master §6.5 | The registry claims a 4B structural guard that does not exist | reality check |
| L16 | should-fix | C5 | §6A.9's three-way currency equality is represented by one row | plan gap |

### L1 — the §7C.2 *selection outcome* is not returned by anything (blocking)

Task 2 says the preview computes "via the §7A.5 classifier and the calculator".
The shipped classifier is
`resolve_economics_configuration(major_category, groups, basis_versions,
cost_model_versions, on_date) -> EconomicsStatusEnum`
(`app/beyo_manager/domain/item_economics/configuration.py:44-82`). It returns a
**status only**. To compute a budget and an allowance the preview needs three
more things the classifier resolves internally and then discards: the selected
group, the applicable basis version (for `cost_per_worker_minute_minor` *and* the
basis currency), and the applicable cost-model version **and its term rows**.

Master plan §6.5 already promised this half — "pure §7A.5 ordered classifier over
loaded rows → `EconomicsStatusEnum` **/ selection outcome**" — but only the status
half was built. `get_economics_configuration_status.py:41-52` already re-derives
`selected_group` inline (the second site); phase 5 would be the third, and phases
7 and 8 the fourth and fifth. Divergence between the classifier's notion of "the
selected group" and a caller's copy of it is a silent mis-pricing, not a crash.

**Verified correction.** Add a registered pure function in `configuration.py`
returning the status *and* the selected rows (`selected_group`,
`basis_version`, `cost_model_version`), name routed to master §6.5, with
`resolve_economics_configuration` implemented in terms of it so the two can never
disagree. Add `domain/item_economics/configuration.py` to the plan's Files list.
Note for the coordinator: the term rows must also be loaded (see L2/L3's
`item_missing_purchase_cost` predicate) and the loader belongs in the command, not
in the pure module.

### L2 — §11A.4 group-2 rows 5–9 have no owner (blocking)

`CONFIGURATION_FAILURE_PRECEDENCE` (`configuration.py:13-19`) is a **5-tuple**:
category, no-group, ambiguous, no-basis, no-model. The remaining ordered reasons
— `item_unvalued` → `item_missing_expected_price` → `item_missing_purchase_cost`
→ `currency_mismatch` → `not_evaluated` — exist only as enum members
(`enums.py:21-25`). The plan gives the preview no home and no name for that
ordering, so the implementer will inline a first-match chain inside
`set_item_valuation.py`, and phase 8's status query will inline a second one.

This is a first-match ordered rule over money inputs: charter rule 6's
silent-failure class. A mis-ordered chain reports `currency_mismatch` where the
truth is `item_missing_expected_price` — a wrong repair instruction, never an
exception.

**Verified correction.** A second registered ordered sequence plus its resolver in
`configuration.py` (name to master §6.5; the §6.3 note that "declaration order
carries NO precedence" applies verbatim), consumed by phase 5's preview and phase
8's status query. Carry 4B's B6-shaped structural probe: permuting
`EconomicsStatusEnum`'s declaration order must leave every row green, and
permuting the *sequence* must redden.

Ordering detail the plan must state, because it is not obvious:
`item_missing_purchase_cost` fires **only when the selected cost-model version
carries an `item_purchase_cost` term** (§11A.4 group 2 row 7), so the preview must
load the model version's non-deleted terms — which no shipped code path loads.

### L3 — `not_evaluated` with numbers contradicts P-B (blocking → owner card 1)

C5 row 2 requires `not_evaluated` "with exact budget/allowed preview values".
§11A.4's closing rule: "for every value except `ok` and `infeasible`, the
payload's numeric fields are **`null`**, never `0` and never omitted". Master §9
P-B restates it: "Every status payload row for a non-`ok`/`infeasible` status
carries `null` numerics". `not_evaluated` is a group-2 value.

C5's preamble quietly narrows P-B to "every **non-computable** status" — that
narrowing *is* the amendment the plan needs, but it was never routed to §11A.4 or
§9, so the plan and its two authorities disagree in writing. §11 meanwhile states
the endpoint "returns the recomputed economic preview (budget + allowed
worker-minutes)", i.e. numbers, and §11A.5 says only that the preview "carries the
same status vocabulary" — it does not resolve the rule.

**Routing.** Upstream (home-artifact rule): an intention amendment to §11A.4 (or a
lettered §11A.5 clause) plus a P-B refinement in master §9, both waiting on owner
card 1. No plan edit can settle this.

### L4 — C5 samples a 12-value ordered vocabulary (blocking)

C5 carries five preview rows. Reachable-but-unenumerated in this phase:

- `item_missing_major_category` — **the plan's own N-d Note mandates it** ("the
  preview's criteria include it with P-B null-numerics") and it is a live outcome
  for 53 of 471 items (L17). C5 has no such row.
- `not_configured_no_basis_version`, `not_configured_no_cost_model_version` — both
  reachable; C5 covers only "no group".
- `not_configured_ambiguous_cost_group` — structurally unreachable under INV-G3
  (§7C.2 keeps it as the total-order defence row); needs a recorded reachability
  judgment (P-S), not a row.
- `item_unvalued` — see L6.
- `ok` / `infeasible` — group 1 is task-scoped and the preview is item-scoped; the
  plan should state that judgment rather than leave it inferred. `infeasible`
  (allowance ≤ 0, from a negative budget) is arithmetically reachable in a preview
  and needs an explicit in/out decision.

**Verified correction.** Rewrite C5 as an enumeration over §11A.4's 12 values with
one exact expected outcome and one reachability judgment per row (charter rule 2,
P-V), each parametrize id naming the authority row it discharges (P-V extension,
e.g. `status-row-7-missing-purchase-cost`), each fixture sole-predicate.

### L5 — `ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE` is unreachable (blocking)

C4 row 1 requires a superseded-row delete to raise
`ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE` (§6.4, registry-authored). But master
§6.5 registers exactly three valuation routes, all item-scoped
(`PUT|DELETE /items/<item_client_id>/valuation`,
`GET /items/<item_client_id>/valuations`) — verified against the shipped router,
which has no valuation-addressed path
(`app/beyo_manager/routers/api_v1/item_economics.py:94-216`). Task 3 defines the
command as "the **current** row only". A caller therefore cannot name a superseded
row, and the guard can never fire in production.

**Verified correction (P-S).** Either (a) keep the item-scoped surface, satisfy
C4 row 1 by calling the command directly with a superseded valuation's client_id,
and record the reachability judgment in the plan; or (b) register
`DELETE /valuations/<client_id>` in §6.5 and make the guard live. Recommend (a) —
(b) adds a surface no product requirement asked for. Whichever is chosen, C4 row 1
must state which, because "delete a superseded row" is not currently expressible.

### L6 — C4's "subsequent status reads `item_unvalued`" has no surface (blocking)

Phase 5 ships exactly one status-producing surface: the preview returned by `PUT`.
Phase 7 owns evaluations, phase 8 owns the status query. So after a delete there is
nothing in this phase that can be read to observe `item_unvalued` — the criterion
is undecidable as written. The plan's Notes hint at the fix ("the preview payload
for it is status-only"), but task 3 never says the DELETE response carries a
preview.

**Verified correction.** Either task 3 declares that `DELETE` returns the
status-only preview (then C4 gets its arbiter and `item_unvalued` gains a phase-5
row, closing L4's gap for that value), or the clause moves to phase 8's plan.
Recommend the former — it is the only way `item_unvalued` is ever exercised before
phase 8.

### L7 — the amount-required identity loses its leading token (should-fix)

§6.4's carrier decision: an error identity is the **leading token** of `message`,
and tests assert the exact leading token. The shipped parser wraps every pydantic
failure as `ValidationError(f"{field}: {first['msg']}")`
(`services/commands/item_economics/requests/__init__.py:115-121`).

Executed against the shipped `_parse` with the natural implementation (a
`model_validator` raising the identity):

```
ValidationError | ": Value error, ITEM_COST_VALUATION_AMOUNT_REQUIRED: at least one amount is required"
```

The identity is not leading; an assertion of the form
`message.startswith("ITEM_COST_VALUATION_AMOUNT_REQUIRED:")` fails, and the
implementer will "fix" it by weakening the assertion to a substring match.

**Verified correction.** Task 1 states that the ≥1-amount rule is raised as a
domain `ValidationError` **outside** the pydantic model (in the parser function
after `_parse` returns, or in the command), and C3's row asserts the leading token
exactly. Negative amounts and missing currency stay pydantic-side per §6.4 (they
carry no identity), so only this one rule needs the exception.

### L8 — Files expected to change is incomplete (should-fix)

Verified against the tree. Correct as listed: `set_item_valuation.py`,
`delete_item_valuation.py`, `get_item_valuation_history.py` (all three new),
`requests/__init__.py`, `domain/item_economics/serializers.py`,
`routers/api_v1/item_economics.py`, `routers/README.md` (item-economics mirror
rows present at `app/beyo_manager/routers/README.md:58-70`, so phase 5 appends
three). Missing:

- `app/beyo_manager/domain/item_economics/configuration.py` — L1, L2.
- `app/beyo_manager/services/commands/item_economics/_common.py` — the
  `INDEX_IDENTITIES` map (`:20-28`) has no `uix_item_valuations_current` entry, so
  the INV-V1 conflict will re-raise unchanged and surface as HTTP 500 rather than
  `ConflictError ITEM_COST_CONCURRENT_VALUATION`. Adding the entry is the whole
  fix; the uniform conflict sentence stays per phase-4 N4 / 4B L-9.
- `app/tests/unit/routers/api_v1/test_item_economics_router.py` — the `_ROUTES`
  fixture (`:12-35`) is the shipped P-R harness and must gain three rows or the
  new routes have zero role-gate arbiters (see also L20).
- `master_plan.md` §6.4 (audit vocabulary, L9) and §6.5 (function/serializer
  names from L1, L2, L15).

Path nit: the plan writes `routers/api_v1/item_economics.py` and
`routers/README.md` without the `app/beyo_manager/` prefix used by its other
entries.

### L9 — audit vocabulary unregistered, and no audit criterion (should-fix)

§6.4's audit block ends with an explicit instruction: "(phases 5/7 add
`item_valuation.*` / `item_cost_evaluation.*` rows here **before use** — never
free-formed in a command.)" No phase-5 task, criterion or Note mentions audit at
all, while phase 4 shipped C11 asserting all nine registered strings and had the
retention mutation named (P-G(a)).

**Verified correction.** Register `item_valuation.created` and
`item_valuation.deleted` in §6.4 (names proposed; the coordinator owns them), and
add a criterion in the shape of phase-4's C11 — each valuation command writes
exactly one registered audit event, with the registered-string list as the table.

### L10 — C3's DB-CHECK half already shipped in phase 2 (should-fix)

C3 demands "request layer AND DB CHECK (both paths per row)". The DB half exists
and is APPROVED:
`app/tests/integration/models/item_economics/test_item_economics_schema.py:581-616`,
`test_item_valuation_amount_and_currency_boundaries`, six ids —
`negative-sale`, `negative-purchase`, `both-null`, `null-currency` (reject) and
`price-only`, `cost-only` (accept). Left as written, phase 5 builds four duplicate
rows.

**Verified correction.** C3 cites the phase-2 rows by node id and scopes phase 5 to
the request-layer half plus the `ITEM_COST_VALUATION_AMOUNT_REQUIRED` identity
(L7). P-L: state what already exists, not only what is skipped. See also L22.

### L11 — C2's race harness, seam and fixture are unnamed (should-fix)

Phase-4 re-review r2 filed exactly this as N6 ("C3's monkeypatched-audit seam
undeclared in the plan"). The precedent harness is
`app/tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py:238-314`:
two sessions from `database._session_factory()`, the command's `audit` call
monkeypatched into an `asyncio.Event` gate, **bounded** waits
(`asyncio.wait_for(..., timeout=0.3)` — P-T extension, after an unbounded wait hung
a suite for 120 s), explicit FK-ordered teardown, and an "exactly one open row
afterwards" count assertion.

Two things the plan must additionally pin:

1. **Which fixture.** §7A.2's described interleaving requires a *pre-existing
   current valuation*: the loser's S1 blocks on the winner's row lock, returns
   rowcount 0 after the winner commits, then its S2 conflicts. A **first**
   valuation for an item races differently (both S1s return rowcount 0 without
   blocking, and only the index arbitrates). These are two distinct paths; C2 as
   written ("two sessions past S1") is satisfied by the easier one. Enumerate both,
   or name one and say why.
2. **Which seam.** If phase 5's command calls `audit` after S3, the phase-4 gate
   transplants directly; if it does not, the plan must name the seam it does use.

### L12 — the N7 persisted-rate arbiter is a Note, not a criterion (should-fix)

The plan's forward item ("a criterion must prove it consumes the PERSISTED
`cost_per_worker_minute_minor`… fixture from the Q2-tie family where the two
differ") never became a criterion; C5's `not_evaluated` row only says "exact
budget/allowed preview values (calculator-derived)", which passes under either
implementation. This is P-Q's exact shape: an implication pin whose fixture must
make the pinned clause the sole cause.

**Verified fixture (computed, and already seeded in the repo).**
`fixed_monthly_cost_minor = 100000`, `monthly_paid_hours = 160.00`,
`planning_utilization_percent = 80.00` → raw rate `13.020833333…`, persisted Q2
rate **`13.0208`** — the exact triple already used at
`test_phase4_fix_coverage.py:648-658`. With `production_budget_minor = 1 000 000`:

| Allowance from | Q3 result |
|---|---|
| persisted `13.0208` | **76800.20** |
| re-divided from basis inputs | 76800.00 |

Named mutation: in the preview, replace the persisted-rate read with
`calculate_cost_per_worker_minute(fixed, hours, util)` — must redden exactly this
row and nothing else.

### L13 — history predicate and ordering underdetermined (should-fix)

Task 4 says "full chain, newest first"; C6 asserts "all rows in order with exactly
one current". Three things are not determined:

- **Does history include soft-deleted rows?** After a delete-then-reset, the
  deleted row still has `superseded_at IS NULL` and `is_deleted = true`. → owner
  card 2.
- **What is "exactly one current"?** It must be INV-V1's predicate
  (`superseded_at IS NULL AND is_deleted = false`, `item_valuation.py:35`) — under
  the looser `superseded_at IS NULL` reading, the delete-then-reset fixture has
  **two**, and C4's own last row builds exactly that state.
- **"Newest first" is not a total order** (charter rule 5). `created_at` is
  Python-side (`item_valuation.py:25`), so two rows can tie. Pin
  `created_at DESC, client_id DESC`.

C6's "byte-identical re-read" is decidable as written (serialize twice, compare
the payloads) once the above are pinned.

### L14 — round-12 prose drift (should-fix)

- **Dependencies** says "Phase 4 APPROVED"; the real gate is **4B** APPROVED
  (master §7 sequences 4B before 5; 4B closed at `377d0b9`).
- **Task 2 and Dependencies** cite "the §7A.5 classifier". §7A.5's group-resolution
  rows are superseded by §7C.2 (round 12); rows 3–6 survive *per the selected
  group*. The plan predates that and reads as if group resolution were "the single
  active group".
- **Read first** omits §7C entire (the governing selection rule), master §6.3
  (`EconomicsStatusEnum` ownership and the declaration-order correction), §6.4
  (error identities, incl. the 4B additions), and master §9's P-rules beyond P-B —
  the prompt binds P-A…P-Z, the plan cites one.

Citations that **do** resolve, checked: intention tests 17 / 12 / 11 say what C1 /
C2 / C3 claim (§14); §4.7A, §7.5, §7A.1–7A.2, §11, §11A.4–§11A.5, §6A.9 all
resolve; all six named contract files exist under `backend/architecture/`.

### L15 — the registry claims a 4B structural guard that does not exist (should-fix)

Master §6.5 says of `resolve_major_category`: "the only reader **within the
item-economics domain**: no module under `domain/item_economics/` or
`services/**/item_economics/` reads `item_major_category_snapshot` except through
it (**a structural row in 4B guards this**)". No such test exists — a grep of the
whole test tree finds `item_major_category_snapshot` in exactly one test file
(`tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py`),
and 4B's own plan (`plans/phase_4b_category_selection.md:479-483`) *forwards* the
per-item path to phase 5 rather than guarding it.

This matters now because phase 5 is the first production caller: the cheapest
implementation is `item.item_major_category_snapshot == "wood"` inline, which
passes every criterion in the plan.

**Verified correction.** Phase 5 carries the structural row (P-J/P-X shape: name
the source the test inspects, and its own named mutation — inlining a snapshot
read in the preview must redden it), and §6.5's parenthetical is corrected from
"a structural row in 4B guards this" to name phase 5.

### L16 — one currency row where §6A.9 mandates three (should-fix)

C5 has a single currency row (valuation ≠ basis). §6A.9 step 3 asserts a
**three-way** equality (valuation = basis = model) and says so explicitly:
"Enumerated as three criterion rows (valuation≠basis, valuation≠model,
basis≠model), not one sampled row." All three are reachable — basis and model
currencies are independent NOT NULL columns with no cross-table constraint
(`production_cost_basis_version.currency`, `cost_model_version.currency`), so
basis≠model is ordinary configuration drift, not a hostile fixture.

**Verified correction.** C5 carries three currency rows, each fixture varying only
its own pair, and the message assertion names each side individually (P-O — an
`or` between the two values is satisfiable by half).

---

## Notes (no routing required, recorded for the coordinator)

**L17 — N-d live re-measurement (the plan's claim has drifted).** Measured
2026-08-13 against the configured dev DB (`beyo_manager` @ 127.0.0.1:5433, head
`5caae620088c`):

| Snapshot | Non-deleted items | Deleted |
|---|---|---|
| `NULL` | **53** | 0 |
| `wood` | 225 | 0 |
| `seat` | 193 | 0 |
| unknown string | **0** | 0 |
| **total** | **471** | 0 |

The plan's Note says 37 NULL / 225 wood / 193 seat. Wood and seat are unchanged;
**NULL has drifted 37 → 53**. `item_missing_major_category` is therefore a live
preview outcome for 11.3 % of items, exactly as the Note claims — the number is
what changed, not the conclusion. Also live-verified: there are **no** items
carrying a non-vocabulary snapshot string and **no** soft-deleted items at all, so
`resolve_major_category`'s unknown-string → `None` branch has no live-data
instance today and remains a defence branch (already unit-pinned by 4B at
`test_phase4b_category_classifier.py:69-73`).

**L18 — the self-FK teardown hazard I expected does not exist (executed).**
`fk_item_valuations_superseded_by_id` is `ondelete=RESTRICT` and self-referential,
so a naive `DELETE FROM item_valuations WHERE workspace_id = …` covering a whole
chain looked likely to fail on the self-reference. Probed inside a rolled-back
transaction on the dev DB: build old row → supersede → insert new → link
`superseded_by_id` → single-statement delete of both. Result: `DELETE 2`, zero rows
left, no error. **The plan needs no special teardown ordering for the self-FK** —
recorded so nobody adds a defensive NULL-out step that has no reason to exist.
The same probe incidentally re-confirmed §7A.1's premise empirically: inserting
two open rows for one item in a single statement raises
`duplicate key value violates unique constraint "uix_item_valuations_current"`,
which is precisely why C1 exists.

**L19 — forward-note N5's count is wrong.** The Note says "parametrize C8's **six**
looped fixtures into named rows". The shipped loop
(`test_phase4_fix_coverage.py:614-672`) has **five** cases: `no-cost-group`,
`no-basis`, `basis-not-applicable`, `no-model`, `all-present`. P-L (items, never
counts). The underlying finding stands — it is a `for` loop, not a parametrize, so
a failure reports one node id for five fixtures.

**L20 — the router harness's names will overclaim.** `_ROUTES` and both
role-gate tests are named `…every_configuration_route…`
(`test_item_economics_router.py:12-79`). Adding the three valuation routes to that
list makes the names cover more than they say (P-G(b): name the audience/surface,
not one example). Either rename to `…every_item_economics_route…` or add a second
list. The generated parametrize ids stay unique for the new routes
(`put-valuation`, `get-valuations`, `delete-valuation`).

**L21 — a Protocol-shape mismatch the preview will hit.**
`calculate_term_amounts(term_rows: Sequence[TermSnapshot], …)`
(`calculator.py:213`) types its argument as `TermSnapshot`, whose Protocol
requires `amount_minor` (`calculator.py:66-71`) — a field that exists on
`ItemCostEvaluationTerm` snapshots, not on the live `CostModelTerm` rows the
preview will pass. Runtime-safe (only `calculation_type`, `percent_value`,
`fixed_amount_minor` are read), but worth one line in the plan so a reviewer does
not file it as a defect and an implementer does not "fix" it by inventing a field.

**L22 — passing-glance, phase 2, settled.** In
`test_item_valuation_amount_and_currency_boundaries` the `both-null` case sets
`constraint_name = None` and so asserts a bare `IntegrityError` with no `match`
(`test_item_economics_schema.py:592-616`). `ck_item_valuations_amount_present`
therefore has no named arbiter: any other integrity failure on that INSERT would
satisfy the row. Phase 2 is APPROVED and this is out of phase-5 scope — reported
per the charter's "anything seen wrong in passing" clause, as a candidate for the
next touch of that file (it is the file L10 asks phase 5 to cite).

**L23 — free choices to delegate explicitly** (so the implementer's freedom is
granted, not taken): the response envelope keys for the valuation and the preview
(phase-4 precedent is `{"<entity_name>": {…}}`); whether the preview is computed
inside or outside the command's transaction; whether S1 is preceded by a SELECT of
the current row (S3 needs its client_id either way); the `NotFound` behaviour when
the item client_id does not resolve in the workspace (phase-4 precedent:
`_common.get_group` raises `NotFound`).

---

## Environment facts recorded (verified this session)

- **Migration head** `5caae620088c`; dev DB at head. Economics tables all at
  **zero rows** (`item_valuations`, `production_cost_groups`,
  `production_cost_basis_versions`, `cost_model_versions`,
  `item_cost_evaluations`) — verified before and after my probes.
- **Collection**: `PYTHONPATH=. pytest --collect-only -q` → **1951 collected**
  in 1.40 s = 1950 selected (1927 passed + 23 known failures) + 1 deselected.
  Consistent with the prompt's baseline; no drift.
- **Containers healthy**: `app-postgres-1` (5433) and `app-redis-1` (6380) both up.
- **Disposable database: not needed for phase 5.** Every criterion is
  service-layer or request-layer; the phase ships no migration and no DDL, so
  charter rule 7's destructive-verification path does not apply. The one DB-CHECK
  family the plan mentions (C3) already ran on the configured DB in phase 2.
- **Teardown scope statement (rule-11½ record).** `db_session`
  (`app/tests/conftest.py:47-50`) **rolls back** at teardown, so every
  non-committing criterion is self-cleaning. Only C2's two-session race commits;
  its `finally` must delete, in this order, `item_valuations` → `audit_logs` →
  `items` → `users` → `workspaces` for the fixture's workspace (no special
  self-FK handling — L18). The residue check must name those five tables: per §10
  the wider suite is known to commit ~116 non-economics workspaces per full run,
  so "two runs → flat" is only meaningful when scoped.

## Full write perimeter

- **Documents written:** this handoff only —
  `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-13_phase5_projection_r0_handoff.md`.
- **Code / tests / plans / intention / master plan:** zero changes. No file under
  `app/` was created, edited or deleted; no plan file was touched (the coordinator
  routes every row above).
- **Database:** read-only queries plus two probes, both executed inside
  transactions that were **rolled back**; `item_valuations` re-queried afterwards
  and confirmed at 0 rows. Dev DB left at head `5caae620088c`. No test run
  committed anything (collection only — the suite was not executed).
- **Scratchpad (outside the repo):** `…/scratchpad/probe.sql`, the rolled-back
  self-FK probe. Not part of the repo tree.
- **Architecture graph:** READ-ONLY, one `archgraph_status` call, **zero delta**.
  Verified state matches the prompt exactly — revision
  `88e185f753253d889a600f23d54228eec8f272281955dfdae49b82a7ec3b517c`,
  **148 nodes / 188 edges**, 0 pending, 0 stale, 0 diagnostics.

## Exit gate

Verdict **AMENDMENTS_REQUIRED**. Six blocking rows (L1–L6) must be routed before
the implementer prompt compiles; L3 and the visibility half of L13 are blocked on
owner cards 1 and 2. The ten should-fix rows are plan/registry amendments the
coordinator can apply directly. The skeleton I derived while doing this is
deliberately **not** attached — the implementer derives their own (fresh-session
rule).
