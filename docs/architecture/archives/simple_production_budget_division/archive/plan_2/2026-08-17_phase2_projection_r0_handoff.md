---
plan: 2
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-17
actor: Opus 5 (projection r0)
---

# Projection r0 — plan 2 (task-scoped section-keyed production-time view)

## Opening (owner-readable)

The plan is buildable and the decision behind it is arithmetically right — I re-derived
the 180-minute example by hand and through the real code, and the new rule gives
72/36/72 minutes exactly, where the old one gave 51.4/25.7/102.9. But the plan does not
yet say what a **finished** step's card should show, and that gap touches almost every
card in production, so an implementer would have to invent the answer in code. Three
questions need you personally; they are the three cards below, each answerable in one
line. Two of them are cheap to get wrong and expensive to notice, because the numbers
stay plausible.

I also found one thing worth telling you plainly: part of the new rule — the part that
says a failed step's burnt time should only be taken from its own section — quietly
undoes a decision you already made (a failed step's time comes off the whole budget).
Dropping that one clause keeps your earlier decision intact and, as a bonus, leaves five
of the existing tests unchanged instead of rewritten. My recommendation is to drop it.

Nothing here is a defect in shipped code. Everything is a paragraph that needs writing
before an implementer starts.

---

## ⚠ OWNER DECISIONS REQUIRED (3)

### Card 1 — What should a *finished* step's card show?

**Question:** when a step is done, should its card show its own time as the target, a
share of its section's slice, or the whole slice?

**Story.** A worker finishes Upholstery on a chair in 50 minutes. Today the card reads
"50m of 1h 12m — 22m left". Now the manager reassigns Upholstery, so the chair has a
finished pass and a fresh one. Tomorrow the same finished card must read *something* —
and when the second pass also finishes, both cards read something again. If each
finished pass claims the full 1h 12m, the two cards together promise the chair 2h 24m of
a 3h budget. If a finished pass shows only its own time, a pass that overran 1h 12m by
20 minutes reads "on target" forever.

**Branches.**
- **Own time as target** — every finished step always reads exactly on target; a real
  overrun becomes invisible the moment the step closes.
- **Share of the slice** — a finished overrun still reads "over its share", and the
  widget and the cards always add up to the same number.
- **Whole slice on every step** — simplest, matches today for the ~98% of sections
  holding one step, but two finished passes double-count the section's time.

**Recommendation:** *share of the slice* — a finished step is allowed the time it
actually worked, and whichever step the section is "currently at" holds the rest. For a
section with one step that is identical to today, so ~98% of cards do not move at all,
and a section that overran still says so.

**On silence:** the gate holds; no implementer prompt is compiled. No guess is made.

**Trace:** intention §12.5 M3.5b, D11a; plan 2 T3, C4/C12/C13/C20.

---

### Card 2 — What does the card say when the first pass already ate the whole slice?

**Question:** if a section's finished pass burnt more than the section's whole share,
should the new pass read "18m over" or "0m left"?

**Story.** A chair gives Upholstery 1h 12m. The first pass burns 1h 30m — it went badly.
The manager reassigns it, and a worker opens the card for the second pass before doing
any work. The section has already spent 18 minutes more than it was ever given, so the
honest answer to "how long do I have?" is "less than nothing".

**Branches.**
- **"18m over" (a negative target)** — honest, and the widget's section total always
  matches the sum of its cards exactly. The progress bar needs one extra rule: a
  non-positive target draws a full over-share bar.
- **"0m left"** — safer to render, but the section's total then stops matching the sum of
  its cards, which is the one guarantee this whole endpoint exists to provide.

**Recommendation:** **"18m over"**, with the bar rule written into the frontend handoff.
The two surfaces agreeing is worth more than avoiding one negative number, and "left"
is already documented as able to go negative.

**On silence:** the gate holds.

**Trace:** intention §12.5 M3.5b, §12.6 P-AGREE; frontend handoff §6.2/§8; plan 2 C12/C13.

---

### Card 3 — Does a failed step still take time from the other sections?

**Question:** when a step fails after burning 40 minutes, should those 40 minutes come
off the whole task's budget (as today), or only off its own section's share?

**Story.** A chair has a 3-hour budget. Sanding fails after 40 minutes of work. Today
those 40 minutes come off the top, so every remaining section's target shrinks a little
and the targets never promise time the chair no longer has. Under the new section rule as
currently written, only Sanding's own share absorbs the loss — and if Sanding has no
further work at all, nobody absorbs it: the remaining sections still add up to the full
3 hours, of which 40 minutes are already gone.

**Branches.**
- **Off the whole budget (today's rule)** — the targets keep their promise; your earlier
  decision stands unchanged; five existing tests keep their exact numbers.
- **Off its own section only** — the section that failed pays, which fits the new
  "the section that overruns pays" idea, but the task can promise time it has already
  spent.

**Recommendation:** **off the whole budget** — keep today's rule. The new decision is
about how the budget is *divided*; it does not need to change what is *subtracted first*,
and changing both at once reverses a promise you already accepted.

**On silence:** the gate holds.

**Trace:** intention §4 (D8 consequence table), §12.5 "Exclusion is decided at the
allocated unit"; plan 2 T2, C8/C9.

---

## Write perimeter (this session)

- **Documents written:** exactly this file.
- **Repository code/tests/docs modified:** none. `git status` is unchanged apart from
  this file.
- **Database:** read-only. `SELECT` only, against the configured DB (`127.0.0.1:5433`,
  `beyo_manager`). No writes, no DDL, no migration.
- **Scratch (outside the repo, non-authoritative, discarded):**
  `…/scratchpad/walk.py`, `…/scratchpad/shadow.py`, `…/scratchpad/t7b.py` — three
  throwaway scripts used to re-derive arithmetic, prove route resolution, and pin new
  expected values. None imports into the repo; none is proposed as code.
- **Tests executed (read-only):** the six phase-1 files, unchanged, **140 passed**
  (baseline confirmed green before predicting what changes).
- **Architecture graph:** not touched (projection records no delta).

---

## 1. §12.4 re-measured on the configured database (2026-08-17, this session)

Every figure below is a count, re-run now. **§12.4 is accurate as written** — all seven
of its claims reproduce exactly. It is, however, **incomplete**: four measurements it
does not carry are load-bearing for phase 2, and one of them (row 12) is a blocking
finding on its own.

| # | §12.4 claim | Measured now | Verdict |
|---|---|---|---|
| 1 | `order_list` populated 14 of 14 non-deleted sections | 14 / 14 | ✅ |
| 2 | not unique — 12 distinct over 14 rows | 12 distinct | ✅ |
| 3 | tie at `2` = cleaning seat / cleaning wood | exactly those two | ✅ |
| 4 | tie at `7` = upholstery installation / weaving | exactly those two | ✅ |
| 5 | steps per (task, section): 1→2732, 2→49, 3→1 | 2732 / 49 / 1 | ✅ |
| 6 | 2782 groups over 2833 non-deleted steps / 522 tasks | 2782 / 2833 / 522 | ✅ |
| 7 | groups with 2+ non-closed steps: **0** | 0 (under *both* candidate definitions) | ✅ |
| 8 | states: completed 1764, pending 1039, paused 28, working 2 | identical | ✅ |
| 9 | zero `skipped`/`cancelled`/`failed` non-deleted | 0 | ✅ |
| 10 | (the 253→0 skipped mystery) | **255 skipped rows exist — all `is_deleted=true`** | explained |
| 11 | — | **45 of the 50 multi-step groups have NO open step** (44×{completed,completed}, 1×{c,c,c}); only **5** are {completed,pending} | **missing → B2** |
| 12 | — | **15 sections are referenced by live steps; 1 of them is soft-deleted** (`sanding`, `order_list=4`, 5 live pending steps) | **missing → B8** |
| 13 | — | `sequence_order` is **NULL on 2833 / 2833** live steps | **missing → N2** |
| 14 | — | **0 committed-current evaluations and 0 `item_cost_results` in the whole database** | **missing → N9** |

Row 10 resolves the coordinator's note: the skipped steps did not vanish, they are all
soft-deleted, i.e. produced by the *remove* door and therefore outside M2's universe by
§4's consequence table. `EXCLUDED_STEP_STATES` genuinely has **no** production instance.

Row 7 detail, because it decides B7: the two candidate readings of "non-closed" —
`state NOT IN (completed, skipped, failed, cancelled)` and `closed_at IS NULL` — agree on
**every one of the 2833 live rows** (0 rows where a terminal state has a NULL `closed_at`;
0 rows where a non-terminal state has one set). The ambiguity is latent, not active.

Supporting facts also measured, used later in this handoff:

- `latest_state_record_id` populated 2833/2833; `entered_at` never NULL; the latest
  record's `state` mirrors the step's state on 2833/2833 and its `exited_at` is NULL on
  2833/2833 → M3.4's `state_entered_at` is safe and the frontend's live tick needs no
  `exited_at` (N7).
- `working_section_name_snapshot` populated 2833/2833 and **equal to the live section
  name on every row** → M3.9's two names are indistinguishable on all current data (P7).
- `weaving` has `sample_count = 0` → typical NULL, so M2's fallback-median ladder is live
  in production today (N8).

---

## 2. D11's arithmetic at the new unit — re-derived, not assumed

Run through the **real** `divide_production_budget` with one unit per section
(`…/scratchpad/walk.py`):

| Section | typical | variant A (per step) | **variant B (per section)** |
|---|---|---|---|
| Structural Repair | 3600 s | 3086 s = 51.43 min | **4320 s = 72.00 min** |
| Sanding | 1800 s | 1543 s = 25.72 min | **2160 s = 36.00 min** |
| Upholstery (2 steps) | 3600 s | 3086 + 3085 = 6171 s = 102.85 min | **4320 s = 72.00 min** |
| Σ | | 10800 | **10800** |

`_budget_seconds(Decimal("180.00"))` → `10800` exactly (`budget_division.py:59-61`,
half-even quantization); weights are `Fraction`s (`:149-155`); no remainder arises here
because 10800 × 3600 / 9000 is integral. **§12.5's table is correct to the digit**, and
D11's own rationale (`owner_decisions.md:104-111`) reproduces exactly.

**Indivisible case, P-SUM3 exactly.** Three sections, equal typicals, budget
`Decimal("1.01")` → `D = 61`: allowances **21 / 20 / 20, Σ = 61** — largest remainder
assigns the single leftover unit and the sum is exact. Re-run with the units supplied in
reversed insertion order: byte-identical (P-DET holds at the new unit).

**Can `_sort_key` (`:72`) serve grouped units unchanged?** Mechanically yes — a group
object exposing `client_id = working_section_id` and `sequence_order = None` yields
`(True, 0, working_section_id)`, so remainder ties break on **section id ASC**,
deterministically and insertion-order-independently (verified). But that is **not** M3.2's
render order, and the two orders genuinely differ on live data: by M3.2 `weaving` is the
8th row (order_list 7, name after "upholstery installation"); by section id it is 11th
(`…13TPM…` sorts after `assembly …13H9Q…` and `sewing …13PBQ…`). So the leftover second
lands on a different section depending on which key is used — see **B6**, which is the
form this becomes when E2 and E3 choose differently.

---

## 3. What D11 does to phase 1's tests — enumerated, every row, values pinned

26 phase-1 tests exist across four files (11 + 4 + 4 + 7). The 7 in
`test_typical_times_query.py` carry no allocation value (M1 only) and are unaffected.
Every remaining row is listed. **New values were computed by running the proposed rule
against each fixture** (`…/scratchpad/t7b.py`), not by reasoning.

Two columns of "new", because Card 3 changes the answer:

- **(i)** intention as written — exclusion decided at the allocated unit;
- **(ii)** Card 3's recommendation — charging stays per step, only *weighting* moves.

| Test (`test_budget_division.py`) | asserted today | new under (i) | new under (ii) — recommended |
|---|---|---|---|
| `…largest_remainder_preserves_distributable_sum` :25 | 21/20/20, Σ 61 | **unchanged** | **unchanged** |
| `…excluded_consumption_is_charged_before_division_and_clamped` :36 | `D == 1200`; live-a/b 600/600 | **`D` → 3600** (per-step values stay 600/600) | **unchanged** |
| " (clamped half) :46 | `D == 0`; live `0`, `on_track` | **`D` → 60; live → −40** | **unchanged** |
| `…typicals_proportionally_weight…` :56 | 3600 / 1800; 30/30 | **unchanged** (distinct sections) | **unchanged** |
| `…tie_order_is_nulls_last_then_client_id` :72 | a=2,b=1; a=1,z=2 | **unchanged** | **unchanged** |
| `…live_step_set_redivides…` :92 | Σ 60; a=50; deleted absent | **unchanged** | **unchanged** |
| `…live_partition_includes_working_paused_and_completed_steps` :105 base | 15/15/15/15 | **20/20/20 + completed 0** | **20/20/20 + completed 0** |
| " with_new :120 | 12×5 | **15/15/15/15 + completed 0** | **15/15/15/15 + completed 0** |
| " after_skip :133 | 20/20/20, skipped excluded | **unchanged** | **unchanged** |
| `…fallback_median_interpolates_even_values` :147 | 800; 811 | **unchanged** (distinct sections) | **unchanged** |
| `…no_budget_and_zero_typicals` :166 | no_budget; Σ 60 | **unchanged** | **unchanged** |
| `…all_excluded_steps_return_task_figures_without_division` :177 | B 600, C 180, D 420 | **unchanged** (whole group excluded) | **unchanged** |
| `…deleted_skipped_step_is_outside_budget_universe…` :190 | C 120, D 480, working 480 | **C → 0, D → 600** (working stays 480) | **unchanged** |
| `…half_even_budget_seconds_quantization` :208 | Σ 11701 | **unchanged** | **unchanged** |

| Test (`test_budget_allocations_query.py`) | asserted today | new under (i) | new under (ii) |
|---|---|---|---|
| `…keeps_excluded_consumption_and_deleted_steps_distinct` :134 | live 4800; failed excluded/None; actual 1200 | **unchanged** | **unchanged** |
| `…uses_shared_typicals_for_two_section_proportional_split` :160 | `section == 2 × second` (3200 = 2×1600) | **BREAKS — 2800 vs 2×2000** | **unchanged** (3200/1600) |
| `…constant_query_count_for_one_and_three_tasks` :176 | `first_count == 11` | unchanged **iff** T3 adds no query to E2 (N5) | same |
| `…remove_service_maps_a_removed_step_to_deleted_skipped` :206 | state/deleted flags | unchanged | unchanged |

`test_budget_division_routes.py` (4 tests): none asserts an allocation value; `:132`
carries the string `"static_proportional_v1"` inside a *fixture dict* whose serializer
output is checked for **key sets only**, so it does not pin the label (see P2).

**The three findings this enumeration produces:**

1. Under (i), **three** unit tests and **one** integration test change; under (ii), only
   the two `live_partition` cases change. Card 3 is therefore also a
   blast-radius decision, not only a semantic one.
2. `…excluded_consumption…` :42 is the sharpest trap in the set: under (i) its
   **per-step** values stay 600/600 while `distributable_seconds` triples 1200 → 3600.
   A reviewer checking only E2's wire sees nothing move.
3. `…uses_shared_typicals_for_two_section_proportional_split` :170 asserts P-PROP as a
   **ratio between two per-step values**. Under D11a per-step values are no longer
   proportional to typicals (a step's number depends on its siblings' consumption), so
   under (i) this row cannot be repaired by changing a literal — its *invariant* is
   wrong. It must become a section-level assertion. This is the one row where "change it
   deliberately with the new literal" (T7b) is not enough.

---

## 4. Decision ledger

| # | Decision point | Class | Routing |
|---|---|---|---|
| B1 | `divide_production_budget`'s return contract for grouped units | plan gap | plan 2 T2/T3 |
| B2 | per-step allowance of a **closed** step | intention gap | intention §12.5 M3.5b · card 1 |
| B3 | open step's allowance may go negative | intention gap | intention §12.5 M3.5b · card 2 |
| B4 | exclusion at the allocated unit changes `C` | intention gap | intention §12.5 · card 3 |
| B5 | multi-open split weights (equal? by typical?) | intention gap | intention §12.5 M3.5b |
| B6 | remainder tie key for grouped units | intention gap (rule 6) | intention §12.5 / master plan §4 |
| B7 | the "closed"/"non-closed" predicate itself | intention gap (rule 6) | intention §12.5 M3.4 |
| B8 | sections referenced by live steps but soft-deleted | intention gap | intention §12.4/§12.5 M3.1 |
| B9 | where `order_list` comes from | plan gap | plan 2 T4 |
| B10 | second route mirror needs a body change, not a row | plan gap | plan 2 T6/C18 |
| B11 | `latest_state_record` eager-loading | plan gap | plan 2 T4 |
| B12 | `final.percent_consumed` has no source column | intention gap | intention §12.5 M3.8 / C17 |
| P1 | P-PROP / P-STABLE are per-step statements | contract amendment | intention §4/§12.6 |
| P2 | `allocation_method` label | contract amendment (delegated to me — ruled) | intention §12.5 |
| P3 | §12.4 lacks four load-bearing counts | contract amendment | intention §12.4 |
| P4 | single home for status + `item_binding` | free choice → delegate explicitly | plan 2 T4 |
| P5 | C3's fixture is unconstructible | plan gap | plan 2 C3 |
| P6 | C5/C7/C10 cannot be DB-backed wire tests | plan gap | plan 2 criteria preamble |
| P7 | no criterion covers M3.9 | plan gap | plan 2 criteria |
| P8 | C19 is not decidable as written | plan gap | plan 2 C19 |
| P9 | C14's recursive walk needs a token list + `final` | plan gap | plan 2 C14 |
| P10 | E3 must filter typicals to the task's sections | free choice → delegate | plan 2 T4 |

---

## 5. Blocking findings

### B1 — `divide_production_budget`'s return contract for grouped units is undetermined, and E2 breaks on the obvious choice

`get_task_budget_allocations.py:231` passes `division["steps"]` straight into
`serialize_budget_allocations`, which builds one wire row per **step**
(`division_serializers.py:51`, `:30-40`). T2 says the allocator "receives one unit per
section"; T3 says E2's shape is unchanged. Nothing says what the function *returns*.
`_step_result` (`budget_division.py:195-213`) emits `step_id` / `section_name_snapshot` /
`typical_worker_seconds` — it cannot serve a section row, which additionally needs
`order_list`, `state`, `state_entered_at`, `step_count`, `step_ids`, `section_name`.

**What would ship:** the natural implementation replaces `["steps"]` with section rows;
E2 then serializes sections as steps, `step_id` becomes a `wsec_…`, and C20's key-set
assertion still passes because the *keys* are unchanged. Wrong ids on a shipped endpoint,
green suite.

**Proposed wording (plan 2 T2):** *"`divide_production_budget` returns BOTH keys:
`sections` — one row per allocated/excluded group, carrying `working_section_id`,
`allowance_seconds`, `worked_seconds`, `share_state`, `step_ids`, `step_count`; and
`steps` — one row per non-deleted step, keys byte-identical to today, values per M3.5b.
`steps` remains the key E2 reads. Both are produced inside `budget_division.py`; neither
service computes an allowance (HC-6)."* Note this settles the master plan §4:81-84
ambiguity ("E2 becomes a consumer that splits its section share") against C19 — the split
lives in the domain module, not in E2.

### B2 — a closed step's per-step allowance is undefined, and the literal reading regresses every finished card → card 1

M3.5b (`intention.md:722-731`) says: *"If a section has no open step, each closed step
displays its own worked seconds and the slice is reported at section level only."*

Three problems, in order of severity:

1. **E2 has no section level.** Its payload is a flat `steps[]` array
   (`intention.md:361-375`); there is nowhere to report a slice. So for a section with no
   open step, the rule instructs E2 to report a number it cannot report.
2. **Measured reach:** 45 of the 50 multi-step groups have no open step (44 ×
   `{completed,completed}`, 1 × `{completed,completed,completed}`) — 9× more common than
   the `{completed,pending}` case D11a was designed for (5 groups). Add the 1668
   single-step groups whose only step is closed, and the branch governs **most rows in
   the database**.
3. **It contradicts P-AGREE (C12).** If closed steps report their worked seconds, Σ of a
   no-open section's step allowances = Σ worked ≠ the section slice. C12 is then
   unsatisfiable on 45 real groups.

It also collides with **P-STABLE** (`intention.md:315-319`: *"a completed step keeps its
full slice however far under or over it landed"*) — under any reading where a closed
step's allowance becomes its worked seconds, `left` is 0 and a finished overrun reads
`on_track`, losing exactly the signal D11 was chosen to surface.

**Proposed wording (intention §12.5 M3.5b, replacing the current paragraph):**
*"Within a section, each **closed** step is allowed exactly its own worked seconds. The
section's **open** steps share the remainder — `slice − Σ closed worked seconds` —
distributed by the same largest-remainder method and tie key `(sequence_order ASC NULLS
LAST, client_id ASC)` used for steps in M2. If the section has **no** open step, the
remainder is allowed to its **governing step** (M3.4 — its most recently closed step,
same tie-break). Σ of a section's step allowances therefore equals its slice exactly, in
every branch (P-AGREE)."*

Consequences of that wording, all verified by running it:
- a section with one step: that step is governing → allowance = worked + remainder = the
  **whole slice**, i.e. **byte-identical to today** on the 98.2% case (item 4's demand);
- `{completed, pending}`: pending gets `slice − first pass` = D11a's intent, unchanged;
- `{completed, completed}`: the later one absorbs the remainder; Σ = slice;
- multi-open: unchanged largest-remainder split → phase-1 rows :25, :72, :208 stay
  byte-identical (measured).

### B3 — the open step's allowance can be negative, and the frontend divides by it → card 2

Measured: section slice 60 s, one closed step burned 100 s → open step allowance
**−40**. §12.7's example shows `allowance_seconds: 3600`; §6.2 of the frontend handoff
documents only **`left_seconds`** as negative-allowed
(`HANDOFF…20260816.md:296`), and §8 specifies *"Progress bar fill =
worked_seconds / allowance_seconds"* — a non-positive denominator draws nothing or draws
backwards. The contract must state which of clamp-at-zero (breaks P-AGREE's exact sum) or
allow-negative (needs a frontend rule) applies. Card 2 recommends allow-negative plus the
rule.

### B4 — "exclusion decided at the allocated unit" silently reverses D8 → card 3

`intention.md:715-720` moves `C` from *the excluded steps' seconds* to *the excluded
groups' seconds*. Consequences, measured:

- `test_deleted_skipped_step_is_outside_budget_universe_but_live_skipped_is_charged:201-202`
  asserts `charged_seconds == 120` and `distributable_seconds == 480`; these become
  **0** and **600**. That test exists to prove §9's two-doors boundary (*"a step skipped
  via `force_task_ready` … appears as excluded with its seconds charged into `C`"*,
  `intention.md:450-452`) — under the new clause the claim is simply false for any section
  that still holds a live step.
- §4's consequence table row *"force task ready → skipped, non-deleted → excluded;
  worked time charged into `C`"* (`intention.md:294`) becomes false.
- D8's stated purpose — *"surviving allowances never promise time a failed step already
  spent"* (`intention.md:243-245`) — is lost whenever the failing section has no open
  step left: the seconds are charged neither to `B` nor to any sibling's slice.

**A second, independent undetermined decision hides inside this one:** does D11a's
residual subtract an *excluded* step's worked seconds, or only a *completed* one's?
Measured on `…excluded_consumption…:36` — subtracting the excluded step gives
600/600, not subtracting it gives **1800/1800**. Three-fold difference, no contract.

**Proposed wording (intention §12.5, replacing the "Exclusion is decided at the allocated
unit" paragraph):** *"D11 changes the **weighting** unit, not the **charging** unit.
`C` remains Σ `total_working_seconds` over the non-deleted `skipped/cancelled/failed`
steps, exactly as in M2 — §4's consequence table stands unchanged. A section group
carries a weight unless **all** its non-deleted steps are excluded, in which case it is
weightless and its row reports `share_state: "excluded"`. Because an excluded step's
seconds are already charged against `B`, M3.5b's residual subtracts only the section's
**completed** steps' worked seconds — never an excluded step's, which would charge them
twice."*

This is the wording that keeps five phase-1 assertions byte-identical (§3 column (ii)).

### B5 — the multi-open split's weights are unstated

§12.10 row 5 and M3.5b say *"distribute the residual across open steps by the same
largest-remainder method and tie key"* — the **method** and the **tie key**, never the
**weights**. Within one section all steps share one typical, so equal weights is the only
sensible reading, but "the same method" could equally be read as re-weighting by typical
(identical result) or by remaining typical (different result). Phase-1 rows :25 and :72
depend on it: equal weights keep them byte-identical; anything else moves them. State
"equal weights" explicitly. (Rule 5: no adjectives for mechanisms.)

### B6 — the grouped-unit remainder tie key is uncontracted, and a mismatch breaks P-AGREE by ±1 second

M2 contracts the step tie key as `(sequence_order ASC NULLS LAST, client_id ASC)`
(`intention.md:269`). For section units, `sequence_order` does not exist and `client_id`
is not the section's identity. Nothing in §12.5 or the naming registry says what the key
is. Two plausible choices, and both are reachable:

- **section id ASC** — what `_sort_key` (`:72`) yields for free, needs no extra data;
- **M3.2's key** `(order_list IS NULL, order_list, name, working_section_id)` — the
  render order, but `name`/`order_list` are not available to E2 without a new query.

**What would ship:** E3 (which loads sections anyway) uses M3.2's key; E2 (which does
not) uses section id. On any task whose `distributable_seconds` does not divide evenly by
the weight sum — i.e. most tasks — the leftover second lands on a **different section** in
the two surfaces, so E3's section `allowance_seconds` and Σ of E2's step allowances for
that section differ by 1. **C12 fails, and P-AGREE — the property this phase exists to
establish — is violated by exactly the amount nobody looks at.** The two orders provably
differ on live data (§2: `weaving` 8th by M3.2, 11th by id).

**Recommendation:** contract **`working_section_id` ASC** as the grouped-unit remainder
tie key, in `budget_division.py` for both callers, and state in the intention that the
remainder order is deliberately *not* the render order (M3.2) — because requiring the
render order would force E2 to load `order_list` it has no other use for (and would break
`…constant_query_count…:196`). Add a criterion asserting both surfaces assign the
leftover unit to the same section on an indivisible fixture.

### B7 — "closed" / "non-closed" is the pivot of M3.4 and M3.5b and is never defined

M3.4 says *"its single non-closed step"*; M3.5b says *"the section's closed steps"*.
Neither says whether that means `state NOT IN TERMINAL_STEP_STATES` or
`closed_at IS NULL`. Verified against the real state machine:

- `TERMINAL_STEP_STATES = {COMPLETED, SKIPPED, FAILED, CANCELLED}`
  (`domain/task_steps/constants.py:4-9`);
- `closed_at` is set **exactly** on entering one of those, at both writers
  (`transition_step_state.py:369-371`, `_step_transition_core.py:224-225`) plus
  `remove_task_step.py:133` (which also soft-deletes → out of universe) and
  `finalize_pending_step_completion.py:130`;
- a terminal step can never transition again (`transition_step_state.py:150-152` raises),
  so **no state is closed-yet-reopenable**. `force_task_ready` only moves
  `pending/working/paused/blocked → SKIPPED` (`force_task_ready.py:74-79`), i.e. into
  terminality, never out;
- **no state is non-closed yet terminal**: `BLOCKED` is non-terminal and, per
  `force_task_ready.py:70-73`, nothing writes it today.

So the two definitions coincide *by construction of the writers*, and measured: 0
disagreeing rows of 2833. **But `intention.md:210-213` explicitly contemplates the
malformed row** — *"A `completed` step with `closed_at IS NULL` never contributes … 0 of
1703 completed rows are affected today"*. On such a row the `closed_at` reading would
classify a finished step as the section's live step, making it the governing step (wrong
`state` on the widget) and handing it M3.5b's remainder.

**Ruling:** `state NOT IN TERMINAL_STEP_STATES` is the faithful proxy for "live" —
it is what the writers key off, it is total (every row has a state; `closed_at` is
nullable), and it cannot be defeated by a missing timestamp. Contract it by name, importing
`TERMINAL_STEP_STATES` rather than re-listing the four states (one-copy rule). Per the
mechanism-inventory waiver's condition this is a **gate failure routed to the intention**,
not a note — it is an admission filter in charter rule 6's class.

### B8 — five live steps point at a soft-deleted working section, and M3.1 has no answer for them

Measured: **15** distinct sections are referenced by non-deleted steps; **14** are live
and **1** is soft-deleted — `sanding`, `client_id wsec_01KVX0G12ZSNWRPRBM67CF1HCR`,
`order_list = 4`, referenced by 5 live **pending** steps across 5 tasks.

M3.1 (`intention.md:659-661`) defines the section set from the **steps**, with no
`WorkingSection.is_deleted` filter. But every source of a section's name, order and
typical is `typical_times_statement`, which filters `WorkingSection.is_deleted.is_(False)`
(`get_working_section_typical_times.py:58-61`). So the deleted section yields no row.

**What would ship**, depending on how the implementer joins:
- inner-join on the typicals dict → **the section disappears from `sections[]`** while its
  pending step still carries a budget weight; Σ `sections[].worked_seconds` no longer
  equals `actual_worker_seconds` → **P-COVER (C11) is violated on 5 production tasks**,
  and 5 tasks silently lose a pipeline row that has real outstanding work;
- outer-join → the row appears with `order_list: null`, so **NULLS LAST sorts a
  position-4 section to the bottom of the widget**, below photography (1000).

Today the seconds at risk are 0 (all five steps are `pending`, worked 0), so P-COVER
would not yet fail numerically — it fails the moment anyone works one of those steps.

**Proposed wording (intention §12.5 M3.1, and a row 12 for §12.4):** *"The section set is
the distinct `working_section_id` over the task's non-deleted steps, **including sections
that have since been soft-deleted** — 1 of the 15 sections referenced by live steps is
soft-deleted today, holding 5 live steps. Section attributes are resolved by an OUTER
join: a section absent from the live-section read renders `section_name: null`,
`order_list: null`, and a `typical` object with `typical_worker_seconds: null,
sample_count: 0`. `section_name_snapshot` (M3.9) is unaffected — it comes from the step —
so the row still has a label. A deleted section sorts last under M3.2's NULLS-LAST rule;
this is accepted, because it holds no future work by definition."*

Add a criterion: a task with a step on a soft-deleted section still yields its row, and
P-COVER holds.

### B9 — nothing in T4's composition supplies `order_list`

`typical_times_statement` selects `WorkingSection.client_id`, `name`, `sample_count`,
`typical_worker_seconds` (`get_working_section_typical_times.py:47-53`) — **not
`order_list`**. It is required twice by §12.7: as the payload field `order_list` and as
M3.2's primary sort term. T4 lists the statement as E3's typicals source and stops there.
The implementer must either add a second `WorkingSection` select in E3 (extra query, no
phase-1 file touched) or add `order_list` to the shared statement's select **and**
`group_by` (`:62`), which edits a phase-1 file and changes E1's statement. Both are
defensible; neither is chosen, and the second silently widens E1's grouping.
**Recommendation:** a separate `WorkingSection` select in E3 over the task's section ids —
E3 already needs the outer-join tolerance of B8, and E1's statement stays untouched.

### B10 — T6's "one row each" turns the second route mirror red

`tests/unit/routers/api_v1/test_item_economics_router.py:126-139`:
`test_budget_status_route_is_available_to_all_roles` iterates `_ALL_ROLE_ROUTES`, returns
early for `budget-allocations`, and otherwise asserts
`calls[0][0] is item_economics.get_task_budget_status_worker` for worker/seller. Adding a
`production-time` row — exactly what T6 and C18 instruct ("additive edits only, one row
each") — sends the new path down the budget-status branch and the assertion **fails for
worker and seller**. The test body needs a third branch asserting
`calls[0][0] is item_economics.get_task_production_time` (service-identity rule, r1
lesson 3).

**Why this is blocking rather than cosmetic:** the implementer meets a red test the plan
told them would be green, and the cheapest repair is to loosen the dispatch — a
**no-weaker-assertions** violation (r2 lesson 1) in an HC-1a-protected v1 file. State the
required edit in T6, and note that only `test_phase9_item_economics_route_mirror.py` has
count assertions (`:125-126`, verified 24 → 25); this file has none.

### B11 — `latest_state_record` is a lazy relationship; M3.4 needs it eagerly

`state_entered_at` comes from `latest_state_record.entered_at`
(`task_step.py:117-121`, a `relationship` with no eager default). Every existing consumer
loads it explicitly — `list_task_steps.py:41`, `tasks.py:655`,
`step_record_payload.py:241`, `steps_list_payload.py:57`, all
`selectinload(TaskStep.latest_state_record)`. T4's composition list omits it. A bare
attribute access on an `AsyncSession`-loaded instance raises
`MissingGreenlet` — a 500, not a wrong number, on the endpoint's happy path. Name the
`selectinload` in T4. (`pause_reason` is not needed — E3 exposes no pause reason.)

### B12 — `final.percent_consumed` has no source column

M3.8 (`intention.md:754-759`) specifies `final` as *"the **time-only** fields of that
row"*, listing `percent_consumed`. `ItemCostResult` has no such column
(`item_cost_result.py:23-32`: `actual_worker_seconds`, `actual_worker_minutes`,
`consumed_cost_minor`, `variance_worker_minutes`, `variance_cost_minor`,
`task_closed_at`, `task_state_snapshot`, `calculation_version`, `computed_at`). v1 solved
this by **injecting the live percentage** into the frozen object
(`serializers.py:193`, `:243-249` — `percent_consumed=status.percent_consumed`), so on
the existing surface `result.percent_consumed` is *not* frozen. C17 ("`final` populated
from the frozen result") is therefore unsatisfiable as worded for that one field.

**Recommendation:** follow the v1 precedent (inject `budget.percent_consumed`) and amend
M3.8 to say so explicitly, plus amend C17 to "every `final` field except
`percent_consumed` is read from the frozen row; `percent_consumed` is the live figure,
per the v1 precedent, and equals `budget.percent_consumed`". Note also (N9) that
`item_cost_results` is **empty** in the whole database, so this branch is fixture-only.

---

## 6. Contract amendments (no owner needed)

### P1 — P-PROP and P-STABLE are per-step statements that D11a makes false per step

T2 requires the handoff to restate P-SUM3 / P-PROP / P-DET / P-FOLLOW / P-STABLE "as
verified, not assumed" at the new unit. Two of them cannot be verified as written:

- **P-PROP** (`intention.md:306`) — *"two allocated steps with typicals in ratio k have
  allowances in ratio k"*. Under D11a a step's allowance is `slice − siblings' worked`, so
  the ratio holds at the **section** level only. Measured: the phase-1 integration test
  asserts precisely the per-step ratio and breaks under reading (i) (§3).
- **P-STABLE** (`intention.md:315-319`) — *"what does NOT move allowances is consumption
  inside an unchanged step set"*. D11a makes the open step's allowance a **function of a
  sibling's consumption**. That is deliberate — it is the whole point of "12m left" — but
  it is consumption-based reallocation inside a section, which is what P-STABLE forbids.

**Proposed wording (intention §12.6, new bullets):** *"P-PROP and P-STABLE hold at the
**section** unit and only there. Section slices are proportional to typicals and do not
move with consumption. **Inside** a section, D11a deliberately reallocates by
consumption: a closed pass's spend reduces what the open pass is allowed. This is the
only place in the contract where consumption moves an allowance, and it is bounded by the
section — D6 still stands at the task level."*

### P2 — `allocation_method` must change (the ruling the coordinator delegated)

**For keeping `static_proportional_v1`:** the derivation family is unchanged — static,
proportional, typical-weighted; HC-5's own examples of label-worthy change are *method*
changes (configured typicals, per-category medians, dynamic reallocation), and D6 reserves
the next `allocation_method` value for dynamic reallocation, so spending a version now
leaves the real change without a name. §12.5:734-736 currently asserts exactly this.

**For changing it:** HC-5 makes the label *the consumer's cache key*
(`intention.md:69-72`). Every per-step number on the worker card can move — measured:
3200/1600 → 2800/2000 on the existing two-section fixture — while the label, the shape and
the key set stay identical. A client holding a cached `static_proportional_v1` payload
beside a fresh one has **no way to tell them apart**, which is the precise failure the
label exists to prevent. And the unit is not a detail: the same typicals now produce a
different answer, and a step's number now depends on its siblings' consumption, which the
old label positively denied (P-STABLE).

**Ruling: change it.** The cost is one line — the literal lives at
`budget_division.py:17` and is echoed only in docs and in one *unasserted* test fixture
dict (`test_budget_division_routes.py:132`); nothing in `Application_contracts` publishes
it and no frontend code consumes it yet (the frontend build waits on this pipeline by
owner decision). Waiting until a consumer exists makes the same edit breaking.

**Recommended value: `static_proportional_section_v1`** — not `_v2`. It names *what*
changed (the unit), it keeps `dynamic_*` free for D6 so nothing is spent, and an opaque
`_v2` tells a consumer only that something changed. Amend §12.5:734-736 and the naming
registry (master plan §4:51).

**Required criterion (new):** assert the literal string, in the unit test, plus that E2
and E3 emit the identical value. Today **no test pins the value at all** — the only
assertion is `row["allocation_method"] == ALLOCATION_METHOD`
(`test_budget_allocations_query.py:140`), which follows the constant wherever it goes. A
cache key that no test pins can drift silently, which defeats its purpose.

### P3 — §12.4 needs the four counts of §1 rows 11–14

Its own preamble is the argument: *"The `sequence_order` lesson from projection r0 (a
contract column that was NULL on 3032/3032 rows) is why each of these is a count."*
Row 11 (45 of 50 multi-step groups have no open step) is the branch B2 turns on; row 12
(1 of 15 referenced sections is soft-deleted) is B8; rows 13–14 are N2 and N9. Add all
four, with the caveat that §12.4's headline "0 groups with 2+ non-closed steps" is true
but describes the *rare* branch while row 11 describes the *common* one.

### P4 — the single home for `status` + `item_binding` (explicit delegation)

The prompt's premise is half right. **`status`** is derived in E2 inline
(`get_task_budget_allocations.py:179-201`) and again in `get_task_budget_status.py:112-127`
and `get_task_budget_status_worker.py:36-52`. **`item_binding`** is not in E2 at all — it
is a verbatim one-line duplicate across
`get_task_budget_status.py:111` and `get_task_budget_status_worker.py:35`, whose
duplication carries a deliberate comment (*"Keep this literal boundary local to the worker
service. It is a separate money-redaction producer and must not inherit a future manager
change"*). So E3 would be the **third** `status` derivation and the **third**
`item_binding` copy.

**Ruling: no extraction in phase 2, and no third copy either.** E3 calls
`get_task_budget_status(ctx)` directly. It already returns `status`, `item_binding`,
`actual_worker_seconds`, `actual_worker_minutes`, `remaining_worker_minutes`,
`percent_consumed`, `allowed_worker_minutes` and `result` — i.e. **every field M3.7 and
M3.8 need**, computed by the calculator functions M3.7 names, plus the 404 on the tenant
boundary (`:59-60`). E3 then computes literally no arithmetic, which is the strongest
possible reading of HC-6/M3.7, and adds zero copies. Extraction is a real improvement but
its blast radius crosses HC-1's v1 perimeter — record it as a follow-up, do not do it here.

Three consequences the plan must state:
- E3 calls the **manager** variant for all four roles (never the worker variant): one code
  path is what makes P-FLAT structural rather than tested. The variant carries monetary
  fields in-process; E3's serializer never emits them, and C14's recursive walk is the
  guard.
- E3 gains a declared dependency on a v1 read model. Say so in the frontend handoff and
  the graph delta.
- P-COVER then compares two independently computed sums — SQL `SUM` over non-deleted steps
  (`get_task_budget_status.py:138-147`) versus the Python sum over the rows E3 loaded —
  which is a **stronger** test than one number compared to itself. Keep it that way.

### P5 — C3's fixture cannot be built

C3 requires "identical `order_list` AND identical `name` → `working_section_id` decides".
`uix_working_sections_name_active` is a partial UNIQUE index on `(workspace_id, name)
WHERE is_deleted = false` (`working_section.py:50-57`, confirmed in
`pg_indexes`), so two live sections in one workspace **cannot** share a name, and two
sections in different workspaces never co-occur in one task. The `working_section_id`
backstop is therefore unreachable through the database. Keep it as defence in depth, but
C3 must become a **pure-function** criterion on `_section_sort_key` with hand-built
inputs — and the plan should say so, since charter rule 3 otherwise reads as forbidding it.

### P6 — C5, C7 and C10 cannot be what the criteria preamble demands

The preamble says *"Every criterion: an automated test, run against the configured DB"*.
C5 (the 180-minute example), C7 (multi-open tie-break, "fixture-only") and C10 (Σ
allowances == `distributable_seconds`) are pure-function properties. C10 additionally
cannot be checked from the wire at all: **`distributable_seconds` is not a field of
§12.7's payload**, nor of E2's. Amend the preamble to "DB-backed unless the criterion is a
property of the pure allocator, which is proven by a unit test on it", and mark C5/C7/C10
as unit rows.

### P7 — no criterion covers M3.9

T5 says "Both names per M3.9" and M3.9 states a rule the frontend must not coin-flip
(render the snapshot; reserve the live name for pickers). No C row tests it, and the two
values are **identical on all 2833 live steps** (measured: 0 renames), so a test that does
not force a rename cannot distinguish them — and an implementation that emits the live
name twice would pass every other criterion. Add: rename the section after the step
exists; assert `section_name` == the new name and `section_name_snapshot` == the old, on
the same row. (Letter-verification rule, r3 lesson 1.)

### P8 — C19 is not decidable as written

*"Assert by import/grep that no second function computes an allowance"* has no mechanical
form: "computes an allowance" is not a syntactic property. Proposed wording: *"Assert
that (a) the set of modules importing `divide_production_budget` is exactly
{`get_task_budget_allocations`, `get_task_production_time`}; (b) neither service module's
source contains `Fraction`, `ROUND_HALF_EVEN`, `largest`, or `//`; (c)
`budget_division.__all__` exports exactly one allocator name."* Each clause is a real
assertion, and (b) is the one that bites if the split leaks out of the domain module.

### P9 — C14's monetary walk: what it must traverse, and where the money would come from

The keys in §12.7's payload that could carry money if a nested object were later widened:

| Depth | Object | Money that would appear, and from where |
|---|---|---|
| 1 | `budget` | `production_budget_minor`, `consumed_cost_minor`, `variance_cost_minor` — the three fields `TaskBudgetStatus` already holds (`get_task_budget_status.py:42-45`) and that P4's reuse brings in-process |
| 1 | **`final`** | `consumed_cost_minor`, `variance_cost_minor` — emitted by the v1 sibling builder `_serialize_result(include_monetary=True)` (`serializers.py:207-217`). **Reusing `serialize_item_cost_result` instead of writing a time-only builder puts money at depth 2 with one import.** Highest-risk object in the payload |
| 2 | `sections[].typical` | none today; a future manager-configured typical (D2) is the plausible widening |
| 2 | `sections[]` | none today; a per-section cost line is the plausible widening |

So the assertion must recurse through **dict values and list elements at every depth** —
the existing check is the decorative form: `test_budget_division_routes.py:163-168`
inspects only top-level keys and `payload["steps"][*]` keys, and matches only the
substrings `money` / `minor`. Proposed wording: *"Collect every key at every depth
(recursing dicts and lists). Assert the collected set contains no key matching any of
`_minor`, `cost`, `price`, `currency`, `money`, `valuation`. The named mutation:
returning `serialize_item_cost_result(result)` for `final` must turn this test red."*

### P10 — E3 must filter typicals to the task's sections (explicit delegation)

`typical_times_statement` returns **every** non-deleted section of the workspace — 14
today, none of them scoped to a task. C21 requires the opposite. Nothing says where the
filter goes (SQL `WHERE ... IN` vs a Python dict lookup keyed by the task's section set).
Either is correct; delegate it in writing so the freedom is granted rather than taken.

---

## 7. Notes

- **N1 — route declaration order is a non-issue here; the P7 hazard does not apply.**
  Proven, not reasoned (`…/scratchpad/shadow.py`): with the fixed
  `/tasks/budget-allocations` declared first and with the parameterized
  `/tasks/{task_client_id}/production-time` declared first, **all four probe paths resolve
  identically to the correct handler in both orders**. The two paths differ in segment
  count (2 vs 3), so neither can shadow the other — unlike E1's P7 case, where
  `/{working_section_id}` and `/typical-times` were both single-segment. T6's instruction
  (declare it beside `budget-status`) is safe; its stated rationale ("therefore below the
  fixed path") implies a necessity that does not exist. Worth knowing so a future reader
  does not treat the ordering as load-bearing. Incidentally
  `/tasks/{task_client_id}/evaluations` (`:331`) is already declared **above** the fixed
  batch path, so the comment at `:345` is already only half true.
  Counts verified: 24 `@router.get/post/...` decorators, `_EXPECTED_ROUTES` length 24
  (`:125-126`), README Quick Index 24 item-economics rows → all three become 25.
- **N2 — the render-order authority changes, and that is a fix, not a regression.**
  The frontend handoff §4 names *"Call 2 `sequence_order`"* as the row order and §3 claims
  the step list is *"already ordered by `sequence_order` (nulls last)"*. Measured:
  `sequence_order` is **NULL on 2833 / 2833** live steps, so today's row order is decided
  entirely by the secondary key — the widget's order is effectively arbitrary. M3.2's
  `order_list` ordering is strictly better and encodes the real workshop pipeline. The
  handoff rewrite (master plan §9 already lists "step ordering authority" as a gap) must
  stop citing `sequence_order` and state that E3's array order is authoritative (HC-11).
  Corollary for B6: `min(sequence_order)` is useless as a grouped-unit tie key.
- **N3 — a third ordering expression appears.** `_sort_key`
  (`budget_division.py:72`) is already duplicated inline at
  `get_task_budget_allocations.py:203-206`; T1 adds `_section_sort_key`. Three ordering
  expressions for two orders. Not phase-2's to fix, but the one-copy rule's trigger is
  visible — record it so it is not rediscovered as a finding.
- **N4 — do not annotate the new route's return type.**
  `test_item_economics_routes_declare_no_response_model` (`:182-183`) asserts every route
  has `response_model is None`; FastAPI infers it from the return annotation.
  `budget-status` sets `response_model=None` explicitly (`item_economics.py:360`) — match
  the neighbours.
- **N5 — E2's query count is pinned at 11** (`test_budget_allocations_query.py:196`).
  T3's split needs no new data (state, `closed_at`, `total_working_seconds` are all on the
  already-loaded rows), so 11 must hold. If any repair of B9 routes `order_list` through
  E2, this test breaks — a useful tripwire, and a reason to prefer B9's recommendation.
- **N6 — the money check precedent.** `test_budget_division_routes.py:163-168` is the
  decorative form P9 replaces. Cite it in the fix prompt so the implementer sees what not
  to copy.
- **N7 — HC-10, element by element, against §12.7.** All of §4's eleven mockup elements
  and all of §8's eight card elements render with **no client-side join**, with two
  qualifications:
  - §4's *"Row order → `sequence_order`"* becomes the array order (N2) — E3 carries no
    `sequence_order`, deliberately;
  - §5's live tick asks for rows where `latest_state_records.state == "working"` **and
    `exited_at == null`**. E3 exposes `state` and `state_entered_at` but not `exited_at`.
    Verified sufficient: the latest record's `state` mirrors the step's on 2833/2833 and
    its `exited_at` is NULL on 2833/2833 (it is NULL by construction — the transition
    writers close the *previous* record and point `latest` at a fresh one with
    `exited_at=None`). So `state == "working"` alone is the correct predicate, and §6.5's
    per-section tick works off `state_entered_at`. Also confirmed present for §2's empty
    state: `status` (twelve-value) and `item_binding`, plus 404. **No HC-10 gap.**
- **N8 — a second, independent reason E2's numbers move.** M2's fallback median is taken
  over the *allocated set's* typicals (`budget_division.py:136-141`). Grouping changes the
  multiset: a task with two Upholstery steps contributed 3706 twice, now once, so the
  median a typical-less section falls back to changes. `weaving` has `sample_count = 0`
  today, so this path is live in production, not hypothetical. T7b's enumeration should
  name it as a cause alongside the double-weighting.
- **N9 — the entire allocation surface is fixture-only today.** 0 committed-current
  `item_cost_evaluations` and 0 `item_cost_results` in the whole database. Every task
  therefore resolves to a non-`ok` status, so `budget.*` is null, every `share_state` is
  `no_budget`, and `final` is always null on real data. Consequences: the reviewer cannot
  validate anything against production; C17's closed-task branch has no production
  instance; and charter rule 10 (operational reachability) is satisfied only through the
  v1 commit endpoint, which is out of this phase's scope. Record it so a later reader does
  not mistake "no data" for "no coverage needed".
- **N10 — `test_typical_times_query.py`'s 7 tests are unaffected.** M1 is untouched by
  D11; the file contains no allowance, `share_state`, or `left_seconds` reference
  (verified by grep). Stated so T7b's enumeration is provably closed over all 26 tests.
- **N11 — baseline is green before the phase starts.** The six phase-1 files run
  **140 passed** in 2.50 s on the configured DB, so every "this changes" in §3 is measured
  against green, not against unknown.

---

## 8. Exit gate

Verdict **AMENDMENTS_REQUIRED**: 12 blocking, 10 contract amendments, 11 notes, 3 owner
cards. Four blocking items (B2, B3, B4 and the `order_list`/section-set half of B8) and
one amendment (P3) route to the **intention**; the rest are plan amendments. Per the
mechanism-inventory waiver's standing condition, **B5, B6 and B7 are gate failures** —
three mechanisms in charter rule 6's class (an ordering key, an integer-division remainder
key, and an admission filter) operating with no contract — and are recorded as such, not
downgraded.

The implementer prompt should not be compiled until every ledger row is routed. Two of the
three owner cards (1 and 3) change what the tests must assert, so compiling before they
are answered would produce a prompt whose T7b enumeration is wrong.

**Recommended order of work for the coordinator:** relay the three cards verbatim →
fold the answers into intention §12.5 with B4's and B2's proposed wording → apply P1/P2/P3
to the intention → then apply B1/B5/B6/B7/B8/B9/B10/B11/B12 and P4–P10 to plan 2. The
answers to cards 1 and 3 determine which column of §3's table becomes T7b's work list.

---

## Appendix — projection sketch (NON-AUTHORITATIVE, do not hand to the implementer)

The three scratch scripts named in the write perimeter are discarded per doctrine. Their
only surviving output is the measured numbers quoted inline above: the 72/36/72 vs
51.4/25.7/102.9 re-derivation, the 21/20/20 largest-remainder check, the −40 negative
allowance, the 600-vs-1800 residual ambiguity, the 2800/2000-vs-3200/1600 divergence, and
the both-orders route-resolution proof. No skeleton, signature or file sketch from this
session is offered as guidance — the implementer derives the code from the amended
artifacts, which is what the fresh-session rule exists to protect.
