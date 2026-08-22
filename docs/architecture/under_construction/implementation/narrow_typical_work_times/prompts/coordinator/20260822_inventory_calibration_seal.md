---
plan: mechanism_inventory_gate
role: coordinator
round: 0
date: 2026-08-22
state: OPENED at the fold, 2026-08-22 — measurement VOID (see fold record at end)
---

# Calibration seal — mechanism-inventory gate, `narrow_typical_work_times`

Written BEFORE the gate prompt was authored (same sitting, prompt authored immediately
after this file was saved). Opened only at the fold of the gate's handoff, where each
hypothesis is scored **found / exceeded / missed**, and anything the gate found that no
hypothesis predicted is recorded as a coordinator blind spot.

## Hypotheses — what I expect the gate to find

**H1 — clock × spec signature (the §2A mechanism).** The gate will contract
`typical_times_statement` as carrying BOTH parameters (`now` and `specs`), preserving the
deliberate two-clock consumer split; §3.1's proposed signature, §4.2's restatement and §5's
call form all get amended. I additionally expect it to find that **HC-4/T11's byte-identity
claim must be stated at both clock forms** (`now=None` and injected `now`), which the
intention currently does not say.

**H2 — the statement's output contract under K distinct specs is undefined.**
`SectionTypicalEvidence` carries no spec identity, yet budget-allocations dedupes K specs
and makes "one statement call for the batch" (§6.2). Nothing in §3–§5 defines the result
*shape* for K > 1 — how a caller maps rows/columns back to (section, spec). I expect the
gate to demand a keyed return contract, independent of the internal strategy choice.

**H3 — NULL/degenerate-range semantics need per-field contracts.** "Unknown never matches"
is stated once globally (§3.1) but the per-field translation table does not exist: nullable
`designer`, half-open ranges `(None, max)`/`(min, None)`, and the degenerate fully-unbounded
range `(None, None)` — which sets a field (so `is_narrowing` is True) while excluding only
NULL-dimension items. I expect a contract enumerating each field's predicate incl. its NULL
row, and a ruling on degenerate ranges.

**H4 — the two-population FILTER arithmetic needs its exact composition written down.**
Today's 90-day window is an aggregate `FILTER` on `max(closed_at)`; the narrowed aggregates
must compose window AND `bool_or(item_match)` correctly for BOTH populations, with the
min-sample NULL rule applied per population. The intention names the mechanism (§13.2) but
never writes the composed form. Expect a contract; possibly also a finding that
`percentile_cont ... FILTER` composition constraints force the group-level `bool_or` into a
subquery/CTE shape that the contract must pin.

**H5 — at least one counted-sentence/enumeration defect inside the intention itself.**
Sealed specific candidates (the sweep may find these or others):
- §2A's drift table: header says **"Five citations checked"** over a **six-row** table, and
  "four of five call sites moved" excludes the `get_task_budget_status` row, which ALSO
  moved (5 of 6 moved by the table's own content).
- "four consumers" (§1, §2.1) vs §6.2's **six-row** integration table (four consumers +
  budget-status + division) — the sentence and table count different things and a criterion
  built from either will miss members of the other.

**H6 — `TaskBudgetStatus` change is cross-pipeline surface and needs a compatibility
contract.** §6.2 row 1 ("stops discarding the loaded primary Item") mutates a dataclass
consumed by the shipped `simple_valuation_editor` price-scenario and by live-clock-touched
services. Expect the gate to demand an additive-only contract (new field, no existing field
changes, no behavioural change to budget-status' own payload) — the lineage has already
paid one round for a `TaskBudgetStatus` claim (re-review r4, H-2 lesson).

**H7 — §3.6's sample_count naming rule has at least one undecided edge.** Candidate: which
population's count an *excluded* section (resolved independently under BROADEN) publishes
when insufficient, and whether §7.2's `narrowed_sample_count`/`section_sample_count`
defaults ("default 0") can conflict with "always present, non-nullable" when no evidence
row exists for a section at all.

**H8 — `is_estimated` / `sections_without_sample` semantic drift.** §6.4 redefines
`is_estimated` ("layer 2 fired for ≥1 participating section"); the current serializer also
ships `sections_without_sample`/`sections_total`. Expect a finding that the intention never
says what happens to those two existing fields under the new regime (kept? recounted
against which population?) — a contract gap on an already-published payload.

**H9 — verification mechanisms themselves under-specified.** T11's "compiles to today's
SQL string" needs a comparison contract (dialect, literal_binds vs bound params — the `now`
cutoff is a bound value); §11.2's "keys only" golden-diff criterion needs a decidable
mechanism (what check proves a diff is keys-only).

## Predicted verdict

FAIL-with-amendments in the productive sense: the gate writes lettered contract sections
into the intention (≈4–8 mechanisms to contract-grade), opens 1–3 owner cards (most likely
from H1's split-vs-collapse design choice and H8's published-field semantics), and the
re-grounding sweep finds drift beyond §2A's sample but nothing that invalidates a decision
D1–D24.

## Contamination statement (honest, per protocol)

- **H1 is fully hinted**: the prompt names the §2A signature question as a mandated depth
  target (orientation requires this). Finding it scores as *found-with-hint*.
- **H2 is hinted**: I chose to include the K-spec output-shape question as a second named
  depth target — a deliberate contamination, declared here, because a miss there costs a
  planner round. Scores as *found-with-hint*.
- **H3, H4, H7 are generically hinted**: the prompt carries §13 step 2's own list (NULL
  semantics, FILTER arithmetic, sample_count naming), which names the areas but none of my
  expected conclusions.
- **H5 is generically hinted** by the standing "every counted sentence is a checklist"
  instruction (lineage-mandated); the two specific sealed instances are NOT in the prompt.
- **H6, H8, H9 are unhinted** — clean calibration probes.

---

## FOLD RECORD (coordinator, 2026-08-22, at handoff consumption)

**Measurement: VOID.** The gate session disclosed, unprompted and first in its handoff,
that it opened this file while orienting, before doing any gate work. Every hypothesis
must therefore be treated as hinted; found/exceeded/missed cannot be scored this round.
The session's honesty is noted in its favour — the disclosure led the handoff.

**Informal correspondence (recorded for continuity, explicitly NOT a calibration
result):** the gate's findings substantively covered H1–H9 (several beyond the sealed
prediction: the §2A count defect was found exactly as sealed; §6B found `is_estimated`
*reverses* a shipped value where H8 predicted only a gap; §4A K5/T11 matched H9), and
produced at least six findings no hypothesis predicted — §4B's reachability invariant
being false as written, five inert named mutations (T5/T7/T14/T19 beyond T11), the
terminal-as-division-by-zero-guard, S-4's production constructors, S-5's diverged step
loads, S-7's two meanings of "task's section ids". The predicted verdict shape
(amendments + 1–3 cards, nothing invalidating D1–D24) matched: 9 amendment sections,
1 card, D1–D24 intact.

**Process lessons, adopted for every future seal in this project:**
1. A seal stored inside the project folder a session is told to read is not sealed.
   Future seals live OUTSIDE the project tree —
   `~/.claude/.../memory/`-adjacent or another path the prompt never references — with
   only a dated pointer line ("a seal exists for this gate") in `prompts/coordinator/`.
2. The session prompt's read order gains an explicit exclusion line: "do not open
   anything under `prompts/coordinator/`".
3. Re-seal at the next gate (plan-projection round 0 or the planner-output review) and
   score that one normally.
