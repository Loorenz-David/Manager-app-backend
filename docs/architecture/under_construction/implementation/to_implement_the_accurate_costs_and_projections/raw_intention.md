# Raw intention: accurate costs & projections

```
status: RAW — direction only. Not resolved, no owner decisions, no mechanism contracts.
role:   input to /intention-shaper (one track at a time)
date:   2026-08-16
source: design conversation 2026-08-12 → 2026-08-16
depends_on: item_cost_calculation v1 — CLOSED 2026-08-15 (all phases APPROVED); tracks below are unblocked
evidence:   research_findings.md (this folder) — a record, never edited
```

---

## 1. Objective

Item cost v1 answers **"what can this item afford?"** — top-down, from the expected
sale price. This body of work answers **"what will this item actually take?"** —
bottom-up, from the work itself. The goal is to hold both numbers at once:

```
what it can afford  ──┐
                      ├──►  feasibility, pricing, accountability
what it will take   ──┘
```

Everything below is in service of that comparison. The tracks are separable and are
listed in dependency order in §8.

---

## 2. What v1 establishes (and therefore what this must not re-litigate)

- The economic chain: expected sale price → allocations → budget → **÷ rate** →
  allowed worker-minutes → measured against trusted working seconds.
- One blended cost-per-worker-minute for the whole production cost group.
- Committed evaluations are immutable snapshots (`HC-1`) and self-reproducing (`HC-7`).
- Consumption is read-time and never stored; results are recompute-and-SET.
- The calculator monopoly (`P-F`): no service computes economics inline.
- No inferred zeros (`R-9` / `P-B`): absent input ⇒ named error or `null`, never `0`.
- Money is ADMIN/MANAGER only (`§11A.1`); worker surfaces carry minutes and percentages.

### The simplification v1 rests on — and why it is sound

A single blended rate encodes the assumption **"all minutes cost the same."** Under
that assumption the allowance is *distribution-independent*: it does not matter which
sections the minutes happen in, because any split costs the same. That is a real
mathematical property, not a compromise.

**The moment section rates differ, the allowance becomes distribution-dependent** —
and therefore requires ratios. This is why §7 is blocked on §5/§6 and not the reverse.

---

## 3. Principles established by this design work

These are prose here. The mechanism-inventory gate will need to turn each into a
contract.

- **P1 — The estimator is the primary object; the ratio is a derived view of it.**
  Issue arithmetic produces *absolute minutes*, which have units. A ratio is
  scale-free. Normalising an estimate into a ratio and multiplying it back by the
  allowance destroys the feasibility signal (see §4).
- **P2 — Decisions are frozen; measurements are recomputed.** Evaluations and
  allowances never move. Consumption and results converge freely. This is why
  `ItemCostResult` is recompute-and-SET while the evaluation beside it is immutable.
- **P3 — The measurement may move; the ruler may not.** Consumed cost must change
  *only* because the work changed (more minutes, or minutes in a different section) —
  never because configuration or assumptions changed.
- **P4 — Absence is not zero.** A section the item never entered is not a zero-minute
  sample. Inherited from `R-9`.
- **P5 — Identifiability before arithmetic.** A model that cannot separate two inputs
  must say so rather than emit a confident split (see §5.4).
- **P6 — Decline over guess.** Every estimate carries its source, sample size and
  spread, and a provider with insufficient or too-variable data **declines with a
  reason** instead of answering weakly. Same shape as v1's `first_failure`.
- **P7 — Snapshot iff a decision rests on it.** Display-only figures are recomputed
  freely. The moment a figure produces a number someone commits to, it must be
  snapshotted or `HC-7` breaks.

---

## 4. The central design decision: estimate first, ratio second

Do **not** model this as "a ratio system". Model it as an estimator whose output can
be viewed as a ratio.

```
expected_worker_minutes[section]        ← absolute, bottom-up, from issues + item type
ratio[section] = expected[s] / Σ expected   ← derived view, for display
allowed_share[section] = allowed × ratio[s] ← budget distribution
```

**Why this ordering matters.** Suppose the allowance is 175 minutes and the estimate
says 210. If the estimate is normalised into ratios and multiplied by the allowance,
every per-section number sums neatly back to 175 and **the system can never say the
item is unaffordable.** The 35-minute gap is the most valuable number in the design.

Three distinct comparisons fall out, and they must not be collapsed:

| Comparison | Question |
|---|---|
| `Σ expected` vs `allowed` | Is this item worth restoring at this price? |
| `actual[s]` vs `expected[s]` | Did this section perform as predicted? |
| `actual[s]` vs `allowed_share[s]` | Did this section overspend the budget? |

**Downstream payoff.** With `Σ expected` known, invert the v1 calculator to obtain the
**minimum expected sale price at which the item is worth restoring**. The calculator
is already a pure module with `rederive()`, so inversion is cheap.

---

## 5. The estimator

### 5.1 Sampling method (confirmed correct)

One sample = for one episode and one section, the **sum** of that task's steps in that
section. Multiple steps of the same section on one task (a rework pass) sum into one
sample. Source columns exist today — `research_findings.md` §1.

Rules:

- **Only closed episodes.** An in-flight task yields a truncated sample.
- **A skipped section is not a zero** (`P4`). Ten chairs where upholstery worked eight
  at ~50 min is an upholstery median of 50, not 40.
- Batch dilution is already applied upstream; samples are fair by construction.

### 5.2 Median, not mean — with spread as the quality gate

Workers forget to pause, producing long-tail outliers that wreck the mean.

```
samples  30, 32, 35, 33, 240      mean = 74      median = 33
```

The mean claims the section is 2.5× more expensive than it is, and every ratio built
on it inherits the error. **Median is the default, not a toggle.**

The *spread* is the decline signal (`P6`): `30, 31, 33, 35` is trustworthy;
`10, 30, 90, 200` has the same kind of median and means nothing. Wide spread at a
coarse grain is the system asking for the narrower grain (item type, issues).

### 5.3 Not all time is issue-driven

If `expected[s] = Σ issue times`, sections with few recorded issues collapse toward
zero and their ratio is systematically wrong — precisely the sections doing quiet
handling, inspection and transport work.

```
expected[s] = base[s, category, style]
            + Σ over issues in s: coefficient(issue_type, placement, style) × f(intensity)
```

The per-section, per-category **baseline is a first-class term**, not a correction.

### 5.4 ⚠️ The identifiability trap — do this query before designing anything

This is the most likely mechanism behind the previous implementation's failure
(`research_findings.md` §4).

**The problem.** To learn what a *loose joint* costs you observe section time on items
that had a loose joint. But issues co-occur:

| Chair | Issues | Section time |
|---|---|---|
| #1 | loose joint + scratched leg | 40 min |
| #2 | loose joint + scratched leg | 45 min |
| … | … | … |
| #50 | loose joint + scratched leg | 41 min |

Fifty consistent samples, and the coefficients are still **unknowable**: 10/31,
20/21 and 35/6 all fit equally well. More data does not help. Only more **variety**
helps — chairs with a loose joint and no scratched leg.

You never observe "this issue took 12 minutes". You observe "this section spent 40
minutes on an item carrying issues A, B and C". Coefficients must be *solved for*
across varied samples, not averaged directly.

**The query to run first (one day of SQL, before any design):** group recorded
`item_issues` by `(item_category, issue-type set)` and measure how often the same
issues appear together versus apart.

- Combinations vary ⇒ per-issue coefficients are solvable; the earlier failure was
  method, not data.
- Combinations always co-occur ⇒ coefficients are unidentifiable **permanently**;
  build combination-level estimates and stop there.

**Design consequence either way — start at the combination level:**

> "Chair, with {loose joint, scratched leg}, in Woodworking → 41 min (median of 50)"

That is a direct observation. Nothing to disentangle, nothing arbitrary, immediately
useful. Per-issue coefficients come later and only where the data separates them —
and the model must be able to answer **"I cannot separate these two"** (`P5`).

### 5.5 Progressive discovery and discovery drift

Issues are found *during* the work: section 1 records three, section 3 finds four
more. Two consequences.

**Expected time is a moving target, so comparisons need a timestamp.** Judging section
1's 30 minutes against a ratio derived from the final seven-issue set judges it
against knowledge it did not have. `item_issues.created_at` already supports
"expected, as known when this section worked" — the discipline is simply not to
compare across time.

**The growth is itself the metric.** Expected rising 90 → 150 over an episode measures
how much the upfront evaluation missed. Call it **discovery drift**. When the evaluator
role is introduced (inspection at intake), shrinking drift is the number that proves it
paid for itself — and because `item_issues.created_at` already exists, the baseline is
computable retroactively.

### 5.6 Snapshot discipline for coefficients

Re-adopt the deleted system's doctrine verbatim (`research_findings.md` §4): when a
coefficient is applied to an issue it is **snapshotted onto the issue row** with a
version stamp. Otherwise tuning the model in March silently rewrites what January's
items were expected to take, and every historical variance report becomes fiction.

---

## 6. The ratio resolver

### 6.1 One coefficient table at several specificities — not three subsystems

Manual, average and narrow are not three algorithms. They are one estimator at
different grains, behind one resolver that walks from most specific to least and
**declares which rung answered**.

```
resolve_section_expectation(item, task, sections) → {
    source:      which rung answered
    per_section: {section_id: minutes} | None
    basis:       sample_size, spread, window
    declined:    [(rung, reason), ...]
}
```

Ladder, first match wins — specificity, not source type, decides:

1. per-item explicit override (a human spoke about *this* item)
2. narrow statistical — (category, style, issue set, intensities)
3. category/style average
4. section average across all items
5. configured default ratios (manual, group level)
6. equal split — **illustrative only, always labelled, never a commitment**

Same idiom as v1's `§7A.5` ordered classifier and `§11A.4` status vocabulary. Build
the resolver and its provenance payload with only rungs 5 and 6 populated; rungs 2–4
then slot in without a rewrite. This is the "flexible and scalable piece" the original
raw draft asked for.

### 6.2 Two meanings of "snapshot" — keep them apart

| | What it is | Verdict |
|---|---|---|
| **Materialized current ratios** | *"Sanding: 30%, 42 samples, computed 2026-08-16."* Cached, recomputed on a schedule, freely overwritten. | ✅ build this |
| **Ratios frozen onto an evaluation** | Attached to a committed decision, never changes. | ⏸ only when a decision rests on them (`P7`) |

**Snapshotting a ratio does not freeze the estimator.** The model keeps learning and
keeps producing today's best answer for new items; the snapshot is a receipt attached
to one evaluation. It is an exchange rate: the market keeps moving, the invoice
records the rate applied on the day.

**And the snapshot is what lets the model learn.** `predicted 60/40` vs
`actual 45/55` is only computable if what was predicted was kept. Without it the
estimator can never be scored against outcomes.

### 6.3 Vocabulary

Do **not** call the section split a "projection" — that word already denotes
`kind = projection` what-if evaluations in this domain. Use **split** or
**distribution**. Same discipline as `P-C`.

---

## 7. Per-section cost rates

### 7.1 ⚠️ Weighted average, never a sum

Summing section rates is wrong and expensive.

```
budget 700 kr; Woodworking 6 kr/min, Sanding 2 kr/min

WRONG   rate = 6 + 2 = 8      → allowed 87.5 min
        at a real 70/30 split that consumes only 420 kr
        → 280 kr of budget unused; profitable work rejected as infeasible

RIGHT   rate = (0.70 × 6) + (0.30 × 2) = 4.80   → allowed 145.83 min
        woodworking 102.08 × 6 = 612.50
        sanding      43.75 × 2 =  87.50
                                 ───────
                                  700.00  ✓ exactly the budget
```

Summing implies every section works the item simultaneously, every minute. They do
not — the item moves through them sequentially.

**The weights are the ratios from §6.** Per-section rates are therefore blocked on the
ratio work, or on consciously accepting equal weights as an approximation (which is
itself a ratio, just a naive one).

### 7.2 Structure: one version, section child rows

```
ProductionCostGroup                      ← survives: version header + selection scope
  └── ProductionCostBasisVersion         ← one open, effective-dated (INV-B1)
        └── SectionRate × N              ← per-section facts + derived rate
```

**Do not give each section its own chain.** Independent chains put Woodworking on v3
while Sanding is on v7, and "what was the cost structure on March 5th" needs N chains
resolved and hoped coherent. One version = one coherent answer, and `INV-B1` still
guarantees exactly one open.

**Do not replace the group.** Per-section rates are a refinement *inside* it. The group
remains the version header, the selection scope and the container. Group totals stay
derivable as `Σ` of the parts, so the blended rate keeps working and nothing migrates.

This is the third instance of a pattern already built twice
(`CostModelVersion` + `CostModelTerm`): version header with immutable child rows,
replaced as a set. Note v1's rule — `effective_to` is written only by chain
construction and `effective_from` must be ≤ today; **versions are never edited**,
only superseded.

### 7.3 Snapshot every section rate, not just the route

**The wandering-section problem.** An evaluation snapshots rates for the three sections
on the planned route. On day three a step is added in a fourth section with no
snapshotted rate. Pricing those minutes at the *live* rate breaks `HC-7` — the closed
episode would reprice itself whenever that section's rate changed.

**Fix:** snapshot **all** the group's section rates at commit. A handful of extra rows
per evaluation; the reassignment case then needs no special handling at all.

Mechanically this is a child table —
`ItemCostEvaluationRateComponent(evaluation_id, working_section_id, ratio, rate_minor)`
— plus a `CALCULATION_VERSION` bump. Purely additive: the existing scalar column keeps
holding the effective blended rate, so nothing downstream changes, and old evaluations
are protected by the version check already in `rederive()`.

### 7.4 Compensation gives worker cost, not section cost

The v1 seam (`§10.3`) populates `fixed_monthly_cost_minor` and `monthly_paid_hours`.
But compensation yields **per-worker** cost, and §2.4 establishes that memberships are
many-to-many and time-varying — "a worker belongs to one section" is not derivable.
That is exactly why v1 uses an aggregate.

**An allocation rule is required, and it is a decision, not a consequence.** The
natural candidate — split each worker's cost across sections by their observed time
distribution (`step_state_records.credited_user_id` + the step's section) — is
derivable from existing data, but has edge cases to settle (a month where someone never
touched a section; workers with no step time at all).

### 7.5 🚨 The tripwire

**The day ratios enter the weighted rate is the day they must be snapshotted onto the
evaluation.** Before that they are a display cache; after that they produce the
allowance, and without the freeze `rederive()` cannot reproduce it and `HC-7` is gone.
Easy to walk straight past — pin it as an explicit gate on the §7 track.

---

## 8. Roadmap

```
per-section actuals  ──►  ratio cache  ──►  per-section rates
       │                                          ▲
       │                                          │
       └──►  issue-combination estimates          │
                        │                         │
                   item styling                   │
                        │                         │
                        └──►  expected vs allowed │
                                    │             │
                                    └──►  price inversion

worker compensation  ─────────────────────────────┘  (independent track)
```

| # | Track | Size | Why here |
|---|---|---|---|
| 1 | **Per-section actuals** — per-item progress line + period view | small | No new schema; history already queryable; standalone manager value ("where did the time go"); the validation set for everything later. Check `working_section_daily_work_stats` before building any table. |
| 2 | **Identifiability query** (§5.4) | ~1 day | Free information that changes what track 6 is. Run it now, not when you reach track 6. |
| 3 | **Ratio cache + resolver** (§6) | medium | Display-only, no snapshots. Establishes the provenance/decline discipline while nothing rests on it. |
| 4 | **Worker compensation** | large | Already shaped and queued. Replaces the manual fixed-cost input. Independent of 1–3. |
| 5 | **Per-section rates** (§7) | medium | Needs the allocation rule from 4 **and** the ratios from 3. **Tripwire §7.5 fires here.** Accuracy refinement — worth less than track 6. |
| 6 | **Issue arithmetic** (§5) | large | Combination-level first; per-issue only where track 2 said it is possible. **The highest-value track** — tracks 1–3 are infrastructure for it. |
| 7 | **Expected vs allowed → price inversion** (§4) | medium | The payoff. Also where the evaluator role and discovery drift land. |

**Recommended immediate next (v1 closed 2026-08-15):** ship track 1 as a small piece, run track 2 in
parallel, and let track 4 proceed as planned. None of the three compete for the same
design attention, and you emerge knowing whether the estimator is buildable *before*
committing to shape it.

---

## 9. Small debts (do not lose)

- **Rework accountability.** `task_steps` records *who* added a step and *when*
  (`created_by_id`, `created_at`) but nothing records **why**. No rework flag, no
  reason, no link to the handing-off section. Cheap to add, and it is what lets the
  time-attribution view say *"+40 min, Woodworking, rework from Sanding"* instead of
  leaving managers to infer it from timestamps.
- **Reassignment is a measurement event, not a decision event.** It must never trigger
  a re-commit: a WORKER can add steps (`research_findings.md` §6), and re-baselining
  on route change makes overruns unmeasurable — if the target moves to match the work,
  the work can never be measured against the target. Surface drift as a flag (the
  `item_binding` mismatch pattern already exists in v1) and let a manager re-commit
  deliberately.
- **When re-commit *is* right:** sale price changed, cost model changed and should
  apply here, wrong item bound, or genuine scope change. Never: rework, handback,
  slowness.
- **Under per-section pricing, money becomes the honest yardstick.** "Allowed minutes"
  stops being stable once minutes cost different amounts in different sections. Compare
  budget vs consumed in currency, and decompose variance into **volume** (worked
  longer) and **mix** (worked in pricier sections) — standard cost accounting, and only
  computable because the baseline holds still.
- **README drift on the deleted timing system** (`research_findings.md` §4):
  `issue_types/README.md:37-51` and `routers/README.md` still document
  `base_time_seconds` / `time_multiplier`. v1 phase 9 fixes `items/README.md` only.
- **`ProductionCostGroupSection` must survive review.** Built in v1, deliberately read
  by nothing, exists for this work (R-8).

---

## 10. Open questions for the shaping session

1. Are per-section allowances ever **committed to** (a target a section is judged
   against), or permanently display-only? Determines whether §6.2's snapshot is ever
   required, and gates track 5.
2. What is the sample-size and spread threshold at which a rung declines? Needs to be a
   number, not a sentiment.
3. What is the recency window for samples — does a chair from 2024 still inform
   today's ratio?
4. The compensation → section allocation rule (§7.4): observed-time split, declared
   membership, or manager-configured?
5. Does the estimator produce a point estimate or a range? A range makes "can we afford
   it" a probability rather than a yes/no — richer, but every consumer must handle it.
6. Does an evaluator role (inspection at intake) change the item lifecycle, or is it
   just a new surface on the existing one?
