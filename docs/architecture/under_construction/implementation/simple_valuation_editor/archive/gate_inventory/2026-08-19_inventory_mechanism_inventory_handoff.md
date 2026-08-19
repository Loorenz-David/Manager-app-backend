---
plan: (pre-plan, project-level — no phase plans exist yet)
role: reviewer (mechanism-inventory gate)
round: inventory
date: 2026-08-19
verdict: OWNER_DECISIONS_PENDING
state: gate held — 3 owner cards open
actor: Claude (Opus 5, 1M)
---

# Mechanism-inventory handoff — `simple_valuation_editor`

## Opening summary

Gate check passed: intention read `RESOLVED (round 2)`, `owner_decisions.md` read **Ledger
empty**, `plans/` held only `.gitkeep`, `master_plan.md` §3 carried one gate row. The
sealed calibration file was **not opened** — it remains at its pre-session mtime.

All eight mechanisms were swept at equal depth against source re-read at head `f1c0ebb`.
**Six of the eight left the gate with a contract-grade definition; the remaining two are
blocked on product calls.** The intention delta is written as twelve lettered sections
(§2A, §3.1A, §3.1B, §3.2A, §4.2A, §4.4A, §5.3A, §6B, §7A, §8A, §9A, §12A) plus a §14
round-3 entry. No section was renumbered; `§6A` was deliberately skipped because that
number already names a section of the item-cost intention cited by HC-1 and by
`calculator.py`'s docstring.

**§14's closing nomination was wrong, and the prompt was right to forbid it as a scope.**
Both claims it nominated as "most worth attacking" survived: the `(n+1)/2` bound is sound
and attained, and the monotonicity argument is sound once stated about the right function.
Every defect worth a round was in a mechanism nobody flagged — M5's band (circular,
adjectival, and reproducing none of its own worked figures), §9.1's status rule (blanks the
screen for the two states the screen exists to resolve), `can_commit` (missing three of
five admission conditions), and M6 (named three times, defined nowhere).

**Three defects would each have shipped as a plausible wrong number**, which is the
silent-failure profile this gate exists for: a break-even 29 minor units off its own
definition, a slider band that cannot be computed in the order it is written, and counters
that disagree with the screen they are specified to agree with.

---

## ⚠ OWNER DECISIONS REQUIRED (3)

### Card 1 — Should the price screen work for an item nobody has priced yet?

**Question.** Should the slider appear for an item that has never been priced or never had
its budget committed?

**Story.** Marta photographs a dining chair that arrived this morning, creates the task,
and opens the price screen to decide what to ask for it. She sees the item, she sees that
chairs like it typically take 3h 25m — and there is no slider, no suggestion, no band. As
specified, the only items the pricing screen can price are the ones somebody has already
priced and committed. Every first pricing of every new item lands here.

**Branches.**
- *Show the slider whenever the workspace's cost setup resolves:* she prices the new chair
  on the screen built for it; two states now carry money figures where an already-shipped
  frontend rule says they carry none.
- *Keep the current rule:* the screen stays consistent with that shipped rule and is empty
  exactly when she needs it.

**Recommendation.** Show the slider — the cost setup is everything the arithmetic needs,
and the missing price is the variable the screen exists to choose.

**On silence.** The gate holds; the planner does not start.

**Trace.** §9.1, §9A.1, §12.6.

### Card 2 — What should Save do on an item that has no price yet?

**Question.** When an item has no price at all, should Save first set the price and then
commit, instead of committing alone?

**Story.** Marta drags to 1 425 kr on that same new chair and presses Save. The commit call
refuses it: it only accepts items that already carry a price row. Nothing is saved, and
pressing again changes nothing, because the press never created the price it needs. Chairs
that were priced last week save fine on the first press — only brand-new items fail, and
they fail every time.

**Branches.**
- *Save sets the price first, then commits:* first pricing works; that one path makes two
  calls instead of one.
- *Save stays commit-only:* the button is disabled on never-priced items and Marta has to
  price them on a different screen before this one is usable.

**Recommendation.** Set-then-commit — first pricing is the commonest reason to open this
screen, and D4's one-call promise still holds for every later price.

**On silence.** The gate holds; the screen ships with a disabled Save and no defined path.

**Trace.** §11 (D4), §9A.2, §8 `can_commit`.

### Card 3 — The slider's top end lands on 2 750, not the mockup's 2 700

**Question.** Accept a top end of 2 750 kr per piece where the mockup drew 2 700?

**Story.** When you accepted the derived band, the reason given was that it "reproduces
700–2 700 exactly for the mockup's own numbers". Done by hand at this gate, it does not:
the bottom lands on 700 exactly, the top lands on 2 750. No pair of multipliers gives both
700 and 2 700 from this item's data. The difference is one slider step at the far right,
on a handle that opens near the middle.

**Branches.**
- *Accept 2 750:* the rule stays derived and unchanged; the band is one step wider than the
  drawing at the top.
- *Re-pick the top multiplier to hit 2 700:* matches the drawing, by fitting a constant to
  one item's numbers — the thing choosing a derived band was meant to avoid.

**Recommendation.** Accept 2 750 — a band one step wider costs nothing, and fitting the
multiplier to a mockup reintroduces exactly the failure D6 rejected.

**On silence.** The gate holds; the band has no ratified constants.

**Trace.** §7.2, §7A.2, D6.

---

## The inventory — all eight rows

| # | Mechanism | Silent-failure risk | Contract before | Contract after | Lives at |
|---|---|---|---|---|---|
| M1 | price → budget → allowance, collapsed affine form + rounding | **Critical** — every figure on the screen; wrong rounding produces plausible numbers forever | **Partial.** Formula and scale factors correct and verified. `round_half_even` specified only as prose ("banker's-rounded integer division … BigInt in the client") with **no behaviour on negative `a`**, which is reachable at every price below the constant deduction — i.e. the `infeasible` state the screen exists to show. Input types uncanonicalised. §2.2's explicit obligation to name *which* rate is published was never discharged, and cited a non-existent "R3" | **Contract-grade.** Reference algorithm (floor-then-tie), Python and BigInt transcriptions with the sign correction, per-operation tie-reachability table, per-input type/canonicalisation table, rate named | §3.1A, §3.1B |
| M1b | the `(n+1)/2` bound vs the persisted per-term path | High — a false bound silently licenses the whole approximation | **Sound.** Re-derived independently: exact because `Numeric(6,3)` makes `×1000` lossless, so the collapsed residual adds no error before its single rounding. Bound is **attained**, so the assertion must use `≤`. Gaps: `n` never defined; the "≤ 1 minor unit → 0.07 s" illustration mixes `n=1` and `n=2` (1 unit is 0.046 s; 0.07 s is 1.5 units) | **Contract-grade.** `n` = non-deleted percentage terms; integer assertion form `2·|Δ| ≤ n+1`; display quantisation named (nearest minute — truncation renders the mockup's own row wrong) | §3.2A |
| M2 | break-even, the search, monotonicity | **Critical** — the chip flips on it and the whole band derives from it | **Broken in three ways.** (1) "strictly monotone non-decreasing" is self-contradictory and only the weak half is true — `round_he(P·r, 100 000)` is flat across consecutive `P` for every real model; (2) the argument is made about `budget` while the search runs on `allowance_seconds`, two roundings further on; (3) `P_hi` is taken from `domain.max_minor`, which §7.2 derives *from* break-even — **circular, uncomputable as written** | **Contract-grade.** Non-decreasing (not strict); composition argument supplied; `P_hi` by doubling from 1, independent of M5; lower-bound bisection form stated | §4.2A |
| M2b | suggested price and its ceiling-to-step | Medium | **Partial.** `ceil_to_step` never defined. §4.4's worked check computes a *real-arithmetic* price, not §4.1's least-integer price — **off by 29 minor units** (see audit) | **Contract-grade.** Both step helpers defined over exact rationals; corrected break-even; `suggested` shown unaffected | §4.4A |
| M3 | typical total: participating set, median substitution, no-evidence case | High — cross-screen disagreement, and §5.2's mirror claim is the only thing keeping two screens honest | **Partial.** Prose accurate; **both citations point at the wrong mechanism** (§5.1's `:322-327` is the per-section typical resolution, §5.2's `:355-370` is the excluded-row builder). Two real gaps: "usable" is `not None and > 0` in the allocator but "non-NULL" in §5.2, so a genuine 0-second typical is counted as sampled here and substituted there; and `_median` returns a `Fraction` that can be `x.5`, with no rule for turning it into an integer duration | **Contract-grade.** `usable()` defined; counters count non-usable; median quantised per section (not at the sum) with the reason; participating set re-cited | §5.3A |
| M4 | the saved-version byline | Low–medium | **Partial.** Three author cases named and all three verified correct. Silent on the two **absent** cases — no valuation row at all, and a row with a NULL price (legal: the CHECK requires only one of the two amounts) — which are the new-item states card 1 is about | **Contract-grade.** Resolution predicate, types, ISO/UTC, three absence rows; `currency` follows `saved` | §6B |
| M5 | the slider domain: band ends, step, `min_minor` floor | **Critical** — the manager drags this with their thumb | **Not a specification.** (1) **Circular**: spans need the step, the step needs the spans; (2) **"a nice step near X"** — two adjectives doing all the specification work, and no ladder produces 15 000 from 15 142 (1‑2‑5 → 20 000; decade → 10 000; snap-to-`quantity` → 15 144); (3) the `min_minor` floor is not a multiple of the step, breaking §7.4's only reason for the step to exist; (4) `infeasible_at_or_below_minor`, which the floor consumes, **is defined nowhere in the document** | **Contract-grade, pending card 3.** Exact-rational spans; per-piece two-significant-digit step (reproduces 15 000 / 25-per-piece and makes `quantity`-divisibility hold by construction); floor ceiled to a step multiple; empty-band guard; `infeasible_at_or_below_minor` defined in §4.2A | §7A, §4.2A |
| M6 | `config_fingerprint` | **Critical by name** (charter rule 6) | **Absent.** Named in §8, §9.3 and §9.5; derived in none. No inputs, no order, no truncation rule, no identity, no coverage claim. Separately, §9.3's "the client echoes `config_fingerprint`" is **unimplementable**: the commit endpoint has no such field and HC-2 forbids adding one | **Contract-grade.** Full ids, fixed order, `CALCULATION_VERSION` as identity, `null` with a null model; coverage *proved* (terms are immutable per version, so two ids cover the whole term set); midnight-rollover behaviour stated; the echo retired for the client-side reconciliation §9.3 actually needed | §9A.3 |

---

## Worked-example audit — every example, arithmetic done by hand

| # | Example | Claims | Arithmetic | Follows its rule? |
|---|---|---|---|---|
| 1 | §3.2 error in seconds | "≤ 1 minor unit … about **0.07 seconds**" | 1 minor unit at 1300/min = `60/1300` = **0.046 s**; 0.07 s = **1.5** units, i.e. `n=2` | **No** — the two halves use different `n`. Conclusion (invisible at whole-minute display) unaffected |
| 2 | §4.4 break-even | `266 500 / 0.22 = **1 211 364**` | Least `B` with `allowance ≥ 12 300` is **266 494** (`266 494/13 = 20 499.54 → 20 500` cm → 12 300 s); least `P` with `round_he(0.22P) ≥ 266 494` is **1 211 335**. At `P = 1 211 363` the allowance is *still* 12 300, so 1 211 364 is not minimal | **No** — solves a real-arithmetic equation, not §4.1's least-integer search. **Off by 29** |
| 3 | §4.4 suggested price | `ceil_to_step(·, 15 000) = 1 215 000` = **2 025**/piece | `ceil_to_step(1 211 335, 15 000) = 81 × 15 000 = 1 215 000`; `/6 = 202 500` = 2 025.00 | **Yes** — and unchanged by defect 2, which is how it survived round 2 |
| 4 | §7.2 band bottom | `0.35× = **424 000**` (`706`/piece) | `0.35 × 1 211 335 = 423 967.25`; `floor_to_step(·, 15 000) = **420 000**` = **700.00**/piece | **No as written, yes in effect** — 424 000 is the exact value hand-rounded, and `706`/piece is computed from the *unstepped* rational. The rule's real output is 420 000 = the mockup's 700 ✓, which §8's `min_minor` already carries |
| 5 | §7.2 band top | `1.35× = **1 635 000**` (`2 726`/piece), rendered `2 700` | `1.35 × 1 211 335 = 1 635 302.25`; `ceil_to_step → **1 650 000**` = **2 750.00**/piece (`floor` would give 1 635 000 = 2 725.00). 2 700/piece needs 1 620 000, i.e. a 1.337 multiplier | **No** — and unreachable under D6's multipliers by any rounding direction. §8's `max_minor` (1 635 000) matches neither the rule nor the claimed render. **Owner card 3** |
| 6 | §7.2 step | `span 1 211 000`, `/80 = 15 142` → "nice step **15 000**" | Span is exactly `B` = 1 211 335 (since 1.35−0.35 = 1); `/80 = 15 141.7`. 15 000 follows from **no stated rule**. It *is* `6 × 2 500` and 2 500 is `15 141.7/6 = 2 523.6` to two significant figures | **No** — the value is right, the derivation is absent. §7A.1 supplies a rule that produces it |
| 7 | §7.2 per-piece step | `25`/piece × 6 | `15 000/6 = 2 500` minor = 25.00 kr | **Yes** |
| 8 | §1 `AT PRICE 2h 25m` | at 855 000 | `budget = round_he(855 000×22 000, 100 000) = 188 100`; `cm = round_he(188 100/13) = 14 469`; `s = round_he(14 469×3, 5) = 8 681` = 144.68 min | **Yes, conditionally** — 2h 25m requires round-to-nearest-minute; truncation renders **2h 24m**. Rounding was unspecified; now §3.2A |
| 9 | §1 `TYPICAL 3h 25m` | 12 300 s | `12 300/60 = 205` min exactly | **Yes** |
| 10 | §1 / §7.4 per-piece vs total | `1 425` × 6 vs `8 550` | `855 000/6 = 142 500` = 1 425.00; §7.4's separate `855 100` case reads 1 425 / 8 551 and is correctly flagged there as the non-multiple illustration | **Yes** |

**Six of ten worked examples do not follow the rule they claim to check.** Five are
presentation errors around correct outputs; one (row 2) is a genuine off-by-29 that an
implementer would have copied into a fixture, where it would have passed review as "the
intention's own number".

---

## The §8 key walk

Every key mapped to a deriving section in §8A. **Four keys had no derivation anywhere in
the document:**

| Key | Was | Now |
|---|---|---|
| `config_fingerprint` | named in §8, §9.3, §9.5; derived nowhere | §9A.3 |
| `anchors.infeasible_at_or_below_minor` | *consumed* by §7.2's floor; derived nowhere | §4.2A |
| `can_commit` | an inline gloss in §8 missing 3 of 5 real conditions | §9A.2 |
| `currency` | undefined when there is no valuation row | §6B |

Plus `status`, whose only gloss was "EconomicsStatusEnum, 12 values" — now §9A.1.

**Three values in §8's example are wrong** (an example is a contract by demonstration; a
frontend will copy it): `"ivl_…"` → `"ival_…"` (the model's prefix is `ival`, and no model
in this domain uses `ivl`); `break_even_price_minor` 1 211 364 → 1 211 335;
`max_minor` 1 635 000 → 1 650 000. `residual_percent_milli: 22000` is correct but easily
misread as "a 22% cost" — it is the residual, so that model deducts 78%.

---

## Contradictions found, and which side won

| # | Sides | Chosen | What the other side ships |
|---|---|---|---|
| 1 | §4.1 defines break-even as a least-integer search; §4.4's worked example computes `budget/residual` in real arithmetic | **§4.1** | A break-even 29 minor units high, a chip that flips one step late, and a band shifted by ~0.0024% — all invisible, all wrong |
| 2 | §9.1 nulls the model for every status but `ok`/`infeasible`; §1 says the screen exists to choose a price | **Neither — routed to card 1** | Keeping §9.1 ships a screen that is blank for every unpriced and uncommitted item, i.e. useless for its stated purpose. §9.1 stands until answered |
| 3 | §9.1 "`item`, `saved`, `typical` stay fully populated"; §6 requires a valuation row to populate `saved` | **§6** (`saved: null`, `currency: null`) | A serializer dereferencing a missing row — a 500 on the empty state, or invented zeros |
| 4 | §7.2 derives spans from the step and the step from the spans | **Spans from exact rationals, step from `B` directly** | Nothing computes; the implementer picks an order and the band silently depends on the choice |
| 5 | §7.2 floors `min_minor` at `infeasible+1`; §7.4 requires every band value to be a multiple of the step | **Both — floor ceiled to a step multiple** | A `min_minor` off-grid, so the leftmost per-piece label is fractional — the one thing §7.4 exists to prevent |
| 6 | §5.2 treats "usable" as non-NULL; `budget_division.py:327` treats it as non-NULL **and > 0** | **The code** | A 0-second typical counted as sampled here and substituted there: `sections_without_sample` undercounts and the two screens disagree with no error anywhere |
| 7 | §9.3 has the client echo `config_fingerprint` to commit; HC-2 forbids changing commit's payload, and HC-2a enumerates four artifacts that do not include it | **HC-2** | Either a silent HC-2 breach in an implementer round, or a field echoed into an endpoint that ignores it |
| 8 | §2.3 says `resolve_item_economics_status` resolves twelve values; it can return nine | **The code** | A status matrix built for a function that cannot produce the two values the matrix keys on |

---

## Unilateral resolutions — listed for ratification

Each is a choice I made where no sentence looked like a decision, and each can carry
product consequence.

1. **`break_even_price_minor = 1 211 335`** for the mockup's data (definition beats worked
   example). Alternative: keep 1 211 364 by redefining M2 as a real-arithmetic solve —
   which reintroduces a non-integer boundary and the off-by-one at the chip's flip that
   §4.3 exists to prevent.
2. **Step = `quantity × two_significant_digits(B / (80 × quantity))`.** Reproduces 15 000
   and 25/piece from the data and makes `quantity`-divisibility structural. Alternative
   (1‑2‑5 ladder) ships a 20 000 step: 33/piece, and the mockup's 25 unreproducible.
3. **The band's ends stay `ceil`/`floor` to the step**, so the top is 2 750 — card 3.
4. **Median substitution quantised per section, half-even**, not at the sum. The two differ
   by up to one second per substituted section; per-section keeps each section's published
   value equal to what the allocator would weight.
5. **"Usable" = non-null **and** > 0** everywhere in M3, including the counters.
6. **The published rate is the persisted column**, not commit's recompute. They cannot
   drift (§2A.1.3), so this is a naming choice — but §2.2 demanded it be made.
7. **`config_fingerprint` is a readable concatenation, not a hash.** A hash would cost the
   client the ability to say which half moved and buys nothing at three components.
8. **`AT PRICE` rounds to the nearest minute.** Truncation makes §1's own row wrong.
9. **`saved: null` and `currency: null`** when no valuation row exists, overriding §9.1.
10. **`can_commit` is price-independent** (everything except the expected price, which Save
    supplies). Making it price-dependent is impossible on a GET.

---

## What I could not settle from the source

| Question | Why the code cannot answer it | What would settle it |
|---|---|---|
| Should `item_unvalued` / `not_evaluated` carry a model block? | The code is consistent and the *shipped frontend contract* says numerics are null there. Publishing them is a contract change with a live consumer, not an implementation choice | Owner card 1 |
| What Save does on a never-priced item | Commit refuses it by design (`:212-213`, `:228-230`); the alternative is a second endpoint, which is a product flow decision | Owner card 2 |
| Whether 2 750 at the top is acceptable | Aesthetic/product; no derivation reaches 2 700 from this data | Owner card 3 |
| Whether the `2**40` search cap is ever reachable in this workspace | Depends on real cost-model data I did not query (no DB reads this session, and none are needed for the gate) | A one-off query over live cost model versions at planning time; harmless either way since the cap returns `null` |

---

## Architecture graph

Not consulted this session: `.archgraph/` tooling was not exercised, and the gate's output
is a document delta with no code change to record. **What I would have recorded**, for the
human to adjudicate at implementation time: `domain-item-economics` gains no new node from
this gate; the future `projection-item-economics-task-price-scenario` node (master plan §4)
should carry §3.1A's `round_half_even` contract and §7A.1's `break_even_band_v1` rule as
evidence spans, because both are cross-language contracts that no single code file will
fully express. No graph node was found to disagree with the code, so nothing is filed under
`archgraph-discrepancies`.

---

## Write perimeter — full, generated from git

`git status --porcelain --untracked-files=all` at `f1c0ebb`. The project folder is
**untracked in its entirety**, so `git diff --name-only` is empty by construction and
cannot serve as the perimeter here; the enumeration below is git's untracked listing
cross-checked against mtimes (the degraded path, declared as such per the charter).

**Written by this session — two files:**

- `docs/architecture/under_construction/implementation/simple_valuation_editor/planning/intention.md`
  (the delta: twelve lettered sections + §14 round-3 entry + frontmatter `round: 2 → 3`
  and its `status:` line)
- `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_inventory_mechanism_inventory_handoff.md`
  (this report)

**Read, not written** — mtimes unchanged from before the session, confirming no write:

- `…/master_plan.md` (14:53:17)
- `…/planning/owner_decisions.md` (14:46:43)
- `…/prompts/reviewer/2026-08-19_inventory_mechanism_inventory.md` (14:54:47)

**Not opened:** `…/prompts/coordinator/2026-08-19_inventory_calibration_seal.md`
(14:53:49, unchanged) — sealed per master plan §7.

**`app/` is clean:** `git status --porcelain -- app/` returns nothing. No code file, test
or migration was touched; no test was run (none required by this gate). No database
connection was opened.

**Not updated, by instruction:** `master_plan.md` §3's tracker row — the coordinator owns
it.

---

## Gate verdict

**`OWNER_DECISIONS_PENDING`** — the gate holds.

M1, M1b, M2, M2b, M3, M4 and M6 now have contract-grade definitions in the intention. M5 is
contract-grade **conditional on card 3** (the rule is complete and computable; only its
top-end constant is unratified). The §9.1 status rule that M1's, M2's and M5's entire
visibility depends on is blocked on card 1, and `can_commit` on card 2.

The implementation-planner does not start on anything but `PASS`. Route the three cards
verbatim; on answers, fold them into §9.1/§9A.1, §11/§9A.2 and §7A.2, and the verdict
converts to `PASS` without a further sweep — no mechanism is left uninventoried.
