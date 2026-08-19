---
plan: (pre-plan, project-level)
role: coordinator
round: inventory
date: 2026-08-19
kind: standing coordinator document — NEVER handed to a session
---

# SEALED — calibration probe on the mechanism-inventory sweep

**Do not open until the inventory handoff is on disk.** This file records what the
coordinator found in `planning/intention.md` by arithmetic *before* authoring the
inventory prompt. The prompt deliberately does not contain any of it.

## Why this is legitimate, and where its limit is

The charter forbids anchoring a **projection** with known suspected defects, and allows a
known defect to serve as a calibration probe **only if it still exists when the session
runs** — never preserved for the probe's sake. Both conditions hold: these defects are in
the resolved intention right now, and the inventory is precisely the session whose job is
to fix them. Nothing is being preserved; the next session is the one that removes them.

**Disclosed hint.** The prompt *does* carry one methodological instruction that points at
the neighbourhood of finding 1 — "verify every worked example by doing its arithmetic."
That is a general rule earned in `master_plan.md` §5 and it would be dishonest to withhold
a method to protect a score. The calibration therefore measures whether the sweep finds
the defects **given the method**, not whether it invents the method. Findings 2 and 3 have
no corresponding hint.

**What this file is not.** It is not a grading rubric and not a scope. An inventory that
finds none of these and finds three others may well be the better sweep. The only
conclusion this file supports is about **coverage**: a sweep that contracts M5 without
noticing that M5 contradicts itself has not read M5 adversarially, whatever else it did.

## Findings, sealed

### 1 — M5's worked example contradicts M5's own rule, in three places

Intention §7.2 states the rule, then "checks" it against the mockup. The check does not
follow the rule.

Taking `break_even_price_minor = 1 211 364` and `step_minor = 15 000` as §7.2 does:

- `span_high = ceil_to_step(1.35 × 1 211 364, 15 000)`. The product is **1 635 341.4**;
  the smallest multiple of 15 000 at or above it is **1 650 000**. §7.2 prints
  `1.35× = 1 635 000` and §8's payload carries `max_minor: 1635000`, which is the
  *floor*, not the ceiling. Under the stated rule the band's top is 1 650 000
  (2 750/piece), not the mockup's 2 700.
- `span_low`: the arithmetic is right (`floor_to_step(424 007.4, 15 000) = 420 000`,
  matching the payload) but §7.2 prints the **un-stepped** 424 000 and labels it
  706/piece, then claims the band renders at 700/piece. Two different numbers are
  presented as one quantity.
- **The step definition is circular.** `step_minor` is defined as a nice step near
  `(span_high − span_low) / 80`, while `span_high` and `span_low` are themselves defined
  by `ceil_to_step` / `floor_to_step` **of `step_minor`**. The worked check silently
  breaks the circle by using the raw un-stepped span (`1 211 000 / 80 = 15 142`), which is
  a third rule, unstated.

Consequence if it ships unfixed: two implementations both "following §7.2" produce
different slider bands, and neither reproduces the mockup. The section's own worked check
is what makes this catchable at zero cost — and it is the reason the master plan now
carries "a worked example is a test, not an illustration."

### 2 — `infeasible_at_or_below_minor` is used twice and defined nowhere

It appears at §7.2 (as the floor applied to `min_minor`) and in §8's payload
(`anchors.infeasible_at_or_below_minor: 0`). Repository-wide grep from the project folder
returns exactly those two lines. There is no definition, no derivation, and no test
expectation for it anywhere in the intention.

It is also load-bearing: §7.2 uses it to keep the band from containing a price that funds
nothing, which is the one guarantee the band makes.

### 3 — §12.6's status matrix contradicts §9.1 and miscounts the enum

`EconomicsStatusEnum` has **12** members (verified at
`app/beyo_manager/domain/item_economics/enums.py:15-27`), two of which are `OK` and
`INFEASIBLE`.

- §12.6 asks for "one row per non-`ok` value … **twelve values, twelve rows**". Non-`ok`
  is **eleven** values.
- §12.6 has every row assert that `model` / `anchors` / `domain` are **absent**. §9.1 says
  the opposite for `infeasible`: it is explicitly *not* a degraded state, and the model
  block stays populated because fixing infeasibility is what the user came to the screen
  to do.

So the criterion as written demands a test that asserts the wrong thing for `infeasible`,
and an implementer who satisfies it literally ships a screen that goes blank in the one
state it exists to repair.

## What the coordinator did NOT find, and says so

The two claims the intention's own §14 nominates as most worth attacking — M1's
`(n+1)/2` error bound (§3.2) and M2's monotonicity argument (§4.2) — **both held** under
the coordinator's check. The bound is an ordinary triangle inequality over per-term
rounding error, and `budget_published` is genuinely monotone non-decreasing for
`residual_percent_milli > 0`, so the bisection is safe.

That is worth recording on its own: **the intention's self-assessment points away from its
own weakest section.** The author was most careful where they were most worried, and M5 —
the section nobody flagged — is the one that does not survive its own worked example. The
inventory prompt is written to neutralise that anchor without revealing where it leads.
