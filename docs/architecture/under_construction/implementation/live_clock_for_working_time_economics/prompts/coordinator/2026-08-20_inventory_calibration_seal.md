---
plan: (pre-plan, project-level)
role: coordinator (standing document — never handed to a session)
round: inventory (calibration seal)
date: 2026-08-20
project: live_clock_for_working_time_economics
---

# Calibration seal — mechanism-inventory gate

**Sealed 2026-08-20, before the gate prompt was authored.** This file records the
coordinator's own pre-gate hypotheses about where the intention's contracts are weakest.
It is NOT given to the gate session and must not be opened until the gate handoff is
consumed. Its purpose, as at the `simple_valuation_editor` gate: measure whether the
sweep finds independently what the coordinator found by reading, and whether it goes
deeper. A hypothesis found here but not by the sweep is a coordinator finding to raise
at the fold; a sweep finding not here is the gate earning its keep.

Contamination statement, for honest measurement: the prompt's scope table names
H1's and H2's **territory** — M-5 directs depth at composition and M-3 at the bound's
arithmetic — because classifying rule-6 surface is the coordinator's job and hiding a
mechanism from the inventory would defeat the gate. What the prompt does NOT contain is
any of the specific defects hypothesized below (the double-computation invisible to
every named test, the price-scenario `ctx` gap, the 2 s-vs-flat-1 s disagreement, the
three-vs-four count). H3's territory is not mentioned at all. Calibration therefore
reads: H1/H2 found = depth-directed sweep worked; H3 found = independent depth on
prose sections worked; expected-outcome mismatches = coordinator findings to raise.

---

## H1 — HC-5/HC-3's "one computation, one `now` per request" has no stated mechanism under service composition

E-P (`get_task_production_time.py:get_task_production_time`) **calls**
`get_task_budget_status` — a query service that will itself invoke the shared loader —
and then separately needs live per-step figures for `divide_production_budget`'s rows.
HC-3 says query services obtain `now` "once per request at the service boundary," but
for a composed request the boundary is ambiguous: if the callee obtains its own `now`
(or runs its own loader invocation), E-P computes the live figures **twice, at two
`now`s**. The same applies to `get_task_price_scenario.py:get_task_price_scenario`,
a shipped endpoint that calls `get_task_budget_status` with a `ctx` that carries no
clock today.

**Why it's silent:** two loader invocations microseconds apart satisfy T1 (fixed `now`
makes both identical), T2, T5, T6, and T7. T8's call-counting covers only E-A. A
double computation on E-P is invisible to every named test and only shows as cost and
as sub-second incoherence in production. The contract needs to state how `now` and the
loader output thread through nested service calls (ctx field, parameter, or
restructure), or explicitly assign that to the planner as a named decision with the
coherence requirement stated.

**Expected gate outcome:** a lettered section under §4 (or an M2 contract clause)
defining "request" and "service boundary" for composed calls, plus a T8-style
call-count criterion extended to E-P.

## H2 — §3.3's bound and T2's assertion disagree on multi-user steps

§3.3 states the no-snap bound as **"≤ 1 second per credited user"**. T2 says "assert
per-step figures agree within 1 second" — flat. A step whose open-interval history
spans two credited users can legitimately drift up to 2 s under the contract while
failing T2 as written, or T2's fixtures quietly avoid multi-user steps and never test
the per-user clause. Additionally, §2.1 describes settlement as
`int(round(Σ closed working shares))` per state — whether that sum is per-user-then-
summed or summed-then-rounded determines whether the "per credited user" qualifier is
even the right unit. The arithmetic of the bound has never been derived in the
document; it is asserted.

**Expected gate outcome:** the bound derived once, properly (who rounds what, where,
per what unit), T2's assertion form aligned with it, and a §3.2-case-1-shaped fixture
(two workers) named as the row where the flat and per-user forms disagree.

## H3 — §8's graph delta says "three projection nodes" and lists four

§8: "update the three projection nodes' descriptions" followed by four node slugs —
`projection-item-economics-task-budget-status`, `…-worker`,
`…-task-budget-allocations`, `…-task-production-time`. A sentence with a count in it
is a checklist (house rule, earned at `simple_valuation_editor` re-review r4), and
this one fails its own count. Trivial to fix, but exactly the class the gate exists to
catch — and whether all four slugs resolve against the live graph is checkable and
unchecked.

**Expected gate outcome:** count corrected; slugs verified against the graph (or the
verification named as a closeout task).

---

## What I deliberately did NOT seal

The intention's own §11 nominations (§3.3 sufficiency-of-buffer, §3.1 window, T8's
query bound) — nominated by the author, historically the sections that survive. And
the two passes already spent and verified by the outgoing coordinator (§4.3 allowance
keystone; §5.3 status-flip immunity), which the prompt licenses the session to consume
rather than re-derive.
