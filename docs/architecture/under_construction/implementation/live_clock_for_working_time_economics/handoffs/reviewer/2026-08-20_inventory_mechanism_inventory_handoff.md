---
plan: (pre-plan, project-level — no phase plans exist)
role: reviewer (mechanism-inventory gate)
round: inventory
date: 2026-08-20
state: CONSUMED_PENDING (awaiting coordinator)
verdict: OWNER_DECISIONS_PENDING
actor: Claude Opus 5 (1M context)
project: live_clock_for_working_time_economics
---

# Mechanism-inventory gate — handoff

## Opening summary

Gate preconditions all hold: intention `RESOLVED (round 3)`, D1–D7 recorded with the
ledger empty, `plans/` contains only `.gitkeep`, master plan §3 shows this gate as the
only tracker row. Nine mechanisms inventoried and ranked; **all nine now carry
contract-grade definitions in the intention**, added as lettered sections (§1A, §2.3A,
§2.5A, §3.1A, §3.2A, §3.3A, §3.4A, §4.1A, §4.3A, §6A, §9A) with §4.2, §8, the status
block and §11 amended in place — no existing citation renumbers.

The gate does **not** pass, because two of the findings are product calls rather than
mechanism definitions. Both cards are below.

The three claims §11 nominated as "most worth attacking" behaved exactly as the prompt
predicted. The **§3.3 bound** survived as a number (≤ 1 s is right) but its denominator
is wrong. The **§3.1 window rule** survived — its conclusion is correct for a reason the
document does not give. **T8's ceiling** was the only nominated claim that was
substantively wrong, and it was wrong in an arithmetic nobody had done. Meanwhile the
two largest findings sit where nothing pointed: **§3.3's parenthetical "after the
transition"**, which hides an asynchronous settlement window in which the number falls
by the whole just-worked share, and **an unstated persistence risk in §4.3's "the
services hand it rows"**, where an ORM assignment writes the live value into the settled
column with nothing failing. Four rounds, four times the nominated list pointed away.

Highest-risk mechanism at the end of the gate: **M-5 (one-basis propagation under
composition)** — not because the rule is unclear, but because every one of its failure
modes produces a payload that is nearly coherent, and "nearly coherent at whole-second
granularity" is indistinguishable from correct in every assertion this feature can
write.

---

## ⚠ OWNER DECISIONS REQUIRED (2)

### Card 1 — When a worker stops, the clock briefly shows the time gone. Ship that, or engineer it away?

**Question.** Closing a working step publishes the time a moment *later* than it removes
it from the live clock. Do we ship that gap and tell the frontend about it, or build the
extra machinery to close it?

**Story.** Jonas finishes sanding at 14:32 after 25 minutes. He taps "done". For a
moment — usually a blink, occasionally half a minute — his card and the manager's widget
both show his 25 minutes **gone**, back to where they were before he started. Then the
number returns. If the background job that files his time fails three times, it does not
return until someone touches that step again.

**Branches.**
- *Ship it, tell them:* costs nothing; the frontend is told to render whatever is
  served, and a brief dip is possible right after someone stops working.
- *Engineer it away:* the live figure would be computed from the work records
  themselves rather than from the filed total — more work per request, and it reopens
  the mechanism you approved in D2.

**Recommendation.** Ship it and tell them. The gap is normally shorter than a page
refresh, and hiding it would mean two ways of counting the same minutes — the thing this
whole pipeline exists to remove.

**On silence.** The gate holds; no decrease contract is written to the frontend.

**Trace.** §3.3A C.1, §5.4, §6A C, §9A T11, closeout obligation 5.

### Card 2 — Inside the frozen "final" box, one number keeps ticking. Leave it?

**Question.** Both the production-time widget and the worker's budget screen show a
frozen end-of-job summary. One field inside it — the percentage — is wired to the live
figure and will now tick while every number beside it stays frozen. Leave that wiring,
or freeze the percentage with its neighbours?

**Story.** A chair's job is finished and its summary reads "2 h 40 m · 12 % over". A
week later someone reopens a step to fix a scratch. The summary's minutes stay at 2 h
40 m, as they should — but the percentage starts climbing while the manager watches.
Same box, one number moving, the rest frozen.

**Branches.**
- *Leave it:* no code changes; the box behaves as it already does today, only more
  visibly.
- *Freeze it:* the summary is internally consistent; one small change to how that box is
  built.

**Recommendation.** Freeze it. This is the same one-line-two-answers defect you settled
in D6 when you said money should tick with its minutes — here the fix points the other
way, because everything else in that box is a record of what happened.

**On silence.** The gate holds; §5.3's disposition stands and both faces ship ticking.

**Trace.** §4.1A B, §4.2, §5.3, §9A.

---

## The inventory

Risk column: *silent-failure risk* per charter rule 6 — "if this is subtly wrong, does
anything crash, or does the system quietly behave wrong forever?"

| # | Mechanism | Silent-failure risk | Contract before | Contract after | Where it lives now |
|---|---|---|---|---|---|
| M-1 | `open_working_share` — predicate set, `COALESCE` attribution, `RecordContribution` filter | **High** — a wrong predicate returns a plausible number for every task | prose sketch; output type, rounding locus, `state` semantics, three zero-cases and the singularity guarantee all undefined | contract-grade: output `int`; rounding locus pinned to the share; input types as the ORM delivers them; the `state` field is the **bucket key**, not the column; totality over the 8-member enum shown, ranking shown inert; three unenumerated zero-cases added; singularity proved from `uix_step_state_records_active`; deleted-step-divides recorded | §3.1A |
| M-2 | the window rule — `min(entered_at)` anchor, 1-day buffer, sufficiency | **High** — an over-late anchor over-credits, silently | anchor correct (finding 3); sufficiency justified by pointing at settlement's buffer | derived independently: `W_start ≤ min(entered_at)` is **necessary and sufficient**; the buffer is slack; the borrowed argument is replaced by the transferable one; strict `entered_at < window_end` recorded | §3.2A |
| M-3 | the no-snap parity bound | **High** — the load-bearing invariant of the feature | bound asserted with an untested denominator; "nothing else may contribute drift" asserted | derived (≤ 1 s, attaining fixture given); denominator corrected to **per step holding an open working record**; "only drift source" **refuted** — three non-rounding sources enumerated at source | §3.3A |
| M-4 | cost model and the stated ceiling | Medium — a cost error degrades, it does not lie | ceiling asserted, bounded by the 50-task cap | derived: bound is `min(open working records, workspace headcount)`; one call = 1 statement + **2** sweeps; window bound restated as conditional on the overnight sweep while correctness is not | §3.4A |
| M-5 | one-basis propagation under composition | **Highest** — every failure mode yields a *nearly* coherent payload | HC-5 stated as a rule; composition unaddressed; `ServiceContext`/`run_service` constraints unnoticed | injection contract (type, site, scope); per-caller declaration table for all four callers of `get_task_budget_status`/`_build_evaluated_status`; the E-P double-computation named; the price-scenario cost/time-dependence regression named | §1A HC-3A, §4.1A D |
| M-6 | the pre-registered E-B aggregate decision | **High** — a silent per-payload divergence | "two resolutions are arithmetically identical" asserted | **conditionally true, condition pinned**: identical iff the rounding is applied to the open share per step; under §3.1's other reading they diverge on any exact half-second. Population equality of the two step sets verified | §4.1A A |
| M-7 | the identity claims that bound the change | **High** — a moved allowance is invisible and catastrophic | one of three allowance paths verified; settled-consumer list of four | three paths enumerated, each with its own reason; consumer list made total (8 sites); field inventory swept key by key across all three serializers, two live keys found unnamed | §2.5A, §4.1A B–C, §4.3A |
| M-8 | disowning-event semantics | Medium-high — a false contract shipped to another codebase | "mark-inaccurate, record/step deletion", monotonicity exception | family enumerated over the shipped commands: two events added (E2 closed-record flag, E3 sibling rise), one removed (**record deletion is not a shipped capability**), settled-column asymmetry named; §5.4's client rules restated per event | §6A |
| M-9 | T1–T8 as mechanisms | **High** — an inert test is worse than no test | eight rows, mutations named but not computed | full writability walk; **T1's mutation shown not to bite**, rewritten as T1′ with both sides; T2's mutation confirmed both-sides with its precondition; T3/T4/T5 preconditions added; T8's ceiling row demoted to a Review-log measurement; four rows added (T9–T12) | §9A |

Two rule-6 mechanisms **not** in the prompt's nine, surfaced during the sweep and
contracted anyway:

- **ORM-instance persistence of the live figure** (§1A HC-1A) — the negation of HC-1,
  reachable by one assignment, with no failing test in the current criterion set.
- **The `now` injection site under a fixed service signature** (§1A HC-3A) — HC-3 is
  unimplementable as stated without deciding this, and the obvious implementation (a
  defaulted parameter that reads the clock when absent) *is* the defect T1 exists to
  catch.

---

## Worked-example audit

Every derived number in the intention, recomputed by hand against
`concurrency.py:_sweep` as coded (boundaries from `sorted({start, end})`, membership
`start <= left and end >= right`, `share = segment / k`).

| # | Number in the document | Arithmetic performed | Follows its rule? |
|---|---|---|---|
| §3.2 case 1 | "60 vs 30" | two `user_id`-scoped sweeps, one interval each, `k = 1` ⇒ 1800 + 1800 = 3600 s; naive per-section divisor ⇒ 900 + 900 = 1800 s | **yes** |
| §3.2 case 2 | "20 + 10/2 = 25 m; B 5 m; naive 15 m" | points {9:00, 9:20, 9:30}; `[9:00,9:20]` k=1 ⇒ A+1200; `[9:20,9:30]` k=2 ⇒ A+300, B+300 ⇒ A 1500 s, B 300 s; naive 1800/2 = 900 s | **yes** (sum 1800 = wall clock) |
| §3.2 case 3 | "the cross-task divisor" | wrapper filters on `user_id` with no task predicate ⇒ both intervals in one sweep ⇒ k=2 | **yes** (no explicit number asserted) |
| §3.2 case 4 | "20/2 + 10 = 20 m, not 30" | `[9:00,9:20]` k=2 ⇒ A+600, B+600; `[9:20,9:30]` k=1 ⇒ A+600 ⇒ A 1200 s | **yes** (sum 1800 = wall clock) |
| §3.3 | "≤ 1 second per credited user" | \|round(P) + round(s_R) − round(P + s_R)\| < 1.5 over integers ⇒ ≤ 1; attained at P = s_R = 1.5 (4 vs 3) | **number yes, denominator no** — see M-3 |
| §3.4 | "≤ 50 small, bounded sweeps" | 50-task cap bounds tasks; steps per task unbounded; one open record per step; one sweep per *user* | **no** — see M-4 |
| §3.4 | "window bounded to under ~2 days" | overnight sweep closes shifts started `< midnight` and stamps at midnight ⇒ open record ≤ ~24 h old; +1 day buffer < 48 h | **yes**, but conditional on the sweep running |
| §4.1 | "two resolutions are arithmetically identical" | `Σ(a+b) = Σa + Σb` for integers ⇒ identical under the per-share locus; banker's rounding at exact halves ⇒ not identical under the per-sum locus | **conditionally** — see M-6 |
| §5.2 c.1 motivating card | "25 minutes into a 3 m 6 s allowance ⇒ `worked_seconds: 0`" | settled column only, open record excluded by `c.is_open` in `_recompute_step_time_totals` | **yes** — the defect is real and correctly diagnosed |

Precondition found by doing the arithmetic: cases 2, 3 and 4 all require
`allows_batch_working = True`. Cases 2 and 3 say "batch"; **case 4 does not**, and a
fixture built from its prose alone computes 1800 s where the row expects 1200 s.

---

## T1–T8 writability walk

Environment supports all rows: real Postgres (`tests/conftest.py:initialize_database`),
existing integration fixtures build real `TaskStep`/`StepStateRecord` rows with
`try/finally` teardown, `count_queries` exists for statement counting, and
`json.dumps(sort_keys=True)` + `sha256` payload identity is already in use in
`test_production_time_query.py`.

| T | Constructible as stated? | Assertions decidable? | Note |
|---|---|---|---|
| T1 | yes | **no** — see below | mutation does not bite; rewritten as T1′ (§9A) |
| T2 | yes | yes | `_recompute_step_time_totals` is directly callable; commits ⇒ owns teardown (charter 11½); one fixture precondition added |
| T3 | yes | yes | rows 2–4 need `allows_batch_working=True`; row 1 needs two **distinct** credited users, its only reason for 3600 |
| T4 | yes | yes | the deleted-record row exercises a state no shipped command produces — defense-in-depth, must say so; marked-wrong must be two rows; one row missing (T4.5) |
| T5 | yes | yes | sequencing already correct (finding 5); strongest fixture is an open **PENDING** record, which proves the state filter rather than the absence of records |
| T6 | yes | **only under the pinned locus** | headline-equals-rows is guaranteed because both sum the same per-step integers (§3.1A A) |
| T7 | yes | yes | extends the existing money-token key walk |
| T8 | yes (heavy fixture) | query-count row yes; **ceiling row no** | "the plan records the measured worst case" is a measurement, not an automated criterion (charter rule 1) — Review log, not criteria; and the ceiling asserted must be §3.4A B's |

### Named mutations — both sides computed, for the named fixture

| Mutation | Site (file, definition vs call) | Value under contract | Value under mutation | Differ? |
|---|---|---|---|---|
| T1 as written: second wall-clock read inside the loader | loader **definition** site | payload A ≡ payload B | payload A ≡ payload B (two runs ~20 ms apart; `int(round(·))` collapses the delta to the same integer) | **NO — inert** |
| T1′ row a: clock stub advancing +5 s per call | loader **definition** site; fixture = one open batchable record entered 600 s ago | `600, 600` | `600, 605` | yes |
| T1′ row b: `now` resolved per callee instead of per request | **call** site, in each of E-P / E-B / E-A | stub call-count `== 1` | call-count `≥ 2` | yes |
| T2: sweep call → `now − entered_at` | loader **call** site (**not** `concurrency.py`'s definition) — batch row, §3.2 case 2 shape | live 1500 vs settled 1500, \|Δ\| = 0 | live 1800 vs settled 1500, \|Δ\| = 300 | yes → **red** |
| T2, same mutation, single-open-record row | same call site | live 1800 vs settled 1800, \|Δ\| = 0 | live 1800 vs settled 1800, \|Δ\| = 0 | no → **green**, as the row claims |
| T9 (added): assign the live figure onto `step.total_working_seconds` | loader **call** site in each of the three services; fixture = step with settled `0`, open share `600` | column re-read `0` | column re-read `600` | yes |
| T12 (added): feed live figures into `charged_seconds` | loader **call** site, where the live row set is built | `allowance_seconds` identical to the settled payload | allowances shift by the excluded step's live share | yes — **but the fixture requires a state the transition core cannot produce**; the honest form is stated in §9A |

T2's "green" row carries a precondition that was not in the document and that destroys
its discrimination if missed: **the single-open-record fixture's worker must hold no
other open interval anywhere**, or §3.2 case 3's cross-task divisor turns it red for an
unrelated reason.

---

## Contradictions found

Each with both sides, the side chosen, and what the other side would have shipped.

**C1 — §4.2 vs §5.3, the E-P `final` block.**
§4.2: "…`allocation_method`, `status` readiness values, **the E-P `final` block**, and
every field not derived from worked seconds: byte-identical to today."
§5.3: "`final` (E-P) stays a frozen record. Its `percent_consumed` key is today wired to
the request-level percent… `final.percent_consumed` **ticks** while the other `final`
fields stay frozen."
**Chose §5.3** — verified in code (`division_serializers.py:serialize_task_production_time`
passes the request percent into `:_serialize_production_time_final`). §4.2 amended in
place. Had §4.2 won, T5's byte-identity golden would have been written to include
`final.percent_consumed`, and the row would have failed on the first task that had both
a result and an open record — read as a bug in the loader rather than in the criterion.

**C2 — §3.1's rounding locus vs §4.1's identity claim.**
§3.1: "rounded `int(round(·))` per step" — written against the whole
`live_worked_seconds` expression.
§4.1: "Two resolutions are arithmetically identical."
**Chose the per-open-share locus** (§3.1A A), which is the only reading that makes §4.1
true. Had the per-sum reading won, the planner's free choice between the two resolutions
would silently change payloads at every exact half-second share — reachable on demand
with a two-way batch split of an odd second count — and the divergence would appear as a
1-second flicker between the headline and the rows, i.e. as HC-5 failing.

**C3 — §2.3's absence claim vs the code.**
§2.3: "The 'no clock in the read layer' property… is a property of the **item-economics
query family**."
Code: `get_task_budget_allocations.py:get_task_budget_allocations` calls `today_utc()`
(= `datetime.now(timezone.utc).date()`) inside its per-task loop; `get_economics_configuration_status.py`
calls it too.
**Chose the code.** Had the claim stood, HC-3's scope would never have been defined, and
T1 would have "passed" for E-A while up to 50 unfrozen clock reads sat inside the
request — the exact shape of a test that cannot fail.

**C4 — §3.3's "Nothing else may contribute drift" vs three verified sources.**
**Chose the code** (§3.3A C). Had the claim stood, the first production report of a
25-minute drop at clock-out would have been triaged as "the live computation and
settlement have diverged, the defect HC-2 exists to prevent" — §3.3's own words — and a
correct mechanism would have been rebuilt to fix an operational lag.

**C5 — §5.4 / §6 / closeout obligation 5 "exactly two ways" vs the event family.**
**Chose the code** (§3.3A C.1, §6A A). The settlement window is a third way; marking a
*closed* record is a fourth entry into the second way; record deletion, which the text
names, is not a shipped capability. Had the text stood, the frontend would have built
smoothing against an enumeration that is wrong in both directions — and this is the
project that already lost four days to a handoff that outlived its own truth.

**C6 — §3.4's ceiling vs its own arithmetic.**
"…itself bounded by the endpoint's 50-task cap." The cap bounds tasks; nothing in it
bounds steps per task or workers per step. **Chose the derived bound** (§3.4A B). Had
the stated ceiling stood, T8's ceiling row would have been written to assert ≤ 50 sweeps
and would have passed on any realistic fixture while measuring nothing.

---

## Unilateral resolutions — listed for ratification

Each is a place where I picked a side. None reopens D1–D7.

| # | Resolution | What the other side would have shipped |
|---|---|---|
| U1 | Parity denominator → "per step holding an open working record" | a task-level parity assertion tolerating 1 s where the mechanism can legitimately produce 6 s, or rejecting correct behaviour as divergence |
| U2 | Rounding locus → round the open share, then add | §4.1's "identical" false; the planner's choice changes payloads |
| U3 | HC-3 scope covers E-A's `today_utc()`, replaced by `now.date()` | up to 50 unfrozen clock reads per request; T1 vacuous for E-A; a real mid-request date-rollover inconsistency left in place |
| U4 | §5.3's disposition extended to the E-B worker face's `result.percent_consumed` (pending card 2) | one of two identical wirings pinned and the other unnamed — the class-not-instance failure, again |
| U5 | §2.3 and §2.5 corrected and made total | the frontend receives an incomplete answer to its own audit question in the closeout handoff |
| U6 | D7's event family corrected: E5 (record deletion) removed, E2/E3 added | a client instructed to handle an event we cannot emit, and unhandled for two we can |
| U7 | Cost ceiling re-derived (headcount ∧ open-record count) | an unfalsifiable ceiling and a T8 row that measures nothing |
| U8 | Loader returns `int`; no ORM mutation (HC-1A) | float rows silently truncated in four allocator sites and a 500 on the money path; live values written into the settled column |
| U9 | Window sufficiency derived rather than borrowed | correct behaviour resting on an argument that does not apply, so the next person to touch the buffer has no way to reason about it |

---

## What I could not settle from the source

1. **Whether the settlement-window drop is acceptable product behaviour** — a value
   judgement, not a code fact. Owner card 1. What would settle it: the owner's answer.
2. **Whether the frozen-block `percent_consumed` should tick** — §5.3 already
   dispositioned the E-P instance, and D6's reasoning cuts the other way for a *frozen*
   block. Owner card 2.
3. **Observed queue latency for `PROCESS_STEP_TRANSITION` in this deployment.** I
   derived the bound from the code (`FALLBACK_POLL_SECONDS = 30`, `max_try = 3`,
   LISTEN/NOTIFY-driven), not from measurement. What would settle it: the analytics
   worker's own timing logs (`step_time_recomputed`) against the outbox row's
   `created_at` over a normal working day. Worth having before answering card 1.
4. **Whether `now` becomes a `ServiceContext` field or a threaded parameter.** Both
   satisfy HC-3A; `ServiceContext` carries a standing "never add flags or config values"
   instruction that a request timestamp arguably does not violate. This is the planner's
   naming-registry decision, not a mechanism, and §1A HC-3A states the contract either
   reading must satisfy.
5. **Whether any path can put a step into a terminal state without closing its open
   record.** I verified the two paths that exist (`_step_transition_core.py:apply_step_transition`,
   `remove_task_step.py`) and both close first. I did not exhaustively prove no future
   path can; the invariant is stated in §4.3A so a reviewer knows what to check.

---

## Architecture graph

Read-only orientation only; **nothing promoted, rejected or edited**. State at the gate:
187 nodes / 278 edges, 0 pending, 0 stale, 0 diagnostics, every node `human_confirmed` —
matches master plan §6.

What I would have recorded, for the closeout batch:

- The intention's §8 names four projection nodes. A **fifth** belongs in the same batch:
  `projection-item-economics-task-price-scenario`, which composes `get_task_budget_status`
  and therefore acquires the transitive read dependency without consuming a
  worked-derived field. Recorded in §8.
- `projection-item-economics-task-budget-allocations` **already** carries the invariant
  "the response's time-only fields reconcile with the same non-deleted step set used by
  budget status." That is HC-5's cross-surface claim, already in the graph. The closeout
  delta must keep it true, not restate it.
- No discrepancy between graph and code was found, so no `archgraph-discrepancies`
  finding is filed.

---

## Write perimeter

Generated from `git status --porcelain` and `git diff --name-only` at the workspace
root, not retyped.

**Modified (tracked):**
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/planning/intention.md` — +758 / −5

**Added (inside the already-untracked `handoffs/` table):**
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/handoffs/reviewer/2026-08-20_inventory_mechanism_inventory_handoff.md` — this file

**Nothing else.** No file under `app/` was touched; no test was run; no tracker row was
updated (the coordinator owns master plan §3); no archgraph mutation was performed. The
five untracked paths in `git status` (`archive/`, `handoffs/`, `master_plan.md`,
`plans/`, `prompts/`) were untracked before this session and are unchanged by it apart
from the handoff added above.

---

## Gate verdict

**OWNER_DECISIONS_PENDING.**

Every rule-6 mechanism now has a contract-grade definition in the intention, so the
inventory half of the exit gate is met. Two findings are product calls the gate cannot
make: the settlement-window drop (card 1) and the ticking field inside the frozen block
(card 2). Both change what ships and what the frontend is told.

**The implementation-planner does not start.** When both cards are answered, the
coordinator folds them into §5.4 / §6A C and §4.1A B / §5.3, flips the intention's status
block, and the gate closes at `PASS` without a further reviewer session — no card
carries a branch that would change any of the nine contracts, only the behaviour those
contracts describe.
