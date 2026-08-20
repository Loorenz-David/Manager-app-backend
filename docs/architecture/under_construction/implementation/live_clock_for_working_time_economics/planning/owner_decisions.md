# Owner decisions — live_clock_for_working_time_economics

Verbatim register. Cards are relayed exactly as authored; answers are recorded with
date and the owner's own words where they carry nuance.

---

## Settled during intention shaping (owner conversation, 2026-08-19)

**D1 — backend-owned, centralized.** One computation home for the live figure,
consumed by every client. Owner, verbatim: *"my intention is for the system to use
this live clock centralized so that any client ( the frontend, or a scheduler ) can
make correct decisions"* — and, on ownership: *"more importantly, when i build
machinery to trigger signals given that a wroking section is approaching the allowed
time those services will need that live clock also, so clearly this is a backend
implementation that needs to happen."*

Context: the frontend's escalation handoff
(`HANDOFF_TO_BACKEND_production_time_live_budget_clock_20260819`) had already refused
to solve this client-side, citing our own D16 one-rule-home reasoning back at us. D1
closes the loop: the rule stays server-side and gains a live evaluation.

**D2 — the mechanism is settled-plus-open-interval, credited by the settlement
sweep.** The owner proposed the mechanism himself: *"can't we build a live clock that
says take the work time ( which means take the sum of all the work time of the close
records ) and if there is an open working record add the entered at until now to that
calculation … it continues to be cheap over time as records pile up."* The shaping
conversation walked through the four cases where the raw `now − entered_at` form
fails (two workers in one section; a divisor that changes mid-interval; a divisor
living on another task; closed records shaping the open one's past), and the owner
accepted the refinement to the concurrency-averaged share computed by the existing
settlement sweep — the same rule, evaluated earlier. Owner: *"sounds greate."*

Recorded rejection, so it is not reopened: dividing by the number of open records on
the section or task. Concurrency is a property of one worker's attention, never of a
container's open-record count; the corrected division — per worker, per timeline
segment, across all tasks, including closed overlaps — *is* the existing
`averaged_seconds_by_record`, so no second formula is ever written.

**D3 — the live/settled dividing line.** *"What is happening" is live; "what
happened" is settled.* Live basis on the three present-tense read surfaces
(production-time, budget-status both faces, budget-allocations — D5 ratified all four surfaces);
settled and untouched: the `final` block, `item_cost_results`, daily analytics
rollups, `task_steps.total_cost_minor`, and every persisted column. Nothing live is
ever persisted. Accepted by the owner with the blast-radius explanation ("sounds
greate" to the consolidated walkthrough).

**D4 — honoured from the frontend handoff (their explicit requests, adopted as
HC-4):** response shapes frozen; no new field; no `server_now` / `as-of` timestamp —
their smoothing anchors to time-of-receipt precisely so no client clock is ever
compared to a server clock.

**D7 — the live figure drops on disowning events, by design (owner, 2026-08-20 —
coordinator review finding 2, ratified as intended behaviour).** Owner, verbatim:
*"yes i'm aware of that, the whole point of marked inaccurrate is exactly that, to
remove data that the user can acknowledge as incorrect, so that is something that all
users can account for, an open record that it is marked as inaccurate will be
removing that time passed as it has poisoned the surrounding timings like it
currently does today when skippiing inacurrate times ( later i will add ways to
recover that time )."*

Recorded consequence: §6's monotonicity is scoped around the disowning events
(mark-inaccurate on a running record — `mark_step_time_inaccurate` has no `exited_at`
filter and sets the step-level flag too — and record/step deletion); the §5.4
closeout handoff tells the frontend the figure drops by the whole disowned share at
once and that smoothing must snap down, never clamp. Time-recovery tooling is future
work, out of scope.

**Round-3 context note — finding 3 (window anchor).** The owner supplied the
operational safeguards during disposition, verbatim: *"at midnight utc they close,
this company im building the app doesn't work on night … when the users log out they
auto close open records also."* Both verified in code
(`services/tasks/users/auto_clock_out_open_shifts.py`;
`_clock_worker_shift.py:200-224`). The `min(entered_at)` anchor is therefore
defense-in-depth, not a live-bug fix — recorded so the gate does not re-litigate the
severity.

---

## Round 1 cards — ALL ANSWERED (owner, 2026-08-19)

Relayed to the owner verbatim; answered in one pass. Owner, verbatim: *"about the two
owner cards both recomendations are the correct answers."*

Both recommendations were accepted, so each card below is followed by its recorded
decision (D5–D6) and the consequence folded into the intention. The cards are
preserved unedited — the rejected branch is what stops a later session from reopening
a settled question.

### Card 1 — Do workers see their own numbers ticking, in this same release?

**Question.** When the live clock ships, do the worker-facing surfaces — the worker
budget-status face and the step cards — go live together with the manager widget, or
does v1 scope liveness to manager/admin surfaces only?

**Story.** Jonas is 25 minutes into a 3-minute sanding allowance. The manager's
widget now says "over share" in red, live. Jonas's own card still says "0m of 3m —
on track", because his surface kept the settled basis. The manager walks over; Jonas
holds up his screen: "says here I'm fine." Every alert your future scheduler sends
him will look like a false alarm, because the screen he checks disagrees with the
clock that fired it.

**Branches.**
- *Everything live in v1:* one truth on every screen; workers watch their own time
  move against the allowance in real time.
- *Manager-only in v1:* smaller release, but the manager/worker split-brain above is
  shipped on purpose, and the scheduler cannot honestly alert workers until v2.

**Recommendation.** Everything live in v1 — the split-brain is the exact defect this
pipeline exists to remove, and D1's "any client" wording already points here.

**On silence.** The gate holds; no surface list is assumed.

**Trace.** Intention §4.1 rows 3–4, §9 T7, §5.4.

> **ANSWERED — D5 (2026-08-19): everything live in v1.** All four §4.1 surface rows —
> production-time, budget-status manager face, budget-status worker/seller face,
> budget-allocations — ship live in the same release. Folded into intention §4.1 and
> the round-2 changelog.
> **Consequence created by the answer:** the release shape is fixed — one phase family
> delivers the shared loader and all three endpoints together; there is no
> manager-first intermediate state to plan or hand off, and the closeout handoff
> (§5.4) speaks for all three endpoints at once.

### Card 2 — Does money tick with its minutes on the manager face?

**Question.** On the manager budget-status face, `consumed_cost_minor` and
`variance_cost_minor` are derived from worked seconds times the frozen evaluation
rate. When the seconds go live, do these money figures tick too, or stay settled?

**Story.** The manager screen shows minutes and their cost side by side. With money
frozen and minutes live, at 9:25 it reads "2h 40m consumed — 1 755 SEK consumed":
the minutes include Jonas's live 25, the kronor still price only the settled 2h 15m.
Two numbers on one line, describing the same work, disagreeing — the exact one-row
two-answers defect the frontend escalated, rebuilt between a number and its price
tag.

**Branches.**
- *Money ticks:* cost is seconds × a frozen rate — same number in different clothes;
  the line stays coherent at every instant.
- *Money stays settled:* the manager face contradicts itself whenever anyone is
  working; nothing is gained, since the rate is frozen anyway.

**Recommendation.** Money ticks — it is not a second liveness decision, it is the
same number multiplied by a constant; freezing it just re-creates the defect
intra-line. (Audience unchanged: ADMIN/MANAGER only, HC-6.)

**On silence.** The gate holds; §4.1 row 2 stays undetermined.

**Trace.** Intention §4.1, §2.4 (E-B), HC-5, HC-6.

> **ANSWERED — D6 (2026-08-19): money ticks.** `consumed_cost_minor` and
> `variance_cost_minor` derive from the live M1 figure like every other
> seconds-derived field; audience unchanged (ADMIN/MANAGER only, HC-6). Folded into
> intention §4.1 row 2.
> **Consequence created by the answer:** HC-5 now holds with no exceptions — every
> worked-seconds-derived field on every present-tense surface, time and money alike,
> derives from the single per-step live figure, so T6's coherence test is one rule
> with no carve-outs.

---

## Ledger status

**Empty as of round 3 (2026-08-20).** D1–D4 settled during shaping, D5–D6 ratified by
the owner (round 2), D7 ratified from the coordinator review (round 3, all six
findings dispositioned — see the intention's round-3 changelog). No decision in this
intention is a guess. Next gate: **mechanism-inventory**.
