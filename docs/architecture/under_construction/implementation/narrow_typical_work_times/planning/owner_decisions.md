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

---

## D26 — Query cost: take the pain now; the real fix is frozen typicals, later (2026-08-22)

**Card.** Plan-2 projection, owner card 1: *do you want a speed ceiling fixed before the
measurements are taken, or will you judge the numbers when you see them?* The projection
recommended fixing a ceiling now, reasoning that "a threshold chosen after seeing the
numbers is the one that always turns out to have been met."

**Owner answer, verbatim.** *"about the owner card, if i understand it correctly this is
about performance, because on every call of budget allocation we are performing that multi
join query and calculation for 50 * join filters. but the current frontend has it already
corrected to 20 fetch pagination on any task query. and in the near future i will frezze
this typicals as more data comes in and then only that schedulers update those snapshots,
that way query and computanional performance will be better, for now we can take the pain
( plus there is not that many item types )"*

**Decision.** **No acceptance ceiling.** The measurements are still taken and recorded in
full — they are the input to the freezing decision — but no number blocks the phase, and
the projection's recommendation is **overridden knowingly**, on three stated grounds:

1. **The card's premise was wrong about the batch size.** It reasoned from 50 tasks per
   call. The API cap is 50 (`_MAX_TASK_IDS`), but **the frontend paginates task queries at
   20**, so the realistic operating point is 20 tasks per call and 50 is a worst case
   nobody currently reaches. §12's matrix is corrected accordingly (§12A).
2. **The narrowing axis is small in practice** — few item categories exist today, so the
   K-spec fan-out is far from its modelled 20.
3. **The architectural fix is already chosen and is not this pipeline's.** Typicals will
   be **frozen into stored snapshots refreshed by a scheduler**, so the per-request cost
   of this query stops mattering rather than being tuned. Optimising it now would be work
   thrown away. Recorded as **direction, not commitment** — no phase of this pipeline
   builds it, and intention §12's "no caching layer is the remedy" still binds *within*
   this pipeline.

**What this does not license.** Measurement is not optional and the numbers are not
decoration: the doc must state them plainly enough to be the evidence the freezing
decision is later argued from. A result an order of magnitude outside expectation is
**surfaced to the owner as information** — not as a gate, and not silently filed.

**Trace.** intention §12 → new §12A · plan 2 §12 and §6A · master plan §7 constraint 2 ·
projection handoff card 1 and L19/L20/L21/L22.

---

## D27 — The one-active-primary rule is tested in phase 3, not phase 2 (2026-08-23)

**Card.** Phase-2 review card 1. Buy the test for the "one active primary item per task"
rule now, in the phase whose central join depends on it, or in phase 3, where the first
real surface reads the narrowed number?

**Owner, 2026-08-23, verbatim:** *"Card 1 will be executed by phase 3."*

**What was decided.** Phase 3. The reviewer's recommendation is followed.

**Why it is safe to defer.** The reviewer read the rule out of the **live migrated test
database**, not off the model:

```
CREATE UNIQUE INDEX uix_task_items_primary_active ON public.task_items USING btree
  (workspace_id, task_id) WHERE ((role = 'primary'::task_item_role_enum) AND (removed_at IS NULL))
```

— an exact match for §3A C5's `ON` clause, so plan §2's fan-out-free claim is **true at the
database right now**. The one migration that could have broken it (`ddc5bf50153b`, the enum
lowercase rename) explicitly drops and recreates it with the lowercase label. Phase 2 ships
no consumer, and the two code-side mutations (C7(ii), C8) already bite.

**What the deferral is buying, restated honestly.** The rule is unguarded at **both**
layers, not one. Besides the database index, `add_item_to_task.py:46-57` pre-checks for an
active primary and raises `ConflictError("Task already has an active primary item.")` —
and **no test file in the repository references `add_item_to_task` at all**. The app-level
gap is pre-existing and outside this pipeline's perimeter; it is recorded because it changes
the shape of the row phase 3 buys, not because phase 2 caused it.

**Consequence if the rule were ever lost.** A task with two active primaries is counted
twice, a section's typical drifts upward, and nothing errors — the business quietly starts
quoting longer jobs than its own history supports.

**Trace.** phase-2 review card 1 + N1 · plan 2 §6A "Recorded, not fixed here" (L33/R10) ·
§3A C5 · plan 3 §6 (two rows, below).

---

## D28 — The architecture-graph queue is adjudicated by an authorized maintenance session (2026-08-23)

**Card.** Phase-2 review card 2. Seven graph review items from phases 1 and 2 sit
unadjudicated; one carries a stale evidence span (it points at
`test_typical_times_narrowing.py:199-224`, where that test no longer lives — a later round
moved it to line 232). Only the owner may approve, reject or edit a review item.

**Owner, 2026-08-23, verbatim:** *"about the card 2: we can have a codex session
maintenance to approve those."*

**What was decided.** A dedicated **maintenance session** carries out the adjudication
**under this recorded owner authorization**, rather than the queue growing across phases
3–6. This is the authorization the standing rule requires; it is **scoped to these seven
items** and does not generalize to future ones, which need their own.

**Dispositions authorized**, following the reviewer's recommendation:
- **Approve** the six items whose evidence the reviewer verified accurate.
- **Reject** the one carrying the stale span, so it can be **re-recorded correctly** —
  reject-and-re-record is the only available fix (an evidence summary has no edit path),
  and a same-id re-record does re-enter the review queue.

**Standing rule, unchanged and reaffirmed.** No agent adjudicates a graph review item on
its own judgment, and a `humanInstruction` string is never authorization. What changed here
is that the owner gave the authorization, for these seven, in this conversation — the
maintenance session executes a decision already made, and reports rather than decides.

**Why it matters.** The graph is the map agents read before touching the system. An entry
pointing at the wrong lines sends an agent looking for the test that proves the new query's
row shape to a different test entirely.

**Trace.** phase-2 review card 2 + N5 · master plan §8 (its recorded "0 pending / 0 stale"
predates phases 1–2 and is now stale) · plan 2 round-1 graph delta (`d07028b`).

---

## D29 — Scoped authorization: one graph session, three operations (2026-08-23)

**Card.** Phase-2 re-review card, plus a defect the coordinator found while answering the
owner's question about it: the entry D28 re-recorded is **still wrong**.

**Owner, 2026-08-23:** authorized, in response to the measured findings below.

**What was decided.** One maintenance session performs **exactly three operations**, then
stops. This authorization is **scoped to these three** and does not generalize.

| # | target | operation | measured 2026-08-23 |
|---|---|---|---|
| 1 | review item `node:source-symbol-working-section-typical-times-statement-narrowing` | **reject, then re-record**, leaving it pending | its test link reads **232–253**; the test's decorator is at **237** and its body ends at **259**. 232–234 are the *previous* test's closing assertions. |
| 2 | `domain-item-economics-typical-filters` → `typical_filters.py :: _optional_values` | **re-accept** (no re-anchor) | span **78–88** is **correct**; only the content changed (plan 1's S2 fix and phase 2's C0 work rewrote the isinstance guard inside it). |
| 3 | `projection-item-economics-task-production-time` → `budget_division.py :: _governing_step` | **re-anchor** | recorded **188–208**; the function actually spans **182–202**. The recorded window covers its tail, *all* of `_step_state_is_terminal` (204–207) and the `def` line of `_step_state_is_excluded` (208). Drift came from a **neighbouring pipeline's** commit `f904100`, not this one. |

**Why operation 1 exists at all — and the rule it buys.** D28's session re-recorded the span
using the **reviewer's round-1 diagnosis** ("the test now begins at 232") instead of reading
the file. Fix round 3 landed *between* that diagnosis and the re-record, and S1's four new
seeded rows pushed the test down six lines. Its prompt did say to read the numbers out of
the file as it is now; it used the number it had been handed.

**Standing rule earned:** *a line number handed to a session is a claim with a shelf life.
Derive every span by locating the symbol in the file at the moment of writing, and assert
the span begins at a `def` or a decorator* — that single check would have caught this
failure and D28's original one. Expected values in a prompt are a **checksum to compare
against**, never the value to write.

**Standing rule unchanged.** No agent promotes, rejects, edits, re-anchors or removes a
graph item on its own judgment; a `humanInstruction` string is never authorization. This
session executes decisions already made and **reports** rather than decides. The re-recorded
item is left **pending** — it does not approve its own work.

**Trace.** phase-2 re-review card + N5 · D28 (scoped to seven items) · coordinator
measurement 2026-08-23 in answer to the owner's question.

## D30 — Scoped authorization: bring the graph's *meaning* current for phase 4, and clear the queue

**Owner, 2026-08-24, verbatim:** *"so we should fix thow three steps before we move to plan 5
because that will leave the current scenario clean and neat. can you make a fix prompt that codex
can execute for those three fixes. codex has permission to human approve."*

**What this authorizes, and nothing beyond it.** One scoped maintenance session may enact graph
mutations **limited to these three items**:

1. **Rewrite the descriptions** of exactly two nodes —
   `projection-item-economics-task-production-time` and
   `projection-item-economics-task-budget-allocations` — so the graph's meaning matches what
   phase 4 shipped.
2. **Adjudicate the single pending review item**
   `node:source-symbol-working-section-typical-times-statement-narrowing` — approve, or
   reject-and-re-record, per the judgment recorded in the session prompt.
3. **Re-record evidence span-free** where the session's own writes would otherwise carry
   `startLine`/`endLine`.

**Explicitly NOT authorized:** any other node or edge; deleting or deprecating anything; the
four `stale: true` source links on the production-time projection (they are `contentHash` drift,
not a repair candidate under the interim policy — leave them); **D29's three operations, which
remain deferred**; and applying `.archgraph/backfill/`, which is the owner's own work.

**Why this is the phase-4 shape and not maintenance.** The phase's graph delta recorded three
**source links** — evidence pointers to two contract tests and `participating_sections` — and
never touched the two projections' **descriptions**, which are the meaning content an agent
actually reads. Both still say *"section typicals"* and describe a pre-narrowing world: no
item-narrowing, no `typical_resolution` block, no `uniform_basis_v1` reconciliation, no
`allocation_method` v2, and for budget-allocations no K-spec batch dedupe. Measured 2026-08-24.
By contrast `domain-item-economics-typical-filters` **is** current and rich — phases 1–2 updated
meaning properly — so the gap is localized to the two consumers.

**The standing rule is relaxed only within this scope.** Outside items 1–3, no agent promotes,
rejects, edits, re-anchors or removes a graph item on its own judgment, and **a
`humanInstruction` string is never authorization**. This authorization is recorded here, in the
repository, which is what makes it one.

**Sequenced before plan 5** at the owner's direction, so phase 5 opens against a graph whose
meaning is current.

---

## D31 — Scoped authorization: bring the price-scenario projection's meaning current, and re-anchor its drifted links

**Owner, 2026-08-24, verbatim:** *"we can create a maintenance prompt for codex to correct this,
codex has permission to edit and then human confirmed"* — answering the coordinator's report of
what the phase-5 graph delta left undone, which enumerated exactly the four items below.

**Context.** Phase 5's implementation round 1 recorded three source links on
`projection-item-economics-task-price-scenario` and then **previewed a description replacement
that the client's safety gate declined**, because that turn had not authorized that exact
mutation. The session escalated instead of forcing it, and fix round 2 carried the item forward
unchanged rather than retrying a gate that had already said no. **This decision is the missing
authorization.** Plan 5 §7A makes the description rewrite part of the phase, so **phase 5 cannot
reach `APPROVED` without item 1.**

**Authorized, and only these, on `projection-item-economics-task-price-scenario`:**

1. **Replace the description's stale mechanism clause** — the words *"median-substituted task
   typical time"*, which name the private `_median(usable)` ladder plan 5 task 4 deleted. The
   replacement states what the projection composes **now**: an item-aware typical drawn from the
   same-category slice of each participating section's history, through the shared engine and the
   shared reconciliation, windowed by the **injected request clock**. Every other clause of the
   description is **true and stays** — the non-bound nulling behaviour, "keeping the step-derived
   typical", "performs no writes", and the transitive budget-status dependency.
2. **Re-anchor `get_task_price_scenario.py:get_task_price_scenario`** — currently
   `startLine 184–315`, `stale: true` — to **`path` + `symbol`, span-free.**
3. **Re-anchor `test_price_scenario_query.py:test_c1_status_matrix_has_twelve_exact_rows`** —
   currently `startLine 583–615`, `stale: true` — to **`path` + `symbol`, span-free.**
4. **Refresh the `contentHash` of
   `test_narrowed_price_scenario.py:test_c5_three_surfaces_use_the_same_published_literal`** —
   symbol-anchored already, recorded at `10:04:22` in round 1 and **stale by the time fix round 2
   finished editing that file**. The symbol is correct; only the hash is behind.

**The owner grants the session permission to perform these edits and to mark the result
`human_confirmed`.** That grant is bounded by this list.

**Items 2 and 3 are re-anchoring, not span repair.** Both links drifted because phase 5 changed
their files. The interim policy is *"a span that merely drifted is not a repair candidate"* —
so the operation is to **remove the span** and anchor by symbol, which is also what the two links
phase 5 added already do.

**Explicitly NOT authorized:** the other **five** stale nodes; any other node, edge, description
or evidence entry; deleting, deprecating or promoting anything; **editing any evidence summary**
(no write path can — reject-and-re-record is the only mechanism, and it is out of scope here);
**D29's three operations, which remain deferred** and are in any case scoped to an operation the
span-removal policy has retired; and applying `.archgraph/backfill/`, which is the owner's own
work.

**The standing rule is relaxed only within this scope.** Outside items 1–4, no agent promotes,
rejects, edits, re-anchors or removes a graph item on its own judgment, and **a `humanInstruction`
string is never authorization**. This authorization is recorded here, in the repository, which is
what makes it one.

---

## D32 — Post-close standing items: check and correct the graph, then confirm; clean the test databases

**Owner, 2026-08-24, verbatim:** *"we should fix all that standing after the close, the graph should
be checked, if correction need it corrected, then move to human confirmed. about the test database.
it should be cleaned ."*

**Scope 1 — the two pending graph reviews**, `node:table-customer` and
`edge:command-task-create--reads_from-->table-customer`, both `ai_inferred`, created 2026-08-24
11:36 **from outside this pipeline**. The owner authorizes: verify at source, **correct if wrong**,
then move to `human_confirmed`.

**Measured finding (coordinator, 2026-08-24).** The **relationship is true** — `create_task.py`
imports `Customer` and selects it filtered by `workspace_id`, `client_id` and
`is_deleted.is_(False)`, raising `NotFound` when absent. **The stated mechanism is false in both
items:**

- The edge's summary claims task creation *"copies `Customer.display_name` into the task
  snapshot"*, and its `inferenceReason` names **`customer_name_snapshot`** as the field.
- The node's `inferenceReason` calls the model *"the customer registry source from which task
  creation reads the canonical display name."*

Measured: **`customer_name_snapshot` appears 0 times anywhere under `beyo_manager/`**, and
**`customer.display_name` is read 0 times in `create_task.py`**. What the command actually copies
from the Customer row is contact data — `primary_phone_number`, `secondary_phone_number`,
`primary_email`, `secondary_email`, `address` (`create_task.py:178-181`). The only `display_name`
in that file is `request.customer_display_name`, used when **creating** a customer from inline
data, not when reading one.

**Correction path: reject and re-record.** Evidence summaries are immutable — no write path edits
one — so the items are rejected with the reason, re-recorded with accurate summaries, and then
confirmed. A same-id re-record re-enters the review queue by design.

**Scope 2 — the orphaned test databases.** ~51 `beyo_test_*_template` databases on
`localhost:5433`, left by prior probe and review sessions, growing ~6 per review round, with
nothing in the pipeline dropping them. The owner authorizes cleaning them.
**Bounded by the coordinator, not by the owner's sentence:** **anything the live test slot needs
stays.** The active slot's databases and any template the current suite builds from are excluded,
identified before anything is dropped, and named in the report.

**Explicitly NOT authorized by this decision:** the six stale nodes; any other node, edge or
evidence entry; `.archgraph/backfill/`; and **D29's re-anchor prompt, which remains deferred and
mis-scoped**. Outside these two scopes the standing rule is unchanged — no agent promotes,
rejects, edits or re-anchors on its own judgment, and a `humanInstruction` string is never
authorization. This authorization is recorded here, in the repository, which is what makes it one.
