# Owner decisions — simple_valuation_editor

Verbatim register. Cards are relayed exactly as authored; answers are recorded with
date and the owner's own words where they carry nuance.

---

## Settled during intention shaping (owner conversation, 2026-08-19)

**D1 — per-piece is a frontend display transform.** The wire carries whole-item minor
units; `quantity` travels in the payload only as the divisor the client applies at the
display edge. Owner, verbatim: *"about the price per quantity i agree with you and that
will be a frontend boundery where it gets the quantity and uses that as denominator for
dividing the expected sold price."*

Context: the coordinator had flagged that the first two mockups' `× 6 pieces` headline
contradicted §8.4 of `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`
("a valuation is per item, not per unit … do not show '1000 × 5' anywhere near these
figures"). D1 resolves the contradiction in the direction that keeps the backend
contract intact: the backend still never multiplies, and only that section's *display
prohibition* is amended at closeout. Recorded consequence: the price this screen saves
is not required to be a multiple of `quantity`, and nothing enforces that it is; the
slider's step is a multiple of `quantity` purely so the screen's own two labels agree
(intention §7.4).

**D2 — a dedicated constants endpoint, not a per-frame preview.** Owner, verbatim:
*"I like the idea of creating an endpoint specialized in bringing this already
configured values so the frontend only needs to use them as constants to modify the
ui."*

Rejected alternative, recorded so it is not reopened: a debounced server round trip per
drag frame. It cannot hold a 60fps drag, and it makes the screen's responsiveness a
function of warehouse wifi. The design that replaced it rests on the item-economics
domain already being pure and closed-set (`domain-item-economics`), which is what makes
shipping the function's inputs a legitimate contract rather than a cache.

**D3 — the simplified screen is v1; expansion follows usage.** Owner, verbatim:
*"after some talk with the team we have simplify the visual aspect of the page for
changing the price, this will make what the backend sends more light, later we will
expand it base on usage."*

Recorded consequence: the cut list is intention §10, dated, with each item's return
path noted as an additive change. The most consequential cut is the per-section
breakdown, which removes `divide_production_budget` from this feature entirely — no
allocation, no largest-remainder, no share states. The second is the already-logged
card, which is what makes owner card 2 a real question rather than a detail.

---

## Round 1 cards — ALL ANSWERED (owner, 2026-08-19)

Relayed to the owner verbatim; answered in one pass. Owner, verbatim:
*"about the 4 owner cards all recommendations you have placed are correct."*

Every recommendation was accepted, so each card below is followed by its recorded
decision (D4–D7) and the consequence the coordinator folded into the intention. The
cards themselves are preserved unedited — the rejected branch is the part that stops a
later session from reopening a settled question.

### Card 1 — Does Save commit, or only set the price?

**Question.** Should the Save button set the price *and* make it the task's working
budget in one action, or only set the price?

**Story.** Marta drops the dining chairs from 2 050 to 1 425 on Thursday and hits Save.
On Friday the floor is still working to the old allowance, because a saved price does
not move a task's budget until someone commits it — and nobody knew there was a second
step. The worker cards keep promising time the new price no longer pays for, and the
gap only shows up when the job overruns.

**Branches.**
- *Save commits:* the number Marta saw is the number the floor works to, immediately.
- *Save prices only:* the screen needs an "uncommitted" banner and someone has to
  remember a second action, every time.

**Recommendation.** Save commits — the commit endpoint already accepts the price and
mirrors it into the price history, so it is one call, and the failure mode of
forgetting is silent.

**On silence.** The gate holds; the endpoint ships without a defined Save flow.

**Trace.** Intention §11, §8 (`can_commit`).

> **ANSWERED — D4 (2026-08-19): Save commits.** The screen's Save button is
> `POST /tasks/{task_client_id}/evaluations/commit` carrying
> `expected_sale_price_minor`. Folded into intention §11.
> **Consequence created by the answer:** `can_commit` stops being informational. Commit
> is admitted only for tasks in `_ADMITTED_STATES` with an active PRIMARY item, so a
> `false` value must *disable* the button — offering an action the screen knows will be
> rejected is worse than not offering it. Reconciliation against the commit response
> (intention §9.3) becomes mandatory rather than advisory, because that response is
> where the published display model meets the persisted authority.

### Card 2 — Should "AT PRICE" count time already lost to cancelled work?

**Question.** When a step on this task was worked on and then cancelled, should
"AT PRICE" still show the full time the price buys?

**Story.** A chair's sanding step fails after 20 minutes and is cancelled; the work is
redone under a fresh step. Marta opens the price screen that afternoon and sees the
price buys 2h 25m. The production-time screen for the same task shows 2h 05m, because
those 20 lost minutes are already spent. Two screens, two numbers, same task, same day.

**Branches.**
- *Gross:* the price screen answers "does this price fund the job", and the two screens
  differ by however much was lost.
- *Net:* the two screens always agree, but an item's price silently looks worse the
  more the job went wrong.

**Recommendation.** Gross — sunk time changes what is *left*, not what the job *costs*.
A divergence you can explain is better than a price that moves with accidents.

**On silence.** The gate holds; §5.4's divergence stays unratified.

**Trace.** Intention §5.4, §10.

> **ANSWERED — D5 (2026-08-19): gross.** `AT PRICE` and the typical are both whole-item
> totals; the allocator's `charged_seconds` deduction is not applied. Folded into
> intention §5.4.
> **Consequence created by the answer:** the divergence from the production-time screen
> is now a ratified property, which obliges the closeout handoff to *name* it. An
> accepted inconsistency nobody wrote down is indistinguishable from an undetected one,
> and the first manager to spot it will file one of the two screens as broken.
> `progress` stays out of the v1 payload (intention §10).

### Card 3 — Where do the slider's ends come from?

**Question.** Should the slider's minimum and maximum be derived from the suggested
price, or fixed numbers?

**Story.** The mockup's slider runs 700 to 2 700 per piece. A workspace that restores
cabinets prices them at 9 000 a piece — on that slider every cabinet sits pinned at the
right edge and the handle does nothing. And when a workspace raises its hourly cost next
quarter, a fixed band stays centred on last quarter's economics without anyone noticing.

**Branches.**
- *Derived* (0.35× to 1.35× of the suggested price): the band re-centres itself whenever
  the economics move, and reproduces 700–2 700 exactly for the mockup's own numbers.
- *Fixed:* predictable, and wrong for every item that is not a dining chair.

**Recommendation.** Derived — it reproduces your mockup today and stays sensible for
items the mockup never imagined.

**On silence.** The gate holds; the slider has no defined band.

**Trace.** Intention §7.2, §7.3.

> **ANSWERED — D6 (2026-08-19): derived.** The band is `break_even_band_v1` —
> 0.35× to 1.35× of the suggested price, stepped to a multiple of `quantity`. Folded
> into intention §7.1–§7.2. The rule reproduces the mockup's 700 / 2 700 / 25-per-piece
> from the data rather than from typed constants, which is the check that it is a rule
> and not a fit.

### Card 4 — What does the screen show when nothing has been measured yet?

**Question.** For an item whose sections have never been measured enough to have a
typical, should the screen show a typical anyway?

**Story.** A new workspace's first fifty items pass through sections with two or three
completed jobs each — not enough to trust a median. Marta prices a chair. The screen
either says "typically 0m", which invites her to think any price is generous, or it
says nothing and offers her no suggestion at all.

**Branches.**
- *Show nothing:* the typical, the chip and the suggested marker are all absent, with a
  reason line explaining that there is not enough history yet.
- *Show the partial sum:* a number that reads as authoritative and is built on two jobs.

**Recommendation.** Show nothing — a typical built on two samples can be wrong by a
factor, and a manager who trusts it prices the next fifty items on it.

**On silence.** The gate holds; §5.3's behaviour stays unratified.

**Trace.** Intention §5.3, §4.1.

> **ANSWERED — D7 (2026-08-19): show nothing.** With no usable typical among the
> participating sections, `typical_total_seconds` is `0`, `is_estimated` is `true`, the
> chip and the suggested marker are absent, and M2 returns `null`. Folded into intention
> §5.3.
> **Recorded rejection:** the allocator's `Fraction(1,1)` weight fallback is deliberately
> *not* copied here — a weight of 1 is meaningful as a proportion between sections and
> meaningless as a duration.

---

---

## Round 3 cards — mechanism-inventory gate (2026-08-19)

Three cards raised by the inventory sweep. **Two answered, one open.**

### Card 1 — Should the price screen work for an item nobody has priced yet? — ANSWERED

> **D8 (2026-08-19): show the slider.** Owner, verbatim: *"the frontend will allow to
> display the handle to set a expected sold price ( as the recommendation says, that is the
> whole point of that page, wheter there is or no expected sold price )."*

The recommendation is accepted: §9A.1's twelve-row table governs, and `model` / `anchors` /
`domain` are **present** for `item_unvalued` (B6), `item_missing_expected_price` (B7) and
`not_evaluated` (B10) as well as `ok` and `infeasible`. §9.1's "everything but ok and
infeasible is null" rule is superseded by that table.

**Recorded rejection:** keeping §9.1 as written. It ships a screen that is blank for every
unpriced and uncommitted item — that is, for every *first* pricing, which is the commonest
reason to open the screen. It fails silently: `200`, well-formed envelope, correct status,
no slider.

**Consequence created by the answer.** Two statuses now carry monetary figures where the
already-shipped frontend contract
(`HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` §6) says numerics are `null`.
That is a contract change with a live consumer, so it becomes a **closeout obligation**
(master plan §8, obligation 5) — the amendment is enumerated, not a general licence to
revise that document. HC-3's money-audience rule is untouched: this endpoint is
ADMIN/MANAGER only, so no monetary key reaches a worker or seller surface.

### Card 2 — What should Save do on an item that has no price yet? — RESOLVED WITHOUT A DECISION

> **D9 (2026-08-19): Save stays commit-only. The question does not arise.** Owner,
> verbatim: *"the frontend will build a default behaviour of telling the user to first
> place the purchase price of an item if missing, if that is set then the page for changing
> the expected sold price behaves normally, allowing the user to set the price and see the
> impact."*

The card asked whether Save must set the price before committing, because commit refuses an
item with **no valuation row at all** regardless of the price in the request body
(`commit_item_cost_evaluation.py:212-213`). The owner's flow removes that state before the
screen is ever reached. Verified by the coordinator, 2026-08-19:

1. `purchase_cost_minor` lives **on the valuation row**, so "purchase price is set" and "a
   valuation row exists" are the same fact.
2. `PUT /items/{id}/valuation` accepts a purchase cost **alone** — the request validator
   requires only *one* of the two amounts
   (`services/commands/item_economics/requests/__init__.py:177-179`), and the table's
   `ck_item_valuations_amount_present` CHECK agrees
   (`models/tables/item_economics/item_valuation.py:34`).
3. The resulting row yields status `item_missing_expected_price` (B7), which **is**
   commit-admissible: `effective` is built from the existing row with the request's price
   substituted, resolves to `not_evaluated`, and commits.

So **D4's one-call promise holds unchanged** and set-then-commit is not needed.

**The precondition the backend cannot enforce, recorded because it is the whole basis of
this resolution.** If a later frontend change skips the purchase-price prompt — for
instance as an optimisation when the cost model carries no purchase term — the item returns
to `item_unvalued` (B6), and Save fails on every press with nothing saved. `can_commit:
false` is exactly the signal that guards this, which is why §9A.2's predicate is
load-bearing rather than informational. **Closeout obligation** (master plan §8, obligation
6): the frontend handoff states that no valuation row means Save cannot commit, and that
the purchase price must be set first — Save will not create one.

### Card 3 — The slider's top end lands on 2 750, not the mockup's 2 700 — ANSWERED

Relayed; the owner asked for it in plainer terms and it was re-explained on 2026-08-19.

> **D10 (2026-08-19): accept 2 750.** Owner, verbatim: *"about card 3: the recommendation
> is the right approach."*

The multipliers stay `0.35` / `1.35`. For the mockup's data the band is
`min_minor 420 000` (700.00/piece, matching the drawing exactly), `max_minor 1 650 000`
(2 750.00/piece, one step wider than the drawing), `step_minor 15 000` (25.00/piece,
matching). Folded into intention §7A.2.

**Recorded rejection:** re-picking the top multiplier to `1.337` so the band lands on
2 700. It matches the drawing by fitting a constant to one item's numbers — the failure
D6 rejected fixed ends to avoid, reintroduced one level down where it is harder to see.

**One correction to the card as authored**, so no decision rests on a false premise: its
story states "No pair of multipliers gives both 700 and 2 700 from this item's data." That
is overstated — `(0.35, 1.337)` gives both, and the card's own second branch says as much.
The decision is unaffected: the objection to 1.337 was never that it is unreachable, only
that it is fitted.

---

## Ledger status

**Empty as of round 4, 2026-08-19. Mechanism-inventory gate PASSED.** D1–D3 settled during
shaping, D4–D7 ratified at round 2, D8–D10 at the inventory gate. No decision in this
intention is a guess, and every rejected branch is recorded beside the decision that
displaced it.

**One decision carries an external precondition.** D9 is sound only while the frontend
sets the purchase price before the price screen is reachable. It is the only decision here
whose basis lives outside this repository, and it is the one to re-check if the screen's
entry flow ever changes. Next gate: **implementation-planner**.
