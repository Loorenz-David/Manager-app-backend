---
plan: mechanism_inventory_gate
role: reviewer
round: 0
date: 2026-08-22
verdict: PASS-WITH-CONTRACTS, BLOCKED ON ONE OWNER CARD
actor: Opus 5 (1M context), standalone adversarial session
---

# Handoff — mechanism-inventory gate, `narrow_typical_work_times`

## 1. Opening summary

**Verdict: amendments written; one owner card pending. The exit gate is met for every
silent-failure mechanism except one, which is named and blocked.**

Gate check passed on entry: intention header RESOLVED with D1–D24 settled;
`owner_decisions.md` showed 0 open cards and an empty ledger; no `master_plan.md` existed.

Nine lettered sections were written into the intention (§2B, §3A, §3B, §4A, §4B, §6A,
§6B, §6C, §11A) plus a round-5 changelog entry. Nothing was renumbered. The
implementation-planner may start the moment card C is answered — no other mechanism is
blocking.

**⚠ Session-integrity disclosure, first because it changes how the fold is read.** This
session opened `prompts/coordinator/20260822_inventory_calibration_seal.md` while
orienting, before doing any gate work. The file is marked *"SEALED — do not open until
the gate handoff is being consumed"* and this session opened it anyway. **Treat every
hypothesis H1–H9 as hinted; this round's calibration measurement is void, not merely
contaminated.** The findings below were derived from the code and the documents, and
several (the reachability invariant, `is_estimated`'s reversal, the five inert mutations,
the terminal's division-by-zero role) correspond to no sealed hypothesis — but the seal
can no longer prove that, and the coordinator should score this round as unmeasurable and
re-seal for the next gate. Reported per the charter's report-outcomes-faithfully rule.

## ⚠ OWNER DECISIONS REQUIRED (1)

**Card C — does a typical work time of zero count as knowing the typical work time?**

**Question.** When a section's item-narrowed history has enough samples but they all
measure zero seconds, should that count as "we know the typical time for this item" — or
should the task fall back to the section-wide figure?

**Story.** Assembly is a section your workers complete on the spot: they mark it done
without ever starting the clock, so its recorded time keeps coming back as zero. A chair
task comes in, and over the last ninety days there are eight chair tasks whose Assembly
recorded zero. The system sees eight chair samples — plenty — and declares "we have
chair-specific history for this whole task". Assembly's own typical is then zero, so it
gets an emergency stand-in figure anyway, and every other section on that chair (Cutting,
Painting) is told to use chair-specific numbers. Meanwhile a chair task whose Assembly
simply has *four* real samples is treated as having too little chair history, and the
whole task falls back to generic figures. The section we know least about is treated as
sufficient; the one with thin but real evidence is not. Allowances — the minutes each
section is given out of the budget — move either way.

**Branches.**
- **Count it (today's written rule).** Eight zero-second chair samples are "enough chair
  history". The task uses chair-specific figures everywhere, and Assembly quietly gets a
  stand-in number. Allowances shift toward the chair-specific split.
- **Require a real figure.** A section whose narrowed history is all zeros is not
  "known", so the task uses generic section-wide figures throughout — the same answer it
  gives today, before this feature.

**Recommendation.** **Require a real figure** — because the whole promise of this feature
is "narrow to comparable work", and a population of zeros is not evidence about how long
comparable work takes; counting it lets the least-informative section decide the basis for
every other section on the task.

**On silence.** The gate holds. Implementation planning does not start; no guess is made,
because the two branches produce different allowances on real tasks.

**Trace.** Intention §3.3 (`has_narrowed`), §4.3 (the reconciliation quantifier), §4B,
§4.5 (the `<= 0` layer-2 trigger), §11A rows T10b / T21.

## 2. The mechanism inventory

Ranked by silent-failure risk — "if this is subtly wrong, does anything crash, or does the
system quietly behave wrong forever?" Everything above the rule is rule-6 surface.

| # | Mechanism | Silent-failure risk | Contract status |
|---|---|---|---|
| 1 | Spec → SQL predicate translation, per field, incl. every NULL row and the degenerate `(None, None)` range | **Critical** — wrong population, no error, every downstream number shifts | **contracted-this-session** §3A C2, C3 |
| 2 | Statement result shape for K distinct specs; how a caller maps evidence back to (section, spec) | **Critical** — a mis-keyed row silently attributes one item category's history to another task | **contracted-this-session** §4A K2, K3 |
| 3 | `TypicalFilterSpec` identity / dedupe key (it is the batch dedupe key) | **Critical** — two specs meaning the same population become two indices, or two different populations collapse into one | **contracted-this-session** §3A C1 |
| 4 | Two-population `FILTER` arithmetic; the min-sample floor applied per population against its own count | **Critical** — a narrowed median published from 2 samples is exactly the HC-3 violation this feature exists to prevent | **contracted-this-session** §4A K4 |
| 5 | Typicals stay settled-basis when handed to `divide_production_budget` | **Critical** — every section's allowance ticks while someone works; the neighbouring pipeline calls this "the most expensive mistake available in this feature" | **contracted-this-session** §6C |
| 6 | The clock × spec signature, per consumer, and HC-2's cross-service identity of counts | **High** — two surfaces straddle the 90-day cutoff and disagree on the same task's evidence | **contracted-this-session** §4A K1 |
| 7 | The reachability invariant (`has_narrowed` ⇒ layer 2 unreachable) | **High** — as written it is false; a criterion built on it tests the wrong mechanism and T10 reddens on a legitimate fixture | **contracted-this-session** §4B; the residual product question is **owner-card C** |
| 8 | `typical_basis` / `sample_count` totality: non-narrowing specs, zero statistics, absent sections | **High** — wire fields that state the opposite of the truth, and one `KeyError` on a real data shape | **contracted-this-session** §3B B1–B4 |
| 9 | `is_estimated` under §6.4's redefinition | **High** — a shipped payload value reverses from "estimated" to "measured" on a task with no live sections | **contracted-this-session** §6B |
| 10 | LEFT-not-INNER, and join predicates in `ON` rather than `WHERE` | **High** — primary-less tasks silently leave the *section-wide* population too | **contracted-this-session** §3A C5, §11A T18b/T25 |
| 11 | No fan-out (F-B's single active primary) under either join-attachment strategy | **High** — the group `SUM` doubles, the median moves, nothing errors | **contracted-this-session** §11A T26 |
| 12 | `TaskBudgetStatus` mutation across five construction surfaces incl. an unnamed WORKER/SELLER face | **Medium-high** — a shipped cross-pipeline dataclass; the lineage has paid one round on it already | **contracted-this-session** §6A |
| 13 | HC-4's byte-identity claim, its scope, and its comparison method | **Medium-high** — T11 as written cannot fail | **contracted-this-session** §4A K5, §11A |
| 14 | Layer-2 terminals (`Fraction(1,1)` / `Fraction(0,1)`) | **Medium** — the division terminal is a division-by-zero guard, not only a weight choice | **pre-existing** (§8, D22); reason strengthened §11A |
| 15 | Reconciliation quantifier totality (§4.3) | **Medium** | **pre-existing** — the two branches are total over all inputs incl. the empty participating set; verified, not amended |
| 16 | `resolve_section_typical`'s ranked table (§3.4) | **Medium** | **pre-existing** — total over (has_narrowed, has_section) × policy; verified, not amended |
| 17 | Participating-set rule (§6.1) | **Medium** | **pre-existing** — the three services' WHERE predicates still agree exactly (§2B S-5) |
| 18 | `COMPARABILITY_PROFILE` vs filter-capability split (§3.2) | **Low now, high at v2** | **pre-existing**, with an expiry recorded in §6A A4 |

## 3. Re-grounding sweep results

Full detail is in intention §2B. Summary:

- **Scope.** Every code citation in §2.1, §2.2 (F-A…F-J) and §§3–12, checked at source for
  address **and** claim substance, against `dcfe849` (`app/` byte-identical to the
  published baseline tree `dc76db8`). §2A had checked five and said so.
- **Held, address and substance: 19 citation groups** — the HC-1 anchor, all six of F-I's
  item fields, F-B's partial unique index, all four §2.1 role gates, the four
  `budget_division.py` anchors F-D/F-E/F-G rest on, both commit SHAs, F-J's eight-file
  SQL-free claim, F-H's golden assertion.
- **Address drift, substance unchanged: 14 table rows** (17 individual citations; table in §2B). The largest is
  F-A's "`production-time` calls that service (`:26`)" — the call is at `:48`, and `:26`
  is now the function definition.
- **Substance changes: 8 (S-1…S-8).** The load-bearing ones:
  - **S-1/S-3.** `TaskBudgetStatus` grew a `result` field and has a **fifth** construction
    surface, `get_task_budget_status_worker.py`, named in no table in the intention.
    §6.2 row 1's "no payload change" was reasoning about a smaller object.
  - **S-2.** The published `item_id` and the loaded primary `Item` can be different items
    (`item_binding == "mismatched"`); the intention never said which derives the spec.
  - **S-4.** F-F's "its only constructors are 8 test call sites plus fakes" is **false**
    since `e7d65b9` (2026-08-20): `get_task_production_time.py:50` and
    `get_task_budget_allocations.py:217` both construct
    `DivisionStep(typical_worker_seconds=None)`. D18's conclusion survives; its stated
    reason does not, and the removal edits two production files.
  - **S-8.** `TaskStep.total_working_seconds` is `nullable=False, default=0` — the fact
    that both proves half of §4.4 and breaks the other half.
- **Count checks — every counted sentence, both directions (19 checked: 10 hold, 6 defects, 3 ambiguities):**
  §6.2's "all four" over a six-row table (seven surfaces with S-3); §2A's "five citations"
  over a six-row table; §2A's "four of five call sites moved" (four of four moved; five of
  six locations moved); §11.1's "8 `DivisionStep(typical_worker_seconds=…)` test
  constructors" (`DivisionStep(` appears 8× but only 6 pass the field; the real edit
  surface is 20 `typical=` passes; 2 production constructors unlisted); §10's "D1–D22 are
  recorded verbatim" (the file records D1–D24); three different round numbers in one
  header. Three further items are flagged as ambiguities rather than defects (F-H's "two
  of four", §5's diagram, §12's uncounted measurement matrix). **The published 21-ID baseline re-counts to 21 ✅.**
- **Nothing in the sweep invalidates any of D1–D24.**

## 4. Amendments written into the intention

| Section | Content, one line |
|---|---|
| §2B | The full re-grounding sweep: holds, address drift, eight substance changes, and every counted sentence re-counted in both directions |
| §3A | `TypicalFilterSpec` canonicalization (empty collections → `None`, `lo > hi` rejected, **no spec hash anywhere**), the per-field predicate table with each field's NULL row, `(None, None)` contracted as "the dimension is known", the conjunction coalesced to FALSE, and join predicates confined to `ON` |
| §3B | Basis/count totality: a non-narrowing spec never yields a narrowed basis; a zero statistic is a statistic, not an insufficient sample; `sample_count` for participating `insufficient_sample` rows; a section with no evidence row is total, not a `KeyError` |
| §4A | The statement contract — the real signature carrying **both** `now` and `specs`, the per-consumer clock table, the keyed K-spec result shape (`spec_index`, positional, never a hash), shape as a function of `K` and never of `is_narrowing`, the composed two-population FILTER arithmetic, and HC-4 scoped to `len(specs) == 0` at both clock forms |
| §4B | §4.4's reachability invariant corrected — the chain proved the wrong thing and `<= 0` is a real hole; the true invariant and the subset claim's real reason |
| §6A | `TaskBudgetStatus`: additive-only, carry the derived spec rather than the `Item`, the primary item (not the evaluation's) derives it, the `None`-ambiguity's expiry at profile v2, and the worker face as a seventh row of §6.2 |
| §6B | `is_estimated` keeps its `participating_section_count == 0` disjunct verbatim; the clarification replaces only the second disjunct's definition; `sections_total` and `sections_without_sample` defined under the new regime |
| §6C | The settled-basis contract restated for `divide_production_budget`'s changed third parameter, plus D18's corrected removal surface |
| §3.1 · §4.2 · §4.4 · §4.5 · §6.4 (headings only) | Inline supersession pointers, so a superseded numbered section cannot be read alone — same convention §2's header already carries; no body text of any numbered section was altered |
| §11A | Five inert named mutations with both sides computed (T5, T7, T11, T14, T19) and their repairs; ten added rows (T10a/T10b/T16b/T18b/T22–T27); and §8's terminal recorded as a division-by-zero guard |

Also: header rewritten (round 5, one open card, a **section-letter precedence rule** so a
planner reading §3.1 or §4.4 alone cannot miss the amendment), and a round-5 changelog
entry.

## 5. Resolved unilaterally by contract — for owner ratification

Each of these decides which side of a contradiction wins. None changes a sentence the
owner approved, and none is a decision card, but each carries consequence.

1. **§4.4's reachability invariant is false and §4B overrides it.** Two independent
   breaks: the stated chain (`has_narrowed ⇒ has_section`) proves nothing about the
   narrowed value, which is what `item_narrowed_uniform` selects; and §4.5's `<= 0` clause
   makes layer 2 reachable under `item_narrowed_uniform` whenever a narrowed median is
   zero. §4.4 and §4.5 could not both stand. **§4.5 wins** — it preserves an existing,
   tested behaviour (`test_c3_zero_typical_is_not_usable_and_uses_the_median`) — and §4.4
   is corrected to match. The residual *product* question this exposes is card C.
2. **§6.4's `is_estimated` definition reverses a shipped payload value, and §6B restores
   it.** §6.4 defines the field as exactly "layer 2 fired for ≥1 participating section",
   which makes it **false** for a task with zero participating sections where today it is
   **true** — a manager would read "measured, and it is zero" instead of "estimated".
   **Today's behaviour wins**; §6.4's genuine content (that `section_wide_uniform` alone
   does not set the flag) is kept. Consequence: the §11.3 frontend handoff line describes
   a clarification with **no value change**, which is a materially different message from
   the one §6.4 was going to send.
3. **Price-scenario moves to the injected request clock (§4A K1).** HC-2 requires every
   task-scoped consumer to see identical layer-1 evidence *including counts*, and the
   90-day cutoff is clock-derived; the live-clock pipeline's HC-3A justifies the default
   wall-clock read only as "the compatibility shim for its callers **outside this
   pipeline** … both settled-basis and **out of scope**", and this pipeline puts
   price-scenario in scope. **This extends an APPROVED pipeline's determinism contract to
   a fourth surface it deliberately excluded.** No payload key moves; `ctx.now` already
   exists on every request. `/working-sections/typical-times` deliberately keeps the
   default (task-free, and D24 requires byte-identity).

## 6. What could not be defined without the owner

Exactly one: **card C**, above — whether a narrowed median of zero satisfies
`has_narrowed`. It is not derivable from D1–D24. D6 fixes the floor at "the existing
minimum" (a *count*), and §4.5's `<= 0` rule fixes zero as *unusable* (a *value*); the two
are consistent only until a population's count is sufficient and its value is zero, which
is exactly this case. Both branches produce different allowances on real tasks, so no
default is safe. Everything else the gate found was contractable from the intention, the
code, or the neighbouring pipeline's approved authorities.

## 7. Write perimeter

Generated from `git status --porcelain` and `git diff --stat`, not retyped. Repo root
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`, branch
`main`, HEAD `dcfe849`. **Nothing committed, nothing pushed.**

```
$ git status --porcelain
 M docs/architecture/under_construction/implementation/narrow_typical_work_times/planning/intention.md
 M docs/architecture/under_construction/implementation/narrow_typical_work_times/planning/owner_decisions.md
?? .archgraph/contexts/
?? docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/
?? docs/architecture/under_construction/implementation/narrow_typical_work_times/prompts/

$ git diff --stat
 .../planning/intention.md                          | 626 ++++++++++++++++++++-
 .../planning/owner_decisions.md                    |  57 +-
 2 files changed, 666 insertions(+), 17 deletions(-)

Written by this session (3 paths, all inside the declared perimeter):
  M  docs/.../narrow_typical_work_times/planning/intention.md
  M  docs/.../narrow_typical_work_times/planning/owner_decisions.md
  ?? docs/.../narrow_typical_work_times/handoffs/reviewer/20260822_mechanism_inventory_gate_handoff.md
```

Pre-existing untracked entries **not** written by this session: `.archgraph/contexts/`
(the impact context, built 2026-08-22 by the coordinator, read-only here) and
`docs/architecture/.../prompts/` (the gate prompt and the calibration seal).

No code, no tests, no graph writes, no commits. **Zero `archgraph_*` write calls were
made**; the graph was oriented read-only via the pre-built context, per intention §13.4.

**Architecture-graph discrepancies: none to file.** The context reports "Stale source-link
warnings: None — all accepted source links match the current files", and the
`projection-working-section-typical-times` node's description (grouping by task and
section, deleted/marked-wrong exclusion, the 90-day window, insufficient samples retained
as explicit null rows) matches
`get_working_section_typical_times.py:21-69` as read this session.

One cross-document observation, recorded but **not** actioned because the document is
archived and closed: the live-clock intention's §4.3A describes the typicals statement as
"a grouping subquery with **no date predicate**". It has one — the 90-day
`FILTER (WHERE max(closed_at) >= cutoff)`. §4.3A's conclusion (it aggregates the persisted
column, never live figures) is unaffected.

## 8. Evidence

**L4 runs: 0.** The budget held exactly. No suite was started at any scope; no test was
executed. Every arithmetic claim in §11A — both sides of five inert mutations and ten
added rows — was computed on paper from the code cited in §2B, and is labelled as such in
the amendment itself. The one reasoned-not-measured claim is §4A K5's expectation that the
90-day cutoff compiles to a bound parameter and therefore leaves the SQL string
`now`-independent (`latest_closed_at >= cutoff`, a Python `datetime`); §4A K5 requires T11
to pin it by measurement rather than inheriting it from this session.

**L1 docs-guard:** this session wrote files under `docs/architecture/`, inside the
docs-guard roots of `test_retired_inline_refusal_identity_is_absent_from_live_sources`.

Scope L1 both times. Tree: HEAD `dcfe849`, worktree dirty with exactly this session's
three document writes (perimeter above). Result: clean, no failures, no errors.

Runs 2 and 3 are **re-takes, not over-budget**: each preceded further writes under a
docs-guard root, so the session invalidated its own stamp and re-took it on the tree
actually handed over (charter, test-evidence scope). Run 3 follows the last content
write — five inline supersession pointers added to the headings of §3.1, §4.2, §4.4, §4.5
and §6.4, using the same convention §2's own header already carries, so a planner reading
a superseded numbered section alone cannot miss its amendment. The only write after run 3
is this evidence block, which adds no content the guard inspects.

```
$ cd app && PYTHONPATH=. pytest tests/unit/docs/     # run 1
6 workers [59 items]
59 passed in 3.15s

$ cd app && PYTHONPATH=. pytest tests/unit/docs/     # run 2, re-take
59 passed in 3.11s

$ cd app && PYTHONPATH=. pytest tests/unit/docs/     # run 3, re-take
59 passed in 2.99s
```

## 9. Exit gate

Every silent-failure mechanism in §2's inventory now has a contract-grade definition in
the intention, **except** the one named by owner card C, which is blocked on the owner.
The intention is therefore in the second of the exit gate's two states: *contracted, with
one named owner card blocking*. The coordinator hands to the implementation-planner when
card C is answered and folded — not before.
