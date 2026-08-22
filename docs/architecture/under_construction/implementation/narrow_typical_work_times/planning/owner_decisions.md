# Owner decisions — narrow_typical_work_times

Verbatim register. Cards are relayed exactly as authored; answers are recorded with
date and the owner's own words where they carry nuance.

---

## Settled during intention shaping (owner conversation, 2026-08-19/20)

The shaping ran as three architecture-projection passes, each owner-corrected. The
decisions below are numbered in the order they became final, not the order first
discussed.

**D1 — one canonical statement.** `typical_times_statement` remains the single
definition of "typical"; no fork, ever. Owner: *"typical_times_statement remains the
single canonical definition of 'typical'. We should not fork the typical-time
calculation into another implementation."*

**D2 — filtering, not dimensioning.** Item-aware narrowing filters the population;
the external result stays one resolved typical per working section. Grouping by
(section, item_dimension) is rejected as the external contract (it may exist only as
an invisible internal execution strategy — see D21).

**D3 — narrowing happens inside the statement.** Callers provide the narrowing
intention (a spec); they never construct or append item joins. One translation
boundary in the query layer.

**D4 — one frozen filter-spec object.** No per-property kwargs. `TypicalFilterSpec`
is frozen and hashable; adding a narrowing capability is one field plus one
predicate-translation entry.

**D5 — both populations in one pass.** Section-wide and narrowed aggregates come
from the same scan via aggregate FILTER predicates, so fallback never costs a second
query and diagnostics are always available. The query gathers facts; the domain
decides what they mean (owner, pass 3: *"I want the query to gather facts and the
domain layer to decide what they mean"* — confirmed).

**D6 — the sample ladder at the existing floor.** narrowed ≥ 5 → narrowed;
else section-wide ≥ 5 → section-wide (where policy permits); else insufficient.
Owner: *"statistical sample floor: existing minimum."*

**D7 — provenance is mandatory.** A consumer must distinguish an item-narrowed
value, a section-wide fallback, and an insufficient sample without
reverse-engineering the query.

**D8 — PRIMARY item only.** Narrowing is defined against the task's active PRIMARY
item; the `uix_task_items_primary_active` no-fan-out guarantee is a design boundary.
*"do not generalize this to secondary/non-primary items as part of this design."*

**D9 — all four consumers adopt now; same semantics, not same HTTP parameters.**
Owner correction to the first projection's display-only V1: *"The item narrowing is
not intended to be an optional informational capability… It is intended to become
part of the canonical typical-time semantics used by every service that currently
consumes typical_times_statement."* Task-scoped endpoints derive the spec
automatically from the active PRIMARY item; *"The client should not be able to
arbitrarily ask a chair task to use a table filter."* Task routes expose no filter
parameters.

**D10 — the goldens are part of the refactor.** *"The golden tests are valuable
regression tests, but if they encode the old intended contract and the contract is
deliberately changing, they are part of the refactor and should be updated
deliberately."* Folded with the keys-only regeneration criterion (intention §11.2):
a diff that changes any numeric value is a gate failure, not a regeneration.

**D11 — comparability profile = `primary_item_category_v1`.** Category-only for
task economics in V1; dimensions/upholstery/designer remain spec *capabilities* for
explicit analytics but not automatic economics policy. *"TypicalFilterSpec =
everything the typical engine is capable of narrowing by. COMPARABILITY_PROFILE =
which of those properties task economics automatically considers… adding a column to
Item must not silently change economics."* Expansion is deliberate and versioned.

**D12 — uniform basis per task (`uniform_basis_v1`).** All participating sections
narrowed-sufficient → narrowed for all; otherwise section-wide for all. Raw mixed
ratios rejected (scale distortion demonstrated); pace-factor/scale-corrected
fallback rejected for V1: *"That would introduce a new predictive assumption… We do
not currently have evidence that this relationship is stable across sections."*
The versioned `reconciliation_method` is the return path if data later validates
one.

**D13 — preserve evidence vs selection.** Layer-1 statistical evidence (both
populations, both counts) is retained and published even when reconciliation
overrides it. Two domain objects (`SectionTypicalEvidence`, `SelectedTypical` /
`TaskTypicalSelection`); no field may ambiguously mean both "best available for this
section" and "selected for this task."

**D14 — the cross-service invariant, including layer 2.** Identical layer-1
evidence and layer-1.5 selected typicals across all task-scoped consumers,
including identical nulls; consumer-specific layer-2 terminals may differ only when
the selected typical is genuinely absent, never appear under `typical_worker_seconds`
or a basis field, and each payload makes the terminal's firing visible. *"The user
should not believe a terminal fallback is itself a statistically observed typical."*

**D15 — resolution policy is orthogonal to the filter.** `TypicalResolutionPolicy`
(`BROADEN_TO_SECTION` | `ANSWER_AS_ASKED`) is an argument of resolution, not a
property of the spec. Statistical population fallback and terminal business fallback
are type-separated so they cannot be confused — no boolean anywhere. *"A narrowed
analytics query must never silently answer with a broader section-wide statistic
unless the caller explicitly requested a fallback policy that permits it."*

**D16 — excluded sections resolve independently (option B).** Owner, 2026-08-20:
*"Excluded sections: B — resolve independently; never influence task
reconciliation."* Grounded in the code trace showing excluded-section typicals are
display-only everywhere. Recorded consequence: an excluded row's `typical_basis` may
differ from the task's uniform basis in either direction; that is correct behaviour,
not a bug.

**D17 — strict analytics diagnostics: counts only.** *"Do not expose the unused
broader typical seconds."* `section_sample_count` tells the analyst broader evidence
exists; the broader median is obtainable by asking the unfiltered question.

**D18 — remove `DivisionStep.typical_worker_seconds`.** *"Historical allocation
reproducibility remains explicitly out of scope for this refactor."* Backed by the
inspection proof: no persistence anywhere, dead in production (ORM steps lack the
attribute), test-input convenience since origin commit `0b85701`. Future audit
need, if it arises, is a persistence feature (snapshot the selection at task close),
not this refactor.

**D19 — statistics V1 locked to `ANSWER_AS_ASKED`.** *"No resolution-policy
override in the route."* The route itself is deferred; its contract is pre-locked
(intention §7.5) and the policy branch ships now with unit coverage.

**D20 — `ALLOCATION_METHOD` versions to `static_proportional_section_v2`**, with
the owner's precision requirement: every task is evaluated under the new rule;
allowances are *eligible* to change where narrowing changes relative weights; many
tasks remain numerically identical; *"The contract changes even where an individual
numeric result does not."*

**D21 — conditional acceptance on measured query cost.** *"I do want the intention
to say that the plan is accepted conditionally on measuring the actual query
plan/cost."* GROUPING SETS (and any internal strategy) stays behind the query
interface, never in the domain contract; measurement matrix in intention §12.

**D22 — two distinct layer-2 terminals.** Division `terminal = 1` (weight-neutral),
price-scenario `terminal = 0` (contribution-neutral); shared median implementation,
deliberately unmerged semantics. *"Do not merge those semantics merely because
their median-search implementation can be shared."*

**D23 — serial sequencing, live-clock first (card B).** Owner, 2026-08-20:
*"that is correct i will implement this after the live clock has finished."*
This pipeline's implementation starts only after the live-clock phases touching the
shared files (production-time, budget-allocations, budget-status, the golden test)
are APPROVED; goldens regenerate once, on the post-live-clock baseline.
Mechanism-inventory on this intention may run meanwhile (documents only).

**D24 — `/working-sections/typical-times` gains no narrowing parameters in V1
(card A).** Owner, 2026-08-20, after a plain-language walkthrough of the card:
*"'no' is the correct answer."* The endpoint stays byte-identical — no query
params, no response change, nothing in the frontend handoff for it beyond the
statement that it is unchanged. Explicit filtered questions wait for the deferred
`/statistics/typical-times` surface, which answers them under `ANSWER_AS_ASKED`
(honest insufficiency instead of a silently broadened number). Task screens still
receive item-aware typicals automatically via the derived spec — card A concerned
only a manual filter knob on the benchmark endpoint. Recorded consequence: V1's
response-contract changes are confined to the three task surfaces (§7.2–§7.4).

---

## Settled at the mechanism-inventory gate fold (2026-08-22)

**D25 — a narrowed median of zero is not a known typical (card C).** Owner, 2026-08-22:
*"the recommended option is the correct approach"* — **Require a real figure.** A section
whose narrowed history has enough samples but a median of zero is not "known"; the task
falls back to section-wide figures throughout, the same answer it gives today. Rationale
as recommended in the card: the promise of the feature is "narrow to comparable work",
and a population of zeros is not evidence about how long comparable work takes; counting
it lets the least-informative section decide the basis for every other section on the
task. Folded as intention §4C: the reconciliation quantifier and `BROADEN_TO_SECTION`'s
first rung require a **usable** narrowed median (`> 0`); `ANSWER_AS_ASKED` analytics
deliberately still reports a zero median verbatim (an honest statistic, HC-3/D17/D19).
Recorded consequence: under `item_narrowed_uniform` no participating section reaches
layer 2 at all, and `typical_worker_seconds: 0` beside `typical_basis: "item_narrowed"`
is unreachable on every task surface. The card's full text is preserved below for
provenance.

<details>
<summary>Card C as relayed (answered 2026-08-22)</summary>

**Question.** When a section's item-narrowed history has enough samples but they all
measure zero seconds, should that count as "we know the typical time for this item" — or
should the task fall back to the section-wide figure?

**Story.** Assembly is a section your workers complete on the spot: they mark it done
without ever starting the clock, so its recorded time keeps coming back as zero. A chair
task comes in, and over the last ninety days there are eight chair tasks whose Assembly
recorded zero. The system sees eight chair samples — plenty — and declares "we have
chair-specific history for this whole task". Assembly's own typical is then zero, so it
gets an emergency stand-in figure anyway, and every other section on that chair
(Cutting, Painting) is told to use chair-specific numbers. Meanwhile a chair task whose
Assembly simply has *four* real samples is treated as having too little chair history,
and the whole task falls back to generic figures. The section we know least about is
treated as sufficient; the one with thin but real evidence is not. Allowances — the
minutes each section is given out of the budget — move either way.

**Branches.**
- **Count it (today's written rule).** Eight zero-second chair samples are "enough chair
  history". The task uses chair-specific figures everywhere, and Assembly quietly gets a
  stand-in number. Allowances shift toward the chair-specific split.
- **Require a real figure.** A section whose narrowed history is all zeros is not
  "known", so the task uses generic section-wide figures throughout — the same answer it
  gives today, before this feature.

**Recommendation.** **Require a real figure** — because the whole promise of this feature
is "narrow to comparable work", and a population of zeros is not evidence about how long
comparable work takes; counting it lets the least-informative section decide the basis
for every other section on the task.

**On silence.** The gate holds. Implementation planning does not start; no guess is made,
because the two branches produce different allowances on real tasks.

**Trace.** Intention §3.3 (`has_narrowed`), §4.3 (the reconciliation quantifier), §4B
(the corrected reachability invariant), §4.5 (the `<= 0` layer-2 trigger), §11A rows
T10b / T21.

</details>

---

## Open — ⚠ OWNER DECISIONS REQUIRED (0)

None. Card C answered 2026-08-22 → D25.

---

## Ledger

**Empty as of the round-6 fold (2026-08-22).** D1–D25 all settled (cards A → D24 and
B → D23 answered 2026-08-20; card C → D25 answered 2026-08-22). The intention is
RESOLVED again; the implementation-planner may start.

Three contradictions the gate resolved **unilaterally by contract** are listed for
ratification in
`handoffs/reviewer/20260822_mechanism_inventory_gate_handoff.md` §5 — they change no
sentence the owner has approved, but each decides which side of a contradiction wins:
the corrected reachability invariant (intention §4B), the `is_estimated` definition
(§6B), and price-scenario's move to the injected request clock (§4A K1). Ratification
was relayed to the owner at the fold as three cards with recommendations to ratify.
**Ratified 2026-08-22** — the owner answered "go" to the relay (R1 additionally implied
by the D25 answer). The contracts stand as written; the record is closed.
